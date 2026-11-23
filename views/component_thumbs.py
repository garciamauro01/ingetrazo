# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez and IngeTrazo contributors.
"""Thumbnails for the tray's «In model» list: a small picture of each
component definition, drawn by hand.

Not a render — the GL renderer is never touched, which is what keeps the
tray cheap. The faces are projected from one fixed corner (front-right,
from above), painted back to front with a plain light on their own colour,
and fitted to the icon. Enough to tell a chair from a table at a glance.
A definition is drawn once and kept; a change to its geometry, its paint
or its subgroups draws it again.
"""
from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap, QPolygonF

#: Icon side, in pixels.
SIZE = 40
#: Threshold separating crisp wireframe-outlined architectural pieces from dense meshes.
MAX_FACES = 3000
_WIREFRAME_MAX_FACES = 400
_SUBPIXEL_CULL_MIN_TRIS = 4000
#: Vertices read for the change check, at most.
_PROBE = 2000

#: Where the picture is seen from (towards the viewer), and the light.
_EYE = (0.62, -0.74, 0.55)
_LIGHT = (0.35, -0.55, 0.85)
#: The default material's front, as the viewport shows it.
_DEFAULT = (0.96, 0.95, 0.925)

_cache: dict = {}
_tex_rgb_cache: dict[str, tuple[float, float, float]] = {}


def _unit(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / n for c in v)


_E = _unit(_EYE)
_R = _unit((-_E[1], _E[0], 0.0))
_U = _unit((_E[1] * _R[2] - _E[2] * _R[1],
            _E[2] * _R[0] - _E[0] * _R[2],
            _E[0] * _R[1] - _E[1] * _R[0]))
_L = _unit(_LIGHT)


def _placements(definition, m=None, depth=0):
    """``(mesh, matrix_or_None, paint)`` for the definition's own mesh and
    every subgroup below it, in the definition's coordinates — its own
    placement in the model is left out, so every copy draws the same."""
    paint = getattr(definition, "material", None)
    yield definition.mesh, m, paint
    if depth > 16:
        return
    for child in getattr(definition, "children", None) or ():
        xf = getattr(child, "xform", None)
        cm = xf if m is None else (m if xf is None else m * xf)
        yield from _placements(child, cm, depth + 1)


