# SPDX-License-Identifier: GPL-3.0-or-later
"""Material and edge-band libraries.

Built-ins are generic descriptions only: no manufacturer reference, price or
proprietary sheet size is invented.  Prices start at zero and the managers
refuse to treat them as a real quote until the user fills them in.
"""
from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path

from ..core.errors import DataError
from ..core.models import EdgeBand, Material
from ..core.logging_utils import get_logger

DEFAULT_MATERIALS = (
    Material("MAT-MDF-BRANCO-18", "MDF Branco 18 mm", "MDF", thickness_mm=18.0,
             color="#F2F0E9", sheet_length_mm=2750.0, sheet_width_mm=1830.0,
             grain_axis="length", finish="Liso",
             edge_band_id="EB-PVC-BRANCO-045",
             notes="Material genérico de referência; cadastre o fornecedor."),
    Material("MAT-MDF-CRU-18", "MDF Cru 18 mm", "MDF", thickness_mm=18.0,
             color="#D8C3A5", sheet_length_mm=2750.0, sheet_width_mm=1830.0,
             grain_axis="length", finish="Liso",
             edge_band_id="EB-PVC-CRU-045"),
    Material("MAT-MDF-BRANCO-6", "MDF Branco 6 mm (fundo)", "MDF",
             thickness_mm=6.0, color="#F4F2EC", sheet_length_mm=2750.0,
             sheet_width_mm=1830.0, grain_axis="length", finish="Liso",
             edge_band_id="EB-PVC-BRANCO-022"),
    Material("MAT-MDF-CARVALHO-18", "MDF Carvalho 18 mm", "MDF",
             thickness_mm=18.0, color="#B4885A", sheet_length_mm=2750.0,
             sheet_width_mm=1830.0, grain_axis="length", finish="Madeira",
             edge_band_id="EB-PVC-CARVALHO-045"),
    Material("MAT-COMPENSADO-18", "Compensado 18 mm", "Compensado",
             thickness_mm=18.0, color="#D6B98C", sheet_length_mm=2750.0,
             sheet_width_mm=1830.0, grain_axis="length", finish="Madeira",
             edge_band_id="EB-PVC-CRU-045"),
    Material("MAT-GRANITO-20", "Granito 20 mm (genérico)", "Pedra",
             thickness_mm=20.0, color="#5B5B5B", sheet_length_mm=3000.0,
             sheet_width_mm=1800.0, grain_axis="none", finish="Pedra",
             allow_rotation=True, edge_band_id="",
             notes="Tampo de pedra; medidas comerciais variam por fornecedor."),
    Material("MAT-VIDRO-6", "Vidro 6 mm (genérico)", "Vidro",
             thickness_mm=6.0, color="#BBD8DE", sheet_length_mm=2000.0,
             sheet_width_mm=1000.0, grain_axis="none", finish="Vidro",
             allow_rotation=True, edge_band_id=""),
)

DEFAULT_EDGE_BANDS = (
    EdgeBand("EB-PVC-BRANCO-045", "Fita PVC Branco 0,45 mm", "#F2F0E9",
             0.45, "PVC", 0.0, notes="Fita genérica; confirme a cor do lote."),
    EdgeBand("EB-PVC-CRU-045", "Fita PVC Cru 0,45 mm", "#D8C3A5",
             0.45, "PVC", 0.0),
    EdgeBand("EB-PVC-CARVALHO-045", "Fita PVC Carvalho 0,45 mm", "#B4885A",
             0.45, "PVC", 0.0),
    EdgeBand("EB-PVC-BRANCO-022", "Fita PVC Branco 0,22 mm", "#F4F2EC",
             0.22, "PVC", 0.0),
    EdgeBand("EB-ABS-BRANCO-100", "Fita ABS Branco 1,0 mm", "#F2F0E9",
             1.0, "ABS", 0.0),
)


