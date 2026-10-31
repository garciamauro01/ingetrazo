# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
"""Gerenciamento de dados, cópias paramétricas e transformações 3D dos Componentes Dinâmicos."""
from __future__ import annotations

import copy
import math
import re
from typing import Any
from PySide6.QtGui import QColor, QMatrix4x4, QVector3D

from core.group import Group, copy_group, oriented_bounds
from .engine import SafeExpressionEvaluator

EXTENSION_KEY = "dynamic_components"

STANDARD_ATTRIBUTES = {
    # Posição
    "X": {"label": "Posição X", "value": 0.0, "unit": "m", "formula": "", "options": [], "editable": True},
    "Y": {"label": "Posição Y", "value": 0.0, "unit": "m", "formula": "", "options": [], "editable": True},
    "Z": {"label": "Posição Z", "value": 0.0, "unit": "m", "formula": "", "options": [], "editable": True},
    # Dimensões
    "LenX": {"label": "Comprimento LenX", "value": 1.0, "unit": "m", "formula": "", "options": [], "editable": True},
    "LenY": {"label": "Profundidade LenY", "value": 1.0, "unit": "m", "formula": "", "options": [], "editable": True},
    "LenZ": {"label": "Altura LenZ", "value": 1.0, "unit": "m", "formula": "", "options": [], "editable": True},
    # Rotação
    "RotX": {"label": "Rotação RotX", "value": 0.0, "unit": "deg", "formula": "", "options": [], "editable": True},
    "RotY": {"label": "Rotação RotY", "value": 0.0, "unit": "deg", "formula": "", "options": [], "editable": True},
    "RotZ": {"label": "Rotação RotZ", "value": 0.0, "unit": "deg", "formula": "", "options": [], "editable": True},
    # Comportamentos & Restrições do SketchUp
    "Copies": {"label": "Cópias (Copies)", "value": 0, "unit": "", "formula": "", "options": [], "editable": True},
    "Copy": {"label": "Índice da Cópia (Copy)", "value": 0, "unit": "", "formula": "", "options": [], "editable": False},
    "Hidden": {"label": "Oculto (Hidden)", "value": 0, "unit": "", "formula": "", "options": [], "editable": True},
    "Material": {"label": "Material / Cor", "value": "", "unit": "", "formula": "", "options": [], "editable": True},
    "ScaleTool": {"label": "Bloqueio Escala (ScaleTool)", "value": 127, "unit": "", "formula": "", "options": [], "editable": True},
}


def get_dc_data(group) -> dict[str, Any] | None:
    if not group or not hasattr(group, "ext") or not group.ext:
        return None
    return group.ext.get(EXTENSION_KEY)


def ensure_dc_data(group) -> dict[str, Any]:
    if not hasattr(group, "ext") or group.ext is None:
        group.ext = {}
    if EXTENSION_KEY not in group.ext:
        mesh = getattr(group, "mesh", None)
        base_lx, base_ly, base_lz = 1.0, 1.0, 1.0
        if mesh and mesh.vertices:
            _, lo, hi = oriented_bounds(mesh)
            base_lx = max(abs(hi[0] - lo[0]), 0.001)
            base_ly = max(abs(hi[1] - lo[1]), 0.001)
            base_lz = max(abs(hi[2] - lo[2]), 0.001)

        init_attrs = copy.deepcopy(STANDARD_ATTRIBUTES)
        init_attrs["LenX"]["value"] = round(base_lx, 4)
        init_attrs["LenY"]["value"] = round(base_ly, 4)
        init_attrs["LenZ"]["value"] = round(base_lz, 4)

        orig_xf = [float(x) for x in group.xform.data()] if getattr(group, "xform", None) is not None else None

        group.ext[EXTENSION_KEY] = {
            "name": getattr(group, "name", "Componente Dinâmico"),
            "description": "",
            "base_dims": (base_lx, base_ly, base_lz),
            "orig_xform": orig_xf,
            "attributes": init_attrs,
            "onClick": "",
            "is_copy": False,
        }
    return group.ext[EXTENSION_KEY]


def is_dc_copy(group) -> bool:
    data = get_dc_data(group)
    return bool(data and data.get("is_copy", False))


def evaluate_dc(group, parent_group=None, copy_index: int = 0) -> dict[str, Any]:
    """Avalia o grafo completo de fórmulas, subcomponentes, cópias e transformações 3D."""
    data = get_dc_data(group)
    if not data:
        return {}

    attrs = data.setdefault("attributes", {})
    context: dict[str, Any] = {}

    attrs.setdefault("Copy", {"label": "Índice da Cópia", "value": copy_index, "unit": "", "editable": False})
    attrs["Copy"]["value"] = copy_index

    # Contexto do pai
    if parent_group:
        p_data = get_dc_data(parent_group)
        if p_data:
            for pk, pv in p_data.get("attributes", {}).items():
                context[f"Parent_{pk}"] = pv.get("value")
                context[f"Parent!{pk}"] = pv.get("value")

    # Contexto dos filhos
    children = getattr(group, "children", []) or []
    for ch in children:
        c_data = get_dc_data(ch)
        c_name = getattr(ch, "name", "").replace(" ", "_")
        if c_data and c_name:
            for ck, cv in c_data.get("attributes", {}).items():
                context[f"{c_name}__{ck}"] = cv.get("value")
                context[f"{c_name}!{ck}"] = cv.get("value")

    for name, item in attrs.items():
        context[name] = item.get("value")

    # Múltiplos passes de avaliação
    for _ in range(4):
        for name, item in attrs.items():
            formula = str(item.get("formula", "")).strip()
            if formula:
                res = SafeExpressionEvaluator.evaluate(formula, context)
                if res is not None and not str(res).startswith("#ERRO"):
                    item["value"] = res
                    context[name] = res

    # Aplica na geometria 3D e materiais
    apply_dc_geometry(group)
    apply_dc_material(group)

    # Gerenciamento de Cópias paramétricas
    _manage_dc_copies(group)

    # Avaliação recursiva de subcomponentes filhos
    for ch in children:
        if not is_dc_copy(ch):
            evaluate_dc(ch, parent_group=group)

    return context


