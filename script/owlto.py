import asyncio
import sys

# ตั้งค่า SelectorEventLoop สำหรับ Windows
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# นำเข้าโมดูลอื่น ๆ ต่อจากนี้
import requests
import time
import json
import random
from colorama import init, Fore, Style
from web3 import Web3, AsyncWeb3
from eth_account import Account
import os

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

# Contract bytecode
DEPLOY_CONTRACT_BYTECODE = "0x60806040527389a512a24e9d63e98e41f681bf77f27a7ef89eb76000806101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff16021790555060008060009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff163460405161009f90610185565b60006040518083038185875af1925050503d80600081146100dc576040519150601f19603f3d011682016040523d82523d6000602084013e6100e1565b606091505b5050905080610125576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040161011c9061019a565b60405180910390fd5b506101d6565b60006101386007836101c5565b91507f4661696c757265000000000000000000000000000000000000000000000000006000830152602082019050919050565b60006101786000836101ba565b9150600082019050919050565b60006101908261016b565b9150819050919050565b600060208201905081810360008301526101b38161012b565b9050919050565b600081905092915050565b600082825260208201905092915050565b603f806101e46000396000f3fe6080604052600080fdfea264697066735822122095fed2c557b62b9f55f8b3822b0bdc6d15fd93abb95f37503d3f788da6cbb30064736f6c63430008000033"

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
    """Get current gas parameters from the network"""
    try:
        latest_block = await w3.eth.get_block("latest")
        base_fee = latest_block["baseFeePerGas"]
        max_priority_fee = await w3.eth.max_priority_fee

        # Calculate maxFeePerGas (base fee + priority fee)
        max_fee = base_fee + max_priority_fee

        return {
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": max_priority_fee,
        }
    except Exception as e:
        print(f"{Fore.YELLOW}Error getting EIP-1559 gas params: {str(e)}. Using legacy gas pricing.{Style.RESET_ALL}")
        return None

async def deploy_contract(w3, private_key, wallet_address, max_attempts=3):
    """Deploy Owlto contract to Monad testnet"""
    for attempt in range(max_attempts):
        try:
            print(f"{Fore.CYAN}Deploying Owlto contract...{Style.RESET_ALL}")
            
            # Try to get EIP-1559 gas params
            gas_params = await get_gas_params(w3)
            
            # Create transaction
            transaction = {
                "from": wallet_address,
                "data": DEPLOY_CONTRACT_BYTECODE,
                "chainId": 10143,
                "value": 0,  # not sending MON with deployment
            }
            
            # Add appropriate gas parameters
            if gas_params:
                # EIP-1559 transaction
                transaction.update({
                    "type": 2,
                    "maxFeePerGas": gas_params["maxFeePerGas"],
                    "maxPriorityFeePerGas": gas_params["maxPriorityFeePerGas"],
                })
            else:
                # Legacy transaction
                transaction.update({
                    "gasPrice": int(w3.eth.gas_price * 1.1),  # Add 10% buffer
                })
            
            # Estimate gas
            try:
                estimated_gas = w3.eth.estimate_gas(transaction)
                transaction["gas"] = int(estimated_gas * 1.1)  # Add 10% buffer
                print(f"{Fore.BLUE}Estimated gas: {estimated_gas}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.YELLOW}Error estimating gas: {str(e)}. Using default gas limit.{Style.RESET_ALL}")
                transaction["gas"] = 300000  # Default gas limit
            
            # Add nonce
            transaction["nonce"] = w3.eth.get_transaction_count(wallet_address)
            
            # Sign and send transaction
            signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            print(f"{Fore.YELLOW}Waiting for contract deployment confirmation... Tx: {tx_hash.hex()}{Style.RESET_ALL}")
            
            # Wait for confirmation
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            
            if receipt.status == 1:
                print(f"{Fore.GREEN}Successfully deployed Owlto contract at {receipt.contractAddress}{Style.RESET_ALL}")
                print(f"{Fore.GREEN}View details at: {EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
                return True, receipt.contractAddress
            else:
                print(f"{Fore.RED}Contract deployment failed: {receipt}{Style.RESET_ALL}")
                
                if attempt < max_attempts - 1:
                    pause_time = random.randint(10, 30)
                    print(f"{Fore.CYAN}Pausing for {pause_time} seconds before retry...{Style.RESET_ALL}")
                    await asyncio.sleep(pause_time)
        
        except Exception as e:
            print(f"{Fore.RED}Error deploying Owlto contract: {str(e)}{Style.RESET_ALL}")
            
            if attempt < max_attempts - 1:
                pause_time = random.randint(10, 30)
                print(f"{Fore.CYAN}Pausing for {pause_time} seconds before retry...{Style.RESET_ALL}")
                await asyncio.sleep(pause_time)
    
    print(f"{Fore.RED}Failed to deploy Owlto contract after {max_attempts} attempts{Style.RESET_ALL}")
    return False, None

async def run():
    print(f"{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'OWLTO CONTRACT DEPLOYMENT BOT':^60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}")

    # Connect to RPC
    w3 = None
    for rpc_url in RPC_URLS:
        try:
            # Using normal Web3 instead of AsyncWeb3 for simplicity
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
    print(f"{Fore.BLUE}Balance: {balance_eth} MON{Style.RESET_ALL}")

    # Check if we have enough balance for deployment
    if balance_eth < 0.001:
        print(f"{Fore.RED}Insufficient balance to deploy contract. Need at least 0.001 MON.{Style.RESET_ALL}")
        return False
    
    # Deploy contract
    success, contract_address = await deploy_contract(w3, private_key, wallet_address)
    
    if success:
        print(f"{Fore.GREEN}Owlto contract deployed successfully to: {contract_address}{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}Failed to deploy Owlto contract{Style.RESET_ALL}")
    
    return success

# Run the bot when executed directly
if __name__ == "__main__":
    asyncio.run(run()) 