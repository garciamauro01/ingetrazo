# SPDX-License-Identifier: GPL-3.0-or-later
"""Gerenciador visual e ferramenta de inserção e controle de luzes físicas do TrazoMob.

Permite inserir e controlar:
- Spot Embutido (Dicroica / AR70 / PAR20) com mira direcionável e ângulo do facho
- Fita LED de Marcenaria / Perfil Linear (iluminação indireta sob armários)
- Ponto de Luz Difuso / Plafon / Pendente
- Controle de Temperatura de Cor em Kelvin (2200K quente a 6500K frio)
- Potência em Watts
- Liga/Desliga individual (se todas forem apagadas num quarto fechado, o render respeita a escuridão física total)
"""
from __future__ import annotations

import logging
import math
from typing import Optional

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPen,
    QVector3D,
)

logger = logging.getLogger("trazomob.light_tools")

_TRAZOMOB_LIGHT_KINDS = ("point", "spot", "led_strip")
_TRAZOMOB_EXTRA_KEYS = ("p1", "p2", "length", "profile_w", "target", "ies_path", "blend", "double_sided")



from .lighting import (
    AimLightTool,
    InsertLedStripTool,
    _get_document_lights,
)
from .lighting_ui import LightQuickPopupHUD

_LIGHT_OCCLUDER_MASK_CACHE: dict = {}
_MAX_LIGHT_OCCLUDER_MASK_CACHE = 32


def _is_opaque_light_occluder(face, grp) -> bool:
    """Retorna True se ``(face, grp)`` deve ocluir ícones e fitas LED."""
    if grp is not None:
        ext = getattr(grp, "ext", None)
        if isinstance(ext, dict) and ("trazomob_light" in ext or "atomic_light" in ext):
            return False
    if face is not None:
        if getattr(face, "hidden", False):
            return False
        attrs = getattr(face, "attrs", None)
        if isinstance(attrs, dict):
            if attrs.get("mat") in ("Fonte de Luz", "Fita LED Emissora"):
                return False
            alpha = attrs.get("alpha", 1.0)
            try:
                if float(alpha) < 0.85:
                    return False
            except (TypeError, ValueError):
                pass
    return True


def _build_light_occluder_context(vp, *, require_camera: bool = True):
    """Monta contexto acelerado de oclusão para luzes excluindo a própria geometria da luz."""
    if vp is None:
        return None
    cam = getattr(vp, "camera", None)
    is_persp = bool(getattr(cam, "perspective", True)) if cam is not None else True
    cam_eye = cam.eye() if (cam is not None and callable(getattr(cam, "eye", None))) else None
    cam_fwd = None
    if not is_persp and cam is not None:
        fwd_fn = getattr(cam, "forward", None)
        if callable(fwd_fn):
            cam_fwd = fwd_fn()
        elif cam_eye is not None and getattr(cam, "target", None) is not None:
            cam_fwd = cam.target - cam_eye
        if cam_fwd is not None and cam_fwd.length() > 1e-6:
            cam_fwd = cam_fwd.normalized()
        else:
            cam_fwd = None

    if require_camera:
        if is_persp and cam_eye is None:
            return None
        if not is_persp and cam_fwd is None:
            return None

    has_pick = callable(getattr(vp, "_pick_index", None)) and callable(getattr(vp, "_ray_hits", None))
    idx = vp._pick_index() if has_pick else None
    mask_arr = None
    fast_kwargs = False
    if has_pick and idx is not None:
        try:
            import inspect
            sig = inspect.signature(vp._ray_hits)
            fast_kwargs = "reduce_global" in sig.parameters
        except Exception:
            fast_kwargs = False
        try:
            entities = getattr(idx, "entities", None) or ()
            if entities:
                import numpy as np
                scene = getattr(vp, "scene", None)
                cache_key = (
                    id(idx),
                    id(entities),
                    len(entities),
                    getattr(scene, "version", None),
                )
                base_mask = _LIGHT_OCCLUDER_MASK_CACHE.get(cache_key)
                if base_mask is None:
                    base_mask = np.array(
                        [_is_opaque_light_occluder(face, grp) for (face, grp) in entities],
                        dtype=bool,
                    )
                    if len(_LIGHT_OCCLUDER_MASK_CACHE) >= _MAX_LIGHT_OCCLUDER_MASK_CACHE:
                        _LIGHT_OCCLUDER_MASK_CACHE.clear()
                    _LIGHT_OCCLUDER_MASK_CACHE[cache_key] = base_mask
                ent_vis = getattr(idx, "ent_vis", None)
                candidate = (base_mask & ent_vis) if ent_vis is not None else base_mask
                if np.any(candidate):
                    mask_arr = candidate
        except Exception:
            mask_arr = None

    nat = None
    has_lazy = False
    if callable(getattr(vp, "_lazy_native", None)) and callable(getattr(vp, "_lazy_face_hits", None)):
        try:
            nat = vp._lazy_native()
            has_lazy = nat is not None
        except Exception:
            nat = None
            has_lazy = False

    if mask_arr is None and not has_lazy:
        return None

    return {
        "is_persp": is_persp,
        "cam_eye": cam_eye,
        "cam_fwd": cam_fwd,
        "idx": idx,
        "mask": mask_arr,
        "fast_kwargs": fast_kwargs,
        "nat": nat if has_lazy else None,
    }


