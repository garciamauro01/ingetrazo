# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations
import math
from typing import Any
from PySide6.QtGui import QVector3D
from core.group import Group
from core.mesh import Mesh
from ..builders.chapa_builder import build_chapa
from ..builders.chapa_spec import ChapaSpec, PapelChapa, ModuloMaterialContext
from ..builders.fronts import FrentesKitBuilder
from ..builders.mesh_utils import create_polygon_board_group
from ..builders.parts import _chapa, _chapa_frente



class CantoEspecialBuilder:
    """Construtor especializado para cantos retos, cantos L, porta-temperos e balcões para forno embutido."""

    @staticmethod
    def get_material_color(material: str) -> tuple[float, float, float]:
        from ..domain.materials_catalog import get_material_color
        return get_material_color(material)

    @staticmethod
    def _calc_desconto_traseiro_fundo(*args, **kwargs) -> float:
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder._calc_desconto_traseiro_fundo(*args, **kwargs)

    @staticmethod
    def build_caixa_inferior(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_caixa_inferior(*args, **kwargs)

    @staticmethod
    def build_fundo_board(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_fundo_board(*args, **kwargs)

    @staticmethod
    def build_caixa_gaveta(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_caixa_gaveta(*args, **kwargs)

    @classmethod
    def build_canto_reto(
        cls, largura_mm: float, altura_mm: float, prof_mm: float,
        esp_mm: float = 15.0, rodape_mm: float = 100.0,
        lado_cego: str = "esquerda",
        largura_porta_mm: float | None = None,
        largura_cego_mm: float | None = None,
        esp_montante_mm: float | None = None,
        tem_fechamento: bool = True,
        tem_regua_fechamento: bool = False,
        larg_regua_fechamento_mm: float = 50.0,
        dist_regua_fechamento_mm: float | None = None,
        num_prateleiras: int = 1,
        material: str = "MDF Branco TX 15mm", material_frentes: str | None = None,
        esp_frentes_mm: float | None = None,
        tipo_fundo: str = "rasgo", esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0, prof_rasgo_mm: float = 5.0,
        folga_fundo_mm: float = 2.0,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto", puxador_pos: str = "padrao", desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        larg_travessa_frontal_mm: float = 70.0,
        larg_travessa_traseira_mm: float = 70.0,
        travessa_frontal_em_pe: bool = False,
        travessa_traseira_em_pe: bool = False,
        recuo_porta_topo_mm: float = 50.0,
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
    ) -> list[Group]:
        if mat_ctx is None:
            mat_ctx = ModuloMaterialContext(
                material_caixa=material,
                material_frentes=material_frentes or material,
            )
        groups, info = cls.build_caixa_inferior(
            prefixo="Canto Reto",
            largura_mm=largura_mm, altura_mm=altura_mm, prof_mm=prof_mm,
            esp_mm=esp_mm, rodape_mm=rodape_mm, material=material, offset=offset,
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
        )
        ox, oy, oz = info["ox"], info["oy"], info["oz"]
        L, A, P, E, R = info["L"], info["A"], info["P"], info["E"], info["R"]
        altura_caixa, largura_interna = info["altura_caixa"], info["largura_interna"]
        cor = info["cor"]
        mat_frente = material_frentes or material
        E_frente = (esp_frentes_mm or esp_mm) / 1000.0
        cor_frente = cls.get_material_color(mat_frente)

        # Montante Cego e Vão da Porta
        # 1. Se largura_cego_mm for explicitamente fornecida, tem prioridade
        if largura_cego_mm is not None and float(largura_cego_mm) > 0:
            larg_cego = max(0.05, min(largura_interna - 0.15, float(largura_cego_mm) / 1000.0))
            vao_porta = max(0.15, largura_interna - larg_cego)
        # 2. Se largura_porta_mm for fornecida, calcula larg_cego a partir da porta
        elif largura_porta_mm is not None and float(largura_porta_mm) > 0:
            larg_p_m = float(largura_porta_mm) / 1000.0
            vao_porta = min(largura_interna - 0.20, larg_p_m)
            larg_cego = max(0.15, largura_interna - vao_porta)
        # 3. Senão usa padrão de profundidade
        else:
            larg_cego = min(0.50, P - 0.05)
            vao_porta = max(0.15, L - E - larg_cego - E)

        is_cego_esq = str(lado_cego or "esquerda").strip().lower().startswith("esq")

        fundo_grp = cls.build_fundo_board(
            prefixo="Canto Reto",
            largura_interna_m=largura_interna,
            altura_interna_m=altura_caixa - 2 * E,
            largura_total_m=L,
            altura_total_caixa_m=altura_caixa,
            prof_total_m=P,
            esp_lateral_m=E,
            origin_caixa=(ox, oy, oz + R),
            z_interno_base_m=oz + R + E,
            tipo_fundo=tipo_fundo,
            esp_fundo_mm=esp_fundo_mm,
            recuo_fundo_mm=recuo_fundo_mm,
            prof_rasgo_mm=prof_rasgo_mm,
            folga_fundo_mm=folga_fundo_mm,
        )
        if fundo_grp:
            groups.append(fundo_grp)

        recuo_topo = (recuo_porta_topo_mm / 1000.0) if travessa_frontal_em_pe else 0.0
        folga_f = FrentesKitBuilder.resolve_folga_mm(mat_ctx=mat_ctx) / 1000.0
        alt_porta = max(0.05, altura_caixa - recuo_topo - (2.0 * folga_f))

        if is_cego_esq:
            # Lado cego à esquerda, porta à direita
            x_cego = ox + E
            x_porta = ox + E + larg_cego + folga_f
            porta_side = "right"
        else:
            # Lado cego à direita, porta à esquerda
            x_cego = ox + L - E - larg_cego
            x_porta = ox + folga_f
            porta_side = "left"

        if tem_fechamento:
            groups.append(_chapa(
                "Canto Reto - Montante Cego", (x_cego, oy - E_frente, oz + R),
                (larg_cego, E_frente, altura_caixa), mat_frente, fita_c1=True, fita_l1=True, color=cor_frente
            ))

            # Régua de fechamento perpendicular (retorno 90°) a partir da tampa cega
            if tem_regua_fechamento:
                larg_r_m = max(0.020, float(larg_regua_fechamento_mm) / 1000.0)
                # Posição da régua (dist_regua_fechamento_mm):
                # Se especificado, mede o afastamento em X a partir da borda externa da tampa cega (junto à lateral do módulo).
                # Se não especificado (None), fica na extremidade interna da tampa cega (junto ao vão da porta).
                if dist_regua_fechamento_mm is not None and float(dist_regua_fechamento_mm) > 0:
                    d_r_m = min(larg_cego - E_frente, max(0.0, float(dist_regua_fechamento_mm) / 1000.0))
                    if is_cego_esq:
                        x_regua = x_cego + d_r_m
                    else:
                        x_regua = (x_cego + larg_cego) - d_r_m - E_frente
                else:
                    if is_cego_esq:
                        x_regua = x_cego + larg_cego - E_frente
                    else:
                        x_regua = x_cego

                y_regua = oy - E_frente - larg_r_m

                groups.append(_chapa(
                    "Canto Reto - Regua Fechamento",
                    (x_regua, y_regua, oz + R),
                    (E_frente, larg_r_m, altura_caixa),
                    mat_frente, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True, color=cor_frente
                ))

        if vao_porta > 0.15:
            groups.append(_chapa_frente(
                "Canto Reto - Porta", (x_porta, oy - E_frente, oz + R + folga_f),
                (vao_porta - (2.0 * folga_f), E_frente, alt_porta), mat_ctx,
                color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                door_side=porta_side, is_upper=False
            ))

        desc_fundo = cls._calc_desconto_traseiro_fundo(tipo_fundo, esp_fundo_mm, recuo_fundo_mm)
        recuo_frontal_prat = 0.020
        prof_prat = max(0.10, P - desc_fundo - recuo_frontal_prat)

        # Prateleiras internas (suporta num_prateleiras)
        num_prat = max(0, int(num_prateleiras))
        if num_prat > 0:
            espaco_util = altura_caixa - 2 * E
            passo = espaco_util / (num_prat + 1)
            for i in range(1, num_prat + 1):
                z_p = oz + R + E + (i * passo)
                groups.append(_chapa(
                    f"Canto Reto - Prateleira {i}" if num_prat > 1 else "Canto Reto - Prateleira",
                    (ox + E, oy + recuo_frontal_prat, z_p),
                    (largura_interna - 0.002, prof_prat, E),
                    material, fita_c1=True, color=cor
                ))

        return groups

    @classmethod
    def build_canto_l(
        cls, largura_mm: float, altura_mm: float, prof_mm: float,
        larg_asa_esq_mm: float = 550.0, larg_asa_dir_mm: float = 550.0,
        tem_batente_canto: bool = False,
        esp_mm: float = 15.0, rodape_mm: float = 100.0,
        num_prateleiras: int = 1,
        material: str = "MDF Branco TX 15mm", material_frentes: str | None = None,
        esp_frentes_mm: float | None = None,
        tipo_fundo: str = "rasgo", esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0, prof_rasgo_mm: float = 5.0,
        folga_fundo_mm: float = 2.0,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto", puxador_pos: str = "padrao", desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        larg_travessa_frontal_mm: float = 70.0,
        larg_travessa_traseira_mm: float = 70.0,
        travessa_frontal_em_pe: bool = False,
        travessa_traseira_em_pe: bool = False,
        recuo_porta_topo_mm: float = 50.0,
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
    ) -> list[Group]:
        """Gera um balcão de Canto L autêntico com 2 aberturas frontais em 90°, pilar/batente de quina interna,

        travessas estruturais (incluindo travessa central de apoio do tampo) e 2 portas de canto.
        """
        if mat_ctx is None:
            mat_ctx = ModuloMaterialContext(
                material_caixa=material,
                material_frentes=material_frentes or material,
            )
        ox, oy, oz = offset
        Lx = largura_mm / 1000.0
        Ly = prof_mm / 1000.0
        A = altura_mm / 1000.0
        E = esp_mm / 1000.0
        R = rodape_mm / 1000.0
        altura_caixa = A - R

        # Profundidade de cada asa (lados esquerdo e direito)
        # Px (direita, ala X) = profundidade ao longo de Y
        # Py (esquerda, ala Y) = largura ao longo de X
        # O limite é min(Lx, Ly) - 0.20 apenas quando a asa não ocupa a dimensão inteira;
        # se o usuário pede 1000mm em um módulo de 1000mm, respeita 1000.
        Px = larg_asa_dir_mm / 1000.0
        Px = max(0.35, Px)
        Py = larg_asa_esq_mm / 1000.0
        Py = max(0.35, Py)
        # Clamp only when asa would exceed module dimension
        Px = min(Px, Ly)
        Py = min(Py, Lx)

        mat_frente = material_frentes or material
        E_frente = (esp_frentes_mm or esp_mm) / 1000.0
        cor = cls.get_material_color(material)
        cor_frente = cls.get_material_color(mat_frente)

        LTF = larg_travessa_frontal_mm / 1000.0
        LTT = larg_travessa_traseira_mm / 1000.0

        mat_fita_cx = material_fita_caixa or material
        cor_fita_cx = cls.get_material_color(mat_fita_cx) if material_fita_caixa else None

        mat_trav = material_travessas or material
        E_trav = (esp_travessas_mm / 1000.0) if (esp_travessas_mm and esp_travessas_mm > 0) else E
        cor_trav = cls.get_material_color(mat_trav)

        mat_fita_tr = material_fita_travessas or mat_trav
        cor_fita_tr = cls.get_material_color(mat_fita_tr) if material_fita_travessas else None

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
        else:
            f_c1_tf, f_c2_tf, f_l1_tf, f_l2_tf = True, False, False, False
            f_c1_tt, f_c2_tt, f_l1_tt, f_l2_tt = False, False, False, False

        groups = []

        # Usinagens de junção
        ops_lat = []
        if gerar_furacao:
            from ..production.machining import make_cabinet_joint_holes
            usar_mini = ("minifix" in str(dispositivo_fixacao).lower())
            ops_lat.extend([
                o.to_dict() for o in make_cabinet_joint_holes(
                    comprimento_junta_mm=Px * 1000.0,
                    posicao_borda_mm=(esp_mm / 2.0),
                    face="traseira",
                    usar_minifix=usar_mini,
                )
            ])

        # ── 1. LATERAIS EXTERNAS DA CAIXARIA (Referência canto l.igz) ──────────
        # Lateral Esquerda inteiriça / Fundo Ala Y (ao longo de Y em X = ox):
        # Ocupa toda a extensão externa de Y: de oy até oy + Ly
        # Vai do chão (oz + R) até o topo (oz + A)
        groups.append(_chapa(
            "Canto L - Lateral Esquerda Inteiriça",
            (ox, oy, oz + R),
            (E, Ly, altura_caixa),
            material, fita_c1=True, fita_l1=True, color=cor,
            material_fita=mat_fita_cx, cor_fita=cor_fita_cx, operacoes=ops_lat,
        ))

        # Lateral Direita da Ala X (ao longo de Y em X = ox + Lx - E):
        # Ocupa a profundidade Px da Ala X: de oy + Ly - Px até oy + Ly
        # Vai do chão (oz + R) até o topo (oz + A)
        groups.append(_chapa(
            "Canto L - Lateral Direita",
            (ox + Lx - E, oy + Ly - Px, oz + R),
            (E, Px, altura_caixa),
            material, fita_c1=True, fita_l1=True, color=cor,
            material_fita=mat_fita_cx, cor_fita=cor_fita_cx, operacoes=ops_lat,
        ))

        # Fechamento Frontal Perpendicular da Ala Y (em Y = oy):
        # Fecha a extremidade frontal da Ala Y: de X = ox + E até ox + Py
        # Vai do chão (oz + R) até o topo (oz + A)
        # Borda +X (direita) fica aparente na fachada ao lado da Porta Ala Y -> fita_l2=True
        # Borda inferior (-Z) e superior (+Z) -> fita_c1=True
        larg_fechamento_frontal = max(0.05, Py - E)
        groups.append(_chapa(
            "Canto L - Lateral Frontal Ala Y",
            (ox + E, oy, oz + R),
            (larg_fechamento_frontal, E, altura_caixa),
            material, fita_c1=True, fita_l1=True, fita_l2=True, color=cor,
            material_fita=mat_fita_cx, cor_fita=cor_fita_cx, operacoes=ops_lat,
        ))

        # ── 2. BASES INFERIORES EM L (Referência canto l.igz) ─────────────────
        # Base da Ala X:
        # Fica entre as laterais externas: de X = ox + E até ox + Lx - E
        # Profundidade Px: de Y = oy + Ly - Px até oy + Ly
        # Borda frontal em -Y fica voltada para as portas -> fita_c1=True
        larg_base_x = max(0.10, Lx - 2 * E)
        groups.append(_chapa(
            "Canto L - Base Ala X",
            (ox + E, oy + Ly - Px, oz + R),
            (larg_base_x, Px, E),
            material, fita_c1=True, color=cor,
            material_fita=mat_fita_cx, cor_fita=cor_fita_cx,
        ))

        # Base da Ala Y:
        # Encaixa perpendicularmente na Base X:
        # Em X ocupa de ox + E até ox + Py
        # Em Y ocupa de oy + E até oy + Ly - Px
        # Borda frontal em +X fica voltada para a Porta Ala Y -> fita_l2=True
        larg_base_y = max(0.05, Py - E)
        prof_base_y = max(0.05, Ly - Px - E)
        groups.append(_chapa(
            "Canto L - Base Ala Y",
            (ox + E, oy + E, oz + R),
            (larg_base_y, prof_base_y, E),
            material, fita_c1=True, fita_l2=True, color=cor,
            material_fita=mat_fita_cx, cor_fita=cor_fita_cx,
        ))

        # ── 3. FUNDO TRASEIRO DA ALA X ───────────────────────────────────────
        if tipo_fundo != "sem_fundo":
            E_fundo = esp_fundo_mm / 1000.0
            recuo_m = recuo_fundo_mm / 1000.0
            py_fundo = (oy + Ly - recuo_m - E_fundo) if tipo_fundo == "rasgo" else (oy + Ly - E_fundo)
            groups.append(_chapa(
                "Canto L - Fundo Traseiro",
                (ox + E, py_fundo, oz + R),
                (larg_base_x, E_fundo, altura_caixa),
                material, color=cor,
            ))

        # ── 4. TRAVESSAS SUPERIORES ESTRUTURAIS EM PÉ (Apoio de Tampo) ────────
        # ── 4. TRAVESSAS SUPERIORES ESTRUTURAIS (Horizontais / Verticais) ──────
        # Travessas Frontais (Ala X e Ala Y):
        if travessa_frontal_em_pe:
            alt_trav_f = LTF if LTF > 0.02 else 0.070
            z_trav_f = oz + R + altura_caixa - alt_trav_f
            # Ala X (em pé vertical em Y = oy + Ly - Px):
            groups.append(_chapa(
                "Canto L - Travessa Frontal Ala X",
                (ox + E, oy + Ly - Px, z_trav_f),
                (larg_base_x, E_trav, alt_trav_f),
                mat_trav, fita_c1=f_c1_tf, fita_c2=f_c2_tf, fita_l1=f_l1_tf, fita_l2=f_l2_tf, color=cor_trav,
                material_fita=mat_fita_tr, cor_fita=cor_fita_tr,
            ))
            # Ala Y (em pé vertical em X = ox + Py - E_trav):
            groups.append(_chapa(
                "Canto L - Travessa Frontal Ala Y",
                (ox + Py - E_trav, oy + E, z_trav_f),
                (E_trav, prof_base_y, alt_trav_f),
                mat_trav, fita_c1=f_c1_tf, fita_c2=f_c2_tf, fita_l1=f_l1_tf, fita_l2=f_l2_tf, color=cor_trav,
                material_fita=mat_fita_tr, cor_fita=cor_fita_tr,
            ))
        else:
            # Travessas deitadas / horizontais no topo (Z = topo - E_trav)
            z_trav_f = oz + R + altura_caixa - E_trav
            # Ala X (deitada no topo em Y = oy + Ly - Px):
            groups.append(_chapa(
                "Canto L - Travessa Frontal Ala X",
                (ox + E, oy + Ly - Px, z_trav_f),
                (larg_base_x, LTF, E_trav),
                mat_trav, fita_c1=f_c1_tf, fita_c2=f_c2_tf, fita_l1=f_l1_tf, fita_l2=f_l2_tf, color=cor_trav,
                material_fita=mat_fita_tr, cor_fita=cor_fita_tr,
            ))
            # Ala Y (deitada no topo em X = ox + Py - LTF):
            groups.append(_chapa(
                "Canto L - Travessa Frontal Ala Y",
                (ox + Py - LTF, oy + E, z_trav_f),
                (LTF, prof_base_y, E_trav),
                mat_trav, fita_c1=f_c1_tf, fita_c2=f_c2_tf, fita_l1=f_l1_tf, fita_l2=f_l2_tf, color=cor_trav,
                material_fita=mat_fita_tr, cor_fita=cor_fita_tr,
            ))

        # Travessa Traseira da Ala X (em pé vertical ou deitada horizontal):
        if travessa_traseira_em_pe:
            alt_trav_t = LTT if LTT > 0.02 else 0.070
            z_trav_t = oz + R + altura_caixa - alt_trav_t
            groups.append(_chapa(
                "Canto L - Travessa Traseira Ala X",
                (ox + E, oy + Ly - E_trav, z_trav_t),
                (larg_base_x, E_trav, alt_trav_t),
                mat_trav, fita_c1=f_c1_tt, fita_c2=f_c2_tt, fita_l1=f_l1_tt, fita_l2=f_l2_tt, color=cor_trav,
                material_fita=mat_fita_tr, cor_fita=cor_fita_tr,
            ))
        else:
            z_trav_t = oz + R + altura_caixa - E_trav
            groups.append(_chapa(
                "Canto L - Travessa Traseira Ala X",
                (ox + E, oy + Ly - LTT, z_trav_t),
                (larg_base_x, LTT, E_trav),
                mat_trav, fita_c1=f_c1_tt, fita_c2=f_c2_tt, fita_l1=f_l1_tt, fita_l2=f_l2_tt, color=cor_trav,
                material_fita=mat_fita_tr, cor_fita=cor_fita_tr,
            ))

        # ── 5. PORTAS / FRENTES DE CANTO L (2 Portas em 90° abrindo para lados opostos) ─
        # Quando as travessas frontais estão em pé, desconta o recuo do topo para pegada de mão / perfil
        recuo_topo = (recuo_porta_topo_mm / 1000.0) if travessa_frontal_em_pe else 0.0
        folga_f = FrentesKitBuilder.resolve_folga_mm(mat_ctx=mat_ctx) / 1000.0
        alt_porta = max(0.10, altura_caixa - recuo_topo - (2.0 * folga_f))
        z_porta = oz + R + folga_f
        folga_canto = folga_f  # Folga técnica na quina interna de 90°

        # Batente de quina interna (opcional): fecha o vão de 90° com a mesma
        # espessura/material das frentes. Sem ele, mantém-se o cruzamento
        # atual das portas (a porta da Ala X recua a espessura da Ala Y).
        larg_vao_y = max(0.10, Ly - Px - E)
        x_batente = ox + Py
        y_batente = oy + Ly - Px - E_frente
        usar_batente = (
            bool(tem_batente_canto)
            and (larg_vao_y - E_frente - folga_canto - folga_f) >= 0.08
            and (Py + E_frente + folga_canto) < (Lx - folga_f)
        )
        if usar_batente:
            groups.append(_chapa(
                "Canto L - Batente Quina",
                (x_batente, y_batente, oz + R),
                (E_frente, E_frente, altura_caixa),
                mat_frente, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor_frente,
            ))

        # Porta 2 (Ala Y - plano YZ, na face frontal da Ala Y):
        # Fica em X = ox + Py (com espessura de ox + Py até ox + Py + E_frente)
        # A porta é sobreposta: cobre a lateral frontal da Ala Y e termina a
        # folga externa configurada (oy + folga_f), não dentro da lateral.
        # Na quina interna termina em Y = oy + Ly - Px - folga_canto
        # Abertura para o lado externo oposto (-Y / lateral externa): dobradiças na extremidade frontal ("right"),
        # puxador na extremidade da quina (+Y)
        larg_porta_y = max(0.08, Ly - Px - folga_canto - folga_f)
        if usar_batente:
            # Com batente, a porta da Ala Y encosta nele com a folga configurada
            larg_porta_y = max(
                0.08, Ly - Px - E_frente - folga_canto - folga_f)
        y_porta_y = oy + folga_f
        groups.append(_chapa_frente(
            "Canto L - Porta Ala Y",
            (ox + Py, y_porta_y, z_porta),
            (E_frente, larg_porta_y, alt_porta),
            mat_ctx, color=cor_frente,
            puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
            desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
            door_side="left", is_upper=False,
        ))

        # Porta 1 (Ala X - plano XZ, na face frontal da Ala X):
        # Fica em Y = oy + Ly - Px - E_frente (com espessura de Y = oy + Ly - Px - E_frente até oy + Ly - Px)
        # Para NÃO encavalar nem colidir com a Porta Ala Y (que ocupa até X = ox + Py + E_frente),
        # a Porta Ala X inicia em X = ox + Py + E_frente + folga_canto.
        # A porta é sobreposta: cobre a lateral direita e termina a folga externa da
        # borda externa do módulo (ox + Lx - folga_f), não dentro da lateral.
        # Abertura para o lado externo (+X): dobradiças à direita ("right"), puxador na extremidade da quina (esquerda)
        x_porta_x = ox + Py + E_frente + folga_canto
        larg_porta_x = max(0.08, (ox + Lx - folga_f) - x_porta_x)
        groups.append(_chapa_frente(
            "Canto L - Porta Ala X",
            (x_porta_x, oy + Ly - Px - E_frente, z_porta),
            (larg_porta_x, E_frente, alt_porta),
            mat_ctx, color=cor_frente,
            puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
            desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
            door_side="right", is_upper=False,
        ))

        # ── 6. PRATELEIRAS INTERNAS EM L ──────────────────────────────────────
        if num_prateleiras > 0:
            z_prat = oz + R + E + (altura_caixa - 2 * E) / 2.0
            desc_fundo = cls._calc_desconto_traseiro_fundo(tipo_fundo, esp_fundo_mm, recuo_fundo_mm)
            # Prateleira Ala X
            groups.append(_chapa(
                "Canto L - Prateleira Ala X",
                (ox + Py, oy + Ly - Px + 0.020, z_prat),
                (max(0.05, Lx - Py - E - 0.004), max(0.05, Px - desc_fundo - 0.024), E),
                material, fita_c1=True, color=cor,
            ))
            # Prateleira Ala Y
            groups.append(_chapa(
                "Canto L - Prateleira Ala Y",
                (ox + E + desc_fundo, oy + E + 0.020, z_prat),
                (max(0.05, Py - desc_fundo - E), max(0.05, Ly - Px - E - 0.024), E),
                material, fita_c1=True, color=cor,
            ))

        # ── 7. RODAPÉ FRONTAL EM L ────────────────────────────────────────────
        if R > 0.01:
            # Rodapé sob a Ala X
            groups.append(_chapa(
                "Canto L - Rodape Ala X",
                (ox + Py, oy + Ly - Px + 0.050, oz),
                (max(0.05, Lx - Py), E, R),
                material, color=cor,
            ))
            # Rodapé sob a Ala Y
            groups.append(_chapa(
                "Canto L - Rodape Ala Y",
                (ox + Py - 0.050 - E, oy + E, oz),
                (E, max(0.05, Ly - Px - E), R),
                material, color=cor,
            ))

        return groups

    @classmethod
    def build_porta_tempero(
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
        larg_travessa_frontal_mm: float = 70.0,
        larg_travessa_traseira_mm: float = 70.0,
        travessa_frontal_em_pe: bool = False,
        travessa_traseira_em_pe: bool = False,
        recuo_porta_topo_mm: float = 50.0,
        material_travessas: str | None = None,
        esp_travessas_mm: float | None = None,
        fita_travessas_modo: str = "frontal_1L",
        fita_travessas_faces: dict[str, bool] | None = None,
        fita_caixa_modo: str = "frontal_1L",
        material_fita_caixa: str | None = None,
        material_fita_travessas: str | None = None,
        gerar_furacao: bool = True,
        dispositivo_fixacao: str = "minifix_cavilha",
        tipo_estrutura_tempero: str = "mdf",
        cor_aramado: str = "cromado",
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> list[Group]:
        if mat_ctx is None:
            mat_ctx = ModuloMaterialContext(
                material_caixa=material,
                material_frentes=material_frentes or material,
            )
        groups, info = cls.build_caixa_inferior(
            prefixo="Porta-Tempero",
            largura_mm=largura_mm, altura_mm=altura_mm, prof_mm=prof_mm,
            esp_mm=esp_mm, rodape_mm=rodape_mm, material=material, offset=offset,
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
        )
        ox, oy, oz = info["ox"], info["oy"], info["oz"]
        L, A, P, E, R = info["L"], info["A"], info["P"], info["E"], info["R"]
        altura_caixa, largura_interna = info["altura_caixa"], info["largura_interna"]
        cor = info["cor"]
        mat_frente = material_frentes or material
        E_frente = (esp_frentes_mm or esp_mm) / 1000.0
        cor_frente = cls.get_material_color(mat_frente)

        fundo_grp = cls.build_fundo_board(
            prefixo="Porta-Tempero",
            largura_interna_m=largura_interna,
            altura_interna_m=altura_caixa - 2 * E,
            largura_total_m=L,
            altura_total_caixa_m=altura_caixa,
            prof_total_m=P,
            esp_lateral_m=E,
            origin_caixa=(ox, oy, oz + R),
            z_interno_base_m=oz + R + E,
            tipo_fundo=tipo_fundo,
            esp_fundo_mm=esp_fundo_mm,
            recuo_fundo_mm=recuo_fundo_mm,
            prof_rasgo_mm=prof_rasgo_mm,
            folga_fundo_mm=folga_fundo_mm,
        )
        if fundo_grp:
            groups.append(fundo_grp)

        folga_f = FrentesKitBuilder.resolve_folga_mm(mat_ctx=mat_ctx) / 1000.0
        recuo_topo = (recuo_porta_topo_mm / 1000.0) if travessa_frontal_em_pe else 0.0
        alt_frente = max(0.05, altura_caixa - recuo_topo - (2.0 * folga_f))
        nome_frente = "Porta-Tempero - Frente Gaveta 1"
        groups.append(_chapa_frente(
            nome_frente, (ox + folga_f, oy - E_frente, oz + R + folga_f),
            (L - (2.0 * folga_f), E_frente, alt_frente), mat_ctx,
            papel=PapelChapa.FRENTE_GAVETA, color=cor_frente,
            puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos, desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo, door_side="drawer", is_upper=False
        ))

        # Se for 100% MDF, gera a torre estrutural com bandejas em MDF vinculadas à frente deslizante
        if str(tipo_estrutura_tempero).lower() != "aramado":
            folga_corredica_total = 0.026  # 13mm de cada lado para corrediças telescópicas padrão
            larg_chassi = max(0.06, largura_interna - folga_corredica_total)
            x_chassi = ox + E + (folga_corredica_total / 2.0)
            prof_chassi = max(0.15, P - 0.05)
            y_chassi = oy + 0.005  # encostado atrás da contra-testa e frente
            z_chassi_base = oz + R + E + 0.02
            alt_torre = max(0.25, altura_caixa - recuo_topo - 2 * E - 0.05)

            # 1. Traseira vertical estrutural da torre (une a base inferior à bandeja superior com rigidez)
            g_traseira = _chapa(
                "Porta-Tempero - Traseira Torre",
                (x_chassi, y_chassi + prof_chassi - E, z_chassi_base),
                (larg_chassi, E, alt_torre),
                material, fita_c1=True, color=cor
            )
            g_traseira.ext.setdefault("trazomob", {})["linked_piece"] = nome_frente
            groups.append(g_traseira)

            # 2. Contra-testa inferior (fixa a estrutura diretamente atrás da frente do gavetão)
            alt_cf = 0.090  # 90mm de altura
            g_cf = _chapa(
                "Porta-Tempero - Contra-Testa",
                (x_chassi, y_chassi, z_chassi_base),
                (larg_chassi, E, alt_cf),
                material, fita_c1=True, color=cor
            )
            g_cf.ext.setdefault("trazomob", {})["linked_piece"] = nome_frente
            groups.append(g_cf)

            # 3. Base inferior estrutural (onde a corrediça lateral se ancora)
            prof_base_util = prof_chassi - 2 * E
            g_base_inf = _chapa(
                "Porta-Tempero - Base Gaveta Inferior",
                (x_chassi, y_chassi + E, z_chassi_base),
                (larg_chassi, prof_base_util, E),
                material, fita_c1=True, color=cor
            )
            g_base_inf.ext.setdefault("trazomob", {})["linked_piece"] = nome_frente
            groups.append(g_base_inf)

            # Laterais de contenção inferiores (Lat Esq Gaveta 1 e Lat Dir Gaveta 1 - servem também de apoio para corrediça)
            g_lat_esq1 = _chapa(
                "Porta-Tempero - Lat Esq Gaveta 1",
                (x_chassi, y_chassi + E, z_chassi_base + E),
                (E, prof_base_util, alt_cf - E),
                material, fita_c1=True, color=cor
            )
            g_lat_esq1.ext.setdefault("trazomob", {})["linked_piece"] = nome_frente
            groups.append(g_lat_esq1)

            g_lat_dir1 = _chapa(
                "Porta-Tempero - Lat Dir Gaveta 1",
                (x_chassi + larg_chassi - E, y_chassi + E, z_chassi_base + E),
                (E, prof_base_util, alt_cf - E),
                material, fita_c1=True, color=cor
            )
            g_lat_dir1.ext.setdefault("trazomob", {})["linked_piece"] = nome_frente
            groups.append(g_lat_dir1)

            # 4. Bandeja Superior (com base e laterais de contenção para temperos não caírem)
            z_bandeja_sup = z_chassi_base + (alt_torre * 0.55)
            alt_aba_sup = 0.060  # 60mm de guarda
            g_base_sup = _chapa(
                "Porta-Tempero - Base Superior",
                (x_chassi, y_chassi + E, z_bandeja_sup),
                (larg_chassi, prof_base_util, E),
                material, fita_c1=True, color=cor
            )
            g_base_sup.ext.setdefault("trazomob", {})["linked_piece"] = nome_frente
            groups.append(g_base_sup)

            # Abas laterais de contenção da bandeja superior
            g_lat_esq2 = _chapa(
                "Porta-Tempero - Aba Lateral Esq",
                (x_chassi, y_chassi + E, z_bandeja_sup + E),
                (E, prof_base_util, alt_aba_sup),
                material, fita_c1=True, color=cor
            )
            g_lat_esq2.ext.setdefault("trazomob", {})["linked_piece"] = nome_frente
            groups.append(g_lat_esq2)

            g_lat_dir2 = _chapa(
                "Porta-Tempero - Aba Lateral Dir",
                (x_chassi + larg_chassi - E, y_chassi + E, z_bandeja_sup + E),
                (E, prof_base_util, alt_aba_sup),
                material, fita_c1=True, color=cor
            )
            g_lat_dir2.ext.setdefault("trazomob", {})["linked_piece"] = nome_frente
            groups.append(g_lat_dir2)

            # Aba frontal da bandeja superior
            g_aba_fr_sup = _chapa(
                "Porta-Tempero - Aba Frontal Sup",
                (x_chassi + E, y_chassi, z_bandeja_sup),
                (larg_chassi - 2 * E, E, alt_aba_sup + E),
                material, fita_c1=True, color=cor
            )
            g_aba_fr_sup.ext.setdefault("trazomob", {})["linked_piece"] = nome_frente
            groups.append(g_aba_fr_sup)

        return groups

    @classmethod
    def build_balcao_forno(
        cls, largura_mm: float, altura_mm: float, prof_mm: float,
        esp_mm: float = 15.0, rodape_mm: float = 100.0,
        material: str = "MDF Branco TX 15mm", material_frentes: str | None = None,
        esp_frentes_mm: float | None = None,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto", puxador_pos: str = "padrao", desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        larg_travessa_frontal_mm: float = 70.0,
        larg_travessa_traseira_mm: float = 70.0,
        travessa_frontal_em_pe: bool = True,
        travessa_traseira_em_pe: bool = False,
        recuo_porta_topo_mm: float = 50.0,
        material_travessas: str | None = None,
        esp_travessas_mm: float | None = None,
        fita_travessas_modo: str = "frontal_1L",
        fita_travessas_faces: dict[str, bool] | None = None,
        fita_caixa_modo: str = "frontal_1L",
        material_fita_caixa: str | None = None,
        material_fita_travessas: str | None = None,
        gerar_furacao: bool = True,
        dispositivo_fixacao: str = "minifix_cavilha",
        tem_gaveta: bool = True,
        alt_gaveta_mm: float = 150.0,
        tipo_fundo_gaveta: str = "rasgo",
        folga_corredica_mm: float = 26.0,
        material_gaveta: str | None = None,
        esp_gaveta_mm: float = 15.0,
        material_fita_gaveta: str | None = None,
        material_fundo_gaveta: str | None = None,
        esp_fundo_gaveta_mm: float = 6.0,
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> list[Group]:
        """Gera caixa padrão de balcão inferior para forno com frente cega em MDF e gaveta opcional."""
        if mat_ctx is None:
            mat_ctx = ModuloMaterialContext(
                material_caixa=material,
                material_frentes=material_frentes or material,
            )
        groups, info = cls.build_caixa_inferior(
            prefixo="Balcao Forno",
            largura_mm=largura_mm, altura_mm=altura_mm, prof_mm=prof_mm,
            esp_mm=esp_mm, rodape_mm=rodape_mm, material=material, offset=offset,
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
        )
        ox, oy, oz = info["ox"], info["oy"], info["oz"]
        L, A, P, E, R = info["L"], info["A"], info["P"], info["E"], info["R"]
        altura_caixa, largura_interna = info["altura_caixa"], info["largura_interna"]
        cor = info["cor"]
        mat_frente = material_frentes or material
        E_frente = (esp_frentes_mm or esp_mm) / 1000.0
        cor_frente = cls.get_material_color(mat_frente)

        # Altura útil total interna
        alt_util_interna = altura_caixa - E  # base inferior desconta E

        # 1. Definição da altura do gavetão e apoio do forno
        folga_f = FrentesKitBuilder.resolve_folga_mm(mat_ctx=mat_ctx) / 1000.0
        if tem_gaveta:
            # Altura do vão da gaveta configurável (padrão ~150mm a 200mm)
            alt_gaveta_m = max(0.080, min(alt_util_interna - 0.450, float(alt_gaveta_mm) / 1000.0))
            z_fg = oz + R + folga_f  # folga inferior em relação à base

            # Prateleira Estrutural de Apoio do Forno (acima do gavetão)
            z_apoio = oz + R + E + alt_gaveta_m
            groups.append(_chapa(
                "Balcao Forno - Base Apoio Forno", (ox + E, oy, z_apoio),
                (largura_interna, P, E), material, fita_c1=True, color=cor
            ))

            # A frente da gaveta cobre o vão e a metade da prateleira de apoio,
            # deixando a folga configurada entre a frente da gaveta e a frente cega do forno.
            folga_entre_frentes = folga_f
            topo_fg = (z_apoio + E / 2.0) - (folga_entre_frentes / 2.0)
            alt_frente_gav = max(0.050, topo_fg - z_fg)

            # Gaveta - Frente em MDF com folga nas laterais
            groups.append(_chapa_frente(
                "Balcao Forno - Gaveta Frente", (ox + folga_f, oy - E_frente, z_fg),
                (L - (2.0 * folga_f), E_frente, alt_frente_gav), mat_ctx,
                papel=PapelChapa.FRENTE_GAVETA, color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                door_side="drawer", is_upper=False
            ))

            # Gaveta - Caixa interna
            larg_corredica = max(0.010, float(folga_corredica_mm) / 1000.0)
            larg_caixa_gav = max(0.08, largura_interna - larg_corredica)
            alt_caixa_gav = max(0.06, alt_frente_gav - 0.040)
            prof_gav = max(0.15, P - 0.060)

            mat_gav = material_gaveta or material
            mat_fg = material_fundo_gaveta or f"MDF Fundo {int(esp_fundo_gaveta_mm)}mm"

            gav_pieces = cls.build_caixa_gaveta(
                prefixo="Balcao Forno - Gaveta",
                x_caixa=ox + E + (larg_corredica / 2.0),
                y_caixa=oy + 0.010,
                z_caixa=z_fg + 0.015,
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
        else:
            # Sem gaveta: o forno apoia diretamente sobre a base inferior
            z_apoio = oz + R
            alt_gaveta_m = 0.0

        # 2. Frente Cega / Painel para Embutir o Forno
        # Em marcenaria padrão, o balcão de forno tem uma frente cega (chapa de MDF)
        # onde na montagem/obra é feito o recorte para embutir o forno.
        # Se a travessa frontal estiver em pé, deve obedecer à folga/rebaixo no topo (recuo_porta_topo_mm).
        recuo_topo = (recuo_porta_topo_mm / 1000.0) if travessa_frontal_em_pe else 0.0

        # Se tem gaveta, a frente cega inicia exatamente `folga_entre_frentes` acima do topo da frente da gaveta.
        # Se não tem gaveta, a frente cega começa na base inferior com folga `folga_f`.
        z_frente_cega = (topo_fg + folga_entre_frentes) if tem_gaveta else (oz + R + folga_f)
        topo_frente_cega = (oz + R + altura_caixa) - recuo_topo - folga_f
        alt_frente_cega = max(0.080, topo_frente_cega - z_frente_cega)

        groups.append(_chapa_frente(
            "Balcao Forno - Frente Cega",
            (ox + folga_f, oy - E_frente, z_frente_cega),
            (L - (2.0 * folga_f), E_frente, alt_frente_cega),
            mat_ctx,
            color=cor_frente,
        ))

        return groups

    @classmethod
    def build_canto_chanfrado(
        cls,
        largura_mm: float,
        altura_mm: float,
        prof_mm: float,
        prof_lateral_esq_mm: float = 550.0,
        prof_lateral_dir_mm: float = 550.0,
        num_portas: int = 1,
        esp_mm: float = 15.0,
        rodape_mm: float = 100.0,
        num_prateleiras: int = 1,
        material: str = "MDF Branco TX 15mm",
        material_frentes: str | None = None,
        esp_frentes_mm: float | None = None,
        tipo_fundo: str = "sobreposto",
        esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0,
        prof_rasgo_mm: float = 5.0,
        folga_fundo_mm: float = 2.0,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto",
        puxador_pos: str = "padrao",
        desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        larg_travessa_topo_mm: float = 70.0,
        esp_travessas_mm: float | None = None,
        material_travessas: str | None = None,
        material_fita_caixa: str | None = None,
        gerar_furacao: bool = True,
        dispositivo_fixacao: str = "minifix_cavilha",
        mat_ctx: ModuloMaterialContext | None = None,
        lado_abertura_porta: str = "esquerda",
    ) -> list[Group]:
        """Gera um Balcão de Canto Chanfrado (Oblíquo/Pentagonal).

        Estrutura:
        - 2 Traseiras em 90° encostando nas paredes (X=ox e Y=oy+Ly);
        - 2 Laterais retas com profundidades prof_lateral_esq_mm e prof_lateral_dir_mm;
        - Base inferior pentagonal com corte a 45° na frente;
        - Prateleira(s) intermediária(s) pentagonal(is);
        - 2 Montantes/batentes frontais chanfrados a 45° para fixação das dobradiças;
        - Travessas superiores de amarração para apoio de tampo/pedra;
        - 1 ou 2 Portas a 45° no vão chanfrado.
        """
        import math
        from ..builders.mesh_utils import create_polygon_board_group
        from ..builders.cabinet_transform import CabinetTransformMixin

        if mat_ctx is None:
            mat_ctx = ModuloMaterialContext(
                material_caixa=material,
                material_frentes=material_frentes or material,
            )

        ox, oy, oz = offset
        Lx = largura_mm / 1000.0
        Ly = prof_mm / 1000.0
        A = altura_mm / 1000.0
        E = esp_mm / 1000.0
        R = rodape_mm / 1000.0
        altura_caixa = A - R

        # Profundidade das laterais retas de encontro com os balcões vizinhos
        Pesq = min(Lx - 0.20, max(0.30, prof_lateral_esq_mm / 1000.0))
        Pdir = min(Ly - 0.20, max(0.30, prof_lateral_dir_mm / 1000.0))

        E_trav = (esp_travessas_mm / 1000.0) if esp_travessas_mm else E
        mat_trav = material_travessas or material
        E_frente = (esp_frentes_mm or esp_mm) / 1000.0
        mat_frente = material_frentes or material

        cor = cls.get_material_color(material)
        cor_frente = cls.get_material_color(mat_frente)
        cor_trav = cls.get_material_color(mat_trav)
        mat_fita_cx = material_fita_caixa or material
        cor_fita_cx = cls.get_material_color(mat_fita_cx) if material_fita_caixa else None

        folga_f = FrentesKitBuilder.resolve_folga_mm(mat_ctx=mat_ctx) / 1000.0

        groups: list[Group] = []

        # ── 1. TRASEIRAS EM 90° (Encosto na parede) ───────────────────────────
        # Traseira X: corre ao longo da parede traseira (Y = oy + Ly - E): de X = ox + E até ox + Lx
        groups.append(_chapa(
            "Canto Chanfrado - Traseira Parede X",
            (ox + E, oy + Ly - E, oz + R),
            (Lx - E, E, altura_caixa),
            material, fita_c1=True, color=cor,
            material_fita=mat_fita_cx, cor_fita=cor_fita_cx,
        ))
        # Traseira Y: corre ao longo da parede lateral esquerda (X = ox): de Y = oy até oy + Ly
        groups.append(_chapa(
            "Canto Chanfrado - Traseira Parede Y",
            (ox, oy, oz + R),
            (E, Ly, altura_caixa),
            material, fita_c1=True, color=cor,
            material_fita=mat_fita_cx, cor_fita=cor_fita_cx,
        ))

        # ── 2. LATERAIS RETAS DE ALINHAMENTO COM MÓDULOS VIZINHOS ────────────
        # Lateral Direita: em X = ox + Lx - E, de Y = oy + Ly - Pdir até oy + Ly - E
        prof_lat_dir = max(0.10, Pdir - E)
        groups.append(_chapa(
            "Canto Chanfrado - Lateral Direita",
            (ox + Lx - E, oy + Ly - Pdir, oz + R),
            (E, prof_lat_dir, altura_caixa),
            material, fita_c1=True, color=cor,
            material_fita=mat_fita_cx, cor_fita=cor_fita_cx,
        ))

        # Lateral Esquerda: em Y = oy, de X = ox + E até ox + Pesq
        larg_lat_esq = max(0.10, Pesq - E)
        groups.append(_chapa(
            "Canto Chanfrado - Lateral Esquerda",
            (ox + E, oy, oz + R),
            (larg_lat_esq, E, altura_caixa),
            material, fita_c1=True, color=cor,
            material_fita=mat_fita_cx, cor_fita=cor_fita_cx,
        ))

        # ── 3. BASE INFERIOR PENTAGONAL (Recorte frontal a 45°) ───────────────
        # Vértices da base pentagonal (anti-horário no plano XY):
        # V1: (ox + E, oy + E) -> quina interna perto da lateral esquerda
        # V2: (ox + Pesq, oy + E) -> início da frente chanfrada
        # V3: (ox + Lx - E, oy + Ly - Pdir) -> fim da frente chanfrada
        # V4: (ox + Lx - E, oy + Ly - E) -> quina direita da parede de fundo
        # V5: (ox + E, oy + Ly - E) -> quina de 90° de encontro das paredes
        poly_base = [
            (ox + E, oy + E),
            (ox + Pesq, oy + E),
            (ox + Lx - E, oy + Ly - Pdir),
            (ox + Lx - E, oy + Ly - E),
            (ox + E, oy + Ly - E),
        ]
        groups.append(create_polygon_board_group(
            name="Canto Chanfrado - Base Inferior",
            polygon_xy=poly_base,
            z0=oz + R,
            espessura=E,
            material=material,
            color=cor,
            material_fita=mat_fita_cx,
            cor_fita=cor_fita_cx,
        ))

        # ── 4. PRATELEIRAS PENTAGONAIS INTERMEDIÁRIAS ─────────────────────────
        num_prat = max(0, int(num_prateleiras))
        if num_prat > 0:
            recuo_prat = 0.020  # 20mm de folga da porta chanfrada
            poly_prat = [
                (ox + E, oy + E),
                (ox + Pesq - recuo_prat * 0.7, oy + E + recuo_prat * 0.7),
                (ox + Lx - E - recuo_prat * 0.7, oy + Ly - Pdir + recuo_prat * 0.7),
                (ox + Lx - E, oy + Ly - E),
                (ox + E, oy + Ly - E),
            ]
            espaco_util = altura_caixa - (2.0 * E)
            passo = espaco_util / (num_prat + 1)
            for i in range(1, num_prat + 1):
                zp = oz + R + E + (i * passo)
                groups.append(create_polygon_board_group(
                    name=f"Canto Chanfrado - Prateleira {i}" if num_prat > 1 else "Canto Chanfrado - Prateleira",
                    polygon_xy=poly_prat,
                    z0=zp,
                    espessura=E,
                    material=material,
                    color=cor,
                    material_fita=mat_fita_cx,
                    cor_fita=cor_fita_cx,
                ))

        # ── 5. TRAVESSAS SUPERIORES ESTRUTURAIS (Apoio de Tampo) ─────────────
        LT = max(0.050, larg_travessa_topo_mm / 1000.0)
        z_trav = oz + A - E_trav
        # Travessa Parede X (fundo):
        groups.append(_chapa(
            "Canto Chanfrado - Travessa Topo Parede X",
            (ox + E, oy + Ly - E - LT, z_trav),
            (Lx - 2 * E, LT, E_trav),
            mat_trav, fita_c1=True, color=cor_trav,
        ))
        # Travessa Parede Y (lateral esquerda):
        groups.append(_chapa(
            "Canto Chanfrado - Travessa Topo Parede Y",
            (ox + E, oy + E, z_trav),
            (LT, Ly - 2 * E - LT, E_trav),
            mat_trav, fita_c1=True, color=cor_trav,
        ))
        # Travessa frontal chanfrada de amarração:
        # Liga o topo das extremidades das laterais (ox+Pesq, oy) até (ox+Lx, oy+Ly-Pdir)
        dx_chanfro = (ox + Lx - E) - (ox + Pesq)
        dy_chanfro = (oy + Ly - Pdir) - (oy + E)
        comp_chanfro = math.hypot(dx_chanfro, dy_chanfro)
        ang_rad = math.atan2(dy_chanfro, dx_chanfro)
        ang_deg = math.degrees(ang_rad)

        g_trav_f = _chapa(
            "Canto Chanfrado - Travessa Topo Frontal",
            (0.0, 0.0, 0.0),
            (comp_chanfro, LT, E_trav),
            mat_trav, fita_c1=True, color=cor_trav,
        )
        # Rotaciona para o alinhamento chanfrado e posiciona no topo
        CabinetTransformMixin.rotate_module(g_trav_f, ang_deg, center=(0.0, 0.0, 0.0), update_param=False)
        for v in g_trav_f.mesh.vertices:
            v.position.setX(v.position.x() + ox + Pesq)
            v.position.setY(v.position.y() + oy + E)
            v.position.setZ(v.position.z() + z_trav)
        groups.append(g_trav_f)

        # ── 6. MONTANTES/BATENTES FRONTAIS CHANFRADOS (45°) ──────────────────
        # Largura de batente padrão para dobradiça caneco de 45°
        larg_montante = 0.070
        # Batente Esquerdo:
        g_mont_esq = _chapa(
            "Canto Chanfrado - Montante Batente Esq",
            (0.0, 0.0, 0.0),
            (larg_montante, E, altura_caixa),
            material, fita_c1=True, color=cor,
        )
        CabinetTransformMixin.rotate_module(g_mont_esq, ang_deg, center=(0.0, 0.0, 0.0), update_param=False)
        for v in g_mont_esq.mesh.vertices:
            v.position.setX(v.position.x() + ox + Pesq)
            v.position.setY(v.position.y() + oy + E)
            v.position.setZ(v.position.z() + oz + R)
        groups.append(g_mont_esq)

        # Batente Direito:
        g_mont_dir = _chapa(
            "Canto Chanfrado - Montante Batente Dir",
            (0.0, 0.0, 0.0),
            (larg_montante, E, altura_caixa),
            material, fita_c1=True, color=cor,
        )
        CabinetTransformMixin.rotate_module(g_mont_dir, ang_deg, center=(0.0, 0.0, 0.0), update_param=False)
        x_mont_dir_0 = (ox + Lx - E) - (larg_montante * math.cos(ang_rad))
        y_mont_dir_0 = (oy + Ly - Pdir) - (larg_montante * math.sin(ang_rad))
        for v in g_mont_dir.mesh.vertices:
            v.position.setX(v.position.x() + x_mont_dir_0)
            v.position.setY(v.position.y() + y_mont_dir_0)
            v.position.setZ(v.position.z() + oz + R)
        groups.append(g_mont_dir)

        # ── 7. PORTAS A 45° NO VÃO CHANFRADO (1 OU 2 PORTAS) ─────────────────
        alt_porta = max(0.05, altura_caixa - (2.0 * folga_f))
        n_portas = max(1, min(2, int(num_portas)))

        # Vão total de cobertura das portas ao longo da face chanfrada externa:
        # A face externa fica recuada de -E_frente normal à face chanfrada.
        # Vetor normal apontando para fora do balcão (em direção ao usuário):
        # Como o vetor tangencial aponta de Esq para Dir (+cos, +sin),
        # o normal exterior aponta para (+sin, -cos)
        nx = math.sin(ang_rad)
        ny = -math.cos(ang_rad)

        larg_vao_portas = comp_chanfro - (2.0 * folga_f)
        z_porta = oz + R + folga_f

        if n_portas == 1:
            larg_porta = max(0.10, larg_vao_portas)
            side_porta = "left" if not str(lado_abertura_porta).lower().startswith(("dir", "right")) else "right"
            g_p = _chapa_frente(
                "Canto Chanfrado - Porta",
                (0.0, 0.0, 0.0),
                (larg_porta, E_frente, alt_porta),
                mat_ctx,
                color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                door_side=side_porta, is_upper=False,
            )
            CabinetTransformMixin.rotate_module(g_p, ang_deg, center=(0.0, 0.0, 0.0), update_param=False)
            x_p0 = (ox + Pesq) + (folga_f * math.cos(ang_rad)) + (nx * E_frente)
            y_p0 = (oy + E) + (folga_f * math.sin(ang_rad)) + (ny * E_frente)
            for v in g_p.mesh.vertices:
                v.position.setX(v.position.x() + x_p0)
                v.position.setY(v.position.y() + y_p0)
                v.position.setZ(v.position.z() + z_porta)
            groups.append(g_p)

        else:
            # 2 Portas conjugadas dividindo o vão chanfrado
            folga_entre_portas = folga_f
            larg_porta = max(0.10, (larg_vao_portas - folga_entre_portas) / 2.0)

            # Porta 1 (Esquerda)
            g_p1 = _chapa_frente(
                "Canto Chanfrado - Porta Esq",
                (0.0, 0.0, 0.0),
                (larg_porta, E_frente, alt_porta),
                mat_ctx,
                color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                door_side="left", is_upper=False,
            )
            CabinetTransformMixin.rotate_module(g_p1, ang_deg, center=(0.0, 0.0, 0.0), update_param=False)
            x_p1_0 = (ox + Pesq) + (folga_f * math.cos(ang_rad)) + (nx * E_frente)
            y_p1_0 = (oy + E) + (folga_f * math.sin(ang_rad)) + (ny * E_frente)
            for v in g_p1.mesh.vertices:
                v.position.setX(v.position.x() + x_p1_0)
                v.position.setY(v.position.y() + y_p1_0)
                v.position.setZ(v.position.z() + z_porta)
            groups.append(g_p1)

            # Porta 2 (Direita)
            g_p2 = _chapa_frente(
                "Canto Chanfrado - Porta Dir",
                (0.0, 0.0, 0.0),
                (larg_porta, E_frente, alt_porta),
                mat_ctx,
                color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                door_side="right", is_upper=False,
            )
            CabinetTransformMixin.rotate_module(g_p2, ang_deg, center=(0.0, 0.0, 0.0), update_param=False)
            offset_p2 = folga_f + larg_porta + folga_entre_portas
            x_p2_0 = (ox + Pesq) + (offset_p2 * math.cos(ang_rad)) + (nx * E_frente)
            y_p2_0 = (oy + E) + (offset_p2 * math.sin(ang_rad)) + (ny * E_frente)
            for v in g_p2.mesh.vertices:
                v.position.setX(v.position.x() + x_p2_0)
                v.position.setY(v.position.y() + y_p2_0)
                v.position.setZ(v.position.z() + z_porta)
            groups.append(g_p2)

        return groups

    @classmethod
    def build_terminal_chanfrado(
        cls,
        largura_mm: float = 300.0,
        altura_mm: float = 720.0,
        prof_mm: float = 550.0,
        prof_frente_mm: float = 200.0,
        lado: str = "direita",  # "direita" ou "esquerda"
        esp_mm: float = 15.0,
        rodape_mm: float = 100.0,
        num_prateleiras: int = 2,
        material: str = "MDF Branco 15mm",
        frente_material: str | None = None,
        cor: tuple[float, float, float] | None = None,
        origin: tuple[float, float, float] = (0.0, 0.0, 0.0),
        **kwargs: Any,
    ) -> list[Group]:
        """Constrói terminal chanfrado/oblíquo aberto com suporte a lado 'esquerda' ou 'direita'.

        Geometria (plano XY, olhando de cima):
        - Fundo (traseira contra a parede Y): largura total L ao longo de X.
        - Se lado == 'direita':
            * Lateral esquerda reta de profundidade total P (encosta no módulo vizinho à esquerda).
            * Lateral frontal direita chanfrada ligando (X=Pesq/frente) até a traseira direita.
            * Ou seja, frente tem largura `prof_frente_mm` à esquerda e chanfra até o fundo à direita.
        - Se lado == 'esquerda':
            * Lateral direita reta de profundidade total P (encosta no módulo vizinho à direita).
            * Frente tem largura `prof_frente_mm` à direita e chanfra até o fundo à esquerda.
        """
        ox, oy, oz = origin
        L = largura_mm / 1000.0
        H = altura_mm / 1000.0
        P = prof_mm / 1000.0
        E = esp_mm / 1000.0
        R = rodape_mm / 1000.0
        Lfrente = min(L - E, max(0.05, prof_frente_mm / 1000.0))

        H_caixa = H - R
        z_base = oz + R
        z_topo = oz + H - E

        groups: list[Group] = []

        # Traseira completa contra a parede
        g_costa = _chapa(
            "Terminal Chanfrado - Costa Traseira",
            (ox, oy + P - E, z_base),
            (L, E, H_caixa),
            material, fita_c1=True, fita_c2=True, color=cor, papel=PapelChapa.FUNDO,
        )
        groups.append(g_costa)

        is_dir = (lado.lower() == "direita")

        if is_dir:
            # Lateral reta na esquerda (encosta no módulo vizinho)
            g_lat_reta = _chapa(
                "Terminal Chanfrado - Lateral Reta Esq",
                (ox, oy, z_base),
                (E, P - E, H_caixa),
                material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, papel=PapelChapa.LATERAL_ESQUERDA,
            )
            groups.append(g_lat_reta)

            # Polígono da Base e Prateleiras (Esq para Dir)
            # Vértices em sentido anti-horário:
            # (ox + E, oy) -> (ox + E + Lfrente, oy) -> (ox + L, oy + P - E) -> (ox + E, oy + P - E)
            poly_base = [
                (ox + E, oy),
                (ox + E + Lfrente, oy),
                (ox + L, oy + P - E),
                (ox + E, oy + P - E),
            ]
        else:
            # Lateral reta na direita (encosta no módulo vizinho)
            g_lat_reta = _chapa(
                "Terminal Chanfrado - Lateral Reta Dir",
                (ox + L - E, oy, z_base),
                (E, P - E, H_caixa),
                material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, papel=PapelChapa.LATERAL_DIREITA,
            )
            groups.append(g_lat_reta)

            # Polígono da Base e Prateleiras (Dir para Esq)
            # (ox, oy + P - E) -> (ox + L - E - Lfrente, oy) -> (ox + L - E, oy) -> (ox + L - E, oy + P - E)
            poly_base = [
                (ox, oy + P - E),
                (ox + L - E - Lfrente, oy),
                (ox + L - E, oy),
                (ox + L - E, oy + P - E),
            ]

        # Base inferior chanfrada
        g_base = create_polygon_board_group(
            name="Terminal Chanfrado - Base Inferior",
            polygon_xy=poly_base,
            z0=z_base,
            espessura=E,
            material=material,
            color=cor,
        )
        groups.append(g_base)

        # Topo chanfrado
        g_topo = create_polygon_board_group(
            name="Terminal Chanfrado - Topo",
            polygon_xy=poly_base,
            z0=z_topo,
            espessura=E,
            material=material,
            color=cor,
        )
        groups.append(g_topo)

        # Prateleiras intermediárias chanfradas
        if num_prateleiras > 0:
            espaco_util = H_caixa - (2.0 * E)
            passo = espaco_util / (num_prateleiras + 1)
            for i in range(1, num_prateleiras + 1):
                z_prat = z_base + E + (i * passo) - (E / 2.0)
                g_prat = create_polygon_board_group(
                    name=f"Terminal Chanfrado - Prateleira {i}",
                    polygon_xy=poly_base,
                    z0=z_prat,
                    espessura=E,
                    material=material,
                    color=cor,
                )
                groups.append(g_prat)

        # Rodapé (se houver)
        if R > 0.01:
            if is_dir:
                poly_rodape = [
                    (ox + E, oy + 0.05),
                    (ox + E + max(0.02, Lfrente - 0.03), oy + 0.05),
                    (ox + L - 0.03, oy + P - E - 0.03),
                    (ox + E, oy + P - E - 0.03),
                ]
            else:
                poly_rodape = [
                    (ox + 0.03, oy + P - E - 0.03),
                    (ox + L - E - max(0.02, Lfrente - 0.03), oy + 0.05),
                    (ox + L - E, oy + 0.05),
                    (ox + L - E, oy + P - E - 0.03),
                ]
            g_rod = create_polygon_board_group(
                name="Terminal Chanfrado - Rodapé Base",
                polygon_xy=poly_rodape,
                z0=oz,
                espessura=R,
                material=material,
                color=cor,
            )
            groups.append(g_rod)

        return groups

    @classmethod
    def build_canto_gaveteiro_l(
        cls,
        largura_mm: float = 1050.0,
        altura_mm: float = 820.0,
        prof_mm: float = 1050.0,
        prof_lateral_esq_mm: float = 600.0,
        prof_lateral_dir_mm: float = 600.0,
        num_gavetas: int = 4,
        esp_mm: float = 15.0,
        rodape_mm: float = 100.0,
        larg_travessa_frontal_mm: float = 70.0,
        larg_travessa_traseira_mm: float = 70.0,
        travessa_frontal_em_pe: bool = False,
        travessa_traseira_em_pe: bool = False,
        recuo_porta_topo_mm: float = 50.0,
        material: str = "MDF Branco 15mm",
        frente_material: str | None = None,
        material_frentes: str | None = None,
        cor: tuple[float, float, float] | None = None,
        origin: tuple[float, float, float] = (0.0, 0.0, 0.0),
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto",
        puxador_pos: str = "padrao",
        desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        mat_ctx: ModuloMaterialContext | None = None,
        **kwargs: Any,
    ) -> list[Group]:
        """Constroi o Modulo Gaveteiro de Canto Diagonal (Space Corner Chevron / Flecha).
        
        Encaixe ortogonal 100% perfeito no canto da parede:
        - Ocupa exatamente a bounding box de canto [ox..ox+Lx, oy..oy+Ly].
        - A quina traseira de 90 graus apoia em (ox, oy + Ly), no vertice da alvenaria.
        - As laterais retas de 45 graus guiam a extrusao/abertura diagonal das gavetas.
        - As frentes em V de 90 graus alinham perfeitamente com os balcoes retos vizinhos.
        - Pilastras frontais laterais com orelhas espacadoras para fixacao nos balcoes vizinhos.
        """
        ox, oy, oz = origin
        Lx = largura_mm / 1000.0
        Ly = prof_mm / 1000.0
        A = altura_mm / 1000.0
        E = esp_mm / 1000.0
        R = rodape_mm / 1000.0
        H_caixa = A - R

        from ..builders.cabinet_caixa import CaixaMixin
        from ..builders.cabinet_transform import _rotate_group_tree
        from PySide6.QtGui import QMatrix4x4

        P_asa_esq = min(prof_lateral_esq_mm / 1000.0, Lx - 0.15)
        P_asa_dir = min(prof_lateral_dir_mm / 1000.0, Ly - 0.15)

        mat_frente = material_frentes or frente_material or material
        cor_mat = cor or cls.get_material_color(material)
        cor_frente = cls.get_material_color(mat_frente)

        if mat_ctx is None:
            mat_ctx = ModuloMaterialContext(
                material_caixa=material,
                material_frentes=mat_frente,
            )

        groups: list[Group] = []

        # Pontos do poligono chevron integrado no canto da sala:
        # V1: frente da ala esquerda (onde encosta o balcao vizinho da esquerda)
        x1, y1 = ox + P_asa_esq, oy
        # V2: vertice interno de 90 graus do V frontal
        x2, y2 = ox + P_asa_esq, oy + Ly - P_asa_dir
        # V3: frente da ala direita (onde encosta o balcao vizinho da direita)
        x3, y3 = ox + Lx, oy + Ly - P_asa_dir
        # V4: lateral direita encontra a parede de fundo (Y = oy + Ly)
        x4, y4 = ox + Lx - P_asa_dir, oy + Ly
        # V5: vertice do canto da parede de alvenaria
        x5, y5 = ox, oy + Ly
        # V6: lateral esquerda encontra a parede lateral (X = ox)
        x6, y6 = ox, oy + P_asa_esq

        poly_chevron = [
            (x1, y1),
            (x2, y2),
            (x3, y3),
            (x4, y4),
            (x5, y5),
            (x6, y6),
        ]

        # 1. Base Inferior Embutida por Dentro (entre laterais e traseiras)
        # Reprodução fiel de gaveteiro.igz:
        # Apoiada nos limites internos das pilastras frontais e traseiras de alvenaria.
        x_tr_int = ox + E
        y_tr_int = oy + Ly - E
        x_dir_base = x3 - E
        x_dir_tras = ox + Lx - P_asa_dir - E

        poly_base_embutida = [
            (x1, y1 + E),
            (x1, y2),
            (x_dir_base, y2),
            (x_dir_tras, y_tr_int),
            (x_tr_int, y_tr_int),
            (x_tr_int, y1 + E + P_asa_esq - E * math.sqrt(2.0)),
        ]

        groups.append(create_polygon_board_group(
            name="Space Corner - Base Inferior em L",
            polygon_xy=poly_base_embutida,
            z0=oz + R,
            espessura=E,
            material=material,
            color=cor_mat,
        ))

        # 2. Laterais Retas Canônicas a 45 graus (reprodução fiel de gaveteiro.igz):
        # A quina interna da Lateral Esquerda morre com precisão milimétrica em (x1, y1 + E),
        # que é exatamente a quina traseira da Pilastra Batente Esq e o início da Travessa Frontal Y.
        alt_lat_gab = H_caixa
        comp_lat_esq_gab = max(0.10, P_asa_esq * math.sqrt(2.0) - E)
        g_lat_esq_gab = _chapa(
            "Space Corner - Lateral Esquerda",
            (-E, 0.0, 0.0),
            (E, comp_lat_esq_gab, alt_lat_gab),
            material, fita_c1=True, fita_c2=True, color=cor_mat, papel=PapelChapa.LATERAL_ESQUERDA
        )
        tx_e = ox
        ty_e = y1 + E + P_asa_esq - E * math.sqrt(2.0)
        m_leg = QMatrix4x4()
        m_leg.translate(tx_e, ty_e, oz + R)
        m_leg.rotate(-135.0, 0.0, 0.0, 1.0)
        _rotate_group_tree(g_lat_esq_gab, m_leg, set())
        groups.append(g_lat_esq_gab)

        # A quina interna da Lateral Direita morre com precisão milimétrica em (x3 - E, y2),
        # que é exatamente a quina traseira da Pilastra Batente Dir e o início da Travessa Frontal X.
        comp_lat_dir_gab = max(0.10, P_asa_dir * math.sqrt(2.0) - E)
        g_lat_dir_gab = _chapa(
            "Space Corner - Lateral Direita",
            (-E, 0.0, 0.0),
            (E, comp_lat_dir_gab, alt_lat_gab),
            material, fita_c1=True, fita_c2=True, color=cor_mat, papel=PapelChapa.LATERAL_DIREITA
        )
        tx_d = (x3 - E) - (P_asa_dir - E / math.sqrt(2.0))
        ty_d = (oy + Ly) - E / math.sqrt(2.0)
        m_ldg = QMatrix4x4()
        m_ldg.translate(tx_d, ty_d, oz + R)
        m_ldg.rotate(-135.0, 0.0, 0.0, 1.0)
        _rotate_group_tree(g_lat_dir_gab, m_ldg, set())
        groups.append(g_lat_dir_gab)

        # 3. Traseiras de encosto na parede de alvenaria (apoiadas sobre a base ou deitadas):
        groups.append(_chapa(
            "Space Corner - Traseira Parede Y",
            (ox, y6, oz + R + E),
            (E, y5 - y6, H_caixa - E),
            material, fita_c1=True, fita_c2=True, color=cor_mat, papel=PapelChapa.FUNDO
        ))
        groups.append(_chapa(
            "Space Corner - Traseira Parede X",
            (x5 + E, y5 - E, oz + R + E),
            (x4 - x5 - E, E, H_caixa - E),
            material, fita_c1=True, fita_c2=True, color=cor_mat, papel=PapelChapa.FUNDO
        ))

        # 4. Travessas Superiores Estruturais (Apoio de Bancada / Granito no padrão dos balcões):
        # Reprodução 100% fiel de gaveteiro.igz com suporte configurável para deitadas ou em pé:
        LTF = (larg_travessa_frontal_mm / 1000.0) if larg_travessa_frontal_mm > 0.02 else 0.070
        LTT = (larg_travessa_traseira_mm / 1000.0) if larg_travessa_traseira_mm > 0.02 else 0.070

        # Travessas Traseiras (Ala Y e Ala X):
        if travessa_traseira_em_pe:
            z_trav_t = oz + A - LTT
            # Ala Y (em pé vertical ao longo da parede X = ox + E):
            groups.append(_chapa(
                "Space Corner - Travessa Traseira Ala Y",
                (ox + E, y6, z_trav_t),
                (E, y5 - y6 - E, LTT),
                material, fita_c1=True, color=cor_mat, papel=PapelChapa.TRAVESSA
            ))
            # Ala X (em pé vertical ao longo da parede Y = y5 - 2*E):
            groups.append(_chapa(
                "Space Corner - Travessa Traseira Ala X",
                (ox + E, y5 - 2 * E, z_trav_t),
                (x4 - ox - E, E, LTT),
                material, fita_c1=True, color=cor_mat, papel=PapelChapa.TRAVESSA
            ))
        else:
            z_trav_t = oz + A - E
            # Ala Y (deitada horizontal ao longo da parede X = ox + E):
            groups.append(_chapa(
                "Space Corner - Travessa Traseira Ala Y",
                (ox + E, y6, z_trav_t),
                (LTT, y5 - y6 - E, E),
                material, fita_c1=True, color=cor_mat, papel=PapelChapa.TRAVESSA
            ))
            # Ala X (deitada horizontal ao longo da parede Y = oy + Ly):
            groups.append(_chapa(
                "Space Corner - Travessa Traseira Ala X",
                (ox + E, y5 - E - LTT, z_trav_t),
                (x4 - ox - E, LTT, E),
                material, fita_c1=True, color=cor_mat, papel=PapelChapa.TRAVESSA
            ))

        # Travessas Frontais (Ala X e Ala Y):
        c_trav_y_fundo = x4 + y5 - E
        if travessa_frontal_em_pe:
            z_trav_f = oz + A - LTF
            # Ala X (em pé vertical em Y = y2, espessura E em Y):
            poly_trav_frontal_x = [
                (x1, y2),
                (x3 - E, y2),
                (x3 - 2 * E, y2 + E),
                (x1, y2 + E),
            ]
            groups.append(create_polygon_board_group(
                name="Space Corner - Travessa Frontal Ala X",
                polygon_xy=poly_trav_frontal_x,
                z0=z_trav_f,
                espessura=LTF,
                material=material,
                color=cor_mat,
            ))
            # Ala Y (em pé vertical em X = x1, espessura E em X):
            poly_trav_frontal_y = [
                (x1, y1 + E),
                (x1, c_trav_y_fundo - x1),
                (x1 - E, c_trav_y_fundo - (x1 - E)),
                (x1 - E, y1 + 2 * E),
            ]
            groups.append(create_polygon_board_group(
                name="Space Corner - Travessa Frontal Ala Y",
                polygon_xy=poly_trav_frontal_y,
                z0=z_trav_f,
                espessura=LTF,
                material=material,
                color=cor_mat,
            ))
        else:
            z_trav_f = oz + A - E
            # Ala X (deitada horizontal no topo, largura LTF no plano XY):
            poly_trav_frontal_x = [
                (x1, y2),
                (x3 - E, y2),
                (x3 - E - LTF, y2 + LTF),
                (x1, y2 + LTF),
            ]
            groups.append(create_polygon_board_group(
                name="Space Corner - Travessa Frontal Ala X",
                polygon_xy=poly_trav_frontal_x,
                z0=z_trav_f,
                espessura=E,
                material=material,
                color=cor_mat,
            ))
            # Ala Y (deitada horizontal no topo, largura LTF no plano XY, viga contínua):
            poly_trav_frontal_y = [
                (x1, y1 + E),
                (x1, c_trav_y_fundo - x1),
                (x1 - LTF, c_trav_y_fundo - (x1 - LTF)),
                (x1 - LTF, y1 + E + LTF),
            ]
            groups.append(create_polygon_board_group(
                name="Space Corner - Travessa Frontal Ala Y",
                polygon_xy=poly_trav_frontal_y,
                z0=z_trav_f,
                espessura=E,
                material=material,
                color=cor_mat,
            ))

        # 4. Pilastras Frontais e Espaçadores Laterais (100% contidos na projeção):
        larg_pil = 0.050
        # Pilastra Esquerda: na linha frontal do balcao vizinho esquerdo
        groups.append(_chapa(
            "Space Corner - Pilastra Batente Esq",
            (x1 - larg_pil, y1, oz + R),
            (larg_pil, E, H_caixa),
            mat_frente, fita_c1=True, fita_l1=True, color=cor_frente, papel=PapelChapa.PECA_AVULSA
        ))
        groups.append(_chapa(
            "Space Corner - Orelha Espacadora Esq Sup",
            (x1 - larg_pil, y1 + E, oz + A - 0.08),
            (0.025, 0.030, 0.020),
            material, color=cor_mat, papel=PapelChapa.PECA_AVULSA
        ))
        groups.append(_chapa(
            "Space Corner - Orelha Espacadora Esq Inf",
            (x1 - larg_pil, y1 + E, oz + R + 0.06),
            (0.025, 0.030, 0.020),
            material, color=cor_mat, papel=PapelChapa.PECA_AVULSA
        ))

        # Pilastra Direita: na linha de encosto do balcao vizinho direito (Y >= y3)
        groups.append(_chapa(
            "Space Corner - Pilastra Batente Dir",
            (x3 - E, y3, oz + R),
            (E, larg_pil, H_caixa),
            mat_frente, fita_c1=True, fita_l1=True, color=cor_frente, papel=PapelChapa.PECA_AVULSA
        ))
        groups.append(_chapa(
            "Space Corner - Orelha Espacadora Dir Sup",
            (x3 - E - 0.030, y3 + (larg_pil - 0.025), oz + A - 0.08),
            (0.030, 0.025, 0.020),
            material, color=cor_mat, papel=PapelChapa.PECA_AVULSA
        ))
        groups.append(_chapa(
            "Space Corner - Orelha Espacadora Dir Inf",
            (x3 - E - 0.030, y3 + (larg_pil - 0.025), oz + R + 0.06),
            (0.030, 0.025, 0.020),
            material, color=cor_mat, papel=PapelChapa.PECA_AVULSA
        ))

        from ..builders.cabinet_caixa import CaixaMixin
        from ..builders.cabinet_transform import _rotate_group_tree
        from PySide6.QtGui import QMatrix4x4

        qtd = max(1, min(6, int(num_gavetas)))
        folga_f = 0.003
        recuo_topo = (recuo_porta_topo_mm / 1000.0) if travessa_frontal_em_pe else 0.0
        alt_disponivel = max(0.10, H_caixa - recuo_topo - E)
        alt_frente_cada = (alt_disponivel - (qtd + 1) * folga_f) / qtd
        cor_pux_rgb = (0.15, 0.15, 0.15) if puxador_cor in ("preto", "dark") else (0.85, 0.85, 0.85)

        slide_vec = QVector3D(1.0 / math.sqrt(2), -1.0 / math.sqrt(2), 0.0)
        slide_len = 0.45

        # Parâmetros geométricos da caixa interna das gavetas:
        # A face interna da lateral do gabinete fica recuada por E.
        # A folga da corrediça telescópica padrão de 13 mm afasta a gaveta da face interna.
        folga_lat_corr = 0.013  # 13 mm de cada lado para as corrediças telescópicas
        folga_total_xy = (E + folga_lat_corr) * math.sqrt(2.0)
        c_esq_gav = (ox + P_asa_esq + oy) + folga_total_xy
        c_dir_gav = (ox + Lx + oy + Ly - P_asa_dir) - folga_total_xy

        recuo_traseira_gav = 0.035
        E_gav = 0.015

        # As frentes ficam PARA FORA das travessas e da caixaria:
        # A face interna da frente esquerda encosta na face externa da carcaça em X = x1 (projeta para fora: X in [x1, x1 + E]).
        # A face interna da frente direita encosta na face externa da carcaça em Y = y2 (projeta para fora: Y in [y2 - E, y2]).
        # A caixa interna da gaveta bate perfeitamente atrás das frentes em (x1, y2).
        x_face_int_fe = x1
        y_face_int_fd = y2

        # Vértices do contorno externo da caixa interna da gaveta:
        # P1: Encontro da lateral esquerda da gaveta com a face interna da frente esquerda
        p1_g = (x_face_int_fe, c_esq_gav - x_face_int_fe)
        # P2: Vértice interno frontal de 90° (encostado perfeitamente atrás das duas frentes)
        p2_g = (x_face_int_fe, y_face_int_fd)
        # P3: Encontro da lateral direita da gaveta com a face interna da frente direita
        p3_g = (c_dir_gav - y_face_int_fd, y_face_int_fd)
        # P4: Traseira direita
        p4_g = (c_dir_gav - (y5 - recuo_traseira_gav), y5 - recuo_traseira_gav)
        # P5: Quina traseira de 90°
        p5_g = (ox + recuo_traseira_gav, y5 - recuo_traseira_gav)
        # P6: Traseira esquerda
        p6_g = (ox + recuo_traseira_gav, c_esq_gav - (ox + recuo_traseira_gav))

        poly_fundo_gav = [p1_g, p2_g, p3_g, p4_g, p5_g, p6_g]

        for i in range(qtd):
            z_gav = oz + R + E + folga_f + i * (alt_frente_cada + folga_f)
            alt_caixa_gav = max(0.06, alt_frente_cada - 0.035)
            idx_1 = i + 1

            # 1. Frente Esquerda Canônica (para fora da travessa/carcaça):
            # - Na quina de 90°: transpassa a espessura E da outra frente para corte a 45° (Y vai até y2 + E)
            # - Na extremidade frontal: obedece a folga técnica de marcenaria (Y começa em y1 + folga_f)
            # - A face interna apoia em X = x1 e a espessura E projeta para fora (X in [x1, x1 + E])
            larg_fe = (y2 + E) - (y1 + folga_f)
            g_fe = CaixaMixin.build_frente_gaveta(
                name=f"Space Corner - Gaveta {idx_1} Frente Esq",
                origin=(0.0, 0.0, z_gav),
                size=(larg_fe, E, alt_frente_cada),
                material=mat_frente,
                color=cor_frente,
                puxador_tipo=puxador_tipo,
                puxador_cor=puxador_cor,
                puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm,
                perfil_modelo=perfil_modelo,
                ctx=mat_ctx,
            )
            m_fe = QMatrix4x4()
            m_fe.translate(x1 + E, y1 + folga_f, 0.0)
            m_fe.rotate(90.0, 0.0, 0.0, 1.0)
            _rotate_group_tree(g_fe, m_fe, set())
            if getattr(g_fe, "ext", None) is None:
                g_fe.ext = {}
            g_fe.ext["slide_axis"] = slide_vec
            g_fe.ext["slide_distance"] = slide_len
            groups.append(g_fe)

            # 2. Frente Direita Canônica (para fora da travessa/carcaça):
            # - Na quina de 90°: transpassa a espessura E da outra frente para corte a 45° (X começa em x1 - E)
            # - Na extremidade lateral: obedece a folga técnica de marcenaria (X vai até x3 - folga_f)
            # - A face interna apoia em Y = y2 e a espessura E projeta para fora (Y in [y2 - E, y2])
            larg_fd = (x3 - folga_f) - (x1 - E)
            g_fd = CaixaMixin.build_frente_gaveta(
                name=f"Space Corner - Gaveta {idx_1} Frente Dir",
                origin=(x1 - E, y2 - E, z_gav),
                size=(larg_fd, E, alt_frente_cada),
                material=mat_frente,
                color=cor_frente,
                puxador_tipo=puxador_tipo,
                puxador_cor=puxador_cor,
                puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm,
                perfil_modelo=perfil_modelo,
                ctx=mat_ctx,
            )
            if getattr(g_fd, "ext", None) is None:
                g_fd.ext = {}
            g_fd.ext["slide_axis"] = slide_vec
            g_fd.ext["slide_distance"] = slide_len
            groups.append(g_fd)

            # 3. Lateral Esquerda Canônica (rotacionada a -135° no plano XY)
            # A face externa (voltada para a corrediça e lateral do gabinete) apoia em p6_g/p1_g.
            # A espessura E_gav (-E_gav) projeta para o interior da gaveta, mantendo os 13 mm livres.
            dx_e = p1_g[0] - p6_g[0]
            dy_e = p1_g[1] - p6_g[1]
            comp_lat_esq = math.hypot(dx_e, dy_e)
            g_lat_esq = _chapa(
                f"Space Corner - Gaveta {idx_1} Lat Esq",
                (-E_gav, 0.0, 0.0),
                (E_gav, comp_lat_esq, alt_caixa_gav),
                material, color=cor_mat, papel=PapelChapa.LATERAL_GAVETA, fita_c1=True
            )
            m_le = QMatrix4x4()
            m_le.translate(p6_g[0], p6_g[1], z_gav + 0.010)
            m_le.rotate(-135.0, 0.0, 0.0, 1.0)
            _rotate_group_tree(g_lat_esq, m_le, set())
            if getattr(g_lat_esq, "ext", None) is None:
                g_lat_esq.ext = {}
            g_lat_esq.ext["slide_axis"] = slide_vec
            g_lat_esq.ext["slide_distance"] = slide_len
            groups.append(g_lat_esq)

            # 4. Lateral Direita Canônica (rotacionada a -135° no plano XY)
            dx_d = p3_g[0] - p4_g[0]
            dy_d = p3_g[1] - p4_g[1]
            comp_lat_dir = math.hypot(dx_d, dy_d)
            g_lat_dir = _chapa(
                f"Space Corner - Gaveta {idx_1} Lat Dir",
                (0.0, 0.0, 0.0),
                (E_gav, comp_lat_dir, alt_caixa_gav),
                material, color=cor_mat, papel=PapelChapa.LATERAL_GAVETA, fita_c1=True
            )
            m_ld = QMatrix4x4()
            m_ld.translate(p4_g[0], p4_g[1], z_gav + 0.010)
            m_ld.rotate(-135.0, 0.0, 0.0, 1.0)
            _rotate_group_tree(g_lat_dir, m_ld, set())
            if getattr(g_lat_dir, "ext", None) is None:
                g_lat_dir.ext = {}
            g_lat_dir.ext["slide_axis"] = slide_vec
            g_lat_dir.ext["slide_distance"] = slide_len
            groups.append(g_lat_dir)

            # 5. Traseiras da Caixa da Gaveta (fechamento traseiro de 90° em MDF)
            g_tras_y = _chapa(
                f"Space Corner - Gaveta {idx_1} Traseira Parede Y",
                (p5_g[0], p6_g[1], z_gav + 0.010),
                (E_gav, p5_g[1] - p6_g[1], alt_caixa_gav),
                material, color=cor_mat, papel=PapelChapa.TRASEIRO_GAVETA
            )
            if getattr(g_tras_y, "ext", None) is None:
                g_tras_y.ext = {}
            g_tras_y.ext["slide_axis"] = slide_vec
            g_tras_y.ext["slide_distance"] = slide_len
            groups.append(g_tras_y)

            g_tras_x = _chapa(
                f"Space Corner - Gaveta {idx_1} Traseira Parede X",
                (p5_g[0] + E_gav, p5_g[1] - E_gav, z_gav + 0.010),
                (p4_g[0] - p5_g[0] - E_gav, E_gav, alt_caixa_gav),
                material, color=cor_mat, papel=PapelChapa.TRASEIRO_GAVETA
            )
            if getattr(g_tras_x, "ext", None) is None:
                g_tras_x.ext = {}
            g_tras_x.ext["slide_axis"] = slide_vec
            g_tras_x.ext["slide_distance"] = slide_len
            groups.append(g_tras_x)

            # 6. Fundo angular chevron da gaveta (base em MDF/HDF)
            g_fundo = create_polygon_board_group(
                name=f"Space Corner - Gaveta {idx_1} Fundo",
                polygon_xy=poly_fundo_gav,
                z0=z_gav + 0.010,
                espessura=0.006,
                material="HDF Eucatex 3mm",
                color=(0.90, 0.90, 0.90),
            )
            if getattr(g_fundo, "ext", None) is None:
                g_fundo.ext = {}
            g_fundo.ext["slide_axis"] = slide_vec
            g_fundo.ext["slide_distance"] = slide_len
            groups.append(g_fundo)

        # 6. Rodapé em Chevron
        if R > 0.01:
            poly_rodape = [
                (x1 + 0.04, y1 + 0.04),
                (x2 + 0.04, y2 + 0.04),
                (x3 - 0.04, y3 + 0.04),
                (x4 - 0.04, y4 - 0.04),
                (x5 + 0.04, y5 - 0.04),
                (x6 + 0.04, y6 - 0.04),
            ]
            groups.append(create_polygon_board_group(
                name="Space Corner - Rodapé Ala X",
                polygon_xy=poly_rodape,
                z0=oz,
                espessura=R,
                material=material,
                color=cor_mat,
            ))

        return groups


# Aliases
CornerCabinetBuilder = CantoEspecialBuilder

