# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Per-face magnetic wall-snap contract for TrazoMob pieces and modules.

Traditional wall snapping assumes the rear face of the module rests against
the wall (cabinet back panel). Standalone pieces, such as a thickened top
panel, can be used in multiple orientations and need to choose which face
snaps to the wall — or disable snapping altogether.

Horizontal faces (``superior`` and ``inferior``) snap to the wall by
tilting the piece 90 degrees around the local X axis so that the top (or
bottom) lies flat against the wall like a vertical panel.

The ``snap_parede`` parameter is stored in the module metadata and read by
magnetic dragging (``interaction/magnetic_drag_snap.py``).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

SNAP_PAREDE_AUTO = "auto"
SNAP_PAREDE_TRASEIRA = "traseira"
SNAP_PAREDE_FRENTE = "frente"
SNAP_PAREDE_ESQUERDA = "esquerda"
SNAP_PAREDE_DIREITA = "direita"
SNAP_PAREDE_SUPERIOR = "superior"
SNAP_PAREDE_INFERIOR = "inferior"
SNAP_PAREDE_NENHUM = "nenhum"

DEFAULT_SNAP_PAREDE: str = SNAP_PAREDE_AUTO

# (persisted value, UI display label)
SNAP_PAREDE_OPCOES: tuple[tuple[str, str], ...] = (
    (SNAP_PAREDE_AUTO, "Automático (fundo na parede)"),
    (SNAP_PAREDE_TRASEIRA, "Traseira na parede"),
    (SNAP_PAREDE_FRENTE, "Frente na parede"),
    (SNAP_PAREDE_ESQUERDA, "Lateral esquerda na parede"),
    (SNAP_PAREDE_DIREITA, "Lateral direita na parede"),
    (SNAP_PAREDE_SUPERIOR, "Face superior (tombada na parede)"),
    (SNAP_PAREDE_INFERIOR, "Face inferior (tombada na parede)"),
    (SNAP_PAREDE_NENHUM, "Sem snap"),
)

SNAP_PAREDE_VALORES: tuple[str, ...] = tuple(valor for valor, _ in SNAP_PAREDE_OPCOES)

_ALIASES: Mapping[str, str] = {
    "": SNAP_PAREDE_AUTO,
    "automatico": SNAP_PAREDE_AUTO,
    "automática": SNAP_PAREDE_AUTO,
    "fundo": SNAP_PAREDE_TRASEIRA,
    "traseiro": SNAP_PAREDE_TRASEIRA,
    "back": SNAP_PAREDE_TRASEIRA,
    "dianteira": SNAP_PAREDE_FRENTE,
    "frontal": SNAP_PAREDE_FRENTE,
    "front": SNAP_PAREDE_FRENTE,
    "esq": SNAP_PAREDE_ESQUERDA,
    "left": SNAP_PAREDE_ESQUERDA,
    "dir": SNAP_PAREDE_DIREITA,
    "right": SNAP_PAREDE_DIREITA,
    "topo": SNAP_PAREDE_SUPERIOR,
    "top": SNAP_PAREDE_SUPERIOR,
    "cima": SNAP_PAREDE_SUPERIOR,
    "base": SNAP_PAREDE_INFERIOR,
    "bottom": SNAP_PAREDE_INFERIOR,
    "baixo": SNAP_PAREDE_INFERIOR,
    "none": SNAP_PAREDE_NENHUM,
    "sem": SNAP_PAREDE_NENHUM,
    "desligado": SNAP_PAREDE_NENHUM,
}

# Pieces that currently expose wall-snap face selection in the UI.
# Simply add new IDs here to reuse the same contract.
SNAP_PAREDE_TIPOS = frozenset({
    "peca_tampo_engrossado",
    "tampo_engrossado",
})


def should_show_snap_parede(tipo: str) -> bool:
    """Returns True when the piece supports wall-snap face configuration."""
    return str(tipo).lower() in SNAP_PAREDE_TIPOS


def normalize_snap_parede(value: Any) -> str:
    """Normalizes the persisted value, accepting aliases and falling back to ``auto``."""
    if value is None:
        return DEFAULT_SNAP_PAREDE
    texto = str(value).strip().lower()
    if texto in SNAP_PAREDE_VALORES:
        return texto
    return _ALIASES.get(texto, DEFAULT_SNAP_PAREDE)


def get_module_snap_parede(mod: Any) -> str:
    """Reads ``snap_parede`` from the module metadata (defaulting to ``auto``)."""
    from .module_utils import is_library_decoration

    if is_library_decoration(mod):
        return SNAP_PAREDE_NENHUM
    ext = getattr(mod, "ext", None)
    if not isinstance(ext, dict):
        return DEFAULT_SNAP_PAREDE
    for chave in ("trazomob_module", "trazomob_esquadria", "trazomob"):
        info = ext.get(chave)
        if isinstance(info, dict) and "snap_parede" in info:
            return normalize_snap_parede(info.get("snap_parede"))
    return DEFAULT_SNAP_PAREDE


def snap_face_tilt_deg(snap_parede: Any) -> float:
    """Tilt angle (degrees) around the local X axis to rest the face on the wall.

    - ``superior``: -90 (local top +Z points toward local rear +Y).
    - ``inferior``: +90 (local bottom -Z points toward local rear +Y).
    - Other faces: 0 (the piece remains flat).

    After tilting, the chosen face points in the rear direction, so wall
    snapping reuses the same math as ``traseira``.
    """
    face = normalize_snap_parede(snap_parede)
    if face == SNAP_PAREDE_SUPERIOR:
        return -90.0
    if face == SNAP_PAREDE_INFERIOR:
        return 90.0
    return 0.0


def snap_face_target_rotation_deg(nx: float, ny: float, snap_parede: Any) -> float:
    """``rot_z`` angle (degrees, multiple of 90) to align the chosen face to the wall.

    ``(nx, ny)`` is the wall normal pointing into the room.
    In the module builder, local front points to ``-Y`` and local back to
    ``+Y``. The result positions the selected face against the wall.

    Tilted faces (``superior``/``inferior``) behave like ``traseira``:
    after tilting around X, the chosen face points toward local back (+Y).
    ``nenhum`` does not rotate the module.
    """
    face = normalize_snap_parede(snap_parede)
    if face == SNAP_PAREDE_NENHUM:
        return 0.0
    base = math.degrees(math.atan2(float(ny), float(nx)))
    if face == SNAP_PAREDE_FRENTE:
        base -= 90.0
    elif face == SNAP_PAREDE_ESQUERDA:
        pass
    elif face == SNAP_PAREDE_DIREITA:
        base += 180.0
    else:  # Fallback: auto / rear / top / bottom face
        base += 90.0
    return round(base / 90.0) * 90.0 % 360.0
