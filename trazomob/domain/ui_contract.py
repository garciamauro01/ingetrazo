"""Formal visual interface contract for the TrazoMob 5-tab sidebar panel.

Defines canonical defaults, tab ownership rules, and conditional visibility
predicates used by both UI controllers and anti-regression tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Mapping, Tuple

DEFAULT_PROF_RASGO_MM: float = 5.0
DEFAULT_RECUO_FUNDO_MM: float = 10.0
DEFAULT_FOLGA_FRENTES_MM: float = 3.0
DEFAULT_ELEVACAO_MM: float = 0.0

FOLGA_FRENTES_MIN_MM: int = 0
FOLGA_FRENTES_MAX_MM: int = 15
ELEVACAO_MIN_MM: int = 0
ELEVACAO_MAX_MM: int = 5000


@dataclass(frozen=True)
class TabContract:
    """Contract specification for a single sidebar tab."""

    index: int
    key: str
    section_attr: str
    required_widgets: Tuple[str, ...]
    forbidden_widgets: Tuple[str, ...] = ()


UI_TABS_CONTRACT: Mapping[str, TabContract] = {
    "medidas": TabContract(
        index=0,
        key="medidas",
        section_attr="sec_dimensoes",
        required_widgets=(
            "cb_trocar_tipo",
            "sp_largura",
            "sp_altura",
            "sp_prof",
            "sp_elevacao",
        ),
        forbidden_widgets=(
            "sp_qtd_elem",
            "cb_lado_porta_armario",
        ),
    ),
    "estrutura": TabContract(
        index=1,
        key="estrutura",
        section_attr="sec_frentes",
        required_widgets=(
            "sp_qtd_elem",
            "cb_lado_porta_armario",
            "sp_largura_gaveteiro",
            "cb_lado_gaveteiro",
            "sp_prateleiras",
            "sp_divisoes",
            "sp_rodape",
            "cb_tipo_fundo",
            "cb_esp_fundo",
            "sp_recuo_fundo",
            "sp_prof_rasgo",
            "sp_larg_travessa_frontal",
            "sp_larg_travessa_traseira",
            "chk_travessa_frontal_em_pe",
            "chk_travessa_traseira_em_pe",
            "sp_recuo_porta_topo",
        ),
        forbidden_widgets=(),
    ),
    "puxadores": TabContract(
        index=2,
        key="puxadores",
        section_attr="sec_puxadores",
        required_widgets=(
            "cb_puxador_tipo",
            "frame_perfil",
            "cb_perfil_modelo",
            "btn_gerenciar_perfis",
            "cb_altura_perfil",
            "sp_desconto_perfil",
        ),
        forbidden_widgets=(),
    ),
    "materiais": TabContract(
        index=3,
        key="materiais",
        section_attr="sec_materiais",
        required_widgets=(
            "cb_material",
            "cb_espessura",
            "cb_fita_caixa",
            "cb_material_fita_caixa",
            "cb_material_frentes",
            "cb_espessura_frentes",
            "btn_aplicar_frentes_todos",
            "btn_aplicar_caixa_todos",
            "cb_material_travessas",
            "cb_espessura_travessas",
            "cb_fita_travessas",
            "cb_material_fita_travessas",
            "btn_aplicar_travessas_todos",
        ),
        forbidden_widgets=(),
    ),
    "avancado": TabContract(
        index=4,
        key="avancado",
        section_attr="sec_ajustes",
        required_widgets=(
            "chk_gerar_furacao",
            "cb_dispositivo_fixacao",
            "cb_dispositivo_prateleira",
            "sp_folga_frentes",
            "cb_tampo_snap_parede",
        ),
        forbidden_widgets=(
            "sp_larg_travessa_frontal",
            "sp_larg_travessa_traseira",
            "chk_travessa_frontal_em_pe",
            "chk_travessa_traseira_em_pe",
            "sp_recuo_porta_topo",
            "cb_material_travessas",
            "cb_espessura_travessas",
            "cb_fita_travessas",
            "cb_material_fita_travessas",
            "btn_aplicar_travessas_todos",
        ),
    ),
}

TAB_ORDER: Tuple[str, ...] = (
    "medidas",
    "estrutura",
    "puxadores",
    "materiais",
    "avancado",
)

CANTOS_LADO_CEGO_TIPOS: FrozenSet[str] = frozenset({"balcao_canto"})


def should_show_config_gaveteiro(tipo: str) -> bool:
    """Return True when the gaveteiro width/side controls must be visible.

    Aplica-se ao balcão misto e ao rack nicho com gaveta, que compartilham os
    parâmetros ``largura_gaveteiro`` e ``lado_gaveteiro``.
    """
    return str(tipo).lower() in ("balcao_misto", "rack_nicho_gaveta")


def should_show_lado_porta_armario(
    tipo: str,
    has_porta_arm: bool,
    num_portas: int,
) -> bool:
    """Return True when `cb_lado_porta_armario` must be visible.

    Visible for corner base modules (`balcao_canto`) to flip the blind side,
    or for hinged-door modules when `num_portas` is odd (e.g., 1 or 3 doors).
    Hidden for even door counts (e.g., 0, 2, 4 doors).
    """
    if tipo in CANTOS_LADO_CEGO_TIPOS:
        return True
    if not has_porta_arm:
        return False
    return int(num_portas) > 0 and (int(num_portas) % 2 == 1)
