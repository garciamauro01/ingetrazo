# SPDX-License-Identifier: GPL-3.0-or-later
from trazomob.builders.cabinet import CabinetBuilder


def _modulo(tipo, **overrides):
    params = {
        "tipo": tipo,
        "largura": 1200,
        "altura": 900,
        "profundidade": 600,
        "material": "MDF Carvalho",
        "material_frentes": "MDF Grafite",
        "espessura_fita_frentes": 1.0,
    }
    params.update(overrides)
    mod = CabinetBuilder.build_module_group(params)
    assert mod is not None
    return mod


def test_balcao_canto_porta_herda_material_e_fita_do_contexto():
    mod = _modulo("balcao_canto")
    portas = [c for c in mod.children if "Porta" in c.name]

    assert portas, [c.name for c in mod.children]
    assert all(p.ext["trazomob"]["material"] == "MDF Grafite" for p in portas)
    assert all(p.ext["trazomob"]["espessura_fita"] == 1.0 for p in portas)


def test_balcao_canto_l_portas_herdam_material_e_fita_do_contexto():
    mod = _modulo("balcao_canto_l")
    portas = [c for c in mod.children if "Porta" in c.name]

    assert len(portas) == 2, [c.name for c in mod.children]
    assert all(p.ext["trazomob"]["material"] == "MDF Grafite" for p in portas)
    assert all(p.ext["trazomob"]["espessura_fita"] == 1.0 for p in portas)


def test_porta_tempero_frente_herda_material_e_fita_do_contexto():
    mod = _modulo("porta_tempero")
    frentes = [c for c in mod.children if "Frente" in c.name]

    assert frentes, [c.name for c in mod.children]
    assert all(f.ext["trazomob"]["material"] == "MDF Grafite" for f in frentes)
    assert all(f.ext["trazomob"]["espessura_fita"] == 1.0 for f in frentes)


def test_balcao_forno_frentes_herdam_material_e_fita_do_contexto():
    mod = _modulo("balcao_forno")
    frentes = [c for c in mod.children if "Frente" in c.name]

    assert frentes, [c.name for c in mod.children]
    assert all(f.ext["trazomob"]["material"] == "MDF Grafite" for f in frentes)
    assert all(f.ext["trazomob"]["espessura_fita"] == 1.0 for f in frentes)
