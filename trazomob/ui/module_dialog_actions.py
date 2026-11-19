# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Inserção, atualização e ações 3D do diálogo TrazoMob."""

from __future__ import annotations

import logging
import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QVector3D
from PySide6.QtWidgets import QMessageBox

from core.history import SnapshotImport

from ..builders.cabinet import CabinetBuilder
from ..domain.i18n import tr
from ..domain.param_mapper import extract_ui_module_params
from ..domain.snap_contract import get_module_snap_parede
from ..interaction.interact import CabinetInteract, CabinetInteractTool

logger = logging.getLogger("trazomob.module_dialog")


class ModuleDialogActionsMixin:
    """Inserção, atualização e ações 3D do diálogo TrazoMob."""

    def _insert_or_update_module(self):
        """Insere um novo módulo ou atualiza dinamicamente o módulo selecionado no mesmo ponto."""
        current_item = self.list_modules.currentItem()
        if not current_item:
            return
        mod_data = current_item.data(Qt.UserRole)
        if not mod_data:
            return

        scene_groups = getattr(self.scene, "groups", None)
        if self._editing_module is not None and scene_groups is not None and self._editing_module not in scene_groups:
            self._editing_module = None

        tipo = mod_data.get("id", "balcao")
        params = extract_ui_module_params(self, base_params={"tipo": tipo})

        # Ferragens editadas na seção de ferragens (dobradiças, corrediças,
        # trilhos, puxadores etc.). Se o usuário não editou, o construtor infere
        # automaticamente a partir dos parâmetros.
        if hasattr(self, "_current_hardware_params"):
            _hw = self._current_hardware_params()
            if _hw:
                params["hardware"] = _hw
        if hasattr(self, "chk_hardware_3d"):
            params["hardware_3d_visible"] = bool(self.chk_hardware_3d.isChecked())

        # Orientação e Rotação
        if self._editing_module is None:
            rot_angles = [0.0, 90.0, 180.0, 270.0]
            rot_idx = self.cb_orientacao.currentIndex() if hasattr(self, "cb_orientacao") else 0
            params["rot_z"] = rot_angles[rot_idx]
        else:
            _old_mod_ref = self._editing_module
            _old_cc_params = _old_mod_ref.ext.get("trazomob_module", {})
            params["rot_z"] = float(_old_cc_params.get("rot_z", 0.0) or 0.0) % 360.0

        # O tampo engrossado nao tem seletor de snap no dialogo; preserva a
        # escolha existente ao editar e usa o padrao do catalogo ao inserir.
        if tipo in ("peca_tampo_engrossado", "tampo_engrossado"):
            params["snap_parede"] = (
                get_module_snap_parede(self._editing_module)
                if self._editing_module is not None
                else str(mod_data.get("snap_parede", "auto"))
            )

        if tipo == "balcao_misto":
            params["num_gavetas"] = self.sp_qtd_elem.value()
            params["num_portas"] = 2
            params["largura_gaveteiro"] = float(self.sp_largura_gaveteiro.value()) if hasattr(self, "sp_largura_gaveteiro") else float(mod_data.get("largura_gaveteiro", 450.0))
            if hasattr(self, "cb_lado_gaveteiro"):
                params["lado_gaveteiro"] = ["esquerda", "direita", "ambos", "nenhum"][self.cb_lado_gaveteiro.currentIndex()] if 0 <= self.cb_lado_gaveteiro.currentIndex() < 4 else "esquerda"
        elif tipo == "rack_nicho_gaveta":
            params["num_gavetas"] = self.sp_qtd_elem.value()
            params["largura_gaveteiro"] = float(self.sp_largura_gaveteiro.value()) if hasattr(self, "sp_largura_gaveteiro") else float(mod_data.get("largura_gaveteiro", 600.0))
            if hasattr(self, "cb_lado_gaveteiro"):
                params["lado_gaveteiro"] = ["esquerda", "direita", "ambos", "nenhum"][self.cb_lado_gaveteiro.currentIndex()] if 0 <= self.cb_lado_gaveteiro.currentIndex() < 4 else "esquerda"
        elif tipo == "balcao_canto_l":
            params["larg_asa_esq"] = float(self.sp_larg_asa_esq.value()) if hasattr(self, "sp_larg_asa_esq") else float(mod_data.get("larg_asa_esq", 550.0))
            params["larg_asa_dir"] = float(self.sp_larg_asa_dir.value()) if hasattr(self, "sp_larg_asa_dir") else float(mod_data.get("larg_asa_dir", 550.0))
            params["tem_batente_canto"] = bool(self.chk_batente_canto.isChecked()) if hasattr(self, "chk_batente_canto") else bool(mod_data.get("tem_batente_canto", False))
            params["num_portas"] = 2
        elif mod_data.get("fixed_portas"):
            # Portas fixas: não ler do spinbox — usar o valor definido no catálogo
            params["num_portas"] = int(mod_data.get("num_portas", 2))
            if mod_data.get("has_gavetas"):
                params["num_gavetas"] = self.sp_qtd_elem.value()
        elif mod_data.get("has_gavetas"):
            params["num_gavetas"] = self.sp_qtd_elem.value()
        elif tipo == "balcao":
            # Balcão com portas: num_portas do spinbox; divisórias automáticas
            params["num_portas"] = self.sp_qtd_elem.value()
            from ..domain.module_geometry import auto_divisoes_for_doors
            params["num_divisoes"] = auto_divisoes_for_doors(int(params["num_portas"]))
        elif mod_data.get("has_portas"):
            params["num_portas"] = self.sp_qtd_elem.value()
        if mod_data.get("has_prateleiras"):
            params["num_prateleiras"] = self.sp_prateleiras.value()
        if tipo == "nicho":
            params["divisoes_vert"] = self.sp_qtd_elem.value()
            params["divisoes_horiz"] = self.sp_prateleiras.value()
            params["num_divisoes"] = params["divisoes_vert"]
            params["num_prateleiras"] = params["divisoes_horiz"]

        if hasattr(self, "cb_lado_porta_armario") and self.cb_lado_porta_armario.isVisible():
            if tipo == "balcao_canto":
                params["lado_cego"] = "esquerda" if self.cb_lado_porta_armario.currentIndex() == 1 else "direita"
                params["lado_abertura_porta"] = "direita" if self.cb_lado_porta_armario.currentIndex() == 1 else "esquerda"
            else:
                params["lado_abertura_porta"] = "direita" if self.cb_lado_porta_armario.currentIndex() == 1 else "esquerda"

        # Grava parâmetros de travessas (Cozinha Inferiores)
        _IDS_COZINHA_INFERIORES = {
            "balcao", "gaveteiro", "balcao_misto", "balcao_pia",
            "balcao_canto", "balcao_canto_l", "porta_tempero", "balcao_forno"
        }
        if hasattr(self, "sp_larg_travessa_frontal") and tipo in _IDS_COZINHA_INFERIORES:
            params["travessa_frontal_em_pe"] = self.chk_travessa_em_pe.isChecked()
            params["travessa_traseira_em_pe"] = self.chk_travessa_traseira_em_pe.isChecked()
            params["larg_travessa_frontal_mm"] = float(self.sp_larg_travessa_frontal.value())
            params["larg_travessa_traseira_mm"] = float(self.sp_larg_travessa_traseira.value())
            params["recuo_porta_topo_mm"] = float(self.sp_recuo_porta_pia.value())
            # Compatibilidade legada para chaves antigas do balcao_pia
            params["larg_travessa_mm"] = float(self.sp_larg_travessa_frontal.value())
            params["recuo_porta_pia_mm"] = float(self.sp_recuo_porta_pia.value())

            # Material e espessura das travessas
            if hasattr(self, "cb_material_travessas"):
                mat_tr_txt = self.cb_material_travessas.currentText()
                esp_tr_txt = self.cb_espessura_travessas.currentText()
                esp_mm_caixa = float(params.get("espessura", 15.0))
                esp_tr_mm = esp_mm_caixa if esp_tr_txt.startswith("(") else float(esp_tr_txt.split()[0])
                if mat_tr_txt.startswith("("):
                    params["material_travessas"] = None
                else:
                    params["material_travessas"] = f"{mat_tr_txt} {int(esp_tr_mm)}mm"
                params["esp_travessas_mm"] = None if esp_tr_txt.startswith("(") else esp_tr_mm
                params["espessura_travessas"] = params["esp_travessas_mm"]

            # Fita de borda das travessas
            if hasattr(self, "cb_fita_travessas"):
                fita_modos = ["frontal_1L", "2L", "4L", "sem_fita"]
                f_idx = self.cb_fita_travessas.currentIndex()
                params["fita_travessas_modo"] = fita_modos[f_idx] if 0 <= f_idx < len(fita_modos) else "frontal_1L"

            if hasattr(self, "cb_material_fita_travessas"):
                mat_ftr_txt = self.cb_material_fita_travessas.currentText()
                params["material_fita_travessas"] = None if mat_ftr_txt.startswith("(") else mat_ftr_txt

        # Grava parâmetros de Forno (balcao_forno)
        if tipo == "balcao_forno":
            params["tem_gaveta"] = bool(self.chk_forno_tem_gaveta.isChecked())
            params["alt_gaveta_mm"] = float(self.sp_forno_alt_gaveta.value())

        # Grava parâmetros de Caixa para Geladeira (caixa_geladeira)
        if tipo == "caixa_geladeira":
            params["alt_nicho_geladeira_mm"] = float(self.sp_geladeira_alt_nicho.value())
            is_basc = (self.cb_geladeira_tipo_porta.currentIndex() == 1)
            params["tipo_porta_superior"] = "basculante" if is_basc else "duas_portas"
            params["num_portas"] = 1 if is_basc else 2

        # Grava parâmetros de Aéreo Micro-ondas (aereo_microondas)
        if tipo == "aereo_microondas":
            is_basc_m = (self.cb_micro_tipo_porta.currentIndex() == 0)
            params["tipo_porta_superior"] = "basculante" if is_basc_m else "duas_portas"
            params["num_portas"] = 1 if is_basc_m else 2


        # Grava parâmetros de Caixa de Gaveta
        has_gav = bool(mod_data.get("has_gavetas", False)) or (tipo in ("gaveteiro", "balcao_misto", "torre_quente", "gabinete_banheiro")) or (tipo == "balcao_forno" and params.get("tem_gaveta", True))
        if hasattr(self, "cb_tipo_fundo_gaveta") and has_gav:
            params["tipo_fundo_gaveta"] = "por_baixo" if self.cb_tipo_fundo_gaveta.currentIndex() == 1 else "rasgo"
            params["folga_corredica_mm"] = float(self.sp_folga_corredica.value())

            mat_g_txt = self.cb_material_gaveta.currentText()
            esp_g_txt = self.cb_espessura_gaveta.currentText()
            esp_g_mm = float(esp_g_txt.split()[0])
            params["material_gaveta"] = None if mat_g_txt.startswith("(") else f"{mat_g_txt} {int(esp_g_mm)}mm"
            params["esp_gaveta_mm"] = esp_g_mm

            mat_fg_txt = self.cb_material_fita_gaveta.currentText()
            params["material_fita_gaveta"] = None if mat_fg_txt.startswith("(") else mat_fg_txt

            mat_fd_txt = self.cb_material_fundo_gaveta.currentText()
            esp_fd_txt = self.cb_esp_fundo_gaveta.currentText()
            esp_fd_mm = float(esp_fd_txt.split()[0])
            if mat_fd_txt.startswith("("):
                params["material_fundo_gaveta"] = f"MDF Fundo {int(esp_fd_mm)}mm" if esp_fd_mm <= 6.0 else f"MDF Branco TX {int(esp_fd_mm)}mm"
            else:
                params["material_fundo_gaveta"] = f"{mat_fd_txt} {int(esp_fd_mm)}mm"
            params["esp_fundo_gaveta_mm"] = esp_fd_mm

        # Grava parâmetros de Marmoraria / Bancada de Pedra
        if "bancada" in str(tipo):
            params["esp_pedra"] = float(self.sp_esp_pedra.value())
            params["altura_saia"] = float(self.sp_altura_saia.value())
            params["altura_frontao"] = float(self.sp_altura_frontao.value())
            params["tem_saia_esq"] = bool(self.chk_tem_saia_esq.isChecked())
            params["tem_saia_dir"] = bool(self.chk_tem_saia_dir.isChecked())
            if tipo in ("bancada_canto_l", "bancada_canto"):
                params["larg_asa_esq"] = float(self.sp_larg_asa_esq.value())
                params["larg_asa_dir"] = float(self.sp_larg_asa_dir.value())

            tem_cuba = bool(mod_data.get("has_cuba", (tipo == "bancada_pia")))
            if tem_cuba:
                cuba_tipos = ["inox_simples", "inox_dupla", "esculpida", "sem_cuba"]
                idx_cb = self.cb_tipo_cuba.currentIndex()
                params["tipo_cuba"] = cuba_tipos[idx_cb] if 0 <= idx_cb < len(cuba_tipos) else "inox_simples"

                cuba_posicoes = ["centro", "esquerda", "direita"]
                idx_cp = self.cb_posicao_cuba.currentIndex()
                params["posicao_cuba"] = cuba_posicoes[idx_cp] if 0 <= idx_cp < len(cuba_posicoes) else "centro"

                params["tem_torneira"] = bool(self.chk_tem_torneira.isChecked())
                params["canto_recorte"] = "arredondado" if self.cb_canto_recorte.currentIndex() == 0 else "reto"
                params["raio_canto_mm"] = 20.0 if params["canto_recorte"] == "arredondado" else 0.0
                params["tem_area_molhada"] = bool(self.chk_tem_area_molhada.isChecked())
                params["has_cuba"] = (params["tipo_cuba"] != "sem_cuba")

        # ── Defaults seguros para posicionamento (evitam NameError em inserções novas) ──
        ref_mod = self._get_reference_module() if hasattr(self, "_get_reference_module") else None
        default_z = float(params.get("default_z", 0.0) or 0.0)
        gap_m = float(self.sp_align_gap.value()) / 1000.0 if hasattr(self, "sp_align_gap") else 0.0
        align_mode = int(self.cb_align_mode.currentIndex()) if hasattr(self, "cb_align_mode") else 0
        offset = (0.0, 0.0, 0.0)

        # Determina a posição de ancoragem com Alinhamento Inteligente TrazoMob
        if self._editing_module is not None:
            _edit_cc = self._editing_module.ext.get("trazomob_module", {})
            if "rot_matrix_3d" in _edit_cc and isinstance(_edit_cc["rot_matrix_3d"], (list, tuple)):
                params["rot_matrix_3d"] = list(_edit_cc["rot_matrix_3d"])
            # Usa o offset original salvo (âncora pré-rotação).
            _orig_off = _edit_cc.get("offset")
            if _orig_off is not None and len(_orig_off) == 3:
                offset = tuple(_orig_off)
            else:
                offset = self._get_module_position(self._editing_module)
        else:
            # ── HERANÇA DE MEDIDAS DA MESMA CATEGORIA ────────────────────────
            from ..domain.module_geometry import get_module_category, is_compatible_category
            cat_novo = get_module_category(tipo, default_z)
            ref_b = None
            ref_cc = {}
            if ref_mod is not None:
                ref_b = self._get_module_carcass_bounds(ref_mod)
                if hasattr(ref_mod, "ext") and "trazomob_module" in ref_mod.ext:
                    ref_cc = ref_mod.ext["trazomob_module"]

                ref_z = ref_b[4] if ref_b is not None else float(ref_cc.get("offset", (0, 0, 0))[2])
                ref_tipo = ref_cc.get("tipo", getattr(ref_mod, "name", ""))
                cat_ref = get_module_category(ref_tipo, ref_z)

                if is_compatible_category(cat_novo, cat_ref):
                    if "profundidade" in ref_cc and float(ref_cc["profundidade"]) > 0:
                        params["profundidade"] = float(ref_cc["profundidade"])
                    elif ref_b is not None:
                        ref_rot = float(ref_cc.get("rot_z", 0.0)) % 360.0
                        if abs(ref_rot) < 45.0 or abs(ref_rot - 180.0) < 45.0:
                            params["profundidade"] = round((ref_b[3] - ref_b[2]) * 1000.0)
                        else:
                            params["profundidade"] = round((ref_b[1] - ref_b[0]) * 1000.0)

                    if "altura" in ref_cc and float(ref_cc["altura"]) > 0:
                        params["altura"] = float(ref_cc["altura"])
                    elif ref_b is not None:
                        params["altura"] = round((ref_b[5] - ref_b[4]) * 1000.0)

                    if "rodape" in ref_cc and cat_novo in ("inferior", "alto"):
                        params["rodape"] = float(ref_cc["rodape"])
                    if ref_b is not None:
                        default_z = ref_b[4]

            novo_L_m = float(params.get("largura", 800.0)) / 1000.0

            # ── VERIFICAÇÃO DE PAREDE SELECIONADA (Prioridade Máxima) ───────────
            from ..wall.selection import WallSelectionManager
            wall_mgr = WallSelectionManager.get_instance(self.viewport)
            sel_wf = wall_mgr.selected_wall_face

            if sel_wf is not None and sel_wf.face is not None:
                # Encosta o módulo contra a face da parede selecionada
                norm = sel_wf.normal
                n_dir = QVector3D(norm.x(), norm.y(), 0.0)
                if n_dir.length() > 1e-4:
                    n_dir.normalize()
                    # Rotação para as costas ficarem na parede e frente apontada para dentro (+n_dir)
                    angle_deg = math.degrees(math.atan2(n_dir.y(), n_dir.x())) + 90.0
                    params["rot_z"] = (round(angle_deg / 90.0) * 90.0) % 360.0

                    c_pt = sel_wf.center
                    u_dir = QVector3D(-n_dir.y(), n_dir.x(), 0.0).normalized()

                    # Se já houver um móvel de referência na mesma parede/orientação,
                    # posiciona imediatamente ao lado dele ao longo da parede
                    positioned_next_to_ref = False
                    if ref_mod is not None and ref_b is not None:
                        ref_rot = float(ref_cc.get("rot_z", 0.0)) % 360.0
                        if abs(ref_rot - params["rot_z"]) < 1e-2 or abs(abs(ref_rot - params["rot_z"]) - 360.0) < 1e-2:
                            novo_P_m = float(params.get("profundidade", 550.0)) / 1000.0
                            half_diff = (novo_L_m - novo_P_m) * 0.5
                            if abs(ref_rot) < 1e-4:
                                offset = (ref_b[1] + gap_m, ref_b[2], default_z)
                            elif abs(ref_rot - 180.0) < 1e-4:
                                cand_x = ref_b[0] - novo_L_m - gap_m
                                if cand_x < 0.14:
                                    cand_x = ref_b[1] + gap_m
                                offset = (cand_x, ref_b[2], default_z)
                            elif abs(ref_rot - 90.0) < 1e-4:
                                cand_min_y = ref_b[3] + gap_m
                                offset = (ref_b[0] - half_diff, cand_min_y + half_diff, default_z)
                            elif abs(ref_rot - 270.0) < 1e-4:
                                cand_min_y = ref_b[2] - novo_L_m - gap_m
                                if cand_min_y < 0.14:
                                    cand_min_y = ref_b[3] + gap_m
                                offset = (ref_b[0] - half_diff, cand_min_y + half_diff, default_z)
                            else:
                                offset = (ref_b[1] + gap_m, ref_b[2], default_z)
                            positioned_next_to_ref = True

                    if not positioned_next_to_ref:
                        pos_base = c_pt + n_dir * 0.001 - u_dir * (novo_L_m * 0.5)
                        offset = (pos_base.x(), pos_base.y(), default_z)
                else:
                    offset = (sel_wf.center.x(), sel_wf.center.y(), default_z)
            elif ref_mod is not None and align_mode in (0, 1, 2):
                ref_rot_z = 0.0
                if hasattr(ref_mod, "ext") and "trazomob_module" in ref_mod.ext:
                    ref_rot_z = float(ref_mod.ext["trazomob_module"].get("rot_z", 0.0)) % 360.0

                if ref_b is None:
                    ref_b = self._get_module_carcass_bounds(ref_mod)
                if ref_b is not None:
                    novo_P_m = float(params.get("profundidade", 550.0)) / 1000.0
                    half_diff = (novo_L_m - novo_P_m) * 0.5

                    if abs(ref_rot_z) < 1e-4:
                        # Rotação 0° (padrão)
                        if align_mode == 0:    # ➡️ Ao lado (Direita)
                            offset = (ref_b[1] + gap_m, ref_b[2], ref_b[4])
                        elif align_mode == 1:  # ⬅️ Ao lado (Esquerda)
                            offset = (ref_b[0] - novo_L_m - gap_m, ref_b[2], ref_b[4])
                        elif align_mode == 2:  # ⬆️ Sobrepor (Acima)
                            offset = (ref_b[0], ref_b[2], ref_b[5] + gap_m)
                    elif abs(ref_rot_z - 180.0) < 1e-4:
                        # Rotação 180°: Direita do móvel aponta para -X, fundo aponta para -Y
                        if align_mode == 0:    # ➡️ Ao lado (Direita local do móvel)
                            offset = (ref_b[0] - novo_L_m - gap_m, ref_b[2], ref_b[4])
                        elif align_mode == 1:  # ⬅️ Ao lado (Esquerda local do móvel)
                            offset = (ref_b[1] + gap_m, ref_b[2], ref_b[4])
                        elif align_mode == 2:  # ⬆️ Sobrepor (Acima)
                            offset = (ref_b[0], ref_b[2], ref_b[5] + gap_m)
                    elif abs(ref_rot_z - 90.0) < 1e-4:
                        # Rotação 90°: Direita local aponta para +Y
                        if align_mode == 0:    # ➡️ Ao lado (Direita local do móvel)
                            offset = (ref_b[0] - half_diff, (ref_b[3] + gap_m) + half_diff, ref_b[4])
                        elif align_mode == 1:  # ⬅️ Ao lado (Esquerda local do móvel)
                            offset = (ref_b[0] - half_diff, (ref_b[2] - novo_L_m - gap_m) + half_diff, ref_b[4])
                        elif align_mode == 2:  # ⬆️ Sobrepor (Acima)
                            offset = (ref_b[0] - half_diff, ref_b[2] + half_diff, ref_b[5] + gap_m)
                    elif abs(ref_rot_z - 270.0) < 1e-4:
                        # Rotação 270°: Direita local aponta para -Y
                        if align_mode == 0:    # ➡️ Ao lado (Direita local do móvel)
                            offset = (ref_b[0] - half_diff, (ref_b[2] - novo_L_m - gap_m) + half_diff, ref_b[4])
                        elif align_mode == 1:  # ⬅️ Ao lado (Esquerda local do móvel)
                            offset = (ref_b[0] - half_diff, (ref_b[3] + gap_m) + half_diff, ref_b[4])
                        elif align_mode == 2:  # ⬆️ Sobrepor (Acima)
                            offset = (ref_b[0] - half_diff, ref_b[2] + half_diff, ref_b[5] + gap_m)
                    else:
                        offset = (ref_b[1] + gap_m, ref_b[2], ref_b[4])
                else:
                    offset = (0.0, 0.0, default_z)
            new_module_group = CabinetBuilder.build_module_group(params, offset=offset)
            # Se inserido em relação a uma parede selecionada, ajusta a posição exata da traseira do móvel na face
            if self._editing_module is None and sel_wf is not None and sel_wf.face is not None:
                norm = sel_wf.normal
                n_dir = QVector3D(norm.x(), norm.y(), 0.0)
                if n_dir.length() > 1e-4:
                    n_dir.normalize()
                    from ..interaction.magnetic_drag import get_module_bounds, get_bounds_min_projection
                    from ..domain.module_geometry import get_module_carcass_bounds
                    b = get_module_carcass_bounds(new_module_group) or get_module_bounds(new_module_group)
                    if b is not None:
                        cur_min_n = get_bounds_min_projection(b, n_dir)
                        wall_face_n = QVector3D.dotProduct(sel_wf.center, n_dir)
                        delta_n = (wall_face_n - cur_min_n) + 0.001
                        if abs(delta_n) > 1e-4:
                            shift = n_dir * delta_n
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
                            if "trazomob_module" in new_module_group.ext:
                                mod_ext = new_module_group.ext["trazomob_module"]
                                old_off = mod_ext.get("offset", (0.0, 0.0, 0.0))
                                mod_ext["offset"] = (
                                    float(old_off[0]) + float(shift.x()),
                                    float(old_off[1]) + float(shift.y()),
                                    float(old_off[2]) + float(shift.z()),
                                )

            # Ao editar módulo existente, preserva o alinhamento espacial e rotação
            if self._editing_module is not None:
                rot_z_eff = float(params.get("rot_z", 0.0))
                from ..interaction.magnetic_drag import get_module_bounds
                from ..domain.module_geometry import get_module_carcass_bounds, preserve_module_back_alignment
                b_old = get_module_carcass_bounds(self._editing_module) or get_module_bounds(self._editing_module)
                b_new = get_module_carcass_bounds(new_module_group) or get_module_bounds(new_module_group)
                has_3d_rot = isinstance(params.get("rot_matrix_3d"), (list, tuple)) and len(params["rot_matrix_3d"]) == 16
                if has_3d_rot or str(tipo).startswith("peca_"):
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
                elif tipo in ("tampo_engrossado", "bancada_reta", "bancada_pia", "bancada_canto_l", "bancada_ilha"):
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
                    preserve_module_back_alignment(self._editing_module, new_module_group, rot_z_eff)

                b_final = get_module_carcass_bounds(new_module_group) or get_module_bounds(new_module_group)
                if b_final and "trazomob_module" in new_module_group.ext:
                    mod_ext = new_module_group.ext["trazomob_module"]
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
                        L_m = float(params.get("largura", 800.0)) / 1000.0
                        P_m = float(params.get("profundidade", 550.0)) / 1000.0
                        mod_ext["offset"] = (
                            cx_final - L_m * 0.5,
                            cy_final - P_m * 0.5,
                            b_final[4],
                        )

            # Transação no histórico (Undo/Redo)
            old_mod = self._editing_module

            def apply_transaction(scene):
                target_layer = getattr(new_module_group, 'layer', None)
                if target_layer and hasattr(scene, 'layer') and hasattr(scene, 'layers'):
                    if scene.layer(target_layer) is None:
                        from core.layers import Layer
                        scene.layers.append(Layer(target_layer))
                if old_mod is not None and old_mod in scene.groups:
                    scene.groups.remove(old_mod)
                scene.groups.append(new_module_group)
                scene.selection = {new_module_group}

            self.viewport.history.execute(SnapshotImport(apply_transaction))
            self.viewport.notify_scene_changed()
        # Enquadra e centraliza a câmera na peça inserida no Viewport
        try:
            lo, hi = self.scene.selection_bounds()
            if lo is not None and hi is not None and hasattr(self.viewport, "camera"):
                self.viewport.camera.fit_box(lo, hi)
        except Exception as e:
            logger.debug("Aviso ao enquadrar peça no viewport: %s", e)

        self.viewport.update()

        # Atualiza a referência de último módulo inserido (usado para alinhamento automático do próximo)
        self._last_inserted_module = new_module_group
        was_editing = (old_mod is not None)
        if was_editing:
            self._editing_module = new_module_group
            self._load_module_values_if_editing()
        else:
            # Era inserção de um novo móvel: mantém o diálogo pronto para inserir novos móveis!
            self._editing_module = None
            self._update_align_reference_label()

        # Atualiza tabela de corte
        self._reload_parts()
        if hasattr(self, "lbl_dyn_status"):
            acao_txt = tr("atualizado") if was_editing else tr("inserido")
            self.lbl_dyn_status.setText(tr("✅ Módulo '{name}' {action} com sucesso!",
                                           name=new_module_group.name, action=acao_txt))

    def _toggle_doors_and_drawers(self):
        """Abre ou fecha portas e gavetas do móvel selecionado no 3D."""
        target = self._editing_module or self._get_reference_module()
        if not target:
            QMessageBox.information(self, "Interação", "Selecione ou insira um móvel no 3D para abrir ou fechar suas portas e gavetas.")
            return
        CabinetInteract.toggle_all(target, self.scene, self.viewport)

    def _on_dialog_open_slider_changed(self, value: int):
        pct = int(value)
        self.lbl_dlg_open_val.setText(f"{pct}%")
        frac = pct / 100.0
        target = self._editing_module or self._get_reference_module()
        if target is not None:
            CabinetInteract.set_module_open_fraction(target, frac, self.scene, self.viewport)
        else:
            CabinetInteract.set_scene_open_fraction(self.scene, frac, self.viewport)

    def _test_module_collisions(self):
        """Testa se há colisões visuais com portas ou gavetas abertas."""
        from ..interaction.collision import check_opening_collisions
        colisoes = check_opening_collisions(self.scene)
        if colisoes:
            msg = "⚠️ <b>Colisões Detectadas na Abertura:</b><br><br>"
            for c in colisoes[:5]:
                msg += f"• {c['desc']}<br>"
            if len(colisoes) > 5:
                msg += f"<br><i>(+ {len(colisoes) - 5} outras colisões encontradas)</i>"
            QMessageBox.warning(self, "Teste de Colisão de Abertura", msg)
        else:
            QMessageBox.information(
                self,
                "Teste de Colisão de Abertura",
                "✅ <b>Nenhuma colisão detectada!</b><br><br>"
                "Todas as portas e gavetas têm espaço livre para abertura completa sem encostar em puxadores ou cantos."
            )

    def _activate_interact_tool(self):
        """Ativa a ferramenta interativa de clique no 3D e fecha o diálogo."""
        self.close()
        win = self.viewport.window() if hasattr(self.viewport, "window") else None
        key = "plugin_trazomob_CabinetInteractTool"
        if win is not None and hasattr(win, "_activate_plugin_tool") and key in getattr(win, "_tools", {}):
            win._activate_plugin_tool(key)
        elif hasattr(self.viewport, "set_active_tool"):
            self.viewport.set_active_tool(CabinetInteractTool())
