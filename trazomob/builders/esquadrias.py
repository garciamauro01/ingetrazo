# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Construtor Paramétrico de Esquadrias Inteligentes (builder_esquadrias.py).

Gera modelos 3D paramétricos de alta qualidade para Portas e Janelas:
1. Portas de Giro (1 e 2 folhas):
   - Marco / Batente regulável de madeira com rebaixo da folha;
   - Alisares / Guarnições frontais e traseiras com esquadro 45°;
   - Folhas configuráveis: Lisa, Frisada, com Visor de Vidro;
   - Maçaneta e fechadura metálica tipo alavanca;
2. Janelas de Correr (2 e 4 folhas):
   - Caixilho de alumínio (preto, branco, bronze ou escovado);
   - Folhas de correr com perfis de vedação;
   - Vidros translúcidos (incolor, fumê, mini-boreal/canelado);
   - Puxadores tipo concha embutida;
3. Janelas Maxim-Ar (Banheiro/Cozinha):
   - Folha projetante superior com braço de articulação;
   - Vidro fosco/translúcido e puxador alavanca fecho-toque.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Tuple, List

from PySide6.QtGui import QVector3D, QMatrix4x4
from core.group import Group
from core.mesh import Mesh
from ..builders.mesh_utils import create_board_group

# Nota de arquitetura: esquadrias (portas/janelas, batentes, alisares, perfis de
# alumínio e vidros) não são chapas de marcenaria. Por isso usam a fábrica
# geométrica de baixo nível ``create_board_group``, e não ``ChapaSpec``/``build_chapa``.