def _signature(definition) -> tuple:
    """What the picture depends on: counts, a sampled coordinate sum and
    the paint of each piece. Cheap, and it changes when the geometry does."""
    from core.mesh import DeferredMesh, face_attrs

    sig = []
    for mesh, m, paint in _placements(definition):
        if type(mesh) is DeferredMesh:
            src = mesh.__dict__["_deferred_source"]
            pos = src["pos"]
            n_verts = len(pos)
            step = max(1, n_verts // _PROBE) if n_verts else 1
            sample = pos[::step]
            s = float(
                sample[:, 0].sum()
                + sample[:, 1].sum() * 1.000003
                + sample[:, 2].sum() * 1.000007
            ) if len(sample) else 0.0
            n_faces = len(src["counts"])
            colors = tuple(_paint_key(fa) for fa in face_attrs(mesh))
            sig.append((id(mesh), n_verts, n_faces, round(s, 6),
                        hash(colors), _paint_key(paint),
                        tuple(m.data()) if m is not None else None))
            continue
        verts = mesh.vertices
        step = max(1, len(verts) // _PROBE)
        s = 0.0
        for v in verts[::step]:
            p = v.position
            s += p.x() + p.y() * 1.000003 + p.z() * 1.000007
        faces = mesh.faces
        fstep = max(1, len(faces) // _PROBE)
        colors = tuple(_paint_key(f.attrs) for f in faces[::fstep])
        sig.append((id(mesh), len(verts), len(faces), round(s, 6),
                    hash(colors), _paint_key(paint),
                    tuple(m.data()) if m is not None else None))
    return tuple(sig)


def _paint_key(attrs):
    if not attrs:
        return None
    c = attrs.get("color")
    t = attrs.get("texture")
    return (tuple(round(float(x), 3) for x in c) if c else None,
            t.get("path") if isinstance(t, dict) else None)


def _texture_rgb(path: str | None) -> tuple[float, float, float] | None:
    if not path:
        return None
    hit = _tex_rgb_cache.get(path)
    if hit is not None:
        return hit
    from pathlib import Path

    if not Path(path).is_file():
        return None
    img = QImage(path)
    if img.isNull():
        return None
    tiny = img.scaled(
        8, 8, Qt.IgnoreAspectRatio, Qt.SmoothTransformation
    ).convertToFormat(QImage.Format_ARGB32)
    r_acc = g_acc = b_acc = w_acc = 0.0
    for y in range(tiny.height()):
        for x in range(tiny.width()):
            col = tiny.pixelColor(x, y)
            a = col.alphaF()
            if a <= 0.02:
                continue
            r_acc += col.redF() * a
            g_acc += col.greenF() * a
            b_acc += col.blueF() * a
            w_acc += a
    if w_acc <= 0.0:
        return None
    rgb = (r_acc / w_acc, g_acc / w_acc, b_acc / w_acc)
    if len(_tex_rgb_cache) > 512:
        _tex_rgb_cache.clear()
    _tex_rgb_cache[path] = rgb
    return rgb


def _rgb(attrs, inherited):
    """The colour a face shows: its own paint, else the definition's, else
    the default material. A texture resolves to its average image colour."""
    for paint in (attrs, inherited):
        if not paint:
            continue
        tex = paint.get("texture")
        if isinstance(tex, dict) and tex.get("path"):
            trgb = _texture_rgb(str(tex["path"]))
            if trgb is not None:
                return trgb
        c = paint.get("color")
        if c:
            return tuple(float(x) for x in c[:3])
        if tex:
            return (0.72, 0.66, 0.58)
    return _DEFAULT


def _transform_points(pts: np.ndarray, m) -> np.ndarray:
    """Apply Qt column-major ``QMatrix4x4`` to an ``(N, 3)`` array."""
    if m is None or not len(pts):
        return pts
    mat = np.asarray(m.data(), dtype=np.float64).reshape(4, 4)
    if np.allclose(mat[:, 3], (0.0, 0.0, 0.0, 1.0)):
        return pts @ mat[:3, :3] + mat[3, :3]
    ones = np.ones((len(pts), 1), dtype=np.float64)
    hom = np.concatenate([pts, ones], axis=1) @ mat
    w = hom[:, 3:4]
    w = np.where(np.abs(w) > 1e-12, w, 1.0)
    return hom[:, :3] / w


def _triangulate_deferred(mesh, m, paint):
    """Extract triangles ``(T, 3, 3)`` and ``(T, 3)`` RGB without building ``DeferredMesh``."""
    src = mesh.__dict__["_deferred_source"]
    counts = np.asarray(src["counts"], dtype=np.int64)
    sizes = np.asarray(src["sizes"], dtype=np.int64)
    if not len(counts) or not len(sizes):
        return None, None, 0
    pos = _transform_points(np.asarray(src["pos"], dtype=np.float64), m)
    rings = np.asarray(src["rings"], dtype=np.int64)
    fa = np.asarray(src["face_attr"], dtype=np.int64)
    table = src["meta"].get("face_attrs") or []
    attrs_fn = getattr(table, "attrs", None)

    unique_k = np.unique(fa)
    palette = np.empty((len(unique_k), 3), dtype=np.float64)
    hidden_mask = np.zeros(len(unique_k), dtype=bool)
    default_rgb = _rgb(None, paint)

    for idx, raw_k in enumerate(unique_k.tolist()):
        if raw_k < 0:
            palette[idx] = default_rgb
            continue
        if attrs_fn is not None:
            f_attrs = attrs_fn(raw_k)
        else:
            from formats.igz import _face_attrs_from_json
            f_attrs = _face_attrs_from_json(table[raw_k])
        if isinstance(f_attrs, dict) and (
            f_attrs.get("hidden") or f_attrs.get("igz_link_placeholder")
        ):
            hidden_mask[idx] = True
            palette[idx] = default_rgb
        else:
            palette[idx] = _rgb(f_attrs, paint)

    k_slot = np.searchsorted(unique_k, fa)
    visible = ~hidden_mask[k_slot]

    ring_offsets = np.empty(len(sizes), dtype=np.int64)
    ring_offsets[0] = 0
    if len(sizes) > 1:
        ring_offsets[1:] = np.cumsum(sizes[:-1])

    face_ring_start = np.empty(len(counts), dtype=np.int64)
    face_ring_start[0] = 0
    if len(counts) > 1:
        face_ring_start[1:] = np.cumsum(counts[:-1])

    outer_sizes = sizes[face_ring_start]
    outer_starts = ring_offsets[face_ring_start]
    n_visible = int(visible.sum())

    tri_chunks = []
    rgb_chunks = []

    m3 = visible & (outer_sizes == 3)
    if m3.any():
        s3 = outer_starts[m3]
        idx3 = np.stack([rings[s3], rings[s3 + 1], rings[s3 + 2]], axis=1)
        tri_chunks.append(pos[idx3])
        rgb_chunks.append(palette[k_slot[m3]])

    m4 = visible & (outer_sizes == 4)
    if m4.any():
        s4 = outer_starts[m4]
        i0, i1, i2, i3 = rings[s4], rings[s4 + 1], rings[s4 + 2], rings[s4 + 3]
        idx4 = np.concatenate([
            np.stack([i0, i1, i2], axis=1),
            np.stack([i0, i2, i3], axis=1),
        ], axis=0)
        tri_chunks.append(pos[idx4])
        rgb4 = palette[k_slot[m4]]
        rgb_chunks.append(np.concatenate([rgb4, rgb4], axis=0))

    mn = visible & (outer_sizes > 4)
    if mn.any():
        ngon_idx = []
        ngon_slot = []
        for fi in np.flatnonzero(mn).tolist():
            st = int(outer_starts[fi])
            sz = int(outer_sizes[fi])
            v0 = int(rings[st])
            sl = int(k_slot[fi])
            for k in range(1, sz - 1):
                ngon_idx.append((v0, int(rings[st + k]), int(rings[st + k + 1])))
                ngon_slot.append(sl)
        if ngon_idx:
            tri_chunks.append(pos[np.asarray(ngon_idx, dtype=np.int64)])
            rgb_chunks.append(palette[np.asarray(ngon_slot, dtype=np.int64)])

    if not tri_chunks:
        return None, None, n_visible
    return np.concatenate(tri_chunks, axis=0), np.concatenate(rgb_chunks, axis=0), n_visible


def _triangulate_mesh(mesh, m, paint):
    """Extract triangles ``(T, 3, 3)`` and ``(T, 3)`` RGB from a built ``Mesh``."""
    faces = getattr(mesh, "faces", None)
    if not faces:
        return None, None, 0

    verts = mesh.vertices
    v_idx = {id(v): i for i, v in enumerate(verts)}
    pos_arr = _transform_points(
        np.array([[v.position.x(), v.position.y(), v.position.z()] for v in verts], dtype=np.float64),
        m,
    )

    attr_cache: dict[tuple[int, int], tuple[bool, tuple[float, float, float]]] = {}
    paint_id = id(paint)
    tri_idx = []
    tri_rgb = []
    n_visible = 0

    for f in faces:
        attrs = f.attrs
        ckey = (id(attrs), paint_id)
        cached = attr_cache.get(ckey)
        if cached is None:
            is_hidden = isinstance(attrs, dict) and (
                bool(attrs.get("hidden")) or bool(attrs.get("igz_link_placeholder"))
            )
            cached = (is_hidden, _DEFAULT if is_hidden else _rgb(attrs, paint))
            attr_cache[ckey] = cached
        if cached[0]:
            continue
        loop = f.loop
        n = len(loop)
        if n < 3:
            continue
        n_visible += 1
        rgb = cached[1]
        i0 = v_idx.get(id(loop[0]))
        if i0 is None:
            tri_idx.append((-1, -1, -1))
            tri_rgb.append(rgb)
            continue
        indices = [v_idx.get(id(v), -1) for v in loop]
        if any(idx < 0 for idx in indices):
            tri_idx.append((-1, -1, -1))
            tri_rgb.append(rgb)
            continue
        for k in range(1, n - 1):
            tri_idx.append((i0, indices[k], indices[k + 1]))
            tri_rgb.append(rgb)

    if not tri_idx:
        return None, None, n_visible
    arr_idx = np.asarray(tri_idx, dtype=np.int64)
    if (arr_idx < 0).any():
        # Fallback rare path if external test passes faces with vertices outside mesh.vertices
        tri_pts = []
        tri_cols = []
        for f in faces:
            attrs = f.attrs
            if isinstance(attrs, dict) and (attrs.get("hidden") or attrs.get("igz_link_placeholder")):
                continue
            loop = f.loop
            if len(loop) < 3:
                continue
            rgb = _rgb(attrs, paint)
            pts = _transform_points(
                np.array([[v.position.x(), v.position.y(), v.position.z()] for v in loop], dtype=np.float64),
                m,
            )
            p0 = pts[0]
            for k in range(1, len(pts) - 1):
                tri_pts.append((p0, pts[k], pts[k + 1]))
                tri_cols.append(rgb)
        if not tri_pts:
            return None, None, n_visible
        return np.asarray(tri_pts, dtype=np.float64), np.asarray(tri_cols, dtype=np.float64), n_visible

    return pos_arr[arr_idx], np.asarray(tri_rgb, dtype=np.float64), n_visible


def thumbnail(definition, size: int = SIZE) -> QPixmap:
    """The icon for ``definition`` (a component instance or a kept
    template), from the cache when nothing it shows has changed."""
    sig = _signature(definition)
    key = (sig[0][0], size)
    hit = _cache.get(key)
    if hit is not None and hit[0] == sig:
        return hit[1]
    pm = _draw(definition, size)
    # Past this, definitions long gone. (256 was below the 1 815 of a big
    # plant, and scrolling its list drew every picture again, #158.)
    if len(_cache) > 4096:
        _cache.clear()
    _cache[key] = (sig, pm)
    return pm


def _draw(definition, size: int) -> QPixmap:
    from core.mesh import DeferredMesh

    tri_parts = []
    rgb_parts = []
    total_faces = 0

    for mesh, m, paint in _placements(definition):
        if mesh is None:
            continue
        if type(mesh) is DeferredMesh:
            t_pts, t_cols, n_vis = _triangulate_deferred(mesh, m, paint)
        else:
            t_pts, t_cols, n_vis = _triangulate_mesh(mesh, m, paint)
        total_faces += n_vis
        if t_pts is not None and len(t_pts):
            tri_parts.append(t_pts)
            rgb_parts.append(t_cols)

    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    if not tri_parts:
        return pm

    tris = np.concatenate(tri_parts, axis=0)
    rgbs = np.concatenate(rgb_parts, axis=0)

    e1 = tris[:, 1] - tris[:, 0]
    e2 = tris[:, 2] - tris[:, 0]
    cross = np.cross(e1, e2)
    norm_len = np.linalg.norm(cross, axis=1)
    valid = norm_len > 1e-12
    if not valid.any():
        return pm

    pts = tris[valid]
    rgbs = rgbs[valid]
    normals = cross[valid] / norm_len[valid, None]
    l_vec = np.asarray(_L, dtype=np.float64)
    lam = np.abs(normals @ l_vec)

    x2d = pts[..., 0] * _R[0] + pts[..., 1] * _R[1] + pts[..., 2] * _R[2]
    y2d = -(pts[..., 0] * _U[0] + pts[..., 1] * _U[1] + pts[..., 2] * _U[2])
    depth = pts.mean(axis=1) @ np.asarray(_E, dtype=np.float64)

    x0, x1 = float(x2d.min()), float(x2d.max())
    y0, y1 = float(y2d.min()), float(y2d.max())
    span = max(x1 - x0, y1 - y0) or 1.0
    margin = 2.0
    scale = (size - 2.0 * margin) / span
    ox = margin + (size - 2.0 * margin - (x1 - x0) * scale) * 0.5
    oy = margin + (size - 2.0 * margin - (y1 - y0) * scale) * 0.5

    px = ox + (x2d - x0) * scale
    py = oy + (y2d - y0) * scale

    if len(pts) > _SUBPIXEL_CULL_MIN_TRIS:
        ext = np.maximum(px.max(axis=1) - px.min(axis=1), py.max(axis=1) - py.min(axis=1))
        large_mask = ext >= 1.5
        keep_large = np.flatnonzero(large_mask)
        small_idx = np.flatnonzero(~large_mask)
        if len(small_idx):
            sub_order = small_idx[np.argsort(depth[small_idx], kind="mergesort")]
            step_grid = size * 2 + 2
            cx = np.clip((px[sub_order].mean(axis=1) * 2.0).astype(np.int32), 0, step_grid - 1)
            cy = np.clip((py[sub_order].mean(axis=1) * 2.0).astype(np.int32), 0, step_grid - 1)
            cells = cy * step_grid + cx
            grid = np.full(step_grid * step_grid, -1, dtype=np.int64)
            grid[cells] = sub_order
            kept_small = grid[grid >= 0]
            indices = np.concatenate([keep_large, kept_small])
        else:
            indices = keep_large
    else:
        indices = np.arange(len(pts), dtype=np.int64)

    indices = indices[np.argsort(depth[indices], kind="mergesort")]
    dense_mesh = total_faces > _WIREFRAME_MAX_FACES

    px_sel = px[indices].tolist()
    py_sel = py[indices].tolist()
    rgb_sel = rgbs[indices]
    k_sel = (0.5 + 0.5 * lam[indices])[:, None]
    shaded = np.clip(rgb_sel * k_sel, 0.0, 1.0)
    rgb_u8 = (shaded * 255.0).round().astype(np.int32).tolist()

    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen()
    pen.setWidthF(0.5)

    for (xs_tri, ys_tri, (r, g, b)) in zip(px_sel, py_sel, rgb_u8):
        col = QColor(r, g, b)
        p.setBrush(col)
        # Modo sólido completo: não traça as arestas triangulares internas em tom escuro (wireframe)
        pen.setColor(col)
        p.setPen(pen)
        p.drawPolygon(QPolygonF((
            QPointF(xs_tri[0], ys_tri[0]),
            QPointF(xs_tri[1], ys_tri[1]),
            QPointF(xs_tri[2], ys_tri[2]),
        )))
    p.end()
    return pm


def _normal(pts):
    """Newell's normal of a polygon, ``None`` when it has no area."""
    nx = ny = nz = 0.0
    for i, a in enumerate(pts):
        b = pts[(i + 1) % len(pts)]
        nx += (a.y() - b.y()) * (a.z() + b.z())
        ny += (a.z() - b.z()) * (a.x() + b.x())
        nz += (a.x() - b.x()) * (a.y() + b.y())
    n = math.sqrt(nx * nx + ny * ny + nz * nz)
    if n < 1e-12:
        return None
    return (nx / n, ny / n, nz / n)
