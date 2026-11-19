# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""API pública canônica para construir uma chapa a partir de um :class:`ChapaSpec`.

Camadas de unidade do plugin:

- **Domínio / catálogo / cutlist:** milímetros (mm);
- **Geometria 3D:** metros (m).

Use :func:`build_chapa` para a camada de geometria (metros) ou
:func:`build_chapa_mm` para receber medidas em milímetros e converter na fronteira.
``create_board_group`` continua sendo a fábrica de baixo nível (metros).
"""
from __future__ import annotations

from typing import Any

from core.group import Group

from .chapa_spec import ChapaSpec
from .mesh_utils import create_board_group


def build_chapa(
    spec: ChapaSpec,
    origin: tuple[float, float, float],
    size: tuple[float, float, float],
    **kwargs: Any,
) -> Group:
    """Cria uma chapa canônica em **metros** a partir de uma especificação resolvida.

    Material, fitas, espessura da fita, veio e operações vêm de ``spec``.
    ``kwargs`` aceita os demais parâmetros visuais/geométricos de
    ``create_board_group`` (cor, puxador, ``door_side`` etc.).
    """
    mat_fita = kwargs.pop("material_fita", spec.material_fita)
    esp_fita = kwargs.pop("espessura_fita", spec.espessura_fita)
    ops = kwargs.pop("operacoes", spec.operacoes)
    ignorar_v = kwargs.pop("ignorar_veio", spec.ignorar_veio)
    return create_board_group(
        name=spec.nome,
        origin=origin,
        size=size,
        material=spec.material,
        fita_c1=spec.fita_c1,
        fita_c2=spec.fita_c2,
        fita_l1=spec.fita_l1,
        fita_l2=spec.fita_l2,
        material_fita=mat_fita,
        espessura_fita=esp_fita,
        ignorar_veio=ignorar_v,
        operacoes=ops,
        spec=spec,
        **kwargs,
    )


def build_chapa_mm(
    spec: ChapaSpec,
    origin_mm: tuple[float, float, float],
    size_mm: tuple[float, float, float],
    **kwargs: Any,
) -> Group:
    """Versão de :func:`build_chapa` que recebe origem e tamanho em **milímetros**."""
    return build_chapa(
        spec,
        (
            origin_mm[0] / 1000.0,
            origin_mm[1] / 1000.0,
            origin_mm[2] / 1000.0,
        ),
        (
            size_mm[0] / 1000.0,
            size_mm[1] / 1000.0,
            size_mm[2] / 1000.0,
        ),
        **kwargs,
    )
