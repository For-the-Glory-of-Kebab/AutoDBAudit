"""
Logging configuration module.

Provides structured logging with file and console output.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logging(level: int = logging.INFO, log_file: str | None = None):
    """
    Configure application-wide logging.
    
    Args:
        level: Logging level (logging.DEBUG, logging.INFO, etc.)
        log_file: Optional path to log file
    """
    # Create formatter
    formatter = logging.Formatter(
        fmt='[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    
    handlers = [console_handler]
    
    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
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
    logger.info("=" * 60)
    logger.info("AutoDBAudit Logging Initialized")
    logger.info(f"Log level: {logging.getLevelName(level)}")
    if log_file:
        logger.info(f"Log file: {log_file}")
    logger.info("=" * 60)
