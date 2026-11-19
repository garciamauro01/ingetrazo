# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Selecao de cena e ativacao da edicao na barra lateral."""
from __future__ import annotations

from core.group import Group

from ..domain.schema import module_params


class SidebarSceneMixin:
    """Operacoes dependentes da selecao atual da cena e ativacao do editor."""

    def _set_editor_enabled(self, enabled: bool) -> None:
        if enabled:
            self._ensure_form_built()
        if hasattr(self, "form_container"):
            self.form_container.setEnabled(enabled)
        if hasattr(self, "btn_apply"):
            self.btn_apply.setEnabled(enabled)
        if hasattr(self, "btn_apply_same_class"):
            self.btn_apply_same_class.setEnabled(enabled)
        if hasattr(self, "btn_save_defaults"):
            self.btn_save_defaults.setEnabled(enabled)
        if hasattr(self, "btn_save_user_module"):
            self.btn_save_user_module.setEnabled(enabled)
        if hasattr(self, "btn_delete"):
            self.btn_delete.setEnabled(enabled)
        if hasattr(self, "actions_bar"):
            self.actions_bar.setVisible(enabled)
        if hasattr(self, 'btn_dup_left'):
            self.btn_dup_left.setEnabled(enabled)
        if hasattr(self, 'btn_dup_right'):
            self.btn_dup_right.setEnabled(enabled)
        if not enabled:
            if hasattr(self, "card_paredes"):
                self.card_paredes.setVisible(False)
            if hasattr(self, "scroll_paredes"):
                self.scroll_paredes.setVisible(False)
            if hasattr(self, "card_interact"):
                self.card_interact.setVisible(True)
            if hasattr(self, "scroll_area"):
                self.scroll_area.setVisible(False)
            if hasattr(self, "actions_bar"):
                self.actions_bar.setVisible(False)
            if hasattr(self, "btn_apply"):
                self.btn_apply.setVisible(False)
            if hasattr(self, "btn_apply_same_class"):
                self.btn_apply_same_class.setVisible(False)
            if hasattr(self, "btn_save_defaults"):
                self.btn_save_defaults.setVisible(False)
            if hasattr(self, "btn_save_user_module"):
                self.btn_save_user_module.setVisible(False)
            if hasattr(self, "btn_delete"):
                self.btn_delete.setVisible(False)
            if hasattr(self, 'btn_dup_left'):
                self.btn_dup_left.setVisible(False)
            if hasattr(self, 'btn_dup_right'):
                self.btn_dup_right.setVisible(False)
            self.lbl_title.setText("🪵 TrazoMob — Módulos")
            self.lbl_status.setText("💡 Selecione uma parede ou um módulo no 3D para editar.")
            self.card_header.setStyleSheet(
                "QFrame { background-color: palette(base); border: 1px solid palette(mid); border-radius: 4px; padding: 2px 4px; }"
            )
        else:
            self.card_header.setStyleSheet(
                "QFrame { background-color: palette(base); border: 1px solid palette(highlight); border-radius: 4px; padding: 2px 4px; }"
            )


    def find_selected_module(self) -> Group | None:
        """Encontra o módulo do TrazoMob correspondente à seleção atual no 3D."""
        scene = self._get_scene()
        if scene is None:
            return None

        selection = list(getattr(scene, "selection", []))
        if not selection:
            return None

        # 1. Checa se o item selecionado é diretamente um módulo mestre
        for item in selection:
            if hasattr(item, "ext") and isinstance(item.ext, dict):
                if "trazomob_module" in item.ext:
                    return item

        # 2. Checa se uma peça filha selecionada pertence a um módulo mestre
        for g in getattr(scene, "groups", []):
            if hasattr(g, "ext") and isinstance(g.ext, dict):
                if "trazomob_module" in g.ext:
                    children = getattr(g, "children", []) or []
                    if any(child in selection for child in children):
                        return g


    def find_selected_wall(self) -> Group | None:
        """Encontra se a seleção atual no 3D é uma parede paramétrica."""
        scene = self._get_scene()
        if scene is None:
            return None

        selection = list(getattr(scene, "selection", []))
        if not selection:
            return None

        for item in selection:
            if hasattr(item, "ext") and isinstance(item.ext, dict):
                if "trazomob_wall" in item.ext:
                    return item

        for g in getattr(scene, "groups", []):
            if hasattr(g, "ext") and isinstance(g.ext, dict):
                if "trazomob_wall" in g.ext:
                    if any(child in selection for child in (getattr(g, "children", []) or [])):
                        return g

        return None


    def find_selected_light(self) -> Group | None:
        """Encontra se a seleção atual no 3D é uma luminária / fonte de luz física."""
        scene = self._get_scene()
        if scene is None:
            return None

        selection = list(getattr(scene, "selection", []))
        if not selection:
            return None

        for item in selection:
            if hasattr(item, "ext") and isinstance(item.ext, dict):
                if "trazomob_light" in item.ext:
                    return item

        for g in getattr(scene, "groups", []):
            if hasattr(g, "ext") and isinstance(g.ext, dict):
                if "trazomob_light" in g.ext:
                    if any(child in selection for child in (getattr(g, "children", []) or [])):
                        return g

        return None


    def _group_in_active_scene(self, grp) -> bool:
        if grp is None:
            return False
        scene = self._get_scene() if hasattr(self, "_get_scene") else None
        if scene is None:
            return False
        groups = getattr(scene, "groups", None)
        if groups is None:
            return False
        return grp in groups

    def _active_selected_module(self):
        mod = getattr(self, "_selected_module", None)
        if mod is not None and not self._group_in_active_scene(mod):
            self._selected_module = None
            mod = None
        return mod or self.find_selected_module()

    def _active_selected_wall(self):
        wall = getattr(self, "_selected_wall", None)
        if wall is not None and not self._group_in_active_scene(wall):
            self._selected_wall = None
            wall = None
        return wall or self.find_selected_wall()

    def _active_selected_light(self):
        lg = getattr(self, "_selected_light_grp", None)
        if lg is not None and not self._group_in_active_scene(lg):
            self._selected_light_grp = None
            lg = None
        return lg

    def on_scene_changed(self) -> None:
        """Chamado automaticamente quando a seleção ou a cena 3D é alterada."""
        if self._updating_ui:
            return

        scene = self._get_scene()
        was_stale = False
        was_stale_light = False
        groups = getattr(scene, "groups", None) if scene is not None else None
        if groups is not None:
            if getattr(self, "_selected_module", None) is not None and self._selected_module not in groups:
                self._selected_module = None
                was_stale = True
            if getattr(self, "_selected_wall", None) is not None and self._selected_wall not in groups:
                self._selected_wall = None
                was_stale = True
            if getattr(self, "_selected_light_grp", None) is not None and self._selected_light_grp not in groups:
                self._selected_light_grp = None
                was_stale = True
                was_stale_light = True
        elif scene is None:
            if any(getattr(self, attr, None) is not None for attr in ("_selected_module", "_selected_wall", "_selected_light_grp")):
                self._selected_module = None
                self._selected_wall = None
                self._selected_light_grp = None
                was_stale = True
                was_stale_light = True

        # Sincroniza automaticamente recortes/vãos de portas e janelas nas paredes da cena
        if scene is not None:
            from ..wall.mesh_builder import WallMeshBuilder
            if WallMeshBuilder.sync_scene_wall_openings(scene):
                vp = self._get_viewport()
                if vp is not None:
                    vp.update()

        sel = list(getattr(scene, "selection", [])) if scene else []
        sel_groups = [it for it in sel if isinstance(it, Group)]

        def _clear_active_wall_frame() -> None:
            from ..wall.selection import WallSelectionManager
            mgr = WallSelectionManager._instance
            if mgr is not None and mgr.viewport is self._get_viewport():
                mgr.clear_placement_frame()

        # 0. Checa se uma luminária 3D foi clicada/selecionada no viewport
        light_grp = self.find_selected_light()
        if light_grp is not None:
            self._selected_wall = None
            self._selected_module = None
            _clear_active_wall_frame()
            self.load_light_group(light_grp)
            return
        elif was_stale_light or (getattr(self, "_selected_light_grp", None) is not None and not sel):
            self.clear_light_selection()

        # 0.1 Checa se há múltiplos objetos selecionados (Modo Alinhamento / Centralização)
        if len(sel_groups) >= 2:
            self.focus_panel()
            _clear_active_wall_frame()
            alvo = sel_groups[-1]
            base = sel_groups[0]
            if hasattr(self, "card_align"):
                self.card_align.setVisible(True)
                self.lbl_align_info.setText(f"🎯 <b>Centralizar:</b> {alvo.name}")
                self.lbl_align_desc.setText(f"Objeto de Referência: <b>{base.name}</b>")
            if hasattr(self, "card_paredes"):
                self.card_paredes.setVisible(False)
            if hasattr(self, "scroll_paredes"):
                self.scroll_paredes.setVisible(False)
            if hasattr(self, "card_luz"):
                self.card_luz.setVisible(False)
            if hasattr(self, "scroll_area"):
                self.scroll_area.setVisible(False)
            if hasattr(self, "btn_apply"):
                self.btn_apply.setVisible(False)
            if hasattr(self, "btn_save_defaults"):
                self.btn_save_defaults.setVisible(False)
            if hasattr(self, "btn_delete"):
                self.btn_delete.setVisible(False)
            if hasattr(self, 'btn_dup_left'):
                self.btn_dup_left.setVisible(False)
            if hasattr(self, 'btn_dup_right'):
                self.btn_dup_right.setVisible(False)
            self._selected_module = None
            self._selected_wall = None
            self._selected_light_grp = None
            return
        else:
            if hasattr(self, "card_align"):
                self.card_align.setVisible(False)

        # 1. Checa se uma parede foi selecionada
        wall = self.find_selected_wall()
        if wall is not None:
            self._selected_wall = wall
            self._selected_module = None
            self._selected_light_grp = None
            if hasattr(self, "card_luz"):
                self.card_luz.setVisible(False)
            self.load_wall(wall)
            return

        self._selected_wall = None

        # 2. Checa se um módulo de marcenaria foi selecionado
        mod = self.find_selected_module()
        if mod is not self._selected_module or (was_stale and mod is None):
            self._selected_module = mod
            self._selected_light_grp = None
            if hasattr(self, "card_luz"):
                self.card_luz.setVisible(False)
            if mod is not None:
                _clear_active_wall_frame()
                self.load_module(mod)
            else:
                _clear_active_wall_frame()
                self._selected_module = None
                self._set_editor_enabled(False)
                if hasattr(self, "card_paredes"):
                    self.card_paredes.setVisible(False)
                if hasattr(self, "scroll_paredes"):
                    self.scroll_paredes.setVisible(False)
                if hasattr(self, "scroll_area"):
                    self.scroll_area.setVisible(False)
                if hasattr(self, "btn_apply"):
                    self.btn_apply.setVisible(False)
                if hasattr(self, "btn_save_defaults"):
                    self.btn_save_defaults.setVisible(False)
                if hasattr(self, "btn_delete"):
                    self.btn_delete.setVisible(False)
            if hasattr(self, 'btn_dup_left'):
                self.btn_dup_left.setVisible(False)
            if hasattr(self, 'btn_dup_right'):
                self.btn_dup_right.setVisible(False)
        elif mod is not None and not getattr(self, "_updating_ui", False):
            # Se o módulo já estava selecionado mas foi redimensionado ou movido no 3D,
            # atualiza os spinboxes na barra lateral para sincronizar os valores imediatamente
            params = module_params(mod) if getattr(mod, "ext", None) else {}
            if params:
                cur_l = int(round(float(params.get("largura", 0.0))))
                cur_p = int(round(float(params.get("profundidade", 0.0))))
                cur_a = int(round(float(params.get("altura", 0.0))))
                sp_l = int(self.sp_largura.value()) if hasattr(self, "sp_largura") else cur_l
                sp_p = int(self.sp_prof.value()) if hasattr(self, "sp_prof") else cur_p
                sp_a = int(self.sp_altura.value()) if hasattr(self, "sp_altura") else cur_a
                if cur_l != sp_l or cur_p != sp_p or cur_a != sp_a:
                    self.load_module(mod)
                else:
                    tipo = str(params.get("tipo", ""))
                    is_esq = bool(
                        getattr(mod, "ext", None) and isinstance(mod.ext, dict) and "trazomob_esquadria" in mod.ext
                        or getattr(mod, "layer", "") == "ESQUADRIAS"
                        or "porta" in tipo.lower() or "janela" in tipo.lower()
                    )
                    if is_esq and hasattr(self, "sp_esq_dist_canto") and hasattr(self, "_get_esquadria_wall_info"):
                        w_info = self._get_esquadria_wall_info(mod, scene) if scene else None
                        if w_info:
                            new_dist = int(w_info["dist_esq_mm"])
                            self.sp_esq_dist_canto.blockSignals(True)
                            self.sp_esq_dist_canto.setRange(0, max(0, int(w_info["seg_len"] * 1000.0 - float(params.get("largura", 800.0)))))
                            self.sp_esq_dist_canto.setValue(new_dist)
                            self.sp_esq_dist_canto.blockSignals(False)
                            if hasattr(self, "lbl_esq_dist_canto"):
                                self.lbl_esq_dist_canto.setText(f"Distância Canto ({new_dist}mm):")

