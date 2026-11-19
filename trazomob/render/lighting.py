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
from typing import Optional, List, Dict, Any

from PySide6.QtCore import Qt, QPointF, QSize
from PySide6.QtGui import (
    QColor, QPixmap, QPainter, QBrush, QPen, QFont, QIcon, QVector3D
)
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QSlider, QSpinBox, QDoubleSpinBox,
    QComboBox, QFrame, QGroupBox, QMessageBox, QSplitter, QWidget
)

from core.group import Group
from core.history import Command
from core.mesh import Mesh
from core.render_blender import (
    kelvin_to_rgb, aim_from_angles, angles_from_aim,
    MIN_KELVIN, MAX_KELVIN, DEFAULT_KELVIN
)
from tools.base import Tool, ToolContext
from ..integrations import platform as host


logger = logging.getLogger("trazomob.light_tools")

try:
    from core.snap import POINT_SNAP_KINDS as _POINT_SNAP_KINDS
except Exception:
    _POINT_SNAP_KINDS = frozenset({
        "endpoint", "midpoint", "intersection", "intersection_edge",
        "intersection_face", "on_edge", "on_line", "close",
        "origin", "center", "centre", "component_origin", "arc_midpoint",
    })

_TRAZOMOB_LIGHT_KINDS = ("point", "spot", "led_strip")
_TRAZOMOB_EXTRA_KEYS = ("p1", "p2", "length", "profile_w", "target", "ies_path", "blend", "double_sided")


def _clean_trazomob_lights(raw) -> list[dict]:
    """Valida luzes do TrazoMob preservando tipos e campos específicos (ex.: Fita LED)."""
    out: list[dict] = []
    for lt in raw if isinstance(raw, list) else []:
        if not isinstance(lt, dict):
            continue
        kind = lt.get("kind", "point")
        if kind not in _TRAZOMOB_LIGHT_KINDS:
            continue
        try:
            pos_src = lt.get("pos")
            if pos_src is None and kind == "led_strip" and "p1" in lt and "p2" in lt:
                p1_raw = [float(v) for v in lt["p1"][:3]]
                p2_raw = [float(v) for v in lt["p2"][:3]]
                if len(p1_raw) == 3 and len(p2_raw) == 3:
                    pos_src = [(p1_raw[i] + p2_raw[i]) * 0.5 for i in range(3)]
            pos = [float(v) for v in pos_src][:3]
            d = [float(v) for v in lt.get("dir", (0.0, 0.0, -1.0))][:3]
            default_pwr = 350.0 if kind == "led_strip" else (450.0 if kind == "spot" else 600.0)
            power = float(lt.get("power", default_pwr))
            angle = float(lt.get("angle", 120.0 if kind == "led_strip" else 60.0))
        except (AttributeError, KeyError, TypeError, ValueError):
            continue
        if len(pos) != 3 or len(d) != 3 or not all(math.isfinite(v) for v in pos + d):
            continue
        if math.hypot(*d) < 1e-9:
            d = [0.0, 0.0, -1.0]

        kelvin = lt.get("kelvin")
        color = lt.get("color")
        rgb = None
        try:
            if kelvin is not None:
                kelvin = int(max(MIN_KELVIN, min(MAX_KELVIN, float(kelvin))))
            elif isinstance(color, str) or color is None:
                kelvin = DEFAULT_KELVIN
            else:
                rgb = tuple(max(0.0, min(1.0, float(c))) for c in color[:3])
                if len(rgb) != 3:
                    rgb, kelvin = None, DEFAULT_KELVIN
        except (TypeError, ValueError):
            rgb, kelvin = None, DEFAULT_KELVIN
        if rgb is None:
            rgb = kelvin_to_rgb(kelvin)

        item = {
            "kind": kind,
            "pos": pos,
            "dir": d,
            "kelvin": kelvin if kelvin is not None else DEFAULT_KELVIN,
            "color": list(rgb),
            "power": max(0.0, min(power, 1e6)),
            "angle": max(1.0, min(angle, 179.0 if kind != "led_strip" else 180.0)),
            "on": bool(lt.get("on", True)),
            "name": str(lt.get("name", "")),
        }
        for key in _TRAZOMOB_EXTRA_KEYS:
            if key in lt and lt[key] is not None:
                val = lt[key]
                if isinstance(val, (list, tuple)):
                    try:
                        nums = [float(x) for x in val[:3]]
                        if len(nums) == 3 and all(math.isfinite(x) for x in nums):
                            item[key] = nums
                    except (TypeError, ValueError):
                        continue
                elif key in ("length", "blend"):
                    try:
                        fval = float(val)
                        if math.isfinite(fval):
                            item[key] = fval
                    except (TypeError, ValueError):
                        continue
                else:
                    item[key] = val
        out.append(item)
    return out


# ── Presets Prontos de Iluminação Residencial / Marcenaria ─────────────
LIGHT_PRESETS = {
    "spot_quente": {
        "name": "Spot Direcional Aconchegante (2700K)",
        "kind": "spot",
        "power": 450.0,
        "kelvin": 2700,
        "angle": 45.0,
        "dir": [0.0, 0.0, -1.0],
    },
    "spot_neutro": {
        "name": "Spot Direcional Neutro (4000K)",
        "kind": "spot",
        "power": 600.0,
        "kelvin": 4000,
        "angle": 60.0,
        "dir": [0.0, 0.0, -1.0],
    },
    "fita_led": {
        "name": "Fita LED Marcenaria (3000K Suave)",
        "kind": "led_strip",
        "power": 350.0,
        "kelvin": 3000,
        "angle": 120.0,
        "dir": [0.0, 0.0, -1.0],
    },
    "omni": {
        "name": "Luz Omni 360° / Lâmpada (2700K)",
        "kind": "point",
        "power": 600.0,
        "kelvin": 2700,
        "angle": 360.0,
        "dir": [0.0, 0.0, -1.0],
    },
    "plafon_geral": {
        "name": "Luz Geral Focada Para Baixo (3500K)",
        "kind": "spot",
        "power": 1200.0,
        "kelvin": 3500,
        "angle": 140.0,
        "dir": [0.0, 0.0, -1.0],
    },
}


# ── Gerador de Malha 3D Real para Luzes (Apenas o elemento luminoso) ───────────
def create_light_mesh(light_data: dict) -> Mesh:
    """Gera apenas o elemento emissor de luz puro (sem carcaças ou acessórios volumosos)."""
    kind = light_data.get("kind", "point")
    color_rgb = light_data.get("color", [1.0, 0.95, 0.85])
    mesh = Mesh()

    if kind == "led_strip" and "p1" in light_data and "p2" in light_data:
        # Fita LED Linear em coordenadas locais ao redor de ``origin``:
        # ``create_light_scene_group`` aplica a translação única por ``pos``.
        p1_world = QVector3D(*light_data["p1"])
        p2_world = QVector3D(*light_data["p2"])
        raw_pos = light_data.get("pos")
        origin = QVector3D(*raw_pos) if raw_pos is not None else (p1_world + p2_world) * 0.5
        p1 = p1_world - origin
        p2 = p2_world - origin
        vec = p2 - p1
        length = vec.length()
        if length < 1e-4:
            vec = QVector3D(1, 0, 0)
        u = vec.normalized()
        raw_dir = light_data.get("dir", [0.0, 0.0, -1.0])
        try:
            emit = QVector3D(float(raw_dir[0]), float(raw_dir[1]), float(raw_dir[2]))
        except Exception:
            emit = QVector3D(0.0, 0.0, -1.0)
        emit = emit - u * QVector3D.dotProduct(emit, u)
        if emit.length() < 1e-4:
            ref = QVector3D(0.0, 0.0, -1.0) if abs(u.z()) < 0.9 else QVector3D(0.0, -1.0, 0.0)
            emit = ref - u * QVector3D.dotProduct(ref, u)
        emit = emit.normalized()
        up = -emit
        n = QVector3D.crossProduct(u, up).normalized()

        w_half = 0.006   # 12mm de largura total
        h_half = 0.0025  # 5mm de espessura para nao vazar chapas de 15/18mm

        c00 = p1 - n * w_half - up * h_half
        c01 = p1 + n * w_half - up * h_half
        c02 = p1 + n * w_half + up * h_half
        c03 = p1 - n * w_half + up * h_half

        c10 = p2 - n * w_half - up * h_half
        c11 = p2 + n * w_half - up * h_half
        c12 = p2 + n * w_half + up * h_half
        c13 = p2 - n * w_half + up * h_half

        box_faces = [
            ([c00, c01, c11, c10], None),   # Inferior (-Z / emissão)
            ([c03, c13, c12, c02], None),   # Superior (+Z)
            ([c00, c10, c13, c03], None),   # Lateral 1
            ([c01, c02, c12, c11], None),   # Lateral 2
            ([c00, c03, c02, c01], "p1"),   # Tampa p1
            ([c10, c11, c12, c13], "p2"),   # Tampa p2
        ]
        for pts, cap_tag in box_faces:
            f = mesh.add_face(pts)
            f.attrs["color"] = (color_rgb[0], color_rgb[1], color_rgb[2])
            f.attrs["mat"] = "Fita LED Emissora"
            if cap_tag is not None:
                f.attrs["led_cap"] = cap_tag
    else:
        # Ponto de luz ou Spot: volume 3D convexo fechado (cilindro/prisma octogonal emissivo de 10cm x 4cm)
        # Sendo 3D fechado, é instantaneamente clicável de QUALQUER ângulo da câmera e tem pontos de snap para M (Move)
        r = 0.050       # 100mm de diâmetro (área de clique confortável)
        h_half = 0.020  # 40mm de espessura (20mm para cima e 20mm para baixo do ponto central)
        n_seg = 12

        bot_pts = []
        top_pts = []
        for s in range(n_seg):
            ang = s * 2.0 * math.pi / n_seg
            x = math.cos(ang) * r
            y = math.sin(ang) * r
            bot_pts.append(QVector3D(x, y, -h_half))
            top_pts.append(QVector3D(x, y, h_half))

        # Face inferior (-Z): emissão principal para baixo
        f_bot = mesh.add_face(list(reversed(bot_pts)))
        f_bot.attrs["color"] = (color_rgb[0], color_rgb[1], color_rgb[2])
        f_bot.attrs["mat"] = "Fonte de Luz"

        # Face superior (+Z): fechamento superior para colisão do mouse visto de cima
        f_top = mesh.add_face(top_pts)
        f_top.attrs["color"] = (color_rgb[0], color_rgb[1], color_rgb[2])
        f_top.attrs["mat"] = "Fonte de Luz"

        # Faces laterais: colisão e pega para quando visto de lado / rasante
        for s in range(n_seg):
            nxt = (s + 1) % n_seg
            side_pts = [bot_pts[s], bot_pts[nxt], top_pts[nxt], top_pts[s]]
            f_side = mesh.add_face(side_pts)
            f_side.attrs["color"] = (color_rgb[0], color_rgb[1], color_rgb[2])
            f_side.attrs["mat"] = "Fonte de Luz"

    return mesh


