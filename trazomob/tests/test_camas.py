import pytest

from core.group import Group
from trazomob.builders.cabinet import CabinetBuilder
from trazomob.builders.camas import CamaBuilder


def _bbox_mm(pieces):
    """Retorna (largura X, comprimento Y, altura Z) do envelope em mm."""
    xs, ys, zs = [], [], []
    for p in pieces:
        mesh = getattr(p, "mesh", None)
        if mesh is None:
            continue
        for v in mesh.vertices:
            pos = v.position
            xs.append(pos.x())
            ys.append(pos.y())
            zs.append(pos.z())
    if not xs:
        return (0.0, 0.0, 0.0)
    return (
        (max(xs) - min(xs)) * 1000.0,
        (max(ys) - min(ys)) * 1000.0,
        (max(zs) - min(zs)) * 1000.0,
    )


def test_build_cama_gaveteiros():
    pieces = CamaBuilder.build_cama_gaveteiros(
        largura_mm=1400,
        prof_mm=1950,
        altura_mm=400,
        num_gavetoes=4,
    )
    assert len(pieces) > 0
    nomes = [p.name for p in pieces]
    assert any("Peseira" in n for n in nomes)
    assert any("Cabeceira" in n for n in nomes)
    assert any("Longarina" in n for n in nomes)
    assert any("Estrado" in n for n in nomes)
    assert any("Gaveta" in n for n in nomes)

    # Testar via CabinetBuilder
    group = CabinetBuilder.build_module_group({
        "tipo": "cama_gaveteiros",
        "largura": 1400,
        "profundidade": 1950,
        "altura": 400,
        "num_gavetas": 4,
    })
    assert isinstance(group, Group)
    assert len(group.children) > 0


def test_build_cama_bau():
    pieces = CamaBuilder.build_cama_bau(
        largura_mm=1400,
        prof_mm=1950,
        altura_mm=420,
    )
    assert len(pieces) > 0
    nomes = [p.name for p in pieces]
    assert any("Peseira" in n for n in nomes)
    assert any("Fundo" in n for n in nomes)
    assert any("Basculante" in n or "Tampa" in n for n in nomes)

    group = CabinetBuilder.build_module_group({
        "tipo": "cama_bau",
        "largura": 1400,
        "profundidade": 1950,
        "altura": 420,
    })
    assert isinstance(group, Group)
    assert len(group.children) > 0


def test_build_cama_cabeceira():
    pieces = CamaBuilder.build_cama_cabeceira(
        largura_mm=2400,
        prof_mm=2050,
        altura_mm=1100,
    )
    assert len(pieces) > 0
    nomes = [p.name for p in pieces]
    assert any("Painel de Cabeceira" in n for n in nomes)
    assert any("Mesinha" in n for n in nomes)
    assert any("Peseira" in n for n in nomes)

    group = CabinetBuilder.build_module_group({
        "tipo": "cama_cabeceira",
        "largura": 2400,
        "profundidade": 2050,
        "altura": 1100,
    })
    assert isinstance(group, Group)
    assert len(group.children) > 0


def test_build_bicama():
    pieces = CamaBuilder.build_bicama(
        largura_mm=950,
        prof_mm=1950,
        altura_mm=500,
    )
    assert len(pieces) > 0
    nomes = [p.name for p in pieces]
    assert any("Peseira" in n for n in nomes)
    assert any("Cabeceira" in n for n in nomes)
    assert any("Cama Auxiliar" in n for n in nomes)

    group = CabinetBuilder.build_module_group({
        "tipo": "bicama",
        "largura": 950,
        "profundidade": 1950,
        "altura": 500,
    })
    assert isinstance(group, Group)
    assert len(group.children) > 0


def test_build_beliche():
    pieces = CamaBuilder.build_beliche(
        largura_mm=950,
        prof_mm=2000,
        altura_mm=1600,
    )
    assert len(pieces) > 0
    nomes = [p.name for p in pieces]
    assert any("Peseira Beliche" in n for n in nomes)
    assert any("Cabeceira Beliche" in n for n in nomes)
    assert any("Inferior" in n for n in nomes)
    assert any("Superior" in n for n in nomes)
    assert any("Guarda-Corpo" in n for n in nomes)
    assert any("Escada" in n or "Degrau" in n for n in nomes)

    group = CabinetBuilder.build_module_group({
        "tipo": "beliche",
        "largura": 950,
        "profundidade": 2000,
        "altura": 1600,
    })
    assert isinstance(group, Group)
    assert len(group.children) > 0


