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
    assert any("Lateral Esquerda" in n for n in names)
    assert any("Lateral Direita" in n for n in names)
    assert any("Base Inferior" in n for n in names)
    assert any("Travessa Frontal" in n for n in names)
    assert any("Travessa Traseira" in n for n in names)
    assert any("Prateleira 4" in n for n in names)


def test_build_adega_colmeia():
    pieces = BalcaoAereoBuilder.build_adega_colmeia(
        largura_mm=200, altura_mm=720, prof_mm=550
    )
    assert len(pieces) >= 6
    names = [p.name for p in pieces]
    assert any("Lateral Esquerda" in n for n in names)
    assert any("Lateral Direita" in n for n in names)
    assert any("Base Inferior" in n for n in names)
    assert any("Travessa Frontal" in n for n in names)
    assert any("Divisória X1" in n for n in names)
    assert any("Divisória X2" in n for n in names)


def test_balcao_porta_panos_e_adega_nomenclatura_e_caixa_padrao():
    from trazomob.builders.cabinet import CabinetBuilder

    # Porta panos via CabinetBuilder
    mod_pp = CabinetBuilder.build_module_group({
        "tipo": "porta_panos",
        "largura": 200,
        "altura": 720,
        "profundidade": 550,
        "num_prateleiras": 4,
    })
    assert mod_pp.name.startswith("Balcao Porta Panos")
    pp_names = [c.name for c in mod_pp.children]
    assert any("Lateral Esquerda" in n for n in pp_names)
    assert any("Lateral Direita" in n for n in pp_names)
    assert any("Base Inferior" in n for n in pp_names)
    assert any("Travessa Frontal" in n for n in pp_names)
    assert any("Travessa Traseira" in n for n in pp_names)
    assert any("Rodape Frontal" in n for n in pp_names)
    assert any("Prateleira 1" in n for n in pp_names)

    # Adega colmeia via CabinetBuilder
    mod_ad = CabinetBuilder.build_module_group({
        "tipo": "adega_colmeia",
        "largura": 200,
        "altura": 720,
        "profundidade": 550,
    })
    assert mod_ad.name.startswith("Balcao Adega Colmeia")
    ad_names = [c.name for c in mod_ad.children]
    assert any("Lateral Esquerda" in n for n in ad_names)
    assert any("Lateral Direita" in n for n in ad_names)
    assert any("Base Inferior" in n for n in ad_names)
    assert any("Travessa Frontal" in n for n in ad_names)
    assert any("Travessa Traseira" in n for n in ad_names)
    assert any("Divisória X1" in n for n in ad_names)


