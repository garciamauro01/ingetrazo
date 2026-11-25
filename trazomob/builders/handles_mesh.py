# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Utilitários de geração de malhas 3D para chapas de MDF, puxadores e usinagens."""
from __future__ import annotations

from core.mesh import Mesh

from .mesh_utils import _make_box_faces


def _get_puxador_rgb(cor: str | tuple[float, float, float] | None) -> tuple[float, float, float]:
    """Retorna os valores RGB para o acabamento do puxador."""
    if isinstance(cor, (tuple, list)) and len(cor) >= 3:
        return (float(cor[0]), float(cor[1]), float(cor[2]))
    if not cor:
        return (0.15, 0.15, 0.18)  # Preto fosco
    c = str(cor).lower()
    if "inox" in c or "alum" in c or "prata" in c or "cinza" in c:
        return (0.78, 0.80, 0.83)
    if "dourad" in c or "gold" in c or "champ" in c:
        return (0.85, 0.68, 0.38)
    if "cobre" in c or "rose" in c:
        return (0.80, 0.45, 0.35)
    if "branco" in c:
        return (0.96, 0.96, 0.96)
    return (0.15, 0.15, 0.18)


def _build_perfil_geometry_legacy(
    mesh: Mesh,
    origin: tuple[float, float, float],
    size: tuple[float, float, float],
    perfil_modelo: str = "gola",
    eff_pos: str = "topo",
    door_side: str = "single",
    rgb: tuple[float, float, float] = (0.15, 0.15, 0.18),
    desc_m: float = 0.035,
) -> None:
    """Gera a geometria 3D realista dos perfis de alumínio (Rometal/TrazoMob/Leo Madeiras).

    Modelos suportados:
    - 'gola': Perfil Gola Côncavo (RM-030) - cava côncava anatômica, aba de fixação de 15.4mm e lábio superior arredondado.
    - 'facetato': Perfil Facetato / Aba Curva (RM-027) - flange superior de 37mm cobrindo a chapa, aba traseira de 15.5mm e gancho ergonômico frontal curvo de 7.5mm.
    - 'canal_c': Perfil Central Duplo / Canal C (RM-032) - perfil simétrico de 42mm com canal central e duplo lábio em T (superior e inferior).
    - 'sp7000': Perfil Haste Reta / SP-7000 - canal U de abraço de 26mm x 13.5mm e haste reta vertical superior saliente de 41mm.
    """
    ox, oy, oz = origin
    sx, sy, sz = size
    mod = (perfil_modelo or "gola").lower()

    # Tons com sutil contraste de sombra/brilho metálico
    rgb_escuro = (max(0.0, rgb[0] * 0.65), max(0.0, rgb[1] * 0.65), max(0.0, rgb[2] * 0.65))
    rgb_destaque = (min(1.0, rgb[0] * 1.15), min(1.0, rgb[1] * 1.15), min(1.0, rgb[2] * 1.15))

    if eff_pos == "base":
        # Perfil horizontal montado na base inferior (portas de armários aéreos e basculantes)
        if "facetato" in mod or "aba" in mod:
            # RM-027 Facetato na base
            _make_box_faces(mesh, (ox, oy, oz), (sx, sy, desc_m), rgb)
            _make_box_faces(mesh, (ox, oy - 0.015, oz), (sx, sy + 0.015, 0.002), rgb_destaque)
            # Gancho virado para cima para puxar por baixo
            _make_box_faces(mesh, (ox, oy - 0.015, oz + 0.002), (sx, 0.0025, 0.0075), rgb)
            _make_box_faces(mesh, (ox, oy - 0.0125, oz + 0.007), (sx, 0.005, 0.0025), rgb_escuro)
            # Aba traseira de fixação (sobe por trás do MDF)
            _make_box_faces(mesh, (ox, oy + sy - 0.0015, oz + desc_m), (sx, 0.0015, 0.0155), rgb)

        elif "canal" in mod or "canal_c" in mod or "perfil c" in mod:
            # RM-032 Canal C Duplo na base
            _make_box_faces(mesh, (ox, oy, oz), (sx, sy, desc_m), rgb)
            _make_box_faces(mesh, (ox, oy - 0.0163, oz), (sx, 0.0163, 0.003), rgb_destaque)
            _make_box_faces(mesh, (ox, oy - 0.0163, oz + desc_m - 0.003), (sx, 0.0163, 0.003), rgb_destaque)
            _make_box_faces(mesh, (ox, oy - 0.0163, oz), (sx, 0.003, 0.006), rgb)
            _make_box_faces(mesh, (ox, oy - 0.0163, oz + desc_m - 0.006), (sx, 0.003, 0.006), rgb)
            _make_box_faces(mesh, (ox, oy - 0.003, oz + 0.003), (sx, 0.003, max(0.004, desc_m - 0.006)), rgb_escuro)

        elif "sp7000" in mod or "haste" in mod:
            # SP-7000 Haste Reta na base
            _make_box_faces(mesh, (ox, oy, oz), (sx, sy, desc_m), rgb)
            _make_box_faces(mesh, (ox, oy - 0.0035, oz), (sx, 0.0035, desc_m), rgb)
            _make_box_faces(mesh, (ox, oy + sy - 0.002, oz + desc_m), (sx, 0.002, 0.012), rgb)
            # Haste reta se estendendo para baixo além da base
            _make_box_faces(mesh, (ox, oy - 0.0035, oz - 0.018), (sx, 0.005, 0.018), rgb_destaque)
            _make_box_faces(mesh, (ox, oy - 0.0025, oz - 0.020), (sx, 0.003, 0.002), rgb)

        else:
            # RM-030 Gola Côncavo na base (invertido para puxar por baixo)
            _make_box_faces(mesh, (ox, oy, oz), (sx, sy, desc_m), rgb)
            _make_box_faces(mesh, (ox, oy - 0.006, oz + desc_m * 0.4), (sx, 0.006, desc_m * 0.5), rgb_escuro)
            _make_box_faces(mesh, (ox, oy - 0.012, oz + 0.008), (sx, 0.012, desc_m * 0.4), rgb)
            _make_box_faces(mesh, (ox, oy - 0.0175, oz), (sx, 0.0175, 0.008), rgb_destaque)
            _make_box_faces(mesh, (ox, oy - 0.0175, oz + 0.008), (sx, 0.0035, 0.005), rgb)
            _make_box_faces(mesh, (ox, oy + sy - 0.0015, oz + desc_m), (sx, 0.0015, 0.0154), rgb)

    elif eff_pos in ("extensao", "lateral") and door_side not in ("drawer", "flap"):
        # Perfil vertical na lateral da porta (ao longo de Z)
        sides_to_build = ("left", "right") if door_side == "both" else (door_side,)
        for cur_side in sides_to_build:
            is_left_side = cur_side in ("left", "single")
            larg_mdf = max(0.02, sx - desc_m)
            hx = ox + larg_mdf if is_left_side else ox

            if "facetato" in mod or "aba" in mod:
                # RM-027 vertical
                _make_box_faces(mesh, (hx, oy, oz), (desc_m, sy, sz), rgb)
                _make_box_faces(mesh, (hx, oy - 0.015, oz), (desc_m, sy + 0.015, sz), rgb)
                g_x = (hx + desc_m - 0.0025) if is_left_side else hx
                _make_box_faces(mesh, (g_x, oy - 0.015, oz), (0.0025, 0.0075, sz), rgb_destaque)
                fix_x = (hx - 0.0155) if is_left_side else (hx + desc_m)
                _make_box_faces(mesh, (fix_x, oy + sy - 0.0015, oz), (0.0155, 0.0015, sz), rgb)

            elif "canal" in mod or "canal_c" in mod or "perfil c" in mod:
                # RM-032 vertical Canal C
                _make_box_faces(mesh, (hx, oy, oz), (desc_m, sy, sz), rgb)
                _make_box_faces(mesh, (hx, oy - 0.0163, oz), (desc_m, 0.003, sz), rgb_destaque)
                _make_box_faces(mesh, (hx, oy - 0.003, oz), (desc_m, 0.003, sz), rgb_escuro)
                _make_box_faces(mesh, (hx, oy - 0.0163, oz), (0.003, 0.006, sz), rgb)
                _make_box_faces(mesh, (hx + desc_m - 0.003, oy - 0.0163, oz), (0.003, 0.006, sz), rgb)

            elif "sp7000" in mod or "haste" in mod:
                # SP-7000 vertical
                _make_box_faces(mesh, (hx, oy, oz), (desc_m, sy, sz), rgb)
                _make_box_faces(mesh, (hx, oy - 0.0035, oz), (desc_m, 0.0035, sz), rgb)
                rod_x = (hx + desc_m) if is_left_side else (hx - 0.018)
                _make_box_faces(mesh, (rod_x, oy - 0.0035, oz), (0.018, 0.005, sz), rgb_destaque)

            else:
                # RM-030 Gola vertical
                _make_box_faces(mesh, (hx, oy, oz), (desc_m, sy, sz), rgb)
                aba_x = (hx - 0.004) if is_left_side else (hx + desc_m - 0.012)
                _make_box_faces(mesh, (aba_x, oy - 0.012, oz), (0.016, 0.012, sz), rgb)
                _make_box_faces(mesh, (aba_x, oy - 0.0175, oz), (0.006, 0.006, sz), rgb_destaque)

    else:
        # eff_pos == "topo" (padrão balcões e frentes de gaveta)
        hz = oz + sz - desc_m
        if "facetato" in mod or "aba" in mod:
            # RM-027: Facetato / Aba Curva (Imagem 1)
            # Flange superior plana cobrindo o topo da chapa de MDF e avançando 17mm para frente
            _make_box_faces(mesh, (ox, oy - 0.017, oz + sz - 0.002), (sx, sy + 0.017, 0.002), rgb_destaque)
            # Corpo do perfil preenchendo o corte do MDF
            _make_box_faces(mesh, (ox, oy, hz), (sx, sy, desc_m - 0.002), rgb)
            # Gancho frontal curvo descendo 7.5mm
            _make_box_faces(mesh, (ox, oy - 0.017, oz + sz - 0.0075), (sx, 0.0025, 0.0075), rgb)
            # Ponta interna do gancho
            _make_box_faces(mesh, (ox, oy - 0.0145, oz + sz - 0.0075), (sx, 0.004, 0.0025), rgb_escuro)
            # Aba traseira de fixação (15.5mm descendo atrás do MDF)
            _make_box_faces(mesh, (ox, oy + sy - 0.0015, hz - 0.0155), (sx, 0.0015, 0.0155), rgb)

        elif "canal" in mod or "canal_c" in mod or "perfil c" in mod:
            # RM-032: Canal Duplo / Perfil C Simétrico (Imagem 3)
            # Fundo do perfil
            _make_box_faces(mesh, (ox, oy, hz), (sx, sy, desc_m), rgb)
            # Aba horizontal superior (profundidade 16.3mm)
            _make_box_faces(mesh, (ox, oy - 0.0163, oz + sz - 0.003), (sx, 0.0163, 0.003), rgb_destaque)
            # Aba horizontal inferior (profundidade 16.3mm)
            _make_box_faces(mesh, (ox, oy - 0.0163, hz), (sx, 0.0163, 0.003), rgb_destaque)
            # Lábio frontal superior em T (4.7mm)
            _make_box_faces(mesh, (ox, oy - 0.0163, oz + sz - 0.006), (sx, 0.003, 0.006), rgb)
            # Lábio frontal inferior em T (4.7mm)
            _make_box_faces(mesh, (ox, oy - 0.0163, hz), (sx, 0.003, 0.006), rgb)
            # Parede interna do canal (fundo do canal C recuado)
            _make_box_faces(mesh, (ox, oy - 0.003, hz + 0.003), (sx, 0.003, max(0.004, desc_m - 0.006)), rgb_escuro)

        elif "sp7000" in mod or "haste" in mod:
            # SP-7000: Haste Reta Minimalista (Imagem 4)
            # Canal U abraçando o MDF:
            _make_box_faces(mesh, (ox, oy, hz), (sx, sy, desc_m), rgb)
            _make_box_faces(mesh, (ox, oy - 0.0035, hz), (sx, 0.0035, desc_m), rgb)
            _make_box_faces(mesh, (ox, oy + sy - 0.002, hz - 0.010), (sx, 0.002, desc_m + 0.010), rgb)
            # Haste vertical reta de puxar (eleva-se 18mm acima da porta)
            _make_box_faces(mesh, (ox, oy - 0.0035, oz + sz), (sx, 0.005, 0.018), rgb_destaque)
            # Topo arredondado sutil da haste
            _make_box_faces(mesh, (ox, oy - 0.0025, oz + sz + 0.018), (sx, 0.003, 0.002), rgb)

        else:
            # RM-030: Gola Côncavo Clássico (Imagem 2)
            # Corpo do perfil
            _make_box_faces(mesh, (ox, oy, hz), (sx, sy, desc_m), rgb)
            # Cava côncava ergonômica em facetas suaves
            _make_box_faces(mesh, (ox, oy - 0.006, hz + 0.005), (sx, 0.006, desc_m * 0.4), rgb_escuro)
            _make_box_faces(mesh, (ox, oy - 0.012, hz + desc_m * 0.4), (sx, 0.012, desc_m * 0.35), rgb)
            # Lábio superior arredondado da cava (17.5mm de projeção)
            _make_box_faces(mesh, (ox, oy - 0.0175, oz + sz - 0.008), (sx, 0.0175, 0.008), rgb_destaque)
            # Bico descendente do lábio
            _make_box_faces(mesh, (ox, oy - 0.0175, oz + sz - 0.013), (sx, 0.0035, 0.005), rgb)
            # Aba de fixação traseira (15.4mm descendo atrás do MDF)
            _make_box_faces(mesh, (ox, oy + sy - 0.0015, hz - 0.0154), (sx, 0.0015, 0.0154), rgb)


