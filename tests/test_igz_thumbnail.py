# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez and IngeTrazo contributors.
"""The preview Windows Explorer shows lives inside the .igz ZIP container."""
from __future__ import annotations

import zipfile

from core.scene import Scene
from formats.igz import load_into, read_thumbnail, save_scene

FAKE_PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRtest_data"


def test_thumbnail_roundtrip(tmp_path):
    doc = tmp_path / "thumb.igz"
    stats = save_scene(Scene(), doc, thumbnail_bytes=FAKE_PNG)

    assert stats == {"embedded": 0, "missing": 0}   # a preview is not a texture
    assert read_thumbnail(doc) == FAKE_PNG
    with zipfile.ZipFile(doc) as zf:
        assert zf.read("meta/thumbnail.png") == FAKE_PNG
    loaded = Scene()
    load_into(loaded, doc)
    assert loaded is not None


def test_without_thumbnail_stays_plain_json(tmp_path):
    doc = tmp_path / "plain.igz"
    stats = save_scene(Scene(), doc)

    assert stats == {"embedded": 0, "missing": 0}
    assert not doc.read_bytes().startswith(b"PK\x03\x04")
    assert read_thumbnail(doc) is None


def test_reads_legacy_entry_names(tmp_path):
    doc = tmp_path / "legacy.igz"
    with zipfile.ZipFile(doc, "w") as zf:
        zf.writestr("thumbnail.png", FAKE_PNG)

    assert read_thumbnail(doc) == FAKE_PNG
