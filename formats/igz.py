# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez and IngeTrazo contributors.
"""Native IngeTrazo document format (``.igz``).

Plain JSON, schema-versioned. Trivial to inspect, edit by hand, and diff
in source control. Will grow as new entity types (faces, groups,
components, materials) land — old documents must keep loading.

Layout::

    {
      "igz_format": 1,
      "app_version": __version__,
      "scene": {
        "edges": [
          {"a": [x, y, z], "b": [x, y, z]},
          ...
        ],
        "faces": [
          {"vertices": [[x, y, z], ...]}
        ]
      }
    }

**Textured documents are ZIP containers** (format 2). A texture is an image
*file*, so a plain-JSON document could only point at one — an absolute path
that broke the moment the ``.igz`` travelled to another machine. When the scene
uses textures the document becomes a ZIP holding the very same JSON as
``document.json`` plus the images under ``textures/``, and each texture entry
carries ``"embed": "textures/<hash>-<name>"`` instead of ``"path"``. The
document is then **self-contained and portable**. Opening one unpacks the
images into the app's texture cache (content-addressed, so documents sharing an
image share the file and the GPU upload) and points the entries back at real
paths — the rest of the app keeps seeing ``attrs["texture"]["path"]`` and knows
nothing about containers.

A preview turns any document into that same ZIP container, under
``meta/thumbnail.png`` — Windows Explorer reads it through the COM handler in
``installer/``. Without a preview, untextured documents stay **plain JSON at
format 1**: the common case remains diffable, hand-editable, and readable by
older builds. ``load_into`` sniffs the ZIP magic, so both shapes open
transparently.

**Large documents are format 3** (see ``_LARGE_DOCUMENT``): always a ZIP, and
each big mesh is a ``{"geom": {...}}`` block instead of ``edges``/``faces``
lists — its distinct points once as float32, edges and face rings as int32
indices, edge flags and a shared table of face attributes, in one raw
member under ``geom/`` (layout in the JSON, no pickles). Builds that read
only up to format 2 refuse it with a message instead of opening it empty.

**A big face-attribute table is format 4** (see ``_ATTRS_MIN``): the table
that a textured import leaves behind — one entry per face, a texture
placement each — is the largest thing in a real document (66 MB of JSON on a
half-furnished house), so from 512 entries on it travels as bytes in the same
block: one string pool, one shape per group of equal-shaped entries, and the
values as columns, a texture placement becoming eight planar float columns
instead of a JSON object per face (layout in ``_pack_face_attrs``). Below
that it stays JSON and the document stays at format 3, so a small document
keeps opening in the builds before this one; builds that read only up to
format 3 refuse format 4 with the same message.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
import math
from pathlib import Path

from core.version import __version__

from PySide6.QtGui import QVector3D

from core.dimension import Dimension
from core.group import Group
from core.mesh import Mesh
from georef.datum import SceneDatum
from georef.geopath import GeoPath


PLAIN_FORMAT = 1        # bare JSON document (no images to carry)
CONTAINER_FORMAT = 2    # ZIP container: document.json + textures/
GEOMETRY_FORMAT = 3     # + big meshes as binary blocks under geom/
ATTRS_FORMAT = 4        # + a big mesh's face-attribute table as bytes
CURRENT_FORMAT = ATTRS_FORMAT      # the newest this build reads
_ZIP_MAGIC = b"PK\x03\x04"
_DOC_ENTRY = "document.json"
# Windows Explorer reads this member through the IThumbnailProvider in
# installer/IngeTrazoThumbnailProvider.cs. A preview forces the ZIP container
# even for an otherwise untextured document; document.json is unchanged.
_THUMB_ENTRY = "meta/thumbnail.png"
_TEX_PREFIX = "textures/"
# Fixed timestamp for every archive member: two saves of the same scene must
# produce byte-identical files (diffable documents, and no pointless churn in
# whatever the user syncs them with).
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)

# A document with more faces + edges than this is written COMPACT (no
# indentation) and deflated at level 1. Indented, the 14 M-face model of
# #158 was 3.3 GB of text — every coordinate on a line of its own — and
# saving it peaked at 16 GB of memory; compact it is 1.4 GB, and level 1
# deflates it in 4 s instead of 20 (the file grows ~35 %). Nobody reads a
# document that size by hand, while a small one stays indented and
# diffable, at the default level where deflating costs nothing anyway.
_LARGE_DOCUMENT = 20_000

# Format 3 — a LARGE document (above) stores each mesh of at least this many
# corners as a binary block instead of JSON lists: every distinct point once
# as float32 (exactly what the QVector3D of the live mesh holds, so nothing
# is lost), and edges and faces as int32 indices into it. On the #158 model
# the JSON spelled out 19 M points to describe 2 M distinct ones, and
# parsing that text was half of the minute it took to open. Structure —
# groups, layers, materials, the face attributes — stays JSON. Small meshes
# stay JSON too: the reader rebuilds a small mesh entity by entity, a big
# one in one bulk pass (see :func:`_bulk_sized`), and the two number their
# vertices differently — a mesh goes binary only where the JSON reader
# would take the bulk pass, so either way it reopens the same.
_GEOM_PREFIX = "geom/"
_BULK_MIN = 1024
#: The dtypes a geometry block may declare — anything else is refused, so a
#: crafted document cannot make the reader build arbitrary objects.
_GEOM_DTYPES = frozenset(("<f4", "<i4", "<i8", "|u1"))

# Format 4 — a face-attribute table of at least this many entries is written
# as bytes (see :func:`_pack_face_attrs`) instead of JSON. Below it the table
# costs a few kilobytes at most, not worth a format bump: a small document
# keeps opening in the builds that came before this one.
_ATTRS_MIN = 512
#: The node kinds of that codec — the shape of what ``_face_attrs_json``
#: writes, stored once per group of equal-shaped entries: a scalar leaf, a
#: dict, a list, and a fixed-length run of numbers (``uvw``, ``color``).
_N_LEAF, _N_DICT, _N_LIST, _N_VECTOR = range(4)
#: The leaf kinds, in the order a crafted blob may name them.
(_L_NULL, _L_BOOL, _L_INT, _L_FLOAT, _L_STR,
 _L_EMPTY_DICT, _L_EMPTY_LIST) = range(7)
#: How deep a value may nest — a crafted blob must not recurse forever.
_ATTRS_MAX_DEPTH = 8


class _GeomSink(dict):
    """The sink a save collects geometry blocks in (member name → bytes).

    It also remembers whether any block took the format-4 attribute codec,
    which is what decides the document's ``igz_format``. A plain ``dict``
    (the tests build blocks with one) never takes it, so a document can never
    claim format 4 while carrying a JSON table.
    """

    binary_attrs = False


# Keys the texture walk never needs to enter: pure coordinate blocks, and
# the edge list (fixed ``_edge_json`` schema — no attrs, no textures).
# Descending into every vertex triple and edge dict made the walk itself
# cost seconds on a 300k-face document.
_TEXTURE_WALK_SKIP = frozenset(("vertices", "holes", "a", "b", "edges",
                                "arrays"))


def _texture_entries(node):
    """Yield every ``"texture"`` dict inside a serialized payload — face
    materials, back-side materials (``attrs["back"]``), and whatever nests one
    later. Walking the JSON keeps this honest as the schema grows: a new place
    to hang a texture is embedded without touching this module. Coordinate
    blocks (:data:`_TEXTURE_WALK_SKIP`) and leaf value lists are skipped —
    they are the bulk of the document and can never carry a texture."""
    for parent, key in _texture_slots(node):
        yield parent[key]


def _texture_slots(node):
    """Yield ``(parent, key)`` for every ``"texture"`` dict that
    :func:`_texture_entries` walks, so a caller can put a copy in its place."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "texture" and isinstance(value, dict):
                yield node, key
            elif key not in _TEXTURE_WALK_SKIP:
                yield from _texture_slots(value)
    elif isinstance(node, list):
        if node and not isinstance(node[0], (dict, list)):
            return                       # a leaf value list (colour, offsets)
        for value in node:
            yield from _texture_slots(value)


def _pack_textures(payload) -> tuple[dict, int]:
    """Rewrite the payload's texture entries in place for storage inside the
    container: ``"path"`` (a machine-local absolute path) → ``"embed"`` (an
    archive member name). Returns ``({member name: image bytes}, missing)``,
    where *missing* counts images whose file could not be read — those keep
    their ``"path"``, so a document whose cache was wiped saves no worse than
    before instead of losing the reference outright."""
    import hashlib
    from core.texture import is_image_file, texture_file_name

    blobs: dict = {}
    resolved: dict = {}          # source path → member name ("" = unreadable)
    missing = 0
    def _member_for(src):
        nonlocal missing
        member = resolved.get(src)
        if member is None:
            if not is_image_file(src):
                resolved[src] = ""
                missing += 1
                return ""
            try:
                data = Path(src).read_bytes()
            except OSError:
                resolved[src] = ""
                missing += 1
                return ""
            digest = hashlib.sha1(data).hexdigest()[:16]
            # ``src`` is usually a cached file already named ``<hash>-<name>``:
            # texture_file_name drops that prefix, so the member is always
            # ``<hash>-<name>`` and never grows with the number of saves.
            member = f"{_TEX_PREFIX}{digest}-{texture_file_name(Path(src).name)}"
            resolved[src] = member
            blobs[member] = data
        return member

    for parent, key in _texture_slots(payload):
        # Rewrite a copy, never the dict itself: the payload may still share
        # it with the live scene (a group's paint went in through a shallow
        # dict(), #877), and rewriting it there took "path" away for good —
        # the next save, an autosave included, wrote the texture without its
        # image.
        tex = parent[key] = dict(parent[key])
        src = tex.get("path")
        if src:
            member = _member_for(src)
            if member:
                tex.pop("path", None)
                tex["embed"] = member
        # A colourized entry also carries its UNTINTED source: without it a
        # document opened on another machine could only re-tint the tinted
        # image, and "remove colour" would have nothing to go back to. The
        # blobs map is content-addressed, so a base shared with another
        # material (or with an untinted face) costs nothing extra.
        base = tex.get("base")
        if base:
            member = _member_for(base)
            if member:
                tex.pop("base", None)
                tex["base_embed"] = member
    return blobs, missing


def _unpack_textures(payload, archive) -> None:
    """Inverse of :func:`_pack_textures`: extract each embedded image into the
    app's texture cache and point the entry back at that real file, so
    everything downstream (renderer, exporters) keeps working with paths. A
    member the archive lost leaves the entry without a texture path — the face
    renders untextured rather than the load failing."""
    from core.texture import cache_image

    unpacked: dict = {}

    def _restore(member):
        """The cached file for an archive member, or None. cache_image drops
        the member's hash prefix(es) and re-derives one from the bytes, so the
        same image lands on the same cached file whether it arrived in a
        document (even one whose member name was bloated by 0.3.10's
        stacking) or straight from a .skp."""
        out = unpacked.get(member)
        if out is None:
            try:
                data = archive.read(member)
            except KeyError:
                return None
            name = member.rsplit("/", 1)[-1]
            try:
                out = str(cache_image(data, name, "embedded"))
            except OSError:
                out = ""        # unwritable cache: the face loses its image
            unpacked[member] = out
        return out or None

    for tex in _texture_entries(payload):
        base_member = tex.pop("base_embed", None)
        if base_member and not tex.get("base"):
            restored = _restore(base_member)
            if restored:
                tex["base"] = restored
        member = tex.pop("embed", None)
        if not member or tex.get("path"):
            continue
        out = _restore(member)
        if out:
            tex["path"] = out


def _face_json(f) -> dict:
    entry = {"vertices": [list(v.position.toTuple()) for v in f.loop]}
    # Holes are written only when present, so simple documents stay terse and
    # older readers ignore the extra key gracefully.
    if getattr(f, "hole_loops", None):
        entry["holes"] = [
            [list(v.position.toTuple()) for v in loop] for loop in f.hole_loops
        ]
    entry.update(_face_attrs_json(f))
    return entry


