# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Fachada pública das esquadrias do Trazomob.

A implementação foi dividida em três módulos, todos com responsabilidade única:

* :mod:`esquadrias_parametric` — portas/janelas geradas por parâmetros;
* :mod:`esquadrias_native` — modelos ``.igz`` reais e sua cinemática;
* :mod:`esquadrias_common` — dados compartilhados e resolução de caminhos.

Os nomes públicos de ``EsquadriaBuilder`` permanecem idênticos.
"""
from __future__ import annotations

from pathlib import Path

from core.group import Group

from . import esquadrias_native as _native
from . import esquadrias_parametric as _parametric
from .esquadrias_common import (
    CORES,
    ESQUADRIA_FILES,
    NOVAS_PORTAS_CINEMATICA,
    NOVAS_PORTAS_FOLHAS,
    PORTA_PROTO_CACHE,
)


class EsquadriaBuilder:
    """Fábrica de portas e janelas paramétricas completas (fachada)."""

    CORES = CORES
    _ESQUADRIA_FILES = ESQUADRIA_FILES
    _NOVAS_PORTAS_FOLHAS = NOVAS_PORTAS_FOLHAS
    _NOVAS_PORTAS_CINEMATICA = NOVAS_PORTAS_CINEMATICA
    _PORTA_PROTO_CACHE = PORTA_PROTO_CACHE

    @classmethod
    def build_porta_giro(cls, largura_mm: float=800.0, altura_mm: float=2100.0, esp_parede_mm: float=150.0, larg_alisar_mm: float=70.0, esp_folha_mm: float=35.0, esp_marco_mm: float=30.0, folga_mm: float=3.0, lado_abertura: str='right', acabamento: str='madeira_branca', offset: tuple[float, float, float]=(0.0, 0.0, 0.0), rot_z: float=0.0):
        return _parametric.build_porta_giro(largura_mm, altura_mm, esp_parede_mm, larg_alisar_mm, esp_folha_mm, esp_marco_mm, folga_mm, lado_abertura, acabamento, offset, rot_z)

    @classmethod
    def build_janela_correr(cls, largura_mm: float=1200.0, altura_mm: float=1000.0, esp_parede_mm: float=150.0, peitoril_mm: float=1100.0, acabamento_aluminio: str='aluminio_preto', tipo_vidro: str='vidro_incolor', offset: tuple[float, float, float]=(0.0, 0.0, 0.0), rot_z: float=0.0):
        return _parametric.build_janela_correr(largura_mm, altura_mm, esp_parede_mm, peitoril_mm, acabamento_aluminio, tipo_vidro, offset, rot_z)

    @classmethod
    def build_janela_correr_4folhas(cls, largura_mm: float=1900.0, altura_mm: float=1200.0, esp_parede_mm: float=150.0, peitoril_mm: float=1000.0, acabamento_aluminio: str='aluminio_branco', tipo_vidro: str='vidro_incolor', offset: tuple[float, float, float]=(0.0, 0.0, 0.0), rot_z: float=0.0):
        return _parametric.build_janela_correr_4folhas(largura_mm, altura_mm, esp_parede_mm, peitoril_mm, acabamento_aluminio, tipo_vidro, offset, rot_z)

    @classmethod
    def build_porta_correr_vidro(cls, largura_mm: float=1600.0, altura_mm: float=2100.0, esp_parede_mm: float=150.0, acabamento_aluminio: str='aluminio_preto', tipo_vidro: str='vidro_incolor', offset: tuple[float, float, float]=(0.0, 0.0, 0.0), rot_z: float=0.0):
        return _parametric.build_porta_correr_vidro(largura_mm, altura_mm, esp_parede_mm, acabamento_aluminio, tipo_vidro, offset, rot_z)

    @classmethod
    def build_porta_pivotante(cls, largura_mm: float=1000.0, altura_mm: float=2150.0, esp_parede_mm: float=150.0, larg_alisar_mm: float=80.0, esp_folha_mm: float=45.0, dist_pivo_mm: float=120.0, acabamento: str='madeira_freijo', offset: tuple[float, float, float]=(0.0, 0.0, 0.0), rot_z: float=0.0):
        return _parametric.build_porta_pivotante(largura_mm, altura_mm, esp_parede_mm, larg_alisar_mm, esp_folha_mm, dist_pivo_mm, acabamento, offset, rot_z)

    @classmethod
    def build_janela_maximar(cls, largura_mm: float=600.0, altura_mm: float=600.0, esp_parede_mm: float=150.0, peitoril_mm: float=1600.0, acabamento_aluminio: str='aluminio_preto', tipo_vidro: str='vidro_incolor', offset: tuple[float, float, float]=(0.0, 0.0, 0.0), rot_z: float=0.0):
        return _parametric.build_janela_maximar(largura_mm, altura_mm, esp_parede_mm, peitoril_mm, acabamento_aluminio, tipo_vidro, offset, rot_z)

    @classmethod
    def build_janela_vertical_bandeira(cls, largura_mm: float=500.0, altura_mm: float=1200.0, esp_parede_mm: float=150.0, peitoril_mm: float=900.0, acabamento_aluminio: str='aluminio_branco', tipo_vidro: str='vidro_incolor', offset: tuple[float, float, float]=(0.0, 0.0, 0.0), rot_z: float=0.0):
        return _parametric.build_janela_vertical_bandeira(largura_mm, altura_mm, esp_parede_mm, peitoril_mm, acabamento_aluminio, tipo_vidro, offset, rot_z)

    @classmethod
    def _build_folha_janela(cls, pieces: list[Group], prefix: str, x: float, y: float, z: float, w: float, prof: float, h: float, e_quadro: float, cor_alum: tuple[float, float, float], cor_vidro: tuple[float, float, float]):
        return _parametric._build_folha_janela(pieces, prefix, x, y, z, w, prof, h, e_quadro, cor_alum, cor_vidro)

    @classmethod
    def _assemble_esquadria_group(cls, name: str, tipo: str, pieces: list[Group], largura_mm: float, altura_mm: float, esp_parede_mm: float, peitoril_mm: float, offset: tuple[float, float, float], rot_z: float, lado_abertura: str='direita', sentido_abertura: str='interno'):
        return _parametric._assemble_esquadria_group(name, tipo, pieces, largura_mm, altura_mm, esp_parede_mm, peitoril_mm, offset, rot_z, lado_abertura, sentido_abertura)

    @classmethod
    def _esquadria_igz_path(cls, base_dir, item_id: str):
        return _native.resolve_igz_path(base_dir, item_id)

    @classmethod
    def get_esquadria_local_mid_y(cls, item_id: str, esp_parede_mm: float=150.0):
        return _native.get_local_mid_y(item_id, esp_parede_mm)

    @classmethod
    def _get_porta_prototype(cls, igz_path):
        return _native.get_porta_prototype(igz_path)

    @classmethod
    def load_esquadria_igz(cls, item_id: str, largura_mm: float, altura_mm: float, esp_parede_mm: float, peitoril_mm: float=0.0, offset: tuple[float, float, float]=(0.0, 0.0, 0.0), rot_z: float=0.0, lado_abertura: str='direita', sentido_abertura: str='interno'):
        return _native.load_esquadria_igz(item_id, largura_mm, altura_mm, esp_parede_mm, peitoril_mm, offset, rot_z, lado_abertura, sentido_abertura)

    @classmethod
    def _load_porta_original_usuario(cls, igz_path: Path, item_id: str, largura_mm: float, altura_mm: float, esp_parede_mm: float, peitoril_mm: float=0.0, offset: tuple[float, float, float]=(0.0, 0.0, 0.0), rot_z: float=0.0, lado_abertura: str='direita', sentido_abertura: str='interno'):
        return _native.load_porta_original_usuario(igz_path, item_id, largura_mm, altura_mm, esp_parede_mm, peitoril_mm, offset, rot_z, lado_abertura, sentido_abertura)

