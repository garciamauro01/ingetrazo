# SPDX-License-Identifier: GPL-3.0-or-later
"""Testes unitários para gestão de retalhos no plano de corte."""
from __future__ import annotations

from pathlib import Path

from trazomob.production.remnants import RemnantStock


def test_remnant_stock_find_best_match_and_rotation():
    stock = RemnantStock()
    r_big = stock.add_remnant("MDF Branco TX 15mm", 15.0, 1200.0, 800.0)
    r_small = stock.add_remnant("MDF Branco TX 15mm", 15.0, 600.0, 400.0)
    stock.add_remnant("MDF Carvalho 15mm", 15.0, 500.0, 500.0)

    # Peça 350x550 cabe no retalho 600x400 rotacionando (sem veio)
    match = stock.find_best_match("MDF Branco TX 15mm", 15.0, 350.0, 550.0)
    assert match is not None
    assert match.id == r_small.id
    assert r_big.area_m2 > r_small.area_m2


def test_remnant_stock_save_and_load_roundtrip(tmp_path: Path):
    db_path = tmp_path / "remnants.json"
    stock = RemnantStock()
    r1 = stock.add_remnant("MDF Grafite 18mm", 18.0, 900.0, 450.0, grain=True, notes="Sobra lateral")
    stock.save(db_path)

    loaded = RemnantStock.load(db_path)
    assert r1.id in loaded.items
    assert loaded.items[r1.id].grain is True
    assert loaded.items[r1.id].notes == "Sobra lateral"
    assert loaded.remove_remnant(r1.id) is True
