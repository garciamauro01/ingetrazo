# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Canonical structure and resolution of boards, materials, and edge banding.

Centralizes woodworking business rules for canonical parts:
- Hierarchical resolution (Room / Module -> Part Type -> Individual Part);
- Contextual edge banding (front, rear, top, bottom, long/short edges);
- Transparent mapping to c1, c2, l1, l2 and cutting metadata.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PapelChapa(str, Enum):
    """Functional role of the board in the cabinetwork structure."""
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
    """Material context and rules inherited from the module."""
    material_caixa: str = "MDF Branco TX 15mm"
    material_fita_caixa: str | None = None
    fita_caixa_modo: str = "frontal_1L"  # Options: frontal_1L, 2L, 4L, sem_fita
    material_frentes: str | None = None
    material_fita_frentes: str | None = None
    fita_frentes_modo: str = "4L"  # Doors/fronts default to 4L (all 4 edges)
    espessura_fita_padrao: float = 0.45
    espessura_fita_frentes: float = 0.45
    folga_frentes_mm: float = 3.0

    @property
    def folga_frentes_m(self) -> float:
        """Clearance between fronts/doors and perimeter in meters."""
        return max(0.0, float(self.folga_frentes_mm)) / 1000.0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ModuloMaterialContext:
        """Create the context from the module parameters dictionary."""
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
    """Complete canonical specification of a woodworking part / board."""
    nome: str
    papel: PapelChapa
    material: str
    fita_c1: bool = False
    fita_c2: bool = False
    fita_l1: bool = False
    fita_l2: bool = False
    material_fita: str | None = None
    espessura_fita: float = 0.45
    ignorar_veio: bool = False
    operacoes: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def resolve(
        cls,
        nome: str,
        papel: PapelChapa | str,
        ctx: ModuloMaterialContext | None = None,
        material_override: str | None = None,
        fita_override: tuple[bool, bool, bool, bool] | None = None,
        material_fita_override: str | None = None,
        espessura_fita_override: float | None = None,
        operacoes: list[dict[str, Any]] | None = None,
    ) -> ChapaSpec:
        """Resolve material and edge banding based on functional role and inherited rules."""
        if isinstance(papel, str):
            try:
                papel = PapelChapa(papel)
            except ValueError:
                papel = PapelChapa.PECA_AVULSA

        ctx = ctx or ModuloMaterialContext()

        # 1. Determine base material
        is_frente = papel in (PapelChapa.PORTA, PapelChapa.FRENTE_GAVETA)
        if material_override:
            mat = material_override
        elif is_frente and ctx.material_frentes:
            mat = ctx.material_frentes
        else:
            mat = ctx.material_caixa

        # 2. Determine edge banding material
        if material_fita_override:
            mat_fita = material_fita_override
        elif is_frente:
            mat_fita = ctx.material_fita_frentes or ctx.material_frentes or mat
        else:
            mat_fita = ctx.material_fita_caixa or ctx.material_caixa or mat

        # 3. Determine edge banding thickness
        if espessura_fita_override is not None:
            esp_fita = float(espessura_fita_override)
        elif is_frente:
            esp_fita = ctx.espessura_fita_frentes
        else:
            esp_fita = ctx.espessura_fita_padrao

        # 4. Determine edge banding (c1, c2, l1, l2)
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
    def _resolve_fitamento_padrao(papel: PapelChapa, ctx: ModuloMaterialContext) -> tuple[bool, bool, bool, bool]:
        """Apply the standard woodworking edge-banding rule by functional role."""
        # Back panel never has edge banding
        if papel in (PapelChapa.FUNDO, PapelChapa.FUNDO_GAVETA):
            return (False, False, False, False)

        # Fronts (doors and drawers) are banded on all 4 edges (4L)
        if papel in (PapelChapa.PORTA, PapelChapa.FRENTE_GAVETA):
            modo = (ctx.fita_frentes_modo or "4L").lower()
            if modo == "sem_fita":
                return (False, False, False, False)
            return (True, True, True, True)

        # Internal shelves and dividers: default 1L front edge
        if papel in (PapelChapa.PRATELEIRA, PapelChapa.DIVISORIA_VERTICAL, PapelChapa.DIVISORIA_HORIZONTAL):
            return (True, False, False, False)

        # Stretchers and toe kick: 1 front edge
        if papel in (PapelChapa.TRAVESSA, PapelChapa.RODAPE):
            return (True, False, False, False)

        # Internal drawer box parts (sides/back): exposed top edge banded
        if papel in (PapelChapa.LATERAL_GAVETA, PapelChapa.CONTRAFRENTE_GAVETA, PapelChapa.TRASEIRO_GAVETA):
            return (True, False, False, False)

        # Cover panels: default 4L or 2L
        if papel == PapelChapa.TAMPONAMENTO:
            modo = (ctx.fita_caixa_modo or "4L").lower()
            if modo == "sem_fita":
                return (False, False, False, False)
            if modo == "frontal_1l":
                return (True, False, False, False)
            if modo == "2l":
                return (True, True, False, False)
            return (True, True, True, True)

        # Structural carcass (Sides, Base, Top)
        modo_cx = (ctx.fita_caixa_modo or "frontal_1L").lower()
        if modo_cx == "sem_fita":
            return (False, False, False, False)
        elif modo_cx == "4l":
            return (True, True, True, True)
        elif modo_cx == "2l":
            return (True, True, False, False)
        else:
            # frontal_1L: exposed visible front edge
            # For side panels and bases, c1=True, l1=True is used by convention on visible joints
            return (True, False, True, False)
