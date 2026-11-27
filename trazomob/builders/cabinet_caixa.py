# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Carcass and structural components for CabinetBuilder."""
from __future__ import annotations

from typing import Any

from core.group import Group

from ..builders.chapa_builder import build_chapa
from ..builders.chapa_spec import ChapaSpec, ModuloMaterialContext, PapelChapa
from ..domain.materials_catalog import get_material_color


class CaixaMixin:
    """Back panels, drawers, and the base modular carcass for modules."""

    @staticmethod
    def get_material_color(material: str) -> tuple[float, float, float]:
        return get_material_color(material)

    @classmethod
    def _calc_desconto_traseiro_fundo(
        cls,
        tipo_fundo: str = "rasgo",
        esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0,
        esp_travessa_traseira_mm: float = 0.0,
    ) -> float:
        """Calculates the rear setback (in meters) up to the front face of the back panel.

        Ensures internal parts (shelves, dividers, drawers) fit strictly within
        the clear internal opening, resting flush against the back panel face
        without ever intersecting or protruding past it.
        When a rear stretcher is present (esp_travessa_traseira_mm > 0), the
        back panel rests directly behind it (setback equal to the rear stretcher thickness).
        """
        recuo_efetivo_mm = esp_travessa_traseira_mm if esp_travessa_traseira_mm > 0 else recuo_fundo_mm
        if tipo_fundo == "rasgo":
            return (recuo_efetivo_mm + esp_fundo_mm) / 1000.0
        elif tipo_fundo == "sobreposto":
            return esp_fundo_mm / 1000.0
        return 0.0

    @classmethod
    def build_fundo_board(
        cls,
        prefixo: str,
        largura_interna_m: float,
        altura_interna_m: float,
        largura_total_m: float,
        altura_total_caixa_m: float,
        prof_total_m: float,
        esp_lateral_m: float,
        origin_caixa: tuple[float, float, float],
        z_interno_base_m: float,
        tipo_fundo: str = "rasgo",
        esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0,
        prof_rasgo_mm: float = 5.0,
        folga_fundo_mm: float = 2.0,
        material_fundo: str | None = None,
        esp_travessa_traseira_mm: float = 0.0,
    ) -> Group | None:
        """Generates the back panel part using TrazoMob cabinetry parameters.

        Supports:
        - 'rasgo': Recessed dado/groove in the sides and base, with rear setback
          (resting directly behind the rear stretcher when present).
        - 'sobreposto': Panel nailed / screwed onto the rear.
        - 'sem_fundo': No back panel part generated.
        """
        if tipo_fundo == "sem_fundo":
            return None

        ox, oy, oz_caixa = origin_caixa
        E = esp_lateral_m
        E_fundo = esp_fundo_mm / 1000.0
        prof_r_m = prof_rasgo_mm / 1000.0
        folga_m = folga_fundo_mm / 1000.0
        recuo_efetivo_mm = esp_travessa_traseira_mm if esp_travessa_traseira_mm > 0 else recuo_fundo_mm
        recuo_m = recuo_efetivo_mm / 1000.0

        if tipo_fundo == "sobreposto":
            # Surface-mounted: covers the full rear (minus squareness clearance)
            comp_m = max(0.05, altura_total_caixa_m - folga_m)
            larg_m = max(0.05, largura_total_m - folga_m)
            px = ox + (folga_m / 2.0)
            py = oy + prof_total_m - E_fundo
            pz = oz_caixa + (folga_m / 2.0)
        else:
            # Dado / Groove: extends into the side and base grooves and deducts clearance
            larg_chapa_mm = (largura_interna_m * 1000.0) + (2.0 * prof_rasgo_mm) - folga_fundo_mm
            alt_chapa_mm = (altura_interna_m * 1000.0) + (2.0 * prof_rasgo_mm) - folga_fundo_mm
            larg_m = max(0.05, larg_chapa_mm / 1000.0)
            comp_m = max(0.05, alt_chapa_mm / 1000.0)
            px = ox + E - prof_r_m + (folga_m / 2.0)
            py = oy + prof_total_m - recuo_m - E_fundo
            pz = z_interno_base_m - prof_r_m + (folga_m / 2.0)

        nome = f"{prefixo} - Fundo {int(esp_fundo_mm)}mm"
        if material_fundo:
            mat = material_fundo
        elif esp_fundo_mm <= 6.0:
            mat = f"MDF Fundo {int(esp_fundo_mm)}mm"
        else:
            mat = f"MDF Branco TX {int(esp_fundo_mm)}mm"

        return cls.build_fundo(
            name=nome,
            origin=(px, py, pz),
            size=(larg_m, E_fundo, comp_m),
            material=mat,
            color=(0.88, 0.88, 0.88),
        )

    @classmethod
    def build_prateleira(
        cls,
        name: str,
        origin: tuple[float, float, float],
        size: tuple[float, float, float],
        material: str,
        color: tuple[float, float, float] | None = None,
        fita_c1: bool = True,
        fita_c2: bool = False,
        fita_l1: bool = False,
        fita_l2: bool = False,
        afastamento_mm: float = 50.0,
        gerar_furacao: bool = True,
        material_fita: str | None = None,
        cor_fita: tuple[float, float, float] | None = None,
        operacoes: list[dict[str, Any]] | None = None,
        ctx: ModuloMaterialContext | None = None,
    ) -> Group:
        """Universal canonical object: Internal shelf with standardized end drilling.

        Cabinetry standard:
        - Edge banding on the front (fita_c1=True) or customized on other faces.
        - Machining on the left and right ends for pins/dowels or shelf supports (Ø8mm or Ø5mm).
        """
        sx, sy, sz = size
        prof_prat_mm = abs(sy) * 1000.0
        esp_prat_mm = abs(sz) * 1000.0

        if operacoes is not None:
            ops = list(operacoes)
        elif gerar_furacao:
            from ..production.machining import make_shelf_joint_holes
            ops_esq, ops_dir = make_shelf_joint_holes(
                prof_prateleira_mm=prof_prat_mm,
                afastamento_mm=afastamento_mm,
                esp_prateleira_mm=esp_prat_mm,
            )
            ops = [o.to_dict() for o in ops_esq + ops_dir]
        else:
            ops = []

        if ctx is not None:
            spec = ChapaSpec.resolve(
                nome=name,
                papel=PapelChapa.PRATELEIRA,
                ctx=ctx,
                material_override=material,
                fita_override=(fita_c1, fita_c2, fita_l1, fita_l2) if (fita_c1, fita_c2, fita_l1, fita_l2) != (True, False, False, False) else None,
                material_fita_override=material_fita,
                operacoes=ops,
            )
            return build_chapa(spec, origin, size)

        spec = ChapaSpec.resolve(
            nome=name,
            papel=PapelChapa.PRATELEIRA,
            ctx=ModuloMaterialContext(material_caixa=material, material_fita_caixa=material_fita),
            material_override=material,
            fita_override=(fita_c1, fita_c2, fita_l1, fita_l2),
            material_fita_override=material_fita,
            operacoes=ops,
        )
        return build_chapa(spec, origin, size)

    @classmethod
    def build_lateral_esquerda(
        cls,
        name: str,
        origin: tuple[float, float, float],
        size: tuple[float, float, float],
        material: str,
        color: tuple[float, float, float] | None = None,
        fita_c1: bool = True,
        fita_c2: bool = False,
        fita_l1: bool = True,
        fita_l2: bool = False,
        material_fita: str | None = None,
        cor_fita: tuple[float, float, float] | None = None,
        operacoes: list[dict[str, Any]] | None = None,
        ctx: ModuloMaterialContext | None = None,
    ) -> Group:
        """Universal canonical object: Carcass Left Side."""
        if ctx is not None:
            spec = ChapaSpec.resolve(
                nome=name,
                papel=PapelChapa.LATERAL_ESQUERDA,
                ctx=ctx,
                material_override=material,
                fita_override=(fita_c1, fita_c2, fita_l1, fita_l2) if (fita_c1, fita_c2, fita_l1, fita_l2) != (True, False, True, False) else None,
                material_fita_override=material_fita,
                operacoes=operacoes,
            )
            return build_chapa(spec, origin, size)

        spec = ChapaSpec.resolve(
            nome=name,
            papel=PapelChapa.LATERAL_ESQUERDA,
            ctx=ModuloMaterialContext(material_caixa=material, material_fita_caixa=material_fita),
            material_override=material,
            fita_override=(fita_c1, fita_c2, fita_l1, fita_l2),
            material_fita_override=material_fita,
            operacoes=operacoes,
        )
        return build_chapa(spec, origin, size)

    @classmethod
    def build_lateral_direita(
        cls,
        name: str,
        origin: tuple[float, float, float],
        size: tuple[float, float, float],
        material: str,
        color: tuple[float, float, float] | None = None,
        fita_c1: bool = True,
        fita_c2: bool = False,
        fita_l1: bool = True,
        fita_l2: bool = False,
        material_fita: str | None = None,
        cor_fita: tuple[float, float, float] | None = None,
        operacoes: list[dict[str, Any]] | None = None,
        ctx: ModuloMaterialContext | None = None,
    ) -> Group:
        """Universal canonical object: Carcass Right Side."""
        if ctx is not None:
            spec = ChapaSpec.resolve(
                nome=name,
                papel=PapelChapa.LATERAL_DIREITA,
                ctx=ctx,
                material_override=material,
                fita_override=(fita_c1, fita_c2, fita_l1, fita_l2) if (fita_c1, fita_c2, fita_l1, fita_l2) != (True, False, True, False) else None,
                material_fita_override=material_fita,
                operacoes=operacoes,
            )
            return build_chapa(spec, origin, size)

        spec = ChapaSpec.resolve(
            nome=name,
            papel=PapelChapa.LATERAL_DIREITA,
            ctx=ModuloMaterialContext(material_caixa=material, material_fita_caixa=material_fita),
            material_override=material,
            fita_override=(fita_c1, fita_c2, fita_l1, fita_l2),
            material_fita_override=material_fita,
            operacoes=operacoes,
        )
        return build_chapa(spec, origin, size)

    @classmethod
    def build_base_inferior(
        cls,
        name: str,
        origin: tuple[float, float, float],
        size: tuple[float, float, float],
        material: str,
        color: tuple[float, float, float] | None = None,
        fita_c1: bool = True,
        fita_c2: bool = False,
        fita_l1: bool = False,
        fita_l2: bool = False,
        material_fita: str | None = None,
        cor_fita: tuple[float, float, float] | None = None,
        operacoes: list[dict[str, Any]] | None = None,
        ctx: ModuloMaterialContext | None = None,
    ) -> Group:
        """Universal canonical object: Carcass Bottom Panel."""
        if ctx is not None:
            spec = ChapaSpec.resolve(
                nome=name,
                papel=PapelChapa.BASE_INFERIOR,
                ctx=ctx,
                material_override=material,
                fita_override=(fita_c1, fita_c2, fita_l1, fita_l2) if (fita_c1, fita_c2, fita_l1, fita_l2) != (True, False, False, False) else None,
                material_fita_override=material_fita,
                operacoes=operacoes,
            )
            return build_chapa(spec, origin, size)

        spec = ChapaSpec.resolve(
            nome=name,
            papel=PapelChapa.BASE_INFERIOR,
            ctx=ModuloMaterialContext(material_caixa=material, material_fita_caixa=material_fita),
            material_override=material,
            fita_override=(fita_c1, fita_c2, fita_l1, fita_l2),
            material_fita_override=material_fita,
            operacoes=operacoes,
        )
        return build_chapa(spec, origin, size)

    @classmethod
    def build_tampo_superior(
        cls,
        name: str,
        origin: tuple[float, float, float],
        size: tuple[float, float, float],
        material: str,
        color: tuple[float, float, float] | None = None,
        fita_c1: bool = True,
        fita_c2: bool = False,
        fita_l1: bool = False,
        fita_l2: bool = False,
        material_fita: str | None = None,
        cor_fita: tuple[float, float, float] | None = None,
        operacoes: list[dict[str, Any]] | None = None,
        ctx: ModuloMaterialContext | None = None,
    ) -> Group:
        """Universal canonical object: Closed Carcass Top Panel."""
        if ctx is not None:
            spec = ChapaSpec.resolve(
                nome=name,
                papel=PapelChapa.TAMPO_SUPERIOR,
                ctx=ctx,
                material_override=material,
                fita_override=(fita_c1, fita_c2, fita_l1, fita_l2) if (fita_c1, fita_c2, fita_l1, fita_l2) != (True, False, False, False) else None,
                material_fita_override=material_fita,
                operacoes=operacoes,
            )
            return build_chapa(spec, origin, size)

        spec = ChapaSpec.resolve(
            nome=name,
            papel=PapelChapa.TAMPO_SUPERIOR,
            ctx=ModuloMaterialContext(material_caixa=material, material_fita_caixa=material_fita),
            material_override=material,
            fita_override=(fita_c1, fita_c2, fita_l1, fita_l2),
            material_fita_override=material_fita,
            operacoes=operacoes,
        )
        return build_chapa(spec, origin, size)

    @classmethod
    def build_fundo(
        cls,
        name: str,
        origin: tuple[float, float, float],
        size: tuple[float, float, float],
        material: str | None = None,
        color: tuple[float, float, float] | None = None,
        operacoes: list[dict[str, Any]] | None = None,
        ctx: ModuloMaterialContext | None = None,
    ) -> Group:
        """Universal canonical object: Back Panel (6mm or 15mm, grooved or surface-mounted)."""
        mat = material or "MDF Fundo 6mm"
        if ctx is not None:
            spec = ChapaSpec.resolve(
                nome=name,
                papel=PapelChapa.FUNDO,
                ctx=ctx,
                material_override=mat,
                fita_override=(False, False, False, False),
                operacoes=operacoes,
            )
            cor_mat = color or cls.get_material_color(spec.material)
            return build_chapa(spec, origin, size, color=cor_mat)
        cor = color or (0.88, 0.88, 0.88)
        spec = ChapaSpec.resolve(
            nome=name,
            papel=PapelChapa.FUNDO,
            ctx=ModuloMaterialContext(material_caixa=mat),
            material_override=mat,
            fita_override=(False, False, False, False),
            operacoes=operacoes,
        )
        return build_chapa(spec, origin, size, color=cor)

    @classmethod
    def build_divisoria(
        cls,
        name: str,
        origin: tuple[float, float, float],
        size: tuple[float, float, float],
        material: str,
        color: tuple[float, float, float] | None = None,
        fita_c1: bool = True,
        fita_c2: bool = False,
        fita_l1: bool = False,
        fita_l2: bool = False,
        material_fita: str | None = None,
        cor_fita: tuple[float, float, float] | None = None,
        operacoes: list[dict[str, Any]] | None = None,
        cavilha_topo_superior: bool = False,
        cavilha_topo_inferior: bool = False,
        afastamento_cavilha_frontal_mm: float = 50.0,
        afastamento_cavilha_traseiro_mm: float = 50.0,
        ctx: ModuloMaterialContext | None = None,
    ) -> Group:
        """Universal canonical object: Internal vertical intermediate divider for any cabinet.

        Allows generating technical dowel drilling on top (upper end) and/or bottom (lower end).
        """
        ops_list: list[dict[str, Any]] = list(operacoes) if operacoes else []
        if cavilha_topo_superior or cavilha_topo_inferior:
            from ..production.machining import make_vertical_divider_joint_holes
            prof_div_mm = abs(size[1]) * 1000.0
            esp_div_mm = abs(size[0]) * 1000.0
            div_ops = make_vertical_divider_joint_holes(
                prof_divisoria_mm=prof_div_mm,
                esp_divisoria_mm=esp_div_mm,
                furacao_cima=cavilha_topo_superior,
                furacao_baixo=cavilha_topo_inferior,
                afastamento_frontal_mm=afastamento_cavilha_frontal_mm,
                afastamento_traseiro_mm=afastamento_cavilha_traseiro_mm,
            )
            for dop in div_ops:
                ops_list.append(dop.to_dict())

        if ctx is None:
            ctx = ModuloMaterialContext(material_caixa=material, material_fita_caixa=material_fita)
        spec = ChapaSpec.resolve(
            nome=name,
            papel=PapelChapa.DIVISORIA_VERTICAL,
            ctx=ctx,
            material_override=material,
            fita_override=(fita_c1, fita_c2, fita_l1, fita_l2) if (fita_c1, fita_c2, fita_l1, fita_l2) != (True, False, False, False) else None,
            material_fita_override=material_fita,
            operacoes=ops_list,
        )
        return build_chapa(
            spec,
            origin,
            size,
            color=color,
            material_fita=spec.material_fita,
            cor_fita=cor_fita,
            espessura_fita=spec.espessura_fita,
            operacoes=spec.operacoes,
        )

    @classmethod
    def build_divisoria_horizontal(
        cls,
        name: str,
        origin: tuple[float, float, float],
        size: tuple[float, float, float],
        material: str,
        color: tuple[float, float, float] | None = None,
        fita_c1: bool = True,
        fita_c2: bool = False,
        fita_l1: bool = False,
        fita_l2: bool = False,
        material_fita: str | None = None,
        cor_fita: tuple[float, float, float] | None = None,
        operacoes: list[dict[str, Any]] | None = None,
        ctx: ModuloMaterialContext | None = None,
    ) -> Group:
        """Universal canonical object: Fixed horizontal intermediate divider separating niches/openings."""
        if ctx is None:
            ctx = ModuloMaterialContext(material_caixa=material, material_fita_caixa=material_fita)
        spec = ChapaSpec.resolve(
            nome=name,
            papel=PapelChapa.DIVISORIA_HORIZONTAL,
            ctx=ctx,
            material_override=material,
            fita_override=(fita_c1, fita_c2, fita_l1, fita_l2) if (fita_c1, fita_c2, fita_l1, fita_l2) != (True, False, False, False) else None,
            material_fita_override=material_fita,
            operacoes=operacoes,
        )
        return build_chapa(
            spec,
            origin,
            size,
            color=color,
            material_fita=spec.material_fita,
            cor_fita=cor_fita,
            espessura_fita=spec.espessura_fita,
            operacoes=spec.operacoes,
        )

    @classmethod
    def build_travessa_peca(
        cls,
        name: str,
        origin: tuple[float, float, float],
        size: tuple[float, float, float],
        material: str,
        color: tuple[float, float, float] | None = None,
        fita_c1: bool = True,
        fita_c2: bool = False,
        fita_l1: bool = False,
        fita_l2: bool = False,
        material_fita: str | None = None,
        cor_fita: tuple[float, float, float] | None = None,
        operacoes: list[dict[str, Any]] | None = None,
        ctx: ModuloMaterialContext | None = None,
    ) -> Group:
        """Universal canonical object: Structural Stretcher (flat or upright)."""
        if ctx is not None:
            spec = ChapaSpec.resolve(
                nome=name,
                papel=PapelChapa.TRAVESSA,
                ctx=ctx,
                material_override=material,
                fita_override=(fita_c1, fita_c2, fita_l1, fita_l2) if (fita_c2 or fita_l1 or fita_l2 or not fita_c1) else None,
                material_fita_override=material_fita,
                operacoes=operacoes,
            )
            cor_mat = color or cls.get_material_color(spec.material)
            cor_f = cor_fita or (cls.get_material_color(spec.material_fita) if spec.material_fita else None)
            return build_chapa(spec, origin, size, color=cor_mat, cor_fita=cor_f)
        cor_mat = color or cls.get_material_color(material)
        cor_f = cor_fita or (cls.get_material_color(material_fita) if material_fita else None)
        spec = ChapaSpec.resolve(
            nome=name,
            papel=PapelChapa.TRAVESSA,
            ctx=ModuloMaterialContext(material_caixa=material, material_fita_caixa=material_fita),
            material_override=material,
            fita_override=(fita_c1, fita_c2, fita_l1, fita_l2),
            material_fita_override=material_fita,
            operacoes=operacoes,
        )
        return build_chapa(spec, origin, size, color=cor_mat, cor_fita=cor_f)

    @classmethod
    def build_porta_esquerda(
        cls,
        name: str,
        origin: tuple[float, float, float],
        size: tuple[float, float, float],
        material: str,
        color: tuple[float, float, float] | None = None,
        fita_c1: bool = True,
        fita_c2: bool = True,
        fita_l1: bool = True,
        fita_l2: bool = True,
        material_fita: str | None = None,
        cor_fita: tuple[float, float, float] | None = None,
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto",
        puxador_pos: str = "padrao",
        desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        is_upper: bool = False,
        gerar_furacao: bool = True,
        operacoes: list[dict[str, Any]] | None = None,
        door_side: str | None = None,
        ctx: ModuloMaterialContext | None = None,
    ) -> Group:
        """Universal canonical object: Left Hinged Door (hinges on the left, handle on the right).

        ``door_side`` allows marking the part as ``"single"`` (single door), in which
        case the opening side can still be inverted by the master module.
        """
        ops = list(operacoes) if operacoes is not None else []
        if gerar_furacao and not ops:
            from ..production.machining import make_hinge_cup_holes
            alt_porta_mm = size[2] * 1000.0
            larg_porta_mm = size[0] * 1000.0
            ops = [o.to_dict() for o in make_hinge_cup_holes(
                altura_porta_mm=alt_porta_mm,
                lado_dobradica="esquerda",
                largura_porta_mm=larg_porta_mm,
            )]

        if ctx is None:
            ctx = ModuloMaterialContext(material_frentes=material, material_fita_frentes=material_fita)
        spec = ChapaSpec.resolve(
            nome=name,
            papel=PapelChapa.PORTA,
            ctx=ctx,
            material_override=material,
            fita_override=(fita_c1, fita_c2, fita_l1, fita_l2) if not (fita_c1 and fita_c2 and fita_l1 and fita_l2) else None,
            material_fita_override=material_fita,
            operacoes=ops,
        )
        return build_chapa(
            spec,
            origin,
            size,
            color=color,
            material_fita=spec.material_fita,
            cor_fita=cor_fita,
            espessura_fita=spec.espessura_fita,
            puxador_tipo=puxador_tipo,
            puxador_cor=puxador_cor,
            puxador_pos=puxador_pos,
            desconto_perfil_mm=desconto_perfil_mm,
            perfil_modelo=perfil_modelo,
            door_side=door_side or "left",
            is_upper=is_upper,
            operacoes=spec.operacoes,
        )

    @classmethod
    def build_porta_direita(
        cls,
        name: str,
        origin: tuple[float, float, float],
        size: tuple[float, float, float],
        material: str,
        color: tuple[float, float, float] | None = None,
        fita_c1: bool = True,
        fita_c2: bool = True,
        fita_l1: bool = True,
        fita_l2: bool = True,
        material_fita: str | None = None,
        cor_fita: tuple[float, float, float] | None = None,
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto",
        puxador_pos: str = "padrao",
        desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        is_upper: bool = False,
        gerar_furacao: bool = True,
        operacoes: list[dict[str, Any]] | None = None,
        door_side: str | None = None,
        ctx: ModuloMaterialContext | None = None,
    ) -> Group:
        """Universal canonical object: Right Hinged Door (hinges on the right, handle on the left)."""
        ops = list(operacoes) if operacoes is not None else []
        if gerar_furacao and not ops:
            from ..production.machining import make_hinge_cup_holes
            alt_porta_mm = size[2] * 1000.0
            larg_porta_mm = size[0] * 1000.0
            ops = [o.to_dict() for o in make_hinge_cup_holes(
                altura_porta_mm=alt_porta_mm,
                lado_dobradica="direita",
                largura_porta_mm=larg_porta_mm,
            )]

        if ctx is None:
            ctx = ModuloMaterialContext(material_frentes=material, material_fita_frentes=material_fita)
        spec = ChapaSpec.resolve(
            nome=name,
            papel=PapelChapa.PORTA,
            ctx=ctx,
            material_override=material,
            fita_override=(fita_c1, fita_c2, fita_l1, fita_l2) if not (fita_c1 and fita_c2 and fita_l1 and fita_l2) else None,
            material_fita_override=material_fita,
            operacoes=ops,
        )
        return build_chapa(
            spec,
            origin,
            size,
            color=color,
            material_fita=spec.material_fita,
            cor_fita=cor_fita,
            espessura_fita=spec.espessura_fita,
            puxador_tipo=puxador_tipo,
            puxador_cor=puxador_cor,
            puxador_pos=puxador_pos,
            desconto_perfil_mm=desconto_perfil_mm,
            perfil_modelo=perfil_modelo,
            door_side="right",
            is_upper=is_upper,
            operacoes=spec.operacoes,
        )

    @classmethod
    def build_porta_basculante(
        cls,
        name: str,
        origin: tuple[float, float, float],
        size: tuple[float, float, float],
        material: str,
        color: tuple[float, float, float] | None = None,
        fita_c1: bool = True,
        fita_c2: bool = True,
        fita_l1: bool = True,
        fita_l2: bool = True,
        material_fita: str | None = None,
        cor_fita: tuple[float, float, float] | None = None,
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto",
        puxador_pos: str = "padrao",
        desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        is_upper: bool = True,
        gerar_furacao: bool = True,
        operacoes: list[dict[str, Any]] | None = None,
        ctx: ModuloMaterialContext | None = None,
    ) -> Group:
        """Universal canonical object: Flip-Up Door (top-opening with gas piston, handle at the bottom edge)."""
        ops = list(operacoes) if operacoes is not None else []
        if gerar_furacao and not ops:
            larg_porta_mm = size[0] * 1000.0
            alt_porta_mm = size[2] * 1000.0
            # Hinge cups at the top of the flip-up door (100mm from side ends, 21.5mm from top edge)
            recuo_topo_mm = 21.5
            y_caneco = alt_porta_mm - recuo_topo_mm
            pontos_x = [100.0, max(132.0, larg_porta_mm - 100.0)]
            if larg_porta_mm > 900.0:
                pontos_x.insert(1, larg_porta_mm / 2.0)
            for idx, px in enumerate(pontos_x, 1):
                ops.append({
                    "tipo": "furo",
                    "face": "traseira",
                    "x": px,
                    "y": y_caneco,
                    "diametro": 35.0,
                    "profundidade": 12.0,
                    "descricao": f"Caneco Basculante {idx} (Ø35mm)",
                })
                ops.append({
                    "tipo": "furo",
                    "face": "traseira",
                    "x": px - 22.5,
                    "y": y_caneco - 9.5,
                    "diametro": 2.5,
                    "profundidade": 2.5,
                    "descricao": f"Marcação Parafuso Basculante {idx}A (Ø2.5mm)",
                })
                ops.append({
                    "tipo": "furo",
                    "face": "traseira",
                    "x": px + 22.5,
                    "y": y_caneco - 9.5,
                    "diametro": 2.5,
                    "profundidade": 2.5,
                    "descricao": f"Marcação Parafuso Basculante {idx}B (Ø2.5mm)",
                })

        if ctx is None:
            ctx = ModuloMaterialContext(material_frentes=material, material_fita_frentes=material_fita)
        spec = ChapaSpec.resolve(
            nome=name,
            papel=PapelChapa.PORTA,
            ctx=ctx,
            material_override=material,
            fita_override=(fita_c1, fita_c2, fita_l1, fita_l2) if not (fita_c1 and fita_c2 and fita_l1 and fita_l2) else None,
            material_fita_override=material_fita,
            operacoes=ops,
        )
        return build_chapa(
            spec,
            origin,
            size,
            color=color,
            material_fita=spec.material_fita,
            cor_fita=cor_fita,
            espessura_fita=spec.espessura_fita,
            puxador_tipo=puxador_tipo,
            puxador_cor=puxador_cor,
            puxador_pos=puxador_pos,
            desconto_perfil_mm=desconto_perfil_mm,
            perfil_modelo=perfil_modelo,
            door_side="flap",
            is_upper=is_upper,
            operacoes=spec.operacoes,
        )

    @classmethod
    def build_frente_gaveta(
        cls,
        name: str,
        origin: tuple[float, float, float],
        size: tuple[float, float, float],
        material: str,
        color: tuple[float, float, float] | None = None,
        fita_c1: bool = True,
        fita_c2: bool = True,
        fita_l1: bool = True,
        fita_l2: bool = True,
        material_fita: str | None = None,
        cor_fita: tuple[float, float, float] | None = None,
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto",
        puxador_pos: str = "padrao",
        desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        operacoes: list[dict[str, Any]] | None = None,
        ctx: ModuloMaterialContext | None = None,
    ) -> Group:
        """Universal canonical object: External Drawer Front."""
        if ctx is None:
            ctx = ModuloMaterialContext(material_frentes=material, material_fita_frentes=material_fita)
        spec = ChapaSpec.resolve(
            nome=name,
            papel=PapelChapa.FRENTE_GAVETA,
            ctx=ctx,
            material_override=material,
            fita_override=(fita_c1, fita_c2, fita_l1, fita_l2) if not (fita_c1 and fita_c2 and fita_l1 and fita_l2) else None,
            material_fita_override=material_fita,
            operacoes=operacoes,
        )
        return build_chapa(
            spec,
            origin,
            size,
            color=color,
            material_fita=spec.material_fita,
            cor_fita=cor_fita,
            espessura_fita=spec.espessura_fita,
            puxador_tipo=puxador_tipo,
            puxador_cor=puxador_cor,
            puxador_pos=puxador_pos,
            desconto_perfil_mm=desconto_perfil_mm,
            perfil_modelo=perfil_modelo,
            door_side="drawer",
            operacoes=spec.operacoes,
        )

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
        """Generates the internal drawer box parts by delegating to CanonicalDrawerBuilder.

        Kept for full backward compatibility, ensuring CanonicalDrawerBuilder
        is the single source of truth for the drawer box and its bottoms.
        """
        from .drawers import CanonicalDrawerBuilder
        return CanonicalDrawerBuilder.build_caixa_gaveta(
            prefixo=prefixo,
            x_caixa=x_caixa,
            y_caixa=y_caixa,
            z_caixa=z_caixa,
            larg_caixa=larg_caixa,
            prof_caixa=prof_caixa,
            alt_caixa=alt_caixa,
            material_gaveta=material_gaveta,
            esp_gaveta_mm=esp_gaveta_mm,
            material_fita_gaveta=material_fita_gaveta,
            tipo_fundo_gaveta=tipo_fundo_gaveta,
            material_fundo_gaveta=material_fundo_gaveta,
            esp_fundo_gaveta_mm=esp_fundo_gaveta_mm,
        )

    @classmethod
    def build_caixa_modular(
        cls,
        prefixo: str,
        largura_mm: float,
        altura_mm: float,
        prof_mm: float,
        esp_mm: float = 15.0,
        rodape_mm: float = 0.0,
        tipo_topo: str = "fechado",  # "fechado" (top panel) or "travessas" (front/rear stretchers)
        material: str = "MDF Branco TX 15mm",
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        # Stretcher parameters (when tipo_topo == "travessas")
        larg_travessa_frontal_mm: float = 70.0,
        larg_travessa_traseira_mm: float = 70.0,
        travessa_frontal_em_pe: bool = False,
        travessa_traseira_em_pe: bool = False,
        material_travessas: str | None = None,
        esp_travessas_mm: float | None = None,
        fita_travessas_modo: str = "frontal_1L",
        fita_travessas_faces: dict[str, bool] | None = None,
        material_fita_travessas: str | None = None,
        # Carcass edge banding (Sides, Bottom, and Top)
        fita_caixa_modo: str = "frontal_1L",
        material_fita_caixa: str | None = None,
        # TrazoMob Back Panel parameters
        tem_fundo: bool = True,
        tipo_fundo: str = "rasgo",  # "rasgo" (grooved), "sobreposto" (surface-mounted), "sem_fundo" (no back panel)
        esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0,
        prof_rasgo_mm: float = 5.0,
        folga_fundo_mm: float = 2.0,
        material_fundo: str | None = None,
        # Technical drilling and Joining Hardware
        gerar_furacao: bool = True,
        dispositivo_fixacao: str = "minifix_cavilha",
        afastamento_fixacao_frontal_mm: float = 50.0,
        afastamento_fixacao_traseiro_mm: float = 50.0,
        afastamento_cavilha_frontal_mm: float = 100.0,
        afastamento_cavilha_traseiro_mm: float = 100.0,
        alturas_prateleiras_mm: list[float] | None = None,
        prof_prateleira_mm: float | None = None,
        recuo_prateleira_frontal_mm: float = 0.0,
        alturas_calcos_esq_mm: list[float] | None = None,
        alturas_calcos_dir_mm: list[float] | None = None,
        tipo_fixacao_calco: str = "parafuso",  # "parafuso" (Ø2.5x2.5mm pilot mark) or "euro" (Ø5.0x11.5mm)
        # Vertical dividers: X centers (relative to the base, ox + E) to
        # transfer dowels from the divider's bottom end to the bottom panel.
        divisorias_x_mm: list[float] | None = None,
        divisorias_prof_mm: float | None = None,
        divisorias_esp_mm: float | None = None,
        ctx: ModuloMaterialContext | None = None,
    ) -> tuple[list[Group], dict]:
        """Core universal engine for parametric construction of cabinetry carcasses.

        Standardizes carcass fabrication for tall/wall cabinets and wardrobes (with closed top)
        as well as kitchen base cabinets (with top stretchers).

        Generates:
        - Left Side and Right Side
        - Bottom Panel
        - Closed Top Panel (if tipo_topo == 'fechado')
          OR Front and Rear Stretchers (if tipo_topo == 'travessas')
        - Structural Front Toe Kick (if rodape_mm > 0)
        - TrazoMob recessed/surface-mounted Back Panel (if tem_fundo and tipo_fundo != 'sem_fundo')
        - Complete Machining Operations:
          * Cam lock / Dowel / Confirmat joints (on the sides for bottom and top)
          * 6mm back panel grooves/dados (on the sides, bottom, and top)
        """
        ox, oy, oz = offset
        L, A, P, E, R = largura_mm / 1000.0, altura_mm / 1000.0, prof_mm / 1000.0, esp_mm / 1000.0, rodape_mm / 1000.0
        cor = cls.get_material_color(material)
        altura_caixa = A - R
        largura_interna = L - 2 * E
        LTF = larg_travessa_frontal_mm / 1000.0
        LTT = larg_travessa_traseira_mm / 1000.0
        E_trav = (esp_travessas_mm / 1000.0) if esp_travessas_mm is not None else E

        # Carcass edge banding resolution (Sides, Bottom, and Top)
        modo_fita_cx = (fita_caixa_modo or "frontal_1L").lower()
        if modo_fita_cx == "sem_fita":
            f_cx_c1, f_cx_c2, f_cx_l1, f_cx_l2 = False, False, False, False
        elif modo_fita_cx == "4l":
            f_cx_c1, f_cx_c2, f_cx_l1, f_cx_l2 = True, True, True, True
        elif modo_fita_cx == "2l":
            # 2 long edges (front and rear)
            f_cx_c1, f_cx_c2, f_cx_l1, f_cx_l2 = True, True, False, False
        else:
            # "frontal_1L" (Cabinetry standard: visible front edge)
            f_cx_c1, f_cx_c2, f_cx_l1, f_cx_l2 = True, False, True, False

        # Carcass edge banding material and color
        mat_fita_cx = material_fita_caixa or material
        cor_fita_cx = cls.get_material_color(mat_fita_cx) if material_fita_caixa else None

        # Assembly hardware drilling and groove machining on the parts
        ops_lateral = []
        ops_base = []
        ops_tampo = []

        eff_tipo_fundo = "sem_fundo" if not tem_fundo else tipo_fundo

        if gerar_furacao:
            from ..production.machining import (
                make_back_panel_groove,
                make_cabinet_joint_holes,
                make_horizontal_board_edge_holes,
            )
            usar_mini = ("minifix" in str(dispositivo_fixacao).lower())

            # 1. Bottom-to-side joint drilling
            # make_cabinet_joint_holes returns connectors along the joint depth
            ops_lateral.extend([
                o.to_dict() for o in make_cabinet_joint_holes(
                    comprimento_junta_mm=prof_mm,
                    posicao_borda_mm=(esp_mm / 2.0),
                    face="traseira",
                    usar_minifix=usar_mini,
                    afastamento_frontal_mm=afastamento_fixacao_frontal_mm,
                    afastamento_traseiro_mm=afastamento_fixacao_traseiro_mm,
                    afastamento_cavilha_frontal_mm=afastamento_cavilha_frontal_mm,
                    afastamento_cavilha_traseiro_mm=afastamento_cavilha_traseiro_mm,
                    dispositivo_fixacao=dispositivo_fixacao,
                    espessura_chapa_mm=esp_mm,
                )
            ])

            # Drilling on the Bottom Panel (face_tambor="topo" so cam housings sit on the inner/upper face of the base, facing inside the cabinet)
            ops_base_e, ops_base_d, ops_base_f = make_horizontal_board_edge_holes(
                prof_chapa_mm=prof_mm,
                largura_chapa_mm=(largura_interna * 1000.0),
                esp_chapa_mm=esp_mm,
                afastamento_fixacao_frontal_mm=afastamento_fixacao_frontal_mm,
                afastamento_fixacao_traseiro_mm=afastamento_fixacao_traseiro_mm,
                afastamento_cavilha_frontal_mm=afastamento_cavilha_frontal_mm,
                afastamento_cavilha_traseiro_mm=afastamento_cavilha_traseiro_mm,
                usar_minifix=usar_mini,
                dispositivo_fixacao=dispositivo_fixacao,
                face_tambor="topo",
            )
            ops_base.extend([o.to_dict() for o in ops_base_e + ops_base_d + ops_base_f])

            # 1b. Transfer of divider dowels to the bottom panel:
            # matching holes on the upper face of the base (Ø8 x 11mm),
            # aligned with the holes on the bottom end of each divider.
            if divisorias_x_mm:
                from ..production.machining import make_vertical_divider_joint_holes
                prof_div_mm = float(divisorias_prof_mm or (prof_mm - recuo_fundo_mm))
                esp_div_mm = float(divisorias_esp_mm or esp_mm)
                prof_furo_base_mm = min(11.0, max(4.0, float(esp_mm) - 2.0))
                div_base_ops = make_vertical_divider_joint_holes(
                    prof_divisoria_mm=prof_div_mm,
                    esp_divisoria_mm=esp_div_mm,
                    furacao_cima=False,
                    furacao_baixo=True,
                    afastamento_frontal_mm=50.0,
                    afastamento_traseiro_mm=50.0,
                )
                for d_idx, x_div_mm in enumerate(divisorias_x_mm, 1):
                    for op_idx, dop in enumerate(div_base_ops, 1):
                        ops_base.append({
                            "tipo": "furo",
                            "face": "topo",
                            "x": round(float(x_div_mm), 2),
                            "y": round(float(dop.x), 2),
                            "diametro": float(dop.diametro),
                            "profundidade": prof_furo_base_mm,
                            "largura": 0.0,
                            "comprimento": 0.0,
                            "descricao": (
                                f"Cavilha Divisoria {d_idx} Base {op_idx} "
                                f"(Ø{int(dop.diametro)}mm x {int(prof_furo_base_mm)}mm)"
                            ),
                        })

            # 2. If closed top, top-to-side joint drilling on the side and top panel
            if tipo_topo == "fechado":
                pos_topo_mm = max(0.0, (altura_caixa * 1000.0) - (esp_mm / 2.0))
                for o in make_cabinet_joint_holes(
                    comprimento_junta_mm=prof_mm,
                    posicao_borda_mm=pos_topo_mm,
                    face="traseira",
                    usar_minifix=usar_mini,
                    afastamento_frontal_mm=afastamento_fixacao_frontal_mm,
                    afastamento_traseiro_mm=afastamento_fixacao_traseiro_mm,
                    afastamento_cavilha_frontal_mm=afastamento_cavilha_frontal_mm,
                    afastamento_cavilha_traseiro_mm=afastamento_cavilha_traseiro_mm,
                    dispositivo_fixacao=dispositivo_fixacao,
                    espessura_chapa_mm=esp_mm,
                ):
                    ops_lateral.append(o.to_dict())

                # Drilling on the Top Panel (face_tambor="base" so cam housings sit on the inner/lower face of the top, facing inside the cabinet)
                ops_tampo_e, ops_tampo_d, ops_tampo_f = make_horizontal_board_edge_holes(
                    prof_chapa_mm=prof_mm,
                    largura_chapa_mm=(largura_interna * 1000.0),
                    esp_chapa_mm=esp_mm,
                    afastamento_fixacao_frontal_mm=afastamento_fixacao_frontal_mm,
                    afastamento_fixacao_traseiro_mm=afastamento_fixacao_traseiro_mm,
                    afastamento_cavilha_frontal_mm=afastamento_cavilha_frontal_mm,
                    afastamento_cavilha_traseiro_mm=afastamento_cavilha_traseiro_mm,
                    usar_minifix=usar_mini,
                    dispositivo_fixacao=dispositivo_fixacao,
                    face_tambor="base",
                )
                ops_tampo.extend([o.to_dict() for o in ops_tampo_e + ops_tampo_d + ops_tampo_f])

            # 3. If recessed grooved back panel, generate groove machining on the carcass parts
            # Only replaces recuo_fundo_mm with rear stretcher thickness when it is upright
            esp_traseira_calc_mm = (E_trav * 1000.0) if (tipo_topo != "fechado" and travessa_traseira_em_pe) else 0.0
            recuo_canal_efetivo_mm = esp_traseira_calc_mm if esp_traseira_calc_mm > 0 else recuo_fundo_mm

            if eff_tipo_fundo == "rasgo":
                canal_lateral = make_back_panel_groove(
                    comprimento_mm=(altura_caixa * 1000.0),
                    afastamento_traseiro_mm=recuo_canal_efetivo_mm,
                    largura_canal_mm=esp_fundo_mm,
                    profundidade_canal_mm=prof_rasgo_mm,
                    face="traseira",
                )
                ops_lateral.append(canal_lateral.to_dict())

                canal_base = make_back_panel_groove(
                    comprimento_mm=(largura_interna * 1000.0),
                    afastamento_traseiro_mm=recuo_canal_efetivo_mm,
                    largura_canal_mm=esp_fundo_mm,
                    profundidade_canal_mm=prof_rasgo_mm,
                    face="traseira",
                )
                ops_base.append(canal_base.to_dict())

                if tipo_topo == "fechado":
                    canal_tampo = make_back_panel_groove(
                        comprimento_mm=(largura_interna * 1000.0),
                        afastamento_traseiro_mm=recuo_canal_efetivo_mm,
                        largura_canal_mm=esp_fundo_mm,
                        profundidade_canal_mm=prof_rasgo_mm,
                        face="traseira",
                    )
                    ops_tampo.append(canal_tampo.to_dict())

            # 4. Dowel drilling for internal shelves transferred to the inner faces of the sides
            if alturas_prateleiras_mm:
                from ..production.machining import make_shelf_side_holes
                prof_p_mm = prof_prateleira_mm if prof_prateleira_mm is not None else (prof_mm - recuo_canal_efetivo_mm - 20.0)
                for alt_p_z in alturas_prateleiras_mm:
                    ops_prat_lat = make_shelf_side_holes(
                        pos_z_na_lateral_mm=alt_p_z,
                        prof_prateleira_mm=prof_p_mm,
                        recuo_frontal_mm=recuo_prateleira_frontal_mm,
                        afastamento_mm=50.0,
                        esp_prateleira_mm=esp_mm,
                        face="traseira",
                    )
                    ops_lateral.extend([o.to_dict() for o in ops_prat_lat])

        # Top closure: Closed Top VS Stretchers
        ops_trav_f = []
        ops_trav_t = []
        if tipo_topo != "fechado" and gerar_furacao:
            from ..production.machining import MachiningOp, make_stretcher_joint_holes
            larg_trav_f_mm = (LTF * 1000.0) if not travessa_frontal_em_pe else (E_trav * 1000.0)
            larg_trav_t_mm = (LTT * 1000.0) if not travessa_traseira_em_pe else (E_trav * 1000.0)
            compr_trav_mm = largura_interna * 1000.0

            # 1. Machining on the stretchers themselves (2 holes per end on the stretcher end face at 25mm from each edge)
            # For flat stretchers, cam lock drum face is "base" (underneath). For upright stretchers, face "traseira" (inside).
            face_tb_f = "base" if not travessa_frontal_em_pe else "traseira"
            ops_trav_f = [
                o.to_dict() for o in make_stretcher_joint_holes(
                    largura_travessa_mm=(LTF * 1000.0) if not travessa_frontal_em_pe else (LTF * 1000.0),
                    esp_travessa_mm=(E_trav * 1000.0),
                    face=face_tb_f,
                    usar_minifix=usar_mini,
                    comprimento_travessa_mm=compr_trav_mm,
                    eh_travessa=True,
                    dispositivo_fixacao=dispositivo_fixacao,
                )
            ]

            face_tb_t = "base" if not travessa_traseira_em_pe else "frontal"
            ops_trav_t = [
                o.to_dict() for o in make_stretcher_joint_holes(
                    largura_travessa_mm=(LTT * 1000.0) if not travessa_traseira_em_pe else (LTT * 1000.0),
                    esp_travessa_mm=(E_trav * 1000.0),
                    face=face_tb_t,
                    usar_minifix=usar_mini,
                    comprimento_travessa_mm=compr_trav_mm,
                    eh_travessa=True,
                    dispositivo_fixacao=dispositivo_fixacao,
                )
            ]

            # 2. Matching machining on the carcass sides (2 holes per stretcher on the sides)
            if not travessa_frontal_em_pe:
                # Flat: spread along Y from 0 to LTF, Z height at the center of the stretcher thickness
                pos_z_tf_mm = (altura_caixa * 1000.0) - (E_trav * 1000.0 / 2.0)
                pos_y_tf_base_mm = 0.0
                ops_lat_tf = make_stretcher_joint_holes(
                    largura_travessa_mm=LTF * 1000.0,
                    esp_travessa_mm=(E_trav * 1000.0),
                    face="traseira",
                    usar_minifix=usar_mini,
                    eh_travessa=False,
                    dispositivo_fixacao=dispositivo_fixacao,
                    posicao_lateral_y_mm=pos_y_tf_base_mm,
                    posicao_lateral_z_mm=pos_z_tf_mm,
                )
            else:
                # Upright: thickness E_trav along Y (from 0 to E_trav), Z height spread from (A - LTF) to A
                # Holes are placed 25mm from the bottom edge and 25mm from the top edge of the stretcher along Z
                p1_z = (altura_caixa * 1000.0) - (LTF * 1000.0) + 25.0
                p2_z = (altura_caixa * 1000.0) - 25.0
                py_tf = E_trav * 1000.0 / 2.0
                ops_lat_tf = []
                disp = str(dispositivo_fixacao or "").lower()
                eh_somente_cav = disp in ("cavilha", "apenas_cavilha", "apenas_cavilhas", "somente_cavilha")
                eh_somente_paraf = disp in ("soberba", "apenas_parafuso", "somente_parafuso", "somente_parafusos", "apenas_parafusos")
                eh_mini = "minifix" in disp and not eh_somente_cav and not eh_somente_paraf
                eh_paraf = ("parafuso" in disp or "confirmat" in disp or "soberba" in disp) and not eh_somente_cav
                for pz_i, is_p1 in [(p1_z, True), (p2_z, False)]:
                    if eh_mini:
                        if is_p1:
                            ops_lat_tf.append(MachiningOp(tipo="furo", face="traseira", x=py_tf, y=pz_i, diametro=5.0, profundidade=11.0, descricao="Pino Minifix Junção Travessa Em Pe (Ø5mm x 11mm)"))
                        else:
                            ops_lat_tf.append(MachiningOp(tipo="furo", face="traseira", x=py_tf, y=pz_i, diametro=8.0, profundidade=11.0, descricao="Cavilha Junção Travessa Em Pe (Ø8mm x 11mm)"))
                    elif eh_somente_paraf:
                        ops_lat_tf.append(MachiningOp(tipo="furo", face="traseira", x=py_tf, y=pz_i, diametro=5.0, profundidade=15.0, descricao="Furo Parafuso Travessa Em Pe Passante (Ø5mm)"))
                    elif eh_somente_cav:
                        ops_lat_tf.append(MachiningOp(tipo="furo", face="traseira", x=py_tf, y=pz_i, diametro=8.0, profundidade=11.0, descricao="Cavilha Junção Travessa Em Pe (Ø8mm x 11mm)"))
                    else:
                        if is_p1:
                            ops_lat_tf.append(MachiningOp(tipo="furo", face="traseira", x=py_tf, y=pz_i, diametro=5.0, profundidade=15.0, descricao="Furo Parafuso Travessa Em Pe Passante (Ø5mm)"))
                        else:
                            ops_lat_tf.append(MachiningOp(tipo="furo", face="traseira", x=py_tf, y=pz_i, diametro=8.0, profundidade=11.0, descricao="Cavilha Junção Travessa Em Pe (Ø8mm x 11mm)"))

            for o in ops_lat_tf:
                ops_lateral.append(o.to_dict())

            if not travessa_traseira_em_pe:
                pos_z_tt_mm = (altura_caixa * 1000.0) - (E_trav * 1000.0 / 2.0)
                pos_y_tt_base_mm = prof_mm - (LTT * 1000.0)
                ops_lat_tt = make_stretcher_joint_holes(
                    largura_travessa_mm=LTT * 1000.0,
                    esp_travessa_mm=(E_trav * 1000.0),
                    face="traseira",
                    usar_minifix=usar_mini,
                    eh_travessa=False,
                    dispositivo_fixacao=dispositivo_fixacao,
                    posicao_lateral_y_mm=pos_y_tt_base_mm,
                    posicao_lateral_z_mm=pos_z_tt_mm,
                )
            else:
                p1_z = (altura_caixa * 1000.0) - (LTT * 1000.0) + 25.0
                p2_z = (altura_caixa * 1000.0) - 25.0
                py_tt = prof_mm - (E_trav * 1000.0 / 2.0)
                ops_lat_tt = []
                disp = str(dispositivo_fixacao or "").lower()
                eh_somente_cav = disp in ("cavilha", "apenas_cavilha", "apenas_cavilhas", "somente_cavilha")
                eh_somente_paraf = disp in ("soberba", "apenas_parafuso", "somente_parafuso", "somente_parafusos", "apenas_parafusos")
                eh_mini = "minifix" in disp and not eh_somente_cav and not eh_somente_paraf
                for pz_i, is_p1 in [(p1_z, True), (p2_z, False)]:
                    if eh_mini:
                        if is_p1:
                            ops_lat_tt.append(MachiningOp(tipo="furo", face="traseira", x=py_tt, y=pz_i, diametro=5.0, profundidade=11.0, descricao="Pino Minifix Junção Travessa Em Pe (Ø5mm x 11mm)"))
                        else:
                            ops_lat_tt.append(MachiningOp(tipo="furo", face="traseira", x=py_tt, y=pz_i, diametro=8.0, profundidade=11.0, descricao="Cavilha Junção Travessa Em Pe (Ø8mm x 11mm)"))
                    elif eh_somente_paraf:
                        ops_lat_tt.append(MachiningOp(tipo="furo", face="traseira", x=py_tt, y=pz_i, diametro=5.0, profundidade=15.0, descricao="Furo Parafuso Travessa Em Pe Passante (Ø5mm)"))
                    elif eh_somente_cav:
                        ops_lat_tt.append(MachiningOp(tipo="furo", face="traseira", x=py_tt, y=pz_i, diametro=8.0, profundidade=11.0, descricao="Cavilha Junção Travessa Em Pe (Ø8mm x 11mm)"))
                    else:
                        if is_p1:
                            ops_lat_tt.append(MachiningOp(tipo="furo", face="traseira", x=py_tt, y=pz_i, diametro=5.0, profundidade=15.0, descricao="Furo Parafuso Travessa Em Pe Passante (Ø5mm)"))
                        else:
                            ops_lat_tt.append(MachiningOp(tipo="furo", face="traseira", x=py_tt, y=pz_i, diametro=8.0, profundidade=11.0, descricao="Cavilha Junção Travessa Em Pe (Ø8mm x 11mm)"))

            for o in ops_lat_tt:
                ops_lateral.append(o.to_dict())

        # Specific operations for Left and Right Sides (e.g., hinge mounting plate marks)
        ops_lateral_esq = list(ops_lateral)
        ops_lateral_dir = list(ops_lateral)
        if gerar_furacao:
            from ..production.machining import make_hinge_plate_holes
            if alturas_calcos_esq_mm:
                ops_h_esq = make_hinge_plate_holes(
                    posicoes_y_mm=alturas_calcos_esq_mm,
                    recuo_borda_frontal_mm=37.0,
                    face="traseira",
                    tipo_fixacao=tipo_fixacao_calco,
                )
                ops_lateral_esq.extend([o.to_dict() for o in ops_h_esq])

            if alturas_calcos_dir_mm:
                ops_h_dir = make_hinge_plate_holes(
                    posicoes_y_mm=alturas_calcos_dir_mm,
                    recuo_borda_frontal_mm=37.0,
                    face="traseira",
                    tipo_fixacao=tipo_fixacao_calco,
                )
                ops_lateral_dir.extend([o.to_dict() for o in ops_h_dir])

        # Carcass material context creation
        ctx_modulo = ctx if ctx is not None else ModuloMaterialContext(
            material_caixa=material,
            material_fita_caixa=material_fita_caixa,
            fita_caixa_modo=fita_caixa_modo,
        )

        groups = [
            cls.build_lateral_esquerda(
                name=f"{prefixo} - Lateral Esquerda",
                origin=(ox, oy, oz + R),
                size=(E, P, altura_caixa),
                material=material,
                fita_c1=f_cx_c1, fita_c2=f_cx_c2, fita_l1=f_cx_l1, fita_l2=f_cx_l2,
                color=cor, material_fita=mat_fita_cx, cor_fita=cor_fita_cx,
                operacoes=ops_lateral_esq,
                ctx=ctx_modulo,
            ),
            cls.build_lateral_direita(
                name=f"{prefixo} - Lateral Direita",
                origin=(ox + L - E, oy, oz + R),
                size=(E, P, altura_caixa),
                material=material,
                fita_c1=f_cx_c1, fita_c2=f_cx_c2, fita_l1=f_cx_l1, fita_l2=f_cx_l2,
                color=cor, material_fita=mat_fita_cx, cor_fita=cor_fita_cx,
                operacoes=ops_lateral_dir,
                ctx=ctx_modulo,
            ),
            cls.build_base_inferior(
                name=f"{prefixo} - Base Inferior",
                origin=(ox + E, oy, oz + R),
                size=(largura_interna, P, E),
                material=material,
                fita_c1=f_cx_c1, fita_c2=f_cx_c2, fita_l1=f_cx_l1, fita_l2=f_cx_l2,
                color=cor, material_fita=mat_fita_cx, cor_fita=cor_fita_cx,
                operacoes=ops_base,
                ctx=ctx_modulo,
            ),
        ]

        if tipo_topo == "fechado":
            groups.append(cls.build_tampo_superior(
                name=f"{prefixo} - Tampo Superior",
                origin=(ox + E, oy, oz + A - E),
                size=(largura_interna, P, E),
                material=material,
                fita_c1=f_cx_c1, fita_c2=f_cx_c2, fita_l1=f_cx_l1, fita_l2=f_cx_l2,
                color=cor, material_fita=mat_fita_cx, cor_fita=cor_fita_cx,
                operacoes=ops_tampo,
                ctx=ctx_modulo,
            ))
        else:
            # Specific material and thickness for stretchers (if defined, otherwise inherits from carcass)
            mat_trav = material_travessas or material
            cor_trav = cls.get_material_color(mat_trav)
            mat_fita_tr = material_fita_travessas or mat_trav
            cor_fita_tr = cls.get_material_color(mat_fita_tr) if material_fita_travessas else None

            # Stretcher edge banding resolution
            modo_fita = (fita_travessas_modo or "frontal_1L").lower()
            if modo_fita == "sem_fita":
                f_c1_tf, f_c2_tf, f_l1_tf, f_l2_tf = False, False, False, False
                f_c1_tt, f_c2_tt, f_l1_tt, f_l2_tt = False, False, False, False
            elif modo_fita == "4l":
                f_c1_tf, f_c2_tf, f_l1_tf, f_l2_tf = True, True, True, True
                f_c1_tt, f_c2_tt, f_l1_tt, f_l2_tt = True, True, True, True
            elif modo_fita == "2l":
                f_c1_tf, f_c2_tf, f_l1_tf, f_l2_tf = True, True, False, False
                f_c1_tt, f_c2_tt, f_l1_tt, f_l2_tt = True, True, False, False
            elif modo_fita == "custom" and isinstance(fita_travessas_faces, dict):
                f_c1_tf = bool(fita_travessas_faces.get("fita_c1", True))
                f_c2_tf = bool(fita_travessas_faces.get("fita_c2", False))
                f_l1_tf = bool(fita_travessas_faces.get("fita_l1", False))
                f_l2_tf = bool(fita_travessas_faces.get("fita_l2", False))
                f_c1_tt = bool(fita_travessas_faces.get("fita_c1_traseira", False))
                f_c2_tt = bool(fita_travessas_faces.get("fita_c2_traseira", False))
                f_l1_tt = bool(fita_travessas_faces.get("fita_l1_traseira", False))
                f_l2_tt = bool(fita_travessas_faces.get("fita_l2_traseira", False))
            else:
                f_c1_tf, f_c2_tf, f_l1_tf, f_l2_tf = True, False, False, False
                f_c1_tt, f_c2_tt, f_l1_tt, f_l2_tt = False, False, False, False

            # Front stretcher (upright / vertical or flat / horizontal)
            if travessa_frontal_em_pe:
                groups.append(cls.build_travessa_peca(
                    name=f"{prefixo} - Travessa Frontal Em Pe",
                    origin=(ox + E, oy, oz + A - LTF),
                    size=(largura_interna, E_trav, LTF),
                    material=mat_trav, fita_c1=f_c1_tf, fita_c2=f_c2_tf, fita_l1=f_l1_tf, fita_l2=f_l2_tf,
                    color=cor_trav, material_fita=mat_fita_tr, cor_fita=cor_fita_tr,
                    operacoes=ops_trav_f,
                ))
            else:
                groups.append(cls.build_travessa_peca(
                    name=f"{prefixo} - Travessa Frontal",
                    origin=(ox + E, oy, oz + A - E_trav),
                    size=(largura_interna, LTF, E_trav),
                    material=mat_trav, fita_c1=f_c1_tf, fita_c2=f_c2_tf, fita_l1=f_l1_tf, fita_l2=f_l2_tf,
                    color=cor_trav, material_fita=mat_fita_tr, cor_fita=cor_fita_tr,
                    operacoes=ops_trav_f,
                ))

            # Rear stretcher (upright / vertical or flat / horizontal)
            if travessa_traseira_em_pe:
                groups.append(cls.build_travessa_peca(
                    name=f"{prefixo} - Travessa Traseira Em Pe",
                    origin=(ox + E, oy + P - E_trav, oz + A - LTT),
                    size=(largura_interna, E_trav, LTT),
                    material=mat_trav, fita_c1=f_c1_tt, fita_c2=f_c2_tt, fita_l1=f_l1_tt, fita_l2=f_l2_tt,
                    color=cor_trav, material_fita=mat_fita_tr, cor_fita=cor_fita_tr,
                    operacoes=ops_trav_t,
                ))
            else:
                groups.append(cls.build_travessa_peca(
                    name=f"{prefixo} - Travessa Traseira",
                    origin=(ox + E, oy + P - LTT, oz + A - E_trav),
                    size=(largura_interna, LTT, E_trav),
                    material=mat_trav, fita_c1=f_c1_tt, fita_c2=f_c2_tt, fita_l1=f_l1_tt, fita_l2=f_l2_tt,
                    color=cor_trav, material_fita=mat_fita_tr, cor_fita=cor_fita_tr,
                    operacoes=ops_trav_t,
                ))

        # Front Toe Kick
        if R > 0.01:
            spec_rodape = ChapaSpec.resolve(
                nome=f"{prefixo} - Rodape Frontal",
                papel=PapelChapa.RODAPE,
                ctx=ctx_modulo,
                material_override=material,
                fita_override=(True, False, False, False),
            )
            groups.append(build_chapa(
                spec_rodape,
                (ox, oy + 0.05, oz),
                (L, E, R),
                color=cor,
            ))

        # Integrated Back Panel generation (if requested)
        fundo_grp = cls.build_fundo_board(
            prefixo=prefixo,
            largura_interna_m=largura_interna,
            altura_interna_m=(altura_caixa - 2 * E),
            largura_total_m=L,
            altura_total_caixa_m=altura_caixa,
            prof_total_m=P,
            esp_lateral_m=E,
            origin_caixa=(ox, oy, oz + R),
            z_interno_base_m=(oz + R + E),
            tipo_fundo=eff_tipo_fundo,
            esp_fundo_mm=esp_fundo_mm,
            recuo_fundo_mm=recuo_fundo_mm,
            prof_rasgo_mm=prof_rasgo_mm,
            folga_fundo_mm=folga_fundo_mm,
            material_fundo=material_fundo,
            esp_travessa_traseira_mm=((E_trav * 1000.0) if (tipo_topo != "fechado" and travessa_traseira_em_pe) else 0.0),
        )
        if fundo_grp:
            groups.append(fundo_grp)

        info = {
            "ox": ox, "oy": oy, "oz": oz,
            "L": L, "A": A, "P": P, "E": E, "R": R,
            "altura_caixa": altura_caixa,
            "largura_interna": largura_interna,
            "tipo_topo": tipo_topo,
            "LTF": LTF, "LTT": LTT,
            "E_trav": E_trav,
            "cor": cor,
            "fundo_grp": fundo_grp,
        }
        return groups, info

    @classmethod
    def build_caixa_inferior(
        cls,
        prefixo: str,
        largura_mm: float,
        altura_mm: float,
        prof_mm: float,
        esp_mm: float = 15.0,
        rodape_mm: float = 100.0,
        material: str = "MDF Branco TX 15mm",
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        larg_travessa_frontal_mm: float = 70.0,
        larg_travessa_traseira_mm: float = 70.0,
        travessa_frontal_em_pe: bool = False,
        travessa_traseira_em_pe: bool = False,
        material_travessas: str | None = None,
        esp_travessas_mm: float | None = None,
        fita_travessas_modo: str = "frontal_1L",
        fita_travessas_faces: dict[str, bool] | None = None,
        fita_caixa_modo: str = "frontal_1L",
        material_fita_caixa: str | None = None,
        material_fita_travessas: str | None = None,
        gerar_furacao: bool = True,
        dispositivo_fixacao: str = "minifix_cavilha",
        afastamento_fixacao_frontal_mm: float = 50.0,
        afastamento_fixacao_traseiro_mm: float = 50.0,
        afastamento_cavilha_frontal_mm: float = 100.0,
        afastamento_cavilha_traseiro_mm: float = 100.0,
        alturas_prateleiras_mm: list[float] | None = None,
        prof_prateleira_mm: float | None = None,
        recuo_prateleira_frontal_mm: float = 0.0,
        alturas_calcos_esq_mm: list[float] | None = None,
        alturas_calcos_dir_mm: list[float] | None = None,
        tipo_fixacao_calco: str = "parafuso",
        divisorias_x_mm: list[float] | None = None,
        divisorias_prof_mm: float | None = None,
        divisorias_esp_mm: float | None = None,
        tem_fundo: bool = False,
        tipo_fundo: str = "rasgo",
        esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0,
        prof_rasgo_mm: float = 5.0,
        folga_fundo_mm: float = 2.0,
        material_fundo: str | None = None,
        ctx: ModuloMaterialContext | None = None,
    ) -> tuple[list[Group], dict]:
        """Compatibility wrapper for kitchen base cabinets with stretchers."""
        return cls.build_caixa_modular(
            prefixo=prefixo,
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            prof_mm=prof_mm,
            esp_mm=esp_mm,
            rodape_mm=rodape_mm,
            tipo_topo="travessas",
            material=material,
            offset=offset,
            larg_travessa_frontal_mm=larg_travessa_frontal_mm,
            larg_travessa_traseira_mm=larg_travessa_traseira_mm,
            travessa_frontal_em_pe=travessa_frontal_em_pe,
            travessa_traseira_em_pe=travessa_traseira_em_pe,
            material_travessas=material_travessas,
            esp_travessas_mm=esp_travessas_mm,
            fita_travessas_modo=fita_travessas_modo,
            fita_travessas_faces=fita_travessas_faces,
            material_fita_travessas=material_fita_travessas,
            fita_caixa_modo=fita_caixa_modo,
            material_fita_caixa=material_fita_caixa,
            tem_fundo=tem_fundo,
            tipo_fundo=tipo_fundo,
            esp_fundo_mm=esp_fundo_mm,
            recuo_fundo_mm=recuo_fundo_mm,
            prof_rasgo_mm=prof_rasgo_mm,
            folga_fundo_mm=folga_fundo_mm,
            material_fundo=material_fundo,
            gerar_furacao=gerar_furacao,
            dispositivo_fixacao=dispositivo_fixacao,
            afastamento_fixacao_frontal_mm=afastamento_fixacao_frontal_mm,
            afastamento_fixacao_traseiro_mm=afastamento_fixacao_traseiro_mm,
            afastamento_cavilha_frontal_mm=afastamento_cavilha_frontal_mm,
            afastamento_cavilha_traseiro_mm=afastamento_cavilha_traseiro_mm,
            alturas_prateleiras_mm=alturas_prateleiras_mm,
            prof_prateleira_mm=prof_prateleira_mm,
            recuo_prateleira_frontal_mm=recuo_prateleira_frontal_mm,
            alturas_calcos_esq_mm=alturas_calcos_esq_mm,
            alturas_calcos_dir_mm=alturas_calcos_dir_mm,
            tipo_fixacao_calco=tipo_fixacao_calco,
            divisorias_x_mm=divisorias_x_mm,
            divisorias_prof_mm=divisorias_prof_mm,
            divisorias_esp_mm=divisorias_esp_mm,
            ctx=ctx,
        )
