# SPDX-License-Identifier: GPL-3.0-or-later
from trazomob.builders.base_wall_cabinets import BalcaoAereoBuilder
from trazomob.builders.corner_cabinets import CantoEspecialBuilder
from trazomob.builders.registry import get_module_builder


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


def test_space_corner_travessa_frontal_em_pe_recuo_topo():
    def get_max_z(g):
        mz = -999.0
        if hasattr(g, 'mesh') and g.mesh:
            for v in g.mesh.vertices:
                pos = v.position
                vz = pos.z() if callable(pos.z) else pos.z
                mz = max(mz, vz)
        if hasattr(g, 'children'):
            for c in g.children:
                cz = get_max_z(c)
                mz = max(mz, cz)
        return mz

    g_deitada = CantoEspecialBuilder.build_canto_gaveteiro_l(
        largura_mm=1050, altura_mm=850, prof_mm=1050,
        travessa_frontal_em_pe=False,
    )
    g_em_pe = CantoEspecialBuilder.build_canto_gaveteiro_l(
        largura_mm=1050, altura_mm=850, prof_mm=1050,
        travessa_frontal_em_pe=True,
        recuo_porta_topo_mm=50.0,
    )

    frentes_deitada = [p for p in g_deitada if 'Frente' in p.name]
    frentes_em_pe = [p for p in g_em_pe if 'Frente' in p.name]

    z_deitada = max(get_max_z(p) for p in frentes_deitada)
    z_em_pe = max(get_max_z(p) for p in frentes_em_pe)

    # A diferença no topo das frentes deve ser exatamente 50 mm (0.050 m)
    assert abs((z_deitada - z_em_pe) - 0.050) < 1e-4


def test_gaveta_config_profundidade_e_dimensoes_uteis():
    from trazomob.builders.drawers import CanonicalDrawerBuilder

    # 1. Resolução automática pelo vão livre
    p_caixa, tam_corr = CanonicalDrawerBuilder.resolve_profundidade_gaveta(prof_disponivel_m=0.485)
    assert tam_corr == 450
    assert abs(p_caixa - 0.45) < 1e-4

    # 2. Resolução com profundidade configurada pelo marceneiro (ex: 400 mm)
    p_manual, tam_manual = CanonicalDrawerBuilder.resolve_profundidade_gaveta(
        prof_disponivel_m=0.550,
        prof_gaveta_param_mm=400.0,
    )
    assert tam_manual == 400
    assert abs(p_manual - 0.40) < 1e-4

    # 3. Cálculo de dimensões úteis internas (luz livre real)
    uteis = CanonicalDrawerBuilder.calcular_dimensoes_uteis(
        larg_caixa_mm=450.0,
        prof_caixa_mm=400.0,
        alt_caixa_mm=150.0,
        esp_gaveta_mm=15.0,
        esp_fundo_gaveta_mm=6.0,
        tipo_fundo_gaveta="rasgo",
    )
    assert uteis["larg_util_mm"] == 420.0
    assert uteis["prof_util_mm"] == 370.0
    assert uteis["alt_util_mm"] == 134.0


