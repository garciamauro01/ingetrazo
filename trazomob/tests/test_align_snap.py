# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes para o sistema de Alinhamento e Centralização 3D."""
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QVector3D
from core.group import Group
from core.mesh import Mesh, Vertex
from trazomob.interaction.align_tool_interactive import AlignSnapTool, NotablePoint


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
