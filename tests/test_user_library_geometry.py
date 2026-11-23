# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
#"Editar geometria": salvar a malha editada na cena de volta na biblioteca."""
from __future__ import annotations

import pytest

from core import user_library
from core.group import Group
from core.scene import Scene
from trazomob.integrations import library_links
from views import component_loader


@pytest.fixture
def library(tmp_path, monkeypatch):
    root = tmp_path / "biblioteca"
    monkeypatch.setenv("INGETRAZO_COMPONENTS", str(root))
    return root


def _obj(path, faces: int) -> None:
    lines = ["v 0 0 0", "v 1 0 0", "v 1 1 0", "v 0 1 0"]
    if faces == 1:
        lines.append("f 1 2 3 4")
    else:
        lines.extend(["v 0 0 1", "f 1 2 3", "f 1 4 5"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_replace_geometry_keeps_id_and_updates_definition(library, tmp_path):
    original = tmp_path / "original.obj"
    _obj(original, 1)
    entry = user_library.register(original, nombre="Peça")

    edited = tmp_path / "editada.obj"
    _obj(edited, 2)
    group = component_loader.load_group(edited)

    updated = user_library.replace_geometry(entry["id"], group)
    assert updated is not None
    assert updated["id"] == entry["id"]
    assert updated["nombre"] == "Peça"
    assert updated["modo"] == "gerenciado"
    assert updated["archivo"] == f"models/{entry['id']}/{entry['id']}.igz"

    path = user_library.resolve(updated)
    assert path is not None and path.is_file()
    loaded = component_loader.load_component(updated, strict=True)
    assert loaded is not None
    assert len(loaded.group.mesh.faces) == 2
    assert user_library.thumbnail(updated) is not None


def test_replace_geometry_rejects_empty_group(library, tmp_path):
    source = tmp_path / "original.obj"
    _obj(source, 1)
    entry = user_library.register(source, nombre="Peça")

    with pytest.raises(ValueError, match="não tem geometria"):
        user_library.replace_geometry(entry["id"], Group(name="Vazia"))


def test_replace_geometry_rejects_placeholder_frame(library, tmp_path):
    source = tmp_path / "original.obj"
    _obj(source, 1)
    entry = user_library.register(source, nombre="Peça")

    stub = Group(name="Stub")
    stub.mesh = library_links._placeholder_mesh({
        "library": "user",
        "id": entry["id"],
        "entry": {"cm": [100.0, 50.0, 80.0]},
    })

    with pytest.raises(ValueError, match="vínculo ausente"):
        user_library.replace_geometry(entry["id"], stub)


def test_refresh_user_groups_updates_every_instance(library, tmp_path):
    source = tmp_path / "original.obj"
    _obj(source, 1)
    entry = user_library.register(source, nombre="Peça")

    edited = tmp_path / "editada.obj"
    _obj(edited, 2)
    group = component_loader.load_group(edited)
    updated = user_library.replace_geometry(entry["id"], group)
    assert updated is not None

    scene = Scene()
    for _ in range(2):
        instance = Group(name="Peça")
        instance.mesh = component_loader.load_group(source).mesh
        library_links.set_link(
            instance, library_links.link_from_entry(entry, library="user"))
        scene.groups.append(instance)

    count = library_links.refresh_user_groups(scene, entry["id"], updated)
    assert count == 2
    for instance in scene.groups:
        assert len(instance.mesh.faces) == 2
        assert library_links.link_of(instance)["rev"] == \
            library_links.link_from_entry(updated, library="user")["rev"]


def test_replace_geometry_and_scene_editor_preserve_pbr_materials(
    library, tmp_path
):
    """Editar PBR na cena + Save geometry grava PBR na ficha, no .igz e na próxima inserção."""
    import os
    from PySide6.QtWidgets import QApplication
    from trazomob.ui.material_editor_dialog import MaterialEditorDialog

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    assert app is not None

    source = tmp_path / "sofa.obj"
    source.write_text(
        "v 0 0 0\nv 2 0 0\nv 2 1 0\nv 0 1 0\nf 1 2 3 4\n",
        encoding="utf-8",
    )
    entry = user_library.register(source, nombre="Sofá")
    loaded = component_loader.load_component(entry, strict=True)
    placed = loaded.group
    placed.mesh.faces[0].attrs = {"mat": "Tecido_Sofa", "color": (0.6, 0.5, 0.4)}
    library_links.mark_built_component(placed, entry, library="user")

    scene = Scene()
    scene.groups.append(placed)

    dlg = MaterialEditorDialog(scene)
    try:
        idx_tecido = dlg.cb_type.findData("tecido")
        assert dlg.select_material_by_name("Tecido_Sofa") is True
        dlg.cb_type.setCurrentIndex(idx_tecido)
        dlg._save_and_close()
    finally:
        dlg.close()

    assert placed.ext["trazomob_render_materials"]["Tecido_Sofa"]["type"] == "tecido"

    updated = user_library.replace_geometry(entry["id"], placed)
    assert updated is not None
    assert updated["render_materials"]["Tecido_Sofa"]["type"] == "tecido"
    assert user_library.get(entry["id"])["render_materials"]["Tecido_Sofa"]["type"] == "tecido"

    # Reabrindo o componente em uma nova cena (ou sem depender do cache), o PBR já vem pronto
    reloaded = component_loader.load_component(user_library.get(entry["id"]), strict=True)
    assert reloaded is not None
    assert reloaded.group.ext["trazomob_render_materials"]["Tecido_Sofa"]["type"] == "tecido"
    assert "igz_link" not in reloaded.group.ext

    # Instâncias existentes na cena também recebem o PBR atualizado no refresh
    count = library_links.refresh_user_groups(scene, entry["id"], updated)
    assert count == 1
    assert placed.ext["trazomob_render_materials"]["Tecido_Sofa"]["type"] == "tecido"


def test_component_thumbnail_dense_mesh_is_solid_and_preserves_deferred_mesh(tmp_path, monkeypatch):
    """Miniatura de malha densa não pode ficar furada (efeito raio-X) e preserva DeferredMesh."""
    from PySide6.QtGui import QImage, QVector3D
    from PySide6.QtWidgets import QApplication
    from core import _native
    from core.group import Group
    from core.mesh import DeferredMesh, Mesh
    from core.scene import Scene
    from formats import igz
    from views import component_thumbs

    QApplication.instance() or QApplication([])
    monkeypatch.setattr(_native, "wanted", lambda: True)

    tex_path = tmp_path / "tecido_azul.png"
    tex_img = QImage(16, 16, QImage.Format_RGB32)
    tex_img.fill(0xFF2050A0)
    assert tex_img.save(str(tex_path), "PNG")

    # Cria caixa densamente subdividida (> 4000 faces) como um estofado detalhado
    mesh = Mesh()
    n = 34  # 6 * 34 * 34 = 6936 faces
    step = 1.0 / n
    mat_attrs = {"texture": {"path": str(tex_path), "sw": 1.0, "sh": 1.0}}

    for face_defs in (
        lambda u, v, d: [QVector3D(1.0, u, v), QVector3D(1.0, u + d, v), QVector3D(1.0, u + d, v + d), QVector3D(1.0, u, v + d)],
        lambda u, v, d: [QVector3D(0.0, u, v), QVector3D(0.0, u, v + d), QVector3D(0.0, u + d, v + d), QVector3D(0.0, u + d, v)],
        lambda u, v, d: [QVector3D(u, 0.0, v), QVector3D(u + d, 0.0, v), QVector3D(u + d, 0.0, v + d), QVector3D(u, 0.0, v + d)],
        lambda u, v, d: [QVector3D(u, 1.0, v), QVector3D(u, 1.0, v + d), QVector3D(u + d, 1.0, v + d), QVector3D(u + d, 1.0, v)],
        lambda u, v, d: [QVector3D(u, v, 1.0), QVector3D(u + d, v, 1.0), QVector3D(u + d, v + d, 1.0), QVector3D(u, v + d, 1.0)],
        lambda u, v, d: [QVector3D(u, v, 0.0), QVector3D(u, v + d, 0.0), QVector3D(u + d, v + d, 0.0), QVector3D(u + d, v, 0.0)],
    ):
        for iu in range(n):
            for iv in range(n):
                f = mesh.add_face(face_defs(iu * step, iv * step, step))
                f.attrs = dict(mat_attrs)

    scene = Scene()
    scene.groups.append(Group(mesh, name="Pufe Denso"))
    igz_path = tmp_path / "pufe.igz"
    igz.save_scene(scene, igz_path, binary=True)

    loaded = Scene()
    igz.load_into(loaded, igz_path)
    grp = loaded.groups[0]
    assert type(grp.mesh) is DeferredMesh

    component_thumbs._cache.clear()
    component_thumbs._tex_rgb_cache.clear()
    pm = component_thumbs.thumbnail(grp, size=128)
    assert type(grp.mesh) is DeferredMesh

    img = pm.toImage()
    # Centro da projeção do cubo 1x1x1 precisa estar sólido e azulado (cor real da textura)
    center_px = img.pixelColor(64, 64)
    assert center_px.alpha() >= 250
    assert center_px.blue() > center_px.red()

    holes_inside = sum(
        1 for y in range(52, 76) for x in range(52, 76)
        if img.pixelColor(x, y).alpha() < 240
    )
    assert holes_inside == 0
