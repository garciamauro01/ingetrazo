# SPDX-License-Identifier: GPL-3.0-or-later
"""Ferramenta e Diálogo de Tintas & Cores de Parede do TrazoMob."""
from __future__ import annotations

from typing import Optional, Dict, Any, List
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QPixmap, QPainter, QBrush, QPen, QCursor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QGridLayout, QScrollArea, QColorDialog,
    QFrame, QMessageBox
)

from core.mesh import Face
from core.group import Group
from core.history import Command
from tools.base import Tool, ToolContext

from ..wall.paint_catalog import WALL_PAINT_CATALOG


class SetWallFaceColorCommand(Command):
    """Comando reversível para pintar uma ou todas as faces de uma parede."""

    def __init__(self, target_group: Group, face_indices: List[int], new_color: tuple[float, float, float], paint_name: str):
        self.target_group = target_group
        self.face_indices = face_indices
        self.new_color = new_color
        self.paint_name = paint_name
        self.old_colors: List[Any] = []
        self.old_names: List[Any] = []

    def do(self, scene) -> None:
        mesh = getattr(self.target_group, "mesh", None)
        if not mesh or not hasattr(mesh, "faces"):
            return
        self.old_colors.clear()
        self.old_names.clear()

        # Guarda cores antigas para undo
        for idx in self.face_indices:
            if 0 <= idx < len(mesh.faces):
                f = mesh.faces[idx]
                self.old_colors.append(f.attrs.get("color"))
                self.old_names.append(f.attrs.get("paint_name"))
                f.attrs["color"] = self.new_color
                f.attrs["paint_name"] = self.paint_name

        if getattr(self.target_group, "ext", None) is not None:
            self.target_group.ext["wall_color"] = self.new_color
            self.target_group.ext["wall_paint_name"] = self.paint_name

        scene.version += 1

    def undo(self, scene) -> None:
        mesh = getattr(self.target_group, "mesh", None)
        if not mesh or not hasattr(mesh, "faces"):
            return
        for i, idx in enumerate(self.face_indices):
            if 0 <= idx < len(mesh.faces) and i < len(self.old_colors):
                f = mesh.faces[idx]
                if self.old_colors[i] is not None:
                    f.attrs["color"] = self.old_colors[i]
                else:
                    f.attrs.pop("color", None)
                if self.old_names[i] is not None:
                    f.attrs["paint_name"] = self.old_names[i]
                else:
                    f.attrs.pop("paint_name", None)
        scene.version += 1


