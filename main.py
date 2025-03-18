import os
import json
import asyncio
import aiohttp
import random
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

async def test_single_proxy(session, proxy_str):
    """Test a single proxy to see if it works"""
    proxy = parse_proxy(proxy_str)
    try:
        ip = await verify_proxy_connection(session, proxy)
        if ip:
            return proxy_str, ip
    except Exception:
        pass
    return None, None

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
                "connectedNodesRewards": connected_rewards,
                "networkNodes": account_data.get("networkNodes", [])
            }
        else:
            return None
    except Exception as e:
        log("ERROR", f"Exception while getting account info: {str(e)}")
        return None

async def fetch_node_ids():
    """Fetch node IDs for all accounts and update accounts.json"""
    console.print("\n[bold cyan]Fetching node IDs for all accounts...[/bold cyan]")
    
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
    
    # Create aiohttp session
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        updated_accounts = []
        
        for idx, acc_data in enumerate(accounts_data):
            email = acc_data["Email"]
            password = acc_data["Password"]
            
            console.print(f"[cyan]Processing account {idx+1}/{len(accounts_data)}: {email}[/cyan]")
            
            # Login to account
            token = await login_account(session, email, password)
            if not token:
                console.print(f"[red]Login failed for {email}, skipping...[/red]")
                updated_accounts.append(acc_data)  # Keep original data
                continue
            
            # Get account info with node IDs
            account_info = await get_account_info(session, token)
            if not account_info or "networkNodes" not in account_info:
                console.print(f"[red]Failed to get node IDs for {email}, skipping...[/red]")
                updated_accounts.append(acc_data)  # Keep original data
                continue
            
            # Extract node IDs
            node_ids = []
            for node in account_info["networkNodes"]:
                node_id = node.get("nodeId")
                if node_id:
                    node_ids.append(node_id)
            
            # Update account data with node IDs
            updated_acc = {
                "Email": email,
                "Password": password,
                "NodeIds": node_ids
            }
            updated_accounts.append(updated_acc)
            
            console.print(f"[green]Found {len(node_ids)} node IDs for {email}[/green]")
            
            # Wait before processing next account to avoid rate limiting
            if idx < len(accounts_data) - 1:
                await asyncio.sleep(2)
        
        # Save updated accounts data
        try:
            with open("accounts.json", "w") as f:
                json.dump(updated_accounts, f, indent=4)
            console.print("[bold green]Successfully updated accounts.json with node IDs![/bold green]")
        except Exception as e:
            console.print(f"[red]Error saving updated accounts data: {str(e)}[/red]")

async def connect_extension_with_retry(session, token, extension_id, proxy=None, max_retries=3):
    """Connect an extension with retry logic"""
    for attempt in range(max_retries):
        try:
            result, ip = await connect_extension(session, token, extension_id, proxy)
            if result:
                return result, ip
            # If connection failed but no exception was raised, wait before retry
            await asyncio.sleep(5 * (attempt + 1))  # Progressive delay
        except Exception as e:
            log("ERROR", f"Attempt {attempt+1}/{max_retries} failed: {str(e)}")
            # Exponential backoff
            await asyncio.sleep(2 ** attempt * 5)  # 5s, 10s, 20s...
    
    return None, None

async def find_working_proxy(session, proxies, current_proxy):
    """Find a working proxy from the available proxies"""
    # First try the current proxy
    if current_proxy:
        ip = await verify_proxy_connection(session, current_proxy)
        if ip:
            return current_proxy, ip
    
    # If current proxy is not working, try other proxies
    for proxy_str in proxies:
        proxy = parse_proxy(proxy_str)
        if proxy != current_proxy:  # Skip the current proxy we just tested
            ip = await verify_proxy_connection(session, proxy)
            if ip:
                log("PROXY", f"Switched to working proxy: {proxy_str}")
                return proxy, ip
    
    # If no working proxy found, return None
    return None, None

