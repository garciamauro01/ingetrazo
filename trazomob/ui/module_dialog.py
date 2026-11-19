# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Interface gráfica principal do TrazoMob (TrazoMobDialog)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QDialog

from ..integrations import platform as host
from ..interaction.module_aligner import ModuleAlignerMixin
from ..production.cutlist_tab import CutListTabMixin
from ..ui.module_gallery import DialogGalleryMixin
from .module_dialog_build import ModuleDialogBuildMixin
from .module_dialog_form import ModuleDialogFormMixin
from .module_dialog_actions import ModuleDialogActionsMixin
from .module_dialog_style import ModuleDialogStyleMixin
from .module_dialog_sections import ModuleDialogSectionsMixin
from .module_dialog_options import ModuleDialogOptionsMixin
from .module_dialog_hardware import ModuleDialogHardwareMixin

if TYPE_CHECKING:
    from core.group import Group


class TrazoMobDialog(
    ModuleDialogBuildMixin,
    ModuleDialogSectionsMixin,
    ModuleDialogOptionsMixin,
    ModuleDialogFormMixin,
    ModuleDialogActionsMixin,
    ModuleDialogStyleMixin,
    ModuleDialogHardwareMixin,
    QDialog,
    ModuleAlignerMixin,
    CutListTabMixin,
    DialogGalleryMixin,
):
    """Janela principal com Biblioteca Paramétrica Dinâmica e Plano de Corte."""

    def __init__(self, viewport, parent=None):
        super().__init__(parent)
        self._host_window = host.window_of(window=parent, viewport=viewport)
        self._fallback_viewport = viewport
        self._fallback_scene = getattr(viewport, "scene", None)
        # Transforma o diálogo em janela de primeira classe com Maximizar, Minimizar e redimensionamento nativo
        self.setWindowFlags(Qt.Window)
        self.setSizeGripEnabled(True)
        self._pedra_widgets = []  # populated in _build_modules_tab
        self._fundo_widgets = []
        self._travessa_widgets = []
        self._gaveta_widgets = []

        # Tamanho mínimo flexível para que a janela nunca trave o redimensionamento
        self.setMinimumSize(720, 460)

        self._editing_module: Group | None = None
        self._parts: list[dict[str, Any]] = []
        self._detect_selected_module()
        self._build_ui()
        self._reload_parts()

        st = QSettings()
        geo = st.value("ui/trazomob_geometry")
        if geo:
            self.restoreGeometry(geo)
        else:
            screen = self.screen() or (QApplication.primaryScreen() if QApplication.instance() else None)
            if screen:
                avail = screen.availableGeometry()
                init_w = min(1000, max(750, int(avail.width() * 0.70)))
                init_h = min(580, max(460, int(avail.height() * 0.68)))
                pos_x = avail.x() + (avail.width() - init_w) // 2
                pos_y = avail.y() + (avail.height() - init_h) // 2
                self.setGeometry(pos_x, pos_y, init_w, init_h)
            else:
                self.resize(920, 540)

    @property
    def viewport(self):
        return host.active_viewport(window=self._host_window, viewport=self._fallback_viewport)

    @viewport.setter
    def viewport(self, vp) -> None:
        if vp is not None:
            self._fallback_viewport = vp
            if hasattr(vp, "scene"):
                self._fallback_scene = vp.scene

    @property
    def scene(self):
        vp = self.viewport
        if vp is not None and hasattr(vp, "scene"):
            return vp.scene
        return self._fallback_scene

    @scene.setter
    def scene(self, sc) -> None:
        self._fallback_scene = sc

    def _sync_category_for_editing_module(self) -> None:
        if self._editing_module is None or not hasattr(self, "cb_category"):
            return
        from ..domain.catalog import MODULE_CATALOG
        from ..domain.schema import module_params
        ed_tipo = module_params(self._editing_module).get("tipo")
        if not ed_tipo:
            return
        for cat_name, items in MODULE_CATALOG.items():
            if any(it.get("id") == ed_tipo for it in items):
                if self.cb_category.currentText() != cat_name:
                    self.cb_category.blockSignals(True)
                    self.cb_category.setCurrentText(cat_name)
                    self.cb_category.blockSignals(False)
                    if hasattr(self, "_populate_module_cards"):
                        self._populate_module_cards()
                return

    def sync_to_active_document(self, viewport=None) -> None:
        """Ressincroniza o diálogo com o viewport/cena do documento atualmente ativo."""
        if viewport is not None:
            self._fallback_viewport = viewport
            win = host.window_of(viewport=viewport)
            if win is not None:
                self._host_window = win
        vp = self.viewport
        if vp is not None and hasattr(vp, "scene"):
            self._fallback_scene = vp.scene
        self._detect_selected_module()
        if self._editing_module is not None and hasattr(self, "list_modules"):
            self._sync_category_for_editing_module()
            self._load_module_values_if_editing()
        if hasattr(self, "_reload_parts"):
            self._reload_parts()

    def _save_geom(self) -> None:
        QSettings().setValue("ui/trazomob_geometry", self.saveGeometry())

    def accept(self) -> None:
        self._save_geom()
        super().accept()

    def reject(self) -> None:
        self._save_geom()
        super().reject()

    def closeEvent(self, event) -> None:
        self._save_geom()
        super().closeEvent(event)
