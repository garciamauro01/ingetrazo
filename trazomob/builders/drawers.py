"""Módulo canônico para construção e montagem padronizada de gavetas em marcenaria.

Isola a lógica canônica de montagem de gavetas (caixa interna e frente externa),
respeitando estritamente a especificação canônica de chapa (ChapaSpec / PapelChapa)
e suportando espessuras dinâmicas (15mm, 18mm, 25mm, etc.).
"""

from __future__ import annotations

from typing import Any, Optional, Tuple
from core.group import Group
from trazomob.builders.chapa_spec import (
    ChapaSpec,
    ModuloMaterialContext,
    PapelChapa,
)
from trazomob.builders.chapa_builder import build_chapa


class CanonicalDrawerBuilder:
    """Construtor canônico e reutilizável de gavetas."""

    @staticmethod
    def get_material_color(material: str | None) -> tuple[float, float, float]:
        """Resolve a cor representativa com base no nome do material."""
        from trazomob.builders.parts import CustomPartsBuilder
        return CustomPartsBuilder.get_material_color(material or "MDF Branco TX 15mm")

    @classmethod
    def build_caixa_gaveta(
        cls,
        prefixo: str,
        x_caixa: float,
        y_caixa: float,
        z_caixa: float,
        larg_caixa: float,
        prof_caixa: float,
        alt_caixa: float,
        material_gaveta: str = "MDF Branco TX 15mm",
        esp_gaveta_mm: float = 15.0,
        material_fita_gaveta: str | None = None,
        tipo_fundo_gaveta: str = "rasgo",
        material_fundo_gaveta: str = "MDF Fundo 6mm",
        esp_fundo_gaveta_mm: float = 6.0,
    ) -> list[Group]:
        """Gera as 5 peças canônicas da caixa de gaveta interna.

        - Lateral Esquerda e Lateral Direita (passando de ponta a ponta na profundidade)
        - Contra-frente Dianteira e Traseira (embutidas entre as laterais)
        - Fundo da gaveta (com rasgo/ranhura embutido ou fixado por baixo)
        """
        E_g = (esp_gaveta_mm / 1000.0) if (esp_gaveta_mm and esp_gaveta_mm > 0) else 0.015
        E_fg = (esp_fundo_gaveta_mm / 1000.0) if (esp_fundo_gaveta_mm and esp_fundo_gaveta_mm > 0) else 0.006
        cor_g = cls.get_material_color(material_gaveta)
        cor_fita_g = cls.get_material_color(material_fita_gaveta) if material_fita_gaveta else None
        cor_fg = cls.get_material_color(material_fundo_gaveta)

        mat_fita_g = material_fita_gaveta or material_gaveta
        larg_cf = max(0.04, larg_caixa - 2.0 * E_g)

        pieces: list[Group] = []

        # 1. Lateral Esquerda e Lateral Direita (E_g x prof_caixa x alt_caixa)
        spec_lat_esq = ChapaSpec.resolve(
            nome=f"{prefixo} - Lat Esq",
            papel=PapelChapa.LATERAL_GAVETA,
            ctx=ModuloMaterialContext(material_caixa=material_gaveta, material_fita_caixa=mat_fita_g),
            material_override=material_gaveta,
            fita_override=(True, False, False, True),
            material_fita_override=mat_fita_g,
        )
        pieces.append(build_chapa(
            spec_lat_esq,
            (x_caixa, y_caixa, z_caixa),
            (E_g, prof_caixa, alt_caixa),
            color=cor_g,
            cor_fita=cor_fita_g,
        ))

        spec_lat_dir = ChapaSpec.resolve(
            nome=f"{prefixo} - Lat Dir",
            papel=PapelChapa.LATERAL_GAVETA,
            ctx=ModuloMaterialContext(material_caixa=material_gaveta, material_fita_caixa=mat_fita_g),
            material_override=material_gaveta,
            fita_override=(True, False, False, True),
            material_fita_override=mat_fita_g,
        )
        pieces.append(build_chapa(
            spec_lat_dir,
            (x_caixa + larg_caixa - E_g, y_caixa, z_caixa),
            (E_g, prof_caixa, alt_caixa),
            color=cor_g,
            cor_fita=cor_fita_g,
        ))

        # 2. Contra-frentes (larg_cf x E_g x alt_cf)
        alt_cf = max(0.04, alt_caixa - 0.015)
        spec_cf_diant = ChapaSpec.resolve(
            nome=f"{prefixo} - Contra-frente Diant",
            papel=PapelChapa.CONTRAFRENTE_GAVETA,
            ctx=ModuloMaterialContext(material_caixa=material_gaveta, material_fita_caixa=mat_fita_g),
            material_override=material_gaveta,
            fita_override=(True, True, False, False),
            material_fita_override=mat_fita_g,
        )
        pieces.append(build_chapa(
            spec_cf_diant,
            (x_caixa + E_g, y_caixa, z_caixa),
            (larg_cf, E_g, alt_cf),
            color=cor_g,
            cor_fita=cor_fita_g,
        ))

        spec_cf_tras = ChapaSpec.resolve(
            nome=f"{prefixo} - Contra-frente Tras",
            papel=PapelChapa.TRASEIRO_GAVETA,
            ctx=ModuloMaterialContext(material_caixa=material_gaveta, material_fita_caixa=mat_fita_g),
            material_override=material_gaveta,
            fita_override=(True, True, False, False),
            material_fita_override=mat_fita_g,
        )
        pieces.append(build_chapa(
            spec_cf_tras,
            (x_caixa + E_g, y_caixa + prof_caixa - E_g, z_caixa),
            (larg_cf, E_g, alt_cf),
            color=cor_g,
            cor_fita=cor_fita_g,
        ))

        # 3. Fundo da Gaveta
        modo_fundo = (tipo_fundo_gaveta or "rasgo").lower()
        if modo_fundo in ("por_baixo", "baixo", "pregado", "aparafusado"):
            fundo_orig = (x_caixa, y_caixa, z_caixa)
            fundo_size = (larg_caixa, prof_caixa, E_fg)
        else:
            prof_rasgo_m = 0.006
            dist_base_m = 0.010
            larg_fundo_m = max(0.05, larg_caixa - 2.0 * E_g + 2.0 * prof_rasgo_m - 0.001)
            prof_fundo_m = max(0.05, prof_caixa - 2.0 * E_g + 2.0 * prof_rasgo_m - 0.001)
            fundo_orig = (x_caixa + E_g - prof_rasgo_m + 0.0005, y_caixa + E_g - prof_rasgo_m + 0.0005, z_caixa + dist_base_m)
            fundo_size = (larg_fundo_m, prof_fundo_m, E_fg)

        spec_fundo_gav = ChapaSpec.resolve(
            nome=f"{prefixo} - Fundo {int(esp_fundo_gaveta_mm)}mm",
            papel=PapelChapa.FUNDO_GAVETA,
            ctx=ModuloMaterialContext(material_caixa=material_fundo_gaveta),
            material_override=material_fundo_gaveta,
            fita_override=(False, False, False, False),
        )
        pieces.append(build_chapa(
            spec_fundo_gav,
            fundo_orig,
            fundo_size,
            color=cor_fg,
        ))

        return pieces

    @classmethod
    def build_gaveta_completa(
        cls,
        prefixo: str = "Gaveta",
        origem: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        largura: float = 0.50,
        profundidade: float = 0.50,
        altura: float = 0.18,
        esp_caixa_mm: float = 15.0,
        material_caixa: str = "MDF Branco TX 15mm",
        material_fita_caixa: str | None = None,
        tipo_fundo: str = "rasgo",
        material_fundo: str = "MDF Fundo 6mm",
        esp_fundo_mm: float = 6.0,
        incluir_frente: bool = False,
        material_frente: str | None = None,
        esp_frente_mm: float = 18.0,
        folga_corredica_mm: float = 26.0,  # 13mm cada lado
    ) -> list[Group]:
        """Gera a gaveta canônica completa, com caixa interna e frente externa opcional."""
        ox, oy, oz = origem
        folga_corr_m = folga_corredica_mm / 1000.0
        larg_caixa = max(0.10, largura - folga_corr_m)
        prof_caixa = max(0.15, profundidade)
        alt_caixa = max(0.08, altura)
        x_caixa = ox + (folga_corr_m / 2.0)

        pieces = cls.build_caixa_gaveta(
            prefixo=prefixo,
            x_caixa=x_caixa,
            y_caixa=oy,
            z_caixa=oz,
            larg_caixa=larg_caixa,
            prof_caixa=prof_caixa,
            alt_caixa=alt_caixa,
            material_gaveta=material_caixa,
            esp_gaveta_mm=esp_caixa_mm,
            material_fita_gaveta=material_fita_caixa,
            tipo_fundo_gaveta=tipo_fundo,
            material_fundo_gaveta=material_fundo,
            esp_fundo_gaveta_mm=esp_fundo_mm,
        )

        if incluir_frente:
            from trazomob.builders.cabinet import CabinetBuilder
            cor_frente = cls.get_material_color(material_frente or material_caixa)
            frente = CabinetBuilder.build_frente_gaveta(
                name=f"{prefixo} - Frente",
                origin=(ox, oy, oz),
                size=(largura, esp_frente_mm / 1000.0, altura),
                color=cor_frente,
                material=material_frente or material_caixa,
                material_fita=material_fita_caixa,
            )
            pieces.append(frente)

        return pieces
