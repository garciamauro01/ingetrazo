# SPDX-License-Identifier: GPL-3.0-or-later
"""Test bootstrap for the Furniture Pro plugin suite.

The plugin is imported as a package (``plugins.furniture_pro``) so relative
imports inside it resolve exactly as they do when Ingetrazo loads the package
by file path.  Qt runs offscreen: no window server is needed.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Keep the developer's real libraries out of the suite.
import tempfile  # noqa: E402

_DATA = tempfile.mkdtemp(prefix="furniture-pro-tests-")
os.environ["XDG_DATA_HOME"] = _DATA
if sys.platform == "win32":
    os.environ["APPDATA"] = _DATA

from PySide6.QtWidgets import QApplication  # noqa: E402

if QApplication.instance() is None:
    QApplication(sys.argv[:1])
