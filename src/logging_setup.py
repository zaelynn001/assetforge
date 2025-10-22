# Rev 1.0.0

"""Logging setup helpers for AssetForge."""
from __future__ import annotations
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Tuple

from src.utils.paths import LOG_DIR, ensure_runtime_dirs


def _make_handlers(logfile: Path) -> Tuple[logging.Handler, logging.Handler]:
    file_handler = RotatingFileHandler(
        logfile,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    file_handler.setFormatter(formatter)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    return file_handler, console


def setup_logging(name: str = "assetforge") -> logging.Logger:
    """Configure logging for the application and return the app logger."""
    ensure_runtime_dirs()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logfile = LOG_DIR / f"{name}.log"

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        file_handler, console = _make_handlers(logfile)
        logger.addHandler(file_handler)
        logger.addHandler(console)

    logger.debug("Logging ready at %s", logfile)
    return logger
