# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from typing import Any

from core.group import Group

from ..builders.chapa_builder import build_chapa
from ..builders.chapa_spec import ChapaSpec, ModuloMaterialContext, PapelChapa
from ..builders.fronts import FrentesKitBuilder
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
    **kwargs: Any,
) -> Group:
    """Cria uma peça de armário pela API canônica de chapa (material explícito)."""
    spec = ChapaSpec.resolve(
        nome=name,
        papel=papel,
        ctx=ModuloMaterialContext(material_caixa=material),
        material_override=material,
        fita_override=(fita_c1, fita_c2, fita_l1, fita_l2),
    )
    if color is not None:
        kwargs["color"] = color
    return build_chapa(spec, origin, size, **kwargs)


def _chapa_porta(
    name: str,
    origin: tuple[float, float, float],
    size: tuple[float, float, float],
    ctx: ModuloMaterialContext,
    **kwargs: Any,
) -> Group:
    """Cria uma porta canônica herdando material/fita de frentes do contexto do módulo."""
    spec = ChapaSpec.resolve(nome=name, papel=PapelChapa.PORTA, ctx=ctx)
    return build_chapa(spec, origin, size, **kwargs)


from .wardrobes_sliding import WardrobesSlidingMixin


class ArmarioBuilder(WardrobesSlidingMixin):
    """Construtor especializado para roupeiros, cabideiros, armários com prateleiras e divisórias."""

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
    def build_prateleira(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_prateleira(*args, **kwargs)

    @staticmethod
    def build_divisoria(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_divisoria(*args, **kwargs)

    @staticmethod
    def build_porta_esquerda(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_porta_esquerda(*args, **kwargs)

    @staticmethod
    def build_porta_direita(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_porta_direita(*args, **kwargs)

    @staticmethod
    def build_divisoria_horizontal(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_divisoria_horizontal(*args, **kwargs)

    @staticmethod
    def build_frente_gaveta(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_frente_gaveta(*args, **kwargs)

    @staticmethod
    def build_caixa_gaveta(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_caixa_gaveta(*args, **kwargs)

    @classmethod
    def build_roupeiro_cabideiro(
        cls, largura_mm: float, altura_mm: float, prof_mm: float,
        num_portas: int = 2,
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
        gerar_furacao: bool = True,
        dispositivo_fixacao: str = "minifix_cavilha",
        lado_abertura_porta: str = "esquerda",
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> list[Group]:
        if mat_ctx is None:
            mat_ctx = ModuloMaterialContext(
                material_caixa=material,
                material_frentes=material_frentes or material,
            )
        mat_frente = material_frentes or material
        E_frente = (esp_frentes_mm or esp_mm) / 1000.0
        cor_frente = cls.get_material_color(mat_frente)
        lado_str = str(lado_abertura_porta or "esquerda").strip().lower()
        default_side = "right" if lado_str.startswith(("dir", "right")) else "left"

        # Pré-calcula marcações de calço de dobradiça nas laterais do roupeiro
        R_val = rodape_mm / 1000.0
        altura_cx_val = (altura_mm / 1000.0) - R_val
        alturas_calcos_esq_mm = []
        alturas_calcos_dir_mm = []
        if num_portas > 0:
            from ..production.machining import make_hinge_cup_holes
            alt_porta_val = altura_cx_val - 0.006
            alt_porta_mm = alt_porta_val * 1000.0
            ops_cup = make_hinge_cup_holes(alt_porta_mm)
            calcos_z = [3.0 + o.y for o in ops_cup if "caneco" in o.descricao.lower()]
            if num_portas == 1:
                if default_side == "right":
                    alturas_calcos_dir_mm = list(calcos_z)
                else:
                    alturas_calcos_esq_mm = list(calcos_z)
            elif num_portas == 3:
                alturas_calcos_esq_mm = list(calcos_z)
                if default_side == "right":
                    alturas_calcos_dir_mm = list(calcos_z)
            elif num_portas >= 2:
                alturas_calcos_esq_mm = list(calcos_z)
                alturas_calcos_dir_mm = list(calcos_z)

        groups, info = cls.build_caixa_modular(
            prefixo="Roupeiro",
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            prof_mm=prof_mm,
            esp_mm=esp_mm,
            rodape_mm=rodape_mm,
            tipo_topo="fechado",
            material=material,
            offset=offset,
            tem_fundo=True,
            tipo_fundo=tipo_fundo,
            esp_fundo_mm=esp_fundo_mm,
            recuo_fundo_mm=recuo_fundo_mm,
            prof_rasgo_mm=prof_rasgo_mm,
            folga_fundo_mm=folga_fundo_mm,
            alturas_calcos_esq_mm=alturas_calcos_esq_mm if alturas_calcos_esq_mm else None,
            alturas_calcos_dir_mm=alturas_calcos_dir_mm if alturas_calcos_dir_mm else None,
            gerar_furacao=gerar_furacao,
            dispositivo_fixacao=dispositivo_fixacao,
        )
        ox, oy, oz = info["ox"], info["oy"], info["oz"]
        L, A, P, E, R = info["L"], info["A"], info["P"], info["E"], info["R"]
        altura_caixa = info["altura_caixa"]
        largura_interna = info["largura_interna"]
        cor = info["cor"]
        desc_fundo = cls._calc_desconto_traseiro_fundo(tipo_fundo, esp_fundo_mm, recuo_fundo_mm)
        recuo_frontal_int = 0.020
        prof_int = max(0.15, P - desc_fundo - recuo_frontal_int)
        prof_div = max(0.15, P - desc_fundo)

        # Em marcenaria residencial (especialmente 3 portas):
        # 3 portas = 1 Vão Duplo (2 portas que abrem em sentido oposto com puxadores juntos no centro)
        #          + 1 Vão Simples (1 porta isolada com dobradiça na divisória).
        # Para isso é necessária 1 DIVISÓRIA ESTRUTURAL separando o vão duplo do vão simples.
        folga_f = FrentesKitBuilder.resolve_folga_mm(mat_ctx=mat_ctx) / 1000.0

        if num_portas == 3:
            larg_porta = (L - (folga_f * 4.0)) / 3.0
            # Vão duplo (2 portas) à esquerda e vão simples (1 porta) à direita
            larg_vao_duplo = (2.0 * larg_porta) + folga_f - (E / 2.0)
            larg_vao_simples = largura_interna - larg_vao_duplo - E
            x_div = ox + E + larg_vao_duplo

            # 1 divisória vertical estrutural
            groups.append(_chapa(
                "Roupeiro - Divisória Estrutural",
                (x_div, oy, oz + R + E),
                (E, prof_div, altura_caixa - 2 * E),
                material, fita_c1=True, color=cor
            ))

            z_maleiro = oz + A - E - 0.400
            z_sapateira = oz + R + E + 0.250
            z_cabide = z_maleiro - 0.060
            centro_y = oy + recuo_frontal_int + (prof_int / 2.0) - 0.012

            # Vão Duplo (lado esquerdo)
            groups.append(_chapa(
                "Roupeiro - Maleiro Vão Duplo",
                (ox + E, oy + recuo_frontal_int, z_maleiro),
                (larg_vao_duplo, prof_int, E), material, fita_c1=True, color=cor
            ))
            groups.append(_chapa(
                "Roupeiro - Sapateira Vão Duplo",
                (ox + E, oy + recuo_frontal_int, z_sapateira),
                (larg_vao_duplo, prof_int, E), material, fita_c1=True, color=cor
            ))
            groups.append(create_board_group(
                "Roupeiro - Varão Cabideiro Vão Duplo",
                (ox + E, centro_y, z_cabide),
                (larg_vao_duplo, 0.025, 0.015), "Alumínio Anodizado", color=(0.80, 0.82, 0.85)
            ))

            # Vão Simples (lado direito)
            x_vs = x_div + E
            groups.append(_chapa(
                "Roupeiro - Maleiro Vão Simples",
                (x_vs, oy + recuo_frontal_int, z_maleiro),
                (larg_vao_simples, prof_int, E), material, fita_c1=True, color=cor
            ))
            groups.append(_chapa(
                "Roupeiro - Sapateira Vão Simples",
                (x_vs, oy + recuo_frontal_int, z_sapateira),
                (larg_vao_simples, prof_int, E), material, fita_c1=True, color=cor
            ))
            groups.append(create_board_group(
                "Roupeiro - Varão Cabideiro Vão Simples",
                (x_vs, centro_y, z_cabide),
                (larg_vao_simples, 0.025, 0.015), "Alumínio Anodizado", color=(0.80, 0.82, 0.85)
            ))

            # Portas do roupeiro de 3 portas:
            # Porta 1: abre para a esquerda (dobradiça na lateral esquerda, puxador na direita -> 'left')
            # Porta 2: abre para a direita (dobradiça na divisória, puxador na esquerda -> 'right')
            # Porta 3 (isolada): abre para a direita (dobradiça na divisória, puxador na lateral direita -> 'left' ou 'single')
            alt_porta = altura_caixa - (2.0 * folga_f)
            xp1 = ox + folga_f
            xp2 = xp1 + larg_porta + folga_f
            xp3 = xp2 + larg_porta + folga_f
            groups.append(cls.build_porta_esquerda(
                name="Roupeiro - Porta 1 (Esq Par)",
                origin=(xp1, oy - E_frente, oz + R + folga_f),
                size=(larg_porta, E_frente, alt_porta),
                material=mat_frente, color=cor_frente, ctx=mat_ctx,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                is_upper=False,
            ))
            groups.append(cls.build_porta_direita(
                name="Roupeiro - Porta 2 (Dir Par)",
                origin=(xp2, oy - E_frente, oz + R + folga_f),
                size=(larg_porta, E_frente, alt_porta),
                material=mat_frente, color=cor_frente, ctx=mat_ctx,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                is_upper=False,
            ))
            porta_isolada_fn = cls.build_porta_direita if default_side == "right" else cls.build_porta_esquerda
            lado_lbl_3 = "Dir" if default_side == "right" else "Esq"
            groups.append(porta_isolada_fn(
                name=f"Roupeiro - Porta 3 (Isolada {lado_lbl_3})",
                origin=(xp3, oy - E_frente, oz + R + folga_f),
                size=(larg_porta, E_frente, alt_porta),
                material=mat_frente, color=cor_frente, ctx=mat_ctx,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                is_upper=False,
            ))
            return groups

        elif num_portas >= 4:
            # Para 4 ou mais portas: divide em pares de portas (ex: 4 portas = 2 vãos duplos e 1 divisória central)
            num_divisoes = (num_portas // 2) - 1 if (num_portas % 2 == 0) else (num_portas - 1)
            if num_divisoes > 0:
                larg_vao = (largura_interna - (num_divisoes * E)) / float(num_divisoes + 1)
                for d_idx in range(num_divisoes):
                    x_div = ox + E + ((d_idx + 1) * larg_vao) + (d_idx * E)
                    groups.append(_chapa(
                        f"Roupeiro - Divisória Estrutural {d_idx+1}",
                        (x_div, oy, oz + R + E),
                        (E, prof_div, altura_caixa - 2 * E),
                        material, fita_c1=True, color=cor
                    ))
                z_maleiro = oz + A - E - 0.400
                z_sapateira = oz + R + E + 0.250
                z_cabide = z_maleiro - 0.060
                centro_y = oy + recuo_frontal_int + (prof_int / 2.0) - 0.012
                for v_idx in range(num_divisoes + 1):
                    x_vao = ox + E + (v_idx * (larg_vao + E))
                    groups.append(_chapa(
                        f"Roupeiro - Maleiro Vão {v_idx+1}",
                        (x_vao, oy + recuo_frontal_int, z_maleiro),
                        (larg_vao, prof_int, E), material, fita_c1=True, color=cor
                    ))
                    groups.append(_chapa(
                        f"Roupeiro - Sapateira Vão {v_idx+1}",
                        (x_vao, oy + recuo_frontal_int, z_sapateira),
                        (larg_vao, prof_int, E), material, fita_c1=True, color=cor
                    ))
                    groups.append(create_board_group(
                        f"Roupeiro - Varão Cabideiro Vão {v_idx+1}",
                        (x_vao, centro_y, z_cabide),
                        (larg_vao, 0.025, 0.015), "Alumínio Anodizado", color=(0.80, 0.82, 0.85)
                    ))
            else:
                z_maleiro = oz + A - E - 0.400
                groups.append(_chapa("Roupeiro - Prateleira Maleiro", (ox + E, oy + recuo_frontal_int, z_maleiro), (largura_interna, prof_int, E), material, fita_c1=True, color=cor))
                z_sapateira = oz + R + E + 0.250
                groups.append(_chapa("Roupeiro - Prateleira Sapateira", (ox + E, oy + recuo_frontal_int, z_sapateira), (largura_interna, prof_int, E), material, fita_c1=True, color=cor))
                z_cabide = z_maleiro - 0.060
                centro_y = oy + recuo_frontal_int + (prof_int / 2.0) - 0.012
                groups.append(create_board_group("Roupeiro - Varao Cabideiro", (ox + E, centro_y, z_cabide), (largura_interna, 0.025, 0.015), "Aluminio Anodizado", color=(0.80, 0.82, 0.85)))

            alt_porta = altura_caixa - (2.0 * folga_f)
            lp = (L - (folga_f * (num_portas + 1))) / float(num_portas)
            for i in range(num_portas):
                xp = ox + folga_f + (i * (lp + folga_f))
                if (num_portas % 2 == 1) and (i == num_portas - 1):
                    d_side = default_side
                else:
                    d_side = "left" if (i % 2 == 0) else "right"
                lado_lbl = "Dir" if d_side == "right" else "Esq"
                groups.append(_chapa_porta(
                    f"Roupeiro - Porta {i+1} ({lado_lbl})",
                    (xp, oy - E_frente, oz + R + folga_f),
                    (lp, E_frente, alt_porta), mat_ctx,
                    color=cor_frente,
                    puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos, desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo, door_side=d_side, is_upper=False
                ))
            return groups
        else:
            # 1 ou 2 portas normais
            z_maleiro = oz + A - E - 0.400
            groups.append(_chapa("Roupeiro - Prateleira Maleiro", (ox + E, oy + recuo_frontal_int, z_maleiro), (largura_interna, prof_int, E), material, fita_c1=True, color=cor))
            z_sapateira = oz + R + E + 0.250
            groups.append(_chapa("Roupeiro - Prateleira Sapateira", (ox + E, oy + recuo_frontal_int, z_sapateira), (largura_interna, prof_int, E), material, fita_c1=True, color=cor))
            z_cabide = z_maleiro - 0.060
            centro_y = oy + recuo_frontal_int + (prof_int / 2.0) - 0.012
            groups.append(create_board_group("Roupeiro - Varao Cabideiro", (ox + E, centro_y, z_cabide), (largura_interna, 0.025, 0.015), "Aluminio Anodizado", color=(0.80, 0.82, 0.85)))

            if num_portas > 0:
                alt_porta = altura_caixa - (2.0 * folga_f)
                if num_portas == 1:
                    porta_unica_fn = cls.build_porta_direita if default_side == "right" else cls.build_porta_esquerda
                    lado_lbl_1 = "Dir" if default_side == "right" else "Esq"
                    groups.append(porta_unica_fn(
                        name=f"Roupeiro - Porta ({lado_lbl_1})",
                        origin=(ox + folga_f, oy - E_frente, oz + R + folga_f),
                        size=(L - (2.0 * folga_f), E_frente, alt_porta),
                        material=mat_frente, color=cor_frente, ctx=mat_ctx,
                        puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                        desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                        is_upper=False,
                    ))
                else:
                    lp = (L - (folga_f * (num_portas + 1))) / float(num_portas)
                    groups.append(cls.build_porta_esquerda(
                        name="Roupeiro - Porta Esq",
                        origin=(ox + folga_f, oy - E_frente, oz + R + folga_f),
                        size=(lp, E_frente, alt_porta),
                        material=mat_frente, color=cor_frente, ctx=mat_ctx,
                        puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                        desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                        is_upper=False,
                    ))
                    groups.append(cls.build_porta_direita(
                        name="Roupeiro - Porta Dir",
                        origin=(ox + folga_f + lp + folga_f, oy - E_frente, oz + R + folga_f),
                        size=(lp, E_frente, alt_porta),
                        material=mat_frente, color=cor_frente, ctx=mat_ctx,
                        puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                        desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                        is_upper=False,
                    ))

            return groups

    @classmethod
    def build_armario_prateleiras(
        cls, largura_mm: float, altura_mm: float, prof_mm: float,
        num_portas: int = 1, num_prateleiras: int = 5,
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
        gerar_furacao: bool = True,
        dispositivo_fixacao: str = "minifix_cavilha",
        mat_ctx: ModuloMaterialContext | None = None,
        lado_abertura_porta: str = "esquerda",
    ) -> list[Group]:
        ox, oy, oz = offset
        if mat_ctx is None:
            mat_ctx = ModuloMaterialContext(
                material_caixa=material,
                material_frentes=material_frentes or material,
            )
        mat_frente = material_frentes or material
        E_frente = (esp_frentes_mm or esp_mm) / 1000.0
        cor_frente = cls.get_material_color(mat_frente)

        lado_str = str(lado_abertura_porta or "esquerda").strip().lower()
        default_side = "right" if lado_str.startswith(("dir", "right")) else "left"

        P_val = prof_mm / 1000.0
        E_val = esp_mm / 1000.0
        R_val = rodape_mm / 1000.0
        altura_cx_val = (altura_mm / 1000.0) - R_val

        desc_fundo = cls._calc_desconto_traseiro_fundo(tipo_fundo, esp_fundo_mm, recuo_fundo_mm)
        recuo_frontal_prat = 0.020
        prof_prat = max(0.10, P_val - desc_fundo - recuo_frontal_prat)
        prof_div = max(0.15, P_val - desc_fundo)

        # Pré-calcula alturas relativas das prateleiras para furações nas laterais
        alturas_prat_armario_mm = []
        if num_prateleiras > 0 and num_portas != 3:
            alt_vao_util = (altura_cx_val - 2 * E_val) - (num_prateleiras * E_val)
            espaco = alt_vao_util / (num_prateleiras + 1)
            for i in range(num_prateleiras):
                z_prat_rel = E_val + espaco + (i * (espaco + E_val))
                alturas_prat_armario_mm.append(z_prat_rel * 1000.0)

        # Pré-calcula marcações de calço de dobradiça nas laterais do armário
        alturas_calcos_esq_mm = []
        alturas_calcos_dir_mm = []
        if num_portas > 0:
            from ..production.machining import make_hinge_cup_holes
            alt_porta_val = altura_cx_val - 0.006
            alt_porta_mm = alt_porta_val * 1000.0
            ops_cup = make_hinge_cup_holes(alt_porta_mm)
            calcos_z = [3.0 + o.y for o in ops_cup if "caneco" in o.descricao.lower()]
            if num_portas == 1:
                if default_side == "right":
                    alturas_calcos_dir_mm = list(calcos_z)
                else:
                    alturas_calcos_esq_mm = list(calcos_z)
            elif num_portas == 3:
                alturas_calcos_esq_mm = list(calcos_z)
                if default_side == "right":
                    alturas_calcos_dir_mm = list(calcos_z)
            elif num_portas >= 2:
                alturas_calcos_esq_mm = list(calcos_z)
                alturas_calcos_dir_mm = list(calcos_z)

        groups, info = cls.build_caixa_modular(
            prefixo="Armário",
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            prof_mm=prof_mm,
            esp_mm=esp_mm,
            rodape_mm=rodape_mm,
            tipo_topo="fechado",
            material=material,
            offset=offset,
            tem_fundo=True,
            tipo_fundo=tipo_fundo,
            esp_fundo_mm=esp_fundo_mm,
            recuo_fundo_mm=recuo_fundo_mm,
            prof_rasgo_mm=prof_rasgo_mm,
            folga_fundo_mm=folga_fundo_mm,
            alturas_prateleiras_mm=alturas_prat_armario_mm if alturas_prat_armario_mm else None,
            prof_prateleira_mm=prof_prat * 1000.0,
            recuo_prateleira_frontal_mm=recuo_frontal_prat * 1000.0,
            alturas_calcos_esq_mm=alturas_calcos_esq_mm if alturas_calcos_esq_mm else None,
            alturas_calcos_dir_mm=alturas_calcos_dir_mm if alturas_calcos_dir_mm else None,
            gerar_furacao=gerar_furacao,
            dispositivo_fixacao=dispositivo_fixacao,
        )

        ox, oy, oz = info["ox"], info["oy"], info["oz"]
        L, A, P, E = info["L"], info["A"], info["P"], info["E"]
        R = info["R"]
        altura_caixa = info["altura_caixa"]
        largura_interna = info["largura_interna"]
        cor = cls.get_material_color(material)

        # Em marcenaria residencial (especialmente 3 portas):
        # 3 portas = 1 Vão Duplo (2 portas abrindo em sentidos opostos com puxadores no centro)
        #          + 1 Vão Simples (1 porta isolada abrindo individualmente).
        # Para isso é necessária 1 DIVISÓRIA ESTRUTURAL separando o vão duplo do vão simples.
        folga_f = FrentesKitBuilder.resolve_folga_mm(mat_ctx=mat_ctx) / 1000.0
        if num_portas == 3:
            larg_porta = (L - (folga_f * 4.0)) / 3.0
            larg_vao_duplo = (2.0 * larg_porta) + folga_f - (E / 2.0)
            larg_vao_simples = largura_interna - larg_vao_duplo - E
            x_div = ox + E + larg_vao_duplo

            # 1 divisória vertical estrutural
            groups.append(_chapa(
                "Armário - Divisória Estrutural",
                (x_div, oy, oz + R + E),
                (E, prof_div, altura_caixa - 2 * E),
                material, fita_c1=True, color=cor
            ))

            # Prateleiras internas por vão
            if num_prateleiras > 0:
                alt_vao_util = (altura_caixa - 2 * E) - (num_prateleiras * E)
                espaco = alt_vao_util / (num_prateleiras + 1)
                for i in range(num_prateleiras):
                    z_prat = oz + R + E + espaco + (i * (espaco + E))
                    # Prateleiras no Vão Duplo
                    groups.append(_chapa(
                        f"Armário - Prat Dupla {i+1}",
                        (ox + E, oy + recuo_frontal_prat, z_prat),
                        (larg_vao_duplo, prof_prat, E),
                        material, fita_c1=True, color=cor
                    ))
                    # Prateleiras no Vão Simples
                    x_vs = x_div + E
                    groups.append(_chapa(
                        f"Armário - Prat Simples {i+1}",
                        (x_vs, oy + recuo_frontal_prat, z_prat),
                        (larg_vao_simples, prof_prat, E),
                        material, fita_c1=True, color=cor
                    ))

            # Portas: Par oposto (Portas 1 e 2) + Porta Isolada (Porta 3)
            alt_porta = altura_caixa - (2.0 * folga_f)
            xp1 = ox + folga_f
            xp2 = xp1 + larg_porta + folga_f
            xp3 = xp2 + larg_porta + folga_f
            groups.append(cls.build_porta_esquerda(
                name="Armário - Porta 1 (Esq Par)",
                origin=(xp1, oy - E_frente, oz + R + folga_f),
                size=(larg_porta, E_frente, alt_porta),
                material=mat_frente, color=cor_frente, ctx=mat_ctx,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                is_upper=False,
            ))
            groups.append(cls.build_porta_direita(
                name="Armário - Porta 2 (Dir Par)",
                origin=(xp2, oy - E_frente, oz + R + folga_f),
                size=(larg_porta, E_frente, alt_porta),
                material=mat_frente, color=cor_frente, ctx=mat_ctx,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                is_upper=False,
            ))
            porta_isolada_fn = cls.build_porta_direita if default_side == "right" else cls.build_porta_esquerda
            lado_lbl_3 = "Dir" if default_side == "right" else "Esq"
            groups.append(porta_isolada_fn(
                name=f"Armário - Porta 3 (Isolada {lado_lbl_3})",
                origin=(xp3, oy - E_frente, oz + R + folga_f),
                size=(larg_porta, E_frente, alt_porta),
                material=mat_frente, color=cor_frente, ctx=mat_ctx,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                is_upper=False,
            ))
            return groups

        elif num_portas >= 4:
            num_divisoes = (num_portas // 2) - 1 if (num_portas % 2 == 0) else (num_portas - 1)
            if num_divisoes > 0:
                larg_vao = (largura_interna - (num_divisoes * E)) / float(num_divisoes + 1)
                for d_idx in range(num_divisoes):
                    x_div = ox + E + ((d_idx + 1) * larg_vao) + (d_idx * E)
                    groups.append(_chapa(
                        f"Armário - Divisória Estrutural {d_idx+1}",
                        (x_div, oy, oz + R + E),
                        (E, prof_div, altura_caixa - 2 * E),
                        material, fita_c1=True, color=cor
                    ))
                if num_prateleiras > 0:
                    alt_vao_util = (altura_caixa - 2 * E) - (num_prateleiras * E)
                    espaco = alt_vao_util / (num_prateleiras + 1)
                    for v_idx in range(num_divisoes + 1):
                        x_vao = ox + E + (v_idx * (larg_vao + E))
                        for i in range(num_prateleiras):
                            z_prat = oz + R + E + espaco + (i * (espaco + E))
                            groups.append(_chapa(
                                f"Armário - Prat Vão {v_idx+1}_{i+1}",
                                (x_vao, oy + recuo_frontal_prat, z_prat),
                                (larg_vao, prof_prat, E),
                                material, fita_c1=True, color=cor
                            ))
            else:
                if num_prateleiras > 0:
                    alt_vao_util = (altura_caixa - 2 * E) - (num_prateleiras * E)
                    espaco = alt_vao_util / (num_prateleiras + 1)
                    for i in range(num_prateleiras):
                        z_prat = oz + R + E + espaco + (i * (espaco + E))
                        groups.append(cls.build_prateleira(
                            name=f"Armário - Prateleira {i+1}",
                            origin=(ox + E, oy + recuo_frontal_prat, z_prat),
                            size=(largura_interna, prof_prat, E),
                            material=material, fita_c1=True, color=cor,
                            gerar_furacao=True,
                        ))

            alt_porta = altura_caixa - (2.0 * folga_f)
            lp = (L - (folga_f * (num_portas + 1))) / float(num_portas)
            for i in range(num_portas):
                xp = ox + folga_f + (i * (lp + folga_f))
                if (num_portas % 2 == 1) and (i == num_portas - 1):
                    d_side = default_side
                else:
                    d_side = "left" if (i % 2 == 0) else "right"
                lado_lbl = "Dir" if d_side == "right" else "Esq"
                groups.append(_chapa_porta(
                    f"Armário - Porta {i+1} ({lado_lbl})",
                    (xp, oy - E_frente, oz + R + folga_f),
                    (lp, E_frente, alt_porta),
                    mat_ctx, color=cor_frente,
                    puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos, desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo, door_side=d_side, is_upper=False
                ))
            return groups
        else:
            # 1 ou 2 portas normais
            if num_prateleiras > 0:
                alt_vao_util = (altura_caixa - 2 * E) - (num_prateleiras * E)
                espaco = alt_vao_util / (num_prateleiras + 1)
                for i in range(num_prateleiras):
                    z_prat = oz + R + E + espaco + (i * (espaco + E))
                    groups.append(cls.build_prateleira(
                        name=f"Armário - Prateleira {i+1}",
                        origin=(ox + E, oy + recuo_frontal_prat, z_prat),
                        size=(largura_interna, prof_prat, E),
                        material=material, fita_c1=True, color=cor,
                        gerar_furacao=True,
                    ))

            if num_portas > 0:
                alt_porta = altura_caixa - (2.0 * folga_f)
                if num_portas == 1:
                    porta_unica_fn = cls.build_porta_direita if default_side == "right" else cls.build_porta_esquerda
                    lado_lbl_1 = "Dir" if default_side == "right" else "Esq"
                    groups.append(porta_unica_fn(
                        name=f"Armário - Porta ({lado_lbl_1})",
                        origin=(ox + folga_f, oy - E_frente, oz + R + folga_f),
                        size=(L - (2.0 * folga_f), E_frente, alt_porta),
                        material=mat_frente, color=cor_frente, ctx=mat_ctx,
                        puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                        desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                        is_upper=False,
                    ))
                else:
                    lp = (L - (folga_f * (num_portas + 1))) / float(num_portas)
                    groups.append(cls.build_porta_esquerda(
                        name="Armário - Porta Esq",
                        origin=(ox + folga_f, oy - E_frente, oz + R + folga_f),
                        size=(lp, E_frente, alt_porta),
                        material=mat_frente, color=cor_frente, ctx=mat_ctx,
                        puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                        desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                        is_upper=False,
                    ))
                    groups.append(cls.build_porta_direita(
                        name="Armário - Porta Dir",
                        origin=(ox + folga_f + lp + folga_f, oy - E_frente, oz + R + folga_f),
                        size=(lp, E_frente, alt_porta),
                        material=mat_frente, color=cor_frente, ctx=mat_ctx,
                        puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                        desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                        is_upper=False,
                    ))

            return groups

    @classmethod
    def build_armario_divisoria(
        cls, largura_mm: float, altura_mm: float, prof_mm: float,
        num_prateleiras: int = 4, esp_mm: float = 15.0, rodape_mm: float = 100.0,
        material: str = "MDF Branco TX 15mm", material_frentes: str | None = None,
        esp_frentes_mm: float | None = None,
        tipo_fundo: str = "rasgo", esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0, prof_rasgo_mm: float = 5.0,
        folga_fundo_mm: float = 2.0,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto", puxador_pos: str = "padrao", desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        gerar_furacao: bool = True,
        dispositivo_fixacao: str = "minifix_cavilha",
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> list[Group]:
        ox, oy, oz = offset
        if mat_ctx is None:
            mat_ctx = ModuloMaterialContext(
                material_caixa=material,
                material_frentes=material_frentes or material,
            )
        mat_frente = material_frentes or material
        E_frente = (esp_frentes_mm or esp_mm) / 1000.0
        cor_frente = cls.get_material_color(mat_frente)

        groups, info = cls.build_caixa_modular(
            prefixo="Armário 2P",
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            prof_mm=prof_mm,
            esp_mm=esp_mm,
            rodape_mm=rodape_mm,
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
        L, A, P, E, R = info["L"], info["A"], info["P"], info["E"], info["R"]
        altura_caixa = info["altura_caixa"]
        largura_interna = info["largura_interna"]
        cor = info["cor"]
        largura_vao = (largura_interna - E) / 2.0

        desc_fundo = cls._calc_desconto_traseiro_fundo(tipo_fundo, esp_fundo_mm, recuo_fundo_mm)
        prof_div = max(0.15, P - desc_fundo)
        recuo_frontal_prat = 0.020
        prof_prat = max(0.10, P - desc_fundo - recuo_frontal_prat)

        # Divisória Central
        groups.append(_chapa("Armário 2P - Divisória Central", (ox + E + largura_vao, oy, oz + R + E), (E, prof_div, altura_caixa - 2 * E), material, fita_c1=True, color=cor))

        # Lado esquerdo: Prateleiras
        espaco_esq = (altura_caixa - 2 * E - (num_prateleiras * E)) / (num_prateleiras + 1)
        for i in range(num_prateleiras):
            z_prat = oz + R + E + espaco_esq + (i * (espaco_esq + E))
            groups.append(_chapa(
                f"Armário - Prat Esq {i+1}",
                (ox + E, oy + recuo_frontal_prat, z_prat),
                (largura_vao, prof_prat, E),
                material, fita_c1=True, color=cor
            ))

        # Lado direito: Maleiro e Varão Cabideiro
        z_maleiro = oz + A - E - 0.400
        groups.append(_chapa(
            "Armário - Maleiro Dir",
            (ox + E + largura_vao + E, oy + recuo_frontal_prat, z_maleiro),
            (largura_vao, prof_prat, E),
            material, fita_c1=True, color=cor
        ))
        z_cabide = z_maleiro - 0.060
        centro_y = oy + recuo_frontal_prat + (prof_prat / 2.0) - 0.012
        groups.append(create_board_group(
            "Armário - Varão Cabideiro",
            (ox + E + largura_vao + E, centro_y, z_cabide),
            (largura_vao, 0.025, 0.015),
            "Alumínio Anodizado", color=(0.80, 0.82, 0.85)
        ))

        # 2 Portas
        folga_f = FrentesKitBuilder.resolve_folga_mm(mat_ctx=mat_ctx) / 1000.0
        alt_porta = altura_caixa - (2.0 * folga_f)
        lp = (L - (3.0 * folga_f)) / 2.0
        groups.append(cls.build_porta_esquerda(
            name="Armário - Porta Esq",
            origin=(ox + folga_f, oy - E_frente, oz + R + folga_f),
            size=(lp, E_frente, alt_porta),
            material=mat_frente, color=cor_frente, ctx=mat_ctx,
            puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
            desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
            is_upper=False,
        ))
        groups.append(cls.build_porta_direita(
            name="Armário - Porta Dir",
            origin=(ox + folga_f + lp + folga_f, oy - E_frente, oz + R + folga_f),
            size=(lp, E_frente, alt_porta),
            material=mat_frente, color=cor_frente, ctx=mat_ctx,
            puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
            desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
            is_upper=False,
        ))

        return groups

    @classmethod
    def build_armario_3portas(
        cls, largura_mm: float, altura_mm: float, prof_mm: float,
        num_gavetas: int = 2, esp_mm: float = 15.0, rodape_mm: float = 100.0,
        material: str = "MDF Branco TX 15mm", material_frentes: str | None = None,
        esp_frentes_mm: float | None = None,
        tipo_fundo: str = "rasgo", esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0, prof_rasgo_mm: float = 5.0,
        folga_fundo_mm: float = 2.0,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto", puxador_pos: str = "padrao", desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        gerar_furacao: bool = True,
        dispositivo_fixacao: str = "minifix_cavilha",
        mat_ctx: ModuloMaterialContext | None = None,
        lado_abertura_porta: str = "esquerda",
    ) -> list[Group]:
        if mat_ctx is None:
            mat_ctx = ModuloMaterialContext(
                material_caixa=material,
                material_frentes=material_frentes or material,
            )
        mat_frente = material_frentes or material
        E_frente = (esp_frentes_mm or esp_mm) / 1000.0
        cor_frente = cls.get_material_color(mat_frente)

        lado_str = str(lado_abertura_porta or "esquerda").strip().lower()
        default_side = "right" if lado_str.startswith(("dir", "right")) else "left"

        from ..production.machining import make_hinge_cup_holes
        folga_f_mm = FrentesKitBuilder.resolve_folga_mm(mat_ctx=mat_ctx)
        alt_porta_mm = max(100.0, (altura_mm - rodape_mm) - (2.0 * folga_f_mm))
        ops_cup = make_hinge_cup_holes(alt_porta_mm)
        calcos_z = [folga_f_mm + o.y for o in ops_cup if "caneco" in o.descricao.lower()]
        alturas_calcos_esq_mm = list(calcos_z)
        alturas_calcos_dir_mm = list(calcos_z) if default_side == "right" else []

        groups, info = cls.build_caixa_modular(
            prefixo="Armário 3P",
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            prof_mm=prof_mm,
            esp_mm=esp_mm,
            rodape_mm=rodape_mm,
            tipo_topo="fechado",
            material=material,
            offset=offset,
            tem_fundo=True,
            tipo_fundo=tipo_fundo,
            esp_fundo_mm=esp_fundo_mm,
            recuo_fundo_mm=recuo_fundo_mm,
            prof_rasgo_mm=prof_rasgo_mm,
            folga_fundo_mm=folga_fundo_mm,
            alturas_calcos_esq_mm=alturas_calcos_esq_mm if alturas_calcos_esq_mm else None,
            alturas_calcos_dir_mm=alturas_calcos_dir_mm if alturas_calcos_dir_mm else None,
            gerar_furacao=gerar_furacao,
            dispositivo_fixacao=dispositivo_fixacao,
        )
        ox, oy, oz = info["ox"], info["oy"], info["oz"]
        L, A, P, E, R = info["L"], info["A"], info["P"], info["E"], info["R"]
        altura_caixa = info["altura_caixa"]
        largura_interna = info["largura_interna"]
        cor = info["cor"]
        largura_vao = (largura_interna - 2 * E) / 3.0

        desc_fundo = cls._calc_desconto_traseiro_fundo(tipo_fundo, esp_fundo_mm, recuo_fundo_mm)
        prof_div = max(0.15, P - desc_fundo)
        recuo_frontal_prat = 0.020
        prof_prat = max(0.10, P - desc_fundo - recuo_frontal_prat)

        # Divisórias verticais estruturais internas
        groups.append(_chapa("Armário 3P - Divisória 1", (ox + E + largura_vao, oy, oz + R + E), (E, prof_div, altura_caixa - 2 * E), material, fita_c1=True, color=cor))
        groups.append(_chapa("Armário 3P - Divisória 2", (ox + E + (2 * largura_vao) + E, oy, oz + R + E), (E, prof_div, altura_caixa - 2 * E), material, fita_c1=True, color=cor))

        # Maleiro superior contínuo nos 3 vãos
        z_maleiro = oz + A - E - 0.400
        for idx_v in range(3):
            xv = ox + E + (idx_v * (largura_vao + E))
            groups.append(_chapa(
                f"Armário 3P - Maleiro Vão {idx_v+1}",
                (xv, oy + recuo_frontal_prat, z_maleiro),
                (largura_vao, prof_prat, E),
                material, fita_c1=True, color=cor
            ))

        # Vão Central: Varão Cabideiro
        z_cabide = z_maleiro - 0.060
        centro_y = oy + recuo_frontal_prat + (prof_prat / 2.0) - 0.012
        groups.append(create_board_group(
            "Armário 3P - Varão Cabideiro Centro",
            (ox + E + largura_vao + E, centro_y, z_cabide),
            (largura_vao, 0.025, 0.015),
            "Alumínio Anodizado", color=(0.80, 0.82, 0.85)
        ))

        # Vãos laterais: Prateleiras
        for v_side in (0, 2):
            xv = ox + E + (v_side * (largura_vao + E))
            for i in range(3):
                zp = oz + R + E + 0.350 + (i * 0.380)
                groups.append(_chapa(
                    f"Armário 3P - Prat Vão {v_side+1}_{i+1}",
                    (xv, oy + recuo_frontal_prat, zp),
                    (largura_vao, prof_prat, E),
                    material, fita_c1=True, color=cor
                ))

        # 3 Portas: par conjugado nas portas 1 (Esq) e 2 (Dir) + porta 3 isolada conforme lado_abertura_porta
        folga_f = FrentesKitBuilder.resolve_folga_mm(mat_ctx=mat_ctx) / 1000.0
        alt_porta = altura_caixa - (2.0 * folga_f)
        lp = (L - (4.0 * folga_f)) / 3.0
        for i in range(3):
            xp = ox + folga_f + (i * (lp + folga_f))
            d_side = "left" if i == 0 else ("right" if i == 1 else default_side)
            porta_builder = cls.build_porta_esquerda if d_side == "left" else cls.build_porta_direita
            groups.append(porta_builder(
                name=f"Armário 3P - Porta {i+1} ({'Esq' if d_side == 'left' else 'Dir'})",
                origin=(xp, oy - E_frente, oz + R + folga_f),
                size=(lp, E_frente, alt_porta),
                material=mat_frente, color=cor_frente, ctx=mat_ctx,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                is_upper=False,
            ))

        return groups




# Aliases
WardrobeBuilder = ArmarioBuilder
