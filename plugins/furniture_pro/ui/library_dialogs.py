# SPDX-License-Identifier: GPL-3.0-or-later
"""Editors for the material, edge-band and hardware libraries."""
from __future__ import annotations

import json

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog,
                               QDialogButtonBox, QDoubleSpinBox, QFormLayout,
                               QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QPlainTextEdit, QPushButton, QVBoxLayout,
                               QWidget)

from ..core.constants import (DEFAULT_FINISHES, GRAIN_LABELS,
                              HARDWARE_CATEGORIES)
from ..core.models import (EdgeBand, HardwareItem, Material, new_id)


def _spin(lo=0.0, hi=1_000_000.0, decimals=2, suffix="") -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setRange(lo, hi)
    box.setDecimals(decimals)
    if suffix:
        box.setSuffix(suffix)
    return box


def _buttons(dialog: QDialog) -> QDialogButtonBox:
    box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    box.accepted.connect(dialog.accept)
    box.rejected.connect(dialog.reject)
    return box


class _ColorField(QWidget):
    def __init__(self, color: str = "#E6E4DD", parent=None) -> None:
        super().__init__(parent)
        self.edit = QLineEdit(color)
        self.button = QPushButton("Escolher…")
        self.button.clicked.connect(self._pick)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.edit, 1)
        layout.addWidget(self.button)

    def _pick(self) -> None:
        color = QColorDialog.getColor(QColor(self.edit.text() or "#E6E4DD"),
                                      self, "Cor do material")
        if color.isValid():
            self.edit.setText(color.name().upper())

    def value(self) -> str:
        return self.edit.text().strip() or "#E6E4DD"


class MaterialDialog(QDialog):
    def __init__(self, material: Material | None = None, *,
                 edge_bands=None, parent=None) -> None:
        super().__init__(parent)
        self.material = material or Material(id=new_id("mat"), name="Novo material")
        self.setWindowTitle("Editar material" if material else "Novo material")
        self.resize(540, 640)
        form = QFormLayout()
        self.name = QLineEdit(self.material.name)
        self.category = QLineEdit(self.material.category)
        self.manufacturer = QLineEdit(self.material.manufacturer)
        self.reference = QLineEdit(self.material.reference)
        self.thickness = _spin(0.1, 100, 2, " mm")
        self.thickness.setValue(self.material.thickness_mm)
        self.sheet_length = _spin(10, 10000, 1, " mm")
        self.sheet_length.setValue(self.material.sheet_length_mm)
        self.sheet_width = _spin(10, 10000, 1, " mm")
        self.sheet_width.setValue(self.material.sheet_width_mm)
        self.cost_sheet = _spin(0, 1_000_000, 2)
        self.cost_sheet.setValue(self.material.cost_per_sheet)
        self.cost_m2 = _spin(0, 1_000_000, 2)
        self.cost_m2.setValue(self.material.cost_per_m2)
        self.grain = QComboBox()
        for value, label in GRAIN_LABELS.items():
            self.grain.addItem(label, value)
        self.grain.setCurrentIndex(max(0, self.grain.findData(
            self.material.grain_axis)))
        self.rotation = QCheckBox("Permitir giro no plano de corte")
        self.rotation.setChecked(self.material.allow_rotation)
        self.finish = QComboBox()
        self.finish.setEditable(True)
        for value in DEFAULT_FINISHES:
            self.finish.addItem(value)
        self.finish.setCurrentText(self.material.finish)
        self.supplier = QLineEdit(self.material.supplier)
        self.availability = QCheckBox("Disponível para novos projetos")
        self.availability.setChecked(self.material.availability)
        self.color = _ColorField(self.material.color)
        self.edge = QComboBox()
        self.edge.addItem("(sem fita padrão)", "")
        for band in (edge_bands or {}).values():
            self.edge.addItem(band.name, band.id)
        pos = self.edge.findData(self.material.edge_band_id)
        if pos < 0 and self.material.edge_band_id:
            self.edge.addItem(self.material.edge_band_id,
                              self.material.edge_band_id)
            pos = self.edge.count() - 1
        self.edge.setCurrentIndex(max(0, pos))
        self.notes = QPlainTextEdit(self.material.notes)
        self.notes.setMaximumHeight(80)
        form.addRow("Nome", self.name)
        form.addRow("Categoria", self.category)
        form.addRow("Fabricante", self.manufacturer)
        form.addRow("Referência", self.reference)
        form.addRow("Espessura", self.thickness)
        form.addRow("Comprimento da chapa", self.sheet_length)
        form.addRow("Largura da chapa", self.sheet_width)
        form.addRow("Custo por chapa", self.cost_sheet)
        form.addRow("Custo por m²", self.cost_m2)
        form.addRow("Veio", self.grain)
        form.addRow("", self.rotation)
        form.addRow("Acabamento", self.finish)
        form.addRow("Fornecedor", self.supplier)
        form.addRow("", self.availability)
        form.addRow("Cor", self.color)
        form.addRow("Fita padrão", self.edge)
        form.addRow("Observações", self.notes)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(_buttons(self))

    def result_material(self) -> Material:
        mat = self.material
        mat.name = self.name.text().strip() or "Material"
        mat.category = self.category.text().strip()
        mat.manufacturer = self.manufacturer.text().strip()
        mat.reference = self.reference.text().strip()
        mat.thickness_mm = self.thickness.value()
        mat.sheet_length_mm = self.sheet_length.value()
        mat.sheet_width_mm = self.sheet_width.value()
        mat.cost_per_sheet = self.cost_sheet.value()
        mat.cost_per_m2 = self.cost_m2.value()
        mat.grain_axis = self.grain.currentData() or "length"
        mat.allow_rotation = self.rotation.isChecked()
        mat.finish = self.finish.currentText().strip() or "Liso"
        mat.supplier = self.supplier.text().strip()
        mat.availability = self.availability.isChecked()
        mat.color = self.color.value()
        mat.edge_band_id = self.edge.currentData() or ""
        mat.notes = self.notes.toPlainText()
        return mat


