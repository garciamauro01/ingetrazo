# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations
from typing import Any
from core.group import Group
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
    operacoes: list[dict[str, Any]] | None = None,
    **kwargs: Any,
) -> Group:
    """Cria uma peça de canto pela API canônica de chapa (material explícito)."""
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
    """Cria porta/frente canônica herdando material e fita de frentes do módulo."""
    spec = ChapaSpec.resolve(nome=name, papel=papel, ctx=ctx)
    return build_chapa(spec, origin, size, **kwargs)


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


# Aliases
CornerCabinetBuilder = CantoEspecialBuilder

