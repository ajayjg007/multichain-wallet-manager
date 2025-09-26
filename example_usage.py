from src.wallet_manager import MultiChainWalletManager

def main():
    # 初始化钱包管理器
    manager = MultiChainWalletManager()
    
    # 创建新钱包
    wallet = manager.create_wallet("my_wallet")
    print(f"Created wallet: {wallet['address']}")
    
    # 获取所有链上的余额
    balances = manager.get_all_balances("my_wallet")
    
    for chain, balance in balances.items():
        if 'error' not in balance:
            print(f"{chain}: {balance['native_token']['balance']} {balance['native_token']['symbol']}")
    
    # 转账示例（注意：需要有足够的余额和gas费）
    # tx_hash = manager.transfer_native_token("my_wallet", "ethereum", "0x...", 0.01)
    # print(f"Transaction hash: {tx_hash}")
    
    # 保存钱包（不包含私钥）
    manager.save_wallets("my_wallets.json", include_private_keys=False)

if __name__ == "__main__":
    main()
