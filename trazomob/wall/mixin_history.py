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



class HistoryMixin:
    """Historico de desenho, undo e limpeza do canvas de planta baixa."""

    def _save_history(self) -> None:
        # Snapshot completo: preserva IDs de nós/segmentos/cotas, referências
        # geométricas, flags ``driving`` e alturas individuais.
        self._history.append(self.graph.to_dict())

    def undo(self) -> bool:
        if not self._history:
            if self._start_pt is not None:
                self._start_pt = None
                self.update()
                return True
            return False

        last_state = self._history.pop()
        if isinstance(last_state, dict) and "nodes" in last_state:
            self.graph.load_dict(last_state)
        elif isinstance(last_state, dict):
            # Compatibilidade com histórico antigo (apenas segmentos/cotas).
            self.graph.clear()
            for item in last_state.get("segments", []):
                x1, y1, x2, y2, th, h = item
                self.graph.add_segment(x1, y1, x2, y2, thickness=th, height=h)
            for d in last_state.get("dimensions", []):
                self.graph.add_dimension(
                    d["p1"], d["p2"], seg_id=d.get("seg_id"),
                    offset=d.get("offset", 0.25),
                    driving=d.get("driving", True),
                )
                dim = self.graph.dimensions.get(d["id"])
                if dim is not None:
                    dim.node_a_id = d.get("node_a_id")
                    dim.node_b_id = d.get("node_b_id")
        else:
            # Compatibilidade com histórico legado simples
            self.graph.clear()
            for x1, y1, x2, y2 in last_state:
                self.graph.add_segment(x1, y1, x2, y2)
        self._start_pt = None
        self._selected_dim_id = None
        self._selected_seg_id = None
        self._selected_node_id = None
        self.wall_count_changed.emit(len(self.graph.segments))
        self.update()
        return True

    def clear_all(self) -> None:
        self._save_history()
        self.graph.clear()
        self._start_pt = None
        self.wall_count_changed.emit(0)
        self.update()

