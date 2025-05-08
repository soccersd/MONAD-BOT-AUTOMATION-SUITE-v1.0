import asyncio
import random
from web3 import Web3
from eth_account import Account
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# ========== NETWORK SETTINGS ==========
RPC_URLS = [
    "https://testnet-rpc.monad.xyz",
    "https://testnet-rpc.monorail.xyz",
    "https://monad-testnet.drpc.org"
]

EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"
CHAIN_ID = 10143  # Monad testnet

# ========== CONTRACT SETTINGS ==========
ONCHAIN_GM_CONTRACT = Web3.to_checksum_address("0x7500a83df2af99b2755c47b6b321a8217d876a85")

# ABI for OnChainGM contract
ONCHAIN_GM_ABI = [
    {
        "inputs": [],
        "name": "mint",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "ownerOf",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# ========== MINT SETTINGS ==========
MINT_PRICE = 0.01  # MON
MIN_BALANCE = 0.02  # MON (including gas)

# Read private key function
def read_private_key(file_path='pvkey.txt'):
    try:
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252', 'utf-16']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    for line in file:
                        # Skip comment lines
                        if line.strip().startswith('#') or not line.strip():
                            continue
                        
                        # Remove whitespace and validate format
                        private_key = line.strip()
                        
                        # Remove 0x prefix if present
                        if private_key.startswith('0x'):
                            private_key = private_key[2:]
                        
                        # Check length
                        if len(private_key) != 64:
                            print(f"{Fore.YELLOW}Warning: Invalid private key (incorrect length){Style.RESET_ALL}")
                            continue
                        
                        # Check if hex string
                        try:
                            int(private_key, 16)
                            print(f"{Fore.GREEN}Found valid private key in file{Style.RESET_ALL}")
                            return '0x' + private_key  # Add 0x prefix
                        except ValueError:
                            print(f"{Fore.YELLOW}Warning: Found non-hex characters in private key{Style.RESET_ALL}")
                            continue
                
                # If no valid private key found in this encoding, try next
            except UnicodeDecodeError:
                continue  # Try next encoding
    
    except FileNotFoundError:
        print(f"{Fore.RED}File {file_path} not found{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Error reading file: {str(e)}{Style.RESET_ALL}")
    
    print(f"{Fore.RED}No valid private key found in {file_path}{Style.RESET_ALL}")
    return None

async def mint_nft(w3, private_key, wallet_address, max_attempts=3):
    """Mint OnChainGM NFT"""
    for attempt in range(max_attempts):
        try:
            print(f"{Fore.CYAN}Minting OnChainGM NFT...{Style.RESET_ALL}")
            
            # Create contract instance
            contract = w3.eth.contract(address=ONCHAIN_GM_CONTRACT, abi=ONCHAIN_GM_ABI)
            
            # Get gas parameters
            gas_price = w3.eth.gas_price
            
            # Build transaction
            transaction = {
                "from": wallet_address,
                "to": ONCHAIN_GM_CONTRACT,
                "value": w3.to_wei(MINT_PRICE, "ether"),  # MINT_PRICE MON mint price
                "nonce": w3.eth.get_transaction_count(wallet_address),
                "gasPrice": int(gas_price * 1.1),  # Add 10% buffer
                "chainId": CHAIN_ID
            }
            
            # Estimate gas
            try:
                gas_estimate = w3.eth.estimate_gas(transaction)
                transaction["gas"] = int(gas_estimate * 1.2)  # Add 20% buffer
                print(f"{Fore.BLUE}Estimated gas: {gas_estimate}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.YELLOW}Error estimating gas: {str(e)}. Using default gas limit.{Style.RESET_ALL}")
                transaction["gas"] = 300000  # Default gas limit
            
            # Sign and send transaction
            signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            print(f"{Fore.YELLOW}Mint transaction sent: {tx_hash.hex()}{Style.RESET_ALL}")
            
            # Wait for confirmation
            print(f"{Fore.YELLOW}Waiting for transaction confirmation...{Style.RESET_ALL}")
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            
            if receipt.status == 1:
                print(f"{Fore.GREEN}Successfully minted OnChainGM NFT!{Style.RESET_ALL}")
                print(f"{Fore.GREEN}View details at: {EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.RED}Minting failed: {receipt}{Style.RESET_ALL}")
                
                if attempt < max_attempts - 1:
                    pause_time = random.randint(10, 30)
                    print(f"{Fore.CYAN}Pausing for {pause_time} seconds before retry...{Style.RESET_ALL}")
                    await asyncio.sleep(pause_time)
        
        except Exception as e:
            print(f"{Fore.RED}Error minting OnChainGM NFT: {str(e)}{Style.RESET_ALL}")
            
            if attempt < max_attempts - 1:
                pause_time = random.randint(10, 30)
                print(f"{Fore.CYAN}Pausing for {pause_time} seconds before retry...{Style.RESET_ALL}")
                await asyncio.sleep(pause_time)
    
    print(f"{Fore.RED}Failed to mint OnChainGM NFT after {max_attempts} attempts{Style.RESET_ALL}")
    return False

async def run():
    print(f"{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'ONCHAIN GM NFT MINTER':^60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}")

    # Connect to RPC
    w3 = None
    for rpc_url in RPC_URLS:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 10}))
            if w3.is_connected():
                print(f"{Fore.GREEN}Successfully connected to RPC: {rpc_url}{Style.RESET_ALL}")
                break
        except Exception as e:
            print(f"{Fore.RED}Cannot connect to {rpc_url}: {str(e)}{Style.RESET_ALL}")
    
    if not w3:
        print(f"{Fore.RED}Cannot connect to any RPC{Style.RESET_ALL}")
        return False

    # Get private key from file
    private_key = read_private_key('pvkey.txt')
    if not private_key:
        print(f"{Fore.RED}Cannot proceed without a valid private key{Style.RESET_ALL}")
        return False

    # Create account from private key
    account = Account.from_key(private_key)
    wallet_address = account.address
    print(f"{Fore.CYAN}Using account: {wallet_address}{Style.RESET_ALL}")

    # Get wallet balance
    balance = w3.eth.get_balance(wallet_address)
    balance_eth = w3.from_wei(balance, 'ether')
    print(f"{Fore.BLUE}MON Balance: {balance_eth} MON{Style.RESET_ALL}")

    # Check if we have enough balance for minting
    if balance_eth < MIN_BALANCE:
        print(f"{Fore.RED}Insufficient balance for minting. Need at least {MIN_BALANCE} MON.{Style.RESET_ALL}")
        return False
    
    # Mint NFT
    success = await mint_nft(w3, private_key, wallet_address)
    
    if success:
        print(f"{Fore.GREEN}OnChainGM NFT minting completed successfully!{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}OnChainGM NFT minting failed{Style.RESET_ALL}")
    
    return success

# Run the bot when executed directly
if __name__ == "__main__":
    asyncio.run(run()) 