class EdgeBandDialog(QDialog):
    def __init__(self, band: EdgeBand | None = None, parent=None) -> None:
        super().__init__(parent)
        self.band = band or EdgeBand(id=new_id("eb"), name="Nova fita")
        self.setWindowTitle("Editar fita" if band else "Nova fita")
        form = QFormLayout()
        self.name = QLineEdit(self.band.name)
        self.thickness = _spin(0.05, 10, 2, " mm")
        self.thickness.setValue(self.band.thickness_mm)
        self.material = QLineEdit(self.band.material)
        self.cost = _spin(0, 1_000_000, 2)
        self.cost.setValue(self.band.cost_per_m)
        self.supplier = QLineEdit(self.band.supplier)
        self.availability = QCheckBox("Disponível")
        self.availability.setChecked(self.band.availability)
        self.color = _ColorField(self.band.color)
        self.notes = QPlainTextEdit(self.band.notes)
        self.notes.setMaximumHeight(70)
        form.addRow("Nome", self.name)
        form.addRow("Espessura", self.thickness)
        form.addRow("Material", self.material)
        form.addRow("Custo por metro", self.cost)
        form.addRow("Fornecedor", self.supplier)
        form.addRow("", self.availability)
        form.addRow("Cor", self.color)
        form.addRow("Observações", self.notes)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(_buttons(self))

    def result_band(self) -> EdgeBand:
        band = self.band
        band.name = self.name.text().strip() or "Fita de borda"
        band.thickness_mm = self.thickness.value()
        band.material = self.material.text().strip() or "PVC"
        band.cost_per_m = self.cost.value()
        band.supplier = self.supplier.text().strip()
        band.availability = self.availability.isChecked()
        band.color = self.color.value()
        band.notes = self.notes.toPlainText()
        return band


class HardwareDialog(QDialog):
    def __init__(self, item: HardwareItem | None = None, parent=None) -> None:
        super().__init__(parent)
        self.item = item or HardwareItem(id=new_id("hw"), name="Nova ferragem")
        self.setWindowTitle("Editar ferragem" if item else "Nova ferragem")
        self.resize(520, 560)
        form = QFormLayout()
        self.name = QLineEdit(self.item.name)
        self.category = QComboBox()
        for value, label in HARDWARE_CATEGORIES.items():
            self.category.addItem(label, value)
        self.category.setCurrentIndex(max(0, self.category.findData(
            self.item.category)))
        self.manufacturer = QLineEdit(self.item.manufacturer)
        self.reference = QLineEdit(self.item.reference)
        self.unit = QLineEdit(self.item.unit)
        self.cost = _spin(0, 1_000_000, 2)
        self.cost.setValue(self.item.cost)
        self.supplier = QLineEdit(self.item.supplier)
        self.verified = QCheckBox(
            "Dados de instalação conferidos no catálogo do fabricante")
        self.verified.setChecked(self.item.verified)
        self.install = QPlainTextEdit(json.dumps(self.item.install or {},
                                                 ensure_ascii=False, indent=2))
        self.install.setMaximumHeight(110)
        self.install.setPlaceholderText(
            '{"copo_mm": 35, "recuo_mm": 3, "fonte": "catálogo 2026"}')
        self.notes = QPlainTextEdit(self.item.notes)
        self.notes.setMaximumHeight(70)
        warning = QLabel(
            "A furação só é emitida em relatórios como dado de instalação "
            "quando esta caixa está marcada. Sem ela, o plugin não presume "
            "medidas de fabricante.")
        warning.setWordWrap(True)
        form.addRow("Nome", self.name)
        form.addRow("Categoria", self.category)
        form.addRow("Fabricante", self.manufacturer)
        form.addRow("Referência", self.reference)
        form.addRow("Unidade", self.unit)
        form.addRow("Custo unitário", self.cost)
        form.addRow("Fornecedor", self.supplier)
        form.addRow("", self.verified)
        form.addRow("Instalação (JSON)", self.install)
        form.addRow("Observações", self.notes)
        form.addRow("", warning)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(_buttons(self))

    def result_item(self) -> HardwareItem:
        item = self.item
        item.name = self.name.text().strip() or "Ferragem"
        item.category = self.category.currentData() or "outro"
        item.manufacturer = self.manufacturer.text().strip()
        item.reference = self.reference.text().strip()
        item.unit = self.unit.text().strip() or "un"
        item.cost = self.cost.value()
        item.supplier = self.supplier.text().strip()
        item.verified = self.verified.isChecked()
        text = self.install.toPlainText().strip() or "{}"
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise ValueError(f"JSON de instalação inválido: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("Os dados de instalação devem ser um objeto JSON.")
        item.install = data
        item.notes = self.notes.toPlainText()
        return item
