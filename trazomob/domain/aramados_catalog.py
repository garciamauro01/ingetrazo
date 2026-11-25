# SPDX-License-Identifier: GPL-3.0-or-later
"""Catálogo paramétrico e geometria 3D para ferragens e aramados internos."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.group import Group
from ..builders.mesh_utils import create_board_group


@dataclass(frozen=True)
class AramadoSpec:
    """Especificação de um acessório aramado/ferragem interna."""

    id: str
    label: str
    category: str
    min_width_mm: float
    min_depth_mm: float
    min_height_mm: float
    unit_price: float
    color: tuple[float, float, float] = (0.72, 0.74, 0.78)


ARAMADOS_CATALOG: dict[str, AramadoSpec] = {
    "lixeira_simples": AramadoSpec(
        id="lixeira_simples",
        label="Lixeira Embutida Simples",
        category="balcao",
        min_width_mm=300.0,
        min_depth_mm=400.0,
        min_height_mm=450.0,
        unit_price=280.0,
    ),
    "lixeira_dupla": AramadoSpec(
        id="lixeira_dupla",
        label="Lixeira Embutida Dupla",
        category="balcao",
        min_width_mm=400.0,
        min_depth_mm=450.0,
        min_height_mm=450.0,
        unit_price=420.0,
    ),
    "porta_temperos": AramadoSpec(
        id="porta_temperos",
        label="Porta-Temperos Aramado",
        category="balcao",
        min_width_mm=150.0,
        min_depth_mm=450.0,
        min_height_mm=550.0,
        unit_price=310.0,
    ),
    "escorredor_loucas": AramadoSpec(
        id="escorredor_loucas",
        label="Escorredor de Louças Embutido",
        category="aereo",
        min_width_mm=500.0,
        min_depth_mm=280.0,
        min_height_mm=350.0,
        unit_price=240.0,
    ),
    "canto_magico": AramadoSpec(
        id="canto_magico",
        label="Canto Mágico (Magic Corner)",
        category="canto",
        min_width_mm=800.0,
        min_depth_mm=500.0,
        min_height_mm=550.0,
        unit_price=1150.0,
    ),
    "calceiro_deslizante": AramadoSpec(
        id="calceiro_deslizante",
        label="Calceiro Deslizante",
        category="roupeiro",
        min_width_mm=400.0,
        min_depth_mm=450.0,
        min_height_mm=600.0,
        unit_price=260.0,
    ),
}


def list_compatible_aramados(
    largura_mm: float,
    prof_mm: float,
    altura_mm: float,
    category: str | None = None,
) -> list[AramadoSpec]:
    """Retorna os aramados compatíveis com as dimensões e categoria informadas."""
    res: list[AramadoSpec] = []
    for spec in ARAMADOS_CATALOG.values():
        if category and spec.category != category:
            continue
        if (
            largura_mm >= spec.min_width_mm
            and prof_mm >= spec.min_depth_mm
            and altura_mm >= spec.min_height_mm
        ):
            res.append(spec)
    return res


def build_aramado_group(
    aramado_id: str,
    largura_mm: float,
    prof_mm: float,
    altura_mm: float,
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> Group:
    """Constrói a representação 3D do aramado interno dentro do vão do módulo."""
    spec = ARAMADOS_CATALOG[aramado_id]
    w_m = max(0.10, (largura_mm - 40.0) / 1000.0)
    d_m = max(0.15, (prof_mm - 60.0) / 1000.0)
    h_m = max(0.08, min(0.35, (altura_mm - 100.0) / 1000.0))
    ox, oy, oz = origin

    grp = create_board_group(
        name=f"Aramado_{spec.id}",
        origin=(ox + 0.02, oy + 0.03, oz + 0.05),
        size=(w_m, d_m, h_m),
        material=spec.label,
        color=spec.color,
    )
    if getattr(grp, "ext", None) is None:
        grp.ext = {}
    grp.ext["trazomob_aramado"] = {
        "id": spec.id,
        "label": spec.label,
        "category": spec.category,
        "unit_price": spec.unit_price,
    }
    return grp
