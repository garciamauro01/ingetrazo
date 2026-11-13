# SPDX-License-Identifier: GPL-3.0-or-later
"""Parts list, cutting optimiser, reports, drawings and previews."""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET

import pytest

from plugins.furniture_pro.core.errors import OptimizerError
from plugins.furniture_pro.core.models import Material
from plugins.furniture_pro.drawings import cut_plan_svg, module_front_svg, write_svg
from plugins.furniture_pro.furniture import template_by_type
from plugins.furniture_pro.furniture.generator import build_module
from plugins.furniture_pro.hardware import HardwareLibrary
from plugins.furniture_pro.manufacturing import (
    BoardPlan,
    CutPlan,
    CutSettings,
    Placement,
    build_parts_list,
    cut_plan_csv_text,
    optimize,
    parts_csv_text,
    pdf_available,
    plan_from_dict,
    validate_plan,
    write_cut_plan_csv,
    write_json,
    write_parts_csv,
    write_pdf_report,
)
from plugins.furniture_pro.manufacturing.parts_list import PartItem
from plugins.furniture_pro.materials import MaterialLibrary
from plugins.furniture_pro.rendering import render_module_image, save_module_png


@pytest.fixture()
def libraries():
    materials = MaterialLibrary.with_defaults()
    hardware = HardwareLibrary.with_defaults()
    for material in materials.materials.values():
        material.cost_per_sheet = 200.0
    return materials.materials, materials.edge_bands, hardware.items


def _part(code, length, width, *, qty=1, grain="length", material="MAT"):
    return PartItem(code=code, id=f"part-{code}", name=f"Peça {code}",
                    role="teste", material_id=material, thickness_mm=18,
                    length_mm=length, width_mm=width, grain=grain, qty=qty,
                    module_ids=["m1"], source_codes=[code])


def _material(material_id="MAT", *, grain="length", rotation=True,
              length=1000.0, width=600.0):
    return Material(material_id, "Chapa teste", thickness_mm=18,
                    sheet_length_mm=length, sheet_width_mm=width,
                    grain_axis=grain, allow_rotation=rotation,
                    cost_per_sheet=120.0)


# ---- parts list -----------------------------------------------------------

def test_parts_list_aggregates_identical_panels_across_modules(libraries):
    materials, bands, _hardware = libraries
    first = template_by_type("armario_inferior").create()
    first.code = "AI-01"
    second = first.copy(new_identity=True)
    second.code = "AI-02"
    results = [build_module(first, materials, bands),
               build_module(second, materials, bands)]
    parts = build_parts_list(results, materials)
    panels = [p for result in results for p in result.panels]
    assert parts.total_pieces == len(panels)
    assert parts.total_area_m2 == pytest.approx(sum(p.area_m2 for p in panels))
    assert parts.total_pieces > len(parts.items)      # aggregation happened
    assert all(item.qty >= 1 for item in parts.items)
    assert all(len(item.source_codes) == len(set(item.source_codes))
               for item in parts.items)
    assert set(parts.edge_length_by_band()) <= set(bands)
    assert not parts.warnings
    assert parts.to_dict()["totals"]["pieces"] == parts.total_pieces
    # Every emitted code is unique in the shop-floor list.
    codes = [item.code for item in parts.items]
    assert len(codes) == len(set(codes))


def test_parts_list_flags_bad_panels_and_unknown_materials():
    from plugins.furniture_pro.core.models import Panel

    bad = Panel("p", "P", "Ruim", "teste", "m", "MISSING", 0, 0, -1)
    parts = build_parts_list([__import__(
        "plugins.furniture_pro.core.models", fromlist=["BuildResult"]
    ).BuildResult(__import__(
        "plugins.furniture_pro.core.models", fromlist=["ModuleSpec"]
    ).ModuleSpec(name="M"), panels=[bad])], {})
    assert any("espessura inválida" in w for w in parts.warnings)
    assert any("dimensões inválidas" in w for w in parts.warnings)
    assert any("material não cadastrado" in w.lower() for w in parts.warnings)


# ---- optimiser ------------------------------------------------------------

