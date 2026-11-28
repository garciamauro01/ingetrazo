# SPDX-License-Identifier: GPL-3.0-or-later
"""The cast_shadow toggle must mean the same thing in the UI, document and Blender."""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

from trazomob.render.lighting import _clean_trazomob_lights, wants_shadow

ROOT = Path(__file__).resolve().parents[1]


def _load_blender_script(monkeypatch):
    """Load the standalone Blender script without a real Blender installation."""
    for name in ("bpy", "bmesh"):
        monkeypatch.setitem(sys.modules, name, types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, "mathutils", types.SimpleNamespace(Matrix=object, Vector=object))
    path = ROOT / "blender_scripts" / "photoreal_render.py"
    spec = importlib.util.spec_from_file_location("_test_shadow_photoreal", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_shadow_default_depends_on_light_kind():
    led = {"kind": "led_strip", "pos": [0, 0, 2], "p1": [0, 0, 2], "p2": [1, 0, 2], "power": 100}
    spot = {"kind": "spot", "pos": [0, 0, 2], "power": 100}
    point = {"kind": "point", "pos": [0, 0, 2], "power": 100}

    assert wants_shadow(led) is False
    assert wants_shadow(spot) is True
    assert wants_shadow(point) is True

    cleaned = _clean_trazomob_lights([led, spot, {**point, "cast_shadow": False}])
    assert [lt["cast_shadow"] for lt in cleaned] == [False, True, False]


def test_blender_script_mirrors_shadow_default(monkeypatch):
    mod = _load_blender_script(monkeypatch)

    assert mod._light_wants_shadow({"kind": "led_strip"}) is False
    assert mod._light_wants_shadow({"kind": "spot"}) is True
    assert mod._light_wants_shadow({"kind": "point"}) is True
    assert mod._light_wants_shadow({"kind": "led_strip", "cast_shadow": True}) is True
    assert mod._light_wants_shadow({"kind": "spot", "cast_shadow": False}) is False


def test_cast_shadow_control_is_translated_and_uses_light_default(qapp, monkeypatch):
    import core.i18n as core_i18n
    from core.scene import Scene
    from trazomob.domain.i18n import clear_i18n_cache
    from trazomob.render.lighting import LightManagerDialog

    scene = Scene()
    scene.plugin_data = {
        "render_blender": {
            "lights": [
                {"kind": "led_strip", "pos": [0, 0, 2], "p1": [0, 0, 2], "p2": [1, 0, 2], "power": 100},
            ]
        }
    }
    viewport = types.SimpleNamespace(scene=scene, window=None)

    monkeypatch.setattr(core_i18n, "current_language", lambda: "en")
    clear_i18n_cache()
    dialog = LightManagerDialog(viewport)
    assert dialog.chk_cast_shadow.text() == "Cast Shadows"
    assert "LED strips" in dialog.chk_cast_shadow.toolTip()
    dialog._on_light_selected(0)
    assert dialog.chk_cast_shadow.isChecked() is False
    dialog.close()

    monkeypatch.setattr(core_i18n, "current_language", lambda: "es")
    clear_i18n_cache()
    dialog = LightManagerDialog(viewport)
    assert dialog.chk_cast_shadow.text() == "Proyectar Sombras"
    assert "tiras LED" in dialog.chk_cast_shadow.toolTip()
    dialog.close()
