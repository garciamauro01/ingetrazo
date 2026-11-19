# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Interacao de entrada, arraste e comandos reversiveis para o filtro de drag."""

from __future__ import annotations

import logging
import math
from typing import List, Optional, Tuple

from PySide6.QtCore import QObject, QEvent, Qt, QPointF, QRectF
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QVector3D, QMouseEvent

from core.group import Group
from core.history import Command, MoveGroupCommand, CompoundCommand

from .magnetic_drag_snap import get_module_bounds, get_module_reference_bounds

logger = logging.getLogger("trazomob.magnetic_drag")


def _intersect_ray_aabb(
    orig: QVector3D,
    dirc: QVector3D,
    bounds: Tuple[float, float, float, float, float, float],
) -> Optional[QVector3D]:
    """Intersecciona um raio com uma caixa AABB (método dos planos) retornando o ponto frontal."""
    b_min = (bounds[0], bounds[2], bounds[4])
    b_max = (bounds[1], bounds[3], bounds[5])
    o_vals = (orig.x(), orig.y(), orig.z())
    d_vals = (dirc.x(), dirc.y(), dirc.z())

    t_near = float("-inf")
    t_far = float("inf")
    for i in range(3):
        if abs(d_vals[i]) < 1e-8:
            if o_vals[i] < b_min[i] or o_vals[i] > b_max[i]:
                return None
        else:
            inv_d = 1.0 / d_vals[i]
            t1 = (b_min[i] - o_vals[i]) * inv_d
            t2 = (b_max[i] - o_vals[i]) * inv_d
            if t1 > t2:
                t1, t2 = t2, t1
            t_near = max(t_near, t1)
            t_far = min(t_far, t2)
            if t_near > t_far or t_far < 0.0:
                return None

    t_hit = t_near if t_near > 1e-4 else t_far
    if t_hit <= 1e-4 or not math.isfinite(t_hit):
        return None
    return orig + dirc * t_hit


def _point_in_bounds(
    pt: QVector3D,
    bounds: Tuple[float, float, float, float, float, float],
    margin: float = 0.0,
) -> bool:
    """Verifica se um ponto 3D está contido dentro de bounds expandido por margin."""
    min_x, max_x, min_y, max_y, min_z, max_z = bounds
    return (
        (min_x - margin) <= pt.x() <= (max_x + margin)
        and (min_y - margin) <= pt.y() <= (max_y + margin)
        and (min_z - margin) <= pt.z() <= (max_z + margin)
    )


def _prevent_camera_inside_module(
    orig_bounds: Tuple[float, float, float, float, float, float],
    delta: QVector3D,
    eye_pos: QVector3D,
    margin_xy: float = 0.05,
    margin_z: float = 0.02,
) -> QVector3D:
    """Impede que o deslocamento envolva o olho da câmera perspectiva dentro do módulo."""
    min_x, max_x, min_y, max_y, min_z, max_z = orig_bounds
    dx, dy, dz = delta.x(), delta.y(), delta.z()
    ex, ey, ez = eye_pos.x(), eye_pos.y(), eye_pos.z()

    if not ((min_z + dz - margin_z) <= ez <= (max_z + dz + margin_z)):
        return delta
    if not ((min_x + dx - margin_xy) < ex < (max_x + dx + margin_xy)):
        return delta
    if not ((min_y + dy - margin_xy) < ey < (max_y + dy + margin_xy)):
        return delta

    # Empurra minimamente no eixo horizontal com menor penetração para manter o móvel visível diante da câmera
    push_left = (ex - margin_xy) - (max_x + dx)
    push_right = (ex + margin_xy) - (min_x + dx)
    push_front = (ey - margin_xy) - (max_y + dy)
    push_back = (ey + margin_xy) - (min_y + dy)

    candidates = [
        (abs(push_left), QVector3D(dx + push_left, dy, dz)),
        (abs(push_right), QVector3D(dx + push_right, dy, dz)),
        (abs(push_front), QVector3D(dx, dy + push_front, dz)),
        (abs(push_back), QVector3D(dx, dy + push_back, dz)),
    ]
    _, best_delta = min(candidates, key=lambda item: item[0])
    return best_delta