def test_build_balcao_peninsula():
    from trazomob.builders.cabinet import CabinetBuilder

    # Modo 1: Em cima do balcão (padrão)
    pieces = BalcaoAereoBuilder.build_balcao_peninsula(
        largura_mm=1200, altura_mm=850, prof_mm=600, largura_mesa_mm=800, comprimento_mesa_mm=1200,
        posicao_peninsula="em_cima",
    )
    assert len(pieces) >= 8
    names = [p.name for p in pieces]
    assert any("Tampo Mesa" in n for n in names)
    assert any("Pé Tubular" in n for n in names)
    assert any("Porta" in n for n in names)
    assert not any("Testeira Frontal Superior" in n for n in names)

    # Modo 2: Frontal Rebaixada (como na referência: testeira superior + mesa frontal + portas abaixo)
    mod_reb = CabinetBuilder.build_module_group({
        "tipo": "balcao_peninsula",
        "largura": 1200,
        "altura": 850,
        "profundidade": 600,
        "posicao_peninsula": "frontal_rebaixada",
        "rebaixo_peninsula_mm": 150,
        "largura_mesa_mm": 800,
        "comprimento_mesa_mm": 1200,
        "esp_tampo_mm": 30,
    })
    assert mod_reb.name.startswith("Balcao Peninsula")
    reb_names = [c.name for c in mod_reb.children]
    assert any("Testeira Frontal Superior" in n for n in reb_names)
    assert any("Tampo Mesa" in n for n in reb_names)
    assert any("Pé Tubular" in n for n in reb_names)
    assert any("Porta" in n for n in reb_names)
    assert any("Travessa Frontal" in n for n in reb_names)
    assert any("Travessa Traseira" in n for n in reb_names)

    # Verifica hierarquia vertical (Z): Portas < Tampo Mesa < Testeira Frontal Superior
    g_testeira = next(c for c in mod_reb.children if "Testeira Frontal Superior" in c.name)
    g_tampo = next(c for c in mod_reb.children if "Tampo Mesa" in c.name)
    g_porta = next(c for c in mod_reb.children if "Porta" in c.name and "Apoio" not in c.name)

    z_max_porta = max(v.position.z() for v in g_porta.mesh.vertices)
    z_min_tampo = min(v.position.z() for v in g_tampo.mesh.vertices)
    z_max_tampo = max(v.position.z() for v in g_tampo.mesh.vertices)
    z_min_testeira = min(v.position.z() for v in g_testeira.mesh.vertices)

    assert z_max_porta <= z_min_tampo + 1e-4
    assert z_max_tampo <= z_min_testeira + 1e-4

    # Verifica que as faces do Tampo Mesa não estão invertidas (topo aponta para +Z, base para -Z)
    for g_t in (
        next(p for p in pieces if "Tampo Mesa" in p.name),
        g_tampo,
    ):
        f_top, f_bot = g_t.mesh.faces[0], g_t.mesh.faces[1]
        assert f_top.normal().z() > 0.99, f"Face superior invertida: normal={f_top.normal()}"
        assert f_bot.normal().z() < -0.99, f"Face inferior invertida: normal={f_bot.normal()}"

    # Verifica peças canônicas e furação automática (minifix/cavilha, calços de dobradiça, canecos, prateleiras e travessa de apoio)
    g_lat_esq = next(c for c in mod_reb.children if "Lateral Esquerda" in c.name)
    g_base = next(c for c in mod_reb.children if "Base Inferior" in c.name)
    g_trav_apoio_h = next(c for c in mod_reb.children if "Travessa Apoio Portas" in c.name)
    g_trav_apoio_v = next(c for c in mod_reb.children if "Travessa Vertical Apoio Portas" in c.name)
    g_prat = next(c for c in mod_reb.children if "Prateleira" in c.name)

    # Portas abrem para o centro: porta da esquerda tem dobradiça à direita ("right"), porta da direita tem dobradiça à esquerda ("left")
    portas_reb = sorted(
        [c for c in mod_reb.children if "Porta" in c.name and "Apoio" not in c.name],
        key=lambda c: min(v.position.x() for v in c.mesh.vertices),
    )
    assert len(portas_reb) == 2
    assert portas_reb[0].ext["trazomob"]["door_side"] == "right"
    assert portas_reb[1].ext["trazomob"]["door_side"] == "left"

    assert len(g_lat_esq.ext["trazomob"]["operacoes"]) >= 6  # minifix/cavilhas + pinos prateleira + rasgo fundo
    assert len(g_base.ext["trazomob"]["operacoes"]) >= 6     # minifix/cavilhas nos topos + tambores + cavilhas do apoio vertical
    assert len(g_trav_apoio_h.ext["trazomob"]["operacoes"]) >= 2  # furação sincronizada pelo JointResolver com as laterais
    assert len(g_trav_apoio_v.ext["trazomob"]["operacoes"]) >= 6  # cavilhas de topo + calços de dobradiça nas duas faces
    assert len(g_prat.ext["trazomob"]["operacoes"]) >= 4     # furos de prateleira nos topos
    assert len(g_porta.ext["trazomob"]["operacoes"]) >= 2    # canecos de dobradiça 35mm

    # Modo com Divisória Central Completa
    mod_div = CabinetBuilder.build_module_group({
        "tipo": "balcao_peninsula",
        "largura": 1200,
        "altura": 850,
        "profundidade": 600,
        "posicao_peninsula": "frontal_rebaixada",
        "rebaixo_peninsula_mm": 150,
        "tipo_apoio_portas": "divisoria_completa",
        "largura_mesa_mm": 800,
        "comprimento_mesa_mm": 1200,
        "esp_tampo_mm": 30,
    })
    div_names = [c.name for c in mod_div.children]
    assert any("Divisoria Central Completa" in n for n in div_names)
    assert any("Divisoria Horizontal Apoio Portas" in n for n in div_names)
    assert any("Prateleira Vao 1" in n for n in div_names)
    assert any("Prateleira Vao 2" in n for n in div_names)
    g_div_c = next(c for c in mod_div.children if "Divisoria Central Completa" in c.name)
    assert len(g_div_c.ext["trazomob"]["operacoes"]) >= 8  # cavilhas + calços das 2 portas + pinos de prateleira nas 2 faces


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
    for mod_id in ["terminal_chanfrado", "porta_panos", "adega_colmeia", "balcao_peninsula", "canto_gaveteiro_l", "balcao_dente_traseiro"]:
        fn = get_module_builder(mod_id)
        assert fn is not None, f"Builder para {mod_id} não encontrado no registro"


def test_thumbnails_novos_balcoes(qapp):
    from trazomob.ui.thumbnails import _THUMBNAIL_CACHE, get_module_thumbnail

    _THUMBNAIL_CACHE.clear()
    for mod_id in ["balcao_peninsula", "porta_panos", "adega_colmeia", "terminal_chanfrado", "balcao_canto_chanfrado", "balcao_dente_traseiro"]:
        icon = get_module_thumbnail(mod_id)
        assert not icon.isNull(), f"Thumbnail nulo para {mod_id}"
        pix = icon.pixmap(130, 130)
        assert pix.width() == 130 and pix.height() == 130


def test_balcao_dente_traseiro_modos_e_canonico():
    from trazomob.builders.cabinet import CabinetBuilder

    for modo in ("canto_direito", "central", "canto_esquerdo"):
        mod = CabinetBuilder.build_module_group({
            "tipo": "balcao_dente_traseiro",
            "largura": 800,
            "altura": 720,
            "profundidade": 550,
            "posicao_dente": modo,
            "largura_dente_mm": 250,
            "profundidade_dente_mm": 150,
            "num_portas": 2,
            "num_prateleiras": 1,
            "gerar_furacao": True,
        })
        assert mod.name.startswith("Balcao Dente Traseiro")
        names = [c.name for c in mod.children]
        assert any("Lateral Esquerda" in n for n in names)
        assert any("Lateral Direita" in n for n in names)
        assert any("Base Inferior" in n for n in names)
        assert any("Prateleira 1" in n for n in names)
        assert any("Travessa Frontal" in n for n in names)
        assert any("Fundo Dente" in n for n in names)
        assert any("Porta" in n for n in names)

        # Verifica normais da base poligonal (topo +Z, base -Z)
        g_base = next(c for c in mod.children if "Base Inferior" in c.name)
        f_top = max(g_base.mesh.faces, key=lambda f: f.normal().z())
        f_bot = min(g_base.mesh.faces, key=lambda f: f.normal().z())
        assert f_top.normal().z() > 0.99
        assert f_bot.normal().z() < -0.99

        # Verifica que o JointResolver gerou operações nas laterais/portas
        g_lat_esq = next(c for c in mod.children if "Lateral Esquerda" in c.name)
        assert len(g_lat_esq.ext["trazomob"]["operacoes"]) > 0



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


