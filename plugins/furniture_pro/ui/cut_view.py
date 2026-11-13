# SPDX-License-Identifier: GPL-3.0-or-later
"""Fast schematic viewer for the cutting plan.

Qt's SVG widget would redraw the whole plan on every scroll; this painter
draws only the boards it needs and keeps the code labels legible at any
zoom.  It is a preview, not a nesting editor.
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


class CutPlanView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.plan = None
        self.margin = 14.0
        self.gap = 16.0
        self.label_height = 18.0
        self.setMinimumHeight(240)
        self.setToolTip("Prévia do plano de corte: códigos iguais aos da "
                        "lista de peças.")

    def set_plan(self, plan) -> None:
        self.plan = plan
        self.updateGeometry()
        self.update()

    def _board_height(self, board, width: float) -> float:
        if not board.length_mm:
            return 80.0
        return max(40.0, width * board.width_mm / board.length_mm)

    def sizeHint(self):
        from PySide6.QtCore import QSize
        if self.plan is None or not self.plan.boards:
            return QSize(320, 180)
        width = 560.0
        total = self.margin
        columns = 2 if len(self.plan.boards) > 1 else 1
        cell_w = (width - self.margin * 2) / columns
        rows = (len(self.plan.boards) + columns - 1) // columns
        for index in range(min(rows, 4)):
            total += 120
        return QSize(int(width), int(total + self.margin))

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.fillRect(self.rect(), QColor("#f7f5f0"))
        if self.plan is None or not self.plan.boards:
            painter.setPen(QPen(QColor("#6b7280")))
            painter.setFont(QFont("Arial", 10))
            painter.drawText(self.rect(), Qt.AlignCenter,
                             "Nenhum plano de corte calculado.")
            painter.end()
            return
        columns = 2 if len(self.plan.boards) > 1 else 1
        usable_w = max(200.0, self.width() - 2 * self.margin)
        cell_w = usable_w / columns
        painter.setFont(QFont("Arial", 8))
        for index, board in enumerate(self.plan.boards):
            col = index % columns
            row = index // columns
            board_w = cell_w - self.gap
            board_h = self._board_height(board, board_w)
            row_h = board_h + self.label_height + self.gap
            x = self.margin + col * cell_w
            y = self.margin + row * row_h
            painter.setPen(QPen(QColor("#334155")))
            painter.setFont(QFont("Arial", 8, QFont.Bold))
            painter.drawText(
                QRectF(x, y, board_w, self.label_height),
                Qt.AlignLeft | Qt.AlignVCenter,
                f"Chapa {board.index} · {board.material_name} · "
                f"{board.length_mm:.0f} × {board.width_mm:.0f} mm · "
                f"{board.utilization * 100:.0f}%")
            top = y + self.label_height
            painter.setBrush(QColor("#fbf9f4"))
            painter.setPen(QPen(QColor("#475569"), 1))
            painter.drawRect(QRectF(x, top, board_w, board_h))
            sx = board_w / max(1.0, board.length_mm)
            sy = board_h / max(1.0, board.width_mm)
            painter.setFont(QFont("Arial", 6))
            for placement in board.placements:
                rect = QRectF(x + placement.x_mm * sx,
                              top + placement.y_mm * sy,
                              placement.length_mm * sx,
                              placement.width_mm * sy)
                painter.setBrush(QColor("#d8c8ab"))
                painter.setPen(QPen(QColor("#8a7554"), 0.6))
                painter.drawRect(rect)
                if rect.width() > 20 and rect.height() > 10:
                    painter.setPen(QPen(QColor("#3f3424")))
                    painter.drawText(rect.adjusted(1, 0, -1, -1),
                                     Qt.AlignCenter, placement.code)
        painter.end()
