# SPDX-License-Identifier: GPL-3.0-or-later
"""Testes de integração para Ambientes, Pavimentos, Filtro no Cutlist e Offset Z."""

import pytest
from core.scene import Scene
from core.group import Group
from PySide6.QtGui import QVector3D
from trazomob.domain.ambiente import (
    AmbienteBuilder,
    iter_ambientes,
    iter_pavimentos,
    set_ambiente_visivel,
    set_pavimento_visivel,
)
from trazomob.wall.plan_2d import WallGraph2D
from trazomob.wall.mesh_builder import WallMeshBuilder
from trazomob.production.parts import extract_parts


def test_wall_mesh_offset_z_pavimento():
    scene = Scene()
    g = WallGraph2D()
    g.thickness = 0.15
    g.add_segment(0.0, 0.0, 3.0, 0.0)

    # Cria parede no 1º andar com Z base de 2.80m
    wall_grp = g.build_3d_group(scene, altura_m=2.60, z_base=2.80)
    assert wall_grp is not None

    # Todos os vértices devem ter Z >= 2.80m
    zs = [v.position.z() for v in wall_grp.mesh.vertices]
    assert min(zs) >= 2.79
    assert max(zs) >= 5.39


def test_floor_and_ceiling_offset_z():
    scene = Scene()
    pts = [
        QVector3D(0, 0, 0),
        QVector3D(3, 0, 0),
        QVector3D(3, 3, 0),
        QVector3D(0, 3, 0),
    ]

    floor = WallMeshBuilder.build_floor_group(scene, pts, z_base=2.80)
    assert floor is not None
    zs_floor = [v.position.z() for v in floor.mesh.vertices]
    # Topo do piso no Z=2.80, fundo no Z=2.75
    assert max(zs_floor) == pytest.approx(2.80)
    assert min(zs_floor) == pytest.approx(2.75)

    ceiling = WallMeshBuilder.build_ceiling_group(scene, pts, altura_m=2.60, z_base=2.80)
    assert ceiling is not None
    zs_ceil = [v.position.z() for v in ceiling.mesh.vertices]
    # Forro em 2.80 + 2.60 = 5.40m
    assert min(zs_ceil) == pytest.approx(5.40)


def test_sidebar_ambiente_visibility_toggle():
    scene = Scene()
    pav = AmbienteBuilder.ensure_pavimento(scene.groups, "Térreo")
    amb = AmbienteBuilder.build_ambiente_group("Cozinha", [], None, None, pavimento_nome="Térreo")
    AmbienteBuilder.adicionar_ao_pavimento(pav, amb)

    child_mod = Group()
    child_mod.name = "Balcao"
    amb.adopt([child_mod])

    # Oculta ambiente
    set_ambiente_visivel(amb, False)
    assert child_mod.layer == "Hidden"

    # Restaura visibilidade
    set_ambiente_visivel(amb, True)
    assert child_mod.layer == "Ambientes"
