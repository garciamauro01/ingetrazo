# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Utilitários de geração de malhas 3D para chapas de MDF, puxadores e usinagens."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from PySide6.QtGui import QVector3D

from core.group import Group
from core.mesh import Mesh


def _resolve_texture_path(base_tex_dir: Path, filename: str) -> Path:
    """Resolve texture path across root, mdf/, and marmores/ subfolders."""
    for candidate in (
        base_tex_dir / filename,
        base_tex_dir / "mdf" / filename,
        base_tex_dir / "marmores" / filename,
    ):
        if candidate.exists():
            return candidate
    return base_tex_dir / filename


# Um rebuild de bancada consulta a textura de cada peça (10-20 chamadas). O
# catálogo é imutável durante a edição, então cache por (caminho, mtime, tamanho).
_CATALOG_ENTRIES_CACHE: dict[tuple[str, int, int], list[dict[str, Any]]] = {}


def _load_catalog_entries(catalog_path: Path) -> list[dict[str, Any]]:
    """Lê um catalog.json no máximo uma vez enquanto o arquivo não mudar."""
    try:
        stat = catalog_path.stat()
    except OSError:
        return []
    key = (str(catalog_path), stat.st_mtime_ns, stat.st_size)
    cached = _CATALOG_ENTRIES_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        entries = json.loads(catalog_path.read_text(encoding="utf-8"))
    except Exception:
        entries = []
    if not isinstance(entries, list):
        entries = []
    # Evita acumular versões antigas se o catálogo for reescrito várias vezes.
    if len(_CATALOG_ENTRIES_CACHE) >= 8:
        _CATALOG_ENTRIES_CACHE.clear()
    _CATALOG_ENTRIES_CACHE[key] = entries
    return entries


def _lookup_catalog_texture(base_tex_dir: Path, mat_lower: str) -> dict[str, Any] | None:
    """Busca textura dinamicamente nos arquivos catalog.json de mdf/ e marmores/."""
    for sub in ("mdf", "marmores"):
        catalog_path = base_tex_dir / sub / "catalog.json"
        for entry in _load_catalog_entries(catalog_path):
            nome = str(entry.get("nome", "")).lower()
            arquivo = str(entry.get("arquivo", ""))
            if not nome or not arquivo:
                continue
            if nome in mat_lower or mat_lower in nome:
                tex_path = base_tex_dir / sub / arquivo
                if tex_path.exists():
                    return {
                        "path": str(tex_path),
                        "sw": float(entry.get("sw", 0.80)),
                        "sh": float(entry.get("sh", 0.80)),
                    }
    return None


def _get_material_texture(material: str) -> dict[str, Any] | None:
    """Retorna os atributos de textura para materiais de marmoraria/pedra."""
    mat_lower = (material or "").lower()
    base_tex_dir = Path(__file__).resolve().parents[1] / "assets" / "textures"

    if mat_lower:
        catalog_hit = _lookup_catalog_texture(base_tex_dir, mat_lower)
        if catalog_hit is not None:
            return catalog_hit

    # 1. Granito Preto São Gabriel / Preto Absoluto
    if "sao gabriel" in mat_lower or "gabriel" in mat_lower:
        tex_path = _resolve_texture_path(base_tex_dir, "granito_preto_sao_gabriel.jpg")
        if tex_path.exists():
            return {"path": str(tex_path), "sw": 0.50, "sh": 0.336}
    if "preto absoluto" in mat_lower or "granito preto" in mat_lower:
        tex_path = _resolve_texture_path(base_tex_dir, "granito_preto_absoluto.jpg")
        if tex_path.exists():
            return {"path": str(tex_path), "sw": 0.60, "sh": 0.60}

    # 2. Mármore / Quartzo Calacatta (Veios dourados/cinzas no fundo branco)
    if "calacatta" in mat_lower or "calacata" in mat_lower:
        tex_path = _resolve_texture_path(base_tex_dir, "marmore_calacatta.jpg")
        if tex_path.exists():
            return {"path": str(tex_path), "sw": 0.80, "sh": 0.80}

    # 3. Mármore Nero Marquina (Fundo preto com veios brancos marcantes)
    if "nero" in mat_lower or "marquina" in mat_lower:
        tex_path = _resolve_texture_path(base_tex_dir, "marmore_nero_marquina.jpg")
        if tex_path.exists():
            return {"path": str(tex_path), "sw": 0.90, "sh": 0.90}

    # 4. Mármore Pietra Grey (Cinza grafite sofisticado com veios finos)
    if "pietra" in mat_lower or "grey" in mat_lower:
        tex_path = _resolve_texture_path(base_tex_dir, "marmore_pietra_grey.jpg")
        if tex_path.exists():
            return {"path": str(tex_path), "sw": 0.90, "sh": 0.60}

    # 5. Granito Branco Siena (Claro pontilhado)
    if "siena" in mat_lower or "parana" in mat_lower or "branco siena" in mat_lower:
        tex_path = _resolve_texture_path(base_tex_dir, "granito_branco_siena.jpg")
        if tex_path.exists():
            return {"path": str(tex_path), "sw": 0.60, "sh": 0.60}

    # 6. Mármore Armani Gris (Marrom acinzentado luxuoso)
    if "armani" in mat_lower or "gris" in mat_lower:
        tex_path = _resolve_texture_path(base_tex_dir, "marmore_armani_gris.jpg")
        if tex_path.exists():
            return {"path": str(tex_path), "sw": 0.80, "sh": 0.80}

    # 6b. Novos acabamentos nobres de bancada
    if "travertino" in mat_lower or "bege" in mat_lower:
        tex_path = _resolve_texture_path(base_tex_dir, "marmore_travertino_bege.jpg")
        if tex_path.exists():
            return {"path": str(tex_path), "sw": 0.80, "sh": 0.80}

    if "silestone" in mat_lower or "quartzo branco" in mat_lower:
        tex_path = _resolve_texture_path(base_tex_dir, "quartzo_branco_silestone.jpg")
        if tex_path.exists():
            return {"path": str(tex_path), "sw": 0.70, "sh": 0.70}

    if "concreto" in mat_lower or "cimento" in mat_lower:
        tex_path = _resolve_texture_path(base_tex_dir, "concreto_cimento_queimado.jpg")
        if tex_path.exists():
            return {"path": str(tex_path), "sw": 0.90, "sh": 0.90}

    if "teca" in mat_lower:
        tex_path = _resolve_texture_path(base_tex_dir, "bancada_madeira_teca.jpg")
        if tex_path.exists():
            return {"path": str(tex_path), "sw": 1.00, "sh": 0.60}

    if "lamelado" in mat_lower:
        tex_path = _resolve_texture_path(base_tex_dir, "bancada_carvalho_lamelado.jpg")
        if tex_path.exists():
            return {"path": str(tex_path), "sw": 1.00, "sh": 0.60}

    if "gold" in mat_lower or "dourado" in mat_lower:
        tex_path = _resolve_texture_path(base_tex_dir, "marmore_calacatta_gold.jpg")
        if tex_path.exists():
            return {"path": str(tex_path), "sw": 0.90, "sh": 0.90}

    # 7. MDF Madeirado / Texturas de Marcenaria de Alta Resolução
    if "autentic" in mat_lower:
        tex_path = _resolve_texture_path(base_tex_dir, "mdf_autentic_arauco.jpg")
        if tex_path.exists():
            return {"path": str(tex_path), "sw": 2.75, "sh": 2.46}

    if "ciliegio" in mat_lower or "florenca" in mat_lower or "florênça" in mat_lower:
        tex_path = _resolve_texture_path(base_tex_dir, "mdf_ciliegio_florenca.jpg")
        if tex_path.exists():
            return {"path": str(tex_path), "sw": 2.75, "sh": 1.85}

    if "castanho" in mat_lower:
        tex_path = _resolve_texture_path(base_tex_dir, "mdf_castanho.jpg")
        if tex_path.exists():
            return {"path": str(tex_path), "sw": 2.00, "sh": 3.01}

    if "carvalho" in mat_lower or "boreal" in mat_lower:
        tex_path_custom = _resolve_texture_path(base_tex_dir, "mdf_carvalho.jpg")
        if tex_path_custom.exists():
            return {"path": str(tex_path_custom), "sw": 1.85, "sh": 2.78}
        tex_path = _resolve_texture_path(base_tex_dir, "mdf_carvalho_boreal.jpg")
        if tex_path.exists():
            return {"path": str(tex_path), "sw": 0.60, "sh": 0.60}

    if "freijo" in mat_lower or "freijó" in mat_lower:
        tex_path = _resolve_texture_path(base_tex_dir, "mdf_louro_freijo.jpg")
        if tex_path.exists():
            return {"path": str(tex_path), "sw": 2.01, "sh": 3.01}

    if "nogueira" in mat_lower or "imbuia" in mat_lower:
        tex_path = _resolve_texture_path(base_tex_dir, "mdf_nogueira.jpg")
        if tex_path.exists():
            return {"path": str(tex_path), "sw": 0.60, "sh": 0.60}

    # Fallback se tiver 'pedra' ou 'granito' genérico
    if "granito" in mat_lower or "marmore" in mat_lower or "mármore" in mat_lower:
        tex_path = _resolve_texture_path(base_tex_dir, "granito_preto_sao_gabriel.jpg")
        if tex_path.exists():
            return {"path": str(tex_path), "sw": 0.50, "sh": 0.336}

    return None


