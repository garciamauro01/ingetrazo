# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Diálogo para mapear cada material/cor/textura de um objeto para presets de render."""
from __future__ import annotations

from typing import Any, Dict

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..domain.render_materials import (
    RENDER_PRESETS,
    extract_group_material_slots,
    get_group_render_materials,
    set_group_render_materials,
)


class RenderMaterialsDialog(QDialog):
    """Lista os materiais/cores/texturas encontrados no objeto e permite escolher o preset de render."""

    def __init__(self, group: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._group = group
        self.setWindowTitle(f"Acabamentos de Render — {getattr(group, 'name', 'Objeto')}")
        self.setMinimumWidth(520)
        self.setMinimumHeight(360)

        root = QVBoxLayout(self)
        info = QLabel(
            "Defina como cada material/cor/textura deste objeto será renderizado no Blender "
            "(presets procedurais sem necessidade de textura externa):"
        )
        info.setWordWrap(True)
        root.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        form = QVBoxLayout(container)
        form.setAlignment(Qt.AlignTop)

        self._combos: Dict[str, QComboBox] = {}
        slots = extract_group_material_slots(group)
        saved = get_group_render_materials(group)

        if not slots:
            form.addWidget(QLabel("Nenhum material ou face encontrado neste objeto."))
        else:
            for slot in slots:
                row = QHBoxLayout()
                swatch = QLabel()
                swatch.setFixedSize(24, 24)
                col = slot.get("color")
                if col:
                    qc = QColor.fromRgbF(col[0], col[1], col[2])
                    pix = QPixmap(24, 24)
                    pix.fill(qc)
                    swatch.setPixmap(pix)
                else:
                    swatch.setText("🖼")
                    swatch.setAlignment(Qt.AlignCenter)
                swatch.setStyleSheet("border: 1px solid #64748B; border-radius: 3px;")
                row.addWidget(swatch)

                lbl = QLabel(f"{slot['label']}  ({slot['face_count']} faces)")
                lbl.setMinimumWidth(210)
                row.addWidget(lbl, 1)

                cb = QComboBox()
                for pid, pname in RENDER_PRESETS:
                    cb.addItem(pname, pid)
                cur_preset = saved.get(slot["key"], "original")
                idx = cb.findData(cur_preset)
                if idx >= 0:
                    cb.setCurrentIndex(idx)
                row.addWidget(cb)

                self._combos[slot["key"]] = cb
                form.addLayout(row)

        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _on_accept(self) -> None:
        mapping = {
            key: str(cb.currentData())
            for key, cb in self._combos.items()
        }
        set_group_render_materials(self._group, mapping)
        self.accept()
