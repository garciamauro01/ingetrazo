# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Gerenciador de Réguas de Altura e Linhas-Guia Paramétricas de Parede (WallGuideRulerManager).

Permite:
1. Definir réguas pré-configuradas de marcenaria por ambiente (Cozinha, Quarto, Banheiro, Personalizado);
2. Projetar linhas-guia com cotas nítidas ao longo da face de parede selecionada;
3. Fornecer atração magnética (snap) vertical exata para posicionamento e arraste de móveis.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple, NamedTuple

from PySide6.QtCore import QPointF, Qt, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QVector3D


class LevelSnapResult(tuple):
    """Resultado do snap a uma linha-guia da régua.
    Compatível com tupla de 2 elementos (z_snapped, name) para código legado,
    mas expondo .z, .name e .diff.
    """
    def __new__(cls, z: float, name: str, diff: float = 0.0):
        obj = super().__new__(cls, (z, name))
        obj.z = z
        obj.name = name
        obj.diff = diff
        return obj

    def __repr__(self) -> str:
        return f"LevelSnapResult(z={self.z}, name='{self.name}', diff={self.diff})"


# Presets de alturas de referência por ambiente (em milímetros)
DEFAULT_RULER_PRESETS: Dict[str, List[Dict[str, any]]] = {
    "Cozinha": [
        {"name": "Rodapé / Base Alvenaria", "z_mm": 150, "color": (234, 179, 8)},       # Amarelo
        {"name": "Bancada Inferior", "z_mm": 900, "color": (16, 185, 129)},             # Esmeralda
        {"name": "Início Armários Aéreos", "z_mm": 1500, "color": (14, 165, 233)},       # Sky
        {"name": "Topo Aéreos / Torres", "z_mm": 2200, "color": (168, 85, 247)},        # Roxo
        {"name": "Pé-Direito Superior", "z_mm": 2600, "color": (239, 68, 68)},           # Vermelho
    ],
    "Quarto": [
        {"name": "Mesa de Cabeceira / Baixo", "z_mm": 450, "color": (234, 179, 8)},
        {"name": "Bancada Estudo / Make", "z_mm": 750, "color": (16, 185, 129)},
        {"name": "Cabideiro Superior", "z_mm": 1900, "color": (14, 165, 233)},
        {"name": "Maleiro Superior", "z_mm": 2200, "color": (168, 85, 247)},
        {"name": "Teto / Sanca", "z_mm": 2600, "color": (239, 68, 68)},
    ],
    "Banheiro": [
        {"name": "Base Suspenso", "z_mm": 300, "color": (234, 179, 8)},
        {"name": "Bancada Pia / Cuba", "z_mm": 850, "color": (16, 185, 129)},
        {"name": "Base Espelheira", "z_mm": 1200, "color": (14, 165, 233)},
        {"name": "Topo Espelheira / Armário", "z_mm": 2000, "color": (168, 85, 247)},
    ],
    "Escritório": [
        {"name": "Gaveteiro / Apoio Baixo", "z_mm": 650, "color": (234, 179, 8)},       # Amarelo
        {"name": "Mesa / Estação de Trabalho", "z_mm": 750, "color": (16, 185, 129)},   # Esmeralda (ergonomia padrão NBR)
        {"name": "Prateleira Baixa / Apoio", "z_mm": 1400, "color": (14, 165, 233)},     # Sky
        {"name": "Armário Alto / Nichos", "z_mm": 1800, "color": (168, 85, 247)},       # Roxo
        {"name": "Teto / Fechamento", "z_mm": 2600, "color": (239, 68, 68)},             # Vermelho
    ],
    "Personalizado": [
        {"name": "Nível 1", "z_mm": 900, "color": (16, 185, 129)},
        {"name": "Nível 2", "z_mm": 1500, "color": (14, 165, 233)},
        {"name": "Nível 3", "z_mm": 2200, "color": (168, 85, 247)},
    ],
}


_NON_OCCLUDER_LAYERS = frozenset({"Piso", "Teto", "Iluminacao", "Luzes", "Guias"})
_NON_OCCLUDER_KINDS = frozenset({"floor", "ceiling", "light", "guide"})


