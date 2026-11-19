# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Gerador e Visualizador de Etiquetas Técnicas de Fabricação (TrazoMob).

Gera etiquetas para peças de marcenaria prontas para impressão térmica ou A4,
contendo:
- Nome da peça e módulo pai
- Medidas finais (Comp x Larg x Esp)
- Medidas de corte bruto
- Padrão de MDF / Material
- Indicadores visuais de fita de borda (C1, C2, L1, L2)
- Resumo de furações e usinagens
- Código de barras **Code 128 real** (com dígito verificador módulo 103) e
  **QR Code**, ambos desenhados via ``QPainter`` sem dependências externas.

A carga útil impressa (:func:`label_payload`) é **estável** — derivada de
``zlib.crc32`` e não do ``hash()`` embutido (que muda a cada processo por causa
do ``PYTHONHASHSEED``) — de modo que a etiqueta impressa e a relida no chão de
fábrica coincidem.
"""
from __future__ import annotations

import os
import zlib
from typing import Any, List

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPixmap, QColor, QFont, QPen, QBrush
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFileDialog, QMessageBox,
)

from .barcode import code128_bar_widths
from .qr import encode as qr_encode


#: Campos de dimensão normalizados no código estável (evita que ``700`` e
#: ``700.0`` gerem códigos diferentes para a mesma peça).
_CAMPOS_DIMENSAO = ("comprimento", "largura", "espessura")


def _campo_normalizado(part: dict[str, Any], campo: str) -> str:
    valor = part.get(campo, "")
    if campo in _CAMPOS_DIMENSAO:
        try:
            return f"{round(float(valor or 0.0)):d}"
        except (TypeError, ValueError):
            return str(valor)
    return str(valor)


def stable_piece_code(part: dict[str, Any]) -> str:
    """Código curto e **estável** de uma peça, igual em qualquer execução.

    Usa ``zlib.crc32`` (determinístico) em vez do ``hash()`` embutido, que
    varia entre processos por causa da randomização de hash do Python. As
    dimensões são arredondadas, de modo que ``700`` e ``700.0`` produzam o
    mesmo código.
    """
    chave = "|".join(
        _campo_normalizado(part, campo) for campo in
        ("nome", "modulo", "material", *_CAMPOS_DIMENSAO)
    )
    return f"{zlib.crc32(chave.encode('utf-8')) % 100000:05d}"


def label_payload(part: dict[str, Any]) -> str:
    """Carga útil ASCII impressa no Code 128 e no QR (estável e escaneável)."""
    comp = int(round(float(part.get("comprimento", 0.0) or 0.0)))
    larg = int(round(float(part.get("largura", 0.0) or 0.0)))
    return f"TM-{stable_piece_code(part)}-{comp}-{larg}"


def _draw_code128_barcode(painter: QPainter, text: str, rect: QRectF) -> None:
    """Desenha um Code 128 real (escaneável) no retângulo informado."""
    barras = code128_bar_widths(text)
    total_modulos = sum(largura for _, largura in barras)
    if total_modulos <= 0 or rect.width() <= 0:
        return

    quiet_zone = 10  # módulos de zona silenciosa em cada lado (norma Code 128)
    escala = rect.width() / float(total_modulos + 2 * quiet_zone)
    x = rect.x() + quiet_zone * escala

    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, False)  # barras nítidas
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(Qt.black))
    for e_barra, largura in barras:
        largura_px = largura * escala
        if e_barra:
            painter.drawRect(QRectF(x, rect.y(), largura_px + 0.25, rect.height()))
        x += largura_px
    painter.restore()


def _draw_qr(painter: QPainter, text: str, rect: QRectF) -> None:
    """Desenha um QR Code (correção M) no retângulo informado."""
    try:
        matriz = qr_encode(text, "M")
    except ValueError:
        return
    n = len(matriz)
    if n == 0 or rect.width() <= 0 or rect.height() <= 0:
        return

    lado = min(rect.width(), rect.height())
    modulo = lado / float(n + 4)  # 2 módulos de zona silenciosa em cada lado
    origem_x = rect.x() + (rect.width() - lado) / 2.0 + 2 * modulo
    origem_y = rect.y() + (rect.height() - lado) / 2.0 + 2 * modulo

    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, False)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(Qt.black))
    for r in range(n):
        linha = matriz[r]
        for c in range(n):
            if linha[c]:
                painter.drawRect(QRectF(origem_x + c * modulo, origem_y + r * modulo,
                                        modulo + 0.4, modulo + 0.4))
    painter.restore()


def render_label_pixmap(
    part: dict[str, Any],
    width_px: int = 340,
    height_px: int = 210,
    scale: float = 1.0,
) -> QPixmap:
    """Renderiza uma etiqueta técnica de produção como um ``QPixmap``.

    O layout é desenhado em coordenadas lógicas ``width_px`` x ``height_px`` e
    o ``scale`` multiplica a resolução física (para impressão nítida do código
    de barras e do QR sem alterar a diagramação).
    """
    scale = max(1.0, float(scale))
    pix = QPixmap(int(round(width_px * scale)), int(round(height_px * scale)))
    pix.fill(Qt.white)

    painter = QPainter(pix)
    if scale != 1.0:
        painter.scale(scale, scale)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.TextAntialiasing, True)

    # Borda externa da etiqueta
    painter.setPen(QPen(QColor("#94A3B8"), 1))
    painter.drawRoundedRect(QRectF(1, 1, width_px - 2, height_px - 2), 4, 4)

    # Faixa do Cabeçalho com Nome da Peça e Módulo
    header_rect = QRectF(2, 2, width_px - 4, 32)
    painter.fillRect(header_rect, QColor("#1E293B"))

    painter.setPen(Qt.white)
    font_h = QFont("Arial", 9, QFont.Bold)
    painter.setFont(font_h)

    nome_peca = part.get("nome", "Peça")
    mod_pai = part.get("modulo", "")
    title = f"{nome_peca}" + (f" ({mod_pai})" if mod_pai else "")
    painter.drawText(QRectF(8, 4, width_px - 16, 26), Qt.AlignLeft | Qt.AlignVCenter, title)

    # Medidas Principais em Destaque
    comp = part.get("comprimento", 0.0)
    larg = part.get("largura", 0.0)
    esp = part.get("espessura", 15.0)
    comp_c = part.get("comprimento_corte", comp)
    larg_c = part.get("largura_corte", larg)

    painter.setPen(QColor("#0F172A"))
    font_med = QFont("Arial", 12, QFont.Bold)
    painter.setFont(font_med)
    med_final_txt = f"{int(round(comp))} x {int(round(larg))} x {int(round(esp))} mm"
    painter.drawText(QRectF(8, 38, width_px - 16, 20), Qt.AlignLeft, med_final_txt)

    # Sub-medida: Corte Bruto e Material
    font_sub = QFont("Arial", 8)
    painter.setFont(font_sub)
    painter.setPen(QColor("#475569"))
    mat_txt = str(part.get("material", "MDF"))
    corte_txt = f"Corte Bruto: {int(round(comp_c))} x {int(round(larg_c))} mm | Mat: {mat_txt}"
    painter.drawText(QRectF(8, 60, width_px - 16, 16), Qt.AlignLeft, corte_txt)

    # Diagrama de Fitas de Borda (C1, C2, L1, L2)
    c1 = bool(part.get("fita_c1", False))
    c2 = bool(part.get("fita_c2", False))
    l1 = bool(part.get("fita_l1", False))
    l2 = bool(part.get("fita_l2", False))
    esp_f = part.get("espessura_fita", 0.45)

    diag_x = 12
    diag_y = 86
    diag_w = 110
    diag_h = 60

    # Retângulo central da peça
    painter.setPen(QPen(QColor("#CBD5E1"), 1))
    painter.setBrush(QBrush(QColor("#F8FAFC")))
    painter.drawRect(QRectF(diag_x, diag_y, diag_w, diag_h))

    # Desenha bordos com fita destacados em azul/laranja
    pen_tape = QPen(QColor("#0284C7"), 3)
    pen_none = QPen(QColor("#E2E8F0"), 1)

    # Topo (C1)
    painter.setPen(pen_tape if c1 else pen_none)
    painter.drawLine(diag_x, diag_y, diag_x + diag_w, diag_y)

    # Base (C2)
    painter.setPen(pen_tape if c2 else pen_none)
    painter.drawLine(diag_x, diag_y + diag_h, diag_x + diag_w, diag_y + diag_h)

    # Esquerda (L1)
    painter.setPen(pen_tape if l1 else pen_none)
    painter.drawLine(diag_x, diag_y, diag_x, diag_y + diag_h)

    # Direita (L2)
    painter.setPen(pen_tape if l2 else pen_none)
    painter.drawLine(diag_x + diag_w, diag_y, diag_x + diag_w, diag_y + diag_h)

    # Texto indicador de fita
    painter.setPen(QColor("#0F172A"))
    font_diag = QFont("Arial", 7, QFont.Bold)
    painter.setFont(font_diag)
    painter.drawText(QRectF(diag_x, diag_y + 15, diag_w, 15), Qt.AlignCenter, f"Fita {esp_f}mm")
    fita_resumo = f"C1:{int(c1)} C2:{int(c2)} L1:{int(l1)} L2:{int(l2)}"
    painter.drawText(QRectF(diag_x, diag_y + 30, diag_w, 15), Qt.AlignCenter, fita_resumo)

    # Usinagens e Detalhes
    ops = part.get("operacoes", [])
    ops_desc = "Furações: Padrão TrazoMob" if not ops else f"Usinagens: {len(ops)} oper."
    painter.drawText(QRectF(135, 86, width_px - 145, 16), Qt.AlignLeft, f"⚙️ {ops_desc}")

    qtd = part.get("quantidade", 1)
    font_qtd = QFont("Arial", 9, QFont.Bold)
    painter.setFont(font_qtd)
    painter.setPen(QColor("#16A34A"))
    painter.drawText(QRectF(135, 108, width_px - 145, 18), Qt.AlignLeft, f"Quantidade: {qtd}x")

    # Rodapé: Code 128 real (esquerda) + QR Code (direita), carga estável
    payload = label_payload(part)
    qr_lado = 56
    rodape_topo = height_px - 62
    qr_rect = QRectF(width_px - 12 - qr_lado, rodape_topo + 2, qr_lado, qr_lado)
    bar_rect = QRectF(12, rodape_topo + 8, width_px - 24 - qr_lado - 10, 30)

    _draw_code128_barcode(painter, payload, bar_rect)

    # Código texto legível abaixo do código de barras
    font_code = QFont("Courier New", 7, QFont.Bold)
    painter.setFont(font_code)
    painter.setPen(QColor("#334155"))
    painter.drawText(QRectF(12, rodape_topo + 40, bar_rect.width(), 14), Qt.AlignCenter, payload)

    _draw_qr(painter, payload, qr_rect)

    painter.end()
    return pix


class ProductionLabelsDialog(QDialog):
    """Diálogo de visualização e impressão das etiquetas técnicas de produção da marcenaria."""

    def __init__(self, parts: List[dict[str, Any]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("🏷️ Etiquetas Técnicas de Produção & Fábrica — TrazoMob")
        self.resize(750, 600)
        self.parts = parts

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Barra superior com ações
        top_bar = QHBoxLayout()
        self.lbl_info = QLabel(f"<b>Total de Etiquetas:</b> {len(parts)} modelo(s) de peças")
        self.lbl_info.setStyleSheet("font-size: 12px; color: palette(text);")
        top_bar.addWidget(self.lbl_info)
        top_bar.addStretch()

        btn_export_all = QPushButton("💾 Salvar Todas as Etiquetas (PNG)")
        btn_export_all.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        btn_export_all.clicked.connect(self._export_all_labels)
        top_bar.addWidget(btn_export_all)

        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(self.accept)
        top_bar.addWidget(btn_close)
        layout.addLayout(top_bar)

        # Scroll com a grade de etiquetas
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.grid_layout = QVBoxLayout(container)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.grid_layout.setSpacing(12)

        for p in parts:
            pix = render_label_pixmap(p)
            lbl_card = QLabel()
            lbl_card.setPixmap(pix)
            lbl_card.setAlignment(Qt.AlignCenter)
            self.grid_layout.addWidget(lbl_card)

        self.grid_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _export_all_labels(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta para Salvar as Etiquetas")
        if not folder:
            return
        saved = 0
        for i, p in enumerate(self.parts):
            # 3x de resolução para o Code 128 e o QR saírem nítidos na impressão
            pix = render_label_pixmap(p, scale=3.0)
            nome_clean = "".join(c if c.isalnum() or c in " _-" else "_" for c in p.get("nome", "peca"))
            filename = os.path.join(folder, f"Etiqueta_{i+1:02d}_{nome_clean}.png")
            pix.save(filename, "PNG")
            saved += 1
        QMessageBox.information(self, "Etiquetas Salvas", f"✅ {saved} etiqueta(s) gerada(s) e salvas com sucesso em:\n{folder}")
