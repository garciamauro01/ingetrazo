# SPDX-License-Identifier: GPL-3.0-or-later
"""Standardized TrazoMob metadata management in group.ext['trazomob'].

As specified in IngeTrazo's docs/plugins.md:
    group.ext = {app.key: {"kind": "...", ...}}
"""
from __future__ import annotations

from typing import Any


def get_trazomob(group: Any) -> dict[str, Any]:
    """Returns the TrazoMob data contained in group.ext['trazomob'].

    Also transparently recognizes legacy objects during the transition.
    """
    if not group or not getattr(group, "ext", None) or not isinstance(group.ext, dict):
        return {}

    # 1. Official standard format: group.ext["trazomob"]
    tm = group.ext.get("trazomob")
    if isinstance(tm, dict):
        return tm

    # 2. Transparent fallback for loose legacy keys (for immediate safety)
    for old_key, kind in (
        ("trazomob_module", "module"),
        ("trazomob_wall", "wall"),
        ("trazomob_esquadria", "esquadria"),
        ("trazomob_floor", "floor"),
        ("trazomob_ceiling", "ceiling"),
        ("trazomob_bancada", "bancada"),
        ("trazomob_light", "light"),
    ):
        if old_key in group.ext:
            val = group.ext[old_key]
            if isinstance(val, dict):
                data = dict(val)
                data.setdefault("kind", kind)
                return data
            elif val is True:
                return {"kind": kind}

    return {}


def set_trazomob(group: Any, kind: str, data: dict[str, Any] | None = None, **kwargs) -> dict[str, Any]:
    """Sets group metadata under the official group.ext['trazomob'] namespace."""
    if getattr(group, "ext", None) is None or not isinstance(group.ext, dict):
        group.ext = {}

    tm = group.ext.setdefault("trazomob", {})
    tm["kind"] = kind
    if data:
        tm.update(data)
    if kwargs:
        tm.update(kwargs)

    # Temporarily keeps a legacy key mirror for compatibility with parts in transition
    legacy_map = {
        "module": "trazomob_module",
        "wall": "trazomob_wall",
        "esquadria": "trazomob_esquadria",
        "floor": "trazomob_floor",
        "ceiling": "trazomob_ceiling",
        "bancada": "trazomob_bancada",
        "light": "trazomob_light",
    }
    old_key = legacy_map.get(kind)
    if old_key:
        if kind in ("floor", "ceiling", "bancada", "light"):
            group.ext[old_key] = True
        else:
            group.ext[old_key] = tm

    return tm


def is_trazomob_kind(group: Any, kind: str) -> bool:
    """Quickly checks whether the group belongs to the specified TrazoMob category."""
    tm = get_trazomob(group)
    return tm.get("kind") == kind