def _make_board_mesh(
    origin: tuple[float, float, float],
    size: tuple[float, float, float],
    color: tuple[float, float, float] = (0.94, 0.94, 0.92),
    fita_c1: bool = False,
    fita_c2: bool = False,
    fita_l1: bool = False,
    fita_l2: bool = False,
    cor_fita: tuple[float, float, float] | None = None,
    is_pedra: bool = False,
    texture: dict[str, Any] | None = None,
    piece_name: str = "",
    operacoes: list[dict[str, Any]] | None = None,
) -> Mesh:
    """Cria uma malha de chapa retangular com acabamento visual de fita de borda e usinagem 3D sólida de rasgo do fundo."""
    ox, oy, oz = origin
    sx, sy, sz = size
    mesh = Mesh()

    p0 = QVector3D(ox, oy, oz)
    p1 = QVector3D(ox + sx, oy, oz)
    p2 = QVector3D(ox + sx, oy + sy, oz)
    p3 = QVector3D(ox, oy + sy, oz)
    p4 = QVector3D(ox, oy, oz + sz)
    p5 = QVector3D(ox + sx, oy, oz + sz)
    p6 = QVector3D(ox + sx, oy + sy, oz + sz)
    p7 = QVector3D(ox, oy + sy, oz + sz)

    if cor_fita is None:
        cor_fita = (
            max(0.0, min(1.0, color[0] * 0.94)),
            max(0.0, min(1.0, color[1] * 0.94)),
            max(0.0, min(1.0, color[2] * 0.94)),
        )
    cor_mdf_cru = (0.74, 0.58, 0.42)  # Miolo de MDF cru exposto

    # Identifica orientação da chapa
    dims = [abs(sx), abs(sy), abs(sz)]
    min_dim = min(dims)

    # Normaliza lista de operações se vier como MachiningOp dataclass
    if operacoes:
        raw_ops = []
        for op in operacoes:
            if hasattr(op, "to_dict"):
                raw_ops.append(op.to_dict())
            elif isinstance(op, dict):
                raw_ops.append(op)
        operacoes = raw_ops

    # Verifica se há operação de rasgo do fundo
    rasgo_op = None
    if operacoes and not is_pedra:
        for op in operacoes:
            if op.get("tipo") == "rasgo":
                rasgo_op = op
                break

    cor_rasgo = (0.35, 0.35, 0.38)

    if rasgo_op is not None and abs(sx - min_dim) < 1e-5:
        # Chapa lateral com rasgo vertical de fundo (espessura em X)
        is_direita = "direit" in piece_name.lower() or "right" in piece_name.lower()
        recuo_y_m = float(rasgo_op.get("y", 15.0)) / 1000.0
        larg_canal_m = float(rasgo_op.get("largura", 6.0)) / 1000.0
        prof_canal_m = float(rasgo_op.get("profundidade", 7.0)) / 1000.0

        y_max = oy + sy
        y1 = y_max - recuo_y_m - larg_canal_m
        y2 = y_max - recuo_y_m

        cor_c1 = cor_fita if fita_c1 else cor_mdf_cru
        cor_c2 = cor_fita if fita_c2 else cor_mdf_cru
        cor_l1 = cor_fita if fita_l1 else cor_mdf_cru
        cor_l2 = cor_fita if fita_l2 else cor_mdf_cru

        if not is_direita:
            # Lateral Esquerda: face interna em ox + sx (normal +X), rasgo avança em -X
            xf = ox + sx - prof_canal_m
            py1 = QVector3D(ox + sx, y1, oz)
            py2 = QVector3D(ox + sx, y2, oz)
            qy1 = QVector3D(ox + sx, y1, oz + sz)
            qy2 = QVector3D(ox + sx, y2, oz + sz)
            r1 = QVector3D(xf, y1, oz)
            r2 = QVector3D(xf, y2, oz)
            s1 = QVector3D(xf, y1, oz + sz)
            s2 = QVector3D(xf, y2, oz + sz)

            faces_data = [
                ([p0, p3, p2, py2, r2, r1, py1, p1], cor_l1),
                ([p4, p5, qy1, s1, s2, qy2, p6, p7], cor_l2),
                ([p0, p1, p5, p4], cor_c1),
                ([p2, p3, p7, p6], cor_c2),
                ([p0, p4, p7, p3], color),
                ([p1, py1, qy1, p5], color),
                ([py2, p2, p6, qy2], color),
                ([py1, r1, s1, qy1], cor_rasgo),
                ([r2, py2, qy2, s2], cor_rasgo),
                ([r1, r2, s2, s1], cor_rasgo),
            ]
        else:
            # Lateral Direita: face interna em ox (normal -X), rasgo avança em +X
            xf = ox + prof_canal_m
            py1 = QVector3D(ox, y1, oz)
            py2 = QVector3D(ox, y2, oz)
            qy1 = QVector3D(ox, y1, oz + sz)
            qy2 = QVector3D(ox, y2, oz + sz)
            r1 = QVector3D(xf, y1, oz)
            r2 = QVector3D(xf, y2, oz)
            s1 = QVector3D(xf, y1, oz + sz)
            s2 = QVector3D(xf, y2, oz + sz)

            faces_data = [
                ([p0, py1, r1, r2, py2, p3, p2, p1], cor_l1),
                ([p4, p5, p6, p7, qy2, s2, s1, qy1], cor_l2),
                ([p0, p1, p5, p4], cor_c1),
                ([p2, p3, p7, p6], cor_c2),
                ([p1, p2, p6, p5], color),
                ([p0, p4, qy1, py1], color),
                ([py2, qy2, p7, p3], color),
                ([py1, qy1, s1, r1], cor_rasgo),
                ([r2, s2, qy2, py2], cor_rasgo),
                ([r1, s1, s2, r2], cor_rasgo),
            ]

    elif rasgo_op is not None and abs(sz - min_dim) < 1e-5:
        # Chapa horizontal (Base Inferior ou Tampo Superior) com rasgo horizontal ao longo de X
        is_tampo = "tampo" in piece_name.lower() or "upper" in piece_name.lower() or "top" in piece_name.lower()
        recuo_y_m = float(rasgo_op.get("y", 15.0)) / 1000.0
        larg_canal_m = float(rasgo_op.get("largura", 6.0)) / 1000.0
        prof_canal_m = float(rasgo_op.get("profundidade", 7.0)) / 1000.0

        y_max = oy + sy
        y1 = y_max - recuo_y_m - larg_canal_m
        y2 = y_max - recuo_y_m

        cor_c1 = cor_fita if fita_c1 else cor_mdf_cru
        cor_c2 = cor_fita if fita_c2 else cor_mdf_cru
        cor_l1 = cor_fita if fita_l1 else cor_mdf_cru
        cor_l2 = cor_fita if fita_l2 else cor_mdf_cru

        if not is_tampo:
            # Base Inferior: rasgo na face SUPERIOR (oz + sz, normal +Z), canal desce para -Z
            zf = oz + sz - prof_canal_m
            py1 = QVector3D(ox, y1, oz + sz)
            py2 = QVector3D(ox, y2, oz + sz)
            qy1 = QVector3D(ox + sx, y1, oz + sz)
            qy2 = QVector3D(ox + sx, y2, oz + sz)
            r1 = QVector3D(ox, y1, zf)
            r2 = QVector3D(ox, y2, zf)
            s1 = QVector3D(ox + sx, y1, zf)
            s2 = QVector3D(ox + sx, y2, zf)

            faces_data = [
                ([p0, p3, p2, p1], color),
                ([p4, p5, qy1, py1], color),
                ([py2, qy2, p6, p7], color),
                ([p0, p1, p5, p4], cor_c1),
                ([p2, p3, p7, p6], cor_c2),
                ([p0, p4, py1, r1, r2, py2, p7, p3], cor_l1),
                ([p1, p2, p6, qy2, s2, s1, qy1, p5], cor_l2),
                ([py1, qy1, s1, r1], cor_rasgo),
                ([qy2, py2, r2, s2], cor_rasgo),
                ([r1, s1, s2, r2], cor_rasgo),
            ]
        else:
            # Tampo Superior: rasgo na face INFERIOR (oz, normal -Z), canal sobe para +Z
            zf = oz + prof_canal_m
            py1 = QVector3D(ox, y1, oz)
            py2 = QVector3D(ox, y2, oz)
            qy1 = QVector3D(ox + sx, y1, oz)
            qy2 = QVector3D(ox + sx, y2, oz)
            r1 = QVector3D(ox, y1, zf)
            r2 = QVector3D(ox, y2, zf)
            s1 = QVector3D(ox + sx, y1, zf)
            s2 = QVector3D(ox + sx, y2, zf)

            faces_data = [
                ([p4, p5, p6, p7], color),
                ([p0, p1, p5, p4], cor_c1),
                ([p2, p3, p7, p6], cor_c2),
                ([p0, p4, p7, p3, py2, r2, r1, py1], cor_l1),
                ([p1, qy1, s1, s2, qy2, p2, p6, p5], cor_l2),
                ([p0, py1, qy1, p1], color),
                ([p3, p2, qy2, py2], color),
                ([py1, r1, s1, qy1], cor_rasgo),
                ([r2, py2, qy2, s2], cor_rasgo),
                ([r1, r2, s2, s1], cor_rasgo),
            ]

    elif is_pedra:
        faces_data = [
            ([p0, p3, p2, p1], color),  # inferior (-Z)
            ([p4, p5, p6, p7], color),  # superior (+Z)
            ([p0, p1, p5, p4], color),  # frontal (-Y)
            ([p2, p3, p7, p6], color),  # traseira (+Y)
            ([p0, p4, p7, p3], color),  # esquerda (-X)
            ([p1, p2, p6, p5], color),  # direita (+X)
        ]
    else:
        if abs(sy - min_dim) < 1e-5:
            # Chapa vertical frontal (Portas / Frentes de Gaveta)
            cor_c1 = cor_fita if fita_c1 else cor_mdf_cru
            cor_c2 = cor_fita if fita_c2 else cor_mdf_cru
            cor_l1 = cor_fita if fita_l1 else cor_mdf_cru
            cor_l2 = cor_fita if fita_l2 else cor_mdf_cru

            faces_data = [
                ([p0, p3, p2, p1], cor_c1),  # inferior (-Z)
                ([p4, p5, p6, p7], cor_c2),  # superior (+Z)
                ([p0, p1, p5, p4], color),   # frontal (-Y)
                ([p2, p3, p7, p6], color),   # traseira (+Y)
                ([p0, p4, p7, p3], cor_l1),  # esquerda (-X)
                ([p1, p2, p6, p5], cor_l2),  # direita (+X)
            ]
        elif abs(sx - min_dim) < 1e-5:
            # Chapa lateral (espessura em X)
            cor_c1 = cor_fita if fita_c1 else cor_mdf_cru
            cor_c2 = cor_fita if fita_c2 else cor_mdf_cru
            cor_l1 = cor_fita if fita_l1 else cor_mdf_cru
            cor_l2 = cor_fita if fita_l2 else cor_mdf_cru

            faces_data = [
                ([p0, p3, p2, p1], cor_l1),  # inferior (-Z)
                ([p4, p5, p6, p7], cor_l2),  # superior (+Z)
                ([p0, p1, p5, p4], cor_c1),  # frontal (-Y)
                ([p2, p3, p7, p6], cor_c2),  # traseira (+Y)
                ([p0, p4, p7, p3], color),   # esquerda (-X)
                ([p1, p2, p6, p5], color),   # direita (+X)
            ]
        else:
            # Chapa horizontal / base / prateleira (espessura em Z)
            cor_c1 = cor_fita if fita_c1 else cor_mdf_cru
            cor_c2 = cor_fita if fita_c2 else cor_mdf_cru
            cor_l1 = cor_fita if fita_l1 else cor_mdf_cru
            cor_l2 = cor_fita if fita_l2 else cor_mdf_cru

            faces_data = [
                ([p0, p3, p2, p1], color),   # inferior (-Z)
                ([p4, p5, p6, p7], color),   # superior (+Z)
                ([p0, p1, p5, p4], cor_c1),  # frontal (-Y)
                ([p2, p3, p7, p6], cor_c2),  # traseira (+Y)
                ([p0, p4, p7, p3], cor_l1),  # esquerda (-X)
                ([p1, p2, p6, p5], cor_l2),  # direita (+X)
            ]

    for pts, c in faces_data:
        f = mesh.add_face(pts)
        f.attrs["color"] = c
        if texture:
            f.attrs["texture"] = dict(texture)

    return mesh


