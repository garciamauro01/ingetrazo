# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Mixin para o painel lateral do TrazoMob especializado em cinemática 3D interativa e operações em lote."""
from __future__ import annotations

from typing import Any
from ..interaction.interact import CabinetInteract, CabinetInteractTool
from ..domain.i18n import tr
from ..domain.param_mapper import extract_ui_module_params
from ..interaction.module_operations import batch_update_scene_modules


class SidebarInteractBatchMixin:
    """Encapsula a cinemática de abertura (portas/gavetas), detecção de colisão e propagação em lote."""

    def _on_dynamic_slider_changed(self, value: int) -> None:
        """Atualiza a cinemática de abertura em tempo real de acordo com o slider."""
        pct = int(value)
        self.lbl_open_pct.setText(f"{pct}%")
        frac = pct / 100.0
        scene = self._get_scene()
        viewport = self._get_viewport()
        if scene is None:
            return

        # Se houver um módulo selecionado, abre prioritariamente ele; caso contrário, abre toda a cena
        mod = self._active_selected_module()
        if mod is not None:
            CabinetInteract.set_module_open_fraction(mod, frac, scene, viewport)
        else:
            CabinetInteract.set_scene_open_fraction(scene, frac, viewport)

        # Se ultrapassar 40% de abertura, executa checagem de colisão sutil
        if pct >= 40:
            self._check_dynamic_collisions(silent=True)
        else:
            if hasattr(self, "lbl_collision_warn"):
                self.lbl_collision_warn.setVisible(False)

    def _check_dynamic_collisions(self, silent: bool = False) -> None:
        """Verifica colisões entre portas/gavetas abertas e objetos adjacentes."""
        scene = self._get_scene()
        if scene is None:
            return
        from ..interaction.collision import check_opening_collisions
        colisoes = check_opening_collisions(scene)

        if hasattr(self, "lbl_collision_warn"):
            if colisoes:
                primeira = colisoes[0]["desc"]
                qtd = len(colisoes)
                mais_txt = f" (+{qtd - 1} outros contatos)" if qtd > 1 else ""
                self.lbl_collision_warn.setText(f"{primeira}{mais_txt}")
                self.lbl_collision_warn.setVisible(True)
            else:
                if not silent:
                    self.lbl_collision_warn.setText("✅ Nenhuma colisão detectada! Abertura livre.")
                    self.lbl_collision_warn.setStyleSheet(
                        "background-color: #ecfdf5; color: #047857; font-size: 10px; font-weight: bold; "
                        "padding: 4px; border: 1px solid #a7f3d0; border-radius: 3px;"
                    )
                    self.lbl_collision_warn.setVisible(True)
                else:
                    self.lbl_collision_warn.setVisible(False)

    def _activate_interact_tool(self) -> None:
        """Ativa a ferramenta interativa de clique individual no 3D."""
        from ..integrations import platform as host
        win = self._get_window()
        viewport = self._get_viewport()
        key = "plugin_trazomob_CabinetInteractTool"
        host.activate_plugin_tool(win, viewport, key, CabinetInteractTool)

    def _toggle_interact(self) -> None:
        mod = self._active_selected_module()
        viewport = self._get_viewport()
        scene = self._get_scene()
        if mod is None or viewport is None or scene is None:
            return
        CabinetInteract.toggle_all(mod, scene, viewport)

    def _on_apply_puxadores_to_all_modules(self) -> None:
        """Aplica o modelo, cor e posição de puxador selecionados a todos os armários da cena."""
        viewport = self._get_viewport()
        pux_params = extract_ui_module_params(self)
        pux_tipo = pux_params.get("puxador_tipo", "alca")
        pux_cor = pux_params.get("puxador_cor", "preto")
        pux_pos = pux_params.get("puxador_pos", "padrao")
        perfil_mod = pux_params.get("perfil_modelo", "gola")
        desc_perfil = pux_params.get("desconto_perfil", 35.0)

        def _filter(mod, params):
            tipo = str(params.get("tipo", "")).lower()
            return not any(k in tipo for k in ("bancada", "tampo_engrossado", "peca_"))

        def _patch(mod, params):
            params["puxador_tipo"] = pux_tipo
            params["puxador_cor"] = pux_cor
            params["puxador_pos"] = pux_pos
            params["perfil_modelo"] = perfil_mod
            params["desconto_perfil"] = desc_perfil
            return params

        count = batch_update_scene_modules(viewport, _filter, _patch)
        if count > 0:
            pux_label = self.cb_puxador_tipo.currentText()
            self.lbl_status.setText(tr("✨ Puxadores aplicados a {count} armários ({pux_label})!",
                                       count=count, pux_label=pux_label))
        else:
            self.lbl_status.setText("ℹ️ Nenhum armário com portas/gavetas encontrado.")

    def _on_apply_frentes_to_all_modules(self) -> None:
        """Troca o material e cor das frentes (portas e gavetas) de todos os módulos da cena."""
        viewport = self._get_viewport()
        mat_frente_txt = self.cb_material_frentes.currentText()
        esp_frente_txt = self.cb_espessura_frentes.currentText()

        def _filter(mod, params):
            tipo = str(params.get("tipo", "")).lower()
            return not any(k in tipo for k in ("bancada", "tampo_engrossado", "peca_"))

        def _patch(mod, params):
            params["material_frentes"] = mat_frente_txt
            if esp_frente_txt and esp_frente_txt.split()[0].isdigit():
                params["espessura_frentes"] = float(esp_frente_txt.split()[0])
            return params

        count = batch_update_scene_modules(viewport, _filter, _patch)
        if count > 0:
            self.lbl_status.setText(tr("🎨 Padrão de frentes atualizado em {count} armário(s) ({mat})!",
                                       count=count, mat=mat_frente_txt))
        else:
            self.lbl_status.setText("ℹ️ Nenhum armário com portas/gavetas encontrado.")

    def _on_apply_caixa_to_all_modules(self) -> None:
        """Troca o material e cor da caixaria de todos os módulos da cena."""
        viewport = self._get_viewport()
        mat_caixa_txt = self.cb_material.currentText()
        esp_caixa_txt = self.cb_espessura.currentText()
        esp_caixa_val = float(esp_caixa_txt.split()[0]) if esp_caixa_txt and esp_caixa_txt.split()[0].isdigit() else 15.0

        def _filter(mod, params):
            tipo = str(params.get("tipo", "")).lower()
            return not any(k in tipo for k in ("bancada", "tampo_engrossado", "peca_"))

        def _patch(mod, params):
            import re
            mat_clean = re.sub(r"\s+\d+\s*mm$", "", mat_caixa_txt).strip()
            params["material"] = f"{mat_clean} {int(esp_caixa_val)}mm"
            params["espessura"] = esp_caixa_val
            return params

        count = batch_update_scene_modules(viewport, _filter, _patch)
        if count > 0:
            self.lbl_status.setText(tr("🪵 Padrão de caixaria atualizado em {count} armário(s) ({mat})!",
                                       count=count, mat=mat_caixa_txt))
        else:
            self.lbl_status.setText("ℹ️ Nenhum armário elegível encontrado.")

    def _on_apply_travessas_to_all_modules(self) -> None:
        """Aplica a orientação (em pé/deitada), larguras e materiais de travessa a todos os balcões da cena."""
        viewport = self._get_viewport()
        curr_params = extract_ui_module_params(self)
        _IDS_COZINHA_INFERIORES = {
            "balcao", "gaveteiro", "balcao_misto", "balcao_pia",
            "balcao_canto", "balcao_canto_l", "porta_tempero", "balcao_forno"
        }

        def _filter(mod, params):
            tipo = str(params.get("tipo", "")).lower()
            return tipo in _IDS_COZINHA_INFERIORES

        def _patch(mod, params):
            params["travessa_frontal_em_pe"] = bool(curr_params.get("travessa_frontal_em_pe", False))
            params["travessa_traseira_em_pe"] = bool(curr_params.get("travessa_traseira_em_pe", False))
            params["larg_travessa_frontal_mm"] = float(curr_params.get("larg_travessa_frontal_mm", 70.0))
            params["larg_travessa_traseira_mm"] = float(curr_params.get("larg_travessa_traseira_mm", 70.0))
            params["recuo_porta_topo_mm"] = float(curr_params.get("recuo_porta_topo_mm", 50.0))
            params["material_travessas"] = curr_params.get("material_travessas")
            params["esp_travessas_mm"] = curr_params.get("esp_travessas_mm")
            params["espessura_travessas"] = params["esp_travessas_mm"]
            params["fita_travessas_modo"] = curr_params.get("fita_travessas_modo", "frontal_1L")
            params["material_fita_travessas"] = curr_params.get("material_fita_travessas")
            return params

        count = batch_update_scene_modules(viewport, _filter, _patch)
        if count > 0:
            orient = "em pé" if curr_params.get("travessa_frontal_em_pe") else "deitadas"
            self.lbl_status.setText(tr("🔧 Travessas atualizadas ({orient}) em {count} balcão(ões)!",
                                       orient=orient, count=count))
        else:
            self.lbl_status.setText("ℹ️ Nenhum balcão inferior de cozinha encontrado na cena.")

