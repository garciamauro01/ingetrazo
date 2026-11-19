# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Detecção de módulo e preenchimento/restauração do formulário."""

from __future__ import annotations

from PySide6.QtCore import Qt

from ..domain.i18n import tr
from ..ui.icons import make_perfil_diagram_pixmap
from ..domain.param_mapper import populate_ui_from_module
from ..domain.ui_contract import should_show_config_gaveteiro
from ..profiles import library as perfis_lib
from ..profiles.editor import PerfilLibraryDialog, fill_profile_combo


class ModuleDialogFormMixin:
    """Detecção de módulo e preenchimento/restauração do formulário."""

    def _detect_selected_module(self):
        """Detecta se há um módulo paramétrico selecionado no viewport para edição dinâmica."""
        sel = list(getattr(self.scene, "selection", []))
        # 1. Checa diretamente na seleção
        for item in sel:
            if hasattr(item, "ext") and isinstance(item.ext, dict):
                if "trazomob_module" in item.ext:
                    from ..domain.migration import migrate_legacy_group
                    migrate_legacy_group(item)
                    self._editing_module = item
                    return
        # 2. Se o usuário selecionou uma peça interna do armário, sobe para o módulo mestre
        for g in getattr(self.scene, "groups", []):
            if hasattr(g, "ext") and isinstance(g.ext, dict):
                if "trazomob_module" in g.ext:
                    children = getattr(g, "children", [])
                    if any(child in sel for child in children):
                        from ..domain.migration import migrate_legacy_group
                        migrate_legacy_group(g)
                        self._editing_module = g
                        return
        self._editing_module = None

    def _load_module_values_if_editing(self):
        """Se houver um módulo selecionado, carrega seus valores nos campos."""
        if self._editing_module is not None:
            from ..domain.schema import module_params
            params = module_params(self._editing_module)
            tipo = params.get("tipo", "balcao")

            # Seleciona o card do módulo correspondente no grid visual
            for i in range(self.list_modules.count()):
                it = self.list_modules.item(i)
                data = it.data(Qt.UserRole)
                if data and data.get("id") == tipo:
                    self.list_modules.setCurrentItem(it)
                    self._on_module_card_selected(it)
                    break

            # Popula campos comuns via mapper compartilhado (preserva largura/profundidade paramétricas independentemente de rot_z)
            populate_ui_from_module(self, params)

            # Restaura ferragens do módulo em edição (dobradiças, corrediças, trilhos etc.)
            if hasattr(self, "_restore_hardware_from_module"):
                self._restore_hardware_from_module(params)

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

            if hasattr(self, "cb_lado_porta_armario") and self.cb_lado_porta_armario.isVisible():
                if tipo == "balcao_canto":
                    lado_c = str(params.get("lado_cego", "esquerda")).lower()
                    self.cb_lado_porta_armario.setCurrentIndex(1 if lado_c.startswith("esq") else 0)
                else:
                    lado_p = str(params.get("lado_abertura_porta", "esquerda")).lower()
                    self.cb_lado_porta_armario.setCurrentIndex(1 if lado_p.startswith(("dir", "right")) else 0)

            is_canto_l_mod = tipo in ("balcao_canto_l", "bancada_canto_l", "bancada_canto")
            if hasattr(self, "lbl_larg_asa_esq"):
                self.lbl_larg_asa_esq.setVisible(is_canto_l_mod)
                self.sp_larg_asa_esq.setVisible(is_canto_l_mod)
                self.lbl_larg_asa_dir.setVisible(is_canto_l_mod)
                self.sp_larg_asa_dir.setVisible(is_canto_l_mod)
                if is_canto_l_mod:
                    if "larg_asa_esq" in params:
                        self.sp_larg_asa_esq.setValue(int(round(float(params["larg_asa_esq"]))))
                    elif "larg_asa" in params:  # fallback para compatibilidade
                        self.sp_larg_asa_esq.setValue(int(round(float(params["larg_asa"]))))
                    if "larg_asa_dir" in params:
                        self.sp_larg_asa_dir.setValue(int(round(float(params["larg_asa_dir"]))))
                    elif "larg_asa" in params:  # fallback para compatibilidade
                        self.sp_larg_asa_dir.setValue(int(round(float(params["larg_asa"]))))
                if hasattr(self, "lbl_batente_canto"):
                    is_batente_mod = (tipo == "balcao_canto_l")
                    self.lbl_batente_canto.setVisible(is_batente_mod)
                    self.chk_batente_canto.setVisible(is_batente_mod)
                    if is_batente_mod:
                        self.chk_batente_canto.setChecked(
                            bool(params.get("tem_batente_canto", False)))

            # Restaura configurações de travessas (se relevante)
            _IDS_COZINHA_INFERIORES = {
                "balcao", "gaveteiro", "balcao_misto", "balcao_pia",
                "balcao_canto", "balcao_canto_l", "porta_tempero", "balcao_forno"
            }
            if hasattr(self, "sp_larg_travessa_frontal") and tipo in _IDS_COZINHA_INFERIORES:
                em_pe = bool(params.get("travessa_frontal_em_pe", (tipo == "balcao_pia")))
                self.chk_travessa_em_pe.setChecked(em_pe)
                self.chk_travessa_traseira_em_pe.setChecked(bool(params.get("travessa_traseira_em_pe", False)))
                larg_f = params.get("larg_travessa_frontal_mm", params.get("larg_travessa_mm", 70.0))
                larg_t = params.get("larg_travessa_traseira_mm", 70.0)
                recuo_t = params.get("recuo_porta_topo_mm", params.get("recuo_porta_pia_mm", 50.0))
                self.sp_larg_travessa_frontal.setValue(int(round(float(larg_f))))
                self.sp_larg_travessa_traseira.setValue(int(round(float(larg_t))))
                self.sp_recuo_porta_pia.setValue(int(round(float(recuo_t))))
                self.lbl_recuo_porta_pia.setVisible(em_pe)
                self.sp_recuo_porta_pia.setVisible(em_pe)

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

            # Restaura configurações de Forno (se tipo balcao_forno)
            is_forno = (tipo == "balcao_forno")
            if hasattr(self, "_forno_widgets"):
                self.lbl_forno_section.setVisible(is_forno)
                self.lbl_forno_tem_gaveta.setVisible(is_forno)
                self.chk_forno_tem_gaveta.setVisible(is_forno)
                tem_gav_f = bool(params.get("tem_gaveta", True))
                if is_forno:
                    self.chk_forno_tem_gaveta.setChecked(tem_gav_f)
                    self.sp_forno_alt_gaveta.setValue(int(round(float(params.get("alt_gaveta_mm", 150.0)))))
                self.lbl_forno_alt_gaveta.setVisible(is_forno and tem_gav_f)
                self.sp_forno_alt_gaveta.setVisible(is_forno and tem_gav_f)

            # Restaura configurações de Caixa para Geladeira (caixa_geladeira)
            is_geladeira = (tipo == "caixa_geladeira")
            if hasattr(self, "_geladeira_widgets"):
                for w in self._geladeira_widgets:
                    w.setVisible(is_geladeira)
                if is_geladeira:
                    self.sp_geladeira_alt_nicho.setValue(int(round(float(params.get("alt_nicho_geladeira_mm", 1800.0)))))
                    is_b = (str(params.get("tipo_porta_superior", "")).lower() in ("basculante", "1_porta") or int(params.get("num_portas", 2)) == 1)
                    self.cb_geladeira_tipo_porta.setCurrentIndex(1 if is_b else 0)

            # Restaura configurações de Aéreo Micro-ondas (aereo_microondas)
            is_micro = (tipo == "aereo_microondas")
            if hasattr(self, "_micro_widgets"):
                for w in self._micro_widgets:
                    w.setVisible(is_micro)
                if is_micro:
                    is_b_micro = (str(params.get("tipo_porta_superior", "basculante")).lower() in ("basculante", "1_porta") or int(params.get("num_portas", 1)) == 1)
                    self.cb_micro_tipo_porta.setCurrentIndex(0 if is_b_micro else 1)


            # Restaura configurações de Caixa de Gaveta
            has_gav = ("num_gavetas" in params) or (tipo in ("gaveteiro", "balcao_misto", "torre_quente", "gabinete_banheiro")) or (is_forno and bool(params.get("tem_gaveta", True)))
            if hasattr(self, "_gaveta_widgets"):
                for w in self._gaveta_widgets:
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

            # Dispara atualizações contextuais de visibilidade/desconto
            if hasattr(self, "_on_tipo_fundo_changed"):
                self._on_tipo_fundo_changed()
            if hasattr(self, "_on_dialog_perfil_modelo_changed"):
                self._on_dialog_perfil_modelo_changed()
            if hasattr(self, "frame_perfil"):
                self.frame_perfil.setVisible(params.get("puxador_tipo") == "perfil")

            # Restaura valores de Marmoraria / Pedra se aplicável
            if "bancada" in str(tipo):
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

                tem_cuba = bool(params.get("has_cuba", (tipo == "bancada_pia")))
                self.lbl_tipo_cuba.setVisible(tem_cuba)
                self.cb_tipo_cuba.setVisible(tem_cuba)
                self.lbl_posicao_cuba.setVisible(tem_cuba)
                self.cb_posicao_cuba.setVisible(tem_cuba)
                self.lbl_tem_torneira.setVisible(tem_cuba)
                self.chk_tem_torneira.setVisible(tem_cuba)

                if tem_cuba:
                    cuba_val = str(params.get("tipo_cuba", "inox_simples")).lower()
                    cuba_map = {"inox_simples": 0, "inox_dupla": 1, "esculpida": 2, "sem_cuba": 3}
                    self.cb_tipo_cuba.setCurrentIndex(cuba_map.get(cuba_val, 0))

                    pos_val = str(params.get("posicao_cuba", "centro")).lower()
                    pos_cuba_map = {"centro": 0, "esquerda": 1, "direita": 2}
                    self.cb_posicao_cuba.setCurrentIndex(pos_cuba_map.get(pos_val, 0))

                    self.chk_tem_torneira.setChecked(bool(params.get("tem_torneira", True)))

                    canto_val = str(params.get("canto_recorte", "arredondado")).lower()
                    self.cb_canto_recorte.setCurrentIndex(1 if "reto" in canto_val else 0)
                    self.chk_tem_area_molhada.setChecked(bool(params.get("tem_area_molhada", True)))

                if hasattr(self, "lbl_canto_recorte"):
                    self.lbl_canto_recorte.setVisible(tem_cuba)
                    self.cb_canto_recorte.setVisible(tem_cuba)
                    self.lbl_tem_area_molhada.setVisible(tem_cuba)
                    self.chk_tem_area_molhada.setVisible(tem_cuba)

            if hasattr(self, "btn_duplicate"):
                self.btn_duplicate.setEnabled(True)
            if hasattr(self, "btn_delete"):
                self.btn_delete.setEnabled(True)
            self.lbl_dyn_status.setText(tr("🎯 Modo Dinâmico Ativo!\nEditando: {name}", name=self._editing_module.name))
            self.btn_insert.setText(tr("🔄 Atualizar Módulo Dinâmico"))
            self.btn_insert.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 12px 14px; font-size: 13px; border-radius: 6px;")
            self.btn_new_mode.setVisible(True)
        else:
            if hasattr(self, "btn_duplicate"):
                self.btn_duplicate.setEnabled(False)
            if hasattr(self, "btn_delete"):
                self.btn_delete.setEnabled(False)
            if self.list_modules.count() > 0:
                self.list_modules.setCurrentRow(0)
            self.lbl_dyn_status.setText("💡 Dica:\nSelecione um módulo no 3D para alterar suas medidas dinamicamente aqui.")
            self.btn_insert.setText("✨ Inserir Novo Módulo")
            self.btn_insert.setStyleSheet("background-color: #1976D2; color: white; font-weight: bold; padding: 12px 14px; font-size: 13px; border-radius: 6px;")
            self.btn_new_mode.setVisible(False)

    def _refresh_perfil_modelos(self, select_id: str | None = None) -> None:
        """Recarrega os modelos de perfil da biblioteca para o combobox."""
        if hasattr(self, "cb_perfil_modelo"):
            fill_profile_combo(self.cb_perfil_modelo, select_id=select_id)
            self._on_dialog_perfil_modelo_changed()

    def _on_dialog_perfil_modelo_changed(self) -> None:
        """Atualiza a prévia do diagrama e a indicação de desconto padrão."""
        if not hasattr(self, "cb_perfil_modelo"):
            return
        pid = self.cb_perfil_modelo.currentData() or "gola"
        p = perfis_lib.get_profile(pid)
        if hasattr(self, "lbl_perfil_diagram"):
            if pid in ("gola", "facetato", "canal_c", "sp7000"):
                self.lbl_perfil_diagram.setPixmap(make_perfil_diagram_pixmap(115, 80, modelo=pid))
            else:
                self.lbl_perfil_diagram.setPixmap(perfis_lib.render_profile_pixmap(p, 115, 80, cotas=True))

        desc = float(p.get("desconto_mm", 35.0))
        if hasattr(self, "cb_altura_perfil") and self.cb_altura_perfil.currentIndex() == 0:
            if hasattr(self, "sp_desconto_perfil"):
                self.sp_desconto_perfil.setValue(int(round(desc)))

    def _open_perfis_manager(self) -> None:
        """Abre o diálogo de gerenciamento/cadastro de perfis 2D com medidas e extrusão."""
        cur_id = self.cb_perfil_modelo.currentData() if hasattr(self, "cb_perfil_modelo") else "gola"
        dlg = PerfilLibraryDialog(parent=self, select_id=cur_id)
        if dlg.exec():
            selected = dlg.selected_id or cur_id
            self._refresh_perfil_modelos(select_id=selected)

    def _sync_desconto_perfil_from_combo(self, text: str) -> None:
        if "padrão" in text.lower():
            pid = self.cb_perfil_modelo.currentData() if hasattr(self, "cb_perfil_modelo") else "gola"
            val = int(round(float(perfis_lib.get_profile(pid).get("desconto_mm", 35.0))))
            self.sp_desconto_perfil.setValue(val)
        else:
            try:
                val = int(text.split()[0])
                self.sp_desconto_perfil.setValue(val)
            except (ValueError, IndexError):
                self.sp_desconto_perfil.setValue(35)

    def _reset_to_new_module(self):
        self._editing_module = None
        self._load_module_values_if_editing()
