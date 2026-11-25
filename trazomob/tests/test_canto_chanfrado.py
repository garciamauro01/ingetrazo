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

