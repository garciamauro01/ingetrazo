# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
import pytest
from trazomob.builders.chapa_spec import ChapaSpec, PapelChapa, ModuloMaterialContext


def test_chapa_spec_inheritance_caixa():
    ctx = ModuloMaterialContext(
        material_caixa="MDF Carvalho 18mm",
        material_fita_caixa="Fita Carvalho 1mm",
        fita_caixa_modo="4L",
        espessura_fita_padrao=1.0,
    )
    spec = ChapaSpec.resolve("Lateral Esquerda", PapelChapa.LATERAL_ESQUERDA, ctx)
    assert spec.material == "MDF Carvalho 18mm"
    assert spec.material_fita == "Fita Carvalho 1mm"
    assert spec.fita_c1 is True and spec.fita_c2 is True and spec.fita_l1 is True and spec.fita_l2 is True
    assert spec.espessura_fita == 1.0


def test_chapa_spec_frentes_inheritance():
    ctx = ModuloMaterialContext(
        material_caixa="MDF Branco TX 15mm",
        material_frentes="MDF Grafite 18mm",
        material_fita_frentes="Fita Grafite 0.45mm",
    )
    spec_porta = ChapaSpec.resolve("Porta Giro", PapelChapa.PORTA, ctx)
    assert spec_porta.material == "MDF Grafite 18mm"
    assert spec_porta.material_fita == "Fita Grafite 0.45mm"
    assert (spec_porta.fita_c1, spec_porta.fita_c2, spec_porta.fita_l1, spec_porta.fita_l2) == (True, True, True, True)


def test_chapa_spec_prateleira_padrao():
    ctx = ModuloMaterialContext(
        material_caixa="MDF Branco TX 15mm",
        fita_caixa_modo="4L",  # Mesmo que a caixa seja 4L, prateleira interna é 1L frontal por regra de marcenaria
    )
    spec = ChapaSpec.resolve("Prateleira Movel", PapelChapa.PRATELEIRA, ctx)
    assert spec.material == "MDF Branco TX 15mm"
    assert (spec.fita_c1, spec.fita_c2, spec.fita_l1, spec.fita_l2) == (True, False, False, False)


def test_chapa_spec_fundo_sem_fita():
    ctx = ModuloMaterialContext(fita_caixa_modo="4L")
    spec = ChapaSpec.resolve("Fundo 6mm", PapelChapa.FUNDO, ctx)
    assert (spec.fita_c1, spec.fita_c2, spec.fita_l1, spec.fita_l2) == (False, False, False, False)


def test_modulo_material_context_from_dict_le_fitas_de_frentes():
    ctx = ModuloMaterialContext.from_dict({
        "material": "MDF Branco TX 15mm",
        "fita_frentes_modo": "sem_fita",
        "espessura_fita_frentes": 1.0,
    })
    assert ctx.fita_frentes_modo == "sem_fita"
    assert ctx.espessura_fita_frentes == 1.0


def test_prateleira_override_all_false_desliga_fitas():
    """Intenção explícita de remover toda a fita deve prevalecer sobre o contexto."""
    from trazomob.builders.cabinet import CabinetBuilder

    ctx = ModuloMaterialContext(fita_caixa_modo="4L")
    group = CabinetBuilder.build_prateleira(
        name="Prateleira Sem Fita",
        origin=(0.0, 0.0, 0.0),
        size=(0.6, 0.3, 0.018),
        material="MDF Branco TX 15mm",
        fita_c1=False, fita_c2=False, fita_l1=False, fita_l2=False,
        ctx=ctx,
    )
    meta = group.ext["trazomob"]
    assert (meta["fita_c1"], meta["fita_c2"], meta["fita_l1"], meta["fita_l2"]) == (False, False, False, False)
