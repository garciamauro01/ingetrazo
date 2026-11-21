# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Fase 4: os contratos compartilhados têm uma única implementação."""
from __future__ import annotations

import pytest
from PySide6.QtGui import QVector3D

from core.group import Group
from core.mesh import Mesh, Vertex

from trazomob.builders import esquadrias_common
from trazomob.domain import module_geometry, module_utils
from trazomob.interaction.magnetic_drag_snap import is_esquadria_group


def test_reexports_apontam_para_a_fonte_unica():
    assert module_utils.is_esquadria is module_geometry.is_esquadria
    assert module_utils.shift_module_geometry is module_geometry.shift_module_geometry
    assert module_utils.resolve_igz_path is esquadrias_common.resolve_igz_path
    assert module_utils.is_esquadria is esquadrias_common.is_esquadria


def test_classificacao_por_id_do_modelo():
    assert module_utils.is_esquadria("porta_d1")
    assert module_utils.is_esquadria("janela_correr_pj")
    assert not module_utils.is_esquadria("armario_alto")
    assert not module_utils.is_esquadria(None)


def test_classificacao_por_grupo():
    por_kind = Group()
    por_kind.ext = {"trazomob": {"kind": "esquadria"}}
    assert module_utils.is_esquadria(por_kind)
    assert is_esquadria_group(por_kind)

    por_tipo = Group()
    por_tipo.ext = {"trazomob_module": {"tipo": "porta_giro"}}
    assert module_utils.is_esquadria(por_tipo)

    por_layer = Group()
    por_layer.layer = "ESQUADRIAS"
    assert module_utils.is_esquadria(por_layer)

    comum = Group()
    comum.ext = {"trazomob": {"kind": "module"}}
    assert not module_utils.is_esquadria(comum)
    assert not is_esquadria_group(None)


def test_resolve_igz_respeita_a_subpasta(tmp_path):
    componentes = tmp_path / "assets" / "components"
    porta = componentes / "portas" / "porta_d1.igz"
    janela = componentes / "janelas" / "janela_correr.igz"
    porta.parent.mkdir(parents=True)
    janela.parent.mkdir(parents=True)
    porta.write_bytes(b"")
    janela.write_bytes(b"")

    assert module_utils.resolve_igz_path(tmp_path, "porta_d1") == porta
    assert module_utils.resolve_igz_path(tmp_path, "janela_correr") == janela


def test_resolve_igz_sem_arquivo_devolve_caminho_canonico(tmp_path):
    caminho = module_utils.resolve_igz_path(tmp_path, "janela_inexistente")
    assert caminho.parent.name == "janelas"
    assert caminho.name == "janela_inexistente.igz"
    assert not caminho.exists()


def test_shift_module_geometry_translada_malha_e_cinematica():
    filha = Group(name="Folha")
    filha.mesh = Mesh()
    filha.mesh.vertices = [Vertex(QVector3D(1.0, 2.0, 3.0))]
    filha.ext = {
        "orig_vertices": [QVector3D(1.0, 2.0, 3.0)],
        "hinge_pivot": QVector3D(0.5, 0.0, 1.0),
        "trazomob": {
            "rot_origin": QVector3D(1.0, 2.0, 3.0),
            "hinge_pivot": [0.5, 0.0, 1.0],
        },
    }
    modulo = Group(name="Modulo")
    modulo.children = [filha]

    module_utils.shift_module_geometry(modulo, QVector3D(0.1, 0.2, 0.3))

    assert filha.mesh.vertices[0].position == QVector3D(1.1, 2.2, 3.3)
    assert filha.ext["orig_vertices"] == [QVector3D(1.1, 2.2, 3.3)]
    assert filha.ext["hinge_pivot"] == QVector3D(0.6, 0.2, 1.3)
    assert filha.ext["trazomob"]["rot_origin"] == QVector3D(1.1, 2.2, 3.3)
    pivot = filha.ext["trazomob"]["hinge_pivot"]
    assert pivot == [pytest.approx(0.6), pytest.approx(0.2), pytest.approx(1.3)]