# ---------------------------------------------------------------------------
# Regressões de unidades e geometria (bug histórico: mm repassado como metros)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("builder,kwargs,esperado", [
    (CamaBuilder.build_cama_gaveteiros, dict(largura_mm=1400, prof_mm=1950, altura_mm=400), (1400, 1950, 400)),
    (CamaBuilder.build_cama_bau, dict(largura_mm=1400, prof_mm=1950, altura_mm=420), (1400, 1950, 420)),
    (CamaBuilder.build_cama_cabeceira, dict(largura_mm=2400, prof_mm=2050, altura_mm=1100), (2400, 2050, 1100)),
    (CamaBuilder.build_bicama, dict(largura_mm=950, prof_mm=1950, altura_mm=500), (950, 1950, 500)),
    (CamaBuilder.build_beliche, dict(largura_mm=950, prof_mm=2000, altura_mm=1600), (950, 2000, 1600)),
    (CamaBuilder.build_cama_colmeia, dict(largura_mm=1400, prof_mm=1950, altura_mm=350), (1400, 1950, 350)),
])
def test_camas_dimensoes_em_metros(builder, kwargs, esperado):
    """A geometria 3D deve ficar em metros (envelope compatível com o módulo em mm)."""
    pieces = builder(**kwargs)
    largura, comprimento, altura = _bbox_mm(pieces)
    assert abs(largura - esperado[0]) <= 60.0, (largura, esperado)
    assert abs(comprimento - esperado[1]) <= 60.0, (comprimento, esperado)
    assert abs(altura - esperado[2]) <= 60.0, (altura, esperado)
    # Nenhuma peça pode exceder os limites úteis de chapa (mm)
    for p in pieces:
        meta = getattr(p, "ext", {}).get("trazomob", {})
        for chave in ("comprimento", "largura", "espessura"):
            assert meta.get(chave, 0.0) <= 2720.0, (p.name, chave, meta.get(chave))


def test_cama_gavetas_lado_esquerda():
    pieces = CamaBuilder.build_cama_gaveteiros(
        largura_mm=1400, prof_mm=1950, altura_mm=400,
        num_gavetoes=4, lado_gavetas="esquerda",
    )
    frentes = [p.name for p in pieces if "Frente Gaveta" in p.name]
    assert len(frentes) == 4
    assert all("Esq" in n for n in frentes)


def test_cama_gavetas_ambos_contagem_impar():
    pieces = CamaBuilder.build_cama_gaveteiros(
        largura_mm=1400, prof_mm=1950, altura_mm=400,
        num_gavetoes=3, lado_gavetas="ambos",
    )
    frentes = [p.name for p in pieces if "Frente Gaveta" in p.name]
    assert len(frentes) == 3


def test_cama_frentes_usam_material_frentes():
    pieces = CamaBuilder.build_cama_gaveteiros(
        largura_mm=1400, prof_mm=1950, altura_mm=400,
        material="MDF Carvalho", material_frentes="MDF Grafite",
    )
    frentes = [p for p in pieces if "Frente Gaveta" in p.name]
    assert frentes
    assert all(p.ext["trazomob"]["material"] == "MDF Grafite" for p in frentes)


def test_cama_herda_contexto_de_material_e_fita_via_registry():
    group = CabinetBuilder.build_module_group({
        "tipo": "cama_gaveteiros",
        "largura": 1400,
        "profundidade": 1950,
        "altura": 400,
        "material": "MDF Carvalho",
        "material_frentes": "MDF Grafite",
        "espessura_fita_frentes": 1.0,
    })
    frentes = [c for c in group.children if "Frente Gaveta" in c.name]
    assert frentes
    assert all(c.ext["trazomob"]["material"] == "MDF Grafite" for c in frentes)
    assert all(c.ext["trazomob"]["espessura_fita"] == 1.0 for c in frentes)

    estrutural = next(c for c in group.children if "Peseira" in c.name)
    assert estrutural.ext["trazomob"]["material"] == "MDF Carvalho"


