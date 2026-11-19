# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Otimizador paramétrico de plano de corte 2D (Guilhotina / Best-Fit Decreasing).

Agrupa peças por material e espessura, aplicando corte com espaçamento de navalha (kerf),
refilo perimetral da chapa de MDF e respeito rigoroso ao sentido do veio da madeira.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CutPiece:
    """Representa uma peça inserida ou a ser inserida no plano de corte."""
    id: int
    nome: str
    comprimento: float  # Dimensão de corte (X bruto para guilhotina)
    largura: float      # Dimensão de corte (Y bruto para guilhotina)
    espessura: float
    material: str
    comprimento_final: float = 0.0  # Medida acabada do móvel
    largura_final: float = 0.0      # Medida acabada do móvel
    espessura_fita: float = 0.45
    fita_c1: bool = False
    fita_c2: bool = False
    fita_l1: bool = False
    fita_l2: bool = False
    ignorar_veio: bool = False
    quantidade: int = 1
    operacoes: list[dict[str, Any]] = field(default_factory=list)
    # Posição calculada na chapa (em mm)
    x: float = 0.0
    y: float = 0.0
    w_aloc: float = 0.0
    h_aloc: float = 0.0
    rotacionada: bool = False


@dataclass
class SheetConfig:
    """Configurações da chapa bruta e parâmetros de corte."""
    comprimento: float = 2750.0  # X (mm)
    largura: float = 1850.0      # Y (mm)
    espessura_corte: float = 4.0  # Kerf do disco de serra (mm)
    refilo: float = 10.0         # Margem de limpeza nas bordas da chapa (mm)


@dataclass
class CutSheet:
    """Representa uma chapa individual cortada com suas peças e sobras."""
    indice: int
    material: str
    espessura: float
    comprimento_bruto: float
    largura_bruto: float
    pecas: list[CutPiece] = field(default_factory=list)
    sobras: list[tuple[float, float, float, float]] = field(default_factory=list)  # (x, y, w, h)
    area_util_mm2: float = 0.0
    aproveitamento_pct: float = 0.0
    metros_fita: float = 0.0

    @property
    def area_bruta_mm2(self) -> float:
        """Área total da chapa bruta (mm²)."""
        return self.comprimento_bruto * self.largura_bruto

    @property
    def area_sobras_mm2(self) -> float:
        """Área total das sobras aproveitáveis (retalhos >= 200x200mm) (mm²)."""
        return sum(w * h for (_x, _y, w, h) in self.sobras)


@dataclass
class ResumoMaterial:
    """Agregado de aproveitamento para um material/espessura."""
    material: str
    espessura: float
    chapas: int
    pecas: int
    area_bruta_mm2: float
    area_util_mm2: float
    aproveitamento_pct: float
    area_sobras_mm2: float
    sobras: int
    metros_fita: float


@dataclass
class ResumoAproveitamento:
    """Relatório agregado de aproveitamento e sobras do projeto."""
    por_material: dict[str, ResumoMaterial]
    total_chapas: int
    total_pecas: int
    area_bruta_mm2: float
    area_util_mm2: float
    aproveitamento_geral_pct: float
    area_sobras_mm2: float
    total_sobras: int
    metros_fita_total: float
    pecas_nao_alocadas: int
    area_nao_alocada_mm2: float


