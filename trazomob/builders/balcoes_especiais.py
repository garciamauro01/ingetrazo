# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from typing import Any

from core.group import Group

from ..builders.chapa_builder import build_chapa
from ..builders.chapa_spec import ChapaSpec, ModuloMaterialContext, PapelChapa
from ..builders.fronts import FrentesKitBuilder
from ..builders.parts import _chapa


class BalcoesEspeciaisMixin:
    """Builders de módulos especiais (banheiro, rack, porta-panos, adega) extraídos de BalcaoAereoBuilder."""

    @classmethod
    def build_gabinete_banheiro(
        cls, largura_mm: float, altura_mm: float, prof_mm: float,
        esp_mm: float = 15.0, material: str = "MDF Branco TX 15mm",
        material_frentes: str | None = None, esp_frentes_mm: float | None = None,
        tipo_fundo: str = "rasgo", esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0, prof_rasgo_mm: float = 5.0,
        folga_fundo_mm: float = 2.0,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.25),
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
        prof_gaveta_mm: float | None = None,
        gerar_furacao: bool = True,
        dispositivo_fixacao: str = "minifix_cavilha",
        lado_abertura_porta: str | None = None,
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> list[Group]:
        ox, oy, oz = offset
        mat_frente = material_frentes or material
        E_frente = (esp_frentes_mm or esp_mm) / 1000.0
        cor_frente = cls.get_material_color(mat_frente)

        groups, info = cls.build_caixa_modular(
            prefixo="Gabinete Banheiro",
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
            ctx=mat_ctx,
        )
        ox, oy, oz = info["ox"], info["oy"], info["oz"]
        L, A, P, E = info["L"], info["A"], info["P"], info["E"]
        largura_interna = info["largura_interna"]
        cor = info["cor"]
        desc_fundo = cls._calc_desconto_traseiro_fundo(tipo_fundo, esp_fundo_mm, recuo_fundo_mm)
        num_gav = 2
        folga_f = FrentesKitBuilder.resolve_folga_mm(mat_ctx=mat_ctx) / 1000.0
        alt_fg = (A - ((num_gav + 1) * folga_f)) / num_gav
        larg_frente = L - (2.0 * folga_f)
        prof_gav = max(0.15, min(P - 0.050, P - desc_fundo - 0.015))
        larg_corredica = max(0.010, float(folga_corredica_mm) / 1000.0)
        larg_cg = max(0.08, largura_interna - larg_corredica)
        alt_cg = max(0.06, alt_fg - 0.040)

        # Materiais da gaveta
        mat_gav = material_gaveta or material
        mat_fg = material_fundo_gaveta or f"MDF Fundo {int(esp_fundo_gaveta_mm)}mm"

        # Gavetas do banheiro via CanonicalDrawerBuilder
        from trazomob.builders.drawers import CanonicalDrawerBuilder
        gav_groups = CanonicalDrawerBuilder.build_stack_gaveteiro(
            prefixo="Banheiro - Gaveta",
            num_gavetas=num_gav,
            x_vao=ox + E,
            y_vao=oy,
            z_vao=oz,
            larg_vao=larg_cg + larg_corredica,
            prof_vao=prof_gav,
            alt_vao=A,
            larg_frente=larg_frente,
            folga_frente_m=folga_f,
            esp_frente_m=E_frente,
            material_frente=mat_frente,
            cor_frente=cor_frente,
            material_gaveta=mat_gav,
            esp_gaveta_mm=esp_gaveta_mm,
            material_fita_gaveta=material_fita_gaveta,
            tipo_fundo_gaveta=tipo_fundo_gaveta,
            material_fundo_gaveta=mat_fg,
            esp_fundo_gaveta_mm=esp_fundo_gaveta_mm,
            folga_corredica_mm=folga_corredica_mm,
            recuo_frontal_caixa_m=0.010,
            prof_gaveta_mm=prof_gaveta_mm,
            puxador_tipo=puxador_tipo,
            puxador_cor=puxador_cor,
            puxador_pos=puxador_pos,
            desconto_perfil_mm=desconto_perfil_mm,
            perfil_modelo=perfil_modelo,
            mat_ctx=mat_ctx,
            x_frente=ox + folga_f,
        )
        groups.extend(gav_groups)

        return groups

    # -------------------------------------------------------------------------
    # RACKS: Módulo Rack tipo nicho com tampo e base cobrindo laterais
    # -------------------------------------------------------------------------
    @classmethod
    def build_rack_nicho_gaveta(
        cls,
        largura_mm: float,
        altura_mm: float,
        prof_mm: float,
        largura_gaveteiro_mm: float = 600.0,
        lado_gaveteiro: str = "esquerda",
        num_gavetas: int = 1,
        esp_mm: float = 15.0,
        material: str = "MDF Carvalho",
        material_frentes: str | None = None,
        esp_frentes_mm: float | None = None,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto",
        puxador_pos: str = "padrao",
        desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        material_gaveta: str | None = None,
        esp_gaveta_mm: float = 15.0,
        material_fita_gaveta: str | None = None,
        material_fundo_gaveta: str | None = None,
        esp_fundo_gaveta_mm: float = 6.0,
        tipo_fundo_gaveta: str = "rasgo",
        folga_corredica_mm: float = 26.0,
        fita_caixa_modo: str = "frontal_1L",
        material_fita_caixa: str | None = None,
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> list[Group]:
        """Gera Rack modular tipo Nicho: tampo passa por cima de tudo, base por baixo de tudo.

        Possui divisória vertical interna delimitando o nicho aberto e o nicho de gaveta
        (reversível à esquerda ou à direita, com largura da gaveta configurável).
        """
        ox, oy, oz = offset
        L = float(largura_mm) / 1000.0
        A = float(altura_mm) / 1000.0
        P = float(prof_mm) / 1000.0
        E = float(esp_mm) / 1000.0
        E_frente = float(esp_frentes_mm or esp_mm) / 1000.0

        cor = cls.get_material_color(material)
        mat_frente = material_frentes or material
        cor_frente = cls.get_material_color(mat_frente)

        ctx_modulo = mat_ctx if mat_ctx is not None else ModuloMaterialContext(
            material_caixa=material,
            material_fita_caixa=material_fita_caixa,
            fita_caixa_modo=fita_caixa_modo,
        )

        groups: list[Group] = []

        # 1. Base Inferior inteiriça de ponta a ponta (Z = oz até oz + E)
        groups.append(cls.build_base_inferior(
            name="Rack - Base Inferior",
            origin=(ox, oy, oz),
            size=(L, P, E),
            material=material,
            fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
            color=cor,
            ctx=ctx_modulo,
        ))

        # 2. Tampo Superior inteiriço de ponta a ponta por cima de tudo (Z = oz + A - E até oz + A)
        groups.append(cls.build_tampo_superior(
            name="Rack - Tampo Superior",
            origin=(ox, oy, oz + A - E),
            size=(L, P, E),
            material=material,
            fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
            color=cor,
            ctx=ctx_modulo,
        ))

        # 3. Laterais embutidas entre a Base e o Tampo (altura = A - 2*E)
        alt_int = max(0.05, A - 2.0 * E)
        groups.append(cls.build_lateral_esquerda(
            name="Rack - Lateral Esquerda",
            origin=(ox, oy, oz + E),
            size=(E, P, alt_int),
            material=material,
            fita_c1=True,
            color=cor,
            ctx=ctx_modulo,
        ))
        groups.append(cls.build_lateral_direita(
            name="Rack - Lateral Direita",
            origin=(ox + L - E, oy, oz + E),
            size=(E, P, alt_int),
            material=material,
            fita_c1=True,
            color=cor,
            ctx=ctx_modulo,
        ))

        # 4. Divisória e Gaveta Reversível (esquerda, direita, ambos, nenhum)
        lado = str(lado_gaveteiro or "esquerda").strip().lower()
        if lado in ("nenhum", "sem_gavetas", "sem gavetas", "none"):
            return groups

        is_ambos = lado in ("ambos", "dois_lados", "2_lados", "both")
        max_gav_ext = ((L - 2.0 * E - 0.15) / 2.0) if is_ambos else (L - 2.0 * E - 0.15)
        larg_gav_ext = min(
            max(0.20, float(largura_gaveteiro_mm) / 1000.0),
            max(0.20, max_gav_ext),
        )

        if is_ambos:
            gav_slots = [
                ("Esq", ox + E + larg_gav_ext - E, ox + E),
                ("Dir", ox + L - E - larg_gav_ext, ox + L - E - larg_gav_ext + E),
            ]
        elif lado.startswith(("dir", "right")):
            x_div = ox + L - E - larg_gav_ext
            gav_slots = [("", x_div, x_div + E)]
        else:
            x_div = ox + E + larg_gav_ext - E
            gav_slots = [("", x_div, ox + E)]

        w_gav_int = larg_gav_ext - E
        num_g = max(1, int(num_gavetas or 1))
        folga_g = FrentesKitBuilder.resolve_folga_mm(mat_ctx=ctx_modulo) / 1000.0
        larg_frente = w_gav_int - 2.0 * folga_g
        alt_frente_total = alt_int - (num_g + 1) * folga_g
        alt_frente_cada = alt_frente_total / float(num_g)

        prof_gav = max(0.15, P - 0.050)
        larg_corredica = float(folga_corredica_mm) / 1000.0
        larg_caixa_g = max(0.08, w_gav_int - larg_corredica)
        alt_caixa_g = max(0.06, alt_frente_cada - 0.040)

        mat_gav = material_gaveta or material
        mat_fg = material_fundo_gaveta or f"MDF Fundo {int(esp_fundo_gaveta_mm)}mm"
        recuo_frontal_caixa_m = 0.010

        for slot_tag, x_div, x_gav_box in gav_slots:
            div_name = f"Rack - Divisória {slot_tag}".strip()
            groups.append(cls.build_divisoria(
                name=div_name,
                origin=(x_div, oy, oz + E),
                size=(E, P, alt_int),
                material=material,
                fita_c1=True,
                color=cor,
                ctx=ctx_modulo,
            ))

            prefix_tag = f" {slot_tag}" if slot_tag else ""
            for i in range(num_g):
                z_fg = oz + E + folga_g + i * (alt_frente_cada + folga_g)
                x_fg = x_gav_box + folga_g
                frente = cls.build_frente_gaveta(
                    name=f"Rack - Gaveta{prefix_tag} {i+1} Frente",
                    origin=(x_fg, oy - E_frente, z_fg),
                    size=(larg_frente, E_frente, alt_frente_cada),
                    material=mat_frente,
                    color=cor_frente,
                    puxador_tipo=puxador_tipo,
                    puxador_cor=puxador_cor,
                    puxador_pos=puxador_pos,
                    desconto_perfil_mm=desconto_perfil_mm,
                    perfil_modelo=perfil_modelo,
                    ctx=ctx_modulo,
                )
                groups.append(frente)

                z_cg = z_fg + E
                x_cg = x_gav_box + (larg_corredica / 2.0)
                y_cg = oy + recuo_frontal_caixa_m
                gav_pieces = cls.build_caixa_gaveta(
                    prefixo=f"Rack - Gaveta{prefix_tag} {i+1}",
                    x_caixa=x_cg,
                    y_caixa=y_cg,
                    z_caixa=z_cg,
                    larg_caixa=larg_caixa_g,
                    prof_caixa=prof_gav,
                    alt_caixa=alt_caixa_g,
                    material_gaveta=mat_gav,
                    esp_gaveta_mm=esp_gaveta_mm,
                    material_fita_gaveta=material_fita_gaveta,
                    tipo_fundo_gaveta=tipo_fundo_gaveta,
                    material_fundo_gaveta=mat_fg,
                    esp_fundo_gaveta_mm=esp_fundo_gaveta_mm,
                )
                groups.extend(gav_pieces)

        return groups

    @classmethod
    @classmethod
    def build_porta_panos(
        cls,
        largura_mm: float = 200.0,
        altura_mm: float = 720.0,
        prof_mm: float = 550.0,
        esp_mm: float = 15.0,
        rodape_mm: float = 100.0,
        num_prateleiras: int = 4,
        material: str = "MDF Branco 15mm",
        cor: tuple[float, float, float] | None = None,
        origin: tuple[float, float, float] = (0.0, 0.0, 0.0),
        has_fundo: bool = True,
        tipo_fundo: str = "rasgo",
        esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0,
        prof_rasgo_mm: float = 5.0,
        folga_fundo_mm: float = 2.0,
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
        mat_ctx: ModuloMaterialContext | None = None,
        prefixo: str = "Balcao Porta-Panos",
        **kwargs: Any,
    ) -> list[Group]:
        """Constrói balcão estreito porta-panos / toalheiro com a caixaria e peças canônicas de balcão."""
        if mat_ctx is None:
            mat_ctx = ModuloMaterialContext(
                material_caixa=material,
                material_fita_caixa=material_fita_caixa,
                fita_caixa_modo=fita_caixa_modo,
            )

        eff_esp_trav_mm = float(esp_travessas_mm) if (esp_travessas_mm is not None and float(esp_travessas_mm) > 0) else esp_mm
        eff_tipo_fundo = "sem_fundo" if not has_fundo else tipo_fundo
        desc_fundo = cls._calc_desconto_traseiro_fundo(
            eff_tipo_fundo, esp_fundo_mm, recuo_fundo_mm,
            esp_travessa_traseira_mm=(eff_esp_trav_mm if travessa_traseira_em_pe else 0.0)
        )

        P_val = prof_mm / 1000.0
        E_val = esp_mm / 1000.0
        R_val = rodape_mm / 1000.0
        altura_cx_val = (altura_mm / 1000.0) - R_val

        # Pré-calcula as posições Z das prateleiras para transportar os furos de cavilha às laterais da caixa
        recuo_frontal_prat = 0.025
        prof_prat = max(0.10, P_val - desc_fundo - recuo_frontal_prat)
        alturas_prat_mm: list[float] = []
        if num_prateleiras > 0:
            espaco_util = altura_cx_val - 2 * E_val
            passo = espaco_util / (num_prateleiras + 1)
            for i in range(1, num_prateleiras + 1):
                alturas_prat_mm.append((E_val + (i * passo)) * 1000.0)

        groups, info = cls.build_caixa_inferior(
            prefixo=prefixo,
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            prof_mm=prof_mm,
            esp_mm=esp_mm,
            rodape_mm=rodape_mm,
            material=material,
            offset=origin,
            larg_travessa_frontal_mm=larg_travessa_frontal_mm,
            larg_travessa_traseira_mm=larg_travessa_traseira_mm,
            travessa_frontal_em_pe=travessa_frontal_em_pe,
            travessa_traseira_em_pe=travessa_traseira_em_pe,
            material_travessas=material_travessas,
            esp_travessas_mm=esp_travessas_mm,
            fita_travessas_modo=fita_travessas_modo,
            fita_travessas_faces=fita_travessas_faces,
            fita_caixa_modo=fita_caixa_modo,
            material_fita_caixa=material_fita_caixa,
            material_fita_travessas=material_fita_travessas,
            gerar_furacao=gerar_furacao,
            dispositivo_fixacao=dispositivo_fixacao,
            alturas_prateleiras_mm=alturas_prat_mm if num_prateleiras > 0 else None,
            prof_prateleira_mm=prof_prat * 1000.0,
            recuo_prateleira_frontal_mm=recuo_frontal_prat * 1000.0,
            tem_fundo=has_fundo,
            tipo_fundo=eff_tipo_fundo,
            esp_fundo_mm=esp_fundo_mm,
            recuo_fundo_mm=recuo_fundo_mm,
            prof_rasgo_mm=prof_rasgo_mm,
            folga_fundo_mm=folga_fundo_mm,
            ctx=mat_ctx,
        )

        ox, oy, oz = info["ox"], info["oy"], info["oz"]
        largura_interna = info["largura_interna"]

        # Prateleiras horizontais canônicas
        if num_prateleiras > 0:
            espaco_util_z = (altura_cx_val - (2.0 * E_val))
            passo_z = espaco_util_z / (num_prateleiras + 1)
            for i in range(1, num_prateleiras + 1):
                z_prat = oz + R_val + E_val + (i * passo_z) - (E_val / 2.0)
                g_prat = cls.build_prateleira(
                    f"{prefixo} - Prateleira {i}",
                    (ox + E_val, oy, z_prat),
                    (largura_interna, prof_prat, E_val),
                    material=material,
                    color=cor,
                    gerar_furacao=gerar_furacao,
                    ctx=mat_ctx,
                )
                groups.append(g_prat)

        return groups

    @classmethod
    def build_adega_colmeia(
        cls,
        largura_mm: float = 200.0,
        altura_mm: float = 720.0,
        prof_mm: float = 550.0,
        esp_mm: float = 15.0,
        rodape_mm: float = 100.0,
        num_garrafas: int = 5,
        material: str = "MDF Branco 15mm",
        cor: tuple[float, float, float] | None = None,
        origin: tuple[float, float, float] = (0.0, 0.0, 0.0),
        has_fundo: bool = True,
        tipo_fundo: str = "rasgo",
        esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0,
        prof_rasgo_mm: float = 5.0,
        folga_fundo_mm: float = 2.0,
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
        mat_ctx: ModuloMaterialContext | None = None,
        prefixo: str = "Balcao Adega Colmeia",
        **kwargs: Any,
    ) -> list[Group]:
        """Constrói balcão adega colmeia com divisórias em X a 45° utilizando caixaria canônica de balcão."""
        import math
        from ..builders.mesh_utils import create_prism_board_group

        if mat_ctx is None:
            mat_ctx = ModuloMaterialContext(
                material_caixa=material,
                material_fita_caixa=material_fita_caixa,
                fita_caixa_modo=fita_caixa_modo,
            )

        eff_esp_trav_mm = float(esp_travessas_mm) if (esp_travessas_mm is not None and float(esp_travessas_mm) > 0) else esp_mm
        eff_tipo_fundo = "sem_fundo" if not has_fundo else tipo_fundo
        desc_fundo = cls._calc_desconto_traseiro_fundo(
            eff_tipo_fundo, esp_fundo_mm, recuo_fundo_mm,
            esp_travessa_traseira_mm=(eff_esp_trav_mm if travessa_traseira_em_pe else 0.0)
        )

        P_val = prof_mm / 1000.0
        E_val = esp_mm / 1000.0
        R_val = rodape_mm / 1000.0
        altura_cx_val = (altura_mm / 1000.0) - R_val

        groups, info = cls.build_caixa_inferior(
            prefixo=prefixo,
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            prof_mm=prof_mm,
            esp_mm=esp_mm,
            rodape_mm=rodape_mm,
            material=material,
            offset=origin,
            larg_travessa_frontal_mm=larg_travessa_frontal_mm,
            larg_travessa_traseira_mm=larg_travessa_traseira_mm,
            travessa_frontal_em_pe=travessa_frontal_em_pe,
            travessa_traseira_em_pe=travessa_traseira_em_pe,
            material_travessas=material_travessas,
            esp_travessas_mm=esp_travessas_mm,
            fita_travessas_modo=fita_travessas_modo,
            fita_travessas_faces=fita_travessas_faces,
            fita_caixa_modo=fita_caixa_modo,
            material_fita_caixa=material_fita_caixa,
            material_fita_travessas=material_fita_travessas,
            gerar_furacao=gerar_furacao,
            dispositivo_fixacao=dispositivo_fixacao,
            tem_fundo=has_fundo,
            tipo_fundo=eff_tipo_fundo,
            esp_fundo_mm=esp_fundo_mm,
            recuo_fundo_mm=recuo_fundo_mm,
            prof_rasgo_mm=prof_rasgo_mm,
            folga_fundo_mm=folga_fundo_mm,
            ctx=mat_ctx,
        )

        ox, oy, oz = info["ox"], info["oy"], info["oz"]
        L, P, E = info["L"], info["P"], info["E"]
        altura_caixa = info["altura_caixa"]
        larg_vao = info["largura_interna"]
        z_base = oz + R_val
        z_topo = oz + (altura_mm / 1000.0) - E_val

        prof_util = max(0.10, P_val - desc_fundo - 0.01)

        # Divisórias cruzadas em X (45 graus)
        altura_vao_util = altura_caixa - (2.0 * E)
        passo_z_modulo = larg_vao  # altura da célula em X
        qtd_divisoes = max(2, int(altura_vao_util / passo_z_modulo))
        offset_inicial_z = z_base + E

        for k in range(qtd_divisoes):
            z_centro = offset_inicial_z + (k + 0.5) * passo_z_modulo
            if z_centro + (passo_z_modulo / 2.0) > z_topo:
                break

            # Lâmina diagonal 1 (/ subindo da esq para dir)
            poly_diag1 = [
                (ox + E, z_centro - (passo_z_modulo / 2.0)),
                (ox + L - E, z_centro + (passo_z_modulo / 2.0)),
                (ox + L - E, z_centro + (passo_z_modulo / 2.0) + (E * math.sqrt(2))),
                (ox + E, z_centro - (passo_z_modulo / 2.0) + (E * math.sqrt(2))),
            ]
            # Lâmina diagonal 2 (\ descendo da esq para dir)
            poly_diag2 = [
                (ox + E, z_centro + (passo_z_modulo / 2.0)),
                (ox + L - E, z_centro - (passo_z_modulo / 2.0)),
                (ox + L - E, z_centro - (passo_z_modulo / 2.0) + (E * math.sqrt(2))),
                (ox + E, z_centro + (passo_z_modulo / 2.0) + (E * math.sqrt(2))),
            ]

            g_d1 = create_prism_board_group(
                f"{prefixo} - Divisória X1_{k+1}",
                poly_xz=poly_diag1,
                y_start=oy,
                y_thickness=prof_util,
                material=material,
                color=cor,
            )
            groups.append(g_d1)

            g_d2 = create_prism_board_group(
                f"{prefixo} - Divisória X2_{k+1}",
                poly_xz=poly_diag2,
                y_start=oy,
                y_thickness=prof_util,
                material=material,
                color=cor,
            )
            groups.append(g_d2)

        return groups

    @classmethod
    def build_balcao_dente_traseiro(
        cls,
        largura_mm: float = 800.0,
        altura_mm: float = 720.0,
        prof_mm: float = 550.0,
        esp_mm: float = 15.0,
        rodape_mm: float = 100.0,
        posicao_dente: str = "canto_direito",  # "canto_direito", "canto_esquerdo", "central"
        largura_dente_mm: float = 250.0,
        profundidade_dente_mm: float = 150.0,
        posicao_dente_x_mm: float | None = None,
        num_portas: int = 2,
        num_prateleiras: int = 1,
        material: str = "MDF Branco TX 15mm",
        material_frentes: str | None = None,
        esp_frentes_mm: float | None = None,
        material_fundo: str | None = None,
        esp_fundo_mm: float = 6.0,
        has_fundo: bool = True,
        origin: tuple[float, float, float] = (0.0, 0.0, 0.0),
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto",
        puxador_pos: str = "padrao",
        desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        larg_travessa_frontal_mm: float = 70.0,
        larg_travessa_traseira_mm: float = 70.0,
        travessa_frontal_em_pe: bool = False,
        travessa_traseira_em_pe: bool = False,
        recuo_porta_topo_mm: float = 50.0,
        material_travessas: str | None = None,
        esp_travessas_mm: float | None = None,
        fita_travessas_modo: str = "frontal_1L",
        fita_caixa_modo: str = "frontal_1L",
        material_fita_caixa: str | None = None,
        material_fita_travessas: str | None = None,
        gerar_furacao: bool = True,
        dispositivo_fixacao: str = "minifix_cavilha",
        lado_abertura_porta: str | None = None,
        mat_ctx: ModuloMaterialContext | None = None,
        prefixo: str = "Balcao Dente Traseiro",
        **kwargs: Any,
    ) -> list[Group]:
        """Constrói Balcão com Recuo Traseiro (Dente/Shaft/Coluna Hidráulica).

        Suporta 3 configurações pelo seletor `posicao_dente`:
        - 'canto_direito' (Módulo Esquerda da ref): dente no canto posterior direito.
        - 'central' (Módulo Centro da ref): dente / shaft no meio da traseira.
        - 'canto_esquerdo' (Módulo Direita da ref): dente no canto posterior esquerdo.

        Totalmente canônico:
        - Base inferior poligonal contornando o dente com `create_polygon_board_group` e `PapelChapa.BASE_INFERIOR`;
        - Laterais externas e fechamentos verticais do dente canônicos com fitas e furações;
        - Fundo 6mm contornando as faces recuadas do dente com `build_fundo`;
        - Prateleira(s) interna(s) poligonais com recuo frontal e folga do dente;
        - Travessas superiores estruturais para apoio de pedra/bancada;
        - Portas de giro frontais canônicas via `FrentesKitBuilder`.
        """
        from ..builders.mesh_utils import create_polygon_board_group

        if mat_ctx is None:
            mat_ctx = ModuloMaterialContext(
                material_caixa=material,
                material_fita_caixa=material_fita_caixa,
                fita_caixa_modo=fita_caixa_modo,
                material_frentes=material_frentes or material,
            )

        ox, oy, oz = origin
        L = float(largura_mm) / 1000.0
        A = float(altura_mm) / 1000.0
        P = float(prof_mm) / 1000.0
        E = float(esp_mm) / 1000.0
        R = float(rodape_mm) / 1000.0
        altura_caixa = A - R

        cor = cls.get_material_color(material)
        mat_frente = material_frentes or material
        E_frente = float(esp_frentes_mm or esp_mm) / 1000.0
        cor_frente = cls.get_material_color(mat_frente)
        mat_trav = material_travessas or material
        cor_trav = cls.get_material_color(mat_trav)
        E_trav = (float(esp_travessas_mm) / 1000.0) if (esp_travessas_mm and float(esp_travessas_mm) > 0) else E
        LTF = max(0.04, float(larg_travessa_frontal_mm or 70.0) / 1000.0)
        LTT = max(0.04, float(larg_travessa_traseira_mm or 70.0) / 1000.0)

        # Dimensões do dente com proteção de limites
        pos_modo = str(posicao_dente or "canto_direito").strip().lower()
        if any(k in pos_modo for k in ("dir", "right")):
            modo = "canto_direito"
        elif any(k in pos_modo for k in ("esq", "left")):
            modo = "canto_esquerdo"
        else:
            modo = "central"

        W_dente = min(L - (2.0 * E) - 0.10, max(0.08, float(largura_dente_mm) / 1000.0))
        D_dente = min(P - LTF - 0.10, max(0.05, float(profundidade_dente_mm) / 1000.0))

        # Determina intervalo X do dente [x_d0, x_d1]
        if modo == "canto_esquerdo":
            x_d0 = ox + E
            x_d1 = ox + E + W_dente
        elif modo == "canto_direito":
            x_d0 = ox + L - E - W_dente
            x_d1 = ox + L - E
        else:  # central
            if posicao_dente_x_mm is not None:
                x_d0 = min(ox + L - E - W_dente, max(ox + E, ox + float(posicao_dente_x_mm) / 1000.0))
            else:
                x_d0 = ox + (L - W_dente) / 2.0
            x_d1 = x_d0 + W_dente

        y_fundo_parede = oy + P
        y_fundo_dente = oy + P - D_dente

        groups: list[Group] = []

        # ── 1. LATERAIS EXTERNAS PRINCIPAIS (ESQUERDA E DIREITA) ──────────────
        # Se o dente for no canto esquerdo, a lateral esquerda externa é mais curta (profundidade = P - D_dente)
        prof_lat_esq = (P - D_dente) if modo == "canto_esquerdo" else P
        groups.append(cls.build_lateral_esquerda(
            name=f"{prefixo} - Lateral Esquerda",
            origin=(ox, oy, oz + R),
            size=(E, prof_lat_esq, altura_caixa),
            material=material,
            fita_c1=True, fita_l1=True,
            color=cor,
            ctx=mat_ctx,
        ))

        # Se o dente for no canto direito, a lateral direita externa é mais curta (profundidade = P - D_dente)
        prof_lat_dir = (P - D_dente) if modo == "canto_direito" else P
        groups.append(cls.build_lateral_direita(
            name=f"{prefixo} - Lateral Direita",
            origin=(ox + L - E, oy, oz + R),
            size=(E, prof_lat_dir, altura_caixa),
            material=material,
            fita_c1=True, fita_l1=True,
            color=cor,
            ctx=mat_ctx,
        ))

        # ── 2. PAREDES / FECHAMENTOS VERTICAIS DO DENTE ────────────────────────
        # Peças verticais que contornam a coluna/shaft
        if modo == "canto_direito":
            # Lateral interna do dente: corre em X de x_d0 a x_d0 + E, profundidade D_dente
            groups.append(cls.build_divisoria(
                name=f"{prefixo} - Fechamento Lateral Dente",
                origin=(x_d0, y_fundo_dente, oz + R + E),
                size=(E, D_dente, altura_caixa - E),
                material=material,
                fita_c1=True,
                color=cor,
                ctx=mat_ctx,
            ))
            # Fundo frontal do dente: corre de X = x_d0 + E até ox + L - E em Y = y_fundo_dente
            larg_fundo_d = max(0.05, (ox + L - E) - (x_d0 + E))
            if has_fundo:
                groups.append(cls.build_fundo(
                    name=f"{prefixo} - Fundo Dente",
                    origin=(x_d0 + E, y_fundo_dente, oz + R + E),
                    size=(larg_fundo_d, esp_fundo_mm / 1000.0, altura_caixa - E),
                    material=material_fundo or f"MDF Fundo {int(esp_fundo_mm)}mm",
                    color=cor,
                    ctx=mat_ctx,
                ))
            # Fundo principal da parte reta (de ox + E até x_d0)
            larg_fundo_p = max(0.05, x_d0 - (ox + E))
            if has_fundo:
                groups.append(cls.build_fundo(
                    name=f"{prefixo} - Fundo Principal",
                    origin=(ox + E, y_fundo_parede - (esp_fundo_mm / 1000.0), oz + R + E),
                    size=(larg_fundo_p, esp_fundo_mm / 1000.0, altura_caixa - E),
                    material=material_fundo or f"MDF Fundo {int(esp_fundo_mm)}mm",
                    color=cor,
                    ctx=mat_ctx,
                ))

        elif modo == "canto_esquerdo":
            # Lateral interna do dente: corre em X = x_d1 - E até x_d1, profundidade D_dente
            groups.append(cls.build_divisoria(
                name=f"{prefixo} - Fechamento Lateral Dente",
                origin=(x_d1 - E, y_fundo_dente, oz + R + E),
                size=(E, D_dente, altura_caixa - E),
                material=material,
                fita_c1=True,
                color=cor,
                ctx=mat_ctx,
            ))
            # Fundo frontal do dente: corre de ox + E até x_d1 - E em Y = y_fundo_dente
            larg_fundo_d = max(0.05, (x_d1 - E) - (ox + E))
            if has_fundo:
                groups.append(cls.build_fundo(
                    name=f"{prefixo} - Fundo Dente",
                    origin=(ox + E, y_fundo_dente, oz + R + E),
                    size=(larg_fundo_d, esp_fundo_mm / 1000.0, altura_caixa - E),
                    material=material_fundo or f"MDF Fundo {int(esp_fundo_mm)}mm",
                    color=cor,
                    ctx=mat_ctx,
                ))
            # Fundo principal da parte reta (de x_d1 até ox + L - E)
            larg_fundo_p = max(0.05, (ox + L - E) - x_d1)
            if has_fundo:
                groups.append(cls.build_fundo(
                    name=f"{prefixo} - Fundo Principal",
                    origin=(x_d1, y_fundo_parede - (esp_fundo_mm / 1000.0), oz + R + E),
                    size=(larg_fundo_p, esp_fundo_mm / 1000.0, altura_caixa - E),
                    material=material_fundo or f"MDF Fundo {int(esp_fundo_mm)}mm",
                    color=cor,
                    ctx=mat_ctx,
                ))

        else:  # central
            # Duas laterais internas fechando o dente à esquerda e à direita
            groups.append(cls.build_divisoria(
                name=f"{prefixo} - Fechamento Dente Esq",
                origin=(x_d0, y_fundo_dente, oz + R + E),
                size=(E, D_dente, altura_caixa - E),
                material=material,
                fita_c1=True,
                color=cor,
                ctx=mat_ctx,
            ))
            groups.append(cls.build_divisoria(
                name=f"{prefixo} - Fechamento Dente Dir",
                origin=(x_d1 - E, y_fundo_dente, oz + R + E),
                size=(E, D_dente, altura_caixa - E),
                material=material,
                fita_c1=True,
                color=cor,
                ctx=mat_ctx,
            ))
            # Fundo frontal do nicho central do dente
            larg_fundo_d = max(0.05, (x_d1 - E) - (x_d0 + E))
            if has_fundo:
                groups.append(cls.build_fundo(
                    name=f"{prefixo} - Fundo Dente",
                    origin=(x_d0 + E, y_fundo_dente, oz + R + E),
                    size=(larg_fundo_d, esp_fundo_mm / 1000.0, altura_caixa - E),
                    material=material_fundo or f"MDF Fundo {int(esp_fundo_mm)}mm",
                    color=cor,
                    ctx=mat_ctx,
                ))
                # Fundos das duas partes retas externas
                larg_fundo_e = max(0.05, x_d0 - (ox + E))
                larg_fundo_d2 = max(0.05, (ox + L - E) - x_d1)
                groups.append(cls.build_fundo(
                    name=f"{prefixo} - Fundo Lateral Esq",
                    origin=(ox + E, y_fundo_parede - (esp_fundo_mm / 1000.0), oz + R + E),
                    size=(larg_fundo_e, esp_fundo_mm / 1000.0, altura_caixa - E),
                    material=material_fundo or f"MDF Fundo {int(esp_fundo_mm)}mm",
                    color=cor,
                    ctx=mat_ctx,
                ))
                groups.append(cls.build_fundo(
                    name=f"{prefixo} - Fundo Lateral Dir",
                    origin=(x_d1, y_fundo_parede - (esp_fundo_mm / 1000.0), oz + R + E),
                    size=(larg_fundo_d2, esp_fundo_mm / 1000.0, altura_caixa - E),
                    material=material_fundo or f"MDF Fundo {int(esp_fundo_mm)}mm",
                    color=cor,
                    ctx=mat_ctx,
                ))

        # ── 3. BASE INFERIOR POLIGONAL CONTORNANDO O DENTE ─────────────────────
        # Construção dos vértices em CCW
        if modo == "canto_direito":
            poly_base = [
                (ox + E, oy),
                (ox + L - E, oy),
                (ox + L - E, y_fundo_dente),
                (x_d0, y_fundo_dente),
                (x_d0, y_fundo_parede),
                (ox + E, y_fundo_parede),
            ]
        elif modo == "canto_esquerdo":
            poly_base = [
                (ox + E, oy),
                (ox + L - E, oy),
                (ox + L - E, y_fundo_parede),
                (x_d1, y_fundo_parede),
                (x_d1, y_fundo_dente),
                (ox + E, y_fundo_dente),
            ]
        else:  # central
            poly_base = [
                (ox + E, oy),
                (ox + L - E, oy),
                (ox + L - E, y_fundo_parede),
                (x_d1, y_fundo_parede),
                (x_d1, y_fundo_dente),
                (x_d0, y_fundo_dente),
                (x_d0, y_fundo_parede),
                (ox + E, y_fundo_parede),
            ]

        spec_base = ChapaSpec.resolve(
            nome=f"{prefixo} - Base Inferior",
            papel=PapelChapa.BASE_INFERIOR,
            ctx=mat_ctx,
            material_override=material,
            fita_override=(True, False, False, False),
        )
        groups.append(create_polygon_board_group(
            name=f"{prefixo} - Base Inferior",
            polygon_xy=poly_base,
            z0=oz + R,
            espessura=E,
            material=material,
            color=cor,
            spec=spec_base,
        ))

        # ── 4. PRATELEIRA(S) POLIGONAL(IS) INTERMEDIÁRIA(S) ───────────────────
        recuo_prat_f = 0.025
        y_prat_f = oy + recuo_prat_f
        y_prat_dente = y_fundo_dente - 0.010
        y_prat_tras = y_fundo_parede - 0.010

        if num_prateleiras > 0:
            espaco_util_z = altura_caixa - (2.0 * E)
            passo_z = espaco_util_z / (num_prateleiras + 1)
            for i in range(1, num_prateleiras + 1):
                zp = oz + R + E + (i * passo_z) - (E / 2.0)
                if modo == "canto_direito":
                    poly_prat = [
                        (ox + E + 0.002, y_prat_f),
                        (ox + L - E - 0.002, y_prat_f),
                        (ox + L - E - 0.002, y_prat_dente),
                        (x_d0 + 0.002, y_prat_dente),
                        (x_d0 + 0.002, y_prat_tras),
                        (ox + E + 0.002, y_prat_tras),
                    ]
                elif modo == "canto_esquerdo":
                    poly_prat = [
                        (ox + E + 0.002, y_prat_f),
                        (ox + L - E - 0.002, y_prat_f),
                        (ox + L - E - 0.002, y_prat_tras),
                        (x_d1 - 0.002, y_prat_tras),
                        (x_d1 - 0.002, y_prat_dente),
                        (ox + E + 0.002, y_prat_dente),
                    ]
                else:  # central
                    poly_prat = [
                        (ox + E + 0.002, y_prat_f),
                        (ox + L - E - 0.002, y_prat_f),
                        (ox + L - E - 0.002, y_prat_tras),
                        (x_d1 - 0.002, y_prat_tras),
                        (x_d1 - 0.002, y_prat_dente),
                        (x_d0 + 0.002, y_prat_dente),
                        (x_d0 + 0.002, y_prat_tras),
                        (ox + E + 0.002, y_prat_tras),
                    ]

                spec_prat = ChapaSpec.resolve(
                    nome=f"{prefixo} - Prateleira {i}",
                    papel=PapelChapa.PRATELEIRA,
                    ctx=mat_ctx,
                    material_override=material,
                    fita_override=(True, False, False, False),
                )
                groups.append(create_polygon_board_group(
                    name=f"{prefixo} - Prateleira {i}",
                    polygon_xy=poly_prat,
                    z0=zp,
                    espessura=E,
                    material=material,
                    color=cor,
                    spec=spec_prat,
                ))

        # ── 5. TRAVESSAS SUPERIORES ESTRUTURAIS ────────────────────────────────
        largura_interna = max(0.10, L - (2.0 * E))
        # Travessa frontal inteiriça (apoio frontal de bancada)
        if travessa_frontal_em_pe:
            groups.append(cls.build_travessa_peca(
                name=f"{prefixo} - Travessa Frontal Em Pe",
                origin=(ox + E, oy, oz + A - LTF),
                size=(largura_interna, E_trav, LTF),
                material=mat_trav, fita_c1=True, color=cor_trav,
                ctx=mat_ctx,
            ))
        else:
            groups.append(cls.build_travessa_peca(
                name=f"{prefixo} - Travessa Frontal",
                origin=(ox + E, oy, oz + A - E_trav),
                size=(largura_interna, LTF, E_trav),
                material=mat_trav, fita_c1=True, color=cor_trav,
                ctx=mat_ctx,
            ))

        # Travessas traseiras nos trechos que encostam na parede traseira
        if modo == "canto_direito":
            larg_tr_p = max(0.05, x_d0 - (ox + E))
            if travessa_traseira_em_pe:
                groups.append(cls.build_travessa_peca(
                    name=f"{prefixo} - Travessa Traseira Em Pe",
                    origin=(ox + E, y_fundo_parede - E_trav, oz + A - LTT),
                    size=(larg_tr_p, E_trav, LTT),
                    material=mat_trav, fita_c1=True, color=cor_trav, ctx=mat_ctx,
                ))
            else:
                groups.append(cls.build_travessa_peca(
                    name=f"{prefixo} - Travessa Traseira",
                    origin=(ox + E, y_fundo_parede - LTT, oz + A - E_trav),
                    size=(larg_tr_p, LTT, E_trav),
                    material=mat_trav, fita_c1=True, color=cor_trav, ctx=mat_ctx,
                ))
        elif modo == "canto_esquerdo":
            larg_tr_p = max(0.05, (ox + L - E) - x_d1)
            if travessa_traseira_em_pe:
                groups.append(cls.build_travessa_peca(
                    name=f"{prefixo} - Travessa Traseira Em Pe",
                    origin=(x_d1, y_fundo_parede - E_trav, oz + A - LTT),
                    size=(larg_tr_p, E_trav, LTT),
                    material=mat_trav, fita_c1=True, color=cor_trav, ctx=mat_ctx,
                ))
            else:
                groups.append(cls.build_travessa_peca(
                    name=f"{prefixo} - Travessa Traseira",
                    origin=(x_d1, y_fundo_parede - LTT, oz + A - E_trav),
                    size=(larg_tr_p, LTT, E_trav),
                    material=mat_trav, fita_c1=True, color=cor_trav, ctx=mat_ctx,
                ))
        else:  # central
            larg_tr_e = max(0.05, x_d0 - (ox + E))
            larg_tr_d = max(0.05, (ox + L - E) - x_d1)
            if travessa_traseira_em_pe:
                groups.append(cls.build_travessa_peca(
                    name=f"{prefixo} - Travessa Traseira Esq Em Pe",
                    origin=(ox + E, y_fundo_parede - E_trav, oz + A - LTT),
                    size=(larg_tr_e, E_trav, LTT),
                    material=mat_trav, fita_c1=True, color=cor_trav, ctx=mat_ctx,
                ))
                groups.append(cls.build_travessa_peca(
                    name=f"{prefixo} - Travessa Traseira Dir Em Pe",
                    origin=(x_d1, y_fundo_parede - E_trav, oz + A - LTT),
                    size=(larg_tr_d, E_trav, LTT),
                    material=mat_trav, fita_c1=True, color=cor_trav, ctx=mat_ctx,
                ))
            else:
                groups.append(cls.build_travessa_peca(
                    name=f"{prefixo} - Travessa Traseira Esq",
                    origin=(ox + E, y_fundo_parede - LTT, oz + A - E_trav),
                    size=(larg_tr_e, LTT, E_trav),
                    material=mat_trav, fita_c1=True, color=cor_trav, ctx=mat_ctx,
                ))
                groups.append(cls.build_travessa_peca(
                    name=f"{prefixo} - Travessa Traseira Dir",
                    origin=(x_d1, y_fundo_parede - LTT, oz + A - E_trav),
                    size=(larg_tr_d, LTT, E_trav),
                    material=mat_trav, fita_c1=True, color=cor_trav, ctx=mat_ctx,
                ))

        # ── 6. RODAPÉ FRONTAL ──────────────────────────────────────────────────
        if R > 0.01:
            spec_rod = ChapaSpec.resolve(
                nome=f"{prefixo} - Rodape Frontal",
                papel=PapelChapa.RODAPE,
                ctx=mat_ctx,
                material_override=material,
                fita_override=(True, False, False, False),
            )
            groups.append(build_chapa(
                spec_rod,
                (ox, oy + 0.05, oz),
                (L, E, R),
                color=cor,
            ))

        # ── 7. PORTAS DE GIRO FRONTAIS ─────────────────────────────────────────
        n_p = max(0, min(4, int(num_portas)))
        if n_p > 0:
            recuo_topo = (recuo_porta_topo_mm / 1000.0) if travessa_frontal_em_pe else 0.0
            lado_s = str(lado_abertura_porta or "esquerda").strip().lower()
            default_side = "right" if lado_s.startswith(("dir", "right")) else "left"
            if n_p == 1:
                door_sides = [default_side]
            elif n_p == 2:
                door_sides = ["left", "right"]
            else:
                door_sides = ["left" if i % 2 == 0 else "right" for i in range(n_p)]

            groups.extend(FrentesKitBuilder.build_kit_portas_giro(
                largura_mm=L * 1000.0,
                altura_mm=altura_caixa * 1000.0,
                num_portas=n_p,
                offset=(ox, oy, oz + R),
                esp_frente_mm=E_frente * 1000.0,
                material=mat_frente,
                color=cor_frente,
                door_sides=door_sides,
                prefixo=prefixo,
                puxador_tipo=puxador_tipo,
                puxador_cor=puxador_cor,
                puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm,
                perfil_modelo=perfil_modelo,
                is_upper=False,
                gerar_furacao=gerar_furacao,
                recuo_topo_mm=recuo_topo * 1000.0,
                mat_ctx=mat_ctx,
            ))

        return groups


