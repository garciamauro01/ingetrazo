# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Estrutura de dados para Planta Baixa 2D de paredes e extrusão para malhas 3D sólidas."""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from PySide6.QtGui import QVector3D

from core.group import Group
from core.layers import Layer
from core.mesh import Mesh

Point2D = Tuple[float, float]

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from .plan_2d import dist_2d, line_intersection_2d


class Plan2DGeometryMixin:
    """Polígonos 2D, pilares e extrusão 3D extraídos de WallGraph2D."""

    def compute_wall_polygons(self) -> Dict[int, Tuple[Point2D, Point2D, Point2D, Point2D]]:
        """Calcula os 4 vértices 2D (c0, c1, c2, c3) para cada segmento de parede.

        c0 e c1 são os vértices na borda 'esquerda' (de node_a a node_b).
        c2 e c3 são os vértices na borda 'direita' (de node_b a node_a).

        Respeita o alinhamento da parede:
        - "centro": a linha de nós passa no eixo central (offset esquerdo = +th/2, direito = -th/2)
        - "interno": a linha de nós passa na face interna/direita (offset esquerdo = +th, direito = 0)
        - "externo": a linha de nós passa na face externa/esquerda (offset esquerdo = 0, direito = -th)

        Em nós de canto (onde 2 paredes se encontram), calcula a bissetriz (miter a 45°
        para ângulos retos), fechando perfeitamente os cantos internos e externos.
        """
        # Mapeia quais segmentos incidem em cada nó
        node_segments: Dict[int, List[int]] = {nid: [] for nid in self.nodes}
        for seg_id, seg in self.segments.items():
            node_segments[seg.node_a_id].append(seg_id)
            node_segments[seg.node_b_id].append(seg_id)

        polys: Dict[int, Tuple[Point2D, Point2D, Point2D, Point2D]] = {}
        for seg_id, seg in self.segments.items():
            na = self.nodes[seg.node_a_id]
            nb = self.nodes[seg.node_b_id]

            dx = nb.x - na.x
            dy = nb.y - na.y
            seg_len = math.hypot(dx, dy)
            off_left, off_right = self.segment_offsets(seg)

            if seg_len < 1e-6:
                c0 = (na.x - off_right, na.y - off_right)
                c1 = (nb.x - off_right, nb.y - off_right)
                c2 = (nb.x + off_left, nb.y + off_left)
                c3 = (na.x + off_left, na.y + off_left)
                polys[seg_id] = (c0, c1, c2, c3)
                continue

            ux = dx / seg_len
            uy = dy / seg_len
            # Normal à esquerda
            nx = -uy
            ny = ux

            # Padrão plano nas extremidades (se livres)
            c0 = (na.x + nx * off_left, na.y + ny * off_left)
            c3 = (na.x - nx * off_right, na.y - ny * off_right)
            c1 = (nb.x + nx * off_left, nb.y + ny * off_left)
            c2 = (nb.x - nx * off_right, nb.y - ny * off_right)
            polys[seg_id] = (c0, c1, c2, c3)

        # Pré-computa as retas de borda esquerda (L) e direita (R) de cada segmento
        # no seu referencial canônico de a->b.
        seg_rails: Dict[int, Dict[str, Tuple[Point2D, Point2D]]] = {}
        for seg_id, seg in self.segments.items():
            na = self.nodes[seg.node_a_id]
            nb = self.nodes[seg.node_b_id]
            dx = nb.x - na.x
            dy = nb.y - na.y
            slen = math.hypot(dx, dy)
            if slen < 1e-6:
                continue
            ux = dx / slen
            uy = dy / slen
            nx = -uy
            ny = ux
            off_l, off_r = self.segment_offsets(seg)
            seg_rails[seg_id] = {
                "L": ((na.x + nx * off_l, na.y + ny * off_l), (ux, uy)),
                "R": ((na.x - nx * off_r, na.y - ny * off_r), (ux, uy)),
                "u": (ux, uy),
            }

        # Para cada nó com grau 2 (canto), calculamos a bissetriz / corte em 45°
        for nid, seg_ids in node_segments.items():
            if len(seg_ids) != 2:
                continue

            s_id1, s_id2 = seg_ids
            if s_id1 not in seg_rails or s_id2 not in seg_rails:
                continue
            seg1 = self.segments[s_id1]
            seg2 = self.segments[s_id2]
            node = self.nodes[nid]

            # Vetor unitário saindo do nó nid ao longo de seg1
            u1 = seg_rails[s_id1]["u"] if seg1.node_a_id == nid else (-seg_rails[s_id1]["u"][0], -seg_rails[s_id1]["u"][1])
            # Vetor unitário saindo do nó nid ao longo de seg2
            u2 = seg_rails[s_id2]["u"] if seg2.node_a_id == nid else (-seg_rails[s_id2]["u"][0], -seg_rails[s_id2]["u"][1])

            # Produto vetorial 2D (u1 x u2) determina para qual lado a parede vira
            cross = u1[0] * u2[1] - u1[1] * u2[0]
            if abs(cross) < 1e-4:
                # Paredes colineares
                continue

            # Determina qual trilho (L ou R) de cada segmento se encontra no canto interno e externo.
            # Olhando a partir do nó nid ao longo de u1:
            # - se nid == node_a, a esquerda do vetor saindo é 'L', direita é 'R'
            # - se nid == node_b, a esquerda do vetor saindo é 'R', direita é 'L'
            # Se cross > 0 (gira para esquerda):
            #   o lado interno é a esquerda de u1 se unindo à direita de u2.
            # Se cross < 0 (gira para direita):
            #   o lado interno é a direita de u1 se unindo à esquerda de u2.
            if cross > 0:
                rail1_in = "L" if seg1.node_a_id == nid else "R"
                rail2_in = "R" if seg2.node_a_id == nid else "L"
                rail1_out = "R" if seg1.node_a_id == nid else "L"
                rail2_out = "L" if seg2.node_a_id == nid else "R"
            else:
                rail1_in = "R" if seg1.node_a_id == nid else "L"
                rail2_in = "L" if seg2.node_a_id == nid else "R"
                rail1_out = "L" if seg1.node_a_id == nid else "R"
                rail2_out = "R" if seg2.node_a_id == nid else "L"

            p_in = line_intersection_2d(
                seg_rails[s_id1][rail1_in][0], seg_rails[s_id1][rail1_in][1],
                seg_rails[s_id2][rail2_in][0], seg_rails[s_id2][rail2_in][1]
            )
            p_out = line_intersection_2d(
                seg_rails[s_id1][rail1_out][0], seg_rails[s_id1][rail1_out][1],
                seg_rails[s_id2][rail2_out][0], seg_rails[s_id2][rail2_out][1]
            )

            max_d = max(seg1.thickness, seg2.thickness) * 3.5
            if p_in and dist_2d(node.pt, p_in) <= max_d and p_out and dist_2d(node.pt, p_out) <= max_d:
                # Atribui diretamente p_in e p_out aos trilhos exatos de cada segmento,
                # garantindo que as faces nunca cruzem (sem adivinhação de distância).
                def _assign_to_seg(sid: int, rail_name: str, pt: Point2D) -> None:
                    s = self.segments[sid]
                    c_0, c_1, c_2, c_3 = polys[sid]
                    if s.node_a_id == nid:
                        # Extremidade A: 'L' é c0, 'R' é c3
                        if rail_name == "L":
                            c_0 = pt
                        else:
                            c_3 = pt
                    else:
                        # Extremidade B: 'L' é c1, 'R' é c2
                        if rail_name == "L":
                            c_1 = pt
                        else:
                            c_2 = pt
                    polys[sid] = (c_0, c_1, c_2, c_3)

                _assign_to_seg(s_id1, rail1_in, p_in)
                _assign_to_seg(s_id1, rail1_out, p_out)
                _assign_to_seg(s_id2, rail2_in, p_in)
                _assign_to_seg(s_id2, rail2_out, p_out)

        # Ajuste para nós com coluna (T-junctions ou X):
        # As paredes que chegam ao nó com coluna devem terminar exatamente na face da coluna,
        # sem invadir o espaço interno da coluna nem o espaço das outras paredes.
        columns = self.compute_columns()
        for nid, col_quad in columns.items():
            for sid in node_segments.get(nid, []):
                s_obj = self.segments[sid]
                c0, c1, c2, c3 = polys[sid]

                na = self.nodes[s_obj.node_a_id]
                nb = self.nodes[s_obj.node_b_id]
                dx = nb.x - na.x
                dy = nb.y - na.y
                slen = math.hypot(dx, dy)
                if slen < 1e-6:
                    continue
                ux = dx / slen
                uy = dy / slen

                if s_obj.node_a_id == nid:
                    # Parede começa no nó nid e vai em direção a nb (direção +u)
                    # c0 (borda esquerda) e c3 (borda direita) devem ser aparadas na coluna
                    p0 = self._intersect_quad_with_line(col_quad, c1, (-ux, -uy))
                    p3 = self._intersect_quad_with_line(col_quad, c2, (-ux, -uy))
                    if p0:
                        c0 = p0
                    if p3:
                        c3 = p3
                else:
                    # Parede termina no nó nid (vem de na em direção a nb, direção +u)
                    # c1 (borda esquerda) e c2 (borda direita) devem ser aparadas na coluna
                    p1 = self._intersect_quad_with_line(col_quad, c0, (ux, uy))
                    p2 = self._intersect_quad_with_line(col_quad, c3, (ux, uy))
                    if p1:
                        c1 = p1
                    if p2:
                        c2 = p2

                polys[sid] = (c0, c1, c2, c3)

        return polys

    @staticmethod
    def _intersect_quad_with_line(quad: Tuple[Point2D, Point2D, Point2D, Point2D], p: Point2D, d: Point2D) -> Optional[Point2D]:
        """Calcula a interseção entre o raio p + t*d (t >= 0) e as 4 arestas do polígono quad."""
        edges = [(quad[0], quad[1]), (quad[1], quad[2]), (quad[2], quad[3]), (quad[3], quad[0])]
        pts = []
        for a, b in edges:
            adx = b[0] - a[0]
            ady = b[1] - a[1]
            det = d[0] * ady - d[1] * adx
            if abs(det) < 1e-6:
                continue
            dp = (a[0] - p[0], a[1] - p[1])
            t = (dp[0] * ady - dp[1] * adx) / det
            s = (dp[0] * d[1] - dp[1] * d[0]) / det
            if t >= -1e-4 and -1e-4 <= s <= 1.0001:
                pts.append((p[0] + t * d[0], p[1] + t * d[1]))
        if not pts:
            return None
        # Pega a interseção mais próxima do ponto de partida p
        return min(pts, key=lambda pt: (pt[0] - p[0]) ** 2 + (pt[1] - p[1]) ** 2)

    def compute_columns(self) -> Dict[int, Tuple[Point2D, Point2D, Point2D, Point2D]]:
        """Calcula as colunas estruturais nos nós que formam junção em T (ou X).

        Quando 3 ou mais paredes se encontram em um nó (ou junção em T),
        gera uma coluna quadrada separando as paredes que chegam ao nó.
        Retorna um dicionário {node_id: (c0, c1, c2, c3)}.
        """
        node_segments: Dict[int, List[int]] = {nid: [] for nid in self.nodes}
        for seg_id, seg in self.segments.items():
            node_segments[seg.node_a_id].append(seg_id)
            node_segments[seg.node_b_id].append(seg_id)

        columns: Dict[int, Tuple[Point2D, Point2D, Point2D, Point2D]] = {}
        for nid, seg_ids in node_segments.items():
            if len(seg_ids) >= 3:
                node = self.nodes[nid]
                max_th = max(self.segments[sid].thickness for sid in seg_ids)
                half = max_th / 2.0
                # Coluna perfeitamente quadrada e centrada no nó
                c0 = (node.x - half, node.y - half)
                c1 = (node.x + half, node.y - half)
                c2 = (node.x + half, node.y + half)
                c3 = (node.x - half, node.y + half)
                columns[nid] = (c0, c1, c2, c3)

        return columns

    def build_3d_group(self, scene, altura_m: float = 2.6, name: str = "Ambiente Paredes", z_base: float = 0.0) -> Optional[Group]:
        """Gera o grupo de malha 3D contínua a partir de todos os segmentos do grafo 2D.

        Salva o próprio grafo 2D serializado em ext['trazomob_wall']['graph_2d'],
        permitindo reabrir e continuar editando a qualquer momento.
        """
        if not self.segments:
            return None

        zv = QVector3D(0, 0, altura_m)
        mesh = Mesh()

        wall_polys = self.compute_wall_polygons()
        columns = self.compute_columns()

        # 1. Cada segmento de parede gera 4 cantos na base (com chanfro/miter a 45° nos cantos)
        raw_faces = []
        # 1. Cada segmento de parede gera as faces externas
        for seg_id, quad in wall_polys.items():
            s_obj = self.segments.get(seg_id)
            seg_alt = s_obj.height if (s_obj and s_obj.height is not None) else altura_m
            seg_zv = QVector3D(0, 0, seg_alt)
            p0, p1, p2, p3 = quad
            c0 = QVector3D(p0[0], p0[1], z_base)
            c1 = QVector3D(p1[0], p1[1], z_base)
            c2 = QVector3D(p2[0], p2[1], z_base)
            c3 = QVector3D(p3[0], p3[1], z_base)

            raw_faces.append([c0, c1, c2, c3])
            raw_faces.append([c3 + seg_zv, c2 + seg_zv, c1 + seg_zv, c0 + seg_zv])
            raw_faces.append([c0, c0 + seg_zv, c1 + seg_zv, c1])
            raw_faces.append([c1, c1 + seg_zv, c2 + seg_zv, c2])
            raw_faces.append([c2, c2 + seg_zv, c3 + seg_zv, c3])
            raw_faces.append([c3, c3 + seg_zv, c0 + seg_zv, c0])

        # 2. Gera as colunas estruturais 3D nos nós de junção em T (ou X)
        for nid, col_quad in columns.items():
            p0, p1, p2, p3 = col_quad
            c0 = QVector3D(p0[0], p0[1], z_base)
            c1 = QVector3D(p1[0], p1[1], z_base)
            c2 = QVector3D(p2[0], p2[1], z_base)
            c3 = QVector3D(p3[0], p3[1], z_base)

            # Como col_quad é CCW (c0->c1->c2->c3 no plano XY), invertemos a ordem para normais externas (+outward):
            raw_faces.append([c3, c2, c1, c0])
            raw_faces.append([c0 + zv, c1 + zv, c2 + zv, c3 + zv])
            raw_faces.append([c0, c1, c1 + zv, c0 + zv])
            raw_faces.append([c1, c2, c2 + zv, c1 + zv])
            raw_faces.append([c2, c3, c3 + zv, c2 + zv])
            raw_faces.append([c3, c0, c0 + zv, c3 + zv])

        # 3. Elimina tampas internas coplanares (faces duplicadas entre segmentos conectados)
        faces_counts = {}
        for f in raw_faces:
            key = tuple(sorted([(round(v.x(), 4), round(v.y(), 4), round(v.z(), 4)) for v in f]))
            faces_counts[key] = faces_counts.get(key, 0) + 1

        for f in raw_faces:
            key = tuple(sorted([(round(v.x(), 4), round(v.y(), 4), round(v.z(), 4)) for v in f]))
            if faces_counts[key] == 1:
                mesh.add_face(f)

        # 4.         # Suaviza arestas coplanares
        for e in mesh.edges:
            if len(e.faces) == 2:
                n0 = e.faces[0].normal()
                n1 = e.faces[1].normal()
                if abs(QVector3D.dotProduct(n0, n1) - 1.0) < 1e-4:
                    e.soft = True

        layer_name = "Parede"
        if scene is not None and scene.layer(layer_name) is None:
            scene.layers.append(Layer(layer_name))

        grp = Group(mesh, name=name)
        grp.layer = layer_name
        from .paint_catalog import default_wall_material, ensure_wall_paint_material
        ensure_wall_paint_material(scene)
        grp.material = default_wall_material()
        # Extrai os pontos ordenados para compatibilidade com inser??o de portas e janelas
        cycles = self.find_closed_cycles()
        if cycles:
            pts_ordered = [[float(p[0]), float(p[1]), float(z_base)] for p in cycles[0]]
            is_closed = True
        else:
            # Caminho aberto: coleta n?s dos segmentos conectados
            pts_ordered = []
            for s in self.segments.values():
                na = self.get_node(s.node_a_id)
                nb = self.get_node(s.node_b_id)
                if na and nb:
                    p_a = [float(na.pt[0]), float(na.pt[1]), float(z_base)]
                    p_b = [float(nb.pt[0]), float(nb.pt[1]), float(z_base)]
                    if not pts_ordered:
                        pts_ordered.extend([p_a, p_b])
                    else:
                        if p_a != pts_ordered[-1]:
                            pts_ordered.append(p_a)
                        if p_b != pts_ordered[-1]:
                            pts_ordered.append(p_b)
            is_closed = False

        grp.ext = {
            "trazomob_wall": {
                "altura": altura_m,
                "alturas": [
                    float(s.height) if s.height is not None else float(altura_m)
                    for s in self.segments.values()
                ],
                "espessura": self.default_thickness,
                "alinhamento": "centro",
                "is_graph_2d": True,
                "num_segments": len(self.segments),
                "graph_2d": self.to_dict(),
                "pontos": pts_ordered,
                "is_closed": is_closed,
                "openings": [],
                "z_base": float(z_base),
            }
        }
        return grp

    def build_ambiente_group(
        self,
        scene,
        nome: str = "Ambiente",
        pavimento_nome: str = "Térreo",
        altura_m: float = 2.6,
        z_base: float = 0.0,
    ) -> Optional[Group]:
        """
        Constrói um grupo **Ambiente** completo com paredes, piso e teto.

        Diferente de ``build_3d_group`` (que devolve só as paredes), este método:
        1. Cria as paredes via ``build_3d_group``
        2. Cria o piso via ``WallMeshBuilder.build_floor_group``
        3. Cria o teto via ``WallMeshBuilder.build_ceiling_group``
        4. Agrupa tudo num container marcado como ``KIND_AMBIENTE``

        O grupo retornado tem metadados ``trazomob_ambiente`` com nome, pavimento,
        área, pé-direito e lista de módulos (inicialmente vazia).
        """
        if not self.segments:
            return None

        # 1. Paredes (reutiliza a lógica existente)
        paredes_grupo = self.build_3d_group(scene, altura_m=altura_m, name=f"{nome} - Paredes")
        if paredes_grupo is None:
            return None
        paredes_lista = list(getattr(paredes_grupo, "children", None) or [paredes_grupo])

        # 2. Pontos do contorno para piso/teto (usa o primeiro ciclo fechado)
        cycles = self.find_closed_cycles()
        if not cycles:
            # Fallback: usa bounds das paredes
            from ..domain.ambiente import AmbienteBuilder
            return AmbienteBuilder.build_ambiente_group(
                nome, paredes_lista, None, None, pavimento_nome, z_base, altura_m
            )

        # Converte pontos do ciclo para QVector3D
        from PySide6.QtGui import QVector3D
        pontos_contorno = [QVector3D(float(p[0]), float(p[1]), 0.0) for p in cycles[0]]

        # 3. Piso
        from ..wall.mesh_builder import WallMeshBuilder
        piso = WallMeshBuilder.build_floor_group(scene, pontos_contorno, espessura=0.0, altura_base=z_base)

        # 4. Teto
        teto = WallMeshBuilder.build_ceiling_group(scene, pontos_contorno, altura_m=altura_m)

        # 5. Monta o Ambiente
        from ..domain.ambiente import AmbienteBuilder
        return AmbienteBuilder.build_ambiente_group(
            nome, paredes_lista, piso, teto, pavimento_nome, z_base, altura_m
        )

