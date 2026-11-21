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
