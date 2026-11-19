# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes de validação para o Zoom Livre / Atravessar Sólidos (FreeZoomManager)."""
import pytest
from PySide6.QtCore import QPoint, QPointF, Qt, QObject
from PySide6.QtGui import QWheelEvent, QVector3D
from PySide6.QtWidgets import QApplication

from trazomob.interaction.free_zoom import FreeZoomManager
from trazomob.interaction.magnetic_drag import MagneticModuleDragFilter


class DummyCamera:
    def __init__(self):
        self.target = QVector3D(0, 0, 0)
        self.distance = 2.0
        self.yaw = 0.0
        self.pitch = 0.0

    def eye(self) -> QVector3D:
        return self.target + QVector3D(self.distance, 0, 0)

    def forward(self) -> QVector3D:
        return QVector3D(-1, 0, 0)

    def move_eye(self, delta: QVector3D) -> None:
        self.target = self.target + delta


class DummyViewport(QObject):
    def __init__(self):
        super().__init__()
        self.camera = DummyCamera()
        self.updated = False
        self._invert_wheel = False

    def width(self):
        return 800

    def height(self):
        return 600

    def _pixel_to_ray(self, x: float, y: float):
        # Raio direcionado para -X
        return (self.camera.eye(), QVector3D(-1, 0, 0))

    def _world_under_cursor(self, x: float, y: float):
        # Foco a 1m à frente do olho (X = 1.0)
        return QVector3D(1.0, 0, 0)

    def _model_diag(self):
        return 5.0

    def update(self):
        self.updated = True


def test_free_zoom_toggle():
    mgr = FreeZoomManager.get_instance()
    mgr.is_enabled = False
    assert not mgr.is_enabled

    state = FreeZoomManager.toggle()
    assert state is True
    assert mgr.is_enabled is True

    state = FreeZoomManager.toggle()
    assert state is False
    assert mgr.is_enabled is False


def test_free_zoom_moves_camera_past_focus():
    mgr = FreeZoomManager.get_instance()
    mgr.is_enabled = True

    vp = DummyViewport()
    cam = vp.camera
    eye_initial = cam.eye()

    # Evento de rolagem para frente (steps = +1.0)
    pos = QPointF(400, 300)
    ev = QWheelEvent(pos, pos, QPoint(0, 0), QPoint(0, 120), Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False)

    # 1. Primeiro notch: olho aproxima do foco
    handled = FreeZoomManager.handle_wheel_event(vp, ev)
    assert handled is True
    assert vp.updated is True
    assert cam.eye().x() < eye_initial.x()

    # 2. Vários notches sucessivos: o olho deve ATRAVESSAR o foco (X=1.0) e continuar avançando sem travar
    for _ in range(25):
        FreeZoomManager.handle_wheel_event(vp, ev)

    # O olho ultrapassou a marca de 1.0 e entrou para o lado negativo ou < 1.0
    assert cam.eye().x() < 1.0
    eye_at_depth = cam.eye().x()

    # Continua avançando mais ainda sem nenhum impedimento
    for _ in range(10):
        FreeZoomManager.handle_wheel_event(vp, ev)

    assert cam.eye().x() < eye_at_depth

    # Limpa estado
    mgr.is_enabled = False


def test_event_filter_interception():
    mgr = FreeZoomManager.get_instance()
    mgr.is_enabled = True

    vp = DummyViewport()
    drag_filter = MagneticModuleDragFilter(vp, parent=vp)

    pos = QPointF(400, 300)
    ev = QWheelEvent(pos, pos, QPoint(0, 0), QPoint(0, 120), Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False)

    # O eventFilter do TrazoMob deve capturar e consumir (return True)
    consumed = drag_filter.eventFilter(vp, ev)
    assert consumed is True

    # Se desativado, o eventFilter não consome e deixa seguir o fluxo normal do IngeTrazo
    mgr.is_enabled = False
    consumed_disabled = drag_filter.eventFilter(vp, ev)
    assert consumed_disabled is False
