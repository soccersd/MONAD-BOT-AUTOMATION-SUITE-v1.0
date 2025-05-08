import requests
import time
import json
import random
import asyncio
import platform
from web3 import Web3, AsyncWeb3
from eth_account import Account
from colorama import init, Fore, Style
from decimal import Decimal
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
CHAIN_ID = 10143  # Monad testnet

# ========== CONTRACT SETTINGS ==========
NARWHAL_CONTRACT = "0x7500a83df2af99b2755c47b6b321a8217d876a85"
USDT_CONTRACT = "0x924F1Bf31b19a7f9695F3FC6c69C2BA668Ea4a0a"

# ========== TOKEN SETTINGS ==========
TOKEN_DECIMALS = 18
MIN_BALANCE = 0.01  # MON
MAX_BALANCE = 0.1   # MON

# ========== GAMBLING SETTINGS ==========
SLOTS_BET_AMOUNT = 0.001  # MON
COINFLIP_BET_AMOUNT = 0.001  # MON
DICE_BET_AMOUNT = 0.001  # MON
MAX_ATTEMPTS = 3
PAUSE_BETWEEN_ATTEMPTS = (5, 15)

# ========== CONTRACT ABIs ==========
NARWHAL_ABI = [
    {
        "inputs": [],
        "name": "playSlots",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "playCoinflip",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "playDice",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    }
]

