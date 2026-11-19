# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Aplicacao das alteracoes da barra lateral ao modulo selecionado."""
from __future__ import annotations

import os as _os
import time as _time
from contextlib import contextmanager

from PySide6.QtGui import QVector3D

from core.group import Group
from core.history import SnapshotImport

from ..builders.cabinet import CabinetBuilder
from ..domain.i18n import tr
from ..domain.param_mapper import extract_ui_module_params
from ..domain.schema import module_params
from ..domain.snap_contract import SNAP_PAREDE_OPCOES


@contextmanager
def _timed_apply(step: str):
    """Cronômetro opcional no mesmo log do INGETRAZO_PERF=1 do host."""
    if not _os.environ.get("INGETRAZO_PERF"):
        yield
        return
    t0 = _time.perf_counter()
    try:
        yield
    finally:
        from core.history import _plog
        _plog(f"trazomob.apply.{step}", (_time.perf_counter() - t0) * 1000.0, floor=0.0)


class SidebarApplyMixin:
    """Reconstrucao e aplicacao de modulos alterados na edicao."""

    def _apply_changes_to_selected(self, forced_tipo: str | None = None) -> None:
        """Aplica as alterações dimensionais e estéticas no módulo selecionado no 3D com Undo/Redo."""
        mod = self._active_selected_module()
        if mod is None:
            return

        viewport = self._get_viewport()
        scene = self._get_scene()
        if viewport is None or scene is None:
            return

        from ..interaction.interact import CabinetInteract
        open_state = CabinetInteract.capture_open_state(mod)

        old_params = module_params(mod)
        tipo = old_params.get("tipo", "balcao")
        with _timed_apply("extract_params"):
            new_params = extract_ui_module_params(self, base_params=old_params)
        if forced_tipo:
            new_params["tipo"] = str(forced_tipo)
            tipo = str(forced_tipo)

        from ..domain.catalog import MODULE_CATALOG
        _mod_cat = next(
            (m for cat in MODULE_CATALOG.values() for m in cat if m.get("id") == tipo),
            {}
        ) if tipo else {}

        has_portas_suportadas = bool(_mod_cat.get("has_portas", False))
        has_gavetas_suportadas = bool(_mod_cat.get("has_gavetas", False))
        has_prat_suportadas = bool(_mod_cat.get("has_prateleiras", False))
        has_fundo_suportado = bool(_mod_cat.get("has_fundo", True))
        has_rodape_suportado = bool(_mod_cat.get("has_rodape", False))
        is_cama = str(tipo).startswith("cama_") or tipo in ("bicama", "beliche")
        is_peca_avulsa = str(tipo).startswith("peca_") or tipo in ("rodape_fechado", "rodape_avulso")

        is_gaveteiro = (tipo == "gaveteiro")
        if is_gaveteiro:
            new_params["num_gavetas"] = int(self.sp_qtd_elem.value())
        elif tipo in ("cama_gaveteiros", "bicama"):
            qtd_g = int(self.sp_qtd_elem.value())
            new_params["num_gavetoes"] = qtd_g
            new_params["num_gavetas"] = qtd_g
        elif tipo == "balcao_misto":
            new_params["num_portas"] = int(self.sp_qtd_elem.value())
            new_params["num_gavetas"] = int(old_params.get("num_gavetas", 4))
            new_params["largura_gaveteiro"] = float(self.sp_largura_gaveteiro.value()) if hasattr(self, "sp_largura_gaveteiro") else float(old_params.get("largura_gaveteiro", 450.0))
            if hasattr(self, "cb_lado_gaveteiro"):
                new_params["lado_gaveteiro"] = ["esquerda", "direita", "ambos", "nenhum"][self.cb_lado_gaveteiro.currentIndex()] if 0 <= self.cb_lado_gaveteiro.currentIndex() < 4 else "esquerda"
            else:
                new_params["lado_gaveteiro"] = str(old_params.get("lado_gaveteiro", "esquerda"))
        elif tipo == "rack_nicho_gaveta":
            new_params["num_gavetas"] = int(self.sp_qtd_elem.value())
            new_params["largura_gaveteiro"] = float(self.sp_largura_gaveteiro.value()) if hasattr(self, "sp_largura_gaveteiro") else float(old_params.get("largura_gaveteiro", 600.0))
            if hasattr(self, "cb_lado_gaveteiro"):
                new_params["lado_gaveteiro"] = ["esquerda", "direita", "ambos", "nenhum"][self.cb_lado_gaveteiro.currentIndex()] if 0 <= self.cb_lado_gaveteiro.currentIndex() < 4 else "esquerda"
            else:
                new_params["lado_gaveteiro"] = str(old_params.get("lado_gaveteiro", "esquerda"))
        elif tipo == "balcao_canto_l":
            new_params["larg_asa_esq"] = float(self.sp_larg_asa_esq.value()) if hasattr(self, "sp_larg_asa_esq") else float(old_params.get("larg_asa_esq", old_params.get("larg_asa", 550.0)))
            new_params["larg_asa_dir"] = float(self.sp_larg_asa_dir.value()) if hasattr(self, "sp_larg_asa_dir") else float(old_params.get("larg_asa_dir", old_params.get("larg_asa", 550.0)))
            new_params["tem_batente_canto"] = bool(self.chk_batente_canto.isChecked()) if hasattr(self, "chk_batente_canto") else bool(old_params.get("tem_batente_canto", False))

        # IDs com portas estruturalmente fixas não devem ter num_portas sobrescrito pelo spinbox
        _FIXED_PORTAS_IDS = {"armario_2p_divisao", "armario_3p_divisao"}
        if tipo in _FIXED_PORTAS_IDS or _mod_cat.get("fixed_portas"):
            # Preserva o valor original fixo do catálogo/parâmetros
            pass
        elif has_portas_suportadas:
            new_params["num_portas"] = int(self.sp_qtd_elem.value())
        elif not is_cama and not is_peca_avulsa and tipo != "rack_nicho_gaveta" and "num_portas" in old_params:
            new_params["num_portas"] = int(self.sp_qtd_elem.value())

        if tipo in ("roupeiro_correr", "roupeiro_correr_2p", "roupeiro_correr_3p", "aereo_correr"):
            new_params["num_vaos"] = int(self.sp_qtd_elem.value())

        # Prateleiras internas
        if has_prat_suportadas:
            new_params["num_prateleiras"] = int(self.sp_prateleiras.value())
        elif "num_prateleiras" in new_params and not is_cama and not is_peca_avulsa:
            new_params.pop("num_prateleiras", None)

        # Divisórias verticais
        if tipo == "balcao":
            from ..domain.module_geometry import auto_divisoes_for_doors
            new_params["num_divisoes"] = auto_divisoes_for_doors(int(self.sp_qtd_elem.value()))
        elif tipo == "nicho":
            new_params["num_prateleiras"] = int(self.sp_prateleiras.value())
            new_params["divisoes_vert"] = int(self.sp_divisoes.value()) if hasattr(self, "sp_divisoes") else int(old_params.get("divisoes_vert", 0))
            new_params["divisoes_horiz"] = int(new_params["num_prateleiras"])
        elif hasattr(self, "sp_divisoes") and self.sp_divisoes.isVisible():
            new_params["num_divisoes"] = int(self.sp_divisoes.value())
        else:
            new_params.pop("num_divisoes", None)

        if hasattr(self, "cb_lado_porta_armario") and self.cb_lado_porta_armario.isVisible():
            if tipo == "balcao_canto":
                # Índice 0: Porta à Esquerda -> Lado Cego à Direita
                # Índice 1: Porta à Direita -> Lado Cego à Esquerda
                new_params["lado_cego"] = "esquerda" if self.cb_lado_porta_armario.currentIndex() == 1 else "direita"
                new_params["lado_abertura_porta"] = "direita" if self.cb_lado_porta_armario.currentIndex() == 1 else "esquerda"
            else:
                new_params["lado_abertura_porta"] = "direita" if self.cb_lado_porta_armario.currentIndex() == 1 else "esquerda"

        if not has_fundo_suportado:
            new_params["tem_fundo"] = False
            new_params["tipo_fundo"] = "sem_fundo"

        if not has_rodape_suportado:
            new_params["rodape"] = 0.0
        if tipo == "balcao_canto":
            if hasattr(self, "sp_largura_cego_canto"):
                new_params["largura_cego_mm"] = float(self.sp_largura_cego_canto.value())
            if hasattr(self, "chk_regua_fechamento_canto"):
                new_params["tem_regua_fechamento"] = bool(self.chk_regua_fechamento_canto.isChecked())
                new_params["larg_regua_fechamento_mm"] = float(self.sp_larg_regua_canto.value())
            if hasattr(self, "sp_dist_regua_canto"):
                new_params["dist_regua_fechamento_mm"] = float(self.sp_dist_regua_canto.value())
        if hasattr(self, "cb_esq_lado_abertura") and self.cb_esq_lado_abertura.isVisible():
            new_params["lado_abertura"] = "esquerda" if self.cb_esq_lado_abertura.currentIndex() == 1 else "direita"
        if hasattr(self, "cb_esq_sentido_abertura") and self.cb_esq_sentido_abertura.isVisible():
            new_params["sentido_abertura"] = "externo" if self.cb_esq_sentido_abertura.currentIndex() == 1 else "interno"

        # Parâmetros de travessas (apenas para módulos de cozinha inferiores)
        _IDS_COZINHA_INFERIORES = {
            "balcao", "gaveteiro", "balcao_misto", "balcao_pia",
            "balcao_canto", "balcao_canto_l", "porta_tempero", "balcao_forno"
        }
        if tipo in _IDS_COZINHA_INFERIORES and hasattr(self, "chk_travessa_frontal_em_pe"):
            tf_em_pe = self.chk_travessa_frontal_em_pe.isChecked()
            tt_em_pe = self.chk_travessa_traseira_em_pe.isChecked()
            new_params["travessa_frontal_em_pe"] = tf_em_pe
            new_params["travessa_traseira_em_pe"] = tt_em_pe
            new_params["larg_travessa_frontal_mm"] = float(self.sp_larg_travessa_frontal.value())
            new_params["larg_travessa_traseira_mm"] = float(self.sp_larg_travessa_traseira.value())
            new_params["recuo_porta_topo_mm"] = float(self.sp_recuo_porta_topo.value())
            # Compatibilidade legada
            new_params["larg_travessa_mm"] = float(self.sp_larg_travessa_frontal.value())
            new_params["recuo_porta_pia_mm"] = float(self.sp_recuo_porta_topo.value())

            # Material e espessura das travessas
            if hasattr(self, "cb_material_travessas"):
                mat_tr_txt = self.cb_material_travessas.currentText()
                esp_tr_txt = self.cb_espessura_travessas.currentText()
                esp_mm_caixa = float(new_params.get("espessura", 15.0))
                esp_tr_mm = esp_mm_caixa if esp_tr_txt.startswith("(") else float(esp_tr_txt.split()[0])
                if mat_tr_txt.startswith("("):
                    new_params["material_travessas"] = None
                else:
                    new_params["material_travessas"] = f"{mat_tr_txt} {int(esp_tr_mm)}mm"
                new_params["esp_travessas_mm"] = None if esp_tr_txt.startswith("(") else esp_tr_mm
                new_params["espessura_travessas"] = new_params["esp_travessas_mm"]

            # Fita de borda das travessas
            if hasattr(self, "cb_fita_travessas"):
                fita_modos = ["frontal_1L", "2L", "4L", "sem_fita"]
                f_idx = self.cb_fita_travessas.currentIndex()
                new_params["fita_travessas_modo"] = fita_modos[f_idx] if 0 <= f_idx < len(fita_modos) else "frontal_1L"

            if hasattr(self, "cb_material_fita_travessas"):
                mat_ftr_txt = self.cb_material_fita_travessas.currentText()
                new_params["material_fita_travessas"] = None if mat_ftr_txt.startswith("(") else mat_ftr_txt

        # Parâmetros de Forno (balcao_forno)
        if tipo == "balcao_forno":
            new_params["tem_gaveta"] = bool(self.chk_forno_tem_gaveta.isChecked())
            new_params["alt_gaveta_mm"] = float(self.sp_forno_alt_gaveta.value())

        # Parâmetros de Porta-Tempero (porta_tempero)
        if tipo == "porta_tempero" and hasattr(self, "cb_tipo_estrutura_tempero"):
            new_params["tipo_estrutura_tempero"] = "aramado" if self.cb_tipo_estrutura_tempero.currentIndex() == 1 else "mdf"
            new_params["cor_aramado"] = "preto" if self.cb_cor_aramado.currentIndex() == 1 else "cromado"

        # Parâmetros de Geladeira (caixa_geladeira)
        if tipo == "caixa_geladeira":
            new_params["alt_nicho_geladeira_mm"] = float(self.sp_geladeira_alt_nicho.value())
            is_basc = (self.cb_geladeira_tipo_porta.currentIndex() == 1)
            new_params["tipo_porta_superior"] = "basculante" if is_basc else "duas_portas"
            new_params["num_portas"] = 1 if is_basc else 2

        # Parâmetros de Aéreo Micro-ondas (aereo_microondas)
        if tipo == "aereo_microondas":
            is_basc_m = (self.cb_micro_tipo_porta.currentIndex() == 0)
            new_params["tipo_porta_superior"] = "basculante" if is_basc_m else "duas_portas"
            new_params["num_portas"] = 1 if is_basc_m else 2

        # Parâmetros de Caixa de Gaveta
        has_gav = ("num_gavetas" in new_params) or (tipo in ("gaveteiro", "balcao_misto", "torre_quente", "gabinete_banheiro")) or (tipo == "balcao_forno" and new_params.get("tem_gaveta", True))
        if has_gav and hasattr(self, "cb_tipo_fundo_gaveta"):
            new_params["tipo_fundo_gaveta"] = "por_baixo" if self.cb_tipo_fundo_gaveta.currentIndex() == 1 else "rasgo"
            new_params["folga_corredica_mm"] = float(self.sp_folga_corredica.value())

            mat_g_txt = self.cb_material_gaveta.currentText()
            esp_g_txt = self.cb_espessura_gaveta.currentText()
            esp_g_mm = float(esp_g_txt.split()[0])
            new_params["material_gaveta"] = None if mat_g_txt.startswith("(") else f"{mat_g_txt} {int(esp_g_mm)}mm"
            new_params["esp_gaveta_mm"] = esp_g_mm

            mat_fg_txt = self.cb_material_fita_gaveta.currentText()
            new_params["material_fita_gaveta"] = None if mat_fg_txt.startswith("(") else mat_fg_txt

            mat_fd_txt = self.cb_material_fundo_gaveta.currentText()
            esp_fd_txt = self.cb_esp_fundo_gaveta.currentText()
            esp_fd_mm = float(esp_fd_txt.split()[0])
            if mat_fd_txt.startswith("("):
                new_params["material_fundo_gaveta"] = f"MDF Fundo {int(esp_fd_mm)}mm" if esp_fd_mm <= 6.0 else f"MDF Branco TX {int(esp_fd_mm)}mm"
            else:
                new_params["material_fundo_gaveta"] = f"{mat_fd_txt} {int(esp_fd_mm)}mm"
            new_params["esp_fundo_gaveta_mm"] = esp_fd_mm

        # Parâmetros de Marmoraria / Bancada de Pedra
        if "bancada" in str(tipo):
            new_params["esp_pedra"] = float(self.sp_esp_pedra.value())
            new_params["altura_saia"] = float(self.sp_altura_saia.value())
            new_params["altura_frontao"] = float(self.sp_altura_frontao.value())
            new_params["tem_saia_esq"] = bool(self.chk_tem_saia_esq.isChecked())
            new_params["tem_saia_dir"] = bool(self.chk_tem_saia_dir.isChecked())
            if tipo in ("bancada_canto_l", "bancada_canto"):
                new_params["larg_asa_esq"] = float(self.sp_larg_asa_esq.value())
                new_params["larg_asa_dir"] = float(self.sp_larg_asa_dir.value())

            tem_cuba = bool(old_params.get("has_cuba", (tipo == "bancada_pia")))
            if tem_cuba:
                cuba_tipos = ["inox_simples", "inox_dupla", "esculpida", "sem_cuba"]
                idx_cb = self.cb_tipo_cuba.currentIndex()
                new_params["tipo_cuba"] = cuba_tipos[idx_cb] if 0 <= idx_cb < len(cuba_tipos) else "inox_simples"

                cuba_posicoes = ["centro", "esquerda", "direita"]
                idx_cp = self.cb_posicao_cuba.currentIndex()
                new_params["posicao_cuba"] = cuba_posicoes[idx_cp] if 0 <= idx_cp < len(cuba_posicoes) else "centro"

                new_params["tem_torneira"] = bool(self.chk_tem_torneira.isChecked())
                new_params["canto_recorte"] = "arredondado" if self.cb_canto_recorte.currentIndex() == 0 else "reto"
                new_params["raio_canto_mm"] = 20.0 if new_params["canto_recorte"] == "arredondado" else 0.0
                new_params["tem_area_molhada"] = bool(self.chk_tem_area_molhada.isChecked())
                new_params["has_cuba"] = (new_params["tipo_cuba"] != "sem_cuba")

        # Parâmetros de Tampo Engrossado (peca_tampo_engrossado)
        if tipo in ("peca_tampo_engrossado", "tampo_engrossado"):
            if hasattr(self, "cb_tampo_esp_chapa"):
                txt_esp_ch = self.cb_tampo_esp_chapa.currentText()
                new_params["esp_chapa"] = float(txt_esp_ch.split()[0])
            if hasattr(self, "sp_tampo_larg_engrosso"):
                new_params["larg_engrosso"] = float(self.sp_tampo_larg_engrosso.value())
            if hasattr(self, "sp_tampo_qtd_engrosso"):
                new_params["qtd_engrosso"] = int(self.sp_tampo_qtd_engrosso.value())
            if hasattr(self, "chk_tampo_fechar_embaixo"):
                new_params["fechar_embaixo"] = bool(self.chk_tampo_fechar_embaixo.isChecked())
            if hasattr(self, "cb_tampo_tipo_engrosso"):
                idx_te = self.cb_tampo_tipo_engrosso.currentIndex()
                tipo_eng_list = ["3_lados", "4_lados", "1_lado"]
                new_params["tipo_engrosso"] = tipo_eng_list[idx_te] if idx_te < len(tipo_eng_list) else "3_lados"
            if hasattr(self, "cb_tampo_snap_parede"):
                idx_snap = self.cb_tampo_snap_parede.currentIndex()
                new_params["snap_parede"] = (
                    SNAP_PAREDE_OPCOES[idx_snap][0]
                    if 0 <= idx_snap < len(SNAP_PAREDE_OPCOES)
                    else "auto"
                )

        # Parâmetros de Divisória Vertical (peca_divisoria_vertical)
        if tipo in ("peca_divisoria_vertical", "divisoria_vertical") and hasattr(self, "cb_cavilhas_divisoria"):
            idx_div = self.cb_cavilhas_divisoria.currentIndex()
            # 0: Ambos, 1: Apenas Cima, 2: Apenas Baixo, 3: Nenhum
            new_params["cavilha_topo_superior"] = (idx_div in (0, 1))
            new_params["cavilha_topo_inferior"] = (idx_div in (0, 2))

        # RotateGroupCommand (ferramenta Q) e RotateTrazoMobModuleCommand já mantêm
        # o parâmetro 'rot_z' e 'rot_matrix_3d' atualizados em old_params!
        rot_z_eff = float(new_params.get("rot_z", old_params.get("rot_z", 0.0)) or 0.0) % 360.0
        new_params["rot_z"] = rot_z_eff
        if "rot_matrix_3d" in old_params and isinstance(old_params["rot_matrix_3d"], (list, tuple)):
            new_params["rot_matrix_3d"] = list(old_params["rot_matrix_3d"])

        # Usa o offset salvo nos parâmetros (ponto de inserção original do módulo).
        offset = old_params.get("offset", (0.0, 0.0, 0.0))
        if not isinstance(offset, (list, tuple)) or len(offset) < 3:
            offset = (0.0, 0.0, 0.0)
        offset = tuple(float(v) for v in offset)

        from ..interaction.magnetic_drag import get_module_bounds
        from ..domain.module_geometry import (
            get_module_carcass_bounds,
            preserve_module_back_alignment,
            shift_module_geometry,
        )
        is_esq_mod = bool(
            (getattr(mod, "ext", None) and isinstance(mod.ext, dict) and ("trazomob_esquadria" in mod.ext or mod.ext.get("trazomob", {}).get("kind") == "esquadria"))
            or getattr(mod, "layer", "") == "ESQUADRIAS"
            or any(str(tipo).startswith(p) for p in ("porta_", "janela_"))
        )
        if is_esq_mod and "janela" in str(tipo).lower() and hasattr(self, "sp_elevacao") and self.sp_elevacao.isVisible():
            peit_ui_mm = float(self.sp_elevacao.value())
            new_params["peitoril_mm"] = peit_ui_mm
            new_params["peitoril"] = peit_ui_mm

        b_old = get_module_carcass_bounds(mod) or get_module_bounds(mod)

        # Reconstrói o módulo já com a rotação efetiva consolidada nos vértices (e xform = Identidade)
        with _timed_apply("build_module"):
            new_module_group = CabinetBuilder.build_module_group(new_params, offset=offset)
        b_new = get_module_carcass_bounds(new_module_group) or get_module_bounds(new_module_group)

        # ── PRESERVAÇÃO RIGOROSA DA POSIÇÃO E ROTAÇÃO ──────────────────
        has_3d_rot = isinstance(new_params.get("rot_matrix_3d"), (list, tuple)) and len(new_params["rot_matrix_3d"]) == 16
        if is_esq_mod:
            # Em esquadrias, o ponto de inserção (offset) já posiciona o marco perfeitamente no centro da parede!
            # Só deslocamos caso os bounds de mod tenham sido movidos manualmente em relação a new_module_group,
            # e mesmo assim usamos b_old / b_new do conjunto completo (e não apenas da fechadura/maçaneta).
            if b_old and b_new:
                cx_old = (b_old[0] + b_old[1]) * 0.5
                cy_old = (b_old[2] + b_old[3]) * 0.5
                cx_new = (b_new[0] + b_new[1]) * 0.5
                cy_new = (b_new[2] + b_new[3]) * 0.5
                shift = QVector3D(cx_old - cx_new, cy_old - cy_new, 0.0)
                if shift.length() > 1e-7:
                    targets = getattr(new_module_group, "children", []) or [new_module_group]
                    for t in targets:
                        m_sub = getattr(t, "mesh", None)
                        if m_sub and hasattr(m_sub, "vertices"):
                            for v in m_sub.vertices:
                                v.position += shift
                            m_sub._mut_serial = getattr(m_sub, "_mut_serial", 0) + 1
                        if getattr(t, "ext", None) is not None:
                            if "orig_vertices" in t.ext:
                                t.ext["orig_vertices"] = [orig + shift for orig in t.ext["orig_vertices"]]
                            if "hinge_pivot" in t.ext and isinstance(t.ext["hinge_pivot"], QVector3D):
                                t.ext["hinge_pivot"] += shift
                    new_off = (
                        float(offset[0]) + float(shift.x()),
                        float(offset[1]) + float(shift.y()),
                        float(offset[2]) + float(shift.z()),
                    )
                    for k_ext in ("trazomob_module", "trazomob_esquadria", "trazomob"):
                        if k_ext in new_module_group.ext and isinstance(new_module_group.ext[k_ext], dict):
                            new_module_group.ext[k_ext]["offset"] = new_off
        elif has_3d_rot or str(tipo).startswith("peca_"):
            if b_old and b_new:
                cx_old = (b_old[0] + b_old[1]) * 0.5
                cy_old = (b_old[2] + b_old[3]) * 0.5
                cz_old = (b_old[4] + b_old[5]) * 0.5
                cx_new = (b_new[0] + b_new[1]) * 0.5
                cy_new = (b_new[2] + b_new[3]) * 0.5
                cz_new = (b_new[4] + b_new[5]) * 0.5
                shift = QVector3D(cx_old - cx_new, cy_old - cy_new, cz_old - cz_new)
                if shift.length() > 1e-7:
                    targets = getattr(new_module_group, "children", []) or [new_module_group]
                    for t in targets:
                        m_sub = getattr(t, "mesh", None)
                        if m_sub and hasattr(m_sub, "vertices"):
                            for v in m_sub.vertices:
                                v.position += shift
                            m_sub._mut_serial = getattr(m_sub, "_mut_serial", 0) + 1
                        if getattr(t, "ext", None) is not None:
                            if "orig_vertices" in t.ext:
                                t.ext["orig_vertices"] = [orig + shift for orig in t.ext["orig_vertices"]]
                            if "hinge_pivot" in t.ext and isinstance(t.ext["hinge_pivot"], QVector3D):
                                t.ext["hinge_pivot"] += shift
        elif tipo in ("tampo_engrossado", "bancada_reta", "bancada_pia", "bancada_canto_l", "bancada_ilha", "bancada_tampao_engrossado"):
            if b_old and b_new:
                rot_norm = int(round(rot_z_eff / 90.0) * 90) % 360
                if rot_norm == 90:
                    dx = b_old[1] - b_new[1]
                    dy = b_old[2] - b_new[2]
                elif rot_norm == 180:
                    dx = b_old[1] - b_new[1]
                    dy = b_old[3] - b_new[3]
                elif rot_norm == 270:
                    dx = b_old[0] - b_new[0]
                    dy = b_old[3] - b_new[3]
                else:
                    dx = b_old[0] - b_new[0]
                    dy = b_old[2] - b_new[2]
                dz = b_old[5] - b_new[5]
                shift = QVector3D(dx, dy, dz)
                if shift.length() > 1e-7:
                    targets = getattr(new_module_group, "children", []) or [new_module_group]
                    for t in targets:
                        m_sub = getattr(t, "mesh", None)
                        if m_sub and hasattr(m_sub, "vertices"):
                            for v in m_sub.vertices:
                                v.position += shift
                            m_sub._mut_serial = getattr(m_sub, "_mut_serial", 0) + 1
        else:
            preserve_module_back_alignment(mod, new_module_group, rot_z_eff)

        is_peca_livre_pedra = (tipo == "bancada_tampao_engrossado")

        # Aplica deslocamento adicional de afastamento da parede (se especificado)
        if not is_esq_mod and not is_peca_livre_pedra and hasattr(self, "sp_afastamento_parede"):
            new_afast_m = float(self.sp_afastamento_parede.value()) / 1000.0
            old_params = (mod.ext.get("trazomob_module", {}) if getattr(mod, "ext", None) and isinstance(mod.ext, dict) else {}) or {}
            old_afast_m = float(old_params.get("afastamento_parede_mm", 0.0)) / 1000.0
            delta_afast = new_afast_m - old_afast_m
            if abs(delta_afast) > 1e-6:
                from ..domain.module_geometry import get_module_back_normal
                back_n = get_module_back_normal(rot_z_eff)
                # O vetor back aponta para trás (em direção à parede).
                # O afastamento afasta da parede, logo caminha no sentido -back_n.
                fwd_shift = -back_n * delta_afast
                shift_module_geometry(new_module_group, fwd_shift)

        if not is_esq_mod and not is_peca_livre_pedra and hasattr(self, "sp_elevacao"):
            target_z_m = float(self.sp_elevacao.value()) / 1000.0
            b_cur_elev = get_module_carcass_bounds(new_module_group) or get_module_bounds(new_module_group)
            if b_cur_elev is not None:
                dz_elev = target_z_m - float(b_cur_elev[4])
                if abs(dz_elev) > 1e-6:
                    shift_module_geometry(new_module_group, QVector3D(0.0, 0.0, dz_elev))

        if not is_esq_mod:
            b_final = get_module_carcass_bounds(new_module_group) or get_module_bounds(new_module_group)
            if b_final and "trazomob_module" in new_module_group.ext:
                mod_ext = new_module_group.ext["trazomob_module"]
                if not is_peca_livre_pedra and hasattr(self, "sp_elevacao"):
                    mod_ext["elevacao_mm"] = float(self.sp_elevacao.value())
                if not is_peca_livre_pedra and hasattr(self, "sp_afastamento_parede"):
                    mod_ext["afastamento_parede_mm"] = float(self.sp_afastamento_parede.value())
                cx_final = (b_final[0] + b_final[1]) * 0.5
                cy_final = (b_final[2] + b_final[3]) * 0.5
                cz_final = (b_final[4] + b_final[5]) * 0.5
                unrot_span = mod_ext.get("_unrot_carcass_span")
                if isinstance(unrot_span, (list, tuple)) and len(unrot_span) == 6:
                    mod_ext["offset"] = (
                        cx_final - float(unrot_span[0]),
                        cy_final - float(unrot_span[1]),
                        cz_final - float(unrot_span[2]),
                    )
                else:
                    L_m = float(new_params.get("largura", 800.0)) / 1000.0
                    P_m = float(new_params.get("profundidade", 550.0)) / 1000.0
                    mod_ext["offset"] = (
                        cx_final - L_m * 0.5,
                        cy_final - P_m * 0.5,
                        b_final[4],
                    )

        # Matriz xform do novo módulo permanece limpa (identidade),
        # pois a rotação 'rot_z' e a posição espacial já estão consolidadas na geometria dos vértices.

        # Restaura cinemática de abertura (portas e gavetas) no módulo recém-construído
        CabinetInteract.restore_open_state(new_module_group, open_state, scene=None, viewport=None)

        # Transação segura no Histórico
        old_mod = mod

        def apply_transaction(sc):
            target_layer = getattr(new_module_group, 'layer', None)
            if target_layer and hasattr(sc, 'layer') and hasattr(sc, 'layers'):
                if sc.layer(target_layer) is None:
                    from core.layers import Layer
                    sc.layers.append(Layer(target_layer))
            if old_mod in sc.groups:
                sc.groups.remove(old_mod)
            sc.groups.append(new_module_group)
            sc.selection = {new_module_group}
            if is_esq_mod:
                from ..wall.mesh_builder import WallMeshBuilder
                WallMeshBuilder.sync_scene_wall_openings(sc)

        with _timed_apply("history_execute"):
            if hasattr(viewport, "history") and viewport.history:
                viewport.history.execute(SnapshotImport(apply_transaction))
            else:
                apply_transaction(scene)

        self._selected_module = new_module_group
        # Sincroniza o slider e label de abertura com o estado real do módulo
        pct = int(round(open_state.get("max_frac", 0.0) * 100)) if open_state.get("has_open", False) else 0
        if hasattr(self, "sl_open_dyn"):
            self.sl_open_dyn.blockSignals(True)
            self.sl_open_dyn.setValue(pct)
            self.sl_open_dyn.blockSignals(False)
        if hasattr(self, "lbl_open_pct"):
            self.lbl_open_pct.setText(f"{pct}%")

        # Invalida só os chunks do módulo substituído; o resto da cena já é
        # revalidado em O(1) pelo viewport, sem rebake de VBOs alheios.
        with _timed_apply("invalidate_render_cache"):
            from ..builders.cabinet_transform import invalidate_replaced_modules_caches
            invalidate_replaced_modules_caches([(old_mod, new_module_group)], viewport)
        # A pintura em si é assíncrona; o custo do frame aparece na telemetria
        # do viewport (INGETRAZO_PERF=1), não aqui.
        viewport.update()

        self.lbl_status.setText(tr("✅ Atualizado: {name}", name=new_module_group.name))

    def _apply_changes_to_same_class(self) -> None:
        """Aplica as configurações estéticas e dimensionais comuns (materiais, puxadores, fitas, rodapé, profundidade)
        a todos os módulos da mesma classe/categoria existentes na cena (com Undo/Redo único)."""
        mod = self._active_selected_module()
        if mod is None:
            return

        viewport = self._get_viewport()
        scene = self._get_scene()
        if viewport is None or scene is None:
            return

        from ..domain.module_geometry import get_module_category
        from ..domain.schema import module_params
        from ..interaction.module_operations import batch_update_scene_modules

        old_params = module_params(mod)
        tipo_base = str(old_params.get("tipo", "balcao"))
        cat_base = get_module_category(tipo_base, default_z=float(old_params.get("offset", (0, 0, 0))[2]))

        # Extrai os parâmetros correntes do formulário da barra lateral
        ui_params = extract_ui_module_params(self, base_params=old_params)

        # Chaves de estilo e padronização que se propagam para módulos da mesma categoria
        common_keys = [
            "material", "material_frentes", "espessura", "espessura_frentes",
            "puxador_tipo", "puxador_cor", "puxador_pos", "perfil_modelo", "desconto_perfil",
            "fita_caixa_modo", "material_fita_caixa", "fita_gaveta_modo",
            "tipo_fundo", "esp_fundo", "recuo_fundo", "prof_rasgo", "folga_fundo",
            "folga_frentes_mm",
            "dispositivo_fixacao", "dispositivo_prateleira", "gerar_furacao",
        ]
        # Para módulos inferiores/aéreos (exceto camas/bancadas), propaga também rodapé e travessas
        if cat_base in ("inferior", "banheiro", "alto"):
            common_keys.extend([
                "rodape", "travessa_frontal_em_pe", "travessa_traseira_em_pe",
                "larg_travessa_frontal_mm", "larg_travessa_traseira_mm",
                "recuo_porta_topo_mm", "material_travessas", "esp_travessas_mm",
                "material_fita_travessas", "fita_travessas_modo",
            ])
        elif cat_base == "bancada":
            common_keys.extend([
                "esp_pedra", "altura_saia", "altura_frontao", "balanco_frontal_mm",
            ])

        def _filter(m: Group, p: dict) -> bool:
            t = str(p.get("tipo", getattr(m, "name", "")))
            z = float(p.get("offset", (0, 0, 0))[2]) if isinstance(p.get("offset"), (list, tuple)) else 0.0
            return get_module_category(t, default_z=z) == cat_base

        def _patch(m: Group, p: dict) -> dict:
            updated = dict(p)
            for k in common_keys:
                if k in ui_params:
                    updated[k] = ui_params[k]
            return updated

        count = batch_update_scene_modules(viewport, _filter, _patch)
        cat_names = {
            "inferior": "balcões inferiores",
            "aereo": "módulos aéreos",
            "alto": "torres e armários",
            "bancada": "bancadas de pedra",
            "banheiro": "gabinetes de banheiro",
        }
        nome_cat = cat_names.get(cat_base, f"módulos da categoria '{cat_base}'")
        if count > 0:
            msg = f"✨ {count} {nome_cat} atualizados com sucesso!"
            self.lbl_status.setText(msg)
            if hasattr(viewport, "flash_status"):
                viewport.flash_status(msg)
        else:
            self.lbl_status.setText("ℹ️ Nenhum outro módulo da mesma classe encontrado na cena.")


