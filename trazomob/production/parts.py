# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Extração e agrupamento de peças 3D da cena para plano de corte."""
from __future__ import annotations

from typing import Any

from core.group import iter_placements


def _get_entity_bbox(entity, xform=None):
    positions = []
    mesh = getattr(entity, "mesh", None)
    if mesh is not None:
        for v in mesh.vertices:
            p = v.position
            if xform is not None:
                p = xform.map(p)
            positions.append(p)

    if not positions:
        return None

    xs = [p.x() for p in positions]
    ys = [p.y() for p in positions]
    zs = [p.z() for p in positions]

    return (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))


def _ambiente_da_peca(g) -> tuple[str | None, str | None]:
    """Lê o ambiente/pavimento associados a um grupo (ou à parede que o contém).

    O ambiente é gravado em ``ext["ambiente"]`` (ou ``ext["trazomob_wall"]``)
    quando o módulo/parede é criado; propagá-lo para a peça permite orçar por
    ambiente sem heurísticas de substring na interface.
    """
    ext = getattr(g, "ext", None)
    if not isinstance(ext, dict):
        return None, None
    wall = ext.get("trazomob_wall") if isinstance(ext.get("trazomob_wall"), dict) else {}
    amb = ext.get("ambiente") or wall.get("ambiente")
    pav = ext.get("pavimento") or wall.get("pavimento")
    return amb, pav


def detect_grain_orientation(
    material_name: str,
    piece_name: str = "",
    dims_sorted: tuple[float, float, float] | None = None,
) -> bool:
    """Retorna True se o material explicitamente permite giro no corte (ignora veio).

    Consulta a definição técnica do material no MaterialsRegistry,
    sem inferência por nome ou string.
    """
    if isinstance(material_name, dict):
        material_name = material_name.get("nome") or material_name.get("material") or ""
    from ..domain.materials_registry import MaterialsRegistry
    return MaterialsRegistry.get_instance().allows_rotation(str(material_name or ""))


def calculate_cut_dimensions(
    comprimento: float,
    largura: float,
    fita_c1: bool = False,
    fita_c2: bool = False,
    fita_l1: bool = False,
    fita_l2: bool = False,
    espessura_fita: float = 0.45,
) -> tuple[float, float]:
    """Calcula a medida de corte bruta abatendo a espessura da fita de borda nos lados aplicados.

    Exemplo:
        Peça acabada de 700 x 400 mm com fita de 1.0mm nos 4 bordos:
        Corte bruto = 700 - (1.0 + 1.0) = 698.0 mm
                      400 - (1.0 + 1.0) = 398.0 mm
    """
    comp_corte = float(comprimento)
    larg_corte = float(largura)
    esp_f = float(espessura_fita or 0.0)

    if esp_f > 0.0:
        if fita_c1:
            larg_corte -= esp_f
        if fita_c2:
            larg_corte -= esp_f
        if fita_l1:
            comp_corte -= esp_f
        if fita_l2:
            comp_corte -= esp_f

    return (max(1.0, round(comp_corte, 1)), max(1.0, round(larg_corte, 1)))



