# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Planning and placement for automatic wall fill.

Planning is independent from IngeTrazo: it takes a span in millimeters and
returns the list of modules (type, width, doors, and divisions) whose widths
sum to the exact requested span. Placement happens after building each
group, aligning the back to the wall face plane and distributing the modules
along the horizontal direction of the face.
"""
from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from PySide6.QtGui import QVector3D

from ..domain.module_geometry import auto_divisoes_for_doors

#: Nominal reference width per door and per drawer bank.
DOOR_WIDTH_MM = 400.0
DRAWER_WIDTH_MM = 450.0

#: Technical limits used when distributing the span remainder.
MIN_MODULE_MM = 250.0
MAX_MODULE_MM = 1800.0

MAX_DOORS_LOWER = 4
MAX_DOORS_UPPER = 2


@dataclass
class LayoutModule:
    """A planned module for automatic wall fill."""

    tipo: str
    largura_mm: float
    num_portas: int = 0
    num_divisoes: int = 0
    num_gavetas: int = 0


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------

def _normalizar_categoria(categoria: str) -> str:
    valor = str(categoria or "").strip().lower()
    if valor in ("aereo", "aéreo", "upper", "superior"):
        return "aereo"
    return "inferior"


def _normalizar_composicao(composicao: str, categoria: str) -> str:
    valor = str(composicao or "").strip().lower()
    if categoria == "aereo":
        return "portas"
    if valor in ("gavetas", "gaveteiros", "somente_gavetas"):
        return "gavetas"
    if valor in ("misto", "mista", "balcoes_gaveteiros", "balcões_gaveteiros"):
        return "misto"
    return "portas"


def _dividir_portas(total_portas: int, max_por_modulo: int) -> list[int]:
    """Distribute doors across balanced modules while respecting the maximum."""
    total = max(1, int(total_portas))
    max_por_modulo = max(1, int(max_por_modulo))
    n_modulos = max(1, math.ceil(total / max_por_modulo))
    base, resto = divmod(total, n_modulos)
    return [base + (1 if i < resto else 0) for i in range(n_modulos)]


def _ajustar_larguras(
    modulos: list[LayoutModule],
    alvo_mm: float,
    min_mm: float = MIN_MODULE_MM,
    max_mm: float = MAX_MODULE_MM,
) -> None:
    """Distribute the difference between nominal sum and actual span.

    The remainder is split evenly among modules that still have headroom to
    grow (or shrink) without exceeding technical limits.
    """
    if not modulos:
        return

    alvo = max(min_mm * len(modulos), min(float(alvo_mm), max_mm * len(modulos)))
    restante = alvo - sum(m.largura_mm for m in modulos)

    for _ in range(64):
        if abs(restante) <= 1e-6:
            break
        if restante > 0:
            ajustaveis = [m for m in modulos if m.largura_mm < max_mm - 1e-9]
        else:
            ajustaveis = [m for m in modulos if m.largura_mm > min_mm + 1e-9]
        if not ajustaveis:
            break

        parte = restante / len(ajustaveis)
        for m in ajustaveis:
            antiga = m.largura_mm
            nova = min(max_mm, max(min_mm, antiga + parte))
            m.largura_mm = nova
            restante -= nova - antiga


def _modulos_de_portas(
    vao_mm: float,
    tipo: str,
    max_portas: int,
    porta_nominal_mm: float = DOOR_WIDTH_MM,
) -> list[LayoutModule]:
    total_portas = max(1, int(vao_mm / porta_nominal_mm + 0.5))
    portas_por_modulo = _dividir_portas(total_portas, max_portas)
    return [
        LayoutModule(
            tipo=tipo,
            largura_mm=portas * porta_nominal_mm,
            num_portas=portas,
            num_divisoes=(
                auto_divisoes_for_doors(portas) if tipo == "balcao" else 0),
        )
        for portas in portas_por_modulo
    ]


def _modulos_de_gavetas(
    vao_mm: float,
    gavetas_por_modulo: int = 4,
) -> list[LayoutModule]:
    n_modulos = max(1, int(vao_mm / DRAWER_WIDTH_MM + 0.5))
    # Avoid modules narrower than the minimum width when the span is small.
    while n_modulos > 1 and (vao_mm / n_modulos) < MIN_MODULE_MM:
        n_modulos -= 1
    return [
        LayoutModule(
            tipo="gaveteiro",
            largura_mm=vao_mm / n_modulos,
            num_gavetas=max(1, int(gavetas_por_modulo)),
        )
        for _ in range(n_modulos)
    ]


def _intercalar(
    portas: Iterable[LayoutModule],
    gavetas: Iterable[LayoutModule],
) -> list[LayoutModule]:
    """Alternate door and drawer modules, keeping any remaining ones."""
    lista_portas = list(portas)
    lista_gavetas = list(gavetas)
    resultado: list[LayoutModule] = []
    for i in range(max(len(lista_portas), len(lista_gavetas))):
        if i < len(lista_portas):
            resultado.append(lista_portas[i])
        if i < len(lista_gavetas):
            resultado.append(lista_gavetas[i])
    return resultado


def plan_wall_fill(
    space_mm: float,
    categoria: str = "inferior",
    composicao: str = "portas",
    porta_nominal_mm: float = DOOR_WIDTH_MM,
) -> list[LayoutModule]:
    """Plan contiguous modules whose widths sum up to close the span.

    ``categoria``: ``inferior`` or ``aereo``.
    ``composicao``: ``portas``, ``misto`` (base only), or ``gavetas``
    (base only). For wall cabinets (``aereo``), composition is always ``portas``.
    """
    vao = float(space_mm)
    if vao < MIN_MODULE_MM:
        raise ValueError(
            f"O vão precisa ter ao menos {MIN_MODULE_MM:.0f} mm.")

    categoria = _normalizar_categoria(categoria)
    composicao = _normalizar_composicao(composicao, categoria)

    if categoria == "aereo":
        modulos = _modulos_de_portas(
            vao, "aereo", MAX_DOORS_UPPER, porta_nominal_mm)
        _ajustar_larguras(modulos, vao)
        return modulos

    if composicao == "gavetas":
        modulos = _modulos_de_gavetas(vao)
        _ajustar_larguras(modulos, vao)
        return modulos

    if composicao == "misto" and vao >= 800.0:
        # ~60% of the span in door base cabinets and ~40% in drawer banks.
        modulos_portas = _modulos_de_portas(
            vao * 0.60, "balcao", MAX_DOORS_LOWER, porta_nominal_mm)
        modulos_gavetas = _modulos_de_gavetas(vao * 0.40)
        modulos = _intercalar(modulos_portas, modulos_gavetas)
    else:
        modulos = _modulos_de_portas(
            vao, "balcao", MAX_DOORS_LOWER, porta_nominal_mm)

    _ajustar_larguras(modulos, vao)
    return modulos


# ---------------------------------------------------------------------------
# Placement on the wall face
# ---------------------------------------------------------------------------

def directions_from_normal(normal: QVector3D) -> tuple[QVector3D, QVector3D]:
    """Return (horizontal normal, horizontal wall direction)."""
    n_dir = QVector3D(normal.x(), normal.y(), 0.0)
    if n_dir.length() < 1e-6:
        n_dir = QVector3D(0.0, 1.0, 0.0)
    n_dir.normalize()
    u_dir = QVector3D(-n_dir.y(), n_dir.x(), 0.0).normalized()
    return n_dir, u_dir


def face_u_range(
    face_vertices: Iterable[QVector3D],
    u_dir: QVector3D,
) -> tuple[float, float]:
    """Face extent along ``u_dir`` (meters)."""
    projs = [QVector3D.dotProduct(p, u_dir) for p in face_vertices]
    if not projs:
        return 0.0, 0.0
    return min(projs), max(projs)


def place_group_on_wall(
    group,
    n_dir: QVector3D,
    u_dir: QVector3D,
    wall_plane_n: float,
    start_u: float,
    z_base: float,
) -> None:
    """Move ``group`` to sit flush against the wall and start at ``start_u``."""
    from ..domain.module_geometry import get_module_carcass_bounds
    from ..interaction.magnetic_drag import get_bounds_min_projection, get_module_bounds

    b = get_module_carcass_bounds(group) or get_module_bounds(group)
    if b is None:
        return

    cur_min_n = get_bounds_min_projection(b, n_dir)
    cur_min_u = min(
        QVector3D.dotProduct(QVector3D(x, y, 0.0), u_dir)
        for x, y in ((b[0], b[2]), (b[1], b[2]),
                     (b[0], b[3]), (b[1], b[3]))
    )

    shift = (
        n_dir * ((wall_plane_n - cur_min_n) + 0.001)
        + u_dir * (start_u - cur_min_u)
        + QVector3D(0.0, 0.0, z_base - b[4])
    )

    for child in getattr(group, "children", []) or [group]:
        mesh = getattr(child, "mesh", None)
        if mesh and getattr(mesh, "vertices", None):
            for v in mesh.vertices:
                v.position += shift
            mesh._mut_serial = getattr(mesh, "_mut_serial", 0) + 1
        ext = getattr(child, "ext", None)
        if isinstance(ext, dict):
            if "orig_vertices" in ext:
                ext["orig_vertices"] = [
                    orig + shift for orig in ext["orig_vertices"]]
            if "hinge_pivot" in ext and isinstance(ext["hinge_pivot"], QVector3D):
                ext["hinge_pivot"] += shift

    mod_ext = getattr(group, "ext", {}).get("trazomob_module")
    if isinstance(mod_ext, dict):
        old_off = mod_ext.get("offset", (0.0, 0.0, 0.0))
        mod_ext["offset"] = (
            float(old_off[0]) + float(shift.x()),
            float(old_off[1]) + float(shift.y()),
            float(old_off[2]) + float(shift.z()),
        )
