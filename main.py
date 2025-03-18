import os
import json
import asyncio
import aiohttp
from rich.console import Console
from rich.prompt import Prompt
from rich.live import Live
from rich import box
from rich.table import Table

from core.banner import display_banner
from core.utils import parse_proxy, create_status_panel, verify_proxy_connection
from core.generator import generate_extension_id
from core.logger import setup_logger, log
from core.models import Account, Connection

# Setup console and logger
console = Console()
logger = setup_logger()

# Global variables
active_accounts = []
display_update_event = asyncio.Event()

async def get_public_ip(session, proxy=None):
    """Get public IP address"""
    try:
        response = await session.get("https://api.ipify.org/?format=json", proxy=proxy, timeout=10)
        if response.status == 200:
            data = await response.json()
            return data.get("ip")
    except Exception:
        pass
    return None

async def test_proxies(session, proxies):
    """Test all proxies to ensure they're working"""
    working_proxies = []
    console.print("[yellow]Testing proxies... This may take a moment.[/yellow]")
    
    for i, proxy_str in enumerate(proxies):
        proxy = parse_proxy(proxy_str)
        try:
            ip = await verify_proxy_connection(session, proxy)
            if ip:
                console.print(f"[green]Proxy {i+1}/{len(proxies)}: Working - IP: {ip}[/green]")
                working_proxies.append(proxy_str)
            else:
                console.print(f"[red]Proxy {i+1}/{len(proxies)}: Not working[/red]")
        except Exception:
            console.print(f"[red]Proxy {i+1}/{len(proxies)}: Error[/red]")
    
    return working_proxies

async def login_account(session, email, password):
    """Login to an ExeOS account and return the token"""
    url = "https://api.exeos.network/auth/web/email/login"
    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "sec-ch-ua": "\"Chromium\";v=\"134\", \"Not:A-Brand\";v=\"24\", \"Google Chrome\";v=\"134\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "Referer": "https://app.exeos.network/",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    }
    payload = {
        "email": email,
        "password": password,
        "referralCode": None
    }
    
    try:
        response = await session.post(url, headers=headers, json=payload)
        data = await response.json()
        if "data" in data and "token" in data["data"]:
            token = data["data"]["token"]
            log("SUCCESS", f"Logged in successfully: {email}")
            return token
        else:
            log("ERROR", f"Login failed for {email}: {data.get('message', 'Unknown error')}")
            return None
    except Exception as e:
        log("ERROR", f"Exception during login for {email}: {str(e)}")
        return None

async def get_account_info(session, token):
    """Get account information"""
    url = "https://api.exeos.network/account/web/me"
    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "authorization": f"Bearer {token}",
        "content-type": "application/json",
        "sec-ch-ua": "\"Chromium\";v=\"134\", \"Not:A-Brand\";v=\"24\", \"Google Chrome\";v=\"134\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "Referer": "https://app.exeos.network/",
        "Referrer-Policy": "strict-origin-when-cross-origin"
    }
    
    try:
        response = await session.get(url, headers=headers)
        data = await response.json()
        if "data" in data:
            account_data = data["data"]
            
            connected_nodes = []
            connected_rewards = 0
            
            if "networkNodes" in account_data and account_data["networkNodes"]:
                for node in account_data["networkNodes"]:
                    if node.get("status") == "Connected":
                        connected_nodes.append(node)
                        connected_rewards += float(node.get("totalRewards", 0))
            
            return {
                "firstName": account_data.get('firstName', ''),
                "lastName": account_data.get('lastName', ''),
                "earningsTotal": account_data.get('earningsTotal', '0'),
                "points": account_data.get("points", 0),
                "referralPoints": account_data.get("referralPoints", 0),
                "connectedNodes": connected_nodes,
                "connectedNodesCount": len(connected_nodes),
                "connectedNodesRewards": connected_rewards
            }
        else:
            return None
    except Exception:
        return None

async def connect_extension(session, token, extension_id, proxy=None):
    """Connect an extension to the ExeOS network"""
    # First verify the proxy is working and get its IP
    ip = await verify_proxy_connection(session, proxy)
    
    # If proxy verification failed, try a direct connection to get IP
    if not ip:
        ip = await get_public_ip(session, proxy)
        
    if not ip:
        log("ERROR", f"Failed to get IP address for extension {extension_id[:8]}...")
        return None, None

    url = "https://api.exeos.network/extension/connect"
    payload = {"ip": ip, "extensionId": extension_id}
    
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Origin": "chrome-extension://ijapofapbjjfegefdmhhgijgkillnogl",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    }
    
    try:
        response = await session.post(url, headers=headers, json=payload, proxy=proxy)
        data = await response.json()
        if response.status == 200:
            log("CONNECT", f"Success for {extension_id[:8]}... from {ip}")
            return data, ip
        else:
            log("ERROR", f"Failed to connect extension: {data.get('message', 'Unknown error')}")
            return None, ip
    except Exception as e:
        log("ERROR", f"Exception while connecting extension: {str(e)}")
        return None, ip

