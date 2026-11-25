# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Utilitários de geração de malhas 3D para chapas de MDF, puxadores e usinagens."""
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
    """Renderiza furações técnicas diretamente no sólido 3D (canecos 35mm, minifix e cavilhas).

    Perfura a face correspondente da chapa usando ``mesh.add_hole`` e cria as paredes
    cilíndricas internas e o fundo do furo com normais voltadas para fora do volume,
    preservando 100% a topologia estanque (manifold / watertight) da peça.
    """
    if not operacoes:
        return

    ox, oy, oz = origin
    sx, sy, sz = size
    cor_furo = (0.20, 0.20, 0.22)       # Fundo da cavidade de usinagem
    cor_borda = (0.45, 0.45, 0.48)      # Parede cilíndrica interna de usinagem

    # Identifica orientação da chapa para projetar os furos na face correspondente
    dims = [abs(sx), abs(sy), abs(sz)]
    min_dim = min(dims)

    # Segmentação circular leve (8 lados) para performance máxima em tempo real
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
        # Desenha no 3D furos de usinagem funcional e marcações (caneco 35mm, tambor 15mm, cavilha 8mm, pino minifix 5mm e marcação parafuso 2.5mm)
        if raio_m < 0.0010:
            continue

        x_op_m = float(op.get("x", 0.0)) / 1000.0
        y_op_m = float(op.get("y", 0.0)) / 1000.0
        prof_m = min(float(op.get("profundidade", 12.0)) / 1000.0, 0.050)

        if abs(sy - min_dim) < 1e-5:
            # Chapa vertical frontal (Porta / Frente de gaveta / Travessa em pé - espessura em Y)
            op_face = str(op.get("face", "")).lower()

            if op_face in ("esquerda", "left"):
                # Furo no topo esquerdo da travessa em pé: face com normal -X (ox)
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
                # Furo no topo direito da travessa em pé: face com normal +X (ox + sx)
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
                # Furos na face frontal (-Y da chapa): face com normal -Y em oy
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

                # Face normal -Y. add_hole requer loop com normal contrária (+Y): list(reversed(pts_face))
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
                # Furos na face larga traseira (+Y da chapa): canecos de dobradiça ou tambores de minifix em pé
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

                # Perfura a face traseira (+Y) com loop horário visto de +Y (pts_face já tem normal -Y)
                mesh.add_hole(target_face, pts_face)

                # Fundo do furo (normal apontando para fora do sólido: +Y)
                f_bot = mesh.add_face(list(reversed(pts_fundo)))
                f_bot.attrs["color"] = cor_furo

                # Paredes cilíndricas do furo (normal apontando para o centro da cavidade, fora do MDF)
                for i in range(n_seg):
                    i_next = (i + 1) % n_seg
                    w_face = mesh.add_face([
                        pts_face[i_next], pts_face[i],
                        pts_fundo[i], pts_fundo[i_next]
                    ])
                    w_face.attrs["color"] = cor_borda

        elif abs(sx - min_dim) < 1e-5:
            # Chapa vertical lateral (Laterais do armário / divisórias - espessura em X)
            op_face = str(op.get("face", "")).lower()

            if op_face in ("topo", "superior"):
                # Topo superior da chapa vertical (face com normal +Z em oz + sz)
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

                # Face normal +Z: add_hole requer loop com normal contrária (-Z): list(reversed(pts_face))
                mesh.add_hole(target_face, list(reversed(pts_face)))
                # Fundo do furo aponta para fora do sólido (+Z)
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
                # Topo inferior (base) da chapa vertical (face com normal -Z em oz)
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

                # Face normal -Z: add_hole requer loop com normal contrária (+Z): pts_face
                mesh.add_hole(target_face, pts_face)
                # Fundo do furo aponta para fora do sólido (-Z)
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
                # Topo frontal da chapa vertical com espessura em X (face com normal -Y em oy)
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

                # Face normal -Y: add_hole requer loop com normal contrária (+Y): list(reversed(pts_face))
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
                # Topo traseiro da chapa vertical com espessura em X (face com normal +Y em oy + sy)
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

                # Face normal +Y: add_hole requer loop com normal contrária (-Y): pts_face
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
                # Furos na face lateral ampla (+X ou -X) da lateral ou divisória.
                # Faces explícitas ("esquerda"/"direita") permitem furar as duas
                # faces de uma mesma divisória; sem elas, usa-se a face interna
                # deduzida pelo nome da peça:
                # - Para Lateral Direita: a face interna fica em ox (normal -X), furo avança em +X
                # - Para Lateral Esquerda ou divisórias: a face interna fica em ox + sx (normal +X), furo avança em -X
                if op_face in ("esquerda", "left"):
                    is_direita = True   # face -X, em ox
                elif op_face in ("direita", "right"):
                    is_direita = False  # face +X, em ox + sx
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
                    # Face tem normal -X. add_hole requer loop com normal contrária (+X): pts_face tem normal +X
                    mesh.add_hole(target_face, pts_face)
                    # Fundo do furo aponta para fora do sólido: -X
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
                    # Face tem normal +X. add_hole requer loop com normal contrária (-X): reversed(pts_face)
                    mesh.add_hole(target_face, list(reversed(pts_face)))
                    # Fundo do furo aponta para fora do sólido: +X
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
            # Chapa horizontal (Base / Tampo / Prateleira - espessura em Z)
            op_face = str(op.get("face", "")).lower()

            # Caso A: Furo do tambor excêntrico Minifix na face horizontal (face inferior ou superior)
            if op_face in ("base", "topo", "inferior", "superior", "fundo"):
                cx = ox + x_op_m if sx >= 0 else ox + sx + x_op_m
                cy = oy + y_op_m if sy >= 0 else oy + sy + y_op_m
                x_lo, x_hi = min(ox, ox + sx), max(ox, ox + sx)
                y_lo, y_hi = min(oy, oy + sy), max(oy, oy + sy)
                is_vb = "vb" in str(op.get("descricao", "")).lower()
                # Para conectores de embutir de borda tipo VB 35 / VB 36 (furo Ø20mm com centro a 9.5mm da borda),
                # o centro fica ligeiramente alinhado à borda para engate do pino (tolerância de borda aberta)
                min_margem_x = 0.0005 if is_vb else (raio_m + 1e-4)
                if is_vb:
                    if not (x_lo <= cx <= x_hi and y_lo + raio_m + 1e-4 <= cy <= y_hi - raio_m - 1e-4):
                        continue
                    # Ajusta centro visual ligeiramente para dentro se necessário para manter o contorno interno estanque
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
                    # Face normal +Z: add_hole requer loop com normal -Z: reversed(pts_face)
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
                    # Face normal -Z: add_hole requer loop com normal +Z: pts_face
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

            # Caso B: Furos nos topos (bordas laterais): face esquerda (-X, normal -1) ou direita (+X, normal +1)
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
                    # Face com normal -X: add_hole com pts_face (normal +X)
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
                    # Face com normal +X: add_hole com reversed(pts_face) (normal -X)
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



