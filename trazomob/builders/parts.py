# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Specialized builder for standalone woodworking parts and thickened countertops."""
from __future__ import annotations

from typing import Any

from core.group import Group

from ..builders.chapa_builder import build_chapa
from ..builders.chapa_spec import ChapaSpec, ModuloMaterialContext, PapelChapa
from ..builders.mesh_utils import create_board_group


def _chapa(
    name: str,
    origin: tuple[float, float, float],
    size: tuple[float, float, float],
    material: str,
    fita_c1: bool = False,
    fita_c2: bool = False,
    fita_l1: bool = False,
    fita_l2: bool = False,
    color: tuple[float, float, float] | None = None,
    papel: PapelChapa = PapelChapa.PECA_AVULSA,
    material_fita: str | None = None,
    operacoes: list[dict[str, Any]] | None = None,
    **kwargs: Any,
) -> Group:
    """Create a standalone part through the canonical board API (explicit material)."""
    spec = ChapaSpec.resolve(
        nome=name,
        papel=papel,
        ctx=ModuloMaterialContext(material_caixa=material),
        material_override=material,
        fita_override=(fita_c1, fita_c2, fita_l1, fita_l2),
        material_fita_override=material_fita,
        operacoes=operacoes,
    )
    if color is not None:
        kwargs["color"] = color
    return build_chapa(spec, origin, size, **kwargs)


def _chapa_frente(
    name: str,
    origin: tuple[float, float, float],
    size: tuple[float, float, float],
    ctx: ModuloMaterialContext,
    papel: PapelChapa = PapelChapa.PORTA,
    **kwargs: Any,
) -> Group:
    """Create a standalone door/front inheriting fronts material and edge banding from context."""
    spec = ChapaSpec.resolve(nome=name, papel=papel, ctx=ctx)
    return build_chapa(spec, origin, size, **kwargs)


