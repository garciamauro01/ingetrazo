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
import os
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QPoint, QSize, Qt, QTimer, Signal, QMimeData
from PySide6.QtGui import QDrag, QIcon, QKeySequence, QMouseEvent, QVector3D
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
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
from core.paths import app_root
from ..integrations import platform as host
from ..builders.cabinet import CabinetBuilder
from ..domain.catalog import MODULE_CATALOG, USER_MODULE_CATEGORY, modulos_usuario
from ..domain.i18n import tr
from ..ui.icons import get_module_thumbnail


logger = logging.getLogger("trazomob.module_ribbon")



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



class DecorationButton(QToolButton):

    """Botão visual moderno para itens de decoração e componentes da biblioteca do IngeTrazo."""

    def __init__(self, item_data: dict[str, Any], on_clicked, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.on_clicked = on_clicked

        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setIconSize(QSize(52, 52))
        self.setFixedSize(100, 84)

        nome = item_data.get("name") or item_data.get("nombre", "")
        if len(nome) > 18:
            parts = nome.split(" (")[0]
            display_name = parts if len(parts) <= 18 else (parts[:16] + "…")
        else:
            display_name = nome

        self.setText(display_name)
        tip = item_data.get("tip") or nome
        self.setToolTip(f"<b>{nome}</b><br>{tip}<br><i>Duplo clique ou arraste para inserir na cena</i>")
        self.setStatusTip(f"Duplo clique ou arraste para inserir {nome}")
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

        icon_path = item_data.get("icon_path")
        if icon_path and os.path.exists(str(icon_path)):
            self.setIcon(QIcon(str(icon_path)))
        elif "library_id" in item_data:
            from core import library
            ident = item_data["library_id"]
            p = library.cached_thumbnail(ident)
            if p and os.path.exists(str(p)):
                self.setIcon(QIcon(str(p)))
            else:
                # Carregamento sob demanda
                library.prefetch_thumbnails([ident])
                QTimer.singleShot(600, self._check_thumb)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.position().toPoint()
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
        from ..interaction.drag_drop_handler import TRAZOMOB_MIME_DECORATION
        mime = QMimeData()
        # Copia dados serializáveis
        clean_data = {}
        for k, v in self.item_data.items():
            if isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                clean_data[k] = v
        mime.setData(TRAZOMOB_MIME_DECORATION, json.dumps(clean_data).encode("utf-8"))

        drag = QDrag(self)
        drag.setMimeData(mime)
        pixmap = self.icon().pixmap(52, 52)
        if not pixmap.isNull():
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
        drag.exec(Qt.CopyAction)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.on_clicked(self.item_data)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _check_thumb(self):
        ident = self.item_data.get("library_id")
        if not ident:
            return
        from core import library
        p = library.cached_thumbnail(ident)
        if p and os.path.exists(str(p)):
            self.setIcon(QIcon(str(p)))


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
        # Somebody may have imported a component while this bar was hidden;
        # the brand buttons are cheap to redraw and the manifest says when.
        self.refresh_user_components()

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

    def _create_decoration_scroll_area(self, items: list[dict[str, Any]]) -> QScrollArea:
        """Cria uma área horizontal com scroll de botões de decoração/componentes."""
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

        for item_data in items:
            btn = DecorationButton(item_data, on_clicked=self.insert_decoration_into_scene, parent=content)
            h_layout.addWidget(btn)

        # Botão para abrir o diálogo completo da biblioteca
        btn_more = QToolButton(content)
        btn_more.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        btn_more.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogContentsView))
        btn_more.setIconSize(QSize(40, 40))
        btn_more.setFixedSize(100, 84)
        btn_more.setText(tr("Biblioteca…"))
        btn_more.setToolTip(tr("Abrir diálogo completo da Biblioteca de Componentes com busca"))
        btn_more.setCursor(Qt.PointingHandCursor)
        btn_more.setStyleSheet(
            "QToolButton {"
            "  border: 1px dashed palette(highlight);"
            "  border-radius: 6px;"
            "  background-color: palette(base);"
            "  color: palette(highlight);"
            "  font-size: 11px;"
            "  font-weight: bold;"
            "  padding: 4px;"
            "}"
            "QToolButton:hover {"
            "  background-color: palette(alternate-base);"
            "}"
        )
        btn_more.clicked.connect(lambda: host.open_component_library(self.main_window))
        h_layout.addWidget(btn_more)

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
                self.refresh_user_components()

    def _populate_decoration_tab(self) -> None:
        """Popula a aba de Decoração sob demanda quando o usuário clica nela pela primeira vez."""
        decor_categories: dict[str, list[dict[str, Any]]] = {
            "Geral & Starters": [],
            "Pessoas (Escala)": [],
            "Sala & Estar": [],
            "Cozinha & Eletros": [],
            "Banheiro": [],
            "Quarto": [],
            "Iluminação": [],
            "Plantas & Exterior": [],
            "Decoração & Vários": [],
        }

        # 1. Carrega os componentes nativos locais do IngeTrazo
        res_comp = app_root() / "resources" / "components"
        manifest_path = res_comp / "components.json"
        if manifest_path.exists():
            try:
                for entry in json.loads(manifest_path.read_text(encoding="utf-8")):
                    key = entry.get("key", "")
                    icon_file = res_comp / "thumbs" / f"{key}.png"
                    decor_categories["Geral & Starters"].append({
                        "tipo": "native_3d",
                        "key": key,
                        "name": tr(entry.get("name", key.capitalize())),
                        "tip": tr(entry.get("tip", "")),
                        "icon_path": str(icon_file) if icon_file.exists() else None,
                    })
            except Exception as exc:
                logger.debug("falha ao ler o manifesto de modelos nativos: %s", exc)

        people_path = res_comp / "people.json"
        if people_path.exists():
            try:
                for entry in json.loads(people_path.read_text(encoding="utf-8")):
                    key = entry.get("key", "")
                    icon_file = res_comp / f"{key}.png"
                    decor_categories["Pessoas (Escala)"].append({
                        "tipo": "native_person",
                        "key": key,
                        "height": float(entry.get("height", 1.75)),
                        "name": tr(entry.get("name", key.capitalize())),
                        "tip": tr(entry.get("tip", "")),
                        "icon_path": str(icon_file) if icon_file.exists() else None,
                    })
            except Exception as exc:
                logger.debug("falha ao ler people.json: %s", exc)

        # 2. Carrega destaques de cada categoria do catálogo (máx 24 por aba rápida; o botão Biblioteca abre todos os 1500+)
        MAX_RIBBON_ITEMS_PER_SUBTAB = 24
        try:
            from core import library
            lib_entries = library.index()
            cat_target_map = {
                "Salón": "Sala & Estar",
                "Cocina": "Cozinha & Eletros",
                "Cuarto de Baño": "Banheiro",
                "Dormitorio": "Quarto",
                "Iluminación": "Iluminação",
                "Exterior": "Plantas & Exterior",
                "Personajes": "Pessoas (Escala)",
                "Varios": "Decoração & Vários",
                "Oficina": "Decoração & Vários",
            }
            for e in lib_entries:
                c_orig = e.get("categoria", "")
                sub_target = cat_target_map.get(c_orig)
                if not sub_target or len(decor_categories[sub_target]) >= MAX_RIBBON_ITEMS_PER_SUBTAB:
                    continue
                name = e.get("nombre_en") or e.get("nombre") or e.get("id", "")
                decor_categories[sub_target].append({
                    "tipo": "library_model",
                    "library_id": e.get("id"),
                    "name": name,
                    "tip": f"{name} ({c_orig})",
                    "entry": e,
                })
        except Exception as exc:
            logger.debug("falha ao carregar destaques da biblioteca: %s", exc)

        decor_tabs = QTabWidget()
        decor_tabs.setTabPosition(QTabWidget.South)
        decor_tabs.setDocumentMode(True)
        decor_tabs.setStyleSheet(self._decor_subtab_style)

        # «Meus Componentes» vem primeiro: é a coleção do próprio usuário,
        # com as marcas que ele cadastrou (Brastemp, Electrolux…), e é onde
        # uma geladeira baixada por ele aparece sem depender do catálogo
        # online — que é de outra gente e não é redistribuído por este app.
        self._decor_tabs = decor_tabs
        self._user_tab_page = self._user_components_page()
        self._user_tab_index = decor_tabs.addTab(
            self._user_tab_page, "⭐ Meus Componentes")

        for sub_label, items in decor_categories.items():
            if items:
                decor_tabs.addTab(self._create_decoration_scroll_area(items), sub_label)

        lay = QVBoxLayout(self._decor_placeholder)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(decor_tabs)


    def _user_components_page(self) -> QWidget:
        """The «Meus Componentes» sub-tab: one button per brand, the whole
        library, and the manager. Rebuilt when the manifest changes, so a
        file imported from the tray shows up here without reopening the app.
        """
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(94)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        row = QHBoxLayout(content)
        row.setContentsMargins(4, 2, 4, 2)
        row.setSpacing(6)
        row.setAlignment(Qt.AlignLeft)
        scroll.setWidget(content)
        lay.addWidget(scroll)
        self._user_scroll = scroll
        self._user_content = content
        self._user_buttons = row
        self._user_revision = None
        self.refresh_user_components(force=True)
        return page

    def _user_button(self, text: str, tip: str, callback, icon=None):
        btn = QToolButton(self._user_content)
        btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        btn.setIcon(icon if icon is not None
                    else self.style().standardIcon(
                        self.style().StandardPixmap.SP_DirIcon))
        btn.setIconSize(QSize(52, 52))
        btn.setFixedSize(100, 84)
        if len(text) > 18:
            text = text[:16] + "…"
        btn.setText(text)
        btn.setToolTip(tip)
        btn.setStatusTip(tip)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
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
        )
        btn.clicked.connect(lambda _c=False: callback())
        self._user_buttons.addWidget(btn)
        return btn

    def refresh_user_components(self, force: bool = False) -> None:
        """Rebuild the brand buttons if the user's library changed since
        they were drawn (a new import, an edit, a removal)."""
        if not hasattr(self, "_user_buttons"):
            return
        try:
            from core import user_library
            revision = user_library.revision()
        except Exception as exc:  # noqa: BLE001 - the ribbon must not fail
            logger.debug("biblioteca do usuário indisponível: %s", exc)
            return
        if not force and revision == getattr(self, "_user_revision", None):
            return
        self._user_revision = revision

        while self._user_buttons.count():
            item = self._user_buttons.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        try:
            entries = user_library.index()
            facets = user_library.facets(entries)
        except Exception as exc:  # noqa: BLE001
            logger.debug("falha ao ler a biblioteca do usuário: %s", exc)
            entries, facets = [], {}

        if entries:
            self._user_button(
                tr("All ({n})", n=len(entries)),
                tr("Show every component in your library"),
                lambda: self._open_user_library())
            for marca in sorted((facets.get("marcas") or {}),
                                key=str.casefold):
                count = facets["marcas"][marca]
                self._user_button(
                    f"{marca} ({count})",
                    tr("{n} components by {brand} — open your library "
                       "filtered by it", n=count, brand=marca),
                    lambda _m=marca: self._open_user_library(_m))
        else:
            empty = QLabel(tr(
                "Your own models live here. Import a file (OBJ, GLB, DAE, "
                "STL, SKP, IGZ) or index a folder to fill this tab."))
            empty.setWordWrap(True)
            empty.setStyleSheet("color: palette(text); padding: 6px;")
            self._user_buttons.addWidget(empty)

        self._user_button(
            tr("Import…"),
            tr("Index a model file in your library and place it"),
            lambda: self._import_user_component())
        self._user_button(
            tr("Manage…"),
            tr("Browse, edit and remove the components in your library"),
            lambda: self._open_user_library())
        self._user_buttons.addStretch(1)

    def _open_user_library(self, brand: str | None = None) -> None:
        """Open the manager and redraw the brands when it closes: an import,
        an edit or a removal made inside it must show up right away."""
        host.open_user_library(self.main_window, brand)
        self.refresh_user_components(force=True)

    def _import_user_component(self) -> None:
        host.import_user_component(self.main_window)
        self.refresh_user_components(force=True)

    def insert_decoration_into_scene(self, item_data: dict[str, Any]):
        """Insere o item de decoração selecionado na cena 3D."""
        tipo = item_data.get("tipo")
        if tipo == "native_3d":
            key = item_data.get("key", "")
            host.insert_component(self.main_window, key, item_data.get("name"))
        elif tipo == "native_person":
            key = item_data.get("key", "")
            height = float(item_data.get("height", 1.75))
            host.insert_person_2d(self.main_window, f"{key}.png", height,
                                  item_data.get("name"))
        elif tipo == "library_model":
            entry = item_data.get("entry")
            if entry and hasattr(self.main_window, "insert_library_component"):
                self.main_window.insert_library_component(entry)

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