def create_light_scene_group(light_data: dict, index: int = 0) -> Group:
    """Cria um Group nativo atômico da luz na coordenada correta."""
    data = dict(light_data)
    kind = data.get("kind", "point")
    data.setdefault("dir", [0.0, 0.0, -1.0])
    if kind != "led_strip" and (
        data.get("dir") == [0.0, 0.0, 1.0] or data.get("dir", [0, 0, -1])[2] > -0.1
    ):
        data["dir"] = [0.0, 0.0, -1.0]

    pos = data.get("pos")
    if pos is None and kind == "led_strip" and "p1" in data and "p2" in data:
        p1_raw, p2_raw = data["p1"], data["p2"]
        pos = [
            (float(p1_raw[0]) + float(p2_raw[0])) * 0.5,
            (float(p1_raw[1]) + float(p2_raw[1])) * 0.5,
            (float(p1_raw[2]) + float(p2_raw[2])) * 0.5,
        ]
        data["pos"] = pos
    if pos is None:
        pos = [0.0, 0.0, 0.0]

    mesh = create_light_mesh(data)
    name = data.get("name") or f"Luz #{index + 1}"
    grp = Group(mesh, name=f"💡 {name}")
    grp.ext = {"trazomob_light": dict(data), "atomic_light": True}

    # Posiciona a malha na coordenada real da luz (uma única translação por pos)
    p_vec = QVector3D(*pos)
    from PySide6.QtGui import QMatrix4x4
    from core.group import carry_axes
    m_tr = QMatrix4x4()
    m_tr.translate(p_vec)
    for v in mesh.vertices:
        v.position = m_tr.map(v.position)
    mesh._chunk_dirty = True
    mesh._mut_serial = getattr(mesh, "_mut_serial", 0) + 1
    carry_axes(grp, m_tr)
    return grp


def _translate_light_scene_group(viewport, light_index: int, delta_vec: QVector3D, updated_lt: Optional[dict] = None) -> None:
    """Mantém o Group 3D da luz sincronizado ao mover ou ajustar Z via ferramenta/diálogo."""
    scene = getattr(viewport, "scene", None)
    if scene is None:
        return
    light_groups = [
        g for g in getattr(scene, "groups", [])
        if isinstance(getattr(g, "ext", None), dict) and "trazomob_light" in g.ext
    ]
    if not (0 <= light_index < len(light_groups)):
        return
    grp = light_groups[light_index]
    if updated_lt is not None:
        grp.ext["trazomob_light"] = dict(updated_lt)
    if delta_vec.lengthSquared() > 1e-12:
        from PySide6.QtGui import QMatrix4x4
        from core.group import carry_axes
        m_tr = QMatrix4x4()
        m_tr.translate(delta_vec)
        if getattr(grp, "xform", None) is not None:
            grp.xform = m_tr * grp.xform
        else:
            mesh = getattr(grp, "mesh", None)
            if mesh is not None and hasattr(mesh, "vertices"):
                for v in mesh.vertices:
                    v.position = v.position + delta_vec
                mesh._chunk_dirty = True
                mesh._mut_serial = getattr(mesh, "_mut_serial", 0) + 1
            carry_axes(grp, m_tr)
        scene.version += 1


def sync_scene_lights_to_document(viewport) -> None:
    """Coleta todos os grupos de luminárias da cena 3D e atualiza a lista de luzes do documento."""
    scene = getattr(viewport, "scene", None)
    if not scene:
        return
    scene_lights = []
    for g in getattr(scene, "groups", []):
        ext = getattr(g, "ext", None)
        if isinstance(ext, dict) and "trazomob_light" in ext:
            lt = dict(ext["trazomob_light"])
            _sync_light_dict_with_group(lt, g)
            scene_lights.append(lt)

    # Sincroniza sempre com o documento (mesmo vazia após deleção de luzes)
    _save_document_lights(viewport, scene_lights)


def _extract_led_strip_endpoints_from_group(grp, lt: dict) -> Optional[tuple[QVector3D, QVector3D]]:
    """Extrai as extremidades mundiais ``(p1, p2)`` da malha 3D de uma fita LED."""
    if lt.get("kind") != "led_strip" or "p1" not in lt or "p2" not in lt:
        return None
    old_p1 = QVector3D(*lt["p1"])
    old_p2 = QVector3D(*lt["p2"])
    old_vec = old_p2 - old_p1
    old_u = old_vec.normalized() if old_vec.length() > 1e-6 else QVector3D(1.0, 0.0, 0.0)

    mesh = getattr(grp, "mesh", None)
    xform = getattr(grp, "xform", None)

    def _to_world(pt: QVector3D) -> QVector3D:
        return xform.map(pt) if xform is not None else QVector3D(pt)

    def _face_centroid(face) -> Optional[QVector3D]:
        verts = getattr(face, "vertices", None)
        if not verts:
            return None
        acc = QVector3D(0.0, 0.0, 0.0)
        for v in verts:
            pos_v = v.position if hasattr(v, "position") else v
            acc += _to_world(pos_v)
        return acc / float(len(verts))

    faces = list(getattr(mesh, "faces", ()) or ()) if mesh is not None else []
    if faces:
        cap_p1 = [f for f in faces if getattr(f, "attrs", {}).get("led_cap") == "p1"]
        cap_p2 = [f for f in faces if getattr(f, "attrs", {}).get("led_cap") == "p2"]
        if len(cap_p1) == 1 and len(cap_p2) == 1:
            c1, c2 = _face_centroid(cap_p1[0]), _face_centroid(cap_p2[0])
            if c1 is not None and c2 is not None:
                return c1, c2

        if len(faces) == 6:
            c1, c2 = _face_centroid(faces[4]), _face_centroid(faces[5])
            if c1 is not None and c2 is not None and (c2 - c1).length() > 1e-4:
                return c1, c2

    verts = list(getattr(mesh, "vertices", ()) or ()) if mesh is not None else []
    if verts:
        world_pts = [_to_world(v.position) for v in verts]
        projs = [QVector3D.dotProduct(p, old_u) for p in world_pts]
        t_min, t_max = min(projs), max(projs)
        lo_pts = [p for p, t in zip(world_pts, projs) if t <= t_min + 1e-3]
        hi_pts = [p for p, t in zip(world_pts, projs) if t >= t_max - 1e-3]
        if lo_pts and hi_pts:
            c1 = sum(lo_pts[1:], QVector3D(lo_pts[0])) / float(len(lo_pts))
            c2 = sum(hi_pts[1:], QVector3D(hi_pts[0])) / float(len(hi_pts))
            return c1, c2

    return None


