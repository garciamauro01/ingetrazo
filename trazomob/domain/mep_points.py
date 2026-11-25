# SPDX-License-Identifier: GPL-3.0-or-later
"""Modelo e geometria 3D para Pontos Elétricos e Hidráulicos (MEP) em paredes."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from core.group import Group
from ..builders.mesh_utils import create_board_group

MEP_KINDS: dict[str, dict[str, Any]] = {
    "tomada_110v": {"label": "Tomada 110V", "category": "eletrica", "default_h": 0.30, "color": (0.85, 0.25, 0.20)},
    "tomada_220v": {"label": "Tomada 220V", "category": "eletrica", "default_h": 0.30, "color": (0.75, 0.12, 0.12)},
    "interruptor": {"label": "Interruptor", "category": "eletrica", "default_h": 1.10, "color": (0.95, 0.60, 0.15)},
    "agua_fria": {"label": "Água Fria", "category": "hidraulica", "default_h": 0.60, "color": (0.15, 0.55, 0.90)},
    "agua_quente": {"label": "Água Quente", "category": "hidraulica", "default_h": 0.60, "color": (0.90, 0.35, 0.15)},
    "esgoto": {"label": "Esgoto", "category": "hidraulica", "default_h": 0.50, "color": (0.35, 0.65, 0.35)},
    "gas": {"label": "Ponto de Gás", "category": "gas", "default_h": 0.60, "color": (0.95, 0.80, 0.15)},
}


@dataclass
class MEPPoint:
    """Ponto técnico (elétrico, hidráulico ou gás) ancorado a um segmento de parede."""

    id: int
    seg_id: int
    kind: str
    offset_m: float
    height_m: float
    side: str = "left"
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MEPPoint:
        kind = str(data.get("kind", "tomada_110v"))
        default_h = float(MEP_KINDS.get(kind, {}).get("default_h", 0.30))
        return cls(
            id=int(data["id"]),
            seg_id=int(data["seg_id"]),
            kind=kind,
            offset_m=float(data.get("offset_m", 0.0)),
            height_m=float(data.get("height_m", default_h)),
            side=str(data.get("side", "left")),
            label=str(data.get("label", "")),
        )


def build_mep_point_group(
    point: MEPPoint,
    world_pos: tuple[float, float, float],
    size_m: tuple[float, float, float] = (0.08, 0.03, 0.12),
) -> Group:
    """Cria um grupo 3D representativo do ponto MEP na posição especificada."""
    meta = MEP_KINDS.get(point.kind, MEP_KINDS["tomada_110v"])
    w, d, h = size_m
    ox, oy, oz = world_pos
    grp = create_board_group(
        name=f"MEP_{point.kind}_{point.id}",
        origin=(ox - w * 0.5, oy - d * 0.5, oz - h * 0.5),
        size=(w, d, h),
        material=meta["label"],
        color=meta["color"],
    )
    if getattr(grp, "ext", None) is None:
        grp.ext = {}
    grp.ext["trazomob_mep_point"] = point.to_dict()
    return grp


def check_mep_interferences(
    points: list[MEPPoint],
    point_world_positions: dict[int, tuple[float, float, float]],
    module_bboxes: list[tuple[str, tuple[float, float, float], tuple[float, float, float]]],
    tolerance_m: float = 0.05,
) -> list[dict[str, Any]]:
    """Detecta interferências entre pontos MEP e caixas delimitadoras (min, max) de módulos."""
    alerts: list[dict[str, Any]] = []
    for pt in points:
        pos = point_world_positions.get(pt.id)
        if pos is None:
            continue
        px, py, pz = pos
        for mod_name, (min_x, min_y, min_z), (max_x, max_y, max_z) in module_bboxes:
            if (
                (min_x - tolerance_m) <= px <= (max_x + tolerance_m)
                and (min_y - tolerance_m) <= py <= (max_y + tolerance_m)
                and (min_z - tolerance_m) <= pz <= (max_z + tolerance_m)
            ):
                alerts.append({
                    "point_id": pt.id,
                    "kind": pt.kind,
                    "module_name": mod_name,
                    "position": pos,
                    "reason": f"Ponto '{pt.kind}' ({pt.height_m:.2f}m) coberto por '{mod_name}'",
                })
    return alerts


def compute_mep_wall_distances(point: MEPPoint, seg_length_m: float) -> dict[str, Any]:
    """Calcula a altura do piso e as distâncias do ponto MEP até os cantos da parede."""
    dist_start = max(0.0, min(seg_length_m, float(point.offset_m)))
    dist_end = max(0.0, seg_length_m - dist_start)
    nearest_corner = "start" if dist_start <= dist_end else "end"
    nearest_dist = dist_start if nearest_corner == "start" else dist_end
    return {
        "height_m": float(point.height_m),
        "dist_start_m": dist_start,
        "dist_end_m": dist_end,
        "nearest_corner": nearest_corner,
        "nearest_dist_m": nearest_dist,
    }


def update_mep_point_position(
    point: MEPPoint,
    seg_length_m: float,
    *,
    height_m: float | None = None,
    dist_from_nearest_m: float | None = None,
) -> MEPPoint:
    """Atualiza altura e/ou distância do ponto MEP a partir da cota editada."""
    if height_m is not None:
        point.height_m = max(0.0, float(height_m))
    if dist_from_nearest_m is not None:
        d = max(0.0, min(seg_length_m, float(dist_from_nearest_m)))
        info = compute_mep_wall_distances(point, seg_length_m)
        if info["nearest_corner"] == "start":
            point.offset_m = d
        else:
            point.offset_m = max(0.0, seg_length_m - d)
    return point
