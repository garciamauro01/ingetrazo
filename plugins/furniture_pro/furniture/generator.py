# SPDX-License-Identifier: GPL-3.0-or-later
"""Parametric furniture rules and part generation.

The generator is deliberately independent of Ingetrazo/Qt.  It receives a
:class:`~..core.models.ModuleSpec`, validates it, and returns a
:class:`~..core.models.BuildResult` containing every physical panel and the
hardware implied by the configuration.  The adapter turns those panels into
3D groups; the manufacturing module turns the same list into cutlists and
cutting plans.

Construction conventions
------------------------
* Module local axes: X = width, Y = depth (front at Y=0, wall at Y=depth),
  Z = height.  All values in millimetres.
* Panels are flat rectangles.  ``length_mm`` is the long cut dimension and
  ``width_mm`` the short one.  The four edge-band sides are named relative to
  that flat rectangle: ``top``/``bottom`` are the long edges and
  ``left``/``right`` the short ends.  This is stated again in the UI.
* A 3D box is described by ``position_mm`` (minimum corner) and ``size_mm``.
"""
from __future__ import annotations

import math
from typing import Any, Iterable

from ..core.errors import ValidationError
from ..core.models import (
    BuildResult,
    HardwareUse,
    Material,
    ModuleSpec,
    Panel,
    now_iso,
)

_ZERO = 0.0


def _r(value: float) -> float:
    return round(float(value), 2)


class _PartFactory:
    def __init__(self, spec: ModuleSpec) -> None:
        self.spec = spec
        self.panels: list[Panel] = []
        self._used: dict[str, int] = {}

    def next_code(self, base: str) -> str:
        n = self._used.get(base, 0) + 1
        self._used[base] = n
        return f"{base}-{n}" if n > 1 else base

    def add(
        self,
        *,
        name: str,
        role: str,
        code: str,
        material_id: str,
        length: float,
        width: float,
        thickness: float,
        size: tuple[float, float, float],
        position: tuple[float, float, float],
        edges: dict | None = None,
        grain: str = "length",
        note: str = "",
    ) -> Panel:
        final_code = self.next_code(code)
        panel = Panel(
            id=f"{self.spec.id}:{final_code}",
            code=final_code,
            name=name,
            role=role,
            module_id=self.spec.id,
            material_id=material_id,
            thickness_mm=_r(thickness),
            length_mm=_r(length),
            width_mm=_r(width),
            grain=grain if grain in ("length", "width", "none") else "length",
            edges={k: (edges or {}).get(k, "") for k in
                   ("top", "bottom", "left", "right")},
            position_mm=tuple(_r(v) for v in position),
            size_mm=tuple(_r(v) for v in size),
            qty=1,
            note=note,
        )
        self.panels.append(panel)
        return panel


def _all_edges(band: str) -> dict[str, str]:
    return {"top": band, "bottom": band, "left": band, "right": band}


def _front_edge(band: str) -> dict[str, str]:
    # The front edge of a horizontal panel is one of its long edges.
    return {"top": band, "bottom": "", "left": "", "right": ""}


def _hinge_count(door_height: float, configured: int) -> int:
    if configured > 0:
        return configured
    if door_height <= 900:
        return 2
    if door_height <= 1600:
        return 3
    if door_height <= 2200:
        return 4
    return 5


def _hinge_positions(door_height: float, count: int, offset: float) -> list[float]:
    """Rule-based positions, measured from the bottom of the door.

    These are *layout* positions for documentation, not a manufacturer's
    drilling pattern.  Real cup/bore data is only emitted when the user has
    entered verified installation data in the hardware library.
    """
    count = max(2, int(count))
    lo = max(0.0, min(offset, door_height / 3.0))
    hi = max(lo, door_height - lo)
    if count == 2:
        return [_r(lo), _r(hi)]
    step = (hi - lo) / (count - 1)
    return [_r(lo + i * step) for i in range(count)]


