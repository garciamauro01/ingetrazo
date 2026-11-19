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


def _render_machining_holes_in_mesh(
    mesh: Mesh,
    origin: tuple[float, float, float],
    size: tuple[float, float, float],
    operacoes: list[dict[str, Any]],
    piece_name: str = "",
) -> None:
    """Renderiza furações técnicas diretamente no sólido 3D (canecos 35mm, minifix e cavilhas).

    Perfura a face correspondente da chapa usando ``mesh.add_hole`` e cria as paredes
    cilíndricas internas e o fundo do furo com normais voltadas para fora do volume,
    preservando 100% a topologia estanque (manifold / watertight) da peça.
    """
    if not operacoes:
        return

    ox, oy, oz = origin
    sx, sy, sz = size
    cor_furo = (0.20, 0.20, 0.22)       # Fundo da cavidade de usinagem
    cor_borda = (0.45, 0.45, 0.48)      # Parede cilíndrica interna de usinagem

    # Identifica orientação da chapa para projetar os furos na face correspondente
    dims = [abs(sx), abs(sy), abs(sz)]
    min_dim = min(dims)

    # Segmentação circular leve (8 lados) para performance máxima em tempo real
    n_seg = 8
    seen_centers: list[tuple[float, float, float, float]] = []

    def _find_target_face(axis_idx: int, target_coord: float, normal_sign: float):
        for f in mesh.faces:
            if not f.loop:
                continue
            coords = [
                (v.position.x() if axis_idx == 0 else (v.position.y() if axis_idx == 1 else v.position.z()))
                for v in f.loop
            ]
            if max(abs(c - target_coord) for c in coords) < 1e-4:
                n = f.normal()
                n_comp = n.x() if axis_idx == 0 else (n.y() if axis_idx == 1 else n.z())
                if n_comp * normal_sign > 0.5:
                    return f
        return None

    for op in operacoes:
        tipo = op.get("tipo", "furo")
        if tipo != "furo":
            continue

        diam_m = float(op.get("diametro", 35.0)) / 1000.0
        raio_m = diam_m / 2.0
        # Desenha no 3D furos de usinagem funcional e marcações (caneco 35mm, tambor 15mm, cavilha 8mm, pino minifix 5mm e marcação parafuso 2.5mm)
        if raio_m < 0.0010:
            continue

        x_op_m = float(op.get("x", 0.0)) / 1000.0
        y_op_m = float(op.get("y", 0.0)) / 1000.0
        prof_m = min(float(op.get("profundidade", 12.0)) / 1000.0, 0.050)

        if abs(sy - min_dim) < 1e-5:
            # Chapa vertical frontal (Porta / Frente de gaveta / Travessa em pé - espessura em Y)
            op_face = str(op.get("face", "")).lower()

            if op_face in ("esquerda", "left"):
                # Furo no topo esquerdo da travessa em pé: face com normal -X (ox)
                cy = oy + y_op_m if sy >= 0 else oy + sy + y_op_m
                cz = oz + x_op_m if sz >= 0 else oz + sz + x_op_m
                cx_face = ox
                cx_fundo = cx_face + prof_m

                y_lo, y_hi = min(oy, oy + sy), max(oy, oy + sy)
                z_lo, z_hi = min(oz, oz + sz), max(oz, oz + sz)
                if not (y_lo + 1e-4 <= cy <= y_hi - 1e-4 and z_lo + raio_m + 1e-4 <= cz <= z_hi - raio_m - 1e-4):
                    continue

                if any(abs(cx_face - sx0) < 1e-3 and math.hypot(cy - sy0, cz - sz0) < (raio_m + sr0 + 1e-3) for sx0, sy0, sz0, sr0 in seen_centers):
                    continue

                target_face = _find_target_face(0, cx_face, -1.0)
                if target_face is None:
                    continue
                seen_centers.append((cx_face, cy, cz, raio_m))

                pts_face = []
                pts_fundo = []
                for i in range(n_seg):
                    ang = 2.0 * math.pi * i / n_seg
                    dy = raio_m * math.cos(ang)
                    dz = raio_m * math.sin(ang)
                    pts_face.append(QVector3D(cx_face, cy + dy, cz + dz))
                    pts_fundo.append(QVector3D(cx_fundo, cy + dy, cz + dz))

                mesh.add_hole(target_face, pts_face)
                f_bot = mesh.add_face(list(reversed(pts_fundo)))
                f_bot.attrs["color"] = cor_furo
                for i in range(n_seg):
                    i_next = (i + 1) % n_seg
                    w_face = mesh.add_face([
                        pts_face[i_next], pts_face[i],
                        pts_fundo[i], pts_fundo[i_next]
                    ])
                    w_face.attrs["color"] = cor_borda

            elif op_face in ("direita", "right"):
                # Furo no topo direito da travessa em pé: face com normal +X (ox + sx)
                cy = oy + y_op_m if sy >= 0 else oy + sy + y_op_m
                cz = oz + x_op_m if sz >= 0 else oz + sz + x_op_m
                cx_face = ox + sx
                cx_fundo = cx_face - prof_m

                y_lo, y_hi = min(oy, oy + sy), max(oy, oy + sy)
                z_lo, z_hi = min(oz, oz + sz), max(oz, oz + sz)
                if not (y_lo + 1e-4 <= cy <= y_hi - 1e-4 and z_lo + raio_m + 1e-4 <= cz <= z_hi - raio_m - 1e-4):
                    continue

                if any(abs(cx_face - sx0) < 1e-3 and math.hypot(cy - sy0, cz - sz0) < (raio_m + sr0 + 1e-3) for sx0, sy0, sz0, sr0 in seen_centers):
                    continue

                target_face = _find_target_face(0, cx_face, 1.0)
                if target_face is None:
                    continue
                seen_centers.append((cx_face, cy, cz, raio_m))

                pts_face = []
                pts_fundo = []
                for i in range(n_seg):
                    ang = 2.0 * math.pi * i / n_seg
                    dy = raio_m * math.cos(ang)
                    dz = raio_m * math.sin(ang)
                    pts_face.append(QVector3D(cx_face, cy + dy, cz + dz))
                    pts_fundo.append(QVector3D(cx_fundo, cy + dy, cz + dz))

                mesh.add_hole(target_face, list(reversed(pts_face)))
                f_bot = mesh.add_face(pts_fundo)
                f_bot.attrs["color"] = cor_furo
                for i in range(n_seg):
                    i_next = (i + 1) % n_seg
                    w_face = mesh.add_face([
                        pts_face[i], pts_face[i_next],
                        pts_fundo[i_next], pts_fundo[i]
                    ])
                    w_face.attrs["color"] = cor_borda

            elif op_face in ("frontal", "front"):
                # Furos na face frontal (-Y da chapa): face com normal -Y em oy
                cx = ox + x_op_m if sx >= 0 else ox + sx + x_op_m
                cz = oz + y_op_m if sz >= 0 else oz + sz + y_op_m
                cy_face = oy
                cy_fundo = cy_face + prof_m

                x_lo, x_hi = min(ox, ox + sx), max(ox, ox + sx)
                z_lo, z_hi = min(oz, oz + sz), max(oz, oz + sz)
                if not (x_lo + raio_m + 1e-4 <= cx <= x_hi - raio_m - 1e-4 and z_lo + raio_m + 1e-4 <= cz <= z_hi - raio_m - 1e-4):
                    continue

                if any(abs(cy_face - sy0) < 1e-3 and math.hypot(cx - sx0, cz - sz0) < (raio_m + sr0 + 1e-3) for sx0, sy0, sz0, sr0 in seen_centers):
                    continue

                target_face = _find_target_face(1, cy_face, -1.0)
                if target_face is None:
                    continue
                seen_centers.append((cx, cy_face, cz, raio_m))

                pts_face = []
                pts_fundo = []
                for i in range(n_seg):
                    ang = 2.0 * math.pi * i / n_seg
                    dx = raio_m * math.cos(ang)
                    dz = raio_m * math.sin(ang)
                    pts_face.append(QVector3D(cx + dx, cy_face, cz + dz))
                    pts_fundo.append(QVector3D(cx + dx, cy_fundo, cz + dz))

                # Face normal -Y. add_hole requer loop com normal contrária (+Y): list(reversed(pts_face))
                mesh.add_hole(target_face, list(reversed(pts_face)))
                f_bot = mesh.add_face(pts_fundo)
                f_bot.attrs["color"] = cor_furo
                for i in range(n_seg):
                    i_next = (i + 1) % n_seg
                    w_face = mesh.add_face([
                        pts_face[i], pts_face[i_next],
                        pts_fundo[i_next], pts_fundo[i]
                    ])
                    w_face.attrs["color"] = cor_borda

            else:
                # Furos na face larga traseira (+Y da chapa): canecos de dobradiça ou tambores de minifix em pé
                cx = ox + x_op_m if sx >= 0 else ox + sx + x_op_m
                cz = oz + y_op_m if sz >= 0 else oz + sz + y_op_m
                cy_face = oy + sy
                cy_fundo = cy_face - prof_m

                x_lo, x_hi = min(ox, ox + sx), max(ox, ox + sx)
                z_lo, z_hi = min(oz, oz + sz), max(oz, oz + sz)
                if not (x_lo + raio_m + 1e-4 <= cx <= x_hi - raio_m - 1e-4 and z_lo + raio_m + 1e-4 <= cz <= z_hi - raio_m - 1e-4):
                    continue

                if any(abs(cy_face - sy0) < 1e-3 and math.hypot(cx - sx0, cz - sz0) < (raio_m + sr0 + 1e-3) for sx0, sy0, sz0, sr0 in seen_centers):
                    continue

                target_face = _find_target_face(1, cy_face, 1.0)
                if target_face is None:
                    continue
                seen_centers.append((cx, cy_face, cz, raio_m))

                pts_face = []
                pts_fundo = []
                for i in range(n_seg):
                    ang = 2.0 * math.pi * i / n_seg
                    dx = raio_m * math.cos(ang)
                    dz = raio_m * math.sin(ang)
                    pts_face.append(QVector3D(cx + dx, cy_face, cz + dz))
                    pts_fundo.append(QVector3D(cx + dx, cy_fundo, cz + dz))

                # Perfura a face traseira (+Y) com loop horário visto de +Y (pts_face já tem normal -Y)
                mesh.add_hole(target_face, pts_face)

                # Fundo do furo (normal apontando para fora do sólido: +Y)
                f_bot = mesh.add_face(list(reversed(pts_fundo)))
                f_bot.attrs["color"] = cor_furo

                # Paredes cilíndricas do furo (normal apontando para o centro da cavidade, fora do MDF)
                for i in range(n_seg):
                    i_next = (i + 1) % n_seg
                    w_face = mesh.add_face([
                        pts_face[i_next], pts_face[i],
                        pts_fundo[i], pts_fundo[i_next]
                    ])
                    w_face.attrs["color"] = cor_borda

        elif abs(sx - min_dim) < 1e-5:
            # Chapa vertical lateral (Laterais do armário / divisórias - espessura em X)
            op_face = str(op.get("face", "")).lower()

            if op_face in ("topo", "superior"):
                # Topo superior da chapa vertical (face com normal +Z em oz + sz)
                cx = ox + y_op_m if sx >= 0 else ox + sx + y_op_m
                cy = oy + x_op_m if sy >= 0 else oy + sy + x_op_m
                cz_face = oz + sz
                cz_fundo = cz_face - prof_m

                x_lo, x_hi = min(ox, ox + sx), max(ox, ox + sx)
                y_lo, y_hi = min(oy, oy + sy), max(oy, oy + sy)
                if not (x_lo + 1e-4 <= cx <= x_hi - 1e-4 and y_lo + raio_m + 1e-4 <= cy <= y_hi - raio_m - 1e-4):
                    continue

                if any(abs(cz_face - sz0) < 1e-3 and math.hypot(cx - sx0, cy - sy0) < (raio_m + sr0 + 1e-3) for sx0, sy0, sz0, sr0 in seen_centers):
                    continue

                target_face = _find_target_face(2, cz_face, 1.0)
                if target_face is None:
                    continue
                seen_centers.append((cx, cy, cz_face, raio_m))

                pts_face = []
                pts_fundo = []
                for i in range(n_seg):
                    ang = 2.0 * math.pi * i / n_seg
                    dx = raio_m * math.cos(ang)
                    dy = raio_m * math.sin(ang)
                    pts_face.append(QVector3D(cx + dx, cy + dy, cz_face))
                    pts_fundo.append(QVector3D(cx + dx, cy + dy, cz_fundo))

                # Face normal +Z: add_hole requer loop com normal contrária (-Z): list(reversed(pts_face))
                mesh.add_hole(target_face, list(reversed(pts_face)))
                # Fundo do furo aponta para fora do sólido (+Z)
                f_bot = mesh.add_face(pts_fundo)
                f_bot.attrs["color"] = cor_furo
                for i in range(n_seg):
                    i_next = (i + 1) % n_seg
                    w_face = mesh.add_face([
                        pts_face[i], pts_face[i_next],
                        pts_fundo[i_next], pts_fundo[i]
                    ])
                    w_face.attrs["color"] = cor_borda

            elif op_face in ("base", "inferior", "baixo"):
                # Topo inferior (base) da chapa vertical (face com normal -Z em oz)
                cx = ox + y_op_m if sx >= 0 else ox + sx + y_op_m
                cy = oy + x_op_m if sy >= 0 else oy + sy + x_op_m
                cz_face = oz
                cz_fundo = cz_face + prof_m

                x_lo, x_hi = min(ox, ox + sx), max(ox, ox + sx)
                y_lo, y_hi = min(oy, oy + sy), max(oy, oy + sy)
                if not (x_lo + 1e-4 <= cx <= x_hi - 1e-4 and y_lo + raio_m + 1e-4 <= cy <= y_hi - raio_m - 1e-4):
                    continue

                if any(abs(cz_face - sz0) < 1e-3 and math.hypot(cx - sx0, cy - sy0) < (raio_m + sr0 + 1e-3) for sx0, sy0, sz0, sr0 in seen_centers):
                    continue

                target_face = _find_target_face(2, cz_face, -1.0)
                if target_face is None:
                    continue
                seen_centers.append((cx, cy, cz_face, raio_m))

                pts_face = []
                pts_fundo = []
                for i in range(n_seg):
                    ang = 2.0 * math.pi * i / n_seg
                    dx = raio_m * math.cos(ang)
                    dy = raio_m * math.sin(ang)
                    pts_face.append(QVector3D(cx + dx, cy + dy, cz_face))
                    pts_fundo.append(QVector3D(cx + dx, cy + dy, cz_fundo))

                # Face normal -Z: add_hole requer loop com normal contrária (+Z): pts_face
                mesh.add_hole(target_face, pts_face)
                # Fundo do furo aponta para fora do sólido (-Z)
                f_bot = mesh.add_face(list(reversed(pts_fundo)))
                f_bot.attrs["color"] = cor_furo
                for i in range(n_seg):
                    i_next = (i + 1) % n_seg
                    w_face = mesh.add_face([
                        pts_face[i_next], pts_face[i],
                        pts_fundo[i], pts_fundo[i_next]
                    ])
                    w_face.attrs["color"] = cor_borda

            elif op_face in ("topo_frontal", "borda_frontal"):
                # Topo frontal da chapa vertical com espessura em X (face com normal -Y em oy)
                cx = ox + y_op_m if sx >= 0 else ox + sx + y_op_m
                cz = oz + x_op_m if sz >= 0 else oz + sz + x_op_m
                cy_face = oy
                cy_fundo = cy_face + prof_m

                x_lo, x_hi = min(ox, ox + sx), max(ox, ox + sx)
                z_lo, z_hi = min(oz, oz + sz), max(oz, oz + sz)
                if not (x_lo + 1e-4 <= cx <= x_hi - 1e-4 and z_lo + raio_m + 1e-4 <= cz <= z_hi - raio_m - 1e-4):
                    continue

                if any(abs(cy_face - sy0) < 1e-3 and math.hypot(cx - sx0, cz - sz0) < (raio_m + sr0 + 1e-3) for sx0, sy0, sz0, sr0 in seen_centers):
                    continue

                target_face = _find_target_face(1, cy_face, -1.0)
                if target_face is None:
                    continue
                seen_centers.append((cx, cy_face, cz, raio_m))

                pts_face = []
                pts_fundo = []
                for i in range(n_seg):
                    ang = 2.0 * math.pi * i / n_seg
                    dx = raio_m * math.cos(ang)
                    dz = raio_m * math.sin(ang)
                    pts_face.append(QVector3D(cx + dx, cy_face, cz + dz))
                    pts_fundo.append(QVector3D(cx + dx, cy_fundo, cz + dz))

                # Face normal -Y: add_hole requer loop com normal contrária (+Y): list(reversed(pts_face))
                mesh.add_hole(target_face, list(reversed(pts_face)))
                f_bot = mesh.add_face(pts_fundo)
                f_bot.attrs["color"] = cor_furo
                for i in range(n_seg):
                    i_next = (i + 1) % n_seg
                    w_face = mesh.add_face([
                        pts_face[i], pts_face[i_next],
                        pts_fundo[i_next], pts_fundo[i]
                    ])
                    w_face.attrs["color"] = cor_borda

            elif op_face in ("topo_traseiro", "borda_traseira"):
                # Topo traseiro da chapa vertical com espessura em X (face com normal +Y em oy + sy)
                cx = ox + y_op_m if sx >= 0 else ox + sx + y_op_m
                cz = oz + x_op_m if sz >= 0 else oz + sz + x_op_m
                cy_face = oy + sy
                cy_fundo = cy_face - prof_m

                x_lo, x_hi = min(ox, ox + sx), max(ox, ox + sx)
                z_lo, z_hi = min(oz, oz + sz), max(oz, oz + sz)
                if not (x_lo + 1e-4 <= cx <= x_hi - 1e-4 and z_lo + raio_m + 1e-4 <= cz <= z_hi - raio_m - 1e-4):
                    continue

                if any(abs(cy_face - sy0) < 1e-3 and math.hypot(cx - sx0, cz - sz0) < (raio_m + sr0 + 1e-3) for sx0, sy0, sz0, sr0 in seen_centers):
                    continue

                target_face = _find_target_face(1, cy_face, 1.0)
                if target_face is None:
                    continue
                seen_centers.append((cx, cy_face, cz, raio_m))

                pts_face = []
                pts_fundo = []
                for i in range(n_seg):
                    ang = 2.0 * math.pi * i / n_seg
                    dx = raio_m * math.cos(ang)
                    dz = raio_m * math.sin(ang)
                    pts_face.append(QVector3D(cx + dx, cy_face, cz + dz))
                    pts_fundo.append(QVector3D(cx + dx, cy_fundo, cz + dz))

                # Face normal +Y: add_hole requer loop com normal contrária (-Y): pts_face
                mesh.add_hole(target_face, pts_face)
                f_bot = mesh.add_face(list(reversed(pts_fundo)))
                f_bot.attrs["color"] = cor_furo
                for i in range(n_seg):
                    i_next = (i + 1) % n_seg
                    w_face = mesh.add_face([
                        pts_face[i_next], pts_face[i],
                        pts_fundo[i], pts_fundo[i_next]
                    ])
                    w_face.attrs["color"] = cor_borda

            else:
                # Furos na face lateral ampla (+X ou -X) da lateral ou divisória.
                # Faces explícitas ("esquerda"/"direita") permitem furar as duas
                # faces de uma mesma divisória; sem elas, usa-se a face interna
                # deduzida pelo nome da peça:
                # - Para Lateral Direita: a face interna fica em ox (normal -X), furo avança em +X
                # - Para Lateral Esquerda ou divisórias: a face interna fica em ox + sx (normal +X), furo avança em -X
                if op_face in ("esquerda", "left"):
                    is_direita = True   # face -X, em ox
                elif op_face in ("direita", "right"):
                    is_direita = False  # face +X, em ox + sx
                else:
                    is_direita = "direit" in piece_name.lower() or "right" in piece_name.lower()
                cy = oy + x_op_m if sy >= 0 else oy + sy + x_op_m
                cz = oz + y_op_m if sz >= 0 else oz + sz + y_op_m

                if is_direita:
                    cx_face = ox
                    cx_fundo = cx_face + prof_m
                    target_sign = -1.0
                else:
                    cx_face = ox + sx
                    cx_fundo = cx_face - prof_m
                    target_sign = 1.0

                y_lo, y_hi = min(oy, oy + sy), max(oy, oy + sy)
                z_lo, z_hi = min(oz, oz + sz), max(oz, oz + sz)
                if not (y_lo + raio_m + 1e-4 <= cy <= y_hi - raio_m - 1e-4 and z_lo + raio_m + 1e-4 <= cz <= z_hi - raio_m - 1e-4):
                    continue

                if any(abs(cx_face - sx0) < 1e-3 and math.hypot(cy - sy0, cz - sz0) < (raio_m + sr0 + 1e-3) for sx0, sy0, sz0, sr0 in seen_centers):
                    continue

                target_face = _find_target_face(0, cx_face, target_sign)
                if target_face is None:
                    continue
                seen_centers.append((cx_face, cy, cz, raio_m))

                pts_face = []
                pts_fundo = []
                for i in range(n_seg):
                    ang = 2.0 * math.pi * i / n_seg
                    dy = raio_m * math.cos(ang)
                    dz = raio_m * math.sin(ang)
                    pts_face.append(QVector3D(cx_face, cy + dy, cz + dz))
                    pts_fundo.append(QVector3D(cx_fundo, cy + dy, cz + dz))

                if is_direita:
                    # Face tem normal -X. add_hole requer loop com normal contrária (+X): pts_face tem normal +X
                    mesh.add_hole(target_face, pts_face)
                    # Fundo do furo aponta para fora do sólido: -X
                    f_bot = mesh.add_face(list(reversed(pts_fundo)))
                    f_bot.attrs["color"] = cor_furo
                    for i in range(n_seg):
                        i_next = (i + 1) % n_seg
                        w_face = mesh.add_face([
                            pts_face[i_next], pts_face[i],
                            pts_fundo[i], pts_fundo[i_next]
                        ])
                        w_face.attrs["color"] = cor_borda
                else:
                    # Face tem normal +X. add_hole requer loop com normal contrária (-X): reversed(pts_face)
                    mesh.add_hole(target_face, list(reversed(pts_face)))
                    # Fundo do furo aponta para fora do sólido: +X
                    f_bot = mesh.add_face(pts_fundo)
                    f_bot.attrs["color"] = cor_furo
                    for i in range(n_seg):
                        i_next = (i + 1) % n_seg
                        w_face = mesh.add_face([
                            pts_face[i], pts_face[i_next],
                            pts_fundo[i_next], pts_fundo[i]
                        ])
                        w_face.attrs["color"] = cor_borda

        elif abs(sz - min_dim) < 1e-5:
            # Chapa horizontal (Base / Tampo / Prateleira - espessura em Z)
            op_face = str(op.get("face", "")).lower()

            # Caso A: Furo do tambor excêntrico Minifix na face horizontal (face inferior ou superior)
            if op_face in ("base", "topo", "inferior", "superior", "fundo"):
                cx = ox + x_op_m if sx >= 0 else ox + sx + x_op_m
                cy = oy + y_op_m if sy >= 0 else oy + sy + y_op_m
                x_lo, x_hi = min(ox, ox + sx), max(ox, ox + sx)
                y_lo, y_hi = min(oy, oy + sy), max(oy, oy + sy)
                is_vb = "vb" in str(op.get("descricao", "")).lower()
                # Para conectores de embutir de borda tipo VB 35 / VB 36 (furo Ø20mm com centro a 9.5mm da borda),
                # o centro fica ligeiramente alinhado à borda para engate do pino (tolerância de borda aberta)
                min_margem_x = 0.0005 if is_vb else (raio_m + 1e-4)
                if is_vb:
                    if not (x_lo <= cx <= x_hi and y_lo + raio_m + 1e-4 <= cy <= y_hi - raio_m - 1e-4):
                        continue
                    # Ajusta centro visual ligeiramente para dentro se necessário para manter o contorno interno estanque
                    cx = max(x_lo + raio_m + 0.0005, min(x_hi - raio_m - 0.0005, cx))
                else:
                    if not (x_lo + min_margem_x <= cx <= x_hi - min_margem_x and y_lo + raio_m + 1e-4 <= cy <= y_hi - raio_m - 1e-4):
                        continue

                is_face_topo = op_face in ("topo", "superior")
                if is_face_topo:
                    cz_face = oz + sz
                    cz_fundo = cz_face - prof_m
                    target_sign = 1.0
                else:
                    cz_face = oz
                    cz_fundo = cz_face + prof_m
                    target_sign = -1.0

                if any(abs(cz_face - sz0) < 1e-3 and math.hypot(cx - sx0, cy - sy0) < (raio_m + sr0 + 1e-3) for sx0, sy0, sz0, sr0 in seen_centers):
                    continue

                target_face = _find_target_face(2, cz_face, target_sign)
                if target_face is None:
                    continue
                seen_centers.append((cx, cy, cz_face, raio_m))

                pts_face = []
                pts_fundo = []
                for i in range(n_seg):
                    ang = 2.0 * math.pi * i / n_seg
                    dx = raio_m * math.cos(ang)
                    dy = raio_m * math.sin(ang)
                    pts_face.append(QVector3D(cx + dx, cy + dy, cz_face))
                    pts_fundo.append(QVector3D(cx + dx, cy + dy, cz_fundo))

                if is_face_topo:
                    # Face normal +Z: add_hole requer loop com normal -Z: reversed(pts_face)
                    mesh.add_hole(target_face, list(reversed(pts_face)))
                    f_bot = mesh.add_face(pts_fundo)
                    f_bot.attrs["color"] = cor_furo
                    for i in range(n_seg):
                        i_next = (i + 1) % n_seg
                        w_face = mesh.add_face([
                            pts_face[i], pts_face[i_next],
                            pts_fundo[i_next], pts_fundo[i]
                        ])
                        w_face.attrs["color"] = cor_borda
                else:
                    # Face normal -Z: add_hole requer loop com normal +Z: pts_face
                    mesh.add_hole(target_face, pts_face)
                    f_bot = mesh.add_face(list(reversed(pts_fundo)))
                    f_bot.attrs["color"] = cor_furo
                    for i in range(n_seg):
                        i_next = (i + 1) % n_seg
                        w_face = mesh.add_face([
                            pts_face[i_next], pts_face[i],
                            pts_fundo[i], pts_fundo[i_next]
                        ])
                        w_face.attrs["color"] = cor_borda

            # Caso B: Furos nos topos (bordas laterais): face esquerda (-X, normal -1) ou direita (+X, normal +1)
            else:
                cy = oy + x_op_m if sy >= 0 else oy + sy + x_op_m
                cz = oz + y_op_m if sz >= 0 else oz + sz + y_op_m

                y_lo, y_hi = min(oy, oy + sy), max(oy, oy + sy)
                z_lo, z_hi = min(oz, oz + sz), max(oz, oz + sz)
                if not (y_lo + raio_m + 1e-4 <= cy <= y_hi - raio_m - 1e-4 and z_lo + 1e-4 <= cz <= z_hi - 1e-4):
                    continue

                if op_face in ("esquerda", "left") or "esq" in op.get("descricao", "").lower():
                    cx_face = ox
                    cx_fundo = cx_face + prof_m
                    target_sign = -1.0
                    is_esq = True
                elif op_face in ("direita", "right") or "dir" in op.get("descricao", "").lower():
                    cx_face = ox + sx
                    cx_fundo = cx_face - prof_m
                    target_sign = 1.0
                    is_esq = False
                else:
                    continue

                if any(abs(cx_face - sx0) < 1e-3 and math.hypot(cy - sy0, cz - sz0) < (raio_m + sr0 + 1e-3) for sx0, sy0, sz0, sr0 in seen_centers):
                    continue

                target_face = _find_target_face(0, cx_face, target_sign)
                if target_face is None:
                    continue
                seen_centers.append((cx_face, cy, cz, raio_m))

                pts_face = []
                pts_fundo = []
                for i in range(n_seg):
                    ang = 2.0 * math.pi * i / n_seg
                    dy = raio_m * math.cos(ang)
                    dz = raio_m * math.sin(ang)
                    pts_face.append(QVector3D(cx_face, cy + dy, cz + dz))
                    pts_fundo.append(QVector3D(cx_fundo, cy + dy, cz + dz))

                if is_esq:
                    # Face com normal -X: add_hole com pts_face (normal +X)
                    mesh.add_hole(target_face, pts_face)
                    f_bot = mesh.add_face(list(reversed(pts_fundo)))
                    f_bot.attrs["color"] = cor_furo
                    for i in range(n_seg):
                        i_next = (i + 1) % n_seg
                        w_face = mesh.add_face([
                            pts_face[i_next], pts_face[i],
                            pts_fundo[i], pts_fundo[i_next]
                        ])
                        w_face.attrs["color"] = cor_borda
                else:
                    # Face com normal +X: add_hole com reversed(pts_face) (normal -X)
                    mesh.add_hole(target_face, list(reversed(pts_face)))
                    f_bot = mesh.add_face(pts_fundo)
                    f_bot.attrs["color"] = cor_furo
                    for i in range(n_seg):
                        i_next = (i + 1) % n_seg
                        w_face = mesh.add_face([
                            pts_face[i], pts_face[i_next],
                            pts_fundo[i_next], pts_fundo[i]
                        ])
                        w_face.attrs["color"] = cor_borda



