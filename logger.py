import logging
import sys
import os
from logging.handlers import RotatingFileHandler


def setup_logger(name="webwoelfe", log_file="webwoelfe.log", level=logging.INFO):
    """
    Sets up a logger with console and file handlers.
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Check if handlers already exist to avoid duplicates
    if logger.handlers:
        return logger

    # Create formatters
    # Detailed format: Time [Level] [Module:Function:Line] Message
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(module)s:%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%H:%M:%S",
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    try:
        # Ensure directory exists if path is used
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to setup file logging: {e}")

    return logger


# Initialize global logger
logger = setup_logger()
