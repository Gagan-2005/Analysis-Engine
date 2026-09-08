import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

def setup_logger(name: str, log_file: Optional[Path] = None, level: int = logging.INFO) -> logging.Logger:
    """
    Sets up a structured, production-ready logger for the application.
    
    Args:
        name: The name of the logger (usually __name__).
        log_file: Optional path to a log file. Defaults to logs/engine.log.
        level: The logging level to use (default: logging.INFO).
        
    Returns:
        A configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    logger.propagate = False
    
    if logger.handlers:
        return logger
        
    logger.setLevel(level)

    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)s | %(filename)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file is None:
        log_file = Path(__file__).parent.parent / "logs" / "engine.log"
        
    log_file.parent.mkdir(parents=True, exist_ok=True)
        
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8',
        delay=True
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
