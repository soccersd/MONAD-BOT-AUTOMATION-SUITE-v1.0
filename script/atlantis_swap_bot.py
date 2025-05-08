import requests
from colorama import init, Fore, Style
from web3 import Web3
from eth_account import Account
import time
import os
import asyncio
import random

# Initialize colorama
init(autoreset=True)

# RPC URLs
RPC_URLS = [
    "https://testnet-rpc.monad.xyz",
    "https://testnet-rpc.monorail.xyz",
    "https://monad-testnet.drpc.org"
]

# Contract addresses and constants
atl_address = "0x1eA9099E3026e0b3F8Dd6FbacAa45f30fCe67431"  # ATL token address
EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"

# API headers
headers = {
    "x-atlantis-api-key": "Z7jM2WR4EuTHK9vyUDxY3ntX8Qgd6eNAFPsLSfBp",
    "Accept": "application/json"
}

# API taker address
taker_address = "0x18224a5bD5e270732CAF81570e8653572e7FFf25"

# ฟังก์ชันอ่าน private key จากไฟล์
def read_private_key(file_path='pvkey.txt'):
    try:
        # ลองอ่านไฟล์ด้วย encoding ต่างๆ
        encodings = ['utf-8', 'latin-1', 'cp1252', 'utf-16']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    for line in file:
                        # ข้ามบรรทัดที่เป็นคอมเมนต์
                        if line.strip().startswith('#') or not line.strip():
                            continue
                        
                        # ลบ whitespace และตรวจสอบรูปแบบ
                        private_key = line.strip()
                        
                        # ลบ 0x นำหน้าออก (จะเติมกลับในภายหลัง)
                        if private_key.startswith('0x'):
                            private_key = private_key[2:]
                        
                        # ตรวจสอบความยาว
                        if len(private_key) != 64:
                            print(f"{Fore.YELLOW}คำเตือน: private key ไม่ถูกต้อง (ความยาวไม่ถูกต้อง){Style.RESET_ALL}")
                            continue
                        
                        # ตรวจสอบว่าเป็น hex string
                        try:
                            int(private_key, 16)
                            print(f"{Fore.GREEN}พบ private key ที่ถูกต้องในไฟล์{Style.RESET_ALL}")
                            return '0x' + private_key  # เติม 0x นำหน้า
                        except ValueError:
                            print(f"{Fore.YELLOW}คำเตือน: พบตัวอักษรที่ไม่ใช่เลขฐานสิบหก (0-9, a-f){Style.RESET_ALL}")
                            continue
                
                # ถ้าไม่พบ private key ที่ถูกต้องใน encoding นี้ ให้ลองต่อไป
            except UnicodeDecodeError:
                continue  # ลอง encoding ถัดไป
    
    except FileNotFoundError:
        print(f"{Fore.RED}ไม่พบไฟล์ {file_path}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}เกิดข้อผิดพลาดในการอ่านไฟล์: {str(e)}{Style.RESET_ALL}")
    
    print(f"{Fore.RED}ไม่พบ private key ที่ถูกต้องในไฟล์ {file_path}{Style.RESET_ALL}")
    return None

async def get_gas_params(w3):
    """Get current gas parameters from the network"""
    try:
        latest_block = w3.eth.get_block("latest")
        base_fee = latest_block["baseFeePerGas"]
        max_priority_fee = w3.eth.max_priority_fee

        # Calculate maxFeePerGas (base fee + priority fee)
        max_fee = base_fee + max_priority_fee

        return {
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": max_priority_fee,
        }
    except Exception as e:
        print(f"{Fore.YELLOW}Error getting EIP-1559 gas params: {str(e)}. Using legacy gas pricing.{Style.RESET_ALL}")
        return None

