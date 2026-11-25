# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Estrutura de dados para Planta Baixa 2D de paredes e extrusão para malhas 3D sólidas."""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

Point2D = Tuple[float, float]

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .plan_2d import (
        CustomDimension2D,
        DimensionChain2D,
        WallSegment2D,
        _DimAnchor,
    )

from .plan_2d import (
    CustomDimension2D,
    DimensionChain2D,
    _DimAnchor,
    dist_2d,
)


class Plan2DDimensionsMixin:
    """Gerenciamento de cotas e cadeias de cotas 2D extraído de WallGraph2D."""

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

