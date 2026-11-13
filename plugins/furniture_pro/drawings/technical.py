# SPDX-License-Identifier: GPL-3.0-or-later
"""Vector drawings (SVG) generated without external dependencies.

DXF is intentionally not produced: the project has no validated DXF writer,
and emitting a slightly wrong file to a CNC machine is worse than not
emitting one.  SVG covers the document/elevation use case and opens in every
browser and vector editor.
"""
from __future__ import annotations

from xml.sax.saxutils import escape

from ..core.models import BuildResult, ModuleSpec, Panel
from ..manufacturing.optimizer import CutPlan


def _header(width: float, height: float, title: str) -> list[str]:
    return [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}mm" '
        f'height="{height:.0f}mm" viewBox="0 0 {width:.0f} {height:.0f}">',
        f"<title>{escape(title)}</title>",
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<g font-family="Arial, Helvetica, sans-serif" font-size="18">',
    ]


def _footer() -> list[str]:
    return ["</g>", "</svg>"]


def _dimension_line(x1: float, y1: float, x2: float, y2: float,
                    label: str, offset: float = 0.0) -> list[str]:
    return [
        f'<line x1="{x1}" y1="{y1 + offset}" x2="{x2}" y2="{y2 + offset}" '
        'stroke="#2a3442" stroke-width="1"/>',
        f'<text x="{(x1 + x2) / 2}" y="{y1 + offset - 4}" '
        'text-anchor="middle" fill="#2a3442" font-size="16">'
        f"{escape(label)}</text>",
    ]


def module_front_svg(spec: ModuleSpec, result: BuildResult | None = None,
                     scale: float = 0.25) -> str:
    """Front elevation with the configured fronts and overall dimensions."""
    margin = 90.0
    width = spec.width_mm * scale + 2 * margin
    height = spec.height_mm * scale + 2 * margin
    out = _header(width, height, f"{spec.label} — elevação frontal")
    x0, y0 = margin, height - margin
    w = spec.width_mm * scale
    h = spec.height_mm * scale
    out.append(f'<rect x="{x0:.1f}" y="{y0 - h:.1f}" width="{w:.1f}" '
               f'height="{h:.1f}" fill="#f6f2e8" stroke="#33404f" '
               'stroke-width="2"/>')
    # Plinth
    if spec.plinth_height_mm > 0 and spec.type not in (
            "armario_superior", "nicho", "prateleira", "painel", "bancada",
            "porta_abrir", "porta_correr"):
        ph = spec.plinth_height_mm * scale
        out.append(f'<rect x="{x0:.1f}" y="{y0 - ph:.1f}" width="{w:.1f}" '
                   f'height="{ph:.1f}" fill="#d9d1c2" stroke="#8a8070"/>')
    # Drawers and doors schematically using the same gap rules as the model.
    front_bottom = spec.plinth_height_mm if not spec.door_covers_plinth else 0.0
    front_top = spec.height_mm
    zone_h = front_top - front_bottom
    if spec.drawer_count:
        heights = spec.drawer_heights_mm or [
            spec.drawer_front_height_mm] * spec.drawer_count
        total = sum(heights)
        if total > zone_h:
            factor = zone_h / total
            heights = [v * factor for v in heights]
        cursor = front_bottom if spec.drawer_position == "bottom" else (
            front_top - sum(heights))
        for i, dh in enumerate(heights, start=1):
            dy = y0 - (cursor + dh) * scale
            dh_px = dh * scale
            if spec.drawer_position == "bottom":
                dy = y0 - (front_bottom + sum(heights[:i])) * scale
            out.append(
                f'<rect x="{x0:.1f}" y="{dy:.1f}" width="{w:.1f}" '
                f'height="{dh_px:.1f}" fill="#e3d6bd" stroke="#806d4d"/>')
            out.append(
                f'<text x="{x0 + w / 2:.1f}" y="{dy + dh_px / 2 + 6:.1f}" '
                'text-anchor="middle" fill="#594b32" font-size="15">'
                f"Gaveta {i}</text>")
    if spec.door_type == "hinged" and spec.door_count:
        door_top = front_top
        door_bottom = front_bottom
        if spec.drawer_count and spec.drawer_position == "bottom":
            door_bottom += sum(spec.drawer_heights_mm or [
                spec.drawer_front_height_mm] * spec.drawer_count)
        elif spec.drawer_count and spec.drawer_position == "top":
            door_top -= sum(spec.drawer_heights_mm or [
                spec.drawer_front_height_mm] * spec.drawer_count)
        door_h = max(0.0, door_top - door_bottom)
        gap = spec.door_gap_mm * scale
        side = spec.door_edge_gap_mm * scale
        usable = w - 2 * side - gap * (spec.door_count - 1)
        dw = usable / spec.door_count
        for i in range(spec.door_count):
            dx = x0 + side + i * (dw + gap)
            out.append(
                f'<rect x="{dx:.1f}" y="{y0 - (door_bottom + door_h) * scale:.1f}" '
                f'width="{dw:.1f}" height="{door_h * scale:.1f}" '
                'fill="#f1eadb" stroke="#806d4d"/>')
    elif spec.door_type == "sliding" and spec.door_count:
        track = spec.sliding_track_height_mm * scale
        out.append(f'<rect x="{x0:.1f}" y="{y0 - h:.1f}" width="{w:.1f}" '
                   f'height="{track:.1f}" fill="#cfc7b8" stroke="#8a8070"/>')
        out.append(f'<rect x="{x0:.1f}" y="{y0 - track:.1f}" width="{w:.1f}" '
                   f'height="{track:.1f}" fill="#cfc7b8" stroke="#8a8070"/>')
    out.extend(_dimension_line(x0, y0 - h, x0 + w, y0 - h,
                               f"{spec.width_mm:.0f} mm", -24))
    out.extend([
        f'<line x1="{x0 - 28:.1f}" y1="{y0:.1f}" x2="{x0 - 28:.1f}" '
        f'y2="{y0 - h:.1f}" stroke="#2a3442" stroke-width="1"/>',
        f'<text x="{x0 - 34:.1f}" y="{y0 - h / 2:.1f}" text-anchor="end" '
        f'fill="#2a3442" font-size="16">{spec.height_mm:.0f} mm</text>',
        f'<text x="{x0:.1f}" y="{y0 + 36:.1f}" fill="#6b7280" font-size="15">'
        f"{escape(spec.label)} — profundidade {spec.depth_mm:.0f} mm</text>",
    ])
    out.extend(_footer())
    return "\n".join(out)


