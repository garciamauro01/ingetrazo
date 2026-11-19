# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Exportação de plano de corte para TrazoMob (texto tsv, CSV e JSON)."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


from .dxf_cnc import export_cut_sheet_dxf, export_piece_dxf


def format_trazomob_text(parts: list[dict[str, Any]]) -> str:
    """Gera texto tab-separado (TSV) pronto para colar no TrazoMob (Ctrl+V)."""
    lines = []
    for p in parts:
        qtd = p.get("quantidade", 1)
        comp = f"{p['comprimento']:.1f}"
        larg = f"{p['largura']:.1f}"
        nome = p["nome"]
        c1 = "1" if p.get("fita_c1") else "0"
        c2 = "1" if p.get("fita_c2") else "0"
        l1 = "1" if p.get("fita_l1") else "0"
        l2 = "1" if p.get("fita_l2") else "0"
        fitas = f"{c1};{c2};{l1};{l2}"
        mat = p["material"]
        veio = "S" if p.get("ignorar_veio") else "N"
        lines.append(f"{qtd}\t{comp}\t{larg}\t{nome}\t{fitas}\t{mat}\t{veio}")
    return "\n".join(lines)


def export_trazomob_csv(parts: list[dict[str, Any]], filepath: str | Path) -> None:
    """Salva lista de peças em arquivo CSV compatível com TrazoMob com resumo de usinagens."""
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([
            "Quantidade", "Comprimento Final", "Largura Final", "Comp Corte Bruto", "Larg Corte Bruto",
            "Espessura", "Descricao", "Material",
            "Espessura Fita", "Fita C1", "Fita C2", "Fita L1", "Fita L2", "Ignorar Veio", "Furações / Usinagens"
        ])
        for p in parts:
            ops = p.get("operacoes", [])
            ops_desc = "; ".join(o.get("descricao", "") for o in ops if o.get("descricao")) if ops else "NENHUMA"
            comp_c = p.get("comprimento_corte", p["comprimento"])
            larg_c = p.get("largura_corte", p["largura"])
            esp_f = p.get("espessura_fita", 0.45)
            writer.writerow([
                p.get("quantidade", 1), f"{p['comprimento']:.1f}", f"{p['largura']:.1f}",
                f"{comp_c:.1f}", f"{larg_c:.1f}", f"{p['espessura']:.1f}",
                p["nome"], p["material"],
                f"{esp_f:.2f}",
                "SIM" if p.get("fita_c1") else "NAO", "SIM" if p.get("fita_c2") else "NAO",
                "SIM" if p.get("fita_l1") else "NAO", "SIM" if p.get("fita_l2") else "NAO",
                "SIM" if p.get("ignorar_veio") else "NAO",
                ops_desc,
            ])


def export_trazomob_json(parts: list[dict[str, Any]], filepath: str | Path) -> None:
    """Salva lista de peças em arquivo JSON estruturado com metadados e usinagens detalhadas."""
    clean_data = [dict(p) for p in parts]
    for p in clean_data:
        p.pop("group", None)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generator": "IngeTrazo TrazoMob",
                "version": "2.0",
                "parts": clean_data,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )


def _collect_scene_groups(scene: Any) -> dict[int, Any]:
    """Indexa todos os grupos da cena (módulos e compostos) pelo ``id()``."""
    groups_by_id: dict[int, Any] = {}
    if scene is None:
        return groups_by_id
    stack = list(getattr(scene, "groups", None) or [])
    while stack:
        g = stack.pop()
        if id(g) in groups_by_id:
            continue
        groups_by_id[id(g)] = g
        children = getattr(g, "children", None)
        if children:
            stack.extend(children)
    return groups_by_id


def _hellomob_part_child(part: dict[str, Any]) -> dict[str, Any]:
    """Converte um dicionário de peça TrazoMob no objeto filho esperado pelo ``.hellomob``."""
    comp = round(float(part.get("comprimento") or 0.0), 1)
    larg = round(float(part.get("largura") or 0.0), 1)
    esp = round(float(part.get("espessura") or 18.0), 1)
    comp_c = round(float(part.get("comprimento_corte", comp)), 1)
    larg_c = round(float(part.get("largura_corte", larg)), 1)
    esp_fita = round(float(part.get("espessura_fita") or 0.45), 2)
    qtd = int(part.get("quantidade") or 1)
    mat = str(part.get("material") or f"MDF {round(esp)}mm")
    mat_fita = str(part.get("material_fita") or mat)

    lenx, leny, lenz = comp, larg, esp
    pg = part.get("group")
    if pg is not None and hasattr(pg, "mesh") and getattr(pg.mesh, "vertices", None):
        from .parts import _get_entity_bbox

        dims = _get_entity_bbox(pg)
        if dims:
            lenx = round(dims[0] * 1000.0, 1)
            leny = round(dims[1] * 1000.0, 1)
            lenz = round(dims[2] * 1000.0, 1)

    attrs: dict[str, Any] = {
        "material": mat,
        "material_fita": mat_fita,
        "thickness": esp,
        "width": larg,
        "length": comp,
        "espessura": esp,
        "largura": larg,
        "comprimento": comp,
        "comprimento_corte": comp_c,
        "largura_corte": larg_c,
        "fita_c1": bool(part.get("fita_c1", False)),
        "fita_c2": bool(part.get("fita_c2", False)),
        "fita_l1": bool(part.get("fita_l1", False)),
        "fita_l2": bool(part.get("fita_l2", False)),
        "espessura_fita": esp_fita,
        "ignorar_veio": bool(part.get("ignorar_veio", False)),
        "quantity": qtd,
        "_lenx_nominal": lenx,
        "_leny_nominal": leny,
        "_lenz_nominal": lenz,
    }
    ops = part.get("operacoes")
    if ops:
        attrs["operacoes"] = [dict(o) for o in ops if isinstance(o, dict)]

    return {
        "name": str(part.get("nome") or "Peça"),
        "attributes": attrs,
        "children": None,
    }


