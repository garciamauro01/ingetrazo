# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors and Pair Programmer.
"""Ferramenta interativa de posicionamento de portas com corte dinâmico de paredes."""
from __future__ import annotations

import math
from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QVector3D
from PySide6.QtWidgets import QApplication

from core.group import Group, iter_placements
from core.history import CompoundCommand, InsertGroupCommand
import core.solids as solids
from tools.base import Tool, ToolContext

from .builder import build_parametric_door, build_wall_cutter, DOOR_FINISHES


class DoorPlacerTool(Tool):
    """Ferramenta que acompanha o cursor sobre as paredes com preview 3D da porta e realiza o corte booleano ao clicar."""

    name = "Porta Paramétrica"
    shortcut = None
    description = "Inserir porta com vão cortado automaticamente na parede."
    uses_snap = True
    wireframe_color = (0.95, 0.45, 0.16, 1.0)
    wireframe_depth_tested = False

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = {
            "width": 0.80,
            "height": 2.10,
            "wall_thickness": 0.15,
            "auto_detect_wall": True,
            "open_angle_deg": 60.0,
            "hinge_side": "left",
            "open_inward": True,
            "has_alizar": True,
            "finish_name": "Madeira Carvalho",
        }
        if config:
            self.config.update(config)

        # Estado dinâmico do hover
        self._target_wall_group: Optional[Group] = None
        self._target_face = None
        self._face_normal: Optional[QVector3D] = None
        self._u_right: Optional[QVector3D] = None
        self._v_inward: Optional[QVector3D] = None
        self._w_up = QVector3D(0, 0, 1)
        self._base_center: Optional[QVector3D] = None
        self._effective_thickness: float = self.config["wall_thickness"]

        # Cache de preview
        self._preview_door: Optional[Group] = None
        self._preview_segments: list[tuple[QVector3D, QVector3D]] = []

    def update_config(self, new_cfg: dict[str, Any]) -> None:
        self.config.update(new_cfg)
        self._invalidate_preview()

    def _invalidate_preview(self) -> None:
        self._preview_door = None
        self._preview_segments = []

    def on_activate(self, viewport) -> None:
        self._invalidate_preview()
        viewport.flash_status("Porta Paramétrica: Passe sobre uma parede para ver a porta. Clique para cortar e inserir.")
        viewport.update()

    def on_deactivate(self, viewport) -> None:
        self._invalidate_preview()
        viewport.update()

    def on_cancel(self, viewport) -> None:
        self._invalidate_preview()
        viewport.update()

    # ---- Detecção e Alinhamento à Parede ---------------------------------------
    def _detect_wall_at(self, ctx: ToolContext) -> None:
        vp = ctx.viewport
        screen_x, screen_y = ctx.screen.x(), ctx.screen.y()

        hit_face = None
        hit_group = None

        pick_placement = getattr(vp, "pick_face_placement", None)
        if callable(pick_placement):
            hit_face, hit_group = pick_placement(screen_x, screen_y)
        if hit_face is None:
            pick_any = getattr(vp, "pick_face_any", None)
            if callable(pick_any):
                hit_face, hit_group = pick_any(screen_x, screen_y)

        # Se não pegou grupo pelo pick_face, tenta pelo pick_group
        if hit_group is None:
            pick_g = getattr(vp, "pick_group", None)
            if callable(pick_g):
                hit_group = pick_g(screen_x, screen_y)

        self._target_face = hit_face
        self._target_wall_group = hit_group

        # 1. Determina a normal da face
        if hit_face is not None:
            normal = hit_face.normal()
            # Se a face estiver no espaço local de um grupo com xform
            if hit_group is not None and getattr(hit_group, "xform", None) is not None:
                normal = hit_group.xform.mapVector(normal).normalized()
        else:
            normal = QVector3D(0, -1, 0)

        # Se a normal for quase horizontal (teto ou chão), usa fallback frontal
        if abs(normal.z()) > 0.85:
            normal = QVector3D(0, -1, 0)
        else:
            # Projeta no plano horizontal XY para manter a porta em prumo perfeitamente vertical
            normal = QVector3D(normal.x(), normal.y(), 0.0)
            if normal.length() < 1e-4:
                normal = QVector3D(0, -1, 0)
            else:
                normal = normal.normalized()

        self._face_normal = normal
        # inward aponta para dentro da parede (contra a normal exterior da face)
        self._v_inward = -normal

        # u_right corre ao longo da parede horizontalmente
        # cross(v_inward, (0,0,1))
        u = QVector3D.crossProduct(self._v_inward, self._w_up)
        if u.length() < 1e-4:
            u = QVector3D(1, 0, 0)
        else:
            u = u.normalized()
        self._u_right = u

        # 2. Determina a cota Z da base (piso) da parede
        base_z = 0.0
        if hit_group is not None and getattr(hit_group, "mesh", None) is not None and hit_group.mesh.vertices:
            # Pega o menor Z da parede
            all_zs = [v.position.z() if hasattr(v, "position") else v.z() for v in hit_group.mesh.vertices]
            if all_zs:
                min_z = min(all_zs)
                # Se o cursor estiver próximo ou acima da base, assenta na base
                if ctx.world.z() >= min_z - 0.20:
                    base_z = min_z
                else:
                    base_z = ctx.world.z()
        else:
            base_z = max(0.0, ctx.world.z() - (self.config["height"] / 2.0))

        # Ponto central inferior do vão na face
        self._base_center = QVector3D(ctx.world.x(), ctx.world.y(), base_z)

        # 3. Detectar espessura da parede automaticamente se solicitado
        thickness = self.config["wall_thickness"]
        if self.config.get("auto_detect_wall", True) and hit_group is not None:
            detected_t = self._measure_wall_thickness(hit_group, self._base_center, normal)
            if detected_t is not None and 0.04 <= detected_t <= 1.20:
                thickness = detected_t
        self._effective_thickness = thickness

    def _measure_wall_thickness(self, wall_group: Group, point_on_face: QVector3D, face_normal: QVector3D) -> Optional[float]:
        """Calcula a espessura da parede pesquisando a face oposta na direção da normal interna."""
        if not hasattr(wall_group, "mesh") or not wall_group.mesh.faces:
            return None

        inward = -face_normal
        best_dist = None

        for f in wall_group.mesh.faces:
            fn = f.normal()
            if getattr(wall_group, "xform", None) is not None:
                fn = wall_group.xform.mapVector(fn).normalized()

            # Procura face apontando na direção oposta (costas da parede)
            if QVector3D.dotProduct(fn, face_normal) < -0.85:
                # Vértices da face
                for v in f.vertices:
                    p = v.position if hasattr(v, "position") else v
                    if getattr(wall_group, "xform", None) is not None:
                        p = wall_group.xform.map(p)
                    dist = QVector3D.dotProduct(p - point_on_face, inward)
                    if dist > 0.02:
                        if best_dist is None or dist < best_dist:
                            best_dist = dist
                            break

        return best_dist

    # ---- Hover e Preview Visual em Tempo Real ---------------------------------
    def on_hover(self, ctx: ToolContext) -> None:
        self._detect_wall_at(ctx)

        # Atualiza a porta de preview para desenhar o contorno
        if self._base_center is not None and self._u_right is not None and self._v_inward is not None:
            self._preview_door = build_parametric_door(
                self._base_center,
                self._u_right,
                self._v_inward,
                self._w_up,
                width=self.config["width"],
                height=self.config["height"],
                wall_thickness=self._effective_thickness,
                open_angle_deg=self.config["open_angle_deg"],
                hinge_side=self.config["hinge_side"],
                open_inward=self.config["open_inward"],
                has_alizar=self.config["has_alizar"],
                finish_name=self.config["finish_name"],
            )

            # Extrai arestas para preview aramado elegante
            segs = []
            max_edges = 250
            for g, m in iter_placements(self._preview_door):
                if g.mesh and g.mesh.edges:
                    for e in g.mesh.edges[:max_edges]:
                        p_a = QVector3D(e.a)
                        p_b = QVector3D(e.b)
                        if m is not None:
                            p_a = m.map(p_a)
                            p_b = m.map(p_b)
                        segs.append((p_a, p_b))
            self._preview_segments = segs

            # Feedback de espessura e medidas no status
            info_wall = f"Parede: {self._effective_thickness*100:.1f}cm"
            if self._target_wall_group is not None and solids.is_solid(self._target_wall_group):
                info_wall += " (Sólido detectado - Corte automático pronto)"
            ctx.viewport.flash_status(
                f"Porta {int(self.config['width']*100)}x{int(self.config['height']*100)}cm | {info_wall} | Clique para inserir."
            )
        else:
            self._preview_segments = []

        ctx.viewport.update()

    def rubber_band_lines(self) -> list[tuple[QVector3D, QVector3D]]:
        return self._preview_segments

    # ---- Clique: Execução do Corte e Inserção ---------------------------------
    def on_click(self, ctx: ToolContext) -> None:
        if self._base_center is None or self._u_right is None or self._v_inward is None:
            return

        vp = ctx.viewport
        scene = vp.scene

        # 1. Cria a porta paramétrica completa definitiva
        door_group = build_parametric_door(
            self._base_center,
            self._u_right,
            self._v_inward,
            self._w_up,
            width=self.config["width"],
            height=self.config["height"],
            wall_thickness=self._effective_thickness,
            open_angle_deg=self.config["open_angle_deg"],
            hinge_side=self.config["hinge_side"],
            open_inward=self.config["open_inward"],
            has_alizar=self.config["has_alizar"],
            finish_name=self.config["finish_name"],
        )

        wall_group = self._target_wall_group
        commands = []

        # 2. Realiza o corte booleano se a parede sob o cursor for um sólido
        cut_performed = False
        if wall_group is not None and solids.is_solid(wall_group):
            try:
                cutter = build_wall_cutter(
                    self._base_center,
                    self._u_right,
                    self._v_inward,
                    self._w_up,
                    width=self.config["width"],
                    height=self.config["height"],
                    wall_thickness=self._effective_thickness,
                )
                cut_cmd = solids.SolidOperationCommand(solids.SUBTRACT, [cutter, wall_group])
                cut_cmd.prepare()
                commands.append(cut_cmd)
                cut_performed = True
            except Exception as e:
                print(f"[PortaParametrica] Falha no corte booleano: {e}")
                cut_performed = False

        # 3. Adiciona a porta ao modelo
        insert_cmd = InsertGroupCommand(door_group)
        commands.append(insert_cmd)

        if len(commands) == 1:
            vp.history.execute(commands[0])
        else:
            compound = CompoundCommand(commands)
            vp.history.execute(compound)

        if cut_performed:
            vp.flash_status("Porta inserida e parede cortada com sucesso!")
        else:
            vp.flash_status("Porta inserida no local.")

        self._invalidate_preview()
        vp.update()