def test_optimiser_packs_parts_without_overlap_or_kerf_loss():
    settings = CutSettings(kerf_mm=10, trim_mm=0, allow_rotation=False,
                           min_offcut_mm=10)
    parts = [_part("A", 400, 300, qty=3), _part("B", 200, 200, qty=2)]
    plan = optimize(parts, {"MAT": _material()}, settings)
    validate_plan(plan)
    assert plan.unplaced == []
    placements = [p for board in plan.boards for p in board.placements]
    assert len(placements) == 5
    for board in plan.boards:
        for i, a in enumerate(board.placements):
            assert (a.x_mm >= -1e-6 and a.y_mm >= -1e-6
                    and a.x_mm + a.length_mm <= board.length_mm + 1e-6
                    and a.y_mm + a.width_mm <= board.width_mm + 1e-6)
            for b in board.placements[i + 1:]:
                # Pieces plus the reserved kerf may not overlap either.
                gap_x = (a.x_mm + a.length_mm + settings.kerf_mm
                         <= b.x_mm + 1e-6
                         or b.x_mm + b.length_mm + settings.kerf_mm
                         <= a.x_mm + 1e-6)
                gap_y = (a.y_mm + a.width_mm + settings.kerf_mm
                         <= b.y_mm + 1e-6
                         or b.y_mm + b.width_mm + settings.kerf_mm
                         <= a.y_mm + 1e-6)
                assert gap_x or gap_y, (a, b)
    assert plan.total_cost == pytest.approx(plan.board_count * 120.0)
    assert 0.0 < plan.utilization <= 1.0


def test_grain_constraints_control_rotation():
    material = _material(grain="length")
    length_grain = _part("L", 600, 300, grain="length")
    width_grain = _part("W", 600, 300, grain="width")
    plan = optimize([length_grain, width_grain], {"MAT": material},
                    CutSettings(kerf_mm=0, trim_mm=0))
    by_code = {p.code: p for p in plan.boards[0].placements}
    assert by_code["L"].rotated is False
    assert (by_code["L"].length_mm, by_code["L"].width_mm) == (600, 300)
    assert by_code["W"].rotated is True
    assert (by_code["W"].length_mm, by_code["W"].width_mm) == (300, 600)


def test_disabling_rotation_never_violates_grain_silently():
    material = _material(grain="length", rotation=False)
    part = _part("W", 900, 500, grain="width")
    plan = optimize([part], {"MAT": material},
                    CutSettings(kerf_mm=0, trim_mm=0,
                                allow_rotation=False))
    assert any("rotação desativada" in w for w in plan.warnings)
    assert plan.boards[0].placements[0].rotated is False


def test_trim_keeps_parts_inside_the_usable_sheet():
    settings = CutSettings(kerf_mm=4, trim_mm=10, allow_rotation=False)
    plan = optimize([_part("A", 500, 400)], {"MAT": _material()}, settings)
    placement = plan.boards[0].placements[0]
    assert placement.x_mm >= 10 and placement.y_mm >= 10
    assert placement.x_mm + placement.length_mm <= 1000 - 10
    assert placement.y_mm + placement.width_mm <= 600 - 10


def test_oversize_parts_are_reported_not_silently_dropped():
    settings = CutSettings(kerf_mm=0, trim_mm=0, allow_rotation=False)
    plan = optimize([_part("BIG", 2000, 900)], {"MAT": _material()}, settings)
    assert plan.boards == []
    assert len(plan.unplaced) == 1
    assert "não cabe" in plan.unplaced[0]["reason"]
    assert any("BIG" in w for w in plan.warnings)


def test_unknown_material_uses_the_documented_fallback():
    plan = optimize([_part("A", 500, 400)], {},
                    CutSettings(fallback_board_length_mm=800,
                                fallback_board_width_mm=600,
                                trim_mm=0, kerf_mm=0))
    assert plan.boards[0].length_mm == 800
    assert plan.boards[0].width_mm == 600
    assert any("Material não cadastrado" in w for w in plan.warnings)


def test_quantity_is_expanded_into_individual_placements():
    plan = optimize([_part("A", 300, 200, qty=5)], {"MAT": _material()},
                    CutSettings(kerf_mm=0, trim_mm=0))
    assert len(plan.boards[0].placements) == 5
    assert plan.boards[0].used_area_m2 == pytest.approx(5 * 0.06)


def test_invalid_cut_settings_are_rejected():
    with pytest.raises(OptimizerError):
        optimize([], {}, CutSettings(kerf_mm=-1))
    with pytest.raises(OptimizerError):
        optimize([], {}, CutSettings(fallback_board_length_mm=10,
                                     trim_mm=10))


