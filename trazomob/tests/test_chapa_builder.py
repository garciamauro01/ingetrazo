# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
import pytest

from trazomob.builders.chapa_builder import build_chapa, build_chapa_mm
from trazomob.builders.chapa_spec import (
    ChapaSpec,
    ModuloMaterialContext,
    PapelChapa,
)


def _ctx():
    return ModuloMaterialContext(
        material_caixa="MDF Carvalho",
        material_frentes="MDF Grafite",
        material_fita_frentes="Fita Grafite",
        espessura_fita_frentes=1.0,
    )


def test_build_chapa_aplica_spec_em_metros():
    spec = ChapaSpec.resolve(
        "Lateral", PapelChapa.LATERAL_ESQUERDA, _ctx(),
        fita_override=(True, False, False, True),
    )
    group = build_chapa(spec, (0.0, 0.0, 0.0), (1.2, 0.6, 0.018))
    meta = group.ext["trazomob"]

    assert meta["material"] == "MDF Carvalho"
    assert meta["comprimento"] == 1200.0
    assert meta["largura"] == 600.0
    assert meta["espessura"] == 18.0
    assert (meta["fita_c1"], meta["fita_c2"], meta["fita_l1"], meta["fita_l2"]) == (
        True, False, False, True,
    )


def test_build_chapa_mm_converte_medidas_e_origem():
    spec = ChapaSpec.resolve("Base", PapelChapa.BASE_INFERIOR, _ctx())
    group = build_chapa_mm(spec, (100.0, 200.0, 300.0), (1200.0, 600.0, 18.0))
    meta = group.ext["trazomob"]

    assert meta["comprimento"] == 1200.0
    assert meta["largura"] == 600.0
    assert meta["espessura"] == 18.0

    xs = [v.position.x() for v in group.mesh.vertices]
    ys = [v.position.y() for v in group.mesh.vertices]
    zs = [v.position.z() for v in group.mesh.vertices]
    assert min(xs) == pytest.approx(0.1, abs=1e-5)
    assert min(ys) == pytest.approx(0.2, abs=1e-5)
    assert min(zs) == pytest.approx(0.3, abs=1e-5)


def test_build_chapa_frente_herda_material_e_fita_do_contexto():
    spec = ChapaSpec.resolve("Frente", PapelChapa.FRENTE_GAVETA, _ctx())
    group = build_chapa(spec, (0.0, 0.0, 0.0), (0.6, 0.018, 0.15))
    meta = group.ext["trazomob"]

    assert meta["material"] == "MDF Grafite"
    assert meta["material_fita"] == "Fita Grafite"
    assert meta["espessura_fita"] == 1.0


def test_build_chapa_resolve_cor_automaticamente_do_catalogo():
    from trazomob.domain.materials_catalog import get_material_color
    spec = ChapaSpec.resolve("Prateleira Freijo", PapelChapa.PRATELEIRA, _ctx(), material_override="MDF Louro Freijo 15mm")
    group = build_chapa(spec, (0.0, 0.0, 0.0), (0.8, 0.5, 0.015))

    cor_esperada = get_material_color("MDF Louro Freijo 15mm")
    assert group.mesh.faces[0].attrs["color"] == cor_esperada

