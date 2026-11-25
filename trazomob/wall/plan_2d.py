# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Estrutura de dados para Planta Baixa 2D de paredes e extrusão para malhas 3D sólidas."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from PySide6.QtGui import QVector3D

from core.group import Group

Point2D = tuple[float, float]


def dist_2d(p1: Point2D, p2: Point2D) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def line_intersection_2d(p1: Point2D, d1: Point2D, p2: Point2D, d2: Point2D) -> Point2D | None:
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
    height: float | None = None  # altura individual em metros

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
    seg_id: int | None = None  # segmento principal associado (compatibilidade/UX)
    offset: float = 0.25          # distância visual da linha de cota em relação aos pontos cotados
    node_a_id: int | None = None  # nó do grafo vinculado a p1 (compatibilidade)
    node_b_id: int | None = None  # nó do grafo vinculado a p2 (compatibilidade)
    driving: bool = True          # True = altera/preserva geometria; False = anotação
    # Referência geométrica de p1 (tem prioridade sobre node_a_id)
    a_seg_id: int | None = None
    a_end: str | None = None   # "a", "b" ou None (ponto interno do segmento)
    a_dist: float = 0.0           # distância do nó A do segmento, quando a_end é None
    a_perp: float = 0.0           # afastamento perpendicular (face da parede)
    # Referência geométrica de p2 (tem prioridade sobre node_b_id)
    b_seg_id: int | None = None
    b_end: str | None = None
    b_dist: float = 0.0
    b_perp: float = 0.0


@dataclass
class _DimAnchor:
    """Referência interna de uma extremidade de cota, resolvida contra o grafo."""
    node_id: int | None = None
    seg_id: int | None = None
    end: str | None = None   # "a" / "b" para extremidades; None para ponto interno
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
    seg_ids: list[int] = field(default_factory=list)
    spans: list[tuple[int, float, float, float]] = field(default_factory=list)
    start_node_id: int | None = None
    end_node_id: int | None = None
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


from .plan_2d_dimensions import Plan2DDimensionsMixin
from .plan_2d_geometry import Plan2DGeometryMixin