def test_cama_cabeceira_respeita_larg_cama():
    pieces = CamaBuilder.build_cama_cabeceira(
        largura_mm=2400, prof_mm=2050, altura_mm=1100, larg_cama_mm=1200,
    )
    peseira = next(p for p in pieces if p.name == "Cama - Peseira")
    assert peseira.ext["trazomob"]["comprimento"] == pytest.approx(1200.0)


def test_beliche_respeita_alt_leito_sup():
    pieces = CamaBuilder.build_beliche(
        largura_mm=950, prof_mm=2000, altura_mm=1600, alt_leito_sup_mm=1400,
    )
    estrado_sup = next(p for p in pieces if p.name == "Beliche - Estrado Superior")
    assert estrado_sup.ext["trazomob"]["espessura"] == pytest.approx(15.0)
    # O estrado superior deve estar na altura informada (1400 mm)
    z_max = max(v.position.z() for v in estrado_sup.mesh.vertices)
    assert z_max * 1000.0 == pytest.approx(1400.0, abs=1.0)


def _group_bounds_mm(group) -> tuple[float, float, float]:
    xs, ys, zs = [], [], []
    for ch in getattr(group, "children", []) or []:
        mesh = getattr(ch, "mesh", None)
        if not mesh or not getattr(mesh, "vertices", None):
            continue
        for v in mesh.vertices:
            xs.append(v.position.x() * 1000.0)
            ys.append(v.position.y() * 1000.0)
            zs.append(v.position.z() * 1000.0)
    return (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))


def test_camas_categoria_defaults_e_sem_corredicas_flutuantes():
    from trazomob.builders.cabinet import CabinetBuilder
    from trazomob.domain.catalog import MODULE_CATALOG
    from trazomob.domain.module_geometry import (
        build_default_module_params,
        get_module_category,
        is_compatible_category,
    )

    assert not is_compatible_category("cama", "inferior")
    assert not is_compatible_category("cama", "cama")

    camas = MODULE_CATALOG["Dormitório — Camas"]
    assert len(camas) == 6

    for item in camas:
        assert get_module_category(item["id"], item.get("default_z", 0.0)) == "cama"
        params = build_default_module_params(item)
        assert params["largura"] == pytest.approx(float(item["largura"]))
        assert params["altura"] == pytest.approx(float(item["altura"]))
        assert params["profundidade"] == pytest.approx(float(item["profundidade"]))

        grp = CabinetBuilder.build_module_group(params)
        larg_mm, comp_mm, alt_mm = _group_bounds_mm(grp)
        assert abs(larg_mm - item["largura"]) <= 60.0, (item["id"], larg_mm, item["largura"])
        assert abs(comp_mm - item["profundidade"]) <= 60.0, (item["id"], comp_mm, item["profundidade"])
        assert abs(alt_mm - item["altura"]) <= 60.0, (item["id"], alt_mm, item["altura"])

        ferragens_corredica = [
            ch.name for ch in grp.children
            if any(k in ch.name.lower() for k in ("corrediça", "corredica", "guia telescópica", "trilho fixo"))
        ]
        assert not ferragens_corredica, (item["id"], ferragens_corredica)