def _build_perfil_geometry(
    mesh: Mesh,
    origin: tuple[float, float, float],
    size: tuple[float, float, float],
    perfil_modelo: str = "gola",
    eff_pos: str = "topo",
    door_side: str = "single",
    rgb: tuple[float, float, float] = (0.15, 0.15, 0.18),
    desc_m: float = 0.035,
) -> None:
    """Extruda a seção 2D do perfil (biblioteca editável em perfis.py) ao longo da porta."""
    from ..profiles.library import extrude_profile, get_profile

    perfil = get_profile(perfil_modelo)
    if door_side == "both" and eff_pos in ("extensao", "lateral"):
        n1 = extrude_profile(mesh, perfil, origin, size, eff_pos, "left", desc_m, rgb)
        n2 = extrude_profile(mesh, perfil, origin, size, eff_pos, "right", desc_m, rgb)
        if (n1 + n2) == 0:
            _build_perfil_geometry_legacy(mesh, origin, size, perfil_modelo, eff_pos, "both", rgb, desc_m)
        return
    n = extrude_profile(mesh, perfil, origin, size, eff_pos, door_side, desc_m, rgb)
    if n == 0:
        _build_perfil_geometry_legacy(mesh, origin, size, perfil_modelo, eff_pos, door_side, rgb, desc_m)


