# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Ferramenta interativa de Conta-gotas / Amostrador de Materiais PBR do TrazoMob.

Permite clicar em qualquer face da cena no 3D do IngeTrazo para capturar o material
e selecioná-lo/editá-lo instantaneamente na janela de Materiais PBR.
"""
from __future__ import annotations

from typing import Optional
from pathlib import Path

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPen, QBrush, QPainter, QPolygonF, QCursor

from tools.base import Tool, ToolContext
from tools.paint import clicked_back_side
from core.group import effective_material
from core.materials import effective_attrs


def resolve_material_name_from_attrs(attrs: dict) -> str:
    """Extrai o nome do material de acordo com o padrão do MaterialEditorDialog."""
    if not attrs:
        return "Padrão (Sem Acabamento)"
    mat_name = attrs.get("mat")
    tex = attrs.get("texture")
    col = attrs.get("color")
    tex_path = tex.get("path") if (isinstance(tex, dict) and tex.get("path")) else None

    if mat_name:
        return str(mat_name)
    elif tex_path:
        return Path(tex_path).stem
    elif col:
        r, g, b = [int(max(0.0, min(1.0, c)) * 255) for c in col[:3]]
        return f"Cor #{r:02X}{g:02X}{b:02X}"
    return "Padrão (Sem Acabamento)"


class MaterialPickerTool(Tool):
    """Ferramenta de captura de materiais (conta-gotas 3D)."""

    name = "Conta-gotas de Materiais PBR"
    shortcut = None
    description = "Clique em qualquer face no modelo 3D para selecionar e editar seu material PBR."
    uses_snap = False

    def __init__(self, on_material_picked_callback=None):
        super().__init__()
        self.callback = on_material_picked_callback
        self._hovered_face = None
        self._hovered_group = None
        self._overlay_installed = False

    def on_activate(self, viewport) -> None:
        self._hovered_face = None
        self._hovered_group = None

        if hasattr(viewport, "setCursor"):
            viewport.setCursor(Qt.CrossCursor)

        if hasattr(viewport, "_ext_overlays") and self._draw_hover_overlay not in viewport._ext_overlays:
            viewport._ext_overlays.append(self._draw_hover_overlay)
            self._overlay_installed = True

        flash = getattr(viewport, "flash_status", None)
        if callable(flash):
            flash("🎨 Conta-gotas PBR ativo: Clique em uma face para carregar seu material")

    def on_deactivate(self, viewport) -> None:
        if hasattr(viewport, "_ext_overlays") and self._draw_hover_overlay in viewport._ext_overlays:
            viewport._ext_overlays.remove(self._draw_hover_overlay)
            self._overlay_installed = False

        if hasattr(viewport, "unsetCursor"):
            viewport.unsetCursor()
        viewport.set_hover(None)
        viewport.update()

    def on_hover(self, ctx: ToolContext) -> None:
        vp = ctx.viewport
        face, group = vp.pick_face_any(ctx.screen.x(), ctx.screen.y())
        self._hovered_face = face
        self._hovered_group = group
        vp.set_hover(face)
        vp.update()

    def on_click(self, ctx: ToolContext) -> None:
        vp = ctx.viewport
        face, group = vp.pick_face_any(ctx.screen.x(), ctx.screen.y())
        if face is None:
            return

        back_side = clicked_back_side(vp, face, group, ctx.screen.x(), ctx.screen.y())
        src = effective_attrs(face.attrs, effective_material(group))
        if back_side:
            back = face.attrs.get("back")
            if isinstance(back, dict):
                src = back
            elif back is not True:
                src = {}

        mat_name = resolve_material_name_from_attrs(src)

        flash = getattr(vp, "flash_status", None)
        if callable(flash):
            flash(f"Material selecionado: {mat_name}")

        if self.callback:
            self.callback(mat_name)
        else:
            win = vp.window() if hasattr(vp, "window") else None
            from ..ui.material_editor_dialog import open_material_editor
            open_material_editor(viewport=vp, parent=win, select_material=mat_name)

    def _draw_hover_overlay(self, viewport, painter: QPainter) -> None:
        """Destaca sutilmente a face sob o cursor com contorno amarelo suave."""
        if self._hovered_face is None or not hasattr(self._hovered_face, "vertices"):
            return

        pts_2d = []
        for v in self._hovered_face.vertices:
            px = viewport.world_to_pixel(v)
            if px is not None:
                pts_2d.append(QPointF(px[0], px[1]))
            else:
                return

        if len(pts_2d) >= 3:
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)
            pen = QPen(QColor(255, 215, 0, 220), 2.0, Qt.SolidLine)
            brush = QBrush(QColor(255, 215, 0, 50))
            painter.setPen(pen)
            painter.setBrush(brush)
            painter.drawPolygon(QPolygonF(pts_2d))
            painter.restore()