def _ray_blocked(vp, ray_orig: QVector3D, ray_dir: QVector3D, reach: float, occ_ctx=None) -> bool:
    """Retorna True se o raio atingir qualquer superfície opaca antes de ``reach``."""
    if reach <= 1e-4:
        return False

    if occ_ctx is not None:
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
                for m_idx, t_val in enumerate(tt):
                    tf = float(t_val)
                    if math.isfinite(tf) and 1e-4 < tf < reach:
                        try:
                            face, grp = ent_fn(m_idx)
                        except Exception:
                            face, grp = None, None
                        if _is_opaque_light_occluder(face, grp):
                            return True
        return False

    ray_dist_fn = getattr(vp, "ray_distance", None)
    if callable(ray_dist_fn):
        try:
            t_hit = ray_dist_fn(ray_orig, ray_dir)
            if t_hit is not None and 1e-4 < float(t_hit) < reach:
                return True
        except Exception as exc:
            logger.debug("teste de oclusão da luz falhou: %s", exc)
    return False


# ── Overlay Gráfico e Seleção de Luzes no 3D ──────────────────────────────────
class TrazoMobLightVisualizer:
    """Gerencia a renderização dos cones de spot, alvos de mira, fitas LED e seleção no viewport."""

    _selected_light_idx: Optional[int] = None
    _active_hud: Optional[LightQuickPopupHUD] = None

    @classmethod
    def get_selected_index(cls) -> Optional[int]:
        return cls._selected_light_idx

    @classmethod
    def set_selected_index(cls, idx: Optional[int], viewport=None):
        cls._selected_light_idx = idx
        if viewport is not None:
            viewport.update()

    @classmethod
    def is_point_visible(
        cls,
        viewport,
        world_pt: QVector3D,
        normal_hint: Optional[QVector3D] = None,
        _ctx=None,
    ) -> bool:
        """Verifica se o ponto 3D está desobstruído na visão da câmera (sem objetos/móveis à frente)."""
        test_pt = world_pt
        if normal_hint is not None and normal_hint.length() > 1e-6:
            test_pt = world_pt + normal_hint.normalized() * 0.002

        ctx = _ctx if _ctx is not None else _build_light_occluder_context(viewport, require_camera=True)
        if ctx is not None:
            if ctx["is_persp"]:
                delta = test_pt - ctx["cam_eye"]
                dist_pt = delta.length()
                if dist_pt < 0.02:
                    return True
                ray_orig = ctx["cam_eye"]
                ray_dir = delta / dist_pt
            else:
                dist_pt = 200.0
                ray_dir = ctx["cam_fwd"]
                ray_orig = test_pt - ray_dir * dist_pt
            reach = dist_pt - 0.003
            return not _ray_blocked(viewport, ray_orig, ray_dir, reach, ctx)

        cam = getattr(viewport, "camera", None)
        if cam is None:
            return True
        is_persp = bool(getattr(cam, "perspective", True))
        eye = cam.eye() if callable(getattr(cam, "eye", None)) else None
        if is_persp:
            if eye is None:
                return True
            delta = test_pt - eye
            dist_pt = delta.length()
            if dist_pt < 0.02:
                return True
            ray_orig = eye
            ray_dir = delta / dist_pt
        else:
            fwd_fn = getattr(cam, "forward", None)
            ray_dir = fwd_fn() if callable(fwd_fn) else None
            if ray_dir is None or ray_dir.length() < 1e-6:
                return True
            ray_dir = ray_dir.normalized()
            dist_pt = 200.0
            ray_orig = test_pt - ray_dir * dist_pt

        # Fallback sem máscara de grupos: tolerância de 8mm cobre o perfil fino (<=6.5mm) e barra MDF de 15/18mm
        reach = dist_pt - 0.008
        return not _ray_blocked(viewport, ray_orig, ray_dir, reach, None)

    @classmethod
    def clip_visible_led_segments(
        cls,
        viewport,
        vec_p1: QVector3D,
        vec_p2: QVector3D,
        normal_hint: Optional[QVector3D] = None,
        _ctx=None,
        samples: int = 24,
    ) -> list[tuple[QVector3D, QVector3D, bool, bool]]:
        """Subdivide uma fita LED e recorta apenas os trechos realmente visíveis pela câmera."""
        delta = vec_p2 - vec_p1
        length = delta.length()
        if length < 1e-4:
            if cls.is_point_visible(viewport, vec_p1, normal_hint=normal_hint, _ctx=_ctx):
                return [(vec_p1, vec_p2, True, True)]
            return []

        occ_ctx = _ctx if _ctx is not None else _build_light_occluder_context(viewport, require_camera=True)
        n = max(max(8, int(samples)), min(64, int(math.ceil(length / 0.04))))

        def _vis_at(t_param: float) -> bool:
            pt = vec_p1 + delta * t_param
            return cls.is_point_visible(viewport, pt, normal_hint=normal_hint, _ctx=occ_ctx)

        def _refine_boundary(t_lo: float, t_hi: float, lo_vis: bool) -> float:
            for _ in range(6):
                t_mid = (t_lo + t_hi) * 0.5
                if _vis_at(t_mid) == lo_vis:
                    t_lo = t_mid
                else:
                    t_hi = t_mid
            return (t_lo + t_hi) * 0.5

        vis_samples = [_vis_at(k / n) for k in range(n + 1)]
        if not any(vis_samples):
            return []
        if all(vis_samples):
            return [(vec_p1, vec_p2, True, True)]

        segments: list[tuple[QVector3D, QVector3D, bool, bool]] = []
        seg_start_t: Optional[float] = 0.0 if vis_samples[0] else None
        seg_start_exact = bool(vis_samples[0])

        for k in range(1, n + 1):
            t_prev = (k - 1) / n
            t_cur = k / n
            v_prev = vis_samples[k - 1]
            v_cur = vis_samples[k]
            if not v_prev and v_cur:
                seg_start_t = _refine_boundary(t_prev, t_cur, False)
                seg_start_exact = False
            elif v_prev and not v_cur and seg_start_t is not None:
                t_end = _refine_boundary(t_prev, t_cur, True)
                segments.append((vec_p1 + delta * seg_start_t, vec_p1 + delta * t_end, seg_start_exact, False))
                seg_start_t = None

        if seg_start_t is not None:
            segments.append((vec_p1 + delta * seg_start_t, vec_p2, seg_start_exact, True))

        return segments

    @classmethod
    def pick_light_or_target(cls, viewport, px: float, py: float) -> Optional[tuple[str, int]]:
        """Verifica se o clique pegou a lâmpada/spot, fita LED ou o ponto focal de um spot.
        Retorna ('bulb', idx), ('target', idx), ('led_p1', idx), ('led_p2', idx) ou None.
        Ignora luzes que estejam obstruídas por móveis ou paredes.
        """
        lights = _get_document_lights(viewport)
        best, best_d = None, 35.0
        occ_ctx = _build_light_occluder_context(viewport, require_camera=True)

        for i, lt in enumerate(lights):
            kind = lt.get("kind", "point")
            pos = lt.get("pos")

            # 1. Ponto focal / Target de Spot
            if kind == "spot":
                t_pos = lt.get("target")
                if not t_pos and "dir" in lt and pos:
                    d = lt["dir"]
                    t_pos = [pos[0] + d[0] * 1.5, pos[1] + d[1] * 1.5, pos[2] + d[2] * 1.5]
                if t_pos:
                    vec_t = QVector3D(*t_pos)
                    if cls.is_point_visible(viewport, vec_t, _ctx=occ_ctx):
                        p = viewport.world_to_pixel(vec_t)
                        if p is not None:
                            dist = math.hypot(p[0] - px, p[1] - py)
                            if dist <= best_d:
                                best, best_d = ("target", i), dist

            # 2. Extremidades da Fita LED (P1 / P2)
            if kind == "led_strip" and "p1" in lt and "p2" in lt:
                d_raw = lt.get("dir")
                n_hint = QVector3D(*d_raw) if isinstance(d_raw, (list, tuple)) and len(d_raw) >= 3 else None
                for k_name, pt_vec in (("led_p1", lt["p1"]), ("led_p2", lt["p2"])):
                    vec_p = QVector3D(*pt_vec)
                    if cls.is_point_visible(viewport, vec_p, normal_hint=n_hint, _ctx=occ_ctx):
                        p = viewport.world_to_pixel(vec_p)
                        if p is not None:
                            dist = math.hypot(p[0] - px, p[1] - py)
                            if dist <= best_d:
                                best, best_d = (k_name, i), dist

            # 3. Bulbo principal / Posição da Luz
            if pos:
                vec_pos = QVector3D(*pos)
                if cls.is_point_visible(viewport, vec_pos, _ctx=occ_ctx):
                    p = viewport.world_to_pixel(vec_pos)
                    if p is not None:
                        dist = math.hypot(p[0] - px, p[1] - py)
                        if dist <= best_d:
                            best, best_d = ("bulb", i), dist

        return best

    @classmethod
    def on_light_clicked(cls, pick_result: Optional[tuple[str, int]], viewport, click_pos=None):
        if pick_result is None:
            cls.set_selected_index(None, viewport)
            if cls._active_hud:
                cls._active_hud.close()
                cls._active_hud = None
            return

        action, idx = pick_result
        cls.set_selected_index(idx, viewport)

        if action == "target":
            # Clicou diretamente no alvo de mira do Spot: ativa a ferramenta de mirar imediatamente
            tool = AimLightTool(idx, on_aimed=lambda: viewport.update())
            viewport.set_active_tool(tool)
            return

        if action in ("bulb", "led_p1", "led_p2"):
            # O Gizmo 3D e o destaque são ativados automaticamente na cena
            viewport.update()


    @classmethod
    def draw_trazomob_lights(cls, viewport, painter) -> None:
        """Desenha a representação 3D das luzes, fita LED e cones/mira de spots."""
        active_tool = getattr(viewport, "active_tool", None) or getattr(viewport, "_active_tool", None)
        lights = _get_document_lights(viewport)
        has_strip_preview = isinstance(active_tool, InsertLedStripTool) and active_tool.p1 is not None
        if not lights and not has_strip_preview:
            return

        painter.setRenderHint(QPainter.Antialiasing)
        occ_ctx = _build_light_occluder_context(viewport, require_camera=True)

        if has_strip_preview:
            p1_w = active_tool.p1
            p2_w = active_tool.p2_hover or active_tool.p1
            preview_segs = cls.clip_visible_led_segments(
                viewport,
                p1_w,
                p2_w,
                normal_hint=getattr(active_tool, "normal", None),
                _ctx=occ_ctx,
            )
            for seg_a, seg_b, a_is_p1, b_is_p2 in preview_segs:
                a_px = viewport.world_to_pixel(seg_a)
                b_px = viewport.world_to_pixel(seg_b)
                if a_px is None or b_px is None:
                    continue
                pt_a = QPointF(a_px[0], a_px[1])
                pt_b = QPointF(b_px[0], b_px[1])
                painter.setPen(QPen(QColor(255, 225, 90, 230), 3.0, Qt.DashLine, Qt.RoundCap))
                painter.drawLine(pt_a, pt_b)
                painter.setPen(QPen(QColor(20, 20, 20), 1.5))
                painter.setBrush(QColor(255, 225, 90))
                if a_is_p1:
                    painter.drawEllipse(pt_a, 5.0, 5.0)
                if b_is_p2:
                    painter.drawEllipse(pt_b, 4.5, 4.5)
        if not lights:
            return

        sel_idx = cls._selected_light_idx
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)

        for i, lt in enumerate(lights):
            kind = lt.get("kind", "point")
            is_on = lt.get("on", True)
            color_rgb = lt.get("color", [1.0, 0.9, 0.8])
            tint = QColor.fromRgbF(*color_rgb) if is_on else QColor(140, 140, 140)
            is_selected = (i == sel_idx)

            # ── 1. DESENHO DE FITA LED LINEAR ──
            if kind == "led_strip" and "p1" in lt and "p2" in lt:
                vec_p1 = QVector3D(*lt["p1"])
                vec_p2 = QVector3D(*lt["p2"])
                d_raw = lt.get("dir")
                n_hint = QVector3D(*d_raw) if isinstance(d_raw, (list, tuple)) and len(d_raw) >= 3 else None
                visible_segs = cls.clip_visible_led_segments(
                    viewport,
                    vec_p1,
                    vec_p2,
                    normal_hint=n_hint,
                    _ctx=occ_ctx,
                )
                if not visible_segs:
                    continue

                glow_col = QColor(tint)
                glow_col.setAlpha(60 if is_on else 20)
                drawn_pts: list[tuple[QPointF, QPointF]] = []

                for seg_a, seg_b, a_is_p1, b_is_p2 in visible_segs:
                    a_px = viewport.world_to_pixel(seg_a)
                    b_px = viewport.world_to_pixel(seg_b)
                    if a_px is None or b_px is None:
                        continue
                    pt_a = QPointF(a_px[0], a_px[1])
                    pt_b = QPointF(b_px[0], b_px[1])
                    drawn_pts.append((pt_a, pt_b))

                    # Brilho / Halo exterior somente nos trechos visíveis
                    painter.setPen(QPen(glow_col, 8.0, Qt.SolidLine, Qt.RoundCap))
                    painter.drawLine(pt_a, pt_b)

                    # Linha do perfil de alumínio com LED
                    painter.setPen(QPen(tint, 3.5, Qt.SolidLine, Qt.RoundCap))
                    painter.drawLine(pt_a, pt_b)

                    # Nós apenas nas pontas reais P1 / P2 quando desobstruídas
                    if a_is_p1:
                        painter.setPen(QPen(QColor(30, 30, 30), 1.5))
                        painter.setBrush(tint)
                        painter.drawEllipse(pt_a, 4.0, 4.0)
                    if b_is_p2:
                        painter.setPen(QPen(QColor(30, 30, 30), 1.5))
                        painter.setBrush(tint)
                        painter.drawEllipse(pt_b, 4.0, 4.0)

                # Se selecionada e ao menos parcialmente visível: anel azul de seleção
                if is_selected and drawn_pts:
                    mid_seg = drawn_pts[len(drawn_pts) // 2]
                    mid_px = QPointF(
                        (mid_seg[0].x() + mid_seg[1].x()) * 0.5,
                        (mid_seg[0].y() + mid_seg[1].y()) * 0.5,
                    )
                    painter.setPen(QPen(QColor(2, 132, 199), 2.0, Qt.DashLine))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawEllipse(mid_px, 12.0, 12.0)
                    painter.setPen(QPen(QColor(240, 240, 240)))
                    l_mm = lt.get("length", 1.0) * 1000.0
                    painter.drawText(mid_px + QPointF(14, 4), f"Fita LED {l_mm:.0f}mm ({int(lt.get('power', 350))}W)")
                continue

            # ── 2. DESENHO DE SPOT COM CONE E PONTO FOCAL ──
            pos = lt.get("pos")
            if not pos:
                continue
            vec_pos = QVector3D(*pos)
            # Luzes obstruídas por móveis ou paredes não são desenhadas na tela
            if not cls.is_point_visible(viewport, vec_pos, _ctx=occ_ctx):
                continue

            pos_px = viewport.world_to_pixel(vec_pos)
            if pos_px is None:
                continue
            c = QPointF(pos_px[0], pos_px[1])

            if kind == "spot":
                # Alvo de mira (Target)
                t_pos = lt.get("target")
                if not t_pos:
                    d = lt.get("dir", [0.0, 0.0, -1.0])
                    t_pos = [pos[0] + d[0] * 1.5, pos[1] + d[1] * 1.5, pos[2] + d[2] * 1.5]

                t_px = viewport.world_to_pixel(QVector3D(*t_pos))
                if t_px is not None:
                    target_pt = QPointF(t_px[0], t_px[1])

                    # Eixo central de mira (Linha pontilhada)
                    pen_axis = QPen(tint.lighter(120), 1.6, Qt.DashLine)
                    painter.setPen(pen_axis)
                    painter.drawLine(c, target_pt)

                    # Cone lateral do facho de luz (abertura angular)
                    ang_deg = float(lt.get("angle", 45.0))
                    rad = math.radians(ang_deg / 2.0)
                    dist_3d = math.hypot(t_pos[0] - pos[0], t_pos[1] - pos[1], t_pos[2] - pos[2]) or 1.5
                    cone_r = dist_3d * math.tan(rad)

                    # Alvo Focal (Target Gizmo 🎯)
                    painter.setBrush(Qt.NoBrush)
                    pen_target = QPen(QColor(2, 132, 199) if is_selected else tint.lighter(130), 2.0)
                    painter.setPen(pen_target)
                    painter.drawEllipse(target_pt, 8.0, 8.0)
                    painter.drawEllipse(target_pt, 3.0, 3.0)
                    painter.drawLine(QPointF(target_pt.x() - 12, target_pt.y()), QPointF(target_pt.x() + 12, target_pt.y()))
                    painter.drawLine(QPointF(target_pt.x(), target_pt.y() - 12), QPointF(target_pt.x(), target_pt.y() + 12))

                    if is_selected:
                        painter.setPen(QPen(QColor(240, 240, 240)))
                        painter.drawText(target_pt + QPointF(14, 4), "🎯 Ponto Focal (Mirar)")

            # ── 3. BULBO PRINCIPAL ──
            # Se selecionado ou hover, desenha auréola brilhante ao redor
            if is_selected:
                painter.setBrush(QBrush(QColor(0, 212, 255, 50)))
                painter.setPen(QPen(QColor(0, 212, 255, 180), 1.5, Qt.DashLine))
                painter.drawEllipse(c, 24.0, 24.0)

            # Bulbo sólido com contorno nítido
            painter.setPen(QPen(QColor(20, 20, 20), 1.8))
            painter.setBrush(tint)
            painter.drawEllipse(c, 9.0, 9.0)

            # Raios solares / filamentos da lâmpada
            painter.setPen(QPen(tint.darker(140), 1.6))
            for k in range(8):
                a = k * math.pi / 4
                painter.drawLine(
                    QPointF(c.x() + 11.0 * math.cos(a), c.y() + 11.0 * math.sin(a)),
                    QPointF(c.x() + 16.0 * math.cos(a), c.y() + 16.0 * math.sin(a)),
                )

            # Rótulo e anel sutil de identificação da luz quando selecionada
            if is_selected and pos:
                name_lbl = lt.get("name") or ("Spot" if kind == "spot" else "Luz")
                painter.setPen(QPen(QColor(255, 255, 255)))
                painter.drawText(c + QPointF(16, -10), f"💡 {name_lbl} ({int(lt.get('power', 400))}W)")

