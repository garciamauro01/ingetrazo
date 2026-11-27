# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Canonical public API for building a board from a :class:`ChapaSpec`.

Plugin unit layers:

- **Domain / catalog / cutlist:** millimeters (mm);
- **3D geometry:** meters (m).

Use :func:`build_chapa` for the geometry layer (meters) or
:func:`build_chapa_mm` to accept dimensions in millimeters and convert at the boundary.
``create_board_group`` remains the low-level factory (meters).
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
    """Create a canonical board in **meters** from a resolved specification.

    Material, edge banding, banding thickness, grain direction, and operations
    come from ``spec``. ``kwargs`` accepts the remaining visual/geometric
    parameters of ``create_board_group`` (color, handle, ``door_side``, etc.).
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
    """Variant of :func:`build_chapa` that accepts origin and size in **millimeters**."""
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
