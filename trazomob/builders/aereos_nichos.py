# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from typing import Any

from core.group import Group

from ..builders.chapa_builder import build_chapa
from ..builders.chapa_spec import ChapaSpec, ModuloMaterialContext, PapelChapa
from ..builders.fronts import FrentesKitBuilder
from ..builders.mesh_utils import (
    create_board_group,
)


class AereosNichosMixin:
    """Builders de módulos aéreos e nichos extraídos de BalcaoAereoBuilder."""

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
                    make_shelf_side_holes,
                    make_vertical_divider_joint_holes,
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

