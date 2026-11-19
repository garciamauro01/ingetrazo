# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Gerador unificado e canônico de kits de frentes de marcenaria (portas e gavetas).

Padroniza as folgas de esquadro (3mm), descontos de perfis de alumínio e
distribuição geométrica de portas de giro, basculantes e frentes de gaveta.

API pública em milímetros; a conversão para metros acontece apenas na
geometria 3D, que é a unidade do espaço de cena.
"""
from __future__ import annotations

from typing import List, Optional, Tuple
from core.group import Group
from ..builders.chapa_spec import ModuloMaterialContext


class FrentesKitBuilder:
    """Helper canônico para distribuição uniforme e geração de conjuntos de frentes."""

    PADRAO_FOLGA_ENTRE_FRENTES_MM: float = 3.0  # 3mm de folga de marcenaria entre portas/frentes
    PADRAO_FOLGA_PERIMETRO_MM: float = 3.0      # 3mm de recuo de contorno

    @classmethod
    def resolve_folga_mm(
        cls,
        folga_frentes_mm: Optional[float] = None,
        mat_ctx: Optional[ModuloMaterialContext] = None,
    ) -> float:
        """Resolve a folga padrão de frentes/portas em mm (override, contexto ou padrão)."""
        if folga_frentes_mm is not None:
            return max(0.0, float(folga_frentes_mm))
        if mat_ctx is not None:
            return max(0.0, float(mat_ctx.folga_frentes_mm))
        return cls.PADRAO_FOLGA_ENTRE_FRENTES_MM

    @classmethod
    def build_kit_portas_giro(
        cls,
        largura_mm: float,
        altura_mm: float,
        num_portas: int,
        offset: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        esp_frente_mm: float = 15.0,
        material: Optional[str] = None,
        color: Optional[Tuple[float, float, float]] = None,
        door_sides: Optional[List[str]] = None,
        prefixo: str = "Modulo",
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto",
        puxador_pos: str = "padrao",
        desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        is_upper: bool = False,
        gerar_furacao: bool = True,
        recuo_topo_mm: float = 0.0,
        recuo_base_mm: float = 0.0,
        mat_ctx: Optional[ModuloMaterialContext] = None,
        folga_frentes_mm: Optional[float] = None,
    ) -> List[Group]:
        """Gera um conjunto distribuído de portas de giro com folgas padronizadas."""
        from ..builders.cabinet_caixa import CaixaMixin

        n = max(0, int(num_portas))
        if n == 0:
            return []

        folga_m = cls.resolve_folga_mm(folga_frentes_mm, mat_ctx) / 1000.0
        folga_f = folga_m
        folga_p = folga_m

        largura_total_m = largura_mm / 1000.0
        altura_total_m = altura_mm / 1000.0
        esp_frente_m = esp_frente_mm / 1000.0
        recuo_topo_m = recuo_topo_mm / 1000.0
        recuo_base_m = recuo_base_mm / 1000.0

        ox, oy, oz = offset

        # Altura útil da porta descontando folga inferior, superior e recuos
        alt_porta = max(0.05, altura_total_m - recuo_topo_m - recuo_base_m - (2.0 * folga_p))

        # Largura útil de cada porta dividida uniformemente
        larg_disponivel = largura_total_m - (2.0 * folga_p) - (n - 1) * folga_f
        larg_porta = max(0.10, larg_disponivel / n)

        groups: List[Group] = []
        x_atual = ox + folga_p
        z_atual = oz + recuo_base_m + folga_p

        sides = list(door_sides) if door_sides else (
            ["left" if n == 1 else ("left" if i % 2 == 0 else "right") for i in range(n)]
        )

        for i in range(n):
            side = sides[i] if i < len(sides) else "left"
            if n == 1:
                lado_txt = "Esq" if side == "left" else "Dir"
                p_nome = f"{prefixo} - Porta Unica ({lado_txt})"
            elif n == 2:
                lado_txt = "Esq" if side == "left" else "Dir"
                p_nome = f"{prefixo} - Porta {lado_txt}"
            else:
                lado_txt = "Esq" if side == "left" else "Dir"
                p_nome = f"{prefixo} - Porta {i + 1} ({lado_txt})"

            builder_porta = CaixaMixin.build_porta_esquerda if side == "left" else CaixaMixin.build_porta_direita
            door_piece = builder_porta(
                name=p_nome,
                origin=(x_atual, oy - esp_frente_m, z_atual),
                size=(larg_porta, esp_frente_m, alt_porta),
                material=material or (mat_ctx.material_frentes if mat_ctx else "MDF Branco TX 15mm"),
                color=color,
                puxador_tipo=puxador_tipo,
                puxador_cor=puxador_cor,
                puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm,
                perfil_modelo=perfil_modelo,
                door_side=side,
                is_upper=is_upper,
                gerar_furacao=gerar_furacao,
                ctx=mat_ctx,
            )
            groups.append(door_piece)
            x_atual += larg_porta + folga_f

        return groups

    @classmethod
    def build_kit_frentes_gavetas(
        cls,
        largura_mm: float,
        altura_mm: float,
        num_gavetas: int,
        offset: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        esp_frente_mm: float = 15.0,
        material: Optional[str] = None,
        color: Optional[Tuple[float, float, float]] = None,
        prefixo: str = "Modulo",
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto",
        puxador_pos: str = "padrao",
        desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        alturas_frentes_mm: Optional[List[float]] = None,
        mat_ctx: Optional[ModuloMaterialContext] = None,
        folga_frentes_mm: Optional[float] = None,
    ) -> List[Group]:
        """Gera um conjunto vertical de frentes de gaveta com folgas uniformes."""
        from ..builders.cabinet_caixa import CaixaMixin

        n = max(0, int(num_gavetas))
        if n == 0:
            return []

        folga_m = cls.resolve_folga_mm(folga_frentes_mm, mat_ctx) / 1000.0
        folga_f = folga_m
        folga_p = folga_m

        largura_total_m = largura_mm / 1000.0
        altura_total_m = altura_mm / 1000.0
        esp_frente_m = esp_frente_mm / 1000.0
        ox, oy, oz = offset

        larg_frente = max(0.10, largura_total_m - (2.0 * folga_p))
        altura_util = altura_total_m - (2.0 * folga_p) - (n - 1) * folga_f

        if alturas_frentes_mm and len(alturas_frentes_mm) == n:
            alturas = [max(0.05, float(h) / 1000.0) for h in alturas_frentes_mm]
        else:
            alt_gaveta = max(0.05, altura_util / n)
            alturas = [alt_gaveta] * n

        groups: List[Group] = []
        z_atual = oz + folga_p

        for i, h_frente in enumerate(alturas, 1):
            gav_piece = CaixaMixin.build_frente_gaveta(
                name=f"{prefixo} - Frente Gaveta {i}",
                origin=(ox + folga_p, oy - esp_frente_m, z_atual),
                size=(larg_frente, esp_frente_m, h_frente),
                material=material or (mat_ctx.material_frentes if mat_ctx else "MDF Branco TX 15mm"),
                color=color,
                puxador_tipo=puxador_tipo,
                puxador_cor=puxador_cor,
                puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm,
                perfil_modelo=perfil_modelo,
                ctx=mat_ctx,
            )
            groups.append(gav_piece)
            z_atual += h_frente + folga_f

        return groups

# Aliases
FrontsKitBuilder = FrentesKitBuilder
