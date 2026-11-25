# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Diálogo 2D de Planta Baixa para desenho de paredes e geração 3D automática."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import (
    QPixmap,
)
from PySide6.QtWidgets import (
    QWidget,
)

from ..wall.plan_2d import WallGraph2D
from .mixin_calibrate import CalibrateMixin
from .mixin_dialogs import DialogsMixin
from .mixin_drawing import DrawingMixin
from .mixin_history import HistoryMixin
from .mixin_input import InputHandlingMixin
from .mixin_measurement import MeasurementMixin
from .mixin_navigation import NavigationMixin


class WallFloorplanCanvas(NavigationMixin, HistoryMixin, InputHandlingMixin, DrawingMixin, MeasurementMixin, DialogsMixin, CalibrateMixin, QWidget):
    """Canvas 2D interativo com grid, zoom, pan e cotas dinâmicas em tempo real."""

    wall_count_changed = Signal(int)
    wall_selected = Signal(int, float)  # (seg_id, length_m)
    current_length_changed = Signal(float)  # comprimento em tempo real enquanto desenha
    point_edit_hint = Signal(str)  # feedback da ferramenta de adicionar/remover pontos

    def __init__(self, graph: WallGraph2D, parent: QWidget | None = None):
        super().__init__(parent)
        self.graph = graph
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        # Visualização (Pan & Zoom)
        self._zoom = 80.0  # pixels por metro (80px = 1.0m)
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._pan_start: QPointF | None = None

        # Ferramenta ativa: "linha", "retangulo", "selecionar", "cota" ou "pontos"
        self.mode = "linha"

        # Estado de desenho
        self._start_pt: tuple[float, float] | None = None
        self._current_mouse_world: tuple[float, float] = (0.0, 0.0)
        self._snap_info: str | None = None
        self._history: list[list[tuple[float, float, float, float]]] = []

        # Guias de alinhamento com outros pontos (cantos / nós)
        self._align_guides: list[tuple[QPointF, QPointF]] = []

        # Estado de seleção e arrasto
        self._selected_seg_id: int | None = None
        self._selected_node_id: int | None = None
        self._selected_dim_id: int | None = None
        self._drag_dim_id: int | None = None
        self._drag_dim_start_mouse: tuple[float, float] | None = None
        self._drag_node_id: int | None = None
        self._drag_mid_seg_id: int | None = None
        self._drag_mid_start_mouse: tuple[float, float] | None = None
        self._drag_start_mouse: tuple[float, float] | None = None
        self._dimension_badges: dict[str, dict[str, Any]] = {}  # {badge_key: {rect, seg_id, dim_id, length_m}}
        self._room_badges: list[dict[str, Any]] = []  # [{rect, cycle_pts, name, area_m2}]
        self._next_badge_id: int = 1

        # Modo Cota Livre / Pontos Cotados
        self._cota_points: list[tuple[float, float]] = []

        # Buffer de digitação direta numérica (VCB)
        self._type_buffer: str = ""
        self._t_ref_info: dict[str, Any] | None = None

        # Linhas de projeção do pavimento inferior (underlay)
        self._underlay_lines: list[tuple[tuple[float, float], tuple[float, float]]] = []

        # Imagem de Referência / Decalque de Fundo
        self._ref_image_path: str | None = None
        self._ref_pixmap: QPixmap | None = None
        self._ref_original_pixmap: QPixmap | None = None
        self._ref_pos_world: tuple[float, float] = (0.0, 0.0)  # Canto inferior esquerdo em coords do mundo
        self._ref_width_m: float = 10.0  # Largura física da imagem no mundo
        self._ref_opacity: float = 0.5   # Opacidade 0.1 a 1.0
        self._ref_visible: bool = True
        self._ref_rotation: int = 0      # Rotação 0, 90, 180, 270

        # Estados de interação da imagem
        self._drag_ref_start: tuple[float, float] | None = None
        self._drag_ref_initial_pos: tuple[float, float] | None = None
        self._calib_points: list[tuple[float, float]] = []