def _make_box_faces(mesh: Mesh, origin: tuple[float, float, float], size: tuple[float, float, float], color: tuple[float, float, float]):
    """Adiciona as 6 faces de um bloco 3D retangular à malha."""
    ox, oy, oz = origin
    sx, sy, sz = size
    p0 = QVector3D(ox, oy, oz)
    p1 = QVector3D(ox + sx, oy, oz)
    p2 = QVector3D(ox + sx, oy + sy, oz)
    p3 = QVector3D(ox, oy + sy, oz)
    p4 = QVector3D(ox, oy, oz + sz)
    p5 = QVector3D(ox + sx, oy, oz + sz)
    p6 = QVector3D(ox + sx, oy + sy, oz + sz)
    p7 = QVector3D(ox, oy + sy, oz + sz)

    faces_pts = [
        [p0, p3, p2, p1],  # inferior (-Z)
        [p4, p5, p6, p7],  # superior (+Z)
        [p0, p1, p5, p4],  # frontal (-Y)
        [p2, p3, p7, p6],  # traseira (+Y)
        [p0, p4, p7, p3],  # esquerda (-X)
        [p1, p2, p6, p5],  # direita (+X)
    ]
    for pts in faces_pts:
        f = mesh.add_face(pts)
        f.attrs["color"] = color


