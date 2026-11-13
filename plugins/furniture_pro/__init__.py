# SPDX-License-Identifier: GPL-3.0-or-later
"""Ingetrazo Furniture Pro — parametric furniture design for Ingetrazo.

This package is a self-contained extension.  The host imports it by file path
and calls :func:`setup` once, after the main window exists.  Everything the
plugin saves travels in the document (module parameters in ``group.ext`` and
the project in ``scene.plugin_data['furniture_pro']``); user libraries live in
the per-user data directory.

The module is import-safe outside Ingetrazo: no host API is touched until
``setup`` runs.
"""
from __future__ import annotations

from .core.constants import PLUGIN_KEY, PLUGIN_NAME, PLUGIN_VERSION

__all__ = ["PLUGIN_NAME", "PLUGIN_VERSION", "setup", "teardown"]

#: Kept alive for the extension's lifetime, and attached to ``app`` so the
#: host's own reference is enough to keep it from being collected.
_state: dict = {}


def _module_group_for(scene, item):
    """Return the Furniture Pro module group that owns ``item``, if any."""
    from .adapters.geometry import spec_from_group

    if spec_from_group(item) is not None:
        return item
    for group in list(getattr(scene, "groups", []) or []):
        try:
            if item in group.children:
                return group
        except TypeError:
            continue
    return None


def _outliner_kind(group):
    """Browser label for a Furniture Pro container."""
    from .adapters.geometry import spec_from_group
    from .core.constants import PLUGIN_KEY, MODULE_LABELS

    ext = getattr(group, "ext", None) or {}
    entry = ext.get(PLUGIN_KEY) if isinstance(ext, dict) else None
    if not isinstance(entry, dict):
        return None
    kind = entry.get("kind")
    if kind == "module":
        spec = spec_from_group(group)
        if spec is None:
            return {"type": "Furniture Pro", "props": [("Estado", "inválido")]}
        return {
            "type": "Móvel Furniture Pro",
            "props": [
                ("Tipo", MODULE_LABELS.get(spec.type, spec.type)),
                ("Código", spec.code or "—"),
                ("Medidas", f"{spec.width_mm:.0f} × {spec.height_mm:.0f} × "
                            f"{spec.depth_mm:.0f} mm"),
                ("Ambiente", spec.room or "Geral"),
            ],
        }
    if kind == "panel":
        panel = entry.get("panel") or {}
        return {
            "type": "Peça Furniture Pro",
            "props": [
                ("Código", panel.get("code") or "—"),
                ("Nome", panel.get("name") or "Peça"),
                ("Medidas", f"{panel.get('length_mm', 0):.0f} × "
                            f"{panel.get('width_mm', 0):.0f} mm"),
            ],
        }
    return None


def _context_menu(menu, selection):
    """Right-click entries for selected Furniture Pro modules."""
    from PySide6.QtCore import QTimer

    state = _state
    if not state:
        return
    controller = state["controller"]
    panel = state["panel"]
    scene = controller.scene
    groups = []
    for item in selection or []:
        group = _module_group_for(scene, item) if scene is not None else None
        if group is not None and group not in groups:
            groups.append(group)
    if not groups:
        return
    if len(groups) == 1:
        label = "Editar módulo Furniture Pro…"
    else:
        label = f"Editar {len(groups)} módulos Furniture Pro…"
    edit = menu.addAction(label)

    def edit_modules() -> None:
        if len(groups) == 1:
            panel.module_list.setCurrentRow(
                _row_for_group(panel, groups[0]))
            QTimer.singleShot(0, panel.edit_selected)
            return
        # Editing several modules at once is deliberately conservative: the
        # form edits one specification, so open the selected one and keep the
        # rest untouched rather than silently copying dimensions.
        QTimer.singleShot(0, panel.edit_selected)

    edit.triggered.connect(edit_modules)

    remove = menu.addAction("Excluir módulo(s) Furniture Pro")
    remove.triggered.connect(lambda: QTimer.singleShot(
        0, lambda: _delete_groups(controller, panel, groups)))


