# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Geometria 3D simplificada de ferragens.

Cada ferragem é criada como um grupo filho do módulo (``Group``) e marcada em
``ext["trazomob"]["kind"] = "hardware"``. Isso permite:

* localizá-la facilmente (``is_hardware_group``);
* excluí-la do cutlist / caixaria / cálculos de área;
* ocultá-la no viewport se desejado (``hidden=True``).

São geometrias *esquemáticas*: suficientes para visualizar onde vão as
dobradiças, corrediças, trilhos e pés, sem depender de um CAD paramétrico por
fornecedor.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Tuple

from PySide6.QtGui import QVector3D

from core.group import Group, iter_placements
from core.mesh import Mesh
from ..domain.hardware import HARDWARE_CATALOG

logger = logging.getLogger("trazomob.hardware_geometry")

Coord = Tuple[float, float, float]

_COLOR_METAL_CLARO = (0.78, 0.80, 0.84)
_COLOR_METAL_ESCURO = (0.35, 0.37, 0.42)
_COLOR_IMEX = (0.55, 0.58, 0.64)


def is_hardware_group(group: Any) -> bool:
    """Indica se ``group`` é uma representação 3D de ferragem."""
    if group is None:
        return False
    ext = getattr(group, "ext", None)
    if isinstance(ext, dict):
        tm = ext.get("trazomob")
        if isinstance(tm, dict) and tm.get("kind") == "hardware":
            return True
        if ext.get("trazomob_hardware") is True:
            return True
    name = str(getattr(group, "name", ""))
    return name.startswith("Ferragem -")


def hardware_row(name: str, key: str, mesh: Mesh, module_tag: str = "",
                 linked_piece: str | None = None) -> Group:
    """Cria um grupo filho que representa uma ferragem."""
    tm: Dict[str, Any] = {
        "kind": "hardware",
        "hardware_code": key,
        "nome": name,
        "modulo": module_tag,
    }
    if linked_piece:
        tm["linked_piece"] = linked_piece
    g = Group(mesh, name=f"Ferragem - {name}")
    g.ext = {
        "trazomob": tm,
        "trazomob_hardware": True,
    }
    return g


# ------------------------------------------------------------- primitivas

def _bounds(mesh: Mesh | None):
    if mesh is None or not getattr(mesh, "vertices", None):
        return None
    xs = [v.position.x() for v in mesh.vertices]
    ys = [v.position.y() for v in mesh.vertices]
    zs = [v.position.z() for v in mesh.vertices]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


def _add_box(
    mesh: Mesh,
    x0: float, y0: float, z0: float,
    sx: float, sy: float, sz: float,
    color: tuple[float, float, float] = _COLOR_METAL_ESCURO,
) -> None:
    x1, y1, z1 = x0 + sx, y0 + sy, z0 + sz
    v = [
        QVector3D(x0, y0, z0), QVector3D(x1, y0, z0),
        QVector3D(x1, y1, z0), QVector3D(x0, y1, z0),
        QVector3D(x0, y0, z1), QVector3D(x1, y0, z1),
        QVector3D(x1, y1, z1), QVector3D(x0, y1, z1),
    ]
    faces = [  # (verts, color)
        ([2, 3, 0, 1], color),
        ([4, 5, 6, 7], color),
        ([0, 4, 7, 3], color),
        ([1, 2, 6, 5], color),
        ([3, 7, 6, 2], color),
        ([0, 1, 5, 4], color),
    ]
    for idxs, c in faces:
        f = mesh.add_face([v[i] for i in idxs])
        f.attrs["color"] = c