def resumo_aproveitamento(
    sheets_by_material: dict[str, list[CutSheet]],
    pecas_nao_alocadas: list[CutPiece] | None = None,
) -> ResumoAproveitamento:
    """Agrega estatísticas de aproveitamento e sobras por material e no total.

    Retorna um :class:`ResumoAproveitamento` com:
    - por material: nº de chapas, peças alocadas, área bruta/útil,
      aproveitamento %, área e nº de sobras, metros de fita de borda;
    - totais do projeto: chapas, peças, áreas, aproveitamento geral,
      sobras totais, fita total e peças que não couberam (não alocadas).
    """
    por_material: dict[str, ResumoMaterial] = {}
    total_chapas = 0
    total_pecas = 0
    area_bruta = 0.0
    area_util = 0.0
    area_sobras = 0.0
    total_sobras = 0
    metros_fita = 0.0

    for mat_key, chapas in sheets_by_material.items():
        if not chapas:
            continue
        espessura = chapas[0].espessura
        n_chapas = len(chapas)
        n_pecas = sum(len(c.pecas) for c in chapas)
        ab = sum(c.area_bruta_mm2 for c in chapas)
        au = sum(c.area_util_mm2 for c in chapas)
        asb = sum(c.area_sobras_mm2 for c in chapas)
        nsb = sum(len(c.sobras) for c in chapas)
        mf = sum(c.metros_fita for c in chapas)
        apct = round((au / ab) * 100.0, 1) if ab else 0.0

        por_material[mat_key] = ResumoMaterial(
            material=mat_key,
            espessura=espessura,
            chapas=n_chapas,
            pecas=n_pecas,
            area_bruta_mm2=ab,
            area_util_mm2=au,
            aproveitamento_pct=apct,
            area_sobras_mm2=asb,
            sobras=nsb,
            metros_fita=mf,
        )

        total_chapas += n_chapas
        total_pecas += n_pecas
        area_bruta += ab
        area_util += au
        area_sobras += asb
        total_sobras += nsb
        metros_fita += mf

    apct_geral = round((area_util / area_bruta) * 100.0, 1) if area_bruta else 0.0

    nao_alocadas = pecas_nao_alocadas or []
    area_nao_alocada = sum(p.comprimento * p.largura for p in nao_alocadas)

    return ResumoAproveitamento(
        por_material=por_material,
        total_chapas=total_chapas,
        total_pecas=total_pecas,
        area_bruta_mm2=area_bruta,
        area_util_mm2=area_util,
        aproveitamento_geral_pct=apct_geral,
        area_sobras_mm2=area_sobras,
        total_sobras=total_sobras,
        metros_fita_total=metros_fita,
        pecas_nao_alocadas=len(nao_alocadas),
        area_nao_alocada_mm2=area_nao_alocada,
    )


