# SPDX-License-Identifier: GPL-3.0-or-later
"""Core domain layer of Ingetrazo Furniture Pro.

This package contains no Qt and no Ingetrazo imports: rules, data models,
validation, persistence formats and the pricing/cutting engines are plain
Python so they can be tested without a running CAD session.
"""
from .constants import PLUGIN_KEY, PLUGIN_VERSION

__all__ = ["PLUGIN_KEY", "PLUGIN_VERSION"]
