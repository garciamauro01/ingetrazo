# SPDX-License-Identifier: GPL-3.0-or-later
"""Domain models, module validation, project bookkeeping and settings."""
from __future__ import annotations

import json

import pytest

from plugins.furniture_pro.core.constants import DEFAULT_LIMITS
from plugins.furniture_pro.core.models import (
    BuildResult,
    EdgeBand,
    HardwareItem,
    Material,
    ModuleSpec,
    Panel,
    hex_to_rgb,
    new_id,
    rgb_to_hex,
)
from plugins.furniture_pro.core.project import Project, ProjectSettings


def test_material_round_trip_keeps_every_field():
    material = Material(
        "MAT-X", "MDF Teste", "MDF", manufacturer="Fornecedor",
        reference="REF-1", color="#123456", texture_path="C:/t.png",
        thickness_mm=25.0, sheet_length_mm=2800.0, sheet_width_mm=1850.0,
        cost_per_sheet=199.9, cost_per_m2=42.5, grain_axis="width",
        allow_rotation=False, finish="Fosco", supplier="Loja",
        availability=False, edge_band_id="EB-X", notes="nota",
    )
    assert Material.from_dict(material.to_dict()) == material
    assert Material.from_dict(None).name == "Material"
    assert material.rgb() == (0x12 / 255, 0x34 / 255, 0x56 / 255)


@pytest.mark.parametrize("value,expected", [
    ("#fff", (1.0, 1.0, 1.0)),
    ("#000000", (0.0, 0.0, 0.0)),
    ("not-a-colour", (0.90, 0.89, 0.85)),
    (None, (0.90, 0.89, 0.85)),
])
def test_hex_to_rgb_is_safe(value, expected):
    assert hex_to_rgb(value) == expected


def test_rgb_to_hex_clamps_and_survives_bad_input():
    assert rgb_to_hex((1.5, -1.0, 0.5)) == "#FF0080"
    assert rgb_to_hex(None) == "#E6E4DD"
    assert rgb_to_hex((0.1,)) == "#E6E4DD"


def test_edge_band_and_hardware_round_trip_and_validation():
    band = EdgeBand("EB-X", "Fita", "#FFFFFF", 0.45, "PVC", 1.5, "Loja",
                    False, "nota")
    assert EdgeBand.from_dict(band.to_dict()) == band
    assert band.validate() == []
    assert EdgeBand("", "", thickness_mm=-1, cost_per_m=-2).validate()

    hardware = HardwareItem("HW-X", "Dobradiça", "dobradica", "Fab",
                            "REF", "un", 12.5, {"cup_mm": 35},
                            "catalogue", True, "Loja", "nota")
    assert HardwareItem.from_dict(hardware.to_dict()) == hardware
    assert HardwareItem("H", "Ok").validate() == []
    assert HardwareItem("", "").validate()
    assert HardwareItem("H", "Ok", cost=-1).validate()


def test_module_spec_round_trip_and_copy_identity():
    spec = ModuleSpec(type="guarda_roupa", name="GR teste",
                      width_mm=1800, height_mm=2300, depth_mm=600,
                      drawer_heights_mm=[200, 250], drawer_count=2,
                      tags=["quarto"], hardware={"HW-HINGE-35": 4},
                      extra={"origin": "cliente"})
    raw = spec.to_dict()
    # The data must survive a JSON round-trip, as the document does.
    assert ModuleSpec.from_dict(json.loads(json.dumps(raw))) == spec
    clone = spec.copy(new_identity=True)
    assert clone.id != spec.id and clone.code == ""
    assert clone.name.endswith("(cópia)")
    assert clone.width_mm == spec.width_mm


def test_module_spec_from_dict_sanitises_hostile_values():
    spec = ModuleSpec.from_dict({
        "width_mm": "not a number", "height_mm": float("nan"),
        "drawer_count": "-3", "shelf_count": "-2",
        "drawer_heights_mm": [0, "bad", 120],
        "origin_mm": ["1", "2"],
        "grain": "sideways",
    })
    assert spec.width_mm == 800.0 and spec.height_mm == 850.0
    assert spec.drawer_count == 0 and spec.shelf_count == 0
    # Without drawers there are no drawer heights to keep; hostile entries
    # are dropped and only positive measurements survive.
    assert spec.drawer_heights_mm == []
    assert spec.origin_mm == (0.0, 0.0, 0.0)

    with_drawers = ModuleSpec.from_dict({
        "drawer_count": 2, "drawer_heights_mm": [100, "bad", 250],
    })
    assert with_drawers.drawer_count == 2
    assert with_drawers.drawer_heights_mm == [100.0, 250.0]


def test_module_requires_a_name_and_valid_dimensions():
    spec = ModuleSpec(type="armario_inferior", name="")
    problems = spec.validate(DEFAULT_LIMITS)
    assert any("nome" in p for p in problems)
    spec = ModuleSpec(type="armario_inferior", name="A", width_mm=0,
                      height_mm=-1, depth_mm=0)
    problems = spec.validate()
    assert any("largura" in p for p in problems)
    assert any("altura" in p for p in problems)
    assert any("profundidade" in p for p in problems)


