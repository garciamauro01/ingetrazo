# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors and Pair Programmer.
"""Ganchos de runtime que o TrazoMob precisa do IngeTrazo.

Ordem de preferência, sempre:

1. **API oficial de extensões** (``app.add_group_transform_hook``,
   ``add_group_copy_hook``, ``add_move_filter``, ``register_light_kind``).
   É o caminho normal num IngeTrazo atual e não toca no código do host.
2. **Monkeypatch registrado** (``platform.install_hook``) apenas para o que
   a API ainda não expõe — hoje, o snap de réguas no Scale, a captura de
   vértices do Scale e a sincronização de luzes após mover. Instala uma
   única vez, loga quando o atributo do host sumiu e pode ser revertido.

Assim o plugin funciona em hosts novos (API) e antigos (patch), e a dívida
de monkeypatch fica visível em ``platform.installed_hooks()``.
"""
from __future__ import annotations

import copy
import logging
import sys
from typing import Any

from . import platform as host

logger = logging.getLogger("trazomob.hooks")

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


# ---------------------------------------------------------------------------
# Entrada única
# ---------------------------------------------------------------------------

def apply_runtime_hooks(app=None) -> None:
    """Instala os ganchos; ``app`` é o ``ExtensionApp`` de ``setup``.

    Com ``app``, usa a API oficial e só recorre a monkeypatch no que ela não
    cobre. Sem ``app`` (teste, host antigo), instala tudo por patch.
    """
    official = _install_official(app)

    if not official.get("light_kind"):
        _patch_render_blender_lights()
    if not official.get("copy"):
        _patch_group_copy()
    if not official.get("move_filter"):
        _patch_move_lock()
    if not official.get("transform"):
        _patch_history_commands()

    # Pontos que a API de extensões ainda não expõe.
    _patch_move_commit()
    _patch_scale_tool()
    _patch_viewport_obb()

    # Itens de biblioteca como vínculo (geometria fora do .igz).
    from .library_links import install as install_library_links
    install_library_links(app=app)

    if host.installed_hooks():
        logger.debug("ganchos de patch ativos: %s",
                     ", ".join(host.installed_hooks()))


# ---------------------------------------------------------------------------
# API oficial de extensões
# ---------------------------------------------------------------------------

def _install_official(app) -> dict[str, bool]:
    """Registra na API oficial o que o host oferecer; devolve o que foi."""
    done: dict[str, bool] = {}
    if app is None:
        return done

    register_light = getattr(app, "register_light_kind", None)
    if callable(register_light):
        register_light("led_strip", 350.0, LED_EXTRA_FIELDS)
        done["light_kind"] = True

    add_copy_hook = getattr(app, "add_group_copy_hook", None)
    if callable(add_copy_hook):
        add_copy_hook(_on_group_copied)
        done["copy"] = True

    add_move_filter = getattr(app, "add_move_filter", None)
    if callable(add_move_filter):
        add_move_filter(_movable_groups)
        done["move_filter"] = True

    add_transform = getattr(app, "add_group_transform_hook", None)
    if callable(add_transform):
        add_transform(_official_transform)
        done["transform"] = True

    return done


def _on_group_copied(group: Any) -> None:
    if _is_trazomob_module(group):
        _unshare_trazomob_module_meshes(group)


def _movable_groups(groups: list) -> list:
    return [g for g in groups if not _motion_locked(g)]


def _official_transform(command: Any, scene: Any, phase: str) -> bool:
    """Move/gira/escala paramétricos pelo caminho oficial (do e undo)."""
    group = getattr(command, "group", None)
    if not _is_trazomob_module(group):
        return False

    from core.history import (MoveGroupCommand, RotateGroupCommand,
                              ScaleGroupCommand, invert_scale_factor)
    from ..builders.cabinet import CabinetBuilder

    forward = phase != "undo"

    if isinstance(command, RotateGroupCommand):
        CabinetBuilder.rotate_module(
            group, command.degrees if forward else -command.degrees,
            center=command.center, axis=command.axis, scene=scene,
            update_param=True)
        return True

    if isinstance(command, ScaleGroupCommand):
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
                b_now = get_module_carcass_bounds(group) or get_module_bounds(group)
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

    if isinstance(command, MoveGroupCommand):
        _translate_module(group, scene,
                          command.delta if forward else -command.delta)
        return True

    return False


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
# Reserva: core.render_blender (host sem register_light_kind)
# ---------------------------------------------------------------------------

