# SPDX-License-Identifier: GPL-3.0-or-later
"""End-to-end export through the controller, plus the parameter editor."""
from __future__ import annotations

from pathlib import Path

import pytest

from plugins.furniture_pro.adapters import FurnitureController
from plugins.furniture_pro.core.models import ModuleSpec
from plugins.furniture_pro.drawings import module_front_svg, write_svg
from plugins.furniture_pro.furniture.generator import build_module
from plugins.furniture_pro.import_export import (export_bundle,
                                                export_project_json, read_json)
from plugins.furniture_pro.materials import MaterialLibrary
from plugins.furniture_pro.rendering import render_module_image, save_module_png
from plugins.furniture_pro.ui.module_form import ModuleEditor
from plugins.furniture_pro.ui.panel import FurniturePanel


@pytest.fixture()
def controller(tmp_path):
    return FurnitureController(data_dir=tmp_path)


def _spec() -> ModuleSpec:
    return ModuleSpec(
        type="armario_inferior", name="Armário inferior 800", code="AI-01",
        width_mm=800, height_mm=850, depth_mm=550, door_type="hinged",
        door_count=2)


def test_module_editor_reads_and_writes_dimensions(controller) -> None:
    editor = ModuleEditor(controller, _spec())
    read = editor.read_spec()
    assert read.type == "armario_inferior"
    assert read.name == "Armário inferior 800"
    assert read.width_mm == 800.0
    assert read.height_mm == 850.0
    assert read.depth_mm == 550.0
    assert read.door_count == 2


def test_module_editor_builds_the_preview_and_the_svg(controller) -> None:
    editor = ModuleEditor(controller, _spec())
    editor._fill_materials()          # noqa: SLF001 - exercising the tab setup
    materials = MaterialLibrary.with_defaults()
    spec = _spec()
    result = build_module(spec, materials.materials, materials.edge_bands)
    assert result.part_count > 0
    svg = module_front_svg(spec, result, scale=0.19)
    assert svg.lstrip().startswith("<?xml")
    write_svg(Path("/tmp/fp_elevacao_teste.svg"), svg)
    image = render_module_image(result, materials.materials, 320, 240)
    assert not image.isNull()
    save_module_png(Path("/tmp/fp_preview_teste.png"), result,
                    materials.materials, 320, 240)


def test_furniture_panel_refreshes_from_an_empty_project(controller) -> None:
    panel = FurniturePanel(controller)
    panel.refresh()
    assert panel.controller is controller


def test_export_bundle_writes_every_artifact(controller, tmp_path) -> None:
    controller.insert_module(_spec())
    bundle_dir = tmp_path / "bundle"
    summary = controller.export_bundle(bundle_dir, include_pdf=True)
    names = {Path(name).name for name in summary["files"]}
    assert "projeto.fproj" in names
    assert "projeto.json" in names
    assert "lista_de_pecas.csv" in names
    assert "orcamento.json" in names
    assert "orcamento.csv" in names
    assert "plano_de_corte.csv" in names
    assert "plano_de_corte.svg" in names
    assert "relatorio.pdf" in names
    assert (bundle_dir / "relatorio.pdf").exists()
    assert (bundle_dir / "projeto.fproj").exists()
    assert (bundle_dir / "plano_de_corte.svg").exists()
    assert (bundle_dir / "orcamento.csv").exists()


def test_export_project_json_and_read_json_round_trip(controller, tmp_path) -> None:
    controller.insert_module(_spec())
    target = tmp_path / "projeto.json"
    export_project_json(target, controller.project)
    payload = read_json(target)
    assert payload["project"]["name"] == controller.project.name
    assert len(payload["project"]["modules"]) == 1
