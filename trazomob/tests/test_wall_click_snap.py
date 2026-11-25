# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Snap magnético do frame de inserção ao clicar na parede perto de um móvel existente."""
from __future__ import annotations

import pytest
from PySide6.QtGui import QVector3D

from core.group import Group
from core.mesh import Mesh
from core.scene import Scene
from trazomob.wall.guides import WallGuideRulerManager
from trazomob.wall.selection import WallFaceInfo, WallSelectionManager


class _Viewport:
    """Viewport mínimo: só o necessário para armar o frame 3D."""

    def __init__(self, scene: Scene, hit_x: float) -> None:
        self.scene = scene
        self.hit_x = hit_x
        self._ext_overlays = []
        self.status = None

    def _pixel_to_ray(self, _px, _py):
        return QVector3D(0.0, 0.0, 0.0), QVector3D(0.0, -1.0, 0.0)

    def _ray_plane(self, _orig, _dir, _center, _normal):
        return QVector3D(self.hit_x, 0.0, 0.35)

    def update(self) -> None:
        pass

    def flash_status(self, msg: str) -> None:
        self.status = msg


def _make_wall(length: float = 4.0):
    mesh = Mesh()
    face = mesh.add_face([
        QVector3D(0.0, 0.0, 0.0),
        QVector3D(length, 0.0, 0.0),
        QVector3D(length, 0.0, 2.6),
        QVector3D(0.0, 0.0, 2.6),
    ])
    grp = Group(mesh, name="Parede")
    grp.ext = {"trazomob_wall": {"pontos": [[0.0, 0.0, 0.0], [length, 0.0, 0.0]]}}
    return grp, face


def _make_module(x0: float, x1: float) -> Group:
    mesh = Mesh()
    for y in (-0.55, 0.0):  # encostado na face da parede (normal -Y)
        mesh.add_face([
            QVector3D(x0, y, 0.0),
            QVector3D(x1, y, 0.0),
            QVector3D(x1, y, 0.72),
            QVector3D(x0, y, 0.72),
        ])
    grp = Group(mesh, name="Balcao")
    grp.ext = {"trazomob_module": {"rot_z": 0.0}, "trazomob": {"kind": "module"}}
    return grp


@pytest.fixture
def arm_click(monkeypatch):
    """Prepara cena com uma parede e um balcão entre X=1.0 e X=1.8."""

    def _arm(hit_x: float, *, with_module: bool = True):
        WallSelectionManager._instance = None
        WallGuideRulerManager._instance = None
        ruler = WallGuideRulerManager.get_instance()
        monkeypatch.setattr(ruler, "get_slot_between_guides", lambda _z: {
            "z_base": 0.0,
            "z_top": 0.9,
            "height_mm": 900.0,
            "default_depth_mm": 550.0,
            "label": "Vão de teste",
        })

        wall, face = _make_wall()
        scene = Scene()
        scene.groups.append(wall)
        if with_module:
            scene.groups.append(_make_module(1.0, 1.8))

        vp = _Viewport(scene, hit_x)
        mgr = WallSelectionManager.get_instance(vp)
        mgr.selected_wall_face = WallFaceInfo(
            wall_group=wall,
            face=face,
            segment_index=0,
            face_type="interna",
            normal=QVector3D(0.0, -1.0, 0.0),
            center=QVector3D(2.0, 0.0, 1.3),
        )
        mgr.arm_frame_from_click(1.0, 1.0)
        assert mgr.active_placement_slot is not None
        return mgr, mgr.active_placement_slot

    return _arm


def test_click_near_right_edge_snaps_frame_to_existing_module(arm_click):
    _mgr, slot = arm_click(hit_x=1.85)  # 5 cm além da borda direita do balcão

    assert slot["anchor_u"] == pytest.approx(1.8)
    assert slot["anchor_side"] == "right"
    # Borda esquerda do novo frame encosta exatamente na borda direita do balcão
    assert slot["u_pos"] - slot["width_m"] * 0.5 == pytest.approx(1.8)


def test_click_near_left_edge_snaps_frame_to_existing_module(arm_click):
    _mgr, slot = arm_click(hit_x=0.95)  # 5 cm antes da borda esquerda do balcão

    assert slot["anchor_u"] == pytest.approx(0.2)  # 1.0 - 0.80 (largura padrão)
    assert slot["anchor_side"] == "left"
    # Borda direita do novo frame encosta exatamente na borda esquerda do balcão
    assert slot["u_pos"] + slot["width_m"] * 0.5 == pytest.approx(1.0)


def test_click_far_from_modules_keeps_raw_position(arm_click):
    _mgr, slot = arm_click(hit_x=3.0)

    assert "anchor_u" not in slot
    assert slot["u_pos"] == pytest.approx(3.0)


def test_snapped_frame_stays_glued_when_width_changes(arm_click):
    mgr, slot = arm_click(hit_x=1.85)
    mgr.update_frame_dimensions(0.6)

    assert slot["width_m"] == pytest.approx(0.6)
    assert slot["u_pos"] - slot["width_m"] * 0.5 == pytest.approx(1.8)
    assert slot["anchor_u"] == pytest.approx(1.8)


def test_left_snapped_frame_stays_glued_when_width_changes(arm_click):
    mgr, slot = arm_click(hit_x=0.95)
    mgr.update_frame_dimensions(0.6)

    assert slot["u_pos"] + slot["width_m"] * 0.5 == pytest.approx(1.0)
    assert slot["anchor_u"] == pytest.approx(0.4)


def test_advance_after_placement_continues_on_snapped_side(arm_click):
    mgr, slot = arm_click(hit_x=1.85)
    mgr.advance_slot_after_placement(0.8)

    # Módulo inserido ocupa 1.8..2.6; o próximo frame começa em 2.6
    assert slot["anchor_u"] == pytest.approx(2.6)
    assert slot["u_pos"] - slot["width_m"] * 0.5 == pytest.approx(2.6)