def _contorno_retangular_xy(
    x0: float, y0: float, w: float, h: float, raio: float = 0.0, segmentos: int = 8,
) -> list[tuple[float, float]]:
    """Contorno 2D (anti-horário, visto de +Z) de um retângulo de canto reto ou arredondado.

    Usado para o recorte de cuba na pedra e para o contorno da bacia. Com ``raio`` > 0
    cada canto vira um arco de 90° discretizado em ``segmentos`` partes.
    """
    r = max(0.0, min(raio, (w / 2.0) - 1e-4, (h / 2.0) - 1e-4))
    if r < 1e-4:
        return [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)]
    centros = [
        (x0 + w - r, y0 + r, -90.0),      # canto inferior direito
        (x0 + w - r, y0 + h - r, 0.0),    # canto superior direito
        (x0 + r, y0 + h - r, 90.0),       # canto superior esquerdo
        (x0 + r, y0 + r, 180.0),          # canto inferior esquerdo
    ]
    pts: list[tuple[float, float]] = []
    for cx, cy, a0 in centros:
        for i in range(segmentos + 1):
            a = math.radians(a0 + 90.0 * i / segmentos)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _make_slab_with_holes_mesh(
    x0: float, y0: float, z0: float,
    largura: float, profundidade: float, espessura: float,
    furos_xy: list[list[tuple[float, float]]],
    color: tuple[float, float, float],
    cor_borda: tuple[float, float, float] | None = None,
    cor_recorte: tuple[float, float, float] | None = None,
    texture: dict[str, Any] | None = None,
) -> Mesh:
    """Cria uma chapa maciça INTEIRIÇA com recortes vazados reais (furos na face superior e inferior).

    - Face superior/inferior: um único polígono com ``hole_loops`` (triangulado por earcut).
    - Paredes externas: 4 quads (bordas polidas).
    - Paredes do recorte: 1 quad por segmento do contorno, voltados para o vão do recorte.
    """
    mesh = Mesh()
    z1 = z0 + espessura
    cor_borda = cor_borda or color
    cor_recorte = cor_recorte or tuple(max(0.0, c * 0.85) for c in color)
    externo = [
        (x0, y0), (x0 + largura, y0),
        (x0 + largura, y0 + profundidade), (x0, y0 + profundidade),
    ]

    # Face superior (+Z): contorno anti-horário, furos horários
    f_top = mesh.add_face(
        [QVector3D(x, y, z1) for x, y in externo],
        [[QVector3D(x, y, z1) for x, y in reversed(furo)] for furo in furos_xy] or None,
    )
    f_top.attrs["color"] = color
    if texture:
        f_top.attrs["texture"] = dict(texture)

    # Face inferior (-Z): orientação invertida
    f_bot = mesh.add_face(
        [QVector3D(x, y, z0) for x, y in reversed(externo)],
        [[QVector3D(x, y, z0) for x, y in furo] for furo in furos_xy] or None,
    )
    f_bot.attrs["color"] = color
    if texture:
        f_bot.attrs["texture"] = dict(texture)

    # Paredes externas (normal para fora)
    n = len(externo)
    for i in range(n):
        ax, ay = externo[i]
        bx, by = externo[(i + 1) % n]
        f = mesh.add_face([
            QVector3D(ax, ay, z0), QVector3D(bx, by, z0),
            QVector3D(bx, by, z1), QVector3D(ax, ay, z1),
        ])
        f.attrs["color"] = cor_borda
        if texture:
            f.attrs["texture"] = dict(texture)

    # Paredes internas do recorte (normal apontando para o vão)
    for furo in furos_xy:
        m = len(furo)
        for i in range(m):
            ax, ay = furo[i]
            bx, by = furo[(i + 1) % m]
            f = mesh.add_face([
                QVector3D(bx, by, z0), QVector3D(ax, ay, z0),
                QVector3D(ax, ay, z1), QVector3D(bx, by, z1),
            ])
            f.attrs["color"] = cor_recorte
            if texture:
                f.attrs["texture"] = dict(texture)
    return mesh


