# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Painel lateral (Dock Widget) de edição de módulos dinâmicos do TrazoMob."""
from __future__ import annotations

import math
from typing import Any

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QIcon, QVector3D
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDockWidget,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.group import Group
from core.history import SnapshotImport
from core.mesh import Mesh

from ..builders.cabinet import CabinetBuilder, RotateTrazoMobModuleCommand
from ..domain.catalog import MODULE_CATALOG
from ..domain.i18n import tr
from ..integrations import platform as host
from ..ui.icons import (
    get_module_thumbnail,
    make_cabinet_icon,
    make_trazomob_icon,
    make_interact_icon,
    make_rotate_ccw_icon,
    make_rotate_cw_icon,
    make_perfil_diagram_pixmap,
)
from ..interaction.interact import CabinetInteract, CabinetInteractTool
from ..profiles import library as perfis_lib
from ..profiles.editor import PerfilLibraryDialog, fill_profile_combo
from ..ui.sidebar_walls_ui import SidebarWallsUIMixin
from ..ui.sidebar_adjustments_controller import SidebarAdjustmentsMixin as SidebarAjustesMixin
from ..ui.sidebar_module_loader import SidebarModuleLoaderMixin
from ..ui.sidebar_apply_controller import SidebarApplyMixin
from ..ui.sidebar_scene_controller import SidebarSceneMixin
from ..ui.sidebar_actions_controller import SidebarActionsMixin
from ..ui.sidebar_fronts_controller import SidebarFrontsMixin as SidebarFrentesMixin
from ..ui.sidebar_materials_controller import SidebarMaterialsMixin as SidebarMateriaisMixin
from ..ui.sidebar_handles_controller import SidebarHandlesMixin as SidebarPuxadoresMixin
from ..ui.sidebar_dimensions_controller import SidebarDimensionsMixin as SidebarMedidasMixin
from ..ui.sidebar_wall_controller import SidebarWallMixin
from ..ui.sidebar_collapsible import CollapsibleSection
from ..domain.param_mapper import extract_ui_module_params, populate_ui_from_module
from ..domain.schema import module_params
from ..domain.module_geometry import get_module_category


# Categorias do catálogo que são compatíveis para "Trocar Tipo" (Swap).
_SWAP_COMPATIBLE_CATEGORIES = {
    "Cozinha \u2014 Inferiores": {"Cozinha \u2014 Inferiores"},
    "Cozinha \u2014 A\u00e9reos": {"Cozinha \u2014 A\u00e9reos", "Nichos & Estantes"},
    "Nichos & Estantes": {"Cozinha \u2014 A\u00e9reos", "Nichos & Estantes"},
    "Cozinha \u2014 Torres": {"Cozinha \u2014 Torres"},
    "Arm\u00e1rios": {"Arm\u00e1rios"},
    "Banheiro": {"Banheiro"},
    "Marmoraria & Pias": {"Marmoraria & Pias"},
    "Portas & Janelas": {"Portas & Janelas"},
    "Pe\u00e7as Avulsas / Componentes": {"Pe\u00e7as Avulsas / Componentes"},
    "Dormit\u00f3rio \u2014 Camas": {"Dormit\u00f3rio \u2014 Camas"},
}


def _get_swap_categories(current_cat: str) -> set[str]:
    return _SWAP_COMPATIBLE_CATEGORIES.get(current_cat, {current_cat})


from ..ui.sidebar_esquadria_controller import SidebarEsquadriaMixin
from ..ui.sidebar_fit_controller import SidebarFitMixin
from ..ui.sidebar_interact_controller import SidebarInteractBatchMixin
from ..ui.sidebar_light_controller import SidebarLightMixin
from ..ui.sidebar_align_controller import SidebarAlignMixin


