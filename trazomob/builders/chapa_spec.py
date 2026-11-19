# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Estrutura e resolução canônica de chapas, materiais e fitamento de borda.

Centraliza as regras de negócio de marcenaria para peças canônicas:
- Resolução hierárquica (Ambiente / Módulo -> Tipo de Peça -> Peça Individual);
- Fitamento contextual (frontal, traseiro, superior, inferior, bordos longos/curtos);
- Mapeamento transparente para c1, c2, l1, l2 e metadados de corte.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Tuple


class PapelChapa(str, Enum):
    """Papel funcional da chapa na estrutura de marcenaria."""
    LATERAL_ESQUERDA = "lateral_esquerda"
    LATERAL_DIREITA = "lateral_direita"
    BASE_INFERIOR = "base_inferior"
    TAMPO_SUPERIOR = "tampo_superior"
    PRATELEIRA = "prateleira"
    DIVISORIA_VERTICAL = "divisoria_vertical"
    DIVISORIA_HORIZONTAL = "divisoria_horizontal"
    TRAVESSA = "travessa"
    FUNDO = "fundo"
    PORTA = "porta"
    FRENTE_GAVETA = "frente_gaveta"
    LATERAL_GAVETA = "lateral_gaveta"
    CONTRAFRENTE_GAVETA = "contrafrente_gaveta"
    TRASEIRO_GAVETA = "traseiro_gaveta"
    FUNDO_GAVETA = "fundo_gaveta"
    RODAPE = "rodape"
    TAMPONAMENTO = "tamponamento"
    PECA_AVULSA = "peca_avulsa"


@dataclass
class ModuloMaterialContext:
    """Contexto de materiais e regras herdadas do módulo."""
    material_caixa: str = "MDF Branco TX 15mm"
    material_fita_caixa: Optional[str] = None
    fita_caixa_modo: str = "frontal_1L"  # frontal_1L, 2L, 4L, sem_fita
    material_frentes: Optional[str] = None
    material_fita_frentes: Optional[str] = None
    fita_frentes_modo: str = "4L"  # Portas/frentes por padrão são 4L
    espessura_fita_padrao: float = 0.45
    espessura_fita_frentes: float = 0.45
    folga_frentes_mm: float = 3.0

    @property
    def folga_frentes_m(self) -> float:
        """Folga entre frentes/portas e perímetro em metros."""
        return max(0.0, float(self.folga_frentes_mm)) / 1000.0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ModuloMaterialContext:
        """Cria o contexto a partir do dicionário de parâmetros do módulo."""
        mat_cx = d.get("material", "MDF Branco TX 15mm")
        fita_cx_modo = d.get("fita_caixa_modo", "frontal_1L")
        fita_fr_modo = d.get("fita_frentes_modo", "4L")
        mat_fita_cx = d.get("material_fita_caixa")
        mat_fr = d.get("material_frentes") or mat_cx
        mat_fita_fr = d.get("material_fita_frentes") or mat_fita_cx
        esp_fita = float(d.get("espessura_fita", 0.45))
        esp_fita_fr = float(d.get("espessura_fita_frentes", esp_fita) or esp_fita)
        raw_folga = d.get("folga_frentes_mm", d.get("folga_frentes", 3.0))
        folga_fr_mm = float(3.0 if raw_folga is None else raw_folga)
        return cls(
            material_caixa=mat_cx,
            material_fita_caixa=mat_fita_cx,
            fita_caixa_modo=fita_cx_modo,
            material_frentes=mat_fr,
            material_fita_frentes=mat_fita_fr,
            fita_frentes_modo=fita_fr_modo,
            espessura_fita_padrao=esp_fita,
            espessura_fita_frentes=esp_fita_fr,
            folga_frentes_mm=folga_fr_mm,
        )


