"""
logging_config.py
=================
Central logging configuration for the FRI project.
Every script imports this to get consistent logging.

Project: forecast-reliability-indicator (FRI)
Author:  Dhan Prasad Ghale
Date:    April 2026
"""

import logging
from pathlib import Path
from datetime import datetime


def get_logger(script_name: str) -> logging.Logger:
    """
    Create and return a logger for a given script.

    Each script gets:
      - A log file in logs/ named after the script
      - Console output for real time monitoring
      - Timestamps on every line

    Args:
        script_name: Name of the calling script
                     e.g. "c1_01_download_aemo_nem"

    Returns:
        Configured logger instance
    """

    # Create logs directory if it does not exist
    logs_dir = Path(__file__).resolve().parent.parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Log file path includes script name and date
    log_date = datetime.now().strftime("%Y%m%d")
    log_file = logs_dir / f"{script_name}_{log_date}.log"

    # Create logger
    logger = logging.getLogger(script_name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if logger already exists
    if logger.handlers:
        return logger

    # Format for all log messages
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler — writes to logs/scriptname_date.log
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # Console handler — prints to terminal
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Attach handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info(f"Logger started for: {script_name}")
    logger.info(f"Log file: {log_file}")

    return logger
