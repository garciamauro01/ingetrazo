# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes de isolamento e roteamento de contexto multi-documento (abas) no TrazoMob."""
from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage, QPainter, QVector3D
from PySide6.QtWidgets import QApplication, QMainWindow

from core.group import Group
from core.mesh import Face, Mesh, Vertex
from core.scene import Scene
from core.style import BUILTIN_STYLES
from trazomob import CabinetInteractTool, TrazoMobTool
from trazomob import bootstrap as tm_bootstrap
from trazomob.builders.cabinet import CabinetBuilder
from trazomob.domain.i18n import tr
from trazomob.domain.module_geometry import build_default_module_params
from trazomob.integrations import platform as host
from trazomob.interaction.magnetic_drag import MagneticModuleDragFilter
from trazomob.render.lighting import LightManagerDialog
from trazomob.ui.module_dialog import TrazoMobDialog
from trazomob.ui.module_ribbon import TrazoMobModuleRibbonBar
from trazomob.ui.sidebar_panel import TrazoMobSidebarPanel
from trazomob.wall.selection import WallSelectionManager


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class DummyHistory:
    def __init__(self, scene: Scene) -> None:
        self._scene = scene
        self.executed: list[object] = []

    def execute(self, cmd) -> None:
        self.executed.append(cmd)
        if hasattr(cmd, "do"):
            cmd.do(self._scene)
        elif callable(cmd):
            cmd(self._scene)


class FakeViewport(QObject):
    sceneVersionChanged = Signal()

    def __init__(self, window, scene: Scene | None = None, shared_overlays=None) -> None:
        super().__init__(window)
        self._window = window
        self.scene = scene or Scene()
        self.history = DummyHistory(self.scene)
        self._ext_overlays = shared_overlays if shared_overlays is not None else []
        self.updated_count = 0
        self.flashed_messages: list[str] = []
        self.camera = None
        self.active_tool = None

    def window(self):
        return self._window

    def update(self) -> None:
        self.updated_count += 1

    def notify_scene_changed(self) -> None:
        self.sceneVersionChanged.emit()

    def flash_status(self, msg: str) -> None:
        self.flashed_messages.append(msg)

    def set_active_tool(self, tool) -> None:
        self.active_tool = tool

    def installEventFilter(self, obj) -> None:  # noqa: N802
        super().installEventFilter(obj)


@dataclass
class FakeDoc:
    viewport: FakeViewport
    front_view: FakeViewport | None = None
    doc_data: dict = field(default_factory=dict)


class FakeTabbedWindow(QMainWindow):
    documentChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._shared_overlays: list = []
        self.documents: list[FakeDoc] = []
        self._active_index = -1
        self._doc_change_hooks: list = []
        self._doc_closed_hooks: list = []
        self._panels: list = []
        self._overlays: list = []

    def new_document(self, scene: Scene | None = None) -> FakeDoc:
        vp = FakeViewport(self, scene=scene, shared_overlays=self._shared_overlays)
        doc = FakeDoc(viewport=vp)
        self.documents.append(doc)
        vp.sceneVersionChanged.connect(lambda v=vp: self._dispatch_doc_change(v))
        if self._active_index < 0:
            self._active_index = 0
        return doc

    def _dispatch_doc_change(self, vp: FakeViewport) -> None:
        if vp is self.viewport:
            for fn in list(self._doc_change_hooks):
                fn()

    @property
    def viewport(self) -> FakeViewport | None:
        if 0 <= self._active_index < len(self.documents):
            doc = self.documents[self._active_index]
            return doc.front_view or doc.viewport
        return None

    @property
    def active_document(self) -> FakeDoc | None:
        if 0 <= self._active_index < len(self.documents):
            return self.documents[self._active_index]
        return None

    def all_viewports(self) -> list[FakeViewport]:
        return [d.front_view or d.viewport for d in self.documents]

    def activate_document(self, index: int) -> None:
        self._active_index = index
        vp = self.viewport
        if vp is not None:
            vp.notify_scene_changed()
        self.documentChanged.emit()

    def close_document(self, index: int) -> None:
        doc = self.documents.pop(index)
        closed_scene = doc.viewport.scene
        if self.documents:
            self._active_index = min(self._active_index, len(self.documents) - 1)
        else:
            self._active_index = -1
        for fn in list(self._doc_closed_hooks):
            fn(closed_scene)