def _get_puxador_rgb(cor: str | tuple[float, float, float] | None) -> tuple[float, float, float]:
    """Retorna os valores RGB para o acabamento do puxador."""
    if isinstance(cor, (tuple, list)) and len(cor) >= 3:
        return (float(cor[0]), float(cor[1]), float(cor[2]))
    if not cor:
        return (0.15, 0.15, 0.18)  # Preto fosco
    c = str(cor).lower()
    if "inox" in c or "alum" in c or "prata" in c or "cinza" in c:
        return (0.78, 0.80, 0.83)
    if "dourad" in c or "gold" in c or "champ" in c:
        return (0.85, 0.68, 0.38)
    if "cobre" in c or "rose" in c:
        return (0.80, 0.45, 0.35)
    if "branco" in c:
        return (0.96, 0.96, 0.96)
    return (0.15, 0.15, 0.18)


def _build_perfil_geometry_legacy(
    mesh: Mesh,
    origin: tuple[float, float, float],
    size: tuple[float, float, float],
    perfil_modelo: str = "gola",
    eff_pos: str = "topo",
    door_side: str = "single",
    rgb: tuple[float, float, float] = (0.15, 0.15, 0.18),
    desc_m: float = 0.035,
) -> None:
    """Gera a geometria 3D realista dos perfis de alumínio (Rometal/TrazoMob/Leo Madeiras).

    Modelos suportados:
    - 'gola': Perfil Gola Côncavo (RM-030) - cava côncava anatômica, aba de fixação de 15.4mm e lábio superior arredondado.
    - 'facetato': Perfil Facetato / Aba Curva (RM-027) - flange superior de 37mm cobrindo a chapa, aba traseira de 15.5mm e gancho ergonômico frontal curvo de 7.5mm.
    - 'canal_c': Perfil Central Duplo / Canal C (RM-032) - perfil simétrico de 42mm com canal central e duplo lábio em T (superior e inferior).
    - 'sp7000': Perfil Haste Reta / SP-7000 - canal U de abraço de 26mm x 13.5mm e haste reta vertical superior saliente de 41mm.
    """
    ox, oy, oz = origin
    sx, sy, sz = size
    mod = (perfil_modelo or "gola").lower()

    # Tons com sutil contraste de sombra/brilho metálico
    rgb_escuro = (max(0.0, rgb[0] * 0.65), max(0.0, rgb[1] * 0.65), max(0.0, rgb[2] * 0.65))
    rgb_destaque = (min(1.0, rgb[0] * 1.15), min(1.0, rgb[1] * 1.15), min(1.0, rgb[2] * 1.15))

    if eff_pos == "base":
        # Perfil horizontal montado na base inferior (portas de armários aéreos e basculantes)
        if "facetato" in mod or "aba" in mod:
            # RM-027 Facetato na base
            _make_box_faces(mesh, (ox, oy, oz), (sx, sy, desc_m), rgb)
            _make_box_faces(mesh, (ox, oy - 0.015, oz), (sx, sy + 0.015, 0.002), rgb_destaque)
            # Gancho virado para cima para puxar por baixo
            _make_box_faces(mesh, (ox, oy - 0.015, oz + 0.002), (sx, 0.0025, 0.0075), rgb)
            _make_box_faces(mesh, (ox, oy - 0.0125, oz + 0.007), (sx, 0.005, 0.0025), rgb_escuro)
            # Aba traseira de fixação (sobe por trás do MDF)
            _make_box_faces(mesh, (ox, oy + sy - 0.0015, oz + desc_m), (sx, 0.0015, 0.0155), rgb)

        elif "canal" in mod or "canal_c" in mod or "perfil c" in mod:
            # RM-032 Canal C Duplo na base
            _make_box_faces(mesh, (ox, oy, oz), (sx, sy, desc_m), rgb)
            _make_box_faces(mesh, (ox, oy - 0.0163, oz), (sx, 0.0163, 0.003), rgb_destaque)
            _make_box_faces(mesh, (ox, oy - 0.0163, oz + desc_m - 0.003), (sx, 0.0163, 0.003), rgb_destaque)
            _make_box_faces(mesh, (ox, oy - 0.0163, oz), (sx, 0.003, 0.006), rgb)
            _make_box_faces(mesh, (ox, oy - 0.0163, oz + desc_m - 0.006), (sx, 0.003, 0.006), rgb)
            _make_box_faces(mesh, (ox, oy - 0.003, oz + 0.003), (sx, 0.003, max(0.004, desc_m - 0.006)), rgb_escuro)

        elif "sp7000" in mod or "haste" in mod:
            # SP-7000 Haste Reta na base
            _make_box_faces(mesh, (ox, oy, oz), (sx, sy, desc_m), rgb)
            _make_box_faces(mesh, (ox, oy - 0.0035, oz), (sx, 0.0035, desc_m), rgb)
            _make_box_faces(mesh, (ox, oy + sy - 0.002, oz + desc_m), (sx, 0.002, 0.012), rgb)
            # Haste reta se estendendo para baixo além da base
            _make_box_faces(mesh, (ox, oy - 0.0035, oz - 0.018), (sx, 0.005, 0.018), rgb_destaque)
            _make_box_faces(mesh, (ox, oy - 0.0025, oz - 0.020), (sx, 0.003, 0.002), rgb)

        else:
            # RM-030 Gola Côncavo na base (invertido para puxar por baixo)
            _make_box_faces(mesh, (ox, oy, oz), (sx, sy, desc_m), rgb)
            _make_box_faces(mesh, (ox, oy - 0.006, oz + desc_m * 0.4), (sx, 0.006, desc_m * 0.5), rgb_escuro)
            _make_box_faces(mesh, (ox, oy - 0.012, oz + 0.008), (sx, 0.012, desc_m * 0.4), rgb)
            _make_box_faces(mesh, (ox, oy - 0.0175, oz), (sx, 0.0175, 0.008), rgb_destaque)
            _make_box_faces(mesh, (ox, oy - 0.0175, oz + 0.008), (sx, 0.0035, 0.005), rgb)
            _make_box_faces(mesh, (ox, oy + sy - 0.0015, oz + desc_m), (sx, 0.0015, 0.0154), rgb)

    elif eff_pos in ("extensao", "lateral") and door_side not in ("drawer", "flap"):
        # Perfil vertical na lateral da porta (ao longo de Z)
        sides_to_build = ("left", "right") if door_side == "both" else (door_side,)
        for cur_side in sides_to_build:
            is_left_side = cur_side in ("left", "single")
            larg_mdf = max(0.02, sx - desc_m)
            hx = ox + larg_mdf if is_left_side else ox

            if "facetato" in mod or "aba" in mod:
                # RM-027 vertical
                _make_box_faces(mesh, (hx, oy, oz), (desc_m, sy, sz), rgb)
                _make_box_faces(mesh, (hx, oy - 0.015, oz), (desc_m, sy + 0.015, sz), rgb)
                g_x = (hx + desc_m - 0.0025) if is_left_side else hx
                _make_box_faces(mesh, (g_x, oy - 0.015, oz), (0.0025, 0.0075, sz), rgb_destaque)
                fix_x = (hx - 0.0155) if is_left_side else (hx + desc_m)
                _make_box_faces(mesh, (fix_x, oy + sy - 0.0015, oz), (0.0155, 0.0015, sz), rgb)

            elif "canal" in mod or "canal_c" in mod or "perfil c" in mod:
                # RM-032 vertical Canal C
                _make_box_faces(mesh, (hx, oy, oz), (desc_m, sy, sz), rgb)
                _make_box_faces(mesh, (hx, oy - 0.0163, oz), (desc_m, 0.003, sz), rgb_destaque)
                _make_box_faces(mesh, (hx, oy - 0.003, oz), (desc_m, 0.003, sz), rgb_escuro)
                _make_box_faces(mesh, (hx, oy - 0.0163, oz), (0.003, 0.006, sz), rgb)
                _make_box_faces(mesh, (hx + desc_m - 0.003, oy - 0.0163, oz), (0.003, 0.006, sz), rgb)

            elif "sp7000" in mod or "haste" in mod:
                # SP-7000 vertical
                _make_box_faces(mesh, (hx, oy, oz), (desc_m, sy, sz), rgb)
                _make_box_faces(mesh, (hx, oy - 0.0035, oz), (desc_m, 0.0035, sz), rgb)
                rod_x = (hx + desc_m) if is_left_side else (hx - 0.018)
                _make_box_faces(mesh, (rod_x, oy - 0.0035, oz), (0.018, 0.005, sz), rgb_destaque)

            else:
                # RM-030 Gola vertical
                _make_box_faces(mesh, (hx, oy, oz), (desc_m, sy, sz), rgb)
                aba_x = (hx - 0.004) if is_left_side else (hx + desc_m - 0.012)
                _make_box_faces(mesh, (aba_x, oy - 0.012, oz), (0.016, 0.012, sz), rgb)
                _make_box_faces(mesh, (aba_x, oy - 0.0175, oz), (0.006, 0.006, sz), rgb_destaque)

    else:
        # eff_pos == "topo" (padrão balcões e frentes de gaveta)
        hz = oz + sz - desc_m
        if "facetato" in mod or "aba" in mod:
            # RM-027: Facetato / Aba Curva (Imagem 1)
            # Flange superior plana cobrindo o topo da chapa de MDF e avançando 17mm para frente
            _make_box_faces(mesh, (ox, oy - 0.017, oz + sz - 0.002), (sx, sy + 0.017, 0.002), rgb_destaque)
            # Corpo do perfil preenchendo o corte do MDF
            _make_box_faces(mesh, (ox, oy, hz), (sx, sy, desc_m - 0.002), rgb)
            # Gancho frontal curvo descendo 7.5mm
            _make_box_faces(mesh, (ox, oy - 0.017, oz + sz - 0.0075), (sx, 0.0025, 0.0075), rgb)
            # Ponta interna do gancho
            _make_box_faces(mesh, (ox, oy - 0.0145, oz + sz - 0.0075), (sx, 0.004, 0.0025), rgb_escuro)
            # Aba traseira de fixação (15.5mm descendo atrás do MDF)
            _make_box_faces(mesh, (ox, oy + sy - 0.0015, hz - 0.0155), (sx, 0.0015, 0.0155), rgb)

        elif "canal" in mod or "canal_c" in mod or "perfil c" in mod:
            # RM-032: Canal Duplo / Perfil C Simétrico (Imagem 3)
            # Fundo do perfil
            _make_box_faces(mesh, (ox, oy, hz), (sx, sy, desc_m), rgb)
            # Aba horizontal superior (profundidade 16.3mm)
            _make_box_faces(mesh, (ox, oy - 0.0163, oz + sz - 0.003), (sx, 0.0163, 0.003), rgb_destaque)
            # Aba horizontal inferior (profundidade 16.3mm)
            _make_box_faces(mesh, (ox, oy - 0.0163, hz), (sx, 0.0163, 0.003), rgb_destaque)
            # Lábio frontal superior em T (4.7mm)
            _make_box_faces(mesh, (ox, oy - 0.0163, oz + sz - 0.006), (sx, 0.003, 0.006), rgb)
            # Lábio frontal inferior em T (4.7mm)
            _make_box_faces(mesh, (ox, oy - 0.0163, hz), (sx, 0.003, 0.006), rgb)
            # Parede interna do canal (fundo do canal C recuado)
            _make_box_faces(mesh, (ox, oy - 0.003, hz + 0.003), (sx, 0.003, max(0.004, desc_m - 0.006)), rgb_escuro)

        elif "sp7000" in mod or "haste" in mod:
            # SP-7000: Haste Reta Minimalista (Imagem 4)
            # Canal U abraçando o MDF:
            _make_box_faces(mesh, (ox, oy, hz), (sx, sy, desc_m), rgb)
            _make_box_faces(mesh, (ox, oy - 0.0035, hz), (sx, 0.0035, desc_m), rgb)
            _make_box_faces(mesh, (ox, oy + sy - 0.002, hz - 0.010), (sx, 0.002, desc_m + 0.010), rgb)
            # Haste vertical reta de puxar (eleva-se 18mm acima da porta)
            _make_box_faces(mesh, (ox, oy - 0.0035, oz + sz), (sx, 0.005, 0.018), rgb_destaque)
            # Topo arredondado sutil da haste
            _make_box_faces(mesh, (ox, oy - 0.0025, oz + sz + 0.018), (sx, 0.003, 0.002), rgb)

        else:
            # RM-030: Gola Côncavo Clássico (Imagem 2)
            # Corpo do perfil
            _make_box_faces(mesh, (ox, oy, hz), (sx, sy, desc_m), rgb)
            # Cava côncava ergonômica em facetas suaves
            _make_box_faces(mesh, (ox, oy - 0.006, hz + 0.005), (sx, 0.006, desc_m * 0.4), rgb_escuro)
            _make_box_faces(mesh, (ox, oy - 0.012, hz + desc_m * 0.4), (sx, 0.012, desc_m * 0.35), rgb)
            # Lábio superior arredondado da cava (17.5mm de projeção)
            _make_box_faces(mesh, (ox, oy - 0.0175, oz + sz - 0.008), (sx, 0.0175, 0.008), rgb_destaque)
            # Bico descendente do lábio
            _make_box_faces(mesh, (ox, oy - 0.0175, oz + sz - 0.013), (sx, 0.0035, 0.005), rgb)
            # Aba de fixação traseira (15.4mm descendo atrás do MDF)
            _make_box_faces(mesh, (ox, oy + sy - 0.0015, hz - 0.0154), (sx, 0.0015, 0.0154), rgb)


