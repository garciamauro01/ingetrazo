# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Gera miniaturas reais das portas e janelas a partir dos modelos ``.igz``.

Uso::

    python -m trazomob.scripts.generate_esquadria_thumbs

Desenha cada modelo com o mesmo projetor vetorial usado pela bandeja de
componentes (:func:`views.component_thumbs.thumbnail`), no tamanho 128×128 das
miniaturas já existentes.  Por padrão **nunca sobrescreve** um PNG presente:
a galeria continua usando as imagens antigas até que se decida substituí-las.
Passe ``--force`` para registrar novamente todos os modelos.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PySide6.QtGui import QGuiApplication

from trazomob.assets.catalog import get_esquadrias_catalogo, get_esquadria_files

COMPONENTS_DIR = Path(__file__).resolve().parents[1] / "assets" / "components"
THUMBS_DIR = Path(__file__).resolve().parents[1] / "assets" / "thumbs" / "esquadrias"
SIZE = 128


def _app() -> QGuiApplication:
    """QPainter precisa de uma aplicação Qt; reaproveita a existente nos testes."""
    return QGuiApplication.instance() or QGuiApplication([])


def render_model(igz_path: Path, size: int = SIZE):
    """Devolve o ``QPixmap`` do modelo, com todos os grupos do ``.igz`` montados."""
    _app()

    from core.group import Group
    from core.mesh import Mesh
    from core.scene import Scene
    from formats import igz
    from views.component_thumbs import thumbnail

    cena = Scene()
    igz.load_into(cena, igz_path)

    raiz = Group(name=igz_path.stem)
    raiz.mesh = Mesh()
    raiz.children = list(cena.groups)
    return thumbnail(raiz, size)


def generate_missing(thumbs_dir: Path = THUMBS_DIR, *, force: bool = False,
                     components_dir: Path = COMPONENTS_DIR, size: int = SIZE) -> dict[str, list[str]]:
    """Cria ``<id>.png`` para os modelos do catálogo que ainda não têm miniatura.

    Nenhum arquivo é apagado.  Com ``force=False``, os PNGs existentes são
    apenas listados em ``mantidos``.
    """
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    arquivos = get_esquadria_files()
    criados: list[str] = []
    mantidos: list[str] = []
    sem_modelo: list[str] = []

    for modelo in get_esquadrias_catalogo():
        item_id = str(modelo["id"])
        destino = thumbs_dir / f"{item_id}.png"
        if destino.exists() and not force:
            mantidos.append(item_id)
            continue
        mapeado = arquivos.get(item_id)
        if not mapeado:
            sem_modelo.append(item_id)
            continue
        arquivo, subpasta = mapeado
        origem = components_dir / subpasta / arquivo
        if not origem.exists():
            sem_modelo.append(item_id)
            continue
        pixmap = render_model(origem, size)
        if not pixmap.save(str(destino), "PNG"):
            raise OSError(f"falha ao gravar miniatura de {item_id}: {destino}")
        criados.append(item_id)

    return {"criados": criados, "mantidos": mantidos, "sem_modelo": sem_modelo}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="regera também as miniaturas já existentes")
    parser.add_argument("--out", type=Path, default=THUMBS_DIR,
                        help="pasta de destino (padrão: assets/thumbs/esquadrias)")
    args = parser.parse_args()

    resultado = generate_missing(args.out, force=args.force)
    print(f"Criadas..........: {len(resultado['criados'])}")
    for item_id in resultado["criados"]:
        print(f"  + {item_id}.png")
    print(f"Mantidas.........: {len(resultado['mantidos'])}")
    print(f"Sem modelo .igz..: {len(resultado['sem_modelo'])}")
    for item_id in resultado["sem_modelo"]:
        print(f"  ! {item_id}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
