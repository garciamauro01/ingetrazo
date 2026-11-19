# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes unitários para o construtor de esquadrias (portas e janelas paramétricas)."""
import pytest
from trazomob.builders.esquadrias import EsquadriaBuilder


def test_build_porta_giro():
    """Testa geração de porta de giro com marco, alisar e folha."""
    porta = EsquadriaBuilder.build_porta_giro(
        largura_mm=800.0,
        altura_mm=2100.0,
        esp_parede_mm=150.0,
        lado_abertura="right",
        acabamento="madeira_branca",
    )

    assert "Porta Giro 800x2100" in porta.name
    assert "trazomob_esquadria" in porta.ext
    info = porta.ext["trazomob_esquadria"]
    assert info["tipo"] == "porta_giro"
    assert info["largura_mm"] == 800.0
    assert info["altura_mm"] == 2100.0

    children = getattr(porta, "children", []) or getattr(porta, "groups", [])
    # Deve conter batentes, alisares frontais/traseiros, folha e maçaneta
    assert len(children) >= 10

    # Verifica se a folha da porta foi criada
    folhas = [c for c in children if "Folha da Porta" in c.name]
    assert len(folhas) == 1


def test_build_janela_correr():
    """Testa geração de janela de correr de 2 folhas com caixilho e vidro."""
    janela = EsquadriaBuilder.build_janela_correr(
        largura_mm=1200.0,
        altura_mm=1000.0,
        esp_parede_mm=150.0,
        peitoril_mm=1100.0,
        acabamento_aluminio="aluminio_preto",
        tipo_vidro="vidro_incolor",
    )

    assert "Janela Correr 1200x1000" in janela.name
    assert "trazomob_esquadria" in janela.ext
    info = janela.ext["trazomob_esquadria"]
    assert info["tipo"] == "janela_correr"
    assert info["peitoril_mm"] == 1100.0

    children = getattr(janela, "children", []) or getattr(janela, "groups", [])
    # Marco (4) + 2 folhas x (4 quadros + 1 vidro) = 14 peças
    assert len(children) >= 14

    vidros = [c for c in children if "Vidro" in c.name]
    assert len(vidros) == 2


def test_build_janela_maximar():
    """Testa janela Maxim-Ar para banheiros."""
    maximar = EsquadriaBuilder.build_janela_maximar(
        largura_mm=600.0,
        altura_mm=600.0,
        peitoril_mm=1600.0,
    )

    assert "Maxim-Ar 600x600" in maximar.name
    info = maximar.ext["trazomob_esquadria"]
    assert info["tipo"] == "janela_maximar"
    assert info["peitoril_mm"] == 1600.0


def test_build_porta_pivotante():
    """Testa geração de porta pivotante com frisos e puxador inox."""
    piv = EsquadriaBuilder.build_porta_pivotante(
        largura_mm=1000.0,
        altura_mm=2150.0,
        esp_parede_mm=150.0,
        acabamento="madeira_freijo",
    )
    assert "Porta Pivotante 1000x2150" in piv.name
    assert "trazomob_esquadria" in piv.ext
    info = piv.ext["trazomob_esquadria"]
    assert info["tipo"] == "porta_pivotante"
    children = getattr(piv, "children", []) or getattr(piv, "groups", [])
    # Deve conter batentes, alisares, folha, frisos e suportes/barra de puxador
    assert len(children) >= 14
    barras = [c for c in children if "Barra Inox" in c.name]
    assert len(barras) == 1


def test_build_porta_correr_vidro():
    """Testa porta de correr de vidro 2 folhas (porta balcão)."""
    p_vidro = EsquadriaBuilder.build_porta_correr_vidro(
        largura_mm=1600.0,
        altura_mm=2100.0,
        esp_parede_mm=150.0,
    )
    assert "Porta Balcão Vidro 1600x2100" in p_vidro.name
    info = p_vidro.ext["trazomob_esquadria"]
    assert info["tipo"] == "porta_correr_vidro"
    children = getattr(p_vidro, "children", []) or getattr(p_vidro, "groups", [])
    vidros = [c for c in children if "Vidro" in c.name]
    assert len(vidros) == 2


