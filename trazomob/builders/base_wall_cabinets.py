# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations
import math
from typing import Any
from core.group import Group
from core.mesh import Mesh
from ..builders.mesh_utils import (
    create_board_group,
    create_polygon_board_group,
    create_prism_board_group,
    create_cylinder_group,
)
from ..builders.chapa_builder import build_chapa
from ..builders.chapa_spec import ChapaSpec, PapelChapa, ModuloMaterialContext
from ..builders.fronts import FrentesKitBuilder
from ..builders.parts import _chapa, _chapa_frente


class BalcaoAereoBuilder:
    """Construtor especializado para balcões inferiores padrão, gaveteiros, balcões mistos, pias, aéreos e nichos."""

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

    @staticmethod
    def build_prateleira(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_prateleira(*args, **kwargs)

    @staticmethod
    def build_divisoria(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_divisoria(*args, **kwargs)

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

    @staticmethod
    def build_travessa_peca(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_travessa_peca(*args, **kwargs)

    @classmethod
    def build_balcao(
        cls, largura_mm: float, altura_mm: float, prof_mm: float,
        esp_mm: float = 15.0, rodape_mm: float = 100.0, num_portas: int = 2,
        num_prateleiras: int = 1, num_divisoes: int | None = None, tem_fundo: bool = True,
        material: str = "MDF Branco TX 15mm", material_frentes: str | None = None,
        esp_frentes_mm: float | None = None,
        tipo_fundo: str = "rasgo", esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0, prof_rasgo_mm: float = 5.0,
        folga_fundo_mm: float = 2.0,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        puxador_tipo: str = "alca", puxador_cor: str = "preto", puxador_pos: str = "padrao", desconto_perfil_mm: float = 35.0,
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
        lado_abertura_porta: str = "esquerda",
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> list[Group]:
        from ..domain.module_geometry import MAX_DOORS, auto_divisoes_for_doors

        if mat_ctx is None:
            mat_ctx = ModuloMaterialContext(
                material_caixa=material,
                material_fita_caixa=material_fita_caixa,
                fita_caixa_modo=fita_caixa_modo,
                material_frentes=material_frentes or material,
            )

        # Limite documentado do balcão com portas: 1 a 4 portas.
        n_portas = int(num_portas)
        n_portas = max(1, min(MAX_DOORS, n_portas)) if n_portas > 0 else 0

        eff_esp_trav_mm = float(esp_travessas_mm) if (esp_travessas_mm is not None and float(esp_travessas_mm) > 0) else esp_mm
        eff_tipo_fundo = "sem_fundo" if not tem_fundo else tipo_fundo
        desc_fundo = cls._calc_desconto_traseiro_fundo(eff_tipo_fundo, esp_fundo_mm, recuo_fundo_mm, esp_travessa_traseira_mm=(eff_esp_trav_mm if travessa_traseira_em_pe else 0.0))

        P_val = prof_mm / 1000.0
        E_val = esp_mm / 1000.0
        R_val = rodape_mm / 1000.0
        altura_cx_val = (altura_mm / 1000.0) - R_val

        # Número de divisórias: mínimo estrutural (3+ portas) e máximo (n_portas - 1).
        min_divisoes = auto_divisoes_for_doors(n_portas) if n_portas >= 3 else 0
        if n_portas > 0:
            max_divisoes = max(0, n_portas - 1)
            solicitadas = int(num_divisoes) if num_divisoes is not None else min_divisoes
            eff_num_divisoes = max(min_divisoes, min(max(0, solicitadas), max_divisoes))
        else:
            eff_num_divisoes = max(0, int(num_divisoes or 0))
        n_bays = eff_num_divisoes + 1

        # Distribui as portas pelos vãos e define o lado da dobradiça de cada porta.
        if n_portas > 0:
            door_counts = [n_portas // n_bays] * n_bays
            for i in range(n_portas % n_bays):
                door_counts[i] += 1
        else:
            door_counts = [0] * n_bays

        lado = str(lado_abertura_porta or "esquerda").strip().lower()
        default_side = "right" if lado.startswith(("dir", "right")) else "left"

        bay_door_sides: list[list[str]] = []
        for b_idx, qtd in enumerate(door_counts):
            if qtd <= 0:
                bay_door_sides.append([])
            elif qtd == 1:
                bay_door_sides.append([default_side])
            else:
                bay_door_sides.append(
                    ["left" if i % 2 == 0 else "right" for i in range(qtd)])
        door_sides = [s for bay in bay_door_sides for s in bay]

        # Pré-calcula as posições Z das prateleiras para transportar os furos de cavilha às laterais da caixa
        recuo_frontal_prat = 0.025
        prof_prat = max(0.10, P_val - desc_fundo - recuo_frontal_prat)
        alturas_prat_mm = []
        if num_prateleiras > 0:
            espaco_util = altura_cx_val - 2 * E_val
            passo = espaco_util / (num_prateleiras + 1)
            for i in range(1, num_prateleiras + 1):
                # Posição Z relativa à base da lateral da caixa (altura_caixa): E + (i * passo)
                alturas_prat_mm.append((E_val + (i * passo)) * 1000.0)

        # Pré-calcula marcações de calço de dobradiça apenas nas laterais efetivamente usadas
        alturas_calcos_esq_mm = []
        alturas_calcos_dir_mm = []
        calcos_z: list[float] = []
        if n_portas > 0:
            from ..production.machining import make_hinge_cup_holes
            recuo_topo_val = (recuo_porta_topo_mm / 1000.0) if travessa_frontal_em_pe else 0.0
            alt_porta_val = max(0.05, altura_cx_val - recuo_topo_val - 0.006)
            alt_porta_mm = alt_porta_val * 1000.0
            ops_cup = make_hinge_cup_holes(alt_porta_mm)
            # z_porta inicia a 3mm do fundo da caixa: z_calco = 3.0 + caneco_y
            calcos_z = [3.0 + o.y for o in ops_cup if "caneco" in o.descricao.lower()]

            # A lateral esquerda só recebe calços se a primeira porta abre pela esquerda;
            # a lateral direita só recebe se a última porta abre pela direita.
            if door_sides and door_sides[0] == "left":
                alturas_calcos_esq_mm = list(calcos_z)
            if door_sides and door_sides[-1] == "right":
                alturas_calcos_dir_mm = list(calcos_z)

        # Largura dos vãos proporcional ao número de portas de cada vão e
        # posições X dos centros das divisórias (relativas à base, ox + E).
        largura_interna_pre = largura_mm / 1000.0 - 2 * E_val
        if n_portas > 0:
            largura_por_porta = max(0.05, (largura_interna_pre - eff_num_divisoes * E_val) / n_portas)
            largura_vaos_pre = [max(0.05, qtd * largura_por_porta) for qtd in door_counts]
        else:
            largura_vaos_pre = [
                max(0.05, (largura_interna_pre - eff_num_divisoes * E_val) / n_bays)
            ] * n_bays

        altura_caixa_pre = altura_mm / 1000.0 - R_val

        divisorias_x_mm: list[float] = []
        x_rel = 0.0
        for d_i in range(eff_num_divisoes):
            divisorias_x_mm.append(
                (x_rel + largura_vaos_pre[d_i] + E_val / 2.0) * 1000.0)
            x_rel += largura_vaos_pre[d_i] + E_val

        groups, info = cls.build_caixa_inferior(
            prefixo="Balcao",
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
            alturas_prateleiras_mm=alturas_prat_mm if num_prateleiras > 0 else None,
            prof_prateleira_mm=prof_prat * 1000.0,
            recuo_prateleira_frontal_mm=recuo_frontal_prat * 1000.0,
            alturas_calcos_esq_mm=alturas_calcos_esq_mm if alturas_calcos_esq_mm else None,
            alturas_calcos_dir_mm=alturas_calcos_dir_mm if alturas_calcos_dir_mm else None,
            divisorias_x_mm=divisorias_x_mm or None,
            divisorias_prof_mm=round((P_val - desc_fundo) * 1000.0, 2),
            divisorias_esp_mm=round(E_val * 1000.0, 2),
            tem_fundo=tem_fundo,
            tipo_fundo=tipo_fundo,
            esp_fundo_mm=esp_fundo_mm,
            recuo_fundo_mm=recuo_fundo_mm,
            prof_rasgo_mm=prof_rasgo_mm,
            folga_fundo_mm=folga_fundo_mm,
        )
        ox, oy, oz = info["ox"], info["oy"], info["oz"]
        L, A, P, E, R = info["L"], info["A"], info["P"], info["E"], info["R"]
        altura_caixa, largura_interna = info["altura_caixa"], info["largura_interna"]
        cor = info["cor"]
        mat_frente = material_frentes or material
        E_frente = (esp_frentes_mm or esp_mm) / 1000.0
        cor_frente = cls.get_material_color(mat_frente)

        # Divisórias verticais estruturais (mínimo automático para 3+ portas).
        # largura_vaos / prof_div / alt_div / prof_prat já foram pré-calculados
        # (largura_vaos_pre) antes do build_caixa_inferior para transportar as
        # divisórias_x_mm até a base.
        largura_vaos = largura_vaos_pre
        prof_div = max(0.15, P - desc_fundo)
        alt_div = (altura_caixa - E) if (travessa_frontal_em_pe and travessa_traseira_em_pe) else (altura_caixa - 2 * E)
        prof_prat = max(0.10, P - desc_fundo - recuo_frontal_prat)

        x_vaos: list[float] = []
        x_curr = ox + E
        for d_i in range(eff_num_divisoes):
            x_vaos.append(x_curr)
            x_div = x_curr + largura_vaos[d_i]

            div_ops: list[dict[str, Any]] = []
            if gerar_furacao:
                from ..production.machining import (
                    make_hinge_plate_holes,
                    make_shelf_side_holes,
                )

                # Os calços/pinos na divisória usam a origem Z da própria peça
                # (oz + R + E), um painel acima da origem das laterais.
                desloc_z_div_mm = E * 1000.0
                calcos_z_div = [z - desloc_z_div_mm for z in calcos_z]

                # Face esquerda da divisória = limite direito do vão d_i.
                if bay_door_sides[d_i] and bay_door_sides[d_i][-1] == "right":
                    div_ops.extend(o.to_dict() for o in make_hinge_plate_holes(
                        posicoes_y_mm=calcos_z_div,
                        recuo_borda_frontal_mm=37.0,
                        face="esquerda",
                        tipo_fixacao="parafuso",
                    ))
                # Face direita da divisória = limite esquerdo do vão d_i + 1.
                if bay_door_sides[d_i + 1] and bay_door_sides[d_i + 1][0] == "left":
                    div_ops.extend(o.to_dict() for o in make_hinge_plate_holes(
                        posicoes_y_mm=calcos_z_div,
                        recuo_borda_frontal_mm=37.0,
                        face="direita",
                        tipo_fixacao="parafuso",
                    ))

                # Pinos das prateleiras nas duas faces da divisória.
                if num_prateleiras > 0:
                    for alt_p_z in alturas_prat_mm:
                        for face_div in ("esquerda", "direita"):
                            div_ops.extend(o.to_dict() for o in make_shelf_side_holes(
                                pos_z_na_lateral_mm=alt_p_z - desloc_z_div_mm,
                                prof_prateleira_mm=prof_prat * 1000.0,
                                recuo_frontal_mm=recuo_frontal_prat * 1000.0,
                                afastamento_mm=50.0,
                                esp_prateleira_mm=esp_mm,
                                face=face_div,
                            ))

            div_name = (
                "Balcao - Divisoria Central" if eff_num_divisoes == 1
                else f"Balcao - Divisoria {d_i + 1}"
            )
            groups.append(cls.build_divisoria(
                name=div_name,
                origin=(x_div, oy, oz + R + E),
                size=(E, prof_div, alt_div),
                material=material, fita_c1=True, color=cor,
                operacoes=div_ops or None,
                cavilha_topo_inferior=gerar_furacao,
                ctx=mat_ctx,
            ))
            x_curr = x_div + E
        x_vaos.append(x_curr)

        # Prateleiras internas por vão
        if num_prateleiras > 0:
            espaco_util = altura_caixa - 2 * E
            passo = espaco_util / (num_prateleiras + 1)
            for v_idx, (xv, lv) in enumerate(zip(x_vaos, largura_vaos)):
                nome_vao = f"Vao {v_idx + 1}" if eff_num_divisoes > 0 else "Vao"
                for i in range(1, num_prateleiras + 1):
                    z_prat = oz + R + E + (i * passo)
                    prat_name = (
                        f"Balcao - {nome_vao} Prateleira {i}"
                        if eff_num_divisoes > 0 else f"Balcao - Prateleira {i}"
                    )
                    groups.append(cls.build_prateleira(
                        name=prat_name,
                        origin=(xv, oy + recuo_frontal_prat, z_prat),
                        size=(max(0.05, lv - 0.002), prof_prat, E),
                        material=material, fita_c1=True, color=cor,
                        gerar_furacao=gerar_furacao,
                        ctx=mat_ctx,
                    ))

        # O fundo já é gerado de forma integrada por build_caixa_modular.

        if n_portas > 0:
            recuo_topo = (recuo_porta_topo_mm / 1000.0) if travessa_frontal_em_pe else 0.0
            from ..builders.frentes import FrentesKitBuilder
            groups.extend(FrentesKitBuilder.build_kit_portas_giro(
                largura_mm=L * 1000.0,
                altura_mm=altura_caixa * 1000.0,
                num_portas=n_portas,
                offset=(ox, oy, oz + R),
                esp_frente_mm=E_frente * 1000.0,
                material=mat_frente,
                color=cor_frente,
                door_sides=door_sides,
                prefixo="Balcao",
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

    @classmethod
    def build_balcao_duplo(
        cls, largura_mm: float, altura_mm: float, prof_mm: float,
        esp_mm: float = 15.0, rodape_mm: float = 100.0,
        num_portas: int = 2, num_portas_verso: int = 2,
        num_prateleiras: int = 1,
        material: str = "MDF Branco TX 15mm", material_frentes: str | None = None,
        esp_frentes_mm: float | None = None,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        puxador_tipo: str = "alca", puxador_cor: str = "preto", puxador_pos: str = "padrao",
        desconto_perfil_mm: float = 35.0, perfil_modelo: str = "gola",
        larg_travessa_frontal_mm: float = 70.0, larg_travessa_traseira_mm: float = 70.0,
        travessa_frontal_em_pe: bool = False, travessa_traseira_em_pe: bool = False,
        recuo_porta_topo_mm: float = 50.0,
        material_travessas: str | None = None, esp_travessas_mm: float | None = None,
        fita_travessas_modo: str = "frontal_1L", fita_travessas_faces: dict[str, bool] | None = None,
        fita_caixa_modo: str = "frontal_1L",
        material_fita_caixa: str | None = None, material_fita_travessas: str | None = None,
        gerar_furacao: bool = True, dispositivo_fixacao: str = "minifix_cavilha",
        lado_abertura_porta: str = "esquerda",
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> list[Group]:
        """Balcão de ilha bilateral com portas na frente e no fundo (1 a 4 portas por lado).

        Estrutura:
        - 2 Laterais contínuas (profundidade total P).
        - 1 Base inferior contínua.
        - 1 Divisória longitudinal central em Y = P/2 (separa lado frente e lado fundo).
        - Divisórias verticais transversais proporcionais ao número de portas de cada lado.
        - Prateleiras frontais e traseiras independentes.
        - Travessas superiores frontais e traseiras.
        - Rodapé frontal e traseiro.
        - Portas frontais (em Y=0 abrindo para frente) e traseiras (em Y=P abrindo para trás).
        """
        from ..domain.module_geometry import MAX_DOORS, auto_divisoes_for_doors

        if mat_ctx is None:
            mat_ctx = ModuloMaterialContext(
                material_caixa=material,
                material_fita_caixa=material_fita_caixa,
                fita_caixa_modo=fita_caixa_modo,
                material_frentes=material_frentes or material,
            )

        n_p_front = max(1, min(MAX_DOORS, int(num_portas)))
        n_p_rear = max(1, min(MAX_DOORS, int(num_portas_verso or num_portas)))

        L = largura_mm / 1000.0
        A = altura_mm / 1000.0
        P = prof_mm / 1000.0
        E = esp_mm / 1000.0
        R = rodape_mm / 1000.0
        altura_caixa = A - R
        largura_interna = max(0.10, L - 2 * E)

        ox, oy, oz = offset
        cor = cls.get_material_color(material)
        mat_frente = material_frentes or material
        E_frente = (esp_frentes_mm or esp_mm) / 1000.0
        cor_frente = cls.get_material_color(mat_frente)

        groups: list[Group] = []

        # 1. Laterais contínuas (Esquerda e Direita)
        groups.append(cls.build_lateral_esquerda(
            name="Balcao Ilha - Lateral Esquerda",
            origin=(ox, oy, oz + R),
            size=(E, P, altura_caixa),
            material=material, fita_c1=True, fita_c2=True, color=cor,
            ctx=mat_ctx,
        ))
        groups.append(cls.build_lateral_direita(
            name="Balcao Ilha - Lateral Direita",
            origin=(ox + L - E, oy, oz + R),
            size=(E, P, altura_caixa),
            material=material, fita_c1=True, fita_c2=True, color=cor,
            ctx=mat_ctx,
        ))

        # 2. Base Inferior contínua
        groups.append(cls.build_base_inferior(
            name="Balcao Ilha - Base Inferior",
            origin=(ox + E, oy, oz + R),
            size=(largura_interna, P, E),
            material=material, fita_c1=True, fita_c2=True, color=cor,
            ctx=mat_ctx,
        ))

        # 3. Rodapé frontal e traseiro
        if R > 0.02:
            recuo_rod = 0.030
            larg_rod = max(0.05, largura_interna)
            # Frontal
            groups.append(cls.build_travessa_peca(
                name="Balcao Ilha - Rodape Frontal",
                origin=(ox + E, oy + recuo_rod, oz),
                size=(larg_rod, E, R),
                material=material, fita_c1=True, color=cor,
                ctx=mat_ctx,
            ))
            # Traseiro
            groups.append(cls.build_travessa_peca(
                name="Balcao Ilha - Rodape Traseiro",
                origin=(ox + E, oy + P - recuo_rod - E, oz),
                size=(larg_rod, E, R),
                material=material, fita_c1=True, color=cor,
                ctx=mat_ctx,
            ))

        # 4. Travessas superiores de amarração (Frontal e Traseira)
        larg_trav_f = (larg_travessa_frontal_mm or 70.0) / 1000.0
        larg_trav_r = (larg_travessa_traseira_mm or 70.0) / 1000.0
        eff_esp_trav = (esp_travessas_mm or esp_mm) / 1000.0
        mat_trav = material_travessas or material

        # Travessa frontal
        if travessa_frontal_em_pe:
            groups.append(cls.build_travessa_peca(
                name="Balcao Ilha - Travessa Superior Frontal",
                origin=(ox + E, oy, oz + R + altura_caixa - larg_trav_f),
                size=(largura_interna, eff_esp_trav, larg_trav_f),
                material=mat_trav, fita_c1=True, color=cor,
                ctx=mat_ctx,
            ))
        else:
            groups.append(cls.build_travessa_peca(
                name="Balcao Ilha - Travessa Superior Frontal",
                origin=(ox + E, oy, oz + R + altura_caixa - eff_esp_trav),
                size=(largura_interna, larg_trav_f, eff_esp_trav),
                material=mat_trav, fita_c1=True, color=cor,
                ctx=mat_ctx,
            ))

        # Travessa traseira
        if travessa_traseira_em_pe:
            groups.append(cls.build_travessa_peca(
                name="Balcao Ilha - Travessa Superior Traseira",
                origin=(ox + E, oy + P - eff_esp_trav, oz + R + altura_caixa - larg_trav_r),
                size=(largura_interna, eff_esp_trav, larg_trav_r),
                material=mat_trav, fita_c1=True, color=cor,
                ctx=mat_ctx,
            ))
        else:
            groups.append(cls.build_travessa_peca(
                name="Balcao Ilha - Travessa Superior Traseira",
                origin=(ox + E, oy + P - larg_trav_r, oz + R + altura_caixa - eff_esp_trav),
                size=(largura_interna, larg_trav_r, eff_esp_trav),
                material=mat_trav, fita_c1=True, color=cor,
                ctx=mat_ctx,
            ))

        # 5. Divisória longitudinal central (separa compartimento frontal e traseiro)
        y_div_long = oy + (P - E) / 2.0
        alt_div_long = altura_caixa - 2 * E
        groups.append(cls.build_travessa_peca(
            name="Balcao Ilha - Divisoria Longitudinal Central",
            origin=(ox + E, y_div_long, oz + R + E),
            size=(largura_interna, E, alt_div_long),
            material=material, fita_c1=True, color=cor,
            ctx=mat_ctx,
        ))

        # Profundidade útil de cada lado
        prof_lado = max(0.15, (P - E) / 2.0)
        recuo_frontal_prat = 0.025
        prof_prat = max(0.10, prof_lado - recuo_frontal_prat)

        # 6. Estrutura interna e prateleiras para o LADO FRONTAL (Y de oy a y_div_long)
        n_div_f = auto_divisoes_for_doors(n_p_front) if n_p_front >= 3 else 0
        n_bays_f = n_div_f + 1
        larg_por_porta_f = max(0.05, (largura_interna - n_div_f * E) / n_p_front)
        door_counts_f = [n_p_front // n_bays_f] * n_bays_f
        for i in range(n_p_front % n_bays_f):
            door_counts_f[i] += 1
        larg_vaos_f = [max(0.05, qtd * larg_por_porta_f) for qtd in door_counts_f]

        x_curr_f = ox + E
        x_vaos_f: list[float] = []
        for d_i in range(n_div_f):
            x_vaos_f.append(x_curr_f)
            x_div = x_curr_f + larg_vaos_f[d_i]
            groups.append(cls.build_divisoria(
                name=f"Balcao Ilha - Divisoria Frontal {d_i + 1}",
                origin=(x_div, oy, oz + R + E),
                size=(E, prof_lado, alt_div_long),
                material=material, fita_c1=True, color=cor,
                ctx=mat_ctx,
            ))
            x_curr_f = x_div + E
        x_vaos_f.append(x_curr_f)

        if num_prateleiras > 0:
            passo = alt_div_long / (num_prateleiras + 1)
            for v_idx, (xv, lv) in enumerate(zip(x_vaos_f, larg_vaos_f)):
                for i in range(1, num_prateleiras + 1):
                    z_prat = oz + R + E + (i * passo)
                    groups.append(cls.build_prateleira(
                        name=f"Balcao Ilha - Prateleira Frontal Vao {v_idx + 1} - Nivel {i}",
                        origin=(xv, oy + recuo_frontal_prat, z_prat),
                        size=(max(0.05, lv - 0.002), prof_prat, E),
                        material=material, fita_c1=True, color=cor,
                        ctx=mat_ctx,
                    ))

        # 7. Estrutura interna e prateleiras para o LADO TRASEIRO (Y de y_div_long + E a oy + P)
        y_rear_start = y_div_long + E
        n_div_r = auto_divisoes_for_doors(n_p_rear) if n_p_rear >= 3 else 0
        n_bays_r = n_div_r + 1
        larg_por_porta_r = max(0.05, (largura_interna - n_div_r * E) / n_p_rear)
        door_counts_r = [n_p_rear // n_bays_r] * n_bays_r
        for i in range(n_p_rear % n_bays_r):
            door_counts_r[i] += 1
        larg_vaos_r = [max(0.05, qtd * larg_por_porta_r) for qtd in door_counts_r]

        x_curr_r = ox + E
        x_vaos_r: list[float] = []
        for d_i in range(n_div_r):
            x_vaos_r.append(x_curr_r)
            x_div = x_curr_r + larg_vaos_r[d_i]
            groups.append(cls.build_divisoria(
                name=f"Balcao Ilha - Divisoria Traseira {d_i + 1}",
                origin=(x_div, y_rear_start, oz + R + E),
                size=(E, prof_lado, alt_div_long),
                material=material, fita_c1=True, color=cor,
                ctx=mat_ctx,
            ))
            x_curr_r = x_div + E
        x_vaos_r.append(x_curr_r)

        if num_prateleiras > 0:
            passo = alt_div_long / (num_prateleiras + 1)
            for v_idx, (xv, lv) in enumerate(zip(x_vaos_r, larg_vaos_r)):
                for i in range(1, num_prateleiras + 1):
                    z_prat = oz + R + E + (i * passo)
                    groups.append(cls.build_prateleira(
                        name=f"Balcao Ilha - Prateleira Traseira Vao {v_idx + 1} - Nivel {i}",
                        origin=(xv, y_rear_start, z_prat),
                        size=(max(0.05, lv - 0.002), prof_prat, E),
                        material=material, fita_c1=True, color=cor,
                        ctx=mat_ctx,
                    ))

        # 8. Kit Portas Frontais (em Y = oy)
        lado = str(lado_abertura_porta or "esquerda").strip().lower()
        default_side = "right" if lado.startswith(("dir", "right")) else "left"
        bay_door_sides_f: list[list[str]] = []
        for qtd in door_counts_f:
            if qtd <= 0:
                bay_door_sides_f.append([])
            elif qtd == 1:
                bay_door_sides_f.append([default_side])
            else:
                bay_door_sides_f.append(["left" if i % 2 == 0 else "right" for i in range(qtd)])
        door_sides_f = [s for bay in bay_door_sides_f for s in bay]

        recuo_topo = (recuo_porta_topo_mm / 1000.0) if travessa_frontal_em_pe else 0.0
        groups.extend(FrentesKitBuilder.build_kit_portas_giro(
            largura_mm=largura_mm,
            altura_mm=altura_caixa * 1000.0,
            num_portas=n_p_front,
            offset=(ox, oy, oz + R),
            esp_frente_mm=E_frente * 1000.0,
            material=mat_frente,
            color=cor_frente,
            door_sides=door_sides_f,
            prefixo="Balcao Ilha - Frente",
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

        # 9. Kit Portas Traseiras (em Y = oy + P)
        bay_door_sides_r: list[list[str]] = []
        for qtd in door_counts_r:
            if qtd <= 0:
                bay_door_sides_r.append([])
            elif qtd == 1:
                bay_door_sides_r.append([default_side])
            else:
                bay_door_sides_r.append(["left" if i % 2 == 0 else "right" for i in range(qtd)])
        door_sides_r = [s for bay in bay_door_sides_r for s in bay]

        folga_m = FrentesKitBuilder.resolve_folga_mm(None, mat_ctx) / 1000.0
        alt_porta_r = max(0.05, altura_caixa - recuo_topo - (2.0 * folga_m))
        larg_disp_r = L - (2.0 * folga_m) - (n_p_rear - 1) * folga_m
        larg_porta_r = max(0.10, larg_disp_r / n_p_rear)

        x_atual_r = ox + folga_m
        z_atual_r = oz + R + folga_m
        y_rear_door = oy + P

        from ..builders.cabinet_caixa import CaixaMixin
        from ..production.machining import make_hinge_cup_holes
        for i in range(n_p_rear):
            side = door_sides_r[i] if i < len(door_sides_r) else "left"
            lado_txt = "Dir" if side == "right" else "Esq"
            nome_p_r = f"Balcao Ilha - Verso Porta {i + 1} ({lado_txt})" if n_p_rear > 1 else f"Balcao Ilha - Verso Porta Unica ({lado_txt})"

            # Para porta traseira (posicionada em Y=oy+P), a face voltada para o interior do móvel
            # é a face FRONTAL (-Y da chapa). Portanto os canecos de dobradiça usam face="frontal".
            ops_porta_verso = None
            if gerar_furacao:
                lado_dob = "esquerda" if side == "left" else "direita"
                ops_porta_verso = [
                    o.to_dict() for o in make_hinge_cup_holes(
                        altura_porta_mm=alt_porta_r * 1000.0,
                        lado_dobradica=lado_dob,
                        largura_porta_mm=larg_porta_r * 1000.0,
                        face="frontal",
                    )
                ]

            builder_porta = CaixaMixin.build_porta_esquerda if side == "left" else CaixaMixin.build_porta_direita
            door_piece = builder_porta(
                name=nome_p_r,
                origin=(x_atual_r, y_rear_door, z_atual_r),
                size=(larg_porta_r, E_frente, alt_porta_r),
                material=mat_frente,
                color=cor_frente,
                puxador_tipo=puxador_tipo,
                puxador_cor=puxador_cor,
                puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm,
                perfil_modelo=perfil_modelo,
                door_side=side,
                is_upper=False,
                gerar_furacao=gerar_furacao,
                operacoes=ops_porta_verso,
                ctx=mat_ctx,
            )
            # Marca a porta como verso para a cinemática de abertura interativa e posicionamento de ferragens
            if getattr(door_piece, "ext", None) is None:
                door_piece.ext = {}
            door_piece.ext["is_rear_door"] = True
            door_piece.ext["door_side"] = side
            groups.append(door_piece)
            x_atual_r += larg_porta_r + folga_m

        return groups

    @classmethod
    def build_gaveteiro(
        cls, largura_mm: float, altura_mm: float, prof_mm: float,
        num_gavetas: int = 4, esp_mm: float = 15.0, rodape_mm: float = 100.0,
        material: str = "MDF Branco TX 15mm", material_frentes: str | None = None,
        esp_frentes_mm: float | None = None,
        tipo_fundo: str = "rasgo", esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0, prof_rasgo_mm: float = 5.0,
        folga_fundo_mm: float = 2.0,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        puxador_tipo: str = "alca", puxador_cor: str = "preto", puxador_pos: str = "padrao", desconto_perfil_mm: float = 35.0,
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
        tipo_fundo_gaveta: str = "rasgo",
        folga_corredica_mm: float = 26.0,
        material_gaveta: str | None = None,
        esp_gaveta_mm: float = 15.0,
        material_fita_gaveta: str | None = None,
        material_fundo_gaveta: str | None = None,
        esp_fundo_gaveta_mm: float = 6.0,
        gerar_furacao: bool = True,
        dispositivo_fixacao: str = "minifix_cavilha",
        lado_abertura_porta: str | None = None,
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> list[Group]:
        groups, info = cls.build_caixa_inferior(
            prefixo="Gaveteiro",
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
            ctx=mat_ctx,
        )
        ox, oy, oz = info["ox"], info["oy"], info["oz"]
        L, A, P, E, R = info["L"], info["A"], info["P"], info["E"], info["R"]
        altura_caixa, largura_interna = info["altura_caixa"], info["largura_interna"]
        cor = info["cor"]
        mat_frente = material_frentes or material
        E_frente = (esp_frentes_mm or esp_mm) / 1000.0
        cor_frente = cls.get_material_color(mat_frente)

        fundo_grp = cls.build_fundo_board(
            prefixo="Gaveteiro",
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

        desc_fundo = cls._calc_desconto_traseiro_fundo(tipo_fundo, esp_fundo_mm, recuo_fundo_mm)
        num_gav = max(1, num_gavetas)
        recuo_topo = (recuo_porta_topo_mm / 1000.0) if travessa_frontal_em_pe else 0.0
        alt_disponivel_frentes = max(0.10, altura_caixa - recuo_topo)
        folga_f = FrentesKitBuilder.resolve_folga_mm(mat_ctx=mat_ctx) / 1000.0
        alt_frente = (alt_disponivel_frentes - (num_gav + 1) * folga_f) / num_gav
        larg_frente = L - (2.0 * folga_f)
        prof_gaveta = max(0.15, min(P - 0.050, P - desc_fundo - 0.015))

        larg_corredica = max(0.010, float(folga_corredica_mm) / 1000.0)
        larg_caixa_gav = max(0.08, largura_interna - larg_corredica)
        alt_caixa_gav = max(0.06, alt_frente - 0.040)

        # Materiais da gaveta
        mat_gav = material_gaveta or material
        mat_fg = material_fundo_gaveta or f"MDF Fundo {int(esp_fundo_gaveta_mm)}mm"

        # Gaveteiro: Frentes externas e Caixas de gaveta internas via CanonicalDrawerBuilder
        from trazomob.builders.drawers import CanonicalDrawerBuilder
        gav_groups = CanonicalDrawerBuilder.build_stack_gaveteiro(
            prefixo="Gaveteiro",
            num_gavetas=num_gav,
            x_vao=ox + E,
            y_vao=oy,
            z_vao=oz + R,
            larg_vao=largura_interna,
            prof_vao=prof_gaveta,
            alt_vao=alt_disponivel_frentes,
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

    @classmethod
    def build_balcao_misto(
        cls, largura_mm: float, altura_mm: float, prof_mm: float,
        num_gavetas: int = 4, largura_gaveteiro_mm: float = 450.0,
        lado_gaveteiro: str = "esquerda",
        num_portas: int = 2, num_prateleiras: int = 1,
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
        tipo_fundo_gaveta: str = "rasgo",
        folga_corredica_mm: float = 26.0,
        material_gaveta: str | None = None,
        esp_gaveta_mm: float = 15.0,
        material_fita_gaveta: str | None = None,
        material_fundo_gaveta: str | None = None,
        esp_fundo_gaveta_mm: float = 6.0,
        gerar_furacao: bool = True,
        dispositivo_fixacao: str = "minifix_cavilha",
        lado_abertura_porta: str | None = None,
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> list[Group]:
        """Gera Balcão Misto (Gaveteiro 4 gavetas à esquerda + 2 portas à direita com divisória)."""

        # Pré-calcula medidas comuns antes de montar a caixa (necessário para
        # transportar as cavilhas das divisórias para a base).
        ox, oy, oz = offset
        E_val = esp_mm / 1000.0
        R_val = rodape_mm / 1000.0
        P_val = prof_mm / 1000.0
        L_val = largura_mm / 1000.0
        A_val = altura_mm / 1000.0
        altura_caixa_pre = A_val - R_val
        largura_interna_pre = L_val - 2 * E_val
        L_gav = min(max(0.30, largura_gaveteiro_mm / 1000.0), largura_interna_pre - 0.40)
        L_portas = max(0.20, largura_interna_pre - L_gav - E_val)
        eff_tipo_fundo = tipo_fundo
        desc_fundo = cls._calc_desconto_traseiro_fundo(tipo_fundo, esp_fundo_mm, recuo_fundo_mm)
        prof_divisoria = max(0.15, P_val - desc_fundo)
        if (not travessa_frontal_em_pe) or (not travessa_traseira_em_pe):
            alt_divisoria = altura_caixa_pre - 2 * E_val
        else:
            alt_divisoria = altura_caixa_pre - E_val

        gav_direita = str(lado_gaveteiro or "esquerda").strip().lower().startswith("dir")
        num_p = max(1, min(3, num_portas))

        # Posições X dos centros das divisórias (relativas à base, ox + E).
        folga_f = FrentesKitBuilder.resolve_folga_mm(mat_ctx=mat_ctx) / 1000.0
        divisorias_x_mm: list[float] = []
        if gav_direita:
            x_div = ox + E_val + L_portas
            x_portas_interno = ox + E_val
            x_gav_interno = x_div + E_val
            x_frente_gav = x_div + (E_val / 2.0) + (0.5 * folga_f)
            x_inicio_portas = ox + folga_f
        else:
            x_div = ox + E_val + L_gav
            x_portas_interno = x_div + E_val
            x_gav_interno = ox + E_val
            x_frente_gav = ox + folga_f
            x_inicio_portas = x_div + (E_val / 2.0) + (0.5 * folga_f)
        divisorias_x_mm.append((x_div - ox - E_val + E_val / 2.0) * 1000.0)

        # Pré-calcula a posição da segunda divisória (vão das portas, 3 portas)
        # para transportar suas cavilhas para a base antes de montar a caixa.
        x_div_p_pre = None
        if num_portas == 3:
            larg_util_vao = L_portas - E_val
            larg_vao_1p = larg_util_vao / 3.0
            larg_vao_2p = larg_util_vao * 2.0 / 3.0
            if gav_direita:
                x_div_p_pre = x_portas_interno + larg_vao_1p
            else:
                x_div_p_pre = x_portas_interno + larg_vao_2p
        if x_div_p_pre is not None:
            divisorias_x_mm.append((x_div_p_pre - ox - E_val + E_val / 2.0) * 1000.0)

        # Pré-calcula marcações de calço de dobradiça apenas nas laterais efetivamente usadas
        alturas_calcos_esq_mm = []
        alturas_calcos_dir_mm = []
        calcos_z: list[float] = []
        lado_str = str(lado_abertura_porta).strip().lower() if lado_abertura_porta else ""
        if lado_str.startswith(("dir", "right")):
            single_side = "right"
        elif lado_str.startswith(("esq", "left")):
            single_side = "left"
        else:
            single_side = "left" if gav_direita else "right"

        if num_p == 1:
            sides_list = [single_side]
        elif num_p == 2:
            sides_list = ["left", "right"]
        else:
            sides_list = [single_side, "left", "right"] if gav_direita else ["left", "right", single_side]

        if num_p > 0:
            from ..production.machining import make_hinge_cup_holes
            recuo_topo_val = (recuo_porta_topo_mm / 1000.0) if travessa_frontal_em_pe else 0.0
            alt_porta_val = max(0.05, altura_caixa_pre - recuo_topo_val - 0.006)
            alt_porta_mm = alt_porta_val * 1000.0
            ops_cup = make_hinge_cup_holes(alt_porta_mm)
            calcos_z = [3.0 + o.y for o in ops_cup if "caneco" in o.descricao.lower()]
            if gav_direita and sides_list and sides_list[0] == "left":
                alturas_calcos_esq_mm = list(calcos_z)
            if (not gav_direita) and sides_list and sides_list[-1] == "right":
                alturas_calcos_dir_mm = list(calcos_z)

        # Constrói a caixa básica externa (laterais, base e rodapé)
        groups, info = cls.build_caixa_inferior(
            prefixo="Balcao Misto",
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
            alturas_calcos_esq_mm=alturas_calcos_esq_mm if alturas_calcos_esq_mm else None,
            alturas_calcos_dir_mm=alturas_calcos_dir_mm if alturas_calcos_dir_mm else None,
            divisorias_x_mm=divisorias_x_mm or None,
            divisorias_prof_mm=round(prof_divisoria * 1000.0, 2),
            divisorias_esp_mm=round(E_val * 1000.0, 2),
            ctx=mat_ctx,
        )
        ox, oy, oz = info["ox"], info["oy"], info["oz"]
        L, A, P, E, R = info["L"], info["A"], info["P"], info["E"], info["R"]
        altura_caixa, largura_interna = info["altura_caixa"], info["largura_interna"]
        cor = info["cor"]
        mat_frente = material_frentes or material
        E_frente = (esp_frentes_mm or esp_mm) / 1000.0
        cor_frente = cls.get_material_color(mat_frente)
        LTF = info["LTF"]
        LTT = info["LTT"]

        # Pré-calcula posições Z das prateleiras (para pinos nas divisórias e prateleiras).
        recuo_frontal_prat = 0.025
        prof_prat = max(0.10, P - desc_fundo - recuo_frontal_prat)
        alturas_prat_mm = []
        if num_prateleiras > 0:
            espaco_util = altura_caixa - 2 * E
            passo = espaco_util / (num_prateleiras + 1)
            for i in range(1, num_prateleiras + 1):
                alturas_prat_mm.append((E + (i * passo)) * 1000.0)

        # Divisória vertical intermediária (apoiada na base) separando gaveteiro das portas.
        # Face voltada para as portas recebe calços se a porta adjacente tiver dobradiça
        # nessa face, e pinos de prateleira se houver prateleiras nos vãos das portas.
        desloc_z_div_mm = E * 1000.0
        calcos_z_div = [z - desloc_z_div_mm for z in calcos_z]
        div_ops_main: list[dict[str, Any]] = []
        if gerar_furacao:
            from ..production.machining import (
                make_hinge_plate_holes,
                make_shelf_side_holes,
            )
            # Face voltada para as portas:
            # - gaveteiro à direita (portas à esquerda) -> face esquerda da divisoria
            # - gaveteiro à esquerda (portas à direita) -> face direita da divisoria
            face_portas = "esquerda" if gav_direita else "direita"
            if (face_portas == "esquerda" and sides_list and sides_list[-1] == "right") or \
               (face_portas == "direita" and sides_list and sides_list[0] == "left"):
                div_ops_main.extend(o.to_dict() for o in make_hinge_plate_holes(
                    posicoes_y_mm=calcos_z_div,
                    recuo_borda_frontal_mm=37.0,
                    face=face_portas,
                    tipo_fixacao="parafuso",
                ))
            # Pinos de prateleira na face voltada para os vãos das portas.
            if num_prateleiras > 0:
                for alt_p_z in alturas_prat_mm:
                    div_ops_main.extend(o.to_dict() for o in make_shelf_side_holes(
                        pos_z_na_lateral_mm=alt_p_z - desloc_z_div_mm,
                        prof_prateleira_mm=prof_prat * 1000.0,
                        recuo_frontal_mm=recuo_frontal_prat * 1000.0,
                        afastamento_mm=50.0,
                        esp_prateleira_mm=esp_mm,
                        face=face_portas,
                    ))
        groups.append(cls.build_divisoria(
            name="Balcao Misto - Divisoria",
            origin=(x_div, oy, oz + R + E),
            size=(E, prof_divisoria, alt_divisoria),
            material=material, fita_c1=True, color=cor,
            operacoes=div_ops_main or None,
            cavilha_topo_inferior=gerar_furacao,
            ctx=mat_ctx,
        ))

        # Fundo do armário
        fundo_grp = cls.build_fundo_board(
            prefixo="Balcao Misto",
            largura_interna_m=largura_interna,
            altura_interna_m=altura_caixa - 2 * E,
            largura_total_m=L,
            altura_total_caixa_m=altura_caixa,
            prof_total_m=P,
            esp_lateral_m=E,
            origin_caixa=(ox, oy, oz + R),
            z_interno_base_m=oz + R + E,
            tipo_fundo=eff_tipo_fundo,
            esp_fundo_mm=esp_fundo_mm,
            recuo_fundo_mm=recuo_fundo_mm,
            prof_rasgo_mm=prof_rasgo_mm,
            folga_fundo_mm=folga_fundo_mm,
        )
        if fundo_grp:
            groups.append(fundo_grp)

        num_p = max(1, min(3, num_portas))

        # Divisórias e Prateleiras internas no vão das portas
        # Para 3 portas: adiciona 1 divisória intermediária de sustentação (um vão simples de 1 porta e um duplo de 2 portas)
        tem_divisoria_portas = (num_p == 3)
        vaos_portas = []  # lista de tuplas: (x_inicio_vao, larg_vao)

        if tem_divisoria_portas:
            # Largura útil interna descontando a divisória adicional
            # Se gaveteiro está à esquerda, portas estão à direita: vão duplo de 2 portas primeiro, depois vão simples
            # Se gaveteiro está à direita, portas estão à esquerda: vão simples primeiro, depois vão duplo
            larg_util_vao = L_portas - E
            larg_vao_1p = (larg_util_vao / 3.0)
            larg_vao_2p = (larg_util_vao * 2.0 / 3.0)

            if gav_direita:
                # Portas à esquerda: vão simples (1 porta) + div + vão duplo (2 portas)
                x_v1 = x_portas_interno
                l_v1 = larg_vao_1p
                x_div_p = x_v1 + l_v1
                x_v2 = x_div_p + E
                l_v2 = larg_vao_2p
            else:
                # Portas à direita: vão duplo (2 portas) + div + vão simples (1 porta)
                x_v1 = x_portas_interno
                l_v1 = larg_vao_2p
                x_div_p = x_v1 + l_v1
                x_v2 = x_div_p + E
                l_v2 = larg_vao_1p

            # Operações nas faces das divisórias (calços e pinos de prateleira).
            # O deslocamento em Z (-E) ajusta da origem da divisória (oz + R + E)
            # para a origem das laterais (oz + R).
            desloc_z_div_mm = E * 1000.0
            calcos_z_div = [z - desloc_z_div_mm for z in calcos_z]
            div_ops: list[dict[str, Any]] = []
            if gerar_furacao:
                from ..production.machining import (
                    make_hinge_plate_holes,
                    make_shelf_side_holes,
                )
                # Face esquerda = limite direito do vão anterior.
                # Face direita = limite esquerdo do vão seguinte.
                # Para o balcão misto, a divisória de portas separa vão simples/duplo;
                # coloca calços nas faces conforme o lado de abertura das portas adjacentes.
                # Porta do vão simples (1 porta) abre para fora; vai duplo abre para dentro/central.
                # Usa regra simples: se o primeiro lado for "right", face esquerda recebe calço;
                # se o último lado for "left", face direita recebe calço.
                if sides_list and sides_list[0] == "right":
                    div_ops.extend(o.to_dict() for o in make_hinge_plate_holes(
                        posicoes_y_mm=calcos_z_div,
                        recuo_borda_frontal_mm=37.0,
                        face="esquerda",
                        tipo_fixacao="parafuso",
                    ))
                if sides_list and sides_list[-1] == "left":
                    div_ops.extend(o.to_dict() for o in make_hinge_plate_holes(
                        posicoes_y_mm=calcos_z_div,
                        recuo_borda_frontal_mm=37.0,
                        face="direita",
                        tipo_fixacao="parafuso",
                    ))
                # Pinos das prateleiras nas duas faces da divisória.
                if num_prateleiras > 0:
                    for alt_p_z in alturas_prat_mm:
                        for face_div in ("esquerda", "direita"):
                            div_ops.extend(o.to_dict() for o in make_shelf_side_holes(
                                pos_z_na_lateral_mm=alt_p_z - desloc_z_div_mm,
                                prof_prateleira_mm=prof_prat * 1000.0,
                                recuo_frontal_mm=recuo_frontal_prat * 1000.0,
                                afastamento_mm=50.0,
                                esp_prateleira_mm=esp_mm,
                                face=face_div,
                            ))
            groups.append(cls.build_divisoria(
                name="Balcao Misto - Divisoria Portas",
                origin=(x_div_p, oy, oz + R + E),
                size=(E, prof_divisoria, alt_divisoria),
                material=material, fita_c1=True, color=cor,
                operacoes=div_ops or None,
                cavilha_topo_inferior=gerar_furacao,
                ctx=mat_ctx,
            ))
            vaos_portas.append((x_v1, l_v1))
            vaos_portas.append((x_v2, l_v2))
        else:
            vaos_portas.append((x_portas_interno, L_portas))

        # Prateleiras nos vãos das portas
        if num_prateleiras > 0:
            recuo_frontal_prat = 0.025
            for v_idx, (xv, lv) in enumerate(vaos_portas):
                sufixo_vao = f" Vao {v_idx + 1}" if len(vaos_portas) > 1 else ""
                for i, z_prat in enumerate(alturas_prat_mm, 1):
                    groups.append(cls.build_prateleira(
                        name=f"Balcao Misto - Prateleira{sufixo_vao} {i}",
                        origin=(xv, oy + recuo_frontal_prat, z_prat / 1000.0),
                        size=(lv - 0.002, prof_prat, E),
                        material=material, fita_c1=True, color=cor,
                        gerar_furacao=gerar_furacao,
                        ctx=mat_ctx,
                    ))

        recuo_topo = (recuo_porta_topo_mm / 1000.0) if travessa_frontal_em_pe else 0.0

        # Gaveteiro (esquerda ou direita conforme lado_gaveteiro)
        num_gav = max(1, num_gavetas)
        alt_disponivel_gav = max(0.10, altura_caixa - recuo_topo)
        folga_f = FrentesKitBuilder.resolve_folga_mm(mat_ctx=mat_ctx) / 1000.0
        alt_frente = (alt_disponivel_gav - (num_gav + 1) * folga_f) / num_gav
        larg_frente = L_gav + E + (E / 2.0) - (2.0 * folga_f)
        prof_gaveta = max(0.15, min(P - 0.050, P - desc_fundo - 0.015))
        larg_corredica = max(0.010, float(folga_corredica_mm) / 1000.0)
        larg_caixa_gav = max(0.08, L_gav - larg_corredica)
        alt_caixa_gav = max(0.06, alt_frente - 0.040)
        x_frente = x_frente_gav

        # Materiais da gaveta
        mat_gav = material_gaveta or material
        mat_fg = material_fundo_gaveta or f"MDF Fundo {int(esp_fundo_gaveta_mm)}mm"

        # Gaveteiro do balcão misto via CanonicalDrawerBuilder
        from trazomob.builders.drawers import CanonicalDrawerBuilder
        gav_groups = CanonicalDrawerBuilder.build_stack_gaveteiro(
            prefixo="Gaveteiro",
            num_gavetas=num_gav,
            x_vao=x_gav_interno,
            y_vao=oy,
            z_vao=oz + R,
            larg_vao=L_gav,
            prof_vao=prof_gaveta,
            alt_vao=alt_disponivel_gav,
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
            puxador_tipo=puxador_tipo,
            puxador_cor=puxador_cor,
            puxador_pos=puxador_pos,
            desconto_perfil_mm=desconto_perfil_mm,
            perfil_modelo=perfil_modelo,
            mat_ctx=mat_ctx,
            x_frente=x_frente,
        )
        groups.extend(gav_groups)

        # Portas (lado oposto ao gaveteiro)
        alt_porta = max(0.05, altura_caixa - recuo_topo - (2.0 * folga_f))
        larg_total_portas = L_portas + (E / 2.0) + E - (2.0 * folga_f)
        num_p = max(1, min(3, num_portas))
        folga_entre_portas = folga_f
        larg_util_portas = larg_total_portas - (num_p - 1) * folga_entre_portas
        larg_cada_porta = max(0.10, larg_util_portas / num_p)

        x_p = x_inicio_portas
        for p_i, d_side in enumerate(sides_list):
            lado_txt = "Dir" if d_side == "right" else "Esq"
            if num_p == 1:
                p_nome = f"Balcao Misto - Porta {lado_txt}"
            elif num_p == 2:
                p_nome = f"Balcao Misto - Porta {lado_txt}"
            else:
                p_nome = f"Balcao Misto - Porta {p_i+1} ({lado_txt})"

            builder_porta = cls.build_porta_esquerda if d_side == "left" else cls.build_porta_direita
            groups.append(builder_porta(
                name=p_nome,
                origin=(x_p, oy - E_frente, oz + R + folga_f),
                size=(larg_cada_porta, E_frente, alt_porta),
                material=mat_frente,
                color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                is_upper=False,
                gerar_furacao=gerar_furacao,
                ctx=mat_ctx,
            ))
            x_p += larg_cada_porta + folga_entre_portas

        return groups

    @classmethod
    def build_aereo(
        cls, largura_mm: float, altura_mm: float, prof_mm: float,
        esp_mm: float = 15.0, num_portas: int = 2, num_prateleiras: int = 1,
        num_divisoes: int | None = None,
        lado_abertura_porta: str = "esquerda",
        material: str = "MDF Branco TX 15mm", material_frentes: str | None = None,
        esp_frentes_mm: float | None = None,
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
        **kwargs,
    ) -> list[Group]:
        if mat_ctx is None:
            mat_ctx = ModuloMaterialContext(
                material_caixa=material,
                material_fita_caixa=kwargs.get("material_fita_caixa"),
                fita_caixa_modo=kwargs.get("fita_caixa_modo", "frontal_1L"),
                material_frentes=material_frentes or material,
            )
        ox, oy, oz = offset
        mat_frente = material_frentes or material
        E_frente = (esp_frentes_mm or esp_mm) / 1000.0
        cor_frente = cls.get_material_color(mat_frente)

        E_val = esp_mm / 1000.0
        desc_fundo = cls._calc_desconto_traseiro_fundo(tipo_fundo, esp_fundo_mm, recuo_fundo_mm, esp_travessa_traseira_mm=esp_mm)
        recuo_frontal_prat = 0.020
        P_val = prof_mm / 1000.0
        A_val = altura_mm / 1000.0
        prof_prat = max(0.10, P_val - desc_fundo - recuo_frontal_prat)

        n_portas = max(0, int(num_portas))

        # Divisórias automáticas seguindo a regra dos 400mm por porta (mesma lógica do balcão):
        # 1 ou 2 portas = 0 divisórias; 3 ou 4 portas = 1 divisória central
        from ..domain.module_geometry import auto_divisoes_for_doors
        if n_portas > 0:
            min_divisoes = auto_divisoes_for_doors(n_portas)
            max_divisoes = max(0, n_portas - 1)
            solicitadas = int(num_divisoes) if num_divisoes is not None else min_divisoes
            eff_num_divisoes = max(min_divisoes, min(max(0, solicitadas), max_divisoes))
        else:
            eff_num_divisoes = max(0, int(num_divisoes or 0))
        n_bays = eff_num_divisoes + 1

        # Distribui as portas pelos vãos e define o lado da dobradiça de cada porta.
        if n_portas > 0:
            door_counts = [n_portas // n_bays] * n_bays
            for i in range(n_portas % n_bays):
                door_counts[i] += 1
        else:
            door_counts = [0] * n_bays

        lado = str(lado_abertura_porta or "esquerda").strip().lower()
        default_side = "right" if lado.startswith(("dir", "right")) else "left"

        bay_door_sides: list[list[str]] = []
        for b_idx, qtd in enumerate(door_counts):
            if qtd <= 0:
                bay_door_sides.append([])
            elif qtd == 1:
                bay_door_sides.append([default_side])
            else:
                bay_door_sides.append(
                    ["left" if i % 2 == 0 else "right" for i in range(qtd)])
        door_sides = [s for bay in bay_door_sides for s in bay]

        # Pré-calcula as alturas das prateleiras para transportar furações às laterais do aéreo
        alturas_prat_mm = []
        if num_prateleiras > 0:
            espaco_util = A_val - 2 * E_val
            passo = espaco_util / (num_prateleiras + 1)
            for i in range(1, num_prateleiras + 1):
                alturas_prat_mm.append((E_val + (i * passo)) * 1000.0)

        # Pré-calcula marcações de calço de dobradiça nas laterais do aéreo
        alturas_calcos_esq_mm = []
        alturas_calcos_dir_mm = []
        calcos_z: list[float] = []
        if n_portas > 0:
            from ..production.machining import make_hinge_cup_holes
            alt_porta_val = max(0.05, A_val - 0.006)
            alt_porta_mm = alt_porta_val * 1000.0
            ops_cup = make_hinge_cup_holes(alt_porta_mm)
            calcos_z = [3.0 + o.y for o in ops_cup if "caneco" in o.descricao.lower()]
            if door_sides and door_sides[0] == "left":
                alturas_calcos_esq_mm = list(calcos_z)
            if door_sides and door_sides[-1] == "right":
                alturas_calcos_dir_mm = list(calcos_z)

        largura_interna_pre = largura_mm / 1000.0 - 2 * E_val
        if n_portas > 0:
            largura_por_porta = max(0.05, (largura_interna_pre - eff_num_divisoes * E_val) / n_portas)
            largura_vaos_pre = [max(0.05, qtd * largura_por_porta) for qtd in door_counts]
        else:
            largura_vaos_pre = [
                max(0.05, (largura_interna_pre - eff_num_divisoes * E_val) / n_bays)
            ] * n_bays

        divisorias_x_mm: list[float] = []
        x_rel = 0.0
        for d_i in range(eff_num_divisoes):
            divisorias_x_mm.append(
                (x_rel + largura_vaos_pre[d_i] + E_val / 2.0) * 1000.0)
            x_rel += largura_vaos_pre[d_i] + E_val

        groups, info = cls.build_caixa_modular(
            prefixo="Aereo",
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
            alturas_prateleiras_mm=alturas_prat_mm if num_prateleiras > 0 else None,
            prof_prateleira_mm=prof_prat * 1000.0,
            recuo_prateleira_frontal_mm=recuo_frontal_prat * 1000.0,
            alturas_calcos_esq_mm=alturas_calcos_esq_mm if alturas_calcos_esq_mm else None,
            alturas_calcos_dir_mm=alturas_calcos_dir_mm if alturas_calcos_dir_mm else None,
            divisorias_x_mm=divisorias_x_mm or None,
            divisorias_prof_mm=round((P_val - desc_fundo) * 1000.0, 2),
            divisorias_esp_mm=round(E_val * 1000.0, 2),
            gerar_furacao=gerar_furacao,
            dispositivo_fixacao=dispositivo_fixacao,
            ctx=mat_ctx,
        )

        ox, oy, oz = info["ox"], info["oy"], info["oz"]
        L, A, P, E = info["L"], info["A"], info["P"], info["E"]
        cor = cls.get_material_color(material)
        largura_interna = L - 2 * E
        prof_div = max(0.15, P - desc_fundo)
        alt_div = A - 2 * E

        # Travessa traseira superior junto ao tampo (sustentação no material escolhido, largura padrão 70mm)
        # Posicionada imediatamente à frente do desconto do fundo para evitar sobreposição
        larg_trav_sup = 0.070
        y_travessa = oy + P - desc_fundo - E
        groups.append(cls.build_travessa_peca(
            name="Aereo - Travessa Traseira Superior",
            origin=(ox + E, y_travessa, oz + A - E - larg_trav_sup),
            size=(largura_interna, E, larg_trav_sup),
            material=material,
            fita_c1=True,
            color=cor,
        ))

        # Divisórias verticais estruturais
        largura_vaos = largura_vaos_pre
        x_vaos: list[float] = []
        x_curr = ox + E
        for d_i in range(eff_num_divisoes):
            x_vaos.append(x_curr)
            x_div = x_curr + largura_vaos[d_i]

            div_ops: list[dict[str, Any]] = []
            if gerar_furacao:
                from ..production.machining import (
                    make_hinge_plate_holes,
                    make_shelf_side_holes,
                )
                desloc_z_div_mm = E * 1000.0
                calcos_z_div = [z - desloc_z_div_mm for z in calcos_z]

                # Face esquerda da divisória
                if bay_door_sides[d_i] and bay_door_sides[d_i][-1] == "right":
                    div_ops.extend(o.to_dict() for o in make_hinge_plate_holes(
                        posicoes_y_mm=calcos_z_div,
                        recuo_borda_frontal_mm=37.0,
                        face="esquerda",
                        tipo_fixacao="parafuso",
                    ))
                # Face direita da divisória
                if bay_door_sides[d_i + 1] and bay_door_sides[d_i + 1][0] == "left":
                    div_ops.extend(o.to_dict() for o in make_hinge_plate_holes(
                        posicoes_y_mm=calcos_z_div,
                        recuo_borda_frontal_mm=37.0,
                        face="direita",
                        tipo_fixacao="parafuso",
                    ))

                # Pinos das prateleiras nas duas faces da divisória
                if num_prateleiras > 0:
                    for alt_p_z in alturas_prat_mm:
                        for face_div in ("esquerda", "direita"):
                            div_ops.extend(o.to_dict() for o in make_shelf_side_holes(
                                pos_z_na_lateral_mm=alt_p_z - desloc_z_div_mm,
                                prof_prateleira_mm=prof_prat * 1000.0,
                                recuo_frontal_mm=recuo_frontal_prat * 1000.0,
                                afastamento_mm=50.0,
                                esp_prateleira_mm=esp_mm,
                                face=face_div,
                            ))

            div_name = (
                "Aereo - Divisoria Central" if eff_num_divisoes == 1
                else f"Aereo - Divisoria {d_i + 1}"
            )
            groups.append(cls.build_divisoria(
                name=div_name,
                origin=(x_div, oy, oz + E),
                size=(E, prof_div, alt_div),
                material=material, fita_c1=True, color=cor,
                operacoes=div_ops or None,
                cavilha_topo_inferior=gerar_furacao,
            ))
            x_curr = x_div + E
        x_vaos.append(x_curr)

        # Prateleiras internas por vão
        if num_prateleiras > 0:
            espaco_util = A - 2 * E
            passo = espaco_util / (num_prateleiras + 1)
            for v_idx, (xv, lv) in enumerate(zip(x_vaos, largura_vaos)):
                nome_vao = f"Vao {v_idx + 1}" if eff_num_divisoes > 0 else ""
                for i in range(1, num_prateleiras + 1):
                    z_prat = oz + E + (i * passo)
                    prat_name = (
                        f"Aereo - {nome_vao} Prateleira {i}"
                        if eff_num_divisoes > 0 else f"Aereo - Prateleira {i}"
                    )
                    groups.append(cls.build_prateleira(
                        name=prat_name,
                        origin=(xv, oy + recuo_frontal_prat, z_prat),
                        size=(max(0.05, lv - 0.002), prof_prat, E),
                        material=material, fita_c1=True, color=cor,
                        gerar_furacao=gerar_furacao,
                        ctx=mat_ctx,
                    ))

        # Portas
        if n_portas > 0:
            folga_f = FrentesKitBuilder.resolve_folga_mm(mat_ctx=mat_ctx) / 1000.0
            alt_porta = max(0.05, A - (2.0 * folga_f))
            folga_entre_portas = folga_f
            larg_total_disponivel = L - (2.0 * folga_f) - (n_portas - 1) * folga_entre_portas
            larg_porta = max(0.10, larg_total_disponivel / n_portas)

            x_porta = ox + folga_f
            for p_i in range(n_portas):
                d_side = door_sides[p_i] if p_i < len(door_sides) else ("left" if p_i % 2 == 0 else "right")
                lado_txt = "Esq" if d_side == "left" else "Dir"

                if n_portas == 1:
                    p_nome = f"Aereo - Porta {lado_txt}"
                elif n_portas == 2:
                    p_nome = f"Aereo - Porta {lado_txt}"
                else:
                    p_nome = f"Aereo - Porta {p_i+1} ({lado_txt})"

                builder_porta = cls.build_porta_esquerda if d_side == "left" else cls.build_porta_direita
                groups.append(builder_porta(
                    name=p_nome,
                    origin=(x_porta, oy - E_frente, oz + folga_f),
                    size=(larg_porta, E_frente, alt_porta),
                    material=mat_frente,
                    color=cor_frente,
                    puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                    desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                    is_upper=True,
                    gerar_furacao=gerar_furacao,
                    ctx=mat_ctx,
                ))
                x_porta += larg_porta + folga_entre_portas

        return groups

    @classmethod
    def build_aereo_correr(
        cls, largura_mm: float, altura_mm: float, prof_mm: float,
        esp_mm: float = 15.0, num_vaos: int = 3, num_portas: int | None = None,
        num_prateleiras: int = 0,
        material: str = "MDF Branco TX 15mm", material_frentes: str | None = None,
        esp_frentes_mm: float | None = None,
        tipo_fundo: str = "rasgo", esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0, prof_rasgo_mm: float = 5.0,
        folga_fundo_mm: float = 2.0,
        offset: tuple[float, float, float] = (0.0, 0.0, 1.4),
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto", puxador_pos: str = "padrao", desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        exibir_portas: bool = True,
        gerar_furacao: bool = True,
        dispositivo_fixacao: str = "minifix_cavilha",
        mat_ctx: ModuloMaterialContext | None = None,
        **kwargs,
    ) -> list[Group]:
        """Gera armário aéreo para portas de correr de 2 a 4 vãos com divisórias verticais estruturais."""
        from PySide6.QtGui import QVector3D
        if mat_ctx is None:
            mat_ctx = ModuloMaterialContext(
                material_caixa=material,
                material_fita_caixa=kwargs.get("material_fita_caixa"),
                fita_caixa_modo=kwargs.get("fita_caixa_modo", "frontal_1L"),
                material_frentes=material_frentes or material,
            )
        ox, oy, oz = offset
        E_frente = (esp_frentes_mm or esp_mm) / 1000.0

        # Número de vãos e portas: 2 a 4
        qtd = int(num_vaos if num_vaos is not None else (num_portas if num_portas is not None else 3))
        n_vaos = max(2, min(4, qtd))
        n_divisoes = n_vaos - 1

        E_val = esp_mm / 1000.0
        desc_fundo = cls._calc_desconto_traseiro_fundo(tipo_fundo, esp_fundo_mm, recuo_fundo_mm, esp_travessa_traseira_mm=esp_mm)
        prof_util_mm = prof_mm - (desc_fundo * 1000.0)

        # Recuo frontal para acomodar trilhos duplos e portas de correr embutidas
        prof_sistema_correr_mm = 50.0  # 50mm para trilho duplo de aéreo
        prof_sistema_correr = prof_sistema_correr_mm / 1000.0
        recuo_trilhos = prof_sistema_correr
        prof_int = (prof_util_mm - prof_sistema_correr_mm) / 1000.0
        prof_div = prof_int
        prof_prat = prof_int

        # Pré-calcula posições relativas das divisórias verticais
        largura_interna_mm = largura_mm - (2.0 * esp_mm)
        larg_total_vaos_mm = largura_interna_mm - (n_divisoes * esp_mm)
        larg_vao_mm = larg_total_vaos_mm / n_vaos
        larg_vao = larg_vao_mm / 1000.0

        divisorias_x_mm: list[float] = []
        for d_i in range(n_divisoes):
            x_div_mm = (d_i + 1) * larg_vao_mm + d_i * esp_mm
            divisorias_x_mm.append(x_div_mm)

        # Pré-calcula alturas das prateleiras internas para furações nas laterais e divisórias
        alturas_prat_mm = []
        altura_int_mm = altura_mm - (2.0 * esp_mm)
        if num_prateleiras > 0:
            passo = altura_int_mm / (num_prateleiras + 1)
            for i in range(1, num_prateleiras + 1):
                alturas_prat_mm.append(esp_mm + (i * passo))

        # 1. Caixa modular universal com topo fechado
        groups, info = cls.build_caixa_modular(
            prefixo=f"Aereo {n_vaos}V Correr",
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
            alturas_prateleiras_mm=alturas_prat_mm if num_prateleiras > 0 else None,
            prof_prateleira_mm=prof_prat * 1000.0,
            recuo_prateleira_frontal_mm=recuo_trilhos * 1000.0,
            divisorias_x_mm=divisorias_x_mm,
            divisorias_prof_mm=prof_div * 1000.0,
            divisorias_esp_mm=esp_mm,
            gerar_furacao=gerar_furacao,
            dispositivo_fixacao=dispositivo_fixacao,
            ctx=mat_ctx,
        )

        L, A, P, E = info["L"], info["A"], info["P"], info["E"]
        larg_interna = info["largura_interna"]
        cor = info["cor"]
        alt_div = A - (2 * E)

        # 2. Divisórias Verticais Estruturais
        x_vaos: list[tuple[float, float]] = []
        x_curr = ox + E
        for d_i in range(n_divisoes):
            x_div = ox + E + (d_i + 1) * larg_vao + (d_i * E)
            x_vaos.append((x_curr, larg_vao))

            div_ops = []
            if gerar_furacao:
                from ..production.machining import (
                    make_vertical_divider_joint_holes,
                    make_shelf_side_holes,
                )
                cav_ops = make_vertical_divider_joint_holes(
                    prof_divisoria_mm=prof_div * 1000.0,
                    esp_divisoria_mm=esp_mm,
                    furacao_cima=False,
                    furacao_baixo=True,
                )
                div_ops.extend(o.to_dict() for o in cav_ops)

                if alturas_prat_mm:
                    for alt_p_z in alturas_prat_mm:
                        for face_div in ("esquerda", "direita"):
                            div_ops.extend(o.to_dict() for o in make_shelf_side_holes(
                                pos_z_na_lateral_mm=alt_p_z - esp_mm,
                                prof_prateleira_mm=prof_prat * 1000.0,
                                recuo_frontal_mm=0.0,
                                afastamento_mm=50.0,
                                esp_prateleira_mm=esp_mm,
                                face=face_div,
                            ))

            groups.append(cls.build_divisoria(
                name=f"Aereo {n_vaos}V - Divisoria {d_i + 1}",
                origin=(x_div, oy + recuo_trilhos, oz + E),
                size=(E, prof_div, alt_div),
                material=material, fita_c1=True, color=cor,
                operacoes=div_ops or None,
                cavilha_topo_inferior=gerar_furacao,
                ctx=mat_ctx,
            ))
            x_curr = x_div + E
        x_vaos.append((x_curr, larg_vao))

        # 3. Prateleiras Internas por Vão
        if num_prateleiras > 0:
            espaco_util = A - 2 * E
            passo = espaco_util / (num_prateleiras + 1)
            for v_idx, (xv, lv) in enumerate(x_vaos):
                for i in range(1, num_prateleiras + 1):
                    z_prat = oz + E + (i * passo)
                    groups.append(cls.build_prateleira(
                        name=f"Aereo {n_vaos}V - Prat Vao {v_idx + 1}_{i}",
                        origin=(xv, oy + recuo_trilhos, z_prat),
                        size=(max(0.05, lv - 0.002), prof_prat, E),
                        material=material, fita_c1=True, color=cor,
                        gerar_furacao=gerar_furacao,
                        ctx=mat_ctx,
                    ))

        # 4. Trilhos Duplos de Alumínio
        groups.append(create_board_group(
            f"Aereo {n_vaos}V - Trilho Inferior",
            (ox + E, oy + 0.006, oz + E),
            (larg_interna, 0.038, 0.008), "Alumínio Anodizado", color=(0.75, 0.77, 0.80)
        ))
        groups.append(create_board_group(
            f"Aereo {n_vaos}V - Trilho Superior",
            (ox + E, oy + 0.006, oz + A - E - 0.030),
            (larg_interna, 0.038, 0.030), "Alumínio Anodizado", color=(0.75, 0.77, 0.80)
        ))

        # 5. Portas de Correr (2, 3 ou 4 folhas)
        if exibir_portas:
            transpasse = 0.030  # 30mm de transpasse padrão
            larg_porta = (larg_interna + ((n_vaos - 1) * transpasse)) / n_vaos
            alt_porta = max(0.10, A - (2 * E) - 0.015)
            z_porta = oz + E + 0.008
            y_trilho_frontal = oy + 0.008
            y_trilho_traseiro = oy + 0.008 + E_frente + 0.008
            slide_dist = max(0.05, larg_porta - transpasse)

            eff_pux_pos = puxador_pos
            if str(eff_pux_pos or "padrao").lower() in ("padrao", "auto", "superior", "topo"):
                eff_pux_pos = "extensao"

            def _add_porta_correr(nome, x, y, side, axis):
                spec = ChapaSpec.resolve(
                    nome, PapelChapa.PORTA, mat_ctx,
                    fita_override=(True, True, True, True),
                )
                porta = build_chapa(
                    spec,
                    (x, y, z_porta),
                    (larg_porta, E_frente, alt_porta),
                    color=cls.get_material_color(spec.material),
                    puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                    desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                    door_side=side,
                )
                if getattr(porta, "ext", None) is None:
                    porta.ext = {}
                porta.ext["slide_axis"] = axis
                porta.ext["slide_distance"] = float(slide_dist)
                groups.append(porta)
                return porta

            if n_vaos == 2:
                # Folha 1 (Esq, trilho traseiro) -> corre para direita
                _add_porta_correr(
                    "Aereo Correr - Porta 1 Folha Traseira",
                    ox + E, y_trilho_traseiro, "right", QVector3D(1.0, 0.0, 0.0),
                )

                # Folha 2 (Dir, trilho frontal) -> corre para esquerda
                x_p2 = ox + E + larg_interna - larg_porta
                _add_porta_correr(
                    "Aereo Correr - Porta 2 Folha Frontal",
                    x_p2, y_trilho_frontal, "left", QVector3D(-1.0, 0.0, 0.0),
                )

            elif n_vaos == 3:
                # 3 Folhas:
                # Folha 1: Esq (trilho traseiro) -> corre para a direita
                x_p1 = ox + E
                _add_porta_correr(
                    "Aereo Correr - Porta 1 Esq (Interna)",
                    x_p1, y_trilho_traseiro, "right", QVector3D(1.0, 0.0, 0.0),
                )

                # Folha 2: Centro (trilho frontal) -> corre para ambos os lados
                x_p2 = ox + E + (larg_interna * 0.5) - (larg_porta * 0.5)
                _add_porta_correr(
                    "Aereo Correr - Porta 2 Centro (Externa)",
                    x_p2, y_trilho_frontal, "both", QVector3D(1.0, 0.0, 0.0),
                )

                # Folha 3: Dir (trilho traseiro) -> corre para a esquerda
                x_p3 = ox + E + larg_interna - larg_porta
                _add_porta_correr(
                    "Aereo Correr - Porta 3 Dir (Interna)",
                    x_p3, y_trilho_traseiro, "left", QVector3D(-1.0, 0.0, 0.0),
                )

            else:
                # 4 Folhas:
                # Folha 1: Canto Esq (Traseira/Interna)
                x_p1 = ox + E
                _add_porta_correr(
                    "Aereo Correr - Porta 1 Esq (Interna)",
                    x_p1, y_trilho_traseiro, "right", QVector3D(1.0, 0.0, 0.0),
                )

                # Folha 2: Centro Esq (Frontal/Externa)
                x_p2 = ox + E + (larg_interna * 0.5) - larg_porta
                _add_porta_correr(
                    "Aereo Correr - Porta 2 Centro Esq (Externa)",
                    x_p2, y_trilho_frontal, "left", QVector3D(-1.0, 0.0, 0.0),
                )

                # Folha 3: Centro Dir (Frontal/Externa)
                x_p3 = ox + E + (larg_interna * 0.5)
                _add_porta_correr(
                    "Aereo Correr - Porta 3 Centro Dir (Externa)",
                    x_p3, y_trilho_frontal, "right", QVector3D(1.0, 0.0, 0.0),
                )

                # Folha 4: Canto Dir (Traseira/Interna)
                x_p4 = ox + E + larg_interna - larg_porta
                _add_porta_correr(
                    "Aereo Correr - Porta 4 Dir (Interna)",
                    x_p4, y_trilho_traseiro, "left", QVector3D(-1.0, 0.0, 0.0),
                )

        return groups

    @classmethod
    def build_nicho(
        cls, largura_mm: float, altura_mm: float, prof_mm: float,
        esp_mm: float = 15.0, divisoes_vert: int = 0, divisoes_horiz: int = 1,
        material: str = "MDF Louro Freijó 15mm", offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        tem_fundo: bool = False,
        tipo_fundo: str = "sem_fundo", esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0, prof_rasgo_mm: float = 5.0,
        folga_fundo_mm: float = 2.0,
        fita_caixa_modo: str = "frontal_1L",
        material_fita_caixa: str | None = None,
        gerar_furacao: bool = True,
        dispositivo_fixacao: str = "minifix_cavilha",
        lado_abertura_porta: str | None = None,
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> list[Group]:
        eff_tem_fundo = bool(tem_fundo) and str(tipo_fundo).lower() != "sem_fundo"
        desc_fundo = cls._calc_desconto_traseiro_fundo(
            tipo_fundo if eff_tem_fundo else "sem_fundo", esp_fundo_mm, recuo_fundo_mm
        )
        prof_util = max(0.05, P_init := (prof_mm / 1000.0) - desc_fundo)
        E_init = esp_mm / 1000.0
        A_init = altura_mm / 1000.0
        altura_int_init = A_init - 2 * E_init

        alturas_prat_nicho_mm = []
        if divisoes_horiz > 0 and divisoes_vert == 0:
            passo = (altura_int_init - (divisoes_horiz * E_init)) / (divisoes_horiz + 1)
            for i in range(1, divisoes_horiz + 1):
                z_div_rel = E_init + (i * passo) + ((i - 1) * E_init)
                alturas_prat_nicho_mm.append(z_div_rel * 1000.0)

        groups, info = cls.build_caixa_modular(
            prefixo="Nicho",
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            prof_mm=prof_mm,
            esp_mm=esp_mm,
            rodape_mm=0.0,
            tipo_topo="fechado",
            material=material,
            offset=offset,
            tem_fundo=eff_tem_fundo,
            tipo_fundo=tipo_fundo if eff_tem_fundo else "sem_fundo",
            esp_fundo_mm=esp_fundo_mm,
            recuo_fundo_mm=recuo_fundo_mm,
            prof_rasgo_mm=prof_rasgo_mm,
            folga_fundo_mm=folga_fundo_mm,
            fita_caixa_modo=fita_caixa_modo,
            material_fita_caixa=material_fita_caixa,
            gerar_furacao=gerar_furacao,
            dispositivo_fixacao=dispositivo_fixacao,
            alturas_prateleiras_mm=alturas_prat_nicho_mm if alturas_prat_nicho_mm else None,
            prof_prateleira_mm=prof_util * 1000.0,
            recuo_prateleira_frontal_mm=0.0,
            ctx=mat_ctx,
        )
        ox, oy, oz = info["ox"], info["oy"], info["oz"]
        L, A, P, E = info["L"], info["A"], info["P"], info["E"]
        largura_interna = info["largura_interna"]
        altura_interna = A - 2 * E
        cor = info["cor"]
        desc_fundo = cls._calc_desconto_traseiro_fundo(
            tipo_fundo if eff_tem_fundo else "sem_fundo", esp_fundo_mm, recuo_fundo_mm
        )
        prof_util = max(0.05, P - desc_fundo)

        if divisoes_horiz > 0:
            passo = (altura_interna - (divisoes_horiz * E)) / (divisoes_horiz + 1)
            for i in range(1, divisoes_horiz + 1):
                z_div = oz + E + (i * passo) + ((i - 1) * E)
                groups.append(cls.build_prateleira(
                    name=f"Nicho - Divisao Horiz {i}",
                    origin=(ox + E, oy, z_div),
                    size=(largura_interna, prof_util, E),
                    material=material, fita_c1=True, color=cor,
                    gerar_furacao=gerar_furacao,
                    ctx=mat_ctx,
                ))

        if divisoes_vert > 0:
            passo_v = (largura_interna - (divisoes_vert * E)) / (divisoes_vert + 1)
            for i in range(1, divisoes_vert + 1):
                x_div = ox + E + (i * passo_v) + ((i - 1) * E)
                groups.append(cls.build_divisoria(
                    name=f"Nicho - Divisao Vert {i}",
                    origin=(x_div, oy, oz + E),
                    size=(E, prof_util, altura_interna),
                    material=material, fita_c1=True, color=cor,
                    ctx=mat_ctx,
                ))

        return groups

    @classmethod
    def build_balcao_pia(
        cls, largura_mm: float, altura_mm: float, prof_mm: float,
        esp_mm: float = 15.0, rodape_mm: float = 100.0, num_portas: int = 2,
        material: str = "MDF Branco TX 15mm", material_frentes: str | None = None,
        esp_frentes_mm: float | None = None,
        tem_fundo: bool = False,
        tipo_fundo: str = "sem_fundo", esp_fundo_mm: float = 6.0,
        recuo_fundo_mm: float = 10.0, prof_rasgo_mm: float = 5.0,
        folga_fundo_mm: float = 2.0,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto", puxador_pos: str = "padrao", desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        # Parâmetros das travessas (unificados e compatibilidade)
        travessa_frontal_em_pe: bool = True,
        travessa_traseira_em_pe: bool = False,
        larg_travessa_frontal_mm: float = 70.0,
        larg_travessa_traseira_mm: float = 70.0,
        recuo_porta_topo_mm: float = 50.0,
        larg_travessa_mm: float | None = None,
        recuo_porta_pia_mm: float | None = None,
        material_travessas: str | None = None,
        esp_travessas_mm: float | None = None,
        fita_travessas_modo: str = "frontal_1L",
        fita_travessas_faces: dict[str, bool] | None = None,
        fita_caixa_modo: str = "frontal_1L",
        material_fita_caixa: str | None = None,
        material_fita_travessas: str | None = None,
        gerar_furacao: bool = True,
        dispositivo_fixacao: str = "minifix_cavilha",
        lado_abertura_porta: str | None = None,
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> list[Group]:
        """Balcão de pia/cuba."""
        if larg_travessa_mm is not None:
            larg_travessa_frontal_mm = larg_travessa_mm
        if recuo_porta_pia_mm is not None:
            recuo_porta_topo_mm = recuo_porta_pia_mm

        groups, info = cls.build_caixa_inferior(
            prefixo="Balcao Pia",
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
            ctx=mat_ctx,
        )
        ox, oy, oz = info["ox"], info["oy"], info["oz"]
        L, A, P, E, R = info["L"], info["A"], info["P"], info["E"], info["R"]
        altura_caixa, largura_interna = info["altura_caixa"], info["largura_interna"]
        cor = info["cor"]
        mat_frente = material_frentes or material
        E_frente = (esp_frentes_mm or esp_mm) / 1000.0
        cor_frente = cls.get_material_color(mat_frente)

        # Fundo (opcional — normalmente sem fundo no balcão de pia por causa do sifão)
        eff_tipo_fundo = "sem_fundo" if not tem_fundo else tipo_fundo
        fundo_grp = cls.build_fundo_board(
            prefixo="Balcao Pia",
            largura_interna_m=largura_interna,
            altura_interna_m=altura_caixa - 2 * E,
            largura_total_m=L,
            altura_total_caixa_m=altura_caixa,
            prof_total_m=P,
            esp_lateral_m=E,
            origin_caixa=(ox, oy, oz + R),
            z_interno_base_m=oz + R + E,
            tipo_fundo=eff_tipo_fundo,
            esp_fundo_mm=esp_fundo_mm,
            recuo_fundo_mm=recuo_fundo_mm,
            prof_rasgo_mm=prof_rasgo_mm,
            folga_fundo_mm=folga_fundo_mm,
        )
        if fundo_grp:
            groups.append(fundo_grp)

        # Portas — quando a travessa frontal está em pé, o topo das portas fica rebaixado (recuo vertical)
        if num_portas > 0:
            folga_f = FrentesKitBuilder.resolve_folga_mm(mat_ctx=mat_ctx) / 1000.0
            recuo_topo = (recuo_porta_topo_mm / 1000.0) if travessa_frontal_em_pe else 0.0
            alt_porta = max(0.05, altura_caixa - recuo_topo - folga_f)
            porta_z0 = oz + R + folga_f
            lado_str = str(lado_abertura_porta or "esquerda").strip().lower()
            default_side = "right" if lado_str.startswith(("dir", "right")) else "left"

            if num_portas == 1:
                larg_porta = L - (2.0 * folga_f)
                lado_txt = "Dir" if default_side == "right" else "Esq"
                builder_porta = cls.build_porta_direita if default_side == "right" else cls.build_porta_esquerda
                groups.append(builder_porta(
                    name=f"Balcao Pia - Porta Unica ({lado_txt})",
                    origin=(ox + folga_f, oy - E_frente, porta_z0),
                    size=(larg_porta, E_frente, alt_porta),
                    material=mat_frente,
                    color=cor_frente,
                    puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                    desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                    is_upper=False,
                    ctx=mat_ctx,
                ))
            else:
                larg_porta = (L - ((num_portas + 1) * folga_f)) / num_portas
                for i in range(num_portas):
                    if num_portas % 2 == 1 and i == num_portas - 1:
                        side = default_side
                    else:
                        side = "left" if i % 2 == 0 else "right"
                    lado_txt = "Dir" if side == "right" else "Esq"
                    builder_porta = cls.build_porta_esquerda if side == "left" else cls.build_porta_direita
                    groups.append(builder_porta(
                        name=f"Balcao Pia - Porta {i + 1} ({lado_txt})",
                        origin=(ox + folga_f + i * (larg_porta + folga_f), oy - E_frente, porta_z0),
                        size=(larg_porta, E_frente, alt_porta),
                        material=mat_frente,
                        color=cor_frente,
                        puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                        desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                        is_upper=False,
                        ctx=mat_ctx,
                    ))

        return groups


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

    @classmethod
    def build_balcao_peninsula(
        cls,
        largura_mm: float = 1200.0,
        altura_mm: float = 850.0,
        prof_mm: float = 600.0,
        largura_mesa_mm: float = 800.0,
        comprimento_mesa_mm: float = 1200.0,
        esp_mm: float = 15.0,
        esp_tampo_mm: float = 30.0,
        rodape_mm: float = 100.0,
        material: str = "MDF Branco 15mm",
        material_tampo: str = "MDF Louro Freijo 30mm",
        cor: tuple[float, float, float] | None = None,
        cor_tampo: tuple[float, float, float] | None = None,
        origin: tuple[float, float, float] = (0.0, 0.0, 0.0),
        puxador_tipo: str = "perfil",
        puxador_cor: str = "anodizado",
        puxador_pos: str = "superior",
        **kwargs: Any,
    ) -> list[Group]:
        """Constrói balcão ilha/península com portas inferiores e mesa projetada com pé tubular."""
        ox, oy, oz = origin
        L = largura_mm / 1000.0
        H = (altura_mm - esp_tampo_mm) / 1000.0  # Altura da caixaria até a base do tampo
        P = prof_mm / 1000.0
        E = esp_mm / 1000.0
        R = rodape_mm / 1000.0
        Et = esp_tampo_mm / 1000.0

        # 1. Base, laterais e caixaria padrão de 2 portas
        groups: list[Group] = []

        # Caixaria
        caixaria = cls.build_balcao(
            largura_mm=largura_mm,
            altura_mm=H * 1000.0,
            prof_mm=prof_mm,
            esp_mm=esp_mm,
            rodape_mm=rodape_mm,
            num_portas=2,
            num_prateleiras=1,
            tem_fundo=True,
            material=material,
            offset=origin,
            puxador_tipo=puxador_tipo,
            puxador_cor=puxador_cor,
            puxador_pos=puxador_pos,
        )
        groups.extend(caixaria)

        # 2. Tampo da Mesa Península com pontas frontais arredondadas
        Lm = largura_mesa_mm / 1000.0
        Cm = comprimento_mesa_mm / 1000.0
        # O tampo apoia sobre o balcão (da esquerda ou centro) e projeta para fora (ex: ao longo de X ou Y)
        # Projetando perpendicularmente para a frente (em -Y) ou extensão lateral (em +X):
        # Península típica: projeta para a frente de quem olha o balcão (em -Y), saindo de oy até oy - Cm
        raio = min(0.15, Lm / 3.0)

        # Polígono do tampo no plano XY:
        # Cobre toda a largura L do balcão na área traseira/sobre o móvel
        # e projeta a bancada de refeições (península):
        # Para ser uma bancada de ilha/península completa e realista:
        # Cobrimos o topo do balcão inteiro (0 a L em X, 0 a P em Y)
        # e a mesa projeta para a frente (em -Y, de 0 até -Cm) com largura Lm (centralizada ou alinhada).
        # Vamos fazer o tampo cobrir todo o balcão (0 a L) e estender a mesa para frente:
        # Ou um tampo contínuo que cobre o balcão (0 a L, 0 a P) + balanço/mesa.
        # Mais ergonômico e limpo para península: tampo inteiro cobre o balcão e estende para frente:
        x_mesa_esq = ox + max(0.0, (L - Lm) / 2.0)
        x_mesa_dir = x_mesa_esq + Lm
        y_frente = oy - Cm
        y_tras = oy + P

        # Vamos traçar o polígono no sentido horário:
        # 1. Traseira: (ox, y_tras) até (ox + L, y_tras)
        # 2. Lateral direita traseira: (ox + L, y_tras) até (ox + L, oy)
        # 3. Transição ou mesa:
        # Se o tampo cobre todo o balcão (L x P):
        poly_tampo: list[tuple[float, float]] = []
        poly_tampo.append((ox, y_tras))
        poly_tampo.append((ox + L, y_tras))
        poly_tampo.append((ox + L, oy))
        if x_mesa_dir < ox + L:
            poly_tampo.append((x_mesa_dir, oy))

        # Canto frontal direito arredondado da mesa (em y_frente)
        # De (x_mesa_dir, y_frente + raio) até (x_mesa_dir - raio, y_frente)
        steps = 8
        cx_dir = x_mesa_dir - raio
        cy_frente = y_frente + raio
        poly_tampo.append((x_mesa_dir, cy_frente))
        for s in range(1, steps + 1):
            ang = (s / steps) * (math.pi / 2.0)
            poly_tampo.append((cx_dir + raio * math.cos(ang), cy_frente - raio * math.sin(ang)))

        # Canto frontal esquerdo arredondado da mesa (em y_frente)
        # De (x_mesa_esq + raio, y_frente) até (x_mesa_esq, y_frente + raio)
        cx_esq = x_mesa_esq + raio
        for s in range(1, steps + 1):
            ang = (math.pi / 2.0) + (s / steps) * (math.pi / 2.0)
            poly_tampo.append((cx_esq + raio * math.cos(ang), cy_frente - raio * math.sin(ang)))

        poly_tampo.append((x_mesa_esq, cy_frente))
        if x_mesa_esq > ox:
            poly_tampo.append((x_mesa_esq, oy))
            poly_tampo.append((ox, oy))

        from ..builders.mesh_utils import create_polygon_board_group
        g_tampo = create_polygon_board_group(
            name="Bancada Peninsula - Tampo Mesa",
            polygon_xy=poly_tampo,
            z0=oz + H,
            espessura=Et,
            material=material_tampo,
            color=cor_tampo,
        )
        groups.append(g_tampo)

        # 3. Pé Tubular de Apoio Metálico
        x_pe = (x_mesa_esq + x_mesa_dir) / 2.0
        y_pe = y_frente + raio + 0.08
        alt_pe = oz + H

        g_pe = create_cylinder_group(
            name="Bancada Peninsula - Pé Tubular Metálico",
            center_xy=(x_pe, y_pe),
            radius=0.025,
            z0=oz,
            height=alt_pe,
            material="Metal Cromado",
            color=(0.85, 0.85, 0.88),
        )
        groups.append(g_pe)

        return groups


# Aliases
BaseWallCabinetBuilder = BalcaoAereoBuilder

