# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes de regressão para visibilidade e oclusão de linhas-guia e contorno de parede selecionada."""
from __future__ import annotations

from types import SimpleNamespace
import numpy as np
import pytest

from PySide6.QtCore import QPointF
from PySide6.QtGui import QImage, QMatrix4x4, QPainter, QVector3D
from PySide6.QtWidgets import QApplication, QWidget

from core.group import Group
from core.mesh import Mesh
from core.scene import Scene
from trazomob.wall.guides import (
    WallGuideRulerManager,
    filter_occluded_segments,
    is_wall_face_visible_to_camera,
)
from trazomob.wall.selection import WallFaceInfo, WallSelectionManager


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _FakeCamera:
    def __init__(self, eye: QVector3D, forward: QVector3D, *, perspective: bool = True) -> None:
        self._eye = eye
        self._fwd = forward.normalized()
        self.perspective = perspective
        self.target = eye + self._fwd * 3.0
        self.distance = 3.0

    def eye(self) -> QVector3D:
        return self._eye

    def forward(self) -> QVector3D:
        return self._fwd

    def projection_matrix(self) -> QMatrix4x4:
        return QMatrix4x4()

    def view_matrix(self) -> QMatrix4x4:
        return QMatrix4x4()


class _RecordingPainter(QPainter):
    def __init__(self, img: QImage) -> None:
        super().__init__(img)
        self.drawn_lines: list[tuple[QPointF, QPointF]] = []

    def drawLine(self, p1, p2=None):  # noqa: N802
        if p2 is not None and isinstance(p1, QPointF):
            self.drawn_lines.append((QPointF(p1), QPointF(p2)))
        super().drawLine(p1, p2) if p2 is not None else super().drawLine(p1)


class _OverlayViewport(QWidget):
    def __init__(self, scene: Scene, camera: _FakeCamera, idx, occluder_t_fn=None) -> None:
        super().__init__()
        self.viewport = self
        self.scene = scene
        self.camera = camera
        self._idx = idx
        self._occluder_t_fn = occluder_t_fn
        self._ext_overlays = []
        self._lazy_fn = None

    def _pick_index(self, near=None):
        return self._idx

    def _ray_hits(self, idx, origin, direction, ent_mask):
        if self._occluder_t_fn is None:
            return np.full(len(idx.entities), np.inf)
        return self._occluder_t_fn(idx, origin, direction, ent_mask)

    def _clip_segment_front(self, a: QVector3D, b: QVector3D):
        return (a, b)

    def world_to_pixel(self, pt: QVector3D):
        return (100.0 + pt.x() * 100.0, 400.0 - pt.z() * 100.0)

    def _clip_pixel_line(self, p0, p1, margin=32.0):
        return (p0, p1)


def _make_wall_quad(name: str = "Parede Norte", length: float = 4.0, height: float = 2.6):
    mesh = Mesh()
    v0 = QVector3D(0.0, 0.0, 0.0)
    v1 = QVector3D(length, 0.0, 0.0)
    v2 = QVector3D(length, 0.0, height)
    v3 = QVector3D(0.0, 0.0, height)
    face = mesh.add_face([v0, v1, v2, v3])
    grp = Group(mesh, name=name)
    grp.ext = {"trazomob_wall": {"pontos": [[0.0, 0.0, 0.0], [length, 0.0, 0.0]]}}
    return grp, face


def test_parallel_and_oblique_transformed_wall_visibility():
    wall_grp, face = _make_wall_quad()
    xf = QMatrix4x4()
    xf.translate(2.0, 1.0, 0.0)
    xf.rotate(90.0, 0.0, 0.0, 1.0)
    raw_pts = [xf.map(p) for p in face.vertices]
    local_normal = QVector3D(0.0, 1.0, 0.0)
    center = QVector3D(2.0, 0.0, 1.3)

    # Câmera paralela deslocada por pan que antes falhava com eye_pos - c_world
    ortho_cam = _FakeCamera(
        eye=QVector3D(10.0, 1.0, 8.0),
        forward=QVector3D(1.0, -0.2, 0.0),
        perspective=False,
    )
    assert is_wall_face_visible_to_camera(ortho_cam, raw_pts, local_normal, center, xf=xf) is True

    # Olhando pelas costas da face transformada -> oculto
    back_cam = _FakeCamera(
        eye=QVector3D(5.0, 3.0, 1.3),
        forward=QVector3D(-1.0, 0.0, 0.0),
        perspective=False,
    )
    assert is_wall_face_visible_to_camera(back_cam, raw_pts, local_normal, center, xf=xf) is False


