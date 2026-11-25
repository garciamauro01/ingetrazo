# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from typing import Any

from core.group import Group

from ..builders.chapa_builder import build_chapa
from ..builders.chapa_spec import ChapaSpec, ModuloMaterialContext, PapelChapa
from ..builders.fronts import FrentesKitBuilder
from ..builders.mesh_utils import create_board_group



from .wardrobes import _chapa, _chapa_porta


class WardrobesSlidingMixin:
    """Builders de roupeiros com portas de correr e maleiro tamponado extraídos de ArmarioBuilder."""

    @classmethod
    def build_roupeiro_portas_correr(
        cls, largura_mm: float, altura_mm: float, prof_mm: float,
        num_portas: int = 2,
        num_vaos: int | None = None,
        esp_mm: float = 15.0, rodape_mm: float = 100.0,
        material: str = "MDF Branco TX 15mm", material_frentes: str | None = None,
        esp_frentes_mm: float | None = None,
        tipo_fundo: str = "rasgo", esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0, prof_rasgo_mm: float = 5.0,
        folga_fundo_mm: float = 2.0,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        puxador_tipo: str = "perfil",
        puxador_cor: str = "preto", puxador_pos: str = "padrao", desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        exibir_portas: bool = True,
        gerar_furacao: bool = True,
        dispositivo_fixacao: str = "minifix_cavilha",
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> list[Group]:
        """Gera roupeiro de portas de correr com 2 ou 3 vaos/portas, trilhos duplos e maleiro continuo."""
        from PySide6.QtGui import QVector3D
        if mat_ctx is None:
            mat_ctx = ModuloMaterialContext(
                material_caixa=material,
                material_frentes=material_frentes or material,
            )
        mat_frente = material_frentes or material
        E_frente = (esp_frentes_mm or esp_mm) / 1000.0
        cor_frente = cls.get_material_color(mat_frente)

        # 2 ou 3 vaos (e respectivamente 2 ou 3 portas de correr)
        n_vaos = 3 if (num_vaos == 3 or num_portas == 3) else 2
        n_divisoes = n_vaos - 1  # 1 divisoria para 2 vaos, 2 divisorias para 3 vaos

        # Caixa estrutural modular do armario
        groups, info = cls.build_caixa_modular(
            prefixo=f"Roupeiro {n_vaos}V Correr",
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
        L = info["L"]
        A = info["A"]
        P = info["P"]
        E = info["E"]
        R = info["R"]
        cor = info["cor"]
        altura_caixa = info["altura_caixa"]
        larg_interna = info["largura_interna"]
        prof_util = P - cls._calc_desconto_traseiro_fundo(tipo_fundo, esp_fundo_mm, recuo_fundo_mm)

        # Recuo frontal de 65mm para acomodar trilhos duplos e portas de correr
        prof_sistema_correr = 0.065
        prof_int = prof_util - prof_sistema_correr
        recuo_trilhos = prof_sistema_correr

        # Largura util interna descontando as divisorias verticais
        larg_total_vaos = larg_interna - (n_divisoes * E)
        larg_vao = larg_total_vaos / n_vaos

        # Altura util interna da caixa
        alt_interna = altura_caixa - (2 * E)

        # Altura do maleiro superior (linha horizontal dos nichos de cima)
        # Padrao marcenaria: nicho de maleiro com ~400mm livre no topo
        h_maleiro_livre = min(0.45, max(0.35, alt_interna * 0.22))
        z_maleiro_base = oz + R + E + (alt_interna - h_maleiro_livre - E)
        h_divisoria_baixa = alt_interna - h_maleiro_livre - E

        # 1. Maleiro Superior continuo / com prateleiras em cada vao
        for v_i in range(n_vaos):
            x_prat = ox + E + v_i * (larg_vao + E)
            groups.append(_chapa(
                f"Roupeiro {n_vaos}V - Base Maleiro Vao {v_i + 1}",
                (x_prat, oy + recuo_trilhos, z_maleiro_base),
                (larg_vao, prof_int, E), material, fita_c1=True, color=cor
            ))

        # 2. Divisorias Verticais:
        # - Divisorias inferiores (do piso da caixa ate a base do maleiro)
        # - Divisorias superiores (do maleiro ate o teto da caixa)
        for d_i in range(n_divisoes):
            x_div = ox + E + (d_i + 1) * larg_vao + (d_i * E)

            # Divisoria Inferior
            groups.append(_chapa(
                f"Roupeiro {n_vaos}V - Divisoria Inferior {d_i + 1}",
                (x_div, oy + recuo_trilhos, oz + R + E),
                (E, prof_int, h_divisoria_baixa), material, fita_c1=True, color=cor
            ))

            # Divisoria Superior do Maleiro (separa os nichos superiores)
            groups.append(_chapa(
                f"Roupeiro {n_vaos}V - Divisoria Maleiro {d_i + 1}",
                (x_div, oy + recuo_trilhos, z_maleiro_base + E),
                (E, prof_int, h_maleiro_livre), material, fita_c1=True, color=cor
            ))

        # 3. Componentes internos por vao (Cabideiros / Sapateiras / Prateleiras):
        centro_y = oy + recuo_trilhos + (prof_int * 0.5)

        if n_vaos == 2:
            # Vao 1 (Esq): Cabideiro longo + Sapateira
            z_sap = oz + R + E + 0.35
            z_cab = z_maleiro_base - 0.06
            groups.append(_chapa(
                "Roupeiro 2V - Sapateira Esq",
                (ox + E, oy + recuo_trilhos, z_sap),
                (larg_vao, prof_int, E), material, fita_c1=True, color=cor
            ))
            groups.append(create_board_group(
                "Roupeiro 2V - Varao Cabideiro Esq",
                (ox + E, centro_y, z_cab),
                (larg_vao, 0.025, 0.015), "Aluminio Anodizado", color=(0.80, 0.82, 0.85)
            ))

            # Vao 2 (Dir): 4 Prateleiras organizadoras
            num_prat = 4
            espaco_p = h_divisoria_baixa / (num_prat + 1)
            x_dir = ox + E + larg_vao + E
            for idx in range(num_prat):
                zp = oz + R + E + espaco_p * (idx + 1)
                groups.append(_chapa(
                    f"Roupeiro 2V - Prateleira Dir {idx + 1}",
                    (x_dir, oy + recuo_trilhos, zp),
                    (larg_vao, prof_int, E), material, fita_c1=True, color=cor
                ))
        else:
            # 3 Vaos:
            # Vao 1 (Esq): Cabideiro para roupas longas / vestidos + Sapateira
            x_v1 = ox + E
            z_sap1 = oz + R + E + 0.35
            z_cab1 = z_maleiro_base - 0.06
            groups.append(_chapa(
                "Roupeiro 3V - Sapateira Vao 1",
                (x_v1, oy + recuo_trilhos, z_sap1),
                (larg_vao, prof_int, E), material, fita_c1=True, color=cor
            ))
            groups.append(create_board_group(
                "Roupeiro 3V - Varao Cabideiro Vao 1",
                (x_v1, centro_y, z_cab1),
                (larg_vao, 0.025, 0.015), "Aluminio Anodizado", color=(0.80, 0.82, 0.85)
            ))

            # Vao 2 (Centro): Torre de 4 Prateleiras
            x_v2 = ox + E + larg_vao + E
            num_prat = 4
            espaco_p = h_divisoria_baixa / (num_prat + 1)
            for idx in range(num_prat):
                zp = oz + R + E + espaco_p * (idx + 1)
                groups.append(_chapa(
                    f"Roupeiro 3V - Prateleira Central {idx + 1}",
                    (x_v2, oy + recuo_trilhos, zp),
                    (larg_vao, prof_int, E), material, fita_c1=True, color=cor
                ))

            # Vao 3 (Dir): Cabideiro Duplo (camisas em cima e calceiro embaixo)
            x_v3 = ox + E + (2 * (larg_vao + E))
            z_prat_meio = oz + R + E + (h_divisoria_baixa * 0.5)
            groups.append(_chapa(
                "Roupeiro 3V - Divisoria Horizontal Vao 3",
                (x_v3, oy + recuo_trilhos, z_prat_meio),
                (larg_vao, prof_int, E), material, fita_c1=True, color=cor
            ))
            groups.append(create_board_group(
                "Roupeiro 3V - Varao Cabideiro Superior Vao 3",
                (x_v3, centro_y, z_maleiro_base - 0.06),
                (larg_vao, 0.025, 0.015), "Aluminio Anodizado", color=(0.80, 0.82, 0.85)
            ))
            groups.append(create_board_group(
                "Roupeiro 3V - Varao Cabideiro Inferior Vao 3",
                (x_v3, centro_y, z_prat_meio - 0.06),
                (larg_vao, 0.025, 0.015), "Aluminio Anodizado", color=(0.80, 0.82, 0.85)
            ))

        # 4. Trilhos Duplos de Aluminio (Inferior e Superior)
        # Trilho Inferior
        groups.append(create_board_group(
            f"Roupeiro {n_vaos}V - Trilho Inferior",
            (ox + E, oy + 0.010, oz + R + E),
            (larg_interna, 0.045, 0.008), "Aluminio Anodizado", color=(0.75, 0.77, 0.80)
        ))
        # Trilho Superior
        groups.append(create_board_group(
            f"Roupeiro {n_vaos}V - Trilho Superior",
            (ox + E, oy + 0.010, oz + A - E - 0.035),
            (larg_interna, 0.045, 0.035), "Aluminio Anodizado", color=(0.75, 0.77, 0.80)
        ))

        # 5. Portas de Correr (se ativadas)
        if exibir_portas:
            # Transpasse entre folhas: 30mm por transpasse
            transpasse = 0.030
            larg_porta = (larg_interna + (n_divisoes * transpasse)) / n_vaos
            alt_porta = altura_caixa - (2 * E) - 0.015
            z_porta = oz + R + E + 0.008
            y_trilho_frontal = oy + 0.012
            y_trilho_traseiro = oy + 0.012 + E_frente + 0.012

            # Em portas de correr de roupeiros, o puxador/perfil padrão fica na lateral/extensão vertical da folha
            eff_pux_pos = puxador_pos
            if str(eff_pux_pos or "padrao").lower() in ("padrao", "auto", "superior", "topo"):
                eff_pux_pos = "extensao"

            if n_vaos == 2:
                # Porta 1: Esquerda (Trilho Traseiro) -> Desliza para a direita, puxador na esquerda
                p1 = _chapa_porta(
                    "Roupeiro Correr - Porta 1 Folha Traseira",
                    (ox + E, y_trilho_traseiro, z_porta),
                    (larg_porta, E_frente, alt_porta), mat_ctx,
                    color=cor_frente,
                    puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                    desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                    door_side="right"
                )
                if getattr(p1, "ext", None) is None:
                    p1.ext = {}
                p1.ext["slide_axis"] = QVector3D(1.0, 0.0, 0.0)
                p1.ext["slide_distance"] = float(larg_porta - transpasse - 0.02)
                groups.append(p1)

                # Porta 2: Direita (Trilho Frontal) -> Desliza para a esquerda, puxador na direita
                x_p2 = ox + E + larg_interna - larg_porta
                p2 = _chapa_porta(
                    "Roupeiro Correr - Porta 2 Folha Frontal",
                    (x_p2, y_trilho_frontal, z_porta),
                    (larg_porta, E_frente, alt_porta), mat_ctx,
                    color=cor_frente,
                    puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                    desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                    door_side="left"
                )
                if getattr(p2, "ext", None) is None:
                    p2.ext = {}
                p2.ext["slide_axis"] = QVector3D(-1.0, 0.0, 0.0)
                p2.ext["slide_distance"] = float(larg_porta - transpasse - 0.02)
                groups.append(p2)

            elif n_vaos == 3:
                # 3 Portas:
                # Porta 1 (Esq, trilho traseiro) -> corre para a direita, puxador na esquerda
                # Porta 2 (Centro, trilho frontal) -> corre para a direita, puxador na esquerda
                # Porta 3 (Dir, trilho traseiro) -> corre para a esquerda, puxador na direita
                x_p1 = ox + E
                p1 = _chapa_porta(
                    "Roupeiro Correr - Porta 1 Esq (Interna)",
                    (x_p1, y_trilho_traseiro, z_porta),
                    (larg_porta, E_frente, alt_porta), mat_ctx,
                    color=cor_frente,
                    puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                    desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                    door_side="right"
                )
                if getattr(p1, "ext", None) is None:
                    p1.ext = {}
                p1.ext["slide_axis"] = QVector3D(1.0, 0.0, 0.0)
                p1.ext["slide_distance"] = float(larg_porta)
                groups.append(p1)

                x_p2 = ox + E + (larg_interna * 0.5) - (larg_porta * 0.5)
                p2 = _chapa_porta(
                    "Roupeiro Correr - Porta 2 Centro (Externa)",
                    (x_p2, y_trilho_frontal, z_porta),
                    (larg_porta, E_frente, alt_porta), mat_ctx,
                    color=cor_frente,
                    puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                    desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                    door_side="both"
                )
                if getattr(p2, "ext", None) is None:
                    p2.ext = {}
                p2.ext["slide_axis"] = QVector3D(1.0, 0.0, 0.0)
                p2.ext["slide_distance"] = float(larg_porta - transpasse)
                groups.append(p2)

                x_p3 = ox + E + larg_interna - larg_porta
                p3 = _chapa_porta(
                    "Roupeiro Correr - Porta 3 Dir (Interna)",
                    (x_p3, y_trilho_traseiro, z_porta),
                    (larg_porta, E_frente, alt_porta), mat_ctx,
                    color=cor_frente,
                    puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                    desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                    door_side="left"
                )
                if getattr(p3, "ext", None) is None:
                    p3.ext = {}
                p3.ext["slide_axis"] = QVector3D(-1.0, 0.0, 0.0)
                p3.ext["slide_distance"] = float(larg_porta)
                groups.append(p3)

        return groups

    @classmethod
    def build_armario_maleiro_tamponado(
        cls,
        largura_mm: float,
        altura_mm: float,
        prof_mm: float,
        num_caixas: int = 2,
        modo_caixaria: str = "isoladas",  # "isoladas" ou "unica"
        esp_mm: float = 15.0,
        esp_tamponamento_mm: float = 18.0,
        recuo_portas_correr_mm: float = 70.0,
        rodape_mm: float = 100.0,
        recuo_rodape_mm: float = 30.0,
        alt_maleiro_mm: float = 400.0,
        material: str = "MDF Branco TX 15mm",
        material_tamponamento: str | None = None,
        tipo_fundo: str = "rasgo",
        esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> list[Group]:
        """Gera um armário completo com base de rodapé fechado estruturado,

        caixaria modular com divisórias de maleiro (isoladas ou única),
        tamponamento lateral de 18mm até o chão e recuo frontal de 70mm
        para posterior encaixe de portas de correr.
        """
        from .cabinet_caixa import CaixaMixin
        from .parts import CustomPartsBuilder

        ox, oy, oz = offset
        L = largura_mm / 1000.0
        A = altura_mm / 1000.0
        P = prof_mm / 1000.0
        E = esp_mm / 1000.0
        E_tamp = esp_tamponamento_mm / 1000.0
        R = rodape_mm / 1000.0
        recuo_correr = recuo_portas_correr_mm / 1000.0

        mat_tamp = material_tamponamento or material
        cor = cls.get_material_color(material)
        cor_tamp = cls.get_material_color(mat_tamp)

        groups: list[Group] = []

        n_caixas = max(2, min(4, int(num_caixas)))
        is_isoladas = (str(modo_caixaria).lower() != "unica")

        # 1. Tamponamentos Laterais (Esq e Dir)
        # Vão do chão (oz) até o topo total (oz + A) e cobrem toda a profundidade total P.
        groups.append(_chapa(
            "Armário - Tamponamento Lateral Esquerdo",
            (ox, oy, oz),
            (E_tamp, P, A),
            mat_tamp,
            fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
            color=cor_tamp
        ))

        groups.append(_chapa(
            "Armário - Tamponamento Lateral Direito",
            (ox + L - E_tamp, oy, oz),
            (E_tamp, P, A),
            mat_tamp,
            fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
            color=cor_tamp
        ))

        # Largura interna entre tamponamentos
        larg_util_total = max(0.1, L - 2 * E_tamp)
        x_base_util = ox + E_tamp

        # 2. Base de Rodapé Fechado Estruturado
        # Apoia-se no chão entre os tamponamentos, com altura R e profundidade total P.
        # Possui frente recuada, laterais em pé, travessa de fundo em pé,
        # réguas deitadas no topo e intermediárias abaixo das deitadas.
        if R > 0.02:
            sub_rodape = CustomPartsBuilder.build_rodape_fechado(
                largura_mm=larg_util_total * 1000.0,
                altura_mm=R * 1000.0,
                prof_mm=P * 1000.0,
                esp_mm=esp_mm,
                larg_travessa_topo_mm=70.0,
                recuo_frontal_mm=recuo_rodape_mm,
                material=material,
                offset=(x_base_util, oy, oz)
            )
            groups.extend(sub_rodape)

        # 3. Travessas Deitadas de Acabamento e Fechamento (plano XY, espessura em Z)
        # Largura padrão da régua/travessa: 70 mm
        larg_trav_acab = min(0.070, P * 0.3)

        # 3.1. Duas travessas deitadas entre o rodapé e as caixas (Z = oz + R):
        # - Travessa Deitada Inferior Frontal: na face frontal (oy até oy + larg_trav_acab)
        groups.append(_chapa(
            "Armário - Travessa Deitada Inferior Frontal",
            (x_base_util, oy, oz + R),
            (larg_util_total, larg_trav_acab, E),
            material, fita_c1=True, fita_c2=False, fita_l1=False, fita_l2=False,
            color=cor
        ))
        # - Travessa Deitada Inferior Traseira: encostada na traseira (oy + P - larg_trav_acab até oy + P)
        groups.append(_chapa(
            "Armário - Travessa Deitada Inferior Traseira",
            (x_base_util, oy + P - larg_trav_acab, oz + R),
            (larg_util_total, larg_trav_acab, E),
            material, fita_c1=False, fita_c2=False, fita_l1=False, fita_l2=False,
            color=cor
        ))

        # 3.2. Travessa deitada superior de acabamento (plano XY, espessura em Z):
        # Fica acima da caixaria com largura de pelo menos 100 mm (oy até oy + 100 mm),
        # posicionada no topo total (Z = oz + A - E), cobrindo o topo frontal entre tamponamentos.
        larg_trav_sup = max(0.100, larg_trav_acab)
        groups.append(_chapa(
            "Armário - Travessa Deitada Superior Frontal",
            (x_base_util, oy, oz + A - E),
            (larg_util_total, larg_trav_sup, E),
            material, fita_c1=True, fita_c2=False, fita_l1=False, fita_l2=False,
            color=cor
        ))

        # 4. Caixarias Superiores
        # As caixas se apoiam sobre as travessas inferiores deitadas (Z = oz + R + E)
        # e terminam com seu topo imediatamente abaixo da travessa superior (Z = oz + A - E).
        alt_caixaria = max(0.2, A - R - 2 * E)
        # Profundidade útil da caixaria: recuada em 70 mm da frente (oy + recuo_correr até oy + P)
        prof_caixaria = max(0.1, P - recuo_correr)
        y_caixaria = oy + recuo_correr
        z_caixaria = oz + R + E

        # Altura livre do maleiro
        h_maleiro = min(alt_caixaria * 0.4, max(0.25, alt_maleiro_mm / 1000.0))

        if is_isoladas:
            # ── Modo Caixas Isoladas: Cada caixa tem laterais esquerda e direita próprias ──
            larg_caixa_indiv = larg_util_total / n_caixas
            larg_interna_indiv = max(0.05, larg_caixa_indiv - 2 * E)
            alt_interna_caixa = max(0.05, alt_caixaria - 2 * E)
            prof_util_fundo = prof_caixaria - CaixaMixin._calc_desconto_traseiro_fundo(tipo_fundo, esp_fundo_mm, recuo_fundo_mm)

            for i in range(n_caixas):
                cx_ox = x_base_util + i * larg_caixa_indiv
                prefix = f"Caixa {i + 1}"

                # Base e Topo da caixa individual
                groups.append(_chapa(
                    f"{prefix} - Base Inferior",
                    (cx_ox + E, y_caixaria, z_caixaria),
                    (larg_interna_indiv, prof_caixaria, E),
                    material, fita_c1=True, color=cor
                ))
                groups.append(_chapa(
                    f"{prefix} - Topo Superior",
                    (cx_ox + E, y_caixaria, z_caixaria + alt_caixaria - E),
                    (larg_interna_indiv, prof_caixaria, E),
                    material, fita_c1=True, color=cor
                ))

                # Lateral Esquerda e Direita da caixa individual
                groups.append(_chapa(
                    f"{prefix} - Lateral Esquerda",
                    (cx_ox, y_caixaria, z_caixaria),
                    (E, prof_caixaria, alt_caixaria),
                    material, fita_c1=True, color=cor
                ))
                groups.append(_chapa(
                    f"{prefix} - Lateral Direita",
                    (cx_ox + larg_caixa_indiv - E, y_caixaria, z_caixaria),
                    (E, prof_caixaria, alt_caixaria),
                    material, fita_c1=True, color=cor
                ))

                # Fundo da caixa individual
                fundo_grp = CaixaMixin.build_fundo_board(
                    prefixo=prefix,
                    largura_interna_m=larg_interna_indiv,
                    altura_interna_m=alt_interna_caixa,
                    largura_total_m=larg_caixa_indiv,
                    altura_total_caixa_m=alt_caixaria,
                    prof_total_m=prof_caixaria,
                    esp_lateral_m=E,
                    origin_caixa=(cx_ox, y_caixaria, z_caixaria),
                    z_interno_base_m=z_caixaria + E,
                    material_fundo=material,
                    tipo_fundo=tipo_fundo,
                    esp_fundo_mm=esp_fundo_mm,
                    recuo_fundo_mm=recuo_fundo_mm,
                )
                if fundo_grp:
                    groups.append(fundo_grp)

                # Divisória Horizontal do Maleiro individual
                z_maleiro = z_caixaria + alt_caixaria - E - h_maleiro - E
                groups.append(_chapa(
                    f"{prefix} - Divisória Maleiro",
                    (cx_ox + E, y_caixaria, z_maleiro),
                    (larg_interna_indiv, prof_util_fundo, E),
                    material, fita_c1=True, color=cor
                ))
        else:
            # ── Modo Caixa Única: Laterais externas e divisórias verticais simples ──
            larg_interna_total = max(0.05, larg_util_total - 2 * E)
            alt_interna_total = max(0.05, alt_caixaria - 2 * E)
            n_divs = n_caixas - 1
            larg_vao = (larg_interna_total - n_divs * E) / n_caixas
            prof_util_fundo = prof_caixaria - CaixaMixin._calc_desconto_traseiro_fundo(tipo_fundo, esp_fundo_mm, recuo_fundo_mm)

            # Base inferior e tampo superior contínuos
            groups.append(_chapa(
                "Caixa Única - Base Inferior",
                (x_base_util + E, y_caixaria, z_caixaria),
                (larg_interna_total, prof_caixaria, E),
                material, fita_c1=True, color=cor
            ))
            groups.append(_chapa(
                "Caixa Única - Topo Superior",
                (x_base_util + E, y_caixaria, z_caixaria + alt_caixaria - E),
                (larg_interna_total, prof_caixaria, E),
                material, fita_c1=True, color=cor
            ))

            # Laterais externas da caixa única
            groups.append(_chapa(
                "Caixa Única - Lateral Esquerda",
                (x_base_util, y_caixaria, z_caixaria),
                (E, prof_caixaria, alt_caixaria),
                material, fita_c1=True, color=cor
            ))
            groups.append(_chapa(
                "Caixa Única - Lateral Direita",
                (x_base_util + larg_util_total - E, y_caixaria, z_caixaria),
                (E, prof_caixaria, alt_caixaria),
                material, fita_c1=True, color=cor
            ))

            # Fundo geral
            fundo_grp = CaixaMixin.build_fundo_board(
                prefixo="Caixa Única",
                largura_interna_m=larg_interna_total,
                altura_interna_m=alt_interna_total,
                largura_total_m=larg_util_total,
                altura_total_caixa_m=alt_caixaria,
                prof_total_m=prof_caixaria,
                esp_lateral_m=E,
                origin_caixa=(x_base_util, y_caixaria, z_caixaria),
                z_interno_base_m=z_caixaria + E,
                material_fundo=material,
                tipo_fundo=tipo_fundo,
                esp_fundo_mm=esp_fundo_mm,
                recuo_fundo_mm=recuo_fundo_mm,
            )
            if fundo_grp:
                groups.append(fundo_grp)

            # Divisórias verticais simples entre os vãos
            for d in range(n_divs):
                x_div = x_base_util + E + (d + 1) * larg_vao + d * E
                groups.append(_chapa(
                    f"Caixa Única - Divisória Vertical {d + 1}",
                    (x_div, y_caixaria, z_caixaria + E),
                    (E, prof_util_fundo, alt_interna_total),
                    material, fita_c1=True, color=cor
                ))

            # Divisórias horizontais de maleiro em cada vão
            z_maleiro = z_caixaria + alt_caixaria - E - h_maleiro - E
            for v in range(n_caixas):
                x_vao = x_base_util + E + v * (larg_vao + E)
                groups.append(_chapa(
                    f"Caixa Única - Divisória Maleiro Vão {v + 1}",
                    (x_vao, y_caixaria, z_maleiro),
                    (larg_vao, prof_util_fundo, E),
                    material, fita_c1=True, color=cor
                ))

        return groups



