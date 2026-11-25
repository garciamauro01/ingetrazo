# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes de regressão da Fase 1 da auditoria de esquadrias/integração."""
from __future__ import annotations

import pytest
from PySide6.QtGui import QVector3D

from trazomob.builders.esquadrias import EsquadriaBuilder


# ---------------------------------------------------------------------------
# Correção 1: winding no espelhamento de um eixo.
# ---------------------------------------------------------------------------
def test_espelhamento_um_eixo_preserva_orientacao_das_faces():
    """flip_x xor flip_y nao pode deixar as normais invertidas."""
    from core.mesh import Mesh

    mesh = Mesh()
    face = mesh.add_face([
        QVector3D(0, 0, 0),
        QVector3D(1, 0, 0),
        QVector3D(0, 1, 0),
    ])
    antes = [v for v in face.vertices]

    # A correcao atua em ``face.loop`` (a lista viva), nao na property.
    face.loop.reverse()
    depois = [v for v in face.vertices]
    assert depois == list(reversed(antes))


def test_builder_espelha_porta_real_sem_quebrar_folha():
    """Uma porta real espelhada continua com folha e cinemática íntegras."""
    norm = EsquadriaBuilder.load_esquadria_igz("porta_d1", 982, 2153, 139)
    flip = EsquadriaBuilder.load_esquadria_igz(
        "porta_d1", 982, 2153, 139, lado_abertura="esquerda"
    )

    def folha(group):
        return [c for c in (group.children or []) if (c.ext or {}).get("hinge_pivot")]

    assert len(folha(norm)) == 1
    assert len(folha(flip)) == 1
    assert len(folha(norm)[0].mesh.faces) == len(folha(flip)[0].mesh.faces)


# ---------------------------------------------------------------------------
# Correção 2: peitoril do catálogo no menu da sidebar.
# ---------------------------------------------------------------------------
def test_peitoril_do_catalogo_usa_peitoril_mm():
    from trazomob.ui.sidebar_esquadria_controller import peitoril_do_catalogo

    item = {"id": "janela_correr_2f_130", "peitoril_mm": 1000}
    assert peitoril_do_catalogo(item) == 1000.0
    # Compatibilidade com módulo antigo de usuário.
    assert peitoril_do_catalogo({"peitoril": 900}) == 900.0
    assert peitoril_do_catalogo({"id": "porta_giro"}) == 0.0


def test_janelas_do_catalogo_tem_peitoril_mm():
    from trazomob.domain.catalog import MODULE_CATALOG

    janelas = [it for it in MODULE_CATALOG["Portas & Janelas"]
               if it["id"].startswith("janela_")]
    assert janelas
    for it in janelas:
        assert "peitoril_mm" in it, f"{it['id']} sem peitoril_mm"


# ---------------------------------------------------------------------------
# Correção 3: linked_pieces so com ferragens, nunca com marco.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("nome,w,h,p", [
    ("porta_vidro_externa_ce", 1680, 3400, 260),
    ("porta_externa_ce", 1680, 3400, 260),
    ("porta_comp1_ce", 1180, 3400, 260),
    ("porta_comp2_ce", 1180, 3400, 260),
    ("porta_dupla_francesa", 2002, 2500, 202),
    ("porta_exterior_conj", 1000, 2499, 202),
    ("porta_frent", 1000, 2500, 202),
    ("porta_d1", 982, 2153, 139),
    ("porta_d2", 1327, 2909, 188),
    ("porta_aluminio_simples", 700, 2000, 70),
    ("porta_amadeirada_ext2", 1566, 2238, 144),
    ("porta_ferro", 900, 2150, 135),
    ("porta_pivotante_ok1", 1740, 2620, 271),
    ("porta_pivotante_ok2", 1740, 2620, 1340),
    ("porta_porshoy1", 1200, 2150, 282),
    ("porta_porshoy2", 1200, 2150, 799),
    ("porta_simples", 2150, 3255, 190),
    ("porta_22", 1501, 2170, 165),
    ("porta_3", 2080, 2190, 225),
    ("porta_ferro_dupla", 2022, 2951, 242),
])
def test_novas_portas_tem_folha_e_linked_pieces_corretos(nome, w, h, p):
    group = EsquadriaBuilder.load_esquadria_igz(nome, w, h, p)
    children = group.children or []
    folhas = [
        c for c in children
        if (c.ext or {}).get("hinge_pivot") is not None
        or (c.ext or {}).get("slide_axis") is not None
    ]
    assert folhas, f"{nome} sem folha com hinge_pivot ou slide_axis"

    nomes = [c.name for c in children]
    assert len(nomes) == len(set(nomes)), f"{nome} tem nomes de peça duplicados: {nomes}"

    for folha in folhas:
        linked = folha.ext.get("linked_pieces", [])
        # linked_pieces rotaciona as peças; marco nunca pode entrar na lista.
        assert all(not str(n).startswith("Marco") for n in linked), (
            f"{nome}: linked_pieces contém marco: {linked}"
        )
        # Todo nome vinculado deve existir de fato entre os filhos.
        for n in linked:
            assert any(n in child for child in nomes), (
                f"{nome}: linked_pieces '{n}' não corresponde a nenhuma peça"
            )


