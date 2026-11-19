# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Diálogo 2D de Planta Baixa para desenho de paredes e geração 3D automática."""
from __future__ import annotations

import math
from typing import Optional, List, Tuple

from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import (
    QPainter,
    QPen,
    QColor,
    QBrush,
    QFont,
    QPolygonF,
    QWheelEvent,
    QMouseEvent,
    QKeyEvent,
    QPixmap,
    QTransform,
)
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QDoubleSpinBox,
    QCheckBox,
    QFrame,
    QSplitter,
    QToolButton,
    QButtonGroup,
    QInputDialog,
    QComboBox,
    QSlider,
    QFileDialog,
    QGroupBox,
    QScrollArea,
    QMessageBox,
)

from PySide6.QtGui import QVector3D
from core.image_plane import ImagePlane
from core.units import format_length, model_unit, model_precision, bare_number_scale
from ..wall.plan_2d import WallGraph2D, WallNode2D, dist_2d
from ..wall.mesh_builder import WallMeshBuilder



class NavigationMixin:
    """Navegacao, zoom e conversao mundo/tela do canvas de planta baixa."""

    def update_cursor(self, hovering_handle: bool = False) -> None:
        """Atualiza o ponteiro do mouse de acordo com a ferramenta ativa e contexto de hover."""
        if self._pan_start is not None:
            self.setCursor(Qt.ClosedHandCursor)
        elif self.mode == "calibrar_ref":
            self.setCursor(Qt.CrossCursor)
        elif self.mode == "mover_ref":
            self.setCursor(Qt.OpenHandCursor if self._drag_ref_start is None else Qt.ClosedHandCursor)
        elif self.mode in ("linha", "retangulo", "cota", "pontos"):
            # Modo desenho ou cotagem: cruz de precisão (estilo CAD)
            self.setCursor(Qt.CrossCursor)
        elif self.mode == "selecionar":
            if self._drag_node_id is not None:
                self.setCursor(Qt.SizeAllCursor)
            elif hovering_handle:
                # Pairando sobre um nó arrastável
                self.setCursor(Qt.SizeAllCursor)
            else:
                # Modo seleção: seta padrão
                self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def reset_view(self) -> None:
        self._offset_x = self.width() / 2.0
        self._offset_y = self.height() / 2.0
        self._zoom = 80.0
        self.update()

    def zoom_extents(self) -> None:
        """Enquadra a planta inteira ou a imagem de referência no canvas ajustando zoom e deslocamento (pan)."""
        xs = [n.x for n in self.graph.nodes.values()]
        ys = [n.y for n in self.graph.nodes.values()]

        if self._ref_pixmap is not None and self._ref_visible:
            rx, ry = self._ref_pos_world
            rw = self._ref_width_m
            rh = rw * (self._ref_pixmap.height() / max(1, self._ref_pixmap.width()))
            xs.extend([rx, rx + rw])
            ys.extend([ry, ry + rh])

        if not xs:
            self.reset_view()
            return
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        span_x = max(0.5, max_x - min_x)
        span_y = max(0.5, max_y - min_y)

        w = max(200.0, float(self.width()))
        h = max(200.0, float(self.height()))
        margin = 80.0

        scale_x = (w - margin * 2.0) / span_x
        scale_y = (h - margin * 2.0) / span_y
        fit_zoom = max(10.0, min(scale_x, scale_y, 300.0))

        mid_x = (min_x + max_x) / 2.0
        mid_y = (min_y + max_y) / 2.0

        self._zoom = fit_zoom
        self._offset_x = (w / 2.0) - mid_x * self._zoom
        self._offset_y = (h / 2.0) + mid_y * self._zoom
        self.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._offset_x == 0.0 and self._offset_y == 0.0:
            self._offset_x = self.width() / 2.0
            self._offset_y = self.height() / 2.0

    def world_to_screen(self, wx: float, wy: float) -> QPointF:
        sx = self._offset_x + wx * self._zoom
        sy = self._offset_y - wy * self._zoom  # Inverte eixo Y para padrão CAD (+Y para cima)
        return QPointF(sx, sy)

    def screen_to_world(self, sx: float, sy: float) -> Tuple[float, float]:
        wx = (sx - self._offset_x) / self._zoom
        wy = -(sy - self._offset_y) / self._zoom
        return wx, wy

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1.0 / 1.15

        # Zoom centrado no mouse
        mouse_pos = event.position()
        wx, wy = self.screen_to_world(mouse_pos.x(), mouse_pos.y())

        self._zoom = max(10.0, min(1000.0, self._zoom * factor))
        self._offset_x = mouse_pos.x() - wx * self._zoom
        self._offset_y = mouse_pos.y() + wy * self._zoom
        self.update()