async def check_liveness(session, token, extension_id, proxy=None):
    """Check liveness of an extension"""
    url = "https://api.exeos.network/extension/liveness"
    payload = {"extensionId": extension_id}
    
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Origin": "chrome-extension://ijapofapbjjfegefdmhhgijgkillnogl",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    }
    
    try:
        response = await session.post(url, headers=headers, json=payload, proxy=proxy)
        if response.status == 200:
            log("LIVENESS", f"OK for {extension_id[:8]}...")
            return True
        else:
            return False
    except Exception:
        return False

async def check_stats(session, token, extension_id, proxy=None):
    """Check stats of an extension"""
    url = "https://api.exeos.network/extension/stats"
    payload = {"extensionId": extension_id}
    
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Origin": "chrome-extension://ijapofapbjjfegefdmhhgijgkillnogl",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    }
    
    try:
        response = await session.post(url, headers=headers, json=payload, proxy=proxy)
        if response.status == 200:
            log("STATS", f"Checked for {extension_id[:8]}...")
            return True
        else:
            return False
    except Exception:
        return False

async def liveness_sequence(session, connection):
    """Run the liveness sequence for a connection"""
    for _ in range(4):
        if await check_liveness(session, connection.token, connection.extension_id, connection.proxy):
            connection.liveness_count += 1
        await asyncio.sleep(5)

async def connection_worker(session, account, connection):
    """Worker to maintain a single connection"""
    while True:
        try:
            # Connect extension
            result, ip = await connect_extension(session, connection.token, connection.extension_id, connection.proxy)
            if result:
                connection.connect_count += 1
                connection.last_connect = asyncio.get_event_loop().time()
                connection.last_ip = ip
                
                # Check stats
                if await check_stats(session, connection.token, connection.extension_id, connection.proxy):
                    connection.stats_checks += 1
                
                # Run liveness sequence
                await liveness_sequence(session, connection)
                
                # Update display
                display_update_event.set()
                
                # Wait before next connect
                await asyncio.sleep(60)
            else:
                # If connection failed, wait before retry
                await asyncio.sleep(30)
        except Exception:
            await asyncio.sleep(30)

async def account_info_updater(session, account):
    """Periodically update account info"""
    while True:
        try:
            # Update account info every 5 minutes
            account_info = await get_account_info(session, account.token)
            if account_info:
                account.account_info = account_info
                account.stats["totalPoints"] = account_info["points"]
                account.stats["referralPoints"] = account_info["referralPoints"]
                account.stats["earningsTotal"] = float(account_info["earningsTotal"])
                account.stats["connectedNodesCount"] = account_info["connectedNodesCount"]
                account.stats["connectedNodesRewards"] = account_info["connectedNodesRewards"]
                account.stats["firstName"] = account_info["firstName"]
                account.stats["lastName"] = account_info["lastName"]
                account.stats["lastUpdated"] = asyncio.get_event_loop().time()
                
                # Update display
                display_update_event.set()
            
            # Wait before next update
            await asyncio.sleep(300)  # 5 minutes
        except Exception:
            await asyncio.sleep(60)

async def status_display_updater():
    """Update the status display periodically"""
    with Live(create_status_panel(active_accounts), refresh_per_second=1, screen=True) as live:
        while True:
            # Wait for an update event or timeout after 5 seconds
            try:
                await asyncio.wait_for(display_update_event.wait(), 5)
                display_update_event.clear()
            except asyncio.TimeoutError:
                pass
            
            # Update the display
            live.update(create_status_panel(active_accounts))

