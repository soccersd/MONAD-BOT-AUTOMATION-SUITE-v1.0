import asyncio
import random
import platform
from decimal import Decimal
from typing import Dict
from web3 import AsyncWeb3, Web3
from eth_account import Account
from colorama import init, Fore, Style
from loguru import logger

# Initialize colorama
init(autoreset=True)

# Fix for Windows
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ========== NETWORK SETTINGS ==========
RPC_URLS = [
    "https://testnet-rpc.monad.xyz",
    "https://testnet-rpc.monorail.xyz",
    "https://monad-testnet.drpc.org"
]

EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"

# ========== CONTRACT SETTINGS ==========
CONTRACT_ADDRESSES = {
    "APRIORI": "0xb2f82D0f38dc453D596Ad40A37799446Cc89274A"
}

# ========== STAKING SETTINGS ==========
STAKING_SETTINGS = {
    "min_amount": 0.1,
    "max_amount": 0.1,
    "pause_between_stakes": (10, 30)
}

# Contract address
STAKE_ADDRESS = CONTRACT_ADDRESSES["APRIORI"]

# Staking settings
AMOUNT_TO_STAKE = STAKING_SETTINGS["min_amount"], STAKING_SETTINGS["max_amount"]
PAUSE_BETWEEN_STAKES = STAKING_SETTINGS["pause_between_stakes"]

STAKE_ABI = [
    {
        "type": "function",
        "name": "deposit",
        "inputs": [
            {"name": "assets", "type": "uint256", "internalType": "uint256"},
            {"name": "receiver", "type": "address", "internalType": "address"}
        ],
        "outputs": [
            {"name": "shares", "type": "uint256", "internalType": "uint256"}
        ],
        "stateMutability": "payable",
    },
    {
        "type": "function",
        "name": "requestRedeem",
        "inputs": [
            {"name": "shares", "type": "uint256", "internalType": "uint256"},
            {"name": "controller", "type": "address", "internalType": "address"},
            {"name": "owner", "type": "address", "internalType": "address"}
        ],
        "outputs": [
            {"name": "requestId", "type": "uint256", "internalType": "uint256"}
        ],
        "stateMutability": "nonpayable"
    },
    {
        "type": "function",
        "name": "maxRedeem",
        "inputs": [
            {"name": "owner", "type": "address", "internalType": "address"}
        ],
        "outputs": [
            {"name": "maxShares", "type": "uint256", "internalType": "uint256"}
        ],
        "stateMutability": "view"
    }
]

# ========== MINIMAL CONFIG ===========
class DummyAprioriConfig:
    class APRIORI:
        AMOUNT_TO_STAKE = AMOUNT_TO_STAKE
        STAKE = True
    class SETTINGS:
        ATTEMPTS = 3
        PAUSE_BETWEEN_ATTEMPTS = PAUSE_BETWEEN_STAKES
    APRIORI = APRIORI()
    SETTINGS = SETTINGS()

