# SPDX-License-Identifier: GPL-3.0-or-later
"""Cross-object validation.

``ModuleSpec.validate`` checks one module in isolation.  This module checks
the things only the project knows: duplicate identifiers, missing catalogue
entries, a door/drawer combination that leaves no useful front, prices that
would make a quote silently incomplete, and so on.  UI and persistence call
it before writing, so a broken project never reaches the document.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .models import EdgeBand, Material, ModuleSpec


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def extend(self, other: "ValidationReport") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)

    def as_text(self) -> str:
        lines: list[str] = []
        if self.errors:
            lines.append("Erros:")
            lines.extend(f"- {e}" for e in self.errors)
        if self.warnings:
            lines.append("Avisos:")
            lines.extend(f"- {w}" for w in self.warnings)
        return "\n".join(lines) or "Nenhum problema encontrado."


def validate_project(
    modules: list[ModuleSpec],
    materials: dict[str, Material] | None = None,
    edge_bands: dict[str, EdgeBand] | None = None,
    hardware: dict | None = None,
    limits: dict | None = None,
) -> ValidationReport:
    """Validate every module and the project's references to the library."""
    report = ValidationReport()
    materials = materials or {}
    edge_bands = edge_bands or {}
    hardware = hardware or {}

    seen_ids: dict[str, int] = {}
    seen_codes: dict[str, int] = {}
    for index, spec in enumerate(modules, start=1):
        label = f"Módulo {index} ({spec.label})"
        seen_ids[spec.id] = seen_ids.get(spec.id, 0) + 1
        if spec.code.strip():
            key = spec.code.strip().lower()
            seen_codes[key] = seen_codes.get(key, 0) + 1

        for problem in spec.validate(limits):
            report.errors.append(f"{label}: {problem}")

        for role, mat_id in (("estrutura", spec.material_id),
                             ("frentes", spec.material_for_front()),
                             ("fundo", spec.material_for_back())):
            if not mat_id:
                report.errors.append(f"{label}: material de {role} não informado.")
            elif mat_id not in materials:
                report.errors.append(
                    f"{label}: material de {role} não cadastrado ({mat_id}).")
            else:
                mat = materials[mat_id]
                if not mat.availability:
                    report.warnings.append(
                        f"{label}: material indisponível ({mat.name}).")
                if mat.cost_per_sheet <= 0 and mat.cost_per_m2 <= 0:
                    report.warnings.append(
                        f"{label}: material sem preço ({mat.name}).")

        for role, band_id in (("estrutura", spec.edge_band_id),
                              ("frentes", spec.edge_for_front()),
                              ("fundo", spec.edge_for_back())):
            if band_id and band_id not in edge_bands:
                report.warnings.append(
                    f"{label}: fita de borda de {role} não cadastrada "
                    f"({band_id}).")

        if spec.hardware:
            for hw_id in spec.hardware:
                if hw_id not in hardware:
                    report.warnings.append(
                        f"{label}: ferragem não cadastrada ({hw_id}).")

        # A door split into more pieces than the width can carry is already
        # caught by ModuleSpec; here we catch the front stack itself.
        if spec.drawer_count and spec.door_type != "none":
            if spec.drawer_position == "bottom":
                if spec.drawer_count * max(1.0, spec.drawer_front_height_mm) > \
                        spec.height_mm * 0.9:
                    report.warnings.append(
                        f"{label}: gavetas ocupam quase toda a altura; "
                        "confira o espaço restante para as portas.")
            else:
                if spec.drawer_count * max(1.0, spec.drawer_front_height_mm) > \
                        spec.height_mm * 0.9:
                    report.warnings.append(
                        f"{label}: gavetas no topo ocupam quase toda a altura.")

        if spec.door_type == "sliding" and spec.depth_mm < 350:
            report.warnings.append(
                f"{label}: profundidade reduzida para portas de correr; "
                "confirme o espaço das guias.")

    for module_id, count in seen_ids.items():
        if count > 1:
            report.errors.append(
                f"Identificador de módulo repetido: {module_id} ({count}×).")
    for code, count in seen_codes.items():
        if count > 1:
            report.errors.append(f"Código de módulo repetido: {code} ({count}×).")

    return report