def _face_attrs_json(f) -> dict:
    """Everything a face stores besides its loops — the part a format-3
    geometry block keeps as JSON, in a table shared by equal faces."""
    entry: dict = {}
    # Material colour (the Paint tool), written only when set.
    color = getattr(f, "attrs", {}).get("color")
    if color is not None:
        entry["color"] = list(color)
    texture = getattr(f, "attrs", {}).get("texture")
    if texture is not None:
        entry["texture"] = dict(texture)
    layer = getattr(f, "attrs", {}).get("layer")
    if layer is not None:
        entry["layer"] = layer
    ifc = getattr(f, "attrs", {}).get("ifc")
    if ifc is not None:
        entry["ifc"] = dict(ifc)
    opacity = getattr(f, "attrs", {}).get("opacity")
    if opacity is not None:
        entry["opacity"] = float(opacity)
    if getattr(f, "attrs", {}).get("hidden"):
        entry["hidden"] = True          # Hide on a face
    # Material identity (core.materials): the registry name this face was
    # painted with. Written only when present; older readers ignore it.
    mat = getattr(f, "attrs", {}).get("mat")
    if mat:
        entry["mat"] = mat
    back = getattr(f, "attrs", {}).get("back")
    if isinstance(back, dict):
        # Deep-copy the nested texture: _pack_textures rewrites the entries it
        # finds, and it must never reach into the live scene's attrs.
        entry["back"] = {k: dict(v) if isinstance(v, dict) else v
                         for k, v in back.items()}
    elif back is True:
        # A two-sided face: the back mirrors the front (what the mesh
        # formats describe, and what a .skp face painted the same on
        # both sides becomes). Absent = the style's default back.
        entry["back"] = True
    return entry


def _edge_json(e) -> dict:
    entry = {"a": list(e.v0.position.toTuple()),
             "b": list(e.v1.position.toTuple())}
    if getattr(e, "soft", False):
        entry["soft"] = True
    if getattr(e, "hidden", False):
        entry["hidden"] = True
    if getattr(e, "curve", None) is not None:
        entry["curve"] = e.curve
    if getattr(e, "layer", None) is not None:
        entry["layer"] = e.layer
    return entry


def _mesh_json(mesh, geom_sink=None) -> dict:
    """The mesh block. With a ``geom_sink`` (a large document) a big mesh
    goes to a binary block in the sink and the JSON keeps only its
    reference and face-attribute table (format 3)."""
    from core.lazy_mesh import plan_of
    plan = plan_of(mesh)
    if plan is not None and geom_sink is not None and _bulk_sized(
            len(plan.edges), plan.nfaces):
        # A lazy mesh (experimental engine): written from its arrays, the
        # same bytes, without building it.
        return {"geom": _pack_plan(mesh, plan, geom_sink)}
    if plan is not None:
        return _plan_json(mesh, plan)
    if geom_sink is not None and _bulk_sized(len(mesh.edges),
                                             len(mesh.faces)):
        return {"geom": _pack_geometry(mesh, geom_sink)}
    return {
        "edges": [_edge_json(e) for e in mesh.edges],
        "faces": [_face_json(f) for f in mesh.faces],
    }


def _plan_json(mesh, plan) -> dict:
    """The JSON block :func:`_mesh_json` writes for the mesh a deferred
    ``mesh`` would build, from its plan: the same entries, keys in the
    same order."""
    pos = plan.pos.tolist()
    edges = []
    for i, (a, b) in enumerate(plan.edges.tolist()):
        entry = {"a": list(pos[a]), "b": list(pos[b])}
        if plan.soft[i]:
            entry["soft"] = True
        if plan.hidden[i]:
            entry["hidden"] = True
        if plan.curve[i] is not None:
            entry["curve"] = plan.curve[i]
        if plan.layer[i] is not None:
            entry["layer"] = plan.layer[i]
        edges.append(entry)
    src = mesh.__dict__["_deferred_source"]
    raw = src["meta"].get("face_attrs") or []
    attrs_of: dict = {}
    corners = plan.corners.tolist()
    sizes = plan.ring_sizes.tolist()
    faces = []
    c = r = 0
    for f, (nr, k) in enumerate(zip(plan.ring_counts.tolist(),
                                    src["face_attr"].tolist())):
        rings = []
        for _ in range(nr):
            rings.append([list(pos[i]) for i in corners[c:c + sizes[r]]])
            c += sizes[r]
            r += 1
        entry = {"vertices": rings[0]}
        if len(rings) > 1:
            entry["holes"] = rings[1:]
        if k >= 0:
            parsed = attrs_of.get(k)
            if parsed is None:
                parsed = attrs_of[k] = _face_attrs_from_json(raw[k]) or {}
            # Fresh dicts per face, as the object writer makes (the
            # texture packer rewrites them in place).
            entry.update(_face_attrs_json(SimpleNamespace(attrs=parsed)))
        faces.append(entry)
    return {"edges": edges, "faces": faces}


def _bulk_sized(n_edges: int, n_faces: int) -> bool:
    """Whether a mesh this size is rebuilt in one bulk pass (a rough corner
    count) — the same test for the JSON reader and the format-3 writer."""
    return n_edges + n_faces * 4 >= _BULK_MIN


def _pack_geometry(mesh, sink: dict) -> dict:
    """Write ``mesh`` as a format-3 geometry block into ``sink`` (member
    name → bytes) and return its JSON side.

    The points are numbered in the order a JSON document lists them —
    every edge's two ends, then every face's outer ring and holes — so
    the reader's weld meets them in the same order and rebuilds the same
    vertices. Holes nested in a bigger hole are dropped here, where the
    JSON reader drops them (:func:`core.topology._maximal_holes`)."""
    import numpy as np
    from core.topology import _maximal_holes

    edges = mesh.edges
    corners: list = []
    for e in edges:
        corners.append(e.v0)
        corners.append(e.v1)
    ring_sizes: list = []
    ring_counts: list = []
    face_attr: list = []
    table: list = []
    table_index: dict = {}
    for f in mesh.faces:
        loop = f.loop
        holes = f.hole_loops or ()
        if len(holes) > 1:
            pos = [[QVector3D(v.position) for v in h] for h in holes]
            kept = {id(k) for k in _maximal_holes(pos)}
            holes = [h for h, p in zip(holes, pos) if id(p) in kept]
        ring_counts.append(1 + len(holes))
        ring_sizes.append(len(loop))
        corners.extend(loop)
        for h in holes:
            ring_sizes.append(len(h))
            corners.extend(h)
        attrs = _face_attrs_json(f) if f.attrs else None
        if attrs:
            key = json.dumps(attrs, sort_keys=True, separators=(",", ":"))
            k = table_index.get(key)
            if k is None:
                k = table_index[key] = len(table)
                table.append(attrs)
            face_attr.append(k)
        else:
            face_attr.append(-1)

    # Number the vertex objects by first appearance.
    ids = np.fromiter((id(v) for v in corners), dtype=np.uint64,
                      count=len(corners))
    _u, first, inverse = np.unique(ids, return_index=True,
                                   return_inverse=True)
    order = np.argsort(first, kind="stable")
    rank = np.empty_like(order)
    rank[order] = np.arange(len(order))
    index = rank[inverse.reshape(-1)].astype(np.int32)
    pos = np.array([corners[i].position.toTuple()
                    for i in first[order].tolist()],
                   dtype=np.float32).reshape(-1, 3)
    if not np.isfinite(pos).all():
        raise NonFiniteDocumentError("geometry")

    ne = len(edges)
    arrays = {
        "pos": pos,
        "edges": index[:2 * ne].reshape(-1, 2),
        "rings": index[2 * ne:],
        "ring_sizes": np.asarray(ring_sizes, dtype=np.int32),
        "ring_counts": np.asarray(ring_counts, dtype=np.int32),
        "face_attr": np.asarray(face_attr, dtype=np.int32),
    }
    flags = np.zeros(ne, dtype=np.uint8)
    curves = layers = None
    layer_table: list = []
    layer_index: dict = {}
    for i, e in enumerate(edges):
        if e.soft:
            flags[i] |= 1
        if e.hidden:
            flags[i] |= 2
        if e.curve is not None:
            if curves is None:
                curves = np.full(ne, -1, dtype=np.int64)
            curves[i] = e.curve
        if e.layer is not None:
            if layers is None:
                layers = np.full(ne, -1, dtype=np.int32)
            k = layer_index.get(e.layer)
            if k is None:
                k = layer_index[e.layer] = len(layer_table)
                layer_table.append(e.layer)
            layers[i] = k
    arrays["edge_flags"] = flags
    if curves is not None:
        arrays["edge_curve"] = curves
    if layers is not None:
        arrays["edge_layer"] = layers
    return _write_geometry(arrays, table, layer_table, sink)


def _write_geometry(arrays, table, layer_table, sink: dict) -> dict:
    """The blob of a format-3 block into ``sink``; its JSON side."""
    import numpy as np
    # Format 4: the attribute table as bytes (see _pack_face_attrs). The
    # table is the biggest thing a textured import leaves in a document —
    # 66 MB of JSON in a real house — and it is one table per mesh, so it
    # rides in the same block as the geometry it describes.
    packed = None
    if table and len(table) >= _ATTRS_MIN and isinstance(sink, _GeomSink):
        packed = _pack_face_attrs(table)
        if packed is not None:
            arrays = dict(arrays)
            arrays["attrs"] = np.frombuffer(packed, dtype=np.uint8)
    # One raw blob, each array at an 8-byte-aligned offset: no pickles, no
    # per-save timestamps (an .npz carries them), so two saves of the same
    # model stay byte-identical.
    layout: dict = {}
    chunks: list = []
    offset = 0
    for name, arr in arrays.items():
        arr = np.ascontiguousarray(arr)
        data = arr.tobytes()
        layout[name] = [arr.dtype.str, list(arr.shape), offset]
        pad = (-len(data)) % 8
        chunks.append(data + b"\0" * pad)
        offset += len(data) + pad
    member = f"{_GEOM_PREFIX}{len(sink)}.bin"
    sink[member] = b"".join(chunks)
    meta = {"member": member, "arrays": layout}
    if packed is not None:
        sink.binary_attrs = True
    elif table:
        meta["face_attrs"] = table
    if layer_table:
        meta["edge_layers"] = layer_table
    return meta


class _Unsupported(Exception):
    """A value the attribute codec does not describe — the table goes JSON."""


def _attrs_leaf(value) -> int:
    """The leaf kind of a scalar, or ``_Unsupported`` for anything else."""
    kind = type(value)
    if value is None:
        return _L_NULL
    if kind is bool:
        return _L_BOOL
    if kind is int:
        return _L_INT
    if kind is float:
        if not math.isfinite(value):
            raise _Unsupported
        return _L_FLOAT
    if kind is str:
        return _L_STR
    raise _Unsupported


def _attrs_template(value, leaves, depth=0):
    """The shape of ``value``, with one entry appended to ``leaves`` per
    column the encoder will write, in the order it writes them."""
    if depth > _ATTRS_MAX_DEPTH:
        raise _Unsupported
    kind = type(value)
    if kind is dict:
        if not value:
            leaves.append(None)
            return (_N_LEAF, _L_EMPTY_DICT)
        items = []
        for key, item in value.items():
            if type(key) is not str:
                raise _Unsupported
            items.append((key, _attrs_template(item, leaves, depth + 1)))
        return (_N_DICT, tuple(items))
    if kind is list or kind is tuple:
        if not value:
            leaves.append(None)
            return (_N_LEAF, _L_EMPTY_LIST)
        first = type(value[0])
        # A run of numbers is ONE column, written planar (every first
        # component, then every second…): a texture placement is eight
        # floats per face, and keeping the components together is what
        # makes them compress — interleaved, the exponents of unrelated
        # components break each other's runs.
        if (first is float or first is int) and \
                all(type(item) is first for item in value):
            if first is float and not all(math.isfinite(item)
                                          for item in value):
                raise _Unsupported
            leaves.append(tuple(value))
            return (_N_VECTOR, _L_FLOAT if first is float else _L_INT,
                    len(value))
        return (_N_LIST, tuple(_attrs_template(item, leaves, depth + 1)
                               for item in value))
    leaves.append(value)
    return (_N_LEAF, _attrs_leaf(value))


def _attrs_specs(node, out=None) -> list:
    """The columns of a template, in write order: ``(leaf kind, length)``,
    length 0 for a scalar and the run length for a vector."""
    if out is None:
        out = []
    kind = node[0]
    if kind == _N_LEAF:
        out.append((node[1], 0))
    elif kind == _N_VECTOR:
        out.append((node[1], node[2]))
    elif kind == _N_DICT:
        for _, child in node[1]:
            _attrs_specs(child, out)
    else:
        for child in node[1]:
            _attrs_specs(child, out)
    return out


def _attrs_columns(node) -> int:
    """How many columns a template writes (what the reader must skip)."""
    kind = node[0]
    if kind == _N_LEAF or kind == _N_VECTOR:
        return 1
    if kind == _N_DICT:
        return sum(_attrs_columns(child) for _, child in node[1])
    return sum(_attrs_columns(child) for child in node[1])


