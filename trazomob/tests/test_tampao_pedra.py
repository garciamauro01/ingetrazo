# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes do módulo Tampão Engrossado de Pedra (Marmoraria)."""
from __future__ import annotations

import pytest
from PySide6.QtGui import QVector3D
from PySide6.QtWidgets import QApplication

from trazomob.builders.cabinet import CabinetBuilder
from trazomob.domain.catalog import MODULE_CATALOG
from trazomob.domain.module_geometry import build_default_module_params
from trazomob.domain.snap_contract import SNAP_PAREDE_NENHUM, get_module_snap_parede


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_tampao_engrossado_pedra_bloco_unico_e_material(qapp):
    cat = next(
        m for c in MODULE_CATALOG.values() for m in c
        if m.get("id") == "bancada_tampao_engrossado"
    )
    params = build_default_module_params(cat)
    params["largura"] = 750.0
    params["altura"] = 900.0
    params["profundidade"] = 60.0  # Espessura total engrossada
    params["material"] = "Mármore Calacatta Gold"

    mod = CabinetBuilder.build_module_group(params, offset=(0.0, 0.0, 0.0))
    assert mod is not None
    assert len(mod.children) == 1
    assert mod.children[0].name == "Tampao Pedra - Bloco"

    pts = [v.position for v in mod.children[0].mesh.vertices]
    xs = [p.x() for p in pts]
    ys = [p.y() for p in pts]
    zs = [p.z() for p in pts]
    assert pytest.approx(max(xs) - min(xs), abs=1e-4) == 0.750
    assert pytest.approx(max(ys) - min(ys), abs=1e-4) == 0.060
    assert pytest.approx(max(zs) - min(zs), abs=1e-4) == 0.900
    assert mod.children[0].ext["trazomob"]["material"] == "Mármore Calacatta Gold"
    assert get_module_snap_parede(mod) == SNAP_PAREDE_NENHUM


def test_tampao_pedra_sem_snap_magnetico(qapp):
    from PySide6.QtCore import QObject

    from core.scene import Scene
    from trazomob.interaction.magnetic_drag import MagneticModuleDragFilter
    from trazomob.wall.builder import WallBuilderTool

    class _DummyVP(QObject):
        def __init__(self, sc):
            super().__init__()
            self.scene = sc

    scene = Scene()
    wall_grp = WallBuilderTool.build_chain_group(
        scene, [QVector3D(0.0, 0.0, 0.0), QVector3D(3.0, 0.0, 0.0)],
        is_closed=False, altura_m=2.6, espessura_m=0.15, alinhamento="interno"
    )
    scene.groups.append(wall_grp)

    cat = next(
        m for c in MODULE_CATALOG.values() for m in c
        if m.get("id") == "bancada_tampao_engrossado"
    )
    params = build_default_module_params(cat)
    mod = CabinetBuilder.build_module_group(params, offset=(1.0, 0.25, 0.0))
    scene.groups.append(mod)

    mgr = MagneticModuleDragFilter(_DummyVP(scene))
    mgr._target_module = mod
    mgr._module_orig_bounds = (1.0, 1.6, 0.25, 0.29, 0.0, 0.86)
    mgr.snap_enabled = True

    raw = QVector3D(0.12, -0.15, 0.05)
    out = mgr._compute_magnetic_snap(raw, QVector3D(1.3, -2.0, 1.0), QVector3D(0.0, 1.0, -0.3))
    assert out == raw
    assert mgr._active_locked_wall_face is None
    assert mgr._auto_rot_deg == 0.0