def _add_cylinder_y(
    mesh: Mesh,
    cx: float, cz: float,
    y0: float, y1: float,
    r: float,
    color: tuple[float, float, float] = _COLOR_METAL_CLARO,
    segs: int = 16,
) -> None:
    circ0 = [
        QVector3D(cx + r * math.cos(2 * math.pi * i / segs), y0,
                   cz + r * math.sin(2 * math.pi * i / segs))
        for i in range(segs)
    ]
    circ1 = [
        QVector3D(cx + r * math.cos(2 * math.pi * i / segs), y1,
                   cz + r * math.sin(2 * math.pi * i / segs))
        for i in range(segs)
    ]
    f0 = mesh.add_face(list(reversed(circ0)))
    f0.attrs["color"] = color
    f1 = mesh.add_face(circ1)
    f1.attrs["color"] = color
    for i in range(segs):
        nxt = (i + 1) % segs
        f = mesh.add_face([circ0[i], circ0[nxt], circ1[nxt], circ1[i]])
        f.attrs["color"] = color


def _add_cylinder_z(
    mesh: Mesh,
    cx: float, cy: float,
    z0: float, z1: float,
    r: float,
    color: tuple[float, float, float] = _COLOR_METAL_CLARO,
    segs: int = 16,
) -> None:
    circ0 = [
        QVector3D(cx + r * math.cos(2 * math.pi * i / segs), cy + r * math.sin(2 * math.pi * i / segs), z0)
        for i in range(segs)
    ]
    circ1 = [
        QVector3D(cx + r * math.cos(2 * math.pi * i / segs), cy + r * math.sin(2 * math.pi * i / segs), z1)
        for i in range(segs)
    ]
    f0 = mesh.add_face(list(reversed(circ0)))
    f0.attrs["color"] = color
    f1 = mesh.add_face(circ1)
    f1.attrs["color"] = color
    for i in range(segs):
        nxt = (i + 1) % segs
        f = mesh.add_face([circ0[i], circ0[nxt], circ1[nxt], circ1[i]])
        f.attrs["color"] = color


def _hinge_positions(altura_m: float, n: int) -> List[float]:
    """Posições Z (m) das dobradiças, com afastamento de 100 mm dos cantos."""
    h = float(altura_m or 0.0)
    if h <= 0:
        return []
    base, topo = 0.1, h - 0.1
    if n <= 1:
        return [base]
    passo = (topo - base) / (n - 1)
    return [base + i * passo for i in range(n)]


def _drawer_index_from_name(name: str | None) -> int | None:
    """Extrai o índice 1-based da gaveta a partir do nome da peça."""
    import re
    m = re.search(r"(?:gaveta|frente)\s*(\d+)", (name or "").lower())
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _add_telescopic_slide_outer(
    mesh: Mesh,
    x_wall: float,
    dir_in: float,
    y0: float,
    length: float,
    cz: float,
) -> None:
    """Desenha o trilho externo fixo na lateral do móvel (perfil C de aço zincado com abas e batente traseiro)."""
    h_out = 0.045       # 45 mm de altura padrão de corrediça telescópica
    w_web = 0.0022      # espessura da alma
    w_flange = 0.0115   # largura total das abas superior/inferior (total ~12.7 mm)
    t_flange = 0.0022   # espessura da dobra superior/inferior
    t_lip = 0.0045      # aba de retenção das esferas

    z_bot = cz - h_out * 0.5
    z_top = cz + h_out * 0.5

    if dir_in > 0:
        x_web = x_wall
        x_fl = x_wall
        x_lip = x_wall + w_flange - 0.0018
    else:
        x_web = x_wall - w_web
        x_fl = x_wall - w_flange
        x_lip = x_wall - w_flange

    # Alma vertical aparafusada na lateral do armário
    _add_box(mesh, x_web, y0, z_bot, w_web, length, h_out, _COLOR_METAL_ESCURO)
    # Aba horizontal inferior e superior do perfil C
    _add_box(mesh, x_fl, y0, z_bot, w_flange, length, t_flange, _COLOR_METAL_CLARO)
    _add_box(mesh, x_fl, y0, z_top - t_flange, w_flange, length, t_flange, _COLOR_METAL_CLARO)
    # Dobra frontal de retenção (guias de esferas superior e inferior)
    _add_box(mesh, x_lip, y0, z_bot + t_flange, 0.0018, length, t_lip, _COLOR_IMEX)
    _add_box(mesh, x_lip, y0, z_top - t_flange - t_lip, 0.0018, length, t_lip, _COLOR_IMEX)
    # Amortecedor / batente traseiro escuro no fim do curso
    _add_box(
        mesh,
        x_fl,
        y0 + length - 0.018,
        z_bot + 0.004,
        w_flange,
        0.018,
        h_out - 0.008,
        (0.18, 0.20, 0.23),
    )


