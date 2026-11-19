# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Manipulador e c?lculo de posicionamento por arraste e soltura (Drag & Drop) de m?dulos na cena 3D."""

from __future__ import annotations

import json
import logging
import math
from typing import Any, Optional, Tuple

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QVector3D

from core.group import Group
from core.history import SnapshotImport

from ..builders.cabinet import CabinetBuilder
from ..domain.module_geometry import build_default_module_params, get_module_category
from .magnetic_drag_snap import draw_snap_dimension_segment, get_bounds_min_projection, get_module_bounds

logger = logging.getLogger("trazomob.drag_drop")

TRAZOMOB_MIME_MODULE = "application/x-trazomob-module"
TRAZOMOB_MIME_DECORATION = "application/x-trazomob-decoration"


def compute_drop_placement(
    viewport: Any,
    pos: QPointF,
    mod_data: dict[str, Any],
) -> Tuple[Tuple[float, float, float], float, Optional[Any]]:
    """Calcula o offset 3D (x, y, z) e rot_z para posicionar o m?dulo no ponto solto pelo mouse.

    Identifica:
    1. Se o cursor est? apontando para uma parede:
       - Encosta a traseira do m?vel na parede com 0.0mm de folga;
       - Alinha a rota??o do m?vel para que as portas fiquem voltadas para o ambiente (+normal da face);
       - Confinamento aos limites da parede [min_u, max_u];
       - Altura Z ancorada na base (ou no peitoril / guia correspondente).
    2. Se o cursor est? solto no piso ou ar livre:
       - Projeta a interse??o do raio do cursor com o plano Z = default_z (ou Z = 0);
       - Mant?m rot_z padr?o (0.0).
    """
    orig, dirc = viewport._pixel_to_ray(pos.x(), pos.y())
    default_z = float(mod_data.get("default_z", 0.0))
    larg_m = float(mod_data.get("largura", 800.0)) / 1000.0
    prof_m = float(mod_data.get("profundidade", 550.0)) / 1000.0
    alt_m = float(mod_data.get("altura", 720.0)) / 1000.0

    if orig is None or dirc is None:
        return (0.0, 0.0, default_z), 0.0, None

    # Coleta paredes da cena
    scene = getattr(viewport, "scene", None)
    walls = []
    if scene and hasattr(scene, "groups"):
        for g in scene.groups:
            if hasattr(g, "ext") and isinstance(g.ext, dict) and "trazomob_wall" in g.ext:
                walls.append(g)

    best_wall_face = None
    best_t = float("inf")

    # Verifica se o raio do mouse intercepta diretamente a face interna de alguma parede
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

            pts_2d = [QVector3D(v.x(), v.y(), 0.0) for v in f_verts]
            u_dir = QVector3D(-n_dir.y(), n_dir.x(), 0.0).normalized()
            projs = [QVector3D.dotProduct(p, u_dir) for p in pts_2d]
            min_u, max_u = min(projs), max(projs)
            if (max_u - min_u) < 0.20:
                continue

            p_ref = QVector3D(f_verts[0].x(), f_verts[0].y(), 0.0)
            denom = QVector3D.dotProduct(dirc, n_dir)
            if denom < -1e-4:  # face apontada para a c?mera
                t_wall = QVector3D.dotProduct(p_ref - orig, n_dir) / denom
                if 0.0 < t_wall < 35.0 and t_wall < best_t:
                    hit_pt = orig + dirc * t_wall
                    hit_u = QVector3D.dotProduct(hit_pt, u_dir)
                    if (min_u - 0.15) <= hit_u <= (max_u + 0.15) and 0.0 <= hit_pt.z() <= 3.5:
                        best_t = t_wall
                        best_wall_face = (n_dir, u_dir, p_ref, hit_pt, wall, face, min_u, max_u)

    if best_wall_face is not None:
        n_dir, u_dir, p_ref, hit_pt, wall, face, min_u, max_u = best_wall_face
        mod_id = str(mod_data.get("id", mod_data.get("tipo", "")) or "").lower()
        is_esquadria = mod_id.startswith(("porta_", "janela_")) or mod_data.get("kind") == "esquadria"

        hit_u = QVector3D.dotProduct(hit_pt, u_dir)
        half_len_u = larg_m * 0.5
        # Confina centro U dentro dos limites da parede
        clamped_center_u = max(min_u + half_len_u, min(max_u - half_len_u, hit_u))

        # Posi??o base da face da parede ao longo de n_dir
        wall_face_n = QVector3D.dotProduct(p_ref, n_dir)

        if is_esquadria:
            w_ext = getattr(wall, "ext", {}).get("trazomob_wall", {}) if hasattr(wall, "ext") else {}
            wall_esp = float(w_ext.get("espessura", 0.15) or 0.15)
            z_base = float(w_ext.get("z_base", 0.0) or 0.0)
            # Centro da espessura da parede: recua metade da espessura para dentro (-n_dir)
            wall_center_n = wall_face_n - (wall_esp * 0.5)
            c_wall_center = u_dir * clamped_center_u + n_dir * wall_center_n

            from ..builders.esquadrias import EsquadriaBuilder
            mid_yl = EsquadriaBuilder.get_esquadria_local_mid_y(mod_id, esp_parede_mm=wall_esp * 1000.0)

            # Local +X = u_dir, Local +Y = -n_dir (rot_z = atan2(u_dir.y, u_dir.x))
            rot_z = math.degrees(math.atan2(u_dir.y(), u_dir.x()))
            p_origin = c_wall_center - u_dir * (larg_m * 0.5) + n_dir * mid_yl
            # Peitoril já é somado internamente por build_module_group para esquadrias
            return (p_origin.x(), p_origin.y(), z_base), rot_z, wall

        # Rota??o para encostar o fundo na parede (+n_dir aponta para o interior do ambiente)
        angle_deg = math.degrees(math.atan2(n_dir.y(), n_dir.x())) + 90.0
        rot_z = (round(angle_deg / 90.0) * 90.0) % 360.0

        # Z na parede
        z_pos = hit_pt.z()
        # Se for arm?rio inferior ou m?vel de ch?o e estiver pr?ximo da base, ancora em default_z
        if z_pos < 0.40 or default_z == 0.0:
            final_z = default_z
        else:
            final_z = z_pos

        pos_center = u_dir * clamped_center_u + n_dir * (wall_face_n + 0.001)
        pos_center.setZ(final_z)

        offset = (pos_center.x() - u_dir.x() * (larg_m * 0.5),
                  pos_center.y() - u_dir.y() * (larg_m * 0.5),
                  final_z)
        return offset, rot_z, wall

    # Caso contr?rio: raio atinge o piso horizontal Z = default_z
    plane_z = default_z
    hit_floor = None
    if abs(dirc.z()) > 1e-4:
        t = (plane_z - orig.z()) / dirc.z()
        if 0.0 < t < 50.0:
            hit_floor = orig + dirc * t

    if hit_floor is None:
        dist_ref = 3.0
        hit_floor = orig + dirc * dist_ref
        hit_floor.setZ(plane_z)

    offset = (hit_floor.x() - larg_m * 0.5, hit_floor.y() - prof_m * 0.5, plane_z)
    return offset, 0.0, None


