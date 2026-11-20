# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors and Pair Programmer.
"""Pontos de chamada do host first-party para o TrazoMob.

O TrazoMob faz parte do IngeTrazo: não há mais ganchos nem monkeypatch. Cada
função aqui é chamada diretamente por um ponto do host (``core.group``,
``core.history``, ``tools.move``, ``tools.scale``, ``views.viewport``,
``core.render_blender``, ``plugins.render_blender``).

O estado do motor é verificado aqui mesmo, no TrazoMob: o host não precisa
saber se o interruptor está ligado. A leitura de vínculos
(:func:`library_links.rebuild_scene_links`) é a única integração sempre ativa.
"""
from __future__ import annotations

import copy
import logging
from typing import Any

logger = logging.getLogger("trazomob.host_calls")

#: Chaves de metadados dos módulos.
MODULE_KEYS = ("trazomob_module",)

#: Campos próprios de uma fita de LED que o render deve preservar.
LED_EXTRA_FIELDS = ("target", "p1", "p2", "length", "profile_w")


# ---------------------------------------------------------------------------
# Identificação de módulos e de grupos travados
# ---------------------------------------------------------------------------

def _is_trazomob_module(group: Any) -> bool:
    if group is None:
        return False
    ext = getattr(group, "ext", None)
    if not isinstance(ext, dict):
        return False
    return any(key in ext for key in MODULE_KEYS)


def _get_module_key(group: Any) -> str:
    ext = getattr(group, "ext", {}) or {}
    for key in MODULE_KEYS:
        if key in ext:
            return key
    return MODULE_KEYS[-1]


def _module_params(group: Any) -> dict:
    return group.ext.get(_get_module_key(group), {})


def _motion_locked(group: Any) -> bool:
    """``motion_locked``: paredes e piso do projeto não se movem."""
    if group is None:
        return False
    if getattr(group, "motion_locked", False):
        return True
    ext = getattr(group, "ext", None)
    if not isinstance(ext, dict):
        return False
    if ext.get("motion_locked"):
        return True
    wall = ext.get("trazomob_wall")
    return isinstance(wall, dict) and bool(wall.get("motion_locked", False))


def _translate_module(group: Any, scene: Any, delta) -> None:
    """Move as peças do módulo e o offset paramétrico (usado do e undo)."""
    from PySide6.QtGui import QVector3D

    for target in getattr(group, "children", []) or [group]:
        mesh = getattr(target, "mesh", None)
        if mesh is not None and hasattr(mesh, "vertices"):
            for vertex in mesh.vertices:
                vertex.position += delta
            mesh._mut_serial = getattr(mesh, "_mut_serial", 0) + 1
        ext = getattr(target, "ext", None)
        if isinstance(ext, dict):
            if isinstance(ext.get("orig_vertices"), list):
                ext["orig_vertices"] = [
                    origin + delta for origin in ext["orig_vertices"]
                    if isinstance(origin, QVector3D)
                ]
            hinge = ext.get("hinge_pivot")
            if isinstance(hinge, QVector3D):
                ext["hinge_pivot"] = hinge + delta

    params = _module_params(group)
    offset = params.get("offset", (0.0, 0.0, 0.0))
    if isinstance(offset, (list, tuple)) and len(offset) >= 3:
        params["offset"] = (
            float(offset[0]) + float(delta.x()),
            float(offset[1]) + float(delta.y()),
            float(offset[2]) + float(delta.z()),
        )
    scene.version += 1


# ---------------------------------------------------------------------------
# core.group.copy_group
# ---------------------------------------------------------------------------

def prepare_copied_group(group: Any) -> None:
    """Dá malha própria a cada peça de um módulo copiado.

    Sem isso, girar/editar a cópia afetaria o original (as peças filhas
    compartilhavam a mesma malha).
    """
    if not _is_trazomob_module(group):
        return
    from core.group import transformed_mesh
    from PySide6.QtGui import QMatrix4x4

    identity = QMatrix4x4()

    def _walk(node):
        for child in getattr(node, "children", []) or []:
            if getattr(child, "mesh", None) is not None:
                child.mesh = transformed_mesh(child.mesh, identity)
            _walk(child)

    _walk(group)