class TrazoMobSidebarPanel(QWidget, SidebarWallMixin, SidebarWallsUIMixin, SidebarAjustesMixin, SidebarModuleLoaderMixin, SidebarApplyMixin, SidebarSceneMixin, SidebarActionsMixin, SidebarFrentesMixin, SidebarMateriaisMixin, SidebarPuxadoresMixin, SidebarMedidasMixin, SidebarEsquadriaMixin, SidebarFitMixin, SidebarInteractBatchMixin, SidebarLightMixin, SidebarAlignMixin):
    """Painel de encaixe da barra lateral para edição dinâmica de módulos do TrazoMob."""

    def __init__(self, app, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._app = app
        self._updating_ui = False
        self._selected_module: Group | None = None
        self._selected_wall: Group | None = None
        self._selected_light_grp: Group | None = None

        self._dock: QDockWidget | None = None
        self._form_built: bool = False

        self._build_ui()

        # Conecta sinal de atualização de cena / troca de documento ativo
        if hasattr(self._app, "on_document_changed"):
            self._app.on_document_changed(self.on_scene_changed)
        else:
            viewport = self._get_viewport()
            if viewport is not None and hasattr(viewport, "sceneVersionChanged"):
                viewport.sceneVersionChanged.connect(self.on_scene_changed)

        win = self._get_window()
        if win is not None and hasattr(win, "documentChanged"):
            try:
                win.documentChanged.connect(self.on_scene_changed)
            except Exception:
                pass

    def set_dock(self, dock: QDockWidget) -> None:
        """Associa o QDockWidget hospedeiro a este painel lateral."""
        self._dock = dock

    def focus_panel(self) -> None:
        """Traz a aba do TrazoMob para o primeiro plano na barra lateral."""
        self._ensure_form_built()
        if hasattr(self._app, "show_panel") and self._dock is not None:
            self._app.show_panel(self._dock)
        elif self._dock is not None:
            self._dock.show()
            self._dock.raise_()

    def _get_window(self):
        return getattr(self._app, "window", None) or getattr(self._app, "_window", None)

    def _get_viewport(self):
        return host.active_viewport(window=self._get_window(), app=self._app)

    def _get_scene(self):
        vp = self._get_viewport()
        return getattr(vp, "scene", None)

    def _build_ui(self) -> None:
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(6, 6, 6, 6)
        self._main_layout.setSpacing(6)

        # Cabeçalho de Status Compacto e Elegante (construído de imediato — < 5ms)
        self.card_header = QFrame()
        self.card_header.setStyleSheet(
            "QFrame { background-color: palette(base); border: 1px solid palette(mid); border-radius: 4px; padding: 2px 4px; }"
        )
        h_head = QVBoxLayout(self.card_header)
        h_head.setContentsMargins(4, 3, 4, 3)
        h_head.setSpacing(2)

        self.lbl_title = QLabel(tr("🪵 TrazoMob — Módulos"))
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 11px; color: palette(text);")
        h_head.addWidget(self.lbl_title)

        self.lbl_status = QLabel(tr("💡 Selecione uma parede ou um módulo no 3D para editar."))
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("font-size: 10px; color: palette(placeholder-text);")
        h_head.addWidget(self.lbl_status)

        self._main_layout.addWidget(self.card_header)

        # ── Card de Alinhamento e Centralização Rápida (quando múltiplos objetos estão selecionados) ──
        self.card_align = QFrame()
        self.card_align.setStyleSheet(
            "QFrame { background-color: palette(base); border: 1px solid palette(mid); border-radius: 4px; padding: 4px; }"
        )
        l_align = QVBoxLayout(self.card_align)
        l_align.setContentsMargins(4, 4, 4, 4)
        l_align.setSpacing(4)

        self.lbl_align_info = QLabel(tr("🎯 <b>Centralizar Objeto Selecionado</b>"))
        self.lbl_align_info.setStyleSheet("color: palette(text); font-size: 11px;")
        l_align.addWidget(self.lbl_align_info)

        self.lbl_align_desc = QLabel(tr("Selecione 2 objetos com Ctrl para centralizar ou alinhar."))
        self.lbl_align_desc.setStyleSheet("font-size: 10px; color: palette(placeholder-text);")
        self.lbl_align_desc.setWordWrap(True)
        l_align.addWidget(self.lbl_align_desc)

        h_align_xy = QHBoxLayout()
        h_align_xy.setSpacing(4)
        self.btn_center_xy = QPushButton(tr("✛ Centro (XY)"))
        self.btn_center_xy.setToolTip(tr("Centraliza no plano horizontal (Largura e Profundidade)"))
        self.btn_center_xy.setStyleSheet("QPushButton { font-weight: bold; padding: 6px; border-radius: 4px; font-size: 11px; }")
        self.btn_center_xy.clicked.connect(lambda: self._trigger_center("xy"))
        h_align_xy.addWidget(self.btn_center_xy)

        self.btn_center_x = QPushButton(tr("↔ Largura (X)"))
        self.btn_center_x.setToolTip(tr("Centraliza apenas no eixo X (Largura)"))
        self.btn_center_x.setStyleSheet("QPushButton { padding: 6px; border-radius: 4px; font-size: 11px; }")
        self.btn_center_x.clicked.connect(lambda: self._trigger_center("x"))
        h_align_xy.addWidget(self.btn_center_x)
        l_align.addLayout(h_align_xy)

        h_align_yz = QHBoxLayout()
        h_align_yz.setSpacing(4)
        self.btn_center_y = QPushButton(tr("↕ Profundidade (Y)"))
        self.btn_center_y.setToolTip(tr("Centraliza apenas no eixo Y (Profundidade)"))
        self.btn_center_y.setStyleSheet("QPushButton { padding: 6px; border-radius: 4px; font-size: 11px; }")
        self.btn_center_y.clicked.connect(lambda: self._trigger_center("y"))
        h_align_yz.addWidget(self.btn_center_y)

        self.btn_center_z = QPushButton(tr("⬍ Altura (Z)"))
        self.btn_center_z.setToolTip(tr("Centraliza apenas no eixo Z (Altura)"))
        self.btn_center_z.setStyleSheet("QPushButton { padding: 6px; border-radius: 4px; font-size: 11px; }")
        self.btn_center_z.clicked.connect(lambda: self._trigger_center("z"))
        h_align_yz.addWidget(self.btn_center_z)
        l_align.addLayout(h_align_yz)

        self.btn_distribute_equidistant = QPushButton(tr("↔ Distribuir Módulos no Vão"))
        self.btn_distribute_equidistant.setToolTip(tr("Distribui os módulos selecionados com espaçamento uniforme ou ajusta contiguamente para preencher o vão livre"))
        self.btn_distribute_equidistant.setStyleSheet("QPushButton { background-color: #0284C7; color: white; font-weight: bold; padding: 6px; border-radius: 4px; font-size: 11px; margin-top: 4px; } QPushButton:hover { background-color: #0369A1; }")
        self.btn_distribute_equidistant.clicked.connect(self._distribute_selected_modules)
        l_align.addWidget(self.btn_distribute_equidistant)

        self.card_align.setVisible(False)
        self._main_layout.addWidget(self.card_align)

        # ── Card de Abertura Dinâmica e Cinemática 3D ──
        self.card_interact = QFrame()
        self.card_interact.setStyleSheet(
            "QFrame { background-color: palette(base); border: 1px solid palette(mid); border-radius: 4px; padding: 4px; }"
        )
        l_interact = QVBoxLayout(self.card_interact)
        l_interact.setContentsMargins(4, 4, 4, 4)
        l_interact.setSpacing(4)

        h_dyn_title = QHBoxLayout()
        lbl_dyn_icon = QLabel(tr("🚪 <b>Abertura Dinâmica 3D</b>"))
        lbl_dyn_icon.setStyleSheet("color: palette(text); font-size: 11px;")
        h_dyn_title.addWidget(lbl_dyn_icon)
        h_dyn_title.addStretch()

        self.btn_dyn_check_col = QPushButton(tr("⚠️ Testar Colisões"))
        self.btn_dyn_check_col.setToolTip(tr("Verifica se alguma gaveta ou porta aberta bate em puxadores, cantos ou paredes"))
        self.btn_dyn_check_col.setStyleSheet(
            "QPushButton { background-color: #f59e0b; color: white; font-weight: bold; padding: 2px 6px; font-size: 10px; border-radius: 3px; }"
            "QPushButton:hover { background-color: #d97706; }"
        )
        self.btn_dyn_check_col.clicked.connect(self._check_dynamic_collisions)
        h_dyn_title.addWidget(self.btn_dyn_check_col)
        l_interact.addLayout(h_dyn_title)

        # Slider contínuo de 0 a 100% de abertura
        h_slider = QHBoxLayout()
        h_slider.setSpacing(6)
        self.sl_open_dyn = QSlider(Qt.Horizontal)
        self.sl_open_dyn.setRange(0, 100)
        self.sl_open_dyn.setValue(0)
        self.sl_open_dyn.setToolTip(tr("Arraste para abrir ou fechar as portas e gavetas progressivamente em tempo real"))
        self.sl_open_dyn.valueChanged.connect(self._on_dynamic_slider_changed)
        h_slider.addWidget(self.sl_open_dyn, 1)

        self.lbl_open_pct = QLabel("0%")
        self.lbl_open_pct.setStyleSheet("font-weight: bold; font-size: 10px; min-width: 32px;")
        h_slider.addWidget(self.lbl_open_pct)
        l_interact.addLayout(h_slider)

        # Botões rápidos: Fechar (0%), 50%, Abrir Tudo (100%), e Ferramenta Interativa de Clique (I)
        h_quick_btns = QHBoxLayout()
        h_quick_btns.setSpacing(3)
        btn_close_all = QPushButton(tr("Fechar"))
        btn_close_all.setStyleSheet("font-size: 10px; padding: 3px;")
        btn_close_all.clicked.connect(lambda: self.sl_open_dyn.setValue(0))
        h_quick_btns.addWidget(btn_close_all)

        btn_half_all = QPushButton("50%")
        btn_half_all.setStyleSheet("font-size: 10px; padding: 3px;")
        btn_half_all.clicked.connect(lambda: self.sl_open_dyn.setValue(50))
        h_quick_btns.addWidget(btn_half_all)

        btn_open_all = QPushButton("100%")
        btn_open_all.setStyleSheet("font-size: 10px; padding: 3px;")
        btn_open_all.clicked.connect(lambda: self.sl_open_dyn.setValue(100))
        h_quick_btns.addWidget(btn_open_all)

        btn_tool_click = QPushButton(tr("👆 Clicar no 3D"))
        btn_tool_click.setToolTip(tr("Ativa o cursor interativo para clicar individualmente em qualquer porta ou gaveta"))
        btn_tool_click.setStyleSheet("font-size: 10px; font-weight: bold; padding: 3px;")
        btn_tool_click.clicked.connect(self._activate_interact_tool)
        h_quick_btns.addWidget(btn_tool_click)
        l_interact.addLayout(h_quick_btns)

        # Banner de resultado de colisão
        self.lbl_collision_warn = QLabel("")
        self.lbl_collision_warn.setStyleSheet(
            "background-color: #fef2f2; color: #b91c1c; font-size: 10px; font-weight: bold; "
            "padding: 4px; border: 1px solid #fecaca; border-radius: 3px;"
        )
        self.lbl_collision_warn.setWordWrap(True)
        self.lbl_collision_warn.setVisible(False)
        l_interact.addWidget(self.lbl_collision_warn)

        self._main_layout.addWidget(self.card_interact)

        # ── Card de Edição de Iluminação (quando uma luz for clicada no 3D) ──
        self.card_luz = QFrame()
        self.card_luz.setStyleSheet(
            "QFrame { background-color: palette(base); border: 1px solid #0284C7; border-radius: 5px; padding: 6px; }"
        )
        l_luz = QVBoxLayout(self.card_luz)
        l_luz.setContentsMargins(4, 4, 4, 4)
        l_luz.setSpacing(6)

        lbl_luz_header = QLabel(tr("💡 <b>Edição de Luz (3D)</b>"))
        lbl_luz_header.setStyleSheet("color: #0284C7; font-size: 11px;")
        l_luz.addWidget(lbl_luz_header)

        self.lbl_luz_nome = QLabel(tr("Luz Selecionada"))
        self.lbl_luz_nome.setStyleSheet("font-weight: bold; font-size: 11px; color: palette(text);")
        l_luz.addWidget(self.lbl_luz_nome)

        # Botão Ligar/Desligar
        self.btn_luz_toggle = QPushButton(tr("Desligar Luz"))
        self.btn_luz_toggle.setStyleSheet("QPushButton { background-color: #059669; color: white; font-weight: bold; padding: 5px; border-radius: 4px; }")
        self.btn_luz_toggle.clicked.connect(self._toggle_light_on_off)
        l_luz.addWidget(self.btn_luz_toggle)

        form_luz = QFormLayout()
        form_luz.setContentsMargins(0, 2, 0, 2)
        form_luz.setSpacing(5)

        # Tipo de Distribuição da Luz (Omni 360° vs Spot Direcionado)
        self.cb_luz_tipo = QComboBox()
        self.cb_luz_tipo.addItem(tr("💡 Omni (Todas as direções 360°)"), "point")
        self.cb_luz_tipo.addItem(tr("🎯 Spot Direcional (Foco para baixo)"), "spot")
        self.cb_luz_tipo.currentIndexChanged.connect(self._on_sidebar_light_tipo_changed)
        form_luz.addRow(tr("Distribuição:"), self.cb_luz_tipo)

        # Potência
        self.sp_luz_power = QSpinBox()
        self.sp_luz_power.setRange(10, 10000)
        self.sp_luz_power.setSingleStep(50)
        self.sp_luz_power.setSuffix(" W")
        self.sp_luz_power.valueChanged.connect(self._on_sidebar_light_prop_changed)
        form_luz.addRow(tr("Potência:"), self.sp_luz_power)

        # Kelvin
        h_k = QHBoxLayout()
        self.sl_luz_kelvin = QSlider(Qt.Horizontal)
        self.sl_luz_kelvin.setRange(2200, 6500)
        self.sl_luz_kelvin.setSingleStep(100)
        self.sl_luz_kelvin.valueChanged.connect(self._on_sidebar_light_prop_changed)
        h_k.addWidget(self.sl_luz_kelvin, 1)
        self.lbl_luz_kelvin = QLabel("2700K")
        self.lbl_luz_kelvin.setStyleSheet("font-weight: bold; font-size: 10px;")
        h_k.addWidget(self.lbl_luz_kelvin)
        form_luz.addRow(tr("Kelvin:"), h_k)

        # Altura Z
        h_z = QHBoxLayout()
        self.sp_luz_z = QDoubleSpinBox()
        self.sp_luz_z.setRange(-10.0, 50.0)
        self.sp_luz_z.setSingleStep(0.05)
        self.sp_luz_z.setDecimals(2)
        self.sp_luz_z.setSuffix(" m")
        self.sp_luz_z.valueChanged.connect(self._on_sidebar_light_z_changed)
        h_z.addWidget(self.sp_luz_z, 1)

        btn_z_up = QPushButton("▲")
        btn_z_up.setToolTip("Subir 10cm (+0.10m)")
        btn_z_up.setMaximumWidth(28)
        btn_z_up.clicked.connect(lambda: self.sp_luz_z.setValue(self.sp_luz_z.value() + 0.10))
        h_z.addWidget(btn_z_up)

        btn_z_dn = QPushButton("▼")
        btn_z_dn.setToolTip("Descer 10cm (-0.10m)")
        btn_z_dn.setMaximumWidth(28)
        btn_z_dn.clicked.connect(lambda: self.sp_luz_z.setValue(self.sp_luz_z.value() - 0.10))
        h_z.addWidget(btn_z_dn)
        form_luz.addRow(tr("Altura (Z):"), h_z)

        # Ângulo do facho (Spot)
        self.row_luz_ang = QWidget()
        l_ang = QHBoxLayout(self.row_luz_ang)
        l_ang.setContentsMargins(0, 0, 0, 0)
        self.sp_luz_ang = QSpinBox()
        self.sp_luz_ang.setRange(10, 120)
        self.sp_luz_ang.setSuffix("°")
        self.sp_luz_ang.valueChanged.connect(self._on_sidebar_light_prop_changed)
        l_ang.addWidget(self.sp_luz_ang)
        form_luz.addRow(tr("Ângulo Facho:"), self.row_luz_ang)

        l_luz.addLayout(form_luz)

        # Botão Mirar Spot no 3D
        self.btn_luz_aim = QPushButton(tr("🎯 Mirar Spot no 3D"))
        self.btn_luz_aim.setStyleSheet("QPushButton { background-color: #0284C7; color: white; font-weight: bold; padding: 6px; border-radius: 4px; }")
        self.btn_luz_aim.clicked.connect(self._aim_selected_light)
        l_luz.addWidget(self.btn_luz_aim)

        # Botões de Ação: Mover e Excluir
        h_act = QHBoxLayout()
        self.btn_luz_move = QPushButton(tr("📍 Reposicionar"))
        self.btn_luz_move.setStyleSheet("QPushButton { background-color: #2563EB; color: white; font-weight: bold; padding: 6px; border-radius: 4px; }")
        self.btn_luz_move.clicked.connect(self._reposition_selected_light)
        h_act.addWidget(self.btn_luz_move)

        self.btn_luz_delete = QPushButton(tr("🗑️ Excluir"))
        self.btn_luz_delete.setStyleSheet("QPushButton { background-color: #DC2626; color: white; font-weight: bold; padding: 6px; border-radius: 4px; }")
        self.btn_luz_delete.clicked.connect(self._delete_selected_light)
        h_act.addWidget(self.btn_luz_delete)
        l_luz.addLayout(h_act)

        # Botão para limpar/excluir todas as luzes do projeto
        self.btn_luz_clear_all = QPushButton(tr("🧹 Remover Todas as Luzes"))
        self.btn_luz_clear_all.setToolTip("Exclui todas as luminárias (tanto objetos 3D quanto luzes legadas salvas no documento)")
        self.btn_luz_clear_all.setStyleSheet("QPushButton { background-color: #4B5563; color: #F3F4F6; font-size: 10px; padding: 4px; border-radius: 4px; margin-top: 4px; }")
        self.btn_luz_clear_all.clicked.connect(self._delete_all_lights)
        l_luz.addWidget(self.btn_luz_clear_all)

        self.card_luz.setVisible(False)
        self._main_layout.addWidget(self.card_luz)
        self._selected_light_idx: int | None = None
        self._selected_light_grp: Group | None = None

    def _ensure_form_built(self) -> None:
        """Constrói os ~100 widgets do formulário sob demanda na primeira interação."""
        if self._form_built:
            return
        self._form_built = True
        main_layout = self._main_layout

        self._build_walls_card(main_layout)

        # Scroll com o Formulário de Edição
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.form_container = QWidget()
        self.form_vbox = QVBoxLayout(self.form_container)
        self.form_vbox.setContentsMargins(0, 2, 0, 2)
        self.form_vbox.setSpacing(6)

        # Abas de Configuração do Módulo (5 Categorias)
        self.tabs_module = QTabWidget()
        self.tabs_module.setObjectName("trazomobConfigTabs")
        self.tabs_module.setUsesScrollButtons(True)
        self.tabs_module.setStyleSheet(
            """
            QTabWidget#trazomobConfigTabs::pane {
                border: 1px solid palette(mid);
                border-radius: 6px;
                background: palette(window);
                top: -1px;
                padding: 2px;
            }
            QTabWidget#trazomobConfigTabs QTabBar::tab {
                background: palette(button);
                color: palette(text);
                border: 1px solid palette(mid);
                border-bottom: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                padding: 5px 8px;
                margin-right: 2px;
                font-size: 11px;
                font-weight: 600;
            }
            QTabWidget#trazomobConfigTabs QTabBar::tab:hover {
                background: palette(midlight);
            }
            QTabWidget#trazomobConfigTabs QTabBar::tab:selected {
                background: palette(highlight);
                color: palette(highlighted-text);
                border-color: palette(highlight);
            }
            """
        )

        self.sec_dimensoes = CollapsibleSection(tr("Dimensões Principais"), "📏", collapsed=False)
        self.sec_frentes = CollapsibleSection(tr("Frentes & Estrutura"), "🚪", collapsed=False)
        self.sec_puxadores = CollapsibleSection(tr("Puxadores & Perfis"), "✨", collapsed=False)
        self.sec_materiais = CollapsibleSection(tr("Materiais & Fitas"), "🎨", collapsed=False)
        self.sec_ajustes = CollapsibleSection(tr("Ajustes Especiais"), "⚙️", collapsed=False)

        tab_defs = [
            (self.sec_dimensoes, tr("📏 Medidas")),
            (self.sec_frentes, tr("🚪 Estrutura")),
            (self.sec_puxadores, tr("✨ Puxadores")),
            (self.sec_materiais, tr("🎨 Materiais")),
            (self.sec_ajustes, tr("⚙️ Avançado")),
        ]
        for idx, (sec, label) in enumerate(tab_defs):
            self.tabs_module.addTab(sec, label)
            sec.bind_tab(self.tabs_module, idx)

        self.form_vbox.addWidget(self.tabs_module)
        self.form_vbox.addStretch(1)

        # Alias de compatibilidade
        self.form_layout = self.sec_dimensoes.form_layout

        self._build_trocar_tipo_section()
        self._build_medidas_section()
        self._build_esquadria_rows()
        self._build_puxadores_section()
        self._build_materiais_section()
        self._build_frentes_section()
        self._build_ajustes_section()
        # Conectar atualização reativa de badges
        self.sp_largura.valueChanged.connect(self._update_badges)
        self.sp_altura.valueChanged.connect(self._update_badges)
        self.sp_prof.valueChanged.connect(self._update_badges)
        self.sp_elevacao.valueChanged.connect(self._update_badges)
        self.sp_qtd_elem.valueChanged.connect(self._update_badges)
        self.sp_qtd_elem.valueChanged.connect(self._on_portas_balcao_changed)
        self.sp_prateleiras.valueChanged.connect(self._update_badges)
        self.sp_qtd_elem.valueChanged.connect(self._sync_nicho_prateleiras_from_qtd)
        self.sp_prateleiras.valueChanged.connect(self._sync_nicho_qtd_from_prateleiras)
        self.cb_puxador_tipo.currentTextChanged.connect(self._update_badges)
        self.cb_material.currentTextChanged.connect(self._update_badges)

        self.scroll_area.setWidget(self.form_container)
        main_layout.addWidget(self.scroll_area)

        # --- Botões de Ação na Barra Lateral ---
        # Linha horizontal compacta para máxima otimização de espaço
        self.actions_bar = QWidget()
        l_actions = QHBoxLayout(self.actions_bar)
        l_actions.setContentsMargins(0, 4, 0, 4)
        l_actions.setSpacing(6)

        # 1. Botão Principal: Aplicar no Módulo Selecionado
        self.btn_apply = QPushButton(tr("🔄 Aplicar"))
        self.btn_apply.setToolTip(tr("Aplicar alterações no módulo 3D selecionado"))
        self.btn_apply.setStyleSheet(
            "QPushButton { background-color: #16A34A; color: white; font-weight: bold; padding: 6px 10px; border-radius: 5px; font-size: 11px; }"
            "QPushButton:hover { background-color: #15803D; }"
            "QPushButton:disabled { background-color: #94A3B8; }"
        )
        self.btn_apply.clicked.connect(self._apply_changes_to_selected)
        l_actions.addWidget(self.btn_apply, stretch=2)

        # 2. Botão Novo: Aplicar a Todos os Módulos da Mesma Classe
        self.btn_apply_same_class = QToolButton()
        self.btn_apply_same_class.setText("👥")
        self.btn_apply_same_class.setToolTip(tr("Aplicar configurações (materiais, puxadores, fitas, rodapé) em todos os módulos da mesma classe"))
        self.btn_apply_same_class.setStyleSheet(
            "QToolButton { background-color: #0284C7; color: white; font-weight: bold; padding: 6px; border-radius: 5px; font-size: 13px; }"
            "QToolButton:hover { background-color: #0369A1; }"
            "QToolButton:disabled { background-color: #94A3B8; }"
        )
        self.btn_apply_same_class.clicked.connect(self._apply_changes_to_same_class)
        l_actions.addWidget(self.btn_apply_same_class)

        # 3. Salvar como Medidas Padrão
        self.btn_save_defaults = QToolButton()
        self.btn_save_defaults.setText("⭐")
        self.btn_save_defaults.setToolTip(
            tr("⭐ Salvar como Medidas Padrão\n"
               "Salva altura, profundidade, materiais e puxadores atuais como padrão permanente da classe.")
        )
        self.btn_save_defaults.setStyleSheet(
            "QToolButton { background-color: palette(button); color: palette(text); font-weight: bold; padding: 6px; border-radius: 5px; font-size: 13px; border: 1px solid palette(mid); }"
            "QToolButton:hover { background-color: palette(highlight); color: palette(highlighted-text); }"
            "QToolButton:disabled { opacity: 0.5; }"
        )
        self.btn_save_defaults.clicked.connect(self._save_current_as_default)
        l_actions.addWidget(self.btn_save_defaults)

        # 4. Salvar em Meus Módulos
        self.btn_save_user_module = QToolButton()
        self.btn_save_user_module.setText("💾")
        self.btn_save_user_module.setToolTip(
            tr("💾 Salvar em Meus Módulos\n"
               "Salva este módulo completo no seu catálogo pessoal na galeria.")
        )
        self.btn_save_user_module.setStyleSheet(
            "QToolButton { background-color: palette(button); color: palette(text); font-weight: bold; padding: 6px; border-radius: 5px; font-size: 13px; border: 1px solid palette(mid); }"
            "QToolButton:hover { background-color: palette(highlight); color: palette(highlighted-text); }"
            "QToolButton:disabled { opacity: 0.5; }"
        )
        self.btn_save_user_module.clicked.connect(self._save_current_to_user_modules)
        l_actions.addWidget(self.btn_save_user_module)

        # 5. Excluir Módulo Selecionado
        self.btn_delete = QToolButton()
        self.btn_delete.setText("🗑️")
        self.btn_delete.setToolTip(tr("🗑️ Excluir Módulo Selecionado (Del)"))
        self.btn_delete.setStyleSheet(
            "QToolButton { background-color: #DC2626; color: white; font-weight: bold; padding: 6px; border-radius: 5px; font-size: 13px; }"
            "QToolButton:hover { background-color: #B91C1C; }"
            "QToolButton:disabled { background-color: #94A3B8; }"
        )
        self.btn_delete.clicked.connect(self._delete_selected)
        l_actions.addWidget(self.btn_delete)

        main_layout.addWidget(self.actions_bar)


        # Atualiza estado inicial
        self._set_editor_enabled(False)


