# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""A grade de miniaturas dos diálogos de biblioteca.

Um ``QListWidget`` em ``IconMode`` mede cada item pelo espaço que o texto e o
ícone ocupam. Sem miniatura — origem ausente, conversão que falhou, thumbnail
ainda não gerada — um nome curto ocupa só ~12 px de altura dentro de uma
célula de ~142 px. O clique no resto da célula não seleciona nada, embora o
usuário veja uma casa inteira; as setas continuam funcionando porque navegam
por ``currentIndex``, e o botão Inserir lê ``currentItem``.

O delegate abaixo dá a todo item o tamanho da célula, com ou sem miniatura,
para que a área de clique coincida com o que está desenhado.
"""
from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QListWidget, QStyledItemDelegate


class CellDelegate(QStyledItemDelegate):
    """Faz a área de clique do item coincidir com a célula do grid."""

    def __init__(self, grid: QSize, parent=None) -> None:
        super().__init__(parent)
        self._grid = QSize(grid)

    def sizeHint(self, option, index):
        # Um pouco menor que a célula: as bordas continuam livres e itens
        # vizinhos não se sobrepõem, mesmo com nomes que quebram muitas linhas.
        return QSize(max(1, self._grid.width() - 4),
                     max(1, self._grid.height() - 4))


def configure(widget: QListWidget, *, icon: int, grid: QSize) -> None:
    """Aplica o modo ícone e instala o delegate de clique cheio."""
    widget.setViewMode(QListWidget.IconMode)
    widget.setIconSize(QSize(icon, icon))
    widget.setGridSize(grid)
    widget.setResizeMode(QListWidget.Adjust)
    widget.setMovement(QListWidget.Static)
    widget.setWordWrap(True)
    widget.setItemDelegate(CellDelegate(grid, widget))
