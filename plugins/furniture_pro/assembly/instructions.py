# SPDX-License-Identifier: GPL-3.0-or-later
"""Assembly instructions and sequence.

The generator returns ``BuildResult.assembly`` — bays, door hinge layouts and
hardware counts.  This module turns that into numbered instructions.  It is
deliberately conservative: it states what the model knows and asks the user
to confirm manufacturer drilling data rather than inventing it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.models import BuildResult


@dataclass
class AssemblyStep:
    number: int
    title: str
    detail: str = ""
    module_id: str = ""
    parts: list[str] = field(default_factory=list)
    hardware: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class AssemblyPlan:
    steps: list[AssemblyStep] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "warnings": list(self.warnings),
        }

    def as_text(self) -> str:
        lines = []
        for step in self.steps:
            lines.append(f"{step.number}. {step.title}")
            if step.detail:
                lines.append(f"   {step.detail}")
            if step.parts:
                lines.append(f"   Peças: {', '.join(step.parts)}")
            if step.hardware:
                lines.append(f"   Ferragens: {', '.join(step.hardware)}")
        return "\n".join(lines)


def build_assembly(results: list[BuildResult]) -> AssemblyPlan:
    plan = AssemblyPlan()
    number = 1
    for result in results:
        spec = result.spec
        assembly = result.assembly or {}
        label = spec.label
        plan.steps.append(AssemblyStep(
            number=number, title=f"Separar as peças de {label}",
            detail=f"{result.part_count} peça(s). Confira a lista de corte e "
                   "a identificação de cada chapa.",
            module_id=spec.id,
            parts=[p.name for p in result.panels[:20]],
        ))
        number += 1
        method = assembly.get("carcass_method", spec.carcass_method)
        plan.steps.append(AssemblyStep(
            number=number, title=f"Montar a caixa de {label}",
            detail=f"Método: {method}. Confirme a posição dos parafusos, "
                   "cavilhas ou minifix conforme o projeto executivo.",
            module_id=spec.id,
        ))
        number += 1
        if spec.back_method != "sem_fundo":
            plan.steps.append(AssemblyStep(
                number=number, title=f"Fixar o fundo de {label}",
                detail=f"Método: {spec.back_method}. Recuo configurado: "
                       f"{spec.back_recess_mm:g} mm.",
                module_id=spec.id,
                parts=["Fundo"],
            ))
            number += 1
        if assembly.get("has_plinth"):
            plan.steps.append(AssemblyStep(
                number=number, title=f"Montar rodapé e pés de {label}",
                detail=f"Rodapé de {assembly.get('plinth_height_mm', 0):g} mm "
                       f"com recuo de {spec.plinth_recess_mm:g} mm.",
                module_id=spec.id,
                hardware=["Pés niveladores"],
            ))
            number += 1
        if spec.divider_count or spec.shelf_count:
            plan.steps.append(AssemblyStep(
                number=number, title=f"Instalar divisórias e prateleiras de {label}",
                detail=f"{spec.divider_count} divisória(s) e "
                       f"{spec.shelf_count} prateleira(s) por baia.",
                module_id=spec.id,
            ))
            number += 1
        if spec.drawer_count:
            plan.steps.append(AssemblyStep(
                number=number, title=f"Montar e alinhar gavetas de {label}",
                detail="Use a altura de caixa e as folgas cadastradas; "
                       "confirme o comprimento da corrediça no catálogo.",
                module_id=spec.id,
                hardware=["Corrediças"],
            ))
            number += 1
        if spec.door_type == "hinged" and spec.door_count:
            plan.steps.append(AssemblyStep(
                number=number, title=f"Instalar portas de abrir de {label}",
                detail="As posições das dobradiças no relatório são de "
                       "layout. A furação do copo só deve ser feita com os "
                       "dados verificados do fabricante.",
                module_id=spec.id,
                hardware=["Dobradiças", "Puxadores"],
            ))
            number += 1
        elif spec.door_type == "sliding" and spec.door_count:
            plan.steps.append(AssemblyStep(
                number=number, title=f"Instalar portas de correr de {label}",
                detail="Confirme a altura das guias e o overlap das folhas.",
                module_id=spec.id,
                hardware=["Kit de correr", "Puxadores"],
            ))
            number += 1

    for result in results:
        for warning in result.warnings:
            plan.warnings.append(f"{result.spec.label}: {warning}")
    return plan