def _build_perfil_geometry(
    mesh: Mesh,
    origin: tuple[float, float, float],
    size: tuple[float, float, float],
    perfil_modelo: str = "gola",
    eff_pos: str = "topo",
    door_side: str = "single",
    rgb: tuple[float, float, float] = (0.15, 0.15, 0.18),
    desc_m: float = 0.035,
) -> None:
    """Extruda a seção 2D do perfil (biblioteca editável em perfis.py) ao longo da porta."""
    from ..profiles.library import extrude_profile, get_profile

    perfil = get_profile(perfil_modelo)
    if door_side == "both" and eff_pos in ("extensao", "lateral"):
        n1 = extrude_profile(mesh, perfil, origin, size, eff_pos, "left", desc_m, rgb)
        n2 = extrude_profile(mesh, perfil, origin, size, eff_pos, "right", desc_m, rgb)
        if (n1 + n2) == 0:
            _build_perfil_geometry_legacy(mesh, origin, size, perfil_modelo, eff_pos, "both", rgb, desc_m)
        return
    n = extrude_profile(mesh, perfil, origin, size, eff_pos, door_side, desc_m, rgb)
    if n == 0:
        _build_perfil_geometry_legacy(mesh, origin, size, perfil_modelo, eff_pos, door_side, rgb, desc_m)


