# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Manual de Montagem (Feature 1).

Valida a geração do HTML do manual a partir da cutlist: agrupamento por módulo,
ferragens consolidadas por módulo, medidas de corte/final, fita de borda,
usinagens (operacoes), ambiente/pavimento e saída estável entre execuções.
"""
from __future__ import annotations

import os
import tempfile

from trazomob.production.assembly_manual import (
    generate_assembly_manual_html,
    save_assembly_manual_html,
)


def _peca(nome: str, modulo_key: int | None, comp: float = 700.0, larg: float = 400.0,
          esp: float = 18.0, mat: str = "MDF Branco", operacoes=None,
          ambiente: str = "Cozinha", pavimento: str = "Térreo",
          fita_c1: bool = True, fita_l1: bool = True) -> dict:
    return {
        "id": 1,
        "nome": nome,
        "comprimento": comp,
        "largura": larg,
        "espessura": esp,
        "comprimento_corte": comp - 1.0,
        "largura_corte": larg - 1.0,
        "material": mat,
        "fita_c1": fita_c1,
        "fita_c2": False,
        "fita_l1": fita_l1,
        "fita_l2": False,
        "espessura_fita": 0.45,
        "operacoes": operacoes or [],
        "quantidade": 2,
        "_module_key": modulo_key,
        "module_hardware": [
            {"key": "dobrada35", "tipo": "dobradiça", "nome": "Dobradiça 35mm",
             "quantidade": 2, "preco_unitario": 5.50},
        ] if modulo_key is not None else [],
        "ambiente": ambiente,
        "pavimento": pavimento,
    }


def _modulo_pecas() -> list[dict]:
    return [
        _peca("Lateral Esq", 1, ambiente="Cozinha", pavimento="Térreo"),
        _peca("Lateral Dir", 1, ambiente="Cozinha", pavimento="Térreo"),
        _peca("Prateleira", 1, comp=650.0, larg=340.0),
        _peca("Porta", 1, comp=700.0, larg=400.0,
              operacoes=[{"tipo": "furo", "face": "traseira", "x": 21.5, "y": 100.0,
                          "diametro": 35.0, "descricao": "Caneco"}]),
    ]


def test_manual_html_contem_estrutura_esperada():
    parts = _modulo_pecas()
    html = generate_assembly_manual_html(parts, project_name="Minha Cozinha")
    assert "<!DOCTYPE html>" in html
    assert "Manual de Montagem" in html
    assert "Minha Cozinha" in html
    assert "Módulo 1" in html
    assert "Lateral Esq" in html
    assert "Lateral Dir" in html
    assert "Prateleira" in html
    assert "Porta" in html
    assert "Cozinha" in html
    assert "Térreo" in html


def test_manual_agrupa_por_modulo_e_conta_pecas():
    parts = _modulo_pecas()
    html = generate_assembly_manual_html(parts)
    # 4 peças distintas no mesmo módulo (chave 1) → um módulo com 4 tipos
    assert "Módulo 1" in html
    assert "4 tipo(s) de peça" in html


def test_manual_ferragens_por_modulo():
    parts = _modulo_pecas()
    html = generate_assembly_manual_html(parts)
    assert "Dobradiça 35mm" in html
    assert "dobrada35" in html


def test_manual_operacoes_viram_instrucoes():
    parts = _modulo_pecas()
    html = generate_assembly_manual_html(parts)
    assert "Fure a face traseira" in html
    assert "35 mm" in html
    assert "Caneco" in html


def test_manual_medidas_corte_e_final():
    parts = [_peca("Peça Teste", None)]
    html = generate_assembly_manual_html(parts)
    assert "700 x 400 x 18" in html
    assert "699 x 399" in html
    assert "Fita C1" in html
    assert "0.45 mm" in html


def test_manual_peças_avulsas_sem_modulo():
    parts = [_peca("Avulsa", None)]
    html = generate_assembly_manual_html(parts)
    assert "Peças Avulsas" in html
    assert "Módulo 1" not in html


def test_manual_estavel_entre_execucoes():
    parts = _modulo_pecas()
    a = generate_assembly_manual_html(parts)
    b = generate_assembly_manual_html(parts)
    assert a == b


def test_save_assembly_manual_html_grava_arquivo():
    parts = _modulo_pecas()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "manual.html")
        assert save_assembly_manual_html(parts, path, project_name="Projeto X") is True
        assert os.path.exists(path)
        content = open(path, encoding="utf-8").read()
        assert "Projeto X" in content
        assert "<!DOCTYPE html>" in content


def test_save_assembly_manual_html_sem_partes_retorna_true_mesmo_vazio():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "vazio.html")
        assert save_assembly_manual_html([], path) is True
