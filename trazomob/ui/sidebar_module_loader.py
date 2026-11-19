# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Carregamento de modulos para edicao na barra lateral."""
from __future__ import annotations

from core.group import Group

from ..domain.catalog import MODULE_CATALOG
from ..domain.i18n import tr
from ..domain.module_geometry import get_module_carcass_bounds, get_module_category
from ..domain.param_mapper import populate_ui_from_module
from ..domain.schema import module_params
from ..domain.snap_contract import SNAP_PAREDE_OPCOES, normalize_snap_parede
from ..domain.ui_contract import DEFAULT_RECUO_FUNDO_MM, should_show_config_gaveteiro, should_show_lado_porta_armario


class SidebarModuleLoaderMixin:
    """Preenche a barra lateral a partir dos parametros do modulo."""

    def load_module(self, mod: Group) -> None:
        """Carrega os dados do módulo selecionado nos controles da barra lateral."""
        self.focus_panel()
        from ..domain.migration import migrate_legacy_group
        migrate_legacy_group(mod)
        self._updating_ui = True
        try:
            params = module_params(mod)
            tipo = params.get("tipo", "balcao")
            # Contexto Estrito: ao selecionar um módulo, esconde completamente as ferramentas de parede
            if hasattr(self, "card_paredes"):
                self.card_paredes.setVisible(False)
            if hasattr(self, "scroll_paredes"):
                self.scroll_paredes.setVisible(False)
            if hasattr(self, "card_interact"):
                self.card_interact.setVisible(True)
            if hasattr(self, "scroll_area"):
                self.scroll_area.setVisible(True)
            if hasattr(self, "actions_bar"):
                self.actions_bar.setVisible(True)
            if hasattr(self, "btn_apply"):
                self.btn_apply.setVisible(True)
            if hasattr(self, "btn_apply_same_class"):
                self.btn_apply_same_class.setVisible(True)
            if hasattr(self, "btn_save_defaults"):
                self.btn_save_defaults.setVisible(True)
            if hasattr(self, "btn_save_user_module"):
                self.btn_save_user_module.setVisible(True)
            if hasattr(self, "btn_delete"):
                self.btn_delete.setVisible(True)
            if hasattr(self, 'btn_dup_left'):
                self.btn_dup_left.setVisible(True)
            if hasattr(self, 'btn_dup_right'):
                self.btn_dup_right.setVisible(True)

            self._set_editor_enabled(True)
            self.lbl_title.setText(f"🎯 {mod.name}")
            if tipo == "peca_prateleiras_avulsas":
                n_prat = len(mod.children) if hasattr(mod, "children") else int(params.get("num_prateleiras", 2))
                A_v = float(params.get("altura", 0))
                E_v = float(params.get("espessura", 15.0))
                n_interm = int(params.get("num_prateleiras", 2))
                n_espacos = n_interm + 1
                passo_v = int(round((A_v - E_v) / n_espacos)) if n_espacos > 0 and A_v >= E_v else 0
                self.lbl_status.setText(
                    tr("📐 Altura do Vão: {alt} mm | Vão livre: ~{passo} mm | Total: {qtd} prateleiras",
                       alt=int(A_v), passo=passo_v, qtd=n_prat)
                )
            else:
                self.lbl_status.setText(tr("Tipo: {tipo} | Editando na barra lateral", tipo=tipo))

            if hasattr(self, "cb_trocar_tipo"):
                self.cb_trocar_tipo.blockSignals(True)
                idx_t = self.cb_trocar_tipo.findData(tipo)
                if idx_t >= 0:
                    self.cb_trocar_tipo.setCurrentIndex(idx_t)
                self.cb_trocar_tipo.blockSignals(False)

            # Popula valores comuns na barra lateral através do mapper centralizado
            populate_ui_from_module(self, params)

            if hasattr(self, "lbl_prof"):
                self.lbl_prof.setText(tr("Profundidade:"))
            if hasattr(self, "lbl_elevacao"):
                self.lbl_elevacao.setText(tr("Elevação do Piso:"))
                self.lbl_elevacao.setVisible(True)
            if hasattr(self, "sp_elevacao"):
                self.sp_elevacao.setVisible(True)
                if "elevacao_mm" in params:
                    elev_mm = float(params["elevacao_mm"])
                else:
                    b_mod = get_module_carcass_bounds(mod)
                    if b_mod is None:
                        from ..interaction.magnetic_drag import get_module_bounds
                        b_mod = get_module_bounds(mod)
                    if b_mod is not None:
                        elev_mm = float(b_mod[4]) * 1000.0
                    else:
                        off_val = params.get("offset")
                        elev_mm = (
                            float(off_val[2]) * 1000.0
                            if isinstance(off_val, (list, tuple)) and len(off_val) >= 3
                            else 0.0
                        )
                self.sp_elevacao.setValue(max(0, int(round(elev_mm))))

            self._on_perfil_modelo_changed()
            self.frame_perfil.setVisible(params.get("puxador_tipo", "alca") == "perfil")

            # Portas / Gavetas
            from ..domain.module_geometry import (MIN_DOORS, MAX_DOORS,
                                          auto_divisoes_for_doors)
            self._portas_400mm = False

            _mod_cat = next(
                (m for cat in MODULE_CATALOG.values() for m in cat if m.get("id") == tipo),
                {}
            ) if tipo else {}

            # Checagem semântica para saber se o módulo suporta portas ou gavetas
            is_cama = str(tipo).startswith("cama_") or tipo in ("bicama", "beliche")
            is_peca_avulsa = str(tipo).startswith("peca_") or tipo in ("rodape_fechado", "rodape_avulso")
            is_gaveteiro = (tipo == "gaveteiro") or (
                params.get("has_gavetas") is True and not params.get("has_portas", False)
            )
            has_portas_suportadas = bool(_mod_cat.get("has_portas", False))
            has_gavetas_suportadas = bool(_mod_cat.get("has_gavetas", False))
            has_prat_suportadas = bool(_mod_cat.get("has_prateleiras", False))
            has_fundo_suportado = bool(_mod_cat.get("has_fundo", True))
            has_rodape_suportado = bool(_mod_cat.get("has_rodape", False))
            is_canto_reto = (tipo == "balcao_canto")

            # Configura visibilidade do seletor de Portas / Gavetas / Vãos (sp_qtd_elem)
            if is_canto_reto:
                # Balcão de Canto Reto: 1 porta fixa, sem campo seletor de portas
                self.lbl_qtd_elem.setVisible(False)
                self.sp_qtd_elem.setVisible(False)
            elif tipo in ("nicho", "peca_prateleiras_avulsas"):
                self.lbl_qtd_elem.setVisible(True)
                self.sp_qtd_elem.setVisible(True)
                self.lbl_qtd_elem.setText(tr("Prateleiras:"))
                self.sp_qtd_elem.setRange(1 if tipo == "peca_prateleiras_avulsas" else 0, 12 if tipo == "peca_prateleiras_avulsas" else 6)
                self.sp_qtd_elem.setValue(int(params.get("num_prateleiras", 2 if tipo == "peca_prateleiras_avulsas" else params.get("divisoes_horiz", 1))))
                self.sp_qtd_elem.setEnabled(True)
            elif tipo in ("cama_gaveteiros", "bicama"):
                self.lbl_qtd_elem.setVisible(True)
                self.sp_qtd_elem.setVisible(True)
                self.lbl_qtd_elem.setText(tr("Gavetões:"))
                self.sp_qtd_elem.setRange(1, 6)
                self.sp_qtd_elem.setValue(int(params.get("num_gavetoes", params.get("num_gavetas", 4 if tipo == "cama_gaveteiros" else 1))))
                self.sp_qtd_elem.setEnabled(True)
            elif is_cama:
                # Camas baú, cabeceira e beliche não possuem portas nem gavetas
                self.lbl_qtd_elem.setVisible(False)
                self.sp_qtd_elem.setVisible(False)
            elif is_peca_avulsa and tipo != "peca_portas_correr":
                # Peças avulsas comuns não possuem seletor de portas/gavetas
                self.lbl_qtd_elem.setVisible(False)
                self.sp_qtd_elem.setVisible(False)
            elif tipo == "balcao_forno":
                # Balcão forno: não tem seletor de quantidade de gavetas (tem apenas 1 gaveta opcional configurada na aba de ajustes)
                self.lbl_qtd_elem.setVisible(False)
                self.sp_qtd_elem.setVisible(False)
            elif is_gaveteiro and tipo == "gaveteiro":
                self.lbl_qtd_elem.setVisible(True)
                self.sp_qtd_elem.setVisible(True)
                self.lbl_qtd_elem.setText(tr("Gavetas:"))
                self.sp_qtd_elem.setRange(1, 8)
                self.sp_qtd_elem.setValue(int(params.get("num_gavetas", 4)))
                self.sp_qtd_elem.setEnabled(True)
            elif tipo == "balcao_misto":
                # Balcão Misto: Gaveteiro + 1 a 3 portas (cada porta padrão 400mm)
                self.lbl_qtd_elem.setVisible(True)
                self.sp_qtd_elem.setVisible(True)
                self.lbl_qtd_elem.setText(tr("Portas:"))
                self.sp_qtd_elem.setRange(1, 3)
                n_p = int(params.get("num_portas", 2))
                self.sp_qtd_elem.setValue(max(1, min(3, n_p)))
                self.sp_qtd_elem.setEnabled(True)
                self._portas_400mm = True
            elif has_portas_suportadas:
                self.lbl_qtd_elem.setVisible(True)
                self.sp_qtd_elem.setVisible(True)
                n_p = int(params.get("num_portas", 2))
                if _mod_cat.get("fixed_portas"):
                    self.lbl_qtd_elem.setText(f"{tr('Portas:')} ({n_p})")
                    self.sp_qtd_elem.setRange(0, 8)
                    self.sp_qtd_elem.setValue(n_p)
                    self.sp_qtd_elem.setEnabled(False)
                elif tipo in ("balcao", "aereo"):
                    # Balcão e Aéreo com portas: 1 a 4 portas de 400 mm e divisória automática a partir da 3ª
                    self.lbl_qtd_elem.setText(tr("Portas:"))
                    self.sp_qtd_elem.setRange(MIN_DOORS, MAX_DOORS)
                    self.sp_qtd_elem.setValue(n_p)
                    self.sp_qtd_elem.setEnabled(True)
                    self._portas_400mm = True
                elif tipo in ("roupeiro_correr", "roupeiro_correr_2p", "roupeiro_correr_3p"):
                    self.lbl_qtd_elem.setText(tr("Vãos / Portas:"))
                    self.sp_qtd_elem.setRange(2, 3)
                    self.sp_qtd_elem.setValue(int(params.get("num_vaos", n_p)))
                    self.sp_qtd_elem.setEnabled(True)
                elif tipo in ("aereo_correr", "aereo_correr_2p", "aereo_correr_3p", "aereo_correr_4p"):
                    self.lbl_qtd_elem.setText(tr("Vãos / Portas:"))
                    self.sp_qtd_elem.setRange(2, 4)
                    self.sp_qtd_elem.setValue(max(2, min(4, int(params.get("num_vaos", n_p)))))
                    self.sp_qtd_elem.setEnabled(True)
                elif tipo == "peca_portas_correr":
                    self.lbl_qtd_elem.setText(tr("Portas:"))
                    self.sp_qtd_elem.setRange(2, 4)
                    self.sp_qtd_elem.setValue(max(2, min(4, n_p)))
                    self.sp_qtd_elem.setEnabled(True)
                else:
                    self.lbl_qtd_elem.setText(tr("Portas:"))
                    self.sp_qtd_elem.setRange(1, 8)
                    self.sp_qtd_elem.setValue(n_p)
                    self.sp_qtd_elem.setEnabled(True)
            elif has_gavetas_suportadas and "num_gavetas" in params and params["num_gavetas"] > 0:
                self.lbl_qtd_elem.setVisible(True)
                self.sp_qtd_elem.setVisible(True)
                self.lbl_qtd_elem.setText(tr("Gavetas:"))
                self.sp_qtd_elem.setRange(1, 8)
                self.sp_qtd_elem.setValue(int(params["num_gavetas"]))
                self.sp_qtd_elem.setEnabled(True)
            else:
                self.lbl_qtd_elem.setVisible(False)
                self.sp_qtd_elem.setVisible(False)

            # Divisórias verticais: só devem existir para balcão ou módulos que suportam divisória explícita
            # Para canto reto, canto L, nichos, camas, peças avulsas, gaveteiros, etc. NÃO há divisória vertical.
            supports_divisoes = (tipo in ("balcao", "nicho"))
            self._auto_divisoes = (tipo == "balcao")
            self.lbl_divisoes.setVisible(supports_divisoes and not self._auto_divisoes)
            self.sp_divisoes.setVisible(supports_divisoes and not self._auto_divisoes)
            if self._auto_divisoes:
                self.sp_divisoes.setValue(
                    auto_divisoes_for_doors(int(params.get("num_portas", 2))))
            elif supports_divisoes:
                self.sp_divisoes.setValue(int(params.get("num_divisoes", params.get("divisoes_vert", 0))))
            else:
                self.sp_divisoes.setValue(0)

            # Prateleiras internas: apenas para módulos com has_prateleiras=True
            self.lbl_prateleiras.setVisible(has_prat_suportadas)
            self.sp_prateleiras.setVisible(has_prat_suportadas)
            if has_prat_suportadas and "num_prateleiras" in params:
                self.sp_prateleiras.setValue(params["num_prateleiras"])

            is_misto = (tipo == "balcao_misto")
            mostra_config_gaveteiro = should_show_config_gaveteiro(tipo)
            if hasattr(self, "lbl_largura_gaveteiro"):
                self.lbl_largura_gaveteiro.setVisible(mostra_config_gaveteiro)
                self.sp_largura_gaveteiro.setVisible(mostra_config_gaveteiro)
                if mostra_config_gaveteiro:
                    larg_gav_default = 450.0 if is_misto else 600.0
                    self.sp_largura_gaveteiro.setValue(int(round(float(params.get("largura_gaveteiro", larg_gav_default)))))
            if hasattr(self, "lbl_lado_gaveteiro"):
                self.lbl_lado_gaveteiro.setVisible(mostra_config_gaveteiro)
                self.cb_lado_gaveteiro.setVisible(mostra_config_gaveteiro)
                if mostra_config_gaveteiro:
                    lado_g = str(params.get("lado_gaveteiro", "esquerda")).lower()
                    self.cb_lado_gaveteiro.setCurrentIndex((1 if lado_g.startswith("dir") else (2 if lado_g in ("ambos", "dois_lados", "2_lados", "both") else (3 if lado_g in ("nenhum", "sem_gavetas", "sem gavetas", "none") else 0))))

            has_porta_arm = (
                (
                    has_portas_suportadas or "num_portas" in params or tipo in (
                        "balcao", "balcao_pia", "balcao_misto", "balcao_canto", "aereo",
                        "roupeiro", "armario_prateleiras", "armario_1p_prat", "armario_2p_prat",
                        "armario_1p_cabide", "armario_3p_divisao", "torre_quente", "peca_porta"
                    )
                )
                and tipo not in (
                    "peca_portas_correr", "roupeiro_correr", "roupeiro_correr_2p", "roupeiro_correr_3p",
                    "aereo_correr", "aereo_correr_2p", "aereo_correr_3p", "aereo_correr_4p",
                    "aereo_basculante", "aereo_basculante_duplo", "balcao_forno", "porta_tempero"
                )
                and not is_cama
                and not (is_peca_avulsa and tipo != "peca_porta")
            )
            self._current_has_porta_arm = has_porta_arm
            self._current_selected_tipo = tipo
            num_portas_cur = int(
                params.get(
                    "num_portas",
                    self.sp_qtd_elem.value() if hasattr(self, "sp_qtd_elem") else 2,
                )
            )
            show_lado_porta = should_show_lado_porta_armario(tipo, has_porta_arm, num_portas_cur)
            if hasattr(self, "lbl_lado_porta_armario"):
                self.lbl_lado_porta_armario.setVisible(show_lado_porta)
                self.cb_lado_porta_armario.setVisible(show_lado_porta)
                if has_porta_arm:
                    if tipo == "balcao_canto":
                        self.lbl_lado_porta_armario.setText(tr("Lado da Porta / Canto:"))
                        self.cb_lado_porta_armario.setItemText(0, tr("⬅️ Porta à Esquerda (Cego à Direita)"))
                        self.cb_lado_porta_armario.setItemText(1, tr("➡️ Porta à Direita (Cego à Esquerda)"))
                        lado_c = str(params.get("lado_cego", "esquerda")).lower()
                        # Se lado_cego é esquerda -> porta à direita (idx 1)
                        # Se lado_cego é direita -> porta à esquerda (idx 0)
                        self.cb_lado_porta_armario.setCurrentIndex(1 if lado_c.startswith("esq") else 0)
                    else:
                        self.lbl_lado_porta_armario.setText(tr("Lado Porta Única/Isolada:"))
                        self.cb_lado_porta_armario.setItemText(0, tr("⬅️ Dobradiça à Esquerda (Padrão)"))
                        self.cb_lado_porta_armario.setItemText(1, tr("➡️ Dobradiça à Direita (Invertido)"))
                        lado_p = str(params.get("lado_abertura_porta", "esquerda")).lower()
                        self.cb_lado_porta_armario.setCurrentIndex(1 if lado_p.startswith(("dir", "right")) else 0)

            is_canto_reto = (tipo == "balcao_canto")
            if hasattr(self, "lbl_largura_cego_canto"):
                self.lbl_largura_cego_canto.setVisible(is_canto_reto)
                self.sp_largura_cego_canto.setVisible(is_canto_reto)
                if is_canto_reto:
                    val_c = float(params.get("largura_cego_mm", 500.0))
                    self.sp_largura_cego_canto.setValue(int(round(val_c)))

            if hasattr(self, "lbl_regua_fechamento_canto"):
                self.lbl_regua_fechamento_canto.setVisible(is_canto_reto)
                self.chk_regua_fechamento_canto.setVisible(is_canto_reto)
                self.sp_larg_regua_canto.setVisible(is_canto_reto)
                if is_canto_reto:
                    self.chk_regua_fechamento_canto.setChecked(bool(params.get("tem_regua_fechamento", False)))
                    self.sp_larg_regua_canto.setValue(int(round(float(params.get("larg_regua_fechamento_mm", 50.0)))))

            if hasattr(self, "lbl_dist_regua_canto"):
                self.lbl_dist_regua_canto.setVisible(is_canto_reto)
                self.sp_dist_regua_canto.setVisible(is_canto_reto)
                if is_canto_reto:
                    val_d = float(params.get("dist_regua_fechamento_mm", 0.0))
                    self.sp_dist_regua_canto.setValue(int(round(val_d)))

            is_canto_l_mod = tipo in ("balcao_canto_l", "bancada_canto_l", "bancada_canto")
            if hasattr(self, "lbl_larg_asa_esq"):
                self.lbl_larg_asa_esq.setVisible(is_canto_l_mod)
                self.sp_larg_asa_esq.setVisible(is_canto_l_mod)
                self.lbl_larg_asa_dir.setVisible(is_canto_l_mod)
                self.sp_larg_asa_dir.setVisible(is_canto_l_mod)
                if is_canto_l_mod:
                    self.sp_larg_asa_esq.setValue(int(round(float(params.get("larg_asa_esq", params.get("larg_asa", 550.0))))))
                    self.sp_larg_asa_dir.setValue(int(round(float(params.get("larg_asa_dir", params.get("larg_asa", 550.0))))))
                if hasattr(self, "lbl_batente_canto"):
                    is_batente_mod = (tipo == "balcao_canto_l")
                    self.lbl_batente_canto.setVisible(is_batente_mod)
                    self.chk_batente_canto.setVisible(is_batente_mod)
                    if is_batente_mod:
                        self.chk_batente_canto.setChecked(
                            bool(params.get("tem_batente_canto", False)))
            else:
                # Fields not built yet (e.g. in _on_edit path) - skip
                pass

            # Travessas Superiores — visíveis só para módulos de cozinha inferiores
            _IDS_COZINHA_INFERIORES = {
                "balcao", "gaveteiro", "balcao_misto", "balcao_pia",
                "balcao_canto", "balcao_canto_l", "porta_tempero", "balcao_forno"
            }
            has_travessa = tipo in _IDS_COZINHA_INFERIORES
            self._current_has_travessa = has_travessa
            self._recuo_fundo_locked_by_travessa = False
            self._recuo_fundo_before_travessa_lock = int(
                round(float(params.get("recuo_fundo", DEFAULT_RECUO_FUNDO_MM)))
            )
            if hasattr(self, "_travessa_sidebar_widgets"):
                for w in self._travessa_sidebar_widgets:
                    w.setVisible(has_travessa)
                if has_travessa:
                    tf_em_pe = bool(params.get("travessa_frontal_em_pe", (tipo in ("balcao_pia", "balcao_forno"))))
                    tt_em_pe = bool(params.get("travessa_traseira_em_pe", False))
                    self.chk_travessa_frontal_em_pe.setChecked(tf_em_pe)
                    self.chk_travessa_traseira_em_pe.setChecked(tt_em_pe)
                    larg_f = params.get("larg_travessa_frontal_mm", params.get("larg_travessa_mm", 70.0))
                    larg_t = params.get("larg_travessa_traseira_mm", 70.0)
                    recuo = params.get("recuo_porta_topo_mm", params.get("recuo_porta_pia_mm", 50.0))
                    self.sp_larg_travessa_frontal.setValue(int(round(float(larg_f))))
                    self.sp_larg_travessa_traseira.setValue(int(round(float(larg_t))))
                    self.sp_recuo_porta_topo.setValue(int(round(float(recuo))))
                    self.lbl_recuo_porta_topo.setVisible(tf_em_pe)
                    self.sp_recuo_porta_topo.setVisible(tf_em_pe)

                    # Material travessas
                    mat_t = params.get("material_travessas")
                    if mat_t and hasattr(self, "cb_material_travessas"):
                        m_idx = 0
                        for i in range(self.cb_material_travessas.count()):
                            t_txt = self.cb_material_travessas.itemText(i)
                            if t_txt in mat_t and not t_txt.startswith("("):
                                m_idx = i
                                break
                        self.cb_material_travessas.setCurrentIndex(m_idx)
                    elif hasattr(self, "cb_material_travessas"):
                        self.cb_material_travessas.setCurrentIndex(0)

                    # Espessura travessas
                    esp_t = params.get("esp_travessas_mm", params.get("espessura_travessas"))
                    if esp_t and hasattr(self, "cb_espessura_travessas"):
                        e_idx = self.cb_espessura_travessas.findText(f"{int(round(float(esp_t)))} mm")
                        self.cb_espessura_travessas.setCurrentIndex(e_idx if e_idx >= 0 else 0)
                    elif hasattr(self, "cb_espessura_travessas"):
                        self.cb_espessura_travessas.setCurrentIndex(0)

                    # Fita de borda travessas
                    modo_f = params.get("fita_travessas_modo", "frontal_1L")
                    if hasattr(self, "cb_fita_travessas"):
                        fita_map = {"frontal_1l": 0, "2l": 1, "4l": 2, "sem_fita": 3}
                        self.cb_fita_travessas.setCurrentIndex(fita_map.get(str(modo_f).lower(), 0))

                    if hasattr(self, "cb_material_fita_travessas"):
                        mat_ftr = params.get("material_fita_travessas")
                        if mat_ftr:
                            idx_ftr = 0
                            for i in range(self.cb_material_fita_travessas.count()):
                                txt_i = self.cb_material_fita_travessas.itemText(i)
                                if txt_i in mat_ftr and not txt_i.startswith("("):
                                    idx_ftr = i
                                    break
                            self.cb_material_fita_travessas.setCurrentIndex(idx_ftr)
                        else:
                            self.cb_material_fita_travessas.setCurrentIndex(0)

            # Fundo (sincronização de interface após carregar travessas)
            self._on_tipo_fundo_changed()

            # Nicho de Forno (balcao_forno)
            self._current_selected_tipo = tipo
            is_forno = (tipo == "balcao_forno")
            if hasattr(self, "_forno_sidebar_widgets"):
                for w in self._forno_sidebar_widgets:
                    w.setVisible(is_forno)
                if is_forno:
                    tem_gav_f = bool(params.get("tem_gaveta", True))
                    self.chk_forno_tem_gaveta.setChecked(tem_gav_f)
                    self.sp_forno_alt_gaveta.setValue(int(round(float(params.get("alt_gaveta_mm", 150.0)))))
                    self.lbl_forno_alt_gaveta.setVisible(tem_gav_f)
                    self.sp_forno_alt_gaveta.setVisible(tem_gav_f)

            # Porta-Tempero (porta_tempero)
            is_tempero = (tipo == "porta_tempero")
            if hasattr(self, "_tempero_sidebar_widgets"):
                for w in self._tempero_sidebar_widgets:
                    w.setVisible(is_tempero)
                if is_tempero:
                    tipo_est = str(params.get("tipo_estrutura_tempero", "mdf")).lower()
                    is_aramado = (tipo_est == "aramado")
                    self.cb_tipo_estrutura_tempero.setCurrentIndex(1 if is_aramado else 0)
                    cor_aram = str(params.get("cor_aramado", "cromado")).lower()
                    self.cb_cor_aramado.setCurrentIndex(1 if ("preto" in cor_aram or "black" in cor_aram) else 0)
                    self.lbl_cor_aramado.setVisible(is_aramado)
                    self.cb_cor_aramado.setVisible(is_aramado)

            # Nicho de Geladeira (caixa_geladeira)
            is_geladeira = (tipo == "caixa_geladeira")
            if hasattr(self, "_geladeira_sidebar_widgets"):
                for w in self._geladeira_sidebar_widgets:
                    w.setVisible(is_geladeira)
                if is_geladeira:
                    self.sp_geladeira_alt_nicho.setValue(int(round(float(params.get("alt_nicho_geladeira_mm", 1800.0)))))
                    is_b = (str(params.get("tipo_porta_superior", "")).lower() in ("basculante", "1_porta") or int(params.get("num_portas", 2)) == 1)
                    self.cb_geladeira_tipo_porta.setCurrentIndex(1 if is_b else 0)

            # Aéreo Micro-ondas (aereo_microondas)
            is_micro = (tipo == "aereo_microondas")
            if hasattr(self, "_micro_sidebar_widgets"):
                for w in self._micro_sidebar_widgets:
                    w.setVisible(is_micro)
                if is_micro:
                    is_b_micro = (str(params.get("tipo_porta_superior", "basculante")).lower() in ("basculante", "1_porta") or int(params.get("num_portas", 1)) == 1)
                    self.cb_micro_tipo_porta.setCurrentIndex(0 if is_b_micro else 1)

            # Caixa de Gaveta — visíveis apenas para módulos com gavetas reais (nunca para camas ou peças sem gaveta)
            has_gav = not is_cama and (("num_gavetas" in params) or (tipo in ("gaveteiro", "balcao_misto", "torre_quente", "gabinete_banheiro")) or (is_forno and bool(params.get("tem_gaveta", True))))
            if hasattr(self, "_gaveta_sidebar_widgets"):
                for w in self._gaveta_sidebar_widgets:
                    w.setVisible(has_gav)
                if has_gav:
                    # Tipo de fundo da gaveta
                    m_fg = str(params.get("tipo_fundo_gaveta", "rasgo")).lower()
                    self.cb_tipo_fundo_gaveta.setCurrentIndex(1 if m_fg in ("por_baixo", "baixo") else 0)

                    # Folga da corrediça
                    self.sp_folga_corredica.setValue(int(round(float(params.get("folga_corredica_mm", 26.0)))))

                    # Material da gaveta
                    mg = params.get("material_gaveta")
                    if mg and hasattr(self, "cb_material_gaveta"):
                        idx_mg = 0
                        for i in range(self.cb_material_gaveta.count()):
                            t_txt = self.cb_material_gaveta.itemText(i)
                            if t_txt in mg and not t_txt.startswith("("):
                                idx_mg = i
                                break
                        self.cb_material_gaveta.setCurrentIndex(idx_mg)
                    else:
                        self.cb_material_gaveta.setCurrentIndex(0)

                    # Espessura da gaveta
                    eg = params.get("esp_gaveta_mm", 15.0)
                    idx_eg = self.cb_espessura_gaveta.findText(f"{int(round(float(eg)))} mm")
                    self.cb_espessura_gaveta.setCurrentIndex(idx_eg if idx_eg >= 0 else 0)

                    # Material fita gaveta
                    mfg = params.get("material_fita_gaveta")
                    if mfg and hasattr(self, "cb_material_fita_gaveta"):
                        idx_mfg = 0
                        for i in range(self.cb_material_fita_gaveta.count()):
                            t_txt = self.cb_material_fita_gaveta.itemText(i)
                            if t_txt in mfg and not t_txt.startswith("("):
                                idx_mfg = i
                                break
                        self.cb_material_fita_gaveta.setCurrentIndex(idx_mfg)
                    else:
                        self.cb_material_fita_gaveta.setCurrentIndex(0)

                    # Material fundo gaveta
                    m_fundo_g = params.get("material_fundo_gaveta")
                    if m_fundo_g and hasattr(self, "cb_material_fundo_gaveta"):
                        idx_mfg = 0
                        for i in range(self.cb_material_fundo_gaveta.count()):
                            t_txt = self.cb_material_fundo_gaveta.itemText(i)
                            if t_txt in m_fundo_g and not t_txt.startswith("("):
                                idx_mfg = i
                                break
                        self.cb_material_fundo_gaveta.setCurrentIndex(idx_mfg)
                    else:
                        self.cb_material_fundo_gaveta.setCurrentIndex(0)

                    # Espessura fundo gaveta
                    efg = params.get("esp_fundo_gaveta_mm", 6.0)
                    idx_efg = self.cb_esp_fundo_gaveta.findText(f"{int(round(float(efg)))} mm")
                    self.cb_esp_fundo_gaveta.setCurrentIndex(idx_efg if idx_efg >= 0 else 0)

            if hasattr(self, "chk_gerar_furacao"):
                self.chk_gerar_furacao.setChecked(bool(params.get("gerar_furacao", True)))
            if hasattr(self, "cb_dispositivo_fixacao"):
                disp = str(params.get("dispositivo_fixacao", "minifix_cavilha")).lower()
                disp_map = {"minifix_cavilha": 0, "cavilha_soberba": 1, "soberba": 2, "cavilha": 3}
                self.cb_dispositivo_fixacao.setCurrentIndex(disp_map.get(disp, 0))
            if hasattr(self, "cb_dispositivo_prateleira"):
                disp_p = str(params.get("dispositivo_prateleira", params.get("fixacao_prateleira", "cavilha"))).lower()
                disp_p_map = {"cavilha": 0, "vb35": 1, "vb_35": 1, "vb": 1, "vb36": 2, "vb_36": 2}
                self.cb_dispositivo_prateleira.setCurrentIndex(disp_p_map.get(disp_p, 0))

            # ── Troca Dinâmica do Contexto da Barra Lateral (Móvel vs Pedra vs Cama vs Peça Avulsa) ──
            is_pedra = "bancada" in str(tipo)
            is_canto_l_asa = tipo in ("balcao_canto_l", "bancada_canto_l", "bancada_canto")

            # Avaliação de abas
            tem_puxadores_reais = (
                (has_portas_suportadas or has_gavetas_suportadas or tipo in ("balcao", "gaveteiro", "balcao_misto", "porta_tempero", "cama_gaveteiros", "peca_porta", "peca_porta_esquerda", "peca_porta_direita", "peca_porta_basculante", "peca_frente_gaveta"))
                and not is_pedra
                and tipo not in ("cama_bau", "cama_cabeceira", "cama_colmeia", "bicama", "beliche", "armario_maleiro_tamponado", "nicho")
                and not (is_peca_avulsa and not str(tipo).startswith(("peca_porta", "peca_frente_gaveta")))
            )
            tem_estrutura_interna = (
                (has_prat_suportadas or supports_divisoes or has_gavetas_suportadas or has_fundo_suportado or has_rodape_suportado or is_misto or tipo in ("balcao_misto", "balcao_forno", "cama_colmeia"))
                and not is_pedra
                and (not is_cama or tipo == "cama_colmeia")
                and not (is_peca_avulsa and tipo != "peca_portas_correr")
            )

            if hasattr(self, "sec_dimensoes"):
                self.sec_dimensoes.set_tab_visible(True)
            if hasattr(self, "sec_frentes"):
                self.sec_frentes.set_tab_visible(tem_estrutura_interna)
            if hasattr(self, "sec_puxadores"):
                self.sec_puxadores.set_tab_visible(tem_puxadores_reais)
            if hasattr(self, "sec_materiais"):
                self.sec_materiais.set_tab_visible(True)
            if hasattr(self, "sec_ajustes"):
                # Exibe a aba de Ajustes/Avançado para móveis com estrutura, incluindo camas com montagem mecânica (ex: cama_colmeia)
                self.sec_ajustes.set_tab_visible(
                    (not is_cama or tipo == "cama_colmeia")
                    and tipo != "bancada_tampao_engrossado"
                    and not (is_peca_avulsa and tipo not in ("peca_tampo_engrossado", "peca_divisoria_vertical", "peca_prateleiras_avulsas"))
                )
            if hasattr(self, "_pedra_sidebar_widgets"):
                for w in self._pedra_sidebar_widgets:
                    w.setVisible(is_pedra)

            if hasattr(self, "_cama_colmeia_sidebar_widgets"):
                for w in self._cama_colmeia_sidebar_widgets:
                    w.setVisible(tipo == "cama_colmeia")

            if is_canto_l_asa:
                if hasattr(self, "lbl_larg_asa_esq"):
                    self.lbl_larg_asa_esq.setVisible(True)
                    self.sp_larg_asa_esq.setVisible(True)
                    self.lbl_larg_asa_dir.setVisible(True)
                    self.sp_larg_asa_dir.setVisible(True)
                    self.sp_larg_asa_esq.setValue(int(round(float(params.get("larg_asa_esq", params.get("larg_asa", 550.0))))))
                    self.sp_larg_asa_dir.setValue(int(round(float(params.get("larg_asa_dir", params.get("larg_asa", 550.0))))))

            if is_pedra:
                # Oculta seções exclusivas de marcenaria
                if hasattr(self, "lbl_rodape"):
                    self.lbl_rodape.setVisible(False)
                self.sp_rodape.setVisible(False)

                if hasattr(self, "lbl_materiais_header"):
                    self.lbl_materiais_header.setVisible(False)
                if hasattr(self, "lbl_material_caixa"):
                    self.lbl_material_caixa.setText("Padrão da Pedra:")
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
                self.cb_puxador_tipo.setVisible(False)
                if hasattr(self, "lbl_puxador_cor"):
                    self.lbl_puxador_cor.setVisible(False)
                self.cb_puxador_cor.setVisible(False)
                if hasattr(self, "lbl_puxador_pos"):
                    self.lbl_puxador_pos.setVisible(False)
                self.cb_puxador_pos.setVisible(False)
                if hasattr(self, "frame_perfil"):
                    self.frame_perfil.setVisible(False)

                if hasattr(self, "lbl_estrutura_header"):
                    self.lbl_estrutura_header.setVisible(False)
                if hasattr(self, "lbl_qtd_elem"):
                    self.lbl_qtd_elem.setVisible(False)
                self.sp_qtd_elem.setVisible(False)
                if hasattr(self, "lbl_largura_gaveteiro"):
                    self.lbl_largura_gaveteiro.setVisible(False)
                if hasattr(self, "sp_largura_gaveteiro"):
                    self.sp_largura_gaveteiro.setVisible(False)
                if hasattr(self, "lbl_prateleiras"):
                    self.lbl_prateleiras.setVisible(False)
                self.sp_prateleiras.setVisible(False)

                if hasattr(self, "_fundo_sidebar_widgets"):
                    for w in self._fundo_sidebar_widgets:
                        w.setVisible(False)
                if hasattr(self, "_travessa_sidebar_widgets"):
                    for w in self._travessa_sidebar_widgets:
                        w.setVisible(False)
                if hasattr(self, "_gaveta_sidebar_widgets"):
                    for w in self._gaveta_sidebar_widgets:
                        w.setVisible(False)

                if hasattr(self, "lbl_furacao"):
                    self.lbl_furacao.setVisible(False)
                if hasattr(self, "chk_gerar_furacao"):
                    self.chk_gerar_furacao.setVisible(False)
                if hasattr(self, "lbl_dispositivo_fixacao"):
                    self.lbl_dispositivo_fixacao.setVisible(False)
                if hasattr(self, "cb_dispositivo_fixacao"):
                    self.cb_dispositivo_fixacao.setVisible(False)
                if hasattr(self, "lbl_dispositivo_prateleira"):
                    self.lbl_dispositivo_prateleira.setVisible(False)
                if hasattr(self, "cb_dispositivo_prateleira"):
                    self.cb_dispositivo_prateleira.setVisible(False)
                if hasattr(self, "lbl_folga_frentes"):
                    self.lbl_folga_frentes.setVisible(False)
                if hasattr(self, "sp_folga_frentes"):
                    self.sp_folga_frentes.setVisible(False)

                # Carrega parâmetros específicos de bancada de pedra
                self.sp_esp_pedra.setValue(int(round(float(params.get("esp_pedra", 20.0)))))
                self.sp_altura_saia.setValue(int(round(float(params.get("altura_saia", 40.0)))))
                self.sp_altura_frontao.setValue(int(round(float(params.get("altura_frontao", 100.0)))))
                self.chk_tem_saia_esq.setChecked(bool(params.get("tem_saia_esq", True)))
                self.chk_tem_saia_dir.setChecked(bool(params.get("tem_saia_dir", True)))

                is_canto_l = tipo in ("bancada_canto_l", "bancada_canto")
                if hasattr(self, "lbl_larg_asa_esq"):
                    self.lbl_larg_asa_esq.setVisible(is_canto_l)
                    self.sp_larg_asa_esq.setVisible(is_canto_l)
                    self.lbl_larg_asa_dir.setVisible(is_canto_l)
                    self.sp_larg_asa_dir.setVisible(is_canto_l)
                if is_canto_l:
                    self.sp_larg_asa_esq.setValue(int(round(float(params.get("larg_asa_esq", params.get("larg_asa", 600.0))))))
                    self.sp_larg_asa_dir.setValue(int(round(float(params.get("larg_asa_dir", params.get("larg_asa", 600.0))))))
                else:
                    if hasattr(self, "lbl_larg_asa_esq"):
                        self.lbl_larg_asa_esq.setVisible(False)
                        self.sp_larg_asa_esq.setVisible(False)
                        self.lbl_larg_asa_dir.setVisible(False)
                        self.sp_larg_asa_dir.setVisible(False)

                tem_cuba = bool(params.get("has_cuba", (tipo == "bancada_pia")))
                self.lbl_tipo_cuba.setVisible(tem_cuba)
                self.cb_tipo_cuba.setVisible(tem_cuba)
                self.lbl_posicao_cuba.setVisible(tem_cuba)
                self.cb_posicao_cuba.setVisible(tem_cuba)
                self.lbl_tem_torneira.setVisible(tem_cuba)
                self.chk_tem_torneira.setVisible(tem_cuba)

                if tipo == "bancada_tampao_engrossado":
                    if hasattr(self, "lbl_prof"):
                        self.lbl_prof.setText("Espessura (Engrosso):")
                    if hasattr(self, "lbl_elevacao"):
                        self.lbl_elevacao.setVisible(False)
                    if hasattr(self, "sp_elevacao"):
                        self.sp_elevacao.setVisible(False)
                    for w_b in (
                        self.lbl_altura_saia, self.sp_altura_saia,
                        self.lbl_altura_frontao, self.sp_altura_frontao,
                        self.lbl_tem_saia_esq, self.chk_tem_saia_esq,
                        self.lbl_tem_saia_dir, self.chk_tem_saia_dir,
                        self.lbl_canto_recorte, self.cb_canto_recorte,
                        self.lbl_tem_area_molhada, self.chk_tem_area_molhada,
                    ):
                        w_b.setVisible(False)
                if hasattr(self, "lbl_canto_recorte"):
                    self.lbl_canto_recorte.setVisible(tem_cuba)
                    self.cb_canto_recorte.setVisible(tem_cuba)
                    self.lbl_tem_area_molhada.setVisible(tem_cuba)
                    self.chk_tem_area_molhada.setVisible(tem_cuba)

                if tem_cuba:
                    cuba_val = str(params.get("tipo_cuba", "inox_simples")).lower()
                    cuba_map = {"inox_simples": 0, "inox_dupla": 1, "esculpida": 2, "sem_cuba": 3}
                    self.cb_tipo_cuba.setCurrentIndex(cuba_map.get(cuba_val, 0))

                    pos_val = str(params.get("posicao_cuba", "centro")).lower()
                    pos_cuba_map = {"centro": 0, "esquerda": 1, "direita": 2}
                    self.cb_posicao_cuba.setCurrentIndex(pos_cuba_map.get(pos_val, 0))

                    self.chk_tem_torneira.setChecked(bool(params.get("tem_torneira", True)))

                    canto_val = str(params.get("canto_recorte", "arredondado")).lower()
                    if hasattr(self, "cb_canto_recorte"):
                        self.cb_canto_recorte.setCurrentIndex(1 if "reto" in canto_val else 0)
                    if hasattr(self, "chk_tem_area_molhada"):
                        self.chk_tem_area_molhada.setChecked(bool(params.get("tem_area_molhada", True)))
            else:
                # Restaura visibilidade para marcenaria tradicional
                show_rodape = has_rodape_suportado and not is_pedra and not is_cama and not is_peca_avulsa
                if hasattr(self, "lbl_rodape"):
                    self.lbl_rodape.setVisible(show_rodape)
                self.sp_rodape.setVisible(show_rodape)

                if hasattr(self, "lbl_materiais_header"):
                    self.lbl_materiais_header.setVisible(True)
                if hasattr(self, "lbl_material_caixa"):
                    self.lbl_material_caixa.setText("Caixa:")
                if hasattr(self, "lbl_espessura_caixa"):
                    self.lbl_espessura_caixa.setText("Esp. Caixa:")

                if hasattr(self, "lbl_fita_caixa"):
                    self.lbl_fita_caixa.setVisible(True)
                if hasattr(self, "cb_fita_caixa"):
                    self.cb_fita_caixa.setVisible(True)
                if hasattr(self, "lbl_material_fita_caixa"):
                    self.lbl_material_fita_caixa.setVisible(True)
                if hasattr(self, "cb_material_fita_caixa"):
                    self.cb_material_fita_caixa.setVisible(True)

                show_frentes_mat = tem_puxadores_reais or has_portas_suportadas or has_gavetas_suportadas
                if hasattr(self, "lbl_material_frentes"):
                    self.lbl_material_frentes.setVisible(show_frentes_mat)
                if hasattr(self, "cb_material_frentes"):
                    self.cb_material_frentes.setVisible(show_frentes_mat)
                if hasattr(self, "lbl_espessura_frentes"):
                    self.lbl_espessura_frentes.setVisible(show_frentes_mat)
                if hasattr(self, "cb_espessura_frentes"):
                    self.cb_espessura_frentes.setVisible(show_frentes_mat)

                if hasattr(self, "lbl_puxadores_header"):
                    self.lbl_puxadores_header.setVisible(tem_puxadores_reais)
                if hasattr(self, "lbl_puxador_tipo"):
                    self.lbl_puxador_tipo.setVisible(tem_puxadores_reais)
                self.cb_puxador_tipo.setVisible(tem_puxadores_reais)
                if hasattr(self, "lbl_puxador_cor"):
                    self.lbl_puxador_cor.setVisible(tem_puxadores_reais)
                self.cb_puxador_cor.setVisible(tem_puxadores_reais)
                if hasattr(self, "lbl_puxador_pos"):
                    self.lbl_puxador_pos.setVisible(tem_puxadores_reais)
                self.cb_puxador_pos.setVisible(tem_puxadores_reais)

                if hasattr(self, "lbl_estrutura_header"):
                    self.lbl_estrutura_header.setVisible(True)

                if hasattr(self, "lbl_prateleiras"):
                    self.lbl_prateleiras.setVisible(has_prat_suportadas)
                self.sp_prateleiras.setVisible(has_prat_suportadas)

                show_fundo = has_fundo_suportado and not is_cama and not is_peca_avulsa
                if hasattr(self, "_fundo_sidebar_widgets"):
                    for w in self._fundo_sidebar_widgets:
                        w.setVisible(show_fundo)

                show_furacao = not (is_peca_avulsa and tipo not in ("peca_divisoria_vertical",)) and (not is_cama or tipo == "cama_colmeia")
                if hasattr(self, "lbl_furacao"):
                    self.lbl_furacao.setVisible(show_furacao)
                if hasattr(self, "chk_gerar_furacao"):
                    self.chk_gerar_furacao.setVisible(show_furacao)
                if hasattr(self, "lbl_dispositivo_fixacao"):
                    self.lbl_dispositivo_fixacao.setVisible(show_furacao)
                if hasattr(self, "cb_dispositivo_fixacao"):
                    self.cb_dispositivo_fixacao.setVisible(show_furacao)

                show_disp_prat = show_furacao and has_prat_suportadas and not is_cama
                if hasattr(self, "lbl_dispositivo_prateleira"):
                    self.lbl_dispositivo_prateleira.setVisible(show_disp_prat)
                if hasattr(self, "cb_dispositivo_prateleira"):
                    self.cb_dispositivo_prateleira.setVisible(show_disp_prat)

                show_folga_frentes = not is_cama and (
                    tem_puxadores_reais or has_portas_suportadas or has_gavetas_suportadas
                )
                if hasattr(self, "lbl_folga_frentes"):
                    self.lbl_folga_frentes.setVisible(show_folga_frentes)
                if hasattr(self, "sp_folga_frentes"):
                    self.sp_folga_frentes.setVisible(show_folga_frentes)

                if tipo == "nicho":
                    if hasattr(self, "sec_frentes"):
                        self.sec_frentes.set_tab_visible(True)
                    if hasattr(self, "sec_puxadores"):
                        self.sec_puxadores.set_tab_visible(False)
                    if hasattr(self, "lbl_rodape"):
                        self.lbl_rodape.setVisible(False)
                    self.sp_rodape.setVisible(False)
                    if hasattr(self, "lbl_material_frentes"):
                        self.lbl_material_frentes.setVisible(False)
                    if hasattr(self, "cb_material_frentes"):
                        self.cb_material_frentes.setVisible(False)
                    if hasattr(self, "lbl_espessura_frentes"):
                        self.lbl_espessura_frentes.setVisible(False)
                    if hasattr(self, "cb_espessura_frentes"):
                        self.cb_espessura_frentes.setVisible(False)
                    if hasattr(self, "lbl_prateleiras"):
                        self.lbl_prateleiras.setVisible(True)
                    self.sp_prateleiras.setVisible(True)
                    self.sp_prateleiras.setValue(int(params.get("num_prateleiras", params.get("divisoes_horiz", 1))))
                    if hasattr(self, "lbl_divisoes"):
                        self.lbl_divisoes.setVisible(True)
                    self.sp_divisoes.setVisible(True)
                    self.sp_divisoes.setValue(int(params.get("num_divisoes", params.get("divisoes_vert", 0))))

            # ── Troca Dinâmica para Tampo Engrossado (peca_tampo_engrossado) ──
            is_tampo = (tipo in ("peca_tampo_engrossado", "tampo_engrossado"))
            if hasattr(self, "sec_frentes") and is_tampo:
                self.sec_frentes.set_tab_visible(False)
            if hasattr(self, "sec_puxadores") and is_tampo:
                self.sec_puxadores.set_tab_visible(False)
            if hasattr(self, "_tampo_sidebar_widgets"):
                for w in self._tampo_sidebar_widgets:
                    w.setVisible(is_tampo)

            if is_tampo:
                # Tampo Engrossado não possui rodapé, puxadores, portas/gavetas, prateleiras, fundo, furações
                if hasattr(self, "lbl_rodape"):
                    self.lbl_rodape.setVisible(False)
                self.sp_rodape.setVisible(False)

                if hasattr(self, "lbl_material_caixa"):
                    self.lbl_material_caixa.setText("Padrão MDF:")
                if hasattr(self, "lbl_espessura_caixa"):
                    self.lbl_espessura_caixa.setVisible(False)
                if hasattr(self, "cb_espessura"):
                    self.cb_espessura.setVisible(False)

                if hasattr(self, "lbl_fita_caixa"):
                    self.lbl_fita_caixa.setVisible(False)
                if hasattr(self, "cb_fita_caixa"):
                    self.cb_fita_caixa.setVisible(False)
                if hasattr(self, "lbl_material_fita_caixa"):
                    self.lbl_material_fita_caixa.setText("Fita de Borda:")

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
                self.cb_puxador_tipo.setVisible(False)
                if hasattr(self, "lbl_puxador_cor"):
                    self.lbl_puxador_cor.setVisible(False)
                self.cb_puxador_cor.setVisible(False)
                if hasattr(self, "lbl_puxador_pos"):
                    self.lbl_puxador_pos.setVisible(False)
                self.cb_puxador_pos.setVisible(False)
                if hasattr(self, "frame_perfil"):
                    self.frame_perfil.setVisible(False)

                if hasattr(self, "lbl_estrutura_header"):
                    self.lbl_estrutura_header.setVisible(False)
                if hasattr(self, "lbl_qtd_elem"):
                    self.lbl_qtd_elem.setVisible(False)
                self.sp_qtd_elem.setVisible(False)
                if hasattr(self, "lbl_largura_gaveteiro"):
                    self.lbl_largura_gaveteiro.setVisible(False)
                if hasattr(self, "sp_largura_gaveteiro"):
                    self.sp_largura_gaveteiro.setVisible(False)
                if hasattr(self, "lbl_prateleiras"):
                    self.lbl_prateleiras.setVisible(False)
                self.sp_prateleiras.setVisible(False)

                if hasattr(self, "_fundo_sidebar_widgets"):
                    for w in self._fundo_sidebar_widgets:
                        w.setVisible(False)
                if hasattr(self, "_travessa_sidebar_widgets"):
                    for w in self._travessa_sidebar_widgets:
                        w.setVisible(False)
                if hasattr(self, "_gaveta_sidebar_widgets"):
                    for w in self._gaveta_sidebar_widgets:
                        w.setVisible(False)

                if hasattr(self, "lbl_furacao"):
                    self.lbl_furacao.setVisible(False)
                if hasattr(self, "chk_gerar_furacao"):
                    self.chk_gerar_furacao.setVisible(False)
                if hasattr(self, "lbl_dispositivo_fixacao"):
                    self.lbl_dispositivo_fixacao.setVisible(False)
                if hasattr(self, "cb_dispositivo_fixacao"):
                    self.cb_dispositivo_fixacao.setVisible(False)
                if hasattr(self, "lbl_dispositivo_prateleira"):
                    self.lbl_dispositivo_prateleira.setVisible(False)
                if hasattr(self, "cb_dispositivo_prateleira"):
                    self.cb_dispositivo_prateleira.setVisible(False)
                if hasattr(self, "lbl_folga_frentes"):
                    self.lbl_folga_frentes.setVisible(False)
                if hasattr(self, "sp_folga_frentes"):
                    self.sp_folga_frentes.setVisible(False)

                # Carrega valores do tampo nos widgets da sidebar
                esp_ch = int(round(float(params.get("esp_chapa", 18.0))))
                idx_esp_ch = self.cb_tampo_esp_chapa.findText(f"{esp_ch} mm")
                self.cb_tampo_esp_chapa.setCurrentIndex(idx_esp_ch if idx_esp_ch >= 0 else 0)

                larg_eng = int(round(float(params.get("larg_engrosso", 70.0))))
                self.sp_tampo_larg_engrosso.setValue(larg_eng)

                qtd_eng = int(params.get("qtd_engrosso", 1))
                self.sp_tampo_qtd_engrosso.setValue(max(1, qtd_eng))

                self.chk_tampo_fechar_embaixo.setChecked(bool(params.get("fechar_embaixo", False)))

                snap_p = normalize_snap_parede(params.get("snap_parede", "auto"))
                idx_snap = next(
                    (i for i, (valor, _rotulo) in enumerate(SNAP_PAREDE_OPCOES) if valor == snap_p),
                    0,
                )
                self.cb_tampo_snap_parede.setCurrentIndex(idx_snap)

                tipo_eng = str(params.get("tipo_engrosso", "3_lados")).lower()
                tipo_eng_map = {"3_lados": 0, "4_lados": 1, "1_lado": 2, "apenas_frontal": 2}
                self.cb_tampo_tipo_engrosso.setCurrentIndex(tipo_eng_map.get(tipo_eng, 0))

            # ── Troca Dinâmica para Divisória Vertical (peca_divisoria_vertical) ──
            is_div_vert = (tipo in ("peca_divisoria_vertical", "divisoria_vertical"))
            if hasattr(self, "_divisoria_sidebar_widgets"):
                for w in self._divisoria_sidebar_widgets:
                    w.setVisible(is_div_vert)
            if is_div_vert and hasattr(self, "cb_cavilhas_divisoria"):
                c_cima = bool(params.get("cavilha_topo_superior", True))
                c_baixo = bool(params.get("cavilha_topo_inferior", True))
                if c_cima and c_baixo:
                    idx_div = 0
                elif c_cima and not c_baixo:
                    idx_div = 1
                elif not c_cima and c_baixo:
                    idx_div = 2
                else:
                    idx_div = 3
                self.cb_cavilhas_divisoria.setCurrentIndex(idx_div)

            # ── Troca Dinâmica para Prateleiras Avulsas (peca_prateleiras_avulsas) ──
            is_prat_avulsa = (tipo == "peca_prateleiras_avulsas")
            if hasattr(self, "_prat_avulsas_sidebar_widgets"):
                for w in self._prat_avulsas_sidebar_widgets:
                    w.setVisible(is_prat_avulsa)

            # ── Troca Dinâmica para Esquadrias (Portas & Janelas) ──
            is_esq = bool(
                getattr(mod, "ext", None) and isinstance(mod.ext, dict) and "trazomob_esquadria" in mod.ext
                or getattr(mod, "layer", "") == "ESQUADRIAS"
                or (
                    ("porta" in tipo.lower() or "janela" in tipo.lower())
                    and not tipo.lower().startswith("peca_")
                    and "porta_tempero" not in tipo.lower()
                )
            )

            # ── Oculta controles internos de caixaria quando for Conjunto de Portas de Correr Avulsas ──
            if tipo == "peca_portas_correr":
                if hasattr(self, "sec_frentes"):
                    self.sec_frentes.set_tab_visible(False)
                if hasattr(self, "lbl_rodape"):
                    self.lbl_rodape.setVisible(False)
                self.sp_rodape.setVisible(False)
                if hasattr(self, "lbl_prateleiras"):
                    self.lbl_prateleiras.setVisible(False)
                self.sp_prateleiras.setVisible(False)
                if hasattr(self, "lbl_divisoes"):
                    self.lbl_divisoes.setVisible(False)
                self.sp_divisoes.setVisible(False)
                if hasattr(self, "_fundo_sidebar_widgets"):
                    for w in self._fundo_sidebar_widgets:
                        w.setVisible(False)
                if hasattr(self, "lbl_furacao"):
                    self.lbl_furacao.setVisible(False)
                if hasattr(self, "chk_gerar_furacao"):
                    self.chk_gerar_furacao.setVisible(False)
                if hasattr(self, "lbl_dispositivo_fixacao"):
                    self.lbl_dispositivo_fixacao.setVisible(False)
                if hasattr(self, "cb_dispositivo_fixacao"):
                    self.cb_dispositivo_fixacao.setVisible(False)
                if hasattr(self, "lbl_dispositivo_prateleira"):
                    self.lbl_dispositivo_prateleira.setVisible(False)
                if hasattr(self, "cb_dispositivo_prateleira"):
                    self.cb_dispositivo_prateleira.setVisible(False)
                if hasattr(self, "lbl_folga_frentes"):
                    self.lbl_folga_frentes.setVisible(False)
                if hasattr(self, "sp_folga_frentes"):
                    self.sp_folga_frentes.setVisible(False)
            if hasattr(self, "_esquadria_pos_widgets"):
                for w in self._esquadria_pos_widgets:
                    w.setVisible(is_esq)
                is_esq_porta = is_esq and ("porta" in str(tipo).lower() or "porta" in getattr(mod, "name", "").lower())
                if hasattr(self, "_esquadria_porta_widgets"):
                    for w in self._esquadria_porta_widgets:
                        w.setVisible(is_esq_porta)
                    if is_esq_porta:
                        esq_meta = getattr(mod, "ext", {}).get("trazomob_esquadria") or params
                        lado_ab = str(esq_meta.get("lado_abertura", params.get("lado_abertura", "direita"))).lower()
                        sent_ab = str(esq_meta.get("sentido_abertura", params.get("sentido_abertura", "interno"))).lower()
                        self.cb_esq_lado_abertura.blockSignals(True)
                        self.cb_esq_lado_abertura.setCurrentIndex(1 if lado_ab.startswith(("esq", "left")) else 0)
                        self.cb_esq_lado_abertura.blockSignals(False)
                        self.cb_esq_sentido_abertura.blockSignals(True)
                        self.cb_esq_sentido_abertura.setCurrentIndex(1 if sent_ab.startswith(("ext", "for", "out")) else 0)
                        self.cb_esq_sentido_abertura.blockSignals(False)

                        if hasattr(self, "cb_esq_tamanho_rapido"):
                            is_piv = "pivotante" in str(tipo).lower()
                            cur_w = int(round(float(params.get("largura", 800.0))))
                            self.cb_esq_tamanho_rapido.blockSignals(True)
                            self.cb_esq_tamanho_rapido.clear()
                            if is_piv:
                                self.cb_esq_tamanho_rapido.addItems([
                                    "80 cm (800 mm)",
                                    "90 cm (900 mm)",
                                    "100 cm (1000 mm)",
                                    "📐 Personalizado",
                                ])
                                if cur_w == 800:
                                    self.cb_esq_tamanho_rapido.setCurrentIndex(0)
                                elif cur_w == 900:
                                    self.cb_esq_tamanho_rapido.setCurrentIndex(1)
                                elif cur_w == 1000:
                                    self.cb_esq_tamanho_rapido.setCurrentIndex(2)
                                else:
                                    self.cb_esq_tamanho_rapido.setCurrentIndex(3)
                            else:
                                self.cb_esq_tamanho_rapido.addItems([
                                    "70 cm (700 mm)",
                                    "80 cm (800 mm)",
                                    "90 cm (900 mm)",
                                    "📐 Personalizado",
                                ])
                                if cur_w == 700:
                                    self.cb_esq_tamanho_rapido.setCurrentIndex(0)
                                elif cur_w == 800:
                                    self.cb_esq_tamanho_rapido.setCurrentIndex(1)
                                elif cur_w == 900:
                                    self.cb_esq_tamanho_rapido.setCurrentIndex(2)
                                else:
                                    self.cb_esq_tamanho_rapido.setCurrentIndex(3)
                            self.cb_esq_tamanho_rapido.blockSignals(False)
                if is_esq:
                    # Esquadrias (Portas e Janelas): não usam os campos de portas/dobradiças de armário
                    if hasattr(self, "lbl_qtd_elem"):
                        self.lbl_qtd_elem.setVisible(False)
                    if hasattr(self, "sp_qtd_elem"):
                        self.sp_qtd_elem.setVisible(False)
                    if hasattr(self, "lbl_lado_porta_armario"):
                        self.lbl_lado_porta_armario.setVisible(False)
                    if hasattr(self, "cb_lado_porta_armario"):
                        self.cb_lado_porta_armario.setVisible(False)
                    is_janela_esq = "janela" in str(tipo).lower() or "janela" in str(getattr(mod, "name", "")).lower()
                    if hasattr(self, "lbl_elevacao"):
                        self.lbl_elevacao.setVisible(is_janela_esq)
                        if is_janela_esq:
                            self.lbl_elevacao.setText("Peitoril (Altura):")
                    if hasattr(self, "sp_elevacao"):
                        self.sp_elevacao.setVisible(is_janela_esq)
                        if is_janela_esq:
                            peit_mm = float(params.get("peitoril_mm", params.get("peitoril", 0.0)) or 0.0)
                            self.sp_elevacao.blockSignals(True)
                            self.sp_elevacao.setValue(max(0, int(round(peit_mm))))
                            self.sp_elevacao.blockSignals(False)

                    # Esconde seções irrelevantes de marcenaria interna para focar na esquadria
                    if hasattr(self, "sec_frentes"):
                        self.sec_frentes.set_tab_visible(False)
                    if hasattr(self, "sec_puxadores"):
                        self.sec_puxadores.set_tab_visible(False)
                    if hasattr(self, "sec_materiais"):
                        self.sec_materiais.set_tab_visible(False)
                    if hasattr(self, "sec_ajustes"):
                        self.sec_ajustes.set_tab_visible(False)
                    if hasattr(self, "tabs_module"):
                        self.tabs_module.setCurrentIndex(0)
                    if hasattr(self, "scroll_area") and self.scroll_area.verticalScrollBar() is not None:
                        self.scroll_area.verticalScrollBar().setValue(0)

                    # Obtém as cotas e distâncias reais até a parede
                    scene = self._get_scene()
                    w_info = self._get_esquadria_wall_info(mod, scene) if scene else None
                    if w_info:
                        self.sp_esq_dist_canto.blockSignals(True)
                        self.sp_esq_dist_canto.setRange(0, max(0, int(w_info["seg_len"] * 1000.0 - float(params.get("largura", 800.0)))))
                        self.sp_esq_dist_canto.setValue(int(w_info["dist_esq_mm"]))
                        self.sp_esq_dist_canto.blockSignals(False)
                        self.lbl_esq_dist_canto.setText(f"Distância Canto ({w_info['dist_esq_mm']}mm):")

            # Sincroniza o slider de abertura com o estado do módulo selecionado
            from ..interaction.interact import CabinetInteract
            st_open = CabinetInteract.capture_open_state(mod)
            pct_open = int(round(st_open.get("max_frac", 0.0) * 100)) if st_open.get("has_open", False) else 0
            if hasattr(self, "sl_open_dyn"):
                self.sl_open_dyn.blockSignals(True)
                self.sl_open_dyn.setValue(pct_open)
                self.sl_open_dyn.blockSignals(False)
            if hasattr(self, "lbl_open_pct"):
                self.lbl_open_pct.setText(f"{pct_open}%")
        finally:
            self._updating_ui = False
            self._update_badges()

