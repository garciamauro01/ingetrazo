# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Espelhamento paramétrico de módulos do TrazoMob.

O espelho nativo do IngeTrazo reflete a MALHA: portas, puxadores, dobradiças e
furações ficam com a geometria invertida e o módulo deixa de poder ser
reconstruído a partir dos parâmetros (a próxima edição de largura desfaz o
espelho ou deixa as ferragens do lado errado).

Aqui o espelho é um PARÂMETRO (``mirror_x``). A geometria é refletida no eixo
local X logo depois de construída e antes de aplicar a rotação, e tudo o que
descreve a peça é refletido junto:

* as faces têm o sentido do loop invertido (senão as normais apontam para
  dentro e o sólido some no render);
* os furos de usinagem (caneco Ø35, minifix, cavilha) acompanham o espelho —
  para peças frontais o eixo X das operações é invertido;
* a fita de borda troca de lado (L1 ↔ L2) nas peças em que essas faces são as
  laterais;
* ``door_side`` (esquerda/direita) é trocado e os nomes "Esquerda"/"Direita"
  acompanham, para o cutlist e a animação de abertura continuarem coerentes;
* o estado de animação em cache é descartado, para ser recalculado a partir da
  geometria já espelhada.

Como o parâmetro fica gravado no ``ext`` do módulo, toda reconstrução
(alterar medida, trocar tipo, undo/redo) volta espelhada.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

from PySide6.QtGui import QVector3D

#: Chave do parâmetro que liga o espelho no eixo local X.
MIRROR_PARAM = "mirror_x"

#: Estado de animação derivado da geometria: não pode sobreviver ao espelho.
_ANIMATION_KEYS = (
    "orig_vertices",
    "orig_uvws",
    "hinge_pivot",
    "flap_axis",
    "door_angle",
    "slide_delta",
    "open_fraction",
    "is_open",
)

#: Trocas de lado aplicadas a nomes de peça.
_SIDE_MAP = {
    "Esquerda": "Direita",
    "Direita": "Esquerda",
    "esquerda": "direita",
    "direita": "esquerda",
    "ESQUERDA": "DIREITA",
    "DIREITA": "ESQUERDA",
    "Esquerdo": "Direito",
    "Direito": "Esquerdo",
    "esquerdo": "direito",
    "direito": "esquerdo",
    "ESQUERDO": "DIREITO",
    "DIREITO": "ESQUERDO",
    "Esq.": "Dir.",
    "Dir.": "Esq.",
    "esq.": "dir.",
    "dir.": "esq.",
    "Esq": "Dir",
    "Dir": "Esq",
    "esq": "dir",
    "dir": "esq",
    "Left": "Right",
    "Right": "Left",
    "left": "right",
    "right": "left",
    "LEFT": "RIGHT",
    "RIGHT": "LEFT",
}

#: Um único passe com as formas mais longas primeiro: "Esquerda" é trocada
#: antes de "Esq", e o texto já substituído não é reprocessado. As abreviações
#: exigem fim de palavra, para "Esq" não casar dentro de "Esquadria".
_SIDE_PATTERNS = [
    re.escape(chave) + ("" if chave.endswith(".") else r"(?!\w)")
    for chave in sorted(_SIDE_MAP, key=len, reverse=True)
]
_SIDE_RE = re.compile("|".join(_SIDE_PATTERNS))


def is_mirrored(group: Any) -> bool:
    """Diz se o módulo está espelhado, lendo o parâmetro gravado no ``ext``."""
    ext = getattr(group, "ext", None)
    if not isinstance(ext, dict):
        return False
    oficial = ext.get("trazomob")
    if isinstance(oficial, dict) and MIRROR_PARAM in oficial:
        return bool(oficial[MIRROR_PARAM])
    legado = ext.get("trazomob_module")
    if isinstance(legado, dict):
        return bool(legado.get(MIRROR_PARAM, False))
    return False


