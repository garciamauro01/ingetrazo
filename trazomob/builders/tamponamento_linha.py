# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Construtor de tamponamentos contínuos de linha e envoltórios para móveis modulados.

Permite gerar:
- Tamponamento Simples (apenas lateral ou apenas topo);
- Envoltório em L (topo + 1 lateral descendo até o piso/rodapé);
- Envoltório em U / Gola Contínua (lateral esquerda + topo contínuo unificado + lateral direita).

O tamponamento pode ser aplicado sobre um único módulo ou cobrir uma sequência
contínua de balcões ou armários adjacentes na cena.
"""
from __future__ import annotations

from typing import Any
from PySide6.QtGui import QVector3D
from core.group import Group

from .chapa_builder import build_chapa
from .chapa_spec import ChapaSpec, ModuloMaterialContext, PapelChapa


class TamponamentoLinhaBuilder:
    """Construtor paramétrico de tamponamentos unificados e contínuos."""

    @classmethod
    def build_tamponamento_linha(
        cls,
        largura_mm: float,
        altura_mm: float,
        prof_mm: float,
        esp_mm: float = 18.0,
        esp_lateral_mm: float | None = None,
        tipo_envoltorio: str = "u_completo",  # "u_completo", "topo", "lateral_esq", "lateral_dir", "l_esq", "l_dir"
        material: str = "MDF Carvalho",
        material_fita: str | None = None,
        recuo_frontal_mm: float = 0.0,
        sobra_frontal_mm: float = 20.0,  # Avanço frontal em relação à caixa para cobrir as portas
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> list[Group]:
        """Gera as chapas engrossadas de tamponamento para envolver uma linha de módulos.

        Dimensões em mm na entrada, geradas em metros no espaço 3D.
        """
        esp_t = esp_mm / 1000.0
        esp_lat = (esp_lateral_mm or esp_mm) / 1000.0

        L = max(0.05, largura_mm / 1000.0)
        A = max(0.05, altura_mm / 1000.0)
        P = max(0.05, prof_mm / 1000.0)

        sobra_f = sobra_frontal_mm / 1000.0
        recuo_f = recuo_frontal_mm / 1000.0
        prof_tamp = P + sobra_f - recuo_f

        ox, oy, oz = offset
        oy_tamp = oy - sobra_f  # Projeta para a frente para alinhar com as portas

        if mat_ctx is None:
            mat_ctx = ModuloMaterialContext(
                material_caixa=material,
                material_fita_caixa=material_fita or material,
                fita_caixa_modo="4L",
            )

        groups: list[Group] = []
        tipo = str(tipo_envoltorio or "u_completo").strip().lower()

        has_topo = tipo in ("topo", "u_completo", "l_esq", "l_dir")
        has_esq = tipo in ("lateral_esq", "u_completo", "l_esq")
        has_dir = tipo in ("lateral_dir", "u_completo", "l_dir")

        # 1. Lateral Esquerda
        if has_esq:
            # A lateral esquerda posiciona-se em ox - esp_lat
            # Altura cobre até o topo da caixa + espessura do topo (se houver topo sobreposto)
            alt_lat_esq = A + (esp_t if has_topo else 0.0)
            spec_esq = ChapaSpec.resolve(
                nome="Tamponamento Lateral Esq",
                papel=PapelChapa.PECA_AVULSA,
                ctx=mat_ctx,
                material_override=material,
                fita_override=(True, True, True, True),
            )
            g_esq = build_chapa(
                spec_esq,
                origin=(ox - esp_lat, oy_tamp, oz),
                size=(esp_lat, prof_tamp, alt_lat_esq),
            )
            groups.append(g_esq)

        # 2. Lateral Direita
        if has_dir:
            # A lateral direita posiciona-se em ox + L
            alt_lat_dir = A + (esp_t if has_topo else 0.0)
            spec_dir = ChapaSpec.resolve(
                nome="Tamponamento Lateral Dir",
                papel=PapelChapa.PECA_AVULSA,
                ctx=mat_ctx,
                material_override=material,
                fita_override=(True, True, True, True),
            )
            g_dir = build_chapa(
                spec_dir,
                origin=(ox + L, oy_tamp, oz),
                size=(esp_lat, prof_tamp, alt_lat_dir),
            )
            groups.append(g_dir)

        # 3. Topo Contínuo
        if has_topo:
            # O tampo cobre a largura dos módulos.
            # No padrão marcenaria sobreposta (L ou U), o topo cobre os módulos
            # entre as laterais externas ou sobrepõe a caixa:
            larg_topo = L
            x_topo = ox
            spec_topo = ChapaSpec.resolve(
                nome="Tamponamento Tampo Superior",
                papel=PapelChapa.PECA_AVULSA,
                ctx=mat_ctx,
                material_override=material,
                fita_override=(True, True, True, True),
            )
            g_topo = build_chapa(
                spec_topo,
                origin=(x_topo, oy_tamp, oz + A),
                size=(larg_topo, prof_tamp, esp_t),
            )
            groups.append(g_topo)

        return groups