class FakeExtensionApp:
    def __init__(self, win: FakeTabbedWindow) -> None:
        self._win = win

    @property
    def window(self):
        return self._win

    @property
    def viewport(self):
        return self._win.viewport

    @property
    def scene(self):
        vp = self._win.viewport
        return vp.scene if vp is not None else None

    def add_panel(self, title: str, widget):
        self._win._panels.append((title, widget))
        return None

    def add_overlay(self, fn) -> None:
        self._win._overlays.append(fn)

    def add_pickable(self, **_kwargs) -> None:
        pass

    def add_menu_action(self, *_args, **_kwargs) -> None:
        pass

    def add_context_menu(self, *_args, **_kwargs) -> None:
        pass

    def on_document_changed(self, fn) -> None:
        self._win._doc_change_hooks.append(fn)

    def on_document_closed(self, fn) -> None:
        self._win._doc_closed_hooks.append(fn)

    def document_data(self, key: str, default=None):
        doc = self._win.active_document
        if doc is None:
            return default
        return doc.doc_data.get(key, default)

    def set_document_data(self, key: str, val) -> None:
        doc = self._win.active_document
        if doc is not None:
            doc.doc_data[key] = val


def _make_module_in_scene(scene: Scene, name: str = "Balcao") -> Group:
    params = build_default_module_params({"id": "balcao", "nome": name})
    grp = CabinetBuilder.build_module_group(params, offset=(0.0, 0.0, 0.0))
    grp.name = name
    scene.groups.append(grp)
    return grp


def _make_wall_in_scene(scene: Scene, name: str = "Parede 1") -> tuple[Group, Face]:
    v0 = Vertex(QVector3D(0.0, 0.0, 0.0))
    v1 = Vertex(QVector3D(2.0, 0.0, 0.0))
    v2 = Vertex(QVector3D(2.0, 0.0, 2.6))
    v3 = Vertex(QVector3D(0.0, 0.0, 2.6))
    face = Face([v0, v1, v2, v3])
    face.attrs["color"] = (0.8, 0.8, 0.8)
    mesh = Mesh()
    mesh.vertices = [v0, v1, v2, v3]
    mesh.faces = [face]
    grp = Group(name=name, mesh=mesh)
    grp.ext = {
        "trazomob_wall": {
            "pontos": [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0)],
            "altura": 2.6,
            "espessura": 0.15,
            "alinhamento": "interno",
            "is_closed": False,
            "face_segment_map": {0: 0},
        }
    }
    scene.groups.append(grp)
    return grp, face


def test_platform_active_and_all_viewports_follow_active_document(qapp):
    win = FakeTabbedWindow()
    doc1 = win.new_document()
    doc2 = win.new_document()
    app = FakeExtensionApp(win)

    assert host.active_viewport(window=win, viewport=doc1.viewport, app=app) is doc1.viewport
    assert host.all_viewports(window=win, viewport=doc1.viewport, app=app) == [doc1.viewport, doc2.viewport]

    win.activate_document(1)
    assert host.active_viewport(window=win, viewport=doc1.viewport, app=app) is doc2.viewport

    # Mesmo passando o viewport antigo (doc1), apply_display_style escreve no documento ativo
    preset = BUILTIN_STYLES[-1]
    assert host.apply_display_style(win, doc1.viewport, preset) is True
    assert doc2.viewport.scene.display_style.name == preset.name

    # Janela sem abas (mock simples em testes unitários) preserva fallback explícito
    dummy_win = SimpleNamespace()
    dummy_vp = SimpleNamespace(window=lambda: dummy_win)
    assert host.active_viewport(window=None, viewport=dummy_vp) is dummy_vp


