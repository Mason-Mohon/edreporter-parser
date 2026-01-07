"""Logging setup for EdReporter Flask application."""

import logging
import sys
from datetime import datetime


def setup_logger(name='edreporter', level=logging.DEBUG):
    """Set up logger with console output.
    
    Args:
        name: Logger name
        level: Logging level
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers = []
    
    # Console handler with formatting
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Detailed formatter
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s %(name)s.%(module)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


# Create default logger
logger = setup_logger()
