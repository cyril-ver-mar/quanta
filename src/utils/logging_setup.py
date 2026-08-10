"""L1 — simple file logger."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from src.utils.paths import LOG_DIR, ensure_runtime_dirs

_configured = False


def get_logger(name: str = "quanta") -> logging.Logger:
    global _configured
    logger = logging.getLogger(name)
    if _configured:
        return logger
    ensure_runtime_dirs()
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(LOG_DIR / "quanta.log", maxBytes=2_000_000, backupCount=3)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    _configured = True
    return logger
