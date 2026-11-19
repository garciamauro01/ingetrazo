# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Diálogo 2D de Planta Baixa para desenho de paredes e geração 3D automática."""
from __future__ import annotations

import math
from typing import Optional, List, Tuple

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
    QRadioButton,
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



class MeasurementMixin:
    """Logica de medicao e aplicacao de cotas/dimensoes do canvas."""

    def _find_segment_for_dimension(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> Optional[int]:
        """Localiza qual parede é representada ou corre paralela a esses dois pontos cotados.

        A escolha é determinística: usa as paredes efetivamente cobertas pela cota
        e prefere a de maior sobreposição (sem percentual mínimo arbitrário).
        """
        chain = self.graph.resolve_dimension_chain(p1, p2)
        if not chain.spans:
            return None
        if chain.exact:
            return chain.seg_ids[0]

        L = chain.span_len

        def overlap(item: Tuple[int, float, float, float]) -> float:
            _sid, min_t, max_t, _sL = item
            return max(0.0, min(L, max_t) - max(0.0, min_t))

        best = max(chain.spans, key=lambda item: (overlap(item), -item[1]))
        return best[0] if overlap(best) > 1e-6 else None

    def _find_segments_along_dimension(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> List[Tuple[int, float, float, float]]:
        """Retorna as paredes colineares cobertas pelo vão de p1 a p2.

        Retorna lista ordenada de tuplas: (seg_id, min_t, max_t, comprimento_m).
        A seleção é geométrica (sobreposição real com o vão), não um percentual.
        """
        return list(self.graph.resolve_dimension_chain(p1, p2).spans)

    def _edit_custom_dimension_dialog(self, dim_id: int, is_new: bool = False) -> bool:
        """Abre diálogo para definir o novo valor da cota criada e redimensiona a parede correspondente.

        Se o usuário cancelar o diálogo e a cota for recém-criada (is_new=True), remove a cota.
        Retorna True se confirmado/aceito, False se cancelado.
        """
        dim = self.graph.dimensions.get(dim_id)
        if not dim:
            return False

        # Verifica se esta cota abrange exatamente uma cadeia de paredes.
        # Cotas parciais/desalinhadas ficam como referência e não deformam nada.
        chain = self.graph.resolve_dimension_chain(dim.p1, dim.p2)
        chain_segs = chain.spans if chain.is_constructive else []

        scale = bare_number_scale()
        u_name = model_unit()
        p = model_precision()
        cur_dim_m = dist_2d(dim.p1, dim.p2)

        if chain_segs:
            # Diálogo paramétrico para cota de parede (seja segmento único ou parede subdividida em cadeia)
            first_sid = chain_segs[0][0]
            last_sid = chain_segs[-1][0]

            # Nós extremos já resolvidos geometricamente pela cadeia
            node_start = chain.start_node_id
            node_end = chain.end_node_id

            na = self.graph.nodes.get(node_start)
            nb = self.graph.nodes.get(node_end)
            if not na or not nb:
                return False

            dx = nb.x - na.x
            dy = nb.y - na.y

            def describe_push_dir(vx: float, vy: float) -> str:
                parts = []
                if vy > 0.05:
                    parts.append("Cima / Norte ⬆")
                elif vy < -0.05:
                    parts.append("Baixo / Sul ⬇")
                if vx > 0.05:
                    parts.append("Direita / Leste ➡")
                elif vx < -0.05:
                    parts.append("Esquerda / Oeste ⬅")
                return " e ".join(parts) if parts else "Frente"

            desc_start_to_end = describe_push_dir(dx, dy)
            desc_end_to_start = describe_push_dir(-dx, -dy)

            dlg = QDialog(self)
            dlg.setWindowTitle("Definir Medida da Cota")
            dlg.setMinimumWidth(380)
            dlg_layout = QVBoxLayout(dlg)
            dlg_layout.setSpacing(12)

            lbl_header = QLabel(f"<b>Novo comprimento da cota ({u_name}):</b>", dlg)
            dlg_layout.addWidget(lbl_header)

            sp = QDoubleSpinBox(dlg)
            sp.setRange(0.01, 100000.0)
            sp.setDecimals(p)
            sp.setValue(round(cur_dim_m / scale, p))
            sp.setSingleStep(100.0 if u_name == "mm" else (10.0 if u_name == "cm" else 0.10))
            dlg_layout.addWidget(sp)

            is_partial = self.graph.dimension_has_partial_anchor(dim) and not chain.is_constructive
            chk_drive = QCheckBox("Ajustar geometria (cota construtiva)", dlg)
            chk_drive.setToolTip(
                "Marcado: altera as paredes para atingir a medida.\n"
                "Desmarcado: mantém a cota apenas como referência (anotação)."
            )
            chk_drive.setChecked(bool(dim.driving) and not is_partial)
            if is_partial:
                chk_drive.setEnabled(False)
                chk_drive.setChecked(False)
            dlg_layout.addWidget(chk_drive)

            if is_partial:
                lbl_note = QLabel(
                    "Esta cota mede um trecho interno da parede. Por segurança ela fica "
                    "como <b>referência</b> e não altera a geometria.",
                    dlg,
                )
                lbl_note.setWordWrap(True)
                dlg_layout.addWidget(lbl_note)

            grp_dir = QGroupBox("Sentido da Alteração (Qual ponta fica fixa?)", dlg)
            vbox_dir = QVBoxLayout(grp_dir)
            vbox_dir.setSpacing(8)

            rb_fix_start = QRadioButton(
                f"Fixar Início ({na.x:.2f}, {na.y:.2f})\n➜ Estender/Empurrar para {desc_start_to_end}",
                grp_dir
            )
            rb_fix_end = QRadioButton(
                f"Fixar Fim ({nb.x:.2f}, {nb.y:.2f})\n➜ Estender/Empurrar para {desc_end_to_start}",
                grp_dir
            )
            rb_auto = QRadioButton("Automático (Preservar paredes já cotadas)", grp_dir)

            rb_fix_start.setChecked(True)
            vbox_dir.addWidget(rb_fix_start)
            vbox_dir.addWidget(rb_fix_end)
            vbox_dir.addWidget(rb_auto)
            dlg_layout.addWidget(grp_dir)

            def _sync_drive_widgets(checked: bool) -> None:
                sp.setEnabled(checked)
                grp_dir.setEnabled(checked)

            chk_drive.toggled.connect(_sync_drive_widgets)
            _sync_drive_widgets(chk_drive.isChecked())

            btn_box = QHBoxLayout()
            btn_cancel = QPushButton("Cancelar", dlg)
            btn_ok = QPushButton("Aplicar", dlg)
            btn_ok.setDefault(True)
            btn_ok.setStyleSheet("background-color: #00E676; color: black; font-weight: bold; padding: 6px 14px;")
            btn_cancel.clicked.connect(dlg.reject)
            btn_ok.clicked.connect(dlg.accept)
            btn_box.addStretch()
            btn_box.addWidget(btn_cancel)
            btn_box.addWidget(btn_ok)
            dlg_layout.addLayout(btn_box)

            if dlg.exec() != QDialog.Accepted:
                if is_new:
                    self.graph.remove_dimension(dim_id)
                    if self._selected_dim_id == dim_id:
                        self._selected_dim_id = None
                    self.update()
                return False

            new_val_m = sp.value() * scale
            drive = chk_drive.isChecked()

            # Cota de anotação: nunca altera a geometria.
            if not drive:
                changed_flag = dim.driving
                if changed_flag:
                    self._save_history()
                dim.driving = False
                self.graph.sync_all_dimensions()
                self.update()
                return True

            if abs(new_val_m - cur_dim_m) <= 1e-4:
                if not dim.driving:
                    self._save_history()
                    dim.driving = True
                    self.update()
                return True

            # Determina a âncora e o segmento que absorve o delta conforme a escolha.
            if rb_fix_end.isChecked():
                target_sid = first_sid
                tseg = self.graph.segments[target_sid]
                anchor_nid = tseg.node_a_id if tseg.node_b_id == node_start else tseg.node_b_id
            elif rb_auto.isChecked():
                target_sid = last_sid
                anchor_nid = None
            else:
                target_sid = last_sid
                tseg = self.graph.segments[target_sid]
                anchor_nid = tseg.node_a_id if tseg.node_b_id == node_end else tseg.node_b_id

            target_seg = self.graph.segments[target_sid]
            cur_target_len = target_seg.length(self.graph)
            # O delta é absorvido pelo segmento do lado escolhido; o outro lado é âncora.
            target_new_len = cur_target_len + (new_val_m - cur_dim_m)

            conflict = self.graph.check_length_edit(
                target_sid, target_new_len, anchor_node_id=anchor_nid, ignore_dim_id=dim_id
            )
            if conflict:
                QMessageBox.warning(self, "Cota não aplicada", conflict)
                # Mantém a cota existente como referência, sem distorcer o modelo.
                if dim.driving:
                    self._save_history()
                    dim.driving = False
                    self.graph.sync_all_dimensions()
                    self.update()
                return True

            self._save_history()

            # Garante que os nós extremos da cota estejam vinculados formalmente
            # (nunca as duas pontas no mesmo nó).
            p1_is_start = dist_2d(dim.p1, (na.x, na.y)) <= dist_2d(dim.p2, (na.x, na.y))
            if node_start != node_end:
                dim.node_a_id = node_start if p1_is_start else node_end
                dim.node_b_id = node_end if p1_is_start else node_start

            ok = self.graph.set_segment_length(
                target_sid, target_new_len, anchor_node_id=anchor_nid,
                ignore_dim_id=dim_id, enforce_constraints=False,
            )
            if not ok:
                QMessageBox.warning(
                    self, "Cota não aplicada",
                    "Não foi possível aplicar essa medida sem distorcer o modelo.",
                )
                self.update()
                return True

            dim.driving = True
            self.wall_selected.emit(target_sid, target_new_len)

            self.update()
            return True

        # Caso contrário (cota livre isolada no vazio não alinhada a nenhuma parede)
        has_refs = any((
            dim.node_a_id, dim.node_b_id, dim.a_seg_id, dim.b_seg_id,
        ))
        if has_refs:
            # Cota vinculada a pontos da parede mas sem trecho construtivo reconhecido:
            # permanece como referência para não deformar a geometria.
            if dim.driving:
                self._save_history()
                dim.driving = False
                self.update()
            QMessageBox.information(
                self,
                "Cota de referência",
                "Esta cota está vinculada à geometria e não pode ser alterada "
                "diretamente sem deformar as paredes. Ela permanece como referência.",
            )
            return True

        cur_val_doc = cur_dim_m / scale
        val_doc, ok = QInputDialog.getDouble(
            self,
            "Definir Cota Livre",
            f"Comprimento desejado para esta cota ({u_name}):",
            value=round(cur_val_doc, p),
            minValue=0.01,
            maxValue=100000.0,
            decimals=p
        )
        if ok:
            val_m = val_doc * scale
            if abs(val_m - cur_dim_m) > 1e-4:
                self._save_history()
                dx = dim.p2[0] - dim.p1[0]
                dy = dim.p2[1] - dim.p1[1]
                L = math.hypot(dx, dy)
                if L > 1e-4:
                    ux, uy = dx / L, dy / L
                    dim.p2 = (dim.p1[0] + ux * val_m, dim.p1[1] + uy * val_m)
                self.update()
            return True
        else:
            if is_new:
                self.graph.remove_dimension(dim_id)
                if self._selected_dim_id == dim_id:
                    self._selected_dim_id = None
                self.update()
            return False

    def _edit_segment_length_dialog(self, seg_id: int, face_type: str = "centro", current_face_len: Optional[float] = None) -> bool:
        """Abre caixa de diálogo para digitar nova medida e escolher o sentido de expansão/ancoragem.

        Retorna True se confirmado/aceito, False se cancelado.
        """
        seg = self.graph.segments.get(seg_id)
        if not seg:
            return False

        scale = bare_number_scale()
        u_name = model_unit()
        p = model_precision()

        cur_center_m = seg.length(self.graph)
        cur_val_doc = cur_center_m / scale

        na = self.graph.nodes.get(seg.node_a_id)
        nb = self.graph.nodes.get(seg.node_b_id)
        if not na or not nb:
            return

        # Vetor do segmento de A para B no mundo (+X leste/direita, +Y norte/cima)
        dx = nb.x - na.x
        dy = nb.y - na.y

        def describe_push_dir(vx: float, vy: float) -> str:
            parts = []
            if vy > 0.05:
                parts.append("Cima / Norte ⬆")
            elif vy < -0.05:
                parts.append("Baixo / Sul ⬇")
            if vx > 0.05:
                parts.append("Direita / Leste ➡")
            elif vx < -0.05:
                parts.append("Esquerda / Oeste ⬅")
            return " e ".join(parts) if parts else "Frente"

        desc_a_to_b = describe_push_dir(dx, dy)
        desc_b_to_a = describe_push_dir(-dx, -dy)

        # Diálogo completo com escolha do sentido de alteração
        dlg = QDialog(self)
        dlg.setWindowTitle("Definir Medida da Parede")
        dlg.setMinimumWidth(380)
        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.setSpacing(12)

        lbl_header = QLabel(f"<b>Novo comprimento da parede ({u_name}):</b>", dlg)
        dlg_layout.addWidget(lbl_header)

        sp = QDoubleSpinBox(dlg)
        sp.setRange(0.01, 100000.0)
        sp.setDecimals(p)
        sp.setSingleStep(100.0 if u_name == "mm" else (10.0 if u_name == "cm" else 0.10))

        ref_box = QHBoxLayout()
        ref_box.addWidget(QLabel("Medida de referência:", dlg))
        cb_ref = QComboBox(dlg)
        cb_ref.addItem("Eixo central", "centro")
        cb_ref.addItem("Face esquerda (A ➜ B)", "left")
        cb_ref.addItem("Face direita (A ➜ B)", "right")
        cb_ref.setToolTip(
            "No eixo central, a medida é a linha entre os nós.\n"
            "Nas faces, a medida considera o corte em 45° dos cantos."
        )
        ref_box.addWidget(cb_ref, 1)
        dlg_layout.addLayout(ref_box)
        dlg_layout.addWidget(sp)

        def _reference_length(ref: str) -> float:
            if ref == "centro":
                return cur_center_m
            face_len = self.graph.segment_face_length(seg_id, ref)
            return face_len if face_len is not None else cur_center_m

        def _sync_spin_to_reference() -> None:
            sp.setValue(round(_reference_length(cb_ref.currentData()) / scale, p))

        if face_type in ("left", "right") and current_face_len is not None:
            cb_ref.setCurrentIndex(1 if face_type == "left" else 2)
            sp.setValue(round(current_face_len / scale, p))
        else:
            sp.setValue(round(cur_val_doc, p))
        cb_ref.currentIndexChanged.connect(_sync_spin_to_reference)

        # Grupo de escolha da direção / âncora fixa
        grp_dir = QGroupBox("Sentido da Alteração (Qual ponta fica fixa?)", dlg)
        vbox_dir = QVBoxLayout(grp_dir)
        vbox_dir.setSpacing(8)

        rb_fix_a = QRadioButton(
            f"Fixar Início ({na.x:.2f}, {na.y:.2f})\n➜ Estender/Empurrar para {desc_a_to_b}",
            grp_dir
        )
        rb_fix_b = QRadioButton(
            f"Fixar Fim ({nb.x:.2f}, {nb.y:.2f})\n➜ Estender/Empurrar para {desc_b_to_a}",
            grp_dir
        )
        rb_auto = QRadioButton("Automático (Preservar paredes já cotadas)", grp_dir)

        # Define opção padrão inteligente
        # Se um nó tem cota conectada e o outro não, seleciona a âncora correspondente por padrão
        dim_segs = {d.seg_id for d in self.graph.dimensions.values() if d.seg_id is not None and d.seg_id != seg_id}
        def has_dim(start_nid: int) -> bool:
            vis = {start_nid}
            q = [start_nid]
            while q:
                cur = q.pop(0)
                for sid, s in self.graph.segments.items():
                    if sid == seg_id:
                        continue
                    if s.node_a_id == cur or s.node_b_id == cur:
                        if sid in dim_segs:
                            return True
                        nxt = s.node_b_id if s.node_a_id == cur else s.node_a_id
                        if nxt not in vis:
                            vis.add(nxt)
                            q.append(nxt)
            return False

        has_a = has_dim(seg.node_a_id)
        has_b = has_dim(seg.node_b_id)

        if has_a and not has_b:
            rb_fix_a.setChecked(True)
        elif has_b and not has_a:
            rb_fix_b.setChecked(True)
        else:
            rb_fix_a.setChecked(True)

        vbox_dir.addWidget(rb_fix_a)
        vbox_dir.addWidget(rb_fix_b)
        vbox_dir.addWidget(rb_auto)
        dlg_layout.addWidget(grp_dir)

        # Botões de Ação
        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar", dlg)
        btn_ok = QPushButton("Aplicar", dlg)
        btn_ok.setDefault(True)
        btn_ok.setStyleSheet("background-color: #00E676; color: black; font-weight: bold; padding: 6px 14px;")
        btn_cancel.clicked.connect(dlg.reject)
        btn_ok.clicked.connect(dlg.accept)
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_ok)
        dlg_layout.addLayout(btn_box)

        if dlg.exec() != QDialog.Accepted:
            return False

        val_doc = sp.value()
        val_m = val_doc * scale

        ref = cb_ref.currentData()
        ref_len = _reference_length(ref)
        # Converte a medida digitada (eixo ou face) para o comprimento do eixo central.
        target_center = val_m + (cur_center_m - ref_len)

        if abs(target_center - cur_center_m) > 1e-4:
            anchor_nid = None
            if rb_fix_a.isChecked():
                anchor_nid = seg.node_a_id
            elif rb_fix_b.isChecked():
                anchor_nid = seg.node_b_id
            # Se rb_auto estiver marcado, anchor_nid fica None e a heurística de CAD cuida

            conflict = self.graph.check_length_edit(seg_id, target_center, anchor_node_id=anchor_nid)
            if conflict:
                QMessageBox.warning(self, "Medida não aplicada", conflict)
                return False

            self._save_history()
            ok = self.graph.set_segment_length(
                seg_id, target_center, anchor_node_id=anchor_nid, enforce_constraints=False
            )
            if not ok:
                QMessageBox.warning(
                    self, "Medida não aplicada",
                    "Não foi possível aplicar essa medida sem distorcer o modelo.",
                )
                return False
            self.wall_selected.emit(seg_id, self.graph.segments[seg_id].length(self.graph))
            self.update()
        return True

    def _apply_typed_length(self, length_m: float) -> None:
        """Aplica o comprimento digitado diretamente pelo teclado e confirma a parede."""
        if length_m <= 0.001:
            return

        # 1. Se houver uma parede selecionada, altera seu comprimento
        if self._selected_seg_id is not None:
            conflict = self.graph.check_length_edit(self._selected_seg_id, length_m)
            if conflict:
                QMessageBox.warning(self, "Medida não aplicada", conflict)
                return
            self._save_history()
            ok = self.graph.set_segment_length(
                self._selected_seg_id, length_m, enforce_constraints=False
            )
            if not ok:
                QMessageBox.warning(
                    self, "Medida não aplicada",
                    "Não foi possível aplicar essa medida sem distorcer o modelo.",
                )
                return
            self.wall_selected.emit(self._selected_seg_id, length_m)
            self.update()
            return

        # 2. Se estiver no meio de um traço (_start_pt ativo), cria o segmento na direção do mouse
        # 2. Se estiver posicionando o ponto de partida em T a partir de uma refer?ncia na parede
        if self._start_pt is None and self._t_ref_info is not None:
            ref_pt = self._t_ref_info["ref_pt"]
            u_dir = self._t_ref_info["u_dir"]
            fixed_x = ref_pt[0] + u_dir[0] * length_m
            fixed_y = ref_pt[1] + u_dir[1] * length_m

            # Subdivide imediatamente a parede existente no ponto do T
            self._save_history()
            split_nid = self.graph._get_or_split_at_point(fixed_x, fixed_y, threshold=0.10)
            split_node = self.graph.nodes[split_nid]
            start_coord = (split_node.x, split_node.y)

            # Fixa como in?cio da nova parede e abre a corda el?stica perpendicularmente
            self._start_pt = start_coord
            # Vetor perpendicular ? parede (normal para puxar o T a 90 graus)
            n_perp = (-u_dir[1], u_dir[0])
            self._current_mouse_world = (start_coord[0] + n_perp[0] * 1.0, start_coord[1] + n_perp[1] * 1.0)
            self._t_ref_info = None
            self.wall_count_changed.emit(len(self.graph.segments))
            self.update()
            return

        if self._start_pt is not None:
            p0 = self._start_pt
            p1 = self._current_mouse_world
            dx = p1[0] - p0[0]
            dy = p1[1] - p0[1]
            dist = math.hypot(dx, dy)
            if dist < 1e-4:
                dx, dy = 1.0, 0.0
                dist = 1.0
            ux, uy = dx / dist, dy / dist

            # 1. Se o usu?rio iniciou no canto/marcador da parede e digitou uma dist?ncia ao longo da parede existente
            # (Rastreamento de Ponto de Ramifica??o em T a partir de canto existente):
            start_nid = self.graph.find_node_at(p0[0], p0[1], threshold=0.20)
            colinear_seg = None
            if start_nid is not None:
                for sid, s in self.graph.segments.items():
                    if s.node_a_id == start_nid or s.node_b_id == start_nid:
                        other_id = s.node_b_id if s.node_a_id == start_nid else s.node_a_id
                        other_n = self.graph.nodes.get(other_id)
                        if not other_n:
                            continue
                        sdx = other_n.x - p0[0]
                        sdy = other_n.y - p0[1]
                        s_len = math.hypot(sdx, sdy)
                        if s_len > 1e-4:
                            dot = (sdx / s_len) * ux + (sdy / s_len) * uy
                            # Se o mouse est? apontando ao longo da parede existente e a dist?ncia digitada est? dentro dela
                            if dot > 0.90 and 0.01 < length_m < s_len:
                                colinear_seg = s
                                break

            if colinear_seg is not None:
                # O usu?rio quis posicionar o T a partir do canto digitando a dist?ncia!
                fixed_x = p0[0] + ux * length_m
                fixed_y = p0[1] + uy * length_m
                self._save_history()
                split_nid = self.graph._get_or_split_at_point(fixed_x, fixed_y, threshold=0.10)
                split_node = self.graph.nodes[split_nid]
                start_coord = (split_node.x, split_node.y)

                # Fixa _start_pt exatamente no ponto do T e abre a corda el?stica perpendicular ? parede existente!
                self._start_pt = start_coord
                n_perp = (-uy, ux)
                self._current_mouse_world = (start_coord[0] + n_perp[0] * 1.0, start_coord[1] + n_perp[1] * 1.0)
                self.wall_count_changed.emit(len(self.graph.segments))
                self.update()
                return

            ext = self.graph.get_start_extension(p0, (ux, uy))
            eff_len = length_m + ext
            end_x = p0[0] + ux * eff_len
            end_y = p0[1] + uy * eff_len

            self._save_history()
            self.graph.add_segment(p0[0], p0[1], end_x, end_y)
            self.graph.merge_close_nodes(threshold=0.25)
            self.wall_count_changed.emit(len(self.graph.segments))

            # Verifica se fechou um ciclo
            end_nid = self.graph.find_node_at(end_x, end_y, threshold=0.25)
            deg = 0
            if end_nid is not None:
                deg = sum(1 for s in self.graph.segments.values() if s.node_a_id == end_nid or s.node_b_id == end_nid)

            if deg >= 2:
                self._start_pt = None
            else:
                self._start_pt = (end_x, end_y)

            self.update()