def silence_native_light_overlay() -> None:
    """Desativa o overlay sem oclusão do render_blender nativo quando carregado."""
    import sys
    for mod_name, mod in list(sys.modules.items()):
        if (
            mod is not None
            and (mod_name == "plugins.render_blender" or mod_name.endswith(".render_blender"))
            and callable(getattr(mod, "draw_lights", None))
            and not getattr(mod, "_trazomob_overlay_silenced", False)
        ):
            def _make_draw_lights_guard(_orig):
                def _guarded_draw_lights(*_a, **_kw):
                    # O TrazoMobLightVisualizer já desenha todas as luzes com teste de oclusão.
                    return None
                return _guarded_draw_lights
            host.install_hook(f"render.overlay.{mod_name}", mod, "draw_lights", _make_draw_lights_guard)
            mod._trazomob_overlay_silenced = True


def _patch_render_blender_lights() -> None:
    rb = host.import_module("core.render_blender")
    if rb is None:
        return
    try:
        if "led_strip" not in rb.LIGHT_KINDS:
            rb.LIGHT_KINDS = (*rb.LIGHT_KINDS, "led_strip")
        if "led_strip" not in rb.DEFAULT_POWER:
            rb.DEFAULT_POWER["led_strip"] = 350.0
    except Exception:
        logger.exception("não foi possível estender os tipos de luz do host")

    def make_clean_lights(original):
        def hooked_clean_lights(raw):
            cleaned = original(raw)
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
        return hooked_clean_lights

    host.install_hook("render.led_lights", rb, "clean_lights", make_clean_lights)

    def make_write_job(original):
        def hooked_write_job(*args, **kwargs):
            lights = kwargs.get("lights")
            if lights:
                expanded = []
                for lt in lights:
                    if isinstance(lt, dict) and lt.get("kind") == "led_strip" and "p1" in lt and "p2" in lt:
                        if not lt.get("on", True):
                            continue
                        p1 = lt["p1"]
                        p2 = lt["p2"]
                        dx = float(p2[0]) - float(p1[0])
                        dy = float(p2[1]) - float(p1[1])
                        dz = float(p2[2]) - float(p1[2])
                        length = (dx * dx + dy * dy + dz * dz) ** 0.5
                        d_raw = lt.get("dir", [0.0, 0.0, -1.0])
                        dl = (float(d_raw[0]) ** 2 + float(d_raw[1]) ** 2 + float(d_raw[2]) ** 2) ** 0.5
                        if dl < 1e-4:
                            dn = (0.0, 0.0, -1.0)
                        else:
                            dn = (float(d_raw[0]) / dl, float(d_raw[1]) / dl, float(d_raw[2]) / dl)
                        n_pts = max(2, min(10, int(round(length / 0.25))))
                        sub_power = float(lt.get("power", 350.0)) / n_pts
                        for k in range(n_pts):
                            frac = (k + 0.5) / n_pts
                            pt_pos = [
                                round(float(p1[0]) + dx * frac + dn[0] * 0.015, 4),
                                round(float(p1[1]) + dy * frac + dn[1] * 0.015, 4),
                                round(float(p1[2]) + dz * frac + dn[2] * 0.015, 4),
                            ]
                            expanded.append({
                                "kind": "point",
                                "name": f"{lt.get('name', 'Fita LED')} #{k + 1}",
                                "pos": pt_pos,
                                "power": sub_power,
                                "color": list(lt.get("color", [1.0, 0.9, 0.8])),
                                "on": True,
                            })
                    else:
                        expanded.append(lt)
                kwargs["lights"] = expanded
            return original(*args, **kwargs)
        return hooked_write_job

    if hasattr(rb, "write_job"):
        host.install_hook("render.write_job", rb, "write_job", make_write_job)

    silence_native_light_overlay()


# ---------------------------------------------------------------------------
# Reserva: core.group.copy_group
# ---------------------------------------------------------------------------

def _unshare_trazomob_module_meshes(group: Any) -> None:
    """Dá malha própria a cada peça filha de um módulo copiado, para que
    girar/editar a cópia não afete o original."""
    from core.group import transformed_mesh
    from PySide6.QtGui import QMatrix4x4

    identity = QMatrix4x4()

    def _walk(node):
        for child in getattr(node, "children", []) or []:
            if getattr(child, "mesh", None) is not None:
                child.mesh = transformed_mesh(child.mesh, identity)
            _walk(child)

    _walk(group)