class ModuleBuilder:
    """Generate panels and hardware from a parametric module specification."""

    def __init__(self, materials: dict[str, Material] | None = None,
                 edge_bands: dict | None = None,
                 limits: dict | None = None) -> None:
        self.materials = materials or {}
        self.edge_bands = edge_bands or {}
        self.limits = limits

    # -- public -------------------------------------------------------------
    def build(self, spec: ModuleSpec) -> BuildResult:
        problems = spec.validate(self.limits)
        if problems:
            raise ValidationError(problems, module_name=spec.label)

        spec.updated_at = now_iso()
        if spec.type in ("prateleira", "painel", "porta_abrir", "bancada"):
            result = self._build_single_panel(spec)
        elif spec.type == "porta_correr":
            result = self._build_sliding_door_set(spec)
        else:
            result = self._build_cabinet(spec)
        self._add_material_warnings(spec, result)
        return result

    # -- special modules ----------------------------------------------------
    def _build_single_panel(self, spec: ModuleSpec) -> BuildResult:
        f = _PartFactory(spec)
        t = spec.panel_thickness_mm
        W, H, D = spec.width_mm, spec.height_mm, spec.depth_mm
        mat = spec.material_id
        band = spec.edge_band_id
        if spec.type == "prateleira":
            size = (W, D, H)
            pos = (0.0, 0.0, 0.0)
            name, role, code = "Prateleira", "prateleira", "PRAT"
            length, width = W, D
            edges = _all_edges(band)
            grain = "length"
        elif spec.type == "painel":
            size = (W, D, H)
            pos = (0.0, 0.0, 0.0)
            name, role, code = "Painel / divisória", "painel", "PAINEL"
            length, width = H, W
            edges = _all_edges(band)
            grain = "length"
        elif spec.type == "porta_abrir":
            size = (W, D, H)
            pos = (0.0, -D, 0.0)
            name, role, code = "Porta de abrir", "porta", "PORTA"
            length, width = H, W
            edges = _all_edges(spec.edge_for_front())
            grain = "length"
            t = spec.front_thickness_mm or D
        else:  # bancada
            size = (W, D, H)
            pos = (0.0, 0.0, 0.0)
            name, role, code = "Bancada", "bancada", "BANCADA"
            length, width = W, D
            edges = _all_edges(band)
            grain = "length"
        f.add(name=name, role=role, code=code, material_id=mat,
              length=length, width=width, thickness=t, size=size, position=pos,
              edges=edges, grain=grain)
        warnings: list[str] = []
        if spec.type in ("prateleira", "painel", "porta_abrir") and H > 600:
            warnings.append(
                "Peça alta: confirme transporte, manuseio e espessura da chapa.")
        return BuildResult(spec=spec, panels=f.panels, warnings=warnings)

    def _build_sliding_door_set(self, spec: ModuleSpec) -> BuildResult:
        f = _PartFactory(spec)
        W, H, D = spec.width_mm, spec.height_mm, spec.depth_mm
        t = spec.panel_thickness_mm
        band = spec.edge_for_front()
        track_h = max(20.0, min(spec.sliding_track_height_mm,
                               max(20.0, H * 0.08)))
        door_h = max(50.0, H - 2 * track_h - 2 * spec.door_vertical_gap_mm)
        count = max(2, spec.door_count)
        overlap = max(0.0, spec.door_overlap_mm)
        door_w = (W + overlap * (count - 1)) / count
        track_depth = max(40.0, min(D * 1.8, 80.0))
        for i in range(count):
            x = i * (door_w - overlap) - overlap / 2.0
            y = -track_depth - (i + 1) * (D + 1.0)
            f.add(name=f"Folha de correr {i + 1}", role="porta_correr",
                  code=f"PORTA-CORRER-{i + 1}", material_id=spec.material_for_front(),
                  length=door_h, width=door_w, thickness=D,
                  size=(door_w, D, door_h), position=(x, y, track_h + spec.door_vertical_gap_mm),
                  edges=_all_edges(band), grain="length")
        # Guide rails are physical parts too; they are not edge-banded.
        for label, z in (("Guia superior", H - track_h),
                         ("Guia inferior", 0.0)):
            f.add(name=label, role="guia", code=label.upper().replace(" ", "-"),
                  material_id=spec.material_id, length=W, width=track_depth,
                  thickness=t, size=(W, track_depth, track_h),
                  position=(0.0, -track_depth, z), edges={}, grain="length")
        hw = [
            HardwareUse("HW-SLIDE-SLIDING", "Kit de correr (par de guias)",
                        max(1, count - 1), "kit",
                        "Quantidade conforme folhas configuradas"),
            HardwareUse("HW-HANDLE-BAR", "Puxador", count, "un",
                        "Um puxador por folha"),
        ]
        return BuildResult(spec=spec, panels=f.panels, hardware=hw,
                           warnings=["Confirme o kit de correr com o fabricante."],
                           assembly={"tracks": {"height_mm": track_h,
                                                "depth_mm": track_depth}})

    # -- cabinet ------------------------------------------------------------
    def _build_cabinet(self, spec: ModuleSpec) -> BuildResult:
        f = _PartFactory(spec)
        W, H, D = spec.width_mm, spec.height_mm, spec.depth_mm
        t = spec.panel_thickness_mm
        tf = spec.front_thickness_mm
        tb = spec.back_thickness_mm
        mat = spec.material_id
        mat_front = spec.material_for_front()
        mat_back = spec.material_for_back()
        band = spec.edge_band_id
        band_front = spec.edge_for_front()
        warnings: list[str] = []

        has_plinth = spec.plinth_height_mm > 0 and spec.type not in (
            "armario_superior", "nicho", "prateleira", "painel",
            "porta_abrir", "porta_correr", "bancada")
        ph = spec.plinth_height_mm if has_plinth else 0.0
        body_h = H - ph
        z0 = ph

        sides_full = spec.carcass_method in (
            "laterais_passantes", "montagem_oculta", "personalizado")
        # Laterais
        if sides_full:
            side_h = body_h
            side_z = z0
            inner_w = W - 2 * t
        else:
            side_h = body_h - 2 * t
            side_z = z0 + t
            inner_w = W - 2 * t
        if inner_w <= 0 or side_h <= 0:
            raise ValidationError(["Dimensões internas inválidas para a caixa."],
                                  module_name=spec.label)

        for label, x in (("Lateral esquerda", 0.0),
                         ("Lateral direita", W - t)):
            f.add(name=label, role="lateral", code="LAT-E" if x == 0 else "LAT-D",
                  material_id=mat, length=side_h, width=D, thickness=t,
                  size=(t, D, side_h), position=(x, 0.0, side_z),
                  edges={"top": band, "bottom": "", "left": "", "right": ""},
                  grain="length", note="Borda frontal = borda superior da peça planificada")

        # Base e topo
        bottom_size_w = W if not sides_full else inner_w
        bottom_x = t if sides_full else 0.0
        f.add(name="Base", role="base", code="BASE", material_id=mat,
              length=bottom_size_w, width=D, thickness=t,
              size=(bottom_size_w, D, t), position=(bottom_x, 0.0, z0),
              edges=_front_edge(band), grain="length")
        top_z = H - t if sides_full else H - t
        if spec.top_method == "tampo":
            f.add(name="Topo", role="topo", code="TOPO", material_id=mat,
                  length=bottom_size_w, width=D, thickness=t,
                  size=(bottom_size_w, D, t), position=(bottom_x, 0.0, top_z),
                  edges=_front_edge(band), grain="length")
        elif spec.top_method == "travessas":
            rail_h = max(60.0, min(100.0, body_h * 0.12))
            for label, y in (("Travessa frontal", 0.0),
                             ("Travessa traseira", D - t)):
                f.add(name=label, role="travessa", code=label.upper().replace(" ", "-"),
                      material_id=mat, length=bottom_size_w, width=rail_h,
                      thickness=t, size=(bottom_size_w, t, rail_h),
                      position=(t if sides_full else 0.0, y, H - rail_h),
                      edges={"top": band, "bottom": "", "left": "", "right": ""},
                      grain="length")

        # Fundo
        back_setback = 0.0
        if spec.back_method != "sem_fundo":
            back_recess = max(0.0, spec.back_recess_mm)
            if spec.back_method == "sobreposto":
                back_w, back_h = W, body_h
                back_x, back_z = 0.0, z0
                back_y = D - tb
                back_setback = tb
            else:
                back_w = max(10.0, inner_w)
                back_h = max(10.0, body_h - 2 * t)
                back_x, back_z = t, z0 + t
                back_y = max(0.0, D - tb - back_recess)
                back_setback = tb + back_recess
            f.add(name="Fundo", role="fundo", code="FUNDO", material_id=mat_back,
                  length=back_h, width=back_w, thickness=tb,
                  size=(back_w, tb, back_h), position=(back_x, back_y, back_z),
                  edges={}, grain="width", note="Fundo sem fita de borda")

        usable_depth = max(50.0, D - back_setback - 20.0)
        interior_z0 = z0 + t
        interior_h = max(10.0, body_h - 2 * t)

        # Divisórias / baias
        div_count = max(0, spec.divider_count)
        boundaries = [t]
        if div_count:
            span = max(1.0, inner_w)
            for i in range(div_count):
                centre = t + span * (i + 1) / (div_count + 1)
                boundaries.extend([centre - t / 2.0, centre + t / 2.0])
                f.add(name=f"Divisória {i + 1}", role="divisoria",
                      code=f"DIV-{i + 1}", material_id=mat,
                      length=interior_h, width=usable_depth, thickness=t,
                      size=(t, usable_depth, interior_h),
                      position=(centre - t / 2.0, 0.0, z0 + t),
                      edges={"top": band, "bottom": "", "left": "", "right": ""},
                      grain="length")
        boundaries.append(W - t)
        bays = [(boundaries[i], boundaries[i + 1])
                for i in range(0, len(boundaries), 2)
                if boundaries[i + 1] > boundaries[i]]

        # Prateleiras em cada baia
        for bay_i, (bx0, bx1) in enumerate(bays, start=1):
            bay_w = bx1 - bx0
            if spec.shelf_count <= 0 or bay_w < 30:
                continue
            clear = min(2.0, max(0.0, bay_w * 0.01))
            shelf_w = max(10.0, bay_w - 2 * clear)
            for s in range(spec.shelf_count):
                z = interior_z0 + interior_h * (s + 1) / (spec.shelf_count + 1) - t / 2.0
                f.add(name=f"Prateleira {bay_i}.{s + 1}", role="prateleira",
                      code=f"PRAT-{bay_i}-{s + 1}", material_id=mat,
                      length=shelf_w, width=usable_depth, thickness=t,
                      size=(shelf_w, usable_depth, t),
                      position=(bx0 + clear, 0.0, max(interior_z0, z)),
                      edges=_front_edge(band), grain="length")

        # Rodapé
        if has_plinth:
            f.add(name="Rodapé", role="rodape", code="RODAPE", material_id=mat,
                  length=ph, width=W, thickness=t,
                  size=(W, t, ph),
                  position=(0.0, min(spec.plinth_recess_mm, D - t), 0.0),
                  edges={"top": band, "bottom": "", "left": "", "right": ""},
                  grain="width", note="Painel frontal recuado")

        # Frentes: gavetas e portas
        front_zone_bottom = 0.0 if spec.door_covers_plinth else z0
        front_zone_top = H
        edge_gap = max(0.0, spec.door_vertical_gap_mm)
        side_gap = max(0.0, spec.door_edge_gap_mm)
        between = max(0.0, spec.door_gap_mm)

        drawer_span = 0.0
        if spec.drawer_count > 0:
            drawer_span = self._build_drawers(
                f, spec, front_zone_bottom, front_zone_top, side_gap, edge_gap,
                between, tf, mat_front, band_front, warnings)
            if spec.door_type == "sliding" and spec.drawer_count:
                warnings.append(
                    "Gavetas atrás de portas de correr: confirme o acesso e o "
                    "espaço de abertura das folhas.")

        if spec.door_type == "hinged" and spec.door_count > 0:
            self._build_hinged_doors(
                f, spec, front_zone_bottom, front_zone_top, side_gap, edge_gap,
                between, drawer_span, tf, mat_front, band_front, warnings)
        elif spec.door_type == "sliding" and spec.door_count > 0:
            self._build_sliding_doors(
                f, spec, front_zone_bottom, front_zone_top, side_gap, edge_gap,
                tf, mat_front, band_front, warnings)

        # Hardware implied by the configuration
        hardware: list[HardwareUse] = []
        doors = int(spec.door_count) if spec.door_type != "none" else 0
        assembly_doors: list[dict] = []
        if spec.door_type == "hinged" and doors:
            hinge_total = 0
            door_h = max(10.0, (front_zone_top - front_zone_bottom - drawer_span)
                         - 2 * edge_gap)
            for i in range(doors):
                count = _hinge_count(door_h, spec.hinge_count_per_door)
                hinge_total += count
                assembly_doors.append({
                    "index": i + 1,
                    "hinges": count,
                    "hinge_positions_mm": _hinge_positions(
                        door_h, count, spec.hinge_offset_mm),
                })
            hardware.append(HardwareUse(
                "HW-HINGE-35", "Dobradiça 35 mm (genérica)", hinge_total, "un",
                "Posições calculadas por regra; furação oficial não presumida"))
        if spec.drawer_count:
            hardware.append(HardwareUse(
                "HW-SLIDE-35", "Corrediça telescópica (par)", spec.drawer_count,
                "par", "Quantidade = número de gavetas"))
        fronts = doors + (spec.drawer_count if spec.drawer_count else 0)
        if fronts:
            hardware.append(HardwareUse(
                "HW-HANDLE-BAR", "Puxador", fronts, "un",
                "Um puxador por frente (ajustável no cadastro)"))
        if has_plinth:
            hardware.append(HardwareUse(
                "HW-FOOT", "Pé nivelador", 4, "un",
                "Quatro pés por módulo de piso"))

        assembly = {
            "carcass_method": spec.carcass_method,
            "has_plinth": has_plinth,
            "plinth_height_mm": ph,
            "body_height_mm": body_h,
            "interior_width_mm": inner_w,
            "inner_depth_mm": usable_depth,
            "bays": [{"x0": _r(a), "x1": _r(b), "width": _r(b - a)}
                     for a, b in bays],
            "drawer_zone_mm": _r(drawer_span),
            "doors": assembly_doors if spec.door_type == "hinged" else [],
        }
        return BuildResult(spec=spec, panels=f.panels, hardware=hardware,
                           warnings=warnings, assembly=assembly)

    # -- fronts -------------------------------------------------------------
    def _drawer_heights(self, spec: ModuleSpec, available: float,
                        edge_gap: float, between: float) -> list[float]:
        n = max(0, spec.drawer_count)
        if n == 0:
            return []
        if len(spec.drawer_heights_mm) == n:
            heights = [float(h) for h in spec.drawer_heights_mm]
        elif spec.door_type != "none" and available > n * 80:
            # Doors share the front: use the configured individual height, but
            # never consume more than 60% of the available front.
            h = min(spec.drawer_front_height_mm,
                    max(80.0, available * 0.6 / n))
            heights = [h] * n
        else:
            h = (available - 2 * edge_gap - (n - 1) * between) / n
            heights = [h] * n
        return heights

    def _build_drawers(self, f: _PartFactory, spec: ModuleSpec,
                       zone_bottom: float, zone_top: float, side_gap: float,
                       edge_gap: float, between: float, tf: float,
                       mat_front: str, band_front: str,
                       warnings: list[str]) -> float:
        available = zone_top - zone_bottom
        heights = self._drawer_heights(spec, available, edge_gap, between)
        n = len(heights)
        span = sum(heights) + 2 * edge_gap + max(0, n - 1) * between
        if span > available + 0.01:
            scale = max(0.1, (available - 2 * edge_gap - max(0, n - 1) * between)
                        / max(1.0, sum(heights)))
            heights = [h * scale for h in heights]
            span = sum(heights) + 2 * edge_gap + max(0, n - 1) * between
            warnings.append("Alturas das gavetas reduzidas para caber no vão.")
        front_w = spec.width_mm - 2 * side_gap
        if spec.drawer_position == "top":
            cursor = zone_top - edge_gap
            ordered = list(reversed(list(enumerate(heights, start=1))))
            for idx, h in ordered:
                z = cursor - h
                self._drawer_front(f, spec, idx, side_gap, z, front_w, h, tf,
                                   mat_front, band_front)
                cursor = z - between
        else:
            cursor = zone_bottom + edge_gap
            for idx, h in enumerate(heights, start=1):
                self._drawer_front(f, spec, idx, side_gap, cursor, front_w, h,
                                   tf, mat_front, band_front)
                cursor += h + between
        if spec.drawer_box:
            self._drawer_boxes(f, spec, heights, zone_bottom, edge_gap, between,
                               tf, warnings)
        return span

    def _drawer_front(self, f: _PartFactory, spec: ModuleSpec, idx: int,
                      x: float, z: float, w: float, h: float, tf: float,
                      material_id: str, band: str) -> None:
        f.add(name=f"Frente de gaveta {idx}", role="frente_gaveta",
              code=f"GAV-FR-{idx}", material_id=material_id,
              length=h, width=w, thickness=tf,
              size=(w, tf, h), position=(x, -tf, z),
              edges=_all_edges(band), grain="length")

    def _drawer_boxes(self, f: _PartFactory, spec: ModuleSpec,
                      heights: list[float], zone_bottom: float,
                      edge_gap: float, between: float, tf: float,
                      warnings: list[str]) -> None:
        tb = max(9.0, spec.drawer_box_thickness_mm)
        interior_w = max(50.0, spec.width_mm - 2 * spec.panel_thickness_mm)
        box_w = max(30.0, interior_w - spec.drawer_slide_clearance_mm)
        box_depth = max(50.0, spec.depth_mm - tb
                        - spec.drawer_box_depth_clearance_mm
                        - spec.back_thickness_mm)
        x = spec.panel_thickness_mm + spec.drawer_slide_clearance_mm / 2.0
        y = max(0.0, spec.depth_mm - box_depth - spec.drawer_box_depth_clearance_mm)
        cursor = zone_bottom + edge_gap
        for idx, front_h in enumerate(heights, start=1):
            box_h = max(40.0, front_h - spec.drawer_box_height_clearance_mm)
            z = cursor + 10.0
            # Sides (plane depth x height)
            for side, sx in (("E", x), ("D", x + box_w - tb)):
                f.add(name=f"Gaveta {idx} - lateral {side}", role="gaveta_lateral",
                      code=f"GAV-{idx}-LAT-{side}", material_id=spec.material_id,
                      length=box_depth, width=box_h, thickness=tb,
                      size=(tb, box_depth, box_h), position=(sx, y, z),
                      edges={"top": band_edge(spec), "bottom": "", "left": "",
                             "right": ""}, grain="length")
            # Front/back rails (plane width x height)
            for label, sy in (("frontal", y), ("traseira", y + box_depth - tb)):
                f.add(name=f"Gaveta {idx} - {label}", role="gaveta_frente",
                      code=f"GAV-{idx}-{label.upper()}", material_id=spec.material_id,
                      length=box_w, width=box_h, thickness=tb,
                      size=(box_w, tb, box_h), position=(x, sy, z),
                      edges={"top": band_edge(spec), "bottom": "", "left": "",
                             "right": ""}, grain="length")
            # Bottom (plane width x depth)
            f.add(name=f"Gaveta {idx} - fundo", role="gaveta_fundo",
                  code=f"GAV-{idx}-FUNDO", material_id=spec.material_for_back(),
                  length=box_w, width=box_depth, thickness=min(
                      6.0, spec.back_thickness_mm),
                  size=(box_w, box_depth, min(6.0, spec.back_thickness_mm)),
                  position=(x, y, z + 10.0), edges={}, grain="width")
            cursor += front_h + between
        if any(h < 100 for h in heights):
            warnings.append("Gaveta baixa: verifique a altura útil da caixa.")

    def _build_hinged_doors(self, f: _PartFactory, spec: ModuleSpec,
                            zone_bottom: float, zone_top: float,
                            side_gap: float, edge_gap: float,
                            between: float, drawer_span: float,
                            tf: float, material_id: str, band: str,
                            warnings: list[str]) -> None:
        n = int(spec.door_count)
        if drawer_span:
            if spec.drawer_position == "bottom":
                zone_bottom = zone_bottom + drawer_span
            else:
                zone_top = zone_top - drawer_span
        door_h = zone_top - zone_bottom - 2 * edge_gap
        if door_h < 50:
            warnings.append("Não há altura suficiente para as portas; frentes ignoradas.")
            return
        usable = spec.width_mm - 2 * side_gap - max(0, n - 1) * between
        if usable <= 0:
            warnings.append("Não há largura suficiente para as portas; frentes ignoradas.")
            return
        door_w = usable / n
        for i in range(n):
            x = side_gap + i * (door_w + between)
            f.add(name=f"Porta {i + 1}", role="porta", code=f"PORTA-{i + 1}",
                  material_id=material_id, length=door_h, width=door_w,
                  thickness=tf, size=(door_w, tf, door_h),
                  position=(x, -tf, zone_bottom + edge_gap),
                  edges=_all_edges(band), grain="length")
        if door_w > 650:
            warnings.append(
                f"Porta de {door_w:.0f} mm: avalie duas folhas ou dobradiças adicionais.")

    def _build_sliding_doors(self, f: _PartFactory, spec: ModuleSpec,
                             zone_bottom: float, zone_top: float,
                             side_gap: float, edge_gap: float, tf: float,
                             material_id: str, band: str,
                             warnings: list[str]) -> None:
        n = max(2, int(spec.door_count))
        track_h = max(20.0, spec.sliding_track_height_mm)
        door_h = zone_top - zone_bottom - 2 * track_h - 2 * edge_gap
        if door_h < 60:
            warnings.append("Altura insuficiente para portas de correr.")
            return
        overlap = max(0.0, spec.door_overlap_mm)
        door_w = (spec.width_mm + overlap * (n - 1)) / n
        track_depth = max(50.0, min(spec.depth_mm, 80.0))
        for i in range(n):
            x = i * (door_w - overlap) - overlap / 2.0
            y = -track_depth - (i % 2) * (tf + 2.0)
            f.add(name=f"Porta de correr {i + 1}", role="porta_correr",
                  code=f"PORTA-CORRER-{i + 1}", material_id=material_id,
                  length=door_h, width=door_w, thickness=tf,
                  size=(door_w, tf, door_h),
                  position=(x, y, zone_bottom + track_h + edge_gap),
                  edges=_all_edges(band), grain="length")
        for label, z in (("Guia superior", zone_top - track_h),
                         ("Guia inferior", zone_bottom)):
            f.add(name=label, role="guia", code=label.upper().replace(" ", "-"),
                  material_id=spec.material_id, length=spec.width_mm,
                  width=track_depth, thickness=spec.panel_thickness_mm,
                  size=(spec.width_mm, track_depth, track_h),
                  position=(0.0, -track_depth, z), edges={}, grain="length")

    # -- warnings -----------------------------------------------------------
    def _add_material_warnings(self, spec: ModuleSpec,
                               result: BuildResult) -> None:
        ids = {spec.material_id, spec.material_for_front(),
               spec.material_for_back()}
        for mat_id in sorted(i for i in ids if i):
            material = self.materials.get(mat_id)
            if material is None:
                result.warnings.append(
                    f"Material não cadastrado: {mat_id}. A peça será criada, "
                    "mas não entrará no custo de chapas.")
                continue
            if not material.availability:
                result.warnings.append(f"Material indisponível: {material.name}.")
            if abs(material.thickness_mm - spec.panel_thickness_mm) > 0.01 and \
                    mat_id == spec.material_id:
                result.warnings.append(
                    f"A espessura cadastrada de {material.name} "
                    f"({material.thickness_mm:g} mm) difere da espessura do "
                    f"módulo ({spec.panel_thickness_mm:g} mm).")
            if material.cost_per_sheet <= 0 and material.cost_per_m2 <= 0:
                result.warnings.append(
                    f"Material sem preço: {material.name}. O orçamento ficará "
                    "incompleto até o custo ser cadastrado.")
        for band_id in {spec.edge_band_id, spec.edge_for_front()}:
            if band_id and band_id not in self.edge_bands:
                result.warnings.append(
                    f"Fita de borda não cadastrada: {band_id}.")
        if not result.hardware:
            result.warnings.append(
                "Nenhuma ferragem inferida para este módulo; confira a ficha técnica.")


def band_edge(spec: ModuleSpec) -> str:
    """The edge band used on hidden drawer-box tops (same as carcass)."""
    return spec.edge_band_id


def build_module(spec: ModuleSpec,
                 materials: dict[str, Material] | None = None,
                 edge_bands: dict | None = None,
                 limits: dict | None = None) -> BuildResult:
    return ModuleBuilder(materials, edge_bands, limits).build(spec)
