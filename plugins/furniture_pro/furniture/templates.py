# SPDX-License-Identifier: GPL-3.0-or-later
"""Parametric catalogue presented in the module library.

The templates are starting points, not limits: every value remains editable
in the form and is stored with the module.  Construction rules live in
``furniture.generator`` so a manufacturer can replace or extend them.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.constants import MODULE_LABELS
from ..core.models import ModuleSpec


@dataclass(frozen=True)
class ModuleTemplate:
    type: str
    label: str
    category: str
    description: str
    defaults: dict = field(default_factory=dict)
    tags: tuple[str, ...] = ()

    def create(self) -> ModuleSpec:
        spec = ModuleSpec(type=self.type, name=self.label,
                          tags=list(self.tags))
        for key, value in self.defaults.items():
            if hasattr(spec, key):
                setattr(spec, key, value)
        spec.name = f"{self.label} {int(spec.width_mm)}"
        return spec


_CATALOGUE: tuple[ModuleTemplate, ...] = (
    ModuleTemplate(
        "armario_inferior", MODULE_LABELS["armario_inferior"], "Armários",
        "Armário de piso com rodapé, portas e prateleiras internas.",
        {"width_mm": 800, "height_mm": 850, "depth_mm": 550,
         "plinth_height_mm": 100, "plinth_recess_mm": 60,
         "door_type": "hinged", "door_count": 2, "shelf_count": 1,
         "drawer_count": 0, "back_method": "rasgo"},
        ("cozinha", "piso"),
    ),
    ModuleTemplate(
        "armario_superior", MODULE_LABELS["armario_superior"], "Armários",
        "Armário aéreo sem rodapé, com portas de abrir.",
        {"width_mm": 800, "height_mm": 700, "depth_mm": 350,
         "plinth_height_mm": 0, "plinth_recess_mm": 0,
         "door_type": "hinged", "door_count": 2, "shelf_count": 1,
         "drawer_count": 0, "back_method": "rasgo"},
        ("cozinha", "aéreo"),
    ),
    ModuleTemplate(
        "torre", MODULE_LABELS["torre"], "Armários",
        "Torre alta para eletrodomésticos, despensa ou coluna.",
        {"width_mm": 600, "height_mm": 2200, "depth_mm": 600,
         "plinth_height_mm": 100, "plinth_recess_mm": 60,
         "door_type": "hinged", "door_count": 1, "shelf_count": 3,
         "drawer_count": 0, "back_method": "rasgo"},
        ("cozinha", "coluna"),
    ),
    ModuleTemplate(
        "guarda_roupa", MODULE_LABELS["guarda_roupa"], "Quartos",
        "Guarda-roupa com portas de correr, divisórias e prateleiras.",
        {"width_mm": 2000, "height_mm": 2400, "depth_mm": 600,
         "plinth_height_mm": 100, "plinth_recess_mm": 60,
         "door_type": "sliding", "door_count": 2, "shelf_count": 3,
         "divider_count": 1, "drawer_count": 0, "back_method": "sobreposto"},
        ("quarto", "roupeiro"),
    ),
    ModuleTemplate(
        "closet", MODULE_LABELS["closet"], "Quartos",
        "Closet aberto com divisórias e prateleiras; sem portas.",
        {"width_mm": 1800, "height_mm": 2400, "depth_mm": 550,
         "plinth_height_mm": 100, "plinth_recess_mm": 60,
         "door_type": "none", "door_count": 0, "shelf_count": 4,
         "divider_count": 2, "drawer_count": 0, "back_method": "sobreposto"},
        ("quarto", "closet"),
    ),
    ModuleTemplate(
        "gaveteiro", MODULE_LABELS["gaveteiro"], "Armários",
        "Gaveteiro com caixas internas e corrediças configuráveis.",
        {"width_mm": 500, "height_mm": 850, "depth_mm": 550,
         "plinth_height_mm": 100, "plinth_recess_mm": 60,
         "door_type": "none", "door_count": 0, "shelf_count": 0,
         "drawer_count": 4, "drawer_box": True, "back_method": "rasgo"},
        ("cozinha", "gavetas"),
    ),
    ModuleTemplate(
        "balcao", MODULE_LABELS["balcao"], "Armários",
        "Balcão com portas e prateleira, preparado para tampo.",
        {"width_mm": 1200, "height_mm": 900, "depth_mm": 600,
         "plinth_height_mm": 100, "plinth_recess_mm": 60,
         "door_type": "hinged", "door_count": 2, "shelf_count": 1,
         "drawer_count": 0, "back_method": "rasgo"},
        ("cozinha", "banheiro", "balcão"),
    ),
    ModuleTemplate(
        "nicho", MODULE_LABELS["nicho"], "Salas",
        "Nicho aberto para TV, livros ou objetos decorativos.",
        {"width_mm": 600, "height_mm": 600, "depth_mm": 300,
         "plinth_height_mm": 0, "plinth_recess_mm": 0,
         "door_type": "none", "door_count": 0, "shelf_count": 2,
         "divider_count": 1, "drawer_count": 0, "back_method": "sobreposto"},
        ("sala", "nicho"),
    ),
    ModuleTemplate(
        "prateleira", MODULE_LABELS["prateleira"], "Salas",
        "Prateleira avulsa; a altura informada é a espessura da chapa.",
        {"width_mm": 800, "height_mm": 25, "depth_mm": 250,
         "panel_thickness_mm": 25, "plinth_height_mm": 0,
         "plinth_recess_mm": 0, "door_type": "none", "door_count": 0,
         "shelf_count": 0, "divider_count": 0, "drawer_count": 0,
         "back_method": "sem_fundo", "top_method": "sem_topo"},
        ("sala", "prateleira"),
    ),
    ModuleTemplate(
        "painel", MODULE_LABELS["painel"], "Estruturas",
        "Painel vertical ou divisória; a profundidade é a espessura.",
        {"width_mm": 800, "height_mm": 2400, "depth_mm": 18,
         "panel_thickness_mm": 18, "plinth_height_mm": 0,
         "plinth_recess_mm": 0, "door_type": "none", "door_count": 0,
         "shelf_count": 0, "divider_count": 0, "drawer_count": 0,
         "back_method": "sem_fundo", "top_method": "sem_topo"},
        ("estrutura", "divisória"),
    ),
    ModuleTemplate(
        "porta_abrir", MODULE_LABELS["porta_abrir"], "Portas",
        "Porta de abrir avulsa; a profundidade é a espessura da folha.",
        {"width_mm": 500, "height_mm": 2000, "depth_mm": 18,
         "panel_thickness_mm": 18, "plinth_height_mm": 0,
         "plinth_recess_mm": 0, "door_type": "none", "door_count": 0,
         "shelf_count": 0, "divider_count": 0, "drawer_count": 0,
         "back_method": "sem_fundo", "top_method": "sem_topo"},
        ("porta",),
    ),
    ModuleTemplate(
        "porta_correr", MODULE_LABELS["porta_correr"], "Portas",
        "Conjunto de portas de correr com guias superior e inferior.",
        {"width_mm": 1500, "height_mm": 2200, "depth_mm": 18,
         "panel_thickness_mm": 18, "plinth_height_mm": 0,
         "plinth_recess_mm": 0, "door_type": "sliding", "door_count": 2,
         "shelf_count": 0, "divider_count": 0, "drawer_count": 0,
         "back_method": "sem_fundo", "top_method": "sem_topo"},
        ("porta",),
    ),
    ModuleTemplate(
        "bancada", MODULE_LABELS["bancada"], "Estruturas",
        "Tampo/bancada maciça; a altura informada é a espessura.",
        {"width_mm": 2000, "height_mm": 40, "depth_mm": 600,
         "panel_thickness_mm": 40, "plinth_height_mm": 0,
         "plinth_recess_mm": 0, "door_type": "none", "door_count": 0,
         "shelf_count": 0, "divider_count": 0, "drawer_count": 0,
         "back_method": "sem_fundo", "top_method": "sem_topo"},
        ("bancada", "pedra"),
    ),
    ModuleTemplate(
        "personalizado", MODULE_LABELS["personalizado"], "Estruturas",
        "Caixa paramétrica livre para regras próprias do marceneiro.",
        {"width_mm": 800, "height_mm": 850, "depth_mm": 550,
         "plinth_height_mm": 0, "plinth_recess_mm": 0,
         "door_type": "none", "door_count": 0, "shelf_count": 2,
         "divider_count": 1, "drawer_count": 0, "back_method": "sobreposto"},
        ("personalizado",),
    ),
)


def templates() -> list[ModuleTemplate]:
    return list(_CATALOGUE)


def template_by_type(module_type: str) -> ModuleTemplate | None:
    for template in _CATALOGUE:
        if template.type == module_type:
            return template
    return None


def categories() -> list[str]:
    seen: list[str] = []
    for template in _CATALOGUE:
        if template.category not in seen:
            seen.append(template.category)
    return seen
