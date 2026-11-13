# SPDX-License-Identifier: GPL-3.0-or-later
"""Catalogue templates and the parametric generator, module by module."""
from __future__ import annotations

import math

import pytest

from plugins.furniture_pro.core.constants import MODULE_TYPES
from plugins.furniture_pro.core.errors import ValidationError
from plugins.furniture_pro.core.models import ModuleSpec
from plugins.furniture_pro.furniture import categories, template_by_type, templates
from plugins.furniture_pro.furniture.generator import build_module
from plugins.furniture_pro.hardware import HardwareLibrary
from plugins.furniture_pro.materials import MaterialLibrary


@pytest.fixture(scope="module")
def libraries():
    materials = MaterialLibrary.with_defaults()
    hardware = HardwareLibrary.with_defaults()
    return materials.materials, materials.edge_bands, hardware.items


@pytest.fixture()
def material_prices():
    materials = MaterialLibrary.with_defaults().materials
    for material in materials.values():
        material.cost_per_sheet = 200.0
    return materials


def test_catalogue_covers_every_documented_module_type():
    assert {t.type for t in templates()} == set(MODULE_TYPES)
    assert len(templates()) == len(MODULE_TYPES)
    assert template_by_type("armario_inferior").label == "Armário inferior"
    assert template_by_type("does-not-exist") is None
    assert "Armários" in categories() and "Portas" in categories()


def test_every_template_creates_a_valid_spec_with_its_own_defaults():
    for template in templates():
        spec = template.create()
        assert spec.type == template.type
        assert spec.id.startswith("mod-")
        assert spec.name.startswith(template.label)
        assert spec.validate() == [], (template.type, spec.validate())
        for key, value in template.defaults.items():
            assert getattr(spec, key) == value


@pytest.mark.parametrize("template", templates(), ids=lambda t: t.type)
def test_every_module_type_builds_real_panels(template, libraries):
    materials, bands, _hardware = libraries
    spec = template.create()
    result = build_module(spec, materials, bands)
    assert result.spec is spec
    assert result.panels, template.type
    codes = [panel.code for panel in result.panels]
    assert len(codes) == len(set(codes)), "duplicate part codes"
    for panel in result.panels:
        assert panel.length_mm > 0 and panel.width_mm > 0
        assert panel.thickness_mm > 0
        assert all(math.isfinite(v) for v in panel.position_mm)
        assert all(math.isfinite(v) for v in panel.size_mm)
        assert all(v > 0 for v in panel.size_mm)
        assert panel.module_id == spec.id
        assert panel.material_id in materials
        assert panel.grain in ("length", "width", "none")
        assert set(panel.edges) == {"top", "bottom", "left", "right"}
    assert result.part_count == len(result.panels)
    # Generic defaults have no prices; the warning is expected and harmless.
    assert any("sem preço" in w for w in result.warnings)


def test_lower_cabinet_has_the_expected_shop_floor_parts(libraries):
    materials, bands, _hardware = libraries
    spec = template_by_type("armario_inferior").create()
    result = build_module(spec, materials, bands)
    roles = {panel.role for panel in result.panels}
    assert {"lateral", "base", "topo", "fundo", "rodape", "porta",
            "prateleira"} <= roles
    assert len([p for p in result.panels if p.role == "porta"]) == 2
    uses = {use.hardware_id: use.qty for use in result.hardware}
    assert uses["HW-HINGE-35"] == 4          # two doors, two hinges each
    assert uses["HW-HANDLE-BAR"] == 2
    assert uses["HW-FOOT"] == 4
    assert result.assembly["has_plinth"] is True
    assert result.assembly["body_height_mm"] == 750
    assert len(result.assembly["doors"]) == 2


def test_drawer_unit_creates_boxes_and_correct_minus_one_clearance(libraries):
    materials, bands, _hardware = libraries
    spec = template_by_type("gaveteiro").create()
    spec.drawer_box = True
    result = build_module(spec, materials, bands)
    fronts = [p for p in result.panels if p.role == "frente_gaveta"]
    assert len(fronts) == 4
    # Each drawer produces two sides, two rails and a bottom.
    box_parts = [p for p in result.panels if p.role.startswith("gaveta_")]
    assert len(box_parts) == 4 * 5
    assert any("corrediça" in use.name.lower() for use in result.hardware)
    zones = [p for p in result.panels if p.role == "gaveta_fundo"]
    assert len(zones) == 4
    for panel in fronts:
        assert panel.width_mm == spec.width_mm - 2 * spec.door_edge_gap_mm