class WallPaintPaletteDialog(QDialog):
    """Diálogo visual de seleção de tintas de interiores."""

    def __init__(self, on_color_selected=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎨 TrazoMob — Paleta de Tintas & Cores de Parede")
        self.setFixedSize(540, 480)
        self.on_color_selected = on_color_selected
        self._selected_color: tuple[float, float, float] = (0.937, 0.925, 0.882) # Algodão Egípcio
        self._selected_name: str = "Algodão Egípcio"

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        lbl_desc = QLabel(
            "<b>Escolha uma tinta de parede para pintar faces ou ambientes inteiros:</b><br>"
            "<span style='color: palette(text); font-size: 11px;'>"
            "A cor selecionada interage fisicamente com a iluminação do render foto-realista.</span>"
        )
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

        tabs = QTabWidget()
        for cat_name, paints in WALL_PAINT_CATALOG.items():
            tab_widget = QWidget()
            tab_layout = QVBoxLayout(tab_widget)
            tab_layout.setContentsMargins(6, 6, 6, 6)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)

            content = QWidget()
            grid = QGridLayout(content)
            grid.setSpacing(8)

            for i, p in enumerate(paints):
                btn = QPushButton()
                btn.setCursor(Qt.PointingHandCursor)
                btn.setFixedHeight(54)

                hex_col = p["hex"]
                name = p["nome"]
                tipo = p.get("tipo", "fosco").title()

                # Gera amostra com swatch e texto
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {hex_col};
                        border: 2px solid #94A3B8;
                        border-radius: 6px;
                        text-align: left;
                        padding-left: 12px;
                        font-weight: bold;
                        font-size: 11px;
                        color: {"#0F172A" if QColor(hex_col).lightness() > 140 else "#FFFFFF"};
                    }}
                    QPushButton:hover {{
                        border: 2.5px solid #2563EB;
                    }}
                """)
                btn.setText(f"{name} ({tipo})")
                btn.clicked.connect(lambda _, paint=p: self._pick_preset(paint))

                row = i // 2
                col = i % 2
                grid.addWidget(btn, row, col)

            scroll.setWidget(content)
            tab_layout.addWidget(scroll)
            tabs.addTab(tab_widget, cat_name)

        layout.addWidget(tabs, 1)

        # Barra inferior com Cor Personalizada e Confirmação
        h_bot = QHBoxLayout()
        btn_custom = QPushButton("🎨 Cor Personalizada...")
        btn_custom.clicked.connect(self._choose_custom_color)
        h_bot.addWidget(btn_custom)

        h_bot.addStretch()

        self.btn_apply = QPushButton("Aplicar Tinta")
        self.btn_apply.setStyleSheet("background-color: #16A34A; color: white; font-weight: bold; padding: 6px 16px; border-radius: 4px;")
        self.btn_apply.clicked.connect(self.accept)
        h_bot.addWidget(self.btn_apply)

        layout.addLayout(h_bot)

    def _pick_preset(self, paint: dict):
        self._selected_color = paint["rgb"]
        self._selected_name = paint["nome"]
        if callable(self.on_color_selected):
            self.on_color_selected(self._selected_color, self._selected_name)
        self.accept()

    def _choose_custom_color(self):
        col = QColorDialog.getColor(QColor.fromRgbF(*self._selected_color), self, "Selecionar Cor da Parede")
        if col.isValid():
            self._selected_color = (col.redF(), col.greenF(), col.blueF())
            self._selected_name = f"Personalizado {col.name().upper()}"
            if callable(self.on_color_selected):
                self.on_color_selected(self._selected_color, self._selected_name)
            self.accept()

    def get_color(self) -> tuple[tuple[float, float, float], str]:
        return self._selected_color, self._selected_name


class WallPaintTool(Tool):
    """Ferramenta interativa de Pintura de Paredes e Pisos no Viewport."""

    name = "Pintar Paredes"
    shortcut = "P"
    description = "Clique em uma parede ou piso para pintar com a cor selecionada. Alt+Clique abre a paleta."

    def __init__(self, color: tuple[float, float, float] = (0.937, 0.925, 0.882), paint_name: str = "Algodão Egípcio"):
        super().__init__()
        self.color = color
        self.paint_name = paint_name

    def on_activate(self, viewport) -> None:
        if hasattr(viewport, "status_message"):
            viewport.status_message(f"🎨 Ferramenta Pintar Parede Ativa: [{self.paint_name}]. Clique na parede ou piso.")

    def on_deactivate(self, viewport) -> None:
        if hasattr(viewport, "status_message"):
            viewport.status_message("")

    def on_click(self, ctx: ToolContext) -> None:
        if ctx.modifiers & Qt.AltModifier:
            # Abre paleta de tintas ao segurar Alt
            dlg = WallPaintPaletteDialog(on_color_selected=self._update_color, parent=ctx.viewport)
            dlg.exec()
            return

        # Localiza o objeto clicado
        picked = ctx.viewport.pick_object(ctx.event.position().toPoint())
        if not picked:
            return

        target_group = None
        if isinstance(picked, Group):
            target_group = picked
        elif hasattr(picked, "group") and picked.group:
            target_group = picked.group

        if not target_group:
            return

        mesh = getattr(target_group, "mesh", None)
        if not mesh or not hasattr(mesh, "faces") or not mesh.faces:
            return

        # Pinta todas as faces do grupo da parede/piso
        all_indices = list(range(len(mesh.faces)))
        cmd = SetWallFaceColorCommand(target_group, all_indices, self.color, self.paint_name)
        ctx.viewport.history.execute(cmd)
        ctx.viewport.update()
        if hasattr(ctx.viewport, "status_message"):
            ctx.viewport.status_message(f"✅ Parede '{target_group.name}' pintada com {self.paint_name}.")

    def _update_color(self, color, name):
        self.color = color
        self.paint_name = name