def _sync_light_dict_with_group(lt: dict, grp, _changed_out: Optional[list[bool]] = None) -> dict:
    """Atualiza ``pos``, ``target``, ``p1``, ``p2`` e ``length`` conforme a geometria atual do grupo 3D."""
    ext = getattr(grp, "ext", None)
    if lt.get("kind") == "led_strip" and "p1" in lt and "p2" in lt:
        endpoints = _extract_led_strip_endpoints_from_group(grp, lt)
        if endpoints is not None:
            new_p1, new_p2 = endpoints
            new_mid = (new_p1 + new_p2) * 0.5
            new_len = float((new_p2 - new_p1).length())
            old_p1 = QVector3D(*lt["p1"])
            old_p2 = QVector3D(*lt["p2"])
            old_pos = QVector3D(*lt["pos"]) if "pos" in lt else new_mid
            old_len = float(lt.get("length", (old_p2 - old_p1).length()))
            if (
                (new_p1 - old_p1).length() > 1e-4
                or (new_p2 - old_p2).length() > 1e-4
                or (new_mid - old_pos).length() > 1e-4
                or abs(new_len - old_len) > 1e-4
                or "pos" not in lt
            ):
                lt["p1"] = [round(new_p1.x(), 4), round(new_p1.y(), 4), round(new_p1.z(), 4)]
                lt["p2"] = [round(new_p2.x(), 4), round(new_p2.y(), 4), round(new_p2.z(), 4)]
                lt["pos"] = [round(new_mid.x(), 4), round(new_mid.y(), 4), round(new_mid.z(), 4)]
                lt["length"] = round(new_len, 4)
                if isinstance(ext, dict):
                    ext["trazomob_light"] = lt
                if _changed_out is not None:
                    _changed_out[0] = True
            return lt

    bounds = None
    try:
        from ..interaction.magnetic_drag import get_module_bounds
        bounds = get_module_bounds(grp)
    except Exception as exc:
        logger.debug("bounds da luz indisponíveis: %s", exc)
    if bounds:
        cx = (bounds[0] + bounds[1]) * 0.5
        cy = (bounds[2] + bounds[3]) * 0.5
        cz = (bounds[4] + bounds[5]) * 0.5
        old_pos = lt.get("pos", [cx, cy, cz])
        dx, dy, dz = cx - old_pos[0], cy - old_pos[1], cz - old_pos[2]
        if abs(dx) > 1e-4 or abs(dy) > 1e-4 or abs(dz) > 1e-4 or "pos" not in lt:
            lt["pos"] = [round(cx, 4), round(cy, 4), round(cz, 4)]
            if lt.get("kind") == "spot" and lt.get("target"):
                lt["target"] = [
                    round(lt["target"][0] + dx, 4),
                    round(lt["target"][1] + dy, 4),
                    round(lt["target"][2] + dz, 4),
                ]
            if lt.get("kind") == "led_strip" and "p1" in lt and "p2" in lt:
                lt["p1"] = [round(lt["p1"][0] + dx, 4), round(lt["p1"][1] + dy, 4), round(lt["p1"][2] + dz, 4)]
                lt["p2"] = [round(lt["p2"][0] + dx, 4), round(lt["p2"][1] + dy, 4), round(lt["p2"][2] + dz, 4)]
            if isinstance(ext, dict):
                ext["trazomob_light"] = lt
            if _changed_out is not None:
                _changed_out[0] = True
    return lt


def _get_scene_lights(scene) -> list[dict]:
    """Coleta todas as luzes diretamente da cena (grupos 3D ou ``plugin_data``)."""
    if scene is not None:
        scene_lights = []
        changed = [False]
        for g in getattr(scene, "groups", ()) or ():
            ext = getattr(g, "ext", None)
            if isinstance(ext, dict) and isinstance(ext.get("trazomob_light"), dict):
                scene_lights.append(_sync_light_dict_with_group(ext["trazomob_light"], g, changed))
        if scene_lights:
            if changed[0]:
                plugin_data = getattr(scene, "plugin_data", None)
                if isinstance(plugin_data, dict):
                    rb = plugin_data.get("render_blender")
                    if isinstance(rb, dict):
                        rb["lights"] = _clean_trazomob_lights(scene_lights)
            return scene_lights

        plugin_data = getattr(scene, "plugin_data", None)
        if isinstance(plugin_data, dict):
            rb = plugin_data.get("render_blender")
            if isinstance(rb, dict) and rb.get("lights"):
                return _clean_trazomob_lights(rb.get("lights", []))
    return []


def _lights_app(viewport):
    """Handle on the native Render plugin's document data (key 'render_blender'),
    so the lights are shared with IngeTrazo's viewport bulbs and its render."""
    from views.extension_api import ExtensionApp
    return ExtensionApp(viewport.window(), "render_blender")


def _get_document_lights(viewport) -> list[dict]:
    """Recupera a lista de luzes combinando grupos 3D da cena e dados do documento."""
    scene_lights = _get_scene_lights(getattr(viewport, "scene", None))
    if scene_lights:
        return scene_lights

    raw = _lights_app(viewport).document_data({}) or {}
    if not isinstance(raw, dict):
        raw = {}
    return _clean_trazomob_lights(raw.get("lights", []))


def _build_document_payload(viewport, lights: list[dict]):
    """Monta o ``render_blender`` que representa ``lights``, ou ``None`` se
    nada mudou (para não empilhar um passo de Undo vazio)."""
    scene = getattr(viewport, "scene", None)
    if not scene:
        return None
    data = getattr(scene, "plugin_data", None)
    if data is None:
        scene.plugin_data = {}
        data = scene.plugin_data

    raw = data.get("render_blender", {}) or {}
    if not isinstance(raw, dict):
        raw = {}
    cleaned = _clean_trazomob_lights(lights)
    if raw.get("lights") == cleaned:
        return None

    raw.setdefault("ambience", "night")
    raw.setdefault("sun_scale", 1.0)
    raw["lights"] = cleaned
    return raw


def _save_document_lights(viewport, lights: list[dict], undoable: bool = False) -> None:
    """Salva as luzes no documento.

    ``undoable=False`` (padrão) grava direto no ``plugin_data``: é o caminho
    das sincronizações que acompanham uma mudança de cena já registrada no
    histórico, e não deve criar um segundo passo de Undo. ``undoable=True``
    registra a mudança como um passo próprio — use quando a edição da luz é a
    única alteração (mover, mirar, apagar).
    """
    import json
    scene = getattr(viewport, "scene", None)
    if not scene:
        return
    raw = _build_document_payload(viewport, lights)
    if raw is None:
        return

    if undoable:
        app = _lights_app(viewport)
        app.set_document_data(raw)
    else:
        # Grava diretamente no plugin_data sem poluir a pilha do Ctrl+Z
        data = getattr(scene, "plugin_data", None)
        if data is None:
            scene.plugin_data = {}
            data = scene.plugin_data
        data["render_blender"] = json.loads(json.dumps(raw))
        viewport.update()


class _CompositeCommand(Command):
    """Duas operações como UM passo de Undo.

    Uma luz tem duas metades — o grupo 3D na cena e o registro em
    ``plugin_data['render_blender']``. Registradas separadamente, um único
    Ctrl+Z desfazia só uma delas e deixava o documento inconsistente.
    """

    def __init__(self, *commands) -> None:
        self._commands = [c for c in commands if c is not None]

    def do(self, scene) -> None:
        for cmd in self._commands:
            cmd.do(scene)

    def undo(self, scene) -> None:
        for cmd in reversed(self._commands):
            cmd.undo(scene)


def _apply_light_change(viewport, mutate_scene, lights: list[dict]) -> None:
    """Aplica a mudança de cena e a lista de luzes do documento como um passo."""
    from core.history import SetPluginDataCommand, SnapshotImport

    payload = _build_document_payload(viewport, lights)
    scene = getattr(viewport, "scene", None)
    history = getattr(viewport, "history", None)

    if scene is None or history is None:
        if mutate_scene is not None and scene is not None:
            mutate_scene(scene)
        _save_document_lights(viewport, lights)
        return

    commands = []
    if mutate_scene is not None:
        commands.append(SnapshotImport(mutate_scene))
    if payload is not None:
        commands.append(SetPluginDataCommand("render_blender", payload))
    if commands:
        history.execute(_CompositeCommand(*commands))
        notify = getattr(viewport, "notify_scene_changed", None)
        if callable(notify):
            notify()
    viewport.update()


def _lights_from_any_window() -> list[dict]:
    from PySide6.QtWidgets import QApplication
    for w in QApplication.topLevelWidgets():
        vp = getattr(w, "viewport", None)
        if vp is not None and hasattr(vp, "scene"):
            return _get_document_lights(vp)
    return []


def _flash(viewport, msg: str) -> None:
    fn = getattr(viewport, "flash_status", None)
    if callable(fn):
        fn(msg)


def _surface_hit(ctx):
    """World point ON the surface under the cursor plus its normal.

    A free cursor point or soft axis/alignment inference lies on the camera or
    ground work plane (e.g. Z=0), causing a 2-point LED strip to land far away
    from the clicked cabinet/wall face. Real model point snaps (endpoint,
    midpoint, intersection, on_edge) within 0.25m of the ray-face hit are kept;
    otherwise the camera ray intersection on the face plane under the cursor
    is returned."""
    vp = ctx.viewport
    kind = getattr(ctx.snap, "kind", None) if ctx.snap is not None else None
    is_point_snap = kind in _POINT_SNAP_KINDS
    x, y = ctx.screen.x(), ctx.screen.y()
    face, grp = (None, None)
    pick = getattr(vp, "pick_face_placement", None) or getattr(vp, "pick_face_any", None)
    if callable(pick):
        face, grp = pick(x, y)
    normal = None
    if face is not None:
        from core.snap import face_plane_world
        pt, n = face_plane_world(face, getattr(grp, "xform", None))
        if n.length() > 1e-9:
            normal = n.normalized()
            origin, direction = vp._pixel_to_ray(x, y)
            if origin is not None:
                hit = vp._ray_plane(origin, direction, pt, normal)
                if hit is not None:
                    # Face normal pointing back at the camera (the room side)
                    if QVector3D.dotProduct(normal, direction) > 0:
                        normal = -normal
                    if is_point_snap and ctx.world is not None:
                        snap_pt = QVector3D(ctx.world)
                        if (snap_pt - hit).length() <= 0.25:
                            return snap_pt, normal
                    return hit, normal
    model_pt_fn = getattr(vp, "_model_point_at", None)
    if callable(model_pt_fn):
        try:
            mp = model_pt_fn(x, y)
            if mp is not None:
                return QVector3D(mp), normal
        except Exception:
            pass
    if is_point_snap and ctx.world is not None:
        return QVector3D(ctx.world), normal
    return None, None