async def connect_extension(session, token, extension_id, proxy=None, proxies=None):
    """Connect an extension to the ExeOS network"""
    # First verify the proxy is working and get its IP
    ip = await verify_proxy_connection(session, proxy)
    
    # If proxy verification failed and we have other proxies, try to find a working one
    if not ip and proxies:
        proxy, ip = await find_working_proxy(session, proxies, proxy)
    
    # If still no working proxy, try a direct connection
    if not ip:
        ip = await get_public_ip(session)
        
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
        
        # Check if we got a 403 or other error status
        if response.status >= 400:
            error_text = await response.text()
            if response.status == 403:
                log("ERROR", f"403 Forbidden error for {extension_id[:8]}... - IP might be banned")
            else:
                log("ERROR", f"Server returned {response.status}: {error_text[:50]}...")
            return None, ip
            
        # Try to parse as JSON
        try:
            data = await response.json()
            if response.status == 200:
                log("CONNECT", f"Success for {extension_id[:8]}... from {ip}")
                return data, ip
            else:
                log("ERROR", f"Failed to connect extension: {data.get('message', 'Unknown error')}")
                return None, ip
        except:
            # If we can't parse as JSON, log the raw response
            error_text = await response.text()
            log("ERROR", f"Failed to parse response as JSON: {error_text[:50]}...")
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
            data = await response.json()
            log("LIVENESS", f"OK for {extension_id[:8]}...")
            
            # Store uptime information if available
            if (data.get("updatedData") and 
                data["updatedData"].get("nodeExtension") and 
                data["updatedData"]["nodeExtension"].get("uptimeTotal")):
                
                uptime = data["updatedData"]["nodeExtension"]["uptimeTotal"]
                # Find the connection object and update its uptime
                for acc in active_accounts:
                    for conn in acc.connections:
                        if conn.extension_id == extension_id:
                            conn.uptime_total = uptime
                            break
            
            return True
        elif response.status == 403:
            log("ERROR", f"403 Forbidden in liveness check for {extension_id[:8]}...")
            return False
        else:
            error_text = await response.text()
            log("ERROR", f"Liveness check failed with status {response.status}: {error_text[:50]}...")
            return False
    except Exception as e:
        log("ERROR", f"Exception in liveness check: {str(e)}")
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
        elif response.status == 403:
            log("ERROR", f"403 Forbidden in stats check for {extension_id[:8]}...")
            return False
        else:
            error_text = await response.text()
            log("ERROR", f"Stats check failed with status {response.status}: {error_text[:50]}...")
            return False
    except Exception as e:
        log("ERROR", f"Exception in stats check: {str(e)}")
        return False

async def liveness_sequence(session, connection):
    """Run the liveness sequence for a connection"""
    # Changed the ping frequency to every 30 seconds (4 pings with 7 second intervals)
    for _ in range(4):
        if await check_liveness(session, connection.token, connection.extension_id, connection.proxy):
            connection.liveness_count += 1
        await asyncio.sleep(7)  # Reduced to 7 seconds between pings to complete in ~30 seconds

async def connection_worker(session, account, connection, all_proxies=None):
    """Worker to maintain a single connection"""
    while True:
        try:
            # Add a random delay between 2-5 seconds before connecting
            # This helps stagger connections and avoid triggering rate limits
            await asyncio.sleep(random.uniform(2, 5))
            
            # Connect extension with retry logic, passing all proxies for potential switching
            result, ip = await connect_extension_with_retry(
                session, 
                connection.token, 
                connection.extension_id, 
                connection.proxy
            )
            
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
                
                # Wait before next connect - reduced to 30 seconds to improve earnings
                await asyncio.sleep(30)
            else:
                # If connection failed and we have proxies, try to find a working one
                if all_proxies:
                    new_proxy, ip = await find_working_proxy(session, all_proxies, connection.proxy)
                    if new_proxy and new_proxy != connection.proxy:
                        log("PROXY", f"Switching proxy for {connection.extension_id[:8]}...")
                        connection.proxy = new_proxy
                
                # Wait before retry
                await asyncio.sleep(15)
        except Exception as e:
            log("ERROR", f"Error in connection worker: {str(e)}")
            await asyncio.sleep(15)

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
        except Exception as e:
            log("ERROR", f"Error in account info updater: {str(e)}")
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

async def verify_token(session, token):
    """Verify that a token is still valid"""
    try:
        account_info = await get_account_info(session, token)
        return account_info is not None
    except:
        return False
    