def _attrs_write_node(node, intern) -> bytes:
    """The template, as bytes — once per group, however many rows it has."""
    import struct

    kind = node[0]
    if kind == _N_LEAF:
        return struct.pack("<BB", _N_LEAF, node[1])
    if kind == _N_VECTOR:
        return struct.pack("<BBH", _N_VECTOR, node[1], node[2])
    if kind == _N_DICT:
        if len(node[1]) > 0xFFFF:
            raise _Unsupported
        out = bytearray(struct.pack("<BH", _N_DICT, len(node[1])))
        for key, child in node[1]:
            out += struct.pack("<H", intern(key))
            out += _attrs_write_node(child, intern)
        return bytes(out)
    if len(node[1]) > 0xFFFF:
        raise _Unsupported
    out = bytearray(struct.pack("<BH", _N_LIST, len(node[1])))
    for child in node[1]:
        out += _attrs_write_node(child, intern)
    return bytes(out)


def _pack_face_attrs(table) -> bytes | None:
    """The face-attribute table as bytes, or ``None`` to keep it as JSON.

    Layout: a string pool (every key and every name once), then one group per
    distinct shape — same keys in the same order, same kinds — its shape
    written once and its values as columns. A texture placement, the bulk of
    a real table, becomes eight planar float columns instead of a JSON object
    per face.

    Numbers go as float32: a placement at 1e-7 is the same picture, and the
    block's own points are float32 already. A value float32 cannot hold, or
    anything the codec does not describe, sends the whole table back to JSON,
    so a save never loses what it cannot carry.
    """
    import struct

    import numpy as np

    groups: dict = {}
    try:
        for index, entry in enumerate(table):
            leaves: list = []
            node = _attrs_template(entry, leaves)
            got = groups.get(node)
            if got is None:
                got = groups[node] = ([], [])
            got[0].append(index)
            got[1].append(tuple(leaves))
    except _Unsupported:
        return None
    order = list(groups.items())
    if len(order) > 0xFFFF:
        return None
    pool: dict = {}
    strings: list = []

    def intern(text: str) -> int:
        k = pool.get(text)
        if k is None:
            if len(strings) > 0xFFFF:
                raise _Unsupported
            k = pool[text] = len(strings)
            strings.append(text)
        return k

    bodies = []
    mapping = b""
    if len(order) > 1:
        # Which group each entry belongs to, and its row inside it: a table
        # is a sequence, so entry k must come back as entry k whatever
        # order the groups ended up in.
        group_of = np.zeros(len(table), dtype="<u2")
        row_of = np.zeros(len(table), dtype="<i4")
        for g, (_node, (rows, _flat)) in enumerate(order):
            at = np.asarray(rows, dtype="<i4")
            group_of[at] = g
            row_of[at] = np.arange(len(at), dtype="<i4")
        mapping = group_of.tobytes() + row_of.tobytes()
    try:
        for node, (rows, flat) in order:
            body = bytearray(struct.pack("<I", len(rows)))
            body += _attrs_write_node(node, intern)
            for j, (leaf, length) in enumerate(_attrs_specs(node)):
                values = [row[j] for row in flat]
                if leaf == _L_FLOAT:
                    wide = np.asarray(values, dtype="<f8")
                    if not np.isfinite(wide).all() or (
                            wide.size and np.abs(wide).max()
                            > np.finfo(np.float32).max):
                        raise _Unsupported
                    arr = wide.astype("<f4")
                    body += (arr.T.copy() if length else arr).tobytes()
                elif leaf == _L_INT:
                    arr = np.asarray(values, dtype="<i8")
                    body += (arr.T.copy() if length else arr).tobytes()
                elif leaf == _L_BOOL:
                    body += np.asarray([1 if v else 0 for v in values],
                                       dtype="|u1").tobytes()
                elif leaf == _L_STR:
                    body += np.asarray([intern(v) for v in values],
                                       dtype="<i4").tobytes()
            bodies.append(bytes(body))
    except (_Unsupported, OverflowError, TypeError, ValueError):
        return None
    head = bytearray(struct.pack("<BII", 1, len(table), len(strings)))
    for text in strings:
        raw = text.encode("utf-8")
        head += struct.pack("<I", len(raw))
        head += raw
    head += struct.pack("<I", len(order))
    return bytes(head) + mapping + b"".join(bodies)


def _attrs_read(node, cols, index, row):
    """``(value, next column)`` — the JSON shape of one row, read in place."""
    kind = node[0]
    if kind == _N_LEAF:
        leaf = node[1]
        if leaf == _L_NULL:
            return None, index
        if leaf == _L_EMPTY_DICT:
            return {}, index
        if leaf == _L_EMPTY_LIST:
            return [], index
        return cols[index][row], index + 1
    if kind == _N_VECTOR:
        return cols[index][row], index + 1
    if kind == _N_DICT:
        out = {}
        for key, child in node[1]:
            out[key], index = _attrs_read(child, cols, index, row)
        return out, index
    out = []
    for child in node[1]:
        value, index = _attrs_read(child, cols, index, row)
        out.append(value)
    return out, index


def _attrs_builder(node, cols):
    """A ``row → attributes`` callable, the fused equivalent of
    ``_face_attrs_from_json(_attrs_read(...))``: it reads only the keys a
    face actually keeps, straight into the dict the mesh is given.

    Mirrors :func:`_face_attrs_from_json` exactly, unknown keys included
    (they are dropped there too). A table of another shape falls back to the
    two-step read, so the fast path can never disagree with the slow one."""
    if node[0] != _N_DICT:
        def generic(row):
            return _face_attrs_from_json(_attrs_read(node, cols, 0, row)[0])
        return generic
    fields = []
    offset = 0
    for key, child in node[1]:
        if key in ("color", "texture", "layer", "ifc", "opacity", "hidden",
                   "mat", "back"):
            fields.append((key, offset, child))
        offset += _attrs_columns(child)

    def build(row):
        out: dict = {}
        for key, start, child in fields:
            value, _ = _attrs_read(child, cols, start, row)
            if key == "color":
                if value is not None:
                    out["color"] = list(value)
            elif key == "texture":
                if value is not None:
                    out["texture"] = dict(value)
            elif key == "ifc":
                if value:
                    out["ifc"] = dict(value)
            elif key == "back":
                if isinstance(value, dict):
                    out["back"] = dict(value)
                elif value is True:
                    out["back"] = True
            elif key == "layer":
                if value:
                    out["layer"] = value
            elif key == "opacity":
                if value is not None:
                    out["opacity"] = float(value)
            elif key == "hidden":
                if value:
                    out["hidden"] = True
            elif key == "mat" and value:
                out["mat"] = value
        return out or None

    return build


class _FaceAttrs:
    """A face-attribute table read from a format-4 block, decoded on demand.

    A read-only sequence: ``table[k]`` is the JSON-shaped entry ``k``, which
    is what the document's other readers index (``core.mesh.face_attrs``,
    ``core.purge``, the array bake). Building a mesh asks for every entry in
    face order instead, so :meth:`attrs_for` skips the intermediate dict and
    hands the mesh its final attributes directly — on a real house that is
    the difference between 3.4 s and 0.6 s of the open."""

    def __init__(self, raw: bytes):
        import struct

        import numpy as np

        self._blob = raw
        view = memoryview(raw)
        end = len(view)
        if end < 9:
            raise ValueError("face attributes: truncated")
        version, n_entries, n_strings = struct.unpack_from("<BII", view, 0)
        if version != 1:
            raise ValueError("face attributes: version")
        pos = 9
        strings = []
        for _ in range(n_strings):
            if pos + 4 > end:
                raise ValueError("face attributes: string pool")
            (size,) = struct.unpack_from("<I", view, pos)
            pos += 4
            if pos + size > end:
                raise ValueError("face attributes: string")
            try:
                strings.append(bytes(view[pos:pos + size]).decode("utf-8"))
            except UnicodeDecodeError:
                raise ValueError("face attributes: string") from None
            pos += size
        if pos + 4 > end:
            raise ValueError("face attributes: groups")
        (n_groups,) = struct.unpack_from("<I", view, pos)
        pos += 4
        if n_groups > n_entries or n_groups > end:
            raise ValueError("face attributes: groups")
        self._strings = strings
        self._n_entries = n_entries
        self._group_of = None
        self._row_of = None
        if n_groups > 1:
            width = 2 if n_groups <= 0xFFFF else 4
            dtype = "<u2" if width == 2 else "<u4"
            if pos + width * n_entries + 4 * n_entries > end:
                raise ValueError("face attributes: index")
            self._group_of = np.frombuffer(raw, dtype=dtype, count=n_entries,
                                           offset=pos)
            pos += width * n_entries
            self._row_of = np.frombuffer(raw, dtype="<i4", count=n_entries,
                                         offset=pos)
            pos += 4 * n_entries
            if self._group_of.size and int(self._group_of.max()) >= n_groups:
                raise ValueError("face attributes: index")
            if self._row_of.size and int(self._row_of.min()) < 0:
                raise ValueError("face attributes: index")
        self._groups = []
        total = 0
        for _ in range(n_groups):
            pos, rows, node, columns = self._read_group(view, pos)
            total += rows
            self._groups.append((rows, node, columns))
        if total != n_entries:
            raise ValueError("face attributes: rows")
        self._columns: dict = {}
        self._builders: dict = {}

    def _read_group(self, view, pos):
        import struct

        import numpy as np

        end = len(view)
        if pos + 4 > end:
            raise ValueError("face attributes: group")
        (n_rows,) = struct.unpack_from("<I", view, pos)
        pos += 4
        if n_rows > self._n_entries:
            raise ValueError("face attributes: group")
        node, pos = self._read_node(view, pos, 0)
        columns: list = []
        for leaf, length in _attrs_specs(node):
            if leaf == _L_FLOAT:
                width, dtype = 4, "<f4"
            elif leaf == _L_INT:
                width, dtype = 8, "<i8"
            elif leaf == _L_BOOL:
                width, dtype = 1, "|u1"
            elif leaf == _L_STR:
                width, dtype = 4, "<i4"
            else:
                columns.append(None)
                continue
            size = width * n_rows * (length or 1)
            if pos + size > end:
                raise ValueError("face attributes: column")
            arr = np.frombuffer(self._blob, dtype=dtype,
                                count=size // np.dtype(dtype).itemsize,
                                offset=pos)
            pos += size
            if length:
                # Written planar; the reader wants one row per entry.
                arr = np.ascontiguousarray(arr.reshape(length, n_rows).T)
            columns.append(arr)
        return pos, n_rows, node, columns

    def _read_node(self, view, pos, depth):
        import struct

        if depth > _ATTRS_MAX_DEPTH:
            raise ValueError("face attributes: nesting")
        end = len(view)
        if pos + 1 > end:
            raise ValueError("face attributes: node")
        kind = view[pos]
        pos += 1
        if kind == _N_LEAF:
            if pos + 1 > end or view[pos] > _L_EMPTY_LIST:
                raise ValueError("face attributes: leaf")
            return (_N_LEAF, int(view[pos])), pos + 1
        if kind == _N_VECTOR:
            if pos + 3 > end:
                raise ValueError("face attributes: vector")
            leaf, length = struct.unpack_from("<BH", view, pos)
            if leaf not in (_L_FLOAT, _L_INT) or not length:
                raise ValueError("face attributes: vector")
            return (_N_VECTOR, leaf, length), pos + 3
        if kind not in (_N_DICT, _N_LIST) or pos + 2 > end:
            raise ValueError("face attributes: node")
        (count,) = struct.unpack_from("<H", view, pos)
        pos += 2
        if kind == _N_DICT:
            items = []
            for _ in range(count):
                if pos + 2 > end:
                    raise ValueError("face attributes: node")
                (k,) = struct.unpack_from("<H", view, pos)
                pos += 2
                if k >= len(self._strings):
                    raise ValueError("face attributes: key")
                child, pos = self._read_node(view, pos, depth + 1)
                items.append((self._strings[k], child))
            return (_N_DICT, tuple(items)), pos
        kids = []
        for _ in range(count):
            child, pos = self._read_node(view, pos, depth + 1)
            kids.append(child)
        return (_N_LIST, tuple(kids)), pos

    # -- sequence ----------------------------------------------------------
    def __len__(self) -> int:
        return self._n_entries

    def __getitem__(self, k):
        return self.entry(k)

    def __eq__(self, other):
        if not isinstance(other, (list, tuple)):
            return NotImplemented
        return len(other) == len(self) and all(
            self.entry(i) == other[i] for i in range(len(self)))

    def __repr__(self) -> str:
        return f"<face attributes: {self._n_entries} entries>"

    def _where(self, k):
        import operator
        k = operator.index(k)
        if k < 0:
            k += self._n_entries
        if not 0 <= k < self._n_entries:
            raise IndexError(k)
        if self._group_of is None:
            return 0, k
        return int(self._group_of[k]), int(self._row_of[k])

    def _lists(self, g):
        """A group's columns as Python lists, built once (the bulk conversion
        is NumPy's C loop; per-row indexing stays in Python either way)."""
        got = self._columns.get(g)
        if got is not None:
            return got
        _rows, node, columns = self._groups[g]
        out: list = []
        for (leaf, _length), col in zip(_attrs_specs(node), columns):
            if col is None:
                out.append(None)
            elif leaf == _L_STR:
                strings = self._strings
                out.append([strings[i] for i in col.tolist()])
            elif leaf == _L_BOOL:
                out.append([bool(i) for i in col.tolist()])
            else:
                out.append(col.tolist())
        self._columns[g] = out
        return out

    def _builder(self, g):
        got = self._builders.get(g)
        if got is None:
            got = _attrs_builder(self._groups[g][1], self._lists(g))
            self._builders[g] = got
        return got

    def entry(self, k):
        """Entry ``k`` in the shape the JSON table had."""
        g, row = self._where(k)
        return _attrs_read(self._groups[g][1], self._lists(g), 0, row)[0]

    def attrs(self, k):
        """Entry ``k`` already as ``face.attrs``: what a mesh wants."""
        g, row = self._where(k)
        return self._builder(g)(row)

    def attrs_for(self, indices) -> list:
        """``face.attrs`` for every face, from the block's ``face_attr``
        array (-1 = no attributes). One group — the common case — skips the
        index lookup entirely."""
        if self._group_of is None:
            build = self._builder(0)
            return [build(k) if k >= 0 else None for k in indices.tolist()]
        return [self.attrs(k) if k >= 0 else None for k in indices.tolist()]