def _add_telescopic_slide_middle(
    mesh: Mesh,
    x_wall: float,
    dir_in: float,
    y0: float,
    length: float,
    cz: float,
) -> None:
    """Desenha a gaiola intermediária de esferas (corre a 50% do curso da gaveta)."""
    h_mid = 0.032
    w_mid = 0.0045
    z_bot = cz - h_mid * 0.5
    if dir_in > 0:
        x0 = x_wall + 0.0032
    else:
        x0 = x_wall - 0.0032 - w_mid

    # Perfil intermediário
    _add_box(mesh, x0, y0 + 0.006, z_bot, w_mid, max(0.06, length - 0.012), h_mid, _COLOR_IMEX)
    # Abas de rolamento superior e inferior
    _add_box(mesh, x0, y0 + 0.006, z_bot, w_mid + 0.002, max(0.06, length - 0.012), 0.0025, _COLOR_METAL_CLARO)
    _add_box(mesh, x0, y0 + 0.006, z_bot + h_mid - 0.0025, w_mid + 0.002, max(0.06, length - 0.012), 0.0025, _COLOR_METAL_CLARO)


def _add_telescopic_slide_inner(
    mesh: Mesh,
    x_box: float,
    dir_out: float,
    y0: float,
    length: float,
    cz: float,
) -> None:
    """Desenha o perfil interno estreito fixado na lateral da caixa de gaveta (corre 100% com a gaveta)."""
    h_in = 0.020
    w_in = 0.0042
    z_bot = cz - h_in * 0.5
    if dir_out < 0:
        # Lateral esquerda da gaveta: perfil fica à esquerda de x_box (entre x_box - w_in e x_box)
        x0 = x_box - w_in
    else:
        # Lateral direita da gaveta: perfil fica à direita de x_box (entre x_box e x_box + w_in)
        x0 = x_box

    # Barra interna de aço polido presa na caixa da gaveta
    _add_box(mesh, x0, y0, z_bot, w_in, length, h_in, _COLOR_METAL_CLARO)
    # Abas horizontais do perfil U interno
    _add_box(mesh, x0, y0, z_bot, w_in, length, 0.002, _COLOR_METAL_ESCURO)
    _add_box(mesh, x0, y0, z_bot + h_in - 0.002, w_in, length, 0.002, _COLOR_METAL_ESCURO)
    # Trava plástica de saque (gatilho preto no meio do perfil)
    _add_box(
        mesh,
        x0 - (0.0005 if dir_out < 0 else 0.0),
        y0 + min(0.055, length * 0.22),
        cz - 0.0045,
        w_in + 0.0005,
        0.022,
        0.009,
        (0.15, 0.16, 0.18),
    )


