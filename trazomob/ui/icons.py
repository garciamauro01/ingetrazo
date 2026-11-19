# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Miniaturas e ícones vetoriais de alta definição para TrazoMob."""
from __future__ import annotations

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)


# Reexporta??o de compatibilidade retroativa para miniaturas de m?dulos
from ..ui.thumbnails import get_module_thumbnail, _THUMBNAIL_CACHE


def make_trazomob_icon():
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QPainterPath
    from PySide6.QtCore import Qt, QRectF
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    p.setBrush(QBrush(QColor("#1976D2")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(2, 2, 44, 44), 10, 10)

    p.setBrush(QBrush(QColor("#FFFFFF")))
    path = QPainterPath()
    path.addEllipse(QRectF(14, 18, 16, 16))
    path.addEllipse(QRectF(8, 22, 14, 12))
    path.addEllipse(QRectF(24, 21, 15, 13))
    path.addRect(QRectF(14, 25, 18, 9))
    p.drawPath(path)

    pen = QPen(QColor("#FFD54F"), 3.0)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    p.drawLine(10, 36, 38, 36)
    p.end()
    return QIcon(pm)


def make_align_tool_icon():
    """Ícone vetorial para a ferramenta Alinhar & Apoiar (snap magnético 3D)."""
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen
    from PySide6.QtCore import Qt, QRectF
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    # Fundo azul moderno
    p.setBrush(QBrush(QColor("#0284C7")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(2, 2, 44, 44), 10, 10)

    # Base / Objeto de referência (retângulo inferior cinza/branco)
    p.setBrush(QBrush(QColor("#E2E8F0")))
    p.setPen(QPen(QColor("#0F172A"), 1.5))
    p.drawRoundedRect(QRectF(8, 28, 32, 12), 3, 3)

    # Objeto apoiado / encaixado em cima (retângulo superior amarelo/âmbar)
    p.setBrush(QBrush(QColor("#F59E0B")))
    p.setPen(QPen(QColor("#78350F"), 1.5))
    p.drawRoundedRect(QRectF(14, 12, 20, 14), 3, 3)

    # Setas magnéticas indicando alinhamento e descida
    pen_arrow = QPen(QColor("#FFFFFF"), 2.0)
    pen_arrow.setCapStyle(Qt.RoundCap)
    p.setPen(pen_arrow)
    p.drawLine(24, 6, 24, 10)
    p.drawLine(22, 9, 24, 11)
    p.drawLine(26, 9, 24, 11)

    p.end()
    return QIcon(pm)


def make_cabinet_icon():
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen
    from PySide6.QtCore import Qt, QRectF
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    p.setBrush(QBrush(QColor("#D97706")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(2, 2, 44, 44), 10, 10)

    p.setBrush(QBrush(QColor("#FEF3C7")))
    p.setPen(QPen(QColor("#78350F"), 2.0))
    p.drawRoundedRect(QRectF(10, 10, 28, 28), 3, 3)

    p.drawLine(10, 19, 38, 19)
    p.setPen(QPen(QColor("#D97706"), 2.0))
    p.drawLine(20, 15, 28, 15)

    p.setPen(QPen(QColor("#78350F"), 2.0))
    p.drawLine(24, 19, 24, 38)
    p.setPen(QPen(QColor("#D97706"), 2.0))
    p.drawLine(22, 26, 22, 30)
    p.drawLine(26, 26, 26, 30)
    p.end()
    return QIcon(pm)


def make_cutlist_icon():
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen
    from PySide6.QtCore import Qt, QRectF
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    p.setBrush(QBrush(QColor("#059669")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(2, 2, 44, 44), 10, 10)

    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.setPen(QPen(QColor("#047857"), 2.0))
    p.drawRoundedRect(QRectF(11, 10, 26, 28), 3, 3)

    p.setPen(QPen(QColor("#059669"), 2.0))
    p.drawLine(16, 18, 32, 18)
    p.drawLine(16, 24, 32, 24)
    p.drawLine(16, 30, 28, 30)
    p.end()
    return QIcon(pm)


def make_interact_icon():
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen
    from PySide6.QtCore import Qt, QRectF
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    # Fundo circular/arredondado roxo/índigo
    p.setBrush(QBrush(QColor("#4F46E5")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(2, 2, 44, 44), 10, 10)

    # Mão com indicador apontando
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.setPen(QPen(QColor("#E0E7FF"), 1.5))
    # Dedo indicador
    p.drawRoundedRect(QRectF(21, 8, 7, 20), 3.5, 3.5)
    # Palma da mão
    p.drawRoundedRect(QRectF(15, 20, 19, 18), 5, 5)
    # Polegar
    p.drawRoundedRect(QRectF(10, 24, 8, 10), 3, 3)

    # Ondas de clique interativo acima do dedo
    p.setPen(QPen(QColor("#FDE047"), 2.0))
    p.drawArc(QRectF(14, 4, 20, 12), 30 * 16, 120 * 16)

    p.end()
    return QIcon(pm)


def make_rotate_ccw_icon():
    """Ícone vetorial de alta definição para rotação de 90° anti-horário (Esq)."""
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QPainterPath
    from PySide6.QtCore import Qt, QRectF
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    p.setBrush(QBrush(QColor("#0284C7")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(2, 2, 44, 44), 10, 10)

    pen = QPen(QColor("#FFFFFF"), 3.2)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawArc(QRectF(11, 13, 26, 26), 40 * 16, 250 * 16)

    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#FFFFFF")))
    path = QPainterPath()
    path.moveTo(11, 23)
    path.lineTo(19, 15)
    path.lineTo(19, 27)
    path.closeSubpath()
    p.drawPath(path)

    font = p.font()
    font.setPointSize(8)
    font.setBold(True)
    p.setFont(font)
    p.setPen(QColor("#BAE6FD"))
    p.drawText(QRectF(12, 17, 24, 18), Qt.AlignCenter, "90°")

    p.end()
    return QIcon(pm)


def make_rotate_cw_icon():
    """Ícone vetorial de alta definição para rotação de 90° horário (Dir)."""
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QPainterPath
    from PySide6.QtCore import Qt, QRectF
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    p.setBrush(QBrush(QColor("#0369A1")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(2, 2, 44, 44), 10, 10)

    pen = QPen(QColor("#FFFFFF"), 3.2)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawArc(QRectF(11, 13, 26, 26), -110 * 16, -250 * 16)

    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#FFFFFF")))
    path = QPainterPath()
    path.moveTo(37, 23)
    path.lineTo(29, 15)
    path.lineTo(29, 27)
    path.closeSubpath()
    p.drawPath(path)

    font = p.font()
    font.setPointSize(8)
    font.setBold(True)
    p.setFont(font)
    p.setPen(QColor("#BAE6FD"))
    p.drawText(QRectF(12, 17, 24, 18), Qt.AlignCenter, "90°")

    p.end()
    return QIcon(pm)


def make_style_palette_icon() -> QIcon:
    """Ícone vetorial de alta definição para Estilos de Visualização (Faces, Arestas, Raio-X)."""
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QPolygonF
    from PySide6.QtCore import Qt, QRectF, QPointF
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    # Fundo arredondado elegante em azul ardósia / ciano
    p.setBrush(QBrush(QColor("#3B82F6")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(2, 2, 44, 44), 10, 10)

    # Cubo isométrico 3D estilizado
    # Face superior
    top_poly = QPolygonF([QPointF(24, 10), QPointF(37, 17), QPointF(24, 24), QPointF(11, 17)])
    p.setBrush(QBrush(QColor("#EFF6FF")))
    p.setPen(QPen(QColor("#1D4ED8"), 1.5))
    p.drawPolygon(top_poly)

    # Face esquerda
    left_poly = QPolygonF([QPointF(11, 17), QPointF(24, 24), QPointF(24, 38), QPointF(11, 31)])
    p.setBrush(QBrush(QColor("#93C5FD")))
    p.drawPolygon(left_poly)

    # Face direita (sombreada)
    right_poly = QPolygonF([QPointF(24, 24), QPointF(37, 17), QPointF(37, 31), QPointF(24, 38)])
    p.setBrush(QBrush(QColor("#60A5FA")))
    p.drawPolygon(right_poly)

    # Arestas de destaque
    p.setPen(QPen(QColor("#FFFFFF"), 2.0))
    p.drawLine(24, 10, 24, 24)
    p.drawLine(11, 17, 24, 24)
    p.drawLine(37, 17, 24, 24)
    p.drawLine(24, 24, 24, 38)

    p.end()
    return QIcon(pm)



def make_perfil_diagram_pixmap(width: int = 140, height: int = 95, modelo: str = "gola") -> QPixmap:
    """Gera o diagrama técnico vetorial do puxador perfil de alumínio estilizado no padrão TrazoMob/Rometal."""
    from PySide6.QtGui import QPixmap, QPainter, QColor, QBrush, QPen, QPainterPath, QPolygonF
    from PySide6.QtCore import Qt, QPointF, QRectF

    pm = QPixmap(width, height)
    pm.fill(QColor("#E2E8F0"))  # Fundo suave cinza neutro
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    mod = (modelo or "gola").lower()

    # 1. Caixa do móvel superior em perspectiva
    p.setPen(QPen(QColor("#475569"), 1.2))
    p.setBrush(QBrush(QColor("#F8FAFC")))
    topo_path = QPainterPath()
    topo_path.moveTo(10, 40)
    topo_path.lineTo(55, 20)
    topo_path.lineTo(135, 35)
    topo_path.lineTo(90, 55)
    topo_path.closeSubpath()
    p.drawPath(topo_path)

    # Lateral esquerda da carcaça
    p.setBrush(QBrush(QColor("#F1F5F9")))
    lat_path = QPainterPath()
    lat_path.moveTo(10, 40)
    lat_path.lineTo(10, 90)
    lat_path.lineTo(25, 90)
    lat_path.lineTo(25, 48)
    lat_path.closeSubpath()
    p.drawPath(lat_path)

    # 2. Portas de MDF (com desconto no topo)
    p.setBrush(QBrush(QColor("#FFFFFF")))
    porta1 = QPainterPath()
    porta1.moveTo(25, 52)
    porta1.lineTo(25, 92)
    porta1.lineTo(75, 87)
    porta1.lineTo(75, 47)
    porta1.closeSubpath()
    p.drawPath(porta1)

    porta2 = QPainterPath()
    porta2.moveTo(78, 47)
    porta2.lineTo(78, 87)
    porta2.lineTo(128, 82)
    porta2.lineTo(128, 42)
    porta2.closeSubpath()
    p.drawPath(porta2)

    # Fresta entre portas
    p.setPen(QPen(QColor("#64748B"), 1.0))
    p.drawLine(QPointF(76.5, 47), QPointF(76.5, 87))

    # 3. Puxador Perfil de Alumínio de acordo com o modelo selecionado
    p.setPen(QPen(QColor("#334155"), 1.2))
    p.setBrush(QBrush(QColor("#CBD5E1")))  # Alumínio anodizado natural

    if "facetato" in mod or "aba" in mod:
        # RM-027: Aba Curva / Facetato
        # Perfil Porta 1
        pf1 = QPainterPath()
        pf1.moveTo(24, 45)
        pf1.lineTo(75, 40)
        pf1.lineTo(75, 49)
        pf1.lineTo(24, 54)
        pf1.closeSubpath()
        p.drawPath(pf1)
        # Gancho frontal curvado descendo
        p.setBrush(QBrush(QColor("#64748B")))
        g1 = QPainterPath()
        g1.moveTo(24, 52)
        g1.lineTo(75, 47)
        g1.lineTo(75, 53)
        g1.lineTo(24, 58)
        g1.closeSubpath()
        p.drawPath(g1)

        # Porta 2
        p.setBrush(QBrush(QColor("#CBD5E1")))
        pf2 = QPainterPath()
        pf2.moveTo(78, 40)
        pf2.lineTo(128, 35)
        pf2.lineTo(128, 44)
        pf2.lineTo(78, 49)
        pf2.closeSubpath()
        p.drawPath(pf2)
        p.setBrush(QBrush(QColor("#64748B")))
        g2 = QPainterPath()
        g2.moveTo(78, 47)
        g2.lineTo(128, 42)
        g2.lineTo(128, 48)
        g2.lineTo(78, 53)
        g2.closeSubpath()
        p.drawPath(g2)

    elif "canal" in mod or "perfil c" in mod or "canal_c" in mod:
        # RM-032: Perfil Central Duplo / Canal C
        # Porta 1 com duplo lábio
        pf1 = QPainterPath()
        pf1.moveTo(24, 43)
        pf1.lineTo(75, 38)
        pf1.lineTo(75, 50)
        pf1.lineTo(24, 55)
        pf1.closeSubpath()
        p.drawPath(pf1)
        # Rebaixo do canal central escuro
        p.setBrush(QBrush(QColor("#475569")))
        c1 = QPainterPath()
        c1.moveTo(24, 46)
        c1.lineTo(75, 41)
        c1.lineTo(75, 48)
        c1.lineTo(24, 53)
        c1.closeSubpath()
        p.drawPath(c1)

        # Porta 2
        p.setBrush(QBrush(QColor("#CBD5E1")))
        pf2 = QPainterPath()
        pf2.moveTo(78, 38)
        pf2.lineTo(128, 33)
        pf2.lineTo(128, 45)
        pf2.lineTo(78, 50)
        pf2.closeSubpath()
        p.drawPath(pf2)
        p.setBrush(QBrush(QColor("#475569")))
        c2 = QPainterPath()
        c2.moveTo(78, 41)
        c2.lineTo(128, 36)
        c2.lineTo(128, 43)
        c2.lineTo(78, 48)
        c2.closeSubpath()
        p.drawPath(c2)

    elif "sp7000" in mod or "haste" in mod:
        # SP-7000: Canal de abraço com Haste Reta Vertical
        # Encaixe no MDF
        pf1 = QPainterPath()
        pf1.moveTo(24, 48)
        pf1.lineTo(75, 43)
        pf1.lineTo(75, 52)
        pf1.lineTo(24, 57)
        pf1.closeSubpath()
        p.drawPath(pf1)
        # Haste reta se projetando para cima
        p.setBrush(QBrush(QColor("#94A3B8")))
        h1 = QPainterPath()
        h1.moveTo(24, 38)
        h1.lineTo(75, 33)
        h1.lineTo(75, 48)
        h1.lineTo(24, 53)
        h1.closeSubpath()
        p.drawPath(h1)

        # Porta 2
        p.setBrush(QBrush(QColor("#CBD5E1")))
        pf2 = QPainterPath()
        pf2.moveTo(78, 43)
        pf2.lineTo(128, 38)
        pf2.lineTo(128, 47)
        pf2.lineTo(78, 52)
        pf2.closeSubpath()
        p.drawPath(pf2)
        p.setBrush(QBrush(QColor("#94A3B8")))
        h2 = QPainterPath()
        h2.moveTo(78, 33)
        h2.lineTo(128, 28)
        h2.lineTo(128, 43)
        h2.lineTo(78, 48)
        h2.closeSubpath()
        p.drawPath(h2)

    else:
        # Padrão: RM-030 Gola Côncavo
        perfil1 = QPainterPath()
        perfil1.moveTo(25, 44)
        perfil1.lineTo(75, 39)
        perfil1.lineTo(75, 49)
        perfil1.quadTo(50, 44, 25, 54)
        perfil1.closeSubpath()
        p.drawPath(perfil1)

        # Aba frontal gola
        p.setBrush(QBrush(QColor("#94A3B8")))
        aba1 = QPainterPath()
        aba1.moveTo(25, 54)
        aba1.lineTo(75, 49)
        aba1.lineTo(75, 52)
        aba1.lineTo(25, 57)
        aba1.closeSubpath()
        p.drawPath(aba1)

        # Perfil Porta 2
        p.setBrush(QBrush(QColor("#CBD5E1")))
        perfil2 = QPainterPath()
        perfil2.moveTo(78, 39)
        perfil2.lineTo(128, 34)
        perfil2.lineTo(128, 44)
        perfil2.quadTo(103, 39, 78, 49)
        perfil2.closeSubpath()
        p.drawPath(perfil2)

        aba2 = QPainterPath()
        aba2.moveTo(78, 49)
        aba2.lineTo(128, 44)
        aba2.lineTo(128, 47)
        aba2.lineTo(78, 52)
        aba2.closeSubpath()
        p.drawPath(aba2)

    # 4. Setas vermelhas de cota / indicação apontando para a altura do perfil
    p.setPen(QPen(QColor("#7F1D1D"), 1.0))
    p.setBrush(QBrush(QColor("#EF4444")))

    # 3 barras de seta empilhadas
    p.drawRect(QRectF(44, 8, 12, 3))
    p.drawRect(QRectF(44, 13, 12, 3))
    p.drawRect(QRectF(44, 18, 12, 3))

    # Ponta da seta
    arrow = QPolygonF([
        QPointF(40, 23),
        QPointF(60, 23),
        QPointF(50, 36)
    ])
    p.drawPolygon(arrow)

    # Linha guia da cota
    p.setPen(QPen(QColor("#DC2626"), 1.2, Qt.DashLine))
    p.drawLine(QPointF(50, 36), QPointF(50, 46))

    p.end()
    return pm


def make_cut_plan_icon():
    """Ícone vetorial representando uma chapa de corte com peças e linhas de corte."""
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen
    from PySide6.QtCore import Qt, QRectF
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    # Fundo azul petróleo escuro
    p.setBrush(QBrush(QColor("#0f172a")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(2, 2, 44, 44), 8, 8)

    # Contorno da chapa de corte (retângulo com borda azul ciano)
    p.setBrush(QBrush(QColor("#1e293b")))
    p.setPen(QPen(QColor("#0ea5e9"), 1.5))
    p.drawRoundedRect(QRectF(6, 6, 36, 36), 3, 3)

    # Peça 1 (topo esquerdo) - Amarelo suave
    p.setBrush(QBrush(QColor("#f59e0b")))
    p.setPen(QPen(QColor("#0f172a"), 1.0))
    p.drawRect(QRectF(8, 8, 16, 20))

    # Peça 2 (topo direito) - Ciano suave
    p.setBrush(QBrush(QColor("#38bdf8")))
    p.drawRect(QRectF(25, 8, 15, 12))

    # Peça 3 (meio direito) - Verde suave
    p.setBrush(QBrush(QColor("#10b981")))
    p.drawRect(QRectF(25, 21, 15, 14))

    # Peça 4 (base) - Roxo suave
    p.setBrush(QBrush(QColor("#a855f7")))
    p.drawRect(QRectF(8, 29, 16, 11))

    # Sobra (canto inferior direito) - Hachurado / pontilhado
    p.setPen(QPen(QColor("#64748b"), 1.0, Qt.DotLine))
    p.setBrush(Qt.NoBrush)
    p.drawRect(QRectF(25, 36, 15, 4))

    p.end()
    return QIcon(pm)


def make_wall_icon() -> QIcon:
    """Ícone vetorial de alta definição representando uma parede sólida / tijolos com colunas."""
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen
    from PySide6.QtCore import Qt, QRectF
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    # Fundo âmbar suave / tijolo
    p.setBrush(QBrush(QColor("#78350F")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(2, 2, 44, 44), 8, 8)

    # Base da parede
    p.setBrush(QBrush(QColor("#B45309")))
    p.setPen(QPen(QColor("#451A03"), 1.2))
    p.drawRoundedRect(QRectF(6, 10, 36, 28), 3, 3)

    # Linhas de tijolo / junta
    p.setPen(QPen(QColor("#FEF3C7"), 1.2))
    # Horizontais
    p.drawLine(6, 17, 42, 17)
    p.drawLine(6, 24, 42, 24)
    p.drawLine(6, 31, 42, 31)

    # Verticais fileira 1
    p.drawLine(15, 10, 15, 17)
    p.drawLine(27, 10, 27, 17)
    p.drawLine(36, 10, 36, 17)

    # Verticais fileira 2
    p.drawLine(10, 17, 10, 24)
    p.drawLine(21, 17, 21, 24)
    p.drawLine(33, 17, 33, 24)

    # Verticais fileira 3
    p.drawLine(15, 24, 15, 31)
    p.drawLine(27, 24, 27, 31)
    p.drawLine(36, 24, 36, 31)

    # Verticais fileira 4
    p.drawLine(10, 31, 10, 38)
    p.drawLine(21, 31, 21, 38)
    p.drawLine(33, 31, 33, 38)

    # Borda destacada
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor("#FDE68A"), 1.5))
    p.drawRoundedRect(QRectF(6, 10, 36, 28), 3, 3)

    p.end()
    return QIcon(pm)


def make_ruler_icon() -> QIcon:
    """Ícone vetorial de alta definição para a régua de alturas e linhas-guia."""
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen
    from PySide6.QtCore import Qt, QRectF
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    # Fundo arredondado âmbar / dourado
    p.setBrush(QBrush(QColor("#D97706")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(2, 2, 44, 44), 10, 10)

    # Corpo da régua vertical em marfim
    p.setBrush(QBrush(QColor("#FFFBEB")))
    p.setPen(QPen(QColor("#78350F"), 1.5))
    p.drawRoundedRect(QRectF(14, 8, 20, 32), 2, 2)

    # Marcas e graduações da régua
    p.setPen(QPen(QColor("#B45309"), 1.5))
    for y, w in [(12, 10), (16, 6), (20, 8), (24, 12), (28, 6), (32, 8), (36, 10)]:
        p.drawLine(14, y, 14 + w, y)

    # Linha guia tracejada cruzando na horizontal
    p.setPen(QPen(QColor("#38BDF8"), 2.0, Qt.DashLine))
    p.drawLine(6, 24, 42, 24)

    p.end()
    return QIcon(pm)


def make_render_icon() -> QIcon:
    """Ícone vetorial de câmera fotográfica com brilho para Render Foto-Realista."""
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QPainterPath
    from PySide6.QtCore import Qt, QRectF
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    # Fundo arredondado elegante em roxo escuro / azul profundo
    p.setBrush(QBrush(QColor("#4338CA")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(2, 2, 44, 44), 10, 10)

    # Corpo da câmera fotográfica
    p.setBrush(QBrush(QColor("#F8FAFC")))
    p.setPen(QPen(QColor("#1E1B4B"), 1.5))
    p.drawRoundedRect(QRectF(10, 16, 28, 20), 4, 4)

    # Topo da câmera / flash
    p.drawRoundedRect(QRectF(14, 12, 10, 5), 2, 2)

    # Lente central
    p.setBrush(QBrush(QColor("#0284C7")))
    p.setPen(QPen(QColor("#38BDF8"), 2.0))
    p.drawEllipse(QRectF(18, 20, 12, 12))

    # Ponto de reflexo na lente
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QRectF(24, 22, 3, 3))

    p.end()
    return QIcon(pm)


def make_paint_icon() -> QIcon:
    """Ícone vetorial de rolo de pintura / paleta de tintas para paredes."""
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen
    from PySide6.QtCore import Qt, QRectF
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    # Fundo arredondado em verde esmeralda / turquesa suave
    p.setBrush(QBrush(QColor("#0D9488")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(2, 2, 44, 44), 10, 10)

    # Rolo de pintura (cilindro horizontal amarelo/âmbar)
    p.setBrush(QBrush(QColor("#F59E0B")))
    p.setPen(QPen(QColor("#B45309"), 1.2))
    p.drawRoundedRect(QRectF(10, 10, 24, 12), 3, 3)

    # Haste metálica do rolo
    p.setBrush(Qt.NoBrush)
    pen_arm = QPen(QColor("#E2E8F0"), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen_arm)
    p.drawLine(34, 16, 38, 16)
    p.drawLine(38, 16, 38, 28)
    p.drawLine(38, 28, 24, 28)
    p.drawLine(24, 28, 24, 34)

    # Cabo de madeira / plástico do rolo
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#334155")))
    p.drawRoundedRect(QRectF(22, 34, 4, 10), 1.5, 1.5)

    p.end()
    return QIcon(pm)


def make_emoji_icon(emoji: str) -> QIcon:
    """Gera um QIcon a partir de um caractere emoji ou texto."""
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QFont
    from PySide6.QtCore import Qt, QRectF
    pm = QPixmap(32, 32)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    font = QFont("Segoe UI Emoji", 18)
    p.setFont(font)
    p.drawText(QRectF(0, 0, 32, 32), Qt.AlignCenter, emoji)
    p.end()
    return QIcon(pm)


def make_light_icon():
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QPolygonF
    from PySide6.QtCore import Qt, QRectF, QPointF
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    p.setBrush(QBrush(QColor('#1E293B')))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(2, 2, 44, 44), 10, 10)

    cone = QPolygonF([QPointF(24, 18), QPointF(8, 42), QPointF(40, 42)])
    p.setBrush(QBrush(QColor(250, 204, 21, 120)))
    p.setPen(Qt.NoPen)
    p.drawPolygon(cone)

    p.setBrush(QBrush(QColor('#FDE047')))
    p.setPen(QPen(QColor('#EAB308'), 1.5))
    p.drawEllipse(QRectF(17, 8, 14, 14))

    p.setBrush(QBrush(QColor('#94A3B8')))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(20, 5, 8, 5), 1, 1)

    p.setBrush(QBrush(QColor('#FFFFFF')))
    p.drawEllipse(QRectF(21, 12, 6, 6))

    p.end()
    return QIcon(pm)


def make_magnet_snap_icon() -> QIcon:
    """Ícone estilizado representando atração e snap magnético (ímã 3D)."""
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QPainterPath
    from PySide6.QtCore import Qt, QRectF
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#0F172A")))
    p.drawRoundedRect(QRectF(2, 2, 44, 44), 10, 10)

    # Ferradura do ímã (U invertido)
    path = QPainterPath()
    path.moveTo(14, 34)
    path.lineTo(14, 21)
    path.arcTo(QRectF(14, 11, 20, 20), 180, -180)
    path.lineTo(34, 34)

    pen_magnet = QPen(QColor("#EF4444"), 5.0)
    pen_magnet.setCapStyle(Qt.FlatCap)
    p.setPen(pen_magnet)
    p.drawPath(path)

    # Polos metálicos prateados
    pen_tips = QPen(QColor("#E2E8F0"), 5.0)
    pen_tips.setCapStyle(Qt.FlatCap)
    p.setPen(pen_tips)
    p.drawLine(14, 29, 14, 35)
    p.drawLine(34, 29, 34, 35)

    # Centelha magnética no centro
    pen_spark = QPen(QColor("#38BDF8"), 2.0)
    pen_spark.setCapStyle(Qt.RoundCap)
    p.setPen(pen_spark)
    p.drawLine(20, 32, 28, 32)

    p.end()
    return QIcon(pm)


def make_pbr_material_icon() -> QIcon:
    """Ícone vetorial de esfera de materiais PBR com reflexo especular e paleta de acabamentos."""
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QRadialGradient
    from PySide6.QtCore import Qt, QRectF, QPointF
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    p.setBrush(QBrush(QColor("#0F172A")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(2, 2, 44, 44), 10, 10)

    grad = QRadialGradient(QPointF(20, 18), 16)
    grad.setColorAt(0.0, QColor("#FFFFFF"))
    grad.setColorAt(0.25, QColor("#38BDF8"))
    grad.setColorAt(0.7, QColor("#0284C7"))
    grad.setColorAt(1.0, QColor("#0369A1"))

    p.setBrush(QBrush(grad))
    p.setPen(QPen(QColor("#7DD3FC"), 1.0))
    p.drawEllipse(QRectF(10, 10, 26, 26))

    p.setBrush(QBrush(QColor(255, 255, 255, 220)))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QRectF(16, 14, 6, 4))

    p.setBrush(QBrush(QColor("#F59E0B")))
    p.setPen(QPen(QColor("#FFFFFF"), 1.2))
    p.drawEllipse(QRectF(28, 28, 14, 14))

    p.setBrush(QBrush(QColor("#EF4444")))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QRectF(32, 32, 6, 6))

    p.end()
    return QIcon(pm)


def make_free_zoom_icon() -> QIcon:
    """Ícone vetorial para a ferramenta Zoom Livre / Atravessar Sólidos (Estilo SketchUp)."""
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QPolygonF
    from PySide6.QtCore import Qt, QRectF, QPointF
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    # Fundo azul petróleo escuro arredondado
    p.setBrush(QBrush(QColor("#0F766E")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(2, 2, 44, 44), 10, 10)

    # Cubo/parede representativo (sólido) em perspectiva
    p.setBrush(QBrush(QColor("#14B8A6")))
    p.setPen(QPen(QColor("#042F2E"), 1.5))
    poly_front = QPolygonF([
        QPointF(16, 20), QPointF(32, 20),
        QPointF(32, 36), QPointF(16, 36)
    ])
    p.drawPolygon(poly_front)

    poly_top = QPolygonF([
        QPointF(16, 20), QPointF(24, 12),
        QPointF(40, 12), QPointF(32, 20)
    ])
    p.setBrush(QBrush(QColor("#5EEAD4")))
    p.drawPolygon(poly_top)

    poly_right = QPolygonF([
        QPointF(32, 20), QPointF(40, 12),
        QPointF(40, 28), QPointF(32, 36)
    ])
    p.setBrush(QBrush(QColor("#0D9488")))
    p.drawPolygon(poly_right)

    # Seta vermelha / dourada atravessando o sólido de fora a fora
    pen_arrow = QPen(QColor("#FBBF24"), 3.0)
    pen_arrow.setCapStyle(Qt.RoundCap)
    p.setPen(pen_arrow)
    p.drawLine(8, 28, 22, 28)
    p.drawLine(26, 28, 42, 28)

    # Ponta da seta à direita ultrapassando o cubo
    p.setBrush(QBrush(QColor("#FBBF24")))
    arrow_head = QPolygonF([
        QPointF(44, 28), QPointF(37, 24), QPointF(37, 32)
    ])
    p.drawPolygon(arrow_head)

    p.end()
    return QIcon(pm)





def make_engine_icon() -> QIcon:
    """Ícone de energia (liga/desliga) para o interruptor geral do TrazoMob."""
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush
    from PySide6.QtCore import Qt, QRectF, QPointF

    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    # Fundo grafite arredondado
    p.setBrush(QBrush(QColor("#111827")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(2, 2, 44, 44), 10, 10)

    # Anel de energia
    pen = QPen(QColor("#22C55E"), 3.4)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawArc(QRectF(11, 11, 26, 26), 55 * 16, 250 * 16)

    # Haste central
    p.drawLine(QPointF(24, 8), QPointF(24, 23))

    p.end()
    return QIcon(pm)
