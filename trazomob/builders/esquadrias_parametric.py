# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Construtores paramétricos de portas e janelas (sem .igz)."""
from __future__ import annotations

import math
from typing import List, Tuple

from PySide6.QtGui import QVector3D, QMatrix4x4
from core.group import Group
from core.mesh import Mesh

from ..builders.mesh_utils import create_board_group
from .esquadrias_common import CORES


def build_porta_giro(largura_mm: float=800.0, altura_mm: float=2100.0, esp_parede_mm: float=150.0, larg_alisar_mm: float=70.0, esp_folha_mm: float=35.0, esp_marco_mm: float=30.0, folga_mm: float=3.0, lado_abertura: str='right', acabamento: str='madeira_branca', offset: Tuple[float, float, float]=(0.0, 0.0, 0.0), rot_z: float=0.0):
    """Gera uma porta de giro completa com batentes, alisares nos dois lados, folha e maçaneta."""
    ox, oy, oz = offset
    L = max(0.50, largura_mm / 1000.0)
    A = max(1.50, altura_mm / 1000.0)
    P = max(0.08, esp_parede_mm / 1000.0)
    L_al = larg_alisar_mm / 1000.0
    E_al = 0.012  # 12mm espessura do alisar
    E_folha = esp_folha_mm / 1000.0
    E_marco = esp_marco_mm / 1000.0
    cor = CORES.get(acabamento, CORES["madeira_branca"])
    cor_metal = CORES["metal_macaneta"]

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

    return _assemble_esquadria_group(
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


def build_janela_correr(largura_mm: float=1200.0, altura_mm: float=1000.0, esp_parede_mm: float=150.0, peitoril_mm: float=1100.0, acabamento_aluminio: str='aluminio_preto', tipo_vidro: str='vidro_incolor', offset: Tuple[float, float, float]=(0.0, 0.0, 0.0), rot_z: float=0.0):
    """Gera uma janela de correr de 2 folhas com caixilho de alumínio e vidros."""
    ox, oy, oz = offset
    # Aplica a altura do peitoril no Z global
    z_base = oz + (peitoril_mm / 1000.0)

    L = max(0.50, largura_mm / 1000.0)
    A = max(0.40, altura_mm / 1000.0)
    P = max(0.06, esp_parede_mm / 1000.0)
    E_perfil = 0.040  # 40mm largura do perfil de alumínio
    E_caixilho_prof = 0.070  # 70mm profundidade do marco de correr
    cor_alum = CORES.get(acabamento_aluminio, CORES["aluminio_preto"])
    cor_vidro = CORES.get(tipo_vidro, CORES["vidro_incolor"])

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

    _build_folha_janela(pieces, "Folha Esq", x_f1, y_f1, z_f, w_folha, prof_folha, h_f, E_perfil, cor_alum, cor_vidro)

    # Folha 2 (Direita - Trilho Frontal)
    x_f2 = ox + L - E_perfil - w_folha
    y_f2 = y_caixilho + E_caixilho_prof - prof_folha - 0.006

    _build_folha_janela(pieces, "Folha Dir", x_f2, y_f2, z_f, w_folha, prof_folha, h_f, E_perfil, cor_alum, cor_vidro)

    return _assemble_esquadria_group(
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


def build_janela_correr_4folhas(largura_mm: float=1900.0, altura_mm: float=1200.0, esp_parede_mm: float=150.0, peitoril_mm: float=1000.0, acabamento_aluminio: str='aluminio_branco', tipo_vidro: str='vidro_incolor', offset: Tuple[float, float, float]=(0.0, 0.0, 0.0), rot_z: float=0.0):
    """Gera uma janela de correr panorâmica de 4 folhas (2 fixas laterais e 2 móveis centrais)."""
    ox, oy, oz = offset
    z_base = oz + (peitoril_mm / 1000.0)

    L = max(1.20, largura_mm / 1000.0)
    A = max(0.60, altura_mm / 1000.0)
    P = max(0.08, esp_parede_mm / 1000.0)
    E_perfil = 0.045
    E_caixilho_prof = 0.090  # 90mm trilho duplo/triplo
    cor_alum = CORES.get(acabamento_aluminio, CORES["aluminio_branco"])
    cor_vidro = CORES.get(tipo_vidro, CORES["vidro_incolor"])

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
    _build_folha_janela(pieces, "Folha Ext Esq", x_f1, y_f_ext, z_f, w_folha, prof_folha, h_f, E_perfil, cor_alum, cor_vidro)

    # Folha 4 (Lateral Direita Externa)
    x_f4 = ox + L - E_perfil - w_folha
    _build_folha_janela(pieces, "Folha Ext Dir", x_f4, y_f_ext, z_f, w_folha, prof_folha, h_f, E_perfil, cor_alum, cor_vidro)

    # Folha 2 (Centro Esquerda Interna)
    y_f_int = y_caixilho + E_caixilho_prof - prof_folha - 0.008
    x_f2 = x_f1 + w_folha - transpasse
    _build_folha_janela(pieces, "Folha Centro Esq", x_f2, y_f_int, z_f, w_folha, prof_folha, h_f, E_perfil, cor_alum, cor_vidro)

    # Folha 3 (Centro Direita Interna)
    x_f3 = x_f4 - w_folha + transpasse
    _build_folha_janela(pieces, "Folha Centro Dir", x_f3, y_f_int, z_f, w_folha, prof_folha, h_f, E_perfil, cor_alum, cor_vidro)

    return _assemble_esquadria_group(
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


def build_porta_correr_vidro(largura_mm: float=1600.0, altura_mm: float=2100.0, esp_parede_mm: float=150.0, acabamento_aluminio: str='aluminio_preto', tipo_vidro: str='vidro_incolor', offset: Tuple[float, float, float]=(0.0, 0.0, 0.0), rot_z: float=0.0):
    """Gera uma porta de correr de vidro/alumínio (balcão/sacada) de piso a teto."""
    ox, oy, oz = offset
    L = max(1.00, largura_mm / 1000.0)
    A = max(1.80, altura_mm / 1000.0)
    P = max(0.08, esp_parede_mm / 1000.0)
    E_perfil = 0.050
    E_caixilho_prof = 0.100  # 100mm trilho embutido
    cor_alum = CORES.get(acabamento_aluminio, CORES["aluminio_preto"])
    cor_vidro = CORES.get(tipo_vidro, CORES["vidro_incolor"])

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
    _build_folha_janela(pieces, "Folha Sacada Esq", x_f1, y_f1, z_f, w_folha, prof_folha, h_f, E_perfil, cor_alum, cor_vidro)

    # Folha Direita (Móvel/Frontal com Fechadura Concha)
    x_f2 = ox + L - E_perfil - w_folha
    y_f2 = y_caixilho + E_caixilho_prof - prof_folha - 0.010
    _build_folha_janela(pieces, "Folha Sacada Dir", x_f2, y_f2, z_f, w_folha, prof_folha, h_f, E_perfil, cor_alum, cor_vidro)

    # Puxador concha na folha direita
    pieces.append(create_board_group(
        "Fecho Concha Frontal",
        (x_f2 + 0.015, y_f2 + prof_folha, oz + 1.00 - 0.05),
        (0.025, 0.006, 0.100),
        "Metal",
        color=CORES["metal_macaneta"],
    ))

    return _assemble_esquadria_group(
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


def build_porta_pivotante(largura_mm: float=1000.0, altura_mm: float=2150.0, esp_parede_mm: float=150.0, larg_alisar_mm: float=80.0, esp_folha_mm: float=45.0, dist_pivo_mm: float=120.0, acabamento: str='madeira_freijo', offset: Tuple[float, float, float]=(0.0, 0.0, 0.0), rot_z: float=0.0):
    """Gera uma porta pivotante de entrada elegante com pino pivô, frisos e puxador barra inox de 80cm."""
    ox, oy, oz = offset
    L = max(0.80, largura_mm / 1000.0)
    A = max(2.00, altura_mm / 1000.0)
    P = max(0.08, esp_parede_mm / 1000.0)
    L_al = larg_alisar_mm / 1000.0
    E_al = 0.015
    E_marco = 0.035
    E_folha = esp_folha_mm / 1000.0
    cor = CORES.get(acabamento, CORES["madeira_freijo"])
    cor_inox = CORES["aluminio_inox"]

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

    return _assemble_esquadria_group(
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


def build_janela_maximar(largura_mm: float=600.0, altura_mm: float=600.0, esp_parede_mm: float=150.0, peitoril_mm: float=1600.0, acabamento_aluminio: str='aluminio_preto', tipo_vidro: str='vidro_incolor', offset: Tuple[float, float, float]=(0.0, 0.0, 0.0), rot_z: float=0.0):
    """Gera uma janela Maxim-Ar de 1 folha basculante projetante para banheiros e lavabos."""
    ox, oy, oz = offset
    z_base = oz + (peitoril_mm / 1000.0)

    L = max(0.40, largura_mm / 1000.0)
    A = max(0.40, altura_mm / 1000.0)
    P = max(0.06, esp_parede_mm / 1000.0)
    E_perfil = 0.035
    E_caixilho_prof = 0.050
    cor_alum = CORES.get(acabamento_aluminio, CORES["aluminio_preto"])
    cor_vidro = CORES.get(tipo_vidro, CORES["vidro_incolor"])

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

    _build_folha_janela(pieces, "Folha Maxim-Ar", x_f, y_f, z_f, w_f, 0.030, h_f, E_perfil, cor_alum, cor_vidro)

    return _assemble_esquadria_group(
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


def build_janela_vertical_bandeira(largura_mm: float=500.0, altura_mm: float=1200.0, esp_parede_mm: float=150.0, peitoril_mm: float=900.0, acabamento_aluminio: str='aluminio_branco', tipo_vidro: str='vidro_incolor', offset: Tuple[float, float, float]=(0.0, 0.0, 0.0), rot_z: float=0.0):
    """Gera uma janela vertical alta com bandeira fixa superior e folha basculante inferior (estilo Proto Agrupar#16)."""
    ox, oy, oz = offset
    z_base = oz + (peitoril_mm / 1000.0)

    L = max(0.40, largura_mm / 1000.0)
    A = max(0.80, altura_mm / 1000.0)
    P = max(0.06, esp_parede_mm / 1000.0)
    E_perfil = 0.035
    E_caixilho_prof = 0.060
    cor_alum = CORES.get(acabamento_aluminio, CORES["aluminio_branco"])
    cor_vidro = CORES.get(tipo_vidro, CORES["vidro_incolor"])

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

    _build_folha_janela(pieces, "Folha Basculante Inf", x_f, y_f, z_f, w_f, 0.030, h_f, E_perfil, cor_alum, cor_vidro)

    return _assemble_esquadria_group(
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


def _build_folha_janela(pieces: List[Group], prefix: str, x: float, y: float, z: float, w: float, prof: float, h: float, e_quadro: float, cor_alum: Tuple[float, float, float], cor_vidro: Tuple[float, float, float]):
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


def _assemble_esquadria_group(name: str, tipo: str, pieces: List[Group], largura_mm: float, altura_mm: float, esp_parede_mm: float, peitoril_mm: float, offset: Tuple[float, float, float], rot_z: float, lado_abertura: str='direita', sentido_abertura: str='interno'):
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