USDT_ABI = [
    {
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Contract addresses
USDT_ADDRESS = "0x6593F49Ca8D3038cA002314C187b63dD348c2F94"
USDT_FAUCET_ADDRESS = "0xFF85587E991E16bcB9a6A0C52ff919305944f011"
SLOTS_ADDRESS = "0x5939199FC366f741c5f4981BF343aC5A3ddf748d"  
COINFLIP_ADDRESS = "0x5c1C68a709427Cfdb184399304251658f91d4ea8"
DICE_ADDRESS = "0xc552a88f2FAB0b7800F2F54141ACe8C4C06f50A2"

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

async def estimate_gas(w3, transaction):
    """Estimate gas for transaction and add some buffer"""
    try:
        estimated = w3.eth.estimate_gas(transaction)
        # Add 10% to estimated gas for safety
        return int(estimated * 1.1)
    except Exception as e:
        print(f"{Fore.RED}Error estimating gas: {e}. Using default gas limit{Style.RESET_ALL}")
        return 100000

async def call_faucet(w3, private_key, wallet_address, token_address, max_attempts=3):
    """Call faucet to get test tokens"""
    for attempt in range(max_attempts):
        try:
            print(f"{Fore.CYAN}Calling faucet for {token_address}...{Style.RESET_ALL}")
            
            # Create faucet contract instance
            faucet_contract = w3.eth.contract(address=USDT_FAUCET_ADDRESS, abi=USDT_ABI)
            
            # Build faucet transaction
            transaction = faucet_contract.functions.mint().build_transaction({
                "from": wallet_address,
                "nonce": w3.eth.get_transaction_count(wallet_address),
                "gasPrice": w3.eth.gas_price,
                "chainId": CHAIN_ID
            })
            
            # Estimate gas
            try:
                gas_estimate = w3.eth.estimate_gas(transaction)
                transaction["gas"] = int(gas_estimate * 1.1)  # Add 10% buffer
                print(f"{Fore.BLUE}Estimated gas: {gas_estimate}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.YELLOW}Error estimating gas: {str(e)}. Using default gas limit.{Style.RESET_ALL}")
                transaction["gas"] = 300000  # Default gas limit
            
            # Sign and send transaction
            signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            print(f"{Fore.YELLOW}Waiting for faucet transaction confirmation...{Style.RESET_ALL}")
            
            # Wait for confirmation
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            
            if receipt.status == 1:
                print(f"{Fore.GREEN}Successfully called faucet!{Style.RESET_ALL}")
                print(f"{Fore.GREEN}View details at: {EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.RED}Faucet call failed: {receipt}{Style.RESET_ALL}")
                
                if attempt < max_attempts - 1:
                    pause_time = random.randint(10, 30)
                    print(f"{Fore.CYAN}Pausing for {pause_time} seconds before retry...{Style.RESET_ALL}")
                    await asyncio.sleep(pause_time)
        
        except Exception as e:
            print(f"{Fore.RED}Error calling faucet: {str(e)}{Style.RESET_ALL}")
            
            if attempt < max_attempts - 1:
                pause_time = random.randint(10, 30)
                print(f"{Fore.CYAN}Pausing for {pause_time} seconds before retry...{Style.RESET_ALL}")
                await asyncio.sleep(pause_time)
    
    print(f"{Fore.RED}Failed to call faucet after {max_attempts} attempts{Style.RESET_ALL}")
    return False

async def approve_usdt(w3, private_key, wallet_address, spender, amount):
    """Approve a specified amount of USDT for a spender"""
    try:
        print(f"{Fore.CYAN}Approving {amount / (10**18)} USDT for spender {spender}{Style.RESET_ALL}")
        
        # Create contract instance
        usdt_contract = w3.eth.contract(address=USDT_ADDRESS, abi=USDT_ABI)
        
        # Convert amount to uint256
        amount_uint = int(amount)
        
        # Get gas parameters
        gas_params = await get_gas_params(w3)
        
        # Build the approval transaction
        transaction = usdt_contract.functions.approve(spender, amount_uint).build_transaction({
            "from": wallet_address,
            "chainId": CHAIN_ID,
            "nonce": w3.eth.get_transaction_count(wallet_address),
            **gas_params,
        })
        
        # Estimate gas
        estimated_gas = await estimate_gas(w3, transaction)
        transaction.update({"gas": estimated_gas})
        
        # Sign and send transaction
        signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        
        print(f"{Fore.YELLOW}Approval transaction sent: {tx_hash.hex()}{Style.RESET_ALL}")
        
        # Wait for transaction confirmation
        print(f"{Fore.YELLOW}Waiting for approval transaction confirmation...{Style.RESET_ALL}")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        
        print(f"{Fore.GREEN}Successfully approved {amount / (10**18)} USDT for spender {spender}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}View details at: {EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
        return True
        
    except Exception as e:
        print(f"{Fore.RED}Error in approval: {str(e)}{Style.RESET_ALL}")
        return False

async def play_slots(w3, private_key, wallet_address, max_attempts=3):
    """Play Slots game on Narwhal Finance"""
    for attempt in range(max_attempts):
        try:
            # Get random USDT amount for bet (1-5 USDT)
            usdt_amount = round(random.uniform(1, 5), 2) * (10**18)  # Convert to wei
            
            print(f"{Fore.CYAN}Playing Slots with {usdt_amount / (10**18)} USDT...{Style.RESET_ALL}")
            
            # First approve USDT spending
            approve_success = await approve_usdt(w3, private_key, wallet_address, SLOTS_ADDRESS, usdt_amount)
            if not approve_success:
                print(f"{Fore.RED}Failed to approve USDT for Slots{Style.RESET_ALL}")
                if attempt < max_attempts - 1:
                    continue
                else:
                    return False
            
            # Format amount to match the payload format (pad with zeros to 64 chars)
            amount_hex = hex(int(usdt_amount))[2:].zfill(64)
            
            # Construct the exact payload for Slots_Play
            payload = (
                "0xf26c05f2"  # Function signature for Slots_Play
                f"{amount_hex}"  # Amount (64 chars)
                "000000000000000000000000"  # Padding
                "6593f49ca8d3038ca002314c187b63dd348c2f94"  # USDT address
                "0000000000000000000000000000000000000000000000000000000000000001"  # numBets
                "000000000000000000000000ffffffffffffffffffffffffffffffffffffffff"  # stopGain
                "000000000000000000000000ffffffffffffffffffffffffffffffffffffffff"  # stopLoss
            )
            
            # Get gas parameters
            gas_params = await get_gas_params(w3)
            
            # Create transaction
            transaction = {
                "from": wallet_address,
                "to": SLOTS_ADDRESS,
                "value": 27000001350000001,  # Exact value in wei required by contract
                "nonce": w3.eth.get_transaction_count(wallet_address),
                "chainId": CHAIN_ID,
                "type": 2,
                "data": payload,
                **gas_params,
            }
            
            # Estimate gas
            try:
                gas_estimate = w3.eth.estimate_gas(transaction)
                transaction["gas"] = int(gas_estimate * 1.3)
            except Exception as e:
                print(f"{Fore.YELLOW}Error estimating gas: {str(e)}. Using default gas limit.{Style.RESET_ALL}")
                transaction["gas"] = 300000
            
            # Sign and send transaction
            signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            print(f"{Fore.YELLOW}Slots_Play transaction sent: {tx_hash.hex()}{Style.RESET_ALL}")
            
            # Wait for transaction confirmation
            print(f"{Fore.YELLOW}Waiting for Slots_Play transaction confirmation...{Style.RESET_ALL}")
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            
            print(f"{Fore.GREEN}Successfully played Slots with {usdt_amount / (10**18)} USDT{Style.RESET_ALL}")
            print(f"{Fore.GREEN}View details at: {EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}Error playing Slots: {str(e)}{Style.RESET_ALL}")
            
            if attempt < max_attempts - 1:
                pause_time = random.randint(10, 30)
                print(f"{Fore.CYAN}Pausing for {pause_time} seconds before retry...{Style.RESET_ALL}")
                await asyncio.sleep(pause_time)
    
    print(f"{Fore.RED}Failed to play Slots after {max_attempts} attempts{Style.RESET_ALL}")
    return False

async def play_coinflip(w3, private_key, wallet_address, max_attempts=3):
    """Play Coinflip game on Narwhal Finance"""
    for attempt in range(max_attempts):
        try:
            # Get random USDT amount for bet (1-5 USDT)
            usdt_amount = round(random.uniform(1, 5), 2) * (10**18)  # Convert to wei
            
            print(f"{Fore.CYAN}Playing Coinflip with {usdt_amount / (10**18)} USDT...{Style.RESET_ALL}")
            
            # First approve USDT spending
            approve_success = await approve_usdt(w3, private_key, wallet_address, COINFLIP_ADDRESS, usdt_amount)
            if not approve_success:
                print(f"{Fore.RED}Failed to approve USDT for Coinflip{Style.RESET_ALL}")
                if attempt < max_attempts - 1:
                    continue
                else:
                    return False
            
            # Format amount to match the payload format (pad with zeros to 64 chars)
            amount_hex = hex(int(usdt_amount))[2:].zfill(64)
            
            # Construct the payload for CoinFlip_Play
            payload = (
                "0x6d974773"  # Function signature for CoinFlip_Play
                f"{amount_hex}"  # Amount (64 chars)
                "000000000000000000000000"  # Padding
                "6593f49ca8d3038ca002314c187b63dd348c2f94"  # USDT address
                "0000000000000000000000000000000000000000000000000000000000000001"  # numBets
                "0000000000000000000000000000000000000000000000000000000000000001"  # betSide
                "000000000000000000000000ffffffffffffffffffffffffffffffffffffffff"  # stopGain
                "000000000000000000000000ffffffffffffffffffffffffffffffffffffffff"  # stopLoss
            )
            
            # Get gas parameters
            gas_params = await get_gas_params(w3)
            
            # Create transaction
            transaction = {
                "from": wallet_address,
                "to": COINFLIP_ADDRESS,
                "value": 27000001350000001,  # Exact value in wei required by contract
                "nonce": w3.eth.get_transaction_count(wallet_address),
                "chainId": CHAIN_ID,
                "type": 2,
                "data": payload,
                **gas_params,
            }
            
            # Estimate gas
            try:
                gas_estimate = w3.eth.estimate_gas(transaction)
                transaction["gas"] = int(gas_estimate * 1.3)
            except Exception as e:
                print(f"{Fore.YELLOW}Error estimating gas: {str(e)}. Using default gas limit.{Style.RESET_ALL}")
                transaction["gas"] = 300000
            
            # Sign and send transaction
            signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            print(f"{Fore.YELLOW}Coinflip_Play transaction sent: {tx_hash.hex()}{Style.RESET_ALL}")
            
            # Wait for transaction confirmation
            print(f"{Fore.YELLOW}Waiting for Coinflip_Play transaction confirmation...{Style.RESET_ALL}")
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            
            print(f"{Fore.GREEN}Successfully played Coinflip with {usdt_amount / (10**18)} USDT{Style.RESET_ALL}")
            print(f"{Fore.GREEN}View details at: {EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}Error playing Coinflip: {str(e)}{Style.RESET_ALL}")
            
            if attempt < max_attempts - 1:
                pause_time = random.randint(10, 30)
                print(f"{Fore.CYAN}Pausing for {pause_time} seconds before retry...{Style.RESET_ALL}")
                await asyncio.sleep(pause_time)
    
    print(f"{Fore.RED}Failed to play Coinflip after {max_attempts} attempts{Style.RESET_ALL}")
    return False

async def play_dice(w3, private_key, wallet_address, max_attempts=3):
    """Play Dice game on Narwhal Finance"""
    for attempt in range(max_attempts):
        try:
            # Get random USDT amount for bet (1-5 USDT)
            usdt_amount = round(random.uniform(1, 5), 2) * (10**18)  # Convert to wei
            
            # Generate random multiplier between 1.1 and 9 (with 0.01 precision)
            multiplier = round(random.uniform(1.1, 9), 2)
            
            print(f"{Fore.CYAN}Playing Dice with {usdt_amount / (10**18)} USDT and multiplier {multiplier}x...{Style.RESET_ALL}")
            
            # First approve USDT spending
            approve_success = await approve_usdt(w3, private_key, wallet_address, DICE_ADDRESS, usdt_amount)
            if not approve_success:
                print(f"{Fore.RED}Failed to approve USDT for Dice{Style.RESET_ALL}")
                if attempt < max_attempts - 1:
                    continue
                else:
                    return False
            
            # Convert multiplier to the format needed (multiply by 10000 and convert to hex)
            multiplier_int = int(multiplier * 10000)
            multiplier_hex = format(multiplier_int, "x").zfill(64)
            
            # Format amount to match the payload format (pad with zeros to 64 chars)
            amount_hex = format(int(usdt_amount), "x").zfill(64)
            
            # Construct the payload for Dice_Play
            payload = (
                "0x74af2e59"  # Function signature for Dice_Play
                f"{amount_hex}"  # Amount (64 chars)
                f"{multiplier_hex}"  # Prediction number (multiplier)
                "0000000000000000000000006593f49ca8d3038ca002314c187b63dd348c2f94"  # USDT address
                "0000000000000000000000000000000000000000000000000000000000000001"  # numBets
                "0000000000000000000000000000000000000000000000000000000000000001"  # betType
                "000000000000000000000000ffffffffffffffffffffffffffffffffffffffff"  # stopGain
                "000000000000000000000000ffffffffffffffffffffffffffffffffffffffff"  # stopLoss
            )
            
            # Get gas parameters
            gas_params = await get_gas_params(w3)
            
            # Create transaction
            transaction = {
                "from": wallet_address,
                "to": DICE_ADDRESS,
                "value": 27000001350000001,  # Exact value in wei required by contract
                "nonce": w3.eth.get_transaction_count(wallet_address),
                "chainId": CHAIN_ID,
                "type": 2,
                "data": payload,
                **gas_params,
            }
            
            # Estimate gas
            try:
                gas_estimate = w3.eth.estimate_gas(transaction)
                transaction["gas"] = int(gas_estimate * 1.3)
            except Exception as e:
                print(f"{Fore.YELLOW}Error estimating gas: {str(e)}. Using default gas limit.{Style.RESET_ALL}")
                transaction["gas"] = 300000
            
            # Sign and send transaction
            signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            print(f"{Fore.YELLOW}Dice_Play transaction sent: {tx_hash.hex()}{Style.RESET_ALL}")
            
            # Wait for transaction confirmation
            print(f"{Fore.YELLOW}Waiting for Dice_Play transaction confirmation...{Style.RESET_ALL}")
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            
            print(f"{Fore.GREEN}Successfully played Dice with {usdt_amount / (10**18)} USDT and multiplier {multiplier}x{Style.RESET_ALL}")
            print(f"{Fore.GREEN}View details at: {EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}Error playing Dice: {str(e)}{Style.RESET_ALL}")
            
            if attempt < max_attempts - 1:
                pause_time = random.randint(10, 30)
                print(f"{Fore.CYAN}Pausing for {pause_time} seconds before retry...{Style.RESET_ALL}")
                await asyncio.sleep(pause_time)
    
    print(f"{Fore.RED}Failed to play Dice after {max_attempts} attempts{Style.RESET_ALL}")
    return False

async def gamble(w3, private_key, wallet_address):
    """Play a random selection of games on Narwhal Finance"""
    try:
        # Number of games to play in this session (1-3)
        num_games = random.randint(1, 3)
        
        print(f"{Fore.CYAN}Starting gambling session with {num_games} games...{Style.RESET_ALL}")
        
        # List of game functions to choose from
        games = [
            (play_slots, "Slots"),
            (play_coinflip, "Coinflip"),
            (play_dice, "Dice")
        ]
        
        # Shuffle the games for random selection
        random.shuffle(games)
        
        # Play the selected number of games
        for i in range(min(num_games, len(games))):
            game_func, game_name = games[i]
            
            print(f"{Fore.CYAN}Playing game {i+1}/{num_games}: {game_name}{Style.RESET_ALL}")
            success = await game_func(w3, private_key, wallet_address)
            
            if not success:
                print(f"{Fore.RED}Failed to play {game_name}. Stopping gambling session.{Style.RESET_ALL}")
                return False
            
            # Add a random pause between games if there are more games to play
            if i < min(num_games, len(games)) - 1:
                pause_time = random.randint(5, 15)
                print(f"{Fore.CYAN}Pausing for {pause_time} seconds before next game...{Style.RESET_ALL}")
                await asyncio.sleep(pause_time)
        
        print(f"{Fore.GREEN}Successfully completed gambling session!{Style.RESET_ALL}")
        return True
        
    except Exception as e:
        print(f"{Fore.RED}Error in gambling session: {str(e)}{Style.RESET_ALL}")
        return False

async def get_token_balance(w3, token_address, wallet_address):
    """Get token balance for the account"""
    try:
        contract = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=USDT_ABI)
        balance = contract.functions.balanceOf(wallet_address).call()
        return balance, Decimal(str(balance)) / Decimal('1000000000000000000')  # Assuming 18 decimals
    except Exception as e:
        print(f"{Fore.RED}Error getting token balance: {str(e)}{Style.RESET_ALL}")
        return 0, Decimal('0')

async def run():
    print(f"{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'NARWHAL FINANCE BOT':^60}{Style.RESET_ALL}")
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

    # Check if we have enough balance for transactions
    if balance_eth < 0.03:
        print(f"{Fore.RED}Insufficient balance to play games. Need at least 0.03 MON.{Style.RESET_ALL}")
        return False
    
    # Check USDT balance
    usdt_balance, usdt_balance_formatted = await get_token_balance(w3, USDT_ADDRESS, wallet_address)
    print(f"USDT Balance: {usdt_balance_formatted} USDT")
    
    # Get USDT from faucet if needed
    if usdt_balance_formatted < 1:  # If less than 1 USDT
        print(f"{Fore.CYAN}Getting USDT from faucet...{Style.RESET_ALL}")
        faucet_success = await call_faucet(w3, private_key, wallet_address, USDT_FAUCET_ADDRESS)
        if not faucet_success:
            print(f"{Fore.RED}Failed to get USDT from faucet. Cannot proceed without USDT.{Style.RESET_ALL}")
            return False
        
        # Wait for faucet transaction to be confirmed
        print(f"{Fore.CYAN}Waiting for faucet transaction to be confirmed...{Style.RESET_ALL}")
        await asyncio.sleep(30)
        
        # Check new USDT balance
        usdt_balance, usdt_balance_formatted = await get_token_balance(w3, USDT_ADDRESS, wallet_address)
        print(f"New USDT Balance: {usdt_balance_formatted} USDT")
    
    if usdt_balance_formatted < 1:
        print(f"{Fore.RED}Insufficient USDT balance. Need at least 1 USDT.{Style.RESET_ALL}")
        return False
    
    # Play games
    await gamble(w3, private_key, wallet_address)
    
    return True

# Run the bot when executed directly
if __name__ == "__main__":
    asyncio.run(run()) 