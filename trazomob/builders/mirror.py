# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Parametric mirroring for TrazoMob modules.

IngeTrazo's native mirror reflects the MESH: doors, handles, hinges, and
drilling holes end up with inverted geometry and the module can no longer be
rebuilt from its parameters (the next width edit undoes the mirror or leaves
the hardware on the wrong side).

Here, mirroring is a PARAMETER (``mirror_x``). The geometry is reflected across
the local X axis right after construction and before rotation is applied, and
everything describing the part is reflected along with it:

* faces have their loop winding reversed (otherwise normals point inward and
  the solid disappears in rendering);
* machining holes (Ø35 hinge cup, cam lock, dowel) follow the mirror — for
  front parts, the X axis of operations is inverted;
* edge banding swaps sides (L1 ↔ L2) on parts where those faces are the sides;
* ``door_side`` (left/right) is swapped and "Esquerda"/"Direita" names follow,
  so the cutlist and opening animation remain consistent;
* cached animation state is discarded, to be recomputed from the already
  mirrored geometry.

Because the parameter is stored in the module's ``ext``, every rebuild
(dimension change, type change, undo/redo) returns mirrored.
"""
from __future__ import annotations

import re
from typing import Any

from PySide6.QtGui import QVector3D

#: Parameter key that enables mirroring on the local X axis.
MIRROR_PARAM = "mirror_x"

#: Animation state derived from geometry: must not survive mirroring.
_ANIMATION_KEYS = (
    "orig_vertices",
    "orig_uvws",
    "hinge_pivot",
    "flap_axis",
    "door_angle",
    "slide_delta",
    "open_fraction",
    "is_open",
)

#: Side swaps applied to part names.
_SIDE_MAP = {
    "Esquerda": "Direita",
    "Direita": "Esquerda",
    "esquerda": "direita",
    "direita": "esquerda",
    "ESQUERDA": "DIREITA",
    "DIREITA": "ESQUERDA",
    "Esquerdo": "Direito",
    "Direito": "Esquerdo",
    "esquerdo": "direito",
    "direito": "esquerdo",
    "ESQUERDO": "DIREITO",
    "DIREITO": "ESQUERDO",
    "Esq.": "Dir.",
    "Dir.": "Esq.",
    "esq.": "dir.",
    "dir.": "esq.",
    "Esq": "Dir",
    "Dir": "Esq",
    "esq": "dir",
    "dir": "esq",
    "Left": "Right",
    "Right": "Left",
    "left": "right",
    "right": "left",
    "LEFT": "RIGHT",
    "RIGHT": "LEFT",
}

#: Single pass with longest forms first: "Esquerda" is replaced before
#: "Esq", and already-substituted text is not reprocessed. Abbreviations
#: require a word boundary so "Esq" does not match inside "Esquadria".
_SIDE_PATTERNS = [
    re.escape(chave) + ("" if chave.endswith(".") else r"(?!\w)")
    for chave in sorted(_SIDE_MAP, key=len, reverse=True)
]
_SIDE_RE = re.compile("|".join(_SIDE_PATTERNS))


def is_mirrored(group: Any) -> bool:
    """Returns whether the module is mirrored, reading the parameter stored in ``ext``."""
    ext = getattr(group, "ext", None)
    if not isinstance(ext, dict):
        return False
    oficial = ext.get("trazomob")
    if isinstance(oficial, dict) and MIRROR_PARAM in oficial:
        return bool(oficial[MIRROR_PARAM])
    legado = ext.get("trazomob_module")
    if isinstance(legado, dict):
        return bool(legado.get(MIRROR_PARAM, False))
    return False


def _mesh_bounds_mm(mesh: Any) -> tuple[float, float, float] | None:
    """Dimensions (x, y, z) of a part's mesh, in millimeters."""
    vertices = getattr(mesh, "vertices", None)
    if not vertices:
        return None
    xs = [v.position.x() for v in vertices]
    ys = [v.position.y() for v in vertices]
    zs = [v.position.z() for v in vertices]
    return (
        (max(xs) - min(xs)) * 1000.0,
        (max(ys) - min(ys)) * 1000.0,
        (max(zs) - min(zs)) * 1000.0,
    )