class InsertLightTool(Tool):
    """Ferramenta interativa para posicionar luzes com o clique do mouse."""

    name = "Inserir Luz"
    shortcut = None
    uses_snap = True
    description = "Clique sobre o teto, móvel ou parede para posicionar a luz."

    def __init__(self, light_data: dict, on_placed=None):
        super().__init__()
        self.light_data = dict(light_data)
        self.on_placed = on_placed
        self.hover_point: Optional[QVector3D] = None

    def on_activate(self, viewport) -> None:
        self.hover_point = None
        _flash(viewport, f"💡 Clique no modelo para fixar a luz [{self.light_data.get('name', 'Luz')}]. Esc cancela.")

    def on_deactivate(self, viewport) -> None:
        self.hover_point = None
        _flash(viewport, "")

    def on_hover(self, ctx: ToolContext) -> None:
        self.hover_point = ctx.world
        ctx.viewport.update()

    def on_click(self, ctx: ToolContext) -> None:
        hit, normal = _surface_hit(ctx)
        if hit is None:
            _flash(ctx.viewport, "Clique sobre uma superfície (teto, móvel, parede) para fixar a luz.")
            return
        is_spot = self.light_data.get("kind") == "spot"
        off = 0.03 if is_spot else 0.15
        if normal is not None:
            hit = hit + normal * off
        pos = [hit.x(), hit.y(), hit.z()]
        new_light = dict(self.light_data)
        new_light["pos"] = pos
        new_light["on"] = True

        if is_spot:
            # Aponta para o chão/superfície oposta por padrão se não tiver target
            d = new_light.get("dir", [0.0, 0.0, -1.0])
            new_light["target"] = [pos[0] + d[0] * 1.5, pos[1] + d[1] * 1.5, pos[2] + d[2] * 1.5]

        # Adiciona na cena como Group nativo com malha 3D real
        lights = _get_document_lights(ctx.viewport)
        lights.append(new_light)

        # Grupo 3D + lista do documento num ÚNICO passo de Undo: um Ctrl+Z
        # desfaz a luz inteira, sem deixar o render com uma luz fantasma.
        light_grp = create_light_scene_group(new_light, len(lights) - 1)
        vp = ctx.viewport

        def _add_light_group(scene):
            scene.groups.append(light_grp)
            scene.selection = {light_grp}

        _apply_light_change(vp, _add_light_group, lights)

        _flash(ctx.viewport, f"✅ Luz inserida com sucesso em X:{pos[0]:.2f} Y:{pos[1]:.2f} Z:{pos[2]:.2f}")

        if callable(self.on_placed):
            self.on_placed(new_light)

        # Volta para a ferramenta de seleção padrão se existir
        if hasattr(ctx.viewport, "set_active_tool"):
            app = getattr(ctx.viewport, "app", None)
            if app and hasattr(app, "select_tool"):
                ctx.viewport.set_active_tool(app.select_tool)

    def on_key(self, viewport, key, modifiers) -> bool:
        if key == Qt.Key_Escape:
            cb = getattr(self, 'on_placed', None)
            if callable(cb):
                cb(None)
            return True
        return False


def _compute_led_strip_direction(
    viewport,
    p1: QVector3D,
    p2: QVector3D,
    n1: Optional[QVector3D] = None,
    n2: Optional[QVector3D] = None,
) -> list[float]:
    """Calcula um vetor de emissão unitário sempre perpendicular à fita e voltado ao espaço livre."""
    vec = p2 - p1
    if vec.length() < 1e-6:
        return [0.0, 0.0, -1.0]
    u = vec.normalized()

    def _ortho_unit(v: Optional[QVector3D]) -> Optional[QVector3D]:
        if v is None or v.length() < 1e-6:
            return None
        perp = v - u * QVector3D.dotProduct(v, u)
        if perp.length() < 1e-4:
            return None
        return perp.normalized()

    ortho_n: list[QVector3D] = []
    for n_cand in (n1, n2):
        if n_cand is None or n_cand.length() < 1e-6:
            continue
        nn = n_cand.normalized()
        if abs(QVector3D.dotProduct(nn, u)) <= 0.85:
            po = _ortho_unit(nn)
            if po is not None:
                ortho_n.append(po)

    down_ortho = _ortho_unit(QVector3D(0.0, 0.0, -1.0))
    agree_normals = (
        len(ortho_n) == 2 and QVector3D.dotProduct(ortho_n[0], ortho_n[1]) > 0.85
    )

    occ_ctx = _build_light_occluder_context(viewport, require_camera=False)
    has_ray = occ_ctx is not None or callable(getattr(viewport, "ray_distance", None))

    under_cabinet = False
    if (
        has_ray
        and agree_normals
        and down_ortho is not None
        and abs(u.z()) < 0.25
        and abs(ortho_n[0].z()) < 0.35
    ):
        probe_xy = ortho_n[0] * 0.04 + QVector3D(0.0, 0.0, -0.02)
        up_vec = QVector3D(0.0, 0.0, 1.0)
        dn_vec = QVector3D(0.0, 0.0, -1.0)
        for t_s in (0.25, 0.50, 0.75):
            probe = p1 * (1.0 - t_s) + p2 * t_s + probe_xy
            if _ray_blocked(viewport, probe, up_vec, 0.06, occ_ctx) and not _ray_blocked(
                viewport, probe, dn_vec, 0.20, occ_ctx
            ):
                under_cabinet = True
                break

    ordered: list[QVector3D] = []

    def _push(v: Optional[QVector3D]) -> None:
        if v is None:
            return
        if all(QVector3D.dotProduct(v, existing) < 0.96 for existing in ordered):
            ordered.append(v)

    if under_cabinet:
        _push(down_ortho)
    if agree_normals:
        _push(ortho_n[0])
    if abs(u.z()) < 0.5:
        _push(down_ortho)
    for po in ortho_n:
        _push(po)
    _push(down_ortho)
    for po in ortho_n:
        _push(-po)
    if down_ortho is not None:
        side = _ortho_unit(QVector3D.crossProduct(u, down_ortho))
        _push(side)
        if side is not None:
            _push(-side)
    for fallback in (QVector3D(0.0, -1.0, 0.0), QVector3D(1.0, 0.0, 0.0), QVector3D(0.0, 0.0, 1.0)):
        fo = _ortho_unit(fallback)
        _push(fo)
        if fo is not None:
            _push(-fo)

    if not ordered:
        return [0.0, 0.0, -1.0]

    if not has_ray:
        best = ordered[0]
        return [round(best.x(), 4), round(best.y(), 4), round(best.z(), 4)]

    # Testa desobstrução a partir de 3 pontos médios para evitar emissão apontada para dentro do MDF
    sample_ts = (0.25, 0.50, 0.75)
    best_cand = ordered[0]
    best_blocked = 999
    for cand in ordered:
        blocked = 0
        for t_s in sample_ts:
            orig = p1 * (1.0 - t_s) + p2 * t_s + cand * 0.002
            if _ray_blocked(viewport, orig, cand, 0.045, occ_ctx):
                blocked += 1
        if blocked == 0:
            return [round(cand.x(), 4), round(cand.y(), 4), round(cand.z(), 4)]
        if blocked < best_blocked:
            best_blocked = blocked
            best_cand = cand

    return [round(best_cand.x(), 4), round(best_cand.y(), 4), round(best_cand.z(), 4)]


