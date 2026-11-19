# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Biblioteca de perfis de alumínio (puxador perfil) baseada em SEÇÃO 2D.

Cada perfil é descrito pela sua seção transversal (como no desenho do catálogo),
em milímetros, no sistema de coordenadas da posição "topo":

    u  -> profundidade.  u = 0 é a FACE FRONTAL da porta; u > 0 entra na
          espessura do MDF (para trás); u < 0 sai para a frente da porta.
    v  -> altura.        v = 0 é o TOPO da chapa de MDF já descontada;
          v > 0 sobe (região do perfil); v < 0 desce sobre a chapa.

    desconto_mm  -> quanto a chapa de MDF é cortada para encaixar o perfil.
    esp_ref_mm   -> espessura de MDF para a qual a seção foi desenhada. Pontos
                    com u >= esp_ref_mm são deslocados automaticamente quando a
                    porta tem outra espessura (aba traseira acompanha o MDF).
    furos        -> lista opcional de polígonos internos (perfis ocos).

A seção é extrudada ao longo da porta/gaveta na posição escolhida:
    topo     -> ao longo de X, como desenhado;
    base     -> ao longo de X, espelhada verticalmente;
    lateral  -> ao longo de Z, girada 90° (o "para cima" vira para fora da borda).
"""
from __future__ import annotations

import copy
import json
import math
import os
from typing import Any

from PySide6.QtGui import QVector3D

Point = tuple[float, float]

_LIB_PATH = os.environ.get(
    "INGETRAZO_PERFIS_PATH",
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "assets", "profiles", "perfis_biblioteca.json"),
)


def _arc(cu: float, cv: float, ru: float, rv: float, a0: float, a1: float, n: int = 10) -> list[list[float]]:
    pts = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        pts.append([round(cu + ru * math.cos(a), 3), round(cv + rv * math.sin(a), 3)])
    return pts


def _default_profiles() -> list[dict[str, Any]]:
    gola = (
        [[0, 0], [18, 0], [18, -15.4], [19.5, -15.4], [19.5, 34.5], [0, 34.5], [0, 31], [2, 31]]
        + _arc(2, 16.5, 13, 14.5, 90, -90, 14)[1:-1]
        + [[2, 2], [0, 2]]
    )
    facetato = [
        [0, 0], [18, 0], [18, -15.5], [19.5, -15.5], [19.5, 10], [-15, 10],
        *_arc(-15, 7.5, 2.5, 2.5, 90, 180, 6)[1:],
        [-17.5, 2.5], [-14.5, 2.5], [-14.5, 4.5], [-16, 4.5], [-16, 7.5], [0, 7.5],
    ]
    canal_c = [
        [0, 0], [16.3, 0], [16.3, 42], [0, 42], [0, 36], [1.5, 36], [1.5, 37.3],
        [14.8, 37.3], [14.8, 4.7], [1.5, 4.7], [1.5, 6], [0, 6],
    ]
    sp7000 = [
        [0, 0], [18, 0], [18, -11.5], [22, -11.5], [22, 2], [1, 2], [1, 41],
        [-4, 41], [-4, -11.5], [0, -11.5],
    ]
    return [
        {"id": "gola", "nome": "Gola Côncavo", "codigo": "RM-030", "desconto_mm": 34.5,
         "esp_ref_mm": 18.0, "pontos": gola, "furos": []},
        {"id": "facetato", "nome": "Facetato / Aba Curva", "codigo": "RM-027", "desconto_mm": 10.0,
         "esp_ref_mm": 18.0, "pontos": facetato, "furos": []},
        {"id": "canal_c", "nome": "Canal Duplo / Perfil C", "codigo": "RM-032", "desconto_mm": 42.0,
         "esp_ref_mm": 18.0, "pontos": canal_c, "furos": []},
        {"id": "sp7000", "nome": "Haste Reta", "codigo": "SP-7000", "desconto_mm": 2.0,
         "esp_ref_mm": 18.0, "pontos": sp7000, "furos": []},
    ]


# ----------------------------------------------------------------------------
# Biblioteca (persistência JSON)
# ----------------------------------------------------------------------------
_cache: list[dict[str, Any]] | None = None


def library_path() -> str:
    return _LIB_PATH


def load_library(force: bool = False) -> list[dict[str, Any]]:
    global _cache
    if _cache is not None and not force:
        return _cache
    perfis: list[dict[str, Any]] = []
    try:
        if os.path.isfile(_LIB_PATH):
            with open(_LIB_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            perfis = [p for p in data.get("perfis", []) if _is_valid(p)]
    except (OSError, ValueError):
        perfis = []
    if not perfis:
        perfis = _default_profiles()
    _cache = perfis
    return _cache


def save_library(perfis: list[dict[str, Any]]) -> None:
    global _cache
    valid = [p for p in perfis if _is_valid(p)]
    with open(_LIB_PATH, "w", encoding="utf-8") as fh:
        json.dump({"versao": 1, "perfis": valid}, fh, ensure_ascii=False, indent=2)
    _cache = valid


def reset_library() -> list[dict[str, Any]]:
    save_library(_default_profiles())
    return load_library()


def get_profile(perfil_id: str | None) -> dict[str, Any]:
    lib = load_library()
    pid = (perfil_id or "").lower()
    for p in lib:
        if p.get("id", "").lower() == pid:
            return p
    return lib[0] if lib else _default_profiles()[0]


def profile_label(p: dict[str, Any]) -> str:
    cod = p.get("codigo") or ""
    return f"{p.get('nome', p.get('id'))} ({cod})" if cod else str(p.get("nome", p.get("id")))


def new_profile_id(base: str, lib: list[dict[str, Any]]) -> str:
    slug = "".join(ch if ch.isalnum() else "_" for ch in base.lower()).strip("_") or "perfil"
    ids = {p.get("id") for p in lib}
    cand, n = slug, 2
    while cand in ids:
        cand = f"{slug}_{n}"
        n += 1
    return cand


def _is_valid(p: Any) -> bool:
    try:
        return isinstance(p, dict) and bool(p.get("id")) and len(p.get("pontos", [])) >= 3
    except TypeError:
        return False


# ----------------------------------------------------------------------------
# Geometria 2D
# ----------------------------------------------------------------------------
def signed_area(pts: list[Point]) -> float:
    a = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return a * 0.5


def _clean(pts: list[Any]) -> list[Point]:
    out: list[Point] = []
    for p in pts:
        q = (float(p[0]), float(p[1]))
        if not out or abs(out[-1][0] - q[0]) > 1e-6 or abs(out[-1][1] - q[1]) > 1e-6:
            out.append(q)
    if len(out) > 1 and abs(out[0][0] - out[-1][0]) < 1e-6 and abs(out[0][1] - out[-1][1]) < 1e-6:
        out.pop()
    return out


def section_loops(perfil: dict[str, Any], esp_mdf_mm: float | None = None) -> tuple[list[Point], list[list[Point]]]:
    """Retorna (contorno CCW, furos CW) em mm, ajustados à espessura do MDF."""
    esp_ref = float(perfil.get("esp_ref_mm", 18.0) or 18.0)
    delta = 0.0 if esp_mdf_mm is None else float(esp_mdf_mm) - esp_ref

    def adj(loop: list[Point]) -> list[Point]:
        if abs(delta) < 1e-6:
            return loop
        return [((u + delta) if u >= esp_ref - 1e-6 else u, v) for (u, v) in loop]

    outer = adj(_clean(perfil.get("pontos", [])))
    if signed_area(outer) < 0:
        outer.reverse()
    holes = []
    for h in perfil.get("furos", []) or []:
        hl = adj(_clean(h))
        if len(hl) >= 3:
            if signed_area(hl) > 0:
                hl.reverse()
            holes.append(hl)
    return outer, holes


def section_bbox(perfil: dict[str, Any]) -> tuple[float, float, float, float]:
    pts = _clean(perfil.get("pontos", []))
    us = [p[0] for p in pts]
    vs = [p[1] for p in pts]
    return min(us), min(vs), max(us), max(vs)


# ----------------------------------------------------------------------------
# Extrusão 3D
# ----------------------------------------------------------------------------
def extrude_profile(
    mesh,
    perfil: dict[str, Any],
    origin: tuple[float, float, float],
    size: tuple[float, float, float],
    eff_pos: str,
    door_side: str,
    desc_m: float,
    rgb: tuple[float, float, float],
) -> int:
    """Extruda a seção do perfil ao longo da porta (origin/size = porta inteira, em m).

    Retorna o número de faces criadas.
    """
    ox, oy, oz = origin
    sx, sy, sz = size
    esp_mm = sy * 1000.0
    outer, holes = section_loops(perfil, esp_mm)
    if len(outer) < 3:
        return 0

    lateral = eff_pos in ("extensao", "lateral") and door_side not in ("drawer", "flap")

    if lateral:
        right_edge = door_side in ("left", "single")
        length = sz
        gap = 0.0002

        def to3d(u: float, v: float, t: float) -> QVector3D:
            y = oy + u / 1000.0
            if right_edge:
                x = ox + sx - desc_m + gap + v / 1000.0
            else:
                x = ox + desc_m - gap - v / 1000.0
            return QVector3D(x, y, oz + t)

        # Base (U, V, T): U=+Y, V=±X, T=+Z
        mirrored = _det((0, 1, 0), (1 if right_edge else -1, 0, 0), (0, 0, 1)) < 0
    elif eff_pos == "base":
        length = sx
        gap = 0.0002

        def to3d(u: float, v: float, t: float) -> QVector3D:
            return QVector3D(ox + t, oy + u / 1000.0, oz + desc_m - gap - v / 1000.0)

        mirrored = _det((0, 1, 0), (0, 0, -1), (1, 0, 0)) < 0
    else:  # topo
        length = sx
        gap = 0.0002
        z0 = oz + sz - desc_m + gap

        def to3d(u: float, v: float, t: float) -> QVector3D:
            return QVector3D(ox + t, oy + u / 1000.0, z0 + v / 1000.0)

        mirrored = _det((0, 1, 0), (0, 0, 1), (1, 0, 0)) < 0

    rgb_lado = (rgb[0] * 0.82, rgb[1] * 0.82, rgb[2] * 0.82)
    count = 0

    def add(pts: list[QVector3D], color, holes3d=None) -> None:
        nonlocal count
        if mirrored:
            pts = list(reversed(pts))
            if holes3d:
                holes3d = [list(reversed(h)) for h in holes3d]
        f = mesh.add_face(pts, holes3d) if holes3d else mesh.add_face(pts)
        f.attrs["color"] = color
        count += 1

    # Paredes (contorno externo e furos)
    for loop in [outer, *holes]:
        n = len(loop)
        for i in range(n):
            ua, va = loop[i]
            ub, vb = loop[(i + 1) % n]
            add([to3d(ua, va, 0.0), to3d(ub, vb, 0.0), to3d(ub, vb, length), to3d(ua, va, length)], rgb)

    # Tampas (as pontas mostram o desenho da seção)
    cap_end = [to3d(u, v, length) for (u, v) in outer]
    holes_end = [[to3d(u, v, length) for (u, v) in h] for h in holes]
    add(cap_end, rgb_lado, holes_end or None)
    cap_start = [to3d(u, v, 0.0) for (u, v) in reversed(outer)]
    holes_start = [[to3d(u, v, 0.0) for (u, v) in reversed(h)] for h in holes]
    add(cap_start, rgb_lado, holes_start or None)
    return count


def _det(a, b, c) -> float:
    return (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )


# ----------------------------------------------------------------------------
# Desenho técnico (pixmap)
# ----------------------------------------------------------------------------
def render_profile_pixmap(perfil: dict[str, Any], width: int = 115, height: int = 80, cotas: bool = True):
    """Desenha a seção do perfil (com a chapa de MDF tracejada e cotas)."""
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QPixmap

    pm = QPixmap(width, height)
    pm.fill(QColor("#F1F5F9"))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)

    outer, holes = section_loops(perfil)
    if len(outer) < 3:
        p.end()
        return pm
    esp = float(perfil.get("esp_ref_mm", 18.0) or 18.0)
    desc = float(perfil.get("desconto_mm", 0.0) or 0.0)
    umin = min(min(u for u, _ in outer), 0.0)
    umax = max(max(u for u, _ in outer), esp)
    vmin = min(min(v for _, v in outer), -max(10.0, desc * 0.4))
    vmax = max(v for _, v in outer)

    margin = 16 if cotas and width >= 100 else 4
    sw = (width - 2 * margin) / max(1e-6, umax - umin)
    sh = (height - 2 * margin) / max(1e-6, vmax - vmin)
    s = min(sw, sh)
    offx = margin + ((width - 2 * margin) - (umax - umin) * s) / 2
    offy = margin + ((height - 2 * margin) - (vmax - vmin) * s) / 2

    def mp(u: float, v: float) -> QPointF:
        return QPointF(offx + (u - umin) * s, offy + (vmax - v) * s)

    # Chapa MDF
    mdf_rect = QRectF(mp(0, 0), mp(esp, vmin))
    p.setPen(QPen(QColor("#A16207"), 1, Qt.DashLine))
    p.setBrush(QBrush(QColor(234, 179, 8, 60)))
    p.drawRect(mdf_rect.normalized())

    # Seção
    path = QPainterPath()
    path.setFillRule(Qt.OddEvenFill)
    for loop in [outer, *holes]:
        path.moveTo(mp(*loop[0]))
        for q in loop[1:]:
            path.lineTo(mp(*q))
        path.closeSubpath()
    p.setPen(QPen(QColor("#1E293B"), 1.2))
    p.setBrush(QBrush(QColor("#94A3B8")))
    p.drawPath(path)

    if cotas and width >= 100:
        f = QFont()
        f.setPointSizeF(6.5 if width < 200 else 8.5)
        p.setFont(f)
        p.setPen(QPen(QColor("#DC2626"), 1))
        bu0, bv0, bu1, bv1 = section_bbox(perfil)
        # Altura total
        x = mp(bu1, 0).x() + 5
        p.drawLine(QPointF(x, mp(0, bv1).y()), QPointF(x, mp(0, bv0).y()))
        p.drawText(QPointF(x + 2, (mp(0, bv1).y() + mp(0, bv0).y()) / 2 + 3), f"{bv1 - bv0:g}")
        # Largura total
        y = mp(0, bv0).y() + 9
        p.drawLine(QPointF(mp(bu0, 0).x(), y - 3), QPointF(mp(bu1, 0).x(), y - 3))
        p.drawText(QPointF((mp(bu0, 0).x() + mp(bu1, 0).x()) / 2 - 6, y + 5), f"{bu1 - bu0:g}")
        # Código
        p.setPen(QColor("#334155"))
        p.drawText(QPointF(3, 10), str(perfil.get("codigo") or perfil.get("id")))
    p.end()
    return pm


def copy_profile(p: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(p)
