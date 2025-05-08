import subprocess
import sys
from colorama import init, Fore, Style
import os
import asyncio
import random
from utils.bot_utils import ProxyManager, Scheduler, AccountManager
from utils.banner import print_banner, print_section
from utils.logger import Logger
from config import PROXY_CONFIG, SCHEDULE_CONFIG, ACCOUNT_CONFIG
import datetime

# Initialize colorama
init(autoreset=True)

BOTS = [
    ("Atlantis Swap Bot", "script/atlantis_swap_bot.py"),
    ("MonadVerse NFT Minter", "script/monadverse_mint.py"),
    ("NAD Domains Bot", "script/nad_domains.py"),
    ("Narwhal Finance Bot", "script/narwhal_finance.py"),
    ("OnChainGM Bot", "script/onchaingm_bot.py"),
    ("Orbiter Bridge Bot", "script/orbiter.py"),
    ("Owlto Contract Bot", "script/owlto.py"),
    ("apriority Bot", "script/apriori_bot.py"),
]

def load_private_keys():
    try:
        with open('pvkey.txt', 'r') as f:
            keys = [line.strip() for line in f if line.strip()]
            Logger.info(f"Loaded {len(keys)} private keys from pvkey.txt")
            return keys
    except FileNotFoundError:
        Logger.error("pvkey.txt not found!")
        sys.exit(1)

async def run_bot_with_config(script_name: str, private_key: str, scheduler: Scheduler):
    proxy_manager = ProxyManager()
    
    # Test proxy if enabled
    if PROXY_CONFIG['enabled']:
        Logger.status("proxy", "Testing proxy connection...")
        if not await proxy_manager.test_proxy():
            Logger.error("Proxy test failed! Please check your proxy settings.")
            return False
    
    # Set environment variables for the bot
    env = os.environ.copy()
    env['PRIVATE_KEY'] = private_key
    if PROXY_CONFIG['enabled']:
        env['PROXY_URL'] = proxy_manager.get_proxy_url()
    
    # Run the bot
    Logger.status("run", f"Running bot with private key: {private_key[:6]}...{private_key[-4:]}")
    Logger.command(f"python {script_name}")
    
    process = subprocess.run([sys.executable, script_name], env=env)
    
    if process.returncode == 0:
        Logger.success(f"Bot execution completed successfully")
        return True
    else:
        Logger.error(f"Bot execution failed with exit code {process.returncode}")
        return False

