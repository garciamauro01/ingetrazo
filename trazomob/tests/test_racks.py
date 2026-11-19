# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes de integração do módulo Rack Nicho com Gaveta."""
from trazomob.builders.cabinet import CabinetBuilder
from trazomob.domain.catalog import MODULE_CATALOG


def _faixa_x(mod, nome_peca: str) -> tuple[float, float]:
    peca = next(c for c in mod.children if nome_peca in c.name)
    xs: list[float] = []

    def _walk(node):
        mesh = getattr(node, "mesh", None)
        for v in getattr(mesh, "vertices", None) or []:
            xs.append(float(v.position.x()))
        for ch in getattr(node, "children", []) or []:
            _walk(ch)

    _walk(peca)
    assert xs, f"Peça sem vértices: {nome_peca}"
    return min(xs), max(xs)


def test_rack_nicho_gaveta_esta_catalogado():
    itens = MODULE_CATALOG["Racks"]
    item = next((i for i in itens if i["id"] == "rack_nicho_gaveta"), None)

    assert item is not None
    assert item["largura"] == 1600
    assert item["altura"] == 500
    assert item["profundidade"] == 450
    assert item["largura_gaveteiro"] == 600
    assert item["lado_gaveteiro"] == "esquerda"


def test_rack_nicho_gaveta_build_module_group():
    group = CabinetBuilder.build_module_group({
        "tipo": "rack_nicho_gaveta",
        "largura": 1600,
        "altura": 500,
        "profundidade": 450,
        "espessura": 18,
        "material": "MDF Carvalho",
        "largura_gaveteiro": 600,
        "lado_gaveteiro": "esquerda",
        "num_gavetas": 1,
    })

    assert group is not None
    nomes = [c.name for c in group.children]
    assert any("Rack - Base Inferior" in n for n in nomes)
    assert any("Rack - Tampo Superior" in n for n in nomes)
    assert any("Rack - Lateral Esquerda" in n for n in nomes)
    assert any("Rack - Lateral Direita" in n for n in nomes)
    assert any("Rack - Divisória" in n for n in nomes)
    assert any("Rack - Gaveta 1 Frente" in n for n in nomes)
    # 5 peças fixas (base, tampo, 2 laterais, divisória) + 6 peças da gaveta
    # + 3 ferragens (corrediças, guia telescópica e trilho fixo).
    assert len(group.children) == 14


def test_rack_nicho_gaveta_lado_direito_multiplas_gavetas():
    group = CabinetBuilder.build_module_group({
        "tipo": "rack_nicho_gaveta",
        "largura": 1600,
        "altura": 700,
        "profundidade": 450,
        "espessura": 18,
        "material": "MDF Carvalho",
        "largura_gaveteiro": 600,
        "lado_gaveteiro": "direita",
        "num_gavetas": 2,
    })

    nomes = [c.name for c in group.children]
    assert any("Rack - Gaveta 1 Frente" in n for n in nomes)
    assert any("Rack - Gaveta 2 Frente" in n for n in nomes)
    # 5 peças fixas + 2 gavetas * (6 peças + 3 ferragens)
    assert len(group.children) == 23


def test_rack_nicho_gaveta_troca_o_lado_geometricamente():
    base = {
        "tipo": "rack_nicho_gaveta",
        "largura": 1600,
        "altura": 500,
        "profundidade": 450,
        "espessura": 18,
        "material": "MDF Carvalho",
        "largura_gaveteiro": 600,
        "num_gavetas": 1,
    }

    esquerda = CabinetBuilder.build_module_group({**base, "lado_gaveteiro": "esquerda"})
    direita = CabinetBuilder.build_module_group({**base, "lado_gaveteiro": "direita"})

    div_esq = _faixa_x(esquerda, "Rack - Divisória")[0]
    div_dir = _faixa_x(direita, "Rack - Divisória")[0]
    frente_esq = _faixa_x(esquerda, "Rack - Gaveta 1 Frente")[0]
    frente_dir = _faixa_x(direita, "Rack - Gaveta 1 Frente")[0]

    assert div_esq < div_dir
    assert frente_esq < frente_dir

