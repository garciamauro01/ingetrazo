# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes de integridade do manifesto único das esquadrias (Fase 2)."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from trazomob.assets import catalog as manifest_mod
from trazomob.builders.esquadrias import EsquadriaBuilder
from trazomob.domain.catalog import MODULE_CATALOG


def test_manifest_carrega_e_tem_schema_atual():
    assert manifest_mod.ESQUADRIAS_MANIFEST["schema"] == 1
    manifest_mod.validar_manifest()


def test_manifest_tem_contagens_esperadas():
    dados = manifest_mod.ESQUADRIAS_MANIFEST
    assert len(dados["modelos"]) == 34
    assert len(dados["aliases"]) == 7
    assert len(manifest_mod.get_esquadria_files()) == 41
    assert len(manifest_mod.get_novas_portas_folhas()) == 19
    assert len(manifest_mod.get_novas_portas_cinematica()) == 19


def test_catalogo_e_builder_usam_o_manifest():
    catalogo = manifest_mod.get_esquadrias_catalogo()
    assert MODULE_CATALOG["Portas & Janelas"] == catalogo
    assert EsquadriaBuilder._ESQUADRIA_FILES == manifest_mod.get_esquadria_files()
    assert EsquadriaBuilder._NOVAS_PORTAS_FOLHAS == manifest_mod.get_novas_portas_folhas()
    assert (
        EsquadriaBuilder._NOVAS_PORTAS_CINEMATICA
        == manifest_mod.get_novas_portas_cinematica()
    )


def test_ids_sao_unicos_e_nao_vazam_metadados_no_catalogo():
    dados = manifest_mod.ESQUADRIAS_MANIFEST
    ids = [m["id"] for m in dados["modelos"]]
    assert len(ids) == len(set(ids))
    assert not set(ids) & set(dados["aliases"])

    metadados = {"igz_file", "subpasta", "folhas", "cinematica"}
    for item in manifest_mod.get_esquadrias_catalogo():
        assert not metadados & set(item)


def test_todos_os_igz_existem_e_estao_na_subpasta_do_prefixo():
    base = Path(__file__).resolve().parents[1] / "assets" / "components"
    tabela = manifest_mod.get_esquadria_files()
    for item_id, (arquivo, subpasta) in tabela.items():
        assert arquivo.endswith(".igz")
        assert Path(arquivo).name == arquivo
        assert subpasta == ("janelas" if item_id.startswith("janela_") else "portas")
        assert (base / subpasta / arquivo).is_file(), (item_id, arquivo)


def test_num_portas_igual_a_quantidade_de_folhas_quando_ha_mapa():
    for modelo in manifest_mod.ESQUADRIAS_MANIFEST["modelos"]:
        if "folhas" in modelo:
            assert modelo["num_portas"] == len(modelo["folhas"]), modelo["id"]


def test_indices_e_donos_da_cinematica_sao_validos():
    folhas = manifest_mod.get_novas_portas_folhas()
    cine = manifest_mod.get_novas_portas_cinematica()
    for arquivo, papel_por_peca in cine.items():
        quantidade = len(folhas.get(arquivo, ()))
        for indice, (papel, dono) in papel_por_peca.items():
            assert indice >= 0
            assert papel in ("fixo", "movel")
            assert dono >= 0
            if quantidade:
                assert dono < quantidade, (arquivo, indice, dono)


def test_valores_de_regressao_das_folhas_foram_preservados():
    folhas = manifest_mod.get_novas_portas_folhas()
    assert folhas["porta_d1.igz"] == (3,)
    assert folhas["porta_d2.igz"] == (2,)
    assert folhas["porta_ferro_dupla.igz"] == (5, 7)
    assert folhas["porta_amadeirada_ext2.igz"] == (11,)
    assert folhas["porta_22.igz"] == (2,)


def test_aliases_continuam_apontando_aos_mesmos_arquivos():
    aliases = manifest_mod.ESQUADRIAS_MANIFEST["aliases"]
    assert aliases["porta_giro_70"] == {
        "igz_file": "porta_giro.igz", "subpasta": "portas"
    }
    assert aliases["porta_giro_80"] == {
        "igz_file": "porta_giro.igz", "subpasta": "portas"
    }
    assert aliases["porta_giro_90"] == {
        "igz_file": "porta_giro.igz", "subpasta": "portas"
    }
    assert aliases["porta_correr_vidro"] == {
        "igz_file": "porta_correr_vidro_170.igz", "subpasta": "portas"
    }
    assert aliases["porta_correr_vidro_4f"] == {
        "igz_file": "porta_correr_vidro_4f_287.igz", "subpasta": "portas"
    }
    assert aliases["porta_aluminio_90"] == {
        "igz_file": "porta_aluminio.igz", "subpasta": "portas"
    }
    assert aliases["porta_pivotante_vidro_80"] == {
        "igz_file": "porta_pivotante_vidro.igz", "subpasta": "portas"
    }


def test_janela_nunca_resolve_para_pasta_de_portas():
    base = Path(__file__).resolve().parents[1]
    for item_id in (
        "janela_correr_2f_130",
        "janela_correr_4f_190",
        "janela_vertical_50",
        "janela_maximar_70",
        "janela_basculante_sup_170",
        "janela_basculante_inf_170",
        "janela_correr_pj",
    ):
        caminho = EsquadriaBuilder._esquadria_igz_path(base, item_id)
        assert caminho.parent.name == "janelas", (item_id, caminho)
        assert caminho.is_file()


def test_getters_devolvem_copias_que_nao_alteram_o_manifest():
    catalogo = manifest_mod.get_esquadrias_catalogo()
    catalogo[0]["nome"] = "ALTERADO"
    files = manifest_mod.get_esquadria_files()
    files["porta_giro"] = ("outro.igz", "portas")
    folhas = manifest_mod.get_novas_portas_folhas()
    folhas["porta_d1.igz"] = (99,)

    manifest_mod.validar_manifest()
    assert manifest_mod.get_esquadrias_catalogo()[0]["nome"] != "ALTERADO"
    assert manifest_mod.get_esquadria_files()["porta_giro"] == ("porta_giro.igz", "portas")
    assert manifest_mod.get_novas_portas_folhas()["porta_d1.igz"] == (3,)


@pytest.mark.parametrize(
    "mutacao",
    [
        lambda d: d.update(schema=2),
        lambda d: d["modelos"][0].update(id=d["modelos"][1]["id"]),
        lambda d: d["modelos"][0].update(subpasta="janelas"),
        lambda d: d["modelos"][0].update(igz_file="inexistente.igz"),
        lambda d: d["modelos"][0].update(folhas=[0, 1]),
        lambda d: d["modelos"][0].update(cinematica={"x": ("movel", 0)}),
        lambda d: d["aliases"].update({"porta_giro": {"igz_file": "x.igz", "subpasta": "portas"}}),
    ],
)
def test_validacao_rejeita_manifestos_invalidos(mutacao):
    dados = copy.deepcopy(manifest_mod.ESQUADRIAS_MANIFEST)
    mutacao(dados)
    with pytest.raises(ValueError):
        manifest_mod._validar_manifest(dados)