def _unpack_face_attrs(raw: bytes) -> _FaceAttrs:
    """The table :func:`_pack_face_attrs` wrote. Every length and index is
    checked against the bytes that are actually there, so a damaged or
    crafted blob fails with a ValueError instead of building garbage."""
    return _FaceAttrs(raw)


def _pack_plan(mesh, plan, sink: dict) -> dict:
    """:func:`_pack_geometry` of the mesh a deferred ``mesh`` would build
    (``plan``, core.lazy_mesh), from its arrays: the same point numbering,
    rings, attribute and layer tables, flags — the same bytes."""
    import numpy as np
    from core.topology import _maximal_holes

    src = mesh.__dict__["_deferred_source"]
    corners_v = plan.corners
    sizes = plan.ring_sizes
    counts = plan.ring_counts
    # Faces with more than one hole drop the nested ones, as the object
    # writer does (by their positions).
    if len(counts) and (counts > 2).any():
        rs = np.concatenate([[0], np.cumsum(sizes)])
        fr = np.concatenate([[0], np.cumsum(counts)])
        keep_ring = np.ones(len(sizes), dtype=bool)
        for f in np.flatnonzero(counts > 2).tolist():
            hk = list(range(int(fr[f]) + 1, int(fr[f + 1])))
            pos = [[QVector3D(*plan.pos[i]) for i in
                    corners_v[int(rs[k]):int(rs[k + 1])].tolist()]
                   for k in hk]
            kept = {id(x) for x in _maximal_holes(pos)}
            for k, p in zip(hk, pos):
                keep_ring[k] = id(p) in kept
        if not keep_ring.all():
            corners_v = corners_v[np.repeat(keep_ring, sizes)]
            ring_face = np.repeat(np.arange(len(counts)), counts)
            counts = np.bincount(ring_face[keep_ring],
                                 minlength=len(counts))
            sizes = sizes[keep_ring]
    corners = np.concatenate([plan.edges.reshape(-1), corners_v]) \
        if len(plan.edges) else corners_v
    _u, first, inverse = np.unique(corners, return_index=True,
                                   return_inverse=True)
    order = np.argsort(first, kind="stable")
    rank = np.empty_like(order)
    rank[order] = np.arange(len(order))
    index = rank[inverse.reshape(-1)].astype(np.int32)
    pos = plan.pos[corners[first[order]]].astype(np.float32).reshape(-1, 3)
    if not np.isfinite(pos).all():
        raise NonFiniteDocumentError("geometry")
    # The attribute table, renumbered in the order faces first use it.
    raw = src["meta"].get("face_attrs") or []
    fa_src = np.asarray(src["face_attr"], dtype=np.int64)
    table: list = []
    table_index: dict = {}
    remap: dict = {}
    if len(fa_src):
        u, firsts = np.unique(fa_src, return_index=True)
        for k in u[np.argsort(firsts, kind="stable")].tolist():
            attrs = _face_attrs_from_json(raw[k]) if k >= 0 else None
            js = _face_attrs_json(SimpleNamespace(attrs=attrs)) \
                if attrs else None
            if js:
                key = json.dumps(js, sort_keys=True, separators=(",", ":"))
                t = table_index.get(key)
                if t is None:
                    t = table_index[key] = len(table)
                    table.append(js)
                remap[k] = t
            else:
                remap[k] = -1
    keys = np.array(sorted(remap), dtype=np.int64)
    vals = np.array([remap[k] for k in keys.tolist()], dtype=np.int32)
    face_attr = vals[np.searchsorted(keys, fa_src)] if len(fa_src) else \
        np.zeros(0, dtype=np.int32)
    ne = len(plan.edges)
    arrays = {
        "pos": pos,
        "edges": index[:2 * ne].reshape(-1, 2),
        "rings": index[2 * ne:],
        "ring_sizes": np.asarray(sizes, dtype=np.int32),
        "ring_counts": np.asarray(counts, dtype=np.int32),
        "face_attr": face_attr.astype(np.int32),
    }
    flags = (plan.soft.astype(np.uint8) | (plan.hidden.astype(np.uint8) << 1))
    arrays["edge_flags"] = flags
    if any(c is not None for c in plan.curve):
        arrays["edge_curve"] = np.array(
            [-1 if c is None else c for c in plan.curve], dtype=np.int64)
    layer_table: list = []
    if any(l is not None for l in plan.layer):
        layer_index: dict = {}
        layers = np.full(ne, -1, dtype=np.int32)
        for i, l in enumerate(plan.layer):
            if l is not None:
                k = layer_index.get(l)
                if k is None:
                    k = layer_index[l] = len(layer_table)
                    layer_table.append(l)
                layers[i] = k
        arrays["edge_layer"] = layers
    return _write_geometry(arrays, table, layer_table, sink)


