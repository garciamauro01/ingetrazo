# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes de geração de Tamponamento Contínuo de Linha (Envoltório)."""
from trazomob.builders.cabinet import CabinetBuilder
from trazomob.builders.tamponamento_linha import TamponamentoLinhaBuilder
from trazomob.domain.catalog import MODULE_CATALOG


def test_tamponamento_linha_catalog():
    """Valida registro do módulo no catálogo."""
    pecas = MODULE_CATALOG["Peças Avulsas / Componentes"]
    item = next((i for i in pecas if i["id"] == "peca_tamponamento_linha"), None)
    assert item is not None
    assert item["largura"] == 1600
    assert item["altura"] == 720
    assert item["tipo_envoltorio"] == "u_completo"


def test_tamponamento_linha_build_u_completo():
    """Valida construção de envoltório em U (lateral esq, lateral dir e tampo superior)."""
    groups = TamponamentoLinhaBuilder.build_tamponamento_linha(
        largura_mm=1600.0,
        altura_mm=720.0,
        prof_mm=570.0,
        esp_mm=18.0,
        esp_lateral_mm=18.0,
        tipo_envoltorio="u_completo",
        material="MDF Carvalho",
    )
    assert len(groups) == 3
    nomes = [g.name for g in groups]
    assert any("Lateral Esq" in n for n in nomes)
    assert any("Lateral Dir" in n for n in nomes)
    assert any("Tampo Superior" in n for n in nomes)


def test_tamponamento_linha_build_module_group():
    """Valida construção completa via CabinetBuilder.build_module_group."""
    group = CabinetBuilder.build_module_group({
        "tipo": "peca_tamponamento_linha",
        "largura": 2000,
        "altura": 850,
        "profundidade": 600,
        "espessura_tampo_mm": 25,
        "espessura_lateral_mm": 25,
        "tipo_envoltorio": "topo",
        "material": "MDF Louro Freijó",
    })
    assert group is not None
    assert len(group.children) == 1
    assert "Tampo Superior" in group.children[0].name