async def create_new_node_ids():
    """Create new NodeIDs for accounts in accounts.json"""
    console.print("\n[bold cyan]Creating new NodeIDs for accounts...[/bold cyan]")
    
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
    
    # Ask for number of NodeIDs to create per account
    nodes_per_account = Prompt.ask(
        "[bold cyan]How many NodeIDs to create per account?[/bold cyan]", 
        default="1"
    )
    
    try:
        nodes_per_account = int(nodes_per_account)
        if nodes_per_account <= 0:
            raise ValueError("Must be a positive number")
    except ValueError:
        console.print("[red]Invalid number. Using default of 1 NodeID per account.[/red]")
        nodes_per_account = 1
    
    console.print(f"[green]Creating {nodes_per_account} NodeIDs for each account...[/green]")
    
    # Create aiohttp session
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        updated_accounts = []
        
        for idx, acc_data in enumerate(accounts_data):
            email = acc_data["Email"]
            password = acc_data["Password"]
            
            console.print(f"[cyan]Processing account {idx+1}/{len(accounts_data)}: {email}[/cyan]")
            
            # Login to account
            token = await login_account(session, email, password)
            if not token:
                console.print(f"[red]Login failed for {email}, skipping...[/red]")
                updated_accounts.append(acc_data)  # Keep original data
                continue
            
            # Create NodeIDs (extension IDs)
            existing_nodes = acc_data.get("NodeIds", [])
            new_nodes = []
            
            for i in range(nodes_per_account):
                new_node_id = generate_extension_id()
                new_nodes.append(new_node_id)
                console.print(f"[green]Created NodeID: {new_node_id[:8]}...[/green]")
            
            # Combine existing and new NodeIDs
            combined_nodes = existing_nodes + new_nodes
            
            # Update account data
            updated_acc = {
                "Email": email,
                "Password": password,
                "NodeIds": combined_nodes
            }
            updated_accounts.append(updated_acc)
            
            console.print(f"[green]Added {len(new_nodes)} NodeIDs to account {email}[/green]")
            
            # Wait before processing next account to avoid rate limiting
            if idx < len(accounts_data) - 1:
                await asyncio.sleep(2)
        
        # Save updated accounts data
        try:
            with open("accounts.json", "w") as f:
                json.dump(updated_accounts, f, indent=4)
            console.print("[bold green]Successfully updated accounts.json with new NodeIDs![/bold green]")
        except Exception as e:
            console.print(f"[red]Error saving updated accounts data: {str(e)}[/red]")

