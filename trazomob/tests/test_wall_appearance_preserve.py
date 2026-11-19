# SPDX-License-Identifier: GPL-3.0-or-later
"""Regressao: Concluir na planta 2D nao pode apagar textura/cor de paredes, pisos e tetos."""
import pytest
from PySide6.QtGui import QVector3D

from core.scene import Scene


@pytest.fixture
def vp():
    scene = Scene()

    class DummyViewport:
        def __init__(self, sc):
            self.scene = sc
            self.history = None

        def update(self):
            pass

        def flash_status(self, msg):
            pass

        def notify_scene_changed(self):
            pass

    return DummyViewport(scene)


def _make_closed_room(dlg):
    dlg.graph.add_segment(0.0, 0.0, 4.0, 0.0)
    dlg.graph.add_segment(4.0, 0.0, 4.0, 3.0)
    dlg.graph.add_segment(4.0, 3.0, 0.0, 3.0)
    dlg.graph.add_segment(0.0, 3.0, 0.0, 0.0)
    dlg.chk_floor.setChecked(True)
    dlg.chk_ceiling.setChecked(True)


def _paint_all(scene, texture):
    for g in scene.groups:
        if not getattr(g, "mesh", None):
            continue
        for f in g.mesh.faces:
            f.attrs["texture"] = dict(texture)
            f.attrs["color"] = (0.85, 0.25, 0.10)
            f.attrs["mat"] = "Pintura teste"


def _textures(scene):
    return [
        f.attrs.get("texture")
        for g in scene.groups if getattr(g, "mesh", None)
        for f in g.mesh.faces
    ]


def test_concluir_preserva_textura_em_paredes_piso_e_teto(vp):
    """Apos aplicar textura e clicar em Concluir novamente, nada pode se perder."""
    from trazomob.wall.floorplan_dialog import WallFloorplanDialog

    dlg = WallFloorplanDialog(vp)
    _make_closed_room(dlg)
    dlg._build_3d_and_close()

    scene = vp.scene
    groups_antes = list(scene.groups)
    assert len(groups_antes) >= 3

    kinds = set()
    for g in groups_antes:
        ext = getattr(g, "ext", None) or {}
        if ext.get("trazomob_floor"):
            kinds.add("floor")
        elif ext.get("trazomob_ceiling"):
            kinds.add("ceiling")
        elif ext.get("trazomob_wall"):
            kinds.add("wall")
    assert {"wall", "floor", "ceiling"} <= kinds

    texture = {"path": "pintura_teste.jpg", "uvw": (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)}
    _paint_all(scene, texture)

    # Reabre o editor e clica em Concluir novamente.
    dlg2 = WallFloorplanDialog(vp)
    dlg2.chk_floor.setChecked(True)
    dlg2.chk_ceiling.setChecked(True)
    dlg2._build_3d_and_close()

    textures = _textures(scene)
    assert textures, "nenhuma face conservou textura"
    assert all(t == texture for t in textures), (
        f"{sum(t != texture for t in textures)} faces perderam a textura")

    cores = [
        f.attrs.get("color")
        for g in scene.groups if getattr(g, "mesh", None)
        for f in g.mesh.faces
    ]
    assert all(c == (0.85, 0.25, 0.10) for c in cores), "cor das paredes/pisos/tetos se perdeu"


def test_paredes_novas_sao_brancas_com_tinta_acetinada(vp):
    """Paredes geradas pela planta 2D ja nascem brancas com finish satin."""
    from trazomob.wall.floorplan_dialog import WallFloorplanDialog
    from trazomob.wall.paint_catalog import DEFAULT_WALL_PAINT

    dlg = WallFloorplanDialog(vp)
    dlg.graph.add_segment(0.0, 0.0, 4.0, 0.0)
    dlg._build_3d_and_close()

    walls = [
        g for g in vp.scene.groups
        if ((getattr(g, "ext", None) or {}).get("trazomob_wall"))
    ]
    assert walls
    for w in walls:
        assert w.material is not None
        assert w.material["color"] == [1.0, 1.0, 1.0]
        assert w.material["mat"] == DEFAULT_WALL_PAINT

    mat = vp.scene.materials.get(DEFAULT_WALL_PAINT)
    assert mat is not None
    assert mat.finish == "satin"


def test_copy_face_appearance_preserva_material_do_grupo():
    """O material pintado pelo usuario vence ate o default branco acetinado."""
    from core.group import Group
    from core.mesh import Mesh
    from trazomob.wall.mesh_builder import WallMeshBuilder
    from trazomob.wall.paint_catalog import default_wall_material

    tri = [QVector3D(0, 0, 0), QVector3D(1, 0, 0), QVector3D(0, 1, 0)]
    src = Group(Mesh(), name="origem")
    src.mesh.add_face(list(tri))
    src.mesh.faces[0].attrs["texture"] = {"path": "x.jpg"}
    src.material = {"mat": "Pintura azul do usuario", "color": [0.0, 0.0, 1.0]}

    dst = Group(Mesh(), name="destino")
    dst.mesh.add_face(list(tri))
    dst.material = default_wall_material()

    assert WallMeshBuilder.copy_face_appearance(src, dst) is True
    assert dst.mesh.faces[0].attrs["texture"] == {"path": "x.jpg"}
    assert dst.material == src.material
