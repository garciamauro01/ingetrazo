# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
"""Conversor e extrator automático de atributos dinâmicos do SketchUp (.skp)."""
from __future__ import annotations

import re
from typing import Any


def convert_skp_dynamic_attributes(raw_props: dict[str, Any]) -> dict[str, Any] | None:
    """Converte um dicionário 'dynamic_attributes' extraído do .skp para o formato do plugin."""
    if not raw_props:
        return None

    # Normaliza chaves (lowercase)
    norm = {str(k).lower(): v for k, v in raw_props.items()}

    # Verifica se realmente contém propriedades dinâmicas do SketchUp
    has_dc = any(
        k.startswith("_") or k in ("lenx", "leny", "lenz", "onclick", "name", "description")
        for k in norm.keys()
    )
    if not has_dc:
        return None

    dc_attrs: dict[str, dict[str, Any]] = {}

    # Chaves de atributos conhecidas
    # No SketchUp: _lenx_formula, _lenx_label, _lenx_units, _onclick_formula, etc.
    keys = set()
    for k in norm.keys():
        clean = k.strip("_")
        parts = clean.split("_")
        keys.add(parts[0])

    for base_key in keys:
        if not base_key:
            continue
        # Nome padrão formatado (ex: lenx -> LenX)
        name_map = {
            "lenx": "LenX", "leny": "LenY", "lenz": "LenZ",
            "rotx": "RotX", "roty": "RotY", "rotz": "RotZ",
            "x": "X", "y": "Y", "z": "Z",
            "copies": "Copies", "copy": "Copy", "hidden": "Hidden",
            "material": "Material", "scaletool": "ScaleTool"
        }
        attr_name = name_map.get(base_key, base_key.capitalize())

        # Valor direto
        val = norm.get(base_key, norm.get(f"_{base_key}", 0.0))
        # Fórmula
        formula = norm.get(f"_{base_key}_formula", norm.get(f"{base_key}_formula", ""))
        # Rótulo
        label = norm.get(f"_{base_key}_label", norm.get(f"{base_key}_label", attr_name))
        # Unidades
        units = norm.get(f"_{base_key}_units", norm.get(f"{base_key}_units", ""))

        # Converte valores numéricos
        try:
            val_num = float(val)
            # SketchUp salva comprimentos em polegadas no dynamic_attributes!
            # Se for LenX, LenY, LenZ, X, Y, Z, converte polegadas -> metros
            if base_key in ("lenx", "leny", "lenz", "x", "y", "z"):
                val_num = round(val_num * 0.0254, 4)
            val = val_num
        except (ValueError, TypeError):
            pass

        dc_attrs[attr_name] = {
            "label": str(label),
            "value": val,
            "formula": str(formula) if formula else "",
            "unit": "m" if base_key in ("lenx", "leny", "lenz", "x", "y", "z") else str(units),
            "options": [],
            "editable": True,
        }

    # onClick
    onclick = norm.get("onclick", norm.get("_onclick_formula", norm.get("_onclick", "")))

    return {
        "name": norm.get("name", "Componente Dinâmico"),
        "description": norm.get("description", ""),
        "attributes": dc_attrs,
        "onClick": str(onclick) if onclick else "",
    }