async def main():
    # Create necessary directories
    os.makedirs("core", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    # Display banner
    display_banner()
    
    # Ask whether to fetch node IDs, run the bot, or create new NodeIDs
    action = Prompt.ask(
        "[bold cyan]Choose action:[/bold cyan]\n" +
        "[cyan]1[/cyan] - Fetch Node IDs for existing accounts\n" +
        "[cyan]2[/cyan] - Run auto farm with existing accounts\n" +
        "[cyan]3[/cyan] - Create new NodeIDs for accounts",
        choices=["1", "2", "3"],
        default="2"
    )
    
    if action == "1":
        # Fetch node IDs
        await fetch_node_ids()
        # After fetching, ask if user wants to run the bot
        run_bot = Prompt.ask(
            "\n[bold green]Do you want to run the bot now?[/bold green]",
            choices=["y", "n"],
            default="y"
        )
        if run_bot.lower() == "y":
            action = "2"  # Set action to run the bot
        else:
            console.print("[yellow]Exiting...[/yellow]")
            return
    elif action == "3":
        # Create new NodeIDs for accounts
        await create_new_node_ids()
        # After creating, ask if user wants to run the bot
        run_bot = Prompt.ask(
            "\n[bold green]Do you want to run the bot now?[/bold green]",
            choices=["y", "n"],
            default="y"
        )
        if run_bot.lower() == "y":
            action = "2"  # Set action to run the bot
        else:
            console.print("[yellow]Exiting...[/yellow]")
            return
    
    if action == "2":
        # Run the bot
        # Load accounts
        if not os.path.exists("accounts.json"):
            console.print("[red]Error: accounts.json file not found[/red]")
            return
    
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
    
    # Determine if accounts have node IDs or need connections per account
    has_node_ids = any("NodeIds" in acc and acc["NodeIds"] for acc in accounts_data)
    
    if not has_node_ids:
        console.print("[yellow]No node IDs found in accounts.json. Will use random extension IDs.[/yellow]")
        # Ask for connections per account
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
    else:
        console.print("[green]Node IDs found in accounts.json. Will use existing node IDs.[/green]")
        connections_per_account = None  # Not needed when using node IDs
    
    # Count total connections
    total_connections = 0
    for acc in accounts_data:
        if "NodeIds" in acc and acc["NodeIds"]:
            total_connections += len(acc["NodeIds"])
        elif connections_per_account:
            total_connections += connections_per_account
    
    if total_connections > len(proxies) and len(proxies) > 0:
        console.print(f"[yellow]Warning: Not enough proxies for all connections. Some connections might share proxies.[/yellow]")
    
    # Create beautiful configuration display
    config_table = Table(title="ExeOS Bot Configuration", box=box.ROUNDED)
    config_table.add_column("Setting", style="cyan bold")
    config_table.add_column("Value", style="green")
    config_table.add_row("Accounts", str(len(accounts_data)))
    if has_node_ids:
        config_table.add_row("Connection mode", "Using saved node IDs")
    else:
        config_table.add_row("Connection mode", "Using random extension IDs")
        config_table.add_row("Connections per account", str(connections_per_account))
    config_table.add_row("Total connections", str(total_connections))
    config_table.add_row("Proxies available", str(len(proxies)))
    config_table.add_row("Ping frequency", "Every 30 seconds")
    console.print(config_table)
    
    # Confirm start
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
    timeout = aiohttp.ClientTimeout(total=60)  # Increased timeout
    connector = aiohttp.TCPConnector(limit=100, force_close=True)  # Increased connection limit
    
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        # Process each account
        tasks = []
        proxy_idx = 0  # Index for proxy rotation
        
        for acc_idx, acc_data in enumerate(accounts_data):
            email = acc_data["Email"]
            password = acc_data["Password"]
            
            # Add delay between account logins to avoid rate limiting
            if acc_idx > 0:
                console.print(f"[yellow]Waiting 15 seconds before starting next account...[/yellow]")
                await asyncio.sleep(15)
            
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
            
            # Check if this account has node IDs
            node_ids = acc_data.get("NodeIds", [])
            
            # If we have node IDs, use them. Otherwise, generate random extension IDs
            if node_ids:
                for node_id in node_ids:
                    # Get a proxy for this connection - don't test it now, just assign it
                    proxy = parse_proxy(proxies[proxy_idx % len(proxies)]) if proxies else None
                    proxy_idx += 1
                    
                    # Create connection object
                    connection = Connection(token, node_id, proxy)
                    account.connections.append(connection)
                    
                    # Start connection worker
                    tasks.append(asyncio.create_task(connection_worker(session, account, connection, proxies)))
                    await asyncio.sleep(1)  # Small delay between starting connections
            else:
                # Create connections for this account with random extension IDs
                for i in range(connections_per_account):
                    # Generate a new extension ID
                    extension_id = generate_extension_id()
                    
                    # Get a proxy for this connection - don't test it now, just assign it
                    proxy = parse_proxy(proxies[proxy_idx % len(proxies)]) if proxies else None
                    proxy_idx += 1
                    
                    # Create connection object
                    connection = Connection(token, extension_id, proxy)
                    account.connections.append(connection)
                    
                    # Start connection worker
                    tasks.append(asyncio.create_task(connection_worker(session, account, connection, proxies)))
                    await asyncio.sleep(1)  # Small delay between starting connections
            
            # Start account info updater
            tasks.append(asyncio.create_task(account_info_updater(session, account)))
        
        # Start status display updater
        tasks.append(asyncio.create_task(status_display_updater()))
        
        # Wait for all tasks to complete
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            # Handle cancellation more gracefully
            console.print("\n[yellow]Shutting down tasks...[/yellow]")
            for task in tasks:
                task.cancel()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Bot stopped by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {str(e)}[/red]")
