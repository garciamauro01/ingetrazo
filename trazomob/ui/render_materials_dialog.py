# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Diálogo para mapear cada material/cor/textura de um objeto para presets de render."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..domain.i18n import tr
from ..domain.render_materials import (
    RENDER_PRESETS,
    extract_group_material_slots,
    face_material_key,
    get_group_render_materials,
    set_group_render_materials,
)


class _ViewportEyedropperFilter(QObject):
    """Captura um único clique no viewport 3D para identificar o material sob o cursor."""

    def __init__(self, dialog: "RenderMaterialsDialog", viewport: Any) -> None:
        super().__init__(dialog)
        self._dialog = dialog
        self._viewport = viewport

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        etype = event.type()
        if etype == QEvent.MouseButtonPress:
            btn = event.button()
            if btn == Qt.LeftButton:
                pos = event.position().toPoint()
                self._dialog._finish_eyedropper(pos.x(), pos.y())
                return True
            if btn == Qt.RightButton:
                self._dialog._cancel_eyedropper()
                return True
        elif etype == QEvent.KeyPress and event.key() == Qt.Key_Escape:
            self._dialog._cancel_eyedropper()
            return True
        return False


class RenderMaterialsDialog(QDialog):
    """Lista os materiais/cores/texturas encontrados no objeto e permite escolher o preset de render."""

    def __init__(
        self,
        group: Any,
        parent: QWidget | None = None,
        viewport: Any = None,
    ) -> None:
        super().__init__(parent)
        self._group = group
        self._viewport = viewport
        self._eyedropper_filter: _ViewportEyedropperFilter | None = None
        self._selected_row_widget: QWidget | None = None

        obj_name = getattr(group, "name", "") or tr("Objeto")
        self.setWindowTitle(f"{tr('Acabamentos de Render')} — {obj_name}")
        self.setMinimumWidth(600)
        self.setMinimumHeight(420)

        root = QVBoxLayout(self)
        info = QLabel(
            tr(
                "Defina como cada material/cor/textura deste objeto será renderizado no Blender "
                "(presets procedurais sem necessidade de textura externa):"
            )
        )
        info.setWordWrap(True)
        root.addWidget(info)

        self._combos: dict[str, QComboBox] = {}
        self._row_widgets: dict[str, QWidget] = {}
        self._rows: list[tuple[str, QWidget, QComboBox]] = []
        slots = extract_group_material_slots(group)
        saved = get_group_render_materials(group)

        if slots:
            filter_bar = QHBoxLayout()
            self._search = QLineEdit()
            self._search.setPlaceholderText(tr("Filtrar por material ou peça…"))
            self._search.setClearButtonEnabled(True)
            self._search.textChanged.connect(self._apply_filter)
            filter_bar.addWidget(self._search, 1)

            if self._viewport is not None and hasattr(self._viewport, "pick_face_any"):
                self._btn_eyedropper = QPushButton(tr("💧 Conta-gotas"))
                self._btn_eyedropper.setToolTip(
                    tr("Clique em uma face na cena 3D para selecionar automaticamente o material dela")
                )
                self._btn_eyedropper.clicked.connect(self._start_eyedropper)
                filter_bar.addWidget(self._btn_eyedropper)

            root.addLayout(filter_bar)

            bulk_bar = QHBoxLayout()
            bulk_bar.addWidget(QLabel(tr("Aplicar em lote:")))
            self._bulk_combo = QComboBox()
            for pid, pname in RENDER_PRESETS:
                self._bulk_combo.addItem(tr(pname), pid)
            bulk_bar.addWidget(self._bulk_combo, 1)

            btn_apply_all = QPushButton(tr("Aplicar a todos"))
            btn_apply_all.clicked.connect(self._apply_bulk_preset)
            bulk_bar.addWidget(btn_apply_all)

            btn_reset = QPushButton(tr("Resetar para Original"))
            btn_reset.clicked.connect(self._reset_all_to_original)
            bulk_bar.addWidget(btn_reset)
            root.addLayout(bulk_bar)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        container = QWidget()
        form = QVBoxLayout(container)
        form.setAlignment(Qt.AlignTop)

        if not slots:
            form.addWidget(QLabel(tr("Nenhum material ou face encontrado neste objeto.")))
        else:
            for slot in slots:
                key = slot["key"]

                row_widget = QWidget()
                row = QHBoxLayout(row_widget)
                row.setContentsMargins(4, 3, 4, 3)

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

                part_names = slot.get("part_names") or []
                lbl_box = QVBoxLayout()
                lbl_box.setContentsMargins(0, 0, 0, 0)
                lbl_box.setSpacing(1)
                lbl_main = QLabel(f"{slot['label']}  ({slot['face_count']} {tr('faces')})")
                lbl_main.setMinimumWidth(210)
                lbl_box.addWidget(lbl_main)
                if part_names:
                    shown = ", ".join(part_names[:3])
                    if len(part_names) > 3:
                        shown += f" (+{len(part_names) - 3})"
                    lbl_parts = QLabel(f"{tr('Peças')}: {shown}")
                    lbl_parts.setStyleSheet("color: #94A3B8; font-size: 11px;")
                    lbl_box.addWidget(lbl_parts)
                row.addLayout(lbl_box, 1)

                cb = QComboBox()
                for pid, pname in RENDER_PRESETS:
                    cb.addItem(tr(pname), pid)
                cur_preset = saved.get(key, "original")
                idx = cb.findData(cur_preset)
                if idx >= 0:
                    cb.setCurrentIndex(idx)
                row.addWidget(cb)

                self._combos[key] = cb
                self._row_widgets[key] = row_widget
                search_haystack = f"{slot['label']} {' '.join(part_names)}".lower()
                self._rows.append((search_haystack, row_widget, cb))
                form.addWidget(row_widget)

        self._scroll.setWidget(container)
        root.addWidget(self._scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _start_eyedropper(self) -> None:
        if self._viewport is None:
            return
        self._cleanup_eyedropper()
        self._eyedropper_filter = _ViewportEyedropperFilter(self, self._viewport)
        self._viewport.installEventFilter(self._eyedropper_filter)
        if hasattr(self._viewport, "setCursor"):
            self._viewport.setCursor(Qt.CrossCursor)
        self.hide()

    def _cleanup_eyedropper(self) -> None:
        if self._eyedropper_filter is not None and self._viewport is not None:
            try:
                self._viewport.removeEventFilter(self._eyedropper_filter)
            except Exception:
                pass
            if hasattr(self._viewport, "unsetCursor"):
                self._viewport.unsetCursor()
        self._eyedropper_filter = None

    def _cancel_eyedropper(self) -> None:
        self._cleanup_eyedropper()
        self.show()
        self.raise_()
        self.activateWindow()

    def _finish_eyedropper(self, px: int, py: int) -> None:
        self._cleanup_eyedropper()
        hit_face = None
        try:
            hit_face, _hit_grp = self._viewport.pick_face_any(px, py)
        except Exception:
            hit_face = None

        self.show()
        self.raise_()
        self.activateWindow()

        if hit_face is None:
            return
        key, _label, _col, _tpath = face_material_key(hit_face)
        self._select_slot_key(key)

    def _select_slot_key(self, key: str) -> None:
        row_widget = self._row_widgets.get(key)
        cb = self._combos.get(key)
        if row_widget is None or cb is None:
            return
        if hasattr(self, "_search") and self._search.text():
            self._search.clear()
        if self._selected_row_widget is not None:
            self._selected_row_widget.setStyleSheet("")
        row_widget.setStyleSheet(
            "QWidget { background-color: rgba(56, 189, 248, 45); "
            "border: 1px solid #38BDF8; border-radius: 4px; }"
        )
        self._selected_row_widget = row_widget
        self._scroll.ensureWidgetVisible(row_widget)
        cb.setFocus()

    def _apply_filter(self, text: str) -> None:
        needle = text.strip().lower()
        for haystack, row_widget, _cb in self._rows:
            row_widget.setVisible(not needle or needle in haystack)

    def _apply_bulk_preset(self) -> None:
        preset_id = self._bulk_combo.currentData()
        for _haystack, row_widget, cb in self._rows:
            if row_widget.isHidden():
                continue
            idx = cb.findData(preset_id)
            if idx >= 0:
                cb.setCurrentIndex(idx)

    def _reset_all_to_original(self) -> None:
        for _haystack, _row_widget, cb in self._rows:
            idx = cb.findData("original")
            if idx >= 0:
                cb.setCurrentIndex(idx)

    def _on_accept(self) -> None:
        self._cleanup_eyedropper()
        mapping = {
            key: str(cb.currentData())
            for key, cb in self._combos.items()
        }
        set_group_render_materials(self._group, mapping)
        self.accept()

    def done(self, result: int) -> None:
        self._cleanup_eyedropper()
        super().done(result)