def cut_plan_svg(plan: CutPlan, *, max_width_mm: float = 900.0) -> str:
    """One page per material, each board drawn to scale with part codes."""
    if not plan.boards:
        return "\n".join(_header(200, 80, "Plano de corte vazio") +
                         ['<text x="20" y="40">Sem chapas.</text>'] +
                         _footer())
    board_w = max(b.length_mm for b in plan.boards)
    board_h = max(b.width_mm for b in plan.boards)
    columns = 2
    scale = min(1.0, (max_width_mm / columns - 50) / max(1.0, board_w))
    cell_w = board_w * scale + 50
    cell_h = board_h * scale + 70
    rows = (len(plan.boards) + columns - 1) // columns
    total_w = cell_w * columns + 40
    total_h = cell_h * rows + 90
    out = _header(total_w, total_h, "Plano de corte")
    out.append(f'<text x="20" y="30" font-size="20" fill="#1f2937">'
               f"Plano de corte — {len(plan.boards)} chapa(s), "
               f"aproveitamento {plan.utilization * 100:.1f}%</text>")
    for index, board in enumerate(plan.boards):
        col = index % columns
        row = index // columns
        left = 20 + col * cell_w
        top = 50 + row * cell_h
        bw = board.length_mm * scale
        bh = board.width_mm * scale
        out.append(f'<text x="{left:.1f}" y="{top:.1f}" font-size="16" '
                   f'fill="#334155">Chapa {board.index} — '
                   f"{escape(board.material_name)} — "
                   f"{board.length_mm:.0f} × {board.width_mm:.0f} mm</text>")
        out.append(f'<rect x="{left:.1f}" y="{top + 10:.1f}" '
                   f'width="{bw:.1f}" height="{bh:.1f}" fill="#faf8f2" '
                   'stroke="#33404f" stroke-width="2"/>')
        for p in board.placements:
            px = left + p.x_mm * scale
            py = top + 10 + p.y_mm * scale
            pw = p.length_mm * scale
            ph = p.width_mm * scale
            out.append(f'<rect x="{px:.1f}" y="{py:.1f}" '
                       f'width="{pw:.1f}" height="{ph:.1f}" '
                       'fill="#d8c8ab" stroke="#8a7554" stroke-width="1"/>')
            if pw > 24 and ph > 12:
                out.append(f'<text x="{px + pw / 2:.1f}" '
                           f'y="{py + ph / 2 + 5:.1f}" text-anchor="middle" '
                           f'font-size="12" fill="#3f3424">'
                           f"{escape(p.code)}</text>")
    out.extend(_footer())
    return "\n".join(out)


def write_svg(path, content: str) -> None:
    from pathlib import Path
    from ..core.errors import ExportError
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise ExportError(f"Não foi possível gravar {path}: {exc}") from exc
