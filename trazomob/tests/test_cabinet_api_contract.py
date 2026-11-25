# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Contrato público mínimo de `trazomob.builders.cabinet`.

A refatoração do monólito em mixins não deve alterar a superfície usada pelo
plugin, pelo registry e pelos módulos/testes importadores.
"""
from __future__ import annotations

import trazomob as plugin
from trazomob.builders import cabinet

EXPECTED_MEMBERS = [
    "build_aereo",
    "build_aereo_basculante",
    "build_aereo_basculante_duplo",
    "build_aereo_microondas",
    "build_armario_3portas",
    "build_armario_divisoria",
    "build_armario_maleiro_tamponado",
    "build_armario_prateleiras",
    "build_balcao",
    "build_balcao_forno",
    "build_balcao_misto",
    "build_balcao_pia",
    "build_bancada_canto_l",
    "build_bancada_ilha",
    "build_bancada_pia",
    "build_bancada_reta",
    "build_beliche",
    "build_bicama",
    "build_caixa_gaveta",
    "build_caixa_geladeira",
    "build_caixa_inferior",
    "build_caixa_modular",
    "build_cama_bau",
    "build_cama_cabeceira",
    "build_cama_colmeia",
    "build_cama_gaveteiros",
    "build_canto_l",
    "build_canto_reto",
    "build_fundo_board",
    "build_gabinete_banheiro",
    "build_gaveteiro",
    "build_janela_correr",
    "build_janela_correr_4folhas",
    "build_janela_maximar",
    "build_janela_vertical_bandeira",
    "build_module_group",
    "build_nicho",
    "build_peca_avulsa",
    "build_porta_correr_vidro",
    "build_porta_giro",
    "build_porta_pivotante",
    "build_porta_tempero",
    "build_prateleiras_avulsas",
    "build_rack_nicho_gaveta",
    "build_rodape_fechado",
    "build_roupeiro_cabideiro",
    "build_roupeiro_portas_correr",
    "build_tamponamento_linha",
    "build_tampo_engrossado",
    "build_torre_quente",
    "get_esquadria_local_mid_y",
    "get_material_color",
    "load_esquadria_igz",
    "rotate_module",
    "scale_module",
]


def test_cabinet_module_exports_are_the_public_plugin_exports():
    assert plugin.CabinetBuilder is cabinet.CabinetBuilder
    assert plugin.RotateTrazoMobModuleCommand is cabinet.RotateTrazoMobModuleCommand
    assert plugin.create_board_group is cabinet.create_board_group
    assert plugin._make_board_mesh is cabinet._make_board_mesh


def test_cabinet_expected_members_are_callable():
    for name in EXPECTED_MEMBERS:
        assert callable(getattr(cabinet.CabinetBuilder, name, None)), name


def test_cabinet_reexports_mesh_helpers():
    assert callable(cabinet.create_board_group)
    assert callable(cabinet._make_board_mesh)
