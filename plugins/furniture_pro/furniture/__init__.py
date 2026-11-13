# SPDX-License-Identifier: GPL-3.0-or-later
"""Parametric furniture catalogue and construction rules."""
from .generator import ModuleBuilder, build_module
from .templates import (ModuleTemplate, categories, template_by_type,
                        templates)

__all__ = ["ModuleBuilder", "build_module", "ModuleTemplate", "templates",
           "template_by_type", "categories"]
