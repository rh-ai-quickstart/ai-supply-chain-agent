"""Centralized logging configuration for the Flask API + ingestion process.

Log format (stdout):  ``<timestamp> <file>:<logtype>: <message>``

Usage::

    from logging_config import setup_logging, getLogger
    setup_logging()
    logger = getLogger(__name__)
"""

from __future__ import annotations

import logging
import sys


class _ConsoleFormatter(logging.Formatter):
    """Log every record as ``YYYY-MM-DD HH:MM:SS <file>:<logtype>: <message>``."""

    def __init__(self) -> None:
        super().__init__(datefmt="%Y-%m-%d %H:%M:%S")

    def format(self, record: logging.LogRecord) -> str:
        ts = self.formatTime(record, self.datefmt)
        file_part = record.name.rpartition(".")[-1]
        logtype = record.levelname.lower()
        msg = record.getMessage()
        return f"{ts} {file_part}:{logtype}: {msg}"


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the root logger with a single console handler.

    Call once from the entry point.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_ConsoleFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        root.addHandler(handler)


def getLogger(name: str) -> logging.Logger:
    """Return a logger for *name* — drop-in for ``logging.getLogger``."""
    return logging.getLogger(name)
