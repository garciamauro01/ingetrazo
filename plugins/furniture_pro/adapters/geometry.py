# SPDX-License-Identifier: GPL-3.0-or-later
"""Geometry adapter: turns domain panels into Ingetrazo groups and meshes.

This is the only layer that knows about metres, ``QVector3D`` and
``Group``.  All domain values stay in millimetres; the conversion happens at
the boundary in :func:`box_mesh`.

A module is one parent ``Group`` whose ``ext`` carries the serialized
``ModuleSpec``.  Its panels are child groups, so the module moves and selects
as one object while each board keeps its own material and metadata.  Panel
boxes are built in module-local coordinates; the parent's ``xform`` places
(and optionally rotates) the module in the world.
"""
from __future__ import annotations

from pathlib import Path

from ..core.constants import PLUGIN_KEY
from ..core.models import BuildResult, Material, ModuleSpec, Panel

MM = 0.001


def _attrs_for(material: Material | None) -> dict:
    if material is None:
        return {"color": (0.92, 0.90, 0.84)}
    attrs: dict = {"color": material.rgb()}
    if material.texture_path and Path(material.texture_path).is_file():
        attrs["texture"] = {"path": str(material.texture_path),
                            "sw": 1.0, "sh": 1.0}
    return attrs


def _add_box(mesh, position_mm, size_mm, attrs: dict) -> None:
    """Append the six faces of an axis-aligned box, in metres."""
    from PySide6.QtGui import QVector3D

    ox, oy, oz = (float(v) * MM for v in position_mm)
    sx, sy, sz = (float(v) * MM for v in size_mm)
    if sx <= 0 or sy <= 0 or sz <= 0:
        return
    p0 = QVector3D(ox, oy, oz)
    p1 = QVector3D(ox + sx, oy, oz)
    p2 = QVector3D(ox + sx, oy + sy, oz)
    p3 = QVector3D(ox, oy + sy, oz)
    p4 = QVector3D(ox, oy, oz + sz)
    p5 = QVector3D(ox + sx, oy, oz + sz)
    p6 = QVector3D(ox + sx, oy + sy, oz + sz)
    p7 = QVector3D(ox, oy + sy, oz + sz)
    loops = (
        (p0, p3, p2, p1),   # bottom (-Z)
        (p4, p5, p6, p7),   # top (+Z)
        (p0, p1, p5, p4),   # front (-Y)
        (p2, p3, p7, p6),   # back (+Y)
        (p0, p4, p7, p3),   # left (-X)
        (p1, p2, p6, p5),   # right (+X)
    )
    for loop in loops:
        face = mesh.add_face(list(loop))
        face.attrs.update(attrs)


def panel_mesh(panel: Panel, material: Material | None = None):
    """Build a fresh ``Mesh`` for one physical panel."""
    from core.mesh import Mesh

    mesh = Mesh()
    _add_box(mesh, panel.position_mm, panel.size_mm, _attrs_for(material))
    return mesh


def panel_group(panel: Panel, material: Material | None = None):
    """A child ``Group`` carrying one panel and its shop-floor metadata."""
    from core.group import Group

    group = Group(panel_mesh(panel, material),
                  name=f"{panel.code} · {panel.name}")
    group.ext = {PLUGIN_KEY: {"kind": "panel", "schema": 1,
                              "panel": panel.to_dict()}}
    return group


def _module_transform(spec: ModuleSpec):
    """Parent transform placing the module at ``origin_mm`` and turning it."""
    from PySide6.QtGui import QMatrix4x4, QVector3D

    matrix = QMatrix4x4()
    matrix.translate(QVector3D(float(spec.origin_mm[0]) * MM,
                               float(spec.origin_mm[1]) * MM,
                               float(spec.origin_mm[2]) * MM))
    if abs(float(spec.rotation_z_deg)) > 1e-9:
        matrix.rotate(float(spec.rotation_z_deg), 0.0, 0.0, 1.0)
    return matrix


def build_module_group(result: BuildResult,
                       materials: dict[str, Material] | None = None,
                       *, layer: str = "Furniture Pro"):
    """Create the parent group with every panel as a child group."""
    from core.group import Group
    from core.mesh import Mesh

    materials = materials or {}
    spec = result.spec
    label = f"{spec.code} · {spec.label}" if spec.code else spec.label
    master = Group(Mesh(), name=label)
    master.layer = layer
    children = []
    for panel in result.panels:
        material = materials.get(panel.material_id)
        group = panel_group(panel, material)
        group.layer = layer
        children.append(group)
    if children:
        master.adopt(children)
        # ``adopt`` installs an identity matrix; replace it with the module's
        # placement so the panels can stay in module-local coordinates.
        if spec.origin_mm != (0.0, 0.0, 0.0) or abs(spec.rotation_z_deg) > 1e-9:
            master.xform = _module_transform(spec)
    master.ext = {
        PLUGIN_KEY: {
            "kind": "module",
            "schema": 1,
            "spec": spec.to_dict(),
            "summary": {
                "panels": len(result.panels),
                "parts": result.part_count,
                "warnings": len(result.warnings),
            },
        }
    }
    return master


def spec_from_group(group) -> ModuleSpec | None:
    """Read the stored specification of a module group, or ``None``."""
    ext = getattr(group, "ext", None) or {}
    entry = ext.get(PLUGIN_KEY) if isinstance(ext, dict) else None
    if not isinstance(entry, dict) or entry.get("kind") != "module":
        return None
    raw = entry.get("spec")
    if not isinstance(raw, dict):
        return None
    try:
        return ModuleSpec.from_dict(raw)
    except Exception:                                   # noqa: BLE001
        return None


def iter_module_groups(scene):
    """Yield ``(group, spec)`` for every Furniture Pro module in the scene."""
    for group in list(getattr(scene, "groups", []) or []):
        spec = spec_from_group(group)
        if spec is not None:
            yield group, spec


def find_module_group(scene, module_id: str):
    for group, spec in iter_module_groups(scene):
        if spec.id == module_id:
            return group
    return None
