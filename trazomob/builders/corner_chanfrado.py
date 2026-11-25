# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import math
from typing import Any

from PySide6.QtGui import QVector3D

from core.group import Group

from ..builders.chapa_spec import ModuloMaterialContext, PapelChapa
from ..builders.fronts import FrentesKitBuilder
from ..builders.mesh_utils import create_polygon_board_group
from ..builders.parts import _chapa, _chapa_frente


class CornerChanfradoMixin:
    """Builders de cantos chanfrados e canto gaveteiro L extraídos de CantoEspecialBuilder."""

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

        from ..builders.cabinet_transform import CabinetTransformMixin
        from ..builders.mesh_utils import create_polygon_board_group

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

        from PySide6.QtGui import QMatrix4x4

        from ..builders.cabinet_caixa import CaixaMixin
        from ..builders.cabinet_transform import _rotate_group_tree

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

        from PySide6.QtGui import QMatrix4x4

        from ..builders.cabinet_caixa import CaixaMixin
        from ..builders.cabinet_transform import _rotate_group_tree

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


