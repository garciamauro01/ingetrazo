# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes de regressão para ajuste fino com mouse muito próximo (sem saltos ou câmera dentro do móvel)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QVector3D
from PySide6.QtWidgets import QApplication, QWidget

from core.group import Group
from core.mesh import Mesh
from core.scene import Scene
from trazomob.interaction.magnetic_drag import MagneticModuleDragFilter


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _DragCamera:
    def __init__(self, eye: QVector3D, forward: QVector3D, *, perspective: bool = True) -> None:
        self._eye = eye
        self._fwd = forward.normalized()
        self.perspective = perspective

    def eye(self) -> QVector3D:
        return self._eye

    def forward(self) -> QVector3D:
        return self._fwd


class _DragTestViewport(QWidget):
    def __init__(self, scene: Scene, camera: _DragCamera, ray_fn) -> None:
        super().__init__()
        self.scene = scene
        self.camera = camera
        self._ray_fn = ray_fn
        self._ext_overlays = []
        self.last_offset = QVector3D(0.0, 0.0, 0.0)

    def _pixel_to_ray(self, x: float, y: float):
        return self._ray_fn(x, y)

    def _build_ctx(self, _event):
        return None

    def set_groups_preview_offset(self, delta: QVector3D) -> None:
        self.last_offset = QVector3D(delta)

    def set_groups_preview_matrix(self, _m) -> None:
        pass


