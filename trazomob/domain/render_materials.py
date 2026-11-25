# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Catálogo de presets procedurais de render e mapeamento por slot de material."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

RENDER_PRESETS: List[Tuple[str, str]] = [
    ("original", "Manter Original"),
    ("aco_escovado", "Aço Escovado (Inox)"),
    ("cromado", "Cromado Espelhado"),
    ("preto_fosco_metal", "Metal Preto Fosco"),
    ("dourado_escovado", "Latão / Dourado Escovado"),
    ("branco_esmaltado", "Branco Esmaltado (Laca)"),
    ("black_piano", "Preto Black Piano"),
    ("pintura_automotiva", "Pintura Automotiva Metálica"),
    ("vidro_incolor", "Vidro Incolor"),
    ("vidro_fume", "Vidro Fumê"),
    ("vidro_jateado", "Vidro Jateado / Fosco"),
    ("espelho", "Espelho"),
    ("borracha_fosca", "Borracha Fosca"),
    ("carpete_felpudo", "Tapete / Carpete Felpudo (3D)"),
    ("grama_3d", "Grama 3D Procedural"),
]

RENDER_PRESET_IDS = {pid for pid, _ in RENDER_PRESETS}


def face_material_key(face: Any) -> Tuple[str, str, Optional[Tuple[float, float, float]], Optional[str]]:
    """Retorna ``(key, label, color_rgb, texture_path)`` estável para uma face."""
    attrs = getattr(face, "attrs", None) or {}
    tex = attrs.get("texture") if isinstance(attrs, dict) else None
    if isinstance(tex, dict) and tex.get("path"):
        tpath = str(tex["path"])
        import os
        fname = os.path.basename(tpath)
        key = f"tex:{tpath}"
        return key, f"Textura: {fname}", None, tpath

    col = attrs.get("color") if isinstance(attrs, dict) else None
    if col is not None and len(col) >= 3:
        r, g, b = float(col[0]), float(col[1]), float(col[2])
        ri, gi, bi = int(round(r * 100)), int(round(g * 100)), int(round(b * 100))
        key = f"mat_{ri}_{gi}_{bi}"
        label = f"Cor RGB ({int(round(r*255))}, {int(round(g*255))}, {int(round(b*255))})"
        return key, label, (r, g, b), None

    return "mat_default", "Cor Padrão", (0.85, 0.85, 0.85), None


def extract_group_material_slots(group: Any) -> List[Dict[str, Any]]:
    """Varre um ``Group`` (e seus filhos) e retorna os slots únicos de material/cor/textura."""
    if group is None:
        return []

    slots: Dict[str, Dict[str, Any]] = {}
    root_name = str(getattr(group, "name", "") or "").strip()

    def _walk(g: Any, is_root: bool = False) -> None:
        g_name = str(getattr(g, "name", "") or "").strip()
        mesh = getattr(g, "mesh", None)
        if mesh is not None and getattr(mesh, "faces", None):
            for f in mesh.faces:
                key, label, color, tpath = face_material_key(f)
                if key not in slots:
                    slots[key] = {
                        "key": key,
                        "label": label,
                        "color": color,
                        "texture_path": tpath,
                        "face_count": 0,
                        "part_names": [],
                        "faces": [],
                    }
                slot = slots[key]
                slot["face_count"] += 1
                slot["faces"].append(f)
                if g_name and (not is_root or g_name != root_name):
                    if g_name not in slot["part_names"]:
                        slot["part_names"].append(g_name)
        for ch in getattr(g, "children", []) or []:
            _walk(ch, is_root=False)

    _walk(group, is_root=True)
    return sorted(slots.values(), key=lambda s: -s["face_count"])


def get_group_render_materials(group: Any) -> Dict[str, str]:
    """Lê o dicionário ``{material_key: preset_id}`` salvo em ``group.ext``."""
    if group is None:
        return {}
    ext = getattr(group, "ext", None)
    if not isinstance(ext, dict):
        return {}
    data = ext.get("trazomob_render_materials")
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if str(v) in RENDER_PRESET_IDS}


def set_group_render_materials(group: Any, mapping: Dict[str, str]) -> None:
    """Grava o dicionário ``{material_key: preset_id}`` em ``group.ext``."""
    if group is None:
        return
    if getattr(group, "ext", None) is None or not isinstance(group.ext, dict):
        group.ext = {}
    cleaned = {
        str(k): str(v)
        for k, v in (mapping or {}).items()
        if str(v) in RENDER_PRESET_IDS and str(v) != "original"
    }
    if cleaned:
        group.ext["trazomob_render_materials"] = cleaned
    else:
        group.ext.pop("trazomob_render_materials", None)


def collect_group_render_overrides(groups: Any) -> Dict[str, Dict[str, Any]]:
    """Collect ``trazomob_render_materials`` dict overrides across ``groups`` and children."""
    collected: Dict[str, Dict[str, Any]] = {}

    def _walk(item: Any) -> None:
        if item is None:
            return
        ext = getattr(item, "ext", None)
        if isinstance(ext, dict):
            raw = ext.get("trazomob_render_materials")
            if isinstance(raw, dict):
                for key, value in raw.items():
                    if isinstance(value, dict):
                        collected[str(key)] = dict(value)
        for child in getattr(item, "children", ()) or ():
            _walk(child)

    for g in groups or ():
        _walk(g)
    return collected
