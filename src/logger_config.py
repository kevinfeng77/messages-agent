"""Logging configuration for the AI Text Agent"""

import os
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime


def setup_logging(log_level=logging.INFO, log_dir="logs", console_output=True, file_output=True):
    """
    Configure logging for the application
    
    Args:
        log_level: Logging level (default: INFO)
        log_dir: Directory for log files (default: "logs")
        console_output: Enable console output (default: True)
        file_output: Enable file output (default: True)
    """
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler - rotating logs
    if file_output:
        log_filename = log_path / f"ai_text_agent_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_filename,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        # Error file handler - only errors and above
        error_log_filename = log_path / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_filename,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)
    
    # Log startup
    logging.info("="*60)
    logging.info("AI Text Agent Starting")
    logging.info(f"Log Level: {logging.getLevelName(log_level)}")
    logging.info(f"Log Directory: {log_path.absolute()}")
    logging.info("="*60)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name"""
    return logging.getLogger(name)