# ---------------------------------------------------------------------------
# core.history: rotação, escala e translação paramétricas
# ---------------------------------------------------------------------------

def rotate_module_command(command: Any, scene: Any, *, sign: float) -> bool:
    """``True`` quando o comando é um módulo e já foi tratado aqui."""
    if not _is_trazomob_module(getattr(command, "group", None)):
        return False
    from ..builders.cabinet import CabinetBuilder

    CabinetBuilder.rotate_module(
        command.group, sign * command.degrees,
        center=command.center, axis=command.axis, scene=scene,
        update_param=True)
    return True


def scale_module_command(command: Any, scene: Any, *, forward: bool) -> bool:
    if not _is_trazomob_module(getattr(command, "group", None)):
        return False
    from ..builders.cabinet import CabinetBuilder

    group = command.group
    if forward:
        if getattr(command, "_mod_params_before", None) is None:
            command._mod_params_before = copy.deepcopy(_module_params(group))
        if getattr(command, "_mod_children_before", None) is None:
            command._mod_children_before = list(getattr(group, "children", []))
        if getattr(command, "_mod_name_before", None) is None:
            command._mod_name_before = getattr(group, "name", "")
        CabinetBuilder.scale_module(
            group, command.center, command.factor, axes=command.axes,
            scene=scene, update_param=True, rebuild=True)
    else:
        if getattr(command, "_mod_params_before", None) is not None:
            params_prev = copy.deepcopy(command._mod_params_before)
            group.ext[_get_module_key(group)] = params_prev
            from ..domain.module_geometry import get_module_carcass_bounds
            from ..interaction.magnetic_drag import get_module_bounds
            b_now = (get_module_carcass_bounds(group)
                     or get_module_bounds(group))
            CabinetBuilder._rebuild_scaled_module_pieces(group, params_prev, b_now)
        elif getattr(command, "_mod_children_before", None) is not None:
            group.children = list(command._mod_children_before)
        if getattr(command, "_mod_name_before", None) is not None:
            group.name = command._mod_name_before
        from core.history import _dirty_group_chunks
        if scene is not None:
            _dirty_group_chunks(scene)
            scene.version += 1
    return True


def translate_module_command(command: Any, scene: Any, delta) -> bool:
    if not _is_trazomob_module(getattr(command, "group", None)):
        return False
    _translate_module(command.group, scene, delta)
    return True


# ---------------------------------------------------------------------------
# tools.move
# ---------------------------------------------------------------------------

def _find_top_module_for_group(group: Any, scene: Any) -> Any:
    """Se ``group`` é peça de um módulo, retorna o módulo-pai."""
    if group is None:
        return None
    if _is_trazomob_module(group):
        return group
    owner = getattr(group, "owner", None)
    if owner is not None and _is_trazomob_module(owner):
        return owner
    if scene is not None and hasattr(scene, "groups"):
        for candidate in scene.groups:
            if not _is_trazomob_module(candidate):
                continue
            if (group in (getattr(candidate, "children", []) or [])
                    or getattr(group, "owner", None) is candidate):
                return candidate
    return group


def resolve_move_groups(groups, scene):
    """Resolve peças para o módulo-pai e remove o que está travado."""
    resolved = []
    for group in groups or ():
        top = _find_top_module_for_group(group, scene)
        if top is not None and top not in resolved:
            resolved.append(top)
        elif top is None and group not in resolved:
            resolved.append(group)
    return [group for group in resolved if not _motion_locked(group)]


