# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Importação direta como vínculo: o documento guarda a referência.

O caso real: decoração que entra arrastando um ``.skp``/``.dae`` não passa
pela biblioteca, então não era marcada — e era justamente ela que enchia o
``.igz``. Aqui o grupo importado é processado uma vez para um ``.igz`` no
cache (binário) e o documento guarda só ``{path, cache, rev}`` + ``xform``.
"""
import ast
import json
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


def test_mark_imported_groups_tags_what_the_import_added(library_root, tmp_path):
    added = [Group(_grid_mesh(10), name="Cortina")]
    source = tmp_path / "cortina.dae"
    source.write_bytes(b"<collada/>")

    library_links.mark_imported_groups(added, source)

    assert library_links.is_linked(added[0])
    assert Path(library_links.link_of(
        added[0])["entry"]["cache"]).is_file()


def test_missing_cache_is_rebuilt_from_the_source(library_root, tmp_path):
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


def _called_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Attribute):
            names.add(func.attr)
        elif isinstance(func, ast.Name):
            names.add(func.id)
    return names


def test_direct_file_importers_keep_groups_self_contained():
    """Importação direta (SKP/DAE/GLB/OBJ) deve permanecer autocontida;
    somente componentes inseridos pela biblioteca geram vínculo automático."""
    main_win_path = (
        Path(__file__).resolve().parents[2] / "views" / "main_window.py"
    )
    tree = ast.parse(main_win_path.read_text(encoding="utf-8"))
    main_win = next(
        n for n in tree.body
        if isinstance(n, ast.ClassDef) and n.name == "MainWindow"
    )
    methods = {
        n.name: n for n in main_win.body
        if isinstance(n, ast.FunctionDef)
    }

    for name in (
        "_import_glb_path",
        "_import_dae_path",
        "import_skp_path",
        "_on_import_obj",
    ):
        calls = _called_names(methods[name])
        assert "mark_imported_groups" not in calls, name
        assert "link_imported_group" not in calls, name

    for name in ("_build_user_component", "_build_library_component"):
        calls = _called_names(methods[name])
        assert "mark_built_component" in calls, name