class FastTranslateGroupCommand(Command):
    """Translada de forma ultrarrápida (em lote) os vértices de um grupo clássico e atualiza metadados cinemáticos."""

    keeps_paint = True

    def __init__(self, group: Group, delta: QVector3D) -> None:
        self.group = group
        self.delta = QVector3D(delta)

    def _shift(self, scene, delta: QVector3D) -> None:
        g = self.group
        if getattr(g, "xform", None) is not None and not getattr(g, "children", None):
            from PySide6.QtGui import QMatrix4x4
            t = QMatrix4x4()
            t.translate(delta)
            g.xform = t * g.xform
            scene.version += 1
            return

        mesh = getattr(g, "mesh", None)
        if mesh is not None and getattr(mesh, "vertices", None):
            from core.topology import _key
            from core.group import _remap_uvws, carry_axes
            from PySide6.QtGui import QMatrix4x4
            dx, dy, dz = delta.x(), delta.y(), delta.z()
            for v in mesh.vertices:
                p = v.position
                v.position = QVector3D(p.x() + dx, p.y() + dy, p.z() + dz)
            mesh._registry = {_key(v.position): v for v in mesh.vertices}
            if hasattr(mesh, "_displaced"):
                mesh._displaced.clear()
            mesh._chunk_dirty = True
            mesh._mut_serial = getattr(mesh, "_mut_serial", 0) + 1
            t = QMatrix4x4()
            t.translate(delta)
            _remap_uvws(mesh, t)
            carry_axes(g, t)

        ext = getattr(g, "ext", None)
        if isinstance(ext, dict):
            if "orig_vertices" in ext and isinstance(ext["orig_vertices"], list):
                ext["orig_vertices"] = [orig + delta for orig in ext["orig_vertices"]]
            if "hinge_pivot" in ext and isinstance(ext["hinge_pivot"], QVector3D):
                ext["hinge_pivot"] = ext["hinge_pivot"] + delta

        scene.version += 1

    def do(self, scene) -> None:
        self._shift(scene, self.delta)

    def undo(self, scene) -> None:
        self._shift(scene, -self.delta)