def _make_bowl_mesh(
    x0: float, y0: float, largura: float, profundidade: float,
    raio: float, z_topo: float, altura: float,
    cor_parede: tuple[float, float, float],
    cor_fundo: tuple[float, float, float],
    conicidade: float = 0.010,
    segmentos: int = 12,
    mat_name: str = "Cuba Inox",
) -> Mesh:
    """Cria a bacia de uma cuba como um sólido de casca fechada (estanque / manifold).

    O contorno do topo coincide com o recorte da pedra (cuba de embutir sob a pedra).
    A parede e o fundo possuem espessura de chapa (2mm), formando um sólido 100% fechado.
    """
    mesh = Mesh()
    esp_chapa = 0.002
    c = max(0.0, min(conicidade, (largura / 2.0) - 0.02, (profundidade / 2.0) - 0.02))
    topo_in = _contorno_retangular_xy(x0, y0, largura, profundidade, raio, segmentos)
    topo_out = _contorno_retangular_xy(
        x0 - esp_chapa, y0 - esp_chapa,
        largura + 2 * esp_chapa, profundidade + 2 * esp_chapa,
        raio + esp_chapa if raio > 1e-4 else 0.0, segmentos
    )
    fundo_in = _contorno_retangular_xy(x0 + c, y0 + c, largura - 2 * c, profundidade - 2 * c, raio, segmentos)
    fundo_out = _contorno_retangular_xy(
        x0 + c - esp_chapa, y0 + c - esp_chapa,
        largura - 2 * c + 2 * esp_chapa, profundidade - 2 * c + 2 * esp_chapa,
        raio + esp_chapa if raio > 1e-4 else 0.0, segmentos
    )
    if len(fundo_in) != len(topo_in):
        fundo_in = topo_in
    if len(fundo_out) != len(topo_out):
        fundo_out = topo_out

    z_fundo_in = z_topo - altura
    z_fundo_out = z_fundo_in - esp_chapa

    m = len(topo_in)
    for i in range(m):
        i_next = (i + 1) % m
        at_in, bt_in = topo_in[i], topo_in[i_next]
        af_in, bf_in = fundo_in[i], fundo_in[i_next]
        at_out, bt_out = topo_out[i], topo_out[i_next]
        af_out, bf_out = fundo_out[i], fundo_out[i_next]

        # Parede interna (normal apontando para dentro da bacia)
        f_in = mesh.add_face([
            QVector3D(bf_in[0], bf_in[1], z_fundo_in),
            QVector3D(af_in[0], af_in[1], z_fundo_in),
            QVector3D(at_in[0], at_in[1], z_topo),
            QVector3D(bt_in[0], bt_in[1], z_topo),
        ])
        f_in.attrs["color"] = cor_parede
        f_in.attrs["mat"] = mat_name

        # Parede externa (normal apontando para fora da bacia)
        f_out = mesh.add_face([
            QVector3D(af_out[0], af_out[1], z_fundo_out),
            QVector3D(bf_out[0], bf_out[1], z_fundo_out),
            QVector3D(bt_out[0], bt_out[1], z_topo),
            QVector3D(at_out[0], at_out[1], z_topo),
        ])
        f_out.attrs["color"] = cor_parede
        f_out.attrs["mat"] = mat_name

        # Borda superior de fechamento (anel entre parede externa e interna)
        f_rim = mesh.add_face([
            QVector3D(at_out[0], at_out[1], z_topo),
            QVector3D(bt_out[0], bt_out[1], z_topo),
            QVector3D(bt_in[0], bt_in[1], z_topo),
            QVector3D(at_in[0], at_in[1], z_topo),
        ])
        f_rim.attrs["color"] = cor_parede
        f_rim.attrs["mat"] = mat_name

    # Fundo interno (normal +Z)
    f_fundo_in = mesh.add_face([QVector3D(x, y, z_fundo_in) for x, y in fundo_in])
    f_fundo_in.attrs["color"] = cor_fundo
    f_fundo_in.attrs["mat"] = mat_name

    # Fundo externo (normal -Z)
    f_fundo_out = mesh.add_face([QVector3D(x, y, z_fundo_out) for x, y in reversed(fundo_out)])
    f_fundo_out.attrs["color"] = cor_fundo
    f_fundo_out.attrs["mat"] = mat_name
    return mesh


def _make_gourmet_faucet_mesh(
    base_center: tuple[float, float, float],
    cor_metal: tuple[float, float, float] = (0.86, 0.88, 0.90),
    cor_detalhe: tuple[float, float, float] = (0.25, 0.25, 0.27),
    segmentos: int = 24,
) -> Mesh:
    """Gera um modelo 3D realista de torneira monocomando gourmet com bica alta em arco curvo.

    Utiliza resolução cilíndrica de 24 segmentos (padrão de círculos do IngeTrazo/SketchUp)
    para garantir reflexos suaves e contínuos em renderizadores fotorrealistas.

    Inclui:
    - Base cilíndrica com anel cromado de vedação;
    - Corpo vertical cilíndrico esguio;
    - Alavanca monocomando cilíndrica inclinada 45°;
    - Bica em pescoço de ganso / arco suave em 90° avançando sobre a cuba;
    - Arejador com ponteira detalhada.
    """
    mesh = Mesh()
    bx, by, bz = base_center
    cor_cromo = cor_metal
    cor_preto = cor_detalhe

    def add_cylinder(cx, cy, z0, z1, r, color, mat_name="Metal Cromado", segs=segmentos):
        circ0 = [
            QVector3D(cx + r * math.cos(2 * math.pi * i / segs), cy + r * math.sin(2 * math.pi * i / segs), z0)
            for i in range(segs)
        ]
        circ1 = [
            QVector3D(cx + r * math.cos(2 * math.pi * i / segs), cy + r * math.sin(2 * math.pi * i / segs), z1)
            for i in range(segs)
        ]
        # Tampa inferior
        f0 = mesh.add_face(list(reversed(circ0)))
        f0.attrs["color"] = color
        f0.attrs["mat"] = mat_name
        # Tampa superior
        f1 = mesh.add_face(circ1)
        f1.attrs["color"] = color
        f1.attrs["mat"] = mat_name
        # Parede cilíndrica
        for i in range(segs):
            i_next = (i + 1) % segs
            f = mesh.add_face([circ0[i], circ0[i_next], circ1[i_next], circ1[i]])
            f.attrs["color"] = color
            f.attrs["mat"] = mat_name

    # 1. Base / Canopla de fixação (raio 24mm, altura 12mm)
    add_cylinder(bx, by, bz, bz + 0.012, 0.024, cor_cromo, mat_name="Metal Cromado", segs=segmentos)

    # 2. Corpo inferior do misturador (raio 18mm, altura 70mm)
    add_cylinder(bx, by, bz + 0.0122, bz + 0.082, 0.018, cor_cromo, mat_name="Metal Cromado", segs=segmentos)

    # 3. Alavanca monocomando lateral (haste cilíndrica saindo na diagonal +Y/+X)
    lx0, ly0, lz0 = bx + 0.015, by, bz + 0.055
    add_cylinder(lx0, ly0, lz0, lz0 + 0.008, 0.009, cor_preto, mat_name="Metal Preto", segs=segmentos)
    # Haste da alavanca com seção cilíndrica real (16 segmentos)
    haste_len = 0.055
    segs_haste = 16
    r_haste = 0.004
    pts_h0 = [
        QVector3D(
            lx0 + 0.0095,
            ly0 + r_haste * math.cos(2 * math.pi * i / segs_haste),
            lz0 + r_haste + r_haste * math.sin(2 * math.pi * i / segs_haste),
        )
        for i in range(segs_haste)
    ]
    pts_h1 = [
        QVector3D(
            lx0 + 0.0095 + haste_len * 0.7,
            ly0 + r_haste * math.cos(2 * math.pi * i / segs_haste),
            lz0 + r_haste + haste_len * 0.7 + r_haste * math.sin(2 * math.pi * i / segs_haste),
        )
        for i in range(segs_haste)
    ]
    f_start = mesh.add_face(list(reversed(pts_h0)))
    f_start.attrs["color"] = cor_cromo
    f_start.attrs["mat"] = "Metal Cromado"
    for i in range(segs_haste):
        i_next = (i + 1) % segs_haste
        f = mesh.add_face([pts_h0[i], pts_h0[i_next], pts_h1[i_next], pts_h1[i]])
        f.attrs["color"] = cor_cromo
        f.attrs["mat"] = "Metal Cromado"
    f_end = mesh.add_face(pts_h1)
    f_end.attrs["color"] = cor_cromo
    f_end.attrs["mat"] = "Metal Cromado"

    # 4. Coluna vertical da bica (raio 12mm, sobe até 240mm)
    z_col_topo = bz + 0.240
    add_cylinder(bx, by, bz + 0.0822, z_col_topo, 0.012, cor_cromo, mat_name="Metal Cromado", segs=segmentos)

    # 5. Bica Curva em Arco Suave (pescoço de ganso suave virando -Y sobre a cuba)
    r_tubo = 0.011
    r_curva = 0.085
    z_arco_base = z_col_topo + 0.0002
    num_passos = 16  # Passos longitudinais mais refinados ao longo da curva

    # Gera seções circulares ao longo do arco de 0 a 140 graus
    secoes = []
    for s in range(num_passos + 1):
        ang_deg = 180.0 * s / num_passos
        ang_rad = math.radians(ang_deg)
        # O arco gira no plano YZ
        cy = by - r_curva * (1.0 - math.cos(ang_rad * 0.8))
        cz = z_arco_base + r_curva * math.sin(ang_rad * 0.8)

        # Vetores tangentes para orientar a seção circular do tubo
        tang_y = -math.sin(ang_rad * 0.8)
        tang_z = math.cos(ang_rad * 0.8)
        # Normal no plano YZ
        norm_y = -tang_z
        norm_z = tang_y

        circ = []
        for i in range(segmentos):
            phi = 2.0 * math.pi * i / segmentos
            # Deslocamento em X (perpendicular ao plano YZ) e no vetor normal
            dx = r_tubo * math.cos(phi)
            dy = r_tubo * math.sin(phi) * norm_y
            dz = r_tubo * math.sin(phi) * norm_z
            circ.append(QVector3D(bx + dx, cy + dy, cz + dz))
        secoes.append(circ)

    # Tampas das extremidades do arco para fechar o volume (normais para fora do tubo)
    f_arc0 = mesh.add_face(secoes[0])
    f_arc0.attrs["color"] = cor_cromo
    f_arc0.attrs["mat"] = "Metal Cromado"
    f_arc1 = mesh.add_face(list(reversed(secoes[-1])))
    f_arc1.attrs["color"] = cor_cromo
    f_arc1.attrs["mat"] = "Metal Cromado"

    # Conecta quads entre as seções do arco (normais para fora do tubo)
    for s in range(num_passos):
        c0 = secoes[s]
        c1 = secoes[s + 1]
        for i in range(segmentos):
            i_next = (i + 1) % segmentos
            f = mesh.add_face([c0[i_next], c0[i], c1[i], c1[i_next]])
            f.attrs["color"] = cor_cromo
            f.attrs["mat"] = "Metal Cromado"

    # 6. Arejador / Ponteira vertical cromada no final da bica
    ponta_circ = secoes[-1]
    ponta_centro = QVector3D(
        sum(p.x() for p in ponta_circ) / len(ponta_circ),
        sum(p.y() for p in ponta_circ) / len(ponta_circ),
        sum(p.z() for p in ponta_circ) / len(ponta_circ),
    )
    # Arejador cilíndrico reto vertical descendo 25mm
    ay = ponta_centro.y()
    az = ponta_centro.z() - 0.0002
    add_cylinder(bx, ay, az - 0.025, az, 0.013, cor_cromo, mat_name="Metal Cromado", segs=segmentos)
    # Difusor de saída cinza grafite
    add_cylinder(bx, ay, az - 0.0282, az - 0.0252, 0.011, cor_preto, mat_name="Metal Preto", segs=segmentos)

    return mesh



