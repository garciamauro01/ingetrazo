# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Gerenciador e visualizador de seleção de faces de parede (WallSelectionManager).

Permite:
1. Detectar o clique numa face de parede no 3D;
2. Destacar visualmente a face selecionada com feedback de cor/highlight translúcido;
3. Fornecer plano, segmento e orientação de referência para encaixe automático de módulos.
"""
from __future__ import annotations

import logging
import math
from typing import Optional, Tuple, List, Dict, Any

from PySide6.QtCore import QPointF, Qt, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF, QVector3D

from core.group import Group
from core.mesh import Face
from ..integrations import platform as host


logger = logging.getLogger("trazomob.wall_selection")


class WallFaceInfo:
    """Informações geométricas e semânticas da face de parede selecionada."""

    def __init__(
        self,
        wall_group: Group,
        face: Face,
        segment_index: int,
        face_type: str,  # 'interna', 'externa', 'topo', 'base', 'topo_degrau', 'topo_termino'
        normal: QVector3D,
        center: QVector3D,
    ) -> None:
        self.wall_group = wall_group
        self.face = face
        self.segment_index = segment_index
        self.face_type = face_type
        self.normal = normal
        self.center = center


class WallSelectionManager:
    """Singleton/Gerenciador de estado para a face de parede ativa no viewport."""

    _instance: Optional[WallSelectionManager] = None

    def __init__(self, viewport=None, sidebar_panel=None) -> None:
        self._fallback_viewport = viewport
        self.sidebar_panel = sidebar_panel
        self.selected_wall_face: Optional[WallFaceInfo] = None
        self._saved_face_color = None
        self._overlay_installed = False
        self.active_placement_slot: Optional[Dict[str, any]] = None

    @property
    def viewport(self):
        return host.active_viewport(viewport=self._fallback_viewport)

    @viewport.setter
    def viewport(self, vp) -> None:
        if vp is not None:
            self._fallback_viewport = vp

    @classmethod
    def get_instance(cls, viewport=None, sidebar_panel=None) -> WallSelectionManager:
        if cls._instance is None:
            cls._instance = WallSelectionManager(viewport, sidebar_panel)
        else:
            if viewport is not None:
                cls._instance.viewport = viewport
            if sidebar_panel is not None:
                cls._instance.sidebar_panel = sidebar_panel
        if viewport is not None:
            active_vp = cls._instance.viewport
            if active_vp is not None:
                cls._instance.sync_with_scene(getattr(active_vp, "scene", None))
        return cls._instance

    @staticmethod
    def _restore_face_color(old_face: Any, saved_color: Any) -> None:
        """Restaura ou remove o atributo de cor salvo em uma face antiga."""
        attrs = getattr(old_face, "attrs", None)
        if attrs is None or not hasattr(attrs, "pop"):
            return
        if saved_color is not None:
            attrs["color"] = saved_color
        else:
            attrs.pop("color", None)

    def sync_with_scene(self, scene) -> None:
        """Limpa seleção/slot de parede se a parede selecionada não pertencer à cena ativa."""
        info = self.selected_wall_face
        if info is None or scene is None:
            return
        groups = getattr(scene, "groups", None)
        if groups is not None and info.wall_group is not None and info.wall_group not in groups:
            self._restore_face_color(info.face, self._saved_face_color)
            self.selected_wall_face = None
            self._saved_face_color = None
            self.active_placement_slot = None

    def install_overlay(self) -> None:
        """Garante registro do callback de overlay na passagem de pintura do viewport."""
        if self.viewport is None:
            return
        if not hasattr(self.viewport, "_ext_overlays") or self.viewport._ext_overlays is None:
            self.viewport._ext_overlays = []
        if self.draw_selection_overlay not in self.viewport._ext_overlays:
            self.viewport._ext_overlays.append(self.draw_selection_overlay)
        self._overlay_installed = True

    def uninstall_overlay(self) -> None:
        """Remove o callback de overlay do viewport (motor TrazoMob desligado)."""
        if self.viewport is None:
            return
        overlays = getattr(self.viewport, "_ext_overlays", None)
        if overlays and self.draw_selection_overlay in overlays:
            try:
                overlays.remove(self.draw_selection_overlay)
            except ValueError:
                pass
        self._overlay_installed = False

    def clear_placement_frame(self) -> None:
        """Remove o frame 3D de inserção sem descartar a face de parede de referência."""
        if self.active_placement_slot is not None:
            self.active_placement_slot = None
            if self.viewport is not None and hasattr(self.viewport, "update"):
                self.viewport.update()

    def clear_selection(self) -> None:
        """Limpa a face de parede selecionada e restaura sua aparência original."""
        if self.selected_wall_face is not None:
            self._restore_face_color(self.selected_wall_face.face, self._saved_face_color)

            # Notifica a cena para atualizar os chunks de malha no OpenGL
            if self.viewport is not None and hasattr(self.viewport, "scene"):
                try:
                    from core.history import _dirty_group_chunks
                    _dirty_group_chunks(self.viewport.scene)
                except Exception as exc:
                    logger.debug("falha ao marcar chunks da parede como sujos: %s", exc)

            self.selected_wall_face = None
            self._saved_face_color = None
            self.active_placement_slot = None
            if self.viewport is not None:
                self.viewport.update()

    def set_selected_face(self, wall_group: Group, face: Face, notify_sidebar: bool = True) -> Optional[WallFaceInfo]:
        """Analisa a face e registra como face ativa de parede."""
        if not hasattr(wall_group, "mesh") or not wall_group.mesh or face not in wall_group.mesh.faces:
            return None

        # Se a face ou o grupo estiverem ocultos, não permite seleção
        if getattr(wall_group, "hidden", False) or bool(getattr(face, "attrs", {}).get("hidden")):
            return None

        ext = getattr(wall_group, "ext", {})
        if not isinstance(ext, dict) or "trazomob_wall" not in ext:
            return None

        from ..domain.migration import migrate_legacy_group
        migrate_legacy_group(wall_group)
        ext = getattr(wall_group, "ext", {})

        # Se já havia outra face selecionada anteriormente, restaura sua cor
        if self.selected_wall_face is not None and self.selected_wall_face.face is not face:
            self._restore_face_color(self.selected_wall_face.face, self._saved_face_color)
            self._saved_face_color = None

        params = ext.get("trazomob_wall", {})
        face_map: Dict[Any, int] = params.get("face_segment_map", {})
        f_idx = wall_group.mesh.faces.index(face)
        seg_idx = face_map.get(f_idx, face_map.get(str(f_idx), 0))

        # Salva a cor original da face (se ainda não salva)
        if face is not None:
            self._saved_face_color = face.attrs.get("color")

        # Calcula a normal e o centro da face
        normal = face.normal()
        pts = face.vertices
        if not pts:
            return None

        cx = sum(p.x() for p in pts) / len(pts)
        cy = sum(p.y() for p in pts) / len(pts)
        cz = sum(p.z() for p in pts) / len(pts)
        center = QVector3D(cx, cy, cz)

        # Determina o tipo de face baseado na normal
        if normal.z() > 0.7:
            face_type = "topo"
        elif normal.z() < -0.7:
            face_type = "base"
        else:
            # Face vertical (parede)
            # Verifica com a direção do segmento para saber se é lado interno ou externo
            pontos = params.get("pontos", [])
            alinhamento = params.get("alinhamento", "interno")
            if len(pontos) >= 2 and seg_idx < len(pontos):
                p0 = QVector3D(*pontos[seg_idx])
                nxt_idx = (seg_idx + 1) % len(pontos) if params.get("is_closed") else min(seg_idx + 1, len(pontos) - 1)
                p1 = QVector3D(*pontos[nxt_idx])
                d = (p1 - p0).normalized()
                seg_norm = QVector3D(-d.y(), d.x(), 0.0).normalized()

                dot = QVector3D.dotProduct(normal, seg_norm)
                if alinhamento == "interno":
                    face_type = "interna" if dot < 0 else "externa"
                else:
                    face_type = "externa" if dot > 0 else "interna"
            else:
                face_type = "lateral"

        # Aplica a cor de highlight na face nativa do OpenGL (GPU Z-Buffer automático)
        # Amarelo bem clarinho e discreto (pastel suave)
        if face_type == "interna":
            face.attrs["color"] = (0.98, 0.96, 0.78)   # Amarelo suave/creme bem discreto
        elif face_type == "externa":
            face.attrs["color"] = (0.95, 0.93, 0.82)   # Tom areia/amarelo pálido
        else:
            face.attrs["color"] = (0.96, 0.94, 0.80)

        info = WallFaceInfo(
            wall_group=wall_group,
            face=face,
            segment_index=seg_idx,
            face_type=face_type,
            normal=normal,
            center=center,
        )
        self.selected_wall_face = info
        # Só arma o frame 3D quando o usuário clica diretamente na parede (arm_frame_from_click)
        self.active_placement_slot = None

        # Marca os chunks como sujos para o OpenGL atualizar a malha 3D com a nova cor da face
        if self.viewport is not None and hasattr(self.viewport, "scene"):
            try:
                from core.history import _dirty_group_chunks
                _dirty_group_chunks(self.viewport.scene)
            except Exception as exc:
                logger.debug("falha ao marcar chunks após pintar a face: %s", exc)

        # Atualiza metadados na parede
        params["selected_segment"] = seg_idx
        params["selected_face_idx"] = f_idx
        params["selected_face_type"] = face_type

        # Notifica o painel lateral se disponível e solicitado
        if notify_sidebar and self.sidebar_panel is not None:
            try:
                self.sidebar_panel.load_wall(wall_group, segment_index=seg_idx, face_type=face_type)
            except Exception as exc:
                logger.debug("painel lateral não carregou a parede: %s", exc)

        self.install_overlay()
        if self.viewport is not None:
            if hasattr(self.viewport, "flash_status"):
                desc_lado = "Face Interna" if face_type == "interna" else ("Face Externa" if face_type == "externa" else f"Face ({face_type})")
                self.viewport.flash_status(f"🧱 Parede Selecionada: Segmento #{seg_idx + 1} — {desc_lado}")
            if hasattr(self.viewport, "update"):
                self.viewport.update()

        return info

    @staticmethod
    def _bounds_u_interval(
        bounds: Tuple[float, float, float, float, float, float],
        u_dir: QVector3D,
    ) -> Tuple[float, float]:
        """Intervalo U ocupado pela AABB de um móvel no eixo tangencial da parede."""
        min_x, max_x, min_y, max_y, _, _ = bounds
        vals = [
            x * u_dir.x() + y * u_dir.y()
            for x, y in ((min_x, min_y), (max_x, min_y), (min_x, max_y), (max_x, max_y))
        ]
        return min(vals), max(vals)

    def _find_u_snap_near_modules(
        self,
        hit_u: float,
        c_world: QVector3D,
        n_dir: QVector3D,
        u_dir: QVector3D,
        min_u: float,
        max_u: float,
        z_base: float,
        z_top: float,
        width_m: float,
        half_w: float,
        tolerance_m: float = 0.12,
    ) -> Optional[Tuple[float, float, str]]:
        """Atrai o frame para a borda de um móvel já existente na mesma parede/faixa.

        Retorna (u_pos, anchor_u, side). ``anchor_u`` é sempre a borda esquerda do
        novo frame (contrato já usado pela sidebar); ``side`` diz se o vizinho está
        à esquerda (``right``) ou à direita (``left``) do frame armado.
        """
        from ..interaction.magnetic_drag_snap import (
            get_bounds_min_projection,
            get_module_reference_bounds,
        )

        scene = getattr(self.viewport, "scene", None)
        groups = getattr(scene, "groups", None) if scene is not None else None
        if not groups:
            return None

        wall_n = QVector3D.dotProduct(c_world, n_dir)
        neighbors = []
        for grp in groups:
            ext = getattr(grp, "ext", None)
            if not isinstance(ext, dict) or "trazomob_module" not in ext:
                continue
            bounds = get_module_reference_bounds(grp)
            if bounds is None:
                continue
            # Mesma parede e mesma faixa vertical do vão armado (critérios do arraste)
            if abs(get_bounds_min_projection(bounds, n_dir) - wall_n) > 0.15:
                continue
            if z_top < bounds[4] - 0.20 or z_base > bounds[5] + 0.20:
                continue
            neighbors.append(self._bounds_u_interval(bounds, u_dir))

        best = None
        for o_min_u, o_max_u in neighbors:
            candidates = []
            d_right = abs(hit_u - o_max_u)
            if d_right <= tolerance_m:
                # Vizinho à esquerda: o novo módulo começa na borda direita dele
                candidates.append((d_right, o_max_u + half_w, o_max_u, "right"))
            d_left = abs(hit_u - o_min_u)
            if d_left <= tolerance_m:
                # Vizinho à direita: o novo módulo termina na borda esquerda dele
                candidates.append((d_left, o_min_u - half_w, o_min_u - width_m, "left"))
            if o_min_u <= hit_u <= o_max_u:
                # Clique sobre a faixa já ocupada: segue logo após o móvel existente
                candidates.append((0.0, o_max_u + half_w, o_max_u, "right"))

            for dist, u_pos, anchor_u, side in candidates:
                if u_pos - half_w < min_u - 1e-6 or u_pos + half_w > max_u + 1e-6:
                    continue
                if best is None or dist < best[0]:
                    best = (dist, u_pos, anchor_u, side)

        if best is None:
            return None
        return best[1], best[2], best[3]

    def arm_frame_from_click(self, px: float, py: float, target_width_m: Optional[float] = None) -> bool:
        """Arma o frame 3D entre as duas linhas-guia mais próximas onde o usuário clicou na parede."""
        self.sync_with_scene(getattr(self.viewport, "scene", None))
        if self.viewport is None or self.selected_wall_face is None:
            return False

        info = self.selected_wall_face
        if info.face is None:
            return False

        # Obtém o raio da câmera para as coordenadas de tela clicadas
        ray_orig, ray_dir = self.viewport._pixel_to_ray(px, py)
        if ray_orig is None or ray_dir is None:
            return False

        # Plano da face da parede: ponto = info.center, normal = info.normal
        # Se houver transformação do grupo, projeta no espaço global
        xf = getattr(info.wall_group, "xform", None)
        c_world = xf.map(info.center) if xf is not None else info.center
        n_world = info.normal

        hit_pt = self.viewport._ray_plane(ray_orig, ray_dir, c_world, n_world)
        if hit_pt is None:
            return False

        # Consulta a faixa vertical entre as linhas-guia da régua ativa
        from ..wall.guides import WallGuideRulerManager
        ruler_mgr = WallGuideRulerManager.get_instance()
        slot = ruler_mgr.get_slot_between_guides(hit_pt.z())

        # Vetor normal e tangencial da parede
        n_dir = QVector3D(n_world.x(), n_world.y(), 0.0).normalized()
        u_dir = QVector3D(-n_dir.y(), n_dir.x(), 0.0).normalized()

        width_m = float(target_width_m) if target_width_m is not None else 0.80
        depth_m = float(slot.get("default_depth_mm", 550.0)) / 1000.0
        half_w = width_m * 0.5

        # Posição horizontal central do clique ao longo do eixo u_dir
        # Garante que o frame fique estritamente confinado dentro dos limites físicos da face da parede
        hit_u = QVector3D.dotProduct(hit_pt, u_dir)
        raw_pts = [xf.map(p) if xf is not None else p for p in getattr(info.face, "vertices", [])]
        if raw_pts:
            projs_u = [QVector3D.dotProduct(p, u_dir) for p in raw_pts]
            min_u, max_u = min(projs_u), max(projs_u)
            if max_u - min_u > width_m:
                clamped_u = max(min_u + half_w, min(max_u - half_w, hit_u))
            else:
                clamped_u = (min_u + max_u) * 0.5
        else:
            min_u = max_u = hit_u
            clamped_u = hit_u

        # Snap magnético (12 cm, igual ao arraste) ao móvel já existente na parede
        snap = self._find_u_snap_near_modules(
            hit_u, c_world, n_dir, u_dir, min_u, max_u,
            slot["z_base"], slot["z_top"], width_m, half_w,
        )
        if snap is not None:
            clamped_u, anchor_u, anchor_side = snap
        else:
            anchor_u = anchor_side = None

        # Ponto central da base do frame na face da parede
        center_u = QVector3D.dotProduct(c_world, u_dir)
        p_frame_wall_center = c_world + u_dir * (clamped_u - center_u)
        p_frame_wall_center = QVector3D(p_frame_wall_center.x(), p_frame_wall_center.y(), slot["z_base"])

        # Calcula os 8 vértices do paralelepípedo do frame 3D
        z_b = slot["z_base"]
        z_t = slot["z_top"]
        half_w = width_m * 0.5

        p_bl_back = p_frame_wall_center - u_dir * half_w
        p_br_back = p_frame_wall_center + u_dir * half_w
        p_tl_back = QVector3D(p_bl_back.x(), p_bl_back.y(), z_t)
        p_tr_back = QVector3D(p_br_back.x(), p_br_back.y(), z_t)

        p_bl_front = p_bl_back + n_dir * depth_m
        p_br_front = p_br_back + n_dir * depth_m
        p_tl_front = p_tl_back + n_dir * depth_m
        p_tr_front = p_tr_back + n_dir * depth_m

        frame_box = {
            "bl_back": p_bl_back,
            "br_back": p_br_back,
            "tl_back": p_tl_back,
            "tr_back": p_tr_back,
            "bl_front": p_bl_front,
            "br_front": p_br_front,
            "tl_front": p_tl_front,
            "tr_front": p_tr_front,
        }

        # Armazena todas as informações do slot armado
        self.active_placement_slot = {
            **slot,
            "width_m": width_m,
            "depth_m": depth_m,
            "center_pt": p_frame_wall_center,
            "u_pos": clamped_u,
            "n_dir": n_dir,
            "u_dir": u_dir,
            "box_vertices": frame_box,
            "wall_face": info,
        }
        if anchor_u is not None:
            self.active_placement_slot["anchor_u"] = anchor_u
            self.active_placement_slot["anchor_side"] = anchor_side
            if hasattr(self.viewport, "flash_status"):
                self.viewport.flash_status("🧲 Snap magnético: módulo alinhado ao existente")
        self.install_overlay()

    def update_frame_dimensions(self, width_m: float, depth_m: Optional[float] = None) -> None:
        """Atualiza a largura e profundidade do frame para casar exatamente com o módulo selecionado no catálogo.

        Se o frame estiver ancorado na quina de um móvel já inserido (anchor_u), ele expande ou contrai
        mantendo-se RIGOROSAMENTE colado na face lateral daquele móvel, sem deixar vão e sem sobrepor!
        """
        if self.active_placement_slot is None or self.selected_wall_face is None:
            return

        info = self.selected_wall_face
        slot = self.active_placement_slot
        u_dir = slot["u_dir"]
        n_dir = slot["n_dir"]
        if depth_m is None:
            depth_m = slot.get("depth_m", 0.55)

        half_w = width_m * 0.5
        anchor_u = slot.get("anchor_u")

        if anchor_u is not None:
            if slot.get("anchor_side") == "left":
                # Vizinho à direita: preserva a borda direita colada ao móvel existente
                cur_u = anchor_u + slot.get("width_m", width_m) - half_w
            else:
                # Vizinho à esquerda: preserva a borda esquerda colada ao móvel existente
                cur_u = anchor_u + half_w
        else:
            cur_u = slot["u_pos"]

        # Confinamento aos limites da parede
        xf = getattr(info.wall_group, "xform", None)
        raw_pts = [xf.map(p) if xf is not None else p for p in getattr(info.face, "vertices", [])]
        if raw_pts:
            projs_u = [QVector3D.dotProduct(p, u_dir) for p in raw_pts]
            min_u, max_u = min(projs_u), max(projs_u)
            if max_u - min_u > width_m:
                cur_u = max(min_u + half_w, min(max_u - half_w, cur_u))
            else:
                cur_u = (min_u + max_u) * 0.5

        if anchor_u is not None:
            # Mantém anchor_u como borda esquerda (contrato já usado pela sidebar)
            slot["anchor_u"] = cur_u - half_w

        c_world = xf.map(info.center) if xf is not None else info.center
        center_u = QVector3D.dotProduct(c_world, u_dir)
        p_frame_wall_center = c_world + u_dir * (cur_u - center_u)
        p_frame_wall_center = QVector3D(p_frame_wall_center.x(), p_frame_wall_center.y(), slot["z_base"])

        z_b = slot["z_base"]
        z_t = slot["z_top"]

        p_bl_back = p_frame_wall_center - u_dir * half_w
        p_br_back = p_frame_wall_center + u_dir * half_w
        p_tl_back = QVector3D(p_bl_back.x(), p_bl_back.y(), z_t)
        p_tr_back = QVector3D(p_br_back.x(), p_br_back.y(), z_t)

        p_bl_front = p_bl_back + n_dir * depth_m
        p_br_front = p_br_back + n_dir * depth_m
        p_tl_front = p_tl_back + n_dir * depth_m
        p_tr_front = p_tr_back + n_dir * depth_m

        slot["width_m"] = width_m
        slot["depth_m"] = depth_m
        slot["u_pos"] = cur_u
        slot["center_pt"] = p_frame_wall_center
        slot["box_vertices"] = {
            "bl_back": p_bl_back,
            "br_back": p_br_back,
            "tl_back": p_tl_back,
            "tr_back": p_tr_back,
            "bl_front": p_bl_front,
            "br_front": p_br_front,
            "tl_front": p_tl_front,
            "tr_front": p_tr_front,
        }

        if self.viewport is not None:
            self.viewport.update()

    def advance_slot_after_placement(self, placed_width_m: float) -> None:
        """Desloca o frame 3D armado para a posição imediatamente contígua ao módulo inserido."""
        if self.active_placement_slot is None or self.selected_wall_face is None:
            return

        info = self.selected_wall_face
        slot = self.active_placement_slot
        u_dir = slot["u_dir"]
        n_dir = slot["n_dir"]
        width_m = slot.get("width_m", 0.80)
        depth_m = slot.get("depth_m", 0.55)
        half_w = width_m * 0.5
        z_b = slot["z_base"]
        z_t = slot["z_top"]

        # Posição U das quinas do móvel recém-inserido
        # (o centro estava em u_pos e a metade era placed_width_m * 0.5)
        side = slot.get("anchor_side", "right")
        inserted_left_u = slot["u_pos"] - (placed_width_m * 0.5)
        inserted_right_u = slot["u_pos"] + (placed_width_m * 0.5)

        if side == "left":
            # Vinha colado à direita de um móvel: continua para a esquerda do inserido
            new_u = inserted_left_u - half_w
        else:
            # Caso padrão: o próximo módulo começa na quina direita do inserido
            new_u = inserted_right_u + half_w

        slot["anchor_side"] = side

        # Limites da parede para evitar que o frame saia para fora
        xf = getattr(info.wall_group, "xform", None)
        raw_pts = [xf.map(p) if xf is not None else p for p in getattr(info.face, "vertices", [])]
        if raw_pts:
            projs_u = [QVector3D.dotProduct(p, u_dir) for p in raw_pts]
            min_u, max_u = min(projs_u), max(projs_u)
            if new_u - half_w < min_u:
                new_u = min_u + half_w
            if new_u + half_w > max_u:
                new_u = max_u - half_w

        slot["anchor_u"] = new_u - half_w

        c_world = xf.map(info.center) if xf is not None else info.center
        center_u = QVector3D.dotProduct(c_world, u_dir)
        p_frame_wall_center = c_world + u_dir * (new_u - center_u)
        p_frame_wall_center = QVector3D(p_frame_wall_center.x(), p_frame_wall_center.y(), z_b)

        p_bl_back = p_frame_wall_center - u_dir * half_w
        p_br_back = p_frame_wall_center + u_dir * half_w
        p_tl_back = QVector3D(p_bl_back.x(), p_bl_back.y(), z_t)
        p_tr_back = QVector3D(p_br_back.x(), p_br_back.y(), z_t)

        p_bl_front = p_bl_back + n_dir * depth_m
        p_br_front = p_br_back + n_dir * depth_m
        p_tl_front = p_tl_back + n_dir * depth_m
        p_tr_front = p_tr_back + n_dir * depth_m

        slot["u_pos"] = new_u
        slot["center_pt"] = p_frame_wall_center
        slot["box_vertices"] = {
            "bl_back": p_bl_back,
            "br_back": p_br_back,
            "tl_back": p_tl_back,
            "tr_back": p_tr_back,
            "bl_front": p_bl_front,
            "br_front": p_br_front,
            "tl_front": p_tl_front,
            "tr_front": p_tr_front,
        }

        if self.viewport is not None:
            self.viewport.update()

        if hasattr(self.viewport, "flash_status"):
            h_mm = int(slot["height_mm"])
            p_mm = int(slot["default_depth_mm"])
            self.viewport.flash_status(f"🎯 Frame Armado: {slot['label']} — {int(width_m * 1000)}x{p_mm}x{h_mm} mm")

        self.viewport.update()
        return True

    def auto_hide_occluding_walls(self, wall_info: WallFaceInfo) -> None:
        """Oculta automaticamente paredes ou tetos que estejam na frente da parede alvo bloqueando a visao."""
        if self.viewport is None or not hasattr(self.viewport, "scene") or not hasattr(self.viewport, "history"):
            return

        scene = self.viewport.scene
        if not scene:
            return

        from core.history import HideCommand

        # 1. Reexibe previamente quaisquer segmentos de parede que o plugin havia auto-ocultado
        auto_hidden = getattr(self.viewport, "_trazomob_auto_hidden_entities", None)
        if auto_hidden:
            valid_unhide = [ent for ent in auto_hidden if getattr(ent, "hidden", False) or bool(getattr(ent, "attrs", {}).get("hidden"))]
            if valid_unhide:
                self.viewport.history.execute(HideCommand(valid_unhide, hidden=False))
            setattr(self.viewport, "_trazomob_auto_hidden_entities", [])

        # 2. Identifica a geometria da face alvo
        target_pts = getattr(wall_info.face, "vertices", [])
        if not target_pts:
            return

        norm = wall_info.normal
        # Tangente horizontal da parede alvo
        tangent = QVector3D(-norm.y(), norm.x(), 0.0).normalized()
        t_projs = [QVector3D.dotProduct(p, tangent) for p in target_pts]
        t_min = min(t_projs)
        t_max = max(t_projs)

        # Centro da face alvo
        cx = sum(p.x() for p in target_pts) / len(target_pts)
        cy = sum(p.y() for p in target_pts) / len(target_pts)
        cz = sum(p.z() for p in target_pts) / len(target_pts)
        plane_pt = QVector3D(cx, cy, cz)

        entities_to_hide: List[Any] = []

        # 3. Oculta tetos para facilitar a vista aérea/frontal sem obstrução de laje
        for g in getattr(scene, "groups", []):
            ext = getattr(g, "ext", {})
            if isinstance(ext, dict) and ext.get("trazomob_ceiling") and not getattr(g, "hidden", False):
                entities_to_hide.append(g)

        # 4. Analisa paredes na cena para encontrar segmentos na frente
        for g in getattr(scene, "groups", []):
            ext = getattr(g, "ext", {})
            if not isinstance(ext, dict) or "trazomob_wall" not in ext or getattr(g, "hidden", False):
                continue

            params = ext["trazomob_wall"]
            face_map = params.get("face_segment_map", {})
            if not face_map or not hasattr(g, "mesh") or not hasattr(g.mesh, "faces"):
                continue

            # Agrupa faces por segmento
            segs: Dict[int, List[Face]] = {}
            for f_key, s_key in face_map.items():
                try:
                    f_idx = int(f_key)
                    s_idx = int(s_key)
                except (ValueError, TypeError):
                    continue
                if 0 <= f_idx < len(g.mesh.faces):
                    segs.setdefault(s_idx, []).append(g.mesh.faces[f_idx])

            for s_idx, seg_faces in segs.items():
                # Não oculta a própria parede/segmento selecionada
                if g is wall_info.wall_group and s_idx == wall_info.segment_index:
                    continue

                pts_seg = [v for f in seg_faces for v in getattr(f, "vertices", [])]
                if not pts_seg:
                    continue

                # Distâncias de todos os vértices do segmento em relação ao plano da parede alvo (ao longo de norm)
                dists = [QVector3D.dotProduct(p - plane_pt, norm) for p in pts_seg]
                min_d = min(dists)

                # Projeções tangenciais no eixo horizontal
                projs = [QVector3D.dotProduct(p - plane_pt, tangent) for p in pts_seg]
                overlap = not (max(projs) < t_min + 0.10 or min(projs) > t_max - 0.10)

                # Se todos os vértices do segmento estiverem estritamente na frente do plano (min_d > 0.10m)
                # e sobrepõem lateralmente o vão de visão da parede alvo:
                if min_d > 0.10 and overlap:
                    # Coleta as faces deste segmento
                    entities_to_hide.extend([f for f in seg_faces if not f.attrs.get("hidden")])

                    # Coleta arestas órfãs que ficarão sem faces visíveis
                    rem_vis = set(f for f in g.mesh.faces if f not in seg_faces and not f.attrs.get("hidden"))
                    for e in getattr(g.mesh, "edges", []):
                        if any(f in seg_faces for f in e.faces) and not any(f in rem_vis for f in e.faces) and not getattr(e, "hidden", False):
                            entities_to_hide.append(e)

        if entities_to_hide:
            self.viewport.history.execute(HideCommand(entities_to_hide, hidden=True))
            setattr(self.viewport, "_trazomob_auto_hidden_entities", entities_to_hide)
            try:
                from core.history import _dirty_group_chunks
                _dirty_group_chunks(scene)
            except Exception as exc:
                logger.debug("falha ao marcar chunks após ocultar a parede: %s", exc)

    def align_view_to_wall(self, wall_info: Optional[WallFaceInfo] = None, margin: float = 1.2) -> bool:
        """Alinha a camera do viewport perpendicularmente de frente para a face da parede e enquadra o segmento."""
        if wall_info is None:
            self.sync_with_scene(getattr(self.viewport, "scene", None))
        info = wall_info or self.selected_wall_face
        if info is None or self.viewport is None:
            return False

        cam = getattr(self.viewport, "camera", None)
        if cam is None:
            return False

        normal = info.normal
        # Apenas para faces verticais da parede (ignora topo e base se for o caso)
        if abs(normal.z()) > 0.7:
            return False

        # Oculta automaticamente paredes que estejam na frente da parede alvo
        self.auto_hide_occluding_walls(info)

        # Para olhar de frente para a parede:
        # A normal da face da parede sai da parede em direcao ao observador.
        # Portanto, a camera precisa estar na frente e olhar na direcao oposta a normal (-normal).
        # No OrbitCamera do IngeTrazo:
        # eye = target + distance * (cos(pitch)*cos(yaw), cos(pitch)*sin(yaw), sin(pitch))
        # forward = target - eye = - (cos(pitch)*cos(yaw), cos(pitch)*sin(yaw), sin(pitch))
        # Com pitch = 0 (olhar horizontal nivelado):
        # forward = (-cos(yaw), -sin(yaw), 0)
        # Queremos forward = -normal => (cos(yaw), sin(yaw), 0) = (normal.x, normal.y, 0)
        # Logo: yaw = atan2(normal.y, normal.x), pitch = 0.0
        yaw = math.atan2(normal.y(), normal.x())
        pitch = 0.0

        cam.yaw = yaw
        cam.pitch = pitch

        # Enquadra a face da parede no campo de visao
        pts = getattr(info.face, "vertices", [])
        if pts:
            min_pt = QVector3D(
                min(p.x() for p in pts),
                min(p.y() for p in pts),
                min(p.z() for p in pts),
            )
            max_pt = QVector3D(
                max(p.x() for p in pts),
                max(p.y() for p in pts),
                max(p.z() for p in pts),
            )
            if hasattr(cam, "fit_box"):
                cam.fit_box(min_pt, max_pt, margin=margin)
            elif hasattr(cam, "fit_to"):
                cam.fit_to(min_pt, max_pt, margin=margin)
        else:
            cam.target = info.center

        if hasattr(self.viewport, "flash_status"):
            desc_lado = "Face Interna" if info.face_type == "interna" else ("Face Externa" if info.face_type == "externa" else f"Face ({info.face_type})")
            self.viewport.flash_status(f"👁 Vista Frontal: Parede #{info.segment_index + 1} ({desc_lado})")

        self.viewport.update()
        return True

    def handle_double_click(self, px: float, py: float) -> bool:
        """Trata o duplo clique em uma face de parede: seleciona e posiciona a camera de frente."""
        self.sync_with_scene(getattr(self.viewport, "scene", None))
        if self.viewport is None or not hasattr(self.viewport, "pick_face_any"):
            return False

        face, grp = self.viewport.pick_face_any(px, py)
        if grp is not None and hasattr(grp, "ext") and isinstance(grp.ext, dict) and "trazomob_wall" in grp.ext:
            if face is not None:
                info = self.set_selected_face(grp, face)
                if info is not None:
                    return self.align_view_to_wall(info)

        return False

    def handle_click(self, px: float, py: float) -> bool:
        """Tenta selecionar uma face de parede ou, se ja selecionada, armar o frame entre linhas-guia."""
        self.sync_with_scene(getattr(self.viewport, "scene", None))
        if self.viewport is None or not hasattr(self.viewport, "pick_face_any"):
            return False

        face, grp = self.viewport.pick_face_any(px, py)
        if grp is not None and hasattr(grp, "ext") and isinstance(grp.ext, dict) and "trazomob_wall" in grp.ext:
            if face is not None:
                # Se clicou na mesma face ja selecionada, arma o frame 3D na faixa clicada!
                if self.selected_wall_face is not None and self.selected_wall_face.face is face:
                    self.arm_frame_from_click(px, py)
                    return True
                # Caso contrario, seleciona a nova face e arma o frame na faixa clicada
                self.set_selected_face(grp, face)
                self.arm_frame_from_click(px, py)
                return True

        return False

    def draw_selection_overlay(self, vp, painter: QPainter) -> None:
        """Renderiza o destaque visual colorido (highlight) sobre a face de parede selecionada."""
        active_vp = self.viewport
        if vp is not None and active_vp is not None and vp is not active_vp:
            return
        info = self.selected_wall_face
        if info is None or info.face is None:
            return

        # Verifica se a parede ainda existe na cena ou se foi ocultada
        scene = getattr(vp, "scene", None)
        if scene is not None:
            if info.wall_group not in getattr(scene, "groups", []) or getattr(info.wall_group, "hidden", False):
                self.sync_with_scene(scene)
                if getattr(info.wall_group, "hidden", False):
                    self.selected_wall_face = None
                return
            if bool(getattr(info.face, "attrs", {}).get("hidden")):
                self.selected_wall_face = None
                return

        pts_3d = getattr(info.face, "vertices", [])
        if not pts_3d:
            return

        # Aplica a transformação do grupo, se houver
        xf = getattr(info.wall_group, "xform", None)
        raw_pts = [xf.map(p) if xf is not None else p for p in pts_3d]

        # ── BACK-FACE CULLING ROBUSTO ──────────────────────────────────────────
        # Mantém visibilidade consistente em projeção perspectiva/paralela, faces com recortes e xform
        from ..wall.guides import (
            build_wall_occluder_context,
            compute_world_face_normal,
            filter_occluded_segments,
            is_wall_face_visible_to_camera,
        )
        cam = getattr(vp, "camera", None)
        if not is_wall_face_visible_to_camera(cam, raw_pts, info.normal, info.center, xf=xf):
            return

        # Contorno elegante e discreto em amarelo dourado suave
        stroke_color = QColor(217, 160, 40, 200)   # Dourado âmbar suave e refinado
        if info.face_type == "interna":
            stroke_color = QColor(220, 165, 30, 220)  # Amarelo âmbar suave
        elif info.face_type == "externa":
            stroke_color = QColor(190, 150, 45, 200)

        painter.save()
        try:
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.TextAntialiasing, True)

            # 1. O preenchimento da face agora é renderizado nativamente pelo OpenGL (GPU Z-buffer)
            # via face.attrs['color'], respeitando a oclusão física dos móveis e objetos na frente!
            pass

            # 2. Desenha o contorno da face respeitando oclusão física dos objetos em primeiro plano
            pen = QPen(stroke_color, 2.5)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)

            world_norm = compute_world_face_normal(raw_pts, info.normal, xf=xf)
            edge_offset = world_norm * 0.003 if world_norm.lengthSquared() > 1e-10 else None
            occ_ctx = build_wall_occluder_context(vp, info.wall_group)

            n_raw = len(raw_pts)
            for i in range(n_raw):
                pa = raw_pts[i]
                pb = raw_pts[(i + 1) % n_raw]
                for sa, sb in filter_occluded_segments(
                    vp, pa, pb, occ_ctx, step_m=0.12, min_steps=4, max_steps=32, test_offset=edge_offset
                ):
                    seg = vp._clip_segment_front(sa, sb)
                    if seg is not None:
                        s0, s1 = seg
                        px0 = vp.world_to_pixel(s0)
                        px1 = vp.world_to_pixel(s1)
                        if px0 and px1:
                            # Corta para o retângulo da viewport com margem segura
                            vis = vp._clip_pixel_line(px0, px1, margin=32.0)
                            if vis is not None:
                                painter.drawLine(QPointF(*vis[0]), QPointF(*vis[1]))

            # Badge da parede desativado
            # 4. Renderiza as Linhas-Guia da Régua Paramétrica na Face Selecionada
            from ..wall.guides import WallGuideRulerManager
            ruler_mgr = WallGuideRulerManager.get_instance()
            ruler_mgr.draw_ruler_overlay(vp, painter, info, occ_ctx=occ_ctx)

            # 5. Renderiza o Frame 3D se houver slot armado entre guias (respeitando oclusão por primeiro plano)
            if self.active_placement_slot is not None:
                self._draw_placement_frame_overlay(vp, painter, self.active_placement_slot, occ_ctx=occ_ctx)

        finally:
            painter.restore()

    def _draw_placement_frame_overlay(
        self, vp, painter: QPainter, slot: Dict[str, any], occ_ctx: Optional[Dict[str, any]] = None
    ) -> None:
        """Renderiza o volume wireframe translúcido e cotas do frame 3D armado."""
        box = slot.get("box_vertices")
        if not box:
            return

        # 12 arestas do paralelepípedo do frame
        edges = [
            # Base inferior
            (box["bl_back"], box["br_back"]),
            (box["br_back"], box["br_front"]),
            (box["br_front"], box["bl_front"]),
            (box["bl_front"], box["bl_back"]),
            # Topo superior
            (box["tl_back"], box["tr_back"]),
            (box["tr_back"], box["tr_front"]),
            (box["tr_front"], box["tl_front"]),
            (box["tl_front"], box["tl_back"]),
            # 4 colunas verticais
            (box["bl_back"], box["tl_back"]),
            (box["br_back"], box["tr_back"]),
            (box["bl_front"], box["tl_front"]),
            (box["br_front"], box["tr_front"]),
        ]

        # Estilo do frame 3D: ciano/azul elétrico tecnológico vibrante com preenchimento suave
        frame_color = QColor(14, 165, 233, 230)      # Sky blue vibrante
        dash_color = QColor(56, 189, 248, 180)       # Azul claro tracejado
        fill_color = QColor(14, 165, 233, 40)        # Preenchimento translúcido

        from ..wall.guides import _is_point_occluded, filter_occluded_segments

        # 1. Desenha a face frontal translúcida apenas se seu centro não estiver ocluído por objeto à frente
        pts_front = [box["bl_front"], box["br_front"], box["tr_front"], box["tl_front"]]
        front_center = (pts_front[0] + pts_front[2]) * 0.5
        front_occluded = occ_ctx is not None and _is_point_occluded(vp, front_center, occ_ctx)
        if not front_occluded:
            px_front = [vp.world_to_pixel(p) for p in pts_front]
            if all(p is not None for p in px_front):
                poly = QPolygonF([QPointF(p[0], p[1]) for p in px_front])
                painter.setPen(Qt.NoPen)
                painter.setBrush(fill_color)
                painter.drawPolygon(poly)

        # 2. Desenha as 12 arestas wireframe do frame 3D respeitando oclusão por primeiro plano
        pen_solid = QPen(frame_color, 2.0, Qt.SolidLine)
        pen_solid.setJoinStyle(Qt.RoundJoin)
        pen_dash = QPen(dash_color, 1.5, Qt.DashLine)

        for idx, (p0, p1) in enumerate(edges):
            is_back_edge = (idx == 0 or idx == 4 or idx == 8 or idx == 9)
            painter.setPen(pen_dash if is_back_edge else pen_solid)
            for sa, sb in filter_occluded_segments(vp, p0, p1, occ_ctx, step_m=0.12, min_steps=4, max_steps=20):
                seg = vp._clip_segment_front(sa, sb)
                if seg is None:
                    continue
                s0, s1 = seg
                px0 = vp.world_to_pixel(s0)
                px1 = vp.world_to_pixel(s1)
                if px0 and px1:
                    vis = vp._clip_pixel_line(px0, px1, margin=32.0)
                    if vis is not None:
                        painter.drawLine(QPointF(*vis[0]), QPointF(*vis[1]))

        pass
