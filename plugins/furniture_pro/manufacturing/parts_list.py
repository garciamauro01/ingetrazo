# SPDX-License-Identifier: GPL-3.0-or-later
"""Parts list: the shop-floor view of the generated panels.

Panels are aggregated by material, thickness, cut size, grain and edge-band
pattern.  Identical pieces from different modules share one line, but the
line remembers every source module so the quote can still be split.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.models import BuildResult, Material, Panel

EDGE_SIDES = ("top", "bottom", "left", "right")


@dataclass
class PartItem:
    id: str
    code: str
    name: str
    role: str
    material_id: str
    thickness_mm: float
    length_mm: float
    width_mm: float
    grain: str = "length"
    edges: dict = field(default_factory=lambda: {s: "" for s in EDGE_SIDES})
    qty: int = 1
    module_ids: list[str] = field(default_factory=list)
    source_codes: list[str] = field(default_factory=list)
    note: str = ""

    @property
    def area_m2(self) -> float:
        return (self.length_mm * self.width_mm) / 1_000_000.0 * self.qty

    def edge_length_mm(self, side: str) -> float:
        return self.length_mm if side in ("top", "bottom") else self.width_mm

    def edge_total_mm(self) -> float:
        return sum(self.edge_length_mm(side) for side, band in self.edges.items()
                   if band) * self.qty

    def to_dict(self) -> dict:
        return {
            "id": self.id, "code": self.code, "name": self.name,
            "role": self.role, "material_id": self.material_id,
            "thickness_mm": self.thickness_mm,
            "length_mm": self.length_mm, "width_mm": self.width_mm,
            "grain": self.grain, "edges": dict(self.edges), "qty": self.qty,
            "module_ids": list(self.module_ids),
            "source_codes": list(self.source_codes), "note": self.note,
        }

    @classmethod
    def from_dict(cls, raw) -> "PartItem":
        raw = raw if isinstance(raw, dict) else {}
        from ..core.models import _num
        edges = {s: "" for s in EDGE_SIDES}
        if isinstance(raw.get("edges"), dict):
            edges.update({s: str(raw["edges"].get(s) or "")
                          for s in EDGE_SIDES})
        return cls(
            id=str(raw.get("id") or ""),
            code=str(raw.get("code") or ""),
            name=str(raw.get("name") or "Peça"),
            role=str(raw.get("role") or "outro"),
            material_id=str(raw.get("material_id") or ""),
            thickness_mm=_num(raw.get("thickness_mm")),
            length_mm=_num(raw.get("length_mm")),
            width_mm=_num(raw.get("width_mm")),
            grain=str(raw.get("grain") or "length"),
            edges=edges, qty=max(1, int(raw.get("qty") or 1)),
            module_ids=[str(v) for v in raw.get("module_ids") or []],
            source_codes=[str(v) for v in raw.get("source_codes") or []],
            note=str(raw.get("note") or ""),
        )


def _key(panel: Panel) -> tuple:
    return (
        panel.material_id,
        round(panel.thickness_mm, 2),
        round(panel.length_mm, 2),
        round(panel.width_mm, 2),
        panel.grain,
        tuple(panel.edges.get(side, "") for side in EDGE_SIDES),
    )


@dataclass
class PartsList:
    items: list[PartItem] = field(default_factory=list)
    panels: list[Panel] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def total_pieces(self) -> int:
        return sum(item.qty for item in self.items)

    @property
    def total_area_m2(self) -> float:
        return sum(item.area_m2 for item in self.items)

    def edge_length_by_band(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for item in self.items:
            for side, band in item.edges.items():
                if band:
                    out[band] = out.get(band, 0.0) + item.edge_length_mm(side) * item.qty
        return out

    def by_material(self) -> dict[str, list[PartItem]]:
        out: dict[str, list[PartItem]] = {}
        for item in self.items:
            out.setdefault(item.material_id, []).append(item)
        return out

    def to_dict(self) -> dict:
        return {
            "items": [item.to_dict() for item in self.items],
            "warnings": list(self.warnings),
            "totals": {
                "pieces": self.total_pieces,
                "area_m2": self.total_area_m2,
                "edge_by_band_m": self.edge_length_by_band(),
            },
        }


def collect_panels(results: list[BuildResult]) -> list[Panel]:
    panels: list[Panel] = []
    for result in results:
        panels.extend(result.panels)
    return panels


def build_parts_list(results: list[BuildResult],
                     materials: dict[str, Material] | None = None) -> PartsList:
    """Aggregate the panels of every module into shop-floor lines."""
    materials = materials or {}
    panels = collect_panels(results)
    grouped: dict[tuple, PartItem] = {}
    warnings: list[str] = []
    for panel in panels:
        key = _key(panel)
        item = grouped.get(key)
        if item is None:
            item = PartItem(
                id=f"part-{len(grouped) + 1:04d}",
                code="",
                name=panel.name,
                role=panel.role,
                material_id=panel.material_id,
                thickness_mm=panel.thickness_mm,
                length_mm=panel.length_mm,
                width_mm=panel.width_mm,
                grain=panel.grain,
                edges=dict(panel.edges),
                qty=0,
                module_ids=[],
                source_codes=[],
                note=panel.note,
            )
            grouped[key] = item
        item.qty += max(1, panel.qty)
        if panel.module_id and panel.module_id not in item.module_ids:
            item.module_ids.append(panel.module_id)
        if panel.code and panel.code not in item.source_codes:
            item.source_codes.append(panel.code)
        if panel.thickness_mm <= 0:
            warnings.append(f"{panel.name}: espessura inválida.")
        if panel.length_mm <= 0 or panel.width_mm <= 0:
            warnings.append(f"{panel.name}: dimensões inválidas.")

    items = sorted(grouped.values(),
                   key=lambda p: (p.material_id, -p.thickness_mm, p.name))
    for index, item in enumerate(items, start=1):
        item.code = f"{index:03d}"
        mat = materials.get(item.material_id)
        if mat is None:
            warnings.append(
                f"{item.name}: material não cadastrado ({item.material_id}).")
            continue
        board_l = max(mat.sheet_length_mm, mat.sheet_width_mm)
        board_w = min(mat.sheet_length_mm, mat.sheet_width_mm)
        if item.length_mm > board_l + 0.001 or item.width_mm > board_l + 0.001:
            warnings.append(
                f"{item.name} ({item.length_mm:.0f} × {item.width_mm:.0f} mm) "
                f"não cabe na chapa {mat.sheet_length_mm:.0f} × "
                f"{mat.sheet_width_mm:.0f} mm.")
        if item.thickness_mm > mat.thickness_mm + 0.01:
            warnings.append(
                f"{item.name}: espessura da peça ({item.thickness_mm:g} mm) "
                f"maior que a do material ({mat.thickness_mm:g} mm).")
    warnings = list(dict.fromkeys(warnings))
    return PartsList(items=items, panels=panels, warnings=warnings)
