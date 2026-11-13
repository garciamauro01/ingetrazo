# SPDX-License-Identifier: GPL-3.0-or-later
"""Generic hardware library.

No mounting dimension is invented.  ``verified`` stays false until the user
enters data taken from the manufacturer's catalogue; the generator only emits
rule-based layout positions, clearly labelled as such.  Prices start at zero.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from ..core.errors import DataError
from ..core.logging_utils import get_logger
from ..core.models import HardwareItem
from ..materials.library import MaterialLibrary, _atomic_write, _read_json

DEFAULT_HARDWARE = (
    HardwareItem("HW-HINGE-35", "Dobradiça 35 mm (genérica)", "dobradica",
                 reference="GEN-35", unit="un",
                 notes="Sem raio de giro, copo ou recuo de fabricante. "
                       "Cadastre os dados oficiais antes de furar."),
    HardwareItem("HW-SLIDE-35", "Corrediça telescópica 35 kg (par)",
                 "corredica", reference="GEN-SLIDE-35", unit="par",
                 notes="Comprimento e furação variam por fabricante."),
    HardwareItem("HW-SLIDE-SLIDING", "Kit de correr para portas (genérico)",
                 "corredica", reference="GEN-SLIDING", unit="kit",
                 notes="Altura de guia é configurável no módulo."),
    HardwareItem("HW-HANDLE-BAR", "Puxador barra (genérico)", "puxador",
                 reference="GEN-HANDLE", unit="un",
                 notes="Comprimento e entre-eixos a definir pelo usuário."),
    HardwareItem("HW-FOOT", "Pé nivelador (genérico)", "pe",
                 reference="GEN-FOOT", unit="un"),
    HardwareItem("HW-SCREW-4X16", "Parafuso 4 × 16 mm", "parafuso",
                 reference="GEN-4X16", unit="un"),
    HardwareItem("HW-DOWEL-8X30", "Cavilha 8 × 30 mm", "cavilha",
                 reference="GEN-8X30", unit="un"),
    HardwareItem("HW-MINIFIX", "Minifix (genérico)", "minifix",
                 reference="GEN-MINIFIX", unit="un"),
)


class HardwareLibrary:
    schema = 1

    def __init__(self, items=None) -> None:
        self.items: dict[str, HardwareItem] = dict(items or {})

    @classmethod
    def with_defaults(cls) -> "HardwareLibrary":
        return cls({item.id: deepcopy(item) for item in DEFAULT_HARDWARE})

    @classmethod
    def from_dict(cls, raw) -> "HardwareLibrary":
        raw = raw if isinstance(raw, dict) else {}
        items = {}
        for entry in raw.get("items") or []:
            try:
                item = HardwareItem.from_dict(entry)
            except Exception as exc:                     # noqa: BLE001
                get_logger().warning("hardware ignored: %s", exc)
                continue
            items[item.id] = item
        library = cls(items)
        if not library.items:
            library.items = {i.id: deepcopy(i) for i in DEFAULT_HARDWARE}
        return library

    @classmethod
    def load(cls, path) -> "HardwareLibrary":
        payload = _read_json(Path(path)) if path else {}
        return cls.from_dict(payload) if payload else cls.with_defaults()

    def to_dict(self) -> dict:
        return {"schema": self.schema,
                "items": [i.to_dict() for i in self.items.values()]}

    def save(self, path) -> None:
        _atomic_write(Path(path), self.to_dict())

    def __len__(self) -> int:
        return len(self.items)

    def get(self, hardware_id: str) -> HardwareItem | None:
        return self.items.get(hardware_id)

    def add(self, item: HardwareItem) -> HardwareItem:
        problems = item.validate()
        if problems:
            raise DataError("; ".join(problems))
        if item.id in self.items:
            raise DataError(f"Já existe uma ferragem com o identificador "
                            f"{item.id}.")
        self.items[item.id] = item
        return item

    def update(self, item: HardwareItem) -> HardwareItem:
        problems = item.validate()
        if problems:
            raise DataError("; ".join(problems))
        if item.id not in self.items:
            raise DataError(f"Ferragem não encontrada: {item.id}.")
        self.items[item.id] = item
        return item

    def remove(self, hardware_id: str) -> None:
        self.items.pop(hardware_id, None)

    def merge(self, other: "HardwareLibrary", *,
              overwrite: bool = False) -> None:
        for item_id, item in other.items.items():
            if overwrite or item_id not in self.items:
                self.items[item_id] = item

    def validate(self) -> list[str]:
        problems: list[str] = []
        for item in self.items.values():
            problems.extend(f"{item.name}: {p}" for p in item.validate())
            if item.install and not item.verified:
                problems.append(
                    f"{item.name}: há dados de instalação sem marcação de "
                    "verificação; confirme no catálogo do fabricante.")
        return problems


# Convenience for callers that already have a material library: the two are
# kept in separate files for compatibility with older user libraries.
def load_libraries(directory) -> tuple[MaterialLibrary, HardwareLibrary]:
    directory = Path(directory)
    return (MaterialLibrary.load(directory / "materials.json"),
            HardwareLibrary.load(directory / "hardware.json"))
