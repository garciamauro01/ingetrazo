# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Itens de biblioteca como vínculo: o .igz guarda a referência, não a malha.

O caso real: sofás, cadeiras e tapetes de milhares de faces. Antes, cada
modelo entrava no documento com a geometria inteira; agora entra só
``{library, id, rev, xform}`` e a malha é relida da biblioteca ao abrir.
"""
import json
from pathlib import Path

import pytest
from PySide6.QtGui import QMatrix4x4, QVector3D

from core import user_library
from core.group import Group
from core.mesh import Mesh
from core.scene import Scene
from formats import igz
from trazomob.integrations import library_links
from views import component_loader


@pytest.fixture()
def library_root(tmp_path, monkeypatch):
    root = tmp_path / "components"
    monkeypatch.setenv("INGETRAZO_COMPONENTS", str(root))
    return root


def _grid_mesh(n: int = 40) -> Mesh:
    """Um «tapete» de ``n × n`` faces — geometria o bastante para pesar."""
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


def _source_igz(path: Path) -> Path:
    scene = Scene()
    scene.groups.append(Group(_grid_mesh(), name="Tapete"))
    igz.save_scene(scene, path)
    return path


def _registered_entry(tmp_path: Path) -> dict:
    source = _source_igz(tmp_path / "tapete.igz")
    return user_library.register(source, managed=False, nombre="Tapete 2x2")


def _place(entry: dict, at=(2.0, 1.0, 0.0)) -> Group:
    group = component_loader.load_component(entry, strict=True).group
    group.xform = QMatrix4x4()
    group.xform.translate(QVector3D(*at))
    return group


def _payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))["scene"]


def _embedded_faces(payload: dict) -> int:
    """Faces gravadas no documento — na entrada ou na tabela de protótipos."""
    total = sum(len(g.get("faces") or ()) for g in payload.get("groups", ()))
    return total + sum(len(p.get("faces") or ())
                       for p in payload.get("protos", ()))


def test_link_saves_reference_instead_of_geometry(library_root, tmp_path):
    entry = _registered_entry(tmp_path)
    placed = _place(entry)
    library_links.set_link(placed, library_links.link_from_entry(entry))

    scene = Scene()
    scene.groups.append(placed)
    linked = tmp_path / "vinculado.igz"
    igz.save_scene(scene, linked)

    linked_payload = _payload(linked)
    raw = linked_payload["groups"][0]
    assert raw["link"]["library"] == "user"
    assert raw["link"]["id"] == entry["id"]
    assert raw["faces"] == []
    assert raw["edges"] == []
    assert _embedded_faces(linked_payload) == 0

    # A mesma cena sem o vínculo grava a malha inteira: a diferença é o ponto.
    embedded = Scene()
    embedded.groups.append(_place(entry))
    full = tmp_path / "embutido.igz"
    igz.save_scene(embedded, full)
    assert _embedded_faces(_payload(full)) == 1600

    assert linked.stat().st_size * 10 < full.stat().st_size


def test_load_rebuilds_the_linked_geometry(library_root, tmp_path):
    entry = _registered_entry(tmp_path)
    placed = _place(entry)
    library_links.set_link(placed, library_links.link_from_entry(entry))

    scene = Scene()
    scene.groups.append(placed)
    out = tmp_path / "cena.igz"
    igz.save_scene(scene, out)

    back = Scene()
    igz.load_into(back, out)

    assert len(back.groups) == 1
    group = back.groups[0]
    assert library_links.is_linked(group)   # continua um vínculo no documento
    assert len(group.mesh.faces) == 1600    # a malha voltou
    assert group.xform is not None
    assert group.xform.column(3).x() == pytest.approx(2.0)
    assert group.xform.column(3).y() == pytest.approx(1.0)


def test_missing_source_leaves_an_empty_stub(library_root, tmp_path):
    entry = _registered_entry(tmp_path)
    placed = _place(entry)
    library_links.set_link(placed, library_links.link_from_entry(entry))

    scene = Scene()
    scene.groups.append(placed)
    out = tmp_path / "cena.igz"
    igz.save_scene(scene, out)

    Path(entry["origen"]).unlink()          # a biblioteca perdeu o arquivo

    back = Scene()
    igz.load_into(back, out)                # não pode explodir

    group = back.groups[0]
    assert library_links.is_linked(group)
    assert not group.mesh.faces
    assert group.xform.column(3).x() == pytest.approx(2.0)


def test_materialize_embeds_the_geometry_again(library_root, tmp_path):
    entry = _registered_entry(tmp_path)
    placed = _place(entry)
    library_links.set_link(placed, library_links.link_from_entry(entry))

    scene = Scene()
    scene.groups.append(placed)
    out = tmp_path / "cena.igz"
    igz.save_scene(scene, out)

    back = Scene()
    igz.load_into(back, out)
    assert library_links.materialize(back.groups[0])

    out2 = tmp_path / "materializado.igz"
    igz.save_scene(back, out2)
    payload = _payload(out2)
    assert "link" not in payload["groups"][0]
    assert _embedded_faces(payload) == 1600


def test_rebuild_stats_separate_missing_from_empty(library_root, tmp_path):
    """Um documento que abre «vazio» precisa dizer o que faltou."""
    empty_cache = library_links._cache_path("e" * 64, 0)
    library_links._write_cache(Group(Mesh(), name="Vazio"), empty_cache)

    empty = Group(name="Vazio")
    library_links.set_link(empty, {
        "library": library_links.IMPORT_LIBRARY,
        "id": "e" * 64 + ":0",
        "rev": None,
        "entry": {"cache": str(empty_cache), "name": "Vazio", "index": 0},
    })

    missing = Group(name="Sumiu")
    library_links.set_link(missing, {
        "library": library_links.IMPORT_LIBRARY,
        "id": "f" * 64 + ":0",
        "rev": None,
        "entry": {"cache": str(tmp_path / "nada.igz"),
                  "name": "Sumiu", "index": 0},
    })

    scene = Scene()
    scene.groups.extend([empty, missing])
    stats = library_links.rebuild_scene_links(scene)

    assert stats == {"rebuilt": 0, "missing": 1, "empty": 1, "linked": 2}
    assert library_links.is_linked(empty)     # continua no documento, como stub
    assert not empty.mesh.faces


def test_unloaded_links_warn_in_the_status_bar(library_root, tmp_path):
    class Bar:
        def __init__(self):
            self.messages = []

        def showMessage(self, text, ms=0):
            self.messages.append((text, ms))

    class FakeWindow:
        def __init__(self):
            self.bar = Bar()

        def statusBar(self):
            return self.bar

    window = FakeWindow()
    previous = library_links._HOST[0]
    library_links._HOST[0] = window
    try:
        group = Group(name="Sumiu")
        library_links.set_link(group, {
            "library": library_links.IMPORT_LIBRARY,
            "id": "a" * 64 + ":0",
            "rev": None,
            "entry": {"cache": str(tmp_path / "nada.igz"),
                      "name": "Sumiu", "index": 0},
        })
        scene = Scene()
        scene.groups.append(group)
        library_links.rebuild_scene_links(scene)
    finally:
        library_links._HOST[0] = previous

    assert len(window.bar.messages) == 1
    text, ms = window.bar.messages[0]
    assert "1" in text
    assert ms == 15000
