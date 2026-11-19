# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Regressão do Balcão Porta-Tempero.

O registro de módulos repassa os parâmetros de fundo (``tipo_fundo``,
``esp_fundo_mm`` etc.) para todos os construtores de caixa inferior. O
``build_porta_tempero`` não aceitava esses argumentos e a inserção pela
galeria falhava com ``TypeError: unexpected keyword argument 'tipo_fundo'``.
"""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from trazomob.builders.cabinet import CabinetBuilder
from trazomob.domain.catalog import MODULE_CATALOG
from trazomob.domain.module_geometry import build_default_module_params


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _porta_tempero_params(tipo_fundo: str) -> dict:
    cat = next(
        m for c in MODULE_CATALOG.values() for m in c
        if m.get("id") == "porta_tempero")
    params = build_default_module_params(cat)
    params["tipo_fundo"] = tipo_fundo
    return params


@pytest.mark.parametrize("tipo_fundo", ["rasgo", "sem_fundo"])
def test_insercao_pela_galeria_aceita_parametros_de_fundo(qapp, tipo_fundo):
    mod = CabinetBuilder.build_module_group(
        _porta_tempero_params(tipo_fundo), offset=(0.0, 0.0, 0.0))

    nomes = [c.name for c in mod.children]
    assert any("Frente" in n for n in nomes)
    tem_fundo = any("Fundo" in n for n in nomes)
    assert tem_fundo is (tipo_fundo != "sem_fundo")


def test_porta_tempero_mdf_vs_aramado(qapp):
    from trazomob.domain.hardware import infer_module_hardware

    # 1. Modo 100% MDF
    params_mdf = _porta_tempero_params("rasgo")
    params_mdf["tipo_estrutura_tempero"] = "mdf"
    mod_mdf = CabinetBuilder.build_module_group(params_mdf)
    nomes_mdf = [c.name for c in mod_mdf.children]

    assert any("Base Gaveta Inferior" in n for n in nomes_mdf)
    assert any("Traseira Torre" in n for n in nomes_mdf)
    assert any("Base Superior" in n for n in nomes_mdf)

    hw_mdf = infer_module_hardware(params_mdf)
    hw_keys_mdf = [h.key for h in hw_mdf]
    assert "corredica_50" in hw_keys_mdf or "corredica_40" in hw_keys_mdf
    assert "kit_porta_tempero_aramado" not in hw_keys_mdf

    # 2. Modo Kit Aramado
    params_aramado = _porta_tempero_params("rasgo")
    params_aramado["tipo_estrutura_tempero"] = "aramado"
    params_aramado["cor_aramado"] = "preto"
    mod_aramado = CabinetBuilder.build_module_group(params_aramado)
    nomes_aramado = [c.name for c in mod_aramado.children]

    # No aramado não devem existir chapas de MDF para a torre/bandejas da gaveta
    assert not any("Base Gaveta Inferior" in n for n in nomes_aramado)
    assert not any("Traseira Torre" in n for n in nomes_aramado)

    # Mas deve existir o grupo 3D de ferragem do aramado
    assert any("Kit Porta-Tempero Aramado" in n for n in nomes_aramado)

    hw_aramado = infer_module_hardware(params_aramado)
    hw_keys_aramado = [h.key for h in hw_aramado]
    assert "kit_porta_tempero_aramado" in hw_keys_aramado
    assert "corredica_50" not in hw_keys_aramado
    assert "corredica_40" not in hw_keys_aramado
