# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
"""Diálogos da interface: Atributos do Componente e Opções do Componente com recursos completos."""
from __future__ import annotations

from typing import Any
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .model import ensure_dc_data, evaluate_dc, get_dc_data, STANDARD_ATTRIBUTES


class ComponentOptionsDialog(QDialog):
    """Janela 'Opções do Componente' (estilo Component Options do SketchUp)."""

    def __init__(self, group, viewport=None, parent=None):
        super().__init__(parent)
        self.group = group
        self.viewport = viewport
        self.setWindowTitle(f"Opções do Componente - {getattr(group, 'name', 'Componente')}")
        self.resize(380, 460)
        self._fields: dict[str, QWidget] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        data = ensure_dc_data(self.group)

        # Cabeçalho
        title_box = QGroupBox("Parâmetros do Componente")
        title_layout = QVBoxLayout(title_box)

        name_lbl = QLabel(f"<b>{data.get('name', 'Componente')}</b>")
        title_layout.addWidget(name_lbl)

        desc = data.get("description", "").strip()
        if desc:
            lbl_desc = QLabel(desc)
            lbl_desc.setWordWrap(True)
            title_layout.addWidget(lbl_desc)

        layout.addWidget(title_box)

        # Formulário dinâmico
        form = QFormLayout()
        attrs = data.get("attributes", {})

        for name, info in attrs.items():
            if not info.get("editable", True):
                continue
            # Se tiver fórmula ativa, campo fica somente leitura
            has_formula = bool(str(info.get("formula", "")).strip())
            unit = info.get("unit", "")
            label_text = f"{info.get('label', name)} ({unit}):" if unit else f"{info.get('label', name)}:"

            options = info.get("options", [])
            if options:
                cmb = QComboBox()
                for opt in options:
                    cmb.addItem(str(opt))
                curr = str(info.get("value", ""))
                idx = cmb.findText(curr)
                if idx >= 0:
                    cmb.setCurrentIndex(idx)
                cmb.setEnabled(not has_formula)
                form.addRow(label_text, cmb)
                self._fields[name] = cmb
            else:
                edit = QLineEdit(str(info.get("value", "")))
                edit.setEnabled(not has_formula)
                form.addRow(label_text, edit)
                self._fields[name] = edit

        layout.addLayout(form)
        layout.addStretch()

        # Botões de Ação
        btn_layout = QHBoxLayout()
        btn_apply = QPushButton("Aplicar")
        btn_apply.setStyleSheet("font-weight: bold; padding: 6px 16px;")
        btn_apply.clicked.connect(self._on_apply)
        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(self.accept)

        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    def _on_apply(self):
        data = get_dc_data(self.group)
        if not data:
            return

        attrs = data.get("attributes", {})
        for name, widget in self._fields.items():
            if name in attrs and widget.isEnabled():
                val_str = widget.currentText() if isinstance(widget, QComboBox) else widget.text()
                try:
                    val = float(val_str)
                except ValueError:
                    val = val_str
                attrs[name]["value"] = val

        evaluate_dc(self.group)
        if self.viewport and hasattr(self.viewport, "update"):
            self.viewport.update()
        QMessageBox.information(self, "Sucesso", "Parâmetros aplicados e geometria recalculada!")


