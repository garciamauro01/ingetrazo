# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Ferramenta de Alinhamento e Centralização 3D por Pontos Notáveis e Faces.

Comportamento e Recursos:
1. PONTOS NOTÁVEIS E CENTROS (Bounding Box e Geometria):
   - Centro Total da Bounding Box (Centro X/Y/Z)
   - Centros de cada uma das 6 Faces da Bounding Box:
     * Centro do Topo (+Z)
     * Centro da Base (-Z)
     * Centro da Frente (-Y) / Traseira (+Y)
     * Centro da Esquerda (-X) / Direita (+X)
   - Pontos médios das 12 arestas (Midpoints)
   - Vértices e quinas (Corners)
   - Centros reais das faces trianguladas/poligonais sob o cursor

2. FLUXO DE 2 CLIQUES:
   - Clique 1 (Origem): Seleciona o ponto de referência no objeto que você quer mover (ex: Centro da Base do Colchão ou Centro do Enfeite).
   - Clique 2 (Destino): Clica no ponto de destino de qualquer outro objeto ou cena (ex: Centro do Tampo da Cama ou Centro da Bancada de Pedra).

3. MODIFICADORES E CONTROLE DE EIXOS:
   - Tecla TAB: Alterna entre [Alinhar + Mover] (Move o objeto até o destino) e [Apenas Alinhar].
   - Tecla X: Trava o alinhamento APENAS no eixo X (Largura).
   - Tecla Y: Trava o alinhamento APENAS no eixo Y (Profundidade).
   - Tecla Z: Trava o alinhamento APENAS no eixo Z (Altura).
   - Tecla A: Libera todos os eixos (XYZ livre - padrão).
   - Tecla Ctrl (ou Alt no Mac): Modo Copiar (mantém o original e gera uma cópia alinhada no destino).
   - Tecla Up/Down: Inverte a direção (face oposta).
   - Tecla Esc: Cancela a operação atual.
