# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez and IngeTrazo contributors.
"""Choosing one of the user's components arms the placement tool with the
model at the size and orientation the ficha recorded — the same path the
tray and the ribbon use."""
from __future__ import annotations

import math

from PySide6.QtWidgets import QApplication

from core import user_library
from views import component_loader

CUBE = """v 0 0 0
v 1 0 0
v 1 1 0
v 0 1 0
v 0 0 1
v 1 0 1
v 1 1 1
v 0 1 1
f 1 2 3 4
f 5 6 7 8
f 1 2 6 5
f 2 3 7 6
f 3 4 8 7
f 4 1 5 8
"""


def test_insert_user_component_arms_the_placement_tool(tmp_path, monkeypatch):
    QApplication.instance() or QApplication([])
    monkeypatch.setenv("INGETRAZO_COMPONENTS", str(tmp_path / "biblioteca"))
    model = tmp_path / "geladeira.obj"
    model.write_text(CUBE, encoding="utf-8")

    entry = user_library.register(
        model, nombre="Geladeira", tipo="Geladeira", marca="Brastemp",
        cm=[70, 65, 180],
        matrix=component_loader.matrix_for("m"))

    from views.main_window import MainWindow
    win = MainWindow()
    try:
        win.insert_user_component(entry)
        tool = win.viewport.active_tool
        from tools.place_group import PlaceGroupTool
        assert isinstance(tool, PlaceGroupTool), tool

        width, depth, height = component_loader.size_cm(tool._group)
        assert math.isclose(width, 70.0, abs_tol=1e-6)
        assert math.isclose(depth, 65.0, abs_tol=1e-6)
        assert math.isclose(height, 180.0, abs_tol=1e-6)
        # Its base rests on the cursor's plane, not sunk half-way.
        lo, _hi = component_loader.bounds(tool._group)
        assert math.isclose(lo[2], 0.0, abs_tol=1e-6)
    finally:
        win._saved_version = win.viewport.scene.version
        win.close()
