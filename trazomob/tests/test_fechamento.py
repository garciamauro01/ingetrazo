# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes unitários para o construtor de régua de arremate / fechamento de canto."""
import pytest
from trazomob.builders.fechamento import FechamentoBuilder


def test_build_fechamento_canto_pieces():
    """Verifica a geração das peças: testeira frontal e sarrafo de recuo."""
    pieces = FechamentoBuilder.build_fechamento_canto(
        largura_mm=65.0,
        altura_mm=720.0,
        prof_mm=550.0,
        esp_mm=15.0,
        material="MDF Grafite 15mm",
        offset=(1.0, 0.0, 0.10),
    )

    # Deve gerar 2 peças: Testeira Arremate e Sarrafo de Fixação
    assert len(pieces) == 2
    frente = pieces[0]
    sarrafo = pieces[1]

    assert "Testeira Arremate" in frente.name
    assert "Sarrafo" in sarrafo.name

    # Testa mesh da frente: dimensões L x E x A
    m_frente = frente.mesh
    assert m_frente is not None
    xs = [v.position.x() for v in m_frente.vertices]
    ys = [v.position.y() for v in m_frente.vertices]
    zs = [v.position.z() for v in m_frente.vertices]

    assert abs((max(xs) - min(xs)) - 0.065) < 1e-4
    assert abs((max(ys) - min(ys)) - 0.015) < 1e-4
    assert abs((max(zs) - min(zs)) - 0.720) < 1e-4


def test_build_fechamento_group_structure():
    """Verifica a estrutura do grupo mestre com metadados para corte."""
    group = FechamentoBuilder.build_fechamento_group(
        largura_mm=80.0,
        altura_mm=850.0,
        prof_mm=550.0,
        esp_mm=15.0,
        material="MDF Louro Freijó 15mm",
        rot_z=90.0,
    )

    assert "Arremate de Canto 80mm" in group.name
    assert "trazomob_module" in group.ext
    mod_info = group.ext["trazomob_module"]
    assert mod_info["tipo"] == "fechamento_canto"
    assert mod_info["largura"] == 80.0
    assert mod_info["altura"] == 850.0
    assert mod_info["rot_z"] == 90.0

    children = getattr(group, "children", []) or getattr(group, "groups", [])
    assert len(children) == 2
