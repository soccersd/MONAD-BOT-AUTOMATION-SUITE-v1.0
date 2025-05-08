import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Proxy configuration
PROXY_CONFIG = {
    'enabled': False,  # Set to True to enable proxy
    'proxy_type': 'http',  # Options: http, https, socks4, socks5
    'proxy_url': '',  # Format: username:password@host:port
}

# Scheduling configuration
SCHEDULE_CONFIG = {
    'enabled': False,  # Set to True to enable scheduling
    'interval_hours': 24,  # Run every X hours
    'random_delay': True,  # Add random delay between runs
    'min_delay_minutes': 5,  # Minimum delay in minutes
    'max_delay_minutes': 30,  # Maximum delay in minutes
}

# Account configuration
ACCOUNT_CONFIG = {
    'sequential_mode': True,  # Run accounts sequentially
    'random_mode': False,  # Run accounts in random order
} 