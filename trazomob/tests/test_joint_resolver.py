# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes de validação da sincronização automática de furações e juntas (JointResolver)."""
from trazomob.builders.cabinet import CabinetBuilder


def test_joint_resolver_caixa_geladeira_dobradicas_e_juntas():
    """Valida se a caixa de geladeira gera calços e furações estruturais automaticamente."""
    group = CabinetBuilder.build_module_group({
        "tipo": "caixa_geladeira",
        "largura": 900.0,
        "altura": 2200.0,
        "profundidade": 600.0,
        "dispositivo_fixacao": "minifix_cavilha",
    })

    pecas = {c.name: c for c in group.children}
    lat_esq = pecas["Geladeira - Lateral Esq"]
    lat_dir = pecas["Geladeira - Lateral Dir"]
    tampo = pecas["Geladeira - Tampo Superior"]
    prat_div = pecas["Geladeira - Prateleira Divisoria"]
    porta_esq = pecas["Geladeira - Porta Maleiro Esq"]
    porta_dir = pecas["Geladeira - Porta Maleiro Dir"]

    # Portas do maleiro possuem canecos de dobradiça
    ops_porta_esq = porta_esq.ext["trazomob"]["operacoes"]
    assert any("caneco" in op["descricao"].lower() for op in ops_porta_esq)

    # Lateral esquerda deve ter recebido os calços da porta maleiro esquerda
    ops_lat_esq = lat_esq.ext["trazomob"]["operacoes"]
    calcos_esq = [op for op in ops_lat_esq if "cal" in op["descricao"].lower()]
    assert len(calcos_esq) >= 4  # 2 dobradiças x 2 furos por calço

    # Lateral direita deve ter recebido os calços da porta maleiro direita
    ops_lat_dir = lat_dir.ext["trazomob"]["operacoes"]
    calcos_dir = [op for op in ops_lat_dir if "cal" in op["descricao"].lower()]
    assert len(calcos_dir) >= 4

    # Ambas as laterais devem ter recebido as furações de minifix e cavilhas do tampo e da divisória
    minifix_esq = [op for op in ops_lat_esq if "minifix" in op["descricao"].lower()]
    cavilhas_esq = [op for op in ops_lat_esq if "cavilha" in op["descricao"].lower()]
    assert len(minifix_esq) >= 4  # 2 pontos x 2 peças horizontais
    assert len(cavilhas_esq) >= 4

    # Tampo e divisória devem ter recebido furos de topo e tambores minifix
    ops_tampo = tampo.ext["trazomob"]["operacoes"]
    assert any(op["face"] == "esquerda" for op in ops_tampo)
    assert any(op["face"] == "direita" for op in ops_tampo)
    assert any("tambor minifix" in op["descricao"].lower() for op in ops_tampo)


def test_joint_resolver_balcao_travessas_e_prateleiras():
    """Valida se balcão gera e sincroniza furações de travessas, prateleiras e dobradiças."""
    group = CabinetBuilder.build_module_group({
        "tipo": "balcao",
        "largura": 800.0,
        "altura": 720.0,
        "profundidade": 550.0,
        "dispositivo_fixacao": "minifix_cavilha",
    })

    pecas = {c.name: c for c in group.children}
    lat_esq = pecas["Balcao - Lateral Esquerda"]
    trav_front = pecas["Balcao - Travessa Frontal"]
    prat = pecas["Balcao - Prateleira 1"]

    ops_lat = lat_esq.ext["trazomob"]["operacoes"]
    # Verifica pinos de prateleira na lateral
    assert any("prateleira" in op["descricao"].lower() for op in ops_lat)
    # Verifica furação de travessa na lateral
    assert any("travessa" in op["descricao"].lower() for op in ops_lat)
    # Verifica usinagem nos topos da travessa frontal
    ops_trav = trav_front.ext["trazomob"]["operacoes"]
    assert any(op["face"] in ("esquerda", "direita") for op in ops_trav)


def test_joint_resolver_sem_furacao():
    """Valida que quando gerar_furacao=False nenhuma usinagem é gerada."""
    group = CabinetBuilder.build_module_group({
        "tipo": "caixa_geladeira",
        "largura": 900.0,
        "altura": 2200.0,
        "profundidade": 600.0,
        "gerar_furacao": False,
    })
    for c in group.children:
        ops = (c.ext or {}).get("trazomob", {}).get("operacoes", [])
        assert len(ops) == 0