def _patch_group_copy() -> None:
    grp_mod = host.import_module("core.group")
    if grp_mod is None:
        return

    def make_copy_group(original):
        def hooked_copy_group(group, delta=None, _in_definition=False):
            new_group = original(group, delta=delta, _in_definition=_in_definition)
            _on_group_copied(new_group)
            return new_group
        return hooked_copy_group

    if not host.install_hook("group.copy", grp_mod, "copy_group", make_copy_group):
        return

    patched = getattr(grp_mod, "copy_group")
    for module_name in ("tools.move", "tools.rotate", "tools.paste", "tools.flip"):
        module = sys.modules.get(module_name)
        if module is not None:
            try:
                setattr(module, "copy_group", patched)
            except Exception:
                logger.debug("copy_group não atualizado em %s", module_name)


# ---------------------------------------------------------------------------
# Reserva: tools.move (trava) e pós-movimento (sempre por patch)
# ---------------------------------------------------------------------------

def _find_top_module_for_group(group: Any, scene: Any) -> Any:
    """Se group for uma peça-filha ou parte de um módulo TrazoMob, retorna o módulo-pai."""
    if group is None:
        return None
    if _is_trazomob_module(group):
        return group
    owner = getattr(group, "owner", None)
    if owner is not None and _is_trazomob_module(owner):
        return owner
    if scene and hasattr(scene, "groups"):
        for g in scene.groups:
            if _is_trazomob_module(g):
                if group in (getattr(g, "children", []) or []) or getattr(group, "owner", None) is g:
                    return g
    return group


def _patch_move_lock() -> None:
    move_mod = host.import_module("tools.move")
    if move_mod is None:
        return

    def make_gather_targets(original):
        def hooked_gather_targets(ctx):
            groups, positions = original(ctx)
            # Resolve peças avulsas ou internas para o módulo-pai correspondente
            scene = getattr(ctx.viewport, "scene", None)
            resolved_groups = []
            for g in groups:
                top_m = _find_top_module_for_group(g, scene)
                if top_m is not None and top_m not in resolved_groups:
                    resolved_groups.append(top_m)
                elif top_m is None and g not in resolved_groups:
                    resolved_groups.append(g)
            return _movable_groups(resolved_groups), positions
        return hooked_gather_targets

    if host.install_hook("move.lock", move_mod, "gather_targets",
                         make_gather_targets):
        patched = move_mod.gather_targets
        for module_name in ("tools.rotate", "tools.scale"):
            module = sys.modules.get(module_name)
            if module is not None:
                setattr(module, "gather_targets", patched)


def _patch_move_commit() -> None:
    move_mod = host.import_module("tools.move")
    if move_mod is None:
        return
    from PySide6.QtGui import QVector3D
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    def hook_post_move(original):
        def hooked_commit(self, viewport, delta: QVector3D):
            # Se a tecla Control NÃO estiver fisicamente pressionada agora,
            # garante que o modo de cópia não fique armado indevidamente.
            mods = QApplication.keyboardModifiers()
            if not bool(mods & Qt.ControlModifier):
                self._copy = False

            original(self, viewport, delta)
            # Isolamento estrito: só sincroniza luzes se a seleção contiver alguma entidade TrazoMob ou luz
            try:
                sc = getattr(viewport, "scene", None)
                sel = getattr(sc, "selection", ()) if sc else ()
                has_trazomob = any(
                    _is_trazomob_module(ent) or (
                        hasattr(ent, "ext") and isinstance(ent.ext, dict) and any(
                            k in ent.ext for k in ("trazomob_light", "atomic_light", "trazomob_wall", "trazomob_esquadria")
                        )
                    )
                    for ent in sel
                )
                if has_trazomob:
                    from ..render.lighting import sync_scene_lights_to_document
                    sync_scene_lights_to_document(viewport)
            except Exception as exc:
                logger.debug("sincronização das luzes falhou após mover: %s", exc)
        return hooked_commit

    move_tool = getattr(move_mod, "MoveTool", None)
    if move_tool is not None:
        host.install_hook("move.commit", move_tool, "_commit", hook_post_move)


# ---------------------------------------------------------------------------
# Reserva: tools.scale (snap de réguas e captura paramétrica)
# ---------------------------------------------------------------------------