def test_build_janela_correr_4folhas():
    """Testa janela de correr 4 folhas (2 fixas + 2 móveis)."""
    j4 = EsquadriaBuilder.build_janela_correr_4folhas(
        largura_mm=1900.0,
        altura_mm=1200.0,
        peitoril_mm=1000.0,
    )
    assert "Janela Correr 4F 1900x1200" in j4.name
    info = j4.ext["trazomob_esquadria"]
    assert info["tipo"] == "janela_correr_4f"
    children = getattr(j4, "children", []) or getattr(j4, "groups", [])
    vidros = [c for c in children if "Vidro" in c.name]
    assert len(vidros) == 4


def test_build_janela_vertical_bandeira():
    """Testa janela vertical com bandeira fixa e folha basculante."""
    jv = EsquadriaBuilder.build_janela_vertical_bandeira(
        largura_mm=500.0,
        altura_mm=1200.0,
        peitoril_mm=900.0,
    )
    assert "Janela Vertical Bandeira 500x1200" in jv.name
    info = jv.ext["trazomob_esquadria"]
    assert info["tipo"] == "janela_vertical_bandeira"
    children = getattr(jv, "children", []) or getattr(jv, "groups", [])
    vidros = [c for c in children if "Vidro" in c.name]
    assert len(vidros) == 2  # 1 bandeira + 1 basculante


def test_esquadrias_reais_igz_catalog():
    """Testa carregamento e parametrização dos modelos reais extraídos do SKP (.igz)."""
    from trazomob.domain.catalog import MODULE_CATALOG
    from trazomob.builders.cabinet import CabinetBuilder

    items = MODULE_CATALOG.get("Portas & Janelas", [])
    assert len(items) == 11  # Inclui porta_correr_vidro_4f_287 extraída do SKP com cinemática de correr

    for it in items:
        params = dict(it)
        params["tipo"] = it["id"]
        group = CabinetBuilder.build_module_group(params)
        assert group is not None
        assert group.layer == "ESQUADRIAS"
        assert "trazomob_esquadria" in group.ext
        info = group.ext["trazomob_esquadria"]
        assert info["tipo"] == it["id"]
        assert info["largura_mm"] == it["largura"]
        assert info["altura_mm"] == it["altura"]

        # Verifica se possui peças com geometria real (faces válidas)
        children = getattr(group, "children", [])
        assert len(children) >= 1
        total_faces = sum(len(c.mesh.faces) for c in children if c.mesh)
        assert total_faces >= 50, f"Modelo {it['id']} possui menos faces do que o esperado ({total_faces})"


def test_recorte_parede_ao_colocar_porta():
    """Testa se a parede hospedeira é recortada automaticamente gerando o vão vazado para a porta."""
    from PySide6.QtGui import QVector3D
    from core.scene import Scene
    from trazomob.builders.cabinet import CabinetBuilder
    from trazomob.wall.builder import WallBuilderTool
    from trazomob.wall.mesh_builder import WallMeshBuilder

    scene = Scene()
    pts = [QVector3D(0, 0, 0), QVector3D(4, 0, 0)]
    wall = WallBuilderTool.build_chain_group(scene, pts, is_closed=False, altura_m=2.6, espessura_m=0.15)
    assert len(wall.mesh.faces) == 6  # Parede contínua maciça inicial

    # Insere uma porta de 80cm centrada em X=2.0m
    door = CabinetBuilder.build_module_group(
        {"tipo": "porta_giro_80", "largura": 800, "altura": 2100, "profundidade": 180},
        offset=(1.6, 0.0, 0.0),
    )
    scene.groups.extend([wall, door])

    # Sincroniza vãos
    changed = WallMeshBuilder.sync_scene_wall_openings(scene)
    assert changed is True
    assert scene.version >= 1

    # A parede recortada deve possuir as faces divididas da verga, montantes e bonecas do túnel
    from core.solids import is_solid
    from core.solids import is_solid
    assert is_solid(wall) is True
    assert len(wall.mesh.faces) == 10

    # Verifica se os metadados da parede registraram o vão
    openings = wall.ext["trazomob_wall"].get("openings", [])
    assert len(openings) == 1
    op = openings[0]
    assert op["segment_index"] == 0
    assert pytest.approx(op["altura_m"], 0.01) == 2.1
    assert pytest.approx(op["peitoril_m"], 0.01) == 0.0
    # Largura de 80cm em parede de 4m = fração ~ 0.20
    assert pytest.approx(op["u1"] - op["u0"], 0.01) == 0.20

    # Verifica se a parede recortada e um solido integro (sem arestas abertas)
    from core.solids import is_solid, solid_report
    ok, vol = solid_report(wall.mesh)
    assert ok is True
    assert vol > 0.0

