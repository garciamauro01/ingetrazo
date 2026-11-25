# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes de regressão para ocultação de cotas em faces encostadas de módulos."""
from __future__ import annotations

import pytest
from PySide6.QtGui import QVector3D
from PySide6.QtWidgets import QApplication, QWidget

from core.group import Group
from core.mesh import Mesh
from core.scene import Scene
from trazomob.interaction.magnetic_drag import MagneticModuleDragFilter


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _MiniViewport(QWidget):
    def __init__(self, scene: Scene) -> None:
        super().__init__()
        self.scene = scene
        self.camera = None
        self._ext_overlays = []


def _make_box_group(
    name: str,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    z0: float,
    z1: float,
    *,
    ext: dict | None = None,
    layer: str = "Layer0",
    hidden: bool = False,
) -> Group:
    mesh = Mesh()
    v0 = QVector3D(x0, y0, z0)
    v1 = QVector3D(x1, y0, z0)
    v2 = QVector3D(x1, y1, z0)
    v3 = QVector3D(x0, y1, z0)
    v4 = QVector3D(x0, y0, z1)
    v5 = QVector3D(x1, y0, z1)
    v6 = QVector3D(x1, y1, z1)
    v7 = QVector3D(x0, y1, z1)
    mesh.add_face([v0, v3, v2, v1])  # fundo z0
    mesh.add_face([v4, v5, v6, v7])  # topo z1
    mesh.add_face([v0, v1, v5, v4])  # frente -Y
    mesh.add_face([v2, v3, v7, v6])  # traseira +Y
    mesh.add_face([v1, v2, v6, v5])  # direita +X
    mesh.add_face([v3, v0, v4, v7])  # esquerda -X
    grp = Group(mesh, name=name)
    grp.layer = layer
    grp.hidden = hidden
    if ext is not None:
        grp.ext = ext
    return grp


def _make_room_walls_scene() -> tuple[Scene, Group]:
    """Cria cômodo [0..4] x [0..3] x [0..2.6] com uma parede externa extra em y=5."""
    scene = Scene()
    wall = _make_box_group(
        "Parede Norte",
        0.0, 4.0, 3.0, 3.15, 0.0, 2.6,
        ext={"trazomob_wall": {"pontos": [[0.0, 3.0, 0.0], [4.0, 3.0, 0.0]], "espessura": 0.15}},
        layer="Parede",
    )
    far_wall = _make_box_group(
        "Parede Externa Atrás",
        0.0, 4.0, 5.0, 5.15, 0.0, 2.6,
        ext={"trazomob_wall": {"pontos": [[0.0, 5.0, 0.0], [4.0, 5.0, 0.0]], "espessura": 0.15}},
        layer="Parede",
    )
    south_wall = _make_box_group(
        "Parede Sul",
        0.0, 4.0, -0.15, 0.0, 0.0, 2.6,
        ext={"trazomob_wall": {"pontos": [[0.0, 0.0, 0.0], [4.0, 0.0, 0.0]], "espessura": 0.15}},
        layer="Parede",
    )
    west_wall = _make_box_group(
        "Parede Oeste",
        -0.15, 0.0, 0.0, 3.0, 0.0, 2.6,
        ext={"trazomob_wall": {"pontos": [[0.0, 0.0, 0.0], [0.0, 3.0, 0.0]], "espessura": 0.15}},
        layer="Parede",
    )
    east_wall = _make_box_group(
        "Parede Leste",
        4.0, 4.15, 0.0, 3.0, 0.0, 2.6,
        ext={"trazomob_wall": {"pontos": [[4.0, 0.0, 0.0], [4.0, 3.0, 0.0]], "espessura": 0.15}},
        layer="Parede",
    )
    for w in (wall, far_wall, south_wall, west_wall, east_wall):
        scene.groups.append(w)
    return scene, wall