def _make_drawer_runners(
    name: str, key: str, bounds: tuple[float, ...], num_gavetas: int,
    module_tag: str = "",
    pieces: List[Group] | None = None,
) -> List[Group]:
    """Cria corrediças telescópicas de 3 estágios realistas posicionadas exatamente nas laterais de cada gaveta.

    Em módulos mistos (ex: ``balcao_misto``), localiza a caixa real de cada gaveta
    (``Gaveta i - Lat Esq`` e ``Gaveta i - Lat Dir``) para posicionar os trilhos
    exatamente no vão do gaveteiro (seja à esquerda ou à direita), evitando colocar
    trilhos na lateral do vão das portas.

    Gera 3 estágios por gaveta:
    1. Trilho Externo (fixo na lateral/divisória do móvel)
    2. Gaiola Intermediária (acompanha 50% da abertura da gaveta via ``slide_scale=0.5``)
    3. Trilho Interno (fixado na lateral da caixa da gaveta, acompanha 100% da abertura)
    """
    n = max(int(num_gavetas or 0), 0)
    if n == 0:
        return []
    min_x, max_x, min_y, max_y, min_z, max_z = bounds
    h = max_z - min_z
    cell = h / n
    default_length = max(0.15, (max_y - min_y) - 0.075)
    groups: List[Group] = []

    # Agrupa peças por índice de gaveta (1..n)
    by_drawer: Dict[int, Dict[str, Tuple[Group, Tuple[float, ...]]]] = {}
    targets: Dict[int, str] = {}
    for p in pieces or []:
        pname = str(getattr(p, "name", "") or "")
        if pname.startswith("Ferragem -"):
            continue
        idx = _drawer_index_from_name(pname)
        if idx is None:
            continue
        b = _bounds(getattr(p, "mesh", None))
        if b is None:
            continue
        dmap = by_drawer.setdefault(idx, {})
        low = pname.lower()
        if "lat esq" in low:
            dmap["lat_esq"] = (p, b)
        elif "lat dir" in low:
            dmap["lat_dir"] = (p, b)
        elif "frente" in low and "contra" not in low:
            dmap["frente"] = (p, b)
        elif "fundo" in low:
            dmap["fundo"] = (p, b)
        # Prioriza vincular à Frente ou à Lateral da gaveta
        if idx not in targets or ("frente" in low and "contra" not in low):
            targets[idx] = pname

    for i in range(n):
        idx = i + 1
        dmap = by_drawer.get(idx, {})
        target = targets.get(idx)

        if "lat_esq" in dmap and "lat_dir" in dmap:
            _, b_esq = dmap["lat_esq"]
            _, b_dir = dmap["lat_dir"]
            # Face externa esquerda da caixa da gaveta = b_esq[0]
            # Face externa direita da caixa da gaveta = b_dir[1]
            x_box_esq = b_esq[0]
            x_box_dir = b_dir[1]
            # A folga da corrediça telescópica fica entre a lateral do móvel/divisória e a caixa da gaveta (~13mm de cada lado)
            folga_lado = 0.013
            x_wall_esq = x_box_esq - folga_lado
            x_wall_dir = x_box_dir + folga_lado
            y_start = b_esq[2] + 0.004
            length = max(0.12, (b_esq[3] - b_esq[2]) - 0.008)
            cz = (b_esq[4] + b_esq[5]) * 0.5
        elif "frente" in dmap:
            _, b_fr = dmap["frente"]
            x_wall_esq = b_fr[0] + 0.012
            x_wall_dir = b_fr[1] - 0.012
            x_box_esq = x_wall_esq + 0.013
            x_box_dir = x_wall_dir - 0.013
            y_start = b_fr[3] + 0.010
            length = default_length
            cz = (b_fr[4] + b_fr[5]) * 0.5
        else:
            x_wall_esq = min_x + 0.015
            x_wall_dir = max_x - 0.015
            x_box_esq = x_wall_esq + 0.013
            x_box_dir = x_wall_dir - 0.013
            y_start = min_y + 0.030
            length = default_length
            cz = min_z + cell * (i + 0.5)

        # 1. Estágio Interno + Intermediário (vinculados ao movimento da gaveta; mantém 1 grupo principal com o nome esperado)
        mesh_inner = Mesh()
        _add_telescopic_slide_inner(mesh_inner, x_box_esq, -1.0, y_start, length, cz)
        _add_telescopic_slide_inner(mesh_inner, x_box_dir, +1.0, y_start, length, cz)
        g_inner = hardware_row(
            f"Corrediças Gaveta {idx} (2x) {module_tag or name}".strip(),
            key, mesh_inner, module_tag, linked_piece=target,
        )
        groups.append(g_inner)

        # 2. Estágio Intermediário (corre a 50% do curso da gaveta)
        mesh_mid = Mesh()
        _add_telescopic_slide_middle(mesh_mid, x_wall_esq, +1.0, y_start, length, cz)
        _add_telescopic_slide_middle(mesh_mid, x_wall_dir, -1.0, y_start, length, cz)
        g_mid = hardware_row(
            f"Guia Telescópica Gaveta {idx} (2x) {module_tag or name}".strip(),
            key, mesh_mid, module_tag, linked_piece=target,
        )
        g_mid.ext["slide_scale"] = 0.5
        groups.append(g_mid)

        # 3. Estágio Externo fixo no armário/divisória (não possui linked_piece, permanece fixo no móvel!)
        mesh_outer = Mesh()
        _add_telescopic_slide_outer(mesh_outer, x_wall_esq, +1.0, y_start, length, cz)
        _add_telescopic_slide_outer(mesh_outer, x_wall_dir, -1.0, y_start, length, cz)
        g_outer = hardware_row(
            f"Trilho Fixo Gaveta {idx} (2x) {module_tag or name}".strip(),
            key, mesh_outer, module_tag, linked_piece=None,
        )
        groups.append(g_outer)

    return groups


