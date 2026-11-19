# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Diálogo 2D de Planta Baixa para desenho de paredes e geração 3D automática."""
from __future__ import annotations

import math
from typing import Dict, Optional, List, Tuple

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



class DrawingMixin:
    """Renderizacao grafica do canvas de planta baixa (grid, paredes, cotas e badges)."""

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Fundo escuro estilo CAD / TrazoMob
        painter.fillRect(self.rect(), QColor(24, 28, 36))

        # 0. Imagem de Referência / Decalque de Fundo
        self._draw_reference_image(painter)

        # 1. Desenha Grid Métrico
        self._draw_grid(painter)

        # 1.5. Desenha Underlay (projeção das paredes do pavimento inferior)
        self._draw_underlay(painter)

        # 2. Desenha Paredes Existentes
        self._draw_walls(painter)

        # 3. Desenha Prévia do que está sendo desenhado (Borracha elástica / Rubberband)
        self._draw_rubberband(painter)

        # 4. Linhas de alinhamento inteligente com outros pontos (traço laranja/ouro)
        self._draw_alignment_guides(painter)

        # 5. Indicador de Snap
        self._draw_snap_marker(painter)
        self._draw_t_junction_tracking(painter)

    def _draw_reference_image(self, painter: QPainter) -> None:
        """Renderiza a imagem de referência de fundo com opacidade ajustável e escala correta."""
        if self._ref_pixmap is None or not self._ref_visible:
            return

        rx, ry = self._ref_pos_world
        rw = self._ref_width_m
        rh = rw * (self._ref_pixmap.height() / max(1, self._ref_pixmap.width()))

        p_top_left = self.world_to_screen(rx, ry + rh)
        p_bottom_right = self.world_to_screen(rx + rw, ry)
        target_rect = QRectF(p_top_left, p_bottom_right)

        painter.save()
        painter.setOpacity(self._ref_opacity)
        painter.drawPixmap(target_rect.toRect(), self._ref_pixmap)

        # Se estiver no modo de mover imagem, desenha borda azul indicativa
        if self.mode == "mover_ref":
            painter.setOpacity(1.0)
            painter.setPen(QPen(QColor(0, 176, 255, 200), 2.0, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(target_rect)
        painter.restore()

        # Se estiver no modo calibrar e tiver pontos marcados:
        if self.mode == "calibrar_ref" and self._calib_points:
            painter.save()
            p1_scr = self.world_to_screen(self._calib_points[0][0], self._calib_points[0][1])
            p_cur_scr = self.world_to_screen(self._current_mouse_world[0], self._current_mouse_world[1])

            painter.setPen(QPen(QColor(255, 214, 0), 2.0, Qt.DashLine))
            painter.drawLine(p1_scr, p_cur_scr)

            painter.setPen(QPen(QColor(255, 255, 255), 1.5))
            painter.setBrush(QBrush(QColor(255, 214, 0)))
            painter.drawEllipse(p1_scr, 5.0, 5.0)
            painter.drawEllipse(p_cur_scr, 4.0, 4.0)

            # Cota em tempo real da calibração
            dist_val = dist_2d(self._calib_points[0], self._current_mouse_world)
            lbl_txt = f"Calibrar: {format_length(dist_val)}"
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.setPen(QColor(255, 214, 0))
            mid_p = (p1_scr + p_cur_scr) / 2.0
            painter.drawText(QPointF(mid_p.x() + 10, mid_p.y() - 10), lbl_txt)
            painter.restore()

    def _draw_alignment_guides(self, painter: QPainter) -> None:
        """Desenha linhas tracejadas infinitas/guias indicando alinhamento X ou Y com nós existentes."""
        if not self._align_guides:
            return

        pen_align = QPen(QColor(255, 140, 0, 200), 1.2, Qt.DashLine)
        painter.setPen(pen_align)

        w = self.width()
        h = self.height()

        for p_from, p_to in self._align_guides:
            # Se alinhado verticalmente (mesmo X no screen)
            if abs(p_from.x() - p_to.x()) < 1.0:
                painter.drawLine(QPointF(p_to.x(), 0), QPointF(p_to.x(), h))
            # Se alinhado horizontalmente (mesmo Y no screen)
            elif abs(p_from.y() - p_to.y()) < 1.0:
                painter.drawLine(QPointF(0, p_to.y()), QPointF(w, p_to.y()))
            else:
                painter.drawLine(p_from, p_to)

            # Marcador em cruz no ponto de referência com o qual está alinhando
            painter.drawLine(QPointF(p_from.x() - 4, p_from.y()), QPointF(p_from.x() + 4, p_from.y()))
            painter.drawLine(QPointF(p_from.x(), p_from.y() - 4), QPointF(p_from.x(), p_from.y() + 4))

    def _draw_grid(self, painter: QPainter) -> None:
        w = self.width()
        h = self.height()

        grid_spacing_m = 1.0 if self._zoom < 60.0 else 0.5
        spacing_px = grid_spacing_m * self._zoom

        x_start = self._offset_x % spacing_px
        y_start = self._offset_y % spacing_px

        pen_grid = QPen(QColor(42, 48, 60), 0.8)
        painter.setPen(pen_grid)

        x = x_start
        while x < w:
            painter.drawLine(QPointF(x, 0), QPointF(x, h))
            x += spacing_px

        y = y_start
        while y < h:
            painter.drawLine(QPointF(0, y), QPointF(w, y))
            y += spacing_px

        # Eixos principais (Origem 0,0)
        orig = self.world_to_screen(0.0, 0.0)
        painter.setPen(QPen(QColor(230, 80, 80, 140), 1.2))
        painter.drawLine(QPointF(0, orig.y()), QPointF(w, orig.y()))  # Eixo X
        painter.setPen(QPen(QColor(80, 200, 120, 140), 1.2))
        painter.drawLine(QPointF(orig.x(), 0), QPointF(orig.x(), h))  # Eixo Y

    def set_underlay_lines(self, lines: List[Tuple[Tuple[float, float], Tuple[float, float]]]) -> None:
        """Define linhas de projeção do pavimento inferior (underlay)."""
        self._underlay_lines = list(lines) if lines else []
        self.update()

    def _draw_underlay(self, painter: QPainter) -> None:
        """Desenha a projeção do pavimento inferior com traço cinza suave para servir de guia."""
        if not self._underlay_lines:
            return
        pen_underlay = QPen(QColor(130, 145, 170, 120), 1.5, Qt.DashLine)
        pen_underlay.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_underlay)
        for (x1, y1), (x2, y2) in self._underlay_lines:
            p1 = self.world_to_screen(x1, y1)
            p2 = self.world_to_screen(x2, y2)
            painter.drawLine(p1, p2)

    def _draw_walls(self, painter: QPainter) -> None:
        polys = self.graph.compute_wall_polygons()
        self._dimension_badges.clear()

        # Mapeia quais nós têm 2 paredes formando canto
        node_segments: Dict[int, List[int]] = {nid: [] for nid in self.graph.nodes}
        for seg_id, seg in self.graph.segments.items():
            node_segments[seg.node_a_id].append(seg_id)
            node_segments[seg.node_b_id].append(seg_id)

        # 1. As linhas de borda de cada parede com cantos chanfrados / miter a 45°
        pen_border = QPen(QColor(230, 235, 245), 1.6, Qt.SolidLine)
        pen_border.setCapStyle(Qt.RoundCap)
        pen_border.setJoinStyle(Qt.MiterJoin)

        pen_selected = QPen(QColor(255, 214, 0), 2.2, Qt.SolidLine)
        pen_selected.setCapStyle(Qt.RoundCap)
        pen_selected.setJoinStyle(Qt.MiterJoin)

        for seg_id, quad in polys.items():
            # Se selecionado, destaca em amarelo dourado
            painter.setPen(pen_selected if seg_id == self._selected_seg_id else pen_border)

            # quad = (c0, c1, c2, c3) em coordenadas de mundo
            s0 = self.world_to_screen(quad[0][0], quad[0][1])
            s1 = self.world_to_screen(quad[1][0], quad[1][1])
            s2 = self.world_to_screen(quad[2][0], quad[2][1])
            s3 = self.world_to_screen(quad[3][0], quad[3][1])

            # Linha lateral esquerda (c0 -> c1)
            painter.drawLine(s0, s1)
            # Linha lateral direita (c2 -> c3)
            painter.drawLine(s2, s3)

            # Se a extremidade A for livre (1 único segmento no nó), fecha a ponta
            seg = self.graph.segments[seg_id]
            if len(node_segments.get(seg.node_a_id, [])) == 1:
                painter.drawLine(s3, s0)
            # Se a extremidade B for livre, fecha a ponta
            if len(node_segments.get(seg.node_b_id, [])) == 1:
                painter.drawLine(s1, s2)

        # 2. Fecha os cantos em 45 graus (Linha de junta / miter do canto da parede)
        pen_miter = QPen(QColor(230, 235, 245, 200), 1.4, Qt.SolidLine)
        painter.setPen(pen_miter)

        for nid, seg_ids in node_segments.items():
            if len(seg_ids) == 2:
                # Canto L com 2 paredes: une o ponto interno ao externo na linha de 45°
                s_a = seg_ids[0]
                q_a = polys.get(s_a)
                if not q_a:
                    continue
                seg_a_obj = self.graph.segments[s_a]
                if seg_a_obj.node_a_id == nid:
                    # No nó nid, os cantos correspondentes deste segmento são q_a[0] e q_a[3]
                    p_miter1 = self.world_to_screen(q_a[0][0], q_a[0][1])
                    p_miter2 = self.world_to_screen(q_a[3][0], q_a[3][1])
                else:
                    # No nó nid, os cantos correspondentes deste segmento são q_a[1] e q_a[2]
                    p_miter1 = self.world_to_screen(q_a[1][0], q_a[1][1])
                    p_miter2 = self.world_to_screen(q_a[2][0], q_a[2][1])
                painter.drawLine(p_miter1, p_miter2)

        # 3. Coluna separando paredes em junções em T (ou X)
        columns = self.graph.compute_columns()
        pen_column = QPen(QColor(245, 180, 70), 1.6, Qt.SolidLine)
        brush_column = QBrush(QColor(40, 32, 20, 180))
        pen_hatch = QPen(QColor(245, 180, 70, 160), 1.0, Qt.SolidLine)

        for nid, col_quad in columns.items():
            s0 = self.world_to_screen(col_quad[0][0], col_quad[0][1])
            s1 = self.world_to_screen(col_quad[1][0], col_quad[1][1])
            s2 = self.world_to_screen(col_quad[2][0], col_quad[2][1])
            s3 = self.world_to_screen(col_quad[3][0], col_quad[3][1])

            # Desenha o contorno preenchido da coluna
            from PySide6.QtGui import QPolygonF
            poly = QPolygonF([s0, s1, s2, s3])
            painter.setPen(pen_column)
            painter.setBrush(brush_column)
            painter.drawPolygon(poly)

            # Hachura em 'X' padrão arquitetural para pilar / coluna estrutural
            painter.setPen(pen_hatch)
            painter.drawLine(s0, s2)
            painter.drawLine(s1, s3)

            # Fecha a extremidade de cada parede que chega a esta coluna (tampa de encosto)
            pen_cap = QPen(QColor(230, 235, 245), 1.4, Qt.SolidLine)
            painter.setPen(pen_cap)
            for sid in node_segments.get(nid, []):
                q = polys.get(sid)
                if not q:
                    continue
                s_obj = self.graph.segments[sid]
                if s_obj.node_a_id == nid:
                    # Extremidade A encostando na coluna: liga c3 e c0
                    pa = self.world_to_screen(q[3][0], q[3][1])
                    pb = self.world_to_screen(q[0][0], q[0][1])
                else:
                    # Extremidade B encostando na coluna: liga c1 e c2
                    pa = self.world_to_screen(q[1][0], q[1][1])
                    pb = self.world_to_screen(q[2][0], q[2][1])
                painter.drawLine(pa, pb)

        # 4. Linhas de eixo central das paredes
        for sid, seg in self.graph.segments.items():
            na = self.graph.nodes[seg.node_a_id]
            nb = self.graph.nodes[seg.node_b_id]
            p0 = self.world_to_screen(na.x, na.y)
            p1 = self.world_to_screen(nb.x, nb.y)

            pen_measure = QPen(QColor(70, 140, 245, 120), 1.0, Qt.DashLine)
            painter.setPen(pen_measure)
            painter.drawLine(p0, p1)

        # 4.4 Selos de Ambiente e Área dos Cômodos Fechados
        self._draw_room_labels(painter)

        # 4.5 Desenha Cotas Personalizadas adicionadas pelo usuário (entre quaisquer dois pontos)
        self._draw_custom_dimensions(painter)

        # 5. Indicação de Ângulos entre Paredes nos nós conectados
        self._draw_corner_angles(painter, node_segments)

        # 6. Desenha os nós (pontos de união) com destaque para nó selecionado/arrastado
        # 5.5 Desenha o grip de arraste paralelo no ponto m?dio da parede selecionada
        if self._selected_seg_id is not None and self._selected_seg_id in self.graph.segments:
            seg_sel = self.graph.segments[self._selected_seg_id]
            na_sel = self.graph.nodes.get(seg_sel.node_a_id)
            nb_sel = self.graph.nodes.get(seg_sel.node_b_id)
            if na_sel and nb_sel:
                mid_wx = (na_sel.x + nb_sel.x) / 2.0
                mid_wy = (na_sel.y + nb_sel.y) / 2.0
                sp_mid = self.world_to_screen(mid_wx, mid_wy)
                painter.setPen(QPen(QColor(255, 255, 255), 1.5))
                painter.setBrush(QBrush(QColor(0, 176, 255, 240) if self._drag_mid_seg_id is None else QColor(255, 214, 0, 240)))
                sz_g = 7.0
                painter.drawRect(QRectF(sp_mid.x() - sz_g / 2.0, sp_mid.y() - sz_g / 2.0, sz_g, sz_g))

        for node in self.graph.nodes.values():
            sp = self.world_to_screen(node.x, node.y)
            is_sel = (node.id == self._selected_node_id or node.id == self._drag_node_id)
            if is_sel:
                painter.setPen(QPen(QColor(255, 214, 0), 2.0))
                painter.setBrush(QBrush(QColor(255, 214, 0, 160)))
                painter.drawEllipse(sp, 6.0, 6.0)
            else:
                painter.setPen(QPen(QColor(0, 230, 118), 1.2))
                painter.setBrush(QBrush(QColor(15, 23, 42)))
                painter.drawEllipse(sp, 3.5, 3.5)

    def _draw_room_labels(self, painter: QPainter) -> None:
        """Exibe selo com nome do ambiente e área calculada no centro geométrico de cada cômodo fechado."""
        self._room_badges.clear()
        cycles = self.graph.find_closed_cycles()
        if not cycles:
            return

        font_title = QFont("Segoe UI", 9, QFont.Bold)
        font_sub = QFont("Segoe UI", 8, QFont.Normal)

        # Se houver apenas 1 cômodo e nenhum nome customizado atribuído a ele, usa o texto digitado na lateral
        default_side_name = "Ambiente"
        label_title = getattr(self.window(), "txt_amb_name", None)
        if label_title and hasattr(label_title, "text") and label_title.text().strip():
            default_side_name = label_title.text().strip()

        for idx, cycle_pts in enumerate(cycles):
            if len(cycle_pts) < 3:
                continue

            # Calcula centróide e área via fórmula do polígono (Shoelace)
            area = 0.0
            cx_sum = 0.0
            cy_sum = 0.0
            n = len(cycle_pts)
            for i in range(n):
                x0, y0 = cycle_pts[i]
                x1, y1 = cycle_pts[(i + 1) % n]
                cross = (x0 * y1 - x1 * y0)
                area += cross
                cx_sum += (x0 + x1) * cross
                cy_sum += (y0 + y1) * cross

            signed_area = area * 0.5
            abs_area = abs(signed_area)
            if abs_area < 0.2:
                continue

            if abs(area) > 1e-6:
                cx = cx_sum / (3.0 * area)
                cy = cy_sum / (3.0 * area)
            else:
                cx = sum(p[0] for p in cycle_pts) / n
                cy = sum(p[1] for p in cycle_pts) / n

            sp = self.world_to_screen(cx, cy)

            # Nome específico do cômodo gravado no grafo ou default
            fallback_name = default_side_name if len(cycles) == 1 else f"Cômodo {idx + 1}"
            nome_comodo = self.graph.get_room_name(cycle_pts, default=fallback_name)
            text_area = f"{abs_area:.2f} m²"

            painter.save()
            # Ajusta largura do selo dinamicamente de acordo com o tamanho do nome
            fm = painter.fontMetrics()
            name_w = fm.horizontalAdvance(nome_comodo)
            badge_w = max(96.0, float(name_w + 20.0))
            badge_h = 36.0
            rect = QRectF(sp.x() - badge_w / 2.0, sp.y() - badge_h / 2.0, badge_w, badge_h)

            self._room_badges.append({
                "rect": rect,
                "cycle_pts": cycle_pts,
                "name": nome_comodo,
                "area_m2": abs_area,
            })

            painter.setPen(QPen(QColor(0, 230, 118, 220), 1.2))
            painter.setBrush(QBrush(QColor(15, 23, 42, 225)))
            painter.drawRoundedRect(rect, 5.0, 5.0)

            # Texto do Cômodo
            painter.setFont(font_title)
            painter.setPen(QColor(241, 245, 249))
            painter.drawText(QRectF(rect.x(), rect.y() + 3, badge_w, 15), Qt.AlignCenter, nome_comodo)

            # Texto da Área
            painter.setFont(font_sub)
            painter.setPen(QColor(0, 230, 118))
            painter.drawText(QRectF(rect.x(), rect.y() + 18, badge_w, 15), Qt.AlignCenter, text_area)

            painter.restore()

    def _draw_custom_dimensions(self, painter: QPainter) -> None:
        """Desenha todas as cotas personalizadas inseridas pelo usuário na planta."""
        for did, dim in self.graph.dimensions.items():
            p1_scr = self.world_to_screen(dim.p1[0], dim.p1[1])
            p2_scr = self.world_to_screen(dim.p2[0], dim.p2[1])

            dx = p2_scr.x() - p1_scr.x()
            dy = p2_scr.y() - p1_scr.y()
            L_px = math.hypot(dx, dy)
            if L_px < 1.0:
                continue

            # Vetor normal para afastar a linha de cota dos pontos
            nx = -dy / L_px
            ny = dx / L_px
            off_px = dim.offset * self._zoom

            # Pontos deslocados da linha de cota
            c1 = QPointF(p1_scr.x() + nx * off_px, p1_scr.y() + ny * off_px)
            c2 = QPointF(p2_scr.x() + nx * off_px, p2_scr.y() + ny * off_px)

            # Linhas de extensão / testemunha (dos pontos até a linha de cota)
            is_dim_sel = (did == self._selected_dim_id)
            pen_witness = QPen(QColor(255, 214, 0, 180) if is_dim_sel else QColor(0, 230, 118, 140), 1.0, Qt.DotLine)
            painter.setPen(pen_witness)
            painter.drawLine(p1_scr, c1)
            painter.drawLine(p2_scr, c2)

            # Linha principal da cota
            pen_dim_line = QPen(QColor(255, 214, 0, 255) if is_dim_sel else QColor(0, 230, 118, 220), 1.8 if is_dim_sel else 1.4, Qt.SolidLine)
            painter.setPen(pen_dim_line)
            painter.drawLine(c1, c2)

            # Tiques/barras inclinadas a 45 graus nas extremidades da cota (padrão arquitetônico)
            tick_sz = 5.0
            painter.drawLine(QPointF(c1.x() - tick_sz, c1.y() + tick_sz), QPointF(c1.x() + tick_sz, c1.y() - tick_sz))
            painter.drawLine(QPointF(c2.x() - tick_sz, c2.y() + tick_sz), QPointF(c2.x() + tick_sz, c2.y() - tick_sz))

            # Badge interativo com o valor da cota
            dist_m = dist_2d(dim.p1, dim.p2)
            self._draw_dimension(painter, c1, c2, dist_m, dim_id=did)

    def _draw_rubberband(self, painter: QPainter) -> None:
        if self._start_pt is None:
            return

        p0_w = self._start_pt
        p1_w = self._current_mouse_world
        p0 = self.world_to_screen(p0_w[0], p0_w[1])
        p1 = self.world_to_screen(p1_w[0], p1_w[1])

        dx = p1.x() - p0.x()
        dy = p1.y() - p0.y()
        length_px = math.hypot(dx, dy)
        th_px = self.graph.default_thickness * self._zoom

        off_l_px = th_px / 2.0
        off_r_px = th_px / 2.0

        if self.mode == "linha":
            if length_px > 1.0:
                # No screen do Qt, Y cresce para baixo enquanto no mundo Y cresce para cima.
                # Vetor u_screen = (dx/length, dy/length).
                # Normal à esquerda no screen que corresponde à normal à esquerda no mundo:
                # No mundo: u = (wdx, wdy), n = (-wdy, wdx).
                # Como sy = offset_y - wy*zoom, dy_screen = -dwy * zoom.
                # Portanto, nx_screen = dy_screen / length_px, ny_screen = -dx_screen / length_px.
                wdx = p1_w[0] - p0_w[0]
                wdy = p1_w[1] - p0_w[1]
                wlen = math.hypot(wdx, wdy)
                if wlen > 1e-6:
                    wnx = -wdy / wlen
                    wny = wdx / wlen
                    # Converte vetor normal do mundo para pixels de tela
                    nx_px = wnx * self._zoom
                    ny_px = -wny * self._zoom

                    # Duas linhas paralelas de borda em ciano/azul
                    pen_guide_border = QPen(QColor(0, 176, 255, 220), 1.4, Qt.SolidLine)
                    painter.setPen(pen_guide_border)

                    factor_l = off_l_px / max(1e-6, th_px)
                    factor_r = off_r_px / max(1e-6, th_px)

                    # Borda esquerda: ponto + n * off_l
                    b0_a = QPointF(p0.x() + nx_px * (self.graph.default_thickness * factor_l),
                                   p0.y() + ny_px * (self.graph.default_thickness * factor_l))
                    b1_a = QPointF(p1.x() + nx_px * (self.graph.default_thickness * factor_l),
                                   p1.y() + ny_px * (self.graph.default_thickness * factor_l))
                    painter.drawLine(b0_a, b1_a)

                    # Borda direita: ponto - n * off_r
                    b0_b = QPointF(p0.x() - nx_px * (self.graph.default_thickness * factor_r),
                                   p0.y() - ny_px * (self.graph.default_thickness * factor_r))
                    b1_b = QPointF(p1.x() - nx_px * (self.graph.default_thickness * factor_r),
                                   p1.y() - ny_px * (self.graph.default_thickness * factor_r))
                    painter.drawLine(b0_b, b1_b)

                    # Tampa final temporária
                    painter.drawLine(b1_a, b1_b)

            # Linha guia de traço / cota
            painter.setPen(QPen(QColor(0, 176, 255, 180), 1.0, Qt.DashLine))
            painter.drawLine(p0, p1)

            total_len_m = dist_2d(p0_w, p1_w)
            if total_len_m > 1e-4:
                dir_u = ((p1_w[0] - p0_w[0]) / total_len_m, (p1_w[1] - p0_w[1]) / total_len_m)
                ext = self.graph.get_start_extension(p0_w, dir_u)
                display_len = max(0.01, total_len_m - ext)
            else:
                display_len = total_len_m
            self._draw_dimension(painter, p0, p1, display_len, is_preview=True)

        elif self.mode == "cota" and self._cota_points:
            p1_scr = self.world_to_screen(self._cota_points[0][0], self._cota_points[0][1])
            p_cur_scr = self.world_to_screen(p1_w[0], p1_w[1])
            pen_cota_prev = QPen(QColor(0, 230, 118, 200), 1.4, Qt.DashLine)
            painter.setPen(pen_cota_prev)
            painter.drawLine(p1_scr, p_cur_scr)
            dist_cota_m = dist_2d(self._cota_points[0], p1_w)
            self._draw_dimension(painter, p1_scr, p_cur_scr, dist_cota_m, is_preview=True)

        elif self.mode == "retangulo":
            x0, y0 = self.world_to_screen(p0_w[0], p0_w[1]).toTuple()
            x1, y1 = self.world_to_screen(p1_w[0], p1_w[1]).toTuple()
            rect = QRectF(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))

            pen_rect = QPen(QColor(0, 176, 255, 200), 1.4, Qt.DashLine)
            painter.setPen(pen_rect)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)

            w_m = abs(p1_w[0] - p0_w[0])
            mid_top_a = QPointF(min(x0, x1), min(y0, y1))
            mid_top_b = QPointF(max(x0, x1), min(y0, y1))
            self._draw_dimension(painter, mid_top_a, mid_top_b, w_m, is_preview=True)

    def _draw_corner_angles(self, painter: QPainter, node_segments: Dict[int, List[int]]) -> None:
        """Desenha arco e texto com o ângulo entre paredes nos cantos (ex: 90.0°)."""
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)

        for nid, seg_ids in node_segments.items():
            if len(seg_ids) == 2:
                node = self.nodes_or_graph_get_node(nid)
                if not node:
                    continue

                s1 = self.graph.segments[seg_ids[0]]
                s2 = self.graph.segments[seg_ids[1]]

                other1 = self.graph.nodes[s1.node_b_id if s1.node_a_id == nid else s1.node_a_id]
                other2 = self.graph.nodes[s2.node_b_id if s2.node_a_id == nid else s2.node_a_id]

                # Ângulos em graus das duas paredes saindo do nó (em coordenadas de mundo: +y para cima)
                ang1 = math.degrees(math.atan2(other1.y - node.y, other1.x - node.x))
                ang2 = math.degrees(math.atan2(other2.y - node.y, other2.x - node.x))

                diff = abs(ang1 - ang2) % 360.0
                if diff > 180.0:
                    diff = 360.0 - diff

                # Não desenha se forem paredes retas colineares (180°)
                if 1.0 < diff < 179.0:
                    sp = self.world_to_screen(node.x, node.y)
                    # Vetor médio bissetriz para posicionar o badge do ângulo
                    rad1 = math.radians(ang1)
                    rad2 = math.radians(ang2)
                    v1 = (math.cos(rad1), math.sin(rad1))
                    v2 = (math.cos(rad2), math.sin(rad2))
                    bis_x = v1[0] + v2[0]
                    bis_y = v1[1] + v2[1]
                    blen = math.hypot(bis_x, bis_y)
                    if blen > 1e-4:
                        bis_x /= blen
                        bis_y /= blen
                    else:
                        bis_x, bis_y = -v1[1], v1[0]

                    # Offset em pixels para a cota de ângulo
                    offset_px = 24.0
                    ang_pt = QPointF(sp.x() + bis_x * offset_px, sp.y() - bis_y * offset_px)

                    ang_text = f"{diff:.0f}°" if abs(diff - round(diff)) < 0.1 else f"{diff:.1f}°"
                    fm = painter.fontMetrics()
                    tw = fm.horizontalAdvance(ang_text)
                    th = fm.height()
                    rect_ang = QRectF(ang_pt.x() - tw / 2.0 - 3, ang_pt.y() - th / 2.0 - 2, tw + 6, th + 4)

                    # Desenha arco indicador
                    arc_r = 16.0
                    arc_rect = QRectF(sp.x() - arc_r, sp.y() - arc_r, arc_r * 2, arc_r * 2)
                    painter.setPen(QPen(QColor(0, 230, 118, 160), 1.2, Qt.DotLine))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawArc(arc_rect, int(min(ang1, ang2) * 16), int(diff * 16))

                    # Badge de texto do ângulo
                    painter.setPen(QPen(QColor(0, 230, 118, 180), 1.0))
                    painter.setBrush(QBrush(QColor(18, 24, 32, 220)))
                    painter.drawRoundedRect(rect_ang, 3.0, 3.0)
                    painter.setPen(QColor(0, 230, 118))
                    painter.drawText(rect_ang, Qt.AlignCenter, ang_text)

    def nodes_or_graph_get_node(self, nid: int):
        return self.graph.nodes.get(nid)

    def _draw_dimension(self, painter: QPainter, p0: QPointF, p1: QPointF, length_m: float, is_preview: bool = False, seg_id: Optional[int] = None, dim_id: Optional[int] = None, face_type: str = "centro") -> None:
        if length_m < 0.001:
            return

        mid = (p0 + p1) / 2.0
        # Se houver digitação direta em andamento, exibe o que está sendo digitado com a unidade
        doc_u = model_unit()
        doc_p = model_precision()
        if is_preview and self._type_buffer:
            text = f"⌨️ {self._type_buffer} {doc_u} (Enter ↵)"
        else:
            text = format_length(length_m, doc_u, doc_p)

        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(text)
        th = fm.height()

        badge_rect = QRectF(mid.x() - tw / 2.0 - 5, mid.y() - th / 2.0 - 3, tw + 10, th + 6)
        if seg_id is not None or dim_id is not None:
            # Use dim_id (persistent dimension ID) as the badge key
            # instead of _next_badge_id (transient, resets on session reload)
            # This ensures badges persist correctly across session reloads
            badge_key = f"dim_{dim_id}" if dim_id is not None else f"seg_{seg_id}"
            self._dimension_badges[badge_key] = {
                "rect": badge_rect,
                "seg_id": seg_id,
                "dim_id": dim_id,
                "face_type": face_type,
                "length_m": length_m,
            }

        is_sel = (seg_id is not None and seg_id == self._selected_seg_id) or (dim_id is not None and dim_id == self._selected_dim_id)
        if is_sel:
            bg_col = QColor(255, 180, 0, 240)
            text_col = QColor(0, 0, 0)
            pen_border = QPen(QColor(255, 255, 255), 1.2)
        elif is_preview:
            bg_col = QColor(0, 120, 215, 230)
            text_col = QColor(255, 255, 255)
            pen_border = QPen(QColor(255, 255, 255, 120), 1.0)
        else:
            bg_col = QColor(20, 24, 30, 220)
            text_col = QColor(255, 255, 255)
            pen_border = QPen(QColor(255, 255, 255, 120), 1.0)

        painter.setPen(pen_border)
        painter.setBrush(QBrush(bg_col))
        painter.drawRoundedRect(badge_rect, 4.0, 4.0)

        painter.setPen(text_col)
        painter.drawText(badge_rect, Qt.AlignCenter, text)

    def _draw_snap_marker(self, painter: QPainter) -> None:
        if self._snap_info is None:
            return

        pos = self.world_to_screen(self._current_mouse_world[0], self._current_mouse_world[1])
        col = QColor(0, 230, 118) if self._snap_info == "canto" else QColor(255, 214, 0)

        painter.setPen(QPen(col, 2.0))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(pos, 8.0, 8.0)
        painter.drawEllipse(pos, 3.0, 3.0)

    def _draw_t_junction_tracking(self, painter: QPainter) -> None:
        """Desenha a linha de cota din?mica e ?ncora visual ao rastrear dist?ncia para parede em T."""
        if self._t_ref_info is None or self._start_pt is not None:
            return

        ref_pt = self._t_ref_info["ref_pt"]
        proj_pt = self._t_ref_info["proj_pt"]
        dist_m = self._t_ref_info["distance_m"]

        p_ref = self.world_to_screen(ref_pt[0], ref_pt[1])
        p_proj = self.world_to_screen(proj_pt[0], proj_pt[1])

        # Linha guia de medi??o em ciano brilhante sobre a parede existente
        pen_track = QPen(QColor(0, 230, 255, 230), 2.0, Qt.SolidLine)
        painter.setPen(pen_track)
        painter.drawLine(p_ref, p_proj)

        # Marcador de ?ncora (diamante / rombo) no canto de refer?ncia
        r_sz = 6.0
        poly_anchor = QPolygonF([
            QPointF(p_ref.x(), p_ref.y() - r_sz),
            QPointF(p_ref.x() + r_sz, p_ref.y()),
            QPointF(p_ref.x(), p_ref.y() + r_sz),
            QPointF(p_ref.x() - r_sz, p_ref.y()),
        ])
        painter.setBrush(QBrush(QColor(0, 230, 255, 200)))
        painter.drawPolygon(poly_anchor)

        # Marcador circular no ponto projetado da parede
        painter.setBrush(QBrush(QColor(255, 214, 0, 220)))
        painter.setPen(QPen(QColor(255, 255, 255), 1.2))
        painter.drawEllipse(p_proj, 4.5, 4.5)

        # Cota din?mica com texto
        self._draw_dimension(painter, p_ref, p_proj, dist_m, is_preview=True)