def _cota_directions(cotas) -> list[tuple[float, float, float]]:
    dirs = []
    for p0, p1, _col, _off in cotas:
        d = (p1 - p0).normalized()
        dirs.append((round(d.x(), 2), round(d.y(), 2), round(d.z(), 2)))
    return dirs


def test_hide_cota_when_flush_with_wall_and_neighbor_module(qapp):
    scene, _ = _make_room_walls_scene()
    # Mod A encostado na parede Norte (y=3.0) e com Mod B encostado na esquerda (x=1.0)
    mod_a = _make_box_group(
        "Balcao_A",
        1.0, 1.8, 2.4, 3.0, 0.0, 0.72,
        ext={"trazomob_module": {"rot_z": 0.0}, "trazomob": {"kind": "module"}},
    )
    mod_b = _make_box_group(
        "Balcao_B",
        0.2, 1.0, 2.4, 3.0, 0.0, 0.72,
        ext={"trazomob_module": {"rot_z": 0.0}, "trazomob": {"kind": "module"}},
    )
    scene.groups.extend([mod_a, mod_b])

    vp = _MiniViewport(scene)
    f = MagneticModuleDragFilter(vp, parent=vp)

    cotas = f._compute_cotas_for_bounds((1.0, 1.8, 2.4, 3.0, 0.0, 0.72), exclude_module=mod_a)
    dirs = _cota_directions(cotas)

    # Fundo (+Y, parede Norte) e esquerda (-X, Balcao_B) devem estar ocultos
    assert (0.0, 1.0, 0.0) not in dirs
    assert (-1.0, 0.0, 0.0) not in dirs
    # Direita (+X -> Parede Leste) e frente aberta (-Y -> Parede Sul) permanecem visíveis
    assert (1.0, 0.0, 0.0) in dirs
    assert (0.0, -1.0, 0.0) in dirs


def test_hide_cota_on_sub_5mm_gap_and_non_module_obstacle_only_when_overlapping_z(qapp):
    scene, _ = _make_room_walls_scene()
    # Aéreo elevado (z=1.50..2.20) encostado no fundo (+Y, 2mm de folga) e numa geladeira não-módulo à direita
    mod_aereo = _make_box_group(
        "Aereo",
        1.0, 1.8, 2.65, 2.998, 1.50, 2.20,
        ext={"trazomob_module": {"rot_z": 0.0}, "trazomob": {"kind": "module"}},
    )
    geladeira = _make_box_group(
        "Geladeira",
        1.802, 2.6, 2.35, 3.0, 0.0, 2.00,
        ext=None,
    )
    # Tampo abaixo do aéreo (não tem sobreposição em Z -> não deve ocultar nada lateralmente)
    balcao_abaixo = _make_box_group(
        "TampoInferior",
        0.95, 1.0, 2.4, 3.0, 0.85, 0.90,
        ext=None,
    )
    # Nicho oculto à esquerda (hidden=True -> ignorado)
    hidden_grp = _make_box_group(
        "Oculto",
        0.5, 1.0, 2.5, 3.0, 1.50, 2.20,
        hidden=True,
    )
    scene.groups.extend([mod_aereo, geladeira, balcao_abaixo, hidden_grp])

    vp = _MiniViewport(scene)
    f = MagneticModuleDragFilter(vp, parent=vp)

    cotas = f._compute_cotas_for_bounds((1.0, 1.8, 2.65, 2.998, 1.50, 2.20), exclude_module=mod_aereo)
    dirs = _cota_directions(cotas)

    # Fundo (+Y, 2mm) e direita (+X, geladeira 2mm) ocultos
    assert (0.0, 1.0, 0.0) not in dirs
    assert (1.0, 0.0, 0.0) not in dirs
    # Esquerda aberta (-X) e cota vertical (-Z) mantidas
    assert (-1.0, 0.0, 0.0) in dirs
    assert (0.0, 0.0, 1.0) in dirs
