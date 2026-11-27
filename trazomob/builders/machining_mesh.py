# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""3D mesh generation utilities for MDF boards, handles, and machining operations."""
from __future__ import annotations

import math
from typing import Any

from PySide6.QtGui import QVector3D

from core.mesh import Mesh


def _render_machining_holes_in_mesh(
    mesh: Mesh,
    origin: tuple[float, float, float],
    size: tuple[float, float, float],
    operacoes: list[dict[str, Any]],
    piece_name: str = "",
) -> None:
    """Render technical drill holes directly onto the 3D solid (35mm hinge cups, cam locks, and dowels).

    Drills through the corresponding board face using ``mesh.add_hole`` and builds the
    inner cylindrical walls and hole bottom with normals facing outward from the volume,
    preserving 100% watertight (manifold) topology on the part.
    """
    if not operacoes:
        return

    ox, oy, oz = origin
    sx, sy, sz = size
    cor_furo = (0.20, 0.20, 0.22)       # Bottom of the machining cavity
    cor_borda = (0.45, 0.45, 0.48)      # Inner cylindrical machining wall

    # Identify board orientation to project holes onto the corresponding face
    dims = [abs(sx), abs(sy), abs(sz)]
    min_dim = min(dims)

    # Lightweight circular segmentation (8 sides) for maximum real-time performance
    n_seg = 8
    seen_centers: list[tuple[float, float, float, float]] = []

    def _find_target_face(axis_idx: int, target_coord: float, normal_sign: float):
        for f in mesh.faces:
            if not f.loop:
                continue
            coords = [
                (v.position.x() if axis_idx == 0 else (v.position.y() if axis_idx == 1 else v.position.z()))
                for v in f.loop
            ]
            if max(abs(c - target_coord) for c in coords) < 1e-4:
                n = f.normal()
                n_comp = n.x() if axis_idx == 0 else (n.y() if axis_idx == 1 else n.z())
                if n_comp * normal_sign > 0.5:
                    return f
        return None

    for op in operacoes:
        tipo = op.get("tipo", "furo")
        if tipo != "furo":
            continue

        diam_m = float(op.get("diametro", 35.0)) / 1000.0
        raio_m = diam_m / 2.0
        # Draw functional machining holes and pilot marks in 3D (35mm hinge cup, 15mm cam housing, 8mm dowel, 5mm cam pin, and 2.5mm screw pilot mark)
        if raio_m < 0.0010:
            continue

        x_op_m = float(op.get("x", 0.0)) / 1000.0
        y_op_m = float(op.get("y", 0.0)) / 1000.0
        prof_m = min(float(op.get("profundidade", 12.0)) / 1000.0, 0.050)

        if abs(sy - min_dim) < 1e-5:
            # Front vertical board (Door / Drawer front / Upright stretcher - thickness along Y)
            op_face = str(op.get("face", "")).lower()

            if op_face in ("esquerda", "left"):
                # Hole on left end edge of upright stretcher: face with -X normal (ox)
                cy = oy + y_op_m if sy >= 0 else oy + sy + y_op_m
                cz = oz + x_op_m if sz >= 0 else oz + sz + x_op_m
                cx_face = ox
                cx_fundo = cx_face + prof_m

                y_lo, y_hi = min(oy, oy + sy), max(oy, oy + sy)
                z_lo, z_hi = min(oz, oz + sz), max(oz, oz + sz)
                if not (y_lo + 1e-4 <= cy <= y_hi - 1e-4 and z_lo + raio_m + 1e-4 <= cz <= z_hi - raio_m - 1e-4):
                    continue

                if any(abs(cx_face - sx0) < 1e-3 and math.hypot(cy - sy0, cz - sz0) < (raio_m + sr0 + 1e-3) for sx0, sy0, sz0, sr0 in seen_centers):
                    continue

                target_face = _find_target_face(0, cx_face, -1.0)
                if target_face is None:
                    continue
                seen_centers.append((cx_face, cy, cz, raio_m))

                pts_face = []
                pts_fundo = []
                for i in range(n_seg):
                    ang = 2.0 * math.pi * i / n_seg
                    dy = raio_m * math.cos(ang)
                    dz = raio_m * math.sin(ang)
                    pts_face.append(QVector3D(cx_face, cy + dy, cz + dz))
                    pts_fundo.append(QVector3D(cx_fundo, cy + dy, cz + dz))

                mesh.add_hole(target_face, pts_face)
                f_bot = mesh.add_face(list(reversed(pts_fundo)))
                f_bot.attrs["color"] = cor_furo
                for i in range(n_seg):
                    i_next = (i + 1) % n_seg
                    w_face = mesh.add_face([
                        pts_face[i_next], pts_face[i],
                        pts_fundo[i], pts_fundo[i_next]
                    ])
                    w_face.attrs["color"] = cor_borda

            elif op_face in ("direita", "right"):
                # Hole on right end edge of upright stretcher: face with +X normal (ox + sx)
                cy = oy + y_op_m if sy >= 0 else oy + sy + y_op_m
                cz = oz + x_op_m if sz >= 0 else oz + sz + x_op_m
                cx_face = ox + sx
                cx_fundo = cx_face - prof_m

                y_lo, y_hi = min(oy, oy + sy), max(oy, oy + sy)
                z_lo, z_hi = min(oz, oz + sz), max(oz, oz + sz)
                if not (y_lo + 1e-4 <= cy <= y_hi - 1e-4 and z_lo + raio_m + 1e-4 <= cz <= z_hi - raio_m - 1e-4):
                    continue

                if any(abs(cx_face - sx0) < 1e-3 and math.hypot(cy - sy0, cz - sz0) < (raio_m + sr0 + 1e-3) for sx0, sy0, sz0, sr0 in seen_centers):
                    continue

                target_face = _find_target_face(0, cx_face, 1.0)
                if target_face is None:
                    continue
                seen_centers.append((cx_face, cy, cz, raio_m))

                pts_face = []
                pts_fundo = []
                for i in range(n_seg):
                    ang = 2.0 * math.pi * i / n_seg
                    dy = raio_m * math.cos(ang)
                    dz = raio_m * math.sin(ang)
                    pts_face.append(QVector3D(cx_face, cy + dy, cz + dz))
                    pts_fundo.append(QVector3D(cx_fundo, cy + dy, cz + dz))

                mesh.add_hole(target_face, list(reversed(pts_face)))
                f_bot = mesh.add_face(pts_fundo)
                f_bot.attrs["color"] = cor_furo
                for i in range(n_seg):
                    i_next = (i + 1) % n_seg
                    w_face = mesh.add_face([
                        pts_face[i], pts_face[i_next],
                        pts_fundo[i_next], pts_fundo[i]
                    ])
                    w_face.attrs["color"] = cor_borda

            elif op_face in ("frontal", "front"):
                # Holes on the front face (-Y of the board): face with -Y normal at oy
                cx = ox + x_op_m if sx >= 0 else ox + sx + x_op_m
                cz = oz + y_op_m if sz >= 0 else oz + sz + y_op_m
                cy_face = oy
                cy_fundo = cy_face + prof_m

                x_lo, x_hi = min(ox, ox + sx), max(ox, ox + sx)
                z_lo, z_hi = min(oz, oz + sz), max(oz, oz + sz)
                if not (x_lo + raio_m + 1e-4 <= cx <= x_hi - raio_m - 1e-4 and z_lo + raio_m + 1e-4 <= cz <= z_hi - raio_m - 1e-4):
                    continue

                if any(abs(cy_face - sy0) < 1e-3 and math.hypot(cx - sx0, cz - sz0) < (raio_m + sr0 + 1e-3) for sx0, sy0, sz0, sr0 in seen_centers):
                    continue

                target_face = _find_target_face(1, cy_face, -1.0)
                if target_face is None:
                    continue
                seen_centers.append((cx, cy_face, cz, raio_m))

                pts_face = []
                pts_fundo = []
                for i in range(n_seg):
                    ang = 2.0 * math.pi * i / n_seg
                    dx = raio_m * math.cos(ang)
                    dz = raio_m * math.sin(ang)
                    pts_face.append(QVector3D(cx + dx, cy_face, cz + dz))
                    pts_fundo.append(QVector3D(cx + dx, cy_fundo, cz + dz))

                # Face normal -Y. add_hole requires a loop with opposite normal (+Y): list(reversed(pts_face))
                mesh.add_hole(target_face, list(reversed(pts_face)))
                f_bot = mesh.add_face(pts_fundo)
                f_bot.attrs["color"] = cor_furo
                for i in range(n_seg):
                    i_next = (i + 1) % n_seg
                    w_face = mesh.add_face([
                        pts_face[i], pts_face[i_next],
                        pts_fundo[i_next], pts_fundo[i]
                    ])
                    w_face.attrs["color"] = cor_borda

            else:
                # Holes on the wide rear face (+Y of the board): hinge cups or upright cam housings
                cx = ox + x_op_m if sx >= 0 else ox + sx + x_op_m
                cz = oz + y_op_m if sz >= 0 else oz + sz + y_op_m
                cy_face = oy + sy
                cy_fundo = cy_face - prof_m

                x_lo, x_hi = min(ox, ox + sx), max(ox, ox + sx)
                z_lo, z_hi = min(oz, oz + sz), max(oz, oz + sz)
                if not (x_lo + raio_m + 1e-4 <= cx <= x_hi - raio_m - 1e-4 and z_lo + raio_m + 1e-4 <= cz <= z_hi - raio_m - 1e-4):
                    continue

                if any(abs(cy_face - sy0) < 1e-3 and math.hypot(cx - sx0, cz - sz0) < (raio_m + sr0 + 1e-3) for sx0, sy0, sz0, sr0 in seen_centers):
                    continue

                target_face = _find_target_face(1, cy_face, 1.0)
                if target_face is None:
                    continue
                seen_centers.append((cx, cy_face, cz, raio_m))

                pts_face = []
                pts_fundo = []
                for i in range(n_seg):
                    ang = 2.0 * math.pi * i / n_seg
                    dx = raio_m * math.cos(ang)
                    dz = raio_m * math.sin(ang)
                    pts_face.append(QVector3D(cx + dx, cy_face, cz + dz))
                    pts_fundo.append(QVector3D(cx + dx, cy_fundo, cz + dz))

                # Drill rear face (+Y) with clockwise loop viewed from +Y (pts_face already has -Y normal)
                mesh.add_hole(target_face, pts_face)

                # Hole bottom (normal pointing outward from the solid: +Y)
                f_bot = mesh.add_face(list(reversed(pts_fundo)))
                f_bot.attrs["color"] = cor_furo

                # Cylindrical hole walls (normal pointing toward cavity center, outside the MDF)
                for i in range(n_seg):
                    i_next = (i + 1) % n_seg
                    w_face = mesh.add_face([
                        pts_face[i_next], pts_face[i],
                        pts_fundo[i], pts_fundo[i_next]
                    ])
                    w_face.attrs["color"] = cor_borda

        elif abs(sx - min_dim) < 1e-5:
            # Side vertical board (Cabinet side panels / dividers - thickness along X)
            op_face = str(op.get("face", "")).lower()

            if op_face in ("topo", "superior"):
                # Top edge of vertical board (face with +Z normal at oz + sz)
                cx = ox + y_op_m if sx >= 0 else ox + sx + y_op_m
                cy = oy + x_op_m if sy >= 0 else oy + sy + x_op_m
                cz_face = oz + sz
                cz_fundo = cz_face - prof_m

                x_lo, x_hi = min(ox, ox + sx), max(ox, ox + sx)
                y_lo, y_hi = min(oy, oy + sy), max(oy, oy + sy)
                if not (x_lo + 1e-4 <= cx <= x_hi - 1e-4 and y_lo + raio_m + 1e-4 <= cy <= y_hi - raio_m - 1e-4):
                    continue

                if any(abs(cz_face - sz0) < 1e-3 and math.hypot(cx - sx0, cy - sy0) < (raio_m + sr0 + 1e-3) for sx0, sy0, sz0, sr0 in seen_centers):
                    continue

                target_face = _find_target_face(2, cz_face, 1.0)
                if target_face is None:
                    continue
                seen_centers.append((cx, cy, cz_face, raio_m))

                pts_face = []
                pts_fundo = []
                for i in range(n_seg):
                    ang = 2.0 * math.pi * i / n_seg
                    dx = raio_m * math.cos(ang)
                    dy = raio_m * math.sin(ang)
                    pts_face.append(QVector3D(cx + dx, cy + dy, cz_face))
                    pts_fundo.append(QVector3D(cx + dx, cy + dy, cz_fundo))

                # Face normal +Z: add_hole requires a loop with opposite normal (-Z): list(reversed(pts_face))
                mesh.add_hole(target_face, list(reversed(pts_face)))
                # Hole bottom points outward from the solid (+Z)
                f_bot = mesh.add_face(pts_fundo)
                f_bot.attrs["color"] = cor_furo
                for i in range(n_seg):
                    i_next = (i + 1) % n_seg
                    w_face = mesh.add_face([
                        pts_face[i], pts_face[i_next],
                        pts_fundo[i_next], pts_fundo[i]
                    ])
                    w_face.attrs["color"] = cor_borda

            elif op_face in ("base", "inferior", "baixo"):
                # Bottom edge (base) of vertical board (face with -Z normal at oz)
                cx = ox + y_op_m if sx >= 0 else ox + sx + y_op_m
                cy = oy + x_op_m if sy >= 0 else oy + sy + x_op_m
                cz_face = oz
                cz_fundo = cz_face + prof_m

                x_lo, x_hi = min(ox, ox + sx), max(ox, ox + sx)
                y_lo, y_hi = min(oy, oy + sy), max(oy, oy + sy)
                if not (x_lo + 1e-4 <= cx <= x_hi - 1e-4 and y_lo + raio_m + 1e-4 <= cy <= y_hi - raio_m - 1e-4):
                    continue

                if any(abs(cz_face - sz0) < 1e-3 and math.hypot(cx - sx0, cy - sy0) < (raio_m + sr0 + 1e-3) for sx0, sy0, sz0, sr0 in seen_centers):
                    continue

                target_face = _find_target_face(2, cz_face, -1.0)
                if target_face is None:
                    continue
                seen_centers.append((cx, cy, cz_face, raio_m))

                pts_face = []
                pts_fundo = []
                for i in range(n_seg):
                    ang = 2.0 * math.pi * i / n_seg
                    dx = raio_m * math.cos(ang)
                    dy = raio_m * math.sin(ang)
                    pts_face.append(QVector3D(cx + dx, cy + dy, cz_face))
                    pts_fundo.append(QVector3D(cx + dx, cy + dy, cz_fundo))

                # Face normal -Z: add_hole requires a loop with opposite normal (+Z): pts_face
                mesh.add_hole(target_face, pts_face)
                # Hole bottom points outward from the solid (-Z)
                f_bot = mesh.add_face(list(reversed(pts_fundo)))
                f_bot.attrs["color"] = cor_furo
                for i in range(n_seg):
                    i_next = (i + 1) % n_seg
                    w_face = mesh.add_face([
                        pts_face[i_next], pts_face[i],
                        pts_fundo[i], pts_fundo[i_next]
                    ])
                    w_face.attrs["color"] = cor_borda

            elif op_face in ("topo_frontal", "borda_frontal"):
                # Front edge of vertical board with thickness along X (face with -Y normal at oy)
                cx = ox + y_op_m if sx >= 0 else ox + sx + y_op_m
                cz = oz + x_op_m if sz >= 0 else oz + sz + x_op_m
                cy_face = oy
                cy_fundo = cy_face + prof_m

                x_lo, x_hi = min(ox, ox + sx), max(ox, ox + sx)
                z_lo, z_hi = min(oz, oz + sz), max(oz, oz + sz)
                if not (x_lo + 1e-4 <= cx <= x_hi - 1e-4 and z_lo + raio_m + 1e-4 <= cz <= z_hi - raio_m - 1e-4):
                    continue

                if any(abs(cy_face - sy0) < 1e-3 and math.hypot(cx - sx0, cz - sz0) < (raio_m + sr0 + 1e-3) for sx0, sy0, sz0, sr0 in seen_centers):
                    continue

                target_face = _find_target_face(1, cy_face, -1.0)
                if target_face is None:
                    continue
                seen_centers.append((cx, cy_face, cz, raio_m))

                pts_face = []
                pts_fundo = []
                for i in range(n_seg):
                    ang = 2.0 * math.pi * i / n_seg
                    dx = raio_m * math.cos(ang)
                    dz = raio_m * math.sin(ang)
                    pts_face.append(QVector3D(cx + dx, cy_face, cz + dz))
                    pts_fundo.append(QVector3D(cx + dx, cy_fundo, cz + dz))

                # Face normal -Y: add_hole requires a loop with opposite normal (+Y): list(reversed(pts_face))
                mesh.add_hole(target_face, list(reversed(pts_face)))
                f_bot = mesh.add_face(pts_fundo)
                f_bot.attrs["color"] = cor_furo
                for i in range(n_seg):
                    i_next = (i + 1) % n_seg
                    w_face = mesh.add_face([
                        pts_face[i], pts_face[i_next],
                        pts_fundo[i_next], pts_fundo[i]
                    ])
                    w_face.attrs["color"] = cor_borda

            elif op_face in ("topo_traseiro", "borda_traseira"):
                # Rear edge of vertical board with thickness along X (face with +Y normal at oy + sy)
                cx = ox + y_op_m if sx >= 0 else ox + sx + y_op_m
                cz = oz + x_op_m if sz >= 0 else oz + sz + x_op_m
                cy_face = oy + sy
                cy_fundo = cy_face - prof_m

                x_lo, x_hi = min(ox, ox + sx), max(ox, ox + sx)
                z_lo, z_hi = min(oz, oz + sz), max(oz, oz + sz)
                if not (x_lo + 1e-4 <= cx <= x_hi - 1e-4 and z_lo + raio_m + 1e-4 <= cz <= z_hi - raio_m - 1e-4):
                    continue

                if any(abs(cy_face - sy0) < 1e-3 and math.hypot(cx - sx0, cz - sz0) < (raio_m + sr0 + 1e-3) for sx0, sy0, sz0, sr0 in seen_centers):
                    continue

                target_face = _find_target_face(1, cy_face, 1.0)
                if target_face is None:
                    continue
                seen_centers.append((cx, cy_face, cz, raio_m))

                pts_face = []
                pts_fundo = []
                for i in range(n_seg):
                    ang = 2.0 * math.pi * i / n_seg
                    dx = raio_m * math.cos(ang)
                    dz = raio_m * math.sin(ang)
                    pts_face.append(QVector3D(cx + dx, cy_face, cz + dz))
                    pts_fundo.append(QVector3D(cx + dx, cy_fundo, cz + dz))

                # Face normal +Y: add_hole requires a loop with opposite normal (-Y): pts_face
                mesh.add_hole(target_face, pts_face)
                f_bot = mesh.add_face(list(reversed(pts_fundo)))
                f_bot.attrs["color"] = cor_furo
                for i in range(n_seg):
                    i_next = (i + 1) % n_seg
                    w_face = mesh.add_face([
                        pts_face[i_next], pts_face[i],
                        pts_fundo[i], pts_fundo[i_next]
                    ])
                    w_face.attrs["color"] = cor_borda

            else:
                # Holes on the wide lateral face (+X or -X) of the side panel or divider.
                # Explicit faces ("esquerda"/"direita") allow drilling both
                # faces of the same divider; otherwise, the inner face
                # inferred from the part name is used:
                # - For Right Side Panel: inner face is at ox (normal -X), hole advances along +X
                # - For Left Side Panel or dividers: inner face is at ox + sx (normal +X), hole advances along -X
                if op_face in ("esquerda", "left"):
                    is_direita = True   # -X face, at ox
                elif op_face in ("direita", "right"):
                    is_direita = False  # +X face, at ox + sx
                else:
                    is_direita = "direit" in piece_name.lower() or "right" in piece_name.lower()
                cy = oy + x_op_m if sy >= 0 else oy + sy + x_op_m
                cz = oz + y_op_m if sz >= 0 else oz + sz + y_op_m

                if is_direita:
                    cx_face = ox
                    cx_fundo = cx_face + prof_m
                    target_sign = -1.0
                else:
                    cx_face = ox + sx
                    cx_fundo = cx_face - prof_m
                    target_sign = 1.0

                y_lo, y_hi = min(oy, oy + sy), max(oy, oy + sy)
                z_lo, z_hi = min(oz, oz + sz), max(oz, oz + sz)
                if not (y_lo + raio_m + 1e-4 <= cy <= y_hi - raio_m - 1e-4 and z_lo + raio_m + 1e-4 <= cz <= z_hi - raio_m - 1e-4):
                    continue

                if any(abs(cx_face - sx0) < 1e-3 and math.hypot(cy - sy0, cz - sz0) < (raio_m + sr0 + 1e-3) for sx0, sy0, sz0, sr0 in seen_centers):
                    continue

                target_face = _find_target_face(0, cx_face, target_sign)
                if target_face is None:
                    continue
                seen_centers.append((cx_face, cy, cz, raio_m))

                pts_face = []
                pts_fundo = []
                for i in range(n_seg):
                    ang = 2.0 * math.pi * i / n_seg
                    dy = raio_m * math.cos(ang)
                    dz = raio_m * math.sin(ang)
                    pts_face.append(QVector3D(cx_face, cy + dy, cz + dz))
                    pts_fundo.append(QVector3D(cx_fundo, cy + dy, cz + dz))

                if is_direita:
                    # Face has -X normal. add_hole requires a loop with opposite normal (+X): pts_face has +X normal
                    mesh.add_hole(target_face, pts_face)
                    # Hole bottom points outward from the solid: -X
                    f_bot = mesh.add_face(list(reversed(pts_fundo)))
                    f_bot.attrs["color"] = cor_furo
                    for i in range(n_seg):
                        i_next = (i + 1) % n_seg
                        w_face = mesh.add_face([
                            pts_face[i_next], pts_face[i],
                            pts_fundo[i], pts_fundo[i_next]
                        ])
                        w_face.attrs["color"] = cor_borda
                else:
                    # Face has +X normal. add_hole requires a loop with opposite normal (-X): reversed(pts_face)
                    mesh.add_hole(target_face, list(reversed(pts_face)))
                    # Hole bottom points outward from the solid: +X
                    f_bot = mesh.add_face(pts_fundo)
                    f_bot.attrs["color"] = cor_furo
                    for i in range(n_seg):
                        i_next = (i + 1) % n_seg
                        w_face = mesh.add_face([
                            pts_face[i], pts_face[i_next],
                            pts_fundo[i_next], pts_fundo[i]
                        ])
                        w_face.attrs["color"] = cor_borda

        elif abs(sz - min_dim) < 1e-5:
            # Horizontal board (Base / Top / Shelf - thickness along Z)
            op_face = str(op.get("face", "")).lower()

            # Case A: Eccentric Minifix cam housing hole on horizontal face (bottom or top face)
            if op_face in ("base", "topo", "inferior", "superior", "fundo"):
                cx = ox + x_op_m if sx >= 0 else ox + sx + x_op_m
                cy = oy + y_op_m if sy >= 0 else oy + sy + y_op_m
                x_lo, x_hi = min(ox, ox + sx), max(ox, ox + sx)
                y_lo, y_hi = min(oy, oy + sy), max(oy, oy + sy)
                is_vb = "vb" in str(op.get("descricao", "")).lower()
                # For edge-mounted connectors such as VB 35 / VB 36 (Ø20mm hole centered 9.5mm from edge),
                # the center sits slightly aligned with the edge for pin engagement (open-edge tolerance)
                min_margem_x = 0.0005 if is_vb else (raio_m + 1e-4)
                if is_vb:
                    if not (x_lo <= cx <= x_hi and y_lo + raio_m + 1e-4 <= cy <= y_hi - raio_m - 1e-4):
                        continue
                    # Slightly shift visual center inward if needed to keep inner contour watertight
                    cx = max(x_lo + raio_m + 0.0005, min(x_hi - raio_m - 0.0005, cx))
                else:
                    if not (x_lo + min_margem_x <= cx <= x_hi - min_margem_x and y_lo + raio_m + 1e-4 <= cy <= y_hi - raio_m - 1e-4):
                        continue

                is_face_topo = op_face in ("topo", "superior")
                if is_face_topo:
                    cz_face = oz + sz
                    cz_fundo = cz_face - prof_m
                    target_sign = 1.0
                else:
                    cz_face = oz
                    cz_fundo = cz_face + prof_m
                    target_sign = -1.0

                if any(abs(cz_face - sz0) < 1e-3 and math.hypot(cx - sx0, cy - sy0) < (raio_m + sr0 + 1e-3) for sx0, sy0, sz0, sr0 in seen_centers):
                    continue

                target_face = _find_target_face(2, cz_face, target_sign)
                if target_face is None:
                    continue
                seen_centers.append((cx, cy, cz_face, raio_m))

                pts_face = []
                pts_fundo = []
                for i in range(n_seg):
                    ang = 2.0 * math.pi * i / n_seg
                    dx = raio_m * math.cos(ang)
                    dy = raio_m * math.sin(ang)
                    pts_face.append(QVector3D(cx + dx, cy + dy, cz_face))
                    pts_fundo.append(QVector3D(cx + dx, cy + dy, cz_fundo))

                if is_face_topo:
                    # Face normal +Z: add_hole requires a loop with -Z normal: reversed(pts_face)
                    mesh.add_hole(target_face, list(reversed(pts_face)))
                    f_bot = mesh.add_face(pts_fundo)
                    f_bot.attrs["color"] = cor_furo
                    for i in range(n_seg):
                        i_next = (i + 1) % n_seg
                        w_face = mesh.add_face([
                            pts_face[i], pts_face[i_next],
                            pts_fundo[i_next], pts_fundo[i]
                        ])
                        w_face.attrs["color"] = cor_borda
                else:
                    # Face normal -Z: add_hole requires a loop with +Z normal: pts_face
                    mesh.add_hole(target_face, pts_face)
                    f_bot = mesh.add_face(list(reversed(pts_fundo)))
                    f_bot.attrs["color"] = cor_furo
                    for i in range(n_seg):
                        i_next = (i + 1) % n_seg
                        w_face = mesh.add_face([
                            pts_face[i_next], pts_face[i],
                            pts_fundo[i], pts_fundo[i_next]
                        ])
                        w_face.attrs["color"] = cor_borda

            # Case B: End-edge holes (side edges): left face (-X, normal -1) or right face (+X, normal +1)
            else:
                cy = oy + x_op_m if sy >= 0 else oy + sy + x_op_m
                cz = oz + y_op_m if sz >= 0 else oz + sz + y_op_m

                y_lo, y_hi = min(oy, oy + sy), max(oy, oy + sy)
                z_lo, z_hi = min(oz, oz + sz), max(oz, oz + sz)
                if not (y_lo + raio_m + 1e-4 <= cy <= y_hi - raio_m - 1e-4 and z_lo + 1e-4 <= cz <= z_hi - 1e-4):
                    continue

                if op_face in ("esquerda", "left") or "esq" in op.get("descricao", "").lower():
                    cx_face = ox
                    cx_fundo = cx_face + prof_m
                    target_sign = -1.0
                    is_esq = True
                elif op_face in ("direita", "right") or "dir" in op.get("descricao", "").lower():
                    cx_face = ox + sx
                    cx_fundo = cx_face - prof_m
                    target_sign = 1.0
                    is_esq = False
                else:
                    continue

                if any(abs(cx_face - sx0) < 1e-3 and math.hypot(cy - sy0, cz - sz0) < (raio_m + sr0 + 1e-3) for sx0, sy0, sz0, sr0 in seen_centers):
                    continue

                target_face = _find_target_face(0, cx_face, target_sign)
                if target_face is None:
                    continue
                seen_centers.append((cx_face, cy, cz, raio_m))

                pts_face = []
                pts_fundo = []
                for i in range(n_seg):
                    ang = 2.0 * math.pi * i / n_seg
                    dy = raio_m * math.cos(ang)
                    dz = raio_m * math.sin(ang)
                    pts_face.append(QVector3D(cx_face, cy + dy, cz + dz))
                    pts_fundo.append(QVector3D(cx_fundo, cy + dy, cz + dz))

                if is_esq:
                    # Face with -X normal: add_hole with pts_face (+X normal)
                    mesh.add_hole(target_face, pts_face)
                    f_bot = mesh.add_face(list(reversed(pts_fundo)))
                    f_bot.attrs["color"] = cor_furo
                    for i in range(n_seg):
                        i_next = (i + 1) % n_seg
                        w_face = mesh.add_face([
                            pts_face[i_next], pts_face[i],
                            pts_fundo[i], pts_fundo[i_next]
                        ])
                        w_face.attrs["color"] = cor_borda
                else:
                    # Face with +X normal: add_hole with reversed(pts_face) (-X normal)
                    mesh.add_hole(target_face, list(reversed(pts_face)))
                    f_bot = mesh.add_face(pts_fundo)
                    f_bot.attrs["color"] = cor_furo
                    for i in range(n_seg):
                        i_next = (i + 1) % n_seg
                        w_face = mesh.add_face([
                            pts_face[i], pts_face[i_next],
                            pts_fundo[i_next], pts_fundo[i]
                        ])
                        w_face.attrs["color"] = cor_borda



