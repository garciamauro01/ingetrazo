# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Zoom Contínuo Livre (Estilo SketchUp / Atravessar Sólidos).

Implementa um manipulador de roda do mouse (wheel) 100% contido no plugin TrazoMob.
Quando ativado via botão de alternância, o zoom da roda não fica preso à âncora
da casca externa de sólidos nem para no min_distance da órbita:
ele translada a câmera (dolly contínuo) ao longo do raio apontado pelo cursor do mouse,
permitindo entrar e atravessar paredes, portas, armários e sólidos livremente.
"""
from __future__ import annotations

import logging
import math
from typing import Optional

from PySide6.QtCore import QEvent, QObject, QPointF
from PySide6.QtGui import QWheelEvent, QVector3D

logger = logging.getLogger("trazomob.free_zoom")


class FreeZoomManager:
    """Controlador global do modo de zoom contínuo/atravessar sólidos."""

    _instance: Optional[FreeZoomManager] = None
    _enabled: bool = False

    @classmethod
    def get_instance(cls) -> FreeZoomManager:
        if cls._instance is None:
            cls._instance = FreeZoomManager()
        return cls._instance

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @is_enabled.setter
    def is_enabled(self, val: bool) -> None:
        self._enabled = bool(val)

    @classmethod
    def toggle(cls) -> bool:
        inst = cls.get_instance()
        inst._enabled = not inst._enabled
        return inst._enabled

    @classmethod
    def handle_wheel_event(cls, viewport: QObject, event: QWheelEvent) -> bool:
        """Processa o evento de roda no Viewport aplicando o Dolly Livre estilo SketchUp."""
        if not cls.get_instance().is_enabled:
            return False

        cam = getattr(viewport, "camera", None)
        if cam is None:
            return False

        # Verifica se o viewport possui o método de projeção de raio
        pixel_to_ray = getattr(viewport, "_pixel_to_ray", None)
        if not callable(pixel_to_ray):
            return False

        # Verifica inversão de roda configurada no viewport/preferências
        steps = event.angleDelta().y() / 120.0
        if getattr(viewport, "_invert_wheel", False):
            steps = -steps

        if abs(steps) < 1e-4:
            return False

        pos: QPointF = event.position()
        ray_origin, ray_direction = pixel_to_ray(pos.x(), pos.y())
        if ray_direction is None or ray_direction.lengthSquared() < 1e-9:
            ray_direction = cam.forward()
        else:
            ray_direction = ray_direction.normalized()

        eye = cam.eye()

        # Determina a distância de referência até o que está sob o cursor
        world_under = getattr(viewport, "_world_under_cursor", None)
        focus: Optional[QVector3D] = None
        if callable(world_under):
            try:
                focus = world_under(pos.x(), pos.y())
            except Exception:
                focus = None

        if focus is not None:
            # Projeção escalar ao longo do raio de visão para saber se o foco está à frente do olho
            dist_to_focus = QVector3D.dotProduct(focus - eye, ray_direction)
        else:
            dist_to_focus = cam.distance

        # Cálculo do passo (dolly step):
        # Quando à frente do objeto: passo suave proporcional à distância (fração ~15% por notch)
        # Quando muito perto (<= 5cm) ou já tendo ultrapassado o foco/dentro do sólido:
        # mantém um passo contínuo constante (ex: 5cm a 10cm) para nunca parar nem empacar.
        diag = 10.0
        if hasattr(viewport, "_model_diag") and callable(viewport._model_diag):
            try:
                diag = max(1.0, float(viewport._model_diag()))
            except Exception:
                diag = 10.0

        step_base = max(0.04, min(0.15 * diag, 0.12))

        if dist_to_focus > 0.05:
            # Aproximação natural proporcional
            step_length = max(step_base, dist_to_focus * 0.15)
        else:
            # Atravessamento contínuo sem travas
            step_length = step_base

        delta = ray_direction * (steps * step_length)

        # Translação suave de câmera mantendo o vetor de visada idêntico
        cam.move_eye(delta)

        # Invalida o cache de zoom interno do viewport para evitar conflitos na volta ao modo nativo
        if hasattr(viewport, "_zoom_focus"):
            viewport._zoom_focus = None

        # Redesenha a cena
        viewport.update()
        return True
