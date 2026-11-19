# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Estrutura e gerador de operações de furação e usinagem para marcenaria (TrazoMob).

Fornece modelos padronizados de operações:
- Furo passante / cego (caneco de dobradiça 35mm, calço, minifix, cavilha, confirmação)
- Canal / rasgo de fundo (fundo rebaixado ou ranhurado de 6mm)
- Furação de corrediças telescópicas e invisíveis (Sistema 32)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

FaceType = Literal["frontal", "traseira", "topo", "base", "esquerda", "direita"]
OpType = Literal["furo", "rasgo", "rebaixo"]


@dataclass
class MachiningOp:
    """Representa uma usinagem ou furação individual em uma chapa de marcenaria."""
    tipo: OpType
    face: FaceType
    x: float             # Distância em mm a partir da origem da face (eixo longitudinal)
    y: float             # Distância em mm a partir da origem da face (eixo transversal)
    diametro: float = 0.0      # Diâmetro em mm (para furos)
    profundidade: float = 0.0  # Profundidade em mm (se 0 ou >= espessura, furo passante)
    largura: float = 0.0       # Largura do rasgo (ex: 6.0 mm para canal de fundo)
    comprimento: float = 0.0   # Comprimento do rasgo
    descricao: str = ""        # Rótulo explicativo (ex: "Caneco Dobradiça 35mm", "Minifix")

    def to_dict(self) -> dict[str, Any]:
        return {
            "tipo": self.tipo,
            "face": self.face,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "diametro": round(self.diametro, 2),
            "profundidade": round(self.profundidade, 2),
            "largura": round(self.largura, 2),
            "comprimento": round(self.comprimento, 2),
            "descricao": self.descricao,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MachiningOp:
        return cls(
            tipo=data.get("tipo", "furo"),
            face=data.get("face", "frontal"),
            x=float(data.get("x", 0.0)),
            y=float(data.get("y", 0.0)),
            diametro=float(data.get("diametro", 0.0)),
            profundidade=float(data.get("profundidade", 0.0)),
            largura=float(data.get("largura", 0.0)),
            comprimento=float(data.get("comprimento", 0.0)),
            descricao=str(data.get("descricao", "")),
        )


def make_hinge_cup_holes(
    altura_porta_mm: float,
    recuo_centro_borda_mm: float = 21.5,
    afastamento_topo_base_mm: float = 100.0,
    face: FaceType = "traseira",
    num_dobradicas: int | None = None,
    lado_dobradica: Literal["esquerda", "direita"] = "esquerda",
    largura_porta_mm: float | None = None,
) -> list[MachiningOp]:
    """Gera furos tipo caneco de dobradiça (Ø 35mm, prof. 12mm) para portas de marcenaria.

    lado_dobradica="esquerda": caneco na borda esquerda da face traseira (x = recuo_centro_borda_mm).
    lado_dobradica="direita": caneco na borda direita da face traseira (x = largura_porta_mm - recuo_centro_borda_mm).
    """
    if num_dobradicas is None:
        if altura_porta_mm < 900:
            n = 2
        elif altura_porta_mm < 1600:
            n = 3
        elif altura_porta_mm < 2100:
            n = 4
        else:
            n = 5
    else:
        n = max(2, num_dobradicas)

    ops: list[MachiningOp] = []
    # Posições ao longo da altura da porta
    y_pos: list[float] = []
    if n == 2:
        y_pos = [afastamento_topo_base_mm, altura_porta_mm - afastamento_topo_base_mm]
    else:
        y_pos = [afastamento_topo_base_mm]
        passo = (altura_porta_mm - 2 * afastamento_topo_base_mm) / (n - 1)
        for i in range(1, n - 1):
            y_pos.append(afastamento_topo_base_mm + i * passo)
        y_pos.append(altura_porta_mm - afastamento_topo_base_mm)

    x_caneco = recuo_centro_borda_mm
    x_parafuso = recuo_centro_borda_mm + 9.5
    if lado_dobradica == "direita" and largura_porta_mm is not None:
        x_caneco = largura_porta_mm - recuo_centro_borda_mm
        x_parafuso = largura_porta_mm - (recuo_centro_borda_mm + 9.5)

    for idx, pos_y in enumerate(y_pos, 1):
        # Furo central caneco Ø 35mm
        ops.append(MachiningOp(
            tipo="furo",
            face=face,
            x=x_caneco,
            y=pos_y,
            diametro=35.0,
            profundidade=12.0,
            descricao=f"Caneco Dobradiça {idx} (Ø35mm)",
        ))
        # Marcação / furos guia rasos para os parafusos da dobradiça (Ø 2.5mm x 2.5mm com entre-furos 45mm padrão)
        ops.append(MachiningOp(
            tipo="furo",
            face=face,
            x=x_parafuso,
            y=pos_y - 22.5,
            diametro=2.5,
            profundidade=2.5,
            descricao=f"Marcação Parafuso Dobradiça {idx}A (Ø2.5mm)",
        ))
        ops.append(MachiningOp(
            tipo="furo",
            face=face,
            x=x_parafuso,
            y=pos_y + 22.5,
            diametro=2.5,
            profundidade=2.5,
            descricao=f"Marcação Parafuso Dobradiça {idx}B (Ø2.5mm)",
        ))

    return ops


def make_hinge_plate_holes(
    posicoes_y_mm: list[float],
    recuo_borda_frontal_mm: float = 37.0,
    face: FaceType = "traseira",
    diametro: float = 2.5,
    profundidade: float = 2.5,
    tipo_fixacao: str = "parafuso",  # "parafuso" (Ø2.5x2.5mm marcação guia) ou "euro" (Ø5.0x11.5mm)
) -> list[MachiningOp]:
    """Gera furos para calço da dobradiça na lateral do móvel (Sistema 32, entre-furos 32mm).

    Suporta:
    - tipo_fixacao='parafuso' (padrão): marcação guia rasa (Ø2.5mm x 2.5mm) para aparafusamento direto.
    - tipo_fixacao='euro': furação técnica (Ø5.0mm x 11.5mm) para bucha plástica ou parafuso Euro.
    """
    if tipo_fixacao == "euro":
        d = 5.0
        p = 11.5
        rotulo = "Calço Dobradiça (Euro Ø5mm)"
    else:
        d = diametro
        p = profundidade
        rotulo = f"Marcação Calço Dobradiça (Ø{d:.1f}mm)"

    ops: list[MachiningOp] = []
    for idx, pos_y in enumerate(posicoes_y_mm, 1):
        ops.append(MachiningOp(
            tipo="furo",
            face=face,
            x=recuo_borda_frontal_mm,
            y=pos_y - 16.0,
            diametro=d,
            profundidade=p,
            descricao=f"{rotulo} {idx}A",
        ))
        ops.append(MachiningOp(
            tipo="furo",
            face=face,
            x=recuo_borda_frontal_mm,
            y=pos_y + 16.0,
            diametro=d,
            profundidade=p,
            descricao=f"{rotulo} {idx}B",
        ))
    return ops


def make_slide_runner_holes(
    alturas_gavetas_mm: list[float],
    profundidade_lateral_mm: float,
    recuo_frontal_mm: float = 37.0,
    face: FaceType = "traseira",
) -> list[MachiningOp]:
    """Gera furações de corrediças telescópicas (linha Sistema 32) na lateral do armário."""
    ops: list[MachiningOp] = []
    for idx, alt_y in enumerate(alturas_gavetas_mm, 1):
        # Primeiro furo (37mm da frente)
        ops.append(MachiningOp(
            tipo="furo",
            face=face,
            x=recuo_frontal_mm,
            y=alt_y,
            diametro=5.0,
            profundidade=12.0,
            descricao=f"Corrediça Gaveta {idx} - Furo Frontal (Ø5mm)",
        ))
        # Segundo furo (sistema 32: múltiplos de 32mm ou ponto intermediário)
        x_inter = recuo_frontal_mm + 128.0
        if x_inter < profundidade_lateral_mm - 50:
            ops.append(MachiningOp(
                tipo="furo",
                face=face,
                x=x_inter,
                y=alt_y,
                diametro=5.0,
                profundidade=12.0,
                descricao=f"Corrediça Gaveta {idx} - Furo Médio (Ø5mm)",
            ))
        # Furo traseiro
        x_tras = profundidade_lateral_mm - 64.0
        if x_tras > x_inter:
            ops.append(MachiningOp(
                tipo="furo",
                face=face,
                x=x_tras,
                y=alt_y,
                diametro=5.0,
                profundidade=12.0,
                descricao=f"Corrediça Gaveta {idx} - Furo Traseiro (Ø5mm)",
            ))
    return ops


def make_cabinet_joint_holes(
    comprimento_junta_mm: float,
    posicao_borda_mm: float = 9.0,
    face: FaceType = "traseira",
    usar_minifix: bool = True,
    afastamento_frontal_mm: float = 50.0,
    afastamento_traseiro_mm: float = 50.0,
    afastamento_cavilha_frontal_mm: float = 100.0,
    afastamento_cavilha_traseiro_mm: float = 100.0,
    dispositivo_fixacao: str = "minifix_cavilha",
    espessura_chapa_mm: float = 15.0,
) -> list[MachiningOp]:
    """Gera furações de junção topo-borda na LATERAL da caixa.

    Na LATERAL da caixa:
    - Se Minifix:
        * Furo para pino/haste: Ø5mm x 11mm de profundidade cega na face interna (50mm das bordas).
    - Se Parafuso (confirmat / parafuso soberbo 4.0 a 5.0mm):
        * Furo passante de passagem do corpo do parafuso: Ø5mm x espessura da lateral (50mm das bordas).
    - Furo para cavilhas (em ambos os casos):
        * Ø8mm x 11mm de profundidade cega exclusivamente na face interna (100mm das bordas).
    """
    ops: list[MachiningOp] = []
    af_f = max(10.0, float(afastamento_frontal_mm if afastamento_frontal_mm is not None else 50.0))
    af_t = max(10.0, float(afastamento_traseiro_mm if afastamento_traseiro_mm is not None else 50.0))
    af_cav_f = max(10.0, float(afastamento_cavilha_frontal_mm if afastamento_cavilha_frontal_mm is not None else 100.0))
    af_cav_t = max(10.0, float(afastamento_cavilha_traseiro_mm if afastamento_cavilha_traseiro_mm is not None else 100.0))

    disp = str(dispositivo_fixacao or "").lower()
    eh_somente_cavilha = (disp in ("cavilha", "apenas_cavilha", "apenas_cavilhas", "somente_cavilha"))
    eh_somente_parafuso = (disp in ("soberba", "apenas_parafuso", "somente_parafuso", "somente_parafusos", "apenas_parafusos"))
    eh_minifix = "minifix" in disp and not eh_somente_cavilha and not eh_somente_parafuso
    eh_parafuso = ("parafuso" in disp or "confirmat" in disp or "soberba" in disp) and not eh_somente_cavilha

    # 1. Elementos de Fixação (Minifix ou Parafuso): 50mm das bordas (não gerados se for apenas cavilha)
    pontos_fixacao = [af_f, max(af_f + 32.0, comprimento_junta_mm - af_t)]
    if comprimento_junta_mm > 650:
        pontos_fixacao.insert(1, (af_f + (comprimento_junta_mm - af_t)) / 2.0)

    for idx, px in enumerate(pontos_fixacao, 1):
        if eh_minifix and usar_minifix:
            # Furo cego na face interna para rosca da haste do Minifix
            ops.append(MachiningOp(
                tipo="furo",
                face=face,
                x=px,
                y=posicao_borda_mm,
                diametro=5.0,
                profundidade=11.0,
                descricao=f"Pino Minifix {idx} (Ø5mm x 11mm)",
            ))
        elif eh_parafuso:
            # Furo passante na lateral para o parafuso atravessar
            ops.append(MachiningOp(
                tipo="furo",
                face=face,
                x=px,
                y=posicao_borda_mm,
                diametro=5.0,
                profundidade=float(espessura_chapa_mm),
                descricao=f"Furo Passante Parafuso {idx} (Ø5mm)",
            ))

    # 2. Cavilhas estruturais: Ø8mm x 11mm cegas, 100mm das bordas (NÃO geradas se for somente parafuso)
    if not eh_somente_parafuso:
        pos_cav_f = min(af_cav_f, comprimento_junta_mm / 2.0 - 15.0)
        pos_cav_t = max(pos_cav_f + 32.0, comprimento_junta_mm - af_cav_t)
        pontos_cavilhas = [pos_cav_f, pos_cav_t]
        if comprimento_junta_mm > 650:
            pontos_cavilhas.insert(1, (pos_cav_f + pos_cav_t) / 2.0)

        for idx, px in enumerate(pontos_cavilhas, 1):
            ops.append(MachiningOp(
                tipo="furo",
                face=face,
                x=px,
                y=posicao_borda_mm,
                diametro=8.0,
                profundidade=11.0,
                descricao=f"Cavilha de Junção {idx} (Ø8mm x 11mm)",
            ))

    return ops


def make_stretcher_joint_holes(
    largura_travessa_mm: float,
    esp_travessa_mm: float = 15.0,
    face: FaceType = "traseira",
    usar_minifix: bool = True,
    comprimento_travessa_mm: float = 0.0,
    eh_travessa: bool = True,
    dispositivo_fixacao: str = "minifix_cavilha",
    posicao_lateral_y_mm: float = 0.0,
    posicao_lateral_z_mm: float = 0.0,
) -> list[MachiningOp]:
    """Gera operações de furação técnica para fixação de travessas estruturais (topo ou laterais).

    Regras de fixação nas pontas da travessa (largura típica 70mm, espessura 15mm/18mm):
    Dois pontos de fixação ao longo da largura da travessa:
    - Ponto 1: a ~18mm da borda frontal da travessa
    - Ponto 2: a ~52mm da borda frontal da travessa (afastamento de 34mm padrão sistema 32)

    Combinações por ponta:
    1. minifix_cavilha: 1 Minifix + 1 Cavilha
       - Travessa: Topos esq/dir com 1 passagem Ø7x34mm + 1 cavilha Ø8x20mm. Face inferior com 1 tambor Ø15x12.5mm a 34mm do topo.
       - Lateral: Face interna com 1 pino Minifix Ø5x11mm + 1 furo de cavilha Ø8x11mm.
    2. parafuso / cavilha_soberba: 1 Parafuso + 1 Cavilha
       - Travessa: Topos esq/dir com 1 furo guia Ø3.5x40mm + 1 cavilha Ø8x20mm.
       - Lateral: 1 furo passante Ø5mm (passagem do parafuso) + 1 cavilha Ø8x11mm.
    3. apenas_parafuso / soberba: 2 Parafusos
       - Travessa: Topos esq/dir com 2 furos guia Ø3.5x40mm (sem cavilhas e sem tambores).
       - Lateral: 2 furos passantes Ø5mm.
    4. apenas_cavilhas / cavilha: 2 Cavilhas
       - Travessa: Topos esq/dir com 2 cavilhas Ø8x20mm (sem parafusos e sem tambores).
       - Lateral: Face interna com 2 cavilhas Ø8x11mm.
    """
    disp = str(dispositivo_fixacao or "").lower()
    eh_somente_cavilha = (disp in ("cavilha", "apenas_cavilha", "apenas_cavilhas", "somente_cavilha"))
    eh_somente_parafuso = (disp in ("soberba", "apenas_parafuso", "somente_parafuso", "somente_parafusos", "apenas_parafusos"))
    eh_minifix = "minifix" in disp and not eh_somente_cavilha and not eh_somente_parafuso
    eh_parafuso = ("parafuso" in disp or "confirmat" in disp or "soberba" in disp) and not eh_somente_cavilha

    # Regra padrão de travessas: afastamento de 25mm de cada face/borda da travessa
    # independente do mecanismo (Minifix, Parafuso ou Cavilha)
    afastamento_borda = 25.0
    if largura_travessa_mm > (2 * afastamento_borda):
        p1 = afastamento_borda
        p2 = largura_travessa_mm - afastamento_borda
    else:
        p1 = max(10.0, largura_travessa_mm * 0.25)
        p2 = max(p1 + 15.0, largura_travessa_mm * 0.75)

    ops: list[MachiningOp] = []

    if eh_travessa:
        # Usinagens na própria travessa:
        # Furos nos topos esquerdo e direito (x=largura, y=espessura), e se minifix, tambor na face inferior
        for topo_face, desc_lado in [("esquerda", "Esq"), ("direita", "Dir")]:
            if eh_minifix:
                # 1 Minifix no ponto 1 + 1 Cavilha no ponto 2
                ops.append(MachiningOp(
                    tipo="furo",
                    face=topo_face,
                    x=p1,
                    y=esp_travessa_mm / 2.0,
                    diametro=7.0,
                    profundidade=34.0,
                    descricao=f"Passagem Haste Minifix Travessa Topo {desc_lado} (Ø7mm x 34mm)",
                ))
                ops.append(MachiningOp(
                    tipo="furo",
                    face=topo_face,
                    x=p2,
                    y=esp_travessa_mm / 2.0,
                    diametro=8.0,
                    profundidade=20.0,
                    descricao=f"Cavilha Travessa Topo {desc_lado} (Ø8mm x 20mm)",
                ))
            elif eh_somente_parafuso:
                # 2 Parafusos
                ops.append(MachiningOp(
                    tipo="furo",
                    face=topo_face,
                    x=p1,
                    y=esp_travessa_mm / 2.0,
                    diametro=3.5,
                    profundidade=40.0,
                    descricao=f"Furo Guia Parafuso 1 Travessa Topo {desc_lado} (Ø3.5mm x 40mm)",
                ))
                ops.append(MachiningOp(
                    tipo="furo",
                    face=topo_face,
                    x=p2,
                    y=esp_travessa_mm / 2.0,
                    diametro=3.5,
                    profundidade=40.0,
                    descricao=f"Furo Guia Parafuso 2 Travessa Topo {desc_lado} (Ø3.5mm x 40mm)",
                ))
            elif eh_somente_cavilha:
                # 2 Cavilhas
                ops.append(MachiningOp(
                    tipo="furo",
                    face=topo_face,
                    x=p1,
                    y=esp_travessa_mm / 2.0,
                    diametro=8.0,
                    profundidade=20.0,
                    descricao=f"Cavilha 1 Travessa Topo {desc_lado} (Ø8mm x 20mm)",
                ))
                ops.append(MachiningOp(
                    tipo="furo",
                    face=topo_face,
                    x=p2,
                    y=esp_travessa_mm / 2.0,
                    diametro=8.0,
                    profundidade=20.0,
                    descricao=f"Cavilha 2 Travessa Topo {desc_lado} (Ø8mm x 20mm)",
                ))
            else:
                # 1 Parafuso + 1 Cavilha (parafuso/cavilha_soberba padrão)
                ops.append(MachiningOp(
                    tipo="furo",
                    face=topo_face,
                    x=p1,
                    y=esp_travessa_mm / 2.0,
                    diametro=3.5,
                    profundidade=40.0,
                    descricao=f"Furo Guia Parafuso Travessa Topo {desc_lado} (Ø3.5mm x 40mm)",
                ))
                ops.append(MachiningOp(
                    tipo="furo",
                    face=topo_face,
                    x=p2,
                    y=esp_travessa_mm / 2.0,
                    diametro=8.0,
                    profundidade=20.0,
                    descricao=f"Cavilha Travessa Topo {desc_lado} (Ø8mm x 20mm)",
                ))

        # Se Minifix, gera os 2 tambores na face interna (face indicada pelo parâmetro face: 'base' quando deitada, 'traseira' quando em pé) a 34mm de cada ponta
        if eh_minifix and comprimento_travessa_mm > 0:
            face_tambor = face if face in ("base", "topo", "traseira", "frontal") else "base"
            ops.append(MachiningOp(
                tipo="furo",
                face=face_tambor,
                x=34.0,
                y=p1,
                diametro=15.0,
                profundidade=12.5,
                descricao="Tambor Minifix Travessa Esq (Ø15mm)",
            ))
            ops.append(MachiningOp(
                tipo="furo",
                face=face_tambor,
                x=comprimento_travessa_mm - 34.0,
                y=p1,
                diametro=15.0,
                profundidade=12.5,
                descricao="Tambor Minifix Travessa Dir (Ø15mm)",
            ))

    else:
        # Usinagens correspondentes na lateral da caixa
        # (posicao_lateral_y_mm é a coordenada Y do início da travessa na lateral,
        # e posicao_lateral_z_mm é a altura Z do centro da travessa)
        py1 = posicao_lateral_y_mm + p1
        py2 = posicao_lateral_y_mm + p2

        if eh_minifix:
            # 1 Pino Minifix (Ø5mm x 11mm cego) no ponto 1 + 1 Cavilha (Ø8mm x 11mm) no ponto 2
            ops.append(MachiningOp(
                tipo="furo",
                face=face,
                x=py1,
                y=posicao_lateral_z_mm,
                diametro=5.0,
                profundidade=11.0,
                descricao="Pino Minifix Junção Travessa (Ø5mm x 11mm)",
            ))
            ops.append(MachiningOp(
                tipo="furo",
                face=face,
                x=py2,
                y=posicao_lateral_z_mm,
                diametro=8.0,
                profundidade=11.0,
                descricao="Cavilha Junção Travessa (Ø8mm x 11mm)",
            ))
        elif eh_somente_parafuso:
            # 2 Parafusos passantes (Ø5mm x espessura)
            prof_passante = max(15.0, esp_travessa_mm)
            ops.append(MachiningOp(
                tipo="furo",
                face=face,
                x=py1,
                y=posicao_lateral_z_mm,
                diametro=5.0,
                profundidade=prof_passante,
                descricao="Furo Parafuso 1 Travessa Passante (Ø5mm)",
            ))
            ops.append(MachiningOp(
                tipo="furo",
                face=face,
                x=py2,
                y=posicao_lateral_z_mm,
                diametro=5.0,
                profundidade=prof_passante,
                descricao="Furo Parafuso 2 Travessa Passante (Ø5mm)",
            ))
        elif eh_somente_cavilha:
            # 2 Cavilhas cegas (Ø8mm x 11mm)
            ops.append(MachiningOp(
                tipo="furo",
                face=face,
                x=py1,
                y=posicao_lateral_z_mm,
                diametro=8.0,
                profundidade=11.0,
                descricao="Cavilha 1 Junção Travessa (Ø8mm x 11mm)",
            ))
            ops.append(MachiningOp(
                tipo="furo",
                face=face,
                x=py2,
                y=posicao_lateral_z_mm,
                diametro=8.0,
                profundidade=11.0,
                descricao="Cavilha 2 Junção Travessa (Ø8mm x 11mm)",
            ))
        else:
            # 1 Parafuso passante + 1 Cavilha cega
            prof_passante = max(15.0, esp_travessa_mm)
            ops.append(MachiningOp(
                tipo="furo",
                face=face,
                x=py1,
                y=posicao_lateral_z_mm,
                diametro=5.0,
                profundidade=prof_passante,
                descricao="Furo Parafuso Travessa Passante (Ø5mm)",
            ))
            ops.append(MachiningOp(
                tipo="furo",
                face=face,
                x=py2,
                y=posicao_lateral_z_mm,
                diametro=8.0,
                profundidade=11.0,
                descricao="Cavilha Junção Travessa (Ø8mm x 11mm)",
            ))

    return ops


def make_back_panel_groove(
    comprimento_mm: float,
    afastamento_traseiro_mm: float = 15.0,
    largura_canal_mm: float = 6.0,
    profundidade_canal_mm: float = 8.0,
    face: FaceType = "traseira",
) -> MachiningOp:
    """Gera operação de rasgo / canal para encaixe do fundo de 6mm."""
    return MachiningOp(
        tipo="rasgo",
        face=face,
        x=0.0,
        y=afastamento_traseiro_mm,
        largura=largura_canal_mm,
        comprimento=comprimento_mm,
        profundidade=profundidade_canal_mm,
        descricao=f"Canal de Fundo {largura_canal_mm:.0f}mm (Prof. {profundidade_canal_mm:.0f}mm)",
    )


def make_shelf_joint_holes(
    prof_prateleira_mm: float,
    afastamento_mm: float = 50.0,
    esp_prateleira_mm: float = 15.0,
    dispositivo_prateleira: str = "cavilha",
    largura_prateleira_mm: float = 0.0,
) -> tuple[list[MachiningOp], list[MachiningOp]]:
    """Gera furações nos topos e/ou face da prateleira interna (retorna ops_esq, ops_dir).

    Regra padrão: apenas cavilhas (Ø8mm), a 50mm das bordas (frontal e traseira).
    Quando dispositivo_prateleira for VB 35 ou VB 36:
    - Adiciona os furos de alojamento de tambor Ø20mm x 12.5mm na face 'base' da prateleira.
    """
    disp = str(dispositivo_prateleira or "cavilha").strip().lower()
    pontos_y = [afastamento_mm, max(afastamento_mm + 32.0, prof_prateleira_mm - afastamento_mm)]

    ops_esq: list[MachiningOp] = []
    ops_dir: list[MachiningOp] = []

    if "vb35" in disp or "vb36" in disp or "vb_35" in disp or "vb_36" in disp or "vb" in disp:
        nome_disp = "VB 36" if "36" in disp else "VB 35"
        diametro_alojamento = 20.0
        profundidade_alojamento = 14.0 if esp_prateleira_mm >= 25.0 else 12.5

        if esp_prateleira_mm <= 15.5:
            dist_borda_x = 9.5
        elif esp_prateleira_mm <= 19.5:
            dist_borda_x = 10.0
        else:
            dist_borda_x = 12.5

        for idx, py in enumerate(pontos_y, 1):
            x_esq = dist_borda_x
            ops_esq.append(MachiningOp(
                tipo="furo",
                face="base",
                x=x_esq,
                y=py,
                diametro=diametro_alojamento,
                profundidade=profundidade_alojamento,
                descricao=f"Tambor {nome_disp} Esq {idx} (Ø{int(diametro_alojamento)}mm x {profundidade_alojamento:.1f}mm)",
            ))

            if largura_prateleira_mm > 0:
                x_dir = max(dist_borda_x, largura_prateleira_mm - dist_borda_x)
                ops_dir.append(MachiningOp(
                    tipo="furo",
                    face="base",
                    x=x_dir,
                    y=py,
                    diametro=diametro_alojamento,
                    profundidade=profundidade_alojamento,
                    descricao=f"Tambor {nome_disp} Dir {idx} (Ø{int(diametro_alojamento)}mm x {profundidade_alojamento:.1f}mm)",
                ))
    else:
        for idx, py in enumerate(pontos_y, 1):
            # Furo de topo esquerdo (-X da prateleira)
            ops_esq.append(MachiningOp(
                tipo="furo",
                face="esquerda",
                x=py,
                y=esp_prateleira_mm / 2.0,
                diametro=8.0,
                profundidade=20.0,
                descricao=f"Cavilha Prateleira Topo Esq {idx} (Ø8mm x 20mm)",
            ))
            # Furo de topo direito (+X da prateleira)
            ops_dir.append(MachiningOp(
                tipo="furo",
                face="direita",
                x=py,
                y=esp_prateleira_mm / 2.0,
                diametro=8.0,
                profundidade=20.0,
                descricao=f"Cavilha Prateleira Topo Dir {idx} (Ø8mm x 20mm)",
            ))

    return ops_esq, ops_dir


def make_shelf_side_holes(
    pos_z_na_lateral_mm: float,
    prof_prateleira_mm: float,
    recuo_frontal_mm: float = 0.0,
    afastamento_mm: float = 50.0,
    esp_prateleira_mm: float = 15.0,
    face: FaceType = "traseira",
    dispositivo_prateleira: str = "cavilha",
) -> list[MachiningOp]:
    """Gera furações correspondentes na face interna da lateral ou divisória do armário.

    - Para cavilha: furo Ø8mm x 11mm (no centro da espessura da prateleira).
    - Para VB 35 / VB 36: pino de aço com furo Ø5mm x 11.5mm (alinhado com o eixo do conector VB).
    """
    disp = str(dispositivo_prateleira or "cavilha").strip().lower()
    pontos_y = [
        recuo_frontal_mm + afastamento_mm,
        recuo_frontal_mm + max(afastamento_mm + 32.0, prof_prateleira_mm - afastamento_mm),
    ]

    ops: list[MachiningOp] = []
    eh_vb = ("vb35" in disp or "vb36" in disp or "vb_35" in disp or "vb_36" in disp or "vb" in disp)

    if eh_vb:
        nome_disp = "VB 36" if "36" in disp else "VB 35"
        diam = 5.0
        prof = 11.5
        z_furo_mm = pos_z_na_lateral_mm + min(esp_prateleira_mm / 2.0, 6.0 if esp_prateleira_mm >= 15.0 else esp_prateleira_mm / 2.0)
        desc_prefix = f"Pino Conector {nome_disp} Face Lateral"
    else:
        diam = 8.0
        prof = 11.0
        z_furo_mm = pos_z_na_lateral_mm + (esp_prateleira_mm / 2.0)
        desc_prefix = "Cavilha Prateleira Face Lateral"

    for idx, py in enumerate(pontos_y, 1):
        ops.append(MachiningOp(
            tipo="furo",
            face=face,
            x=py,
            y=z_furo_mm,
            diametro=diam,
            profundidade=prof,
            descricao=f"{desc_prefix} {idx} (Ø{int(diam)}mm x {prof:.1f}mm)",
        ))

    return ops


def make_horizontal_board_edge_holes(
    prof_chapa_mm: float,
    largura_chapa_mm: float = 0.0,
    esp_chapa_mm: float = 15.0,
    afastamento_fixacao_frontal_mm: float = 50.0,
    afastamento_fixacao_traseiro_mm: float = 50.0,
    afastamento_cavilha_frontal_mm: float = 100.0,
    afastamento_cavilha_traseiro_mm: float = 100.0,
    usar_minifix: bool = True,
    dispositivo_fixacao: str = "minifix_cavilha",
    face_tambor: FaceType = "base",
) -> tuple[list[MachiningOp], list[MachiningOp], list[MachiningOp]]:
    """Gera furações da chapa horizontal (Base / Tampo Fechado):

    Se Minifix:
    1. Furos de topo (esquerdo e direito):
       - Passagem da haste do Minifix (Ø7mm x 34mm no topo) a 50mm das bordas.
       - Cavilhas Ø8mm x 20mm de profundidade no topo a 100mm das bordas.
    2. Furos de face (face inferior da base ou face interna do tampo):
       - Furo do tambor excêntrico Minifix (Ø15mm x 12.5mm) a 34mm da borda do topo e a 50mm das bordas frontal e traseira.

    Se Parafuso:
    1. Furos de topo (esquerdo e direito):
       - Furo piloto / guia para parafuso (Ø3.5mm ou Ø4.0mm x 35mm no topo) a 50mm das bordas.
       - Cavilhas Ø8mm x 20mm de profundidade no topo a 100mm das bordas.
    2. Furos de face:
       - Nenhum furo de tambor (faces 100% lisas e limpas).

    Retorna: (ops_topo_esq, ops_topo_dir, ops_face_tambor)
    """
    af_f = max(10.0, float(afastamento_fixacao_frontal_mm if afastamento_fixacao_frontal_mm is not None else 50.0))
    af_t = max(10.0, float(afastamento_fixacao_traseiro_mm if afastamento_fixacao_traseiro_mm is not None else 50.0))
    af_cav_f = max(10.0, float(afastamento_cavilha_frontal_mm if afastamento_cavilha_frontal_mm is not None else 100.0))
    af_cav_t = max(10.0, float(afastamento_cavilha_traseiro_mm if afastamento_cavilha_traseiro_mm is not None else 100.0))

    disp = str(dispositivo_fixacao or "").lower()
    eh_somente_cavilha = (disp in ("cavilha", "apenas_cavilha", "apenas_cavilhas", "somente_cavilha"))
    eh_somente_parafuso = (disp in ("soberba", "apenas_parafuso", "somente_parafuso", "somente_parafusos", "apenas_parafusos"))
    eh_minifix = "minifix" in disp and not eh_somente_cavilha and not eh_somente_parafuso
    eh_parafuso = ("parafuso" in disp or "confirmat" in disp or "soberba" in disp) and not eh_somente_cavilha

    pos_cav_f = min(af_cav_f, prof_chapa_mm / 2.0 - 15.0)
    pos_cav_t = max(pos_cav_f + 32.0, prof_chapa_mm - af_cav_t)
    pontos_cav = [pos_cav_f, pos_cav_t]
    if prof_chapa_mm > 650:
        pontos_cav.insert(1, (pos_cav_f + pos_cav_t) / 2.0)

    pontos_fix = [af_f, max(af_f + 32.0, prof_chapa_mm - af_t)]
    if prof_chapa_mm > 650:
        pontos_fix.insert(1, (af_f + (prof_chapa_mm - af_t)) / 2.0)

    ops_esq: list[MachiningOp] = []
    ops_dir: list[MachiningOp] = []
    ops_face: list[MachiningOp] = []

    # 1. Cavilhas nos topos laterais (geradas se NÃO for somente parafuso)
    if not eh_somente_parafuso:
        for idx, py in enumerate(pontos_cav, 1):
            ops_esq.append(MachiningOp(
                tipo="furo",
                face="esquerda",
                x=py,
                y=esp_chapa_mm / 2.0,
                diametro=8.0,
                profundidade=20.0,
                descricao=f"Cavilha Topo Esq {idx} (Ø8mm x 20mm)",
            ))
            ops_dir.append(MachiningOp(
                tipo="furo",
                face="direita",
                x=py,
                y=esp_chapa_mm / 2.0,
                diametro=8.0,
                profundidade=20.0,
                descricao=f"Cavilha Topo Dir {idx} (Ø8mm x 20mm)",
            ))

    # 2. Elementos de Fixação
    if eh_minifix and usar_minifix:
        # Minifix: Passagem no topo + Tambor na face
        for idx, py in enumerate(pontos_fix, 1):
            ops_esq.append(MachiningOp(
                tipo="furo",
                face="esquerda",
                x=py,
                y=esp_chapa_mm / 2.0,
                diametro=7.0,
                profundidade=34.0,
                descricao=f"Passagem Haste Minifix Esq {idx} (Ø7mm x 34mm)",
            ))
            ops_dir.append(MachiningOp(
                tipo="furo",
                face="direita",
                x=py,
                y=esp_chapa_mm / 2.0,
                diametro=7.0,
                profundidade=34.0,
                descricao=f"Passagem Haste Minifix Dir {idx} (Ø7mm x 34mm)",
            ))

            ops_face.append(MachiningOp(
                tipo="furo",
                face=face_tambor,
                x=34.0,
                y=py,
                diametro=15.0,
                profundidade=12.5,
                descricao=f"Tambor Minifix Esq {idx} (Ø15mm)",
            ))
            if largura_chapa_mm > 0:
                ops_face.append(MachiningOp(
                    tipo="furo",
                    face=face_tambor,
                    x=largura_chapa_mm - 34.0,
                    y=py,
                    diametro=15.0,
                    profundidade=12.5,
                    descricao=f"Tambor Minifix Dir {idx} (Ø15mm)",
                ))
    elif eh_parafuso:
        # Parafuso: Furo piloto/guia no topo com 40mm de profundidade, SEM tambor na face
        for idx, py in enumerate(pontos_fix, 1):
            ops_esq.append(MachiningOp(
                tipo="furo",
                face="esquerda",
                x=py,
                y=esp_chapa_mm / 2.0,
                diametro=3.5,
                profundidade=40.0,
                descricao=f"Furo Guia Parafuso Topo Esq {idx} (Ø3.5mm x 40mm)",
            ))
            ops_dir.append(MachiningOp(
                tipo="furo",
                face="direita",
                x=py,
                y=esp_chapa_mm / 2.0,
                diametro=3.5,
                profundidade=40.0,
                descricao=f"Furo Guia Parafuso Topo Dir {idx} (Ø3.5mm x 40mm)",
            ))

    return ops_esq, ops_dir, ops_face


def make_vertical_divider_joint_holes(
    prof_divisoria_mm: float,
    esp_divisoria_mm: float = 15.0,
    furacao_cima: bool = True,
    furacao_baixo: bool = True,
    afastamento_frontal_mm: float = 50.0,
    afastamento_traseiro_mm: float = 50.0,
    diametro_cavilha_mm: float = 8.0,
    prof_cavilha_mm: float = 20.0,
) -> list[MachiningOp]:
    """Gera furações técnicas de cavilha para topos de divisórias verticais.

    Configurável para gerar furação:
    - No topo superior (em cima): face="topo"
    - No topo inferior (embaixo): face="base"
    - Em ambos ou nenhum.

    As cavilhas ficam centradas na espessura (y = esp_divisoria_mm / 2.0) e distribuídas
    ao longo da profundidade da divisória (x ao longo de Y da peça).
    """
    ops: list[MachiningOp] = []
    if not furacao_cima and not furacao_baixo:
        return ops

    af_f = max(10.0, float(afastamento_frontal_mm))
    af_t = max(10.0, float(afastamento_traseiro_mm))
    pos_f = min(af_f, prof_divisoria_mm / 2.0 - 15.0)
    pos_t = max(pos_f + 32.0, prof_divisoria_mm - af_t)

    pontos_y = [pos_f, pos_t]
    if prof_divisoria_mm > 650.0:
        pontos_y.insert(1, (pos_f + pos_t) / 2.0)

    # Topo superior (+Z, em cima)
    if furacao_cima:
        for idx, py in enumerate(pontos_y, 1):
            ops.append(MachiningOp(
                tipo="furo",
                face="topo",
                x=py,
                y=esp_divisoria_mm / 2.0,
                diametro=diametro_cavilha_mm,
                profundidade=prof_cavilha_mm,
                descricao=f"Cavilha Divisoria Topo Sup {idx} (Ø{int(diametro_cavilha_mm)}mm x {int(prof_cavilha_mm)}mm)",
            ))

    # Topo inferior (-Z, embaixo)
    if furacao_baixo:
        for idx, py in enumerate(pontos_y, 1):
            ops.append(MachiningOp(
                tipo="furo",
                face="base",
                x=py,
                y=esp_divisoria_mm / 2.0,
                diametro=diametro_cavilha_mm,
                profundidade=prof_cavilha_mm,
                descricao=f"Cavilha Divisoria Base Inf {idx} (Ø{int(diametro_cavilha_mm)}mm x {int(prof_cavilha_mm)}mm)",
            ))

    return ops