def compute_world_face_normal(
    raw_pts: List[QVector3D],
    local_normal: Optional[QVector3D],
    xf=None,
) -> QVector3D:
    """Calcula a normal da face em coordenadas do mundo de forma robusta (inclui faces com recortes e xform)."""
    if local_normal is not None:
        wn = (
            xf.mapVector(local_normal)
            if (xf is not None and hasattr(xf, "mapVector"))
            else QVector3D(local_normal)
        )
        if wn.lengthSquared() > 1e-10:
            return wn.normalized()

    n_pts = len(raw_pts)
    if n_pts >= 3:
        nx = ny = nz = 0.0
        for i in range(n_pts):
            p0 = raw_pts[i]
            p1 = raw_pts[(i + 1) % n_pts]
            nx += (p0.y() - p1.y()) * (p0.z() + p1.z())
            ny += (p0.z() - p1.z()) * (p0.x() + p1.x())
            nz += (p0.x() - p1.x()) * (p0.y() + p1.y())
        newell = QVector3D(nx, ny, nz)
        if newell.lengthSquared() > 1e-10:
            return newell.normalized()

    return QVector3D(0.0, 0.0, 0.0)


def get_camera_eye(cam) -> Optional[QVector3D]:
    """Obtém a posição eye() da câmera em coordenadas de mundo."""
    if cam is None:
        return None
    if hasattr(cam, "eye") and callable(cam.eye):
        return cam.eye()
    if hasattr(cam, "target") and hasattr(cam, "distance"):
        fwd = cam.forward() if (hasattr(cam, "forward") and callable(cam.forward)) else QVector3D(0, 1, 0)
        return cam.target - fwd * cam.distance
    return None


def is_wall_face_visible_to_camera(
    cam,
    raw_pts: List[QVector3D],
    local_normal: Optional[QVector3D],
    center: Optional[QVector3D],
    xf=None,
) -> bool:
    """Determina se a face da parede está voltada para a câmera (perspectiva ou paralela/ortográfica)."""
    if cam is None:
        return True
    world_norm = compute_world_face_normal(raw_pts, local_normal, xf=xf)
    if world_norm.lengthSquared() < 1e-10:
        return True

    if not getattr(cam, "perspective", True):
        if hasattr(cam, "forward") and callable(cam.forward):
            fwd = cam.forward()
            if fwd.lengthSquared() > 1e-10:
                return QVector3D.dotProduct(world_norm, -fwd.normalized()) >= -0.15

    eye_pos = get_camera_eye(cam)
    if eye_pos is None:
        return True

    if raw_pts:
        sx = sum(p.x() for p in raw_pts) / len(raw_pts)
        sy = sum(p.y() for p in raw_pts) / len(raw_pts)
        sz = sum(p.z() for p in raw_pts) / len(raw_pts)
        c_world = QVector3D(sx, sy, sz)
    elif center is not None:
        c_world = xf.map(center) if xf is not None else QVector3D(center)
    else:
        return True

    delta = eye_pos - c_world
    if delta.lengthSquared() < 1e-10:
        return True
    if QVector3D.dotProduct(world_norm, delta.normalized()) >= -0.15:
        return True

    # Em ângulos oblíquos em paredes longas, garante visibilidade se algum ponto da face estiver à frente do observador
    for pt in raw_pts:
        d_pt = eye_pos - pt
        if d_pt.lengthSquared() > 1e-10 and QVector3D.dotProduct(world_norm, d_pt.normalized()) >= -0.05:
            return True
    return False


