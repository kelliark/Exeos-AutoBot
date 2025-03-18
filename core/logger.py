import logging
import os
from datetime import datetime
from rich.console import Console

console = Console()

def setup_logger():
    """Setup the logger"""
    logger = logging.getLogger('exeos_bot')
    logger.setLevel(logging.INFO)
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Create file handler
    log_file = f"logs/exeos_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(file_handler)
    
    return logger

def log(level, message, account_info=""):
    """Log a message with rich formatting"""
    # Only log to console if it's an important message
    if level in ["SUCCESS", "ERROR"]:
        log_colors = {
            "CONNECT": "[green]",
            "LIVENESS": "[blue]",
            "STATS": "[magenta]",
            "POINTS": "[yellow]",
            "ERROR": "[red]",
            "INFO": "[cyan]",
            "SUCCESS": "[green]"
        }
        
        color = log_colors.get(level, "[white]")
        formatted_message = f"{color}[{level}]{account_info} {message}[/]"
        console.print(formatted_message)
    
    # Log to file via the logger
    logger = logging.getLogger('exeos_bot')
    logger_level = getattr(logging, level.upper()) if hasattr(logging, level.upper()) else logging.INFO
    logger.log(logger_level, f"{account_info} {message}")