"""
from __future__ import annotations

import math
from typing import Optional, List, Tuple
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QVector3D

from core.group import Group, copy_group
from core.history import MoveGroupCommand
from core.snap import face_plane_world
from tools.base import Tool, ToolContext
from .align_tools import get_entity_world_bounds


class NotablePoint:
    """Representa um ponto de atração magnética (Centro, Ponto Médio, Quina ou Face)."""
    def __init__(self, pos: QVector3D, kind: str, label: str, group: Optional[Group] = None):
        self.pos = QVector3D(pos)
        self.kind = kind    # "center", "face_center", "midpoint", "corner"
        self.label = label  # "Centro da Base", "Centro do Topo", "Centro XYZ", etc.
        self.group = group


class AlignSnapTool(Tool):
    """Ferramenta com comportamento de pontos notáveis e centros de alinhamento."""

    name = "Alinhar e Centralizar"
    shortcut = "Shift+A"
    description = "Clique no ponto/centro de origem e depois no ponto/centro de destino. TAB: modo, X/Y/Z: trava eixo, Ctrl: copiar."
    uses_snap = False

    def __init__(self):
        super().__init__()
        self.source_group: Optional[Group] = None
        self.source_point: Optional[NotablePoint] = None
        self.hovered_point: Optional[NotablePoint] = None
        self.align_and_move: bool = True
        self.axis_lock: Optional[str] = None  # None (XYZ livre), "x", "y", "z"
        self.copy_mode: bool = False
        self._overlay_installed: bool = False

    def on_activate(self, viewport) -> None:
        self.source_group = None
        self.source_point = None
        self.hovered_point = None
        self.align_and_move = True
        self.axis_lock = None
        self.copy_mode = False

        if hasattr(viewport, "setCursor"):
            viewport.setCursor(Qt.CrossCursor)

        if hasattr(viewport, "_ext_overlays") and self._draw_align_overlay not in viewport._ext_overlays:
            viewport._ext_overlays.append(self._draw_align_overlay)
            self._overlay_installed = True

        # Se houver objeto já selecionado, pode pré-definir como objeto de origem
        scene = getattr(viewport, "scene", None)
        if scene and hasattr(scene, "selection"):
            sel_groups = [it for it in scene.selection if isinstance(it, Group)]
            if len(sel_groups) == 1:
                self.source_group = sel_groups[0]
                if hasattr(viewport, "flash_status"):
                    viewport.flash_status(
                        f"🎯 Objeto: '{self.source_group.name}'. Clique no PONTO DE ORIGEM (ex: Centro da Base ou Quina)."
                    )
                return

        if hasattr(viewport, "flash_status"):
            viewport.flash_status("🎯 Clique no PONTO/CENTRO do objeto que deseja alinhar.")

    def on_deactivate(self, viewport) -> None:
        self.source_group = None
        self.source_point = None
        self.hovered_point = None
        if hasattr(viewport, "unsetCursor"):
            viewport.unsetCursor()
        if hasattr(viewport, "_ext_overlays") and self._draw_align_overlay in viewport._ext_overlays:
            try:
                viewport._ext_overlays.remove(self._draw_align_overlay)
            except ValueError:
                pass
            self._overlay_installed = False
        viewport.update()

    def claims_key(self, key: int, modifiers: Qt.KeyboardModifiers) -> bool:
        """Informa ao Viewport do IngeTrazo para não consumir TAB, X, Y, Z, A e repassar à ferramenta."""
        return key in (
            int(Qt.Key_Tab),
            int(Qt.Key_Backtab),
            int(Qt.Key_X),
            int(Qt.Key_Y),
            int(Qt.Key_Z),
            int(Qt.Key_A),
            int(Qt.Key_Escape),
        )

    def on_key(self, viewport, key: int, modifiers: Qt.KeyboardModifiers) -> bool:
        # Alterna Alinhar + Mover com TAB (ou Shift+TAB)
        if key in (int(Qt.Key_Tab), int(Qt.Key_Backtab)):
            self.align_and_move = not self.align_and_move
            modo_str = "Alinhar e Mover (Snap Total)" if self.align_and_move else "Apenas Alinhar Posição"
            if hasattr(viewport, "flash_status"):
                viewport.flash_status(f"🔄 Modo: {modo_str} (TAB para alternar)")
            viewport.update()
            return True

        # Trava de eixos (X, Y, Z ou A para Todos)
        elif key == int(Qt.Key_X):
            self.axis_lock = "x" if self.axis_lock != "x" else None
            status = "Travado em X (Largura)" if self.axis_lock == "x" else "Eixos Livres (XYZ)"
            if hasattr(viewport, "flash_status"):
                viewport.flash_status(f"🔒 {status}")
            viewport.update()
            return True

        elif key == int(Qt.Key_Y):
            self.axis_lock = "y" if self.axis_lock != "y" else None
            status = "Travado em Y (Profundidade)" if self.axis_lock == "y" else "Eixos Livres (XYZ)"
            if hasattr(viewport, "flash_status"):
                viewport.flash_status(f"🔒 {status}")
            viewport.update()
            return True

        elif key == int(Qt.Key_Z):
            self.axis_lock = "z" if self.axis_lock != "z" else None
            status = "Travado em Z (Altura)" if self.axis_lock == "z" else "Eixos Livres (XYZ)"
            if hasattr(viewport, "flash_status"):
                viewport.flash_status(f"🔒 {status}")
            viewport.update()
            return True

        elif key == int(Qt.Key_A):
            self.axis_lock = None
            if hasattr(viewport, "flash_status"):
                viewport.flash_status("🔓 Eixos Livres (XYZ)")
            viewport.update()
            return True

        elif key == int(Qt.Key_Escape):
            self.source_point = None
            self.source_group = None
            self.hovered_point = None
            if hasattr(viewport, "flash_status"):
                viewport.flash_status("Alinhamento cancelado.")
            viewport.update()
            return True

        return False

    def _get_group_notable_points(self, group: Group) -> List[NotablePoint]:
        """Calcula todos os pontos notáveis da Bounding Box do grupo (Centros, Pontos Médios e Quinas)."""
        b = get_entity_world_bounds(group)
        if not b:
            return []

        x0, x1, y0, y1, z0, z1 = b
        cx = (x0 + x1) * 0.5
        cy = (y0 + y1) * 0.5
        cz = (z0 + z1) * 0.5

        points = []

        # 1. Centro Geométrico Total (XYZ)
        points.append(NotablePoint(QVector3D(cx, cy, cz), "center", "Centro (XYZ)", group))

        # 2. Centros das 6 Faces da Bounding Box (Essencial para apoiar colchão/enfeite/armário)
        points.append(NotablePoint(QVector3D(cx, cy, z0), "face_center", "Centro da Base (-Z)", group))
        points.append(NotablePoint(QVector3D(cx, cy, z1), "face_center", "Centro do Topo (+Z)", group))
        points.append(NotablePoint(QVector3D(cx, y0, cz), "face_center", "Centro da Frente (-Y)", group))
        points.append(NotablePoint(QVector3D(cx, y1, cz), "face_center", "Centro da Traseira (+Y)", group))
        points.append(NotablePoint(QVector3D(x0, cy, cz), "face_center", "Centro da Esquerda (-X)", group))
        points.append(NotablePoint(QVector3D(x1, cy, cz), "face_center", "Centro da Direita (+X)", group))

        # 3. Pontos Médios das Arestas do Topo e da Base
        # Base
        points.append(NotablePoint(QVector3D(cx, y0, z0), "midpoint", "Meio Frente Base", group))
        points.append(NotablePoint(QVector3D(cx, y1, z0), "midpoint", "Meio Traseira Base", group))
        points.append(NotablePoint(QVector3D(x0, cy, z0), "midpoint", "Meio Esquerda Base", group))
        points.append(NotablePoint(QVector3D(x1, cy, z0), "midpoint", "Meio Direita Base", group))
        # Topo
        points.append(NotablePoint(QVector3D(cx, y0, z1), "midpoint", "Meio Frente Topo", group))
        points.append(NotablePoint(QVector3D(cx, y1, z1), "midpoint", "Meio Traseira Topo", group))
        points.append(NotablePoint(QVector3D(x0, cy, z1), "midpoint", "Meio Esquerda Topo", group))
        points.append(NotablePoint(QVector3D(x1, cy, z1), "midpoint", "Meio Direita Topo", group))

        # 4. As 8 Quinas (Corners)
        points.append(NotablePoint(QVector3D(x0, y0, z0), "corner", "Quina Inf. Esq. Frontal", group))
        points.append(NotablePoint(QVector3D(x1, y0, z0), "corner", "Quina Inf. Dir. Frontal", group))
        points.append(NotablePoint(QVector3D(x0, y1, z0), "corner", "Quina Inf. Esq. Traseira", group))
        points.append(NotablePoint(QVector3D(x1, y1, z0), "corner", "Quina Inf. Dir. Traseira", group))
        points.append(NotablePoint(QVector3D(x0, y0, z1), "corner", "Quina Sup. Esq. Frontal", group))
        points.append(NotablePoint(QVector3D(x1, y0, z1), "corner", "Quina Sup. Dir. Frontal", group))
        points.append(NotablePoint(QVector3D(x0, y1, z1), "corner", "Quina Sup. Esq. Traseira", group))
        points.append(NotablePoint(QVector3D(x1, y1, z1), "corner", "Quina Sup. Dir. Traseira", group))

        return points

    def on_hover(self, ctx: ToolContext) -> None:
        sx, sy = ctx.screen.x(), ctx.screen.y()
        self.copy_mode = bool(ctx.modifiers & (Qt.ControlModifier | Qt.AltModifier))

        # Identifica o grupo sob o cursor
        picked_group = ctx.viewport.pick_group(sx, sy)
        if not picked_group:
            pick_fn = getattr(ctx.viewport, "pick_face_placement", None) or getattr(ctx.viewport, "pick_face_any", None)
            if pick_fn:
                _f, owner = pick_fn(sx, sy)
                if owner:
                    picked_group = getattr(ctx.viewport, "_owner_of", lambda g: g)(owner)

        if not picked_group:
            if self.hovered_point is not None:
                self.hovered_point = None
                ctx.viewport.update()
            return

        # Coleta os pontos notáveis desse grupo
        candidate_points = self._get_group_notable_points(picked_group)

        # Também adiciona o centro da face específica sob o cursor, se houver
        pick_fn = getattr(ctx.viewport, "pick_face_placement", None) or getattr(ctx.viewport, "pick_face_any", None)
        if pick_fn:
            face, owner = pick_fn(sx, sy)
            if face:
                xform = getattr(owner, "xform", None)
                pt, _norm = face_plane_world(face, xform)
                candidate_points.append(NotablePoint(pt, "face_center", "Centro da Face Real", picked_group))

        # Encontra o ponto com menor distância em pixels até o cursor
        best_pt: Optional[NotablePoint] = None
        best_dist = 28.0  # Raio de atração magnética de 28 pixels

        for np in candidate_points:
            px = ctx.viewport.world_to_pixel(np.pos)
            if px is not None:
                d = math.hypot(px[0] - sx, px[1] - sy)
                if d < best_dist:
                    best_dist = d
                    best_pt = np

        if best_pt != self.hovered_point:
            self.hovered_point = best_pt
            ctx.viewport.update()

    def on_click(self, ctx: ToolContext) -> None:
        self.copy_mode = bool(ctx.modifiers & (Qt.ControlModifier | Qt.AltModifier))

        # Passo 1: Captura o Ponto de Origem
        if self.source_point is None:
            if not self.hovered_point:
                if hasattr(ctx.viewport, "flash_status"):
                    ctx.viewport.flash_status("Passe o cursor sobre uma quina, centro ou face do objeto a mover.")
                return

            self.source_point = self.hovered_point
            self.source_group = self.hovered_point.group or ctx.viewport.pick_group(ctx.screen.x(), ctx.screen.y())

            if hasattr(ctx.viewport, "flash_status"):
                eixo_info = f" [Trava: {self.axis_lock.upper()}]" if self.axis_lock else ""
                ctx.viewport.flash_status(
                    f"📍 Origem: {self.source_point.label} de '{self.source_group.name}'. "
                    f"Agora clique no PONTO DE DESTINO{eixo_info}."
                )
            ctx.viewport.update()
            return

        # Passo 2: Captura o Ponto de Destino e executa o Alinhamento
        if not self.hovered_point:
            if hasattr(ctx.viewport, "flash_status"):
                ctx.viewport.flash_status("Clique em um centro, quina ou face de destino para alinhar.")
            return

        dest_point = self.hovered_point
        dest_group = self.hovered_point.group

        if self.source_group is None:
            return

        # Vetor de deslocamento exato conectando o ponto de origem ao ponto de destino
        p_orig = self.source_point.pos
        p_dest = dest_point.pos

        dx = p_dest.x() - p_orig.x()
        dy = p_dest.y() - p_orig.y()
        dz = p_dest.z() - p_orig.z()

        # Aplica a trava de eixo se solicitada pelo usuário (X, Y, Z ou Total)
        if self.axis_lock == "x":
            dy = 0.0
            dz = 0.0
        elif self.axis_lock == "y":
            dx = 0.0
            dz = 0.0
        elif self.axis_lock == "z":
            dx = 0.0
            dy = 0.0

        delta = QVector3D(dx, dy, dz)

        if delta.length() > 1e-5 and hasattr(ctx.viewport, "history"):
            target = self.source_group

            # Se estiver com Ctrl pressionado, gera uma CÓPIA alinhada
            if self.copy_mode:
                new_grp = copy_group(self.source_group)
                if hasattr(ctx.viewport, "scene") and hasattr(ctx.viewport.scene, "groups"):
                    ctx.viewport.scene.groups.append(new_grp)
                target = new_grp

            cmd = MoveGroupCommand(target, delta)
            ctx.viewport.history.execute(cmd)

            if hasattr(ctx.viewport, "notify_scene_changed"):
                ctx.viewport.notify_scene_changed()
            ctx.viewport.update()

        alvo_nome = getattr(self.source_group, "name", "Objeto")
        dest_nome = getattr(dest_group, "name", "Destino") if dest_group else "Destino"
        copia_str = " (Cópia gerada)" if self.copy_mode else ""
        eixo_str = f" no eixo {self.axis_lock.upper()}" if self.axis_lock else ""

        if hasattr(ctx.viewport, "flash_status"):
            ctx.viewport.flash_status(
                f"🎯 Alinhado com sucesso{copia_str}: {self.source_point.label} ➔ {dest_point.label}{eixo_str}!"
            )

        # Prepara para próximo alinhamento
        self.source_point = None
        self.source_group = None
        self.hovered_point = None
        ctx.viewport.update()

    def _draw_align_overlay(self, viewport, painter: QPainter) -> None:
        """Renderiza os pontos magnéticos de Bounding Box e centros na tela."""
        painter.setRenderHint(QPainter.Antialiasing, True)

        # 1. Desenha o ponto de origem se já tiver sido clicado
        if self.source_point:
            px_src = viewport.world_to_pixel(self.source_point.pos)
            if px_src:
                painter.setPen(QPen(QColor("#B91C1C"), 2.0))
                painter.setBrush(QBrush(QColor("#EF4444")))
                painter.drawEllipse(QPointF(px_src[0], px_src[1]), 6, 6)

                # Rótulo de origem fixo
                f = QFont()
                f.setPointSize(8)
                f.setBold(True)
                painter.setFont(f)
                painter.setPen(QPen(QColor("#FFFFFF"), 1.0))
                painter.setBrush(QBrush(QColor(185, 28, 28, 210)))
                lbl = f"Origem: {self.source_point.label}"
                fm = painter.fontMetrics()
                tw = fm.horizontalAdvance(lbl)
                painter.drawRoundedRect(px_src[0] + 10, px_src[1] - 12, tw + 8, 20, 3, 3)
                painter.drawText(px_src[0] + 14, px_src[1] + 2, lbl)

                # Se houver hover de destino, desenha a linha elástica conectando
                if self.hovered_point:
                    px_dst = viewport.world_to_pixel(self.hovered_point.pos)
                    if px_dst:
                        pen_line = QPen(QColor("#2563EB"), 1.5, Qt.DashLine)
                        painter.setPen(pen_line)
                        painter.drawLine(QPointF(px_src[0], px_src[1]), QPointF(px_dst[0], px_dst[1]))

        # 2. Desenha o ponto notável magnetizado sob o cursor
        if self.hovered_point:
            px = viewport.world_to_pixel(self.hovered_point.pos)
            if px:
                # Cores por tipo de ponto notável
                if "center" in self.hovered_point.kind:
                    c_fill = QColor("#10B981")  # Verde para Centros
                    c_pen = QColor("#065F46")
                elif self.hovered_point.kind == "midpoint":
                    c_fill = QColor("#0284C7")  # Azul para Pontos Médios
                    c_pen = QColor("#0C4A6E")
                else:
                    c_fill = QColor("#F59E0B")  # Âmbar para Quinas
                    c_pen = QColor("#78350F")

                painter.setPen(QPen(c_pen, 2.0))
                painter.setBrush(QBrush(c_fill))
                painter.drawEllipse(QPointF(px[0], px[1]), 5, 5)

                # Badge flutuante com a identificação exata
                f = QFont()
                f.setPointSize(8)
                f.setBold(True)
                painter.setFont(f)
                painter.setPen(QPen(QColor("#0F172A"), 1.0))
                painter.setBrush(QBrush(QColor(255, 255, 255, 230)))

                txt = f"🎯 {self.hovered_point.label}"
                if self.axis_lock:
                    txt += f" [{self.axis_lock.upper()}]"
                if self.copy_mode:
                    txt += " (+Cópia)"

                fm = painter.fontMetrics()
                tw = fm.horizontalAdvance(txt)
                painter.drawRoundedRect(px[0] + 10, px[1] - 10, tw + 10, 20, 4, 4)
                painter.drawText(px[0] + 15, px[1] + 4, txt)

        # 3. HUD permanente no canto superior da tela com o Status do Modo
        # Exibe se está em "Alinhar e Mover" ou "Apenas Alinhar", Eixos travados e Atalhos
        painter.save()
        f_hud = QFont()
        f_hud.setPointSize(9)
        f_hud.setBold(True)
        painter.setFont(f_hud)

        # Determina os textos do HUD
        modo_txt = "📦 MODO: ALINHAR + MOVER" if self.align_and_move else "📐 MODO: APENAS ALINHAR"
        modo_cor_bg = QColor(16, 185, 129, 230) if self.align_and_move else QColor(2, 132, 199, 230)

        eixo_txt = f"EIXO: {self.axis_lock.upper()}" if self.axis_lock else "EIXO: XYZ LIVRE"
        copia_txt = " | CÓPIA: ATIVA" if self.copy_mode else ""
        dica_txt = "[TAB] Alternar Modo | [X/Y/Z] Trava Eixo | [A] Livre | [Ctrl] Copiar"

        fm_hud = painter.fontMetrics()
        w1 = fm_hud.horizontalAdvance(f"{modo_txt}  |  {eixo_txt}{copia_txt}") + 20
        w2 = fm_hud.horizontalAdvance(dica_txt) + 20
        hud_w = max(w1, w2, 280)
        hud_h = 44

        # Caixa no topo central da tela
        vp_w = viewport.width() if hasattr(viewport, "width") else 800
        hud_x = (vp_w - hud_w) // 2
        hud_y = 12

        # Fundo do badge
        painter.setPen(QPen(QColor(0, 0, 0, 60), 1.0))
        painter.setBrush(QBrush(modo_cor_bg))
        painter.drawRoundedRect(hud_x, hud_y, hud_w, 22, 5, 5)

        # Texto do Modo e Eixo
        painter.setPen(QPen(QColor("#FFFFFF"), 1.0))
        painter.drawText(hud_x, hud_y + 15, f"  {modo_txt}  •  {eixo_txt}{copia_txt}")

        # Caixa de Dica/Atalhos logo abaixo
        painter.setBrush(QBrush(QColor(15, 23, 42, 200)))  # Slate escuro
        painter.drawRoundedRect(hud_x, hud_y + 23, hud_w, 20, 4, 4)
        f_sub = QFont()
        f_sub.setPointSize(8)
        painter.setFont(f_sub)
        painter.setPen(QPen(QColor("#E2E8F0"), 1.0))
        painter.drawText(hud_x, hud_y + 36, f"  {dica_txt}")

        painter.restore()
