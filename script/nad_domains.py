import requests
import time
import json
import random
import string
import asyncio
from web3 import Web3
from eth_account import Account
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# RPC URLs
RPC_URLS = [
    "https://testnet-rpc.monad.xyz",
    "https://testnet-rpc.monorail.xyz",
    "https://monad-testnet.drpc.org"
]

# Explorer URL
EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"

# NAD Domains contract address and API URL
NAD_CONTRACT_ADDRESS = "0x758D80767a751fc1634f579D76e1CcaAb3485c9c"
NAD_API_URL = "https://api.nad.domains/register/signature"
NAD_NFT_ADDRESS = "0x3019BF1dfB84E5b46Ca9D0eEC37dE08a59A41308"

# Contract ABIs
NAD_NFT_ABI = [
    {
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

NAD_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"name": "name", "type": "string"},
                    {"name": "nameOwner", "type": "address"},
                    {"name": "setAsPrimaryName", "type": "bool"},
                    {"name": "referrer", "type": "address"},
                    {"name": "discountKey", "type": "bytes32"},
                    {"name": "discountClaimProof", "type": "bytes"},
                    {"name": "nonce", "type": "uint256"},
                    {"name": "deadline", "type": "uint256"}
                ],
                "name": "params",
                "type": "tuple"
            },
            {"name": "signature", "type": "bytes"}
        ],
        "name": "registerWithSignature",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "components": [
                    {"name": "name", "type": "string"},
                    {"name": "nameOwner", "type": "address"},
                    {"name": "setAsPrimaryName", "type": "bool"},
                    {"name": "referrer", "type": "address"},
                    {"name": "discountKey", "type": "bytes32"},
                    {"name": "discountClaimProof", "type": "bytes"}
                ],
                "name": "params",
                "type": "tuple"
            }
        ],
        "name": "calculateRegisterFee",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
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

def generate_random_name(min_length=6, max_length=12):
    """Generate a random domain name"""
    # Choose a random length between min and max
    length = random.randint(min_length, max_length)
    
    # Generate random string with letters and numbers
    characters = string.ascii_lowercase + string.digits
    name = ''.join(random.choice(characters) for _ in range(length))
    
    # Ensure it starts with a letter
    if name[0].isdigit():
        name = random.choice(string.ascii_lowercase) + name[1:]
    
    return name

async def get_signature(session, wallet_address, name):
    """Get signature from API for domain registration"""
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9',
        'origin': 'https://app.nad.domains',
        'referer': 'https://app.nad.domains/',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
    }

    params = {
        'name': name,
        'nameOwner': wallet_address,
        'setAsPrimaryName': 'true',
        'referrer': '0x0000000000000000000000000000000000000000',
        'discountKey': '0x0000000000000000000000000000000000000000000000000000000000000000',
        'discountClaimProof': '0x0000000000000000000000000000000000000000000000000000000000000000',
        'chainId': '10143',
    }
    
    try:
        print(f"{Fore.CYAN}Checking availability of domain: {name}{Style.RESET_ALL}")
        
        response = await session.get(NAD_API_URL, params=params, headers=headers)
        
        if response.status_code != 200:
            print(f"{Fore.RED}API error: Status code {response.status_code}{Style.RESET_ALL}")
            return None
        
        data = response.json()
        if data.get('success'):
            print(f"{Fore.GREEN}Domain {name} is available{Style.RESET_ALL}")
            
            # Store the signature exactly as returned from API
            return {
                'signature': data['signature'],
                'nonce': int(data['nonce']),
                'deadline': int(data['deadline'])
            }
        else:
            print(f"{Fore.RED}API error: {data.get('message', 'Unknown error')}{Style.RESET_ALL}")
            return None
            
    except Exception as e:
        print(f"{Fore.RED}Error getting signature: {str(e)}{Style.RESET_ALL}")
        return None

async def is_name_available(session, wallet_address, name):
    """Check if domain name is available"""
    try:
        signature_data = await get_signature(session, wallet_address, name)
        return signature_data is not None
    except Exception as e:
        print(f"{Fore.RED}Error checking name availability: {str(e)}{Style.RESET_ALL}")
        return False

async def has_domain(w3, wallet_address):
    """Check if wallet already owns a NAD domain"""
    try:
        nft_contract = w3.eth.contract(address=NAD_NFT_ADDRESS, abi=NAD_NFT_ABI)
        balance = nft_contract.functions.balanceOf(wallet_address).call()
        
        if balance > 0:
            print(f"{Fore.GREEN}Wallet already owns {balance} NAD domain(s){Style.RESET_ALL}")
            return True
        return False
    except Exception as e:
        print(f"{Fore.RED}Error checking NAD domain balance: {str(e)}{Style.RESET_ALL}")
        return False

