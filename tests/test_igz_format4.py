# SPDX-License-Identifier: GPL-3.0-or-later
"""Format 4: a big face-attribute table travels as columns.

The promise is the same as format 3's: nothing changes but the size. A model
whose attribute table went binary reopens as the same faces, with the same
texture placement, colour and material — and the document stays byte-for-byte
reproducible. The one deliberate difference is the placement's precision:
float32, the same the block's own points already have.
"""
from __future__ import annotations

import json
import zipfile

import pytest
from PySide6.QtGui import QVector3D as V

from core.scene import Scene
from formats import igz
from tests.test_igz_format3 import _canonical


@pytest.fixture
def binary(monkeypatch):
    """Every document counts as large and every mesh goes binary."""
    monkeypatch.setattr(igz, "_LARGE_DOCUMENT", 0)
    monkeypatch.setattr(igz, "_BULK_MIN", 1)


def _attrs_scene(n: int = 600) -> Scene:
    """A mesh with one face per attribute entry — the shape a textured import
    leaves behind. The numbers are exact in float32 on purpose, so a reloaded
    scene can be compared with the JSON one without a tolerance."""
    scene = Scene()
    mesh = scene.mesh
    for i in range(n):
        f = mesh.add_face([V(i, 0, 0), V(i + 1, 0, 0), V(i, 1, 0), V(i, 1, 1)])
        f.attrs.update({
            "color": [0.5, 0.25, 0.125],
            "texture": {"path": "/x.png", "sw": 1.5, "sh": 0.75,
                        "uvw": [i * 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
                        "planar": True},
            "mat": "Madera",
            "back": True,
            "layer": "Pisos",
            "opacity": 0.5,
            "ifc": {"class": "IfcWall"},
        })
    return scene


def _document(path):
    with zipfile.ZipFile(path) as zf:
        return json.loads(zf.read("document.json")), zf.namelist()


def test_a_big_table_goes_binary_and_reopens_the_same(tmp_path, monkeypatch):
    scene = _attrs_scene()
    json_path = tmp_path / "json.igz"
    igz.save_scene(scene, json_path, binary=False)   # the table as JSON
    json_back = Scene()
    igz.load_into(json_back, json_path)

    monkeypatch.setattr(igz, "_LARGE_DOCUMENT", 0)
    monkeypatch.setattr(igz, "_BULK_MIN", 1)
    bin_path = tmp_path / "bin.igz"
    igz.save_scene(scene, bin_path)

    doc, members = _document(bin_path)
    block = doc["scene"]["geom"]
    assert doc["igz_format"] == igz.ATTRS_FORMAT
    assert "face_attrs" not in block          # the JSON table is gone
    assert "attrs" in block["arrays"]         # …and rides in the blob
    assert any(n.startswith("geom/") for n in members)

    bin_back = Scene()
    igz.load_into(bin_back, bin_path)
    assert len(bin_back.mesh.faces) == 600
    assert _canonical(bin_back) == _canonical(json_back)


def test_the_table_arrives_lazy_not_as_a_list(tmp_path, binary):
    path = tmp_path / "lazy.igz"
    igz.save_scene(_attrs_scene(), path)
    back = Scene()
    igz.load_into(back, path)
    table = back.mesh.__dict__["_deferred_source"]["meta"]["face_attrs"] \
        if "_deferred_source" in back.mesh.__dict__ else None
    # Either the mesh is deferred (the table is in its source) or it was
    # built at once and the table is gone — but it must never have been
    # materialized into 600 dicts on the way in.
    assert table is None or isinstance(table, igz._FaceAttrs)


def test_a_small_table_stays_json_at_format_3(tmp_path, binary):
    scene = Scene()
    for i in range(igz._ATTRS_MIN - 1):
        f = scene.mesh.add_face([V(i, 0, 0), V(i + 1, 0, 0), V(i, 1, 0)])
        f.attrs["texture"] = {"path": "/x.png", "sw": i * 0.5, "sh": 1.0}
    out = tmp_path / "small.igz"
    igz.save_scene(scene, out)
    doc, _ = _document(out)
    assert doc["igz_format"] == igz.GEOMETRY_FORMAT
    assert "attrs" not in doc["scene"]["geom"]["arrays"]
    assert len(doc["scene"]["geom"]["face_attrs"]) == igz._ATTRS_MIN - 1


def test_two_saves_are_byte_identical_with_the_codec(tmp_path, binary):
    scene = _attrs_scene()
    igz.save_scene(scene, tmp_path / "a.igz")
    igz.save_scene(scene, tmp_path / "b.igz")
    assert (tmp_path / "a.igz").read_bytes() == (tmp_path / "b.igz").read_bytes()


def test_a_placement_that_float32_cannot_hold_keeps_its_precision():
    """The placement is quantized to float32 — by 1e-7, the precision of the
    points it transforms. What must not happen is a value that overflows:
    that table goes back to JSON instead of turning into infinity."""
    value = 0.1234567890123
    table = [{"texture": {"uvw": [value]}}]
    back = igz._unpack_face_attrs(igz._pack_face_attrs(table))
    assert back[0]["texture"]["uvw"][0] == pytest.approx(value, rel=1e-7)
    assert back[0]["texture"]["uvw"][0] != value       # it did quantize
    assert igz._pack_face_attrs([{"opacity": 1e300}]) is None


def test_a_reloaded_document_saves_again_the_same_way(tmp_path, binary):
    """Opening a house and saving it again is the everyday path: the table
    that came back as bytes must go back out as bytes, same faces."""
    first = tmp_path / "a.igz"
    igz.save_scene(_attrs_scene(), first)
    back = Scene()
    igz.load_into(back, first)
    second = tmp_path / "b.igz"
    igz.save_scene(back, second)
    doc, _ = _document(second)
    assert doc["igz_format"] == igz.ATTRS_FORMAT
    assert "attrs" in doc["scene"]["geom"]["arrays"]
    again = Scene()
    igz.load_into(again, second)
    assert _canonical(again) == _canonical(back)


def test_the_codec_roundtrips_every_shape():
    table = [
        {"color": [1.0, 0.5, 0.25],
         "texture": {"path": "x.png", "sw": 1.0, "sh": 2.0,
                     "uvw": [0.0] * 8, "planar": True},
         "mat": "Madera", "back": True, "opacity": 0.5, "hidden": True,
         "layer": "Pisos", "ifc": {"class": "IfcWall", "level": 3}},
        {"back": {"texture": {"path": "y.png"}}},
        {"nothing": None, "empty": {}, "none": []},
        {"texture": {"path": "z.png", "uvw": [1.0, 2.0], "sw": 0}},
        {},
    ]
    packed = igz._pack_face_attrs(table)
    assert packed is not None
    assert igz._unpack_face_attrs(packed) == table


def test_entries_of_different_shapes_keep_their_own(tmp_path, binary):
    """The table is grouped by shape: the mapping back must not shuffle an
    entry into the group next to it."""
    scene = Scene()
    for i in range(600):
        f = scene.mesh.add_face([V(i, 0, 0), V(i + 1, 0, 0), V(i, 1, 0)])
        if i % 3 == 0:
            f.attrs["mat"] = f"A{i}"
        elif i % 3 == 1:
            f.attrs["texture"] = {"path": "/b.png", "sw": i}
        else:
            f.attrs["color"] = [0.5, 0.5, 0.5]
    back = Scene()
    igz.save_scene(scene, tmp_path / "mix.igz")
    igz.load_into(back, tmp_path / "mix.igz")
    for i, face in enumerate(back.mesh.faces):
        if i % 3 == 0:
            assert face.attrs["mat"] == f"A{i}"
        elif i % 3 == 1:
            assert face.attrs["texture"]["sw"] == i
        else:
            assert face.attrs["color"] == [0.5, 0.5, 0.5]


def test_the_codec_refuses_what_it_cannot_carry():
    assert igz._pack_face_attrs([{"x": object()}]) is None
    assert igz._pack_face_attrs([{"x": float("nan")}]) is None
    assert igz._pack_face_attrs([{1: "key is not a string"}]) is None


def test_a_truncated_table_is_refused():
    raw = igz._pack_face_attrs([{"a": 1.0, "b": [2.0, 3.0]}])
    assert raw is not None
    with pytest.raises(ValueError):
        igz._unpack_face_attrs(raw[:-2])


def test_a_damaged_table_fails_cleanly(tmp_path, binary):
    out = tmp_path / "d.igz"
    igz.save_scene(_attrs_scene(), out)
    with zipfile.ZipFile(out) as zf:
        members = {n: zf.read(n) for n in zf.namelist()}
    doc = json.loads(members["document.json"])
    block = doc["scene"]["geom"]
    member = block["member"]
    offset = block["arrays"]["attrs"][2]
    blob = bytearray(members[member])
    blob[offset] = 0x7F                        # not a node kind
    members[member] = bytes(blob)
    members["document.json"] = json.dumps(doc).encode()
    with zipfile.ZipFile(out, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    with pytest.raises(ValueError, match="damaged geometry block"):
        igz.load_into(Scene(), out)
