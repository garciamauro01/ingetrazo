# SPDX-License-Identifier: GPL-3.0-or-later
"""Gerenciamento padronizado de metadados do TrazoMob em group.ext['trazomob'].

Conforme especificado em docs/plugins.md do IngeTrazo:
    group.ext = {app.key: {"kind": "...", ...}}
"""
from __future__ import annotations
from typing import Any, Dict, Optional


def get_trazomob(group: Any) -> Dict[str, Any]:
    """Retorna os dados do TrazoMob contidos em group.ext['trazomob'].

    Também reconhece de forma transparente objetos legados durante a transição.
    """
    if not group or not getattr(group, "ext", None) or not isinstance(group.ext, dict):
        return {}

    # 1. Formato padrão oficial: group.ext["trazomob"]
    tm = group.ext.get("trazomob")
    if isinstance(tm, dict):
        return tm

    # 2. Fallback transparente para chaves legadas soltas (para segurança imediata)
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


def set_trazomob(group: Any, kind: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """Define metadados do grupo sob o namespace oficial group.ext['trazomob']."""
    if getattr(group, "ext", None) is None or not isinstance(group.ext, dict):
        group.ext = {}

    tm = group.ext.setdefault("trazomob", {})
    tm["kind"] = kind
    if data:
        tm.update(data)
    if kwargs:
        tm.update(kwargs)

    # Mantém espelho da chave legada temporariamente para compatibilidade com partes em transição
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
    """Verifica rapidamente se o grupo pertence à categoria especificada do TrazoMob."""
    tm = get_trazomob(group)
    return tm.get("kind") == kind
