# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Módulo de detecção de colisões para interatividade 3D (Abertura de portas e gavetas).

Permite verificar se portas e gavetas abertas colidem visualmente com puxadores,
marcos de portas, paredes ou outros móveis adjacentes (ex: balcão de canto).
"""
from __future__ import annotations

from typing import Any
from PySide6.QtGui import QVector3D
from core.group import Group


def get_piece_aabb(piece: Group) -> tuple[float, float, float, float, float, float] | None:
    """Calcula a caixa delimitadora AABB (min_x, max_x, min_y, max_y, min_z, max_z) dos vértices da peça."""
    mesh = getattr(piece, "mesh", None)
    if mesh is None or not getattr(mesh, "vertices", None):
        return None
    min_x = min_y = min_z = float("inf")
    max_x = max_y = max_z = float("-inf")
    for v in mesh.vertices:
        p = getattr(v, "position", v)
        x, y, z = p.x(), p.y(), p.z()
        if x < min_x: min_x = x
        if x > max_x: max_x = x
        if y < min_y: min_y = y
        if y > max_y: max_y = y
        if z < min_z: min_z = z
        if z > max_z: max_z = z
    if min_x == float("inf"):
        return None
    return (min_x, max_x, min_y, max_y, min_z, max_z)


def aabb_intersect(
    box_a: tuple[float, float, float, float, float, float],
    box_b: tuple[float, float, float, float, float, float],
    margin: float = 0.003,  # 3mm de tolerância para junções naturais
) -> bool:
    """Verifica se duas AABBs se interceptam com uma tolerância de segurança."""
    ax1, ax2, ay1, ay2, az1, az2 = box_a
    bx1, bx2, by1, by2, bz1, bz2 = box_b

    if (ax2 - margin) < (bx1 + margin) or (ax1 + margin) > (bx2 - margin):
        return False
    if (ay2 - margin) < (by1 + margin) or (ay1 + margin) > (by2 - margin):
        return False
    if (az2 - margin) < (bz1 + margin) or (az1 + margin) > (bz2 - margin):
        return False
    return True


def check_opening_collisions(scene, active_modules: list[Group] | None = None) -> list[dict[str, Any]]:
    """Testa colisões entre todas as peças móveis atualmente abertas e os objetos da cena.

    Retorna uma lista de colisões encontradas:
    [
        {
            "piece_a": Group,
            "piece_b": Group,
            "module_a": Group,
            "module_b": Group,
            "desc": "Gaveta colide com Puxador do Balcão Canto"
        }
    ]
    """
    if scene is None:
        return []

    from ..interaction.interact import CabinetInteract

    groups = getattr(scene, "groups", [])
    open_pieces: list[tuple[Group, Group]] = []  # (piece, module_owner)
    static_pieces: list[tuple[Group, Group | None]] = []

    # 1. Identifica módulos e peças
    for g in groups:
        if getattr(g, "layer", None) in ("Piso", "Floor"):
            continue
        if hasattr(g, "children") and g.children:
            is_mod = hasattr(g, "ext") and isinstance(g.ext, dict) and "trazomob_module" in g.ext
            for child in g.children:
                if CabinetInteract.is_interactive_piece(getattr(child, "name", "")):
                    if getattr(child, "ext", None) and child.ext.get("is_open"):
                        open_pieces.append((child, g))
                    else:
                        static_pieces.append((child, g))
                else:
                    static_pieces.append((child, g))
        else:
            # Objeto avulso (parede, bancada, etc)
            static_pieces.append((g, None))

    if not open_pieces:
        return []

    collisions = []

    # 2. Testa cada peça aberta contra as peças estáticas e outras peças abertas
    for p_open, mod_a in open_pieces:
        box_open = get_piece_aabb(p_open)
        if not box_open:
            continue

        # Não testa contra peças internas do próprio módulo que se movem juntas (ex: gaveta contra suas laterais)
        drawer_id_open = CabinetInteract.get_drawer_id(p_open.name)

        for p_other, mod_b in (static_pieces + open_pieces):
            if p_other is p_open:
                continue

            # Se for do mesmo módulo
            if mod_a is mod_b and mod_a is not None:
                # Se for a mesma gaveta se movendo junta
                if drawer_id_open and CabinetInteract.get_drawer_id(p_other.name) == drawer_id_open:
                    continue
                # Se for o fundo ou base interna do próprio nicho, tolera contato traseiro
                other_name = getattr(p_other, "name", "").lower()
                if "fundo" in other_name or "contra-frente" in other_name:
                    continue

            box_other = get_piece_aabb(p_other)
            if not box_other:
                continue

            if aabb_intersect(box_open, box_other):
                nome_a = getattr(p_open, "name", "Peça Móvel")
                nome_b = getattr(p_other, "name", "Objeto")
                mod_a_nome = getattr(mod_a, "name", "Módulo") if mod_a else ""
                mod_b_nome = getattr(mod_b, "name", "Módulo") if mod_b else ""

                collisions.append({
                    "piece_a": p_open,
                    "piece_b": p_other,
                    "module_a": mod_a,
                    "module_b": mod_b,
                    "desc": f"⚠️ Colisão: '{nome_a}' ({mod_a_nome}) encosta em '{nome_b}' ({mod_b_nome})",
                })

    return collisions
