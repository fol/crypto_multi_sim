import logging
import os
import sys
from typing import Optional
import pathlib

# Create a custom formatter
class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to log levels"""
    
    # Row counter
    row_counter = 0
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Make path relative to project root
        if hasattr(record, 'pathname') and record.pathname:
            try:
                # Get the project root directory
                project_root = pathlib.Path(__file__).parent.parent
                # Make the path relative
                relative_path = pathlib.Path(record.pathname).relative_to(project_root)
                record.pathname = str(relative_path)
            except ValueError:
                # If we can't make it relative, keep the original path
                pass
        
        # Add color to the level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        # Add color to the entire message including filename and line number
        if levelname in self.COLORS:
            # Colorize the entire log message
            original_message = super().format(record)
            colored_message = f"{self.COLORS[levelname]}{original_message}{self.COLORS['RESET']}"
            return colored_message
        
        return super().format(record)

def setup_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Set up a logger with the specified name and level.
    
    Args:
        name: Name of the logger
        level: Logging level (default: None, which means use global level from LOG_LEVEL env var or INFO)
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    
    # Determine log level
    if level is not None:
        # Use explicitly provided level
        logger_level = level
    else:
        # Get level from environment variable or default to INFO
        log_level_str = os.environ.get('LOG_LEVEL', 'INFO').upper()
        logger_level = getattr(logging, log_level_str, logging.INFO)
    
    logger.setLevel(logger_level)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logger_level)
    
    # Create formatter
    formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Name of the logger
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)