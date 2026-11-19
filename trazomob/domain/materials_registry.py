# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Cadastro e catálogo persistente de materiais de marcenaria do TrazoMob.

Substitui qualquer inferência por nome ou string, fornecendo propriedades
explícitas de fabricação (permite_giro, sentido_veio, espessuras e cores).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class MaterialDefinition:
    """Definição formal de um padrão de material/chapa para marcenaria."""
    nome: str
    categoria: str = "mdf"              # "mdf", "pedra", "madeira_macica", "metal"
    permite_giro: bool = True           # Se True, corte pode rotacionar 90° (ex: unicolores como Branco TX)
    sentido_veio: str = "indiferente"   # "indiferente", "longitudinal", "transversal"
    espessuras: list[float] = field(default_factory=lambda: [15.0, 18.0])
    comprimento_chapa_mm: float = 2750.0
    largura_chapa_mm: float = 1850.0
    refilo_mm: float = 15.0
    cor_rgb: list[float] = field(default_factory=lambda: [0.95, 0.95, 0.93])
    custom: bool = False                # Se foi cadastrado pelo usuário

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MaterialDefinition:
        return cls(
            nome=str(data.get("nome", "")),
            categoria=str(data.get("categoria", "mdf")),
            permite_giro=bool(data.get("permite_giro", True)),
            sentido_veio=str(data.get("sentido_veio", "indiferente")),
            espessuras=[float(e) for e in data.get("espessuras", [15.0, 18.0])],
            comprimento_chapa_mm=float(data.get("comprimento_chapa_mm", 2750.0)),
            largura_chapa_mm=float(data.get("largura_chapa_mm", 1850.0)),
            refilo_mm=float(data.get("refilo_mm", 15.0)),
            cor_rgb=[float(c) for c in data.get("cor_rgb", [0.95, 0.95, 0.93])],
            custom=bool(data.get("custom", False)),
        )


# Materiais de fábrica pré-definidos com propriedades técnicas precisas
_DEFAULT_MATERIALS: list[MaterialDefinition] = [
    # ── Unicolores (sem veio -> permite_giro=True, sentido="indiferente") ──
    MaterialDefinition(
        nome="MDF Branco TX",
        categoria="mdf",
        permite_giro=True,
        sentido_veio="indiferente",
        espessuras=[6.0, 15.0, 18.0, 25.0],
        cor_rgb=[0.96, 0.96, 0.95],
    ),
    MaterialDefinition(
        nome="MDF Grafite",
        categoria="mdf",
        permite_giro=True,
        sentido_veio="indiferente",
        espessuras=[15.0, 18.0],
        cor_rgb=[0.25, 0.25, 0.25],
    ),
    MaterialDefinition(
        nome="MDF Cinza Sagrado",
        categoria="mdf",
        permite_giro=True,
        sentido_veio="indiferente",
        espessuras=[15.0, 18.0],
        cor_rgb=[0.65, 0.65, 0.65],
    ),

    # ── Madeirados / Com Veio (sentido longitudinal obrigatório -> permite_giro=False) ──
    MaterialDefinition(
        nome="MDF Autentic Arauco",
        categoria="mdf",
        permite_giro=False,
        sentido_veio="longitudinal",
        espessuras=[15.0, 18.0],
        cor_rgb=[198 / 255.0, 165 / 255.0, 127 / 255.0],
    ),
    MaterialDefinition(
        nome="MDF Carvalho",
        categoria="mdf",
        permite_giro=False,
        sentido_veio="longitudinal",
        espessuras=[15.0, 18.0],
        cor_rgb=[203 / 255.0, 175 / 255.0, 142 / 255.0],
    ),
    MaterialDefinition(
        nome="MDF Castanho",
        categoria="mdf",
        permite_giro=False,
        sentido_veio="longitudinal",
        espessuras=[15.0, 18.0],
        cor_rgb=[100 / 255.0, 74 / 255.0, 54 / 255.0],
    ),
    MaterialDefinition(
        nome="MDF Ciliegio Florença",
        categoria="mdf",
        permite_giro=False,
        sentido_veio="longitudinal",
        espessuras=[15.0, 18.0],
        cor_rgb=[206 / 255.0, 190 / 255.0, 171 / 255.0],
    ),
    MaterialDefinition(
        nome="MDF Louro Freijó",
        categoria="mdf",
        permite_giro=False,
        sentido_veio="longitudinal",
        espessuras=[15.0, 18.0],
        cor_rgb=[0.75, 0.55, 0.35],
    ),
    MaterialDefinition(
        nome="MDF Carvalho Boreal",
        categoria="mdf",
        permite_giro=False,
        sentido_veio="longitudinal",
        espessuras=[15.0, 18.0],
        cor_rgb=[210 / 255.0, 185 / 255.0, 150 / 255.0],
    ),

    # ── Pedras e Bancadas ──
    MaterialDefinition(
        nome="Granito Preto São Gabriel 20mm",
        categoria="pedra",
        permite_giro=True,
        sentido_veio="indiferente",
        espessuras=[20.0],
        cor_rgb=[0.12, 0.12, 0.13],
    ),
    MaterialDefinition(
        nome="Granito Preto Absoluto 20mm",
        categoria="pedra",
        permite_giro=True,
        sentido_veio="indiferente",
        espessuras=[20.0],
        cor_rgb=[0.08, 0.08, 0.09],
    ),
    MaterialDefinition(
        nome="Mármore Nero Marquina 20mm",
        categoria="pedra",
        permite_giro=False,
        sentido_veio="longitudinal",
        espessuras=[20.0],
        cor_rgb=[0.10, 0.10, 0.11],
    ),
    MaterialDefinition(
        nome="Quartzo Branco Calacatta 20mm",
        categoria="pedra",
        permite_giro=False,
        sentido_veio="longitudinal",
        espessuras=[20.0],
        cor_rgb=[0.93, 0.93, 0.94],
    ),
    MaterialDefinition(
        nome="Granito Branco Siena 20mm",
        categoria="pedra",
        permite_giro=True,
        sentido_veio="indiferente",
        espessuras=[20.0],
        cor_rgb=[0.88, 0.88, 0.86],
    ),
    MaterialDefinition(
        nome="Bancada Madeira Teca 30mm",
        categoria="madeira_macica",
        permite_giro=False,
        sentido_veio="longitudinal",
        espessuras=[30.0],
        cor_rgb=[0.72, 0.52, 0.32],
    ),
]


