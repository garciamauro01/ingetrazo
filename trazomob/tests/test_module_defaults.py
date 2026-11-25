# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""As preferências do usuário voltam a valer ao inserir um módulo.

Regressão de ``8c44525``: ao extrair ``build_default_module_params`` para
``module_geometry.py``, o corpo passou a ler só o catálogo e as medidas
padrão salvas ("Salvar como Medidas Padrão") deixaram de ser aplicadas.
"""
from __future__ import annotations

import copy

import pytest

from trazomob.domain import module_geometry
from trazomob.domain.preferences import DEFAULT_PREFERENCES, TrazoMobPreferencesManager


@pytest.fixture()
def prefs():
    manager = TrazoMobPreferencesManager.get_instance()
    original = copy.deepcopy(manager._data)
    manager._data["global"] = copy.deepcopy(DEFAULT_PREFERENCES["global"])
    manager._data["module_defaults"] = {}
    try:
        yield manager
    finally:
        manager._data = original


def _catalogo(**extra):
    data = {"id": "balcao", "largura": 800.0, "altura": 720.0,
            "profundidade": 550.0, "has_fundo": True}
    data.update(extra)
    return data


def test_medidas_salvas_da_categoria_substituem_o_catalogo(prefs):
    prefs.set_module_defaults("inferior", {
        "altura": 800.0, "profundidade": 600.0, "rodape": 50.0})

    params = module_geometry.build_default_module_params(_catalogo())

    assert params["altura"] == pytest.approx(800.0)
    assert params["profundidade"] == pytest.approx(600.0)
    assert params["rodape"] == pytest.approx(50.0)


def test_medida_salva_do_tipo_vence_a_da_categoria(prefs):
    prefs.set_module_defaults("inferior", {"altura": 800.0})
    prefs.set_module_defaults("balcao", {"altura": 850.0})

    params = module_geometry.build_default_module_params(_catalogo())

    assert params["altura"] == pytest.approx(850.0)


def test_sem_preferencia_salva_o_catalogo_e_preservado(prefs):
    params = module_geometry.build_default_module_params(
        _catalogo(altura=900.0, profundidade=580.0))

    assert params["altura"] == pytest.approx(900.0)
    assert params["profundidade"] == pytest.approx(580.0)


def test_padroes_globais_de_marcenaria_sao_aplicados(prefs):
    prefs.set_global("espessura_caixa_mm", 18.0)
    prefs.set_global("material_caixa", "MDF Louro Freijó")
    prefs.set_global("puxador_tipo", "gola")
    prefs.set_global("puxador_cor", "preto")
    prefs.set_global("tipo_fundo", "rasgo")
    prefs.set_global("esp_fundo_mm", 8.0)

    params = module_geometry.build_default_module_params(_catalogo())

    assert params["espessura"] == pytest.approx(18.0)
    assert params["material"] == "MDF Louro Freijó 18mm"
    assert params["puxador_tipo"] == "gola"
    assert params["puxador_cor"] == "preto"
    assert params["tipo_fundo"] == "rasgo"
    assert params["esp_fundo"] == pytest.approx(8.0)


def test_travessas_de_cozinha_inferior_seguem_as_preferencias(prefs):
    prefs.set_global("travessa_frontal_em_pe", True)
    prefs.set_global("larg_travessa_frontal_mm", 90.0)

    params = module_geometry.build_default_module_params(_catalogo())

    assert params["travessa_frontal_em_pe"] is True
    assert params["larg_travessa_frontal_mm"] == pytest.approx(90.0)


def test_esquadrias_preservam_as_medidas_do_catalogo(prefs):
    prefs.set_module_defaults("inferior", {"altura": 300.0})
    prefs.set_global("espessura_caixa_mm", 18.0)

    params = module_geometry.build_default_module_params({
        "id": "porta_giro", "tipo": "esquadria", "largura": 800.0,
        "altura": 2100.0, "profundidade": 150.0})

    assert params["altura"] == pytest.approx(2100.0)
    assert params["profundidade"] == pytest.approx(150.0)
    assert params["rodape"] == pytest.approx(0.0)


def test_balcao_canto_l_nao_herda_profundidade_da_categoria(prefs):
    prefs.set_module_defaults("inferior", {
        "largura": 800.0, "profundidade": 550.0})

    params = module_geometry.build_default_module_params({
        "id": "balcao_canto_l", "largura": 1000.0, "altura": 720.0,
        "profundidade": 1000.0, "num_portas": 2})

    assert params["largura"] == pytest.approx(1000.0)
    assert params["profundidade"] == pytest.approx(1000.0)


def test_bancada_usa_medidas_padrao_da_categoria(prefs):
    prefs.set_module_defaults("bancada", {
        "esp_pedra": 30.0, "altura_saia": 60.0, "altura_frontao": 120.0})

    params = module_geometry.build_default_module_params({
        "id": "bancada_granito", "largura": 2000.0, "altura": 40.0,
        "profundidade": 600.0})

    assert params["esp_pedra"] == pytest.approx(30.0)
    assert params["altura_saia"] == pytest.approx(60.0)
    assert params["altura_frontao"] == pytest.approx(120.0)
