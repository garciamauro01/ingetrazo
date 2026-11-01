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
    """Cria uma porta paramétrica dinâmica 100% nativa com batente vazado em 'U' e folha móvel."""
    total_w = 0.90
    total_h = 2.10
    wall_th = 0.14
    post_w = 0.05
    head_h = 0.05

    # 1. Batente vazado em 'U' invertido (sem fechar o vão onde a folha gira)
    frame_mesh = Mesh()
    # Montante esquerdo
    left_post = _create_box_mesh(post_w, wall_th, total_h, dx=0.0, dy=0.0, dz=0.0)
    for f in left_post.faces:
        frame_mesh.add_face([QVector3D(v) for v in f.vertices])

    # Montante direito
    right_post = _create_box_mesh(post_w, wall_th, total_h, dx=total_w - post_w, dy=0.0, dz=0.0)
    for f in right_post.faces:
        frame_mesh.add_face([QVector3D(v) for v in f.vertices])

    # Travessa superior
    top_head = _create_box_mesh(total_w - 2 * post_w, wall_th, head_h, dx=post_w, dy=0.0, dz=total_h - head_h)
    for f in top_head.faces:
        frame_mesh.add_face([QVector3D(v) for v in f.vertices])

    door_group = Group(frame_mesh, name="Porta_Dinamica")
    door_group.component = True

    # 2. Folha da porta (Leaf)
    # A folha tem origem local (0, 0, 0) exatamente no pivô da dobradiça!
    leaf_w = total_w - 2 * post_w   # 0.80m de largura
    leaf_th = 0.035                 # 3.5cm de espessura
    leaf_h = total_h - head_h - 0.01 # 2.04m de altura

    leaf_mesh = _create_box_mesh(leaf_w, leaf_th, leaf_h, dx=0.0, dy=0.0, dz=0.0)
    leaf_group = Group(leaf_mesh, name="Folha")
    leaf_group.component = True

    # Posiciona o pivô da folha em X=0.05 (junto ao montante esquerdo), Y=0.03 (rebaixo), Z=0.01 (folga chão)
    leaf_dc = ensure_dc_data(leaf_group)
    leaf_dc["name"] = "Folha"
    leaf_dc["attributes"]["X"] = {"label": "X", "value": post_w, "formula": "", "unit": "m", "editable": False}
    leaf_dc["attributes"]["Y"] = {"label": "Y", "value": 0.03, "formula": "", "unit": "m", "editable": False}
    leaf_dc["attributes"]["Z"] = {"label": "Z", "value": 0.01, "formula": "", "unit": "m", "editable": False}
    # A rotação RotZ da Folha herda dinamicamente do atributo Abertura do componente pai (sinal negativo para abrir para fora)
    leaf_dc["attributes"]["RotZ"] = {
        "label": "RotZ",
        "value": -90.0,
        "formula": "=-Parent!Abertura",
        "unit": "deg",
        "editable": False,
    }
    # O material da folha também herda do atributo Material do pai
    leaf_dc["attributes"]["Material"] = {
        "label": "Material",
        "value": "#8B5A2B",
        "formula": "=Parent!Material",
        "unit": "",
        "editable": False,
    }

    # Vincula a folha dentro do componente pai da porta
    door_group.adopt([leaf_group])
    leaf_group.owner = door_group

    door_dc = ensure_dc_data(door_group)
    door_dc["name"] = "Porta Dinamica Parametrica"
    door_dc["description"] = "Porta dinamica com batente e folha articulada. Use a ferramenta Interagir para abrir/fechar."
    door_dc["onClick"] = 'ANIMATE("Folha!RotZ", 0, -Abertura)'

    # Adiciona opções de usuário demonstrando paridade com o painel de opções
    door_dc["attributes"]["Abertura"] = {
        "label": "Ângulo de Abertura",
        "value": 90,
        "formula": "",
        "unit": "graus",
        "display_unit": "deg",
        "user_editable": True,
        "user_visible": True,
        "options": [
            {"label": "Fechada (0°)", "value": 0},
            {"label": "Semiaberta (45°)", "value": 45},
            {"label": "Aberta (90°)", "value": 90},
            {"label": "Totalmente aberta (120°)", "value": 120},
        ],
    }
    door_dc["attributes"]["Material"] = {
        "label": "Cor / Acabamento",
        "value": "#8B5A2B",
        "formula": "",
        "unit": "",
        "display_unit": "",
        "user_editable": True,
        "user_visible": True,
        "options": [
            {"label": "Madeira Clara", "value": "#D2B48C"},
            {"label": "Madeira Escura", "value": "#8B5A2B"},
            {"label": "Branco Neve", "value": "#FFFFFF"},
        ],
    }

    evaluate_dc(door_group)
    return door_group
