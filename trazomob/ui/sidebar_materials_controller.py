# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Montagem da aba Materiais e Fitas da barra lateral."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
from ..domain.i18n import tr


class SidebarMateriaisMixin:
    """Cria as secoes de materiais, chapas e fitas."""

    def _build_materiais_section(self) -> None:
        """Monta as secoes de materiais e fitas."""
        # Botão para Gerenciamento do Catálogo Técnico de Materiais
        self.btn_gerenciar_materiais = QPushButton(tr("⚙️ Gerenciar Padrões de Materiais..."))
        self.btn_gerenciar_materiais.setToolTip(tr("Cadastre novos padrões de MDF/pedras e defina se possuem veio orientado ou se permitem giro no corte"))
        self.btn_gerenciar_materiais.setStyleSheet(
            "QPushButton { background-color: #E2E8F0; border: 1px solid #94A3B8; border-radius: 4px; padding: 5px; font-weight: bold; color: #1E293B; }"
            "QPushButton:hover { background-color: #CBD5E1; color: #0F172A; }"
        )
        self.btn_gerenciar_materiais.clicked.connect(self._on_open_materials_manager)
        self.sec_materiais.form_layout.addRow(self.btn_gerenciar_materiais)

        # --- Padrões de MDF e Chapas ---
        from ..domain.materials_catalog import ALL_BOX_MATERIALS, MDF_MATERIALS


        self.cb_material = QComboBox()
        self.cb_material.addItems(ALL_BOX_MATERIALS)
        self.lbl_material_caixa = QLabel(tr("Caixa:"))
        self.sec_materiais.form_layout.addRow(self.lbl_material_caixa, self.cb_material)

        self.cb_espessura = QComboBox()
        self.cb_espessura.addItems(["15 mm", "18 mm", "20 mm", "25 mm", "40 mm"])
        self.lbl_espessura_caixa = QLabel(tr("Esp. Caixa:"))
        self.sec_materiais.form_layout.addRow(self.lbl_espessura_caixa, self.cb_espessura)

        self.cb_fita_caixa = QComboBox()
        self.cb_fita_caixa.addItems([
            tr("Frontal 1L (Bordo Aparente)"),
            tr("2L (Frontal e Traseiro)"),
            tr("4L (Todos os 4 Bordos)"),
            tr("Sem Fita de Borda"),
        ])
        self.lbl_fita_caixa = QLabel(tr("Fita Caixa:"))
        self.sec_materiais.form_layout.addRow(self.lbl_fita_caixa, self.cb_fita_caixa)

        self.cb_material_fita_caixa = QComboBox()
        self.cb_material_fita_caixa.addItems([tr("(Mesmo da Caixa)")] + MDF_MATERIALS)
        self.lbl_material_fita_caixa = QLabel(tr("Padrão Fita Cx:"))
        self.sec_materiais.form_layout.addRow(self.lbl_material_fita_caixa, self.cb_material_fita_caixa)

        self.cb_material_frentes = QComboBox()
        self.cb_material_frentes.addItems([tr("(Mesmo da Caixa)")] + MDF_MATERIALS)
        self.lbl_material_frentes = QLabel(tr("Frentes:"))
        self.sec_materiais.form_layout.addRow(self.lbl_material_frentes, self.cb_material_frentes)

        self.cb_espessura_frentes = QComboBox()
        self.cb_espessura_frentes.addItems([
            tr("(Mesma da Caixa)"),
            "15 mm",
            "18 mm",
            "25 mm",
        ])
        self.lbl_espessura_frentes = QLabel(tr("Esp. Frentes:"))
        self.sec_materiais.form_layout.addRow(self.lbl_espessura_frentes, self.cb_espessura_frentes)

        # Botões para Troca Rápida Global de Cores e Padrões no Ambiente
        self.btn_aplicar_frentes_todos = QPushButton(tr("🎨 Aplicar Padrão de Frentes em Todo o Projeto"))
        self.btn_aplicar_frentes_todos.setToolTip(tr("Substitui o padrão de MDF das frentes (portas e gavetas) de todos os armários da cena"))
        self.btn_aplicar_frentes_todos.setStyleSheet(
            "QPushButton { background-color: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 4px; padding: 5px; font-weight: bold; color: #334155; }"
            "QPushButton:hover { background-color: #E2E8F0; color: #0F172A; border-color: #94A3B8; }"
        )
        self.btn_aplicar_frentes_todos.clicked.connect(self._on_apply_frentes_to_all_modules)
        self.sec_materiais.form_layout.addRow(self.btn_aplicar_frentes_todos)

        self.btn_aplicar_caixa_todos = QPushButton(tr("🪵 Aplicar Padrão de Caixaria em Todo o Projeto"))
        self.btn_aplicar_caixa_todos.setToolTip(tr("Substitui o padrão de MDF da caixaria (laterais, bases, prateleiras) de todos os armários da cena"))
        self.btn_aplicar_caixa_todos.setStyleSheet(
            "QPushButton { background-color: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 4px; padding: 5px; font-weight: bold; color: #334155; }"
            "QPushButton:hover { background-color: #E2E8F0; color: #0F172A; border-color: #94A3B8; }"
        )
        self.btn_aplicar_caixa_todos.clicked.connect(self._on_apply_caixa_to_all_modules)
        self.sec_materiais.form_layout.addRow(self.btn_aplicar_caixa_todos)

        # --- Acabamento das Travessas (Cozinha Inferiores) ---
        self.lbl_travessa_mat_section = QLabel(tr("<b>🔩 Acabamento das Travessas:</b>"))
        self.sec_materiais.form_layout.addRow(self.lbl_travessa_mat_section)

        self.cb_material_travessas = QComboBox()
        self.cb_material_travessas.addItems([tr("(Mesmo da Caixa)")] + MDF_MATERIALS)
        self.lbl_material_travessas = QLabel(tr("Padrão Trav.:"))
        self.sec_materiais.form_layout.addRow(self.lbl_material_travessas, self.cb_material_travessas)

        self.cb_espessura_travessas = QComboBox()
        self.cb_espessura_travessas.addItems([
            tr("(Mesma da Caixa)"),
            "15 mm",
            "18 mm",
            "25 mm",
        ])
        self.lbl_espessura_travessas = QLabel(tr("Esp. Trav.:"))
        self.sec_materiais.form_layout.addRow(self.lbl_espessura_travessas, self.cb_espessura_travessas)

        self.cb_fita_travessas = QComboBox()
        self.cb_fita_travessas.addItems([
            tr("Frontal 1L (Bordo Aparente)"),
            tr("2L (2 Bordos Longos)"),
            tr("4L (Todos os 4 Bordos)"),
            tr("Sem Fita de Borda"),
        ])
        self.lbl_fita_travessas = QLabel(tr("Fita Trav.:"))
        self.sec_materiais.form_layout.addRow(self.lbl_fita_travessas, self.cb_fita_travessas)

        self.cb_material_fita_travessas = QComboBox()
        self.cb_material_fita_travessas.addItems([tr("(Mesmo da Travessa)")] + MDF_MATERIALS)
        self.lbl_material_fita_travessas = QLabel(tr("Padrão Fita Tr.:"))
        self.sec_materiais.form_layout.addRow(self.lbl_material_fita_travessas, self.cb_material_fita_travessas)

        self.btn_aplicar_travessas_todos = QPushButton(tr("🔄 Aplicar Travessas em Todos os Balcões"))
        self.btn_aplicar_travessas_todos.setToolTip(
            tr("Aplica a orientação (em pé/deitada), largura e materiais de travessa selecionados a todos os balcões inferiores da cena")
        )
        self.btn_aplicar_travessas_todos.setStyleSheet(
            "QPushButton { background-color: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 4px; padding: 5px; font-weight: bold; color: #334155; }"
            "QPushButton:hover { background-color: #E2E8F0; color: #0F172A; border-color: #94A3B8; }"
        )
        self.btn_aplicar_travessas_todos.clicked.connect(self._on_apply_travessas_to_all_modules)
        self.sec_materiais.form_layout.addRow(self.btn_aplicar_travessas_todos)

        self._travessa_materiais_widgets = [
            self.lbl_travessa_mat_section,
            self.lbl_material_travessas, self.cb_material_travessas,
            self.lbl_espessura_travessas, self.cb_espessura_travessas,
            self.lbl_fita_travessas, self.cb_fita_travessas,
            self.lbl_material_fita_travessas, self.cb_material_fita_travessas,
            self.btn_aplicar_travessas_todos,
        ]
        for w in self._travessa_materiais_widgets:
            w.setVisible(False)

        self.cb_espessura.currentIndexChanged.connect(self._refresh_recuo_fundo_from_travessa)
        self.cb_espessura_travessas.currentIndexChanged.connect(self._refresh_recuo_fundo_from_travessa)

    def _refresh_recuo_fundo_from_travessa(self, *_args) -> None:
        """Atualiza o recuo do fundo travado quando a espessura da caixa/travessa muda."""
        if hasattr(self, "_sync_recuo_fundo_state"):
            self._sync_recuo_fundo_state()

    def _on_open_materials_manager(self) -> None:
        """Abre a janela de cadastro e gerenciamento de materiais."""
        from .materials_dialog import MaterialsManagerDialog
        from ..domain.materials_catalog import get_all_materials, get_available_mdf_materials
        dlg = MaterialsManagerDialog(parent=self)
        if dlg.exec():
            # Atualiza dinamicamente as opções em todos os comboboxes da aba de materiais
            all_mats = get_all_materials()
            mdf_mats = get_available_mdf_materials()

            for cb, items in (
                (getattr(self, "cb_material", None), all_mats),
                (getattr(self, "cb_material_fita_caixa", None), [tr("(Mesmo da Caixa)")] + mdf_mats),
                (getattr(self, "cb_material_frentes", None), [tr("(Mesmo da Caixa)")] + mdf_mats),
                (getattr(self, "cb_material_fita_frentes", None), [tr("(Mesmo das Frentes)")] + mdf_mats),
                (getattr(self, "cb_material_travessas", None), [tr("(Mesmo da Caixa)")] + mdf_mats),
                (getattr(self, "cb_material_fita_travessas", None), [tr("(Mesmo da Travessa)")] + mdf_mats),
            ):
                if cb is not None:
                    curr_txt = cb.currentText()
                    cb.blockSignals(True)
                    cb.clear()
                    cb.addItems(items)
                    idx = cb.findText(curr_txt)
                    if idx >= 0:
                        cb.setCurrentIndex(idx)
                    cb.blockSignals(False)



# Aliases
SidebarMaterialsMixin = SidebarMateriaisMixin

