# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes do contrato de snap magnetico por face (snap_parede)."""

from __future__ import annotations

import math

import pytest

from trazomob.builders.cabinet import CabinetBuilder
from trazomob.domain.schema import module_params
from trazomob.domain.snap_contract import (
    DEFAULT_SNAP_PAREDE,
    SNAP_PAREDE_INFERIOR,
    SNAP_PAREDE_NENHUM,
    SNAP_PAREDE_OPCOES,
    SNAP_PAREDE_SUPERIOR,
    SNAP_PAREDE_VALORES,
    get_module_snap_parede,
    normalize_snap_parede,
    should_show_snap_parede,
    snap_face_target_rotation_deg,
    snap_face_tilt_deg,
)


def _rot_local(x: float, y: float, rot_deg: float) -> tuple[float, float]:
    """Gira um vetor local pelo rot_z do modulo (mesmo sentido do construtor)."""
    rad = math.radians(rot_deg)
    return (
        x * math.cos(rad) - y * math.sin(rad),
        x * math.sin(rad) + y * math.cos(rad),
    )


def _build_tampo(**extra):
    params = {
        "tipo": "peca_tampo_engrossado",
        "largura": 1200,
        "altura": 36,
        "profundidade": 600,
        "esp_chapa": 18,
        "qtd_engrosso": 1,
        "larg_engrosso": 70,
        "tipo_engrosso": "3_lados",
        "material": "MDF Carvalho",
    }
    params.update(extra)
    return CabinetBuilder.build_module_group(params)


def test_opcoes_de_snap_tem_valores_unicos():
    valores = [valor for valor, _rotulo in SNAP_PAREDE_OPCOES]
    assert len(valores) == len(set(valores))
    assert valores == list(SNAP_PAREDE_VALORES)
    assert "auto" in valores
    assert SNAP_PAREDE_SUPERIOR in valores
    assert SNAP_PAREDE_INFERIOR in valores
    assert SNAP_PAREDE_NENHUM in valores


def test_normalizacao_aceita_aliases_e_invalidos():
    assert normalize_snap_parede(None) == DEFAULT_SNAP_PAREDE
    assert normalize_snap_parede("") == DEFAULT_SNAP_PAREDE
    assert normalize_snap_parede("FRENTE") == "frente"
    assert normalize_snap_parede("fundo") == "traseira"
    assert normalize_snap_parede("right") == "direita"
    assert normalize_snap_parede("topo") == "superior"
    assert normalize_snap_parede("base") == "inferior"
    assert normalize_snap_parede("none") == "nenhum"
    assert normalize_snap_parede("desconhecido") == DEFAULT_SNAP_PAREDE


def test_visibilidade_do_controle_apenas_para_tampo():
    assert should_show_snap_parede("peca_tampo_engrossado") is True
    assert should_show_snap_parede("tampo_engrossado") is True
    assert should_show_snap_parede("balcao") is False
    assert should_show_snap_parede("peca_prateleiras_avulsas") is False


def test_rotacao_coloca_a_face_escolhida_contra_a_parede():
    # Parede ao sul: normal apontando para dentro do ambiente = +Y.
    nx, ny = 0.0, 1.0

    # Face traseira (local +Y) deve apontar para -Y (contra a parede).
    rot_tras = snap_face_target_rotation_deg(nx, ny, "traseira")
    assert rot_tras == 180.0
    assert _rot_local(0.0, 1.0, rot_tras) == pytest.approx((0.0, -1.0), abs=1e-12)

    # Face frontal (local -Y) idem.
    rot_frente = snap_face_target_rotation_deg(nx, ny, "frente")
    assert rot_frente == 0.0
    assert _rot_local(0.0, -1.0, rot_frente) == pytest.approx((0.0, -1.0), abs=1e-12)

    # Lateral esquerda (local -X).
    rot_esq = snap_face_target_rotation_deg(nx, ny, "esquerda")
    assert rot_esq == 90.0
    assert _rot_local(-1.0, 0.0, rot_esq) == pytest.approx((0.0, -1.0), abs=1e-12)

    # Lateral direita (local +X).
    rot_dir = snap_face_target_rotation_deg(nx, ny, "direita")
    assert rot_dir == 270.0
    assert _rot_local(1.0, 0.0, rot_dir) == pytest.approx((0.0, -1.0), abs=1e-12)


def test_auto_mantem_o_comportamento_do_fundo_na_parede():
    assert snap_face_target_rotation_deg(0.0, 1.0, "auto") == 180.0
    assert snap_face_target_rotation_deg(1.0, 0.0, "auto") == 90.0


def test_sem_snap_nao_gera_rotacao():
    assert snap_face_target_rotation_deg(0.0, 1.0, "nenhum") == 0.0


def test_faces_horizontais_tombam_para_encostar_na_parede():
    # superior: o topo local +Z passa a apontar para a traseira +Y.
    assert snap_face_tilt_deg("superior") == -90.0
    assert snap_face_tilt_deg("inferior") == 90.0
    assert snap_face_tilt_deg("auto") == 0.0
    assert snap_face_tilt_deg("nenhum") == 0.0

    # Depois do tombamento a face escolhida se comporta como a traseira.
    assert snap_face_target_rotation_deg(0.0, 1.0, "superior") == 180.0
    assert snap_face_target_rotation_deg(0.0, 1.0, "inferior") == 180.0
    assert snap_face_target_rotation_deg(1.0, 0.0, "superior") == 90.0
    assert snap_face_target_rotation_deg(1.0, 0.0, "inferior") == 90.0


def test_face_tombada_aponta_contra_a_parede():
    # Parede ao sul, normal para dentro do ambiente = +Y.
    nx, ny = 0.0, 1.0

    # Rotacao em X (sentido do Qt: +angulo = regra da mao direita).
    def _tilt(x: float, y: float, z: float, deg: float) -> tuple[float, float, float]:
        rad = math.radians(deg)
        return (
            x,
            y * math.cos(rad) - z * math.sin(rad),
            y * math.sin(rad) + z * math.cos(rad),
        )

    for face, normal_local in (("superior", (0.0, 0.0, 1.0)), ("inferior", (0.0, 0.0, -1.0))):
        nx_l, ny_l, nz_l = _tilt(*normal_local, snap_face_tilt_deg(face))
        rx, ry = _rot_local(nx_l, ny_l, snap_face_target_rotation_deg(nx, ny, face))
        assert math.isclose(rx, 0.0, abs_tol=1e-6)
        assert math.isclose(ry, -1.0, abs_tol=1e-6)


def test_tampo_persiste_snap_parede_nos_metadados():
    group = _build_tampo(snap_parede="direita")

    assert module_params(group)["snap_parede"] == "direita"
    assert group.ext["trazomob_module"]["snap_parede"] == "direita"
    assert get_module_snap_parede(group) == "direita"


def test_tampo_sem_parametro_usa_auto():
    group = _build_tampo()
    assert get_module_snap_parede(group) == DEFAULT_SNAP_PAREDE


def test_tampo_persiste_face_horizontal():
    group = _build_tampo(snap_parede="inferior")
    assert module_params(group)["snap_parede"] == "inferior"
    assert get_module_snap_parede(group) == "inferior"