from .builder import build_parametric_window, build_window_wall_cutter, WINDOW_FINISHES


class WindowPlacerTool(Tool):
    """Ferramenta que acompanha o cursor sobre paredes com preview 3D da janela e realiza o corte booleano na altura do peitoril."""

    name = "Janela Paramétrica"
    shortcut = None
    description = "Inserir janela com vão e peitoril cortados automaticamente na parede."
    uses_snap = True
    wireframe_color = (0.17, 0.47, 0.89, 1.0)
    wireframe_depth_tested = False

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = {
            "width": 1.20,
            "height": 1.20,
            "sill_height": 1.00,
            "wall_thickness": 0.15,
            "auto_detect_wall": True,
            "window_type": "sliding",
            "open_pct": 0.0,
            "has_sill": True,
            "finish_name": "Alumínio Preto",
        }
        if config:
            self.config.update(config)

        self._target_wall_group: Optional[Group] = None
        self._target_face = None
        self._face_normal: Optional[QVector3D] = None
        self._u_right: Optional[QVector3D] = None
        self._v_inward: Optional[QVector3D] = None
        self._w_up = QVector3D(0, 0, 1)
        self._base_center: Optional[QVector3D] = None
        self._effective_thickness: float = self.config["wall_thickness"]

        self._preview_window: Optional[Group] = None
        self._preview_segments: list[tuple[QVector3D, QVector3D]] = []

    def update_config(self, new_cfg: dict[str, Any]) -> None:
        self.config.update(new_cfg)
        self._invalidate_preview()

    def _invalidate_preview(self) -> None:
        self._preview_window = None
        self._preview_segments = []

    def on_activate(self, viewport) -> None:
        self._invalidate_preview()
        viewport.flash_status("Janela Paramétrica: Aponte sobre uma parede para ver a janela no peitoril. Clique para cortar e inserir.")
        viewport.update()

    def on_deactivate(self, viewport) -> None:
        self._invalidate_preview()
        viewport.update()

    def on_cancel(self, viewport) -> None:
        self._invalidate_preview()
        viewport.update()

    def _detect_wall_at(self, ctx: ToolContext) -> None:
        vp = ctx.viewport
        screen_x, screen_y = ctx.screen.x(), ctx.screen.y()

        hit_face = None
        hit_group = None

        pick_placement = getattr(vp, "pick_face_placement", None)
        if callable(pick_placement):
            hit_face, hit_group = pick_placement(screen_x, screen_y)
        if hit_face is None:
            pick_any = getattr(vp, "pick_face_any", None)
            if callable(pick_any):
                hit_face, hit_group = pick_any(screen_x, screen_y)
        if hit_group is None:
            pick_g = getattr(vp, "pick_group", None)
            if callable(pick_g):
                hit_group = pick_g(screen_x, screen_y)

        self._target_face = hit_face
        self._target_wall_group = hit_group

        if hit_face is not None:
            normal = hit_face.normal()
            if hit_group is not None and getattr(hit_group, "xform", None) is not None:
                normal = hit_group.xform.mapVector(normal).normalized()
        else:
            normal = QVector3D(0, -1, 0)

        if abs(normal.z()) > 0.85:
            normal = QVector3D(0, -1, 0)
        else:
            normal = QVector3D(normal.x(), normal.y(), 0.0)
            if normal.length() < 1e-4:
                normal = QVector3D(0, -1, 0)
            else:
                normal = normal.normalized()

        self._face_normal = normal
        self._v_inward = -normal

        u = QVector3D.crossProduct(self._v_inward, self._w_up)
        if u.length() < 1e-4:
            u = QVector3D(1, 0, 0)
        else:
            u = u.normalized()
        self._u_right = u

        base_z = 0.0
        if hit_group is not None and getattr(hit_group, "mesh", None) is not None and hit_group.mesh.vertices:
            all_zs = [v.position.z() if hasattr(v, "position") else v.z() for v in hit_group.mesh.vertices]
            if all_zs:
                min_z = min(all_zs)
                if ctx.world.z() >= min_z - 0.20:
                    base_z = min_z
                else:
                    base_z = ctx.world.z()
        else:
            base_z = max(0.0, ctx.world.z() - self.config["sill_height"] - (self.config["height"] / 2.0))

        self._base_center = QVector3D(ctx.world.x(), ctx.world.y(), base_z)

        thickness = self.config["wall_thickness"]
        if self.config.get("auto_detect_wall", True) and hit_group is not None:
            detected_t = self._measure_wall_thickness(hit_group, self._base_center, normal)
            if detected_t is not None and 0.04 <= detected_t <= 1.20:
                thickness = detected_t
        self._effective_thickness = thickness

    def _measure_wall_thickness(self, wall_group: Group, point_on_face: QVector3D, face_normal: QVector3D) -> Optional[float]:
        if not hasattr(wall_group, "mesh") or not wall_group.mesh.faces:
            return None

        inward = -face_normal
        best_dist = None

        for f in wall_group.mesh.faces:
            fn = f.normal()
            if getattr(wall_group, "xform", None) is not None:
                fn = wall_group.xform.mapVector(fn).normalized()

            if QVector3D.dotProduct(fn, face_normal) < -0.85:
                for v in f.vertices:
                    p = v.position if hasattr(v, "position") else v
                    if getattr(wall_group, "xform", None) is not None:
                        p = wall_group.xform.map(p)
                    dist = QVector3D.dotProduct(p - point_on_face, inward)
                    if dist > 0.02:
                        if best_dist is None or dist < best_dist:
                            best_dist = dist
                            break

        return best_dist

    def on_hover(self, ctx: ToolContext) -> None:
        self._detect_wall_at(ctx)

        if self._base_center is not None and self._u_right is not None and self._v_inward is not None:
            self._preview_window = build_parametric_window(
                self._base_center,
                self._u_right,
                self._v_inward,
                self._w_up,
                width=self.config["width"],
                height=self.config["height"],
                sill_height=self.config["sill_height"],
                wall_thickness=self._effective_thickness,
                has_sill=self.config["has_sill"],
                window_type=self.config["window_type"],
                open_pct=self.config["open_pct"],
                finish_name=self.config["finish_name"],
            )

            segs = []
            max_edges = 250
            for g, m in iter_placements(self._preview_window):
                if g.mesh and g.mesh.edges:
                    for e in g.mesh.edges[:max_edges]:
                        p_a = QVector3D(e.a)
                        p_b = QVector3D(e.b)
                        if m is not None:
                            p_a = m.map(p_a)
                            p_b = m.map(p_b)
                        segs.append((p_a, p_b))
            self._preview_segments = segs

            info_wall = f"Parede: {self._effective_thickness*100:.1f}cm | Peitoril: {self.config['sill_height']:.2f}m"
            if self._target_wall_group is not None and solids.is_solid(self._target_wall_group):
                info_wall += " (Corte automático pronto)"
            ctx.viewport.flash_status(
                f"Janela {int(self.config['width']*100)}x{int(self.config['height']*100)}cm | {info_wall} | Clique para inserir."
            )
        else:
            self._preview_segments = []

        ctx.viewport.update()

    def rubber_band_lines(self) -> list[tuple[QVector3D, QVector3D]]:
        return self._preview_segments

    def on_click(self, ctx: ToolContext) -> None:
        if self._base_center is None or self._u_right is None or self._v_inward is None:
            return

        vp = ctx.viewport
        scene = vp.scene

        window_group = build_parametric_window(
            self._base_center,
            self._u_right,
            self._v_inward,
            self._w_up,
            width=self.config["width"],
            height=self.config["height"],
            sill_height=self.config["sill_height"],
            wall_thickness=self._effective_thickness,
            has_sill=self.config["has_sill"],
            window_type=self.config["window_type"],
            open_pct=self.config["open_pct"],
            finish_name=self.config["finish_name"],
        )

        wall_group = self._target_wall_group
        commands = []

        cut_performed = False
        if wall_group is not None and solids.is_solid(wall_group):
            try:
                cutter = build_window_wall_cutter(
                    self._base_center,
                    self._u_right,
                    self._v_inward,
                    self._w_up,
                    width=self.config["width"],
                    height=self.config["height"],
                    sill_height=self.config["sill_height"],
                    wall_thickness=self._effective_thickness,
                )
                cut_cmd = solids.SolidOperationCommand(solids.SUBTRACT, [cutter, wall_group])
                cut_cmd.prepare()
                commands.append(cut_cmd)
                cut_performed = True
            except Exception as e:
                print(f"[JanelaParametrica] Falha no corte booleano: {e}")
                cut_performed = False

        insert_cmd = InsertGroupCommand(window_group)
        commands.append(insert_cmd)

        if len(commands) == 1:
            vp.history.execute(commands[0])
        else:
            compound = CompoundCommand(commands)
            vp.history.execute(compound)

        if cut_performed:
            vp.flash_status("Janela inserida e parede cortada no peitoril com sucesso!")
        else:
            vp.flash_status("Janela inserida no local.")

        self._invalidate_preview()
        vp.update()

