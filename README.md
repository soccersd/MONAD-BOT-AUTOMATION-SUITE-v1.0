# Monad Bot Automation Suite

An automation suite for running various bots on the Monad network. This suite allows for scheduling, proxy support, and efficient management of multiple accounts (private keys).

## Features

- **Multiple Bot Support**: Includes various specialized bots for different functions on the Monad network
- **Random Bot Mode**: Automatically selects and runs random bots
- **Scheduling**: Configure automated schedules with customizable time intervals (hours, minutes, seconds)
- **Proxy Support**: Use proxies from a configuration file or from a list in `proxy.txt`
- **Account Management**: Sequential or random selection of accounts from private keys
- **Error Handling**: Automatic retry with different bots on failure

## Setup

1. Install requirements:
   ```
   pip install -r requirements.txt
   ```

2. Configure your private keys:
   Create a file named `pvkey.txt` with one private key per line.

3. (Optional) Configure proxies:
   Create a file named `proxy.txt` with one proxy per line in the format `ip:port` or `username:password@ip:port`.

4. (Optional) Adjust configuration in `config.py`.

## Usage

Run the main script:
```
python main.py
```

### Main Menu Options

1. **Select specific bot**: Choose a specific bot to run
2. **Run random bot**: Run random bots with customizable settings
3. **Exit**: Exit the program

### Random Bot Mode

When selecting the random bot mode, you'll be asked:
1. How many bots to run per private key
2. How long to wait between cycles (with customizable time units - hours, minutes, or seconds)

## Bot Types

The suite includes various bots:
- Atlantis Swap Bot
- MonadVerse NFT Minter
- NAD Domains Bot
- Narwhal Finance Bot
- OnChainGM Bot
- Orbiter Bridge Bot
- Owlto Contract Bot
- Apriori Bot

## Configuration

Edit `config.py` to adjust:
- Proxy settings
- Scheduling parameters
- Account usage mode (sequential or random)

## License

This project is licensed under the MIT License - see the LICENSE file for details. 