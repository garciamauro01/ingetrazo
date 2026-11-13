# SPDX-License-Identifier: GPL-3.0-or-later
"""The project model: the one value Furniture Pro saves in the document.

``Project`` is deliberately plain data.  It does not know about Qt, the
host document, or the UI; :mod:`..persistence.store` wraps it in the versioned
payload stored in ``scene.plugin_data`` and in ``.fproj`` files.  That keeps
the save format testable without a running Ingetrazo.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .constants import MODULE_LABELS, PLUGIN_KEY, PLUGIN_VERSION, SCHEMA_VERSION
from .models import ModuleSpec, now_iso
from .validation import ValidationReport, validate_project


@dataclass
class ProjectSettings:
    """Preferences that belong to the project, not to the installation."""

    units: str = "mm"
    precision_mm: float = 0.1
    currency: str = "BRL"
    company_name: str = ""
    company_document: str = ""
    validity_days: int = 15
    show_dimensions: bool = True
    construction_notes: str = ""

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, raw) -> "ProjectSettings":
        raw = raw if isinstance(raw, dict) else {}
        out = cls()
        units = str(raw.get("units") or "mm").lower()
        out.units = units if units in ("mm", "cm", "m") else "mm"
        try:
            out.precision_mm = max(0.001, float(raw.get("precision_mm", 0.1)))
        except (TypeError, ValueError):
            out.precision_mm = 0.1
        out.currency = str(raw.get("currency") or "BRL")
        out.company_name = str(raw.get("company_name") or "")
        out.company_document = str(raw.get("company_document") or "")
        try:
            out.validity_days = max(0, int(raw.get("validity_days", 15)))
        except (TypeError, ValueError):
            out.validity_days = 15
        out.show_dimensions = bool(raw.get("show_dimensions", True))
        out.construction_notes = str(raw.get("construction_notes") or "")
        return out

    def to_display(self, millimetres: float) -> float:
        """Convert a millimetre value to the project's display unit."""
        if self.units == "cm":
            return millimetres / 10.0
        if self.units == "m":
            return millimetres / 1000.0
        return millimetres

    def unit_label(self) -> str:
        return {"mm": "mm", "cm": "cm", "m": "m"}.get(self.units, "mm")