async def main_async():
    # Display the fancy banner
    print_banner()
    
    # Load private keys
    private_keys = load_private_keys()
    account_manager = AccountManager(private_keys)
    scheduler = Scheduler()
    
    while True:
        print_section("MAIN MENU")
        
        # Use logger's prompt for interactive input
        options = ["Select specific bot", "Run random bot", "Exit"]
        for i, option in enumerate(options, 1):
            Logger.status(f"option {i}", option)
        
        choice = Logger.input("Enter number (1-3):")
        
        if choice == "3":
            Logger.info("Exiting program")
            break
        elif choice == "1":
            print_section("SELECT BOT")
            
            for i, (name, _) in enumerate(BOTS, 1):
                Logger.status(f"bot {i}", name)
            Logger.status("option 0", "Back to main menu")
            
            bot_choice = Logger.input(f"Enter number (0-{len(BOTS)}):")
            if bot_choice == "0":
                continue
                
            try:
                idx = int(bot_choice) - 1
                if idx < 0 or idx >= len(BOTS):
                    raise ValueError
            except ValueError:
                Logger.error("Invalid bot selection!")
                continue
                
            script = BOTS[idx][1]
            if not os.path.exists(script):
                Logger.error(f"Script file not found: {script}")
                continue
                
            Logger.header(f"RUNNING {BOTS[idx][0].upper()}")
            
            while True:
                private_key = account_manager.get_next_account()
                success = await run_bot_with_config(script, private_key, scheduler)
                
                if not success:
                    Logger.warning(f"Bot execution failed for key: {private_key[:6]}...{private_key[-4:]}")
                    # If it's the apriori bot that failed, move to the next key since it might be due to insufficient balance
                    if "apriori_bot.py" in script:
                        Logger.info("Apriori bot failed, moving to next private key...")
                        continue
                
                if SCHEDULE_CONFIG['enabled']:
                    Logger.info("Waiting for next scheduled run...")
                    await scheduler.wait_for_next_run()
                else:
                    break
                    
        elif choice == "2":
            # Random bot mode
            print_section("RANDOM BOT MODE")
            
            # Ask how many bots to run per private key
            while True:
                try:
                    bots_per_key = int(Logger.input(f"How many bots would you like to run per private key? (1-{len(BOTS)}):"))
                    if 1 <= bots_per_key <= len(BOTS):
                        break
                    else:
                        Logger.error(f"Please enter a number between 1 and {len(BOTS)}.")
                except ValueError:
                    Logger.error("Please enter a valid number.")
            
            # Ask for time between full cycles with unit selection
            wait_seconds = 0
            time_display = "no repeat"
            
            while True:
                try:
                    time_unit = Logger.input("Select time unit for cycle interval (h=hours, m=minutes, s=seconds):").lower()
                    if time_unit not in ['h', 'm', 's']:
                        Logger.error("Please enter 'h' for hours, 'm' for minutes, or 's' for seconds.")
                        continue
                        
                    unit_name = 'hours' if time_unit == 'h' else 'minutes' if time_unit == 'm' else 'seconds'
                    time_between_cycles = float(Logger.input(f"After running all private keys, how many {unit_name} should we wait before starting again? (0 for no repeat):"))
                        
                    if time_between_cycles < 0:
                        Logger.error("Please enter a positive number or 0.")
                        continue
                        
                    # Convert to seconds internally
                    if time_unit == 'h':
                        wait_seconds = int(time_between_cycles * 3600)
                        time_display = f"{time_between_cycles} hours"
                    elif time_unit == 'm':
                        wait_seconds = int(time_between_cycles * 60)
                        time_display = f"{time_between_cycles} minutes"
                    else:  # seconds
                        wait_seconds = int(time_between_cycles)
                        time_display = f"{time_between_cycles} seconds"
                        
                    break
                except ValueError:
                    Logger.error("Please enter a valid number.")
            
            Logger.info(f"Running {bots_per_key} random bots per private key")
            if wait_seconds > 0:
                Logger.info(f"Will repeat the entire cycle every {time_display}")
            
            # Load all private keys
            private_keys = load_private_keys()
            
            cycle_number = 1
            while True:  # Main cycle loop
                print_section("STARTING NEW CYCLE")
                Logger.header(f"CYCLE #{cycle_number}")
                Logger.info(f"Starting a new cycle of bot runs for all private keys")
                
                # For each private key
                for idx, private_key in enumerate(private_keys):
                    key_progress = f"{idx+1}/{len(private_keys)}"
                    Logger.step(idx+1, len(private_keys), f"Processing private key: {private_key[:6]}...{private_key[-4:]}")
                    
                    # Run specified number of random bots for this key
                    bots_run = 0
                    used_bots = []  # Keep track of which bots have been used for this key
                    
                    while bots_run < bots_per_key:
                        # Select a random bot that hasn't been used for this key yet
                        available_bots = [(name, script) for name, script in BOTS if (name, script) not in used_bots]
                        
                        if not available_bots:
                            Logger.warning("All available bots have been run for this key")
                            break
                        
                        bot_name, script = random.choice(available_bots)
                        used_bots.append((bot_name, script))
                        
                        bot_progress = f"{bots_run+1}/{bots_per_key}"
                        Logger.status("bot", f"Running bot {bot_progress}: {bot_name}")
                        
                        if not os.path.exists(script):
                            Logger.error(f"Script not found: {script}. Trying another...")
                            await asyncio.sleep(1)
                            continue
                        
                        success = await run_bot_with_config(script, private_key, scheduler)
                        bots_run += 1
                        
                        if not success:
                            Logger.error(f"Bot execution failed for key: {private_key[:6]}...{private_key[-4:]}")
                            Logger.warning(f"Delaying for 3 seconds before trying another bot...")
                            await asyncio.sleep(3)
                        else:
                            # Small pause between successful bot runs
                            await asyncio.sleep(2)
                
                # Check if we should repeat the cycle
                if wait_seconds <= 0:
                    Logger.success("All private keys processed. Exiting as per configuration.")
                    break
                
                # Wait for the specified time before starting a new cycle
                wait_until = datetime.datetime.now() + datetime.timedelta(seconds=wait_seconds)
                print_section("WAITING FOR NEXT CYCLE")
                Logger.info(f"All private keys processed. Waiting until {wait_until.strftime('%Y-%m-%d %H:%M:%S')} before starting a new cycle...")
                
                # Show progress bar for waiting
                start_time = datetime.datetime.now()
                total_wait = wait_seconds
                
                for remaining in range(wait_seconds, 0, -1):
                    elapsed = total_wait - remaining
                    Logger.progress(elapsed, total_wait, "Waiting", f"{remaining} seconds remaining")
                    await asyncio.sleep(1)
                
                cycle_number += 1
        else:
            Logger.error("Invalid choice!")

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
