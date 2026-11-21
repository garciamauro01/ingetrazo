# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Dados e resolução de caminho compartilhados pelas esquadrias do Trazomob."""
from __future__ import annotations

from ..assets.catalog import (
    get_esquadria_files,
    get_novas_portas_cinematica,
    get_novas_portas_folhas,
)
from ..domain.module_utils import is_esquadria, resolve_igz_path

__all__ = (
    "CORES",
    "ESQUADRIA_FILES",
    "NOVAS_PORTAS_FOLHAS",
    "NOVAS_PORTAS_CINEMATICA",
    "PORTA_PROTO_CACHE",
    "is_esquadria",
    "resolve_igz_path",
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

# ``resolve_igz_path`` e ``is_esquadria`` são reexportados de domain.module_utils:
# a resolução de arquivo e a classificação são contratos compartilhados com a
# interação, a UI e os ganchos do host — não pertencem apenas ao builder.
