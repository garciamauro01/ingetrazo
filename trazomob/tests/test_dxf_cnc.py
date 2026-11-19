# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes de exportação de usinagens e plano de corte em formato DXF CNC."""
import os
import tempfile
from pathlib import Path

from trazomob.production.dxf_cnc import export_cut_sheet_dxf, export_piece_dxf
from trazomob.production.machining import MachiningOp
from trazomob.production.optimizer import CutPiece, CutSheet


def test_export_piece_dxf_layers_and_holes():
    """Valida que uma peça com furos caneco e rasgo gera layers DXF padronizados."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dxf_path = Path(tmpdir) / "porta.dxf"

        ops = [
            MachiningOp(tipo="furo", face="traseira", x=21.5, y=100.0, diametro=35.0, profundidade=12.0, descricao="Caneco"),
            MachiningOp(tipo="furo", face="traseira", x=21.5, y=600.0, diametro=35.0, profundidade=12.0, descricao="Caneco"),
            MachiningOp(tipo="furo", face="traseira", x=50.0, y=50.0, diametro=5.0, profundidade=13.0, descricao="Calço"),
            MachiningOp(tipo="rasgo", face="traseira", x=10.0, y=10.0, largura=6.0, comprimento=380.0, profundidade=10.0, descricao="Canal"),
        ]

        piece = {
            "nome": "Porta_Gabinete",
            "comprimento": 700.0,
            "largura": 400.0,
            "espessura": 15.0,
            "material": "MDF Carvalho",
            "operacoes": ops,
        }

        total_entities = export_piece_dxf(piece, dxf_path, include_labels=True)
        assert total_entities > 0
        assert dxf_path.exists()

        content = dxf_path.read_text(encoding="ascii")
        assert "SECTION" in content
        assert "TABLES" in content
        assert "ENTITIES" in content
        # Layers esperados
        assert "CONTORNO" in content
        assert "FURO_D35_P12" in content
        assert "FURO_D5_P13" in content
        assert "RASGO_L6_P10" in content
        assert "TEXTO" in content
        # Círculos
        assert "CIRCLE" in content
        assert "EOF" in content


def test_export_cut_sheet_dxf():
    """Valida a exportação completa de uma chapa de corte com peças e furações."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dxf_path = Path(tmpdir) / "chapa_1.dxf"

        p1 = CutPiece(
            id=1,
            nome="Lateral_Esq",
            comprimento=720.0,
            largura=550.0,
            espessura=15.0,
            material="MDF Branco TX",
            x=15.0,
            y=15.0,
            w_aloc=720.0,
            h_aloc=550.0,
            operacoes=[
                {"tipo": "furo", "face": "frontal", "x": 37.0, "y": 100.0, "diametro": 5.0, "profundidade": 13.0},
            ],
        )

        p2 = CutPiece(
            id=2,
            nome="Prateleira",
            comprimento=768.0,
            largura=530.0,
            espessura=15.0,
            material="MDF Branco TX",
            x=740.0,
            y=15.0,
            w_aloc=768.0,
            h_aloc=530.0,
        )

        sheet = CutSheet(
            indice=1,
            material="MDF Branco TX (15mm)",
            espessura=15.0,
            comprimento_bruto=2750.0,
            largura_bruto=1850.0,
            pecas=[p1, p2],
            aproveitamento_pct=82.5,
        )

        total = export_cut_sheet_dxf(sheet, dxf_path, include_holes=True)
        assert total > 0
        assert dxf_path.exists()

        content = dxf_path.read_text(encoding="ascii")
        assert "CHAPA_BRUTA" in content
        assert "PECAS_CONTORNO" in content
        assert "FURO_D5_P13" in content
        assert "Lateral_Esq" in content
        assert "Prateleira" in content