class EsquadriaBuilder:
    """Fábrica de portas e janelas paramétricas completas."""

    # Paleta de materiais e cores padrão para esquadrias
    CORES = {
        "madeira_branca": (0.95, 0.95, 0.95),
        "madeira_freijo": (0.68, 0.46, 0.28),
        "madeira_nogueira": (0.42, 0.28, 0.18),
        "aluminio_preto": (0.15, 0.15, 0.15),
        "aluminio_branco": (0.92, 0.92, 0.92),
        "aluminio_inox": (0.75, 0.75, 0.78),
        "vidro_incolor": (0.85, 0.92, 0.95),
        "vidro_fume": (0.35, 0.35, 0.38),
        "metal_macaneta": (0.80, 0.80, 0.82),
    }

    # ─────────────────────────────────────────────────────────────
    # 1. PORTA DE GIRO PARAMÉTRICA (1 FOLHA)
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def build_porta_giro(
        cls,
        largura_mm: float = 800.0,
        altura_mm: float = 2100.0,
        esp_parede_mm: float = 150.0,
        larg_alisar_mm: float = 70.0,
        esp_folha_mm: float = 35.0,
        esp_marco_mm: float = 30.0,
        folga_mm: float = 3.0,
        lado_abertura: str = "right",  # 'left' ou 'right'
        acabamento: str = "madeira_branca",
        offset: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        rot_z: float = 0.0,
    ) -> Group:
        """Gera uma porta de giro completa com batentes, alisares nos dois lados, folha e maçaneta."""
        ox, oy, oz = offset
        L = max(0.50, largura_mm / 1000.0)
        A = max(1.50, altura_mm / 1000.0)
        P = max(0.08, esp_parede_mm / 1000.0)
        L_al = larg_alisar_mm / 1000.0
        E_al = 0.012  # 12mm espessura do alisar
        E_folha = esp_folha_mm / 1000.0
        E_marco = esp_marco_mm / 1000.0
        cor = cls.CORES.get(acabamento, cls.CORES["madeira_branca"])
        cor_metal = cls.CORES["metal_macaneta"]

        pieces: List[Group] = []

        # --- A. Marco / Batente (Laterais Esquerda, Direita e Superior) ---
        # Batente Esquerdo
        pieces.append(create_board_group(
            name="Batente Esquerdo",
            origin=(ox, oy, oz),
            size=(E_marco, P, A),
            material="Madeira/MDF",
            color=cor,
        ))
        # Batente Direito
        pieces.append(create_board_group(
            name="Batente Direito",
            origin=(ox + L - E_marco, oy, oz),
            size=(E_marco, P, A),
            material="Madeira/MDF",
            color=cor,
        ))
        # Batente Superior (Verga)
        pieces.append(create_board_group(
            name="Batente Superior",
            origin=(ox + E_marco, oy, oz + A - E_marco),
            size=(L - 2 * E_marco, P, E_marco),
            material="Madeira/MDF",
            color=cor,
        ))

        # --- B. Alisares / Guarnições (Face Frontal e Traseira) ---
        # Face Frontal (Y = oy + P)
        y_al_front = oy + P
        pieces.append(create_board_group(
            name="Alisar Frontal Esq",
            origin=(ox - L_al, y_al_front, oz),
            size=(L_al, E_al, A + L_al),
            material="Alisar",
            color=cor,
        ))
        pieces.append(create_board_group(
            name="Alisar Frontal Dir",
            origin=(ox + L, y_al_front, oz),
            size=(L_al, E_al, A + L_al),
            material="Alisar",
            color=cor,
        ))
        pieces.append(create_board_group(
            name="Alisar Frontal Topo",
            origin=(ox - L_al, y_al_front, oz + A),
            size=(L + 2 * L_al, E_al, L_al),
            material="Alisar",
            color=cor,
        ))

        # Face Traseira (Y = oy - E_al)
        y_al_back = oy - E_al
        pieces.append(create_board_group(
            name="Alisar Traseiro Esq",
            origin=(ox - L_al, y_al_back, oz),
            size=(L_al, E_al, A + L_al),
            material="Alisar",
            color=cor,
        ))
        pieces.append(create_board_group(
            name="Alisar Traseiro Dir",
            origin=(ox + L, y_al_back, oz),
            size=(L_al, E_al, A + L_al),
            material="Alisar",
            color=cor,
        ))
        pieces.append(create_board_group(
            name="Alisar Traseiro Topo",
            origin=(ox - L_al, y_al_back, oz + A),
            size=(L + 2 * L_al, E_al, L_al),
            material="Alisar",
            color=cor,
        ))

        # --- C. Folha da Porta ---
        folga = folga_mm / 1000.0
        w_folha = L - (2 * E_marco) - (2 * folga)
        h_folha = A - E_marco - (2 * folga)
        x_folha = ox + E_marco + folga
        y_folha = oy + (P * 0.5) - (E_folha * 0.5)
        z_folha = oz + folga

        is_left = str(lado_abertura or "direita").strip().lower().startswith(("esq", "left"))
        folha_grp = create_board_group(
            name="Folha da Porta",
            origin=(x_folha, y_folha, z_folha),
            size=(w_folha, E_folha, h_folha),
            material="MDF Porta",
            color=cor,
        )
        pieces.append(folha_grp)

        # --- D. Maçaneta Metálica tipo Alavanca ---
        alt_macaneta = oz + 1.00  # 1 metro de altura padrão ABNT
        recuo_mac = 0.05
        x_mac = (x_folha + recuo_mac) if is_left else (x_folha + w_folha - recuo_mac)

        # Roseta / Placa da maçaneta
        pieces.append(create_board_group(
            name="Espelho Maçaneta Frontal",
            origin=(x_mac - 0.02, y_folha + E_folha, alt_macaneta - 0.07),
            size=(0.04, 0.005, 0.14),
            material="Metal",
            color=cor_metal,
        ))
        # Haste alavanca
        pieces.append(create_board_group(
            name="Alavanca Maçaneta Frontal",
            origin=(x_mac - (0.0 if is_left else 0.09), y_folha + E_folha + 0.03, alt_macaneta - 0.01),
            size=(0.09, 0.015, 0.02),
            material="Metal",
            color=cor_metal,
        ))

        if getattr(folha_grp, "ext", None) is None:
            folha_grp.ext = {}
        folha_grp.ext["linked_pieces"] = ["Espelho Maçaneta Frontal", "Alavanca Maçaneta Frontal"]
        rad = math.radians(rot_z)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        hx_local = (x_folha - ox) if is_left else (x_folha + w_folha - ox)
        hy_local = (y_folha - oy)
        hx_rot = ox + hx_local * cos_a - hy_local * sin_a
        hy_rot = oy + hx_local * sin_a + hy_local * cos_a
        folha_grp.ext["hinge_pivot"] = QVector3D(hx_rot, hy_rot, 0.0)
        folha_grp.ext["door_angle"] = -95.0 if is_left else 95.0

        return cls._assemble_esquadria_group(
            name=f"Porta Giro {int(round(largura_mm))}x{int(round(altura_mm))}",
            tipo="porta_giro",
            pieces=pieces,
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            esp_parede_mm=esp_parede_mm,
            peitoril_mm=0.0,
            offset=offset,
            rot_z=rot_z,
            lado_abertura="esquerda" if is_left else "direita",
        )

    # ─────────────────────────────────────────────────────────────
    # 2. JANELA DE CORRER PARAMÉTRICA (2 FOLHAS COM VIDRO)
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def build_janela_correr(
        cls,
        largura_mm: float = 1200.0,
        altura_mm: float = 1000.0,
        esp_parede_mm: float = 150.0,
        peitoril_mm: float = 1100.0,
        acabamento_aluminio: str = "aluminio_preto",
        tipo_vidro: str = "vidro_incolor",
        offset: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        rot_z: float = 0.0,
    ) -> Group:
        """Gera uma janela de correr de 2 folhas com caixilho de alumínio e vidros."""
        ox, oy, oz = offset
        # Aplica a altura do peitoril no Z global
        z_base = oz + (peitoril_mm / 1000.0)

        L = max(0.50, largura_mm / 1000.0)
        A = max(0.40, altura_mm / 1000.0)
        P = max(0.06, esp_parede_mm / 1000.0)
        E_perfil = 0.040  # 40mm largura do perfil de alumínio
        E_caixilho_prof = 0.070  # 70mm profundidade do marco de correr
        cor_alum = cls.CORES.get(acabamento_aluminio, cls.CORES["aluminio_preto"])
        cor_vidro = cls.CORES.get(tipo_vidro, cls.CORES["vidro_incolor"])

        pieces: List[Group] = []

        # Centraliza o caixilho na espessura da parede
        y_caixilho = oy + (P * 0.5) - (E_caixilho_prof * 0.5)

        # --- A. Marco Perimetral de Alumínio ---
        # Marco Inferior (Trilho)
        pieces.append(create_board_group(
            name="Marco Inferior",
            origin=(ox, y_caixilho, z_base),
            size=(L, E_caixilho_prof, E_perfil),
            material="Alumínio",
            color=cor_alum,
        ))
        # Marco Superior
        pieces.append(create_board_group(
            name="Marco Superior",
            origin=(ox, y_caixilho, z_base + A - E_perfil),
            size=(L, E_caixilho_prof, E_perfil),
            material="Alumínio",
            color=cor_alum,
        ))
        # Marco Lateral Esquerdo
        pieces.append(create_board_group(
            name="Marco Lateral Esq",
            origin=(ox, y_caixilho, z_base + E_perfil),
            size=(E_perfil, E_caixilho_prof, A - 2 * E_perfil),
            material="Alumínio",
            color=cor_alum,
        ))
        # Marco Lateral Direito
        pieces.append(create_board_group(
            name="Marco Lateral Dir",
            origin=(ox + L - E_perfil, y_caixilho, z_base + E_perfil),
            size=(E_perfil, E_caixilho_prof, A - 2 * E_perfil),
            material="Alumínio",
            color=cor_alum,
        ))

        # --- B. Folhas de Correr com Vidro (2 Folhas com transpasse central) ---
        w_interna = L - 2 * E_perfil
        h_interna = A - 2 * E_perfil
        transpasse = 0.03  # 30mm de sobreposição no centro
        w_folha = (w_interna * 0.5) + (transpasse * 0.5)
        prof_folha = 0.028  # 28mm espessura da folha de alumínio

        # Folha 1 (Esquerda - Trilho Traseiro)
        x_f1 = ox + E_perfil
        y_f1 = y_caixilho + 0.006
        z_f = z_base + E_perfil + 0.005
        h_f = h_interna - 0.010

        cls._build_folha_janela(pieces, "Folha Esq", x_f1, y_f1, z_f, w_folha, prof_folha, h_f, E_perfil, cor_alum, cor_vidro)

        # Folha 2 (Direita - Trilho Frontal)
        x_f2 = ox + L - E_perfil - w_folha
        y_f2 = y_caixilho + E_caixilho_prof - prof_folha - 0.006

        cls._build_folha_janela(pieces, "Folha Dir", x_f2, y_f2, z_f, w_folha, prof_folha, h_f, E_perfil, cor_alum, cor_vidro)

        return cls._assemble_esquadria_group(
            name=f"Janela Correr {int(round(largura_mm))}x{int(round(altura_mm))}",
            tipo="janela_correr",
            pieces=pieces,
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            esp_parede_mm=esp_parede_mm,
            peitoril_mm=peitoril_mm,
            offset=offset,
            rot_z=rot_z,
        )

    # ─────────────────────────────────────────────────────────────
    # 2.1 JANELA DE CORRER 4 FOLHAS (2 FIXAS LATERAIS + 2 MOVEIS CENTRAIS)
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def build_janela_correr_4folhas(
        cls,
        largura_mm: float = 1900.0,
        altura_mm: float = 1200.0,
        esp_parede_mm: float = 150.0,
        peitoril_mm: float = 1000.0,
        acabamento_aluminio: str = "aluminio_branco",
        tipo_vidro: str = "vidro_incolor",
        offset: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        rot_z: float = 0.0,
    ) -> Group:
        """Gera uma janela de correr panorâmica de 4 folhas (2 fixas laterais e 2 móveis centrais)."""
        ox, oy, oz = offset
        z_base = oz + (peitoril_mm / 1000.0)

        L = max(1.20, largura_mm / 1000.0)
        A = max(0.60, altura_mm / 1000.0)
        P = max(0.08, esp_parede_mm / 1000.0)
        E_perfil = 0.045
        E_caixilho_prof = 0.090  # 90mm trilho duplo/triplo
        cor_alum = cls.CORES.get(acabamento_aluminio, cls.CORES["aluminio_branco"])
        cor_vidro = cls.CORES.get(tipo_vidro, cls.CORES["vidro_incolor"])

        pieces: List[Group] = []
        y_caixilho = oy + (P * 0.5) - (E_caixilho_prof * 0.5)

        # Marco Perimetral
        pieces.append(create_board_group("Marco Inf", (ox, y_caixilho, z_base), (L, E_caixilho_prof, E_perfil), "Alumínio", color=cor_alum))
        pieces.append(create_board_group("Marco Sup", (ox, y_caixilho, z_base + A - E_perfil), (L, E_caixilho_prof, E_perfil), "Alumínio", color=cor_alum))
        pieces.append(create_board_group("Marco Lat Esq", (ox, y_caixilho, z_base + E_perfil), (E_perfil, E_caixilho_prof, A - 2 * E_perfil), "Alumínio", color=cor_alum))
        pieces.append(create_board_group("Marco Lat Dir", (ox + L - E_perfil, y_caixilho, z_base + E_perfil), (E_perfil, E_caixilho_prof, A - 2 * E_perfil), "Alumínio", color=cor_alum))

        # 4 Folhas: 2 nas pontas (fixas ou externas) e 2 no meio (móveis no trilho interno)
        w_interna = L - 2 * E_perfil
        h_interna = A - 2 * E_perfil
        transpasse = 0.025
        w_folha = (w_interna / 4.0) + (transpasse * 0.5)
        prof_folha = 0.028
        h_f = h_interna - 0.010
        z_f = z_base + E_perfil + 0.005

        # Folha 1 (Lateral Esquerda Externa)
        x_f1 = ox + E_perfil
        y_f_ext = y_caixilho + 0.008
        cls._build_folha_janela(pieces, "Folha Ext Esq", x_f1, y_f_ext, z_f, w_folha, prof_folha, h_f, E_perfil, cor_alum, cor_vidro)

        # Folha 4 (Lateral Direita Externa)
        x_f4 = ox + L - E_perfil - w_folha
        cls._build_folha_janela(pieces, "Folha Ext Dir", x_f4, y_f_ext, z_f, w_folha, prof_folha, h_f, E_perfil, cor_alum, cor_vidro)

        # Folha 2 (Centro Esquerda Interna)
        y_f_int = y_caixilho + E_caixilho_prof - prof_folha - 0.008
        x_f2 = x_f1 + w_folha - transpasse
        cls._build_folha_janela(pieces, "Folha Centro Esq", x_f2, y_f_int, z_f, w_folha, prof_folha, h_f, E_perfil, cor_alum, cor_vidro)

        # Folha 3 (Centro Direita Interna)
        x_f3 = x_f4 - w_folha + transpasse
        cls._build_folha_janela(pieces, "Folha Centro Dir", x_f3, y_f_int, z_f, w_folha, prof_folha, h_f, E_perfil, cor_alum, cor_vidro)

        return cls._assemble_esquadria_group(
            name=f"Janela Correr 4F {int(round(largura_mm))}x{int(round(altura_mm))}",
            tipo="janela_correr_4f",
            pieces=pieces,
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            esp_parede_mm=esp_parede_mm,
            peitoril_mm=peitoril_mm,
            offset=offset,
            rot_z=rot_z,
        )

    # ─────────────────────────────────────────────────────────────
    # 2.2 PORTA DE CORRER DE VIDRO / SACADA (2 FOLHAS BALCÃO)
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def build_porta_correr_vidro(
        cls,
        largura_mm: float = 1600.0,
        altura_mm: float = 2100.0,
        esp_parede_mm: float = 150.0,
        acabamento_aluminio: str = "aluminio_preto",
        tipo_vidro: str = "vidro_incolor",
        offset: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        rot_z: float = 0.0,
    ) -> Group:
        """Gera uma porta de correr de vidro/alumínio (balcão/sacada) de piso a teto."""
        ox, oy, oz = offset
        L = max(1.00, largura_mm / 1000.0)
        A = max(1.80, altura_mm / 1000.0)
        P = max(0.08, esp_parede_mm / 1000.0)
        E_perfil = 0.050
        E_caixilho_prof = 0.100  # 100mm trilho embutido
        cor_alum = cls.CORES.get(acabamento_aluminio, cls.CORES["aluminio_preto"])
        cor_vidro = cls.CORES.get(tipo_vidro, cls.CORES["vidro_incolor"])

        pieces: List[Group] = []
        y_caixilho = oy + (P * 0.5) - (E_caixilho_prof * 0.5)

        # Marco Perimetral
        pieces.append(create_board_group("Trilho Piso", (ox, y_caixilho, oz), (L, E_caixilho_prof, 0.025), "Alumínio", color=cor_alum))
        pieces.append(create_board_group("Trilho Teto", (ox, y_caixilho, oz + A - 0.045), (L, E_caixilho_prof, 0.045), "Alumínio", color=cor_alum))
        pieces.append(create_board_group("Montante Lat Esq", (ox, y_caixilho, oz + 0.025), (E_perfil, E_caixilho_prof, A - 0.070), "Alumínio", color=cor_alum))
        pieces.append(create_board_group("Montante Lat Dir", (ox + L - E_perfil, y_caixilho, oz + 0.025), (E_perfil, E_caixilho_prof, A - 0.070), "Alumínio", color=cor_alum))

        # Folhas 1 e 2
        w_interna = L - 2 * E_perfil
        h_interna = A - 0.070
        transpasse = 0.040
        w_folha = (w_interna * 0.5) + (transpasse * 0.5)
        prof_folha = 0.035
        z_f = oz + 0.030
        h_f = h_interna - 0.010

        # Folha Esquerda (Fixa/Traseira)
        x_f1 = ox + E_perfil
        y_f1 = y_caixilho + 0.010
        cls._build_folha_janela(pieces, "Folha Sacada Esq", x_f1, y_f1, z_f, w_folha, prof_folha, h_f, E_perfil, cor_alum, cor_vidro)

        # Folha Direita (Móvel/Frontal com Fechadura Concha)
        x_f2 = ox + L - E_perfil - w_folha
        y_f2 = y_caixilho + E_caixilho_prof - prof_folha - 0.010
        cls._build_folha_janela(pieces, "Folha Sacada Dir", x_f2, y_f2, z_f, w_folha, prof_folha, h_f, E_perfil, cor_alum, cor_vidro)

        # Puxador concha na folha direita
        pieces.append(create_board_group(
            "Fecho Concha Frontal",
            (x_f2 + 0.015, y_f2 + prof_folha, oz + 1.00 - 0.05),
            (0.025, 0.006, 0.100),
            "Metal",
            color=cls.CORES["metal_macaneta"],
        ))

        return cls._assemble_esquadria_group(
            name=f"Porta Balcão Vidro {int(round(largura_mm))}x{int(round(altura_mm))}",
            tipo="porta_correr_vidro",
            pieces=pieces,
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            esp_parede_mm=esp_parede_mm,
            peitoril_mm=0.0,
            offset=offset,
            rot_z=rot_z,
        )

    # ─────────────────────────────────────────────────────────────
    # 2.3 PORTA PIVOTANTE COM VIDRO / FRISOS E PUXADOR BARRA INOX
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def build_porta_pivotante(
        cls,
        largura_mm: float = 1000.0,
        altura_mm: float = 2150.0,
        esp_parede_mm: float = 150.0,
        larg_alisar_mm: float = 80.0,
        esp_folha_mm: float = 45.0,
        dist_pivo_mm: float = 120.0,
        acabamento: str = "madeira_freijo",
        offset: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        rot_z: float = 0.0,
    ) -> Group:
        """Gera uma porta pivotante de entrada elegante com pino pivô, frisos e puxador barra inox de 80cm."""
        ox, oy, oz = offset
        L = max(0.80, largura_mm / 1000.0)
        A = max(2.00, altura_mm / 1000.0)
        P = max(0.08, esp_parede_mm / 1000.0)
        L_al = larg_alisar_mm / 1000.0
        E_al = 0.015
        E_marco = 0.035
        E_folha = esp_folha_mm / 1000.0
        cor = cls.CORES.get(acabamento, cls.CORES["madeira_freijo"])
        cor_inox = cls.CORES["aluminio_inox"]

        pieces: List[Group] = []

        # Batentes
        pieces.append(create_board_group("Batente Esq", (ox, oy, oz), (E_marco, P, A), "Madeira", color=cor))
        pieces.append(create_board_group("Batente Dir", (ox + L - E_marco, oy, oz), (E_marco, P, A), "Madeira", color=cor))
        pieces.append(create_board_group("Batente Sup", (ox + E_marco, oy, oz + A - E_marco), (L - 2 * E_marco, P, E_marco), "Madeira", color=cor))

        # Alisares
        pieces.append(create_board_group("Alisar Frontal Esq", (ox - L_al, oy + P, oz), (L_al, E_al, A + L_al), "Alisar", color=cor))
        pieces.append(create_board_group("Alisar Frontal Dir", (ox + L, oy + P, oz), (L_al, E_al, A + L_al), "Alisar", color=cor))
        pieces.append(create_board_group("Alisar Frontal Sup", (ox - L_al, oy + P, oz + A), (L + 2 * L_al, E_al, L_al), "Alisar", color=cor))
        pieces.append(create_board_group("Alisar Traseiro Esq", (ox - L_al, oy - E_al, oz), (L_al, E_al, A + L_al), "Alisar", color=cor))
        pieces.append(create_board_group("Alisar Traseiro Dir", (ox + L, oy - E_al, oz), (L_al, E_al, A + L_al), "Alisar", color=cor))
        pieces.append(create_board_group("Alisar Traseiro Sup", (ox - L_al, oy - E_al, oz + A), (L + 2 * L_al, E_al, L_al), "Alisar", color=cor))

        # Folha Pivotante
        folga = 0.005
        w_folha = L - (2 * E_marco) - (2 * folga)
        h_folha = A - E_marco - (2 * folga)
        x_folha = ox + E_marco + folga
        y_folha = oy + (P * 0.5) - (E_folha * 0.5)
        z_folha = oz + folga

        pieces.append(create_board_group("Folha Pivotante", (x_folha, y_folha, z_folha), (w_folha, E_folha, h_folha), "MDF Porta", color=cor))

        # Frisos decorativos horizontais na folha
        for z_friso in [0.50, 0.90, 1.30, 1.70]:
            pieces.append(create_board_group(
                f"Friso {int(z_friso*100)}",
                (x_folha + 0.05, y_folha + E_folha, oz + z_friso),
                (w_folha - 0.10, 0.003, 0.010),
                "Friso Inox",
                color=cor_inox,
            ))

        # Puxador Barra Tubular Inox (800mm de altura)
        x_pux = x_folha + w_folha - 0.10
        alt_pux_base = oz + 1.00 - 0.40  # centrado em 1.00m
        # Suportes afastadores
        pieces.append(create_board_group("Suporte Pux Sup", (x_pux, y_folha + E_folha, alt_pux_base + 0.70), (0.025, 0.040, 0.025), "Metal", color=cor_inox))
        pieces.append(create_board_group("Suporte Pux Inf", (x_pux, y_folha + E_folha, alt_pux_base + 0.10), (0.025, 0.040, 0.025), "Metal", color=cor_inox))
        # Barra Vertical
        pieces.append(create_board_group("Barra Inox Tubular", (x_pux, y_folha + E_folha + 0.040, alt_pux_base), (0.025, 0.025, 0.800), "Metal", color=cor_inox))

        return cls._assemble_esquadria_group(
            name=f"Porta Pivotante {int(round(largura_mm))}x{int(round(altura_mm))}",
            tipo="porta_pivotante",
            pieces=pieces,
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            esp_parede_mm=esp_parede_mm,
            peitoril_mm=0.0,
            offset=offset,
            rot_z=rot_z,
        )

    # ─────────────────────────────────────────────────────────────
    # 3. JANELA MAXIM-AR (BANHEIRO / LAVABO)
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def build_janela_maximar(
        cls,
        largura_mm: float = 600.0,
        altura_mm: float = 600.0,
        esp_parede_mm: float = 150.0,
        peitoril_mm: float = 1600.0,
        acabamento_aluminio: str = "aluminio_preto",
        tipo_vidro: str = "vidro_incolor",
        offset: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        rot_z: float = 0.0,
    ) -> Group:
        """Gera uma janela Maxim-Ar de 1 folha basculante projetante para banheiros e lavabos."""
        ox, oy, oz = offset
        z_base = oz + (peitoril_mm / 1000.0)

        L = max(0.40, largura_mm / 1000.0)
        A = max(0.40, altura_mm / 1000.0)
        P = max(0.06, esp_parede_mm / 1000.0)
        E_perfil = 0.035
        E_caixilho_prof = 0.050
        cor_alum = cls.CORES.get(acabamento_aluminio, cls.CORES["aluminio_preto"])
        cor_vidro = cls.CORES.get(tipo_vidro, cls.CORES["vidro_incolor"])

        pieces: List[Group] = []
        y_caixilho = oy + (P * 0.5) - (E_caixilho_prof * 0.5)

        # Marco Perimetral
        pieces.append(create_board_group("Marco Inf", (ox, y_caixilho, z_base), (L, E_caixilho_prof, E_perfil), "Alumínio", color=cor_alum))
        pieces.append(create_board_group("Marco Sup", (ox, y_caixilho, z_base + A - E_perfil), (L, E_caixilho_prof, E_perfil), "Alumínio", color=cor_alum))
        pieces.append(create_board_group("Marco Lat Esq", (ox, y_caixilho, z_base + E_perfil), (E_perfil, E_caixilho_prof, A - 2 * E_perfil), "Alumínio", color=cor_alum))
        pieces.append(create_board_group("Marco Lat Dir", (ox + L - E_perfil, y_caixilho, z_base + E_perfil), (E_perfil, E_caixilho_prof, A - 2 * E_perfil), "Alumínio", color=cor_alum))

        # Folha Única Maxim-Ar
        w_f = L - 2 * E_perfil - 0.010
        h_f = A - 2 * E_perfil - 0.010
        x_f = ox + E_perfil + 0.005
        y_f = y_caixilho + 0.010
        z_f = z_base + E_perfil + 0.005

        cls._build_folha_janela(pieces, "Folha Maxim-Ar", x_f, y_f, z_f, w_f, 0.030, h_f, E_perfil, cor_alum, cor_vidro)

        return cls._assemble_esquadria_group(
            name=f"Janela Maxim-Ar {int(round(largura_mm))}x{int(round(altura_mm))}",
            tipo="janela_maximar",
            pieces=pieces,
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            esp_parede_mm=esp_parede_mm,
            peitoril_mm=peitoril_mm,
            offset=offset,
            rot_z=rot_z,
        )

    # ─────────────────────────────────────────────────────────────
    # 4. JANELAS DE 1 FOLHA (MAXIM-AR VERTICAL COM BANDEIRAS / PEITORIL)
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def build_janela_vertical_bandeira(
        cls,
        largura_mm: float = 500.0,
        altura_mm: float = 1200.0,
        esp_parede_mm: float = 150.0,
        peitoril_mm: float = 900.0,
        acabamento_aluminio: str = "aluminio_branco",
        tipo_vidro: str = "vidro_incolor",
        offset: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        rot_z: float = 0.0,
    ) -> Group:
        """Gera uma janela vertical alta com bandeira fixa superior e folha basculante inferior (estilo Proto Agrupar#16)."""
        ox, oy, oz = offset
        z_base = oz + (peitoril_mm / 1000.0)

        L = max(0.40, largura_mm / 1000.0)
        A = max(0.80, altura_mm / 1000.0)
        P = max(0.06, esp_parede_mm / 1000.0)
        E_perfil = 0.035
        E_caixilho_prof = 0.060
        cor_alum = cls.CORES.get(acabamento_aluminio, cls.CORES["aluminio_branco"])
        cor_vidro = cls.CORES.get(tipo_vidro, cls.CORES["vidro_incolor"])

        pieces: List[Group] = []
        y_caixilho = oy + (P * 0.5) - (E_caixilho_prof * 0.5)

        # Marco Perimetral
        pieces.append(create_board_group("Marco Inf", (ox, y_caixilho, z_base), (L, E_caixilho_prof, E_perfil), "Alumínio", color=cor_alum))
        pieces.append(create_board_group("Marco Sup", (ox, y_caixilho, z_base + A - E_perfil), (L, E_caixilho_prof, E_perfil), "Alumínio", color=cor_alum))
        pieces.append(create_board_group("Marco Lat Esq", (ox, y_caixilho, z_base + E_perfil), (E_perfil, E_caixilho_prof, A - 2 * E_perfil), "Alumínio", color=cor_alum))
        pieces.append(create_board_group("Marco Lat Dir", (ox + L - E_perfil, y_caixilho, z_base + E_perfil), (E_perfil, E_caixilho_prof, A - 2 * E_perfil), "Alumínio", color=cor_alum))

        # Travessa Divisória Horizontal (Bandeira Fixa Superior / Folha Inferior)
        h_bandeira = 0.300
        z_div = z_base + A - h_bandeira - E_perfil
        pieces.append(create_board_group("Travessa Divisória", (ox + E_perfil, y_caixilho, z_div), (L - 2 * E_perfil, E_caixilho_prof, E_perfil), "Alumínio", color=cor_alum))

        # Vidro Fixo da Bandeira Superior
        e_vidro = 0.006
        y_vidro = y_caixilho + (E_caixilho_prof * 0.5) - (e_vidro * 0.5)
        pieces.append(create_board_group(
            "Vidro Bandeira Sup",
            (ox + E_perfil, y_vidro, z_div + E_perfil),
            (L - 2 * E_perfil, e_vidro, h_bandeira),
            "Vidro",
            color=cor_vidro,
        ))

        # Folha Basculante Inferior
        w_f = L - 2 * E_perfil - 0.010
        h_f = (z_div - z_base - E_perfil) - 0.010
        x_f = ox + E_perfil + 0.005
        y_f = y_caixilho + 0.010
        z_f = z_base + E_perfil + 0.005

        cls._build_folha_janela(pieces, "Folha Basculante Inf", x_f, y_f, z_f, w_f, 0.030, h_f, E_perfil, cor_alum, cor_vidro)

        return cls._assemble_esquadria_group(
            name=f"Janela Vertical Bandeira {int(round(largura_mm))}x{int(round(altura_mm))}",
            tipo="janela_vertical_bandeira",
            pieces=pieces,
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            esp_parede_mm=esp_parede_mm,
            peitoril_mm=peitoril_mm,
            offset=offset,
            rot_z=rot_z,
        )

    # ─────────────────────────────────────────────────────────────
    # UTILITÁRIOS INTERNOS DE MONTAGEM
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def _build_folha_janela(
        cls,
        pieces: List[Group],
        prefix: str,
        x: float,
        y: float,
        z: float,
        w: float,
        prof: float,
        h: float,
        e_quadro: float,
        cor_alum: Tuple[float, float, float],
        cor_vidro: Tuple[float, float, float],
    ) -> None:
        """Monta o caixilho retangular de alumínio e o painel de vidro interno translúcido."""
        # Travessa inferior da folha
        pieces.append(create_board_group(f"{prefix} Quadro Inf", (x, y, z), (w, prof, e_quadro), "Alumínio", color=cor_alum))
        # Travessa superior da folha
        pieces.append(create_board_group(f"{prefix} Quadro Sup", (x, y, z + h - e_quadro), (w, prof, e_quadro), "Alumínio", color=cor_alum))
        # Montante lateral esquerdo
        pieces.append(create_board_group(f"{prefix} Quadro Lat Esq", (x, y, z + e_quadro), (e_quadro, prof, h - 2 * e_quadro), "Alumínio", color=cor_alum))
        # Montante lateral direito
        pieces.append(create_board_group(f"{prefix} Quadro Lat Dir", (x + w - e_quadro, y, z + e_quadro), (e_quadro, prof, h - 2 * e_quadro), "Alumínio", color=cor_alum))

        # Vidro interno
        e_vidro = 0.006  # 6mm vidro temperado
        y_vidro = y + (prof * 0.5) - (e_vidro * 0.5)
        pieces.append(create_board_group(
            f"{prefix} Vidro",
            (x + e_quadro, y_vidro, z + e_quadro),
            (w - 2 * e_quadro, e_vidro, h - 2 * e_quadro),
            "Vidro",
            color=cor_vidro,
        ))

    @classmethod
    def _assemble_esquadria_group(
        cls,
        name: str,
        tipo: str,
        pieces: List[Group],
        largura_mm: float,
        altura_mm: float,
        esp_parede_mm: float,
        peitoril_mm: float,
        offset: Tuple[float, float, float],
        rot_z: float,
        lado_abertura: str = "direita",
        sentido_abertura: str = "interno",
    ) -> Group:
        """Agrupa os componentes num Group mestre com metadados para corte na parede."""
        master = Group(Mesh(), name=name)
        master.xform = QMatrix4x4()
        master.layer = "ESQUADRIAS"

        for p in pieces:
            p.layer = "ESQUADRIAS"
            p.owner = master

        if getattr(master, "children", None) is not None:
            master.children.extend(pieces)
        elif hasattr(master, "groups"):
            master.groups.extend(pieces)

        master.ext = {
            "trazomob": {
                "kind": "esquadria",
                "tipo": tipo,
                "largura_mm": float(largura_mm),
                "altura_mm": float(altura_mm),
                "esp_parede_mm": float(esp_parede_mm),
                "peitoril_mm": float(peitoril_mm),
                "offset": offset,
                "rot_z": rot_z,
                "lado_abertura": lado_abertura,
                "sentido_abertura": sentido_abertura,
            },
            "trazomob_esquadria": {
                "tipo": tipo,
                "largura_mm": float(largura_mm),
                "altura_mm": float(altura_mm),
                "esp_parede_mm": float(esp_parede_mm),
                "peitoril_mm": float(peitoril_mm),
                "offset": offset,
                "rot_z": float(rot_z),
                "lado_abertura": lado_abertura,
                "sentido_abertura": sentido_abertura,
            },
            "trazomob_module": {
                "tipo": tipo,
                "largura": float(largura_mm),
                "altura": float(altura_mm),
                "profundidade": float(esp_parede_mm),
                "peitoril_mm": float(peitoril_mm),
                "offset": offset,
                "rot_z": float(rot_z),
                "lado_abertura": lado_abertura,
                "sentido_abertura": sentido_abertura,
            },
        }

        # Aplica rotação Z se necessário
        if abs(rot_z) > 1e-4:
            rad = math.radians(rot_z)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            ox, oy, _ = offset
            for p in pieces:
                m = getattr(p, "mesh", None)
                if m and hasattr(m, "vertices"):
                    for v in m.vertices:
                        px = v.position.x() - ox
                        py = v.position.y() - oy
                        rx = px * cos_a - py * sin_a + ox
                        ry = px * sin_a + py * cos_a + oy
                        v.position = QVector3D(rx, ry, v.position.z())
                    m._mut_serial = getattr(m, "_mut_serial", 0) + 1

        return master

    # ─────────────────────────────────────────────────────────────
    # CARREGAMENTO E PARAMETRIZAÇÃO DAS ESQUADRIAS REAIS (.IGZ)
    # ─────────────────────────────────────────────────────────────

    # Cache em memória das portas .igz já parseadas e com xforms consolidados na origem
    _PORTA_PROTO_CACHE: dict[str, tuple[list[Group], float, float, float]] = {}

    @classmethod
    def get_esquadria_local_mid_y(cls, item_id: str, esp_parede_mm: float = 150.0) -> float:
        """Retorna a coordenada Y central local da esquadria sem precisar clonar ou construir toda a malha."""
        from pathlib import Path
        base_dir = Path(__file__).resolve().parents[1]
        user_portas_path = base_dir / "assets" / "components" / "portas" / f"{item_id}.igz"
        if not user_portas_path.exists():
            mapping = {
                "porta_giro_90": "porta_giro.igz",
                "porta_giro_80": "porta_giro.igz",
                "porta_giro_70": "porta_giro.igz",
                "porta_giro": "porta_giro.igz",
                "porta_aluminio_90": "porta_aluminio.igz",
                "porta_aluminio": "porta_aluminio.igz",
                "porta_correr_vidro_4f_287": "porta_correr_vidro_4f_287.igz",
                "porta_correr_vidro_4f": "porta_correr_vidro_4f_287.igz",
                "porta_correr_vidro_170": "porta_correr_vidro_170.igz",
                "porta_correr_vidro": "porta_correr_vidro_170.igz",
                "porta_pivotante_vidro_80": "porta_pivotante_vidro.igz",
                "porta_pivotante_vidro": "porta_pivotante_vidro.igz",
                "janela_correr_2f_130": "janela_correr_2f_130.igz",
                "janela_correr_4f_190": "janela_correr_4f_190.igz",
                "janela_vertical_50": "janela_vertical_50.igz",
                "janela_maximar_70": "janela_maximar_70.igz",
                "janela_basculante_sup_170": "janela_vertical_50.igz",
                "janela_basculante_inf_170": "janela_vertical_50.igz",
            }
            if item_id in mapping:
                user_portas_path = base_dir / "assets" / "components" / "portas" / mapping[item_id]
        if user_portas_path.exists():
            _, _, min_y, max_y = cls._get_porta_prototype(user_portas_path)
            return (min_y + max_y) * 0.5
        return (esp_parede_mm / 1000.0) * 0.5

    @classmethod
    def _get_porta_prototype(cls, igz_path) -> tuple[list[Group], float, float, float]:
        """Carrega e armazena em cache os grupos protótipos já consolidados (xform baked) de uma porta .igz."""
        key = str(igz_path)
        cached = cls._PORTA_PROTO_CACHE.get(key)
        if cached is not None:
            return cached

        from collections import defaultdict
        from core.scene import Scene
        from core.group import transformed_mesh
        from formats import igz

        temp_scene = Scene()
        igz.load_into(temp_scene, igz_path)

        def bake_xforms(group: Group, parent_matrix: QMatrix4x4 | None = None) -> None:
            if parent_matrix is None:
                current = QMatrix4x4(group.xform) if group.xform else QMatrix4x4()
            else:
                current = parent_matrix * (group.xform if group.xform else QMatrix4x4())
            group.xform = None
            if group.mesh and len(group.mesh.vertices) > 0:
                if not current.isIdentity():
                    group.mesh = transformed_mesh(group.mesh, current)
            for c in getattr(group, "children", []):
                bake_xforms(c, current)

        for g in temp_scene.groups:
            bake_xforms(g)

        loaded_groups = list(temp_scene.groups)
        if "porta_pivotante_vidro" in igz_path.name and len(loaded_groups) == 1 and loaded_groups[0].mesh:
            orig_mesh = loaded_groups[0].mesh
            # 1. Folha de vidro: prisma sólido estanque com as dimensões reais do vão
            vidro_attrs = {
                "color": [0.9647058823529412, 0.9686274509803922, 0.9176470588235294],
                "material": "vidro_incolor",
            }
            mesh_vidro = Mesh()
            p0 = QVector3D(0.005, 0.04125, 0.01505)
            p1 = QVector3D(0.795, 0.05325, 2.08785)
            v000 = QVector3D(p0.x(), p0.y(), p0.z())
            v100 = QVector3D(p1.x(), p0.y(), p0.z())
            v110 = QVector3D(p1.x(), p1.y(), p0.z())
            v010 = QVector3D(p0.x(), p1.y(), p0.z())
            v001 = QVector3D(p0.x(), p0.y(), p1.z())
            v101 = QVector3D(p1.x(), p0.y(), p1.z())
            v111 = QVector3D(p1.x(), p1.y(), p1.z())
            v011 = QVector3D(p0.x(), p1.y(), p1.z())
            for gf in [
                [v000, v010, v110, v100],  # base
                [v001, v101, v111, v011],  # topo
                [v000, v100, v101, v001],  # frente
                [v110, v010, v011, v111],  # costas
                [v010, v000, v001, v011],  # esquerda
                [v100, v110, v111, v101],  # direita
            ]:
                nf = mesh_vidro.add_face(gf)
                nf.attrs = dict(vidro_attrs)

            # 2. Puxador: faces frontais/traseiras e tampões de apoio estanques
            mesh_puxador = Mesh()
            # 3. Braçadeiras/clamps articuláveis (giram com a porta)
            mesh_ferragens_moveis = Mesh()
            # 4. Bases dos pivôs fixas (chão e teto)
            mesh_pivots_fixos = Mesh()

            for i, f in enumerate(orig_mesh.faces):
                pts = [QVector3D(v) for v in f.vertices]
                attrs = dict(f.attrs) if hasattr(f, "attrs") else {}
                color = tuple(attrs.get("color")) if attrs.get("color") else None
                if color == (0.9647058823529412, 0.9686274509803922, 0.9176470588235294):
                    continue
                elif color == (0.0, 0.0, 0.0) and min(p.x() for p in pts) > 0.5:
                    nf = mesh_puxador.add_face(pts)
                    nf.attrs = attrs
                elif i not in (0, 51) and i not in range(108, 120):
                    zs = [round(p.z(), 4) for p in pts]
                    if max(zs) <= 0.009 or min(zs) >= 2.091:
                        nf = mesh_pivots_fixos.add_face(pts)
                        nf.attrs = attrs
                    else:
                        nf = mesh_ferragens_moveis.add_face(pts)
                        nf.attrs = attrs

            # Repara e fecha o puxador e as ferragens para solidez manifold estanque
            import plugins.solid_inspector as si
            from core.orient import orient_outward
            si.repair_mesh(mesh_puxador)

            for loop in si._border_loops(mesh_ferragens_moveis):
                si._cap(mesh_ferragens_moveis, loop)
            orient_outward(mesh_ferragens_moveis)
            orient_outward(mesh_pivots_fixos)

            grp_marco = Group(mesh=mesh_pivots_fixos, name="Pivôs Fixos Marco")
            grp_ferr_mov = Group(mesh=mesh_ferragens_moveis, name="Braçadeiras Ferragens Vidro")
            grp_folha = Group(mesh=mesh_vidro, name="Folha Vidro Pivotante")
            grp_pux = Group(mesh=mesh_puxador, name="Puxador Porta Pivotante")
            loaded_groups = [grp_marco, grp_ferr_mov, grp_folha, grp_pux]

        elif "porta_aluminio" in igz_path.name:
            # Separa o marco das ferragens da fechadura posterior que estavam fundidas em Agrupar#98
            g98 = next((g for g in loaded_groups if g.name == "Agrupar#98"), None)
            if g98 and g98.mesh and len(g98.mesh.faces) > 0:
                m_98 = g98.mesh

                def _pt_k(p):
                    return (round(p.x(), 5), round(p.y(), 5), round(p.z(), 5))

                p2f: dict[tuple[float, float, float], list[int]] = {}
                for fi, f in enumerate(m_98.faces):
                    for v in f.vertices:
                        p2f.setdefault(_pt_k(v), []).append(fi)
                f_adj = [set() for _ in range(len(m_98.faces))]
                for flist in p2f.values():
                    for f1 in flist:
                        for f2 in flist:
                            if f1 != f2:
                                f_adj[f1].add(f2)
                vis = [False] * len(m_98.faces)
                comps: list[list[int]] = []
                for i in range(len(m_98.faces)):
                    if not vis[i]:
                        comp = []
                        q = [i]
                        vis[i] = True
                        while q:
                            curr = q.pop()
                            comp.append(curr)
                            for nb in f_adj[curr]:
                                if not vis[nb]:
                                    vis[nb] = True
                                    q.append(nb)
                        comps.append(comp)

                fech_f_indices: list[int] = []
                marco_f_indices: list[int] = []
                for comp in comps:
                    comp_pts = [v for fi in comp for v in m_98.faces[fi].vertices]
                    xs = [p.x() for p in comp_pts]
                    if min(xs) > 0.80 or len(comp) == 97:
                        marco_f_indices.extend(comp)
                    else:
                        fech_f_indices.extend(comp)

                mesh_fech_post = Mesh()
                for fi in fech_f_indices:
                    f = m_98.faces[fi]
                    nf = mesh_fech_post.add_face([v for v in f.vertices])
                    if f.attrs:
                        nf.attrs = dict(f.attrs)
                    for h in f.holes:
                        mesh_fech_post.add_hole(nf, [v for v in h])

                mesh_marco_limpo = Mesh()
                for fi in marco_f_indices:
                    f = m_98.faces[fi]
                    nf = mesh_marco_limpo.add_face([v for v in f.vertices])
                    if f.attrs:
                        nf.attrs = dict(f.attrs)
                    for h in f.holes:
                        mesh_marco_limpo.add_hole(nf, [v for v in h])

                g98.mesh = mesh_marco_limpo
                g98.name = "Marco da Porta"
                grp_fech_post = Group(mesh=mesh_fech_post, name="Fechadura Posterior")

                new_loaded = []
                for g in loaded_groups:
                    new_loaded.append(g)
                    if g is g98:
                        new_loaded.append(grp_fech_post)
                loaded_groups = new_loaded

        elif "porta_correr_vidro_4f" in igz_path.name:
            pass
        elif "porta_correr" in igz_path.name:
            # Separa as duas folhas de correr (esquerda frontal e direita traseira)
            g_folha = next((g for g in loaded_groups if "Porta de correr" in g.name), None)
            if g_folha and g_folha.mesh and len(g_folha.mesh.faces) > 0:
                m_f = g_folha.mesh

                def _pt_kc(p):
                    return (round(p.x(), 5), round(p.y(), 5), round(p.z(), 5))

                p2fc: dict[tuple[float, float, float], list[int]] = {}
                for fi, f in enumerate(m_f.faces):
                    for v in f.vertices:
                        p2fc.setdefault(_pt_kc(v), []).append(fi)
                fc_adj = [set() for _ in range(len(m_f.faces))]
                for flist in p2fc.values():
                    for f1 in flist:
                        for f2 in flist:
                            if f1 != f2:
                                fc_adj[f1].add(f2)
                vis_c = [False] * len(m_f.faces)
                comps_c: list[list[int]] = []
                for i in range(len(m_f.faces)):
                    if not vis_c[i]:
                        comp = []
                        q = [i]
                        vis_c[i] = True
                        while q:
                            curr = q.pop()
                            comp.append(curr)
                            for nb in fc_adj[curr]:
                                if not vis_c[nb]:
                                    vis_c[nb] = True
                                    q.append(nb)
                        comps_c.append(comp)

                esq_f_indices: list[int] = []
                dir_f_indices: list[int] = []
                for comp in comps_c:
                    comp_pts = [v for fi in comp for v in m_f.faces[fi].vertices]
                    xs = [p.x() for p in comp_pts]
                    if min(xs) < 0.80:
                        esq_f_indices.extend(comp)
                    else:
                        dir_f_indices.extend(comp)

                mesh_esq = Mesh()
                for fi in esq_f_indices:
                    f = m_f.faces[fi]
                    nf = mesh_esq.add_face([v for v in f.vertices])
                    if f.attrs:
                        nf.attrs = dict(f.attrs)
                    for h in f.holes:
                        mesh_esq.add_hole(nf, [v for v in h])

                mesh_dir = Mesh()
                for fi in dir_f_indices:
                    f = m_f.faces[fi]
                    nf = mesh_dir.add_face([v for v in f.vertices])
                    if f.attrs:
                        nf.attrs = dict(f.attrs)
                    for h in f.holes:
                        mesh_dir.add_hole(nf, [v for v in h])

                g_folha.mesh = mesh_esq
                g_folha.name = "Folha de Correr Esquerda"
                grp_folha_dir = Group(mesh=mesh_dir, name="Folha de Correr Direita")

                new_loaded = []
                for g in loaded_groups:
                    new_loaded.append(g)
                    if g is g_folha:
                        new_loaded.append(grp_folha_dir)
                loaded_groups = new_loaded

        elif "janela_correr_2f" in igz_path.name:
            # Mesma estratégia da 4f: separa as faces originais por componentes conectados,
            # preservando os attrs de material/opacidade do vidro (reconstruir do zero
            # fazia o vidro perder "mat"/"opacity" e ficar opaco na cena).
            if loaded_groups and loaded_groups[0].mesh:
                m = loaded_groups[0].mesh
                def _pt_k(p): return (round(p.x(), 4), round(p.y(), 4), round(p.z(), 4))
                p2f = defaultdict(list)
                for fi, f in enumerate(m.faces):
                    for pt in f.vertices: p2f[_pt_k(pt)].append(fi)
                f_adj = [set() for _ in range(len(m.faces))]
                for flist in p2f.values():
                    for f1 in flist:
                        for f2 in flist:
                            if f1 != f2: f_adj[f1].add(f2)
                vis = [False] * len(m.faces)
                comps = []
                for i in range(len(m.faces)):
                    if not vis[i]:
                        comp = []; q = [i]; vis[i] = True
                        while q:
                            curr = q.pop(); comp.append(curr)
                            for nb in f_adj[curr]:
                                if not vis[nb]: vis[nb] = True; q.append(nb)
                        comps.append(comp)

                def build_submesh(indices):
                    nm = Mesh()
                    for fi in indices:
                        f = m.faces[fi]
                        nf = nm.add_face([pt for pt in f.vertices])
                        if f.attrs: nf.attrs = dict(f.attrs)
                        for h in f.holes: nm.add_hole(nf, [pt for pt in h])
                    return nm

                # comp 0: marco (137 faces)
                # folha esq: comp 2 (com vidro) + comps 1 e 3 (fecho e puxador esquerdos)
                # folha dir: comp 4 (com vidro) + comps 5 e 6 (fecho e puxador direitos)
                f_marco = list(comps[0])
                f_esq = list(comps[2]) + list(comps[1]) + list(comps[3])
                f_dir = list(comps[4]) + list(comps[5]) + list(comps[6])

                g_marco = Group(mesh=build_submesh(f_marco), name="Marco da Janela")
                g_esq = Group(mesh=build_submesh(f_esq), name="Folha de Correr Esquerda")
                g_dir = Group(mesh=build_submesh(f_dir), name="Folha de Correr Direita")
                loaded_groups = [g_marco, g_esq, g_dir]

        elif "janela_correr_4f" in igz_path.name:
            if loaded_groups and loaded_groups[0].mesh:
                m = loaded_groups[0].mesh
                def _pt_k(p): return (round(p.x(), 4), round(p.y(), 4), round(p.z(), 4))
                p2f = defaultdict(list)
                for fi, f in enumerate(m.faces):
                    for pt in f.vertices: p2f[_pt_k(pt)].append(fi)
                f_adj = [set() for _ in range(len(m.faces))]
                for flist in p2f.values():
                    for f1 in flist:
                        for f2 in flist:
                            if f1 != f2: f_adj[f1].add(f2)
                vis = [False] * len(m.faces)
                comps = []
                for i in range(len(m.faces)):
                    if not vis[i]:
                        comp = []; q = [i]; vis[i] = True
                        while q:
                            curr = q.pop(); comp.append(curr)
                            for nb in f_adj[curr]:
                                if not vis[nb]: vis[nb] = True; q.append(nb)
                        comps.append(comp)

                def build_submesh(indices):
                    nm = Mesh()
                    for fi in indices:
                        f = m.faces[fi]
                        nf = nm.add_face([pt for pt in f.vertices])
                        if f.attrs: nf.attrs = dict(f.attrs)
                        for h in f.holes: nm.add_hole(nf, [pt for pt in h])
                    return nm

                # comp 7: marco (137 faces)
                # fixa esq: comps 0, 2, e faces de comp 1 em X <= 0.510 (37 faces)
                # movel centro esq: comps 3, 4, 5, e faces de comp 1 em X > 0.480 e Y > 0.040 (81 faces)
                # movel centro dir: comps 6, 8, 9 (76 faces)
                # fixa dir: comps 10, 11 (29 faces)
                c1_esq = [13, 30, 17, 28, 18, 16]
                c1_centro = [40, 51, 49, 48, 56, 46, 39]
                f_fixa_esq = list(comps[0]) + list(comps[2]) + c1_esq
                f_movel_esq = list(comps[3]) + list(comps[4]) + list(comps[5]) + c1_centro
                f_movel_dir = list(comps[6]) + list(comps[8]) + list(comps[9])
                f_fixa_dir = list(comps[10]) + list(comps[11])
                f_marco = list(comps[7])

                g_marco = Group(mesh=build_submesh(f_marco), name="Marco da Janela")
                g_fixa_esq = Group(mesh=build_submesh(f_fixa_esq), name="Folha Fixa Esquerda")
                g_movel_esq = Group(mesh=build_submesh(f_movel_esq), name="Folha de Correr Centro Esquerda")
                g_movel_dir = Group(mesh=build_submesh(f_movel_dir), name="Folha de Correr Centro Direita")
                g_fixa_dir = Group(mesh=build_submesh(f_fixa_dir), name="Folha Fixa Direita")
                loaded_groups = [g_marco, g_fixa_esq, g_movel_esq, g_movel_dir, g_fixa_dir]

        elif "janela_maximar" in igz_path.name:
            if loaded_groups and loaded_groups[0].mesh:
                m = loaded_groups[0].mesh
                def _pt_k(p): return (round(p.x(), 4), round(p.y(), 4), round(p.z(), 4))
                p2f = defaultdict(list)
                for fi, f in enumerate(m.faces):
                    for pt in f.vertices: p2f[_pt_k(pt)].append(fi)
                f_adj = [set() for _ in range(len(m.faces))]
                for flist in p2f.values():
                    for f1 in flist:
                        for f2 in flist:
                            if f1 != f2: f_adj[f1].add(f2)
                vis = [False] * len(m.faces)
                comps = []
                for i in range(len(m.faces)):
                    if not vis[i]:
                        comp = []; q = [i]; vis[i] = True
                        while q:
                            curr = q.pop(); comp.append(curr)
                            for nb in f_adj[curr]:
                                if not vis[nb]: vis[nb] = True; q.append(nb)
                        comps.append(comp)

                def build_submesh(indices):
                    nm = Mesh()
                    for fi in indices:
                        f = m.faces[fi]
                        nf = nm.add_face([pt for pt in f.vertices])
                        if f.attrs: nf.attrs = dict(f.attrs)
                        for h in f.holes: nm.add_hole(nf, [pt for pt in h])
                    return nm

                # comp 3: marco fixo (124 faces)
                # comps 0, 1, 2, 4, 5: folha móvel basculante/projetante (113 faces)
                f_marco = list(comps[3])
                f_folha = list(comps[0]) + list(comps[1]) + list(comps[2]) + list(comps[4]) + list(comps[5])
                g_marco = Group(mesh=build_submesh(f_marco), name="Marco da Janela")
                g_folha = Group(mesh=build_submesh(f_folha), name="Folha Basculante Maxim-Ar")
                loaded_groups = [g_marco, g_folha]

        elif "janela_vertical" in igz_path.name:
            if loaded_groups and loaded_groups[0].mesh:
                m = loaded_groups[0].mesh
                def _pt_k(p): return (round(p.x(), 4), round(p.y(), 4), round(p.z(), 4))
                p2f = defaultdict(list)
                for fi, f in enumerate(m.faces):
                    for pt in f.vertices: p2f[_pt_k(pt)].append(fi)
                f_adj = [set() for _ in range(len(m.faces))]
                for flist in p2f.values():
                    for f1 in flist:
                        for f2 in flist:
                            if f1 != f2: f_adj[f1].add(f2)
                vis = [False] * len(m.faces)
                comps = []
                for i in range(len(m.faces)):
                    if not vis[i]:
                        comp = []; q = [i]; vis[i] = True
                        while q:
                            curr = q.pop(); comp.append(curr)
                            for nb in f_adj[curr]:
                                if not vis[nb]: vis[nb] = True; q.append(nb)
                        comps.append(comp)

                def build_submesh(indices):
                    nm = Mesh()
                    for fi in indices:
                        f = m.faces[fi]
                        nf = nm.add_face([pt for pt in f.vertices])
                        if f.attrs: nf.attrs = dict(f.attrs)
                        for h in f.holes: nm.add_hole(nf, [pt for pt in h])
                    return nm

                # folha móvel: comp 0 (10 faces), comp 5 (9 faces), e 5 faces de caixilho inferior (total 24 faces)
                # marco fixo e bandeiras fixas: 65 faces
                c2_folha = [50, 52, 49, 41, 64]
                f_folha = list(comps[0]) + list(comps[5]) + c2_folha
                f_marco = [fi for fi in range(len(m.faces)) if fi not in f_folha]
                g_marco = Group(mesh=build_submesh(f_marco), name="Marco da Janela")
                g_folha = Group(mesh=build_submesh(f_folha), name="Folha Basculante Vertical")
                loaded_groups = [g_marco, g_folha]

        sub_pieces: List[Group] = []
        def flatten_pieces(g: Group) -> None:
            if g.mesh and len(g.mesh.faces) > 0:
                sub_pieces.append(g)
            for c in getattr(g, "children", []):
                flatten_pieces(c)

        for g in loaded_groups:
            flatten_pieces(g)

        all_pts = [v.position for sp in sub_pieces if sp.mesh for v in sp.mesh.vertices]
        min_x = min(p.x() for p in all_pts) if all_pts else 0.0
        max_x = max(p.x() for p in all_pts) if all_pts else 0.80
        min_y = min(p.y() for p in all_pts) if all_pts else 0.0
        max_y = max(p.y() for p in all_pts) if all_pts else 0.15
        min_z = min(p.z() for p in all_pts) if all_pts else 0.0

        shift_zero = QVector3D(-min_x, -min_y, -min_z)
        for sp in sub_pieces:
            if sp.mesh:
                for v in sp.mesh.vertices:
                    v.position += shift_zero
                sp.mesh._mut_serial = getattr(sp.mesh, "_mut_serial", 0) + 1

        # Calcula os limites Y do marco estrutural (após shift_zero) para que o espelhamento
        # Dentro/Fora (flip_y) reflita em torno do centro real do marco na parede!
        frame_names = {"Agrupar#95", "Agrupar#98", "Trilho e Marco Fixo", "Marco e Ferragens Fixas"}
        frame_pts = [
            v.position
            for sp in sub_pieces
            if sp.mesh and (sp.name in frame_names or "Marco" in sp.name or "Trilho" in sp.name)
            for v in sp.mesh.vertices
        ]
        if frame_pts:
            f_min_y = min(p.y() for p in frame_pts)
            f_max_y = max(p.y() for p in frame_pts)
        else:
            f_min_y = 0.0
            f_max_y = max_y - min_y

        res = (sub_pieces, max_x - min_x, f_min_y, f_max_y)
        cls._PORTA_PROTO_CACHE[key] = res
        return res

    @classmethod
    def load_esquadria_igz(
        cls,
        item_id: str,
        largura_mm: float,
        altura_mm: float,
        esp_parede_mm: float,
        peitoril_mm: float = 0.0,
        offset: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        rot_z: float = 0.0,
        lado_abertura: str = "direita",
        sentido_abertura: str = "interno",
    ) -> Group:
        """Carrega e instancia o modelo 3D nativo (.igz) com sub-peças dinâmicas isoladas.

        Preserva 100% da fidelidade dos componentes (marco fixo, folha móvel articulável,
        fechadura e maçaneta sem distorção).
        """
        import os
        import json
        from pathlib import Path

        base_dir = Path(__file__).resolve().parents[1]
        # Procura primeiro nos modelos originais de portas salvos pelo usuário
        user_portas_path = base_dir / "assets" / "components" / "portas" / f"{item_id}.igz"
        if not user_portas_path.exists():
            mapping = {
                "porta_giro_90": "porta_giro.igz",
                "porta_giro_80": "porta_giro.igz",
                "porta_giro_70": "porta_giro.igz",
                "porta_giro": "porta_giro.igz",
                "porta_aluminio_90": "porta_aluminio.igz",
                "porta_aluminio": "porta_aluminio.igz",
                "porta_correr_vidro_4f_287": "porta_correr_vidro_4f_287.igz",
                "porta_correr_vidro_4f": "porta_correr_vidro_4f_287.igz",
                "porta_correr_vidro_170": "porta_correr_vidro_170.igz",
                "porta_correr_vidro": "porta_correr_vidro_170.igz",
                "porta_pivotante_vidro_80": "porta_pivotante_vidro.igz",
                "porta_pivotante_vidro": "porta_pivotante_vidro.igz",
                "janela_correr_2f_130": "janela_correr_2f_130.igz",
                "janela_correr_4f_190": "janela_correr_4f_190.igz",
                "janela_vertical_50": "janela_vertical_50.igz",
                "janela_maximar_70": "janela_maximar_70.igz",
                "janela_basculante_sup_170": "janela_vertical_50.igz",
                "janela_basculante_inf_170": "janela_vertical_50.igz",
            }
            if item_id in mapping:
                user_portas_path = base_dir / "assets" / "components" / "portas" / mapping[item_id]

        is_user_porta = user_portas_path.exists()
        if is_user_porta:
            igz_path = user_portas_path
        else:
            igz_path = base_dir / "assets" / "components" / "esquadrias" / f"{item_id}.igz"

        if not igz_path.exists():
            if "janela" in item_id:
                if "4f" in item_id:
                    grp = cls.build_janela_correr_4folhas(largura_mm, altura_mm, esp_parede_mm, peitoril_mm=peitoril_mm, offset=offset, rot_z=rot_z)
                elif "correr" in item_id:
                    grp = cls.build_janela_correr(largura_mm, altura_mm, esp_parede_mm, peitoril_mm=peitoril_mm, offset=offset, rot_z=rot_z)
                elif "vertical" in item_id:
                    grp = cls.build_janela_vertical_bandeira(largura_mm, altura_mm, esp_parede_mm, peitoril_mm=peitoril_mm, offset=offset, rot_z=rot_z)
                else:
                    grp = cls.build_janela_maximar(largura_mm, altura_mm, esp_parede_mm, peitoril_mm=peitoril_mm, offset=offset, rot_z=rot_z)
            else:
                grp = cls.build_porta_giro(largura_mm, altura_mm, esp_parede_mm, lado_abertura=lado_abertura, offset=offset, rot_z=rot_z)
            if hasattr(grp, "ext") and ("trazomob_esquadria" in grp.ext
                                        or "trazomob" in grp.ext):
                from ..domain.schema import update_esquadria_data
                update_esquadria_data(grp, {"tipo": item_id})
            return grp

        # Se for uma das 4 portas originais copiadas pelo usuário, usamos o carregador de alta fidelidade
        if is_user_porta:
            return cls._load_porta_original_usuario(
                igz_path=igz_path,
                item_id=item_id,
                largura_mm=largura_mm,
                altura_mm=altura_mm,
                esp_parede_mm=esp_parede_mm,
                peitoril_mm=peitoril_mm,
                offset=offset,
                rot_z=rot_z,
                lado_abertura=lado_abertura,
                sentido_abertura=sentido_abertura,
            )

        with open(igz_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_groups = data.get("scene", {}).get("groups", [])
        if not raw_groups:
            return cls.build_porta_giro(largura_mm, altura_mm, esp_parede_mm, lado_abertura=lado_abertura, offset=offset, rot_z=rot_z)

        # 1. Encontrar bounding box total de referência de todo o conjunto
        all_pts_total = []
        for g_dict in raw_groups:
            for f_data in g_dict.get("faces", []):
                for p in f_data.get("vertices", []):
                    all_pts_total.append(p)

        if not all_pts_total:
            return cls.build_porta_giro(largura_mm, altura_mm, esp_parede_mm, lado_abertura=lado_abertura, offset=offset, rot_z=rot_z)

        min_x = min(p[0] for p in all_pts_total)
        max_x = max(p[0] for p in all_pts_total)
        min_y = min(p[1] for p in all_pts_total)
        max_y = max(p[1] for p in all_pts_total)
        min_z = min(p[2] for p in all_pts_total)
        max_z = max(p[2] for p in all_pts_total)

        orig_w = max(0.001, max_x - min_x)
        orig_d = max(0.001, max_y - min_y)
        orig_h = max(0.001, max_z - min_z)

        target_w = largura_mm / 1000.0
        target_h = altura_mm / 1000.0
        target_d = (esp_parede_mm / 1000.0) if esp_parede_mm > 50 else orig_d

        scale_x = target_w / orig_w
        scale_y = target_d / orig_d if orig_d > 0.05 else 1.0
        scale_z = target_h / orig_h

        flip_x = str(lado_abertura or "direita").strip().lower().startswith(("esq", "left"))
        flip_y = str(sentido_abertura or "interno").strip().lower().startswith(("ext", "for", "out"))

        ox, oy, oz = offset
        peit_m = peitoril_mm / 1000.0

        rad = math.radians(rot_z)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        sub_pieces = []
        for g_dict in raw_groups:
            part_name = g_dict.get("name", "Parte Esquadria")
            mesh = Mesh()
            raw_faces = g_dict.get("faces", [])

            for f_data in raw_faces:
                pts = [QVector3D(p[0], p[1], p[2]) for p in f_data.get("vertices", [])]
                if len(pts) < 3:
                    continue

                transformed_pts = []
                for pt in pts:
                    # Normaliza em relação à origem do modelo
                    px = (pt.x() - min_x) * scale_x
                    py = (pt.y() - min_y) * scale_y
                    pz = (pt.z() - min_z) * scale_z + peit_m

                    if flip_x:
                        px = target_w - px
                    if flip_y:
                        py = target_d - py

                    if abs(rot_z) > 1e-4:
                        rx = px * cos_a - py * sin_a
                        ry = px * sin_a + py * cos_a
                        px, py = rx, ry

                    transformed_pts.append(QVector3D(px + ox, py + oy, pz + oz))

                if flip_x != flip_y:
                    transformed_pts.reverse()

                face = mesh.add_face(transformed_pts)
                color = f_data.get("color")
                if color:
                    face.attrs["color"] = tuple(color)

            sub_grp = Group(mesh=mesh, name=part_name)
            sub_grp.layer = "ESQUADRIAS"
            sub_pieces.append(sub_grp)

        # Monta o grupo raiz da Esquadria contendo marco e folhas articuláveis
        root_name = f"{item_id.replace('_', ' ').title()} {int(largura_mm)}x{int(altura_mm)}"
        root_grp = Group(name=root_name)
        for sp in sub_pieces:
            sp.owner = root_grp
        root_grp.children.extend(sub_pieces)
        root_grp.layer = "ESQUADRIAS"
        if getattr(root_grp, 'ext', None) is None:
            root_grp.ext = {}
        lado_norm = "esquerda" if flip_x else "direita"
        sentido_norm = "externo" if flip_y else "interno"
        from ..domain.schema import set_esquadria_data
        set_esquadria_data(root_grp, {
            "tipo": item_id,
            "largura_mm": float(largura_mm),
            "altura_mm": float(altura_mm),
            "esp_parede_mm": float(esp_parede_mm),
            "peitoril_mm": float(peitoril_mm),
            "offset": offset,
            "rot_z": float(rot_z),
            "lado_abertura": lado_norm,
            "sentido_abertura": sentido_norm,
        })
        return root_grp

    @classmethod
    def _load_porta_original_usuario(
        cls,
        igz_path: Path,
        item_id: str,
        largura_mm: float,
        altura_mm: float,
        esp_parede_mm: float,
        peitoril_mm: float = 0.0,
        offset: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        rot_z: float = 0.0,
        lado_abertura: str = "direita",
        sentido_abertura: str = "interno",
    ) -> Group:
        """Carrega com máxima fidelidade uma das portas reais fornecidas pelo usuário.

        Preserva 100% da malha geométrica original sem distorcer fechaduras ou puxadores.
        Utiliza protótipo pré-consolidado em cache e cópia vetorizada (transformed_mesh),
        com suporte a inversão de lado (esquerda/direita) e sentido (interno/externo).
        """
        from core.group import transformed_mesh

        proto_pieces, orig_w, f_min_y, f_max_y = cls._get_porta_prototype(igz_path)

        # Suporte a redimensionamento paramétrico contínuo de largura (70, 80, 90cm ou personalizado)
        # sem deformar fechaduras, puxadores, ferragens ou caixilhos/folhas:
        target_w = float(largura_mm) / 1000.0 if largura_mm and float(largura_mm) > 100 else orig_w
        delta_w = target_w - orig_w
        is_j2f = "janela_correr_2f" in igz_path.name
        is_j4f = "janela_correr_4f" in igz_path.name
        cut_x = 0.40 if "porta_pivotante" in igz_path.name else 0.50

        flip_x = str(lado_abertura or "direita").strip().lower().startswith(("esq", "left"))
        flip_y = str(sentido_abertura or "interno").strip().lower().startswith(("ext", "for", "out"))
        lado_norm = "esquerda" if flip_x else "direita"
        sentido_norm = "externo" if flip_y else "interno"

        ox, oy, oz = offset
        peit_m = peitoril_mm / 1000.0
        m_transform = QMatrix4x4()
        m_transform.translate(ox, oy, oz + peit_m)
        if abs(rot_z) > 1e-4:
            m_transform.rotate(rot_z, 0.0, 0.0, 1.0)
        if flip_x or flip_y:
            m_transform.translate(target_w if flip_x else 0.0, (f_min_y + f_max_y) if flip_y else 0.0, 0.0)
            m_transform.scale(-1.0 if flip_x else 1.0, -1.0 if flip_y else 1.0, 1.0)

        odd_reflection = (flip_x != flip_y)

        sub_pieces: List[Group] = []
        ident = QMatrix4x4()
        d_quart = delta_w * 0.25

        for proto in proto_pieces:
            if not proto.mesh:
                cloned_mesh = Mesh()
            else:
                cloned_mesh = transformed_mesh(proto.mesh, ident)
                if abs(delta_w) > 1e-4:
                    p_name = proto.name or ""
                    if is_j2f:
                        # Janela de correr 2 folhas: escala uniforme em X.
                        # Os limites fixos antigos (0.65/0.60/0.35/0.95) colapsavam a
                        # barra central do marco (~5 cm) quando delta_w era negativo:
                        # em 1,20 os vertices 0.6214+(-0,05) e 0.6714+(-0,10)
                        # coincidiam; abaixo disso a ordem se invertia. Escalar tudo
                        # preserva marco, folhas, vidro e ferragens sem colapsos.
                        scale_x = target_w / orig_w
                        for v in cloned_mesh.vertices:
                            v.position.setX(v.position.x() * scale_x)
                    elif is_j4f:
                        # Janela de correr 4 folhas: 2 fixas laterais + 2 móveis centrais
                        for v in cloned_mesh.vertices:
                            vx = v.position.x()
                            if "Marco" in p_name:
                                if vx > 1.80:
                                    v.position.setX(vx + delta_w)
                                elif vx > 1.30:
                                    v.position.setX(vx + d_quart * 3.0)
                                elif vx > 0.90:
                                    v.position.setX(vx + d_quart * 2.0)
                                elif vx > 0.40:
                                    v.position.setX(vx + d_quart)
                            elif "Fixa Esquerda" in p_name:
                                if vx > 0.25:
                                    v.position.setX(vx + d_quart)
                            elif "Centro Esquerda" in p_name:
                                if vx > 0.70:
                                    v.position.setX(vx + d_quart * 2.0)
                                else:
                                    v.position.setX(vx + d_quart)
                            elif "Centro Direita" in p_name:
                                if vx > 1.15:
                                    v.position.setX(vx + d_quart * 3.0)
                                else:
                                    v.position.setX(vx + d_quart * 2.0)
                            elif "Fixa Direita" in p_name:
                                if vx > 1.60:
                                    v.position.setX(vx + delta_w)
                                else:
                                    v.position.setX(vx + d_quart * 3.0)
                    else:
                        for v in cloned_mesh.vertices:
                            if v.position.x() > cut_x:
                                v.position.setX(v.position.x() + delta_w)
                cloned_mesh = transformed_mesh(cloned_mesh, m_transform)
            if odd_reflection and cloned_mesh.faces:
                for face in cloned_mesh.faces:
                    face.vertices.reverse()
                    if getattr(face, "hole_loops", None):
                        for hloop in face.hole_loops:
                            hloop.reverse()
                cloned_mesh._mut_serial = getattr(cloned_mesh, "_mut_serial", 0) + 1
            sp = Group(mesh=cloned_mesh, name=proto.name)
            sp.layer = "ESQUADRIAS"
            sub_pieces.append(sp)

        rad = math.radians(rot_z)
        u_dir = QVector3D(math.cos(rad), math.sin(rad), 0.0)
        n_dir = QVector3D(-math.sin(rad), math.cos(rad), 0.0)
        p_orig_2d = QVector3D(ox, oy, 0.0)

        def _local_extents(mesh_obj: Mesh) -> tuple[float, float, float, float]:
            pts = [v.position for v in mesh_obj.vertices]
            if not pts:
                return (0.0, 0.0, 0.0, 0.0)
            us = [QVector3D.dotProduct(QVector3D(p.x(), p.y(), 0.0) - p_orig_2d, u_dir) for p in pts]
            ns = [QVector3D.dotProduct(QVector3D(p.x(), p.y(), 0.0) - p_orig_2d, n_dir) for p in pts]
            return (min(us), max(us), min(ns), max(ns))

        sx = -1.0 if flip_x else 1.0
        sy = -1.0 if flip_y else 1.0

        # Identifica folha e acessórios conforme o tipo de porta
        linked_names = []
        if "porta_giro" in igz_path.name:
            for sp in sub_pieces:
                if sp.name == "Agrupar#89":
                    sp.name = "Folha da Porta"
                elif sp.name == "Agrupar#95":
                    sp.name = "Marco da Porta"
                else:
                    sp.name = f"Fechadura {sp.name}"
                    linked_names.append(sp.name)
            for sp in sub_pieces:
                if sp.name == "Folha da Porta":
                    if getattr(sp, "ext", None) is None:
                        sp.ext = {}
                    sp.ext["linked_pieces"] = list(linked_names)
                    min_u_f, max_u_f, min_n_f, max_n_f = _local_extents(sp.mesh)
                    hinge_u = min_u_f if flip_x else max_u_f
                    hinge_n = max_n_f if flip_y else min_n_f
                    hp_2d = p_orig_2d + u_dir * hinge_u + n_dir * hinge_n
                    sp.ext["hinge_pivot"] = QVector3D(hp_2d.x(), hp_2d.y(), 0.0)
                    sp.ext["door_angle"] = 95.0 * sx * sy

        elif "porta_aluminio" in igz_path.name:
            for sp in sub_pieces:
                if sp.name == "Agrupar#91":
                    sp.name = "Folha da Porta"
                elif sp.name in ("Agrupar#98", "Marco da Porta"):
                    sp.name = "Marco da Porta"
                elif "Agrupar#6" in sp.name:
                    sp.name = f"Ferragem {sp.name}"
                    linked_names.append(sp.name)
                else:
                    sp.name = f"Fechadura {sp.name}"
                    linked_names.append(sp.name)
            for sp in sub_pieces:
                if sp.name == "Folha da Porta":
                    if getattr(sp, "ext", None) is None:
                        sp.ext = {}
                    sp.ext["linked_pieces"] = list(linked_names)
                    min_u_f, max_u_f, min_n_f, max_n_f = _local_extents(sp.mesh)
                    hinge_u = min_u_f if flip_x else max_u_f
                    hinge_n = max_n_f if flip_y else min_n_f
                    hp_2d = p_orig_2d + u_dir * hinge_u + n_dir * hinge_n
                    sp.ext["hinge_pivot"] = QVector3D(hp_2d.x(), hp_2d.y(), 0.0)
                    sp.ext["door_angle"] = 95.0 * sx * sy

        elif "porta_correr_vidro_4f" in igz_path.name:
            pass
        elif "porta_correr" in igz_path.name:
            for sp in sub_pieces:
                if "Esquerda" in sp.name:
                    sp.name = "Folha de Correr Esquerda"
                    if getattr(sp, "ext", None) is None:
                        sp.ext = {}
                    # Folha esquerda desliza em direção à folha direita (fica face a face / uma atrás da outra)
                    sp.ext["slide_axis"] = QVector3D(u_dir.x() * sx, u_dir.y() * sx, 0.0)
                    sp.ext["slide_distance"] = 0.788
                elif "Direita" in sp.name:
                    sp.name = "Folha de Correr Direita"
                    if getattr(sp, "ext", None) is None:
                        sp.ext = {}
                    # Folha direita desliza em direção à folha esquerda
                    sp.ext["slide_axis"] = QVector3D(-u_dir.x() * sx, -u_dir.y() * sx, 0.0)
                    sp.ext["slide_distance"] = 0.788
                elif "Folha" in sp.name or "Porta" in sp.name:
                    sp.name = "Folha de Correr"
                    if getattr(sp, "ext", None) is None:
                        sp.ext = {}
                    sp.ext["slide_axis"] = QVector3D(u_dir.x() * sx, u_dir.y() * sx, 0.0)
                    sp.ext["slide_distance"] = 0.788
                else:
                    sp.name = "Trilho e Marco Fixo"

        elif "porta_pivotante" in igz_path.name:
            for sp in sub_pieces:
                if "Puxador" in sp.name or "Braçadeira" in sp.name:
                    linked_names.append(sp.name)
            for sp in sub_pieces:
                if "Folha Vidro" in sp.name:
                    if getattr(sp, "ext", None) is None:
                        sp.ext = {}
                    sp.ext["linked_pieces"] = list(linked_names)
                    min_u_f, max_u_f, min_n_f, max_n_f = _local_extents(sp.mesh)
                    hinge_u = (max_u_f - 0.075) if flip_x else (min_u_f + 0.075)
                    hinge_n = max_n_f if flip_y else min_n_f
                    hp_2d = p_orig_2d + u_dir * hinge_u + n_dir * hinge_n
                    sp.ext["hinge_pivot"] = QVector3D(hp_2d.x(), hp_2d.y(), 0.0)
                    sp.ext["door_angle"] = -90.0 * sx * sy

        elif "janela_correr_2f" in igz_path.name:
            # O curso de 0.589 m e a diferenca entre as posicoes iniciais das
            # folhas no template de 1,30 m; escala junto com a largura para que
            # a folha movel continue alinhada a fixa em qualquer medida.
            slide_dist_2f = 0.589 * (target_w / orig_w)
            for sp in sub_pieces:
                if "Esquerda" in sp.name:
                    if getattr(sp, "ext", None) is None:
                        sp.ext = {}
                    sp.ext["slide_axis"] = QVector3D(u_dir.x() * sx, u_dir.y() * sx, 0.0)
                    sp.ext["slide_distance"] = slide_dist_2f
                elif "Direita" in sp.name:
                    if getattr(sp, "ext", None) is None:
                        sp.ext = {}
                    sp.ext["slide_axis"] = QVector3D(-u_dir.x() * sx, -u_dir.y() * sx, 0.0)
                    sp.ext["slide_distance"] = slide_dist_2f

        elif "janela_correr_4f" in igz_path.name:
            for sp in sub_pieces:
                if "Centro Esquerda" in sp.name:
                    if getattr(sp, "ext", None) is None:
                        sp.ext = {}
                    sp.ext["slide_axis"] = QVector3D(-u_dir.x() * sx, -u_dir.y() * sx, 0.0)
                    sp.ext["slide_distance"] = max(0.20, 0.4328 + d_quart)
                elif "Centro Direita" in sp.name:
                    if getattr(sp, "ext", None) is None:
                        sp.ext = {}
                    sp.ext["slide_axis"] = QVector3D(u_dir.x() * sx, u_dir.y() * sx, 0.0)
                    sp.ext["slide_distance"] = max(0.20, 0.4459 + d_quart)

        elif "janela_maximar" in igz_path.name:
            for sp in sub_pieces:
                if "Basculante" in sp.name:
                    if getattr(sp, "ext", None) is None:
                        sp.ext = {}
                    zs = [v.position.z() for v in sp.mesh.vertices]
                    pz = max(zs) if zs else oz + peit_m + 0.55
                    top_verts = [v.position for v in sp.mesh.vertices if abs(v.position.z() - pz) < 0.015]
                    if top_verts:
                        px = sum(v.x() for v in top_verts) / len(top_verts)
                        py = sum(v.y() for v in top_verts) / len(top_verts)
                    else:
                        px, py = ox, oy
                    sp.ext["hinge_pivot"] = QVector3D(px, py, pz)
                    sp.ext["flap_axis"] = QVector3D(u_dir.x(), u_dir.y(), 0.0).normalized()

        elif "janela_vertical" in igz_path.name:
            for sp in sub_pieces:
                if "Basculante" in sp.name:
                    if getattr(sp, "ext", None) is None:
                        sp.ext = {}
                    zs = [v.position.z() for v in sp.mesh.vertices]
                    pz = max(zs) if zs else oz + peit_m + 0.88
                    top_verts = [v.position for v in sp.mesh.vertices if abs(v.position.z() - pz) < 0.015]
                    if top_verts:
                        px = sum(v.x() for v in top_verts) / len(top_verts)
                        py = sum(v.y() for v in top_verts) / len(top_verts)
                    else:
                        px, py = ox, oy
                    sp.ext["hinge_pivot"] = QVector3D(px, py, pz)
                    sp.ext["flap_axis"] = QVector3D(u_dir.x(), u_dir.y(), 0.0).normalized()

        root_name = f"{item_id.replace('_', ' ').title()} {int(largura_mm)}x{int(altura_mm)}"
        root_grp = Group(name=root_name)
        for sp in sub_pieces:
            sp.owner = root_grp
        root_grp.children.extend(sub_pieces)
        root_grp.layer = "ESQUADRIAS"
        if getattr(root_grp, "ext", None) is None:
            root_grp.ext = {}
        from ..domain.schema import set_esquadria_data
        set_esquadria_data(root_grp, {
            "tipo": item_id,
            "largura_mm": float(largura_mm),
            "altura_mm": float(altura_mm),
            "esp_parede_mm": float(esp_parede_mm),
            "peitoril_mm": float(peitoril_mm),
            "offset": offset,
            "rot_z": float(rot_z),
            "lado_abertura": lado_norm,
            "sentido_abertura": sentido_norm,
        })
        return root_grp
