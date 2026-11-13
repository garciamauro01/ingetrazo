# SPDX-License-Identifier: GPL-3.0-or-later
"""CSV, JSON and PDF reports.

PDF uses Qt's own ``QPdfWriter`` (already a host dependency), so no new
package is required.  CSV uses the standard library and is written with a
UTF-8 BOM so Excel opens Portuguese accents correctly.
"""
from __future__ import annotations

import csv
import io
import json
import os
import tempfile
from pathlib import Path

from ..core.errors import ExportError
from ..core.logging_utils import get_logger
from .optimizer import CutPlan
from .parts_list import PartsList

PART_COLUMNS = ("Código", "Peça", "Módulo(s)", "Material", "Espessura (mm)",
                "Comprimento (mm)", "Largura (mm)", "Qtd", "Veio",
                "Fita superior", "Fita inferior", "Fita esquerda",
                "Fita direita", "Área (m²)")
CUT_COLUMNS = ("Chapa", "Material", "Comprimento (mm)", "Largura (mm)",
               "Peça", "Código", "X (mm)", "Y (mm)", "Comprimento peça (mm)",
               "Largura peça (mm)", "Rotacionada", "Módulo(s)")


def _atomic_text(path, text: str, *, bom: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
        with os.fdopen(fd, "w", encoding="utf-8-sig" if bom else "utf-8",
                       newline="") as handle:
            handle.write(text)
        os.replace(temp_name, path)
    except OSError as exc:
        raise ExportError(f"Não foi possível gravar {path}: {exc}",
                          details=str(exc)) from exc


def _csv_text(columns, rows) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(columns)
    writer.writerows(rows)
    return buffer.getvalue()


def parts_csv_text(parts: PartsList,
                   materials: dict | None = None) -> str:
    materials = materials or {}
    rows = []
    for item in parts.items:
        mat = materials.get(item.material_id)
        rows.append((
            item.code, item.name, ", ".join(item.source_codes), 
            mat.name if mat else item.material_id,
            f"{item.thickness_mm:g}", f"{item.length_mm:g}",
            f"{item.width_mm:g}", item.qty, item.grain,
            item.edges.get("top", ""), item.edges.get("bottom", ""),
            item.edges.get("left", ""), item.edges.get("right", ""),
            f"{item.area_m2:.4f}",
        ))
    return _csv_text(PART_COLUMNS, rows)


def cut_plan_csv_text(plan: CutPlan) -> str:
    rows = []
    for board in plan.boards:
        for p in board.placements:
            rows.append((
                board.index, board.material_name, f"{board.length_mm:g}",
                f"{board.width_mm:g}", p.name, p.code, f"{p.x_mm:g}",
                f"{p.y_mm:g}", f"{p.length_mm:g}", f"{p.width_mm:g}",
                "sim" if p.rotated else "não", ", ".join(p.module_ids),
            ))
    return _csv_text(CUT_COLUMNS, rows)


def write_parts_csv(path, parts: PartsList, materials: dict | None = None) -> None:
    _atomic_text(path, parts_csv_text(parts, materials), bom=True)


def write_cut_plan_csv(path, plan: CutPlan) -> None:
    _atomic_text(path, cut_plan_csv_text(plan), bom=True)


def write_json(path, payload) -> None:
    try:
        text = json.dumps(payload, ensure_ascii=False, indent=2,
                          default=str) + "\n"
    except (TypeError, ValueError) as exc:
        raise ExportError(f"Dados não serializáveis: {exc}") from exc
    _atomic_text(path, text)


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def pdf_available() -> bool:
    try:
        from PySide6.QtGui import QPdfWriter  # noqa: F401
        return True
    except Exception:                                   # noqa: BLE001
        return False


def _money(value: float, currency: str) -> str:
    from ..pricing.calculator import format_money
    return format_money(value, currency)


def write_pdf_report(path, *, title: str, parts: PartsList,
                     plan: CutPlan | None = None, quote=None,
                     materials: dict | None = None,
                     hardware: dict | None = None,
                     drawing_svgs: dict | None = None) -> None:
    """Write a paginated project report with parts, cut plan and quote."""
    try:
        from PySide6.QtCore import QMarginsF, QRectF, Qt
        from PySide6.QtGui import (QColor, QFont, QPageLayout, QPageSize,
                                   QPainter, QPdfWriter, QPen, QTextDocument)
    except Exception as exc:                           # noqa: BLE001
        raise ExportError("PySide6 não está disponível para gerar PDF.",
                          details=str(exc)) from exc

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = QPdfWriter(str(path))
    writer.setPageSize(QPageSize(QPageSize.A4))
    writer.setPageMargins(QMarginsF(14, 14, 14, 14),
                          QPageLayout.Millimeter)
    writer.setResolution(96)
    writer.setTitle(title)
    painter = QPainter(writer)
    if not painter.isActive():
        raise ExportError("Não foi possível iniciar a impressão do PDF.")
    metrics = writer.pageLayout().paintRectPixels(writer.resolution())
    page_w = metrics.width()
    page_h = metrics.height()
    margin = int(writer.resolution() * 0.35)
    left, top = margin, margin
    width = page_w - 2 * margin
    bottom = page_h - margin
    state = {"y": top, "page": 0}

    def new_page(heading: str = "") -> None:
        if state["y"] > top or state["page"] == 0:
            if state["page"] > 0:
                writer.newPage()
            state["page"] += 1
            state["y"] = top
        if heading:
            painter.setFont(QFont("Arial", 12, QFont.Bold))
            painter.setPen(QPen(QColor(30, 40, 55)))
            painter.drawText(QRectF(left, state["y"], width, 22),
                             Qt.AlignLeft | Qt.AlignVCenter, heading)
            state["y"] += 26
        painter.setFont(QFont("Arial", 8))
        painter.setPen(QPen(QColor(80, 80, 80)))

    def ensure(height: float) -> None:
        if state["y"] + height > bottom:
            new_page()

    def text_line(text: str, size: int = 8, bold: bool = False,
                  color=(30, 30, 30), gap: float = 12) -> None:
        ensure(gap + 2)
        painter.setFont(QFont("Arial", size, QFont.Bold if bold else QFont.Normal))
        painter.setPen(QPen(QColor(*color)))
        painter.drawText(QRectF(left, state["y"], width, gap),
                         Qt.AlignLeft | Qt.AlignVCenter, str(text))
        state["y"] += gap

    def table(headers, rows, widths: list[float] | None = None,
              row_h: float = 12) -> None:
        ensure(row_h * 2)
        if widths is None:
            widths = [width / len(headers)] * len(headers)
        painter.setFont(QFont("Arial", 7, QFont.Bold))
        painter.setPen(QPen(QColor(30, 40, 55)))
        x = left
        for header, w in zip(headers, widths):
            painter.drawText(QRectF(x, state["y"], w, row_h),
                             Qt.AlignLeft | Qt.AlignVCenter, str(header))
            x += w
        state["y"] += row_h
        painter.setPen(QPen(QColor(180, 180, 180)))
        painter.drawLine(int(left), int(state["y"]),
                         int(left + width), int(state["y"]))
        state["y"] += 2
        painter.setFont(QFont("Arial", 7))
        for row in rows:
            ensure(row_h)
            painter.setPen(QPen(QColor(45, 45, 45)))
            x = left
            for value, w in zip(row, widths):
                painter.drawText(QRectF(x, state["y"], w, row_h),
                                 Qt.AlignLeft | Qt.AlignVCenter,
                                 str(value)[:60])
                x += w
            state["y"] += row_h

    def draw_boards(plan_data: CutPlan) -> None:
        for board in plan_data.boards:
            ensure(220)
            scale = min((width - 20) / max(1.0, board.length_mm),
                        (bottom - state["y"] - 45) / max(1.0, board.width_mm))
            scale = max(0.002, min(scale, 0.30))
            bw = board.length_mm * scale
            bh = board.width_mm * scale
            origin_y = state["y"] + 14
            painter.setFont(QFont("Arial", 7, QFont.Bold))
            painter.setPen(QPen(QColor(30, 40, 55)))
            painter.drawText(
                QRectF(left, state["y"], width, 12),
                Qt.AlignLeft | Qt.AlignVCenter,
                f"Chapa {board.index} — {board.material_name} — "
                f"{board.length_mm:.0f} × {board.width_mm:.0f} mm — "
                f"aproveitamento {board.utilization * 100:.1f}%")
            state["y"] = origin_y
            painter.setPen(QPen(QColor(80, 80, 80), 1))
            painter.setBrush(QColor(248, 246, 240))
            painter.drawRect(QRectF(left, state["y"], bw, bh))
            painter.setFont(QFont("Arial", 5))
            for p in board.placements:
                rect = QRectF(left + p.x_mm * scale,
                              state["y"] + p.y_mm * scale,
                              p.length_mm * scale, p.width_mm * scale)
                painter.setBrush(QColor(214, 202, 178))
                painter.setPen(QPen(QColor(120, 105, 80), 0.5))
                painter.drawRect(rect)
                if rect.width() > 26 and rect.height() > 12:
                    painter.setPen(QPen(QColor(40, 40, 40)))
                    painter.drawText(rect.adjusted(2, 1, -1, -1),
                                     Qt.AlignCenter, p.code)
            state["y"] += bh + 8

    try:
        # Page 1 — summary
        new_page(title)
        text_line("Relatório de fabricação e orçamento", 16, True,
                  (20, 30, 45), 22)
        text_line(f"Peças: {parts.total_pieces}   "
                  f"Área das peças: {parts.total_area_m2:.3f} m²",
                  9, False, (60, 60, 60), 14)
        if plan is not None:
            text_line(f"Chapas: {plan.board_count}   "
                      f"Aproveitamento: {plan.utilization * 100:.1f}%",
                      9, False, (60, 60, 60), 14)
        if quote is not None:
            text_line(f"Total do orçamento: "
                      f"{_money(quote.total, quote.currency)}",
                      11, True, (20, 30, 45), 18)
        state["y"] += 8

        new_page("Lista de peças")
        rows = []
        for item in parts.items:
            mat = (materials or {}).get(item.material_id)
            rows.append((item.code, item.name[:34],
                         mat.name[:22] if mat else item.material_id,
                         f"{item.thickness_mm:g}", f"{item.length_mm:g}",
                         f"{item.width_mm:g}", item.qty,
                         f"{item.area_m2:.3f}"))
        table(("Cód.", "Peça", "Material", "Esp.", "Comp.", "Larg.",
               "Qtd", "m²"), rows,
              [30, 150, 130, 30, 45, 45, 28, 40])
        if parts.warnings:
            state["y"] += 6
            text_line("Avisos da lista de peças:", 8, True, (120, 60, 20))
            for warning in parts.warnings[:20]:
                text_line(f"• {warning}", 7, False, (90, 60, 20), 10)

        if plan is not None:
            new_page("Plano de corte")
            draw_boards(plan)
            if plan.warnings:
                state["y"] += 4
                text_line("Avisos do plano de corte:", 8, True, (120, 60, 20))
                for warning in plan.warnings[:20]:
                    text_line(f"• {warning}", 7, False, (90, 60, 20), 10)

        if quote is not None:
            new_page("Orçamento")
            text_line(f"Moeda: {quote.currency}   "
                      f"Modo de preço: "
                      f"{'margem sobre venda' if quote.pricing_mode == 'margin' else 'markup sobre custo'}",
                      8, False, (60, 60, 60), 12)
            rows = [(label, _money(value, quote.currency))
                    for label, value in quote.lines()]
            table(("Item", "Valor"), rows, [width * 0.65, width * 0.35])
            state["y"] += 6
            text_line(f"Margem efetiva sobre venda: "
                      f"{quote.margin_on_sale * 100:.1f}%    "
                      f"Markup efetivo sobre custo: "
                      f"{quote.markup_on_cost * 100:.1f}%", 8)
            if quote.warnings:
                state["y"] += 4
                text_line("Avisos do orçamento:", 8, True, (120, 60, 20))
                for warning in quote.warnings[:25]:
                    text_line(f"• {warning}", 7, False, (90, 60, 20), 10)

        if drawing_svgs:
            new_page("Desenhos técnicos")
            for name in drawing_svgs:
                text_line(name, 9, True, (30, 40, 55), 14)
                text_line("Os desenhos vetoriais são exportados em SVG "
                          "separadamente.", 7, False, (90, 90, 90), 12)
    except ExportError:
        raise
    except Exception as exc:                           # noqa: BLE001
        get_logger().exception("PDF report failed")
        raise ExportError(f"Falha ao gerar o PDF: {exc}",
                          details=str(exc)) from exc
    finally:
        painter.end()
