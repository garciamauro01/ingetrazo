# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes do modelo de dados de ferragens (domain/hardware.py)."""

from __future__ import annotations

from trazomob.domain.hardware import (
    HardwareItem,
    HARDWARE_CATALOG,
    consolidate_hardware,
    deserialize_hardware,
    hardware_total_preco,
    infer_module_hardware,
    serialize_hardware,
)


def test_catalogo_tem_ferragens_esperadas():
    assert "dobradica_35mm" in HARDWARE_CATALOG
    assert "corredica_40" in HARDWARE_CATALOG
    assert "trilho_correr" in HARDWARE_CATALOG
    assert HARDWARE_CATALOG["dobradica_35mm"]["tipo"] == "dobradica"


def test_serializa_e_deserializa():
    item = HardwareItem(
        "dobradica_35mm", "dobradica", "Dobradiça 35mm (caneco)", 4, 3.50,
        posicao={"por_porta": 2, "portas": 2}, visivel_3d=True,
    )
    d = item.to_dict()
    assert d["key"] == "dobradica_35mm"
    assert d["quantidade"] == 4
    assert d["preco_unitario"] == 3.5

    restaurado = HardwareItem.from_dict(d)
    assert restaurado.key == item.key
    assert restaurado.quantidade == item.quantidade
    assert restaurado.visivel_3d is True

    lista = [item]
    assert deserialize_hardware(serialize_hardware(lista)) == lista


def test_deserializa_lista_vazia_e_dados_invalidos():
    assert deserialize_hardware(None) == []
    assert deserialize_hardware([]) == []
    assert deserialize_hardware([{"key": ""}, {"não": "tem key"}]) == []


def test_inferencia_balcao_com_portas():
    params = {
        "tipo": "balcao",
        "num_portas": 2,
        "num_gavetas": 0,
        "altura": 720,
        "profundidade": 550,
        "puxador_tipo": "alca",
        "dispositivo_fixacao": "minifix_cavilha",
    }
    hw = infer_module_hardware(params)
    chaves = {it.key for it in hw}
    assert "dobradica_35mm" in chaves
    assert "calco_dobradica" in chaves
    assert "puxador_ponto" in chaves
    assert "minifix_kit" in chaves
    assert "pes_nivelador" not in chaves
    # 2 portas * 2 dobradiças (altura < 900)
    dobra = next(it for it in hw if it.key == "dobradica_35mm")
    assert dobra.quantidade == 4
    # 2 puxadores (1 por porta)
    pux = next(it for it in hw if it.key == "puxador_ponto")
    assert pux.quantidade == 2
    # O kit minifix já inclui a cavilha: não deve contar pino avulso em dobro
    assert "pino_cavilha_8" not in chaves


def test_inferencia_porta_alta_usa_mais_dobradiças():
    params_baixa = {"tipo": "balcao", "num_portas": 1, "num_gavetas": 0,
                    "altura": 700, "profundidade": 550,
                    "puxador_tipo": "sem_puxador", "dispositivo_fixacao": "cavilha"}
    params_alta = dict(params_baixa, altura=2200, num_portas=1)
    n_baixa = next(it for it in infer_module_hardware(params_baixa)
                   if it.key == "dobradica_35mm").quantidade
    n_alta = next(it for it in infer_module_hardware(params_alta)
                  if it.key == "dobradica_35mm").quantidade
    assert n_baixa == 2
    assert n_alta == 5


def test_inferencia_gaveta_usa_corredica():
    params = {"tipo": "gaveteiro", "num_portas": 0, "num_gavetas": 3,
              "num_prateleiras": 0, "altura": 720, "profundidade": 550,
              "puxador_tipo": "perfil", "dispositivo_fixacao": "minifix_cavilha"}
    hw = infer_module_hardware(params)
    chaves = {it.key for it in hw}
    assert "corredica_50" in chaves  # profundidade > 500
    assert "puxador_perfil" in chaves
    corredica = next(it for it in hw if it.key == "corredica_50")
    assert corredica.quantidade == 3
    pux = next(it for it in hw if it.key == "puxador_perfil")
    assert pux.quantidade == 3


def test_inferencia_gaveta_profunda_baixa_usa_corredica_40():
    params = {"tipo": "gaveteiro", "num_portas": 0, "num_gavetas": 1,
              "num_prateleiras": 0, "altura": 720, "profundidade": 450,
              "puxador_tipo": "sem_puxador", "dispositivo_fixacao": "cavilha"}
    hw = infer_module_hardware(params)
    chaves = {it.key for it in hw}
    assert "corredica_40" in chaves
    assert "corredica_50" not in chaves


def test_inferencia_porta_correr_usa_trilho_e_roldanas():
    params = {"tipo": "armario_portas_correr", "num_portas": 3, "num_gavetas": 0,
              "num_prateleiras": 0, "altura": 2200, "profundidade": 600,
              "puxador_tipo": "sem_puxador", "dispositivo_fixacao": "cavilha"}
    hw = infer_module_hardware(params)
    chaves = {it.key for it in hw}
    assert "trilho_correr" in chaves
    assert "roldana_correr" in chaves
    trilho = next(it for it in hw if it.key == "trilho_correr")
    assert trilho.quantidade == 3
    roldana = next(it for it in hw if it.key == "roldana_correr")
    assert roldana.quantidade == 6  # 2 por porta


def test_inferencia_sem_portas_nao_gera_dobradiça():
    params = {"tipo": "prateleira_avulsa", "num_portas": 0, "num_gavetas": 0,
              "num_prateleiras": 2, "altura": 200, "profundidade": 300,
              "puxador_tipo": "sem_puxador", "dispositivo_fixacao": "cavilha"}
    hw = infer_module_hardware(params)
    chaves = {it.key for it in hw}
    assert "dobradica_35mm" not in chaves
    assert "pino_cavilha_8" in chaves  # prateleiras geram pinos


def test_consolidate_agrupa_e_dedupe_por_modulo():
    hw_mod1 = infer_module_hardware({
        "tipo": "balcao", "num_portas": 2, "num_gavetas": 0, "altura": 720,
        "profundidade": 550, "puxador_tipo": "alca",
        "dispositivo_fixacao": "minifix_cavilha",
    })
    hw_mod2 = infer_module_hardware({
        "tipo": "gaveteiro", "num_portas": 0, "num_gavetas": 2, "num_prateleiras": 0,
        "altura": 720, "profundidade": 550, "puxador_tipo": "alca",
        "dispositivo_fixacao": "minifix_cavilha",
    })
    consolidado = consolidate_hardware([("modA", hw_mod1), ("modB", hw_mod2)])
    # minifix_kit aparece nos dois módulos (8 + 8)
    assert consolidado["minifix_kit"]["quantidade"] == 16
    assert consolidado["dobradica_35mm"]["quantidade"] == 4
    # gaveteiro com profundidade 550 mm -> corredica_50
    assert consolidado["corredica_50"]["quantidade"] == 2
    total = hardware_total_preco(consolidado)
    assert total > 0


def test_consolidate_ignora_quantidade_zero():
    itens = [
        HardwareItem("dobradica_35mm", "dobradica", "D", 0, 3.50),
        HardwareItem("puxador_ponto", "puxador", "P", 2, 8.00),
    ]
    cons = consolidate_hardware([("m", itens)])
    assert "dobradica_35mm" not in cons
    assert cons["puxador_ponto"]["quantidade"] == 2


def test_hardware_item_defaults():
    it = HardwareItem("x", "outro", "X")
    assert it.quantidade == 1
    assert it.preco_unitario == 0.0
    assert it.visivel_3d is True
    assert it.posicao is None