def _make_sliding_tracks(
    name: str, key: str, bounds: tuple[float, ...], num_rails: int,
    module_tag: str = "",
) -> Group | None:
    """Trilhos superior e inferior para portas de correr."""
    n = max(int(num_rails or 0), 0)
    if n == 0:
        return None
    min_x, max_x, min_y, max_y, min_z, max_z = bounds
    w = max_x - min_x
    # duas vias por trilho (trilho duplo)
    num_channels = 2
    mesh = Mesh()
    for z in (min_z + 0.02, max_z - 0.022):
        for c in range(num_channels):
            y_off = 0.012 + c * 0.030
            _add_box(mesh, min_x + 0.005, min_y + y_off, z,
                      w - 0.010, 0.016, 0.006, _COLOR_IMEX)
    return hardware_row(f"Trilhos ({n}x) {module_tag or name}".strip(), key, mesh, module_tag)


def _make_feet(name: str, key: str, bounds: tuple[float, ...], n: int,
               module_tag: str = "") -> Group | None:
    count = max(int(n or 0), 0)
    if count == 0:
        return None
    min_x, max_x, min_y, max_y, min_z, max_z = bounds
    from itertools import repeat
    if count <= 4:
        positions = [(min_x + 0.06, min_y + 0.06), (max_x - 0.06, min_y + 0.06),
                     (min_x + 0.06, max_y - 0.06), (max_x - 0.06, max_y - 0.06)]
    else:
        positions = [(min_x + 0.06, min_y + 0.06), (max_x - 0.06, min_y + 0.06)]
    mesh = Mesh()
    for x, y in positions[:count]:
        _add_cylinder_z(mesh, x, y, min_z - 0.08, min_z, 0.030,
                        (0.35, 0.36, 0.40), segs=12)
    return hardware_row(f"Pés Niveladores ({count}x) {module_tag or name}".strip(), key, mesh, module_tag)