def _patch_scale_tool() -> None:
    scale_mod = host.import_module("tools.scale")
    if scale_mod is None:
        return
    scale_tool = getattr(scale_mod, "ScaleTool", None)
    if scale_tool is None:
        return

    def make_factors_for(original):
        def hooked_factors_for(self, ctx, viewport, sx, sy):
            got = original(self, ctx, viewport, sx, sy)

            # Um ponto nomeado (endpoint, midpoint...) vence: o usuário mirou nele.
            try:
                if self._snapped_point(ctx) is not None:
                    return got
            except Exception:
                logger.debug("Falha ao avaliar ponto de snap nomeado", exc_info=True)

            groups = getattr(self, "_groups", [])

            def _is_esquadria(group):
                ext = getattr(group, "ext", None)
                if isinstance(ext, dict) and "trazomob_esquadria" in ext:
                    return True
                return getattr(group, "layer", "") == "ESQUADRIAS"

            if not any(_is_trazomob_module(g) for g in groups):
                return got
            if any(_is_esquadria(g) for g in groups):
                return got

            grip = getattr(self, "_grip", None)
            anchor = getattr(self, "_anchor", None)
            if grip is None or 2 not in grip.mask or anchor is None:
                return got
            try:
                from ..wall.guides import WallGuideRulerManager
                from PySide6.QtGui import QVector3D

                ruler_mgr = WallGuideRulerManager.get_instance()
                if not (ruler_mgr.visible and ruler_mgr.snap_enabled):
                    return got
                factors_est = self._factors_from_cursor(viewport, sx, sy)
                if factors_est is None:
                    return got
                grip_pos = self._grip_pos(grip)
                est_z = anchor.z() + (grip_pos.z() - anchor.z()) * factors_est[2]
                snap_res = ruler_mgr.snap_to_levels(est_z, threshold_m=0.08)
                if snap_res is None:
                    return got
                snapped = QVector3D(grip_pos.x(), grip_pos.y(), snap_res[0])
                return self._factors_from_point(snapped) or got
            except Exception as exc:
                logger.debug("snap de nível no Scale falhou: %s", exc)
                return got
        return hooked_factors_for

    host.install_hook("scale.ruler_snap", scale_tool, "_factors_for", make_factors_for)

    def _promote_selection_modules(viewport):
        sc = getattr(viewport, 'scene', None)
        if sc is None or not getattr(sc, 'selection', None):
            return
        to_replace = []
        for ent in sc.selection:
            owner = getattr(ent, 'owner', None)
            if owner is not None and _is_trazomob_module(owner):
                to_replace.append((ent, owner))
        for old_ent, master in to_replace:
            sc.selection.discard(old_ent)
            sc.selection.add(master)

    def make_on_activate(original):
        def hooked_on_activate(self, viewport):
            _promote_selection_modules(viewport)
            return original(self, viewport)
        return hooked_on_activate

    host.install_hook('scale.on_activate', scale_tool, 'on_activate', make_on_activate)

    def make_selection_bounds(original):
        def hooked_selection_bounds(self, viewport):
            import math
            from PySide6.QtGui import QVector3D
            from core.group import Group

            sc = getattr(viewport, "scene", None)
            sel = list(getattr(sc, "selection", [])) if sc else []
            # Verifica se há módulo de prateleiras avulsas na seleção
            prat_mods = [
                g for g in sel if isinstance(g, Group) and _is_trazomob_module(g)
                and str(_module_params(g).get("tipo", "")) == "peca_prateleiras_avulsas"
            ]
            if prat_mods:
                self._pick_frame(viewport)
                lo = [float("inf")] * 3
                hi = [float("-inf")] * 3

                def absorb(p: QVector3D) -> None:
                    p = self._to_local(p)
                    for i, c in enumerate((p.x(), p.y(), p.z())):
                        if c < lo[i]:
                            lo[i] = c
                        if c > hi[i]:
                            hi[i] = c

                for mod in prat_mods:
                    p_meta = _module_params(mod)
                    L_m = float(p_meta.get("largura", 800.0)) / 1000.0
                    P_m = float(p_meta.get("profundidade", 300.0)) / 1000.0
                    A_m = float(p_meta.get("altura", 720.0)) / 1000.0
                    rot_z = float(p_meta.get("rot_z", 0.0))
                    off = p_meta.get("offset", (0.0, 0.0, 0.0))

                    rad = math.radians(rot_z)
                    cos_a, sin_a = math.cos(rad), math.sin(rad)
                    off_v = QVector3D(*off)

                    # Os 8 vértices locais do volume do vão delimitado
                    for c in (
                        QVector3D(0.0, 0.0, 0.0),
                        QVector3D(L_m, 0.0, 0.0),
                        QVector3D(L_m, P_m, 0.0),
                        QVector3D(0.0, P_m, 0.0),
                        QVector3D(0.0, 0.0, A_m),
                        QVector3D(L_m, 0.0, A_m),
                        QVector3D(L_m, P_m, A_m),
                        QVector3D(0.0, P_m, A_m),
                    ):
                        rx = c.x() * cos_a - c.y() * sin_a
                        ry = c.x() * sin_a + c.y() * cos_a
                        absorb(QVector3D(rx, ry, c.z()) + off_v)

                # Absorve quaisquer outras entidades selecionadas junto
                other_ents = [e for e in sel if e not in prat_mods]
                if other_ents:
                    from core.group import iter_placements
                    from core.image_plane import ImagePlane
                    from core.mesh import Edge, Face
                    for ent in other_ents:
                        if isinstance(ent, Edge):
                            absorb(ent.a)
                            absorb(ent.b)
                        elif isinstance(ent, Face):
                            for v in ent.vertices:
                                absorb(v)
                        elif isinstance(ent, ImagePlane):
                            for c in ent.corners():
                                absorb(c)
                        elif hasattr(ent, "mesh"):
                            for pg, m in iter_placements(ent):
                                for v in pg.mesh.vertices:
                                    p = m.map(v.position) if m is not None else v.position
                                    absorb(p)

                return QVector3D(*lo), QVector3D(*hi)

            return original(self, viewport)
        return hooked_selection_bounds

    host.install_hook("scale.selection_bounds", scale_tool, "_selection_bounds", make_selection_bounds)

    def make_capture_originals(original):
        def hooked_capture_originals(self, viewport):
            from PySide6.QtGui import QMatrix4x4, QVector3D

            orig_vertices = []
            orig_xforms = []
            has_module = False
            for group in getattr(self, "_groups", []):
                if _is_trazomob_module(group):
                    has_module = True
                    targets = getattr(group, "children", []) or [group]
                    for target in targets:
                        mesh = getattr(target, "mesh", None)
                        if mesh is not None and hasattr(mesh, "vertices"):
                            orig_vertices.extend(
                                (mesh, v, QVector3D(v.position)) for v in mesh.vertices)
                elif getattr(group, "xform", None) is not None:
                    orig_xforms.append((group, QMatrix4x4(group.xform)))
                else:
                    targets = getattr(group, "children", []) or [group]
                    for target in targets:
                        mesh = getattr(target, "mesh", None)
                        if mesh is not None and hasattr(mesh, "vertices"):
                            orig_vertices.extend(
                                (mesh, v, QVector3D(v.position)) for v in mesh.vertices)

            if not has_module:
                original(self, viewport)
                return

            # scene.mesh (não loose_mesh) de propósito: _verts pertencem à
            # malha em edição.
            mesh = viewport.scene.mesh
            orig_vertices.extend(
                (mesh, v, QVector3D(v.position)) for v in getattr(self, "_verts", []))
            self._orig_v = orig_vertices
            self._orig_x = orig_xforms
            self._orig_im = [
                (im, QVector3D(im.origin), QVector3D(im.u), QVector3D(im.v))
                for im in getattr(self, "_images", [])
            ]
        return hooked_capture_originals

    host.install_hook("scale.capture", scale_tool, "_capture_originals",
                      make_capture_originals)


