# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
from trazomob.builders.registry import get_module_builder
from trazomob.builders.corner_cabinets import CantoEspecialBuilder
from trazomob.builders.base_wall_cabinets import BalcaoAereoBuilder


def test_build_terminal_chanfrado_direita_e_esquerda():
    # Direita
    pieces_dir = CantoEspecialBuilder.build_terminal_chanfrado(
        largura_mm=300, altura_mm=720, prof_mm=550, lado="direita"
    )
    assert len(pieces_dir) >= 5
    names_dir = [p.name for p in pieces_dir]
    assert any("Lateral Reta Esq" in n for n in names_dir)
    assert any("Base Inferior" in n for n in names_dir)
    assert any("Topo" in n for n in names_dir)
    assert any("Prateleira" in n for n in names_dir)

    # Esquerda
    pieces_esq = CantoEspecialBuilder.build_terminal_chanfrado(
        largura_mm=300, altura_mm=720, prof_mm=550, lado="esquerda"
    )
    assert len(pieces_esq) >= 5
    names_esq = [p.name for p in pieces_esq]
    assert any("Lateral Reta Dir" in n for n in names_esq)


def test_build_porta_panos():
    pieces = BalcaoAereoBuilder.build_porta_panos(
        largura_mm=200, altura_mm=720, prof_mm=550, num_prateleiras=4
    )
    assert len(pieces) >= 6
    names = [p.name for p in pieces]
    assert any("Lateral Esq" in n for n in names)
    assert any("Lateral Dir" in n for n in names)
    assert any("Base Inferior" in n for n in names)
    assert any("Topo" in n for n in names)
    assert any("Prateleira 4" in n for n in names)


def test_build_adega_colmeia():
    pieces = BalcaoAereoBuilder.build_adega_colmeia(
        largura_mm=200, altura_mm=720, prof_mm=550
    )
    assert len(pieces) >= 6
    names = [p.name for p in pieces]
    assert any("Lateral Esq" in n for n in names)
    assert any("Divisória X1" in n for n in names)
    assert any("Divisória X2" in n for n in names)


def test_build_balcao_peninsula():
    pieces = BalcaoAereoBuilder.build_balcao_peninsula(
        largura_mm=1200, altura_mm=850, prof_mm=600, largura_mesa_mm=800, comprimento_mesa_mm=1200
    )
    assert len(pieces) >= 8
    names = [p.name for p in pieces]
    assert any("Tampo Mesa" in n for n in names)
    assert any("Pé Tubular" in n for n in names)
    assert any("Porta" in n for n in names)


def test_build_space_corner():
    pieces = CantoEspecialBuilder.build_canto_gaveteiro_l(
        largura_mm=1050, altura_mm=720, prof_mm=1050, prof_lateral_esq_mm=600, prof_lateral_dir_mm=600, num_gavetas=4
    )
    assert len(pieces) >= 10
    names = [p.name for p in pieces]
    assert any("Traseira Parede X" in n for n in names)
    assert any("Traseira Parede Y" in n for n in names)
    assert any("Base Inferior em L" in n for n in names)
    assert any("Frente Esq" in n for n in names)
    assert any("Frente Dir" in n for n in names)
    assert any("Lat Esq" in n for n in names)
    assert any("Lat Dir" in n for n in names)
    assert any("Fundo" in n for n in names)


def test_space_corner_corredicas_alinhadas_e_bounds():
    from trazomob.builders.cabinet import CabinetBuilder
    from trazomob.domain.module_geometry import get_module_carcass_bounds

    params = {
        "id": "balcao_canto_gaveteiro_l",
        "tipo": "balcao_canto_gaveteiro_l",
        "largura": 1050,
        "altura": 720,
        "profundidade": 1050,
        "prof_lateral_esq": 600,
        "prof_lateral_dir": 600,
        "num_gavetas": 4,
    }
    mod = CabinetBuilder.build_module_group(params)
    cb = get_module_carcass_bounds(mod)
    assert cb is not None
    # Bounds exatos do canto 1050x1050 mm
    assert abs(cb[0] - 0.0) < 1e-4
    assert abs(cb[1] - 1.05) < 1e-4
    assert abs(cb[2] - 0.0) < 1e-4
    assert abs(cb[3] - 1.05) < 1e-4

    # Corrediças 3D geradas nas laterais inclinadas sem sobrar para fora
    hw_runners = [c for c in mod.children if "Trilho Fixo Gaveta" in c.name or "Corrediças Gaveta" in c.name]
    assert len(hw_runners) == 8  # 4 gavetas x 2 tipos (inner + outer)
    for hr in hw_runners:
        vs = hr.mesh.vertices
        xs = [v.position.x() for v in vs]
        ys = [v.position.y() for v in vs]
        assert min(xs) >= -0.01 and max(xs) <= 1.06
        assert min(ys) >= -0.01 and max(ys) <= 1.06


def test_registry_novos_modulos():
    for mod_id in ["terminal_chanfrado", "porta_panos", "adega_colmeia", "balcao_peninsula", "canto_gaveteiro_l"]:
        fn = get_module_builder(mod_id)
        assert fn is not None, f"Builder para {mod_id} não encontrado no registro"
