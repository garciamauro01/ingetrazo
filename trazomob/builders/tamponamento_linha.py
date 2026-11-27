# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Continuous line cover panel and wrap builder for modular furniture.

Generates:
- Simple Cover Panel (side only or top only);
- L-Shaped Wrap (top + 1 side extending down to the floor/toe kick);
- U-Shaped Wrap / Continuous Gola (left side + unified continuous top + right side).

Cover paneling can be applied over a single module or span a continuous
sequence of adjacent base cabinets or cabinets in the scene.
"""
from __future__ import annotations

from core.group import Group

from .chapa_builder import build_chapa
from .chapa_spec import ChapaSpec, ModuloMaterialContext, PapelChapa


class TamponamentoLinhaBuilder:
    """Parametric builder for unified, continuous cover panels."""

    @classmethod
    def build_tamponamento_linha(
        cls,
        largura_mm: float,
        altura_mm: float,
        prof_mm: float,
        esp_mm: float = 18.0,
        esp_lateral_mm: float | None = None,
        tipo_envoltorio: str = "u_completo",  # Options: "u_completo", "topo", "lateral_esq", "lateral_dir", "l_esq", "l_dir"
        material: str = "MDF Carvalho",
        material_fita: str | None = None,
        recuo_frontal_mm: float = 0.0,
        sobra_frontal_mm: float = 20.0,  # Front overhang relative to the carcass to cover the doors
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> list[Group]:
        """Generates thickened cover panels to wrap a line of modules.

        Dimensions in mm on input, generated in meters in 3D space.
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
        oy_tamp = oy - sobra_f  # Projects forward to align with the doors

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

        # 1. Left Side
        if has_esq:
            # Left side panel is positioned at ox - esp_lat
            # Height covers up to the carcass top + top panel thickness (if overlaid top exists)
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

        # 2. Right Side
        if has_dir:
            # Right side panel is positioned at ox + L
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

        # 3. Continuous Top
        if has_topo:
            # The top panel spans the width of the modules.
            # In the overlaid cabinetry standard (L or U), the top covers the modules
            # between the outer sides or overlays the carcass:
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

