# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes de inserção de módulos em slots de réguas guia com e sem rodapé."""
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QVector3D
from trazomob.builders.cabinet import CabinetBuilder
from trazomob.ui.module_ribbon import TrazoMobModuleRibbonBar, get_module_carcass_bounds
from trazomob.wall.selection import WallSelectionManager, WallFaceInfo


class MockScene:
    def __init__(self):
        self.objects = []
        self.groups = []
        self.layers = []
        self.saved_views = []
        self.dimensions = []
        self.text_labels = []
        self.compositions = []
        self.version = 0
        self.mesh = type("MockMesh", (), {"capture_state": lambda self: {}})()

    def add_group(self, grp):
        self.groups.append(grp)
        self.objects.append(grp)


class MockHistory:
    def __init__(self, scene):
        self.scene = scene

    def record_state(self, desc):
        pass

    def execute(self, cmd):
        if hasattr(cmd, "do"):
            cmd.do(self.scene)
        elif hasattr(cmd, "redo"):
            cmd.redo(self.scene)


class MockViewport:
    def __init__(self):
        self.scene = MockScene()
        self.history = MockHistory(self.scene)
        self.selected_object = None

    def notify_scene_changed(self):
        pass

    def update(self):
        pass


class MockMainWindow:
    def __init__(self, viewport):
        self.viewport = viewport
        self.editor_dock = None
        self.materials_dock = None

    def select_object(self, obj):
        self.viewport.selected_object = obj


def test_insert_inferior_between_guides_sem_rodape():
    """Garante que quando um módulo inferior tem rodape == 0 e é inserido em um vão entre guias,
    ele não herda rodapé de módulo de chão pré-existente e fica rigorosamente delimitado
    entre as duas guias (z_base e z_top).
    """
    _app = QApplication.instance() or QApplication([])
    vp = MockViewport()
    main_win = MockMainWindow(vp)
    ribbon = TrazoMobModuleRibbonBar(main_window=main_win, viewport=vp, sidebar_panel=None)

    # 1. Adiciona um balcão de referência no chão com rodapé de 150mm
    ref_balcao = CabinetBuilder.build_module_group(
        {
            "tipo": "balcao",
            "largura": 800,
            "altura": 720,
            "profundidade": 550,
            "rodape": 150.0,
            "rot_z": 0.0,
        },
        offset=(0.0, 0.0, 0.0),
    )
    vp.scene.add_group(ref_balcao)
    vp.selected_object = ref_balcao

    # 2. Configura a parede e arma o slot entre as guias z = 0.15 e z = 0.85 (altura = 700mm)
    wall_mgr = WallSelectionManager.get_instance(vp)
    wall_face = WallFaceInfo(
        wall_group=None,
        face=None,
        segment_index=0,
        face_type="interna",
        normal=QVector3D(0.0, 1.0, 0.0),
        center=QVector3D(1.5, 0.0, 1.4),
    )
    wall_mgr.selected_wall_face = wall_face
    wall_mgr.active_placement_slot = {
        "z_base": 0.15,
        "z_top": 0.85,
        "height_mm": 700.0,
        "label": "Balcão Suspenso",
        "category": "inferior",
        "default_depth_mm": 550.0,
        "center_pt": QVector3D(1.5, 0.0, 0.5),
        "target_u": 1.5,
        "u_pos": 1.5,
        "u_dir": QVector3D(1.0, 0.0, 0.0),
        "n_dir": QVector3D(0.0, 1.0, 0.0),
        "depth_m": 0.55,
        "width_m": 0.80,
    }

    # 3. Insere um novo balcão com rodape = 0
    mod_data = {
        "id": "balcao",
        "nome": "Balcão Suspenso 800",
        "largura": 800,
        "altura": 720,
        "profundidade": 550,
        "rodape": 0,
        "default_z": 0.0,
    }
    ribbon.insert_module_into_scene(mod_data)

    # Verifica o módulo recém-inserido
    assert len(vp.scene.groups) == 2
    novo_mod = vp.scene.groups[1]
    mod_info = novo_mod.ext.get("trazomob_module", {})

    # O rodapé deve ser 0.0 e a altura deve ser exatamente os 700mm do slot
    assert mod_info.get("rodape") == 0.0
    assert mod_info.get("altura") == 700.0

    # Verifica os limites verticais reais (bounds)
    bounds = get_module_carcass_bounds(novo_mod)
    assert bounds is not None
    z_min = bounds[4]
    z_max = bounds[5]

    assert z_min == pytest.approx(0.15, abs=1e-3)
    assert z_max == pytest.approx(0.85, abs=1e-3)
