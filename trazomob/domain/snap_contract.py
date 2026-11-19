# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Contrato de snap magnetico por face para pecas e modulos do TrazoMob.

O snap de parede tradicional assume que a face traseira do modulo encosta na
parede (fundo do armario). Pecas avulsas, como o tampo engrossado, podem ser
usadas em varias posicoes e precisam escolher qual face adere a parede - ou
nao aderir a nenhuma.

As faces horizontais (``superior`` e ``inferior``) aderem a parede tombando a
peca 90 graus em torno do eixo X local, de modo que o topo (ou a base) fique
plano contra a parede, como um painel vertical.

O parametro ``snap_parede`` e gravado nos metadados do modulo e lido pelo
arraste magnetico (``interaction/magnetic_drag_snap.py``).
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Tuple

SNAP_PAREDE_AUTO = "auto"
SNAP_PAREDE_TRASEIRA = "traseira"
SNAP_PAREDE_FRENTE = "frente"
SNAP_PAREDE_ESQUERDA = "esquerda"
SNAP_PAREDE_DIREITA = "direita"
SNAP_PAREDE_SUPERIOR = "superior"
SNAP_PAREDE_INFERIOR = "inferior"
SNAP_PAREDE_NENHUM = "nenhum"

DEFAULT_SNAP_PAREDE: str = SNAP_PAREDE_AUTO

# (valor persistido, rotulo exibido na UI)
SNAP_PAREDE_OPCOES: Tuple[Tuple[str, str], ...] = (
    (SNAP_PAREDE_AUTO, "Automático (fundo na parede)"),
    (SNAP_PAREDE_TRASEIRA, "Traseira na parede"),
    (SNAP_PAREDE_FRENTE, "Frente na parede"),
    (SNAP_PAREDE_ESQUERDA, "Lateral esquerda na parede"),
    (SNAP_PAREDE_DIREITA, "Lateral direita na parede"),
    (SNAP_PAREDE_SUPERIOR, "Face superior (tombada na parede)"),
    (SNAP_PAREDE_INFERIOR, "Face inferior (tombada na parede)"),
    (SNAP_PAREDE_NENHUM, "Sem snap"),
)

SNAP_PAREDE_VALORES: Tuple[str, ...] = tuple(valor for valor, _ in SNAP_PAREDE_OPCOES)

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

# Pecas que hoje expõem a escolha de face de snap na interface.
# Basta acrescentar novos ids aqui para reutilizar o mesmo contrato.
SNAP_PAREDE_TIPOS = frozenset({
    "peca_tampo_engrossado",
    "tampo_engrossado",
})


def should_show_snap_parede(tipo: str) -> bool:
    """Retorna True quando a peca aceita configuracao de face de snap."""
    return str(tipo).lower() in SNAP_PAREDE_TIPOS


def normalize_snap_parede(value: Any) -> str:
    """Normaliza o valor persistido, aceitando aliases e caindo em ``auto``."""
    if value is None:
        return DEFAULT_SNAP_PAREDE
    texto = str(value).strip().lower()
    if texto in SNAP_PAREDE_VALORES:
        return texto
    return _ALIASES.get(texto, DEFAULT_SNAP_PAREDE)


def get_module_snap_parede(mod: Any) -> str:
    """Le ``snap_parede`` dos metadados do modulo (com fallback ``auto``)."""
    ext = getattr(mod, "ext", None)
    if not isinstance(ext, dict):
        return DEFAULT_SNAP_PAREDE
    for chave in ("trazomob_module", "trazomob_esquadria", "trazomob"):
        info = ext.get(chave)
        if isinstance(info, dict) and "snap_parede" in info:
            return normalize_snap_parede(info.get("snap_parede"))
    return DEFAULT_SNAP_PAREDE


def snap_face_tilt_deg(snap_parede: Any) -> float:
    """Inclinacao (graus) em torno do eixo X local para apoiar a face na parede.

    - ``superior``: -90 (o topo local +Z passa a apontar para a traseira +Y).
    - ``inferior``: +90 (a base local -Z passa a apontar para a traseira +Y).
    - Demais faces: 0 (a peca permanece deitada).

    Depois do tombamento a face escolhida fica na direcao da traseira, por isso
    o encaixe em paredes reaproveita a mesma matematica de ``traseira``.
    """
    face = normalize_snap_parede(snap_parede)
    if face == SNAP_PAREDE_SUPERIOR:
        return -90.0
    if face == SNAP_PAREDE_INFERIOR:
        return 90.0
    return 0.0


def snap_face_target_rotation_deg(nx: float, ny: float, snap_parede: Any) -> float:
    """Angulo ``rot_z`` (graus, multiplo de 90) para encostar a face escolhida.

    ``(nx, ny)`` e a normal da parede apontando para dentro do ambiente.
    No construtor do modulo a frente local aponta para ``-Y`` e o fundo para
    ``+Y``. O resultado posiciona a face selecionada contra a parede.

    Faces tombadas (``superior``/``inferior``) se comportam como ``traseira``:
    apos a inclinacao em X, a face escolhida aponta para o fundo local (+Y).
    ``nenhum`` nao gira o modulo.
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
    else:  # auto / traseira / superior / inferior
        base += 90.0
    return round(base / 90.0) * 90.0 % 360.0
