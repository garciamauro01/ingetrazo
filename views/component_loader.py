# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez and IngeTrazo contributors.
"""Read a user's component file as one Group, standing up and at its size.

The online catalogue knows how to read each of its models because it declares
the unit, the vertical and the size. A file the user brings declares none of
that, so the import asks once — unit and vertical — and this module turns the
answer into a matrix that is stored with the entry. Insertion then reads the
file with that matrix, which is what keeps a centimetre OBJ, a Y-up DAE and a
metre IGZ arriving the same way up.

The geometry never touches the live scene: a throwaway :class:`~core.scene.Scene`
receives it, the result is flattened into one classic Group in world
coordinates (so thumbnails and shared definitions both behave) and the caller
decides whether to place it.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QMatrix4x4

from core import user_library
from core.group import Group, iter_placements, transformed_mesh, world_mesh
from core.mesh import Mesh
from core.scene import Scene


class ComponentLoadError(Exception):
    """The file could not be read as a component, with a reason for the user."""


class Loaded:
    """A model ready to place, plus what the importer needs to record."""

    def __init__(self, group: Group, path: Path) -> None:
        self.group = group
        self.path = path

    @property
    def size_cm(self) -> tuple[float, float, float]:
        return size_cm(self.group)


#: What an OBJ unit is worth in metres. Kept in step with formats.obj.
_UNITS = {"m": 1.0, "cm": 0.01, "mm": 0.001, "in": 0.0254, "ft": 0.3048}

_IDENTITY = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)


def matrix_for(unit: str = "m", y_up: bool = False) -> tuple:
    """The 3x3 (row-major) that puts a file in metres, Z-up, as this app
    expects it. ``y_up`` turns the file a quarter about X; the scale is the
    unit the importer was told."""
    scale = _UNITS.get(str(unit).lower(), 1.0)
    base = _IDENTITY
    if y_up:
        from formats.obj import Y_UP_TO_Z_UP
        base = Y_UP_TO_Z_UP
    return tuple(float(base[i]) * scale for i in range(9))


def _qmatrix(m3) -> QMatrix4x4:
    m = [float(v) for v in m3]
    return QMatrix4x4(m[0], m[1], m[2], 0.0,
                      m[3], m[4], m[5], 0.0,
                      m[6], m[7], m[8], 0.0,
                      0.0, 0.0, 0.0, 1.0)


def _scene_group(temp: Scene, name: str) -> Group:
    """The loaded scene as ONE group. A file written as parts keeps them as
    nested placements; a multi-group document becomes a container."""
    groups = [g for g in (getattr(temp, "groups", None) or []) if g is not None]
    loose = getattr(temp, "mesh", None)
    if len(groups) == 1 and not (loose is not None and loose.faces):
        return groups[0]
    if not groups:
        return Group(loose if loose is not None else Mesh(), name=name)
    root = Group(loose if loose is not None else Mesh(), name=name)
    for g in groups:
        if g.xform is None:
            g.xform = QMatrix4x4()      # a classic group becomes a placement
            g.component = False
    root.adopt(groups)
    return root


def load_group(path, *, matrix=None, name: str | None = None) -> Group:
    """Read ``path`` into one Group. ``matrix`` is the row-major 3x3 the
    importer chose (unit + vertical); it is applied to every format, so the
    caller never has to know which loaders take one and which do not."""
    p = Path(path)
    if not p.is_file():
        raise ComponentLoadError(f"file not found: {p}")
    suffix = p.suffix.lower()
    temp = Scene()
    try:
        if suffix == ".obj":
            from formats import obj as obj_format
            obj_format.load_obj(temp, p, matrix=matrix)
        elif suffix == ".glb":
            from formats.glb import load_glb
            load_glb(temp, p)
        elif suffix == ".dae":
            from formats.dae import load_dae
            load_dae(temp, p)
        elif suffix == ".stl":
            from formats.stl import load_stl
            # STL has no unit of its own; matrix carries the scale.
            load_stl(temp, p)
        elif suffix == ".skp":
            from formats.skp import load_skp
            load_skp(temp, p)
        elif suffix == ".igz":
            from formats.igz import load_into
            load_into(temp, p)
        else:
            raise ComponentLoadError(
                f"unsupported model format: {p.suffix}")
    except ComponentLoadError:
        raise
    except Exception as exc:  # noqa: BLE001 - a bad file is a message, not a crash
        raise ComponentLoadError(str(exc)) from exc

    group = _scene_group(temp, name or p.stem)
    if not group.mesh.faces and not group.children:
        raise ComponentLoadError("the file has no geometry")

    # OBJ took the matrix above; the others are turned/scaled after reading.
    if suffix != ".obj" and matrix is not None:
        group = _bake(group, matrix)
    return group


def _bake(group: Group, matrix) -> Group:
    mesh = transformed_mesh(world_mesh(group), _qmatrix(matrix))
    return Group(mesh, name=getattr(group, "name", ""))


def bounds(group: Group):
    """``(lo, hi)`` in world metres, over the vertices the faces use."""
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    for g, m in iter_placements(group):
        mesh = getattr(g, "mesh", None)
        if mesh is None:
            continue
        for v in mesh.vertices:
            p = v.position
            if m is not None:
                p = m.map(p)
            for k in range(3):
                c = (p.x(), p.y(), p.z())[k]
                lo[k] = min(lo[k], c)
                hi[k] = max(hi[k], c)
    return lo, hi


def size_cm(group: Group) -> tuple[float, float, float]:
    lo, hi = bounds(group)
    if lo[0] == float("inf"):
        return (0.0, 0.0, 0.0)
    return tuple(round((hi[k] - lo[k]) * 100.0, 2) for k in range(3))


def fit(group: Group, cm=None, anchor: str = "base") -> Group:
    """Scale ``group`` to ``cm`` (width, depth, height) when given, and put
    its anchor at the origin: ``base`` centres X/Y and rests the model on
    Z=0, which is where the placement tool's cursor sits."""
    lo, hi = bounds(group)
    if lo[0] == float("inf"):
        return group
    scale = [1.0, 1.0, 1.0]
    if cm:
        try:
            want = [max(0.0, float(v)) / 100.0 for v in cm[:3]]
        except (TypeError, ValueError):
            want = [0.0, 0.0, 0.0]
        ext = [hi[k] - lo[k] for k in range(3)]
        usable = [want[k] > 0.0 and ext[k] > 1e-9 for k in range(3)]
        good = [want[k] / ext[k] for k in range(3) if usable[k]]
        fallback = sum(good) / len(good) if good else 1.0
        for k in range(3):
            scale[k] = want[k] / ext[k] if usable[k] else fallback

    slo = [lo[k] * scale[k] for k in range(3)]
    shi = [hi[k] * scale[k] for k in range(3)]
    tx = ty = tz = 0.0
    if anchor in ("base", "center"):
        tx = -(slo[0] + shi[0]) / 2.0
        ty = -(slo[1] + shi[1]) / 2.0
    if anchor == "base":
        tz = -slo[2]
    elif anchor == "center":
        tz = -(slo[2] + shi[2]) / 2.0

    if all(abs(v - 1.0) < 1e-12 for v in scale) and \
            abs(tx) + abs(ty) + abs(tz) < 1e-12:
        return group
    m = QMatrix4x4(scale[0], 0.0, 0.0, tx,
                   0.0, scale[1], 0.0, ty,
                   0.0, 0.0, scale[2], tz,
                   0.0, 0.0, 0.0, 1.0)
    return Group(transformed_mesh(world_mesh(group), m),
                 name=getattr(group, "name", ""))


