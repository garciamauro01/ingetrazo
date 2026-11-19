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



class CalibrateMixin:
    """Gerenciamento de imagem de referencia e calibracao do canvas."""

    def set_reference_image(self, file_path: str, pos_world: Optional[Tuple[float, float]] = None,
                            width_m: Optional[float] = None, opacity: float = 0.5,
                            rotation: int = 0, visible: bool = True) -> bool:
        """Carrega imagem de referência e define escala e posicionamento."""
        pm = QPixmap(file_path)
        if pm.isNull():
            return False
        self._ref_image_path = file_path
        self._ref_original_pixmap = pm
        self._ref_rotation = rotation % 360
        if self._ref_rotation == 0:
            self._ref_pixmap = pm
        else:
            tr = QTransform().rotate(self._ref_rotation)
            self._ref_pixmap = pm.transformed(tr, Qt.SmoothTransformation)

        aspect = self._ref_pixmap.height() / max(1, self._ref_pixmap.width())
        self._ref_width_m = float(width_m) if (width_m is not None and width_m > 0) else 10.0
        height_m = self._ref_width_m * aspect

        if pos_world is not None:
            self._ref_pos_world = (float(pos_world[0]), float(pos_world[1]))
        else:
            # Centraliza a imagem na origem
            self._ref_pos_world = (-self._ref_width_m / 2.0, -height_m / 2.0)

        self._ref_opacity = float(opacity)
        self._ref_visible = bool(visible)
        self.update()
        return True

    def rotate_reference_image(self, degrees: int = 90) -> None:
        """Rotaciona a imagem de referência em múltiplos de 90 graus."""
        if self._ref_original_pixmap is None:
            return
        self._ref_rotation = (self._ref_rotation + degrees) % 360
        if self._ref_rotation == 0:
            self._ref_pixmap = self._ref_original_pixmap
        else:
            tr = QTransform().rotate(self._ref_rotation)
            self._ref_pixmap = self._ref_original_pixmap.transformed(tr, Qt.SmoothTransformation)
        self.update()

    def remove_reference_image(self) -> None:
        """Remove a imagem de referência do canvas."""
        self._ref_image_path = None
        self._ref_pixmap = None
        self._ref_original_pixmap = None
        self._calib_points.clear()
        if self.mode in ("calibrar_ref", "mover_ref"):
            self.mode = "linha"
            self.update_cursor()
        self.update()

