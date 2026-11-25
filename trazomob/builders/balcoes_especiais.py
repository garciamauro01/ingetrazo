# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from typing import Any

from core.group import Group

from ..builders.chapa_spec import ModuloMaterialContext, PapelChapa
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
        esp_fundo_mm: float = 6.0,
        **kwargs: Any,
    ) -> list[Group]:
        """Constrói nicho estreito porta-panos / toalheiro / garrafeiro reto com prateleiras horizontais."""
        ox, oy, oz = origin
        L = largura_mm / 1000.0
        H = altura_mm / 1000.0
        P = prof_mm / 1000.0
        E = esp_mm / 1000.0
        R = rodape_mm / 1000.0
        Ef = esp_fundo_mm / 1000.0

        H_caixa = H - R
        z_base = oz + R
        z_topo = oz + H - E
        groups: list[Group] = []

        # Laterais retas
        g_lat_esq = _chapa(
            "Porta Panos - Lateral Esq",
            (ox, oy, z_base),
            (E, P, H_caixa),
            material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
            color=cor, papel=PapelChapa.LATERAL_ESQUERDA,
        )
        groups.append(g_lat_esq)

        g_lat_dir = _chapa(
            "Porta Panos - Lateral Dir",
            (ox + L - E, oy, z_base),
            (E, P, H_caixa),
            material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
            color=cor, papel=PapelChapa.LATERAL_DIREITA,
        )
        groups.append(g_lat_dir)

        larg_vao = max(0.02, L - (2.0 * E))

        # Base inferior
        g_base = _chapa(
            "Porta Panos - Base Inferior",
            (ox + E, oy, z_base),
            (larg_vao, P, E),
            material, fita_c1=True, color=cor, papel=PapelChapa.BASE_INFERIOR,
        )
        groups.append(g_base)

        # Topo
        g_topo = _chapa(
            "Porta Panos - Topo",
            (ox + E, oy, z_topo),
            (larg_vao, P, E),
            material, fita_c1=True, color=cor, papel=PapelChapa.TAMPO_SUPERIOR,
        )
        groups.append(g_topo)

        # Fundo traseiro
        if has_fundo:
            g_fundo = _chapa(
                "Porta Panos - Fundo",
                (ox + E, oy + P - Ef, z_base + E),
                (larg_vao, Ef, H_caixa - (2.0 * E)),
                material, color=cor, papel=PapelChapa.FUNDO,
            )
            groups.append(g_fundo)
            prof_util = P - Ef - 0.01
        else:
            prof_util = P - 0.01

        # Prateleiras horizontais
        if num_prateleiras > 0:
            espaco_util_z = (H_caixa - (2.0 * E))
            passo_z = espaco_util_z / (num_prateleiras + 1)
            for i in range(1, num_prateleiras + 1):
                z_prat = z_base + E + (i * passo_z) - (E / 2.0)
                g_prat = _chapa(
                    f"Porta Panos - Prateleira {i}",
                    (ox + E, oy, z_prat),
                    (larg_vao, prof_util, E),
                    material, fita_c1=True, color=cor, papel=PapelChapa.PRATELEIRA,
                )
                groups.append(g_prat)

        # Rodapé
        if R > 0.01:
            g_rod = _chapa(
                "Porta Panos - Rodapé Frontal",
                (ox, oy + 0.05, oz),
                (L, E, R),
                material, color=cor, papel=PapelChapa.RODAPE,
            )
            groups.append(g_rod)

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
        esp_fundo_mm: float = 6.0,
        **kwargs: Any,
    ) -> list[Group]:
        """Constrói adega colmeia em X (losangos inclinados a 45 graus) para garrafas."""
        ox, oy, oz = origin
        L = largura_mm / 1000.0
        H = altura_mm / 1000.0
        P = prof_mm / 1000.0
        E = esp_mm / 1000.0
        R = rodape_mm / 1000.0
        Ef = esp_fundo_mm / 1000.0

        H_caixa = H - R
        z_base = oz + R
        z_topo = oz + H - E
        groups: list[Group] = []

        # Caixa externa
        g_lat_esq = _chapa(
            "Adega Colmeia - Lateral Esq",
            (ox, oy, z_base),
            (E, P, H_caixa),
            material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
            color=cor, papel=PapelChapa.LATERAL_ESQUERDA,
        )
        groups.append(g_lat_esq)

        g_lat_dir = _chapa(
            "Adega Colmeia - Lateral Dir",
            (ox + L - E, oy, z_base),
            (E, P, H_caixa),
            material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
            color=cor, papel=PapelChapa.LATERAL_DIREITA,
        )
        groups.append(g_lat_dir)

        larg_vao = max(0.05, L - (2.0 * E))

        g_base = _chapa(
            "Adega Colmeia - Base Inferior",
            (ox + E, oy, z_base),
            (larg_vao, P, E),
            material, fita_c1=True, color=cor, papel=PapelChapa.BASE_INFERIOR,
        )
        groups.append(g_base)

        g_topo = _chapa(
            "Adega Colmeia - Topo",
            (ox + E, oy, z_topo),
            (larg_vao, P, E),
            material, fita_c1=True, color=cor, papel=PapelChapa.TAMPO_SUPERIOR,
        )
        groups.append(g_topo)

        if has_fundo:
            g_fundo = _chapa(
                "Adega Colmeia - Fundo",
                (ox + E, oy + P - Ef, z_base + E),
                (larg_vao, Ef, H_caixa - (2.0 * E)),
                material, color=cor, papel=PapelChapa.FUNDO,
            )
            groups.append(g_fundo)
            prof_util = P - Ef - 0.01
        else:
            prof_util = P - 0.01

        # Divisórias cruzadas em X (45 graus)
        # Cada célula tem largura = larg_vao. Para 45 graus, a altura de meio-passo = larg_vao.
        import math
        altura_vao_util = H_caixa - (2.0 * E)
        comprimento_lamina = math.sqrt(2.0) * larg_vao
        passo_z_modulo = larg_vao  # altura da célula em X

        qtd_divisoes = max(2, int(altura_vao_util / passo_z_modulo))
        offset_inicial_z = z_base + E

        for k in range(qtd_divisoes):
            z_centro = offset_inicial_z + (k + 0.5) * passo_z_modulo
            if z_centro + (passo_z_modulo / 2.0) > z_topo:
                break

            # Lâmina diagonal 1 (/ subindo da esq para dir)
            # Polígono no plano XZ extrudado ao longo de Y
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

            # Criando chapas extrudadas no plano XZ em Y
            from ..builders.mesh_utils import create_prism_board_group
            g_d1 = create_prism_board_group(
                f"Adega Colmeia - Divisória X1_{k+1}",
                poly_xz=poly_diag1,
                y_start=oy,
                y_thickness=prof_util,
                material=material,
                color=cor,
            )
            groups.append(g_d1)

            g_d2 = create_prism_board_group(
                f"Adega Colmeia - Divisória X2_{k+1}",
                poly_xz=poly_diag2,
                y_start=oy,
                y_thickness=prof_util,
                material=material,
                color=cor,
            )
            groups.append(g_d2)

        # Rodapé
        if R > 0.01:
            g_rod = _chapa(
                "Adega Colmeia - Rodapé Frontal",
                (ox, oy + 0.05, oz),
                (L, E, R),
                material, color=cor, papel=PapelChapa.RODAPE,
            )
            groups.append(g_rod)

        return groups

