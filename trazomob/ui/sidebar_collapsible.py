# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Componente de Página de Aba (CollapsibleSection) para a Sidebar do TrazoMob.

Fornece um container enxuto de página de aba com QFormLayout integrado
e controle de visibilidade e tooltip da aba no QTabWidget pai, sem cabeçalho redundante.
"""
from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QLabel,
    QFrame,
    QLayout,
    QTabWidget,
)


class CollapsibleSection(QWidget):
    """Página de aba enxuta com QFormLayout integrado."""

    toggled = Signal(bool)

    def __init__(
        self,
        title: str,
        icon_text: str = "",
        parent: Optional[QWidget] = None,
        collapsed: bool = False,
    ) -> None:
        super().__init__(parent)
        self._is_collapsed = False
        self._title = title
        self._icon_text = icon_text
        self._tab_widget: Optional[QTabWidget] = None
        self._tab_index: int = -1

        # Mantido oculto apenas para compatibilidade de chamadas a set_badge()
        self._lbl_badge = QLabel("", self)
        self._lbl_badge.setVisible(False)

        # Layout Principal da Página da Aba (direto ao conteúdo, sem barra de título redundante)
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(2, 4, 2, 4)
        self._main_layout.setSpacing(6)

        # ─── CONTAINER DE CONTEÚDO DO FORMULÁRIO ───
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
        """Associa esta página ao índice correspondente no QTabWidget."""
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
