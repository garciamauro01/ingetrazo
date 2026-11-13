# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors and Pair Programmer.
"""Gerador de ícones vetoriais modernos para a ferramenta de Porta Paramétrica."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


def make_door_icon(size: int = 32) -> QIcon:
    """Cria um ícone vetorial elegante mostrando uma porta em perspectiva com parede e arco de abertura."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    # Cores
    accent_orange = QColor(243, 115, 41)
    wall_gray = QColor(140, 145, 155)
    leaf_wood = QColor(190, 135, 80)
    bg_frame = QColor(80, 85, 95)

    s = size / 32.0

    # 1. Parede de fundo com vão aberto
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(wall_gray))
    # Trecho esquerdo da parede
    p.drawRect(QRectF(2 * s, 4 * s, 6 * s, 24 * s))
    # Trecho direito da parede
    p.drawRect(QRectF(24 * s, 4 * s, 6 * s, 24 * s))
    # Verga superior da parede
    p.drawRect(QRectF(8 * s, 4 * s, 16 * s, 5 * s))

    # 2. Marco/Batente em volta do vão
    pen_frame = QPen(bg_frame, 1.8 * s)
    p.setPen(pen_frame)
    p.setBrush(Qt.NoBrush)
    path_frame = QPainterPath()
    path_frame.moveTo(8 * s, 28 * s)
    path_frame.lineTo(8 * s, 9 * s)
    path_frame.lineTo(24 * s, 9 * s)
    path_frame.lineTo(24 * s, 28 * s)
    p.drawPath(path_frame)

    # 3. Arco de giro no chão (indicador de abertura arquitetônica)
    pen_arc = QPen(accent_orange, 1.2 * s, Qt.DashLine)
    p.setPen(pen_arc)
    p.drawArc(QRectF(-6 * s, 14 * s, 28 * s, 28 * s), 0 * 16, 75 * 16)

    # 4. Folha da porta semi-aberta em perspectiva
    p.setPen(QPen(QColor(130, 85, 45), 1.2 * s))
    p.setBrush(QBrush(leaf_wood))
    path_leaf = QPainterPath()
    path_leaf.moveTo(8 * s, 28 * s)       # Pivô inferior
    path_leaf.lineTo(19 * s, 21 * s)      # Borda inferior aberta
    path_leaf.lineTo(19 * s, 5 * s)       # Borda superior aberta
    path_leaf.lineTo(8 * s, 9 * s)        # Pivô superior
    path_leaf.closeSubpath()
    p.drawPath(path_leaf)

    # 5. Maçaneta cromada/dourada
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor(255, 230, 120)))
    p.drawEllipse(QPointF(17 * s, 13 * s), 1.4 * s, 1.4 * s)

    # 6. Símbolo de corte/tesoura sutil ou detalhe moderno
    p.setPen(QPen(accent_orange, 1.5 * s))
    p.drawLine(QPointF(27 * s, 26 * s), QPointF(29 * s, 28 * s))

    p.end()
    return QIcon(pix)


def make_window_icon(size: int = 32) -> QIcon:
    """Cria um ícone vetorial elegante mostrando uma janela arquitetônica envidraçada com peitoril na parede."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    s = size / 32.0
    accent_orange = QColor(243, 115, 41)
    wall_gray = QColor(140, 145, 155)
    frame_color = QColor(60, 65, 75)
    glass_color = QColor(170, 215, 245, 200)

    # 1. Parede em volta do vão
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(wall_gray))
    # Trecho superior
    p.drawRect(QRectF(2 * s, 3 * s, 28 * s, 4 * s))
    # Trecho inferior (peitoril da parede)
    p.drawRect(QRectF(2 * s, 25 * s, 28 * s, 4 * s))
    # Laterais
    p.drawRect(QRectF(2 * s, 7 * s, 4 * s, 18 * s))
    p.drawRect(QRectF(26 * s, 7 * s, 4 * s, 18 * s))

    # 2. Marco/Caixilho exterior da janela
    p.setBrush(QBrush(frame_color))
    p.drawRect(QRectF(6 * s, 7 * s, 20 * s, 18 * s))

    # 3. Vidros (Folhas bipartidas)
    p.setBrush(QBrush(glass_color))
    p.drawRect(QRectF(7.5 * s, 8.5 * s, 7.5 * s, 15 * s))
    p.drawRect(QRectF(17 * s, 8.5 * s, 7.5 * s, 15 * s))

    # 4. Brilho diagonal no vidro
    p.setPen(QPen(QColor(255, 255, 255, 160), 1.2 * s))
    p.drawLine(QPointF(9 * s, 20 * s), QPointF(13 * s, 10 * s))
    p.drawLine(QPointF(18.5 * s, 20 * s), QPointF(22.5 * s, 10 * s))

    # 5. Pingadeira / Peitoril em destaque
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor(220, 225, 230)))
    p.drawRect(QRectF(5 * s, 24 * s, 22 * s, 2.2 * s))

    # 6. Ponto de acento da ferramenta (laranja)
    p.setBrush(QBrush(accent_orange))
    p.drawEllipse(QPointF(25.5 * s, 6.5 * s), 2.2 * s, 2.2 * s)

    p.end()
    return QIcon(pix)

