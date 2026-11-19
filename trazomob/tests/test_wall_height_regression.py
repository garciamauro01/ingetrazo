# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Regressões do construtor de paredes: altura por segmento e altura do teto."""

import sys

import pytest
from PySide6.QtGui import QVector3D
from PySide6.QtWidgets import QApplication

from core.scene import Scene
from core.units import bare_number_scale
from trazomob.wall.builder import WallBuilderTool
from trazomob.wall.floorplan_dialog import WallFloorplanDialog
from trazomob.wall.plan_2d import WallGraph2D


class DummyViewport:
    def __init__(self, scene):
        self.scene = scene

    def update(self):
        pass

    def flash_status(self, msg):
        pass


def _app():
    return QApplication.instance() or QApplication(sys.argv)


def _square_graph(short_height=1.0, tall_height=2.6):
    graph = WallGraph2D()
    seg_ids = [
        graph.add_segment(0, 0, 4, 0),
        graph.add_segment(4, 0, 4, 3),
        graph.add_segment(4, 3, 0, 3),
        graph.add_segment(0, 3, 0, 0),
    ]
    for index, seg_id in enumerate(seg_ids):
        graph.segments[seg_id].height = short_height if index == 0 else tall_height
    return graph, seg_ids


def _heights(graph):
    return sorted(round(s.height, 3) for s in graph.segments.values())


def test_height_per_segment_survives_graph_2d_roundtrip():
    """Baseline: o grafo serializado no grupo 3D conserva a altura individual."""
    graph, _ = _square_graph()
    scene = Scene()
    group = graph.build_3d_group(scene, altura_m=2.6, name="Cozinha")

    restored = WallGraph2D.from_group(group)

    assert restored is not None
    assert _heights(restored) == [1.0, 2.6, 2.6, 2.6]


def test_height_per_segment_survives_legacy_group():
    """Paredes sem graph_2d devem recuperar as alturas do campo 'alturas'."""
    graph, _ = _square_graph()
    scene = Scene()
    group = graph.build_3d_group(scene, altura_m=2.6, name="Cozinha")
    group.ext["trazomob_wall"] = {
        "pontos": [[0, 0, 0], [4, 0, 0], [4, 3, 0], [0, 3, 0]],
        "is_closed": True,
        "espessura": 0.15,
        "altura": 2.6,
        "alturas": [1.0, 2.6, 2.6, 2.6],
    }

    restored = WallGraph2D.from_group(group)

    assert restored is not None
    assert _heights(restored) == [1.0, 2.6, 2.6, 2.6]


def test_opening_editor_does_not_overwrite_segment_heights():
    """Abrir a planta 2D não pode apagar a altura de 1000 mm com o pé-direito padrão."""
    _app()
    graph, _ = _square_graph()
    scene = Scene()
    group = graph.build_3d_group(scene, altura_m=2.6, name="Cozinha")
    scene.groups.append(group)
    scene.selection = {group}

    dialog = WallFloorplanDialog(DummyViewport(scene), existing_group=group)

    assert _heights(dialog.graph) == [1.0, 2.6, 2.6, 2.6]


def test_opening_editor_with_low_default_keeps_taller_walls():
    """O campo inicial não pode propagar um pé-direito baixo a todas as paredes."""
    _app()
    graph, _ = _square_graph()
    scene = Scene()
    group = graph.build_3d_group(scene, altura_m=2.6, name="Cozinha")
    group.ext["trazomob_wall"] = {
        "pontos": [[0, 0, 0], [4, 0, 0], [4, 3, 0], [0, 3, 0]],
        "is_closed": True,
        "espessura": 0.15,
        "altura": 1.0,
        "alturas": [1.0, 2.6, 2.6, 2.6],
    }
    scene.groups.append(group)
    scene.selection = {group}

    dialog = WallFloorplanDialog(DummyViewport(scene), existing_group=group)

    assert _heights(dialog.graph) == [1.0, 2.6, 2.6, 2.6]


