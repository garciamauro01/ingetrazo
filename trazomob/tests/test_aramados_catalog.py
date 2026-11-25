# SPDX-License-Identifier: GPL-3.0-or-later
"""Testes unitários para o catálogo de ferragens e aramados interativos."""
from __future__ import annotations

from trazomob.domain.aramados_catalog import (
    ARAMADOS_CATALOG,
    build_aramado_group,
    list_compatible_aramados,
)


def test_list_compatible_aramados_filters_by_dimensions_and_category():
    small = list_compatible_aramados(200.0, 500.0, 700.0, category="balcao")
    ids_small = [s.id for s in small]
    assert "porta_temperos" in ids_small
    assert "lixeira_dupla" not in ids_small

    wide_aereo = list_compatible_aramados(600.0, 320.0, 700.0, category="aereo")
    assert [s.id for s in wide_aereo] == ["escorredor_loucas"]


def test_build_aramado_group_creates_valid_3d_group_and_pricing_metadata():
    grp = build_aramado_group("lixeira_dupla", 600.0, 550.0, 720.0)
    assert grp.name == "Aramado_lixeira_dupla"
    assert grp.mesh is not None and len(grp.mesh.faces) > 0
    meta = grp.ext["trazomob_aramado"]
    assert meta["id"] == "lixeira_dupla"
    assert meta["unit_price"] == ARAMADOS_CATALOG["lixeira_dupla"].unit_price
