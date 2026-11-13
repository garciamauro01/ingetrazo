# SPDX-License-Identifier: GPL-3.0-or-later
"""The host bridge: controller CRUD, quotes, cutting plan and diagnostics."""
from __future__ import annotations

import pytest

from plugins.furniture_pro.adapters import FurnitureController
from plugins.furniture_pro.core.constants import DEFAULT_LIMITS
from plugins.furniture_pro.core.errors import ValidationError
from plugins.furniture_pro.core.models import ModuleSpec
from plugins.furniture_pro.core.validation import validate_project
from plugins.furniture_pro.furniture import template_by_type
from plugins.furniture_pro.manufacturing import validate_plan


@pytest.fixture()
def controller(tmp_path):
    return FurnitureController(data_dir=tmp_path)


def _spec(**overrides) -> ModuleSpec:
    values = dict(type="armario_inferior", name="Armário teste", width_mm=800,
                  height_mm=850, depth_mm=550, door_type="hinged", door_count=2)
    values.update(overrides)
    return ModuleSpec(**values)


def test_controller_starts_with_an_empty_project(controller) -> None:
    assert controller.project.modules == []
    assert controller.results() == []
    assert controller.validation().ok


def test_controller_inserts_builds_updates_and_deletes_a_module(
        controller) -> None:
    spec = _spec()
    result = controller.insert_module(spec)
    assert result.part_count > 0
    assert len(controller.project.modules) == 1
    assert controller.build(spec).part_count == result.part_count

    updated = spec.copy()
    updated.width_mm = 900.0
    controller.update_module(updated)
    assert controller.project.module(spec.id).width_mm == 900.0

    assert controller.delete_module(spec.id)
    assert controller.project.modules == []


def test_controller_rejects_a_duplicate_module_identifier(controller) -> None:
    spec = _spec()
    controller.insert_module(spec)
    with pytest.raises(ValidationError):
        controller.insert_module(spec.copy())


def test_controller_duplicate_creates_a_following_code(controller) -> None:
    first = controller.insert_module(_spec())
    clone = controller.duplicate_module(first.spec.id)
    assert clone is not None
    assert clone.code == "AI-02"
    assert len(controller.project.modules) == 2


def test_controller_quote_and_cut_plan_for_a_real_module(controller) -> None:
    controller.insert_module(_spec())
    quote = controller.quote()
    assert len(quote.modules) == 1
    assert quote.currency == "BRL"
    assert quote.warnings, "the generic catalogue has no prices yet"

    plan = controller.cut_plan()
    validate_plan(plan)
    assert plan.unplaced == []
    assert plan.boards


def test_controller_validation_of_a_project_with_an_unpriced_material(
        controller) -> None:
    controller.insert_module(_spec())
    report = controller.validation()
    assert report.ok
    assert any("sem preço" in w for w in report.warnings)


def test_controller_limits_are_the_default_catalogue_limits() -> None:
    assert FurnitureController(data_dir=None).limits() == DEFAULT_LIMITS


def test_controller_environment_report_is_readable() -> None:
    controller = FurnitureController(data_dir=None)
    report = controller.environment_report()
    assert "Furniture Pro" in report
    assert "Schema:" in report


def test_controller_save_and_load_project_through_the_host_bridge(
        controller, tmp_path) -> None:
    controller.insert_module(_spec())
    path = tmp_path / "projeto.fproj"
    controller.save_project(path)
    loaded = controller.load_project(path, replace_scene=False)
    module = loaded.modules[0]
    assert module.width_mm == 800.0


def test_controller_domain_helpers_are_available() -> None:
    controller = FurnitureController(data_dir=None)
    assert callable(controller.parts_list)
    assert callable(controller.assembly)
    assert callable(controller.results)
    assert callable(controller.libraries)