def extract_parts(scene, selected_only: bool = False, ambiente: Any = None) -> list[dict[str, Any]]:
    parts = []
    groups = getattr(scene, "groups", [])
    selected_set = set(
        getattr(scene, "selection", None)
        or getattr(scene, "selected_groups", None)
        or []
    )

    from core.group import iter_placements

    from ..domain.assembly import is_module
    from ..domain.schema import KIND_AMBIENTE, KIND_ESQUADRIA, KIND_MODULE, is_kind, kind_of

    # Se ambiente foi passado, mapeia toda a árvore de nós que pertencem a ele
    ambiente_nodes: set[int] = set()
    if ambiente is not None:
        def _map_ambiente(node: Any) -> None:
            ambiente_nodes.add(id(node))
            for child in getattr(node, "children", None) or []:
                _map_ambiente(child)
        _map_ambiente(ambiente)

    def _is_target_ambiente(group: Any) -> bool:
        if ambiente is None:
            return True
        return id(group) in ambiente_nodes

    # Um módulo pode estar dentro de um assembly (ou de um grupo nativo):
    # percorre a árvore para o cutlist não perder o que foi agrupado.
    candidates: list[Any] = []

    def _is_part_container(group: Any) -> bool:
        """Módulo/esquadria cujos filhos são peças (não descemos neles)."""
        if kind_of(group) in (KIND_MODULE, KIND_ESQUADRIA) or is_module(group):
            return True
        ext = getattr(group, "ext", None)
        return isinstance(ext, dict) and "trazomob_module" in ext

    def _collect(group: Any) -> None:
        # Um pai oculto esconde a subárvore inteira (mesma regra do viewport).
        if not getattr(scene, "entity_visible", lambda _: True)(group):
            return
        # Filtra por ambiente se especificado
        if not _is_target_ambiente(group):
            return
        if _is_part_container(group):
            candidates.append(group)
            return
        children = getattr(group, "children", None) or []
        if children:
            for child in children:
                _collect(child)
            return
        candidates.append(group)

    for root in groups:
        # Se ambiente especificado, só coleta se raiz for o ambiente ou descendente
        if ambiente is not None and not _is_target_ambiente(root):
            continue
        _collect(root)

    if selected_only:
        # Módulos agrupados podem ser o item selecionado, mesmo que o grupo
        # raiz (o assembly) não esteja: filtra pela folha, não pela raiz.
        candidates = [c for c in candidates if c in selected_set]

    idx = 1
    # Se o grupo for um container de módulo, inspeciona seus filhos
    for g in candidates:
        if getattr(g, "layer", None) in ("Paredes", "Piso", "Bancadas", "Walls", "Floor"):
            continue

        # Se for um container mestre de módulo com peças filhas
        if getattr(g, "children", None) and hasattr(g, "ext") and g.ext and "trazomob_module" in g.ext:
            from ..builders.hardware_geometry import is_hardware_group
            for pg, m in iter_placements(g):
                if pg is g:
                    continue
                if is_hardware_group(pg):
                    continue
                dims = _get_entity_bbox(pg, m)
                if not dims:
                    continue

                dx_mm = round(dims[0] * 1000.0, 1)
                dy_mm = round(dims[1] * 1000.0, 1)
                dz_mm = round(dims[2] * 1000.0, 1)

                sorted_dims = sorted([dx_mm, dy_mm, dz_mm])
                espessura = sorted_dims[0]
                largura = sorted_dims[1]
                comprimento = sorted_dims[2]

                if espessura < 1.0 or comprimento < 5.0 or largura < 5.0:
                    continue

                saved_meta = {}
                if hasattr(pg, "ext") and isinstance(pg.ext, dict):
                    saved_meta = pg.ext.get("trazomob") or {}
                if isinstance(saved_meta, dict) and (
                    saved_meta.get("ignorar_corte")
                    or saved_meta.get("kind") in ("hardware", "colchao", "decoracao")
                ):
                    continue

                if saved_meta.get("espessura") is not None:
                    espessura = float(saved_meta["espessura"])
                if saved_meta.get("largura") is not None:
                    largura = float(saved_meta["largura"])
                if saved_meta.get("comprimento") is not None:
                    comprimento = float(saved_meta["comprimento"])

                name = saved_meta.get("nome") or getattr(pg, "name", None) or f"Peca_{idx}"
                mat_name = saved_meta.get("material") or getattr(pg, "material", None) or f"MDF {round(espessura)}mm"

                # Detecção inteligente de veio se não definido explicitamente
                ign_veio = saved_meta.get("ignorar_veio")
                if ign_veio is None:
                    ign_veio = detect_grain_orientation(mat_name, name, (espessura, largura, comprimento))
                else:
                    ign_veio = bool(ign_veio)

                fita_c1 = bool(saved_meta.get("fita_c1", False))
                fita_c2 = bool(saved_meta.get("fita_c2", False))
                fita_l1 = bool(saved_meta.get("fita_l1", False))
                fita_l2 = bool(saved_meta.get("fita_l2", False))
                esp_fita = float(saved_meta.get("espessura_fita") or 0.45)
                mat_fita = saved_meta.get("material_fita") or mat_name

                comp_corte, larg_corte = calculate_cut_dimensions(
                    comprimento, largura, fita_c1, fita_c2, fita_l1, fita_l2, esp_fita
                )

                operacoes = saved_meta.get("operacoes", [])

                # Ferragens do módulo ao qual a peça pertence. A chave do módulo
                # permite dedup no orçamento/relatório (contar uma ferragem por
                # módulo, não uma vez por peça).
                _module_key = id(g)
                _module_hw = []
                _g_ext = getattr(g, "ext", None)
                if isinstance(_g_ext, dict):
                    _module_hw = list(_g_ext.get("trazomob_hardware") or [])
                _amb, _pav = _ambiente_da_peca(g)

                parts.append({
                    "id": idx,
                    "group": pg,
                    "nome": name,
                    "comprimento": round(comprimento, 1),
                    "largura": round(largura, 1),
                    "espessura": round(espessura, 1),
                    "comprimento_corte": comp_corte,
                    "largura_corte": larg_corte,
                    "material": mat_name,
                    "material_fita": mat_fita,
                    "espessura_fita": esp_fita,
                    "fita_c1": fita_c1,
                    "fita_c2": fita_c2,
                    "fita_l1": fita_l1,
                    "fita_l2": fita_l2,
                    "ignorar_veio": ign_veio,
                    "operacoes": operacoes,
                    "quantidade": 1,
                    "_module_key": _module_key,
                    "module_hardware": _module_hw,
                    "ambiente": _amb,
                    "pavimento": _pav,
                })
                idx += 1
            continue

        # Grupos avulsos só entram se forem expressamente marcados como peças do TrazoMob
        has_trazomob_tag = (
            (hasattr(g, "ext") and isinstance(g.ext, dict) and any(k in g.ext for k in ("trazomob", "trazomob_module")))
            or getattr(g, "layer", None) == "PLANEJADOS"
        )
        if not has_trazomob_tag:
            continue
        from ..builders.hardware_geometry import is_hardware_group
        if is_hardware_group(g):
            continue

        targets = [g]

        for tgt in targets:
            for pg, m in iter_placements(tgt):
                if is_hardware_group(pg):
                    continue
                dims = _get_entity_bbox(pg, m)
                if not dims:
                    continue

                dx_mm = round(dims[0] * 1000.0, 1)
                dy_mm = round(dims[1] * 1000.0, 1)
                dz_mm = round(dims[2] * 1000.0, 1)

                sorted_dims = sorted([dx_mm, dy_mm, dz_mm])
                espessura = sorted_dims[0]
                largura = sorted_dims[1]
                comprimento = sorted_dims[2]

                if espessura < 1.0 or comprimento < 5.0 or largura < 5.0:
                    continue

                saved_meta = {}
                if hasattr(tgt, "ext") and isinstance(tgt.ext, dict):
                    saved_meta = tgt.ext.get("trazomob") or {}
                if not saved_meta and hasattr(pg, "ext") and isinstance(pg.ext, dict):
                    saved_meta = pg.ext.get("trazomob") or {}
                if isinstance(saved_meta, dict) and (
                    saved_meta.get("ignorar_corte")
                    or saved_meta.get("kind") in ("hardware", "colchao", "decoracao")
                ):
                    continue

                # Se estiver no layer PLANEJADOS ou tiver metadados de marcenaria
                if not saved_meta and getattr(tgt, "layer", None) != "PLANEJADOS":
                    continue

                if saved_meta.get("espessura") is not None:
                    espessura = float(saved_meta["espessura"])
                if saved_meta.get("largura") is not None:
                    largura = float(saved_meta["largura"])
                if saved_meta.get("comprimento") is not None:
                    comprimento = float(saved_meta["comprimento"])

                name = saved_meta.get("nome") or getattr(tgt, "name", None) or getattr(pg, "name", None) or f"Peca_{idx}"
                mat_name = saved_meta.get("material") or getattr(tgt, "material", None) or getattr(pg, "material", None) or f"MDF {round(espessura)}mm"
                if isinstance(mat_name, dict):
                    mat_name = mat_name.get("nome") or mat_name.get("material") or f"MDF {round(espessura)}mm"
                mat_name = str(mat_name or f"MDF {round(espessura)}mm")

                ign_veio = saved_meta.get("ignorar_veio")
                if ign_veio is None:
                    ign_veio = detect_grain_orientation(mat_name, name, (espessura, largura, comprimento))
                else:
                    ign_veio = bool(ign_veio)

                operacoes = saved_meta.get("operacoes", [])

                fita_c1 = bool(saved_meta.get("fita_c1", False))
                fita_c2 = bool(saved_meta.get("fita_c2", False))
                fita_l1 = bool(saved_meta.get("fita_l1", False))
                fita_l2 = bool(saved_meta.get("fita_l2", False))
                esp_fita = float(saved_meta.get("espessura_fita") or 0.45)
                mat_fita = saved_meta.get("material_fita") or mat_name

                comp_corte, larg_corte = calculate_cut_dimensions(
                    comprimento, largura, fita_c1, fita_c2, fita_l1, fita_l2, esp_fita
                )

                _amb, _pav = _ambiente_da_peca(tgt)

                parts.append({
                    "id": idx,
                    "group": tgt,
                    "nome": name,
                    "comprimento": round(comprimento, 1),
                    "largura": round(largura, 1),
                    "espessura": round(espessura, 1),
                    "comprimento_corte": comp_corte,
                    "largura_corte": larg_corte,
                    "material": mat_name,
                    "material_fita": mat_fita,
                    "espessura_fita": esp_fita,
                    "fita_c1": fita_c1,
                    "fita_c2": fita_c2,
                    "fita_l1": fita_l1,
                    "fita_l2": fita_l2,
                    "ignorar_veio": ign_veio,
                    "operacoes": operacoes,
                    "quantidade": 1,
                    "ambiente": _amb,
                    "pavimento": _pav,
                })
                idx += 1

    return parts


def group_similar_parts(parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = {}
    for p in parts:
        # Serializa operações para agrupamento estrito
        ops_key = tuple(
            (o.get("tipo"), o.get("face"), o.get("x"), o.get("y"), o.get("diametro"))
            for o in p.get("operacoes", [])
        )
        key = (
            p["nome"],
            p["comprimento"],
            p["largura"],
            p["espessura"],
            p["material"],
            p["fita_c1"],
            p["fita_c2"],
            p["fita_l1"],
            p["fita_l2"],
            p.get("espessura_fita", 0.45),
            p["ignorar_veio"],
            ops_key,
        )
        if key in grouped:
            grouped[key]["quantidade"] += 1
        else:
            grouped[key] = dict(p)
    return list(grouped.values())