def thumbnail_pixmap(group: Group, size: int = 128):
    """The hand-drawn picture the tray uses, without touching the GL."""
    from views.component_thumbs import thumbnail
    return thumbnail(group, size)


def flatten(group: Group) -> Group:
    """One Group with one mesh: the shape both the placement tool and the
    shared-definition bookkeeping expect. Nested placements are folded in
    (face colours and UV attrs survive, see :func:`core.group.world_mesh`)."""
    if not getattr(group, "children", None) and \
            getattr(group, "xform", None) is None:
        return group
    return Group(world_mesh(group), name=getattr(group, "name", ""))


def save_thumbnail(group: Group, path, size: int = 128) -> Path | None:
    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        thumbnail_pixmap(group, size).save(str(p), "PNG")
    except (OSError, ValueError):
        return None
    return p


def load_component(entry: dict, *, anchor: str = "base",
                   thumbnail_size: int | None = None,
                   strict: bool = False) -> Loaded | None:
    """Read the file an entry points at, with the orientation and size the
    entry recorded. ``thumbnail_size`` also writes the preview. On failure,
    returns ``None`` unless ``strict`` — then it raises with the reason."""
    try:
        path = user_library.resolve(entry)
        if path is None:
            raise ComponentLoadError(
                "the model file is missing from where it was indexed")
        matrix = entry.get("matrix")
        if matrix:
            m = tuple(float(v) for v in matrix)
        else:
            m = matrix_for(entry.get("unidad") or "m",
                           bool(entry.get("y_up")))
            factor = float(entry.get("escala") or 1.0)
            if factor != 1.0:
                m = tuple(v * factor for v in m)
        group = load_group(path, matrix=m,
                           name=entry.get("nombre") or path.stem)
        group = fit(group, cm=entry.get("cm"), anchor=anchor)
        group = flatten(group)
        loaded = Loaded(group, path)
        if thumbnail_size:
            save_thumbnail(group, user_library.thumbnail_path(entry),
                           thumbnail_size)
        return loaded
    except ComponentLoadError:
        if strict:
            raise
        return None
    except Exception as exc:  # noqa: BLE001 - a preview is never worth a crash
        if strict:
            raise ComponentLoadError(str(exc)) from exc
        return None
