# SPDX-License-Identifier: GPL-3.0-or-later
"""Small offscreen renderer used for thumbnails and preview export.

This is a schematic isometric renderer, not a replacement for the viewport's
renderer.  It exists so a module can be shown in a report or in a file dialog
preview without a GPU context.
"""
from __future__ import annotations

import math
from pathlib import Path

from ..core.models import BuildResult, Material


def render_module_image(result: BuildResult,
                        materials: dict[str, Material] | None = None,
                        width: int = 640, height: int = 480):
    """Return a QImage with an isometric view of the generated panels."""
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPolygonF

    materials = materials or {}
    image = QImage(width, height, QImage.Format_ARGB32)
    image.fill(QColor("#f6f4ee"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)
    try:
        panels = result.panels
        if not panels:
            painter.setPen(QPen(QColor("#6b7280")))
            painter.drawText(QRectF(0, 0, width, height), Qt.AlignCenter,
                             "Sem geometria")
            return image
        xs, ys, zs = [], [], []
        for panel in panels:
            x, y, z = panel.position_mm
            sx, sy, sz = panel.size_mm
            xs.extend((x, x + sx))
            ys.extend((y, y + sy))
            zs.extend((z, z + sz))
        span_x = max(1.0, max(xs) - min(xs))
        span_y = max(1.0, max(ys) - min(ys))
        span_z = max(1.0, max(zs) - min(zs))
        scale = min(width * 0.72 / max(span_x + span_y, 1.0),
                    height * 0.72 / max(span_z + (span_x + span_y) * 0.5, 1.0))
        cx = (min(xs) + max(xs)) / 2.0
        cy = (min(ys) + max(ys)) / 2.0
        cz = (min(zs) + max(zs)) / 2.0
        ox, oy = width / 2.0, height / 2.0 + span_z * scale * 0.25

        def project(point):
            px, py, pz = point
            ix = (px - cx) - (py - cy)
            iz = (px - cx) * 0.5 + (py - cy) * 0.5 - (pz - cz)
            return QPointF(ox + ix * scale * 0.78, oy + iz * scale * 0.78)

        faces = []
        for panel in panels:
            x, y, z = panel.position_mm
            sx, sy, sz = panel.size_mm
            corners = [(x, y, z), (x + sx, y, z), (x + sx, y + sy, z),
                       (x, y + sy, z), (x, y, z + sz), (x + sx, y, z + sz),
                       (x + sx, y + sy, z + sz), (x, y + sy, z + sz)]
            quads = ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4),
                     (2, 3, 7, 6), (1, 2, 6, 5), (0, 3, 7, 4))
            material = materials.get(panel.material_id)
            base = material.rgb() if material is not None else (0.9, 0.86, 0.76)
            for qi, quad in enumerate(quads):
                pts = [corners[i] for i in quad]
                depth = sum(p[0] + p[1] + p[2] for p in pts) / 4.0
                shade = 0.86 + 0.14 * (qi % 3)
                color = QColor(
                    max(0, min(255, int(base[0] * 255 * shade))),
                    max(0, min(255, int(base[1] * 255 * shade))),
                    max(0, min(255, int(base[2] * 255 * shade))),
                )
                faces.append((depth, [project(p) for p in pts], color))
        for _depth, points, color in sorted(faces, key=lambda f: f[0],
                                            reverse=True):
            painter.setBrush(color)
            painter.setPen(QPen(QColor(70, 65, 55, 120), 0.7))
            painter.drawPolygon(QPolygonF(points))
    finally:
        painter.end()
    return image


def save_module_png(path, result: BuildResult,
                    materials: dict[str, Material] | None = None,
                    width: int = 640, height: int = 480) -> None:
    from ..core.errors import ExportError
    image = render_module_image(result, materials, width, height)
    if not image.save(str(Path(path)), "PNG"):
        raise ExportError(f"Não foi possível gravar a imagem em {path}.")