def test_cama_gaveteiros_abertura_lateral_independente():
    from trazomob.builders.cabinet import CabinetBuilder
    from trazomob.interaction.interact import CabinetInteract

    for rot_z, exp_dir, exp_esq in ((0.0, (1.0, 0.0), (-1.0, 0.0)), (90.0, (0.0, 1.0), (0.0, -1.0))):
        grp = CabinetBuilder.build_module_group({
            "tipo": "cama_gaveteiros",
            "largura": 1400.0,
            "altura": 400.0,
            "profundidade": 1950.0,
            "num_gavetoes": 4,
            "lado_gavetas": "ambos",
            "rot_z": rot_z,
        })
        names = {ch.name for ch in grp.children}
        assert "Cama - Lateral Esquerda" not in names
        assert "Cama - Lateral Direita" not in names

        fg_dir1 = next(ch for ch in grp.children if ch.name == "Cama - Frente Gaveta Dir 1")
        fundo_dir1 = next(ch for ch in grp.children if ch.name == "Cama - Fundo Gaveta Dir 1")
        fg_dir2 = next(ch for ch in grp.children if ch.name == "Cama - Frente Gaveta Dir 2")
        fg_esq1 = next(ch for ch in grp.children if ch.name == "Cama - Frente Gaveta Esq 1")

        assert CabinetInteract.is_interactive_piece(fg_dir1.name)
        assert CabinetInteract.get_piece_interaction_type(fg_dir1.name) == "drawer"

        p0_dir1 = sum(v.position.x() for v in fg_dir1.mesh.vertices) / len(fg_dir1.mesh.vertices)
        q0_dir1 = sum(v.position.y() for v in fg_dir1.mesh.vertices) / len(fg_dir1.mesh.vertices)
        f0_dir1_x = sum(v.position.x() for v in fundo_dir1.mesh.vertices) / len(fundo_dir1.mesh.vertices)
        f0_dir1_y = sum(v.position.y() for v in fundo_dir1.mesh.vertices) / len(fundo_dir1.mesh.vertices)
        p0_dir2 = (fg_dir2.mesh.vertices[0].position.x(), fg_dir2.mesh.vertices[0].position.y())
        p0_esq1 = (
            sum(v.position.x() for v in fg_esq1.mesh.vertices) / len(fg_esq1.mesh.vertices),
            sum(v.position.y() for v in fg_esq1.mesh.vertices) / len(fg_esq1.mesh.vertices),
        )

        assert CabinetInteract.set_piece_open_fraction(fg_dir1, 1.0, module_group=grp)
        dx = (sum(v.position.x() for v in fg_dir1.mesh.vertices) / len(fg_dir1.mesh.vertices)) - p0_dir1
        dy = (sum(v.position.y() for v in fg_dir1.mesh.vertices) / len(fg_dir1.mesh.vertices)) - q0_dir1
        assert dx * exp_dir[0] + dy * exp_dir[1] > 0.30
        assert abs(dx * exp_dir[1] - dy * exp_dir[0]) < 1e-3

        fdx = (sum(v.position.x() for v in fundo_dir1.mesh.vertices) / len(fundo_dir1.mesh.vertices)) - f0_dir1_x
        fdy = (sum(v.position.y() for v in fundo_dir1.mesh.vertices) / len(fundo_dir1.mesh.vertices)) - f0_dir1_y
        assert fdx == pytest.approx(dx, abs=1e-4)
        assert fdy == pytest.approx(dy, abs=1e-4)

        assert (fg_dir2.mesh.vertices[0].position.x(), fg_dir2.mesh.vertices[0].position.y()) == pytest.approx(p0_dir2, abs=1e-5)
        assert CabinetInteract.set_piece_open_fraction(fg_esq1, 1.0, module_group=grp)
        ex = (sum(v.position.x() for v in fg_esq1.mesh.vertices) / len(fg_esq1.mesh.vertices)) - p0_esq1[0]
        ey = (sum(v.position.y() for v in fg_esq1.mesh.vertices) / len(fg_esq1.mesh.vertices)) - p0_esq1[1]
        assert ex * exp_esq[0] + ey * exp_esq[1] > 0.30


def test_cama_bau_tampa_bascula_para_cima():
    from trazomob.builders.cabinet import CabinetBuilder
    from trazomob.interaction.interact import CabinetInteract

    for rot_z in (0.0, 90.0):
        grp = CabinetBuilder.build_module_group({
            "tipo": "cama_bau",
            "largura": 1400.0,
            "altura": 420.0,
            "profundidade": 1980.0,
            "rot_z": rot_z,
        })
        tampa = next(ch for ch in grp.children if ch.name == "Cama Baú - Tampa Estrado Basculante")
        assert CabinetInteract.is_interactive_piece(tampa.name)
        assert CabinetInteract.get_piece_interaction_type(tampa.name) == "door_flap"

        z_closed_max = max(v.position.z() for v in tampa.mesh.vertices)
        assert CabinetInteract.set_piece_open_fraction(tampa, 1.0, module_group=grp)
        z_open_max = max(v.position.z() for v in tampa.mesh.vertices)
        assert z_open_max - z_closed_max > 0.80

        assert CabinetInteract.set_piece_open_fraction(tampa, 0.0, module_group=grp)
        z_reset_max = max(v.position.z() for v in tampa.mesh.vertices)
        assert z_reset_max == pytest.approx(z_closed_max, abs=1e-4)


