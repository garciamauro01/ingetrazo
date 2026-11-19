# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Relatório agregado de aproveitamento e sobras (Feature 3).

Valida ``resumo_aproveitamento``: agrega por material e no total — chapas,
peças alocadas, área bruta/útil, aproveitamento %, sobras (retalhos >= 200x200),
metros de fita de borda e peças não alocadas.
"""
from __future__ import annotations

from trazomob.production.optimizer import (
    CutPiece,
    CutSheet,
    GuillotineOptimizer,
    ResumoAproveitamento,
    SheetConfig,
    resumo_aproveitamento,
)


def _peca(nome: str, comp: float = 700.0, larg: float = 400.0, mat: str = "MDF (18mm)") -> CutPiece:
    return CutPiece(
        id=1,
        nome=nome,
        comprimento=comp,
        largura=larg,
        espessura=18.0,
        material=mat,
        comprimento_final=comp,
        largura_final=larg,
    )


def _chapa(indice: int, material: str, area_util: float, pecas_qtd: int,
           sobras_qtd: int = 0, metros_fita: float = 0.0) -> CutSheet:
    chapa = CutSheet(
        indice=indice,
        material=material,
        espessura=18.0,
        comprimento_bruto=2750.0,
        largura_bruto=1850.0,
        area_util_mm2=area_util,
        aproveitamento_pct=round((area_util / (2750.0 * 1850.0)) * 100.0, 1),
        metros_fita=metros_fita,
    )
    for i in range(pecas_qtd):
        chapa.pecas.append(_peca(f"{material} P{i+1}"))
    for i in range(sobras_qtd):
        chapa.sobras.append((100.0 + i * 250, 100.0, 300.0, 300.0))  # 90.000 mm² cada
    return chapa


def test_resumo_por_material_agrega_chapas_e_pecas():
    sheets = {
        "MDF (18mm)": [
            _chapa(1, "MDF (18mm)", 1_000_000.0, 3, sobras_qtd=2, metros_fita=5.0),
            _chapa(2, "MDF (18mm)", 1_200_000.0, 4, sobras_qtd=1, metros_fita=3.0),
        ],
        "MDF (15mm)": [
            _chapa(3, "MDF (15mm)", 800_000.0, 2, sobras_qtd=0, metros_fita=2.0),
        ],
    }
    resumo = resumo_aproveitamento(sheets)

    rm18 = resumo.por_material["MDF (18mm)"]
    assert rm18.chapas == 2
    assert rm18.pecas == 7
    assert rm18.area_bruta_mm2 == 2 * 2750.0 * 1850.0
    assert rm18.area_util_mm2 == 2_200_000.0
    assert rm18.sobras == 3
    assert rm18.metros_fita == 8.0
    # Aproveitamento = soma útil / soma bruta
    esperado = round((2_200_000.0 / (2 * 2750.0 * 1850.0)) * 100.0, 1)
    assert rm18.aproveitamento_pct == esperado

    rm15 = resumo.por_material["MDF (15mm)"]
    assert rm15.chapas == 1
    assert rm15.pecas == 2
    assert rm15.sobras == 0


def test_resumo_totais_do_projeto():
    sheets = {
        "MDF (18mm)": [
            _chapa(1, "MDF (18mm)", 1_000_000.0, 3, sobras_qtd=1),
            _chapa(2, "MDF (18mm)", 1_200_000.0, 4, sobras_qtd=1),
        ],
    }
    nao_alocadas = [_peca("Sobra avulsa", 500.0, 500.0)]
    resumo = resumo_aproveitamento(sheets, pecas_nao_alocadas=nao_alocadas)

    assert resumo.total_chapas == 2
    assert resumo.total_pecas == 7
    assert resumo.pecas_nao_alocadas == 1
    assert resumo.total_sobras == 2
    assert resumo.area_sobras_mm2 == 2 * 300.0 * 300.0
    assert resumo.area_nao_alocada_mm2 == 500.0 * 500.0
    assert 0.0 <= resumo.aproveitamento_geral_pct <= 100.0


def test_resumo_vazio_retorna_zeros():
    resumo = resumo_aproveitamento({})
    assert resumo.total_chapas == 0
    assert resumo.total_pecas == 0
    assert resumo.aproveitamento_geral_pct == 0.0
    assert resumo.total_sobras == 0
    assert resumo.metros_fita_total == 0.0
    assert resumo.pecas_nao_alocadas == 0
    assert resumo.por_material == {}


def test_resumo_tipos_de_retorno():
    sheets = {"Madeira (25mm)": [_chapa(1, "Madeira (25mm)", 500_000.0, 1)]}
    resumo = resumo_aproveitamento(sheets)
    assert isinstance(resumo, ResumoAproveitamento)
    assert isinstance(resumo.por_material["Madeira (25mm)"].aproveitamento_pct, float)


def test_optimize_exposes_nao_alocadas():
    """Peças maiores que a chapa bruta não são descartadas silenciosamente."""
    cfg = SheetConfig(comprimento=500.0, largura=500.0, refilo=0.0, espessura_corte=0.0)
    opt = GuillotineOptimizer(cfg)
    resultado = opt.optimize([{"nome": "Gigante", "comprimento": 900.0,
                               "largura": 900.0, "espessura": 18.0,
                               "material": "MDF", "quantidade": 1}])
    assert len(opt.pecas_nao_alocadas) == 1
    assert opt.pecas_nao_alocadas[0].nome == "Gigante"
    # Nenhuma chapa gerada para a peça que não cabe
    assert all(len(c.pecas) == 0 for c in resultado["MDF (18mm)"])
