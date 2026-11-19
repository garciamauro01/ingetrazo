# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Montagem da aba Ajustes Especiais da barra lateral."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ..domain.materials_catalog import MDF_MATERIALS
from ..domain.snap_contract import SNAP_PAREDE_OPCOES
from ..domain.ui_contract import (
    DEFAULT_FOLGA_FRENTES_MM,
    FOLGA_FRENTES_MAX_MM,
    FOLGA_FRENTES_MIN_MM,
)


class SidebarAjustesMixin:
    """Cria as secoes especiais de ajustes adicionais na aba Avancado."""

    def _build_ajustes_section(self) -> None:
        """Monta as secoes especiais de ajustes."""
        # Combina os widgets de travessas das abas Estrutura e Materiais para controle de visibilidade unificado
        self._travessa_sidebar_widgets = (
            list(getattr(self, "_travessa_estrutura_widgets", []))
            + list(getattr(self, "_travessa_materiais_widgets", []))
        )

        # ── Configurações de Geladeira (caixa_geladeira) na Barra Lateral ─────
        self.lbl_geladeira_section = QLabel("<b>❄️ Nicho de Geladeira & Maleiro:</b>")
        self.sec_ajustes.form_layout.addRow(self.lbl_geladeira_section)

        self.sp_geladeira_alt_nicho = QSpinBox()
        self.sp_geladeira_alt_nicho.setRange(1200, 2400)
        self.sp_geladeira_alt_nicho.setValue(1800)
        self.sp_geladeira_alt_nicho.setSuffix(" mm")
        self.lbl_geladeira_alt_nicho = QLabel("Altura Vão Geladeira:")
        self.sec_ajustes.form_layout.addRow(self.lbl_geladeira_alt_nicho, self.sp_geladeira_alt_nicho)

        self.cb_geladeira_tipo_porta = QComboBox()
        self.cb_geladeira_tipo_porta.addItems([
            "2 Portas de Abrir",
            "1 Porta Basculante",
        ])
        self.lbl_geladeira_tipo_porta = QLabel("Portas do Maleiro:")
        self.sec_ajustes.form_layout.addRow(self.lbl_geladeira_tipo_porta, self.cb_geladeira_tipo_porta)

        self._geladeira_sidebar_widgets = [
            self.lbl_geladeira_section,
            self.lbl_geladeira_alt_nicho, self.sp_geladeira_alt_nicho,
            self.lbl_geladeira_tipo_porta, self.cb_geladeira_tipo_porta,
        ]
        for w in self._geladeira_sidebar_widgets:
            w.setVisible(False)

        # ── Configurações de Aéreo Micro-ondas na Barra Lateral ──────────────────
        self.lbl_micro_section = QLabel("<b>🚪 Portas do Micro-ondas:</b>")
        self.sec_ajustes.form_layout.addRow(self.lbl_micro_section)

        self.cb_micro_tipo_porta = QComboBox()
        self.cb_micro_tipo_porta.addItems([
            "1 Porta Basculante",
            "2 Portas de Abrir",
        ])
        self.lbl_micro_tipo_porta = QLabel("Tipo de Porta:")
        self.sec_ajustes.form_layout.addRow(self.lbl_micro_tipo_porta, self.cb_micro_tipo_porta)

        self._micro_sidebar_widgets = [
            self.lbl_micro_section,
            self.lbl_micro_tipo_porta, self.cb_micro_tipo_porta,
        ]
        for w in self._micro_sidebar_widgets:
            w.setVisible(False)

        # ── Configurações de Caixa de Gaveta na Barra Lateral ──────────────────
        self.lbl_gaveta_section = QLabel("<b>⚙️ Caixa de Gaveta:</b>")
        self.sec_ajustes.form_layout.addRow(self.lbl_gaveta_section)

        self.cb_tipo_fundo_gaveta = QComboBox()
        self.cb_tipo_fundo_gaveta.addItems([
            "Canal / Rasgo Lateral",
            "Por Baixo (Sobreposto)",
        ])
        self.lbl_tipo_fundo_gaveta = QLabel("Montagem Fundo:")
        self.sec_ajustes.form_layout.addRow(self.lbl_tipo_fundo_gaveta, self.cb_tipo_fundo_gaveta)

        self.sp_folga_corredica = QSpinBox()
        self.sp_folga_corredica.setRange(10, 50)
        self.sp_folga_corredica.setValue(26)
        self.sp_folga_corredica.setSuffix(" mm")
        self.sp_folga_corredica.setToolTip("Folga total a descontar da largura para corrediças (ex.: 26mm)")
        self.lbl_folga_corredica = QLabel("Folga Corrediças:")
        self.sec_ajustes.form_layout.addRow(self.lbl_folga_corredica, self.sp_folga_corredica)

        self.cb_material_gaveta = QComboBox()
        self.cb_material_gaveta.addItems(["(Mesmo da Caixa)"] + MDF_MATERIALS)
        self.lbl_material_gaveta = QLabel("Material Gaveta:")
        self.sec_ajustes.form_layout.addRow(self.lbl_material_gaveta, self.cb_material_gaveta)

        self.cb_espessura_gaveta = QComboBox()
        self.cb_espessura_gaveta.addItems([
            "15 mm",
            "18 mm",
        ])
        self.lbl_espessura_gaveta = QLabel("Espessura Gaveta:")
        self.sec_ajustes.form_layout.addRow(self.lbl_espessura_gaveta, self.cb_espessura_gaveta)

        self.cb_material_fita_gaveta = QComboBox()
        self.cb_material_fita_gaveta.addItems(["(Mesmo da Gaveta)"] + MDF_MATERIALS)
        self.lbl_material_fita_gaveta = QLabel("Fita Borda Gav.:")
        self.sec_ajustes.form_layout.addRow(self.lbl_material_fita_gaveta, self.cb_material_fita_gaveta)

        self.cb_material_fundo_gaveta = QComboBox()
        self.cb_material_fundo_gaveta.addItems(["(Padrão Fundo)"] + MDF_MATERIALS)
        self.lbl_material_fundo_gaveta = QLabel("Material Fundo Gav.:")
        self.sec_ajustes.form_layout.addRow(self.lbl_material_fundo_gaveta, self.cb_material_fundo_gaveta)

        self.cb_esp_fundo_gaveta = QComboBox()
        self.cb_esp_fundo_gaveta.addItems([
            "6 mm",
            "3 mm",
            "15 mm",
        ])
        self.lbl_esp_fundo_gaveta = QLabel("Esp. Fundo Gav.:")
        self.sec_ajustes.form_layout.addRow(self.lbl_esp_fundo_gaveta, self.cb_esp_fundo_gaveta)

        self._gaveta_sidebar_widgets = [
            self.lbl_gaveta_section,
            self.lbl_tipo_fundo_gaveta, self.cb_tipo_fundo_gaveta,
            self.lbl_folga_corredica, self.sp_folga_corredica,
            self.lbl_material_gaveta, self.cb_material_gaveta,
            self.lbl_espessura_gaveta, self.cb_espessura_gaveta,
            self.lbl_material_fita_gaveta, self.cb_material_fita_gaveta,
            self.lbl_material_fundo_gaveta, self.cb_material_fundo_gaveta,
            self.lbl_esp_fundo_gaveta, self.cb_esp_fundo_gaveta,
        ]

        # ── Configurações de Marmoraria / Bancadas de Pedra ────────────────────
        self.lbl_pedra_section = QLabel("<b>🪨 Marmoraria & Bancada:</b>")
        self.sec_ajustes.form_layout.addRow(self.lbl_pedra_section)

        self.sp_esp_pedra = QSpinBox()
        self.sp_esp_pedra.setRange(10, 60)
        self.sp_esp_pedra.setValue(20)
        self.sp_esp_pedra.setSuffix(" mm")
        self.sp_esp_pedra.setToolTip("Espessura da chapa de pedra (padrão: 20mm)")
        self.lbl_esp_pedra = QLabel("Espessura Pedra:")
        self.sec_ajustes.form_layout.addRow(self.lbl_esp_pedra, self.sp_esp_pedra)

        self.sp_altura_saia = QSpinBox()
        self.sp_altura_saia.setRange(20, 200)
        self.sp_altura_saia.setValue(40)
        self.sp_altura_saia.setSuffix(" mm")
        self.sp_altura_saia.setToolTip("Altura da saia/testeira engrossada frontal (padrão: 40mm ou 60mm)")
        self.lbl_altura_saia = QLabel("Altura Saia / Testeira:")
        self.sec_ajustes.form_layout.addRow(self.lbl_altura_saia, self.sp_altura_saia)

        self.sp_altura_frontao = QSpinBox()
        self.sp_altura_frontao.setRange(0, 300)
        self.sp_altura_frontao.setValue(100)
        self.sp_altura_frontao.setSuffix(" mm")
        self.sp_altura_frontao.setToolTip("Altura do rodabanca/frontão na parede (padrão: 100mm)")
        self.lbl_altura_frontao = QLabel("Rodabanca / Frontão:")
        self.sec_ajustes.form_layout.addRow(self.lbl_altura_frontao, self.sp_altura_frontao)

        self.chk_tem_saia_esq = QCheckBox("Saia Lateral Esquerda")
        self.chk_tem_saia_esq.setChecked(True)
        self.lbl_tem_saia_esq = QLabel("Saia Esquerda:")
        self.sec_ajustes.form_layout.addRow(self.lbl_tem_saia_esq, self.chk_tem_saia_esq)

        self.chk_tem_saia_dir = QCheckBox("Saia Lateral Direita")
        self.chk_tem_saia_dir.setChecked(True)
        self.lbl_tem_saia_dir = QLabel("Saia Direita:")
        self.sec_ajustes.form_layout.addRow(self.lbl_tem_saia_dir, self.chk_tem_saia_dir)

        self.cb_tipo_cuba = QComboBox()
        self.cb_tipo_cuba.addItems([
            "Cuba Inox Simples",
            "Cuba Inox Dupla",
            "Cuba Esculpida na Pedra",
            "Sem Cuba (Tampo Cego)",
        ])
        self.lbl_tipo_cuba = QLabel("Modelo Cuba:")
        self.sec_ajustes.form_layout.addRow(self.lbl_tipo_cuba, self.cb_tipo_cuba)

        self.cb_posicao_cuba = QComboBox()
        self.cb_posicao_cuba.addItems([
            "🎯 Centralizada",
            "⬅️ À Esquerda",
            "➡️ À Direita",
        ])
        self.lbl_posicao_cuba = QLabel("Posição Cuba:")
        self.sec_ajustes.form_layout.addRow(self.lbl_posicao_cuba, self.cb_posicao_cuba)

        self.chk_tem_torneira = QCheckBox("Incluir Torneira Gourmet")
        self.chk_tem_torneira.setChecked(True)
        self.lbl_tem_torneira = QLabel("Torneira:")
        self.sec_ajustes.form_layout.addRow(self.lbl_tem_torneira, self.chk_tem_torneira)

        self.cb_canto_recorte = QComboBox()
        self.cb_canto_recorte.addItems(["Cantos Arredondados (R20)", "Cantos Retos 90°"])
        self.lbl_canto_recorte = QLabel("Recorte Cuba:")
        self.sec_ajustes.form_layout.addRow(self.lbl_canto_recorte, self.cb_canto_recorte)

        self.chk_tem_area_molhada = QCheckBox("Área Molhada Rebaixada")
        self.chk_tem_area_molhada.setChecked(True)
        self.lbl_tem_area_molhada = QLabel("Área Molhada:")
        self.sec_ajustes.form_layout.addRow(self.lbl_tem_area_molhada, self.chk_tem_area_molhada)

        self._pedra_sidebar_widgets = [
            self.lbl_pedra_section,
            self.lbl_esp_pedra, self.sp_esp_pedra,
            self.lbl_altura_saia, self.sp_altura_saia,
            self.lbl_altura_frontao, self.sp_altura_frontao,
            self.lbl_tem_saia_esq, self.chk_tem_saia_esq,
            self.lbl_tem_saia_dir, self.chk_tem_saia_dir,
            self.lbl_tipo_cuba, self.cb_tipo_cuba,
            self.lbl_posicao_cuba, self.cb_posicao_cuba,
            self.lbl_tem_torneira, self.chk_tem_torneira,
            self.lbl_canto_recorte, self.cb_canto_recorte,
            self.lbl_tem_area_molhada, self.chk_tem_area_molhada,
        ]
        for w in self._pedra_sidebar_widgets:
            w.setVisible(False)

        # ── Configurações de Tampo Engrossado (peca_tampo_engrossado) ─────────
        self.lbl_tampo_section = QLabel("<b>🪵 Configurações do Tampo:</b>")
        self.sec_ajustes.form_layout.addRow(self.lbl_tampo_section)

        self.cb_tampo_esp_chapa = QComboBox()
        self.cb_tampo_esp_chapa.addItems(["18 mm", "15 mm", "25 mm"])
        self.lbl_tampo_esp_chapa = QLabel("Espessura Chapa:")
        self.sec_ajustes.form_layout.addRow(self.lbl_tampo_esp_chapa, self.cb_tampo_esp_chapa)

        self.sp_tampo_qtd_engrosso = QSpinBox()
        self.sp_tampo_qtd_engrosso.setRange(1, 6)
        self.sp_tampo_qtd_engrosso.setValue(1)
        self.sp_tampo_qtd_engrosso.setSuffix(" camada(s)")
        self.sp_tampo_qtd_engrosso.setToolTip("Quantidade de réguas/camadas empilhadas no engrosso inferior (1 camada = chapa dupla, 2 camadas = chapa tripla, etc.)")
        self.lbl_tampo_qtd_engrosso = QLabel("Fatias Engrosso:")
        self.sec_ajustes.form_layout.addRow(self.lbl_tampo_qtd_engrosso, self.sp_tampo_qtd_engrosso)

        self.sp_tampo_larg_engrosso = QSpinBox()
        self.sp_tampo_larg_engrosso.setRange(30, 200)
        self.sp_tampo_larg_engrosso.setValue(70)
        self.sp_tampo_larg_engrosso.setSuffix(" mm")
        self.sp_tampo_larg_engrosso.setToolTip("Largura das réguas perimetrais inferiores de engrosso (padrão: 70mm)")
        self.lbl_tampo_larg_engrosso = QLabel("Largura Réguas:")
        self.sec_ajustes.form_layout.addRow(self.lbl_tampo_larg_engrosso, self.sp_tampo_larg_engrosso)

        self.cb_tampo_tipo_engrosso = QComboBox()
        self.cb_tampo_tipo_engrosso.addItems([
            "Frontal e Laterais (3 Lados)",
            "Perímetro Completo (4 Lados / Ilha)",
            "Apenas Frontal (1 Lado)",
        ])
        self.lbl_tampo_tipo_engrosso = QLabel("Lados Engrosso:")
        self.sec_ajustes.form_layout.addRow(self.lbl_tampo_tipo_engrosso, self.cb_tampo_tipo_engrosso)

        self.chk_tampo_fechar_embaixo = QCheckBox("Fechar com chapa inferior")
        self.chk_tampo_fechar_embaixo.setChecked(False)
        self.chk_tampo_fechar_embaixo.setToolTip("Adiciona uma chapa inteiriça inferior de acabamento por baixo das réguas (tampo tipo sanduíche/tamburato)")
        self.lbl_tampo_fechar_embaixo = QLabel("Fundo do Tampo:")
        self.sec_ajustes.form_layout.addRow(self.lbl_tampo_fechar_embaixo, self.chk_tampo_fechar_embaixo)

        self.cb_tampo_snap_parede = QComboBox()
        self.cb_tampo_snap_parede.addItems([label for _valor, label in SNAP_PAREDE_OPCOES])
        self.cb_tampo_snap_parede.setToolTip(
            "Face do tampo que adere à parede ao arrastar. As faces superior e "
            "inferior tombam a peça 90° para ficarem planas contra a parede. "
            "Escolha 'Sem snap' para manter a peça totalmente livre."
        )
        self.lbl_tampo_snap_parede = QLabel("Face de Encaixe:")
        self.sec_ajustes.form_layout.addRow(self.lbl_tampo_snap_parede, self.cb_tampo_snap_parede)

        # Atualiza a altura total aparente no sp_altura ao mudar espessura, camadas ou fechamento
        def _recalc_tampo_height():
            if getattr(self, "_current_selected_tipo", "") in ("peca_tampo_engrossado", "tampo_engrossado"):
                try:
                    e_ch = float(self.cb_tampo_esp_chapa.currentText().split()[0])
                except Exception:
                    e_ch = 18.0
                n_cam = self.sp_tampo_qtd_engrosso.value()
                tem_fech = self.chk_tampo_fechar_embaixo.isChecked()
                total_h = e_ch * (1 + n_cam + (1 if tem_fech else 0))
                self.sp_altura.setValue(int(round(total_h)))

        self.cb_tampo_esp_chapa.currentIndexChanged.connect(_recalc_tampo_height)
        self.sp_tampo_qtd_engrosso.valueChanged.connect(_recalc_tampo_height)
        self.chk_tampo_fechar_embaixo.toggled.connect(_recalc_tampo_height)

        self._tampo_sidebar_widgets = [
            self.lbl_tampo_section,
            self.lbl_tampo_esp_chapa, self.cb_tampo_esp_chapa,
            self.lbl_tampo_qtd_engrosso, self.sp_tampo_qtd_engrosso,
            self.lbl_tampo_larg_engrosso, self.sp_tampo_larg_engrosso,
            self.lbl_tampo_tipo_engrosso, self.cb_tampo_tipo_engrosso,
            self.lbl_tampo_fechar_embaixo, self.chk_tampo_fechar_embaixo,
            self.lbl_tampo_snap_parede, self.cb_tampo_snap_parede,
        ]
        for w in self._tampo_sidebar_widgets:
            w.setVisible(False)

        self.chk_gerar_furacao = QCheckBox("Gerar furações e usinagens")
        self.chk_gerar_furacao.setChecked(True)
        self.chk_gerar_furacao.setToolTip("Gera furações de dobradiças, corrediças e canais para este módulo")
        self.lbl_furacao = QLabel("Furação:")
        self.sec_ajustes.form_layout.addRow(self.lbl_furacao, self.chk_gerar_furacao)

        self.cb_dispositivo_fixacao = QComboBox()
        self.cb_dispositivo_fixacao.addItems([
            "Minifix + Cavilha",
            "Cavilha + Parafuso",
            "Apenas Parafuso",
            "Apenas Cavilhas",
        ])
        self.cb_dispositivo_fixacao.setToolTip("Dispositivo de junção da caixa (Minifix / Cavilha / Parafuso)")
        self.lbl_dispositivo_fixacao = QLabel("Fixação Caixa:")
        self.sec_ajustes.form_layout.addRow(self.lbl_dispositivo_fixacao, self.cb_dispositivo_fixacao)

        self.cb_dispositivo_prateleira = QComboBox()
        self.cb_dispositivo_prateleira.addItems([
            "Cavilhas de Topo (Ø8mm)",
            "Conector Häfele VB 35 (Ø20mm)",
            "Conector Häfele VB 36 com Aba (Ø20mm)",
        ])
        self.cb_dispositivo_prateleira.setToolTip("Dispositivo de fixação de prateleiras internas (Cavilha / VB 35 / VB 36)")
        self.lbl_dispositivo_prateleira = QLabel("Fixação Prateleira:")
        self.sec_ajustes.form_layout.addRow(self.lbl_dispositivo_prateleira, self.cb_dispositivo_prateleira)

        self.sp_folga_frentes = QSpinBox()
        self.sp_folga_frentes.setRange(FOLGA_FRENTES_MIN_MM, FOLGA_FRENTES_MAX_MM)
        self.sp_folga_frentes.setValue(int(DEFAULT_FOLGA_FRENTES_MM))
        self.sp_folga_frentes.setSuffix(" mm")
        self.sp_folga_frentes.setToolTip(
            "Folga perimetral e entre portas/gavetas nas frentes do módulo (padrão: 3 mm)"
        )
        self.lbl_folga_frentes = QLabel("Folga das Frentes:")
        self.sec_ajustes.form_layout.addRow(self.lbl_folga_frentes, self.sp_folga_frentes)

        def _on_dispositivo_ajustes_changed(*_args):
            if not getattr(self, "_updating_ui", False):
                self._apply_changes_to_selected()

        self.chk_gerar_furacao.toggled.connect(_on_dispositivo_ajustes_changed)
        self.cb_dispositivo_fixacao.currentIndexChanged.connect(_on_dispositivo_ajustes_changed)
        self.cb_dispositivo_prateleira.currentIndexChanged.connect(_on_dispositivo_ajustes_changed)

        # ── Configurações de Cavilha em Divisória Vertical (peca_divisoria_vertical) ──
        self.lbl_divisoria_section = QLabel("<b>🔩 Cavilhas da Divisória:</b>")
        self.sec_ajustes.form_layout.addRow(self.lbl_divisoria_section)

        self.cb_cavilhas_divisoria = QComboBox()
        self.cb_cavilhas_divisoria.addItems([
            "Em Cima e Embaixo (Ambos)",
            "Apenas Em Cima (Topo Superior)",
            "Apenas Embaixo (Base Inferior)",
            "Sem Furação (Nenhum)",
        ])
        self.cb_cavilhas_divisoria.setToolTip("Configura a presença de furos para cavilhas no topo superior e/ou base inferior da divisória")
        self.lbl_cavilhas_divisoria = QLabel("Posição Cavilhas:")
        self.sec_ajustes.form_layout.addRow(self.lbl_cavilhas_divisoria, self.cb_cavilhas_divisoria)
        self.cb_cavilhas_divisoria.currentIndexChanged.connect(_on_dispositivo_ajustes_changed)

        self._divisoria_sidebar_widgets = [
            self.lbl_divisoria_section,
            self.lbl_cavilhas_divisoria,
            self.cb_cavilhas_divisoria,
        ]
        for w in self._divisoria_sidebar_widgets:
            w.setVisible(False)

        # ── Configurações de Prateleiras Avulsas (peca_prateleiras_avulsas) ──
        self.lbl_prat_avulsas_section = QLabel("<b>📚 Prateleiras Avulsas:</b>")
        self.sec_ajustes.form_layout.addRow(self.lbl_prat_avulsas_section)

        self.chk_prat_has_primeira = QCheckBox("Criar primeira prateleira (Base)")
        self.chk_prat_has_primeira.setChecked(False)
        self.chk_prat_has_primeira.setToolTip("Gera uma prateleira exatamente na base inferior do vão delimitado")
        self.lbl_prat_has_primeira = QLabel("Primeira Prateleira:")
        self.sec_ajustes.form_layout.addRow(self.lbl_prat_has_primeira, self.chk_prat_has_primeira)

        self.chk_prat_has_ultima = QCheckBox("Criar última prateleira (Topo)")
        self.chk_prat_has_ultima.setChecked(False)
        self.chk_prat_has_ultima.setToolTip("Gera uma prateleira exatamente no topo superior do vão delimitado")
        self.lbl_prat_has_ultima = QLabel("Última Prateleira:")
        self.sec_ajustes.form_layout.addRow(self.lbl_prat_has_ultima, self.chk_prat_has_ultima)

        self.chk_prat_has_primeira.toggled.connect(_on_dispositivo_ajustes_changed)
        self.chk_prat_has_ultima.toggled.connect(_on_dispositivo_ajustes_changed)

        self._prat_avulsas_sidebar_widgets = [
            self.lbl_prat_avulsas_section,
            self.lbl_prat_has_primeira, self.chk_prat_has_primeira,
            self.lbl_prat_has_ultima, self.chk_prat_has_ultima,
        ]
        for w in self._prat_avulsas_sidebar_widgets:
            w.setVisible(False)



# Aliases
SidebarAdjustmentsMixin = SidebarAjustesMixin

