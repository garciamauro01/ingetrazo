# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Diálogo de Planta Baixa 2D Interativa para Paredes."""
from __future__ import annotations

import logging
import math
from typing import Optional, List, Dict, Tuple, Any

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QFont, QKeyEvent, QVector3D
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QDoubleSpinBox,
    QSpinBox,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QMessageBox,
    QFrame,
    QSplitter,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QButtonGroup,
    QSlider,
    QFileDialog,
)

from core.group import Group
from core.history import SnapshotImport
from core.image_plane import ImagePlane

from ..wall.floorplan_canvas import WallFloorplanCanvas
from ..wall.plan_2d import WallGraph2D, WallNode2D, dist_2d
from ..wall.mesh_builder import WallMeshBuilder
from core.units import format_length, model_unit, model_precision, bare_number_scale


logger = logging.getLogger("trazomob.wall_floorplan_dialog")


class WallFloorplanDialog(QDialog):
    """Janela de Diálogo para Desenhar Paredes em Planta Baixa 2D com Extrusão 3D Direta."""

    def __init__(self, viewport, existing_group: Optional[Group] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.viewport = viewport
        self.existing_group = existing_group
        self.setWindowTitle("Planta Baixa 2D — Construtor de Paredes (TrazoMob)")
        self.resize(1000, 680)

        # Dicionários de grafos e paredes organizados por pavimento
        self._graphs_by_pav: Dict[str, WallGraph2D] = {}
        self._scene_walls_by_pav: Dict[str, List[Group]] = {}
        self.existing_walls = []
        self._current_pav = "Térreo"

        # Identifica pavimento inicial
        if self.existing_group is not None and isinstance(getattr(self.existing_group, "ext", None), dict):
            grp_pav = (
                self.existing_group.ext.get("pavimento")
                or self.existing_group.ext.get("trazomob_wall", {}).get("pavimento")
            )
            if grp_pav:
                self._current_pav = str(grp_pav).strip()

        if self.viewport is not None and hasattr(self.viewport, "scene"):
            all_scene_walls = [
                g for g in getattr(self.viewport.scene, "groups", [])
                if isinstance(getattr(g, "ext", None), dict) and g.ext.get("trazomob_wall")
            ]
            for g in all_scene_walls:
                p_nome = (
                    g.ext.get("pavimento")
                    or g.ext.get("trazomob_wall", {}).get("pavimento")
                    or "Térreo"
                ).strip()
                if p_nome not in self._scene_walls_by_pav:
                    self._scene_walls_by_pav[p_nome] = []
                self._scene_walls_by_pav[p_nome].append(g)

            # Reconstrói grafo por pavimento
            for p_nome, p_walls in self._scene_walls_by_pav.items():
                p_graph = None
                for g in p_walls:
                    w_data = g.ext["trazomob_wall"]
                    if isinstance(w_data.get("graph_2d"), dict):
                        # Reconcilia todos os grupos de uma vez mais abaixo;
                        # from_group() ancoraria os nós num único segmento.
                        p_graph = WallGraph2D.from_dict(w_data["graph_2d"])
                        break
                if p_graph is None:
                    # Paredes sem grafo salvo: os padrões vêm dos metadados
                    # do próprio grupo, não dos valores fixos de um projeto novo.
                    for g in p_walls:
                        w_data = g.ext["trazomob_wall"]
                        if len(w_data.get("pontos", [])) >= 2:
                            p_graph = WallGraph2D(
                                default_thickness=w_data.get("espessura", 0.15),
                                default_height=w_data.get("altura", 2.60),
                            )
                            break
                if p_graph is None:
                    p_graph = WallGraph2D(default_thickness=0.15, default_height=2.60)
                for g in p_walls:
                    w_data = g.ext["trazomob_wall"]
                    if "graph_2d" not in w_data:
                        pts = w_data.get("pontos", [])
                        th = w_data.get("espessura", 0.15)
                        alturas = w_data.get("alturas", [])
                        n = len(pts)
                        n_segs = n if w_data.get("is_closed", False) else max(0, n - 1)
                        for i in range(n_segs):
                            seg_h = float(alturas[i]) if i < len(alturas) else float(w_data.get("altura", 2.60))
                            p1, p2 = pts[i], pts[(i + 1) % n]
                            p_graph.add_segment(
                                p1[0], p1[1], p2[0], p2[1],
                                thickness=th, height=seg_h,
                            )
                        p_graph.reconcile_with_3d_groups([g])
                p_graph.reconcile_with_3d_groups(p_walls)
                p_graph.merge_close_nodes(threshold=0.25)
                p_graph.cleanup_isolated_nodes()
                self._graphs_by_pav[p_nome] = p_graph

            if self.existing_group is None and all_scene_walls:
                # Se não especificou grupo, seleciona o primeiro do pavimento ativo
                cur_walls = self._scene_walls_by_pav.get(self._current_pav, all_scene_walls)
                self.existing_group = cur_walls[0] if cur_walls else all_scene_walls[0]

        elif self.existing_group is not None:
            loaded_graph = WallGraph2D.from_group(self.existing_group)
            loaded_graph.cleanup_isolated_nodes()
            self._graphs_by_pav[self._current_pav] = loaded_graph
            self._scene_walls_by_pav[self._current_pav] = [self.existing_group]

        if self._current_pav in self._graphs_by_pav:
            self.graph = self._graphs_by_pav[self._current_pav]
            self.existing_walls = self._scene_walls_by_pav.get(self._current_pav, [])
        else:
            self.graph = WallGraph2D(default_thickness=0.15, default_height=2.60)
            self._graphs_by_pav[self._current_pav] = self.graph
            self.existing_walls = []

        self._setup_ui()
        scale = bare_number_scale()
        p = model_precision()
        # Bloqueia os sinais: o valor inicial é só a leitura do grafo salvo, não
        # uma alteração do usuário. Sem isso, _on_params_changed propagaria o
        # pé-direito padrão a todas as paredes e apagaria alturas por segmento.
        self.sp_thickness.blockSignals(True)
        self.sp_thickness.setValue(round(self.graph.default_thickness / scale, p))
        self.sp_thickness.blockSignals(False)
        self.sp_height.blockSignals(True)
        self.sp_height.setValue(round(self.graph.default_height / scale, p))
        self.sp_height.blockSignals(False)
        if self.graph.segments:
            self.lbl_status.setText(f"Paredes carregadas: {len(self.graph.segments)}")

        self._update_underlay_for_pav(self._current_pav)

        # Restaura imagem de referência previamente salva no documento se houver
        self._restore_reference_image_from_scene()

        # Guarda o snapshot inicial para detecção de alterações pendentes
        self._initial_graph_dict = self.graph.to_dict()

    def has_unsaved_changes(self) -> bool:
        """Verifica se houve alterações no traçado de paredes em relação ao início."""
        return self.graph.to_dict() != self._initial_graph_dict

    def _setup_ui(self) -> None:
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Canvas 2D
        self.canvas = WallFloorplanCanvas(self.graph, parent=self)
        self.canvas.wall_count_changed.connect(self._on_wall_count_changed)
        self.canvas.wall_selected.connect(self._on_wall_selected)
        self.canvas.current_length_changed.connect(self._on_current_length_changed)
        self.canvas.point_edit_hint.connect(self._on_point_edit_hint)

        # 2. Painel Lateral de Controle dentro de QScrollArea (evita esticar para fora da tela)
        side_container = QFrame(self)
        side_container.setFixedWidth(295)
        side_container_layout = QVBoxLayout(side_container)
        side_container_layout.setContentsMargins(0, 0, 0, 0)
        side_container_layout.setSpacing(0)

        scroll_area = QScrollArea(side_container)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #1e222b;
                border-left: 1px solid #2e3544;
            }
            QScrollBar:vertical {
                background: #181c24;
                width: 8px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #3e4a63;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #00b0ff;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        side_panel = QFrame()
        side_panel.setStyleSheet("""
            QFrame {
                background-color: #1e222b;
                border: none;
                color: #e0e0e0;
            }
            QLabel {
                font-weight: bold;
                font-size: 11px;
                color: #9aa4b2;
            }
            QDoubleSpinBox {
                background-color: #13171f;
                border: 1px solid #363f52;
                border-radius: 4px;
                color: #ffffff;
                padding: 4px 6px;
                font-weight: bold;
            }
            QPushButton {
                background-color: #2b3345;
                border: 1px solid #3e4a63;
                border-radius: 4px;
                color: #ffffff;
                padding: 6px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #38435c;
            }
            QPushButton:checked {
                background-color: #00b0ff;
                border: 1px solid #40c4ff;
                color: #000000;
            }
            QPushButton.tool-btn {
                font-size: 16px;
                padding: 6px 0px;
                min-width: 44px;
                min-height: 36px;
            }
            QGroupBox {
                border: 1px solid #2e3544;
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 10px;
                font-weight: bold;
                color: #40c4ff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
        """)

        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(12, 14, 12, 14)
        side_layout.setSpacing(9)

        # Título
        title_lbl = QLabel("📐 Parâmetros da Parede", side_panel)
        title_lbl.setStyleSheet("font-size: 14px; color: #ffffff;")
        side_layout.addWidget(title_lbl)

        # Ferramentas de desenho e seleção (ícones compactos com hint/tooltip)
        tool_box = QHBoxLayout()
        tool_box.setSpacing(6)

        self.btn_tool_line = QPushButton("📏", side_panel)
        self.btn_tool_line.setProperty("class", "tool-btn")
        self.btn_tool_line.setCheckable(True)
        self.btn_tool_line.setChecked(True)
        self.btn_tool_line.setToolTip("Desenhar Parede contínua (Linha por linha)")
        self.btn_tool_line.clicked.connect(lambda: self._set_mode("linha"))

        self.btn_tool_rect = QPushButton("🔲", side_panel)
        self.btn_tool_rect.setProperty("class", "tool-btn")
        self.btn_tool_rect.setCheckable(True)
        self.btn_tool_rect.setToolTip("Desenhar Cômodo Retangular fechado")
        self.btn_tool_rect.clicked.connect(lambda: self._set_mode("retangulo"))

        self.btn_tool_select = QPushButton("👆", side_panel)
        self.btn_tool_select.setProperty("class", "tool-btn")
        self.btn_tool_select.setCheckable(True)
        self.btn_tool_select.setToolTip("Selecionar ou mover paredes e nós")
        self.btn_tool_select.clicked.connect(lambda: self._set_mode("selecionar"))

        self.btn_tool_cota = QPushButton("📐", side_panel)
        self.btn_tool_cota.setProperty("class", "tool-btn")
        self.btn_tool_cota.setCheckable(True)
        self.btn_tool_cota.setToolTip("Adicionar Cota entre dois pontos quaisquer (faces, cantos ou centros)")
        self.btn_tool_cota.clicked.connect(lambda: self._set_mode("cota"))

        self.btn_tool_ponto = QPushButton("📍", side_panel)
        self.btn_tool_ponto.setProperty("class", "tool-btn")
        self.btn_tool_ponto.setCheckable(True)
        self.btn_tool_ponto.setToolTip(
            "Adicionar/remover pontos: clique na parede para dividir em dois trechos; "
            "clique num ponto interno colinear para uni-los em uma parede única"
        )
        self.btn_tool_ponto.clicked.connect(lambda: self._set_mode("pontos"))

        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.btn_tool_line)
        self.btn_group.addButton(self.btn_tool_rect)
        self.btn_group.addButton(self.btn_tool_select)
        self.btn_group.addButton(self.btn_tool_cota)
        self.btn_group.addButton(self.btn_tool_ponto)

        tool_box.addWidget(self.btn_tool_line)
        tool_box.addWidget(self.btn_tool_rect)
        tool_box.addWidget(self.btn_tool_select)
        tool_box.addWidget(self.btn_tool_cota)
        tool_box.addWidget(self.btn_tool_ponto)
        side_layout.addLayout(tool_box)

        # Unidade do documento
        u_name = model_unit()
        p = model_precision()
        scale = bare_number_scale()

        # Comprimento da Parede - Entrada numérica direta ou edição
        self.lbl_length = QLabel(f"Comprimento da Parede ({u_name}):", side_panel)
        side_layout.addWidget(self.lbl_length)
        len_box = QHBoxLayout()
        self.sp_length = QDoubleSpinBox(side_panel)
        # Limites escalados conforme a unidade
        self.sp_length.setRange(0.01, 100000.0)
        self.sp_length.setDecimals(p)
        step = 100.0 if u_name == "mm" else (10.0 if u_name == "cm" else 0.10)
        self.sp_length.setSingleStep(step)
        self.sp_length.setValue(2.0 / scale)
        self.sp_length.setToolTip("Digite o comprimento desejado e clique em Aplicar ou aperte Enter")
        if self.sp_length.lineEdit():
            self.sp_length.lineEdit().returnPressed.connect(self._on_apply_length_clicked)
        len_box.addWidget(self.sp_length)

        self.btn_apply_len = QPushButton("✔️ Aplicar", side_panel)
        self.btn_apply_len.setFixedWidth(70)
        self.btn_apply_len.clicked.connect(self._on_apply_length_clicked)
        len_box.addWidget(self.btn_apply_len)
        side_layout.addLayout(len_box)

        # Sentido da alteração ao aplicar comprimento
        self.lbl_anchor_dir = QLabel("Sentido ao Alterar Medida:", side_panel)
        side_layout.addWidget(self.lbl_anchor_dir)
        self.cb_anchor_dir = QComboBox(side_panel)
        self.cb_anchor_dir.addItem("⚡ Automático (Preservar cotas)", None)
        self.cb_anchor_dir.addItem("Fixar Início ➜ Empurrar Fim", "node_a")
        self.cb_anchor_dir.addItem("Fixar Fim ➜ Empurrar Início", "node_b")
        self.cb_anchor_dir.setToolTip("Indica qual extremidade permanece fixa quando a parede selecionada tiver a medida alterada")
        side_layout.addWidget(self.cb_anchor_dir)

        # Nome do Ambiente e Pavimento
        self.lbl_amb_name = QLabel("Nome do Cômodo / Ambiente:", side_panel)
        side_layout.addWidget(self.lbl_amb_name)
        self.txt_amb_name = QLineEdit(side_panel)
        self.txt_amb_name.setPlaceholderText("Ex: Cozinha, Sala, Suíte")
        initial_name = "Cozinha"
        if self.existing_group:
            ext = getattr(self.existing_group, "ext", {})
            if isinstance(ext, dict):
                initial_name = (
                    ext.get("ambiente")
                    or ext.get("trazomob_wall", {}).get("ambiente")
                    or getattr(self.existing_group, "name", "Cozinha")
                )
            else:
                initial_name = getattr(self.existing_group, "name", "Cozinha")
        self.txt_amb_name.setText(initial_name)
        side_layout.addWidget(self.txt_amb_name)

        self.lbl_pav_name = QLabel("Pavimento / Andar:", side_panel)
        side_layout.addWidget(self.lbl_pav_name)
        self.cb_pav_name = QComboBox(side_panel)
        self.cb_pav_name.setEditable(True)
        pav_nomes = ["Térreo", "1º Andar", "2º Andar", "Subsolo", "Área Externa"]
        if getattr(self.viewport, "scene", None) is not None:
            for g in getattr(self.viewport.scene, "groups", []):
                ext = getattr(g, "ext", {})
                if isinstance(ext, dict):
                    p_data = ext.get("trazomob_pavimento")
                    if p_data and p_data.get("nome") and p_data.get("nome") not in pav_nomes:
                        pav_nomes.append(p_data.get("nome"))
                    p_direto = ext.get("pavimento") or ext.get("trazomob_wall", {}).get("pavimento")
                    if p_direto and str(p_direto).strip() not in pav_nomes:
                        pav_nomes.append(str(p_direto).strip())
        self.cb_pav_name.addItems(pav_nomes)
        idx_cur = self.cb_pav_name.findText(self._current_pav)
        if idx_cur >= 0:
            self.cb_pav_name.setCurrentIndex(idx_cur)
        else:
            self.cb_pav_name.setEditText(self._current_pav)
        side_layout.addWidget(self.cb_pav_name)

        # Elevação Base (Cota Z) do Pavimento
        self.lbl_z_base = QLabel(f"Elevação Base Z ({u_name}):", side_panel)
        side_layout.addWidget(self.lbl_z_base)
        self.sp_z_base = QDoubleSpinBox(side_panel)
        self.sp_z_base.setRange(-500000.0, 500000.0)
        self.sp_z_base.setDecimals(p)
        self.sp_z_base.setSingleStep(step)
        initial_z = self._get_z_for_pav(self._current_pav)
        self.sp_z_base.setValue(round(initial_z / scale, p))
        side_layout.addWidget(self.sp_z_base)
        self.cb_pav_name.currentTextChanged.connect(self._on_pavimento_changed)

        # Espessura
        self.lbl_thickness = QLabel(f"Espessura da Parede ({u_name}):", side_panel)
        side_layout.addWidget(self.lbl_thickness)
        self.sp_thickness = QDoubleSpinBox(side_panel)
        self.sp_thickness.setRange(0.01, 10000.0)
        self.sp_thickness.setDecimals(p)
        self.sp_thickness.setSingleStep(step)
        self.sp_thickness.setValue(0.15 / scale)
        self.sp_thickness.valueChanged.connect(self._on_params_changed)
        side_layout.addWidget(self.sp_thickness)

        # Altura / Pé-direito
        self.lbl_height = QLabel(f"Pé-Direito / Altura ({u_name}):", side_panel)
        side_layout.addWidget(self.lbl_height)
        self.sp_height = QDoubleSpinBox(side_panel)
        self.sp_height.setRange(0.1, 10000.0)
        self.sp_height.setDecimals(p)
        self.sp_height.setSingleStep(step)
        self.sp_height.setValue(2.60 / scale)
        self.sp_height.valueChanged.connect(self._on_params_changed)
        side_layout.addWidget(self.sp_height)

        # Opções automáticas de piso e teto
        # Mantém marcado por padrão para que o usuário decida gerar ou manter atualizado.
        has_existing_floor = False
        has_existing_ceiling = False
        if getattr(self.viewport, "scene", None) is not None:
            scene_groups = getattr(self.viewport.scene, "groups", [])
            target_walls = getattr(self, "existing_walls", []) or ([self.existing_group] if self.existing_group else [])
            wall_names = {getattr(w, "name", "") for w in target_walls}
            cur_amb = initial_name.strip().lower()
            for g in scene_groups:
                g_ext = getattr(g, "ext", None)
                if isinstance(g_ext, dict):
                    assoc = str(g_ext.get("associated_wall_name", "")).strip().lower()
                    g_amb = str(g_ext.get("ambiente", "")).strip().lower()
                    match = (
                        (assoc in {w.lower() for w in wall_names})
                        or (cur_amb and assoc == cur_amb)
                        or (cur_amb and g_amb == cur_amb)
                    )
                    if g_ext.get("trazomob_floor") and match:
                        has_existing_floor = True
                    if g_ext.get("trazomob_ceiling") and match:
                        has_existing_ceiling = True

        self.chk_floor = QCheckBox("Gerar Piso Automaticamente", side_panel)
        # Sempre marcado por padrão (tanto para novos ambientes quanto para ambientes existentes)
        self.chk_floor.setChecked(True)
        side_layout.addWidget(self.chk_floor)

        self.chk_ceiling = QCheckBox("Gerar Teto / Forro", side_panel)
        # Se o ambiente já tinha teto gerado, mantém marcado ao voltar para editar!
        self.chk_ceiling.setChecked(has_existing_ceiling)
        side_layout.addWidget(self.chk_ceiling)

        # Status / Contador
        self.lbl_status = QLabel("Paredes desenhadas: 0", side_panel)
        self.lbl_status.setStyleSheet("color: #00e676; font-size: 11px;")
        side_layout.addWidget(self.lbl_status)

        # Grupo Imagem de Referência / Planta de Fundo
        grp_ref = QGroupBox("🖼️ Referência", side_panel)
        grp_ref_layout = QVBoxLayout(grp_ref)
        grp_ref_layout.setContentsMargins(6, 6, 6, 6)
        grp_ref_layout.setSpacing(4)

        btn_load_ref = QPushButton("📁 Carregar Imagem...", grp_ref)
        btn_load_ref.setToolTip("Carrega uma planta baixa em JPG/PNG para desenhar por cima")
        btn_load_ref.clicked.connect(self._on_load_reference_image)
        grp_ref_layout.addWidget(btn_load_ref)

        box_ref_tools = QHBoxLayout()
        box_ref_tools.setSpacing(4)
        self.btn_calib_ref = QPushButton("📏", grp_ref)
        self.btn_calib_ref.setToolTip("Calibrar escala: clique em dois pontos com medida conhecida")
        self.btn_calib_ref.setCheckable(True)
        self.btn_calib_ref.clicked.connect(self._on_calib_ref_clicked)
        box_ref_tools.addWidget(self.btn_calib_ref)

        self.btn_move_ref = QPushButton("✋", grp_ref)
        self.btn_move_ref.setToolTip("Mover imagem de referência: arraste para posicionar")
        self.btn_move_ref.setCheckable(True)
        self.btn_move_ref.clicked.connect(self._on_move_ref_clicked)
        box_ref_tools.addWidget(self.btn_move_ref)

        btn_rot_ref = QPushButton("🔄", grp_ref)
        btn_rot_ref.setToolTip("Rotacionar imagem em 90°")
        btn_rot_ref.clicked.connect(self._on_rotate_ref_clicked)
        box_ref_tools.addWidget(btn_rot_ref)

        btn_remove_ref = QPushButton("❌", grp_ref)
        btn_remove_ref.setToolTip("Remover imagem de referência")
        btn_remove_ref.clicked.connect(self._on_remove_reference_image)
        box_ref_tools.addWidget(btn_remove_ref)
        grp_ref_layout.addLayout(box_ref_tools)

        # Opacidade / Transparência
        box_opac = QHBoxLayout()
        box_opac.addWidget(QLabel("Opacidade:", grp_ref))
        self.slider_opac = QSlider(Qt.Horizontal, grp_ref)
        self.slider_opac.setRange(10, 100)
        self.slider_opac.setValue(50)
        self.slider_opac.valueChanged.connect(self._on_ref_opacity_changed)
        box_opac.addWidget(self.slider_opac)
        grp_ref_layout.addLayout(box_opac)

        self.chk_ref_vis = QCheckBox("Exibir Imagem", grp_ref)
        self.chk_ref_vis.setChecked(True)
        self.chk_ref_vis.toggled.connect(self._on_ref_visibility_toggled)
        grp_ref_layout.addWidget(self.chk_ref_vis)

        side_layout.addWidget(grp_ref)

        # Botões de Visualização e Ações em Grade Compacta com Ícones
        box_actions = QHBoxLayout()
        box_actions.setSpacing(4)

        btn_zoom_fit = QPushButton("📐", side_panel)
        btn_zoom_fit.setToolTip("Enquadrar todas as paredes desenhadas na tela")
        btn_zoom_fit.clicked.connect(self.canvas.zoom_extents)
        box_actions.addWidget(btn_zoom_fit)

        btn_reset_cam = QPushButton("🎯", side_panel)
        btn_reset_cam.setToolTip("Centralizar na Origem (0, 0)")
        btn_reset_cam.clicked.connect(self.canvas.reset_view)
        box_actions.addWidget(btn_reset_cam)

        btn_undo = QPushButton("↩️", side_panel)
        btn_undo.setToolTip("Desfazer última alteração (Ctrl+Z)")
        btn_undo.clicked.connect(self.canvas.undo)
        box_actions.addWidget(btn_undo)

        btn_clear = QPushButton("🗑️", side_panel)
        btn_clear.setToolTip("Limpar todas as paredes")
        btn_clear.clicked.connect(self.canvas.clear_all)
        box_actions.addWidget(btn_clear)

        side_layout.addLayout(box_actions)

        # Dicas de uso compactas
        hints = QLabel("💡 <b>Dicas:</b> Digite a medida e aperte Enter. Duplo clique na cota para editar. Delete remove.", side_panel)
        hints.setStyleSheet("color: #788599; font-weight: normal; font-size: 10px;")
        hints.setWordWrap(True)
        side_layout.addWidget(hints)

        side_layout.addStretch()

        scroll_area.setWidget(side_panel)
        side_container_layout.addWidget(scroll_area, 1)

        # Botão Concluir em destaque fixo no rodapé
        bottom_box = QFrame(side_container)
        bottom_box.setStyleSheet("""
            QFrame {
                background-color: #181c24;
                border-top: 1px solid #2e3544;
                padding: 4px;
            }
            QPushButton#btn_build {
                background-color: #00b0ff;
                border: 1px solid #40c4ff;
                color: #000000;
                font-size: 13px;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton#btn_build:hover {
                background-color: #40c4ff;
            }
        """)
        bottom_layout = QVBoxLayout(bottom_box)
        bottom_layout.setContentsMargins(10, 8, 10, 8)
        self.btn_build = QPushButton("🧱 Concluir e Gerar no 3D", bottom_box)
        self.btn_build.setObjectName("btn_build")
        self.btn_build.clicked.connect(self._build_3d_and_close)
        bottom_layout.addWidget(self.btn_build)
        side_container_layout.addWidget(bottom_box)

        for btn in self.findChildren(QPushButton):
            btn.setAutoDefault(False)
            btn.setDefault(False)
        root_layout.addWidget(self.canvas, 1)
        root_layout.addWidget(side_container)

    def _set_mode(self, mode: str) -> None:
        self.canvas.mode = mode
        self.canvas._start_pt = None
        self.canvas._cota_points.clear()
        tool_buttons = (
            ("btn_tool_line", "linha"),
            ("btn_tool_rect", "retangulo"),
            ("btn_tool_select", "selecionar"),
            ("btn_tool_cota", "cota"),
            ("btn_tool_ponto", "pontos"),
        )
        for attr, btn_mode in tool_buttons:
            btn = getattr(self, attr, None)
            if btn is not None:
                btn.setChecked(mode == btn_mode)
        if hasattr(self, 'btn_calib_ref'):
            self.btn_calib_ref.setChecked(mode == "calibrar_ref")
        if hasattr(self, 'btn_move_ref'):
            self.btn_move_ref.setChecked(mode == "mover_ref")
        if mode == "pontos":
            self.lbl_status.setText(
                "📍 Clique na parede para adicionar um ponto; clique num ponto "
                "interno colinear para removê-lo e unir os trechos."
            )
        self.canvas.update_cursor()
        self.canvas.update()

    def _on_params_changed(self) -> None:
        scale = bare_number_scale()
        new_th = self.sp_thickness.value() * scale
        new_h = self.sp_height.value() * scale
        if self.canvas._selected_seg_id is not None and self.canvas._selected_seg_id in self.graph.segments:
            seg = self.graph.segments[self.canvas._selected_seg_id]
            seg.thickness = new_th
            seg.height = new_h
        else:
            self.graph.default_thickness = new_th
            self.graph.default_height = new_h
            # Atualiza também todas as paredes existentes para a nova espessura padrão global
            for s in self.graph.segments.values():
                s.thickness = new_th
                s.height = new_h
        self.canvas.update()

    def _on_wall_count_changed(self, count: int) -> None:
        self.lbl_status.setText(f"Paredes desenhadas: {count}")

    def _on_point_edit_hint(self, msg: str) -> None:
        self.lbl_status.setText(msg)

    def _get_z_for_pav(self, pav_nome: str) -> float:
        """Determina a elevação base Z para um pavimento a partir da cena ou convenção."""
        pav_nome = pav_nome.strip()
        scene = getattr(self.viewport, "scene", None)
        if scene is not None:
            for g in getattr(scene, "groups", []):
                ext = getattr(g, "ext", {})
                if isinstance(ext, dict):
                    p_data = ext.get("trazomob_pavimento")
                    if p_data and p_data.get("nome", "").strip().lower() == pav_nome.lower():
                        return float(p_data.get("z_base", 0.0))
                    if (ext.get("pavimento") or "").strip().lower() == pav_nome.lower():
                        z_val = ext.get("trazomob_wall", {}).get("z_base")
                        if z_val is not None:
                            return float(z_val)
        # Dedução inteligente padrão
        if "1" in pav_nome and "andar" in pav_nome.lower():
            return 2.80
        elif "2" in pav_nome and "andar" in pav_nome.lower():
            return 5.60
        elif "3" in pav_nome and "andar" in pav_nome.lower():
            return 8.40
        elif "subsolo" in pav_nome.lower():
            return -2.80
        return 0.00

    def _update_underlay_for_pav(self, cur_pav: str) -> None:
        """Calcula as linhas do pavimento imediatamente inferior para servir de guia fantasma (underlay)."""
        lines: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
        # Se estamos no 1º Andar ou superior, procura o andar de baixo (ex: Térreo)
        lower_pav = None
        if "1" in cur_pav:
            lower_pav = "Térreo"
        elif "2" in cur_pav:
            lower_pav = "1º Andar"
        elif "3" in cur_pav:
            lower_pav = "2º Andar"

        if lower_pav and lower_pav in self._graphs_by_pav:
            g_low = self._graphs_by_pav[lower_pav]
            for seg in g_low.segments.values():
                na = g_low.nodes.get(seg.node_a_id)
                nb = g_low.nodes.get(seg.node_b_id)
                if na and nb:
                    lines.append((na.pt, nb.pt))
        elif lower_pav and lower_pav in self._scene_walls_by_pav:
            # Pega pontos das paredes 3D do andar de baixo
            for w in self._scene_walls_by_pav[lower_pav]:
                pts = getattr(w, "ext", {}).get("trazomob_wall", {}).get("pontos", [])
                for i in range(len(pts) - 1):
                    lines.append((tuple(pts[i][:2]), tuple(pts[i + 1][:2])))

        self.canvas.set_underlay_lines(lines)

    def _on_pavimento_changed(self, new_pav: str) -> None:
        """Alterna o pavimento ativo na planta baixa, isolando o desenho de paredes por andar."""
        new_pav = (new_pav or "").strip()
        if not new_pav or new_pav == self._current_pav:
            return

        # 1. Salva o grafo atual no cache do pavimento anterior
        self._graphs_by_pav[self._current_pav] = self.graph

        # 2. Carrega ou cria grafo para o novo pavimento
        self._current_pav = new_pav
        if new_pav in self._graphs_by_pav:
            self.graph = self._graphs_by_pav[new_pav]
        else:
            scale = bare_number_scale()
            th = self.sp_thickness.value() * scale
            h = self.sp_height.value() * scale
            self.graph = WallGraph2D(default_thickness=th, default_height=h)
            self._graphs_by_pav[new_pav] = self.graph

        # 3. Atualiza paredes existentes a substituir para este pavimento
        self.existing_walls = self._scene_walls_by_pav.get(new_pav, [])

        # 4. Atualiza o canvas
        self.canvas.graph = self.graph
        self.canvas.clear_selection()
        self._update_underlay_for_pav(new_pav)

        # 5. Atualiza o campo de Elevação Base Z para a cota deste pavimento
        if hasattr(self, "sp_z_base"):
            scale = bare_number_scale()
            p = model_precision()
            z_val = self._get_z_for_pav(new_pav)
            self.sp_z_base.blockSignals(True)
            self.sp_z_base.setValue(round(z_val / scale, p))
            self.sp_z_base.blockSignals(False)

        # 6. Sugestão amigável de nome de cômodo ao trocar de pavimento
        cur_text = self.txt_amb_name.text().strip()
        if new_pav != "Térreo" and cur_text in ("Cozinha", "Sala"):
            self.txt_amb_name.setText("Suíte" if "1" in new_pav else "Quarto")
        elif new_pav == "Térreo" and cur_text in ("Suíte", "Quarto"):
            self.txt_amb_name.setText("Sala")

        self.lbl_status.setText(f"Pavimento: {new_pav} ({len(self.graph.segments)} parede(s))")
        self.canvas.update()

    def _on_wall_selected(self, seg_id: int, length_m: float) -> None:
        """Quando o usuário clica ou seleciona uma parede, atualiza os campos de espessura e comprimento na unidade do documento."""
        scale = bare_number_scale()
        p = model_precision()

        seg = self.graph.segments.get(seg_id)
        if seg:
            self.sp_length.blockSignals(True)
            self.sp_length.setValue(round(length_m / scale, p))
            self.sp_length.blockSignals(False)

            th_val = seg.thickness if seg.thickness is not None else self.graph.default_thickness
            self.sp_thickness.blockSignals(True)
            self.sp_thickness.setValue(round(th_val / scale, p))
            self.sp_thickness.blockSignals(False)

            h_val = seg.height if seg.height is not None else self.graph.default_height
            self.sp_height.blockSignals(True)
            self.sp_height.setValue(round(h_val / scale, p))
            self.sp_height.blockSignals(False)

            # Atualiza rótulos do combo de sentido de acordo com as coordenadas da parede
            na = self.graph.nodes.get(seg.node_a_id)
            nb = self.graph.nodes.get(seg.node_b_id)
            if na and nb:
                dx = nb.x - na.x
                dy = nb.y - na.y
                parts_ab = []
                if dy > 0.05: parts_ab.append("Norte ⬆")
                elif dy < -0.05: parts_ab.append("Sul ⬇")
                if dx > 0.05: parts_ab.append("Leste ➡")
                elif dx < -0.05: parts_ab.append("Oeste ⬅")
                desc_ab = " e ".join(parts_ab) if parts_ab else "Frente"

                parts_ba = []
                if -dy > 0.05: parts_ba.append("Norte ⬆")
                elif -dy < -0.05: parts_ba.append("Sul ⬇")
                if -dx > 0.05: parts_ba.append("Leste ➡")
                elif -dx < -0.05: parts_ba.append("Oeste ⬅")
                desc_ba = " e ".join(parts_ba) if parts_ba else "Frente"

                self.cb_anchor_dir.blockSignals(True)
                self.cb_anchor_dir.setItemText(1, f"Fixar Início ({na.x:.2f}, {na.y:.2f}) ➜ {desc_ab}")
                self.cb_anchor_dir.setItemText(2, f"Fixar Fim ({nb.x:.2f}, {nb.y:.2f}) ➜ {desc_ba}")
                self.cb_anchor_dir.blockSignals(False)
        else:
            # Nenhuma parede selecionada: exibe valores padrão globais
            self.cb_anchor_dir.blockSignals(True)
            self.cb_anchor_dir.setItemText(1, "Fixar Início ➜ Empurrar Fim")
            self.cb_anchor_dir.setItemText(2, "Fixar Fim ➜ Empurrar Início")
            self.cb_anchor_dir.setCurrentIndex(0)
            self.cb_anchor_dir.blockSignals(False)
            self.sp_thickness.blockSignals(True)
            self.sp_thickness.setValue(round(self.graph.default_thickness / scale, p))
            self.sp_thickness.blockSignals(False)

            self.sp_height.blockSignals(True)
            self.sp_height.setValue(round(self.graph.default_height / scale, p))
            self.sp_height.blockSignals(False)
    def _on_current_length_changed(self, length_m: float) -> None:
        """Atualiza a caixa de comprimento dinamicamente enquanto o mouse se move na tela."""
        if not self.sp_length.hasFocus():
            scale = bare_number_scale()
            p = model_precision()
            self.sp_length.blockSignals(True)
            self.sp_length.setValue(round(length_m / scale, p))
            self.sp_length.blockSignals(False)

    def _on_apply_length_clicked(self) -> None:
        """Aplica o comprimento digitado no campo de texto para a parede selecionada ou traço ativo."""
        scale = bare_number_scale()
        new_len_m = self.sp_length.value() * scale
        if new_len_m <= 0.01:
            return

        # 1. Se houver uma parede selecionada, altera seu comprimento diretamente
        if self.canvas._selected_seg_id is not None:
            seg_id = self.canvas._selected_seg_id
            seg = self.canvas.graph.segments.get(seg_id)
            anchor_nid = None
            if seg:
                chosen_dir = self.cb_anchor_dir.currentData()
                if chosen_dir == "node_a":
                    anchor_nid = seg.node_a_id
                elif chosen_dir == "node_b":
                    anchor_nid = seg.node_b_id

            conflict = self.canvas.graph.check_length_edit(
                seg_id, new_len_m, anchor_node_id=anchor_nid
            )
            if conflict:
                QMessageBox.warning(self, "Medida não aplicada", conflict)
                return

            self.canvas._save_history()
            ok = self.canvas.graph.set_segment_length(
                seg_id, new_len_m, anchor_node_id=anchor_nid, enforce_constraints=False
            )
            if not ok:
                QMessageBox.warning(
                    self, "Medida não aplicada",
                    "Não foi possível aplicar essa medida sem distorcer o modelo.",
                )
                return
            self.canvas.update()
            return

        # 2. Se estiver desenhando (iniciou o traço com _start_pt), traça na direção atual com o comprimento exato
        if self.canvas._start_pt is not None:
            p0 = self.canvas._start_pt
            p1 = self.canvas._current_mouse_world
            dx = p1[0] - p0[0]
            dy = p1[1] - p0[1]
            dist = math.hypot(dx, dy)
            if dist < 1e-4:
                dx, dy = 1.0, 0.0
                dist = 1.0
            ux, uy = dx / dist, dy / dist
            ext = self.canvas.graph.get_start_extension(p0, (ux, uy))
            eff_len = new_len_m + ext
            end_x = p0[0] + ux * eff_len
            end_y = p0[1] + uy * eff_len

            self.canvas._save_history()
            self.canvas.graph.add_segment(p0[0], p0[1], end_x, end_y)
            self.canvas.graph.merge_close_nodes(threshold=0.25)
            self.canvas.wall_count_changed.emit(len(self.canvas.graph.segments))

            # Verifica se fechou um ciclo
            end_nid = self.canvas.graph.find_node_at(end_x, end_y, threshold=0.25)
            deg = 0
            if end_nid is not None:
                deg = sum(1 for s in self.canvas.graph.segments.values() if s.node_a_id == end_nid or s.node_b_id == end_nid)

            if deg >= 2:
                self.canvas._start_pt = None
            else:
                self.canvas._start_pt = (end_x, end_y)

            self.canvas.update()

    def _on_load_reference_image(self) -> None:
        """Abre seletor de arquivos para carregar imagem de referência."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Imagem de Referência / Planta Baixa",
            "",
            "Imagens (*.png *.jpg *.jpeg *.bmp *.webp);;Todos os Arquivos (*)"
        )
        if path:
            if self.canvas.set_reference_image(path):
                self.chk_ref_vis.setChecked(True)
                self.slider_opac.setValue(50)
                self._sync_reference_image_to_scene()

    def _sync_reference_image_to_scene(self) -> None:
        """Persiste a imagem de referência no documento 3D (Scene.image_planes e Scene.plugin_data)."""
        scene = getattr(self.viewport, "scene", None)
        if scene is None:
            return

        ref_planes_name = "Planta Baixa Referencia (TrazoMob)"
        # 1. Remove qualquer ImagePlane anterior com este nome
        if hasattr(scene, "image_planes"):
            scene.image_planes = [im for im in scene.image_planes if getattr(im, "name", "") != ref_planes_name]

        # 2. Se a imagem foi removida no canvas, limpa também os dados persistidos
        if self.canvas._ref_original_pixmap is None or not self.canvas._ref_image_path:
            if hasattr(scene, "plugin_data") and isinstance(scene.plugin_data, dict):
                scene.plugin_data.pop("trazomob_floorplan_ref", None)
            if hasattr(self.viewport, "update"):
                self.viewport.update()
            return

        # 3. Salva os metadados completos no plugin_data
        if not hasattr(scene, "plugin_data") or not isinstance(scene.plugin_data, dict):
            scene.plugin_data = {}

        pdata = {
            "path": self.canvas._ref_image_path,
            "pos_world": list(self.canvas._ref_pos_world),
            "width_m": float(self.canvas._ref_width_m),
            "opacity": float(self.canvas._ref_opacity),
            "rotation": int(self.canvas._ref_rotation),
            "visible": bool(self.canvas._ref_visible),
        }
        scene.plugin_data["trazomob_floorplan_ref"] = pdata

        # 4. Cria ImagePlane nativo na cena 3D (para embutir automaticamente no arquivo .igz)
        if hasattr(scene, "image_planes") and self.canvas._ref_visible:
            # Salva uma cópia orientada temporária se a imagem estiver rotacionada
            eff_path = self.canvas._ref_image_path
            if self.canvas._ref_rotation % 360 != 0 and self.canvas._ref_pixmap is not None:
                import tempfile
                import os
                tmp_dir = os.path.join(tempfile.gettempdir(), "trazomob_ref")
                os.makedirs(tmp_dir, exist_ok=True)
                rot_deg = self.canvas._ref_rotation % 360
                base_name = os.path.splitext(os.path.basename(self.canvas._ref_image_path))[0]
                eff_path = os.path.join(tmp_dir, f"{base_name}_rot{rot_deg}.png")
                self.canvas._ref_pixmap.save(eff_path, "PNG")

            rx, ry = self.canvas._ref_pos_world
            rw = self.canvas._ref_width_m
            rh = rw * (self.canvas._ref_pixmap.height() / max(1, self.canvas._ref_pixmap.width()))

            # Vetores u e v horizontais na mesa Z=0
            origin = QVector3D(rx, ry, 0.0)
            u = QVector3D(rw, 0.0, 0.0)
            v = QVector3D(0.0, rh, 0.0)

            try:
                plane = ImagePlane(
                    path=eff_path,
                    origin=origin,
                    u=u,
                    v=v,
                    aspect=(rh / max(1e-4, rw)),
                    name=ref_planes_name,
                    opacity=float(self.canvas._ref_opacity),
                )
                scene.image_planes.append(plane)
            except Exception as exc:
                logger.debug("falha ao inserir a imagem de referência na planta: %s", exc)

        if hasattr(self.viewport, "update"):
            self.viewport.update()

    def _restore_reference_image_from_scene(self) -> None:
        """Restaura a imagem de referência previamente salva no documento."""
        scene = getattr(self.viewport, "scene", None)
        if scene is None:
            return

        ref_data = None
        # 1. Tenta carregar do plugin_data (fonte rica)
        if hasattr(scene, "plugin_data") and isinstance(scene.plugin_data, dict):
            ref_data = scene.plugin_data.get("trazomob_floorplan_ref")

        # 2. Se não encontrou no plugin_data, tenta resgatar de ImagePlane existente
        if not ref_data and hasattr(scene, "image_planes"):
            ref_planes_name = "Planta Baixa Referencia (TrazoMob)"
            for im in scene.image_planes:
                if getattr(im, "name", "") == ref_planes_name:
                    ref_data = {
                        "path": im.path,
                        "pos_world": [im.origin.x(), im.origin.y()],
                        "width_m": im.u.length(),
                        "opacity": getattr(im, "opacity", 0.5),
                        "rotation": 0,
                        "visible": True,
                    }
                    break

        if isinstance(ref_data, dict) and ref_data.get("path"):
            path = ref_data["path"]
            import os
            if os.path.exists(path):
                pos = tuple(ref_data.get("pos_world", (0.0, 0.0)))
                w_m = float(ref_data.get("width_m", 10.0))
                opac = float(ref_data.get("opacity", 0.5))
                rot = int(ref_data.get("rotation", 0))
                vis = bool(ref_data.get("visible", True))

                if self.canvas.set_reference_image(path, pos_world=pos, width_m=w_m,
                                                   opacity=opac, rotation=rot, visible=vis):
                    self.slider_opac.setValue(int(opac * 100))
                    self.chk_ref_vis.setChecked(vis)

    def _on_rotate_ref_clicked(self) -> None:
        self.canvas.rotate_reference_image(90)
        self._sync_reference_image_to_scene()

    def _on_calib_ref_clicked(self) -> None:
        if self.btn_calib_ref.isChecked():
            self.btn_move_ref.setChecked(False)
            self.btn_tool_line.setChecked(False)
            self.btn_tool_rect.setChecked(False)
            self.btn_tool_select.setChecked(False)
            self.btn_tool_cota.setChecked(False)
            self.btn_tool_ponto.setChecked(False)
            self.canvas.mode = "calibrar_ref"
            self.canvas._calib_points.clear()
            self.canvas.update_cursor()
        else:
            self._set_mode("linha")
            self.btn_tool_line.setChecked(True)

    def _on_move_ref_clicked(self) -> None:
        if self.btn_move_ref.isChecked():
            self.btn_calib_ref.setChecked(False)
            self.btn_tool_line.setChecked(False)
            self.btn_tool_rect.setChecked(False)
            self.btn_tool_select.setChecked(False)
            self.btn_tool_cota.setChecked(False)
            self.btn_tool_ponto.setChecked(False)
            self.canvas.mode = "mover_ref"
            self.canvas.update_cursor()
        else:
            self._set_mode("linha")
            self.btn_tool_line.setChecked(True)

    def _on_ref_opacity_changed(self, value: int) -> None:
        self.canvas._ref_opacity = float(value) / 100.0
        self.canvas.update()
        self._sync_reference_image_to_scene()

    def _on_ref_visibility_toggled(self, checked: bool) -> None:
        self.canvas._ref_visible = checked
        self.canvas.update()
        self._sync_reference_image_to_scene()

    def _on_remove_reference_image(self) -> None:
        self.canvas.remove_reference_image()
        self.btn_calib_ref.setChecked(False)
        self.btn_move_ref.setChecked(False)
        self._set_mode("linha")
        self.btn_tool_line.setChecked(True)
        self._sync_reference_image_to_scene()

    def _confirm_discard_changes(self) -> bool:
        """Exibe diálogo de confirmação se houver alterações não geradas no 3D."""
        if not self.has_unsaved_changes():
            return True

        res = QMessageBox.question(
            self,
            "Descartar Alterações?",
            "Você possui alterações não salvas na planta das paredes.\n\n"
            "Deseja descartar as alterações e fechar sem gerar no 3D?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        return res == QMessageBox.Yes

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Trata tecla ESC no nível do diálogo evitando fechar acidentalmente se houver traço ou alterações."""
        if event.key() == Qt.Key_Escape:
            # 1. Se o canvas estiver desenhando ou com algo selecionado, cancela apenas a ação do canvas
            if (self.canvas._start_pt is not None or
                self.canvas._selected_seg_id is not None or
                self.canvas._selected_node_id is not None or
                self.canvas._type_buffer or
                self.canvas.mode in ("calibrar_ref", "mover_ref")):
                self.canvas.keyPressEvent(event)
                return

            # 2. Se não houver nada ativo no canvas, confirma descarte se houver alterações
            if not self._confirm_discard_changes():
                event.ignore()
                return

        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        """Solicita confirmação antes de fechar a janela se houver alterações não salvas."""
        if not self._confirm_discard_changes():
            event.ignore()
            return
        self._sync_reference_image_to_scene()
        super().closeEvent(event)

    def reject(self) -> None:
        """Cancela/fecha o diálogo solicitando confirmação caso haja alterações."""
        if not self._confirm_discard_changes():
            return
        self._sync_reference_image_to_scene()
        super().reject()

    def _build_3d_and_close(self) -> None:
        self._sync_reference_image_to_scene()
        if self.graph.is_empty():
            self.reject()
            return

        scene = getattr(self.viewport, "scene", None)
        if scene is not None:
            amb_nome = self.txt_amb_name.text().strip() or "Cozinha"
            pav_nome = self.cb_pav_name.currentText().strip() or "Térreo"
            group_name = amb_nome
            scale = bare_number_scale()
            altura = self.sp_height.value() * scale

            # Cota Z definida pelo usuário no campo sp_z_base ou calculada
            if hasattr(self, "sp_z_base"):
                z_base_pav = self.sp_z_base.value() * scale
            else:
                z_base_pav = self._get_z_for_pav(pav_nome)

            res = {"wall": None, "floors": 0, "ceilings": 0, "ambiente": None}

            # Toda a alteracao do modelo em UMA transacao do historico (Ctrl+Z desfaz tudo),
            # como pede docs/plugins.md ("Mutating the document").
            def _apply(scene):
                from ..domain.ambiente import AmbienteBuilder
                # Constrói o sólido extrudado contínuo a partir do grafo 2D
                wall_grp = self.graph.build_3d_group(
                    scene,
                    altura_m=altura,
                    name=group_name,
                    z_base=z_base_pav,
                )
                if wall_grp is not None:
                    from ..wall.builder import WallBuilderTool
                    subs = WallBuilderTool.split_wall_group_into_segments(wall_grp)

                    # Preserva cor/textura das paredes antes de substituí-las.
                    old_walls = list(getattr(self, "existing_walls", []) or [])
                    if (self.existing_group is not None
                            and self.existing_group not in old_walls):
                        old_walls.append(self.existing_group)
                    old_wall_look = {}
                    for w in old_walls:
                        wp = ((getattr(w, "ext", None) or {}).get("trazomob_wall") or {})
                        key = wp.get("node_id") if wp.get("is_column") else wp.get("segment_id")
                        if key is not None:
                            old_wall_look[key] = w
                    # Paredes antigas monolíticas podem não ter segment_id; nesse
                    # caso a única origem disponível serve para todos os trechos.
                    fallback_wall = old_walls[0] if len(old_walls) == 1 else None
                    for s in subs:
                        sp = ((getattr(s, "ext", None) or {}).get("trazomob_wall") or {})
                        key = sp.get("node_id") if sp.get("is_column") else sp.get("segment_id")
                        src = old_wall_look.get(key) or fallback_wall
                        if src is not None:
                            WallMeshBuilder.copy_face_appearance(src, s)

                    # Substitui estritamente as paredes que pertencem a este pavimento
                    walls_to_replace = []
                    for w in getattr(self, "existing_walls", []):
                        w_p = (
                            getattr(w, "ext", {}).get("pavimento")
                            or getattr(w, "ext", {}).get("trazomob_wall", {}).get("pavimento")
                            or "Térreo"
                        ).strip()
                        if w_p == pav_nome:
                            walls_to_replace.append(w)

                    if not walls_to_replace and self.existing_group is not None:
                        eg_p = (
                            getattr(self.existing_group, "ext", {}).get("pavimento")
                            or getattr(self.existing_group, "ext", {}).get("trazomob_wall", {}).get("pavimento")
                            or "Térreo"
                        ).strip()
                        if eg_p == pav_nome:
                            walls_to_replace = [self.existing_group]

                    first_idx = None
                    for w in walls_to_replace:
                        if w in scene.groups:
                            cur_idx = scene.groups.index(w)
                            if first_idx is None or cur_idx < first_idx:
                                first_idx = cur_idx
                            scene.groups.remove(w)

                    if first_idx is not None:
                        for offset, g in enumerate(subs):
                            scene.groups.insert(first_idx + offset, g)
                    else:
                        for g in subs:
                            scene.groups.append(g)

                    # Identifica ciclos fechados (cômodos) formados pelas paredes
                    cycles = self.graph.find_closed_cycles()
                    floor_created = 0
                    ceiling_created = 0

                    # Remove pisos/tetos anteriores associados a este ambiente se já existiam
                    # Evita multiplicação de pisos/tetos cada vez que o usuário clica em Concluir
                    groups_to_remove = []
                    prev_wall_name = self.existing_group.name if self.existing_group is not None else None

                    for g in list(scene.groups):
                        if g is wall_grp or g is self.existing_group:
                            continue
                        g_ext = getattr(g, "ext", None)
                        if not isinstance(g_ext, dict):
                            continue

                        # Verifica se o grupo é piso ou teto associado a este ambiente e pavimento
                        is_floor = bool(g_ext.get("trazomob_floor"))
                        is_ceiling = bool(g_ext.get("trazomob_ceiling"))
                        assoc_wall = str(g_ext.get("associated_wall_name", "")).strip().lower()
                        g_amb = str(g_ext.get("ambiente", "")).strip().lower()
                        g_pav = str(g_ext.get("pavimento", "")).strip().lower()
                        cur_amb = amb_nome.strip().lower()
                        cur_pav = pav_nome.strip().lower()

                        # Identifica se pertence ao mesmo cômodo e pavimento
                        # (se não tiver pavimento gravado, assume Térreo)
                        g_pav_effective = g_pav if g_pav else "térreo"
                        match_pav = (g_pav_effective == cur_pav)
                        match_amb = (assoc_wall == cur_amb) or (g_amb == cur_amb)

                        if match_pav and match_amb:
                            # Se for piso e a opção de gerar piso está marcada, substitui o piso existente do ambiente
                            if is_floor and self.chk_floor.isChecked():
                                groups_to_remove.append(g)
                            # Se for teto e a opção de gerar teto está marcada, substitui o teto existente do ambiente
                            elif is_ceiling and self.chk_ceiling.isChecked():
                                groups_to_remove.append(g)

                    # Guarda a aparência de pisos/tetos antes de removê-los.
                    old_surface_look = {}
                    for g in groups_to_remove:
                        ge = getattr(g, "ext", None) or {}
                        kind = "floor" if ge.get("trazomob_floor") else "ceiling"
                        for nm in (ge.get("associated_wall_name"), ge.get("ambiente")):
                            if nm:
                                old_surface_look.setdefault(
                                    (kind, str(nm).strip().lower()), g)

                    for g in groups_to_remove:
                        if g in scene.groups:
                            scene.groups.remove(g)

                    for idx, cycle_pts in enumerate(cycles):
                        vec_pts = [QVector3D(p[0], p[1], 0.0) for p in cycle_pts]

                        # Resgata o nome individual atribuído ao cômodo no grafo ou usa o nome base
                        fallback_c_name = amb_nome if len(cycles) == 1 else f"{amb_nome} {idx + 1}"
                        c_nome = self.graph.get_room_name(cycle_pts, default=fallback_c_name)

                        # 1. Gera Piso automaticamente com o nome específico do cômodo
                        if self.chk_floor.isChecked():
                            floor_grp = WallMeshBuilder.build_floor_group(scene, vec_pts, z_base=z_base_pav)
                            if floor_grp is not None:
                                if not isinstance(floor_grp.ext, dict):
                                    floor_grp.ext = {}
                                floor_grp.ext["associated_wall_name"] = wall_grp.name
                                floor_grp.ext["ambiente"] = c_nome
                                floor_grp.ext["pavimento"] = pav_nome
                                floor_grp.name = f"Piso {c_nome} ({pav_nome})"
                                src = (old_surface_look.get(("floor", c_nome.strip().lower()))
                                       or old_surface_look.get(("floor", amb_nome.strip().lower())))
                                if src is not None:
                                    WallMeshBuilder.copy_face_appearance(src, floor_grp)
                                scene.groups.append(floor_grp)
                                res["floors"] += 1

                        # 2. Gera Teto / Forro automaticamente no pé-direito com o nome específico do cômodo.
                        # Usa a maior altura das paredes do ciclo: uma parede mais baixa não
                        # pode baixar o forro de todo o ambiente.
                        if self.chk_ceiling.isChecked():
                            altura_teto = self.graph.max_height_for_cycle(cycle_pts, fallback=altura)
                            ceiling_grp = WallMeshBuilder.build_ceiling_group(scene, vec_pts, altura_m=altura_teto, z_base=z_base_pav)
                            if ceiling_grp is not None:
                                if not isinstance(ceiling_grp.ext, dict):
                                    ceiling_grp.ext = {}
                                ceiling_grp.ext["associated_wall_name"] = wall_grp.name
                                ceiling_grp.ext["ambiente"] = c_nome
                                ceiling_grp.ext["pavimento"] = pav_nome
                                ceiling_grp.name = f"Teto {c_nome} ({pav_nome})"
                                src = (old_surface_look.get(("ceiling", c_nome.strip().lower()))
                                       or old_surface_look.get(("ceiling", amb_nome.strip().lower())))
                                if src is not None:
                                    WallMeshBuilder.copy_face_appearance(src, ceiling_grp)
                                scene.groups.append(ceiling_grp)
                                res["ceilings"] += 1

                    # Registra metadados de Ambiente e Pavimento nos elementos gerados
                    for s in subs:
                        if hasattr(s, "ext") and isinstance(s.ext, dict):
                            s.ext["ambiente"] = amb_nome
                            s.ext["pavimento"] = pav_nome
                            if "trazomob_wall" in s.ext and isinstance(s.ext["trazomob_wall"], dict):
                                s.ext["trazomob_wall"]["ambiente"] = amb_nome
                                s.ext["trazomob_wall"]["pavimento"] = pav_nome

                    # Assegura que o pavimento exista formalmente como grupo Pavimento na cena
                    # para que a árvore da Sidebar exiba o pavimento e seus ambientes imediatamente
                    pav_grp = AmbienteBuilder.ensure_pavimento(scene.groups, pav_nome, z_base=z_base_pav)
                    if pav_grp not in scene.groups:
                        scene.groups.append(pav_grp)

                    res["wall"] = wall_grp

            from core.history import SnapshotImport
            history = getattr(self.viewport, "history", None)
            if history is not None:
                history.execute(SnapshotImport(_apply))
            else:
                _apply(scene)
                scene.version += 1
            if hasattr(self.viewport, "notify_scene_changed"):
                self.viewport.notify_scene_changed()
            wall_grp = res["wall"]
            floor_created, ceiling_created = res["floors"], res["ceilings"]
            if wall_grp is not None:
                if hasattr(self.viewport, "flash_status"):
                    detalhes = []
                    if floor_created > 0:
                        detalhes.append(f"{floor_created} piso(s)")
                    if ceiling_created > 0:
                        detalhes.append(f"{ceiling_created} teto(s)")
                    extra_str = f" com {' e '.join(detalhes)}" if detalhes else ""
                    self.viewport.flash_status(f"🧱 Paredes geradas com sucesso{extra_str}! ({len(self.graph.segments)} paredes)")
                self.viewport.update()

        self.accept()
