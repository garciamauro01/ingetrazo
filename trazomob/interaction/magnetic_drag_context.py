# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Contexto de selecao, recupera de modulo e vizinhos para o arraste magnetico."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Tuple

from PySide6.QtGui import QVector3D

from core.group import Group

from .magnetic_drag_snap import get_bounds_min_projection, get_module_reference_bounds

if TYPE_CHECKING:
    from core.mesh import Face


class MagneticDragContextMixin:
    """Contexto de selecao e vizinhos para o arraste magnetico."""

    def _get_selected_module(self) -> Optional[Group]:
        """Retorna o módulo TrazoMob atualmente selecionado na cena, se houver."""
        scene = getattr(self.viewport, "scene", None)
        if not scene:
            return None
        groups = getattr(scene, "groups", None)
        sel = getattr(scene, "selection", set())
        for item in sel:
            mod = self._find_top_module(item)
            if mod is not None and self._is_module_group(mod):
                if groups is None or mod in groups:
                    return mod
        return None

    def _on_scene_or_selection_changed(self, *args) -> None:
        """Atualiza cotas para a seleção atual quando não estiver em drag."""
        if not self._drag_active:
            scene = getattr(self.viewport, "scene", None)
            groups = getattr(scene, "groups", None) if scene is not None else None
            if self._target_module is not None and groups is not None and self._target_module not in groups:
                self._target_module = None
            self._cota_cache_key = None
            self._refresh_active_cotas()
            self.viewport.update()

    def _is_module_group(self, group: Optional[Group]) -> bool:
        if group is None:
            return False
        return bool(
            hasattr(group, "ext")
            and isinstance(group.ext, dict)
            and "trazomob_module" in group.ext
        )

    def _find_top_module(self, group: Optional[Group]) -> Optional[Group]:
        """Encontra o módulo raiz caso o usuário tenha clicado numa peça interna."""
        if group is None:
            return None
        # Se o objeto é uma parede, piso ou está com motion_locked, não deve ser arrastado
        if getattr(group, "motion_locked", False):
            return None
        ext = getattr(group, "ext", None)
        if isinstance(ext, dict):
            if ext.get("motion_locked"):
                return None
            if "trazomob_wall" in ext or "trazomob_floor" in ext:
                return None
        if getattr(group, "layer", "") in ("Parede", "Piso"):
            return None

        if self._is_module_group(group):
            return group

        owner = getattr(group, "owner", None)
        if owner is not None and self._is_module_group(owner):
            return owner

        scene = getattr(self.viewport, "scene", None)
        if scene and hasattr(scene, "groups"):
            for g in scene.groups:
                if self._is_module_group(g):
                    children = getattr(g, "children", []) or []
                    if group in children or getattr(group, "owner", None) is g:
                        return g
        return group if hasattr(group, "mesh") or getattr(group, "xform", None) is not None else None

    def _get_other_modules_bounds(self, exclude_module: Optional[Group] = None, exclude_groups: Optional[List[Group]] = None) -> List[Tuple[Group, Tuple[float, float, float, float, float, float]]]:
        """Retorna [(group, bounds)] dos demais módulos da cena, usando cache durante o arraste."""
        if self._drag_active and getattr(self, "_other_modules_bounds_cache", None) is not None:
            return self._other_modules_bounds_cache
        scene = getattr(self.viewport, "scene", None)
        if not scene or not hasattr(scene, "groups"):
            return []
        affected_set = set(exclude_groups or self._affected_groups or [])
        target_ex = exclude_module or self._target_module
        if target_ex:
            affected_set.add(target_ex)
            for c in getattr(target_ex, "children", []) or []:
                affected_set.add(c)
        res = []
        for g in scene.groups:
            if g in affected_set:
                continue
            if hasattr(g, "ext") and isinstance(g.ext, dict) and "trazomob_module" in g.ext:
                ob = get_module_reference_bounds(g)
                if ob:
                    res.append((g, ob))
        if self._drag_active:
            self._other_modules_bounds_cache = res
        return res

    def _collect_walls(self) -> List[Group]:
        """Retorna todos os grupos de paredes contínuas presentes na cena."""
        walls = []
        scene = getattr(self.viewport, "scene", None)
        if scene and hasattr(scene, "groups"):
            for g in scene.groups:
                if hasattr(g, "ext") and isinstance(g.ext, dict) and "trazomob_wall" in g.ext:
                    walls.append(g)
        return walls

    def _find_adjacent_wall_face(self, module: Group, tolerance_m: float = 0.08) -> Optional[Tuple[Group, Face]]:
        """Verifica se o móvel está encostado ou rente a alguma face de parede na cena."""
        bounds = get_module_reference_bounds(module)
        if not bounds:
            return None
        min_x, max_x, min_y, max_y, min_z, _ = bounds
        cur_bounds = (min_x, max_x, min_y, max_y, min_z, min_z)
        cur_cx, cur_cy = (min_x + max_x) * 0.5, (min_y + max_y) * 0.5
        cur_center = QVector3D(cur_cx, cur_cy, 0.0)

        walls = self._collect_walls()
        best_match = None
        best_gap = float("inf")

        for wall in walls:
            mesh = getattr(wall, "mesh", None)
            if mesh is None or not getattr(mesh, "faces", None):
                continue
            for face in mesh.faces:
                norm = face.normal()
                if abs(norm.z()) > 0.05:
                    continue
                n_dir = QVector3D(norm.x(), norm.y(), 0.0).normalized()
                f_verts = list(face.vertices)
                if len(f_verts) < 2:
                    continue
                p_ref = QVector3D(f_verts[0].x(), f_verts[0].y(), 0.0)

                # A face precisa estar voltada para o móvel
                if QVector3D.dotProduct(cur_center - p_ref, n_dir) < -0.05:
                    continue

                pts_2d = [QVector3D(v.x(), v.y(), 0.0) for v in f_verts]
                u_dir = QVector3D(-n_dir.y(), n_dir.x(), 0.0).normalized()
                projs = [QVector3D.dotProduct(p, u_dir) for p in pts_2d]
                min_u, max_u = min(projs), max(projs)

                proj_u = QVector3D.dotProduct(cur_center, u_dir)
                if not ((min_u - 0.20) <= proj_u <= (max_u + 0.20)):
                    continue

                cur_min_n = get_bounds_min_projection(cur_bounds, n_dir)
                wall_face_n = QVector3D.dotProduct(p_ref, n_dir)
                dist_gap = abs(cur_min_n - wall_face_n)

                if dist_gap <= tolerance_m and dist_gap < best_gap:
                    best_gap = dist_gap
                    best_match = (wall, face)

        return best_match