class InsertLedStripTool(Tool):
    """Ferramenta interativa de 2 cliques para desenhar fita LED contínua / perfil linear sob armários."""

    name = "Inserir Fita LED"
    shortcut = None
    uses_snap = True
    description = "Clique no ponto inicial e depois no ponto final do perfil de LED."

    def __init__(self, light_data: dict, on_placed=None):
        super().__init__()
        self.light_data = dict(light_data)
        self.on_placed = on_placed
        self.p1: Optional[QVector3D] = None
        self.p2_hover: Optional[QVector3D] = None
        self.normal: Optional[QVector3D] = None
        self.work_plane = None

    @property
    def start_point(self) -> Optional[QVector3D]:
        """Expõe o primeiro clique ao motor de snap/medição do viewport."""
        return self.p1

    def on_activate(self, viewport) -> None:
        self.p1 = None
        self.p2_hover = None
        self.normal = None
        self.work_plane = None
        _flash(viewport, "✨ Fita LED (1/2): Clique no PONTO INICIAL da fita (ex: início do armário). Esc cancela.")

    def on_deactivate(self, viewport) -> None:
        self.p1 = None
        self.p2_hover = None
        self.normal = None
        self.work_plane = None
        _flash(viewport, "")

    def on_hover(self, ctx: ToolContext) -> None:
        hit, _n = _surface_hit(ctx)
        self.p2_hover = hit or ctx.world
        ctx.viewport.update()

    def on_click(self, ctx: ToolContext) -> None:
        hit, normal = _surface_hit(ctx)
        if hit is None:
            hit = ctx.world
        if hit is None:
            return

        if self.p1 is None:
            # 1º Clique: Ponto inicial
            self.p1 = QVector3D(hit)
            self.normal = normal
            self.p2_hover = QVector3D(hit)
            _flash(ctx.viewport, "✨ Fita LED (2/2): Agora clique no PONTO FINAL da fita LED.")
            ctx.viewport.update()
        else:
            # 2º Clique: Ponto final
            p2 = QVector3D(hit)
            dist = (p2 - self.p1).length()
            if dist < 0.05:
                _flash(ctx.viewport, "⚠️ O comprimento da fita LED é muito curto (mínimo 5 cm). Clique mais distante.")
                return

            mid = (self.p1 + p2) * 0.5
            pos = [mid.x(), mid.y(), mid.z()]

            new_light = dict(self.light_data)
            new_light["kind"] = "led_strip"
            new_light["pos"] = pos
            new_light["p1"] = [self.p1.x(), self.p1.y(), self.p1.z()]
            new_light["p2"] = [p2.x(), p2.y(), p2.z()]
            new_light["length"] = float(dist)
            new_light["on"] = True
            new_light["dir"] = _compute_led_strip_direction(
                ctx.viewport, self.p1, p2, self.normal, normal
            )

            # Reseta estado antes de notificar callbacks / trocar ferramenta
            self.p1 = None
            self.p2_hover = None
            self.normal = None
            self.work_plane = None

            lights = _get_document_lights(ctx.viewport)
            lights.append(new_light)

            # Grupo 3D + lista do documento num ÚNICO passo de Undo.
            light_grp = create_light_scene_group(new_light, len(lights) - 1)
            vp = ctx.viewport

            def _add_strip_group(scene):
                scene.groups.append(light_grp)
                scene.selection = {light_grp}

            _apply_light_change(vp, _add_strip_group, lights)

            _flash(ctx.viewport, f"✅ Fita LED inserida com {dist*1000:.0f}mm ({new_light.get('power', 350):.0f}W)!")

            if callable(self.on_placed):
                self.on_placed(new_light)

            # Restaura ferramenta de seleção
            if hasattr(ctx.viewport, "set_active_tool"):
                app = getattr(ctx.viewport, "app", None)
                if app and hasattr(app, "select_tool"):
                    ctx.viewport.set_active_tool(app.select_tool)

    def on_key(self, viewport, key, modifiers) -> bool:
        if key == Qt.Key_Escape:
            cb = getattr(self, 'on_placed', None)
            if callable(cb):
                cb(None)
            return True
        return False


class MoveLightTool(Tool):
    """Ferramenta para mover / reposicionar uma luz no 3D com o mouse."""

    name = "Mover Luz"
    shortcut = None
    uses_snap = True
    description = "Clique na nova superfície ou posição onde a luz deve ser fixada."

    def __init__(self, light_index: int, on_moved=None):
        super().__init__()
        self.light_index = light_index
        self.on_moved = on_moved
        self.hover_point: Optional[QVector3D] = None

    def on_activate(self, viewport) -> None:
        self.hover_point = None
        _flash(viewport, "📍 Clique no teto, móvel, parede ou posição desejada para MOVER a luz. Esc cancela.")

    def on_deactivate(self, viewport) -> None:
        self.hover_point = None
        _flash(viewport, "")

    def on_hover(self, ctx: ToolContext) -> None:
        hit, _n = _surface_hit(ctx)
        self.hover_point = hit or ctx.world
        ctx.viewport.update()

    def on_click(self, ctx: ToolContext) -> None:
        lights = _get_document_lights(ctx.viewport)
        if not (0 <= self.light_index < len(lights)):
            return

        lt = lights[self.light_index]
        kind = lt.get("kind", "point")
        hit, normal = _surface_hit(ctx)
        if hit is None:
            hit = ctx.world
        if hit is None:
            _flash(ctx.viewport, "Clique sobre o modelo ou plano de trabalho para posicionar a luz.")
            return

        off = 0.03 if kind == "spot" else 0.12
        if normal is not None:
            hit = hit + normal * off

        new_pos = [round(hit.x(), 4), round(hit.y(), 4), round(hit.z(), 4)]
        old_pos = lt.get("pos", [0, 0, 0])
        dx = new_pos[0] - old_pos[0]
        dy = new_pos[1] - old_pos[1]
        dz = new_pos[2] - old_pos[2]

        lt["pos"] = new_pos

        # Se tiver target (spot), desloca o target junto com a luminária para manter o ângulo de mira
        if "target" in lt and lt["target"]:
            t = lt["target"]
            lt["target"] = [round(t[0] + dx, 4), round(t[1] + dy, 4), round(t[2] + dz, 4)]

        # Se for fita LED (p1 e p2), desloca ambos os terminais mantendo o comprimento e orientação
        if kind == "led_strip" and "p1" in lt and "p2" in lt:
            p1 = lt["p1"]
            p2 = lt["p2"]
            lt["p1"] = [round(p1[0] + dx, 4), round(p1[1] + dy, 4), round(p1[2] + dz, 4)]
            lt["p2"] = [round(p2[0] + dx, 4), round(p2[1] + dy, 4), round(p2[2] + dz, 4)]

        _translate_light_scene_group(ctx.viewport, self.light_index, QVector3D(dx, dy, dz), lt)
        _save_document_lights(ctx.viewport, lights, undoable=True)
        _flash(ctx.viewport, f"✅ Luz movida com sucesso para X:{new_pos[0]:.2f} Y:{new_pos[1]:.2f} Z:{new_pos[2]:.2f}")

        if callable(self.on_moved):
            self.on_moved()

        if hasattr(ctx.viewport, "set_active_tool"):
            app = getattr(ctx.viewport, "app", None)
            if app and hasattr(app, "select_tool"):
                ctx.viewport.set_active_tool(app.select_tool)

    def on_key(self, viewport, key, modifiers) -> bool:
        if key == Qt.Key_Escape:
            cb = getattr(self, 'on_moved', None)
            if callable(cb):
                cb()
            return True

        # Setas Up / Down para ajuste fino de elevação Z (5cm normal, 10cm com Shift)
        if key in (Qt.Key_Up, Qt.Key_Down):
            step = 0.10 if (modifiers & Qt.ShiftModifier) else 0.05
            if key == Qt.Key_Down:
                step = -step
            lights = _get_document_lights(viewport)
            if 0 <= self.light_index < len(lights):
                lt = lights[self.light_index]
                pos = lt.get("pos") or [0, 0, 0]
                pos[2] = round(pos[2] + step, 4)
                lt["pos"] = pos
                if lt.get("kind") == "spot" and "target" in lt and lt["target"]:
                    lt["target"][2] = round(lt["target"][2] + step, 4)
                if lt.get("kind") == "led_strip" and "p1" in lt and "p2" in lt:
                    lt["p1"][2] = round(lt["p1"][2] + step, 4)
                    lt["p2"][2] = round(lt["p2"][2] + step, 4)
                _translate_light_scene_group(viewport, self.light_index, QVector3D(0.0, 0.0, step), lt)
                _save_document_lights(viewport, lights, undoable=True)
                _flash(viewport, f"📏 Altura ajustada: Z={pos[2]:.2f}m (Setas ↑/↓)")
                if callable(self.on_moved):
                    self.on_moved()
                viewport.update()
                return True
        return False


class AimLightTool(Tool):
    """Ferramenta para direcionar a mira e ponto focal do Spot com o mouse."""

    name = "Mirar Spot"
    shortcut = None
    uses_snap = True
    description = "Clique no ponto ou superfície onde o Spot deve iluminar."

    def __init__(self, light_index: int, on_aimed=None):
        super().__init__()
        self.light_index = light_index
        self.on_aimed = on_aimed

    def on_activate(self, viewport) -> None:
        _flash(viewport, "🎯 Clique no móvel ou ponto para onde o Spot deve mirar. Esc cancela.")

    def on_deactivate(self, viewport) -> None:
        _flash(viewport, "")

    def on_click(self, ctx: ToolContext) -> None:
        lights = _get_document_lights(ctx.viewport)
        if 0 <= self.light_index < len(lights):
            lt = lights[self.light_index]
            pos = lt.get("pos", [0, 0, 0])
            target, _n = _surface_hit(ctx)
            if target is None:
                target = ctx.world
            if target is None:
                _flash(ctx.viewport, "Clique sobre uma superfície para mirar o spot.")
                return

            t_vec = [target.x(), target.y(), target.z()]
            dir_vec = [target.x() - pos[0], target.y() - pos[1], target.z() - pos[2]]
            dist = math.hypot(*dir_vec)
            if dist > 1e-4:
                lt["target"] = t_vec
                lt["dir"] = [dir_vec[0] / dist, dir_vec[1] / dist, dir_vec[2] / dist]
                _save_document_lights(ctx.viewport, lights, undoable=True)
                _flash(ctx.viewport, "✅ Ponto Focal do Spot atualizado com sucesso!")

        if callable(self.on_aimed):
            self.on_aimed()

        if hasattr(ctx.viewport, "set_active_tool"):
            app = getattr(ctx.viewport, "app", None)
            if app and hasattr(app, "select_tool"):
                ctx.viewport.set_active_tool(app.select_tool)

    def on_key(self, viewport, key, modifiers) -> bool:
        if key == Qt.Key_Escape:
            cb = getattr(self, 'on_aimed', None)
            if callable(cb):
                cb()
            return True
        return False