def test_rebuild_preserves_short_wall_height():
    """Reconstruir a partir do editor não pode devolver a parede ao pé-direito padrão."""
    _app()
    graph, _ = _square_graph()
    scene = Scene()
    group = graph.build_3d_group(scene, altura_m=2.6, name="Cozinha")
    group.ext["trazomob_wall"] = {
        "pontos": [[0, 0, 0], [4, 0, 0], [4, 3, 0], [0, 3, 0]],
        "is_closed": True,
        "espessura": 0.15,
        "altura": 2.6,
        "alturas": [1.0, 2.6, 2.6, 2.6],
    }
    scene.groups.append(group)
    scene.selection = {group}

    dialog = WallFloorplanDialog(DummyViewport(scene), existing_group=group)
    dialog.chk_floor.setChecked(False)
    dialog.chk_ceiling.setChecked(False)
    dialog._build_3d_and_close()

    walls = [
        g for g in scene.groups
        if isinstance(g.ext, dict) and g.ext.get("trazomob_wall")
    ]
    assert len(walls) == 4
    tops = sorted(
        round(max(v.position.z() for v in w.mesh.vertices), 3)
        for w in walls
    )
    assert tops == [1.0, 2.6, 2.6, 2.6]


def test_sidebar_height_survives_editor_and_rebuild():
    """Fluxo completo: sidebar grava 1000 mm, planta reabre e reconstrói sem perder."""
    _app()
    scene = Scene()
    pts = [
        QVector3D(0, 0, 0), QVector3D(4, 0, 0),
        QVector3D(4, 3, 0), QVector3D(0, 3, 0),
    ]
    group = WallBuilderTool.build_chain_group(
        scene, pts, is_closed=True,
        altura_m=[1.0, 2.6, 2.6, 2.6], espessura_m=0.15,
    )
    scene.groups.append(group)
    scene.selection = {group}

    dialog = WallFloorplanDialog(DummyViewport(scene), existing_group=group)
    assert _heights(dialog.graph) == [1.0, 2.6, 2.6, 2.6]

    dialog.chk_floor.setChecked(False)
    dialog.chk_ceiling.setChecked(False)
    dialog._build_3d_and_close()

    walls = [
        g for g in scene.groups
        if isinstance(g.ext, dict) and g.ext.get("trazomob_wall")
    ]
    assert len(walls) == 4
    tops = sorted(round(max(v.position.z() for v in w.mesh.vertices), 3) for w in walls)
    assert tops == [1.0, 2.6, 2.6, 2.6]


def test_ceiling_uses_tallest_wall_in_room():
    """O forro deve ficar no pé-direito do cômodo, não na altura da parede selecionada."""
    _app()
    scene = Scene()
    dialog = WallFloorplanDialog(DummyViewport(scene))
    seg_ids = [
        dialog.graph.add_segment(0, 0, 4, 0),
        dialog.graph.add_segment(4, 0, 4, 3),
        dialog.graph.add_segment(4, 3, 0, 3),
        dialog.graph.add_segment(0, 3, 0, 0),
    ]

    # Usuário seleciona a parede de 1000 mm: o campo passa a exibir 1.0 m.
    dialog.canvas._selected_seg_id = seg_ids[0]
    dialog.sp_height.setValue(1.0 / bare_number_scale())
    # As demais paredes continuam com o pé-direito de 2.60 m.
    for seg_id in seg_ids[1:]:
        dialog.graph.segments[seg_id].height = 2.6

    dialog.chk_floor.setChecked(False)
    dialog.chk_ceiling.setChecked(True)
    dialog._build_3d_and_close()

    ceilings = [
        g for g in scene.groups
        if isinstance(g.ext, dict) and g.ext.get("trazomob_ceiling")
    ]
    assert len(ceilings) == 1
    zs = [v.position.z() for v in ceilings[0].mesh.vertices]
    assert min(zs) == pytest.approx(2.6, abs=1e-4)
