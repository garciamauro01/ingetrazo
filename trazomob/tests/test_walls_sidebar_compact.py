# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes de contrato e compacidade do painel lateral de paredes."""
from __future__ import annotations

import pytest
from PySide6.QtGui import QVector3D
from PySide6.QtWidgets import QApplication

from core.history import History
from core.scene import Scene
from trazomob.ui.sidebar_panel import TrazoMobSidebarPanel
from trazomob.wall.builder import WallBuilderTool


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _CompactTestViewport:
    def __init__(self, scene: Scene) -> None:
        self.scene = scene
        self.history = History(scene)
        self.status_messages: list[str] = []

    def update(self) -> None:
        pass

    def flash_status(self, msg: str) -> None:
        self.status_messages.append(msg)


def test_walls_sidebar_preserves_all_controls_and_compact_dimensions(qapp):
    scene = Scene()
    wall = WallBuilderTool.build_chain_group(
        scene=scene,
        pts=[QVector3D(0.0, 0.0, 0.0), QVector3D(4.4, 0.0, 0.0), QVector3D(4.4, 3.0, 0.0)],
        is_closed=True,
        altura_m=2.60,
        espessura_m=0.15,
        alinhamento="centro",
    )
    scene.groups.append(wall)
    vp = _CompactTestViewport(scene)

    panel = TrazoMobSidebarPanel(None)
    panel._get_viewport = lambda: vp
    panel._get_scene = lambda: scene
    panel.load_wall(wall, segment_index=0, face_type="externa")
    panel.resize(380, 700)
    panel.show()
    qapp.processEvents()

    required_controls = [
        "cb_parede_segmento",
        "sp_parede_comprimento",
        "sp_parede_altura",
        "sp_parede_esp",
        "cb_parede_alinhar",
        "chk_parede_todas",
        "chk_parede_teto",
        "cb_regua_ambiente",
        "btn_edit_reguas",
        "chk_regua_visivel",
        "chk_regua_labels",
        "btn_toggle_wall_tool",
        "btn_apply_wall",
        "btn_frente_parede",
        "btn_elevacao_parede",
        "btn_encaixar_bancada",
        "btn_encaixar_tamponamento",
        "btn_encaixar_rodape",
        "btn_fechar_vao",
        "cb_auto_composicao",
        "btn_auto_inferiores",
        "btn_auto_aereos",
        "btn_hide_selected_wall",
        "btn_split_walls",
        "btn_lock_walls_floor",
        "btn_unhide_all_walls",
    ]
    for attr in required_controls:
        w = getattr(panel, attr, None)
        assert w is not None, f"Controle esperado ausente: {attr}"
        assert w.isVisible() is True, f"Controle deveria ficar visível com parede selecionada: {attr}"

    # Verifica compacidade real do card para não gerar painel gigante nem estouro horizontal
    card = panel.card_paredes
    assert card.sizeHint().height() <= 440
    assert card.minimumSizeHint().width() <= 360

    # Verifica alternância da trava de posição
    panel.btn_lock_walls_floor.click()
    assert panel.btn_lock_walls_floor.isChecked() is False
    assert wall.ext.get("motion_locked") is False
    panel.btn_lock_walls_floor.click()
    assert panel.btn_lock_walls_floor.isChecked() is True
    assert wall.ext.get("motion_locked") is True
