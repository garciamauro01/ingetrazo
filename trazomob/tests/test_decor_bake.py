# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Pré-assado de decoração: converter uma vez, inserir lendo ``.igz``.

O que se quer provar é que a conversão estrangeira **e** o ``fit`` do host
deixam de acontecer na inserção: o cache já sai orientado, dimensionado e
centrado, e ``load_component`` devolve o grupo pronto.
"""
import json
from pathlib import Path

import pytest
from PySide6.QtGui import QVector3D

from core import user_library
from core.group import Group
from core.mesh import Mesh
from trazomob.integrations import decor_bake, library_links
from views import component_loader


@pytest.fixture()
def library_root(tmp_path, monkeypatch):
    root = tmp_path / "components"
    monkeypatch.setenv("INGETRAZO_COMPONENTS", str(root))
    return root


def _grid_mesh(n: int = 12) -> Mesh:
    mesh = Mesh()
    for i in range(n):
        for j in range(n):
            x, y = i * 0.05, j * 0.05
            mesh.add_face([
                QVector3D(x, y, 0.0),
                QVector3D(x + 0.05, y, 0.0),
                QVector3D(x + 0.05, y + 0.05, 0.0),
                QVector3D(x, y + 0.05, 0.0),
            ])
    return mesh


@pytest.fixture()
def fake_import(monkeypatch):
    """Faz o papel do conversor de SKP/DAE/OBJ, contando as conversões."""
    calls = []

    def fake(path, entry):
        calls.append(Path(path))
        return Group(_grid_mesh(), name=entry.get("name") or "Decoracao")

    monkeypatch.setattr(library_links, "_reimport", fake)
    return calls


def _source(tmp_path: Path, suffix: str = ".dae", size: int = 16) -> Path:
    src = tmp_path / ("almofada" + suffix)
    src.write_bytes(b"x" * size)
    return src


def _obj(tmp_path: Path, n: int = 4) -> Path:
    """OBJ de verdade (o host transforma quads coplanares ao ler)."""
    obj = tmp_path / "tapete.obj"
    with obj.open("w", encoding="utf-8") as out:
        for i in range(n + 1):
            for j in range(n + 1):
                out.write("v %.4f %.4f 0.0\n" % (i * 0.05, j * 0.05))
        for i in range(n):
            for j in range(n):
                a = i * (n + 1) + j + 1
                out.write("f %d %d %d %d\n" % (a, a + 1, a + n + 2, a + n + 1))
    return obj


def test_bake_source_writes_cache_only_once(library_root, tmp_path, fake_import):
    src = _source(tmp_path)

    meta = decor_bake.bake_source(src)
    cached = Path(meta["cache"])

    assert cached.is_file()
    assert cached.stat().st_size > 0
    assert meta["faces"] == 144
    assert len(fake_import) == 1

    again = decor_bake.bake_source(src)
    assert again["key"] == meta["key"]
    assert again["cache"] == meta["cache"]
    assert again["faces"] == meta["faces"]
    assert len(fake_import) == 1                 # cache hit: não converteu de novo


def test_baked_cache_roundtrips_as_native_geometry(library_root, tmp_path, fake_import):
    src = _source(tmp_path, ".skp")
    meta = decor_bake.bake_source(src)

    group = decor_bake.load_baked(meta["cache"])
    assert group is not None
    assert len(group.mesh.faces) == 144
    assert not getattr(group, "children", None)  # hierarquia já foi achatada


def test_changing_the_source_gets_a_new_cache_key(library_root, tmp_path, fake_import):
    src = _source(tmp_path, ".dae", size=16)
    first = decor_bake.bake_source(src)

    src.write_bytes(b"y" * 32)                   # mtime + tamanho diferentes
    second = decor_bake.bake_source(src)

    assert second["key"] != first["key"]
    assert second["cache"] != first["cache"]
    assert len(fake_import) == 2


def test_bake_warms_the_host_chunk_cache(library_root, tmp_path, fake_import,
                                         monkeypatch):
    """O assado deixa o chunk pronto no cache do host, de forma síncrona."""
    from views.viewport import Viewport

    seen, stored = [], []
    monkeypatch.setattr(Viewport, "_CHUNK_CACHE_MIN_FACES", 1)
    monkeypatch.setattr(Viewport, "_group_chunk",
                        lambda self, group: seen.append(group) or {"nf": 144})
    monkeypatch.setattr(Viewport, "_chunk_cache_store",
                        lambda self, mesh, entry, *, sync: stored.append(sync))

    meta = decor_bake.bake_source(_source(tmp_path))

    assert meta["chunk_warmed"] is True
    assert len(seen) == 1
    assert stored == [True]                  # arquivo pronto antes de inserir


def test_older_caches_are_warmed_once_on_first_load(library_root, tmp_path,
                                                   fake_import, monkeypatch):
    meta = decor_bake.bake_source(_source(tmp_path))
    sidecar = Path(meta["cache"]).with_suffix(".json")
    saved = json.loads(sidecar.read_text(encoding="utf-8"))
    saved.pop("chunk_ready", None)
    sidecar.write_text(json.dumps(saved), encoding="utf-8")

    calls = []
    monkeypatch.setattr(decor_bake, "_warm_chunk_cache",
                        lambda group: calls.append(group) or True)

    assert decor_bake.load_baked(meta["cache"]) is not None
    assert decor_bake.load_baked(meta["cache"]) is not None
    assert len(calls) == 1
    assert json.loads(sidecar.read_text(encoding="utf-8"))["chunk_ready"]


def test_native_engine_does_not_warm_the_disk_cache(library_root, tmp_path,
                                                    fake_import, monkeypatch):
    from views import array_bake

    monkeypatch.setattr(array_bake, "can_bake", lambda mesh: True)
    meta = decor_bake.bake_source(_source(tmp_path))

    assert meta["chunk_warmed"] is False


def test_chunk_cache_store_sync_writes_before_returning(tmp_path, monkeypatch):
    from views.viewport import Viewport

    monkeypatch.setattr(Viewport, "_chunk_cache_dir",
                        staticmethod(lambda: tmp_path))
    monkeypatch.setattr(Viewport, "_chunk_cache_key",
                        staticmethod(lambda mesh, fp: "warm"))
    entry = {k: b"" for k in Viewport._CHUNK_CACHE_FIELDS}
    entry.update(nf=6000, fp=())

    Viewport._chunk_cache_store(Viewport.__new__(Viewport), None, entry,
                                sync=True)

    assert (tmp_path / "warm.chunk").is_file()


def test_fit_config_is_part_of_the_cache_key(library_root, tmp_path):
    src = _source(tmp_path)
    plain = decor_bake._norm_config(fitted=True)
    sized = decor_bake._norm_config(fitted=True, cm=[10.0, 20.0, 30.0])
    other_anchor = decor_bake._norm_config(fitted=True, anchor="center")

    assert decor_bake.cache_key(src, plain) != decor_bake.cache_key(src, sized)
    assert decor_bake.cache_key(src, plain) != decor_bake.cache_key(src, other_anchor)
    assert decor_bake.cache_key(src, plain) != decor_bake.cache_key(src)
    assert decor_bake.cache_key(src, sized) != decor_bake.cache_key(src, other_anchor)


def test_load_group_fast_uses_the_baked_cache(library_root, tmp_path, fake_import):
    """O cache já traz a matrix aplicada: qualquer matrix vira leitura direta."""
    src = _source(tmp_path, ".skp")

    for matrix in (None, (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
                   (2.0, 0.0, 0.0, 0.0, 3.0, 0.0, 0.0, 0.0, 5.0)):
        group = decor_bake.load_group_fast(src, matrix=matrix, name="Almofada")
        assert isinstance(group, Group)
        assert group.name == "Almofada"
        assert len(group.mesh.faces) == 144
    assert len(fake_import) == 3            # uma chave por configuração de matrix

    # Sem ``name``, o rótulo vem da origem — não do hash do .igz.
    assert decor_bake.load_group_fast(src, matrix=None).name == src.stem

    # Um .igz já nativo nunca é re-assado: o host lê direto.
    cached = next(p for p in (library_root / "_cache" / "baked").rglob("*.igz"))
    assert decor_bake.load_group_fast(cached, matrix=None) is None
    assert len(fake_import) == 3


def test_register_bakes_when_adding_to_library(library_root, tmp_path, fake_import):
    src = _source(tmp_path, ".skp")

    entry = user_library.register(src, managed=False, nombre="Almofada")
    source = decor_bake.source_of(entry)
    assert source is not None
    config = decor_bake.config_for_entry(entry)
    assert config["fitted"] is True
    assert decor_bake.bake_path(source, config).is_file()
    assert len(fake_import) == 1                 # pago no cadastro, não na inserção

    # A inserção pela biblioteca lê o .igz assado, sem converter de novo.
    loaded = component_loader.load_component(entry, strict=True)
    assert loaded is not None
    assert len(loaded.group.mesh.faces) == 144
    assert len(fake_import) == 1


def test_load_component_returns_the_prefitted_group(library_root, tmp_path):
    """A inserção não materializa nem re-centraliza a malha: o cache já fez isso."""
    obj = _obj(tmp_path)
    original = component_loader.load_component
    entry = user_library.register(obj, managed=False, nombre="Tapete")

    expected = original(entry, strict=True)
    actual = component_loader.load_component(entry, strict=True)

    assert len(actual.group.mesh.faces) == len(expected.group.mesh.faces)
    assert component_loader.bounds(actual.group) == pytest.approx(
        component_loader.bounds(expected.group))
    assert actual.group.name == "Tapete"
    assert actual.path == decor_bake.source_of(entry)


def test_baked_geometry_preserves_the_host_matrix(library_root, tmp_path):
    """A matrix de unidade/escala continua idêntica à do host."""
    obj = _obj(tmp_path)
    original = component_loader.load_group
    matrix = (2.0, 0.0, 0.0, 0.0, 3.0, 0.0, 0.0, 0.0, 5.0)

    cold = original(obj, matrix=matrix, name="Tapete")
    warm = component_loader.load_group(obj, matrix=matrix, name="Tapete")

    assert component_loader.bounds(cold) == pytest.approx(
        component_loader.bounds(warm))
    assert len(warm.mesh.faces) == len(cold.mesh.faces)


def test_non_decoration_formats_are_ignored(library_root, tmp_path, fake_import):
    native = tmp_path / "tapete.igz"
    native.write_bytes(b"igz")
    assert decor_bake.bake_source(native) is None
    assert decor_bake.load_for_entry({"origen": str(native)}) is None
    assert not fake_import
