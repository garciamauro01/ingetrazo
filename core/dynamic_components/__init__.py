# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
"""Módulo nativo de Componentes Dinâmicos do IngeTrazo."""
from __future__ import annotations

from .engine import SafeExpressionEvaluator
from .model import (
    STANDARD_ATTRIBUTES,
    apply_dc_geometry,
    apply_dc_material,
    ensure_dc_data,
    evaluate_dc,
    get_dc_data,
    is_dc_copy,
)
from .report import DCReportDialog
from .skp_bridge import convert_skp_dynamic_attributes
from .tool_interact import InteractTool
from .ui import ComponentAttributesDialog, ComponentOptionsDialog

__all__ = [
    "STANDARD_ATTRIBUTES",
    "SafeExpressionEvaluator",
    "get_dc_data",
    "ensure_dc_data",
    "evaluate_dc",
    "apply_dc_geometry",
    "apply_dc_material",
    "is_dc_copy",
    "convert_skp_dynamic_attributes",
    "ComponentAttributesDialog",
    "ComponentOptionsDialog",
    "InteractTool",
    "DCReportDialog",
]
