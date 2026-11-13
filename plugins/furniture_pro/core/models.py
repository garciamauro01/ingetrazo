# SPDX-License-Identifier: GPL-3.0-or-later
"""Serializable domain models shared by the whole plugin.

Everything here is plain Python and JSON-safe.  Distances are millimetres;
the geometry adapter converts to metres only when creating Ingetrazo meshes.
"""
from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .constants import (
    BACK_METHODS,
    CARCASS_METHODS,
    DEFAULT_EDGE_BAND_ID,
    DEFAULT_MATERIAL_ID,
    DOOR_TYPES,
    GRAIN_CHOICES,
    MODULE_LABELS,
    MODULE_TYPES,
    TOP_METHODS,
)

EDGE_SIDES = ("top", "bottom", "left", "right")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_id(prefix: str = "mod") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _num(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float(default)
    return out if math.isfinite(out) else float(default)


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return int(default)


def _bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "sim", "on")
    if value is None:
        return default
    return bool(value)


def _tuple3(value: Any, default=(0.0, 0.0, 0.0)) -> tuple[float, float, float]:
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return (_num(value[0]), _num(value[1]), _num(value[2]))
    return (float(default[0]), float(default[1]), float(default[2]))


def hex_to_rgb(value: str, fallback=(0.90, 0.89, 0.85)) -> tuple[float, float, float]:
    """Convert ``#RRGGBB`` (or ``#RGB``) to floats 0–1, safely."""
    text = str(value or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{3}", text):
        text = "#" + "".join(ch * 2 for ch in text[1:])
    if re.fullmatch(r"#[0-9a-fA-F]{6}", text):
        return tuple(int(text[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    return tuple(fallback)


def rgb_to_hex(rgb) -> str:
    if rgb is None or len(rgb) < 3:
        return "#E6E4DD"
    return "#" + "".join(f"{max(0, min(255, round(float(c) * 255))):02X}"
                         for c in rgb[:3])


def _edges(raw: Any) -> dict[str, str]:
    out = {side: "" for side in EDGE_SIDES}
    if isinstance(raw, dict):
        for side in EDGE_SIDES:
            value = raw.get(side)
            if value:
                out[side] = str(value)
    return out


# ---------------------------------------------------------------------------
# Catalogue entities
# ---------------------------------------------------------------------------

@dataclass
class Material:
    id: str
    name: str
    category: str = "MDF"
    manufacturer: str = ""
    reference: str = ""
    color: str = "#E6E4DD"
    texture_path: str = ""
    thickness_mm: float = 18.0
    sheet_length_mm: float = 2750.0
    sheet_width_mm: float = 1830.0
    cost_per_sheet: float = 0.0
    cost_per_m2: float = 0.0
    grain_axis: str = "length"
    allow_rotation: bool = True
    finish: str = "Liso"
    supplier: str = ""
    availability: bool = True
    edge_band_id: str = ""
    notes: str = ""

    @classmethod
    def from_dict(cls, raw: Any) -> "Material":
        raw = raw if isinstance(raw, dict) else {}
        return cls(
            id=str(raw.get("id") or new_id("mat")),
            name=str(raw.get("name") or "Material"),
            category=str(raw.get("category") or "MDF"),
            manufacturer=str(raw.get("manufacturer") or ""),
            reference=str(raw.get("reference") or ""),
            color=str(raw.get("color") or "#E6E4DD"),
            texture_path=str(raw.get("texture_path") or ""),
            thickness_mm=_num(raw.get("thickness_mm"), 18.0),
            sheet_length_mm=_num(raw.get("sheet_length_mm"), 2750.0),
            sheet_width_mm=_num(raw.get("sheet_width_mm"), 1830.0),
            cost_per_sheet=_num(raw.get("cost_per_sheet")),
            cost_per_m2=_num(raw.get("cost_per_m2")),
            grain_axis=str(raw.get("grain_axis") or "length"),
            allow_rotation=_bool(raw.get("allow_rotation"), True),
            finish=str(raw.get("finish") or "Liso"),
            supplier=str(raw.get("supplier") or ""),
            availability=_bool(raw.get("availability"), True),
            edge_band_id=str(raw.get("edge_band_id") or ""),
            notes=str(raw.get("notes") or ""),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "category": self.category,
            "manufacturer": self.manufacturer, "reference": self.reference,
            "color": self.color, "texture_path": self.texture_path,
            "thickness_mm": self.thickness_mm,
            "sheet_length_mm": self.sheet_length_mm,
            "sheet_width_mm": self.sheet_width_mm,
            "cost_per_sheet": self.cost_per_sheet,
            "cost_per_m2": self.cost_per_m2,
            "grain_axis": self.grain_axis,
            "allow_rotation": self.allow_rotation, "finish": self.finish,
            "supplier": self.supplier, "availability": self.availability,
            "edge_band_id": self.edge_band_id, "notes": self.notes,
        }

    def rgb(self) -> tuple[float, float, float]:
        return hex_to_rgb(self.color)

    def validate(self) -> list[str]:
        problems: list[str] = []
        if not self.name.strip():
            problems.append("O material precisa de um nome.")
        if self.thickness_mm <= 0:
            problems.append("A espessura do material deve ser positiva.")
        if self.sheet_length_mm <= 0 or self.sheet_width_mm <= 0:
            problems.append("As dimensões comerciais da chapa devem ser positivas.")
        if self.cost_per_sheet < 0 or self.cost_per_m2 < 0:
            problems.append("O custo do material não pode ser negativo.")
        if self.grain_axis not in ("length", "width", "none"):
            problems.append("Direção do veio inválida.")
        return problems


@dataclass
class EdgeBand:
    id: str
    name: str
    color: str = "#E6E4DD"
    thickness_mm: float = 0.45
    material: str = "PVC"
    cost_per_m: float = 0.0
    supplier: str = ""
    availability: bool = True
    notes: str = ""

    @classmethod
    def from_dict(cls, raw: Any) -> "EdgeBand":
        raw = raw if isinstance(raw, dict) else {}
        return cls(
            id=str(raw.get("id") or new_id("eb")),
            name=str(raw.get("name") or "Fita de borda"),
            color=str(raw.get("color") or "#E6E4DD"),
            thickness_mm=_num(raw.get("thickness_mm"), 0.45),
            material=str(raw.get("material") or "PVC"),
            cost_per_m=_num(raw.get("cost_per_m")),
            supplier=str(raw.get("supplier") or ""),
            availability=_bool(raw.get("availability"), True),
            notes=str(raw.get("notes") or ""),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "color": self.color,
            "thickness_mm": self.thickness_mm, "material": self.material,
            "cost_per_m": self.cost_per_m, "supplier": self.supplier,
            "availability": self.availability, "notes": self.notes,
        }

    def validate(self) -> list[str]:
        problems = []
        if not self.name.strip():
            problems.append("A fita de borda precisa de um nome.")
        if self.thickness_mm <= 0:
            problems.append("A espessura da fita deve ser positiva.")
        if self.cost_per_m < 0:
            problems.append("O custo da fita não pode ser negativo.")
        return problems


@dataclass
class HardwareItem:
    id: str
    name: str
    category: str = "outro"
    manufacturer: str = ""
    reference: str = ""
    unit: str = "un"
    cost: float = 0.0
    install: dict = field(default_factory=dict)
    spec_source: str = "manual"
    verified: bool = False
    supplier: str = ""
    notes: str = ""

    @classmethod
    def from_dict(cls, raw: Any) -> "HardwareItem":
        raw = raw if isinstance(raw, dict) else {}
        install = raw.get("install")
        return cls(
            id=str(raw.get("id") or new_id("hw")),
            name=str(raw.get("name") or "Ferragem"),
            category=str(raw.get("category") or "outro"),
            manufacturer=str(raw.get("manufacturer") or ""),
            reference=str(raw.get("reference") or ""),
            unit=str(raw.get("unit") or "un"),
            cost=_num(raw.get("cost")),
            install=dict(install) if isinstance(install, dict) else {},
            spec_source=str(raw.get("spec_source") or "manual"),
            verified=_bool(raw.get("verified"), False),
            supplier=str(raw.get("supplier") or ""),
            notes=str(raw.get("notes") or ""),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "category": self.category,
            "manufacturer": self.manufacturer, "reference": self.reference,
            "unit": self.unit, "cost": self.cost, "install": dict(self.install),
            "spec_source": self.spec_source, "verified": self.verified,
            "supplier": self.supplier, "notes": self.notes,
        }

    def validate(self) -> list[str]:
        problems = []
        if not self.name.strip():
            problems.append("A ferragem precisa de um nome.")
        if self.cost < 0:
            problems.append("O custo da ferragem não pode ser negativo.")
        if self.install and not self.verified:
            # Allowed, but the report flags it; here only structural issues.
            pass
        return problems


# ---------------------------------------------------------------------------
# Parametric module
# ---------------------------------------------------------------------------

@dataclass
class ModuleSpec:
    id: str = field(default_factory=lambda: new_id("mod"))
    code: str = ""
    type: str = "armario_inferior"
    name: str = ""
    room: str = ""
    width_mm: float = 800.0
    height_mm: float = 850.0
    depth_mm: float = 550.0
    panel_thickness_mm: float = 18.0
    front_thickness_mm: float = 18.0
    back_thickness_mm: float = 6.0
    material_id: str = DEFAULT_MATERIAL_ID
    front_material_id: str = ""
    back_material_id: str = ""
    edge_band_id: str = DEFAULT_EDGE_BAND_ID
    front_edge_band_id: str = ""
    back_edge_band_id: str = ""
    carcass_method: str = "laterais_passantes"
    top_method: str = "tampo"
    back_method: str = "rasgo"
    back_recess_mm: float = 15.0
    plinth_height_mm: float = 100.0
    plinth_recess_mm: float = 60.0
    shelf_count: int = 1
    divider_count: int = 0
    door_type: str = "hinged"
    door_count: int = 2
    door_gap_mm: float = 3.0
    door_edge_gap_mm: float = 2.0
    door_vertical_gap_mm: float = 2.0
    door_overlap_mm: float = 20.0
    door_covers_plinth: bool = False
    sliding_track_height_mm: float = 40.0
    drawer_count: int = 0
    drawer_heights_mm: list[float] = field(default_factory=list)
    drawer_front_height_mm: float = 180.0
    drawer_position: str = "bottom"
    drawer_box: bool = True
    drawer_box_thickness_mm: float = 15.0
    drawer_slide_clearance_mm: float = 26.0
    drawer_box_depth_clearance_mm: float = 50.0
    drawer_box_height_clearance_mm: float = 30.0
    hinge_count_per_door: int = 0
    hinge_offset_mm: float = 100.0
    hardware: dict = field(default_factory=dict)
    origin_mm: tuple = (0.0, 0.0, 0.0)
    rotation_z_deg: float = 0.0
    notes: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    extra: dict = field(default_factory=dict)

    @property
    def label(self) -> str:
        return self.name or MODULE_LABELS.get(self.type, self.type)

    def material_for_front(self) -> str:
        return self.front_material_id or self.material_id

    def material_for_back(self) -> str:
        return self.back_material_id or self.material_id

    def edge_for_front(self) -> str:
        return self.front_edge_band_id or self.edge_band_id

    def edge_for_back(self) -> str:
        return self.back_edge_band_id or self.edge_band_id

    def to_dict(self) -> dict:
        return {
            "id": self.id, "code": self.code, "type": self.type,
            "name": self.name, "room": self.room,
            "width_mm": self.width_mm, "height_mm": self.height_mm,
            "depth_mm": self.depth_mm,
            "panel_thickness_mm": self.panel_thickness_mm,
            "front_thickness_mm": self.front_thickness_mm,
            "back_thickness_mm": self.back_thickness_mm,
            "material_id": self.material_id,
            "front_material_id": self.front_material_id,
            "back_material_id": self.back_material_id,
            "edge_band_id": self.edge_band_id,
            "front_edge_band_id": self.front_edge_band_id,
            "back_edge_band_id": self.back_edge_band_id,
            "carcass_method": self.carcass_method,
            "top_method": self.top_method, "back_method": self.back_method,
            "back_recess_mm": self.back_recess_mm,
            "plinth_height_mm": self.plinth_height_mm,
            "plinth_recess_mm": self.plinth_recess_mm,
            "shelf_count": self.shelf_count,
            "divider_count": self.divider_count,
            "door_type": self.door_type, "door_count": self.door_count,
            "door_gap_mm": self.door_gap_mm,
            "door_edge_gap_mm": self.door_edge_gap_mm,
            "door_vertical_gap_mm": self.door_vertical_gap_mm,
            "door_overlap_mm": self.door_overlap_mm,
            "door_covers_plinth": self.door_covers_plinth,
            "sliding_track_height_mm": self.sliding_track_height_mm,
            "drawer_count": self.drawer_count,
            "drawer_heights_mm": [float(v) for v in self.drawer_heights_mm],
            "drawer_front_height_mm": self.drawer_front_height_mm,
            "drawer_position": self.drawer_position,
            "drawer_box": self.drawer_box,
            "drawer_box_thickness_mm": self.drawer_box_thickness_mm,
            "drawer_slide_clearance_mm": self.drawer_slide_clearance_mm,
            "drawer_box_depth_clearance_mm": self.drawer_box_depth_clearance_mm,
            "drawer_box_height_clearance_mm": self.drawer_box_height_clearance_mm,
            "hinge_count_per_door": self.hinge_count_per_door,
            "hinge_offset_mm": self.hinge_offset_mm,
            "hardware": dict(self.hardware),
            "origin_mm": [float(v) for v in self.origin_mm],
            "rotation_z_deg": self.rotation_z_deg,
            "notes": self.notes, "tags": list(self.tags),
            "created_at": self.created_at, "updated_at": self.updated_at,
            "extra": dict(self.extra),
        }

    @classmethod
    def from_dict(cls, raw: Any) -> "ModuleSpec":
        if not isinstance(raw, dict):
            raise ValueError("module must be a JSON object")
        heights = raw.get("drawer_heights_mm")
        tags = raw.get("tags")
        hardware = raw.get("hardware")
        extra = raw.get("extra")
        spec = cls(
            id=str(raw.get("id") or new_id("mod")),
            code=str(raw.get("code") or ""),
            type=str(raw.get("type") or "armario_inferior"),
            name=str(raw.get("name") or ""),
            room=str(raw.get("room") or ""),
            width_mm=_num(raw.get("width_mm"), 800.0),
            height_mm=_num(raw.get("height_mm"), 850.0),
            depth_mm=_num(raw.get("depth_mm"), 550.0),
            panel_thickness_mm=_num(raw.get("panel_thickness_mm"), 18.0),
            front_thickness_mm=_num(raw.get("front_thickness_mm"), 18.0),
            back_thickness_mm=_num(raw.get("back_thickness_mm"), 6.0),
            material_id=str(raw.get("material_id") or DEFAULT_MATERIAL_ID),
            front_material_id=str(raw.get("front_material_id") or ""),
            back_material_id=str(raw.get("back_material_id") or ""),
            edge_band_id=str(raw.get("edge_band_id") or DEFAULT_EDGE_BAND_ID),
            front_edge_band_id=str(raw.get("front_edge_band_id") or ""),
            back_edge_band_id=str(raw.get("back_edge_band_id") or ""),
            carcass_method=str(raw.get("carcass_method") or "laterais_passantes"),
            top_method=str(raw.get("top_method") or "tampo"),
            back_method=str(raw.get("back_method") or "rasgo"),
            back_recess_mm=_num(raw.get("back_recess_mm"), 15.0),
            plinth_height_mm=_num(raw.get("plinth_height_mm"), 100.0),
            plinth_recess_mm=_num(raw.get("plinth_recess_mm"), 60.0),
            shelf_count=max(0, _int(raw.get("shelf_count"), 1)),
            divider_count=max(0, _int(raw.get("divider_count"), 0)),
            door_type=str(raw.get("door_type") or "hinged"),
            door_count=max(0, _int(raw.get("door_count"), 2)),
            door_gap_mm=_num(raw.get("door_gap_mm"), 3.0),
            door_edge_gap_mm=_num(raw.get("door_edge_gap_mm"), 2.0),
            door_vertical_gap_mm=_num(raw.get("door_vertical_gap_mm"), 2.0),
            door_overlap_mm=_num(raw.get("door_overlap_mm"), 20.0),
            door_covers_plinth=_bool(raw.get("door_covers_plinth"), False),
            sliding_track_height_mm=_num(raw.get("sliding_track_height_mm"), 40.0),
            drawer_count=max(0, _int(raw.get("drawer_count"), 0)),
            drawer_heights_mm=([_num(v) for v in heights if _num(v) > 0]
                                if max(0, _int(raw.get("drawer_count"), 0)) > 0
                                and isinstance(heights, (list, tuple))
                                else []),
            drawer_front_height_mm=_num(raw.get("drawer_front_height_mm"), 180.0),
            drawer_position=str(raw.get("drawer_position") or "bottom"),
            drawer_box=_bool(raw.get("drawer_box"), True),
            drawer_box_thickness_mm=_num(raw.get("drawer_box_thickness_mm"), 15.0),
            drawer_slide_clearance_mm=_num(raw.get("drawer_slide_clearance_mm"), 26.0),
            drawer_box_depth_clearance_mm=_num(
                raw.get("drawer_box_depth_clearance_mm"), 50.0),
            drawer_box_height_clearance_mm=_num(
                raw.get("drawer_box_height_clearance_mm"), 30.0),
            hinge_count_per_door=max(0, _int(raw.get("hinge_count_per_door"), 0)),
            hinge_offset_mm=_num(raw.get("hinge_offset_mm"), 100.0),
            hardware=dict(hardware) if isinstance(hardware, dict) else {},
            origin_mm=_tuple3(raw.get("origin_mm")),
            rotation_z_deg=_num(raw.get("rotation_z_deg")),
            notes=str(raw.get("notes") or ""),
            tags=[str(t) for t in tags] if isinstance(tags, (list, tuple)) else [],
            created_at=str(raw.get("created_at") or now_iso()),
            updated_at=str(raw.get("updated_at") or now_iso()),
            extra=dict(extra) if isinstance(extra, dict) else {},
        )
        if not spec.name:
            spec.name = f"{MODULE_LABELS.get(spec.type, 'Módulo')} {int(spec.width_mm)}"
        return spec

    def copy(self, *, new_identity: bool = False) -> "ModuleSpec":
        import copy as _copy
        spec = _copy.deepcopy(self)
        if new_identity:
            spec.id = new_id("mod")
            spec.code = ""
            spec.name = (spec.name + " (cópia)") if spec.name else spec.name
            spec.created_at = spec.updated_at = now_iso()
        return spec

    # ---- validation -------------------------------------------------------
    def validate(self, limits: dict | None = None) -> list[str]:
        problems: list[str] = []
        if self.type not in MODULE_TYPES:
            problems.append(f"Tipo de módulo desconhecido: {self.type}.")
        if not self.name.strip():
            problems.append("O módulo precisa de um nome.")
        for label, value in (("largura", self.width_mm),
                             ("altura", self.height_mm),
                             ("profundidade", self.depth_mm)):
            if not math.isfinite(value) or value <= 0:
                problems.append(f"A {label} deve ser maior que zero.")
        if self.panel_thickness_mm <= 0:
            problems.append("A espessura das chapas deve ser positiva.")
        if self.front_thickness_mm <= 0:
            problems.append("A espessura das frentes deve ser positiva.")
        if self.back_thickness_mm <= 0:
            problems.append("A espessura do fundo deve ser positiva.")
        if self.back_thickness_mm >= self.depth_mm:
            problems.append("O fundo não pode ser mais espesso que a profundidade.")
        if self.plinth_height_mm < 0 or self.plinth_height_mm >= self.height_mm:
            problems.append("A altura do rodapé deve ser menor que a altura total.")
        if self.plinth_recess_mm < 0 or self.plinth_recess_mm >= self.depth_mm:
            problems.append("O recuo do rodapé deve ser menor que a profundidade.")
        if self.back_recess_mm < 0 or self.back_recess_mm >= self.depth_mm:
            problems.append("O recuo do fundo deve ser menor que a profundidade.")
        if self.carcass_method not in CARCASS_METHODS:
            problems.append("Método de montagem da caixa inválido.")
        if self.top_method not in TOP_METHODS:
            problems.append("Método de topo inválido.")
        if self.back_method not in BACK_METHODS:
            problems.append("Método de fundo inválido.")
        if self.door_type not in DOOR_TYPES:
            problems.append("Tipo de porta inválido.")
        if self.door_type != "none" and self.door_count <= 0:
            problems.append("Informe pelo menos uma porta.")
        if self.door_type == "sliding" and self.door_count not in (2, 3):
            problems.append("Portas de correr usam 2 ou 3 folhas.")
        if min(self.door_gap_mm, self.door_edge_gap_mm,
               self.door_vertical_gap_mm) < 0:
            problems.append("As folgas das portas não podem ser negativas.")
        if self.door_type != "none":
            effective_gap = 2 * self.door_edge_gap_mm + max(
                0, self.door_count - 1) * self.door_gap_mm
            door_width = (self.width_mm - effective_gap) / max(1, self.door_count)
            if door_width < 100:
                problems.append(
                    f"As portas resultariam com {door_width:.0f} mm de largura "
                    "(mínimo prático de 100 mm nesta versão).")
        if self.drawer_count < 0:
            problems.append("A quantidade de gavetas não pode ser negativa.")
        if len(self.drawer_heights_mm) not in (0, self.drawer_count):
            problems.append(
                "A lista de alturas de gavetas deve ter uma medida por gaveta.")
        if any(h <= 0 for h in self.drawer_heights_mm):
            problems.append("As alturas das gavetas devem ser positivas.")
        if self.drawer_position not in ("bottom", "top"):
            problems.append("Posição das gavetas inválida.")
        if self.shelf_count < 0 or self.divider_count < 0:
            problems.append("Prateleiras e divisórias não podem ser negativas.")
        if self.shelf_count > 30 or self.divider_count > 12:
            problems.append("Quantidade de prateleiras/divisórias acima do limite seguro.")
        if self.rotation_z_deg % 360 != 0 and not all(
                math.isfinite(v) for v in self.origin_mm):
            problems.append("Origem do módulo inválida.")
        if self.hinge_count_per_door < 0:
            problems.append("A quantidade de dobradiças não pode ser negativa.")
        if self.hinge_offset_mm < 0:
            problems.append("O recuo das dobradiças não pode ser negativo.")
        # Reasonable interior must remain after the carcass.  These rules only
        # apply to modules that actually build a carcass: a shelf or a
        # worktop is one solid panel whose height *is* its thickness, so the
        # "two sides + base + top" arithmetic would reject valid pieces.
        builds_carcass = self.type not in (
            "prateleira", "painel", "porta_abrir", "porta_correr", "bancada")
        body_h = self.height_mm - max(0.0, self.plinth_height_mm)
        if builds_carcass:
            if self.width_mm - 2 * self.panel_thickness_mm <= 0:
                problems.append("A largura é insuficiente para duas laterais.")
            if body_h - 2 * self.panel_thickness_mm <= 0:
                problems.append("A altura é insuficiente para base e topo.")
        if self.back_method != "sem_fundo" and (
                self.depth_mm - self.back_thickness_mm
                - self.back_recess_mm <= 0):
            problems.append("A profundidade é insuficiente para o fundo.")
        if self.door_type != "none" and self.door_count > 0:
            if self.door_type == "sliding" and body_h <= 2 * self.sliding_track_height_mm:
                problems.append("A altura é insuficiente para as guias das portas.")
        if limits:
            table = limits.get(self.type) if isinstance(limits, dict) else None
            if isinstance(table, dict):
                for key, value, label in (
                        ("w", self.width_mm, "largura"),
                        ("h", self.height_mm, "altura"),
                        ("d", self.depth_mm, "profundidade")):
                    bounds = table.get(key)
                    if isinstance(bounds, (list, tuple)) and len(bounds) == 2:
                        lo, hi = float(bounds[0]), float(bounds[1])
                        if not (lo <= value <= hi):
                            problems.append(
                                f"A {label} de {value:.0f} mm está fora da faixa "
                                f"configurada ({lo:.0f}–{hi:.0f} mm).")
        return problems

    def raise_if_invalid(self, limits: dict | None = None) -> None:
        from .errors import ValidationError
        problems = self.validate(limits)
        if problems:
            raise ValidationError(problems, module_name=self.label)


# ---------------------------------------------------------------------------
# Generated results
# ---------------------------------------------------------------------------

@dataclass
class Panel:
    """One physical board, plus the metadata needed by the shop floor."""
    id: str
    code: str
    name: str
    role: str
    module_id: str
    material_id: str
    thickness_mm: float
    length_mm: float
    width_mm: float
    grain: str = "length"
    edges: dict = field(default_factory=lambda: {s: "" for s in EDGE_SIDES})
    position_mm: tuple = (0.0, 0.0, 0.0)
    size_mm: tuple = (0.0, 0.0, 0.0)
    qty: int = 1
    note: str = ""

    @property
    def area_m2(self) -> float:
        return (self.length_mm * self.width_mm) / 1_000_000.0 * max(1, self.qty)

    def edge_length_mm(self, side: str) -> float:
        if side in ("top", "bottom"):
            return self.length_mm
        return self.width_mm

    def edge_total_mm(self) -> float:
        return sum(self.edge_length_mm(s) for s, band in self.edges.items() if band)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "code": self.code, "name": self.name,
            "role": self.role, "module_id": self.module_id,
            "material_id": self.material_id,
            "thickness_mm": self.thickness_mm,
            "length_mm": self.length_mm, "width_mm": self.width_mm,
            "grain": self.grain, "edges": dict(self.edges),
            "position_mm": [float(v) for v in self.position_mm],
            "size_mm": [float(v) for v in self.size_mm],
            "qty": int(self.qty), "note": self.note,
        }

    @classmethod
    def from_dict(cls, raw: Any) -> "Panel":
        raw = raw if isinstance(raw, dict) else {}
        return cls(
            id=str(raw.get("id") or new_id("part")),
            code=str(raw.get("code") or "P"),
            name=str(raw.get("name") or "Peça"),
            role=str(raw.get("role") or "outro"),
            module_id=str(raw.get("module_id") or ""),
            material_id=str(raw.get("material_id") or ""),
            thickness_mm=_num(raw.get("thickness_mm")),
            length_mm=_num(raw.get("length_mm")),
            width_mm=_num(raw.get("width_mm")),
            grain=str(raw.get("grain") or "length")
            if raw.get("grain") in GRAIN_CHOICES else "length",
            edges=_edges(raw.get("edges")),
            position_mm=_tuple3(raw.get("position_mm")),
            size_mm=_tuple3(raw.get("size_mm")),
            qty=max(1, _int(raw.get("qty"), 1)),
            note=str(raw.get("note") or ""),
        )


@dataclass
class HardwareUse:
    hardware_id: str
    name: str
    qty: float
    unit: str = "un"
    detail: str = ""

    def to_dict(self) -> dict:
        return {"hardware_id": self.hardware_id, "name": self.name,
                "qty": float(self.qty), "unit": self.unit,
                "detail": self.detail}

    @classmethod
    def from_dict(cls, raw: Any) -> "HardwareUse":
        raw = raw if isinstance(raw, dict) else {}
        return cls(str(raw.get("hardware_id") or ""),
                   str(raw.get("name") or "Ferragem"),
                   _num(raw.get("qty")), str(raw.get("unit") or "un"),
                   str(raw.get("detail") or ""))


@dataclass
class BuildResult:
    spec: ModuleSpec
    panels: list[Panel] = field(default_factory=list)
    hardware: list[HardwareUse] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    assembly: dict = field(default_factory=dict)

    @property
    def part_count(self) -> int:
        return sum(max(1, p.qty) for p in self.panels)

    def to_dict(self) -> dict:
        return {
            "module": self.spec.to_dict(),
            "panels": [p.to_dict() for p in self.panels],
            "hardware": [h.to_dict() for h in self.hardware],
            "warnings": list(self.warnings),
            "assembly": dict(self.assembly),
        }