class LightManagerDialog(QDialog):
    """Diálogo visual para gerenciamento completo das luzes físicas da cena."""

    def __init__(self, viewport, parent=None):
        super().__init__(parent)
        self._host_window = host.window_of(window=parent, viewport=viewport)
        self._fallback_viewport = viewport
        self.setWindowTitle("💡 TrazoMob — Gerenciador de Iluminação & Spots Físicos")
        self.setMinimumSize(680, 520)

        self._lights: list[dict] = []
        self._current_index: int = -1

        self._build_ui()
        self._reload_lights()

    @property
    def viewport(self):
        return host.active_viewport(window=self._host_window, viewport=self._fallback_viewport)

    @viewport.setter
    def viewport(self, vp) -> None:
        if vp is not None:
            self._fallback_viewport = vp

    def sync_to_active_document(self, viewport=None) -> None:
        """Recarrega as luzes do documento atualmente ativo ao trocar de aba."""
        if viewport is not None:
            self._fallback_viewport = viewport
            win = host.window_of(viewport=viewport)
            if win is not None:
                self._host_window = win
        self._current_index = -1
        self._reload_lights()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Cabeçalho Explicativo
        lbl_head = QLabel(
            "<b>Controle Físico de Iluminação para Render Foto-Realista (Blender Cycles)</b><br>"
            "<span style='color: palette(text); font-size: 11px;'>"
            "As lâmpadas e spots inseridos iluminam fisicamente o ambiente.<br>"
            "Se todas as luzes forem desligadas e a cena for fechada, o render ficará no escuro real.</span>"
        )
        lbl_head.setWordWrap(True)
        layout.addWidget(lbl_head)

        # Corpo dividido em Lista (esquerda) e Propriedades (direita)
        splitter = QSplitter(Qt.Horizontal)

        # ── ESQUERDA: LISTA DE LUZES E PRESETS ──
        w_left = QWidget()
        l_left = QVBoxLayout(w_left)
        l_left.setContentsMargins(0, 0, 0, 0)
        l_left.setSpacing(8)

        lbl_list = QLabel("<b>Luzes no Projeto:</b>")
        l_left.addWidget(lbl_list)

        self.list_lights = QListWidget()
        self.list_lights.currentRowChanged.connect(self._on_light_selected)
        self.list_lights.itemChanged.connect(self._on_item_checked)
        l_left.addWidget(self.list_lights, 1)

        # Ações de adição rápida
        lbl_add = QLabel("<b>+ Adicionar Nova Luz:</b>")
        l_left.addWidget(lbl_add)

        h_add = QHBoxLayout()
        btn_add_spot = QPushButton("🔦 + Spot / Dicroica")
        btn_add_spot.setToolTip("Adiciona um spot com cone de luz direcionável")
        btn_add_spot.clicked.connect(lambda: self._start_placement("spot_quente"))
        h_add.addWidget(btn_add_spot)

        btn_add_led = QPushButton("✨ + Fita LED")
        btn_add_led.setToolTip("Adiciona iluminação difusa para nichos e sob armários")
        btn_add_led.clicked.connect(lambda: self._start_placement("fita_led"))
        h_add.addWidget(btn_add_led)

        l_left.addLayout(h_add)

        h_add2 = QHBoxLayout()
        btn_add_omni = QPushButton("💡 + Luz Omni")
        btn_add_omni.setToolTip("Lâmpada que ilumina em todas as direções (bulbo, pendente, arandela)")
        btn_add_omni.clicked.connect(lambda: self._start_placement("omni"))
        h_add2.addWidget(btn_add_omni)
        btn_add_plafon = QPushButton("⬜ + Plafon")
        btn_add_plafon.setToolTip("Luz geral difusa de teto, mais forte")
        btn_add_plafon.clicked.connect(lambda: self._start_placement("plafon_geral"))
        h_add2.addWidget(btn_add_plafon)
        l_left.addLayout(h_add2)

        btn_del = QPushButton("🗑️ Excluir Luz Selecionada")
        btn_del.clicked.connect(self._delete_current_light)
        l_left.addWidget(btn_del)

        splitter.addWidget(w_left)

        # ── DIREITA: PROPRIEDADES DA LUZ SELECIONADA ──
        self.w_right = QGroupBox("Propriedades da Luz")
        l_right = QVBoxLayout(self.w_right)
        l_right.setSpacing(10)

        # Nome
        h_name = QHBoxLayout()
        h_name.addWidget(QLabel("Nome / Identificação:"))
        self.txt_name = QPushButton()
        self.txt_name.setEnabled(False)
        h_name.addWidget(self.txt_name, 1)
        l_right.addLayout(h_name)

        # Tipo (Spot vs Difusa)
        h_kind = QHBoxLayout()
        h_kind.addWidget(QLabel("Tipo de Emissão:"))
        self.cb_kind = QComboBox()
        self.cb_kind.addItems([
            "Spot Direcionável (Cone de Foco)",
            "Omni / Ponto (todas as direções)",
            "Fita LED Linear",
        ])
        self.cb_kind.currentIndexChanged.connect(self._on_prop_changed)
        h_kind.addWidget(self.cb_kind, 1)
        l_right.addLayout(h_kind)

        # Potência (Watts)
        h_pwr = QHBoxLayout()
        h_pwr.addWidget(QLabel("Potência:"))
        self.spin_power = QDoubleSpinBox()
        self.spin_power.setRange(10.0, 10000.0)
        self.spin_power.setSingleStep(50.0)
        self.spin_power.setSuffix(" W")
        self.spin_power.valueChanged.connect(self._on_prop_changed)
        h_pwr.addWidget(self.spin_power, 1)
        l_right.addLayout(h_pwr)

        # Temperatura de Cor (Kelvin)
        lbl_k = QLabel("Temperatura de Cor (Kelvin):")
        l_right.addWidget(lbl_k)

        h_k = QHBoxLayout()
        self.slider_kelvin = QSlider(Qt.Horizontal)
        self.slider_kelvin.setRange(MIN_KELVIN, MAX_KELVIN)
        self.slider_kelvin.setSingleStep(100)
        self.spin_kelvin = QSpinBox()
        self.spin_kelvin.setRange(MIN_KELVIN, MAX_KELVIN)
        self.spin_kelvin.setSingleStep(100)
        self.spin_kelvin.setSuffix(" K")

        self.slider_kelvin.valueChanged.connect(self.spin_kelvin.setValue)
        self.spin_kelvin.valueChanged.connect(self.slider_kelvin.setValue)
        self.slider_kelvin.sliderReleased.connect(self._on_prop_changed)
        self.spin_kelvin.editingFinished.connect(self._on_prop_changed)

        h_k.addWidget(self.slider_kelvin, 1)
        h_k.addWidget(self.spin_kelvin)
        l_right.addLayout(h_k)

        self.lbl_kelvin_desc = QLabel("2700K — Amarela Quente Aconchegante")
        self.lbl_kelvin_desc.setStyleSheet("color: palette(mid); font-style: italic;")
        l_right.addWidget(self.lbl_kelvin_desc)

        # Ângulo de Abertura (para Spots)
        self.w_spot_group = QWidget()
        l_spot = QVBoxLayout(self.w_spot_group)
        l_spot.setContentsMargins(0, 0, 0, 0)
        l_spot.setSpacing(8)

        h_ang = QHBoxLayout()
        h_ang.addWidget(QLabel("Abertura do Facho:"))
        self.spin_angle = QDoubleSpinBox()
        self.spin_angle.setRange(10.0, 120.0)
        self.spin_angle.setSingleStep(5.0)
        self.spin_angle.setSuffix(" °")
        self.spin_angle.valueChanged.connect(self._on_prop_changed)
        h_ang.addWidget(self.spin_angle, 1)
        l_spot.addLayout(h_ang)

        h_bld = QHBoxLayout()
        h_bld.addWidget(QLabel("Suavidade / Falloff:"))
        self.spin_blend = QDoubleSpinBox()
        self.spin_blend.setRange(0.0, 1.0)
        self.spin_blend.setSingleStep(0.05)
        self.spin_blend.setDecimals(2)
        self.spin_blend.setToolTip("Controle de transição do facho: 0.0 = borda nítida/cortada; 1.0 = borda ultra suave e difusa.")
        self.spin_blend.valueChanged.connect(self._on_prop_changed)
        h_bld.addWidget(self.spin_blend, 1)
        l_spot.addLayout(h_bld)

        h_ies = QHBoxLayout()
        self.btn_ies = QPushButton("📂 Carregar Fotometria IES...")
        self.btn_ies.setToolTip("Carrega arquivo .ies real do fabricante (Phillips, Osram, Stella) para facho foto-realista.")
        self.btn_ies.clicked.connect(self._select_ies_file)
        h_ies.addWidget(self.btn_ies, 1)

        self.btn_clear_ies = QPushButton("✕")
        self.btn_clear_ies.setToolTip("Remover curva IES e voltar ao cone padrão")
        self.btn_clear_ies.setFixedWidth(28)
        self.btn_clear_ies.clicked.connect(self._clear_ies_file)
        h_ies.addWidget(self.btn_clear_ies)
        l_spot.addLayout(h_ies)

        self.btn_aim = QPushButton("🎯 Mirar Spot no 3D (Clique onde iluminar)")
        self.btn_aim.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 6px;")
        self.btn_aim.clicked.connect(self._start_aim)
        l_spot.addWidget(self.btn_aim)

        l_right.addWidget(self.w_spot_group)

        # Altura / Elevação (Z)
        h_elev = QHBoxLayout()
        h_elev.addWidget(QLabel("Altura / Elevação (Z):"))
        self.spin_z = QDoubleSpinBox()
        self.spin_z.setRange(-10.0, 50.0)
        self.spin_z.setSingleStep(0.05)
        self.spin_z.setDecimals(2)
        self.spin_z.setSuffix(" m")
        self.spin_z.valueChanged.connect(self._on_prop_changed)
        h_elev.addWidget(self.spin_z, 1)

        btn_elev_up = QPushButton("▲ +10cm")
        btn_elev_up.clicked.connect(lambda: self.spin_z.setValue(self.spin_z.value() + 0.10))
        h_elev.addWidget(btn_elev_up)

        btn_elev_dn = QPushButton("▼ -10cm")
        btn_elev_dn.clicked.connect(lambda: self.spin_z.setValue(self.spin_z.value() - 0.10))
        h_elev.addWidget(btn_elev_dn)

        l_right.addLayout(h_elev)

        # Botão Reposicionar
        self.btn_reposition = QPushButton("📍 Reposicionar Luz no 3D")
        self.btn_reposition.clicked.connect(self._reposition_current_light)
        l_right.addWidget(self.btn_reposition)

        l_right.addStretch()
        splitter.addWidget(self.w_right)

        layout.addWidget(splitter, 1)

        # Rodapé
        h_bot = QHBoxLayout()
        h_bot.addStretch()
        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(self.accept)
        h_bot.addWidget(btn_close)
        layout.addLayout(h_bot)

    def _reload_lights(self):
        """Atualiza a lista visual com os dados das luzes salvas."""
        self._lights = _get_document_lights(self.viewport)
        self.list_lights.blockSignals(True)
        self.list_lights.clear()

        for i, lt in enumerate(self._lights):
            kind = "Spot" if lt.get("kind") == "spot" else "Difusa"
            name = lt.get("name") or f"Luz {i+1} ({kind})"
            power = int(lt.get("power", 400.0))
            k = int(lt.get("kelvin", 2700))
            icon_char = "🔦" if kind == "Spot" else "💡"

            item = QListWidgetItem(f"{icon_char} {name} — {power}W ({k}K)")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if lt.get("on", True) else Qt.Unchecked)
            self.list_lights.addItem(item)

        self.list_lights.blockSignals(False)

        if self._lights:
            sel_idx = min(max(self._current_index, 0), len(self._lights) - 1)
            self.list_lights.setCurrentRow(sel_idx)
        else:
            self._current_index = -1
            self.w_right.setEnabled(False)

    def _on_light_selected(self, row: int):
        self._current_index = row
        if not (0 <= row < len(self._lights)):
            self.w_right.setEnabled(False)
            return

        self.w_right.setEnabled(True)
        lt = self._lights[row]

        kind = lt.get("kind", "spot")
        self.cb_kind.blockSignals(True)
        if kind == "led_strip":
            self.cb_kind.setCurrentIndex(2)
            self.cb_kind.setEnabled(False)
        else:
            self.cb_kind.setCurrentIndex(0 if kind == "spot" else 1)
            self.cb_kind.setEnabled(True)
        self.cb_kind.blockSignals(False)

        self.txt_name.setText(lt.get("name") or f"Luz #{row+1}")

        self.spin_power.blockSignals(True)
        self.spin_power.setValue(float(lt.get("power", 400.0)))
        self.spin_power.blockSignals(False)

        k = int(lt.get("kelvin", 2700))
        self.slider_kelvin.blockSignals(True)
        self.spin_kelvin.blockSignals(True)
        self.slider_kelvin.setValue(k)
        self.spin_kelvin.setValue(k)
        self.slider_kelvin.blockSignals(False)
        self.spin_kelvin.blockSignals(False)
        self._update_kelvin_desc(k)

        self.w_spot_group.setVisible(kind == "spot")
        self.spin_angle.blockSignals(True)
        self.spin_angle.setValue(float(lt.get("angle", 45.0)))
        self.spin_angle.blockSignals(False)

        self.spin_blend.blockSignals(True)
        self.spin_blend.setValue(float(lt.get("blend", 0.35)))
        self.spin_blend.blockSignals(False)

        ies_cur = lt.get("ies_path")
        if ies_cur:
            from pathlib import Path
            self.btn_ies.setText(f"📄 IES: {Path(ies_cur).name}")
            self.btn_ies.setStyleSheet("font-weight: bold; color: #0284C7;")
        else:
            self.btn_ies.setText("📂 Carregar Fotometria IES...")
            self.btn_ies.setStyleSheet("")

        pos = lt.get("pos") or [0, 0, 0]
        self.spin_z.blockSignals(True)
        self.spin_z.setValue(float(pos[2]))
        self.spin_z.blockSignals(False)

    def _select_ies_file(self):
        row = self._current_index
        if not (0 <= row < len(self._lights)):
            return
        from PySide6.QtWidgets import QFileDialog
        from pathlib import Path
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Arquivo de Fotometria IES",
            "",
            "Arquivos IES (*.ies);;Todos os Arquivos (*.*)"
        )
        if path:
            self._lights[row]["ies_path"] = path
            self.btn_ies.setText(f"📄 IES: {Path(path).name}")
            self.btn_ies.setStyleSheet("font-weight: bold; color: #0284C7;")
            _save_document_lights(self.viewport, self._lights)

    def _clear_ies_file(self):
        row = self._current_index
        if not (0 <= row < len(self._lights)):
            return
        self._lights[row].pop("ies_path", None)
        self.btn_ies.setText("📂 Carregar Fotometria IES...")
        self.btn_ies.setStyleSheet("")
        _save_document_lights(self.viewport, self._lights)

    def _update_kelvin_desc(self, k: int):
        if k < 2500:
            desc = "Luz de Vela / Fogo (Muito Quente)"
        elif k < 3200:
            desc = "Luz Quente Aconchegante (Ideal para quartos e salas)"
        elif k < 4500:
            desc = "Luz Neutra de Trabalho (Ideal para cozinhas e escritórios)"
        else:
            desc = "Luz Fria / Luz do Dia (LED 6500K)"
        self.lbl_kelvin_desc.setText(f"{k}K — {desc}")

    def _on_item_checked(self, item: QListWidgetItem):
        row = self.list_lights.row(item)
        if 0 <= row < len(self._lights):
            self._lights[row]["on"] = item.checkState() == Qt.Checked
            _save_document_lights(self.viewport, self._lights)

    def _on_prop_changed(self):
        row = self._current_index
        if not (0 <= row < len(self._lights)):
            return

        lt = self._lights[row]
        if lt.get("kind") == "led_strip":
            is_spot = False
        else:
            is_spot = self.cb_kind.currentIndex() == 0
            lt["kind"] = "spot" if is_spot else "point"
        self.w_spot_group.setVisible(is_spot)

        lt["power"] = float(self.spin_power.value())
        k = int(self.spin_kelvin.value())
        lt["kelvin"] = k
        lt["color"] = list(kelvin_to_rgb(k))
        lt["angle"] = float(self.spin_angle.value())
        lt["blend"] = float(self.spin_blend.value())

        # Atualiza Z e desloca target/fitas de acordo
        new_z = round(float(self.spin_z.value()), 4)
        pos = lt.get("pos") or [0, 0, 0]
        dz = new_z - pos[2]
        pos[2] = new_z
        lt["pos"] = pos

        if lt.get("kind") == "spot" and "target" in lt and lt["target"]:
            lt["target"][2] = round(lt["target"][2] + dz, 4)
        if lt.get("kind") == "led_strip" and "p1" in lt and "p2" in lt:
            lt["p1"][2] = round(lt["p1"][2] + dz, 4)
            lt["p2"][2] = round(lt["p2"][2] + dz, 4)

        self._update_kelvin_desc(k)
        _translate_light_scene_group(self.viewport, row, QVector3D(0.0, 0.0, dz), lt)
        _save_document_lights(self.viewport, self._lights)

        # Atualiza o texto do item da lista
        kind_label = "Spot" if is_spot else "Difusa"
        icon_char = "🔦" if is_spot else "💡"
        name = lt.get("name") or f"Luz {row+1} ({kind_label})"
        self.list_lights.item(row).setText(f"{icon_char} {name} — {int(lt['power'])}W ({k}K)")

    def _start_placement(self, preset_key: str):
        preset = LIGHT_PRESETS.get(preset_key, LIGHT_PRESETS["spot_quente"])
        new_light = dict(preset)
        new_light["color"] = list(kelvin_to_rgb(new_light["kelvin"]))

        self.hide()

        def _on_done(_placed):
            self._reload_lights()
            self.show()

        if preset.get("kind") == "led_strip" or preset_key == "fita_led":
            tool = InsertLedStripTool(new_light, on_placed=_on_done)
        else:
            tool = InsertLightTool(new_light, on_placed=_on_done)
        self.viewport.set_active_tool(tool)


    def _reposition_current_light(self):
        if not (0 <= self._current_index < len(self._lights)):
            return
        self.hide()

        def _on_done():
            self._reload_lights()
            self.show()

        tool = MoveLightTool(self._current_index, on_moved=_on_done)
        self.viewport.set_active_tool(tool)

    def _start_aim(self):
        if not (0 <= self._current_index < len(self._lights)):
            return
        self.hide()

        def _on_aimed():
            self._reload_lights()
            self.show()

        tool = AimLightTool(self._current_index, on_aimed=_on_aimed)
        self.viewport.set_active_tool(tool)

    def _delete_current_light(self):
        if 0 <= self._current_index < len(self._lights):
            del self._lights[self._current_index]
            _save_document_lights(self.viewport, self._lights, undoable=True)
            self._reload_lights()


