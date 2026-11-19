# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Módulo de Elevação Técnica 2D de Paredes com Cotas (Wall Elevation 2D).

Projeta a vista ortogonal frontal de uma parede selecionada exibindo:
1. Contorno milimétrico da alvenaria (largura x pé-direito);
2. Todos os móveis e bancadas instalados encostados nessa parede com suas frentes, puxadores e divisões;
3. Linhas e réguas paramétricas de alturas (níveis de rodapé, balcão, bancada, backsplash, aéreo);
4. Linhas de cotas arquitetônicas automáticas:
   - Cotas horizontais de largura de cada módulo e vão residual;
   - Cota horizontal total da parede;
   - Cotas verticais de cada faixa/nível de móvel (rodapé, corpo do balcão, vão livre, aéreo, fechamento superior);
   - Cota vertical total do pé-direito;
5. Ferramentas interativas de Zoom, Pan, Exportação para Imagem PNG de alta resolução e Impressão direta.
"""
from __future__ import annotations

import math
from typing import Optional, List, Dict, Tuple, Any

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPen,
    QBrush,
    QPixmap,
    QPainterPath,
    QVector3D,
)
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolBar,
    QFileDialog,
    QMessageBox,
    QFrame,
    QComboBox,
    QCheckBox,
)

from core.group import Group
from ..wall.selection import WallFaceInfo, WallSelectionManager
from ..interaction.magnetic_drag import get_module_bounds, get_bounds_min_projection
from ..domain.module_geometry import get_module_carcass_bounds


class WallElevationCanvas(QWidget):
    """Canvas 2D interativo com renderização ortogonal precisa da elevação da parede."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        # Dados da elevação
        self.wall_width_m: float = 3.00
        self.wall_height_m: float = 2.60
        self.wall_label: str = "Parede"
        self.modules_2d: List[Dict[str, Any]] = []
        self.guide_levels: List[Dict[str, Any]] = []

        # Navegação (Pan e Zoom estilo CAD)
        self._scale: float = 200.0  # pixels por metro
        self._offset_x: float = 120.0
        self._offset_y: float = 100.0
        self._is_panning: bool = False
        self._last_mouse_pos: Optional[QPointF] = None

        # Opções visuais
        self.show_cotas: bool = True
        self.show_guides: bool = True
        self.show_names: bool = True
        self.show_instalacoes: bool = True

    def set_data(
        self,
        wall_width_m: float,
        wall_height_m: float,
        wall_label: str,
        modules_2d: List[Dict[str, Any]],
        guide_levels: List[Dict[str, Any]],
    ) -> None:
        self.wall_width_m = max(0.10, wall_width_m)
        self.wall_height_m = max(0.10, wall_height_m)
        self.wall_label = wall_label
        self.modules_2d = modules_2d
        self.guide_levels = guide_levels
        self.fit_to_view()
        self.update()

    def fit_to_view(self) -> None:
        """Ajusta o zoom e a centralização para enquadrar a parede inteira com margem para cotas."""
        w_avail = self.width() if self.width() > 100 else 900
        h_avail = self.height() if self.height() > 100 else 600

        # Margens para cotas: 180px na esquerda/direita, 160px acima/abaixo
        margin_x = 220.0
        margin_y = 180.0

        scale_w = (w_avail - margin_x) / self.wall_width_m
        scale_h = (h_avail - margin_y) / self.wall_height_m
        self._scale = max(60.0, min(scale_w, scale_h))

        # Centraliza na janela
        wall_px_w = self.wall_width_m * self._scale
        wall_px_h = self.wall_height_m * self._scale

        self._offset_x = (w_avail - wall_px_w) * 0.5 + 40.0
        # Em CAD 2D de elevação, Z=0 (piso) fica embaixo
        self._offset_y = (h_avail + wall_px_h) * 0.5 - 20.0

    def world_to_screen(self, u_m: float, z_m: float) -> QPointF:
        """Converte coordenadas locais da parede (u em metros ao longo da base, z em metros de altura) para a tela."""
        sx = self._offset_x + u_m * self._scale
        sy = self._offset_y - z_m * self._scale
        return QPointF(sx, sy)

    # --- Eventos de Mouse (Zoom e Pan) ---

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 0.85
        old_scale = self._scale
        self._scale = max(30.0, min(1500.0, self._scale * factor))

        # Zoom centrado na posição do mouse
        mouse_pos = event.position()
        self._offset_x = mouse_pos.x() - (mouse_pos.x() - self._offset_x) * (self._scale / old_scale)
        self._offset_y = mouse_pos.y() - (mouse_pos.y() - self._offset_y) * (self._scale / old_scale)
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() in (Qt.MiddleButton, Qt.RightButton) or (event.button() == Qt.LeftButton and event.modifiers() & Qt.AltModifier):
            self._is_panning = True
            self._last_mouse_pos = event.position()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event) -> None:
        if self._is_panning and self._last_mouse_pos is not None:
            delta = event.position() - self._last_mouse_pos
            self._offset_x += delta.x()
            self._offset_y += delta.y()
            self._last_mouse_pos = event.position()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if self._is_panning:
            self._is_panning = False
            self._last_mouse_pos = None
            self.setCursor(Qt.ArrowCursor)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)

    # --- Renderização Visual ---

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        # Fundo estilo prancha técnica blueprint / CAD claro
        painter.fillRect(self.rect(), QColor("#F8FAFC"))

        # 1. Desenha a Alvenaria da Parede
        self._draw_wall_background(painter)

        # 2. Desenha Linhas-Guia Paramétricas
        if self.show_guides:
            self._draw_guide_lines(painter)

        # 3. Desenha Módulos, Bancadas e Portas
        self._draw_modules(painter)

        # 4. Desenha Pontos e Cotas de Instalação Técnica (Elétrica / Hidráulica)
        if self.show_instalacoes:
            self._draw_installation_points(painter)

        # 5. Desenha Cotas Técnicas (Horizontais e Verticais)
        if self.show_cotas:
            self._draw_dimensions(painter)

        # 6. Legenda e Título Técnico da Prancha
        self._draw_title_block(painter)

    def _draw_wall_background(self, painter: QPainter) -> None:
        p_bl = self.world_to_screen(0.0, 0.0)
        p_br = self.world_to_screen(self.wall_width_m, 0.0)
        p_tl = self.world_to_screen(0.0, self.wall_height_m)
        p_tr = self.world_to_screen(self.wall_width_m, self.wall_height_m)

        rect_wall = QRectF(p_tl, p_br)

        # Preenchimento de alvenaria suave
        painter.fillRect(rect_wall, QColor("#F1F5F9"))

        # Linha de piso / solo (linha dupla reforçada)
        pen_floor = QPen(QColor("#0F172A"), 3.0)
        painter.setPen(pen_floor)
        p_floor_l = self.world_to_screen(-0.30, 0.0)
        p_floor_r = self.world_to_screen(self.wall_width_m + 0.30, 0.0)
        painter.drawLine(p_floor_l, p_floor_r)

        # Linha de teto / laje
        pen_ceiling = QPen(QColor("#64748B"), 1.8, Qt.DashLine)
        painter.setPen(pen_ceiling)
        p_ceil_l = self.world_to_screen(-0.20, self.wall_height_m)
        p_ceil_r = self.world_to_screen(self.wall_width_m + 0.20, self.wall_height_m)
        painter.drawLine(p_ceil_l, p_ceil_r)

        # Contorno das laterais da parede
        pen_wall = QPen(QColor("#334155"), 2.0)
        painter.setPen(pen_wall)
        painter.drawRect(rect_wall)

        # Hachura de piso (terra / contrapiso)
        pen_hachura = QPen(QColor("#94A3B8"), 1.0)
        painter.setPen(pen_hachura)
        step_px = 14.0
        cur_x = p_floor_l.x()
        while cur_x < p_floor_r.x():
            painter.drawLine(QPointF(cur_x, p_bl.y()), QPointF(cur_x - 10, p_bl.y() + 10))
            cur_x += step_px

    def _draw_guide_lines(self, painter: QPainter) -> None:
        font_guide = QFont("Segoe UI", 8)
        painter.setFont(font_guide)

        for g in self.guide_levels:
            z_m = g.get("z", 0.0)
            if z_m <= 0.001 or z_m >= self.wall_height_m - 0.001:
                continue
            name = g.get("name", "")
            p_l = self.world_to_screen(-0.15, z_m)
            p_r = self.world_to_screen(self.wall_width_m + 0.15, z_m)

            pen_g = QPen(QColor(14, 165, 233, 160), 1.0, Qt.DashDotLine)
            painter.setPen(pen_g)
            painter.drawLine(p_l, p_r)

            # Rótulo de texto à direita da linha guia
            painter.setPen(QColor("#0284C7"))
            label_text = f"{name} ({int(round(z_m * 1000))}mm)"
            painter.drawText(QPointF(p_r.x() + 6, p_r.y() + 4), label_text)

    def _draw_modules(self, painter: QPainter) -> None:
        font_name = QFont("Segoe UI", 9, QFont.Bold)
        font_dim = QFont("Segoe UI", 8)

        for mod in self.modules_2d:
            u0 = mod["u_min"]
            u1 = mod["u_max"]
            z0 = mod["z_min"]
            z1 = mod["z_max"]
            tipo = mod.get("tipo", "modulo")
            nome = mod.get("nome", "Módulo")

            p_tl = self.world_to_screen(u0, z1)
            p_br = self.world_to_screen(u1, z0)
            rect_mod = QRectF(p_tl, p_br)

            # Estilização conforme categoria de móvel
            if tipo == "bancada":
                fill_color = QColor("#E2E8F0")
                border_color = QColor("#0284C7")
                pen = QPen(border_color, 2.0)
            elif "porta" in tipo:
                fill_color = QColor("#F8FAFC")
                border_color = QColor("#7C3AED")
                pen = QPen(border_color, 2.0)
            elif "janela" in tipo:
                fill_color = QColor(224, 242, 254, 180)  # Vidro azul transl?cido
                border_color = QColor("#0284C7")
                pen = QPen(border_color, 2.0)
            elif "aereo" in tipo or "alto" in tipo:
                fill_color = QColor("#FFFFFF")
                border_color = QColor("#1E293B")
                pen = QPen(border_color, 1.8)
            else:
                # Balcão / Torre
                fill_color = QColor("#FFFFFF")
                border_color = QColor("#0F172A")
                pen = QPen(border_color, 2.0)

            painter.setPen(pen)
            painter.setBrush(QBrush(fill_color))
            painter.drawRect(rect_mod)

            # Linha de rodapé do módulo se for balcão pousado no piso
            if z0 < 0.05 and z1 > 0.30:
                # Linha de rodapé a 100mm ou 150mm
                rodape_z = min(0.15, z1 * 0.2)
                p_r_tl = self.world_to_screen(u0, rodape_z)
                p_r_br = self.world_to_screen(u1, z0)
                rect_rodape = QRectF(p_r_tl, p_r_br)
                painter.fillRect(rect_rodape, QColor("#CBD5E1"))
                painter.setPen(QPen(QColor("#64748B"), 1.2))
                painter.drawLine(rect_rodape.topLeft(), rect_rodape.topRight())

            # Desenho simbólico de portas / frentes (linhas de abertura a 45 graus estilo arquitetônico)
            if tipo != "bancada":
                self._draw_door_opening_lines(painter, rect_mod, mod)

            # Nome e Dimensão no centro do móvel
            if self.show_names and rect_mod.height() > 24 and rect_mod.width() > 30:
                painter.setPen(QColor("#0F172A"))
                painter.setFont(font_name)
                w_mm = int(round((u1 - u0) * 1000))
                h_mm = int(round((z1 - z0) * 1000))

                text_title = nome
                text_dim = f"{w_mm} × {h_mm} mm"

                # Centraliza textos
                cy = rect_mod.center().y()
                rect_title = QRectF(rect_mod.left() + 2, cy - 14, rect_mod.width() - 4, 14)
                rect_sub = QRectF(rect_mod.left() + 2, cy + 2, rect_mod.width() - 4, 12)

                painter.drawText(rect_title, Qt.AlignCenter, text_title)
                painter.setFont(font_dim)
                painter.setPen(QColor("#475569"))
                painter.drawText(rect_sub, Qt.AlignCenter, text_dim)

    def _draw_door_opening_lines(self, painter: QPainter, rect: QRectF, mod: Dict[str, Any]) -> None:
        """Desenha linhas finas tracejadas indicando o sentido de abertura de portas ou gavetas."""
        pen_dash = QPen(QColor("#94A3B8"), 1.0, Qt.DotLine)
        painter.setPen(pen_dash)

        tipo = mod.get("tipo", "").lower()
        if "gavet" in tipo:
            # Gaveteiro: linhas horizontais divisórias
            n_gav = 4 if "4" in tipo else 3
            dy = rect.height() / n_gav
            for i in range(1, n_gav):
                y_div = rect.top() + dy * i
                painter.drawLine(QPointF(rect.left(), y_div), QPointF(rect.right(), y_div))
                # Puxadorzinho simbólico no meio de cada gaveta
                painter.fillRect(QRectF(rect.center().x() - 15, y_div - dy * 0.5 - 2, 30, 4), QColor("#64748B"))
        elif "2_portas" in tipo or "2p" in tipo or (rect.width() > 70 and "1_porta" not in tipo):
            # 2 Portas: Linha central e triângulos de abertura
            mid_x = rect.center().x()
            painter.drawLine(QPointF(mid_x, rect.top()), QPointF(mid_x, rect.bottom()))
            # Triângulo porta esquerda
            painter.drawLine(rect.topLeft(), QPointF(mid_x, rect.center().y()))
            painter.drawLine(rect.bottomLeft(), QPointF(mid_x, rect.center().y()))
            # Triângulo porta direita
            painter.drawLine(rect.topRight(), QPointF(mid_x, rect.center().y()))
            painter.drawLine(rect.bottomRight(), QPointF(mid_x, rect.center().y()))
        else:
            # 1 Porta padrão (abertura para direita ou esquerda)
            painter.drawLine(rect.topLeft(), QPointF(rect.right(), rect.center().y()))
            painter.drawLine(rect.bottomLeft(), QPointF(rect.right(), rect.center().y()))

    def _draw_dimensions(self, painter: QPainter) -> None:
        """Gera e renderiza as cadeias de cotas horizontais e verticais profissionais."""
        # 1. Cotas Horizontais Inferiores (Subdivisões de módulos e vãos)
        self._draw_horizontal_dimensions(painter)

        # 2. Cotas Verticais Laterais (Níveis de alturas de móveis e pé-direito)
        self._draw_vertical_dimensions(painter)

    def _draw_horizontal_dimensions(self, painter: QPainter) -> None:
        # Coleta todas as divisões horizontais dos módulos instalados
        x_breaks = {0.0, self.wall_width_m}
        for mod in self.modules_2d:
            if mod.get("tipo") != "bancada":
                x_breaks.add(round(mod["u_min"], 4))
                x_breaks.add(round(mod["u_max"], 4))

        sorted_breaks = sorted(b for b in x_breaks if 0.0 <= b <= self.wall_width_m)

        # Nível 1 de Cota: Divisões detalhadas (logo abaixo da parede)
        y_cota1 = -0.22  # metros abaixo do solo
        for i in range(len(sorted_breaks) - 1):
            u_start = sorted_breaks[i]
            u_end = sorted_breaks[i + 1]
            seg_len = u_end - u_start
            if seg_len > 0.015:  # ignora frestas menores que 15mm
                self._draw_dimension_segment_horizontal(painter, u_start, u_end, y_cota1)

        # Nível 2 de Cota: Cota Geral Total da Parede
        y_cota2 = -0.42  # metros abaixo do solo
        self._draw_dimension_segment_horizontal(painter, 0.0, self.wall_width_m, y_cota2, is_total=True)

    def _draw_vertical_dimensions(self, painter: QPainter) -> None:
        # Coleta os pontos críticos de altura (base e topo dos móveis instalados)
        z_breaks = {0.0, self.wall_height_m}
        for mod in self.modules_2d:
            z_breaks.add(round(mod["z_min"], 4))
            z_breaks.add(round(mod["z_max"], 4))

        sorted_z = sorted(z for z in z_breaks if 0.0 <= z <= self.wall_height_m)

        # Nível 1 de Cota Vertical: À esquerda da parede (detalhado)
        u_cota1 = -0.25  # metros à esquerda
        for i in range(len(sorted_z) - 1):
            z_start = sorted_z[i]
            z_end = sorted_z[i + 1]
            seg_len = z_end - z_start
            if seg_len > 0.015:
                self._draw_dimension_segment_vertical(painter, z_start, z_end, u_cota1)

        # Nível 2 de Cota Vertical: Cota Geral do Pé-Direito
        u_cota2 = -0.48  # metros à esquerda
        self._draw_dimension_segment_vertical(painter, 0.0, self.wall_height_m, u_cota2, is_total=True)

    def _draw_dimension_segment_horizontal(
        self, painter: QPainter, u_start: float, u_end: float, z_fixed: float, is_total: bool = False
    ) -> None:
        p1 = self.world_to_screen(u_start, z_fixed)
        p2 = self.world_to_screen(u_end, z_fixed)

        # Linhas de extensão conectando a parede ou móvel à cota
        pen_ext = QPen(QColor("#94A3B8"), 0.8, Qt.DashLine)
        painter.setPen(pen_ext)
        p_orig1 = self.world_to_screen(u_start, 0.0)
        p_orig2 = self.world_to_screen(u_end, 0.0)
        painter.drawLine(p_orig1, p1)
        painter.drawLine(p_orig2, p2)

        # Linha contínua da cota
        pen_cota = QPen(QColor("#0F172A") if is_total else QColor("#334155"), 1.4 if is_total else 1.1)
        painter.setPen(pen_cota)
        painter.drawLine(p1, p2)

        # Ticks arquitetônicos a 45 graus
        tick_sz = 5.0
        painter.drawLine(QPointF(p1.x() - tick_sz, p1.y() + tick_sz), QPointF(p1.x() + tick_sz, p1.y() - tick_sz))
        painter.drawLine(QPointF(p2.x() - tick_sz, p2.y() + tick_sz), QPointF(p2.x() + tick_sz, p2.y() - tick_sz))

        # Texto da medida em milímetros
        dist_mm = int(round((u_end - u_start) * 1000))
        label = f"{dist_mm}"

        mid_x = (p1.x() + p2.x()) * 0.5
        font_cota = QFont("Segoe UI", 9 if is_total else 8, QFont.Bold if is_total else QFont.Normal)
        painter.setFont(font_cota)

        # Fundo do badge de cota para legibilidade
        badge_rect = QRectF(mid_x - 18, p1.y() - 14, 36, 13)
        painter.fillRect(badge_rect, QColor("#F8FAFC"))
        painter.setPen(QColor("#0F172A"))
        painter.drawText(badge_rect, Qt.AlignCenter, label)

    def _draw_dimension_segment_vertical(
        self, painter: QPainter, z_start: float, z_end: float, u_fixed: float, is_total: bool = False
    ) -> None:
        p1 = self.world_to_screen(u_fixed, z_start)
        p2 = self.world_to_screen(u_fixed, z_end)

        # Linhas de extensão
        pen_ext = QPen(QColor("#94A3B8"), 0.8, Qt.DashLine)
        painter.setPen(pen_ext)
        p_orig1 = self.world_to_screen(0.0, z_start)
        p_orig2 = self.world_to_screen(0.0, z_end)
        painter.drawLine(p_orig1, p1)
        painter.drawLine(p_orig2, p2)

        # Linha contínua da cota
        pen_cota = QPen(QColor("#0F172A") if is_total else QColor("#334155"), 1.4 if is_total else 1.1)
        painter.setPen(pen_cota)
        painter.drawLine(p1, p2)

        # Ticks a 45 graus
        tick_sz = 5.0
        painter.drawLine(QPointF(p1.x() - tick_sz, p1.y() + tick_sz), QPointF(p1.x() + tick_sz, p1.y() - tick_sz))
        painter.drawLine(QPointF(p2.x() - tick_sz, p2.y() + tick_sz), QPointF(p2.x() + tick_sz, p2.y() - tick_sz))

        # Texto da medida
        dist_mm = int(round((z_end - z_start) * 1000))
        label = f"{dist_mm}"

        mid_y = (p1.y() + p2.y()) * 0.5
        font_cota = QFont("Segoe UI", 9 if is_total else 8, QFont.Bold if is_total else QFont.Normal)
        painter.setFont(font_cota)

        # Badge vertical
        badge_rect = QRectF(p1.x() - 38, mid_y - 7, 34, 14)
        painter.fillRect(badge_rect, QColor("#F8FAFC"))
        painter.setPen(QColor("#0F172A"))
        painter.drawText(badge_rect, Qt.AlignCenter, label)

    def _draw_installation_points(self, painter: QPainter) -> None:
        """Desenha pontos de instalações elétricas (tomadas) e hidráulicas (esgoto/água de pia) com cotas automáticas."""
        painter.save()
        font_inst = QFont("Segoe UI", 7, QFont.Bold)
        painter.setFont(font_inst)

        for m in self.modules_2d:
            u_min = m["u_min"]
            u_max = m["u_max"]
            z_min = m["z_min"]
            z_max = m["z_max"]
            tipo = str(m.get("tipo", "")).lower()
            name_l = str(m.get("name", "")).lower()
            u_center = (u_min + u_max) * 0.5

            # Ponto de Esgoto e Água da Pia
            if "pia" in tipo or "pia" in name_l:
                z_esgoto = 0.50  # 50cm do piso
                p_esg = self.world_to_screen(u_center, z_esgoto)
                # Ícone hidráulico (círculo azul ciano)
                painter.setPen(QPen(QColor("#0284C7"), 2.0))
                painter.setBrush(QBrush(QColor("#E0F2FE")))
                painter.drawEllipse(p_esg, 7, 7)
                painter.setPen(QColor("#0369A1"))
                painter.drawText(QPointF(p_esg.x() + 10, p_esg.y() + 4), f"💧 Esgoto/Água (Z={int(round(z_esgoto*1000))}mm)")

            # Ponto de Tomada de Eletros (Cooktop, Forno, Microondas ou Bancada)
            elif any(k in tipo or k in name_l for k in ("forno", "torre", "micro", "cooktop")):
                z_tomada = z_min + (z_max - z_min) * 0.5
                p_tom = self.world_to_screen(u_center, z_tomada)
                # Ícone elétrico (quadrado amarelo/laranja)
                painter.setPen(QPen(QColor("#D97706"), 2.0))
                painter.setBrush(QBrush(QColor("#FEF3C7")))
                painter.drawRect(QRectF(p_tom.x() - 6, p_tom.y() - 6, 12, 12))
                painter.setPen(QColor("#B45309"))
                painter.drawText(QPointF(p_tom.x() + 10, p_tom.y() + 4), f"⚡ Tomada 20A (Z={int(round(z_tomada*1000))}mm)")

        painter.restore()

    def _draw_title_block(self, painter: QPainter) -> None:
        """Desenha a legenda técnica no canto superior esquerdo com dados do ambiente."""
        rect_info = QRectF(20, 20, 280, 52)
        painter.fillRect(rect_info, QColor(255, 255, 255, 220))
        painter.setPen(QPen(QColor("#E2E8F0"), 1.0))
        painter.drawRect(rect_info)

        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.setPen(QColor("#0F172A"))
        painter.drawText(QPointF(30, 40), f"ELEVAÇÃO TÉCNICA: {self.wall_label.upper()}")

        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(QColor("#64748B"))
        dim_parede_str = f"Dimensões: {int(round(self.wall_width_m * 1000))}mm × {int(round(self.wall_height_m * 1000))}mm (Pé-Direito)"
        painter.drawText(QPointF(30, 58), dim_parede_str)


