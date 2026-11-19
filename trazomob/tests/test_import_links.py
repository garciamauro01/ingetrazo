# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Importação direta como vínculo: o documento guarda a referência.

O caso real: decoração que entra arrastando um ``.skp``/``.dae`` não passa
pela biblioteca, então não era marcada — e era justamente ela que enchia o
``.igz``. Aqui o grupo importado é processado uma vez para um ``.igz`` no
cache (binário) e o documento guarda só ``{path, cache, rev}`` + ``xform``.
"""
import json
import types
from pathlib import Path

import pytest
from PySide6.QtGui import QMatrix4x4, QVector3D

from core.group import Group
from core.mesh import Mesh
from core.scene import Scene
from formats import igz
from trazomob.integrations import library_links


@pytest.fixture()
def library_root(tmp_path, monkeypatch):
    root = tmp_path / "components"
    monkeypatch.setenv("INGETRAZO_COMPONENTS", str(root))
    return root


@pytest.fixture(autouse=True)
def _clean_state():
    library_links._DEF_CACHE.clear()
    library_links._REBUILDING[0] = False
    yield
    library_links._DEF_CACHE.clear()
    library_links._REBUILDING[0] = False


def _grid_mesh(n: int = 20) -> Mesh:
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


def _payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))["scene"]


def _faces(payload: dict) -> int:
    total = sum(len(g.get("faces") or ()) for g in payload.get("groups", ()))
    return total + sum(len(p.get("faces") or ())
                       for p in payload.get("protos", ()))


def _imported_group(n: int = 20, name: str = "Sofa importado") -> Group:
    group = Group(_grid_mesh(n), name=name)
    group.xform = QMatrix4x4()
    group.xform.translate(QVector3D(3.0, 2.0, 0.0))
    return group


def test_imported_group_saves_as_link_and_roundtrips(library_root, tmp_path):
    library_links.install()
    group = _imported_group()
    source = tmp_path / "sofa.dae"
    source.write_bytes(b"<collada/>")

    payload = library_links.link_imported_group(group, source)
    assert payload["library"] == "file"
    assert library_links.is_linked(group)

    scene = Scene()
    scene.groups.append(group)
    out = tmp_path / "casa.igz"
    igz.save_scene(scene, out)

    raw = _payload(out)["groups"][0]
    assert raw["link"]["library"] == "file"
    assert raw["link"]["entry"]["path"] == str(source)
    assert raw["faces"] == []
    assert _faces(_payload(out)) == 0

    cache = Path(payload["entry"]["cache"])
    assert cache.is_file()

    back = Scene()
    igz.load_into(back, out)
    assert len(back.groups) == 1
    rebuilt = back.groups[0]
    assert library_links.is_linked(rebuilt)
    assert len(rebuilt.mesh.faces) == 400
    assert rebuilt.xform.column(3).x() == pytest.approx(3.0)
    assert rebuilt.xform.column(3).y() == pytest.approx(2.0)


def test_import_hook_tags_what_the_import_added(library_root, tmp_path):
    scene = Scene()

    class FakeWindow:
        def __init__(self, viewport_scene):
            self.viewport = types.SimpleNamespace(scene=viewport_scene)

        def _import_dae_path(self, path):
            self.viewport.scene.groups.append(
                Group(_grid_mesh(10), name="Cortina"))
            return True

    window = FakeWindow(scene)
    library_links._install_import_hooks(FakeWindow)

    source = tmp_path / "cortina.dae"
    source.write_bytes(b"<collada/>")
    assert window._import_dae_path(source)

    assert len(scene.groups) == 1
    assert library_links.is_linked(scene.groups[0])
    assert Path(library_links.link_of(
        scene.groups[0])["entry"]["cache"]).is_file()


def test_missing_cache_is_rebuilt_from_the_source(library_root, tmp_path):
    library_links.install()
    source = tmp_path / "tapete.igz"
    src_scene = Scene()
    src_scene.groups.append(Group(_grid_mesh(12), name="Tapete"))
    igz.save_scene(src_scene, source)

    group = Group(_grid_mesh(12), name="Tapete")
    payload = library_links.link_imported_group(group, source)
    cache = Path(payload["entry"]["cache"])
    assert cache.is_file()
    cache.unlink()                       # cache limpo, origem ainda existe

    scene = Scene()
    scene.groups.append(group)
    out = tmp_path / "casa.igz"
    igz.save_scene(scene, out)

    back = Scene()
    igz.load_into(back, out)
    assert len(back.groups[0].mesh.faces) == 144
    assert cache.is_file()               # regravado ao reler


def test_missing_cache_and_source_leaves_a_stub(library_root, tmp_path):
    library_links.install()
    source = tmp_path / "sumiu.dae"
    source.write_bytes(b"<collada/>")

    group = _imported_group()
    payload = library_links.link_imported_group(group, source)
    Path(payload["entry"]["cache"]).unlink()
    source.unlink()

    scene = Scene()
    scene.groups.append(group)
    out = tmp_path / "casa.igz"
    igz.save_scene(scene, out)

    back = Scene()
    igz.load_into(back, out)             # não pode explodir
    stub = back.groups[0]
    assert library_links.is_linked(stub)
    assert not stub.mesh.faces
    assert stub.xform.column(3).x() == pytest.approx(3.0)


def test_cache_is_binary_and_far_smaller_than_embedding(library_root, tmp_path):
    group = _imported_group(40, "Painel")
    source = tmp_path / "painel.skp"
    source.write_bytes(b"skp")

    payload = library_links.link_imported_group(group, source)
    cache = Path(payload["entry"]["cache"])

    embedded = Scene()
    embedded.groups.append(_imported_group(40, "Painel"))
    full = tmp_path / "embutido.igz"
    igz.save_scene(embedded, full)

    assert cache.stat().st_size * 10 < full.stat().st_size


def test_empty_import_does_not_become_a_link(library_root, tmp_path):
    """O nó raiz vazio de um .skp não pode virar vínculo de cache vazio.

    Era o caso do ``PainelA.``: um grupo sem geometria virava link, o cache
    saía com 500 bytes e o documento guardava uma referência que nunca
    devolvia nada.
    """
    source = tmp_path / "painel.skp"
    source.write_bytes(b"skp")

    group = Group(Mesh(), name="PainelA.")
    assert library_links.link_imported_group(group, source) is None
    assert not library_links.is_linked(group)
    assert not list(library_links.cache_root().rglob("*.igz"))


def test_install_without_marking_still_reads_links(library_root):
    """Motor desligado: ler vínculos continua, marcar novos não."""
    from trazomob.integrations import platform as host

    class FakeWindow:
        def _build_user_component(self, entry):
            return None

        def _build_library_component(self, entry):
            return None

    for feature in ("igz.load_into.links",
                    "main_window._build_user_component.links",
                    "main_window._build_library_component.links"):
        host.restore_hook(feature)
    previous = library_links._HOST[0]
    try:
        library_links.install(window=FakeWindow(), marking=False)
        assert host.hook_installed("igz.load_into.links")
        assert not host.hook_installed(
            "main_window._build_user_component.links")
        assert not host.hook_installed(
            "main_window._build_library_component.links")
    finally:
        library_links._HOST[0] = previous
        host.restore_hook("igz.load_into.links")
