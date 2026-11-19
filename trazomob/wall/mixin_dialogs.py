# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Diálogo 2D de Planta Baixa para desenho de paredes e geração 3D automática."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional, List, Tuple

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

if TYPE_CHECKING:
    Point2D = Tuple[float, float]


class DialogsMixin:
    """Dialogos auxiliares de interacao do canvas de planta baixa."""

    def _prompt_calibrate_scale(self, current_measured_dist: float) -> None:
        """Abre diálogo solicitando a medida real e ajusta a escala da imagem de referência."""
        if self._ref_pixmap is None:
            return

        scale = bare_number_scale()
        u_name = model_unit()
        p = model_precision()

        cur_val_doc = current_measured_dist / scale
        val_doc, ok = QInputDialog.getDouble(
            self,
            "Calibrar Escala da Imagem",
            f"Qual é o comprimento real entre os 2 pontos clicados ({u_name})?:",
            value=round(cur_val_doc, p),
            minValue=0.001,
            maxValue=100000.0,
            decimals=p
        )
        if ok and val_doc > 0:
            target_real_m = val_doc * scale
            ratio = target_real_m / current_measured_dist
            self._ref_width_m *= ratio
            self.update()
            sync = getattr(self.window(), "_sync_reference_image_to_scene", None)
            if callable(sync):
                sync()

    def _edit_room_name_dialog(self, cycle_pts: List[Point2D], current_name: str, area_m2: float) -> None:
        """Abre diálogo para renomear individualmente o cômodo selecionado na planta 2D."""
        from PySide6.QtWidgets import QInputDialog
        novo_nome, ok = QInputDialog.getText(
            self,
            "Renomear Cômodo / Ambiente",
            f"Nome do cômodo ({area_m2:.2f} m²):",
            text=current_name
        )
        if ok and novo_nome.strip():
            nome_final = novo_nome.strip()
            self.graph.set_room_name(cycle_pts, nome_final)
            # Se for o único cômodo ou houver campo no dialog principal, atualiza também
            label_title = getattr(self.window(), "txt_amb_name", None)
            if label_title and hasattr(label_title, "setText"):
                # Se for o primeiro ou único cômodo, reflete no campo principal
                if len(self._room_badges) <= 1:
                    label_title.setText(nome_final)
            self.update()