def test_ceiling_floor_light_and_glass_do_not_occlude_guides_at_elevated_angles(qapp):
    WallGuideRulerManager._instance = None
    ruler = WallGuideRulerManager.get_instance()
    ruler.visible = True
    ruler.show_labels = False

    scene = Scene()
    wall_grp, face = _make_wall_quad()
    ceiling = Group(Mesh(), name="Teto")
    ceiling.ext = {"trazomob_ceiling": True}
    floor = Group(Mesh(), name="Piso")
    floor.ext = {"trazomob_floor": True}
    glass_mod = Group(Mesh(), name="Cristaleira")
    glass_face = SimpleNamespace(attrs={"opacity": 0.25, "mat": "Vidro Incolor"})
    scene.groups.extend([wall_grp, ceiling, floor, glass_mod])

    info = WallFaceInfo(
        wall_group=wall_grp,
        face=face,
        normal=QVector3D(0.0, 1.0, 0.0),
        center=QVector3D(2.0, 0.0, 1.3),
        segment_index=0,
        face_type="interna",
    )

    idx = SimpleNamespace(
        entities=[(face, wall_grp), (SimpleNamespace(attrs={}), ceiling), (SimpleNamespace(attrs={}), floor), (glass_face, glass_mod)],
        ent_vis=np.array([True, True, True, True], dtype=bool),
    )
    cam = _FakeCamera(eye=QVector3D(2.0, 3.0, 3.4), forward=QVector3D(0.0, -0.8, -0.6), perspective=True)

    # Simula ray_hits que só acusa colisão se ent_mask incluir teto/piso/vidro
    def ray_fn(_idx, _orig, _dir, mask):
        out = np.full(len(_idx.entities), np.inf)
        for i in range(len(out)):
            if mask[i]:
                out[i] = 1.0
        return out

    vp = _OverlayViewport(scene, cam, idx, occluder_t_fn=ray_fn)
    img = QImage(800, 600, QImage.Format_ARGB32)
    painter = _RecordingPainter(img)
    ruler.draw_ruler_overlay(vp, painter, info)
    painter.end()

    # Todos os 5 níveis de Cozinha devem ser desenhados mesmo olhando de cima pelo teto/vidro
    assert len(painter.drawn_lines) == len(ruler.get_active_levels())


def test_selection_outline_and_guides_respect_foreground_and_lazy_occlusion(qapp):
    WallSelectionManager._instance = None
    WallGuideRulerManager._instance = None
    ruler = WallGuideRulerManager.get_instance()
    ruler.visible = True
    ruler.show_labels = False

    scene = Scene()
    wall_grp, face = _make_wall_quad(length=4.0, height=2.6)
    cabinet = Group(Mesh(), name="Balcao")
    cabinet.ext = {"trazomob_module": True}
    cab_face = SimpleNamespace(attrs={})
    scene.groups.extend([wall_grp, cabinet])

    info = WallFaceInfo(
        wall_group=wall_grp,
        face=face,
        normal=QVector3D(0.0, 1.0, 0.0),
        center=QVector3D(2.0, 0.0, 1.3),
        segment_index=0,
        face_type="interna",
    )

    idx = SimpleNamespace(
        entities=[(face, wall_grp), (cab_face, cabinet)],
        ent_vis=np.array([True, True], dtype=bool),
    )
    cam = _FakeCamera(eye=QVector3D(2.0, 4.0, 1.3), forward=QVector3D(0.0, -1.0, 0.0), perspective=True)

    # Balcão opaco cobre x in [1.0, 3.0], z in [0.0, 1.0]; ilha lazy cobre x in [0.0, 4.0], z < 0.2
    def ray_fn(_idx, orig, dirc, mask):
        out = np.full(len(_idx.entities), np.inf)
        if mask[1]:
            # Plano y = 1.0 do balcão
            if abs(dirc.y()) > 1e-6:
                t = (1.0 - orig.y()) / dirc.y()
                hit = orig + dirc * t
                if t > 0 and 1.0 <= hit.x() <= 3.0 and 0.0 <= hit.z() <= 1.0:
                    out[1] = t
        return out

    vp = _OverlayViewport(scene, cam, idx, occluder_t_fn=ray_fn)
    lazy_island = Group(Mesh(), name="IlhaLazy")
    vp._lazy_native = lambda: "native_handle"

    def _lazy_face_hits(_nat, orig, dirc, _which, reach=None):
        # Pessoa em pé na direita: em y = 2.0 (metade da distância até y = 0), cobre x em [2.6, 4.1]
        if abs(dirc.y()) > 1e-6:
            t = (2.0 - orig.y()) / dirc.y()
            hit = orig + dirc * t
            if t > 0 and (reach is None or t <= reach) and 2.6 <= hit.x() <= 4.1 and 0.0 <= hit.z() <= 2.7:
                return ([t], [1.0], [(0, 0)], lambda _m: (SimpleNamespace(attrs={}), lazy_island), lambda _m: lazy_island)
        return None

    vp._lazy_face_hits = _lazy_face_hits

    sel_mgr = WallSelectionManager.get_instance(vp)
    sel_mgr.selected_wall_face = info

    img = QImage(800, 600, QImage.Format_ARGB32)
    painter = _RecordingPainter(img)
    sel_mgr.draw_selection_overlay(vp, painter)
    painter.end()

    # Aresta de base (z=0) deve aparecer só na esquerda livre [0.0 .. 1.0], nunca cobrindo o balcão nem a pessoa à direita
    base_segments = [
        (p0, p1) for p0, p1 in painter.drawn_lines
        if abs(p0.y() - 400.0) < 1.0 and abs(p1.y() - 400.0) < 1.0
    ]
    assert len(base_segments) == 1
    seg_min_x = min(base_segments[0][0].x(), base_segments[0][1].x())
    seg_max_x = max(base_segments[0][0].x(), base_segments[0][1].x())
    # Coordenada de tela: x_world = 0..1 -> px = 100..200 (com step discreto próximo de 200)
    assert seg_min_x < 120.0
    assert seg_max_x <= 215.0