def _add_handle_geometry(
    mesh: Mesh,
    origin: tuple[float, float, float],
    size: tuple[float, float, float],
    puxador_tipo: str = "alca",
    puxador_cor: str | tuple[float, float, float] | None = None,
    door_side: str = "single",  # "left", "right", "single", "both", "drawer", "flap"
    is_upper: bool = False,
    puxador_pos: str = "padrao",
    desconto_perfil_mm: float = 35.0,  # "padrao", "topo", "extensao", "base", "centro"
    perfil_modelo: str = "gola",
):
    """Adiciona a geometria 3D do puxador (alça, perfil, cava, ponto) à malha da porta ou gaveta."""
    tipo = (puxador_tipo or "alca").lower()
    if tipo in ("sem_puxador", "toque", "fecho_toque", "nenhum", "sem"):
        return

    if door_side == "both":
        _add_handle_geometry(
            mesh, origin, size, puxador_tipo=puxador_tipo, puxador_cor=puxador_cor,
            door_side="left", is_upper=is_upper, puxador_pos=puxador_pos,
            desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
        )
        _add_handle_geometry(
            mesh, origin, size, puxador_tipo=puxador_tipo, puxador_cor=puxador_cor,
            door_side="right", is_upper=is_upper, puxador_pos=puxador_pos,
            desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
        )
        return

    pos = (puxador_pos or "padrao").lower()
    ox, oy, oz = origin
    sx, sy, sz = size
    rgb = _get_puxador_rgb(puxador_cor)

    # Determina a orientação vertical efetiva
    eff_pos = pos
    if eff_pos in ("padrao", "auto"):
        if is_upper or door_side == "flap":
            eff_pos = "base"
        elif door_side == "drawer":
            eff_pos = "topo"
        else:
            eff_pos = "extensao" if sz >= 1.2 else "topo"

    if tipo == "perfil":
        desc_m = min(desconto_perfil_mm / 1000.0, max(0.015, (sx if eff_pos in ("extensao", "lateral") else sz) - 0.05))
        _build_perfil_geometry(
            mesh, origin, size,
            perfil_modelo=perfil_modelo,
            eff_pos=eff_pos,
            door_side=door_side,
            rgb=rgb,
            desc_m=desc_m,
        )

    elif tipo == "cava":
        # Cava Usinada 45°
        cor_cava = (max(0.0, rgb[0] * 0.7), max(0.0, rgb[1] * 0.7), max(0.0, rgb[2] * 0.7))
        if eff_pos in ("extensao", "lateral") and door_side not in ("drawer", "flap"):
            alt = max(0.04, sz - 0.04)
            hz = oz + 0.02
            hy = oy - 0.008
            hx = ox + sx - 0.024 if door_side in ("left", "single") else ox + 0.014
            _make_box_faces(mesh, (hx, hy, hz), (0.010, 0.010, alt), cor_cava)
        elif eff_pos == "base":
            larg = max(0.04, sx - 0.024)
            hx = ox + 0.012
            hy = oy - 0.008
            hz = oz + 0.004
            _make_box_faces(mesh, (hx, hy, hz), (larg, 0.010, 0.024), cor_cava)
        else:
            larg = max(0.04, sx - 0.024)
            hx = ox + 0.012
            hy = oy - 0.008
            hz = oz + sz - 0.028
            _make_box_faces(mesh, (hx, hy, hz), (larg, 0.010, 0.024), cor_cava)

    elif tipo == "ponto":
        # Puxador Ponto / Botão Minimalista
        tam = 0.022
        recuo_x = 0.035
        is_yz_plane = (abs(sx) <= 0.035 and abs(sy) > 0.05 and abs(sz) > 0.05)
        if is_yz_plane:
            hx = ox + sx + 0.001
            if door_side in ("left", "single"):
                hy = oy + sy - recuo_x - tam
            else:
                hy = oy + recuo_x
            if eff_pos == "centro":
                hz = oz + (sz - tam) / 2.0
            elif eff_pos == "base":
                hz = oz + 0.04
            elif eff_pos in ("extensao", "lateral"):
                hz = oz + (sz - tam) / 2.0
            else:
                hz = oz + sz - tam - 0.04
        else:
            hy = oy - tam
            if door_side in ("left", "single"):
                hx = ox + sx - recuo_x - tam
            elif door_side == "right":
                hx = ox + recuo_x
            else:
                hx = ox + (sx - tam) / 2.0

            if eff_pos == "centro":
                hz = oz + (sz - tam) / 2.0
                if door_side == "drawer":
                    hx = ox + (sx - tam) / 2.0
            elif eff_pos == "base":
                hz = oz + 0.04
            elif eff_pos in ("extensao", "lateral"):
                hz = oz + (sz - tam) / 2.0
            else:  # "topo"
                hz = oz + sz - tam - 0.04 if door_side != "drawer" else oz + (sz - tam) / 2.0
        _make_box_faces(mesh, (hx, hy, hz), (tam, tam, tam), rgb)

    else:
        # Puxador Alça / Barra Linear
        is_yz_plane = (abs(sx) <= 0.035 and abs(sy) > 0.05 and abs(sz) > 0.05)
        if is_yz_plane:
            # Porta orientada no plano YZ (espessura da chapa em X, largura em Y, altura em Z)
            # A face frontal da porta da Ala Y no Canto L aponta para +X (para fora do balcão)
            alt = min(0.18, sz * 0.3)
            recuo_y = 0.035
            # door_side="left": puxador no lado da quina/livre (+Y); door_side="right": puxador na extremidade frontal (-Y)
            hy = oy + recuo_y if door_side == "right" else oy + sy - recuo_y - 0.012
            hz = oz + sz - alt - 0.05
            hx = ox + sx + 0.001
            _make_box_faces(mesh, (hx, hy, hz), (0.025, 0.010, alt), rgb)
            _make_box_faces(mesh, (hx, hy + 0.001, hz + 0.015), (0.025, 0.012, 0.010), rgb)
            _make_box_faces(mesh, (hx, hy + 0.001, hz + alt - 0.027), (0.025, 0.012, 0.010), rgb)
        elif door_side == "drawer" or eff_pos == "centro":
            comp = min(0.20, sx * 0.65)
            hx = ox + (sx - comp) / 2.0
            hy = oy - 0.025
            hz = oz + (sz / 2.0) - 0.006 if eff_pos == "centro" or door_side == "drawer" else (oz + sz - 0.05 if eff_pos == "topo" else oz + 0.04)
            # Barra horizontal
            _make_box_faces(mesh, (hx, hy, hz), (comp, 0.010, 0.012), rgb)
            _make_box_faces(mesh, (hx + 0.015, oy - 0.025, hz + 0.001), (0.012, 0.025, 0.010), rgb)
            _make_box_faces(mesh, (hx + comp - 0.027, oy - 0.025, hz + 0.001), (0.012, 0.025, 0.010), rgb)
        elif door_side == "flap":
            comp = min(0.24, sx * 0.5)
            hx = ox + (sx - comp) / 2.0
            hy = oy - 0.025
            hz = oz + 0.04 if eff_pos != "topo" else (oz + sz - 0.04)
            _make_box_faces(mesh, (hx, hy, hz), (comp, 0.010, 0.012), rgb)
            _make_box_faces(mesh, (hx + 0.015, oy - 0.025, hz + 0.001), (0.012, 0.025, 0.010), rgb)
            _make_box_faces(mesh, (hx + comp - 0.027, oy - 0.025, hz + 0.001), (0.012, 0.025, 0.010), rgb)
        elif eff_pos in ("extensao", "lateral"):
            # Barra vertical ao longo da extensão da porta
            alt = min(0.35, sz * 0.55)
            recuo_x = 0.035
            hx = ox + sx - recuo_x - 0.012 if door_side in ("left", "single") else ox + recuo_x
            hz = oz + (sz - alt) / 2.0
            hy = oy - 0.025
            _make_box_faces(mesh, (hx, hy, hz), (0.012, 0.010, alt), rgb)
            _make_box_faces(mesh, (hx + 0.001, oy - 0.025, hz + 0.015), (0.010, 0.025, 0.012), rgb)
            _make_box_faces(mesh, (hx + 0.001, oy - 0.025, hz + alt - 0.027), (0.010, 0.025, 0.012), rgb)
        elif eff_pos == "base":
            # Barra horizontal ou vertical na base
            alt = min(0.18, sz * 0.3)
            recuo_x = 0.035
            hx = ox + sx - recuo_x - 0.012 if door_side in ("left", "single") else ox + recuo_x
            hz = oz + 0.04
            hy = oy - 0.025
            _make_box_faces(mesh, (hx, hy, hz), (0.012, 0.010, alt), rgb)
            _make_box_faces(mesh, (hx + 0.001, oy - 0.025, hz + 0.015), (0.010, 0.025, 0.012), rgb)
            _make_box_faces(mesh, (hx + 0.001, oy - 0.025, hz + alt - 0.027), (0.010, 0.025, 0.012), rgb)
        else:
            # Topo (horizontal ou vertical no topo)
            alt = min(0.18, sz * 0.3)
            recuo_x = 0.035
            hx = ox + sx - recuo_x - 0.012 if door_side in ("left", "single") else ox + recuo_x
            hz = oz + sz - alt - 0.05
            hy = oy - 0.025
            _make_box_faces(mesh, (hx, hy, hz), (0.012, 0.010, alt), rgb)
            _make_box_faces(mesh, (hx + 0.001, oy - 0.025, hz + 0.015), (0.010, 0.025, 0.012), rgb)
            _make_box_faces(mesh, (hx + 0.001, oy - 0.025, hz + alt - 0.027), (0.010, 0.025, 0.012), rgb)


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
    color: tuple[float, float, float] = (0.94, 0.94, 0.92),
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

