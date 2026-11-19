# SPDX-License-Identifier: GPL-3.0-or-later
from trazomob.builders.cabinet import CabinetBuilder


def _modulo(tipo, **overrides):
    params = {
        "tipo": tipo,
        "largura": 1600,
        "altura": 2200,
        "profundidade": 600,
        "material": "MDF Carvalho",
        "material_frentes": "MDF Grafite",
        "espessura_fita_frentes": 1.0,
    }
    params.update(overrides)
    mod = CabinetBuilder.build_module_group(params)
    assert mod is not None
    return mod


def test_roupeiro_correr_portas_herdam_material_e_fita_do_contexto():
    mod = _modulo("roupeiro_correr", num_vaos=3, num_portas=3, exibir_portas=True)
    portas = [c for c in mod.children if "Porta" in c.name]

    assert len(portas) == 3
    assert all(p.ext["trazomob"]["material"] == "MDF Grafite" for p in portas)
    assert all(p.ext["trazomob"]["espessura_fita"] == 1.0 for p in portas)


def test_armario_prateleiras_portas_herdam_material_e_fita_do_contexto():
    mod = _modulo("armario_prateleiras", num_portas=2, num_prateleiras=3)
    portas = [c for c in mod.children if "Porta" in c.name]
    prateleiras = [c for c in mod.children if "Prateleira" in c.name]

    assert len(portas) == 2
    assert all(p.ext["trazomob"]["material"] == "MDF Grafite" for p in portas)
    assert all(p.ext["trazomob"]["espessura_fita"] == 1.0 for p in portas)

    # Estrutura continua no material da caixa
    assert prateleiras
    assert all(p.ext["trazomob"]["material"] == "MDF Carvalho" for p in prateleiras)


def test_roupeiro_cabideiro_portas_herdam_material_e_fita_do_contexto():
    mod = _modulo("roupeiro", num_portas=2)
    portas = [c for c in mod.children if "Porta" in c.name]

    assert len(portas) == 2
    assert all(p.ext["trazomob"]["material"] == "MDF Grafite" for p in portas)
    assert all(p.ext["trazomob"]["espessura_fita"] == 1.0 for p in portas)


def test_armario_divisoria_estrutura_usa_material_da_caixa_na_fita():
    mod = _modulo("armario_2p_divisao")
    divisoria = next(c for c in mod.children if "Divisória Central" in c.name)
    meta = divisoria.ext["trazomob"]

    assert meta["material"] == "MDF Carvalho"
    assert meta["material_fita"] == "MDF Carvalho"


def test_armario_maleiro_tamponado_respeita_material_de_tamponamento():
    mod = _modulo(
        "armario_maleiro_tamponado",
        material_tamponamento="MDF Grafite",
    )
    tamponamentos = [c for c in mod.children if "Tamponamento Lateral" in c.name]

    assert len(tamponamentos) == 2
    assert all(t.ext["trazomob"]["material"] == "MDF Grafite" for t in tamponamentos)