def test_ribbon_inserts_into_active_document_after_tab_switch(qapp):
    WallSelectionManager._instance = None
    win = FakeTabbedWindow()
    doc1 = win.new_document()
    doc2 = win.new_document()
    app = FakeExtensionApp(win)

    sidebar = TrazoMobSidebarPanel(app)
    ribbon = TrazoMobModuleRibbonBar(win, doc1.viewport, sidebar)
    mod_data = {"id": "balcao", "nome": "Balcão 2 Portas", "largura": 800, "altura": 720, "profundidade": 550}

    ribbon.insert_module_into_scene(mod_data)
    assert len(doc1.viewport.scene.groups) == 1
    assert len(doc2.viewport.scene.groups) == 0

    win.activate_document(1)
    assert ribbon.viewport is doc2.viewport

    ribbon.insert_module_into_scene(mod_data)
    assert len(doc1.viewport.scene.groups) == 1
    assert len(doc2.viewport.scene.groups) == 1
    assert sidebar._selected_module in doc2.viewport.scene.groups


def test_wall_selection_manager_clears_stale_wall_on_scene_switch(qapp):
    WallSelectionManager._instance = None
    win = FakeTabbedWindow()
    doc1 = win.new_document()
    doc2 = win.new_document()

    wall1, face1 = _make_wall_in_scene(doc1.viewport.scene, "Parede Doc1")
    mgr = WallSelectionManager.get_instance(doc1.viewport)
    info = mgr.set_selected_face(wall1, face1, notify_sidebar=False)
    assert info is not None
    mgr.active_placement_slot = {"box_vertices": None}

    # Em troca para doc2, draw no vp1 inativo não limpa prematuramente nem pinta no errado
    win.activate_document(1)
    img = QImage(64, 64, QImage.Format_ARGB32)
    painter = QPainter(img)
    mgr.draw_selection_overlay(doc1.viewport, painter)
    painter.end()
    assert mgr.selected_wall_face is info

    # Ao consultar gerenciador para vp2 (doc2), parede da aba 1 é limpa e sua cor restaurada
    mgr2 = WallSelectionManager.get_instance(doc2.viewport)
    assert mgr2 is mgr
    assert mgr.viewport is doc2.viewport
    assert mgr.selected_wall_face is None
    assert mgr.active_placement_slot is None
    assert face1.attrs["color"] == (0.8, 0.8, 0.8)


def test_sidebar_panel_syncs_on_tab_switch_and_guards_stale_actions(qapp):
    WallSelectionManager._instance = None
    win = FakeTabbedWindow()
    doc1 = win.new_document()
    doc2 = win.new_document()
    app = FakeExtensionApp(win)

    mod1 = _make_module_in_scene(doc1.viewport.scene, "Balcao Doc1")
    doc1.viewport.scene.selection = {mod1}

    sidebar = TrazoMobSidebarPanel(app)
    doc1.viewport.notify_scene_changed()
    assert sidebar._selected_module is mod1

    # Muda para doc2 vazio: antes mesmo do evento, ações não podem agir em mod1 da aba 1
    win._active_index = 1
    assert sidebar._get_viewport() is doc2.viewport
    assert sidebar._active_selected_module() is None
    sidebar._rotate_selected(90.0)
    assert doc1.viewport.history.executed == []

    # Ao disparar a troca de documento, o cache antigo do sidebar é limpo
    win.activate_document(1)
    assert sidebar._selected_module is None
    assert sidebar._selected_wall is None

    # Seleciona mod2 na aba 2 -> sidebar sincroniza com mod2 e exclui somente em doc2
    mod2 = _make_module_in_scene(doc2.viewport.scene, "Balcao Doc2")
    doc2.viewport.scene.selection = {mod2}
    doc2.viewport.notify_scene_changed()
    assert sidebar._selected_module is mod2
    assert len(doc1.viewport.scene.groups) == 1
    assert len(doc2.viewport.scene.groups) == 1


