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


def test_gaveta_furacao_e_fixacao():
    from trazomob.builders.cabinet import CabinetBuilder

    # 1. Gaveta avulsa com furação parafuso e frente
    mod_parafuso = CabinetBuilder.build_module_group({
        "tipo": "peca_gaveta_avulsa",
        "largura": 500,
        "altura": 180,
        "profundidade": 450,
        "esp_chapa": 15,
        "tem_frente": True,
        "gerar_furacao": True,
        "dispositivo_fixacao": "parafuso",
    })
    assert mod_parafuso is not None
    pecas = mod_parafuso.children
    by_name = {p.name: p for p in pecas}

    lat_esq = by_name["Gaveta Avulsa - Lat Esq"]
    lat_dir = by_name["Gaveta Avulsa - Lat Dir"]
    cf_diant = by_name["Gaveta Avulsa - Contra-frente Diant"]
    cf_tras = by_name["Gaveta Avulsa - Contra-frente Tras"]

    ops_le = lat_esq.ext["trazomob"]["operacoes"]
    ops_ld = lat_dir.ext["trazomob"]["operacoes"]
    ops_cfd = cf_diant.ext["trazomob"]["operacoes"]
    ops_cft = cf_tras.ext["trazomob"]["operacoes"]

    # Furações nas laterais da gaveta
    assert len(ops_le) == 4
    assert len(ops_ld) == 4
    assert any("Cavilha Gaveta Caixa" in op["descricao"] for op in ops_le)
    assert any("Furo Parafuso Gaveta Caixa" in op["descricao"] for op in ops_le)

    # Furações nas contrafrentes (topos e fixação da frente externa)
    assert len(ops_cfd) == 6  # 2 topos esq/dir + 2 topos esq/dir + 2 furos fixação frente
    assert len(ops_cft) == 4  # 2 topos esq/dir + 2 topos esq/dir
    assert any("Fixação Frente" in op["descricao"] for op in ops_cfd)

    # Malhas 3D devem ter os furos perfurados (mais vértices que o paralelepípedo de 8 vértices)
    assert len(lat_esq.mesh.vertices) > 8
    assert len(lat_dir.mesh.vertices) > 8
    assert len(cf_diant.mesh.vertices) > 8
    assert len(cf_tras.mesh.vertices) > 8

    # 2. Gaveta avulsa com minifix + cavilha
    mod_minifix = CabinetBuilder.build_module_group({
        "tipo": "peca_gaveta_avulsa",
        "largura": 500,
        "altura": 180,
        "profundidade": 450,
        "esp_chapa": 15,
        "tem_frente": False,
        "gerar_furacao": True,
        "dispositivo_fixacao": "minifix_cavilha",
    })
    le_m = next(p for p in mod_minifix.children if "Lat Esq" in p.name)
    cf_m = next(p for p in mod_minifix.children if "Contra-frente Diant" in p.name)
    assert any("Minifix" in op["descricao"] for op in le_m.ext["trazomob"]["operacoes"])
    assert any("Minifix" in op["descricao"] for op in cf_m.ext["trazomob"]["operacoes"])
    # Deve conter os tambores Minifix Ø15mm na face interna da contrafrente
    assert any("Tambor Minifix" in op["descricao"] for op in cf_m.ext["trazomob"]["operacoes"])

    # 3. Teste das 3 opções de montagem de fundo da gaveta (rasgo, por_baixo, sem_fundo)
    mod_sem_fundo = CabinetBuilder.build_module_group({
        "tipo": "peca_gaveta_avulsa",
        "largura": 500,
        "altura": 180,
        "profundidade": 450,
        "tipo_fundo_gaveta": "sem_fundo",
        "tem_frente": True,
    })
    assert not any("Fundo" in p.name for p in mod_sem_fundo.children)
    assert len(mod_sem_fundo.children) == 5  # 2 lat + 2 cf + 1 frente




