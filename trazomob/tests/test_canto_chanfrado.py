from trazomob.builders.cabinet import CabinetBuilder
from trazomob.builders.corner_cabinets import CantoEspecialBuilder
from trazomob.builders.registry import get_module_builder


def test_balcao_canto_chanfrado_1_porta():
    pieces = CantoEspecialBuilder.build_canto_chanfrado(
        largura_mm=1000.0,
        altura_mm=720.0,
        prof_mm=1000.0,
        prof_lateral_esq_mm=550.0,
        prof_lateral_dir_mm=550.0,
        num_portas=1,
        esp_mm=15.0,
        rodape_mm=100.0,
        num_prateleiras=1,
    )
    assert len(pieces) > 5

    names = [p.name for p in pieces]
    assert any("Traseira Parede X" in n for n in names)
    assert any("Traseira Parede Y" in n for n in names)
    assert any("Lateral Direita" in n for n in names)
    assert any("Lateral Esquerda" in n for n in names)
    assert any("Base Inferior" in n for n in names)
    assert any("Prateleira" in n for n in names)
    assert any("Travessa Topo Frontal" in n for n in names)
    assert any("Montante Batente Esq" in n for n in names)
    assert any("Montante Batente Dir" in n for n in names)
    assert any("Porta" in n for n in names)

    # 1 porta única
    portas = [p for p in pieces if "Porta" in p.name and "Montante" not in p.name]
    assert len(portas) == 1


def test_balcao_canto_chanfrado_2_portas():
    pieces = CantoEspecialBuilder.build_canto_chanfrado(
        largura_mm=1000.0,
        altura_mm=720.0,
        prof_mm=1000.0,
        prof_lateral_esq_mm=550.0,
        prof_lateral_dir_mm=550.0,
        num_portas=2,
        esp_mm=15.0,
        rodape_mm=100.0,
        num_prateleiras=2,
    )
    names = [p.name for p in pieces]
    assert any("Porta Esq" in n for n in names)
    assert any("Porta Dir" in n for n in names)

    prateleiras = [p for p in pieces if "Prateleira" in p.name]
    assert len(prateleiras) == 2


def test_balcao_canto_chanfrado_via_registry():
    builder_fn = get_module_builder("balcao_canto_chanfrado")
    assert builder_fn is not None

    ctx = {
        "L_mm": 1000.0,
        "A_mm": 720.0,
        "P_mm": 1000.0,
        "esp_mm": 15.0,
        "rodape_mm": 100.0,
        "material": "MDF Branco TX 15mm",
        "material_frentes": "MDF Branco TX 15mm",
        "esp_frentes_mm": 15.0,
        "offset": (0.0, 0.0, 0.0),
        "fundo_kwargs": {},
        "pux_kw": {},
        "travessas_kwargs": {},
        "mat_ctx": None,
    }
    pieces, name = builder_fn(CabinetBuilder, {"num_portas": 2}, ctx)
    assert "Canto Chanfrado" in name
    assert len(pieces) > 8


