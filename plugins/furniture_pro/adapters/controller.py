# SPDX-License-Identifier: GPL-3.0-or-later
"""Application controller: the bridge between the domain and the host.

The UI talks only to this class.  Everything host-specific (document data,
geometry groups, undo history, material registry) is isolated here and in
:mod:`.geometry` / :mod:`.commands`, so the same controller runs headless in
tests with ``app=None``.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from ..assembly import build_assembly
from ..core.constants import DEFAULT_LIMITS
from ..core.diagnostics import environment_report
from ..core.errors import FurnitureError, ValidationError
from ..core.logging_utils import get_logger, user_data_dir
from ..core.models import BuildResult, ModuleSpec
from ..core.project import Project
from ..core.validation import ValidationReport
from ..furniture.generator import build_module
from ..hardware import HardwareLibrary
from ..manufacturing import (CutSettings, build_parts_list, optimize,
                             plan_from_dict)
from ..materials import MaterialLibrary
from ..pricing import PricingSettings, calculate_quote
from .commands import GroupsEditCommand
from .geometry import build_module_group, iter_module_groups, spec_from_group

logger = get_logger()


class FurnitureController:
    """Owns the project, libraries and derived manufacturing results."""

    def __init__(self, app=None, data_dir=None) -> None:
        self.app = app
        self.data_dir = Path(data_dir) if data_dir else user_data_dir()
        self.materials = MaterialLibrary.load(self.data_dir / "materials.json")
        self.hardware = HardwareLibrary.load(self.data_dir / "hardware.json")
        self.project = Project()
        self._results: dict[str, BuildResult] = {}
        self._result_keys: dict[str, str] = {}
        self.errors: dict[str, str] = {}
        self._cut_plan = None
        self._cut_key = None
        self._quote = None
        self._quote_key = None
        self.reload(keep_libraries=True)

    # ------------------------------------------------------------------
    # Document data
    # ------------------------------------------------------------------
    @property
    def scene(self):
        if self.app is None:
            return None
        try:
            return self.app.scene
        except Exception:                               # noqa: BLE001
            return None

    @property
    def viewport(self):
        if self.app is None:
            return None
        try:
            return self.app.viewport
        except Exception:                               # noqa: BLE001
            return None

    def document_data(self):
        if self.app is None:
            return None
        try:
            return self.app.document_data()
        except Exception:                               # noqa: BLE001
            logger.exception("could not read document data")
            return None

    def reload(self, *, keep_libraries: bool = False) -> Project:
        """Reload the project from the host document (or start empty)."""
        raw = self.document_data()
        if raw is None:
            project = Project()
        else:
            try:
                from ..persistence import project_from_payload
                project = project_from_payload(raw)
            except Exception as exc:                    # noqa: BLE001
                logger.exception("invalid project data in document")
                project = Project()
                project.load_warnings.append(
                    f"Não foi possível ler os dados do documento: {exc}")
        self.project = project
        self._normalise_project()
        self.invalidate()
        return project

    def _normalise_project(self) -> None:
        try:
            self.project.cut = CutSettings.from_dict(self.project.cut).to_dict()
        except Exception:                               # noqa: BLE001
            self.project.cut = CutSettings().to_dict()
        try:
            pricing = PricingSettings.from_dict(self.project.pricing)
            if not self.project.pricing:
                pricing.currency = self.project.settings.currency
            self.project.pricing = pricing.to_dict()
        except Exception:                               # noqa: BLE001
            self.project.pricing = PricingSettings().to_dict()

    def document_payload(self) -> dict:
        return self.project.document_payload()

    def store_project(self) -> None:
        """Persist non-geometric project changes as one undo step."""
        if self.app is None:
            return
        try:
            self.app.set_document_data(self.document_payload())
            self._notify()
        except Exception as exc:                        # noqa: BLE001
            logger.exception("could not store project data")
            raise FurnitureError("Não foi possível salvar os dados do projeto "
                                 "no documento.", details=str(exc)) from exc

    def _notify(self) -> None:
        vp = self.viewport
        if vp is not None:
            notify = getattr(vp, "notify_scene_changed", None)
            if callable(notify):
                try:
                    notify()
                except Exception:                       # noqa: BLE001
                    logger.exception("notify_scene_changed failed")
            update = getattr(vp, "update", None)
            if callable(update):
                update()

    def _execute(self, command) -> None:
        if self.app is None:
            return
        vp = self.viewport
        if vp is None:
            raise FurnitureError("A janela do Ingetrazo não está disponível.")
        vp.history.execute(command)
        self._notify()

    # ------------------------------------------------------------------
    # Libraries
    # ------------------------------------------------------------------
    def libraries(self) -> dict:
        return {"materials": self.materials.materials,
                "edge_bands": self.materials.edge_bands,
                "hardware": self.hardware.items}

    def save_libraries(self) -> None:
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.materials.save(self.data_dir / "materials.json")
            self.hardware.save(self.data_dir / "hardware.json")
        except Exception as exc:                        # noqa: BLE001
            raise FurnitureError("Não foi possível gravar as bibliotecas.",
                                 details=str(exc)) from exc

    def reload_libraries(self) -> None:
        self.materials = MaterialLibrary.load(self.data_dir / "materials.json")
        self.hardware = HardwareLibrary.load(self.data_dir / "hardware.json")
        self.invalidate()

    # ------------------------------------------------------------------
    # Building
    # ------------------------------------------------------------------
    def limits(self) -> dict:
        return copy.deepcopy(DEFAULT_LIMITS)

    def build(self, spec: ModuleSpec, *, strict: bool = True) -> BuildResult:
        key = json.dumps(spec.to_dict(), sort_keys=True, default=str)
        cached = self._results.get(spec.id)
        if cached is not None and self._result_keys.get(spec.id) == key:
            return cached
        try:
            result = build_module(spec, self.materials.materials,
                                  self.materials.edge_bands, self.limits())
        except FurnitureError as exc:
            self.errors[spec.id] = exc.user_message
            if strict:
                raise
            result = BuildResult(spec=spec, warnings=[exc.user_message],
                                 assembly={"error": exc.user_message})
            self._results[spec.id] = result
            self._result_keys[spec.id] = key
            return result
        except Exception as exc:                        # noqa: BLE001
            logger.exception("unexpected build failure for %s", spec.id)
            self.errors[spec.id] = str(exc)
            if strict:
                raise FurnitureError(
                    "Falha inesperada ao gerar o módulo.",
                    details=str(exc)) from exc
            result = BuildResult(spec=spec, warnings=[str(exc)])
            self._results[spec.id] = result
            self._result_keys[spec.id] = key
            return result
        self.errors.pop(spec.id, None)
        self._results[spec.id] = result
        self._result_keys[spec.id] = key
        return result

    def results(self, *, strict: bool = False) -> list[BuildResult]:
        out = []
        for spec in self.project.modules:
            try:
                out.append(self.build(spec, strict=strict))
            except FurnitureError:
                continue
        return out

    def invalidate(self) -> None:
        self._results.clear()
        self._result_keys.clear()
        self._cut_plan = None
        self._cut_key = None
        self._quote = None
        self._quote_key = None
        self.errors.clear()

    # ------------------------------------------------------------------
    # Module operations
    # ------------------------------------------------------------------
    def group_for(self, module_id: str):
        scene = self.scene
        if scene is None:
            return None
        for group, spec in iter_module_groups(scene):
            if spec.id == module_id:
                return group
        return None

    def insert_module(self, spec: ModuleSpec, *, select: bool = True,
                      at=None) -> BuildResult:
        spec.raise_if_invalid(self.limits())
        if self.project.module(spec.id) is not None:
            raise ValidationError(["Já existe um módulo com este identificador."],
                                  module_name=spec.label)
        if at is not None:
            spec.origin_mm = (float(at[0]), float(at[1]), float(at[2]))
        before_project = self.project.to_dict()
        before_data = self.document_data()
        result = self.build(spec, strict=True)
        self.project.add_module(spec)
        group = build_module_group(result, self.materials.materials)
        self._register_host_materials()
        try:
            self._execute(GroupsEditCommand(
                added=[group], before_data=before_data,
                after_data=self.document_payload(),
                description="Inserir módulo Furniture Pro"))
        except Exception:
            self.project = Project.from_dict(before_project)
            self._results.pop(spec.id, None)
            raise
        if select and self.scene is not None:
            self.scene.selection.clear()
            self.scene.selection.add(group)
            self._notify()
        logger.info("module inserted: %s (%s)", spec.code, spec.id)
        return result

    def update_module(self, spec: ModuleSpec) -> BuildResult:
        spec.raise_if_invalid(self.limits())
        current = self.project.module(spec.id)
        if current is None:
            return self.insert_module(spec)
        before_project = self.project.to_dict()
        before_data = self.document_data()
        result = self.build(spec, strict=True)
        old_group = self.group_for(spec.id)
        new_group = build_module_group(result, self.materials.materials)
        self._register_host_materials()
        self.project.update_module(spec)
        try:
            self._execute(GroupsEditCommand(
                added=[new_group], removed=[old_group] if old_group else [],
                before_data=before_data, after_data=self.document_payload(),
                description="Editar módulo Furniture Pro"))
        except Exception:
            self.project = Project.from_dict(before_project)
            self.invalidate()
            raise
        if old_group is not None and self.scene is not None:
            self.scene.selection.discard(old_group)
            self.scene.selection.add(new_group)
            self._notify()
        logger.info("module updated: %s (%s)", spec.code, spec.id)
        return result

    def delete_module(self, module_id: str) -> bool:
        spec = self.project.module(module_id)
        if spec is None:
            return False
        before_project = self.project.to_dict()
        before_data = self.document_data()
        group = self.group_for(module_id)
        self.project.remove_module(module_id)
        try:
            self._execute(GroupsEditCommand(
                removed=[group] if group else [], before_data=before_data,
                after_data=self.document_payload(),
                description="Excluir módulo Furniture Pro"))
        except Exception:
            self.project = Project.from_dict(before_project)
            raise
        self._results.pop(module_id, None)
        self._result_keys.pop(module_id, None)
        self.invalidate()
        return True

    def duplicate_module(self, module_id: str) -> ModuleSpec | None:
        spec = self.project.module(module_id)
        if spec is None:
            return None
        clone = spec.copy(new_identity=True)
        clone.code = self.project.next_code(clone.type)
        clone.origin_mm = (spec.origin_mm[0] + spec.width_mm,
                           spec.origin_mm[1], spec.origin_mm[2])
        self.insert_module(clone)
        return clone

    def selected_specs(self) -> list[ModuleSpec]:
        scene = self.scene
        if scene is None:
            return []
        out = []
        for item in list(getattr(scene, "selection", []) or []):
            spec = spec_from_group(item)
            if spec is not None:
                out.append(spec)
        return out

    def restore_missing_geometry(self) -> int:
        """Create groups for modules stored in the document but not in the scene."""
        scene = self.scene
        if scene is None:
            return 0
        existing = {spec.id for _g, spec in iter_module_groups(scene)}
        missing = [s for s in self.project.modules if s.id not in existing]
        if not missing:
            return 0
        before_data = self.document_data()
        groups = []
        for spec in missing:
            result = self.build(spec, strict=False)
            if result.panels:
                groups.append(build_module_group(result, self.materials.materials))
        if not groups:
            return 0
        self._execute(GroupsEditCommand(
            added=groups, before_data=before_data,
            after_data=self.document_payload(),
            description="Recriar geometria Furniture Pro"))
        return len(groups)

    def _register_host_materials(self) -> None:
        scene = self.scene
        if scene is None:
            return
        try:
            from core.materials import Material as HostMaterial
            from core.materials import register
            registry = getattr(scene, "materials", None)
            if not isinstance(registry, dict):
                return
            for material in self.materials.materials.values():
                host = HostMaterial(name=material.name,
                                    color=material.rgb(),
                                    opacity=None,
                                    finish=None)
                register(registry, host)
        except Exception:                               # noqa: BLE001
            logger.exception("could not register host materials")

    # ------------------------------------------------------------------
    # Manufacturing and pricing
    # ------------------------------------------------------------------
    def parts_list(self):
        return build_parts_list(self.results(), self.materials.materials)

    def cut_settings(self) -> CutSettings:
        return CutSettings.from_dict(self.project.cut)

    def cut_plan(self, *, force: bool = False):
        parts = self.parts_list()
        settings = self.cut_settings()
        key = (tuple((p.material_id, p.thickness_mm, round(p.length_mm, 2),
                      round(p.width_mm, 2), p.qty, p.grain,
                      tuple(p.edges.values())) for p in parts.items),
               json.dumps(settings.to_dict(), sort_keys=True))
        if not force and self._cut_plan is not None and key == self._cut_key:
            return self._cut_plan
        try:
            plan = optimize(parts.items, self.materials.materials, settings)
        except FurnitureError:
            raise
        except Exception as exc:                        # noqa: BLE001
            logger.exception("cutting optimizer failed")
            raise FurnitureError("Não foi possível calcular o plano de corte.",
                                 details=str(exc)) from exc
        self._cut_plan = plan
        self._cut_key = key
        return plan

    def set_cut_plan(self, plan) -> None:
        self._cut_plan = plan
        self._cut_key = None

    def set_cut_settings(self, settings: CutSettings) -> None:
        self.project.cut = settings.to_dict()
        self._cut_plan = None
        self._cut_key = None
        self._quote = None
        self._quote_key = None

    def set_pricing_settings(self, settings: PricingSettings) -> None:
        self.project.pricing = settings.to_dict()
        self._quote = None
        self._quote_key = None

    def pricing_settings(self) -> PricingSettings:
        return PricingSettings.from_dict(self.project.pricing)

    def quote(self, *, force: bool = False):
        settings = self.pricing_settings()
        key = (json.dumps(settings.to_dict(), sort_keys=True),
               tuple(self._result_keys.items()),
               len(self.project.modules))
        if not force and self._quote is not None and key == self._quote_key:
            return self._quote
        plan = None
        try:
            plan = self.cut_plan()
        except FurnitureError as exc:
            logger.warning("quote without cut plan: %s", exc)
        quote = calculate_quote(
            self.results(), self.materials.materials,
            self.materials.edge_bands, self.hardware.items, settings,
            cut_plan=plan, project_name=self.project.name)
        self._quote = quote
        self._quote_key = key
        return quote

    def assembly(self):
        return build_assembly(self.results())

    def validation(self) -> ValidationReport:
        report = self.project.validate(self.libraries(), self.limits())
        for module_id, error in self.errors.items():
            report.errors.append(f"Módulo {module_id}: {error}")
        return report

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def save_project(self, path) -> None:
        from ..persistence import save_project
        save_project(path, self.project)

    def load_project(self, path, *, replace_scene: bool = True) -> Project:
        from ..persistence import load_project
        project = load_project(path)
        self.apply_project(project, replace_scene=replace_scene)
        return project

    def apply_project(self, project: Project, *,
                      replace_scene: bool = True) -> None:
        """Make ``project`` current and (optionally) rebuild its geometry."""
        project.load_warnings = list(project.load_warnings)
        self.project = project
        self._normalise_project()
        self.invalidate()
        scene = self.scene
        if scene is None:
            return
        existing: list = []
        existing_ids: set[str] = set()
        if replace_scene:
            for group, spec in iter_module_groups(scene):
                existing.append(group)
                existing_ids.add(spec.id)
        groups = []
        for spec in project.modules:
            if spec.id in existing_ids:
                continue
            result = self.build(spec, strict=False)
            if result.panels:
                groups.append(build_module_group(result, self.materials.materials))
        before_data = self.document_data()
        self._execute(GroupsEditCommand(
            added=groups, removed=existing, before_data=before_data,
            after_data=self.document_payload(),
            description="Abrir projeto Furniture Pro"))

    def restore_persisted_plan(self, raw) -> None:
        try:
            self.set_cut_plan(plan_from_dict(raw))
        except Exception:                               # noqa: BLE001
            logger.exception("invalid persisted cut plan ignored")

    # ------------------------------------------------------------------
    # Exports and diagnostics
    # ------------------------------------------------------------------
    def export_bundle(self, directory, *, include_pdf: bool = True) -> dict:
        from ..import_export import export_bundle
        return export_bundle(directory, controller=self, include_pdf=include_pdf)

    def environment_report(self) -> str:
        return environment_report(self.app, {
            "materiais": self.materials.materials,
            "fitas": self.materials.edge_bands,
            "ferragens": self.hardware.items,
        }, project=self.project)
