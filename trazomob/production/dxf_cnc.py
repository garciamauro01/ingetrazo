# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Exportador de usinagem e plano de corte em formato DXF CNC 2D.

Gera arquivos DXF R12 limpos e compatíveis com softwares CAM de marcenaria
(WoodWOP, BiesseWorks/bSolid, Maestro, Aspire/Vectric, AutoDesk Fusion, etc.),
organizando furações, contornos e rasgos em layers dedicados padronizados.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from .machining import MachiningOp
from .optimizer import CutPiece, CutSheet


def _layer_name(name: str) -> str:
    """Padroniza nome de layer DXF (maiúsculas, sem espaços)."""
    return (name or "CONTORNO").strip().upper().replace(" ", "_")


# Cores padrão ACI (AutoCAD Color Index)
ACI_CONTORNO = 7   # Branco/Preto
ACI_FURO_FACE = 1  # Vermelho
ACI_FURO_TOPO = 5  # Azul
ACI_RASGO = 3      # Verde
ACI_TEXTO = 2      # Amarelo
ACI_CHAPA = 8      # Cinza


def export_piece_dxf(
    piece: CutPiece | dict[str, Any],
    filepath: str | Path,
    include_labels: bool = True,
) -> int:
    """Exporta a geometria desdobrada de uma única peça com suas usinagens em DXF 2D.

    - Unidades: Milímetros (mm)
    - Origem (0, 0): Canto inferior esquerdo da face principal da peça
    - Layers gerados:
        * CONTORNO (Linhas perimetrais da peça acabada)
        * FURO_D{diam}_P{prof} (Círculos com diâmetro e profundidade explícitos)
        * RASGO_L{larg}_P{prof} (Retângulos do canal de fundo/rebaixo)
        * TEXTO (Identificação da peça e fitas de borda)
    """
    if isinstance(piece, dict):
        comp = float(piece.get("comprimento", 100.0))
        larg = float(piece.get("largura", 100.0))
        esp = float(piece.get("espessura", 15.0))
        nome = str(piece.get("nome", "Peca"))
        mat = str(piece.get("material", "MDF"))
        raw_ops = piece.get("operacoes", [])
    else:
        comp = float(piece.comprimento_final or piece.comprimento)
        larg = float(piece.largura_final or piece.largura)
        esp = float(piece.espessura)
        nome = str(piece.nome)
        mat = str(piece.material)
        raw_ops = piece.operacoes

    ops: list[MachiningOp] = []
    for o in raw_ops:
        if isinstance(o, MachiningOp):
            ops.append(o)
        elif isinstance(o, dict):
            ops.append(MachiningOp.from_dict(o))

    layers: dict[str, int] = {
        "CONTORNO": ACI_CONTORNO,
    }

    # Contorno externo retangular da peça
    lines: list[tuple[str, float, float, float, float]] = [
        ("CONTORNO", 0.0, 0.0, comp, 0.0),
        ("CONTORNO", comp, 0.0, comp, larg),
        ("CONTORNO", comp, larg, 0.0, larg),
        ("CONTORNO", 0.0, larg, 0.0, 0.0),
    ]

    circles: list[tuple[str, float, float, float]] = []

    for op in ops:
        if op.tipo == "furo":
            # Formata layer com diâmetro e profundidade em mm
            # Ex: FURO_D35_P12, FURO_D5_P13, FURO_D8_P30
            d_str = f"D{int(round(op.diametro)) if round(op.diametro, 1).is_integer() else f'{op.diametro:.1f}'.replace('.', '_')}"
            p_str = f"P{int(round(op.profundidade)) if round(op.profundidade, 1).is_integer() else f'{op.profundidade:.1f}'.replace('.', '_')}"
            layer = f"FURO_{d_str}_{p_str}"
            layers[layer] = ACI_FURO_FACE
            circles.append((layer, float(op.x), float(op.y), float(op.diametro) / 2.0))

        elif op.tipo in ("rasgo", "rebaixo"):
            l_str = f"L{int(round(op.largura)) if round(op.largura, 1).is_integer() else f'{op.largura:.1f}'.replace('.', '_')}"
            p_str = f"P{int(round(op.profundidade)) if round(op.profundidade, 1).is_integer() else f'{op.profundidade:.1f}'.replace('.', '_')}"
            layer = f"RASGO_{l_str}_{p_str}"
            layers[layer] = ACI_RASGO

            rx = float(op.x)
            ry = float(op.y)
            rw = float(op.comprimento)
            rh = float(op.largura)
            lines.extend([
                (layer, rx, ry, rx + rw, ry),
                (layer, rx + rw, ry, rx + rw, ry + rh),
                (layer, rx + rw, ry + rh, rx, ry + rh),
                (layer, rx, ry + rh, rx, ry),
            ])

    texts: list[tuple[str, float, float, float, str]] = []
    if include_labels:
        layers["TEXTO"] = ACI_TEXTO
        label_str = f"{nome} [{int(comp)}x{int(larg)}x{int(esp)}mm] - {mat}"
        texts.append(("TEXTO", 15.0, 15.0, 12.0, label_str))

    return _write_dxf_r12(filepath, layers, lines, circles, texts)


