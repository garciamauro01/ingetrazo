# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Barra de Ferramentas com Abas de Módulos (Ribbon/Dock Toolbar) para TrazoMob.

Exibe os módulos de marcenaria e design de interiores agrupados por abas temáticas:
- Cozinha (Inferiores, Aéreos, Torres)
- Dormitório / Quarto (Roupeiros, Cabideiros, Sapateiras)
- Banheiro (Gabinetes suspensos, Nichos)
- Nichos & Estantes
- Marmoraria & Pias
- Peças Avulsas

Permite inserir o módulo diretamente na cena no ponto correto (ao lado do anterior ou na origem)
em um único clique, abrindo imediatamente seus parâmetros na barra lateral.
"""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QPoint, QSize, Qt, QTimer, Signal, QMimeData
from PySide6.QtGui import (QDrag, QIcon, QKeySequence, QMouseEvent, QPixmap,
                           QVector3D)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListView,
    QMenu,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.group import Group, iter_placements
from core.history import SnapshotImport
from ..integrations import platform as host
from ..builders.cabinet import CabinetBuilder
from ..domain.catalog import MODULE_CATALOG, USER_MODULE_CATEGORY, modulos_usuario
from ..domain.i18n import tr
from ..ui.icons import get_module_thumbnail


logger = logging.getLogger("trazomob.module_ribbon")

#: Tamanho das miniaturas da aba da biblioteca do usuário (uma única linha).
LIBRARY_ICON = 52
LIBRARY_CELL = QSize(LIBRARY_ICON + 28, LIBRARY_ICON + 38)


# Re-exporta utilitários geométricos canônicos movidos para module_geometry.py
from ..domain.module_geometry import (
    get_module_carcass_bounds,
    get_module_back_normal,
    preserve_module_back_alignment,
    get_reference_module,
    get_module_category,
    is_compatible_category,
    build_default_module_params,
)


class ModuleButton(QToolButton):
    """Botão visual moderno de módulo com miniatura vetorial, título, tooltip rica e seletor dinâmico de variantes."""

    def __init__(self, mod_data: dict[str, Any], on_clicked, ribbon=None, parent=None):
        super().__init__(parent)
        self.mod_data = dict(mod_data)
        self.on_clicked = on_clicked
        self.ribbon = ribbon

        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setIcon(get_module_thumbnail(mod_data["id"]))
        self.setIconSize(QSize(52, 52))
        self.setFixedSize(100, 84)

        nome = tr(mod_data.get("nome", ""))
        # Trunca nome longo para 2 linhas legíveis no botão
        if len(nome) > 18:
            parts = nome.split(" (")[0]
            display_name = parts if len(parts) <= 18 else (parts[:16] + "…")
        else:
            display_name = nome

        self.setText(display_name)
        dim_info = f"{self.mod_data.get('largura', 0)} x {self.mod_data.get('altura', 0)} x {self.mod_data.get('profundidade', 0)} mm"
        desc = tr(mod_data.get("desc", ""))
        self.setToolTip(f"<b>{nome}</b><br>📏 {dim_info}<br>💡 {desc}<br><i>Duplo clique ou arraste para inserir na cena 3D</i>")
        self.setStatusTip(f"Duplo clique ou arraste para inserir {nome} ({dim_info})")

        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            "QToolButton {"
            "  border: 1px solid palette(midlight);"
            "  border-radius: 6px;"
            "  background-color: palette(base);"
            "  color: palette(text);"
            "  font-size: 11px;"
            "  font-weight: 500;"
            "  padding: 4px;"
            "}"
            "QToolButton:hover {"
            "  border: 1.5px solid palette(highlight);"
            "  background-color: palette(alternate-base);"
            "}"
            "QToolButton:focus {"
            "  border: 2px solid palette(highlight);"
            "  background-color: palette(alternate-base);"
            "}"
            "QToolButton:pressed {"
            "  background-color: palette(highlight);"
            "  color: palette(highlighted-text);"
            "}"
        )

        # Se houver opções predefinidas de largura (ex.: Porta Giro 70, 80, 90 cm):
        self.combo_options = mod_data.get("largura_options", [])
        self.combo_variante = None
        if self.combo_options:
            from PySide6.QtWidgets import QComboBox
            self.combo_variante = QComboBox(self)
            for opt in self.combo_options:
                self.combo_variante.addItem(opt.get("label", str(opt.get("largura"))), opt.get("largura"))

            # Seleciona a opção que coincide com a largura padrão
            cur_w = self.mod_data.get("largura", 800)
            for idx, opt in enumerate(self.combo_options):
                if opt.get("largura") == cur_w:
                    self.combo_variante.setCurrentIndex(idx)
                    break

            self.combo_variante.setFixedSize(56, 18)
            self.combo_variante.move(40, 4)
            self.combo_variante.setToolTip("Selecione a largura da porta (70, 80 ou 90 cm)")
            self.combo_variante.setStyleSheet(
                "QComboBox {"
                "  font-size: 9px;"
                "  font-weight: bold;"
                "  background-color: #2563EB;"
                "  color: #FFFFFF;"
                "  border: 1px solid #1D4ED8;"
                "  border-radius: 3px;"
                "  padding: 0px 2px;"
                "}"
                "QComboBox::drop-down {"
                "  subcontrol-origin: padding;"
                "  subcontrol-position: top right;"
                "  width: 10px;"
                "  border-left: 1px solid #1D4ED8;"
                "}"
                "QComboBox QAbstractItemView {"
                "  background-color: #1E293B;"
                "  color: #FFFFFF;"
                "  selection-background-color: #2563EB;"
                "}"
            )
            self.combo_variante.currentIndexChanged.connect(self._on_combo_variante_changed)

    def _on_combo_variante_changed(self, index: int) -> None:
        if not self.combo_options or not (0 <= index < len(self.combo_options)):
            return
        opt = self.combo_options[index]
        new_w = opt.get("largura", self.mod_data.get("largura"))
        self.mod_data["largura"] = new_w
        dim_info = f"{new_w} x {self.mod_data.get('altura', 0)} x {self.mod_data.get('profundidade', 0)} mm"
        nome = self.mod_data.get("nome", "")
        self.setToolTip(f"<b>{nome} ({opt.get('label')})</b><br>📏 {dim_info}<br>💡 {self.mod_data.get('desc', '')}<br><i>Duplo clique para inserir na cena 3D</i>")
        self.setStatusTip(f"Duplo clique para inserir {nome} ({dim_info})")

        # 1. Se houver frame de posicionamento armado na parede, atualiza seu tamanho imediatamente no 3D:
        from ..wall.selection import WallSelectionManager
        ribbon_vp = self.ribbon.viewport if self.ribbon is not None else None
        wall_mgr = WallSelectionManager.get_instance(ribbon_vp)
        if wall_mgr.active_placement_slot is not None:
            mod_w = float(new_w) / 1000.0
            mod_p = float(self.mod_data.get("profundidade", 550.0)) / 1000.0
            wall_mgr.update_frame_dimensions(mod_w, mod_p)

        # 2. Se houver uma porta/esquadria correspondente selecionada na cena, reconfigura dinamicamente na hora!
        if self.ribbon is not None and hasattr(self.ribbon, "sidebar_panel") and self.ribbon.sidebar_panel is not None:
            sidebar = self.ribbon.sidebar_panel
            sel_mod = (
                sidebar._active_selected_module()
                if hasattr(sidebar, "_active_selected_module")
                else (getattr(sidebar, "_selected_module", None) or sidebar.find_selected_module())
            )
            if sel_mod is not None:
                m_tipo = str(getattr(sel_mod, "ext", {}).get("trazomob_module", {}).get("tipo", ""))
                if "porta" in m_tipo.lower() or "janela" in m_tipo.lower():
                    if hasattr(sidebar, "sp_largura"):
                        sidebar.sp_largura.setValue(int(new_w))
                    if hasattr(sidebar, "_apply_changes_to_selected"):
                        sidebar._apply_changes_to_selected()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.position().toPoint()
            # 1. Clique simples: se houver frame armado, atualiza seu tamanho imediatamente no 3D!
            from ..wall.selection import WallSelectionManager
            ribbon_vp = self.ribbon.viewport if self.ribbon is not None else None
            wall_mgr = WallSelectionManager.get_instance(ribbon_vp)
            if wall_mgr.active_placement_slot is not None:
                mod_w = float(self.mod_data.get("largura", 800.0)) / 1000.0
                mod_p = float(self.mod_data.get("profundidade", 550.0)) / 1000.0
                wall_mgr.update_frame_dimensions(mod_w, mod_p)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.LeftButton and hasattr(self, "_drag_start_pos") and self._drag_start_pos is not None:
            dist = (event.position().toPoint() - self._drag_start_pos).manhattanLength()
            from PySide6.QtWidgets import QApplication
            if dist >= QApplication.startDragDistance():
                self._start_drag()
                return
        super().mouseMoveEvent(event)

    def _start_drag(self) -> None:
        self._drag_start_pos = None
        from ..interaction.drag_drop_handler import TRAZOMOB_MIME_MODULE
        if getattr(self, "combo_variante", None) is not None and getattr(self, "combo_options", None):
            idx = self.combo_variante.currentIndex()
            if 0 <= idx < len(self.combo_options):
                self.mod_data["largura"] = self.combo_options[idx].get("largura", self.mod_data.get("largura"))

        mime = QMimeData()
        payload = json.dumps(dict(self.mod_data)).encode("utf-8")
        mime.setData(TRAZOMOB_MIME_MODULE, payload)

        drag = QDrag(self)
        drag.setMimeData(mime)
        pixmap = self.icon().pixmap(52, 52)
        if not pixmap.isNull():
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
        drag.exec(Qt.CopyAction)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            if getattr(self, "combo_variante", None) is not None and getattr(self, "combo_options", None):
                idx = self.combo_variante.currentIndex()
                if 0 <= idx < len(self.combo_options):
                    self.mod_data["largura"] = self.combo_options[idx].get("largura", self.mod_data.get("largura"))
            self.on_clicked(dict(self.mod_data))
            event.accept()
            return
        super().mouseDoubleClickEvent(event)



class TrazoMobModuleRibbonBar(QToolBar):

    """Barra de ferramentas superior em abas que organiza os móveis por categoria/ambiente.

    Abre logo abaixo da barra principal ao clicar em 'Módulos', permitindo navegar e
    inserir balcões, aéreos, torres, quartos, banheiros e marmorarias diretamente na cena.
    """

    @property
    def viewport(self):
        return host.active_viewport(
            window=getattr(self, "main_window", None),
            viewport=getattr(self, "_fallback_viewport", None),
        )

    @viewport.setter
    def viewport(self, vp) -> None:
        if vp is not None:
            self._fallback_viewport = vp

    def __init__(self, main_window, viewport, sidebar_panel, parent=None):
        parent_widget = parent if isinstance(parent, QWidget) else (main_window if isinstance(main_window, QWidget) else None)
        super().__init__(tr("Catálogo de Módulos (TrazoMob)"), parent_widget)
        self.setObjectName("TrazoMobModuleRibbonBar")
        self.main_window = main_window
        self._fallback_viewport = viewport
        self.sidebar_panel = sidebar_panel
        if self.viewport is not None:
            setattr(self.viewport, "_trazomob_ribbon", self)

        self.setMovable(True)
        self.setFloatable(False)

        # Widget central com abas
        self.container = QWidget()
        layout = QHBoxLayout(self.container)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        # QTabWidget principal compacto para os ambientes
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet(
            "QTabWidget::pane { border: 1px solid palette(midlight); border-radius: 6px; background-color: palette(base); }"
            "QTabBar::tab {"
            "  padding: 5px 12px;"
            "  font-weight: bold;"
            "  font-size: 11px;"
            "  border-top-left-radius: 4px;"
            "  border-top-right-radius: 4px;"
            "  margin-right: 2px;"
            "  background-color: palette(button);"
            "  color: palette(button-text);"
            "}"
            "QTabBar::tab:selected {"
            "  background-color: palette(highlight);"
            "  color: palette(highlighted-text);"
            "}"
            "QTabBar::tab:hover:!selected {"
            "  background-color: palette(midlight);"
            "}"
        )

        self._populate_tabs()
        layout.addWidget(self.tabs, stretch=1)

        # Botão Rápido de Bancada sobre Balcões no Ribbon Superior
        self.btn_ribbon_bancada = QPushButton(tr("🪨 Encaixar Bancada"))
        self.btn_ribbon_bancada.setToolTip(tr("Cria e encaixa uma bancada contínua de pedra sobre os balcões da parede selecionada"))
        self.btn_ribbon_bancada.setFixedHeight(32)
        self.btn_ribbon_bancada.setStyleSheet(
            "QPushButton { background-color: #0284C7; color: white; font-weight: bold; border-radius: 4px; padding: 4px 10px; font-size: 11px; }"
            "QPushButton:hover { background-color: #0369A1; }"
        )
        def _on_click_ribbon_bancada():
            if self.sidebar_panel is not None and hasattr(self.sidebar_panel, "_on_encaixar_bancada_sobre_balcoes"):
                self.sidebar_panel._on_encaixar_bancada_sobre_balcoes()
        self.btn_ribbon_bancada.clicked.connect(_on_click_ribbon_bancada)
        layout.addWidget(self.btn_ribbon_bancada)

        # Botão Elevação 2D com Cotas no Ribbon Superior
        self.btn_ribbon_elevacao = QPushButton(tr("📐 Elevação 2D"))
        self.btn_ribbon_elevacao.setToolTip(tr("Abre a elevação técnica ortogonal 2D com cotas milimétricas da parede e módulos"))
        self.btn_ribbon_elevacao.setFixedHeight(32)
        self.btn_ribbon_elevacao.setStyleSheet(
            "QPushButton { background-color: #4338CA; color: white; font-weight: bold; border-radius: 4px; padding: 4px 10px; font-size: 11px; }"
            "QPushButton:hover { background-color: #3730A3; }"
        )
        def _on_click_ribbon_elevacao():
            if self.sidebar_panel is not None and hasattr(self.sidebar_panel, "_on_abrir_elevacao_parede"):
                self.sidebar_panel._on_abrir_elevacao_parede()
            else:
                from ..wall.elevation_dialog import WallElevationDialog
                dlg = WallElevationDialog(viewport=self.viewport, parent=self.window())
                dlg.exec()
        self.btn_ribbon_elevacao.clicked.connect(_on_click_ribbon_elevacao)
        layout.addWidget(self.btn_ribbon_elevacao)

        # Botão Fechamento / Arremate de Canto no Ribbon Superior
        self.btn_ribbon_arremate = QPushButton(tr("🧩 Arremate de Canto"))
        self.btn_ribbon_arremate.setToolTip(tr("Preenche a folga residual entre o último módulo e o final da parede com uma régua de testeira e sarrafo"))
        self.btn_ribbon_arremate.setFixedHeight(32)
        self.btn_ribbon_arremate.setStyleSheet(
            "QPushButton { background-color: #0D9488; color: white; font-weight: bold; border-radius: 4px; padding: 4px 10px; font-size: 11px; }"
            "QPushButton:hover { background-color: #0F766E; }"
        )
        def _on_click_ribbon_arremate():
            if self.sidebar_panel is not None and hasattr(self.sidebar_panel, "_on_fechar_vao_canto"):
                self.sidebar_panel._on_fechar_vao_canto()
        self.btn_ribbon_arremate.clicked.connect(_on_click_ribbon_arremate)
        layout.addWidget(self.btn_ribbon_arremate)



        # Botão Fechar barra
        btn_close = QPushButton("✕")
        btn_close.setToolTip(tr("Fechar barra de módulos"))
        btn_close.setFixedSize(24, 24)
        btn_close.setStyleSheet(
            "QPushButton { border: none; font-weight: bold; border-radius: 12px; color: palette(text); }"
            "QPushButton:hover { background-color: palette(dark); color: #EF4444; }"
        )
        btn_close.clicked.connect(self.hide)
        layout.addWidget(btn_close)

        self.addWidget(self.container)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Alguém pode ter importado um componente enquanto a barra estava
        # oculta; a revisão do manifesto diz quando redesenhar a biblioteca.
        self.refresh_user_library()

    def _create_module_scroll_area(self, items: list[dict[str, Any]]) -> QScrollArea:
        """Cria uma área horizontal com scroll de botões de módulos."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(94)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        h_layout = QHBoxLayout(content)
        h_layout.setContentsMargins(4, 2, 4, 2)
        h_layout.setSpacing(6)
        h_layout.setAlignment(Qt.AlignLeft)

        for mod_data in items:
            btn = ModuleButton(mod_data, on_clicked=self.insert_module_into_scene, ribbon=self, parent=content)
            h_layout.addWidget(btn)

        scroll.setWidget(content)
        return scroll

    def _populate_tabs(self):
        """Preenche as abas principais e sub-abas categorizadas (ex: Cozinha -> Inferiores, Aéreos, Torres)."""
        # Estrutura: Ambiente -> { Subcategoria: [itens] }
        env_map: dict[str, dict[str, list[dict[str, Any]]]] = {
            "🍳 Cozinha": {
                "Balcões Inferiores": [],
                "Aéreos & Suspensos": [],
                "Torres de Eletros": [],
            },
            "🛏️ Dormitório": {
                "Roupeiros & Armários": [],
                "Camas": [],
            },
            "🚿 Banheiro": {
                "Gabinetes & Pias": [],
            },
            "📦 Nichos & Prateleiras": {
                "Nichos & Estantes": [],
            },
            "🪨 Marmoraria": {
                "Bancadas & Tampos": [],
            },
            "🚪 Portas & Janelas": {
                "Portas": [],
                "Janelas": [],
            },
            "📺 Racks": {
                "Racks": [],
            },
            "📐 Peças Avulsas": {
                "Peças": [],
            },
        }

        for cat_name, items in MODULE_CATALOG.items():
            if "Cozinha — Inferiores" in cat_name:
                env_map["🍳 Cozinha"]["Balcões Inferiores"].extend(items)
            elif "Cozinha — Aéreos" in cat_name:
                env_map["🍳 Cozinha"]["Aéreos & Suspensos"].extend(items)
            elif "Cozinha — Torres" in cat_name:
                env_map["🍳 Cozinha"]["Torres de Eletros"].extend(items)
            elif "Camas" in cat_name:
                env_map["🛏️ Dormitório"]["Camas"].extend(items)
            elif "Armário" in cat_name or "Dormitório" in cat_name:
                env_map["🛏️ Dormitório"]["Roupeiros & Armários"].extend(items)
            elif "Banheiro" in cat_name:
                env_map["🚿 Banheiro"]["Gabinetes & Pias"].extend(items)
            elif "Nicho" in cat_name:
                env_map["📦 Nichos & Prateleiras"]["Nichos & Estantes"].extend(items)
            elif "Marmoraria" in cat_name:
                env_map["🪨 Marmoraria"]["Bancadas & Tampos"].extend(items)
            elif "Rack" in cat_name:
                env_map["📺 Racks"]["Racks"].extend(items)
            elif "Portas" in cat_name or "Janelas" in cat_name:
                for it in items:
                    if "porta" in it.get("id", ""):
                        env_map["🚪 Portas & Janelas"]["Portas"].append(it)
                    else:
                        env_map["🚪 Portas & Janelas"]["Janelas"].append(it)
            else:
                env_map["📐 Peças Avulsas"]["Peças"].extend(items)

        # Módulos pessoais salvos pelo usuário aparecem numa aba dedicada.
        _user_mods = modulos_usuario()
        if _user_mods:
            env_map[USER_MODULE_CATEGORY] = {"Meus Módulos": _user_mods}

        subtab_style = (
            "QTabWidget::pane { border: none; background-color: transparent; }"
            "QTabBar::tab {"
            "  padding: 3px 10px;"
            "  font-size: 10px;"
            "  font-weight: 600;"
            "  border-radius: 4px;"
            "  margin-right: 4px;"
            "  background-color: palette(button);"
            "  color: palette(button-text);"
            "}"
            "QTabBar::tab:selected {"
            "  background-color: palette(highlight);"
            "  color: palette(highlighted-text);"
            "}"
            "QTabBar::tab:hover:!selected {"
            "  background-color: palette(midlight);"
            "}"
        )

        for env_label, subcategories in env_map.items():
            valid_subcats = {k: v for k, v in subcategories.items() if v}
            if not valid_subcats:
                continue

            # Se houver mais de uma subcategoria (como na Cozinha: Inferiores, Aéreos, Torres),
            # renderiza um QTabWidget de sub-abas interno na parte inferior!
            if len(valid_subcats) > 1:
                sub_tabs = QTabWidget()
                sub_tabs.setTabPosition(QTabWidget.South)
                sub_tabs.setDocumentMode(True)
                sub_tabs.setStyleSheet(subtab_style)
                for sub_label, sub_items in valid_subcats.items():
                    sub_tabs.addTab(self._create_module_scroll_area(sub_items), tr(sub_label))
                self.tabs.addTab(sub_tabs, tr(env_label))
            else:
                # Subcategoria única direta
                sub_items = next(iter(valid_subcats.values()))
                self.tabs.addTab(self._create_module_scroll_area(sub_items), tr(env_label))


        # ── ABA DECORAÇÃO (CARREGADA SOB DEMANDA AO CLICAR NA ABA) ──────
        self._decor_populated = False
        self._decor_subtab_style = subtab_style
        self._decor_placeholder = QWidget()
        self._decor_tab_idx = self.tabs.addTab(self._decor_placeholder, tr("🎨 Decoração"))
        self.tabs.currentChanged.connect(self._on_main_tab_changed)

    def _on_main_tab_changed(self, idx: int) -> None:
        if idx == getattr(self, "_decor_tab_idx", -1):
            if not getattr(self, "_decor_populated", False):
                self._decor_populated = True
                self._populate_decoration_tab()
            else:
                self.refresh_user_library()

    def _populate_decoration_tab(self) -> None:
        """Substitui o conteúdo da aba Decoração pelo navegador da biblioteca
        do usuário: categorias em abas, marcas em sub-abas e um grid de
        miniaturas. Nenhum dado vem da biblioteca nativa do IngeTrazo."""
        lay = QVBoxLayout(self._decor_placeholder)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        self._library_host = QWidget()
        self._library_host_lay = QVBoxLayout(self._library_host)
        self._library_host_lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._library_host, 1)

        action_row = QHBoxLayout()
        self._library_status = QLabel("")
        action_row.addWidget(self._library_status, 1)
        for label, slot in (
            (tr("Import model…"), self._import_user_component),
            (tr("Add folder…"), self._add_user_folder),
            (tr("Manage…"), self._open_user_library),
        ):
            button = QPushButton(label)
            button.clicked.connect(slot)
            action_row.addWidget(button)

        from views.user_library_transfer import export_library, import_library

        transfer = QPushButton(tr("Transfer…"))
        transfer_menu = QMenu(transfer)
        transfer_menu.addAction(
            tr("Export library…"),
            lambda: export_library(self, after=self._refresh_after_transfer))
        transfer_menu.addAction(
            tr("Import library…"),
            lambda: import_library(self, after=self._refresh_after_transfer))
        transfer.setMenu(transfer_menu)
        action_row.addWidget(transfer)

        insert = QPushButton(tr("Insert"))
        insert.setDefault(True)
        insert.clicked.connect(self._insert_selected_user_component)
        action_row.addWidget(insert)
        lay.addLayout(action_row)

        self._library_lists: list[QListWidget] = []
        self._library_pending: list[dict] = []
        self._library_queued: set[str] = set()
        self._library_failed: set[str] = set()
        self._library_thumb_timer = QTimer(self)
        self._library_thumb_timer.timeout.connect(self._fill_library_thumbs)
        self._library_thumb_timer.start(150)
        self._library_selected = {"categoria": "", "marca": ""}
        self.refresh_user_library(force=True)

    def refresh_user_library(self, force: bool = False) -> None:
        """Reconstrói as abas quando o manifesto do usuário muda."""
        if not hasattr(self, "_library_host"):
            return
        from core import user_library

        try:
            revision = user_library.revision()
        except Exception as exc:  # a barra nunca derruba o app por isso
            logger.debug("biblioteca do usuário indisponível: %s", exc)
            return
        if not force and revision == getattr(self, "_library_revision", None):
            return
        self._library_revision = revision

        self._library_pending.clear()
        self._library_queued.clear()
        self._library_failed.clear()
        self._library_lists = []
        selected = dict(getattr(self, "_library_selected",
                                {"categoria": "", "marca": ""}))

        while self._library_host_lay.count():
            item = self._library_host_lay.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        entries = user_library.index()
        self._library_entries = entries
        self._library_selected = {"categoria": "", "marca": ""}
        no_category = tr("Sem categoria")
        no_brand = tr("Sem marca")

        by_category: dict[str, list[dict]] = {}
        for entry in entries:
            category = str(entry.get("categoria") or "").strip() or no_category
            by_category.setdefault(category, []).append(entry)

        category_choices = [("", tr("Todas"))]
        category_choices.extend(
            (value, value) for value in sorted(by_category, key=str.casefold)
            if value != no_category)
        if no_category in by_category:
            category_choices.append((no_category, no_category))
        self._library_category_choices = category_choices

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        self._decor_tabs = tabs
        self._library_brand_values: dict[str, list[str]] = {}

        for category, category_label in category_choices:
            category_entries = (entries if category == ""
                                else by_category.get(category, []))
            by_brand: dict[str, list[dict]] = {}
            for entry in category_entries:
                brand = str(entry.get("marca") or "").strip() or no_brand
                by_brand.setdefault(brand, []).append(entry)

            brand_choices = [("", tr("Todas"))]
            brand_choices.extend(
                (value, value) for value in sorted(by_brand, key=str.casefold)
                if value != no_brand)
            if no_brand in by_brand:
                brand_choices.append((no_brand, no_brand))

            sub_tabs = QTabWidget()
            sub_tabs.setTabPosition(QTabWidget.South)
            sub_tabs.setDocumentMode(True)
            sub_tabs.setStyleSheet(self._decor_subtab_style)
            brand_values: list[str] = []
            for brand, brand_label in brand_choices:
                brand_values.append(brand)
                brand_entries = (category_entries if brand == ""
                                 else by_brand.get(brand, []))
                sub_tabs.addTab(self._make_library_page(brand_entries),
                                brand_label)
            self._library_brand_values[category] = brand_values
            sub_tabs.currentChanged.connect(
                lambda _idx, _c=category: self._library_tab_selected(_c))
            tabs.addTab(sub_tabs, category_label)

        tabs.currentChanged.connect(self._library_category_selected)
        self._library_host_lay.addWidget(tabs)
        self._library_host.setMinimumHeight(180)

        cat_values = [value for value, _label in category_choices]
        try:
            cat_index = cat_values.index(selected.get("categoria", ""))
        except ValueError:
            cat_index = 0
        tabs.setCurrentIndex(cat_index)
        sub_tabs = tabs.widget(cat_index)
        if isinstance(sub_tabs, QTabWidget):
            brands = self._library_brand_values.get(cat_values[cat_index], [])
            try:
                brand_index = brands.index(selected.get("marca", ""))
            except ValueError:
                brand_index = 0
            sub_tabs.setCurrentIndex(brand_index)

        self._update_library_status()
        QTimer.singleShot(0, self._fill_library_thumbs)

    def _library_category_selected(self, index: int) -> None:
        tabs = getattr(self, "_decor_tabs", None)
        if tabs is None or not (0 <= index < tabs.count()):
            return
        values = [value for value, _label in getattr(
            self, "_library_category_choices", [])]
        self._library_selected["categoria"] = (
            values[index] if index < len(values) else "")
        self._library_selected["marca"] = ""
        self._update_library_status()

    def _library_tab_selected(self, category: str) -> None:
        tabs = getattr(self, "_decor_tabs", None)
        if tabs is None:
            return
        values = self._library_brand_values.get(category, [])
        sub_tabs = tabs.currentWidget()
        index = sub_tabs.currentIndex() if isinstance(sub_tabs, QTabWidget) else 0
        self._library_selected["categoria"] = category
        self._library_selected["marca"] = (
            values[index] if 0 <= index < len(values) else "")
        self._update_library_status()

    def _update_library_status(self) -> None:
        if not hasattr(self, "_library_status"):
            return
        total = len(getattr(self, "_library_entries", []))
        visible = 0
        grid = self._current_library_grid()
        if grid is not None:
            visible = grid.count()
        self._library_status.setText(
            tr("{n} of {total} components", n=visible, total=total))

    def _make_library_page(self, entries: list[dict]) -> QWidget:
        from core import user_library
        from views import library_grid

        page = QWidget()
        page_lay = QVBoxLayout(page)
        page_lay.setContentsMargins(4, 4, 4, 4)
        grid = QListWidget()
        library_grid.configure(grid, icon=LIBRARY_ICON, grid=LIBRARY_CELL)
        grid.setFlow(QListView.LeftToRight)
        grid.setWrapping(False)
        grid.setUniformItemSizes(True)
        grid.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        grid.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        grid.setFixedHeight(LIBRARY_CELL.height() + 4)
        grid.itemDoubleClicked.connect(
            lambda _item, _g=grid: self._insert_selected_user_component(_g))
        for entry in entries:
            item = QListWidgetItem(
                entry.get("nombre") or entry.get("id", "?"))
            item.setData(Qt.UserRole, entry)
            item.setToolTip(self._library_tooltip(entry))
            thumb = user_library.thumbnail(entry)
            if thumb is not None:
                pixmap = QPixmap(str(thumb))
                if not pixmap.isNull():
                    item.setIcon(QIcon(pixmap))
            grid.addItem(item)
        self._library_lists.append(grid)
        page_lay.addWidget(grid)
        return page

    def _library_tooltip(self, entry: dict) -> str:
        from core import user_library

        parts = [str(entry.get("nombre") or "")]
        for key in ("marca", "modelo"):
            if entry.get(key):
                parts.append(str(entry[key]))
        cm = entry.get("cm") or ()
        if len(cm) == 3:
            parts.append("%g × %g × %g cm" % tuple(cm))
        if user_library.missing(entry):
            parts.append(tr("File missing"))
        return " · ".join(part for part in parts if part)

    def _current_library_grid(self) -> QListWidget | None:
        tabs = getattr(self, "_decor_tabs", None)
        if tabs is None:
            return None
        sub_tabs = tabs.currentWidget()
        page = (sub_tabs.currentWidget() if isinstance(sub_tabs, QTabWidget)
                else sub_tabs)
        if page is None:
            return None
        for grid in page.findChildren(QListWidget):
            return grid
        return None

    def _insert_selected_user_component(self, grid=None) -> None:
        grid = grid if grid is not None else self._current_library_grid()
        item = grid.currentItem() if grid is not None else None
        entry = item.data(Qt.UserRole) if item is not None else None
        if not isinstance(entry, dict) or not entry:
            return
        host.insert_user_component(self.main_window, entry)

    def _fill_library_thumbs(self) -> None:
        from core import user_library

        for grid in list(getattr(self, "_library_lists", [])):
            rect = grid.viewport().rect()
            if rect.isEmpty():
                continue
            for index in range(grid.count()):
                item = grid.item(index)
                if item is None or not rect.intersects(
                        grid.visualItemRect(item)) or not item.icon().isNull():
                    continue
                entry = item.data(Qt.UserRole) or {}
                thumb = user_library.thumbnail(entry)
                if thumb is not None:
                    pixmap = QPixmap(str(thumb))
                    if not pixmap.isNull():
                        item.setIcon(QIcon(pixmap))
                        continue
                ident = str(entry.get("id") or "")
                if (not ident or ident in self._library_failed
                        or ident in self._library_queued):
                    continue
                if user_library.missing(entry):
                    self._library_failed.add(ident)
                    continue
                self._library_queued.add(ident)
                self._library_pending.append(entry)
        if self._library_pending:
            QTimer.singleShot(0, self._make_one_library_thumb)

    def _make_one_library_thumb(self) -> None:
        if not self._library_pending:
            return
        from views import component_loader

        entry = self._library_pending.pop(0)
        ident = str(entry.get("id") or "")
        self._library_status.setText(
            tr("Drawing a preview of {name}…",
               name=entry.get("nombre", "")))
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            loaded = component_loader.load_component(
                entry, thumbnail_size=128)
        except Exception as exc:  # noqa: BLE001 - um modelo ruim não trava a aba
            logger.debug("falha ao gerar miniatura de %s: %s", ident, exc)
            loaded = None
        finally:
            QApplication.restoreOverrideCursor()
        if loaded is None:
            self._library_failed.add(ident)
        else:
            self._reload_library_icon(ident)
        self._library_queued.discard(ident)
        if self._library_pending:
            QTimer.singleShot(0, self._make_one_library_thumb)
        else:
            self._update_library_status()

    def _reload_library_icon(self, ident: str) -> None:
        from core import user_library

        thumb = user_library.thumbnail(ident)
        if thumb is None:
            return
        pixmap = QPixmap(str(thumb))
        if pixmap.isNull():
            return
        for grid in list(getattr(self, "_library_lists", [])):
            for index in range(grid.count()):
                item = grid.item(index)
                if (item is not None
                        and str((item.data(Qt.UserRole) or {}).get("id"))
                        == ident):
                    item.setIcon(QIcon(pixmap))

    def _refresh_after_transfer(self) -> None:
        self.refresh_user_library(force=True)

    def _open_user_library(self, brand: str | None = None) -> None:
        host.open_user_library(self.main_window, brand)
        self.refresh_user_library(force=True)

    def _import_user_component(self) -> None:
        host.import_user_component(self.main_window)
        self.refresh_user_library(force=True)

    def _add_user_folder(self) -> None:
        from views import file_dialogs

        folder = file_dialogs.getExistingDirectory(
            self, tr("Add component folder"))
        if not folder:
            return
        answer = QMessageBox.question(
            self, tr("Add component folder"),
            tr("Include subfolders?"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            from core import user_library
            added = user_library.add_folder(
                folder, recursive=answer == QMessageBox.Yes)
        except Exception as exc:  # noqa: BLE001
            logger.debug("falha ao indexar pasta: %s", exc)
            added = []
        finally:
            QApplication.restoreOverrideCursor()
        QMessageBox.information(
            self, tr("Add component folder"),
            tr("{n} components indexed from {folder}",
               n=len(added), folder=folder))
        self.refresh_user_library(force=True)

    def insert_decoration_into_scene(self, item_data: dict[str, Any]):
        """Compatibilidade com objetos nativos e arrastar/soltar antigos."""
        tipo = item_data.get("tipo")
        if tipo == "native_3d":
            key = item_data.get("key", "")
            host.insert_component(self.main_window, key, item_data.get("name"))
        elif tipo == "native_person":
            key = item_data.get("key", "")
            height = float(item_data.get("height", 1.75))
            host.insert_person_2d(self.main_window, f"{key}.png", height,
                                  item_data.get("name"))

    def insert_module_into_scene(
        self,
        mod_data: dict[str, Any],
        explicit_offset: Optional[tuple[float, float, float]] = None,
        explicit_rot_z: Optional[float] = None,
        explicit_wall: Optional[Any] = None,
    ):
        # Garante cópia defensiva fresca dos dados do módulo
        mod_data = dict(mod_data)

        """Insere o módulo diretamente no 3D com posicionamento inteligente e abre no editor lateral."""
        vp = self.viewport
        scene = getattr(vp, "scene", None)
        if scene is None or vp is None:
            return
        setattr(vp, "_trazomob_ribbon", self)

        params = build_default_module_params(mod_data)
        if explicit_rot_z is not None:
            params["rot_z"] = float(explicit_rot_z)

        # Se veio com offset explícito vindo do Drag & Drop:
        if explicit_offset is not None:
            new_module_group = CabinetBuilder.build_module_group(params, offset=explicit_offset)
            def apply_explicit_insert(sc):
                target_layer = getattr(new_module_group, "layer", None)
                if target_layer and hasattr(sc, "layer") and hasattr(sc, "layers"):
                    if sc.layer(target_layer) is None:
                        from core.layers import Layer
                        sc.layers.append(Layer(target_layer))
                ref_wall = explicit_wall
                if ref_wall is not None and hasattr(ref_wall, "ext") and isinstance(ref_wall.ext, dict):
                    amb_n = ref_wall.ext.get("ambiente") or ref_wall.ext.get("trazomob_wall", {}).get("ambiente")
                    pav_n = ref_wall.ext.get("pavimento") or ref_wall.ext.get("trazomob_wall", {}).get("pavimento")
                    if amb_n and hasattr(new_module_group, "ext") and isinstance(new_module_group.ext, dict):
                        new_module_group.ext["ambiente"] = amb_n
                        new_module_group.ext["pavimento"] = pav_n or "Térreo"
                sc.groups.append(new_module_group)
                sc.selection = {new_module_group}
                from ..wall.mesh_builder import WallMeshBuilder
                WallMeshBuilder.sync_scene_wall_openings(sc)

            self.viewport.history.execute(SnapshotImport(apply_explicit_insert))
            if self.sidebar_panel is not None:
                self.sidebar_panel._selected_module = new_module_group
                self.sidebar_panel.focus_panel()
                self.sidebar_panel.load_module(new_module_group)
            self.viewport.notify_scene_changed()
            self.viewport.update()
            if hasattr(self.viewport, "flash_status"):
                self.viewport.flash_status(f"✨ Módulo '{new_module_group.name}' posicionado na cena!")
            return
        ref_mod = get_reference_module(scene)
        default_z = float(mod_data.get("default_z", 0.0))
        novo_L_m = float(params["largura"]) / 1000.0

        # ── VERIFICAÇÃO DE MESMA CATEGORIA E HERANÇA DE MEDIDAS ────────
        cat_novo = get_module_category(mod_data.get("id", ""), default_z)
        is_same_cat = False
        ref_b = None
        ref_cc = {}
        if ref_mod is not None:
            ref_b = get_module_carcass_bounds(ref_mod)
            if hasattr(ref_mod, "ext") and "trazomob_module" in ref_mod.ext:
                ref_cc = ref_mod.ext["trazomob_module"]

            # Determina Z real da base do módulo de referência
            ref_z = ref_b[4] if ref_b is not None else float(ref_cc.get("offset", (0, 0, 0))[2])
            ref_tipo = ref_cc.get("tipo", getattr(ref_mod, "name", ""))
            cat_ref = get_module_category(ref_tipo, ref_z)

            # Caso especial: se o novo item for Bancada e a referência for Balcão/Inferior,
            # a bancada herda as dimensões de largura e profundidade do balcão para encaixar no topo!
            if cat_novo == "bancada" and cat_ref in ("inferior", "banheiro"):
                if ref_b is not None:
                    ref_rot = float(ref_cc.get("rot_z", 0.0)) % 360.0
                    if abs(ref_rot) < 45.0 or abs(ref_rot - 180.0) < 45.0:
                        params["largura"] = round((ref_b[1] - ref_b[0]) * 1000.0)
                        params["profundidade"] = round((ref_b[3] - ref_b[2]) * 1000.0)
                    else:
                        params["largura"] = round((ref_b[3] - ref_b[2]) * 1000.0)
                        params["profundidade"] = round((ref_b[1] - ref_b[0]) * 1000.0)
                elif "largura" in ref_cc and "profundidade" in ref_cc:
                    params["largura"] = float(ref_cc["largura"])
                    params["profundidade"] = float(ref_cc["profundidade"])
            elif is_compatible_category(cat_novo, cat_ref):
                is_same_cat = True
                # Herda profundidade da caixa anterior (do dict ou das dimensões físicas da caixa)
                if "profundidade" in ref_cc and float(ref_cc["profundidade"]) > 0:
                    params["profundidade"] = float(ref_cc["profundidade"])
                elif ref_b is not None:
                    ref_rot = float(ref_cc.get("rot_z", 0.0)) % 360.0
                    if abs(ref_rot) < 45.0 or abs(ref_rot - 180.0) < 45.0:
                        params["profundidade"] = round((ref_b[3] - ref_b[2]) * 1000.0)
                    else:
                        params["profundidade"] = round((ref_b[1] - ref_b[0]) * 1000.0)

                # Herda altura da caixa anterior (do dict ou das dimensões físicas da caixa)
                if "altura" in ref_cc and float(ref_cc["altura"]) > 0:
                    params["altura"] = float(ref_cc["altura"])
                elif ref_b is not None:
                    params["altura"] = round((ref_b[5] - ref_b[4]) * 1000.0)

                # Herda rodapé se ambos forem inferiores/altos com rodapé
                if "rodape" in ref_cc and cat_novo in ("inferior", "alto"):
                    params["rodape"] = float(ref_cc["rodape"])

                # Adota o nível vertical Z exato da base do móvel de referência
                if ref_b is not None and cat_novo not in ("porta", "janela"):
                    default_z = ref_b[4]

        novo_L_m = float(params["largura"]) / 1000.0

        # ── VERIFICAÇÃO DE PAREDE SELECIONADA E FRAME ARMADO ─────────
        from ..wall.selection import WallSelectionManager
        wall_mgr = WallSelectionManager.get_instance(self.viewport)
        wall_mgr.sync_with_scene(scene)
        sel_wf = wall_mgr.selected_wall_face
        active_slot = getattr(wall_mgr, "active_placement_slot", None)

        # Se houver parede selecionada no andar superior (ex: 1º Andar com Z > 0),
        # ajusta o Z base padrão do módulo para coincidir com a base da parede.
        w_z_min = 0.0
        if sel_wf is not None and getattr(sel_wf, "wall_group", None) is not None:
            w_grp = sel_wf.wall_group
            w_m = getattr(w_grp, "mesh", None)
            if w_m and hasattr(w_m, "vertices") and w_m.vertices:
                w_z_min = min(v.position.z() for v in w_m.vertices)
                if w_z_min > 0.05 and not is_same_cat:
                    default_z += w_z_min

        # Regra de negócio estrita: esquadrias (portas e janelas) NÃO devem sofrer alinhamento
        # automático ou redimensionamento pelas réguas-guia de marcenaria.
        mod_id_str = str(mod_data.get("id", "")).lower()
        is_esquadria = (
            mod_data.get("tipo") == "esquadria"
            or "porta" in mod_id_str
            or "janela" in mod_id_str
        ) and "porta_tempero" not in mod_id_str and not mod_id_str.startswith("peca_")

        # Regra para Torres de Eletros (torre_quente, caixa_geladeira):
        # Devem sempre ir do chão (base da parede / piso) até a linha-guia de Topo de Aéreos / Torres.
        is_torre_eletro = mod_id_str in ("torre_quente", "caixa_geladeira") or "torre" in mod_id_str
        is_cama = mod_id_str.lower().startswith("cama_") or mod_id_str.lower() in ("bicama", "beliche")
        if is_torre_eletro:
            from ..wall.guides import WallGuideRulerManager
            ruler_mgr = WallGuideRulerManager.get_instance()
            tower_top_mm = ruler_mgr.get_tower_top_z_mm()
            default_z = w_z_min if sel_wf is not None else 0.0
            if tower_top_mm > 500.0:
                params["altura"] = float(tower_top_mm)

        # Se houver um frame armado entre linhas-guia na parede, ele tem prioridade para marcenaria:
        if active_slot is not None and sel_wf is not None and not is_esquadria:
            norm = sel_wf.normal
            n_dir = QVector3D(norm.x(), norm.y(), 0.0).normalized()
            u_dir = QVector3D(-n_dir.y(), n_dir.x(), 0.0).normalized()

            # Rotação Z para encostar traseira na parede e frente apontada para o cômodo (+n_dir)
            angle_deg = math.degrees(math.atan2(n_dir.y(), n_dir.x())) + 90.0
            params["rot_z"] = (round(angle_deg / 90.0) * 90.0) % 360.0

            if is_torre_eletro or is_cama:
                # Torres de eletros e camas vão sempre do chão (w_z_min) com suas medidas próprias,
                # independentemente de qual faixa vertical/profundidade estava clicada no slot da parede.
                z_base = w_z_min
                z_top = w_z_min + (float(params["altura"]) / 1000.0)
            else:
                # 1. Ajusta o módulo para a altura exata do vão entre réguas
                z_base = float(active_slot["z_base"])
                z_top = float(active_slot["z_top"])
                slot_height_mm = float(active_slot.get("height_mm", round((z_top - z_base) * 1000.0)))

                # Se o módulo a ser inserido tem rodape == 0 ou se o slot armado define vão suspenso,
                # garante que rodape seja 0.0 e a altura seja exatamente a do vão entre as guias.
                req_rodape = float(mod_data.get("rodape", params.get("rodape", 0.0)))
                is_sem_rodape = req_rodape <= 0.0 or float(params.get("rodape", 0.0)) <= 0.0
                if is_sem_rodape and slot_height_mm > 100:
                    params["altura"] = slot_height_mm
                    params["rodape"] = 0.0
                elif slot_height_mm > 100:
                    # Ajusta altura se o vão for delimitado entre duas réguas elevadas (ex: aéreos, torres, nichos)
                    params["altura"] = slot_height_mm

                # Se a profundidade padrão do slot for recomendada (ex: 350mm para aéreos, 550mm para balcões)
                if "default_depth_mm" in active_slot:
                    params["profundidade"] = float(active_slot["default_depth_mm"])

            # Atualiza o frame para ter a largura real do móvel selecionado
            # e reconfinar dentro dos limites físicos da parede
            mod_larg_m = float(params.get("largura", 800.0)) / 1000.0
            mod_prof_m = float(params.get("profundidade", 550.0)) / 1000.0
            if hasattr(wall_mgr, "update_frame_dimensions"):
                wall_mgr.update_frame_dimensions(mod_larg_m, mod_prof_m)

            # Constrói temporariamente em (0, 0, 0) para calcular bounds reais pós-rotação
            new_module_group = CabinetBuilder.build_module_group(params, offset=(0.0, 0.0, 0.0))

            from ..interaction.magnetic_drag import get_module_bounds, get_bounds_min_projection
            b = get_module_carcass_bounds(new_module_group) or get_module_bounds(new_module_group)
            if b is not None:
                p_wall = active_slot["center_pt"]

                # 2. Encosta a traseira rigorosamente na face da parede ao longo de n_dir
                cur_min_n = get_bounds_min_projection(b, n_dir)
                wall_n = QVector3D.dotProduct(p_wall, n_dir)
                shift_n = (wall_n - cur_min_n) + 0.001

                # 3. Alinha com o centro horizontal do frame já confinado aos limites da parede
                cur_center_u = QVector3D.dotProduct(QVector3D((b[0] + b[1]) * 0.5, (b[2] + b[3]) * 0.5, 0.0), u_dir)
                wall_u = QVector3D.dotProduct(p_wall, u_dir)
                shift_u = wall_u - cur_center_u

                # 4. Encaixa a base Z exatamente na cota z_base do slot
                shift_z = z_base - b[4]

                shift = n_dir * shift_n + u_dir * shift_u + QVector3D(0.0, 0.0, shift_z)

                targets = getattr(new_module_group, "children", []) or [new_module_group]
                for t in targets:
                    m_sub = getattr(t, "mesh", None)
                    if m_sub and hasattr(m_sub, "vertices"):
                        for v in m_sub.vertices:
                            v.position += shift
                        m_sub._mut_serial = getattr(m_sub, "_mut_serial", 0) + 1
                    if getattr(t, "ext", None) is not None:
                        if "orig_vertices" in t.ext:
                            t.ext["orig_vertices"] = [orig + shift for orig in t.ext["orig_vertices"]]
                        if "hinge_pivot" in t.ext and isinstance(t.ext["hinge_pivot"], QVector3D):
                            t.ext["hinge_pivot"] += shift
                if "trazomob_module" in new_module_group.ext:
                    mod_ext = new_module_group.ext["trazomob_module"]
                    mod_ext["offset"] = (float(shift.x()), float(shift.y()), float(shift.z()))
        elif sel_wf is not None and sel_wf.face is not None:
            norm = sel_wf.normal
            n_dir = QVector3D(norm.x(), norm.y(), 0.0)
            wall_grp = getattr(sel_wf, "wall_group", None)
            w_ext = getattr(wall_grp, "ext", {}).get("trazomob_wall", {}) if wall_grp else {}

            if is_esquadria and w_ext and "pontos" in w_ext:
                # ── INSERÇÃO INTELIGENTE DE ESQUADRIAS (PORTAS E JANELAS) ──
                # Portas e janelas são instaladas no MIOLO do vão da alvenaria (ao longo do segmento da parede)
                pts_data = w_ext.get("pontos", [])
                seg_idx = getattr(sel_wf, "segment_index", 0)
                n_pts = len(pts_data)
                is_closed = w_ext.get("is_closed", False)
                n_segs = n_pts if is_closed else max(0, n_pts - 1)

                if 0 <= seg_idx < n_segs:
                    p0 = QVector3D(*pts_data[seg_idx])
                    p1 = QVector3D(*pts_data[(seg_idx + 1) % n_pts])
                    seg_v = p1 - p0
                    seg_len = seg_v.length()
                    seg_u = seg_v.normalized() if seg_len > 1e-4 else QVector3D(1, 0, 0)
                    seg_n = QVector3D(-seg_u.y(), seg_u.x(), 0.0).normalized()
                    wall_esp = float(w_ext.get("espessura", 0.15))
                    alinhamento = w_ext.get("alinhamento", "interno")

                    # Dire??o transversal para o centro da espessura da alvenaria
                    if alinhamento == "interno":
                        transv = seg_n * (wall_esp * 0.5)
                    elif alinhamento == "externo":
                        transv = seg_n * (-wall_esp * 0.5)
                    else:
                        transv = QVector3D(0, 0, 0)

                    larg_m = float(params.get("largura", 800.0)) / 1000.0
                    c_seg_center = p0 + seg_u * (seg_len * 0.5) + transv

                    # Mede o centro geométrico transversal local da esquadria sem instanciar em duplicidade
                    from ..builders.esquadrias import EsquadriaBuilder
                    mid_yl = EsquadriaBuilder.get_esquadria_local_mid_y(str(params.get("tipo", "")), esp_parede_mm=wall_esp * 1000.0)

                    angle_deg = math.degrees(math.atan2(seg_u.y(), seg_u.x()))
                    params["rot_z"] = angle_deg

                    pos_base = c_seg_center - seg_u * (larg_m * 0.5) - seg_n * mid_yl
                    z_base_esq = float(w_ext.get("z_base", 0.0) or 0.0)
                    offset = (pos_base.x(), pos_base.y(), z_base_esq)
                else:
                    offset = (sel_wf.center.x(), sel_wf.center.y(), 0.0)

                new_module_group = CabinetBuilder.build_module_group(params, offset=offset)
            elif n_dir.length() > 1e-4:
                n_dir.normalize()
                angle_deg = math.degrees(math.atan2(n_dir.y(), n_dir.x())) + 90.0
                params["rot_z"] = (round(angle_deg / 90.0) * 90.0) % 360.0

                u_dir = QVector3D(-n_dir.y(), n_dir.x(), 0.0).normalized()
                c_pt = sel_wf.center

                positioned_next_to_ref = False
                if ref_mod is not None and ref_b is not None:
                    ref_rot = float(ref_cc.get("rot_z", 0.0)) % 360.0
                    if abs(ref_rot - params["rot_z"]) < 1e-2 or abs(abs(ref_rot - params["rot_z"]) - 360.0) < 1e-2:
                        novo_P_m = float(params.get("profundidade", 550.0)) / 1000.0
                        half_diff = (novo_L_m - novo_P_m) * 0.5
                        if abs(ref_rot) < 1e-4:
                            offset = (ref_b[1], ref_b[2], default_z)
                        elif abs(ref_rot - 180.0) < 1e-4:
                            cand_x = ref_b[0] - novo_L_m
                            if cand_x < 0.14:
                                cand_x = ref_b[1]
                            offset = (cand_x, ref_b[2], default_z)
                        elif abs(ref_rot - 90.0) < 1e-4:
                            cand_min_y = ref_b[3]
                            offset = (ref_b[0] - half_diff, cand_min_y + half_diff, default_z)
                        elif abs(ref_rot - 270.0) < 1e-4:
                            cand_min_y = ref_b[2] - novo_L_m
                            if cand_min_y < 0.14:
                                cand_min_y = ref_b[3]
                            offset = (ref_b[0] - half_diff, cand_min_y + half_diff, default_z)
                        else:
                            offset = (ref_b[1], ref_b[2], default_z)
                        positioned_next_to_ref = True

                if not positioned_next_to_ref:
                    larg_m = float(params.get("largura", 800.0)) / 1000.0
                    pos_base = c_pt + n_dir * 0.001 - u_dir * (larg_m * 0.5)
                    offset = (pos_base.x(), pos_base.y(), default_z)

                new_module_group = CabinetBuilder.build_module_group(params, offset=offset)

                from ..interaction.magnetic_drag import get_module_bounds, get_bounds_min_projection
                b = get_module_carcass_bounds(new_module_group) or get_module_bounds(new_module_group)
                if b is not None:
                    cur_min_n = get_bounds_min_projection(b, n_dir)
                    wall_face_n = QVector3D.dotProduct(sel_wf.center, n_dir)
                    delta_n = (wall_face_n - cur_min_n) + 0.001
                    if abs(delta_n) > 1e-4:
                        shift = n_dir * delta_n
                        targets = getattr(new_module_group, "children", []) or [new_module_group]
                        for t in targets:
                            m_sub = getattr(t, "mesh", None)
                            if m_sub and hasattr(m_sub, "vertices"):
                                for v in m_sub.vertices:
                                    v.position += shift
                                m_sub._mut_serial = getattr(m_sub, "_mut_serial", 0) + 1
                            if getattr(t, "ext", None) is not None:
                                if "orig_vertices" in t.ext:
                                    t.ext["orig_vertices"] = [orig + shift for orig in t.ext["orig_vertices"]]
                                if "hinge_pivot" in t.ext and isinstance(t.ext["hinge_pivot"], QVector3D):
                                    t.ext["hinge_pivot"] += shift
                        if "trazomob_module" in new_module_group.ext:
                            mod_ext = new_module_group.ext["trazomob_module"]
                            old_off = mod_ext.get("offset", (0.0, 0.0, 0.0))
                            mod_ext["offset"] = (
                                float(old_off[0]) + float(shift.x()),
                                float(old_off[1]) + float(shift.y()),
                                float(old_off[2]) + float(shift.z()),
                            )
            else:
                offset = (sel_wf.center.x(), sel_wf.center.y(), default_z)
                new_module_group = CabinetBuilder.build_module_group(params, offset=offset)
        elif ref_mod is not None:
            ref_rot_z = 0.0
            if hasattr(ref_mod, "ext") and "trazomob_module" in ref_mod.ext:
                ref_rot_z = float(ref_mod.ext["trazomob_module"].get("rot_z", 0.0)) % 360.0
            params["rot_z"] = ref_rot_z

            if ref_b is not None:
                # Caso especial: Bancada sendo inserida sobre Balcão selecionado
                ref_z = ref_b[4] if ref_b is not None else float(ref_cc.get("offset", (0, 0, 0))[2])
                ref_tipo = ref_cc.get("tipo", getattr(ref_mod, "name", ""))
                cat_ref = get_module_category(ref_tipo, ref_z)

                if cat_novo == "bancada" and cat_ref in ("inferior", "banheiro"):
                    ref_top_z = ref_b[5]
                    # Adota exatamente o offset X, Y do balcão de referência com Z no topo da caixa
                    ref_off = ref_cc.get("offset") if ref_cc else None
                    if ref_off is not None and len(ref_off) == 3:
                        offset = (float(ref_off[0]), float(ref_off[1]), ref_top_z)
                    else:
                        offset = (ref_b[0], ref_b[2], ref_top_z)
                else:
                    novo_P_m = float(params.get("profundidade", 550.0)) / 1000.0
                    half_diff = (novo_L_m - novo_P_m) * 0.5
                    z_target = 0.0 if is_torre_eletro else (ref_b[4] if is_same_cat else default_z)
                    if abs(ref_rot_z) < 1e-4:
                        offset = (ref_b[1], ref_b[2], z_target)
                    elif abs(ref_rot_z - 180.0) < 1e-4:
                        offset = (ref_b[0] - novo_L_m, ref_b[2], z_target)
                    elif abs(ref_rot_z - 90.0) < 1e-4:
                        offset = (ref_b[0] - half_diff, ref_b[3] + half_diff, z_target)
                    elif abs(ref_rot_z - 270.0) < 1e-4:
                        offset = (ref_b[0] - half_diff, (ref_b[2] - novo_L_m) + half_diff, z_target)
                    else:
                        offset = (ref_b[1], ref_b[2], z_target)
            else:
                offset = (0.0, 0.0, default_z)
            new_module_group = CabinetBuilder.build_module_group(params, offset=offset)
        else:
            camera = getattr(self.viewport, "camera", None)
            if camera is not None and hasattr(camera, "target"):
                offset = (camera.target.x(), camera.target.y(), default_z)
            else:
                offset = (0.0, 0.0, default_z)
            new_module_group = CabinetBuilder.build_module_group(params, offset=offset)

        def apply_insert(sc):
            target_layer = getattr(new_module_group, "layer", None)
            if target_layer and hasattr(sc, "layer") and hasattr(sc, "layers"):
                if sc.layer(target_layer) is None:
                    from core.layers import Layer
                    sc.layers.append(Layer(target_layer))
            # Se houver parede de referência ou selecionada com ambiente definido, herda o ambiente
            ref_wall = sel_wf.wall_group if sel_wf is not None else None
            if ref_wall is not None and hasattr(ref_wall, "ext") and isinstance(ref_wall.ext, dict):
                amb_n = ref_wall.ext.get("ambiente") or ref_wall.ext.get("trazomob_wall", {}).get("ambiente")
                pav_n = ref_wall.ext.get("pavimento") or ref_wall.ext.get("trazomob_wall", {}).get("pavimento")
                if amb_n and hasattr(new_module_group, "ext") and isinstance(new_module_group.ext, dict):
                    new_module_group.ext["ambiente"] = amb_n
                    new_module_group.ext["pavimento"] = pav_n or "Térreo"
                    for k in ("trazomob_module", "trazomob_esquadria", "trazomob"):
                        if k in new_module_group.ext and isinstance(new_module_group.ext[k], dict):
                            new_module_group.ext[k]["ambiente"] = amb_n
                            new_module_group.ext[k]["pavimento"] = pav_n or "Térreo"

            sc.groups.append(new_module_group)
            sc.selection = {new_module_group}

            # Se inseriu uma esquadria (porta/janela), sincroniza o recorte na parede
            from ..wall.mesh_builder import WallMeshBuilder
            WallMeshBuilder.sync_scene_wall_openings(sc)

        self.viewport.history.execute(SnapshotImport(apply_insert))

        # Abre o módulo recém-inserido diretamente no painel lateral ANTES de notificar a cena,
        # evitando que on_scene_changed processe o módulo duas vezes ou perca a sincronia de _selected_module.
        if self.sidebar_panel is not None:
            self.sidebar_panel._selected_module = new_module_group
            self.sidebar_panel.focus_panel()
            self.sidebar_panel.load_module(new_module_group)

        self.viewport.notify_scene_changed()

        # Desloca o frame 3D armado para a posição imediatamente contígua para o próximo móvel
        if active_slot is not None and hasattr(wall_mgr, "advance_slot_after_placement"):
            placed_larg_m = float(params.get("largura", 800.0)) / 1000.0
            wall_mgr.advance_slot_after_placement(placed_larg_m)

        self.viewport.update()

        if hasattr(self.viewport, "flash_status"):
            self.viewport.flash_status(f"✨ Módulo '{new_module_group.name}' inserido na cena!")