@dataclass
class ChapaSpec:
    """Especificação canônica completa de uma peça / chapa de marcenaria."""
    nome: str
    papel: PapelChapa
    material: str
    fita_c1: bool = False
    fita_c2: bool = False
    fita_l1: bool = False
    fita_l2: bool = False
    material_fita: Optional[str] = None
    espessura_fita: float = 0.45
    ignorar_veio: bool = False
    operacoes: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def resolve(
        cls,
        nome: str,
        papel: PapelChapa | str,
        ctx: Optional[ModuloMaterialContext] = None,
        material_override: Optional[str] = None,
        fita_override: Optional[Tuple[bool, bool, bool, bool]] = None,
        material_fita_override: Optional[str] = None,
        espessura_fita_override: Optional[float] = None,
        operacoes: Optional[list[dict[str, Any]]] = None,
    ) -> ChapaSpec:
        """Resolve material e fitamento com base no papel funcional e regras herdadas."""
        if isinstance(papel, str):
            try:
                papel = PapelChapa(papel)
            except ValueError:
                papel = PapelChapa.PECA_AVULSA

        ctx = ctx or ModuloMaterialContext()

        # 1. Determina material base
        is_frente = papel in (PapelChapa.PORTA, PapelChapa.FRENTE_GAVETA)
        if material_override:
            mat = material_override
        elif is_frente and ctx.material_frentes:
            mat = ctx.material_frentes
        else:
            mat = ctx.material_caixa

        # 2. Determina material da fita
        if material_fita_override:
            mat_fita = material_fita_override
        elif is_frente:
            mat_fita = ctx.material_fita_frentes or ctx.material_frentes or mat
        else:
            mat_fita = ctx.material_fita_caixa or ctx.material_caixa or mat

        # 3. Determina espessura da fita
        if espessura_fita_override is not None:
            esp_fita = float(espessura_fita_override)
        elif is_frente:
            esp_fita = ctx.espessura_fita_frentes
        else:
            esp_fita = ctx.espessura_fita_padrao

        # 4. Determina fitamento (c1, c2, l1, l2)
        if fita_override is not None:
            c1, c2, l1, l2 = fita_override
        else:
            c1, c2, l1, l2 = cls._resolve_fitamento_padrao(papel, ctx)

        return cls(
            nome=nome,
            papel=papel,
            material=mat,
            fita_c1=c1,
            fita_c2=c2,
            fita_l1=l1,
            fita_l2=l2,
            material_fita=mat_fita,
            espessura_fita=esp_fita,
            operacoes=list(operacoes) if operacoes else [],
        )

    @staticmethod
    def _resolve_fitamento_padrao(papel: PapelChapa, ctx: ModuloMaterialContext) -> Tuple[bool, bool, bool, bool]:
        """Aplica a regra padrão de marcenaria por papel funcional."""
        # Fundo nunca tem fita
        if papel in (PapelChapa.FUNDO, PapelChapa.FUNDO_GAVETA):
            return (False, False, False, False)

        # Frentes (portas e gavetas) são fitadas nos 4 bordos (4L)
        if papel in (PapelChapa.PORTA, PapelChapa.FRENTE_GAVETA):
            modo = (ctx.fita_frentes_modo or "4L").lower()
            if modo == "sem_fita":
                return (False, False, False, False)
            return (True, True, True, True)

        # Prateleiras internas e divisórias: padrão 1L frontal
        if papel in (PapelChapa.PRATELEIRA, PapelChapa.DIVISORIA_VERTICAL, PapelChapa.DIVISORIA_HORIZONTAL):
            return (True, False, False, False)

        # Travessas e rodapé: 1 bordo frontal
        if papel in (PapelChapa.TRAVESSA, PapelChapa.RODAPE):
            return (True, False, False, False)

        # Gavetas internas (laterais/traseiro): topo aparente fitado
        if papel in (PapelChapa.LATERAL_GAVETA, PapelChapa.CONTRAFRENTE_GAVETA, PapelChapa.TRASEIRO_GAVETA):
            return (True, False, False, False)

        # Tamponamentos: por padrão 4L ou 2L
        if papel == PapelChapa.TAMPONAMENTO:
            modo = (ctx.fita_caixa_modo or "4L").lower()
            if modo == "sem_fita":
                return (False, False, False, False)
            if modo == "frontal_1l":
                return (True, False, False, False)
            if modo == "2l":
                return (True, True, False, False)
            return (True, True, True, True)

        # Caixaria estrutural (Laterais, Base, Tampo)
        modo_cx = (ctx.fita_caixa_modo or "frontal_1L").lower()
        if modo_cx == "sem_fita":
            return (False, False, False, False)
        elif modo_cx == "4l":
            return (True, True, True, True)
        elif modo_cx == "2l":
            return (True, True, False, False)
        else:
            # frontal_1L: frente visível aparente
            # Para laterais e bases, convenciona-se c1=True, l1=True nas conexões aparentes
            return (True, False, True, False)