def export_cut_sheet_dxf(
    sheet: CutSheet,
    filepath: str | Path,
    include_holes: bool = True,
) -> int:
    """Exporta o mapa de corte completo de uma chapa em DXF (escala 1:1 mm).

    Permite carregar o plano de corte diretamente em seccionadoras CNC / mesas de corte.
    """
    layers: dict[str, int] = {
        "CHAPA_BRUTA": ACI_CHAPA,
        "PECAS_CONTORNO": ACI_CONTORNO,
        "TEXTO": ACI_TEXTO,
    }

    bw = sheet.comprimento_bruto
    bh = sheet.largura_bruto

    lines: list[tuple[str, float, float, float, float]] = [
        # Chapa bruta perimetral
        ("CHAPA_BRUTA", 0.0, 0.0, bw, 0.0),
        ("CHAPA_BRUTA", bw, 0.0, bw, bh),
        ("CHAPA_BRUTA", bw, bh, 0.0, bh),
        ("CHAPA_BRUTA", 0.0, bh, 0.0, 0.0),
    ]

    circles: list[tuple[str, float, float, float]] = []
    texts: list[tuple[str, float, float, float, str]] = []

    # Cabeçalho da chapa
    hdr = f"CHAPA #{sheet.indice} - {sheet.material} ({sheet.espessura}mm) - Aprov: {sheet.aproveitamento_pct}%"
    texts.append(("TEXTO", 20.0, bh + 30.0, 25.0, hdr))

    for p in sheet.pecas:
        px, py = p.x, p.y
        pw, ph = p.w_aloc, p.h_aloc

        # Retângulo da peça alocada
        lines.extend([
            ("PECAS_CONTORNO", px, py, px + pw, py),
            ("PECAS_CONTORNO", px + pw, py, px + pw, py + ph),
            ("PECAS_CONTORNO", px + pw, py + ph, px, py + ph),
            ("PECAS_CONTORNO", px, py + ph, px, py),
        ])

        # Texto identificando a peça
        p_label = f"{p.nome} ({int(p.comprimento)}x{int(p.largura)})"
        texts.append(("TEXTO", px + 8.0, py + 8.0, min(14.0, max(8.0, ph * 0.15)), p_label))

        # Se habilitado, inclui as furações posicionadas na coordenada global da chapa
        if include_holes and p.operacoes:
            for op_raw in p.operacoes:
                op = MachiningOp.from_dict(op_raw) if isinstance(op_raw, dict) else op_raw
                if op.tipo == "furo":
                    d_str = f"D{int(round(op.diametro)) if round(op.diametro, 1).is_integer() else f'{op.diametro:.1f}'.replace('.', '_')}"
                    p_str = f"P{int(round(op.profundidade)) if round(op.profundidade, 1).is_integer() else f'{op.profundidade:.1f}'.replace('.', '_')}"
                    layer = f"FURO_{d_str}_{p_str}"
                    layers[layer] = ACI_FURO_FACE

                    # Se a peça foi rotacionada no plano de corte, inverte as coordenadas
                    if p.rotacionada:
                        ox = px + float(op.y)
                        oy = py + float(op.x)
                    else:
                        ox = px + float(op.x)
                        oy = py + float(op.y)

                    circles.append((layer, ox, oy, float(op.diametro) / 2.0))

    return _write_dxf_r12(filepath, layers, lines, circles, texts)


def _write_dxf_r12(
    filepath: str | Path,
    layers: dict[str, int],
    lines: list[tuple[str, float, float, float, float]],
    circles: list[tuple[str, float, float, float]],
    texts: list[tuple[str, float, float, float, str]],
) -> int:
    """Escreve um arquivo ASCII DXF versão R12 compatível universalmente."""
    total_entities = len(lines) + len(circles) + len(texts)
    with open(filepath, "w", encoding="ascii", errors="replace") as f:
        w = f.write
        # Seção TABLES (Definição de layers)
        w("0\nSECTION\n2\nTABLES\n")
        w(f"0\nTABLE\n2\nLAYER\n70\n{len(layers)}\n")
        for layer_name, aci_color in layers.items():
            clean_name = _layer_name(layer_name)
            w("0\nLAYER\n2\n" f"{clean_name}\n70\n0\n62\n{aci_color}\n6\nCONTINUOUS\n")
        w("0\nENDTAB\n0\nENDSEC\n")

        # Seção ENTITIES
        w("0\nSECTION\n2\nENTITIES\n")

        # Linhas
        for layer, x0, y0, x1, y1 in lines:
            w(f"0\nLINE\n8\n{_layer_name(layer)}\n"
              f"10\n{x0:.4f}\n20\n{y0:.4f}\n30\n0.0\n"
              f"11\n{x1:.4f}\n21\n{y1:.4f}\n31\n0.0\n")

        # Círculos (Furações CNC)
        for layer, cx, cy, radius in circles:
            w(f"0\nCIRCLE\n8\n{_layer_name(layer)}\n"
              f"10\n{cx:.4f}\n20\n{cy:.4f}\n30\n0.0\n"
              f"40\n{radius:.4f}\n")

        # Textos de anotação
        for layer, tx, ty, height, text_str in texts:
            safe_text = str(text_str).replace("\n", " ")
            w(f"0\nTEXT\n8\n{_layer_name(layer)}\n"
              f"10\n{tx:.4f}\n20\n{ty:.4f}\n30\n0.0\n"
              f"40\n{height:.4f}\n"
              f"1\n{safe_text}\n")

        w("0\nENDSEC\n0\nEOF\n")

    return total_entities

