from datetime import datetime
from rich.panel import Panel
from rich.table import Table
from rich import box

def parse_proxy(proxy_string):
    """Parse proxy string to format usable by aiohttp"""
    if not proxy_string:
        return None
    
    # Make sure the proxy has a protocol
    if not (proxy_string.startswith('http://') or proxy_string.startswith('https://') or 
            proxy_string.startswith('socks5://') or proxy_string.startswith('socks4://')):
        # Default to http if no protocol specified
        proxy_string = 'http://' + proxy_string
    
    # Ensure the proxy string is correctly formatted
    if '@' not in proxy_string and ':' in proxy_string:
        # Check if it's just host:port
        host_port = proxy_string.split('://')[-1]
        if host_port.count(':') == 1:
            return proxy_string
    
    return proxy_string

async def verify_proxy_connection(session, proxy=None):
    """Verify a proxy connection by checking if it returns a different IP than our own"""
    try:
        # First get our own IP without proxy
        direct_ip = None
        try:
            direct_response = await session.get("https://api.ipify.org/?format=json", timeout=10)
            if direct_response.status == 200:
                direct_data = await direct_response.json()
                direct_ip = direct_data.get("ip")
        except Exception:
            pass
        
        # Then try to get IP through proxy
        if proxy:
            proxy_response = await session.get("https://api.ipify.org/?format=json", proxy=proxy, timeout=10)
            if proxy_response.status == 200:
                proxy_data = await proxy_response.json()
                proxy_ip = proxy_data.get("ip")
                
                # If proxy IP is different from direct IP, proxy is working
                if proxy_ip and proxy_ip != direct_ip:
                    return proxy_ip
        
        return None
    except Exception:
        return None

def format_duration(seconds):
    """Format duration in seconds to human-readable format"""
    # Convert string to int if needed
    if isinstance(seconds, str):
        try:
            seconds = int(seconds)
        except ValueError:
            seconds = 0
    
    # Fix for negative or extremely large seconds values
    if seconds < 0 or seconds > 315360000:  # 10 years
        return "0h 0m 0s"
        
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

def create_status_panel(accounts):
    """Create a beautiful status panel for all accounts and connections"""
    if not accounts:
        return Panel("No active accounts", title="ExeOS Bot Status", border_style="red")
    
    now = datetime.now().timestamp()  # Define 'now' here
    main_table = Table(box=box.ROUNDED, expand=True, show_header=False)
    main_table.add_column("Content", style="white")
    
    for idx, account in enumerate(accounts):  # 'account' is defined in this loop
        # Create account table
        account_table = Table(
            box=box.SIMPLE,
            expand=True,
            show_header=False,
            title=f"Account {idx+1}: {account.stats['firstName']} {account.stats['lastName']}",
            title_style="bold cyan"
        )
        account_table.add_column("Property", style="bright_blue")
        account_table.add_column("Value", style="white")
        
        # Add account info
        account_table.add_row("Email", account.email)
        account_table.add_row("Earnings Total", f"[yellow]{account.stats['earningsTotal']}[/yellow]")
        account_table.add_row("Connected Nodes", f"[green]{account.stats['connectedNodesCount']}[/green]")
        account_table.add_row("Connected Rewards", f"[yellow]{account.stats['connectedNodesRewards']}[/yellow]")
        
        # Calculate uptime
        uptime = now - account.stats["startTime"].timestamp()
        account_table.add_row("Uptime", format_duration(uptime))
        
        # Last updated
        last_updated = "Never" if not account.stats["lastUpdated"] else \
            datetime.fromtimestamp(account.stats["lastUpdated"]).strftime('%H:%M:%S')
        account_table.add_row("Last Updated", last_updated)
        
        # Add connections table - define it here within the account loop
        connections_table = Table(box=box.SIMPLE, expand=True, title="Active Connections", title_style="bold cyan")
        connections_table.add_column("ID", style="dim")
        connections_table.add_column("Connects", style="green")
        connections_table.add_column("Liveness", style="blue")
        connections_table.add_column("IP", style="bright_magenta")
        connections_table.add_column("Last Active", style="yellow")
        connections_table.add_column("Total Uptime", style="cyan")  # Add uptime column
        
        for conn in account.connections:
            # Fix for the timestamp issue
            if conn.last_connect:
                time_diff = now - conn.last_connect
                last_active = format_duration(time_diff) if time_diff > 0 else "Active now"
            else:
                last_active = "Never"
                
            # Display uptime from API if available
            uptime_display = format_duration(conn.uptime_total) if hasattr(conn, 'uptime_total') and conn.uptime_total else "N/A"
            
            connections_table.add_row(
                f"{conn.extension_id[:8]}...", 
                str(conn.connect_count),
                str(conn.liveness_count),
                str(conn.last_ip or "N/A"),
                last_active,
                uptime_display  # Add uptime column
            )
        
        # Add to main table
        main_table.add_row(account_table)
        main_table.add_row(connections_table)
        main_table.add_row("")  # Spacer
    
    return Panel(
        main_table, 
        title="ExeOS Bot Status", 
        border_style="bright_blue",
        box=box.ROUNDED
    )
