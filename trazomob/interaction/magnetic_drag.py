# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Manipulador de Aderência Magnética, Movimentação por Arraste e Cotas Inteligentes para Módulos.

Instala um eventFilter no Viewport (100% contido no plugin) para:
1. Detectar clique e arraste com o botão esquerdo sobre um módulo de marcenaria;
2. Desativar a seleção retangular (box-select) apenas durante o arraste de módulos;
3. Proporcionar Aderência Magnética Inteligente (Snap Magnético):
   - Ao Piso (Z = 0): A base do móvel se fixa magneticamente no chão.
   - Às Paredes: Quando o móvel se aproxima de uma parede contínua,
     a face escolhida em `snap_parede` (padrão: traseira) encosta na face
     interna da parede com 0.0mm de folga. O valor "nenhum" desliga o snap
     magnético para aquela peça.
   - Elevação na Parede: Ao erguer o cursor sobre a parede, o módulo rompe a atração do piso
     e desliza verticalmente fixado na parede (ideal para armários aéreos e nichos).
4. Cotas Dinâmicas de Snap em Tempo Real:
   - Mede as distâncias para todos os lados (4 direções principais + piso/teto) até as paredes
     ou objetos mais próximos.
   - Renderiza linhas de cota com setas e etiquetas com fundo escuro e valores em mm.
   - Mantém as cotas visíveis na tela enquanto o módulo estiver selecionado.
5. Fornecer preview suave em tempo real e registrar o comando reversível (Undo/Redo) no final.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Tuple

from PySide6.QtCore import QObject, QPointF
from PySide6.QtGui import QColor, QVector3D

from core.group import Group

from .magnetic_drag_context import MagneticDragContextMixin
from .magnetic_drag_input import FastTranslateGroupCommand, MagneticDragInputMixin
from .magnetic_drag_snap import (
    MagneticDragSnapMixin,
    _extract_esquadria_u_dir,
    draw_snap_dimension_segment,
    get_bounds_min_projection,
    get_module_bounds,
    get_module_reference_bounds,
    is_esquadria_group,
)

logger = logging.getLogger("trazomob.magnetic_drag")

__all__ = [
    "MagneticModuleDragFilter",
    "FastTranslateGroupCommand",
    "_extract_esquadria_u_dir",
    "draw_snap_dimension_segment",
    "get_bounds_min_projection",
    "get_module_bounds",
    "get_module_reference_bounds",
    "is_esquadria_group",
]


class MagneticModuleDragFilter(
    MagneticDragInputMixin,
    MagneticDragContextMixin,
    MagneticDragSnapMixin,
    QObject,
):
    """Filtro de eventos Qt para movimentação com arraste, aderência magnética e cotas dinâmicas."""

    DRAG_THRESHOLD_PX = 5.0
    SNAP_FLOOR_DISTANCE = 0.15   # 15 cm de atração ao piso
    SNAP_WALL_DISTANCE = 0.25    # 25 cm de atração às paredes

    snap_enabled: bool = True    # Alternância global dos snaps magnéticos

    def __init__(self, viewport, parent: Optional[QObject] = None) -> None:
        super().__init__(parent or viewport)
        self.viewport = viewport

        self._mouse_pressed = False
        self._press_pos: Optional[QPointF] = None
        self._drag_active = False

        self._target_module: Optional[Group] = None
        self._affected_groups: List[Group] = []
        self._start_world_pt: Optional[QVector3D] = None
        self._module_orig_bounds: Optional[Tuple[float, float, float, float, float, float]] = None
        self._active_locked_wall_face = None
        self._press_wall_u: Optional[float] = None
        self._press_wall_z: Optional[float] = None
        self._axis_lock: Optional[str] = None  # None, 'z', 'u', 'x', 'y'
        self._last_event_pos: Optional[QPointF] = None
        self._drag_plane_normal: Optional[QVector3D] = None
        self._drag_grab_dist: float = 1.0
        self._cam_started_inside_module: bool = False
        self._drag_is_esquadria: bool = False

        # Estado dinâmico de cotas
        self._active_cota_items: List[Tuple[QVector3D, QVector3D, QColor, float]] = []
        self._cota_cache_key: Optional[tuple] = None
        # Estado dinâmico de preview para Drag & Drop da Ribbon
        self._active_drop_preview: Optional[dict[str, Any]] = None

        # Garante que o Viewport aceite eventos de Drag & Drop
        if hasattr(self.viewport, "setAcceptDrops"):
            self.viewport.setAcceptDrops(True)

        # Instala overlay para desenhar as cotas na passagem 2D do Viewport
        self._install_overlay()

    def _install_overlay(self) -> None:
        """Garante que a função de pintura das cotas seja chamada durante a renderização do Viewport."""
        if not hasattr(self.viewport, "_ext_overlays") or self.viewport._ext_overlays is None:
            self.viewport._ext_overlays = []
        if self._draw_cota_overlay not in self.viewport._ext_overlays:
            self.viewport._ext_overlays.append(self._draw_cota_overlay)

        # Conecta a mudanças na cena para atualizar cotas automaticamente
        if hasattr(self.viewport, "sceneVersionChanged"):
            try:
                self.viewport.sceneVersionChanged.connect(self._on_scene_or_selection_changed)
            except Exception as exc:
                logger.debug("não foi possível conectar sceneVersionChanged: %s", exc)

    def cleanup(self) -> None:
        """Remove event filter, overlay e conexões deste filtro ao fechar o documento."""
        vp = self.viewport
        if vp is not None:
            overlays = getattr(vp, "_ext_overlays", None)
            if isinstance(overlays, list) and self._draw_cota_overlay in overlays:
                overlays.remove(self._draw_cota_overlay)
            sig = getattr(vp, "sceneVersionChanged", None)
            if sig is not None:
                try:
                    sig.disconnect(self._on_scene_or_selection_changed)
                except Exception:
                    pass
            remover = getattr(vp, "removeEventFilter", None)
            if callable(remover):
                try:
                    remover(self)
                except Exception:
                    pass
        self._active_cota_items = []
        self._cota_cache_key = None
        self._active_drop_preview = None
        self._target_module = None
        self._affected_groups = []

