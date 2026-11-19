# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Seções avançadas do formulário: travessas, gavetas, fundo, alinhamento e ações."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)


class ModuleDialogOptionsMixin:
    """Seções avançadas do formulário: travessas, gavetas, fundo, alinhamento e ações."""

    def _build_travessas_section(self, form_layout):
        """Configurações de travessas."""

        # ── Configurações de Travessas (Cozinha Inferiores) ─────────────────────
        self.lbl_travessa_section = QLabel("<b>⚙️ Travessas Superiores:</b>")
        form_layout.addRow(self.lbl_travessa_section)

        # Balcão padrão: largura das travessas frontal e traseira
        self.sp_larg_travessa_frontal = QSpinBox()
        self.sp_larg_travessa_frontal.setRange(20, 300)
        self.sp_larg_travessa_frontal.setValue(70)
        self.sp_larg_travessa_frontal.setSuffix(" mm")
        self.sp_larg_travessa_frontal.setToolTip("Largura (profundidade visível) da travessa frontal superior")
        self.lbl_larg_travessa_frontal = QLabel("Travessa Frontal:")
        form_layout.addRow(self.lbl_larg_travessa_frontal, self.sp_larg_travessa_frontal)

        self.sp_larg_travessa_traseira = QSpinBox()
        self.sp_larg_travessa_traseira.setRange(20, 300)
        self.sp_larg_travessa_traseira.setValue(70)
        self.sp_larg_travessa_traseira.setSuffix(" mm")
        self.sp_larg_travessa_traseira.setToolTip("Largura (profundidade visível) da travessa traseira superior")
        self.lbl_larg_travessa_traseira = QLabel("Travessa Traseira:")
        form_layout.addRow(self.lbl_larg_travessa_traseira, self.sp_larg_travessa_traseira)

        # Balcão de pia: travessa frontal em pé (vertical)
        self.chk_travessa_em_pe = QCheckBox("Travessa frontal em pé (vertical)")
        self.chk_travessa_em_pe.setChecked(True)
        self.chk_travessa_em_pe.setToolTip(
            "Ativado: travessa frontal ocupa toda a altura da caixa (estilo balcão de pia).\n"
            "Desativado: travessa deitada, estilo balcão comum."
        )
        self.lbl_travessa_em_pe = QLabel("Orientação Frontal:")
        form_layout.addRow(self.lbl_travessa_em_pe, self.chk_travessa_em_pe)

        # Travessa traseira em pé (vertical)
        self.chk_travessa_traseira_em_pe = QCheckBox("Travessa traseira em pé (vertical)")
        self.chk_travessa_traseira_em_pe.setChecked(False)
        self.chk_travessa_traseira_em_pe.setToolTip(
            "Ativado: travessa traseira fica em pé (vertical), apoiada na lateral traseira.\n"
            "Desativado: travessa deitada (horizontal), padrão para a maioria dos módulos."
        )
        self.lbl_travessa_traseira_em_pe = QLabel("Orientação Traseira:")
        form_layout.addRow(self.lbl_travessa_traseira_em_pe, self.chk_travessa_traseira_em_pe)

        self.sp_recuo_porta_pia = QSpinBox()
        self.sp_recuo_porta_pia.setRange(0, 200)
        self.sp_recuo_porta_pia.setValue(50)
        self.sp_recuo_porta_pia.setSuffix(" mm")
        self.sp_recuo_porta_pia.setToolTip(
            "Rebaixo do topo das portas em relação ao topo do móvel quando a travessa frontal está em pé.\n"
            "Padrão: 50 mm (as portas começam mais baixas para liberar o visual/pingadeira da pia)."
        )
        self.lbl_recuo_porta_pia = QLabel("Rebaixo Superior Portas:")
        form_layout.addRow(self.lbl_recuo_porta_pia, self.sp_recuo_porta_pia)

        # Padrão e Espessura das Travessas
        self.cb_material_travessas = QComboBox()
        self.cb_material_travessas.addItems([
            "(Mesmo da Caixa)",
            "MDF Branco TX",
            "MDF Louro Freijó",
            "MDF Carvalho Boreal",
            "MDF Grafite",
            "MDF Cinza Sagrado",
        ])
        self.lbl_material_travessas = QLabel("Padrão Travessas:")
        form_layout.addRow(self.lbl_material_travessas, self.cb_material_travessas)

        self.cb_espessura_travessas = QComboBox()
        self.cb_espessura_travessas.addItems([
            "(Mesma da Caixa)",
            "15 mm",
            "18 mm",
            "25 mm",
        ])
        self.lbl_espessura_travessas = QLabel("Espessura Travessas:")
        form_layout.addRow(self.lbl_espessura_travessas, self.cb_espessura_travessas)

        # Fita de borda das travessas
        self.cb_fita_travessas = QComboBox()
        self.cb_fita_travessas.addItems([
            "Frontal 1L (Bordo Aparente)",
            "2L (2 Bordos Longos)",
            "4L (Todos os 4 Bordos)",
            "Sem Fita de Borda",
        ])
        self.lbl_fita_travessas = QLabel("Fita de Borda Trav.:")
        form_layout.addRow(self.lbl_fita_travessas, self.cb_fita_travessas)

        self.cb_material_fita_travessas = QComboBox()
        self.cb_material_fita_travessas.addItems([
            "(Mesmo da Travessa)",
            "MDF Branco TX",
            "MDF Louro Freijó",
            "MDF Carvalho Boreal",
            "MDF Grafite",
            "MDF Cinza Sagrado",
        ])
        self.lbl_material_fita_travessas = QLabel("Padrão Fita Trav.:")
        form_layout.addRow(self.lbl_material_fita_travessas, self.cb_material_fita_travessas)

        # Ocultar seção de travessas por padrão — aparece só para módulos relevantes
        self._travessa_widgets = [
            self.lbl_travessa_section,
            self.lbl_larg_travessa_frontal, self.sp_larg_travessa_frontal,
            self.lbl_larg_travessa_traseira, self.sp_larg_travessa_traseira,
            self.lbl_travessa_em_pe, self.chk_travessa_em_pe,
            self.lbl_travessa_traseira_em_pe, self.chk_travessa_traseira_em_pe,
            self.lbl_recuo_porta_pia, self.sp_recuo_porta_pia,
            self.lbl_material_travessas, self.cb_material_travessas,
            self.lbl_espessura_travessas, self.cb_espessura_travessas,
            self.lbl_fita_travessas, self.cb_fita_travessas,
            self.lbl_material_fita_travessas, self.cb_material_fita_travessas,
        ]
        for w in self._travessa_widgets:
            w.setVisible(False)

        # Conectar checkbox para mostrar/esconder recuo quando travessa frontal em pé
        def _on_travessa_em_pe_changed(state):
            em_pe = self.chk_travessa_em_pe.isChecked()
            self.lbl_recuo_porta_pia.setVisible(em_pe)
            self.sp_recuo_porta_pia.setVisible(em_pe)
        self.chk_travessa_em_pe.stateChanged.connect(_on_travessa_em_pe_changed)

    def _build_drawers_countertop_section(self, form_layout):
        """Caixa de gaveta e pedra/bancada."""

        # ── Configurações da Caixa de Gaveta ──────────────────────────────────
        self.lbl_gaveta_section = QLabel("<b>⚙️ Caixa de Gaveta:</b>")
        form_layout.addRow(self.lbl_gaveta_section)

        self.cb_tipo_fundo_gaveta = QComboBox()
        self.cb_tipo_fundo_gaveta.addItems([
            "Canal / Rasgo Lateral",
            "Por Baixo (Sobreposto)",
        ])
        self.lbl_tipo_fundo_gaveta = QLabel("Montagem Fundo Gav.:")
        form_layout.addRow(self.lbl_tipo_fundo_gaveta, self.cb_tipo_fundo_gaveta)

        self.sp_folga_corredica = QSpinBox()
        self.sp_folga_corredica.setRange(10, 50)
        self.sp_folga_corredica.setValue(26)
        self.sp_folga_corredica.setSuffix(" mm")
        self.sp_folga_corredica.setToolTip("Vão / folga total a descontar da largura da caixa para corrediças (ex.: 26mm = 13mm de cada lado)")
        self.lbl_folga_corredica = QLabel("Folga Corrediças:")
        form_layout.addRow(self.lbl_folga_corredica, self.sp_folga_corredica)

        self.cb_material_gaveta = QComboBox()
        self.cb_material_gaveta.addItems([
            "(Mesmo da Caixa)",
            "MDF Branco TX",
            "MDF Louro Freijó",
            "MDF Carvalho Boreal",
            "MDF Grafite",
            "MDF Cinza Sagrado",
        ])
        self.lbl_material_gaveta = QLabel("Material Gaveta:")
        form_layout.addRow(self.lbl_material_gaveta, self.cb_material_gaveta)

        self.cb_espessura_gaveta = QComboBox()
        self.cb_espessura_gaveta.addItems([
            "15 mm",
            "18 mm",
        ])
        self.lbl_espessura_gaveta = QLabel("Espessura Gaveta:")
        form_layout.addRow(self.lbl_espessura_gaveta, self.cb_espessura_gaveta)

        self.cb_material_fita_gaveta = QComboBox()
        self.cb_material_fita_gaveta.addItems([
            "(Mesmo da Gaveta)",
            "MDF Branco TX",
            "MDF Louro Freijó",
            "MDF Carvalho Boreal",
            "MDF Grafite",
            "MDF Cinza Sagrado",
        ])
        self.lbl_material_fita_gaveta = QLabel("Fita Borda Gaveta:")
        form_layout.addRow(self.lbl_material_fita_gaveta, self.cb_material_fita_gaveta)

        self.cb_material_fundo_gaveta = QComboBox()
        self.cb_material_fundo_gaveta.addItems([
            "(Padrão Fundo)",
            "MDF Branco TX",
            "MDF Louro Freijó",
            "MDF Carvalho Boreal",
            "MDF Grafite",
            "MDF Cinza Sagrado",
        ])
        self.lbl_material_fundo_gaveta = QLabel("Material Fundo Gav.:")
        form_layout.addRow(self.lbl_material_fundo_gaveta, self.cb_material_fundo_gaveta)

        self.cb_esp_fundo_gaveta = QComboBox()
        self.cb_esp_fundo_gaveta.addItems([
            "6 mm",
            "3 mm",
            "15 mm",
        ])
        self.lbl_esp_fundo_gaveta = QLabel("Espessura Fundo Gav.:")
        form_layout.addRow(self.lbl_esp_fundo_gaveta, self.cb_esp_fundo_gaveta)

        self._gaveta_widgets = [
            self.lbl_gaveta_section,
            self.lbl_tipo_fundo_gaveta, self.cb_tipo_fundo_gaveta,
            self.lbl_folga_corredica, self.sp_folga_corredica,
            self.lbl_material_gaveta, self.cb_material_gaveta,
            self.lbl_espessura_gaveta, self.cb_espessura_gaveta,
            self.lbl_material_fita_gaveta, self.cb_material_fita_gaveta,
            self.lbl_material_fundo_gaveta, self.cb_material_fundo_gaveta,
            self.lbl_esp_fundo_gaveta, self.cb_esp_fundo_gaveta,
        ]
        for w in self._gaveta_widgets:
            w.setVisible(False)

        # ── Configurações de Marmoraria / Bancadas de Pedra ────────────────────
        self.lbl_pedra_section = QLabel("<b>🪨 Marmoraria & Bancada de Pedra:</b>")
        form_layout.addRow(self.lbl_pedra_section)

        self.sp_esp_pedra = QSpinBox()
        self.sp_esp_pedra.setRange(10, 60)
        self.sp_esp_pedra.setValue(20)
        self.sp_esp_pedra.setSuffix(" mm")
        self.sp_esp_pedra.setToolTip("Espessura da chapa de pedra (padrão: 20mm)")
        self.lbl_esp_pedra = QLabel("Espessura da Pedra:")
        form_layout.addRow(self.lbl_esp_pedra, self.sp_esp_pedra)

        self.sp_altura_saia = QSpinBox()
        self.sp_altura_saia.setRange(20, 200)
        self.sp_altura_saia.setValue(40)
        self.sp_altura_saia.setSuffix(" mm")
        self.sp_altura_saia.setToolTip("Altura da saia/testeira engrossada frontal (padrão: 40mm ou 60mm)")
        self.lbl_altura_saia = QLabel("Altura da Saia / Testeira:")
        form_layout.addRow(self.lbl_altura_saia, self.sp_altura_saia)

        self.sp_altura_frontao = QSpinBox()
        self.sp_altura_frontao.setRange(0, 300)
        self.sp_altura_frontao.setValue(100)
        self.sp_altura_frontao.setSuffix(" mm")
        self.sp_altura_frontao.setToolTip("Altura do rodabanca/frontão na parede (padrão: 100mm)")
        self.lbl_altura_frontao = QLabel("Rodabanca / Frontão:")
        form_layout.addRow(self.lbl_altura_frontao, self.sp_altura_frontao)

        self.sp_larg_asa_esq = QSpinBox()
        self.sp_larg_asa_esq.setRange(300, 1200)
        self.sp_larg_asa_esq.setSingleStep(50)
        self.sp_larg_asa_esq.setValue(550)
        self.sp_larg_asa_esq.setSuffix(" mm")
        self.sp_larg_asa_esq.setToolTip("Profundidade da asa esquerda do balcão em L (padrão: 550mm)")
        self.lbl_larg_asa_esq = QLabel("Prof. Asa Esquerda:")
        form_layout.addRow(self.lbl_larg_asa_esq, self.sp_larg_asa_esq)

        self.sp_larg_asa_dir = QSpinBox()
        self.sp_larg_asa_dir.setRange(300, 1200)
        self.sp_larg_asa_dir.setSingleStep(50)
        self.sp_larg_asa_dir.setValue(550)
        self.sp_larg_asa_dir.setSuffix(" mm")
        self.sp_larg_asa_dir.setToolTip("Profundidade da asa direita do balcão em L (padrão: 550mm)")
        self.lbl_larg_asa_dir = QLabel("Prof. Asa Direita:")
        form_layout.addRow(self.lbl_larg_asa_dir, self.sp_larg_asa_dir)

        self.chk_batente_canto = QCheckBox("Batente de quina interna")
        self.chk_batente_canto.setToolTip(
            "Fecha o vão interno de 90° com um montante da mesma espessura/material "
            "das portas. Desmarque para manter o cruzamento atual das portas.")
        self.lbl_batente_canto = QLabel("Quina Interna:")
        form_layout.addRow(self.lbl_batente_canto, self.chk_batente_canto)
        self.lbl_batente_canto.setVisible(False)
        self.chk_batente_canto.setVisible(False)

        self.chk_tem_saia_esq = QCheckBox("Saia Lateral Esquerda")
        self.chk_tem_saia_esq.setChecked(True)
        self.lbl_tem_saia_esq = QLabel("Saia Esquerda:")
        form_layout.addRow(self.lbl_tem_saia_esq, self.chk_tem_saia_esq)

        self.chk_tem_saia_dir = QCheckBox("Saia Lateral Direita")
        self.chk_tem_saia_dir.setChecked(True)
        self.lbl_tem_saia_dir = QLabel("Saia Direita:")
        form_layout.addRow(self.lbl_tem_saia_dir, self.chk_tem_saia_dir)

        self.cb_tipo_cuba = QComboBox()
        self.cb_tipo_cuba.addItems([
            "Cuba Inox Simples",
            "Cuba Inox Dupla",
            "Cuba Esculpida na Pedra",
            "Sem Cuba (Tampo Cego)",
        ])
        self.lbl_tipo_cuba = QLabel("Modelo da Cuba:")
        form_layout.addRow(self.lbl_tipo_cuba, self.cb_tipo_cuba)

        self.cb_posicao_cuba = QComboBox()
        self.cb_posicao_cuba.addItems([
            "🎯 Centralizada",
            "⬅️ À Esquerda",
            "➡️ À Direita",
        ])
        self.lbl_posicao_cuba = QLabel("Posição da Cuba:")
        form_layout.addRow(self.lbl_posicao_cuba, self.cb_posicao_cuba)

        self.chk_tem_torneira = QCheckBox("Incluir Torneira Gourmet")
        self.chk_tem_torneira.setChecked(True)
        self.lbl_tem_torneira = QLabel("Metais / Torneira:")
        form_layout.addRow(self.lbl_tem_torneira, self.chk_tem_torneira)

        self.cb_canto_recorte = QComboBox()
        self.cb_canto_recorte.addItems(["Cantos Arredondados (R20)", "Cantos Retos 90°"])
        self.lbl_canto_recorte = QLabel("Recorte da Cuba:")
        form_layout.addRow(self.lbl_canto_recorte, self.cb_canto_recorte)

        self.chk_tem_area_molhada = QCheckBox("Área Molhada Rebaixada")
        self.chk_tem_area_molhada.setChecked(True)
        self.lbl_tem_area_molhada = QLabel("Área Molhada:")
        form_layout.addRow(self.lbl_tem_area_molhada, self.chk_tem_area_molhada)

        self._pedra_widgets = [
            self.lbl_pedra_section,
            self.lbl_esp_pedra, self.sp_esp_pedra,
            self.lbl_altura_saia, self.sp_altura_saia,
            self.lbl_altura_frontao, self.sp_altura_frontao,
            self.lbl_larg_asa_esq, self.sp_larg_asa_esq,
            self.lbl_larg_asa_dir, self.sp_larg_asa_dir,
            self.lbl_tem_saia_esq, self.chk_tem_saia_esq,
            self.lbl_tem_saia_dir, self.chk_tem_saia_dir,
            self.lbl_tipo_cuba, self.cb_tipo_cuba,
            self.lbl_posicao_cuba, self.cb_posicao_cuba,
            self.lbl_tem_torneira, self.chk_tem_torneira,
            self.lbl_canto_recorte, self.cb_canto_recorte,
            self.lbl_tem_area_molhada, self.chk_tem_area_molhada,
        ]
        for w in self._pedra_widgets:
            w.setVisible(False)

        # ── Configurações de Prateleiras Avulsas (peca_prateleiras_avulsas) ────
        self.lbl_prat_avulsas_section = QLabel("<b>📚 Prateleiras Avulsas:</b>")
        form_layout.addRow(self.lbl_prat_avulsas_section)

        self.chk_prat_has_primeira = QCheckBox("Criar primeira prateleira (Base)")
        self.chk_prat_has_primeira.setChecked(False)
        self.chk_prat_has_primeira.setToolTip("Gera uma prateleira exatamente na base inferior do vão delimitado")
        self.lbl_prat_has_primeira = QLabel("Primeira Prateleira:")
        form_layout.addRow(self.lbl_prat_has_primeira, self.chk_prat_has_primeira)

        self.chk_prat_has_ultima = QCheckBox("Criar última prateleira (Topo)")
        self.chk_prat_has_ultima.setChecked(False)
        self.chk_prat_has_ultima.setToolTip("Gera uma prateleira exatamente no topo superior do vão delimitado")
        self.lbl_prat_has_ultima = QLabel("Última Prateleira:")
        form_layout.addRow(self.lbl_prat_has_ultima, self.chk_prat_has_ultima)

        self._prat_avulsas_widgets = [
            self.lbl_prat_avulsas_section,
            self.lbl_prat_has_primeira, self.chk_prat_has_primeira,
            self.lbl_prat_has_ultima, self.chk_prat_has_ultima,
        ]
        for pw in self._prat_avulsas_widgets:
            pw.setVisible(False)

    def _build_back_section(self, form_layout):
        """Fundo do móvel."""

        # Fundo do móvel (agrupador para ocultar quando for pedra)
        self.lbl_fundo_section = QLabel("<b>⚙️ Fundo do Móvel (TrazoMob):</b>")
        form_layout.addRow(self.lbl_fundo_section)

        self.cb_tipo_fundo = QComboBox()
        self.cb_tipo_fundo.addItems([
            "Canal / Rasgo",
            "Sobreposto",
            "Sem Fundo",
        ])
        self.cb_tipo_fundo.currentIndexChanged.connect(self._on_tipo_fundo_changed)
        self.lbl_tipo_fundo = QLabel("Tipo de Fundo:")
        form_layout.addRow(self.lbl_tipo_fundo, self.cb_tipo_fundo)

        self.cb_esp_fundo = QComboBox()
        self.cb_esp_fundo.addItems(["6 mm", "3 mm", "15 mm"])
        self.lbl_esp_fundo = QLabel("Espessura Fundo:")
        form_layout.addRow(self.lbl_esp_fundo, self.cb_esp_fundo)

        self.sp_recuo_fundo = QSpinBox()
        self.sp_recuo_fundo.setRange(0, 100)
        self.sp_recuo_fundo.setValue(10)
        self.sp_recuo_fundo.setSuffix(" mm")
        self.lbl_recuo_fundo = QLabel("Recuo Traseiro:")
        form_layout.addRow(self.lbl_recuo_fundo, self.sp_recuo_fundo)

        self.sp_prof_rasgo = QSpinBox()
        self.sp_prof_rasgo.setRange(1, 15)
        self.sp_prof_rasgo.setValue(5)
        self.sp_prof_rasgo.setSuffix(" mm")
        self.lbl_prof_rasgo = QLabel("Prof. do Rasgo:")
        form_layout.addRow(self.lbl_prof_rasgo, self.sp_prof_rasgo)

        self.sp_folga_fundo = QSpinBox()
        self.sp_folga_fundo.setRange(0, 20)
        self.sp_folga_fundo.setValue(2)
        self.sp_folga_fundo.setSuffix(" mm")
        self.lbl_folga_fundo = QLabel("Folga do Fundo:")
        form_layout.addRow(self.lbl_folga_fundo, self.sp_folga_fundo)

        self.chk_fundo = QCheckBox()
        self.chk_fundo.setChecked(True)

        self._fundo_widgets = [
            self.lbl_fundo_section,
            self.lbl_tipo_fundo, self.cb_tipo_fundo,
            self.lbl_esp_fundo, self.cb_esp_fundo,
            self.lbl_recuo_fundo, self.sp_recuo_fundo,
            self.lbl_prof_rasgo, self.sp_prof_rasgo,
            self.lbl_folga_fundo, self.sp_folga_fundo,
        ]

    def _build_alignment_section(self, form_layout):
        """Alinhamento, encaixe e rotação no 3D."""

        # Seção de Alinhamento e Encaixe (Estilo TrazoMob)
        form_layout.addRow(QLabel("<b>Alinhamento & Encaixe (TrazoMob):</b>"))

        self.cb_align_mode = QComboBox()
        self.cb_align_mode.addItems([
            "➡️ Ao lado (Direita)",
            "⬅️ Ao lado (Esquerda)",
            "⬆️ Sobrepor (Acima)",
            "🎯 Livre (Câmera)",
        ])
        form_layout.addRow("Posição ao Inserir:", self.cb_align_mode)

        self.cb_orientacao = QComboBox()
        self.cb_orientacao.addItems([
            "0° (Frente / Padrão)",
            "90° (Giro Horário / Parede Lateral Dir)",
            "180° (Costas / Invertido)",
            "270° (Giro Anti-horário / Parede Lateral Esq)",
        ])
        form_layout.addRow("Orientação ao Inserir:", self.cb_orientacao)

        self.sp_align_gap = QSpinBox()
        self.sp_align_gap.setRange(0, 500)
        self.sp_align_gap.setValue(0)
        self.sp_align_gap.setSuffix(" mm")
        form_layout.addRow("Folga / Vão:", self.sp_align_gap)

        self.lbl_align_ref = QLabel("📌 Encostar em: Origem (1º Módulo)")
        self.lbl_align_ref.setStyleSheet("font-size: 11px; font-style: italic; color: #64748B;")
        form_layout.addRow("", self.lbl_align_ref)

        h_align_btns = QHBoxLayout()
        btn_al_left = QPushButton("⬅️ Esq")
        btn_al_left.setToolTip("Encosta o módulo na lateral esquerda do vizinho")
        btn_al_left.clicked.connect(lambda: self._align_module("left"))
        h_align_btns.addWidget(btn_al_left)

        btn_al_right = QPushButton("➡️ Dir")
        btn_al_right.setToolTip("Encosta o módulo na lateral direita do vizinho")
        btn_al_right.clicked.connect(lambda: self._align_module("right"))
        h_align_btns.addWidget(btn_al_right)

        btn_al_z = QPushButton("📐 Altura")
        btn_al_z.setToolTip("Nivela a altura Z da base com o vizinho")
        btn_al_z.clicked.connect(lambda: self._align_module("height"))
        h_align_btns.addWidget(btn_al_z)

        btn_al_y = QPushButton("🧱 Parede")
        btn_al_y.setToolTip("Alinha o fundo / parede (profundidade Y) com o vizinho")
        btn_al_y.clicked.connect(lambda: self._align_module("depth"))
        h_align_btns.addWidget(btn_al_y)

        form_layout.addRow("Ajustar no 3D:", h_align_btns)

        h_rot_btns = QHBoxLayout()
        btn_rot_ccw = QPushButton("↺ Girar 90° Esq")
        btn_rot_ccw.setToolTip("Gira o módulo 90° para a esquerda (anti-horário)")
        btn_rot_ccw.clicked.connect(lambda: self._rotate_selected_module(-90.0))
        h_rot_btns.addWidget(btn_rot_ccw)

        btn_rot_cw = QPushButton("↻ Girar 90° Dir")
        btn_rot_cw.setToolTip("Gira o módulo 90° para a direita (horário)")
        btn_rot_cw.clicked.connect(lambda: self._rotate_selected_module(90.0))
        h_rot_btns.addWidget(btn_rot_cw)

        form_layout.addRow("Girar no 3D (90°):", h_rot_btns)

        self._align_buttons = [btn_al_left, btn_al_right, btn_al_z, btn_al_y, btn_rot_ccw, btn_rot_cw]

    def _build_actions_section(self, v_props):
        """Botões de ação, gestão e abertura 3D."""

        # Botões de Ação
        self.btn_insert = QPushButton("✨ Inserir no Projeto")
        self.btn_insert.setStyleSheet(
            "background-color: #1976D2; color: white; font-weight: bold; padding: 9px 12px; font-size: 12px; border-radius: 5px;"
        )
        self.btn_insert.clicked.connect(self._insert_or_update_module)
        v_props.addWidget(self.btn_insert)

        # Ações de Gestão do Módulo Selecionado (Duplicar, Novo, Excluir)
        h_dup_del = QHBoxLayout()
        h_dup_del.setSpacing(4)
        self.btn_duplicate = QPushButton("📋 Duplicar")
        self.btn_duplicate.setToolTip("Clona o módulo selecionado ao lado com todas as suas medidas e configurações (Atalho: Ctrl+D)")
        self.btn_duplicate.setStyleSheet(
            "QPushButton { background-color: #0284c7; color: white; font-weight: bold; padding: 5px 8px; border-radius: 4px; font-size: 11px; }"
            "QPushButton:disabled { background-color: #64748b; color: #cbd5e1; }"
        )
        self.btn_duplicate.clicked.connect(self._duplicate_selected_module)
        h_dup_del.addWidget(self.btn_duplicate)

        self.btn_new_mode = QPushButton("✨ Novo")
        self.btn_new_mode.setToolTip("Limpa seleção para criar um novo móvel")
        self.btn_new_mode.setStyleSheet("padding: 5px 8px; font-size: 11px;")
        self.btn_new_mode.clicked.connect(self._reset_to_new_module)
        h_dup_del.addWidget(self.btn_new_mode)

        self.btn_delete = QPushButton("🗑️ Excluir")
        self.btn_delete.setToolTip("Exclui o módulo selecionado da cena 3D (com Undo/Redo) (Atalho: Del)")
        self.btn_delete.setStyleSheet(
            "QPushButton { background-color: #dc2626; color: white; font-weight: bold; padding: 5px 8px; border-radius: 4px; font-size: 11px; }"
            "QPushButton:disabled { background-color: #64748b; color: #cbd5e1; }"
        )
        self.btn_delete.clicked.connect(self._delete_selected_module)
        h_dup_del.addWidget(self.btn_delete)
        v_props.addLayout(h_dup_del)

        # Atalhos de Teclado no Diálogo
        QShortcut(QKeySequence("Ctrl+D"), self, self._duplicate_selected_module)
        QShortcut(QKeySequence(Qt.Key_Delete), self, self._delete_selected_module)

        # Botões e Controle de Abertura Dinâmica 3D
        h_interact_box = QVBoxLayout()
        h_interact_box.setSpacing(4)

        h_interact_btns = QHBoxLayout()
        h_interact_btns.setSpacing(4)
        self.btn_toggle_interact = QPushButton("🚪 Abrir/Fechar")
        self.btn_toggle_interact.setStyleSheet("font-weight: 500; padding: 5px 8px; font-size: 11px;")
        self.btn_toggle_interact.setToolTip("Abre ou fecha todas as portas e gavetas do móvel selecionado")
        self.btn_toggle_interact.clicked.connect(self._toggle_doors_and_drawers)
        h_interact_btns.addWidget(self.btn_toggle_interact)

        self.btn_interact_tool = QPushButton("👆 Interagir (3D)")
        self.btn_interact_tool.setStyleSheet("font-weight: 500; padding: 5px 8px; font-size: 11px;")
        self.btn_interact_tool.setToolTip("Ativa a ferramenta de clique para abrir/fechar livremente no 3D")
        self.btn_interact_tool.clicked.connect(self._activate_interact_tool)
        h_interact_btns.addWidget(self.btn_interact_tool)

        self.btn_test_col = QPushButton("⚠️ Testar Colisão")
        self.btn_test_col.setStyleSheet("background-color: #f59e0b; color: white; font-weight: bold; padding: 5px 8px; font-size: 11px; border-radius: 4px;")
        self.btn_test_col.setToolTip("Testa se as portas/gavetas batem em puxadores, cantos ou outros armários")
        self.btn_test_col.clicked.connect(self._test_module_collisions)
        h_interact_btns.addWidget(self.btn_test_col)
        h_interact_box.addLayout(h_interact_btns)

        # Slider de abertura contínua no diálogo
        h_dlg_slider = QHBoxLayout()
        h_dlg_slider.setSpacing(6)
        lbl_sl_icon = QLabel("Abertura:")
        lbl_sl_icon.setStyleSheet("font-size: 11px; font-weight: bold;")
        h_dlg_slider.addWidget(lbl_sl_icon)

        self.sl_dlg_open = QSlider(Qt.Horizontal)
        self.sl_dlg_open.setRange(0, 100)
        self.sl_dlg_open.setValue(0)
        self.sl_dlg_open.valueChanged.connect(self._on_dialog_open_slider_changed)
        h_dlg_slider.addWidget(self.sl_dlg_open, 1)

        self.lbl_dlg_open_val = QLabel("0%")
        self.lbl_dlg_open_val.setStyleSheet("font-size: 10px; font-weight: bold; min-width: 30px;")
        h_dlg_slider.addWidget(self.lbl_dlg_open_val)
        h_interact_box.addLayout(h_dlg_slider)

        v_props.addLayout(h_interact_box)
