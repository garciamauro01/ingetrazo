# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Exportação/importação portátil da biblioteca do usuário."""
from __future__ import annotations

import json
import zipfile

import pytest

from core import user_library


@pytest.fixture
def library(tmp_path, monkeypatch):
    root = tmp_path / "biblioteca"
    monkeypatch.setenv("INGETRAZO_COMPONENTS", str(root))
    return root


def _obj(path) -> None:
    path.write_text("v 0 0 0\nv 1 0 0\nv 1 1 0\nf 1 2 3\n", encoding="utf-8")


def _source_bundle(library, tmp_path):
    source = tmp_path / "original" / "geladeira.obj"
    source.parent.mkdir(parents=True)
    _obj(source)
    entry = user_library.register(
        source, nombre="Geladeira", categoria="Cozinha", marca="Brastemp")
    bundle = tmp_path / "biblioteca.zip"
    stats = user_library.export_bundle(bundle)
    return entry, bundle, stats


def test_export_is_self_contained_without_absolute_paths(library, tmp_path):
    entry, bundle, stats = _source_bundle(library, tmp_path)
    assert stats["entries"] == 1
    assert stats["skipped"] == 0

    with zipfile.ZipFile(bundle) as zf:
        names = zf.namelist()
        assert "library.json" in names
        assert "bundle.json" in names
        assert entry["archivo"] in names
        manifest = json.loads(zf.read("library.json").decode("utf-8"))
        exported = manifest["componentes"][0]
        assert exported["archivo"] == entry["archivo"]
        assert exported["origen"] == "geladeira.obj"
        assert ":\\" not in exported["origen"]
        assert all(not name.startswith("/") and ".." not in name
                   for name in names)


def test_import_merge_adds_missing_and_keeps_existing(library, tmp_path,
                                                       monkeypatch):
    entry, bundle, _stats = _source_bundle(library, tmp_path)

    other = tmp_path / "outra-maquina"
    monkeypatch.setenv("INGETRAZO_COMPONENTS", str(other))
    result = user_library.import_bundle(bundle, mode="merge")
    assert result["added"] == 1
    imported = user_library.index()[0]
    assert imported["id"] == entry["id"]
    assert imported["nombre"] == "Geladeira"
    assert user_library.resolve(imported) is not None
    assert user_library.resolve(imported).is_file()

    # Um segundo pacote com o mesmo id não pode sobrescrever o que já existe.
    monkeypatch.setenv("INGETRAZO_COMPONENTS", str(library))
    user_library.update(entry["id"], nombre="Nome diferente")
    changed = tmp_path / "alterado.zip"
    user_library.export_bundle(changed)
    monkeypatch.setenv("INGETRAZO_COMPONENTS", str(other))
    result = user_library.import_bundle(changed, mode="merge")
    assert result["added"] == 0
    assert result["skipped"] == 1
    assert user_library.index()[0]["nombre"] == "Geladeira"


def test_import_replace_restores_exactly_the_bundle(library, tmp_path,
                                                     monkeypatch):
    _entry, bundle, _stats = _source_bundle(library, tmp_path)

    local = tmp_path / "local.obj"
    _obj(local)
    user_library.register(local, nombre="Local")

    other = tmp_path / "destino"
    monkeypatch.setenv("INGETRAZO_COMPONENTS", str(other))
    own = tmp_path / "proprio.obj"
    _obj(own)
    user_library.register(own, nombre="Próprio")

    result = user_library.import_bundle(bundle, mode="replace")
    assert result["mode"] == "replace"
    entries = user_library.index()
    assert [e["nombre"] for e in entries] == ["Geladeira"]
    assert user_library.resolve(entries[0]).is_file()


def test_import_rejects_path_traversal(library, tmp_path, monkeypatch):
    bad = tmp_path / "ruim.zip"
    bundle = {
        "format": user_library.BUNDLE_FORMAT,
        "version": user_library.BUNDLE_VERSION,
        "library_version": user_library.VERSION,
        "unidad": "m",
        "entries": 1,
    }
    manifest = {"version": user_library.VERSION, "unidad": "m",
                "componentes": [{"id": "good", "modo": "gerenciado",
                                 "archivo": "models/good/good.obj"}]}
    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr(user_library.BUNDLE_MANIFEST,
                    json.dumps(bundle, ensure_ascii=False))
        zf.writestr(user_library.MANIFEST,
                    json.dumps(manifest, ensure_ascii=False))
        zf.writestr("models/good/good.obj", "v 0 0 0\n")
        zf.writestr("models/../evil.obj", "malicioso")

    other = tmp_path / "seguro"
    monkeypatch.setenv("INGETRAZO_COMPONENTS", str(other))
    with pytest.raises(ValueError, match="arquivo inválido"):
        user_library.import_bundle(bad, mode="merge")
    assert not (other / "evil.obj").exists()


def test_import_rejects_unknown_archive(library, tmp_path, monkeypatch):
    other = tmp_path / "vazio"
    monkeypatch.setenv("INGETRAZO_COMPONENTS", str(other))
    random = tmp_path / "qualquer.zip"
    with zipfile.ZipFile(random, "w") as zf:
        zf.writestr("ler.txt", "não é uma biblioteca")
    with pytest.raises(ValueError, match="não é um pacote"):
        user_library.import_bundle(random)


def test_bundle_export_and_import_preserve_pbr_materials(
    library, tmp_path, monkeypatch
):
    from views import component_loader

    source = tmp_path / "cadeira.obj"
    _obj(source)
    pbr = {
        "Madeira_Carvalho": {
            "type": "madeira",
            "sub_type": "MDF Madeirado",
            "roughness": 0.35,
            "specular": 0.5,
            "bump": 0.03,
        }
    }
    entry = user_library.register(source, nombre="Cadeira", render_materials=pbr)
    bundle = tmp_path / "biblioteca_pbr.zip"
    stats = user_library.export_bundle(bundle)
    assert stats["entries"] == 1

    other = tmp_path / "outra-maquina-pbr"
    monkeypatch.setenv("INGETRAZO_COMPONENTS", str(other))
    res = user_library.import_bundle(bundle, mode="merge")
    assert res["added"] == 1

    imported = user_library.get(entry["id"])
    assert imported is not None
    assert imported["render_materials"] == pbr

    loaded = component_loader.load_component(imported, strict=True)
    assert loaded is not None
    assert loaded.group.ext["trazomob_render_materials"] == pbr
