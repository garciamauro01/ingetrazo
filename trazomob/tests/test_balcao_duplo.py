# SPDX-License-Identifier: GPL-3.0-or-later
"""Testes unitários para o módulo Balcão Ilha Bilateral (balcao_duplo)."""
from core.group import Group
from trazomob.builders.cabinet import CabinetBuilder
from trazomob.domain.hardware import infer_module_hardware
from trazomob.domain.module_geometry import get_module_category
from trazomob.interaction.interact import CabinetInteract


def test_balcao_duplo_catalog_and_category():
    assert get_module_category("balcao_duplo") == "inferior"
    assert get_module_category("balcao_ilha") == "inferior"


def test_balcao_duplo_build_2_doors():
    params = {
        "tipo": "balcao_duplo",
        "largura": 1200,
        "altura": 720,
        "profundidade": 900,
        "rodape": 100,
        "num_portas": 2,
        "num_portas_verso": 2,
        "num_prateleiras": 1,
    }
    mod = CabinetBuilder.build_module_group(params)
    assert isinstance(mod, Group)
    names = [c.name for c in mod.children]

    assert any("Lateral Esquerda" in n for n in names)
    assert any("Lateral Direita" in n for n in names)
    assert any("Base Inferior" in n for n in names)
    assert any("Divisoria Longitudinal Central" in n for n in names)
    assert any("Frente - Porta" in n for n in names)
    assert any("Verso Porta" in n for n in names)

    # Verifica cinemática das portas frontais e traseiras
    front_doors = [c for c in mod.children if "Frente - Porta" in c.name]
    rear_doors = [c for c in mod.children if "Verso Porta" in c.name]
    assert len(front_doors) == 2
    assert len(rear_doors) == 2

    # Abertura 100%
    for d in front_doors:
        ok = CabinetInteract.set_piece_open_fraction(d, 1.0, module_group=mod)
        assert ok is True
        piv = d.ext.get("hinge_pivot")
        assert piv is not None
        assert piv.y() < 0.05  # Pivot na frente

    for d in rear_doors:
        ok = CabinetInteract.set_piece_open_fraction(d, 1.0, module_group=mod)
        assert ok is True
        piv = d.ext.get("hinge_pivot")
        assert piv is not None
        assert piv.y() > 0.85  # Pivot no verso (profundidade 900mm)


def test_balcao_duplo_hardware():
    params = {
        "tipo": "balcao_duplo",
        "largura": 1200,
        "altura": 720,
        "profundidade": 900,
        "num_portas": 2,
        "num_portas_verso": 2,
    }
    hw = infer_module_hardware(params)
    dobradicas = [h for h in hw if h.key == "dobradica_35mm"]
    assert len(dobradicas) == 1
    # 4 portas totais * 2 dobradiças por porta = 8
    assert dobradicas[0].quantidade == 8

    puxadores = [h for h in hw if h.tipo == "puxador"]
    assert len(puxadores) == 1
    assert puxadores[0].quantidade == 4