def test_trazomob_dialog_and_light_manager_follow_active_document(qapp):
    win = FakeTabbedWindow()
    doc1 = win.new_document()
    doc2 = win.new_document()

    mod1 = _make_module_in_scene(doc1.viewport.scene, "Modulo Doc1")
    doc1.viewport.scene.selection = {mod1}

    dlg = TrazoMobDialog(doc1.viewport, parent=win)
    assert dlg.viewport is doc1.viewport
    assert dlg.scene is doc1.viewport.scene
    assert dlg._editing_module is mod1

    mod2 = _make_module_in_scene(doc2.viewport.scene, "Modulo Doc2")
    doc2.viewport.scene.selection = {mod2}
    win.activate_document(1)

    assert dlg.viewport is doc2.viewport
    assert dlg.scene is doc2.viewport.scene
    dlg.sync_to_active_document(doc2.viewport)
    assert dlg._editing_module is mod2

    # Também testa guarda contra _editing_module obsoleto em doc vazio
    win._active_index = 0
    assert mod2 not in doc1.viewport.scene.groups
    dlg._editing_module = mod2
    dlg.list_modules.setCurrentRow(0)
    dlg._insert_or_update_module()
    assert mod2 not in doc1.viewport.scene.groups
    dlg.close()

    # Gerenciador de Luzes segue o documento ativo e recarrega as luzes da aba ativa
    lgrp1 = Group(name="Spot Doc1")
    lgrp1.ext = {"trazomob_light": {"name": "Spot Doc1", "kind": "spot", "power": 300, "kelvin": 2700, "on": True}}
    doc1.viewport.scene.groups.append(lgrp1)

    lgrp2 = Group(name="LED Doc2")
    lgrp2.ext = {"trazomob_light": {"name": "LED Doc2", "kind": "led_strip", "power": 150, "kelvin": 4000, "on": True}}
    doc2.viewport.scene.groups.append(lgrp2)

    win.activate_document(0)
    light_dlg = LightManagerDialog(doc1.viewport, parent=win)
    assert len(light_dlg._lights) == 1
    assert light_dlg._lights[0]["name"] == "Spot Doc1"

    win.activate_document(1)
    assert light_dlg.viewport is doc2.viewport
    light_dlg.sync_to_active_document(doc2.viewport)
    assert len(light_dlg._lights) == 1
    assert light_dlg._lights[0]["name"] == "LED Doc2"
    light_dlg.close()


def test_magnetic_drag_filter_overlay_and_cleanup_multi_document(qapp):
    win = FakeTabbedWindow()
    doc1 = win.new_document()
    doc2 = win.new_document()
    mod1 = _make_module_in_scene(doc1.viewport.scene, "Mod1")

    f1 = MagneticModuleDragFilter(doc1.viewport, parent=doc1.viewport)
    f2 = MagneticModuleDragFilter(doc2.viewport, parent=doc2.viewport)

    assert f1._draw_cota_overlay in doc1.viewport._ext_overlays
    assert f2._draw_cota_overlay in doc1.viewport._ext_overlays

    # Desenho no vp2 não dispara cálculo de cotas de f1
    f1._active_drop_preview = {"pos": (0, 0, 0)}
    img = QImage(32, 32, QImage.Format_ARGB32)
    painter = QPainter(img)
    f1._draw_cota_overlay(doc2.viewport, painter)
    painter.end()
    assert f1._active_cota_items == []

    # _target_module removido da cena é limpo ao atualizar seleção
    f1._target_module = mod1
    doc1.viewport.scene.groups.clear()
    f1._on_scene_or_selection_changed()
    assert f1._target_module is None

    # cleanup remove overlay e desconecta somente o filtro do documento fechado
    f1.cleanup()
    assert f1._draw_cota_overlay not in win._shared_overlays
    assert f2._draw_cota_overlay in win._shared_overlays