def save_scene(scene, path: Path,
               thumbnail_bytes: bytes | None = None,
               *, binary: bool | None = None) -> dict:
    """Write ``scene`` to ``path``. Returns ``{"embedded", "missing"}``: how
    many texture images were packed into the document, and how many could not
    be read (those keep pointing at their original path). The thumbnail is
    not counted as a texture.

    When ``thumbnail_bytes`` is given it goes into ``meta/thumbnail.png`` and
    the document is written as a ZIP even when it has no textures. That is the
    member Windows Explorer's thumbnail handler reads. Without a preview the
    common case stays plain JSON at format 1.

    ``binary`` overrides the size-based choice of format 3: ``True`` writes
    the big meshes as binary blocks even for a small document (a component
    cache is one model, so its element count never reaches the document
    threshold), ``False`` keeps JSON. ``None`` — the default — keeps the
    historical rule, so nothing changes for a normal save.
    """
    # Accept a Scene or a bare Mesh (the M1 read-compat path feeds a Mesh).
    mesh = scene.mesh if hasattr(scene, "mesh") else scene
    # Decided BEFORE anything is serialized: a large document writes its
    # big meshes as binary blocks (format 3) and never builds their JSON.
    large = _live_element_count(scene) > _LARGE_DOCUMENT
    if binary is not None:
        large = bool(binary)
    geom: dict | None = _GeomSink() if large else None
    payload = _mesh_json(mesh, geom)
    groups = getattr(scene, "groups", None)
    kept = getattr(scene, "kept_components", None)
    if groups or kept:
        # Component prototypes: each shared instance mesh is written ONCE —
        # including the ones only NESTED placements reference, which is what
        # keeps a component's internal repetition (the hedge: 9600 faces
        # placed 48 times) from being written out 48 times over.
        proto_index: dict = {}
        protos: list = []

        def _entry(g):
            ext = getattr(g, "ext", None)
            link = ext.get("igz_link") if isinstance(ext, dict) else None
            if isinstance(link, dict):
                # An external reference (a model a library owns): the
                # document keeps WHERE it lives and HOW it is placed, never
                # its geometry. The empty mesh is deliberate — a reader that
                # predates this key opens the file and simply shows nothing
                # there, instead of failing on a group it cannot build.
                entry = _mesh_json(Mesh(), geom)
                entry["link"] = json.loads(json.dumps(link, default=str))
                xf = getattr(g, "xform", None)
                if xf is not None:
                    entry["xform"] = [float(x) for x in xf.data()]
            else:
                xf = getattr(g, "xform", None)
                if xf is not None:
                    idx = proto_index.get(id(g.mesh))
                    if idx is None:
                        idx = proto_index[id(g.mesh)] = len(protos)
                        protos.append(None)          # reserve: recursion is depth
                        protos[idx] = _mesh_json(g.mesh, geom)
                    entry = {"proto": idx,
                             "xform": [float(x) for x in xf.data()]}
                    # Group or component (issue #90): a group of groups and a
                    # copied group carry a matrix too. Written for EVERY
                    # instance — a file without the key is an older one, which
                    # the reader tells apart its own way. Older readers ignore it.
                    entry["component"] = bool(getattr(g, "component", True))
                else:
                    entry = _mesh_json(g.mesh, geom)
            # The name — never written until 2026-09-11, so every reopened
            # document renumbered its groups and a "Pérgola" came back as
            # "Group 7". Older readers ignore the key.
            if getattr(g, "name", None):
                entry["name"] = g.name
            axes = getattr(g, "axes", None)
            if axes is not None:
                # A classic group's own axes (issue #44), column-major like
                # "xform"; older readers ignore the key.
                entry["axes"] = [float(x) for x in axes.data()]
            if getattr(g, "layer", None) is not None:
                entry["layer"] = g.layer
            if getattr(g, "ifc", None):
                entry["ifc"] = dict(g.ifc)
            if getattr(g, "billboard", False):
                # True = legacy textured-quad face-me; "mesh" = imported
                # silhouette whose real geometry turns toward the camera.
                entry["billboard"] = g.billboard
            if getattr(g, "material", None):
                # The container's own paint (issue #47); older readers
                # ignore the key and show the faces in the default.
                entry["material"] = dict(g.material)
            if getattr(g, "text3d", None):
                # A 3D text keeps what it was made from, so it reopens
                # editable. Older readers ignore the key.
                entry["text3d"] = dict(g.text3d)
            if getattr(g, "ext", None):
                # Extensions' parameters for this container (JSON-safe by
                # contract); older readers ignore the key.
                entry["ext"] = json.loads(json.dumps(g.ext, default=str))
            if getattr(g, "uid", None):
                # The identity a scene's hidden-object list names.
                entry["uid"] = g.uid
            if getattr(g, "hidden", False):
                entry["hidden"] = True
            if getattr(g, "locked", False):
                entry["locked"] = True          # older readers ignore it
            if getattr(g, "exploded", None):
                # An exploded view and each part's share of it, so the
                # document reopens able to reassemble (core/explode.py).
                # Older readers ignore both and see the parts where they
                # stand.
                entry["exploded"] = dict(g.exploded)
            if getattr(g, "explode_offset", None):
                entry["explode_offset"] = list(g.explode_offset)
            kids = getattr(g, "children", None)
            if kids and not isinstance(link, dict):
                # A link's children belong to the library definition: they
                # come back with it, not from the document.
                entry["children"] = [_entry(c) for c in kids]
            return entry

        payload["groups"] = [_entry(g) for g in groups or ()]
        if kept:
            # Definitions kept with no copy placed: written like instances
            # through the SAME prototype table, so one still in use is not
            # written twice. Older readers ignore the key (and lose them).
            payload["kept_components"] = [_entry(t) for t in kept]
        if protos:
            payload["protos"] = protos
    layers = getattr(scene, "layers", None)
    if layers is not None and (len(layers) > 1 or any(
            not ly.visible or ly.locked or ly.has_style()
            for ly in layers)):
        payload["layers"] = [ly.to_dict() for ly in layers]
    # Older readers ignore both keys: new objects simply go to the default
    # layer there, and the layers show as one flat list.
    if getattr(scene, "active_layer", None):
        payload["active_layer"] = scene.active_layer
    folders = getattr(scene, "layer_folders", None)
    if folders:
        payload["layer_folders"] = list(folders)
    from core.layers import folder_parent
    parents = {f: folder_parent(scene, f) for f in folders or ()
               if folder_parent(scene, f)}
    if parents:
        payload["layer_folder_parents"] = parents
    views = getattr(scene, "saved_views", None)
    if views:
        payload["saved_views"] = [v.to_dict() for v in views]
    comps = getattr(scene, "compositions", None)
    if comps:
        payload["compositions"] = [c.to_dict() for c in comps]
    dims = getattr(scene, "dimensions", None)
    if dims:
        payload["dimensions"] = [
            {"a": [d.a.x(), d.a.y(), d.a.z()],
             "b": [d.b.x(), d.b.y(), d.b.z()],
             "offset": [d.offset.x(), d.offset.y(), d.offset.z()],
             **({"axis": d.axis} if getattr(d, "axis", None) else {}),
             **({"layer": d.layer} if getattr(d, "layer", None) else {}),
             **({"text": d.text} if getattr(d, "text", None) else {})}
            for d in dims
        ]
    mats = getattr(scene, "materials", None)
    if mats:
        payload["materials"] = [m.to_dict() for m in mats.values()]
    style = getattr(scene, "dimension_style", None)
    if style:
        payload["dimension_style"] = dict(style)
    cam = getattr(scene, "camera_home", None)
    if isinstance(cam, dict) and _non_finite_where(cam) == "scene":
        payload["camera"] = dict(cam)      # what the author was looking at
    # A camera holding a NaN is left out instead of refusing the save: it is
    # only the view, and the file opens framed on the model (#485). The
    # geometry keeps its own guard below.
    views = getattr(scene, "views_home", None)
    if isinstance(views, dict) and _non_finite_where(views) == "scene":
        payload["views"] = dict(views)
    units = getattr(scene, "units", None)
    if isinstance(units, dict) and units != {"length": "m", "precision": 2}:
        payload["units"] = dict(units)     # only when not the metre default
    pdata = getattr(scene, "plugin_data", None)
    if pdata:
        # Extensions' data: JSON-safe by contract; a value that is not is
        # dropped with its key rather than breaking the save.
        import json as _json
        keep = {}
        for key, value in pdata.items():
            try:
                keep[str(key)] = _json.loads(_json.dumps(value))
            except (TypeError, ValueError):
                continue
        if keep:
            payload["plugin_data"] = keep
    scales = getattr(scene, "custom_scales", None)
    if scales:
        payload["custom_scales"] = [float(n) for n in scales]
    back = getattr(scene, "back_face_color", None)
    if back:
        payload["back_face_color"] = list(back)
    splanes = getattr(scene, "section_planes", None)
    if splanes:
        payload["section_planes"] = [sp.to_dict() for sp in splanes]
        vis = {}
        if not getattr(scene, "show_section_planes", True):
            vis["planes_hidden"] = True
        if not getattr(scene, "show_section_cuts", True):
            vis["cuts_hidden"] = True
        if vis:
            payload["section_view"] = vis
    shown = {}
    if getattr(scene, "show_hidden_objects", False):
        shown["objects"] = True
    if getattr(scene, "show_hidden_geometry", False):
        shown["geometry"] = True
    if shown:
        payload["hidden_view"] = shown       # View ▸ Hidden Objects / Geometry
    if not getattr(scene, "show_axes", True):
        payload["axes_hidden"] = True        # Camera ▸ Axes (shown is implicit)
    dstyle = getattr(scene, "display_style", None)
    if dstyle is not None:
        from core.style import Style
        d = dstyle.to_dict()
        if d != Style().to_dict():   # default stays implicit (terse files)
            payload["display_style"] = d
    shadows = getattr(scene, "shadows", None)
    if shadows is not None:
        from core.sun import ShadowSettings
        d = shadows.to_dict()
        if d != ShadowSettings().to_dict():
            payload["shadows"] = d
    # Georeferencing datum (Track G) — optional block, written only when set so
    # ungeoreferenced documents stay terse and older readers ignore it.
    datum = getattr(scene, "georef", None)
    if datum is not None:
        payload["georef"] = {"datum": datum.to_dict()}
    # Base-map capture (Track G, G1). Only the capture rectangle and the
    # source, never the tiles — see TileLayer.to_dict.
    tile_layer = getattr(scene, "tile_layer", None)
    if tile_layer is not None:
        payload["tile_layer"] = tile_layer.to_dict()
    paths = getattr(scene, "geo_paths", None)
    if paths:
        payload["geo_paths"] = [p.to_dict() for p in paths]
    points = getattr(scene, "geo_points", None)
    if points:
        payload["geo_points"] = [p.to_dict() for p in points]
    labels = getattr(scene, "text_labels", None)
    if labels:
        payload["text_labels"] = [t.to_dict() for t in labels]
    guides = getattr(scene, "guides", None)
    if guides:
        # A guide at NaN is left out instead of refusing the save (#723):
        # it is only scaffolding, and the loader drops it anyway (#185).
        payload["guides"] = [g.to_dict() for g in guides
                             if not hasattr(g, "is_finite") or g.is_finite()]
    # Reference images. Written BEFORE the packing step below on purpose:
    # each entry hangs its file under a "texture" key, so the same walk that
    # embeds face textures embeds the scans too.
    images = getattr(scene, "image_planes", None)
    if images:
        payload["image_planes"] = [im.to_dict() for im in images]
    # Images ride INSIDE the document (see the module docstring). Only a scene
    # that actually has textures pays for the container; everything else stays
    # plain JSON at format 1, readable by older builds.
    blobs, missing = _pack_textures(payload)
    # The Explorer preview travels with the document for the same reason the
    # textures do: a .png sitting next to the .igz is one move away from being
    # lost, and IThumbnailProvider only receives the document itself.
    if thumbnail_bytes:
        blobs[_THUMB_ENTRY] = thumbnail_bytes
    # The photogrammetric survey (Track G, G6) rides inside the document too,
    # for the same reason the textures do: a reference mesh that lives in a
    # folder next to the .igz is one move away from being lost.
    survey = getattr(scene, "photo_mesh", None)
    if survey is not None and getattr(survey, "triangle_count", 0):
        from georef.photomesh import pack_mesh
        meta, survey_blobs = pack_mesh(survey)
        payload["photo_mesh"] = meta
        blobs.update(survey_blobs)
    data = {
        "igz_format": (ATTRS_FORMAT if geom and geom.binary_attrs else
                       GEOMETRY_FORMAT if geom else
                       CONTAINER_FORMAT if blobs else PLAIN_FORMAT),
        "app_version": __version__,
        "scene": payload,
    }
    try:
        if large:
            doc = json.dumps(data, separators=(",", ":"), allow_nan=False)
        else:
            doc = json.dumps(data, indent=2, allow_nan=False)
    except ValueError:
        # A NaN or an infinity in a coordinate (#185). Python would write
        # it as the bare word NaN — not JSON, and a broken shape for good.
        # Refuse, and leave the file on disk as it was.
        raise NonFiniteDocumentError(_non_finite_where(payload)) from None
    if blobs or geom:
        _write_container(path, doc, blobs, fast=large, deflated=geom)
    else:
        _write_atomic(path, doc.encode("utf-8"))
    # ``embedded`` keeps counting textures only: the save dialog says
    # "texture(s) packed", and a thumbnail is not one.
    return {"embedded": len(blobs) - int(bool(thumbnail_bytes)),
            "missing": missing}


def read_thumbnail(path: Path | str) -> bytes | None:
    """The embedded PNG preview, without parsing the 3D scene. ``None`` for a
    plain-JSON document or one saved without a preview."""
    path = Path(path)
    if not path.is_file():
        return None
    try:
        with open(path, "rb") as f:
            if f.read(4) != _ZIP_MAGIC:
                return None
        import zipfile
        from core import zip_limits
        with zipfile.ZipFile(path) as zf:
            for name in (_THUMB_ENTRY, "thumbnail.png", "thumb.png"):
                try:
                    return zip_limits.read(zf, name)
                except KeyError:
                    continue
    except Exception:                    # noqa: BLE001 — no preview is not fatal
        return None
    return None


def _live_element_count(scene) -> int:
    """Faces + edges the document will hold: the loose mesh, and every
    distinct mesh of the groups (a component prototype is written once,
    however many times it is placed). Only list lengths."""
    from core.lazy_mesh import entity_count
    mesh = scene.mesh if hasattr(scene, "mesh") else scene
    total = entity_count(mesh)
    seen: set = set()
    stack = (list(getattr(scene, "groups", None) or ())
             + list(getattr(scene, "kept_components", None) or ()))
    while stack:
        g = stack.pop()
        m = getattr(g, "mesh", None)
        if m is not None and id(m) not in seen:
            seen.add(id(m))
            total += entity_count(m)
        stack.extend(getattr(g, "children", None) or ())
    return total


class NonFiniteDocumentError(ValueError):
    """The document holds a coordinate that is not a number; it is not
    written, so the file on disk keeps its last good version."""

    def __init__(self, where: str) -> None:
        from core.i18n import tr
        self.where = where
        super().__init__(tr(
            "The model has a point with invalid coordinates (not a number), "
            "so it was not saved and the file on disk keeps its last good "
            "version. Undo the last step and save again. Where: {where}",
            where=where))


def _non_finite_where(node, path: str = "scene") -> str:
    """The first place in the payload holding a NaN or an infinity."""
    import math as _math
    stack = [(node, path)]
    while stack:
        cur, here = stack.pop()
        if isinstance(cur, float) and not _math.isfinite(cur):
            return here
        if isinstance(cur, dict):
            stack.extend((v, f"{here} › {k}") for k, v in
                         reversed(list(cur.items())))
        elif isinstance(cur, (list, tuple)):
            stack.extend((v, f"{here}[{i}]") for i, v in
                         reversed(list(enumerate(cur))))
    return path