def build_module_hardware_3d(
    master: Group | None,
    hardware_items: Any,
    pieces: List[Group] | None = None,
    params: Dict[str, Any] | None = None,
) -> List[Group]:
    """Cria grupos 3D esquemáticos de ferragem e os anexa ao módulo.

    Retorna a lista de grupos criados. Nunca lança exceção.
    """
    if master is None:
        return []
    params = params or {}
    try:
        from ..domain.hardware import deserialize_hardware
        if isinstance(hardware_items, str):
            import json
            hardware_items = json.loads(hardware_items)
        items = (
            deserialize_hardware(hardware_items)
            if not isinstance(hardware_items, list)
            or (hardware_items and not hasattr(hardware_items[0], "key"))
            else hardware_items
        )
    except Exception:
        items = []

    if not items:
        return []

    # Aceita tanto lista de dicts quanto HardwareItem
    try:
        from ..domain.hardware import HardwareItem  # noqa: F401  (type check only)
    except Exception:
        logger.debug("HardwareItem indisponível para verificação de tipo", exc_info=True)

    bb_by_piece: List[Tuple[Group, Tuple[float, ...]]] = []
    for p in pieces or []:
        b = _bounds(getattr(p, "mesh", None))
        if b:
            bb_by_piece.append((p, b))

    module_tag = str(params.get("tipo", "Módulo"))
    by_key = {getattr(it, "key", None): it for it in items}

    # limites do módulo (caixaria, aproximadamente, incluindo frentes)
    xs: List[float] = []
    ys: List[float] = []
    zs: List[float] = []
    for _p, b in bb_by_piece:
        xs.extend([b[0], b[1]])
        ys.extend([b[2], b[3]])
        zs.extend([b[4], b[5]])
    full = (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)) if xs else None

    criadas: List[Group] = []

    # ── Dobradiças 35mm (Caneco + Braço Articulado + Calço Cruciforme) ──
    dobra = by_key.get("dobradica_35mm")
    if dobra is not None and bb_by_piece:
        door_seq = 0
        for p, b in bb_by_piece:
            p_ext = getattr(p, "ext", None)
            p_tm = p_ext.get("trazomob", {}) if isinstance(p_ext, dict) else {}
            if not isinstance(p_tm, dict):
                continue
            d_side = p_tm.get("door_side")
            if d_side not in ("left", "right"):
                continue
            door_seq += 1
            ops = p_tm.get("operacoes") or []
            canecos = [op for op in ops if "caneco" in str(op.get("descricao", "")).lower()]
            p_min_x, p_max_x, p_min_y, p_max_y, p_min_z, p_max_z = b
            alt_m = p_max_z - p_min_z
            if canecos:
                zs_hinge = [p_min_z + (float(op.get("y", 100.0)) / 1000.0) for op in canecos]
            else:
                zs_hinge = [p_min_z + z_rel for z_rel in _hinge_positions(alt_m, 2)]

            mesh_cup = Mesh()
            mesh_plate = Mesh()
            # Face traseira da porta fica em p_max_y (pois a porta está em oy - E_frente .. oy)
            y_back_door = p_max_y
            is_left = (d_side == "left")
            # Centro X do caneco (a 22.5 mm da borda da dobradiça)
            x_cup = (p_min_x + 0.0225) if is_left else (p_max_x - 0.0225)
            # Face interna da lateral/divisória adjacente (~12 mm para dentro a partir da borda da porta)
            x_wall_in = (p_min_x + 0.012) if is_left else (p_max_x - 0.012)

            for hz in zs_hinge:
                # Caneco Ø35mm embutido/aparente na face interna da porta + flange oval
                _add_cylinder_y(mesh_cup, x_cup, hz, y_back_door - 0.002, y_back_door + 0.003, 0.0175, _COLOR_METAL_CLARO, segs=14)
                _add_box(
                    mesh_cup,
                    x_cup - 0.008,
                    y_back_door,
                    hz - 0.026,
                    0.016,
                    0.0025,
                    0.052,
                    _COLOR_IMEX,
                )
                # Pescoço articulado saindo do caneco em direção à lateral
                if is_left:
                    _add_box(mesh_cup, x_wall_in, y_back_door, hz - 0.007, max(0.006, x_cup - x_wall_in), 0.014, 0.014, _COLOR_METAL_CLARO)
                else:
                    _add_box(mesh_cup, x_cup, y_back_door, hz - 0.007, max(0.006, x_wall_in - x_cup), 0.014, 0.014, _COLOR_METAL_CLARO)

                # Calço cruciforme e braço fixo na lateral/divisória (37 mm para dentro do armário)
                x_plate = x_wall_in if is_left else (x_wall_in - 0.004)
                # Placa base cruciforme vertical (parafusos a 37mm da borda frontal, espaçados 32mm em Z)
                _add_box(mesh_plate, x_plate, y_back_door + 0.022, hz - 0.024, 0.004, 0.024, 0.048, _COLOR_METAL_ESCURO)
                # Corpo do braço de regulagem clipado no calço
                x_arm = x_wall_in if is_left else (x_wall_in - 0.009)
                _add_box(mesh_plate, x_arm, y_back_door + 0.003, hz - 0.008, 0.009, 0.052, 0.016, _COLOR_METAL_CLARO)

            pname = str(getattr(p, "name", "Porta"))
            lado_tag = "Esq" if is_left else "Dir"
            g_cup = hardware_row(
                f"Dobradiças #{door_seq} ({len(zs_hinge)}x) [{lado_tag}]",
                "dobradica_35mm",
                mesh_cup,
                module_tag,
                linked_piece=pname,
            )
            criadas.append(g_cup)
            criadas.append(hardware_row(
                f"Dobradiças Calço #{door_seq} ({len(zs_hinge)}x) [{lado_tag}]",
                "calco_dobradica",
                mesh_plate,
                module_tag,
                linked_piece=None,
            ))

    # ── Corrediças ──────────────────────────────────────────────────
    corredica = None
    if "corredica_40" in by_key:
        corredica = by_key["corredica_40"]
    elif "corredica_50" in by_key:
        corredica = by_key["corredica_50"]
    num_gavetas = int(params.get("num_gavetas", 0) or 0)
    tipo_lower = str(params.get("tipo", "")).lower()
    # balcao_forno construído sem gaveta e módulos de cama (corrediças laterais) não devem renderizar corrediças 3D frontais.
    if tipo_lower == "balcao_forno" and not bool(params.get("tem_gaveta", True)):
        num_gavetas = 0
    if tipo_lower.startswith("cama_") or tipo_lower in ("bicama", "beliche"):
        num_gavetas = 0
    if corredica is not None and full is not None and num_gavetas:
        for g in _make_drawer_runners(
            module_tag, getattr(corredica, "key", "corredica_40"), full, num_gavetas, module_tag,
            pieces=[p for p, _b in bb_by_piece],
        ):
            criadas.append(g)

    # ── Trilhos ─────────────────────────────────────────────────────
    trilho = by_key.get("trilho_correr")
    num_portas = int(params.get("num_portas", 0) or 0)
    if trilho is not None and full is not None and "correr" in str(params.get("tipo", "")).lower():
        g = _make_sliding_tracks(module_tag, "trilho_correr", full, num_portas, module_tag)
        if g is not None:
            criadas.append(g)

    # ── Kit Porta-Tempero Aramado ───────────────────────────────────
    kit_tempero = by_key.get("kit_porta_tempero_aramado")
    if kit_tempero is not None and full is not None:
        target_front = None
        for p, _b in bb_by_piece:
            p_name = getattr(p, "name", "").lower()
            if "porta-tempero" in p_name and ("frente" in p_name or "gaveta" in p_name):
                target_front = getattr(p, "name", "")
                break
        cor_aramado_param = str(params.get("cor_aramado", "cromado")).lower()
        color_wire = (0.15, 0.15, 0.15) if "preto" in cor_aramado_param or "black" in cor_aramado_param else (0.82, 0.84, 0.88)
        min_x, max_x, min_y, max_y, min_z, max_z = full
        larg_kit = max(0.08, (max_x - min_x) - 0.05)
        prof_kit = max(0.20, (max_y - min_y) - 0.06)
        alt_kit = max(0.30, (max_z - min_z) - 0.12)
        cx = (min_x + max_x) / 2.0
        y_ini = min_y + 0.02
        z_base = min_z + 0.04

        mesh_basket = Mesh()
        # 1. Guias telescópicas inferiores fixadas na lateral/base
        _add_box(mesh_basket, min_x + 0.012, y_ini + 0.01, z_base - 0.01, 0.012, prof_kit, 0.035, _COLOR_IMEX)

        # 2. Estrutura vertical do cesto (chassi aramado)
        _add_cylinder_z(mesh_basket, min_x + 0.025, y_ini + 0.02, z_base, z_base + alt_kit, 0.005, color_wire, segs=10)
        _add_cylinder_z(mesh_basket, min_x + 0.025, y_ini + prof_kit - 0.02, z_base, z_base + alt_kit, 0.005, color_wire, segs=10)
        _add_cylinder_y(mesh_basket, min_x + 0.025, z_base + alt_kit, y_ini + 0.02, y_ini + prof_kit - 0.02, 0.005, color_wire, segs=10)

        # 3. Suportes de fixação na contra-face da frente da gaveta
        _add_box(mesh_basket, cx - larg_kit/2, y_ini - 0.012, z_base + 0.05, larg_kit, 0.012, 0.025, _COLOR_IMEX)
        _add_box(mesh_basket, cx - larg_kit/2, y_ini - 0.012, z_base + alt_kit - 0.06, larg_kit, 0.012, 0.025, _COLOR_IMEX)

        # 4. Duas bandejas aramadas (Inferior e Superior)
        for h_b in [z_base + 0.02, z_base + alt_kit * 0.55]:
            # Contorno retangular superior da bandeja
            x1, x2 = cx - larg_kit / 2, cx + larg_kit / 2
            y1, y2 = y_ini + 0.01, y_ini + prof_kit - 0.01
            h_barreira = 0.065
            # Aros perimetrais
            _add_box(mesh_basket, x1, y1, h_b, larg_kit, 0.004, 0.004, color_wire)
            _add_box(mesh_basket, x1, y2 - 0.004, h_b, larg_kit, 0.004, 0.004, color_wire)
            _add_box(mesh_basket, x1, y1, h_b, 0.004, prof_kit - 0.02, 0.004, color_wire)
            _add_box(mesh_basket, x2 - 0.004, y1, h_b, 0.004, prof_kit - 0.02, 0.004, color_wire)

            # Gradil superior de contenção (borda alta)
            _add_box(mesh_basket, x1, y1, h_b + h_barreira, larg_kit, 0.004, 0.004, color_wire)
            _add_box(mesh_basket, x1, y2 - 0.004, h_b + h_barreira, larg_kit, 0.004, 0.004, color_wire)
            _add_box(mesh_basket, x1, y1, h_b + h_barreira, 0.004, prof_kit - 0.02, 0.004, color_wire)
            _add_box(mesh_basket, x2 - 0.004, y1, h_b + h_barreira, 0.004, prof_kit - 0.02, 0.004, color_wire)

            # Arames verticais da grade
            step_y = 0.06
            curr_y = y1 + step_y
            while curr_y < y2 - 0.02:
                _add_cylinder_z(mesh_basket, x1 + 0.002, curr_y, h_b, h_b + h_barreira, 0.002, color_wire, segs=8)
                _add_cylinder_z(mesh_basket, x2 - 0.002, curr_y, h_b, h_b + h_barreira, 0.002, color_wire, segs=8)
                curr_y += step_y

            # Arames longitudinais do fundo da bandeja
            step_x = 0.025
            curr_x = x1 + 0.015
            while curr_x < x2 - 0.01:
                _add_cylinder_y(mesh_basket, curr_x, h_b + 0.002, y1, y2, 0.002, color_wire, segs=8)
                curr_x += step_x

        g_kit = hardware_row(
            f"Kit Porta-Tempero Aramado {module_tag or target_front or 'Gaveta'}".strip(),
            "kit_porta_tempero_aramado",
            mesh_basket,
            module_tag,
            linked_piece=target_front,
        )
        criadas.append(g_kit)

    # ── Pés niveladores ─────────────────────────────────────────────
    pes = by_key.get("pes_nivelador")
    if pes is not None and full is not None:
        g = _make_feet(module_tag, "pes_nivelador", full, int(pes.quantidade or 4), module_tag)
        if g is not None:
            criadas.append(g)

    for g in criadas:
        master.children = list(getattr(master, "children", []) or []) + [g]

    return criadas
