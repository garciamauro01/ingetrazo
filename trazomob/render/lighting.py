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

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QVector3D,
)

from core.group import Group
from core.history import Command
from core.mesh import Mesh
from core.render_blender import (
    DEFAULT_KELVIN,
    MAX_KELVIN,
    MIN_KELVIN,
    kelvin_to_rgb,
)
from tools.base import Tool, ToolContext

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




from .lighting_visualizer import (  # noqa: E402
    _build_light_occluder_context,
    _ray_blocked,
)


from .lighting_ui import LightManagerDialog, LightQuickPopupHUD  # noqa: E402, F401
from .lighting_visualizer import (  # noqa: E402, F401
    _is_opaque_light_occluder,
    _build_light_occluder_context,
    _ray_blocked,
    TrazoMobLightVisualizer,
)
