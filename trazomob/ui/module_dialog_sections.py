# SPDX-License-Identifier: GPL-3.0-or-later

# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.

"""Seções básicas do formulário: galeria, identificação, medidas e puxadores."""



from __future__ import annotations



from PySide6.QtCore import QSize, Qt

from PySide6.QtWidgets import (

    QCheckBox,

    QComboBox,

    QFrame,

    QGroupBox,

    QHBoxLayout,

    QLabel,

    QLineEdit,

    QListWidget,

    QPushButton,

    QSpinBox,

    QVBoxLayout,

)



from ..domain.catalog import MODULE_CATALOG, USER_MODULE_CATEGORY

from ..ui.icons import make_perfil_diagram_pixmap





class ModuleDialogSectionsMixin:

    """Seções básicas do formulário: galeria, identificação, medidas e puxadores."""



    def _build_gallery_section(self, layout):

        """Painel esquerdo: galeria visual de módulos."""



        # -------------------------------------------------------------------

        # Painel Esquerdo: Galeria Visual de Módulos (Estilo TrazoMob)

        # -------------------------------------------------------------------

        gallery_box = QGroupBox("Catálogo de Módulos TrazoMob")

        v_gallery = QVBoxLayout(gallery_box)

        v_gallery.setContentsMargins(10, 12, 10, 10)

        v_gallery.setSpacing(10)



        # Cabeçalho da Galeria TrazoMob (Título + Filtro de Categoria)

        header_bar = QHBoxLayout()

        header_bar.setSpacing(10)



        self.lbl_cat_title = QLabel("Armários")

        header_bar.addWidget(self.lbl_cat_title)

        header_bar.addStretch()



        self.cb_category = QComboBox()

        self.cb_category.addItems(["Armários"] + [k for k in MODULE_CATALOG.keys() if k != "Armários"] + [USER_MODULE_CATEGORY, "📂 Todas as Categorias"])

        self.cb_category.currentIndexChanged.connect(self._populate_module_cards)

        header_bar.addWidget(self.cb_category)



        v_gallery.addLayout(header_bar)



        # Barra de Busca Instantânea

        search_bar = QHBoxLayout()

        self.txt_search = QLineEdit()

        self.txt_search.setPlaceholderText("🔍 Filtrar módulos por nome...")

        self.txt_search.setClearButtonEnabled(True)

        self.txt_search.textChanged.connect(self._populate_module_cards)

        search_bar.addWidget(self.txt_search)

        v_gallery.addLayout(search_bar)



        # Banner azul TrazoMob

        self.banner = QLabel("clique sobre o módulo para inserir no projeto")

        self.banner.setAlignment(Qt.AlignCenter)

        v_gallery.addWidget(self.banner)



        # Grade / Grid Visual com Miniaturas dos Armários

        self.list_modules = QListWidget()

        self.list_modules.setViewMode(QListWidget.IconMode)

        self.list_modules.setIconSize(QSize(90, 90))

        self.list_modules.setGridSize(QSize(118, 132))

        self.list_modules.setResizeMode(QListWidget.Adjust)

        self.list_modules.setMovement(QListWidget.Static)

        self.list_modules.setWordWrap(True)

        self.list_modules.setSpacing(6)

        self.list_modules.currentItemChanged.connect(self._on_module_card_selected)

        self.list_modules.itemDoubleClicked.connect(lambda _: self._insert_or_update_module())

        v_gallery.addWidget(self.list_modules)



        layout.addWidget(gallery_box, stretch=3)



    def _build_info_section(self, v_props):

        """Card de identificação do módulo selecionado."""



        # Card de Identificação do Módulo Selecionado

        self.card_info = QFrame()

        v_info = QVBoxLayout(self.card_info)

        v_info.setContentsMargins(6, 4, 6, 4)

        v_info.setSpacing(2)



        self.lbl_selected_title = QLabel("Selecione um Módulo")

        v_info.addWidget(self.lbl_selected_title)



        self.lbl_module_desc = QLabel()

        self.lbl_module_desc.setWordWrap(True)

        self.lbl_module_desc.setMaximumHeight(36)

        v_info.addWidget(self.lbl_module_desc)

        v_props.addWidget(self.card_info)



        # Status de Edição Dinâmica

        self.lbl_dyn_status = QLabel()

        self.lbl_dyn_status.setWordWrap(True)

        self.lbl_dyn_status.setStyleSheet("background-color: #E3F2FD; color: #0D47A1; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;")

        v_props.addWidget(self.lbl_dyn_status)



    def _build_dimensions_section(self, form_layout):

        """Medidas principais, caixa e frentes."""



        # Largura com botões rápidos

        h_larg = QHBoxLayout()

        self.sp_largura = QSpinBox()

        self.sp_largura.setRange(1, 3000)

        self.sp_largura.setValue(800)

        self.sp_largura.setSuffix(" mm")

        h_larg.addWidget(self.sp_largura)

        btn_l_minus = QPushButton("-50")

        btn_l_minus.setFixedWidth(38)

        btn_l_minus.clicked.connect(lambda: self.sp_largura.setValue(self.sp_largura.value() - 50))

        h_larg.addWidget(btn_l_minus)

        btn_l_plus = QPushButton("+50")

        btn_l_plus.setFixedWidth(38)

        btn_l_plus.clicked.connect(lambda: self.sp_largura.setValue(self.sp_largura.value() + 50))

        h_larg.addWidget(btn_l_plus)

        form_layout.addRow("Largura Total:", h_larg)



        # Altura com botões rápidos

        h_alt = QHBoxLayout()

        self.sp_altura = QSpinBox()

        self.sp_altura.setRange(1, 3000)

        self.sp_altura.setValue(720)

        self.sp_altura.setSuffix(" mm")

        h_alt.addWidget(self.sp_altura)

        btn_a_minus = QPushButton("-50")

        btn_a_minus.setFixedWidth(38)

        btn_a_minus.clicked.connect(lambda: self.sp_altura.setValue(self.sp_altura.value() - 50))

        h_alt.addWidget(btn_a_minus)

        btn_a_plus = QPushButton("+50")

        btn_a_plus.setFixedWidth(38)

        btn_a_plus.clicked.connect(lambda: self.sp_altura.setValue(self.sp_altura.value() + 50))

        h_alt.addWidget(btn_a_plus)

        form_layout.addRow("Altura Total:", h_alt)



        # Profundidade com botões rápidos

        h_prof = QHBoxLayout()

        self.sp_prof = QSpinBox()

        self.sp_prof.setRange(1, 3000)

        self.sp_prof.setValue(550)



        self.sp_prof.setSuffix(" mm")

        h_prof.addWidget(self.sp_prof)

        btn_p_minus = QPushButton("-50")

        btn_p_minus.setFixedWidth(38)

        btn_p_minus.clicked.connect(lambda: self.sp_prof.setValue(self.sp_prof.value() - 50))

        h_prof.addWidget(btn_p_minus)

        btn_p_plus = QPushButton("+50")

        btn_p_plus.setFixedWidth(38)

        btn_p_plus.clicked.connect(lambda: self.sp_prof.setValue(self.sp_prof.value() + 50))

        h_prof.addWidget(btn_p_plus)

        form_layout.addRow("Profundidade:", h_prof)



        self._step_buttons = [btn_l_minus, btn_l_plus, btn_a_minus, btn_a_plus, btn_p_minus, btn_p_plus]



        # Caixa (Corpo / Bancada)

        from ..domain.materials_catalog import ALL_BOX_MATERIALS, MDF_MATERIALS



        self.cb_material = QComboBox()

        self.cb_material.addItems(ALL_BOX_MATERIALS)

        self.lbl_material_caixa = QLabel("Padrão da Caixa / Pedra:")

        form_layout.addRow(self.lbl_material_caixa, self.cb_material)



        self.cb_espessura = QComboBox()

        self.cb_espessura.addItems(["15 mm", "18 mm", "20 mm", "25 mm", "40 mm"])

        self.lbl_espessura_caixa = QLabel("Espessura:")

        form_layout.addRow(self.lbl_espessura_caixa, self.cb_espessura)



        self.cb_fita_caixa = QComboBox()

        self.cb_fita_caixa.addItems([

            "Frontal 1L (Bordo Aparente)",

            "2L (Frontal e Traseiro)",

            "4L (Todos os 4 Bordos)",

            "Sem Fita de Borda",

        ])

        self.lbl_fita_caixa = QLabel("Fita da Caixa:")

        form_layout.addRow(self.lbl_fita_caixa, self.cb_fita_caixa)



        self.cb_material_fita_caixa = QComboBox()

        self.cb_material_fita_caixa.addItems(["(Mesmo da Caixa)"] + MDF_MATERIALS)

        self.lbl_material_fita_caixa = QLabel("Padrão Fita Caixa:")

        form_layout.addRow(self.lbl_material_fita_caixa, self.cb_material_fita_caixa)



        self.sp_rodape = QSpinBox()

        self.sp_rodape.setRange(0, 300)

        self.sp_rodape.setValue(0)

        self.sp_rodape.setSuffix(" mm")

        self.lbl_rodape = QLabel("Altura Rodapé:")

        form_layout.addRow(self.lbl_rodape, self.sp_rodape)



        # Frentes (Portas e Gavetas independentes)

        self.cb_material_frentes = QComboBox()

        self.cb_material_frentes.addItems(["(Mesmo da Caixa)"] + MDF_MATERIALS)

        self.lbl_material_frentes = QLabel("Padrão das Frentes:")

        form_layout.addRow(self.lbl_material_frentes, self.cb_material_frentes)



        self.cb_espessura_frentes = QComboBox()

        self.cb_espessura_frentes.addItems([

            "(Mesma da Caixa)",

            "15 mm",

            "18 mm",

            "25 mm",

        ])

        self.lbl_espessura_frentes = QLabel("Espessura das Frentes:")

        form_layout.addRow(self.lbl_espessura_frentes, self.cb_espessura_frentes)



    def _build_handles_section(self, form_layout):

        """Puxadores e perfil de alumínio."""



        # Puxadores (Portas e Gavetas)

        self.lbl_puxadores_header = QLabel("<b>🚪 Puxadores (Portas / Gavetas):</b>")

        form_layout.addRow(self.lbl_puxadores_header)



        self.cb_puxador_tipo = QComboBox()

        self.cb_puxador_tipo.addItems([

            "Puxador Alça (Linear / Metálico)",

            "Puxador Perfil (Alumínio)",

            "Puxador Cava (Chanfro 45°)",

            "Puxador Ponto (Botão Minimalista)",

            "Sem Puxador (Toque / Fecho Pulsador)",

        ])

        self.lbl_puxador_tipo = QLabel("Tipo de Puxador:")

        form_layout.addRow(self.lbl_puxador_tipo, self.cb_puxador_tipo)



        self.cb_puxador_cor = QComboBox()

        self.cb_puxador_cor.addItems([

            "Preto Fosco",

            "Alumínio / Inox",

            "Dourado / Champanhe",

            "Cobre / Rosé",

            "Branco",

        ])

        self.lbl_puxador_cor = QLabel("Acabamento Puxador:")

        form_layout.addRow(self.lbl_puxador_cor, self.cb_puxador_cor)



        self.cb_puxador_pos = QComboBox()

        self.cb_puxador_pos.addItems([

            "📌 Automático / Padrão",

            "⬆️ Na Parte de Cima (Topo)",

            "↕️ Na Extensão da Porta (Lateral)",

            "⬇️ Na Parte de Baixo (Base)",

            "🎯 No Centro",

        ])

        self.lbl_puxador_pos = QLabel("Posição do Puxador:")

        form_layout.addRow(self.lbl_puxador_pos, self.cb_puxador_pos)



        # --- Card Estilo TrazoMob: Altura do Puxador Perfil ---

        self.frame_perfil = QFrame()

        self.frame_perfil.setFrameShape(QFrame.StyledPanel)

        self.frame_perfil.setStyleSheet(

            "QFrame { background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; padding: 6px; }"

        )

        layout_perfil = QVBoxLayout(self.frame_perfil)

        layout_perfil.setContentsMargins(6, 6, 6, 6)

        layout_perfil.setSpacing(6)



        h_perfil_head = QHBoxLayout()

        h_perfil_head.setSpacing(8)



        self.lbl_perfil_diagram = QLabel()

        self.lbl_perfil_diagram.setPixmap(make_perfil_diagram_pixmap(115, 80, modelo="gola"))

        self.lbl_perfil_diagram.setStyleSheet("border: 1px solid #94A3B8; border-radius: 4px; background: #E2E8F0;")

        h_perfil_head.addWidget(self.lbl_perfil_diagram)



        v_perfil_text = QVBoxLayout()

        v_perfil_text.setSpacing(2)

        lbl_p_title = QLabel("Puxador Perfil de Alumínio")

        lbl_p_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #1E293B;")

        v_perfil_text.addWidget(lbl_p_title)



        lbl_p_sub = QLabel("Escolha o perfil e a altura de desconto na porta/gaveta")

        lbl_p_sub.setStyleSheet("font-size: 10px; color: #64748B;")

        lbl_p_sub.setWordWrap(True)

        v_perfil_text.addWidget(lbl_p_sub)

        v_perfil_text.addStretch()



        h_perfil_head.addLayout(v_perfil_text)

        layout_perfil.addLayout(h_perfil_head)



        lbl_m_title = QLabel("Modelo do perfil:")

        lbl_m_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #334155;")

        h_mod_row = QHBoxLayout()

        self.cb_perfil_modelo = QComboBox()

        self.cb_perfil_modelo.setStyleSheet("font-size: 11px; padding: 3px;")

        h_mod_row.addWidget(self.cb_perfil_modelo, stretch=1)



        self.btn_gerenciar_perfis = QPushButton("⚙️ Perfis…")

        self.btn_gerenciar_perfis.setToolTip("Abrir editor de perfis (seções 2D personalizadas, medidas e extrusão)")

        self.btn_gerenciar_perfis.setStyleSheet("font-size: 11px; padding: 3px 8px;")

        self.btn_gerenciar_perfis.clicked.connect(self._open_perfis_manager)

        h_mod_row.addWidget(self.btn_gerenciar_perfis)

        layout_perfil.addLayout(h_mod_row)



        lbl_a_title = QLabel("Altura / Desconto do perfil:")

        lbl_a_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #334155;")

        layout_perfil.addWidget(lbl_a_title)



        self.cb_altura_perfil = QComboBox()

        self.cb_altura_perfil.addItems([

            "Padrão do perfil",

            "35 MM",

            "40 MM",

            "38 MM",

            "32 MM",

            "30 MM",

            "25 MM",

            "22 MM",

        ])

        self.cb_altura_perfil.setStyleSheet("font-weight: bold; font-size: 11px; padding: 3px;")

        layout_perfil.addWidget(self.cb_altura_perfil)



        self._refresh_perfil_modelos()

        self.cb_perfil_modelo.currentIndexChanged.connect(self._on_dialog_perfil_modelo_changed)



        form_layout.addRow(self.frame_perfil)



        self.sp_desconto_perfil = QSpinBox()

        self.sp_desconto_perfil.setRange(15, 60)

        self.sp_desconto_perfil.setValue(35)

        self.sp_desconto_perfil.setVisible(False)

        self.cb_altura_perfil.currentTextChanged.connect(self._sync_desconto_perfil_from_combo)



        def _update_dialog_perfil_card(idx):

            is_perfil = (idx == 1)

            self.frame_perfil.setVisible(is_perfil)



        self.cb_puxador_tipo.currentIndexChanged.connect(_update_dialog_perfil_card)

        _update_dialog_perfil_card(self.cb_puxador_tipo.currentIndex())



        self.sp_qtd_elem = QSpinBox()

        self.sp_qtd_elem.setRange(0, 8)

        self.sp_qtd_elem.setValue(2)

        self.lbl_qtd_elem = QLabel("Número de Portas:")

        form_layout.addRow(self.lbl_qtd_elem, self.sp_qtd_elem)

        self.cb_lado_porta_armario = QComboBox()
        self.cb_lado_porta_armario.addItems([
            "⬅️ Dobradiça à Esquerda (Padrão)",
            "➡️ Dobradiça à Direita (Invertido)",
        ])
        self.cb_lado_porta_armario.setToolTip(
            "Define o lado da dobradiça na porta única (1 porta) ou na porta isolada (em módulos ímpares, ex: 3 portas)"
        )
        self.lbl_lado_porta_armario = QLabel("Lado Porta Única/Isolada:")
        form_layout.addRow(self.lbl_lado_porta_armario, self.cb_lado_porta_armario)
        self.lbl_lado_porta_armario.setVisible(False)
        self.cb_lado_porta_armario.setVisible(False)



        self.sp_largura_gaveteiro = QSpinBox()

        self.sp_largura_gaveteiro.setRange(250, 1200)

        self.sp_largura_gaveteiro.setValue(450)

        self.sp_largura_gaveteiro.setSingleStep(50)

        self.sp_largura_gaveteiro.setSuffix(" mm")

        self.sp_largura_gaveteiro.setToolTip("Largura externa da seção de gavetas (balcão misto e rack)")

        self.lbl_largura_gaveteiro = QLabel("Largura do Gaveteiro:")

        form_layout.addRow(self.lbl_largura_gaveteiro, self.sp_largura_gaveteiro)

        self.lbl_largura_gaveteiro.setVisible(False)

        self.sp_largura_gaveteiro.setVisible(False)



        self.cb_lado_gaveteiro = QComboBox()

        self.cb_lado_gaveteiro.addItems([

            "⬅️ À Esquerda",

            "➡️ À Direita",

            "↔️ Ambos os lados",

            "🚫 Sem gavetas",

        ])

        self.cb_lado_gaveteiro.setToolTip("Define em qual lado do módulo fica o gaveteiro (balcão misto e rack)")

        self.lbl_lado_gaveteiro = QLabel("Lado do Gaveteiro:")

        form_layout.addRow(self.lbl_lado_gaveteiro, self.cb_lado_gaveteiro)

        self.lbl_lado_gaveteiro.setVisible(False)

        self.cb_lado_gaveteiro.setVisible(False)



        self.sp_prateleiras = QSpinBox()

        self.sp_prateleiras.setRange(0, 6)

        self.sp_prateleiras.setValue(1)

        form_layout.addRow("Prateleiras Internas:", self.sp_prateleiras)



        # ── Configurações do Balcão de Forno (balcao_forno) ───────────────────

        self.lbl_forno_section = QLabel("<b>🔥 Balcão para Forno Embutido:</b>")

        form_layout.addRow(self.lbl_forno_section)



        self.chk_forno_tem_gaveta = QCheckBox("Possui Gaveta Inferior")

        self.chk_forno_tem_gaveta.setChecked(True)

        self.chk_forno_tem_gaveta.setToolTip(

            "Ativado: cria uma gaveta na parte inferior com prateleira de apoio acima dela e frente cega superior.\n"

            "Desativado: frente cega ocupa toda a altura da caixa para embutir o forno direto."

        )

        self.lbl_forno_tem_gaveta = QLabel("Gaveta Inferior:")

        form_layout.addRow(self.lbl_forno_tem_gaveta, self.chk_forno_tem_gaveta)



        self.sp_forno_alt_gaveta = QSpinBox()

        self.sp_forno_alt_gaveta.setRange(80, 500)

        self.sp_forno_alt_gaveta.setValue(150)

        self.sp_forno_alt_gaveta.setSuffix(" mm")

        self.sp_forno_alt_gaveta.setToolTip("Altura do vão da gaveta inferior (o restante vira a frente cega para embutir)")

        self.lbl_forno_alt_gaveta = QLabel("Altura da Gaveta:")

        form_layout.addRow(self.lbl_forno_alt_gaveta, self.sp_forno_alt_gaveta)



        self._forno_widgets = [

            self.lbl_forno_section,

            self.lbl_forno_tem_gaveta, self.chk_forno_tem_gaveta,

            self.lbl_forno_alt_gaveta, self.sp_forno_alt_gaveta,

        ]

        for w in self._forno_widgets:

            w.setVisible(False)



        def _on_forno_tem_gaveta_toggle(state):

            tem_g = self.chk_forno_tem_gaveta.isChecked()

            is_forno = getattr(self, "_current_module_id", "") == "balcao_forno"

            self.lbl_forno_alt_gaveta.setVisible(is_forno and tem_g)

            self.sp_forno_alt_gaveta.setVisible(is_forno and tem_g)

            if hasattr(self, "_gaveta_widgets") and is_forno:

                for gw in self._gaveta_widgets:

                    gw.setVisible(tem_g)

        self.chk_forno_tem_gaveta.stateChanged.connect(_on_forno_tem_gaveta_toggle)



        # ── Configurações de Caixa para Geladeira (caixa_geladeira) ───────────

        self.lbl_geladeira_section = QLabel("<b>❄️ Nicho para Geladeira & Maleiro:</b>")

        form_layout.addRow(self.lbl_geladeira_section)



        self.sp_geladeira_alt_nicho = QSpinBox()

        self.sp_geladeira_alt_nicho.setRange(1200, 2400)

        self.sp_geladeira_alt_nicho.setValue(1800)

        self.sp_geladeira_alt_nicho.setSuffix(" mm")

        self.sp_geladeira_alt_nicho.setToolTip("Altura livre interna do nicho para a geladeira")

        self.lbl_geladeira_alt_nicho = QLabel("Altura do Vão da Geladeira:")

        form_layout.addRow(self.lbl_geladeira_alt_nicho, self.sp_geladeira_alt_nicho)



        self.cb_geladeira_tipo_porta = QComboBox()

        self.cb_geladeira_tipo_porta.addItems([

            "2 Portas de Abrir",

            "1 Porta Basculante",

        ])

        self.lbl_geladeira_tipo_porta = QLabel("Portas do Maleiro:")

        form_layout.addRow(self.lbl_geladeira_tipo_porta, self.cb_geladeira_tipo_porta)



        self._geladeira_widgets = [

            self.lbl_geladeira_section,

            self.lbl_geladeira_alt_nicho, self.sp_geladeira_alt_nicho,

            self.lbl_geladeira_tipo_porta, self.cb_geladeira_tipo_porta,

        ]

        for w in self._geladeira_widgets:

            w.setVisible(False)



        # ── Configurações de Aéreo Micro-ondas ──────────────────────────────────

        self.lbl_micro_section = QLabel("<b>🚪 Portas do Micro-ondas:</b>")

        form_layout.addRow(self.lbl_micro_section)



        self.cb_micro_tipo_porta = QComboBox()

        self.cb_micro_tipo_porta.addItems([

            "1 Porta Basculante",

            "2 Portas de Abrir",

        ])

        self.lbl_micro_tipo_porta = QLabel("Tipo de Porta:")

        form_layout.addRow(self.lbl_micro_tipo_porta, self.cb_micro_tipo_porta)



        self._micro_widgets = [

            self.lbl_micro_section,

            self.lbl_micro_tipo_porta, self.cb_micro_tipo_porta,

        ]

        for w in self._micro_widgets:

            w.setVisible(False)

