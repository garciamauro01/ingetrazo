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


def test_gaveta_avulsa_canonica():
    from trazomob.builders.parts import CustomPartsBuilder
    from trazomob.builders.drawers import CanonicalDrawerBuilder

    # 1. Teste via CanonicalDrawerBuilder direto
    pecas = CanonicalDrawerBuilder.build_gaveta_completa(
        prefixo="Gaveta Teste",
        largura=0.60,
        profundidade=0.50,
        altura=0.20,
        esp_caixa_mm=18.0,
        material_caixa="MDF Branco TX 18mm",
        esp_fundo_mm=6.0,
        incluir_frente=True,
    )
    assert len(pecas) == 6  # 2 laterais + 2 contrafrentes + 1 fundo + 1 frente
    nomes = [p.name for p in pecas]
    assert any("Lat Esq" in n for n in nomes)
    assert any("Lat Dir" in n for n in nomes)
    assert any("Contra-frente Diant" in n for n in nomes)
    assert any("Contra-frente Tras" in n for n in nomes)
    assert any("Fundo 6mm" in n for n in nomes)
    assert any("Frente" in n for n in nomes)

    # 2. Teste via CustomPartsBuilder.build_peca_avulsa com subtipo 'gaveta_avulsa'
    pecas_avulsas = CustomPartsBuilder.build_peca_avulsa(
        subtipo="gaveta_avulsa",
        largura_mm=500,
        altura_mm=180,
        prof_mm=450,
        esp_mm=18.0,
        material="MDF Grafite 18mm",
        tipo_fundo="rasgo",
        incluir_frente=False,
    )
    assert len(pecas_avulsas) == 5  # 2 laterais + 2 contrafrentes + 1 fundo
    assert all(p.ext.get("trazomob", {}).get("material") in ("MDF Grafite 18mm", "MDF Fundo 6mm") for p in pecas_avulsas)