def _patch_viewport_obb() -> None:
    vp_mod = host.import_module("views.viewport")
    if vp_mod is None:
        return
    vp_cls = getattr(vp_mod, "Viewport", None)
    if vp_cls is None:
        return

    def make_group_obb(original):
        def hooked_group_obb(self, group):
            if _is_trazomob_module(group):
                p_meta = _module_params(group)
                if str(p_meta.get("tipo", "")) == "peca_prateleiras_avulsas":
                    import math
                    from PySide6.QtGui import QVector3D
                    from core.group import group_frame

                    L_m = float(p_meta.get("largura", 800.0)) / 1000.0
                    P_m = float(p_meta.get("profundidade", 300.0)) / 1000.0
                    A_m = float(p_meta.get("altura", 720.0)) / 1000.0
                    rot_z = float(p_meta.get("rot_z", 0.0))
                    off = p_meta.get("offset", (0.0, 0.0, 0.0))

                    rad = math.radians(rot_z)
                    cos_a, sin_a = math.cos(rad), math.sin(rad)
                    off_v = QVector3D(*off)

                    lo = [float("inf")] * 3
                    hi = [float("-inf")] * 3
                    for c in (
                        QVector3D(0.0, 0.0, 0.0),
                        QVector3D(L_m, 0.0, 0.0),
                        QVector3D(L_m, P_m, 0.0),
                        QVector3D(0.0, P_m, 0.0),
                        QVector3D(0.0, 0.0, A_m),
                        QVector3D(L_m, 0.0, A_m),
                        QVector3D(L_m, P_m, A_m),
                        QVector3D(0.0, P_m, A_m),
                    ):
                        rx = c.x() * cos_a - c.y() * sin_a
                        ry = c.x() * sin_a + c.y() * cos_a
                        p_w = QVector3D(rx, ry, c.z()) + off_v
                        for i, val in enumerate((p_w.x(), p_w.y(), p_w.z())):
                            if val < lo[i]:
                                lo[i] = val
                            if val > hi[i]:
                                hi[i] = val

                    frame = (QVector3D(1.0, 0.0, 0.0), QVector3D(0.0, 1.0, 0.0), QVector3D(0.0, 0.0, 1.0))
                    return frame, tuple(lo), tuple(hi)

            return original(self, group)
        return hooked_group_obb

    host.install_hook("viewport.group_obb", vp_cls, "_group_obb", make_group_obb)


