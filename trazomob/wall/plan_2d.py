# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Estrutura de dados para Planta Baixa 2D de paredes e extrusão para malhas 3D sólidas."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Set

from PySide6.QtGui import QVector3D
from core.mesh import Mesh
from core.group import Group
from core.layers import Layer
from core.triangulate import triangulate


Point2D = Tuple[float, float]


def dist_2d(p1: Point2D, p2: Point2D) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def line_intersection_2d(p1: Point2D, d1: Point2D, p2: Point2D, d2: Point2D) -> Optional[Point2D]:
    """Calcula a interseção entre duas retas parametrizadas: p1 + s*d1 e p2 + t*d2."""
    det = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(det) < 1e-6:
        return None
    dp = (p2[0] - p1[0], p2[1] - p1[1])
    s = (dp[0] * d2[1] - dp[1] * d2[0]) / det
    return (p1[0] + s * d1[0], p1[1] + s * d1[1])


@dataclass
class WallNode2D:
    """Vértice / nó da planta baixa 2D."""
    id: int
    x: float
    y: float

    @property
    def pt(self) -> Point2D:
        return (self.x, self.y)

    def to_qvector3d(self, z: float = 0.0) -> QVector3D:
        return QVector3D(self.x, self.y, z)


@dataclass
class WallSegment2D:
    """Segmento de parede conectando dois nós."""
    id: int
    node_a_id: int
    node_b_id: int
    thickness: float = 0.15  # em metros
    flip_side: bool = False  # mantido para compatibilidade de arquivos legados
    height: Optional[float] = None  # altura individual em metros

    def length(self, graph: WallGraph2D) -> float:
        na = graph.get_node(self.node_a_id)
        nb = graph.get_node(self.node_b_id)
        if na is None or nb is None:
            return 0.0
        return dist_2d(na.pt, nb.pt)


@dataclass
class CustomDimension2D:
    """Cota entre dois pontos quaisquer (faces, cantos, centros ou pontos da parede).

    O estado autoritativo da cota são as **referências** abaixo, não ``p1``/``p2``.
    ``p1``/``p2`` são apenas cache de renderização, recalculados por
    :meth:`WallGraph2D.sync_all_dimensions`.

    Uma referência pode ser:
    - nó do grafo (``node_a_id`` / ``node_b_id``);
    - ponto sobre um segmento (``*_seg_id`` + ``*_end``/``*_dist`` + ``*_perp``);
    - livre (sem nenhuma referência), quando a cota é apenas uma anotação no vazio.

    ``driving`` separa a **anotação** da **restrição**: só cotas ``driving``
    participam do arraste rígido e da propagação de restrições.
    """
    id: int
    p1: Point2D
    p2: Point2D
    seg_id: Optional[int] = None  # segmento principal associado (compatibilidade/UX)
    offset: float = 0.25          # distância visual da linha de cota em relação aos pontos cotados
    node_a_id: Optional[int] = None  # nó do grafo vinculado a p1 (compatibilidade)
    node_b_id: Optional[int] = None  # nó do grafo vinculado a p2 (compatibilidade)
    driving: bool = True          # True = altera/preserva geometria; False = anotação
    # Referência geométrica de p1 (tem prioridade sobre node_a_id)
    a_seg_id: Optional[int] = None
    a_end: Optional[str] = None   # "a", "b" ou None (ponto interno do segmento)
    a_dist: float = 0.0           # distância do nó A do segmento, quando a_end é None
    a_perp: float = 0.0           # afastamento perpendicular (face da parede)
    # Referência geométrica de p2 (tem prioridade sobre node_b_id)
    b_seg_id: Optional[int] = None
    b_end: Optional[str] = None
    b_dist: float = 0.0
    b_perp: float = 0.0


@dataclass
class _DimAnchor:
    """Referência interna de uma extremidade de cota, resolvida contra o grafo."""
    node_id: Optional[int] = None
    seg_id: Optional[int] = None
    end: Optional[str] = None   # "a" / "b" para extremidades; None para ponto interno
    dist: float = 0.0
    perp: float = 0.0

    @property
    def is_free(self) -> bool:
        return self.node_id is None and self.seg_id is None

    @property
    def is_partial(self) -> bool:
        return self.seg_id is not None and self.end is None


@dataclass
class DimensionChain2D:
    """Trecho de paredes colineares coberto por uma cota.

    ``spans`` traz ``(seg_id, min_t, max_t, comprimento)`` ordenado ao longo do
    eixo da cota (t medido em metros a partir da primeira ponta).
    """
    seg_ids: List[int] = field(default_factory=list)
    spans: List[Tuple[int, float, float, float]] = field(default_factory=list)
    start_node_id: Optional[int] = None
    end_node_id: Optional[int] = None
    start_pt: Point2D = (0.0, 0.0)
    end_pt: Point2D = (0.0, 0.0)
    span_len: float = 0.0
    gap_m: float = 0.0
    overshoot_m: float = 0.0
    exact: bool = False

    @property
    def is_constructive(self) -> bool:
        """Só é construtiva quando as paredes cobrem exatamente o vão da cota."""
        return bool(self.exact and self.start_node_id is not None and self.end_node_id is not None)


