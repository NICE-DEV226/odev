"""
odev.logger — Logging fichier simple (rotatif léger), n'interfère jamais avec le TUI.
"""

import logging
from logging.handlers import RotatingFileHandler
from .config import LOG_FILE


def get_logger() -> logging.Logger:
    logger = logging.getLogger("odev")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    return logger


log = get_logger()
