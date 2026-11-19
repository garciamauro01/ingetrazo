# SPDX-License-Identifier: GPL-3.0-or-later
from trazomob.builders.bancadas import BancadaBuilder


def test_bancada_reta_preserva_material_e_nao_limita_pedra():
    pieces = BancadaBuilder.build_bancada_reta(
        3000.0,
        prof_mm=600.0,
        material="Granito Preto São Gabriel 20mm",
    )
    tampo = next(p for p in pieces if "Tampo Superior" in p.name)
    meta = tampo.ext["trazomob"]

    assert meta["material"] == "Granito Preto São Gabriel 20mm"
    # Pedra não está sujeita ao limite de chapa de MDF (2720 mm)
    assert meta["comprimento"] == 3000.0
    assert meta["espessura"] == 20.0


def test_bancada_ilha_gera_saias_nos_quatro_lados():
    pieces = BancadaBuilder.build_bancada_ilha(
        1800.0,
        prof_mm=900.0,
        altura_saia_mm=60.0,
        material="Quartzo Branco Calacatta 20mm",
    )
    nomes = [p.name for p in pieces]
    assert any("Tampo Gourmet" in n for n in nomes)
    assert sum("Saia" in n for n in nomes) == 4
    assert all(
        p.ext["trazomob"]["material"] == "Quartzo Branco Calacatta 20mm"
        for p in pieces
        if "trazomob" in getattr(p, "ext", {})
    )
