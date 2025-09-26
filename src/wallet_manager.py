import json
import time
from typing import Dict, List, Optional, Tuple
from web3 import Web3
from eth_account import Account
import requests

class MultiChainWalletManager:
    def __init__(self, config_file: str = "chains_config.json"):
        self.chains = {}
        self.wallets = {}
        self.load_config(config_file)
        
    def load_config(self, config_file: str):
        """加载链配置"""
        with open(config_file, 'r') as f:
            config = json.load(f)
            
        for chain_name, chain_config in config['chains'].items():
            self.chains[chain_name] = {
                'rpc_url': chain_config['rpc_url'],
                'chain_id': chain_config['chain_id'],
                'name': chain_config['name'],
                'symbol': chain_config['symbol'],
                'decimals': chain_config['decimals'],
                'explorer': chain_config.get('explorer', ''),
                'web3': Web3(Web3.HTTPProvider(chain_config['rpc_url']))
            }

    def create_wallet(self, wallet_name: str) -> Dict:
        """创建新钱包"""
        account = Account.create()
        wallet_info = {
            'name': wallet_name,
            'address': account.address,
            'private_key': account.privateKey.hex(),
            'balances': {}
        }
        
        self.wallets[wallet_name] = wallet_info
        return wallet_info

    def import_wallet(self, wallet_name: str, private_key: str) -> Dict:
        """导入现有钱包"""
        account = Account.from_key(private_key)
        wallet_info = {
            'name': wallet_name,
            'address': account.address,
            'private_key': private_key,
            'balances': {}
        }
        
        self.wallets[wallet_name] = wallet_info
        return wallet_info

    def get_balance(self, wallet_name: str, chain_name: str) -> Dict:
        """获取指定链上的余额"""
        if wallet_name not in self.wallets:
            raise ValueError(f"Wallet {wallet_name} not found")
        
        if chain_name not in self.chains:
            raise ValueError(f"Chain {chain_name} not found")
        
        wallet = self.wallets[wallet_name]
        chain = self.chains[chain_name]
        web3 = chain['web3']
        
        # 获取原生代币余额
        balance_wei = web3.eth.get_balance(wallet['address'])
        balance_eth = web3.from_wei(balance_wei, 'ether')
        
        balance_info = {
            'chain': chain_name,
            'address': wallet['address'],
            'native_token': {
                'symbol': chain['symbol'],
                'balance': float(balance_eth),
                'balance_wei': balance_wei
            },
            'tokens': []
        }
        
        # 更新钱包余额信息
        if chain_name not in wallet['balances']:
            wallet['balances'][chain_name] = {}
        
        wallet['balances'][chain_name]['native'] = balance_info['native_token']
        
        return balance_info

    def get_all_balances(self, wallet_name: str) -> Dict:
        """获取所有链上的余额"""
        all_balances = {}
        
        for chain_name in self.chains:
            try:
                balance = self.get_balance(wallet_name, chain_name)
                all_balances[chain_name] = balance
            except Exception as e:
                print(f"Error getting balance for {chain_name}: {e}")
                all_balances[chain_name] = {'error': str(e)}
        
        return all_balances

    def transfer_native_token(self, wallet_name: str, chain_name: str, 
                            to_address: str, amount: float, gas_price_gwei: int = 20) -> str:
        """转账原生代币"""
        if wallet_name not in self.wallets:
            raise ValueError(f"Wallet {wallet_name} not found")
        
        wallet = self.wallets[wallet_name]
        chain = self.chains[chain_name]
        web3 = chain['web3']
        
        # 构建交易
        nonce = web3.eth.get_transaction_count(wallet['address'])
        
        transaction = {
            'to': to_address,
            'value': web3.to_wei(amount, 'ether'),
            'gas': 21000,
            'gasPrice': web3.to_wei(gas_price_gwei, 'gwei'),
            'nonce': nonce,
        }
        
        # 签名交易
        signed_txn = web3.eth.account.sign_transaction(transaction, wallet['private_key'])
        
        # 发送交易
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        return tx_hash.hex()

    def get_token_balance(self, wallet_name: str, chain_name: str, token_address: str) -> Dict:
        """获取ERC20代币余额"""
        wallet = self.wallets[wallet_name]
        chain = self.chains[chain_name]
        web3 = chain['web3']
        
        # ERC20 ABI
        erc20_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "symbol",
                "outputs": [{"name": "", "type": "string"}],
                "type": "function"
            }
        ]
        
        contract = web3.eth.contract(address=token_address, abi=erc20_abi)
        
        balance = contract.functions.balanceOf(wallet['address']).call()
        decimals = contract.functions.decimals().call()
        symbol = contract.functions.symbol().call()
        
        balance_formatted = balance / (10 ** decimals)
        
        return {
            'token_address': token_address,
            'symbol': symbol,
            'balance': balance_formatted,
            'balance_raw': balance,
            'decimals': decimals
        }

    def transfer_token(self, wallet_name: str, chain_name: str, token_address: str,
                      to_address: str, amount: float, gas_price_gwei: int = 20) -> str:
        """转账ERC20代币"""
        wallet = self.wallets[wallet_name]
        chain = self.chains[chain_name]
        web3 = chain['web3']
        
        # ERC20 ABI
        erc20_abi = [
            {
                "constant": False,
                "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function"
            }
        ]
        
        contract = web3.eth.contract(address=token_address, abi=erc20_abi)
        decimals = contract.functions.decimals().call()
        
        # 计算转账金额
        amount_with_decimals = int(amount * (10 ** decimals))
        
        # 构建交易
        nonce = web3.eth.get_transaction_count(wallet['address'])
        
        transaction = contract.functions.transfer(
            to_address,
            amount_with_decimals
        ).build_transaction({
            'from': wallet['address'],
            'gas': 100000,
            'gasPrice': web3.to_wei(gas_price_gwei, 'gwei'),
            'nonce': nonce,
        })
        
        # 签名并发送交易
        signed_txn = web3.eth.account.sign_transaction(transaction, wallet['private_key'])
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        return tx_hash.hex()

    def get_transaction_history(self, wallet_name: str, chain_name: str, limit: int = 10) -> List[Dict]:
        """获取交易历史（需要使用区块浏览器API）"""
        wallet = self.wallets[wallet_name]
        chain = self.chains[chain_name]
        
        if not chain.get('explorer'):
            return []
        
        # 这里需要根据不同的区块浏览器API来实现
        # 以Etherscan为例
        if 'etherscan' in chain['explorer']:
            return self._get_etherscan_history(wallet['address'], chain['explorer'], limit)
        
        return []

    def _get_etherscan_history(self, address: str, explorer_url: str, limit: int) -> List[Dict]:
        """从Etherscan获取交易历史"""
        try:
            # 注意：这需要Etherscan API密钥
            api_key = "YOUR_ETHERSCAN_API_KEY"
            url = f"{explorer_url}/api"
            
            params = {
                'module': 'account',
                'action': 'txlist',
                'address': address,
                'startblock': 0,
                'endblock': 99999999,
                'page': 1,
                'offset': limit,
                'sort': 'desc',
                'apikey': api_key
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if data['status'] == '1':
                return data['result']
            else:
                return []
                
        except Exception as e:
            print(f"Error fetching transaction history: {e}")
            return []

    def export_wallet(self, wallet_name: str, include_private_key: bool = False) -> Dict:
        """导出钱包信息"""
        if wallet_name not in self.wallets:
            raise ValueError(f"Wallet {wallet_name} not found")
        
        wallet = self.wallets[wallet_name].copy()
        
        if not include_private_key:
            wallet.pop('private_key', None)
        
        return wallet

    def save_wallets(self, filename: str = "wallets.json", include_private_keys: bool = False):
        """保存钱包到文件"""
        wallets_data = {}
        
        for name, wallet in self.wallets.items():
            wallet_data = wallet.copy()
            if not include_private_keys:
                wallet_data.pop('private_key', None)
            wallets_data[name] = wallet_data
        
        with open(filename, 'w') as f:
            json.dump(wallets_data, f, indent=2, default=str)

    def load_wallets(self, filename: str = "wallets.json"):
        """从文件加载钱包"""
        try:
            with open(filename, 'r') as f:
                wallets_data = json.load(f)
            
            self.wallets.update(wallets_data)
            
        except FileNotFoundError:
            print(f"Wallet file {filename} not found")
