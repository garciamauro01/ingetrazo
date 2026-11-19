# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes de configuração do lado de abertura em portas únicas e ímpares (porta isolada)."""

from __future__ import annotations

import pytest

from trazomob.builders.cabinet import CabinetBuilder
from trazomob.interaction.interact import CabinetInteract


def _get_doors(module_group):
    """Retorna todas as peças de porta de giro do módulo."""
    doors = []
    for p in getattr(module_group, "children", []):
        meta = getattr(p, "ext", {}).get("trazomob", {}) if getattr(p, "ext", None) else {}
        if "porta" in p.name.lower() and "correr" not in p.name.lower() and "basculante" not in p.name.lower():
            if meta.get("door_side") in ("left", "right"):
                doors.append(p)
    # Ordena da esquerda para a direita pela coordenada X mínima dos vértices
    def _min_x(piece):
        if piece.mesh and piece.mesh.vertices:
            return min(v.position.x() for v in piece.mesh.vertices)
        return 0.0
    doors.sort(key=_min_x)
    return doors


def _get_caneco_xs(door_piece) -> list[float]:
    """Retorna as coordenadas X das furações de caneco da porta."""
    meta = getattr(door_piece, "ext", {}).get("trazomob", {})
    ops = meta.get("operacoes", [])
    return [float(op["x"]) for op in ops if "caneco" in str(op.get("descricao", "")).lower()]


def _has_calco_holes(module_group, lateral_substr: str) -> bool:
    """Verifica se a peça lateral/divisória contém furações de calço de dobradiça."""
    for p in getattr(module_group, "children", []):
        if lateral_substr.lower() in p.name.lower():
            meta = getattr(p, "ext", {}).get("trazomob", {}) if getattr(p, "ext", None) else {}
            ops = meta.get("operacoes", [])
            if any("calço" in str(op.get("descricao", "")).lower() or "calco" in str(op.get("descricao", "")).lower() for op in ops):
                return True
    return False


@pytest.mark.parametrize(
    "tipo,extra_params",
    [
        ("balcao", {"largura": 400.0, "altura": 720.0, "profundidade": 550.0, "num_portas": 1}),
        ("aereo", {"largura": 400.0, "altura": 700.0, "profundidade": 350.0, "num_portas": 1}),
        ("balcao_misto", {"largura": 850.0, "altura": 720.0, "profundidade": 550.0, "largura_gaveteiro": 450.0, "num_portas": 1}),
        ("balcao_pia", {"largura": 500.0, "altura": 720.0, "profundidade": 550.0, "num_portas": 1}),
        ("roupeiro", {"largura": 500.0, "altura": 2200.0, "profundidade": 550.0, "num_portas": 1}),
        ("armario_1p_cabide", {"largura": 500.0, "altura": 2200.0, "profundidade": 550.0, "num_portas": 1}),
        ("armario_prateleiras", {"largura": 450.0, "altura": 2200.0, "profundidade": 500.0, "num_portas": 1}),
        ("armario_1p_prat", {"largura": 450.0, "altura": 2200.0, "profundidade": 500.0, "num_portas": 1}),
        ("torre_quente", {"largura": 550.0, "altura": 2200.0, "profundidade": 580.0}),
        ("peca_porta", {"largura": 450.0, "altura": 700.0, "profundidade": 15.0}),
    ],
)
def test_porta_unica_esquerda_vs_direita(tipo: str, extra_params: dict):
    """Em todos os módulos com 1 porta, alternar lado_abertura_porta entre esquerda e direita deve inverter:
    - metadado door_side ('left' vs 'right')
    - tipo de interação cinemática ('door_left' vs 'door_right')
    - lado dos furos de caneco na porta (próximo a X=22mm vs próximo a L-22mm)
    """
    params_esq = {"tipo": tipo, "lado_abertura_porta": "esquerda", **extra_params}
    params_dir = {"tipo": tipo, "lado_abertura_porta": "direita", **extra_params}

    mod_esq = CabinetBuilder.build_module_group(params_esq)
    mod_dir = CabinetBuilder.build_module_group(params_dir)

    doors_esq = _get_doors(mod_esq)
    doors_dir = _get_doors(mod_dir)

    assert len(doors_esq) == 1, f"{tipo} deveria ter 1 porta (esquerda)"
    assert len(doors_dir) == 1, f"{tipo} deveria ter 1 porta (direita)"

    d_esq = doors_esq[0]
    d_dir = doors_dir[0]

    meta_esq = d_esq.ext["trazomob"]
    meta_dir = d_dir.ext["trazomob"]

    assert meta_esq["door_side"] == "left", f"{tipo}: door_side deveria ser 'left'"
    assert meta_dir["door_side"] == "right", f"{tipo}: door_side deveria ser 'right'"

    # Cinemática de abertura no clique 3D
    assert CabinetInteract.get_piece_interaction_type(d_esq.name) == "door_left"
    assert CabinetInteract.get_piece_interaction_type(d_dir.name) == "door_right"

    # Posição dos canecos de dobradiça na porta
    larg_mm = float(meta_esq["largura"])
    xs_esq = _get_caneco_xs(d_esq)
    xs_dir = _get_caneco_xs(d_dir)
    assert xs_esq and xs_dir, f"{tipo}: portas devem ter furação de caneco"
    assert all(x < larg_mm * 0.5 for x in xs_esq), f"{tipo}: canecos na porta esquerda devem ficar na borda esquerda (< metade)"
    assert all(x > larg_mm * 0.5 for x in xs_dir), f"{tipo}: canecos na porta direita devem ficar na borda direita (> metade)"