def _swap_side_words(text: Any) -> Any:
    """Swaps "Esquerda"↔"Direita" (and equivalents) in a part name."""
    if not isinstance(text, str) or not text:
        return text
    return _SIDE_RE.sub(lambda m: _SIDE_MAP[m.group(0)], text)


def _flip_operations(meta: dict[str, Any], length_mm: float) -> None:
    """Inverts the X axis of machining operations on a front part."""
    operacoes = meta.get("operacoes")
    if not isinstance(operacoes, list):
        return
    novas = []
    for op in operacoes:
        if not isinstance(op, dict):
            novas.append(op)
            continue
        copia = dict(op)
        if copia.get("x") is not None:
            try:
                copia["x"] = round(float(length_mm) - float(copia["x"]), 3)
            except (TypeError, ValueError):
                pass
        novas.append(copia)
    meta["operacoes"] = novas


def _mirror_piece_metadata(piece: Any, dims_mm: tuple[float, float, float] | None) -> None:
    """Reflects a part's metadata: edge banding, machining, side, and name."""
    ext = getattr(piece, "ext", None)
    if not isinstance(ext, dict):
        ext = {}
        piece.ext = ext
    meta = ext.get("trazomob")
    if not isinstance(meta, dict):
        meta = {}
        ext["trazomob"] = meta

    if dims_mm is not None:
        sx, sy, sz = dims_mm
        min_dim = min(sx, sy, sz)
        # Front part (thickness along Y) or horizontal part (thickness along Z):
        # L1/L2 faces are the X sides, so they swap sides when mirrored.
        if abs(sy - min_dim) < 1e-5 or abs(sz - min_dim) < 1e-5:
            meta["fita_l1"], meta["fita_l2"] = (
                bool(meta.get("fita_l2", False)),
                bool(meta.get("fita_l1", False)),
            )
        # Only the front part has machining operations measured along X.
        if abs(sy - min_dim) < 1e-5 and meta.get("comprimento"):
            _flip_operations(meta, float(meta["comprimento"]))

    side = str(meta.get("door_side", "")).lower()
    if side == "left":
        meta["door_side"] = "right"
    elif side == "right":
        meta["door_side"] = "left"

    if "nome" in meta:
        meta["nome"] = _swap_side_words(meta["nome"])
    if isinstance(getattr(piece, "name", None), str):
        piece.name = _swap_side_words(piece.name)

    for key in _ANIMATION_KEYS:
        ext.pop(key, None)


def mirror_module_geometry(master: Any, plane_x: float) -> None:
    """Reflects all module geometry and metadata across the ``x = plane_x`` plane.

    Must be called BEFORE final rotation: the plane is the local X axis of the
    newly built module, not the world axis.
    """
    targets = list(getattr(master, "children", None) or [])
    if not targets:
        targets = [master]

    for piece in targets:
        mesh = getattr(piece, "mesh", None)
        vertices = getattr(mesh, "vertices", None)
        if not vertices:
            continue

        dims_mm = _mesh_bounds_mm(mesh)

        for vertex in vertices:
            p = vertex.position
            vertex.position = QVector3D(2.0 * plane_x - p.x(), p.y(), p.z())

        # Reflection flips the orientation of all loops: reversing the winding
        # keeps normals pointing outward (and holes pointing inward).
        for face in getattr(mesh, "faces", None) or []:
            loop = getattr(face, "loop", None)
            if loop:
                loop.reverse()
            for hole in getattr(face, "hole_loops", None) or []:
                if hole:
                    hole.reverse()

        mesh._mut_serial = getattr(mesh, "_mut_serial", 0) + 1
        _mirror_piece_metadata(piece, dims_mm)
