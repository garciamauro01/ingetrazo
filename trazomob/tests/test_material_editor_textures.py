# SPDX-License-Identifier: GPL-3.0-or-later
"""Testes para extração e exibição de texturas no MaterialEditorDialog."""
import pytest
from PySide6.QtGui import QVector3D
from core.scene import Scene
from core.group import Group
from core.mesh import Mesh
from trazomob.ui.material_editor_dialog import extract_scene_materials


def test_extract_scene_materials_group_texture(tmp_path):
    # Cria arquivo falso de textura
    tex_file = tmp_path / "tijolo_vista.png"
    tex_file.write_bytes(b"\x89PNG\r\n\x1a\n")

    scene = Scene()
    m = Mesh()
    f = m.add_face([QVector3D(0, 0, 0), QVector3D(1, 0, 0), QVector3D(1, 1, 0), QVector3D(0, 1, 0)])

    # Parede (grupo) com material de textura atribuído
    wall_group = Group(m, name="Parede 1")
    wall_group.material = {
        "texture": {"path": str(tex_file), "sw": 1.0, "sh": 1.0},
        "mat": "Tijolo a Vista"
    }
    scene.groups.append(wall_group)

    mats = extract_scene_materials(scene)
    names = [m["name"] for m in mats]
    assert "Tijolo a Vista" in names

    item = next(m for m in mats if m["name"] == "Tijolo a Vista")
    assert item["texture_path"] == str(tex_file)
    assert item["display_name"] == "Tijolo a Vista"


def test_extract_scene_materials_face_texture(tmp_path):
    tex_file = tmp_path / "madeira_nogueira.jpg"
    tex_file.write_bytes(b"\xff\xd8\xff")

    scene = Scene()
    m = Mesh()
    f = m.add_face([QVector3D(0, 0, 0), QVector3D(1, 0, 0), QVector3D(1, 1, 0), QVector3D(0, 1, 0)])
    f.attrs["texture"] = {"path": str(tex_file)}
    # Sem mat explícito: deve usar o stem do arquivo
    g = Group(m, name="Módulo 1")
    scene.groups.append(g)

    mats = extract_scene_materials(scene)
    names = [m["name"] for m in mats]
    assert "madeira_nogueira" in names

    item = next(m for m in mats if m["name"] == "madeira_nogueira")
    assert item["texture_path"] == str(tex_file)


def test_material_highlight_is_drawn_in_world_coordinates(qapp):
    """O destaque deve seguir o xform do grupo, não a malha local."""
    from types import SimpleNamespace

    from PySide6.QtGui import QMatrix4x4
    from trazomob.ui.material_editor_dialog import MaterialEditorDialog

    scene = Scene()
    mesh = Mesh()
    face = mesh.add_face([QVector3D(0, 0, 0), QVector3D(1, 0, 0),
                          QVector3D(1, 1, 0)])
    face.attrs = {"mat": "Vermelho", "color": (1.0, 0.0, 0.0)}
    group = Group(mesh, name="Bloco")
    moved = QMatrix4x4()
    moved.translate(10.0, 0.0, 0.0)
    group.xform = moved
    scene.groups.append(group)

    class Viewport:
        def world_to_pixel(self, point):
            return (point.x(), point.y())

    class Painter:
        def __init__(self):
            self.polygons = []

        def save(self):
            pass

        def restore(self):
            pass

        def setRenderHint(self, *_args):
            pass

        def setPen(self, *_args):
            pass

        def setBrush(self, *_args):
            pass

        def drawPolygon(self, polygon):
            self.polygons.append(polygon)

    dialog = SimpleNamespace(_highlight_active=True, _current_mat="Vermelho",
                             scene=scene, _group=None)
    painter = Painter()
    MaterialEditorDialog._draw_material_highlight(dialog, Viewport(), painter)

    assert len(painter.polygons) == 1
    xs = [point.x() for point in painter.polygons[0]]
    assert min(xs) == pytest.approx(10.0)
    assert max(xs) == pytest.approx(11.0)

    # Aberto sobre um grupo específico: mesma posição, sem varrer a cena inteira.
    dialog._group = group
    group_painter = Painter()
    MaterialEditorDialog._draw_material_highlight(dialog, Viewport(), group_painter)
    assert len(group_painter.polygons) == 1
    xs = [point.x() for point in group_painter.polygons[0]]
    assert min(xs) == pytest.approx(10.0)
