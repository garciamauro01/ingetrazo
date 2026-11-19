# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Preenchimento automático de paredes: planejamento e posicionamento."""
from __future__ import annotations

import pytest
from PySide6.QtGui import QVector3D
from PySide6.QtWidgets import QApplication

from trazomob.domain.auto_layout import (
    place_group_on_wall,
    plan_wall_fill,
)
from trazomob.builders.cabinet import CabinetBuilder
from trazomob.domain.catalog import MODULE_CATALOG
from trazomob.domain.module_geometry import (
    auto_divisoes_for_doors,
    build_default_module_params,
    get_module_carcass_bounds,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.mark.parametrize("categoria,composicao,vao", [
    ("inferior", "portas", 3000.0),
    ("inferior", "portas", 2200.0),
    ("inferior", "portas", 500.0),
    ("inferior", "gavetas", 3000.0),
    ("inferior", "misto", 3000.0),
    ("aereo", "portas", 3000.0),
])
def test_plan_fecha_exatamente_o_vao(categoria, composicao, vao):
    modulos = plan_wall_fill(vao, categoria=categoria, composicao=composicao)

    assert modulos
    assert sum(m.largura_mm for m in modulos) == pytest.approx(vao, abs=1e-6)
    assert all(m.largura_mm > 0 for m in modulos)


def test_planejamento_respeita_regras_de_portas():
    inferiores = plan_wall_fill(3000.0, categoria="inferior")
    assert all(m.tipo == "balcao" for m in inferiores)
    assert all(1 <= m.num_portas <= 4 for m in inferiores)
    assert all(
        m.num_divisoes == auto_divisoes_for_doors(m.num_portas)
        for m in inferiores)

    aereos = plan_wall_fill(3000.0, categoria="aereo")
    assert all(m.tipo == "aereo" for m in aereos)
    assert all(1 <= m.num_portas <= 2 for m in aereos)


def test_composicao_mista_alterna_balcoes_e_gaveteiros():
    modulos = plan_wall_fill(3000.0, categoria="inferior", composicao="misto")
    tipos = {m.tipo for m in modulos}
    assert tipos == {"balcao", "gaveteiro"}


def test_composicao_gavetas_usa_apenas_gaveteiros():
    modulos = plan_wall_fill(
        2400.0, categoria="inferior", composicao="gavetas")
    assert all(m.tipo == "gaveteiro" for m in modulos)
    assert all(m.num_gavetas == 4 for m in modulos)


def test_vao_menor_que_o_minimo_e_rejeitado():
    with pytest.raises(ValueError):
        plan_wall_fill(100.0)


def _balcao(largura_mm: float, portas: int = 2):
    entry = next(
        m for c in MODULE_CATALOG.values() for m in c
        if m.get("id") == "balcao")
    params = build_default_module_params(dict(entry))
    params["largura"] = largura_mm
    params["num_portas"] = portas
    params["num_divisoes"] = auto_divisoes_for_doors(portas)
    params["rot_z"] = 0.0
    return CabinetBuilder.build_module_group(params, offset=(0.0, 0.0, 0.0))


def test_posicionamento_encosta_na_parede_e_mantem_contiguidade(qapp):
    n_dir = QVector3D(0.0, 1.0, 0.0)
    u_dir = QVector3D(-1.0, 0.0, 0.0)
    wall_plane_n = 0.0

    primeiro = _balcao(1000.0, portas=2)
    segundo = _balcao(1000.0, portas=2)

    place_group_on_wall(
        primeiro, n_dir, u_dir, wall_plane_n, start_u=0.0, z_base=0.0)
    place_group_on_wall(
        segundo, n_dir, u_dir, wall_plane_n, start_u=1.0, z_base=0.0)

    b1 = get_module_carcass_bounds(primeiro)
    b2 = get_module_carcass_bounds(segundo)

    # Traseira encostada no plano da parede (com 1 mm de folga).
    assert b1[2] == pytest.approx(0.001, abs=1e-6)
    assert b2[2] == pytest.approx(0.001, abs=1e-6)
    # Base apoiada em Z = 0.
    assert b1[4] == pytest.approx(0.0, abs=1e-6)
    assert b2[4] == pytest.approx(0.0, abs=1e-6)
    # Módulos contíguos ao longo da direção da parede.
    assert b1[0] == pytest.approx(b2[1], abs=1e-6)
    assert (b1[1] - b1[0]) == pytest.approx(1.0, abs=1e-6)
    assert (b2[1] - b2[0]) == pytest.approx(1.0, abs=1e-6)


class _FakeViewport:
    def __init__(self, scene):
        from core.history import History
        self.scene = scene
        self.history = History(scene)
        self.flash = ""

    def update(self):
        pass

    def notify_scene_changed(self):
        pass

    def flash_status(self, msg):
        self.flash = msg


class _FakeFace:
    def __init__(self):
        self.vertices = [
            QVector3D(0.0, 0.0, 0.0),
            QVector3D(3.0, 0.0, 0.0),
            QVector3D(3.0, 0.0, 2.6),
            QVector3D(0.0, 0.0, 2.6),
        ]


class _FakeWallManager:
    def __init__(self):
        from trazomob.wall.selection import WallFaceInfo
        self.selected_wall_face = WallFaceInfo(
            wall_group=None,
            face=_FakeFace(),
            segment_index=0,
            face_type="interna",
            normal=QVector3D(0.0, 1.0, 0.0),
            center=QVector3D(1.5, 0.0, 1.3),
        )
        self.active_placement_slot = None


def test_sidebar_preenche_a_parede_selecionada(qapp, monkeypatch):
    from core.scene import Scene
    from trazomob.ui.sidebar_panel import TrazoMobSidebarPanel
    from trazomob.wall.selection import WallSelectionManager

    fake_mgr = _FakeWallManager()
    monkeypatch.setattr(
        WallSelectionManager, "get_instance",
        classmethod(lambda cls, viewport=None, sidebar_panel=None: fake_mgr))

    scene = Scene()
    vp = _FakeViewport(scene)
    panel = TrazoMobSidebarPanel(None)
    panel._get_viewport = lambda: vp
    panel._get_scene = lambda: scene
    panel._ensure_form_built()
    panel.sp_parede_comprimento.setValue(2200)

    panel._auto_preencher_parede("inferior")

    assert len(scene.groups) == 2
    b1 = get_module_carcass_bounds(scene.groups[0])
    b2 = get_module_carcass_bounds(scene.groups[1])
    assert sum(b[1] - b[0] for b in (b1, b2)) == pytest.approx(2.2, abs=1e-6)
    # A distribuição é contígua e centrada nos 3 m da face.
    assert abs(b1[0] - b2[1]) < 1e-6 or abs(b2[0] - b1[1]) < 1e-6
    assert min(b1[0], b2[0]) >= 0.39
    assert max(b1[1], b2[1]) <= 2.61
    assert "2 módulo" in vp.flash

    # Todo o preenchimento entra como um único passo de desfazer.
    vp.history.undo()
    assert len(scene.groups) == 0

