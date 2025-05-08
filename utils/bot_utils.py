import asyncio
import random
import time
from datetime import datetime, timedelta
from typing import List, Optional
import aiohttp
from config import PROXY_CONFIG, SCHEDULE_CONFIG, ACCOUNT_CONFIG
import os

class ProxyManager:
    def __init__(self):
        self.proxy_config = PROXY_CONFIG
        self.proxies = self.load_proxies_from_file('proxy.txt')
        self.current_proxy_index = 0

    def load_proxies_from_file(self, file_path: str) -> List[str]:
        """Load proxies from file."""
        proxies = []
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    for line in f:
                        proxy = line.strip()
                        if proxy and not proxy.startswith('#'):
                            proxies.append(proxy)
            except Exception as e:
                print(f"Error loading proxies: {e}")
        
        return proxies

    def get_proxy_url(self) -> Optional[str]:
        """Get a proxy URL to use."""
        # If proxies are available from the file, use them first
        if self.proxies:
            # Use a round-robin approach
            proxy = self.proxies[self.current_proxy_index]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
            
            # Format proxy depending on whether it already has a protocol
            if '://' in proxy:
                return proxy
            else:
                proxy_type = self.proxy_config['proxy_type']
                return f"{proxy_type}://{proxy}"
        
        # If no proxies in file or proxy not enabled, use the config
        if not self.proxy_config['enabled'] or not self.proxy_config['proxy_url']:
            return None
        
        proxy_type = self.proxy_config['proxy_type']
        proxy_url = self.proxy_config['proxy_url']
        
        if proxy_type in ['http', 'https']:
            return f"{proxy_type}://{proxy_url}"
        elif proxy_type in ['socks4', 'socks5']:
            return f"{proxy_type}://{proxy_url}"
        return None

    async def test_proxy(self) -> bool:
        proxy_url = self.get_proxy_url()
        if not proxy_url:
            return True

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.ipify.org?format=json', proxy=proxy_url, timeout=10) as response:
                    return response.status == 200
        except:
            return False

class Scheduler:
    def __init__(self):
        self.schedule_config = SCHEDULE_CONFIG

    async def wait_for_next_run(self):
        if not self.schedule_config['enabled']:
            return

        if self.schedule_config['random_delay']:
            delay_minutes = random.randint(
                self.schedule_config['min_delay_minutes'],
                self.schedule_config['max_delay_minutes']
            )
            await asyncio.sleep(delay_minutes * 60)
        else:
            await asyncio.sleep(self.schedule_config['interval_hours'] * 3600)

class AccountManager:
    def __init__(self, private_keys: List[str]):
        self.private_keys = private_keys
        self.current_index = 0
        self.account_config = ACCOUNT_CONFIG

    def get_next_account(self) -> str:
        if not self.private_keys:
            raise ValueError("No private keys available")

        if self.account_config['random_mode']:
            return random.choice(self.private_keys)
        
        if self.account_config['sequential_mode']:
            key = self.private_keys[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.private_keys)
            return key
        
        return self.private_keys[0]

    def reset_index(self):
        self.current_index = 0 