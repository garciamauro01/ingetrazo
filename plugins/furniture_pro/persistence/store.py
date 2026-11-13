# SPDX-License-Identifier: GPL-3.0-or-later
"""Versioned persistence for projects and libraries.

Two formats exist and must not be confused:

* **document payload** — one JSON-safe dict in ``scene.plugin_data``; saved by
  Ingetrazo inside the ``.igz`` and restored by the host automatically.
* **project file** — ``.fproj``, a JSON envelope around the same project, for
  sharing a job with another machine or keeping a version in a folder.

Both go through :func:`migrate_payload`, so an old document opened after a
plugin upgrade is converted once and then re-saved in the current schema.
Writes are atomic (temporary file + ``os.replace``) so an interrupted save
never destroys the previous file.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from ..core.constants import PLUGIN_KEY, PLUGIN_VERSION, SCHEMA_VERSION
from ..core.errors import DataError
from ..core.logging_utils import get_logger
from ..core.models import now_iso
from ..core.project import Project

PROJECT_SUFFIX = ".fproj"
PROJECT_FILTER = "Projeto Furniture Pro (*.fproj);;JSON (*.json)"


def wrap_project(project: Project, *, schema: int = SCHEMA_VERSION) -> dict:
    """Current envelope for a project, used by both save paths."""
    return {
        "schema": max(1, int(schema)),
        "plugin": PLUGIN_KEY,
        "plugin_version": PLUGIN_VERSION,
        "saved_at": now_iso(),
        "project": project.to_dict(),
    }


def migrate_payload(raw, *, warnings: list[str] | None = None) -> tuple[dict, int]:
    """Return ``(current_payload, original_schema)`` for any supported input.

    Accepted inputs:

    * a current envelope (``{"project": {...}, "schema": 1}``);
    * a bare project dict (early development builds and hand-made files);
    * ``None``/``{}`` — an empty project.
    """
    warnings = warnings if warnings is not None else []
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        warnings.append("Dados do projeto não são um objeto JSON; "
                        "um projeto vazio foi carregado.")
        raw = {}
    original = raw.get("schema", 0)
    try:
        original = int(original)
    except (TypeError, ValueError):
        original = 0

    if "project" in raw:
        project_data = raw.get("project")
        if not isinstance(project_data, dict):
            warnings.append("Seção 'project' inválida; projeto vazio.")
            project_data = {}
    else:
        # Schema 0: the project itself was the payload.
        project_data = dict(raw)
        project_data.pop("schema", None)
        project_data.pop("plugin", None)
        project_data.pop("plugin_version", None)

    # Schema 1 is current.  Future migrations slot in here, one step per
    # version, always converting forward and never mutating the input.
    if original < 1:
        project_data.setdefault("created_at", now_iso())
        project_data.setdefault("updated_at", now_iso())
        settings = project_data.get("settings")
        if not isinstance(settings, dict):
            project_data["settings"] = {}
    elif original > SCHEMA_VERSION:
        warnings.append(
            f"O arquivo usa o esquema {original}, mais novo que o suportado "
            f"({SCHEMA_VERSION}). Os campos desconhecidos serão preservados, "
            "mas confira o projeto antes de fabricar.")

    payload = {
        "schema": SCHEMA_VERSION,
        "plugin": PLUGIN_KEY,
        "plugin_version": raw.get("plugin_version") or PLUGIN_VERSION,
        "saved_at": raw.get("saved_at") or now_iso(),
        "project": project_data,
    }
    return payload, original


def project_from_payload(raw, *, warnings: list[str] | None = None) -> Project:
    warnings = warnings if warnings is not None else []
    payload, original = migrate_payload(raw, warnings=warnings)
    project = Project.from_document_payload(payload, warnings=warnings)
    if original != SCHEMA_VERSION:
        get_logger().info("project migrated from schema %s to %s",
                          original, SCHEMA_VERSION)
    return project


def _atomic_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = None
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
        handle = os.fdopen(fd, "w", encoding="utf-8", newline="\n")
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        handle = None
        os.replace(temp_name, path)
    except OSError as exc:
        raise DataError(f"Não foi possível gravar {path}: {exc}",
                        details=str(exc)) from exc
    finally:
        if handle is not None:
            handle.close()


def save_project(path, project: Project) -> None:
    """Write a ``.fproj`` file atomically."""
    payload = wrap_project(project)
    try:
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    except (TypeError, ValueError) as exc:
        raise DataError(f"O projeto contém dados inválidos: {exc}",
                        details=str(exc)) from exc
    _atomic_text(Path(path), text)


def load_project(path) -> Project:
    """Read a ``.fproj`` file; never crashes on a damaged file."""
    path = Path(path)
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            raw = json.load(handle)
    except FileNotFoundError as exc:
        raise DataError(f"Arquivo não encontrado: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise DataError(f"Arquivo de projeto inválido: {path}",
                        details=str(exc)) from exc
    warnings: list[str] = []
    project = project_from_payload(raw, warnings=warnings)
    if warnings:
        get_logger().warning("project loaded with warnings: %s", warnings)
    project.load_warnings = list(dict.fromkeys(warnings))
    return project


def dumps_project(project: Project) -> str:
    return json.dumps(wrap_project(project), ensure_ascii=False, indent=2) + "\n"


def loads_project(text: str) -> Project:
    try:
        raw = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise DataError("O texto não contém um projeto válido.",
                        details=str(exc)) from exc
    warnings: list[str] = []
    return project_from_payload(raw, warnings=warnings)
