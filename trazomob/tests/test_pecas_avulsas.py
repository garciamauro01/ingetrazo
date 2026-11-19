# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes de peças avulsas que usam o contrato canônico em mm."""
from trazomob.builders.cabinet import CabinetBuilder


def test_tampo_engrossado_build_module_group():
    group = CabinetBuilder.build_module_group({
        "tipo": "peca_tampo_engrossado",
        "largura": 1200,
        "altura": 36,
        "profundidade": 600,
        "esp_chapa": 18,
        "qtd_engrosso": 1,
        "larg_engrosso": 70,
        "tipo_engrosso": "3_lados",
        "material": "MDF Carvalho",
    })

    assert group is not None
    nomes = [c.name for c in group.children]
    assert any("Tampo Superior" in n for n in nomes)
    assert any("Régua Engrosso Frontal" in n for n in nomes)
    assert any("Régua Engrosso Lateral Esquerda" in n for n in nomes)
    assert any("Régua Engrosso Lateral Direita" in n for n in nomes)
    assert len(group.children) == 5  # topo + frontal + 2 laterais + reforço central


def test_prateleiras_avulsas_build_module_group():
    group = CabinetBuilder.build_module_group({
        "tipo": "peca_prateleiras_avulsas",
        "largura": 800,
        "altura": 700,
        "profundidade": 500,
        "espessura": 18,
        "num_prateleiras": 2,
        "material": "MDF Carvalho",
        "material_caixa": "MDF Carvalho",
    })

    assert group is not None
    assert len(group.children) == 2
    assert all("Prateleira Avulsa" in c.name for c in group.children)
    assert all(c.ext["trazomob"]["material"] == "MDF Carvalho" for c in group.children)