async def register_domain(w3, session, private_key, wallet_address, name, max_attempts=3):
    """Register a domain name using the NAD Domains smart contract"""
    for attempt in range(max_attempts):
        try:
            print(f"{Fore.CYAN}Registering domain: {name}{Style.RESET_ALL}")
            
            # Get signature from API
            signature_data = await get_signature(session, wallet_address, name)
            if not signature_data:
                print(f"{Fore.RED}Could not get signature for {name}{Style.RESET_ALL}")
                if attempt < max_attempts - 1:
                    continue
                else:
                    return False
            
            # Use fixed fee of 0.1 MON
            fee = w3.to_wei(0.1, 'ether')
            
            # Create contract instance
            contract = w3.eth.contract(address=NAD_CONTRACT_ADDRESS, abi=NAD_ABI)
            
            # Prepare register data
            register_data = [
                name,                                   # name
                wallet_address,                         # nameOwner
                True,                                   # setAsPrimaryName
                "0x0000000000000000000000000000000000000000",  # referrer
                "0x0000000000000000000000000000000000000000000000000000000000000000", # discountKey
                "0x0000000000000000000000000000000000000000000000000000000000000000", # discountClaimProof
                signature_data['nonce'],                # nonce
                signature_data['deadline']              # deadline
            ]
            
            # Pass the signature exactly as received from API
            signature = signature_data['signature']
            
            # Get gas parameters
            gas_params = await get_gas_params(w3)
            
            # Estimate gas for the transaction
            try:
                gas_estimate = contract.functions.registerWithSignature(
                    register_data,
                    signature
                ).estimate_gas({
                    'from': wallet_address,
                    'value': fee
                })
                # Add 20% buffer to gas estimate to ensure transaction doesn't run out of gas
                gas_with_buffer = int(gas_estimate * 1.2)
                print(f"{Fore.BLUE}Estimated gas: {gas_estimate}, with buffer: {gas_with_buffer}{Style.RESET_ALL}")
            except Exception as e:
                # If gas estimation fails, log error and return false
                print(f"{Fore.RED}Gas estimation failed: {str(e)}.{Style.RESET_ALL}")
                if attempt < max_attempts - 1:
                    continue
                else:
                    return False
            
            # Build the transaction
            transaction = contract.functions.registerWithSignature(
                register_data,
                signature
            ).build_transaction({
                'from': wallet_address,
                'value': fee,
                'gas': gas_with_buffer,
                'nonce': w3.eth.get_transaction_count(wallet_address),
                'chainId': 10143,
                'type': 2,
                **gas_params
            })
            
            # Sign the transaction
            signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
            
            # Send the transaction
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            print(f"{Fore.YELLOW}Registering {name} - Transaction sent: {tx_hash.hex()}{Style.RESET_ALL}")
            
            # Wait for transaction receipt
            print(f"{Fore.YELLOW}Waiting for transaction confirmation...{Style.RESET_ALL}")
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            success = receipt.status == 1
            
            if success:
                print(f"{Fore.GREEN}Successfully registered {name}!{Style.RESET_ALL}")
                print(f"{Fore.GREEN}View details at: {EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Failed to register {name}.{Style.RESET_ALL}")
                print(f"{Fore.RED}Transaction: {EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
            
            return success
        
        except Exception as e:
            print(f"{Fore.RED}Error registering {name}: {str(e)}{Style.RESET_ALL}")
            
            if attempt < max_attempts - 1:
                pause_time = random.randint(10, 30)
                print(f"{Fore.CYAN}Pausing for {pause_time} seconds before retry...{Style.RESET_ALL}")
                await asyncio.sleep(pause_time)
    
    print(f"{Fore.RED}Failed to register domain after {max_attempts} attempts{Style.RESET_ALL}")
    return False

async def register_random_domain(w3, session, private_key, wallet_address, max_attempts=3):
    """Register a random domain name with retry logic"""
    try:
        # First check if wallet already has a domain
        if await has_domain(w3, wallet_address):
            print(f"{Fore.GREEN}Wallet already has a NAD domain, skipping registration{Style.RESET_ALL}")
            return True
            
        # Continue with registration if no domain is owned
        for attempt in range(max_attempts):
            try:
                # Generate a random name
                name = generate_random_name()
                print(f"{Fore.CYAN}Generated random domain name: {name}{Style.RESET_ALL}")
                
                # Check if the name is available
                if await is_name_available(session, wallet_address, name):
                    print(f"{Fore.CYAN}Domain {name} is available, registering...{Style.RESET_ALL}")
                    
                    # Register the domain
                    success = await register_domain(w3, session, private_key, wallet_address, name)
                    return success
                else:
                    print(f"{Fore.YELLOW}Domain {name} is not available, trying another...{Style.RESET_ALL}")
                    continue
                
            except Exception as e:
                print(f"{Fore.RED}Error registering domain (attempt {attempt+1}/{max_attempts}): {str(e)}{Style.RESET_ALL}")
                
                if attempt < max_attempts - 1:
                    pause_time = random.randint(10, 30)
                    print(f"{Fore.CYAN}Pausing for {pause_time} seconds before retry...{Style.RESET_ALL}")
                    await asyncio.sleep(pause_time)
        
        return False
        
    except Exception as e:
        print(f"{Fore.RED}Error in register_random_domain: {str(e)}{Style.RESET_ALL}")
        return False

class AsyncSession:
    """Simple async session implementation"""
    async def get(self, url, **kwargs):
        try:
            response = requests.get(url, **kwargs)
            return response
        except Exception as e:
            print(f"{Fore.RED}Request error: {str(e)}{Style.RESET_ALL}")
            raise e

async def run():
    print(f"{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'NAD DOMAINS BOT':^60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}")

    # Create async session
    session = AsyncSession()

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

    # Check if we have enough balance for domain registration (0.1 MON + gas)
    if balance_eth < 0.13:
        print(f"{Fore.RED}Insufficient balance for domain registration. Need at least 0.13 MON.{Style.RESET_ALL}")
        return False
    
    # Register random domain
    success = await register_random_domain(w3, session, private_key, wallet_address)
    
    if success:
        print(f"{Fore.GREEN}Domain registration process completed successfully!{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}Domain registration process failed{Style.RESET_ALL}")
    
    return success

# Run the bot when executed directly
if __name__ == "__main__":
    asyncio.run(run()) 