class MagneticDragInputMixin:
    """Interacao de entrada, arraste com snap magnetico e comandos reversiveis."""

    def _is_select_tool_active(self) -> bool:
        """Retorna True apenas se a ferramenta ativa no Viewport for a de Seleção
        e nenhuma ferramenta de navegação de câmera (Orbit, Pan, Zoom, etc.) estiver ativa.
        Quando ferramentas como Move (M), Rotate (Q), Line (L), Tape, ou modos de câmera
        (nav_mode = 'orbit' / 'pan' / 'zoom' / 'zoom_window') estão ativos,
        o filtro magnético NÃO deve interceptar cliques nem desviar a seleção/câmera!
        """
        if getattr(self.viewport, "nav_mode", None) is not None:
            return False
        if getattr(self.viewport, "_middle_drag_active", False):
            return False
        if getattr(self.viewport, "_look_drag", None) is not None:
            return False
        tool = getattr(self.viewport, "active_tool", None)
        if tool is None:
            tool = getattr(self.viewport, "tool", None)
        if tool is None:
            return True
        tname = getattr(tool, "name", "")
        return tname in ("Select", "")

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is not self.viewport:
            return super().eventFilter(watched, event)

        etype = event.type()
        if etype == QEvent.Wheel:
            from .free_zoom import FreeZoomManager
            if FreeZoomManager.handle_wheel_event(self.viewport, event):
                return True

        if etype == QEvent.MouseButtonPress and isinstance(event, QMouseEvent):
            if event.button() == Qt.LeftButton:
                if not self._is_select_tool_active():
                    self._mouse_pressed = False
                    self._drag_active = False
                    self._target_module = None
                    return False

                mods = event.modifiers()
                is_multi = bool(mods & (Qt.ControlModifier | Qt.ShiftModifier))

                from ..wall.selection import WallSelectionManager
                wall_mgr = WallSelectionManager.get_instance(self.viewport)
                pos_x, pos_y = event.position().x(), event.position().y()
                # 0. Tenta primeiro verificar se clicou numa fonte de luz física (spot, cone, lâmpada ou fita LED)
                from ..render.lighting import TrazoMobLightVisualizer, _get_document_lights
                light_pick = TrazoMobLightVisualizer.pick_light_or_target(self.viewport, pos_x, pos_y)
                if light_pick is not None:
                    action, light_idx = light_pick
                    TrazoMobLightVisualizer.on_light_clicked(light_pick, self.viewport, click_pos=(pos_x, pos_y))
                    wall_mgr.clear_selection()
                    # Encontra o grupo 3D correspondente na cena para colocar na seleção ativa
                    doc_lights = _get_document_lights(self.viewport)
                    target_grp = None
                    if 0 <= light_idx < len(doc_lights):
                        lt_data = doc_lights[light_idx]
                        sc = getattr(self.viewport, "scene", None)
                        if sc and hasattr(sc, "groups"):
                            for g in sc.groups:
                                ext = getattr(g, "ext", None)
                                if isinstance(ext, dict) and "trazomob_light" in ext:
                                    g_lt = ext["trazomob_light"]
                                    if g_lt.get("pos") == lt_data.get("pos") and g_lt.get("kind") == lt_data.get("kind"):
                                        target_grp = g
                                        break
                    if target_grp is not None and hasattr(self.viewport, "scene"):
                        if hasattr(self.viewport.scene, "select"):
                            self.viewport.scene.select([target_grp], mode="add" if is_multi else "replace")
                        else:
                            self.viewport.scene.selection = {target_grp}
                        if hasattr(self.viewport, "notify_scene_changed"):
                            self.viewport.notify_scene_changed()
                        else:
                            self.viewport.update()
                    # Notifica a barra lateral para abrir a edição da luz diretamente
                    sidebar = getattr(self.viewport, "_trazomob_sidebar", None)
                    if sidebar is not None:
                        if target_grp is not None:
                            sidebar.load_light_group(target_grp)
                        else:
                            sidebar.load_light(light_idx)
                    return True

                # 1. Verifica primeiro se clicou num módulo/móvel (por face ou aresta via pick_group)
                hit_grp = self.viewport.pick_group(pos_x, pos_y) if hasattr(self.viewport, "pick_group") else None
                top_mod = self._find_top_module(hit_grp)
                if top_mod is not None and not (hasattr(top_mod, "ext") and isinstance(top_mod.ext, dict) and "trazomob_wall" in top_mod.ext):
                    # Clicou no móvel (não na parede): desarma o frame de próxima inserção na parede
                    wall_mgr.clear_placement_frame()
                    adj = self._find_adjacent_wall_face(top_mod)
                    if adj is not None:
                        adj_wall, adj_face = adj
                        # Seleciona a parede visualmente no 3D sem roubar o contexto da barra lateral do móvel
                        wall_mgr.set_selected_face(adj_wall, adj_face, notify_sidebar=False)
                    else:
                        wall_mgr.clear_selection()
                elif hit_grp is not None and not (hasattr(hit_grp, "ext") and isinstance(hit_grp.ext, dict) and "trazomob_wall" in hit_grp.ext):
                    # Clicou em outro objeto qualquer (bancada solta, eletro, decoração, piso) -> limpa seleção/frame
                    wall_mgr.clear_selection()
                elif wall_mgr.handle_click(pos_x, pos_y):
                    # Se clicou diretamente numa parede, seleciona a parede na cena também (se não for multi-seleção)
                    if wall_mgr.selected_wall_face and not is_multi:
                        wall_grp = wall_mgr.selected_wall_face.wall_group
                        if hasattr(self.viewport, "scene"):
                            self.viewport.scene.selection = {wall_grp}
                            self.viewport.update()
                else:
                    # Se clicou no vazio ou num objeto que não é parede nem móvel encostado, limpa
                    face, grp = self.viewport.pick_face_any(pos_x, pos_y) if hasattr(self.viewport, "pick_face_any") else (None, None)
                    if grp is None or not (hasattr(grp, "ext") and isinstance(grp.ext, dict) and "trazomob_wall" in grp.ext):
                        wall_mgr.clear_selection()

                if self._handle_press(event):
                    return False

        elif etype == QEvent.MouseButtonDblClick and isinstance(event, QMouseEvent):
            if event.button() == Qt.LeftButton and self._is_select_tool_active():
                pos_x, pos_y = event.position().x(), event.position().y()
                from ..wall.selection import WallSelectionManager
                wall_mgr = WallSelectionManager.get_instance(self.viewport)
                if wall_mgr.handle_double_click(pos_x, pos_y):
                    # Seleciona também a parede na cena se tiver
                    if wall_mgr.selected_wall_face:
                        wall_grp = wall_mgr.selected_wall_face.wall_group
                        if hasattr(self.viewport, "scene"):
                            self.viewport.scene.selection = {wall_grp}
                            self.viewport.update()
                    return True

        elif etype == QEvent.MouseMove and isinstance(event, QMouseEvent):
            if self._mouse_pressed and self._is_select_tool_active():
                if self._handle_move(event):
                    return True  # Intercepta e consome o evento evitando seleção retangular!

        elif etype == QEvent.MouseButtonRelease and isinstance(event, QMouseEvent):
            if event.button() == Qt.LeftButton and (self._mouse_pressed or self._drag_active):
                if not self._is_select_tool_active():
                    self._mouse_pressed = False
                    self._drag_active = False
                    self._target_module = None
                    return False
                if self._handle_release(event):
                    return True

        elif etype == QEvent.KeyPress and (self._mouse_pressed or self._drag_active):
            from PySide6.QtGui import QKeyEvent
            if isinstance(event, QKeyEvent):
                key = event.key()
                # Setas Up / Down: Trava no eixo Vertical (Z)
                if key in (Qt.Key_Up, Qt.Key_Down):
                    if self._axis_lock == "z":
                        self._axis_lock = None
                        if hasattr(self.viewport, "flash_status"):
                            self.viewport.flash_status("🔓 Trava de eixo liberada")
                    else:
                        self._axis_lock = "z"
                        if hasattr(self.viewport, "flash_status"):
                            self.viewport.flash_status("🔒 Eixo Vertical (Z) travado pelas setas [Cima/Baixo]")
                    if self._last_event_pos is not None:
                        self._recompute_from_pos(self._last_event_pos)
                    return True

                # Setas Left / Right: Trava no eixo Horizontal (ao longo da parede / X/Y)
                elif key in (Qt.Key_Left, Qt.Key_Right):
                    if self._axis_lock == "u":
                        self._axis_lock = None
                        if hasattr(self.viewport, "flash_status"):
                            self.viewport.flash_status("🔓 Trava de eixo liberada")
                    else:
                        self._axis_lock = "u"
                        if hasattr(self.viewport, "flash_status"):
                            self.viewport.flash_status("🔒 Eixo Horizontal (ao longo da parede) travado [Esq/Dir]")
                    if self._last_event_pos is not None:
                        self._recompute_from_pos(self._last_event_pos)
                    return True

                elif key == Qt.Key_Escape:
                    if self._axis_lock is not None:
                        self._axis_lock = None
                        if hasattr(self.viewport, "flash_status"):
                            self.viewport.flash_status("🔓 Trava de eixo liberada (Esc)")
                        if self._last_event_pos is not None:
                            self._recompute_from_pos(self._last_event_pos)
                        return True


        # ── EVENTOS DE DRAG & DROP DA BARRA DE MÓDULOS (RIBBON) ──
        elif etype in (QEvent.DragEnter, QEvent.DragMove):
            from .drag_drop_handler import TRAZOMOB_MIME_MODULE, TRAZOMOB_MIME_DECORATION, compute_drop_placement
            mime = event.mimeData() if hasattr(event, "mimeData") else None
            if mime and (mime.hasFormat(TRAZOMOB_MIME_MODULE) or mime.hasFormat(TRAZOMOB_MIME_DECORATION)):
                event.acceptProposedAction()
                if mime.hasFormat(TRAZOMOB_MIME_MODULE):
                    try:
                        import json
                        raw_data = bytes(mime.data(TRAZOMOB_MIME_MODULE)).decode("utf-8")
                        mod_data = json.loads(raw_data)
                        pos = event.position() if hasattr(event, "position") else event.pos()
                        offset, rot_z, wall = compute_drop_placement(self.viewport, pos, mod_data)
                        self._active_drop_preview = {
                            "mod_data": mod_data,
                            "offset": offset,
                            "rot_z": rot_z,
                            "wall": wall,
                        }
                        self.viewport.update()
                    except Exception:
                        logger.debug("Falha ao calcular preview de drop do módulo", exc_info=True)
                return True

        elif etype == QEvent.DragLeave:
            if getattr(self, "_active_drop_preview", None) is not None:
                self._active_drop_preview = None
                self.viewport.update()
            return False

        elif etype == QEvent.Drop:
            from .drag_drop_handler import TRAZOMOB_MIME_MODULE, TRAZOMOB_MIME_DECORATION, compute_drop_placement
            mime = event.mimeData() if hasattr(event, "mimeData") else None
            if mime and (mime.hasFormat(TRAZOMOB_MIME_MODULE) or mime.hasFormat(TRAZOMOB_MIME_DECORATION)):
                pos = event.position() if hasattr(event, "position") else event.pos()
                self._active_drop_preview = None
                if mime.hasFormat(TRAZOMOB_MIME_MODULE):
                    try:
                        import json
                        raw_data = bytes(mime.data(TRAZOMOB_MIME_MODULE)).decode("utf-8")
                        mod_data = json.loads(raw_data)
                        offset, rot_z, wall = compute_drop_placement(self.viewport, pos, mod_data)
                        mod_data_placed = dict(mod_data)
                        mod_data_placed["offset"] = offset
                        mod_data_placed["rot_z"] = rot_z

                        ribbon = getattr(self.viewport, "_trazomob_ribbon", None)
                        sidebar = getattr(self.viewport, "_trazomob_sidebar", None)
                        if ribbon is not None and hasattr(ribbon, "insert_module_into_scene"):
                            ribbon.insert_module_into_scene(mod_data_placed, explicit_offset=offset, explicit_rot_z=rot_z, explicit_wall=wall)
                        else:
                            from ..builders.cabinet import CabinetBuilder
                            from ..domain.module_defaults import build_default_module_params
                            from core.history import SnapshotImport
                            params = build_default_module_params(mod_data_placed)
                            params["rot_z"] = rot_z
                            new_mod = CabinetBuilder.build_module_group(params, offset=offset)
                            def _ins(sc):
                                sc.groups.append(new_mod)
                                sc.selection = {new_mod}
                            self.viewport.history.execute(SnapshotImport(_ins))
                            if sidebar is not None and hasattr(sidebar, "load_module"):
                                sidebar._selected_module = new_mod
                                sidebar.load_module(new_mod)
                            self.viewport.notify_scene_changed()
                            self.viewport.update()
                    except Exception as err:
                        logger.error("Erro ao soltar módulo na cena: %s", err)
                elif mime.hasFormat(TRAZOMOB_MIME_DECORATION):
                    try:
                        import json
                        raw_data = bytes(mime.data(TRAZOMOB_MIME_DECORATION)).decode("utf-8")
                        item_data = json.loads(raw_data)
                        ribbon = getattr(self.viewport, "_trazomob_ribbon", None)
                        if ribbon is not None and hasattr(ribbon, "insert_decoration_into_scene"):
                            ribbon.insert_decoration_into_scene(item_data)
                    except Exception as err:
                        logger.error("Erro ao soltar decoração na cena: %s", err)
                event.acceptProposedAction()
                self.viewport.update()
                return True

        return super().eventFilter(watched, event)

    def _handle_press(self, event: QMouseEvent) -> bool:
        pos_x, pos_y = event.position().x(), event.position().y()
        self._press_pos = event.position()
        self._mouse_pressed = True
        self._drag_active = False
        self._current_delta = QVector3D(0, 0, 0)
        self._active_locked_wall_face = None
        self._press_wall_u = None
        self._press_wall_z = None
        self._active_cota_items = []

        hit_group = self.viewport.pick_group(pos_x, pos_y)
        module = self._find_top_module(hit_group)

        if module is None:
            self._target_module = None
            self._affected_groups = []
            self._start_world_pt = None
            return False

        self._target_module = module
        scene = self.viewport.scene
        sel = list(getattr(scene, "selection", []))

        if module in sel and len(sel) > 1:
            self._affected_groups = [g for g in sel if hasattr(g, "mesh") or getattr(g, "xform", None) is not None]
        else:
            self._affected_groups = [module]

        ctx = self.viewport._build_ctx(event)
        orig, dirc = self.viewport._pixel_to_ray(pos_x, pos_y)

        # Se o módulo for uma esquadria (porta/janela), usamos sempre os limites estáveis do marco/caixaria
        # (get_module_reference_bounds), pois a folha aberta gira para fora da parede e não deve
        # alterar a referência de posicionamento (snap e recorte do vão).
        _m_name = module.name.lower() if hasattr(module, "name") else ""
        _m_kind = getattr(module, "ext", {}).get("trazomob", {}).get("kind", "") if hasattr(module, "ext") and isinstance(module.ext, dict) else ""
        is_esq_target = bool(
            (hasattr(module, "ext") and isinstance(module.ext, dict) and ("trazomob_esquadria" in module.ext or _m_kind == "esquadria"))
            or getattr(module, "layer", "") == "ESQUADRIAS"
            or (("porta" in _m_name or "janela" in _m_name) and _m_kind != "module" and "roupeiro" not in _m_name and "balcao" not in _m_name and "armario" not in _m_name and "aereo" not in _m_name)
        )
        self._drag_is_esquadria = is_esq_target
        if is_esq_target:
            self._module_orig_bounds = get_module_reference_bounds(module)
        else:
            from ..domain.module_geometry import get_module_carcass_bounds
            self._module_orig_bounds = get_module_carcass_bounds(module) or get_module_bounds(module)
        self._auto_rot_deg = 0.0
        self._initial_wall_face = self._find_adjacent_wall_face(module, tolerance_m=0.06)
        self._other_modules_bounds_cache: Optional[List[Tuple[Group, Tuple[float, float, float, float, float, float]]]] = None

        # Preserva exatamente o ponto clicado na superfície do móvel (evita saltos de dezenas de metros no zoom próximo)
        grab_pt: Optional[QVector3D] = QVector3D(ctx.world) if (ctx is not None and ctx.world is not None) else None
        if grab_pt is None and orig is not None and dirc is not None:
            if self._module_orig_bounds:
                grab_pt = _intersect_ray_aabb(orig, dirc, self._module_orig_bounds)
            if grab_pt is None:
                ref_z = (self._module_orig_bounds[4] + self._module_orig_bounds[5]) * 0.5 if self._module_orig_bounds else 0.0
                if abs(dirc.z()) > 0.05:
                    t_plane = (ref_z - orig.z()) / dirc.z()
                    if 0.0 < t_plane <= 50.0:
                        grab_pt = orig + dirc * t_plane
            if grab_pt is None and self._module_orig_bounds:
                b = self._module_orig_bounds
                grab_pt = QVector3D((b[0] + b[1]) * 0.5, (b[2] + b[3]) * 0.5, (b[4] + b[5]) * 0.5)
        if grab_pt is None:
            grab_pt = QVector3D(0.0, 0.0, 0.0)

        self._start_world_pt = grab_pt
        self._drag_grab_dist = max(0.05, (grab_pt - orig).length()) if (orig is not None) else 1.0

        cam = getattr(self.viewport, "camera", None)
        is_persp = bool(getattr(cam, "perspective", True)) if cam is not None else True
        cam_fwd = cam.forward().normalized() if (cam and hasattr(cam, "forward") and callable(cam.forward) and cam.forward().lengthSquared() > 1e-10) else None
        view_dir = cam_fwd or (dirc.normalized() if dirc is not None and dirc.lengthSquared() > 1e-10 else QVector3D(0.0, 0.0, -1.0))

        # Escolhe plano horizontal só quando o ângulo for inclinado (>= ~17°); próximo ao nível dos olhos usa plano vertical voltado à câmera
        if dirc is not None and abs(dirc.z()) >= 0.30 and abs(view_dir.z()) >= 0.30:
            self._drag_plane_normal = QVector3D(0.0, 0.0, 1.0)
        else:
            horiz = QVector3D(view_dir.x(), view_dir.y(), 0.0)
            if horiz.lengthSquared() > 1e-10:
                self._drag_plane_normal = horiz.normalized()
            elif dirc is not None and dirc.lengthSquared() > 1e-10:
                self._drag_plane_normal = dirc.normalized()
            else:
                self._drag_plane_normal = QVector3D(0.0, 0.0, 1.0)

        eye_ref = cam.eye() if (cam and hasattr(cam, "eye") and callable(cam.eye)) else orig
        if is_persp and eye_ref is not None and self._module_orig_bounds:
            self._cam_started_inside_module = _point_in_bounds(eye_ref, self._module_orig_bounds, margin=0.04)
        else:
            self._cam_started_inside_module = False
        return True

    def _handle_move(self, event: QMouseEvent) -> bool:
        if not self._target_module or self._press_pos is None or self._start_world_pt is None:
            return False

        dist_px = math.hypot(
            event.position().x() - self._press_pos.x(),
            event.position().y() - self._press_pos.y(),
        )

        if not self._drag_active:
            if dist_px >= self.DRAG_THRESHOLD_PX:
                self._drag_active = True
                self.viewport._box_active = False
                self.viewport._box_start = None
                self.viewport._box_cur = None

                for g in self._affected_groups:
                    if g not in self.viewport.scene.selection:
                        self.viewport.scene.selection.add(g)

                self.viewport.begin_groups_preview(self._affected_groups)
            else:
                return False

        self._last_event_pos = event.position()
        return self._recompute_from_pos(event.position())

    def _fallback_vertical_plane_pt(self, orig: QVector3D, dirc: QVector3D, p0: QVector3D, grab_dist: float) -> QVector3D:
        """Projeta o raio sobre o plano vertical voltado para a câmera passando por p0."""
        cam = getattr(self.viewport, "camera", None)
        fwd = cam.forward() if (cam and hasattr(cam, "forward") and callable(cam.forward)) else dirc
        horiz = QVector3D(fwd.x(), fwd.y(), 0.0)
        n = horiz.normalized() if horiz.lengthSquared() > 1e-10 else dirc.normalized()
        denom = QVector3D.dotProduct(dirc, n)
        if abs(denom) > 1e-4:
            t = QVector3D.dotProduct(p0 - orig, n) / denom
            max_t = min(35.0, max(2.0, grab_dist * 4.0))
            if 0.02 < t <= max_t:
                return orig + dirc * t
        return orig + dirc * grab_dist

    def _recompute_from_pos(self, pos: QPointF) -> bool:
        if not self._target_module or self._start_world_pt is None:
            return False

        orig, dirc = self.viewport._pixel_to_ray(pos.x(), pos.y())
        if orig is None or dirc is None:
            return True

        p0 = self._start_world_pt
        plane_n = getattr(self, "_drag_plane_normal", None) or QVector3D(0.0, 0.0, 1.0)
        grab_dist = max(0.05, float(getattr(self, "_drag_grab_dist", (p0 - orig).length())))
        curr_pt: Optional[QVector3D] = None

        if abs(plane_n.z()) > 0.9:
            max_t = min(35.0, max(1.2, grab_dist * 5.0))
            if abs(dirc.z()) > 0.08:
                t = (p0.z() - orig.z()) / dirc.z()
                if 0.02 < t <= max_t:
                    curr_pt = orig + dirc * t
            if curr_pt is None:
                curr_pt = self._fallback_vertical_plane_pt(orig, dirc, p0, grab_dist)
        else:
            denom = QVector3D.dotProduct(dirc, plane_n)
            if abs(denom) > 1e-4:
                t = QVector3D.dotProduct(p0 - orig, plane_n) / denom
                max_t = min(35.0, max(2.0, grab_dist * 4.0))
                if 0.02 < t <= max_t:
                    curr_pt = orig + dirc * t
            if curr_pt is None:
                curr_pt = orig + dirc * grab_dist

        raw_delta = curr_pt - p0
        raw_delta.setZ(0.0)

        cam = getattr(self.viewport, "camera", None)
        is_persp = bool(getattr(cam, "perspective", True)) if cam is not None else True
        eye_ref = cam.eye() if (cam and hasattr(cam, "eye") and callable(cam.eye)) else orig
        guard_cam = (
            is_persp
            and eye_ref is not None
            and self._module_orig_bounds is not None
            and not getattr(self, "_cam_started_inside_module", False)
            and not getattr(self, "_drag_is_esquadria", False)
        )
        if guard_cam:
            raw_delta = _prevent_camera_inside_module(self._module_orig_bounds, raw_delta, eye_ref)

        # ── CÁLCULO DE ADERÊNCIA MAGNÉTICA (SNAP) ───────────────────────────
        snapped_delta = self._compute_magnetic_snap(raw_delta, orig, dirc)
        if guard_cam:
            snapped_delta = _prevent_camera_inside_module(self._module_orig_bounds, snapped_delta, eye_ref)

        self._current_delta = snapped_delta
        if abs(getattr(self, "_auto_rot_deg", 0.0)) > 1e-3 and self._module_orig_bounds:
            from PySide6.QtGui import QMatrix4x4
            from core.history import rotation_matrix
            b = self._module_orig_bounds
            c_orig = QVector3D((b[0] + b[1]) * 0.5, (b[2] + b[3]) * 0.5, (b[4] + b[5]) * 0.5)
            m_rot = rotation_matrix(c_orig, QVector3D(0.0, 0.0, 1.0), self._auto_rot_deg)
            m_tr = QMatrix4x4()
            m_tr.translate(snapped_delta)
            self.viewport.set_groups_preview_matrix(m_tr * m_rot)
        else:
            self.viewport.set_groups_preview_offset(snapped_delta)

        # ── CÁLCULO DAS COTAS EM TEMPO REAL PARA OS OBJETOS MAIS PRÓXIMOS ──
        self._update_snap_cotas(snapped_delta)

        self.viewport.update()
        return True

    def _handle_release(self, event: QMouseEvent) -> bool:
        self._mouse_pressed = False
        if not self._drag_active:
            target = self._target_module
            self._start_world_pt = None
            self._drag_active = False
            mods = event.modifiers()
            is_multi = bool(mods & (Qt.ControlModifier | Qt.ShiftModifier))
            if target is not None and hasattr(self.viewport, "scene"):
                if is_multi:
                    from tools.select import selection_mode
                    mode = selection_mode(mods)
                    self.viewport.scene.select([target], mode=mode)
                else:
                    self.viewport.scene.select([target], mode="replace")
                if hasattr(self.viewport, "notify_scene_changed"):
                    self.viewport.notify_scene_changed()
                sidebar = getattr(self.viewport, "_trazomob_sidebar", None)
                if sidebar is not None and hasattr(sidebar, "load_module") and self._is_module_group(target):
                    sidebar._selected_module = target
                    sidebar.load_module(target)
            self._refresh_active_cotas(target)
            self.viewport.update()
            return False

        self._drag_active = False
        self.viewport.end_groups_preview()

        delta = self._current_delta
        auto_rot_deg = getattr(self, "_auto_rot_deg", 0.0)
        orig_bounds = self._module_orig_bounds
        target_groups = list(self._affected_groups)
        last_target_module = self._target_module

        self._target_module = None
        self._affected_groups = []
        self._start_world_pt = None
        self._current_delta = QVector3D(0, 0, 0)
        self._auto_rot_deg = 0.0
        self._active_locked_wall_face = None
        self._axis_lock = None
        self._last_event_pos = None
        self._other_modules_bounds_cache = None
        self._cota_cache_key = None
        self._drag_plane_normal = None
        self._drag_grab_dist = 1.0
        self._cam_started_inside_module = False
        self._drag_is_esquadria = False

        if (delta.length() > 1e-4 or abs(auto_rot_deg) > 1e-3) and target_groups:
            cmds = []
            if abs(auto_rot_deg) > 1e-3 and orig_bounds:
                from ..builders.cabinet import RotateTrazoMobModuleCommand
                for g in target_groups:
                    cmds.append(RotateTrazoMobModuleCommand(g, auto_rot_deg))
            if delta.length() > 1e-4:
                # Expande toda a árvore de grupos (folhas com malha ou componentes folha)
                all_moving_groups = []
                seen_moving = set()
                def _collect_all(grps):
                    for g in grps:
                        if id(g) in seen_moving:
                            continue
                        seen_moving.add(id(g))
                        has_verts = getattr(g, "mesh", None) is not None and bool(getattr(g.mesh, "vertices", None))
                        has_leaf_xform = getattr(g, "xform", None) is not None and not getattr(g, "children", None)
                        if has_verts or has_leaf_xform:
                            all_moving_groups.append(g)
                        _collect_all(getattr(g, "children", []) or [])
                _collect_all(target_groups)

                for g in all_moving_groups:
                    cmds.append(FastTranslateGroupCommand(g, delta))
            if cmds:
                cmd = cmds[0] if len(cmds) == 1 else CompoundCommand(cmds)
                self.viewport.history.execute(cmd)

            # Sincroniza o offset real dos parâmetros do módulo a partir dos bounds da carcaça após o comando
            from ..domain.module_geometry import get_module_carcass_bounds
            for g in target_groups:
                if hasattr(g, "ext") and isinstance(g.ext, dict):
                    is_esq_g = (
                        "trazomob_esquadria" in g.ext
                        or g.ext.get("trazomob", {}).get("kind") == "esquadria"
                        or getattr(g, "layer", "") == "ESQUADRIAS"
                    )
                    if is_esq_g:
                        base_dict = g.ext.get("trazomob_esquadria") or g.ext.get("trazomob_module") or g.ext.get("trazomob") or {}
                        old_off = base_dict.get("offset", (0.0, 0.0, 0.0))
                        old_peit = float(base_dict.get("peitoril_mm", base_dict.get("peitoril", 0.0)) or 0.0)
                        if abs(delta.z()) > 1e-5:
                            new_peit = max(0.0, round(old_peit + float(delta.z()) * 1000.0, 1))
                            new_z_off = float(old_off[2])
                        else:
                            new_peit = old_peit
                            new_z_off = float(old_off[2]) + float(delta.z())
                        new_off = (
                            float(old_off[0]) + float(delta.x()),
                            float(old_off[1]) + float(delta.y()),
                            new_z_off,
                        )
                        for k_ext in ("trazomob_module", "trazomob_esquadria", "trazomob"):
                            if k_ext in g.ext and isinstance(g.ext[k_ext], dict):
                                g.ext[k_ext]["offset"] = new_off
                                if "peitoril_mm" in g.ext[k_ext] or abs(delta.z()) > 1e-5:
                                    g.ext[k_ext]["peitoril_mm"] = new_peit
                                    g.ext[k_ext]["peitoril"] = new_peit
                    elif "trazomob_module" in g.ext:
                        cb = get_module_carcass_bounds(g) or get_module_bounds(g)
                        if cb:
                            mod_ext = g.ext["trazomob_module"]
                            unrot_span = mod_ext.get("_unrot_carcass_span")
                            if isinstance(unrot_span, (list, tuple)) and len(unrot_span) == 6:
                                cx_f = (cb[0] + cb[1]) * 0.5
                                cy_f = (cb[2] + cb[3]) * 0.5
                                cz_f = (cb[4] + cb[5]) * 0.5
                                mod_ext["offset"] = (
                                    float(cx_f - float(unrot_span[0])),
                                    float(cy_f - float(unrot_span[1])),
                                    float(cz_f - float(unrot_span[2])),
                                )
                            else:
                                mod_ext["offset"] = (float(cb[0]), float(cb[2]), float(cb[4]))

            # Se algum dos grupos movidos for uma luminária, sincroniza as coordenadas reais da luz
            if any(hasattr(g, "ext") and isinstance(g.ext, dict) and "trazomob_light" in g.ext for g in target_groups):
                try:
                    from ..render.lighting import sync_scene_lights_to_document
                    sync_scene_lights_to_document(self.viewport)
                except Exception as exc:
                    logger.debug("sincronização das luzes falhou após arrastar: %s", exc)

            # Se algum dos grupos movidos for uma esquadria, atualiza os recortes de parede
            if any(
                hasattr(g, "ext") and isinstance(g.ext, dict) and (
                    "trazomob_esquadria" in g.ext
                    or g.ext.get("trazomob", {}).get("kind") == "esquadria"
                    or getattr(g, "layer", "") == "ESQUADRIAS"
                    or (("porta" in g.name.lower() or "janela" in g.name.lower()) and g.ext.get("trazomob", {}).get("kind") != "module" and "roupeiro" not in g.name.lower() and "balcao" not in g.name.lower() and "armario" not in g.name.lower() and "aereo" not in g.name.lower())
                )
                for g in target_groups
            ):
                try:
                    from ..wall.mesh_builder import WallMeshBuilder
                    if hasattr(self.viewport, "scene"):
                        WallMeshBuilder.sync_scene_wall_openings(self.viewport.scene)
                except Exception as exc:
                    logger.debug("recorte de vãos da parede falhou após arrastar: %s", exc)

            if last_target_module is not None and hasattr(self.viewport, "scene"):
                self.viewport.scene.select([last_target_module], mode="replace")

            if hasattr(self.viewport, "notify_scene_changed"):
                self.viewport.notify_scene_changed()
            if hasattr(self.viewport, "flash_status"):
                dx_mm = int(round(delta.x() * 1000.0))
                dy_mm = int(round(delta.y() * 1000.0))
                dz_mm = int(round(delta.z() * 1000.0))
                self.viewport.flash_status(f"Módulo movido: ΔX={dx_mm}mm, ΔY={dy_mm}mm, ΔZ={dz_mm}mm (Snap Magnético)")

        # Recalcula e mantém as cotas ativas na posição final do módulo selecionado
        self._refresh_active_cotas(last_target_module)

        # Se o módulo finalizou o movimento encostado na parede, herda o ambiente da parede
        if last_target_module is not None:
            adj = self._find_adjacent_wall_face(last_target_module)
            if adj is not None:
                adj_wall, _ = adj
                if hasattr(adj_wall, "ext") and isinstance(adj_wall.ext, dict):
                    amb_n = adj_wall.ext.get("ambiente") or adj_wall.ext.get("trazomob_wall", {}).get("ambiente")
                    pav_n = adj_wall.ext.get("pavimento") or adj_wall.ext.get("trazomob_wall", {}).get("pavimento")
                    if amb_n and hasattr(last_target_module, "ext") and isinstance(last_target_module.ext, dict):
                        last_target_module.ext["ambiente"] = amb_n
                        last_target_module.ext["pavimento"] = pav_n or "Térreo"
                        for k in ("trazomob_module", "trazomob_esquadria", "trazomob"):
                            if k in last_target_module.ext and isinstance(last_target_module.ext[k], dict):
                                last_target_module.ext[k]["ambiente"] = amb_n
                                last_target_module.ext[k]["pavimento"] = pav_n or "Térreo"

        # Se o módulo finalizou o movimento encostado na parede, mantém a parede selecionada visualmente
        if last_target_module is not None:
            from ..wall.selection import WallSelectionManager
            wall_mgr = WallSelectionManager.get_instance(self.viewport)
            adj = self._find_adjacent_wall_face(last_target_module)
            if adj is not None:
                adj_wall, adj_face = adj
                wall_mgr.set_selected_face(adj_wall, adj_face, notify_sidebar=False)

        self.viewport.update()
        return True