def _manage_dc_copies(group) -> None:
    data = get_dc_data(group)
    if not data:
        return

    attrs = data.get("attributes", {})
    try:
        num_copies = int(float(attrs.get("Copies", {}).get("value", 0)))
    except Exception:
        num_copies = 0

    if num_copies <= 0:
        if hasattr(group, "children") and group.children:
            group.children = [c for c in group.children if not is_dc_copy(c)]
        return

    if not hasattr(group, "children") or group.children is None:
        group.children = []

    base_children = [c for c in group.children if not is_dc_copy(c)]
    new_copies = []
    for c in base_children:
        c_data = get_dc_data(c)
        if not c_data:
            continue
        c_attrs = c_data.get("attributes", {})
        has_copy_ref = any("Copy" in str(it.get("formula", "")) for it in c_attrs.values())
        if has_copy_ref:
            for i in range(1, num_copies + 1):
                clone = copy_group(c)
                c_ext = ensure_dc_data(clone)
                c_ext["is_copy"] = True
                clone.name = f"{c.name}_Copy{i}"
                evaluate_dc(clone, parent_group=group, copy_index=i)
                new_copies.append(clone)

    group.children = base_children + new_copies


def apply_dc_geometry(group) -> None:
    """Aplica redimensionamento, rotação e translação usando a matriz xform do grupo."""
    data = get_dc_data(group)
    if not data:
        return

    attrs = data.get("attributes", {})

    # Mede base_dims se não houver
    if "base_dims" not in data:
        mesh = getattr(group, "mesh", None)
        base_lx, base_ly, base_lz = 1.0, 1.0, 1.0
        if mesh and mesh.vertices:
            _, lo, hi = oriented_bounds(mesh)
            base_lx = max(abs(hi[0] - lo[0]), 0.001)
            base_ly = max(abs(hi[1] - lo[1]), 0.001)
            base_lz = max(abs(hi[2] - lo[2]), 0.001)
        data["base_dims"] = (base_lx, base_ly, base_lz)

    # Guarda matriz original se ainda não tiver guardado
    if "orig_xform" not in data:
        data["orig_xform"] = [float(x) for x in group.xform.data()] if getattr(group, "xform", None) is not None else None

    base_lx, base_ly, base_lz = data.get("base_dims", (1.0, 1.0, 1.0))
    if base_lx <= 0: base_lx = 1.0
    if base_ly <= 0: base_ly = 1.0
    if base_lz <= 0: base_lz = 1.0

    len_x = float(attrs.get("LenX", {}).get("value", base_lx))
    len_y = float(attrs.get("LenY", {}).get("value", base_ly))
    len_z = float(attrs.get("LenZ", {}).get("value", base_lz))

    pos_x = float(attrs.get("X", {}).get("value", 0.0))
    pos_y = float(attrs.get("Y", {}).get("value", 0.0))
    pos_z = float(attrs.get("Z", {}).get("value", 0.0))

    rot_x = float(attrs.get("RotX", {}).get("value", 0.0))
    rot_y = float(attrs.get("RotY", {}).get("value", 0.0))
    rot_z = float(attrs.get("RotZ", {}).get("value", 0.0))

    # Ocultar / Exibir
    hidden_val = attrs.get("Hidden", {}).get("value", 0)
    group.hidden = bool(hidden_val and hidden_val != 0 and hidden_val != "0")

    scale_x = len_x / base_lx
    scale_y = len_y / base_ly
    scale_z = len_z / base_lz

    # Se o grupo veio do SKP com matriz original, preserva ou compõe a rotação relativa
    orig_xf_data = data.get("orig_xform")
    if orig_xf_data and len(orig_xf_data) == 16:
        # data() retorna lista em column-major, enquanto o construtor QMatrix4x4(*args) espera row-major.
        # Transpõe para restaurar exatamente a matriz 4x4 original do modelo:
        row_major = [orig_xf_data[c * 4 + r] for r in range(4) for c in range(4)]
        m = QMatrix4x4(*row_major)
        if rot_z:
            m.rotate(rot_z, 0.0, 0.0, 1.0)
        if rot_y:
            m.rotate(rot_y, 0.0, 1.0, 0.0)
        if rot_x:
            m.rotate(rot_x, 1.0, 0.0, 0.0)
    else:
        m = QMatrix4x4()
        m.translate(pos_x, pos_y, pos_z)
        if rot_z:
            m.rotate(rot_z, 0.0, 0.0, 1.0)
        if rot_y:
            m.rotate(rot_y, 0.0, 1.0, 0.0)
        if rot_x:
            m.rotate(rot_x, 1.0, 0.0, 0.0)
        m.scale(scale_x, scale_y, scale_z)

    group.xform = m


def apply_dc_material(group) -> None:
    data = get_dc_data(group)
    if not data:
        return

    mat_val = str(data.get("attributes", {}).get("Material", {}).get("value", "")).strip()
    if not mat_val:
        return

    color = QColor(mat_val)
    if color.isValid():
        r, g, b = color.redF(), color.greenF(), color.blueF()
        group.material = {"color": [r, g, b]}
        mesh = getattr(group, "mesh", None)
        if mesh and hasattr(mesh, "faces"):
            for f in mesh.faces:
                if not hasattr(f, "attrs") or f.attrs is None:
                    f.attrs = {}
                f.attrs["color"] = [r, g, b]
