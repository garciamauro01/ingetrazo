# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes de regressão para furações e usinagens técnicas (Minifix, Cavilhas e Parafusos)."""

from __future__ import annotations

import pytest

from trazomob.builders.balcoes_aereos import BalcaoAereoBuilder
from trazomob.production.machining import (
    make_cabinet_joint_holes,
)


def test_furacoes_distancias_padroes_minifix_e_cavilha():
    """Garante que parafusos/minifix ficam a 50mm e cavilhas a 100mm das bordas."""
    ops = make_cabinet_joint_holes(
        comprimento_junta_mm=550.0,
        posicao_borda_mm=7.5,
        usar_minifix=True,
        dispositivo_fixacao="minifix_cavilha",
    )

    pinos = [o for o in ops if "pino minifix" in o.descricao.lower()]
    cavilhas = [o for o in ops if "cavilha" in o.descricao.lower()]

    assert len(pinos) == 2
    assert pinos[0].x == 50.0
    assert pinos[1].x == 500.0  # 550 - 50
    assert pinos[0].diametro == 5.0
    assert pinos[0].profundidade == 11.0

    assert len(cavilhas) == 2
    assert cavilhas[0].x == 100.0
    assert cavilhas[1].x == 450.0  # 550 - 100
    assert cavilhas[0].diametro == 8.0
    assert cavilhas[0].profundidade == 11.0


def test_furacoes_orientacao_faces_nicho_minifix():
    """Valida orientação das furações no Nicho:
    - Laterais: furos somente na face interna (+X na esq, -X na dir).
    - Base: tambores na face superior (+Z, para dentro do móvel).
    - Tampo: tambores na face inferior (-Z, para dentro do móvel).
    - Prateleira: exclusivamente cavilhas (sem minifix) nos topos e a 50mm das bordas.
    """
    grps = BalcaoAereoBuilder.build_nicho(
        largura_mm=800,
        altura_mm=750,
        prof_mm=300,
        divisoes_horiz=1,
        dispositivo_fixacao="minifix_cavilha",
    )

    by_name = {g.name: g for g in grps}

    # 1. Lateral Esquerda: furos na face interna (+X)
    lat_esq = by_name["Nicho - Lateral Esquerda"]
    holes_esq = [f for f in lat_esq.mesh.faces if f.holes]
    assert len(holes_esq) == 1
    assert round(holes_esq[0].normal().x(), 2) == 1.0
    assert round(holes_esq[0].normal().y(), 2) == 0.0
    assert round(holes_esq[0].normal().z(), 2) == 0.0

    # 2. Lateral Direita: furos na face interna (-X)
    lat_dir = by_name["Nicho - Lateral Direita"]
    holes_dir = [f for f in lat_dir.mesh.faces if f.holes]
    assert len(holes_dir) == 1
    assert round(holes_dir[0].normal().x(), 2) == -1.0
    assert round(holes_dir[0].normal().y(), 2) == 0.0
    assert round(holes_dir[0].normal().z(), 2) == 0.0

    # 3. Base Inferior: tambor de 15mm na face superior (+Z, virado para dentro)
    base = by_name["Nicho - Base Inferior"]
    face_tambor_base = next(f for f in base.mesh.faces if f.holes and abs(f.normal().z()) > 0.5)
    assert round(face_tambor_base.normal().z(), 2) == 1.0  # +Z

    # Topos laterais da base têm furos (cavilhas e passagem de minifix)
    faces_topos_base = [f for f in base.mesh.faces if f.holes and abs(f.normal().x()) > 0.5]
    assert len(faces_topos_base) == 2  # esquerda (-X) e direita (+X)

    # 4. Tampo Superior: tambor de 15mm na face inferior (-Z, virado para dentro)
    tampo = by_name["Nicho - Tampo Superior"]
    face_tambor_tampo = next(f for f in tampo.mesh.faces if f.holes and abs(f.normal().z()) > 0.5)
    assert round(face_tambor_tampo.normal().z(), 2) == -1.0  # -Z

    # 5. Prateleira (Divisao Horiz): apenas cavilhas nos topos, a 50mm das bordas
    prat = by_name["Nicho - Divisao Horiz 1"]
    prat_ops = prat.ext.get("trazomob", {}).get("operacoes", [])
    assert all("cavilha" in o["descricao"].lower() for o in prat_ops)
    assert not any("minifix" in o["descricao"].lower() for o in prat_ops)
    assert not any("parafuso" in o["descricao"].lower() for o in prat_ops)
    # 2 furos no topo esquerdo e 2 no direito
    assert len(prat_ops) == 4
    for o in prat_ops:
        assert o["diametro"] == 8.0
        assert o["profundidade"] == 20.0
        assert o["x"] in (50.0, 250.0)