def test_construction_methods_change_the_geometry(libraries):
    materials, bands, _hardware = libraries
    base = template_by_type("armario_inferior").create()
    full = build_module(base, materials, bands)
    side_full = next(p for p in full.panels if p.role == "lateral")

    rail = base.copy()
    rail.carcass_method = "tampo_base_passantes"
    rail_result = build_module(rail, materials, bands)
    side_rail = next(p for p in rail_result.panels if p.role == "lateral")
    assert side_rail.length_mm == pytest.approx(
        side_full.length_mm - 2 * rail.panel_thickness_mm)

    open_top = base.copy()
    open_top.top_method = "travessas"
    open_result = build_module(open_top, materials, bands)
    assert not any(p.role == "topo" for p in open_result.panels)
    assert len([p for p in open_result.panels if p.role == "travessa"]) == 2

    no_back = base.copy()
    no_back.back_method = "sem_fundo"
    no_back_result = build_module(no_back, materials, bands)
    assert not any(p.role == "fundo" for p in no_back_result.panels)

    no_doors = base.copy()
    no_doors.door_type = "none"
    no_doors.door_count = 0
    no_doors_result = build_module(no_doors, materials, bands)
    assert not any(p.role == "porta" for p in no_doors_result.panels)
    assert not any(use.hardware_id == "HW-HINGE-35"
                   for use in no_doors_result.hardware)


def test_single_panel_modules_are_one_physical_board(libraries):
    materials, bands, _hardware = libraries
    for module_type, expected_name in (("prateleira", "Prateleira"),
                                       ("painel", "Painel / divisória"),
                                       ("porta_abrir", "Porta de abrir"),
                                       ("bancada", "Bancada")):
        spec = template_by_type(module_type).create()
        result = build_module(spec, materials, bands)
        assert len(result.panels) == 1, module_type
        panel = result.panels[0]
        assert panel.name == expected_name
        if module_type == "painel":
            assert panel.length_mm == spec.height_mm
            assert panel.width_mm == spec.width_mm
        elif module_type == "prateleira":
            assert panel.length_mm == spec.width_mm
            assert panel.width_mm == spec.depth_mm


def test_sliding_door_set_has_leaves_and_guides(libraries):
    materials, bands, _hardware = libraries
    spec = template_by_type("porta_correr").create()
    result = build_module(spec, materials, bands)
    leaves = [p for p in result.panels if p.role == "porta_correr"]
    guides = [p for p in result.panels if p.role == "guia"]
    assert len(leaves) == 2 and len(guides) == 2
    assert all(p.material_id == spec.material_for_front() for p in leaves)
    assert all(p.length_mm < spec.height_mm for p in leaves)
    assert result.assembly["tracks"]["height_mm"] >= 20
    assert any("kit de correr" in w.lower() for w in result.warnings)


def test_custom_dimensions_flow_into_every_panel(libraries):
    materials, bands, _hardware = libraries
    spec = template_by_type("armario_superior").create()
    spec.width_mm, spec.height_mm, spec.depth_mm = 1000, 800, 400
    result = build_module(spec, materials, bands)
    for panel in result.panels:
        assert panel.position_mm[0] <= 1000 + 1e-6
        assert panel.position_mm[2] <= 800 + 1e-6
        if panel.role not in ("porta",):
            assert panel.position_mm[1] <= 400 + 1e-6
    assert max(p.position_mm[0] + p.size_mm[0] for p in result.panels) \
        == pytest.approx(1000, abs=0.01)


def test_invalid_modules_raise_a_readable_validation_error(libraries):
    materials, bands, _hardware = libraries
    spec = template_by_type("armario_inferior").create()
    spec.width_mm = 10
    with pytest.raises(ValidationError) as info:
        build_module(spec, materials, bands)
    assert "largura" in info.value.user_message.lower()
    assert info.value.problems


def test_missing_library_entries_produce_warnings_not_crashes():
    spec = template_by_type("armario_inferior").create()
    spec.material_id = "MAT-MISSING"
    result = build_module(spec, {}, {})
    assert result.panels
    assert any("Material não cadastrado" in w for w in result.warnings)
    assert any("Fita de borda não cadastrada" in w for w in result.warnings)


def test_priced_material_removes_the_price_warning(material_prices, libraries):
    _materials, bands, _hardware = libraries
    spec = template_by_type("armario_inferior").create()
    result = build_module(spec, material_prices, bands)
    assert not any("sem preço" in w for w in result.warnings)


def test_spec_validation_and_generation_are_pure(libraries):
    materials, bands, _hardware = libraries
    spec = ModuleSpec(type="armario_inferior", name="Dois")
    build_module(spec, materials, bands)
    persisted = spec.to_dict()
    assert persisted["type"] == "armario_inferior"
    assert persisted["width_mm"] == 800
