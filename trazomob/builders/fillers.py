# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Construtor de Peças de Fechamento / Arremate Automático de Vãos Residuais (builder_fechamento.py).

Gera um conjunto profissional de arremate de canto para marcenaria sob medida:
1. Testeira / Frente de Fechamento frontal:
   - Cortada rigorosamente na largura milimétrica exata da folga residual (ex: 30mm a 200mm);
   - Alinhada no mesmo plano da linha de portas/frentes dos módulos vizinhos;
   - Fita de borda nos 4 lados;
   - Acabamento com o material/cor padrão das frentes do ambiente.
2. Sarrafo Estrutural de Recuo (Batten / Cleat):
   - Régua interna de suporte estrutural recuada 15mm para fixação por parafusos na lateral do módulo;
   - Garante sustentação sólida contra a parede de alvenaria.
"""
from __future__ import annotations

from typing import Optional, Tuple, List, Dict, Any

from PySide6.QtGui import QVector3D
from core.group import Group
from core.mesh import Mesh
from ..builders.mesh_utils import create_board_group
from ..builders.chapa_builder import build_chapa
from ..builders.chapa_spec import ChapaSpec, PapelChapa, ModuloMaterialContext


class FechamentoBuilder:
    """Fábrica de peças de fechamento e arremate de vãos residuais."""

    @classmethod
    def build_fechamento_canto(
        cls,
        largura_mm: float,
        altura_mm: float,
        prof_mm: float,
        esp_mm: float = 15.0,
        material: str = "MDF Branco TX 15mm",
        material_fita: Optional[str] = None,
        offset: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        cor: Optional[Tuple[float, float, float]] = None,
        cor_fita: Optional[Tuple[float, float, float]] = None,
        recuo_sarrafo_mm: float = 50.0,
    ) -> List[Group]:
        """Gera as chapas da testeira frontal de arremate e o sarrafo de fixação interno.

        Orientação padrão no espaço local:
        - X (Largura): vai de ox até ox + largura_mm;
        - Y (Profundidade): vai de oy (face da parede) até oy + prof_mm (frente do móvel);
        - Z (Altura): vai de oz até oz + altura_mm.
        """
        from ..builders.cabinet import CabinetBuilder
        if cor is None:
            cor = CabinetBuilder.get_material_color(material)
        if cor_fita is None and material_fita:
            cor_fita = CabinetBuilder.get_material_color(material_fita)

        ox, oy, oz = offset
        L = max(0.015, largura_mm / 1000.0)
        A = max(0.100, altura_mm / 1000.0)
        P = max(0.050, prof_mm / 1000.0)
        E = max(0.006, esp_mm / 1000.0)

        groups: List[Group] = []

        # 1. Testeira Frontal de Arremate (alinhada na face frontal do móvel: Y = oy + P - E)
        y_frente = oy + P - E
        spec_frente = ChapaSpec.resolve(
            nome="Testeira Arremate",
            papel=PapelChapa.TAMPONAMENTO,
            ctx=ModuloMaterialContext(material_caixa=material, material_fita_caixa=material_fita),
            material_override=material,
            fita_override=(True, True, True, True),
            material_fita_override=material_fita,
        )
        frente_group = build_chapa(
            spec_frente,
            (ox, y_frente, oz),
            (L, E, A),
            color=cor,
            cor_fita=cor_fita,
        )
        groups.append(frente_group)

        # 2. Sarrafo de Apoio / Fixação Lateral (perpendicular, encostado na lateral do móvel)
        # Largura = E, Profundidade = 70mm a 100mm, Altura = A
        prof_sarrafo = min(P - E, max(0.060, recuo_sarrafo_mm / 1000.0))
        y_sarrafo = y_frente - prof_sarrafo
        # Se L >= 25mm, posiciona o sarrafo recuado atrás da frente para parafusar por trás
        x_sarrafo = ox + L - E if L >= E else ox
        spec_sarrafo = ChapaSpec.resolve(
            nome="Sarrafo de Fixação",
            papel=PapelChapa.TRAVESSA,
            ctx=ModuloMaterialContext(material_caixa=material, material_fita_caixa=material_fita),
            material_override=material,
            fita_override=(False, False, True, False),
            material_fita_override=material_fita,
        )
        sarrafo_group = build_chapa(
            spec_sarrafo,
            (x_sarrafo, y_sarrafo, oz),
            (E, prof_sarrafo, A),
            color=cor,
            cor_fita=cor_fita,
        )
        groups.append(sarrafo_group)

        return groups

    @classmethod
    def build_fechamento_group(
        cls,
        largura_mm: float,
        altura_mm: float,
        prof_mm: float,
        esp_mm: float = 15.0,
        material: str = "MDF Branco TX 15mm",
        material_fita: Optional[str] = None,
        offset: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        cor: Optional[Tuple[float, float, float]] = None,
        cor_fita: Optional[Tuple[float, float, float]] = None,
        rot_z: float = 0.0,
    ) -> Group:
        """Cria o Group mestre container de fechamento de vão com metadados para lista de corte e orçamento."""
        pieces = cls.build_fechamento_canto(
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            prof_mm=prof_mm,
            esp_mm=esp_mm,
            material=material,
            material_fita=material_fita,
            offset=offset,
            cor=cor,
            cor_fita=cor_fita,
        )

        master_name = f"Arremate de Canto {int(round(largura_mm))}mm"
        master = Group(Mesh(), name=master_name)
        from PySide6.QtGui import QMatrix4x4
        master.xform = QMatrix4x4()
        master.layer = "PLANEJADOS"

        for p in pieces:
            p.layer = "PLANEJADOS"

        if getattr(master, "children", None) is not None:
            master.children.extend(pieces)
        elif hasattr(master, "groups"):
            master.groups.extend(pieces)

        # Metadados completos do TrazoMob (chaves oficial e legada em sincronia)
        from ..domain.schema import set_module_data
        set_module_data(master, {
            "tipo": "fechamento_canto",
            "largura": float(largura_mm),
            "altura": float(altura_mm),
            "profundidade": float(prof_mm),
            "espessura": float(esp_mm),
            "material": material,
            "material_fita": material_fita,
            "rot_z": float(rot_z),
            "offset": offset,
        })

        # Aplica rotação Z se necessário
        if abs(rot_z) > 1e-4:
            import math
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

# Aliases
FillerBuilder = FechamentoBuilder

