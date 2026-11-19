# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Diálogo 2D de Planta Baixa para desenho de paredes e geração 3D automática."""
from __future__ import annotations

import math
from typing import Any, Dict, Optional, List, Tuple

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

from .mixin_navigation import NavigationMixin
from .mixin_history import HistoryMixin
from .mixin_input import InputHandlingMixin
from .mixin_drawing import DrawingMixin
from .mixin_measurement import MeasurementMixin
from .mixin_dialogs import DialogsMixin
from .mixin_calibrate import CalibrateMixin

class WallFloorplanCanvas(NavigationMixin, HistoryMixin, InputHandlingMixin, DrawingMixin, MeasurementMixin, DialogsMixin, CalibrateMixin, QWidget):
    """Canvas 2D interativo com grid, zoom, pan e cotas dinâmicas em tempo real."""

    wall_count_changed = Signal(int)
    wall_selected = Signal(int, float)  # (seg_id, length_m)
    current_length_changed = Signal(float)  # comprimento em tempo real enquanto desenha
    point_edit_hint = Signal(str)  # feedback da ferramenta de adicionar/remover pontos

    def __init__(self, graph: WallGraph2D, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.graph = graph
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        # Visualização (Pan & Zoom)
        self._zoom = 80.0  # pixels por metro (80px = 1.0m)
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._pan_start: Optional[QPointF] = None

        # Ferramenta ativa: "linha", "retangulo", "selecionar", "cota" ou "pontos"
        self.mode = "linha"

        # Estado de desenho
        self._start_pt: Optional[Tuple[float, float]] = None
        self._current_mouse_world: Tuple[float, float] = (0.0, 0.0)
        self._snap_info: Optional[str] = None
        self._history: List[List[Tuple[float, float, float, float]]] = []

        # Guias de alinhamento com outros pontos (cantos / nós)
        self._align_guides: List[Tuple[QPointF, QPointF]] = []

        # Estado de seleção e arrasto
        self._selected_seg_id: Optional[int] = None
        self._selected_node_id: Optional[int] = None
        self._selected_dim_id: Optional[int] = None
        self._drag_dim_id: Optional[int] = None
        self._drag_dim_start_mouse: Optional[Tuple[float, float]] = None
        self._drag_node_id: Optional[int] = None
        self._drag_mid_seg_id: Optional[int] = None
        self._drag_mid_start_mouse: Optional[Tuple[float, float]] = None
        self._drag_start_mouse: Optional[Tuple[float, float]] = None
        self._dimension_badges: Dict[str, Dict[str, Any]] = {}  # {badge_key: {rect, seg_id, dim_id, length_m}}
        self._room_badges: List[Dict[str, Any]] = []  # [{rect, cycle_pts, name, area_m2}]
        self._next_badge_id: int = 1

        # Modo Cota Livre / Pontos Cotados
        self._cota_points: List[Tuple[float, float]] = []

        # Buffer de digitação direta numérica (VCB)
        self._type_buffer: str = ""
        self._t_ref_info: Optional[Dict[str, Any]] = None

        # Linhas de projeção do pavimento inferior (underlay)
        self._underlay_lines: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []

        # Imagem de Referência / Decalque de Fundo
        self._ref_image_path: Optional[str] = None
        self._ref_pixmap: Optional[QPixmap] = None
        self._ref_original_pixmap: Optional[QPixmap] = None
        self._ref_pos_world: Tuple[float, float] = (0.0, 0.0)  # Canto inferior esquerdo em coords do mundo
        self._ref_width_m: float = 10.0  # Largura física da imagem no mundo
        self._ref_opacity: float = 0.5   # Opacidade 0.1 a 1.0
        self._ref_visible: bool = True
        self._ref_rotation: int = 0      # Rotação 0, 90, 180, 270

        # Estados de interação da imagem
        self._drag_ref_start: Optional[Tuple[float, float]] = None
        self._drag_ref_initial_pos: Optional[Tuple[float, float]] = None
        self._calib_points: List[Tuple[float, float]] = []

