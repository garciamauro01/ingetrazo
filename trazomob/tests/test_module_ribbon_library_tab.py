# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""A aba Decoração do ribbon é o navegador da biblioteca do usuário."""
from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (QListView, QListWidget, QMenu, QPushButton,
                               QTabWidget, QWidget)

from core import user_library
from trazomob.integrations import platform as host
from trazomob.ui import module_ribbon
from trazomob.ui.module_ribbon import TrazoMobModuleRibbonBar


class FakeWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.inserted: list[dict] = []

    def insert_user_component(self, entry: dict) -> None:
        self.inserted.append(entry)


@pytest.fixture
def fake_library(monkeypatch, tmp_path):
    png = tmp_path / "preview.png"
    image = QImage(8, 8, QImage.Format_ARGB32)
    image.fill(Qt.green)
    assert image.save(str(png))

    data = [
        {"id": "geladeira", "nombre": "Geladeira", "categoria": "Cozinha",
         "marca": "Brastemp", "modelo": "BRM54", "cm": [70, 70, 180]},
        {"id": "maquina", "nombre": "Máquina", "categoria": "Cozinha",
         "marca": "Electrolux", "modelo": "LEB12", "cm": [60, 60, 85]},
        {"id": "cortina", "nombre": "Cortina", "categoria": "",
         "marca": "", "modelo": "", "cm": [200, 5, 250]},
    ]
    state = {"revision": 1, "entries": list(data)}
    monkeypatch.setattr(user_library, "index",
                        lambda refresh=False: list(state["entries"]))
    monkeypatch.setattr(user_library, "revision", lambda: state["revision"])
    monkeypatch.setattr(user_library, "thumbnail", lambda entry: png)
    monkeypatch.setattr(user_library, "missing", lambda entry: False)
    return state


@pytest.fixture
def ribbon(qapp, fake_library):
    win = FakeWindow()
    viewport = SimpleNamespace(scene=None, window=lambda: win)
    bar = TrazoMobModuleRibbonBar(win, viewport, None)
    bar._populate_decoration_tab()
    yield bar, win, fake_library
    timer = getattr(bar, "_library_thumb_timer", None)
    if timer is not None:
        timer.stop()


def _category_tabs(ribbon):
    return ribbon._decor_tabs


def test_clicking_decoration_tab_creates_library_browser(qapp, fake_library):
    win = FakeWindow()
    viewport = SimpleNamespace(scene=None, window=lambda: win)
    bar = TrazoMobModuleRibbonBar(win, viewport, None)
    try:
        assert not hasattr(bar, "_library_host")
        bar.tabs.setCurrentIndex(bar._decor_tab_idx)
        assert hasattr(bar, "_library_host")
        tabs = bar._decor_tabs
        assert [tabs.tabText(i) for i in range(tabs.count())] == [
            "Todas", "Cozinha", "Sem categoria"]
    finally:
        timer = getattr(bar, "_library_thumb_timer", None)
        if timer is not None:
            timer.stop()


def test_categories_and_brands_come_from_user_library(ribbon):
    bar, _win, _state = ribbon
    tabs = _category_tabs(bar)
    assert isinstance(tabs, QTabWidget)
    labels = [tabs.tabText(i) for i in range(tabs.count())]
    assert "Todas" in labels
    assert "Cozinha" in labels
    assert "Sem categoria" in labels

    cozinha_index = labels.index("Cozinha")
    brands = tabs.widget(cozinha_index)
    assert isinstance(brands, QTabWidget)
    assert brands.tabPosition() == QTabWidget.South
    brand_labels = [brands.tabText(i) for i in range(brands.count())]
    assert "Todas" in brand_labels
    assert "Brastemp" in brand_labels
    assert "Electrolux" in brand_labels
    assert "Sem marca" not in brand_labels

    no_cat = tabs.widget(labels.index("Sem categoria"))
    no_cat_brands = [no_cat.tabText(i) for i in range(no_cat.count())]
    assert "Sem marca" in no_cat_brands


def test_grid_uses_user_library_thumbnails_and_entries(ribbon):
    bar, _win, _state = ribbon
    tabs = _category_tabs(bar)
    grid = tabs.widget(0).currentWidget().findChild(QListWidget)
    assert grid is not None
    assert grid.count() == 3
    assert [grid.item(i).text() for i in range(grid.count())] == [
        "Geladeira", "Máquina", "Cortina"]
    assert not any(grid.item(i).icon().isNull() for i in range(grid.count()))
    assert grid.flow() == QListView.LeftToRight
    assert grid.isWrapping() is False
    assert grid.verticalScrollBarPolicy() == Qt.ScrollBarAlwaysOff


def test_double_click_inserts_user_component(ribbon, monkeypatch):
    bar, win, _state = ribbon
    captured = []
    monkeypatch.setattr(host, "insert_user_component",
                        lambda window, entry: captured.append((window, entry)))
    tabs = _category_tabs(bar)
    grid = tabs.widget(0).currentWidget().findChild(QListWidget)
    grid.setCurrentRow(1)
    grid.itemDoubleClicked.emit(grid.item(1))
    assert captured == [(win, {
        "id": "maquina", "nombre": "Máquina", "categoria": "Cozinha",
        "marca": "Electrolux", "modelo": "LEB12", "cm": [60, 60, 85]})]
    assert win.inserted == []


def test_revision_change_rebuilds_browser(ribbon, fake_library):
    bar, _win, state = ribbon
    tabs = _category_tabs(bar)
    assert "Banheiro" not in [tabs.tabText(i) for i in range(tabs.count())]
    state["entries"].append({
        "id": "pia", "nombre": "Pia", "categoria": "Banheiro",
        "marca": "Deca", "cm": [60, 45, 20]})
    state["revision"] = 2
    bar.refresh_user_library()
    tabs = _category_tabs(bar)
    labels = [tabs.tabText(i) for i in range(tabs.count())]
    assert "Banheiro" in labels
    brands = tabs.widget(labels.index("Banheiro"))
    assert "Deca" in [brands.tabText(i) for i in range(brands.count())]


def test_transfer_menu_offers_export_and_import(ribbon):
    bar, _win, _state = ribbon
    menus = [button.menu() for button in bar.findChildren(QPushButton)
             if isinstance(button.menu(), QMenu)]
    assert menus
    actions = [action.text() for menu in menus for action in menu.actions()]
    assert "Export library…" in actions
    assert "Import library…" in actions


def test_ribbon_has_no_native_library_path():
    source = inspect.getsource(module_ribbon)
    assert "from core import library" not in source
    assert "library_model" not in source
    assert "open_component_library" not in source
    assert not hasattr(host, "open_component_library")
    assert "open_library" not in host.capabilities(
        SimpleNamespace(_on_open_library=lambda: None))
