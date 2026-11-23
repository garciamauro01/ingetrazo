# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez and IngeTrazo contributors.
"""The user's own component library: every import is copied into it.

The point of these tests is the PROMISE, not the JSON: an import must survive
moving the original, no entry may point back to the file the user imported
from, and nothing the manifest says may read or write outside the library.
"""
from __future__ import annotations

import json

import pytest

from core import user_library


@pytest.fixture
def library(tmp_path, monkeypatch):
    """A library of its own, so the developer's real one is never touched."""
    root = tmp_path / "biblioteca"
    monkeypatch.setenv("INGETRAZO_COMPONENTS", str(root))
    return root


def _obj(path, *, mtllib=None):
    lines = ["v 0 0 0", "v 1 0 0", "v 1 1 0", "v 0 1 0",
             "f 1 2 3 4"]
    text = "\n".join(lines) + "\n"
    if mtllib:
        text = f"mtllib {mtllib}\n" + text
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Every import is managed
# ---------------------------------------------------------------------------

def test_import_copy_survives_deleting_the_original(library, tmp_path):
    src = _obj(tmp_path / "geladeira.obj")
    entry = user_library.register(src, nombre="Geladeira")

    assert entry["modo"] == "gerenciado"
    original = user_library.resolve(entry)
    assert original is not None
    assert original.is_file()
    # Inside the library, not the folder the user imported it from.
    assert library.resolve() in original.resolve().parents
    assert entry["archivo"] == original.relative_to(
        library.resolve()).as_posix()

    src.unlink()
    still_there = user_library.resolve(entry)
    assert still_there is not None and still_there.is_file()


def test_import_never_indexes_the_original_in_place(library, tmp_path):
    src = _obj(tmp_path / "fogao.obj")
    entry = user_library.register(src, nombre="Fogão")
    copied = user_library.resolve(entry)

    assert entry["modo"] == "gerenciado"
    assert copied is not None and copied.resolve() != src.resolve()
    assert library.resolve() in copied.resolve().parents

    assert user_library.remove(entry["id"]) is True
    assert not copied.exists()
    assert src.is_file()


def test_remove_deletes_the_library_copy_but_not_the_original(library,
                                                              tmp_path):
    src = _obj(tmp_path / "forno.obj")
    entry = user_library.register(src, nombre="Forno")
    copy = user_library.resolve(entry)

    assert user_library.remove(entry["id"]) is True
    assert not copy.exists()
    assert src.is_file()
    assert user_library.get(entry["id"]) is None


def test_missing_library_copy_is_reported_not_dropped(library, tmp_path):
    src = _obj(tmp_path / "some.obj")
    entry = user_library.register(src, nombre="Some")
    copy = user_library.resolve(entry)
    assert copy is not None
    copy.unlink()

    assert user_library.resolve(entry) is None
    assert user_library.missing(entry) is True
    # The ficha is still there: the user can re-import or remove it.
    assert user_library.get(entry["id"]) is not None
    assert user_library.index()[0]["nombre"] == "Some"


# ---------------------------------------------------------------------------
# Sidecars and paths
# ---------------------------------------------------------------------------

def test_managed_obj_brings_its_mtl_and_textures(library, tmp_path):
    (tmp_path / "tex.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    (tmp_path / "mat.mtl").write_text(
        "newmtl Body\nKd 0.9 0.9 0.9\nmap_Kd tex.png\n", encoding="utf-8")
    src = _obj(tmp_path / "brastemp.obj", mtllib="mat.mtl")

    entry = user_library.register(src, nombre="Brastemp")
    folder = user_library.resolve(entry).parent

    assert (folder / "mat.mtl").is_file()
    assert (folder / "tex.png").is_file()


def test_managed_path_cannot_escape_the_library(library, tmp_path):
    library.mkdir(parents=True)
    outside = _obj(tmp_path / "fora.obj")
    (library / user_library.MANIFEST).write_text(json.dumps({
        "version": 1,
        "componentes": [{
            "id": "mau", "nombre": "Mau", "modo": "gerenciado",
            "archivo": "../fora.obj",
        }],
    }), encoding="utf-8")

    entry = user_library.get("mau")
    assert entry is not None
    assert user_library.resolve(entry) is None
    assert outside.is_file()


def test_index_ignores_entries_with_unsafe_ids(library):
    library.mkdir(parents=True)
    (library / user_library.MANIFEST).write_text(json.dumps({
        "version": 1,
        "componentes": [
            {"id": "ok-1", "nombre": "Bom"},
            {"id": "../mau", "nombre": "Mau"},
            {"id": "", "nombre": "Vazio"},
            {"nombre": "Sem id"},
        ],
    }), encoding="utf-8")

    ids = [e["id"] for e in user_library.index()]
    assert ids == ["ok-1"]


# ---------------------------------------------------------------------------
# Metadata, facets, folders
# ---------------------------------------------------------------------------