def _atomic_write(path: Path, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = None
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
        handle = os.fdopen(fd, "w", encoding="utf-8")
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        handle = None
        os.replace(temp_name, path)
    except OSError as exc:
        raise DataError(f"Não foi possível gravar {path}: {exc}",
                        details=str(exc)) from exc
    finally:
        if handle is not None:
            handle.close()


def _read_json(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        raise DataError(f"Não foi possível ler {path}: {exc}",
                        details=str(exc)) from exc
    if not isinstance(data, dict):
        raise DataError(f"Arquivo de biblioteca inválido: {path}")
    return data


class MaterialLibrary:
    """User-editable material and edge-band registry.

    The library is plain data.  The scene's own material registry is written
    by the geometry adapter, so the domain layer can be tested with no host
    and no Qt.
    """

    schema = 1

    def __init__(self, materials=None, edge_bands=None) -> None:
        self.materials: dict[str, Material] = dict(materials or {})
        self.edge_bands: dict[str, EdgeBand] = dict(edge_bands or {})

    # -- construction -------------------------------------------------------
    @classmethod
    def with_defaults(cls) -> "MaterialLibrary":
        # Fresh copies: the module-level defaults must never be mutated by a
        # caller (tests do mutate prices; a user must be able to too).
        return cls({m.id: deepcopy(m) for m in DEFAULT_MATERIALS},
                   {b.id: deepcopy(b) for b in DEFAULT_EDGE_BANDS})

    @classmethod
    def from_dict(cls, raw) -> "MaterialLibrary":
        raw = raw if isinstance(raw, dict) else {}
        materials = {}
        for item in raw.get("materials") or []:
            try:
                mat = Material.from_dict(item)
            except Exception as exc:                     # noqa: BLE001
                get_logger().warning("material ignored: %s", exc)
                continue
            materials[mat.id] = mat
        bands = {}
        for item in raw.get("edge_bands") or []:
            try:
                band = EdgeBand.from_dict(item)
            except Exception as exc:                     # noqa: BLE001
                get_logger().warning("edge band ignored: %s", exc)
                continue
            bands[band.id] = band
        library = cls(materials, bands)
        if not library.materials:
            library.materials = {m.id: m for m in DEFAULT_MATERIALS}
        if not library.edge_bands:
            library.edge_bands = {b.id: b for b in DEFAULT_EDGE_BANDS}
        return library

    @classmethod
    def load(cls, path) -> "MaterialLibrary":
        payload = _read_json(Path(path)) if path else {}
        return cls.from_dict(payload) if payload else cls.with_defaults()

    def to_dict(self) -> dict:
        return {
            "schema": self.schema,
            "materials": [m.to_dict() for m in self.materials.values()],
            "edge_bands": [b.to_dict() for b in self.edge_bands.values()],
        }

    def save(self, path) -> None:
        _atomic_write(Path(path), self.to_dict())

    # -- operations ---------------------------------------------------------
    def __len__(self) -> int:
        return len(self.materials) + len(self.edge_bands)

    def material(self, material_id: str) -> Material | None:
        return self.materials.get(material_id)

    def edge_band(self, band_id: str) -> EdgeBand | None:
        return self.edge_bands.get(band_id) if band_id else None

    def add_material(self, material: Material) -> Material:
        problems = material.validate()
        if problems:
            raise DataError("; ".join(problems))
        if material.id in self.materials:
            raise DataError(f"Já existe um material com o identificador "
                            f"{material.id}.")
        self.materials[material.id] = material
        return material

    def update_material(self, material: Material) -> Material:
        problems = material.validate()
        if problems:
            raise DataError("; ".join(problems))
        if material.id not in self.materials:
            raise DataError(f"Material não encontrado: {material.id}.")
        self.materials[material.id] = material
        return material

    def remove_material(self, material_id: str, *, in_use: bool = False) -> None:
        if in_use:
            raise DataError("O material está em uso por um módulo.")
        self.materials.pop(material_id, None)

    def add_edge_band(self, band: EdgeBand) -> EdgeBand:
        problems = band.validate()
        if problems:
            raise DataError("; ".join(problems))
        if band.id in self.edge_bands:
            raise DataError(f"Já existe uma fita com o identificador {band.id}.")
        self.edge_bands[band.id] = band
        return band

    def update_edge_band(self, band: EdgeBand) -> EdgeBand:
        problems = band.validate()
        if problems:
            raise DataError("; ".join(problems))
        if band.id not in self.edge_bands:
            raise DataError(f"Fita não encontrada: {band.id}.")
        self.edge_bands[band.id] = band
        return band

    def remove_edge_band(self, band_id: str) -> None:
        self.edge_bands.pop(band_id, None)

    def merge(self, other: "MaterialLibrary", *, overwrite: bool = False) -> None:
        for mat_id, mat in other.materials.items():
            if overwrite or mat_id not in self.materials:
                self.materials[mat_id] = mat
        for band_id, band in other.edge_bands.items():
            if overwrite or band_id not in self.edge_bands:
                self.edge_bands[band_id] = band

    def validate(self) -> list[str]:
        problems: list[str] = []
        for mat in self.materials.values():
            problems.extend(f"{mat.name}: {p}" for p in mat.validate())
        for band in self.edge_bands.values():
            problems.extend(f"{band.name}: {p}" for p in band.validate())
        return problems
