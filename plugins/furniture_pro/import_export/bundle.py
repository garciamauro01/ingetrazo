# SPDX-License-Identifier: GPL-3.0-or-later
"""Project import/export: one folder with everything a shop needs.

The bundle is deliberately boring and self-describing: JSON for the data,
CSV for the machines and spreadsheets, SVG for drawings, PDF for the client.
A failure in one artefact is reported and does not abort the others.  DXF is
not emitted; see :mod:`..drawings.technical` for why.
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from ..core.errors import ExportError
from ..core.logging_utils import get_logger
from ..drawings import cut_plan_svg, module_front_svg, write_svg
from ..manufacturing.reports import (write_cut_plan_csv, write_json,
                                     write_parts_csv, write_pdf_report)
from ..persistence import load_project, save_project

logger = get_logger()

QUOTE_COLUMNS = ("Módulo", "Código", "Custo", "Venda", "Margem %", "Markup %")


def _quote_csv_text(quote) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(QUOTE_COLUMNS)
    for row in quote.modules:
        writer.writerow((row.name, row.code, f"{row.cost:.2f}",
                         f"{row.sale:.2f}", f"{row.margin * 100:.2f}",
                         f"{row.markup * 100:.2f}"))
    writer.writerow(())
    for label, value in quote.lines():
        writer.writerow((label, "", f"{value:.2f}", "", "", ""))
    return buffer.getvalue()


def export_bundle(directory, *, controller, include_pdf: bool = True,
                  include_previews: bool = True) -> dict:
    """Write ``directory`` and return ``{"files": [...], "warnings": [...]}``."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    files: list[str] = []
    warnings: list[str] = []
    project = controller.project

    def attempt(label, function):
        try:
            result = function()
            if result is not None:
                files.append(str(result))
        except Exception as exc:                        # noqa: BLE001
            logger.exception("bundle step failed: %s", label)
            warnings.append(f"{label}: {exc}")

    # Project data
    attempt("Projeto (.fproj)",
            lambda: (save_project(directory / "projeto.fproj", project),
                     directory / "projeto.fproj")[1])
    attempt("Projeto (JSON)",
            lambda: (write_json(directory / "projeto.json",
                                project.document_payload()),
                     directory / "projeto.json")[1])

    parts = controller.parts_list()
    attempt("Lista de peças (CSV)",
            lambda: (write_parts_csv(directory / "lista_de_pecas.csv", parts,
                                     controller.materials.materials),
                     directory / "lista_de_pecas.csv")[1])

    plan = None
    try:
        plan = controller.cut_plan()
    except Exception as exc:                            # noqa: BLE001
        warnings.append(f"Plano de corte: {exc}")

    if plan is not None:
        attempt("Plano de corte (CSV)",
                lambda: (write_cut_plan_csv(directory / "plano_de_corte.csv",
                                            plan),
                         directory / "plano_de_corte.csv")[1])
        attempt("Plano de corte (SVG)",
                lambda: (write_svg(directory / "plano_de_corte.svg",
                                   cut_plan_svg(plan)),
                         directory / "plano_de_corte.svg")[1])

    try:
        quote = controller.quote()
    except Exception as exc:                            # noqa: BLE001
        quote = None
        warnings.append(f"Orçamento: {exc}")
    if quote is not None:
        attempt("Orçamento (JSON)",
                lambda: (write_json(directory / "orcamento.json",
                                    quote.to_dict()),
                         directory / "orcamento.json")[1])
        attempt("Orçamento (CSV)",
                lambda: (directory.joinpath("orcamento.csv").write_text(
                    _quote_csv_text(quote), encoding="utf-8-sig"),
                    directory / "orcamento.csv")[1])

    # Technical drawings: one elevation per module.
    drawings = directory / "desenhos"
    drawing_names = {}
    for result in controller.results():
        spec = result.spec
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_"
                       for ch in (spec.code or spec.id))
        name = f"{safe}_elevacao.svg"
        drawing_names[result.spec.label] = name
        attempt(f"Desenho de {spec.label}",
                lambda result=result, name=name: (
                    write_svg(drawings / name,
                              module_front_svg(result.spec, result)),
                    drawings / name)[1])

    if include_previews:
        try:
            from ..rendering import save_module_png
            previews = directory / "previews"
            for result in controller.results():
                safe = "".join(ch if ch.isalnum() or ch in "-_" else "_"
                               for ch in (result.spec.code or result.spec.id))
                attempt(f"Prévia de {result.spec.label}",
                        lambda result=result, name=f"{safe}.png": (
                            save_module_png(previews / name, result,
                                            controller.materials.materials),
                            previews / name)[1])
        except Exception as exc:                        # noqa: BLE001
            warnings.append(f"Prévias: {exc}")

    if include_pdf:
        def make_pdf():
            write_pdf_report(
                directory / "relatorio.pdf", title=project.name or "Projeto",
                parts=parts, plan=plan, quote=quote,
                materials=controller.materials.materials,
                hardware=controller.hardware.items,
                drawing_svgs=drawing_names)
            return directory / "relatorio.pdf"

        attempt("Relatório (PDF)", make_pdf)

    return {"files": files, "warnings": warnings,
            "directory": str(directory)}


def import_project_file(path, *, controller,
                        replace_scene: bool = True):
    """Load a ``.fproj``/JSON project through the controller."""
    project = load_project(path)
    if str(path).lower().endswith(".json"):
        # A plain JSON may be a raw project or a full envelope; load_project
        # already migrates both, so nothing else is needed here.
        pass
    controller.apply_project(project, replace_scene=replace_scene)
    return project


def export_project_json(path, project) -> None:
    payload = project.document_payload()
    write_json(path, payload)


def read_json(path) -> dict:
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ExportError(f"Não foi possível ler {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ExportError(f"Arquivo inválido: {path}")
    return data