# ========== APRIORI CLASS ============
class Apriori:
    def __init__(self, account_index: int, proxy: str, private_key: str, config: DummyAprioriConfig):
        self.account_index = account_index
        self.proxy = proxy
        self.private_key = private_key
        self.config = config
        self.account = Account.from_key(private_key=private_key)
        
        # Connect to RPC
        self.web3 = None
        for rpc_url in RPC_URLS:
            try:
                # First check connection with synchronous Web3
                sync_web3 = Web3(Web3.HTTPProvider(rpc_url))
                if sync_web3.is_connected():
                    logger.info(f"Successfully connected to RPC: {rpc_url}")
                    # Now create AsyncWeb3 for later async usage
                    self.web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))
                    break
            except Exception as e:
                logger.error(f"Cannot connect to {rpc_url}: {str(e)}")
        
        if not self.web3:
            raise Exception("Cannot connect to any RPC")

    async def get_gas_params(self) -> Dict[str, int]:
        latest_block = await self.web3.eth.get_block("latest")
        base_fee = latest_block["baseFeePerGas"]
        max_priority_fee = await self.web3.eth.max_priority_fee
        max_fee = base_fee + max_priority_fee
        return {"maxFeePerGas": max_fee, "maxPriorityFeePerGas": max_priority_fee}

    async def estimate_gas(self, transaction: dict) -> int:
        try:
            estimated = await self.web3.eth.estimate_gas(transaction)
            return int(estimated * 1.1)
        except Exception as e:
            logger.warning(f"[{self.account_index}] Error estimating gas: {e}. Using default gas limit")
            raise e

    async def stake_mon(self):
        insufficient_balance_count = 0
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                random_amount = round(
                    random.uniform(
                        self.config.APRIORI.AMOUNT_TO_STAKE[0],
                        self.config.APRIORI.AMOUNT_TO_STAKE[1],
                    ),
                    random.randint(6, 12),
                )
                logger.info(f"[{self.account_index}] Staking {random_amount} MON on Apriori")
                contract = Web3().eth.contract(address=STAKE_ADDRESS, abi=STAKE_ABI)
                amount_wei = Web3.to_wei(random_amount, "ether")
                gas_params = await self.get_gas_params()
                transaction = {
                    "from": self.account.address,
                    "to": STAKE_ADDRESS,
                    "value": amount_wei,
                    "data": contract.functions.deposit(amount_wei, self.account.address)._encode_transaction_data(),
                    "chainId": 10143,
                    "type": 2,
                }
                estimated_gas = await self.estimate_gas(transaction)
                transaction.update({
                    "nonce": await self.web3.eth.get_transaction_count(self.account.address, "latest"),
                    "gas": estimated_gas,
                    **gas_params,
                })
                signed_txn = self.web3.eth.account.sign_transaction(transaction, self.private_key)
                tx_hash = await self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
                logger.info(f"[{self.account_index}] Waiting for transaction confirmation...")
                await self.web3.eth.wait_for_transaction_receipt(tx_hash)
                logger.success(f"[{self.account_index}] Successfully staked {random_amount} MON on Apriori. TX: {EXPLORER_URL}{tx_hash.hex()}")
                return True
            except Exception as e:
                error_str = str(e)
                if "insufficient balance" in error_str:
                    insufficient_balance_count += 1
                    logger.error(f"[{self.account_index}] | Error in stake_mon on Apriori: {e}. Sleeping for 5 seconds")
                    if insufficient_balance_count >= 3:
                        logger.warning(f"[{self.account_index}] Insufficient balance detected 3 times. Moving to next account.")
                        return False
                    await asyncio.sleep(5)
                else:
                    random_pause = random.randint(self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0], self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1])
                    logger.error(f"[{self.account_index}] | Error in stake_mon on Apriori: {e}. Sleeping for {random_pause} seconds")
                    await asyncio.sleep(random_pause)
        return False

    async def request_unstake(self):
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                logger.info(f"[{self.account_index}] Requesting to unstake MON from Apriori")
                contract = self.web3.eth.contract(address=STAKE_ADDRESS, abi=STAKE_ABI)
                max_shares = await contract.functions.maxRedeem(self.account.address).call()
                if max_shares == 0:
                    logger.warning(f"[{self.account_index}] No shares available to redeem")
                    return False
                amount_wei = max_shares
                logger.info(f"[{self.account_index}] Maximum available to unstake: {Web3.from_wei(max_shares, 'ether')} shares")
                gas_params = await self.get_gas_params()
                transaction = {
                    "from": self.account.address,
                    "to": STAKE_ADDRESS,
                    "data": contract.functions.requestRedeem(amount_wei, self.account.address, self.account.address)._encode_transaction_data(),
                    "chainId": 10143,
                    "type": 2,
                }
                estimated_gas = await self.estimate_gas(transaction)
                transaction.update({
                    "nonce": await self.web3.eth.get_transaction_count(self.account.address, "latest"),
                    "gas": estimated_gas,
                    **gas_params,
                })
                signed_txn = self.web3.eth.account.sign_transaction(transaction, self.private_key)
                tx_hash = await self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
                logger.info(f"[{self.account_index}] Waiting for unstake request confirmation...")
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
                if receipt["status"] == 1:
                    logger.success(f"[{self.account_index}] Successfully requested to unstake {Web3.from_wei(amount_wei, 'ether')} MON from Apriori. TX: {EXPLORER_URL}{tx_hash.hex()}")
                    return True
                else:
                    logger.error(f"[{self.account_index}] Transaction failed. Status: {receipt['status']}")
                    return False
            except Exception as e:
                random_pause = random.randint(self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0], self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1])
                logger.error(f"[{self.account_index}] | Error in request_unstake on Apriori: {e}. Sleeping for {random_pause} seconds")
                await asyncio.sleep(random_pause)
        return False

# ========== PRIVATE KEY READER ==========
def read_private_key(file_path='pvkey.txt'):
    try:
        with open(file_path, 'r') as f:
            for line in f:
                if line.strip() and not line.strip().startswith('#'):
                    pk = line.strip()
                    if pk.startswith('0x'):
                        pk = pk[2:]
                    if len(pk) == 64:
                        return '0x' + pk
    except Exception as e:
        print(f"{Fore.RED}Error reading private key: {e}{Style.RESET_ALL}")
    return None

# ========== MAIN CLI ==========
async def main():
    print(f"{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'APRIORI BOT':^60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}")

    private_key = read_private_key('pvkey.txt')
    if not private_key:
        print(f"{Fore.RED}No valid private key found!{Style.RESET_ALL}")
        return

    proxy = ""
    config = DummyAprioriConfig()
    account_index = 0
    apriori = Apriori(account_index, proxy, private_key, config)
    print(f"{Fore.CYAN}Using account: {Account.from_key(private_key).address}{Style.RESET_ALL}")

    # Automatically stake 0.1 MON
    print(f"{Fore.YELLOW}Staking 0.1 MON on Apriori...{Style.RESET_ALL}")
    await apriori.stake_mon()

if __name__ == "__main__":
    asyncio.run(main()) 