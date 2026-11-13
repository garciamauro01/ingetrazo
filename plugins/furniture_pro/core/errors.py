# SPDX-License-Identifier: GPL-3.0-or-later
"""Exceptions used across Furniture Pro.

Every user-facing operation raises one of these instead of leaking a raw
``KeyError`` or Qt error into the Ingetrazo event loop.  The UI catches them
and shows a readable message; the command layer logs the traceback.
"""
from __future__ import annotations


class FurnitureError(Exception):
    """Base class for recoverable Furniture Pro failures."""

    user_message = "Não foi possível concluir a operação."

    def __init__(self, message: str | None = None, *, details: str = "",
                 warnings: list[str] | None = None) -> None:
        self.user_message = message or self.user_message
        self.details = details or ""
        self.warnings = list(warnings or [])
        super().__init__(self.user_message)


class ValidationError(FurnitureError):
    """Invalid parameters; nothing was written to the document."""

    user_message = "Os parâmetros informados são inválidos."

    def __init__(self, problems, *, module_name: str = "") -> None:
        if isinstance(problems, str):
            problems = [problems]
        self.problems = [str(p) for p in (problems or [])]
        prefix = f"{module_name}: " if module_name else ""
        super().__init__(prefix + "; ".join(self.problems) if self.problems
                         else self.user_message)


class DataError(FurnitureError):
    """A stored project/catalogue cannot be read or is from a broken version."""

    user_message = "Os dados do Furniture Pro estão inválidos ou incompletos."


class ExportError(FurnitureError):
    """A report or data file could not be written."""

    user_message = "Não foi possível gerar o arquivo solicitado."


class GeometryError(FurnitureError):
    """The host refused or could not represent the generated geometry."""

    user_message = "A geometria do móvel não pôde ser criada no modelo."


class OptimizerError(FurnitureError):
    """The cutting optimiser received impossible constraints."""

    user_message = "As restrições do plano de corte são incompatíveis."