def _is_opaque_guide_occluder(face, grp, w_grp) -> bool:
    """Retorna True apenas para entidades sólidas opacas que realmente devem ocluir linhas-guia."""
    if grp is w_grp:
        return False
    if grp is not None:
        if getattr(grp, "visible", True) is False or bool(getattr(grp, "hidden", False)):
            return False
        if getattr(grp, "layer", "") in _NON_OCCLUDER_LAYERS:
            return False
        ext = getattr(grp, "ext", None)
        if isinstance(ext, dict):
            if any(k in ext for k in ("trazomob_floor", "trazomob_ceiling", "trazomob_light")):
                return False
            if ext.get("trazomob_role") in _NON_OCCLUDER_KINDS:
                return False
            tm_info = ext.get("trazomob")
            if isinstance(tm_info, dict) and tm_info.get("kind") in _NON_OCCLUDER_KINDS:
                return False

    attrs = getattr(face, "attrs", None)
    if isinstance(attrs, dict):
        if bool(attrs.get("hidden")):
            return False
        for alpha_key in ("opacity", "alpha"):
            val = attrs.get(alpha_key)
            if isinstance(val, (int, float)) and float(val) < 0.99:
                return False
        col = attrs.get("color")
        if isinstance(col, (tuple, list)) and len(col) >= 4 and isinstance(col[3], (int, float)):
            a_val = float(col[3])
            if (isinstance(col[3], float) and a_val <= 1.0 and a_val < 0.99) or a_val < 252.0:
                return False
        mat_name = str(attrs.get("mat") or attrs.get("material") or "").lower()
        if any(tok in mat_name for tok in ("vidro", "glass", "transp")):
            return False
    return True


def _ray_hits_accepts_fast_kwargs(ray_hits_fn) -> bool:
    """Detecta se vp._ray_hits aceita reduce_global/reach/own (Viewport real vs mock simples)."""
    try:
        import inspect
        params = inspect.signature(ray_hits_fn).parameters
        return "reduce_global" in params and "reach" in params and "own" in params
    except Exception:
        return False


_OCCLUDER_MASK_CACHE: dict[tuple, any] = {}
_MAX_OCCLUDER_MASK_CACHE = 16


def build_wall_occluder_context(vp, wall_group) -> Optional[Dict[str, any]]:
    """Prepara contexto de oclusão para linhas-guia e contorno de parede selecionada."""
    cam = getattr(vp, "camera", None)
    if cam is None:
        return None
    is_persp = bool(getattr(cam, "perspective", True))
    cam_eye = get_camera_eye(cam) if is_persp else None
    cam_fwd = None
    if not is_persp and hasattr(cam, "forward") and callable(cam.forward):
        fwd_v = cam.forward()
        if fwd_v.lengthSquared() > 1e-10:
            cam_fwd = fwd_v.normalized()
    if (is_persp and cam_eye is None) or (not is_persp and cam_fwd is None):
        return None

    idx = None
    mask_no_wall = None
    has_ray_hits = hasattr(vp, "_ray_hits") and hasattr(vp, "_pick_index")
    fast_kwargs = _ray_hits_accepts_fast_kwargs(vp._ray_hits) if has_ray_hits else False
    nat = None
    if hasattr(vp, "_lazy_native") and callable(vp._lazy_native):
        try:
            nat = vp._lazy_native()
        except Exception:
            nat = None
    has_lazy = nat is not None and hasattr(vp, "_lazy_face_hits")

    if has_ray_hits:
        try:
            idx = vp._pick_index()
            entities = getattr(idx, "entities", None) if idx is not None else None
            if idx is not None and entities:
                import numpy as np
                scene = getattr(vp, "scene", None)
                cache_key = (
                    id(idx),
                    id(entities),
                    len(entities),
                    id(wall_group),
                    getattr(scene, "version", None),
                )
                base_mask = _OCCLUDER_MASK_CACHE.get(cache_key)
                if base_mask is None:
                    base_mask = np.array(
                        [_is_opaque_guide_occluder(face, grp, wall_group) for (face, grp) in entities],
                        dtype=bool,
                    )
                    if len(_OCCLUDER_MASK_CACHE) >= _MAX_OCCLUDER_MASK_CACHE:
                        _OCCLUDER_MASK_CACHE.clear()
                    _OCCLUDER_MASK_CACHE[cache_key] = base_mask
                mask_arr = base_mask & idx.ent_vis
                if np.any(mask_arr):
                    mask_no_wall = mask_arr
        except Exception:
            mask_no_wall = None

    if mask_no_wall is None and not has_lazy:
        return None

    return {
        "wall_group": wall_group,
        "is_persp": is_persp,
        "cam_eye": cam_eye,
        "cam_fwd": cam_fwd,
        "idx": idx,
        "mask": mask_no_wall,
        "fast_kwargs": fast_kwargs,
        "nat": nat if has_lazy else None,
    }