def _module_entry(mod_g: Any, fallback_name: str, parts_list: list[dict[str, Any]]) -> dict[str, Any]:
    """Constrói o objeto raiz de um módulo no formato ``.hellomob``."""
    children = [_hellomob_part_child(p) for p in parts_list]
    if mod_g is not None:
        from ..domain.schema import module_params

        mp = module_params(mod_g)
        name = str(getattr(mod_g, "name", None) or mp.get("nome") or fallback_name)
        width = round(float(mp.get("largura") or 0.0), 1)
        height = round(float(mp.get("altura") or 0.0), 1)
        depth = round(float(mp.get("profundidade") or 0.0), 1)
        esp = round(float(mp.get("espessura") or (parts_list[0].get("espessura") if parts_list else 18.0) or 18.0), 1)
        offset = mp.get("offset") or (0.0, 0.0, 0.0)
        rot = round(float(mp.get("rotation") or mp.get("rotacionar") or 0.0), 1)
        mod_type = str(mp.get("tipo") or "")
    else:
        name = fallback_name
        width = round(max((float(p.get("comprimento") or 0.0) for p in parts_list), default=0.0), 1)
        depth = round(max((float(p.get("largura") or 0.0) for p in parts_list), default=0.0), 1)
        height = round(sum(float(p.get("espessura") or 18.0) * int(p.get("quantidade") or 1) for p in parts_list), 1)
        esp = round(float(parts_list[0].get("espessura") or 18.0), 1) if parts_list else 18.0
        offset = (0.0, 0.0, 0.0)
        rot = 0.0
        mod_type = "pecas_avulsas"

    return {
        "name": name,
        "attributes": {
            "module_type": mod_type,
            "width": width,
            "height": height,
            "depth": depth,
            "thickness": esp,
            "_lenx_nominal": width,
            "_leny_nominal": depth,
            "_lenz_nominal": height,
        },
        "position": {
            "x": round(float(offset[0]) * 1000.0, 1),
            "y": round(float(offset[1]) * 1000.0, 1),
            "z": round(float(offset[2]) * 1000.0, 1),
            "rotx": 0.0,
            "roty": 0.0,
            "rotz": rot,
            "rotation": rot,
        },
        "children": children,
    }


def build_hellomob_payload(
    parts: list[dict[str, Any]] | None = None,
    *,
    scene: Any = None,
) -> list[dict[str, Any]]:
    """Monta a estrutura JSON compatível com arquivos ``.hellomob`` (Hellomob / Cortecloud)."""
    if parts is None and scene is not None:
        from .parts import extract_parts

        parts = extract_parts(scene)

    parts_list = list(parts or [])
    if not parts_list:
        return []

    groups_by_id = _collect_scene_groups(scene)
    buckets: dict[Any, list[dict[str, Any]]] = {}
    bucket_order: list[Any] = []

    for part in parts_list:
        mod_key = part.get("_module_key")
        bucket_id: Any = ("mod", mod_key) if mod_key in groups_by_id else ("avulsa", part.get("modulo") or "TrazoMob Peças Avulsas")
        if bucket_id not in buckets:
            buckets[bucket_id] = []
            bucket_order.append(bucket_id)
        buckets[bucket_id].append(part)

    payload: list[dict[str, Any]] = []
    for bucket_id in bucket_order:
        kind, key_val = bucket_id
        mod_g = groups_by_id.get(key_val) if kind == "mod" else None
        fallback_name = "Módulo TrazoMob" if kind == "mod" else str(key_val)
        payload.append(_module_entry(mod_g, fallback_name, buckets[bucket_id]))
    return payload


def export_trazomob_hellomob(
    parts_or_scene: list[dict[str, Any]] | Any,
    filepath: str | Path,
    *,
    scene: Any = None,
) -> Path:
    """Exporta peças ou cena do TrazoMob para arquivo ``.hellomob`` (JSON compatível Hellomob/Cortecloud)."""
    if parts_or_scene is not None and not isinstance(parts_or_scene, (list, tuple)):
        scene = parts_or_scene
        parts: list[dict[str, Any]] | None = None
    else:
        parts = list(parts_or_scene or []) if parts_or_scene is not None else None

    payload = build_hellomob_payload(parts, scene=scene)
    out_path = Path(filepath)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return out_path


def import_hellomob_file(filepath: str | Path) -> list[dict[str, Any]]:
    """Lê e valida a estrutura básica de um arquivo ``.hellomob``."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Arquivo .hellomob inválido: raiz deve ser uma lista de módulos.")
    modules: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        modules.append({
            "name": str(item.get("name") or ""),
            "attributes": dict(item.get("attributes") or {}),
            "position": dict(item.get("position") or {}),
            "children": item.get("children"),
        })
    return modules