def test_bicama_cama_cabeceira_e_beliche_estruturais():
    from trazomob.builders.cabinet import CabinetBuilder
    from trazomob.interaction.interact import CabinetInteract

    bicama = CabinetBuilder.build_module_group({
        "tipo": "bicama",
        "largura": 920.0,
        "altura": 500.0,
        "profundidade": 1950.0,
    })
    frente_aux = next(ch for ch in bicama.children if ch.name == "Bicama - Frente Cama Auxiliar")
    estrado_aux = next(ch for ch in bicama.children if ch.name == "Bicama - Estrado Cama Auxiliar")
    assert CabinetInteract.is_interactive_piece(estrado_aux.name)
    assert CabinetInteract.get_piece_interaction_type(estrado_aux.name) == "drawer"

    fx0 = frente_aux.mesh.vertices[0].position.x()
    ex0 = estrado_aux.mesh.vertices[0].position.x()
    assert CabinetInteract.set_piece_open_fraction(frente_aux, 1.0, module_group=bicama)
    assert frente_aux.mesh.vertices[0].position.x() - fx0 < -0.40
    assert estrado_aux.mesh.vertices[0].position.x() - ex0 == pytest.approx(
        frente_aux.mesh.vertices[0].position.x() - fx0, abs=1e-4
    )

    cab = CabinetBuilder.build_module_group({
        "tipo": "cama_cabeceira",
        "largura": 2500.0,
        "altura": 1100.0,
        "profundidade": 2050.0,
    })
    cab_names = {ch.name for ch in cab.children}
    for req in (
        "Cama - Lateral Ext Mesinha Esq",
        "Cama - Lateral Int Mesinha Esq",
        "Cama - Frente Gaveta Mesinha Esq",
        "Cama - Lateral Ext Mesinha Dir",
        "Cama - Lateral Int Mesinha Dir",
        "Cama - Frente Gaveta Mesinha Dir",
    ):
        assert req in cab_names
    fg_me = next(ch for ch in cab.children if ch.name == "Cama - Frente Gaveta Mesinha Esq")
    fg_md = next(ch for ch in cab.children if ch.name == "Cama - Frente Gaveta Mesinha Dir")
    ye0 = fg_me.mesh.vertices[0].position.y()
    yd0 = fg_md.mesh.vertices[0].position.y()
    assert CabinetInteract.set_piece_open_fraction(fg_me, 1.0, module_group=cab)
    assert fg_me.mesh.vertices[0].position.y() - ye0 < -0.20
    assert fg_md.mesh.vertices[0].position.y() == pytest.approx(yd0, abs=1e-5)

    beliche = CabinetBuilder.build_module_group({
        "tipo": "beliche",
        "largura": 950.0,
        "altura": 1600.0,
        "profundidade": 2000.0,
    })
    bel_names = {ch.name for ch in beliche.children}
    assert "Beliche - Guarda-Corpo Traseiro" in bel_names
    assert "Beliche - Montante Escada" in bel_names
    assert "Beliche - Montante Escada Frontal" in bel_names


def test_sp_prof_ui_range_suporta_camas():
    from PySide6.QtWidgets import QApplication, QFormLayout

    from trazomob.ui.module_dialog_sections import ModuleDialogSectionsMixin
    from trazomob.ui.sidebar_panel import TrazoMobSidebarPanel

    app = QApplication.instance() or QApplication([])
    assert app is not None

    panel = TrazoMobSidebarPanel(None)
    panel._ensure_form_built()
    assert panel.sp_prof.maximum() >= 2050
    panel.sp_prof.setValue(2050)
    assert panel.sp_prof.value() == 2050

    class _DialogHolder(ModuleDialogSectionsMixin):
        pass

    holder = _DialogHolder()
    holder._build_dimensions_section(QFormLayout())
    assert holder.sp_prof.maximum() >= 2050
    holder.sp_prof.setValue(2050)
    assert holder.sp_prof.value() == 2050


