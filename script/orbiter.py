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

# URLs and contract addresses
SEPOLIA_RPC_URL = "https://sepolia.drpc.org/"
SEPOLIA_EXPLORER_URL = "https://sepolia.etherscan.io/tx/0x"
MONAD_RPC_URLS = [
    "https://testnet-rpc.monad.xyz",
    "https://testnet-rpc.monorail.xyz",
    "https://monad-testnet.drpc.org"
]
MONAD_EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"

# Orbiter addresses
ORBITER_SEPOLIA_ADDRESS = "0xB5AADef97d81A77664fcc3f16Bfe328ad6CEc7ac"
MONAD_SEPOLIA_TOKEN_ADDRESS = "0x836047a99e11F376522B447bffb6e3495Dd0637c"

# ERC20 ABI for checking token balances
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
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
    """Get EIP-1559 gas parameters from the network"""
    try:
        latest_block = await w3.eth.get_block("latest")
        base_fee = latest_block["baseFeePerGas"]
        max_priority_fee = await w3.eth.max_priority_fee
        
        # Multiply both fees by 1.5 for faster confirmation
        max_priority_fee = int(max_priority_fee * 1.5)
        max_fee = int((base_fee + max_priority_fee) * 1.5)
        
        return {
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": max_priority_fee,
        }
    except Exception as e:
        print(f"{Fore.YELLOW}Error getting EIP-1559 gas params: {str(e)}. Using legacy gas pricing.{Style.RESET_ALL}")
        return None

async def wait_for_funds(monad_w3, wallet_address, initial_balance, max_wait_time=600):
    """Wait for funds to arrive in Monad network after bridging"""
    try:
        # Create token contract instance
        token_contract = monad_w3.eth.contract(
            address=monad_w3.to_checksum_address(MONAD_SEPOLIA_TOKEN_ADDRESS),
            abi=ERC20_ABI
        )
        
        # Check balance every 10 seconds
        max_attempts = max_wait_time // 10
        print(f"{Fore.CYAN}Waiting for funds to arrive in Monad (max wait time: {max_wait_time} seconds)...{Style.RESET_ALL}")
        
        for attempt in range(max_attempts):
            try:
                current_balance = token_contract.functions.balanceOf(wallet_address).call()
                
                if current_balance > initial_balance:
                    print(f"{Fore.GREEN}Funds arrived in Monad! New balance: {current_balance / 10**18} ETH{Style.RESET_ALL}")
                    return True
                
                seconds_remaining = (max_attempts - attempt) * 10
                print(f"{Fore.BLUE}Still waiting for funds... (attempt {attempt + 1}/{max_attempts}, {seconds_remaining} seconds remaining){Style.RESET_ALL}")
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                print(f"{Fore.RED}Error checking token balance: {str(e)}{Style.RESET_ALL}")
                await asyncio.sleep(10)
                
        print(f"{Fore.RED}Timeout waiting for funds after {max_wait_time} seconds{Style.RESET_ALL}")
        return False
        
    except Exception as e:
        print(f"{Fore.RED}Error in wait_for_funds: {str(e)}{Style.RESET_ALL}")
        return False

