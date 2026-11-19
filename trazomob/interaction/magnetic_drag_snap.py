# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Aderencia magnetica, cotas dinamicas e renderizacao de cotas para o arraste de modulos."""

from __future__ import annotations

import logging
import math
from typing import Any, List, Optional, Tuple

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QVector3D

from core.group import Group

from ..domain.snap_contract import (
    SNAP_PAREDE_NENHUM,
    get_module_snap_parede,
    snap_face_target_rotation_deg,
)

logger = logging.getLogger("trazomob.magnetic_drag")


def _extract_esquadria_u_dir(mod: Optional[Group], bounds: Tuple[float, float, float, float, float, float]) -> Optional[QVector3D]:
    """Determina o vetor de direção longitudinal U da esquadria no plano XY."""
    if mod is not None and hasattr(mod, "ext") and isinstance(mod.ext, dict):
        esq_info = mod.ext.get("trazomob_esquadria") or mod.ext.get("trazomob_module") or mod.ext.get("trazomob") or {}
        if isinstance(esq_info, dict) and "rot_z" in esq_info and esq_info["rot_z"] is not None:
            try:
                rad = math.radians(float(esq_info["rot_z"]))
                return QVector3D(math.cos(rad), math.sin(rad), 0.0).normalized()
            except (TypeError, ValueError):
                pass
    dx_b = bounds[1] - bounds[0]
    dy_b = bounds[3] - bounds[2]
    if dx_b >= dy_b * 1.2:
        return QVector3D(1.0, 0.0, 0.0)
    if dy_b >= dx_b * 1.2:
        return QVector3D(0.0, 1.0, 0.0)
    return None


def get_module_bounds(mod: Group) -> Optional[Tuple[float, float, float, float, float, float]]:
    """Calcula os limites AABB do módulo em coordenadas globais (min_x, max_x, min_y, max_y, min_z, max_z)."""
    from ..interaction.align_tools import get_entity_world_bounds
    return get_entity_world_bounds(mod)


def is_esquadria_group(mod: Optional[Group]) -> bool:
    """Identifica se o grupo é uma esquadria (porta ou janela) e não um módulo de marcenaria."""
    if mod is None:
        return False
    ext = getattr(mod, "ext", None)
    if isinstance(ext, dict):
        if "trazomob_esquadria" in ext:
            return True
        for key in ("trazomob", "trazomob_module"):
            info = ext.get(key)
            if isinstance(info, dict):
                if str(info.get("kind", "")) == "esquadria":
                    return True
                if str(info.get("tipo", "")).startswith(("porta_", "janela_")):
                    return True
    return getattr(mod, "layer", "") == "ESQUADRIAS"


def get_module_reference_bounds(mod: Group) -> Optional[Tuple[float, float, float, float, float, float]]:
    """Limites estáveis de posicionamento (marco/caixaria), ignorando peças móveis abertas.

    Ao abrir uma porta ou janela, a folha gira (ou desliza) para fora do plano da parede.
    A AABB total do grupo passaria então a incluir a folha aberta, deslocando o centro
    e a profundidade de referência. Com isso o snap magnético e o recorte do vão na
    parede perdem a posição real do marco e a esquadria "sai" da parede ao ser arrastada.
    Para esquadrias usamos sempre a caixaria/marco como referência (idêntica aberta ou fechada).
    """
    if is_esquadria_group(mod):
        try:
            from ..domain.module_geometry import get_module_carcass_bounds
            carcass = get_module_carcass_bounds(mod)
            if carcass:
                return carcass
        except Exception as exc:
            logger.debug("bounds da caixaria indisponíveis; usando AABB total: %s", exc)
    return get_module_bounds(mod)


def get_bounds_min_projection(bounds: Tuple[float, float, float, float, float, float], direction: QVector3D) -> float:
    """Calcula a projeção mínima da AABB do móvel ao longo de 'direction' de forma instantânea."""
    min_x, max_x, min_y, max_y, _, _ = bounds
    corners = (
        (min_x, min_y),
        (max_x, min_y),
        (min_x, max_y),
        (max_x, max_y),
    )
    dx, dy = direction.x(), direction.y()
    return min(x * dx + y * dy for x, y in corners)


def draw_snap_dimension_segment(
    viewport,
    painter: QPainter,
    p0: QVector3D,
    p1: QVector3D,
    cota_color: QColor = QColor(0, 140, 255),
    offset_px: float = 0.0,
) -> None:
    """Renderiza uma cota interativa completa com setas e etiqueta de milímetros entre dois pontos 3D."""
    dist_m = (p1 - p0).length()
    if math.isnan(dist_m) or math.isinf(dist_m) or dist_m < 0.005:
        return

    p0_px = viewport.world_to_pixel(p0)
    p1_px = viewport.world_to_pixel(p1)
    if p0_px is None or p1_px is None:
        return

    x0, y0 = p0_px
    x1, y1 = p1_px
    if any(math.isnan(v) or math.isinf(v) for v in (x0, y0, x1, y1)):
        return

    dx, dy = x1 - x0, y1 - y0
    screen_len = math.hypot(dx, dy)
    if math.isnan(screen_len) or math.isinf(screen_len) or screen_len < 12.0:
        return

    ux, uy = dx / screen_len, dy / screen_len
    nx, ny = -uy, ux

    cx0, cy0 = x0 + nx * offset_px, y0 + ny * offset_px
    cx1, cy1 = x1 + nx * offset_px, y1 + ny * offset_px

    painter.save()
    try:
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        # 1. Linhas de extensão / testemunhas (se houver deslocamento)
        if abs(offset_px) > 1.0:
            pen_ext = QPen(QColor(120, 140, 160, 160), 1.0, Qt.DashLine)
            painter.setPen(pen_ext)
            painter.drawLine(QPointF(x0, y0), QPointF(cx0 + nx * 3.0, cy0 + ny * 3.0))
            painter.drawLine(QPointF(x1, y1), QPointF(cx1 + nx * 3.0, cy1 + ny * 3.0))

        # 2. Linha principal da cota
        painter.setPen(QPen(cota_color, 1.8))
        painter.drawLine(QPointF(cx0, cy0), QPointF(cx1, cy1))

        # 3. Setas indicadoras nas extremidades
        arrow_len = min(8.0, screen_len * 0.22)
        arrow_w = 3.0
        for tip_x, tip_y, sgn in ((cx0, cy0, 1.0), (cx1, cy1, -1.0)):
            ax = tip_x + (ux * sgn) * arrow_len
            ay = tip_y + (uy * sgn) * arrow_len
            painter.drawLine(QPointF(tip_x, tip_y), QPointF(ax + nx * arrow_w, ay + ny * arrow_w))
            painter.drawLine(QPointF(tip_x, tip_y), QPointF(ax - nx * arrow_w, ay - ny * arrow_w))

        # 4. Etiqueta / Badge com valor nítido em mm
        mm_val = int(round(dist_m * 1000.0))
        texto = f"{mm_val} mm"
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        fm = painter.fontMetrics()
        tw, th = fm.horizontalAdvance(texto), fm.height()

        mid_x, mid_y = (cx0 + cx1) * 0.5, (cy0 + cy1) * 0.5
        pad_x, pad_y = 6, 3
        badge_rect = QRectF(mid_x - tw * 0.5 - pad_x, mid_y - th * 0.5 - pad_y, tw + pad_x * 2, th + pad_y * 2)

        painter.setPen(QPen(cota_color, 1.2))
        painter.setBrush(QColor(24, 28, 36, 220))
        painter.drawRoundedRect(badge_rect, 4.0, 4.0)

        painter.setPen(QColor(255, 255, 255))
        painter.drawText(badge_rect, Qt.AlignCenter, texto)

    finally:
        painter.restore()