def test_build_cama_colmeia():
    """Valida geometria estrutural da cama colmeia sem colchão e inclusão integral no plano de corte."""
    from core.scene import Scene
    from trazomob.production.parts import extract_parts

    grp = CabinetBuilder.build_module_group({
        "tipo": "cama_colmeia",
        "largura": 1400,
        "altura": 350,
        "profundidade": 1950,
        "espessura": 18,
        "material_caixa": "Branco_TX",
        "material_frentes": "Branco_TX",
    })
    assert grp is not None
    child_names = [getattr(c, "name", "") for c in getattr(grp, "children", [])]
    assert any("Rodapé" in n for n in child_names)
    assert any("Travessa" in n for n in child_names)
    assert any("Estrado Cabeceira" in n for n in child_names)
    assert all("Colchão" not in n for n in child_names)

    # Verifica quando parametrizado com apoio tipo pé e ilustração do colchão
    grp_pe = CabinetBuilder.build_module_group({
        "tipo": "cama_colmeia",
        "largura": 1400,
        "altura": 350,
        "profundidade": 1950,
        "espessura": 18,
        "material_caixa": "Branco_TX",
        "material_frentes": "Branco_TX",
        "tipo_apoio": "pe",
        "tem_colchao": True,
    })
    pe_names = [getattr(c, "name", "") for c in getattr(grp_pe, "children", [])]
    assert any("Pé" in n for n in pe_names)
    assert any("Colchão" in n for n in pe_names)
    # Garante que colchão visual não entra no plano de corte
    sc_test = Scene()
    sc_test.groups.append(grp_pe)
    parts_pe = extract_parts(sc_test)
    assert all("Colchão" not in p["nome"] for p in parts_pe)

    bbox = _bbox_mm(grp.children)
    assert bbox == pytest.approx((1400.0, 1950.0, 350.0), abs=1.0)

    scene = Scene()
    scene.groups.append(grp)
    parts = extract_parts(scene)
    part_names = [p["nome"] for p in parts]
    assert len(parts) == len(grp.children)
    assert any("Travessa" in n for n in part_names)


def test_export_hellomob_file(tmp_path):
    """Valida geração, serialização JSON e releitura do formato .hellomob."""
    from core.scene import Scene
    from trazomob.production.export import (
        build_hellomob_payload,
        export_trazomob_hellomob,
        import_hellomob_file,
    )
    from trazomob.production.parts import extract_parts

    grp = CabinetBuilder.build_module_group(
        {
            "tipo": "cama_colmeia",
            "largura": 1400,
            "altura": 350,
            "profundidade": 1950,
            "espessura": 18,
            "material_caixa": "Branco_TX",
            "material_frentes": "Branco_TX",
        },
        offset=(0.5, 0.25, 0.0),
    )
    scene = Scene()
    scene.groups.append(grp)

    parts = extract_parts(scene)
    payload = build_hellomob_payload(parts, scene=scene)
    assert len(payload) == 1
    mod = payload[0]
    assert mod["attributes"]["module_type"] == "cama_colmeia"
    assert mod["attributes"]["_lenx_nominal"] == pytest.approx(1400.0)
    assert mod["attributes"]["_leny_nominal"] == pytest.approx(1950.0)
    assert mod["attributes"]["_lenz_nominal"] == pytest.approx(350.0)
    assert mod["position"]["x"] == pytest.approx(500.0)
    assert mod["position"]["y"] == pytest.approx(250.0)
    assert len(mod["children"]) == len(parts)
    assert all("Colchão" not in c["name"] for c in mod["children"])

    out_file = tmp_path / "projeto.hellomob"
    export_trazomob_hellomob(scene, out_file)
    assert out_file.is_file()

    loaded = import_hellomob_file(out_file)
    assert len(loaded) == 1
    assert loaded[0]["name"] == mod["name"]
    assert len(loaded[0]["children"]) == len(parts)
