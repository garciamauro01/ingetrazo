# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez and IngeTrazo contributors.
"""Reading a user's file as a component: which way is up, how big it is, and
where its base sits once placed."""
from __future__ import annotations

import math

from views import component_loader

CUBE = """v 0 0 0
v 1 0 0
v 1 1 0
v 0 1 0
v 0 0 1
v 1 0 1
v 1 1 1
v 0 1 1
f 1 2 3 4
f 5 6 7 8
f 1 2 6 5
f 2 3 7 6
f 3 4 8 7
f 4 1 5 8
"""

#: A flat card lying in XY, one hundred units across each way.
CARD = """v 0 0 0
v 100 0 0
v 100 100 0
v 0 100 0
f 1 2 3 4
"""


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_matrix_for_turns_units_into_metres():
    matrix = component_loader.matrix_for("cm")
    assert matrix[0] == 0.01
    assert matrix[4] == 0.01
    assert matrix[8] == 0.01
    assert matrix[1] == matrix[2] == 0.0


def test_matrix_for_y_up_turns_the_model_about_x():
    from formats.obj import Y_UP_TO_Z_UP
    assert component_loader.matrix_for("m", y_up=True) == Y_UP_TO_Z_UP


def test_metre_cube_measures_one_hundred_centimetres(tmp_path):
    path = _write(tmp_path, "cubo.obj", CUBE)
    group = component_loader.load_group(
        path, matrix=component_loader.matrix_for("m"))

    assert component_loader.size_cm(group) == (100.0, 100.0, 100.0)


def test_centimetre_file_is_scaled_to_its_real_size(tmp_path):
    path = _write(tmp_path, "cubo-cm.obj", CUBE)
    group = component_loader.load_group(
        path, matrix=component_loader.matrix_for("cm"))

    assert component_loader.size_cm(group) == (1.0, 1.0, 1.0)


def test_y_up_card_stands_in_the_xz_plane(tmp_path):
    path = _write(tmp_path, "carta.obj", CARD)
    group = component_loader.load_group(
        path, matrix=component_loader.matrix_for("cm", y_up=True))
    width, depth, height = component_loader.size_cm(group)

    assert math.isclose(width, 100.0, abs_tol=1e-6)
    assert math.isclose(depth, 0.0, abs_tol=1e-6)
    assert math.isclose(height, 100.0, abs_tol=1e-6)


def test_fit_scales_to_the_recorded_size_and_rests_on_the_floor(tmp_path):
    path = _write(tmp_path, "cubo.obj", CUBE)
    group = component_loader.load_group(
        path, matrix=component_loader.matrix_for("m"))

    fitted = component_loader.fit(group, cm=[200, 50, 300], anchor="base")
    width, depth, height = component_loader.size_cm(fitted)

    assert math.isclose(width, 200.0, abs_tol=1e-6)
    assert math.isclose(depth, 50.0, abs_tol=1e-6)
    assert math.isclose(height, 300.0, abs_tol=1e-6)
    lo, _hi = component_loader.bounds(fitted)
    assert math.isclose(lo[2], 0.0, abs_tol=1e-9)


def test_a_file_without_geometry_is_an_error_with_a_reason(tmp_path):
    path = tmp_path / "vazio.obj"
    path.write_text("# nada aqui\n", encoding="utf-8")
    try:
        component_loader.load_group(path)
    except component_loader.ComponentLoadError as exc:
        assert "geometry" in str(exc)
    else:  # pragma: no cover - the assertion is the point
        raise AssertionError("an empty model should not load silently")