_NON_OBSTACLE_LAYERS = frozenset({"Piso", "Teto", "Iluminacao", "Luzes", "Guias", "Parede"})
_NON_OBSTACLE_ROLES = frozenset({"floor", "ceiling", "light", "wall", "guide"})
_TOUCH_MIN_GAP_M = -0.03
_TOUCH_MAX_GAP_M = 0.005
_MIN_CONTACT_OVERLAP_M = 0.01


def _interval_overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    """Comprimento da intersecao entre dois intervalos 1D."""
    return min(a1, b1) - max(a0, b0)


def _polygon_u_intervals_at_z(
    loops_2d: List[List[Tuple[float, float]]],
    z_val: float,
) -> List[Tuple[float, float]]:
    """Retorna intervalos horizontais [u0, u1] solidos da face na cota Z dada."""
    crossings: List[float] = []
    for loop in loops_2d:
        n = len(loop)
        if n < 3:
            continue
        for i in range(n):
            u0, z0 = loop[i]
            u1, z1 = loop[(i + 1) % n]
            if (z0 <= z_val < z1) or (z1 <= z_val < z0):
                crossings.append(u0 + ((z_val - z0) / (z1 - z0)) * (u1 - u0))
    if len(crossings) < 2:
        return []
    crossings.sort()
    return [(crossings[i], crossings[i + 1]) for i in range(0, len(crossings) - 1, 2)]


def _is_group_visible_obstacle(group: Any, affected_set: set) -> bool:
    """Indica se um grupo da cena deve ser considerado obstaculo fisico para cotas."""
    if group in affected_set:
        return False
    if getattr(group, "visible", True) is False or getattr(group, "hidden", False):
        return False
    if getattr(group, "layer", "") in _NON_OBSTACLE_LAYERS:
        return False
    ext = getattr(group, "ext", None)
    if isinstance(ext, dict):
        if any(k in ext for k in ("trazomob_wall", "trazomob_floor", "trazomob_ceiling", "trazomob_light")):
            return False
        if ext.get("trazomob_role") in _NON_OBSTACLE_ROLES:
            return False
        tm_info = ext.get("trazomob")
        if isinstance(tm_info, dict) and tm_info.get("kind") in _NON_OBSTACLE_ROLES:
            return False
    return True


def _extract_vertical_wall_faces(scene: Any, affected_set: set) -> List[dict[str, Any]]:
    """Extrai faces verticais de paredes visiveis em coordenadas de mundo."""
    faces_data: List[dict[str, Any]] = []
    for g in getattr(scene, "groups", []):
        if g in affected_set:
            continue
        if getattr(g, "visible", True) is False or bool(getattr(g, "hidden", False)):
            continue
        ext = getattr(g, "ext", None)
        if not (isinstance(ext, dict) and "trazomob_wall" in ext):
            continue
        mesh = getattr(g, "mesh", None)
        if not mesh or not getattr(mesh, "faces", None):
            continue
        xf = getattr(g, "xform", None)
        has_map_vec = xf is not None and hasattr(xf, "mapVector")
        for face in mesh.faces:
            n_local = face.normal()
            n_world = xf.mapVector(n_local) if has_map_vec else QVector3D(n_local)
            if n_world.lengthSquared() < 1e-10:
                continue
            n_world = n_world.normalized()
            if abs(n_world.z()) > 0.05:
                continue
            raw_verts = list(getattr(face, "vertices", []) or [])
            if len(raw_verts) < 3:
                continue
            verts_w = [xf.map(v) if xf is not None else QVector3D(v) for v in raw_verts]
            u_dir = QVector3D(-n_world.y(), n_world.x(), 0.0)
            if u_dir.lengthSquared() < 1e-10:
                continue
            u_dir = u_dir.normalized()
            loops_2d: List[List[Tuple[float, float]]] = [
                [(QVector3D.dotProduct(v, u_dir), float(v.z())) for v in verts_w]
            ]
            for hole in getattr(face, "holes", None) or []:
                h_pts = list(hole or [])
                if len(h_pts) >= 3:
                    hw = [xf.map(v) if xf is not None else QVector3D(v) for v in h_pts]
                    loops_2d.append([(QVector3D.dotProduct(v, u_dir), float(v.z())) for v in hw])
            zs = [v.z() for v in verts_w]
            faces_data.append({
                "normal": n_world,
                "u_dir": u_dir,
                "plane_pt": QVector3D(verts_w[0].x(), verts_w[0].y(), 0.0),
                "min_z": min(zs),
                "max_z": max(zs),
                "loops_2d": loops_2d,
            })
    return faces_data


def _wall_face_touches_side(
    wf: dict[str, Any],
    d_ray: QVector3D,
    face_pa: QVector3D,
    face_pb: QVector3D,
    mod_min_z: float,
    mod_max_z: float,
) -> bool:
    """Retorna True quando uma face de parede oposta encosta na lateral/fundo dentro da tolerancia."""
    wn: QVector3D = wf["normal"]
    denom = QVector3D.dotProduct(d_ray, wn)
    if denom >= -0.5:
        return False
    z_lo = max(mod_min_z, wf["min_z"])
    z_hi = min(mod_max_z, wf["max_z"])
    if z_hi - z_lo <= _MIN_CONTACT_OVERLAP_M:
        return False

    p_plane = wf["plane_pt"]
    u_dir: QVector3D = wf["u_dir"]
    ta = QVector3D.dotProduct(p_plane - face_pa, wn) / denom
    tb = QVector3D.dotProduct(p_plane - face_pb, wn) / denom
    if max(ta, tb) < _TOUCH_MIN_GAP_M or min(ta, tb) > _TOUCH_MAX_GAP_M:
        return False

    ua = QVector3D.dotProduct(face_pa + d_ray * ta, u_dir)
    ub = QVector3D.dotProduct(face_pb + d_ray * tb, u_dir)
    u_span_lo, u_span_hi = min(ua, ub), max(ua, ub)

    if z_hi - z_lo > 0.02:
        z_samples = (z_lo + 0.005, (z_lo + z_hi) * 0.5, z_hi - 0.005)
    else:
        z_samples = ((z_lo + z_hi) * 0.5,)

    for zs in z_samples:
        for iu0, iu1 in _polygon_u_intervals_at_z(wf["loops_2d"], zs):
            if _interval_overlap(u_span_lo, u_span_hi, iu0, iu1) <= _MIN_CONTACT_OVERLAP_M:
                continue
            ov_mid = 0.5 * (max(u_span_lo, iu0) + min(u_span_hi, iu1))
            if abs(ub - ua) > 1e-6:
                t_mid = ta + ((ov_mid - ua) / (ub - ua)) * (tb - ta)
            else:
                t_mid = 0.5 * (ta + tb)
            if _TOUCH_MIN_GAP_M <= t_mid <= _TOUCH_MAX_GAP_M:
                return True
    return False


