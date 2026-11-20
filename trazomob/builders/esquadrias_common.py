# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Dados e resolução de caminho compartilhados pelas esquadrias do Trazomob."""
from __future__ import annotations

from pathlib import Path

from ..assets.catalog import (
    get_esquadria_files,
    get_novas_portas_cinematica,
    get_novas_portas_folhas,
)

CORES = {
    "madeira_branca": (0.95, 0.95, 0.95),
    "madeira_freijo": (0.68, 0.46, 0.28),
    "madeira_nogueira": (0.42, 0.28, 0.18),
    "aluminio_preto": (0.15, 0.15, 0.15),
    "aluminio_branco": (0.92, 0.92, 0.92),
    "aluminio_inox": (0.75, 0.75, 0.78),
    "vidro_incolor": (0.85, 0.92, 0.95),
    "vidro_fume": (0.35, 0.35, 0.38),
    "metal_macaneta": (0.80, 0.80, 0.82),
}

ESQUADRIA_FILES = get_esquadria_files()
NOVAS_PORTAS_FOLHAS = get_novas_portas_folhas()
NOVAS_PORTAS_CINEMATICA = get_novas_portas_cinematica()
PORTA_PROTO_CACHE: dict[str, tuple[list, float, float, float]] = {}


def resolve_igz_path(base_dir, item_id: str):
    """Resolve o .igz de uma esquadria, com portas e janelas em pastas próprias.

    O nome do arquivo é preservado para não afetar os carregadores que
    reconhecem o modelo por ``igz_path.name``. A subpasta vem do prefixo do
    id e é definitiva: janelas só em ``janelas/``, portas só em ``portas/``.
    Não há busca em nenhuma outra pasta.
    """
    from pathlib import Path
    components = Path(base_dir) / "assets" / "components"
    subpasta = "janelas" if item_id.startswith("janela_") else "portas"
    mapped = ESQUADRIA_FILES.get(item_id)
    arquivo = mapped[0] if mapped else f"{item_id}.igz"
    candidatos = list(dict.fromkeys([
        components / subpasta / f"{item_id}.igz",
        components / subpasta / arquivo,
    ]))
    for candidato in candidatos:
        if candidato.exists():
            return candidato
    # Nenhum arquivo encontrado: devolve o caminho canônico ao chamador.
    return candidatos[0]


def is_esquadria(item_id: str) -> bool:
    """Um id é esquadria quando está no manifesto ou usa um prefixo reservado."""
    if not isinstance(item_id, str):
        return False
    return (item_id in ESQUADRIA_FILES
            or item_id.startswith("janela_")
            or item_id.startswith("porta_"))