def _mesh_bounds_mm(mesh: Any) -> Optional[Tuple[float, float, float]]:
    """Dimensões (x, y, z) da malha de uma peça, em milímetros."""
    vertices = getattr(mesh, "vertices", None)
    if not vertices:
        return None
    xs = [v.position.x() for v in vertices]
    ys = [v.position.y() for v in vertices]
    zs = [v.position.z() for v in vertices]
    return (
        (max(xs) - min(xs)) * 1000.0,
        (max(ys) - min(ys)) * 1000.0,
        (max(zs) - min(zs)) * 1000.0,
    )


def _swap_side_words(text: Any) -> Any:
    """Troca "Esquerda"↔"Direita" (e equivalentes) num nome de peça."""
    if not isinstance(text, str) or not text:
        return text
    return _SIDE_RE.sub(lambda m: _SIDE_MAP[m.group(0)], text)


def _flip_operations(meta: Dict[str, Any], length_mm: float) -> None:
    """Inverte o eixo X das usinagens de uma peça frontal."""
    operacoes = meta.get("operacoes")
    if not isinstance(operacoes, list):
        return
    novas = []
    for op in operacoes:
        if not isinstance(op, dict):
            novas.append(op)
            continue
        copia = dict(op)
        if copia.get("x") is not None:
            try:
                copia["x"] = round(float(length_mm) - float(copia["x"]), 3)
            except (TypeError, ValueError):
                pass
        novas.append(copia)
    meta["operacoes"] = novas


def _mirror_piece_metadata(piece: Any, dims_mm: Optional[Tuple[float, float, float]]) -> None:
    """Reflete os metadados de uma peça: fita, usinagens, lado e nome."""
    ext = getattr(piece, "ext", None)
    if not isinstance(ext, dict):
        ext = {}
        piece.ext = ext
    meta = ext.get("trazomob")
    if not isinstance(meta, dict):
        meta = {}
        ext["trazomob"] = meta

    if dims_mm is not None:
        sx, sy, sz = dims_mm
        min_dim = min(sx, sy, sz)
        # Peça frontal (espessura em Y) ou horizontal (espessura em Z): as
        # faces L1/L2 são as laterais em X, então trocam de lado no espelho.
        if abs(sy - min_dim) < 1e-5 or abs(sz - min_dim) < 1e-5:
            meta["fita_l1"], meta["fita_l2"] = (
                bool(meta.get("fita_l2", False)),
                bool(meta.get("fita_l1", False)),
            )
        # Só a peça frontal tem as usinagens medidas ao longo de X.
        if abs(sy - min_dim) < 1e-5 and meta.get("comprimento"):
            _flip_operations(meta, float(meta["comprimento"]))

    side = str(meta.get("door_side", "")).lower()
    if side == "left":
        meta["door_side"] = "right"
    elif side == "right":
        meta["door_side"] = "left"

    if "nome" in meta:
        meta["nome"] = _swap_side_words(meta["nome"])
    if isinstance(getattr(piece, "name", None), str):
        piece.name = _swap_side_words(piece.name)

    for key in _ANIMATION_KEYS:
        ext.pop(key, None)


def mirror_module_geometry(master: Any, plane_x: float) -> None:
    """Reflete no plano ``x = plane_x`` toda a geometria e os metadados do módulo.

    Deve ser chamada ANTES da rotação final: o plano é o eixo local X do módulo
    recém-construído, não o eixo do mundo.
    """
    targets = list(getattr(master, "children", None) or [])
    if not targets:
        targets = [master]

    for piece in targets:
        mesh = getattr(piece, "mesh", None)
        vertices = getattr(mesh, "vertices", None)
        if not vertices:
            continue

        dims_mm = _mesh_bounds_mm(mesh)

        for vertex in vertices:
            p = vertex.position
            vertex.position = QVector3D(2.0 * plane_x - p.x(), p.y(), p.z())

        # A reflexão inverte a orientação de todos os loops: reverter o sentido
        # mantém as normais apontando para fora (e os furos, para dentro).
        for face in getattr(mesh, "faces", None) or []:
            loop = getattr(face, "loop", None)
            if loop:
                loop.reverse()
            for hole in getattr(face, "hole_loops", None) or []:
                if hole:
                    hole.reverse()

        mesh._mut_serial = getattr(mesh, "_mut_serial", 0) + 1
        _mirror_piece_metadata(piece, dims_mm)
