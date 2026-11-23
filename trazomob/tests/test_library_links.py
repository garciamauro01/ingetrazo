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
    return user_library.register(source, nombre="Tapete 2x2")


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


def _assert_placeholder_frame(group: Group) -> None:
    """Verifica o quadro translúcido de destaque sem bloquear reconstruções."""
    assert len(group.mesh.edges) == 12
    assert len(group.mesh.faces) == 6
    assert library_links.is_placeholder_mesh(group.mesh) is True
    assert library_links._has_geometry(group) is False
    for face in group.mesh.faces:
        assert face.attrs.get("color") is not None
        assert 0.0 < float(face.attrs.get("opacity") or 0.0) < 0.3
        assert face.attrs.get("igz_link_placeholder") is True


def test_missing_source_leaves_an_empty_stub(library_root, tmp_path):
    entry = _registered_entry(tmp_path)
    placed = _place(entry)
    library_links.set_link(placed, library_links.link_from_entry(entry))

    scene = Scene()
    scene.groups.append(placed)
    out = tmp_path / "cena.igz"
    igz.save_scene(scene, out)

    copy = user_library.resolve(entry)     # a cópia que a biblioteca possui
    assert copy is not None
    copy.unlink()                           # a biblioteca perdeu o arquivo

    back = Scene()
    igz.load_into(back, out)                # não pode explodir

    group = back.groups[0]
    assert library_links.is_linked(group)
    _assert_placeholder_frame(group)
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
    _assert_placeholder_frame(empty)


def test_unresolved_link_shows_a_wireframe_frame(library_root, tmp_path):
    """O lugar do item ausente fica visível em destaque suave e selecionável."""
    group = Group(name="Sumiu")
    library_links.set_link(group, {
        "library": library_links.IMPORT_LIBRARY,
        "id": "a" * 64 + ":0",
        "rev": None,
        "entry": {"cache": str(tmp_path / "nada.igz"), "name": "Sumiu",
                  "index": 0, "cm": [200.0, 80.0, 250.0]},
    })
    scene = Scene()
    scene.groups.append(group)

    assert library_links.rebuild_scene_links(scene)["missing"] == 1

    _assert_placeholder_frame(group)
    assert library_links.is_linked(group)     # ainda pode ser relocalizado
    xs = [v.position.x() for e in group.mesh.edges for v in (e.v0, e.v1)]
    zs = [v.position.z() for e in group.mesh.edges for v in (e.v0, e.v1)]
    assert min(xs) == pytest.approx(-1.0)
    assert max(xs) == pytest.approx(1.0)
    assert min(zs) == pytest.approx(0.0)
    assert max(zs) == pytest.approx(2.5)


def test_opening_a_document_shows_the_frame(tmp_path, monkeypatch):
    """O cenário relatado: abrir um .igz cuja biblioteca não está disponível."""
    monkeypatch.setenv("INGETRAZO_COMPONENTS", str(tmp_path / "components"))
    group = Group(name="Sofá sumido")
    library_links.set_link(group, {
        "library": "user", "id": "sem-biblioteca", "rev": None,
        "entry": {"id": "sem-biblioteca", "nombre": "Sofá sumido",
                  "archivo": "models/sem-biblioteca/sofá.igz",
                  "cm": [180.0, 90.0, 80.0]},
    })
    scene = Scene()
    scene.groups.append(group)
    documento = tmp_path / "cena.igz"
    igz.save_scene(scene, documento)

    library_links._DEF_CACHE.clear()
    aberto = Scene()
    igz.load_into(aberto, documento)

    volta = aberto.groups[0]
    assert library_links.is_linked(volta)
    _assert_placeholder_frame(volta)


def test_frame_does_not_block_a_later_rebuild(library_root, tmp_path):
    """Com a biblioteca de volta, o frame dá lugar à geometria de verdade."""
    entry = _registered_entry(tmp_path)
    model = user_library.resolve(entry)
    afastado = Path(str(model) + ".away")
    model.rename(afastado)

    group = Group(name="Tapete 2x2")
    library_links.set_link(group, {"library": "user", "id": entry["id"],
                                   "rev": None, "entry": dict(entry)})
    scene = Scene()
    scene.groups.append(group)
    library_links._DEF_CACHE.clear()

    assert library_links.rebuild_scene_links(scene)["missing"] == 1
    _assert_placeholder_frame(group)

    afastado.rename(model)
    library_links._DEF_CACHE.clear()
    assert library_links.rebuild_scene_links(scene)["rebuilt"] == 1
    assert group.mesh.faces
    assert not library_links.is_placeholder_mesh(group.mesh)
    assert library_links.is_linked(group)