class WallElevationDialog(QDialog):
    """Janela completa de visualização, exportação e impressão de elevação técnica de paredes."""

    def __init__(self, viewport=None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.viewport = viewport
        self.setWindowTitle("TrazoMob — Elevação Técnica da Parede com Cotas")
        self.resize(1100, 720)

        self._build_ui()
        self.reload_from_scene()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # Barra Superior de Ferramentas
        bar_frame = QFrame()
        bar_frame.setStyleSheet("QFrame { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; }")
        bar_layout = QHBoxLayout(bar_frame)
        bar_layout.setContentsMargins(8, 6, 8, 6)
        bar_layout.setSpacing(10)

        # Seletor de Parede
        lbl_wall = QLabel("<b>Parede:</b>")
        self.cb_walls = QComboBox()
        self.cb_walls.setMinimumWidth(180)
        self.cb_walls.currentIndexChanged.connect(self._on_wall_selected)
        bar_layout.addWidget(lbl_wall)
        bar_layout.addWidget(self.cb_walls)

        # Opções visuais
        self.chk_cotas = QCheckBox("Exibir Cotas")
        self.chk_cotas.setChecked(True)
        self.chk_cotas.toggled.connect(self._toggle_cotas)
        bar_layout.addWidget(self.chk_cotas)

        self.chk_guides = QCheckBox("Exibir Níveis / Réguas")
        self.chk_guides.setChecked(True)
        self.chk_guides.toggled.connect(self._toggle_guides)
        bar_layout.addWidget(self.chk_guides)

        self.chk_names = QCheckBox("Nomes dos Módulos")
        self.chk_names.setChecked(True)
        self.chk_names.toggled.connect(self._toggle_names)
        bar_layout.addWidget(self.chk_names)

        self.chk_inst = QCheckBox("⚡ Pontos de Instalação")
        self.chk_inst.setChecked(True)
        self.chk_inst.setToolTip("Exibe pontos recomendados de tomadas elétricas e esgoto/água de pias com cotas de altura")
        self.chk_inst.toggled.connect(lambda chk: setattr(self.canvas, "show_instalacoes", chk) or self.canvas.update())
        bar_layout.addWidget(self.chk_inst)

        bar_layout.addStretch()

        # Botão Enquadrar
        btn_fit = QPushButton("🔍 Enquadrar")
        btn_fit.setToolTip("Ajusta o zoom e centraliza a elevação na tela")
        btn_fit.clicked.connect(self._on_fit_view)
        bar_layout.addWidget(btn_fit)

        # Botão Exportar Imagem PNG
        btn_export = QPushButton("📷 Salvar Imagem (PNG)")
        btn_export.setStyleSheet(
            "QPushButton { background: #0284C7; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px; }"
            "QPushButton:hover { background: #0369A1; }"
        )
        btn_export.clicked.connect(self._export_elevation_image)
        bar_layout.addWidget(btn_export)

        main_layout.addWidget(bar_frame)

        # Canvas da Elevação
        self.canvas = WallElevationCanvas(self)
        main_layout.addWidget(self.canvas, stretch=1)

    def _toggle_cotas(self, checked: bool) -> None:
        self.canvas.show_cotas = checked
        self.canvas.update()

    def _toggle_guides(self, checked: bool) -> None:
        self.canvas.show_guides = checked
        self.canvas.update()

    def _toggle_names(self, checked: bool) -> None:
        self.canvas.show_names = checked
        self.canvas.update()

    def _on_fit_view(self) -> None:
        self.canvas.fit_to_view()
        self.canvas.update()

    def reload_from_scene(self) -> None:
        """Carrega todas as paredes da cena 3D e preenche o seletor."""
        self.cb_walls.blockSignals(True)
        self.cb_walls.clear()

        scene = getattr(self.viewport, "scene", None) if self.viewport else None
        if not scene:
            self.cb_walls.blockSignals(False)
            return

        wall_mgr = WallSelectionManager.get_instance(self.viewport)
        selected_face_info = wall_mgr.selected_wall_face

        target_idx = 0
        current_opt_idx = 0

        # Procura todos os grupos de parede
        for g in getattr(scene, "groups", []):
            ext = getattr(g, "ext", {})
            if isinstance(ext, dict) and "trazomob_wall" in ext:
                params = ext["trazomob_wall"]
                pontos = params.get("pontos", [])
                h_wall = float(params.get("altura", 2.60))
                alturas = params.get("alturas", [])
                graph_data = params.get("graph_2d")
                graph_segs = graph_data.get("segments", []) if isinstance(graph_data, dict) else []
                is_closed = params.get("is_closed", False)

                num_segs = len(pontos) if is_closed else max(0, len(pontos) - 1)
                for seg_i in range(num_segs):
                    p0 = pontos[seg_i]
                    p1 = pontos[(seg_i + 1) % len(pontos)]
                    seg_len = math.hypot(p1[0] - p0[0], p1[1] - p0[1])

                    # Altura individual da parede, com fallback para o grafo 2D
                    # e, por fim, para o pé-direito global do grupo.
                    h_seg = h_wall
                    if seg_i < len(alturas):
                        h_seg = float(alturas[seg_i])
                    elif seg_i < len(graph_segs):
                        seg_h = graph_segs[seg_i].get("height")
                        if seg_h is not None:
                            h_seg = float(seg_h)

                    label = f"Parede #{seg_i + 1} — {int(round(seg_len * 1000))}mm"
                    wall_data = {
                        "wall_group": g,
                        "seg_index": seg_i,
                        "width_m": seg_len,
                        "height_m": h_seg,
                        "label": f"Parede #{seg_i + 1}",
                        "p0": p0,
                        "p1": p1,
                    }
                    self.cb_walls.addItem(label, wall_data)

                    # Se esta era a parede selecionada na cena 3D, define como ativa
                    if selected_face_info and selected_face_info.wall_group is g:
                        if selected_face_info.segment_index == seg_i:
                            target_idx = current_opt_idx

                    current_opt_idx += 1

        self.cb_walls.blockSignals(False)
        if self.cb_walls.count() > 0:
            self.cb_walls.setCurrentIndex(target_idx)
            self._load_elevation_for_item(target_idx)

    def _on_wall_selected(self, index: int) -> None:
        if index >= 0:
            self._load_elevation_for_item(index)

    def _load_elevation_for_item(self, index: int) -> None:
        wall_data = self.cb_walls.itemData(index)
        if not wall_data:
            return

        wall_group = wall_data["wall_group"]
        seg_index = wall_data["seg_index"]
        wall_w = wall_data["width_m"]
        wall_h = wall_data["height_m"]
        label = wall_data["label"]
        p0 = wall_data["p0"]
        p1 = wall_data["p1"]

        # Vetor tangencial da parede (eixo U) e vetor normal para o interior (eixo N)
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        l = math.hypot(dx, dy)
        if l < 1e-4:
            return

        u_dir = QVector3D(dx / l, dy / l, 0.0)
        # Normal apontando para o ambiente
        n_dir = QVector3D(-u_dir.y(), u_dir.x(), 0.0)
        p0_vec = QVector3D(p0[0], p0[1], 0.0)

        # Descobre os módulos encostados nesta parede
        scene = getattr(self.viewport, "scene", None) if self.viewport else None
        modules_2d: List[Dict[str, Any]] = []

        if scene:
            for g in getattr(scene, "groups", []):
                ext = getattr(g, "ext", {})
                if not isinstance(ext, dict):
                    continue

                is_mod = "trazomob_module" in ext
                is_bancada = "trazomob_bancada" in ext
                is_esquadria = "trazomob_esquadria" in ext

                if is_mod or is_bancada or is_esquadria:
                    b = get_module_carcass_bounds(g) or get_module_bounds(g)
                    if b is None:
                        continue

                    # Verifica se o módulo está posicionado encostado nesta parede (distância < 8cm)
                    # O bounding box tem 8 vértices
                    corners = [
                        QVector3D(b[0], b[2], b[4]),
                        QVector3D(b[1], b[2], b[4]),
                        QVector3D(b[0], b[3], b[4]),
                        QVector3D(b[1], b[3], b[4]),
                        QVector3D(b[0], b[2], b[5]),
                        QVector3D(b[1], b[2], b[5]),
                        QVector3D(b[0], b[3], b[5]),
                        QVector3D(b[1], b[3], b[5]),
                    ]

                    # Projeções na normal em relação a p0
                    proj_n = [QVector3D.dotProduct(c - p0_vec, n_dir) for c in corners]
                    min_n, max_n = min(proj_n), max(proj_n)

                    # Se estiver próximo da face da parede (min_n entre -0.05 e 0.90)
                    if -0.06 <= min_n <= 0.12 or (-0.12 <= max_n <= 0.06):
                        # Projeções no eixo horizontal da parede (U)
                        proj_u = [QVector3D.dotProduct(c - p0_vec, u_dir) for c in corners]
                        u_min = max(0.0, min(proj_u))
                        u_max = min(wall_w, max(proj_u))

                        if u_max - u_min > 0.04:  # largura mínima de 4cm
                            z_min = max(0.0, b[4])
                            z_max = min(wall_h, b[5])

                            mod_info = ext.get("trazomob_module", {})
                            nome = getattr(g, "name", "Módulo")
                            tipo = mod_info.get("tipo", "bancada" if is_bancada else "modulo")

                            modules_2d.append({
                                "u_min": u_min,
                                "u_max": u_max,
                                "z_min": z_min,
                                "z_max": z_max,
                                "nome": nome,
                                "tipo": tipo,
                            })

        # Consulta réguas de alturas
        from ..wall.guides import WallGuideRulerManager
        ruler_mgr = WallGuideRulerManager.get_instance()
        guide_levels = ruler_mgr.get_active_levels()

        self.canvas.set_data(
            wall_width_m=wall_w,
            wall_height_m=wall_h,
            wall_label=label,
            modules_2d=modules_2d,
            guide_levels=guide_levels,
        )

    def _export_elevation_image(self) -> None:
        """Exporta um desenho de alta definição (PNG) com resolução de prancha para fabricação."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Elevação Técnica da Parede",
            f"Elevacao_{self.canvas.wall_label.replace(' ', '_').replace('#', '')}.png",
            "Imagens PNG (*.png)",
        )
        if not filepath:
            return

        # Renderiza em resolução nítida (1920x1080)
        export_pixmap = QPixmap(1920, 1080)
        export_pixmap.fill(QColor("#F8FAFC"))

        painter = QPainter(export_pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        # Salva o estado atual do canvas
        old_w = self.canvas.width()
        old_h = self.canvas.height()
        old_scale = self.canvas._scale
        old_ox = self.canvas._offset_x
        old_oy = self.canvas._offset_y

        # Configura para o tamanho de exportação
        self.canvas.resize(1920, 1080)
        self.canvas.fit_to_view()

        # Renderiza
        self.canvas.render(painter)
        painter.end()

        # Restaura canvas
        self.canvas.resize(old_w, old_h)
        self.canvas._scale = old_scale
        self.canvas._offset_x = old_ox
        self.canvas._offset_y = old_oy

        if export_pixmap.save(filepath, "PNG"):
            QMessageBox.information(
                self,
                "Elevação Exportada",
                f"Desenho técnico 2D com cotas salvo com sucesso em:\n{filepath}",
            )