@dataclass
class Project:
    name: str = "Projeto sem nome"
    code: str = ""
    client: str = ""
    client_contact: str = ""
    address: str = ""
    notes: str = ""
    modules: list[ModuleSpec] = field(default_factory=list)
    settings: ProjectSettings = field(default_factory=ProjectSettings)
    pricing: dict = field(default_factory=dict)
    cut: dict = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    #: Non-fatal problems found while loading (not written back to the file).
    load_warnings: list[str] = field(default_factory=list)

    # -- module management ---------------------------------------------------
    def module(self, module_id: str) -> ModuleSpec | None:
        for spec in self.modules:
            if spec.id == module_id:
                return spec
        return None

    def add_module(self, spec: ModuleSpec) -> ModuleSpec:
        if self.module(spec.id) is not None:
            raise ValueError(f"Módulo já existe: {spec.id}")
        if not spec.code.strip():
            spec.code = self.next_code(spec.type)
        if not spec.name.strip():
            spec.name = f"{MODULE_LABELS.get(spec.type, 'Módulo')} " \
                         f"{int(spec.width_mm)}"
        self.modules.append(spec)
        self.touch()
        return spec

    def update_module(self, spec: ModuleSpec) -> ModuleSpec:
        for index, current in enumerate(self.modules):
            if current.id == spec.id:
                spec.updated_at = now_iso()
                self.modules[index] = spec
                self.touch()
                return spec
        raise ValueError(f"Módulo não encontrado: {spec.id}")

    def remove_module(self, module_id: str) -> ModuleSpec | None:
        for index, spec in enumerate(self.modules):
            if spec.id == module_id:
                self.touch()
                return self.modules.pop(index)
        return None

    def move_module(self, module_id: str, delta: int) -> None:
        for index, spec in enumerate(self.modules):
            if spec.id != module_id:
                continue
            target = max(0, min(len(self.modules) - 1, index + delta))
            if target != index:
                self.modules.insert(target, self.modules.pop(index))
                self.touch()
            return

    def next_code(self, module_type: str) -> str:
        """Stable, human-friendly module code such as ``AI-01``."""
        prefixes = {
            "armario_inferior": "AI", "armario_superior": "AS",
            "torre": "TR", "guarda_roupa": "GR", "closet": "CL",
            "gaveteiro": "GV", "balcao": "BC", "nicho": "NI",
            "prateleira": "PR", "painel": "PN", "porta_abrir": "PA",
            "porta_correr": "PC", "bancada": "BT", "personalizado": "PM",
        }
        prefix = prefixes.get(module_type, "MOD")
        used = set()
        for spec in self.modules:
            if spec.code.upper().startswith(prefix + "-"):
                tail = spec.code.split("-", 1)[1]
                if tail.isdigit():
                    used.add(int(tail))
        number = 1
        while number in used:
            number += 1
        return f"{prefix}-{number:02d}"

    def touch(self) -> None:
        self.updated_at = now_iso()

    def total_width_mm(self) -> float:
        return sum(max(0.0, spec.width_mm) for spec in self.modules)

    def rooms(self) -> list[str]:
        seen: list[str] = []
        for spec in self.modules:
            room = spec.room.strip() or "Geral"
            if room not in seen:
                seen.append(room)
        return seen

    # -- serialization -------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "code": self.code,
            "client": self.client,
            "client_contact": self.client_contact,
            "address": self.address,
            "notes": self.notes,
            "modules": [spec.to_dict() for spec in self.modules],
            "settings": self.settings.to_dict(),
            "pricing": dict(self.pricing),
            "cut": dict(self.cut),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, raw, *, warnings: list[str] | None = None) -> "Project":
        raw = raw if isinstance(raw, dict) else {}
        warnings = warnings if warnings is not None else []
        project = cls(
            name=str(raw.get("name") or "Projeto sem nome"),
            code=str(raw.get("code") or ""),
            client=str(raw.get("client") or ""),
            client_contact=str(raw.get("client_contact") or ""),
            address=str(raw.get("address") or ""),
            notes=str(raw.get("notes") or ""),
            settings=ProjectSettings.from_dict(raw.get("settings")),
            pricing=dict(raw.get("pricing") or {}),
            cut=dict(raw.get("cut") or {}),
            created_at=str(raw.get("created_at") or now_iso()),
            updated_at=str(raw.get("updated_at") or now_iso()),
        )
        project.load_warnings = list(warnings)
        for entry in raw.get("modules") or []:
            try:
                project.modules.append(ModuleSpec.from_dict(entry))
            except Exception as exc:                     # noqa: BLE001
                project.load_warnings.append(
                    f"Módulo ignorado ao carregar: {exc}")
        return project

    # -- validation ----------------------------------------------------------
    def validate(self, libraries: dict | None = None,
                 limits: dict | None = None) -> ValidationReport:
        libraries = libraries or {}
        return validate_project(
            self.modules,
            materials=libraries.get("materials"),
            edge_bands=libraries.get("edge_bands"),
            hardware=libraries.get("hardware"),
            limits=limits,
        )

    # -- file payload ---------------------------------------------------------
    def document_payload(self) -> dict:
        """The value stored under ``scene.plugin_data[PLUGIN_KEY]``."""
        return {
            "schema": SCHEMA_VERSION,
            "plugin": PLUGIN_KEY,
            "plugin_version": PLUGIN_VERSION,
            "saved_at": now_iso(),
            "project": self.to_dict(),
        }

    @classmethod
    def from_document_payload(cls, raw: dict,
                              warnings: list[str] | None = None) -> "Project":
        raw = raw if isinstance(raw, dict) else {}
        return cls.from_dict(raw.get("project", raw), warnings=warnings)


def empty_project() -> Project:
    return Project()