def before_move_commit(move_tool: Any) -> None:
    """Não deixa o modo cópia ficar armado sem a tecla Control."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    if not bool(QApplication.keyboardModifiers() & Qt.ControlModifier):
        move_tool._copy = False


def after_move_commit(viewport: Any) -> None:
    """Sincroniza as luzes do documento após mover entidades do TrazoMob."""
    try:
        scene = getattr(viewport, "scene", None)
        selection = getattr(scene, "selection", ()) if scene else ()
        has_trazomob = any(
            _is_trazomob_module(entity) or (
                hasattr(entity, "ext") and isinstance(entity.ext, dict)
                and any(key in entity.ext for key in (
                    "trazomob_light", "atomic_light", "trazomob_wall",
                    "trazomob_esquadria"))
            )
            for entity in selection
        )
        if has_trazomob:
            from ..render.lighting import sync_scene_lights_to_document
            sync_scene_lights_to_document(viewport)
    except Exception as exc:
        logger.debug("sincronização das luzes falhou após mover: %s", exc)


# ---------------------------------------------------------------------------
# tools.scale
# ---------------------------------------------------------------------------

def scale_factor_override(scale_tool: Any, ctx: Any, viewport: Any,
                          sx: float, sy: float, default):
    """Snap de réguas de altura ao escalar módulos do TrazoMob."""
    # Um ponto nomeado (endpoint, midpoint...) vence: o usuário mirou nele.
    try:
        if scale_tool._snapped_point(ctx) is not None:
            return default
    except Exception:
        logger.debug("Falha ao avaliar ponto de snap nomeado", exc_info=True)

    groups = getattr(scale_tool, "_groups", [])

    def _is_esquadria(group):
        ext = getattr(group, "ext", None)
        if isinstance(ext, dict) and "trazomob_esquadria" in ext:
            return True
        return getattr(group, "layer", "") == "ESQUADRIAS"

    if not any(_is_trazomob_module(group) for group in groups):
        return default
    if any(_is_esquadria(group) for group in groups):
        return default

    grip = getattr(scale_tool, "_grip", None)
    anchor = getattr(scale_tool, "_anchor", None)
    if grip is None or 2 not in grip.mask or anchor is None:
        return default
    try:
        from ..wall.guides import WallGuideRulerManager
        from PySide6.QtGui import QVector3D

        ruler_mgr = WallGuideRulerManager.get_instance()
        if not (ruler_mgr.visible and ruler_mgr.snap_enabled):
            return default
        factors_est = scale_tool._factors_from_cursor(viewport, sx, sy)
        if factors_est is None:
            return default
        grip_pos = scale_tool._grip_pos(grip)
        est_z = anchor.z() + (grip_pos.z() - anchor.z()) * factors_est[2]
        snap_res = ruler_mgr.snap_to_levels(est_z, threshold_m=0.08)
        if snap_res is None:
            return default
        snapped = QVector3D(grip_pos.x(), grip_pos.y(), snap_res[0])
        return scale_tool._factors_from_point(snapped) or default
    except Exception as exc:
        logger.debug("snap de nível no Scale falhou: %s", exc)
        return default


def promote_selection_modules(viewport: Any) -> None:
    """Na ativação do Scale, seleciona o módulo em vez de uma peça filha."""
    scene = getattr(viewport, "scene", None)
    if scene is None or not getattr(scene, "selection", None):
        return
    to_replace = []
    for entity in scene.selection:
        owner = getattr(entity, "owner", None)
        if owner is not None and _is_trazomob_module(owner):
            to_replace.append((entity, owner))
    for old_entity, master in to_replace:
        scene.selection.discard(old_entity)
        scene.selection.add(master)


def prateleiras_bounds(scale_tool: Any, viewport: Any):
    """Caixa do vão de prateleiras avulsas, ou ``None`` para a caixa nativa."""
    import math
    from core.group import Group
    from PySide6.QtGui import QVector3D

    scene = getattr(viewport, "scene", None)
    selection = list(getattr(scene, "selection", [])) if scene else []
    prat_mods = [
        group for group in selection
        if isinstance(group, Group) and _is_trazomob_module(group)
        and str(_module_params(group).get("tipo", "")) == "peca_prateleiras_avulsas"
    ]
    if not prat_mods:
        return None
    scale_tool._pick_frame(viewport)
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3

    def absorb(point: QVector3D) -> None:
        point = scale_tool._to_local(point)
        for i, coord in enumerate((point.x(), point.y(), point.z())):
            if coord < lo[i]:
                lo[i] = coord
            if coord > hi[i]:
                hi[i] = coord

    for mod in prat_mods:
        params = _module_params(mod)
        width = float(params.get("largura", 800.0)) / 1000.0
        depth = float(params.get("profundidade", 300.0)) / 1000.0
        height = float(params.get("altura", 720.0)) / 1000.0
        rot_z = float(params.get("rot_z", 0.0))
        offset = params.get("offset", (0.0, 0.0, 0.0))
        rad = math.radians(rot_z)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        off = QVector3D(*offset)
        for corner in (
            QVector3D(0.0, 0.0, 0.0), QVector3D(width, 0.0, 0.0),
            QVector3D(width, depth, 0.0), QVector3D(0.0, depth, 0.0),
            QVector3D(0.0, 0.0, height), QVector3D(width, 0.0, height),
            QVector3D(width, depth, height), QVector3D(0.0, depth, height),
        ):
            rx = corner.x() * cos_a - corner.y() * sin_a
            ry = corner.x() * sin_a + corner.y() * cos_a
            absorb(QVector3D(rx, ry, corner.z()) + off)

    others = [entity for entity in selection if entity not in prat_mods]
    if others:
        from core.group import iter_placements
        from core.image_plane import ImagePlane
        from core.mesh import Edge, Face

        for entity in others:
            if isinstance(entity, Edge):
                absorb(entity.a)
                absorb(entity.b)
            elif isinstance(entity, Face):
                for vertex in entity.vertices:
                    absorb(vertex)
            elif isinstance(entity, ImagePlane):
                for corner in entity.corners():
                    absorb(corner)
            elif hasattr(entity, "mesh"):
                for placement, matrix in iter_placements(entity):
                    for vertex in placement.mesh.vertices:
                        absorb(matrix.map(vertex.position)
                               if matrix is not None else vertex.position)
    return QVector3D(*lo), QVector3D(*hi)


def capture_module_originals(scale_tool: Any, viewport: Any) -> bool:
    """Captura vértices de módulos; ``True`` quando o host deve usar estes."""
    from PySide6.QtGui import QMatrix4x4, QVector3D

    orig_vertices: list = []
    orig_xforms: list = []
    has_module = False
    for group in getattr(scale_tool, "_groups", []):
        if _is_trazomob_module(group):
            has_module = True
            targets = getattr(group, "children", []) or [group]
            for target in targets:
                mesh = getattr(target, "mesh", None)
                if mesh is not None and hasattr(mesh, "vertices"):
                    orig_vertices.extend(
                        (mesh, vertex, QVector3D(vertex.position))
                        for vertex in mesh.vertices)
        elif getattr(group, "xform", None) is not None:
            orig_xforms.append((group, QMatrix4x4(group.xform)))
        else:
            targets = getattr(group, "children", []) or [group]
            for target in targets:
                mesh = getattr(target, "mesh", None)
                if mesh is not None and hasattr(mesh, "vertices"):
                    orig_vertices.extend(
                        (mesh, vertex, QVector3D(vertex.position))
                        for vertex in mesh.vertices)
    if not has_module:
        return False

    # scene.mesh (não loose_mesh): _verts pertencem à malha em edição.
    mesh = viewport.scene.mesh
    orig_vertices.extend(
        (mesh, vertex, QVector3D(vertex.position))
        for vertex in getattr(scale_tool, "_verts", []))
    scale_tool._orig_v = orig_vertices
    scale_tool._orig_x = orig_xforms
    scale_tool._orig_im = [
        (image, QVector3D(image.origin), QVector3D(image.u), QVector3D(image.v))
        for image in getattr(scale_tool, "_images", [])
    ]
    return True


# ---------------------------------------------------------------------------
# views.viewport
# ---------------------------------------------------------------------------

def prateleiras_obb(group: Any):
    """OBB do vão de prateleiras avulsas, ou ``None`` para o OBB nativo."""
    if not _is_trazomob_module(group):
        return None
    params = _module_params(group)
    if str(params.get("tipo", "")) != "peca_prateleiras_avulsas":
        return None
    import math
    from PySide6.QtGui import QVector3D

    width = float(params.get("largura", 800.0)) / 1000.0
    depth = float(params.get("profundidade", 300.0)) / 1000.0
    height = float(params.get("altura", 720.0)) / 1000.0
    rot_z = float(params.get("rot_z", 0.0))
    offset = params.get("offset", (0.0, 0.0, 0.0))
    rad = math.radians(rot_z)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    off = QVector3D(*offset)
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    for corner in (
        QVector3D(0.0, 0.0, 0.0), QVector3D(width, 0.0, 0.0),
        QVector3D(width, depth, 0.0), QVector3D(0.0, depth, 0.0),
        QVector3D(0.0, 0.0, height), QVector3D(width, 0.0, height),
        QVector3D(width, depth, height), QVector3D(0.0, depth, height),
    ):
        rx = corner.x() * cos_a - corner.y() * sin_a
        ry = corner.x() * sin_a + corner.y() * cos_a
        point = QVector3D(rx, ry, corner.z()) + off
        for i, value in enumerate((point.x(), point.y(), point.z())):
            if value < lo[i]:
                lo[i] = value
            if value > hi[i]:
                hi[i] = value
    frame = (QVector3D(1.0, 0.0, 0.0),
             QVector3D(0.0, 1.0, 0.0),
             QVector3D(0.0, 0.0, 1.0))
    return frame, tuple(lo), tuple(hi)


# ---------------------------------------------------------------------------
# Render: luzes e fitas LED
# ---------------------------------------------------------------------------

def preserve_led_extra(raw, cleaned: list) -> list:
    """Mantém os campos da fita LED que ``clean_lights`` não conhece."""
    raw_list = raw if isinstance(raw, list) else []
    for i, light in enumerate(cleaned):
        if i >= len(raw_list) or not isinstance(raw_list[i], dict):
            continue
        source = raw_list[i]
        for field in LED_EXTRA_FIELDS:
            if field in source and field not in light:
                light[field] = source[field]
        if source.get("kind") == "led_strip":
            light["kind"] = "led_strip"
    return cleaned


def expand_led_strips(lights):
    """Converte cada fita LED numa serie de pontos para o Blender."""
    expanded = []
    for light in lights or ():
        if not (isinstance(light, dict) and light.get("kind") == "led_strip"
                and "p1" in light and "p2" in light):
            expanded.append(light)
            continue
        if not light.get("on", True):
            continue
        p1, p2 = light["p1"], light["p2"]
        dx = float(p2[0]) - float(p1[0])
        dy = float(p2[1]) - float(p1[1])
        dz = float(p2[2]) - float(p1[2])
        length = (dx * dx + dy * dy + dz * dz) ** 0.5
        direction = light.get("dir", [0.0, 0.0, -1.0])
        norm = (float(direction[0]) ** 2 + float(direction[1]) ** 2
                + float(direction[2]) ** 2) ** 0.5
        normal = ((0.0, 0.0, -1.0) if norm < 1e-4 else
                  (float(direction[0]) / norm,
                   float(direction[1]) / norm,
                   float(direction[2]) / norm))
        count = max(2, min(10, int(round(length / 0.25))))
        sub_power = float(light.get("power", 350.0)) / count
        for k in range(count):
            frac = (k + 0.5) / count
            expanded.append({
                "kind": "point",
                "name": "%s #%d" % (light.get("name", "Fita LED"), k + 1),
                "pos": [
                    round(float(p1[0]) + dx * frac + normal[0] * 0.015, 4),
                    round(float(p1[1]) + dy * frac + normal[1] * 0.015, 4),
                    round(float(p1[2]) + dz * frac + normal[2] * 0.015, 4),
                ],
                "power": sub_power,
                "color": list(light.get("color", [1.0, 0.9, 0.8])),
                "on": True,
            })
    return expanded


def suppress_native_light_overlay() -> bool:
    """O visualizador do TrazoMob desenha as luzes com teste de oclusão."""
    return True


__all__ = [
    "LED_EXTRA_FIELDS", "prepare_copied_group", "rotate_module_command",
    "scale_module_command", "translate_module_command", "resolve_move_groups",
    "before_move_commit", "after_move_commit", "scale_factor_override",
    "promote_selection_modules", "prateleiras_bounds",
    "capture_module_originals", "prateleiras_obb", "preserve_led_extra",
    "expand_led_strips", "suppress_native_light_overlay",
]