from .handles_mesh import (  # noqa: E402
    _add_handle_geometry,
    _build_perfil_geometry,
    _get_puxador_rgb,
)
from .machining_mesh import _render_machining_holes_in_mesh  # noqa: E402


def create_board_group(
    name: str,
    origin: tuple[float, float, float],
    size: tuple[float, float, float],
    material: str,
    fita_c1: bool = False,
    fita_c2: bool = False,
    fita_l1: bool = False,
    fita_l2: bool = False,
    ignorar_veio: bool = False,
    color: tuple[float, float, float] | None = None,
    puxador_tipo: str | None = None,
    puxador_cor: str | tuple[float, float, float] | None = None,
    door_side: str | None = None,
    is_upper: bool = False,
    puxador_pos: str = "padrao",
    desconto_perfil_mm: float = 35.0,
    perfil_modelo: str = "gola",
    material_fita: str | None = None,
    cor_fita: tuple[float, float, float] | None = None,
    espessura_fita: float = 0.45,
    operacoes: list[dict[str, Any]] | None = None,
    spec: Any | None = None,
) -> Group:
    """Cria uma peça (Group) com geometria 3D, puxadores opcionais e metadados de marcenaria.

    API de baixo nível (medidas em **metros**). Para o caminho canônico, prefira
    :func:`build_chapa` (metros) ou :func:`build_chapa_mm` (milímetros), que recebem
    um :class:`ChapaSpec` resolvido.

    Para puxadores do tipo Perfil de Alumínio:
    - Desconta a chapa de MDF (padrão marcenaria: 35mm), integrando o perfil ao vão da porta/gaveta;
    - Gera a geometria realista do modelo selecionado (Gola RM-030, Facetato RM-027, Canal C RM-032, SP-7000);
    - Remove a fita de borda no lado onde o perfil é encaixado;
    - Registra a medida real cortada nos metadados para envio ao TrazoMob.
    """
    from ..domain.materials_catalog import get_material_color

    # Resolução automática da cor visual e fita de borda via catálogo oficial de materiais
    if color is None:
        color = get_material_color(material)
    if cor_fita is None and material_fita:
        cor_fita = get_material_color(material_fita)

    # Converte qualquer objeto MachiningOp para dict padrão
    if operacoes:
        normalized_ops = []
        for op in operacoes:
            if hasattr(op, "to_dict"):
                normalized_ops.append(op.to_dict())
            elif isinstance(op, dict):
                normalized_ops.append(op)
        operacoes = normalized_ops
    if spec is not None:
        name = getattr(spec, "nome", name)
        material = getattr(spec, "material", material)
        fita_c1 = getattr(spec, "fita_c1", fita_c1)
        fita_c2 = getattr(spec, "fita_c2", fita_c2)
        fita_l1 = getattr(spec, "fita_l1", fita_l1)
        fita_l2 = getattr(spec, "fita_l2", fita_l2)
        if getattr(spec, "material_fita", None):
            material_fita = spec.material_fita
        if getattr(spec, "espessura_fita", None) is not None:
            espessura_fita = spec.espessura_fita
        if getattr(spec, "ignorar_veio", False):
            ignorar_veio = True
        if getattr(spec, "operacoes", None):
            operacoes = spec.operacoes

    tipo_pux = (puxador_tipo or "").lower()
    ox, oy, oz = origin
    sx, sy, sz = size

    # Validação e limitação rígida aos limites da chapa de MDF (com refilo de limpeza)
    from ..domain.materials_catalog import clamp_peca_to_sheet_limits
    sx, sy, sz = clamp_peca_to_sheet_limits(sx, sy, sz, material=material)
    size = (sx, sy, sz)

    mat_lower = (material or "").lower()
    name_lower = (name or "").lower()
    is_pedra = any(
        kw in mat_lower for kw in ("granito", "marmore", "mármore", "quartzo", "silestone", "corumba", "corumbá", "gabriel", "calacatta", "pedra")
    ) or any(
        kw in name_lower for kw in ("bancada", "moldura seca", "saia", "frontao", "frontão")
    )

    # Se for Puxador Perfil Integrado: desconta a chapa de MDF e integra o perfil com geometria realista
    if tipo_pux == "perfil":
        pos = (puxador_pos or "padrao").lower()
        eff_pos = pos
        if eff_pos in ("padrao", "auto"):
            if is_upper or door_side == "flap":
                eff_pos = "base"
            elif door_side == "drawer":
                eff_pos = "topo"
            else:
                eff_pos = "extensao" if sz >= 1.2 else "topo"

        rgb = _get_puxador_rgb(puxador_cor)
        desc_m = min(desconto_perfil_mm / 1000.0, max(0.015, (sx if eff_pos in ("extensao", "lateral") else sz) - 0.05))

        tex_mat = _get_material_texture(material)

        if eff_pos == "base":
            # Perfil integrado na base (comum em armários aéreos)
            alt_mdf = max(0.02, sz - desc_m)
            mdf_origin = (ox, oy, oz + desc_m)
            mdf_size = (sx, sy, alt_mdf)
            fita_c1 = False  # Sem fita na base onde entra o perfil

            mesh = _make_board_mesh(
                mdf_origin, mdf_size, color=color,
                fita_c1=fita_c1, fita_c2=fita_c2, fita_l1=fita_l1, fita_l2=fita_l2,
                cor_fita=cor_fita,
                texture=tex_mat,
            )
            _build_perfil_geometry(
                mesh, origin, size,
                perfil_modelo=perfil_modelo,
                eff_pos="base",
                door_side=door_side or "single",
                rgb=rgb,
                desc_m=desc_m,
            )

        elif eff_pos in ("extensao", "lateral") and door_side not in ("drawer", "flap"):
            # Perfil vertical na extensão lateral da porta
            if door_side == "both":
                larg_mdf = max(0.02, sx - 2.0 * desc_m)
                mdf_origin = (ox + desc_m, oy, oz)
                mdf_size = (larg_mdf, sy, sz)
                fita_l1 = False  # Sem fita na borda esquerda
                fita_l2 = False  # Sem fita na borda direita
                mesh = _make_board_mesh(
                    mdf_origin, mdf_size, color=color,
                    fita_c1=fita_c1, fita_c2=fita_c2, fita_l1=fita_l1, fita_l2=fita_l2,
                    cor_fita=cor_fita,
                    texture=tex_mat,
                )
            elif door_side in ("left", "single"):
                larg_mdf = max(0.02, sx - desc_m)
                mdf_origin = (ox, oy, oz)
                mdf_size = (larg_mdf, sy, sz)
                fita_l2 = False  # Sem fita na borda direita
                mesh = _make_board_mesh(
                    mdf_origin, mdf_size, color=color,
                    fita_c1=fita_c1, fita_c2=fita_c2, fita_l1=fita_l1, fita_l2=fita_l2,
                    cor_fita=cor_fita,
                    texture=tex_mat,
                )
            else:  # "right"
                larg_mdf = max(0.02, sx - desc_m)
                mdf_origin = (ox + desc_m, oy, oz)
                mdf_size = (larg_mdf, sy, sz)
                fita_l1 = False  # Sem fita na borda esquerda
                mesh = _make_board_mesh(
                    mdf_origin, mdf_size, color=color,
                    fita_c1=fita_c1, fita_c2=fita_c2, fita_l1=fita_l1, fita_l2=fita_l2,
                    cor_fita=cor_fita,
                    texture=tex_mat,
                )

            _build_perfil_geometry(
                mesh, origin, size,
                perfil_modelo=perfil_modelo,
                eff_pos="lateral",
                door_side=door_side or "single",
                rgb=rgb,
                desc_m=desc_m,
            )

        else:
            # Perfil integrado no topo (padrão em balcões e frentes de gaveta)
            alt_mdf = max(0.02, sz - desc_m)
            mdf_origin = (ox, oy, oz)
            mdf_size = (sx, sy, alt_mdf)
            fita_c2 = False  # Sem fita no topo onde entra o perfil

            mesh = _make_board_mesh(
                mdf_origin, mdf_size, color=color,
                fita_c1=fita_c1, fita_c2=fita_c2, fita_l1=fita_l1, fita_l2=fita_l2,
                cor_fita=cor_fita,
                texture=tex_mat,
            )
            _build_perfil_geometry(
                mesh, origin, size,
                perfil_modelo=perfil_modelo,
                eff_pos="topo",
                door_side=door_side or "single",
                rgb=rgb,
                desc_m=desc_m,
            )

        cut_size = mdf_size
    else:
        # Puxadores sobrepostos / convencionais (Alça, Cava, Ponto, Sem Puxador)
        tex_mat = _get_material_texture(material)
        mesh = _make_board_mesh(
            origin, size, color=color,
            fita_c1=fita_c1, fita_c2=fita_c2, fita_l1=fita_l1, fita_l2=fita_l2,
            cor_fita=cor_fita,
            is_pedra=is_pedra,
            texture=tex_mat,
            piece_name=name,
            operacoes=operacoes,
        )
        if tipo_pux and tipo_pux not in ("sem_puxador", "toque", "nenhum"):
            _add_handle_geometry(
                mesh, origin, size,
                puxador_tipo=puxador_tipo,
                puxador_cor=puxador_cor,
                door_side=door_side or "single",
                is_upper=is_upper,
                puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm,
                perfil_modelo=perfil_modelo,
            )
        cut_size = size

    # Renderiza visualmente as furações técnicas na geometria da peça
    if operacoes:
        _render_machining_holes_in_mesh(mesh, origin, cut_size, operacoes, piece_name=name)

    g = Group(mesh, name=name)

    dims_mm = sorted([abs(cut_size[0]) * 1000.0, abs(cut_size[1]) * 1000.0, abs(cut_size[2]) * 1000.0])
    esp_mm = round(dims_mm[0], 1)
    larg_mm = round(dims_mm[1], 1)
    comp_mm = round(dims_mm[2], 1)

    from ..production.parts import detect_grain_orientation

    meta = {
        "nome": name,
        "material": material,
        "comprimento": comp_mm,
        "largura": larg_mm,
        "espessura": esp_mm,
        "fita_c1": fita_c1,
        "fita_c2": fita_c2,
        "fita_l1": fita_l1,
        "fita_l2": fita_l2,
        "espessura_fita": float(espessura_fita or 0.45),
        "ignorar_veio": (
            ignorar_veio if ignorar_veio else
            detect_grain_orientation(material, name, (esp_mm, larg_mm, comp_mm))
        ),
        "operacoes": [dict(o) for o in operacoes] if operacoes else [],
        "_rendered_ops_count": len(operacoes) if operacoes else 0,
    }
    if door_side:
        meta["door_side"] = door_side
    if material_fita:
        meta["material_fita"] = material_fita
    if puxador_tipo:
        meta["puxador"] = puxador_tipo
        meta["puxador_pos"] = puxador_pos
        if tipo_pux == "perfil":
            meta["desconto_perfil"] = desconto_perfil_mm
            meta["perfil_modelo"] = perfil_modelo

    if hasattr(g, "ext"):
        if getattr(g, "ext", None) is None:
            g.ext = {}
        g.ext["trazomob"] = meta

    return g