def test_recorte_parede_ao_colocar_janela():
    """Testa se a parede hospedeira é recortada para janela com peitoril sólido e verga superior."""
    from PySide6.QtGui import QVector3D
    from core.scene import Scene
    from trazomob.builders.cabinet import CabinetBuilder
    from trazomob.wall.builder import WallBuilderTool
    from trazomob.wall.mesh_builder import WallMeshBuilder

    scene = Scene()
    pts = [QVector3D(0, 0, 0), QVector3D(4, 0, 0)]
    wall = WallBuilderTool.build_chain_group(scene, pts, is_closed=False, altura_m=2.6, espessura_m=0.15)

    # Insere janela de correr com peitoril 1.0m e altura 1.2m
    janela = CabinetBuilder.build_module_group(
        {"tipo": "janela_correr_2f_130", "largura": 1300, "altura": 1200, "peitoril": 1000, "profundidade": 150},
        offset=(1.35, 0.0, 1.0),
    )
    scene.groups.extend([wall, janela])

    changed = WallMeshBuilder.sync_scene_wall_openings(scene)
    assert changed is True
    from core.solids import is_solid
    assert is_solid(wall) is True
    assert len(wall.mesh.faces) == 10

    openings = wall.ext["trazomob_wall"].get("openings", [])
    assert len(openings) == 1
    assert pytest.approx(openings[0]["peitoril_m"], 0.01) == 1.0
    assert pytest.approx(openings[0]["altura_m"], 0.01) == 1.2


def test_recorte_muda_junto_ao_mover_porta():
    """Testa se o vão na parede se desloca junto quando a porta é movida de lugar e fecha se for deletada."""
    from PySide6.QtGui import QVector3D
    from core.scene import Scene
    from trazomob.builders.cabinet import CabinetBuilder
    from trazomob.wall.builder import WallBuilderTool
    from trazomob.wall.mesh_builder import WallMeshBuilder

    scene = Scene()
    pts = [QVector3D(0, 0, 0), QVector3D(6, 0, 0)]
    wall = WallBuilderTool.build_chain_group(scene, pts, is_closed=False, altura_m=2.6, espessura_m=0.15)

    # 1. Porta na posição inicial (X ~ 1.5m)
    door = CabinetBuilder.build_module_group(
        {"tipo": "porta_giro_80", "largura": 800, "altura": 2100, "profundidade": 180},
        offset=(1.1, 0.0, 0.0),
    )
    scene.groups.extend([wall, door])
    WallMeshBuilder.sync_scene_wall_openings(scene)

    op_ini = wall.ext["trazomob_wall"]["openings"][0]
    u0_ini = op_ini["u0"]
    u1_ini = op_ini["u1"]

    # 2. Desloca a porta 2.4 metros para a direita (X vai para ~ 3.9m)
    shift = QVector3D(2.4, 0.0, 0.0)
    for c in getattr(door, "children", [door]):
        for v in c.mesh.vertices:
            v.position += shift
        c.mesh._mut_serial += 1

    # Sincroniza a cena (chamado no término do arraste magnético ou ao mover)
    changed = WallMeshBuilder.sync_scene_wall_openings(scene)
    assert changed is True

    op_novo = wall.ext["trazomob_wall"]["openings"][0]
    u0_novo = op_novo["u0"]
    u1_novo = op_novo["u1"]

    # 2.4 metros em uma parede de 6 metros equivale a um avanço exato de 0.40 em U
    assert pytest.approx(u0_novo - u0_ini, 0.01) == 0.40
    assert pytest.approx(u1_novo - u1_ini, 0.01) == 0.40

    # 3. Se a porta for deletada da cena, a parede volta automaticamente a ser inteiriça e contínua
    scene.groups.remove(door)
    WallMeshBuilder.sync_scene_wall_openings(scene)
    assert len(wall.ext["trazomob_wall"]["openings"]) == 0
    assert len(wall.mesh.faces) == 6  # Sólido maciço restaurado






