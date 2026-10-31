# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
"""Gerador de componentes dinâmicos de teste (Porta Paramétrica com folha articulada)."""
from __future__ import annotations

from PySide6.QtGui import QVector3D
from core.group import Group
from core.mesh import Mesh
from .model import ensure_dc_data, evaluate_dc


def _create_box_mesh(lx: float, ly: float, lz: float, dx: float = 0.0, dy: float = 0.0, dz: float = 0.0) -> Mesh:
    """Cria uma malha sólida paralelepipédica fechada e com normais consistentes."""
    m = Mesh()
    pts = [
        QVector3D(dx, dy, dz),
        QVector3D(dx + lx, dy, dz),
        QVector3D(dx + lx, dy + ly, dz),
        QVector3D(dx, dy + ly, dz),
        QVector3D(dx, dy, dz + lz),
        QVector3D(dx + lx, dy, dz + lz),
        QVector3D(dx + lx, dy + ly, dz + lz),
        QVector3D(dx, dy + ly, dz + lz),
    ]
    # 6 faces orientadas
    m.add_face([pts[0], pts[3], pts[2], pts[1]])  # Inferior
    m.add_face([pts[4], pts[5], pts[6], pts[7]])  # Superior
    m.add_face([pts[0], pts[1], pts[5], pts[4]])  # Frontal
    m.add_face([pts[2], pts[3], pts[7], pts[6]])  # Traseira
    m.add_face([pts[0], pts[4], pts[7], pts[3]])  # Esquerda
    m.add_face([pts[1], pts[2], pts[6], pts[5]])  # Direita
    return m


def create_sample_dynamic_door() -> Group:
    """Cria uma porta paramétrica dinâmica 100% nativa com batente e folha móvel."""
    # 1. Batente (Marco da porta)
    frame_mesh = _create_box_mesh(0.90, 0.15, 2.10)
    door_group = Group(frame_mesh, name="Porta_Dinamica")
    door_group.component = True

    # 2. Folha da porta (Leaf)
    leaf_mesh = _create_box_mesh(0.82, 0.04, 2.05, dx=0.04, dy=0.05, dz=0.02)
    leaf_group = Group(leaf_mesh, name="Folha")
    leaf_group.component = True

    leaf_dc = ensure_dc_data(leaf_group)
    leaf_dc["name"] = "Folha"
    leaf_dc["attributes"]["RotZ"] = {
        "label": "RotZ",
        "value": 0.0,
        "formula": "",
        "unit": "graus",
        "editable": True,
    }

    # Vincula a folha dentro do componente pai da porta
    door_group.adopt([leaf_group])
    leaf_group.owner = door_group

    door_dc = ensure_dc_data(door_group)
    door_dc["name"] = "Porta Dinamica Parametrica"
    door_dc["description"] = "Porta dinamica de teste. Clique na folha ou no batente com a ferramenta Interact para abrir/fechar."
    door_dc["onClick"] = 'ANIMATE("Folha!RotZ", "0", "-90")'

    evaluate_dc(door_group)
    return door_group
