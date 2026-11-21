# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Auditoria somente leitura das miniaturas de portas e janelas.

Uso::

    python -m trazomob.scripts.audit_esquadria_thumbs

A galeria procura ``assets/thumbs/esquadrias/<id>.png`` e, quando o arquivo
não existe, usa a miniatura vetorial genérica de ``ui/thumbnails.py``.  Este
script nunca cria, substitui ou apaga PNGs: ele apenas informa quais modelos
estão sem miniatura própria e se algum arquivo está órfão ou corrompido.
"""
from __future__ import annotations

from pathlib import Path

from trazomob.assets.catalog import get_esquadrias_catalogo

THUMBS_DIR = Path(__file__).resolve().parents[1] / "assets" / "thumbs" / "esquadrias"
_PNG_ASSINATURA = b"\x89PNG\r\n\x1a\n"


def audit_thumbs(thumbs_dir: Path = THUMBS_DIR) -> dict[str, list[str]]:
    """Devolve o estado das miniaturas, sem alterar nenhum arquivo."""
    ids = {str(modelo["id"]) for modelo in get_esquadrias_catalogo()}
    arquivos = sorted(thumbs_dir.glob("*.png")) if thumbs_dir.is_dir() else []
    presentes = {p.stem for p in arquivos}

    invalidos = []
    for png in arquivos:
        try:
            with png.open("rb") as handle:
                cabecalho = handle.read(8)
        except OSError:
            invalidos.append(png.name)
            continue
        if cabecalho != _PNG_ASSINATURA or png.stat().st_size <= len(_PNG_ASSINATURA):
            invalidos.append(png.name)

    return {
        "com_miniatura": sorted(ids & presentes),
        "sem_miniatura": sorted(ids - presentes),
        "orfas": sorted(presentes - ids),
        "invalidas": sorted(invalidos),
    }


def main() -> int:
    resultado = audit_thumbs()
    print(f"Modelos no catálogo..........: {len(resultado['com_miniatura']) + len(resultado['sem_miniatura'])}")
    print(f"Com miniatura própria........: {len(resultado['com_miniatura'])}")
    print(f"Usando ícone genérico........: {len(resultado['sem_miniatura'])}")
    print(f"PNG órfãos (fora do catálogo): {len(resultado['orfas'])}")
    print(f"PNG inválidos................: {len(resultado['invalidas'])}")
    if resultado["sem_miniatura"]:
        print("\nSem miniatura própria:")
        for item_id in resultado["sem_miniatura"]:
            print(f"  - {item_id}")
    if resultado["orfas"]:
        print("\nÓrfãos:")
        for nome in resultado["orfas"]:
            print(f"  - {nome}.png")
    if resultado["invalidas"]:
        print("\nInválidos:")
        for nome in resultado["invalidas"]:
            print(f"  - {nome}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
