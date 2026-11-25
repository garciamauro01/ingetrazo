# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes de rotação e aproveitamento otimizado no plano de corte."""
from __future__ import annotations

import pytest

from trazomob.production.optimizer import GuillotineOptimizer, SheetConfig


def test_optimizer_rotates_neutrals_to_fill_pockets():
    """Valida se o otimizador gira peças neutras (Branco TX) para preencher vãos úteis."""
    cfg = SheetConfig(comprimento=2750, largura=1850, refilo=15, espessura_corte=4)
    opt = GuillotineOptimizer(cfg)

    # Conjunto onde sem rotação a Base não caberia ao lado das laterais de 2000mm
    parts = [
        {"nome": "Lateral 1", "comprimento": 2000, "largura": 550, "espessura": 15, "material": "MDF Branco TX", "ignorar_veio": True},
        {"nome": "Lateral 2", "comprimento": 2000, "largura": 550, "espessura": 15, "material": "MDF Branco TX", "ignorar_veio": True},
        {"nome": "Base 1", "comprimento": 800, "largura": 550, "espessura": 15, "material": "MDF Branco TX", "ignorar_veio": True},
        {"nome": "Base 2", "comprimento": 800, "largura": 550, "espessura": 15, "material": "MDF Branco TX", "ignorar_veio": True},
        {"nome": "Base 3", "comprimento": 800, "largura": 550, "espessura": 15, "material": "MDF Branco TX", "ignorar_veio": True},
        {"nome": "Base 4", "comprimento": 800, "largura": 550, "espessura": 15, "material": "MDF Branco TX", "ignorar_veio": True},
    ]

    res = opt.optimize(parts)
    chapas = res["MDF Branco TX (15mm)"]
    assert len(chapas) == 1  # Couberam todas as 6 peças em 1 única chapa graças à rotação da Base 1!

    pecas_chapa = chapas[0].pecas
    # Verifica que houve rotação da peça para encaixe perfeito
    pecas_rotacionadas = [p for p in pecas_chapa if p.rotacionada]
    assert len(pecas_rotacionadas) >= 1
    base_rot = next(p for p in pecas_chapa if p.nome == "Base 1")
    assert base_rot.rotacionada is True
    assert base_rot.w_aloc == pytest.approx(550.0)
    assert base_rot.h_aloc == pytest.approx(800.0)