class MagneticDragSnapMixin:
    """Aderencia magnetica, snap e cotas dinamicas durante o arraste de modulos."""

    def _draw_cota_overlay(self, vp, painter: QPainter) -> None:
        """Chamado pelo ciclo de desenho do Viewport (_draw_extension_overlays)."""
        if vp is not None and self.viewport is not None and vp is not self.viewport:
            return
        # Se houver preview de m?dulo sendo arrastado da Ribbon (drag & drop), renderiza a caixa fantasma
        drop_info = getattr(self, "_active_drop_preview", None)
        if drop_info:
            from .drag_drop_handler import draw_drop_preview_overlay
            draw_drop_preview_overlay(vp, painter, drop_info)

        sel_mod = self._get_selected_module()
        if not self._drag_active:
            scene = getattr(vp, "scene", None)
            cur_key = (
                getattr(sel_mod, "uid", id(sel_mod)) if sel_mod is not None else None,
                getattr(scene, "version", None),
                getattr(scene, "content_version", None),
            )
            if getattr(self, "_cota_cache_key", None) != cur_key:
                self._refresh_active_cotas(sel_mod)

        for p0, p1, col, offset_px in self._active_cota_items:
            draw_snap_dimension_segment(vp, painter, p0, p1, cota_color=col, offset_px=offset_px)

        # Se houver módulo de Prateleiras Avulsas selecionado, desenha o volume delimitado e as cotas verticais do vão
        if sel_mod and getattr(sel_mod, "ext", None) and isinstance(sel_mod.ext, dict):
            cc_m = sel_mod.ext.get("trazomob_module", {})
            if str(cc_m.get("tipo", "")) == "peca_prateleiras_avulsas":
                self._draw_prateleiras_avulsas_envelope_overlay(vp, painter, sel_mod, cc_m)

    def _draw_prateleiras_avulsas_envelope_overlay(self, vp, painter: QPainter, mod: Group, cc_m: dict[str, Any]) -> None:
        """Renderiza o envelope/volume do vão delimitado e a cota vertical da altura total para Prateleiras Avulsas."""
        L_m = float(cc_m.get("largura", 800.0)) / 1000.0
        A_m = float(cc_m.get("altura", 720.0)) / 1000.0
        P_m = float(cc_m.get("profundidade", 300.0)) / 1000.0
        rot_z = float(cc_m.get("rot_z", 0.0))
        offset = cc_m.get("offset", (0.0, 0.0, 0.0))

        # Se houver filhos, pega a posição mínima para determinar offset real atual (caso tenha sido movido)
        z_min_base = float(offset[2])
        if hasattr(mod, "children") and mod.children:
            all_xs, all_ys, all_zs = [], [], []
            for ch in mod.children:
                m = getattr(ch, "mesh", None)
                if m and getattr(m, "vertices", None):
                    for v in m.vertices:
                        pos = getattr(v, "position", v)
                        all_xs.append(pos.x())
                        all_ys.append(pos.y())
                        all_zs.append(pos.z())
            if all_xs and all_ys and all_zs:
                has_primeira = bool(cc_m.get("has_primeira", False))
                # Se não tem primeira, a primeira chapa física está acima da base
                if has_primeira:
                    z_min_base = min(all_zs)
                else:
                    # offset Z registrado
                    z_min_base = float(offset[2])

        ox, oy, oz = float(offset[0]), float(offset[1]), z_min_base

        local_corners = [
            QVector3D(0.0, 0.0, 0.0),
            QVector3D(L_m, 0.0, 0.0),
            QVector3D(L_m, P_m, 0.0),
            QVector3D(0.0, P_m, 0.0),
            QVector3D(0.0, 0.0, A_m),
            QVector3D(L_m, 0.0, A_m),
            QVector3D(L_m, P_m, A_m),
            QVector3D(0.0, P_m, A_m),
        ]

        rad = math.radians(rot_z)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        off_v = QVector3D(ox, oy, oz)

        world_pts = []
        for c in local_corners:
            rx = c.x() * cos_a - c.y() * sin_a
            ry = c.x() * sin_a + c.y() * cos_a
            world_pts.append(QVector3D(rx, ry, c.z()) + off_v)

        pixel_pts = [vp.world_to_pixel(wp) for wp in world_pts]
        if any(p is None for p in pixel_pts):
            return

        edges = [
            (0, 1), (1, 2), (2, 3), (3, 0),  # base
            (4, 5), (5, 6), (6, 7), (7, 4),  # topo
            (0, 4), (1, 5), (2, 6), (3, 7),  # colunas verticais
        ]

        painter.save()
        try:
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.TextAntialiasing, True)

            # 1. Desenha as arestas do vão delimitado (azul/ciano elegante)
            pen_box = QPen(QColor(14, 165, 233, 210), 1.8, Qt.DashLine)
            painter.setPen(pen_box)
            for i, j in edges:
                p0, p1 = pixel_pts[i], pixel_pts[j]
                painter.drawLine(QPointF(p0[0], p0[1]), QPointF(p1[0], p1[1]))

            # 2. Cota Vertical da Altura do Vão Envolvido (de world_pts[0] até world_pts[4])
            p_base_cota = world_pts[0]
            p_topo_cota = world_pts[4]
            draw_snap_dimension_segment(vp, painter, p_base_cota, p_topo_cota, cota_color=QColor(245, 158, 11), offset_px=24.0)
        finally:
            painter.restore()

    def _refresh_active_cotas(self, target: Optional[Group] = None) -> None:
        """Centraliza o cálculo e atualização das cotas para um módulo ou seleção atual."""
        scene = getattr(self.viewport, "scene", None)
        groups = getattr(scene, "groups", None) if scene is not None else None
        if target is not None and groups is not None and target not in groups:
            target = None
        mod = target if target is not None else self._get_selected_module()
        self._cota_cache_key = (
            getattr(mod, "uid", id(mod)) if mod is not None else None,
            getattr(scene, "version", None) if scene is not None else None,
            getattr(scene, "content_version", None) if scene is not None else None,
        )
        if mod and self._is_module_group(mod) and (groups is None or mod in groups):
            bounds = get_module_reference_bounds(mod)
            if bounds:
                self._active_cota_items = self._compute_cotas_for_bounds(bounds, exclude_module=mod)
                return
        self._active_cota_items = []

    def _compute_magnetic_snap(self, raw_delta: QVector3D, ray_orig: QVector3D, ray_dirc: QVector3D) -> QVector3D:
        """Calcula atração magnética ao piso e às paredes circundantes."""
        if not getattr(self, "snap_enabled", True):
            return raw_delta
        if not self._module_orig_bounds:
            return raw_delta

        min_x, max_x, min_y, max_y, min_z, max_z = self._module_orig_bounds

        # Face de encosto escolhida pelo usuario (metadado do modulo).
        # "nenhum" desliga completamente o snap magnetico desta peca.
        snap_parede = get_module_snap_parede(self._target_module)
        _mod_tipo = str(
            (getattr(self._target_module, "ext", None) or {}).get("trazomob_module", {}).get("tipo", "")
            or (getattr(self._target_module, "ext", None) or {}).get("trazomob", {}).get("tipo", "")
        ).lower()
        if snap_parede == SNAP_PAREDE_NENHUM or _mod_tipo == "bancada_tampao_engrossado":
            self._active_locked_wall_face = None
            self._auto_rot_deg = 0.0
            return raw_delta

        # ── TRATAMENTO ESPECIALIZADO PARA ESQUADRIAS (PORTAS E JANELAS) ──
        # Esquadrias vivem inseridas no plano da parede hospedeira.
        # Seu arraste deve deslizar suavemente e com 100% de liberdade no comprimento da parede (eixo U),
        # mantendo a cota vertical Z estritamente no piso/peitoril e sem sofrer repulsão/penetração normal.
        is_esquadria = False
        if self._target_module and hasattr(self._target_module, "ext") and isinstance(self._target_module.ext, dict):
            name_l = self._target_module.name.lower()
            tm_kind = getattr(self._target_module, "ext", {}).get("trazomob", {}).get("kind", "")
            if "trazomob_esquadria" in self._target_module.ext or tm_kind == "esquadria":
                is_esquadria = True
            elif getattr(self._target_module, "layer", "") == "ESQUADRIAS":
                is_esquadria = True
            elif ("porta" in name_l or "janela" in name_l) and tm_kind != "module" and "roupeiro" not in name_l and "balcao" not in name_l and "armario" not in name_l and "aereo" not in name_l:
                is_esquadria = True

        walls = self._collect_walls()
        if is_esquadria and walls:
            b = self._module_orig_bounds
            c_esq = QVector3D((b[0] + b[1]) * 0.5, (b[2] + b[3]) * 0.5, 0.0)
            esq_u = _extract_esquadria_u_dir(self._target_module, b)
            for w in walls:
                w_ext = getattr(w, "ext", {}).get("trazomob_wall", {})
                if w_ext.get("is_column"):
                    continue
                pts_data = w_ext.get("pontos", [])
                is_closed = w_ext.get("is_closed", False)
                n_pts = len(pts_data)
                n_segs = n_pts if is_closed else max(0, n_pts - 1)
                for seg_i in range(n_segs):
                    p0 = QVector3D(*pts_data[seg_i])
                    p1 = QVector3D(*pts_data[(seg_i + 1) % n_pts])
                    seg_v = p1 - p0
                    seg_len = seg_v.length()
                    if seg_len < 0.05:
                        continue
                    seg_u = seg_v.normalized()
                    if esq_u is not None and abs(QVector3D.dotProduct(esq_u, seg_u)) < 0.80:
                        continue
                    seg_n = QVector3D(-seg_u.y(), seg_u.x(), 0.0).normalized()
                    dist_norm = abs(QVector3D.dotProduct(c_esq - p0, seg_n))
                    wall_esp = float(w_ext.get("espessura", 0.15))
                    if dist_norm <= wall_esp + 0.25:
                        proj_u_center = QVector3D.dotProduct(c_esq - p0, seg_u)
                        if -0.05 <= proj_u_center <= seg_len + 0.05:
                            projs = [
                                QVector3D.dotProduct(QVector3D(b[0], b[2], 0.0) - p0, seg_u),
                                QVector3D.dotProduct(QVector3D(b[1], b[2], 0.0) - p0, seg_u),
                                QVector3D.dotProduct(QVector3D(b[0], b[3], 0.0) - p0, seg_u),
                                QVector3D.dotProduct(QVector3D(b[1], b[3], 0.0) - p0, seg_u),
                            ]
                            u_min_cur, u_max_cur = min(projs), max(projs)
                            half_len = (u_max_cur - u_min_cur) * 0.5
                            center_u_cur = (u_min_cur + u_max_cur) * 0.5

                            cur_delta_u = QVector3D.dotProduct(raw_delta, seg_u)
                            target_center_u = center_u_cur + cur_delta_u
                            clamped_center_u = max(half_len, min(seg_len - half_len, target_center_u))
                            final_delta_u = clamped_center_u - center_u_cur

                            final_delta = seg_u * final_delta_u
                            esq_tipo = str(
                                (self._target_module.ext.get("trazomob_esquadria") or self._target_module.ext.get("trazomob_module") or {}).get("tipo", "")
                            ).lower()
                            is_janela = "janela" in esq_tipo or "janela" in self._target_module.name.lower()
                            if is_janela:
                                w_z_base = float(w_ext.get("z_base", 0.0) or 0.0)
                                w_alt = float(w_ext.get("altura", 2.6) or 2.6)
                                esq_h = max(0.1, b[5] - b[4])
                                target_z = b[4] + raw_delta.z()
                                clamped_z = max(w_z_base, min(w_z_base + w_alt - esq_h, target_z))
                                final_delta.setZ(clamped_z - b[4])
                            else:
                                final_delta.setZ(0.0)

                            # Destaca a parede no gerenciador de paredes para feedback visual
                            from ..wall.selection import WallSelectionManager
                            wall_mgr = WallSelectionManager.get_instance(self.viewport)
                            if w.mesh and w.mesh.faces:
                                for f in w.mesh.faces:
                                    if abs(f.normal().z()) < 0.05:
                                        if wall_mgr.selected_wall_face is None or wall_mgr.selected_wall_face.wall_group is not w:
                                            wall_mgr.set_selected_face(w, f, notify_sidebar=False)
                                        break
                            return final_delta

        cur_min_x = min_x + raw_delta.x()
        cur_max_x = max_x + raw_delta.x()
        cur_min_y = min_y + raw_delta.y()
        cur_max_y = max_y + raw_delta.y()

        final_dx = raw_delta.x()
        final_dy = raw_delta.y()
        final_dz = raw_delta.z()

        walls = self._collect_walls()
        best_wall_face = None
        best_dist = float("inf")
        locked_candidate = None

        # Parede vinculada atualmente (ou parede em que o móvel já estava encostado ao iniciar o clique)
        current_locked_pair = None
        if self._active_locked_wall_face is not None:
            current_locked_pair = (self._active_locked_wall_face[7], self._active_locked_wall_face[8])
        elif getattr(self, "_initial_wall_face", None) is not None:
            current_locked_pair = self._initial_wall_face

        cur_bounds = (cur_min_x, cur_max_x, cur_min_y, cur_max_y, min_z, min_z)
        cur_cx, cur_cy = (cur_min_x + cur_max_x) * 0.5, (cur_min_y + cur_max_y) * 0.5
        cur_center = QVector3D(cur_cx, cur_cy, 0.0)

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

                # Filtra faces curtas de topo/espessura de parede (< 20cm) para não confundir com paredes reais
                pts_2d = [QVector3D(v.x(), v.y(), 0.0) for v in f_verts]
                u_dir = QVector3D(-n_dir.y(), n_dir.x(), 0.0).normalized()
                projs = [QVector3D.dotProduct(p, u_dir) for p in pts_2d]
                min_u, max_u = min(projs), max(projs)
                if (max_u - min_u) < 0.20:
                    continue

                p_ref = QVector3D(f_verts[0].x(), f_verts[0].y(), 0.0)

                # Projeção da AABB atual do móvel (considerando a dimensão efetiva se girar para esta parede)
                # No construtor (rot_z=0), a frente do móvel (portas) aponta para -Y (0, -1, 0) e o fundo para +Y (0, 1, 0).
                # Para que a frente (portas) aponte para dentro do ambiente (+n_dir), rot_z deve ser atan2(ny, nx) + 90°!
                cand_rot_deg = snap_face_target_rotation_deg(n_dir.x(), n_dir.y(), snap_parede)
                orig_rot_cand = 0.0
                if self._target_module and hasattr(self._target_module, "ext") and isinstance(self._target_module.ext, dict):
                    orig_rot_cand = float(self._target_module.ext.get("trazomob_module", {}).get("rot_z", 0.0) or 0.0) % 360.0
                cand_diff_deg = (cand_rot_deg - orig_rot_cand) % 360.0
                if abs(cand_diff_deg - 90.0) < 1.0 or abs(cand_diff_deg - 270.0) < 1.0:
                    hx_c, hy_c = (cur_max_x - cur_min_x) * 0.5, (cur_max_y - cur_min_y) * 0.5
                    eff_cur_bounds = (cur_cx - hy_c, cur_cx + hy_c, cur_cy - hx_c, cur_cy + hx_c, min_z, min_z)
                else:
                    eff_cur_bounds = cur_bounds

                cur_min_n = get_bounds_min_projection(eff_cur_bounds, n_dir)
                wall_face_n = QVector3D.dotProduct(p_ref, n_dir)
                dist_gap = cur_min_n - wall_face_n
                proj_u = QVector3D.dotProduct(cur_center, u_dir)

                # Raio mirando diretamente na parede (denom < 0 indica que a normal da face aponta em direção à câmera!)
                denom = QVector3D.dotProduct(ray_dirc, n_dir)
                # Ignora a face traseira/externa da parede quando ela está de costas para a câmera (denom > 0.02)
                if denom > 0.02:
                    continue

                ray_hits_wall = False
                hit_wall_z = 0.0
                hit_wall_u = 0.0
                hit_pt_2d = None
                if denom < -1e-4:
                    t_wall = QVector3D.dotProduct(p_ref - ray_orig, n_dir) / denom
                    if 0.0 < t_wall < 30.0:
                        hit_pt = ray_orig + ray_dirc * t_wall
                        hit_u = QVector3D.dotProduct(hit_pt, u_dir)
                        if (min_u - 0.15) <= hit_u <= (max_u + 0.15) and 0.0 <= hit_pt.z() <= 3.5:
                            ray_hits_wall = True
                            hit_wall_z = hit_pt.z()
                            hit_wall_u = hit_u
                            hit_pt_2d = QVector3D(hit_pt.x(), hit_pt.y(), 0.0)

                cand_tuple = (
                    n_dir, u_dir, wall_face_n, cur_min_n,
                    ray_hits_wall, hit_wall_z, hit_wall_u,
                    wall, face, dist_gap, min_u, max_u,
                )

                if current_locked_pair is not None and wall is current_locked_pair[0] and face is current_locked_pair[1]:
                    locked_candidate = cand_tuple

                # Distância normal da caixa à face da parede:
                # Só considera a parede se o móvel estiver próximo da frente da face (-0.30m <= dist_gap < SNAP_WALL_DISTANCE)
                # ou se o raio do cursor estiver apontando diretamente na parede dentro da área útil da face.
                is_near_front = (-0.30 <= dist_gap < self.SNAP_WALL_DISTANCE)
                is_in_bounds_u = ((min_u - 0.15) <= proj_u <= (max_u + 0.15))

                # Se o raio do mouse atinge diretamente a face interna da parede (ray_hits_wall),
                # o ponto na parede (hit_pt_2d) já está dentro dos limites U e Z da parede!
                ray_near_cur = (
                    ray_hits_wall
                    and hit_pt_2d is not None
                    and -2.50 <= dist_gap <= 1.20
                )

                if (is_in_bounds_u and is_near_front) or ray_near_cur:
                    # Quando o cursor aponta diretamente para a face da parede, prioriza a distância da câmera até o impacto
                    rank_dist = abs(dist_gap) * 0.25 if ray_near_cur else abs(dist_gap)
                    if rank_dist < best_dist:
                        best_dist = rank_dist
                        best_wall_face = cand_tuple

        # Se o móvel já estava vinculado a uma parede ativa, ele permanece nela ao deslizar para a esquerda ou direita
        # (evitando que troque de parede sozinho ao encostar no canto da parede perpendicular!).
        # Só permite trocar para outra parede (ou soltar da parede) se o usuário afastar o móvel perpendicularmente
        # da parede ativa (l_dist_gap > SNAP_WALL_DISTANCE, ou > 0.20m quando mirando diretamente na outra parede)!
        if locked_candidate is not None:
            l_n_dir, l_u_dir, l_wall_face_n, l_cur_min_n, l_ray_hits, l_hit_z, l_hit_u, l_wall, l_face, l_dist_gap, l_min_u, l_max_u = locked_candidate
            pointing_at_other_wall = (
                best_wall_face is not None
                and (best_wall_face[7] is not l_wall or best_wall_face[8] is not l_face)
                and best_wall_face[4]  # ray_hits_wall na outra parede
                and l_dist_gap > 0.20  # puxou pelo menos 20cm para fora da parede atual
            )
            if l_dist_gap <= self.SNAP_WALL_DISTANCE and not pointing_at_other_wall:
                best_wall_face = locked_candidate

        # 2. Aplica Aderência Magnética e Bloqueio à Parede Selecionada
        if best_wall_face is not None:
            n_dir, u_dir, wall_face_n, cur_min_n, ray_hits_wall, hit_wall_z, hit_wall_u, matched_wall, matched_face, dist_gap, min_u, max_u = best_wall_face

            # Verifica se o móvel trocou de face de parede durante o arraste!
            prev_locked = self._active_locked_wall_face
            wall_changed = (
                prev_locked is None
                or prev_locked[7] is not matched_wall
                or prev_locked[8] is not matched_face
            )
            self._active_locked_wall_face = best_wall_face

            if wall_changed:
                # Recalcula a referência U/Z na NOVA parede a partir do estado atual para evitar saltos bruscos!
                self._press_wall_u = QVector3D.dotProduct(self._start_world_pt, u_dir)
                cur_dz = self._current_delta.z() if isinstance(getattr(self, "_current_delta", None), QVector3D) else 0.0
                self._press_wall_z = (hit_wall_z - cur_dz) if ray_hits_wall else None

            # Auto-rotação inteligente ao encostar em outra parede.
            # A face escolhida em `snap_parede` fica voltada para a parede.
            target_rot_deg = snap_face_target_rotation_deg(n_dir.x(), n_dir.y(), snap_parede)
            orig_rot_deg = 0.0
            if self._target_module and hasattr(self._target_module, "ext") and isinstance(self._target_module.ext, dict):
                orig_rot_deg = float(self._target_module.ext.get("trazomob_module", {}).get("rot_z", 0.0) or 0.0) % 360.0
            self._auto_rot_deg = (target_rot_deg - orig_rot_deg) % 360.0

            # Destaca visualmente a face da parede sem roubar a seleção do móvel nem trocar o painel lateral!
            from ..wall.selection import WallSelectionManager
            wall_mgr = WallSelectionManager.get_instance(self.viewport)
            if wall_mgr.selected_wall_face is None or wall_mgr.selected_wall_face.wall_group is not matched_wall or wall_mgr.selected_wall_face.face is not matched_face:
                wall_mgr.set_selected_face(matched_wall, matched_face, notify_sidebar=False)

            if self._press_wall_u is None:
                self._press_wall_u = QVector3D.dotProduct(self._start_world_pt, u_dir)
            if self._press_wall_z is None and ray_hits_wall:
                cur_dz = self._current_delta.z() if isinstance(getattr(self, "_current_delta", None), QVector3D) else 0.0
                self._press_wall_z = hit_wall_z - cur_dz

            # Dimensionamento efetivo da caixa após eventual auto-rotação de 90°/270°
            rot_swap = abs(self._auto_rot_deg - 90.0) < 1.0 or abs(self._auto_rot_deg - 270.0) < 1.0
            if rot_swap:
                cx_o, cy_o = (min_x + max_x) * 0.5, (min_y + max_y) * 0.5
                hx_o, hy_o = (max_x - min_x) * 0.5, (max_y - min_y) * 0.5
                eff_bounds = (cx_o - hy_o, cx_o + hy_o, cy_o - hx_o, cy_o + hx_o, min_z, max_z)
            else:
                eff_bounds = (min_x, max_x, min_y, max_y, min_z, max_z)

            cur_mod_corners = [
                (eff_bounds[0], eff_bounds[2]), (eff_bounds[1], eff_bounds[2]),
                (eff_bounds[0], eff_bounds[3]), (eff_bounds[1], eff_bounds[3]),
            ]
            cur_mod_projs_u = [x * u_dir.x() + y * u_dir.y() for x, y in cur_mod_corners]
            cur_mod_center_u = (min(cur_mod_projs_u) + max(cur_mod_projs_u)) * 0.5
            half_len_u = (max(cur_mod_projs_u) - min(cur_mod_projs_u)) * 0.5

            # Usa o deslocamento projetado ao longo de u_dir para continuidade suave entre piso e parede
            orig_center_u = cur_mod_center_u
            cur_delta_u = QVector3D.dotProduct(raw_delta, u_dir)
            if ray_hits_wall and self._press_wall_z is not None:
                raw_dz = hit_wall_z - self._press_wall_z
            else:
                raw_dz = raw_delta.z()
            candidate_dz = raw_dz if (min_z + raw_dz) > self.SNAP_FLOOR_DISTANCE else -min_z

            # Limita o deslizamento U estritamente aos limites físicos da parede [min_u, max_u]
            # descontando a meia-largura do próprio móvel (half_len_u), para que nenhuma das laterais
            # do móvel ultrapasse a parede ou entre dentro das paredes laterais!
            target_center_u = orig_center_u + cur_delta_u
            allowed_min_center_u = min_u + half_len_u
            allowed_max_center_u = max_u - half_len_u
            if allowed_min_center_u <= allowed_max_center_u:
                clamped_center_u = max(allowed_min_center_u, min(allowed_max_center_u, target_center_u))
            else:
                clamped_center_u = (min_u + max_u) * 0.5
            cur_delta_u = clamped_center_u - orig_center_u

            # ── SNAP MAGNÉTICO ÀS LINHAS-GUIA DA RÉGUA DE ALTURA ──
            # Regra de negócio estrita: esquadrias (portas e janelas) NÃO devem sofrer alinhamento
            # ou atração magnética das réguas-guia de marcenaria.
            is_esquadria = False
            if self._target_module and hasattr(self._target_module, "ext") and isinstance(self._target_module.ext, dict):
                if "trazomob_esquadria" in self._target_module.ext:
                    is_esquadria = True
                elif getattr(self._target_module, "layer", "") == "ESQUADRIAS":
                    is_esquadria = True
                elif "porta" in self._target_module.name.lower() or "janela" in self._target_module.name.lower():
                    is_esquadria = True

            from ..wall.guides import WallGuideRulerManager
            ruler_mgr = WallGuideRulerManager.get_instance()
            cur_world_bottom_z = min_z + candidate_dz
            cur_world_top_z = max_z + candidate_dz

            # Checa atração magnética na base e no topo do móvel (apenas para módulos de marcenaria)
            snap_bottom = None if is_esquadria else ruler_mgr.snap_to_levels(cur_world_bottom_z, threshold_m=0.10)
            snap_top = None if is_esquadria else ruler_mgr.snap_to_levels(cur_world_top_z, threshold_m=0.10)

            mod_height = max_z - min_z

            # Escolhe o snap adequado:
            chosen_snap = None
            if snap_bottom is not None and snap_top is not None:
                diff_b = getattr(snap_bottom, "diff", abs(cur_world_bottom_z - snap_bottom[0]))
                diff_t = getattr(snap_top, "diff", abs(cur_world_top_z - snap_top[0]))

                # Para móveis altos (balcões/armários de h > 20cm) próximos à região inferior (Z <= 0.40m),
                # a intenção do usuário ao arrastar próximo da base é o rodapé/base, não a bancada superior.
                if mod_height > 0.20 and cur_world_bottom_z <= 0.40:
                    chosen_snap = ("bottom", snap_bottom)
                # Para peças delgadas (tampos, prateleiras, bancadas com h <= 20cm), escolhe o que estiver mais próximo
                elif diff_t < diff_b:
                    chosen_snap = ("top", snap_top)
                else:
                    chosen_snap = ("bottom", snap_bottom)
            elif snap_top is not None:
                chosen_snap = ("top", snap_top)
            elif snap_bottom is not None:
                chosen_snap = ("bottom", snap_bottom)

            if chosen_snap is not None:
                mode, s_info = chosen_snap
                snapped_z = s_info[0]
                guide_name = s_info[1]
                if mode == "top":
                    final_dz = snapped_z - max_z
                else:
                    final_dz = snapped_z - min_z
            else:
                final_dz = candidate_dz

            # ── SNAP MAGNÉTICO CONTÍGUO A OUTROS MÓDULOS NA MESMA PAREDE (EIXO U) ──
            other_modules_with_bounds = self._get_other_modules_bounds()

            best_snap_u_offset = None
            min_snap_u_dist = 0.12  # Raio de atração magnética de 12 cm (120 mm)

            for om, ob in other_modules_with_bounds:
                # Verifica se o outro módulo está na mesma parede (distância normal próxima)
                ob_min_n = get_bounds_min_projection(ob, n_dir)
                if abs(ob_min_n - wall_face_n) > 0.15:
                    continue

                # Checa sobreposição ou proximidade no eixo vertical Z
                # Para grudar lateralmente, deve ter alguma compatibilidade vertical
                if (max_z + final_dz) < (ob[4] - 0.20) or (min_z + final_dz) > (ob[5] + 0.20):
                    continue

                # Limites U do módulo vizinho
                o_pts = [
                    (ob[0], ob[2]), (ob[1], ob[2]),
                    (ob[0], ob[3]), (ob[1], ob[3]),
                ]
                o_projs_u = [x * u_dir.x() + y * u_dir.y() for x, y in o_pts]
                o_min_u, o_max_u = min(o_projs_u), max(o_projs_u)

                # Casos de snap contíguo ao longo de U (somente se couber dentro dos limites da parede [min_u, max_u]):
                snap_right_u = (o_max_u + half_len_u) - cur_mod_center_u
                if allowed_min_center_u - 1e-4 <= (orig_center_u + snap_right_u) <= allowed_max_center_u + 1e-4:
                    dist_right = abs(cur_delta_u - snap_right_u)
                    if dist_right < min_snap_u_dist:
                        min_snap_u_dist = dist_right
                        best_snap_u_offset = snap_right_u

                snap_left_u = (o_min_u - half_len_u) - cur_mod_center_u
                if allowed_min_center_u - 1e-4 <= (orig_center_u + snap_left_u) <= allowed_max_center_u + 1e-4:
                    dist_left = abs(cur_delta_u - snap_left_u)
                    if dist_left < min_snap_u_dist:
                        min_snap_u_dist = dist_left
                        best_snap_u_offset = snap_left_u

                # Snap de alinhamento vertical Z com o módulo vizinho (se não houver snap de régua ativo)
                if snap_bottom is None and snap_top is None:
                    if abs((min_z + final_dz) - ob[4]) < 0.08:
                        final_dz = ob[4] - min_z
                    elif abs((max_z + final_dz) - ob[5]) < 0.08:
                        final_dz = ob[5] - max_z

            if best_snap_u_offset is not None:
                cur_delta_u = best_snap_u_offset

            # Reaplica o clamp de segurança após qualquer snap lateral para garantir que o móvel NUNCA ultrapasse os limites da parede!
            if allowed_min_center_u <= allowed_max_center_u:
                cur_delta_u = max(allowed_min_center_u - orig_center_u, min(allowed_max_center_u - orig_center_u, cur_delta_u))

            # ── BLOQUEIO FÍSICO CONTRA PENETRAÇÃO NA PAREDE ──
            orig_min_n = get_bounds_min_projection(eff_bounds, n_dir)
            snap_delta_n = wall_face_n - orig_min_n

            # Componente normal do movimento do mouse
            raw_delta_n = QVector3D.dotProduct(raw_delta, n_dir)

            # Se o cursor do mouse estiver mais afastado para dentro do cômodo do que a parede E não estiver mirando na parede:
            if not ray_hits_wall and raw_delta_n > (snap_delta_n + self.SNAP_WALL_DISTANCE):
                # Puxou claramente para longe da parede, solta o travamento
                self._active_locked_wall_face = None
                self._initial_wall_face = None
                self._auto_rot_deg = 0.0
                final_delta_xy = raw_delta
            else:
                # ── AMARRAÇÃO DIRETA AO PLANO DA PAREDE ──
                final_delta_xy = u_dir * cur_delta_u + n_dir * snap_delta_n

            final_dx = final_delta_xy.x()
            final_dy = final_delta_xy.y()
        else:
            self._active_locked_wall_face = None
            self._auto_rot_deg = 0.0
            final_dz = -min_z
            # Se não estiver preso a uma parede, ainda podemos atrair em X e Y para módulos vizinhos livres
            other_modules_with_bounds = self._get_other_modules_bounds()

            cur_min_x_cand = min_x + final_dx
            cur_max_x_cand = max_x + final_dx
            cur_min_y_cand = min_y + final_dy
            cur_max_y_cand = max_y + final_dy
            snap_dist_free = 0.10

            for om, ob in other_modules_with_bounds:
                # Snap X (lateral esquerda/direita)
                if abs(cur_min_x_cand - ob[1]) < snap_dist_free:
                    final_dx = ob[1] - min_x
                elif abs(cur_max_x_cand - ob[0]) < snap_dist_free:
                    final_dx = ob[0] - max_x

                # Snap Y (frente/costas)
                if abs(cur_min_y_cand - ob[3]) < snap_dist_free:
                    final_dy = ob[3] - min_y
                elif abs(cur_max_y_cand - ob[2]) < snap_dist_free:
                    final_dy = ob[2] - max_y

        # ── TRAVA DE EIXOS VIA SETINHAS DO TECLADO (Arrow Keys Lock) ──
        if self._axis_lock == "z":
            # Trava estrita em Z: cancela movimento horizontal (X e Y)
            final_dx = 0.0
            final_dy = 0.0
        elif self._axis_lock == "u":
            # Trava estrita no plano horizontal: cancela movimento vertical (Z)
            final_dz = 0.0

        return QVector3D(final_dx, final_dy, final_dz)

    def _compute_cotas_for_bounds(
        self,
        bounds: Tuple[float, float, float, float, float, float],
        exclude_module: Optional[Group] = None,
        exclude_groups: Optional[List[Group]] = None,
    ) -> List[Tuple[QVector3D, QVector3D, QColor, float]]:
        if any(not math.isfinite(v) for v in bounds):
            return []

        scene = getattr(self.viewport, "scene", None)
        if scene is None:
            return []

        # ── CASO ESPECIAL: COTAS PROJETADAS PARA ESQUADRIAS (PORTAS E JANELAS) ──
        # Projeta a distância exata em mm até a quina esquerda e direita da parede hospedeira
        is_esquadria = False
        target_mod = exclude_module or self._target_module
        if target_mod and hasattr(target_mod, "ext") and isinstance(target_mod.ext, dict):
            _t_name = target_mod.name.lower() if hasattr(target_mod, "name") else ""
            _t_kind = target_mod.ext.get("trazomob", {}).get("kind", "")
            if "trazomob_esquadria" in target_mod.ext or _t_kind == "esquadria" or getattr(target_mod, "layer", "") == "ESQUADRIAS":
                is_esquadria = True
            elif ("porta" in _t_name or "janela" in _t_name) and _t_kind != "module" and "roupeiro" not in _t_name and "balcao" not in _t_name and "armario" not in _t_name and "aereo" not in _t_name:
                is_esquadria = True

        if is_esquadria:
            b = bounds
            c_esq = QVector3D((b[0] + b[1]) * 0.5, (b[2] + b[3]) * 0.5, 0.0)
            esq_u = _extract_esquadria_u_dir(target_mod, b)
            for g in scene.groups:
                if not (hasattr(g, "ext") and isinstance(g.ext, dict) and "trazomob_wall" in g.ext):
                    continue
                w_ext = g.ext["trazomob_wall"]
                if w_ext.get("is_column"):
                    continue
                pts_data = w_ext.get("pontos", [])
                is_closed = w_ext.get("is_closed", False)
                n_pts = len(pts_data)
                n_segs = n_pts if is_closed else max(0, n_pts - 1)
                for seg_i in range(n_segs):
                    p0 = QVector3D(*pts_data[seg_i])
                    p1 = QVector3D(*pts_data[(seg_i + 1) % n_pts])
                    seg_v = p1 - p0
                    seg_len = seg_v.length()
                    if seg_len < 0.05:
                        continue
                    seg_u = seg_v.normalized()
                    if esq_u is not None and abs(QVector3D.dotProduct(esq_u, seg_u)) < 0.80:
                        continue
                    seg_n = QVector3D(-seg_u.y(), seg_u.x(), 0.0).normalized()
                    dist_norm = abs(QVector3D.dotProduct(c_esq - p0, seg_n))
                    wall_esp = float(w_ext.get("espessura", 0.15))
                    if dist_norm <= wall_esp + 0.25:
                        proj_c = QVector3D.dotProduct(c_esq - p0, seg_u)
                        if not (-0.05 <= proj_c <= seg_len + 0.05):
                            continue
                        projs = [
                            QVector3D.dotProduct(QVector3D(b[0], b[2], 0.0) - p0, seg_u),
                            QVector3D.dotProduct(QVector3D(b[1], b[2], 0.0) - p0, seg_u),
                            QVector3D.dotProduct(QVector3D(b[0], b[3], 0.0) - p0, seg_u),
                            QVector3D.dotProduct(QVector3D(b[1], b[3], 0.0) - p0, seg_u),
                        ]
                        u_min = min(projs)
                        u_max = max(projs)
                        z_cota = b[4] + 0.15
                        cota_offset_n = seg_n * (wall_esp * 0.5 + 0.04)

                        esq_cotas = []
                        # Cota Esquerda (da quina esquerda da parede p0 até a lateral da esquadria)
                        p_wall_esq = p0 + cota_offset_n
                        p_wall_esq.setZ(z_cota)
                        p_door_esq = p0 + seg_u * u_min + cota_offset_n
                        p_door_esq.setZ(z_cota)
                        d_esq = (p_door_esq - p_wall_esq).length()
                        if d_esq > 0.01:
                            col_esq = QColor(0, 140, 255) if d_esq > 0.05 else QColor(0, 210, 120)
                            esq_cotas.append((p_wall_esq, p_door_esq, col_esq, 0.0))

                        # Cota Direita (da lateral da esquadria até a quina direita da parede p1)
                        p_door_dir = p0 + seg_u * u_max + cota_offset_n
                        p_door_dir.setZ(z_cota)
                        p_wall_dir = p1 + cota_offset_n
                        p_wall_dir.setZ(z_cota)
                        d_dir = (p_wall_dir - p_door_dir).length()
                        if d_dir > 0.01:
                            col_dir = QColor(0, 140, 255) if d_dir > 0.05 else QColor(0, 210, 120)
                            esq_cotas.append((p_door_dir, p_wall_dir, col_dir, 0.0))

                        # Janelas (peitoril > 0): cotas verticais piso→peitoril e verga→topo da parede
                        z_base = b[4]
                        z_top = b[5]
                        if z_base > 0.05:
                            alt_w = w_ext.get("altura", 2.6)
                            if isinstance(alt_w, (list, tuple)):
                                alt_w = alt_w[seg_i] if seg_i < len(alt_w) else (alt_w[-1] if alt_w else 2.6)
                            try:
                                h_wall = float(alt_w)
                            except (TypeError, ValueError):
                                h_wall = 2.6
                            p_ref = p0 + seg_u * u_min + cota_offset_n - seg_u * 0.10
                            col_v = QColor(0, 140, 255)
                            # Peitoril (piso até a base da janela)
                            p_floor = QVector3D(p_ref.x(), p_ref.y(), 0.0)
                            p_sill = QVector3D(p_ref.x(), p_ref.y(), z_base)
                            esq_cotas.append((p_floor, p_sill, col_v, 0.0))
                            # Altura da janela (base até a verga)
                            p_head = QVector3D(p_ref.x(), p_ref.y(), z_top)
                            esq_cotas.append((p_sill, p_head, QColor(0, 210, 120), 0.0))
                            # Verga até o topo da parede
                            if h_wall > z_top + 0.01:
                                p_wtop = QVector3D(p_ref.x(), p_ref.y(), h_wall)
                                esq_cotas.append((p_head, p_wtop, col_v, 0.0))

                        return esq_cotas

        cur_min_x, cur_max_x, cur_min_y, cur_max_y, cur_min_z, cur_max_z = bounds
        center_x = (cur_min_x + cur_max_x) * 0.5
        center_y = (cur_min_y + cur_max_y) * 0.5
        center_z = (cur_min_z + cur_max_z) * 0.5

        scene = getattr(self.viewport, "scene", None)
        if scene is None:
            return []

        module_bounds_pairs = self._get_other_modules_bounds(
            exclude_module=exclude_module,
            exclude_groups=exclude_groups,
        )
        obstacle_bounds: List[Tuple[float, float, float, float, float, float]] = [
            ob for _om, ob in module_bounds_pairs
        ]

        affected_set = set(exclude_groups or [])
        for eg in list(affected_set):
            for c in getattr(eg, "children", []) or []:
                affected_set.add(c)
        if exclude_module:
            affected_set.add(exclude_module)
            for c in getattr(exclude_module, "children", []) or []:
                affected_set.add(c)
        seen_mods = {om for om, _ob in module_bounds_pairs}

        for g in getattr(scene, "groups", []):
            if g in seen_mods or not _is_group_visible_obstacle(g, affected_set):
                continue
            ob = get_module_reference_bounds(g)
            if ob is not None:
                obstacle_bounds.append(ob)

        wall_faces = _extract_vertical_wall_faces(scene, affected_set)

        cota_items = []

        # Determina a orientação/face traseira do módulo para posicionar as cotas
        # rente ao fundo (5 a 10 mm avançado da traseira) em vez de no meio do móvel
        rot_deg = 0.0
        if exclude_module and hasattr(exclude_module, "ext") and isinstance(exclude_module.ext, dict):
            cc_dict = exclude_module.ext.get("trazomob_module", {})
            rot_deg = float(cc_dict.get("rot_z", 0.0)) % 360.0

        # Posição de amostragem no plano horizontal:
        # No construtor (rot 0): frente é -Y, fundo é +Y. Avanço de 10 mm para dentro = cur_max_y - 0.010
        # Se rot 180: fundo é -Y -> cur_min_y + 0.010
        # Se rot 90: fundo é -X -> cur_min_x + 0.010
        # Se rot 270: fundo é +X -> cur_max_x - 0.010
        if abs(rot_deg) < 45.0 or abs(rot_deg - 360.0) < 45.0:
            cota_x = center_x
            cota_y = cur_max_y - 0.010
        elif abs(rot_deg - 180.0) < 45.0:
            cota_x = center_x
            cota_y = cur_min_y + 0.010
        elif abs(rot_deg - 90.0) < 45.0:
            cota_x = cur_min_x + 0.010
            cota_y = center_y
        elif abs(rot_deg - 270.0) < 45.0:
            cota_x = cur_max_x - 0.010
            cota_y = center_y
        else:
            cota_x = center_x
            cota_y = cur_max_y - 0.010

        cardinal_specs = [
            (
                "right",
                QVector3D(cur_max_x, cota_y, center_z),
                QVector3D(1, 0, 0),
                QVector3D(cur_max_x, cur_min_y, 0.0),
                QVector3D(cur_max_x, cur_max_y, 0.0),
            ),
            (
                "left",
                QVector3D(cur_min_x, cota_y, center_z),
                QVector3D(-1, 0, 0),
                QVector3D(cur_min_x, cur_min_y, 0.0),
                QVector3D(cur_min_x, cur_max_y, 0.0),
            ),
            (
                "front",
                QVector3D(cota_x, cur_max_y, center_z),
                QVector3D(0, 1, 0),
                QVector3D(cur_min_x, cur_max_y, 0.0),
                QVector3D(cur_max_x, cur_max_y, 0.0),
            ),
            (
                "rear",
                QVector3D(cota_x, cur_min_y, center_z),
                QVector3D(0, -1, 0),
                QVector3D(cur_min_x, cur_min_y, 0.0),
                QVector3D(cur_max_x, cur_min_y, 0.0),
            ),
        ]

        for name, p_start, d_ray, face_pa, face_pb in cardinal_specs:
            # Se esta face do modulo estiver encostada em parede, outro modulo ou superficie solida, oculta a cota
            is_touching = False
            for ob in obstacle_bounds:
                om_min_x, om_max_x, om_min_y, om_max_y, om_min_z, om_max_z = ob
                if _interval_overlap(cur_min_z, cur_max_z, om_min_z, om_max_z) <= _MIN_CONTACT_OVERLAP_M:
                    continue
                if name in ("right", "left"):
                    if _interval_overlap(cur_min_y, cur_max_y, om_min_y, om_max_y) <= _MIN_CONTACT_OVERLAP_M:
                        continue
                    gap = (om_min_x - cur_max_x) if name == "right" else (cur_min_x - om_max_x)
                else:
                    if _interval_overlap(cur_min_x, cur_max_x, om_min_x, om_max_x) <= _MIN_CONTACT_OVERLAP_M:
                        continue
                    gap = (om_min_y - cur_max_y) if name == "front" else (cur_min_y - om_max_y)
                if _TOUCH_MIN_GAP_M <= gap <= _TOUCH_MAX_GAP_M:
                    is_touching = True
                    break

            if not is_touching:
                for wf in wall_faces:
                    if _wall_face_touches_side(wf, d_ray, face_pa, face_pb, cur_min_z, cur_max_z):
                        is_touching = True
                        break

            if is_touching:
                continue

            best_t = float("inf")
            best_hit_pt = None

            # 1. Colisão com paredes contínuas (na altura center_z)
            for wf in wall_faces:
                wn = wf["normal"]
                denom = QVector3D.dotProduct(d_ray, wn)
                if denom >= -0.05:
                    continue
                if not (wf["min_z"] <= center_z <= wf["max_z"]):
                    continue
                t = QVector3D.dotProduct(wf["plane_pt"] - p_start, wn) / denom
                if _TOUCH_MAX_GAP_M < t < best_t:
                    u_hit = QVector3D.dotProduct(p_start + d_ray * t, wf["u_dir"])
                    intervals = _polygon_u_intervals_at_z(wf["loops_2d"], center_z)
                    if any((iu0 - 1e-4) <= u_hit <= (iu1 + 1e-4) for iu0, iu1 in intervals):
                        best_t = t
                        best_hit_pt = p_start + d_ray * t

            # 2. Colisão com outros módulos / superfícies AABB (busca unificada e compacta)
            for om_min_x, om_max_x, om_min_y, om_max_y, om_min_z, om_max_z in obstacle_bounds:
                if _interval_overlap(cur_min_z, cur_max_z, om_min_z, om_max_z) <= _MIN_CONTACT_OVERLAP_M:
                    continue

                t = None
                if name == "right" and om_min_x > cur_max_x and om_min_y <= cota_y <= om_max_y:
                    t = om_min_x - cur_max_x
                elif name == "left" and om_max_x < cur_min_x and om_min_y <= cota_y <= om_max_y:
                    t = cur_min_x - om_max_x
                elif name == "front" and om_min_y > cur_max_y and om_min_x <= cota_x <= om_max_x:
                    t = om_min_y - cur_max_y
                elif name == "rear" and om_max_y < cur_min_y and om_min_x <= cota_x <= om_max_x:
                    t = cur_min_y - om_max_y

                if t is not None and _TOUCH_MAX_GAP_M < t < best_t:
                    best_t = t
                    best_hit_pt = p_start + d_ray * t

            if best_hit_pt is not None and _TOUCH_MAX_GAP_M < best_t < 10.0:
                cota_color = QColor(0, 140, 255) if best_t > 0.05 else QColor(0, 210, 120)
                cota_items.append((p_start, best_hit_pt, cota_color, 0.0))

        # Cota Vertical (do piso até a base do módulo) se o módulo estiver elevado
        # Posicionada no plano do fundo para perfeita visibilidade
        if cur_min_z > 0.02:
            p_floor = QVector3D(cota_x, cota_y, 0.0)
            p_base = QVector3D(cota_x, cota_y, cur_min_z)
            cota_items.append((p_floor, p_base, QColor(255, 160, 20), 0.0))

        return cota_items

    def _update_snap_cotas(self, current_delta: QVector3D) -> None:
        """Calcula as cotas dinâmicas nos 4 lados e verticalmente para o objeto mais próximo."""
        if not self._module_orig_bounds:
            self._active_cota_items = []
            return

        min_x, max_x, min_y, max_y, min_z, max_z = self._module_orig_bounds
        cur_bounds = (
            min_x + current_delta.x(),
            max_x + current_delta.x(),
            min_y + current_delta.y(),
            max_y + current_delta.y(),
            min_z + current_delta.z(),
            max_z + current_delta.z(),
        )

        self._active_cota_items = self._compute_cotas_for_bounds(
            cur_bounds,
            exclude_module=self._target_module,
            exclude_groups=self._affected_groups,
        )