class MaterialsRegistry:
    """Gerenciador central de catálogo de materiais com persistência em JSON."""

    _instance: Optional[MaterialsRegistry] = None

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        if storage_path is None:
            storage_path = Path(__file__).resolve().parent / "materials_data.json"
        self.storage_path = storage_path
        self._materials: dict[str, MaterialDefinition] = {}
        self.load()

    @classmethod
    def get_instance(cls) -> MaterialsRegistry:
        if cls._instance is None:
            cls._instance = MaterialsRegistry()
        return cls._instance

    def load(self) -> None:
        """Carrega materiais do arquivo JSON ou inicializa com os padrões."""
        self._materials.clear()
        # 1. Carrega os padrões
        for mat in _DEFAULT_MATERIALS:
            self._materials[mat.nome] = mat

        # 2. Carrega catálogos dinâmicos de texturas (mdf/ e marmores/)
        tex_root = Path(__file__).resolve().parents[1] / "assets" / "textures"
        for sub, default_cat, default_esp in (
            ("mdf", "mdf", [15.0, 18.0]),
            ("marmores", "pedra", [20.0]),
        ):
            cat_path = tex_root / sub / "catalog.json"
            if not cat_path.exists():
                continue
            try:
                entries = json.loads(cat_path.read_text(encoding="utf-8"))
                if isinstance(entries, list):
                    for entry in entries:
                        nome = str(entry.get("nome", "")).strip()
                        if not nome or nome in self._materials:
                            continue
                        self._materials[nome] = MaterialDefinition.from_dict({
                            "nome": nome,
                            "categoria": entry.get("categoria", default_cat),
                            "permite_giro": entry.get("permite_giro", default_cat != "mdf"),
                            "sentido_veio": entry.get("sentido_veio", "indiferente"),
                            "espessuras": entry.get("espessuras", default_esp),
                            "cor_rgb": entry.get("cor_rgb", [0.85, 0.85, 0.85]),
                        })
            except Exception:
                pass

        # 3. Se houver arquivo customizado salvo, mescla/atualiza
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        m = MaterialDefinition.from_dict(item)
                        self._materials[m.nome] = m
            except Exception:
                pass

    def save(self) -> None:
        """Salva a lista completa de materiais no arquivo JSON."""
        try:
            data = [m.to_dict() for m in self._materials.values()]
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def get_material(self, name: str) -> Optional[MaterialDefinition]:
        """Busca a definição do material pelo nome exato ou normalizado sem sufixo de espessura."""
        if not name:
            return None
        # 1. Busca direta exata
        if name in self._materials:
            return self._materials[name]

        # 2. Busca removendo sufixos como " 15mm", " 18mm", etc.
        import re
        clean_name = re.sub(r"\s+\d+\s*mm$", "", name.strip(), flags=re.IGNORECASE)
        if clean_name in self._materials:
            return self._materials[clean_name]

        # 3. Busca insensível a maiúsculas/minúsculas
        clean_lower = clean_name.lower()
        for k, v in self._materials.items():
            if k.lower() == clean_lower:
                return v

        return None

    def allows_rotation(self, material_name: str) -> bool:
        """Retorna True se o material explicitamente permite giro no corte (ignora veio)."""
        mat = self.get_material(material_name)
        if mat is not None:
            return mat.permite_giro
        # Se for um material desconhecido não cadastrado, por segurança estrutural não gira
        return False

    def list_materials(self, categoria: Optional[str] = None) -> list[MaterialDefinition]:
        """Lista os materiais cadastrados, opcionalmente filtrados por categoria."""
        items = list(self._materials.values())
        if categoria:
            items = [m for m in items if m.categoria == categoria]
        return items

    def add_or_update_material(self, material: MaterialDefinition) -> None:
        """Adiciona ou atualiza um material e persiste no JSON."""
        self._materials[material.nome] = material
        self.save()

    def remove_material(self, name: str) -> bool:
        """Remove um material cadastrado."""
        if name in self._materials:
            del self._materials[name]
            self.save()
            return True
        return False

    def reset_to_defaults(self) -> None:
        """Restaura o catálogo para os padrões de fábrica."""
        self._materials.clear()
        for mat in _DEFAULT_MATERIALS:
            self._materials[mat.nome] = mat
        self.save()