def _is_point_occluded(vp, pt: QVector3D, occ_ctx: Dict[str, any]) -> bool:
    """Verifica se há algum sólido opaco entre a câmera e o ponto 3D informado."""
    if occ_ctx["is_persp"]:
        cam_eye = occ_ctx["cam_eye"]
        delta = pt - cam_eye
        dist = delta.length()
        if dist <= 1e-4:
            return False
        ray_orig = cam_eye
        ray_dir = delta / dist
    else:
        dist = 200.0
        ray_dir = occ_ctx["cam_fwd"]
        ray_orig = pt - ray_dir * dist

    reach = dist - 0.015
    if reach <= 1e-4:
        return False

    idx = occ_ctx["idx"]
    mask = occ_ctx["mask"]
    nat = occ_ctx["nat"]
    if mask is not None and idx is not None:
        if occ_ctx["fast_kwargs"]:
            hits = vp._ray_hits(
                idx, ray_orig, ray_dir, mask,
                reduce_global=True, reach=reach, own=(nat is None),
            )
            if hits is not None:
                try:
                    t_val = float(hits)
                    if math.isfinite(t_val) and 1e-4 < t_val < reach:
                        return True
                except (TypeError, ValueError):
                    pass
        else:
            import numpy as np
            hits = vp._ray_hits(idx, ray_orig, ray_dir, mask)
            if hits is not None:
                if isinstance(hits, (int, float)):
                    if math.isfinite(float(hits)) and 1e-4 < float(hits) < reach:
                        return True
                elif np.any(np.isfinite(hits) & (hits > 1e-4) & (hits < reach)):
                    return True

    if nat is not None:
        try:
            lazy = vp._lazy_face_hits(nat, ray_orig, ray_dir, "vis", reach=reach)
        except Exception:
            lazy = None
        if lazy is not None:
            tt, _area, _keys, ent_fn, _place_fn = lazy
            w_grp = occ_ctx["wall_group"]
            for m_idx, t_val in enumerate(tt):
                tf = float(t_val)
                if math.isfinite(tf) and 1e-4 < tf < reach:
                    f_hit, g_hit = ent_fn(m_idx)
                    if _is_opaque_guide_occluder(f_hit, g_hit, w_grp):
                        return True
    return False


def filter_occluded_segments(
    vp,
    p0: QVector3D,
    p1: QVector3D,
    occ_ctx: Optional[Dict[str, any]],
    step_m: float = 0.12,
    min_steps: int = 4,
    max_steps: int = 36,
    test_offset: Optional[QVector3D] = None,
) -> List[Tuple[QVector3D, QVector3D]]:
    """Subdivide um segmento 3D e retorna apenas os trechos contínuos não ocluídos."""
    if occ_ctx is None:
        return [(p0, p1)]
    diff = p1 - p0
    total_len = diff.length()
    if total_len < 1e-4:
        return []

    coarse_step = max(step_m * 2.2, 0.25)
    n_coarse = max(min_steps, min(min(16, max_steps), int(math.ceil(total_len / coarse_step))))

    def _is_vis(t_param: float) -> bool:
        pt = p0 + diff * t_param
        if test_offset is not None:
            pt = pt + test_offset
        return not _is_point_occluded(vp, pt, occ_ctx)

    mids_t = [(s_i + 0.5) / n_coarse for s_i in range(n_coarse)]
    mids_vis = [_is_vis(t) for t in mids_t]

    visible_runs: List[Tuple[QVector3D, QVector3D]] = []
    run_start_t: Optional[float] = 0.0 if mids_vis[0] else None

    for s_i in range(n_coarse - 1):
        v_a = mids_vis[s_i]
        v_b = mids_vis[s_i + 1]
        if v_a == v_b:
            continue
        t_lo = mids_t[s_i]
        t_hi = mids_t[s_i + 1]
        for _ in range(2):
            t_mid = 0.5 * (t_lo + t_hi)
            if _is_vis(t_mid) == v_a:
                t_lo = t_mid
            else:
                t_hi = t_mid
        t_split = 0.5 * (t_lo + t_hi)
        if v_a and not v_b:
            if run_start_t is not None:
                visible_runs.append((p0 + diff * run_start_t, p0 + diff * t_split))
                run_start_t = None
        else:
            run_start_t = t_split

    if run_start_t is not None and mids_vis[-1]:
        visible_runs.append((p0 + diff * run_start_t, p1))
    return visible_runs