def test_modo_apenas_parafuso_elimina_cavilhas_da_caixa():
    """Garante que no modo 'apenas_parafuso':
    - Laterais têm furos passantes para parafuso e NENHUMA cavilha de junção com base/tampo.
    - Base e Tampo têm furos guia de 40mm no topo e ZERO cavilhas e ZERO tambores na face.
    """
    grps = BalcaoAereoBuilder.build_nicho(
        largura_mm=800,
        altura_mm=750,
        prof_mm=300,
        divisoes_horiz=0,
        dispositivo_fixacao="apenas_parafuso",
    )
    by_name = {g.name: g for g in grps}

    lat_esq_ops = by_name["Nicho - Lateral Esquerda"].ext.get("trazomob", {}).get("operacoes", [])
    base_ops = by_name["Nicho - Base Inferior"].ext.get("trazomob", {}).get("operacoes", [])
    tampo_ops = by_name["Nicho - Tampo Superior"].ext.get("trazomob", {}).get("operacoes", [])

    # Na lateral: apenas furos passantes de parafuso
    assert all("parafuso" in o["descricao"].lower() for o in lat_esq_ops)
    assert not any("cavilha" in o["descricao"].lower() for o in lat_esq_ops)
    assert not any("minifix" in o["descricao"].lower() for o in lat_esq_ops)

    # Na base e tampo: apenas furos guia no topo com 40mm
    for ops in (base_ops, tampo_ops):
        assert all("parafuso" in o["descricao"].lower() for o in ops)
        assert not any("cavilha" in o["descricao"].lower() for o in ops)
        assert not any("tambor" in o["descricao"].lower() for o in ops)
        for o in ops:
            assert o["profundidade"] == 40.0
            assert o["diametro"] == 3.5


def test_modo_apenas_cavilhas_elimina_minifix_e_parafusos():
    """Garante que no modo 'apenas_cavilhas' não há furos de parafuso nem minifix."""
    grps = BalcaoAereoBuilder.build_nicho(
        largura_mm=800,
        altura_mm=750,
        prof_mm=300,
        divisoes_horiz=0,
        dispositivo_fixacao="apenas_cavilhas",
    )
    by_name = {g.name: g for g in grps}

    lat_ops = by_name["Nicho - Lateral Esquerda"].ext.get("trazomob", {}).get("operacoes", [])
    base_ops = by_name["Nicho - Base Inferior"].ext.get("trazomob", {}).get("operacoes", [])

    assert all("cavilha" in o["descricao"].lower() for o in lat_ops)
    assert not any("parafuso" in o["descricao"].lower() for o in lat_ops)
    assert not any("minifix" in o["descricao"].lower() for o in lat_ops)

    assert all("cavilha" in o["descricao"].lower() for o in base_ops)
    assert not any("parafuso" in o["descricao"].lower() for o in base_ops)
    assert not any("minifix" in o["descricao"].lower() for o in base_ops)


@pytest.mark.parametrize("disp, esperados_por_ponta", [
    ("minifix_cavilha", {"minifix": 1, "cavilha": 1, "parafuso": 0}),
    ("parafuso", {"minifix": 0, "cavilha": 1, "parafuso": 1}),
    ("apenas_parafuso", {"minifix": 0, "cavilha": 0, "parafuso": 2}),
    ("apenas_cavilhas", {"minifix": 0, "cavilha": 2, "parafuso": 0}),
])
def test_furacoes_travessas_duplas_cabeça_25mm(disp, esperados_por_ponta):
    """Garante que as travessas recebem furações em dupla na cabeça (topos esq/dir) a 25mm de cada face."""
    grps = BalcaoAereoBuilder.build_balcao(
        largura_mm=800,
        altura_mm=750,
        prof_mm=550,
        num_portas=2,
        num_prateleiras=0,
        num_divisoes=0,
        dispositivo_fixacao=disp,
    )
    by_name = {g.name: g for g in grps}

    # Verifica furações na cabeça da travessa frontal
    trav_f = next(g for name, g in by_name.items() if "travessa frontal" in name.lower())
    ops_f = trav_f.ext.get("trazomob", {}).get("operacoes", [])

    # Topo esquerdo (-X): exatamente 2 furos a x=25mm e x=45mm (70 - 25)
    furos_esq = [o for o in ops_f if o.get("face") == "esquerda"]
    assert len(furos_esq) == 2
    xs_esq = sorted(o["x"] for o in furos_esq)
    assert xs_esq == [25.0, 45.0]

    # Topo direito (+X): exatamente 2 furos a x=25mm e x=45mm
    furos_dir = [o for o in ops_f if o.get("face") == "direita"]
    assert len(furos_dir) == 2
    xs_dir = sorted(o["x"] for o in furos_dir)
    assert xs_dir == [25.0, 45.0]

    # Quantidades por tipo de dispositivo
    n_mini = sum(1 for o in furos_esq if "minifix" in o["descricao"].lower())
    n_cav = sum(1 for o in furos_esq if "cavilha" in o["descricao"].lower())
    n_paraf = sum(1 for o in furos_esq if "parafuso" in o["descricao"].lower())

    assert n_mini == esperados_por_ponta["minifix"]
    assert n_cav == esperados_por_ponta["cavilha"]
    assert n_paraf == esperados_por_ponta["parafuso"]


