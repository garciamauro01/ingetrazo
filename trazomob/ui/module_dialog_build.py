# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Montagem da janela e orquestração das seções do formulário TrazoMob."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class ModuleDialogBuildMixin:
    """Montagem da janela e orquestração das seções do formulário TrazoMob."""

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: Módulos Paramétricos Dinâmicos
        tab_modules = QWidget()
        self._build_modules_tab(tab_modules)
        self.tabs.addTab(tab_modules, "🗂️ Módulos Dinâmicos (TrazoMob)")

        # Tab 2: Lista de Peças e TrazoMob
        tab_cutlist = QWidget()
        self._build_cutlist_tab(tab_cutlist)
        self.tabs.addTab(tab_cutlist, "📋 Lista de Peças & TrazoMob")

        footer = QHBoxLayout()
        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(self.close)
        footer.addWidget(btn_close)
        footer.addStretch()
        main_layout.addLayout(footer)

        self._apply_dialog_styles()

    def _build_modules_tab(self, parent_widget):
        layout = QHBoxLayout(parent_widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(14)

        self._build_gallery_section(layout)

        # -------------------------------------------------------------------
        # Painel Direito: Configuração das Medidas e Ações (Fixo ~340px)
        # -------------------------------------------------------------------
        props_box = QGroupBox("Propriedades e Dimensões")
        props_box.setMinimumWidth(320)
        props_box.setMaximumWidth(400)
        v_props = QVBoxLayout(props_box)
        v_props.setContentsMargins(8, 8, 8, 8)
        v_props.setSpacing(6)

        self._build_info_section(v_props)

        # Formulário de Medidas Dinâmicas com Ajustes Rápidos (+/- 50mm)
        scroll_form = QScrollArea()
        scroll_form.setWidgetResizable(True)
        scroll_form.setFrameShape(QFrame.NoFrame)
        scroll_form.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setContentsMargins(0, 2, 0, 2)
        form_layout.setSpacing(6)

        self._build_dimensions_section(form_layout)
        self._build_handles_section(form_layout)
        if hasattr(self, "_build_hardware_section"):
            self._build_hardware_section(form_layout)
        self._build_travessas_section(form_layout)
        self._build_drawers_countertop_section(form_layout)
        self._build_back_section(form_layout)
        self._build_alignment_section(form_layout)

        scroll_form.setWidget(form_widget)
        v_props.addWidget(scroll_form)

        self._build_actions_section(v_props)

        layout.addWidget(props_box, stretch=2)

        if hasattr(self, "_sync_category_for_editing_module"):
            self._sync_category_for_editing_module()
        self._populate_module_cards()
        self._load_module_values_if_editing()
