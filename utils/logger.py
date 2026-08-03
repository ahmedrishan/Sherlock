"""Standardized logging utility for Sherlock.

Provides pre-configured loggers with standardized formatting.
"""

import logging
import sys
import config

def get_logger(name: str) -> logging.Logger:
    """Configures and returns a logger with a standard formatter.

    Args:
        name: The name of the logger (typically __name__).

    Returns:
        logging.Logger: A configured logger instance.
    """
    logger = logging.getLogger(name)
    
    # Prevent duplicate handlers if get_logger is called multiple times for same name
    if not logger.handlers:
        logger.setLevel(config.LOG_LEVEL)
        
        # Stream Handler for stdout
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(config.LOG_LEVEL)
        
        # Formatter
        formatter = logging.Formatter(config.LOG_FORMAT)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        
        # Prevent propagation to the root logger to avoid duplicate log lines
        logger.propagate = False
        
    return logger