# ── Mini Popup Flutuante de Edição Rápida da Luz (HUD) ─────────────────────────
class LightQuickPopupHUD(QFrame):
    """Mini painel flutuante de edição rápida ao clicar numa luz no 3D."""

    def __init__(self, viewport, light_index: int, on_changed=None, parent=None):
        super().__init__(parent or viewport)
        self.viewport = viewport
        self.light_index = light_index
        self.on_changed = on_changed
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 35, 235);
                border: 1px solid #0284C7;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 11px;
            }
            QLabel { background: transparent; color: #FFFFFF; }
            QPushButton {
                background-color: #374151;
                border: 1px solid #4B5563;
                border-radius: 4px;
                padding: 4px 8px;
                color: white;
            }
            QPushButton:hover { background-color: #4B5563; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        lights = _get_document_lights(self.viewport)
        if not (0 <= self.light_index < len(lights)):
            self.close()
            return
        lt = lights[self.light_index]

        kind = lt.get("kind", "point")
        kind_label = "Spot Direcionável" if kind == "spot" else ("Fita LED Linear" if kind == "led_strip" else "Luz Ponto/Omni")

        # Cabeçalho
        h_top = QHBoxLayout()
        lbl_title = QLabel(f"<b>💡 {lt.get('name') or kind_label}</b>")
        h_top.addWidget(lbl_title, 1)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(20, 20)
        btn_close.clicked.connect(self.close)
        h_top.addWidget(btn_close)
        layout.addLayout(h_top)

        # Ligar / Desligar
        h_on = QHBoxLayout()
        self.btn_toggle = QPushButton("Desligar Luz" if lt.get("on", True) else "Ligar Luz")
        self.btn_toggle.setStyleSheet("background-color: #059669;" if lt.get("on", True) else "background-color: #6B7280;")
        self.btn_toggle.clicked.connect(self._toggle_on)
        h_on.addWidget(self.btn_toggle, 1)
        layout.addLayout(h_on)

        # Potência
        h_pwr = QHBoxLayout()
        h_pwr.addWidget(QLabel("Potência:"))
        self.sp_pwr = QSpinBox()
        self.sp_pwr.setRange(10, 10000)
        self.sp_pwr.setSingleStep(50)
        self.sp_pwr.setSuffix(" W")
        self.sp_pwr.setValue(int(lt.get("power", 400)))
        self.sp_pwr.valueChanged.connect(self._on_prop_change)
        h_pwr.addWidget(self.sp_pwr, 1)
        layout.addLayout(h_pwr)

        # Kelvin
        h_k = QHBoxLayout()
        h_k.addWidget(QLabel("Kelvin:"))
        self.sl_k = QSlider(Qt.Horizontal)
        self.sl_k.setRange(MIN_KELVIN, MAX_KELVIN)
        self.sl_k.setSingleStep(100)
        self.sl_k.setValue(int(lt.get("kelvin", 2700)))
        self.sl_k.valueChanged.connect(self._on_prop_change)
        h_k.addWidget(self.sl_k, 1)
        self.lbl_k_val = QLabel(f"{int(lt.get('kelvin', 2700))}K")
        h_k.addWidget(self.lbl_k_val)
        layout.addLayout(h_k)

        # Se for spot: botão para mirar ponto focal e ângulo
        if kind == "spot":
            h_ang = QHBoxLayout()
            h_ang.addWidget(QLabel("Ângulo Facho:"))
            self.sp_ang = QSpinBox()
            self.sp_ang.setRange(10, 120)
            self.sp_ang.setSuffix("°")
            self.sp_ang.setValue(int(lt.get("angle", 45)))
            self.sp_ang.valueChanged.connect(self._on_prop_change)
            h_ang.addWidget(self.sp_ang, 1)
            layout.addLayout(h_ang)

            btn_aim = QPushButton("🎯 Mirar no Ponto Focal (3D)")
            btn_aim.setStyleSheet("background-color: #0284C7; font-weight: bold;")
            btn_aim.clicked.connect(self._aim_spot)
            layout.addWidget(btn_aim)

        # Elevação / Altura Z
        pos = lt.get("pos") or [0, 0, 0]
        h_z = QHBoxLayout()
        h_z.addWidget(QLabel("Altura (Z):"))
        self.sp_z = QDoubleSpinBox()
        self.sp_z.setRange(-10.0, 50.0)
        self.sp_z.setSingleStep(0.05)
        self.sp_z.setDecimals(2)
        self.sp_z.setSuffix(" m")
        self.sp_z.setValue(float(pos[2]))
        self.sp_z.valueChanged.connect(self._on_z_change)
        h_z.addWidget(self.sp_z, 1)

        btn_z_up = QPushButton("▲")
        btn_z_up.setToolTip("Subir 10cm (+0.10m)")
        btn_z_up.setFixedWidth(24)
        btn_z_up.clicked.connect(lambda: self.sp_z.setValue(self.sp_z.value() + 0.10))
        h_z.addWidget(btn_z_up)

        btn_z_dn = QPushButton("▼")
        btn_z_dn.setToolTip("Descer 10cm (-0.10m)")
        btn_z_dn.setFixedWidth(24)
        btn_z_dn.clicked.connect(lambda: self.sp_z.setValue(self.sp_z.value() - 0.10))
        h_z.addWidget(btn_z_dn)

        layout.addLayout(h_z)

        # Ações inferiores: Mover e Excluir
        h_bot = QHBoxLayout()
        btn_move = QPushButton("📍 Mover Posição")
        btn_move.setStyleSheet("background-color: #2563EB; font-weight: bold;")
        btn_move.setToolTip("Clique na nova posição/superfície onde deseja fixar esta luz.")
        btn_move.clicked.connect(self._move_light)
        h_bot.addWidget(btn_move)

        btn_del = QPushButton("🗑️ Excluir")
        btn_del.setStyleSheet("background-color: #DC2626;")
        btn_del.clicked.connect(self._delete_light)
        h_bot.addWidget(btn_del)
        layout.addLayout(h_bot)

        self.adjustSize()

    def _move_light(self):
        self.close()
        tool = MoveLightTool(self.light_index, on_moved=self.on_changed)
        self.viewport.set_active_tool(tool)


    def _toggle_on(self):
        lights = _get_document_lights(self.viewport)
        if 0 <= self.light_index < len(lights):
            cur = lights[self.light_index].get("on", True)
            lights[self.light_index]["on"] = not cur
            _save_document_lights(self.viewport, lights)
            self.btn_toggle.setText("Desligar Luz" if not cur else "Ligar Luz")
            self.btn_toggle.setStyleSheet("background-color: #059669;" if not cur else "background-color: #6B7280;")
            if callable(self.on_changed):
                self.on_changed()

    def _on_prop_change(self):
        lights = _get_document_lights(self.viewport)
        if 0 <= self.light_index < len(lights):
            lt = lights[self.light_index]
            lt["power"] = float(self.sp_pwr.value())
            k = int(self.sl_k.value())
            lt["kelvin"] = k
            lt["color"] = list(kelvin_to_rgb(k))
            self.lbl_k_val.setText(f"{k}K")
            if hasattr(self, "sp_ang"):
                lt["angle"] = float(self.sp_ang.value())
            _save_document_lights(self.viewport, lights)
            if callable(self.on_changed):
                self.on_changed()

    def _on_z_change(self):
        lights = _get_document_lights(self.viewport)
        if 0 <= self.light_index < len(lights):
            lt = lights[self.light_index]
            new_z = round(float(self.sp_z.value()), 4)
            pos = lt.get("pos") or [0, 0, 0]
            dz = new_z - pos[2]
            pos[2] = new_z
            lt["pos"] = pos

            # Desloca target se for spot
            if lt.get("kind") == "spot" and "target" in lt and lt["target"]:
                lt["target"][2] = round(lt["target"][2] + dz, 4)

            # Desloca terminais se for fita LED
            if lt.get("kind") == "led_strip" and "p1" in lt and "p2" in lt:
                lt["p1"][2] = round(lt["p1"][2] + dz, 4)
                lt["p2"][2] = round(lt["p2"][2] + dz, 4)

            _translate_light_scene_group(self.viewport, self.light_index, QVector3D(0.0, 0.0, dz), lt)
            _save_document_lights(self.viewport, lights)
            if callable(self.on_changed):
                self.on_changed()

    def _aim_spot(self):
        self.close()
        tool = AimLightTool(self.light_index, on_aimed=self.on_changed)
        self.viewport.set_active_tool(tool)

    def _delete_light(self):
        lights = _get_document_lights(self.viewport)
        if 0 <= self.light_index < len(lights):
            del lights[self.light_index]
            _save_document_lights(self.viewport, lights, undoable=True)
        if callable(self.on_changed):
            self.on_changed()
        self.close()


_LIGHT_OCCLUDER_MASK_CACHE: dict[tuple[Any, ...], Any] = {}
_MAX_LIGHT_OCCLUDER_MASK_CACHE = 8


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

        try:
            import sys
            mod = sys.modules.get("plugins.render_blender")
            if mod is not None and not getattr(mod, "_trazomob_overlay_silenced", False):
                from ..integrations.hooks import silence_native_light_overlay
                silence_native_light_overlay()
        except Exception:
            pass

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