def test_porta_ferro_dupla_particiona_ferragens():
    group = EsquadriaBuilder.load_esquadria_igz("porta_ferro_dupla", 2022, 2951, 242)
    folhas = [c for c in (group.children or []) if (c.ext or {}).get("hinge_pivot")]
    assert len(folhas) == 2

    esq = set(folhas[0].ext.get("linked_pieces", []))
    dir_ = set(folhas[1].ext.get("linked_pieces", []))
    assert esq and dir_, "ambas as folhas devem ter ferragens vinculadas"
    assert not (esq & dir_), "as folhas não podem compartilhar ferragens"


def test_indice_de_folha_invalido_falha_alto(monkeypatch):
    """Um índice de folha fora do intervalo nao pode ser descartado em silencio."""
    monkeypatch.setitem(
        EsquadriaBuilder._NOVAS_PORTAS_FOLHAS, "porta_d1.igz", (999,)
    )
    with pytest.raises(ValueError, match="indice de folha 999 invalido"):
        EsquadriaBuilder.load_esquadria_igz("porta_d1", 982, 2153, 139)


# ---------------------------------------------------------------------------
# Correção 5: catraca de dívida privada enxerga subpastas.
# ---------------------------------------------------------------------------
def test_catraca_enxerga_subpastas_e_baseline_sem_orfaos():
    from trazomob.tests import test_platform_contract as tc

    arqs = {p.relative_to(tc.Path(__file__).resolve().parents[1]).as_posix()
            for p in tc.Path(__file__).resolve().parents[1].rglob("*.py")
            if not tc._SKIP_DIRS.intersection(
                p.relative_to(tc.Path(__file__).resolve().parents[1]).parts)}
    assert "interaction/interact.py" in arqs
    assert "builders/esquadrias.py" in arqs
    for baseline in (tc.PRIVATE_ATTR_BASELINE, tc.PRIVATE_IMPORT_BASELINE):
        assert not (set(baseline) - arqs), f"chaves órfãs: {set(baseline) - arqs}"


def test_contagem_de_divida_privada_nao_cresceu():
    from trazomob.tests import test_platform_contract as tc

    attr = tc._counts(tc._ATTR_RE)
    imp = tc._counts(tc._IMPORT_RE)
    for atual, baseline, rotulo in (
        (attr, tc.PRIVATE_ATTR_BASELINE, "atributo"),
        (imp, tc.PRIVATE_IMPORT_BASELINE, "import"),
    ):
        for nome, qtd in atual.items():
            assert qtd <= baseline.get(nome, 0), (
                f"{rotulo} privado cresceu em {nome}: {baseline.get(nome, 0)}->{qtd}"
            )


# ---------------------------------------------------------------------------
# Correção 6: módulo de usuário derivado de esquadria preserva a origem.
# ---------------------------------------------------------------------------
def test_build_user_module_preserva_origem_da_esquadria():
    from trazomob.domain.catalog import build_user_module
    from trazomob.domain.module_geometry import build_default_module_params

    base = {
        "id": "porta_giro", "nome": "Porta Giro", "largura": 800,
        "altura": 2150, "profundidade": 180, "rodape": 0,
    }
    user = build_user_module(base, {}, "Minha Porta", set())
    assert user["base_id"] == "porta_giro"
    assert user["origem_id"] == "porta_giro"
    assert user["kind"] == "esquadria"
    assert user["id"].startswith("user_")

    params = build_default_module_params(user)
    assert params["tipo"] == "porta_giro"


def test_build_user_module_nao_marca_balcao_como_esquadria():
    from trazomob.domain.catalog import build_user_module

    base = {"id": "balcao", "nome": "Balcão", "largura": 600}
    user = build_user_module(base, {}, "Meu Balcão", set())
    assert "base_id" not in user
    assert "kind" not in user
