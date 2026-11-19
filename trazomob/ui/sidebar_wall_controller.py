# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Mixin para o painel lateral do TrazoMob especializado em paredes 3D (SidebarWallMixin)."""
from __future__ import annotations

from typing import Any, Optional
from PySide6.QtGui import QVector3D
from core.group import Group
from ..domain.i18n import tr
from ..wall.builder import WallBuilderTool, ReplaceWallGroupCommand


class SidebarWallMixin:
    """Mixin que encapsula o modo de parede, carregamento, alteração e ferramenta interativa."""

    def set_wall_mode(self, active: bool = True) -> None:
        """Configura a barra lateral em modo exclusivo de parede ou modo de marcenaria."""
        if hasattr(self, "_ensure_form_built"):
            self._ensure_form_built()
        if active:
            self.focus_panel()
            self.card_paredes.setVisible(True)
            if hasattr(self, 'scroll_paredes'):
                self.scroll_paredes.setVisible(True)
            self.scroll_area.setVisible(False)
            self.btn_apply.setVisible(False)
            if hasattr(self, "btn_duplicate"):
                self.btn_duplicate.setVisible(False)
            if hasattr(self, "btn_delete"):
                self.btn_delete.setVisible(False)
            if hasattr(self, 'btn_dup_left'):
                self.btn_dup_left.setVisible(False)
            if hasattr(self, 'btn_dup_right'):
                self.btn_dup_right.setVisible(False)
            if hasattr(self, "btn_open_dialog"):
                self.btn_open_dialog.setVisible(False)

            self.lbl_title.setText("🧱 Construtor de Paredes")
            self.lbl_status.setText("💡 Clique no 3D para traçar os cantos das paredes. Feche no início para criar o piso.")
            self.card_header.setStyleSheet(
                "QFrame { background-color: palette(base); border: 1px solid palette(highlight); border-radius: 4px; padding: 2px 4px; }"
            )
            self.btn_toggle_wall_tool.setVisible(True)
            self.btn_toggle_wall_tool.setChecked(True)
            self.btn_toggle_wall_tool.setText(tr("⏹️ Finalizar (Esc)"))
            self.btn_apply_wall.setVisible(False)
        else:
            self.card_paredes.setVisible(False)
            if hasattr(self, 'scroll_paredes'):
                self.scroll_paredes.setVisible(False)
            if hasattr(self, "card_interact"):
                self.card_interact.setVisible(True)
            self.scroll_area.setVisible(self._selected_module is not None)
            self.btn_apply.setVisible(self._selected_module is not None)
            if hasattr(self, "btn_delete"):
                self.btn_delete.setVisible(self._selected_module is not None)

            self.btn_toggle_wall_tool.setVisible(True)
            self.btn_toggle_wall_tool.setChecked(False)
            self.btn_toggle_wall_tool.setText(tr("✏️ Paredes 3D"))
            self.btn_apply_wall.setVisible(False)
            self._set_editor_enabled(self._selected_module is not None)

    def load_wall(self, wall: Group, segment_index: Optional[int] = None, face_type: Optional[str] = None) -> None:
        """Carrega os parâmetros da parede selecionada no painel de paredes da barra lateral."""
        if hasattr(self, "_ensure_form_built"):
            self._ensure_form_built()
        if hasattr(self, "focus_panel"):
            self.focus_panel()
        from ..domain.migration import migrate_legacy_group
        migrate_legacy_group(wall)
        self._updating_ui = True
        try:
            self._selected_wall = wall
            params = wall.ext.get("trazomob_wall", {})
            seg_idx = segment_index if segment_index is not None else params.get("selected_segment")
            alturas = params.get("alturas", [])

            if seg_idx is not None and 0 <= seg_idx < len(alturas):
                current_alt = alturas[seg_idx]
            else:
                current_alt = params.get("altura", 2.6)

            alt_mm = int(round(current_alt * 1000.0))
            esp_mm = int(round(params.get("espessura", 0.15) * 1000.0))
            al = params.get("alinhamento", "interno")

            # Popula a lista de segmentos com seus comprimentos
            raw_pts = params.get("pontos", [])
            pts_vec = [QVector3D(p[0], p[1], p[2]) for p in raw_pts]
            is_closed = params.get("is_closed", False)
            n_segs = len(pts_vec) if is_closed else max(0, len(pts_vec) - 1)

            self.cb_parede_segmento.blockSignals(True)
            self.cb_parede_segmento.clear()
            for s_i in range(n_segs):
                pA = pts_vec[s_i]
                pB = pts_vec[(s_i + 1) % len(pts_vec)]
                len_mm = int(round((pB - pA).length() * 1000.0))
                self.cb_parede_segmento.addItem(f"Parede #{s_i + 1} ({len_mm} mm)", s_i)

            curr_seg = seg_idx if (seg_idx is not None and 0 <= seg_idx < n_segs) else 0
            if n_segs > 0:
                self.cb_parede_segmento.setCurrentIndex(curr_seg)
                pA = pts_vec[curr_seg]
                pB = pts_vec[(curr_seg + 1) % len(pts_vec)]
                seg_len_mm = int(round((pB - pA).length() * 1000.0))
                self.sp_parede_comprimento.setValue(seg_len_mm)
            self.cb_parede_segmento.blockSignals(False)

            self.sp_parede_altura.setValue(alt_mm)
            self.sp_parede_esp.setValue(esp_mm)
            idx_al = 0 if al == "interno" else (1 if al == "centro" else 2)
            self.cb_parede_alinhar.setCurrentIndex(idx_al)

            # Exibe informações de Ambiente e Pavimento da parede
            amb_name = params.get("ambiente") or wall.ext.get("ambiente") or getattr(wall, "name", "Cozinha")
            pav_name = params.get("pavimento") or wall.ext.get("pavimento") or "Térreo"
            if hasattr(self, "cb_parede_ambiente"):
                self._populate_ambiente_combobox(self.cb_parede_ambiente, current_amb=amb_name, current_pav=pav_name)
            elif hasattr(self, "lbl_parede_ambiente_info"):
                self.lbl_parede_ambiente_info.setText(f"Ambiente: <b>{amb_name}</b> ({pav_name})")

            # Armazena segmento ativo
            is_seg = bool(params.get("is_segmented", False))
            effective_seg = curr_seg if n_segs > 0 else (seg_idx if seg_idx is not None else 0)
            params["selected_segment"] = effective_seg
            if face_type:
                params["selected_face_type"] = face_type

            # Exibe painel de parede com foco total (oculta ações gerais e módulos)
            if hasattr(self, "card_quick_actions"):
                self.card_quick_actions.setVisible(False)
            if hasattr(self, "card_ambientes"):
                self.card_ambientes.setVisible(False)
            if hasattr(self, "card_interact"):
                self.card_interact.setVisible(False)
            self.card_paredes.setVisible(True)
            if hasattr(self, 'scroll_paredes'):
                self.scroll_paredes.setVisible(True)
            self.scroll_area.setVisible(False)
            self.btn_apply.setVisible(False)
            if hasattr(self, "btn_delete"):
                self.btn_delete.setVisible(False)
            if hasattr(self, 'btn_dup_left'):
                self.btn_dup_left.setVisible(False)
            if hasattr(self, 'btn_dup_right'):
                self.btn_dup_right.setVisible(False)

            f_desc = ""
            if face_type:
                f_desc = f" ({'Face Interna' if face_type == 'interna' else ('Face Externa' if face_type == 'externa' else face_type.capitalize())})"
            seg_desc = f" — Seg #{effective_seg + 1}{f_desc}" if not is_seg else f"{f_desc}"
            self.lbl_title.setText(f"🧱 {wall.name}{seg_desc}")
            if face_type:
                self.lbl_status.setText(f"🎯 Face ativa para referência e módulos: {f_desc.strip(' ()')}.")
            else:
                self.lbl_status.setText("💡 Altere o comprimento, pé-direito ou espessura e clique em Atualizar Parede.")
            self.card_header.setStyleSheet(
                "QFrame { background-color: palette(base); border: 1px solid palette(highlight); border-radius: 4px; padding: 2px 4px; }"
            )
            self.btn_toggle_wall_tool.setVisible(True)
            self.btn_toggle_wall_tool.setText(tr("📐 Planta 2D"))
            self.btn_apply_wall.setVisible(True)
            if hasattr(self, "btn_frente_parede"):
                self.btn_frente_parede.setVisible(True)
            if hasattr(self, "btn_encaixar_bancada"):
                self.btn_encaixar_bancada.setVisible(True)
            if hasattr(self, "btn_encaixar_tamponamento"):
                self.btn_encaixar_tamponamento.setVisible(True)
            if hasattr(self, 'btn_encaixar_rodape'):
                self.btn_encaixar_rodape.setVisible(True)
            if hasattr(self, "btn_elevacao_parede"):
                self.btn_elevacao_parede.setVisible(True)
            if hasattr(self, "btn_fechar_vao"):
                self.btn_fechar_vao.setVisible(True)
            for nome in ("lbl_auto_preencher", "cb_auto_composicao",
                         "btn_auto_inferiores", "btn_auto_aereos"):
                w = getattr(self, nome, None)
                if w is not None:
                    w.setVisible(True)

            if hasattr(self, "btn_split_walls"):
                # Exibe botão de seccionar somente se for monólito com múltiplos segmentos
                self.btn_split_walls.setVisible(not is_seg and n_segs > 1)

            if hasattr(self, "btn_hide_selected_wall"):
                self.btn_hide_selected_wall.setVisible(True)
                if is_seg:
                    short_name = wall.name[:12] + "…" if len(wall.name) > 13 else wall.name
                    self.btn_hide_selected_wall.setText(f"👁️ Ocultar {short_name}")
                    self.btn_hide_selected_wall.setToolTip(f"Ocultar {wall.name} (use 'Reexibir Tudo' para restaurar).")
                else:
                    self.btn_hide_selected_wall.setText(f"👁️ Ocultar #{effective_seg + 1}")
                    self.btn_hide_selected_wall.setToolTip(f"Ocultar Parede #{effective_seg + 1}.")
        finally:
            self._updating_ui = False

    def _on_wall_segment_combobox_changed(self, index: int) -> None:
        """Chamado quando o usuário escolhe outro segmento de parede no combobox."""
        if self._updating_ui:
            return
        wall = self._active_selected_wall()
        if wall is None:
            return
        params = wall.ext.get("trazomob_wall", {})
        raw_pts = params.get("pontos", [])
        if not raw_pts:
            return
        pts_vec = [QVector3D(p[0], p[1], p[2]) for p in raw_pts]
        is_closed = params.get("is_closed", False)
        n_segs = len(pts_vec) if is_closed else max(0, len(pts_vec) - 1)
        if 0 <= index < n_segs:
            params["selected_segment"] = index
            pA = pts_vec[index]
            pB = pts_vec[(index + 1) % len(pts_vec)]
            seg_len_mm = int(round((pB - pA).length() * 1000.0))
            self.sp_parede_comprimento.blockSignals(True)
            self.sp_parede_comprimento.setValue(seg_len_mm)
            self.sp_parede_comprimento.blockSignals(False)

            alturas = params.get("alturas", [])
            alt_m = alturas[index] if index < len(alturas) else params.get("altura", 2.6)
            self.sp_parede_altura.blockSignals(True)
            self.sp_parede_altura.setValue(int(round(alt_m * 1000.0)))
            self.sp_parede_altura.blockSignals(False)

            if hasattr(self, "btn_hide_selected_wall"):
                self.btn_hide_selected_wall.setText(f"👁️ Ocultar #{index + 1}")

    @staticmethod
    def _adjust_wall_points_length(
        pts: list[QVector3D], is_closed: bool, seg_idx: int, new_length_m: float
    ) -> list[QVector3D]:
        """Recalcula as coordenadas dos vértices da parede ao alterar o comprimento do segmento seg_idx."""
        n = len(pts)
        n_segs = n if is_closed else n - 1
        if not (0 <= seg_idx < n_segs):
            return pts

        pA = pts[seg_idx]
        pB = pts[(seg_idx + 1) % n]
        dir_vec = pB - pA
        curr_len = dir_vec.length()
        if curr_len < 1e-6:
            return pts

        delta_len = new_length_m - curr_len
        if abs(delta_len) < 1e-5:
            return pts

        unit_dir = dir_vec.normalized()
        shift = unit_dir * delta_len

        # Caso 1: Retângulo ortogonal de 4 paredes fechadas (caso clássico de quarto/cômodo)
        if is_closed and n == 4:
            idx_b = (seg_idx + 1) % 4
            idx_c = (seg_idx + 2) % 4
            new_pts = [QVector3D(p) for p in pts]
            new_pts[idx_b] += shift
            new_pts[idx_c] += shift
            return new_pts

        # Caso 2: Polígono ortogonal fechado geral (ex: cômodo em L, 6 vértices)
        # Se os segmentos adjacentes forem perpendiculares a dir_vec, desloca a aresta inteira
        if is_closed and n > 4:
            new_pts = [QVector3D(p) for p in pts]
            idx_b = (seg_idx + 1) % n
            # Verifica se o próximo segmento é perpendicular
            next_seg_dir = (pts[(idx_b + 1) % n] - pts[idx_b]).normalized()
            if abs(QVector3D.dotProduct(unit_dir, next_seg_dir)) < 0.15:
                # O segmento seg_idx empurra o ponto B e estende/encurta os segmentos conectados
                new_pts[idx_b] += shift
                return new_pts

        # Caso 3: Cadeia aberta ou polígono geral:
        # Desloca pB e todos os pontos subsequentes pelo shift
        new_pts = [QVector3D(p) for p in pts]
        for i in range(seg_idx + 1, n):
            new_pts[i] += shift
        return new_pts

    def _apply_wall_changes(self) -> None:
        """Reconstrói a parede selecionada com as novas medidas configuradas na barra lateral."""
        wall = self._active_selected_wall()
        if wall is None:
            return

        viewport = self._get_viewport()
        scene = self._get_scene()
        if viewport is None or scene is None:
            return

        params = wall.ext.get("trazomob_wall", {})
        raw_pts = params.get("pontos", [])
        if not raw_pts:
            return

        pts = [QVector3D(p[0], p[1], p[2]) for p in raw_pts]
        is_closed = params.get("is_closed", False)
        n_segs = len(pts) if is_closed else max(0, len(pts) - 1)

        alt_m = float(self.sp_parede_altura.value()) / 1000.0
        esp_m = float(self.sp_parede_esp.value()) / 1000.0
        new_len_m = float(self.sp_parede_comprimento.value()) / 1000.0
        idx_al = self.cb_parede_alinhar.currentIndex()
        alinhamento = "interno" if idx_al == 0 else ("centro" if idx_al == 1 else "externo")

        # Verifica se altera todas ou somente a parede selecionada
        apply_all = self.chk_parede_todas.isChecked()
        selected_seg = self.cb_parede_segmento.currentIndex()
        if selected_seg < 0 or selected_seg >= n_segs:
            selected_seg = params.get("selected_segment", 0)

        # Ajusta comprimento do segmento se foi modificado
        pts = self._adjust_wall_points_length(pts, is_closed, selected_seg, new_len_m)

        if apply_all or selected_seg is None or not (0 <= selected_seg < n_segs):
            alturas_to_apply: float | list[float] = alt_m
        else:
            old_alturas = params.get("alturas", [])
            if len(old_alturas) < n_segs:
                def_h = params.get("altura", 2.6)
                old_alturas = [def_h] * n_segs
            else:
                old_alturas = list(old_alturas)
            old_alturas[selected_seg] = alt_m
            alturas_to_apply = old_alturas

        # Preserva material do grupo e atributos das faces antigas (cores, texturas, pintura)
        old_material = getattr(wall, "material", None)
        old_face_attrs = []
        if hasattr(wall, "mesh") and hasattr(wall.mesh, "faces"):
            for f in wall.mesh.faces:
                old_face_attrs.append(dict(f.attrs) if f.attrs else {})

        new_grp = WallBuilderTool.build_chain_group(
            scene=scene,
            pts=pts,
            is_closed=is_closed,
            altura_m=alturas_to_apply,
            espessura_m=esp_m,
            alinhamento=alinhamento,
            name_override=wall.name,
            segment_index=selected_seg,
        )

        if old_material:
            new_grp.material = dict(old_material)

        # Transfere cores e texturas das faces antigas para as novas faces
        if hasattr(new_grp, "mesh") and hasattr(new_grp.mesh, "faces"):
            for idx, nf in enumerate(new_grp.mesh.faces):
                if idx < len(old_face_attrs) and old_face_attrs[idx]:
                    for k in ("color", "texture", "opacity", "mat"):
                        if k in old_face_attrs[idx]:
                            nf.attrs[k] = old_face_attrs[idx][k]

        cmd = ReplaceWallGroupCommand(wall, new_grp)
        viewport.history.execute(cmd)
        self._selected_wall = new_grp
        scene.selection = {new_grp}

        # Se houver piso associado no cômodo e o perímetro mudou, atualiza o piso também
        if is_closed:
            from ..wall.mesh_builder import WallMeshBuilder
            floor_grp = None
            for g in getattr(scene, "groups", []):
                ext_g = getattr(g, "ext", None)
                if isinstance(ext_g, dict) and ext_g.get("trazomob_floor"):
                    floor_grp = g
                    break
            if floor_grp is not None:
                new_floor = WallMeshBuilder.build_floor_group(scene, pts)
                if new_floor is not None:
                    viewport.history.execute(ReplaceWallGroupCommand(floor_grp, new_floor))

        viewport.update()

        alvo_txt = "Todas as paredes" if apply_all else f"Parede #{selected_seg + 1}"
        pA = pts[selected_seg]
        pB = pts[(selected_seg + 1) % len(pts)]
        final_len_mm = int(round((pB - pA).length() * 1000.0))
        self.lbl_status.setText(f"✅ {alvo_txt} atualizada: {final_len_mm}mm x {alt_m:.2f}m (esp: {int(esp_m*1000)}mm).")

    def _toggle_wall_builder(self) -> None:
        """Abre o diálogo 2D de Planta Baixa para desenhar ou editar paredes existentes."""
        from ..integrations import platform as host
        viewport = self._get_viewport()
        win = host.window_of(self._get_window(), viewport) if hasattr(self, "_get_window") else (viewport.window() if viewport else None)
        wall = self._active_selected_wall() if self._group_in_active_scene(getattr(self, "_selected_wall", None)) else None
        from ..wall.floorplan_dialog import WallFloorplanDialog
        dlg = WallFloorplanDialog(viewport, existing_group=wall, parent=win)
        dlg.exec()
        if hasattr(self, "btn_toggle_wall_tool"):
            self.btn_toggle_wall_tool.setChecked(False)

    def _toggle_walls_floor_lock(self, checked: bool = True) -> None:
        """Alterna a trava anti-movimento para paredes e pisos da cena."""
        scene = self._get_scene()
        vp = self._get_viewport()
        is_locked = bool(checked)

        if is_locked:
            self.btn_lock_walls_floor.setText(tr("🔒 Trava: ATIVA"))
            if vp and hasattr(vp, "flash_status"):
                vp.flash_status("🔒 Posição de Paredes e Piso travada (Snaps e Cotas 100% ativos).")
        else:
            self.btn_lock_walls_floor.setText(tr("🔓 Trava: LIVRE"))
            if vp and hasattr(vp, "flash_status"):
                vp.flash_status("🔓 Posição de Paredes e Piso liberada para movimentação.")

        if scene and hasattr(scene, "groups"):
            for g in scene.groups:
                ext = getattr(g, "ext", None)
                if not isinstance(ext, dict):
                    continue
                if "trazomob_wall" in ext or "trazomob_floor" in ext or getattr(g, "layer", "") in ("Parede", "Piso"):
                    ext["motion_locked"] = is_locked
                    g.motion_locked = is_locked
                    if "trazomob_wall" in ext and isinstance(ext["trazomob_wall"], dict):
                        ext["trazomob_wall"]["motion_locked"] = is_locked

        if vp:
            vp.update()

    def _on_wall_ambiente_changed(self, idx: int) -> None:
        if getattr(self, "_updating_ui", False):
            return
        wall = self._active_selected_wall()
        if wall is None or not hasattr(self, "cb_parede_ambiente"):
            return
        data = self.cb_parede_ambiente.itemData(idx)
        if isinstance(data, dict):
            new_amb = data.get("ambiente", "Cozinha")
            new_pav = data.get("pavimento", "Térreo")
        else:
            txt = self.cb_parede_ambiente.currentText().strip()
            new_amb = txt.split("(")[0].strip() or "Cozinha"
            new_pav = "Térreo"
        self._apply_wall_ambiente(wall, new_amb, new_pav)

    def _on_wall_ambiente_editing_finished(self) -> None:
        if getattr(self, "_updating_ui", False):
            return
        wall = self._active_selected_wall()
        if wall is None or not hasattr(self, "cb_parede_ambiente"):
            return
        txt = self.cb_parede_ambiente.currentText().strip()
        new_amb = txt.split("(")[0].strip() or "Cozinha"
        new_pav = "Térreo"
        self._apply_wall_ambiente(wall, new_amb, new_pav)

    def _apply_wall_ambiente(self, wall: Any, new_amb: str, new_pav: str) -> None:
        if hasattr(wall, "ext") and isinstance(wall.ext, dict):
            wall.ext["ambiente"] = new_amb
            wall.ext["pavimento"] = new_pav
            if "trazomob_wall" in wall.ext and isinstance(wall.ext["trazomob_wall"], dict):
                wall.ext["trazomob_wall"]["ambiente"] = new_amb
                wall.ext["trazomob_wall"]["pavimento"] = new_pav

        if hasattr(self, "card_ambientes"):
            self.card_ambientes.refresh_tree()

        vp = self._get_viewport()
        if vp is not None:
            if hasattr(vp, "flash_status"):
                vp.flash_status(f"Parede movida para '{new_amb} ({new_pav})'")
            vp.update()
