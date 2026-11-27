# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""TrazoMob plugin for IngeTrazo — dynamic cabinetry components and cut plan.

Provides:
1. Dynamic Parametric Modules (TrazoMob-style):
   - Base cabinets, drawer banks, wall cabinets, and open cubbies;
   - Real-time dynamic selection and editing (resize without distorting boards);
   - Quick dimensional adjustments (+/- 50mm, +/- 100mm);
2. Smart board extraction (length, width, thickness, edge banding, and grain direction);
3. Direct export to TrazoMob (Ctrl+V copy, CSV, and JSON);
4. Dynamic interactivity: open/close doors and drawers by clicking in 3D.

This module is the public facade of the plugin: it exposes the API (``__all__``),
the tool classes discovered by the IngeTrazo loader, and the ``setup`` entry
point. The body of ``setup`` lives in :mod:`bootstrap` and the context menu in
:mod:`context_menu`, keeping this file concise.
"""
from __future__ import annotations

import logging

from tools.base import Tool

from .builders.cabinet import (
    CabinetBuilder,
    RotateTrazoMobModuleCommand,
    _make_board_mesh,
    build_chapa,
    build_chapa_mm,
    create_board_group,
)
from .domain.catalog import MODULE_CATALOG
from .integrations import platform as host
from .interaction.align_tool_interactive import AlignSnapTool
from .interaction.interact import (
    CabinetInteract,
)
from .interaction.interact import (
    CabinetInteractTool as _CabinetInteractToolImpl,
)
from .interaction.material_picker_tool import MaterialPickerTool
from .production.cut_plan_viewer import CutPlanViewerDialog
from .production.export import (
    export_trazomob_csv,
    export_trazomob_json,
    format_trazomob_text,
)
from .production.parts import _get_entity_bbox, extract_parts, group_similar_parts
from .ui.icons import (
    get_module_thumbnail,
    make_cabinet_icon,
    make_cut_plan_icon,
    make_cutlist_icon,
    make_interact_icon,
    make_perfil_diagram_pixmap,
    make_rotate_ccw_icon,
    make_rotate_cw_icon,
    make_ruler_icon,
    make_trazomob_icon,
)
from .ui.module_dialog import TrazoMobDialog
from .ui.ruler_editor_dialog import RulerEditorDialog
from .ui.sidebar_panel import TrazoMobSidebarPanel

logger = logging.getLogger("trazomob")


class TrazoMobTool(Tool):
    """Extensions menu tool to open TrazoMob."""
    name = "TrazoMob"
    shortcut = None
    description = "Biblioteca de módulos paramétricos de marcenaria e gerador de corte para TrazoMob."
    uses_snap = False

    def on_activate(self, viewport) -> None:
        vp = host.active_viewport(viewport=viewport)
        win = host.window_of(viewport=vp)
        dlg = getattr(win, "_trazomob_dialog", None)
        if dlg is None or not dlg.isVisible():
            dlg = TrazoMobDialog(vp, parent=win)
            if win is not None:
                setattr(win, "_trazomob_dialog", dlg)
            dlg.show()
        else:
            if hasattr(dlg, "sync_to_active_document"):
                dlg.sync_to_active_document(vp)
            dlg.raise_()
            dlg.activateWindow()

    def on_deactivate(self, viewport) -> None:
        pass


class CabinetInteractTool(_CabinetInteractToolImpl):
    """Interactive click tool to open and close doors and drawers in 3D."""
    pass


def setup(app) -> None:
    """Initializes the TrazoMob plugin by registering the sidebar, toolbar, and context menus."""
    from .bootstrap import install

    install(app, TrazoMobTool, CabinetInteractTool)


__all__ = [
    "CabinetBuilder",
    "RotateTrazoMobModuleCommand",
    "_make_board_mesh",
    "create_board_group",
    "build_chapa",
    "build_chapa_mm",
    "MODULE_CATALOG",
    "CabinetInteract",
    "CabinetInteractTool",
    "AlignSnapTool",
    "MaterialPickerTool",
    "_get_entity_bbox",
    "extract_parts",
    "group_similar_parts",
    "format_trazomob_text",
    "export_trazomob_csv",
    "export_trazomob_json",
    "TrazoMobDialog",
    "TrazoMobSidebarPanel",
    "RulerEditorDialog",
    "get_module_thumbnail",
    "make_trazomob_icon",
    "make_cabinet_icon",
    "make_cutlist_icon",
    "make_interact_icon",
    "make_rotate_ccw_icon",
    "make_rotate_cw_icon",
    "make_cut_plan_icon",
    "make_perfil_diagram_pixmap",
    "make_ruler_icon",
    "CutPlanViewerDialog",
    "TrazoMobTool",
    "setup",
]
