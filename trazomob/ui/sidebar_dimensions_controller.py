# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Montagem da aba Medidas da barra lateral."""
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

from ..domain.catalog import MODULE_CATALOG
from ..domain.i18n import tr
from ..domain.schema import module_params
from ..domain.ui_contract import ELEVACAO_MAX_MM, ELEVACAO_MIN_MM


class SidebarMedidasMixin:
    """Cria a aba Medidas com medidas principais e troca de tipo."""

    def _build_trocar_tipo_section(self) -> None:
        """Monta o seletor de troca rapida de modulo."""
        # --- Troca Rápida de Módulo (Substituição Dinâmica / Swap) ---
        h_trocar_tipo = QHBoxLayout()
        self.cb_trocar_tipo = QComboBox()
        self.cb_trocar_tipo.setToolTip(tr("Substitui o tipo do módulo selecionado mantendo posição 3D, medidas, rotação na parede e materiais."))
        for cat_name, cat_items in MODULE_CATALOG.items():
            self.cb_trocar_tipo.addItem(f"\u2500\u2500 {tr(cat_name)} \u2500\u2500", None)
            model = self.cb_trocar_tipo.model()
            last_row = self.cb_trocar_tipo.count() - 1
            if hasattr(model, "item"):
                item_obj = model.item(last_row)
                if item_obj:
                    item_obj.setEnabled(False)
            for m_item in cat_items:
                self.cb_trocar_tipo.addItem(f"  {tr(m_item.get('nome', m_item['id']))}", m_item["id"])
        self.cb_trocar_tipo.currentIndexChanged.connect(self._on_trocar_tipo_changed)
        h_trocar_tipo.addWidget(self.cb_trocar_tipo)
        self.lbl_trocar_tipo = QLabel(tr("Tipo Módulo:"))
        self.sec_dimensoes.form_layout.addRow(self.lbl_trocar_tipo, h_trocar_tipo)



    def _build_medidas_section(self) -> None:
        """Monta as medidas principais."""
        # --- Medidas Principais ---

        from ..domain.materials_catalog import CHAPA_MAX_COMPRIMENTO_UTIL_MM

        # Largura (limitada à dimensão útil máxima da chapa de 2750mm com refilo de limpeza: 2720mm)
        h_larg = QHBoxLayout()
        self.sp_largura = QSpinBox()
        self.sp_largura.setRange(1, int(CHAPA_MAX_COMPRIMENTO_UTIL_MM))
        self.sp_largura.setValue(800)
        self.sp_largura.setSuffix(" mm")
        h_larg.addWidget(self.sp_largura)
        btn_l_minus = QPushButton("-50")
        btn_l_minus.setMaximumWidth(36)
        btn_l_minus.clicked.connect(lambda: self.sp_largura.setValue(self.sp_largura.value() - 50))
        h_larg.addWidget(btn_l_minus)
        btn_l_plus = QPushButton("+50")
        btn_l_plus.setMaximumWidth(36)
        btn_l_plus.clicked.connect(lambda: self.sp_largura.setValue(self.sp_largura.value() + 50))
        h_larg.addWidget(btn_l_plus)
        self.lbl_largura = QLabel(tr("Largura:"))
        self.sec_dimensoes.form_layout.addRow(self.lbl_largura, h_larg)

        # Altura (limitada à dimensão útil máxima da chapa: 2720mm)
        h_alt = QHBoxLayout()
        self.sp_altura = QSpinBox()
        self.sp_altura.setRange(1, int(CHAPA_MAX_COMPRIMENTO_UTIL_MM))
        self.sp_altura.setValue(720)
        self.sp_altura.setSuffix(" mm")
        h_alt.addWidget(self.sp_altura)
        btn_a_minus = QPushButton("-50")
        btn_a_minus.setMaximumWidth(36)
        btn_a_minus.clicked.connect(lambda: self.sp_altura.setValue(self.sp_altura.value() - 50))
        h_alt.addWidget(btn_a_minus)
        btn_a_plus = QPushButton("+50")
        btn_a_plus.setMaximumWidth(36)
        btn_a_plus.clicked.connect(lambda: self.sp_altura.setValue(self.sp_altura.value() + 50))
        h_alt.addWidget(btn_a_plus)
        self.lbl_altura = QLabel(tr("Altura:"))
        self.sec_dimensoes.form_layout.addRow(self.lbl_altura, h_alt)

        # Profundidade (também permite dimensões de cama até CHAPA_MAX_COMPRIMENTO_UTIL_MM)
        h_prof = QHBoxLayout()
        self.sp_prof = QSpinBox()
        self.sp_prof.setRange(1, int(CHAPA_MAX_COMPRIMENTO_UTIL_MM))
        self.sp_prof.setValue(550)

        self.sp_prof.setSuffix(" mm")
        h_prof.addWidget(self.sp_prof)
        btn_p_minus = QPushButton("-50")
        btn_p_minus.setMaximumWidth(36)
        btn_p_minus.clicked.connect(lambda: self.sp_prof.setValue(self.sp_prof.value() - 50))
        h_prof.addWidget(btn_p_minus)
        btn_p_plus = QPushButton("+50")
        btn_p_plus.setMaximumWidth(36)
        btn_p_plus.clicked.connect(lambda: self.sp_prof.setValue(self.sp_prof.value() + 50))
        h_prof.addWidget(btn_p_plus)
        self.lbl_prof = QLabel(tr("Profundidade:"))
        self.sec_dimensoes.form_layout.addRow(self.lbl_prof, h_prof)

        # Elevação do Piso (Z inferior em mm)
        h_elev = QHBoxLayout()
        self.sp_elevacao = QSpinBox()
        self.sp_elevacao.setRange(ELEVACAO_MIN_MM, ELEVACAO_MAX_MM)
        self.sp_elevacao.setValue(0)
        self.sp_elevacao.setSingleStep(10)
        self.sp_elevacao.setSuffix(" mm")
        self.sp_elevacao.setToolTip(
            tr("Altura do módulo em relação ao piso (cota inferior Z em milímetros)")
        )
        h_elev.addWidget(self.sp_elevacao)
        btn_e_minus = QPushButton("-50")
        btn_e_minus.setMaximumWidth(36)
        btn_e_minus.clicked.connect(lambda: self.sp_elevacao.setValue(self.sp_elevacao.value() - 50))
        h_elev.addWidget(btn_e_minus)
        btn_e_plus = QPushButton("+50")
        btn_e_plus.setMaximumWidth(36)
        btn_e_plus.clicked.connect(lambda: self.sp_elevacao.setValue(self.sp_elevacao.value() + 50))
        h_elev.addWidget(btn_e_plus)
        self.lbl_elevacao = QLabel(tr("Elevação do Piso:"))
        self.sec_dimensoes.form_layout.addRow(self.lbl_elevacao, h_elev)

        # Afastamento Parede (recuo/deslocamento para frente em relação à parede de encosto)
        h_afast = QHBoxLayout()
        self.sp_afastamento_parede = QSpinBox()
        self.sp_afastamento_parede.setRange(0, 1000)
        self.sp_afastamento_parede.setValue(0)
        self.sp_afastamento_parede.setSingleStep(10)
        self.sp_afastamento_parede.setSuffix(" mm")
        self.sp_afastamento_parede.setToolTip(
            tr("Afastamento do fundo do módulo em relação à parede (desloca o móvel para frente em mm)")
        )
        h_afast.addWidget(self.sp_afastamento_parede)
        btn_af_minus = QPushButton("-50")
        btn_af_minus.setMaximumWidth(36)
        btn_af_minus.clicked.connect(lambda: self.sp_afastamento_parede.setValue(max(0, self.sp_afastamento_parede.value() - 50)))
        h_afast.addWidget(btn_af_minus)
        btn_af_plus = QPushButton("+50")
        btn_af_plus.setMaximumWidth(36)
        btn_af_plus.clicked.connect(lambda: self.sp_afastamento_parede.setValue(self.sp_afastamento_parede.value() + 50))
        h_afast.addWidget(btn_af_plus)
        self.lbl_afastamento_parede = QLabel(tr("Afastamento Parede:"))
        self.sec_dimensoes.form_layout.addRow(self.lbl_afastamento_parede, h_afast)

        # Asas do módulo de canto em L (profundidade de cada ala)
        self.sp_larg_asa_esq = QSpinBox()
        self.sp_larg_asa_esq.setRange(300, 1200)
        self.sp_larg_asa_esq.setSingleStep(50)
        self.sp_larg_asa_esq.setValue(550)
        self.sp_larg_asa_esq.setSuffix(" mm")
        self.sp_larg_asa_esq.setToolTip(
            "Profundidade da asa esquerda (ala que corre no eixo X) do módulo de canto em L")
        self.lbl_larg_asa_esq = QLabel(tr("Asa Esquerda:"))
        self.sec_dimensoes.form_layout.addRow(
            self.lbl_larg_asa_esq, self.sp_larg_asa_esq)
        self.lbl_larg_asa_esq.setVisible(False)
        self.sp_larg_asa_esq.setVisible(False)

        self.sp_larg_asa_dir = QSpinBox()
        self.sp_larg_asa_dir.setRange(300, 1200)
        self.sp_larg_asa_dir.setSingleStep(50)
        self.sp_larg_asa_dir.setValue(550)
        self.sp_larg_asa_dir.setSuffix(" mm")
        self.sp_larg_asa_dir.setToolTip(
            "Profundidade da asa direita (ala que corre no eixo Y) do módulo de canto em L")
        self.lbl_larg_asa_dir = QLabel(tr("Asa Direita:"))
        self.sec_dimensoes.form_layout.addRow(
            self.lbl_larg_asa_dir, self.sp_larg_asa_dir)
        self.lbl_larg_asa_dir.setVisible(False)
        self.sp_larg_asa_dir.setVisible(False)

        # Batente de quina interna do canto L (opcional)
        self.chk_batente_canto = QCheckBox(tr("Batente de quina interna"))
        self.chk_batente_canto.setToolTip(
            "Fecha o vão interno de 90° com um montante da mesma espessura/material "
            "das portas. Desmarque para manter o cruzamento atual das portas.")
        self.lbl_batente_canto = QLabel(tr("Quina Interna:"))
        self.sec_dimensoes.form_layout.addRow(
            self.lbl_batente_canto, self.chk_batente_canto)
        self.lbl_batente_canto.setVisible(False)
        self.chk_batente_canto.setVisible(False)

        # Régua de Fechamento de Canto (50 mm perpendicular a partir da tampa cega)
        self.sp_largura_cego_canto = QSpinBox()
        self.sp_largura_cego_canto.setRange(100, 1500)
        self.sp_largura_cego_canto.setValue(500)
        self.sp_largura_cego_canto.setSuffix(" mm")
        self.sp_largura_cego_canto.setSingleStep(10)
        self.sp_largura_cego_canto.setToolTip("Largura da tampa cega frontal (profundidade de encaixe do módulo perpendicular)")
        self.lbl_largura_cego_canto = QLabel(tr("Largura Fechamento Cego:"))
        self.sec_dimensoes.form_layout.addRow(self.lbl_largura_cego_canto, self.sp_largura_cego_canto)
        self.lbl_largura_cego_canto.setVisible(False)
        self.sp_largura_cego_canto.setVisible(False)

        h_regua_canto = QHBoxLayout()
        self.chk_regua_fechamento_canto = QCheckBox(tr("Adicionar Régua 90°"))
        self.chk_regua_fechamento_canto.setToolTip("Cria uma régua de acabamento perpendicular (90°) projetada para frente a partir da tampa cega onde o outro balcão encosta")
        h_regua_canto.addWidget(self.chk_regua_fechamento_canto)

        self.sp_larg_regua_canto = QSpinBox()
        self.sp_larg_regua_canto.setRange(20, 200)
        self.sp_larg_regua_canto.setValue(50)
        self.sp_larg_regua_canto.setSuffix(" mm")
        self.sp_larg_regua_canto.setToolTip("Largura da régua de fechamento perpendicular (padrão 50 mm)")
        h_regua_canto.addWidget(self.sp_larg_regua_canto)

        self.lbl_regua_fechamento_canto = QLabel(tr("Régua Fechamento:"))
        self.sec_dimensoes.form_layout.addRow(self.lbl_regua_fechamento_canto, h_regua_canto)
        self.lbl_regua_fechamento_canto.setVisible(False)
        self.chk_regua_fechamento_canto.setVisible(False)
        self.sp_larg_regua_canto.setVisible(False)

        self.sp_dist_regua_canto = QSpinBox()
        self.sp_dist_regua_canto.setRange(0, 1500)
        self.sp_dist_regua_canto.setValue(0)
        self.sp_dist_regua_canto.setSuffix(" mm")
        self.sp_dist_regua_canto.setSingleStep(5)
        self.sp_dist_regua_canto.setToolTip("Distância/afastamento da régua em relação à borda externa da tampa cega (0 mm = posicionamento na borda junto ao vão da porta)")
        self.lbl_dist_regua_canto = QLabel(tr("Distância da Régua:"))
        self.sec_dimensoes.form_layout.addRow(self.lbl_dist_regua_canto, self.sp_dist_regua_canto)
        self.lbl_dist_regua_canto.setVisible(False)
        self.sp_dist_regua_canto.setVisible(False)



    def _sync_nicho_prateleiras_from_qtd(self, val: int) -> None:
        if getattr(self, "_updating_ui", False):
            return
        if getattr(self, "_current_selected_tipo", "") in ("nicho", "peca_prateleiras_avulsas") and hasattr(self, "sp_prateleiras"):
            if self.sp_prateleiras.value() != val:
                self.sp_prateleiras.blockSignals(True)
                self.sp_prateleiras.setValue(int(val))
                self.sp_prateleiras.blockSignals(False)

    def _sync_nicho_qtd_from_prateleiras(self, val: int) -> None:
        if getattr(self, "_updating_ui", False):
            return
        if getattr(self, "_current_selected_tipo", "") in ("nicho", "peca_prateleiras_avulsas") and hasattr(self, "sp_qtd_elem"):
            if self.sp_qtd_elem.value() != val:
                self.sp_qtd_elem.blockSignals(True)
                self.sp_qtd_elem.setValue(int(val))
                self.sp_qtd_elem.blockSignals(False)

    def _on_portas_balcao_changed(self, num_portas: int) -> None:
        """Balcão com portas, Aéreo e Balcão Misto: cada porta acrescenta 400 mm à largura."""
        if getattr(self, "_updating_ui", False) or not getattr(self, "_portas_400mm", False):
            return
        tipo = getattr(self, "_current_selected_tipo", "balcao")
        if tipo == "balcao_misto":
            larg_gav = float(self.sp_largura_gaveteiro.value()) if hasattr(self, "sp_largura_gaveteiro") else 450.0
            n_p = max(1, min(3, int(num_portas)))
            # Gaveteiro + N portas de 400 mm
            self.sp_largura.setValue(int(round(larg_gav + (n_p * 400.0))))
            return

        from ..domain.module_geometry import auto_divisoes_for_doors, width_for_doors
        self.sp_largura.setValue(int(round(width_for_doors(num_portas))))
        self.sp_divisoes.setValue(auto_divisoes_for_doors(num_portas))


    def _populate_trocar_tipo_combo(self, allowed_cats: set[str] | None = None) -> None:
        """Reconstrói o combo 'Trocar Tipo' filtrando por categorias permitidas.

        Se ``allowed_cats`` for None, mostra todas as categorias (uso inicial).
        Sempre inclui a categoria do módulo corrente primeiro.
        """
        self.cb_trocar_tipo.blockSignals(True)
        try:
            self.cb_trocar_tipo.clear()
            # Garante que a categoria do módulo corrente esteja sempre disponível
            cur_cat_name = None
            for cat_name, cat_items in MODULE_CATALOG.items():
                ids = [m.get("id") for m in cat_items]
                # Encontrar se algum módulo deste catálogo já está selecionado
                if cur_cat_name is None:
                    # Não temos o tipo ainda; vamos deixar o combo aberto
                    pass
            # Se allowed_cats for None, adiciona tudo (modo inicial)
            if allowed_cats is None:
                for cat_name, cat_items in MODULE_CATALOG.items():
                    self.cb_trocar_tipo.addItem(f"\u2500\u2500 {tr(cat_name)} \u2500\u2500", None)
                    model = self.cb_trocar_tipo.model()
                    last_row = self.cb_trocar_tipo.count() - 1
                    if hasattr(model, "item"):
                        item_obj = model.item(last_row)
                        if item_obj:
                            item_obj.setEnabled(False)
                    for m_item in cat_items:
                        self.cb_trocar_tipo.addItem(f"  {tr(m_item.get('nome', m_item['id']))}", m_item["id"])
            else:
                # Modo filtrado: começa pela categoria do módulo corrente (se for compatível)
                added_current = False
                for cat_name, cat_items in MODULE_CATALOG.items():
                    if cat_name not in allowed_cats:
                        continue
                    # Se esta for a categoria do módulo corrente, marcar para adicionar primeiro
                    if not added_current:
                        self.cb_trocar_tipo.addItem(f"\u2500\u2500 {tr(cat_name)} \u2500\u2500", None)
                        model = self.cb_trocar_tipo.model()
                        last_row = self.cb_trocar_tipo.count() - 1
                        if hasattr(model, "item"):
                            item_obj = model.item(last_row)
                            if item_obj:
                                item_obj.setEnabled(False)
                        for m_item in cat_items:
                            self.cb_trocar_tipo.addItem(f"  {tr(m_item.get('nome', m_item['id']))}", m_item["id"])
                        added_current = True
                    else:
                        # Categorias compatíveis adicionais
                        self.cb_trocar_tipo.addItem(f"\u2500\u2500 {tr(cat_name)} \u2500\u2500", None)
                        model = self.cb_trocar_tipo.model()
                        last_row = self.cb_trocar_tipo.count() - 1
                        if hasattr(model, "item"):
                            item_obj = model.item(last_row)
                            if item_obj:
                                item_obj.setEnabled(False)
                        for m_item in cat_items:
                            self.cb_trocar_tipo.addItem(f"  {tr(m_item.get('nome', m_item['id']))}", m_item["id"])
        finally:
            self.cb_trocar_tipo.blockSignals(False)


    def _on_trocar_tipo_changed(self, index: int) -> None:
        """Substitui o tipo do módulo selecionado mantendo dimensões, posição 3D e rotação (Swap)."""
        if getattr(self, "_updating_ui", False):
            return
        new_tipo = self.cb_trocar_tipo.itemData(index)
        if not new_tipo:
            return
        mod = self._active_selected_module()
        if mod is None or not hasattr(mod, "ext") or "trazomob_module" not in mod.ext:
            return
        cur_tipo = module_params(mod).get("tipo")
        if cur_tipo == new_tipo:
            return
        self._apply_changes_to_selected(forced_tipo=new_tipo)


# Aliases
SidebarDimensionsMixin = SidebarMedidasMixin

