# SPDX-License-Identifier: GPL-3.0-or-later
"""Diálogo Visual do TrazoMob para Renderização Foto-Realista de Ambientes e Marcenaria."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap, QPainter, QWheelEvent, QMouseEvent
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QFrame,
    QLabel, QPushButton, QComboBox, QCheckBox, QProgressBar,
    QFileDialog, QMessageBox, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QDoubleSpinBox
)

from ..render.engine import TrazoMobRenderEngine


logger = logging.getLogger("trazomob.render_dialog")


class ZoomablePreviewView(QGraphicsView):
    """QGraphicsView avançado com suporte a Zoom pela rodinha do mouse (wheel) e Pan com clique-e-arraste."""

    def __init__(self, scene: QGraphicsScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._zoom_factor = 1.0

    def wheelEvent(self, event: QWheelEvent):
        """Aplica zoom suave centralizado na posição do cursor do mouse."""
        zoom_in_factor = 1.15
        zoom_out_factor = 1.0 / zoom_in_factor

        # Salva a posição sob o mouse antes de aplicar o zoom
        old_pos = self.mapToScene(event.position().toPoint())

        delta = event.angleDelta().y()
        if delta > 0:
            scale_factor = zoom_in_factor
        elif delta < 0:
            scale_factor = zoom_out_factor
        else:
            scale_factor = 1.0

        # Limita o zoom entre 0.05x e 50x
        new_factor = self._zoom_factor * scale_factor
        if 0.05 <= new_factor <= 50.0:
            self._zoom_factor = new_factor
            self.scale(scale_factor, scale_factor)

        # Reposiciona a cena para manter o ponto sob o cursor estável
        new_pos = self.mapToScene(event.position().toPoint())
        delta_pos = new_pos - old_pos
        self.translate(delta_pos.x(), delta_pos.y())

    def zoom_in(self):
        """Aumenta o zoom em 25%."""
        if self._zoom_factor * 1.25 <= 50.0:
            self._zoom_factor *= 1.25
            self.scale(1.25, 1.25)

    def zoom_out(self):
        """Diminui o zoom em 25%."""
        if self._zoom_factor / 1.25 >= 0.05:
            self._zoom_factor /= 1.25
            self.scale(1.0 / 1.25, 1.0 / 1.25)

    def fit_image(self, pixmap_item: QGraphicsPixmapItem):
        """Enquadra a imagem inteira na área visível da tela."""
        if pixmap_item is not None and not pixmap_item.pixmap().isNull():
            self.resetTransform()
            self._zoom_factor = 1.0
            self.fitInView(pixmap_item, Qt.KeepAspectRatio)

    def zoom_100(self, pixmap_item: QGraphicsPixmapItem):
        """Exibe os pixels da imagem em tamanho real 1:1 (100%)."""
        if pixmap_item is not None and not pixmap_item.pixmap().isNull():
            self.resetTransform()
            self._zoom_factor = 1.0
            self.centerOn(pixmap_item)


class TrazoMobRenderDialog(QDialog):
    """Janela de Render Foto-Realista integrada à barra de ferramentas do TrazoMob."""

    def __init__(self, viewport, parent=None):
        super().__init__(parent)
        self.viewport = viewport
        self.setWindowTitle("📸 TrazoMob — Render Foto-Realista de Interiores")
        self.setMinimumSize(920, 640)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

        self._engine = TrazoMobRenderEngine(self)
        self._engine.progress_updated.connect(self._on_progress)
        self._engine.render_finished.connect(self._on_finished)
        self._engine.render_failed.connect(self._on_failed)

        self._current_image_path: str | None = None
        self._material_overrides: dict = {}
        self._build_ui()

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # ── PAINEL LATERAL ESQUERDO: CONTROLES E PRESETS ──
        ctrl_frame = QFrame()
        ctrl_frame.setFixedWidth(300)
        ctrl_frame.setStyleSheet("QFrame { background-color: palette(base); border: 1px solid palette(mid); border-radius: 6px; }")
        l_ctrl = QVBoxLayout(ctrl_frame)
        l_ctrl.setContentsMargins(10, 10, 10, 10)
        l_ctrl.setSpacing(10)

        lbl_sec_preset = QLabel("<b>🎨 Iluminação do Ambiente</b>")
        l_ctrl.addWidget(lbl_sec_preset)

        self.cb_preset = QComboBox()
        self.cb_preset.addItems([
            "☀️ Dia Claro (Luz Solar + Céu Físico)",
            "🌅 Entardecer / Golden Hour (Luz Dourada)",
            "🛋️ Noturno Aconchegante (Fitas LED + Luz Suave)",
            "🏢 Estúdio Comercial (Catálogo de Marcenaria)",
            "🌑 Totalmente Escuro / Breu (Apenas Luzes Internas)"
        ])
        l_ctrl.addWidget(self.cb_preset)

        l_ctrl.addSpacing(6)
        lbl_sec_quality = QLabel("<b>⚙️ Motor e Resolução</b>")
        l_ctrl.addWidget(lbl_sec_quality)

        form_opts = QFormLayout()
        form_opts.setSpacing(8)

        self.cb_engine = QComboBox()
        self.cb_engine.addItems(["Cycles (Máximo Foto-Realismo)", "EEVEE Next (Ultra-Rápido)"])
        form_opts.addRow("Motor:", self.cb_engine)

        self.cb_quality = QComboBox()
        self.cb_quality.addItems(["Rápido (Prévia)", "Média", "Alta Definição (Cliente)", "Ultra / 4K"])
        self.cb_quality.setCurrentIndex(2)  # Alta Definição padrão
        form_opts.addRow("Amostras:", self.cb_quality)

        self.cb_resolution = QComboBox()
        self.cb_resolution.addItems([
            "Aspecto da Janela 3D (Idêntico ao Viewport)",
            "1920 × 1080 (Full HD 16:9)",
            "1280 × 720 (HD 16:9)",
            "2560 × 1440 (2K 16:9)",
            "3840 × 2160 (4K 16:9)",
        ])
        self.cb_resolution.setCurrentIndex(0)  # Padrão: 100% fiel à tela do viewport
        form_opts.addRow("Resolução:", self.cb_resolution)

        l_ctrl.addLayout(form_opts)

        self.chk_verticals = QCheckBox("Corrigir Verticais (Perspectiva 2 Pontos)")
        self.chk_verticals.setToolTip("Mantém as paredes a 90° perfeitos sem inclinação vertical (estilo foto arquitetônica).")
        # Se a câmera do viewport já estiver com two_point ativo, respeita o estado
        cam_two_point = getattr(self.viewport.camera, "two_point", False)
        self.chk_verticals.setChecked(cam_two_point)
        l_ctrl.addWidget(self.chk_verticals)

        self.chk_clay = QCheckBox("🏛️ Maquete Branca / Clay Render")
        self.chk_clay.setToolTip("Modo de estudo volumétrico: renderiza em gesso branco fosco sem texturas, ideal para estudar a iluminação e aprovar sombras.")
        l_ctrl.addWidget(self.chk_clay)

        self.chk_selected = QCheckBox("🎯 Renderizar Apenas Seleção")
        self.chk_selected.setToolTip("Renderiza em poucos segundos apenas o móvel ou objetos selecionados no 3D.")
        has_sel = hasattr(self.viewport.scene, "selection") and len(self.viewport.scene.selection) > 0
        self.chk_selected.setEnabled(has_sel)
        if not has_sel:
            self.chk_selected.setText("🎯 Renderizar Seleção (Nenhum item)")
        l_ctrl.addWidget(self.chk_selected)

        # Suavidade das Sombras do Sol
        f_sun = QFormLayout()
        self.spin_sun_soft = QDoubleSpinBox()
        self.spin_sun_soft.setRange(0.5, 15.0)
        self.spin_sun_soft.setSingleStep(0.5)
        self.spin_sun_soft.setValue(2.5)
        self.spin_sun_soft.setSuffix(" °")
        self.spin_sun_soft.setToolTip("Tamanho angular do Sol: 0.5° = sombras duras cortantes; 2.5° a 5.0° = luz suave e agradável de janelas.")
        f_sun.addRow("Sombra do Sol:", self.spin_sun_soft)
        l_ctrl.addLayout(f_sun)

        l_ctrl.addSpacing(6)
        self.btn_materials = QPushButton("🎨 Configurar Materiais PBR...")
        self.btn_materials.setToolTip("Personalizar como madeiras, tecidos, pedras, vidros e metais reagem à luz.")
        self.btn_materials.setStyleSheet("QPushButton { font-weight: bold; padding: 6px; }")
        self.btn_materials.clicked.connect(self._open_material_editor)
        l_ctrl.addWidget(self.btn_materials)

        # Restaura preferências salvas do usuário (preset, motor, amostras, resolução)
        self._load_preferences()

        # Salva automaticamente sempre que o usuário alterar alguma opção
        self.cb_preset.currentIndexChanged.connect(self._save_preferences)
        self.cb_engine.currentIndexChanged.connect(self._save_preferences)
        self.cb_quality.currentIndexChanged.connect(self._save_preferences)
        self.cb_resolution.currentIndexChanged.connect(self._save_preferences)
        self.chk_verticals.toggled.connect(self._save_preferences)

        l_ctrl.addStretch()

        self.btn_render = QPushButton("🚀 Iniciar Render Foto-Realista")
        self.btn_render.setStyleSheet(
            "QPushButton { background-color: #16A34A; color: white; font-weight: bold; font-size: 13px; padding: 12px; border-radius: 6px; }"
            "QPushButton:hover { background-color: #15803D; }"
            "QPushButton:disabled { background-color: #94A3B8; }"
        )
        self.btn_render.clicked.connect(self._start_render)
        l_ctrl.addWidget(self.btn_render)

        self.btn_render_all = QPushButton("📸 Renderizar Todas as Cenas (Lote)")
        self.btn_render_all.setToolTip("Batch Render: renderiza automaticamente todas as Cenas/Páginas salvas no projeto em sequência.")
        self.btn_render_all.setStyleSheet(
            "QPushButton { background-color: #0284C7; color: white; font-weight: bold; padding: 8px; border-radius: 6px; }"
            "QPushButton:hover { background-color: #0369A1; }"
            "QPushButton:disabled { background-color: #94A3B8; }"
        )
        self.btn_render_all.clicked.connect(self._start_batch_render)
        l_ctrl.addWidget(self.btn_render_all)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self._cancel_render)
        l_ctrl.addWidget(self.btn_cancel)

        main_layout.addWidget(ctrl_frame)

        # ── PAINEL PRINCIPAL DIREITO: VISUALIZADOR DA IMAGEM ──
        view_layout = QVBoxLayout()
        view_layout.setContentsMargins(0, 0, 0, 0)
        view_layout.setSpacing(6)

        # Barra superior com controles rápidos de Zoom
        h_zoom_toolbar = QHBoxLayout()
        h_zoom_toolbar.setContentsMargins(0, 0, 0, 0)
        h_zoom_toolbar.setSpacing(6)

        lbl_zoom_hint = QLabel("🔍 Zoom (Scroll ou Botões) | ✋ Pan (Clique e Arraste)")
        lbl_zoom_hint.setStyleSheet("color: palette(text); font-size: 11px;")
        h_zoom_toolbar.addWidget(lbl_zoom_hint)
        h_zoom_toolbar.addStretch()

        self.btn_zoom_in = QPushButton("➕ Zoom In")
        self.btn_zoom_in.setToolTip("Aumentar zoom da imagem")
        self.btn_zoom_in.clicked.connect(lambda: self.view.zoom_in())
        h_zoom_toolbar.addWidget(self.btn_zoom_in)

        self.btn_zoom_out = QPushButton("➖ Zoom Out")
        self.btn_zoom_out.setToolTip("Diminuir zoom da imagem")
        self.btn_zoom_out.clicked.connect(lambda: self.view.zoom_out())
        h_zoom_toolbar.addWidget(self.btn_zoom_out)

        self.btn_zoom_100 = QPushButton("🔍 100% (1:1)")
        self.btn_zoom_100.setToolTip("Visualizar em tamanho real (pixel por pixel)")
        self.btn_zoom_100.clicked.connect(lambda: self.view.zoom_100(self._pix_item))
        h_zoom_toolbar.addWidget(self.btn_zoom_100)

        self.btn_zoom_fit = QPushButton("⛶ Ajustar à Tela")
        self.btn_zoom_fit.setToolTip("Enquadrar imagem inteira na tela")
        self.btn_zoom_fit.clicked.connect(lambda: self.view.fit_image(self._pix_item))
        h_zoom_toolbar.addWidget(self.btn_zoom_fit)

        view_layout.addLayout(h_zoom_toolbar)

        # Área Gráfica Interativa com Zoom e Pan
        self.scene = QGraphicsScene(self)
        self.view = ZoomablePreviewView(self.scene, self)
        self.view.setStyleSheet("background-color: #1E293B; border: 1px solid palette(mid); border-radius: 6px;")
        self._pix_item = QGraphicsPixmapItem()
        self.scene.addItem(self._pix_item)
        view_layout.addWidget(self.view, 1)

        # Barra de Progresso e Status
        h_status = QHBoxLayout()
        self.lbl_status = QLabel("Pronto para renderizar a vista atual da câmera.")
        self.lbl_status.setStyleSheet("font-weight: bold; color: palette(text);")
        h_status.addWidget(self.lbl_status, 1)

        self.btn_save = QPushButton("💾 Salvar Imagem...")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._save_image)
        h_status.addWidget(self.btn_save)

        self.btn_open_blender = QPushButton("🟠 Abrir no Blender...")
        self.btn_open_blender.setEnabled(False)
        self.btn_open_blender.setToolTip("Abre a cena completa com shaders PBR e luzes configuradas diretamente no Blender.")
        self.btn_open_blender.clicked.connect(self._open_in_blender)
        h_status.addWidget(self.btn_open_blender)

        view_layout.addLayout(h_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid palette(mid);
                border-radius: 4px;
                text-align: center;
                font-weight: bold;
                background-color: palette(base);
                color: palette(text);
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2563EB, stop:1 #38BDF8);
                border-radius: 3px;
            }
        """)
        self.progress_bar.setVisible(False)
        view_layout.addWidget(self.progress_bar)

        main_layout.addLayout(view_layout, 1)

    def _start_render(self):
        preset_keys = ["dia", "tarde", "noturno", "estudio", "escuro"]
        preset = preset_keys[self.cb_preset.currentIndex()]

        engine = "cycles" if self.cb_engine.currentIndex() == 0 else "eevee"

        qual_keys = ["draft", "medium", "high", "ultra"]
        quality = qual_keys[self.cb_quality.currentIndex()]

        idx = self.cb_resolution.currentIndex()
        if idx == 0:
            # 100% proporcional à janela 3D do IngeTrazo
            vp_w = max(self.viewport.width(), 1)
            vp_h = max(self.viewport.height(), 1)
            aspect = vp_w / vp_h
            w = 1920
            h = max(2, round(w / aspect))
        else:
            res_map = [(1920, 1080), (1280, 720), (2560, 1440), (3840, 2160)]
            w, h = res_map[idx - 1]

        vert = self.chk_verticals.isChecked()
        clay = self.chk_clay.isChecked()
        sel_only = self.chk_selected.isChecked()
        sun_soft = float(self.spin_sun_soft.value())

        self.btn_render.setEnabled(False)
        self.btn_cancel.setVisible(True)
        self.btn_save.setEnabled(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        ok = self._engine.start_render(
            scene=self.viewport.scene,
            camera=self.viewport.camera,
            preset=preset,
            engine=engine,
            quality=quality,
            width=w,
            height=h,
            correct_verticals=vert,
            material_overrides=self._material_overrides,
            clay_mode=clay,
            selected_only=sel_only,
            sun_softness=sun_soft
        )
        if not ok:
            self._reset_buttons()

    def _start_batch_render(self):
        saved_views = list(getattr(self.viewport.scene, "saved_views", []))
        if not saved_views:
            QMessageBox.information(
                self,
                "Renderizar Cenas em Lote",
                "Nenhuma Cena/Página salva foi encontrada no projeto.\n"
                "Para usar o Batch Render, salve ao menos uma visualização no painel 'Scenes'."
            )
            return

        self._batch_queue = list(saved_views)
        self._batch_total = len(self._batch_queue)
        self._batch_index = 0
        self._render_next_batch_scene()

    def _render_next_batch_scene(self):
        if not hasattr(self, "_batch_queue") or not self._batch_queue:
            self._reset_buttons()
            self.lbl_status.setText(f"🎉 Render em lote concluído! ({self._batch_total} cenas finalizadas)")
            return

        view = self._batch_queue.pop(0)
        self._batch_index += 1
        scene = self.viewport.scene
        # Aplica o enquadramento da câmera da cena salva
        view.apply(scene, self.viewport.camera)

        preset_keys = ["dia", "tarde", "noturno", "estudio", "escuro"]
        preset = preset_keys[self.cb_preset.currentIndex()]
        engine = "cycles" if self.cb_engine.currentIndex() == 0 else "eevee"
        qual_keys = ["draft", "medium", "high", "ultra"]
        quality = qual_keys[self.cb_quality.currentIndex()]
        idx = self.cb_resolution.currentIndex()
        if idx == 0:
            vp_w = max(self.viewport.width(), 1)
            vp_h = max(self.viewport.height(), 1)
            aspect = vp_w / vp_h
            w = 1920
            h = max(2, round(w / aspect))
        else:
            res_map = [(1920, 1080), (1280, 720), (2560, 1440), (3840, 2160)]
            w, h = res_map[idx - 1]

        vert = self.chk_verticals.isChecked()
        clay = self.chk_clay.isChecked()
        sun_soft = float(self.spin_sun_soft.value())

        self.btn_render.setEnabled(False)
        self.btn_render_all.setEnabled(False)
        self.btn_cancel.setVisible(True)
        self.btn_save.setEnabled(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.lbl_status.setText(f"📸 Renderizando cena {self._batch_index}/{self._batch_total}: '{view.name}'...")

        ok = self._engine.start_render(
            scene=scene,
            camera=self.viewport.camera,
            preset=preset,
            engine=engine,
            quality=quality,
            width=w,
            height=h,
            correct_verticals=vert,
            material_overrides=self._material_overrides,
            clay_mode=clay,
            sun_softness=sun_soft
        )
        if not ok:
            self._reset_buttons()

    def _open_material_editor(self):
        from ..ui.material_editor_dialog import MaterialEditorDialog
        dlg = MaterialEditorDialog(self.viewport.scene, current_overrides=self._material_overrides, viewport=self.viewport, parent=self)
        if dlg.exec():
            self._material_overrides = dlg.get_overrides()
            n_custom = len(self._material_overrides)
            if n_custom > 0:
                self.btn_materials.setText(f"🎨 Materiais PBR ({n_custom} customizados)")
                self.btn_materials.setStyleSheet("QPushButton { font-weight: bold; padding: 6px; color: #0284C7; }")
            else:
                self.btn_materials.setText("🎨 Configurar Materiais PBR...")
                self.btn_materials.setStyleSheet("QPushButton { font-weight: bold; padding: 6px; }")
            self._save_preferences()

    def _load_preferences(self):
        from PySide6.QtCore import QSettings
        import json
        settings = QSettings()
        # Carrega índices
        p_idx = settings.value("trazomob_render/preset_index", 0, type=int)
        e_idx = settings.value("trazomob_render/engine_index", 0, type=int)
        q_idx = settings.value("trazomob_render/quality_index", 2, type=int)
        r_idx = settings.value("trazomob_render/resolution_index", 0, type=int)
        vert = settings.value("trazomob_render/correct_verticals", True, type=bool)

        self.cb_preset.blockSignals(True)
        self.cb_preset.setCurrentIndex(max(0, min(p_idx, self.cb_preset.count() - 1)))
        self.cb_preset.blockSignals(False)

        self.cb_engine.blockSignals(True)
        self.cb_engine.setCurrentIndex(max(0, min(e_idx, self.cb_engine.count() - 1)))
        self.cb_engine.blockSignals(False)

        self.cb_quality.blockSignals(True)
        self.cb_quality.setCurrentIndex(max(0, min(q_idx, self.cb_quality.count() - 1)))
        self.cb_quality.blockSignals(False)

        self.cb_resolution.blockSignals(True)
        self.cb_resolution.setCurrentIndex(max(0, min(r_idx, self.cb_resolution.count() - 1)))
        self.cb_resolution.blockSignals(False)

        self.chk_verticals.blockSignals(True)
        self.chk_verticals.setChecked(bool(vert))
        self.chk_verticals.blockSignals(False)

        # 1. Carrega preferências GLOBAIS do usuário (para todo projeto novo)
        raw_globals = settings.value("trazomob_render/global_material_defaults", "{}")
        combined_mats = {}
        try:
            if isinstance(raw_globals, str) and raw_globals.strip():
                combined_mats.update(json.loads(raw_globals))
        except Exception:
            pass

        # 2. Carrega preferências salvas no próprio projeto (.igz / scene.plugin_data)
        scene = getattr(self.viewport, "scene", None)
        if scene is not None:
            pdata = getattr(scene, "plugin_data", None) or {}
            proj_mats = pdata.get("trazomob", {}).get("material_overrides")
            if isinstance(proj_mats, dict):
                combined_mats.update(proj_mats)

        self._material_overrides = combined_mats
        n = len(self._material_overrides)
        if n > 0:
            self.btn_materials.setText(f"🎨 Materiais PBR ({n} customizados)")
            self.btn_materials.setStyleSheet("QPushButton { font-weight: bold; padding: 6px; color: #0284C7; }")
        else:
            self.btn_materials.setText("🎨 Configurar Materiais PBR...")
            self.btn_materials.setStyleSheet("QPushButton { font-weight: bold; padding: 6px; }")

    def _save_preferences(self):
        from PySide6.QtCore import QSettings
        import json
        settings = QSettings()
        settings.setValue("trazomob_render/preset_index", self.cb_preset.currentIndex())
        settings.setValue("trazomob_render/engine_index", self.cb_engine.currentIndex())
        settings.setValue("trazomob_render/quality_index", self.cb_quality.currentIndex())
        settings.setValue("trazomob_render/resolution_index", self.cb_resolution.currentIndex())
        settings.setValue("trazomob_render/correct_verticals", self.chk_verticals.isChecked())
        # Salva as alterações de material diretamente na cena (.igz) para persistir no projeto
        scene = getattr(self.viewport, "scene", None)
        if scene is not None:
            if not hasattr(scene, "plugin_data") or not isinstance(scene.plugin_data, dict):
                scene.plugin_data = {}
            if "trazomob" not in scene.plugin_data or not isinstance(scene.plugin_data["trazomob"], dict):
                scene.plugin_data["trazomob"] = {}
            scene.plugin_data["trazomob"]["material_overrides"] = dict(self._material_overrides)
            if hasattr(scene, "version"):
                scene.version += 1



    def _cancel_render(self):
        self._engine.cancel()
        self._reset_buttons()

    def _reset_buttons(self):
        self.btn_render.setEnabled(True)
        self.btn_render_all.setEnabled(True)
        self.btn_cancel.setVisible(False)
        self.progress_bar.setVisible(False)

    def _on_progress(self, percent: int, msg: str):
        self.lbl_status.setText(msg)
        if percent < 0:
            # Modo indeterminado (marcador animado pulsante se samples não numéricos)
            self.progress_bar.setRange(0, 0)
        else:
            if self.progress_bar.maximum() == 0:
                self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(max(0, min(100, percent)))

    def _on_finished(self, img_path: str):
        self._current_image_path = img_path
        pix = QPixmap(img_path)
        self._pix_item.setPixmap(pix)
        self.scene.setSceneRect(self._pix_item.boundingRect())
        self.view.fit_image(self._pix_item)
        self.btn_save.setEnabled(True)
        self.btn_open_blender.setEnabled(True)

        # Se houver fila de batch render ativa, continua para a próxima cena
        if hasattr(self, "_batch_queue") and self._batch_queue:
            self._render_next_batch_scene()
        else:
            self._reset_buttons()
            self.lbl_status.setText(f"✅ Render concluído com sucesso ({pix.width()} × {pix.height()} px)!")

    def _on_failed(self, err_msg: str):
        self._reset_buttons()
        self.lbl_status.setText("❌ Falha na renderização.")
        QMessageBox.warning(self, "Render Foto-Realista", err_msg)

    def _open_in_blender(self):
        blend_file = Path(self._current_image_path).parent / "cena_marcenaria_trazomob.blend"
        if not blend_file.exists():
            QMessageBox.warning(self, "Abrir no Blender", "O arquivo .blend da cena não foi encontrado.")
            return
        blender_exe = self._engine.get_blender_executable()
        if not blender_exe:
            QMessageBox.warning(self, "Abrir no Blender", "Executável do Blender não encontrado.")
            return
        import subprocess
        subprocess.Popen([blender_exe, str(blend_file)])

    def _save_image(self):
        if not self._current_image_path or not os.path.isfile(self._current_image_path):
            return
        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Render Foto-Realista",
            "render_ambiente.png",
            "Imagens PNG (*.png);;Imagens JPEG (*.jpg)"
        )
        if dest:
            import shutil
            shutil.copyfile(self._current_image_path, dest)
            QMessageBox.information(self, "Imagem Salva", f"Render salvo com sucesso em:\n{dest}")
