# SPDX-License-Identifier: GPL-3.0-or-later
"""The Furniture Pro side panel.

The panel is the always-available face of the plugin: a compact project list
with quick actions.  The full window (:mod:`.dialogs`) holds the library
editors, manufacturing and quote tabs; opening it from here is one click, and
only one copy is kept so the panel and the viewport stay in sync.

The host emits a scene-version signal for every edit, including selection.
Reloading the project on each of those would throw away unsaved edits in the
full window, so the panel compares the document payload first and only
reloads when the stored data really changed.
"""
from __future__ import annotations

import json

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QMessageBox, QPlainTextEdit,
                               QPushButton, QVBoxLayout, QWidget)

from ..adapters.geometry import iter_module_groups
from ..core.constants import MODULE_LABELS, PLUGIN_NAME, PLUGIN_VERSION


def _signature(value) -> str:
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False,
                          default=str)
    except (TypeError, ValueError):
        return repr(value)


class FurniturePanel(QWidget):
    """Compact project overview for the side tray."""

    def __init__(self, controller, app=None, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.app = app
        self.dock = None
        self.window = None
        self._signature = _signature(controller.document_data())
        self._pending = False
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel("Furniture Pro")
        title.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(title)
        self.project_label = QLabel("")
        self.project_label.setWordWrap(True)
        self.project_label.setStyleSheet("color: #475569;")
        layout.addWidget(self.project_label)

        self.module_list = QListWidget()
        self.module_list.setAlternatingRowColors(True)
        self.module_list.setToolTip(
            "Módulos salvos no documento. Dê dois cliques para editar.")
        self.module_list.itemDoubleClicked.connect(
            lambda _item: self.edit_selected())
        self.module_list.currentItemChanged.connect(self._show_selected)
        layout.addWidget(self.module_list, 1)

        self.detail = QLabel("")
        self.detail.setWordWrap(True)
        self.detail.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(self.detail)

        row = QHBoxLayout()
        self.add_button = QPushButton("Novo…")
        self.add_button.setToolTip("Inserir um módulo paramétrico")
        self.add_button.clicked.connect(self.new_module)
        self.edit_button = QPushButton("Editar…")
        self.edit_button.clicked.connect(self.edit_selected)
        row.addWidget(self.add_button)
        row.addWidget(self.edit_button)
        layout.addLayout(row)

        row = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        row.addWidget(self.status_label, 1)
        self.open_button = QPushButton("Abrir janela")
        self.open_button.clicked.connect(self.open_window)
        row.addWidget(self.open_button)
        layout.addLayout(row)

        footer = QLabel(f"v{PLUGIN_VERSION}")
        footer.setStyleSheet("color: #94a3b8; font-size: 10px;")
        layout.addWidget(footer)

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        project = self.controller.project
        modules = project.modules
        self.project_label.setText(
            f"{project.name or 'Projeto sem nome'}"
            + (f" · {project.client}" if project.client else ""))
        current = self.module_list.currentItem()
        current_id = current.data(Qt.UserRole) if current else None
        self.module_list.blockSignals(True)
        try:
            self.module_list.clear()
            for spec in modules:
                item = QListWidgetItem(
                    f"{spec.code or '—'} · {spec.label}")
                item.setData(Qt.UserRole, spec.id)
                item.setToolTip(
                    f"{MODULE_LABELS.get(spec.type, spec.type)}\n"
                    f"{spec.width_mm:.0f} × {spec.height_mm:.0f} × "
                    f"{spec.depth_mm:.0f} mm\n"
                    f"Ambiente: {spec.room or 'Geral'}")
                self.module_list.addItem(item)
                if spec.id == current_id:
                    self.module_list.setCurrentItem(item)
        finally:
            self.module_list.blockSignals(False)

        report = self.controller.validation()
        temp = self.controller.materials
        total_width = sum(s.width_mm for s in modules)
        self.status_label.setText(
            f"{len(modules)} módulo(s) · {total_width:,.0f} mm"
            f" · {len(temp.materials)} chapas"
            + (f" · {len(report.errors)} erro(s)" if report.errors else ""))
        if report.errors:
            self.status_label.setStyleSheet("color: #b91c1c;")
        elif report.warnings:
            self.status_label.setStyleSheet("color: #b45309;")
        else:
            self.status_label.setStyleSheet("color: #15803d;")
        self._show_selected(self.module_list.currentItem())

    def _show_selected(self, item) -> None:
        if item is None:
            self.detail.setText("Nenhum módulo selecionado.")
            return
        module_id = item.data(Qt.UserRole)
        spec = self.controller.project.module(module_id)
        if spec is None:
            self.detail.setText("")
            return
        self.detail.setText(
            f"{MODULE_LABELS.get(spec.type, spec.type)} · "
            f"{spec.width_mm:.0f} × {spec.height_mm:.0f} × "
            f"{spec.depth_mm:.0f} mm")
        if self.app is not None:
            try:
                group = self.controller.group_for(module_id)
                if group is not None:
                    self.app.scene.selection.clear()
                    self.app.scene.selection.add(group)
                    self.app.viewport.update()
            except Exception:                        # noqa: BLE001
                pass

    # ------------------------------------------------------------------
    # Document changes
    # ------------------------------------------------------------------
    def document_changed(self) -> None:
        """Host callback: defer so the command that emitted it finishes."""
        if self._pending:
            return
        self._pending = True
        QTimer.singleShot(0, self._apply_document_change)

    def _apply_document_change(self) -> None:
        self._pending = False
        data = self.controller.document_data()
        signature = _signature(data)
        if signature != self._signature:
            self._signature = signature
            try:
                self.controller.reload()
            except Exception:                        # noqa: BLE001
                pass
        self.refresh()
        if self.window is not None and self.window.isVisible():
            self.window.refresh_from_document()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def selected_spec(self):
        item = self.module_list.currentItem()
        if item is None:
            return None
        return self.controller.project.module(item.data(Qt.UserRole))

    def new_module(self) -> None:
        from .module_form import ModuleEditorDialog
        from ..furniture import template_by_type

        template = template_by_type("armario_inferior")
        spec = template.create() if template else None
        if spec is None:
            return
        spec.code = self.controller.project.next_code(spec.type)
        dialog = ModuleEditorDialog(self.controller, spec, self)
        if dialog.exec() != QDialog.Accepted:
            return
        result = dialog.result_spec()
        try:
            self.controller.insert_module(result)
        except Exception as exc:                     # noqa: BLE001
            self._error("Inserir módulo", exc)
            return
        self._signature = _signature(self.controller.document_data())
        self.refresh()

    def edit_selected(self) -> None:
        from .module_form import ModuleEditorDialog

        spec = self.selected_spec()
        if spec is None:
            return
        dialog = ModuleEditorDialog(self.controller, spec.copy(), self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.controller.update_module(dialog.result_spec())
        except Exception as exc:                     # noqa: BLE001
            self._error("Editar módulo", exc)
            return
        self._signature = _signature(self.controller.document_data())
        self.refresh()

    def open_window(self, tab: int = 0) -> None:
        from .dialogs import FurnitureDialog

        if self.window is None:
            self.window = FurnitureDialog(self.controller, self, initial_tab=tab)
            self.window.setAttribute(Qt.WA_DeleteOnClose, False)
            self.window.finished.connect(self._window_closed)
        else:
            self.window.tabs.setCurrentIndex(max(0, min(
                tab, self.window.tabs.count() - 1)))
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def _window_closed(self, _result: int = 0) -> None:
        self._signature = _signature(self.controller.document_data())
        self.refresh()

    def show_diagnostics(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Diagnóstico — {PLUGIN_NAME}")
        dialog.resize(760, 560)
        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText(self.controller.environment_report())
        layout = QVBoxLayout(dialog)
        layout.addWidget(text)
        close = QPushButton("Fechar")
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()

    def _error(self, title: str, exc: Exception) -> None:
        logger_text = getattr(exc, "user_message", None)
        if logger_text:
            QMessageBox.warning(self, title, str(logger_text))
        else:
            QMessageBox.critical(self, title, f"Falha inesperada: {exc}")
