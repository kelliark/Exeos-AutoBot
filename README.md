# ExeOS Auto Bot

ExeOS Bot is an asynchronous Python application that automates interactions with the ExeOS network. The bot logs into your ExeOS accounts, establishes extension connections (optionally using proxies), and continuously monitors connection statuses—all while displaying real-time updates using a visually appealing dashboard.

# Register here:
[Exeos Network](https://app.exeos.network?referralCode=REFJYMYYOZ8)

Use my code: **REFJYMYYOZ8**

## Features

- **Account Management:** Logs in using credentials provided in `accounts.json`.
- **Proxy Support:** Optionally routes connections through proxies listed in `proxies.txt`.
- **Asynchronous Operations:** Leverages `asyncio` and `aiohttp` for concurrent tasks.
- **Live Status Dashboard:** Uses Rich for a real-time terminal UI.
- **Logging:** Logs events and errors to both the console and daily log files in the `logs` directory.
- **Extension Connection Management:** Automates connecting and monitoring extension statuses on the ExeOS network.

## Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/kelliark/Exeos-AutoBot.git
   cd Exeos-AutoBot
   ```

2. **Set Up a Virtual Environment (Optional but Recommended)**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### Accounts

Create an `accounts.json` file in the project root with your ExeOS account credentials. For example:
```json
[
    {
        "Email": "example@gmail.com",
        "Password": "examplepassword"
    },
    {
        "Email": "example2@gmail.com",
        "Password": "examplepassword2"
    }

// you can add more via putting , on the 2nd part and the last part no coma
]
```

### Proxies (Optional)

If you want to use proxies, create a `proxies.txt` file in the project root. Each line should contain one proxy in the following format:
```
http://username:password@proxyserver:port
https://username:password@proxyserver:port
socks5://username:password@proxyserver:port
socks4://username:password@proxyserver:port
```
The bot will automatically test these proxies and use only the working ones.

## Usage

Run the bot with the following command:
```bash
python main.py
```
## Contributing

Contributions are welcome! Please open an issue or submit a pull request if you have suggestions, bug fixes, or enhancements.

## Disclaimer

Use it at your own risk when using this bot. all risk are borne with the user.