class ComponentAttributesDialog(QDialog):
    """Janela 'Atributos do Componente' (estilo Component Attributes do SketchUp)."""

    def __init__(self, group, viewport=None, parent=None):
        super().__init__(parent)
        self.group = group
        self.viewport = viewport
        self.setWindowTitle(f"Atributos do Componente - {getattr(group, 'name', 'Componente')}")
        self.resize(750, 520)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        self.data = ensure_dc_data(self.group)

        # Header explicativo
        info_lbl = QLabel(
            "<b>Atributos e Fórmulas</b><br>"
            "Fórmulas iniciam com <code>=</code> (ex: <code>=Parent!LenX / 2</code> ou <code>=IF(Aberto=1, 90, 0)</code>)."
        )
        layout.addWidget(info_lbl)

        # Tabela de Atributos
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Atributo", "Rótulo", "Valor Atual", "Fórmula", "Unidade"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        self._populate_table()

        # Configuração do onClick
        click_box = QGroupBox("Comportamento ao Clicar (onClick)")
        click_layout = QHBoxLayout(click_box)
        self.click_input = QLineEdit(self.data.get("onClick", ""))
        self.click_input.setPlaceholderText("Ex: ANIMATE('RotZ', 0, 90) ou SET('Aberto', 1 - Aberto)")
        click_layout.addWidget(self.click_input)
        layout.addWidget(click_box)

        # Barra de Botões
        btn_bar = QHBoxLayout()
        btn_add = QPushButton("+ Adicionar Atributo Customizado")
        btn_add.clicked.connect(self._add_custom_row)
        btn_add_std = QPushButton("+ Atributos Padrão")
        btn_add_std.clicked.connect(self._add_missing_standard)
        btn_del = QPushButton("- Remover Selecionado")
        btn_del.clicked.connect(self._del_row)
        btn_calc = QPushButton("Avaliar Fórmulas")
        btn_calc.clicked.connect(self._evaluate)

        btn_save = QPushButton("Salvar e Aplicar")
        btn_save.setStyleSheet("font-weight: bold; background-color: #2e7d32; color: white; padding: 6px 14px;")
        btn_save.clicked.connect(self._save)

        btn_bar.addWidget(btn_add)
        btn_bar.addWidget(btn_add_std)
        btn_bar.addWidget(btn_del)
        btn_bar.addWidget(btn_calc)
        btn_bar.addStretch()
        btn_bar.addWidget(btn_save)

        layout.addLayout(btn_bar)

    def _populate_table(self):
        attrs = self.data.get("attributes", {})
        self.table.setRowCount(len(attrs))
        for row, (name, info) in enumerate(attrs.items()):
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(str(info.get("label", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(str(info.get("value", ""))))
            self.table.setItem(row, 3, QTableWidgetItem(str(info.get("formula", ""))))
            self.table.setItem(row, 4, QTableWidgetItem(str(info.get("unit", ""))))

    def _add_custom_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(f"Custom_{row+1}"))
        self.table.setItem(row, 1, QTableWidgetItem("Novo Atributo"))
        self.table.setItem(row, 2, QTableWidgetItem("0"))
        self.table.setItem(row, 3, QTableWidgetItem(""))
        self.table.setItem(row, 4, QTableWidgetItem(""))

    def _add_missing_standard(self):
        attrs = self.data.get("attributes", {})
        for k, v in STANDARD_ATTRIBUTES.items():
            if k not in attrs:
                attrs[k] = dict(v)
        self._populate_table()

    def _del_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def _save(self):
        attrs = {}
        for row in range(self.table.rowCount()):
            item_k = self.table.item(row, 0)
            if not item_k:
                continue
            key = item_k.text().strip()
            if not key:
                continue
            lbl = self.table.item(row, 1).text().strip() if self.table.item(row, 1) else key
            val_str = self.table.item(row, 2).text().strip() if self.table.item(row, 2) else "0"
            form = self.table.item(row, 3).text().strip() if self.table.item(row, 3) else ""
            unit = self.table.item(row, 4).text().strip() if self.table.item(row, 4) else ""

            try:
                val = float(val_str)
            except ValueError:
                val = val_str

            attrs[key] = {
                "label": lbl,
                "value": val,
                "formula": form,
                "unit": unit,
                "editable": True,
            }

        self.data["attributes"] = attrs
        self.data["onClick"] = self.click_input.text().strip()
        evaluate_dc(self.group)
        self._populate_table()
        if self.viewport and hasattr(self.viewport, "update"):
            self.viewport.update()
        QMessageBox.information(self, "Salvo", "Atributos atualizados e geometria recalculada na cena!")

    def _evaluate(self):
        self._save()