def test_placement_frame_disappears_on_module_and_non_wall_click(qapp):
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QMouseEvent
    from trazomob.interaction.magnetic_drag import MagneticModuleDragFilter

    WallSelectionManager._instance = None
    scene = Scene()
    wall_grp, wall_face = _make_wall_quad(length=4.0, height=2.6)
    cab_mesh = Mesh()
    cab_mesh.add_face([
        QVector3D(1.0, 0.0, 0.0),
        QVector3D(1.8, 0.0, 0.0),
        QVector3D(1.8, 0.55, 0.0),
        QVector3D(1.0, 0.55, 0.0),
    ])
    cab = Group(cab_mesh, name="Balcao")
    cab.ext = {"trazomob_module": {"rot_z": 0.0}, "trazomob": {"kind": "module"}}
    decor = Group(Mesh(), name="Batedeira")
    scene.groups.extend([wall_grp, cab, decor])

    cam = _FakeCamera(eye=QVector3D(2.0, 4.0, 1.3), forward=QVector3D(0.0, -1.0, 0.0), perspective=True)
    vp = _OverlayViewport(scene, cam, None)
    vp._pixel_to_ray = lambda _x, _y: (cam.eye(), QVector3D(0.0, -1.0, 0.0))
    vp._ray_plane = lambda _o, _d, c, _n: QVector3D(2.0, 0.0, 0.5)
    vp._build_ctx = lambda _e: None

    pick_state = {"group": wall_grp, "face": wall_face}
    vp.pick_group = lambda _x, _y: pick_state["group"]
    vp.pick_face_any = lambda _x, _y: (pick_state["face"], pick_state["group"])

    drag_filter = MagneticModuleDragFilter(vp, parent=vp)
    wall_mgr = WallSelectionManager.get_instance(vp)

    def _left_click():
        return QMouseEvent(
            QEvent.MouseButtonPress,
            QPointF(100.0, 100.0),
            QPointF(100.0, 100.0),
            Qt.LeftButton,
            Qt.LeftButton,
            Qt.NoModifier,
        )

    # 1. Clique diretamente na parede arma o frame 3D
    drag_filter.eventFilter(vp, _left_click())
    assert wall_mgr.selected_wall_face is not None
    assert wall_mgr.active_placement_slot is not None

    # 2. Clique em um módulo encostado na parede deve limpar o frame 3D imediatamente
    pick_state["group"] = cab
    pick_state["face"] = None
    drag_filter.eventFilter(vp, _left_click())
    assert wall_mgr.active_placement_slot is None

    # 3. Re-arma na parede e clica em objeto solto não-parede -> limpa seleção e frame
    pick_state["group"] = wall_grp
    pick_state["face"] = wall_face
    drag_filter.eventFilter(vp, _left_click())
    assert wall_mgr.active_placement_slot is not None

    pick_state["group"] = decor
    pick_state["face"] = None
    drag_filter.eventFilter(vp, _left_click())
    assert wall_mgr.active_placement_slot is None
    assert wall_mgr.selected_wall_face is None