# ---------------------------------------------------------------------------
# Reserva: core.history (host sem add_group_transform_hook)
# ---------------------------------------------------------------------------

def _patch_history_commands() -> None:
    history = host.import_module("core.history")
    if history is None:
        return

    from ..builders.cabinet import CabinetBuilder

    def make_rotate(degrees_sign):
        def factory(original):
            def hooked(self, scene):
                if _is_trazomob_module(self.group):
                    CabinetBuilder.rotate_module(
                        self.group, degrees_sign * self.degrees,
                        center=self.center, axis=self.axis, scene=scene,
                        update_param=True)
                    return
                original(self, scene)
            return hooked
        return factory

    if hasattr(history, "RotateGroupCommand"):
        host.install_hook("history.rotate.do", history.RotateGroupCommand, "do",
                          make_rotate(1))
        host.install_hook("history.rotate.undo", history.RotateGroupCommand, "undo",
                          make_rotate(-1))

    def make_scale(forward):
        def factory(original):
            def hooked(self, scene):
                if not _is_trazomob_module(self.group):
                    original(self, scene)
                    return
                if forward:
                    if getattr(self, "_mod_params_before", None) is None:
                        self._mod_params_before = copy.deepcopy(
                            _module_params(self.group))
                    if getattr(self, "_mod_children_before", None) is None:
                        self._mod_children_before = list(getattr(self.group, "children", []))
                    if getattr(self, "_mod_name_before", None) is None:
                        self._mod_name_before = getattr(self.group, "name", "")
                    CabinetBuilder.scale_module(
                        self.group, self.center, self.factor, axes=self.axes,
                        scene=scene, update_param=True, rebuild=True)
                else:
                    if getattr(self, "_mod_params_before", None) is not None:
                        params_prev = copy.deepcopy(self._mod_params_before)
                        self.group.ext[_get_module_key(self.group)] = params_prev
                        from ..domain.module_geometry import get_module_carcass_bounds
                        from ..interaction.magnetic_drag import get_module_bounds
                        b_now = get_module_carcass_bounds(self.group) or get_module_bounds(self.group)
                        CabinetBuilder._rebuild_scaled_module_pieces(self.group, params_prev, b_now)
                    elif getattr(self, "_mod_children_before", None) is not None:
                        self.group.children = list(self._mod_children_before)
                    if getattr(self, "_mod_name_before", None) is not None:
                        self.group.name = self._mod_name_before
                    from core.history import _dirty_group_chunks
                    if scene is not None:
                        _dirty_group_chunks(scene)
                        scene.version += 1
            return hooked
        return factory

    if hasattr(history, "ScaleGroupCommand"):
        host.install_hook("history.scale.do", history.ScaleGroupCommand, "do",
                          make_scale(True))
        host.install_hook("history.scale.undo", history.ScaleGroupCommand, "undo",
                          make_scale(False))

    def make_translate(original):
        def hooked(self, scene, delta):
            if not _is_trazomob_module(self.group):
                original(self, scene, delta)
                return
            _translate_module(self.group, scene, delta)
        return hooked

    if hasattr(history, "MoveGroupCommand"):
        host.install_hook("history.move", history.MoveGroupCommand,
                          "_shift", make_translate)