def test_shelf_and_worktop_are_not_rejected_as_tiny_cabinets():
    """A 25 mm shelf is one board, not a cabinet that cannot fit a base."""
    shelf = ModuleSpec.from_dict({
        "type": "prateleira", "name": "Prateleira", "height_mm": 25,
        "panel_thickness_mm": 25, "depth_mm": 250,
        "plinth_height_mm": 0, "plinth_recess_mm": 0,
        "door_type": "none", "door_count": 0, "back_method": "sem_fundo",
    })
    assert shelf.validate() == []
    top = ModuleSpec.from_dict({
        "type": "bancada", "name": "Bancada", "width_mm": 2000,
        "height_mm": 40, "depth_mm": 600, "panel_thickness_mm": 40,
        "plinth_height_mm": 0, "back_method": "sem_fundo",
        "door_type": "none", "door_count": 0,
    })
    assert top.validate() == []


def test_door_and_drawer_rules_catch_impossible_configurations():
    spec = ModuleSpec(type="armario_inferior", name="A", width_mm=250,
                      height_mm=500, depth_mm=300, door_count=6,
                      door_type="hinged", drawer_count=2,
                      drawer_heights_mm=[100])
    problems = spec.validate()
    assert any("100 mm" in p for p in problems)
    assert any("alturas de gavetas" in p for p in problems)

    sliding = ModuleSpec(type="guarda_roupa", name="GR", width_mm=2000,
                         height_mm=2400, depth_mm=600, door_type="sliding",
                         door_count=4)
    assert any("2 ou 3" in p for p in sliding.validate())


def test_project_code_generation_is_stable_and_unique():
    project = Project()
    first = project.next_code("armario_inferior")
    project.add_module(ModuleSpec(type="armario_inferior", code=first))
    second = project.next_code("armario_inferior")
    assert (first, second) == ("AI-01", "AI-02")
    assert project.next_code("torre") == "TR-01"
    assert project.next_code("desconhecido") == "MOD-01"


def test_project_module_management_and_room_list():
    project = Project(name="Cozinha")
    a = project.add_module(ModuleSpec(type="armario_inferior", room="Cozinha"))
    b = project.add_module(ModuleSpec(type="armario_superior", room=""))
    assert a.code and b.code
    assert project.module(a.id) is a
    assert project.rooms() == ["Cozinha", "Geral"]
    assert project.total_width_mm() == a.width_mm + b.width_mm
    with pytest.raises(ValueError):
        project.add_module(ModuleSpec(id=a.id, type="armario_inferior"))

    project.move_module(b.id, -1)
    assert project.modules[0] is b
    project.move_module(b.id, 99)
    assert project.modules[-1] is b

    updated = a.copy()
    updated.width_mm = 900
    project.update_module(updated)
    assert project.module(a.id).width_mm == 900
    with pytest.raises(ValueError):
        project.update_module(ModuleSpec(id="missing"))

    assert project.remove_module(b.id) is not None
    assert project.remove_module(b.id) is None


def test_project_settings_units_and_round_trip():
    settings = ProjectSettings.from_dict({
        "units": "cm", "precision_mm": "0.5", "currency": "EUR",
        "validity_days": "30", "show_dimensions": False,
    })
    assert settings.units == "cm"
    assert settings.precision_mm == 0.5
    assert settings.validity_days == 30
    assert settings.show_dimensions is False
    assert settings.to_display(123.0) == pytest.approx(12.3)
    assert settings.unit_label() == "cm"
    assert ProjectSettings.from_dict({"units": "furlong"}).units == "mm"


def test_project_document_payload_round_trip_and_validation_errors():
    from plugins.furniture_pro.hardware import HardwareLibrary
    from plugins.furniture_pro.materials import MaterialLibrary

    materials = MaterialLibrary.with_defaults()
    hardware = HardwareLibrary.with_defaults()
    libraries = {"materials": materials.materials,
                 "edge_bands": materials.edge_bands,
                 "hardware": hardware.items}
    project = Project(name="Projeto", client="Cliente")
    spec = project.add_module(ModuleSpec(type="armario_inferior", width_mm=800))
    payload = project.document_payload()
    loaded = Project.from_document_payload(json.loads(json.dumps(payload)))
    assert loaded.name == project.name
    assert loaded.modules[0].to_dict() == spec.to_dict()

    report = project.validate(libraries)
    assert report.ok, report.as_text()
    # The generic catalogue has no prices: that is a warning, never an error.
    assert any("sem preço" in w for w in report.warnings)

    duplicate = Project()
    duplicate.modules = [spec.copy(), spec.copy()]
    report = duplicate.validate(libraries)
    assert any("repetido" in e for e in report.errors)
    assert report.as_text().startswith("Erros:")
    assert Project.from_dict({"modules": ["not a dict"]}).load_warnings


def test_build_result_helpers():
    panel = Panel("p1", "P1", "Peça", "base", "m1", "MAT", 18,
                  1000, 500, edges={"top": "EB", "bottom": "EB"})
    assert panel.area_m2 == pytest.approx(0.5)
    assert panel.edge_total_mm() == 2000
    result = BuildResult(ModuleSpec(name="M"), panels=[panel, panel])
    assert result.part_count == 2
    assert result.to_dict()["panels"][0]["length_mm"] == 1000
    assert json.dumps(result.to_dict())
    assert new_id("x").startswith("x-")
