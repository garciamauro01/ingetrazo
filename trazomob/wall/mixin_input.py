# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Diálogo 2D de Planta Baixa para desenho de paredes e geração 3D automática."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional, List, Tuple

from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import (
    QPainter,
    QPen,
    QColor,
    QBrush,
    QFont,
    QPolygonF,
    QWheelEvent,
    QMouseEvent,
    QKeyEvent,
    QPixmap,
    QTransform,
)
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QDoubleSpinBox,
    QCheckBox,
    QFrame,
    QSplitter,
    QToolButton,
    QButtonGroup,
    QInputDialog,
    QComboBox,
    QSlider,
    QFileDialog,
    QGroupBox,
    QScrollArea,
    QMessageBox,
)

from PySide6.QtGui import QVector3D
from core.image_plane import ImagePlane
from core.units import format_length, model_unit, model_precision, bare_number_scale
from ..wall.plan_2d import WallGraph2D, WallNode2D, dist_2d
from ..wall.mesh_builder import WallMeshBuilder

if TYPE_CHECKING:
    Point2D = Tuple[float, float]


class InputHandlingMixin:
    """Manipulacao de eventos de entrada (mouse/teclado) do canvas."""

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and event.modifiers() & Qt.AltModifier):
            self._pan_start = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            return

        if event.button() == Qt.RightButton:
            if self._start_pt is not None:
                # Se estava no meio do desenho da parede, cancelar traço
                self._start_pt = None
                self._selected_seg_id = None
                self._selected_node_id = None
                self._drag_node_id = None
                self.update()
                return
            else:
                # Se não havia traço ativo, botão direito funciona como Pan fluido
                self._selected_seg_id = None
                self._selected_node_id = None
                self._drag_node_id = None
                self._pan_start = event.position()
                self.setCursor(Qt.ClosedHandCursor)
                self.update()
                return

        if event.button() == Qt.LeftButton:
            wx, wy = self.screen_to_world(event.position().x(), event.position().y())
            click_pos = event.position()

            # Modo Mover Imagem de Referência
            if self.mode == "mover_ref":
                if self._ref_pixmap is not None:
                    self._drag_ref_start = (wx, wy)
                    self._drag_ref_initial_pos = self._ref_pos_world
                    self.setCursor(Qt.ClosedHandCursor)
                    return

            # Modo Calibrar Imagem de Referência: dois cliques definem a distância conhecida
            if self.mode == "calibrar_ref":
                if self._ref_pixmap is None:
                    return
                if not self._calib_points:
                    self._calib_points.append((wx, wy))
                    self._current_mouse_world = (wx, wy)
                    self.update()
                    return

                p1 = self._calib_points[0]
                measured = dist_2d(p1, (wx, wy))
                self._calib_points.clear()
                if measured > 1e-6:
                    self._prompt_calibrate_scale(measured)

                # Finaliza a calibração e volta para a ferramenta de desenho
                self.mode = "linha"
                window = self.window()
                set_mode = getattr(window, "_set_mode", None)
                if callable(set_mode):
                    set_mode("linha")
                else:
                    self.update_cursor()
                self.update()
                return

            # Modo Cotar: suporte a clique direto na parede ou seleção de 2 pontos livres
            if self.mode == "cota":
                # 1. Checa se o usuário clicou em um PONTO notável (canto de face ou nó do grafo)
                snap_pt, has_point_snap = self._snap_point_or_face(wx, wy)

                if has_point_snap or len(self._cota_points) > 0:
                    # O usuário clicou em um ponto (ou já está no meio da seleção de 2 pontos)
                    if len(self._cota_points) == 0:
                        # Primeiro ponto selecionado: armazena e NÃO abre caixa de diálogo de cotar!
                        # Fica aguardando o clique no segundo ponto.
                        self._cota_points.append(snap_pt)
                        self.update()
                        return
                    elif len(self._cota_points) == 1:
                        # Segundo ponto selecionado: cria a cota como anotação e abre o diálogo
                        p1 = self._cota_points[0]
                        p2 = snap_pt
                        self._cota_points.clear()
                        if dist_2d(p1, p2) > 0.01:
                            self._save_history()
                            seg_assoc = self._find_segment_for_dimension(p1, p2)
                            dim_id = self.graph.add_dimension(
                                p1, p2, seg_id=seg_assoc, driving=False
                            )
                            self._selected_dim_id = dim_id
                            self._selected_seg_id = None
                            self._selected_node_id = None
                            self.update()
                            if dim_id is not None:
                                try:
                                    self._edit_custom_dimension_dialog(dim_id, is_new=True)
                                except TypeError:
                                    self._edit_custom_dimension_dialog(dim_id)
                        return

                # 2. Se NÃO clicou em nenhum ponto e ainda não iniciou pontos, checa se clicou diretamente em uma LINHA
                # Prioridade: linha/aresta da face real da parede onde o usuário clicou (interna ou externa)
                polys = self.graph.compute_wall_polygons()
                best_face_edge = None
                best_face_dist = 0.20
                best_face_sid = None

                for sid, quad in polys.items():
                    for i in range(4):
                        p_a = quad[i]
                        p_b = quad[(i + 1) % 4]
                        dx = p_b[0] - p_a[0]
                        dy = p_b[1] - p_a[1]
                        l2 = dx * dx + dy * dy
                        if l2 < 0.04:  # ignora tampas transversais menores que a espessura
                            continue
                        t = max(0.0, min(1.0, ((wx - p_a[0]) * dx + (wy - p_a[1]) * dy) / l2))
                        proj = (p_a[0] + t * dx, p_a[1] + t * dy)
                        d = dist_2d((wx, wy), proj)
                        if d < best_face_dist:
                            best_face_dist = d
                            best_face_edge = (p_a, p_b)
                            best_face_sid = sid

                if best_face_edge is not None and best_face_sid is not None:
                    # Clicou diretamente na linha da face específica (interna ou externa):
                    p1_face, p2_face = best_face_edge
                    self._save_history()
                    dim_id = self.graph.add_dimension(
                        p1_face, p2_face, seg_id=best_face_sid, driving=False
                    )
                    self._selected_dim_id = dim_id
                    self._selected_seg_id = None
                    self._selected_node_id = None
                    self.update()
                    if dim_id is not None:
                        try:
                            self._edit_custom_dimension_dialog(dim_id, is_new=True)
                        except TypeError:
                            self._edit_custom_dimension_dialog(dim_id)
                    return

                hit_seg_cota = self.graph.find_segment_at(wx, wy, threshold=0.25)
                if hit_seg_cota is not None and hit_seg_cota in self.graph.segments:
                    # Clicou no eixo central
                    seg = self.graph.segments[hit_seg_cota]
                    na = self.graph.nodes[seg.node_a_id]
                    nb = self.graph.nodes[seg.node_b_id]
                    self._save_history()
                    dim_id = self.graph.add_dimension(
                        na.pt, nb.pt, seg_id=hit_seg_cota, driving=False
                    )
                    self._selected_dim_id = dim_id
                    self._selected_seg_id = None
                    self._selected_node_id = None
                    self.update()
                    if dim_id is not None:
                        try:
                            self._edit_custom_dimension_dialog(dim_id, is_new=True)
                        except TypeError:
                            self._edit_custom_dimension_dialog(dim_id)
                    return
                else:
                    # Clicou no vazio: marca o primeiro ponto livre e aguarda o segundo
                    self._cota_points.append((wx, wy))
                    self.update()
                    return

            # Ferramenta de pontos: clique na parede divide; clique no ponto une.
            if self.mode == "pontos":
                hit_node = self.graph.find_node_at(wx, wy, threshold=0.25)
                if hit_node is not None:
                    pair = self.graph.mergeable_segments_at(hit_node)
                    if pair is None:
                        self._selected_node_id = hit_node
                        self._selected_seg_id = None
                        self._selected_dim_id = None
                        self.point_edit_hint.emit(
                            "Este ponto não pode ser removido: só é possível unir "
                            "trechos colineares com a mesma altura e espessura."
                        )
                        self.update()
                        return
                    self._save_history()
                    merged_id = self.graph.merge_node(hit_node)
                    self._selected_node_id = None
                    self._selected_seg_id = merged_id
                    self._selected_dim_id = None
                    self.wall_count_changed.emit(len(self.graph.segments))
                    if merged_id is not None:
                        seg_len = self.graph.segments[merged_id].length(self.graph)
                        self.wall_selected.emit(merged_id, seg_len)
                    self.point_edit_hint.emit(
                        "🔗 Ponto removido: os dois trechos agora formam uma parede única."
                    )
                    self.update()
                    return

                hit_seg = self.graph.find_segment_at(wx, wy, threshold=0.30)
                if hit_seg is not None and hit_seg in self.graph.segments:
                    seg = self.graph.segments[hit_seg]
                    na = self.graph.nodes.get(seg.node_a_id)
                    nb = self.graph.nodes.get(seg.node_b_id)
                    if na is not None and nb is not None:
                        proj, t = self.graph._project_point_on_segment(
                            (wx, wy), na.pt, nb.pt
                        )
                        if t <= 0.03 or t >= 0.97:
                            self.point_edit_hint.emit(
                                "Ponto não adicionado: clique no meio do trecho, "
                                "longe das extremidades."
                            )
                            self.update()
                            return
                        self._save_history()
                        n_before = len(self.graph.segments)
                        new_node_id = self.graph.split_segment(hit_seg, t)
                        if new_node_id is not None and len(self.graph.segments) > n_before:
                            self._selected_node_id = new_node_id
                            self._selected_seg_id = None
                            self._selected_dim_id = None
                            self.wall_count_changed.emit(len(self.graph.segments))
                            self.point_edit_hint.emit(
                                "➕ Ponto adicionado: a parede foi dividida em dois trechos."
                            )
                        else:
                            self.point_edit_hint.emit(
                                "Ponto não adicionado: escolha um trecho válido da parede."
                            )
                        self.update()
                        return

                self._selected_node_id = None
                self._selected_seg_id = None
                self._selected_dim_id = None
                self.point_edit_hint.emit(
                    "Clique sobre uma parede para adicionar um ponto ou sobre um "
                    "ponto interno para removê-lo e unir os trechos."
                )
                self.update()
                return

            # 1. PRIORIDADE ABSOLUTA: Checa se clicou na alça de arraste (grip do ponto médio) da parede selecionada
            if self._start_pt is None and self._selected_seg_id is not None and self._selected_seg_id in self.graph.segments:
                seg_cur = self.graph.segments[self._selected_seg_id]
                na_c = self.graph.nodes.get(seg_cur.node_a_id)
                nb_c = self.graph.nodes.get(seg_cur.node_b_id)
                if na_c and nb_c:
                    sp_mid = self.world_to_screen((na_c.x + nb_c.x) / 2.0, (na_c.y + nb_c.y) / 2.0)
                    px_dist = math.hypot(click_pos.x() - sp_mid.x(), click_pos.y() - sp_mid.y())
                    # Tolerância de 15 pixels na tela ou 0.25m no mundo
                    m_wx = (na_c.x + nb_c.x) / 2.0
                    m_wy = (na_c.y + nb_c.y) / 2.0
                    if px_dist <= 15.0 or dist_2d((wx, wy), (m_wx, m_wy)) <= 0.25:
                        self._drag_mid_seg_id = self._selected_seg_id
                        self._drag_mid_start_mouse = (wx, wy)
                        self._save_history()
                        self.setCursor(Qt.SizeAllCursor)
                        self.update()
                        return

            # Se estiver no modo selecionar:
            if self.mode == "selecionar":
                # 1. Checa se clicou em um badge de cota
                for bid, binfo in self._dimension_badges.items():
                    if binfo["rect"].contains(click_pos):
                        if binfo.get("dim_id") is not None:
                            self._selected_dim_id = binfo["dim_id"]
                            self._selected_seg_id = None
                            self._selected_node_id = None
                            self._drag_dim_id = binfo["dim_id"]
                            self._drag_dim_start_mouse = (wx, wy)
                            self._save_history()
                            self.update()
                            return
                        elif binfo.get("seg_id") is not None:
                            self._selected_seg_id = binfo["seg_id"]
                            self._selected_node_id = None
                            self._selected_dim_id = None
                            seg_len = self.graph.segments[binfo["seg_id"]].length(self.graph)
                            self.wall_selected.emit(binfo["seg_id"], seg_len)
                            self.update()
                            return

                # 2. Checa se clicou na linha de alguma cota personalizada
                for did, d_obj in self.graph.dimensions.items():
                    p1_s = self.world_to_screen(d_obj.p1[0], d_obj.p1[1])
                    p2_s = self.world_to_screen(d_obj.p2[0], d_obj.p2[1])
                    dx_s = p2_s.x() - p1_s.x()
                    dy_s = p2_s.y() - p1_s.y()
                    L_s = math.hypot(dx_s, dy_s)
                    if L_s > 1.0:
                        nx_s = -dy_s / L_s
                        ny_s = dx_s / L_s
                        off_px = d_obj.offset * self._zoom
                        c1 = QPointF(p1_s.x() + nx_s * off_px, p1_s.y() + ny_s * off_px)
                        c2 = QPointF(p2_s.x() + nx_s * off_px, p2_s.y() + ny_s * off_px)
                        # Distância do clique ao segmento (c1 -> c2) em pixels
                        line_vec = (c2.x() - c1.x(), c2.y() - c1.y())
                        pt_vec = (click_pos.x() - c1.x(), click_pos.y() - c1.y())
                        t_proj = max(0.0, min(1.0, (pt_vec[0] * line_vec[0] + pt_vec[1] * line_vec[1]) / (L_s * L_s)))
                        proj_px = (c1.x() + t_proj * line_vec[0], c1.y() + t_proj * line_vec[1])
                        d_click = math.hypot(click_pos.x() - proj_px[0], click_pos.y() - proj_px[1])
                        if d_click <= 8.0:
                            self._selected_dim_id = did
                            self._selected_seg_id = None
                            self._selected_node_id = None
                            self._drag_dim_id = did
                            self._drag_dim_start_mouse = (wx, wy)
                            self._save_history()
                            self.update()
                            return

                hit_node = self.graph.find_node_at(wx, wy, threshold=0.25)
                if hit_node is not None:
                    self._selected_node_id = hit_node
                    self._selected_seg_id = None
                    self._selected_dim_id = None
                    self._drag_node_id = hit_node
                    self._drag_start_mouse = (wx, wy)
                    self._save_history()
                    self.update()
                    return

                hit_seg = self.graph.find_segment_at(wx, wy, threshold=0.25)
                if hit_seg is not None:
                    self._selected_seg_id = hit_seg
                    self._selected_node_id = None
                    self._selected_dim_id = None
                    seg_len = self.graph.segments[hit_seg].length(self.graph)
                    self.wall_selected.emit(hit_seg, seg_len)
                    self.update()
                    return

                # Clicou no vazio: desmarca e atualiza os inputs para os padrões globais
                self._selected_node_id = None
                self._selected_seg_id = None
                self._selected_dim_id = None
                self.wall_selected.emit(0, 0.0)
                self.update()
                return

            # Se não estiver no meio de um traço (_start_pt is None), checa seleção no modo linha
            if self._start_pt is None:
                clicked_dim_seg = None
                clicked_dim_id = None
                for bid, binfo in self._dimension_badges.items():
                    if binfo["rect"].contains(click_pos):
                        clicked_dim_seg = binfo.get("seg_id")
                        clicked_dim_id = binfo.get("dim_id")
                        break

                if clicked_dim_id is not None:
                    self._selected_dim_id = clicked_dim_id
                    self._selected_seg_id = None
                    self._selected_node_id = None
                    self._start_pt = None
                    self.update()
                    return

                # No modo 'linha', um clique sobre uma parede existente NÃO deve apenas selecioná-la e bloquear
                # o desenho; ele deve ancorar e iniciar a nova parede (ex: divisória ou cômodo anexo)!
                hit_seg = clicked_dim_seg if clicked_dim_seg is not None else self.graph.find_segment_at(wx, wy, threshold=0.20)
                hit_node = self.graph.find_node_at(wx, wy, threshold=0.20)
                if clicked_dim_seg is not None and hit_seg is not None and hit_node is None:
                    self._selected_seg_id = hit_seg
                    self._selected_node_id = None
                    self._selected_dim_id = None
                    self._start_pt = None
                    seg_len = self.graph.segments[hit_seg].length(self.graph)
                    self.wall_selected.emit(hit_seg, seg_len)
                    self.update()
                    return
                elif hit_node is None and clicked_dim_seg is None:
                    if self._selected_seg_id is not None or self._selected_dim_id is not None:
                        self._selected_seg_id = None
                        self._selected_dim_id = None
                        self.wall_selected.emit(0, 0.0)
                        self.update()

            # Modo de desenho ("linha" ou "retangulo")
            # 1. Aplica alinhamento com outros pontos/nós da cena (guias X e Y)
            wx, wy = self._align_to_existing_points(wx, wy)

            # 2. Aplica snap a cantos ou paredes
            wx, wy, _ = self.graph.snap_point(wx, wy, threshold=0.25)

            # 3. Snap ortogonal a 90 graus se shift ou se próximo do ponto inicial
            if self._start_pt is not None:
                wx, wy = self._ortho_align(self._start_pt, (wx, wy), force_ortho=bool(event.modifiers() & Qt.ShiftModifier))

            if self.mode == "linha":
                if self._start_pt is None:
                    self._start_pt = (wx, wy)
                else:
                    # Ignora clique acidental no mesmo ponto de in?cio (evita cancelar o tra?o da parede)
                    if math.hypot(wx - self._start_pt[0], wy - self._start_pt[1]) < 0.05:
                        return

                    self._save_history()
                    seg_id = self.graph.add_segment(self._start_pt[0], self._start_pt[1], wx, wy)
                    self.graph.merge_close_nodes(threshold=0.25)
                    self.wall_count_changed.emit(len(self.graph.segments))

                    # Verifica se o ponto final conectou a um nó que já tinha paredes (fechando o cômodo/ciclo)
                    # Se fechou um ciclo, encerra a cadeia contínua para não puxar mais segmentos
                    end_node_id = self.graph.find_node_at(wx, wy, threshold=0.25)
                    deg = 0
                    if end_node_id is not None:
                        deg = sum(1 for s in self.graph.segments.values() if s.node_a_id == end_node_id or s.node_b_id == end_node_id)

                    if deg >= 2:
                        # Fechou o cômodo ou conectou a um canto/T existente: encerra o traço contínuo
                        self._start_pt = None
                    else:
                        self._start_pt = (wx, wy)
            elif self.mode == "retangulo":
                if self._start_pt is None:
                    self._start_pt = (wx, wy)
                else:
                    self._save_history()
                    x0, y0 = self._start_pt
                    x1, y1 = wx, wy
                    self.graph.add_segment(x0, y0, x1, y0)
                    self.graph.add_segment(x1, y0, x1, y1)
                    self.graph.add_segment(x1, y1, x0, y1)
                    self.graph.add_segment(x0, y1, x0, y0)
                    self.graph.merge_close_nodes(threshold=0.25)
                    self._start_pt = None
                    self.wall_count_changed.emit(len(self.graph.segments))

            self.update()

    def _align_to_existing_points(self, wx: float, wy: float, tol_px: float = 12.0) -> Tuple[float, float]:
        """Detecta alinhamento horizontal (mesmo Y) e vertical (mesmo X) com nós existentes e cria guias."""
        self._align_guides.clear()
        tol_m = tol_px / max(1.0, self._zoom)

        best_x = wx
        best_y = wy
        min_dx = tol_m
        min_dy = tol_m
        align_node_x = None
        align_node_y = None

        for nid, node in self.graph.nodes.items():
            # Não alinha consigo mesmo se estiver arrastando
            if nid == self._drag_node_id:
                continue

            # Alinhamento vertical (mesmo X)
            dx = abs(node.x - wx)
            if dx <= min_dx:
                min_dx = dx
                best_x = node.x
                align_node_x = node

            # Alinhamento horizontal (mesmo Y)
            dy = abs(node.y - wy)
            if dy <= min_dy:
                min_dy = dy
                best_y = node.y
                align_node_y = node

        # Registra as linhas de guia para desenhar na tela
        if align_node_x is not None:
            p_top = self.world_to_screen(best_x, align_node_x.y)
            p_cur = self.world_to_screen(best_x, best_y)
            self._align_guides.append((p_top, p_cur))

        if align_node_y is not None:
            p_lat = self.world_to_screen(align_node_y.x, best_y)
            p_cur = self.world_to_screen(best_x, best_y)
            self._align_guides.append((p_lat, p_cur))

        return best_x, best_y

    def _snap_point_or_face(self, wx: float, wy: float) -> Tuple[Point2D, bool]:
        """Ancora no ponto notável mais próximo (canto de face ou nó do grafo).

        Retorna:
            (ponto_snappado, foi_encontrado_ponto_notavel)
        """
        best_pt = (wx, wy)
        min_dist = 0.22  # tolerância precisa de snap

        # 1. Cantos reais das faces da parede (face interna e face externa)
        polys = self.graph.compute_wall_polygons()
        found = False
        for quad in polys.values():
            for corner in quad:
                d = dist_2d((wx, wy), corner)
                if d < min_dist:
                    min_dist = d
                    best_pt = corner
                    found = True

        # 2. Se não estiver perto de nenhum canto da face, checa os nós centrais do grafo
        for node in self.graph.nodes.values():
            d = dist_2d((wx, wy), (node.x, node.y))
            if d < min_dist:
                min_dist = d
                best_pt = (node.x, node.y)
                found = True

        # 3. Snap nos pontos das linhas de underlay (projeção do andar inferior)
        if not found and self._underlay_lines:
            for p_a, p_b in self._underlay_lines:
                for pt in (p_a, p_b):
                    d = dist_2d((wx, wy), pt)
                    if d < min_dist:
                        min_dist = d
                        best_pt = pt
                        found = True

        return best_pt, found

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Duplo clique em um selo de cômodo, cota ou parede para editar numericamente/renomear."""
        click_pos = event.position()

        # 0. Checa se clicou no selo do cômodo (para renomear o ambiente)
        for r_badge in self._room_badges:
            if r_badge["rect"].contains(click_pos):
                self._edit_room_name_dialog(r_badge["cycle_pts"], r_badge["name"], r_badge["area_m2"])
                return

        target_seg_id = None
        target_dim_id = None
        target_len_m = None

        # 1. Checa se clicou no badge de cota
        for bid, binfo in self._dimension_badges.items():
            if binfo["rect"].contains(click_pos):
                target_seg_id = binfo.get("seg_id")
                target_dim_id = binfo.get("dim_id")
                target_len_m = binfo["length_m"]
                break

        if target_dim_id is not None:
            self._edit_custom_dimension_dialog(target_dim_id)
            return

        # 2. Se não clicou no badge, checa se clicou próximo de alguma parede
        if target_seg_id is None:
            wx, wy = self.screen_to_world(click_pos.x(), click_pos.y())
            target_seg_id = self.graph.find_segment_at(wx, wy, threshold=0.30)

        if target_seg_id is not None:
            self._edit_segment_length_dialog(target_seg_id, current_face_len=target_len_m)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._pan_start is not None:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self._offset_x += delta.x()
            self._offset_y += delta.y()
            self.update()
            return

        wx, wy = self.screen_to_world(event.position().x(), event.position().y())

        # Arrastar imagem de referência
        if self.mode == "mover_ref" and self._drag_ref_start is not None and self._drag_ref_initial_pos is not None:
            dwx = wx - self._drag_ref_start[0]
            dwy = wy - self._drag_ref_start[1]
            self._ref_pos_world = (self._drag_ref_initial_pos[0] + dwx, self._drag_ref_initial_pos[1] + dwy)
            self.update()
            return

        # No modo calibrar imagem, atualiza tela para desenhar linha elástica
        if self.mode == "calibrar_ref":
            self._current_mouse_world = (wx, wy)
            self.update()
            return

        # Se estiver arrastando a linha de afastamento (offset) de uma cota selecionada:
        if self._drag_dim_id is not None and self._drag_dim_start_mouse is not None:
            dim_cur = self.graph.dimensions.get(self._drag_dim_id)
            if dim_cur:
                dx = dim_cur.p2[0] - dim_cur.p1[0]
                dy = dim_cur.p2[1] - dim_cur.p1[1]
                L = math.hypot(dx, dy)
                if L > 1e-4:
                    # Vetor normal unitário no plano mundo
                    nx = -dy / L
                    ny = dx / L
                    # Projeção do vetor de p1 ao mouse atual sobre a normal
                    proj_offset = (wx - dim_cur.p1[0]) * nx + (wy - dim_cur.p1[1]) * ny
                    dim_cur.offset = proj_offset
                    self.update()
                    return

        # Se estiver arrastando um nó (ex: junção em T ou canto de parede):
        # Se estiver arrastando a al?a m?dia da parede (deslocamento paralelo):
        if self._drag_mid_seg_id is not None and self._drag_mid_start_mouse is not None:
            seg = self.graph.segments.get(self._drag_mid_seg_id)
            if seg:
                na = self.graph.nodes.get(seg.node_a_id)
                nb = self.graph.nodes.get(seg.node_b_id)
                if na and nb:
                    dx = nb.x - na.x
                    dy = nb.y - na.y
                    L = math.hypot(dx, dy)
                    if L > 1e-6:
                        nx, ny = -dy / L, dx / L
                        mdx = wx - self._drag_mid_start_mouse[0]
                        mdy = wy - self._drag_mid_start_mouse[1]
                        proj_dist = mdx * nx + mdy * ny
                        shift_x = nx * proj_dist
                        shift_y = ny * proj_dist
                        self.graph.move_node(seg.node_a_id, na.x + shift_x, na.y + shift_y)
                        self._drag_mid_start_mouse = (wx, wy)
                        self.update()
                        return

        if self._drag_node_id is not None:
            self.update_cursor(hovering_handle=True)
            # Alinha com outros nós
            wx, wy = self._align_to_existing_points(wx, wy)
            # Aplica snap ortogonal ou de grid se shift estiver pressionado
            if bool(event.modifiers() & Qt.ShiftModifier) and self._drag_start_mouse:
                wx, wy = self._ortho_align(self._drag_start_mouse, (wx, wy), force_ortho=True)
            self.graph.move_node(self._drag_node_id, wx, wy)
            self._current_mouse_world = (wx, wy)
            self.update()
            return

        # Verifica se o mouse está pairando sobre a alça de arraste da parede selecionada
        hover_grip = False
        if self.mode == "selecionar" and self._selected_seg_id is not None and self._selected_seg_id in self.graph.segments:
            seg_h = self.graph.segments[self._selected_seg_id]
            na_h = self.graph.nodes.get(seg_h.node_a_id)
            nb_h = self.graph.nodes.get(seg_h.node_b_id)
            if na_h and nb_h:
                sp_mid = self.world_to_screen((na_h.x + nb_h.x) / 2.0, (na_h.y + nb_h.y) / 2.0)
                if math.hypot(event.position().x() - sp_mid.x(), event.position().y() - sp_mid.y()) <= 15.0:
                    hover_grip = True

        if hover_grip:
            self.setCursor(Qt.SizeAllCursor)
        elif self.mode == "selecionar":
            hover_nid = self.graph.find_node_at(wx, wy, threshold=0.25)
            self.update_cursor(hovering_handle=(hover_nid is not None))
        else:
            self.update_cursor()

        if self.mode == "cota":
            # No modo cota, destaca os cantos das faces da parede e não força o centro
            self._snap_info = None
            snap_cota, has_snap = self._snap_point_or_face(wx, wy)
            if has_snap and dist_2d((wx, wy), snap_cota) < 0.20:
                wx, wy = snap_cota
                self._snap_info = "canto"
        else:
            # 1. Alinha com outros pontos existentes (guias inteligentes tipo CAD)
            wx, wy = self._align_to_existing_points(wx, wy)

            # 2. Snap magnético para canto ou parede
            wx, wy, snap_type = self.graph.snap_point(wx, wy, threshold=0.25)
            self._snap_info = snap_type

        # Se estiver preparando o primeiro ponto da parede e passar o mouse sobre uma parede existente
        if self._start_pt is None and self.mode == "linha" and snap_type == "parede":
            seg_id = self.graph.find_segment_at(wx, wy, threshold=0.30)
            if seg_id is not None:
                seg = self.graph.segments[seg_id]
                na = self.graph.nodes[seg.node_a_id]
                nb = self.graph.nodes[seg.node_b_id]
                proj, t = self.graph._project_point_on_segment((wx, wy), na.pt, nb.pt)
                d_a = dist_2d(na.pt, proj)
                d_b = dist_2d(nb.pt, proj)
                ref_node = na if d_a <= d_b else nb
                other_node = nb if d_a <= d_b else na
                dist_val = d_a if d_a <= d_b else d_b

                dx = other_node.x - ref_node.x
                dy = other_node.y - ref_node.y
                L = math.hypot(dx, dy)
                u_dir = (dx / L, dy / L) if L > 1e-6 else (1.0, 0.0)

                self._t_ref_info = {
                    "seg_id": seg_id,
                    "ref_node_id": ref_node.id,
                    "ref_pt": ref_node.pt,
                    "other_pt": other_node.pt,
                    "proj_pt": proj,
                    "u_dir": u_dir,
                    "distance_m": dist_val,
                }
                if not self._type_buffer:
                    self.current_length_changed.emit(dist_val)
            else:
                self._t_ref_info = None
        elif self._start_pt is None:
            self._t_ref_info = None

        # 3. Snap ortogonal
        if self._start_pt is not None:
            wx, wy = self._ortho_align(self._start_pt, (wx, wy), force_ortho=bool(event.modifiers() & Qt.ShiftModifier))
            cur_len = dist_2d(self._start_pt, (wx, wy))
            dx = wx - self._start_pt[0]
            dy = wy - self._start_pt[1]
            if cur_len > 1e-4:
                ux, uy = dx / cur_len, dy / cur_len
                ext = self.graph.get_start_extension(self._start_pt, (ux, uy))
                visible_len = max(0.01, cur_len - ext)
            else:
                visible_len = cur_len
            self.current_length_changed.emit(visible_len)

        self._current_mouse_world = (wx, wy)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() in (Qt.MiddleButton, Qt.RightButton) or (event.button() == Qt.LeftButton and self._pan_start is not None):
            self._pan_start = None
            self.update_cursor()

        if event.button() == Qt.LeftButton and self._drag_dim_id is not None:
            self._drag_dim_id = None
            self._drag_dim_start_mouse = None
            self.update_cursor()
            self.update()

        if event.button() == Qt.LeftButton and self._drag_mid_seg_id is not None:
            self._drag_mid_seg_id = None
            self._drag_mid_start_mouse = None
            self.update_cursor()
            self.update()

        if event.button() == Qt.LeftButton and self._drag_ref_start is not None:
            self._drag_ref_start = None
            self._drag_ref_initial_pos = None
            self.update_cursor()
            self.update()

        if event.button() == Qt.LeftButton and self._drag_node_id is not None:
            self.graph.merge_close_nodes(threshold=0.25)
            self._drag_node_id = None
            self._drag_start_mouse = None
            self.wall_count_changed.emit(len(self.graph.segments))
            self.update_cursor()
            self.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        text = event.text()

        if key == Qt.Key_Escape:
            # 1. Se estiver calibrando ou movendo imagem de referência, volta para o modo linha
            if self.mode in ("calibrar_ref", "mover_ref"):
                self.mode = "linha"
                self._calib_points.clear()
                self.update_cursor()
                self.update()
                return

            # 2. Se estiver traçando parede (_start_pt ativo), cancela apenas o traço atual
            if self._start_pt is not None:
                self._start_pt = None
                self._type_buffer = ""
                self.update()
                return

            # 3. Se houver elemento selecionado ou buffer de digitação, limpa a seleção
            if self._selected_seg_id is not None or self._selected_node_id is not None or self._selected_dim_id is not None or self._type_buffer:
                self._selected_node_id = None
                self._selected_seg_id = None
                self._selected_dim_id = None
                self._drag_node_id = None
                self._type_buffer = ""
                self.update()
                return

            # 4. Se não havia nenhuma operação ativa no canvas, passa o evento para o diálogo (que tratará com confirmação)
            super().keyPressEvent(event)
            return
        elif key in (Qt.Key_Delete, Qt.Key_Backspace) and self._selected_dim_id is not None:
            # Exclui cota personalizada selecionada
            self._save_history()
            self.graph.remove_dimension(self._selected_dim_id)
            self._selected_dim_id = None
            self.update()
            return
        elif key in (Qt.Key_Delete, Qt.Key_Backspace) and self._selected_seg_id is not None:
            # Exclui segmento selecionado e limpa nós órfãos
            self._save_history()
            self.graph.remove_segment(self._selected_seg_id)
            self._selected_seg_id = None
            self.wall_count_changed.emit(len(self.graph.segments))
            self.update()
            return
        elif key in (Qt.Key_Delete, Qt.Key_Backspace) and self._selected_node_id is not None:
            mergeable = self.graph.mergeable_segments_at(self._selected_node_id)
            if mergeable is not None:
                # Nó interno colinear: remover o ponto une os dois trechos em uma parede única.
                self._save_history()
                merged_id = self.graph.merge_node(self._selected_node_id)
                self._selected_node_id = None
                self._selected_seg_id = merged_id
                self.wall_count_changed.emit(len(self.graph.segments))
                self.point_edit_hint.emit(
                    "🔗 Ponto removido: os dois trechos agora formam uma parede única."
                )
                self.update()
                return
            # Demais nós mantêm o comportamento de excluir as paredes que convergem nele.
            self._save_history()
            self.graph.remove_node(self._selected_node_id)
            self._selected_node_id = None
            self.wall_count_changed.emit(len(self.graph.segments))
            self.update()
            return
        elif key in (Qt.Key_Insert, Qt.Key_P) and self._selected_seg_id is not None:
            # Atalho: adiciona um ponto no meio da parede selecionada, dividindo-a.
            seg = self.graph.segments.get(self._selected_seg_id)
            if seg is not None:
                self._save_history()
                n_before = len(self.graph.segments)
                new_node_id = self.graph.split_segment(self._selected_seg_id, 0.5)
                if new_node_id is not None and len(self.graph.segments) > n_before:
                    self._selected_node_id = new_node_id
                    self._selected_seg_id = None
                    self.wall_count_changed.emit(len(self.graph.segments))
                    self.point_edit_hint.emit(
                        "➕ Ponto adicionado no meio da parede: agora há dois trechos."
                    )
                self.update()
                return
        elif key == Qt.Key_Z and event.modifiers() & Qt.ControlModifier:
            self.undo()
            return

        # Digitação direta de medidas numéricas
        # Se estiver desenhando (iniciou parede com _start_pt) ou tiver uma parede selecionada:
        if (self._start_pt is not None or self._selected_seg_id is not None or self._t_ref_info is not None):
            if text and text in "0123456789.,":
                # Converte vírgula para ponto se necessário
                char = "." if text == "," else text
                if char == "." and "." in self._type_buffer:
                    return
                self._type_buffer += char
                try:
                    val_doc = float(self._type_buffer)
                    scale = bare_number_scale()
                    val_m = val_doc * scale
                    self.current_length_changed.emit(val_m)
                except ValueError:
                    pass
                self.update()
                return
            elif key == Qt.Key_Backspace:
                if self._type_buffer:
                    self._type_buffer = self._type_buffer[:-1]
                    try:
                        val_doc = float(self._type_buffer) if self._type_buffer else 0.0
                        scale = bare_number_scale()
                        self.current_length_changed.emit(val_doc * scale)
                    except ValueError:
                        pass
                    self.update()
                    return
            elif key in (Qt.Key_Return, Qt.Key_Enter):
                if self._type_buffer:
                    try:
                        val_doc = float(self._type_buffer)
                        scale = bare_number_scale()
                        val_m = val_doc * scale
                        self._apply_typed_length(val_m)
                    except ValueError:
                        pass
                    self._type_buffer = ""
                    self.update()
                    return

        super().keyPressEvent(event)

    def _ortho_align(self, p0: Tuple[float, float], p1: Tuple[float, float], force_ortho: bool = False) -> Tuple[float, float]:
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        dist = math.hypot(dx, dy)
        if dist < 0.05:
            return p1

        angle = math.degrees(math.atan2(dy, dx))
        tol = 12.0
        if force_ortho or abs(angle) <= tol or abs(abs(angle) - 180.0) <= tol:
            return (p1[0], p0[1])
        elif force_ortho or abs(abs(angle) - 90.0) <= tol:
            return (p0[0], p1[1])
        return p1

    def clear_selection(self) -> None:
        """Limpa as seleções ativas de parede, nó e cota."""
        self._selected_seg_id = None
        self._selected_node_id = None
        self._selected_dim_id = None
        self._drag_node_id = None
        self._drag_dim_id = None
        self._drag_mid_seg_id = None
        self.update()

