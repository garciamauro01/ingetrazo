# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Construtor Interativo de Paredes (Wall Builder) para Design de Interiores.

Permite desenhar paredes contínuas no viewport com cantos em esquadria (miter corners)
perfeitamente fechados e alinhados, pé-direito, espessura e alinhamento configuráveis,
gerando geometria 3D sólida (manifold), limpa e agrupada automaticamente na camada "Paredes"
(e piso na camada "Piso" ao fechar o ciclo).
"""
from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QVector3D

from core.group import Group
from core.history import Command
from core.layers import Layer
from core.mesh import Mesh
from core.triangulate import triangulate
from tools.base import Tool, ToolContext


from ..wall.mesh_builder import line_intersection_2d, WallMeshBuilder


class AddWallGroupCommand(Command):
    """Comando reversível (Undo/Redo) para inserção de paredes contínuas."""

    def __init__(self, group: Group) -> None:
        self.group = group

    def do(self, scene) -> None:
        if self.group not in scene.groups:
            scene.groups.append(self.group)
        scene.version += 1

    def undo(self, scene) -> None:
        if self.group in scene.groups:
            scene.groups.remove(self.group)
        scene.version += 1


class ReplaceWallGroupCommand(Command):
    """Comando reversível para atualizar o sólido da parede contínua ao estender a cadeia."""

    def __init__(self, old_group: Optional[Group], new_group: Group) -> None:
        self.old_group = old_group
        self.new_group = new_group

    def do(self, scene) -> None:
        if self.old_group is not None and self.old_group in scene.groups:
            idx = scene.groups.index(self.old_group)
            scene.groups[idx] = self.new_group
        else:
            scene.groups.append(self.new_group)
        scene.version += 1

    def undo(self, scene) -> None:
        if self.new_group in scene.groups:
            if self.old_group is not None:
                idx = scene.groups.index(self.new_group)
                scene.groups[idx] = self.old_group
            else:
                scene.groups.remove(self.new_group)
        scene.version += 1


class AddFloorCommand(Command):
    """Comando reversível para inserção de piso ao fechar o perímetro de paredes."""

    def __init__(self, group: Group) -> None:
        self.group = group

    def do(self, scene) -> None:
        if self.group not in scene.groups:
            scene.groups.append(self.group)
        scene.version += 1

    def undo(self, scene) -> None:
        if self.group in scene.groups:
            scene.groups.remove(self.group)
        scene.version += 1

class SplitWallGroupCommand(Command):
    """Comando reversível que substitui um grupo monolítico de paredes por paredes individuais seccionadas."""

    def __init__(self, old_group: Group, new_groups: list[Group]) -> None:
        self.old_group = old_group
        self.new_groups = new_groups

    def do(self, scene) -> None:
        if self.old_group in scene.groups:
            idx = scene.groups.index(self.old_group)
            scene.groups.remove(self.old_group)
            for offset, g in enumerate(self.new_groups):
                scene.groups.insert(idx + offset, g)
        else:
            for g in self.new_groups:
                if g not in scene.groups:
                    scene.groups.append(g)
        scene.version += 1

    def undo(self, scene) -> None:
        first_idx = None
        for g in self.new_groups:
            if g in scene.groups:
                if first_idx is None:
                    first_idx = scene.groups.index(g)
                scene.groups.remove(g)
        if self.old_group is not None:
            if first_idx is not None:
                scene.groups.insert(first_idx, self.old_group)
            else:
                scene.groups.append(self.old_group)
        scene.version += 1



class WallBuilderTool(Tool):
    """Ferramenta interativa de desenho de paredes no padrão de design de interiores."""

    name = "Construtor de Paredes"
    shortcut = "W"
    description = "Clique para posicionar cantos de paredes contínuas; digite o comprimento ou feche o ciclo."
    vcb_label = "Comprimento"
    uses_snap = True
    magnetic_axis_deg = 4.0
    screen_axis_px = 12.0

    def __init__(
        self,
        altura_m: float = 2.60,
        espessura_m: float = 0.15,
        alinhamento: str = "interno",
        gerar_teto: bool = False,
        on_wall_added=None,
        on_deactivated=None,
    ) -> None:
        super().__init__()
        self.altura_m = altura_m
        self.espessura_m = espessura_m
        # "interno" (referência na face interna), "centro", "externo"
        self.alinhamento = alinhamento
        self.gerar_teto = gerar_teto
        self.on_wall_added = on_wall_added
        self.on_deactivated = on_deactivated

        self.start_point: Optional[QVector3D] = None
        self.hover_point: Optional[QVector3D] = None
        self.chain_first_point: Optional[QVector3D] = None
        self.chain_points: list[QVector3D] = []
        self._current_wall_group: Optional[Group] = None
        self._wall_counter = 1

    def set_params(self, altura_m: float, espessura_m: float, alinhamento: str, gerar_teto: Optional[bool] = None) -> None:
        self.altura_m = altura_m
        self.espessura_m = espessura_m
        self.alinhamento = alinhamento
        if gerar_teto is not None:
            self.gerar_teto = bool(gerar_teto)

    def on_activate(self, viewport) -> None:
        self._reset()
        if hasattr(viewport, "status_message"):
            viewport.status_message(
                f"🧱 Construtor de Paredes Ativo: Altura={self.altura_m:.2f}m, Espessura={self.espessura_m*100:.0f}cm. Clique para iniciar."
            )

    def on_deactivate(self, viewport) -> None:
        self._reset()
        self.hover_point = None
        if callable(self.on_deactivated):
            self.on_deactivated()

    def _reset(self) -> None:
        self.start_point = None
        self.chain_first_point = None
        self.chain_points.clear()
        self._current_wall_group = None
        self._initial_snap_grp = None
        self._initial_snap_pt = None
        self._initial_snap_type = None
        self._initial_snap_seg = None

    def on_cancel(self, viewport) -> None:
        self._reset()
        viewport.update()

    def _apply_ortho_snap(self, pt: QVector3D, shift_held: bool = False) -> tuple[QVector3D, Optional[str]]:
        """Aplica atracão magnética ortogonal 90° (Eixos X e Y) em relação ao start_point.

        Se Shift estiver pressionado ou o ângulo estiver dentro da tolerância magnética (~15°),
        trava rigidamente o vetor no eixo X ou Y puro.
        Retorna (ponto_ajustado, eixo_travado).
        """
        if self.start_point is None:
            return pt, None

        dx = pt.x() - self.start_point.x()
        dy = pt.y() - self.start_point.y()
        dist = math.hypot(dx, dy)
        if dist < 1e-4:
            return pt, None

        # Ângulo em relação ao eixo X (-180° a +180°)
        angle_deg = math.degrees(math.atan2(dy, dx))
        if angle_deg < 0:
            angle_deg += 360.0

        # Tolerância angular para atração magnética ortogonal (15°)
        tol = 15.0
        axis = None
        # Eixo X positivo (0° ou 360°)
        if shift_held or angle_deg <= tol or angle_deg >= (360.0 - tol):
            if abs(dx) >= abs(dy) or shift_held:
                pt = QVector3D(pt.x(), self.start_point.y(), 0.0)
                axis = "x"
        # Eixo Y positivo (90°)
        elif abs(angle_deg - 90.0) <= tol:
            pt = QVector3D(self.start_point.x(), pt.y(), 0.0)
            axis = "y"
        # Eixo X negativo (180°)
        elif abs(angle_deg - 180.0) <= tol:
            pt = QVector3D(pt.x(), self.start_point.y(), 0.0)
            axis = "x"
        # Eixo Y negativo (270°)
        elif abs(angle_deg - 270.0) <= tol:
            pt = QVector3D(self.start_point.x(), pt.y(), 0.0)
            axis = "y"

        # Se shift estiver pressionado e não caiu nas faixas acima, força o eixo dominante
        if shift_held and axis is None:
            if abs(dx) >= abs(dy):
                pt = QVector3D(pt.x(), self.start_point.y(), 0.0)
                axis = "x"
            else:
                pt = QVector3D(self.start_point.x(), pt.y(), 0.0)
                axis = "y"

        return pt, axis

    def _find_snap_on_existing_walls(
        self, raw_pt: QVector3D, scene, threshold_m: float = 0.25
    ) -> tuple[Optional[QVector3D], Optional[str], Optional[Group], Optional[int]]:
        """Busca vértices ou arestas de paredes existentes (trazomob_wall) próximas ao cursor.

        Retorna (ponto_ajustado, tipo_snap, wall_group, seg_index).
        """
        if scene is None or not hasattr(scene, "groups"):
            return None, None, None, None

        best_pt = None
        best_dist = threshold_m
        best_type = None
        best_grp = None
        best_seg = None

        # 1. Primeiro verifica cantos/vértices das paredes existentes (prioridade alta)
        for g in scene.groups:
            if g is self._current_wall_group:
                continue
            ext = getattr(g, "ext", {})
            if not isinstance(ext, dict) or "trazomob_wall" not in ext:
                continue
            wall_data = ext["trazomob_wall"]
            pts_data = wall_data.get("pontos", [])
            for idx_p, p_coords in enumerate(pts_data):
                p_vec = QVector3D(p_coords[0], p_coords[1], 0.0)
                dist = (p_vec - raw_pt).length()
                if dist < best_dist:
                    best_dist = dist
                    best_pt = p_vec
                    best_type = "canto"
                    best_grp = g
                    best_seg = idx_p

        if best_pt is not None:
            return best_pt, best_type, best_grp, best_seg

        # 2. Se não pegou canto, busca projeção ao longo dos segmentos de parede (junção em T)
        for g in scene.groups:
            if g is self._current_wall_group:
                continue
            ext = getattr(g, "ext", {})
            if not isinstance(ext, dict) or "trazomob_wall" not in ext:
                continue
            wall_data = ext["trazomob_wall"]
            pts_data = wall_data.get("pontos", [])
            is_closed = wall_data.get("is_closed", False)
            n = len(pts_data)
            n_segs = n if is_closed else (n - 1)
            for i in range(n_segs):
                p1 = QVector3D(pts_data[i][0], pts_data[i][1], 0.0)
                p2 = QVector3D(pts_data[(i + 1) % n][0], pts_data[(i + 1) % n][1], 0.0)
                v = p2 - p1
                seg_len = v.length()
                if seg_len < 1e-4:
                    continue
                v_norm = v.normalized()
                proj = QVector3D.dotProduct(raw_pt - p1, v_norm)
                # Verifica se a projeção perpendicular cai dentro do segmento
                if 0.0 <= proj <= seg_len:
                    foot = p1 + v_norm * proj
                    dist = (raw_pt - foot).length()
                    if dist < best_dist:
                        best_dist = dist
                        best_pt = foot
                        best_type = "juncao_t"
                        best_grp = g
                        best_seg = i

        return best_pt, best_type, best_grp, best_seg

    def on_hover(self, ctx: ToolContext) -> None:
        pt = ctx.world
        raw_pt = QVector3D(pt.x(), pt.y(), 0.0)
        shift_held = bool(ctx.modifiers & Qt.ShiftModifier) if hasattr(ctx, "modifiers") else False

        self._snap_info = None
        self._snap_wall_grp = None
        self._snap_wall_seg = None

        # 1. Se não começou ou se o snap da cena pegou aresta/face de parede
        snap_wall_pt, snap_type, snap_grp, snap_seg = self._find_snap_on_existing_walls(raw_pt, getattr(ctx.viewport, "scene", None))

        if snap_wall_pt is not None:
            # Encontrou vértice ou aresta de parede existente
            self.hover_point = snap_wall_pt
            self._snap_info = snap_type  # 'canto' ou 'juncao_t'
            self._snap_wall_grp = snap_grp
            self._snap_wall_seg = snap_seg
            self._locked_axis = None
        elif self.start_point is not None:
            # Trava ortogonal 90° em relação ao start_point
            snapped_pt, self._locked_axis = self._apply_ortho_snap(raw_pt, shift_held=shift_held)
            self.hover_point = snapped_pt
        else:
            self.hover_point = raw_pt
            self._locked_axis = None

        ctx.viewport.update()

    def on_key(self, viewport, key: int, modifiers: Qt.KeyboardModifiers) -> bool:
        """Trata atalhos de teclado da ferramenta: Backspace/Ctrl+Z desfaz ponto, Enter finaliza parede aberta."""
        is_backspace = (key == Qt.Key_Backspace)
        is_ctrl_z = (key == Qt.Key_Z and bool(modifiers & Qt.ControlModifier))

        if is_backspace or is_ctrl_z:
            return self.undo_last_point(viewport)

        # Enter ou Return sem valor no VCB finaliza a cadeia de paredes aberta
        if key in (Qt.Key_Return, Qt.Key_Enter):
            if len(self.chain_points) >= 2:
                self.finish_open_chain(viewport)
                return True

        return False

    def _apply_t_junction_split(
        self,
        scene,
        host_grp: Group,
        snap_pt: QVector3D,
        snap_type: str,
        snap_seg: Optional[int],
        branch_dir: QVector3D,
    ) -> None:
        """Divide a parede hospedeira no ponto de junção T (Split) e abre a face de encontro

        para criar um T ou quina aberta contínua e sem paredes divisórias internas.
        """
        if host_grp is None or scene is None:
            return

        ext = getattr(host_grp, "ext", {})
        if not isinstance(ext, dict) or "trazomob_wall" not in ext:
            return

        wall_data = ext["trazomob_wall"]
        pts_raw = wall_data.get("pontos", [])
        if len(pts_raw) < 2:
            return

        pts = [QVector3D(p[0], p[1], 0.0) for p in pts_raw]
        is_closed = wall_data.get("is_closed", False)
        alturas = wall_data.get("alturas", [wall_data.get("altura", 2.6)])
        esp = wall_data.get("espessura", 0.15)
        alin = wall_data.get("alinhamento", "interno")
        open_q = list(wall_data.get("open_quinas", []))
        open_sa = list(wall_data.get("open_side_a", []))
        open_sb = list(wall_data.get("open_side_b", []))

        # 1. Caso snap_type == "juncao_t": ponto ao longo de um segmento existente
        if snap_type == "juncao_t":
            n = len(pts)
            n_segs = n if is_closed else (n - 1)
            # Localiza o segmento onde o snap_pt está inserido
            seg_idx = None
            if snap_seg is not None and 0 <= snap_seg < n_segs:
                seg_idx = snap_seg
            else:
                for i in range(n_segs):
                    p1 = pts[i]
                    p2 = pts[(i + 1) % n]
                    v = p2 - p1
                    v_len = v.length()
                    if v_len > 1e-4:
                        proj = QVector3D.dotProduct(snap_pt - p1, v.normalized())
                        if 0.0 <= proj <= v_len and (snap_pt - (p1 + v.normalized() * proj)).length() < 0.20:
                            seg_idx = i
                            break

            if seg_idx is not None:
                p1 = pts[seg_idx]
                p2 = pts[(seg_idx + 1) % n]
                seg_v = (p2 - p1).normalized()
                seg_norm = QVector3D(-seg_v.y(), seg_v.x(), 0.0).normalized()

                # Verifica se o snap_pt não coincide com as extremidades
                d1 = (snap_pt - p1).length()
                d2 = (snap_pt - p2).length()
                if d1 > 0.05 and d2 > 0.05:
                    # Insere o novo ponto no hospedeiro
                    insert_idx = seg_idx + 1
                    pts.insert(insert_idx, snap_pt)

                    # Ajusta alturas
                    if len(alturas) > seg_idx:
                        alturas.insert(insert_idx, alturas[seg_idx])

                    # Determina de qual lado da parede a nova ramificação sai:
                    # Se dot(branch_dir, seg_norm) > 0 -> lado da normal (Side B no alinhamento interno/centro)
                    # Senão -> lado oposto (Side A)
                    dot_n = QVector3D.dotProduct(branch_dir.normalized(), seg_norm)
                    if dot_n > 0.0:
                        # Ramificação sai para o lado B
                        if seg_idx not in open_sb:
                            open_sb.append(seg_idx)
                    else:
                        # Ramificação sai para o lado A
                        if seg_idx not in open_sa:
                            open_sa.append(seg_idx)

                    # Abre a quina no novo vértice inserido
                    if insert_idx not in open_q:
                        open_q.append(insert_idx)

        # 2. Caso snap_type == "canto": ponto em quina existente
        elif snap_type == "canto":
            canto_idx = None
            for idx_p, p in enumerate(pts):
                if (p - snap_pt).length() < 0.20:
                    canto_idx = idx_p
                    break
            if canto_idx is not None:
                if canto_idx not in open_q:
                    open_q.append(canto_idx)

        # Reconstrói a parede hospedeira com o ponto inserido e abertura aplicada
        new_host = self.build_chain_group(
            scene=scene,
            pts=pts,
            is_closed=is_closed,
            altura_m=alturas,
            espessura_m=esp,
            alinhamento=alin,
            name_override=host_grp.name,
            open_quinas=open_q,
            open_side_a=open_sa,
            open_side_b=open_sb,
        )

        if host_grp in scene.groups:
            idx_g = scene.groups.index(host_grp)
            scene.groups[idx_g] = new_host
            scene.version += 1
        return new_host

    def finish_open_chain(self, viewport) -> None:
        """Finaliza a construção da parede aberta atual, permitindo iniciar um novo cômodo/divisória."""
        if len(self.chain_points) >= 2 and self._current_wall_group is not None:
            if hasattr(viewport, "flash_status"):
                viewport.flash_status(f"🧱 Parede finalizada com {len(self.chain_points)-1} segmentos!")
        self._reset()
        viewport.update()

    def undo_last_point(self, viewport) -> bool:
        """Remove o último segmento de parede adicionado, retornando ao ponto anterior."""
        if len(self.chain_points) <= 1:
            # Se só tinha o ponto inicial ou nada, reseta o estado da ferramenta
            if self._current_wall_group is not None and self._current_wall_group in viewport.scene.groups:
                viewport.scene.groups.remove(self._current_wall_group)
                viewport.scene.version += 1
            self._reset()
            if hasattr(viewport, "status_message"):
                viewport.status_message("🧱 Início de parede cancelado.")
            viewport.update()
            return True

        # Remove o último vértice confirmado
        self.chain_points.pop()
        self.start_point = self.chain_points[-1]

        if len(self.chain_points) == 1:
            # Sobrou apenas o ponto de início (nenhum segmento completo)
            if self._current_wall_group is not None and self._current_wall_group in viewport.scene.groups:
                viewport.scene.groups.remove(self._current_wall_group)
                viewport.scene.version += 1
            self._current_wall_group = None
            if hasattr(viewport, "status_message"):
                viewport.status_message("🧱 Ponto removido. Pronto para recomeçar o primeiro segmento.")
        else:
            # Reconstrói a parede contínua até o ponto anterior
            new_grp = self.build_chain_group(
                scene=viewport.scene,
                pts=list(self.chain_points),
                is_closed=False,
                altura_m=self.altura_m,
                espessura_m=self.espessura_m,
                alinhamento=self.alinhamento,
                name_override=self._current_wall_group.name if self._current_wall_group else None,
                open_start=bool(self._initial_snap_grp is not None),
            )
            cmd = ReplaceWallGroupCommand(self._current_wall_group, new_grp)
            viewport.history.execute(cmd)
            self._current_wall_group = new_grp
            if hasattr(viewport, "status_message"):
                viewport.status_message(f"🧱 Ponto anterior removido. Segmentos restantes: {len(self.chain_points)-1}")

        viewport.update()
        return True

    def on_click(self, ctx: ToolContext) -> None:
        clicked = QVector3D(ctx.world.x(), ctx.world.y(), 0.0)
        # Se hover_point estiver ativo e ortogonalmente travado, usa a posição ajustada
        if self.start_point is not None and self.hover_point is not None:
            # Se a distância entre o hover travado e o clique for coerente, respeita o alinhamento
            clicked = QVector3D(self.hover_point.x(), self.hover_point.y(), 0.0)

        # Se o hover_point estiver ativo com snap em vértice/parede existente, usa ele mesmo no 1º clique
        if self.start_point is None and getattr(self, "hover_point", None) is not None:
            if getattr(self, "_snap_wall_grp", None) is not None:
                clicked = QVector3D(self.hover_point.x(), self.hover_point.y(), 0.0)

        # 1. Primeiro clique: define início da cadeia de paredes
        if self.start_point is None:
            self.start_point = clicked
            self.chain_first_point = clicked
            self.chain_points = [clicked]
            self._current_wall_group = None
            # Salva se o ponto inicial começou encostado numa parede existente
            self._initial_snap_grp = getattr(self, "_snap_wall_grp", None)
            self._initial_snap_pt = clicked if self._initial_snap_grp is not None else None
            self._initial_snap_type = getattr(self, "_snap_info", None) if self._initial_snap_grp is not None else None
            self._initial_snap_seg = getattr(self, "_snap_wall_seg", None) if self._initial_snap_grp is not None else None
            ctx.viewport.update()
            return

        # Distância mínima para evitar ponto duplicado no mesmo local
        delta = clicked - self.start_point
        if delta.length() < 0.02:
            return

        # 2. Verificar se fechou o ciclo clicando próximo ao ponto inicial da cadeia
        is_closing = False
        if self.chain_first_point is not None and len(self.chain_points) >= 2:
            dist_to_first = (clicked - self.chain_first_point).length()
            if dist_to_first < max(0.20, self.espessura_m * 1.5):
                clicked = self.chain_first_point
                is_closing = True

        # 2b. Verificar se fechou um ciclo apoiando-se em uma parede existente (novo cômodo anexo)
        closing_with_existing = False
        target_snap_grp = getattr(self, "_snap_wall_grp", None)

        # Se não pegou via hover, roda o detector de snap diretamente no ponto clicado
        if target_snap_grp is None:
            snap_c, snap_t, target_snap_grp, _ = self._find_snap_on_existing_walls(clicked, ctx.viewport.scene, threshold_m=0.35)
            if snap_c is not None:
                clicked = snap_c

        if not is_closing and len(self.chain_points) >= 1 and target_snap_grp is not None:
            # Confirma que o ponto clicado encostou em um canto ou ao longo de um segmento da parede existente
            is_at_existing_wall = False
            wall_ext = getattr(target_snap_grp, "ext", {}).get("trazomob_wall", {})
            pts_ext = wall_ext.get("pontos", [])
            for p_c in pts_ext:
                if (QVector3D(p_c[0], p_c[1], 0.0) - clicked).length() < 0.35:
                    is_at_existing_wall = True
                    break

            # Se não bateu exatamente no vértice, verifica se caiu ao longo de uma aresta (junção T)
            if not is_at_existing_wall and len(pts_ext) >= 2:
                n_e = len(pts_ext)
                is_cl_e = wall_ext.get("is_closed", False)
                n_segs_e = n_e if is_cl_e else (n_e - 1)
                for i_e in range(n_segs_e):
                    p1_e = QVector3D(pts_ext[i_e][0], pts_ext[i_e][1], 0.0)
                    p2_e = QVector3D(pts_ext[(i_e + 1) % n_e][0], pts_ext[(i_e + 1) % n_e][1], 0.0)
                    v_e = p2_e - p1_e
                    len_e = v_e.length()
                    if len_e > 1e-4:
                        v_norm = v_e.normalized()
                        proj = QVector3D.dotProduct(clicked - p1_e, v_norm)
                        if 0.0 <= proj <= len_e:
                            foot = p1_e + v_norm * proj
                            if (clicked - foot).length() < 0.35:
                                is_at_existing_wall = True
                                clicked = foot
                                break

            if is_at_existing_wall:
                closing_with_existing = True

        pts_for_build = list(self.chain_points)
        if not is_closing:
            pts_for_build.append(clicked)

        # Se começou ou terminou em parede existente, ativa miter de encaixe e abertura de tampa
        miter_s = bool(self._initial_snap_grp is not None)
        miter_e = bool(target_snap_grp is not None or is_closing)
        open_s = bool(self._initial_snap_grp is not None)
        open_e = bool(closing_with_existing)

        # Constrói o sólido contínuo com cantos em esquadria (miter) fechados
        new_grp = self.build_chain_group(
            scene=ctx.viewport.scene,
            pts=pts_for_build,
            is_closed=is_closing,
            altura_m=self.altura_m,
            espessura_m=self.espessura_m,
            alinhamento=self.alinhamento,
            name_override=self._current_wall_group.name if self._current_wall_group else None,
            miter_start=miter_s,
            miter_end=miter_e,
            open_start=open_s,
            open_end=open_e,
        )

        cmd = ReplaceWallGroupCommand(self._current_wall_group, new_grp)
        ctx.viewport.history.execute(cmd)
        self._current_wall_group = new_grp

        if self.on_wall_added:
            self.on_wall_added(new_grp)

        if is_closing or closing_with_existing:
            # Aplica split e abertura em T se fechou em parede existente
            if closing_with_existing and target_snap_grp is not None and len(self.chain_points) >= 1:
                branch_dir = (clicked - self.chain_points[-1])
                if branch_dir.length() > 1e-4:
                    self._apply_t_junction_split(
                        ctx.viewport.scene,
                        target_snap_grp,
                        clicked,
                        getattr(self, "_snap_info", "juncao_t"),
                        getattr(self, "_snap_wall_seg", None),
                        -branch_dir,
                    )
            # Aplica split e abertura em T na parede inicial se ela era existente
            if self._initial_snap_grp is not None and self._initial_snap_pt is not None and len(self.chain_points) >= 1:
                branch_dir_init = (self.chain_points[1] - self.chain_points[0]) if len(self.chain_points) >= 2 else (clicked - self.chain_points[0])
                if branch_dir_init.length() > 1e-4:
                    self._apply_t_junction_split(
                        ctx.viewport.scene,
                        self._initial_snap_grp,
                        self._initial_snap_pt,
                        self._initial_snap_type or "juncao_t",
                        self._initial_snap_seg,
                        branch_dir_init,
                    )

            # Monta os pontos do contorno completo do cômodo para o piso e teto
            pts_polygon = list(self.chain_points)
            if not is_closing:
                pts_polygon.append(clicked)

            # Gerar automaticamente o piso delimitado pelos cantos
            floor_cmd = self._build_floor(ctx.viewport.scene, pts_polygon)
            if floor_cmd is not None:
                ctx.viewport.history.execute(floor_cmd)

            # Gerar automaticamente o teto no pé-direito se configurado
            created_teto = False
            if getattr(self, "gerar_teto", False):
                # O forro cobre todo o perímetro: uma parede baixa não pode
                # determinar a altura do teto das demais.
                if isinstance(self.altura_m, (list, tuple)):
                    alt = max((float(h) for h in self.altura_m), default=2.60)
                else:
                    alt = float(self.altura_m)
                ceiling_cmd = self._build_ceiling(ctx.viewport.scene, pts_polygon, altura_m=alt)
                if ceiling_cmd is not None:
                    ctx.viewport.history.execute(ceiling_cmd)
                    created_teto = True

            if hasattr(ctx.viewport, "flash_status"):
                if closing_with_existing:
                    msg = "🧱 Cômodo anexo concluído: parede, piso e teto integrados!"
                else:
                    msg = "🧱 Parede, piso e teto criados com sucesso!" if created_teto else "🧱 Perímetro de paredes e piso criados com sucesso!"
                ctx.viewport.flash_status(msg)

            # Secciona as paredes do cômodo em grupos individuais independentes
            if new_grp is not None:
                subs = self.split_wall_group_into_segments(new_grp)
                if len(subs) > 1:
                    cmd_split = SplitWallGroupCommand(new_grp, subs)
                    ctx.viewport.history.execute(cmd_split)
                    self._current_wall_group = None

            self._reset()
        else:
            self.chain_points.append(clicked)
            self.start_point = clicked

        ctx.viewport.update()

    def on_value(self, viewport, value) -> bool:
        """Suporte a digitação direta da medida na caixa de medição (VCB)."""
        if self.start_point is None or self.hover_point is None:
            return False

        direction = self.hover_point - self.start_point
        dist = direction.length()
        if dist < 1e-4:
            return False

        if isinstance(value, (int, float)):
            length_m = float(value)
            # Se digitou em mm (> 50), converte para m
            if length_m > 50.0:
                length_m /= 1000.0
            new_target = self.start_point + direction.normalized() * length_m
            new_target.setZ(0.0)

            pts_for_build = list(self.chain_points) + [new_target]
            new_grp = self.build_chain_group(
                scene=viewport.scene,
                pts=pts_for_build,
                is_closed=False,
                altura_m=self.altura_m,
                espessura_m=self.espessura_m,
                alinhamento=self.alinhamento,
                name_override=self._current_wall_group.name if self._current_wall_group else None,
                open_start=bool(self._initial_snap_grp is not None),
            )

            cmd = ReplaceWallGroupCommand(self._current_wall_group, new_grp)
            viewport.history.execute(cmd)
            self._current_wall_group = new_grp

            if self.on_wall_added:
                self.on_wall_added(new_grp)

            self.chain_points.append(new_target)
            self.start_point = new_target
            self.hover_point = new_target
            viewport.update()
            return True

        return False

    def rubber_band_lines(self):
        """Desenha a prévia dinâmica da parede e de sua espessura enquanto o mouse se move."""
        if self.start_point is None or self.hover_point is None:
            return []

        p0 = self.start_point
        p1 = self.hover_point
        direction = p1 - p0
        dist = direction.length()
        if dist < 1e-4:
            return []

        dir_norm = direction.normalized()
        perp = QVector3D(-dir_norm.y(), dir_norm.x(), 0.0).normalized()

        esp = self.espessura_m
        if self.alinhamento == "interno":
            offset_a = QVector3D(0, 0, 0)
            offset_b = perp * esp
        elif self.alinhamento == "externo":
            offset_a = -perp * esp
            offset_b = QVector3D(0, 0, 0)
        else:  # centro
            offset_a = -perp * (esp / 2.0)
            offset_b = perp * (esp / 2.0)

        # 4 cantos no piso
        c0 = p0 + offset_a
        c1 = p1 + offset_a
        c2 = p1 + offset_b
        c3 = p0 + offset_b

        alt_vec = QVector3D(0, 0, self.altura_m)

        lines = [
            # Base
            (c0, c1), (c1, c2), (c2, c3), (c3, c0),
            # Linha guia central de clique
            (p0, p1),
            # Colunas verticais
            (c0, c0 + alt_vec), (c1, c1 + alt_vec),
            (c2, c2 + alt_vec), (c3, c3 + alt_vec),
            # Topo
            (c0 + alt_vec, c1 + alt_vec),
            (c1 + alt_vec, c2 + alt_vec),
            (c2 + alt_vec, c3 + alt_vec),
            (c3 + alt_vec, c0 + alt_vec),
        ]

        # Se estiver perto do ponto inicial, destaca fechamento
        if self.chain_first_point is not None and len(self.chain_points) >= 2:
            dist_to_first = (p1 - self.chain_first_point).length()
            if dist_to_first < max(0.25, self.espessura_m * 1.5):
                lines.append((p1, self.chain_first_point))

        return lines

    def draw_overlay(self, viewport, painter: QPainter) -> None:
        """Renderiza a cota visual interativa (linha de cota, setas e etiqueta de metragem)

        em tempo real durante o desenho da parede.
        """
        if self.start_point is None or self.hover_point is None:
            return

        p0 = self.start_point
        p1 = self.hover_point
        dist_m = (p1 - p0).length()
        if dist_m < 0.05:
            return

        # Converte pontos 3D do chão para pixels da tela 2D
        p0_px = viewport.world_to_pixel(p0)
        p1_px = viewport.world_to_pixel(p1)
        if p0_px is None or p1_px is None:
            return

        x0, y0 = p0_px
        x1, y1 = p1_px
        dx = x1 - x0
        dy = y1 - y0
        screen_len = math.hypot(dx, dy)
        if screen_len < 10.0:
            return

        ux = dx / screen_len
        uy = dy / screen_len
        # Vetor normal perpendicular à linha na tela (deslocamento para o lado da cota)
        nx = -uy
        ny = ux
        offset_px = 24.0

        # Pontos da linha principal de cota
        cx0 = x0 + nx * offset_px
        cy0 = y0 + ny * offset_px
        cx1 = x1 + nx * offset_px
        cy1 = y1 + ny * offset_px

        painter.save()
        try:
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.TextAntialiasing, True)

            # 1. Linhas de extensão / testemunhas (finas e discretas)
            pen_ext = QPen(QColor(120, 140, 160, 160), 1.0, Qt.DashLine)
            painter.setPen(pen_ext)
            painter.drawLine(QPointF(x0 + nx * 4.0, y0 + ny * 4.0), QPointF(cx0 + nx * 5.0, cy0 + ny * 5.0))
            painter.drawLine(QPointF(x1 + nx * 4.0, y1 + ny * 4.0), QPointF(cx1 + nx * 5.0, cy1 + ny * 5.0))

            # 2. Linha de cota com cor de destaque vibrante (azul elétrico / ciano)
            cota_color = QColor(0, 140, 255)
            pen_cota = QPen(cota_color, 1.8)
            painter.setPen(pen_cota)
            painter.drawLine(QPointF(cx0, cy0), QPointF(cx1, cy1))

            # 3. Setas nas extremidades
            arrow_len = min(10.0, screen_len * 0.25)
            arrow_width = 3.5
            for tip_x, tip_y, sgn in ((cx0, cy0, 1.0), (cx1, cy1, -1.0)):
                wing1_x = tip_x + (ux * sgn) * arrow_len + nx * arrow_width
                wing1_y = tip_y + (uy * sgn) * arrow_len + ny * arrow_width
                wing2_x = tip_x + (ux * sgn) * arrow_len - nx * arrow_width
                wing2_y = tip_y + (uy * sgn) * arrow_len - ny * arrow_width
                painter.drawLine(QPointF(tip_x, tip_y), QPointF(wing1_x, wing1_y))
                painter.drawLine(QPointF(tip_x, tip_y), QPointF(wing2_x, wing2_y))

            # 4. Etiqueta / Badge com as medidas em mm e metros
            dist_mm = int(round(dist_m * 1000.0))
            texto = f"{dist_mm} mm ({dist_m:.2f} m)"

            font = QFont()
            font.setPointSize(10)
            font.setBold(True)
            painter.setFont(font)
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(texto)
            th = fm.height()

            # Ponto médio da cota
            mid_x = (cx0 + cx1) / 2.0
            mid_y = (cy0 + cy1) / 2.0

            pad_x, pad_y = 7, 4
            badge_rect = QRectF(
                mid_x - tw / 2.0 - pad_x,
                mid_y - th / 2.0 - pad_y,
                tw + pad_x * 2,
                th + pad_y * 2,
            )

            # Fundo escuro translúcido com borda suave
            painter.setPen(QPen(cota_color, 1.2))
            painter.setBrush(QColor(24, 28, 36, 220))
            painter.drawRoundedRect(badge_rect, 5.0, 5.0)

            # Texto nítido em branco
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(badge_rect, Qt.AlignCenter, texto)

            # 5. Indicador visual de atração (Snap) em parede existente (Canto ou Junção T)
            snap_info = getattr(self, "_snap_info", None)
            if snap_info in ("canto", "juncao_t"):
                snap_px = viewport.world_to_pixel(p1)
                if snap_px is not None:
                    sx, sy = snap_px
                    is_t = (snap_info == "juncao_t")
                    marker_col = QColor(0, 230, 118) if is_t else QColor(255, 214, 0)  # Verde vibrante para Junção T, Âmbar para Canto
                    label_snap = "┫ Junção em T" if is_t else "⬢ Canto de Parede"

                    # Desenha anel de destaque pulsante no ponto de snap
                    painter.setPen(QPen(marker_col, 2.5))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawEllipse(QPointF(sx, sy), 8.0, 8.0)
                    painter.drawEllipse(QPointF(sx, sy), 3.0, 3.0)

                    # Badge indicador do snap
                    font_snap = QFont()
                    font_snap.setPointSize(9)
                    font_snap.setBold(True)
                    painter.setFont(font_snap)
                    fm_s = painter.fontMetrics()
                    tw_s = fm_s.horizontalAdvance(label_snap)
                    th_s = fm_s.height()

                    s_rect = QRectF(sx + 14, sy - th_s / 2.0 - 4, tw_s + 12, th_s + 8)
                    painter.setPen(QPen(marker_col, 1.2))
                    painter.setBrush(QColor(15, 20, 25, 230))
                    painter.drawRoundedRect(s_rect, 4.0, 4.0)
                    painter.setPen(marker_col)
                    painter.drawText(s_rect, Qt.AlignCenter, label_snap)

        finally:
            painter.restore()

    @classmethod
    def build_chain_group(
        cls,
        scene,
        pts: list[QVector3D],
        is_closed: bool,
        altura_m: float | list[float],
        espessura_m: float,
        alinhamento: str = "interno",
        name_override: Optional[str] = None,
        segment_index: Optional[int] = None,
        miter_start: bool = False,
        miter_end: bool = False,
        open_start: bool = False,
        open_end: bool = False,
        open_quinas: Optional[list[int]] = None,
        open_side_a: Optional[list[int]] = None,
        open_side_b: Optional[list[int]] = None,
        openings: Optional[list[dict[str, any]]] = None,
    ) -> Group:
        """Constrói uma parede contínua única (manifold sólida), com cantos unidos em esquadria."""
        n_pts = len(pts)
        n_segs = n_pts if is_closed else max(0, n_pts - 1)

        if isinstance(altura_m, (int, float)):
            alturas_list = [float(altura_m)] * n_segs
        else:
            alturas_list = [float(h) for h in altura_m]
            if len(alturas_list) < n_segs:
                last_h = alturas_list[-1] if alturas_list else 2.6
                alturas_list.extend([last_h] * (n_segs - len(alturas_list)))
            elif len(alturas_list) > n_segs:
                alturas_list = alturas_list[:n_segs]

        mesh, face_map = cls.compute_wall_mesh(
            pts,
            is_closed,
            alturas_list,
            espessura_m,
            alinhamento,
            miter_start=miter_start,
            miter_end=miter_end,
            open_start=open_start,
            open_end=open_end,
            open_quinas=open_quinas,
            open_side_a=open_side_a,
            open_side_b=open_side_b,
            openings=openings,
        )

        layer_name = "Parede"
        if scene is not None and scene.layer(layer_name) is None:
            scene.layers.append(Layer(layer_name))

        name = name_override or "Parede Contínua"

        # Guarda metadados paramétricos no container para permitir edição dinâmica
        pts_serialized = [[p.x(), p.y(), p.z()] for p in pts]
        from ..domain.entity import set_trazomob
        wall_dict = {
            "pontos": pts_serialized,
            "is_closed": bool(is_closed),
            "altura": float(alturas_list[0]) if alturas_list else 2.6,
            "alturas": [float(h) for h in alturas_list],
            "espessura": float(espessura_m),
            "alinhamento": str(alinhamento),
            "selected_segment": segment_index,
            "face_segment_map": face_map,
            "open_quinas": list(open_quinas) if open_quinas else [],
            "open_side_a": list(open_side_a) if open_side_a else [],
            "open_side_b": list(open_side_b) if open_side_b else [],
            "openings": list(openings) if openings else [],
        }
        ext_data = {
            "trazomob": {"kind": "wall", **wall_dict},
            "trazomob_wall": wall_dict,
            "motion_locked": True,
        }

        grp = Group(mesh, name=name)
        grp.layer = layer_name
        grp.ext = ext_data
        from .paint_catalog import default_wall_material, ensure_wall_paint_material
        ensure_wall_paint_material(scene)
        grp.material = default_wall_material()
        return grp

    @classmethod
    def compute_wall_mesh(
        cls,
        pts: list[QVector3D],
        is_closed: bool,
        altura_m: float | list[float],
        espessura_m: float,
        alinhamento: str = "interno",
        miter_start: bool = False,
        miter_end: bool = False,
        open_start: bool = False,
        open_end: bool = False,
        open_quinas: Optional[list[int]] = None,
        open_side_a: Optional[list[int]] = None,
        open_side_b: Optional[list[int]] = None,
        openings: Optional[list[dict[str, any]]] = None,
    ) -> tuple[Mesh, dict[int, int]]:
        """Delega o calculo da malha 3D de paredes para o WallMeshBuilder."""
        return WallMeshBuilder.compute_wall_mesh(
            pts,
            is_closed,
            altura_m,
            espessura_m,
            alinhamento,
            miter_start=miter_start,
            miter_end=miter_end,
            open_start=open_start,
            open_end=open_end,
            open_quinas=open_quinas,
            open_side_a=open_side_a,
            open_side_b=open_side_b,
            openings=openings,
        )

    def _build_floor(self, scene, points: list[QVector3D]) -> Optional[AddFloorCommand]:
        """Delega a geracao do solido do piso para o WallMeshBuilder."""
        grp = WallMeshBuilder.build_floor_group(scene, points)
        return AddFloorCommand(grp) if grp is not None else None

    def _build_ceiling(self, scene, points: list[QVector3D], altura_m: float = 2.60) -> Optional[AddFloorCommand]:
        """Delega a geracao do solido do teto para o WallMeshBuilder."""
        grp = WallMeshBuilder.build_ceiling_group(scene, points, altura_m=altura_m)
        return AddFloorCommand(grp) if grp is not None else None
    @classmethod
    def split_wall_group_into_segments(cls, mono_group: Group) -> list[Group]:
        """Secciona um grupo monolítico de paredes em grupos individuais independentes."""
        ext = getattr(mono_group, "ext", {})
        p = ext.get("trazomob_wall", {}) if isinstance(ext, dict) else {}

        # 1. Se o grupo foi gerado a partir do WallGraph2D (planta baixa com nós e junções T/X)
        if p.get("is_graph_2d") and "graph_2d" in p:
            from ..wall.plan_2d import WallGraph2D
            g2d = WallGraph2D.from_dict(p["graph_2d"])
            polys = g2d.compute_wall_polygons()
            sub_groups = []
            altura_padrao = p.get("altura", 2.6)
            z_base = float(p.get("z_base", 0.0))
            for sid, seg in g2d.segments.items():
                quad = polys.get(sid)
                if not quad:
                    continue
                s_mesh = Mesh()
                p0, p1, p2, p3 = quad
                c0 = QVector3D(p0[0], p0[1], z_base)
                c1 = QVector3D(p1[0], p1[1], z_base)
                c2 = QVector3D(p2[0], p2[1], z_base)
                c3 = QVector3D(p3[0], p3[1], z_base)
                seg_h = seg.height if getattr(seg, "height", None) is not None else altura_padrao
                seg_zv = QVector3D(0, 0, seg_h)

                s_mesh.add_face([c0, c1, c2, c3])
                s_mesh.add_face([c3 + seg_zv, c2 + seg_zv, c1 + seg_zv, c0 + seg_zv])
                s_mesh.add_face([c0, c0 + seg_zv, c1 + seg_zv, c1])
                s_mesh.add_face([c1, c1 + seg_zv, c2 + seg_zv, c2])
                s_mesh.add_face([c2, c2 + seg_zv, c3 + seg_zv, c3])
                s_mesh.add_face([c3, c3 + seg_zv, c0 + seg_zv, c0])

                for e in s_mesh.edges:
                    if len(e.faces) == 2:
                        n0 = e.faces[0].normal()
                        n1 = e.faces[1].normal()
                        if abs(QVector3D.dotProduct(n0, n1) - 1.0) < 1e-4:
                            e.soft = True

                na = g2d.nodes[seg.node_a_id]
                nb = g2d.nodes[seg.node_b_id]
                len_mm = int(round(seg.length(g2d) * 1000.0))
                sub_grp = Group(s_mesh, name=f"Parede #{sid} ({len_mm} mm)")
                sub_grp.layer = "Parede"
                if getattr(mono_group, "material", None):
                    sub_grp.material = dict(mono_group.material)
                sub_grp.ext = {
                    "trazomob_wall": {
                        "is_segmented": True,
                        "is_graph_2d": True,
                        "graph_2d": p["graph_2d"],
                        "segment_id": sid,
                        "comprimento_mm": len_mm,
                        "altura": seg_h,
                        "espessura": seg.thickness or p.get("espessura", 0.15),
                        "alinhamento": p.get("alinhamento", "centro"),
                        "pontos": [[na.x, na.y, z_base], [nb.x, nb.y, z_base]],
                        "quad_2d": [[p0[0], p0[1]], [p1[0], p1[1]], [p2[0], p2[1]], [p3[0], p3[1]]],
                        "is_closed": False,
                        "openings": [],
                        "z_base": z_base,
                    }
                }
                sub_groups.append(sub_grp)

            # Gera também as colunas estruturais 3D nos nós de junção em T (ou X)
            columns = g2d.compute_columns()
            node_segments = {nid: [] for nid in g2d.nodes}
            for sid, seg in g2d.segments.items():
                node_segments[seg.node_a_id].append(sid)
                node_segments[seg.node_b_id].append(sid)

            for nid, col_quad in columns.items():
                col_mesh = Mesh()
                p0, p1, p2, p3 = col_quad
                c0 = QVector3D(p0[0], p0[1], z_base)
                c1 = QVector3D(p1[0], p1[1], z_base)
                c2 = QVector3D(p2[0], p2[1], z_base)
                c3 = QVector3D(p3[0], p3[1], z_base)

                inc_segs = [g2d.segments[s] for s in node_segments.get(nid, []) if s in g2d.segments]
                col_h = max(
                    (s.height if getattr(s, "height", None) is not None else altura_padrao for s in inc_segs),
                    default=altura_padrao,
                )
                col_th = max(
                    (s.thickness or p.get("espessura", 0.15) for s in inc_segs),
                    default=p.get("espessura", 0.15),
                )
                col_zv = QVector3D(0, 0, col_h)

                # Como col_quad é CCW no plano XY, a ordem das faces com normais apontando para fora (estanque) é:
                col_mesh.add_face([c3, c2, c1, c0])
                col_mesh.add_face([c0 + col_zv, c1 + col_zv, c2 + col_zv, c3 + col_zv])
                col_mesh.add_face([c0, c1, c1 + col_zv, c0 + col_zv])
                col_mesh.add_face([c1, c2, c2 + col_zv, c1 + col_zv])
                col_mesh.add_face([c2, c3, c3 + col_zv, c2 + col_zv])
                col_mesh.add_face([c3, c0, c0 + col_zv, c3 + col_zv])

                for e in col_mesh.edges:
                    if len(e.faces) == 2:
                        n0 = e.faces[0].normal()
                        n1 = e.faces[1].normal()
                        if abs(QVector3D.dotProduct(n0, n1) - 1.0) < 1e-4:
                            e.soft = True

                node_obj = g2d.nodes[nid]
                col_grp = Group(col_mesh, name=f"Coluna #{nid}")
                col_grp.layer = "Parede"
                if getattr(mono_group, "material", None):
                    col_grp.material = dict(mono_group.material)
                col_grp.ext = {
                    "trazomob_wall": {
                        "is_segmented": True,
                        "is_column": True,
                        "is_graph_2d": True,
                        "graph_2d": p["graph_2d"],
                        "node_id": nid,
                        "altura": col_h,
                        "espessura": col_th,
                        "alinhamento": p.get("alinhamento", "centro"),
                        "pontos": [[node_obj.x, node_obj.y, 0.0]],
                        "is_closed": False,
                        "openings": [],
                    }
                }
                sub_groups.append(col_grp)

            if sub_groups:
                return sub_groups

        pts_raw = p.get("pontos", [])
        if len(pts_raw) < 2:
            return [mono_group]

        pts_vec = [QVector3D(pt[0], pt[1], pt[2]) for pt in pts_raw]
        is_closed = p.get("is_closed", False)
        alturas = p.get("alturas", [p.get("altura", 2.6)])
        esp = p.get("espessura", 0.15)
        alin = p.get("alinhamento", "interno")
        openings = p.get("openings", [])

        n_pts = len(pts_vec)
        n_segs = n_pts if is_closed else max(0, n_pts - 1)
        if n_segs <= 1:
            return [mono_group]

        full_mesh, face_map = WallMeshBuilder.compute_wall_mesh(
            pts=pts_vec,
            is_closed=is_closed,
            altura_m=alturas,
            espessura_m=esp,
            alinhamento=alin,
            open_quinas=[],
            openings=openings,
        )

        sub_groups = []
        old_face_attrs = []
        if hasattr(mono_group, "mesh") and hasattr(mono_group.mesh, "faces"):
            old_face_attrs = [f.attrs for f in mono_group.mesh.faces if hasattr(f, "attrs")]

        for s_idx in range(n_segs):
            s_mesh = Mesh()
            seg_face_idxs = [fi for fi, s in face_map.items() if s == s_idx]
            for fi in seg_face_idxs:
                if fi < len(full_mesh.faces):
                    f = full_mesh.faces[fi]
                    new_f = s_mesh.add_face(list(f.vertices))
                    if fi < len(old_face_attrs) and old_face_attrs[fi]:
                        for k in ("color", "texture", "opacity", "mat"):
                            if k in old_face_attrs[fi]:
                                new_f.attrs[k] = old_face_attrs[fi][k]

            for e in s_mesh.edges:
                if len(e.faces) == 2:
                    n0 = e.faces[0].normal()
                    n1 = e.faces[1].normal()
                    if abs(QVector3D.dotProduct(n0, n1) - 1.0) < 1e-4:
                        e.soft = True

            pA = pts_vec[s_idx]
            pB = pts_vec[(s_idx + 1) % n_pts]
            len_mm = int(round((pB - pA).length() * 1000.0))

            h_val = alturas[s_idx] if s_idx < len(alturas) else (alturas[0] if alturas else 2.6)
            seg_dict = {
                "segment_index": s_idx,
                "comprimento_mm": len_mm,
                "altura": float(h_val),
                "alturas": [float(h_val)],
                "espessura": float(esp),
                "alinhamento": str(alin),
                "p0": [pA.x(), pA.y(), pA.z()],
                "p1": [pB.x(), pB.y(), pB.z()],
                "parent_room": mono_group.name,
                "all_room_pts": pts_raw,
                "is_closed": bool(is_closed),
                "openings": [op for op in openings if int(op.get("segment_index", 0)) == s_idx],
                "pontos": [[pA.x(), pA.y(), pA.z()], [pB.x(), pB.y(), pB.z()]],
                "is_segmented": True,
            }

            wg = Group(s_mesh, name=f"Parede #{s_idx + 1} ({len_mm} mm)")
            wg.layer = getattr(mono_group, "layer", "Parede")
            wg.ext = {
                "trazomob": {"kind": "wall", **seg_dict},
                "trazomob_wall": seg_dict,
                "motion_locked": True,
            }
            if getattr(mono_group, "material", None):
                wg.material = dict(mono_group.material)

            sub_groups.append(wg)

        return sub_groups


