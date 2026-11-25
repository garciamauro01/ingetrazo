# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Regression tests for 2-point LED strip placement, orbit smoothness, and 90-deg rotation of any object."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QImage, QMatrix4x4, QPainter, QVector3D
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from core.group import Group
from core.history import History
from core.mesh import Mesh
from core.scene import Scene
from trazomob.context_menu import build_context_menu
from trazomob.domain.i18n import tr


@pytest.fixture
def engine_on():
    """Mantido por compatibilidade de assinatura nos testes de menu de contexto."""
    yield
from trazomob.interaction.align_tools import (
    get_entity_world_bounds,
    resolve_rotatable_groups,
    rotate_groups_with_command,
)
from trazomob.interaction.magnetic_drag import MagneticModuleDragFilter
from trazomob.render.lighting import (
    InsertLedStripTool,
    ToolContext,
    _clean_trazomob_lights,
    _surface_hit,
    create_light_scene_group,
)
from trazomob.wall.guides import build_wall_occluder_context


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _make_box_mesh(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> Mesh:
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
    mesh.add_face([v1, v2, v6, v5])
    mesh.add_face([v3, v0, v4, v7])
    return mesh


class _DummyWindow:
    def __init__(self, viewport=None) -> None:
        self._ext_data: dict = {}
        self.viewport = viewport


class _FakeSurfaceViewport:
    """Viewport double exposing pick_face_placement + ray-plane intersection + History."""

    def __init__(self, scene: Scene, plane_z: float = 2.1) -> None:
        self.scene = scene
        if not hasattr(self.scene, "plugin_data") or self.scene.plugin_data is None:
            self.scene.plugin_data = {}
        self.history = History(scene)
        self.plane_z = plane_z
        self._face_grp = Group(_make_box_mesh(0.0, 5.0, 0.0, 1.0, plane_z, plane_z + 0.3), name="Aereo")
        self._face = self._face_grp.mesh.faces[0]  # bottom face at z=plane_z
        self._window = _DummyWindow(self)
        self.updates = 0
        self.scene_notified = 0
        self.flash = ""
        self.active_tool = None

    def window(self):
        return self._window

    def pick_face_placement(self, _x, _y):
        return self._face, self._face_grp

    def _pixel_to_ray(self, x, y):
        # Screen (x, y) maps directly to target world XY at Z=self.plane_z from a camera at Z=0 looking up
        target = QVector3D(float(x) / 100.0, float(y) / 100.0, self.plane_z)
        origin = QVector3D(target.x(), target.y(), 0.0)
        direction = (target - origin).normalized()
        return origin, direction

    def _ray_plane(self, origin: QVector3D, direction: QVector3D, pt: QVector3D, normal: QVector3D):
        denom = QVector3D.dotProduct(direction, normal)
        if abs(denom) < 1e-8:
            return None
        t = QVector3D.dotProduct(pt - origin, normal) / denom
        return origin + direction * t

    def update(self) -> None:
        self.updates += 1

    def notify_scene_changed(self) -> None:
        self.scene_notified += 1

    def flash_status(self, msg: str) -> None:
        self.flash = msg

    def set_active_tool(self, tool) -> None:
        self.active_tool = tool


def test_led_strip_scene_group_no_double_translation():
    """Fita LED fora da origem não pode sofrer dupla translação entre mesh local e Group."""
    lt = {
        "kind": "led_strip",
        "p1": [2.4, 0.35, 2.1],
        "p2": [3.6, 0.35, 2.1],
        "pos": [3.0, 0.35, 2.1],
        "dir": [0.0, 0.0, -1.0],
        "length": 1.2,
        "power": 300.0,
        "color": [1.0, 0.95, 0.85],
    }
    grp = create_light_scene_group(lt, 0)
    bounds = get_entity_world_bounds(grp)
    assert bounds is not None
    # Centro deve ser exatamente pos (3.0, 0.35, 2.1), nunca ~6.0
    assert (bounds[0] + bounds[1]) * 0.5 == pytest.approx(3.0, abs=1e-3)
    assert (bounds[2] + bounds[3]) * 0.5 == pytest.approx(0.35, abs=1e-3)
    assert (bounds[4] + bounds[5]) * 0.5 == pytest.approx(2.1, abs=1e-3)
    assert bounds[0] == pytest.approx(2.4, abs=0.02)
    assert bounds[1] == pytest.approx(3.6, abs=0.02)


def test_clean_trazomob_lights_keeps_led_strip_and_fields():
    raw = [
        {
            "kind": "led_strip",
            "pos": [1.5, 0.3, 2.0],
            "p1": [1.0, 0.3, 2.0],
            "p2": [2.0, 0.3, 2.0],
            "dir": [0.0, 0.0, -1.0],
            "length": 1.0,
            "profile_w": 0.015,
            "power": 180.0,
            "color": [1.0, 0.9, 0.8],
        },
        {"kind": "spot", "pos": [0.0, 0.0, 2.5], "target": [0.0, 0.0, 0.0], "power": 100.0},
    ]
    cleaned = _clean_trazomob_lights(raw)
    assert len(cleaned) == 2
    assert cleaned[0]["kind"] == "led_strip"
    assert cleaned[0]["p1"] == [1.0, 0.3, 2.0]
    assert cleaned[0]["p2"] == [2.0, 0.3, 2.0]
    assert cleaned[0]["length"] == pytest.approx(1.0)
    assert cleaned[0]["profile_w"] == pytest.approx(0.015)


def test_surface_hit_prefers_clicked_face_over_distant_axis_inference():
    scene = Scene()
    vp = _FakeSurfaceViewport(scene, plane_z=2.1)

    # Snap fraco ("axis_inference") em Z=0 não deve puxar o ponto para longe da face em Z=2.1
    ctx_soft = ToolContext(
        viewport=vp,
        screen=QPoint(250, 40),
        world=QVector3D(0.2, 0.1, 0.0),
        modifiers=Qt.NoModifier,
        snap=SimpleNamespace(kind="axis_inference"),
    )
    hit, normal = _surface_hit(ctx_soft)
    assert hit is not None
    assert hit.x() == pytest.approx(2.5, abs=1e-4)
    assert hit.y() == pytest.approx(0.4, abs=1e-4)
    assert hit.z() == pytest.approx(2.1, abs=1e-4)
    assert normal is not None
    assert abs(normal.z()) == pytest.approx(1.0, abs=1e-4)

    # Snap real de ponto ("endpoint") próximo à face clicada é preservado
    ctx_end = ToolContext(
        viewport=vp,
        screen=QPoint(250, 40),
        world=QVector3D(2.52, 0.41, 2.1),
        modifiers=Qt.NoModifier,
        snap=SimpleNamespace(kind="endpoint"),
    )
    hit_end, _ = _surface_hit(ctx_end)
    assert hit_end == QVector3D(2.52, 0.41, 2.1)


def test_insert_led_strip_tool_two_clicks_places_at_clicked_points():
    scene = Scene()
    vp = _FakeSurfaceViewport(scene, plane_z=2.1)
    vp.app = SimpleNamespace(select_tool="SELECT")

    placed = []
    tool = InsertLedStripTool({"power": 240.0, "color": [1.0, 0.95, 0.85]}, on_placed=placed.append)
    tool.on_activate(vp)
    assert tool.start_point is None
    assert hasattr(tool, "work_plane") and tool.work_plane is None

    # 1º clique em (2.20, 0.30, 2.10)
    tool.on_click(ToolContext(viewport=vp, screen=QPoint(220, 30), world=QVector3D(0.0, 0.0, 0.0), modifiers=Qt.NoModifier, snap=None))
    assert tool.start_point is not None
    assert tool.start_point.x() == pytest.approx(2.2, abs=1e-4)
    assert tool.start_point.y() == pytest.approx(0.3, abs=1e-4)
    assert tool.start_point.z() == pytest.approx(2.1, abs=1e-4)

    # 2º clique em (3.80, 0.30, 2.10)
    tool.on_click(ToolContext(viewport=vp, screen=QPoint(380, 30), world=QVector3D(0.0, 0.0, 0.0), modifiers=Qt.NoModifier, snap=None))
    assert len(placed) == 1
    assert len(scene.groups) == 1
    assert tool.start_point is None
    assert tool.work_plane is None

    led_grp = scene.groups[0]
    bounds = get_entity_world_bounds(led_grp)
    assert bounds is not None
    assert (bounds[0] + bounds[1]) * 0.5 == pytest.approx(3.0, abs=1e-3)
    assert (bounds[2] + bounds[3]) * 0.5 == pytest.approx(0.3, abs=1e-3)
    assert (bounds[4] + bounds[5]) * 0.5 == pytest.approx(2.1, abs=1e-3)
    assert bounds[0] == pytest.approx(2.2, abs=0.02)
    assert bounds[1] == pytest.approx(3.8, abs=0.02)


class _OrbitViewport(QWidget):
    def __init__(self, scene: Scene) -> None:
        super().__init__()
        self.scene = scene
        self.camera = SimpleNamespace(yaw=35.0, pitch=20.0, distance=3.0, target=QVector3D(1.0, 0.5, 0.4))
        self._ext_overlays = []

    def world_to_screen(self, _p: QVector3D):
        return (400.0, 300.0)


def test_orbit_frames_reuse_cota_cache_when_module_selected(qapp, monkeypatch):
    """Girar câmera com módulo selecionado (mesmo sem cotas visíveis) não deve recalcular cotas todo frame."""
    scene = Scene()
    mod = Group(name="Balcao Encostado")
    mod.mesh = _make_box_mesh(0.0, 0.8, 0.0, 0.6, 0.0, 0.85)
    mod.ext = {"trazomob_module": {"largura": 800, "altura": 850, "profundidade": 600}}
    scene.groups = [mod]
    scene.selection = {mod}

    vp = _OrbitViewport(scene)
    filt = MagneticModuleDragFilter(vp)
    try:
        calls = 0

        def _fake_compute_cotas(bounds, exclude_module=None, exclude_groups=None):
            nonlocal calls
            calls += 1
            return []

        monkeypatch.setattr(filt, "_compute_cotas_for_bounds", _fake_compute_cotas)

        img = QImage(32, 32, QImage.Format_ARGB32)
        painter = QPainter(img)
        try:
            for frame in range(60):
                vp.camera.yaw = 35.0 + frame * 2.0
                filt._draw_cota_overlay(vp, painter)
        finally:
            painter.end()

        assert calls == 1

        # Ao mudar a seleção ou versão da cena, invalida corretamente e recalcula 1 vez
        scene.version += 1
        img2 = QImage(32, 32, QImage.Format_ARGB32)
        painter2 = QPainter(img2)
        try:
            filt._draw_cota_overlay(vp, painter2)
        finally:
            painter2.end()
        assert calls == 2
    finally:
        filt.cleanup()


def test_wall_occluder_context_caches_mask_on_unchanged_scene_and_camera():
    import numpy as np

    from trazomob.wall.guides import _OCCLUDER_MASK_CACHE

    wall = Group(_make_box_mesh(0.0, 4.0, 0.0, 0.15, 0.0, 2.6), name="Parede")
    cab = Group(_make_box_mesh(1.0, 2.0, -0.6, 0.0, 0.0, 0.85), name="Modulo")
    scene = SimpleNamespace(groups=[wall, cab], version=7)
    entities = [(cab.mesh.faces[0], cab), (wall.mesh.faces[0], wall)]
    idx = SimpleNamespace(entities=entities, ent_vis=np.array([True, True], dtype=bool))

    class _MockProjVp:
        def __init__(self) -> None:
            self.scene = scene
            self.camera = SimpleNamespace(
                perspective=True,
                eye=lambda: QVector3D(2.0, -3.0, 1.5),
            )

        def _pick_index(self):
            return idx

        def _ray_hits(self, *_args, **_kwargs):
            return []

    vp = _MockProjVp()
    before_keys = len(_OCCLUDER_MASK_CACHE)
    ctx1 = build_wall_occluder_context(vp, wall)
    after_first = len(_OCCLUDER_MASK_CACHE)
    ctx2 = build_wall_occluder_context(vp, wall)
    after_second = len(_OCCLUDER_MASK_CACHE)
    assert ctx1 is not None and ctx2 is not None
    assert after_first >= before_keys
    assert after_second == after_first
    assert ctx1["mask"] is not None and ctx2["mask"] is not None


def test_rotate_90_generic_group_undo_redo():
    """Qualquer Group comum fora da origem rotaciona 90° em torno do seu centro com Undo/Redo."""
    scene = Scene()
    sofa = Group(_make_box_mesh(4.0, 6.0, 1.0, 2.0, 0.0, 0.8), name="Sofa Sala")
    scene.groups = [sofa]
    scene.selection = {sofa}
    vp = _FakeSurfaceViewport(scene)

    targets = resolve_rotatable_groups(scene)
    assert targets == [sofa]

    rotate_groups_with_command(targets, 90.0, vp)
    b_rot = get_entity_world_bounds(sofa)
    assert b_rot is not None
    # Centro (5.0, 1.5, 0.4) preservado, dimensões XY invertidas de 2x1 para 1x2
    assert (b_rot[0] + b_rot[1]) * 0.5 == pytest.approx(5.0, abs=1e-4)
    assert (b_rot[2] + b_rot[3]) * 0.5 == pytest.approx(1.5, abs=1e-4)
    assert (b_rot[1] - b_rot[0]) == pytest.approx(1.0, abs=1e-4)
    assert (b_rot[3] - b_rot[2]) == pytest.approx(2.0, abs=1e-4)

    vp.history.undo()
    b_undo = get_entity_world_bounds(sofa)
    assert (b_undo[1] - b_undo[0]) == pytest.approx(2.0, abs=1e-4)
    assert (b_undo[3] - b_undo[2]) == pytest.approx(1.0, abs=1e-4)

    vp.history.redo()
    b_redo = get_entity_world_bounds(sofa)
    assert (b_redo[1] - b_redo[0]) == pytest.approx(1.0, abs=1e-4)
    assert (b_redo[3] - b_redo[2]) == pytest.approx(2.0, abs=1e-4)


def test_rotate_90_component_instance_with_xform_does_not_mutate_shared_mesh():
    """Instância com ``xform`` rotaciona sem alterar a malha compartilhada por outras instâncias."""
    scene = Scene()
    proto_mesh = _make_box_mesh(-1.0, 1.0, -0.5, 0.5, 0.0, 0.9)

    xf_a = QMatrix4x4()
    xf_a.translate(0.0, 0.0, 0.0)
    inst_a = Group(proto_mesh, name="Mesa A")
    inst_a.xform = xf_a

    xf_b = QMatrix4x4()
    xf_b.translate(5.0, 2.0, 0.0)
    inst_b = Group(proto_mesh, name="Mesa B")
    inst_b.xform = xf_b

    scene.groups = [inst_a, inst_b]
    scene.selection = {inst_b}
    vp = _FakeSurfaceViewport(scene)

    # Seleção em inst_b deve resolver apenas inst_b (nunca inst_a apesar de proto_mesh compartilhada)
    targets = resolve_rotatable_groups(scene)
    assert targets == [inst_b]

    rotate_groups_with_command(targets, -90.0, vp)
    b_a = get_entity_world_bounds(inst_a)
    b_b = get_entity_world_bounds(inst_b)
    assert b_a is not None and b_b is not None
    # inst_a intacta (2.0 x 1.0 em torno de (0, 0))
    assert (b_a[1] - b_a[0]) == pytest.approx(2.0, abs=1e-4)
    assert (b_a[3] - b_a[2]) == pytest.approx(1.0, abs=1e-4)
    # inst_b girada 90° (1.0 x 2.0 em torno de (5, 2))
    assert (b_b[0] + b_b[1]) * 0.5 == pytest.approx(5.0, abs=1e-4)
    assert (b_b[2] + b_b[3]) * 0.5 == pytest.approx(2.0, abs=1e-4)
    assert (b_b[1] - b_b[0]) == pytest.approx(1.0, abs=1e-4)
    assert (b_b[3] - b_b[2]) == pytest.approx(2.0, abs=1e-4)

    vp.history.undo()
    b_b_undo = get_entity_world_bounds(inst_b)
    assert (b_b_undo[1] - b_b_undo[0]) == pytest.approx(2.0, abs=1e-4)


def test_rotate_90_led_strip_updates_endpoints_and_document_sync():
    scene = Scene()
    vp = _FakeSurfaceViewport(scene)
    lt = {
        "kind": "led_strip",
        "p1": [2.0, 1.0, 2.1],
        "p2": [4.0, 1.0, 2.1],
        "pos": [3.0, 1.0, 2.1],
        "dir": [0.0, 0.0, -1.0],
        "length": 2.0,
        "power": 300.0,
        "color": [1.0, 0.95, 0.85],
    }
    led_grp = create_light_scene_group(lt, 0)
    scene.groups = [led_grp]
    scene.selection = {led_grp}

    rotate_groups_with_command([led_grp], 90.0, vp)
    meta = led_grp.ext["trazomob_light"]
    # Ponto médio (3, 1, 2.1); p1=(2,1) -> (3,0) e p2=(4,1) -> (3,2)
    assert meta["p1"][0] == pytest.approx(3.0, abs=1e-3)
    assert meta["p1"][1] == pytest.approx(0.0, abs=1e-3)
    assert meta["p2"][0] == pytest.approx(3.0, abs=1e-3)
    assert meta["p2"][1] == pytest.approx(2.0, abs=1e-3)

    vp.history.undo()
    meta_u = led_grp.ext["trazomob_light"]
    assert meta_u["p1"][0] == pytest.approx(2.0, abs=1e-3)
    assert meta_u["p2"][0] == pytest.approx(4.0, abs=1e-3)


def test_context_menu_offers_90_deg_rotation_for_generic_object_and_skips_walls(qapp, engine_on):
    scene = Scene()
    sofa = Group(_make_box_mesh(1.0, 3.0, 1.0, 2.0, 0.0, 0.8), name="Sofa")
    wall = Group(_make_box_mesh(0.0, 4.0, 0.0, 0.15, 0.0, 2.6), name="Parede Norte")
    wall.ext = {"trazomob_wall": {}, "motion_locked": True}
    scene.groups = [sofa, wall]

    vp = _FakeSurfaceViewport(scene)
    app = SimpleNamespace(viewport=vp, _trazomob_sidebar=None)
    sidebar_stub = SimpleNamespace(focus_panel=lambda: None, load_module=lambda *_a: None)
    tool_stub = lambda: SimpleNamespace(on_activate=lambda *_a: None)

    menu_sofa = QMenu()
    build_context_menu(menu_sofa, [sofa], app, sidebar_stub, tool_stub)
    expected_menu_label = tr("🔄 Girar 90° (TrazoMob)")
    expected_cw_label = tr("↻ Girar 90° Horário")
    texts_sofa = [a.text() for a in menu_sofa.actions()]
    assert expected_menu_label in texts_sofa

    # Dispara ação de +90° pelo menu de contexto e verifica rotação real do sofá
    rot_sub = next(a.menu() for a in menu_sofa.actions() if a.text() == expected_menu_label and a.menu() is not None)
    act_cw = next(a for a in rot_sub.actions() if a.text() == expected_cw_label)
    act_cw.trigger()
    b_sofa = get_entity_world_bounds(sofa)
    assert (b_sofa[1] - b_sofa[0]) == pytest.approx(1.0, abs=1e-4)
    assert (b_sofa[3] - b_sofa[2]) == pytest.approx(2.0, abs=1e-4)

    # Parede estrutural travada não deve habilitar rotação
    assert resolve_rotatable_groups(scene, [wall]) == []
    menu_wall = QMenu()
    build_context_menu(menu_wall, [wall], app, sidebar_stub, tool_stub)
    texts_wall = [a.text() for a in menu_wall.actions()]
    assert expected_menu_label not in texts_wall


def test_rotate_multiple_mixed_objects_as_compound_command():
    scene = Scene()
    obj1 = Group(_make_box_mesh(0.0, 1.0, 0.0, 1.0, 0.0, 0.5), name="Mesa")
    obj2 = Group(_make_box_mesh(2.0, 3.0, 0.0, 1.0, 0.0, 0.5), name="Cadeira")
    scene.groups = [obj1, obj2]
    scene.selection = {obj1, obj2}
    vp = _FakeSurfaceViewport(scene)

    targets = resolve_rotatable_groups(scene)
    rotate_groups_with_command(targets, 90.0, vp)
    b1 = get_entity_world_bounds(obj1)
    b2 = get_entity_world_bounds(obj2)
    # Centro combinado é (1.5, 0.5, 0.25): [0..1]x[0..1] vira [1..2]x[-1..0], [2..3]x[0..1] vira [1..2]x[1..2]
    assert (b1[0] + b1[1]) * 0.5 == pytest.approx(1.5, abs=1e-4)
    assert (b1[2] + b1[3]) * 0.5 == pytest.approx(-0.5, abs=1e-4)
    assert (b2[0] + b2[1]) * 0.5 == pytest.approx(1.5, abs=1e-4)
    assert (b2[2] + b2[3]) * 0.5 == pytest.approx(1.5, abs=1e-4)

    # 1 único Undo desfaz ambos juntos
    vp.history.undo()
    b1_u = get_entity_world_bounds(obj1)
    assert (b1_u[0] + b1_u[1]) * 0.5 == pytest.approx(0.5, abs=1e-4)
    assert (b1_u[2] + b1_u[3]) * 0.5 == pytest.approx(0.5, abs=1e-4)
