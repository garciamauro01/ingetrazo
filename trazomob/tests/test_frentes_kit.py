# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
from trazomob.builders.chapa_spec import ModuloMaterialContext
from trazomob.builders.frentes import FrentesKitBuilder


def test_kit_portas_giro_dimensoes_e_folgas():
    # Balcão de 800mm de largura x 700mm de altura, 2 portas
    ctx = ModuloMaterialContext(
        material_frentes="MDF Carvalho 18mm",
    )
    portas = FrentesKitBuilder.build_kit_portas_giro(
        largura_mm=800.0,
        altura_mm=700.0,
        num_portas=2,
        offset=(0.0, 0.0, 0.0),
        esp_frente_mm=18.0,
        mat_ctx=ctx,
        prefixo="Balcao Teste",
    )
    assert len(portas) == 2
    p_esq, p_dir = portas

    # Verifica nomes
    assert "Porta Esq" in p_esq.name
    assert "Porta Dir" in p_dir.name

    # Folga perimetro = 3mm em cada ponta -> largura total disponível = 800 - 6 - 3 (folga centro) = 791mm / 2 = 395.5mm
    meta_esq = p_esq.ext["trazomob"]
    meta_dir = p_dir.ext["trazomob"]
    assert meta_esq["material"] == "MDF Carvalho 18mm"
    assert round(meta_esq["largura"], 1) == 395.5 or round(meta_esq["comprimento"], 1) == 395.5


def test_resolve_folga_mm_usa_unidades_milimetricas():
    ctx = ModuloMaterialContext(folga_frentes_mm=4.0)

    assert FrentesKitBuilder.resolve_folga_mm(mat_ctx=ctx) == 4.0
    assert FrentesKitBuilder.resolve_folga_mm(folga_frentes_mm=2.5) == 2.5
    assert FrentesKitBuilder.resolve_folga_mm() == 3.0


def test_kit_frentes_gavetas_distribuicao():
    ctx = ModuloMaterialContext(
        material_frentes="MDF Grafite 18mm",
    )
    # Gaveteiro de 500mm x 700mm, 4 gavetas
    gavetas = FrentesKitBuilder.build_kit_frentes_gavetas(
        largura_mm=500.0,
        altura_mm=700.0,
        num_gavetas=4,
        offset=(0.0, 0.0, 0.0),
        esp_frente_mm=18.0,
        mat_ctx=ctx,
        prefixo="Gaveteiro",
    )
    assert len(gavetas) == 4
    for i, g in enumerate(gavetas, 1):
        assert f"Frente Gaveta {i}" in g.name
        assert g.ext["trazomob"]["material"] == "MDF Grafite 18mm"