def test_plan_validation_refuses_overlaps_and_out_of_sheet_parts():
    board = BoardPlan(1, "MAT", "Chapa", 1000, 600, 18)
    board.placements.append(Placement("P1", "a", "A", "A", "MAT", [],
                                      10, 10, 500, 300, False, "length"))
    board.placements.append(Placement("P2", "b", "B", "B", "MAT", [],
                                      100, 100, 500, 300, False, "length"))
    with pytest.raises(OptimizerError, match="Sobreposição"):
        validate_plan(CutPlan(boards=[board]))

    board.placements[1] = Placement("P2", "b", "B", "B", "MAT", [],
                                    900, 10, 200, 100, False, "length")
    with pytest.raises(OptimizerError, match="fora da chapa"):
        validate_plan(CutPlan(boards=[board]))


def test_cut_plan_dict_round_trip(libraries):
    materials, bands, _hardware = libraries
    spec = template_by_type("armario_inferior").create()
    result = build_module(spec, materials, bands)
    plan = optimize(build_parts_list([result], materials).items, materials,
                    CutSettings(kerf_mm=4, trim_mm=10))
    restored = plan_from_dict(json.loads(json.dumps(plan.to_dict())))
    assert restored.board_count == plan.board_count
    assert restored.unplaced == plan.unplaced
    assert restored.used_area_m2 == pytest.approx(plan.used_area_m2)
    assert restored.to_dict()["totals"] == pytest.approx(plan.to_dict()["totals"])


# ---- reports and drawings --------------------------------------------------

def test_csv_and_json_reports_are_well_formed(libraries, tmp_path):
    materials, bands, hardware = libraries
    spec = template_by_type("armario_inferior").create()
    result = build_module(spec, materials, bands)
    parts = build_parts_list([result], materials)
    plan = optimize(parts.items, materials, CutSettings())

    parts_text = parts_csv_text(parts, materials)
    cut_text = cut_plan_csv_text(plan)
    assert "Código" in parts_text and "Fita superior" in parts_text
    assert "Chapa" in cut_text and "X (mm)" in cut_text
    assert "None" not in parts_text and "nan" not in parts_text.lower()

    write_parts_csv(tmp_path / "parts.csv", parts, materials)
    write_cut_plan_csv(tmp_path / "cut.csv", plan)
    write_json(tmp_path / "cut.json", plan.to_dict())
    assert (tmp_path / "parts.csv").read_bytes().startswith(b"\xef\xbb\xbf")
    assert (tmp_path / "cut.csv").read_bytes().startswith(b"\xef\xbb\xbf")
    payload = json.loads((tmp_path / "cut.json").read_text(encoding="utf-8"))
    assert payload["totals"]["boards"] == plan.board_count


def test_svg_drawings_are_valid_vectors(libraries, tmp_path):
    materials, bands, _hardware = libraries
    spec = template_by_type("cozinha" if False else "armario_inferior").create()
    result = build_module(spec, materials, bands)
    plan = optimize(build_parts_list([result], materials).items, materials,
                    CutSettings())

    front = module_front_svg(spec, result)
    cutting = cut_plan_svg(plan)
    for text in (front, cutting):
        root = ET.fromstring(text)
        assert root.tag.endswith("svg")
        assert "mm" in root.attrib["width"]

    write_svg(tmp_path / "front.svg", front)
    write_svg(tmp_path / "cut.svg", cutting)
    assert "Armário inferior" in front
    assert "Chapa" in cutting
    assert (tmp_path / "front.svg").read_text(encoding="utf-8").startswith("<?xml")


def test_png_preview_renders_and_saves(libraries, tmp_path):
    materials, bands, _hardware = libraries
    spec = template_by_type("armario_inferior").create()
    result = build_module(spec, materials, bands)
    image = render_module_image(result, materials, 320, 240)
    assert not image.isNull()
    assert image.width() == 320 and image.height() == 240
    path = tmp_path / "preview.png"
    save_module_png(path, result, materials, 320, 240)
    assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.skipif(not pdf_available(), reason="PySide6 QPdfWriter missing")
def test_pdf_report_is_generated(libraries, tmp_path):
    materials, bands, hardware = libraries
    spec = template_by_type("armario_inferior").create()
    result = build_module(spec, materials, bands)
    parts = build_parts_list([result], materials)
    plan = optimize(parts.items, materials, CutSettings())
    path = tmp_path / "report.pdf"
    write_pdf_report(path, title="Teste", parts=parts, plan=plan,
                     materials=materials, hardware=hardware,
                     drawing_svgs={"Armário inferior": "AI-01.svg"})
    data = path.read_bytes()
    assert data.startswith(b"%PDF")
    assert len(data) > 2000
