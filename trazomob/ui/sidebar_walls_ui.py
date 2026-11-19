# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Construcao do card Construtor de Paredes da barra lateral."""
from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
)
from ..domain.i18n import tr


def _compact_wall_btn(
    text: str,
    tooltip: str = "",
    *,
    variant: str = "secondary",
    accent: str | None = None,
    checkable: bool = False,
    checked: bool = False,
    visible: bool = True,
) -> QPushButton:
    """Create a space-efficient button matching TrazoMob's compact CAD panel density."""
    btn = QPushButton(text)
    if tooltip:
        btn.setToolTip(tooltip)
    if checkable:
        btn.setCheckable(True)
        btn.setChecked(checked)
    btn.setVisible(visible)
    btn.setMinimumWidth(0)
    btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    if variant == "primary":
        btn.setStyleSheet(
            "QPushButton { background-color: palette(highlight); color: palette(highlighted-text);"
            " font-weight: 600; font-size: 11px; padding: 4px 6px; border-radius: 3px;"
            " border: 1px solid palette(highlight); }"
            "QPushButton:hover { opacity: 0.9; }"
            "QPushButton:checked { background-color: palette(dark); color: palette(text);"
            " border: 1px solid palette(highlight); }"
        )
    elif variant == "lock":
        btn.setStyleSheet(
            "QPushButton { background-color: palette(button); color: palette(text);"
            " font-size: 11px; font-weight: 600; padding: 4px 6px; border-radius: 3px;"
            " border: 1px solid palette(mid); }"
            "QPushButton:hover { background-color: palette(midlight); }"
            "QPushButton:checked { background-color: #2e7d32; color: white; border: 1px solid #1b5e20; }"
            "QPushButton:checked:hover { background-color: #388e3c; }"
        )
    else:
        left_border = f" border-left: 3px solid {accent};" if accent else ""
        btn.setStyleSheet(
            "QPushButton { background-color: palette(button); color: palette(text);"
            f" font-size: 11px; font-weight: 500; padding: 4px 6px; border-radius: 3px;"
            f" border: 1px solid palette(mid);{left_border} }}"
            "QPushButton:hover { background-color: palette(midlight); border-color: palette(highlight); }"
        )
    return btn


def _micro_field(label_text: str, widget) -> QVBoxLayout:
    """Stack a compact 10px caption cleanly above an input control."""
    box = QVBoxLayout()
    box.setContentsMargins(0, 0, 0, 0)
    box.setSpacing(1)
    lbl = QLabel(label_text)
    lbl.setStyleSheet("font-size: 10px; color: palette(placeholder-text);")
    box.addWidget(lbl)
    box.addWidget(widget)
    return box


def _pair_row(*widgets) -> QHBoxLayout:
    """Pack two or more buttons into an equal-width compact horizontal strip."""
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(4)
    for w in widgets:
        row.addWidget(w, 1)
    return row