def test_transporte_furacao_cavilha_prateleira_para_laterais():
    """Garante que quando há prateleira interna no balcão/aéreo/nicho:
    1. A lateral esquerda e direita recebem furos de cavilha de prateleira (8mm x 11mm) na face interna.
    2. A quantidade e posições dos furos nas laterais correspondem exatamente às prateleiras.
    """
    grps = BalcaoAereoBuilder.build_balcao(
        largura_mm=800,
        altura_mm=720,
        prof_mm=550,
        esp_mm=15.0,
        num_portas=2,
        num_prateleiras=1,
        gerar_furacao=True,
    )
    by_name = {g.name: g for g in grps}

    lat_esq = by_name["Balcao - Lateral Esquerda"]
    lat_dir = by_name["Balcao - Lateral Direita"]

    ops_esq = lat_esq.ext.get("trazomob", {}).get("operacoes", [])
    ops_dir = lat_dir.ext.get("trazomob", {}).get("operacoes", [])

    furos_prat_esq = [o for o in ops_esq if "prateleira" in o["descricao"].lower()]
    furos_prat_dir = [o for o in ops_dir if "prateleira" in o["descricao"].lower()]

    # Para 1 prateleira: 2 furos na lateral esquerda e 2 na lateral direita
    assert len(furos_prat_esq) == 2
    assert len(furos_prat_dir) == 2

    for op in furos_prat_esq + furos_prat_dir:
        assert op["diametro"] == 8.0
        assert op["profundidade"] == 11.0
        assert op["face"] == "traseira"  # face interna da chapa lateral

    # 3. Marcações de calço de dobradiça nas laterais (Sistema 32: 37mm da frente, entre-furos 32mm)
    calcos_esq = [o for o in ops_esq if "calço" in o["descricao"].lower() or "calco" in o["descricao"].lower()]
    calcos_dir = [o for o in ops_dir if "calço" in o["descricao"].lower() or "calco" in o["descricao"].lower()]
    # Para 2 portas (1 porta na esq e 1 na dir com 2 dobradiças cada = 4 furos em cada lateral)
    assert len(calcos_esq) == 4
    assert len(calcos_dir) == 4
    for op in calcos_esq + calcos_dir:
        assert op["face"] == "traseira"  # face interna
        assert op["x"] == 37.0           # Sistema 32: 37mm do bordo frontal
        assert op["diametro"] == 2.5
        assert op["profundidade"] == 2.5


def test_divisoria_vertical_cavilha_cima_e_baixo():
    """Valida furação de cavilha na divisória vertical:
    - Furos no topo superior (+Z) e base inferior (-Z)
    - Configurável: ambos, apenas cima, apenas baixo, nenhum
    - Malha watertight / sólida (manifold) verificada pelo solid_volume
    """
    from core.solids import is_solid, solid_volume
    from trazomob.builders.parts import CustomPartsBuilder
    from trazomob.production.machining import make_vertical_divider_joint_holes

    # 1. Teste do gerador com 'ambos'
    ops_ambos = make_vertical_divider_joint_holes(
        prof_divisoria_mm=500.0,
        esp_divisoria_mm=15.0,
        furacao_cima=True,
        furacao_baixo=True,
    )
    assert len(ops_ambos) == 4
    topos = [o for o in ops_ambos if o.face == "topo"]
    bases = [o for o in ops_ambos if o.face == "base"]
    assert len(topos) == 2
    assert len(bases) == 2
    for op in topos + bases:
        assert op.diametro == 8.0
        assert op.profundidade == 20.0
        assert op.y == 7.5  # centrado na chapa de 15mm

    # 2. Teste com apenas em cima
    ops_cima = make_vertical_divider_joint_holes(
        prof_divisoria_mm=500.0,
        furacao_cima=True,
        furacao_baixo=False,
    )
    assert len(ops_cima) == 2
    assert all(o.face == "topo" for o in ops_cima)

    # 3. Teste com apenas embaixo
    ops_baixo = make_vertical_divider_joint_holes(
        prof_divisoria_mm=500.0,
        furacao_cima=False,
        furacao_baixo=True,
    )
    assert len(ops_baixo) == 2
    assert all(o.face == "base" for o in ops_baixo)

    # 4. Teste com nenhum
    ops_nenhum = make_vertical_divider_joint_holes(
        prof_divisoria_mm=500.0,
        furacao_cima=False,
        furacao_baixo=False,
    )
    assert len(ops_nenhum) == 0

    # 5. Geometria 3D sólida da divisória com cavilhas nos topos
    grps = CustomPartsBuilder.build_peca_avulsa(
        subtipo="divisoria_vertical",
        largura_mm=15.0,
        altura_mm=700.0,
        prof_mm=500.0,
        esp_mm=15.0,
        cavilha_topo_superior=True,
        cavilha_topo_inferior=True,
    )
    assert len(grps) == 1
    div_grp = grps[0]
    assert is_solid(div_grp)
    assert solid_volume(div_grp) is not None
    # 4 cavilhas = 4 furos em faces
    holes_in_faces = sum(len(f.holes) for f in div_grp.mesh.faces)
    assert holes_in_faces == 4




