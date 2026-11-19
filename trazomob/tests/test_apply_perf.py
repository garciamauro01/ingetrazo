# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Regressões das otimizações do botão Aplicar (catálogo de textura e sync de vãos)."""
from __future__ import annotations

import json
from pathlib import Path

from types import SimpleNamespace

from PySide6.QtGui import QVector3D

from core.group import Group
from core.mesh import Mesh
from core.scene import Scene
from trazomob.builders import mesh_utils
from trazomob.builders.cabinet_transform import invalidate_replaced_modules_caches
from trazomob.wall.builder import WallBuilderTool
from trazomob.wall.mesh_builder import WallMeshBuilder


def test_catalog_texture_is_read_once_per_file_version(tmp_path, monkeypatch):
    tex_dir = tmp_path / "textures"
    (tex_dir / "mdf").mkdir(parents=True)
    (tex_dir / "marmores").mkdir()
    (tex_dir / "mdf" / "catalog.json").write_text("[]", encoding="utf-8")
    (tex_dir / "marmores" / "catalog.json").write_text(json.dumps([
        {"nome": "Marmore Teste", "arquivo": "pedra.jpg", "sw": 0.8, "sh": 0.8},
    ]), encoding="utf-8")
    (tex_dir / "marmores" / "pedra.jpg").write_bytes(b"x")

    mesh_utils._CATALOG_ENTRIES_CACHE.clear()
    real_read = Path.read_text
    reads = []

    def counting_read(self, *args, **kwargs):
        if str(self).endswith("catalog.json"):
            reads.append(str(self))
        return real_read(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", counting_read)

    first = mesh_utils._lookup_catalog_texture(tex_dir, "marmore teste")
    second = mesh_utils._lookup_catalog_texture(tex_dir, "marmore teste")

    assert first is not None
    assert first == second
    # mdf + marmores lidos uma vez cada, não uma vez por peça rebuild
    assert len(reads) == 2


def test_catalog_texture_cache_follows_file_changes(tmp_path):
    tex_dir = tmp_path / "textures"
    (tex_dir / "mdf").mkdir(parents=True)
    (tex_dir / "marmores").mkdir()
    catalog = tex_dir / "marmores" / "catalog.json"
    catalog.write_text("[]", encoding="utf-8")

    mesh_utils._CATALOG_ENTRIES_CACHE.clear()
    assert mesh_utils._lookup_catalog_texture(tex_dir, "marmore teste") is None

    catalog.write_text(json.dumps([
        {"nome": "Marmore Teste", "arquivo": "pedra.jpg", "sw": 0.8, "sh": 0.8},
    ]), encoding="utf-8")
    (tex_dir / "marmores" / "pedra.jpg").write_bytes(b"x")

    assert mesh_utils._lookup_catalog_texture(tex_dir, "marmore teste") is not None


def test_wall_openings_sync_is_deduplicated(monkeypatch):
    scene = Scene()
    wall = WallBuilderTool.build_chain_group(
        scene,
        [QVector3D(0, 0, 0), QVector3D(4, 0, 0)],
        is_closed=False,
        altura_m=2.6,
        espessura_m=0.15,
    )

    mesh = Mesh()
    for y in (-0.09, 0.09):
        mesh.add_face([
            QVector3D(1.6, y, 0.0),
            QVector3D(2.4, y, 0.0),
            QVector3D(2.4, y, 2.1),
            QVector3D(1.6, y, 2.1),
        ])
    door = Group(mesh, name="Porta")
    door.ext = {
        "trazomob_esquadria": {"largura_mm": 800, "altura_mm": 2100, "esp_parede_mm": 180},
        "trazomob": {"kind": "esquadria"},
    }
    scene.groups.extend([wall, door])

    from trazomob.interaction import magnetic_drag
    real_bounds = magnetic_drag.get_module_reference_bounds
    calls = {"n": 0}

    def counting_bounds(mod):
        calls["n"] += 1
        return real_bounds(mod)

    monkeypatch.setattr(magnetic_drag, "get_module_reference_bounds", counting_bounds)

    assert WallMeshBuilder.sync_scene_wall_openings(scene) is True
    first_calls = calls["n"]
    assert first_calls > 0

    # Segundo disparo no mesmo estado (sidebar + bootstrap) não refaz a varredura
    assert WallMeshBuilder.sync_scene_wall_openings(scene) is False
    assert calls["n"] == first_calls

    # Uma mudança real na malha da esquadria invalida a assinatura
    door.mesh._mut_serial += 1
    assert WallMeshBuilder.sync_scene_wall_openings(scene) is False
    assert calls["n"] > first_calls


def _chunk_group(name: str) -> Group:
    g = Group(Mesh(), name=name)
    g.children = [Group(Mesh(), name=name + "-filho")]
    return g


def test_selective_chunk_invalidation_keeps_unrelated_groups():
    """Aplicar a um módulo não pode forçar rebake de VBOs do resto da cena."""
    old_mod = _chunk_group("Bancada antiga")
    new_mod = _chunk_group("Bancada nova")
    other = _chunk_group("Parede importada")
    child = old_mod.children[0]
    proxy = Group(child.mesh, name="Bancada antiga-proxy")

    vp = SimpleNamespace(
        _group_chunks={
            id(old_mod): {"uid": 1},
            id(child): {"uid": 2},
            id(proxy): {"uid": 3},
            id(other): {"uid": 4},
            id(other.children[0]): {"uid": 5},
        },
        _inst_chunks={id(old_mod): {"ikey": (1,)}, id(other): {"ikey": (4,)}},
        _placement_proxies={id(child): proxy},
        _placement_tops={id(proxy): id(old_mod)},
        _placements_memo=("stale",),
        _epoch_same=123,
    )

    invalidate_replaced_modules_caches([(old_mod, new_mod)], vp)

    # Órfãos do módulo substituído removidos dos dois caches e dos proxies
    for gid in (id(old_mod), id(child), id(proxy)):
        assert gid not in vp._group_chunks
        assert gid not in vp._inst_chunks
    assert vp._placement_proxies == {}
    assert vp._placement_tops == {}
    # Resto da cena intacto — é o que evita os ~5 s de rebake global
    assert vp._group_chunks[id(other)] == {"uid": 4}
    assert vp._group_chunks[id(other.children[0])] == {"uid": 5}
    assert vp._inst_chunks[id(other)] == {"ikey": (4,)}
    assert vp._placements_memo is None
    assert vp._epoch_same is None


def test_selective_chunk_invalidation_handles_batch_replacements():
    """Aplicar em lote invalida apenas os módulos substituídos."""
    old_a, new_a = _chunk_group("A antiga"), _chunk_group("A nova")
    old_b, new_b = _chunk_group("B antiga"), _chunk_group("B nova")
    untouched = _chunk_group("C intocada")

    vp = SimpleNamespace(
        _group_chunks={id(g): {"uid": i} for i, g in enumerate(
            [old_a, old_b, untouched, new_a, new_b])},
        _inst_chunks={id(g): {"ikey": (i,)} for i, g in enumerate([old_a, untouched])},
        _placements_memo=("stale",),
    )

    invalidate_replaced_modules_caches([(old_a, new_a), (old_b, new_b)], vp)

    assert id(old_a) not in vp._group_chunks
    assert id(old_b) not in vp._group_chunks
    assert id(untouched) in vp._group_chunks
    assert id(old_a) not in vp._inst_chunks
    assert id(untouched) in vp._inst_chunks

