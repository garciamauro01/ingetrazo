# SPDX-License-Identifier: GPL-3.0-or-later
"""Gestão de estoque de retalhos aproveitáveis para o plano de corte."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class Remnant:
    """Retalho de chapa armazenado em estoque."""

    id: int
    material: str
    thickness_mm: float
    width_mm: float
    height_mm: float
    grain: bool = False
    notes: str = ""

    @property
    def area_m2(self) -> float:
        return (self.width_mm * self.height_mm) / 1_000_000.0

    def fits_part(self, part_w: float, part_h: float, allow_rotate: bool = True) -> bool:
        if part_w <= self.width_mm and part_h <= self.height_mm:
            return True
        if allow_rotate and not self.grain:
            return part_h <= self.width_mm and part_w <= self.height_mm
        return False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Remnant:
        return cls(
            id=int(data["id"]),
            material=str(data["material"]),
            thickness_mm=float(data.get("thickness_mm", 15.0)),
            width_mm=float(data["width_mm"]),
            height_mm=float(data["height_mm"]),
            grain=bool(data.get("grain", False)),
            notes=str(data.get("notes", "")),
        )


class RemnantStock:
    """Estoque persistente de retalhos em JSON."""

    def __init__(self) -> None:
        self.items: dict[int, Remnant] = {}
        self._next_id: int = 1

    def add_remnant(
        self,
        material: str,
        thickness_mm: float,
        width_mm: float,
        height_mm: float,
        grain: bool = False,
        notes: str = "",
    ) -> Remnant:
        rid = self._next_id
        self._next_id += 1
        rem = Remnant(
            id=rid,
            material=material,
            thickness_mm=float(thickness_mm),
            width_mm=float(width_mm),
            height_mm=float(height_mm),
            grain=bool(grain),
            notes=notes,
        )
        self.items[rid] = rem
        return rem

    def remove_remnant(self, remnant_id: int) -> bool:
        return self.items.pop(remnant_id, None) is not None

    def find_best_match(
        self,
        material: str,
        thickness_mm: float,
        part_w: float,
        part_h: float,
        allow_rotate: bool = True,
    ) -> Remnant | None:
        """Retorna o menor retalho compatível (menor desperdício) para a peça."""
        candidates = [
            r for r in self.items.values()
            if r.material == material
            and abs(r.thickness_mm - thickness_mm) <= 0.1
            and r.fits_part(part_w, part_h, allow_rotate=allow_rotate)
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda r: r.area_m2)

    def save(self, path: Path) -> None:
        payload = [r.to_dict() for r in self.items.values()]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> RemnantStock:
        stock = cls()
        if not path.exists():
            return stock
        raw = json.loads(path.read_text(encoding="utf-8"))
        for entry in raw:
            rem = Remnant.from_dict(entry)
            stock.items[rem.id] = rem
        if stock.items:
            stock._next_id = max(stock.items.keys()) + 1
        return stock
