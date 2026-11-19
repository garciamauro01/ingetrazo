# SPDX-License-Identifier: GPL-3.0-or-later
"""A click selects a decoration: Entity Info must not redo work that only a
document change can invalidate (#decor-bake)."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture
def panel():
    QApplication.instance() or QApplication([])
    from core.group import Group
    from core.scene import Scene
    from views.tray import EntityInfoPanel

    scene = Scene()
    group = Group(name="Decor")
    group.component = True
    from PySide6.QtGui import QMatrix4x4
    group.xform = QMatrix4x4()
    scene.groups.append(group)
    scene.selection.add(group)
    win = SimpleNamespace(viewport=SimpleNamespace(scene=scene))
    yield EntityInfoPanel(win), panel_scope(scene, group)
    scene.selection.clear()


def panel_scope(scene, group):
    return SimpleNamespace(scene=scene, group=group)


def test_solid_volume_is_not_recomputed_on_a_selection_bump(panel, monkeypatch):
    info, ctx = panel
    calls = []

    def fake_volume(group):
        calls.append(group)
        return 1.0

    monkeypatch.setattr("core.solids.solid_volume", fake_volume)
    info.refresh()
    assert len(calls) == 1

    ctx.scene.bump_view()          # what selecting an object does
    info.refresh()
    assert len(calls) == 1         # the expensive solid check stayed cached

    ctx.scene.version += 1         # a real document change
    info.refresh()
    assert len(calls) == 2


def test_large_deferred_mesh_is_not_built_to_check_solidity(panel, monkeypatch):
    info, ctx = panel
    from core.mesh import DeferredMesh, Mesh

    calls = []
    monkeypatch.setattr("core.solids.solid_volume",
                        lambda group: calls.append(group))
    built = []

    def build(mesh):
        built.append(mesh)

    mesh = Mesh()
    assert DeferredMesh.defer(mesh, build, 100_676)
    ctx.group.mesh = mesh
    text = info._describe([ctx.group])
    assert not built
    assert not calls
    assert "100676" in text.replace(",", "")