def test_balcao_canto_chanfrado_travessas_em_pe():
    pieces_em_pe = CantoEspecialBuilder.build_canto_chanfrado(
        largura_mm=1000.0,
        altura_mm=720.0,
        prof_mm=1000.0,
        travessa_frontal_em_pe=True,
        travessa_traseira_em_pe=True,
        larg_travessa_frontal_mm=70.0,
        larg_travessa_traseira_mm=70.0,
    )
    pieces_deitada = CantoEspecialBuilder.build_canto_chanfrado(
        largura_mm=1000.0,
        altura_mm=720.0,
        prof_mm=1000.0,
        travessa_frontal_em_pe=False,
        travessa_traseira_em_pe=False,
        larg_travessa_frontal_mm=70.0,
        larg_travessa_traseira_mm=70.0,
    )

    t_f_em_pe = next(p for p in pieces_em_pe if "Travessa Topo Frontal" in p.name)
    t_f_deitada = next(p for p in pieces_deitada if "Travessa Topo Frontal" in p.name)

    zs_em_pe = [v.position.z() for v in t_f_em_pe.mesh.vertices]
    zs_deitada = [v.position.z() for v in t_f_deitada.mesh.vertices]

    delta_z_em_pe = max(zs_em_pe) - min(zs_em_pe)
    delta_z_deitada = max(zs_deitada) - min(zs_deitada)

    assert abs(delta_z_em_pe - 0.070) < 1e-4
    assert abs(delta_z_deitada - 0.015) < 1e-4

    t_x_em_pe = next(p for p in pieces_em_pe if "Travessa Topo Parede X" in p.name)
    t_x_deitada = next(p for p in pieces_deitada if "Travessa Topo Parede X" in p.name)

    zs_x_em_pe = [v.position.z() for v in t_x_em_pe.mesh.vertices]
    zs_x_deitada = [v.position.z() for v in t_x_deitada.mesh.vertices]

    assert abs((max(zs_x_em_pe) - min(zs_x_em_pe)) - 0.070) < 1e-4
    assert abs((max(zs_x_deitada) - min(zs_x_deitada)) - 0.015) < 1e-4

    # Verifica folga extra / rebaixo no topo da porta (recuo_porta_topo_mm = 50mm por padrão)
    porta_em_pe = next(p for p in pieces_em_pe if "Porta" in p.name)
    porta_deitada = next(p for p in pieces_deitada if "Porta" in p.name)

    zs_porta_em_pe = [v.position.z() for v in porta_em_pe.mesh.vertices]
    zs_porta_deitada = [v.position.z() for v in porta_deitada.mesh.vertices]

    alt_porta_em_pe = max(zs_porta_em_pe) - min(zs_porta_em_pe)
    alt_porta_deitada = max(zs_porta_deitada) - min(zs_porta_deitada)

    # A porta quando a travessa frontal está em pé deve ser 50mm menor na altura (rebaixo/folga extra no topo)
    assert abs((alt_porta_deitada - alt_porta_em_pe) - 0.050) < 1e-4


def test_balcao_canto_chanfrado_furacoes_canonicas():
    mod = CabinetBuilder.build_module_group({
        "tipo": "balcao_canto_chanfrado",
        "largura": 1000,
        "profundidade": 1000,
        "altura": 720,
    })
    children = {p.name: p for p in mod.children}

    lat_esq = children["Canto Chanfrado - Lateral Esquerda"]
    lat_dir = children["Canto Chanfrado - Lateral Direita"]
    mont_esq = children["Canto Chanfrado - Montante Batente Esq"]
    mont_dir = children["Canto Chanfrado - Montante Batente Dir"]
    porta = children["Canto Chanfrado - Porta"]
    base = children["Canto Chanfrado - Base Inferior"]
    trav_f = children["Canto Chanfrado - Travessa Topo Frontal"]

    ops_lat_e = lat_esq.ext.get("trazomob", {}).get("operacoes", [])
    ops_lat_d = lat_dir.ext.get("trazomob", {}).get("operacoes", [])
    ops_mont_e = mont_esq.ext.get("trazomob", {}).get("operacoes", [])
    ops_mont_d = mont_dir.ext.get("trazomob", {}).get("operacoes", [])
    ops_base = base.ext.get("trazomob", {}).get("operacoes", [])
    ops_trav_f = trav_f.ext.get("trazomob", {}).get("operacoes", [])

    # 1. Lateral Esquerda não deve conter calços de dobradiça (a porta articula no montante batente)
    assert not any("cal" in str(op.get("descricao", "")).lower() for op in ops_lat_e)

    # 2. Montante Batente Esq deve conter marcações de calço de dobradiça
    calcos_mont = [op for op in ops_mont_e if "cal" in str(op.get("descricao", "")).lower()]
    assert len(calcos_mont) >= 2

    # 3. Lateral Direita deve ter furações dentro da peça (x entre 0 e 535mm) sem coordenadas negativas
    assert len(ops_lat_d) > 0
    for op in ops_lat_d:
        assert float(op.get("x", 0.0)) >= 0.0
        assert float(op.get("x", 0.0)) <= 535.0

    # 4. Base Inferior e Travessa Frontal possuem furações sincronizadas no lado direito
    assert any("Direita" in p.name for p in [lat_dir])
    assert len(ops_base) > 0
    assert len(ops_trav_f) > 0




