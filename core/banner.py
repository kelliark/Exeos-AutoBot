from rich.console import Console
from rich.panel import Panel
from rich import box

console = Console()

def display_banner():
    """Display the ExeOS Bot banner with improved styling"""
    banner = """
    ███████╗██╗  ██╗███████╗ ██████╗ ███████╗    ██████╗  ██████╗ ████████╗
    ██╔════╝╚██╗██╔╝██╔════╝██╔═══██╗██╔════╝    ██╔══██╗██╔═══██╗╚══██╔══╝
    █████╗   ╚███╔╝ █████╗  ██║   ██║███████╗    ██████╔╝██║   ██║   ██║   
    ██╔══╝   ██╔██╗ ██╔══╝  ██║   ██║╚════██║    ██╔══██╗██║   ██║   ██║   
    ███████╗██╔╝ ██╗███████╗╚██████╔╝███████║    ██████╔╝╚██████╔╝   ██║   
    ╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚══════╝    ╚═════╝  ╚═════╝    ╚═╝   
    
                       [bold cyan]Exeos Auto Bot[/bold cyan]
                       [green]Developed by Kelliark[/green]
    """
    console.print(Panel(banner, border_style="bright_blue", box=box.DOUBLE))