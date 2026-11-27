# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Tab Page Component (CollapsibleSection) for the TrazoMob Sidebar.

Provides a lean tab page container with an integrated QFormLayout and
visibility/tooltip control on the parent QTabWidget, without a redundant header.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QLabel,
    QLayout,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class CollapsibleSection(QWidget):
    """Lean tab page with integrated QFormLayout."""

    toggled = Signal(bool)

    def __init__(
        self,
        title: str,
        icon_text: str = "",
        parent: QWidget | None = None,
        collapsed: bool = False,
    ) -> None:
        super().__init__(parent)
        self._is_collapsed = False
        self._title = title
        self._icon_text = icon_text
        self._tab_widget: QTabWidget | None = None
        self._tab_index: int = -1

        # Kept hidden only for compatibility with set_badge() calls
        self._lbl_badge = QLabel("", self)
        self._lbl_badge.setVisible(False)

        # Main Tab Page Layout (straight to content, no redundant title bar)
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(2, 4, 2, 4)
        self._main_layout.setSpacing(6)

        # ─── FORM CONTENT CONTAINER ───
        self._content_area = QFrame(self)
        self._content_area.setObjectName("tabSectionContent")
        self._content_area.setStyleSheet(
            """
            QFrame#tabSectionContent {
                background-color: palette(base);
                border: 1px solid palette(midlight);
                border-radius: 5px;
                padding: 6px;
            }
            """
        )
        self._content_layout = QVBoxLayout(self._content_area)
        self._content_layout.setContentsMargins(6, 6, 6, 6)
        self._content_layout.setSpacing(6)

        self._form_layout = QFormLayout()
        self._form_layout.setContentsMargins(0, 0, 0, 0)
        self._form_layout.setSpacing(6)
        self._content_layout.addLayout(self._form_layout)

        self._main_layout.addWidget(self._content_area)
        self._main_layout.addStretch(1)

    def bind_tab(self, tab_widget: QTabWidget, index: int) -> None:
        """Associates this page with the corresponding index in the QTabWidget."""
        self._tab_widget = tab_widget
        self._tab_index = index

    def is_tab_visible(self) -> bool:
        """Retorna se a aba vinculada no QTabWidget está visível."""
        if self._tab_widget is not None and self._tab_index >= 0:
            return self._tab_widget.isTabVisible(self._tab_index)
        return self.isVisible()

    def set_tab_visible(self, visible: bool) -> None:
        """Exibe ou oculta a aba correspondente no QTabWidget."""
        if self._tab_widget is not None and self._tab_index >= 0:
            self._tab_widget.setTabVisible(self._tab_index, bool(visible))
            if not visible and self._tab_widget.currentIndex() == self._tab_index:
                self._tab_widget.setCurrentIndex(0)
        else:
            super().setVisible(visible)

    @property
    def form_layout(self) -> QFormLayout:
        """Acesso direto ao QFormLayout interno."""
        return self._form_layout

    def add_row(self, *args) -> None:
        """Atalho conveniente para adicionar linhas diretamente ao QFormLayout interno."""
        self._form_layout.addRow(*args)

    def set_content_layout(self, layout: QLayout) -> None:
        """Define o layout interno de widgets."""
        QWidget().setLayout(self._content_layout)
        self._content_layout = layout
        self._content_area.setLayout(layout)

    def add_widget(self, widget: QWidget) -> None:
        """Adiciona um widget ao corpo da aba."""
        self._content_layout.addWidget(widget)

    def add_layout(self, layout: QLayout) -> None:
        """Adiciona um sub-layout ao corpo da aba."""
        self._content_layout.addLayout(layout)

    def set_badge(self, text: str) -> None:
        """Atualiza o tooltip da aba com o resumo rápido, sem ocupar espaço visual."""
        self._lbl_badge.setText(text or "")
        if self._tab_widget is not None and self._tab_index >= 0:
            if text:
                self._tab_widget.setTabToolTip(self._tab_index, f"{self._title}: {text}")
            else:
                self._tab_widget.setTabToolTip(self._tab_index, self._title)

    def is_collapsed(self) -> bool:
        return self._is_collapsed

    def set_collapsed(self, collapsed: bool) -> None:
        self._is_collapsed = collapsed
        if not collapsed and self._tab_widget is not None and self._tab_index >= 0:
            self._tab_widget.setCurrentIndex(self._tab_index)
        self.toggled.emit(not self._is_collapsed)

    def toggle(self) -> None:
        self.set_collapsed(not self._is_collapsed)
