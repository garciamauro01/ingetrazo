# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Visualizador interativo 2D de Plano de Corte e Aproveitamento de Chapas."""
from __future__ import annotations

import math
from typing import Any

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..production.optimizer import (
    CutPiece,
    CutSheet,
    GuillotineOptimizer,
    ResumoAproveitamento,
    SheetConfig,
    resumo_aproveitamento,
)


class SheetCanvasWidget(QWidget):
    """Área gráfica de desenho 2D da chapa de corte com peças e cotas."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sheet: CutSheet | None = None
        self._config: SheetConfig = SheetConfig()
        self.setMinimumSize(700, 480)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self._hover_cache: list[tuple[QRectF, CutPiece]] = []

    def set_sheet(self, sheet: CutSheet | None, config: SheetConfig) -> None:
        self._sheet = sheet
        self._config = config
        self._hover_cache.clear()
        self.update()

    def mouseMoveEvent(self, event) -> None:
        pos = event.position() if hasattr(event, "position") else event.pos()
        for rect, p in self._hover_cache:
            if rect.contains(pos.x(), pos.y()):
                comp_c = p.comprimento
                larg_c = p.largura
                comp_f = getattr(p, "comprimento_final", comp_c)
                larg_f = getattr(p, "largura_final", larg_c)
                esp_f = getattr(p, "espessura_fita", 0.45)
                fitas = []
                if p.fita_c1: fitas.append("C1")
                if p.fita_c2: fitas.append("C2")
                if p.fita_l1: fitas.append("L1")
                if p.fita_l2: fitas.append("L2")
                fita_str = ", ".join(fitas) if fitas else "Nenhuma"
                rot_str = " (Rotacionada 90°)" if p.rotacionada else ""
                tip = (
                    f"<b>{p.nome}</b>{rot_str}<br>"
                    f"📏 <b>Medida Final:</b> {comp_f:.1f} x {larg_f:.1f} mm<br>"
                    f"✂️ <b>Medida de Corte:</b> {comp_c:.1f} x {larg_c:.1f} mm<br>"
                    f"🎗️ <b>Fitas:</b> {fita_str} (esp. {esp_f:.2f}mm)<br>"
                    f"🪵 <b>Material:</b> {p.material} ({p.espessura:.0f}mm)"
                )
                self.setToolTip(tip)
                return
        self.setToolTip("")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        w_view = self.width()
        h_view = self.height()

        # Fundo do canvas (cinza blueprint moderno)
        painter.fillRect(0, 0, w_view, h_view, QColor("#1e2024"))

        if not self._sheet:
            painter.setPen(QColor("#94a3b8"))
            painter.setFont(QFont("Segoe UI", 12))
            painter.drawText(self.rect(), Qt.AlignCenter, "Nenhuma chapa gerada para visualização.")
            return

        sheet = self._sheet
        cfg = self._config

        # Margem de respiro no visualizador
        margin = 50.0
        avail_w = max(100.0, w_view - 2 * margin)
        avail_h = max(100.0, h_view - 2 * margin)

        # Escala uniforme para caber a chapa no canvas
        scale_x = avail_w / cfg.comprimento
        scale_y = avail_h / cfg.largura
        scale = min(scale_x, scale_y)

        draw_w = cfg.comprimento * scale
        draw_h = cfg.largura * scale

        ox = (w_view - draw_w) / 2.0
        oy = (h_view - draw_h) / 2.0

        # Sombra sutil sob a chapa
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 70))
        painter.drawRoundedRect(QRectF(ox + 5, oy + 5, draw_w, draw_h), 4, 4)

        # 1. Desenho da chapa bruta
        chapa_rect = QRectF(ox, oy, draw_w, draw_h)
        painter.setBrush(QColor("#f8fafc"))
        painter.setPen(QPen(QColor("#475569"), 1.5))
        painter.drawRect(chapa_rect)

        # 2. Desenho das margens de refilo (linha pontilhada)
        if cfg.refilo > 0:
            ref_x = ox + (cfg.refilo * scale)
            ref_y = oy + (cfg.refilo * scale)
            ref_w = draw_w - (2 * cfg.refilo * scale)
            ref_h = draw_h - (2 * cfg.refilo * scale)
            pen_ref = QPen(QColor("#94a3b8"), 1.0, Qt.DashLine)
            painter.setPen(pen_ref)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(QRectF(ref_x, ref_y, ref_w, ref_h))

        # 3. Desenho das sobras aproveitáveis (hachurado verde claro)
        for sx, sy, sw, sh in sheet.sobras:
            r_sobra = QRectF(ox + sx * scale, oy + sy * scale, sw * scale, sh * scale)
            painter.setPen(QPen(QColor("#10b981"), 1.0, Qt.DotLine))
            painter.setBrush(QColor(16, 185, 129, 35))
            painter.drawRect(r_sobra)

            if r_sobra.width() > 50 and r_sobra.height() > 25:
                painter.setPen(QColor("#059669"))
                painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
                painter.drawText(
                    r_sobra,
                    Qt.AlignCenter,
                    f"Sobra\n{int(sw)}x{int(sh)}",
                )

        # Paleta de cores harmoniosas para as peças
        cores_pecas = [
            QColor("#e0e7ff"),  # Índigo suave
            QColor("#dcfce7"),  # Verde suave
            QColor("#fef3c7"),  # Âmbar suave
            QColor("#fee2e2"),  # Rosa/coral suave
            QColor("#f3e8ff"),  # Roxo suave
            QColor("#e0f2fe"),  # Ciano suave
            QColor("#ffedd5"),  # Laranja suave
        ]

        # 4. Desenho das peças cortadas
        new_hover_cache = []
        for i, p in enumerate(sheet.pecas):
            px = ox + p.x * scale
            py = oy + p.y * scale
            pw = p.w_aloc * scale
            ph = p.h_aloc * scale
            rect_peca = QRectF(px, py, pw, ph)
            new_hover_cache.append((rect_peca, p))

            cor = cores_pecas[i % len(cores_pecas)]
            painter.setPen(QPen(QColor("#334155"), 1.2))
            painter.setBrush(cor)
            painter.drawRect(rect_peca)

            # Fita de borda (arestas destacadas com fita vermelha/laranja grossa)
            pen_fita = QPen(QColor("#dc2626"), 3.0, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(pen_fita)

            # C1 e C2: arestas de comprimento
            # L1 e L2: arestas de largura
            if not p.rotacionada:
                # Comprimento na horizontal (topo/base), Largura na vertical (esq/dir)
                if p.fita_c1: painter.drawLine(QPointF(px, py + ph), QPointF(px + pw, py + ph))  # Base
                if p.fita_c2: painter.drawLine(QPointF(px, py), QPointF(px + pw, py))            # Topo
                if p.fita_l1: painter.drawLine(QPointF(px, py), QPointF(px, py + ph))            # Esquerda
                if p.fita_l2: painter.drawLine(QPointF(px + pw, py), QPointF(px + pw, py + ph))  # Direita
            else:
                # Rotacionada 90°: Comprimento na vertical, Largura na horizontal
                if p.fita_c1: painter.drawLine(QPointF(px, py), QPointF(px, py + ph))
                if p.fita_c2: painter.drawLine(QPointF(px + pw, py), QPointF(px + pw, py + ph))
                if p.fita_l1: painter.drawLine(QPointF(px, py + ph), QPointF(px + pw, py + ph))
                if p.fita_l2: painter.drawLine(QPointF(px, py), QPointF(px + pw, py))

            # Rótulo de texto da peça com dimensões de corte e final
            if pw >= 30 and ph >= 18:
                painter.setPen(QColor("#0f172a"))
                rot_tag = " 🔄" if p.rotacionada else ""

                # Exibe medidas: Corte (bruto serra) e Final (acabado)
                comp_corte = p.comprimento
                larg_corte = p.largura
                comp_final = getattr(p, "comprimento_final", 0.0) or comp_corte
                larg_final = getattr(p, "largura_final", 0.0) or larg_corte
                tem_desconto = (abs(comp_corte - comp_final) > 0.05 or abs(larg_corte - larg_final) > 0.05)

                font_size = 9 if (pw > 70 and ph > 40) else 7
                painter.setFont(QFont("Segoe UI", font_size, QFont.Bold))

                if ph > 50 and pw > 80 and tem_desconto:
                    txt_dim = f"Corte: {comp_corte:.1f}x{larg_corte:.1f}\n(Fin: {int(round(comp_final))}x{int(round(larg_final))})"
                    txt_full = f"{p.nome}{rot_tag}\n{txt_dim}"
                elif ph > 35:
                    txt_dim = f"{comp_corte:.1f}x{larg_corte:.1f}" if tem_desconto else f"{int(comp_corte)}x{int(larg_corte)}"
                    txt_full = f"{p.nome}{rot_tag}\n{txt_dim}"
                else:
                    txt_full = f"{comp_corte:.1f}x{larg_corte:.1f}" if tem_desconto else f"{int(comp_corte)}x{int(larg_corte)}"

                painter.drawText(rect_peca.adjusted(2, 2, -2, -2), Qt.AlignCenter, txt_full)

            # 4.1. Marcações visuais de furação e usinagem (canecos, cavilhas, rasgos)
            ops = getattr(p, "operacoes", []) or []
            if ops and pw >= 20 and ph >= 15:
                for op in ops:
                    op_tipo = op.get("tipo", "furo")
                    op_x = float(op.get("x", 0.0))
                    op_y = float(op.get("y", 0.0))
                    diam = float(op.get("diametro", 5.0))

                    # Converte coordenadas locais da peça para o canvas da chapa
                    if not p.rotacionada:
                        pt_x = px + (op_x / max(1.0, p.comprimento)) * pw
                        pt_y = py + (op_y / max(1.0, p.largura)) * ph
                    else:
                        pt_x = px + (op_y / max(1.0, p.largura)) * pw
                        pt_y = py + (op_x / max(1.0, p.comprimento)) * ph

                    if op_tipo == "furo":
                        r_px = max(2.0, min(8.0, (diam / 2.0) * scale))
                        painter.setPen(QPen(QColor("#0284c7"), 1.0))
                        painter.setBrush(QBrush(QColor(2, 132, 199, 140)))
                        painter.drawEllipse(QPointF(pt_x, pt_y), r_px, r_px)
                        # Cruz central técnica do furo
                        painter.setPen(QPen(QColor("#ffffff"), 0.8))
                        painter.drawLine(QPointF(pt_x - r_px, pt_y), QPointF(pt_x + r_px, pt_y))
                        painter.drawLine(QPointF(pt_x, pt_y - r_px), QPointF(pt_x, pt_y + r_px))
                    elif op_tipo in ("rasgo", "rebaixo"):
                        # Desenha linha tracejada representando o canal
                        painter.setPen(QPen(QColor("#ea580c"), 1.5, Qt.DashLine))
                        if not p.rotacionada:
                            painter.drawLine(QPointF(px, pt_y), QPointF(px + pw, pt_y))
                        else:
                            painter.drawLine(QPointF(pt_x, py), QPointF(pt_x, py + ph))


        # 5. Cotas da Chapa Bruta no Rodapé e Lateral
        painter.setPen(QColor("#cbd5e1"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        # Cota horizontal
        painter.drawText(
            QRectF(ox, oy + draw_h + 8, draw_w, 25),
            Qt.AlignCenter,
            f"↔ {int(cfg.comprimento)} mm",
        )
        # Cota vertical
        painter.save()
        painter.translate(ox - 18, oy + (draw_h / 2.0))
        painter.rotate(-90)
        painter.drawText(QRectF(-60, -10, 120, 20), Qt.AlignCenter, f"↕ {int(cfg.largura)} mm")
        painter.restore()

        self._hover_cache = new_hover_cache


class CutPlanViewerDialog(QDialog):
    """Janela completa de visualização, navegação e exportação do Plano de Corte."""

    def __init__(self, raw_parts: list[dict[str, Any]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("📐 Plano de Corte Otimizado 2D — IngeTrazo / TrazoMob")
        self.resize(1150, 750)
        self._raw_parts = raw_parts
        self._config = SheetConfig()
        self._optimizer = GuillotineOptimizer(self._config)
        self._sheets_by_material: dict[str, list[CutSheet]] = {}
        self._current_material: str = ""
        self._current_sheet_idx: int = 0
        self._resumo: ResumoAproveitamento | None = None

        self._build_ui()
        self._run_optimization()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Barra Superior: Parâmetros e Configuração da Chapa
        top_box = QGroupBox("Configurações da Chapa e Corte")
        top_box.setStyleSheet("font-weight: bold;")
        h_top = QHBoxLayout(top_box)
        h_top.setSpacing(12)

        h_top.addWidget(QLabel("Chapa (mm):"))
        self.sp_chapa_comp = QSpinBox()
        self.sp_chapa_comp.setRange(500, 4000)
        self.sp_chapa_comp.setValue(int(self._config.comprimento))
        self.sp_chapa_comp.setSuffix(" L")
        h_top.addWidget(self.sp_chapa_comp)

        self.sp_chapa_larg = QSpinBox()
        self.sp_chapa_larg.setRange(500, 4000)
        self.sp_chapa_larg.setValue(int(self._config.largura))
        self.sp_chapa_larg.setSuffix(" A")
        h_top.addWidget(self.sp_chapa_larg)

        h_top.addWidget(QLabel("Serra / Kerf:"))
        self.sp_kerf = QDoubleSpinBox()
        self.sp_kerf.setRange(1.0, 10.0)
        self.sp_kerf.setSingleStep(0.5)
        self.sp_kerf.setValue(self._config.espessura_corte)
        self.sp_kerf.setSuffix(" mm")
        h_top.addWidget(self.sp_kerf)

        h_top.addWidget(QLabel("Refilo:"))
        self.sp_refilo = QDoubleSpinBox()
        self.sp_refilo.setRange(0.0, 50.0)
        self.sp_refilo.setValue(self._config.refilo)
        self.sp_refilo.setSuffix(" mm")
        h_top.addWidget(self.sp_refilo)

        btn_recalc = QPushButton("⚡ Re-otimizar")
        btn_recalc.setStyleSheet("background-color: #2563eb; color: white; padding: 6px 14px; border-radius: 4px;")
        btn_recalc.clicked.connect(self._run_optimization)
        h_top.addWidget(btn_recalc)

        h_top.addStretch()

        btn_export_img = QPushButton("📷 Salvar Imagem")
        btn_export_img.clicked.connect(self._export_sheet_image)
        h_top.addWidget(btn_export_img)

        btn_export_dxf = QPushButton("📐 Exportar DXF CNC")
        btn_export_dxf.setStyleSheet("background-color: #059669; color: white; padding: 6px 12px; border-radius: 4px; font-weight: bold;")
        btn_export_dxf.clicked.connect(self._export_sheet_dxf)
        h_top.addWidget(btn_export_dxf)

        main_layout.addWidget(top_box)

        # Barra de Navegação de Chapas e Estatísticas
        nav_bar = QHBoxLayout()
        nav_bar.setSpacing(14)

        nav_bar.addWidget(QLabel("Material:"))
        self.cb_material = QComboBox()
        self.cb_material.setMinimumWidth(220)
        self.cb_material.currentIndexChanged.connect(self._on_material_changed)
        nav_bar.addWidget(self.cb_material)

        self.btn_prev_sheet = QPushButton("◀ Anterior")
        self.btn_prev_sheet.clicked.connect(self._prev_sheet)
        nav_bar.addWidget(self.btn_prev_sheet)

        self.lbl_sheet_nav = QLabel("Chapa 1 de 1")
        self.lbl_sheet_nav.setStyleSheet("font-size: 13px; font-weight: bold;")
        nav_bar.addWidget(self.lbl_sheet_nav)

        self.btn_next_sheet = QPushButton("Próxima ▶")
        self.btn_next_sheet.clicked.connect(self._next_sheet)
        nav_bar.addWidget(self.btn_next_sheet)

        nav_bar.addStretch()

        # Banner de Indicadores / Estatísticas
        self.lbl_sheet_stats = QLabel("Aproveitamento: 0% | Área Útil: 0.00 m² | Fita de Borda: 0.0 m")
        self.lbl_sheet_stats.setStyleSheet(
            "background-color: #ecfdf5; color: #047857; font-weight: bold; padding: 6px 12px; "
            "border: 1px solid #a7f3d0; border-radius: 6px; font-size: 12px;"
        )
        nav_bar.addWidget(self.lbl_sheet_stats)

        main_layout.addLayout(nav_bar)

        # Detalhe agregado do material selecionado (aproveitamento + sobras)
        self.lbl_material_detail = QLabel("")
        self.lbl_material_detail.setStyleSheet(
            "background-color: #fffbeb; color: #92400e; font-weight: bold; padding: 5px 12px; "
            "border: 1px solid #fcd34d; border-radius: 6px; font-size: 12px;"
        )
        main_layout.addWidget(self.lbl_material_detail)

        # Canvas Gráfico 2D
        self.canvas = SheetCanvasWidget(self)
        main_layout.addWidget(self.canvas, stretch=1)

        # Rodapé com Resumo Geral do Projeto
        foot_layout = QHBoxLayout()
        self.lbl_total_summary = QLabel("Total do Projeto: 0 chapas | 0.00 m²")
        self.lbl_total_summary.setStyleSheet("font-weight: 500; color: #64748b;")
        foot_layout.addWidget(self.lbl_total_summary)

        foot_layout.addStretch()

        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(self.close)
        foot_layout.addWidget(btn_close)

        main_layout.addLayout(foot_layout)

    def _run_optimization(self) -> None:
        """Executa o algoritmo com as configurações atuais."""
        self._config.comprimento = float(self.sp_chapa_comp.value())
        self._config.largura = float(self.sp_chapa_larg.value())
        self._config.espessura_corte = float(self.sp_kerf.value())
        self._config.refilo = float(self.sp_refilo.value())

        self._optimizer = GuillotineOptimizer(self._config)
        self._sheets_by_material = self._optimizer.optimize(self._raw_parts)

        if self._optimizer.pecas_nao_alocadas:
            nomes = sorted({p.nome for p in self._optimizer.pecas_nao_alocadas})
            lista = "\n".join(f"• {n}" for n in nomes[:10])
            if len(nomes) > 10:
                lista += f"\n• … e mais {len(nomes) - 10} peça(s)"
            QMessageBox.warning(
                self,
                "Peças não alocadas",
                "Estas peças não couberam em nenhuma chapa e NÃO aparecem no "
                "plano de corte:\n\n" + lista +
                "\n\nAumente o tamanho da chapa ou reduza as peças.",
            )

        # Atualiza combo de materiais
        self.cb_material.blockSignals(True)
        self.cb_material.clear()
        for mat in self._sheets_by_material.keys():
            chapas_count = len(self._sheets_by_material[mat])
            self.cb_material.addItem(f"{mat} ({chapas_count} chapa{'s' if chapas_count > 1 else ''})", mat)
        self.cb_material.blockSignals(False)

        if self._sheets_by_material:
            self._current_material = list(self._sheets_by_material.keys())[0]
            self._current_sheet_idx = 0
            self._update_view()
        else:
            self.canvas.set_sheet(None, self._config)
            self.lbl_sheet_stats.setText("Nenhuma peça para cortar.")
            self.lbl_material_detail.setText("")

        self._resumo = resumo_aproveitamento(
            self._sheets_by_material, self._optimizer.pecas_nao_alocadas
        )
        self._update_total_summary()

    def _on_material_changed(self) -> None:
        mat_data = self.cb_material.currentData()
        if mat_data and mat_data in self._sheets_by_material:
            self._current_material = mat_data
            self._current_sheet_idx = 0
            self._update_view()
            self._update_material_detail()

    def _update_material_detail(self) -> None:
        """Exibe o agregado de aproveitamento e sobras do material selecionado."""
        if not self._resumo:
            self.lbl_material_detail.setText("")
            return
        rm = self._resumo.por_material.get(self._current_material)
        if not rm:
            self.lbl_material_detail.setText("")
            return
        area_util_m2 = rm.area_util_mm2 / 1_000_000.0
        area_bruta_m2 = rm.area_bruta_mm2 / 1_000_000.0
        area_sobras_m2 = rm.area_sobras_mm2 / 1_000_000.0
        self.lbl_material_detail.setText(
            f"📦 {rm.material} • "
            f"{rm.chapas} chapa(s) • {rm.pecas} peça(s) • "
            f"✂️ Aproveitamento: {rm.aproveitamento_pct}% "
            f"({area_util_m2:.2f}/{area_bruta_m2:.2f} m²) • "
            f"🪵 Sobras: {rm.sobras} retalho(s) = {area_sobras_m2:.2f} m² • "
            f"🎗️ Fita: {rm.metros_fita:.1f} m"
        )

    def _prev_sheet(self) -> None:
        if self._current_sheet_idx > 0:
            self._current_sheet_idx -= 1
            self._update_view()

    def _next_sheet(self) -> None:
        chapas = self._sheets_by_material.get(self._current_material, [])
        if self._current_sheet_idx < len(chapas) - 1:
            self._current_sheet_idx += 1
            self._update_view()

    def _update_view(self) -> None:
        chapas = self._sheets_by_material.get(self._current_material, [])
        if not chapas:
            self.canvas.set_sheet(None, self._config)
            return

        total_chapas = len(chapas)
        sheet = chapas[self._current_sheet_idx]

        self.canvas.set_sheet(sheet, self._config)
        self.lbl_sheet_nav.setText(f"Chapa {self._current_sheet_idx + 1} de {total_chapas}")
        self.btn_prev_sheet.setEnabled(self._current_sheet_idx > 0)
        self.btn_next_sheet.setEnabled(self._current_sheet_idx < total_chapas - 1)

        area_util_m2 = sheet.area_util_mm2 / 1_000_000.0
        area_sobras_m2 = sheet.area_sobras_mm2 / 1_000_000.0
        self.lbl_sheet_stats.setText(
            f"🎯 Aproveitamento: {sheet.aproveitamento_pct}%  |  "
            f"Área Útil: {area_util_m2:.2f} m²  |  "
            f"Peças: {len(sheet.pecas)}  |  "
            f"Sobras: {len(sheet.sobras)} retalho(s) ({area_sobras_m2:.2f} m²)  |  "
            f"Fita de Borda: {sheet.metros_fita:.1f} m"
        )

    def _update_total_summary(self) -> None:
        total_chapas = sum(len(c) for c in self._sheets_by_material.values())
        total_pecas = sum(len(s.pecas) for c in self._sheets_by_material.values() for s in c)
        total_fita = sum(s.metros_fita for c in self._sheets_by_material.values() for s in c)

        resumo = self._resumo
        if resumo:
            area_bruta_m2 = resumo.area_bruta_mm2 / 1_000_000.0
            area_util_m2 = resumo.area_util_mm2 / 1_000_000.0
            area_sobras_m2 = resumo.area_sobras_mm2 / 1_000_000.0
            texto = (
                f"📊 Total do Projeto: {resumo.total_chapas} chapa(s)  •  "
                f"{resumo.total_pecas} peça(s) alocada(s)  •  "
                f"✂️ Aproveitamento geral: {resumo.aproveitamento_geral_pct}% "
                f"({area_util_m2:.2f}/{area_bruta_m2:.2f} m²)  •  "
                f"🪵 Sobras: {resumo.total_sobras} retalho(s) = {area_sobras_m2:.2f} m²  •  "
                f"🎗️ Fita: {resumo.metros_fita_total:.1f} m"
            )
            if resumo.pecas_nao_alocadas:
                texto += f"  •  ⚠️ {resumo.pecas_nao_alocadas} peça(s) não alocada(s)"
        else:
            texto = (
                f"📊 Total do Projeto: {total_chapas} chapa(s)  •  "
                f"{total_pecas} peça(s) alocada(s)  •  "
                f"🎗️ Fita: {total_fita:.1f} m"
            )

        self.lbl_total_summary.setText(texto)

    def _export_sheet_image(self) -> None:
        """Salva uma imagem de alta resolução (PNG) da chapa atual."""
        chapas = self._sheets_by_material.get(self._current_material, [])
        if not chapas:
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Diagrama de Corte",
            f"Plano_Corte_Chapa_{self._current_sheet_idx + 1}.png",
            "Imagens PNG (*.png)",
        )
        if not filepath:
            return

        pix = QPixmap(self.canvas.size())
        self.canvas.render(pix)
        if pix.save(filepath, "PNG"):
            QMessageBox.information(self, "Exportação", f"Diagrama salvo com sucesso em:\n{filepath}")

    def _export_sheet_dxf(self) -> None:
        """Exporta o plano de corte da chapa atual em formato DXF CNC com camadas e furações."""
        chapas = self._sheets_by_material.get(self._current_material, [])
        if not chapas:
            return

        sheet = chapas[self._current_sheet_idx]
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Chapa para DXF CNC",
            f"CNC_Chapa_{sheet.indice}_{sheet.material.split()[0]}.dxf",
            "Desenho DXF (*.dxf)",
        )
        if not filepath:
            return

        try:
            from .dxf_cnc import export_cut_sheet_dxf
            total = export_cut_sheet_dxf(sheet, filepath, include_holes=True)
            QMessageBox.information(
                self,
                "Exportação DXF Concluída",
                f"Chapa #{sheet.indice} exportada com sucesso!\n\n"
                f"• Arquivo: {filepath}\n"
                f"• Entidades DXF: {total} (peças, cotas e furações CNC)",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Erro na Exportação DXF", f"Falha ao gerar arquivo DXF:\n{exc}")