def _write_atomic(path: Path, data: bytes) -> None:
    """Write via a sibling temp file + rename: a failure mid-write must not
    leave the user's existing document truncated."""
    tmp = path.with_name(path.name + ".part")
    try:
        tmp.write_bytes(data)
        tmp.replace(path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


def _write_container(path: Path, doc: str, blobs: dict,
                     fast: bool = False, deflated: dict | None = None) -> None:
    """The ZIP shape: ``document.json`` deflated, images stored as-is (PNG/JPG
    are already compressed — deflating them again costs time for nothing).
    ``fast`` deflates at level 1 (see ``_LARGE_DOCUMENT``). ``deflated``
    holds members compressed like the document — the geometry blocks."""
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        info = zipfile.ZipInfo(_DOC_ENTRY, date_time=_ZIP_EPOCH)
        info.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(info, doc, compresslevel=1 if fast else None)
        for member in sorted(deflated or ()):
            info = zipfile.ZipInfo(member, date_time=_ZIP_EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, deflated[member],
                        compresslevel=1 if fast else None)
        for member in sorted(blobs):
            info = zipfile.ZipInfo(member, date_time=_ZIP_EPOCH)
            info.compress_type = zipfile.ZIP_STORED
            zf.writestr(info, blobs[member])
    _write_atomic(path, buf.getvalue())


def _parse_json(text, pump=None):
    """``json.loads`` — in a worker thread while ``pump`` keeps the window
    answering, when given. A 3.3 GB document took 24 s in one call, and the
    desktop flagged IngeTrazo as «not responding» after five (Marco, 01-10,
    the model of #158); the parser lets the main thread in every ~0.4 s."""
    if pump is None:
        return json.loads(text, parse_constant=_note_constant)
    import threading
    box: dict = {}

    def work():
        try:
            box["data"] = json.loads(text, parse_constant=_note_constant)
        except BaseException as exc:  # noqa: BLE001 — re-raised below
            box["error"] = exc
    th = threading.Thread(target=work, daemon=True)
    th.start()
    while th.is_alive():
        th.join(0.1)
        pump()
    if "error" in box:
        raise box["error"]
    return box["data"]


def _read_document(path: Path, pump=None):
    """``(data, archive)`` for a document of either shape — the archive is
    ``None`` for a plain-JSON one, and stays open while the caller extracts
    embedded images."""
    raw = path.read_bytes()
    if not raw.startswith(_ZIP_MAGIC):
        return _parse_json(raw.decode("utf-8"), pump), None
    import zipfile
    from core import zip_limits
    archive = zipfile.ZipFile(path)
    try:
        # Every later read (geometry blocks, textures, the survey) is from
        # this archive: one check covers them all.
        zip_limits.check(archive, path.name)
    except zipfile.BadZipFile:
        archive.close()
        raise
    try:
        data = _parse_json(archive.read(_DOC_ENTRY).decode("utf-8"), pump)
    except KeyError:
        archive.close()
        raise ValueError(
            f"{path.name} is not an IngeTrazo document (no {_DOC_ENTRY}).")
    return data, archive


def _unpack_photo_mesh(payload: dict, archive):
    """Rebuild the stored survey, or ``None`` when the document has none."""
    meta = payload.get("photo_mesh")
    if not meta:
        return None
    from georef.photomesh import unpack_mesh

    def read_blob(member: str) -> bytes:
        try:
            return archive.read(member)
        except KeyError:
            return b""

    return unpack_mesh(meta, read_blob)


def load_into(scene, path: Path, progress=None) -> None:
    """Replace ``scene`` contents with what's stored at ``path``.

    ``progress(fraction, text)``, when given, is called at the loader's
    milestones so the window can show a bar: a big document took seconds
    with nothing on screen and read as frozen (issue #59, @pacaeiro)."""
    import gc

    # Mass object construction ahead — see formats.skp.apply_payload: the
    # generational GC re-scanning the growing heap can dominate big loads.
    _gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        _load_into_inner(scene, path, progress)
        # First-party: os vínculos do TrazoMob são reconstruídos aqui, sem
        # gancho. A leitura não depende do motor — um documento salvo com
        # vínculos precisa abrir mesmo com o TrazoMob desligado.
        from trazomob.integrations import library_links
        library_links.rebuild_scene_links(scene)
    finally:
        if _gc_was_enabled:
            gc.enable()


#: Entities left out of the document being opened because a coordinate
#: is not a number (NaN / inf) — counted per load, reported on the scene.
_dropped_nonfinite = [0]
#: Whether the document text holds any NaN / Infinity at all. The JSON
#: parser reports them as it reads (``parse_constant``), so a clean
#: document — nearly every one — skips the per-coordinate check entirely.
_saw_nonfinite = [False]


def _note_constant(token: str) -> float:
    _saw_nonfinite[0] = True
    return float(token)


def _finite_points(*points) -> bool:
    try:
        return all(math.isfinite(float(c)) for p in points for c in p)
    except (TypeError, ValueError):
        return False


def _without_nonfinite(payload: dict) -> dict:
    """The mesh block minus the edges and faces with a NaN or infinite
    coordinate. One such corner made the WHOLE document unopenable
    («cannot convert float NaN to integer», #185): the rest of the model
    opens, the damaged pieces are left out and counted."""
    if not _saw_nonfinite[0]:
        return payload
    edges = [r for r in payload.get("edges", [])
             if _finite_points(r.get("a", ()), r.get("b", ()))]
    faces = [r for r in payload.get("faces", [])
             if _finite_points(*r.get("vertices", ()),
                               *(p for h in r.get("holes", []) for p in h))]
    dropped = (len(payload.get("edges", [])) - len(edges)
               + len(payload.get("faces", [])) - len(faces))
    if not dropped:
        return payload
    _dropped_nonfinite[0] += dropped
    return dict(payload, edges=edges, faces=faces)


def _normalize_text_curve_ids(payload: dict, geom: dict) -> None:
    """Map stored text curve identities to the engine's integer identities.

    JSON documents can carry named curves. Their segments must stay grouped,
    but the engine's counter and binary geometry writer require integer ids.
    Reserve the document's existing integers first, including binary meshes
    loaded later, so a name cannot collide with an existing numeric curve.
    """
    import core.mesh as _mesh_mod

    def group_meshes(groups, depth=0):
        for raw in groups:
            if not isinstance(raw, dict):
                continue
            # A placement uses its prototype, not any local geometry block.
            if raw.get("xform") is None or "proto" not in raw:
                yield raw
            if depth < 32:             # the same limit as _group_from
                yield from group_meshes(raw.get("children", []) or [],
                                        depth + 1)

    def meshes():
        yield payload
        yield from payload.get("protos", [])
        yield from group_meshes(payload.get("groups", []) or [])
        yield from group_meshes(payload.get("kept_components", []) or [])

    text_edges = []
    binary_meshes = []
    top = _mesh_mod._CURVE_COUNTER - 1
    for block in meshes():
        if "geom" in block:
            binary_meshes.append(block["geom"])
            continue
        for raw in block.get("edges", []):
            cid = raw.get("curve")
            if isinstance(cid, str):
                text_edges.append(raw)
            elif isinstance(cid, int):
                top = max(top, cid)
    if not text_edges:
        return                         # no extra scan of ordinary binary meshes

    for meta in binary_meshes:
        curves = _document_geometry_arrays(meta, geom).get("edge_curve")
        if curves is not None and curves.size:
            top = max(top, int(curves.max()))
    _mesh_mod._CURVE_COUNTER = top + 1
    ids: dict[str, int] = {}
    for raw in text_edges:
        name = raw["curve"]
        if name not in ids:
            ids[name] = Mesh.next_curve_id()
        raw["curve"] = ids[name]


def _load_into_inner(scene, path: Path, progress=None) -> None:
    def tick(frac, text):
        if progress is not None:
            progress(frac, text)

    _dropped_nonfinite[0] = 0
    _saw_nonfinite[0] = False

    tick(0.05, "Reading the document…")
    data, archive = _read_document(
        path, pump=(lambda: tick(0.1, "Reading the document…"))
        if progress is not None else None)
    survey = None
    geom: dict = {}
    try:
        if archive is not None:
            # Format 3's binary geometry blocks, read while the archive is
            # open (it closes below).
            geom = {n: archive.read(n) for n in archive.namelist()
                    if n.startswith(_GEOM_PREFIX)}
            tick(0.2, "Unpacking textures…")
            _unpack_textures(data.get("scene", {}), archive)
            # Rebuilt here, while the archive is still open — it closes below
            # and the survey's blobs live inside it.
            survey = _unpack_photo_mesh(data.get("scene", {}), archive)
    finally:
        if archive is not None:
            archive.close()
    fmt = data.get("igz_format", 1)
    if fmt > CURRENT_FORMAT:
        raise ValueError(
            f"Document format v{fmt} is newer than this build (v{CURRENT_FORMAT})."
        )

    payload = data.get("scene", {})
    _normalize_text_curve_ids(payload, geom)

    scene.mesh.clear()
    scene.selection.clear()
    scene.groups.clear()
    scene.geo_paths.clear()
    scene.geo_points.clear()
    scene.text_labels.clear()
    scene.dimensions.clear()
    scene.georef = None
    scene.photo_mesh = survey
    scene.tile_layer = None
    # The writer leaves a block out when it holds the default (no planes,
    # nothing hidden, no own scales…), so what the file does not bring is
    # reset here — or it leaked from the document open before (#602).
    from core.layers import DEFAULT_LAYER, Layer
    scene.layers = [Layer(DEFAULT_LAYER)]
    scene.active_layer = None
    scene.layer_folders = []
    scene.folder_parents = {}
    scene.section_planes = []
    scene.show_section_planes = True
    scene.show_section_cuts = True
    scene.show_hidden_objects = False
    scene.show_hidden_geometry = False
    scene.show_axes = True
    scene.custom_scales = []
    scene.back_face_color = None
    from core.scene import Scene
    scene.dimension_style = \
        Scene.__dataclass_fields__["dimension_style"].default_factory()

    tick(0.35, "Building geometry…")
    _load_mesh(scene.mesh, payload, geom)
    raw_layers = payload.get("layers")
    if raw_layers:
        from core.layers import DEFAULT_LAYER, Layer
        scene.layers = [Layer.from_dict(r) for r in raw_layers]
        if not any(ly.name == DEFAULT_LAYER for ly in scene.layers):
            scene.layers.insert(0, Layer(DEFAULT_LAYER))
    active = payload.get("active_layer")
    if isinstance(active, str) and scene.layer(active) is not None:
        scene.active_layer = active
    raw_folders = payload.get("layer_folders")
    if isinstance(raw_folders, list):
        scene.layer_folders = [f for f in raw_folders
                               if isinstance(f, str) and f]
    raw_parents = payload.get("layer_folder_parents")
    if isinstance(raw_parents, dict):
        scene.folder_parents = {f: p for f, p in raw_parents.items()
                                if isinstance(f, str) and isinstance(p, str)}
    raw_tiles = payload.get("tile_layer")
    if raw_tiles:
        from georef.tiles import TileLayer
        try:
            scene.tile_layer = TileLayer.from_dict(raw_tiles)
        except Exception:  # noqa: BLE001 — a bad block costs the map, not the file
            scene.tile_layer = None
    from core.materials import Material
    scene.materials = {}
    for raw in payload.get("materials", []):
        mat = Material.from_dict(raw)
        if mat.name:
            scene.materials[mat.name] = mat
    from core.saved_views import SavedView
    scene.saved_views = [SavedView.from_dict(r)
                         for r in payload.get("saved_views", [])]
    from core.composition import Composicion
    scene.compositions = []
    for r in payload.get("compositions", []):
        # A sheet this version cannot rebuild must not take the model down
        # with it: keep the others, log the one that failed.
        try:
            scene.compositions.append(Composicion.from_dict(r))
        except Exception as exc:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).warning(
                "sheet %r skipped: %s", r.get("name", "?"), exc)
    proto_meshes: list = []
    import time as _time
    raw_protos = payload.get("protos", [])
    last = _time.monotonic()
    for k, raw in enumerate(raw_protos):
        m = Mesh()
        _load_mesh(m, raw, geom)
        proto_meshes.append(m)
        if _time.monotonic() - last > 0.25:
            # Thousands of components took 25 s here without a word to the
            # window, which the desktop reads as a hang (#158).
            tick(0.35 + 0.25 * k / max(1, len(raw_protos)),
                 "Building geometry…")
            last = _time.monotonic()
    names: list = []

    def _group_from(raw, depth=0):
        name = raw.get("name") or None
        if name:
            names.append(name)
        linked = isinstance(raw.get("link"), dict)
        if linked:
            # An external reference: placed by its matrix, its geometry
            # arrives later — the extension that owns ``link`` rebuilds it.
            from PySide6.QtGui import QMatrix4x4
            group = Group(name=name)
            if raw.get("xform") is not None:
                vals = [float(x) for x in raw["xform"]]
                rm = [vals[col * 4 + row] for row in range(4) for col in range(4)]
                group.xform = QMatrix4x4(*rm)
        elif raw.get("xform") is not None and "proto" in raw:
            from PySide6.QtGui import QMatrix4x4
            group = Group(proto_meshes[int(raw["proto"])], name=name)
            vals = [float(x) for x in raw["xform"]]
            # data() is column-major; the constructor takes row-major.
            rm = [vals[col * 4 + row] for row in range(4) for col in range(4)]
            group.xform = QMatrix4x4(*rm)
        else:
            group = Group(name=name)
            _load_mesh(group.mesh, raw, geom)
        if isinstance(raw.get("axes"), list) and len(raw["axes"]) == 16:
            from PySide6.QtGui import QMatrix4x4
            vals = [float(x) for x in raw["axes"]]
            group.axes = QMatrix4x4(*[vals[col * 4 + row] for row in range(4)
                                      for col in range(4)])
        if raw.get("layer"):
            group.layer = raw["layer"]
        if raw.get("ifc"):
            group.ifc = dict(raw["ifc"])
        if raw.get("billboard"):
            group.billboard = raw["billboard"]   # True | "mesh"
        if isinstance(raw.get("text3d"), dict):
            group.text3d = dict(raw["text3d"])
        if isinstance(raw.get("ext"), dict):
            group.ext = raw["ext"]
        if raw.get("uid"):
            group.uid = str(raw["uid"])   # older documents keep the fresh one
        if raw.get("hidden"):
            group.hidden = True
        if raw.get("locked"):
            group.locked = True
        if isinstance(raw.get("material"), dict):
            group.material = dict(raw["material"])
        if isinstance(raw.get("exploded"), dict):
            group.exploded = dict(raw["exploded"])
        off = raw.get("explode_offset")
        if isinstance(off, list) and len(off) == 3:
            group.explode_offset = tuple(float(v) for v in off)
        if depth < 32 and not linked:   # a corrupt document must not spin
            group.adopt(_group_from(c, depth + 1)
                        for c in raw.get("children", []) or [])
        if "component" in raw:
            group.component = bool(raw["component"])
        elif any(isinstance(c, dict) and "xform" not in c
                 for c in raw.get("children", []) or []):
            # Saved before the key existed (issue #90): a container holding
            # a CLASSIC group can only be Make Group's — a .skp import
            # places every child with a matrix. A group, then.
            group.component = False
        return group

    # Every name the document itself stores, children included: the groups
    # it carries WITHOUT one are numbered continuing these, not the
    # session's counter — the same file must load to the same names
    # whatever was opened before it (issue #943).
    stored_names: list = []

    def _collect_name(raw, depth=0):
        if not isinstance(raw, dict):
            return
        if raw.get("name"):
            stored_names.append(raw["name"])
        if depth < 32:              # the same limit as _group_from
            for c in raw.get("children", []) or []:
                _collect_name(c, depth + 1)

    for raw in payload.get("groups", []) or []:
        _collect_name(raw)
    for raw in payload.get("kept_components", []) or []:
        _collect_name(raw)

    from core.group import document_name_scope
    raw_groups = payload.get("groups", []) or []
    with document_name_scope(stored_names):
        for i, raw in enumerate(raw_groups):
            if i % 50 == 0:
                tick(0.6 + 0.35 * i / max(1, len(raw_groups)),
                     "Placing groups…")
            scene.groups.append(_group_from(raw))
        scene.kept_components = [
            t for t in (_group_from(raw) for raw in
                        payload.get("kept_components", []) or []
                        if isinstance(raw, dict))
            if t.is_component()]
    tick(0.96, "Finishing…")
    if names:
        from core.group import reserve_group_names
        reserve_group_names(names)   # new groups never reuse a stored "Group N"

    # Until #765 every open-and-save doubled the dimensions: a file can hold
    # each one 128 times over (1024 entries for 8, reported). The copies
    # are identical entry for entry, so an entry equal to one already read
    # is dropped; two dimensions that differ in anything both stay.
    seen_dims: set = set()
    for raw in payload.get("dimensions", []):
        key = json.dumps(raw, sort_keys=True, default=str)
        if key in seen_dims:
            continue
        seen_dims.add(key)
        dim = Dimension(
            QVector3D(*raw["a"]), QVector3D(*raw["b"]),
            QVector3D(*raw["offset"]), layer=raw.get("layer") or None,
            text=raw.get("text") or None, axis=raw.get("axis") or None)
        dim.bind(scene)         # the vertex at that spot is the one snapped to
        scene.dimensions.append(dim)

    # A document from before the ends could be chosen drew oblique ticks:
    # it keeps them. Only a NEW document is born with arrows.
    style = payload.get("dimension_style")
    scene.dimension_style.update(
        {"ends": "tick", **(style if isinstance(style, dict) else {})})
    cam = payload.get("camera")
    scene.camera_home = dict(cam) if isinstance(cam, dict) else None
    views = payload.get("views")
    scene.views_home = dict(views) if isinstance(views, dict) else None
    from core.units import model_units_of
    scene.units = model_units_of(payload)   # validated; absent = metres
    pdata = payload.get("plugin_data")
    scene.plugin_data = dict(pdata) if isinstance(pdata, dict) else {}
    scales = payload.get("custom_scales")
    if isinstance(scales, list):
        scene.custom_scales = [float(n) for n in scales
                               if isinstance(n, (int, float)) and n > 0]

    back = payload.get("back_face_color")
    if isinstance(back, list) and len(back) == 3:
        scene.back_face_color = tuple(float(c) for c in back)

    # Defaults stay implicit in the file (terse), so a document WITHOUT the
    # block must reset the field — otherwise the previous document's look or
    # sun leaks into the one being opened.
    from core.style import Style
    dstyle = payload.get("display_style")
    scene.display_style = (Style.from_dict(dstyle)
                           if isinstance(dstyle, dict) else Style())

    from core.sun import ShadowSettings
    shadows = payload.get("shadows")
    scene.shadows = (ShadowSettings.from_dict(shadows)
                     if isinstance(shadows, dict) else ShadowSettings())

    raw_planes = payload.get("section_planes")
    if isinstance(raw_planes, list):
        from core.section import SectionPlane
        scene.section_planes = [SectionPlane.from_dict(r)
                                for r in raw_planes]
        # One active cut max: keep the FIRST marked active.
        seen_active = False
        for sp in scene.section_planes:
            if sp.active and seen_active:
                sp.active = False
            seen_active = seen_active or sp.active
    vis = payload.get("section_view")
    if isinstance(vis, dict):
        scene.show_section_planes = not vis.get("planes_hidden", False)
        scene.show_section_cuts = not vis.get("cuts_hidden", False)
    shown = payload.get("hidden_view")
    if isinstance(shown, dict):
        scene.show_hidden_objects = bool(shown.get("objects", False))
        scene.show_hidden_geometry = bool(shown.get("geometry", False))
    scene.show_axes = not bool(payload.get("axes_hidden", False))

    georef = payload.get("georef")
    if isinstance(georef, dict) and isinstance(georef.get("datum"), dict):
        scene.georef = SceneDatum.from_dict(georef["datum"])

    for raw in payload.get("geo_paths", []):
        scene.geo_paths.append(GeoPath.from_dict(raw))

    from georef.points import GeoPoint
    for raw in payload.get("geo_points", []):
        scene.geo_points.append(GeoPoint.from_dict(raw))

    from core.textlabel import TextLabel
    for raw in payload.get("text_labels", []):
        scene.text_labels.append(TextLabel.from_dict(raw))

    from core.guide import Guide
    scene.guides.clear()
    for raw in payload.get("guides", []):
        # A guide at (nan, nan, nan) stalled every tool (#185): left out.
        if not _finite_points(raw.get("point", ()),
                              raw.get("direction") or (),
                              raw.get("origin") or ()):
            _dropped_nonfinite[0] += 1
            continue
        scene.guides.append(Guide.from_dict(raw))
    # What had to be left out, for the window to say so.
    scene.load_repairs = _dropped_nonfinite[0]

    from core.image_plane import ImagePlane
    scene.image_planes.clear()
    for raw in payload.get("image_planes", []):
        scene.image_planes.append(ImagePlane.from_dict(raw))

    if progress is not None:
        _release_in_steps(data, lambda: tick(0.98, "Finishing…"))
    data = payload = None
    scene.version += 1


