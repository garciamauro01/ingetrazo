# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations
import math
from typing import Any
from core.group import Group
from core.mesh import Mesh
from ..builders.mesh_utils import create_board_group
from ..builders.chapa_builder import build_chapa
from ..builders.chapa_spec import ChapaSpec, PapelChapa, ModuloMaterialContext
from ..builders.fronts import FrentesKitBuilder


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
    **kwargs: Any,
) -> Group:
    """Cria uma peça pela API canônica de chapa (material explícito)."""
    spec = ChapaSpec.resolve(
        nome=name,
        papel=papel,
        ctx=ModuloMaterialContext(material_caixa=material, material_fita_caixa=material_fita),
        material_override=material,
        fita_override=(fita_c1, fita_c2, fita_l1, fita_l2),
        material_fita_override=material_fita,
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
    material_override: str | None = None,
    color: tuple[float, float, float] | None = None,
    **kwargs: Any,
) -> Group:
    """Cria uma frente/porta canônica herdando material e fita do contexto do módulo."""
    spec = ChapaSpec.resolve(
        nome=name,
        papel=papel,
        ctx=ctx,
        material_override=material_override,
    )
    if color is not None:
        kwargs["color"] = color
    return build_chapa(spec, origin, size, **kwargs)

class AereoTorreBuilder:
    """Construtor especializado para aéreos basculantes, nichos de microondas, torres quentes e caixas de geladeira."""

    @staticmethod
    def get_material_color(material: str) -> tuple[float, float, float]:
        from ..domain.materials_catalog import get_material_color
        return get_material_color(material)

    @staticmethod
    def _calc_desconto_traseiro_fundo(*args, **kwargs) -> float:
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder._calc_desconto_traseiro_fundo(*args, **kwargs)

    @staticmethod
    def build_caixa_modular(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_caixa_modular(*args, **kwargs)

    @staticmethod
    def build_fundo_board(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_fundo_board(*args, **kwargs)

    @staticmethod
    def build_caixa_gaveta(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_caixa_gaveta(*args, **kwargs)

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

    @classmethod
    def build_aereo_basculante(
        cls, largura_mm: float, altura_mm: float, prof_mm: float,
        esp_mm: float = 15.0, material: str = "MDF Branco TX 15mm",
        material_frentes: str | None = None, esp_frentes_mm: float | None = None,
        tipo_fundo: str = "rasgo", esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0, prof_rasgo_mm: float = 5.0,
        folga_fundo_mm: float = 2.0,
        offset: tuple[float, float, float] = (0.0, 0.0, 1.5),
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto", puxador_pos: str = "padrao", desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        gerar_furacao: bool = True,
        dispositivo_fixacao: str = "minifix_cavilha",
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> list[Group]:
        mat_frente = material_frentes or material
        E_frente = (esp_frentes_mm or esp_mm) / 1000.0
        cor_frente = cls.get_material_color(mat_frente)

        groups, info = cls.build_caixa_modular(
            prefixo="Aereo Basc",
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            prof_mm=prof_mm,
            esp_mm=esp_mm,
            rodape_mm=0.0,
            tipo_topo="fechado",
            material=material,
            offset=offset,
            tem_fundo=True,
            tipo_fundo=tipo_fundo,
            esp_fundo_mm=esp_fundo_mm,
            recuo_fundo_mm=recuo_fundo_mm,
            prof_rasgo_mm=prof_rasgo_mm,
            folga_fundo_mm=folga_fundo_mm,
            gerar_furacao=gerar_furacao,
            dispositivo_fixacao=dispositivo_fixacao,
        )
        ox, oy, oz = info["ox"], info["oy"], info["oz"]
        L, A, P, E = info["L"], info["A"], info["P"], info["E"]

        folga_f = FrentesKitBuilder.resolve_folga_mm(mat_ctx=mat_ctx) / 1000.0
        alt_porta = A - (2.0 * folga_f)
        groups.append(cls.build_porta_basculante(
            name="Aereo Basc - Porta Basculante",
            origin=(ox + folga_f, oy - E_frente, oz + folga_f),
            size=(L - (2.0 * folga_f), E_frente, alt_porta),
            material=mat_frente,
            color=cor_frente,
            puxador_tipo=puxador_tipo,
            puxador_cor=puxador_cor,
            puxador_pos=puxador_pos,
            desconto_perfil_mm=desconto_perfil_mm,
            perfil_modelo=perfil_modelo,
            is_upper=True,
            ctx=mat_ctx,
        ))

        return groups

    @classmethod
    def build_aereo_basculante_duplo(
        cls, largura_mm: float, altura_mm: float, prof_mm: float,
        esp_mm: float = 15.0, material: str = "MDF Branco TX 15mm",
        material_frentes: str | None = None, esp_frentes_mm: float | None = None,
        tipo_fundo: str = "rasgo", esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0, prof_rasgo_mm: float = 5.0,
        folga_fundo_mm: float = 2.0,
        offset: tuple[float, float, float] = (0.0, 0.0, 1.4),
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto", puxador_pos: str = "padrao", desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        gerar_furacao: bool = True,
        dispositivo_fixacao: str = "minifix_cavilha",
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> list[Group]:
        ox, oy, oz = offset
        mat_frente = material_frentes or material
        E_frente = (esp_frentes_mm or esp_mm) / 1000.0
        cor_frente = cls.get_material_color(mat_frente)
        cor = cls.get_material_color(material)

        groups, info = cls.build_caixa_modular(
            prefixo="Aereo Duplo",
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            prof_mm=prof_mm,
            esp_mm=esp_mm,
            rodape_mm=0.0,
            tipo_topo="fechado",
            material=material,
            offset=offset,
            tem_fundo=True,
            tipo_fundo=tipo_fundo,
            esp_fundo_mm=esp_fundo_mm,
            recuo_fundo_mm=recuo_fundo_mm,
            prof_rasgo_mm=prof_rasgo_mm,
            folga_fundo_mm=folga_fundo_mm,
            gerar_furacao=gerar_furacao,
            dispositivo_fixacao=dispositivo_fixacao,
        )
        ox, oy, oz = info["ox"], info["oy"], info["oz"]
        L, A, P, E = info["L"], info["A"], info["P"], info["E"]
        largura_interna = info["largura_interna"]

        desc_fundo = cls._calc_desconto_traseiro_fundo(tipo_fundo, esp_fundo_mm, recuo_fundo_mm)
        recuo_frontal_div = 0.020
        prof_div = max(0.10, P - desc_fundo - recuo_frontal_div)
        z_div = oz + (A / 2.0) - (E / 2.0)
        groups.append(cls.build_divisoria_horizontal(
            name="Aereo Duplo - Divisao Central",
            origin=(ox + E, oy + recuo_frontal_div, z_div),
            size=(largura_interna, prof_div, E),
            material=material,
            fita_c1=True,
            color=cor,
            ctx=mat_ctx,
        ))

        folga_f = FrentesKitBuilder.resolve_folga_mm(mat_ctx=mat_ctx) / 1000.0
        alt_porta = (A - (3.0 * folga_f)) / 2.0
        groups.append(cls.build_porta_basculante(
            name="Aereo Duplo - Porta Basc Inf",
            origin=(ox + folga_f, oy - E_frente, oz + folga_f),
            size=(L - (2.0 * folga_f), E_frente, alt_porta),
            material=mat_frente,
            color=cor_frente,
            puxador_tipo=puxador_tipo,
            puxador_cor=puxador_cor,
            puxador_pos=puxador_pos,
            desconto_perfil_mm=desconto_perfil_mm,
            perfil_modelo=perfil_modelo,
            is_upper=True,
            ctx=mat_ctx,
        ))
        groups.append(cls.build_porta_basculante(
            name="Aereo Duplo - Porta Basc Sup",
            origin=(ox + folga_f, oy - E_frente, oz + folga_f + alt_porta + folga_f),
            size=(L - (2.0 * folga_f), E_frente, alt_porta),
            material=mat_frente,
            color=cor_frente,
            puxador_tipo=puxador_tipo,
            puxador_cor=puxador_cor,
            puxador_pos=puxador_pos,
            desconto_perfil_mm=desconto_perfil_mm,
            perfil_modelo=perfil_modelo,
            is_upper=True,
            ctx=mat_ctx,
        ))

        return groups

    @classmethod
    def build_aereo_microondas(
        cls, largura_mm: float, altura_mm: float, prof_mm: float,
        esp_mm: float = 15.0, material: str = "MDF Branco TX 15mm",
        material_frentes: str | None = None, esp_frentes_mm: float | None = None,
        tipo_fundo: str = "rasgo", esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0, prof_rasgo_mm: float = 5.0,
        folga_fundo_mm: float = 2.0,
        offset: tuple[float, float, float] = (0.0, 0.0, 1.4),
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto", puxador_pos: str = "padrao", desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        tipo_porta_superior: str = "basculante",
        num_portas: int = 1,
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> list[Group]:
        ox, oy, oz = offset
        L, A, P, E = largura_mm / 1000.0, altura_mm / 1000.0, prof_mm / 1000.0, esp_mm / 1000.0
        mat_frente = material_frentes or material
        E_frente = (esp_frentes_mm or esp_mm) / 1000.0
        cor = cls.get_material_color(material)
        cor_frente = cls.get_material_color(mat_frente)
        largura_interna = L - 2 * E
        altura_nicho_micro = 0.380
        groups = []

        groups.append(cls.build_lateral_esquerda(
            name="Aereo Micro - Lateral Esq",
            origin=(ox, oy, oz),
            size=(E, P, A),
            material=material,
            fita_c1=True, fita_l1=True,
            color=cor,
            ctx=mat_ctx,
        ))
        groups.append(cls.build_lateral_direita(
            name="Aereo Micro - Lateral Dir",
            origin=(ox + L - E, oy, oz),
            size=(E, P, A),
            material=material,
            fita_c1=True, fita_l1=True,
            color=cor,
            ctx=mat_ctx,
        ))
        groups.append(cls.build_base_inferior(
            name="Aereo Micro - Base Projetada",
            origin=(ox + E, oy - 0.03, oz),
            size=(largura_interna, P + 0.03, E),
            material=material,
            fita_c1=True,
            color=cor,
            ctx=mat_ctx,
        ))
        groups.append(cls.build_tampo_superior(
            name="Aereo Micro - Tampo",
            origin=(ox + E, oy, oz + A - E),
            size=(largura_interna, P, E),
            material=material,
            fita_c1=True,
            color=cor,
            ctx=mat_ctx,
        ))

        z_div = oz + E + altura_nicho_micro
        groups.append(cls.build_divisoria_horizontal(
            name="Aereo Micro - Divisao",
            origin=(ox + E, oy, z_div),
            size=(largura_interna, P, E),
            material=material,
            fita_c1=True,
            color=cor,
            ctx=mat_ctx,
        ))

        alt_sup = A - E - (E + altura_nicho_micro + E)
        if alt_sup > 0.10:
            fundo_grp = cls.build_fundo_board(
                prefixo="Aereo Micro",
                largura_interna_m=largura_interna,
                altura_interna_m=alt_sup,
                largura_total_m=L,
                altura_total_caixa_m=alt_sup + 2 * E,
                prof_total_m=P,
                esp_lateral_m=E,
                origin_caixa=(ox, oy, z_div + E),
                z_interno_base_m=z_div + E,
                tipo_fundo=tipo_fundo,
                esp_fundo_mm=esp_fundo_mm,
                recuo_fundo_mm=recuo_fundo_mm,
                prof_rasgo_mm=prof_rasgo_mm,
                folga_fundo_mm=folga_fundo_mm,
            )
            if fundo_grp:
                groups.append(fundo_grp)

            # Cobre a divisória e o tampo deixando folga técnica configurada no topo e na base
            folga_f = FrentesKitBuilder.resolve_folga_mm(mat_ctx=mat_ctx) / 1000.0
            z_porta = z_div + folga_f
            alt_porta = max(0.05, (oz + A - folga_f) - z_porta)
            alt_porta_mm = alt_porta * 1000.0
            is_basculante = (tipo_porta_superior == "basculante" or num_portas == 1)

            if is_basculante:
                # 1 Porta Basculante
                groups.append(cls.build_porta_basculante(
                    name="Aereo Micro - Porta Superior Basculante",
                    origin=(ox + folga_f, oy - E_frente, z_porta),
                    size=(L - (2.0 * folga_f), E_frente, alt_porta),
                    material=mat_frente,
                    color=cor_frente,
                    puxador_tipo=puxador_tipo, puxador_cor=puxador_cor,
                    puxador_pos=puxador_pos, desconto_perfil_mm=desconto_perfil_mm,
                    perfil_modelo=perfil_modelo,
                    is_upper=True,
                    ctx=mat_ctx,
                ))
            else:
                # 2 Portas de Abrir / Giro
                folga_entre_portas = folga_f
                larg_total_disponivel = L - (2.0 * folga_f) - folga_entre_portas
                larg_porta = max(0.10, larg_total_disponivel / 2.0)

                # Porta Esquerda
                groups.append(cls.build_porta_esquerda(
                    name="Aereo Micro - Porta Superior Esq",
                    origin=(ox + folga_f, oy - E_frente, z_porta),
                    size=(larg_porta, E_frente, alt_porta),
                    material=mat_frente,
                    color=cor_frente,
                    puxador_tipo=puxador_tipo, puxador_cor=puxador_cor,
                    puxador_pos=puxador_pos, desconto_perfil_mm=desconto_perfil_mm,
                    perfil_modelo=perfil_modelo,
                    is_upper=True,
                    ctx=mat_ctx,
                ))
                # Porta Direita
                x_dir = ox + folga_f + larg_porta + folga_entre_portas
                groups.append(cls.build_porta_direita(
                    name="Aereo Micro - Porta Superior Dir",
                    origin=(x_dir, oy - E_frente, z_porta),
                    size=(larg_porta, E_frente, alt_porta),
                    material=mat_frente,
                    color=cor_frente,
                    puxador_tipo=puxador_tipo, puxador_cor=puxador_cor,
                    puxador_pos=puxador_pos, desconto_perfil_mm=desconto_perfil_mm,
                    perfil_modelo=perfil_modelo,
                    is_upper=True,
                    ctx=mat_ctx,
                ))

        return groups

    @classmethod
    def build_torre_quente(
        cls, largura_mm: float, altura_mm: float, prof_mm: float,
        esp_mm: float = 15.0, rodape_mm: float = 100.0,
        material: str = "MDF Branco TX 15mm", material_frentes: str | None = None,
        esp_frentes_mm: float | None = None,
        tipo_fundo: str = "rasgo", esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0, prof_rasgo_mm: float = 5.0,
        folga_fundo_mm: float = 2.0,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto", puxador_pos: str = "padrao", desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        tipo_fundo_gaveta: str = "rasgo",
        folga_corredica_mm: float = 26.0,
        material_gaveta: str | None = None,
        esp_gaveta_mm: float = 15.0,
        material_fita_gaveta: str | None = None,
        material_fundo_gaveta: str | None = None,
        esp_fundo_gaveta_mm: float = 6.0,
        gerar_furacao: bool = True,
        dispositivo_fixacao: str = "minifix_cavilha",
        mat_ctx: ModuloMaterialContext | None = None,
        lado_abertura_porta: str = "esquerda",
    ) -> list[Group]:
        mat_frente = material_frentes or material
        E_frente = (esp_frentes_mm or esp_mm) / 1000.0
        cor_frente = cls.get_material_color(mat_frente)

        groups, info = cls.build_caixa_modular(
            prefixo="Torre Quente",
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            prof_mm=prof_mm,
            esp_mm=esp_mm,
            rodape_mm=rodape_mm,
            tipo_topo="fechado",
            material=material,
            offset=offset,
            tem_fundo=False,  # O fundo da torre quente é dividido entre nichos e gavetas conforme geometria interna
            gerar_furacao=gerar_furacao,
            dispositivo_fixacao=dispositivo_fixacao,
        )
        ox, oy, oz = info["ox"], info["oy"], info["oz"]
        L, A, P, E, R = info["L"], info["A"], info["P"], info["E"], info["R"]
        altura_caixa = info["altura_caixa"]
        largura_interna = info["largura_interna"]
        cor = info["cor"]
        desc_fundo = cls._calc_desconto_traseiro_fundo(tipo_fundo, esp_fundo_mm, recuo_fundo_mm)
        folga_f = FrentesKitBuilder.resolve_folga_mm(mat_ctx=mat_ctx) / 1000.0
        alt_vao_gavetas = 0.550
        num_gav = 2
        alt_frente_gav = (alt_vao_gavetas - ((num_gav + 1) * folga_f)) / num_gav
        larg_frente = L - (2.0 * folga_f)
        prof_gav = max(0.15, min(P - 0.050, P - desc_fundo - 0.015))
        larg_corredica = max(0.010, float(folga_corredica_mm) / 1000.0)
        larg_caixa_gav = max(0.08, largura_interna - larg_corredica)
        alt_caixa_gav = max(0.06, alt_frente_gav - 0.040)

        # Materiais da gaveta
        mat_gav = material_gaveta or material
        mat_fg = material_fundo_gaveta or f"MDF Fundo {int(esp_fundo_gaveta_mm)}mm"

        for i in range(num_gav):
            z_fg = oz + R + folga_f + (i * (alt_frente_gav + folga_f))
            groups.append(cls.build_frente_gaveta(
                name=f"Torre - Gaveta {i+1} Frente",
                origin=(ox + folga_f, oy - E_frente, z_fg),
                size=(larg_frente, E_frente, alt_frente_gav),
                material=mat_frente,
                color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                ctx=mat_ctx,
            ))
            z_cg = z_fg + 0.015
            x_cg = ox + E + (larg_corredica / 2.0)
            y_cg = oy + 0.010

            gav_pieces = cls.build_caixa_gaveta(
                prefixo=f"Torre - Gaveta {i+1}",
                x_caixa=x_cg,
                y_caixa=y_cg,
                z_caixa=z_cg,
                larg_caixa=larg_caixa_gav,
                prof_caixa=prof_gav,
                alt_caixa=alt_caixa_gav,
                material_gaveta=mat_gav,
                esp_gaveta_mm=esp_gaveta_mm,
                material_fita_gaveta=material_fita_gaveta,
                tipo_fundo_gaveta=tipo_fundo_gaveta,
                material_fundo_gaveta=mat_fg,
                esp_fundo_gaveta_mm=esp_fundo_gaveta_mm,
            )
            groups.extend(gav_pieces)

        z_div1 = oz + R + E + alt_vao_gavetas
        groups.append(cls.build_divisoria_horizontal(
            name="Torre - Prateleira Apoio Forno",
            origin=(ox + E, oy, z_div1),
            size=(largura_interna, P, E),
            material=material,
            fita_c1=True,
            color=cor,
            ctx=mat_ctx,
        ))

        alt_nicho_forno = 0.600
        z_div2 = z_div1 + E + alt_nicho_forno
        groups.append(cls.build_divisoria_horizontal(
            name="Torre - Prateleira Apoio Micro",
            origin=(ox + E, oy, z_div2),
            size=(largura_interna, P, E),
            material=material,
            fita_c1=True,
            color=cor,
            ctx=mat_ctx,
        ))

        alt_nicho_micro = 0.400
        z_div3 = z_div2 + E + alt_nicho_micro
        groups.append(cls.build_divisoria_horizontal(
            name="Torre - Divisao Despensa",
            origin=(ox + E, oy, z_div3),
            size=(largura_interna, P, E),
            material=material,
            fita_c1=True,
            color=cor,
            ctx=mat_ctx,
        ))

        alt_despensa = (oz + A - E) - (z_div3 + E)
        if alt_despensa > 0.20:
            fundo_grp = cls.build_fundo_board(
                prefixo="Torre Despensa",
                largura_interna_m=largura_interna,
                altura_interna_m=alt_despensa,
                largura_total_m=L,
                altura_total_caixa_m=alt_despensa + 2 * E,
                prof_total_m=P,
                esp_lateral_m=E,
                origin_caixa=(ox, oy, z_div3 + E),
                z_interno_base_m=z_div3 + E,
                tipo_fundo=tipo_fundo,
                esp_fundo_mm=esp_fundo_mm,
                recuo_fundo_mm=recuo_fundo_mm,
                prof_rasgo_mm=prof_rasgo_mm,
                folga_fundo_mm=folga_fundo_mm,
            )
            if fundo_grp:
                groups.append(fundo_grp)
            folga_f = FrentesKitBuilder.resolve_folga_mm(mat_ctx=mat_ctx) / 1000.0
            alt_porta_d = alt_despensa - (2.0 * folga_f)
            if L <= 0.60:
                lado_str = str(lado_abertura_porta or "esquerda").strip().lower()
                is_dir = lado_str.startswith(("dir", "right"))
                porta_fn = cls.build_porta_direita if is_dir else cls.build_porta_esquerda
                lado_lbl = "Dir" if is_dir else "Esq"
                groups.append(porta_fn(
                    name=f"Torre - Porta Despensa ({lado_lbl})",
                    origin=(ox + folga_f, oy - E_frente, z_div3 + E + folga_f),
                    size=(L - (2.0 * folga_f), E_frente, alt_porta_d),
                    material=mat_frente,
                    color=cor_frente,
                    puxador_tipo=puxador_tipo, puxador_cor=puxador_cor,
                    puxador_pos=puxador_pos, desconto_perfil_mm=desconto_perfil_mm,
                    perfil_modelo=perfil_modelo,
                    is_upper=True,
                    ctx=mat_ctx,
                ))
            else:
                lp = (L - (3.0 * folga_f)) / 2.0
                groups.append(cls.build_porta_esquerda(
                    name="Torre - Porta Despensa Esq",
                    origin=(ox + folga_f, oy - E_frente, z_div3 + E + folga_f),
                    size=(lp, E_frente, alt_porta_d),
                    material=mat_frente,
                    color=cor_frente,
                    puxador_tipo=puxador_tipo, puxador_cor=puxador_cor,
                    puxador_pos=puxador_pos, desconto_perfil_mm=desconto_perfil_mm,
                    perfil_modelo=perfil_modelo,
                    is_upper=True,
                    ctx=mat_ctx,
                ))
                groups.append(cls.build_porta_direita(
                    name="Torre - Porta Despensa Dir",
                    origin=(ox + folga_f + lp + folga_f, oy - E_frente, z_div3 + E + folga_f),
                    size=(lp, E_frente, alt_porta_d),
                    material=mat_frente,
                    color=cor_frente,
                    puxador_tipo=puxador_tipo, puxador_cor=puxador_cor,
                    puxador_pos=puxador_pos, desconto_perfil_mm=desconto_perfil_mm,
                    perfil_modelo=perfil_modelo,
                    is_upper=True,
                    ctx=mat_ctx,
                ))

        return groups

    @classmethod
    def build_caixa_geladeira(
        cls, largura_mm: float, altura_mm: float, prof_mm: float,
        esp_mm: float = 15.0, alt_nicho_geladeira_mm: float = 1800.0,
        num_portas: int = 2,
        tipo_porta_superior: str = "duas_portas",
        material: str = "MDF Branco TX 15mm", material_frentes: str | None = None,
        esp_frentes_mm: float | None = None,
        tipo_fundo: str = "rasgo", esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0, prof_rasgo_mm: float = 5.0,
        folga_fundo_mm: float = 2.0,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto", puxador_pos: str = "padrao", desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> list[Group]:
        """Constrói o módulo Caixa para Geladeira (Módulo torre / fechamento).

        Composição:
        - 2 Laterais altas que vão até o chão (sem rodapé ou base inferior para permitir a geladeira entrar no vão).
        - 1 Tampo superior fechando a caixa.
        - 1 Prateleira horizontal estrutural (divisória) que delimita o topo do nicho da geladeira e a base do armário superior.
        - Fundo técnico no armário superior (maleiro).
        - Portas frontais no armário superior (1 porta basculante se num_portas==1 ou 2 portas de abrir).
        """
        ox, oy, oz = offset
        L = largura_mm / 1000.0
        A = altura_mm / 1000.0
        P = prof_mm / 1000.0
        E = esp_mm / 1000.0
        mat_frente = material_frentes or material
        E_frente = (esp_frentes_mm or esp_mm) / 1000.0
        cor = cls.get_material_color(material)
        cor_frente = cls.get_material_color(mat_frente)

        largura_interna = max(0.20, L - 2.0 * E)
        alt_nicho = max(0.50, min(A - 0.20 - 2.0 * E, alt_nicho_geladeira_mm / 1000.0))

        groups: list[Group] = []

        # 1. Laterais Direita e Esquerda canônicas (vão completas até o piso oz)
        groups.append(cls.build_lateral_esquerda(
            name="Geladeira - Lateral Esq",
            origin=(ox, oy, oz),
            size=(E, P, A),
            material=material,
            fita_c1=True, fita_c2=True, fita_l1=True,
            color=cor,
            ctx=mat_ctx,
        ))
        groups.append(cls.build_lateral_direita(
            name="Geladeira - Lateral Dir",
            origin=(ox + L - E, oy, oz),
            size=(E, P, A),
            material=material,
            fita_c1=True, fita_c2=True, fita_l1=True,
            color=cor,
            ctx=mat_ctx,
        ))

        # 2. Tampo Superior canônico (entre as laterais)
        groups.append(cls.build_tampo_superior(
            name="Geladeira - Tampo Superior",
            origin=(ox + E, oy, oz + A - E),
            size=(largura_interna, P, E),
            material=material,
            fita_c1=True,
            color=cor,
            ctx=mat_ctx,
        ))

        # 3. Prateleira Divisória Estrutural canônica (Teto do nicho da geladeira / Base do maleiro)
        z_div = oz + alt_nicho
        groups.append(cls.build_divisoria_horizontal(
            name="Geladeira - Prateleira Divisoria",
            origin=(ox + E, oy, z_div),
            size=(largura_interna, P, E),
            material=material,
            fita_c1=True,
            color=cor,
            ctx=mat_ctx,
        ))

        # 4. Armário Superior (Maleiro)
        # Altura interna do maleiro
        alt_maleiro_int = max(0.05, (oz + A - E) - (z_div + E))
        if alt_maleiro_int > 0.08:
            # Fundo técnico do maleiro
            if tipo_fundo != "sem_fundo":
                fundo_grp = cls.build_fundo_board(
                    prefixo="Geladeira Maleiro",
                    largura_interna_m=largura_interna,
                    altura_interna_m=alt_maleiro_int,
                    largura_total_m=L,
                    altura_total_caixa_m=alt_maleiro_int + 2.0 * E,
                    prof_total_m=P,
                    esp_lateral_m=E,
                    origin_caixa=(ox, oy, z_div + E),
                    z_interno_base_m=z_div + E,
                    tipo_fundo=tipo_fundo,
                    esp_fundo_mm=esp_fundo_mm,
                    recuo_fundo_mm=recuo_fundo_mm,
                    prof_rasgo_mm=prof_rasgo_mm,
                    folga_fundo_mm=folga_fundo_mm,
                )
                if fundo_grp:
                    groups.append(fundo_grp)

            # Portas do maleiro
            folga_f = FrentesKitBuilder.resolve_folga_mm(mat_ctx=mat_ctx) / 1000.0
            alt_porta = alt_maleiro_int + 2.0 * E - (2.0 * folga_f)  # Cobre a divisória e o tampo deixando folga configurada topo e base
            z_porta = z_div + folga_f

            is_basculante = (num_portas == 1 or tipo_porta_superior in ("basculante", "1_porta", "porta_unica"))

            if is_basculante:
                # Porta Basculante / única
                larg_porta = L - (2.0 * folga_f)
                groups.append(cls.build_porta_basculante(
                    name="Geladeira - Porta Superior Basculante",
                    origin=(ox + folga_f, oy - E_frente, z_porta),
                    size=(larg_porta, E_frente, alt_porta),
                    material=mat_frente,
                    color=cor_frente,
                    puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                    desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                    is_upper=True,
                    ctx=mat_ctx,
                ))
            else:
                # Duas portas de abrir com folga central configurada
                larg_cada_porta = (L - (3.0 * folga_f)) / 2.0
                groups.append(cls.build_porta_esquerda(
                    name="Geladeira - Porta Maleiro Esq",
                    origin=(ox + folga_f, oy - E_frente, z_porta),
                    size=(larg_cada_porta, E_frente, alt_porta),
                    material=mat_frente,
                    color=cor_frente,
                    puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                    desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                    is_upper=True,
                    ctx=mat_ctx,
                ))
                groups.append(cls.build_porta_direita(
                    name="Geladeira - Porta Maleiro Dir",
                    origin=(ox + folga_f + larg_cada_porta + folga_f, oy - E_frente, z_porta),
                    size=(larg_cada_porta, E_frente, alt_porta),
                    material=mat_frente,
                    color=cor_frente,
                    puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                    desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                    is_upper=True,
                    ctx=mat_ctx,
                ))

        return groups

# Aliases
WallTallCabinetBuilder = AereoTorreBuilder

