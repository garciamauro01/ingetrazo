# SPDX-License-Identifier: GPL-3.0-or-later
"""Two-dimensional cutting optimiser.

The algorithm is MaxRects with Best Short Side Fit and a reserved saw kerf.
It is deterministic: parts are sorted by area, then by the longest side, so
the same project always produces the same plan.  Every generated placement is
checked for overlap and for staying inside the trimmed sheet; a plan that
fails this check raises instead of reaching the shop floor.

Scope and honesty: this is nesting for rectangular panels with grain and
rotation constraints.  It does not claim guillotine cuts, common-line
optimisation, remnant inventory or true machine-postprocessor output.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.errors import OptimizerError
from ..core.models import Material
from .parts_list import PartItem


@dataclass
class CutSettings:
    kerf_mm: float = 4.0
    trim_mm: float = 10.0
    allow_rotation: bool = True
    min_offcut_mm: float = 80.0
    fallback_board_length_mm: float = 2750.0
    fallback_board_width_mm: float = 1830.0
    fallback_thickness_mm: float = 18.0

    def validate(self) -> list[str]:
        problems = []
        if self.kerf_mm < 0:
            problems.append("A espessura do corte (kerf) não pode ser negativa.")
        if self.trim_mm < 0:
            problems.append("O refilo não pode ser negativo.")
        if self.fallback_board_length_mm <= 2 * self.trim_mm:
            problems.append("A chapa de reserva é menor que o refilo.")
        if self.fallback_board_width_mm <= 2 * self.trim_mm:
            problems.append("A largura da chapa de reserva é menor que o refilo.")
        return problems

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, raw) -> "CutSettings":
        raw = raw if isinstance(raw, dict) else {}
        out = cls()
        for key in out.__dict__:
            if key not in raw:
                continue
            value = raw[key]
            if isinstance(getattr(out, key), bool):
                setattr(out, key, bool(value))
            else:
                try:
                    setattr(out, key, float(value))
                except (TypeError, ValueError):
                    pass
        return out


@dataclass
class Placement:
    id: str
    part_id: str
    code: str
    name: str
    material_id: str
    module_ids: list[str]
    x_mm: float
    y_mm: float
    length_mm: float
    width_mm: float
    rotated: bool
    grain: str
    role: str = ""

    @property
    def area_m2(self) -> float:
        return self.length_mm * self.width_mm / 1_000_000.0

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class BoardPlan:
    index: int
    material_id: str
    material_name: str
    length_mm: float
    width_mm: float
    thickness_mm: float
    placements: list[Placement] = field(default_factory=list)
    cost: float = 0.0

    @property
    def used_area_m2(self) -> float:
        return sum(p.area_m2 for p in self.placements)

    @property
    def board_area_m2(self) -> float:
        return self.length_mm * self.width_mm / 1_000_000.0

    @property
    def utilization(self) -> float:
        return (self.used_area_m2 / self.board_area_m2
                if self.board_area_m2 else 0.0)

    def to_dict(self) -> dict:
        return {
            "index": self.index, "material_id": self.material_id,
            "material_name": self.material_name,
            "length_mm": self.length_mm, "width_mm": self.width_mm,
            "thickness_mm": self.thickness_mm,
            "placements": [p.to_dict() for p in self.placements],
            "used_area_m2": self.used_area_m2,
            "board_area_m2": self.board_area_m2,
            "utilization": self.utilization, "cost": self.cost,
        }


@dataclass
class CutPlan:
    boards: list[BoardPlan] = field(default_factory=list)
    unplaced: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    settings: dict = field(default_factory=dict)

    @property
    def board_count(self) -> int:
        return len(self.boards)

    @property
    def used_area_m2(self) -> float:
        return sum(b.used_area_m2 for b in self.boards)

    @property
    def board_area_m2(self) -> float:
        return sum(b.board_area_m2 for b in self.boards)

    @property
    def utilization(self) -> float:
        return (self.used_area_m2 / self.board_area_m2
                if self.board_area_m2 else 0.0)

    @property
    def total_cost(self) -> float:
        return sum(b.cost for b in self.boards)

    def to_dict(self) -> dict:
        return {
            "boards": [b.to_dict() for b in self.boards],
            "unplaced": list(self.unplaced),
            "warnings": list(self.warnings),
            "settings": dict(self.settings),
            "totals": {
                "boards": self.board_count,
                "used_area_m2": self.used_area_m2,
                "board_area_m2": self.board_area_m2,
                "utilization": self.utilization,
                "cost": self.total_cost,
            },
        }


@dataclass
class _Rect:
    x: float
    y: float
    w: float
    h: float

    @property
    def area(self) -> float:
        return self.w * self.h


def _fits(rect: _Rect, w: float, h: float, eps: float = 1e-6) -> bool:
    return rect.w + eps >= w and rect.h + eps >= h


def _find_best(free: list[_Rect], w: float, h: float):
    best = None
    for rect in free:
        if not _fits(rect, w, h):
            continue
        short = min(rect.w - w, rect.h - h)
        long = max(rect.w - w, rect.h - h)
        score = (short, long, rect.y, rect.x)
        if best is None or score < best[0]:
            best = (score, rect)
    return best[1] if best else None


def _split_free(free: list[_Rect], used: _Rect,
                min_offcut: float) -> list[_Rect]:
    out: list[_Rect] = []
    for rect in free:
        if (used.x >= rect.x + rect.w - 1e-6
                or used.x + used.w <= rect.x + 1e-6
                or used.y >= rect.y + rect.h - 1e-6
                or used.y + used.h <= rect.y + 1e-6):
            out.append(rect)
            continue
        if used.x > rect.x + 1e-6:
            out.append(_Rect(rect.x, rect.y, used.x - rect.x, rect.h))
        if used.x + used.w < rect.x + rect.w - 1e-6:
            out.append(_Rect(used.x + used.w, rect.y,
                             rect.x + rect.w - (used.x + used.w), rect.h))
        if used.y > rect.y + 1e-6:
            out.append(_Rect(rect.x, rect.y, rect.w, used.y - rect.y))
        if used.y + used.h < rect.y + rect.h - 1e-6:
            out.append(_Rect(rect.x, used.y + used.h, rect.w,
                             rect.y + rect.h - (used.y + used.h)))
    # Drop slivers and rectangles fully contained in another.
    out = [r for r in out if r.w > min_offcut / 4 and r.h > min_offcut / 4]
    pruned: list[_Rect] = []
    for i, rect in enumerate(out):
        contained = False
        for j, other in enumerate(out):
            if i == j:
                continue
            if (rect.x >= other.x - 1e-6 and rect.y >= other.y - 1e-6
                    and rect.x + rect.w <= other.x + other.w + 1e-6
                    and rect.y + rect.h <= other.y + other.h + 1e-6):
                if (rect.area < other.area
                        or (rect.area == other.area and j < i)):
                    contained = True
                    break
        if not contained:
            pruned.append(rect)
    return pruned


def _orientations(part: PartItem, material: Material | None,
                  settings: CutSettings) -> tuple[list[tuple[bool, float, float]],
                                                  str]:
    """(rotated, x_size, y_size) candidates and an optional grain warning."""
    w, h = part.length_mm, part.width_mm
    allow_rot = bool(settings.allow_rotation
                     and (material is None or material.allow_rotation))
    grain_axis = (material.grain_axis if material is not None else "length")
    if not allow_rot:
        warning = ""
        if part.grain in ("length", "width") and grain_axis != "none":
            required_rotation = (
                (part.grain == "length" and grain_axis == "width")
                or (part.grain == "width" and grain_axis == "length"))
            if required_rotation:
                warning = ("rotação desativada impede respeitar o veio desta "
                           "peça")
        return [(False, w, h)], warning
    if grain_axis == "none" or part.grain not in ("length", "width"):
        return [(False, w, h), (True, h, w)], ""
    if part.grain == "length":
        if grain_axis == "length":
            return [(False, w, h)], ""
        return [(True, h, w)], ""
    # part.grain == "width"
    if grain_axis == "length":
        return [(True, h, w)], ""
    return [(False, w, h)], ""


def _material_cost(material: Material | None) -> float:
    if material is None:
        return 0.0
    if material.cost_per_sheet > 0:
        return material.cost_per_sheet
    if material.cost_per_m2 > 0:
        return (material.sheet_length_mm * material.sheet_width_mm) / 1e6 \
            * material.cost_per_m2
    return 0.0


def optimize(parts: list[PartItem],
             materials: dict[str, Material] | None = None,
             settings: CutSettings | None = None) -> CutPlan:
    """Pack every part into the fewest rectangular sheets.

    Parts are grouped by material and thickness.  An unregistered material
    uses the conservative fallback sheet size and produces a warning.
    """
    materials = materials or {}
    settings = settings or CutSettings()
    problems = settings.validate()
    if problems:
        raise OptimizerError(problems)
    plan = CutPlan(settings=settings.to_dict())
    groups: dict[tuple[str, float], list[PartItem]] = {}
    for part in parts:
        if part.qty <= 0 or part.length_mm <= 0 or part.width_mm <= 0:
            plan.warnings.append(f"{part.name}: peça sem dimensões úteis.")
            continue
        groups.setdefault((part.material_id, round(part.thickness_mm, 2)),
                          []).append(part)

    global_index = 0
    for (material_id, thickness), group in sorted(groups.items()):
        material = materials.get(material_id)
        if material is None:
            plan.warnings.append(
                f"Material não cadastrado ({material_id}); usando chapa de "
                f"{settings.fallback_board_length_mm:.0f} × "
                f"{settings.fallback_board_width_mm:.0f} mm.")
            board_l = settings.fallback_board_length_mm
            board_w = settings.fallback_board_width_mm
            board_t = thickness or settings.fallback_thickness_mm
            material_name = material_id
        else:
            board_l = max(material.sheet_length_mm, material.sheet_width_mm)
            board_w = min(material.sheet_length_mm, material.sheet_width_mm)
            board_t = material.thickness_mm
            material_name = material.name
        usable_l = board_l - 2 * settings.trim_mm
        usable_w = board_w - 2 * settings.trim_mm
        if usable_l <= 0 or usable_w <= 0:
            plan.warnings.append(
                f"{material_name}: refilo maior que a chapa; grupo ignorado.")
            continue

        # Expand quantities into physical pieces.
        instances: list[PartItem] = []
        for part in group:
            instances.extend([part] * max(1, part.qty))
        instances.sort(key=lambda p: (-(p.length_mm * p.width_mm),
                                      -max(p.length_mm, p.width_mm),
                                      p.code))

        boards: list[tuple[BoardPlan, list[_Rect]]] = []

        def new_board() -> tuple[BoardPlan, list[_Rect]]:
            index = len(plan.boards) + 1
            board = BoardPlan(index=index, material_id=material_id,
                              material_name=material_name,
                              length_mm=board_l, width_mm=board_w,
                              thickness_mm=board_t,
                              cost=_material_cost(material))
            plan.boards.append(board)
            free = [_Rect(settings.trim_mm, settings.trim_mm,
                          usable_l, usable_w)]
            boards.append((board, free))
            return board, free

        for part in instances:
            options, grain_warning = _orientations(part, material, settings)
            if grain_warning:
                plan.warnings.append(f"{part.name}: {grain_warning}.")
            best = None          # (score, board, free, rect, rotated, w, h)
            for board, free in boards:
                for rotated, w, h in options:
                    if w > usable_l + 1e-6 or h > usable_w + 1e-6:
                        continue
                    rect = _find_best(free, w, h)
                    if rect is None:
                        continue
                    short = min(rect.w - w, rect.h - h)
                    long = max(rect.w - w, rect.h - h)
                    score = (short, long, board.index, rect.y, rect.x)
                    if best is None or score < best[0]:
                        best = (score, board, free, rect, rotated, w, h)
            if best is None:
                # Every existing sheet failed: open one and try there.
                board, free = new_board()
                for rotated, w, h in options:
                    if w > usable_l + 1e-6 or h > usable_w + 1e-6:
                        continue
                    rect = _find_best(free, w, h)
                    if rect is not None:
                        best = ((0, 0, board.index, rect.y, rect.x),
                                board, free, rect, rotated, w, h)
                        break
            if best is None:
                plan.unplaced.append({
                    "part_id": part.id, "code": part.code, "name": part.name,
                    "material_id": part.material_id,
                    "length_mm": part.length_mm,
                    "width_mm": part.width_mm,
                    "reason": "não cabe na chapa nas orientações permitidas",
                })
                plan.warnings.append(
                    f"{part.name} ({part.length_mm:.0f} × "
                    f"{part.width_mm:.0f} mm) não cabe na chapa de "
                    f"{material_name}.")
                # Remove a board that we opened but could not use.
                if boards and not boards[-1][0].placements and boards[-1][0] is board:
                    plan.boards.remove(board)
                    boards.pop()
                continue
            _, board, free, rect, rotated, w, h = best
            global_index += 1
            placement = Placement(
                id=f"P{global_index:05d}", part_id=part.id, code=part.code,
                name=part.name, material_id=part.material_id,
                module_ids=list(part.module_ids), x_mm=round(rect.x, 2),
                y_mm=round(rect.y, 2), length_mm=round(w, 2),
                width_mm=round(h, 2), rotated=rotated, grain=part.grain,
                role=part.role,
            )
            board.placements.append(placement)
            used = _Rect(rect.x, rect.y, w + settings.kerf_mm,
                         h + settings.kerf_mm)
            free[:] = _split_free(free, used, settings.min_offcut_mm)

    validate_plan(plan)
    if plan.unplaced:
        plan.warnings.append(
            f"{len(plan.unplaced)} peça(s) não puderam ser encaixadas.")
    return plan


def validate_plan(plan: CutPlan) -> None:
    """Refuse a plan with overlaps or pieces outside the sheet."""
    for board in plan.boards:
        half_l = board.length_mm / 2.0
        half_w = board.width_mm / 2.0
        for i, a in enumerate(board.placements):
            if (a.x_mm < -1e-6 or a.y_mm < -1e-6
                    or a.x_mm + a.length_mm > board.length_mm + 1e-6
                    or a.y_mm + a.width_mm > board.width_mm + 1e-6):
                raise OptimizerError(
                    f"Peça {a.code} fora da chapa {board.index}.")
            for b in board.placements[i + 1:]:
                overlap_x = (a.x_mm < b.x_mm + b.length_mm - 1e-6
                             and b.x_mm < a.x_mm + a.length_mm - 1e-6)
                overlap_y = (a.y_mm < b.y_mm + b.width_mm - 1e-6
                             and b.y_mm < a.y_mm + a.width_mm - 1e-6)
                if overlap_x and overlap_y:
                    raise OptimizerError(
                        f"Sobreposição detectada entre {a.code} e {b.code} "
                        f"na chapa {board.index}.")


def plan_from_dict(raw) -> CutPlan:
    raw = raw if isinstance(raw, dict) else {}
    plan = CutPlan(warnings=list(raw.get("warnings") or []),
                   settings=dict(raw.get("settings") or {}))
    for entry in raw.get("boards") or []:
        board = BoardPlan(
            index=int(entry.get("index") or 0),
            material_id=str(entry.get("material_id") or ""),
            material_name=str(entry.get("material_name") or ""),
            length_mm=float(entry.get("length_mm") or 0.0),
            width_mm=float(entry.get("width_mm") or 0.0),
            thickness_mm=float(entry.get("thickness_mm") or 0.0),
            cost=float(entry.get("cost") or 0.0),
        )
        for p in entry.get("placements") or []:
            board.placements.append(Placement(
                id=str(p.get("id") or ""), part_id=str(p.get("part_id") or ""),
                code=str(p.get("code") or ""), name=str(p.get("name") or ""),
                material_id=str(p.get("material_id") or ""),
                module_ids=[str(v) for v in p.get("module_ids") or []],
                x_mm=float(p.get("x_mm") or 0.0),
                y_mm=float(p.get("y_mm") or 0.0),
                length_mm=float(p.get("length_mm") or 0.0),
                width_mm=float(p.get("width_mm") or 0.0),
                rotated=bool(p.get("rotated")),
                grain=str(p.get("grain") or "length"),
                role=str(p.get("role") or ""),
            ))
        plan.boards.append(board)
    plan.unplaced = list(raw.get("unplaced") or [])
    return plan
