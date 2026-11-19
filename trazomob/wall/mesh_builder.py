# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Gerador de malha 3D e cálculo geométrico de esquadrias para paredes e pisos (WallMeshBuilder)."""
from __future__ import annotations

import math
from typing import Optional, Union, Tuple, Dict, List
from PySide6.QtGui import QVector3D

from core.group import Group
from core.history import Command
from core.layers import Layer
from core.mesh import Mesh
from core.triangulate import triangulate


def line_intersection_2d(p1: QVector3D, d1: QVector3D, p2: QVector3D, d2: QVector3D) -> QVector3D:
    """Calcula a interseção entre duas retas no plano horizontal Z=0."""
    det = d1.x() * d2.y() - d1.y() * d2.x()
    if abs(det) < 1e-5:
        # Retas quase paralelas ou colineares
        return p2
    dx = p2.x() - p1.x()
    dy = p2.y() - p1.y()
    s = (dx * d2.y() - dy * d2.x()) / det
    # Limita avanço exagerado em ângulos extremamente agudos (< 5°)
    if abs(s) > 20.0:
        return p2
    return p1 + d1 * s


class WallMeshBuilder:
    """Responsável por calcular e construir as malhas 3D de paredes e pisos."""

    @classmethod
    def compute_wall_mesh(
        cls,
        pts: List[QVector3D],
        is_closed: bool,
        altura_m: Union[float, List[float]],
        espessura_m: float,
        alinhamento: str = "interno",
        miter_start: bool = False,
        miter_end: bool = False,
        open_start: bool = False,
        open_end: bool = False,
        open_quinas: Optional[List[int]] = None,
        open_side_a: Optional[List[int]] = None,
        open_side_b: Optional[List[int]] = None,
        openings: Optional[List[Dict[str, any]]] = None,
        quad_2d: Optional[List[Union[List[float], Tuple[float, float]]]] = None,
    ) -> Tuple[Mesh, Dict[int, int]]:
        """Calcula a malha 3D sólida manifold da parede com miter joints em cada canto.

        Suporta aberturas/recortes arquitetônicos de portas e janelas (openings).
        Retorna (mesh, face_index_to_segment_map).
        """
        n_pts = len(pts)
        if n_pts < 2:
            return Mesh(), {}

        n_segs = n_pts if is_closed else (n_pts - 1)
        if isinstance(altura_m, (int, float)):
            alturas = [float(altura_m)] * n_segs
        else:
            alturas = [float(h) for h in altura_m]
            if len(alturas) < n_segs:
                last_h = alturas[-1] if alturas else 2.6
                alturas.extend([last_h] * (n_segs - len(alturas)))
            elif len(alturas) > n_segs:
                alturas = alturas[:n_segs]

        segs_dir: List[QVector3D] = []
        segs_norm: List[QVector3D] = []

        for i in range(n_segs):
            p_a = pts[i]
            p_b = pts[(i + 1) % n_pts]
            d = (p_b - p_a).normalized()
            if d.length() < 1e-4:
                d = QVector3D(1, 0, 0)
            norm = QVector3D(-d.y(), d.x(), 0.0).normalized()
            segs_dir.append(d)
            segs_norm.append(norm)

        pts_A: List[QVector3D] = []
        pts_B: List[QVector3D] = []

        z_base_val = pts[0].z() if pts else 0.0
        if quad_2d and len(quad_2d) == 4 and not is_closed and n_segs == 1:
            # Usa os 4 cantos chanfrados (mitered) exatos do segmento (c0, c1, c2, c3):
            # c0 e c1 na borda esquerda (+norm = pts_B), c3 e c2 na borda direita (-norm = pts_A)
            q0, q1, q2, q3 = quad_2d
            pts_A = [QVector3D(float(q3[0]), float(q3[1]), z_base_val), QVector3D(float(q2[0]), float(q2[1]), z_base_val)]
            pts_B = [QVector3D(float(q0[0]), float(q0[1]), z_base_val), QVector3D(float(q1[0]), float(q1[1]), z_base_val)]
        elif is_closed:
            for i in range(n_pts):
                prev_i = (i - 1 + n_pts) % n_pts
                curr_i = i

                d_prev, n_prev = segs_dir[prev_i], segs_norm[prev_i]
                d_curr, n_curr = segs_dir[curr_i], segs_norm[curr_i]

                if alinhamento == "interno":
                    off_a_prev, off_a_curr = QVector3D(0, 0, 0), QVector3D(0, 0, 0)
                    off_b_prev, off_b_curr = n_prev * espessura_m, n_curr * espessura_m
                elif alinhamento == "externo":
                    off_a_prev, off_a_curr = -n_prev * espessura_m, -n_curr * espessura_m
                    off_b_prev, off_b_curr = QVector3D(0, 0, 0), QVector3D(0, 0, 0)
                else:  # centro
                    off_a_prev = -n_prev * (espessura_m / 2.0)
                    off_a_curr = -n_curr * (espessura_m / 2.0)
                    off_b_prev = n_prev * (espessura_m / 2.0)
                    off_b_curr = n_curr * (espessura_m / 2.0)

                pt_a = line_intersection_2d(
                    pts[prev_i] + off_a_prev, d_prev, pts[curr_i] + off_a_curr, d_curr
                )
                pt_b = line_intersection_2d(
                    pts[prev_i] + off_b_prev, d_prev, pts[curr_i] + off_b_curr, d_curr
                )
                pts_A.append(pt_a)
                pts_B.append(pt_b)
        else:
            for i in range(n_pts):
                if i == 0:
                    d_curr, n_curr = segs_dir[0], segs_norm[0]
                    if alinhamento == "interno":
                        off_a = QVector3D(0, 0, 0)
                        off_b = n_curr * espessura_m
                    elif alinhamento == "externo":
                        off_a = -n_curr * espessura_m
                        off_b = QVector3D(0, 0, 0)
                    else:
                        off_a = -n_curr * (espessura_m / 2.0)
                        off_b = n_curr * (espessura_m / 2.0)
                    pts_A.append(pts[0] + off_a)
                    pts_B.append(pts[0] + off_b)
                elif i == n_pts - 1:
                    d_prev, n_prev = segs_dir[-1], segs_norm[-1]
                    if alinhamento == "interno":
                        off_a = QVector3D(0, 0, 0)
                        off_b = n_prev * espessura_m
                    elif alinhamento == "externo":
                        off_a = -n_prev * espessura_m
                        off_b = QVector3D(0, 0, 0)
                    else:
                        off_a = -n_prev * (espessura_m / 2.0)
                        off_b = n_prev * (espessura_m / 2.0)
                    pts_A.append(pts[-1] + off_a)
                    pts_B.append(pts[-1] + off_b)
                else:
                    d_prev, n_prev = segs_dir[i - 1], segs_norm[i - 1]
                    d_curr, n_curr = segs_dir[i], segs_norm[i]
                    if alinhamento == "interno":
                        off_a_prev, off_a_curr = QVector3D(0, 0, 0), QVector3D(0, 0, 0)
                        off_b_prev, off_b_curr = n_prev * espessura_m, n_curr * espessura_m
                    elif alinhamento == "externo":
                        off_a_prev, off_a_curr = -n_prev * espessura_m, -n_curr * espessura_m
                        off_b_prev, off_b_curr = QVector3D(0, 0, 0), QVector3D(0, 0, 0)
                    else:
                        off_a_prev = -n_prev * (espessura_m / 2.0)
                        off_a_curr = -n_curr * (espessura_m / 2.0)
                        off_b_prev = n_prev * (espessura_m / 2.0)
                        off_b_curr = n_curr * (espessura_m / 2.0)

                    pt_a = line_intersection_2d(
                        pts[i - 1] + off_a_prev, d_prev, pts[i] + off_a_curr, d_curr
                    )
                    pt_b = line_intersection_2d(
                        pts[i - 1] + off_b_prev, d_prev, pts[i] + off_b_curr, d_curr
                    )
                    pts_A.append(pt_a)
                    pts_B.append(pt_b)

        mesh = Mesh()
        face_map: Dict[int, int] = {}
        face_idx = 0

        for i in range(n_segs):
            nxt = (i + 1) % n_pts
            h_curr = alturas[i]
            zv_curr = QVector3D(0, 0, h_curr)

            prev_seg = (i - 1 + n_segs) % n_segs if is_closed else (i - 1 if i > 0 else None)
            nxt_seg = (i + 1) % n_segs if is_closed else (i + 1 if i + 1 < n_segs else None)
            h_prev = alturas[prev_seg] if prev_seg is not None else h_curr
            h_next = alturas[nxt_seg] if nxt_seg is not None else h_curr

            a0, a1 = pts_A[i], pts_A[nxt]
            b0, b1 = pts_B[i], pts_B[nxt]

            # Coleta aberturas/recortes deste segmento
            seg_openings = []
            if openings:
                for op in openings:
                    if int(op.get("segment_index", 0)) == i:
                        seg_openings.append(op)

            seg_d = segs_dir[i]
            seg_n = segs_norm[i]
            p_node0 = pts[i]
            p_node1 = pts[nxt]
            seg_len_center = max(1e-4, (p_node1 - p_node0).length())

            def _pt_on_rail(rail_start: QVector3D, rail_end: QVector3D, u_frac: float) -> QVector3D:
                """Projeta u_frac (fração na linha central p_node0->p_node1) perpendicularmente sobre a face da parede.
                Isso garante que o túnel da porta/janela fique 100% em esquadro (90°) mesmo quando a parede tem chanfro de 45° nas pontas!
                """
                if u_frac <= 1e-5:
                    return rail_start
                if u_frac >= 1.0 - 1e-5:
                    return rail_end
                pt_center = p_node0 + seg_d * (u_frac * seg_len_center)
                dist_n = QVector3D.dotProduct(rail_start - p_node0, seg_n)
                return pt_center + seg_n * dist_n

            # 1. Base (Z=0)
            if not seg_openings:
                mesh.add_face([a0, b0, b1, a1])
                face_map[face_idx] = i
                face_idx += 1
            else:
                # Divide o piso nos intervalos fora das portas
                # Intervale U ao longo do segmento (de 0 a 1)
                cuts = []
                for op in seg_openings:
                    u0 = max(0.0, min(1.0, float(op.get("u0", 0.0))))
                    u1 = max(0.0, min(1.0, float(op.get("u1", 1.0))))
                    z_peit = float(op.get("peitoril_m", 0.0))
                    # Se tiver peitoril > 0 (janela), a base do piso continua contínua embaixo
                    if z_peit <= 0.05:
                        cuts.append((min(u0, u1), max(u0, u1)))
                cuts.sort()

                # Mescla cortes sobrepostos
                merged_cuts = []
                for c_start, c_end in cuts:
                    if not merged_cuts or c_start > merged_cuts[-1][1]:
                        merged_cuts.append([c_start, c_end])
                    else:
                        merged_cuts[-1][1] = max(merged_cuts[-1][1], c_end)

                curr_u = 0.0
                for c_start, c_end in merged_cuts:
                    if c_start > curr_u + 1e-4:
                        sub_a0 = _pt_on_rail(a0, a1, curr_u)
                        sub_a1 = _pt_on_rail(a0, a1, c_start)
                        sub_b0 = _pt_on_rail(b0, b1, curr_u)
                        sub_b1 = _pt_on_rail(b0, b1, c_start)
                        mesh.add_face([sub_a0, sub_b0, sub_b1, sub_a1])
                        face_map[face_idx] = i
                        face_idx += 1
                    curr_u = max(curr_u, c_end)
                if curr_u < 1.0 - 1e-4:
                    sub_a0 = _pt_on_rail(a0, a1, curr_u)
                    sub_a1 = a1
                    sub_b0 = _pt_on_rail(b0, b1, curr_u)
                    sub_b1 = b1
                    mesh.add_face([sub_a0, sub_b0, sub_b1, sub_a1])
                    face_map[face_idx] = i
                    face_idx += 1

            # 2. Topo (Z=altura)
            mesh.add_face([a0 + zv_curr, a1 + zv_curr, b1 + zv_curr, b0 + zv_curr])
            face_map[face_idx] = i
            face_idx += 1

            open_sa_set = set(open_side_a) if open_side_a else set()
            open_sb_set = set(open_side_b) if open_side_b else set()

            # 3 e 4. Faces A e B e túneis das aberturas
            if not seg_openings:
                # 3. Face A inteiriça
                if i not in open_sa_set:
                    face_a = [a1]
                    if nxt_seg is not None and h_next < h_curr:
                        face_a.append(a1 + QVector3D(0, 0, h_next))
                    face_a.append(a1 + zv_curr)
                    face_a.append(a0 + zv_curr)
                    if prev_seg is not None and h_prev < h_curr:
                        face_a.append(a0 + QVector3D(0, 0, h_prev))
                    face_a.append(a0)
                    mesh.add_face(face_a)
                    face_map[face_idx] = i
                    face_idx += 1

                # 4. Face B inteiriça
                if i not in open_sb_set:
                    face_b = [b0]
                    if prev_seg is not None and h_prev < h_curr:
                        face_b.append(b0 + QVector3D(0, 0, h_prev))
                    face_b.append(b0 + zv_curr)
                    face_b.append(b1 + zv_curr)
                    if nxt_seg is not None and h_next < h_curr:
                        face_b.append(b1 + QVector3D(0, 0, h_next))
                    face_b.append(b1)
                    mesh.add_face(face_b)
                    face_map[face_idx] = i
                    face_idx += 1
            else:
                # Ordena recortes por u0
                sorted_ops = sorted(seg_openings, key=lambda o: float(o.get("u0", 0.0)))

                # Separa aberturas no chao (portas: peitoril <= 0.05) de janelas (peitoril > 0.05)
                ground_openings = []
                hole_openings = []

                for op in sorted_ops:
                    u0 = max(0.0, min(1.0, float(op.get("u0", 0.0))))
                    u1 = max(0.0, min(1.0, float(op.get("u1", 1.0))))
                    if u0 > u1:
                        u0, u1 = u1, u0
                    z_peit = max(0.0, float(op.get("peitoril_m", 0.0)))
                    alt_op = max(0.1, float(op.get("altura_m", 2.1)))
                    z_verga = min(h_curr, z_peit + alt_op)
                    op_data = {
                        "u0": u0, "u1": u1,
                        "z_peit": z_peit, "z_verga": z_verga,
                        "alt_op": alt_op
                    }
                    if z_peit <= 0.05:
                        ground_openings.append(op_data)
                    else:
                        hole_openings.append(op_data)

                # Constroi o contorno externo da Face A
                # Para evitar fatiar a parede em paineis separados que quebram a estanqueidade
                # e criam linhas visiveis, a Face A e uma unica face continua com contorno em U invertido
                # contornando as aberturas do chao e com hole_loops para janelas.
                if i not in open_sa_set:
                    face_a = [a1]
                    if nxt_seg is not None and h_next < h_curr:
                        face_a.append(a1 + QVector3D(0, 0, h_next))
                    face_a.append(a1 + zv_curr)
                    face_a.append(a0 + zv_curr)
                    if prev_seg is not None and h_prev < h_curr:
                        face_a.append(a0 + QVector3D(0, 0, h_prev))
                    face_a.append(a0)

                    # Se houver portas (vao ate o chao), incorpora ao contorno da base (de a0 para a1)
                    if ground_openings:
                        for g_op in ground_openings:
                            va0 = _pt_on_rail(a0, a1, g_op["u0"])
                            va1 = _pt_on_rail(a0, a1, g_op["u1"])
                            zv_v = QVector3D(0, 0, g_op["z_verga"])
                            face_a.extend([va0, va0 + zv_v, va1 + zv_v, va1])

                    # Buracos de janelas para Face A
                    hole_loops_a = []
                    for h_op in hole_openings:
                        va0 = _pt_on_rail(a0, a1, h_op["u0"])
                        va1 = _pt_on_rail(a0, a1, h_op["u1"])
                        zv_p = QVector3D(0, 0, h_op["z_peit"])
                        zv_v = QVector3D(0, 0, h_op["z_verga"])
                        hole_loops_a.append([va0 + zv_p, va1 + zv_p, va1 + zv_v, va0 + zv_v])

                    mesh.add_face(face_a, hole_loops=hole_loops_a if hole_loops_a else None)
                    face_map[face_idx] = i
                    face_idx += 1

                # Constroi o contorno externo da Face B
                if i not in open_sb_set:
                    face_b = [b0]
                    if prev_seg is not None and h_prev < h_curr:
                        face_b.append(b0 + QVector3D(0, 0, h_prev))
                    face_b.append(b0 + zv_curr)
                    face_b.append(b1 + zv_curr)
                    if nxt_seg is not None and h_next < h_curr:
                        face_b.append(b1 + QVector3D(0, 0, h_next))
                    face_b.append(b1)

                    # Se houver portas no chao, incorpora ao contorno da base (de b1 para b0)
                    if ground_openings:
                        for g_op in reversed(ground_openings):
                            vb0 = _pt_on_rail(b0, b1, g_op["u0"])
                            vb1 = _pt_on_rail(b0, b1, g_op["u1"])
                            zv_v = QVector3D(0, 0, g_op["z_verga"])
                            face_b.extend([vb1, vb1 + zv_v, vb0 + zv_v, vb0])

                    # Buracos de janelas para Face B
                    hole_loops_b = []
                    for h_op in hole_openings:
                        vb0 = _pt_on_rail(b0, b1, h_op["u0"])
                        vb1 = _pt_on_rail(b0, b1, h_op["u1"])
                        zv_p = QVector3D(0, 0, h_op["z_peit"])
                        zv_v = QVector3D(0, 0, h_op["z_verga"])
                        hole_loops_b.append([vb0 + zv_p, vb0 + zv_v, vb1 + zv_v, vb1 + zv_p])

                    mesh.add_face(face_b, hole_loops=hole_loops_b if hole_loops_b else None)
                    face_map[face_idx] = i
                    face_idx += 1

                # Constroi as faces internas dos tuneis para todas as aberturas (portas e janelas)
                for op_data in sorted_ops:
                    u0 = max(0.0, min(1.0, float(op_data.get("u0", 0.0))))
                    u1 = max(0.0, min(1.0, float(op_data.get("u1", 1.0))))
                    if u0 > u1:
                        u0, u1 = u1, u0
                    z_peit = max(0.0, float(op_data.get("peitoril_m", 0.0)))
                    alt_op = max(0.1, float(op_data.get("altura_m", 2.1)))
                    z_verga = min(h_curr, z_peit + alt_op)

                    va0 = _pt_on_rail(a0, a1, u0)
                    va1 = _pt_on_rail(a0, a1, u1)
                    vb0 = _pt_on_rail(b0, b1, u0)
                    vb1 = _pt_on_rail(b0, b1, u1)

                    zv_peit = QVector3D(0, 0, z_peit)
                    zv_verga = QVector3D(0, 0, z_verga)

                    # 1. Peitoril topo do tunel (apenas se for janela com peitoril > 0)
                    if z_peit > 0.05:
                        mesh.add_face([va0 + zv_peit, vb0 + zv_peit, vb1 + zv_peit, va1 + zv_peit])
                        face_map[face_idx] = i
                        face_idx += 1

                    # 2. Boneca esquerda (u0):
                    mesh.add_face([va0 + zv_peit, va0 + zv_verga, vb0 + zv_verga, vb0 + zv_peit])
                    face_map[face_idx] = i
                    face_idx += 1

                    # 3. Boneca direita (u1):
                    mesh.add_face([vb1 + zv_peit, vb1 + zv_verga, va1 + zv_verga, va1 + zv_peit])
                    face_map[face_idx] = i
                    face_idx += 1

                    # 4. Verga inferior do tunel (olhando para baixo):
                    mesh.add_face([va0 + zv_verga, va1 + zv_verga, vb1 + zv_verga, vb0 + zv_verga])
                    face_map[face_idx] = i
                    face_idx += 1

            open_q_set = set(open_quinas) if open_quinas is not None else (set(range(n_segs)) if is_closed else set(range(1, n_segs)))

            # 5. Canto Inicial (Quina i): corte em esquadria fechando o sólido do segmento
            if (is_closed or i > 0) and (i not in open_q_set):
                h_c0 = min(h_curr, h_prev) if prev_seg is not None else h_curr
                zv_c0 = QVector3D(0, 0, h_c0)
                mesh.add_face([a0, a0 + zv_c0, b0 + zv_c0, b0])
                face_map[face_idx] = i
                face_idx += 1

            # 6. Canto Final (Quina nxt): corte em esquadria fechando o sólido do segmento
            if (is_closed or i < n_segs - 1) and (nxt not in open_q_set):
                h_c1 = min(h_curr, h_next) if nxt_seg is not None else h_curr
                zv_c1 = QVector3D(0, 0, h_c1)
                mesh.add_face([b1, b1 + zv_c1, a1 + zv_c1, a1])
                face_map[face_idx] = i
                face_idx += 1

        if not is_closed:
            zv_0 = QVector3D(0, 0, alturas[0])
            zv_end = QVector3D(0, 0, alturas[-1])
            if not open_start:
                mesh.add_face([pts_B[0], pts_A[0], pts_A[0] + zv_0, pts_B[0] + zv_0])
                face_map[face_idx] = 0
                face_idx += 1
            if not open_end:
                mesh.add_face([pts_A[-1], pts_B[-1], pts_B[-1] + zv_end, pts_A[-1] + zv_end])
                face_map[face_idx] = n_segs - 1
                face_idx += 1

        # 7. Suaviza todas as arestas internas entre faces coplanares (costuras de esquadria, piso e topo)
        # para que o encontro das quinas e divisões não mostre linhas indesejadas no sólido
        for e in mesh.edges:
            if len(e.faces) == 2:
                n0 = e.faces[0].normal()
                n1 = e.faces[1].normal()
                # Se as duas faces forem estritamente coplanares (mesma orientação de normal)
                if abs(QVector3D.dotProduct(n0, n1) - 1.0) < 1e-4:
                    e.soft = True

        return mesh, face_map

    @classmethod
    def _clean_polygon_points(cls, points: List[QVector3D]) -> List[QVector3D]:
        """Remove pontos duplicados ou colineares consecutivos do contorno."""
        clean: List[QVector3D] = []
        for p in points:
            if not clean or (p - clean[-1]).length() > 1e-4:
                clean.append(p)
        if len(clean) > 2 and (clean[0] - clean[-1]).length() < 1e-4:
            clean.pop()
        return clean

    @classmethod
    def build_floor_group(cls, scene, points: List[QVector3D], z_base: float = 0.0) -> Optional[Group]:
        """Gera o sólido do piso fechado a partir dos pontos de perímetro sem arestas de corte internas."""
        pts_clean = cls._clean_polygon_points(points)
        if len(pts_clean) < 3:
            return None

        esp_piso = 0.05
        z_floor = z_base - esp_piso

        mesh = Mesh()
        pts_top = [QVector3D(p.x(), p.y(), z_base) for p in pts_clean]
        pts_bot = [QVector3D(p.x(), p.y(), z_floor) for p in pts_clean]

        try:
            # Calcula orientação (área assinada 2D) para orientar as normais para fora
            area = sum(
                (pts_top[i].x() * pts_top[(i + 1) % len(pts_top)].y() -
                 pts_top[(i + 1) % len(pts_top)].x() * pts_top[i].y())
                for i in range(len(pts_top))
            )

            # Face Superior (Top) - adicionada como n-gon limpo, sem arestas de corte no meio do chão
            if area > 0:
                mesh.add_face(list(pts_top))
                mesh.add_face(list(reversed(pts_bot)))
            else:
                mesh.add_face(list(reversed(pts_top)))
                mesh.add_face(list(pts_bot))

            # Paredes Laterais da laje do piso
            n = len(pts_top)
            for i in range(n):
                j = (i + 1) % n
                if area > 0:
                    mesh.add_face([pts_top[i], pts_bot[i], pts_bot[j], pts_top[j]])
                else:
                    mesh.add_face([pts_top[j], pts_bot[j], pts_bot[i], pts_top[i]])
        except Exception:
            return None

        layer_name = "Piso"
        if scene.layer(layer_name) is None:
            scene.layers.append(Layer(layer_name))

        grp = Group(mesh, name="Piso Ambiente")
        grp.layer = layer_name
        grp.ext = {"trazomob": {"kind": "floor"}, "trazomob_floor": True, "motion_locked": True}
        return grp

    @classmethod
    def build_ceiling_group(cls, scene, points: List[QVector3D], altura_m: float = 2.60, z_base: float = 0.0) -> Optional[Group]:
        """Gera o sólido do teto / forro de gesso fechado no pé-direito do ambiente."""
        pts_clean = cls._clean_polygon_points(points)
        if len(pts_clean) < 3:
            return None

        esp_teto = 0.05
        z_sub = float(z_base) + float(altura_m)
        z_top = z_sub + esp_teto

        mesh = Mesh()
        pts_sub = [QVector3D(p.x(), p.y(), z_sub) for p in pts_clean]
        pts_sup = [QVector3D(p.x(), p.y(), z_top) for p in pts_clean]

        try:
            area = sum(
                (pts_sub[i].x() * pts_sub[(i + 1) % len(pts_sub)].y() -
                 pts_sub[(i + 1) % len(pts_sub)].x() * pts_sub[i].y())
                for i in range(len(pts_sub))
            )

            # Face inferior do teto (visível de dentro do cômodo olhando para cima: normal para baixo)
            if area > 0:
                mesh.add_face(list(reversed(pts_sub)))
                mesh.add_face(list(pts_sup))
            else:
                mesh.add_face(list(pts_sub))
                mesh.add_face(list(reversed(pts_sup)))

            # Laterais da laje do teto
            n = len(pts_sub)
            for i in range(n):
                j = (i + 1) % n
                if area > 0:
                    mesh.add_face([pts_sub[i], pts_sub[j], pts_sup[j], pts_sup[i]])
                else:
                    mesh.add_face([pts_sub[j], pts_sub[i], pts_sup[i], pts_sup[j]])
        except Exception:
            return None

        layer_name = "Teto"
        if scene.layer(layer_name) is None:
            scene.layers.append(Layer(layer_name))

        grp = Group(mesh, name="Teto Ambiente")
        grp.layer = layer_name
        grp.ext = {"trazomob": {"kind": "ceiling"}, "trazomob_ceiling": True, "motion_locked": True}
        return grp

    APPEARANCE_KEYS = ("color", "texture", "opacity", "mat", "paint_name")

    @classmethod
    def copy_face_appearance(cls, src_group, dst_group) -> bool:
        """Transfere cor/textura/material de um grupo para outro, face a face.

        Usado quando a planta 2D reconstrói paredes, pisos e tetos: sem isto,
        clicar em Concluir apagava a textura aplicada pelo usuário. A ordem das
        faces geradas é estável (tampa, fundo, laterais), então a cópia é feita
        por índice, preservando também o material do grupo quando ausente.
        """
        if src_group is None or dst_group is None:
            return False

        src_faces = getattr(getattr(src_group, "mesh", None), "faces", None) or []
        dst_faces = getattr(getattr(dst_group, "mesh", None), "faces", None) or []
        changed = False
        for src_f, dst_f in zip(src_faces, dst_faces):
            src_attrs = getattr(src_f, "attrs", None) or {}
            if not src_attrs:
                continue
            if getattr(dst_f, "attrs", None) is None:
                dst_f.attrs = {}
            for key in cls.APPEARANCE_KEYS:
                if key in src_attrs:
                    dst_f.attrs[key] = src_attrs[key]
                    changed = True

        # O destino é sempre recém-criado e pode já trazer o material padrão
        # branco acetinado. Se a origem tem material (inclusive o do usuário),
        # ele vence: é assim que a pintura por grupo sobrevive ao Concluir.
        src_mat = getattr(src_group, "material", None)
        if src_mat:
            dst_group.material = dict(src_mat)
            changed = True
        return changed

    @classmethod
    def extract_wall_data_from_mesh(cls, group: Group) -> dict | None:
        """Extrai parâmetros de alvenaria de qualquer sólido 3D de parede (mesmo desenhado com retângulo/push-pull)."""
        mesh = getattr(group, "mesh", None)
        if not mesh or not getattr(mesh, "vertices", None) or len(mesh.faces) < 4:
            return None
        verts = [v.position if hasattr(v, "position") else v for v in mesh.vertices]
        min_z = min(p.z() for p in verts)
        max_z = max(p.z() for p in verts)
        height = max_z - min_z
        if height < 0.5:
            return None

        vert_faces = []
        for f in mesh.faces:
            n = f.normal()
            if abs(n.z()) < 0.1 and f.area() > 0.05:
                vert_faces.append(f)
        if len(vert_faces) < 2:
            return None

        sorted_faces = sorted(vert_faces, key=lambda f: f.area(), reverse=True)
        f1 = sorted_faces[0]
        n1 = f1.normal()
        f2 = None
        for f in sorted_faces[1:]:
            n2 = f.normal()
            if QVector3D.dotProduct(n1, n2) < -0.80:
                f2 = f
                break
        if not f2:
            return None

        pts1 = [v.position if hasattr(v, "position") else v for v in f1.vertices]
        pts2 = [v.position if hasattr(v, "position") else v for v in f2.vertices]
        c1 = sum(pts1, QVector3D(0, 0, 0)) / len(pts1)
        c2 = sum(pts2, QVector3D(0, 0, 0)) / len(pts2)
        espessura = abs(QVector3D.dotProduct(c2 - c1, n1.normalized()))

        u_dir = QVector3D(-n1.y(), n1.x(), 0.0).normalized()
        projs = [QVector3D.dotProduct(p, u_dir) for p in pts1]
        min_u, max_u = min(projs), max(projs)
        seg_len = max_u - min_u
        if seg_len < 0.2:
            return None

        c_mid = (c1 + c2) * 0.5
        c_mid_z0 = QVector3D(c_mid.x(), c_mid.y(), min_z)
        p0 = c_mid_z0 - u_dir * (seg_len * 0.5)
        p1 = c_mid_z0 + u_dir * (seg_len * 0.5)

        return {
            "pontos": [[p0.x(), p0.y(), p0.z()], [p1.x(), p1.y(), p1.z()]],
            "is_closed": False,
            "altura": height,
            "espessura": espessura,
            "alinhamento": "centro",
        }

    @classmethod
    def ensure_wall_metadata_on_scene_walls(cls, scene) -> None:
        """Garante que todas as paredes da cena (mesmo importadas ou criadas nativamente) sejam reconhecidas."""
        for g in getattr(scene, "groups", []):
            layer_str = str(getattr(g, "layer", "")).lower()
            name_str = str(getattr(g, "name", "")).lower()
            ext = getattr(g, "ext", None)
            has_wall_ext = isinstance(ext, dict) and "trazomob_wall" in ext
            if not has_wall_ext:
                is_candidate = (
                    "parede" in layer_str or "wall" in layer_str
                    or "parede" in name_str or "muro" in name_str
                    or (isinstance(ext, dict) and "openings" in ext)
                )
                if is_candidate:
                    w_data = cls.extract_wall_data_from_mesh(g)
                    if w_data:
                        if getattr(g, "ext", None) is None:
                            g.ext = {}
                        g.ext["trazomob_wall"] = w_data

    @classmethod
    @staticmethod
    def _scene_openings_stamp(scene) -> tuple:
        """Assinatura barata do estado que afeta os vãos (sem calcular bounds)."""
        groups = getattr(scene, "groups", ()) or ()
        parts = [getattr(scene, "version", 0), len(groups)]
        for g in groups:
            parts.append(id(g))
            mesh = getattr(g, "mesh", None)
            if mesh is not None:
                parts.append(getattr(mesh, "_mut_serial", 0))
            for child in getattr(g, "children", ()) or ():
                cmesh = getattr(child, "mesh", None)
                if cmesh is not None:
                    parts.append((id(child), getattr(cmesh, "_mut_serial", 0)))
        return tuple(parts)

    @classmethod
    def sync_scene_wall_openings(cls, scene) -> bool:
        """Varre todas as esquadrias da cena e atualiza automaticamente os recortes/vãos nas paredes."""
        if not scene:
            return False

        # Sidebar e bootstrap disparam a varredura no mesmo sceneVersionChanged.
        # Uma assinatura barata evita refazer o trabalho quando nada mudou —
        # inclui _mut_serial porque arrastes mudam vértices sem subir scene.version.
        stamp = cls._scene_openings_stamp(scene)
        if getattr(scene, "_trazomob_wall_sync_stamp", None) == stamp:
            return False

        import os as _os
        import time as _time
        _perf = bool(_os.environ.get("INGETRAZO_PERF"))
        _t0 = _time.perf_counter() if _perf else 0.0

        def _log(elapsed_walls: int = 0, changed: bool = False) -> None:
            if not _perf:
                return
            from core.history import _plog
            _plog("trazomob.wall_sync", (_time.perf_counter() - _t0) * 1000.0,
                  f"walls={elapsed_walls} changed={changed}", floor=0.0)

        cls.ensure_wall_metadata_on_scene_walls(scene)

        walls = [
            g for g in getattr(scene, "groups", [])
            if hasattr(g, "ext") and isinstance(g.ext, dict) and "trazomob_wall" in g.ext
        ]
        if not walls:
            _log()
            return False

        from ..domain.entity import get_trazomob
        esquadrias = [
            g for g in getattr(scene, "groups", [])
            if hasattr(g, "ext") and isinstance(g.ext, dict) and (
                get_trazomob(g).get("kind") == "esquadria"
                or "trazomob_esquadria" in g.ext
                or getattr(g, "layer", "") == "ESQUADRIAS"
                or (("porta" in g.name.lower() or "janela" in g.name.lower()) and "roupeiro" not in g.name.lower() and "balcao" not in g.name.lower() and "armario" not in g.name.lower() and "aereo" not in g.name.lower() and get_trazomob(g).get("kind") != "module")
            )
        ]

        # Pré-calcula bounding box no espaço de mundo e orientação horizontal (esq_u)
        # de cada esquadria UMA ÚNICA VEZ fora do loop de paredes (sem soldar malha via world_mesh).
        from ..interaction.magnetic_drag import get_module_reference_bounds
        esq_records = []
        for esq in esquadrias:
            bounds = get_module_reference_bounds(esq)
            if not bounds:
                continue
            min_x, max_x, min_y, max_y, min_z, max_z = bounds
            cx, cy = (min_x + max_x) * 0.5, (min_y + max_y) * 0.5
            center_pt = QVector3D(cx, cy, 0.0)
            esq_info = esq.ext.get("trazomob_esquadria") or esq.ext.get("trazomob_module") or esq.ext.get("trazomob") or {}
            prof_m = float(esq_info.get("esp_parede_mm", esq_info.get("profundidade", 150.0))) / 1000.0
            larg_m = float(esq_info.get("largura_mm", esq_info.get("largura", max(max_x - min_x, max_y - min_y) * 1000.0))) / 1000.0
            alt_m = float(esq_info.get("altura_mm", esq_info.get("altura", (max_z - min_z) * 1000.0))) / 1000.0
            peit_meta = float(esq_info.get("peitoril_mm", 0.0) or 0.0) / 1000.0
            peit_m = peit_meta if peit_meta > 0.0 else max(0.0, min_z)

            # Determina o vetor diretor horizontal da largura da esquadria (esq_u)
            if "rot_z" in esq_info and esq_info["rot_z"] is not None:
                rad = math.radians(float(esq_info["rot_z"]))
                esq_u = QVector3D(math.cos(rad), math.sin(rad), 0.0).normalized()
            else:
                dx_b = max_x - min_x
                dy_b = max_y - min_y
                if dx_b >= dy_b * 1.2:
                    esq_u = QVector3D(1.0, 0.0, 0.0)
                elif dy_b >= dx_b * 1.2:
                    esq_u = QVector3D(0.0, 1.0, 0.0)
                else:
                    esq_u = None

            esq_records.append({
                "center_pt": center_pt,
                "prof_m": prof_m,
                "larg_m": larg_m,
                "alt_m": alt_m,
                "peit_m": peit_m,
                "esq_u": esq_u,
            })

        any_wall_changed = False
        for wall in walls:
            w_ext = wall.ext["trazomob_wall"]
            if w_ext.get("is_column"):
                continue
            pts_data = w_ext.get("pontos", [])
            is_closed = w_ext.get("is_closed", False)
            n_pts = len(pts_data)
            n_segs = n_pts if is_closed else max(0, n_pts - 1)
            if n_segs < 1:
                continue

            openings = []
            w_z_base = float(w_ext.get("z_base", pts_data[0][2] if pts_data and len(pts_data[0]) >= 3 else 0.0))
            raw_alt = w_ext.get("alturas", w_ext.get("altura", 2.6))
            if isinstance(raw_alt, (list, tuple)):
                w_alt = max((float(x) for x in raw_alt), default=2.6)
            else:
                w_alt = float(raw_alt)

            for rec in esq_records:
                center_pt = rec["center_pt"]
                prof_m = rec["prof_m"]
                larg_m = rec["larg_m"]
                alt_m = rec["alt_m"]
                peit_m = rec["peit_m"]
                esq_u = rec["esq_u"]

                # Verifica se a esquadria intercepta a parede verticalmente no eixo Z
                esq_z_min = peit_m
                esq_z_max = peit_m + alt_m
                if esq_z_max < w_z_base - 0.10 or esq_z_min > w_z_base + w_alt + 0.10:
                    continue

                for seg_i in range(n_segs):
                    p0 = QVector3D(*pts_data[seg_i])
                    p1 = QVector3D(*pts_data[(seg_i + 1) % n_pts])
                    seg_v = p1 - p0
                    seg_len = seg_v.length()
                    if seg_len < 0.05:
                        continue
                    seg_u = seg_v.normalized()
                    seg_n = QVector3D(-seg_u.y(), seg_u.x(), 0.0).normalized()

                    # 1. A esquadria deve estar orientada paralelamente ao segmento da parede!
                    # Impede que uma porta próxima ao canto corte a parede perpendicular adjacente.
                    if esq_u is not None and abs(QVector3D.dotProduct(esq_u, seg_u)) < 0.80:
                        continue

                    dist_norm = abs(QVector3D.dotProduct(center_pt - p0, seg_n))
                    wall_esp = float(w_ext.get("espessura", 0.15))

                    # 2. Tolerância transversal precisa e centro projetado dentro do vão do segmento
                    if dist_norm <= wall_esp + prof_m * 0.5 + 0.12:
                        proj_u = QVector3D.dotProduct(center_pt - p0, seg_u)
                        if not (-0.05 <= proj_u <= seg_len + 0.05):
                            continue

                        half_w = larg_m * 0.5
                        u0_m = max(0.0, proj_u - half_w)
                        u1_m = min(seg_len, proj_u + half_w)

                        if u1_m > u0_m + 0.05:
                            rel_peit = max(0.0, peit_m - w_z_base)
                            openings.append({
                                "segment_index": seg_i,
                                "u0": u0_m / seg_len,
                                "u1": u1_m / seg_len,
                                "altura_m": alt_m,
                                "peitoril_m": rel_peit,
                            })

            old_openings = w_ext.get("openings", [])
            def _op_key(op):
                return (op["segment_index"], round(op["u0"], 3), round(op["u1"], 3), round(op["altura_m"], 3), round(op["peitoril_m"], 3))

            set_old = set(_op_key(o) for o in old_openings)
            set_new = set(_op_key(o) for o in openings)

            if set_old != set_new:
                w_ext["openings"] = openings
                pts_vec = [QVector3D(p[0], p[1], p[2]) for p in pts_data]
                quad_2d = w_ext.get("quad_2d")
                if not quad_2d and w_ext.get("is_graph_2d") and "graph_2d" in w_ext and "segment_id" in w_ext:
                    try:
                        from ..wall.plan_2d import WallGraph2D
                        g2d = WallGraph2D.from_dict(w_ext["graph_2d"])
                        polys = g2d.compute_wall_polygons()
                        sid = int(w_ext["segment_id"])
                        if sid in polys:
                            q = polys[sid]
                            quad_2d = [[q[0][0], q[0][1]], [q[1][0], q[1][1]], [q[2][0], q[2][1]], [q[3][0], q[3][1]]]
                            w_ext["quad_2d"] = quad_2d
                    except Exception:
                        quad_2d = None

                new_mesh, face_map = cls.compute_wall_mesh(
                    pts=pts_vec,
                    is_closed=is_closed,
                    altura_m=w_ext.get("alturas", w_ext.get("altura", 2.6)),
                    espessura_m=w_ext.get("espessura", 0.15),
                    alinhamento=w_ext.get("alinhamento", "interno"),
                    open_quinas=w_ext.get("open_quinas"),
                    open_side_a=w_ext.get("open_side_a"),
                    open_side_b=w_ext.get("open_side_b"),
                    openings=openings,
                    quad_2d=quad_2d,
                )
                if hasattr(wall, "mesh") and hasattr(wall.mesh, "faces"):
                    old_attrs = [f.attrs for f in wall.mesh.faces if hasattr(f, "attrs")]
                    for idx_f, nf in enumerate(new_mesh.faces):
                        if idx_f < len(old_attrs) and old_attrs[idx_f]:
                            for k in ("color", "texture", "opacity", "mat"):
                                if k in old_attrs[idx_f]:
                                    nf.attrs[k] = old_attrs[idx_f][k]

                wall.mesh = new_mesh
                wall.mesh._chunk_dirty = True
                wall.mesh._attrs_dirty = True
                wall.mesh._mut_serial = getattr(wall.mesh, "_mut_serial", 0) + 1
                w_ext["face_segment_map"] = face_map
                any_wall_changed = True

        if any_wall_changed:
            scene.version += 1
            if hasattr(scene, "_bounds_cache"):
                scene._bounds_cache = None

        # Marca o estado final: se paredes mudaram, o novo estado já foi sincronizado.
        try:
            scene._trazomob_wall_sync_stamp = cls._scene_openings_stamp(scene)
        except Exception:
            pass
        _log(len(walls), any_wall_changed)
        return any_wall_changed