class SidebarWallsUIMixin:
    """Monta o card completo de edicao e referencia de paredes."""

    def _build_walls_card(self, layout) -> None:
        """Cria o card de paredes compacto e organizado, adicionando-o a ``layout``."""
        self.scroll_paredes = QScrollArea()
        self.scroll_paredes.setWidgetResizable(True)
        self.scroll_paredes.setFrameShape(QFrame.NoFrame)
        self.scroll_paredes.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.card_paredes = QFrame()
        self.card_paredes.setObjectName("card_paredes")
        self.card_paredes.setStyleSheet(
            "QFrame#card_paredes { background-color: palette(base); border: 1px solid palette(mid);"
            " border-radius: 4px; }"
            "QFrame#card_paredes QSpinBox, QFrame#card_paredes QComboBox"
            " { min-height: 22px; padding: 1px 4px; font-size: 11px; }"
            "QFrame#card_paredes QCheckBox { font-size: 11px; spacing: 4px; }"
            "QFrame#card_paredes QLabel { font-size: 11px; color: palette(text); border: none; padding: 0px; }"
        )
        l_paredes = QVBoxLayout(self.card_paredes)
        l_paredes.setContentsMargins(6, 5, 6, 5)
        l_paredes.setSpacing(4)

        # ── Bloco 1: Segmento, Medidas & Referência (Grid Compacto) ────────────
        grid_params = QGridLayout()
        grid_params.setContentsMargins(0, 0, 0, 0)
        grid_params.setHorizontalSpacing(6)
        grid_params.setVerticalSpacing(3)

        self.cb_parede_segmento = QComboBox()
        self.cb_parede_segmento.setMinimumWidth(0)
        self.cb_parede_segmento.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.cb_parede_segmento.setMinimumContentsLength(10)
        self.cb_parede_segmento.setToolTip(
            tr("Selecione qual parede do cômodo você deseja consultar ou alterar o comprimento.")
        )
        self.cb_parede_segmento.currentIndexChanged.connect(self._on_wall_segment_combobox_changed)
        grid_params.addWidget(QLabel(tr("🧱 Parede:")), 0, 0)
        grid_params.addWidget(self.cb_parede_segmento, 0, 1, 1, 3)

        self.sp_parede_comprimento = QSpinBox()
        self.sp_parede_comprimento.setRange(200, 50000)
        self.sp_parede_comprimento.setValue(3000)
        self.sp_parede_comprimento.setSuffix(" mm")
        self.sp_parede_comprimento.setSingleStep(50)
        self.sp_parede_comprimento.setMinimumWidth(0)
        self.sp_parede_comprimento.setToolTip(
            tr("Comprimento desta parede em milímetros. Clique em 'Atualizar' para aplicar.")
        )

        self.sp_parede_altura = QSpinBox()
        self.sp_parede_altura.setRange(1000, 6000)
        self.sp_parede_altura.setValue(2600)
        self.sp_parede_altura.setSuffix(" mm")
        self.sp_parede_altura.setSingleStep(50)
        self.sp_parede_altura.setMinimumWidth(0)

        self.sp_parede_esp = QSpinBox()
        self.sp_parede_esp.setRange(50, 500)
        self.sp_parede_esp.setValue(150)
        self.sp_parede_esp.setSuffix(" mm")
        self.sp_parede_esp.setSingleStep(10)
        self.sp_parede_esp.setMinimumWidth(0)

        self.cb_parede_alinhar = QComboBox()
        self.cb_parede_alinhar.setMinimumWidth(0)
        self.cb_parede_alinhar.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.cb_parede_alinhar.setMinimumContentsLength(8)
        self.cb_parede_alinhar.addItems([
            tr("Face Interna (Medida Livre)"),
            tr("Centro da Parede"),
            tr("Face Externa"),
        ])

        grid_params.addLayout(_micro_field(tr("Comprimento:"), self.sp_parede_comprimento), 1, 0, 1, 2)
        grid_params.addLayout(_micro_field(tr("Pé-Direito:"), self.sp_parede_altura), 1, 2, 1, 2)
        grid_params.addLayout(_micro_field(tr("Espessura:"), self.sp_parede_esp), 2, 0, 1, 2)
        grid_params.addLayout(_micro_field(tr("Alinhamento:"), self.cb_parede_alinhar), 2, 2, 1, 2)

        # --- Réguas Paramétricas de Alturas (Linhas-Guia) ---
        from ..wall.guides import WallGuideRulerManager
        self._ruler_mgr = WallGuideRulerManager.get_instance()

        self.cb_regua_ambiente = QComboBox()
        self.cb_regua_ambiente.setMinimumWidth(0)
        self.cb_regua_ambiente.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.cb_regua_ambiente.setMinimumContentsLength(8)
        self.cb_regua_ambiente.addItems(list(self._ruler_mgr.presets.keys()))
        self.cb_regua_ambiente.setCurrentText(self._ruler_mgr.active_preset_name)

        def _on_ruler_changed(preset_name):
            if preset_name:
                self._ruler_mgr.set_active_preset(preset_name)
                vp = self._get_viewport()
                if vp:
                    vp.update()

        self.cb_regua_ambiente.currentTextChanged.connect(_on_ruler_changed)

        self.btn_edit_reguas = QPushButton("⚙️")
        self.btn_edit_reguas.setFixedSize(26, 22)
        self.btn_edit_reguas.setToolTip(tr("Configurar, criar e editar réguas e alturas personalizadas..."))

        def _open_ruler_dialog():
            from ..ui.ruler_editor_dialog import RulerEditorDialog
            dlg = RulerEditorDialog(parent=self.window(), ruler_mgr=self._ruler_mgr)
            if dlg.exec():
                self.cb_regua_ambiente.blockSignals(True)
                self.cb_regua_ambiente.clear()
                self.cb_regua_ambiente.addItems(list(self._ruler_mgr.presets.keys()))
                self.cb_regua_ambiente.setCurrentText(self._ruler_mgr.active_preset_name)
                self.cb_regua_ambiente.blockSignals(False)
                vp = self._get_viewport()
                if vp:
                    vp.update()

        self.btn_edit_reguas.clicked.connect(_open_ruler_dialog)

        h_ruler_row = QHBoxLayout()
        h_ruler_row.setContentsMargins(0, 0, 0, 0)
        h_ruler_row.setSpacing(3)
        h_ruler_row.addWidget(self.cb_regua_ambiente, 1)
        h_ruler_row.addWidget(self.btn_edit_reguas)
        grid_params.addWidget(QLabel(tr("📏 Régua:")), 3, 0)
        grid_params.addLayout(h_ruler_row, 3, 1, 1, 3)

        for col in range(4):
            grid_params.setColumnStretch(col, 1)
        l_paredes.addLayout(grid_params)

        # --- Checkboxes em Grade 2x2 (Sem coluna vazia à esquerda) ---
        grid_chk = QGridLayout()
        grid_chk.setContentsMargins(0, 0, 0, 2)
        grid_chk.setHorizontalSpacing(6)
        grid_chk.setVerticalSpacing(2)

        self.chk_parede_todas = QCheckBox(tr("Todas as paredes"))
        self.chk_parede_todas.setChecked(True)
        self.chk_parede_todas.setToolTip(
            tr("Aplicar a todas as paredes: se marcado, altera o pé-direito de todas as paredes interligadas.\nSe desmarcado, altera somente a parede selecionada.")
        )

        self.chk_parede_teto = QCheckBox(tr("Gerar Teto / Forro"))
        _saved_teto = QSettings().value("trazomob_wall/gerar_teto", False, type=bool)
        self.chk_parede_teto.setChecked(_saved_teto)
        self.chk_parede_teto.toggled.connect(
            lambda chk: QSettings().setValue("trazomob_wall/gerar_teto", bool(chk))
        )
        self.chk_parede_teto.setToolTip(
            tr("Gerar Teto / Forro ao fechar: cria automaticamente a laje/forro de teto no pé-direito ao fechar o perímetro.")
        )

        self.chk_regua_visivel = QCheckBox(tr("Linhas-Guia 3D"))
        self.chk_regua_visivel.setChecked(self._ruler_mgr.visible)
        self.chk_regua_visivel.setToolTip(tr("Exibir linhas-guia horizontais e ativar snap magnético nas alturas."))

        def _on_ruler_toggle(checked):
            self._ruler_mgr.visible = bool(checked)
            self._ruler_mgr.snap_enabled = bool(checked)
            self._ruler_mgr.save_preferences()
            vp = self._get_viewport()
            if vp:
                vp.update()

        self.chk_regua_visivel.toggled.connect(_on_ruler_toggle)

        self.chk_regua_labels = QCheckBox(tr("Rótulos das Guias"))
        self.chk_regua_labels.setChecked(self._ruler_mgr.show_labels)
        self.chk_regua_labels.setToolTip(tr("Exibir rótulos de texto com o nome e cota de cada linha-guia."))

        def _on_ruler_labels_toggle(checked):
            self._ruler_mgr.show_labels = bool(checked)
            self._ruler_mgr.save_preferences()
            vp = self._get_viewport()
            if vp:
                vp.update()

        self.chk_regua_labels.toggled.connect(_on_ruler_labels_toggle)

        grid_chk.addWidget(self.chk_parede_todas, 0, 0)
        grid_chk.addWidget(self.chk_parede_teto, 0, 1)
        grid_chk.addWidget(self.chk_regua_visivel, 1, 0)
        grid_chk.addWidget(self.chk_regua_labels, 1, 1)
        l_paredes.addLayout(grid_chk)

        # ── Bloco 2: Edição da Parede & Vista ───────────────────────────────────
        self.btn_toggle_wall_tool = _compact_wall_btn(
            tr("✏️ Paredes 3D"),
            tr("Construir ou editar paredes no 3D / Planta 2D."),
            variant="primary",
            checkable=True,
        )
        self.btn_toggle_wall_tool.clicked.connect(self._toggle_wall_builder)

        self.btn_apply_wall = _compact_wall_btn(
            tr("🔄 Atualizar"),
            tr("Aplicar comprimento, pé-direito e espessura na parede selecionada."),
            variant="primary",
            visible=False,
        )
        self.btn_apply_wall.clicked.connect(self._apply_wall_changes)
        l_paredes.addLayout(_pair_row(self.btn_toggle_wall_tool, self.btn_apply_wall))

        self.btn_frente_parede = _compact_wall_btn(
            tr("👁️ Frente (3D)"),
            tr("Posiciona a câmera do 3D perfeitamente de frente para a parede selecionada (ou dê dois cliques rápidos nela)."),
            accent="#059669",
            visible=False,
        )

        def _on_clicar_frente_parede():
            from ..wall.selection import WallSelectionManager
            wall_mgr = WallSelectionManager.get_instance(self._get_viewport())
            wall_mgr.align_view_to_wall()

        self.btn_frente_parede.clicked.connect(_on_clicar_frente_parede)

        self.btn_elevacao_parede = _compact_wall_btn(
            tr("📐 Elevação 2D"),
            tr("Abre a vista ortogonal técnica 2D da parede com todos os móveis e cotas milimétricas detalhadas."),
            accent="#059669",
            visible=False,
        )
        self.btn_elevacao_parede.clicked.connect(self._on_abrir_elevacao_parede)
        l_paredes.addLayout(_pair_row(self.btn_frente_parede, self.btn_elevacao_parede))

        # ── Bloco 3: Encaixes Rápidos (2x2) ─────────────────────────────────────
        self.btn_encaixar_bancada = _compact_wall_btn(
            tr("🪨 Bancada"),
            tr("Cria e encaixa automaticamente uma bancada de pedra/tampo cobrindo todos os balcões encostados nesta parede."),
            accent="#0284C7",
            visible=False,
        )
        self.btn_encaixar_bancada.clicked.connect(self._on_encaixar_bancada_sobre_balcoes)

        self.btn_encaixar_tamponamento = _compact_wall_btn(
            tr("📐 Tamponam. (U)"),
            tr("Cria e encaixa um envoltório contínuo (lateral esq + tampo superior + lateral dir) abraçando os módulos desta parede."),
            accent="#0284C7",
            visible=False,
        )
        self.btn_encaixar_tamponamento.clicked.connect(self._on_encaixar_tamponamento_sobre_balcoes)
        l_paredes.addLayout(_pair_row(self.btn_encaixar_bancada, self.btn_encaixar_tamponamento))

        self.btn_encaixar_rodape = _compact_wall_btn(
            tr("🪵 Rodapé"),
            tr("Cria e encaixa uma régua única de rodapé contínuo cobrindo a base frontal de todos os balcões encostados nesta parede."),
            accent="#B45309",
            visible=False,
        )
        self.btn_encaixar_rodape.clicked.connect(self._on_encaixar_rodape_sobre_balcoes)

        self.btn_fechar_vao = _compact_wall_btn(
            tr("🧩 Arremate"),
            tr("Detecta a folga residual entre o último módulo e a parede de canto e insere uma régua de arremate sob medida."),
            accent="#0D9488",
            visible=False,
        )
        self.btn_fechar_vao.clicked.connect(self._on_fechar_vao_canto)
        l_paredes.addLayout(_pair_row(self.btn_encaixar_rodape, self.btn_fechar_vao))

        # ── Bloco 4: Preenchimento Automático (Compacto) ────────────────────────
        h_auto_cfg = QHBoxLayout()
        h_auto_cfg.setContentsMargins(0, 2, 0, 0)
        h_auto_cfg.setSpacing(6)
        self.lbl_auto_preencher = QLabel(tr("🤖 <b>Auto:</b>"))
        self.lbl_auto_preencher.setToolTip(tr("Preenchimento Automático da parede selecionada."))
        self.lbl_auto_preencher.setVisible(False)
        h_auto_cfg.addWidget(self.lbl_auto_preencher)

        self.cb_auto_composicao = QComboBox()
        self.cb_auto_composicao.setMinimumWidth(0)
        self.cb_auto_composicao.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.cb_auto_composicao.setMinimumContentsLength(8)
        self.cb_auto_composicao.addItem(tr("Balcões com portas"), "portas")
        self.cb_auto_composicao.addItem(tr("Balcões + gaveteiros"), "misto")
        self.cb_auto_composicao.addItem(tr("Somente gaveteiros"), "gavetas")
        self.cb_auto_composicao.setToolTip(
            tr("Composição usada no preenchimento dos módulos inferiores.\nPara aéreos o preenchimento usa sempre armários com portas.")
        )
        self.cb_auto_composicao.setVisible(False)
        h_auto_cfg.addWidget(self.cb_auto_composicao, 1)
        l_paredes.addLayout(h_auto_cfg)

        self.btn_auto_inferiores = _compact_wall_btn(
            tr("⬇️ Inferiores"),
            tr("Gera e distribui módulos inferiores contíguos para fechar o vão informado em 'Comprimento'."),
            accent="#0284C7",
            visible=False,
        )
        self.btn_auto_inferiores.clicked.connect(self._on_auto_preencher_inferiores)

        self.btn_auto_aereos = _compact_wall_btn(
            tr("⬆️ Aéreos"),
            tr("Gera e distribui armários aéreos contíguos para fechar o vão informado em 'Comprimento'."),
            accent="#0891B2",
            visible=False,
        )
        self.btn_auto_aereos.clicked.connect(self._on_auto_preencher_aereos)
        l_paredes.addLayout(_pair_row(self.btn_auto_inferiores, self.btn_auto_aereos))

        # ── Bloco 5: Ocultar, Seccionar, Trava & Reexibir ───────────────────────
        self.btn_hide_selected_wall = _compact_wall_btn(
            tr("👁️ Ocultar Parede"),
            tr("Oculta a parede selecionada para liberar a visão interna (use 'Reexibir' para restaurar)."),
            visible=False,
        )

        def _finish_hide_wall(vp, status_msg: str) -> None:
            from ..wall.selection import WallSelectionManager
            WallSelectionManager.get_instance(vp).clear_selection()
            self._selected_wall = None
            for attr in ("btn_apply_wall", "btn_hide_selected_wall", "btn_frente_parede", "btn_split_walls"):
                w = getattr(self, attr, None)
                if w is not None:
                    w.setVisible(False)
            vp.update()
            if hasattr(vp, "flash_status"):
                vp.flash_status(status_msg)

        def _on_click_hide_selected_wall():
            vp = self._get_viewport()
            w = self._active_selected_wall()
            if not (w and vp and hasattr(vp, "history")):
                return
            from core.history import HideCommand
            from ..wall.builder import SplitWallGroupCommand, WallBuilderTool

            params = getattr(w, "ext", {}).get("trazomob_wall") if isinstance(getattr(w, "ext", None), dict) else {}
            is_seg = bool(params.get("is_segmented", False))
            pts_count = len(params.get("pontos", []))

            if is_seg or pts_count <= 2:
                vp.history.execute(HideCommand([w], hidden=True))
                if hasattr(vp, "scene"):
                    vp.scene.selection.discard(w)
                _finish_hide_wall(vp, f"👁️ {w.name} ocultada (use 'Reexibir' para mostrar novamente).")
                return

            seg_idx = self.cb_parede_segmento.currentData() if hasattr(self, "cb_parede_segmento") else None
            if seg_idx is None:
                seg_idx = params.get("selected_segment", 0)

            subs = WallBuilderTool.split_wall_group_into_segments(w)
            if len(subs) > 1:
                vp.history.execute(SplitWallGroupCommand(w, subs))
                target_sub = next(
                    (s for s in subs if s.ext.get("trazomob_wall", {}).get("segment_index") == int(seg_idx)),
                    subs[0],
                )
                vp.history.execute(HideCommand([target_sub], hidden=True))
                if hasattr(vp, "scene"):
                    vp.scene.selection.discard(w)
                _finish_hide_wall(vp, f"👁️ Parede #{int(seg_idx) + 1} seccionada e ocultada com sucesso!")

        self.btn_hide_selected_wall.clicked.connect(_on_click_hide_selected_wall)

        self.btn_split_walls = _compact_wall_btn(
            tr("✂️ Seccionar"),
            tr("Divide o bloco contínuo de paredes em paredes individuais para ocultar, mover ou editar cada uma separadamente."),
            accent="#0284C7",
            visible=False,
        )

        def _on_click_split_walls():
            vp = self._get_viewport()
            w = self._active_selected_wall()
            if w and vp and hasattr(vp, "history"):
                from ..wall.builder import SplitWallGroupCommand, WallBuilderTool
                subs = WallBuilderTool.split_wall_group_into_segments(w)
                if len(subs) > 1:
                    vp.history.execute(SplitWallGroupCommand(w, subs))
                    if hasattr(vp, "scene"):
                        vp.scene.selection = {subs[0]}
                    self.load_wall(subs[0])
                    vp.update()
                    if hasattr(vp, "flash_status"):
                        vp.flash_status(f"✂️ Bloco dividido com sucesso em {len(subs)} paredes individuais independentes!")

        self.btn_split_walls.clicked.connect(_on_click_split_walls)
        l_paredes.addLayout(_pair_row(self.btn_hide_selected_wall, self.btn_split_walls))

        self.btn_lock_walls_floor = _compact_wall_btn(
            tr("🔒 Trava: ATIVA"),
            tr("Impede mover paredes e piso acidentalmente. Snaps, cotas e medições continuam funcionando normalmente!"),
            variant="lock",
            checkable=True,
            checked=True,
        )
        self.btn_lock_walls_floor.clicked.connect(self._toggle_walls_floor_lock)

        self.btn_unhide_all_walls = _compact_wall_btn(
            tr("👁️ Reexibir Tudo"),
            tr("Reexibe todas as paredes e tetos que estavam ocultos na cena."),
        )

        def _on_click_unhide_all():
            vp = self._get_viewport()
            if vp and hasattr(vp, "scene") and hasattr(vp, "history"):
                arch_to_show = []
                for g in getattr(vp.scene, "groups", []):
                    ext = getattr(g, "ext", {})
                    if isinstance(ext, dict) and ("trazomob_wall" in ext or "trazomob_ceiling" in ext):
                        if getattr(g, "hidden", False) or vp.scene.entity_hidden(g):
                            arch_to_show.append(g)
                if arch_to_show:
                    from core.history import HideCommand
                    vp.history.execute(HideCommand(arch_to_show, hidden=False))
                    vp.update()
                    if hasattr(vp, "flash_status"):
                        vp.flash_status(f"👁️ {len(arch_to_show)} elemento(s) reexibido(s).")
                else:
                    if hasattr(vp, "flash_status"):
                        vp.flash_status("Nenhuma parede ou teto oculto.")

        self.btn_unhide_all_walls.clicked.connect(_on_click_unhide_all)
        l_paredes.addLayout(_pair_row(self.btn_lock_walls_floor, self.btn_unhide_all_walls))
        l_paredes.addStretch(1)

        self.scroll_paredes.setWidget(self.card_paredes)
        self.scroll_paredes.setVisible(False)
        layout.addWidget(self.scroll_paredes)

