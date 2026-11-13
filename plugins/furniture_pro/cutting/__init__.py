# SPDX-License-Identifier: GPL-3.0-or-later
"""Cutting-plan facade.

The optimiser lives in :mod:`..manufacturing.optimizer` so the same engine
serves both the manufacturing tab and this module.  This package exists to
keep the architecture explicit and to give future algorithms (guillotine,
common-line, remnants) a home without changing callers.
"""
from ..manufacturing.optimizer import (BoardPlan, CutPlan, CutSettings,
                                       Placement, optimize, plan_from_dict,
                                       validate_plan)

__all__ = ["CutSettings", "CutPlan", "BoardPlan", "Placement", "optimize",
           "validate_plan", "plan_from_dict"]