def _bulky(node) -> bool:
    """A container worth taking apart before dropping: a long list, or a
    dict holding one (a group, a prototype, the scene). Coordinates and
    small face records just go with their parent."""
    if isinstance(node, list):
        return len(node) > 64
    if isinstance(node, dict):
        return any(isinstance(v, (list, dict)) and len(v) > 64
                   for v in node.values())
    return False


def _release_in_steps(data, pump) -> None:
    """Drop the parsed document a slice at a time, ``pump()`` between
    slices. Released in one go when the loader returned, the JSON tree of
    a 3.3 GB document — tens of millions of objects — kept the window from
    answering for 8 s, long enough for the desktop to call IngeTrazo «not
    responding» (#158)."""
    import time
    last = time.monotonic()
    stack = [data]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for key in list(node):
                child = node.pop(key)
                if _bulky(child):
                    stack.append(child)
        elif isinstance(node, list):
            while node:
                child = node.pop()
                if _bulky(child):
                    stack.append(child)
                if time.monotonic() - last > 0.25:
                    pump()
                    last = time.monotonic()
        if time.monotonic() - last > 0.25:
            pump()
            last = time.monotonic()


def _face_attrs_from_json(raw) -> dict | None:
    attrs: dict = {}
    color = raw.get("color")
    if color is not None:
        attrs["color"] = list(color)
    texture = raw.get("texture")
    if texture is not None:
        attrs["texture"] = dict(texture)
    if raw.get("layer"):
        attrs["layer"] = raw["layer"]
    if raw.get("ifc"):
        attrs["ifc"] = dict(raw["ifc"])
    if raw.get("opacity") is not None:
        attrs["opacity"] = float(raw["opacity"])
    if raw.get("hidden"):
        attrs["hidden"] = True
    if raw.get("mat"):
        attrs["mat"] = raw["mat"]
    back = raw.get("back")
    if isinstance(back, dict):
        attrs["back"] = dict(back)
    elif back is True:
        attrs["back"] = True
    return attrs or None


def _load_mesh_small(mesh, payload) -> None:
    """The plain per-entity walk — faster than the bulk pass's fixed NumPy
    cost for the many small groups a document can carry."""
    import core.mesh as _mesh_mod
    for raw in payload.get("edges", []):
        try:
            edge = mesh.add_edge(QVector3D(*raw["a"]), QVector3D(*raw["b"]))
        except ValueError:
            continue  # degenerate edge in the document — skip
        if raw.get("soft"):
            edge.soft = True
        if raw.get("hidden"):
            edge.hidden = True
        if raw.get("layer"):
            edge.layer = raw["layer"]
        cid = raw.get("curve")
        if cid is not None:
            edge.curve = cid
            # Keep new curves unique after loading stored ids.
            if cid >= _mesh_mod._CURVE_COUNTER:
                _mesh_mod._CURVE_COUNTER = cid + 1
    for raw in payload.get("faces", []):
        verts = [QVector3D(*v) for v in raw["vertices"]]
        holes = [[QVector3D(*v) for v in loop] for loop in raw.get("holes", [])]
        face = mesh.add_face(verts, holes)
        attrs = _face_attrs_from_json(raw)
        if attrs:
            face.attrs.update(attrs)


def _load_mesh(mesh, payload, geom=None) -> None:
    """Rebuild a mesh from its JSON block in ONE bulk pass: every edge
    endpoint and face corner welds through :meth:`Mesh.bulk_weld` at once,
    then the edges and faces are created vectorized — the per-entity
    ``add_edge``/``add_face`` walk dominated opening big documents. Small
    groups take the plain walk (the bulk pass's fixed cost loses there).
    A format-3 block (``"geom"``) is read from ``geom``, the document's
    binary members."""
    import numpy as np
    import core.mesh as _mesh_mod
    from core.topology import _maximal_holes

    if "geom" in payload:
        _load_geometry(mesh, payload["geom"], geom or {})
        return

    payload = _without_nonfinite(payload)
    from core import _native
    if _native.wanted() and type(mesh) is _mesh_mod.Mesh:
        # A lazy mesh (experimental engine): its arrays now, its objects —
        # built by the very walk below — on first touch.
        src = _json_arrays(payload)
        if src is not None:
            curves = src["curves"]
            if curves is not None and curves.size and \
                    int(curves.max()) >= _mesh_mod._CURVE_COUNTER:
                _mesh_mod._CURVE_COUNTER = int(curves.max()) + 1
            # Built from its own arrays, not from ``payload``: the loader
            # empties the document tree in place once it is read
            # (_release_in_steps), and a mesh built later from it came out
            # with no faces at all.
            def build(m, src=src):
                _load_mesh_json(m, _payload_from_arrays(src))
            if _mesh_mod.DeferredMesh.defer(mesh, build, len(src["counts"]),
                                            src):
                return
    _load_mesh_json(mesh, payload)


def _json_arrays(payload) -> dict | None:
    """A JSON mesh block as the arrays of a format-3 one (the deferred
    source core.lazy_mesh plans from), or ``None`` when it holds nothing.
    The points in the order both JSON readers weld them: every edge's two
    ends, then each face's ring and its holes (nested ones dropped first,
    as add_face and the bulk reader do)."""
    import numpy as np
    from core.topology import _maximal_holes
    raw_edges = payload.get("edges", [])
    raw_faces = payload.get("faces", [])
    small = not _bulk_sized(len(raw_edges), len(raw_faces))
    flat: list = []
    flags: list = []
    curves: list = []
    layers: list = []
    names: dict = {}
    for raw in raw_edges:
        flat.append(raw["a"])
        flat.append(raw["b"])
        flags.append((1 if raw.get("soft") else 0)
                     | (2 if raw.get("hidden") else 0))
        cid = raw.get("curve")
        curves.append(-1 if cid is None else int(cid))
        lay = raw.get("layer")
        # The per-entity walk keeps a layer only when it is truthy, the
        # bulk one whenever it is present.
        if lay is None or (small and not lay):
            layers.append(-1)
        else:
            layers.append(names.setdefault(lay, len(names)))
    n_edge_pts = len(flat)
    ring_sizes: list = []
    ring_counts: list = []
    face_attr: list = []
    table: list = []
    table_index: dict = {}
    for raw in raw_faces:
        verts = raw["vertices"]
        holes = raw.get("holes", [])
        if len(holes) > 1:
            qholes = _maximal_holes(
                [[QVector3D(*v) for v in loop] for loop in holes])
            holes = [[(p.x(), p.y(), p.z()) for p in loop] for loop in qholes]
        ring_counts.append(1 + len(holes))
        ring_sizes.append(len(verts))
        flat.extend(verts)
        for loop in holes:
            ring_sizes.append(len(loop))
            flat.extend(loop)
        attrs = {k: v for k, v in raw.items()
                 if k not in ("vertices", "holes")}
        if _face_attrs_from_json(attrs):
            key = json.dumps(attrs, sort_keys=True, default=str)
            k = table_index.get(key)
            if k is None:
                k = table_index[key] = len(table)
                table.append(attrs)
            face_attr.append(k)
        else:
            face_attr.append(-1)
    if not flat:
        return None
    ne = len(raw_edges)
    meta: dict = {"face_attrs": table}
    if names:
        meta["edge_layers"] = list(names)
    return dict(
        meta=meta,
        pos=np.asarray(flat, dtype=np.float64).reshape(-1, 3),
        edges=np.arange(2 * ne, dtype=np.int64).reshape(-1, 2),
        flags=np.asarray(flags, dtype=np.uint8),
        curves=(np.asarray(curves, dtype=np.int64)
                if any(c >= 0 for c in curves) else None),
        layers=(np.asarray(layers, dtype=np.int32) if names else None),
        rings=np.arange(n_edge_pts, len(flat), dtype=np.int64),
        sizes=np.asarray(ring_sizes, dtype=np.int64),
        counts=np.asarray(ring_counts, dtype=np.int64),
        face_attr=np.asarray(face_attr, dtype=np.int64),
        sequential=small)


