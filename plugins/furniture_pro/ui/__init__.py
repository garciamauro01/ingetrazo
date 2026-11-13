# SPDX-License-Identifier: GPL-3.0-or-later
"""Qt user interface for Furniture Pro.

Imports are kept lazy where a module pulls in the whole dialog stack, so the
plugin can load its side panel without constructing every widget.
"""
from .panel import FurniturePanel

__all__ = ["FurniturePanel"]