def draw_drop_preview_overlay(
    viewport: Any,
    painter: QPainter,
    drop_info: Optional[dict[str, Any]],
) -> None:
    """Renderiza a caixa 3D fantasma (bounding box) e a etiqueta do m?dulo no ponto solto."""
    if not drop_info:
        return

    mod_data = drop_info.get("mod_data")
    if not mod_data:
        return

    offset = drop_info.get("offset", (0.0, 0.0, 0.0))
    rot_z = float(drop_info.get("rot_z", 0.0))
    larg_m = float(mod_data.get("largura", 800.0)) / 1000.0
    prof_m = float(mod_data.get("profundidade", 550.0)) / 1000.0
    alt_m = float(mod_data.get("altura", 720.0)) / 1000.0
    mod_id = str(mod_data.get("id", mod_data.get("tipo", "")) or "").lower()
    is_esquadria = mod_id.startswith(("porta_", "janela_")) or mod_data.get("kind") == "esquadria"

    if is_esquadria:
        from ..builders.esquadrias import EsquadriaBuilder
        mid_yl = EsquadriaBuilder.get_esquadria_local_mid_y(mod_id, esp_parede_mm=prof_m * 1000.0)
        peit_m = float(mod_data.get("peitoril_mm", mod_data.get("peitoril", 0.0)) or 0.0) / 1000.0
        y0_l, y1_l = mid_yl - prof_m * 0.5, mid_yl + prof_m * 0.5
        z0_l, z1_l = peit_m, peit_m + alt_m
    else:
        # Os 8 v?rtices locais da caixa
        # No construtor: x vai de 0 a L, y vai de -P a 0, z vai de 0 a H
        y0_l, y1_l = -prof_m, 0.0
        z0_l, z1_l = 0.0, alt_m

    local_corners = [
        QVector3D(0.0, y0_l, z0_l),
        QVector3D(larg_m, y0_l, z0_l),
        QVector3D(larg_m, y1_l, z0_l),
        QVector3D(0.0, y1_l, z0_l),
        QVector3D(0.0, y0_l, z1_l),
        QVector3D(larg_m, y0_l, z1_l),
        QVector3D(larg_m, y1_l, z1_l),
        QVector3D(0.0, y1_l, z1_l),
    ]

    rad = math.radians(rot_z)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    off_v = QVector3D(*offset)

    world_pts = []
    for c in local_corners:
        rx = c.x() * cos_a - c.y() * sin_a
        ry = c.x() * sin_a + c.y() * cos_a
        world_pts.append(QVector3D(rx, ry, c.z()) + off_v)

    # Converte v?rtices para pixels de tela
    pixel_pts = [viewport.world_to_pixel(wp) for wp in world_pts]
    if any(p is None for p in pixel_pts):
        return

    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),  # base
        (4, 5), (5, 6), (6, 7), (7, 4),  # topo
        (0, 4), (1, 5), (2, 6), (3, 7),  # verticais
    ]

    painter.save()
    try:
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        # 1. Linhas da caixa delimitadora com cor vibrante
        pen_box = QPen(QColor(37, 99, 235, 230), 2.0, Qt.DashLine)
        painter.setPen(pen_box)
        for i, j in edges:
            p0, p1 = pixel_pts[i], pixel_pts[j]
            painter.drawLine(QPointF(p0[0], p0[1]), QPointF(p1[0], p1[1]))

        # 2. Badge central identificando o m?vel e suas medidas
        top_center = (world_pts[4] + world_pts[6]) * 0.5
        top_px = viewport.world_to_pixel(top_center)
        if top_px is not None:
            name = mod_data.get("nome", "M?dulo")
            dim_str = f"{int(round(larg_m*1000))}x{int(round(alt_m*1000))}x{int(round(prof_m*1000))} mm"
            texto = f"? {name} ({dim_str})"

            font = QFont()
            font.setPointSize(9)
            font.setBold(True)
            painter.setFont(font)
            fm = painter.fontMetrics()
            tw, th = fm.horizontalAdvance(texto), fm.height()
            pad_x, pad_y = 8, 4

            from PySide6.QtCore import QRectF
            badge_rect = QRectF(top_px[0] - tw * 0.5 - pad_x, top_px[1] - th - 12 - pad_y, tw + pad_x * 2, th + pad_y * 2)

            painter.setPen(QPen(QColor(37, 99, 235), 1.5))
            painter.setBrush(QColor(15, 23, 42, 230))
            painter.drawRoundedRect(badge_rect, 5.0, 5.0)

            painter.setPen(QColor(255, 255, 255))
            painter.drawText(badge_rect, Qt.AlignCenter, texto)
    finally:
        painter.restore()