class WallGraph2D:
    """Grafo topológico 2D de paredes.

    Gerencia nós, arestas/segmentos, junções (L, T, X) e gera os contornos
    2D unificados e polígonos para extrusão direta em sólidos 3D.
    """

    def __init__(self, default_thickness: float = 0.15, default_height: float = 2.60, alignment: str = "centro"):
        self.default_thickness = default_thickness
        self.default_height = default_height
        self.alignment = "centro"  # Todas as paredes são desenhadas e calculadas pelo eixo central
        self.nodes: Dict[int, WallNode2D] = {}
        self.segments: Dict[int, WallSegment2D] = {}
        self.dimensions: Dict[int, CustomDimension2D] = {}
        self.room_names: Dict[str, str] = {}
        self._next_node_id: int = 1
        self._next_seg_id: int = 1
        self._next_dim_id: int = 1

    def clear(self) -> None:
        self.nodes.clear()
        self.segments.clear()
        self.dimensions.clear()
        self.room_names.clear()
        self._next_node_id = 1
        self._next_seg_id = 1
        self._next_dim_id = 1

    def canonical_room_key(self, cycle_pts: List[Point2D]) -> str:
        """Gera uma chave topológica robusta baseada nos IDs das paredes que delimitam o cômodo.

        Isso garante que ao reposicionar, esticar ou arrastar as paredes,
        o cômodo continue mantendo seu nome inalterado, pois a topologia estrutural
        (as paredes que o formam) permanece a mesma.
        """
        if not cycle_pts or len(cycle_pts) < 3:
            return ""

        # Mapeia as arestas do ciclo para os IDs das paredes do grafo
        seg_ids = set()
        n = len(cycle_pts)
        for i in range(n):
            p1 = cycle_pts[i]
            p2 = cycle_pts[(i + 1) % n]
            # Encontra nós mais próximos de p1 e p2
            na_id = None
            nb_id = None
            for nid, node in self.nodes.items():
                if dist_2d(p1, node.pt) < 0.05:
                    na_id = nid
                if dist_2d(p2, node.pt) < 0.05:
                    nb_id = nid
            if na_id is not None and nb_id is not None:
                for sid, s in self.segments.items():
                    if (s.node_a_id == na_id and s.node_b_id == nb_id) or (s.node_a_id == nb_id and s.node_b_id == na_id):
                        seg_ids.add(sid)
                        break

        if seg_ids:
            return "room_segs_" + "-".join(str(sid) for sid in sorted(seg_ids))

        # Fallback de coordenadas se por algum motivo nós não forem encontrados
        pts = [(round(float(p[0]), 1), round(float(p[1]), 1)) for p in cycle_pts]
        canonical = min([pts[i:] + pts[:i] for i in range(len(pts))] + [list(reversed(pts))[i:] + list(reversed(pts))[:i] for i in range(len(pts))])
        return "room_geom_" + ";".join(f"{x},{y}" for x, y in canonical)

    def get_room_name(self, cycle_pts: List[Point2D], default: str = "Ambiente") -> str:
        ck = self.canonical_room_key(cycle_pts)
        if ck in self.room_names:
            return self.room_names[ck]
        # Compatibilidade com chaves legadas puramente geométricas
        pts = [(round(float(p[0]), 2), round(float(p[1]), 2)) for p in cycle_pts]
        if pts:
            canonical = min([pts[i:] + pts[:i] for i in range(len(pts))] + [list(reversed(pts))[i:] + list(reversed(pts))[:i] for i in range(len(pts))])
            legacy_key = ";".join(f"{x},{y}" for x, y in canonical)
            if legacy_key in self.room_names:
                return self.room_names[legacy_key]
        return default

    def set_room_name(self, cycle_pts: List[Point2D], name: str) -> None:
        ck = self.canonical_room_key(cycle_pts)
        if ck:
            self.room_names[ck] = str(name).strip()

    def max_height_for_cycle(self, cycle_pts: List[Point2D], fallback: float = 2.60) -> float:
        """Maior altura das paredes que limitam um cômodo.

        O forro cobre o cômodo todo, então uma parede mais baixa (ex.: 1.00 m)
        não pode determinar a altura do teto. Se o contorno não contiver
        segmentos com altura explícita, usa a maior altura do grafo.
        """
        if not cycle_pts:
            return float(fallback)
        keys = {(round(float(p[0]), 4), round(float(p[1]), 4)) for p in cycle_pts}

        def _key(node_id: int):
            node = self.nodes.get(node_id)
            return None if node is None else (round(float(node.pt[0]), 4), round(float(node.pt[1]), 4))

        heights = [
            float(s.height)
            for s in self.segments.values()
            if s.height is not None
            and _key(s.node_a_id) in keys
            and _key(s.node_b_id) in keys
        ]
        if not heights:
            heights = [float(s.height) for s in self.segments.values() if s.height is not None]
        return max(heights) if heights else float(fallback)

    def _segment_attachment_tolerance(self, seg: Optional[WallSegment2D] = None) -> float:
        th = seg.thickness if seg is not None and seg.thickness is not None else self.default_thickness
        return max(0.10, th * 0.5 + 0.05)

    def _attach_dimension_point(self, p: Point2D, preferred_seg_id: Optional[int] = None) -> _DimAnchor:
        """Resolve um ponto cotado para uma referência estável do grafo.

        Regras (estilo CAD):
        - nó exato do grafo → referência de nó;
        - ponto sobre a face/eixo de uma parede → referência ``(seg_id, distância, afastamento)``;
        - ponto no vazio → referência livre (nunca vira restrição por proximidade).
        """
        # 1. Nó exato (tolerância de coincidência real, não de "vizinhança")
        for nid, node in self.nodes.items():
            if dist_2d(p, node.pt) <= 1e-3:
                seg_id = None
                end = None
                if preferred_seg_id is not None:
                    seg = self.segments.get(preferred_seg_id)
                    if seg and nid in (seg.node_a_id, seg.node_b_id):
                        seg_id = preferred_seg_id
                        end = "a" if nid == seg.node_a_id else "b"
                if seg_id is None:
                    for sid, seg in self.segments.items():
                        if nid in (seg.node_a_id, seg.node_b_id):
                            seg_id = sid
                            end = "a" if nid == seg.node_a_id else "b"
                            break
                if seg_id is not None:
                    return _DimAnchor(node_id=nid, seg_id=seg_id, end=end)
                return _DimAnchor(node_id=nid)

        # 2. Projeta sobre o(s) segmento(s) próximos
        candidate_ids: List[int]
        if preferred_seg_id is not None and preferred_seg_id in self.segments:
            candidate_ids = [preferred_seg_id]
        else:
            candidate_ids = list(self.segments.keys())

        best: Optional[_DimAnchor] = None
        best_score = float("inf")
        for sid in candidate_ids:
            seg = self.segments.get(sid)
            if seg is None:
                continue
            na = self.nodes.get(seg.node_a_id)
            nb = self.nodes.get(seg.node_b_id)
            if na is None or nb is None:
                continue
            dx = nb.x - na.x
            dy = nb.y - na.y
            sL = math.hypot(dx, dy)
            if sL < 1e-6:
                continue
            ux, uy = dx / sL, dy / sL
            nx, ny = -uy, ux
            # Pontos de face (cantos mitrados) ficam até meia espessura fora do
            # eixo, inclusive longitudinalmente. A tolerância precisa ser métrica:
            # 2 % de uma parede de 10 m (0,20 m) ou 2 % de uma parede de 1 m (0,02 m)
            # nunca representam a mesma coisa.
            tol_att = self._segment_attachment_tolerance(seg)
            along_raw = (p[0] - na.x) * ux + (p[1] - na.y) * uy
            # Só considera pontos realmente sobre (ou na ponta de) o segmento
            if along_raw < -tol_att or along_raw > sL + tol_att:
                continue
            perp = (p[0] - na.x) * nx + (p[1] - na.y) * ny
            if abs(perp) > tol_att:
                continue
            along = max(0.0, min(sL, along_raw))
            end = None
            if along_raw <= tol_att:
                end = "a"
            elif along_raw >= sL - tol_att:
                end = "b"
            score = abs(perp)
            if score >= best_score:
                continue
            node_id = None
            if end == "a":
                node_id = seg.node_a_id
            elif end == "b":
                node_id = seg.node_b_id
            best_score = score
            if end == "a":
                dist_ref = along_raw
            elif end == "b":
                dist_ref = along_raw - sL
            else:
                dist_ref = along
            best = _DimAnchor(
                node_id=node_id,
                seg_id=sid,
                end=end,
                dist=dist_ref,
                perp=perp,
            )

        if best is not None:
            return best

        return _DimAnchor()

    def _resolve_dimension_anchor(self, seg_id: Optional[int], end: Optional[str],
                                  along: float, perp: float,
                                  node_id: Optional[int], fallback: Point2D) -> Point2D:
        """Recalcula a posição absoluta de uma extremidade de cota a partir da referência."""
        seg = self.segments.get(seg_id) if seg_id is not None else None
        if seg is not None:
            na = self.nodes.get(seg.node_a_id)
            nb = self.nodes.get(seg.node_b_id)
            if na is not None and nb is not None:
                dx = nb.x - na.x
                dy = nb.y - na.y
                sL = math.hypot(dx, dy)
                if sL > 1e-9:
                    ux, uy = dx / sL, dy / sL
                    nx, ny = -uy, ux
                    if end in ("a", "b"):
                        # ``along`` é o deslocamento longitudinal a partir do nó
                        # (positivo no sentido A→B). Permite reproduzir cantos
                        # mitrados, que ficam meia espessura além do eixo.
                        base_nid = self.nodes.get(node_id) if node_id is not None else None
                        if base_nid is None:
                            base_nid = na if end == "a" else nb
                        base = (base_nid.x + ux * along, base_nid.y + uy * along)
                    else:
                        d = max(0.0, min(float(along), sL))
                        base = (na.x + ux * d, na.y + uy * d)
                    return (base[0] + nx * perp, base[1] + ny * perp)

        node = self.nodes.get(node_id) if node_id is not None else None
        if node is not None:
            return node.pt
        return fallback

    def _resolve_dimension_points(self, d: CustomDimension2D) -> Tuple[Point2D, Point2D]:
        p1 = self._resolve_dimension_anchor(
            d.a_seg_id, d.a_end, d.a_dist, d.a_perp, d.node_a_id, d.p1
        )
        p2 = self._resolve_dimension_anchor(
            d.b_seg_id, d.b_end, d.b_dist, d.b_perp, d.node_b_id, d.p2
        )
        return p1, p2

    def dimension_has_partial_anchor(self, d: CustomDimension2D) -> bool:
        """True quando a cota mede um trecho interno da parede (não uma ponta/segmento inteiro)."""
        a_partial = d.a_seg_id is not None and d.a_end is None
        b_partial = d.b_seg_id is not None and d.b_end is None
        return a_partial or b_partial

    def _nearest_node_within(self, p: Point2D, tol: float) -> Optional[int]:
        best_nid = None
        best_d = tol
        for nid, node in self.nodes.items():
            d = dist_2d(p, node.pt)
            if d <= best_d:
                best_d = d
                best_nid = nid
        return best_nid

    def _collinear_segment_path(self, start_nid: int, end_nid: int,
                                axis: Point2D, corridor: float) -> List[int]:
        """Caminho de segmentos colineares entre dois nós (lista ordenada de seg_ids)."""
        ax, ay = axis
        origin = self.nodes[start_nid].pt
        nx, ny = -ay, ax
        adj: Dict[int, List[Tuple[int, int]]] = {}
        for sid, seg in self.segments.items():
            na = self.nodes.get(seg.node_a_id)
            nb = self.nodes.get(seg.node_b_id)
            if na is None or nb is None:
                continue
            sdx, sdy = nb.x - na.x, nb.y - na.y
            sL = math.hypot(sdx, sdy)
            if sL < 1e-4:
                continue
            if abs(ax * sdx / sL + ay * sdy / sL) < 0.98:
                continue
            perp_a = abs((na.x - origin[0]) * nx + (na.y - origin[1]) * ny)
            perp_b = abs((nb.x - origin[0]) * nx + (nb.y - origin[1]) * ny)
            if max(perp_a, perp_b) > corridor:
                continue
            adj.setdefault(seg.node_a_id, []).append((seg.node_b_id, sid))
            adj.setdefault(seg.node_b_id, []).append((seg.node_a_id, sid))

        # BFS do nó inicial até o final, guardando o caminho de segmentos
        queue: List[Tuple[int, List[int]]] = [(start_nid, [])]
        visited = {start_nid}
        while queue:
            nid, path = queue.pop(0)
            if nid == end_nid:
                return path
            for other_nid, sid in adj.get(nid, []):
                if other_nid in visited:
                    continue
                visited.add(other_nid)
                queue.append((other_nid, path + [sid]))
        return []

    def resolve_dimension_chain(self, p1: Point2D, p2: Point2D,
                                length_tol: float = 0.02) -> DimensionChain2D:
        """Descobre quais paredes uma cota cobre, sem heurísticas de percentual.

        A cota é **construtiva** quando suas duas pontas estão sobre nós do grafo
        e existe um caminho de paredes colineares entre eles. Nesse caso editar o
        valor redimensiona exatamente esse trecho.

        Quando as pontas estão no meio de uma parede (ou separadas por um vão),
        ela é uma cota de referência e nunca deforma a planta.

        O critério anterior (sobreposição > 30 % do segmento) classificava
        trechos internos de paredes longas como "parede inteira" e esticava a
        parede errada.
        """
        chain = DimensionChain2D(start_pt=p1, end_pt=p2)
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        L = math.hypot(dx, dy)
        chain.span_len = L
        if L < 1e-4:
            return chain

        ux, uy = dx / L, dy / L
        nx, ny = -uy, ux

        thicknesses = [s.thickness for s in self.segments.values() if s.thickness is not None]
        max_th = max(thicknesses, default=self.default_thickness)
        corridor = max(0.25, max_th * 1.5 + 0.10)
        # Cantos de face ficam afastados do nó do eixo em ~t/2 em cada eixo.
        anchor_tol = max(0.15, max_th * 0.90)

        def build_spans(sids: List[int]) -> List[Tuple[int, float, float, float]]:
            out: List[Tuple[int, float, float, float]] = []
            for sid in sids:
                seg = self.segments.get(sid)
                if seg is None:
                    continue
                na = self.nodes.get(seg.node_a_id)
                nb = self.nodes.get(seg.node_b_id)
                if na is None or nb is None:
                    continue
                sL = dist_2d(na.pt, nb.pt)
                t_a = (na.x - p1[0]) * ux + (na.y - p1[1]) * uy
                t_b = (nb.x - p1[0]) * ux + (nb.y - p1[1]) * uy
                out.append((sid, min(t_a, t_b), max(t_a, t_b), sL))
            return out

        # 1. Cota ancorada em nós: caminho de paredes colineares entre eles.
        start_nid = self._nearest_node_within(p1, anchor_tol)
        end_nid = self._nearest_node_within(p2, anchor_tol)
        if start_nid is not None and end_nid is not None and start_nid != end_nid:
            na = self.nodes[start_nid]
            nb = self.nodes[end_nid]
            ax = nb.x - na.x
            ay = nb.y - na.y
            aL = math.hypot(ax, ay)
            if aL > 1e-6:
                ax, ay = ax / aL, ay / aL
                path = self._collinear_segment_path(start_nid, end_nid, (ax, ay), corridor)
                if path:
                    chain.spans = build_spans(path)
                    chain.seg_ids = path
                    chain.start_node_id = start_nid
                    chain.end_node_id = end_nid
                    chain.gap_m = 0.0
                    chain.overshoot_m = 0.0
                    chain.exact = True
                    return chain

        # 2. Pontas no meio da parede: só é construtiva se o vão for coberto
        # exatamente pela projeção das paredes (sem sobra e sem buraco).
        spans: List[Tuple[int, float, float, float]] = []
        for sid, seg in self.segments.items():
            na = self.nodes.get(seg.node_a_id)
            nb = self.nodes.get(seg.node_b_id)
            if na is None or nb is None:
                continue
            sdx, sdy = nb.x - na.x, nb.y - na.y
            sL = math.hypot(sdx, sdy)
            if sL < 1e-4:
                continue
            sux, suy = sdx / sL, sdy / sL
            if abs(ux * sux + uy * suy) < 0.98:
                continue
            perp_a = abs((na.x - p1[0]) * nx + (na.y - p1[1]) * ny)
            perp_b = abs((nb.x - p1[0]) * nx + (nb.y - p1[1]) * ny)
            if max(perp_a, perp_b) > corridor:
                continue
            t_a = (na.x - p1[0]) * ux + (na.y - p1[1]) * uy
            t_b = (nb.x - p1[0]) * ux + (nb.y - p1[1]) * uy
            min_t, max_t = min(t_a, t_b), max(t_a, t_b)
            # Segmento totalmente fora do vão não participa da cota.
            if max_t <= 1e-6 or min_t >= L - 1e-6:
                continue
            spans.append((sid, min_t, max_t, sL))

        spans.sort(key=lambda item: (item[1], item[2]))
        chain.spans = spans
        chain.seg_ids = [item[0] for item in spans]
        if not spans:
            return chain

        # Cobertura contígua: qualquer buraco entre segmentos (porta, vão) impede
        # que a cota seja construtiva, pois não há parede para absorver o delta.
        gap = 0.0
        prev_end = 0.0
        for _sid, min_t, max_t, _sL in spans:
            if min_t > prev_end:
                gap += min_t - prev_end
            prev_end = max(prev_end, max_t)
        if prev_end < L:
            gap += L - prev_end
        chain.gap_m = gap

        # Sobra: parede que continua além de uma das pontas da cota.
        chain.overshoot_m = max(
            [0.0] + [-item[1] for item in spans] + [item[2] - L for item in spans]
        )

        def nearest_node(sid: int, target: Point2D) -> Optional[int]:
            seg = self.segments[sid]
            candidates = [seg.node_a_id, seg.node_b_id]
            candidates = [nid for nid in candidates if nid in self.nodes]
            if not candidates:
                return None
            return min(candidates, key=lambda nid: dist_2d(target, self.nodes[nid].pt))

        chain.start_node_id = nearest_node(spans[0][0], p1)
        chain.end_node_id = nearest_node(spans[-1][0], p2)
        if chain.start_node_id == chain.end_node_id:
            chain.end_node_id = None

        chain.exact = (
            chain.gap_m <= length_tol
            and chain.overshoot_m <= length_tol
            and chain.start_node_id is not None
            and chain.end_node_id is not None
        )
        return chain

    def add_dimension(self, p1: Point2D, p2: Point2D, seg_id: Optional[int] = None,
                      offset: float = 0.25, driving: bool = True) -> Optional[int]:
        """Adiciona uma nova cota personalizada entre dois pontos.

        A cota nasce como anotação ou restrição conforme ``driving``. Pontos internos
        de parede são guardados como ``(seg_id, distância, afastamento)``; nunca são
        ligados artificialmente às duas extremidades do segmento.
        """
        if dist_2d(p1, p2) < 0.01:
            return None
        did = self._next_dim_id
        self._next_dim_id += 1

        a = self._attach_dimension_point(p1, preferred_seg_id=seg_id)
        b = self._attach_dimension_point(p2, preferred_seg_id=seg_id)

        # Um nó não pode representar as duas pontas de uma cota com comprimento > 0.
        node_a_id = a.node_id if a.end is not None else None
        node_b_id = b.node_id if b.end is not None else None
        if node_a_id is not None and node_a_id == node_b_id:
            node_a_id = None
            node_b_id = None

        # ``seg_id`` histórico: mantém o segmento principal para compatibilidade/UX.
        if seg_id is None:
            seg_id = a.seg_id if a.seg_id is not None else b.seg_id

        self.dimensions[did] = CustomDimension2D(
            id=did, p1=p1, p2=p2, seg_id=seg_id, offset=offset,
            node_a_id=node_a_id, node_b_id=node_b_id,
            driving=driving,
            a_seg_id=a.seg_id, a_end=a.end, a_dist=a.dist, a_perp=a.perp,
            b_seg_id=b.seg_id, b_end=b.end, b_dist=b.dist, b_perp=b.perp,
        )
        return did

    def sync_all_dimensions(self, old_node_positions: Optional[Dict[int, Point2D]] = None) -> None:
        """Sincroniza todas as cotas com a geometria atual.

        ``p1``/``p2`` são recalculados a partir das referências. Não existe mais
        associação implícita por proximidade: uma cota livre continua livre.
        ``old_node_positions`` é aceito apenas por compatibilidade de assinatura.
        """
        for d in self.dimensions.values():
            # Compatibilidade com cotas antigas: associa de forma determinística
            # apenas se houver um ``seg_id`` explícito e nenhuma referência de segmento gravada.
            if d.a_seg_id is None and d.seg_id in self.segments:
                a = self._attach_dimension_point(d.p1, preferred_seg_id=d.seg_id)
                d.a_seg_id, d.a_end, d.a_dist, d.a_perp = a.seg_id, a.end, a.dist, a.perp
                if a.node_id is not None:
                    d.node_a_id = a.node_id
            if d.b_seg_id is None and d.seg_id in self.segments:
                b = self._attach_dimension_point(d.p2, preferred_seg_id=d.seg_id)
                d.b_seg_id, d.b_end, d.b_dist, d.b_perp = b.seg_id, b.end, b.dist, b.perp
                if b.node_id is not None:
                    d.node_b_id = b.node_id

            if d.node_a_id is not None and d.node_a_id == d.node_b_id:
                # Invariante: as duas pontas nunca compartilham o mesmo nó.
                d.node_b_id = None

            # Migração: cotas antigas criadas sobre cantos mitrados ficaram com
            # referência "parcial" (ponto a meia espessura da ponta). Se a ponta
            # está dentro da tolerância de um nó do próprio segmento, ela é
            # reancorada no nó — do contrário a cota jamais poderia ser restritiva.
            for side, pt in (("a", d.p1), ("b", d.p2)):
                seg_id = getattr(d, f"{side}_seg_id")
                if seg_id is None or getattr(d, f"{side}_end") is not None:
                    continue
                seg = self.segments.get(seg_id)
                if seg is None:
                    continue
                tol = self._segment_attachment_tolerance(seg)
                nid = self._nearest_node_within(pt, tol)
                if nid not in (seg.node_a_id, seg.node_b_id):
                    continue
                na = self.nodes.get(seg.node_a_id)
                nb = self.nodes.get(seg.node_b_id)
                if na is None or nb is None:
                    continue
                sdx, sdy = nb.x - na.x, nb.y - na.y
                sL = math.hypot(sdx, sdy)
                if sL < 1e-9:
                    continue
                sux, suy = sdx / sL, sdy / sL
                npt = self.nodes[nid].pt
                setattr(d, f"{side}_end", "a" if nid == seg.node_a_id else "b")
                # Deslocamento longitudinal do canto mitrado a partir do nó
                setattr(d, f"{side}_dist", (pt[0] - npt[0]) * sux + (pt[1] - npt[1]) * suy)
                setattr(d, f"node_{side}_id", nid)

            if d.node_a_id is not None and d.node_a_id == d.node_b_id:
                d.node_b_id = None

            d.p1, d.p2 = self._resolve_dimension_points(d)

    def remove_dimension(self, dim_id: int) -> bool:
        if dim_id in self.dimensions:
            del self.dimensions[dim_id]
            return True
        return False

    def check_dimension_conflict(self, p1: Point2D, p2: Point2D, ignore_dim_id: Optional[int] = None) -> Optional[str]:
        """Verifica se uma nova cota conflita com cotas já existentes na mesma parede ou alinhamento.

        Regra de CAD:
        1. É permitido cotar um ou mais segmentos individuais de uma parede.
        2. É permitido cotar a parede inteira de ponta a ponta se os segmentos NÃO cobrirem a parede toda.
        3. O que NÃO é permitido (conflito / super-restrição):
           - Criar duas cotas para o MESMO vão/segmento (duplicidade exata ou quase exata).
           - Ter cotado TODOS os segmentos individuais e AINDA tentar cotar a parede toda de ponta a ponta
             (ou o inverso: já ter a parede inteira cotada e tentar cotar TODOS os segmentos individuais,
             pois a soma fecha 100% e travaria/conflitaria o modelo).
        """
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        L = math.hypot(dx, dy)
        if L < 1e-4:
            return "Comprimento nulo ou inválido."

        ux, uy = dx / L, dy / L
        nx, ny = -uy, ux

        thicknesses = [s.thickness for s in self.segments.values() if s.thickness is not None]
        max_th = max(thicknesses, default=self.default_thickness)
        corridor_tol = max(0.20, max_th * 1.5 + 0.10)

        # Encontra todos os segmentos colineares que a nova cota cobre por inteiro.
        # Nada de "30 % de sobreposição": ou a parede está dentro do vão da cota, ou não.
        chain = self.resolve_dimension_chain(p1, p2, length_tol=0.05)
        segs_along = [
            (sid, sL, min_t, max_t)
            for (sid, min_t, max_t, sL) in chain.spans
            if min_t >= -0.05 and max_t <= L + 0.05
        ]

        # Cotas existentes no mesmo alinhamento
        matching_dims = []
        for did, dim in self.dimensions.items():
            if ignore_dim_id is not None and did == ignore_dim_id:
                continue

            ddx = dim.p2[0] - dim.p1[0]
            ddy = dim.p2[1] - dim.p1[1]
            dL = math.hypot(ddx, ddy)
            if dL < 1e-4:
                continue
            dux, duy = ddx / dL, ddy / dL

            # 1. Verifica se são paralelas ou colineares
            dot = abs(ux * dux + uy * duy)
            if dot > 0.95:
                # 2. Verifica se estão na mesma faixa/linha da parede
                perp1 = abs((dim.p1[0] - p1[0]) * nx + (dim.p1[1] - p1[1]) * ny)
                perp2 = abs((dim.p2[0] - p1[0]) * nx + (dim.p2[1] - p1[1]) * ny)
                if max(perp1, perp2) <= corridor_tol:
                    t1 = (dim.p1[0] - p1[0]) * ux + (dim.p1[1] - p1[1]) * uy
                    t2 = (dim.p2[0] - p1[0]) * ux + (dim.p2[1] - p1[1]) * uy
                    min_t, max_t = min(t1, t2), max(t1, t2)
                    overlap = max(0.0, min(L, max_t) - max(0.0, min_t))

                    # 1. Conflito direto: Cota idêntica ou quase idêntica cobrindo o mesmo vão
                    if overlap > 0.85 * min(L, dL) and abs(L - dL) < 0.15:
                        return (
                            f"Já existe uma cota de {dL:.2f} m para este mesmo trecho. "
                            f"Não é necessário duplicar a cota."
                        )

                    if overlap > 0.10:
                        matching_dims.append((did, dL, min_t, max_t, overlap))

        # Se houver uma parede composta por múltiplos segmentos (cadeia):
        if len(segs_along) >= 2:
            total_wall_len = sum(item[1] for item in segs_along)
            # A nova cota é de ponta a ponta?
            is_new_span_total = abs(L - total_wall_len) < 0.20

            # Calcula quanto do comprimento total já está coberto por cotas parciais
            covered_len = sum(md[4] for md in matching_dims)

            if is_new_span_total:
                # Tentando cotar a parede toda: só é proibido se TODOS os segmentos já tiverem cota
                # (ou seja, se a cobertura de cotas parciais já for de praticamente 100% da parede)
                if covered_len >= 0.85 * total_wall_len:
                    return (
                        f"Todos os segmentos desta parede já possuem cotas individuais. "
                        f"Cotar também de ponta a ponta criaria uma redundância de cotas (super-restrição)."
                    )
            else:
                # A nova cota é de um segmento individual:
                # Verifica se já existe uma cota de ponta a ponta cobrindo tudo
                span_dim = next((md for md in matching_dims if abs(md[1] - total_wall_len) < 0.20), None)
                if span_dim is not None:
                    # Já existe cota total. A nova cota parcial é permitida DESDE QUE
                    # não feche 100% de todos os segmentos cotados juntos com a cota total!
                    # Se já temos outros segmentos cotados e este era o último que faltava:
                    other_covered = sum(md[4] for md in matching_dims if md[0] != span_dim[0])
                    if other_covered + L >= 0.85 * total_wall_len:
                        return (
                            f"Esta parede já possui uma cota total ({span_dim[1]:.2f} m) e os demais segmentos já estão cotados. "
                            f"Cotar todos os segmentos juntamente com a cota total geraria conflito de cotas."
                        )

        return None

    def is_empty(self) -> bool:
        return len(self.segments) == 0

    def add_node(self, x: float, y: float, merge_threshold: float = 0.05) -> int:
        """Adiciona um nó ou reutiliza um nó existente próximo dentro da tolerância."""
        for n_id, node in self.nodes.items():
            if dist_2d((x, y), (node.x, node.y)) <= merge_threshold:
                return n_id
        n_id = self._next_node_id
        self._next_node_id += 1
        self.nodes[n_id] = WallNode2D(id=n_id, x=x, y=y)
        return n_id

    def get_node(self, node_id: int) -> Optional[WallNode2D]:
        return self.nodes.get(node_id)

    def add_segment(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        thickness: Optional[float] = None,
        height: Optional[float] = None,
    ) -> Optional[int]:
        """Cria uma parede conectando (x1, y1) a (x2, y2).

        Se o ponto inicial ou final cair em cima de uma parede existente,
        a parede existente é subdividida no ponto de contato criando uma junção em T perfeita.
        """
        if dist_2d((x1, y1), (x2, y2)) < 0.02:
            return None

        # 1. Verifica se (x1, y1) cai sobre algum segmento existente e faz split se necessário
        na_id = self._get_or_split_at_point(x1, y1)
        # 2. Verifica se (x2, y2) cai sobre algum segmento existente e faz split se necessário
        nb_id = self._get_or_split_at_point(x2, y2)

        if na_id == nb_id:
            return None

        # Evita segmento duplicado
        for seg in self.segments.values():
            if (seg.node_a_id == na_id and seg.node_b_id == nb_id) or (seg.node_a_id == nb_id and seg.node_b_id == na_id):
                return seg.id

        th = thickness if thickness is not None else self.default_thickness
        flip = self._determine_auto_flip(na_id, nb_id)
        seg_id = self._next_seg_id
        self._next_seg_id += 1
        self.segments[seg_id] = WallSegment2D(
            id=seg_id,
            node_a_id=na_id,
            node_b_id=nb_id,
            thickness=th,
            height=height,
            flip_side=flip,
        )
        return seg_id

    def _remap_dimension_refs_after_split(self, old_seg_id: int, new_seg_id: int,
                                          split_dist: float) -> None:
        """Remapeia referências internas de cotas quando uma parede é subdividida.

        A parede original fica com o trecho ``[0, split_dist]`` e o novo segmento
        herda ``[split_dist, comprimento_total]``. Pontas (nós) não mudam; apenas
        pontos internos precisam migrar para o segmento correto.
        """
        for d in self.dimensions.values():
            for prefix in ("a", "b"):
                seg_id = getattr(d, f"{prefix}_seg_id")
                end = getattr(d, f"{prefix}_end")
                if seg_id != old_seg_id or end is not None:
                    continue
                dist = getattr(d, f"{prefix}_dist")
                if dist > split_dist + 1e-9:
                    setattr(d, f"{prefix}_seg_id", new_seg_id)
                    setattr(d, f"{prefix}_dist", dist - split_dist)
                elif abs(dist - split_dist) <= 1e-9:
                    # Ponto exatamente na divisão: torna-se uma ponta do segmento original.
                    setattr(d, f"{prefix}_end", "b")
                    setattr(d, f"{prefix}_dist", 0.0)
                    if getattr(d, f"node_{prefix}_id") is None:
                        setattr(d, f"node_{prefix}_id", self.segments[old_seg_id].node_b_id)
            # Mantém o segmento principal coerente com as referências.
            if d.seg_id == old_seg_id:
                on_new = (d.a_seg_id == new_seg_id) or (d.b_seg_id == new_seg_id)
                off_old = (
                    (d.a_seg_id is None or d.a_seg_id == new_seg_id)
                    and (d.b_seg_id is None or d.b_seg_id == new_seg_id)
                )
                if on_new and off_old:
                    d.seg_id = new_seg_id

    def _remap_dimension_node(self, old_node_id: int, new_node_id: int) -> None:
        """Redireciona referências de cota de um nó mesclado para o nó sobrevivente."""
        for d in self.dimensions.values():
            if d.node_a_id == old_node_id:
                d.node_a_id = new_node_id
            if d.node_b_id == old_node_id:
                d.node_b_id = new_node_id
            # Invariante: as duas extremidades nunca são o mesmo nó.
            if d.node_a_id is not None and d.node_a_id == d.node_b_id:
                d.node_b_id = None

    def _purge_dimension_segment_refs(self, removed_seg_ids: Set[int]) -> None:
        """Remove/limpa cotas que dependem de segmentos excluídos do grafo."""
        if not removed_seg_ids:
            return
        for did, d in list(self.dimensions.items()):
            # Cota cujo segmento principal sumiu deixa de fazer sentido.
            if d.seg_id in removed_seg_ids:
                self.dimensions.pop(did, None)
                continue
            lost_anchor = False
            for prefix in ("a", "b"):
                seg_id = getattr(d, f"{prefix}_seg_id")
                if seg_id not in removed_seg_ids:
                    continue
                end = getattr(d, f"{prefix}_end")
                if end is None:
                    # Ponto interno sem segmento não pode ser reancorado com segurança.
                    lost_anchor = True
                    break
                # Ponta: preserva a referência de nó, descarta só a de segmento.
                setattr(d, f"{prefix}_seg_id", None)
                setattr(d, f"{prefix}_end", None)
            if lost_anchor:
                self.dimensions.pop(did, None)

    def split_segment(self, seg_id: int, t: float = 0.5) -> Optional[int]:
        """Divide uma parede no parâmetro ``t`` (0..1, medido de A para B).

        Cria um nó no ponto de divisão e um novo segmento que herda espessura,
        altura e orientação da parede original. As cotas que apontavam para
        pontos internos são remapeadas para o trecho correto.

        Retorna o id do nó criado (ou de uma das pontas, se ``t`` cair nelas).
        """
        seg = self.segments.get(seg_id)
        if seg is None:
            return None
        na = self.nodes.get(seg.node_a_id)
        nb = self.nodes.get(seg.node_b_id)
        if na is None or nb is None:
            return None

        old_len = dist_2d(na.pt, nb.pt)
        if old_len < 1e-6:
            return None

        t = float(t)
        if t <= 1e-6:
            return seg.node_a_id
        if t >= 1.0 - 1e-6:
            return seg.node_b_id
        t = max(1e-4, min(1.0 - 1e-4, t))

        split_pt = (na.x + (nb.x - na.x) * t, na.y + (nb.y - na.y) * t)
        split_node_id = self.add_node(split_pt[0], split_pt[1], merge_threshold=1e-6)

        orig_b = seg.node_b_id
        orig_height = seg.height
        orig_flip = seg.flip_side
        split_dist = t * old_len

        # Segmento original passa a ir de A até o novo nó.
        seg.node_b_id = split_node_id

        # Novo segmento vai do novo nó até B, herdando as propriedades.
        new_s_id = self._next_seg_id
        self._next_seg_id += 1
        self.segments[new_s_id] = WallSegment2D(
            id=new_s_id,
            node_a_id=split_node_id,
            node_b_id=orig_b,
            thickness=seg.thickness,
            height=orig_height,
            flip_side=orig_flip,
        )
        self._remap_dimension_refs_after_split(seg_id, new_s_id, split_dist)
        return split_node_id

    def mergeable_segments_at(self, node_id: int,
                              angle_tol_deg: float = 1.5) -> Optional[Tuple[int, int]]:
        """Retorna os dois segmentos que podem ser unidos ao remover um nó.

        Só há união segura quando o nó é interno (grau 2), os dois trechos são
        colineares e compartilham a mesma espessura/altura. Nós de canto, de
        junção em T/X ou com alturas diferentes não são unificáveis.
        """
        if node_id not in self.nodes:
            return None
        incident = [
            s for s in self.segments.values()
            if s.node_a_id == node_id or s.node_b_id == node_id
        ]
        if len(incident) != 2:
            return None

        s1, s2 = incident
        node = self.nodes[node_id]
        other1 = s1.node_b_id if s1.node_a_id == node_id else s1.node_a_id
        other2 = s2.node_b_id if s2.node_a_id == node_id else s2.node_a_id
        if other1 == other2:
            return None
        o1 = self.nodes.get(other1)
        o2 = self.nodes.get(other2)
        if o1 is None or o2 is None:
            return None

        v1 = (o1.x - node.x, o1.y - node.y)
        v2 = (o2.x - node.x, o2.y - node.y)
        l1 = math.hypot(*v1)
        l2 = math.hypot(*v2)
        if l1 < 1e-6 or l2 < 1e-6:
            return None

        # Vetores apontam do nó para as pontas opostas: colinear = ~180°.
        cosang = (v1[0] * v2[0] + v1[1] * v2[1]) / (l1 * l2)
        min_cos = -math.cos(math.radians(max(0.0, angle_tol_deg)))
        if cosang > min_cos + 1e-9:
            return None

        if abs(float(s1.thickness) - float(s2.thickness)) > 1e-6:
            return None
        h1 = s1.height if s1.height is not None else self.default_height
        h2 = s2.height if s2.height is not None else self.default_height
        if abs(float(h1) - float(h2)) > 1e-6:
            return None

        return s1.id, s2.id

    def merge_node(self, node_id: int, angle_tol_deg: float = 1.5) -> Optional[int]:
        """Remove um nó interno colinear unindo os dois trechos em uma parede única.

        Retorna o id do segmento resultante, ou ``None`` quando a união não é
        segura (canto, T, X, alturas/espessuras diferentes).
        """
        pair = self.mergeable_segments_at(node_id, angle_tol_deg=angle_tol_deg)
        if pair is None:
            return None
        sid_a, sid_b = pair
        keep_id = min(sid_a, sid_b)
        drop_id = max(sid_a, sid_b)
        keep = self.segments[keep_id]
        drop = self.segments.pop(drop_id, None)
        node = self.nodes.get(node_id)
        if drop is None or node is None:
            return None

        other_keep = keep.node_b_id if keep.node_a_id == node_id else keep.node_a_id
        other_drop = drop.node_b_id if drop.node_a_id == node_id else drop.node_a_id

        # Resolve as extremidades cotadas antes de alterar a topologia.
        saved_anchors = []
        for d in self.dimensions.values():
            for prefix in ("a", "b"):
                seg_ref = getattr(d, f"{prefix}_seg_id")
                node_ref = getattr(d, f"node_{prefix}_id")
                if seg_ref not in (sid_a, sid_b) and node_ref != node_id:
                    continue
                pt = self._resolve_dimension_anchor(
                    seg_ref,
                    getattr(d, f"{prefix}_end"),
                    getattr(d, f"{prefix}_dist"),
                    getattr(d, f"{prefix}_perp"),
                    node_ref,
                    getattr(d, f"p{1 if prefix == 'a' else 2}"),
                )
                saved_anchors.append((d, prefix, pt))

        # Remove o nó e o segmento secundário; estende o segmento mantido.
        self.segments.pop(drop_id, None)
        self.nodes.pop(node_id, None)
        keep.node_a_id = other_keep
        keep.node_b_id = other_drop

        for d, prefix, pt in saved_anchors:
            anchor = self._attach_dimension_point(pt, preferred_seg_id=keep_id)
            setattr(d, f"{prefix}_seg_id", anchor.seg_id)
            setattr(d, f"{prefix}_end", anchor.end)
            setattr(d, f"{prefix}_dist", anchor.dist)
            setattr(d, f"{prefix}_perp", anchor.perp)
            setattr(d, f"node_{prefix}_id", anchor.node_id)
            if d.seg_id in (sid_a, sid_b) or d.seg_id not in self.segments:
                d.seg_id = keep_id

        self.sync_all_dimensions()
        return keep_id

    def _get_or_split_at_point(self, x: float, y: float, threshold: float = 0.20) -> int:
        """Encontra ou cria nó em (x, y), subdividindo segmento existente se estiver no meio."""
        # Primeiro checa nós existentes (tolerância de atração para fechar cômodos ou conectar)
        for n_id, node in self.nodes.items():
            if dist_2d((x, y), (node.x, node.y)) <= threshold:
                return n_id

        # Checa se o ponto cai em algum segmento existente (escolhe o mais próximo)
        pt = (x, y)
        best_sid: Optional[int] = None
        best_t = 0.0
        best_d = threshold
        for seg_id, seg in self.segments.items():
            na = self.nodes.get(seg.node_a_id)
            nb = self.nodes.get(seg.node_b_id)
            if na is None or nb is None:
                continue
            proj_pt, t = self._project_point_on_segment(pt, na.pt, nb.pt)
            d = dist_2d(pt, proj_pt)
            if 0.03 < t < 0.97 and d <= best_d:
                best_d = d
                best_sid = seg_id
                best_t = t

        if best_sid is not None:
            return self.split_segment(best_sid, best_t)

        # Se não caiu em nenhum segmento, cria um nó livre
        return self.add_node(x, y, merge_threshold=threshold)

    @staticmethod
    def _project_point_on_segment(p: Point2D, a: Point2D, b: Point2D) -> Tuple[Point2D, float]:
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        l2 = dx * dx + dy * dy
        if l2 < 1e-9:
            return a, 0.0
        t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2))
        return (a[0] + t * dx, a[1] + t * dy), t

    def snap_point(self, x: float, y: float, threshold: float = 0.20) -> Tuple[float, float, Optional[str]]:
        """Atracão magnética para auxílio ao desenho do usuário."""
        # 1. Cantos / nós
        for node in self.nodes.values():
            if dist_2d((x, y), (node.x, node.y)) <= threshold:
                return node.x, node.y, "canto"

        # 2. Ao longo de paredes (Junção em T)
        for seg in self.segments.values():
            na = self.nodes[seg.node_a_id]
            nb = self.nodes[seg.node_b_id]
            proj, t = self._project_point_on_segment((x, y), na.pt, nb.pt)
            if 0.0 <= t <= 1.0 and dist_2d((x, y), proj) <= threshold:
                return proj[0], proj[1], "parede"

        return x, y, None

    def find_node_at(self, x: float, y: float, threshold: float = 0.20) -> Optional[int]:
        """Retorna o id do nó mais próximo de (x, y) dentro do raio threshold."""
        closest_id = None
        min_d = threshold
        for nid, node in self.nodes.items():
            d = dist_2d((x, y), (node.x, node.y))
            if d <= min_d:
                min_d = d
                closest_id = nid
        return closest_id

    def find_segment_at(self, x: float, y: float, threshold: float = 0.25) -> Optional[int]:
        """Retorna o id do segmento mais próximo de (x, y) dentro da distância threshold."""
        closest_id = None
        min_d = threshold
        for sid, seg in self.segments.items():
            na = self.nodes[seg.node_a_id]
            nb = self.nodes[seg.node_b_id]
            proj, t = self._project_point_on_segment((x, y), na.pt, nb.pt)
            d = dist_2d((x, y), proj)
            if d <= min_d:
                min_d = d
                closest_id = sid
        return closest_id

    def get_rigid_component(self, start_nid: int) -> Set[int]:
        """Calcula o componente rígido paramétrico a partir de um nó inicial.

        Em softwares CAD paramétricos, uma cota é imutável: ela define uma restrição
        geométrica rígida. Todos os nós interligados por paredes cotadas formam um corpo
        rígido indeformável. Divisórias perpendiculares conectadas a esses nós também se
        deslocam em bloco com o corpo rígido. Apenas paredes e nós NÃO cotados absorvem
        o deslocamento/deformação.
        """
        dim_segs = {
            d.seg_id for d in self.dimensions.values()
            if d.driving and d.seg_id is not None
        }
        # Referências de segmento de cotas driving também tornam a parede rígida.
        for d in self.dimensions.values():
            if not d.driving:
                continue
            for sid in (d.a_seg_id, d.b_seg_id):
                if sid is not None:
                    dim_segs.add(sid)

        # 1. Se start_nid for extremidade livre de uma divisória conectada a uma base cotada:
        base_nid = start_nid
        for sid, s in self.segments.items():
            if s.node_a_id == start_nid or s.node_b_id == start_nid:
                other = s.node_b_id if s.node_a_id == start_nid else s.node_a_id
                deg_curr = sum(1 for s2 in self.segments.values() if s2.node_a_id == start_nid or s2.node_b_id == start_nid)
                deg_other = sum(1 for s2 in self.segments.values() if s2.node_a_id == other or s2.node_b_id == other)
                if deg_curr == 1 and deg_other >= 3:
                    dx = self.nodes[start_nid].x - self.nodes[other].x
                    dy = self.nodes[start_nid].y - self.nodes[other].y
                    L = math.hypot(dx, dy)
                    if L > 1e-4:
                        ux, uy = dx / L, dy / L
                        other_segs = [s2 for s2 in self.segments.values() if s2.id != sid and (s2.node_a_id == other or s2.node_b_id == other)]
                        for s2 in other_segs:
                            s2_other = s2.node_b_id if s2.node_a_id == other else s2.node_a_id
                            s2_dx = self.nodes[s2_other].x - self.nodes[other].x
                            s2_dy = self.nodes[s2_other].y - self.nodes[other].y
                            s2_L = math.hypot(s2_dx, s2_dy)
                            if s2_L > 1e-4 and abs((ux * s2_dx + uy * s2_dy) / s2_L) < 0.20:
                                base_nid = other
                                break

        # 2. Localiza todos os nós cotados interligados a base_nid via segmentos com cota
        dim_nodes: Set[int] = set()
        if any(s.node_a_id == base_nid or s.node_b_id == base_nid for sid, s in self.segments.items() if sid in dim_segs):
            q = [base_nid]
            dim_nodes.add(base_nid)
            while q:
                curr = q.pop(0)
                for sid in dim_segs:
                    s = self.segments.get(sid)
                    if s:
                        if s.node_a_id == curr and s.node_b_id not in dim_nodes:
                            dim_nodes.add(s.node_b_id)
                            q.append(s.node_b_id)
                        elif s.node_b_id == curr and s.node_a_id not in dim_nodes:
                            dim_nodes.add(s.node_a_id)
                            q.append(s.node_a_id)

        # Se não há cotas no grafo ou este nó não participa de nenhuma cota,
        # move apenas o nó ou a divisória simples sem afetar outros
        if not dim_nodes:
            # Se não há cota nenhuma no grafo inteiro, move o conjunto conectado para manter cantos
            if not dim_segs:
                connected_nodes = {start_nid}
                queue = [start_nid]
                while queue:
                    curr = queue.pop(0)
                    for s in self.segments.values():
                        if s.node_a_id == curr or s.node_b_id == curr:
                            nxt = s.node_b_id if s.node_a_id == curr else s.node_a_id
                            if nxt not in connected_nodes:
                                connected_nodes.add(nxt)
                                queue.append(nxt)
                return connected_nodes
            return {start_nid, base_nid} if base_nid != start_nid else {start_nid}

        # 3. Inclui divisórias perpendiculares que brotam dos nós cotados (ex: as paredes verticais)
        rigid: Set[int] = set(dim_nodes)
        for bn in dim_nodes:
            for sid, s in self.segments.items():
                if sid not in dim_segs:
                    other = s.node_b_id if s.node_a_id == bn else (s.node_a_id if s.node_b_id == bn else None)
                    if other is not None and other not in rigid:
                        deg_other = sum(1 for s2 in self.segments.values() if s2.node_a_id == other or s2.node_b_id == other)
                        if deg_other == 1:
                            dx = self.nodes[other].x - self.nodes[bn].x
                            dy = self.nodes[other].y - self.nodes[bn].y
                            L = math.hypot(dx, dy)
                            if L > 1e-4:
                                ux, uy = dx / L, dy / L
                                dim_connected_segs = [s2 for s2 in self.segments.values() if s2.id in dim_segs and (s2.node_a_id == bn or s2.node_b_id == bn)]
                                if dim_connected_segs:
                                    s2 = dim_connected_segs[0]
                                    s2_other = s2.node_b_id if s2.node_a_id == bn else s2.node_a_id
                                    s2_dx = self.nodes[s2_other].x - self.nodes[bn].x
                                    s2_dy = self.nodes[s2_other].y - self.nodes[bn].y
                                    s2_L = math.hypot(s2_dx, s2_dy)
                                    if s2_L > 1e-4 and abs((ux * s2_dx + uy * s2_dy) / s2_L) < 0.20:
                                        rigid.add(other)

        return rigid

    def move_node(self, node_id: int, new_x: float, new_y: float) -> bool:
        """Move as coordenadas de um nó existente respeitando rigorosamente as cotas paramétricas imutáveis.

        As cotas são tratadas como restrições rígidas: se uma ou mais paredes possuem cotas,
        elas e suas divisórias a 90° formam um corpo rígido inalterável. Ao arrastar qualquer
        um dos nós cotados, o bloco inteiro é transladado junto, e os segmentos/paredes NÃO
        cotados absorvem a diferença de posição.
        """
        node = self.nodes.get(node_id)
        if node is None:
            return False

        dx = new_x - node.x
        dy = new_y - node.y

        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            return True

        old_positions = {nid: (n.x, n.y) for nid, n in self.nodes.items()}

        # Obtém o componente rígido imutável vinculado por cotas
        rigid_nodes = self.get_rigid_component(node_id)
        rigid_nodes.add(node_id)

        # Expande o deslocamento para não girar/entortar nenhuma parede vizinha
        # (preserva cantos retos e junções em T).
        rigid_nodes = self._expand_shift_to_preserve_walls(rigid_nodes, (dx, dy))

        # Atualiza as posições de todos os nós do componente rígido
        for nid in rigid_nodes:
            n = self.nodes.get(nid)
            if n:
                n.x += dx
                n.y += dy

        # Sincroniza deterministicamente todas as cotas com os nós movidos
        self.sync_all_dimensions(old_positions)
        return True

    def remove_segment(self, seg_id: int) -> bool:
        """Remove um segmento de parede e limpa nós órfãos que ficarem sem nenhuma parede conectada."""
        if seg_id not in self.segments:
            return False
        seg = self.segments.pop(seg_id)
        # Remove/limpa cotas associadas a este segmento (inclusive referências internas).
        self._purge_dimension_segment_refs({seg_id})
        # Limpa nós que ficaram isolados
        self.cleanup_isolated_nodes()
        return True

    def remove_node(self, node_id: int) -> bool:
        """Remove um nó e todos os segmentos de parede conectados a ele."""
        if node_id not in self.nodes:
            return False
        to_del_segs = [sid for sid, s in self.segments.items() if s.node_a_id == node_id or s.node_b_id == node_id]
        for sid in to_del_segs:
            self.segments.pop(sid, None)
        self._purge_dimension_segment_refs(set(to_del_segs))
        self.nodes.pop(node_id, None)
        self.cleanup_isolated_nodes()
        return True

    def cleanup_isolated_nodes(self) -> int:
        """Remove nós órfãos que não pertencem a nenhum segmento de parede do grafo."""
        connected_nids = set()
        for s in self.segments.values():
            connected_nids.add(s.node_a_id)
            connected_nids.add(s.node_b_id)
        isolated = [nid for nid in list(self.nodes.keys()) if nid not in connected_nids]
        for nid in isolated:
            self.nodes.pop(nid, None)
        return len(isolated)

    def merge_close_nodes(self, threshold: float = 0.20) -> int:
        """Mescla nós que ficaram muito próximos um do outro (detectando fechamento de paredes).

        Quando o usuário edita a medida ou arrasta a ponta de uma parede para encostar
        em outro nó, os dois nós se fundem em um único nó, fechando o cômodo e ativando
        automaticamente o canto chanfrado a 45° ou a junção em T/coluna.
        """
        merged_count = 0
        changed = True
        while changed:
            changed = False
            for nid1 in list(self.nodes.keys()):
                if nid1 not in self.nodes:
                    continue
                node1 = self.nodes[nid1]
                for nid2 in list(self.nodes.keys()):
                    if nid2 <= nid1 or nid2 not in self.nodes:
                        continue
                    node2 = self.nodes[nid2]
                    if dist_2d((node1.x, node1.y), (node2.x, node2.y)) <= threshold:
                        # Mescla nid2 em nid1: redireciona todos os segmentos que usam nid2
                        for seg in self.segments.values():
                            if seg.node_a_id == nid2:
                                seg.node_a_id = nid1
                            if seg.node_b_id == nid2:
                                seg.node_b_id = nid1

                        # Remove segmentos degenerados (de nid1 para nid1) se houver
                        degen = [sid for sid, s in self.segments.items() if s.node_a_id == s.node_b_id]
                        for sid in degen:
                            del self.segments[sid]
                        if degen:
                            self._purge_dimension_segment_refs(set(degen))

                        # Redireciona referências de cota do nó mesclado
                        self._remap_dimension_node(nid2, nid1)

                        # Remove nó duplicado
                        del self.nodes[nid2]
                        merged_count += 1
                        changed = True
                        break
                if changed:
                    break
        return merged_count

    @staticmethod
    def _segment_angle(seg: WallSegment2D, graph: "WallGraph2D") -> Optional[float]:
        na = graph.nodes.get(seg.node_a_id)
        nb = graph.nodes.get(seg.node_b_id)
        if na is None or nb is None:
            return None
        return math.atan2(nb.y - na.y, nb.x - na.x)

    def _dimension_node_ids(self, d: CustomDimension2D) -> Tuple[Optional[int], Optional[int]]:
        na_id = d.node_a_id
        nb_id = d.node_b_id
        if na_id is None and d.a_seg_id in self.segments and d.a_end in ("a", "b"):
            s = self.segments[d.a_seg_id]
            na_id = s.node_a_id if d.a_end == "a" else s.node_b_id
        if nb_id is None and d.b_seg_id in self.segments and d.b_end in ("a", "b"):
            s = self.segments[d.b_seg_id]
            nb_id = s.node_a_id if d.b_end == "a" else s.node_b_id
        return na_id, nb_id

    def _dimension_measures_segment(self, d: CustomDimension2D, seg_id: int) -> bool:
        """True se a cota mede exatamente a parede indicada (comprimento total)."""
        if not d.driving:
            return False
        seg = self.segments.get(seg_id)
        if seg is None:
            return False
        na_id, nb_id = self._dimension_node_ids(d)
        if na_id is not None and nb_id is not None and na_id != nb_id:
            if {na_id, nb_id} == {seg.node_a_id, seg.node_b_id}:
                return True
        # Cota ligada às duas pontas do mesmo segmento.
        if d.a_seg_id == seg_id and d.b_seg_id == seg_id and d.a_end and d.b_end:
            return True
        return False

    def check_length_edit(self, seg_id: int, new_length_m: float,
                          anchor_node_id: Optional[int] = None,
                          ignore_dim_id: Optional[int] = None) -> Optional[str]:
        """Simula a alteração de medida e devolve uma mensagem se ela distorcer o modelo.

        Regras de proteção (CAD):
        - nenhuma parede pode girar (virar diagonal) por causa de uma edição de medida;
        - cotas *driving* não podem ter seus valores alterados, exceto a cota editada
          ou cotas que medem diretamente a própria parede editada;
        - nenhum segmento pode colapsar.
        """
        if seg_id not in self.segments:
            return "Parede não encontrada."
        if new_length_m <= 0.01:
            return "A medida deve ser maior que zero."

        trial = WallGraph2D.from_dict(self.to_dict())
        if not trial._set_segment_length_unchecked(
            seg_id, new_length_m, anchor_node_id=anchor_node_id, ignore_dim_id=ignore_dim_id
        ):
            return "Não foi possível aplicar essa medida nessa parede."

        target = trial.segments.get(seg_id)
        if target is None:
            return (
                "Essa alteração fecharia ou colapsaria a parede. "
                "Ajuste a medida ou remova a parede vizinha que ficaria sobreposta."
            )
        if abs(target.length(trial) - new_length_m) > 0.005:
            return (
                "A medida solicitada não pôde ser atingida sem mover uma parede "
                "que está bloqueada por outra cota."
            )

        # 1. Nenhuma parede existente pode mudar de direção (virar diagonal).
        for sid, orig_seg in self.segments.items():
            new_seg = trial.segments.get(sid)
            if new_seg is None:
                continue
            a0 = self._segment_angle(orig_seg, self)
            a1 = self._segment_angle(new_seg, trial)
            if a0 is None or a1 is None:
                continue
            diff = abs(a0 - a1) % math.pi
            if min(diff, math.pi - diff) > math.radians(0.50):
                return (
                    "Essa alteração entortaria a parede vizinha (o canto deixaria de ser reto "
                    "ou a parede viraria diagonal). Ajuste a âncora/sentido ou torne a cota "
                    "conflitante uma cota de referência."
                )

        # 2. Nenhum segmento pode colapsar.
        for sid, new_seg in trial.segments.items():
            if new_seg.length(trial) <= 1e-3:
                return "Essa alteração colapsaria uma parede. Ajuste a medida ou remova a parede vizinha."

        # 3. Cotas driving existentes não podem mudar de valor (exceto a editada e as
        #    que medem diretamente a parede alterada).
        for did, dim in self.dimensions.items():
            if not dim.driving:
                continue
            if did == ignore_dim_id:
                continue
            if self._dimension_measures_segment(dim, seg_id):
                continue
            trial_dim = trial.dimensions.get(did)
            if trial_dim is None:
                continue
            old_len = dist_2d(dim.p1, dim.p2)
            new_len = dist_2d(trial_dim.p1, trial_dim.p2)
            if abs(old_len - new_len) > 0.002:
                return (
                    f"A cota de {old_len:.2f} m já existente seria alterada para "
                    f"{new_len:.2f} m. Para evitar distorção, remova essa cota, torne-a "
                    f"de referência ou edite-a primeiro."
                )

        return None

    def set_segment_length(self, seg_id: int, new_length_m: float, anchor_node_id: Optional[int] = None,
                           ignore_dim_id: Optional[int] = None, enforce_constraints: bool = True) -> bool:
        """Altera o comprimento de uma parede preservando as demais cotas driving.

        Retorna ``False`` sem tocar na geometria quando a alteração provocaria
        distorção/sobre-restrição. Use ``enforce_constraints=False`` apenas em
        operações internas de simulação.
        """
        if enforce_constraints:
            msg = self.check_length_edit(seg_id, new_length_m, anchor_node_id, ignore_dim_id)
            if msg:
                return False
        return self._set_segment_length_unchecked(seg_id, new_length_m, anchor_node_id, ignore_dim_id)

    def _set_segment_length_unchecked(self, seg_id: int, new_length_m: float,
                                      anchor_node_id: Optional[int] = None,
                                      ignore_dim_id: Optional[int] = None) -> bool:
        """Implementação interna da alteração de medida, sem validação de restrições."""
        seg = self.segments.get(seg_id)
        if seg is None or new_length_m <= 0.01:
            return False

        na = self.nodes[seg.node_a_id]
        nb = self.nodes[seg.node_b_id]
        dx = nb.x - na.x
        dy = nb.y - na.y
        cur_len = math.hypot(dx, dy)
        if cur_len < 1e-6:
            return False

        ux = dx / cur_len
        uy = dy / cur_len

        old_positions = {nid: (n.x, n.y) for nid, n in self.nodes.items()}

        # Decide qual nó mover: o nó oposto ao anchor_node_id
        # Se ancorado em um canto existente com alinhamento interno/externo, compensa a extensão
        # para que o comprimento da face terminada seja exatamente new_length_m.
        deg_a = sum(1 for s in self.segments.values() if s.node_a_id == seg.node_a_id or s.node_b_id == seg.node_a_id)
        deg_b = sum(1 for s in self.segments.values() if s.node_a_id == seg.node_b_id or s.node_b_id == seg.node_b_id)

        actual_anchor = anchor_node_id
        if actual_anchor is None:
            # 1. Regra Paramétrica de CAD: Um lado que já possui cota definida é rígido/protegido
            # e DEVE atuar como âncora fixa para que a alteração de medida empurre o lado livre/não cotado.
            dim_segs = {
                d.seg_id for d in self.dimensions.values()
                if d.driving and d.seg_id is not None and d.seg_id != seg_id
            }
            for d in self.dimensions.values():
                if not d.driving:
                    continue
                for sid in (d.a_seg_id, d.b_seg_id):
                    if sid is not None and sid != seg_id:
                        dim_segs.add(sid)

            # Checa se o subgrafo a partir de node_a tem paredes cotadas (sem passar por seg_id)
            def has_dim_connected(start_nid: int) -> bool:
                vis = {start_nid}
                q = [start_nid]
                while q:
                    cur = q.pop(0)
                    for sid, s in self.segments.items():
                        if sid == seg_id:
                            continue
                        if s.node_a_id == cur or s.node_b_id == cur:
                            if sid in dim_segs:
                                return True
                            nxt = s.node_b_id if s.node_a_id == cur else s.node_a_id
                            if nxt not in vis:
                                vis.add(nxt)
                                q.append(nxt)
                return False

            has_dim_a = has_dim_connected(seg.node_a_id)
            has_dim_b = has_dim_connected(seg.node_b_id)

            if has_dim_a and not has_dim_b:
                actual_anchor = seg.node_a_id
            elif has_dim_b and not has_dim_a:
                actual_anchor = seg.node_b_id
            else:
                # Se ambos têm cotas ou nenhum tem cota, ancora na extremidade conectada anterior
                segs_a = [s.id for s in self.segments.values() if s.id != seg_id and (s.node_a_id == seg.node_a_id or s.node_b_id == seg.node_a_id)]
                segs_b = [s.id for s in self.segments.values() if s.id != seg_id and (s.node_a_id == seg.node_b_id or s.node_b_id == seg.node_b_id)]
                min_a = min(segs_a) if segs_a else 999999
                min_b = min(segs_b) if segs_b else 999999

                if min_a < seg_id and min_a < min_b:
                    actual_anchor = seg.node_a_id
                elif min_b < seg_id and min_b < min_a:
                    actual_anchor = seg.node_b_id
                else:
                    actual_anchor = seg.node_a_id

        if actual_anchor == seg.node_a_id:
            ext = self.get_start_extension((na.x, na.y), (ux, uy))
            eff_len = new_length_m + ext
            delta_L = eff_len - cur_len
            # Move nb e propaga para paredes perpendiculares conectadas em nb mantendo os cantos ortogonais
            self._move_node_with_orthogonal_propagation(seg.node_b_id, seg_id, (ux * delta_L, uy * delta_L), ignore_dim_id=ignore_dim_id)
        elif actual_anchor == seg.node_b_id:
            ext = self.get_start_extension((nb.x, nb.y), (-ux, -uy))
            eff_len = new_length_m + ext
            delta_L = eff_len - cur_len
            self._move_node_with_orthogonal_propagation(seg.node_a_id, seg_id, (-ux * delta_L, -uy * delta_L), ignore_dim_id=ignore_dim_id)
        else:
            delta_L = new_length_m - cur_len
            self._move_node_with_orthogonal_propagation(seg.node_b_id, seg_id, (ux * delta_L, uy * delta_L), ignore_dim_id=ignore_dim_id)

        # Sincroniza todas as cotas do grafo com as novas posições dos nós
        self.sync_all_dimensions(old_positions)

        # Após alterar o comprimento, verifica se o nó movido fechou com outro nó próximo
        self.merge_close_nodes(threshold=0.20)
        return True

    def _expand_shift_to_preserve_walls(self, nodes_to_shift: Set[int],
                                        delta: Tuple[float, float],
                                        anchor_nid: Optional[int] = None,
                                        skip_seg_id: Optional[int] = None,
                                        ignore_dim_id: Optional[int] = None) -> Set[int]:
        """Expande um deslocamento até que nenhuma parede existente gire ou entorte.

        - cotas *driving* mantêm os dois lados juntos (corpo rígido);
        - se uma parede recebe o deslocamento em apenas uma ponta e ele tem
          componente perpendicular à parede, a parede inteira é transladada.
        """
        def dim_node_ids(d: CustomDimension2D) -> Tuple[Optional[int], Optional[int]]:
            na_id = d.node_a_id
            nb_id = d.node_b_id
            if na_id is None and d.a_seg_id in self.segments and d.a_end in ("a", "b"):
                s = self.segments[d.a_seg_id]
                na_id = s.node_a_id if d.a_end == "a" else s.node_b_id
            if nb_id is None and d.b_seg_id in self.segments and d.b_end in ("a", "b"):
                s = self.segments[d.b_seg_id]
                nb_id = s.node_a_id if d.b_end == "a" else s.node_b_id
            return na_id, nb_id

        dlen = math.hypot(delta[0], delta[1])
        dux, duy = (delta[0] / dlen, delta[1] / dlen) if dlen > 1e-9 else (0.0, 0.0)

        changed = True
        while changed:
            changed = False

            # 1. Cotas driving: nenhuma pode mudar de comprimento por causa do deslocamento.
            for did, d in self.dimensions.items():
                if not d.driving:
                    continue
                if ignore_dim_id is not None and did == ignore_dim_id:
                    continue
                if skip_seg_id is not None and d.seg_id == skip_seg_id:
                    continue
                na_id, nb_id = dim_node_ids(d)
                if na_id is None or nb_id is None or na_id == nb_id:
                    continue
                na_in = na_id in nodes_to_shift
                nb_in = nb_id in nodes_to_shift
                if na_in and not nb_in:
                    nodes_to_shift.add(nb_id)
                    changed = True
                elif nb_in and not na_in:
                    nodes_to_shift.add(na_id)
                    changed = True

            # 2. Preserva a orientação de paredes que recebem apenas uma ponta.
            if dlen > 1e-9:
                for sid, s in self.segments.items():
                    if sid == skip_seg_id:
                        continue
                    a_in = s.node_a_id in nodes_to_shift
                    b_in = s.node_b_id in nodes_to_shift
                    if a_in == b_in:
                        continue
                    other = s.node_b_id if a_in else s.node_a_id
                    if other == anchor_nid or other in nodes_to_shift:
                        continue
                    na = self.nodes.get(s.node_a_id)
                    nb = self.nodes.get(s.node_b_id)
                    if na is None or nb is None:
                        continue
                    sdx = nb.x - na.x
                    sdy = nb.y - na.y
                    sL = math.hypot(sdx, sdy)
                    if sL < 1e-6:
                        continue
                    sux, suy = sdx / sL, sdy / sL
                    perp_move = abs(dux * suy - duy * sux)
                    if perp_move > 1e-6:
                        nodes_to_shift.add(other)
                        changed = True

        return nodes_to_shift

    def _move_node_with_orthogonal_propagation(self, move_nid: int, from_seg_id: int, delta: Tuple[float, float], ignore_dim_id: Optional[int] = None) -> None:
        """Move o nó e propaga o deslocamento de forma inteligente.

        - Em cadeias abertas: translada todo o restante da cadeia subsequente mantendo intactos
          os comprimentos e cotas de todas as paredes já definidas.
        - Em ciclos fechados: preserva a ortogonalidade dos cantos retos a 90°.
        """
        from_seg = self.segments.get(from_seg_id)
        if not from_seg:
            n = self.nodes.get(move_nid)
            if n:
                n.x += delta[0]
                n.y += delta[1]
            return

        anchor_nid = from_seg.node_a_id if from_seg.node_b_id == move_nid else from_seg.node_b_id

        # 1. Verifica se existe ciclo fechado de move_nid até anchor_nid sem usar from_seg_id
        visited_downstream = {move_nid}
        queue = [move_nid]
        has_cycle = False

        while queue:
            curr = queue.pop(0)
            if curr == anchor_nid:
                has_cycle = True
                break
            for sid, s in self.segments.items():
                if sid == from_seg_id:
                    continue
                if s.node_a_id == curr or s.node_b_id == curr:
                    nxt = s.node_b_id if s.node_a_id == curr else s.node_a_id
                    if nxt not in visited_downstream:
                        visited_downstream.add(nxt)
                        queue.append(nxt)

        # Conjunto inicial de nós a serem transladados por delta
        nodes_to_shift = set()

        if not has_cycle:
            # CADEIA ABERTA: Translada o subgrafo à frente de move_nid.
            nodes_to_shift = set(visited_downstream)
        else:
            # CICLO FECHADO / POLÍGONO ORTOGONAL:
            # A parede perpendicular conectada a move_nid se desloca inteira por delta,
            # mantendo rigorosamente os ângulos de 90° e cantos ortogonais.
            nodes_to_shift = {move_nid}
            na = self.nodes.get(from_seg.node_a_id)
            nb = self.nodes.get(from_seg.node_b_id)
            if na and nb:
                fdx = nb.x - na.x
                fdy = nb.y - na.y
                flen = math.hypot(fdx, fdy)
                if flen > 1e-6:
                    fux, fuy = fdx / flen, fdy / flen
                    for sid, s in self.segments.items():
                        if sid == from_seg_id:
                            continue
                        if s.node_a_id == move_nid or s.node_b_id == move_nid:
                            other_id = s.node_b_id if s.node_a_id == move_nid else s.node_a_id
                            on = self.nodes.get(other_id)
                            mn = self.nodes.get(move_nid)
                            if on and mn:
                                odx = on.x - mn.x
                                ody = on.y - mn.y
                                olen = math.hypot(odx, ody)
                                if olen > 1e-4:
                                    dot_parallel = abs((odx * fux + ody * fuy) / olen)
                                    if dot_parallel < 0.20:
                                        nodes_to_shift.add(other_id)

        # -----------------------------------------------------------------
        # RESTRIÇÃO PARAMÉTRICA RÍGIDA DE COTAS DE CAD:
        # Somente cotas *driving* restringem a geometria. Cotas de anotação
        # (driving=False) apenas acompanham a parede e nunca empurram nós.
        # -----------------------------------------------------------------
        self._expand_shift_to_preserve_walls(
            nodes_to_shift, delta, anchor_nid=anchor_nid,
            skip_seg_id=from_seg_id, ignore_dim_id=ignore_dim_id,
        )

        # Aplica a translação de corpo rígido
        for nid in nodes_to_shift:
            n = self.nodes.get(nid)
            if n:
                n.x += delta[0]
                n.y += delta[1]

    def find_closed_cycles(self) -> List[List[Point2D]]:
        """Identifica todos os ciclos fechados simples (cômodos / faces) formados pelas paredes.

        Usa o algoritmo planar de 'menor ângulo à esquerda' (left-turn) para cada aresta direcionada,
        extraindo o contorno de cada cômodo fechado delimitado pelas paredes.
        """
        if len(self.segments) < 3:
            return []

        # Grafo de adjacência direcionado: node_id -> list of (neighbor_id, angle)
        adj: Dict[int, List[int]] = {nid: [] for nid in self.nodes}
        for seg in self.segments.values():
            if seg.node_a_id != seg.node_b_id:
                if seg.node_b_id not in adj[seg.node_a_id]:
                    adj[seg.node_a_id].append(seg.node_b_id)
                if seg.node_a_id not in adj[seg.node_b_id]:
                    adj[seg.node_b_id].append(seg.node_a_id)

        # Ordena os vizinhos de cada nó pelo ângulo polar
        def angle_from(u_id: int, v_id: int) -> float:
            nu = self.nodes[u_id]
            nv = self.nodes[v_id]
            return math.atan2(nv.y - nu.y, nv.x - nu.x)

        sorted_adj: Dict[int, List[int]] = {}
        for nid, neighbors in adj.items():
            sorted_adj[nid] = sorted(neighbors, key=lambda v: angle_from(nid, v))

        visited_half_edges: Set[Tuple[int, int]] = set()
        cycles: List[List[Point2D]] = []

        for u in self.nodes:
            for v in sorted_adj.get(u, []):
                if (u, v) in visited_half_edges:
                    continue

                # Rastreia a face fazendo curvas à esquerda
                cycle = [u]
                curr_u, curr_v = u, v
                is_cycle = False

                while (curr_u, curr_v) not in visited_half_edges:
                    visited_half_edges.add((curr_u, curr_v))
                    cycle.append(curr_v)

                    # No nó curr_v, a aresta de entrada veio com ângulo angle_from(curr_v, curr_u)
                    in_angle = angle_from(curr_v, curr_u)
                    v_neighbors = sorted_adj.get(curr_v, [])
                    if not v_neighbors:
                        break

                    # Encontra o próximo vizinho logo no sentido anti-horário
                    # (primeiro vizinho cujo ângulo é maior que in_angle)
                    next_node = None
                    for cand in v_neighbors:
                        if angle_from(curr_v, cand) > in_angle + 1e-7:
                            next_node = cand
                            break
                    if next_node is None:
                        next_node = v_neighbors[0]

                    if next_node == u:
                        is_cycle = True
                        visited_half_edges.add((curr_v, next_node))
                        break

                    curr_u, curr_v = curr_v, next_node
                    if len(cycle) > len(self.segments) + 2:
                        break

                if is_cycle and len(cycle) >= 3:
                    pts = [self.nodes[nid].pt for nid in cycle]
                    # Calcula área assinada
                    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts))) / 2.0
                    if area < -0.05:
                        # Faces internas do algoritmo left-turn possuem orientação horária (área negativa)
                        cycles.append(list(reversed(pts)))

        # Fallback: se não encontrou faces internas com área negativa, usa ciclo com área positiva
        if not cycles:
            visited_fb = set()
            for u in self.nodes:
                for v in sorted_adj.get(u, []):
                    if (u, v) in visited_fb:
                        continue
                    cycle = [u]
                    curr_u, curr_v = u, v
                    is_cycle = False
                    while (curr_u, curr_v) not in visited_fb:
                        visited_fb.add((curr_u, curr_v))
                        cycle.append(curr_v)
                        in_angle = angle_from(curr_v, curr_u)
                        v_neighbors = sorted_adj.get(curr_v, [])
                        if not v_neighbors:
                            break
                        next_node = None
                        for cand in v_neighbors:
                            if angle_from(curr_v, cand) > in_angle + 1e-7:
                                next_node = cand
                                break
                        if next_node is None:
                            next_node = v_neighbors[0]
                        if next_node == u:
                            is_cycle = True
                            visited_fb.add((curr_v, next_node))
                            break
                        curr_u, curr_v = curr_v, next_node
                        if len(cycle) > len(self.segments) + 2:
                            break
                    if is_cycle and len(cycle) >= 3:
                        pts = [self.nodes[nid].pt for nid in cycle]
                        area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts))) / 2.0
                        if area > 0.05:
                            cycles.append(pts)
                            break

        return cycles

    def flip_segment_side(self, seg_id: int) -> bool:
        """Inverte o lado do alinhamento (face interna vs face externa) de uma parede especifica."""
        seg = self.segments.get(seg_id)
        if not seg:
            return False
        seg.flip_side = not seg.flip_side
        return True

    def segment_offsets(self, seg: WallSegment2D) -> Tuple[float, float]:
        """Calcula o offset esquerdo e direito da parede.
        Com o alinhamento 100% no eixo central, a parede se expande exatamente
        metade da sua espessura (thickness / 2.0) para cada um dos lados.
        """
        th = seg.thickness
        return (th / 2.0, th / 2.0)

    def _determine_auto_flip(self, na_id: int, nb_id: int) -> bool:
        return False

    def get_start_extension(self, start_pt: Tuple[float, float], dir_u: Tuple[float, float],
                            thickness: Optional[float] = None,
                            face: str = "center") -> float:
        """Deslocamento longitudinal da face no canto inicial da parede.

        Quando uma parede nasce em um canto existente, a face (interna/externa)
        não começa no nó do eixo: o encontro em 45° a desloca ao longo da parede.
        O valor retornado é esse deslocamento (positivo = à frente do nó).

        Use ``face="left"``/``"right"`` (esquerda/direita no sentido ``dir_u``).
        ``face="center"`` (padrão) mantém o comportamento de eixo central (0).
        Sem canto (extremidade livre, parede colinear ou início no vazio) retorna 0.
        """
        if face not in ("left", "right"):
            return 0.0
        if thickness is None:
            thickness = self.default_thickness
        ux, uy = dir_u
        ulen = math.hypot(ux, uy)
        if ulen < 1e-9:
            return 0.0
        ux, uy = ux / ulen, uy / ulen

        # Nó exato na extremidade inicial
        node_id = None
        best_d = 0.02
        for nid, node in self.nodes.items():
            d = dist_2d(start_pt, node.pt)
            if d <= best_d:
                best_d = d
                node_id = nid
        if node_id is None:
            return 0.0

        o_new = (thickness * 0.5) if face == "left" else (-thickness * 0.5)
        best_ext: Optional[float] = None
        for seg in self.segments.values():
            if seg.node_a_id != node_id and seg.node_b_id != node_id:
                continue
            oa = self.nodes.get(seg.node_a_id)
            ob = self.nodes.get(seg.node_b_id)
            if oa is None or ob is None:
                continue
            # Direção v saindo do nó ao longo da parede vizinha
            if seg.node_a_id == node_id:
                vx, vy = ob.x - oa.x, ob.y - oa.y
                adj_is_a = True
            else:
                vx, vy = oa.x - ob.x, oa.y - ob.y
                adj_is_a = False
            vlen = math.hypot(vx, vy)
            if vlen < 1e-9:
                continue
            vx, vy = vx / vlen, vy / vlen

            sin_t = ux * vy - uy * vx   # seno do ângulo de u para v
            if abs(sin_t) < 1e-4:
                continue  # parede colinear: sem extensão
            cos_t = ux * vx + uy * vy
            cross2 = vx * uy - vy * ux  # v x u

            off_l, off_r = self.segment_offsets(seg)
            off_l = off_l if off_l is not None else seg.thickness * 0.5
            off_r = off_r if off_r is not None else seg.thickness * 0.5

            # Mesma regra de pareamento de trilhos usada em compute_wall_polygons.
            if cross2 > 0:
                rail_in = "L" if adj_is_a else "R"
                rail_out = "R" if adj_is_a else "L"
                face_wants = "out" if face == "left" else "in"
            else:
                rail_in = "R" if adj_is_a else "L"
                rail_out = "L" if adj_is_a else "R"
                face_wants = "in" if face == "left" else "out"
            rail = rail_out if face_wants == "out" else rail_in

            off_canonical = off_l if rail == "L" else -off_r
            # Offset do trilho no referencial da direção que sai do nó.
            o_adj = off_canonical if adj_is_a else -off_canonical

            ext = (cos_t * o_new - o_adj) / sin_t
            if best_ext is None or abs(ext) < abs(best_ext):
                best_ext = ext

        return float(best_ext) if best_ext is not None else 0.0

    def get_start_node_extension(self, start_nid: Optional[int], dir_u: Tuple[float, float],
                                 thickness: Optional[float] = None,
                                 face: str = "left") -> float:
        node = self.nodes.get(start_nid) if start_nid is not None else None
        if node is None:
            return 0.0
        return self.get_start_extension(node.pt, dir_u, thickness=thickness, face=face)

    def segment_face_length(self, seg_id: int, side: str = "left") -> Optional[float]:
        """Comprimento da face longa de uma parede, já considerando os cantos em 45°."""
        polys = self.compute_wall_polygons()
        quad = polys.get(seg_id)
        if quad is None:
            return None
        c0, c1, c2, c3 = quad
        if side == "right":
            return dist_2d(c3, c2)
        return dist_2d(c0, c1)

    def to_dict(self) -> dict:
        """Serializa o grafo 2D para salvar nos metadados do grupo 3D."""
        return {
            "default_thickness": self.default_thickness,
            "default_height": self.default_height,
            "alignment": "centro",
            "nodes": [{"id": n.id, "x": n.x, "y": n.y} for n in self.nodes.values()],
            "segments": [
                {
                    "id": s.id,
                    "node_a_id": s.node_a_id,
                    "node_b_id": s.node_b_id,
                    "thickness": s.thickness,
                    "flip_side": s.flip_side,
                    "height": s.height,
                }
                for s in self.segments.values()
            ],
            "dimensions": [
                {
                    "id": d.id,
                    "p1": [d.p1[0], d.p1[1]],
                    "p2": [d.p2[0], d.p2[1]],
                    "seg_id": d.seg_id,
                    "offset": d.offset,
                    "node_a_id": d.node_a_id,
                    "node_b_id": d.node_b_id,
                    "driving": d.driving,
                    "a_seg_id": d.a_seg_id,
                    "a_end": d.a_end,
                    "a_dist": d.a_dist,
                    "a_perp": d.a_perp,
                    "b_seg_id": d.b_seg_id,
                    "b_end": d.b_end,
                    "b_dist": d.b_dist,
                    "b_perp": d.b_perp,
                }
                for d in self.dimensions.values()
            ],
            "room_names": dict(self.room_names),
        }

    @classmethod
    def from_dict(cls, data: dict) -> WallGraph2D:
        """Restaura o grafo 2D a partir dos metadados salvos."""
        graph = cls(
            default_thickness=data.get("default_thickness", 0.15),
            default_height=data.get("default_height", 2.60),
            alignment="centro",
        )
        for nd in data.get("nodes", []):
            graph.nodes[nd["id"]] = WallNode2D(id=nd["id"], x=nd["x"], y=nd["y"])
        for sd in data.get("segments", []):
            graph.segments[sd["id"]] = WallSegment2D(
                id=sd["id"],
                node_a_id=sd["node_a_id"],
                node_b_id=sd["node_b_id"],
                thickness=sd.get("thickness", graph.default_thickness),
                flip_side=sd.get("flip_side", False),
                height=sd.get("height", None),
            )
        for dd in data.get("dimensions", []):
            graph.dimensions[dd["id"]] = CustomDimension2D(
                id=dd["id"],
                p1=(dd["p1"][0], dd["p1"][1]),
                p2=(dd["p2"][0], dd["p2"][1]),
                seg_id=dd.get("seg_id"),
                offset=dd.get("offset", 0.25),
                node_a_id=dd.get("node_a_id"),
                node_b_id=dd.get("node_b_id"),
                driving=dd.get("driving", True),
                a_seg_id=dd.get("a_seg_id"),
                a_end=dd.get("a_end"),
                a_dist=dd.get("a_dist", 0.0),
                a_perp=dd.get("a_perp", 0.0),
                b_seg_id=dd.get("b_seg_id"),
                b_end=dd.get("b_end"),
                b_dist=dd.get("b_dist", 0.0),
                b_perp=dd.get("b_perp", 0.0),
            )
        if graph.nodes:
            graph._next_node_id = max(graph.nodes.keys()) + 1
        if graph.segments:
            graph._next_seg_id = max(graph.segments.keys()) + 1
        if graph.dimensions:
            graph._next_dim_id = max(graph.dimensions.keys()) + 1
        graph.room_names = dict(data.get("room_names", {}))
        # Normaliza referências e pontas (inclui a migração de cotas antigas
        # criadas sobre cantos mitrados) ao carregar um plano salvo.
        graph.sync_all_dimensions()
        return graph

    def clone(self) -> "WallGraph2D":
        """Cópia profunda independente do grafo (usada na validação de restrições)."""
        return WallGraph2D.from_dict(self.to_dict())

    def load_dict(self, data: dict) -> None:
        """Substitui o conteúdo deste grafo pelos dados fornecidos, mantendo a identidade do objeto."""
        other = WallGraph2D.from_dict(data)
        self.default_thickness = other.default_thickness
        self.default_height = other.default_height
        self.alignment = other.alignment
        self.nodes = other.nodes
        self.segments = other.segments
        self.dimensions = other.dimensions
        self.room_names = other.room_names
        self._next_node_id = other._next_node_id
        self._next_seg_id = other._next_seg_id
        self._next_dim_id = other._next_dim_id

    @classmethod
    def from_group(cls, group: Group) -> Optional[WallGraph2D]:
        """Tenta carregar o grafo 2D de um grupo de parede existente na cena."""
        ext = getattr(group, "ext", {})
        if not isinstance(ext, dict):
            return None
        w_data = ext.get("trazomob_wall")
        if not isinstance(w_data, dict):
            return None

        # 1. Se já possui o grafo 2D salvo diretamente
        if "graph_2d" in w_data:
            graph = cls.from_dict(w_data["graph_2d"])
            graph.reconcile_with_3d_groups([group])
            graph.cleanup_isolated_nodes()
            return graph

        # 2. Se for uma parede legada com lista de pontos sequenciais
        pts = w_data.get("pontos", [])
        if len(pts) >= 2:
            th = w_data.get("espessura", 0.15)
            h = w_data.get("altura", 2.60)
            alturas = w_data.get("alturas", [])
            al = w_data.get("alinhamento", "centro")
            graph = cls(default_thickness=th, default_height=h, alignment=al)
            is_closed = w_data.get("is_closed", False)
            n = len(pts)
            n_segs = n if is_closed else (n - 1)
            for i in range(n_segs):
                p1 = pts[i]
                p2 = pts[(i + 1) % n]
                seg_h = float(alturas[i]) if i < len(alturas) else float(h)
                graph.add_segment(p1[0], p1[1], p2[0], p2[1], thickness=th, height=seg_h)
            graph.reconcile_with_3d_groups([group])
            return graph

        return None

    def reconcile_with_3d_groups(self, wall_groups: List[Group]) -> None:
        """Sincroniza as coordenadas 2D dos nós e cotas do grafo com a posição real atual
        das paredes na cena 3D (caso o usuário tenha movido ou rotacionado as paredes no 3D).
        """
        if not self.segments or not wall_groups:
            return

        orig_polys = self.compute_wall_polygons()
        orig_cols = self.compute_columns()
        old_positions = {nid: (n.x, n.y) for nid, n in self.nodes.items()}

        def _group_world_xy_verts(grp: Group) -> List[Point2D]:
            verts = getattr(getattr(grp, "mesh", None), "vertices", None) or []
            if not verts:
                return []
            xform = getattr(grp, "xform", None)
            pts_2d: List[Point2D] = []
            seen = set()
            for v in verts:
                pos = xform.map(v.position) if xform is not None else v.position
                key = (round(pos.x(), 4), round(pos.y(), 4))
                if key not in seen:
                    seen.add(key)
                    pts_2d.append((float(pos.x()), float(pos.y())))
            return pts_2d

        def _aabb_center_2d(pts: List[Point2D]) -> Point2D:
            """Centro da caixa envolvente no plano XY.

            É estável mesmo quando a malha da parede ganha vértices extras por
            causa de vãos (portas/janelas) assimétricos. A média dos vértices
            se deslocaria nesses casos e falsearia a translação, inclinando as
            paredes vizinhas ao reabrir a planta.
            """
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            return ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0)

        # Mapeia grupos segmentados por segment_id ou node_id
        seg_groups: Dict[int, Group] = {}
        col_groups: Dict[int, Group] = {}
        mono_groups: List[Group] = []
        for g in wall_groups:
            ext = getattr(g, "ext", None)
            w_data = ext.get("trazomob_wall", {}) if isinstance(ext, dict) else {}
            if w_data.get("is_column") and "node_id" in w_data:
                col_groups[int(w_data["node_id"])] = g
            elif "segment_id" in w_data:
                seg_groups[int(w_data["segment_id"])] = g
            else:
                mono_groups.append(g)

        node_new_pts: Dict[int, List[Point2D]] = {nid: [] for nid in self.nodes}

        # 1. Para cada segmento que possui grupo 3D correspondente, extrai a transformação rígida 2D (ou translação)
        for sid, seg in self.segments.items():
            g = seg_groups.get(sid)
            orig_quad = orig_polys.get(sid)
            if g is None or orig_quad is None:
                continue

            cur_pts = _group_world_xy_verts(g)
            if not cur_pts:
                continue

            orig_cx, orig_cy = _aabb_center_2d(list(orig_quad))
            cur_cx, cur_cy = _aabb_center_2d(cur_pts)

            # Verifica se houve também rotação no plano XY via axes/xform do grupo
            from core.group import group_frame
            frame = group_frame(g)
            cos_a, sin_a = 1.0, 0.0
            if frame is not None:
                vx = frame.mapVector(QVector3D(1.0, 0.0, 0.0))
                vlen = math.hypot(vx.x(), vx.y())
                if vlen > 1e-6:
                    cos_a = vx.x() / vlen
                    sin_a = vx.y() / vlen

            for nid in (seg.node_a_id, seg.node_b_id):
                n_orig = old_positions.get(nid)
                if n_orig is None:
                    continue
                rx = n_orig[0] - orig_cx
                ry = n_orig[1] - orig_cy
                nx = cur_cx + (rx * cos_a - ry * sin_a)
                ny = cur_cy + (rx * sin_a + ry * cos_a)
                node_new_pts[nid].append((nx, ny))

        # 2. Se houver colunas 3D movidas, usa também o centro da coluna para o respectivo nó
        for nid, cg in col_groups.items():
            if nid in node_new_pts and nid in orig_cols:
                cur_pts = _group_world_xy_verts(cg)
                if cur_pts:
                    cur_cx, cur_cy = _aabb_center_2d(cur_pts)
                    node_new_pts[nid].append((cur_cx, cur_cy))

        # 3. Caso seja um grupo monolítico único (não segmentado)
        if not seg_groups and mono_groups:
            g = mono_groups[0]
            cur_pts = _group_world_xy_verts(g)
            all_orig_pts = [pt for quad in orig_polys.values() for pt in quad]
            if cur_pts and all_orig_pts:
                orig_min_x = min(p[0] for p in all_orig_pts)
                orig_max_x = max(p[0] for p in all_orig_pts)
                orig_min_y = min(p[1] for p in all_orig_pts)
                orig_max_y = max(p[1] for p in all_orig_pts)
                orig_cx = (orig_min_x + orig_max_x) / 2.0
                orig_cy = (orig_min_y + orig_max_y) / 2.0

                cur_min_x = min(p[0] for p in cur_pts)
                cur_max_x = max(p[0] for p in cur_pts)
                cur_min_y = min(p[1] for p in cur_pts)
                cur_max_y = max(p[1] for p in cur_pts)
                cur_cx = (cur_min_x + cur_max_x) / 2.0
                cur_cy = (cur_min_y + cur_max_y) / 2.0

                from core.group import group_frame
                frame = group_frame(g)
                cos_a, sin_a = 1.0, 0.0
                if frame is not None:
                    vx = frame.mapVector(QVector3D(1.0, 0.0, 0.0))
                    vlen = math.hypot(vx.x(), vx.y())
                    if vlen > 1e-6:
                        cos_a = vx.x() / vlen
                        sin_a = vx.y() / vlen

                for nid, n_orig in old_positions.items():
                    rx = n_orig[0] - orig_cx
                    ry = n_orig[1] - orig_cy
                    nx = cur_cx + (rx * cos_a - ry * sin_a)
                    ny = cur_cy + (rx * sin_a + ry * cos_a)
                    node_new_pts[nid].append((nx, ny))

        # Aplica as novas posições calculadas aos nós se houve deslocamento significativo (> 0.1 mm)
        moved = False
        for nid, candidates in node_new_pts.items():
            if not candidates:
                continue
            avg_x = sum(p[0] for p in candidates) / len(candidates)
            avg_y = sum(p[1] for p in candidates) / len(candidates)
            node = self.nodes[nid]
            if math.hypot(avg_x - node.x, avg_y - node.y) > 1e-4:
                node.x = round(avg_x, 4)
                node.y = round(avg_y, 4)
                moved = True

        if moved:
            self.sync_all_dimensions(old_positions)

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

