# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Mixin para gerenciamento da galeria visual de cartões de módulos TrazoMob (DialogGalleryMixin)."""
from __future__ import annotations

from typing import Any, Optional
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QListWidgetItem

from ..domain.catalog import MODULE_CATALOG, USER_MODULE_CATEGORY, modulos_usuario
from ..ui.thumbnails import get_module_thumbnail
from ..domain.param_mapper import populate_ui_from_module
from ..domain.ui_contract import should_show_config_gaveteiro


class DialogGalleryMixin:
    """Encapsula preenchimento da lista de módulos, busca, filtragem e atualização reativa do formulário."""

    def _populate_module_cards(self):
        """Preenche o grid visual de miniaturas com base na categoria e busca."""
        cat_filter = self.cb_category.currentText()
        search_filter = self.txt_search.text().strip().lower()

        if hasattr(self, "lbl_cat_title"):
            self.lbl_cat_title.setText(cat_filter if cat_filter != "📂 Todas as Categorias" else "Todas as Categorias")

        current_selected_id = None
        current_item = self.list_modules.currentItem()
        if current_item:
            cdata = current_item.data(Qt.UserRole)
            if cdata:
                current_selected_id = cdata.get("id")
        if current_selected_id is None and getattr(self, "_editing_module", None) is not None:
            from ..domain.schema import module_params
            current_selected_id = module_params(self._editing_module).get("tipo")

        self.list_modules.blockSignals(True)
        self.list_modules.clear()

        def _match(item: dict) -> bool:
            if not search_filter:
                return True
            return (search_filter in item.get("nome", "").lower()
                    or search_filter in item.get("desc", "").lower())

        matched_items = []

        # Módulos pessoais do usuário ("Meus Módulos") aparecem primeiro,
        # tanto na categoria dedicada quanto em "Todas as Categorias".
        if cat_filter in ("📂 Todas as Categorias", USER_MODULE_CATEGORY):
            for item in modulos_usuario():
                if _match(item):
                    matched_items.append(item)

        for cat_name, items in MODULE_CATALOG.items():
            if cat_filter != "📂 Todas as Categorias" and cat_filter != cat_name:
                continue
            for item in items:
                if not _match(item):
                    continue
                matched_items.append(item)

        select_item_target = None
        for item in matched_items:
            list_item = QListWidgetItem(item["nome"])
            list_item.setIcon(get_module_thumbnail(item["id"]))
            list_item.setData(Qt.UserRole, item)
            list_item.setSizeHint(QSize(110, 122))
            self.list_modules.addItem(list_item)
            if current_selected_id and item["id"] == current_selected_id:
                select_item_target = list_item

        self.list_modules.blockSignals(False)

        if select_item_target:
            self.list_modules.setCurrentItem(select_item_target)
            self._on_module_card_selected(select_item_target)
        elif self.list_modules.count() > 0:
            first_item = self.list_modules.item(0)
            self.list_modules.setCurrentItem(first_item)
            self._on_module_card_selected(first_item)

    def _on_tipo_fundo_changed(self):
        """Habilita ou desabilita campos dependendo se o fundo é rasgo, sobreposto ou ausente."""
        idx = self.cb_tipo_fundo.currentIndex()
        if idx == 0:  # Canal / Rasgo
            self.cb_esp_fundo.setEnabled(True)
            self.sp_recuo_fundo.setEnabled(True)
            self.sp_prof_rasgo.setEnabled(True)
            self.sp_folga_fundo.setEnabled(True)
            self.chk_fundo.setChecked(True)
        elif idx == 1:  # Sobreposto
            self.cb_esp_fundo.setEnabled(True)
            self.sp_recuo_fundo.setEnabled(False)
            self.sp_prof_rasgo.setEnabled(False)
            self.sp_folga_fundo.setEnabled(True)
            self.chk_fundo.setChecked(True)
        else:  # Sem Fundo
            self.cb_esp_fundo.setEnabled(False)
            self.sp_recuo_fundo.setEnabled(False)
            self.sp_prof_rasgo.setEnabled(False)
            self.sp_folga_fundo.setEnabled(False)
            self.chk_fundo.setChecked(False)

    def _on_module_card_selected(self, current: QListWidgetItem | None, previous=None):
        if not current:
            return
        mod_data = current.data(Qt.UserRole)
        if not mod_data:
            return

        self.lbl_selected_title.setText(mod_data.get("nome", "Módulo"))
        desc_text = mod_data.get("desc", "")
        self.lbl_module_desc.setText(desc_text)
        self.lbl_module_desc.setToolTip(desc_text)

        # Se o usuário clicou em um modelo do catálogo diferente do módulo que estava em edição,
        # ou se não estamos editando, carregamos as dimensões e parâmetros do novo modelo escolhido!
        novo_tipo = mod_data.get("id")
        if self._editing_module:
            from ..domain.schema import module_params
            tipo_editando = module_params(self._editing_module).get("tipo")
        else:
            tipo_editando = None

        if self._editing_module is None or novo_tipo != tipo_editando:
            if self._editing_module is not None and novo_tipo != tipo_editando:
                self._editing_module = None
                self._load_module_values_if_editing()

            self.sp_largura.setValue(int(mod_data.get("largura", 800)))
            self.sp_altura.setValue(int(mod_data.get("altura", 720)))
            self.sp_prof.setValue(int(mod_data.get("profundidade", 550)))
            self.sp_rodape.setValue(int(mod_data.get("rodape", 0)))
            if mod_data.get("has_gavetas"):
                self.sp_qtd_elem.setValue(int(mod_data.get("num_gavetas", 2)))
            elif mod_data.get("has_portas"):
                self.sp_qtd_elem.setValue(int(mod_data.get("num_portas", 2)))
            self.sp_prateleiras.setValue(int(mod_data.get("num_prateleiras", 1)))
            has_fundo = bool(mod_data.get("has_fundo", True))
            if hasattr(self, "cb_tipo_fundo"):
                self.cb_tipo_fundo.setCurrentIndex(0 if has_fundo else 2)
                self.cb_esp_fundo.setCurrentIndex(0)
                self.sp_recuo_fundo.setValue(10)
                self.sp_prof_rasgo.setValue(5)
                self.sp_folga_fundo.setValue(2)
                self._on_tipo_fundo_changed()
            self.chk_fundo.setChecked(has_fundo)

            # Para módulos de Marmoraria / Bancadas: define material padrão de pedra
            if "bancada" in str(novo_tipo):
                if novo_tipo == "bancada_ilha":
                    idx_mat = self.cb_material.findText("Quartzo Branco Calacatta 20mm")
                else:
                    idx_mat = self.cb_material.findText("Granito Preto São Gabriel 20mm")
                if idx_mat >= 0:
                    self.cb_material.setCurrentIndex(idx_mat)
                idx_esp = self.cb_espessura.findText("20 mm")
                if idx_esp >= 0:
                    self.cb_espessura.setCurrentIndex(idx_esp)
                self.cb_fita_caixa.setCurrentIndex(3)
            elif self.cb_material.currentIndex() >= 5:
                self.cb_material.setCurrentIndex(0)
                self.cb_espessura.setCurrentIndex(0)
                self.cb_fita_caixa.setCurrentIndex(0)

        has_rodape = mod_data.get("has_rodape", False)
        self.sp_rodape.setEnabled(has_rodape)

        has_frentes = bool(mod_data.get("has_gavetas") or mod_data.get("has_portas"))
        self.cb_material_frentes.setEnabled(has_frentes)
        self.cb_espessura_frentes.setEnabled(has_frentes)
        if hasattr(self, "cb_puxador_tipo"):
            self.cb_puxador_tipo.setEnabled(has_frentes)
        if hasattr(self, "cb_puxador_cor"):
            self.cb_puxador_cor.setEnabled(has_frentes)

        is_misto = (mod_data.get("id") == "balcao_misto")
        mostra_config_gaveteiro = should_show_config_gaveteiro(str(mod_data.get("id", "")))
        if hasattr(self, "lbl_largura_gaveteiro"):
            self.lbl_largura_gaveteiro.setVisible(mostra_config_gaveteiro)
            self.sp_largura_gaveteiro.setVisible(mostra_config_gaveteiro)
            if mostra_config_gaveteiro:
                larg_gav_default = 450.0 if is_misto else 600.0
                self.sp_largura_gaveteiro.setValue(int(round(float(mod_data.get("largura_gaveteiro", larg_gav_default)))))
        if hasattr(self, "lbl_lado_gaveteiro"):
            self.lbl_lado_gaveteiro.setVisible(mostra_config_gaveteiro)
            self.cb_lado_gaveteiro.setVisible(mostra_config_gaveteiro)
            if mostra_config_gaveteiro:
                lado_g = str(mod_data.get("lado_gaveteiro", "esquerda")).lower()
                self.cb_lado_gaveteiro.setCurrentIndex((1 if lado_g.startswith("dir") else (2 if lado_g in ("ambos", "dois_lados", "2_lados", "both") else (3 if lado_g in ("nenhum", "sem_gavetas", "sem gavetas", "none") else 0))))

        if is_misto:
            self.lbl_qtd_elem.setText("Número de Gavetas:")
            self.sp_qtd_elem.setEnabled(True)
            self.sp_qtd_elem.setValue(int(mod_data.get("num_gavetas", 4)))
        elif mod_data.get("has_gavetas") and not mod_data.get("fixed_portas"):
            self.lbl_qtd_elem.setText("Número de Gavetas:")
            self.sp_qtd_elem.setValue(int(mod_data.get("num_gavetas", 2)))
            self.sp_qtd_elem.setEnabled(True)
        elif mod_data.get("has_portas") and mod_data.get("fixed_portas"):
            n = int(mod_data.get("num_portas", 2))
            self.lbl_qtd_elem.setText(f"Portas (fixo: {n}):")
            self.sp_qtd_elem.setValue(n)
            self.sp_qtd_elem.setEnabled(False)
        elif mod_data.get("id") in ("balcao", "aereo"):
            # Balcão e Aéreo com portas: 1 a 4 portas de 400 mm e divisória
            # estrutural automática a partir da 3ª.
            from ..domain.module_geometry import MIN_DOORS, MAX_DOORS
            self.lbl_qtd_elem.setText("Portas (400 mm cada):")
            self.sp_qtd_elem.setRange(MIN_DOORS, MAX_DOORS)
            self.sp_qtd_elem.setValue(int(mod_data.get("num_portas", 2)))
            self.sp_qtd_elem.setEnabled(True)
        elif mod_data.get("has_gavetas"):
            self.lbl_qtd_elem.setText("Número de Gavetas:")
            self.sp_qtd_elem.setEnabled(True)
        elif mod_data.get("has_portas"):
            self.lbl_qtd_elem.setText("Número de Portas:")
            self.sp_qtd_elem.setEnabled(True)
        elif mod_data.get("id") == "nicho":
            self.lbl_qtd_elem.setText("Divisões Verticais:")
            self.sp_qtd_elem.setEnabled(True)
        else:
            self.lbl_qtd_elem.setText("Divisões / Itens:")
            self.sp_qtd_elem.setEnabled(False)

        self.sp_prateleiras.setEnabled(mod_data.get("has_prateleiras", False))
        if hasattr(self, "cb_tipo_fundo"):
            self.cb_tipo_fundo.setEnabled(True)

        # ── Visibilidade dos controles de Travessas ─────────────────────────────
        mod_id = mod_data.get("id", "")
        has_porta_arm = (
            (
                bool(mod_data.get("has_portas", False)) or mod_id in (
                    "balcao", "balcao_pia", "balcao_misto", "balcao_canto", "aereo",
                    "roupeiro", "armario_prateleiras", "armario_1p_prat", "armario_2p_prat",
                    "armario_1p_cabide", "armario_3p_divisao", "torre_quente", "peca_porta"
                )
            )
            and mod_id not in (
                "peca_portas_correr", "roupeiro_correr", "roupeiro_correr_2p", "roupeiro_correr_3p",
                "aereo_correr", "aereo_correr_2p", "aereo_correr_3p", "aereo_correr_4p",
                "aereo_basculante", "aereo_basculante_duplo", "balcao_forno", "porta_tempero"
            )
        )
        if hasattr(self, "lbl_lado_porta_armario"):
            self.lbl_lado_porta_armario.setVisible(has_porta_arm)
            self.cb_lado_porta_armario.setVisible(has_porta_arm)
            if has_porta_arm:
                if mod_id == "balcao_canto":
                    self.lbl_lado_porta_armario.setText("Lado da Porta / Canto:")
                    self.cb_lado_porta_armario.setItemText(0, "⬅️ Porta à Esquerda (Cego à Direita)")
                    self.cb_lado_porta_armario.setItemText(1, "➡️ Porta à Direita (Cego à Esquerda)")
                    lado_c = str(mod_data.get("lado_cego", "esquerda")).lower()
                    self.cb_lado_porta_armario.setCurrentIndex(1 if lado_c.startswith("esq") else 0)
                else:
                    self.lbl_lado_porta_armario.setText("Lado Porta Única/Isolada:")
                    self.cb_lado_porta_armario.setItemText(0, "⬅️ Dobradiça à Esquerda (Padrão)")
                    self.cb_lado_porta_armario.setItemText(1, "➡️ Dobradiça à Direita (Invertido)")
                    lado_p = str(mod_data.get("lado_abertura_porta", "esquerda")).lower()
                    self.cb_lado_porta_armario.setCurrentIndex(1 if lado_p.startswith(("dir", "right")) else 0)

        _IDS_COZINHA_INFERIORES = {
            "balcao", "gaveteiro", "balcao_misto", "balcao_pia",
            "balcao_canto", "balcao_canto_l", "porta_tempero", "balcao_forno"
        }
        has_travessa = mod_id in _IDS_COZINHA_INFERIORES

        if hasattr(self, "lbl_travessa_section"):
            self.lbl_travessa_section.setVisible(has_travessa)
            self.lbl_larg_travessa_frontal.setVisible(has_travessa)
            self.sp_larg_travessa_frontal.setVisible(has_travessa)
            self.lbl_larg_travessa_traseira.setVisible(has_travessa)
            self.sp_larg_travessa_traseira.setVisible(has_travessa)
            self.lbl_travessa_em_pe.setVisible(has_travessa)
            self.chk_travessa_em_pe.setVisible(has_travessa)
            self.lbl_travessa_traseira_em_pe.setVisible(has_travessa)
            self.chk_travessa_traseira_em_pe.setVisible(has_travessa)
            em_pe = self.chk_travessa_em_pe.isChecked()
            self.lbl_recuo_porta_pia.setVisible(has_travessa and em_pe)
            self.sp_recuo_porta_pia.setVisible(has_travessa and em_pe)
            self.lbl_larg_travessa_frontal.setText("Travessa Frontal:")

        if hasattr(self, "sp_larg_travessa_frontal") and has_travessa:
            self.chk_travessa_em_pe.setChecked(bool(mod_data.get("travessa_frontal_em_pe", False)))
            self.chk_travessa_traseira_em_pe.setChecked(bool(mod_data.get("travessa_traseira_em_pe", False)))
            self.sp_larg_travessa_frontal.setValue(int(mod_data.get("larg_travessa_frontal_mm", 70)))
            self.sp_larg_travessa_traseira.setValue(int(mod_data.get("larg_travessa_traseira_mm", 70)))
            self.sp_recuo_porta_pia.setValue(int(mod_data.get("recuo_porta_topo_mm", 50)))
            em_pe = self.chk_travessa_em_pe.isChecked()
            self.lbl_recuo_porta_pia.setVisible(em_pe)
            self.sp_recuo_porta_pia.setVisible(em_pe)
            if hasattr(self, "cb_material_travessas"):
                self.cb_material_travessas.setCurrentIndex(0)
            if hasattr(self, "cb_espessura_travessas"):
                self.cb_espessura_travessas.setCurrentIndex(0)
            if hasattr(self, "cb_fita_travessas"):
                self.cb_fita_travessas.setCurrentIndex(0)
            if hasattr(self, "cb_material_fita_travessas"):
                self.cb_material_fita_travessas.setCurrentIndex(0)

        # ── Visibilidade dos controles de Nicho de Forno (balcao_forno) ─────────
        self._current_module_id = mod_id
        is_forno = (mod_id == "balcao_forno")
        if hasattr(self, "_forno_widgets"):
            self.lbl_forno_section.setVisible(is_forno)
            self.lbl_forno_tem_gaveta.setVisible(is_forno)
            self.chk_forno_tem_gaveta.setVisible(is_forno)
            tem_gav_f = self.chk_forno_tem_gaveta.isChecked()
            self.lbl_forno_alt_gaveta.setVisible(is_forno and tem_gav_f)
            self.sp_forno_alt_gaveta.setVisible(is_forno and tem_gav_f)
            if is_forno:
                self.chk_forno_tem_gaveta.setChecked(bool(mod_data.get("tem_gaveta", True)))
                self.sp_forno_alt_gaveta.setValue(int(mod_data.get("alt_gaveta_mm", 150)))

        # ── Visibilidade dos controles de Caixa para Geladeira (caixa_geladeira) ─
        is_geladeira = (mod_id == "caixa_geladeira")
        if hasattr(self, "_geladeira_widgets"):
            for w in self._geladeira_widgets:
                w.setVisible(is_geladeira)
            if is_geladeira:
                self.sp_geladeira_alt_nicho.setValue(int(mod_data.get("alt_nicho_geladeira_mm", 1800)))
                self.cb_geladeira_tipo_porta.setCurrentIndex(1 if mod_data.get("tipo_porta_superior") == "basculante" else 0)

        # ── Visibilidade dos controles de Aéreo Micro-ondas (aereo_microondas) ──
        is_micro = (mod_id == "aereo_microondas")
        if hasattr(self, "_micro_widgets"):
            for w in self._micro_widgets:
                w.setVisible(is_micro)
            if is_micro:
                self.cb_micro_tipo_porta.setCurrentIndex(0 if mod_data.get("tipo_porta_superior") == "basculante" else 1)

        # ── Visibilidade dos controles de Caixa de Gaveta ──────────────────────
        has_gav = bool(mod_data.get("has_gavetas", False)) or (mod_id in ("gaveteiro", "balcao_misto", "torre_quente", "gabinete_banheiro")) or (is_forno and self.chk_forno_tem_gaveta.isChecked())
        if hasattr(self, "_gaveta_widgets"):
            for w in self._gaveta_widgets:
                w.setVisible(has_gav)
            if has_gav:
                self.cb_tipo_fundo_gaveta.setCurrentIndex(0)
                self.sp_folga_corredica.setValue(26)
                self.cb_material_gaveta.setCurrentIndex(0)
                self.cb_espessura_gaveta.setCurrentIndex(0)
                self.cb_material_fita_gaveta.setCurrentIndex(0)
                self.cb_material_fundo_gaveta.setCurrentIndex(0)
                self.cb_esp_fundo_gaveta.setCurrentIndex(0)

        # ── Troca Dinâmica do Contexto da Janela (Marmoraria vs Marcenaria) ────
        is_pedra = "bancada" in str(mod_id)
        is_canto_l_asa = mod_id in ("balcao_canto_l", "bancada_canto_l", "bancada_canto")
        if hasattr(self, "_pedra_widgets"):
            for w in self._pedra_widgets:
                w.setVisible(is_pedra or is_canto_l_asa)

        # Asa fields are NOT in _pedra_widgets for balcao_canto_l (they are
        # only visible when a canto L module is selected, regardless of stone).
        # Force them visible/field-set here; the pedra block below toggles
        # them off for non-cantoL bancadas only.
        if is_canto_l_asa:
            if hasattr(self, "lbl_larg_asa_esq"):
                self.lbl_larg_asa_esq.setVisible(True)
                self.sp_larg_asa_esq.setVisible(True)
                self.lbl_larg_asa_dir.setVisible(True)
                self.sp_larg_asa_dir.setVisible(True)
                self.sp_larg_asa_esq.setValue(int(mod_data.get("larg_asa_esq", mod_data.get("larg_asa", 550))))
                self.sp_larg_asa_dir.setValue(int(mod_data.get("larg_asa_dir", mod_data.get("larg_asa", 550))))

        if hasattr(self, "lbl_batente_canto"):
            is_batente_mod = (mod_id == "balcao_canto_l")
            self.lbl_batente_canto.setVisible(is_batente_mod)
            self.chk_batente_canto.setVisible(is_batente_mod)
            if is_batente_mod:
                self.chk_batente_canto.setChecked(
                    bool(mod_data.get("tem_batente_canto", False)))

        if is_pedra:
            if hasattr(self, "lbl_rodape"):
                self.lbl_rodape.setVisible(False)
            self.sp_rodape.setVisible(False)

            if hasattr(self, "lbl_material_caixa"):
                self.lbl_material_caixa.setText("Padrão da Pedra / Granito:")
            if hasattr(self, "lbl_espessura_caixa"):
                self.lbl_espessura_caixa.setText("Espessura Chapa:")

            if hasattr(self, "lbl_fita_caixa"):
                self.lbl_fita_caixa.setVisible(False)
            if hasattr(self, "cb_fita_caixa"):
                self.cb_fita_caixa.setVisible(False)
            if hasattr(self, "lbl_material_fita_caixa"):
                self.lbl_material_fita_caixa.setVisible(False)
            if hasattr(self, "cb_material_fita_caixa"):
                self.cb_material_fita_caixa.setVisible(False)

            if hasattr(self, "lbl_material_frentes"):
                self.lbl_material_frentes.setVisible(False)
            if hasattr(self, "cb_material_frentes"):
                self.cb_material_frentes.setVisible(False)
            if hasattr(self, "lbl_espessura_frentes"):
                self.lbl_espessura_frentes.setVisible(False)
            if hasattr(self, "cb_espessura_frentes"):
                self.cb_espessura_frentes.setVisible(False)

            if hasattr(self, "lbl_puxadores_header"):
                self.lbl_puxadores_header.setVisible(False)
            if hasattr(self, "lbl_puxador_tipo"):
                self.lbl_puxador_tipo.setVisible(False)
            if hasattr(self, "cb_puxador_tipo"):
                self.cb_puxador_tipo.setVisible(False)
            if hasattr(self, "lbl_puxador_cor"):
                self.lbl_puxador_cor.setVisible(False)
            if hasattr(self, "cb_puxador_cor"):
                self.cb_puxador_cor.setVisible(False)
            if hasattr(self, "lbl_puxador_pos"):
                self.lbl_puxador_pos.setVisible(False)
            if hasattr(self, "cb_puxador_pos"):
                self.cb_puxador_pos.setVisible(False)
            if hasattr(self, "frame_perfil"):
                self.frame_perfil.setVisible(False)

            if hasattr(self, "lbl_qtd_elem"):
                self.lbl_qtd_elem.setVisible(False)
            self.sp_qtd_elem.setVisible(False)
            if hasattr(self, "lbl_largura_gaveteiro"):
                self.lbl_largura_gaveteiro.setVisible(False)
            if hasattr(self, "sp_largura_gaveteiro"):
                self.sp_largura_gaveteiro.setVisible(False)
            if hasattr(self, "lbl_lado_gaveteiro"):
                self.lbl_lado_gaveteiro.setVisible(False)
            if hasattr(self, "cb_lado_gaveteiro"):
                self.cb_lado_gaveteiro.setVisible(False)
            self.sp_prateleiras.setVisible(False)
            _lbl_prat = self.form_layout.labelForField(self.sp_prateleiras) if hasattr(self, "form_layout") else None
            if _lbl_prat:
                _lbl_prat.setVisible(False)

            if hasattr(self, "_fundo_widgets"):
                for w in self._fundo_widgets:
                    w.setVisible(False)
            if hasattr(self, "_travessa_widgets"):
                for w in self._travessa_widgets:
                    w.setVisible(False)
            if hasattr(self, "_gaveta_widgets"):
                for w in self._gaveta_widgets:
                    w.setVisible(False)

            self.sp_esp_pedra.setValue(int(mod_data.get("esp_pedra", 20)))
            self.sp_altura_saia.setValue(int(mod_data.get("altura_saia", 40)))
            self.sp_altura_frontao.setValue(int(mod_data.get("altura_frontao", 100)))
            self.chk_tem_saia_esq.setChecked(bool(mod_data.get("tem_saia_esq", True)))
            self.chk_tem_saia_dir.setChecked(bool(mod_data.get("tem_saia_dir", True)))

            is_canto_l = mod_id in ("bancada_canto_l", "bancada_canto")
            self.lbl_larg_asa_esq.setVisible(is_canto_l)
            self.sp_larg_asa_esq.setVisible(is_canto_l)
            self.lbl_larg_asa_dir.setVisible(is_canto_l)
            self.sp_larg_asa_dir.setVisible(is_canto_l)
            if is_canto_l:
                self.sp_larg_asa_esq.setValue(int(mod_data.get("larg_asa_esq", mod_data.get("larg_asa", 550))))
                self.sp_larg_asa_dir.setValue(int(mod_data.get("larg_asa_dir", mod_data.get("larg_asa", 550))))
            # For bancada_saia (non-canto), hide asa fields
            if not is_canto_l:
                self.lbl_larg_asa_esq.setVisible(False)
                self.sp_larg_asa_esq.setVisible(False)
                self.lbl_larg_asa_dir.setVisible(False)
                self.sp_larg_asa_dir.setVisible(False)

            tem_cuba = bool(mod_data.get("has_cuba", (mod_id == "bancada_pia")))
            self.lbl_tipo_cuba.setVisible(tem_cuba)
            self.cb_tipo_cuba.setVisible(tem_cuba)
            self.lbl_posicao_cuba.setVisible(tem_cuba)
            self.cb_posicao_cuba.setVisible(tem_cuba)
            self.lbl_tem_torneira.setVisible(tem_cuba)
            self.chk_tem_torneira.setVisible(tem_cuba)
            if hasattr(self, "lbl_canto_recorte"):
                self.lbl_canto_recorte.setVisible(tem_cuba)
                self.cb_canto_recorte.setVisible(tem_cuba)
                self.lbl_tem_area_molhada.setVisible(tem_cuba)
                self.chk_tem_area_molhada.setVisible(tem_cuba)

            if tem_cuba:
                self.cb_tipo_cuba.setCurrentIndex(0)
                self.cb_posicao_cuba.setCurrentIndex(0)
                self.chk_tem_torneira.setChecked(True)
                if hasattr(self, "cb_canto_recorte"):
                    self.cb_canto_recorte.setCurrentIndex(0)
                    self.chk_tem_area_molhada.setChecked(True)
        else:
            if hasattr(self, "lbl_rodape"):
                self.lbl_rodape.setVisible(True)
            self.sp_rodape.setVisible(True)

            if hasattr(self, "lbl_material_caixa"):
                self.lbl_material_caixa.setText("Padrão da Caixa / Pedra:")
            if hasattr(self, "lbl_espessura_caixa"):
                self.lbl_espessura_caixa.setText("Espessura:")

            if hasattr(self, "lbl_fita_caixa"):
                self.lbl_fita_caixa.setVisible(True)
            if hasattr(self, "cb_fita_caixa"):
                self.cb_fita_caixa.setVisible(True)
            if hasattr(self, "lbl_material_fita_caixa"):
                self.lbl_material_fita_caixa.setVisible(True)
            if hasattr(self, "cb_material_fita_caixa"):
                self.cb_material_fita_caixa.setVisible(True)

            if hasattr(self, "lbl_material_frentes"):
                self.lbl_material_frentes.setVisible(True)
            if hasattr(self, "cb_material_frentes"):
                self.cb_material_frentes.setVisible(True)
            if hasattr(self, "lbl_espessura_frentes"):
                self.lbl_espessura_frentes.setVisible(True)
            if hasattr(self, "cb_espessura_frentes"):
                self.cb_espessura_frentes.setVisible(True)

            if hasattr(self, "lbl_puxadores_header"):
                self.lbl_puxadores_header.setVisible(True)
            if hasattr(self, "lbl_puxador_tipo"):
                self.lbl_puxador_tipo.setVisible(True)
            if hasattr(self, "cb_puxador_tipo"):
                self.cb_puxador_tipo.setVisible(True)
            if hasattr(self, "lbl_puxador_cor"):
                self.lbl_puxador_cor.setVisible(True)
            if hasattr(self, "cb_puxador_cor"):
                self.cb_puxador_cor.setVisible(True)
            if hasattr(self, "lbl_puxador_pos"):
                self.lbl_puxador_pos.setVisible(True)
            if hasattr(self, "cb_puxador_pos"):
                self.cb_puxador_pos.setVisible(True)

            if hasattr(self, "lbl_qtd_elem"):
                self.lbl_qtd_elem.setVisible(True)
            self.sp_qtd_elem.setVisible(True)
            self.sp_prateleiras.setVisible(True)
            _lbl_prat = self.form_layout.labelForField(self.sp_prateleiras) if hasattr(self, "form_layout") else None
            if _lbl_prat:
                _lbl_prat.setVisible(True)

            if hasattr(self, "_fundo_widgets"):
                for w in self._fundo_widgets:
                    w.setVisible(True)

            if hasattr(self, "_travessa_widgets"):
                for w in self._travessa_widgets:
                    w.setVisible(True)

            if hasattr(self, "_gaveta_widgets"):
                for w in self._gaveta_widgets:
                    w.setVisible(True)

            # Fields that were shown by the stone-visibility loop are now restored
            is_canto_l_asa = mod_id in ("balcao_canto_l", "bancada_canto_l", "bancada_canto")
            if is_canto_l_asa and hasattr(self, "lbl_larg_asa_esq"):
                self.lbl_larg_asa_esq.setVisible(True)
                self.sp_larg_asa_esq.setVisible(True)
                self.lbl_larg_asa_dir.setVisible(True)
                self.sp_larg_asa_dir.setVisible(True)
            elif not is_canto_l_asa and hasattr(self, "lbl_larg_asa_esq"):
                self.lbl_larg_asa_esq.setVisible(False)
                self.sp_larg_asa_esq.setVisible(False)
                self.lbl_larg_asa_dir.setVisible(False)
                self.sp_larg_asa_dir.setVisible(False)

            if hasattr(self, "lbl_batente_canto"):
                is_batente_mod = (mod_id == "balcao_canto_l")
                self.lbl_batente_canto.setVisible(is_batente_mod)
                self.chk_batente_canto.setVisible(is_batente_mod)

        # ── Visibilidade dos controles de Prateleiras Avulsas ────────────────────
        is_prat_avulsa = (mod_id == "peca_prateleiras_avulsas")
        if hasattr(self, "_prat_avulsas_widgets"):
            for w in self._prat_avulsas_widgets:
                w.setVisible(is_prat_avulsa)