def test_bootstrap_install_toolbar_actions_and_new_tab_wiring(qapp):
    WallSelectionManager._instance = None
    win = FakeTabbedWindow()
    doc1 = win.new_document()
    app = FakeExtensionApp(win)

    from trazomob.domain.engine_state import (
        reset_engine_cache,
        set_engine_enabled,
    )

    set_engine_enabled(True)
    try:
        tm_bootstrap.install(app, TrazoMobTool, CabinetInteractTool)

        assert getattr(doc1.viewport, "_trazomob_drag_filter", None) is not None
        assert getattr(doc1.viewport, "_trazomob_sidebar", None) is not None

        # Cria nova aba DEPOIS do install() e alterna para ela
        doc2 = win.new_document()
        mod2 = _make_module_in_scene(doc2.viewport.scene, "Balcao Aba2")
        doc2.viewport.scene.selection = {mod2}
        win.activate_document(1)
        qapp.processEvents()

        # _do_resync deve ter conectado automaticamente o novo viewport
        assert getattr(doc2.viewport, "_trazomob_drag_filter", None) is not None
        assert getattr(doc2.viewport, "_trazomob_sidebar", None) is not None

        # Ação da barra de ferramentas: Snap Magnético propaga entre abas e mostra status na aba 2
        tb = win.findChild(QObject, "toolbar_trazomob")
        assert tb is not None
        actions = {a.text(): a for a in tb.actions()}

        snap_act = actions[tr("Snap Magnético")]
        snap_act.setChecked(False)
        assert doc1.viewport._trazomob_drag_filter.snap_enabled is False
        assert doc2.viewport._trazomob_drag_filter.snap_enabled is False
        assert doc2.viewport.flashed_messages

        # Ação de girar 90° gira somente o módulo da aba ativa (doc2), sem afetar doc1
        rot_act = actions[tr("Girar 90° Horário")]
        rot_act.trigger()
        assert len(doc1.viewport.history.executed) == 0
        assert len(doc2.viewport.history.executed) == 1

        # Fechamento da aba 2 limpa seu filtro de overlay compartilhado
        drag2 = doc2.viewport._trazomob_drag_filter
        win.close_document(1)
        assert drag2._draw_cota_overlay not in win._shared_overlays

    finally:
        set_engine_enabled(False)
        reset_engine_cache()

def test_bootstrap_motor_desligado_por_padrao(qapp):
    """Com o motor desligado, o plugin não instala arraste e mantém só o botão mestre."""
    from PySide6.QtCore import QSettings

    from trazomob.domain.engine_state import (
        SETTING_KEY,
        is_engine_enabled,
        reset_engine_cache,
    )

    QSettings().remove(SETTING_KEY)
    reset_engine_cache()
    WallSelectionManager._instance = None

    win = FakeTabbedWindow()
    doc = win.new_document()
    app = FakeExtensionApp(win)

    try:
        tm_bootstrap.install(app, TrazoMobTool, CabinetInteractTool)

        assert is_engine_enabled() is False
        assert getattr(doc.viewport, "_trazomob_drag_filter", None) is None

        tb = win.findChild(QObject, "toolbar_trazomob")
        assert tb is not None
        actions = {a.text(): a for a in tb.actions()}
        engine_act = actions[tr("Motor TrazoMob")]
        assert engine_act.isCheckable() is True
        assert engine_act.isChecked() is False
        assert engine_act.isEnabled() is True
        assert actions[tr("Snap Magnético")].isEnabled() is False
    finally:
        QSettings().remove(SETTING_KEY)
        reset_engine_cache()
