# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Diálogo de gerenciamento e cadastro de materiais e padrões de MDF."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
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

from ..domain.i18n import tr
from ..domain.materials_registry import MaterialDefinition, MaterialsRegistry


class MaterialsManagerDialog(QDialog):
    """Diálogo modal para cadastrar, editar e remover materiais do catálogo."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Gerenciamento de Materiais e Padrões"))
        self.resize(750, 480)
        self.registry = MaterialsRegistry.get_instance()
        self._build_ui()
        self._load_table()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        lbl_info = QLabel(
            tr("<b>Catálogo Oficial de Materiais:</b> Configure o sentido do veio e permissão de giro "
               "no plano de corte de cada padrão de MDF ou pedra.")
        )
        lbl_info.setWordWrap(True)
        layout.addWidget(lbl_info)

        # Tabela de materiais
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            tr("Padrão / Nome"),
            tr("Categoria"),
            tr("Permite Giro (Sem Veio)"),
            tr("Sentido do Veio"),
            tr("Ações"),
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

        # Barra de botões inferiores
        btn_bar = QHBoxLayout()
        self.btn_add = QPushButton(tr("➕ Novo Material"))
        self.btn_add.setStyleSheet("font-weight: bold; padding: 6px 12px;")
        self.btn_add.clicked.connect(self._on_add_material)
        btn_bar.addWidget(self.btn_add)

        self.btn_reset = QPushButton(tr("🔄 Restaurar Padrões de Fábrica"))
        self.btn_reset.clicked.connect(self._on_reset_defaults)
        btn_bar.addWidget(self.btn_reset)

        btn_bar.addStretch()

        self.btn_close = QPushButton(tr("Fechar"))
        self.btn_close.clicked.connect(self.accept)
        btn_bar.addWidget(self.btn_close)

        layout.addLayout(btn_bar)

    def _load_table(self) -> None:
        materials = self.registry.list_materials()
        self.table.setRowCount(len(materials))

        for row, mat in enumerate(materials):
            # 0: Nome
            item_nome = QTableWidgetItem(mat.nome)
            item_nome.setFlags(item_nome.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, item_nome)

            # 1: Categoria
            item_cat = QTableWidgetItem(mat.categoria.upper())
            item_cat.setTextAlignment(Qt.AlignCenter)
            item_cat.setFlags(item_cat.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 1, item_cat)

            # 2: Permite Giro (Checkbox direto na tabela)
            chk_giro = QCheckBox()
            chk_giro.setChecked(mat.permite_giro)
            chk_giro.setToolTip(tr("Se marcado, o corte pode virar a peça 90° para economizar chapa (Branco TX e unicolores)"))
            chk_giro.toggled.connect(lambda val, m=mat: self._on_giro_toggled(m, val))

            w_giro = QWidget()
            l_giro = QHBoxLayout(w_giro)
            l_giro.setContentsMargins(0, 0, 0, 0)
            l_giro.setAlignment(Qt.AlignCenter)
            l_giro.addWidget(chk_giro)
            self.table.setCellWidget(row, 2, w_giro)

            # 3: Sentido Veio
            txt_veio = tr("Indiferente") if mat.permite_giro else tr("Longitudinal (Madeirado)")
            item_veio = QTableWidgetItem(txt_veio)
            item_veio.setTextAlignment(Qt.AlignCenter)
            item_veio.setFlags(item_veio.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 3, item_veio)

            # 4: Ações (Remover se customizado)
            w_act = QWidget()
            l_act = QHBoxLayout(w_act)
            l_act.setContentsMargins(2, 2, 2, 2)
            l_act.setAlignment(Qt.AlignCenter)
            btn_del = QPushButton("🗑️")
            btn_del.setToolTip(tr("Excluir material"))
            btn_del.setMaximumWidth(32)
            btn_del.clicked.connect(lambda _, m_nome=mat.nome: self._on_delete_material(m_nome))
            l_act.addWidget(btn_del)
            self.table.setCellWidget(row, 4, w_act)

    def _on_giro_toggled(self, mat: MaterialDefinition, val: bool) -> None:
        mat.permite_giro = val
        mat.sentido_veio = "indiferente" if val else "longitudinal"
        self.registry.add_or_update_material(mat)
        self._load_table()

    def _on_add_material(self) -> None:
        dlg = MaterialEditDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            new_mat = dlg.get_material_definition()
            if new_mat:
                self.registry.add_or_update_material(new_mat)
                self._load_table()

    def _on_delete_material(self, name: str) -> None:
        res = QMessageBox.question(
            self,
            tr("Remover Material"),
            tr("Deseja realmente remover o material '{nome}' do catálogo?", nome=name),
            QMessageBox.Yes | QMessageBox.No,
        )
        if res == QMessageBox.Yes:
            self.registry.remove_material(name)
            self._load_table()

    def _on_reset_defaults(self) -> None:
        res = QMessageBox.question(
            self,
            tr("Restaurar Padrões"),
            tr("Deseja restaurar todos os materiais originais de fábrica?"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if res == QMessageBox.Yes:
            self.registry.reset_to_defaults()
            self._load_table()


class MaterialEditDialog(QDialog):
    """Diálogo para criar ou editar um padrão de material."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Cadastrar Novo Material"))
        self.resize(400, 240)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.txt_nome = QLineEdit()
        self.txt_nome.setPlaceholderText("Ex: MDF Verde Jade, MDF Freijó Puro")
        form.addRow(tr("Nome do Material:"), self.txt_nome)

        self.cb_cat = QComboBox()
        self.cb_cat.addItem(tr("MDF / MDP (Marcenaria)"), "mdf")
        self.cb_cat.addItem(tr("Pedra / Bancada"), "pedra")
        self.cb_cat.addItem(tr("Madeira Maciça"), "madeira_macica")
        form.addRow(tr("Categoria:"), self.cb_cat)

        self.chk_permite_giro = QCheckBox(tr("Permite rotação 90° no corte (Sem veio / Neutro)"))
        self.chk_permite_giro.setChecked(True)
        self.chk_permite_giro.setToolTip(tr("Desmarque para materiais madeirados ou ripados que exigem veio alinhado"))
        form.addRow(tr("Giro / Veio:"), self.chk_permite_giro)

        self.cb_sentido = QComboBox()
        self.cb_sentido.addItem(tr("Indiferente (Unicolor / TX)"), "indiferente")
        self.cb_sentido.addItem(tr("Longitudinal (No comprimento da chapa)"), "longitudinal")
        self.cb_sentido.addItem(tr("Transversal (Na largura da chapa)"), "transversal")
        form.addRow(tr("Sentido do Veio:"), self.cb_sentido)

        def _on_giro_changed(state):
            is_giro = self.chk_permite_giro.isChecked()
            if is_giro:
                self.cb_sentido.setCurrentIndex(0)
            else:
                self.cb_sentido.setCurrentIndex(1)
        self.chk_permite_giro.stateChanged.connect(_on_giro_changed)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _validate_and_accept(self) -> None:
        nome = self.txt_nome.text().strip()
        if not nome:
            QMessageBox.warning(self, tr("Atenção"), tr("Digite o nome do material."))
            return
        self.accept()

    def get_material_definition(self) -> MaterialDefinition:
        nome = self.txt_nome.text().strip()
        cat = str(self.cb_cat.currentData() or "mdf")
        permite_giro = self.chk_permite_giro.isChecked()
        sentido = str(self.cb_sentido.currentData() or "indiferente")
        return MaterialDefinition(
            nome=nome,
            categoria=cat,
            permite_giro=permite_giro,
            sentido_veio=sentido,
            espessuras=[15.0, 18.0],
            custom=True,
        )
