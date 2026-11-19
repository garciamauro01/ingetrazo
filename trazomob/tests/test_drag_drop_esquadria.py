# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Regressão do posicionamento por Drag & Drop de esquadrias (portas e janelas) em paredes."""
from __future__ import annotations

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QVector3D
from PySide6.QtWidgets import QApplication

from trazomob.builders.cabinet import CabinetBuilder
from trazomob.domain.catalog import MODULE_CATALOG
from trazomob.domain.module_geometry import build_default_module_params
from trazomob.interaction.drag_drop_handler import compute_drop_placement
from trazomob.wall.builder import WallBuilderTool


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _DummyViewport:
    """Viewport mínimo que dispara um raio determinístico para testar compute_drop_placement."""

    def __init__(self, scene, ray_orig: QVector3D, ray_dir: QVector3D):
        self.scene = scene
        self._orig = ray_orig
        self._dir = ray_dir.normalized()

    def _pixel_to_ray(self, _x: float, _y: float):
        return self._orig, self._dir


def test_drop_porta_giro_centraliza_nas_duas_faces_da_parede(qapp):
    from core.scene import Scene

    scene = Scene()
    # Parede horizontal ao longo de X com espessura 150mm: Y ocupa [0.00, 0.15], centro = 0.075
    pts = [QVector3D(0.0, 0.0, 0.0), QVector3D(4.0, 0.0, 0.0)]
    wall_grp = WallBuilderTool.build_chain_group(
        scene, pts, is_closed=False, altura_m=2.6, espessura_m=0.15, alinhamento="interno"
    )
    scene.groups.append(wall_grp)

    cat_porta = next(
        m for c in MODULE_CATALOG.values() for m in c
        if m.get("id") == "porta_giro"
    )
    mod_data = dict(cat_porta)
    mod_data["largura"] = 800.0
    mod_data["altura"] = 2150.0

    # 1. Arraste solto na face frontal (y = 0.00)
    vp_front = _DummyViewport(scene, QVector3D(1.5, -2.0, 1.2), QVector3D(0.0, 1.0, 0.0))
    off_f, rot_f, w_f = compute_drop_placement(vp_front, QPointF(100, 100), mod_data)
    assert w_f is wall_grp

    p_f = build_default_module_params(mod_data)
    p_f["rot_z"] = rot_f
    mod_f = CabinetBuilder.build_module_group(p_f, offset=off_f)
    marco_f = next(c for c in mod_f.children if "Marco" in c.name)
    ys_f = [v.position.y() for v in marco_f.mesh.vertices]
    assert pytest.approx((min(ys_f) + max(ys_f)) * 0.5, abs=1e-3) == 0.075

    # 2. Arraste solto na face traseira (y = 0.15)
    vp_back = _DummyViewport(scene, QVector3D(2.5, 2.0, 1.2), QVector3D(0.0, -1.0, 0.0))
    off_b, rot_b, w_b = compute_drop_placement(vp_back, QPointF(100, 100), mod_data)
    assert w_b is wall_grp

    p_b = build_default_module_params(mod_data)
    p_b["rot_z"] = rot_b
    mod_b = CabinetBuilder.build_module_group(p_b, offset=off_b)
    marco_b = next(c for c in mod_b.children if "Marco" in c.name)
    ys_b = [v.position.y() for v in marco_b.mesh.vertices]
    assert pytest.approx((min(ys_b) + max(ys_b)) * 0.5, abs=1e-3) == 0.075


def test_drop_janela_nao_duplica_peitoril_e_centraliza_na_parede(qapp):
    from core.scene import Scene

    scene = Scene()
    pts = [QVector3D(0.0, 0.0, 0.0), QVector3D(4.0, 0.0, 0.0)]
    wall_grp = WallBuilderTool.build_chain_group(
        scene, pts, is_closed=False, altura_m=2.6, espessura_m=0.15, alinhamento="interno"
    )
    scene.groups.append(wall_grp)

    cat_janela = next(
        m for c in MODULE_CATALOG.values() for m in c
        if m.get("id") == "janela_correr_2f_130"
    )
    mod_data = dict(cat_janela)

    vp = _DummyViewport(scene, QVector3D(2.0, -2.0, 1.5), QVector3D(0.0, 1.0, 0.0))
    off, rot_z, w = compute_drop_placement(vp, QPointF(100, 100), mod_data)
    assert w is wall_grp
    assert off[2] == pytest.approx(0.0, abs=1e-4)

    params = build_default_module_params(mod_data)
    params["rot_z"] = rot_z
    mod_j = CabinetBuilder.build_module_group(params, offset=off)
    zs = [v.position.z() for c in mod_j.children if c.mesh for v in c.mesh.vertices]
    # Peitoril de 1000mm -> Z mínimo deve ser ~1.00m (não 2.00m)
    assert 0.95 <= min(zs) <= 1.05
    ys = [v.position.y() for c in mod_j.children if c.mesh for v in c.mesh.vertices]
    assert pytest.approx((min(ys) + max(ys)) * 0.5, abs=0.02) == 0.075