def test_placeholder_frame_is_selectable_in_front_of_a_wall(library_root, tmp_path):
    """Clicar no interior da caixa translúcida seleciona o vínculo, não a parede atrás."""
    import math
    import os
    from PySide6.QtWidgets import QApplication

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    assert app is not None

    from views.viewport import Viewport

    wall_mesh = Mesh()
    wall_mesh.add_face([
        QVector3D(-3.0, 2.0, 0.0),
        QVector3D(3.0, 2.0, 0.0),
        QVector3D(3.0, 2.0, 3.0),
        QVector3D(-3.0, 2.0, 3.0),
    ])
    wall = Group(wall_mesh, name="Parede")

    missing = Group(name="Sofá ausente")
    library_links.set_link(missing, {
        "library": "user",
        "id": "sofa-ausente",
        "rev": None,
        "entry": {
            "id": "sofa-ausente",
            "nombre": "Sofá ausente",
            "archivo": "models/sofa-ausente/sofa.igz",
            "cm": [180.0, 90.0, 100.0],
        },
    })

    vp = Viewport(None)
    try:
        vp.resize(800, 600)
        vp.camera.set_aspect(800, 600)
        vp.flash_status = lambda *a, **k: None
        vp.scene.groups.extend([wall, missing])
        library_links.rebuild_scene_links(vp.scene)
        vp.scene.version += 1
        cam = vp.camera
        cam.yaw = math.radians(-90.0)
        cam.pitch = math.radians(15.0)
        cam.target = QVector3D(0.0, 0.0, 0.5)
        cam.distance = 5.0

        px = vp._world_to_pixel(QVector3D(0.0, -0.45, 0.5))
        assert px is not None
        assert vp.pick_group(px[0], px[1]) is missing
    finally:
        vp.close()


def test_library_object_never_cuts_wall_or_triggers_magnetic_snap(library_root, tmp_path):
    """Objeto da biblioteca do usuário não recorta parede nem sofre snap magnético."""
    from types import SimpleNamespace

    from trazomob.domain.module_utils import is_esquadria, is_library_decoration
    from trazomob.domain.snap_contract import SNAP_PAREDE_NENHUM, get_module_snap_parede
    from trazomob.interaction.magnetic_drag import MagneticModuleDragFilter
    from trazomob.wall.builder import WallBuilderTool
    from trazomob.wall.mesh_builder import WallMeshBuilder

    scene = Scene()
    wall = WallBuilderTool.build_chain_group(
        scene,
        [QVector3D(0.0, 0.0, 0.0), QVector3D(4.0, 0.0, 0.0)],
        is_closed=False,
        altura_m=2.60,
        espessura_m=0.15,
    )
    initial_faces = len(wall.mesh.faces)

    for obj_name in ("Porta-retrato", "Janela decorativa", "Aparador 2 portas"):
        decor = Group(_grid_mesh(4), name=obj_name)
        decor.layer = "ESQUADRIAS"
        library_links.set_link(decor, {
            "library": "user",
            "id": "decor-teste",
            "rev": None,
            "entry": {"id": "decor-teste", "nombre": obj_name},
        })
        decor.xform = QMatrix4x4()
        decor.xform.translate(QVector3D(2.0, 0.0, 0.8))
        scene.groups.append(decor)

        assert is_library_decoration(decor) is True
        assert is_esquadria(decor) is False
        assert get_module_snap_parede(decor) == SNAP_PAREDE_NENHUM

        dummy_vp = SimpleNamespace(scene=scene)
        assert MagneticModuleDragFilter._find_top_module(dummy_vp, decor) is None

    changed = WallMeshBuilder.sync_scene_wall_openings(scene)
    assert changed is False
    assert len(wall.mesh.faces) == initial_faces
    assert wall.ext["trazomob_wall"].get("openings", []) == []


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