def create_polygon_board_group(
    name: str,
    polygon_xy: list[tuple[float, float]],
    z0: float,
    espessura: float,
    material: str,
    color: tuple[float, float, float] | None = None,
    material_fita: str | None = None,
    cor_fita: tuple[float, float, float] | None = None,
    espessura_fita: float = 0.45,
    spec: Any | None = None,
) -> Group:
    """Cria uma chapa poligonal (prisma extrudado em Z, ex: base pentagonal de canto chanfrado)."""
    from ..domain.materials_catalog import get_material_color

    mesh = Mesh()
    z1 = z0 + espessura
    eff_color = color if color is not None else get_material_color(material)
    cor_borda = cor_fita or (get_material_color(material_fita) if material_fita else tuple(max(0.0, c * 0.94) for c in eff_color))
    tex_mat = _get_material_texture(material)


    # Face superior (+Z): sentido anti-horário
    f_top = mesh.add_face([QVector3D(x, y, z1) for x, y in polygon_xy])
    f_top.attrs["color"] = eff_color
    if tex_mat:
        f_top.attrs["texture"] = dict(tex_mat)

    # Face inferior (-Z): sentido horário (normal apontando para baixo)
    f_bot = mesh.add_face([QVector3D(x, y, z0) for x, y in reversed(polygon_xy)])
    f_bot.attrs["color"] = eff_color
    if tex_mat:
        f_bot.attrs["texture"] = dict(tex_mat)

    # Paredes laterais (cada aresta do polígono)
    n = len(polygon_xy)
    for i in range(n):
        ax, ay = polygon_xy[i]
        bx, by = polygon_xy[(i + 1) % n]
        f_side = mesh.add_face([
            QVector3D(ax, ay, z0),
            QVector3D(bx, by, z0),
            QVector3D(bx, by, z1),
            QVector3D(ax, ay, z1),
        ])
        f_side.attrs["color"] = cor_borda
        if tex_mat:
            f_side.attrs["texture"] = dict(tex_mat)

    g = Group(mesh, name=name)

    xs = [p[0] for p in polygon_xy]
    ys = [p[1] for p in polygon_xy]
    bb_w = (max(xs) - min(xs)) * 1000.0
    bb_d = (max(ys) - min(ys)) * 1000.0
    esp_mm = round(espessura * 1000.0, 1)

    meta = {
        "nome": name,
        "material": material,
        "comprimento": round(max(bb_w, bb_d), 1),
        "largura": round(min(bb_w, bb_d), 1),
        "espessura": esp_mm,
        "fita_c1": True,
        "fita_c2": False,
        "fita_l1": False,
        "fita_l2": False,
        "espessura_fita": float(espessura_fita or 0.45),
        "ignorar_veio": True,
        "operacoes": [],
        "_rendered_ops_count": 0,
    }
    if material_fita:
        meta["material_fita"] = material_fita

    if hasattr(g, "ext"):
        if getattr(g, "ext", None) is None:
            g.ext = {}
        g.ext["trazomob"] = meta

    return g


