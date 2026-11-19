# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Mixin para o painel lateral do TrazoMob especializado na edição de luminárias e iluminação 3D."""
from __future__ import annotations

from typing import Any
from PySide6.QtGui import QVector3D
from PySide6.QtWidgets import QMessageBox
from core.group import Group


class SidebarLightMixin:
    """Encapsula seleção, parametrização (kelvin, potência, ângulo) e ferramentas de luz."""

    def load_light_group(self, light_grp: Group) -> None:
        """Carrega e exibe a edição da luz a partir do Group 3D nativo selecionado no viewport."""
        if not light_grp or not getattr(light_grp, "ext", None):
            self.clear_light_selection()
            return
        ext = light_grp.ext
        if not isinstance(ext, dict) or "trazomob_light" not in ext:
            self.clear_light_selection()
            return

        self._selected_light_grp = light_grp
        vp = self._get_viewport()
        from ..render.lighting import _get_document_lights, sync_scene_lights_to_document, TrazoMobLightVisualizer
        if vp is not None:
            sync_scene_lights_to_document(vp)
        lights = _get_document_lights(vp) if vp else []
        lt = ext["trazomob_light"]

        # Encontra o índice correspondente
        found_idx = None
        for i, l_item in enumerate(lights):
            if l_item.get("pos") == lt.get("pos") and l_item.get("kind") == lt.get("kind"):
                found_idx = i
                break
        self._selected_light_idx = found_idx
        if vp is not None:
            TrazoMobLightVisualizer.set_selected_index(found_idx, vp)

        self._display_light_data(lt, light_grp.name)

    def load_light(self, light_idx: int) -> None:
        """Carrega e exibe a edição da luz selecionada por índice na barra lateral."""
        from ..render.lighting import _get_document_lights
        vp = self._get_viewport()
        lights = _get_document_lights(vp) if vp else []
        if not (0 <= light_idx < len(lights)):
            self.clear_light_selection()
            return

        self._selected_light_idx = light_idx
        lt = lights[light_idx]

        # Localiza o Group correspondente na cena, se houver
        self._selected_light_grp = None
        scene = self._get_scene()
        if scene:
            for g in getattr(scene, "groups", []):
                ext = getattr(g, "ext", None)
                if isinstance(ext, dict) and "trazomob_light" in ext:
                    g_lt = ext["trazomob_light"]
                    if g_lt.get("pos") == lt.get("pos") and g_lt.get("kind") == lt.get("kind"):
                        self._selected_light_grp = g
                        break

        self._display_light_data(lt)

    def _display_light_data(self, lt: dict, custom_name: str | None = None) -> None:
        """Preenche os controles da barra lateral com os dados da luz."""
        self._ensure_form_built()
        self.focus_panel()

        # Oculta outros cards e exibe o card de luz
        if hasattr(self, "card_paredes"):
            self.card_paredes.setVisible(False)
        if hasattr(self, "scroll_paredes"):
            self.scroll_paredes.setVisible(False)
        if hasattr(self, "card_align"):
            self.card_align.setVisible(False)
        if hasattr(self, "scroll_area"):
            self.scroll_area.setVisible(False)
        if hasattr(self, "btn_apply"):
            self.btn_apply.setVisible(False)
        if hasattr(self, "btn_save_defaults"):
            self.btn_save_defaults.setVisible(False)
        if hasattr(self, "btn_delete"):
            self.btn_delete.setVisible(False)
            if hasattr(self, "btn_dup_left"):
                self.btn_dup_left.setVisible(False)
            if hasattr(self, "btn_dup_right"):
                self.btn_dup_right.setVisible(False)
        if hasattr(self, "btn_apply_wall"):
            self.btn_apply_wall.setVisible(False)
        if hasattr(self, "btn_hide_selected_wall"):
            self.btn_hide_selected_wall.setVisible(False)

        self.card_luz.setVisible(True)

        kind = lt.get("kind", "point")
        is_on = lt.get("on", True)
        name = custom_name or lt.get("name") or ("Spot Direcionável" if kind == "spot" else ("Fita LED Linear" if kind == "led_strip" else "Luz Ponto/Omni"))
        idx_txt = f" (#{self._selected_light_idx + 1})" if self._selected_light_idx is not None else ""

        self.lbl_title.setText(f"💡 {name}")
        self.lbl_status.setText(f"Tipo: {kind.upper()} | Objeto 3D Nativo na Cena")
        self.lbl_luz_nome.setText(f"{name}{idx_txt}")

        # Botão Ligar/Desligar
        self.btn_luz_toggle.setText("Desligar Luz" if is_on else "Ligar Luz")
        self.btn_luz_toggle.setStyleSheet(
            "QPushButton { background-color: #059669; color: white; font-weight: bold; padding: 5px; border-radius: 4px; }"
            if is_on else
            "QPushButton { background-color: #6B7280; color: white; font-weight: bold; padding: 5px; border-radius: 4px; }"
        )

        # Distribuição (Omni vs Spot)
        is_spot = (kind == "spot")
        is_led = (kind == "led_strip")
        if hasattr(self, "cb_luz_tipo"):
            self.cb_luz_tipo.setVisible(not is_led)
            self.cb_luz_tipo.blockSignals(True)
            self.cb_luz_tipo.setCurrentIndex(1 if is_spot else 0)
            self.cb_luz_tipo.blockSignals(False)

        # Potência
        self.sp_luz_power.blockSignals(True)
        self.sp_luz_power.setValue(int(lt.get("power", 400)))
        self.sp_luz_power.blockSignals(False)

        # Kelvin
        k = int(lt.get("kelvin", 2700))
        self.sl_luz_kelvin.blockSignals(True)
        self.sl_luz_kelvin.setValue(k)
        self.lbl_luz_kelvin.setText(f"{k}K")
        self.sl_luz_kelvin.blockSignals(False)

        # Altura Z
        pos = lt.get("pos") or [0, 0, 0]
        self.sp_luz_z.blockSignals(True)
        self.sp_luz_z.setValue(float(pos[2]))
        self.sp_luz_z.blockSignals(False)

        # Ângulo e Mira (Spot)
        self.row_luz_ang.setVisible(is_spot)
        self.btn_luz_aim.setVisible(is_spot)
        if is_spot:
            self.sp_luz_ang.blockSignals(True)
            self.sp_luz_ang.setValue(int(lt.get("angle", 45)))
            self.sp_luz_ang.blockSignals(False)

    def clear_light_selection(self) -> None:
        """Limpa a seleção de luz e restaura o card correspondente."""
        self._selected_light_idx = None
        self._selected_light_grp = None
        if hasattr(self, "card_luz"):
            self.card_luz.setVisible(False)
        mod_in_scene = (
            self._selected_module is not None
            and (not hasattr(self, "_group_in_active_scene") or self._group_in_active_scene(self._selected_module))
        )
        if mod_in_scene:
            if hasattr(self, "scroll_area"):
                self.scroll_area.setVisible(True)
            if hasattr(self, "btn_apply"):
                self.btn_apply.setVisible(True)
            if hasattr(self, "btn_delete"):
                self.btn_delete.setVisible(True)
            if hasattr(self, "btn_dup_left"):
                self.btn_dup_left.setVisible(True)
            if hasattr(self, "btn_dup_right"):
                self.btn_dup_right.setVisible(True)

    def _toggle_light_on_off(self) -> None:
        light_grp = self._active_selected_light() if hasattr(self, "_active_selected_light") else self._selected_light_grp
        if light_grp is not None:
            lt = light_grp.ext.get("trazomob_light", {})
            cur = lt.get("on", True)
            lt["on"] = not cur
            light_grp.ext["trazomob_light"] = lt
            self.btn_luz_toggle.setText("Desligar Luz" if not cur else "Ligar Luz")
            self.btn_luz_toggle.setStyleSheet(
                "QPushButton { background-color: #059669; color: white; font-weight: bold; padding: 5px; border-radius: 4px; }"
                if not cur else
                "QPushButton { background-color: #6B7280; color: white; font-weight: bold; padding: 5px; border-radius: 4px; }"
            )
            vp = self._get_viewport()
            if vp:
                from ..render.lighting import sync_scene_lights_to_document
                sync_scene_lights_to_document(vp)
                vp.update()
            return

        if self._selected_light_idx is None:
            return
        from ..render.lighting import _get_document_lights, _save_document_lights
        vp = self._get_viewport()
        lights = _get_document_lights(vp) if vp else []
        idx = self._selected_light_idx
        if 0 <= idx < len(lights):
            cur = lights[idx].get("on", True)
            lights[idx]["on"] = not cur
            _save_document_lights(vp, lights)
            self.btn_luz_toggle.setText("Desligar Luz" if not cur else "Ligar Luz")
            self.btn_luz_toggle.setStyleSheet(
                "QPushButton { background-color: #059669; color: white; font-weight: bold; padding: 5px; border-radius: 4px; }"
                if not cur else
                "QPushButton { background-color: #6B7280; color: white; font-weight: bold; padding: 5px; border-radius: 4px; }"
            )

    def _on_sidebar_light_tipo_changed(self) -> None:
        """Alterna a distribuição entre Omni (360° todas as direções) e Spot (Foco para baixo)."""
        new_kind = self.cb_luz_tipo.currentData() or ("spot" if self.cb_luz_tipo.currentIndex() == 1 else "point")
        is_spot = (new_kind == "spot")
        self.row_luz_ang.setVisible(is_spot)
        self.btn_luz_aim.setVisible(is_spot)

        vp = self._get_viewport()
        light_grp = self._active_selected_light() if hasattr(self, "_active_selected_light") else self._selected_light_grp
        if light_grp is not None:
            lt = light_grp.ext.get("trazomob_light", {})
            lt["kind"] = new_kind
            if is_spot:
                lt.setdefault("angle", float(self.sp_luz_ang.value()))
                lt.setdefault("dir", [0.0, 0.0, -1.0])
            light_grp.ext["trazomob_light"] = lt
            if vp:
                from ..render.lighting import sync_scene_lights_to_document
                sync_scene_lights_to_document(vp)
                vp.update()
        elif self._selected_light_idx is not None:
            from ..render.lighting import _get_document_lights, _save_document_lights
            lights = _get_document_lights(vp) if vp else []
            if 0 <= self._selected_light_idx < len(lights):
                lights[self._selected_light_idx]["kind"] = new_kind
                _save_document_lights(vp, lights)

        self.lbl_status.setText(f"Distribuição: {'SPOT (Foco direcionado)' if is_spot else 'OMNI (360° todas as direções)'}")

    def _on_sidebar_light_prop_changed(self) -> None:
        from ..render.lighting import kelvin_to_rgb, sync_scene_lights_to_document, _get_document_lights, _save_document_lights
        vp = self._get_viewport()
        k = int(self.sl_luz_kelvin.value())
        pwr = float(self.sp_luz_power.value())
        ang = float(self.sp_luz_ang.value()) if hasattr(self, "sp_luz_ang") and self.row_luz_ang.isVisible() else 45.0
        rgb = list(kelvin_to_rgb(k))
        self.lbl_luz_kelvin.setText(f"{k}K")

        light_grp = self._active_selected_light() if hasattr(self, "_active_selected_light") else self._selected_light_grp
        if light_grp is not None:
            lt = light_grp.ext.get("trazomob_light", {})
            lt["power"] = pwr
            lt["kelvin"] = k
            lt["color"] = rgb
            if lt.get("kind") == "spot":
                lt["angle"] = ang
            light_grp.ext["trazomob_light"] = lt
            # Atualiza cor emissiva na malha do grupo 3D
            mesh = getattr(light_grp, "mesh", None)
            if mesh:
                for f in getattr(mesh, "faces", []):
                    m_name = f.attrs.get("mat", "")
                    if "Difusor" in m_name or "Lente" in m_name or "Vidro" in m_name:
                        f.attrs["color"] = (rgb[0], rgb[1], rgb[2])
                mesh._chunk_dirty = True
            if vp:
                sync_scene_lights_to_document(vp)
                vp.update()
            return

        if self._selected_light_idx is None:
            return
        lights = _get_document_lights(vp) if vp else []
        idx = self._selected_light_idx
        if 0 <= idx < len(lights):
            lt = lights[idx]
            lt["power"] = pwr
            lt["kelvin"] = k
            lt["color"] = rgb
            if hasattr(self, "sp_luz_ang") and self.row_luz_ang.isVisible():
                lt["angle"] = ang
            _save_document_lights(vp, lights)

    def _on_sidebar_light_z_changed(self) -> None:
        new_z = round(float(self.sp_luz_z.value()), 4)
        vp = self._get_viewport()

        light_grp = self._active_selected_light() if hasattr(self, "_active_selected_light") else self._selected_light_grp
        if light_grp is not None:
            lt = light_grp.ext.get("trazomob_light", {})
            pos = lt.get("pos") or [0, 0, 0]
            dz = new_z - pos[2]
            pos[2] = new_z
            lt["pos"] = pos
            if lt.get("kind") == "spot" and "target" in lt and lt["target"]:
                lt["target"][2] = round(lt["target"][2] + dz, 4)
            if lt.get("kind") == "led_strip" and "p1" in lt and "p2" in lt:
                lt["p1"][2] = round(lt["p1"][2] + dz, 4)
                lt["p2"][2] = round(lt["p2"][2] + dz, 4)
            light_grp.ext["trazomob_light"] = lt

            # Desloca a malha 3D real no eixo Z
            shift = QVector3D(0.0, 0.0, dz)
            mesh = getattr(light_grp, "mesh", None)
            if mesh and hasattr(mesh, "vertices"):
                for v in mesh.vertices:
                    v.position += shift
                mesh._chunk_dirty = True
            if vp:
                from ..render.lighting import sync_scene_lights_to_document
                sync_scene_lights_to_document(vp)
                vp.update()
            return

        if self._selected_light_idx is None:
            return
        from ..render.lighting import _get_document_lights, _save_document_lights
        lights = _get_document_lights(vp) if vp else []
        idx = self._selected_light_idx
        if 0 <= idx < len(lights):
            lt = lights[idx]
            pos = lt.get("pos") or [0, 0, 0]
            dz = new_z - pos[2]
            pos[2] = new_z
            lt["pos"] = pos
            if lt.get("kind") == "spot" and "target" in lt and lt["target"]:
                lt["target"][2] = round(lt["target"][2] + dz, 4)
            if lt.get("kind") == "led_strip" and "p1" in lt and "p2" in lt:
                lt["p1"][2] = round(lt["p1"][2] + dz, 4)
                lt["p2"][2] = round(lt["p2"][2] + dz, 4)
            _save_document_lights(vp, lights)

    def _aim_selected_light(self) -> None:
        idx = self._selected_light_idx or 0
        from ..render.lighting import AimLightTool
        vp = self._get_viewport()
        if vp:
            tool = AimLightTool(idx, on_aimed=lambda: vp.update())
            vp.set_active_tool(tool)

    def _reposition_selected_light(self) -> None:
        idx = self._selected_light_idx or 0
        from ..render.lighting import MoveLightTool
        vp = self._get_viewport()
        if vp:
            tool = MoveLightTool(idx, on_moved=lambda: self.load_light(idx))
            vp.set_active_tool(tool)

    def _delete_selected_light(self) -> None:
        reply = QMessageBox.question(
            self,
            "Excluir Luz",
            "Deseja realmente remover esta luminária do projeto?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        vp = self._get_viewport()
        scene = self._get_scene()

        # Remove o Group 3D nativo da cena com Undo/Redo
        grp = self._active_selected_light() if hasattr(self, "_active_selected_light") else self._selected_light_grp
        if grp is not None and scene is not None:
            from core.history import SnapshotImport
            def _remove_light_group(sc):
                if grp in sc.groups:
                    sc.groups.remove(grp)
                if hasattr(sc, "selection") and grp in sc.selection:
                    sc.selection.discard(grp)
            if hasattr(vp, "history") and vp.history:
                vp.history.execute(SnapshotImport(_remove_light_group))
            else:
                _remove_light_group(scene)

        if vp is not None:
            from ..render.lighting import sync_scene_lights_to_document, TrazoMobLightVisualizer
            sync_scene_lights_to_document(vp)
            TrazoMobLightVisualizer.set_selected_index(None, vp)
            vp.update()

        self.clear_light_selection()
        self.lbl_status.setText("🗑️ Luminária removida com sucesso.")

    def _delete_all_lights(self) -> None:
        """Remove todas as luminárias do projeto: tanto os grupos 3D quanto os dados do documento legados."""
        reply = QMessageBox.question(
            self,
            "Remover Todas as Luzes",
            "Deseja remover TODAS as luzes do projeto (incluindo luzes legadas antigas e objetos 3D)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        vp = self._get_viewport()
        scene = self._get_scene()

        if scene is not None and vp is not None:
            from ..render.lighting import _apply_light_change, TrazoMobLightVisualizer
            light_grps = [
                g for g in getattr(scene, "groups", [])
                if getattr(g, "ext", None) and isinstance(g.ext, dict) and "trazomob_light" in g.ext
            ]

            def _remove_all_light_groups(sc):
                for g in light_grps:
                    if g in sc.groups:
                        sc.groups.remove(g)
                    if hasattr(sc, "selection") and g in sc.selection:
                        sc.selection.discard(g)

            _apply_light_change(vp, _remove_all_light_groups if light_grps else None, [])
            TrazoMobLightVisualizer.set_selected_index(None, vp)
            vp.update()

        self.clear_light_selection()
        self.lbl_status.setText("🧹 Todas as luzes foram removidas com sucesso.")

