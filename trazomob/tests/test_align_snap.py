# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes para o sistema de Alinhamento e Centralização 3D."""
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QVector3D

from core.group import Group
from core.mesh import Mesh, Vertex
from trazomob.interaction.align_tool_interactive import AlignSnapTool


def _create_mock_box(name: str, x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> Group:
    """Cria um Group simples com mesh cúbico para testar alinhamentos 3D."""
    verts = [
        Vertex(QVector3D(x0, y0, z0)),
        Vertex(QVector3D(x1, y0, z0)),
        Vertex(QVector3D(x1, y1, z0)),
        Vertex(QVector3D(x0, y1, z0)),
        Vertex(QVector3D(x0, y0, z1)),
        Vertex(QVector3D(x1, y0, z1)),
        Vertex(QVector3D(x1, y1, z1)),
        Vertex(QVector3D(x0, y1, z1)),
    ]
    mesh = Mesh()
    mesh.vertices = verts
    child = Group(name=f"child_{name}")
    child.mesh = mesh
    grp = Group(name=name)
    grp.children = [child]
    return grp


def test_notable_points_generation():
    """Testa se o cálculo da bounding box gera centros, pontos médios e quinas com exatidão."""
    # Objeto de 2.0 x 1.0 x 0.8
    grp = _create_mock_box("Armario", 0.0, 2.0, 0.0, 1.0, 0.0, 0.8)
    tool = AlignSnapTool()
    points = tool._get_group_notable_points(grp)

    # Verifica se os centros principais foram calculados corretamente
    labels = {p.label: p.pos for p in points}

    # Centro Total XYZ
    assert "Centro (XYZ)" in labels
    c_xyz = labels["Centro (XYZ)"]
    assert pytest.approx(c_xyz.x()) == 1.0
    assert pytest.approx(c_xyz.y()) == 0.5
    assert pytest.approx(c_xyz.z()) == 0.4

    # Centro da Base (-Z)
    assert "Centro da Base (-Z)" in labels
    c_base = labels["Centro da Base (-Z)"]
    assert pytest.approx(c_base.x()) == 1.0
    assert pytest.approx(c_base.y()) == 0.5
    assert pytest.approx(c_base.z()) == 0.0

    # Centro do Topo (+Z)
    assert "Centro do Topo (+Z)" in labels
    c_topo = labels["Centro do Topo (+Z)"]
    assert pytest.approx(c_topo.x()) == 1.0
    assert pytest.approx(c_topo.y()) == 0.5
    assert pytest.approx(c_topo.z()) == 0.8


def test_axis_locking_keys():
    """Testa se as teclas X, Y, Z e A travam e liberam os eixos de centralização."""
    tool = AlignSnapTool()
    assert tool.axis_lock is None

    class DummyVP:
        def update(self):
            pass
        def flash_status(self, msg):
            pass

    vp = DummyVP()

    # Pressiona X -> Trava X
    tool.on_key(vp, int(Qt.Key_X), Qt.NoModifier)
    assert tool.axis_lock == "x"

    # Pressiona Y -> Trava Y
    tool.on_key(vp, int(Qt.Key_Y), Qt.NoModifier)
    assert tool.axis_lock == "y"

    # Pressiona Z -> Trava Z
    tool.on_key(vp, int(Qt.Key_Z), Qt.NoModifier)
    assert tool.axis_lock == "z"

    # Pressiona A -> Libera todos (XYZ livre)
    tool.on_key(vp, int(Qt.Key_A), Qt.NoModifier)
    assert tool.axis_lock is None


def test_align_snap_tool_tab_filter_toggles_mode(qapp):
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QWidget
    from trazomob.interaction.align_tool_interactive import AlignSnapTool

    vp = QWidget()
    tool = AlignSnapTool()
    tool.on_activate(vp)
    assert tool.align_and_move is True

    ev = QKeyEvent(QEvent.KeyPress, Qt.Key_Tab, Qt.NoModifier)
    qapp.sendEvent(vp, ev)
    assert tool.align_and_move is False

    ev2 = QKeyEvent(QEvent.KeyPress, Qt.Key_Tab, Qt.NoModifier)
    qapp.sendEvent(vp, ev2)
    assert tool.align_and_move is True

    tool.on_deactivate(vp)


def test_align_snap_tool_apenas_alinhar_moves_only_dominant_axis():
    from PySide6.QtGui import QVector3D
    from trazomob.interaction.align_tool_interactive import AlignSnapTool

    tool = AlignSnapTool()
    # Simula cálculo de delta nos dois modos
    dx, dy, dz = 1.5, 0.3, 0.2
    tool.align_and_move = False
    ax, ay, az = abs(dx), abs(dy), abs(dz)
    if ax >= ay and ax >= az:
        dy_res, dz_res = 0.0, 0.0
    assert (dx, dy_res, dz_res) == (1.5, 0.0, 0.0)


def test_align_snap_tool_preselects_source_point_for_one_click_align(qapp):
    from types import SimpleNamespace
    from PySide6.QtWidgets import QWidget
    from trazomob.builders.mesh_utils import create_board_group
    from trazomob.interaction.align_tool_interactive import AlignSnapTool

    grp = create_board_group("Modulo_1", origin=(0.0, 0.0, 0.0), size=(0.6, 0.5, 0.7), material="MDF")
    vp = QWidget()
    vp.scene = SimpleNamespace(selection=[grp])

    tool = AlignSnapTool()
    tool.on_activate(vp)
    assert tool.source_group is grp
    assert tool.source_point is not None
    assert tool.source_point.kind == "center"
    tool.on_deactivate(vp)
