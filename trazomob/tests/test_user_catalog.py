# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Meus Módulos — catálogo pessoal do usuário (Feature 5).

Cobre a persistência dos módulos em ``user_modules`` (preferências JSON) e a
mesclagem com o catálogo estático feita por ``domain.catalog``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from trazomob.domain import catalog, preferences
from trazomob.domain.preferences import TrazoMobPreferencesManager


@pytest.fixture()
def isolated_prefs(tmp_path, monkeypatch):
    """Redireciona o arquivo de preferências para tmp_path e zera o singleton."""
    prefs_file = tmp_path / "trazomob_preferences.json"
    monkeypatch.setattr(preferences, "get_preferences_file_path", lambda: prefs_file)
    monkeypatch.setattr(TrazoMobPreferencesManager, "_instance", None)
    manager = TrazoMobPreferencesManager.get_instance()
    yield manager, prefs_file
    monkeypatch.setattr(TrazoMobPreferencesManager, "_instance", None)


def _modulo(id_: str = "meu-balcao", nome: str = "Meu Balcão") -> dict:
    return {
        "id": id_,
        "nome": nome,
        "desc": "Módulo salvo pelo usuário",
        "largura": 900,
        "altura": 720,
        "profundidade": 560,
        "has_portas": True,
        "num_portas": 2,
    }


def test_default_user_modules_vazio(isolated_prefs):
    manager, _ = isolated_prefs
    assert manager.get_user_modules() == []


def test_add_get_remove_user_module(isolated_prefs):
    manager, _ = isolated_prefs
    assert manager.add_user_module(_modulo()) is True

    mods = manager.get_user_modules()
    assert len(mods) == 1
    assert mods[0]["id"] == "meu-balcao"
    assert mods[0]["nome"] == "Meu Balcão"

    assert manager.remove_user_module("meu-balcao") is True
    assert manager.get_user_modules() == []


def test_remove_inexistente_retorna_false(isolated_prefs):
    manager, _ = isolated_prefs
    assert manager.remove_user_module("nao-existe") is False


def test_add_mesmo_id_atualiza_sem_duplicar(isolated_prefs):
    manager, _ = isolated_prefs
    manager.add_user_module(_modulo(nome="Versão 1"))
    manager.add_user_module(_modulo(nome="Versão 2"))

    mods = manager.get_user_modules()
    assert len(mods) == 1
    assert mods[0]["nome"] == "Versão 2"


def test_persistencia_em_arquivo_json(isolated_prefs):
    manager, prefs_file = isolated_prefs
    manager.add_user_module(_modulo())

    assert prefs_file.exists()
    raw = json.loads(prefs_file.read_text(encoding="utf-8"))
    assert isinstance(raw.get("user_modules"), list)
    assert raw["user_modules"][0]["id"] == "meu-balcao"

    # Uma instância nova relê do mesmo arquivo
    TrazoMobPreferencesManager._instance = None
    novo = TrazoMobPreferencesManager.get_instance()
    assert novo.get_user_modules()[0]["nome"] == "Meu Balcão"


def test_get_user_modules_retorna_copia_defensiva(isolated_prefs):
    manager, _ = isolated_prefs
    manager.add_user_module(_modulo())
    copia = manager.get_user_modules()
    copia[0]["nome"] = "Alterado fora"
    assert manager.get_user_modules()[0]["nome"] == "Meu Balcão"


def test_iter_modulos_todos_marca_origem(isolated_prefs):
    manager, _ = isolated_prefs
    manager.add_user_module(_modulo())

    todos = list(catalog.iter_modulos_todos())
    estaticos = [m for m in todos if not m["usuario"]]
    usuario = [m for m in todos if m["usuario"]]

    assert len(estaticos) > 0
    assert len(usuario) == 1
    assert usuario[0]["categoria"] == catalog.USER_MODULE_CATEGORY
    assert usuario[0]["id"] == "meu-balcao"
    # Todo item estático carrega a categoria real do catálogo
    assert all(m["categoria"] in catalog.MODULE_CATALOG for m in estaticos)


def test_buscar_modulo_estatico_e_usuario(isolated_prefs):
    manager, _ = isolated_prefs
    manager.add_user_module(_modulo())

    estatico = catalog.buscar_modulo("balcao")
    assert estatico is not None
    assert estatico["usuario"] is False

    usuario = catalog.buscar_modulo("meu-balcao")
    assert usuario is not None
    assert usuario["usuario"] is True
    assert usuario["categoria"] == catalog.USER_MODULE_CATEGORY

    assert catalog.buscar_modulo("inexistente-xyz") is None
    assert catalog.buscar_modulo("meu-balcao", incluir_usuario=False) is None


def test_modulos_usuario_lidos_das_preferencias(isolated_prefs):
    manager, _ = isolated_prefs
    manager.add_user_module(_modulo(id_="a"))
    manager.add_user_module(_modulo(id_="b"))

    ids = [m["id"] for m in catalog.modulos_usuario()]
    assert ids == ["a", "b"]


def test_build_user_module_aplica_parametros_e_id_unico():
    base = dict(catalog.MODULE_CATALOG["Cozinha — Inferiores"][0])
    params = {
        "largura": 1000.0,
        "altura": 760.0,
        "profundidade": 600.0,
        "rodape": 120.0,
        "num_prateleiras": 2,
        "material": "MDF Branco 18mm",
    }

    novo = catalog.build_user_module(base, params, "Meu Balcão Grande", {"user_meu_balcao_grande"})
    assert novo["id"] == "user_meu_balcao_grande_2"
    assert novo["nome"] == "Meu Balcão Grande"
    assert novo["largura"] == 1000
    assert novo["altura"] == 760
    assert novo["profundidade"] == 600
    assert novo["rodape"] == 120
    assert novo["num_prateleiras"] == 2
    assert novo["material"] == "MDF Branco 18mm"
    assert novo["usuario"] is True
    assert novo["categoria"] == catalog.USER_MODULE_CATEGORY
    # Flags do catálogo de origem são preservadas
    assert novo["has_portas"] == base["has_portas"]


def test_build_user_module_sem_nome_usa_nome_base():
    base = {"id": "balcao", "nome": "Balcão com Portas", "largura": 800}
    novo = catalog.build_user_module(base, {}, "")
    assert novo["nome"] == "Balcão com Portas"
    assert novo["id"] == "user_balcao_com_portas"


def test_sidebar_expoe_botao_salvar_em_meus_modulos():
    """A barra lateral oferece o botão e o handler de salvar em Meus Módulos."""
    from PySide6.QtWidgets import QApplication

    from trazomob.ui.sidebar_panel import TrazoMobSidebarPanel

    _app = QApplication.instance() or QApplication([])
    panel = TrazoMobSidebarPanel(None)
    panel._ensure_form_built()
    assert hasattr(panel, "btn_save_user_module")
    assert panel.btn_save_user_module.text()
    assert hasattr(panel, "_save_current_to_user_modules")