class WallGraph2D(Plan2DDimensionsMixin, Plan2DGeometryMixin):
    """Grafo topológico 2D de paredes.

    Gerencia nós, arestas/segmentos, junções (L, T, X) e gera os contornos
    2D unificados e polígonos para extrusão direta em sólidos 3D.
    """

    def __init__(self, default_thickness: float = 0.15, default_height: float = 2.60, alignment: str = "centro"):
        self.default_thickness = default_thickness
        self.default_height = default_height
        self.alignment = "centro"  # Todas as paredes são desenhadas e calculadas pelo eixo central
        self.nodes: dict[int, WallNode2D] = {}
        self.segments: dict[int, WallSegment2D] = {}
        self.dimensions: dict[int, CustomDimension2D] = {}
        self.room_names: dict[str, str] = {}
        self.mep_points: dict[int, Any] = {}
        self._next_node_id: int = 1
        self._next_seg_id: int = 1
        self._next_dim_id: int = 1
        self._next_mep_id: int = 1

    def clear(self) -> None:
        self.nodes.clear()
        self.segments.clear()
        self.dimensions.clear()
        self.room_names.clear()
        self.mep_points.clear()
        self._next_node_id = 1
        self._next_seg_id = 1
        self._next_dim_id = 1
        self._next_mep_id = 1

    def add_mep_point(
        self,
        seg_id: int,
        kind: str,
        offset_m: float,
        height_m: float | None = None,
        side: str = "left",
        label: str = "",
    ) -> int:
        from ..domain.mep_points import MEP_KINDS, MEPPoint

        pid = self._next_mep_id
        self._next_mep_id += 1
        h = float(height_m) if height_m is not None else float(MEP_KINDS.get(kind, {}).get("default_h", 0.30))
        self.mep_points[pid] = MEPPoint(
            id=pid, seg_id=int(seg_id), kind=str(kind),
            offset_m=float(offset_m), height_m=h, side=str(side), label=str(label),
        )
        return pid

    def remove_mep_point(self, point_id: int) -> bool:
        return self.mep_points.pop(point_id, None) is not None

    def canonical_room_key(self, cycle_pts: list[Point2D]) -> str:
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

    def get_room_name(self, cycle_pts: list[Point2D], default: str = "Ambiente") -> str:
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

    def set_room_name(self, cycle_pts: list[Point2D], name: str) -> None:
        ck = self.canonical_room_key(cycle_pts)
        if ck:
            self.room_names[ck] = str(name).strip()

    def max_height_for_cycle(self, cycle_pts: list[Point2D], fallback: float = 2.60) -> float:
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

    def get_node(self, node_id: int) -> WallNode2D | None:
        return self.nodes.get(node_id)

    def add_segment(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        thickness: float | None = None,
        height: float | None = None,
    ) -> int | None:
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

    def _purge_dimension_segment_refs(self, removed_seg_ids: set[int]) -> None:
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

    def split_segment(self, seg_id: int, t: float = 0.5) -> int | None:
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
                              angle_tol_deg: float = 1.5) -> tuple[int, int] | None:
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

    def merge_node(self, node_id: int, angle_tol_deg: float = 1.5) -> int | None:
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
        best_sid: int | None = None
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
    def _project_point_on_segment(p: Point2D, a: Point2D, b: Point2D) -> tuple[Point2D, float]:
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        l2 = dx * dx + dy * dy
        if l2 < 1e-9:
            return a, 0.0
        t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2))
        return (a[0] + t * dx, a[1] + t * dy), t

    def snap_point(self, x: float, y: float, threshold: float = 0.20) -> tuple[float, float, str | None]:
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

    def find_node_at(self, x: float, y: float, threshold: float = 0.20) -> int | None:
        """Retorna o id do nó mais próximo de (x, y) dentro do raio threshold."""
        closest_id = None
        min_d = threshold
        for nid, node in self.nodes.items():
            d = dist_2d((x, y), (node.x, node.y))
            if d <= min_d:
                min_d = d
                closest_id = nid
        return closest_id

    def find_segment_at(self, x: float, y: float, threshold: float = 0.25) -> int | None:
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

    def get_rigid_component(self, start_nid: int) -> set[int]:
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
        dim_nodes: set[int] = set()
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
        rigid: set[int] = set(dim_nodes)
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
    def _segment_angle(seg: WallSegment2D, graph: "WallGraph2D") -> float | None:
        na = graph.nodes.get(seg.node_a_id)
        nb = graph.nodes.get(seg.node_b_id)
        if na is None or nb is None:
            return None
        return math.atan2(nb.y - na.y, nb.x - na.x)

    def _dimension_node_ids(self, d: CustomDimension2D) -> tuple[int | None, int | None]:
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
                          anchor_node_id: int | None = None,
                          ignore_dim_id: int | None = None) -> str | None:
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

    def set_segment_length(self, seg_id: int, new_length_m: float, anchor_node_id: int | None = None,
                           ignore_dim_id: int | None = None, enforce_constraints: bool = True) -> bool:
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
                                      anchor_node_id: int | None = None,
                                      ignore_dim_id: int | None = None) -> bool:
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

    def _expand_shift_to_preserve_walls(self, nodes_to_shift: set[int],
                                        delta: tuple[float, float],
                                        anchor_nid: int | None = None,
                                        skip_seg_id: int | None = None,
                                        ignore_dim_id: int | None = None) -> set[int]:
        """Expande um deslocamento até que nenhuma parede existente gire ou entorte.

        - cotas *driving* mantêm os dois lados juntos (corpo rígido);
        - se uma parede recebe o deslocamento em apenas uma ponta e ele tem
          componente perpendicular à parede, a parede inteira é transladada.
        """
        def dim_node_ids(d: CustomDimension2D) -> tuple[int | None, int | None]:
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

    def _move_node_with_orthogonal_propagation(self, move_nid: int, from_seg_id: int, delta: tuple[float, float], ignore_dim_id: int | None = None) -> None:
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

    def find_closed_cycles(self) -> list[list[Point2D]]:
        """Identifica todos os ciclos fechados simples (cômodos / faces) formados pelas paredes.

        Usa o algoritmo planar de 'menor ângulo à esquerda' (left-turn) para cada aresta direcionada,
        extraindo o contorno de cada cômodo fechado delimitado pelas paredes.
        """
        if len(self.segments) < 3:
            return []

        # Grafo de adjacência direcionado: node_id -> list of (neighbor_id, angle)
        adj: dict[int, list[int]] = {nid: [] for nid in self.nodes}
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

        sorted_adj: dict[int, list[int]] = {}
        for nid, neighbors in adj.items():
            sorted_adj[nid] = sorted(neighbors, key=lambda v: angle_from(nid, v))

        visited_half_edges: set[tuple[int, int]] = set()
        cycles: list[list[Point2D]] = []

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

    def segment_offsets(self, seg: WallSegment2D) -> tuple[float, float]:
        """Calcula o offset esquerdo e direito da parede.
        Com o alinhamento 100% no eixo central, a parede se expande exatamente
        metade da sua espessura (thickness / 2.0) para cada um dos lados.
        """
        th = seg.thickness
        return (th / 2.0, th / 2.0)

    def _determine_auto_flip(self, na_id: int, nb_id: int) -> bool:
        return False

    def get_start_extension(self, start_pt: tuple[float, float], dir_u: tuple[float, float],
                            thickness: float | None = None,
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
        best_ext: float | None = None
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

    def get_start_node_extension(self, start_nid: int | None, dir_u: tuple[float, float],
                                 thickness: float | None = None,
                                 face: str = "left") -> float:
        node = self.nodes.get(start_nid) if start_nid is not None else None
        if node is None:
            return 0.0
        return self.get_start_extension(node.pt, dir_u, thickness=thickness, face=face)

    def segment_face_length(self, seg_id: int, side: str = "left") -> float | None:
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
            "mep_points": [p.to_dict() for p in self.mep_points.values()],
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
        mep_raw = data.get("mep_points") or []
        if mep_raw:
            from ..domain.mep_points import MEPPoint
            for md in mep_raw:
                pt = MEPPoint.from_dict(md)
                graph.mep_points[pt.id] = pt
            if graph.mep_points:
                graph._next_mep_id = max(graph.mep_points.keys()) + 1
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
    def from_group(cls, group: Group) -> WallGraph2D | None:
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

    def reconcile_with_3d_groups(self, wall_groups: list[Group]) -> None:
        """Sincroniza as coordenadas 2D dos nós e cotas do grafo com a posição real atual
        das paredes na cena 3D (caso o usuário tenha movido ou rotacionado as paredes no 3D).
        """
        if not self.segments or not wall_groups:
            return

        orig_polys = self.compute_wall_polygons()
        orig_cols = self.compute_columns()
        old_positions = {nid: (n.x, n.y) for nid, n in self.nodes.items()}

        def _group_world_xy_verts(grp: Group) -> list[Point2D]:
            verts = getattr(getattr(grp, "mesh", None), "vertices", None) or []
            if not verts:
                return []
            xform = getattr(grp, "xform", None)
            pts_2d: list[Point2D] = []
            seen = set()
            for v in verts:
                pos = xform.map(v.position) if xform is not None else v.position
                key = (round(pos.x(), 4), round(pos.y(), 4))
                if key not in seen:
                    seen.add(key)
                    pts_2d.append((float(pos.x()), float(pos.y())))
            return pts_2d

        def _aabb_center_2d(pts: list[Point2D]) -> Point2D:
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
        seg_groups: dict[int, Group] = {}
        col_groups: dict[int, Group] = {}
        mono_groups: list[Group] = []
        for g in wall_groups:
            ext = getattr(g, "ext", None)
            w_data = ext.get("trazomob_wall", {}) if isinstance(ext, dict) else {}
            if w_data.get("is_column") and "node_id" in w_data:
                col_groups[int(w_data["node_id"])] = g
            elif "segment_id" in w_data:
                seg_groups[int(w_data["segment_id"])] = g
            else:
                mono_groups.append(g)

        node_new_pts: dict[int, list[Point2D]] = {nid: [] for nid in self.nodes}

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