def _row_for_group(panel, group) -> int:
    from PySide6.QtCore import Qt
    from .adapters.geometry import spec_from_group

    spec = spec_from_group(group)
    if spec is None:
        return -1
    for row in range(panel.module_list.count()):
        item = panel.module_list.item(row)
        if item is not None and item.data(Qt.UserRole) == spec.id:
            return row
    return -1


def _delete_groups(controller, panel, groups) -> None:
    from PySide6.QtWidgets import QMessageBox
    from .adapters.geometry import spec_from_group

    specs = [spec_from_group(g) for g in groups]
    specs = [s for s in specs if s is not None]
    if not specs:
        return
    answer = QMessageBox.question(
        panel, "Excluir módulos",
        f"Excluir {len(specs)} módulo(s) e toda a geometria gerada?")
    if answer != QMessageBox.Yes:
        return
    for spec in specs:
        try:
            controller.delete_module(spec.id)
        except Exception as exc:                     # noqa: BLE001
            panel._error("Excluir módulo", exc)
    panel.refresh()


def _about(app) -> None:
    from PySide6.QtWidgets import QMessageBox

    QMessageBox.information(
        app.window, f"Sobre {PLUGIN_NAME}",
        f"{PLUGIN_NAME} {PLUGIN_VERSION}\n\n"
        "Projeto paramétrico de móveis para Ingetrazo.\n\n"
        "Medidas de fabricação em milímetros. Ferragens sem dados de "
        "instalação verificados não geram furação. DXF não é exportado sem "
        "uma biblioteca validada.\n\n"
        "Os dados do projeto ficam no documento (.igz); as bibliotecas "
        "ficam na pasta do usuário.")


def setup(app) -> None:
    """Extension entry point, called once by Ingetrazo."""
    global _state
    if getattr(app, "_furniture_pro_state", None) is not None:
        return                               # already initialised this session

    from .adapters import FurnitureController
    from .core.logging_utils import get_logger
    from .ui import FurniturePanel

    logger = get_logger()
    controller = FurnitureController(app)
    panel = FurniturePanel(controller, app)
    dock = app.add_panel(PLUGIN_NAME, panel, name="main", stretch=1)
    panel.dock = dock

    state = {"controller": controller, "panel": panel, "dock": dock}
    _state = state
    app._furniture_pro_state = state

    menu = app.add_menu("Furniture Pro")
    if menu is not None:
        action = menu.addAction("Abrir janela…")
        action.triggered.connect(lambda: panel.open_window(0))
        action = menu.addAction("Inserir módulo…")
        action.triggered.connect(panel.new_module)
        action = menu.addAction("Fabricação e orçamento…")
        action.triggered.connect(lambda: panel.open_window(3))
        action = menu.addAction("Diagnóstico…")
        action.triggered.connect(panel.show_diagnostics)
        menu.addSeparator()
        action = menu.addAction("Sobre…")
        action.triggered.connect(lambda: _about(app))
    else:                                    # minimal host: loose entries
        app.add_menu_action("Furniture Pro — abrir janela",
                            lambda: panel.open_window(0))
        app.add_menu_action("Furniture Pro — inserir módulo",
                            panel.new_module)

    app.on_document_changed(panel.document_changed)
    app.add_outliner_kind(_outliner_kind)
    app.add_context_menu(_context_menu)

    try:
        created = controller.restore_missing_geometry()
        if created:
            logger.info("restored %s module group(s) from document data", created)
    except Exception:                        # noqa: BLE001
        # A damaged document must still open; the panel will offer to fix it.
        logger.exception("could not restore module geometry")

    logger.info("%s %s initialised", PLUGIN_NAME, PLUGIN_VERSION)


def teardown(app=None) -> None:
    """Release the dialog, if any.  The host does not require this."""
    state = _state
    window = state.get("panel").window if state.get("panel") else None
    if window is not None:
        window.close()
    _state = {}
    if app is not None:
        try:
            app._furniture_pro_state = None
        except Exception:                    # noqa: BLE001
            pass
