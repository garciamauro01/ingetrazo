# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes do mapeamento de presets procedurais de render por material."""
from __future__ import annotations

import pytest
from PySide6.QtGui import QVector3D
from PySide6.QtWidgets import QApplication

from core.group import Group
from core.mesh import Mesh
from trazomob.domain.render_materials import (
    RENDER_PRESET_IDS,
    extract_group_material_slots,
    get_group_render_materials,
    set_group_render_materials,
)
from trazomob.ui.render_materials_dialog import RenderMaterialsDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _make_face_mesh(color=None, tex_path=None):
    m = Mesh()
    f = m.add_face([
        QVector3D(0, 0, 0),
        QVector3D(1, 0, 0),
        QVector3D(1, 1, 0),
        QVector3D(0, 1, 0),
    ])
    if color is not None:
        f.attrs["color"] = color
    if tex_path is not None:
        f.attrs["texture"] = {"path": tex_path}
    return m


def test_extract_e_mapeamento_multiplos_materiais(qapp):
    root = Group(Mesh(), name="Lava e Seca")
    g_corpo = Group(_make_face_mesh(color=(0.9, 0.9, 0.9)), name="Corpo")
    g_vidro = Group(_make_face_mesh(color=(0.27, 0.28, 0.33)), name="Visor")
    g_estampa = Group(_make_face_mesh(tex_path="C:/tmp/persa.jpg"), name="Tapete")
    root.children = [g_corpo, g_vidro, g_estampa]

    slots = extract_group_material_slots(root)
    keys = {s["key"] for s in slots}
    assert "mat_90_90_90" in keys
    assert "mat_27_28_33" in keys
    assert "tex:C:/tmp/persa.jpg" in keys

    set_group_render_materials(root, {
        "mat_90_90_90": "aco_escovado",
        "mat_27_28_33": "vidro_fume",
        "tex:C:/tmp/persa.jpg": "carpete_felpudo",
        "mat_default": "original",  # 'original' não precisa ser persistido
    })
    saved = get_group_render_materials(root)
    assert saved == {
        "mat_90_90_90": "aco_escovado",
        "mat_27_28_33": "vidro_fume",
        "tex:C:/tmp/persa.jpg": "carpete_felpudo",
    }

    dlg = RenderMaterialsDialog(root)
    assert len(dlg._combos) == 3
    assert dlg._combos["mat_90_90_90"].currentData() == "aco_escovado"
    assert "branco_esmaltado" in RENDER_PRESET_IDS
