# SPDX-License-Identifier: GPL-3.0-or-later
"""Versioned project persistence: .fproj files, JSON envelopes and migration."""
from __future__ import annotations

import json

import pytest

from plugins.furniture_pro.core.errors import DataError
from plugins.furniture_pro.core.project import Project
from plugins.furniture_pro.core.models import ModuleSpec
from plugins.furniture_pro.core.constants import SCHEMA_VERSION
from plugins.furniture_pro.persistence import (PROJECT_SUFFIX, dumps_project,
                                              loads_project, load_project,
                                              migrate_payload, project_from_payload,
                                              save_project, wrap_project)


def _project() -> Project:
    project = Project(name="Cozinha", client="Ana Souza")
    project.add_module(ModuleSpec(
        type="armario_inferior", name="Armário inferior 800", width_mm=800,
        height_mm=850, depth_mm=550, code="AI-01"))
    return project


def _module_id(project: Project) -> str:
    module = project.modules[0]
    return module.id


def test_save_and_load_project_file_round_trip(tmp_path) -> None:
    project = _project()
    path = tmp_path / "projeto.fproj"
    save_project(path, project)
    assert path.exists()
    loaded = load_project(path)
    assert loaded.name == "Cozinha"
    assert loaded.client == "Ana Souza"
    module = loaded.modules[0]
    assert module.width_mm == 800
    envelope = json.loads(path.read_text(encoding="utf-8"))
    assert envelope["schema"] == SCHEMA_VERSION
    assert envelope["plugin"] == "furniture_pro"
    assert envelope["project"]["name"] == "Cozinha"


def test_dumps_and_loads_project_json_round_trip() -> None:
    project = _project()
    loaded = loads_project(dumps_project(project))
    assert loaded.name == project.name
    assert len(loaded.modules) == 1
    assert loaded.modules[0].height_mm == 850


def test_document_payload_round_trip(tmp_path) -> None:
    from plugins.furniture_pro.persistence import project_from_payload

    project = _project()
    raw = json.loads(json.dumps(project.document_payload()))
    loaded = project_from_payload(raw)
    assert loaded.name == project.name
    assert loaded.modules[0].to_dict() == project.modules[0].to_dict()


def test_migrate_bare_project_dict_from_schema_zero() -> None:
    project = _project()
    payload, original = migrate_payload(project.to_dict())
    assert original == 0
    assert payload["schema"] == SCHEMA_VERSION
    assert payload["project"]["name"] == "Cozinha"


def test_migrate_current_envelope_keeps_schema_one() -> None:
    payload, original = migrate_payload(_project().document_payload())
    assert original == SCHEMA_VERSION
    assert payload["schema"] == SCHEMA_VERSION
    assert payload["project"]["name"] == "Cozinha"


def test_migrate_future_schema_adds_a_warning() -> None:
    warnings: list[str] = []
    payload, original = migrate_payload(
        {"schema": 99, "plugin": "furniture_pro", "project": _project().to_dict()},
        warnings=warnings)
    assert original == 99
    assert payload["schema"] == SCHEMA_VERSION
    assert any("mais novo" in w for w in warnings)


def test_migrate_never_mutates_the_input_and_tolerates_bad_shapes() -> None:
    warnings: list[str] = []
    payload, original = migrate_payload(["not an object"], warnings=warnings)
    assert original == 0
    assert payload["schema"] == SCHEMA_VERSION
    assert any("objeto" in w for w in warnings)

    payload, original = migrate_payload({"project": "not-a-dict"}, warnings=[])
    assert original == 0
    assert payload["schema"] == SCHEMA_VERSION


def test_load_project_never_crashes_on_a_missing_file(tmp_path) -> None:
    with pytest.raises(DataError):
        load_project(tmp_path / "does-not-exist.fproj")


def test_load_project_rejects_a_corrupt_json_file(tmp_path) -> None:
    path = tmp_path / "corrupto.fproj"
    path.write_text("{not json at all", encoding="utf-8")
    with pytest.raises(DataError):
        load_project(path)


def test_load_project_migrates_and_keeps_the_modules(tmp_path) -> None:
    path = tmp_path / "legado.fproj"
    save_project(path, _project())
    envelope = json.loads(path.read_text(encoding="utf-8"))
    envelope["schema"] = 0
    path.write_text(json.dumps(envelope), encoding="utf-8")
    loaded = load_project(path)
    assert loaded.modules[0].width_mm == 800
    assert loaded.load_warnings == []