async def run():
    print(f"{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'ATLANTIS SWAP BOT':^60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}")

    # Connect to Monad RPC
    w3 = None
    for rpc_url in RPC_URLS:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 10}))
            if w3.is_connected():
                print(f"{Fore.GREEN}Successfully connected to Monad network: {rpc_url}{Style.RESET_ALL}")
                break
        except Exception as e:
            print(f"{Fore.RED}Cannot connect to Monad RPC {rpc_url}: {str(e)}{Style.RESET_ALL}")
    
    if not w3:
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

    # Get current balance
    balance_wei = w3.eth.get_balance(wallet_address)
    balance_eth = float(w3.from_wei(balance_wei, 'ether'))  # Convert to float
    print(f"{Fore.BLUE}Current MON balance: {balance_eth} MON{Style.RESET_ALL}")

    # Get gas parameters
    try:
        gas_params = await get_gas_params(w3)
        if not gas_params:
            gas_price = w3.eth.gas_price
            gas_params = {"gasPrice": int(gas_price * 1.1)}
    except:
        gas_price = w3.eth.gas_price
        gas_params = {"gasPrice": int(gas_price * 1.1)}

    # Calculate gas cost
    if "gasPrice" in gas_params:
        gas_cost = gas_params["gasPrice"] * 200000  # Standard gas limit for swap
    else:
        gas_cost = gas_params["maxFeePerGas"] * 200000
        
    gas_cost_eth = float(w3.from_wei(gas_cost, 'ether'))  # Convert to float
    
    # Calculate available balance after gas
    available_balance = balance_eth - gas_cost_eth
    
    if available_balance <= 0:
        print(f"{Fore.RED}Insufficient balance to cover gas costs{Style.RESET_ALL}")
        return False
        
    # Calculate optimal swap amount (80-90% of available balance)
    swap_percentage = random.uniform(0.8, 0.9)
    swap_amount_eth = available_balance * swap_percentage
    
    # Ensure minimum swap amount
    if swap_amount_eth < 0.001:
        print(f"{Fore.RED}Swap amount too low: {swap_amount_eth} MON{Style.RESET_ALL}")
        return False
        
    swap_amount_wei = w3.to_wei(swap_amount_eth, 'ether')
    print(f"{Fore.CYAN}Swap amount: {swap_amount_eth} MON{Style.RESET_ALL}")

    # Create URL for API with user's wallet address
    url = f"https://api.atlantisdex.xyz/api/Ox/swap/quote?chainId=10143&sellToken=0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee&buyToken={atl_address}&sellAmount={swap_amount_wei}&taker={wallet_address}&slippageBps=50"
    print(f"{Fore.CYAN}Using native MON to buy ATL token...{Style.RESET_ALL}")

    # Send GET request to get quote
    try:
        await asyncio.sleep(1)  # Delay to avoid rate limit
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            quote_data = response.json()
            print(f"{Fore.GREEN}Successfully got quote from Atlantis DEX{Style.RESET_ALL}")
            
            # Debug response structure
            print(f"{Fore.CYAN}Response structure:{Style.RESET_ALL}")
            for key in quote_data.keys():
                print(f"{Fore.CYAN}Key: {key}{Style.RESET_ALL}")
            
            # Check if 'to' is in transaction object
            if 'transaction' in quote_data:
                tx_data = quote_data['transaction']
                print(f"{Fore.CYAN}Transaction keys: {list(tx_data.keys())}{Style.RESET_ALL}")
            
            # Create transaction
            try:
                # Check if wallet is same as taker
                if wallet_address.lower() != taker_address.lower():
                    print(f"{Fore.YELLOW}Warning: Your account address ({wallet_address}) doesn't match the taker in API ({taker_address}){Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}Updating URL to use your account...{Style.RESET_ALL}")
                    
                    # Create new URL with your wallet address
                    new_url = f"https://api.atlantisdex.xyz/api/Ox/swap/quote?chainId=10143&sellToken=0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee&buyToken={atl_address}&sellAmount={swap_amount_wei}&taker={wallet_address}&slippageBps=50"
                    
                    print(f"{Fore.CYAN}Getting new quote with your account...{Style.RESET_ALL}")
                    await asyncio.sleep(2)  # Wait to avoid rate limit
                    
                    response = requests.get(new_url, headers=headers)
                    if response.status_code != 200:
                        print(f"{Fore.RED}Failed to get quote with your account{Style.RESET_ALL}")
                        return False
                    quote_data = response.json()
                    
                    # Debug updated response
                    print(f"{Fore.CYAN}Updated response structure:{Style.RESET_ALL}")
                    for key in quote_data.keys():
                        print(f"{Fore.CYAN}Key: {key}{Style.RESET_ALL}")
                    
                    if 'transaction' in quote_data:
                        tx_data = quote_data['transaction']
                        print(f"{Fore.CYAN}Transaction keys: {list(tx_data.keys())}{Style.RESET_ALL}")
                
                # Use correct structure to access fields
                if 'transaction' in quote_data and 'to' in quote_data['transaction']:
                    # Print out raw types to debug
                    print(f"{Fore.CYAN}Gas type: {type(quote_data['transaction']['gas'])}, Value: {quote_data['transaction']['gas']}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}To address: {quote_data['transaction']['to']}{Style.RESET_ALL}")
                    
                    # Ensure gas is treated as integer
                    try:
                        gas_value = int(quote_data['transaction']['gas'])
                        # Add 20% buffer to gas (as integer)
                        gas_with_buffer = int(gas_value * 1.2)
                    except (ValueError, TypeError):
                        # If gas can't be converted to int, use default
                        print(f"{Fore.YELLOW}Could not convert gas to integer, using default value{Style.RESET_ALL}")
                        gas_with_buffer = 300000
                    
                    # Ensure the 'to' address is properly checksummed
                    try:
                        to_address = w3.to_checksum_address(quote_data['transaction']['to'])
                    except:
                        print(f"{Fore.RED}Invalid 'to' address from API: {quote_data['transaction']['to']}{Style.RESET_ALL}")
                        return False
                    
                    tx = {
                        'from': wallet_address,
                        'to': to_address,
                        'value': int(quote_data['transaction']['value']),
                        'data': quote_data['transaction']['data'],
                        'nonce': w3.eth.get_transaction_count(wallet_address),
                        'chainId': 10143,  # Monad testnet
                        'gas': gas_with_buffer,
                        **gas_params
                    }
                elif 'to' in quote_data:
                    # Print out raw types to debug
                    print(f"{Fore.CYAN}Gas type: {type(quote_data.get('gas', 'not found'))}, Value: {quote_data.get('gas', 'not found')}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}To address: {quote_data['to']}{Style.RESET_ALL}")
                    
                    # Ensure gas is treated as integer
                    try:
                        if 'gas' in quote_data:
                            gas_value = int(quote_data['gas'])
                            # Add 20% buffer to gas (as integer)
                            gas_with_buffer = int(gas_value * 1.2)
                        else:
                            gas_with_buffer = 300000
                    except (ValueError, TypeError):
                        # If gas can't be converted to int, use default
                        print(f"{Fore.YELLOW}Could not convert gas to integer, using default value{Style.RESET_ALL}")
                        gas_with_buffer = 300000
                    
                    # Ensure the 'to' address is properly checksummed
                    try:
                        to_address = w3.to_checksum_address(quote_data['to'])
                    except:
                        print(f"{Fore.RED}Invalid 'to' address from API: {quote_data['to']}{Style.RESET_ALL}")
                        return False
                    
                    tx = {
                        'from': wallet_address,
                        'to': to_address,
                        'value': int(quote_data['value']),
                        'data': quote_data['data'],
                        'nonce': w3.eth.get_transaction_count(wallet_address),
                        'chainId': 10143,  # Monad testnet
                        'gas': gas_with_buffer,
                        **gas_params
                    }
                else:
                    print(f"{Fore.RED}Error: Cannot find required transaction fields in API response{Style.RESET_ALL}")
                    return False
                
                # Sign and send transaction
                signed_tx = w3.eth.account.sign_transaction(tx, private_key)
                tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                
                print(f"{Fore.YELLOW}Swap transaction sent: {tx_hash.hex()}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}View on explorer: {EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
                
                # Wait for confirmation
                print(f"{Fore.YELLOW}Waiting for transaction confirmation...{Style.RESET_ALL}")
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
                
                if receipt.status == 1:
                    print(f"{Fore.GREEN}Swap transaction successful!{Style.RESET_ALL}")
                    return True
                else:
                    print(f"{Fore.RED}Swap transaction failed: {receipt}{Style.RESET_ALL}")
                    return False
                    
            except Exception as e:
                print(f"{Fore.RED}Error creating transaction: {str(e)}{Style.RESET_ALL}")
                return False
        else:
            print(f"{Fore.RED}Failed to get quote from Atlantis DEX: {response.text}{Style.RESET_ALL}")
            return False
            
    except Exception as e:
        print(f"{Fore.RED}Error getting quote: {str(e)}{Style.RESET_ALL}")
        return False

# ทำการรันโปรแกรมเมื่อเรียกใช้โดยตรง
if __name__ == "__main__":
    asyncio.run(run())