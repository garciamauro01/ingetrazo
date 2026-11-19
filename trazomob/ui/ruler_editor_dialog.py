# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Diálogo para Configuração e Criação de Réguas e Linhas-Guia de Altura (TrazoMob).

Permite ao usuário:
1. Criar novas réguas personalizadas (ex: "Lavanderia", "Closet Casal", "Escritório");
2. Duplicar ou renomear réguas existentes;
3. Adicionar, editar ou remover níveis de altura (com nome, altura em mm e cor);
4. Salvar tudo automaticamente nas preferências persistentes do TrazoMob.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from views.color_dialog import get_color

from ..wall.guides import WallGuideRulerManager, DEFAULT_RULER_PRESETS


class RulerEditorDialog(QDialog):
    """Diálogo modal moderno para gerenciar réguas e seus níveis de altura."""

    def __init__(self, parent: Optional[QWidget] = None, ruler_mgr: Optional[WallGuideRulerManager] = None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Réguas de Altura — TrazoMob")
        self.setMinimumSize(540, 480)
        self.resize(580, 520)

        self.ruler_mgr = ruler_mgr or WallGuideRulerManager.get_instance()
        # Cópia de trabalho local dos presets para permitir Cancelar ou Salvar
        self._working_presets: Dict[str, List[Dict[str, any]]] = {}
        for k, v in self.ruler_mgr.presets.items():
            self._working_presets[k] = [dict(item) for item in v]
        self._active_preset = self.ruler_mgr.active_preset_name

        self._build_ui()
        self._populate_presets()
        self._load_current_preset_table()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Cabeçalho explicativo
        lbl_info = QLabel(
            "<b>Gerenciamento de Réguas Paramétricas de Parede</b><br>"
            "<span style='color: gray;'>Defina níveis de referência (rodapé, bancadas, aéreos, pé-direito) "
            "com linhas-guia magnéticas no 3D.</span>"
        )
        layout.addWidget(lbl_info)

        # Barra de seleção e ações de presets
        h_preset = QHBoxLayout()
        h_preset.setSpacing(6)

        lbl_preset = QLabel("<b>Régua:</b>")
        h_preset.addWidget(lbl_preset)

        self.cb_preset = QComboBox()
        self.cb_preset.setMinimumWidth(160)
        self.cb_preset.currentTextChanged.connect(self._on_preset_selection_changed)
        h_preset.addWidget(self.cb_preset)

        self.btn_new = QPushButton("➕ Nova")
        self.btn_new.setToolTip("Criar uma nova régua em branco ou baseada na atual")
        self.btn_new.clicked.connect(self._create_new_preset)
        h_preset.addWidget(self.btn_new)

        self.btn_rename = QPushButton("✏️ Renomear")
        self.btn_rename.setToolTip("Renomear a régua selecionada")
        self.btn_rename.clicked.connect(self._rename_current_preset)
        h_preset.addWidget(self.btn_rename)

        self.btn_delete = QPushButton("🗑️ Excluir")
        self.btn_delete.setToolTip("Excluir a régua selecionada")
        self.btn_delete.clicked.connect(self._delete_current_preset)
        h_preset.addWidget(self.btn_delete)

        self.btn_reset = QPushButton("↺ Restaurar")
        self.btn_reset.setToolTip("Restaurar para a configuração padrão de fábrica")
        self.btn_reset.clicked.connect(self._reset_current_preset)
        h_preset.addWidget(self.btn_reset)

        h_preset.addStretch()
        layout.addLayout(h_preset)

        # Tabela de níveis da régua
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Nível / Descrição", "Altura (mm)", "Cor da Linha"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)

        # Botões de gerenciamento de níveis (Adicionar, Remover)
        h_levels = QHBoxLayout()
        h_levels.setSpacing(8)

        self.btn_add_level = QPushButton("➕ Adicionar Nível")
        self.btn_add_level.clicked.connect(self._add_level_row)
        h_levels.addWidget(self.btn_add_level)

        self.btn_remove_level = QPushButton("➖ Remover Nível")
        self.btn_remove_level.clicked.connect(self._remove_selected_level_row)
        h_levels.addWidget(self.btn_remove_level)

        h_levels.addStretch()
        layout.addLayout(h_levels)

        # Botões de Salvar / Cancelar
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Salvar Preferências")
        buttons.button(QDialogButtonBox.Cancel).setText("Cancelar")
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate_presets(self) -> None:
        self.cb_preset.blockSignals(True)
        self.cb_preset.clear()
        self.cb_preset.addItems(list(self._working_presets.keys()))
        if self._active_preset in self._working_presets:
            self.cb_preset.setCurrentText(self._active_preset)
        elif self.cb_preset.count() > 0:
            self._active_preset = self.cb_preset.currentText()
        self.cb_preset.blockSignals(False)

        # Habilita/desabilita restaurar e excluir
        is_default = self._active_preset in DEFAULT_RULER_PRESETS
        self.btn_reset.setEnabled(is_default)
        self.btn_delete.setEnabled(len(self._working_presets) > 1)

    def _save_table_to_working_preset(self) -> None:
        """Lê os dados da tabela e atualiza o preset de trabalho atual."""
        if not self._active_preset or self._active_preset not in self._working_presets:
            return

        levels = []
        for row in range(self.table.rowCount()):
            item_name = self.table.item(row, 0)
            name = item_name.text().strip() if item_name else f"Nível {row + 1}"

            w_spin = self.table.cellWidget(row, 1)
            z_mm = w_spin.value() if isinstance(w_spin, QSpinBox) else 1000

            w_color_btn = self.table.cellWidget(row, 2)
            color_rgb = getattr(w_color_btn, "_rgb_color", (16, 185, 129))

            levels.append({
                "name": name,
                "z_mm": int(z_mm),
                "color": tuple(color_rgb),
            })

        # Ordena por altura
        levels.sort(key=lambda x: x["z_mm"])
        self._working_presets[self._active_preset] = levels

    def _load_current_preset_table(self) -> None:
        levels = self._working_presets.get(self._active_preset, [])
        self.table.setRowCount(0)
        self.table.setRowCount(len(levels))

        for row, lv in enumerate(levels):
            # 0. Nome
            name_item = QTableWidgetItem(str(lv.get("name", f"Nível {row + 1}")))
            self.table.setItem(row, 0, name_item)

            # 1. Altura Z (mm)
            spin = QSpinBox()
            spin.setRange(0, 10000)
            spin.setValue(int(lv.get("z_mm", 1000)))
            spin.setSuffix(" mm")
            self.table.setCellWidget(row, 1, spin)

            # 2. Cor
            rgb = tuple(lv.get("color", (16, 185, 129)))
            btn_col = self._make_color_button(rgb)
            self.table.setCellWidget(row, 2, btn_col)

    def _make_color_button(self, rgb: Tuple[int, int, int]) -> QPushButton:
        btn = QPushButton()
        btn._rgb_color = rgb
        r, g, b = rgb
        qcol = QColor(r, g, b)
        btn.setStyleSheet(f"background-color: {qcol.name()}; border: 1px solid #555; border-radius: 4px; min-width: 40px; min-height: 20px;")
        def _pick_color():
            c = get_color(qcol, self, "Escolher Cor da Linha-Guia")
            if c.isValid():
                new_rgb = (c.red(), c.green(), c.blue())
                btn._rgb_color = new_rgb
                btn.setStyleSheet(f"background-color: {c.name()}; border: 1px solid #555; border-radius: 4px; min-width: 40px; min-height: 20px;")
        btn.clicked.connect(_pick_color)
        return btn

    def _on_preset_selection_changed(self, new_preset: str) -> None:
        if not new_preset:
            return
        self._save_table_to_working_preset()
        self._active_preset = new_preset
        self._load_current_preset_table()

        is_default = self._active_preset in DEFAULT_RULER_PRESETS
        self.btn_reset.setEnabled(is_default)
        self.btn_delete.setEnabled(len(self._working_presets) > 1)

    def _create_new_preset(self) -> None:
        self._save_table_to_working_preset()
        name, ok = QInputDialog.getText(
            self,
            "Nova Régua de Alturas",
            "Nome da nova régua (ex: Lavanderia, Closet, Home Theater):"
        )
        if ok and name.strip():
            name = name.strip()
            if name in self._working_presets:
                QMessageBox.warning(self, "Aviso", f"Já existe uma régua com o nome '{name}'.")
                return
            # Clona a régua atualmente ativa como ponto de partida
            current_levels = self._working_presets.get(self._active_preset, [])
            self._working_presets[name] = [dict(lv) for lv in current_levels]
            self._active_preset = name
            self._populate_presets()
            self._load_current_preset_table()

    def _rename_current_preset(self) -> None:
        self._save_table_to_working_preset()
        old_name = self._active_preset
        new_name, ok = QInputDialog.getText(
            self,
            "Renomear Régua",
            "Novo nome da régua:",
            text=old_name,
        )
        if ok and new_name.strip() and new_name.strip() != old_name:
            new_name = new_name.strip()
            if new_name in self._working_presets:
                QMessageBox.warning(self, "Aviso", f"Já existe uma régua com o nome '{new_name}'.")
                return
            levels = self._working_presets.pop(old_name)
            self._working_presets[new_name] = levels
            self._active_preset = new_name
            self._populate_presets()
            self._load_current_preset_table()

    def _delete_current_preset(self) -> None:
        if len(self._working_presets) <= 1:
            QMessageBox.warning(self, "Aviso", "É necessário manter pelo menos uma régua cadastrada.")
            return

        resp = QMessageBox.question(
            self,
            "Confirmar Exclusão",
            f"Deseja realmente excluir a régua '{self._active_preset}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if resp == QMessageBox.Yes:
            del self._working_presets[self._active_preset]
            self._active_preset = next(iter(self._working_presets.keys()))
            self._populate_presets()
            self._load_current_preset_table()

    def _reset_current_preset(self) -> None:
        if self._active_preset in DEFAULT_RULER_PRESETS:
            resp = QMessageBox.question(
                self,
                "Restaurar Padrão",
                f"Deseja restaurar a régua '{self._active_preset}' para as alturas padrão de fábrica?",
                QMessageBox.Yes | QMessageBox.No
            )
            if resp == QMessageBox.Yes:
                self._working_presets[self._active_preset] = [dict(lv) for lv in DEFAULT_RULER_PRESETS[self._active_preset]]
                self._load_current_preset_table()

    def _add_level_row(self) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)

        name_item = QTableWidgetItem(f"Nível {row + 1}")
        self.table.setItem(row, 0, name_item)

        spin = QSpinBox()
        spin.setRange(0, 10000)
        spin.setValue(1000 + row * 200)
        spin.setSuffix(" mm")
        self.table.setCellWidget(row, 1, spin)

        btn_col = self._make_color_button((14, 165, 233))
        self.table.setCellWidget(row, 2, btn_col)

        self.table.selectRow(row)

    def _remove_selected_level_row(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def _save_and_accept(self) -> None:
        self._save_table_to_working_preset()

        # Atualiza o WallGuideRulerManager com os novos presets
        self.ruler_mgr.presets = dict(self._working_presets)
        self.ruler_mgr.active_preset_name = self._active_preset
        self.ruler_mgr.save_preferences()

        self.accept()