@pytest.mark.parametrize(
    "tipo,extra_params",
    [
        ("balcao", {"largura": 1200.0, "altura": 720.0, "profundidade": 550.0, "num_portas": 3}),
        ("aereo", {"largura": 1200.0, "altura": 700.0, "profundidade": 350.0, "num_portas": 3}),
        ("balcao_misto", {"largura": 1650.0, "altura": 720.0, "profundidade": 550.0, "largura_gaveteiro": 450.0, "num_portas": 3}),
        ("balcao_pia", {"largura": 1200.0, "altura": 720.0, "profundidade": 550.0, "num_portas": 3}),
        ("roupeiro", {"largura": 1350.0, "altura": 2200.0, "profundidade": 550.0, "num_portas": 3}),
        ("armario_prateleiras", {"largura": 1350.0, "altura": 2200.0, "profundidade": 500.0, "num_portas": 3}),
        ("armario_3p_divisao", {"largura": 1350.0, "altura": 2200.0, "profundidade": 550.0}),
    ],
)
def test_tres_portas_isolada_esquerda_vs_direita(tipo: str, extra_params: dict):
    """Em módulos com número ímpar de portas (3 portas):
    - As 2 primeiras portas formam um par conjugado ('left', 'right')
    - A 3ª porta (porta isolada) deve obedecer a configuração lado_abertura_porta ('esquerda' -> 'left', 'direita' -> 'right').
    """
    params_esq = {"tipo": tipo, "lado_abertura_porta": "esquerda", **extra_params}
    params_dir = {"tipo": tipo, "lado_abertura_porta": "direita", **extra_params}

    mod_esq = CabinetBuilder.build_module_group(params_esq)
    mod_dir = CabinetBuilder.build_module_group(params_dir)

    doors_esq = _get_doors(mod_esq)
    doors_dir = _get_doors(mod_dir)

    assert len(doors_esq) == 3, f"{tipo} deveria ter 3 portas"
    assert len(doors_dir) == 3, f"{tipo} deveria ter 3 portas"

    # Par conjugado (Portas 1 e 2) permanece sempre Esq + Dir
    assert doors_esq[0].ext["trazomob"]["door_side"] == "left"
    assert doors_esq[1].ext["trazomob"]["door_side"] == "right"
    assert doors_dir[0].ext["trazomob"]["door_side"] == "left"
    assert doors_dir[1].ext["trazomob"]["door_side"] == "right"

    # Porta isolada (3ª porta) muda conforme lado_abertura_porta
    porta_iso_esq = doors_esq[2]
    porta_iso_dir = doors_dir[2]

    assert porta_iso_esq.ext["trazomob"]["door_side"] == "left", f"{tipo}: 3ª porta isolada deveria ser 'left' quando configurado esquerda"
    assert porta_iso_dir.ext["trazomob"]["door_side"] == "right", f"{tipo}: 3ª porta isolada deveria ser 'right' quando configurado direita"

    assert CabinetInteract.get_piece_interaction_type(porta_iso_esq.name) == "door_left"
    assert CabinetInteract.get_piece_interaction_type(porta_iso_dir.name) == "door_right"

    larg_mm = float(porta_iso_esq.ext["trazomob"]["largura"])
    xs_esq = _get_caneco_xs(porta_iso_esq)
    xs_dir = _get_caneco_xs(porta_iso_dir)
    assert xs_esq and xs_dir
    assert all(x < larg_mm * 0.5 for x in xs_esq)
    assert all(x > larg_mm * 0.5 for x in xs_dir)