def _make_cabinet(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> Group:
    mesh = Mesh()
    v0 = QVector3D(x0, y0, z0)
    v1 = QVector3D(x1, y0, z0)
    v2 = QVector3D(x1, y1, z0)
    v3 = QVector3D(x0, y1, z0)
    v4 = QVector3D(x0, y0, z1)
    v5 = QVector3D(x1, y0, z1)
    v6 = QVector3D(x1, y1, z1)
    v7 = QVector3D(x0, y1, z1)
    mesh.add_face([v0, v3, v2, v1])
    mesh.add_face([v4, v5, v6, v7])
    mesh.add_face([v0, v1, v5, v4])
    mesh.add_face([v2, v3, v7, v6])
    grp = Group(mesh, name="BalcaoFino")
    grp.ext = {"trazomob_module": {"rot_z": 0.0}, "trazomob": {"kind": "module"}}
    return grp


def test_close_up_eye_level_press_and_fine_drag_does_not_jump_to_camera(qapp):
    scene = Scene()
    # Balcão em y=[0.40, 1.00], câmera muito próxima em y=0.18 (22 cm da frente!)
    mod = _make_cabinet(0.0, 0.8, 0.40, 1.00, 0.0, 0.72)
    scene.groups.append(mod)
    eye = QVector3D(0.40, 0.18, 0.50)
    cam = _DragCamera(eye=eye, forward=QVector3D(0.0, 1.0, -0.04))

    def ray_fn(px: float, py: float):
        # px desloca 1mm por pixel na distância de ~22cm; py oscila verticalmente perto do horizonte
        dx = (px - 100.0) * 0.001
        dz = -0.04 + (py - 100.0) * 0.005
        return eye, QVector3D(dx, 1.0, dz).normalized()

    vp = _DragTestViewport(scene, cam, ray_fn)
    f = MagneticModuleDragFilter(vp, parent=vp)
    f._module_orig_bounds = (0.0, 0.8, 0.40, 1.00, 0.0, 0.72)

    # _handle_press deve manter o ponto clicado na face (~y=0.40, z~0.49), sem projetar dezenas de metros no chão z=0
    vp._build_ctx = lambda _e: SimpleNamespace(world=None)
    event = SimpleNamespace(position=lambda: QPointF(100.0, 100.0))
    f.snap_enabled = False
    f._target_module = mod
    f._affected_groups = [mod]

    # Executa lógica equivalente via _handle_press mockando _find_top_module
    f._find_top_module = lambda _g: mod
    vp.pick_group = lambda _x, _y: mod
    assert f._handle_press(event) is True
    assert f._start_world_pt is not None
    assert abs(f._start_world_pt.y() - 0.40) < 0.02
    assert f._start_world_pt.z() > 0.35

    # Movimento fino lateral (20px direita = ~4.4mm) com pequena deriva vertical no mouse (py 100 -> 115, cruzando horizonte!)
    assert f._recompute_from_pos(QPointF(120.0, 115.0)) is True
    assert 0.0 < vp.last_offset.x() < 0.05
    # Não pode dar salto brusco em Y em direção ou além da câmera
    assert abs(vp.last_offset.y()) < 0.05


def test_camera_inside_module_guard_prevents_swallowing_eye(qapp):
    scene = Scene()
    mod = _make_cabinet(0.0, 0.8, 0.40, 1.00, 0.0, 0.72)
    scene.groups.append(mod)
    eye = QVector3D(0.40, 0.18, 0.85)  # 13cm acima do topo? Vamos testar com eye dentro da altura [0..0.72]
    eye_low = QVector3D(0.40, 0.18, 0.50)
    cam = _DragCamera(eye=eye_low, forward=QVector3D(0.0, 0.8, -0.6))

    def ray_fn(px: float, py: float):
        # Raio mirando bem para baixo (tento puxar móvel direto para cima da câmera!)
        dy = 0.8 - (py - 100.0) * 0.015
        return eye_low, QVector3D((px - 100.0) * 0.002, max(0.05, dy), -0.6).normalized()

    vp = _DragTestViewport(scene, cam, ray_fn)
    vp.pick_group = lambda _x, _y: mod
    f = MagneticModuleDragFilter(vp, parent=vp)
    f._find_top_module = lambda _g: mod
    f.snap_enabled = False
    vp._build_ctx = lambda _e: SimpleNamespace(world=QVector3D(0.40, 0.40, 0.35))

    assert f._handle_press(SimpleNamespace(position=lambda: QPointF(100.0, 100.0))) is True
    # Puxa agressivamente para perto da câmera
    assert f._recompute_from_pos(QPointF(102.0, 145.0)) is True

    # Limite frontal mínimo (0.40 + dy) nunca pode passar por cima de eye_low.y() = 0.18
    assert 0.40 + vp.last_offset.y() >= eye_low.y() + 0.04


def test_wall_lock_does_not_jump_vertically_when_grabbed_close_up(qapp):
    from trazomob.wall.selection import WallSelectionManager

    WallSelectionManager._instance = None
    scene = Scene()
    wall_mesh = Mesh()
    wv0 = QVector3D(0.0, 1.0, 0.0)
    wv1 = QVector3D(3.0, 1.0, 0.0)
    wv2 = QVector3D(3.0, 1.0, 2.6)
    wv3 = QVector3D(0.0, 1.0, 2.6)
    wall_mesh.add_face([wv0, wv1, wv2, wv3])  # normal (0, -1, 0) voltada para -Y
    wall = Group(wall_mesh, name="ParedeNorte")
    wall.ext = {"trazomob_wall": {"pontos": [[0.0, 1.0, 0.0], [3.0, 1.0, 0.0]], "espessura": 0.15}}

    # Aéreo já montado na parede em z=[1.50..2.20], frente em y=0.65, fundo encostado em y=1.00
    aereo = _make_cabinet(0.8, 1.6, 0.65, 1.00, 1.50, 2.20)
    scene.groups.extend([wall, aereo])

    eye = QVector3D(1.2, 0.40, 1.85)  # 25cm à frente do aéreo
    cam = _DragCamera(eye=eye, forward=QVector3D(0.0, 1.0, 0.0))
    vp = _DragTestViewport(scene, cam, lambda _x, _y: (eye, QVector3D(0.0, 1.0, 0.0)))
    f = MagneticModuleDragFilter(vp, parent=vp)
    f._target_module = aereo
    f._affected_groups = [aereo]
    f._module_orig_bounds = (0.8, 1.6, 0.65, 1.00, 1.50, 2.20)
    f._start_world_pt = QVector3D(1.2, 0.65, 1.92)  # usuário clicou em z=1.92 na frente
    f._current_delta = QVector3D(0.0, 0.0, 0.0)

    # Raio inclinado atinge a parede ao fundo em z = 1.78 (diferente de start_world_pt.z=1.92)
    ray_dir = QVector3D(0.0, 0.60, -0.14).normalized()
    snapped = f._compute_magnetic_snap(QVector3D(0.01, 0.0, 0.0), eye, ray_dir)

    # No primeiro instante de engate na parede, não pode haver salto vertical para baixo/cima!
    assert abs(snapped.z()) < 0.01
