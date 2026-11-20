# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""TrazoMob plugin for IngeTrazo — componentes dinâmicos de marcenaria e plano de corte.

Fornece:
1. Módulos Paramétricos Dinâmicos (estilo TrazoMob):
   - Balcões inferiores, gaveteiros, armários aéreos e nichos;
   - Seleção e edição dinâmica em tempo real (redimensionar sem deformar chapas);
   - Ajustes dimensionais rápidos (+/- 50mm, +/- 100mm);
2. Extração inteligente de chapas (comprimento, largura, espessura, fitas e veio);
3. Envio direto para o TrazoMob (cópia com Ctrl+V, CSV e JSON);
4. Interatividade dinâmica: abrir/fechar portas e gavetas com clique no 3D.

Este módulo é a fachada pública do plugin: expõe a API (``__all__``), as classes
de ferramenta descobertas pelo carregador do IngeTrazo e o ponto de entrada
``setup``. O corpo do ``setup`` vive em :mod:`bootstrap` e o menu de contexto em
:mod:`context_menu`, para manter este arquivo enxuto.
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
from .interaction.interact import (
    CabinetInteract,
    CabinetInteractTool as _CabinetInteractToolImpl,
)
from .interaction.align_tool_interactive import AlignSnapTool
from .interaction.material_picker_tool import MaterialPickerTool
from .production.cut_plan_viewer import CutPlanViewerDialog
from .production.export import export_trazomob_csv, export_trazomob_json, format_trazomob_text
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
    """Ferramenta do menu Extensões para abrir o TrazoMob."""
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
    """Ferramenta de clique interativo para abrir e fechar portas e gavetas no 3D."""
    pass


def setup(app) -> None:
    """Inicializa o plugin TrazoMob registrando barra lateral, toolbar e menus de contexto."""
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