def test_porta_pivotante_vidro_solids_sound():
    """Valida que todos os subcomponentes da porta pivotante de vidro são sólidos estanques (watertight manifolds)
    e que o puxador e as braçadeiras rotacionam articuladamente com a folha de vidro.
    """
    import plugins.solid_inspector as si
    from trazomob.builders.esquadrias import EsquadriaBuilder
    from trazomob.interaction.interact import CabinetInteract

    porta = EsquadriaBuilder.load_esquadria_igz("porta_pivotante_vidro", 800.0, 2100.0, 150.0)
    assert porta is not None
    pieces = [c for c in porta.children if c.mesh]
    assert len(pieces) == 4

    for p in pieces:
        rep = si.inspect_mesh(p.mesh)
        assert si.is_sound(rep) is True, f"Componente {p.name} não é estanque: open={len(rep['open'])}, over={len(rep['over'])}"

    folha = [c for c in porta.children if "Folha" in c.name][0]
    pux = [c for c in porta.children if "Puxador" in c.name][0]
    brac = [c for c in porta.children if "Braçadeira" in c.name][0]
    piv_fix = [c for c in porta.children if "Pivôs" in c.name][0]

    orig_pux_pos = pux.mesh.vertices[0].position
    orig_brac_pos = brac.mesh.vertices[0].position
    orig_fix_pos = piv_fix.mesh.vertices[0].position

    CabinetInteract.toggle_piece(folha, porta)
    assert folha.ext.get("is_open") is True
    assert pux.mesh.vertices[0].position != orig_pux_pos
    assert brac.mesh.vertices[0].position != orig_brac_pos
    assert piv_fix.mesh.vertices[0].position == orig_fix_pos

    CabinetInteract.toggle_piece(folha, porta)
    assert folha.ext.get("is_open") is False
    assert pux.mesh.vertices[0].position == orig_pux_pos
    assert brac.mesh.vertices[0].position == orig_brac_pos


@pytest.mark.parametrize("largura", [1500, 1300, 1200, 1100, 1000, 800])
def test_janela_2f_largura_menor_nao_colapsa_marco(largura):
    """Regressao: abaixo de 1,30 m a barra central do marco colapsava/invertia.

    Os limites fixos (0.65/0.60) aplicavam deslocamentos diferentes a vertices
    separados por ~5 cm. Com delta_w negativo os vertices se encontravam
    (1,20 m) e depois trocavam de ordem (< 1,20 m), deformando a esquadria.
    """
    base = EsquadriaBuilder.load_esquadria_igz(
        "janela_correr_2f_130", 1300.0, 1200.0, 150.0)
    janela = EsquadriaBuilder.load_esquadria_igz(
        "janela_correr_2f_130", float(largura), 1200.0, 150.0)

    marco_base = next(c for c in base.children if "Marco" in c.name)
    marco = next(c for c in janela.children if "Marco" in c.name)

    xs_base = sorted({round(v.position.x(), 5) for v in marco_base.mesh.vertices})
    xs = sorted({round(v.position.x(), 5) for v in marco.mesh.vertices})

    # Nenhuma colisao de vertices: a contagem de X distintos e preservada.
    assert len(xs) == len(xs_base), (
        f"{largura} mm colapsou {len(xs_base) - len(xs)} posicoes do marco")

    # Escala uniforme: todos os X crescem pela mesma proporcao.
    scale = largura / 1300.0
    for xb, x in zip(xs_base, xs):
        assert x == pytest.approx(xb * scale, abs=1e-4), (
            f"{largura} mm: X {xb} -> {x}, esperado {xb * scale}")

    # A largura total acompanha a solicitacao.
    assert xs[-1] == pytest.approx(largura / 1000.0, abs=1e-4)

    # O curso das folhas escala junto, mantendo o alinhamento.
    folha_base = next(c for c in base.children if "Esquerda" in c.name)
    folha = next(c for c in janela.children if "Esquerda" in c.name)
    slide_base = folha_base.ext["slide_distance"]
    assert folha.ext["slide_distance"] == pytest.approx(slide_base * scale, abs=1e-4)

    # Os atributos de material/opacidade do vidro sobrevivem ao redimensionamento.
    assert any((f.attrs or {}).get("opacity") is not None
               for c in janela.children if c.mesh for f in c.mesh.faces)
