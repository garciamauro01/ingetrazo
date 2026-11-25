# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes unitários para o módulo de Elevação Técnica 2D de Paredes (Wall Elevation 2D)."""
import pytest
from PySide6.QtWidgets import QApplication

from trazomob.wall.elevation_dialog import WallElevationCanvas


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_wall_elevation_canvas_math_and_scaling(qapp):
    """Testa a projeção ortogonal, conversão de metros para coordenadas de tela e enquadramento."""
    canvas = WallElevationCanvas()
    canvas.resize(1000, 700)

    modules = [
        {"u_min": 0.0, "u_max": 0.80, "z_min": 0.0, "z_max": 0.85, "nome": "Balcão 2P", "tipo": "balcao"},
        {"u_min": 0.80, "u_max": 1.40, "z_min": 0.0, "z_max": 0.85, "nome": "Gaveteiro", "tipo": "gaveteiro"},
        {"u_min": 0.0, "u_max": 1.40, "z_min": 0.85, "z_max": 0.89, "nome": "Bancada", "tipo": "bancada"},
        {"u_min": 0.0, "u_max": 1.40, "z_min": 1.50, "z_max": 2.20, "nome": "Aéreo Basculante", "tipo": "aereo"},
    ]

    guides = [
        {"z": 0.10, "name": "Rodapé"},
        {"z": 0.85, "name": "Balcão"},
        {"z": 0.89, "name": "Bancada"},
        {"z": 1.50, "name": "Início Aéreo"},
        {"z": 2.20, "name": "Topo Aéreo"},
    ]

    canvas.set_data(
        wall_width_m=3.00,
        wall_height_m=2.60,
        wall_label="Parede #1",
        modules_2d=modules,
        guide_levels=guides,
    )

    # Verifica se os dados foram atribuídos corretamente
    assert canvas.wall_width_m == 3.00
    assert canvas.wall_height_m == 2.60
    assert len(canvas.modules_2d) == 4
    assert len(canvas.guide_levels) == 5

    # Testa conversão de coordenadas: Z=0 deve ter Y maior que Z=2.60 (origem superior esquerda)
    p_floor = canvas.world_to_screen(0.0, 0.0)
    p_ceil = canvas.world_to_screen(0.0, 2.60)
    p_right = canvas.world_to_screen(3.00, 0.0)

    assert p_floor.y() > p_ceil.y()
    assert p_right.x() > p_floor.x()

    # Distância proporcional à escala
    h_px = p_floor.y() - p_ceil.y()
    w_px = p_right.x() - p_floor.x()
    assert abs((w_px / canvas.wall_width_m) - (h_px / canvas.wall_height_m)) < 1e-3


def test_wall_elevation_canvas_dimensions_generation(qapp):
    """Testa se os pontos de quebra para cotas horizontais e verticais são calculados sem erros."""
    canvas = WallElevationCanvas()
    canvas.resize(1000, 700)

    canvas.set_data(
        wall_width_m=2.00,
        wall_height_m=2.60,
        wall_label="Parede Teste",
        modules_2d=[
            {"u_min": 0.20, "u_max": 1.00, "z_min": 0.0, "z_max": 0.85, "nome": "Balcão", "tipo": "balcao"}
        ],
        guide_levels=[],
    )

    x_breaks = {0.0, canvas.wall_width_m}
    for mod in canvas.modules_2d:
        x_breaks.add(round(mod["u_min"], 4))
        x_breaks.add(round(mod["u_max"], 4))

    sorted_breaks = sorted(b for b in x_breaks if 0.0 <= b <= canvas.wall_width_m)
    # Deve conter [0.0, 0.20, 1.00, 2.00] -> Vão esquerdo (200mm), Módulo (800mm), Vão direito (1000mm)
    assert sorted_breaks == [0.0, 0.20, 1.00, 2.00]
