import pytest

from core.scene import Scene
from trazomob.builders.cabinet import CabinetBuilder
from trazomob.production.parts import extract_parts


@pytest.mark.parametrize("n_vaos", [2, 3, 4])
def test_aereo_portas_correr_vaos(n_vaos):
    params = {
        "tipo": "aereo_correr",
        "largura": 1500,
        "altura": 600,
        "profundidade": 350,
        "num_vaos": n_vaos,
        "num_portas": n_vaos,
        "num_prateleiras": 1,
        "gerar_furacao": True,
        "exibir_portas": True,
    }
    mod = CabinetBuilder.build_module_group(params)
    assert mod is not None
    children_names = [c.name for c in mod.children]

    # Verifica caixaria
    assert any("Lateral Esquerda" in n for n in children_names)
    assert any("Lateral Direita" in n for n in children_names)
    assert any("Base Inferior" in n for n in children_names)
    assert any("Tampo Superior" in n for n in children_names)
    assert any("Fundo" in n for n in children_names)

    # Divisórias: n_vaos - 1
    divs = [n for n in children_names if "Divisoria" in n]
    assert len(divs) == n_vaos - 1

    # Portas: n_vaos portas
    portas = [n for n in children_names if "Porta" in n]
    assert len(portas) == n_vaos

    # Prateleiras: 1 por vão
    prats = [n for n in children_names if "Prat" in n or "Prateleira" in n]
    assert len(prats) == n_vaos

    # Trilhos duplos
    assert any("Trilho Inferior" in n for n in children_names)
    assert any("Trilho Superior" in n for n in children_names)

    # Todas as portas têm eixos de deslizamento interativo (slide_axis)
    for p in mod.children:
        if "Porta" in p.name:
            assert "slide_axis" in p.ext
            assert "slide_distance" in p.ext
            assert float(p.ext["slide_distance"]) > 0

    # Cutlist limpo e com peças
    scene = Scene()
    scene.groups.append(mod)
    parts = extract_parts(scene)
    assert parts
    # Trilhos de alumínio e portas são peças válidas
    p_nomes = [p["nome"] for p in parts]
    assert any("Divisoria" in p for p in p_nomes)
    assert any("Porta" in p for p in p_nomes)


def test_aereo_correr_portas_herdam_material_e_fita_do_contexto():
    mod = CabinetBuilder.build_module_group({
        "tipo": "aereo_correr",
        "largura": 1500,
        "altura": 600,
        "profundidade": 350,
        "num_vaos": 3,
        "num_portas": 3,
        "exibir_portas": True,
        "material": "MDF Carvalho",
        "material_frentes": "MDF Grafite",
        "espessura_fita_frentes": 1.0,
    })
    portas = [c for c in mod.children if "Porta" in c.name]
    assert len(portas) == 3
    assert all(c.ext["trazomob"]["material"] == "MDF Grafite" for c in portas)
    assert all(c.ext["trazomob"]["espessura_fita"] == 1.0 for c in portas)