def test_update_edits_metadata_but_not_identity(library, tmp_path):
    src = _obj(tmp_path / "x.obj")
    entry = user_library.register(src, nombre="Antigo")

    updated = user_library.update(
        entry["id"], nombre="Novo", marca="Electrolux", tipo="Geladeira",
        tags=["inox", " "], cm=[70, 65, 180], y_up=True,
        id="outro", archivo="/etc/passwd", modo="gerenciado")

    assert updated["nombre"] == "Novo"
    assert updated["marca"] == "Electrolux"
    assert updated["tags"] == ["inox"]
    assert updated["cm"] == [70, 65, 180]
    assert updated["y_up"] is True
    # Identity and the file it points at were not in the editable set.
    assert updated["id"] == entry["id"]
    assert updated["archivo"] == entry["archivo"]
    assert updated["modo"] == "gerenciado"
    # And it persisted.
    assert user_library.get(entry["id"])["nombre"] == "Novo"


def test_registering_the_same_file_twice_updates_instead_of_duplicating(
        library, tmp_path):
    src = _obj(tmp_path / "unico.obj")
    first = user_library.register(src, nombre="Um")
    again = user_library.register(src, nombre="Dois")

    assert again["id"] == first["id"]
    assert len(user_library.index()) == 1
    assert user_library.get(first["id"])["nombre"] == "Dois"
    assert again["modo"] == "gerenciado"


def test_reimport_keeps_one_managed_copy(library, tmp_path):
    src = _obj(tmp_path / "promover.obj")
    first = user_library.register(src, nombre="Um")
    again = user_library.register(src, nombre="Um")

    assert again["id"] == first["id"]
    assert again["modo"] == "gerenciado"
    copy = user_library.resolve(again)
    assert copy is not None
    assert library.resolve() in copy.resolve().parents
    assert len(user_library.index()) == 1


def test_legacy_reference_is_promoted_on_reimport(library, tmp_path):
    src = _obj(tmp_path / "antigo.obj")
    library.mkdir(parents=True)
    (library / user_library.MANIFEST).write_text(json.dumps({
        "version": 1,
        "componentes": [{
            "id": "antigo-1", "nombre": "Antigo", "modo": "referencia",
            "archivo": str(src), "origen": str(src),
        }],
    }), encoding="utf-8")

    promoted = user_library.register(src, nombre="Antigo")

    assert promoted["id"] == "antigo-1"
    assert promoted["modo"] == "gerenciado"
    path = user_library.resolve(promoted)
    assert path is not None
    assert library.resolve() in path.resolve().parents


def test_facets_count_types_brands_and_tags(library, tmp_path):
    user_library.register(_obj(tmp_path / "a.obj"), nombre="A",
                          tipo="Geladeira", marca="Brastemp",
                          tags=["inox"])
    user_library.register(_obj(tmp_path / "b.obj"), nombre="B",
                          tipo="Geladeira", marca="Brastemp",
                          tags=["inox", "french-door"])
    user_library.register(_obj(tmp_path / "c.obj"), nombre="C",
                          tipo="Fogão", marca="Electrolux")

    facets = user_library.facets()
    assert facets["tipos"]["Geladeira"] == 2
    assert facets["marcas"]["Brastemp"] == 2
    assert facets["marcas"]["Electrolux"] == 1
    assert facets["tags"]["inox"] == 2


def test_add_folder_copies_every_model_and_tags_the_folders(library,
                                                            tmp_path):
    branch = tmp_path / "Geladeiras" / "Brastemp"
    branch.mkdir(parents=True)
    _obj(branch / "BRM54.obj")
    _obj(tmp_path / "Geladeiras" / "outra.obj")

    added = user_library.add_folder(tmp_path / "Geladeiras")

    assert {e["nombre"] for e in added} == {"BRM54", "outra"}
    for entry in added:
        assert entry["modo"] == "gerenciado"
        path = user_library.resolve(entry)
        assert path is not None
        assert library.resolve() in path.resolve().parents
    by_name = {e["nombre"]: e for e in added}
    assert "Brastemp" in by_name["BRM54"]["tags"]
    assert "outra" not in by_name["BRM54"]["tags"]


def test_thumbnails_live_under_the_library(library, tmp_path):
    entry = user_library.register(_obj(tmp_path / "com.obj"))
    assert user_library.thumbnail(entry) is None
    path = user_library.thumbnail_path(entry)
    assert path == library / "thumbs" / f"{entry['id']}.png"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
    assert user_library.thumbnail(entry) == path


def test_register_and_update_preserve_render_materials(library, tmp_path):
    from views import component_loader

    src = _obj(tmp_path / "pia.obj")
    entry = user_library.register(
        src,
        nombre="Pia",
        render_materials={"mat_10_10_10": {"type": "metal"}},
    )

    assert entry["render_materials"] == {"mat_10_10_10": {"type": "metal"}}
    assert user_library.get(entry["id"])["render_materials"] == {
        "mat_10_10_10": {"type": "metal"}
    }

    updated = user_library.update(
        entry["id"],
        render_materials={"mat_20_20_20": {"type": "vidro"}},
    )
    assert updated is not None
    assert updated["render_materials"] == {"mat_20_20_20": {"type": "vidro"}}
    assert user_library.get(entry["id"])["render_materials"] == {
        "mat_20_20_20": {"type": "vidro"}
    }

    loaded = component_loader.load_component(updated, strict=True)
    assert loaded is not None
    assert loaded.group.ext["trazomob_render_materials"] == {
        "mat_20_20_20": {"type": "vidro"}
    }