class CustomPartsBuilder:
    """Decoupled builder for thickened countertops and individual standalone parts."""

    @staticmethod
    def get_material_color(material: str) -> tuple[float, float, float]:
        from ..domain.materials_catalog import get_material_color
        return get_material_color(material)

    @staticmethod
    def build_lateral_esquerda(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_lateral_esquerda(*args, **kwargs)

    @staticmethod
    def build_lateral_direita(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_lateral_direita(*args, **kwargs)

    @staticmethod
    def build_base_inferior(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_base_inferior(*args, **kwargs)

    @staticmethod
    def build_tampo_superior(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_tampo_superior(*args, **kwargs)

    @staticmethod
    def build_prateleira(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_prateleira(*args, **kwargs)

    @staticmethod
    def build_divisoria(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_divisoria(*args, **kwargs)

    @staticmethod
    def build_divisoria_horizontal(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_divisoria_horizontal(*args, **kwargs)

    @staticmethod
    def build_travessa_peca(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_travessa_peca(*args, **kwargs)

    @staticmethod
    def build_fundo(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_fundo(*args, **kwargs)

    @staticmethod
    def build_porta_esquerda(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_porta_esquerda(*args, **kwargs)

    @staticmethod
    def build_porta_direita(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_porta_direita(*args, **kwargs)

    @staticmethod
    def build_porta_basculante(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_porta_basculante(*args, **kwargs)

    @staticmethod
    def build_frente_gaveta(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_frente_gaveta(*args, **kwargs)

    @classmethod
    def build_gaveta_avulsa(cls, *args, **kwargs):
        """Generate the standalone canonical drawer via CanonicalDrawerBuilder."""
        from trazomob.builders.drawers import CanonicalDrawerBuilder
        return CanonicalDrawerBuilder.build_gaveta_completa(*args, **kwargs)

    @classmethod
    def build_peca_avulsa(
        cls,
        subtipo: str,
        largura_mm: float,
        altura_mm: float,
        prof_mm: float,
        esp_mm: float = 15.0,
        material: str = "MDF Branco TX 15mm",
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        material_fita: str | None = None,
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto",
        puxador_pos: str = "padrao",
        desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        cavilha_topo_superior: bool = True,
        cavilha_topo_inferior: bool = True,
        afastamento_cavilha_frontal_mm: float = 50.0,
        afastamento_cavilha_traseiro_mm: float = 50.0,
        fita_borda_modo: str = "4L",
        lado_abertura_porta: str = "esquerda",
        **kwargs: Any,
    ) -> list[Group]:
        """Generate an individual standalone part (side panel, base, stretcher, back panel, door, etc.)."""
        ox, oy, oz = offset
        profundidade_mm = float(prof_mm if prof_mm is not None else kwargs.get("profundidade_mm", 0.0))
        L = float(largura_mm) / 1000.0
        A = float(altura_mm) / 1000.0
        P = float(profundidade_mm) / 1000.0
        E = float(esp_mm) / 1000.0

        cor = cls.get_material_color(material)
        cor_fita = cls.get_material_color(material_fita) if material_fita else None

        groups: list[Group] = []

        if subtipo in ("tamponamento", "tamponamento_vertical"):
            # Canonical external vertical cover panel in YZ (thickness along X = E, depth = P, height = A)
            modo_f = (fita_borda_modo or "4L").lower()
            fc1 = modo_f in ("frontal_1l", "2l", "4l")
            fc2 = modo_f in ("2l", "4l")
            fl1 = modo_f in ("4l",)
            fl2 = modo_f in ("4l",)
            groups.append(cls.build_lateral_esquerda(
                name="Tamponamento Vertical Avulso",
                origin=(ox, oy, oz),
                size=(L, P, A),
                material=material,
                fita_c1=fc1, fita_c2=fc2, fita_l1=fl1, fita_l2=fl2,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
            ))
        elif subtipo in ("lateral", "lateral_esquerda"):
            # Canonical vertical left side panel in YZ (thickness along X = E, depth = P, height = A)
            groups.append(cls.build_lateral_esquerda(
                name="Lateral Esquerda Avulsa",
                origin=(ox, oy, oz),
                size=(E, P, A),
                material=material,
                fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
            ))
        elif subtipo == "lateral_direita":
            # Canonical vertical right side panel in YZ
            groups.append(cls.build_lateral_direita(
                name="Lateral Direita Avulsa",
                origin=(ox, oy, oz),
                size=(E, P, A),
                material=material,
                fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
            ))
        elif subtipo == "base":
            # Canonical horizontal board: Bottom Base (width = L, depth = P, thickness along Z = E)
            groups.append(cls.build_base_inferior(
                name="Base Avulsa",
                origin=(ox, oy, oz),
                size=(L, P, E),
                material=material,
                fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
            ))
        elif subtipo == "tampo_superior":
            # Canonical horizontal board: Top Panel
            groups.append(cls.build_tampo_superior(
                name="Tampo Superior Avulso",
                origin=(ox, oy, oz),
                size=(L, P, E),
                material=material,
                fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
            ))
        elif subtipo == "prateleira":
            # Canonical horizontal shelf
            groups.append(cls.build_prateleira(
                name="Prateleira Avulsa",
                origin=(ox, oy, oz),
                size=(L, P, E),
                material=material,
                fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
            ))
        elif subtipo in ("divisoria", "divisoria_vertical"):
            # Canonical vertical divider (thickness along X = E, depth = P, height = A)
            groups.append(cls.build_divisoria(
                name="Divisória Vertical Avulsa",
                origin=(ox, oy, oz),
                size=(E, P, A),
                material=material,
                fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
                cavilha_topo_superior=cavilha_topo_superior,
                cavilha_topo_inferior=cavilha_topo_inferior,
                afastamento_cavilha_frontal_mm=afastamento_cavilha_frontal_mm,
                afastamento_cavilha_traseiro_mm=afastamento_cavilha_traseiro_mm,
            ))
        elif subtipo == "divisoria_horizontal":
            # Canonical horizontal divider (width = L, depth = P, thickness along Z = E)
            groups.append(cls.build_divisoria_horizontal(
                name="Divisória Horizontal Avulsa",
                origin=(ox, oy, oz),
                size=(L, P, E),
                material=material,
                fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
            ))
        elif subtipo in ("travessa_deitada", "travessa"):
            # Canonical flat horizontal stretcher (width = L, depth = P, thickness along Z = E)
            groups.append(cls.build_travessa_peca(
                name="Travessa Deitada Avulsa",
                origin=(ox, oy, oz),
                size=(L, P, E),
                material=material,
                fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
            ))
        elif subtipo == "travessa_em_pe":
            # Canonical upright vertical stretcher (width = L, thickness along Y = E, height = A)
            groups.append(cls.build_travessa_peca(
                name="Travessa em Pe Avulsa",
                origin=(ox, oy, oz),
                size=(L, E, A),
                material=material,
                fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
            ))
        elif subtipo == "pilar_quina":
            # Vertical corner post strip (width = L, thickness along Y = E, height = A)
            groups.append(cls.build_travessa_peca(
                name="Pilar de Quina Avulso",
                origin=(ox, oy, oz),
                size=(L, E, A),
                material=material,
                fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
            ))
        elif subtipo == "fundo":
            # Canonical vertical rear back panel (width = L, thickness along Y = E or back thickness, height = A)
            esp_f = E if E <= 0.010 else 0.006
            groups.append(cls.build_fundo(
                name="Fundo Avulso",
                origin=(ox, oy, oz),
                size=(L, esp_f, A),
                material=material,
                color=cor,
            ))
        elif subtipo == "porta":
            lado_str = str(lado_abertura_porta or "esquerda").strip().lower()
            is_dir = lado_str.startswith(("dir", "right"))
            if is_dir:
                groups.append(cls.build_porta_direita(
                    name="Porta Direita Avulsa",
                    origin=(ox, oy, oz),
                    size=(L, E, A),
                    material=material,
                    color=cor,
                    material_fita=material_fita, cor_fita=cor_fita,
                    puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                    desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                    is_upper=False,
                ))
            else:
                groups.append(cls.build_porta_esquerda(
                    name="Porta Esquerda Avulsa",
                    origin=(ox, oy, oz),
                    size=(L, E, A),
                    material=material,
                    color=cor,
                    material_fita=material_fita, cor_fita=cor_fita,
                    puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                    desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                    is_upper=False,
                ))
        elif subtipo == "porta_esquerda":
            # Canonical left hinged door
            groups.append(cls.build_porta_esquerda(
                name="Porta Esquerda Avulsa",
                origin=(ox, oy, oz),
                size=(L, E, A),
                material=material,
                color=cor,
                material_fita=material_fita, cor_fita=cor_fita,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                is_upper=False,
            ))
        elif subtipo == "porta_direita":
            # Canonical right hinged door
            groups.append(cls.build_porta_direita(
                name="Porta Direita Avulsa",
                origin=(ox, oy, oz),
                size=(L, E, A),
                material=material,
                color=cor,
                material_fita=material_fita, cor_fita=cor_fita,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                is_upper=False,
            ))
        elif subtipo == "porta_basculante":
            # Canonical flip-up door (top opening, handle at bottom)
            groups.append(cls.build_porta_basculante(
                name="Porta Basculante Avulsa",
                origin=(ox, oy, oz),
                size=(L, E, A),
                material=material,
                color=cor,
                material_fita=material_fita, cor_fita=cor_fita,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                is_upper=True,
            ))
        elif subtipo == "frente_gaveta":
            # Canonical external drawer front
            groups.append(cls.build_frente_gaveta(
                name="Frente Gaveta Avulsa",
                origin=(ox, oy, oz),
                size=(L, E, A),
                material=material,
                color=cor,
                material_fita=material_fita, cor_fita=cor_fita,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
            ))
        elif subtipo in ("gaveta", "gaveta_avulsa", "caixa_gaveta"):
            # Standalone Canonical Drawer (box + bottom panel + optional front)
            from trazomob.builders.drawers import CanonicalDrawerBuilder
            esp_cx_mm = float(esp_mm) if esp_mm else 15.0
            incluir_fr = bool(kwargs.get("incluir_frente", kwargs.get("tem_frente", False)))
            mat_fr = kwargs.get("material_frente", material)
            esp_fr = float(kwargs.get("esp_frente_mm", esp_cx_mm))
            tipo_fd = str(kwargs.get("tipo_fundo_gaveta", kwargs.get("tipo_fundo", "rasgo")))
            mat_fd = str(kwargs.get("material_fundo_gaveta", kwargs.get("material_fundo", "MDF Fundo 6mm")))
            esp_fd = float(kwargs.get("esp_fundo_gaveta_mm", kwargs.get("esp_fundo_mm", 6.0)))
            folga_corr = float(kwargs.get("folga_corredica_mm", 26.0))

            gav_pieces = CanonicalDrawerBuilder.build_gaveta_completa(
                prefixo="Gaveta Avulsa",
                origem=(ox, oy, oz),
                largura=L,
                profundidade=P,
                altura=A,
                esp_caixa_mm=esp_cx_mm,
                material_caixa=material,
                material_fita_caixa=material_fita,
                tipo_fundo=tipo_fd,
                material_fundo=mat_fd,
                esp_fundo_mm=esp_fd,
                incluir_frente=incluir_fr,
                material_frente=mat_fr,
                esp_frente_mm=esp_fr,
                folga_corredica_mm=folga_corr,
            )
            groups.extend(gav_pieces)

        else:
            groups.append(_chapa(
                f"Peca {subtipo}",
                (ox, oy, oz),
                (L, P, A),
                material, fita_c1=True, color=cor,
            ))

        return groups

    @classmethod
    def build_rodape_fechado(
        cls,
        largura_mm: float,
        altura_mm: float,
        prof_mm: float,
        esp_mm: float = 15.0,
        larg_travessa_topo_mm: float = 70.0,
        recuo_frontal_mm: float = 30.0,
        material: str = "MDF Branco TX 15mm",
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        material_fita: str | None = None,
    ) -> list[Group]:
        """Generate a structured closed toe-kick base for cabinetwork.

        Composition:
        1. Recessed front (XZ plane, thickness along Y, upright).
        2. Left and right side panels (YZ plane, thickness along X, upright).
        3. Upright rear stretcher (XZ plane, thickness along Y, closes the back).
        4. Horizontal top/mounting stretchers (XY plane, thickness along Z, flat):
           - Top flat front stretcher (right behind the recessed front).
           - Top flat rear stretcher (right in front of the rear closure).
        5. Intermediate vertical reinforcement/support cleats for wide spans (L > 600mm).
        """
        ox, oy, oz = offset
        L = largura_mm / 1000.0
        A = altura_mm / 1000.0
        P = prof_mm / 1000.0
        E = esp_mm / 1000.0

        recuo = max(0.0, recuo_frontal_mm / 1000.0)
        larg_trav = min(max(0.0, larg_travessa_topo_mm / 1000.0), max(0.0, P - recuo))
        prof_lateral = max(0.0, P - recuo - E)

        cor = cls.get_material_color(material)
        cor_fita = cls.get_material_color(material_fita) if material_fita else None

        groups: list[Group] = []

        # 1. Recessed front (XZ plane, thickness along Y)
        if L > 0 and A > 0 and E > 0:
            groups.append(_chapa(
                "Rodapé Fechado - Frente",
                (ox, oy + recuo, oz),
                (L, E, A),
                material,
                fita_c1=True, fita_c2=False, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
                papel=PapelChapa.RODAPE,
            ))

        # 2. Upright rear stretcher (XZ plane, thickness along Y, at total rear oy + P - E)
        if L > 0 and A > 0 and E > 0 and P > (recuo + 2 * E):
            larg_fundo_util = max(0.0, L - 2 * E) if L > 2 * E else L
            x_fundo = (ox + E) if L > 2 * E else ox
            groups.append(_chapa(
                "Rodapé Fechado - Travessa Fundo em Pé",
                (x_fundo, oy + P - E, oz),
                (larg_fundo_util, E, A),
                material,
                fita_c1=False, fita_c2=False, fita_l1=False, fita_l2=False,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
                papel=PapelChapa.TRAVESSA,
            ))

        # 3. Closure side panels (YZ plane, thickness along X)
        # Span from behind the recessed front (oy + recuo + E) to the total rear (oy + P)
        prof_lateral = max(0.0, P - recuo - E)
        if prof_lateral > 0 and A > 0 and E > 0:
            groups.append(_chapa(
                "Rodapé Fechado - Lateral Esquerda",
                (ox, oy + recuo + E, oz),
                (E, prof_lateral, A),
                material,
                fita_c1=True, fita_c2=True, fita_l1=False, fita_l2=False,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
                papel=PapelChapa.LATERAL_ESQUERDA,
            ))
            groups.append(_chapa(
                "Rodapé Fechado - Lateral Direita",
                (ox + L - E, oy + recuo + E, oz),
                (E, prof_lateral, A),
                material,
                fita_c1=True, fita_c2=True, fita_l1=False, fita_l2=False,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
                papel=PapelChapa.LATERAL_DIREITA,
            ))

        # 4. Top flat front stretcher (XY plane, thickness along Z)
        # Positioned at the top of the toe kick (oz + A - E), right behind the recessed front
        largura_util_trav = max(0.0, L - 2 * E) if L > 2 * E else L
        x_trav = (ox + E) if L > 2 * E else ox

        if larg_trav > 0 and L > 0 and E > 0:
            groups.append(_chapa(
                "Rodapé Fechado - Travessa Superior Frontal",
                (x_trav, oy + recuo + E, oz + A - E),
                (largura_util_trav, larg_trav, E),
                material,
                fita_c1=True, fita_c2=False, fita_l1=True, fita_l2=False,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
                papel=PapelChapa.TRAVESSA,
            ))

        # 5. Top flat rear stretcher (XY plane, thickness along Z)
        # Positioned at the top of the toe kick (oz + A - E), flush against the rear
        if larg_trav > 0 and L > 0 and E > 0 and P > (recuo + larg_trav + E):
            y_trav_fundo = max(oy + recuo + E + larg_trav, oy + P - E - larg_trav)
            groups.append(_chapa(
                "Rodapé Fechado - Travessa Deitada do Fundo",
                (x_trav, y_trav_fundo, oz + A - E),
                (largura_util_trav, larg_trav, E),
                material,
                fita_c1=False, fita_c2=False, fita_l1=False, fita_l2=False,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
                papel=PapelChapa.TRAVESSA,
            ))

        # 6. Internal reinforcement stretchers (intermediate ribs/supports along Y - depth)
        # For wide spans (L >= 600 mm), distributes intermediate reinforcement stretchers.
        # The intermediate height sits just below the top flat stretchers (A - E),
        # serving as continuous bottom support for the flat stretchers without overlapping them.
        prof_reforco = max(0.0, P - recuo - 2 * E)
        alt_reforco = max(0.0, A - E) if (larg_trav > 0) else A
        if L > 0.6 and prof_reforco > 0 and alt_reforco > 0 and E > 0:
            num_espacos = max(2, int(round(L / 0.5)))
            passo_x = (L - 2 * E) / num_espacos
            for i in range(1, num_espacos):
                rx = (ox + E) + i * passo_x - (E / 2.0)
                groups.append(_chapa(
                    f"Rodapé Fechado - Reforço Central {i}",
                    (rx, oy + recuo + E, oz),
                    (E, prof_reforco, alt_reforco),
                    material,
                    fita_c1=False, fita_c2=False, fita_l1=False, fita_l2=False,
                    color=cor, material_fita=material_fita, cor_fita=cor_fita,
                    papel=PapelChapa.TRAVESSA,
                ))

        return groups

    @classmethod
    def build_tampo_engrossado(
        cls,
        largura_mm: float,
        altura_mm: float,
        prof_mm: float,
        esp_chapa_mm: float = 18.0,
        larg_engrosso_mm: float = 70.0,
        tipo_engrosso: str = "3_lados",
        qtd_engrosso: int = 1,
        fechar_embaixo: bool = False,
        snap_parede: str = "auto",
        material: str = "MDF Branco TX",
        material_fita: str | None = None,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> list[Group]:
        """Generate a thickened woodworking top with perimeter strips at the actual board thickness.

        ``snap_parede`` is snap metadata (does not alter geometry): it defines
        which face snaps to the wall during magnetic drag and allows disabling snap.
        """
        ox, oy, oz = offset
        L = largura_mm / 1000.0
        P = prof_mm / 1000.0

        # Nominal wood board thickness
        e_chapa = (esp_chapa_mm if esp_chapa_mm > 0 else 18.0) / 1000.0

        # Determine the number of intermediate thickening strip layers:
        # If qtd_engrosso is explicitly passed (> 0), use it directly.
        n_camadas = int(qtd_engrosso) if qtd_engrosso and int(qtd_engrosso) >= 1 else 1

        w_regua = (larg_engrosso_mm if larg_engrosso_mm > 0 else 70.0) / 1000.0
        w_regua = min(w_regua, min(L, P) * 0.45)

        cor = cls.get_material_color(material)
        cor_fita = cls.get_material_color(material_fita) if material_fita else None

        groups: list[Group] = []

        # ── VERTICAL STRUCTURE FROM BOTTOM TO TOP: ──────────────────
        # Bottom level of the complete module starts at oz:
        # 1. If 'fechar_embaixo' is active:
        #    - The bottom closure board sits at the base: z = oz to oz + e_chapa.
        #    - The thickening strips sit on top of it: z = oz + e_chapa + (idx * e_chapa).
        #    - The top board sits on top of everything: z = oz + e_chapa + (n_camadas * e_chapa).
        # 2. If there is NO bottom closure:
        #    - The thickening strips sit at the base: z = oz + (idx * e_chapa).
        #    - The top board sits at the top: z = oz + (n_camadas * e_chapa).

        z_base_reguas = oz + (e_chapa if fechar_embaixo else 0.0)
        z_tampo_topo = z_base_reguas + n_camadas * e_chapa

        # 1. Main Top Board (Sits at the top at z_tampo_topo)
        grp_tampo = _chapa(
            "Tampo Superior",
            (ox, oy, z_tampo_topo),
            (L, P, e_chapa),
            material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
            color=cor, material_fita=material_fita, cor_fita=cor_fita,
            papel=PapelChapa.TAMPO_SUPERIOR,
        )
        groups.append(grp_tampo)

        # 2. Intermediate Thickening Strips in Discrete Slices/Layers
        # Each layer has thickness strictly equal to 'e_chapa' of the wood board
        for camada_idx in range(n_camadas):
            z_layer = z_base_reguas + camada_idx * e_chapa
            sufixo_camada = f" Camada {camada_idx + 1}" if n_camadas > 1 else ""

            # Front Strip (along X)
            grp_regua_front = _chapa(
                f"Régua Engrosso Frontal{sufixo_camada}",
                (ox, oy, z_layer),
                (L, w_regua, e_chapa),
                material, fita_c1=True, fita_c2=False, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
                papel=PapelChapa.TRAVESSA,
            )
            groups.append(grp_regua_front)

            # Side Strips (along Y)
            if tipo_engrosso in ("3_lados", "4_lados", "laterais"):
                y_lat_inicio = oy + w_regua
                comp_lat = P - w_regua - (w_regua if tipo_engrosso == "4_lados" else 0.0)
                if comp_lat > 0.02:
                    # Left Side
                    grp_lat_esq = _chapa(
                        f"Régua Engrosso Lateral Esquerda{sufixo_camada}",
                        (ox, y_lat_inicio, z_layer),
                        (w_regua, comp_lat, e_chapa),
                        material, fita_c1=False, fita_c2=False, fita_l1=True, fita_l2=False,
                        color=cor, material_fita=material_fita, cor_fita=cor_fita,
                        papel=PapelChapa.TRAVESSA,
                    )
                    groups.append(grp_lat_esq)

                    # Right Side
                    grp_lat_dir = _chapa(
                        f"Régua Engrosso Lateral Direita{sufixo_camada}",
                        (ox + L - w_regua, y_lat_inicio, z_layer),
                        (w_regua, comp_lat, e_chapa),
                        material, fita_c1=False, fita_c2=False, fita_l1=False, fita_l2=True,
                        color=cor, material_fita=material_fita, cor_fita=cor_fita,
                        papel=PapelChapa.TRAVESSA,
                    )
                    groups.append(grp_lat_dir)

            # Rear Strip (along X, if 4 sides)
            if tipo_engrosso == "4_lados":
                grp_regua_tras = _chapa(
                    f"Régua Engrosso Traseira{sufixo_camada}",
                    (ox, oy + P - w_regua, z_layer),
                    (L, w_regua, e_chapa),
                    material, fita_c1=False, fita_c2=True, fita_l1=True, fita_l2=True,
                    color=cor, material_fita=material_fita, cor_fita=cor_fita,
                    papel=PapelChapa.TRAVESSA,
                )
                groups.append(grp_regua_tras)

            # Central Support Stretcher (if clear span L > 900 mm)
            if L > 0.90:
                y_centro_inicio = oy + w_regua
                comp_centro = P - w_regua - (w_regua if tipo_engrosso == "4_lados" else 0.0)
                if comp_centro > 0.05:
                    x_centro = ox + (L - w_regua) * 0.5
                    grp_centro = _chapa(
                        f"Régua Reforço Central{sufixo_camada}",
                        (x_centro, y_centro_inicio, z_layer),
                        (w_regua, comp_centro, e_chapa),
                        material, fita_c1=False, fita_c2=False, fita_l1=False, fita_l2=False,
                        color=cor, material_fita=material_fita, cor_fita=cor_fita,
                        papel=PapelChapa.TRAVESSA,
                    )
                    groups.append(grp_centro)

        # 3. Bottom Closure Board (Sandwich / Hollow-Core Panel - Tamburato)
        if fechar_embaixo:
            # Full-piece bottom board at the absolute base (oz)
            grp_fechamento = _chapa(
                "Chapa Fechamento Inferior",
                (ox, oy, oz),
                (L, P, e_chapa),
                material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
                papel=PapelChapa.BASE_INFERIOR,
            )
            groups.append(grp_fechamento)

        return groups

    @classmethod
    def build_portas_correr_avulsas(
        cls,
        largura_mm: float,
        altura_mm: float,
        prof_mm: float = 65.0,
        num_portas: int = 2,
        esp_mm: float = 15.0,
        transpasse_mm: float = 30.0,
        material: str = "MDF Branco TX 15mm",
        material_fita: str | None = None,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        puxador_tipo: str = "perfil",
        puxador_cor: str = "preto",
        puxador_pos: str = "padrao",
        desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> list[Group]:
        """Generate a standalone sliding door set (2 to 4 doors) with double aluminum tracks."""
        from PySide6.QtGui import QVector3D
        if mat_ctx is None:
            mat_ctx = ModuloMaterialContext(
                material_caixa=material,
                material_frentes=material,
            )

        ox, oy, oz = offset
        L = max(0.40, float(largura_mm) / 1000.0)
        A = max(0.30, float(altura_mm) / 1000.0)
        P = max(0.045, float(prof_mm) / 1000.0)
        E_frente = max(0.006, float(esp_mm) / 1000.0)
        n_portas = max(2, min(4, int(num_portas)))
        transpasse = max(0.0, float(transpasse_mm) / 1000.0)

        cor_frente = cls.get_material_color(material)
        cor_fita = cls.get_material_color(material_fita) if material_fita else None

        groups: list[Group] = []

        # 1. Double Aluminum Tracks (Bottom and Top)
        prof_trilho = min(0.045, P)
        groups.append(create_board_group(
            "Portas Correr - Trilho Inferior",
            (ox, oy, oz),
            (L, prof_trilho, 0.008),
            "Alumínio Anodizado", color=(0.75, 0.77, 0.80),
        ))
        groups.append(create_board_group(
            "Portas Correr - Trilho Superior",
            (ox, oy, oz + A - 0.035),
            (L, prof_trilho, 0.035),
            "Alumínio Anodizado", color=(0.75, 0.77, 0.80),
        ))

        # 2. Door leaf cut calculation (2, 3, or 4 doors)
        # For sliding doors, when puxador_pos is "padrao"/"auto"/"superior" and puxador_tipo is "perfil" or "alca",
        # the sliding door handle/profile sits along the vertical side/extension of the door leaf.
        eff_pux_pos = puxador_pos
        if str(eff_pux_pos or "padrao").lower() in ("padrao", "auto", "superior", "topo"):
            eff_pux_pos = "extensao"
        # Standard 15mm vertical deduction for sliding track/roller system
        alt_porta = max(0.10, A - 0.015)
        z_porta = oz + 0.008
        # In TrazoMob's coordinate system, the furniture front points toward -Y and the back toward +Y.
        # Therefore, the outer (front) track is at smaller Y and the inner (rear) track is at larger Y.
        y_trilho_frontal = oy + 0.004
        y_trilho_traseiro = oy + 0.004 + E_frente + 0.012

        if n_portas == 2:
            # 2 Doors: 1 central overlap (30mm)
            larg_porta = (L + transpasse) / 2.0
            slide_dist = max(0.05, larg_porta - transpasse)

            # Leaf 1: Left (Rear/Inner Track) -> slides right (+X)
            # Handle on the outer left edge (door_side="right" places the handle at ox)
            p1 = _chapa_frente(
                "Porta Correr 1 - Esq (Interna)",
                (ox, y_trilho_traseiro, z_porta),
                (larg_porta, E_frente, alt_porta),
                mat_ctx, color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                door_side="right",
            )
            if getattr(p1, "ext", None) is None:
                p1.ext = {}
            p1.ext["slide_axis"] = QVector3D(1.0, 0.0, 0.0)
            p1.ext["slide_distance"] = float(slide_dist)
            groups.append(p1)

            # Leaf 2: Right (Front/Outer Track) -> slides left (-X)
            # Handle on the outer right edge (door_side="left" places the handle at ox + larg_porta)
            x_p2 = ox + L - larg_porta
            p2 = _chapa_frente(
                "Porta Correr 2 - Dir (Externa)",
                (x_p2, y_trilho_frontal, z_porta),
                (larg_porta, E_frente, alt_porta),
                mat_ctx, color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                door_side="left",
            )
            if getattr(p2, "ext", None) is None:
                p2.ext = {}
            p2.ext["slide_axis"] = QVector3D(-1.0, 0.0, 0.0)
            p2.ext["slide_distance"] = float(slide_dist)
            groups.append(p2)

        elif n_portas == 3:
            # 3 Doors: 2 overlaps (30mm between Leaf 1-2 and 30mm between Leaf 2-3)
            larg_porta = (L + (2.0 * transpasse)) / 3.0
            slide_dist = max(0.05, larg_porta - transpasse)

            # Leaf 1: Left (Rear/Inner Track) -> slides right (+X), handle on the left
            p1 = _chapa_frente(
                "Porta Correr 1 - Esq (Interna)",
                (ox, y_trilho_traseiro, z_porta),
                (larg_porta, E_frente, alt_porta),
                mat_ctx, color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                door_side="right",
            )
            if getattr(p1, "ext", None) is None:
                p1.ext = {}
            p1.ext["slide_axis"] = QVector3D(1.0, 0.0, 0.0)
            p1.ext["slide_distance"] = float(slide_dist)
            groups.append(p1)

            # Leaf 2: Center (Front/Outer Track) -> slides both ways, handle on both sides ("both")
            x_p2 = ox + (L * 0.5) - (larg_porta * 0.5)
            p2 = _chapa_frente(
                "Porta Correr 2 - Centro (Externa)",
                (x_p2, y_trilho_frontal, z_porta),
                (larg_porta, E_frente, alt_porta),
                mat_ctx, color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                door_side="both",
            )
            if getattr(p2, "ext", None) is None:
                p2.ext = {}
            p2.ext["slide_axis"] = QVector3D(1.0, 0.0, 0.0)
            p2.ext["slide_distance"] = float(slide_dist)
            groups.append(p2)

            # Leaf 3: Right (Rear/Inner Track) -> slides left (-X), handle on the right
            x_p3 = ox + L - larg_porta
            p3 = _chapa_frente(
                "Porta Correr 3 - Dir (Interna)",
                (x_p3, y_trilho_traseiro, z_porta),
                (larg_porta, E_frente, alt_porta),
                mat_ctx, color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                door_side="left",
            )
            if getattr(p3, "ext", None) is None:
                p3.ext = {}
            p3.ext["slide_axis"] = QVector3D(-1.0, 0.0, 0.0)
            p3.ext["slide_distance"] = float(slide_dist)
            groups.append(p3)

        else:
            # 4 Doors: symmetrical system (2 outer leaves on rear track + 2 center leaves on front track)
            larg_porta = (L + (2.0 * transpasse)) / 4.0
            slide_dist = max(0.05, larg_porta - transpasse)

            # Leaf 1: Left End (Rear/Inner) -> slides right (+X), handle on the left
            x_p1 = ox
            p1 = _chapa_frente(
                "Porta Correr 1 - Esq (Interna)",
                (x_p1, y_trilho_traseiro, z_porta),
                (larg_porta, E_frente, alt_porta),
                mat_ctx, color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                door_side="right",
            )
            if getattr(p1, "ext", None) is None:
                p1.ext = {}
            p1.ext["slide_axis"] = QVector3D(1.0, 0.0, 0.0)
            p1.ext["slide_distance"] = float(slide_dist)
            groups.append(p1)

            # Leaf 2: Center-Left (Front/Outer) -> slides left (-X), handle at center meeting (right)
            x_p2 = ox + (L * 0.5) - larg_porta
            p2 = _chapa_frente(
                "Porta Correr 2 - Centro Esq (Externa)",
                (x_p2, y_trilho_frontal, z_porta),
                (larg_porta, E_frente, alt_porta),
                mat_ctx, color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                door_side="left",
            )
            if getattr(p2, "ext", None) is None:
                p2.ext = {}
            p2.ext["slide_axis"] = QVector3D(-1.0, 0.0, 0.0)
            p2.ext["slide_distance"] = float(slide_dist)
            groups.append(p2)

            # Leaf 3: Center-Right (Front/Outer) -> slides right (+X), handle at center meeting (left)
            x_p3 = ox + (L * 0.5)
            p3 = _chapa_frente(
                "Porta Correr 3 - Centro Dir (Externa)",
                (x_p3, y_trilho_frontal, z_porta),
                (larg_porta, E_frente, alt_porta),
                mat_ctx, color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                door_side="right",
            )
            if getattr(p3, "ext", None) is None:
                p3.ext = {}
            p3.ext["slide_axis"] = QVector3D(1.0, 0.0, 0.0)
            p3.ext["slide_distance"] = float(slide_dist)
            groups.append(p3)

            # Leaf 4: Right End (Rear/Inner) -> slides left (-X), handle on the right
            x_p4 = ox + L - larg_porta
            p4 = _chapa_frente(
                "Porta Correr 4 - Dir (Interna)",
                (x_p4, y_trilho_traseiro, z_porta),
                (larg_porta, E_frente, alt_porta),
                mat_ctx, color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                door_side="left",
            )
            if getattr(p4, "ext", None) is None:
                p4.ext = {}
            p4.ext["slide_axis"] = QVector3D(-1.0, 0.0, 0.0)
            p4.ext["slide_distance"] = float(slide_dist)
            groups.append(p4)

        return groups

    @classmethod
    def build_prateleiras_avulsas(
        cls,
        largura_mm: float,
        altura_mm: float,
        prof_mm: float,
        num_prateleiras: int = 2,
        esp_mm: float = 15.0,
        has_primeira: bool = False,
        has_ultima: bool = False,
        material: str = "MDF Branco TX 15mm",
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        material_fita: str | None = None,
        cor_fita: tuple[float, float, float] | None = None,
        fita_c1: bool = True,
        fita_c2: bool = True,
        fita_l1: bool = True,
        fita_l2: bool = True,
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> list[Group]:
        """Generate a set of standalone shelves distributed across the specified total space.

        The ``num_prateleiras`` parameter defines the number of intermediate shelves
        that divide the opening into equal sections.
        ``has_primeira``: if True, adds a shelf at the bottom base of the opening (oz).
        ``has_ultima``: if True, adds a shelf at the top of the opening (oz + A - E).
        Example: 2 intermediate + has_primeira + has_ultima = 4 shelves in total.
        """
        ox, oy, oz = offset
        L = float(largura_mm) / 1000.0
        A = float(altura_mm) / 1000.0
        P = float(prof_mm) / 1000.0
        E = float(esp_mm) / 1000.0
        cor = cls.get_material_color(material)
        mat_ctx = mat_ctx or ModuloMaterialContext(
            material_caixa=material,
            material_fita_caixa=material_fita,
        )

        n_interm = max(0, int(num_prateleiras))
        n_espacos = n_interm + 1

        # Usable clear height for distribution discounting thicknesses
        z_pos: list[tuple[str, float]] = []

        # 1. First shelf (Bottom of usable space)
        if has_primeira:
            z_pos.append(("Base", oz))

        # 2. Intermediate shelves: divide height A evenly
        if n_interm > 0:
            passo = max(0.0, (A - E) / n_espacos) if A >= E else 0.0
            for i in range(1, n_interm + 1):
                z_interm = oz + (i * passo)
                z_pos.append((f"Intermediária {i}" if n_interm > 1 else "Intermediária", z_interm))

        # 3. Last shelf (Top of usable space)
        if has_ultima:
            z_topo = oz + max(0.0, A - E)
            z_pos.append(("Topo", z_topo))

        # If neither is selected and there are no intermediate shelves, ensure at least 1
        if not z_pos:
            z_pos.append(("Central", oz + max(0.0, (A - E) / 2.0)))

        # Sort shelves along Z for logical numbering
        z_pos.sort(key=lambda item: item[1])

        groups: list[Group] = []
        for idx, (label, z) in enumerate(z_pos, 1):
            spec = ChapaSpec.resolve(
                nome=f"Prateleira Avulsa {idx} ({label})",
                papel=PapelChapa.PRATELEIRA,
                ctx=mat_ctx,
                material_override=material,
                fita_override=(fita_c1, fita_c2, fita_l1, fita_l2),
                material_fita_override=material_fita,
            )
            p = build_chapa(
                spec,
                (ox, oy, z),
                (L, P, E),
                color=cor,
                cor_fita=cor_fita,
            )
            groups.append(p)

        return groups





