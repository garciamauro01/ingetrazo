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
