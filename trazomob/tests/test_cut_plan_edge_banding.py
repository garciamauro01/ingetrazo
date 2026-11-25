from trazomob.production.optimizer import GuillotineOptimizer, SheetConfig
from trazomob.production.parts import calculate_cut_dimensions


def test_calculate_cut_dimensions_with_edge_banding():
    # 700 x 400 mm com fita de 1.0mm nos 4 bordos:
    # Corte bruto esperado: 700 - 2.0 = 698.0, 400 - 2.0 = 398.0
    c_corte, l_corte = calculate_cut_dimensions(
        comprimento=700.0,
        largura=400.0,
        fita_c1=True,
        fita_c2=True,
        fita_l1=True,
        fita_l2=True,
        espessura_fita=1.0,
    )
    assert c_corte == 698.0
    assert l_corte == 398.0


def test_calculate_cut_dimensions_partial_tape():
    # Fita apenas em C1 (comprimento) e L1 (largura) com espessura 0.45mm
    c_corte, l_corte = calculate_cut_dimensions(
        comprimento=700.0,
        largura=400.0,
        fita_c1=True,
        fita_c2=False,
        fita_l1=True,
        fita_l2=False,
        espessura_fita=0.45,
    )
    assert c_corte == 699.55 or c_corte == round(700.0 - 0.45, 1)
    assert l_corte == 399.55 or l_corte == round(400.0 - 0.45, 1)


def test_optimizer_uses_cut_dimensions_and_preserves_final():
    optimizer = GuillotineOptimizer(SheetConfig())
    raw_parts = [
        {
            "id": 1,
            "nome": "Porta Balcao",
            "comprimento": 700.0,
            "largura": 400.0,
            "espessura": 15.0,
            "material": "MDF Branco TX 15mm",
            "comprimento_corte": 698.0,
            "largura_corte": 398.0,
            "espessura_fita": 1.0,
            "fita_c1": True,
            "fita_c2": True,
            "fita_l1": True,
            "fita_l2": True,
            "quantidade": 1,
        }
    ]
    result = optimizer.optimize(raw_parts)
    sheets = result["MDF Branco TX 15mm (15mm)"]
    assert len(sheets) == 1
    peca = sheets[0].pecas[0]

    # Medidas de corte enviadas para otimização na chapa
    assert peca.comprimento == 698.0
    assert peca.largura == 398.0

    # Medidas finais preservadas
    assert peca.comprimento_final == 700.0
    assert peca.largura_final == 400.0
    assert peca.espessura_fita == 1.0
