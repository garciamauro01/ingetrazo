# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez and IngeTrazo contributors.
"""A click that only selects a decoration must not build its lazy mesh.

The pre-baked decorator cache opens a 100k-face mesh as a ``DeferredMesh``.
Its ``faces`` are built on first touch (~4 s here). ``pick_group`` and the
right-click's locked-group search only wanted the OWNER of the hit, but asked
``hits.ent()`` for the ``(face, owner)`` pair — which built every face just to
throw the face away. Resolving the owner beside the faces keeps insertion and
selection both instant."""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
from PySide6.QtGui import QVector3D as V

from views.array_bake import LazyPairs, PickEntities
from views.viewport import Viewport


class _Faces:
    """Stands in for ``DeferredFaces``: any touch is the slow rebuild."""

    def __init__(self):
        self.touched = 0

    def __len__(self):
        return 3

    def __getitem__(self, i):
        self.touched += 1
        raise AssertionError("the deferred mesh was materialized")


def test_owner_is_read_beside_the_lazy_faces():
    faces = _Faces()
    group = object()
    ents = PickEntities()
    ents.extend([(None, None)])
    ents.extend(LazyPairs(faces, group))
    assert len(ents) == 4
    assert ents.owner(0) is None                 # plain (face, owner) part
    assert ents.owner(1) is group
    assert ents.owner(3) is group
    assert faces.touched == 0


def test_face_hits_gives_the_owner_without_the_face():
    faces = _Faces()
    group = object()
    idx = SimpleNamespace(
        entities=PickEntities(LazyPairs(faces, group)),
        ent_place_idx=np.full(3, -1, np.int32),
        ent_placements=[],
        ent_area=np.ones(3),
        ent_sel=np.ones(3, bool),
        ent_vis=np.ones(3, bool),
        ent_loose=np.zeros(3, bool),
    )
    class VP:
        def _ray_hits(self, *a, **kw):
            return np.array([1.0, np.inf, np.inf])

    hits = Viewport._face_hits(VP(), idx, V(0, 0, 0), V(0, 0, -1), "sel")
    assert hits.owner(0) is group
    assert faces.touched == 0
    # The old path really did build the mesh, which is what this fixes.
    with np.testing.assert_raises(AssertionError):
        hits.ent(0)


def test_pick_group_selects_the_group_without_building_it():
    faces = _Faces()
    group = object()
    hits = SimpleNamespace(
        t=np.array([1.0]), area=np.array([1.0]), loose=np.array([False]),
        ent=lambda k: faces[int(k)], owner=lambda k: group)

    class VP:
        scene = SimpleNamespace(edit_group=None)

        def _pixel_to_ray(self, x, y):
            return V(0, 0, 0), V(0, 0, -1)

        def _pick_index(self, *, near=None):
            return object()

        def _hover_hits(self, idx, origin, direction):
            return hits

        def _coplanar_eps(self, origin, direction, t):
            return 0.0

        def _context_placements(self):
            return []

    assert Viewport.pick_group(VP(), 5, 5) is group
    assert faces.touched == 0
