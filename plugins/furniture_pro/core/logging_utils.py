# SPDX-License-Identifier: GPL-3.0-or-later
"""Logging and crash-safe helper utilities for Furniture Pro.

Logs go to the user's Ingetrazo log directory and never raise if the location
is read-only.  A small rotating file handler keeps the plugin from filling the
disk over months of use.
"""
from __future__ import annotations

import logging
import os
import sys
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_NAME = "ingetrazo.plugins.furniture_pro"


def user_data_dir() -> Path:
    """Writable per-user directory for libraries, logs and exported drafts."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA")
                    or (Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME")
                    or (Path.home() / ".local" / "share"))
    return base / "ingetrazo" / "furniture_pro"


def log_dir() -> Path:
    """Prefer Ingetrazo's own log folder so diagnostics stay together."""
    try:
        from core.paths import user_log_dir          # type: ignore
        return Path(user_log_dir())
    except Exception:                                 # running outside Ingetrazo
        path = user_data_dir() / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path


_LOGGER: logging.Logger | None = None


def get_logger() -> logging.Logger:
    """Return the plugin logger, configuring a rotating file once."""
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER
    logger = logging.getLogger(LOG_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = True
    if not logger.handlers:
        try:
            path = log_dir() / "furniture-pro.log"
            handler = RotatingFileHandler(
                path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
            handler.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s: %(message)s"))
            logger.addHandler(handler)
        except OSError:
            # A read-only home must not keep the plugin from working.
            pass
    _LOGGER = logger
    return logger


def log_exception(context: str) -> str:
    """Log the active exception and return the traceback for a details pane."""
    text = traceback.format_exc()
    get_logger().error("%s\n%s", context, text)
    return text