async def main():
    # Create necessary directories
    os.makedirs("core", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    # Display banner
    display_banner()
    
    # Load accounts
    if not os.path.exists("accounts.json"):
        console.print("[red]Error: accounts.json file not found[/red]")
        return
    
    try:
        with open("accounts.json", "r") as f:
            accounts_data = json.load(f)
        
        if not accounts_data:
            console.print("[red]Error: No accounts found in accounts.json[/red]")
            return
    except Exception as e:
        console.print(f"[red]Error loading accounts: {str(e)}[/red]")
        return
    
    # Load proxies
    try:
        if os.path.exists("proxies.txt"):
            with open("proxies.txt", "r") as f:
                proxies = [line.strip() for line in f if line.strip()]
            console.print(f"[green]Loaded {len(proxies)} proxies from proxies.txt[/green]")
        else:
            proxies = []
            console.print("[yellow]No proxies.txt file found. Running without proxies.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error loading proxies: {str(e)}[/red]")
        proxies = []
    
    # Display account information
    console.print(f"[green]Found {len(accounts_data)} accounts in accounts.json[/green]")
    
    # Ask for connections per account with a beautiful prompt
    connections_per_account = Prompt.ask(
        "[bold cyan]How many connections per account?[/bold cyan]", 
        default="1", 
        show_default=True
    )
    
    try:
        connections_per_account = int(connections_per_account)
        if connections_per_account <= 0:
            raise ValueError("Must be a positive number")
    except ValueError:
        console.print("[red]Invalid number. Using default of 1 connection per account.[/red]")
        connections_per_account = 1
    
    if connections_per_account * len(accounts_data) > len(proxies) and len(proxies) > 0:
        console.print(f"[yellow]Warning: Not enough proxies for all connections. Some connections might not work properly.[/yellow]")
    
    # Create beautiful configuration display
    config_table = Table(title="🚀 ExeOS Bot Configuration", box=box.ROUNDED)
    config_table.add_column("Setting", style="cyan bold")
    config_table.add_column("Value", style="green")
    config_table.add_row("Accounts", str(len(accounts_data)))
    config_table.add_row("Connections per account", str(connections_per_account))
    config_table.add_row("Total connections", str(len(accounts_data) * connections_per_account))
    config_table.add_row("Proxies available", str(len(proxies)))
    console.print(config_table)
    
    # Confirm start with a beautiful prompt
    start_confirm = Prompt.ask(
        "\n[bold green]Start the ExeOS Bot?[/bold green]", 
        choices=["y", "n"], 
        default="y"
    )
    
    if start_confirm.lower() != "y":
        console.print("[yellow]Bot startup cancelled.[/yellow]")
        return
    
    console.print("\n[bold green]Starting ExeOS Bot...[/bold green]")
    
    # Create aiohttp session with longer timeout
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Test proxies before using them
        if proxies:
            proxies = await test_proxies(session, proxies)
            if not proxies:
                console.print("[red]No working proxies found. Exiting...[/red]")
                return
            console.print(f"[green]Using {len(proxies)} working proxies[/green]")
        
        # Process each account
        tasks = []
        
        for acc_idx, acc_data in enumerate(accounts_data):
            email = acc_data["Email"]
            password = acc_data["Password"]
            
            # Login to account
            token = await login_account(session, email, password)
            if not token:
                continue
            
            # Create account object
            account = Account(email, password, token)
            active_accounts.append(account)
            
            # Get initial account info
            account_info = await get_account_info(session, token)
            if account_info:
                account.account_info = account_info
                account.stats["totalPoints"] = account_info["points"]
                account.stats["referralPoints"] = account_info["referralPoints"]
                account.stats["earningsTotal"] = float(account_info["earningsTotal"])
                account.stats["connectedNodesCount"] = account_info["connectedNodesCount"]
                account.stats["connectedNodesRewards"] = account_info["connectedNodesRewards"]
                account.stats["firstName"] = account_info["firstName"]
                account.stats["lastName"] = account_info["lastName"]
                account.stats["lastUpdated"] = asyncio.get_event_loop().time()
            
            # Create connections for this account
            for i in range(connections_per_account):
                # Generate a new extension ID
                extension_id = generate_extension_id()
                
                # Get a proxy for this connection
                proxy_idx = (acc_idx * connections_per_account + i) % len(proxies) if proxies else None
                proxy = parse_proxy(proxies[proxy_idx]) if proxy_idx is not None else None
                
                # Create connection object
                connection = Connection(token, extension_id, proxy)
                account.connections.append(connection)
                
                # Start connection worker
                tasks.append(connection_worker(session, account, connection))
            
            # Start account info updater
            tasks.append(account_info_updater(session, account))
        
        # Start status display updater
        tasks.append(status_display_updater())
        
        # Run all tasks
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Bot stopped by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {str(e)}[/red]")