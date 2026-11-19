# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Mixin para o painel lateral do TrazoMob especializado em alinhamento, distribuição e centralização 3D."""
from __future__ import annotations

from typing import Any
from PySide6.QtGui import QVector3D
from core.group import Group


class SidebarAlignMixin:
    """Encapsula as ferramentas de centralização relativa (XY, X, Y, Z) e distribuição uniforme no vão."""

    def _trigger_center(self, axes: str) -> None:
        """Executa a centralização entre os objetos atualmente selecionados."""
        scene = self._get_scene()
        sel = list(getattr(scene, "selection", [])) if scene else []
        sel_groups = [it for it in sel if isinstance(it, Group)]
        if len(sel_groups) < 2:
            return
        from ..interaction.align_tools import center_objects
        alvo = sel_groups[-1]
        base = sel_groups[0]
        vp = self._get_viewport()
        center_objects(alvo, base, axes=axes, viewport=vp)

    def _trigger_align(self, mode: str) -> None:
        """Executa um alinhamento direto (ex: apoiar sobre o topo) entre os objetos selecionados."""
        scene = self._get_scene()
        sel = list(getattr(scene, "selection", [])) if scene else []
        sel_groups = [it for it in sel if isinstance(it, Group)]
        if len(sel_groups) < 2:
            return
        from ..interaction.align_tools import align_objects
        alvo = sel_groups[-1]
        base = sel_groups[0]
        vp = self._get_viewport()
        align_objects(alvo, base, mode=mode, viewport=vp)

    def _distribute_selected_modules(self) -> None:
        """Distribui com precisão milimétrica 3 ou mais módulos selecionados ao longo do vão livre horizontal."""
        scene = self._get_scene()
        sel = list(getattr(scene, "selection", [])) if scene else []
        sel_groups = [it for it in sel if isinstance(it, Group)]
        if len(sel_groups) < 3:
            if hasattr(self, "lbl_status"):
                self.lbl_status.setText("ℹ️ Selecione 3 ou mais módulos com Ctrl para distribuir igualmente no vão.")
            return

        from ..interaction.align_tools import get_entity_world_bounds
        bounds_map = []
        for g in sel_groups:
            b = get_entity_world_bounds(g)
            if b:
                cx = (b[0] + b[1]) * 0.5
                bounds_map.append((cx, b[1] - b[0], g, b))

        if len(bounds_map) < 3:
            return

        # Ordena pelo centro horizontal X
        bounds_map.sort(key=lambda item: item[0])

        first_cx, first_w, first_g, first_b = bounds_map[0]
        last_cx, last_w, last_g, last_b = bounds_map[-1]

        # Vão total entre a extremidade esquerda do primeiro e a extremidade direita do último
        total_span = last_b[1] - first_b[0]
        sum_widths = sum(item[1] for item in bounds_map)
        num_gaps = len(bounds_map) - 1

        if num_gaps <= 0:
            return

        gap = max(0.0, (total_span - sum_widths) / num_gaps)

        from core.history import MoveGroupCommand, CompoundCommand
        cmds = []
        cur_left = first_b[0]

        for i, (cx, w, g, b) in enumerate(bounds_map):
            target_left = cur_left
            dx = target_left - b[0]
            if abs(dx) > 1e-4:
                cmds.append(MoveGroupCommand(g, QVector3D(dx, 0.0, 0.0)))
            cur_left += w + gap

        vp = self._get_viewport()
        if cmds and vp and hasattr(vp, "history"):
            compound = CompoundCommand(cmds)
            vp.history.execute(compound)
            if hasattr(vp, "notify_scene_changed"):
                vp.notify_scene_changed()
            vp.update()
            if hasattr(vp, "flash_status"):
                vp.flash_status(f"↔ {len(bounds_map)} módulos distribuídos com vão de {int(round(gap * 1000.0))} mm.")