def _payload_from_arrays(src) -> dict:
    """The JSON block :func:`_json_arrays` read, back from its arrays: the
    same points (the document's own floats), flags, curves, layers, rings
    (nested holes already dropped — dropping again keeps them) and face
    attributes, for :func:`_load_mesh_json`."""
    pos = src["pos"].tolist()
    names = src["meta"].get("edge_layers") or []
    flags = src["flags"].tolist()
    curves = src["curves"].tolist() if src["curves"] is not None else None
    layers = src["layers"].tolist() if src["layers"] is not None else None
    edges = []
    for i, (a, b) in enumerate(src["edges"].tolist()):
        raw = {"a": pos[a], "b": pos[b]}
        if flags[i] & 1:
            raw["soft"] = True
        if flags[i] & 2:
            raw["hidden"] = True
        if curves is not None and curves[i] >= 0:
            raw["curve"] = curves[i]
        if layers is not None and layers[i] >= 0:
            raw["layer"] = names[layers[i]]
        edges.append(raw)
    rings = src["rings"].tolist()
    sizes = src["sizes"].tolist()
    table = src["meta"].get("face_attrs") or []
    faces = []
    c = r = 0
    for nr, k in zip(src["counts"].tolist(), src["face_attr"].tolist()):
        loops = []
        for _ in range(nr):
            loops.append([pos[i] for i in rings[c:c + sizes[r]]])
            c += sizes[r]
            r += 1
        raw = dict(table[k]) if k >= 0 else {}
        raw["vertices"] = loops[0]
        if len(loops) > 1:
            raw["holes"] = loops[1:]
        faces.append(raw)
    return {"edges": edges, "faces": faces}


def _load_mesh_json(mesh, payload) -> None:
    """:func:`_load_mesh` of a JSON block already cleared of non-finite
    points: the bulk pass, or the per-entity walk for a small one."""
    import numpy as np
    import core.mesh as _mesh_mod
    from core.topology import _maximal_holes

    raw_edges = payload.get("edges", [])
    raw_faces = payload.get("faces", [])
    if not _bulk_sized(len(raw_edges), len(raw_faces)):
        _load_mesh_small(mesh, payload)
        return
    flat: list = []
    for raw in raw_edges:
        flat.append(raw["a"])
        flat.append(raw["b"])
    n_edge_pts = len(flat)
    ring_sizes: list = []
    ring_counts: list = []
    attrs_list: list = []
    for raw in raw_faces:
        verts = raw["vertices"]
        holes = raw.get("holes", [])
        if len(holes) > 1:
            qholes = _maximal_holes(
                [[QVector3D(*v) for v in loop] for loop in holes])
            holes = [[(p.x(), p.y(), p.z()) for p in loop] for loop in qholes]
        ring_counts.append(1 + len(holes))
        ring_sizes.append(len(verts))
        flat.extend(verts)
        for loop in holes:
            ring_sizes.append(len(loop))
            flat.extend(loop)
        attrs_list.append(_face_attrs_from_json(raw))
    if not flat:
        return
    vobjs, inverse = mesh.bulk_weld(np.array(flat, dtype=np.float64))
    emap = None
    if raw_edges:
        flags = []
        max_curve = None
        for raw in raw_edges:
            cid = raw.get("curve")
            if cid is not None and (max_curve is None or cid > max_curve):
                max_curve = cid
            flags.append((bool(raw.get("soft")), cid, raw.get("layer"),
                          bool(raw.get("hidden"))))
        emap = mesh.add_edges_welded(
            vobjs, inverse[0:n_edge_pts:2], inverse[1:n_edge_pts:2], flags)
        # Keep new curves unique after loading stored ids.
        if max_curve is not None and max_curve >= _mesh_mod._CURVE_COUNTER:
            _mesh_mod._CURVE_COUNTER = max_curve + 1
    if ring_counts:
        mesh.add_faces_welded(vobjs, inverse[n_edge_pts:], ring_sizes,
                              ring_counts, attrs_list, edge_map=emap)


def _geometry_arrays(meta, blob: bytes) -> dict:
    """The arrays of a format-3 block, checked: known dtypes, inside the
    blob, and every index pointing at something that exists. A damaged or
    crafted document fails with a ValueError instead of building garbage."""
    import numpy as np

    def bad(why):
        return ValueError(f"damaged geometry block ({why})")

    layout = meta.get("arrays") if isinstance(meta, dict) else None
    if not isinstance(layout, dict):
        raise bad("no layout")
    out = {}
    for name, spec in layout.items():
        try:
            dtype, shape, offset = spec
            shape = tuple(int(n) for n in shape)
            offset = int(offset)
        except (TypeError, ValueError):
            raise bad(name) from None
        if dtype not in _GEOM_DTYPES or offset < 0 or any(n < 0 for n in shape):
            raise bad(name)
        count = 1
        for n in shape:
            count *= n
        size = count * np.dtype(dtype).itemsize
        if offset + size > len(blob):
            raise bad(name)
        out[name] = np.frombuffer(blob, dtype=dtype, count=count,
                                  offset=offset).reshape(shape)
    for name in ("pos", "edges", "rings", "ring_sizes", "ring_counts",
                 "face_attr", "edge_flags"):
        if name not in out:
            raise bad(f"missing {name}")
    pos = out["pos"]
    nv = len(pos)
    ne = len(out["edges"])
    if pos.ndim != 2 or pos.shape[1] != 3:
        raise bad("pos")
    if out["edges"].ndim != 2 or out["edges"].shape[1] != 2:
        raise bad("edges")
    for name in ("edges", "rings"):
        a = out[name]
        if a.size and (a.min() < 0 or a.max() >= nv):
            raise bad(name)
    sizes, counts = out["ring_sizes"], out["ring_counts"]
    if (sizes.size and sizes.min() < 1) or (counts.size and counts.min() < 1):
        raise bad("rings")
    if int(sizes.sum()) != len(out["rings"]) or int(counts.sum()) != len(sizes):
        raise bad("rings")
    # Format 4: the attribute table arrives as bytes in the same block (the
    # key "attrs" in the layout). Decoded here, so the rest of the reader
    # keeps seeing the list of dicts it always saw — and every index below is
    # checked against what was actually decoded.
    raw_attrs = out.pop("attrs", None)
    table = meta.get("face_attrs")
    if table is None:
        if raw_attrs is None:
            table = []
        else:
            try:
                table = _unpack_face_attrs(raw_attrs.tobytes())
            except ValueError:
                raise bad("face_attrs") from None
    if not isinstance(table, (list, tuple, _FaceAttrs)):
        raise bad("face_attrs")
    # Kept as the object it is: a format-4 table decodes per entry, so
    # building the mesh never materializes the JSON shape of all of it.
    out["face_attrs"] = table
    n_attrs = len(table)
    fa = out["face_attr"]
    if len(fa) != len(counts) or (fa.size and (fa.min() < -1
                                               or fa.max() >= n_attrs)):
        raise bad("face_attr")
    n_layers = len(meta.get("edge_layers") or ())
    for name in ("edge_flags", "edge_curve", "edge_layer"):
        if name in out and len(out[name]) != ne:
            raise bad(name)
    el = out.get("edge_layer")
    if el is not None and el.size and (el.min() < -1 or el.max() >= n_layers):
        raise bad("edge_layer")
    return out


def _document_geometry_arrays(meta, geom: dict) -> dict:
    """Read and validate a mesh's referenced format-3 geometry block."""
    member = meta.get("member") if isinstance(meta, dict) else None
    blob = geom.get(member)
    if blob is None:
        raise ValueError(f"the document lost its geometry block {member!r}")
    return _geometry_arrays(meta, blob)


def _load_geometry(mesh, meta, geom: dict) -> None:
    """Rebuild a mesh from its format-3 block — the same weld and the same
    bulk edge/face creation as the JSON path, fed from arrays."""
    import numpy as np
    import core.mesh as _mesh_mod

    a = _document_geometry_arrays(meta, geom)
    # The table may have come from the block's bytes (format 4). Put it back
    # in the block's JSON side, where everything downstream looks for it —
    # _build_geometry now, and the lazy mesh's plan later (_pack_plan).
    table = a.pop("face_attrs")
    if table is not meta.get("face_attrs"):
        meta = dict(meta)
        meta["face_attrs"] = table
    pos = a["pos"]
    edges, rings = a["edges"], a["rings"]
    sizes, counts = a["ring_sizes"], a["ring_counts"]
    face_attr = a["face_attr"]
    flags, curves, layers = (a["edge_flags"], a.get("edge_curve"),
                             a.get("edge_layer"))

    bad = ~np.isfinite(pos).all(axis=1)
    if bad.any():
        # Never written by this build (it refuses to save such a point),
        # but a damaged document opens like a JSON one: the pieces touching
        # the bad points are left out and counted (#185).
        keep_e = ~(bad[edges[:, 0]] | bad[edges[:, 1]])
        ring_bad = np.add.reduceat(bad[rings].astype(np.int64),
                                   np.cumsum(sizes) - sizes) > 0 \
            if len(sizes) else np.zeros(0, dtype=bool)
        face_bad = np.add.reduceat(ring_bad.astype(np.int64),
                                   np.cumsum(counts) - counts) > 0 \
            if len(counts) else np.zeros(0, dtype=bool)
        _dropped_nonfinite[0] += int((~keep_e).sum() + face_bad.sum())
        edges, flags = edges[keep_e], flags[keep_e]
        curves = curves[keep_e] if curves is not None else None
        layers = layers[keep_e] if layers is not None else None
        ring_face = np.repeat(np.arange(len(counts)), counts)
        keep_r = ~face_bad[ring_face]
        rings = rings[np.repeat(keep_r, sizes)]
        sizes, counts = sizes[keep_r], counts[~face_bad]
        face_attr = face_attr[~face_bad]
    if not len(pos) or not (len(edges) or len(counts)):
        return
    if curves is not None and curves.size:
        top = int(curves.max())
        if top >= _mesh_mod._CURVE_COUNTER:
            _mesh_mod._CURVE_COUNTER = top + 1

    from core import _native
    if _native.wanted():
        # Owned, not borrowed: a deferred mesh is built (or saved, or its
        # materials counted) after load_into has emptied the parsed tree in
        # place (_release_in_steps) — its face_attrs table came back empty
        # and the mesh lost every face, in the file too once saved (#1533).
        # (A pickle round trip: a deep copy, ~5× faster than copy's.)
        import pickle
        meta = pickle.loads(pickle.dumps(meta, pickle.HIGHEST_PROTOCOL))

    def build(mesh):
        _build_geometry(mesh, meta, pos, edges, flags, curves, layers,
                        rings, sizes, counts, face_attr)
    if not (_native.wanted()
            and _mesh_mod.DeferredMesh.defer(
                mesh, build, len(counts),
                dict(meta=meta, pos=pos, edges=edges, flags=flags,
                     curves=curves, layers=layers, rings=rings, sizes=sizes,
                     counts=counts, face_attr=face_attr))):
        build(mesh)


def _build_geometry(mesh, meta, pos, edges, flags, curves, layers, rings,
                    sizes, counts, face_attr) -> None:
    """The objects of a format-3 block: :func:`_load_geometry`'s second
    half, run at once or, for a lazy mesh, on its first touch."""
    import numpy as np

    vobjs, inverse = mesh.bulk_weld(pos.astype(np.float64))
    emap = None
    if len(edges):
        eflags = None
        if flags.any() or curves is not None or layers is not None:
            names = meta.get("edge_layers") or []
            soft = (flags & 1).astype(bool).tolist()
            hidden = (flags & 2).astype(bool).tolist()
            cl = (curves.tolist() if curves is not None
                  else [-1] * len(edges))
            ll = (layers.tolist() if layers is not None
                  else [-1] * len(edges))
            eflags = [(s, c if c >= 0 else None, names[l] if l >= 0 else None,
                       h) for s, c, l, h in zip(soft, cl, ll, hidden)]
        emap = mesh.add_edges_welded(vobjs, inverse[edges[:, 0]],
                                     inverse[edges[:, 1]], eflags)
    if len(counts):
        table = meta.get("face_attrs") or []
        fast = getattr(table, "attrs_for", None)
        if fast is not None:
            # Format 4: the attributes come straight from the columns, in
            # face order — no intermediate JSON-shaped dict per face.
            attrs = fast(face_attr)
        else:
            attrs = [_face_attrs_from_json(table[k]) if k >= 0 else None
                     for k in face_attr.tolist()]
        mesh.add_faces_welded(vobjs, inverse[rings], sizes, counts, attrs,
                              edge_map=emap)
