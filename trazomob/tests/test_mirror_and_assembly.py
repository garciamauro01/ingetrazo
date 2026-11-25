# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Espelho paramétrico, agrupamento de módulos e Ambientes/Pavimentos do TrazoMob.

Cobrem as frentes da onda 2:
* espelhar reconstrói o módulo com ``mirror_x`` gravado no ``ext``
* agrupar/desagrupar usa comandos do core, marca como ``assembly``
* ambientes/pavimentos: entidade com nome, piso, teto, lista de módulos
"""
import pytest
from PySide6.QtGui import QVector3D
from PySide6.QtWidgets import QApplication

from core.group import Group, iter_placements
from core.mesh import Mesh
from core.scene import Scene
from trazomob.builders.cabinet import CabinetBuilder
from trazomob.builders.mirror import MIRROR_PARAM, is_mirrored, mirror_module_geometry
from trazomob.domain import schema
from trazomob.domain.ambiente import (
    AmbienteBuilder,
    is_ambiente,
    is_pavimento,
    iter_ambientes,
    iter_modulos_do_ambiente,
    iter_pavimentos,
    resumo_ambiente,
)
from trazomob.domain.assembly import (
    apply_assembly_tag,
    build_assembly_command,
    build_dissolve_command,
    is_assembly,
    iter_module_groups,
)
from trazomob.production.parts import extract_parts


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _params(**extra):
    params = {
        "tipo": "balcao",
        "largura": 800,
        "altura": 720,
        "profundidade": 550,
        "offset": (1.0, 2.0, 0.0),
    }
    params.update(extra)
    return params


def _build(**extra):
    return CabinetBuilder.build_module_group(_params(**extra), offset=(1.0, 2.0, 0.0))


def _module_bounds(mod):
    xs, ys, zs = [], [], []
    for piece, xform in iter_placements(mod):
        mesh = getattr(piece, "mesh", None)
        if mesh is None:
            continue
        for vertex in mesh.vertices:
            p = xform.map(vertex.position) if xform is not None else vertex.position
            xs.append(p.x())
            ys.append(p.y())
            zs.append(p.z())
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def _pieces_by_name(mod):
    return {piece.name: piece for piece in mod.children}


# --------------------------------------------------------------------------
# Espelho: geometria
# --------------------------------------------------------------------------

def test_espelho_preserva_os_limites_da_caixaria(qapp):
    normal = _build()
    espelhado = _build(mirror_x=True)

    b_normal = _module_bounds(normal)
    b_esp = _module_bounds(espelhado)
    for a, b in zip(b_normal, b_esp):
        assert a == pytest.approx(b, abs=1e-5)


def test_espelho_persiste_o_parametro_e_sobrevive_a_reconstrucao(qapp):
    espelhado = _build(mirror_x=True)

    assert is_mirrored(espelhado)
    assert espelhado.ext["trazomob"][MIRROR_PARAM] is True
    # O espelho legado é o mesmo dicionário: o parâmetro chega aos dois.
    assert espelhado.ext["trazomob_module"][MIRROR_PARAM] is True

    # Reeditar reconstrói a partir dos parâmetros salvos e continua espelhado.
    salvo = dict(espelhado.ext["trazomob"])
    salvo["largura"] = 900
    reconstruido = CabinetBuilder.build_module_group(salvo, offset=(1.0, 2.0, 0.0))
    assert is_mirrored(reconstruido)
    b = _module_bounds(reconstruido)
    assert b[1] - b[0] == pytest.approx(0.9, abs=1e-3)


def test_espelho_desligado_nao_marca_o_modulo(qapp):
    assert not is_mirrored(_build())
    assert not is_mirrored(_build(mirror_x=False))


def test_espelho_troca_a_fita_das_bordas_laterais(qapp):
    """Chapa horizontal (base): L1/L2 são as bordas em X e trocam de lado."""
    normal = _pieces_by_name(_build())
    espelhado = _pieces_by_name(_build(mirror_x=True))

    base_n = normal["Balcao - Base Inferior"].ext["trazomob"]
    base_e = espelhado["Balcao - Base Inferior"].ext["trazomob"]
    assert base_n["fita_l1"] is True and base_n["fita_l2"] is False
    assert base_e["fita_l1"] is False and base_e["fita_l2"] is True
    # As bordas em Z (C1/C2) não mudam com uma reflexão em X.
    assert base_e["fita_c1"] == base_n["fita_c1"]
    assert base_e["fita_c2"] == base_n["fita_c2"]


def test_espelho_nao_troca_a_fita_vertical_da_lateral(qapp):
    """Lateral é fina em X: L1/L2 são topo/base em Z e ficam como estão."""
    normal = _pieces_by_name(_build())
    espelhado = _pieces_by_name(_build(mirror_x=True))

    lat_n = normal["Balcao - Lateral Esquerda"].ext["trazomob"]
    lat_e = espelhado["Balcao - Lateral Direita"].ext["trazomob"]
    assert (lat_n["fita_l1"], lat_n["fita_l2"]) == (True, False)
    assert (lat_e["fita_l1"], lat_e["fita_l2"]) == (True, False)


def test_espelho_troca_lado_da_porta_e_nomes(qapp):
    normal = _pieces_by_name(_build())
    espelhado = _pieces_by_name(_build(mirror_x=True))

    porta_n = normal["Balcao - Porta Esq"].ext["trazomob"]
    assert porta_n["door_side"] == "left"

    # A porta da esquerda vira a da direita, e vice-versa.
    assert "Balcao - Porta Dir" in espelhado
    assert "Balcao - Porta Esq" in espelhado
    porta_e = espelhado["Balcao - Porta Dir"].ext["trazomob"]
    assert porta_e["door_side"] == "right"
    assert porta_e["nome"] == "Balcao - Porta Dir"

    # A lateral acompanha a troca de nome.
    assert "Balcao - Lateral Direita" in espelhado
    assert espelhado["Balcao - Lateral Direita"].ext["trazomob"]["nome"] == (
        "Balcao - Lateral Direita"
    )


def test_espelho_inverte_as_usinagens_da_peca_frontal(qapp):
    normal = _pieces_by_name(_build())
    espelhado = _pieces_by_name(_build(mirror_x=True))

    porta_n = normal["Balcao - Porta Esq"].ext["trazomob"]
    porta_e = espelhado["Balcao - Porta Dir"].ext["trazomob"]

    comprimento = float(porta_n["comprimento"])
    ops_n = porta_n["operacoes"]
    ops_e = porta_e["operacoes"]
    assert ops_n, "a porta precisa ter usinagens para o teste valer"
    assert len(ops_n) == len(ops_e)
    for antes, depois in zip(ops_n, ops_e):
        if antes.get("x") is None:
            continue
        assert depois["x"] == pytest.approx(comprimento - float(antes["x"]), abs=1e-3)


def test_espelho_mantem_as_normais_para_fora(qapp):
    """Refletir sem reverter o loop inverteria as normais e sumiria com o sólido."""
    chapa = Group(_box_mesh((0.0, 0.0, 0.0), (0.4, 0.018, 0.3)), name="Chapa")
    schema.set_module_data(chapa, {"tipo": "peca_avulsa"})
    master = Group(Mesh(), name="Módulo de uma peça")
    master.children = [chapa]

    # A reflexão no centro devolve a chapa ao mesmo intervalo [0, 0.4].
    mirror_module_geometry(master, 0.2)

    xs = [v.position.x() for v in chapa.mesh.vertices]
    assert min(xs) == pytest.approx(0.0, abs=1e-5)
    assert max(xs) == pytest.approx(0.4, abs=1e-5)

    centro_solido = _mesh_center(chapa.mesh)
    for face in chapa.mesh.faces:
        normal = face.normal()
        outward = face.centroid() - centro_solido
        assert QVector3D.dotProduct(normal, outward) > 0.0


def test_espelho_descarta_cache_de_animacao(qapp):
    mod = _build()
    porta = _pieces_by_name(mod)["Balcao - Porta Esq"]
    porta.ext["hinge_pivot"] = object()
    porta.ext["orig_vertices"] = [object()]
    porta.ext["is_open"] = True

    mirror_module_geometry(mod, 1.4)

    for chave in ("hinge_pivot", "orig_vertices", "is_open"):
        assert chave not in porta.ext


def test_troca_de_nomes_so_atinge_palavras_de_lado(qapp):
    from trazomob.builders.mirror import _swap_side_words

    assert _swap_side_words("Porta Esq") == "Porta Dir"
    assert _swap_side_words("Porta Esq. 2") == "Porta Dir. 2"
    assert _swap_side_words("Lateral Esquerda") == "Lateral Direita"
    assert _swap_side_words("Door Left") == "Door Right"
    # "Esq" dentro de outra palavra não é uma abreviação de lado.
    assert _swap_side_words("Esquadria de Correr") == "Esquadria de Correr"


def test_is_mirrored_le_o_espelho_legado(qapp):
    modulo = Group(Mesh(), name="Legado")
    modulo.ext = {"trazomob_module": {MIRROR_PARAM: True}}
    assert is_mirrored(modulo)

    modulo.ext = {"trazomob": {MIRROR_PARAM: False},
                  "trazomob_module": {MIRROR_PARAM: True}}
    assert not is_mirrored(modulo), "a chave oficial manda"


# --------------------------------------------------------------------------
# Agrupar / desagrupar
# --------------------------------------------------------------------------

def _scene_com_modulos():
    scene = Scene()
    mod_a = _build()
    mod_b = CabinetBuilder.build_module_group(
        _params(offset=(1.9, 2.0, 0.0)), offset=(1.9, 2.0, 0.0)
    )
    scene.groups.extend([mod_a, mod_b])
    scene.selection = {mod_a, mod_b}
    return scene, mod_a, mod_b


def test_agrupar_precisa_de_dois_modulos(qapp):
    scene = Scene()
    mod = _build()
    scene.groups.append(mod)
    scene.selection = {mod}
    assert build_assembly_command([mod]) is None


def test_agrupar_marca_assembly_e_preserva_os_modulos(qapp):
    scene, mod_a, mod_b = _scene_com_modulos()

    cmd = build_assembly_command([mod_a, mod_b], name="Grupo de Módulos")
    assert cmd is not None
    cmd.do(scene)
    container = apply_assembly_tag(cmd.container, name="Grupo de Módulos")

    assert is_assembly(container)
    assert container.ext["trazomob"]["kind"] == "assembly"
    assert len(container.children) == 2
    assert mod_a not in scene.groups and mod_b not in scene.groups
    # Nenhum parâmetro de módulo foi tocado pelo agrupamento.
    assert schema.module_params(mod_a)["largura"] == 800
    assert schema.module_params(mod_b)["largura"] == 800


def test_cutlist_enxerga_modulos_agrupados(qapp):
    scene, mod_a, mod_b = _scene_com_modulos()
    antes = extract_parts(scene)
    assert len(antes) >= 20

    cmd = build_assembly_command([mod_a, mod_b], name="Grupo de Módulos")
    cmd.do(scene)
    apply_assembly_tag(cmd.container, name="Grupo de Módulos")

    depois = extract_parts(scene)
    assert len(depois) == len(antes), "agrupar não pode esconder peças do cutlist"

    # Com um módulo agrupado selecionado, o cutlist da seleção o encontra.
    scene.selection = {mod_a}
    selecionadas = extract_parts(scene, selected_only=True)
    assert len(selecionadas) == len(antes) // 2


def test_iter_module_groups_acha_modulos_em_qualquer_nivel(qapp):
    scene, mod_a, mod_b = _scene_com_modulos()
    cmd = build_assembly_command([mod_a, mod_b], name="Grupo de Módulos")
    cmd.do(scene)
    container = apply_assembly_tag(cmd.container, name="Grupo de Módulos")

    encontrados = list(iter_module_groups(scene.groups))
    assert mod_a in encontrados
    assert mod_b in encontrados
    assert container not in encontrados


def test_desagrupar_devolve_os_modulos_ao_modelo(qapp):
    scene, mod_a, mod_b = _scene_com_modulos()
    cmd = build_assembly_command([mod_a, mod_b], name="Grupo de Módulos")
    cmd.do(scene)
    container = apply_assembly_tag(cmd.container, name="Grupo de Módulos")

    dissolve = build_dissolve_command(container)
    assert dissolve is not None
    dissolve.do(scene)

    assert container not in scene.groups
    assert mod_a in scene.groups
    assert mod_b in scene.groups
    # Os módulos voltam inteiros, com os parâmetros e as peças de antes.
    assert schema.module_params(mod_a)["tipo"] == "balcao"
    from trazomob.builders.hardware_geometry import is_hardware_group
    modulos_filhos = [c for c in mod_a.children if not is_hardware_group(c)]
    assert len(modulos_filhos) == 10


def test_desagrupar_recusa_grupo_que_nao_e_assembly(qapp):
    comum = Group(Mesh(), name="Grupo comum")
    comum.children = [_build(), _build()]
    assert build_dissolve_command(comum) is None


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _box_mesh(origin, size):
    from PySide6.QtGui import QVector3D

    ox, oy, oz = origin
    sx, sy, sz = size
    mesh = Mesh()
    corners = [
        QVector3D(ox, oy, oz),
        QVector3D(ox + sx, oy, oz),
        QVector3D(ox + sx, oy + sy, oz),
        QVector3D(ox, oy + sy, oz),
        QVector3D(ox, oy, oz + sz),
        QVector3D(ox + sx, oy, oz + sz),
        QVector3D(ox + sx, oy + sy, oz + sz),
        QVector3D(ox, oy + sy, oz + sz),
    ]
    faces = [
        (0, 3, 2, 1),  # baixo
        (4, 5, 6, 7),  # cima
        (0, 1, 5, 4),  # frente
        (1, 2, 6, 5),  # direita
        (2, 3, 7, 6),  # trás
        (3, 0, 4, 7),  # esquerda
    ]
    for indices in faces:
        mesh.add_face([corners[i] for i in indices])
    return mesh


def _mesh_center(mesh):
    xs = [v.position.x() for v in mesh.vertices]
    ys = [v.position.y() for v in mesh.vertices]
    zs = [v.position.z() for v in mesh.vertices]
    from PySide6.QtGui import QVector3D
    return QVector3D(
        (min(xs) + max(xs)) / 2.0,
        (min(ys) + max(ys)) / 2.0,
        (min(zs) + max(zs)) / 2.0,
    )


# --------------------------------------------------------------------------
# Ambientes / Pavimentos
# --------------------------------------------------------------------------

def _build_ambiente_simples(qapp, nome="Cozinha", pavimento="Térreo"):
    """Cria um ambiente simples com paredes, piso, teto (mock)."""
    from trazomob.domain import schema
    from trazomob.domain.ambiente import (
        set_ceiling_data,
        set_floor_data,
    )

    # Paredes (mock - grupo com mesh retangular)
    parede = Group(_box_mesh((0.0, 0.0, 0.0), (4.0, 0.15, 2.7)), name="Parede")
    schema.set_wall_data(parede, {"altura": 2.7})

    # Piso
    piso = Group(_box_mesh((0.0, 0.0, 0.0), (4.0, 3.0, 0.1)), name="Piso")
    set_floor_data(piso, {"ambiente": nome})

    # Teto
    teto = Group(_box_mesh((0.0, 0.0, 2.7), (4.0, 3.0, 0.05)), name="Teto")
    set_ceiling_data(teto, {"ambiente": nome})

    return AmbienteBuilder.build_ambiente_group(
        nome, [parede], piso, teto, pavimento, 0.0, 2.7
    )


def test_ambiente_kind_e_metadados(qapp):
    amb = _build_ambiente_simples(qapp, "Cozinha", "Térreo")

    assert is_ambiente(amb)
    assert amb.ext["trazomob"]["kind"] == "ambiente"
    assert amb.ext["trazomob"]["nome"] == "Cozinha"
    assert amb.ext["trazomob"]["pavimento"] == "Térreo"
    assert amb.ext["trazomob"]["area_m2"] > 0
    assert amb.ext["trazomob"]["pe_direito"] == pytest.approx(2.7, abs=0.1)


def test_pavimento_kind_e_agrupa_ambientes(qapp):
    from trazomob.domain.ambiente import set_pavimento_data

    pav = Group(Mesh(), name="Térreo")
    set_pavimento_data(pav, {"nome": "Térreo"})

    amb1 = _build_ambiente_simples(qapp, "Cozinha", "Térreo")
    amb2 = _build_ambiente_simples(qapp, "Sala", "Térreo")

    AmbienteBuilder.adicionar_ao_pavimento(pav, amb1)
    AmbienteBuilder.adicionar_ao_pavimento(pav, amb2)

    assert is_pavimento(pav)
    assert len(pav.children) == 2
    assert amb1 in pav.children
    assert amb2 in pav.children


def test_iter_ambientes_e_pavimentos(qapp):
    pav = Group(Mesh(), name="Térreo")
    from trazomob.domain.ambiente import set_pavimento_data
    set_pavimento_data(pav, {"nome": "Térreo"})

    amb1 = _build_ambiente_simples(qapp, "Cozinha", "Térreo")
    amb2 = _build_ambiente_simples(qapp, "Sala", "Térreo")
    AmbienteBuilder.adicionar_ao_pavimento(pav, amb1)
    AmbienteBuilder.adicionar_ao_pavimento(pav, amb2)

    scene_groups = [pav]
    ambientes = list(iter_ambientes(scene_groups))
    pavimentos = list(iter_pavimentos(scene_groups))

    assert len(ambientes) == 2
    assert len(pavimentos) == 1
    assert pavimentos[0] is pav


def test_iter_modulos_do_ambiente(qapp):
    amb = _build_ambiente_simples(qapp)
    mod = CabinetBuilder.build_module_group({
        "tipo": "balcao", "largura": 800, "altura": 720, "profundidade": 550,
        "offset": (0.5, 0.5, 0.0)
    }, offset=(0.5, 0.5, 0.0))
    amb.adopt([mod])

    modulos = list(iter_modulos_do_ambiente(amb))
    assert len(modulos) == 1
    assert modulos[0] is mod


def test_extract_parts_filtrado_por_ambiente(qapp):
    # Cria dois ambientes com módulos diferentes
    amb1 = _build_ambiente_simples(qapp, "Cozinha", "Térreo")
    amb2 = _build_ambiente_simples(qapp, "Sala", "Térreo")

    mod1 = CabinetBuilder.build_module_group({
        "tipo": "balcao", "largura": 800, "altura": 720, "profundidade": 550,
        "offset": (0.5, 0.5, 0.0)
    }, offset=(0.5, 0.5, 0.0))
    mod2 = CabinetBuilder.build_module_group({
        "tipo": "balcao", "largura": 600, "altura": 720, "profundidade": 550,
        "offset": (5.0, 0.5, 0.0)
    }, offset=(5.0, 0.5, 0.0))

    amb1.adopt([mod1])
    amb2.adopt([mod2])

    scene = Scene()
    scene.groups.extend([amb1, amb2])

    # Cutlist geral vê todos
    todos = extract_parts(scene)
    assert len(todos) >= 20  # ~10 peças por módulo

    # Cutlist filtrado por ambiente 1
    so_cozinha = extract_parts(scene, ambiente=amb1)
    assert len(so_cozinha) >= 10
    assert len(so_cozinha) < len(todos)

    # Cutlist filtrado por ambiente 2
    so_sala = extract_parts(scene, ambiente=amb2)
    assert len(so_sala) >= 10
    assert len(so_sala) < len(todos)


def test_resumo_ambiente_para_relatorio(qapp):
    amb = _build_ambiente_simples(qapp, "Cozinha", "Térreo")
    mod = CabinetBuilder.build_module_group({
        "tipo": "balcao", "largura": 800, "altura": 720, "profundidade": 550,
        "offset": (0.5, 0.5, 0.0)
    }, offset=(0.5, 0.5, 0.0))
    amb.adopt([mod])

    resumo = resumo_ambiente(amb)
    assert resumo["nome"] == "Cozinha"
    assert resumo["pavimento"] == "Térreo"
    assert resumo["area_m2"] > 0
    assert resumo["qtd_modulos"] == 1
    assert "Balcao" in resumo["modulos"][0]
