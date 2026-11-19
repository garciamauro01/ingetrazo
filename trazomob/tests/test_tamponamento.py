from trazomob.builders.cabinet import CabinetBuilder
from trazomob.domain.catalog import MODULE_CATALOG

def test_tamponamento_vertical_build():
    # Verifica que o módulo está catalogado em Peças Avulsas
    catalog_items = MODULE_CATALOG["Peças Avulsas / Componentes"]
    item = next((i for i in catalog_items if i["id"] == "peca_tamponamento"), None)
    assert item is not None
    assert item["largura"] == 18
    assert item["altura"] == 720
    assert item["profundidade"] == 570

    # Constrói o grupo do tamponamento com 4L
    group = CabinetBuilder.build_module_group({
        "tipo": "peca_tamponamento",
        "largura": 18,
        "altura": 720,
        "profundidade": 570,
        "espessura": 18,
        "fita_caixa_modo": "4L",
    })
    assert group is not None
    assert len(group.children) == 1
    tamp = group.children[0]
    assert "Tamponamento" in tamp.name
    assert tamp.mesh is not None
    assert len(tamp.mesh.faces) == 6

    # Testa com frontal 1L
    group_1l = CabinetBuilder.build_module_group({
        "tipo": "peca_tamponamento",
        "largura": 15,
        "altura": 800,
        "profundidade": 600,
        "espessura": 15,
        "fita_caixa_modo": "frontal_1L",
    })
    assert group_1l is not None
    assert len(group_1l.children) == 1


def test_tamponamento_respeita_largura_como_espessura():
    group = CabinetBuilder.build_module_group({
        "tipo": "peca_tamponamento",
        "largura": 25,
        "altura": 720,
        "profundidade": 570,
        "espessura": 18,
    })
    meta = group.children[0].ext["trazomob"]
    assert meta["espessura"] == 25.0
    assert meta["largura"] == 570.0
    assert meta["comprimento"] == 720.0
