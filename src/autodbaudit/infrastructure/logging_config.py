"""
Logging configuration module.

Provides structured logging with colored console output and file output.
"""

import logging
import sys
from pathlib import Path


# ANSI color codes for Windows 10+ and Unix terminals
class Colors:
    """ANSI escape sequences for terminal colors."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright colors
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    
    # Background colors
    BG_RED = "\033[41m"
    BG_YELLOW = "\033[43m"


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter that adds colors to log levels.
    
    Colors:
        DEBUG    - Dim/Gray
        INFO     - Cyan
        WARNING  - Yellow
        ERROR    - Red
        CRITICAL - Bold Red on background
    """
    
    LEVEL_COLORS = {
        logging.DEBUG: Colors.DIM + Colors.WHITE,
        logging.INFO: Colors.CYAN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.BRIGHT_RED,
        logging.CRITICAL: Colors.BOLD + Colors.WHITE + Colors.BG_RED,
    }
    
    def __init__(self, fmt: str, datefmt: str = None, use_colors: bool = True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors
    
    def format(self, record: logging.LogRecord) -> str:
        if not self.use_colors:
            return super().format(record)
        
        # Save original levelname
        original_levelname = record.levelname
        original_msg = record.msg
        
        # Colorize level name
        color = self.LEVEL_COLORS.get(record.levelno, Colors.WHITE)
        record.levelname = f"{color}{record.levelname:8}{Colors.RESET}"
        
        # Colorize the module/logger name
        record.name = f"{Colors.DIM}{record.name}{Colors.RESET}"
        
        # Format the record
        result = super().format(record)
        
        # Restore original values (for other handlers like file)
        record.levelname = original_levelname
        record.msg = original_msg
        
        return result


class PlainFormatter(logging.Formatter):
    """Non-colored formatter for file output."""


def _enable_windows_ansi():
    """Enable ANSI escape sequences on Windows."""
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # Enable virtual terminal processing
            kernel32.SetConsoleMode(
                kernel32.GetStdHandle(-11),  # STD_OUTPUT_HANDLE
                7  # ENABLE_PROCESSED_OUTPUT | ENABLE_WRAP_AT_EOL_OUTPUT | ENABLE_VIRTUAL_TERMINAL_PROCESSING
            )
        except Exception:
            pass  # Fallback to no colors on older Windows


def setup_logging(level: int = logging.INFO, log_file: str | None = None):
    """
    Configure application-wide logging with colored output.
    
    Args:
        level: Logging level (logging.DEBUG, logging.INFO, etc.)
        log_file: Optional path to log file
    """
    # Enable ANSI on Windows
    _enable_windows_ansi()
    
    # Colored console formatter
    console_formatter = ColoredFormatter(
        fmt='[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
        datefmt='%H:%M:%S',
        use_colors=True
    )
    
    # Plain file formatter (no colors, full timestamp)
    file_formatter = PlainFormatter(
        fmt='[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(level)
    
    handlers = [console_handler]
    
    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)  # Always debug to file
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG,  # Capture all levels, handlers filter
        handlers=handlers,
        force=True
    )
    
    # Reduce noise from libraries
    logging.getLogger('pyodbc').setLevel(logging.WARNING)
    logging.getLogger('openpyxl').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("AutoDBAudit Logging Initialized")
    logger.debug("Log level: %s", logging.getLevelName(level))
    if log_file:
        logger.debug("Log file: %s", log_file)
    logger.info("=" * 50)
