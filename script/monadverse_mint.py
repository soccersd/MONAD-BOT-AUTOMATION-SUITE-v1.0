import requests
import time
import json
import random
import asyncio
from web3 import Web3
from eth_account import Account
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Network settings
RPC_URLS = [
    "https://monad-testnet-rpc.dwellir.com",  # Dwellir RPC
    "http://testnet-rpc.monad.xyz",  # HTTP fallback
    "https://testnet-rpc.monad.xyz"  # HTTPS option
]
EXPLORER_URL = "https://explorer.monad.xyz/tx/"
CHAIN_ID = 10143

# Contract settings
MONADVERSE_CONTRACT_ADDRESS = "0x2953399124F0cBB46d2CbACD8A89cF0599974963"  # Replace with actual address
MINT_PRICE = 1.79  # Price in MON
MIN_BALANCE = 2  # Minimum balance required
TOKEN_ID = 5  # MonadVerse token ID

# ERC1155 ABI for MonadVerse NFT
ERC1155_ABI = [
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "account",
                "type": "address"
            },
            {
                "internalType": "uint256",
                "name": "id",
                "type": "uint256"
            }
        ],
        "name": "balanceOf",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "tokenId",
                "type": "uint256"
            },
            {
                "internalType": "uint256",
                "name": "amount",
                "type": "uint256"
            }
        ],
        "name": "mint",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    }
]

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

async def get_gas_params(w3):
    """Get gas parameters for transaction"""
    try:
        # Get base fee
        latest_block = w3.eth.get_block('latest')
        base_fee = latest_block['baseFeePerGas']
        
        # Get max priority fee
        max_priority_fee = w3.eth.max_priority_fee
        
        # Calculate max fee
        max_fee = (base_fee * 2) + max_priority_fee
        
        return {
            'maxFeePerGas': max_fee,
            'maxPriorityFeePerGas': max_priority_fee
        }
    except Exception as e:
        print(f"{Fore.YELLOW}Error getting EIP-1559 gas params: {str(e)}. Using legacy gas pricing.{Style.RESET_ALL}")
        return None

async def get_nft_balance(w3, wallet_address):
    """Check NFT balance for current account"""
    try:
        # Create contract instance
        nft_contract = w3.eth.contract(
            address=MONADVERSE_CONTRACT_ADDRESS,
            abi=ERC1155_ABI
        )
        
        # Check balance using ERC1155 balanceOf
        balance = nft_contract.functions.balanceOf(wallet_address, TOKEN_ID).call()
        print(f"{Fore.GREEN}Current NFT Balance: {balance}{Style.RESET_ALL}")
        return balance
        
    except Exception as e:
        print(f"{Fore.YELLOW}Note: Could not check NFT balance: {str(e)}{Style.RESET_ALL}")
        return 0

async def mint_nft(w3, contract, wallet_address, private_key):
    try:
        print(f"{Fore.CYAN}Preparing mint transaction...{Style.RESET_ALL}")
        
        # Build mint transaction
        gas_params = await get_gas_params(w3)
        nonce = w3.eth.get_transaction_count(wallet_address)
        
        transaction = contract.functions.mint(TOKEN_ID, 1).build_transaction({
            "from": wallet_address,
            "value": w3.to_wei(MINT_PRICE, 'ether'),
            "nonce": nonce,
            **gas_params
        })
        
        print(f"{Fore.YELLOW}Signing transaction...{Style.RESET_ALL}")
        
        # Sign transaction
        signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
        
        print(f"{Fore.YELLOW}Sending transaction...{Style.RESET_ALL}")
        
        # Send raw transaction
        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        
        print(f"{Fore.GREEN}Mint transaction sent: {tx_hash.hex()}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}View on explorer: {EXPLORER_URL}/tx/{tx_hash.hex()}{Style.RESET_ALL}")
        
        print(f"{Fore.YELLOW}Waiting for transaction confirmation...{Style.RESET_ALL}")
        
        # Wait for transaction confirmation
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        if tx_receipt["status"] == 1:
            print(f"{Fore.GREEN}✓ Mint successful!{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}× Mint failed - Transaction reverted{Style.RESET_ALL}")
            return False
            
    except Exception as e:
        print(f"{Fore.RED}Error minting NFT: {str(e)}{Style.RESET_ALL}")
        return False

async def run():
    print(f"{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'MONADVERSE NFT MINTER':^60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}")

    # Connect to RPC with better error handling
    w3 = None
    connection_errors = []
    
    print(f"{Fore.CYAN}Attempting to connect to Monad Testnet...{Style.RESET_ALL}")
    for rpc_url in RPC_URLS:
        try:
            print(f"{Fore.YELLOW}Trying endpoint: {rpc_url}{Style.RESET_ALL}")
            provider = Web3.HTTPProvider(
                rpc_url,
                request_kwargs={
                    'timeout': 30,
                    'verify': rpc_url.startswith('https'),
                    'headers': {
                        'User-Agent': 'Mozilla/5.0',
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    }
                }
            )
            w3 = Web3(provider)
            
            if w3.is_connected():
                try:
                    chain_id = w3.eth.chain_id
                    print(f"{Fore.GREEN}Connected successfully! Chain ID: {chain_id}{Style.RESET_ALL}")
                    if chain_id == CHAIN_ID:
                        print(f"{Fore.GREEN}✓ Confirmed Monad Testnet{Style.RESET_ALL}")
                        break
                    else:
                        print(f"{Fore.RED}× Wrong network (expected {CHAIN_ID}, got {chain_id}){Style.RESET_ALL}")
                        continue
                except Exception as e:
                    print(f"{Fore.RED}Connected but failed to get chain ID: {str(e)}{Style.RESET_ALL}")
                    continue
        except Exception as e:
            error_msg = str(e)
            connection_errors.append(f"{rpc_url}: {error_msg}")
            print(f"{Fore.RED}Connection failed: {error_msg}{Style.RESET_ALL}")
            continue
    
    if not w3 or not w3.is_connected():
        print(f"{Fore.RED}Failed to connect to any RPC endpoints. Errors:{Style.RESET_ALL}")
        for error in connection_errors:
            print(f"{Fore.RED}- {error}{Style.RESET_ALL}")
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
    
    # Check current NFT balance
    current_balance = await get_nft_balance(w3, wallet_address)
    
    # Mint NFT
    success = await mint_nft(w3, w3.eth.contract(address=MONADVERSE_CONTRACT_ADDRESS, abi=ERC1155_ABI), wallet_address, private_key)
    
    if success:
        print(f"{Fore.GREEN}NFT minting process completed successfully!{Style.RESET_ALL}")
        # Check new balance after minting
        new_balance = await get_nft_balance(w3, wallet_address)
        if new_balance > current_balance:
            print(f"{Fore.GREEN}Successfully minted {new_balance - current_balance} new NFT(s)!{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}NFT minting process failed{Style.RESET_ALL}")
    
    return success

# Run the bot when executed directly
if __name__ == "__main__":
    asyncio.run(run()) 