class GuillotineOptimizer:
    """Algoritmo de corte 2D guilhotinado com suporte a corte de serra e veio."""

    def __init__(self, config: SheetConfig | None = None) -> None:
        self.config = config or SheetConfig()
        #: Peças que não couberam em nenhuma chapa (maiores que a chapa bruta
        #: ou que sobraram após o empacotamento). O chamador deve avisar o
        #: usuário: antes elas eram descartadas silenciosamente.
        self.pecas_nao_alocadas: list[CutPiece] = []

    def optimize(self, raw_parts: list[dict[str, Any]]) -> dict[str, list[CutSheet]]:
        """Otimiza a lista de peças separando por material e espessura."""
        self.pecas_nao_alocadas = []
        # 1. Expande quantidades e agrupa por (material, espessura)
        grupos_material: dict[str, list[CutPiece]] = {}
        for p in raw_parts:
            qtd = int(p.get("quantidade", 1))
            mat = str(p.get("material", "MDF Branco TX 15mm"))
            esp = float(p.get("espessura", 15.0))
            chave = f"{mat} ({int(round(esp))}mm)"

            comp_final = float(p.get("comprimento", 100.0))
            larg_final = float(p.get("largura", 100.0))
            comp_corte = float(p.get("comprimento_corte") or comp_final)
            larg_corte = float(p.get("largura_corte") or larg_final)
            esp_fita = float(p.get("espessura_fita") or 0.45)

            for _ in range(qtd):
                peca = CutPiece(
                    id=int(p.get("id", 0)),
                    nome=str(p.get("nome", "Peça")),
                    comprimento=comp_corte,
                    largura=larg_corte,
                    espessura=esp,
                    material=mat,
                    comprimento_final=comp_final,
                    largura_final=larg_final,
                    espessura_fita=esp_fita,
                    fita_c1=bool(p.get("fita_c1", False)),
                    fita_c2=bool(p.get("fita_c2", False)),
                    fita_l1=bool(p.get("fita_l1", False)),
                    fita_l2=bool(p.get("fita_l2", False)),
                    ignorar_veio=bool(p.get("ignorar_veio", False)),
                    quantidade=1,
                    operacoes=list(p.get("operacoes", [])),
                )
                grupos_material.setdefault(chave, []).append(peca)

        # 2. Otimiza cada grupo de material individualmente
        resultado: dict[str, list[CutSheet]] = {}
        for mat_key, pecas in grupos_material.items():
            resultado[mat_key] = self._pack_material_group(pecas, mat_key)

        return resultado

    def _pack_material_group(self, pecas: list[CutPiece], mat_key: str) -> list[CutSheet]:
        """Empacota peças de um mesmo material nas chapas com algoritmo Maximal Rectangles / Best-Fit."""
        # Ordena peças por maior área e maior dimensão (Heurística Best-Fit Decreasing)
        pecas_ordenadas = sorted(
            pecas,
            key=lambda p: (max(p.comprimento, p.largura), p.comprimento * p.largura),
            reverse=True,
        )

        chapas: list[CutSheet] = []
        pecas_restantes = list(pecas_ordenadas)

        cfg = self.config
        kerf = cfg.espessura_corte
        refilo = cfg.refilo

        # Área útil da chapa bruta descontando refilos
        util_w = cfg.comprimento - 2 * refilo
        util_h = cfg.largura - 2 * refilo

        while pecas_restantes:
            num_chapa = len(chapas) + 1
            chapa = CutSheet(
                indice=num_chapa,
                material=mat_key,
                espessura=pecas_restantes[0].espessura if pecas_restantes else 15.0,
                comprimento_bruto=cfg.comprimento,
                largura_bruto=cfg.largura,
            )

            # Lista de retângulos livres disponíveis na chapa (x, y, w, h)
            # Inicialmente, um grande retângulo útil descontando refilo inicial
            espacos_livres: list[tuple[float, float, float, float]] = [(refilo, refilo, util_w, util_h)]
            nao_couberam: list[CutPiece] = []

            for p in pecas_restantes:
                melhor_espaco_idx = -1
                melhor_rot = False
                menor_sobra_area = float("inf")

                # Testa orientação normal (comprimento no eixo X, largura no Y)
                orientacoes = [(p.comprimento, p.largura, False)]
                # Se veio ignorado ou indiferente, pode girar 90 graus
                if p.ignorar_veio:
                    orientacoes.append((p.largura, p.comprimento, True))

                for pw, ph, rot in orientacoes:
                    for i, (fx, fy, fw, fh) in enumerate(espacos_livres):
                        if pw <= fw + 1e-4 and ph <= fh + 1e-4:
                            sobra_area = (fw * fh) - (pw * ph)
                            # Prefere o espaço mais justo (Best-Fit)
                            if sobra_area < menor_sobra_area:
                                menor_sobra_area = sobra_area
                                melhor_espaco_idx = i
                                melhor_rot = rot
                                melhor_pw, melhor_ph = pw, ph

                if melhor_espaco_idx >= 0:
                    # Encontrou espaço para alocar a peça!
                    fx, fy, fw, fh = espacos_livres.pop(melhor_espaco_idx)
                    p.x = fx
                    p.y = fy
                    p.w_aloc = melhor_pw
                    p.h_aloc = melhor_ph
                    p.rotacionada = melhor_rot
                    chapa.pecas.append(p)
                    chapa.area_util_mm2 += (p.comprimento * p.largura)

                    # Calcula fita de borda
                    if p.fita_c1: chapa.metros_fita += p.comprimento / 1000.0
                    if p.fita_c2: chapa.metros_fita += p.comprimento / 1000.0
                    if p.fita_l1: chapa.metros_fita += p.largura / 1000.0
                    if p.fita_l2: chapa.metros_fita += p.largura / 1000.0

                    # Divisão guilhotina dinâmica do espaço livre restante (Split com serra kerf):
                    # Avalia os dois sentidos de corte (vertical primeiro vs. horizontal primeiro)
                    # e escolhe a partição que preserva o maior retângulo contínuo útil.
                    s1_dir_w = fw - melhor_pw - kerf
                    s1_dir_h = fh
                    s1_cima_w = melhor_pw
                    s1_cima_h = fh - melhor_ph - kerf

                    s2_dir_w = fw - melhor_pw - kerf
                    s2_dir_h = melhor_ph
                    s2_cima_w = fw
                    s2_cima_h = fh - melhor_ph - kerf

                    max_area_s1 = max(s1_dir_w * s1_dir_h, s1_cima_w * s1_cima_h)
                    max_area_s2 = max(s2_dir_w * s2_dir_h, s2_cima_w * s2_cima_h)

                    if max_area_s1 >= max_area_s2:
                        if s1_dir_w > 15.0 and s1_dir_h > 15.0:
                            espacos_livres.append((fx + melhor_pw + kerf, fy, s1_dir_w, s1_dir_h))
                        if s1_cima_w > 15.0 and s1_cima_h > 15.0:
                            espacos_livres.append((fx, fy + melhor_ph + kerf, s1_cima_w, s1_cima_h))
                    else:
                        if s2_dir_w > 15.0 and s2_dir_h > 15.0:
                            espacos_livres.append((fx + melhor_pw + kerf, fy, s2_dir_w, s2_dir_h))
                        if s2_cima_w > 15.0 and s2_cima_h > 15.0:
                            espacos_livres.append((fx, fy + melhor_ph + kerf, s2_cima_w, s2_cima_h))

                    # Fusão de retângulos livres adjacentes (merge) para evitar fragmentação de retalhos
                    self._merge_adjacent_free_spaces(espacos_livres, kerf)

                    # Ordena espaços livres por menor área para manter o empacotamento denso
                    espacos_livres.sort(key=lambda s: s[2] * s[3])
                else:
                    nao_couberam.append(p)

            # Sobras aproveitáveis (retalhos maiores que 200x200mm)
            for s in espacos_livres:
                if s[2] >= 200.0 and s[3] >= 200.0:
                    chapa.sobras.append(s)

            area_bruta = cfg.comprimento * cfg.largura
            chapa.aproveitamento_pct = round((chapa.area_util_mm2 / area_bruta) * 100.0, 1)
            chapas.append(chapa)

            if len(nao_couberam) == len(pecas_restantes):
                # Nenhuma peça restante coube na chapa: não há como alocá-las.
                self.pecas_nao_alocadas.extend(pecas_restantes)
                break
            pecas_restantes = nao_couberam

        return chapas

    @staticmethod
    def _merge_adjacent_free_spaces(
        rects: list[tuple[float, float, float, float]], kerf: float = 4.0
    ) -> None:
        """Funde retângulos livres vizinhos que compartilham bordas colineares.

        Evita que sobras contíguas fiquem fragmentadas em fatias finas,
        permitindo que peças rotacionadas de materiais neutros (como Branco TX)
        encontrem espaço útil contínuo na chapa.
        """
        merged = True
        while merged:
            merged = False
            n = len(rects)
            for i in range(n):
                if merged:
                    break
                x1, y1, w1, h1 = rects[i]
                for j in range(i + 1, n):
                    x2, y2, w2, h2 = rects[j]
                    # Fusão vertical: mesmo X e W, adjacentes em Y (com kerf de tolerância)
                    if abs(x1 - x2) < 1e-3 and abs(w1 - w2) < 1e-3:
                        if abs((y1 + h1 + kerf) - y2) < 1e-3:
                            rects[i] = (x1, y1, w1, h1 + kerf + h2)
                            rects.pop(j)
                            merged = True
                            break
                        elif abs((y2 + h2 + kerf) - y1) < 1e-3:
                            rects[i] = (x1, y2, w1, h2 + kerf + h1)
                            rects.pop(j)
                            merged = True
                            break
                    # Fusão horizontal: mesmo Y e H, adjacentes em X
                    elif abs(y1 - y2) < 1e-3 and abs(h1 - h2) < 1e-3:
                        if abs((x1 + w1 + kerf) - x2) < 1e-3:
                            rects[i] = (x1, y1, w1 + kerf + w2, h1)
                            rects.pop(j)
                            merged = True
                            break
                        elif abs((x2 + w2 + kerf) - x1) < 1e-3:
                            rects[i] = (x2, y1, w2 + kerf + w1, h1)
                            rects.pop(j)
                            merged = True
                            break