async def bridge_to_monad(sepolia_w3, monad_w3, private_key, wallet_address, max_attempts=3):
    """Bridge ETH from Sepolia to Monad via Orbiter"""
    for attempt in range(max_attempts):
        try:
            print(f"{Fore.CYAN}Initiating bridge from Sepolia to Monad...{Style.RESET_ALL}")
            
            # Get initial balance on Monad
            token_contract = monad_w3.eth.contract(
                address=monad_w3.to_checksum_address(MONAD_SEPOLIA_TOKEN_ADDRESS),
                abi=ERC20_ABI
            )
            
            initial_monad_balance = token_contract.functions.balanceOf(wallet_address).call()
            print(f"{Fore.BLUE}Initial Monad-Sepolia token balance: {initial_monad_balance / 10**18} ETH{Style.RESET_ALL}")
            
            # Get current balance in Wei
            balance_wei = sepolia_w3.eth.get_balance(wallet_address)
            balance_eth = sepolia_w3.from_wei(balance_wei, 'ether')
            print(f"{Fore.BLUE}Sepolia ETH balance: {balance_eth} ETH{Style.RESET_ALL}")
            
            # Get gas parameters for fee estimation
            gas_params = await get_gas_params(sepolia_w3)
            
            if not gas_params:
                # Fallback to legacy gas pricing
                gas_price = sepolia_w3.eth.gas_price
                gas_cost_wei = gas_price * 21000
                transaction_type = 0
            else:
                gas_cost_wei = gas_params['maxFeePerGas'] * 21000
                transaction_type = 2
            
            # Determine amount to bridge (leave some for gas)
            gas_cost_with_buffer = int(gas_cost_wei * 1.1)  # Add 10% buffer
            
            if balance_wei <= gas_cost_with_buffer:
                print(f"{Fore.RED}Balance too low to cover gas costs. Need at least {sepolia_w3.from_wei(gas_cost_with_buffer, 'ether')} ETH{Style.RESET_ALL}")
                return False
                
            # Bridge 80-90% of balance
            percentage = random.uniform(0.8, 0.9)
            available_wei = balance_wei - gas_cost_with_buffer
            amount_wei = int(available_wei * percentage)
            
            # Convert to ETH string
            base_amount = sepolia_w3.from_wei(amount_wei, 'ether')
            
            # Format with random precision between 5-12 decimals
            precision = random.randint(5, 12)
            amount_str = f"{base_amount:.{precision}f}"
            
            # Ensure exactly 14 decimal places + 9596 (Orbiter identifier for Monad)
            if '.' not in amount_str:
                amount_str += '.'
            whole, decimal = amount_str.split('.')
            # Pad with zeros to get exactly 14 decimal places
            decimal = (decimal + '0' * 14)[:14]
            formatted_amount = f"{whole}.{decimal}9596"
            
            # Convert back to Wei
            amount_wei = sepolia_w3.to_wei(formatted_amount, 'ether')
            print(f"{Fore.CYAN}Bridging amount: {formatted_amount} ETH{Style.RESET_ALL}")
            
            # Prepare transaction
            transaction = {
                'from': wallet_address,
                'to': ORBITER_SEPOLIA_ADDRESS,
                'value': amount_wei,
                'nonce': sepolia_w3.eth.get_transaction_count(wallet_address),
                'chainId': 11155111,  # Sepolia chain ID
                'gas': 21000,  # Simple ETH transfer gas limit
            }
            
            # Add appropriate gas parameters
            if transaction_type == 2:
                transaction.update({
                    'type': 2,
                    'maxFeePerGas': gas_params['maxFeePerGas'],
                    'maxPriorityFeePerGas': gas_params['maxPriorityFeePerGas'],
                })
            else:
                transaction.update({
                    'gasPrice': int(sepolia_w3.eth.gas_price * 1.1),  # Add 10% buffer
                })
            
            # Sign and send transaction
            signed_txn = sepolia_w3.eth.account.sign_transaction(transaction, private_key)
            tx_hash = sepolia_w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            print(f"{Fore.YELLOW}Bridge transaction sent: {tx_hash.hex()}{Style.RESET_ALL}")
            
            # Wait for confirmation
            print(f"{Fore.YELLOW}Waiting for bridge transaction confirmation...{Style.RESET_ALL}")
            receipt = sepolia_w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            
            if receipt.status == 1:
                print(f"{Fore.GREEN}Successfully initiated bridge to Monad!{Style.RESET_ALL}")
                print(f"{Fore.GREEN}View details at: {SEPOLIA_EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
                
                # Wait for funds to arrive in Monad
                wait_success = await wait_for_funds(monad_w3, wallet_address, initial_monad_balance)
                return wait_success
            else:
                print(f"{Fore.RED}Bridge transaction failed: {receipt}{Style.RESET_ALL}")
                
                if attempt < max_attempts - 1:
                    pause_time = random.randint(10, 30)
                    print(f"{Fore.CYAN}Pausing for {pause_time} seconds before retry...{Style.RESET_ALL}")
                    await asyncio.sleep(pause_time)
        
        except Exception as e:
            print(f"{Fore.RED}Error bridging to Monad: {str(e)}{Style.RESET_ALL}")
            
            if "insufficient funds" in str(e).lower():
                print(f"{Fore.RED}Insufficient funds to cover bridge and gas costs{Style.RESET_ALL}")
                return False
                
            if attempt < max_attempts - 1:
                pause_time = random.randint(10, 30)
                print(f"{Fore.CYAN}Pausing for {pause_time} seconds before retry...{Style.RESET_ALL}")
                await asyncio.sleep(pause_time)
    
    print(f"{Fore.RED}Failed to bridge to Monad after {max_attempts} attempts{Style.RESET_ALL}")
    return False

async def run():
    print(f"{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'ORBITER BRIDGE BOT (SEPOLIA -> MONAD)':^60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}")

    # Connect to Sepolia RPC
    sepolia_w3 = None
    try:
        print(f"{Fore.CYAN}Connecting to Sepolia network...{Style.RESET_ALL}")
        sepolia_w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL, request_kwargs={'timeout': 30}))
        
        if sepolia_w3.is_connected():
            print(f"{Fore.GREEN}Successfully connected to Sepolia network{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Cannot connect to Sepolia network{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"{Fore.RED}Error connecting to Sepolia: {str(e)}{Style.RESET_ALL}")
        return False

    # Connect to Monad RPC
    monad_w3 = None
    for rpc_url in MONAD_RPC_URLS:
        try:
            monad_w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 10}))
            if monad_w3.is_connected():
                print(f"{Fore.GREEN}Successfully connected to Monad network: {rpc_url}{Style.RESET_ALL}")
                break
        except Exception as e:
            print(f"{Fore.RED}Cannot connect to Monad RPC {rpc_url}: {str(e)}{Style.RESET_ALL}")
    
    if not monad_w3:
        print(f"{Fore.RED}Cannot connect to any Monad RPC{Style.RESET_ALL}")
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

    # Check Sepolia balance
    sepolia_balance = sepolia_w3.eth.get_balance(wallet_address)
    sepolia_balance_eth = sepolia_w3.from_wei(sepolia_balance, 'ether')
    print(f"{Fore.BLUE}Sepolia ETH Balance: {sepolia_balance_eth} ETH{Style.RESET_ALL}")

    # Check if we have enough balance on Sepolia
    if sepolia_balance_eth < 0.001:
        print(f"{Fore.RED}Insufficient balance on Sepolia to bridge. Need at least 0.001 ETH{Style.RESET_ALL}")
        return False
    
    # Bridge to Monad
    bridge_success = await bridge_to_monad(sepolia_w3, monad_w3, private_key, wallet_address)
    
    if bridge_success:
        print(f"{Fore.GREEN}Successfully bridged funds from Sepolia to Monad{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}Failed to bridge funds from Sepolia to Monad{Style.RESET_ALL}")
    
    return bridge_success

# Run the bot when executed directly
if __name__ == "__main__":
    asyncio.run(run()) 