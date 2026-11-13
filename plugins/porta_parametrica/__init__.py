# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors and Pair Programmer.
"""Plugin Gerador de Esquadrias Paramétricas (Portas e Janelas) com Corte Dinâmico de Paredes."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QToolBar

from tools.base import Tool

from .dialog import (
    DoorConfigDialog,
    DoorConfigWidget,
    WindowConfigDialog,
    WindowConfigWidget,
)
from .icons import make_door_icon, make_window_icon
from .tool import DoorPlacerTool, WindowPlacerTool

# Instâncias compartilhadas das ferramentas
_door_tool = DoorPlacerTool()
_window_tool = WindowPlacerTool()


class GeradorPortasTool(Tool):
    """Ferramenta para abrir o configurador e ativar a inserção de portas."""
    name = "Gerador de Portas"
    shortcut = None
    description = "Criar portas paramétricas e cortar paredes automaticamente ao avançar sobre elas."
    uses_snap = True

    def on_activate(self, viewport) -> None:
        global _door_tool
        win = getattr(viewport, "window", None)
        if callable(win):
            win = win()

        dlg = DoorConfigDialog(_door_tool.config, on_apply=self._on_apply, parent=win)
        dlg.show()

        if win is not None and hasattr(win, "_tools"):
            win._tools["porta_parametrica"] = _door_tool
            if hasattr(win, "_activate_tool"):
                win._activate_tool("porta_parametrica")

    def _on_apply(self, new_cfg: dict[str, Any]) -> None:
        global _door_tool
        _door_tool.update_config(new_cfg)

    def on_deactivate(self, viewport) -> None:
        pass


class GeradorJanelasTool(Tool):
    """Ferramenta para abrir o configurador e ativar a inserção de janelas."""
    name = "Gerador de Janelas"
    shortcut = None
    description = "Criar janelas paramétricas e cortar paredes no peitoril automaticamente."
    uses_snap = True

    def on_activate(self, viewport) -> None:
        global _window_tool
        win = getattr(viewport, "window", None)
        if callable(win):
            win = win()

        dlg = WindowConfigDialog(_window_tool.config, on_apply=self._on_apply, parent=win)
        dlg.show()

        if win is not None and hasattr(win, "_tools"):
            win._tools["janela_parametrica"] = _window_tool
            if hasattr(win, "_activate_tool"):
                win._activate_tool("janela_parametrica")

    def _on_apply(self, new_cfg: dict[str, Any]) -> None:
        global _window_tool
        _window_tool.update_config(new_cfg)

    def on_deactivate(self, viewport) -> None:
        pass


def setup(app) -> None:
    """Registra o plugin de Esquadrias (Portas e Janelas) no IngeTrazo."""
    global _door_tool, _window_tool
    win = getattr(app, "window", None)
    vp = getattr(app, "viewport", None)

    # 1. Registra as ferramentas na janela principal
    if win is not None and hasattr(win, "_tools"):
        win._tools["porta_parametrica"] = _door_tool
        win._tools["janela_parametrica"] = _window_tool

    # 2. Painéis Laterais no Side Tray
    door_config_widget = DoorConfigWidget(_door_tool.config)
    door_config_widget.config_changed.connect(lambda cfg: _door_tool.update_config(cfg))
    if hasattr(app, "add_panel"):
        app.add_panel("Portas", door_config_widget, name="door_generator", start_hidden=True)

    win_config_widget = WindowConfigWidget(_window_tool.config)
    win_config_widget.config_changed.connect(lambda cfg: _window_tool.update_config(cfg))
    if hasattr(app, "add_panel"):
        app.add_panel("Janelas", win_config_widget, name="window_generator", start_hidden=True)

    # 3. Adiciona ações no menu Extensões
    def _open_door_tool():
        if win is not None and hasattr(win, "_activate_tool"):
            dlg = DoorConfigDialog(_door_tool.config, on_apply=lambda cfg: _door_tool.update_config(cfg), parent=win)
            dlg.show()
            win._activate_tool("porta_parametrica")

    def _open_window_tool():
        if win is not None and hasattr(win, "_activate_tool"):
            dlg = WindowConfigDialog(_window_tool.config, on_apply=lambda cfg: _window_tool.update_config(cfg), parent=win)
            dlg.show()
            win._activate_tool("janela_parametrica")

    if hasattr(app, "add_menu_action"):
        app.add_menu_action(
            "Gerador de Portas Parametrizável",
            _open_door_tool,
            shortcut=None,
            tip="Inserir porta paramétrica cortando automaticamente a parede."
        )
        app.add_menu_action(
            "Gerador de Janelas Parametrizável",
            _open_window_tool,
            shortcut=None,
            tip="Inserir janela paramétrica cortando automaticamente a parede no peitoril."
        )

    # 4. Barra de Ferramentas "Esquadrias" (Porta e Janela)
    if win is not None and hasattr(win, "addToolBar"):
        tb = QToolBar("Esquadrias", win)
        tb.setObjectName("toolbar_esquadrias")
        tb.setWindowTitle("Esquadrias")
        tb.setMovable(True)
        tb.setFloatable(True)
        tb.setIconSize(QSize(24, 24))
        tb.setToolButtonStyle(Qt.ToolButtonIconOnly)

        act_door = QAction(make_door_icon(24), "Porta Paramétrica", win)
        act_door.setStatusTip("Inserir porta paramétrica cortando automaticamente a parede")
        act_door.setToolTip("Porta Paramétrica (Corte Automático)")
        act_door.triggered.connect(_open_door_tool)
        tb.addAction(act_door)

        act_window = QAction(make_window_icon(24), "Janela Paramétrica", win)
        act_window.setStatusTip("Inserir janela paramétrica cortando automaticamente a parede no peitoril")
        act_window.setToolTip("Janela Paramétrica (Corte Automático de Peitoril)")
        act_window.triggered.connect(_open_window_tool)
        tb.addAction(act_window)

        win.addToolBar(Qt.TopToolBarArea, tb)

    # 5. Menu de Contexto (Botão Direito do Mouse) sobre portas e janelas já colocadas
    def _context(menu, selection):
        door_group = None
        window_group = None

        for item in selection:
            if hasattr(item, "ext") and isinstance(item.ext, dict):
                if "porta_parametrica" in item.ext:
                    door_group = item
                    break
                if "janela_parametrica" in item.ext:
                    window_group = item
                    break

        if door_group is None and window_group is None and vp is not None and hasattr(vp, "scene"):
            for g in getattr(vp.scene, "groups", []):
                if hasattr(g, "ext") and isinstance(g.ext, dict):
                    children = getattr(g, "children", [])
                    if any(c in selection for c in children):
                        if "porta_parametrica" in g.ext:
                            door_group = g
                            break
                        if "janela_parametrica" in g.ext:
                            window_group = g
                            break

        # Contexto de Porta
        if door_group is not None:
            ext = door_group.ext.get("porta_parametrica", {})
            curr_ang = float(ext.get("open_angle_deg", 0.0))
            is_open = curr_ang > 10.0

            act_toggle = menu.addAction("🚪 Fechar Porta (0°)" if is_open else "🚪 Abrir Porta (90°)")
            from .builder import ToggleDoorCommand, EditDoorCommand
            act_toggle.triggered.connect(lambda: vp.history.execute(ToggleDoorCommand(door_group, vp)))

            act_edit = menu.addAction("📐 Editar Porta Paramétrica…")
            def _open_edit_door_dialog():
                curr_cfg = dict(door_group.ext.get("porta_parametrica", {}))
                def _apply_edit(new_cfg):
                    vp.history.execute(EditDoorCommand(door_group, new_cfg, vp))
                    vp.flash_status(f"Porta '{door_group.name}' atualizada com sucesso!")

                dlg = DoorConfigDialog(
                    curr_cfg,
                    on_apply=_apply_edit,
                    title=f"Editar: {door_group.name}",
                    apply_text="Salvar Alterações na Porta",
                    parent=win,
                )
                dlg.exec()

            from PySide6.QtCore import QTimer
            act_edit.triggered.connect(lambda: QTimer.singleShot(0, _open_edit_door_dialog))

        # Contexto de Janela
        if window_group is not None:
            ext = window_group.ext.get("janela_parametrica", {})
            curr_pct = float(ext.get("open_pct", 0.0))
            is_open = curr_pct > 5.0

            act_toggle_w = menu.addAction("🪟 Fechar Janela (0%)" if is_open else "🪟 Abrir Janela (50%)")
            from .builder import ToggleWindowCommand, EditWindowCommand
            act_toggle_w.triggered.connect(lambda: vp.history.execute(ToggleWindowCommand(window_group, vp)))

            act_edit_w = menu.addAction("📐 Editar Janela Paramétrica…")
            def _open_edit_window_dialog():
                curr_cfg = dict(window_group.ext.get("janela_parametrica", {}))
                def _apply_edit_w(new_cfg):
                    vp.history.execute(EditWindowCommand(window_group, new_cfg, vp))
                    vp.flash_status(f"Janela '{window_group.name}' atualizada com sucesso!")

                dlg = WindowConfigDialog(
                    curr_cfg,
                    on_apply=_apply_edit_w,
                    title=f"Editar: {window_group.name}",
                    apply_text="Salvar Alterações na Janela",
                    parent=win,
                )
                dlg.exec()

            from PySide6.QtCore import QTimer
            act_edit_w.triggered.connect(lambda: QTimer.singleShot(0, _open_edit_window_dialog))

    if hasattr(app, "add_context_menu"):
        app.add_context_menu(_context)