def _add_handle_geometry(
    mesh: Mesh,
    origin: tuple[float, float, float],
    size: tuple[float, float, float],
    puxador_tipo: str = "alca",
    puxador_cor: str | tuple[float, float, float] | None = None,
    door_side: str = "single",  # "left", "right", "single", "both", "drawer", "flap"
    is_upper: bool = False,
    puxador_pos: str = "padrao",
    desconto_perfil_mm: float = 35.0,  # "padrao", "topo", "extensao", "base", "centro"
    perfil_modelo: str = "gola",
):
    """Adiciona a geometria 3D do puxador (alça, perfil, cava, ponto) à malha da porta ou gaveta."""
    tipo = (puxador_tipo or "alca").lower()
    if tipo in ("sem_puxador", "toque", "fecho_toque", "nenhum", "sem"):
        return

    if door_side == "both":
        _add_handle_geometry(
            mesh, origin, size, puxador_tipo=puxador_tipo, puxador_cor=puxador_cor,
            door_side="left", is_upper=is_upper, puxador_pos=puxador_pos,
            desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
        )
        _add_handle_geometry(
            mesh, origin, size, puxador_tipo=puxador_tipo, puxador_cor=puxador_cor,
            door_side="right", is_upper=is_upper, puxador_pos=puxador_pos,
            desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
        )
        return

    pos = (puxador_pos or "padrao").lower()
    ox, oy, oz = origin
    sx, sy, sz = size
    rgb = _get_puxador_rgb(puxador_cor)

    # Determina a orientação vertical efetiva
    eff_pos = pos
    if eff_pos in ("padrao", "auto"):
        if is_upper or door_side == "flap":
            eff_pos = "base"
        elif door_side == "drawer":
            eff_pos = "topo"
        else:
            eff_pos = "extensao" if sz >= 1.2 else "topo"

    if tipo == "perfil":
        desc_m = min(desconto_perfil_mm / 1000.0, max(0.015, (sx if eff_pos in ("extensao", "lateral") else sz) - 0.05))
        _build_perfil_geometry(
            mesh, origin, size,
            perfil_modelo=perfil_modelo,
            eff_pos=eff_pos,
            door_side=door_side,
            rgb=rgb,
            desc_m=desc_m,
        )

    elif tipo == "cava":
        # Cava Usinada 45°
        cor_cava = (max(0.0, rgb[0] * 0.7), max(0.0, rgb[1] * 0.7), max(0.0, rgb[2] * 0.7))
        if eff_pos in ("extensao", "lateral") and door_side not in ("drawer", "flap"):
            alt = max(0.04, sz - 0.04)
            hz = oz + 0.02
            hy = oy - 0.008
            hx = ox + sx - 0.024 if door_side in ("left", "single") else ox + 0.014
            _make_box_faces(mesh, (hx, hy, hz), (0.010, 0.010, alt), cor_cava)
        elif eff_pos == "base":
            larg = max(0.04, sx - 0.024)
            hx = ox + 0.012
            hy = oy - 0.008
            hz = oz + 0.004
            _make_box_faces(mesh, (hx, hy, hz), (larg, 0.010, 0.024), cor_cava)
        else:
            larg = max(0.04, sx - 0.024)
            hx = ox + 0.012
            hy = oy - 0.008
            hz = oz + sz - 0.028
            _make_box_faces(mesh, (hx, hy, hz), (larg, 0.010, 0.024), cor_cava)

    elif tipo == "ponto":
        # Puxador Ponto / Botão Minimalista
        tam = 0.022
        recuo_x = 0.035
        is_yz_plane = (abs(sx) <= 0.035 and abs(sy) > 0.05 and abs(sz) > 0.05)
        if is_yz_plane:
            hx = ox + sx + 0.001
            if door_side in ("left", "single"):
                hy = oy + sy - recuo_x - tam
            else:
                hy = oy + recuo_x
            if eff_pos == "centro":
                hz = oz + (sz - tam) / 2.0
            elif eff_pos == "base":
                hz = oz + 0.04
            elif eff_pos in ("extensao", "lateral"):
                hz = oz + (sz - tam) / 2.0
            else:
                hz = oz + sz - tam - 0.04
        else:
            hy = oy - tam
            if door_side in ("left", "single"):
                hx = ox + sx - recuo_x - tam
            elif door_side == "right":
                hx = ox + recuo_x
            else:
                hx = ox + (sx - tam) / 2.0

            if eff_pos == "centro":
                hz = oz + (sz - tam) / 2.0
                if door_side == "drawer":
                    hx = ox + (sx - tam) / 2.0
            elif eff_pos == "base":
                hz = oz + 0.04
            elif eff_pos in ("extensao", "lateral"):
                hz = oz + (sz - tam) / 2.0
            else:  # "topo"
                hz = oz + sz - tam - 0.04 if door_side != "drawer" else oz + (sz - tam) / 2.0
        _make_box_faces(mesh, (hx, hy, hz), (tam, tam, tam), rgb)

    else:
        # Puxador Alça / Barra Linear
        is_yz_plane = (abs(sx) <= 0.035 and abs(sy) > 0.05 and abs(sz) > 0.05)
        if is_yz_plane:
            # Porta orientada no plano YZ (espessura da chapa em X, largura em Y, altura em Z)
            # A face frontal da porta da Ala Y no Canto L aponta para +X (para fora do balcão)
            alt = min(0.18, sz * 0.3)
            recuo_y = 0.035
            # door_side="left": puxador no lado da quina/livre (+Y); door_side="right": puxador na extremidade frontal (-Y)
            hy = oy + recuo_y if door_side == "right" else oy + sy - recuo_y - 0.012
            hz = oz + sz - alt - 0.05
            hx = ox + sx + 0.001
            _make_box_faces(mesh, (hx, hy, hz), (0.025, 0.010, alt), rgb)
            _make_box_faces(mesh, (hx, hy + 0.001, hz + 0.015), (0.025, 0.012, 0.010), rgb)
            _make_box_faces(mesh, (hx, hy + 0.001, hz + alt - 0.027), (0.025, 0.012, 0.010), rgb)
        elif door_side == "drawer" or eff_pos == "centro":
            comp = min(0.20, sx * 0.65)
            hx = ox + (sx - comp) / 2.0
            hy = oy - 0.025
            hz = oz + (sz / 2.0) - 0.006 if eff_pos == "centro" or door_side == "drawer" else (oz + sz - 0.05 if eff_pos == "topo" else oz + 0.04)
            # Barra horizontal
            _make_box_faces(mesh, (hx, hy, hz), (comp, 0.010, 0.012), rgb)
            _make_box_faces(mesh, (hx + 0.015, oy - 0.025, hz + 0.001), (0.012, 0.025, 0.010), rgb)
            _make_box_faces(mesh, (hx + comp - 0.027, oy - 0.025, hz + 0.001), (0.012, 0.025, 0.010), rgb)
        elif door_side == "flap":
            comp = min(0.24, sx * 0.5)
            hx = ox + (sx - comp) / 2.0
            hy = oy - 0.025
            hz = oz + 0.04 if eff_pos != "topo" else (oz + sz - 0.04)
            _make_box_faces(mesh, (hx, hy, hz), (comp, 0.010, 0.012), rgb)
            _make_box_faces(mesh, (hx + 0.015, oy - 0.025, hz + 0.001), (0.012, 0.025, 0.010), rgb)
            _make_box_faces(mesh, (hx + comp - 0.027, oy - 0.025, hz + 0.001), (0.012, 0.025, 0.010), rgb)
        elif eff_pos in ("extensao", "lateral"):
            # Barra vertical ao longo da extensão da porta
            alt = min(0.35, sz * 0.55)
            recuo_x = 0.035
            hx = ox + sx - recuo_x - 0.012 if door_side in ("left", "single") else ox + recuo_x
            hz = oz + (sz - alt) / 2.0
            hy = oy - 0.025
            _make_box_faces(mesh, (hx, hy, hz), (0.012, 0.010, alt), rgb)
            _make_box_faces(mesh, (hx + 0.001, oy - 0.025, hz + 0.015), (0.010, 0.025, 0.012), rgb)
            _make_box_faces(mesh, (hx + 0.001, oy - 0.025, hz + alt - 0.027), (0.010, 0.025, 0.012), rgb)
        elif eff_pos == "base":
            # Barra horizontal ou vertical na base
            alt = min(0.18, sz * 0.3)
            recuo_x = 0.035
            hx = ox + sx - recuo_x - 0.012 if door_side in ("left", "single") else ox + recuo_x
            hz = oz + 0.04
            hy = oy - 0.025
            _make_box_faces(mesh, (hx, hy, hz), (0.012, 0.010, alt), rgb)
            _make_box_faces(mesh, (hx + 0.001, oy - 0.025, hz + 0.015), (0.010, 0.025, 0.012), rgb)
            _make_box_faces(mesh, (hx + 0.001, oy - 0.025, hz + alt - 0.027), (0.010, 0.025, 0.012), rgb)
        else:
            # Topo (horizontal ou vertical no topo)
            alt = min(0.18, sz * 0.3)
            recuo_x = 0.035
            hx = ox + sx - recuo_x - 0.012 if door_side in ("left", "single") else ox + recuo_x
            hz = oz + sz - alt - 0.05
            hy = oy - 0.025
            _make_box_faces(mesh, (hx, hy, hz), (0.012, 0.010, alt), rgb)
            _make_box_faces(mesh, (hx + 0.001, oy - 0.025, hz + 0.015), (0.010, 0.025, 0.012), rgb)
            _make_box_faces(mesh, (hx + 0.001, oy - 0.025, hz + alt - 0.027), (0.010, 0.025, 0.012), rgb)