class WallGuideRulerManager:
    """Gerencia as réguas ativas, configurações de altura e renderização das guias."""

    _instance: Optional[WallGuideRulerManager] = None

    def __init__(self) -> None:
        from ..domain.preferences import TrazoMobPreferencesManager
        prefs_mgr = TrazoMobPreferencesManager.get_instance()
        wg_cfg = prefs_mgr.get_wall_guides_config()

        self.presets = dict(DEFAULT_RULER_PRESETS)
        custom_presets = wg_cfg.get("custom_presets")
        if isinstance(custom_presets, dict):
            for k, v in custom_presets.items():
                if isinstance(v, list):
                    self.presets[k] = v

        self.active_preset_name = wg_cfg.get("active_preset", "Cozinha")
        if self.active_preset_name not in self.presets:
            self.active_preset_name = "Cozinha"
        self.visible = bool(wg_cfg.get("visible", True))
        self.show_labels = bool(wg_cfg.get("show_labels", False))
        self.snap_enabled = bool(wg_cfg.get("snap_enabled", True))

    @classmethod
    def get_instance(cls) -> WallGuideRulerManager:
        if cls._instance is None:
            cls._instance = WallGuideRulerManager()
        return cls._instance

    def save_preferences(self) -> None:
        """Salva as configurações atuais de régua nas preferências persistentes do usuário."""
        from ..domain.preferences import TrazoMobPreferencesManager
        prefs_mgr = TrazoMobPreferencesManager.get_instance()
        # Preserva apenas presets que diferem do padrão para não inflar o JSON
        custom = {k: v for k, v in self.presets.items() if k not in DEFAULT_RULER_PRESETS or v != DEFAULT_RULER_PRESETS[k]}
        prefs_mgr.save_wall_guides_config(
            active_preset=self.active_preset_name,
            visible=self.visible,
            show_labels=self.show_labels,
            snap_enabled=self.snap_enabled,
            custom_presets=custom,
        )

    def get_active_levels(self) -> List[Dict[str, any]]:
        """Retorna a lista de níveis de altura da régua ativa."""
        return self.presets.get(self.active_preset_name, self.presets.get("Cozinha", []))

    def get_tower_top_z_mm(self) -> float:
        """Retorna a cota Z (em mm) da linha-guia de Topo de Aéreos / Torres da régua ativa.

        Procura primeiro por palavras-chave típicas ('torre', 'topo aéreos', 'topo aereos',
        'maleiro', 'armário alto', 'topo espelheira'). Se não encontrar pelo nome,
        seleciona a guia na faixa de 1800 a 2450 mm (ou a penúltima guia antes do teto).
        Fallback padrão: 2200.0 mm.
        """
        levels = self.get_active_levels()
        if not levels:
            return 2200.0

        sorted_levels = sorted(levels, key=lambda x: float(x.get("z_mm", 0)))
        keywords = ("torre", "topo aéreos", "topo aereos", "maleiro", "armário alto", "armario alto", "topo espelheira")
        for lv in sorted_levels:
            name_low = str(lv.get("name", "")).lower()
            if any(k in name_low for k in keywords):
                z_val = float(lv.get("z_mm", 2200.0))
                if z_val > 1000.0:
                    return z_val

        # Fallback por faixa típica de topo de aéreos/torres (1800mm a 2450mm)
        in_range = [float(lv.get("z_mm", 0)) for lv in sorted_levels if 1800.0 <= float(lv.get("z_mm", 0)) <= 2450.0]
        if in_range:
            return in_range[-1]

        # Se houver pelo menos 2 níveis e o último for pé-direito/teto (>= 2500mm), usa o penúltimo
        if len(sorted_levels) >= 2 and float(sorted_levels[-1].get("z_mm", 0)) >= 2500.0:
            return float(sorted_levels[-2].get("z_mm", 2200.0))

        return float(sorted_levels[-1].get("z_mm", 2200.0))

    def set_active_preset(self, name: str) -> None:
        if name in self.presets:
            self.active_preset_name = name
            self.save_preferences()

    def create_preset(self, name: str, levels: Optional[List[Dict[str, any]]] = None, base_preset: Optional[str] = None) -> bool:
        """Cria um novo preset de régua com nome único."""
        name = name.strip()
        if not name or name in self.presets:
            return False
        if levels is not None:
            self.presets[name] = [dict(lv) for lv in levels]
        elif base_preset and base_preset in self.presets:
            self.presets[name] = [dict(lv) for lv in self.presets[base_preset]]
        else:
            self.presets[name] = [
                {"name": "Nível 1", "z_mm": 900, "color": (16, 185, 129)},
                {"name": "Nível 2", "z_mm": 1500, "color": (14, 165, 233)},
            ]
        self.active_preset_name = name
        self.save_preferences()
        return True

    def delete_preset(self, name: str) -> bool:
        """Exclui um preset. Não permite excluir se for o único restante."""
        if len(self.presets) <= 1 or name not in self.presets:
            return False
        del self.presets[name]
        if self.active_preset_name == name:
            self.active_preset_name = next(iter(self.presets.keys()))
        self.save_preferences()
        return True

    def rename_preset(self, old_name: str, new_name: str) -> bool:
        """Renomeia um preset existente."""
        new_name = new_name.strip()
        if not new_name or old_name not in self.presets or (new_name != old_name and new_name in self.presets):
            return False
        if new_name == old_name:
            return True
        levels = self.presets.pop(old_name)
        self.presets[new_name] = levels
        if self.active_preset_name == old_name:
            self.active_preset_name = new_name
        self.save_preferences()
        return True

    def update_preset_levels(self, name: str, levels: List[Dict[str, any]]) -> bool:
        """Atualiza a lista completa de níveis de um preset."""
        if name not in self.presets:
            return False
        # Ordena os níveis por altura (z_mm) crescente
        sorted_levels = sorted([dict(lv) for lv in levels], key=lambda x: int(x.get("z_mm", 0)))
        self.presets[name] = sorted_levels
        self.save_preferences()
        return True

    def reset_preset_to_default(self, name: str) -> bool:
        """Restaura um preset de fábrica para sua configuração original."""
        if name in DEFAULT_RULER_PRESETS:
            self.presets[name] = [dict(lv) for lv in DEFAULT_RULER_PRESETS[name]]
            self.save_preferences()
            return True
        return False

    def compute_wall_face_guide_segments(
        self,
        wall_face_info,
        margin_m: float = 0.05,
    ) -> List[Dict[str, any]]:
        """Calcula as coordenadas 3D (p0, p1) de cada linha-guia na face da parede selecionada."""
        if wall_face_info is None or not getattr(wall_face_info, "face", None):
            return []

        pts = getattr(wall_face_info.face, "vertices", [])
        if len(pts) < 2:
            return []

        xf = getattr(wall_face_info.wall_group, "xform", None)
        raw_pts = [xf.map(p) if xf is not None else p for p in pts]

        # Encontra os limites horizontais e o plano exato da face em coordenadas de mundo
        normal = compute_world_face_normal(raw_pts, wall_face_info.normal, xf=xf)
        n_dir = QVector3D(normal.x(), normal.y(), 0.0)
        if n_dir.lengthSquared() < 1e-10:
            return []
        n_dir = n_dir.normalized()
        u_dir = QVector3D(-n_dir.y(), n_dir.x(), 0.0).normalized()

        projs = [QVector3D.dotProduct(p, u_dir) for p in raw_pts]
        min_u, max_u = min(projs), max(projs)

        # Centro em coordenadas de mundo alinhado ao grupo transformado
        if xf is not None and wall_face_info.center is not None:
            c_pt = xf.map(wall_face_info.center)
        else:
            c_pt = wall_face_info.center or raw_pts[0]
        center_u = QVector3D.dotProduct(c_pt, u_dir)
        p_base_left = c_pt + u_dir * (min_u - center_u - margin_m)
        p_base_right = c_pt + u_dir * (max_u - center_u + margin_m)

        # Projeta um leve deslocamento (offset) na direção da normal para desenhar na face da parede
        p_base_left = p_base_left + n_dir * 0.002
        p_base_right = p_base_right + n_dir * 0.002

        levels = self.get_active_levels()
        guides = []
        for lv in levels:
            z_m = float(lv["z_mm"]) / 1000.0
            p0 = QVector3D(p_base_left.x(), p_base_left.y(), z_m)
            p1 = QVector3D(p_base_right.x(), p_base_right.y(), z_m)
            guides.append({
                "name": lv["name"],
                "z_mm": lv["z_mm"],
                "z_m": z_m,
                "color": lv["color"],
                "p0": p0,
                "p1": p1,
            })

        return guides

    def draw_ruler_overlay(self, vp, painter: QPainter, wall_face_info, occ_ctx: Optional[Dict[str, any]] = None) -> None:
        """Renderiza as linhas-guia com traçado moderno e badges com cotas em milímetros."""
        if not self.visible or wall_face_info is None or not wall_face_info.face:
            return

        # Se a face ou o grupo de parede estiverem ocultos, não desenha as réguas/linhas-guia
        if getattr(wall_face_info.wall_group, "hidden", False) or bool(getattr(wall_face_info.face, "attrs", {}).get("hidden")):
            return

        # Back-face culling consistente para perspectiva e projeção paralela
        cam = getattr(vp, "camera", None)
        if cam is not None:
            xf = getattr(wall_face_info.wall_group, "xform", None)
            pts_face = getattr(wall_face_info.face, "vertices", [])
            raw_pts = [xf.map(p) if xf is not None else p for p in pts_face]
            if not is_wall_face_visible_to_camera(
                cam, raw_pts, wall_face_info.normal, wall_face_info.center, xf=xf
            ):
                return

        guides = self.compute_wall_face_guide_segments(wall_face_info)
        if not guides:
            return

        painter.save()
        try:
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.TextAntialiasing, True)

            font = QFont()
            font.setPointSize(9)
            font.setBold(True)
            painter.setFont(font)
            fm = painter.fontMetrics()

            # Filtro de oclusão: verifica apenas sólidos opacos (excluindo piso, teto, luzes e vidros)
            if occ_ctx is None:
                occ_ctx = build_wall_occluder_context(vp, wall_face_info.wall_group)

            for g in guides:
                p0, p1 = g["p0"], g["p1"]
                sub_segs = filter_occluded_segments(vp, p0, p1, occ_ctx, step_m=0.10, min_steps=4, max_steps=40)

                if not sub_segs:
                    continue

                r, gr, b = g["color"]
                line_color = QColor(r, gr, b, 230)
                pen = QPen(line_color, 1.8, Qt.DashLine)
                painter.setPen(pen)

                first_vis_pt = None

                for sa, sb in sub_segs:
                    seg = vp._clip_segment_front(sa, sb)
                    if seg is None:
                        continue
                    s0, s1 = seg
                    px0 = vp.world_to_pixel(s0)
                    px1 = vp.world_to_pixel(s1)
                    if px0 is None or px1 is None:
                        continue
                    vis = vp._clip_pixel_line(px0, px1, margin=32.0)
                    if vis is None:
                        continue
                    p_start = QPointF(*vis[0])
                    p_end = QPointF(*vis[1])
                    painter.drawLine(p_start, p_end)
                    if first_vis_pt is None:
                        first_vis_pt = p_start if p_start.x() <= p_end.x() else p_end

                # Badge de cota e nome da linha-guia (apenas se configurado para exibir)
                if self.show_labels and first_vis_pt is not None:
                    txt = f"{g['name']} ({g['z_mm']} mm)"
                    tw, th = fm.horizontalAdvance(txt), fm.height()
                    pad_x, pad_y = 6, 3

                    badge_x = first_vis_pt.x() + 10
                    badge_y = first_vis_pt.y() - th - pad_y

                    badge_rect = QRectF(badge_x, badge_y, tw + pad_x * 2, th + pad_y * 2)

                    painter.setPen(QPen(line_color, 1.0))
                    painter.setBrush(QColor(24, 28, 36, 230))
                    painter.drawRoundedRect(badge_rect, 4.0, 4.0)

                    painter.setPen(QColor(255, 255, 255))
                    painter.drawText(badge_rect, Qt.AlignCenter, txt)

        finally:
            painter.restore()

    def snap_to_levels(self, current_z: float, threshold_m: float = 0.08) -> Optional[LevelSnapResult]:
        """Retorna LevelSnapResult(z_snapped, guide_name, diff) se o current_z estiver dentro do threshold de atração.
        Compatível com desempacotamento de 2 itens: (snapped_z, guide_name) = res.
        """
        if not self.snap_enabled:
            return None

        best_z = None
        best_name = None
        min_diff = threshold_m

        for lv in self.get_active_levels():
            z_m = float(lv["z_mm"]) / 1000.0
            diff = abs(current_z - z_m)
            if diff <= min_diff:
                min_diff = diff
                best_z = z_m
                best_name = lv["name"]

        if best_z is not None:
            return LevelSnapResult(best_z, best_name, min_diff)
        return None

    def get_slot_between_guides(self, z_world: float) -> Dict[str, any]:
        """Detecta a faixa vertical RIGOROSA entre as duas linhas-guia adjacentes onde o usuário clicou.

        Obedece estritamente às linhas-guia da régua:
        - z_base: cota Z exata da linha-guia inferior do vão (ou piso 0.0 se clicou abaixo da primeira guia)
        - z_top: cota Z exata da linha-guia superior do vão
        - height_mm: altura exata do vão (z_top - z_base) em milímetros
        """
        levels = self.get_active_levels()
        if not levels:
            if z_world <= 1.10:
                z_b, z_t = 0.0, 0.90
            else:
                z_b, z_t = 1.50, 2.20
            h_mm = round((z_t - z_b) * 1000.0)
            return {
                "z_base": z_b,
                "z_top": z_t,
                "height_mm": float(h_mm),
                "category": "inferior" if z_b < 1.0 else "aereo",
                "default_depth_mm": 550.0 if z_b < 1.0 else 350.0,
                "label": f"Vão ({int(z_b * 1000)} a {int(z_t * 1000)} mm)",
                "lower_guide": f"{int(z_b * 1000)}mm",
                "upper_guide": f"{int(z_t * 1000)}mm",
            }

        sorted_levels = sorted(levels, key=lambda x: float(x.get("z_mm", 0)))
        z_vals = [float(lv["z_mm"]) / 1000.0 for lv in sorted_levels]
        names = [lv.get("name", f"{lv.get('z_mm')}mm") for lv in sorted_levels]

        # 1. Clique abaixo da primeira linha-guia: entre o Piso (0.0) e a 1ª Linha-Guia
        if z_world < z_vals[0]:
            z_base = 0.0
            z_top = z_vals[0]
            name_lo = "Piso (0 mm)"
            name_hi = names[0]
        # 2. Clique acima da última linha-guia: entre a última Linha-Guia e o Teto (estimado em +400mm ou 2.60m)
        elif z_world >= z_vals[-1]:
            z_base = z_vals[-1]
            z_top = max(z_base + 0.40, 2.60)
            name_lo = names[-1]
            name_hi = "Teto"
        # 3. Clique entre duas linhas-guia adjacentes: z_base = guia inferior, z_top = guia superior
        else:
            lower_idx = 0
            for i in range(len(z_vals) - 1):
                if z_vals[i] <= z_world < z_vals[i + 1]:
                    lower_idx = i
                    break
            z_base = z_vals[lower_idx]
            z_top = z_vals[lower_idx + 1]
            name_lo = names[lower_idx]
            name_hi = names[lower_idx + 1]

        # Altura exata e rígida entre as duas linhas-guia selecionadas
        h_mm = round((z_top - z_base) * 1000.0)

        # Categoria e profundidade sugerida
        if z_base < 0.20 and z_top <= 1.05:
            cat = "inferior"
            p_mm = 550.0
        elif z_base >= 1.20 and z_top <= 2.30:
            cat = "aereo"
            p_mm = 350.0
        elif z_top > 2.20:
            cat = "fechamento"
            p_mm = 350.0
        elif z_base >= 0.70 and z_top <= 1.60:
            cat = "nicho"
            p_mm = 300.0
        else:
            cat = "aereo" if z_base >= 1.10 else "inferior"
            p_mm = 350.0 if cat == "aereo" else 550.0

        lbl = f"{name_lo} a {name_hi} ({h_mm} mm)"

        return {
            "z_base": z_base,
            "z_top": z_top,
            "height_mm": float(h_mm),
            "category": cat,
            "default_depth_mm": p_mm,
            "label": lbl,
            "lower_guide": name_lo,
            "upper_guide": name_hi,
        }
