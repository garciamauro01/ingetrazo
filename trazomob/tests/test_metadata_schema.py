# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Onda 1 — confiança: persistência dos metadados e fonte única de leitura.

Cobrem o bug em que ``_unrot_carcass_span`` (e ``rot_z``/``rot_matrix_3d``)
era calculado depois de ``set_trazomob`` e nunca chegava ao documento, e a
divergência entre as três chaves de metadados (``trazomob``,
``trazomob_module``, ``trazomob_esquadria``).
"""
import pytest
from PySide6.QtWidgets import QApplication

from core.group import Group
from core.mesh import Mesh
from trazomob.builders.cabinet import CabinetBuilder
from trazomob.builders.esquadrias import EsquadriaBuilder
from trazomob.domain.entity import get_trazomob
from trazomob.domain import schema


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _params(rot_z=0.0, **extra):
    params = {
        "tipo": "balcao",
        "largura": 800,
        "altura": 720,
        "profundidade": 550,
        "rot_z": rot_z,
        "offset": (1.0, 2.0, 0.0),
    }
    params.update(extra)
    return params


# --------------------------------------------------------------------------
# 1. Persistência: o que é calculado depois de gravar os metadados não pode
#    ficar só na variável local.
# --------------------------------------------------------------------------

def test_module_persiste_unrot_carcass_span(qapp):
    mod = CabinetBuilder.build_module_group(_params(rot_z=90.0),
                                            offset=(1.0, 2.0, 0.0))

    oficial = mod.ext["trazomob"]
    legado = mod.ext["trazomob_module"]

    assert oficial["_unrot_carcass_span"] is not None, (
        "o span não-rotacionado é calculado depois de set_trazomob e precisa "
        "ser reaplicado no dicionário publicado"
    )
    # O espelho legado é o mesmo dicionário: nunca pode divergir.
    assert legado["_unrot_carcass_span"] == oficial["_unrot_carcass_span"]
    assert len(oficial["_unrot_carcass_span"]) == 6
    # Três primeiros campos: deslocamento do centro não-rotacionado; três
    # últimos: as medidas da caixaria em metros.
    span = oficial["_unrot_carcass_span"]
    assert span[3] == pytest.approx(0.8, abs=1e-3)
    assert span[4] == pytest.approx(0.55, abs=1e-3)
    assert span[5] == pytest.approx(0.72, abs=1e-3)


def test_module_persiste_rot_z_da_rotacao(qapp):
    """``rotacao`` (sem ``rot_z``) também precisa sobreviver ao build."""
    params = {
        "tipo": "balcao",
        "largura": 800,
        "altura": 720,
        "profundidade": 550,
        "rotacao": 90.0,
        "offset": (1.0, 2.0, 0.0),
    }
    mod = CabinetBuilder.build_module_group(params, offset=(1.0, 2.0, 0.0))

    assert mod.ext["trazomob"]["rot_z"] == pytest.approx(90.0)
    assert mod.ext["trazomob_module"]["rot_z"] == pytest.approx(90.0)


def test_module_persiste_rot_matrix_3d(qapp):
    matriz = [
        1.0, 0.0, 0.0, 0.0,
        0.0, 0.0, -1.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]
    mod = CabinetBuilder.build_module_group(
        _params(rot_matrix_3d=matriz), offset=(1.0, 2.0, 0.0))

    assert mod.ext["trazomob"]["rot_matrix_3d"] == matriz
    assert mod.ext["trazomob_module"]["rot_matrix_3d"] == matriz


def test_module_meta_sobrevive_a_reedicao(qapp):
    """Reconstruir com os parâmetros persistidos mantém o span."""
    mod = CabinetBuilder.build_module_group(_params(rot_z=90.0),
                                            offset=(1.0, 2.0, 0.0))
    salvo = dict(mod.ext["trazomob"])

    novo = CabinetBuilder.build_module_group(salvo, offset=(1.0, 2.0, 0.0))
    assert novo.ext["trazomob"]["_unrot_carcass_span"] is not None
    assert novo.ext["trazomob"]["rot_z"] == pytest.approx(90.0)


# --------------------------------------------------------------------------
# 2. Fonte única: leitura tolerante e escrita consistente.
# --------------------------------------------------------------------------

def test_kind_of_reconhece_todas_as_chaves(qapp):
    modulo = Group(Mesh(), name="Modulo")
    schema.set_module_data(modulo, {"tipo": "balcao", "largura": 800})
    assert schema.kind_of(modulo) == schema.KIND_MODULE

    porta = EsquadriaBuilder.build_porta_giro(
        largura_mm=800.0, altura_mm=2100.0, esp_parede_mm=150.0,
        lado_abertura="right", acabamento="madeira_branca")
    assert schema.kind_of(porta) == schema.KIND_ESQUADRIA

    parede = Group(Mesh(), name="Parede")
    parede.ext = {"trazomob_wall": {"espessura": 0.15}}
    assert schema.kind_of(parede) == schema.KIND_WALL

    luz = Group(Mesh(), name="Luz")
    luz.ext = {"trazomob_light": {"kind": "spot"}}
    assert schema.kind_of(luz) == schema.KIND_LIGHT

    assert schema.kind_of(Group(Mesh(), name="Solto")) is None
    assert schema.kind_of(None) is None


def test_params_of_preenche_apelidos_dos_dois_lados(qapp):
    """Só a chave legada de módulo: ``largura_mm`` aparece na leitura."""
    so_legado = Group(Mesh(), name="Fechamento")
    so_legado.ext = {"trazomob_module": {"tipo": "fechamento_canto",
                                         "largura": 600.0, "altura": 720.0,
                                         "profundidade": 350.0}}
    dados = schema.params_of(so_legado)
    assert dados["largura_mm"] == 600.0
    assert dados["altura_mm"] == 720.0
    assert dados["esp_parede_mm"] == 350.0
    # get_trazomob enxerga a chave legada, então a fonte única não perde nada.
    assert get_trazomob(so_legado)["tipo"] == "fechamento_canto"


def test_set_esquadria_data_mantem_as_tres_chaves_coerentes(qapp):
    porta = Group(Mesh(), name="Porta")
    schema.set_esquadria_data(
        porta, tipo="porta_giro", largura_mm=800.0, altura_mm=2100.0,
        esp_parede_mm=150.0, peitoril_mm=0.0, rot_z=0.0,
        offset=(0.0, 0.0, 0.0))

    assert porta.ext["trazomob"]["kind"] == "esquadria"
    assert porta.ext["trazomob_esquadria"]["largura_mm"] == 800.0
    assert porta.ext["trazomob_module"]["largura"] == 800.0
    assert porta.ext["trazomob_module"]["profundidade"] == 150.0

    # Qualquer porta de entrada de leitura devolve os mesmos valores.
    for dados in (schema.params_of(porta),
                  schema.module_params(porta),
                  schema.esquadria_params(porta)):
        assert dados["largura"] == 800.0
        assert dados["largura_mm"] == 800.0
        assert dados["altura"] == 2100.0
        assert dados["profundidade"] == 150.0


def test_update_module_data_alcanca_os_dois_espelhos(qapp):
    modulo = Group(Mesh(), name="Modulo")
    schema.set_module_data(modulo, {"tipo": "balcao", "largura": 800})
    schema.update_module_data(modulo, {"_unrot_carcass_span": (1, 2, 3, 4, 5, 6)})

    assert modulo.ext["trazomob"]["_unrot_carcass_span"] == (1, 2, 3, 4, 5, 6)
    assert modulo.ext["trazomob_module"]["_unrot_carcass_span"] == (1, 2, 3, 4, 5, 6)
    assert modulo.ext["trazomob"] is modulo.ext["trazomob_module"]


def test_live_module_data_e_mutavel_e_compartilhado(qapp):
    modulo = Group(Mesh(), name="Modulo")
    schema.set_module_data(modulo, {"tipo": "balcao", "rot_z": 0.0})

    vivo = schema.live_module_data(modulo)
    vivo["rot_z"] = 90.0

    assert modulo.ext["trazomob"]["rot_z"] == 90.0
    assert modulo.ext["trazomob_module"]["rot_z"] == 90.0


def test_set_module_data_nao_compartilha_o_dict_do_chamador(qapp):
    """O chamador continua dono do seu dicionário; o grupo recebe uma cópia."""
    modulo = Group(Mesh(), name="Modulo")
    origem = {"tipo": "balcao", "largura": 800}
    schema.set_module_data(modulo, origem)
    origem["largura"] = 999

    assert modulo.ext["trazomob"]["largura"] == 800


def test_bidirectional_en_pt_aliases():
    """Garante que tanto os nomes em inglês quanto os legados em português sejam acessíveis."""
    from trazomob.domain.schema import module_params

    # Cenário 1: gravado com chaves em português (legado)
    g_pt = Group()
    g_pt.ext = {"trazomob": {"largura": 900, "altura": 720, "num_portas": 2, "tem_fundo": True}}
    p_pt = module_params(g_pt)
    assert p_pt["largura"] == 900
    assert p_pt["width"] == 900
    assert p_pt["altura"] == 720
    assert p_pt["height"] == 720
    assert p_pt["num_portas"] == 2
    assert p_pt["door_count"] == 2
    assert p_pt["tem_fundo"] is True
    assert p_pt["has_back"] is True

    # Cenário 2: gravado com chaves em inglês (moderno)
    g_en = Group()
    g_en.ext = {"trazomob": {"width": 1200, "height": 800, "door_count": 3, "has_back": False}}
    p_en = module_params(g_en)
    assert p_en["width"] == 1200
    assert p_en["largura"] == 1200
    assert p_en["height"] == 800
    assert p_en["altura"] == 800
    assert p_en["door_count"] == 3
    assert p_en["num_portas"] == 3
    assert p_en["has_back"] is False
    assert p_en["tem_fundo"] is False