def create_prism_board_group(
    name: str,
    poly_xz: list[tuple[float, float]],
    y_start: float,
    y_thickness: float,
    material: str = "MDF Branco 15mm",
    color: tuple[float, float, float] | None = None,
    material_fita: str | None = None,
    espessura_fita: float = 0.45,
) -> Group:
    """Cria uma chapa prismática com seção arbitrária no plano XZ extrudada ao longo de Y."""
    from PySide6.QtGui import QVector3D

    from core.mesh import Mesh

    from ..domain.materials_catalog import get_material_color

    mesh = Mesh()
    y0 = y_start
    y1 = y_start + y_thickness
    eff_color = color if color is not None else get_material_color(material)
    tex_mat = _get_material_texture(material)

    # Face frontal (y0)
    f_front = mesh.add_face([QVector3D(x, y0, z) for x, z in poly_xz])
    f_front.attrs["color"] = eff_color
    if tex_mat:
        f_front.attrs["texture"] = dict(tex_mat)

    # Face traseira (y1)
    f_back = mesh.add_face([QVector3D(x, y1, z) for x, z in reversed(poly_xz)])
    f_back.attrs["color"] = eff_color
    if tex_mat:
        f_back.attrs["texture"] = dict(tex_mat)

    # Bordas laterais
    n = len(poly_xz)
    for i in range(n):
        ax, az = poly_xz[i]
        bx, bz = poly_xz[(i + 1) % n]
        f_side = mesh.add_face([
            QVector3D(ax, y0, az),
            QVector3D(bx, y0, bz),
            QVector3D(bx, y1, bz),
            QVector3D(ax, y1, az),
        ])
        f_side.attrs["color"] = eff_color
        if tex_mat:
            f_side.attrs["texture"] = dict(tex_mat)

    g = Group()
    g.name = name
    g.mesh = mesh

    xs = [p[0] for p in poly_xz]
    zs = [p[1] for p in poly_xz]
    bb_w = (max(xs) - min(xs)) * 1000.0
    bb_h = (max(zs) - min(zs)) * 1000.0
    bb_d = abs(y_thickness) * 1000.0

    meta = {
        "nome": name,
        "material": material,
        "comprimento": round(max(bb_w, bb_h), 1),
        "largura": round(bb_d, 1),
        "espessura": 15.0,
        "fita_c1": True,
        "fita_c2": False,
        "fita_l1": False,
        "fita_l2": False,
        "espessura_fita": float(espessura_fita or 0.45),
        "ignorar_veio": True,
        "operacoes": [],
        "_rendered_ops_count": 0,
    }
    if material_fita:
        meta["material_fita"] = material_fita

    if hasattr(g, "ext"):
        if getattr(g, "ext", None) is None:
            g.ext = {}
        g.ext["trazomob"] = meta

    return g


def create_cylinder_group(
    name: str,
    center_xy: tuple[float, float],
    radius: float,
    z0: float,
    height: float,
    material: str = "Metal Cromado",
    color: tuple[float, float, float] | None = None,
    segments: int = 16,
) -> Group:
    """Cria um sólido cilíndrico prismático vertical (ex: pé tubular metálico ou tubo de cabideiro)."""
    import math
    cx, cy = center_xy
    poly_circle: list[tuple[float, float]] = []
    for s in range(segments):
        ang = s * (2.0 * math.pi / segments)
        poly_circle.append((cx + radius * math.cos(ang), cy + radius * math.sin(ang)))

    eff_color = color if color is not None else (0.85, 0.85, 0.88)
    return create_polygon_board_group(
        name=name,
        polygon_xy=poly_circle,
        z0=z0,
        espessura=height,
        material=material,
        color=eff_color,
    )



