# SPDX-License-Identifier: GPL-3.0-or-later
"""Paleta de Tintas e Cores de Paredes para o TrazoMob e Renderizador Foto-Realista."""
from __future__ import annotations

from typing import Dict, List, Tuple

# ── Catálogo de Cores Arquitetônicas / Suvinil / Coral / Tendências ──
WALL_PAINT_CATALOG: Dict[str, List[Dict[str, any]]] = {
    "Brancos & Neutros": [
        {"nome": "Branco Neve / Puro", "hex": "#FFFFFF", "rgb": (1.0, 1.0, 1.0), "tipo": "fosco"},
        {"nome": "Algodão Egípcio", "hex": "#EFECE1", "rgb": (0.937, 0.925, 0.882), "tipo": "fosco"},
        {"nome": "Calopsita", "hex": "#E5E1D3", "rgb": (0.898, 0.882, 0.827), "tipo": "fosco"},
        {"nome": "Off-White Clássico", "hex": "#F5F5F0", "rgb": (0.960, 0.960, 0.941), "tipo": "fosco"},
        {"nome": "Linho Suave", "hex": "#E8E2D5", "rgb": (0.910, 0.886, 0.835), "tipo": "fosco"},
    ],
    "Cinzas & Urbanos": [
        {"nome": "Crômio", "hex": "#D8D9D4", "rgb": (0.847, 0.851, 0.831), "tipo": "fosco"},
        {"nome": "Elefante", "hex": "#BDBEB9", "rgb": (0.741, 0.745, 0.725), "tipo": "fosco"},
        {"nome": "Cimento Queimado Claro", "hex": "#C2C4C1", "rgb": (0.760, 0.768, 0.756), "tipo": "cimento"},
        {"nome": "Cimento Queimado Médio", "hex": "#8C8E8B", "rgb": (0.549, 0.556, 0.545), "tipo": "cimento"},
        {"nome": "Grafite Intenso", "hex": "#3D4144", "rgb": (0.239, 0.254, 0.266), "tipo": "fosco"},
    ],
    "Tons Quentes & Terrosos": [
        {"nome": "Terracota Aconchegante", "hex": "#C16B4D", "rgb": (0.756, 0.419, 0.301), "tipo": "fosco"},
        {"nome": "Areia do Deserto", "hex": "#D9C7B2", "rgb": (0.850, 0.780, 0.698), "tipo": "fosco"},
        {"nome": "Argila Rosada", "hex": "#D19C87", "rgb": (0.819, 0.611, 0.529), "tipo": "fosco"},
        {"nome": "Caramelo Quente", "hex": "#9E643E", "rgb": (0.619, 0.392, 0.243), "tipo": "fosco"},
    ],
    "Verdes & Azuis": [
        {"nome": "Verde Sálvia / Eucalipto", "hex": "#8FA691", "rgb": (0.560, 0.650, 0.568), "tipo": "fosco"},
        {"nome": "Verde Oliva Profundo", "hex": "#505842", "rgb": (0.313, 0.345, 0.258), "tipo": "fosco"},
        {"nome": "Azul Petróleo", "hex": "#1E3B4D", "rgb": (0.117, 0.231, 0.301), "tipo": "fosco"},
        {"nome": "Azul Névoa Suave", "hex": "#A7B8C4", "rgb": (0.654, 0.721, 0.768), "tipo": "fosco"},
    ]
}

# ── Padrão das paredes recém-criadas ──
# Branco puro com acabamento acetinado. Registrado como Material para que o
# exportador GLB resolva finish="satin" (roughness 0.45) mesmo com nome em
# português, que o inferidor de finish classificaria como "matte".
DEFAULT_WALL_PAINT = "Pintura de parede fosco acetinado"
DEFAULT_WALL_COLOR: Tuple[float, float, float] = (1.0, 1.0, 1.0)


def default_wall_material() -> dict:
    """Material de container aplicado a paredes novas (branco acetinado)."""
    return {"color": list(DEFAULT_WALL_COLOR), "mat": DEFAULT_WALL_PAINT}


def ensure_wall_paint_material(scene) -> None:
    """Registra o material padrão na cena para o render/export saber o finish."""
    materials = getattr(scene, "materials", None)
    if materials is None or DEFAULT_WALL_PAINT in materials:
        return
    from core.materials import Material

    materials[DEFAULT_WALL_PAINT] = Material(
        DEFAULT_WALL_PAINT,
        color=DEFAULT_WALL_COLOR,
        finish="satin",
    )
