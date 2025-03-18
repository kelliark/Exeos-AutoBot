# ExeOS Bot

An automated tool for managing ExeOS network nodes and maximizing rewards.

# Register here:
[Exeos Network](https://app.exeos.network?referralCode=REFJYMYYOZ8)

Use my code: **REFJYMYYOZ8**


## Features

- **Multi-Account Support**: Manage multiple ExeOS accounts from a single interface
- **Auto Connection**: Automatically connect and maintain nodes on the ExeOS network
- **Proxy Support**: Use proxies to distribute connections and avoid IP bans
- **Real-time Monitoring**: Track connections, earnings, and node status in real-time
- **Node ID Management**: Create and fetch node IDs for your accounts
- **Beautiful Interface**: Rich console interface with detailed status panels

## Installation

1. Clone the repository:
```bash
git clone https://github.com/kelliark/Exeos-AutoBot.git
cd Exeos-AutoBot/
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your accounts by creating an `accounts.json` file:
```json
[
    {
        "Email": "your_email@example.com",
        "Password": "your_password",
        "NodeIds": []
    }
]
```

4. (Optional) Add proxies in a `proxies.txt` file, one per line:
```
http://username:password@host:port
https://host:port
socks5://host:port
```

## Usage

Run the bot:
```bash
python main.py
```

### Options

When you run the bot, you'll have three options:

1. **Fetch Node IDs**: Retrieve existing node IDs for your accounts
2. **Run Auto Farm**: Start the bot with existing accounts
3. **Create New NodeIDs**: Generate new node IDs for your accounts

## Tips for Best Results

- Use high-quality proxies to avoid IP bans
- Create multiple nodes per account (5-10 recommended)
- Run the bot 24/7 for maximum earnings
- Check logs regularly for any issues

## Notes

This tool is provided for educational purposes only. Use at your own risk. The developers are not responsible for any account bans or other issues that may arise from using this bot.
If you find this tool helpful, consider leaving a star ⭐ on the repository!
