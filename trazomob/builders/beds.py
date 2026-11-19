# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Construtor parametrico 3D de camas planejadas (CamaBuilder).

Modelos implementados:
1. build_cama_gaveteiros: Cama plataforma com gavetoes embutidos (2 a 4 gavetas).
2. build_cama_bau: Cama box com baú fechado e estrado basculante superior.
3. build_cama_cabeceira: Cama com painel de cabeceira traseiro integrado e mesinhas laterais.
4. build_bicama: Cama solteiro com gavetão cama auxiliar deslizante inferior.
5. build_beliche: Beliche planejado com 2 leitos, guarda-corpo de proteção e escada lateral.
"""
from __future__ import annotations

from typing import Any

from PySide6.QtGui import QVector3D

from core.group import Group
from ..builders.chapa_builder import build_chapa_mm
from ..builders.chapa_spec import ChapaSpec, ModuloMaterialContext, PapelChapa
from ..production.machining import MachiningOp


def _board_spec(
    ctx: ModuloMaterialContext | None,
    name: str,
    origin: tuple[float, float, float],
    size: tuple[float, float, float],
    material: str,
    papel: PapelChapa = PapelChapa.PECA_AVULSA,
    material_frentes: str | None = None,
    fita_c1: bool = False,
    fita_c2: bool = False,
    fita_l1: bool = False,
    fita_l2: bool = False,
    **kwargs: Any,
) -> Group:
    """Resolve material/fitas via ChapaSpec e constrói a chapa em mm."""
    if ctx is None:
        ctx = ModuloMaterialContext(
            material_caixa=material,
            material_frentes=material_frentes or material,
        )
    spec = ChapaSpec.resolve(
        nome=name,
        papel=papel,
        ctx=ctx,
        fita_override=(fita_c1, fita_c2, fita_l1, fita_l2),
    )
    return build_chapa_mm(spec, origin, size, **kwargs)


class CamaBuilder:
    """Construtor de camas e beliches de marcenaria sob medida."""

    # -------------------------------------------------------------------------
    # 1. CAMA COM GAVETEIROS LATERAIS
    # -------------------------------------------------------------------------
    @classmethod
    def build_cama_gaveteiros(
        cls,
        largura_mm: float = 1400.0,      # Largura externa (ex: casal ~1400)
        prof_mm: float = 1950.0,  # Profundidade/Comprimento externo (Y)
        altura_mm: float = 400.0,        # Altura do estrado/caixa (Z)
        esp_mm: float = 18.0,      # Espessura das chapas estruturais
        num_gavetoes: int = 4,        # 2 ou 4 gavetas laterais
        lado_gavetas: str = "ambos",  # "ambos", "esquerda", "direita"
        has_estrado: bool = True,
        material: str = "MDF Carvalho",
        material_frentes: str | None = None,
        mat_ctx: ModuloMaterialContext | None = None,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        **params: Any,
    ) -> list[Group]:
        """Cama box plataforma com gavetoes laterais e divisórias estruturais de sustentacao."""
        E = float(esp_mm)
        L = float(largura_mm)
        C = float(prof_mm)
        H = float(altura_mm)
        num_gav = int(params.get("num_gavetas", num_gavetoes))
        ox, oy, oz = (offset[0] * 1000.0, offset[1] * 1000.0, offset[2] * 1000.0)

        groups: list[Group] = []

        # 1. Peseira (frontal Y=0) e Cabeceira da caixa (traseira Y=C-E)
        groups.append(_board_spec(mat_ctx,
            "Cama - Peseira",
            (ox, oy, oz),
            (L, E, H),
            material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True
        ))

        groups.append(_board_spec(mat_ctx,
            "Cama - Cabeceira Caixa",
            (ox, oy + C - E, oz),
            (L, E, H),
            material, fita_c1=True, fita_l1=True, fita_l2=True
        ))

        # 2. Longarinas / Divisória Central de Sustentação do Peso (ao longo de Y)
        dist_y_int = C - 2 * E
        groups.append(_board_spec(mat_ctx,
            "Cama - Longarina Central",
            (ox + (L - E) / 2.0, oy + E, oz),
            (E, dist_y_int, H),
            material, fita_c1=True
        ))

        # Define distribuição de gavetas antes das laterais para estruturar os vãos abertos sem fechamento cego
        lados_gav = []
        if num_gav > 0:
            lado = (lado_gavetas or "ambos").strip().lower()
            if lado not in ("ambos", "esquerda", "direita"):
                lado = "ambos"
            if lado == "ambos":
                # Distribui o total (inclusive ímpar) entre os dois lados, priorizando o direito
                lados_gav = [("dir", (num_gav + 1) // 2), ("esq", num_gav // 2)]
            elif lado == "direita":
                lados_gav = [("dir", num_gav)]
            else:
                lados_gav = [("esq", num_gav)]

        qtd_by_side = {s: q for s, q in lados_gav if q > 0}
        qtd_esq = qtd_by_side.get("esq", 0)
        qtd_dir = qtd_by_side.get("dir", 0)
        prof_gaveta = max(150.0, (L / 2.0) - E - 25.0)
        gap_end = 4.0
        gap_inter = E + 6.0

        # 3. Laterais externas (sólidas quando sem gavetas; nichos estruturados com montantes quando há gavetas)
        if qtd_esq <= 0:
            groups.append(_board_spec(mat_ctx,
                "Cama - Lateral Esquerda",
                (ox, oy + E, oz),
                (E, dist_y_int, H),
                material, fita_c1=True, fita_c2=True
            ))
        else:
            groups.append(_board_spec(mat_ctx,
                "Cama - Rodape Lateral Esq",
                (ox, oy + E, oz),
                (E, dist_y_int, 20.0),
                material, fita_c1=True
            ))
            groups.append(_board_spec(mat_ctx,
                "Cama - Travessa Lateral Esq Sup",
                (ox, oy + E, oz + H - 40.0),
                (E, dist_y_int, 40.0),
                material, fita_c1=True
            ))
            comp_esq = (dist_y_int - 2.0 * gap_end - (qtd_esq - 1) * gap_inter) / float(qtd_esq)
            alt_nicho = max(40.0, H - 60.0)
            prof_nicho = min(prof_gaveta + E, (L / 2.0) - 20.0)
            for i in range(qtd_esq - 1):
                y_div = oy + E + gap_end + (i + 1) * comp_esq + i * gap_inter + 3.0
                groups.append(_board_spec(mat_ctx,
                    f"Cama - Montante Lateral Esq {i+1}",
                    (ox, y_div, oz + 20.0),
                    (prof_nicho, E, alt_nicho),
                    material, fita_c1=True
                ))

        if qtd_dir <= 0:
            groups.append(_board_spec(mat_ctx,
                "Cama - Lateral Direita",
                (ox + L - E, oy + E, oz),
                (E, dist_y_int, H),
                material, fita_c1=True, fita_c2=True
            ))
        else:
            groups.append(_board_spec(mat_ctx,
                "Cama - Rodape Lateral Dir",
                (ox + L - E, oy + E, oz),
                (E, dist_y_int, 20.0),
                material, fita_c1=True
            ))
            groups.append(_board_spec(mat_ctx,
                "Cama - Travessa Lateral Dir Sup",
                (ox + L - E, oy + E, oz + H - 40.0),
                (E, dist_y_int, 40.0),
                material, fita_c1=True
            ))
            comp_dir = (dist_y_int - 2.0 * gap_end - (qtd_dir - 1) * gap_inter) / float(qtd_dir)
            alt_nicho = max(40.0, H - 60.0)
            prof_nicho = min(prof_gaveta + E, (L / 2.0) - 20.0)
            for i in range(qtd_dir - 1):
                y_div = oy + E + gap_end + (i + 1) * comp_dir + i * gap_inter + 3.0
                groups.append(_board_spec(mat_ctx,
                    f"Cama - Montante Lateral Dir {i+1}",
                    (ox + L - prof_nicho, y_div, oz + 20.0),
                    (prof_nicho, E, alt_nicho),
                    material, fita_c1=True
                ))

        # 4. Estrado Superior Ventilado (Chapa de apoio bipartida)
        if has_estrado:
            larg_estrado = (L - 2 * E) / 2.0 - 2.0
            prof_estrado = dist_y_int - 4.0
            alt_estrado = 15.0

            groups.append(_board_spec(mat_ctx,
                "Cama - Estrado Superior Esq",
                (ox + E, oy + E + 2.0, oz + H - alt_estrado),
                (larg_estrado, prof_estrado, alt_estrado),
                material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True
            ))

            groups.append(_board_spec(mat_ctx,
                "Cama - Estrado Superior Dir",
                (ox + (L / 2.0) + 1.0, oy + E + 2.0, oz + H - alt_estrado),
                (larg_estrado, prof_estrado, alt_estrado),
                material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True
            ))

        # 5. Gavetões Laterais Embutidos
        if num_gav > 0:
            mat_frentes = material_frentes or material
            alt_gaveta = max(80.0, H - 64.0)
            slide_dist_m = float(prof_gaveta / 1000.0)

            for side, qtd in lados_gav:
                if qtd <= 0:
                    continue
                side_cap = "Dir" if side == "dir" else "Esq"
                comp_gaveta = (dist_y_int - 2.0 * gap_end - (qtd - 1) * gap_inter) / float(qtd)
                for i in range(qtd):
                    y_pos = oy + E + gap_end + i * (comp_gaveta + gap_inter)
                    if side == "dir":
                        x_pos = ox + L - E
                        eixo = QVector3D(1.0, 0.0, 0.0)
                        x_caixa = ox + L - E - prof_gaveta
                    else:
                        x_pos = ox
                        eixo = QVector3D(-1.0, 0.0, 0.0)
                        x_caixa = ox + E

                    drawer_id = f"gaveta_{side}_{i+1}"
                    fg = _board_spec(
                        mat_ctx,
                        f"Cama - Frente Gaveta {side_cap} {i+1}",
                        (x_pos, y_pos, oz + 22.0),
                        (E, comp_gaveta, alt_gaveta),
                        mat_frentes,
                        papel=PapelChapa.FRENTE_GAVETA,
                        fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                    )
                    CamaBuilder._tag_slide_piece(fg, eixo, slide_dist_m, drawer_id)
                    groups.append(fg)

                    # Caixa interna do gavetão (chapas de 15/6 mm solidárias à frente)
                    comp_caixa = max(80.0, comp_gaveta - 30.0)
                    y_caixa = y_pos + 15.0
                    alt_caixa = max(60.0, alt_gaveta - 40.0)
                    lat1 = _board_spec(
                        mat_ctx,
                        f"Cama - Lat Frontal Gaveta {side_cap} {i+1}",
                        (x_caixa, y_caixa, oz + 28.0),
                        (prof_gaveta, E, alt_caixa),
                        material, fita_c1=True,
                    )
                    CamaBuilder._tag_slide_piece(lat1, eixo, slide_dist_m, drawer_id)
                    groups.append(lat1)

                    lat2 = _board_spec(
                        mat_ctx,
                        f"Cama - Lat Traseira Gaveta {side_cap} {i+1}",
                        (x_caixa, y_caixa + comp_caixa - E, oz + 28.0),
                        (prof_gaveta, E, alt_caixa),
                        material, fita_c1=True,
                    )
                    CamaBuilder._tag_slide_piece(lat2, eixo, slide_dist_m, drawer_id)
                    groups.append(lat2)

                    fundo_g = _board_spec(
                        mat_ctx,
                        f"Cama - Fundo Gaveta {side_cap} {i+1}",
                        (x_caixa, y_caixa + E, oz + 28.0),
                        (prof_gaveta, max(40.0, comp_caixa - 2.0 * E), 6.0),
                        material,
                    )
                    CamaBuilder._tag_slide_piece(fundo_g, eixo, slide_dist_m, drawer_id)
                    groups.append(fundo_g)

        return groups

    @staticmethod
    def _tag_slide_piece(piece, axis: QVector3D, distance_m: float, drawer_id: str) -> None:
        """Registra metadados de deslizamento e vínculo da gaveta/cama auxiliar no dicionário ext."""
        if getattr(piece, "ext", None) is None:
            piece.ext = {}
        piece.ext["slide_axis"] = QVector3D(axis)
        piece.ext["slide_distance"] = float(distance_m)
        piece.ext["drawer_id"] = drawer_id

    # -------------------------------------------------------------------------
    # 2. CAMA BAÚ (BASCULANTE COM PISTÕES)
    # -------------------------------------------------------------------------
    @classmethod
    def build_cama_bau(
        cls,
        largura_mm: float = 1400.0,
        prof_mm: float = 1950.0,
        altura_mm: float = 420.0,
        esp_mm: float = 18.0,
        esp_fundo_mm: float = 6.0,
        material: str = "MDF Carvalho",
        material_frentes: str | None = None,
        mat_ctx: ModuloMaterialContext | None = None,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        **params: Any,
    ) -> list[Group]:
        """Cama box com baú fechado para armazenamento e tampa de estrado articulado."""
        E = float(esp_mm)
        Ef = float(esp_fundo_mm)
        L = float(largura_mm)
        C = float(prof_mm)
        H = float(altura_mm)
        ox, oy, oz = (offset[0] * 1000.0, offset[1] * 1000.0, offset[2] * 1000.0)

        groups: list[Group] = []

        dist_y_int = C - 2 * E
        groups.append(_board_spec(mat_ctx,
            "Cama Baú - Peseira",
            (ox, oy, oz),
            (L, E, H - 25.0),
            material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True
        ))

        groups.append(_board_spec(mat_ctx,
            "Cama Baú - Cabeceira",
            (ox, oy + C - E, oz),
            (L, E, H - 25.0),
            material, fita_c1=True, fita_l1=True, fita_l2=True
        ))

        groups.append(_board_spec(mat_ctx,
            "Cama Baú - Lateral Esq",
            (ox, oy + E, oz),
            (E, dist_y_int, H - 25.0),
            material, fita_c1=True
        ))

        groups.append(_board_spec(mat_ctx,
            "Cama Baú - Lateral Dir",
            (ox + L - E, oy + E, oz),
            (E, dist_y_int, H - 25.0),
            material, fita_c1=True
        ))

        # Fundo interno do Baú
        groups.append(_board_spec(mat_ctx,
            "Cama Baú - Fundo",
            (ox + E, oy + E, oz + 30.0),
            (L - 2 * E, dist_y_int, Ef),
            material
        ))

        # Divisória central longitudinal interna
        groups.append(_board_spec(mat_ctx,
            "Cama Baú - Divisória Central",
            (ox + (L - E) / 2.0, oy + E, oz + 30.0 + Ef),
            (E, dist_y_int, H - 55.0 - Ef),
            material, fita_c1=True
        ))

        # Tampa / Estrado Articulado do Baú
        tampa = _board_spec(mat_ctx,
            "Cama Baú - Tampa Estrado Basculante",
            (ox + 5.0, oy + 5.0, oz + H - 22.0),
            (L - 10.0, C - 10.0, 20.0),
            material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True
        )
        if getattr(tampa, "ext", None) is None:
            tampa.ext = {}
        tampa.ext["door_type"] = "basculante"
        tampa.ext["hinge_side"] = "superior"
        # Pivô junto à cabeceira (+Y) para que os pés (-Y) basculem para cima (+Z)
        tampa.ext["hinge_pivot"] = QVector3D(
            (ox + L * 0.5) / 1000.0,
            (oy + C - 5.0) / 1000.0,
            (oz + H - 2.0) / 1000.0,
        )
        tampa.ext["flap_axis"] = QVector3D(1.0, 0.0, 0.0)
        tampa.ext["flap_max_angle_deg"] = -40.0
        groups.append(tampa)

        return groups

    # -------------------------------------------------------------------------
    # 3. CAMA COM CABECEIRA INTEGRADA E MESINHAS LATERAIS
    # -------------------------------------------------------------------------
    @classmethod
    def build_cama_cabeceira(
        cls,
        largura_mm: float = 2400.0,       # Largura total incluindo painel de cabeceira
        prof_mm: float = 2050.0,   # Comprimento total (Y)
        altura_mm: float = 1100.0,        # Altura do painel de cabeceira (Z)
        larg_cama_mm: float | None = None,   # Largura do leito da cama (None = automático)
        alt_cama_mm: float | None = None,    # Altura do leito da cama (None = 380 mm)
        esp_mm: float = 18.0,
        material: str = "MDF Carvalho",
        material_frentes: str | None = None,
        mat_ctx: ModuloMaterialContext | None = None,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        **params: Any,
    ) -> list[Group]:
        """Cama plataforma integrada com painel de cabeceira estendido e mesinhas suspensas."""
        E = float(esp_mm)
        L_painel = float(largura_mm)
        C_total = float(prof_mm)
        H_painel = float(altura_mm)
        ox, oy, oz = (offset[0] * 1000.0, offset[1] * 1000.0, offset[2] * 1000.0)

        L_leito = float(larg_cama_mm if larg_cama_mm is not None else min(largura_mm * 0.65, 1400.0))
        H_leito = float(alt_cama_mm if alt_cama_mm is not None else 380.0)
        C_leito = C_total - E

        groups: list[Group] = []

        # 1. Painel de Cabeceira Posterior
        groups.append(_board_spec(mat_ctx,
            "Cama - Painel de Cabeceira",
            (ox, oy + C_total - E, oz),
            (L_painel, E, H_painel),
            material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True
        ))

        # 2. Estrutura do Leito Centralizado em X
        x_leito = ox + (L_painel - L_leito) / 2.0
        comp_lat = C_leito - E

        # Peseira frontal
        groups.append(_board_spec(mat_ctx,
            "Cama - Peseira",
            (x_leito, oy, oz),
            (L_leito, E, H_leito),
            material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True
        ))

        # Laterais do leito
        groups.append(_board_spec(mat_ctx,
            "Cama - Lateral Esq",
            (x_leito, oy + E, oz),
            (E, comp_lat, H_leito),
            material, fita_c1=True
        ))

        groups.append(_board_spec(mat_ctx,
            "Cama - Lateral Dir",
            (x_leito + L_leito - E, oy + E, oz),
            (E, comp_lat, H_leito),
            material, fita_c1=True
        ))

        # Longarina e Estrado
        groups.append(_board_spec(mat_ctx,
            "Cama - Longarina Apoio",
            (x_leito + (L_leito - E) / 2.0, oy + E, oz),
            (E, comp_lat, H_leito - 20.0),
            material, fita_c1=True
        ))

        groups.append(_board_spec(mat_ctx,
            "Cama - Estrado",
            (x_leito + E, oy + E, oz + H_leito - 18.0),
            (L_leito - 2 * E, comp_lat, 15.0),
            material, fita_c1=True, fita_c2=True
        ))

        # 3. Mesinhas de Cabeceira Suspensas Laterais (caixas completas com gaveta frontal)
        larg_mesa = max(250.0, ((L_painel - L_leito) / 2.0) - 40.0)
        prof_mesa = 350.0
        alt_mesa = 150.0
        z_mesa = oz + H_leito * 0.75
        y_mesa_front = oy + C_total - E - prof_mesa
        slide_mesa_m = float(max(0.18, (prof_mesa - 50.0) / 1000.0))

        for side_cap, x_mesa in (("Esq", ox + 20.0), ("Dir", ox + L_painel - larg_mesa - 20.0)):
            drawer_id = f"gaveta_mesinha_{side_cap.lower()}"
            groups.append(_board_spec(mat_ctx,
                f"Cama - Tampo Mesinha {side_cap}",
                (x_mesa, y_mesa_front, z_mesa + alt_mesa - E),
                (larg_mesa, prof_mesa, E),
                material, fita_c1=True, fita_l1=True, fita_l2=True
            ))
            groups.append(_board_spec(mat_ctx,
                f"Cama - Base Mesinha {side_cap}",
                (x_mesa, y_mesa_front, z_mesa),
                (larg_mesa, prof_mesa, E),
                material, fita_c1=True, fita_l1=True, fita_l2=True
            ))
            groups.append(_board_spec(mat_ctx,
                f"Cama - Lateral Ext Mesinha {side_cap}",
                (x_mesa, y_mesa_front, z_mesa + E),
                (E, prof_mesa, alt_mesa - 2.0 * E),
                material, fita_c1=True
            ))
            groups.append(_board_spec(mat_ctx,
                f"Cama - Lateral Int Mesinha {side_cap}",
                (x_mesa + larg_mesa - E, y_mesa_front, z_mesa + E),
                (E, prof_mesa, alt_mesa - 2.0 * E),
                material, fita_c1=True
            ))
            fg_m = _board_spec(
                mat_ctx,
                f"Cama - Frente Gaveta Mesinha {side_cap}",
                (x_mesa + 2.0, y_mesa_front - E, z_mesa + 2.0),
                (max(100.0, larg_mesa - 4.0), E, max(60.0, alt_mesa - 4.0)),
                material,
                papel=PapelChapa.FRENTE_GAVETA,
                fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
            )
            CamaBuilder._tag_slide_piece(fg_m, QVector3D(0.0, -1.0, 0.0), slide_mesa_m, drawer_id)
            groups.append(fg_m)

            fundo_m = _board_spec(
                mat_ctx,
                f"Cama - Fundo Gaveta Mesinha {side_cap}",
                (x_mesa + E + 13.0, y_mesa_front + 10.0, z_mesa + E + 6.0),
                (max(80.0, larg_mesa - 2.0 * E - 26.0), max(120.0, prof_mesa - 40.0), 6.0),
                material,
            )
            CamaBuilder._tag_slide_piece(fundo_m, QVector3D(0.0, -1.0, 0.0), slide_mesa_m, drawer_id)
            groups.append(fundo_m)

        return groups

    # -------------------------------------------------------------------------
    # 4. BICAMA (CAMA SOLTEIRO COM CAMA AUXILIAR DESLIZANTE)
    # -------------------------------------------------------------------------
    @classmethod
    def build_bicama(
        cls,
        largura_mm: float = 950.0,
        prof_mm: float = 1950.0,
        altura_mm: float = 500.0,
        esp_mm: float = 18.0,
        material: str = "MDF Carvalho",
        material_frentes: str | None = None,
        mat_ctx: ModuloMaterialContext | None = None,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        **params: Any,
    ) -> list[Group]:
        """Bicama com leito superior de solteiro e cama auxiliar com rodízios deslizante."""
        E = float(esp_mm)
        L = float(largura_mm)
        C = float(prof_mm)
        H = float(altura_mm)
        ox, oy, oz = (offset[0] * 1000.0, offset[1] * 1000.0, offset[2] * 1000.0)

        groups: list[Group] = []

        # 1. Estrutura Cama Principal
        groups.append(_board_spec(mat_ctx,
            "Bicama - Peseira",
            (ox, oy, oz),
            (L, E, H * 0.8),
            material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True
        ))

        groups.append(_board_spec(mat_ctx,
            "Bicama - Cabeceira",
            (ox, oy + C - E, oz),
            (L, E, H),
            material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True
        ))

        dist_y_int = C - 2 * E
        groups.append(_board_spec(mat_ctx,
            "Bicama - Lateral Traseira",
            (ox + L - E, oy + E, oz),
            (E, dist_y_int, H * 0.9),
            material, fita_c1=True
        ))

        alt_vao_aux = 260.0
        alt_barra_sup = H - alt_vao_aux
        groups.append(_board_spec(mat_ctx,
            "Bicama - Barra Frontal Superior",
            (ox, oy + E, oz + alt_vao_aux),
            (E, dist_y_int, alt_barra_sup),
            material, fita_c1=True, fita_c2=True
        ))

        groups.append(_board_spec(mat_ctx,
            "Bicama - Estrado Superior",
            (ox + E, oy + E, oz + H - 50.0),
            (L - 2 * E, dist_y_int, 15.0),
            material, fita_c1=True, fita_c2=True
        ))

        # 2. Cama Auxiliar Deslizante Inferior
        mat_frentes = material_frentes or material
        larg_aux = L - 50.0
        comp_aux = dist_y_int - 20.0
        alt_frente_aux = alt_vao_aux - 15.0

        frente_aux = _board_spec(
            mat_ctx,
            "Bicama - Frente Cama Auxiliar",
            (ox, oy + E + 10.0, oz + 10.0),
            (E, comp_aux, alt_frente_aux),
            mat_frentes,
            papel=PapelChapa.FRENTE_GAVETA,
            fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
        )
        slide_aux_m = float(max(0.25, (larg_aux - 50.0) / 1000.0))
        CamaBuilder._tag_slide_piece(frente_aux, QVector3D(-1.0, 0.0, 0.0), slide_aux_m, "bicama_aux")
        groups.append(frente_aux)

        estrado_aux = _board_spec(mat_ctx,
            "Bicama - Estrado Cama Auxiliar",
            (ox + E, oy + E + 10.0 + E, oz + 45.0),
            (larg_aux, comp_aux - 2 * E, 15.0),
            material, fita_c1=True, fita_c2=True
        )
        CamaBuilder._tag_slide_piece(estrado_aux, QVector3D(-1.0, 0.0, 0.0), slide_aux_m, "bicama_aux")
        groups.append(estrado_aux)

        return groups

    # -------------------------------------------------------------------------
    # 5. BELICHE PLANEJADO
    # -------------------------------------------------------------------------
    @classmethod
    def build_beliche(
        cls,
        largura_mm: float = 950.0,
        prof_mm: float = 2000.0,
        altura_mm: float = 1600.0,
        esp_mm: float = 18.0,
        alt_leito_sup_mm: float | None = None,
        material: str = "MDF Carvalho",
        material_frentes: str | None = None,
        mat_ctx: ModuloMaterialContext | None = None,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        **params: Any,
    ) -> list[Group]:
        """Beliche planejado com 2 leitos, guarda-corpo de proteção no leito superior e escada."""
        E = float(esp_mm)
        L = float(largura_mm)
        C = float(prof_mm)
        H = float(altura_mm)
        H_sup = float(alt_leito_sup_mm if alt_leito_sup_mm is not None else min(altura_mm * 0.75, 1200.0))
        ox, oy, oz = (offset[0] * 1000.0, offset[1] * 1000.0, offset[2] * 1000.0)

        groups: list[Group] = []

        # 1. Peseira e Cabeceira Verticais Altas
        groups.append(_board_spec(mat_ctx,
            "Beliche - Peseira Beliche",
            (ox, oy, oz),
            (L, E, H),
            material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True
        ))

        groups.append(_board_spec(mat_ctx,
            "Beliche - Cabeceira Beliche",
            (ox, oy + C - E, oz),
            (L, E, H),
            material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True
        ))

        dist_y_int = C - 2 * E
        barras_h = 140.0

        # 2. Leito Inferior
        alt_inf = 300.0
        groups.append(_board_spec(mat_ctx,
            "Beliche - Barra Inferior Esq",
            (ox, oy + E, oz + alt_inf - barras_h),
            (E, dist_y_int, barras_h),
            material, fita_c1=True, fita_c2=True
        ))

        groups.append(_board_spec(mat_ctx,
            "Beliche - Barra Inferior Dir",
            (ox + L - E, oy + E, oz + alt_inf - barras_h),
            (E, dist_y_int, barras_h),
            material, fita_c1=True, fita_c2=True
        ))

        groups.append(_board_spec(mat_ctx,
            "Beliche - Estrado Inferior",
            (ox + E, oy + E, oz + alt_inf - 15.0),
            (L - 2 * E, dist_y_int, 15.0),
            material, fita_c1=True, fita_c2=True
        ))

        # 3. Leito Superior
        groups.append(_board_spec(mat_ctx,
            "Beliche - Barra Superior Esq",
            (ox, oy + E, oz + H_sup - barras_h),
            (E, dist_y_int, barras_h),
            material, fita_c1=True, fita_c2=True
        ))

        groups.append(_board_spec(mat_ctx,
            "Beliche - Barra Superior Dir",
            (ox + L - E, oy + E, oz + H_sup - barras_h),
            (E, dist_y_int, barras_h),
            material, fita_c1=True, fita_c2=True
        ))

        groups.append(_board_spec(mat_ctx,
            "Beliche - Estrado Superior",
            (ox + E, oy + E, oz + H_sup - 15.0),
            (L - 2 * E, dist_y_int, 15.0),
            material, fita_c1=True, fita_c2=True
        ))

        # 4. Guarda-corpos de Proteção Superior (frontal parcial + traseiro integral)
        alt_guardacorpo = min(350.0, H - H_sup - 50.0)
        larg_escada = min(400.0, dist_y_int * 0.24)
        y_esc_back = oy + C - E - E
        y_escada = y_esc_back - larg_escada
        y_esc_front = y_escada - E
        comp_guardacorpo = max(300.0, y_esc_front - (oy + E) - 20.0)

        groups.append(_board_spec(mat_ctx,
            "Beliche - Guarda-Corpo Frontal",
            (ox, oy + E, oz + H_sup),
            (E, comp_guardacorpo, alt_guardacorpo),
            material, fita_c1=True, fita_l1=True, fita_l2=True
        ))
        groups.append(_board_spec(mat_ctx,
            "Beliche - Guarda-Corpo Traseiro",
            (ox + L - E, oy + E, oz + H_sup),
            (E, dist_y_int, alt_guardacorpo),
            material, fita_c1=True, fita_l1=True, fita_l2=True
        ))

        # 5. Escada de Acesso (dois montantes completos + degraus dentro do vão do leito)
        groups.append(_board_spec(mat_ctx,
            "Beliche - Montante Escada",
            (ox - 50.0, y_esc_back, oz),
            (60.0, E, H_sup + 200.0),
            material, fita_c1=True, fita_l1=True, fita_l2=True
        ))
        groups.append(_board_spec(mat_ctx,
            "Beliche - Montante Escada Frontal",
            (ox - 50.0, y_esc_front, oz),
            (60.0, E, H_sup + 200.0),
            material, fita_c1=True, fita_l1=True, fita_l2=True
        ))

        num_degraus = 4
        espacamento_degrau = H_sup / (num_degraus + 1)
        for d in range(1, num_degraus + 1):
            groups.append(_board_spec(mat_ctx,
                f"Beliche - Degrau {d}",
                (ox - 50.0, y_escada, oz + d * espacamento_degrau),
                (60.0, larg_escada, E),
                material, fita_c1=True, fita_c2=True
            ))

        return groups

    @classmethod
    def _make_bed_corner_joint(
        cls,
        altura_peca_mm: float,
        esp_chapa_mm: float,
        dispositivo_fixacao: str = "cavilha_soberba",
        usar_minifix: bool = True,
    ) -> tuple[list[MachiningOp], list[MachiningOp]]:
        """Gera furações limpas e proporcionais para junções de canto em camas/rodapés.

        Retorna:
            (ops_lateral, ops_topo)
            - ops_lateral: Furos na face interna da lateral (onde a peça transversal encosta)
            - ops_topo: Furos nos topos da peseira/cabeceira/travessa transversal (esquerda ou direita)
        """
        disp = str(dispositivo_fixacao or "").lower()
        eh_somente_cavilha = disp in ("cavilha", "apenas_cavilha", "apenas_cavilhas", "somente_cavilha")
        eh_somente_parafuso = disp in ("soberba", "apenas_parafuso", "somente_parafuso", "somente_parafusos", "apenas_parafusos")
        eh_minifix = "minifix" in disp and not eh_somente_cavilha and not eh_somente_parafuso
        eh_parafuso = ("parafuso" in disp or "confirmat" in disp or "soberba" in disp) and not eh_somente_cavilha

        ops_lat: list[MachiningOp] = []
        ops_top: list[MachiningOp] = []
        ops_face: list[MachiningOp] = []

        if altura_peca_mm <= 140.0:
            # Rodapé (~100mm): 1 conjunto de fixação completo com cada elemento a 40mm das bordas
            # Borda inferior a 40mm e borda superior a 40mm (altura_peca_mm - 40mm)
            p_inf = 40.0
            p_sup = max(p_inf + 20.0, altura_peca_mm - 40.0)

            if eh_minifix and usar_minifix:
                # Elemento inferior: Cavilha guia | Elemento superior: Minifix
                ops_lat.append(MachiningOp(
                    tipo="furo", face="traseira", x=p_inf, y=esp_chapa_mm / 2.0,
                    diametro=8.0, profundidade=11.0, descricao="Cavilha Guia Rodapé (Ø8mm)",
                ))
                ops_top.append(MachiningOp(
                    tipo="furo", face="topo", x=p_inf, y=esp_chapa_mm / 2.0,
                    diametro=8.0, profundidade=20.0, descricao="Cavilha Guia Topo Rodapé (Ø8mm)",
                ))
                ops_lat.append(MachiningOp(
                    tipo="furo", face="traseira", x=p_sup, y=esp_chapa_mm / 2.0,
                    diametro=5.0, profundidade=11.0, descricao="Pino Minifix Rodapé (Ø5mm)",
                ))
                ops_top.append(MachiningOp(
                    tipo="furo", face="topo", x=p_sup, y=esp_chapa_mm / 2.0,
                    diametro=7.0, profundidade=34.0, descricao="Passagem Haste Minifix Rodapé (Ø7mm)",
                ))
                ops_face.append(MachiningOp(
                    tipo="furo", face="traseira", x=34.0, y=p_sup,
                    diametro=15.0, profundidade=12.5, descricao="Tambor Minifix Rodapé (Ø15mm)",
                ))
            elif eh_somente_cavilha:
                for idx, p in enumerate((p_inf, p_sup), 1):
                    ops_lat.append(MachiningOp(
                        tipo="furo", face="traseira", x=p, y=esp_chapa_mm / 2.0,
                        diametro=8.0, profundidade=11.0, descricao=f"Cavilha Rodapé {idx} (Ø8mm)",
                    ))
                    ops_top.append(MachiningOp(
                        tipo="furo", face="topo", x=p, y=esp_chapa_mm / 2.0,
                        diametro=8.0, profundidade=20.0, descricao=f"Cavilha Topo Rodapé {idx} (Ø8mm)",
                    ))
            elif eh_somente_parafuso:
                for idx, p in enumerate((p_inf, p_sup), 1):
                    ops_lat.append(MachiningOp(
                        tipo="furo", face="traseira", x=p, y=esp_chapa_mm / 2.0,
                        diametro=5.0, profundidade=esp_chapa_mm, descricao=f"Furo Passante Parafuso Rodapé {idx} (Ø5mm)",
                    ))
                    ops_top.append(MachiningOp(
                        tipo="furo", face="topo", x=p, y=esp_chapa_mm / 2.0,
                        diametro=3.5, profundidade=40.0, descricao=f"Furo Guia Parafuso Topo Rodapé {idx} (Ø3.5mm)",
                    ))
            else:
                # Padrão cavilha + parafuso (1 conjunto de fixação):
                # Borda inferior (40mm): Cavilha guia Ø8mm
                # Borda superior (40mm): Parafuso estrutural passante Ø5mm
                ops_lat.append(MachiningOp(
                    tipo="furo", face="traseira", x=p_inf, y=esp_chapa_mm / 2.0,
                    diametro=8.0, profundidade=11.0, descricao="Cavilha Guia Rodapé (Ø8mm)",
                ))
                ops_top.append(MachiningOp(
                    tipo="furo", face="topo", x=p_inf, y=esp_chapa_mm / 2.0,
                    diametro=8.0, profundidade=20.0, descricao="Cavilha Guia Topo Rodapé (Ø8mm)",
                ))
                ops_lat.append(MachiningOp(
                    tipo="furo", face="traseira", x=p_sup, y=esp_chapa_mm / 2.0,
                    diametro=5.0, profundidade=esp_chapa_mm, descricao="Furo Passante Parafuso Rodapé (Ø5mm)",
                ))
                ops_top.append(MachiningOp(
                    tipo="furo", face="topo", x=p_sup, y=esp_chapa_mm / 2.0,
                    diametro=3.5, profundidade=40.0, descricao="Furo Guia Parafuso Topo Rodapé (Ø3.5mm)",
                ))
        else:
            # Peça média/alta (ex: Caixote ~250mm a 300mm, Travessas):
            # Se houver altura_mm suficiente (>= 220mm, ex: caixote da cama de 300mm), gera 2 conjuntos completos
            # (cada conjunto com 1 cavilha guia + 1 parafuso de fixação espaçados entre si por 32mm a 40mm)
            # Afastamento de 40mm das bordas inferior e superior (ao invés de 50mm).
            af_borda = 40.0
            p_inf = min(af_borda, altura_peca_mm * 0.2)
            p_sup = max(p_inf + 64.0, altura_peca_mm - af_borda)

            tem_dois_conjuntos = (altura_peca_mm >= 200.0)

            if tem_dois_conjuntos:
                # 2 conjuntos (inferior e superior):
                # Conjunto 1 (inferior): cavilha em p_inf, parafuso em p_inf + 32mm
                # Conjunto 2 (superior): parafuso em p_sup, cavilha em p_sup - 32mm
                p_inf_cav = p_inf
                p_inf_paraf = p_inf + 32.0
                p_sup_cav = p_sup - 32.0
                p_sup_paraf = p_sup

                if eh_minifix and usar_minifix:
                    for idx, (p_m, p_c) in enumerate([(p_inf_paraf, p_inf_cav), (p_sup_paraf, p_sup_cav)], 1):
                        ops_lat.append(MachiningOp(
                            tipo="furo", face="traseira", x=p_m, y=esp_chapa_mm / 2.0,
                            diametro=5.0, profundidade=11.0, descricao=f"Pino Minifix {idx} (Ø5mm)",
                        ))
                        ops_top.append(MachiningOp(
                            tipo="furo", face="topo", x=p_m, y=esp_chapa_mm / 2.0,
                            diametro=7.0, profundidade=34.0, descricao=f"Passagem Haste Minifix {idx} (Ø7mm)",
                        ))
                        ops_face.append(MachiningOp(
                            tipo="furo", face="traseira", x=34.0, y=p_m,
                            diametro=15.0, profundidade=12.5, descricao=f"Tambor Minifix {idx} (Ø15mm)",
                        ))
                        ops_lat.append(MachiningOp(
                            tipo="furo", face="traseira", x=p_c, y=esp_chapa_mm / 2.0,
                            diametro=8.0, profundidade=11.0, descricao=f"Cavilha Guia {idx} (Ø8mm)",
                        ))
                        ops_top.append(MachiningOp(
                            tipo="furo", face="topo", x=p_c, y=esp_chapa_mm / 2.0,
                            diametro=8.0, profundidade=20.0, descricao=f"Cavilha Guia Topo {idx} (Ø8mm)",
                        ))
                elif eh_somente_cavilha:
                    for idx, p in enumerate([p_inf_cav, p_inf_paraf, p_sup_cav, p_sup_paraf], 1):
                        ops_lat.append(MachiningOp(
                            tipo="furo", face="traseira", x=p, y=esp_chapa_mm / 2.0,
                            diametro=8.0, profundidade=11.0, descricao=f"Cavilha {idx} (Ø8mm)",
                        ))
                        ops_top.append(MachiningOp(
                            tipo="furo", face="topo", x=p, y=esp_chapa_mm / 2.0,
                            diametro=8.0, profundidade=20.0, descricao=f"Cavilha Topo {idx} (Ø8mm)",
                        ))
                elif eh_somente_parafuso:
                    for idx, p in enumerate([p_inf_cav, p_inf_paraf, p_sup_cav, p_sup_paraf], 1):
                        ops_lat.append(MachiningOp(
                            tipo="furo", face="traseira", x=p, y=esp_chapa_mm / 2.0,
                            diametro=5.0, profundidade=esp_chapa_mm, descricao=f"Furo Passante Parafuso {idx} (Ø5mm)",
                        ))
                        ops_top.append(MachiningOp(
                            tipo="furo", face="topo", x=p, y=esp_chapa_mm / 2.0,
                            diametro=3.5, profundidade=40.0, descricao=f"Furo Guia Parafuso Topo {idx} (Ø3.5mm)",
                        ))
                else:
                    # Padrão cavilha + parafuso (2 conjuntos: 2 cavilhas + 2 parafusos):
                    # Conjunto inferior:
                    ops_lat.append(MachiningOp(
                        tipo="furo", face="traseira", x=p_inf_cav, y=esp_chapa_mm / 2.0,
                        diametro=8.0, profundidade=11.0, descricao="Cavilha Guia Inf (Ø8mm)",
                    ))
                    ops_top.append(MachiningOp(
                        tipo="furo", face="topo", x=p_inf_cav, y=esp_chapa_mm / 2.0,
                        diametro=8.0, profundidade=20.0, descricao="Cavilha Guia Topo Inf (Ø8mm)",
                    ))
                    ops_lat.append(MachiningOp(
                        tipo="furo", face="traseira", x=p_inf_paraf, y=esp_chapa_mm / 2.0,
                        diametro=5.0, profundidade=esp_chapa_mm, descricao="Furo Passante Parafuso Inf (Ø5mm)",
                    ))
                    ops_top.append(MachiningOp(
                        tipo="furo", face="topo", x=p_inf_paraf, y=esp_chapa_mm / 2.0,
                        diametro=3.5, profundidade=40.0, descricao="Furo Guia Parafuso Topo Inf (Ø3.5mm)",
                    ))
                    # Conjunto superior:
                    ops_lat.append(MachiningOp(
                        tipo="furo", face="traseira", x=p_sup_cav, y=esp_chapa_mm / 2.0,
                        diametro=8.0, profundidade=11.0, descricao="Cavilha Guia Sup (Ø8mm)",
                    ))
                    ops_top.append(MachiningOp(
                        tipo="furo", face="topo", x=p_sup_cav, y=esp_chapa_mm / 2.0,
                        diametro=8.0, profundidade=20.0, descricao="Cavilha Guia Topo Sup (Ø8mm)",
                    ))
                    ops_lat.append(MachiningOp(
                        tipo="furo", face="traseira", x=p_sup_paraf, y=esp_chapa_mm / 2.0,
                        diametro=5.0, profundidade=esp_chapa_mm, descricao="Furo Passante Parafuso Sup (Ø5mm)",
                    ))
                    ops_top.append(MachiningOp(
                        tipo="furo", face="topo", x=p_sup_paraf, y=esp_chapa_mm / 2.0,
                        diametro=3.5, profundidade=40.0, descricao="Furo Guia Parafuso Topo Sup (Ø3.5mm)",
                    ))
            else:
                # Peças com altura_mm intermediária (< 200mm, ex: travessas estreitas): 1 ponto inf e 1 sup
                p1 = p_inf
                p2 = p_sup
                if eh_minifix and usar_minifix:
                    ops_lat.append(MachiningOp(
                        tipo="furo", face="traseira", x=p1, y=esp_chapa_mm / 2.0,
                        diametro=5.0, profundidade=11.0, descricao="Pino Minifix (Ø5mm)",
                    ))
                    ops_top.append(MachiningOp(
                        tipo="furo", face="topo", x=p1, y=esp_chapa_mm / 2.0,
                        diametro=7.0, profundidade=34.0, descricao="Passagem Haste Minifix (Ø7mm)",
                    ))
                    ops_face.append(MachiningOp(
                        tipo="furo", face="traseira", x=34.0, y=p1,
                        diametro=15.0, profundidade=12.5, descricao="Tambor Minifix (Ø15mm)",
                    ))
                    ops_lat.append(MachiningOp(
                        tipo="furo", face="traseira", x=p2, y=esp_chapa_mm / 2.0,
                        diametro=8.0, profundidade=11.0, descricao="Cavilha Guia (Ø8mm)",
                    ))
                    ops_top.append(MachiningOp(
                        tipo="furo", face="topo", x=p2, y=esp_chapa_mm / 2.0,
                        diametro=8.0, profundidade=20.0, descricao="Cavilha Guia Topo (Ø8mm)",
                    ))
                elif eh_somente_cavilha:
                    for idx, p in enumerate((p1, p2), 1):
                        ops_lat.append(MachiningOp(
                            tipo="furo", face="traseira", x=p, y=esp_chapa_mm / 2.0,
                            diametro=8.0, profundidade=11.0, descricao=f"Cavilha {idx} (Ø8mm)",
                        ))
                        ops_top.append(MachiningOp(
                            tipo="furo", face="topo", x=p, y=esp_chapa_mm / 2.0,
                            diametro=8.0, profundidade=20.0, descricao=f"Cavilha Topo {idx} (Ø8mm)",
                        ))
                elif eh_somente_parafuso:
                    for idx, p in enumerate((p1, p2), 1):
                        ops_lat.append(MachiningOp(
                            tipo="furo", face="traseira", x=p, y=esp_chapa_mm / 2.0,
                            diametro=5.0, profundidade=esp_chapa_mm, descricao=f"Furo Passante Parafuso {idx} (Ø5mm)",
                        ))
                        ops_top.append(MachiningOp(
                            tipo="furo", face="topo", x=p, y=esp_chapa_mm / 2.0,
                            diametro=3.5, profundidade=40.0, descricao=f"Furo Guia Parafuso Topo {idx} (Ø3.5mm)",
                        ))
                else:
                    ops_lat.append(MachiningOp(
                        tipo="furo", face="traseira", x=p1, y=esp_chapa_mm / 2.0,
                        diametro=8.0, profundidade=11.0, descricao="Cavilha Guia (Ø8mm)",
                    ))
                    ops_top.append(MachiningOp(
                        tipo="furo", face="topo", x=p1, y=esp_chapa_mm / 2.0,
                        diametro=8.0, profundidade=20.0, descricao="Cavilha Guia Topo (Ø8mm)",
                    ))
                    ops_lat.append(MachiningOp(
                        tipo="furo", face="traseira", x=p2, y=esp_chapa_mm / 2.0,
                        diametro=5.0, profundidade=esp_chapa_mm, descricao="Furo Passante Parafuso (Ø5mm)",
                    ))
                    ops_top.append(MachiningOp(
                        tipo="furo", face="topo", x=p2, y=esp_chapa_mm / 2.0,
                        diametro=3.5, profundidade=40.0, descricao="Furo Guia Parafuso Topo (Ø3.5mm)",
                    ))

        return ops_lat, ops_top, ops_face

    @classmethod
    def build_cama_colmeia(
        cls,
        largura_mm: float = 1400.0,
        prof_mm: float = 1950.0,
        altura_mm: float = 400.0,
        esp_mm: float = 18.0,
        material: str = "Branco_TX",
        material_frentes: str | None = None,
        mat_ctx: ModuloMaterialContext | None = None,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        rodape_mm: float = 60.0,
        recuo_rodape_mm: float = 100.0,
        num_longarinas: int | None = None,
        num_travessas: int | None = None,
        altura_aba_mm: float = 50.0,
        tipo_apoio: str = "rodape",
        alt_apoio_mm: float = 100.0,
        vao_colmeia_mm: float = 300.0,
        tem_colchao: bool = False,
        gerar_furacao: bool = True,
        dispositivo_fixacao: str = "cavilha_soberba",
        **kwargs: Any,
    ) -> list[Group]:
        """Cama plataforma com base tipo colmeia estrutural, apoio parametrizado e estrado bipartido."""
        from ..production.machining import (
            make_cabinet_joint_holes,
            make_horizontal_board_edge_holes,
        )
        E = float(esp_mm)
        L = float(largura_mm)
        P = float(prof_mm)
        H = float(altura_mm)
        ox, oy, oz = (offset[0] * 1000.0, offset[1] * 1000.0, offset[2] * 1000.0)

        groups: list[Group] = []

        # Determina altura_mm e elevação do apoio
        tipo_ap = str(tipo_apoio).lower()
        if tipo_ap == "chao":
            alt_ap = 0.0
        else:
            alt_ap = float(alt_apoio_mm if alt_apoio_mm is not None else rodape_mm)
            alt_ap = min(max(30.0, alt_ap), max(40.0, H * 0.4))

        tem_chapa_base = alt_ap > 0
        esp_base = E if tem_chapa_base else 0.0
        z_base_bot = oz + alt_ap
        z_base_top = z_base_bot + esp_base

        # Altura do tamponamento externo lateral
        alt_caixote_ext = max(40.0, H - alt_ap - esp_base)
        aba = min(max(0.0, float(altura_aba_mm)), max(0.0, alt_caixote_ext - 2.0 * E))

        # A caixa interna e as travessas de reforço sobem juntas até a face inferior
        # da chapa de apoio do colchão (estrado).
        # A chapa de apoio do colchão passa por cima da caixa interna e travessas,
        # encostando na face interna do tamponamento externo.
        alt_caixa_int = max(20.0, alt_caixote_ext - E - aba)
        alt_grade = alt_caixa_int
        z_estrado_bot = z_base_top + alt_caixa_int
        z_grid_top = z_estrado_bot

        # 1. Apoio Inferior (Rodapé recuado, Pés ou Chão)
        if alt_ap > 0:
            if tipo_ap == "pe":
                # Pés estruturais de madeira/MDF nos 4 cantos e no centro
                dim_pe = max(60.0, 3.0 * E)
                for nome_pe, px, py in (
                    ("Cama Colmeia - Pé Frontal Esquerdo", ox + 50.0, oy + 50.0),
                    ("Cama Colmeia - Pé Frontal Direito", ox + L - 50.0 - dim_pe, oy + 50.0),
                    ("Cama Colmeia - Pé Traseiro Esquerdo", ox + 50.0, oy + P - 50.0 - dim_pe),
                    ("Cama Colmeia - Pé Traseiro Direito", ox + L - 50.0 - dim_pe, oy + P - 50.0 - dim_pe),
                    ("Cama Colmeia - Pé Central", ox + (L - dim_pe) / 2.0, oy + (P - dim_pe) / 2.0),
                ):
                    groups.append(_board_spec(mat_ctx, nome_pe, (px, py, oz), (dim_pe, dim_pe, alt_ap), material))
            else:
                # Rodapé recuado
                recuo = min(max(20.0, float(recuo_rodape_mm or 100.0)), L * 0.25, P * 0.25)
                rod_L = max(3.0 * E, L - 2.0 * recuo)
                rod_P = max(3.0 * E, P - 2.0 * recuo)
                rx = ox + (L - rod_L) / 2.0
                ry = oy + (P - rod_P) / 2.0

                # Operações de furação do rodapé (padrão cavilha + parafuso)
                ops_rod_esq = []
                ops_rod_dir = []
                ops_rod_pes = []
                ops_rod_cab = []
                ops_rod_cen = []

                if gerar_furacao:
                    lat_rod, top_rod, face_rod = cls._make_bed_corner_joint(
                        altura_peca_mm=alt_ap,
                        esp_chapa_mm=E,
                        dispositivo_fixacao=dispositivo_fixacao,
                    )
                    # Rodapés laterais (esp_mm em X, prof_mm ao longo de Y, altura_mm em Z):
                    # No mesh_utils para chapa vertical com esp_mm em X:
                    # cy = oy + x_op_m (posição ao longo do prof_mm Y)
                    # cz = oz + y_op_m (posição ao longo da altura_mm Z)
                    # Portanto: x=posição_em_Y, y=altura_em_Z (o.x do helper é a altura_peca_mm)
                    ops_rod_lat_frente = [
                        MachiningOp(tipo=o.tipo, face="traseira", x=E / 2.0, y=o.x,
                                    diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                        for o in lat_rod
                    ]
                    ops_rod_lat_tras = [
                        MachiningOp(tipo=o.tipo, face="traseira", x=rod_P - (E / 2.0), y=o.x,
                                    diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                        for o in lat_rod
                    ]
                    ops_rod_esq = ops_rod_lat_frente + ops_rod_lat_tras
                    ops_rod_dir = ops_rod_lat_frente + ops_rod_lat_tras

                    # Peseira e cabeceira do rodapé (esp_mm em Y, prof_mm em X, altura_mm em Z):
                    # No mesh_utils para chapa em pé com esp_mm em Y:
                    # cy = oy + y_op_m (ao longo da esp_mm Y) -> y=E/2
                    # cz = oz + x_op_m (ao longo da altura_mm Z) -> x=o.x (altura_mm)
                    top_esq = [
                        MachiningOp(tipo=o.tipo, face="esquerda", x=o.x, y=E / 2.0,
                                    diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                        for o in top_rod
                    ]
                    top_dir = [
                        MachiningOp(tipo=o.tipo, face="direita", x=o.x, y=E / 2.0,
                                    diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                        for o in top_rod
                    ]
                    # Tambores minifix (na face interna traseira da peseira e frontal da cabeceira)
                    face_pes = [
                        MachiningOp(tipo=o.tipo, face="traseira", x=o.x, y=o.y,
                                    diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                        for o in face_rod
                    ] + [
                        MachiningOp(tipo=o.tipo, face="traseira", x=(rod_L - 2.0 * E) - o.x, y=o.y,
                                    diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                        for o in face_rod
                    ]
                    face_cab = [
                        MachiningOp(tipo=o.tipo, face="frontal", x=o.x, y=o.y,
                                    diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                        for o in face_rod
                    ] + [
                        MachiningOp(tipo=o.tipo, face="frontal", x=(rod_L - 2.0 * E) - o.x, y=o.y,
                                    diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                        for o in face_rod
                    ]
                    # Rodapé Central (esp_mm em X, prof_mm ao longo de Y, altura_mm em Z):
                    # Furações de topo frontal (-Y) e topo traseiro (+Y)
                    top_cen_front = [
                        MachiningOp(tipo=o.tipo, face="topo_frontal", x=o.x, y=E / 2.0,
                                    diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                        for o in top_rod
                    ]
                    top_cen_tras = [
                        MachiningOp(tipo=o.tipo, face="topo_traseiro", x=o.x, y=E / 2.0,
                                    diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                        for o in top_rod
                    ]
                    ops_rod_cen = top_cen_front + top_cen_tras

                    # Peseira e cabeceira do rodapé recebem furos na face interna onde o rodapé central encosta
                    x_mid_rod = (rod_L - 2.0 * E) / 2.0
                    face_cen_pes = [
                        MachiningOp(tipo=o.tipo, face="traseira", x=x_mid_rod, y=o.x,
                                    diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                        for o in lat_rod
                    ]
                    face_cen_cab = [
                        MachiningOp(tipo=o.tipo, face="frontal", x=x_mid_rod, y=o.x,
                                    diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                        for o in lat_rod
                    ]
                    ops_rod_pes = top_esq + top_dir + face_pes + face_cen_pes
                    ops_rod_cab = top_esq + top_dir + face_cab + face_cen_cab

                for nome_rod, orig_rod, size_rod, ops_r in (
                    ("Cama Colmeia - Rodapé Esquerdo", (rx, ry, oz), (E, rod_P, alt_ap), ops_rod_esq),
                    ("Cama Colmeia - Rodapé Direito", (rx + rod_L - E, ry, oz), (E, rod_P, alt_ap), ops_rod_dir),
                    ("Cama Colmeia - Rodapé Peseira", (rx + E, ry, oz), (rod_L - 2.0 * E, E, alt_ap), ops_rod_pes),
                    ("Cama Colmeia - Rodapé Cabeceira", (rx + E, ry + rod_P - E, oz), (rod_L - 2.0 * E, E, alt_ap), ops_rod_cab),
                    (
                        "Cama Colmeia - Rodapé Central",
                        (ox + (L - E) / 2.0, ry + E, oz),
                        (E, rod_P - 2.0 * E, alt_ap),
                        ops_rod_cen,
                    ),
                ):
                    groups.append(_board_spec(mat_ctx, nome_rod, orig_rod, size_rod, material, operacoes=ops_r))

        # 2. Chapa de Base Estrutural Intermediária (entre o rodapé e a caixaria/travessas)
        # Encaixada entre os tamponamentos laterais (X = ox + E até ox + L - E)
        larg_base = max(2.0 * E, L - 2.0 * E)
        if tem_chapa_base:
            groups.append(_board_spec(
                mat_ctx,
                "Cama Colmeia - Chapa de Base",
                (ox + E, oy, z_base_bot),
                (larg_base, P, E),
                material,
                fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
            ))

        # 3. Caixote com estrutura dupla completa: Caixa Externa (Tamponamento 4 faces) + Caixa Interna Estrutural
        ops_lat_esq = []
        ops_lat_dir = []
        ops_peseira = []
        ops_cabeceira = []

        if gerar_furacao:
            lat_caixote_ops, top_caixote_ops, face_caixote_ops = cls._make_bed_corner_joint(
                altura_peca_mm=alt_caixa_int,
                esp_chapa_mm=E,
                dispositivo_fixacao=dispositivo_fixacao,
            )
            # As laterais internas recebem furação na face interna onde peseira e cabeceira encostam
            # (esp_mm em X, prof_mm ao longo de Y, altura_mm em Z):
            # No mesh_utils: cy = oy + x_op_m (eixo Y) e cz = oz + y_op_m (eixo Z)
            # 1. Peseira (em y = E/2 das laterais):
            ops_lat_frente = [
                MachiningOp(tipo=o.tipo, face="traseira", x=E / 2.0, y=o.x,
                            diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                for o in lat_caixote_ops
            ]
            # 2. Cabeceira (em y = P - E/2 das laterais):
            ops_lat_tras = [
                MachiningOp(tipo=o.tipo, face="traseira", x=P - (E / 2.0), y=o.x,
                            diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                for o in lat_caixote_ops
            ]
            ops_lat_esq = ops_lat_frente + ops_lat_tras
            ops_lat_dir = ops_lat_frente + ops_lat_tras

            # Peseira e cabeceira (chapas em pé com esp_mm em Y):
            # Furos de topo nas pontas esquerda e direita (x=altura_mm Z, y=esp_mm Y)
            top_esq_caixote = [
                MachiningOp(tipo=o.tipo, face="esquerda", x=o.x, y=E / 2.0,
                            diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                for o in top_caixote_ops
            ]
            top_dir_caixote = [
                MachiningOp(tipo=o.tipo, face="direita", x=o.x, y=E / 2.0,
                            diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                for o in top_caixote_ops
            ]
            # Tambores minifix na face interna da peseira (traseira) e da cabeceira (frontal)
            larg_caixote_int = L - 4.0 * E
            face_pes_caixote = [
                MachiningOp(tipo=o.tipo, face="traseira", x=o.x, y=o.y,
                            diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                for o in face_caixote_ops
            ] + [
                MachiningOp(tipo=o.tipo, face="traseira", x=larg_caixote_int - o.x, y=o.y,
                            diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                for o in face_caixote_ops
            ]
            face_cab_caixote = [
                MachiningOp(tipo=o.tipo, face="frontal", x=o.x, y=o.y,
                            diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                for o in face_caixote_ops
            ] + [
                MachiningOp(tipo=o.tipo, face="frontal", x=larg_caixote_int - o.x, y=o.y,
                            diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                for o in face_caixote_ops
            ]
            ops_peseira = top_esq_caixote + top_dir_caixote + face_pes_caixote
            ops_cabeceira = top_esq_caixote + top_dir_caixote + face_cab_caixote

        # Estrutura Dupla Completa (Caixa Externa de Tamponamento + Caixa Interna Estrutural):
        mat_externo = material_frentes or material

        # A. Caixa Externa (Tamponamento nos 4 lados, iniciando no topo do rodapé Z = z_base_bot)
        # Conforme o projeto:
        # - Tamponamentos Frontal e Traseiro: vão de oy a oy+E e de oy+P-E a oy+P (largura_mm total L cobrindo o contorno)
        # - Tamponamentos Laterais: encaixam entre frontal e traseiro, com prof_mm P - 2*E (de oy+E a oy+P-E)
        alt_tamponamento = alt_caixote_ext + esp_base
        comp_tamp_lat = max(2.0 * E, P - 2.0 * E)
        for nome_ext, orig_ext, size_ext, mat_peca, fc1, fc2, fl1, fl2, ops_ext in (
            ("Cama Colmeia - Tamponamento Lateral Esquerdo", (ox, oy + E, z_base_bot), (E, comp_tamp_lat, alt_tamponamento), mat_externo, True, True, True, True, []),
            ("Cama Colmeia - Tamponamento Lateral Direito", (ox + L - E, oy + E, z_base_bot), (E, comp_tamp_lat, alt_tamponamento), mat_externo, True, True, True, True, []),
            ("Cama Colmeia - Tamponamento Frontal", (ox, oy, z_base_bot), (L, E, alt_tamponamento), mat_externo, True, True, True, True, []),
            ("Cama Colmeia - Tamponamento Traseiro", (ox, oy + P - E, z_base_bot), (L, E, alt_tamponamento), mat_externo, True, True, True, True, []),
            # B. Caixa Interna Estrutural (apoiada na chapa de base Z = z_base_top e indo até a face inferior do estrado)
            ("Cama Colmeia - Lateral Esquerda Interna", (ox + E, oy + E, z_base_top), (E, comp_tamp_lat, alt_caixa_int), material, True, True, False, False, ops_lat_esq),
            ("Cama Colmeia - Lateral Direita Interna", (ox + L - 2.0 * E, oy + E, z_base_top), (E, comp_tamp_lat, alt_caixa_int), material, True, True, False, False, ops_lat_dir),
            ("Cama Colmeia - Peseira", (ox + 2.0 * E, oy + E, z_base_top), (L - 4.0 * E, E, alt_caixa_int), material, True, True, False, False, ops_peseira),
            ("Cama Colmeia - Cabeceira", (ox + 2.0 * E, oy + P - 2.0 * E, z_base_top), (L - 4.0 * E, E, alt_caixa_int), material, True, True, False, False, ops_cabeceira),
        ):
            groups.append(_board_spec(
                mat_ctx, nome_ext, orig_ext, size_ext, mat_peca,
                material_frentes=material_frentes,
                fita_c1=fc1, fita_c2=fc2, fita_l1=fl1, fita_l2=fl2,
                operacoes=ops_ext,
            ))

        # 4. Travessas estruturais internas em sentido único (transversais)
        x_int_ini = ox + 2.0 * E
        y_int_ini = oy + E
        L_int = max(2.0 * E, L - 4.0 * E)
        P_int = max(2.0 * E, P - 2.0 * E)

        max_vao = max(150.0, float(vao_colmeia_mm if vao_colmeia_mm is not None else 300.0))
        n_trav = int(num_travessas) if num_travessas is not None else max(2, min(8, round(P_int / max_vao) - 1))
        cell_len = (P_int - n_trav * E) / (n_trav + 1)

        # Furação nas extremidades das travessas transversais
        ops_travessa = []
        if gerar_furacao:
            _, top_trav_ops, face_trav_ops = cls._make_bed_corner_joint(
                altura_peca_mm=alt_grade,
                esp_chapa_mm=E,
                dispositivo_fixacao=dispositivo_fixacao,
            )
            top_tr_esq = [
                MachiningOp(tipo=o.tipo, face="esquerda", x=o.x, y=E / 2.0,
                            diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                for o in top_trav_ops
            ]
            top_tr_dir = [
                MachiningOp(tipo=o.tipo, face="direita", x=o.x, y=E / 2.0,
                            diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                for o in top_trav_ops
            ]
            # Tambores minifix nas extremidades das travessas transversais (face traseira)
            face_tr = [
                MachiningOp(tipo=o.tipo, face="traseira", x=o.x, y=o.y,
                            diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                for o in face_trav_ops
            ] + [
                MachiningOp(tipo=o.tipo, face="traseira", x=L_int - o.x, y=o.y,
                            diametro=o.diametro, profundidade=o.profundidade, descricao=o.descricao)
                for o in face_trav_ops
            ]
            ops_travessa = top_tr_esq + top_tr_dir + face_tr

        # Travessas transversais inteiriças de lado a lado
        for j in range(n_trav):
            y_trav = y_int_ini + (j + 1) * cell_len + j * E
            groups.append(_board_spec(
                mat_ctx,
                f"Cama - Travessa {j + 1}",
                (x_int_ini, y_trav, z_base_top),
                (L_int, E, alt_grade),
                material,
                operacoes=ops_travessa,
            ))

        # 4. Estrado superior dividido ao meio (cabeceira / peseira)
        # Sobe por cima de toda a caixa interna e travessas, até encostar no tamponamento externo.
        # Em X: de ox + E até ox + L - E (largura_mm = L - 2*E).
        # Em Y: de oy até oy + P (prof_mm total P, dividido ao meio para manuseio).
        larg_estrado = max(2.0 * E, L - 2.0 * E)
        y_meio_estrado = P / 2.0
        for nome_est, y_est, comp_est in (
            ("Cama Colmeia - Estrado Peseira", oy, y_meio_estrado),
            ("Cama Colmeia - Estrado Cabeceira", oy + y_meio_estrado, P - y_meio_estrado),
        ):
            groups.append(_board_spec(
                mat_ctx,
                nome_est,
                (ox + E, y_est, z_grid_top),
                (larg_estrado, comp_est, E),
                material,
                fita_c1=True, fita_c2=True,
            ))

        # 5. Ilustração opcional do colchão no 3D (visual apenas, não gera corte)
        if tem_colchao:
            alt_colchao = 200.0
            z_colchao = z_grid_top + E
            colchao_grp = build_chapa_mm(
                ChapaSpec.resolve(
                    nome="Ilustração Colchão (Apenas 3D)",
                    papel=PapelChapa.PECA_AVULSA,
                    ctx=mat_ctx,
                ),
                (ox + E + 5.0, oy + 5.0, z_colchao),
                (larg_estrado - 10.0, P - 10.0, alt_colchao),
            )
            colchao_grp.ext = colchao_grp.ext or {}
            colchao_grp.ext["ignorar_corte"] = True
            colchao_grp.ext["trazomob"] = {
                "nome": "Ilustração Colchão",
                "kind": "colchao",
                "ignorar_corte": True,
            }
            colchao_grp.ext["trazomob_part"] = {
                "nome": "Ilustração Colchão",
                "kind": "colchao",
                "ignorar_corte": True,
            }
            groups.append(colchao_grp)

        return groups

# Aliases
BedBuilder = CamaBuilder

