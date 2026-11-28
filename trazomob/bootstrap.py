# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""TrazoMob plugin bootstrap.

Extracted from ``__init__.py`` to keep the root module small. Registers the
TrazoMob sidebar panel, toolbar, outliner, pickables, and context menu.

The tool classes (``TrazoMobTool`` and ``CabinetInteractTool``) remain defined
in ``__init__.py``: the IngeTrazo plugin loader only discovers ``Tool`` classes
whose ``__module__`` is the plugin module itself, so they are passed in here
as parameters.
"""

from __future__ import annotations

import logging
import weakref

_LIGHT_DLGS: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
_RENDER_DLGS: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QToolBar

from .domain.i18n import tr
from .integrations import platform as host
from .production.cut_plan_viewer import CutPlanViewerDialog
from .production.parts import extract_parts
from .ui.icons import (
    make_align_tool_icon,
    make_cabinet_icon,
    make_cut_plan_icon,
    make_cutlist_icon,
    make_free_zoom_icon,
    make_interact_icon,
    make_light_icon,
    make_magnet_snap_icon,
    make_pbr_material_icon,
    make_render_icon,
    make_rotate_ccw_icon,
    make_rotate_cw_icon,
    make_ruler_icon,
    make_style_palette_icon,
    make_wall_icon,
)
from .ui.sidebar_panel import TrazoMobSidebarPanel

logger = logging.getLogger("trazomob")


def install(app, TrazoMobTool, CabinetInteractTool) -> None:
    """Initializes the TrazoMob plugin by registering the sidebar, toolbar, and context menus."""
    # First-party: the host calls TrazoMob directly. Here we only need
    # to register the window for link warnings in the status bar.
    from .integrations.library_links import set_host_window

    main_window = getattr(app, "window", None)
    viewport = getattr(app, "viewport", None)
    set_host_window(main_window)

    def _vp():
        return host.active_viewport(window=main_window, viewport=viewport, app=app)

    _snap_state = {"enabled": True}
    _wired_viewports = []

    # Stable keys for shortcuts remembered by the host: without objectName,
    # each action's translated text would become a different key in every
    # language and the saved shortcut would disappear when switching languages.
    from .domain.i18n import source_text

    def _name_action(act):
        if act.isSeparator() or act.objectName() or not act.text():
            return
        src = source_text(act.text())
        key = "".join(c if c.isalnum() else "_" for c in src).strip("_")
        act.setObjectName("trazomob_" + (key or "action"))

    if viewport is not None:
        # Preload hardware prototypes in the background for instant double-click
        from PySide6.QtCore import QTimer
        def _warmup_hardware():
            try:
                from .builders.hardware_geometry import _load_hinge_prototypes
                _load_hinge_prototypes()
            except Exception:
                logger.debug("Falha ao pré-carregar protótipos de ferragens", exc_info=True)
        QTimer.singleShot(100, _warmup_hardware)

    # 1. Side Tray Dock panel
    sidebar_panel = TrazoMobSidebarPanel(app)
    sidebar_dock = None
    if hasattr(app, "add_panel"):
        sidebar_dock = app.add_panel("TrazoMob", sidebar_panel)
    elif main_window is not None and hasattr(main_window, "_register_extension_dock"):
        from PySide6.QtWidgets import QDockWidget
        sidebar_dock = QDockWidget("TrazoMob", main_window)
        sidebar_dock.setObjectName("extension_trazomob")
        sidebar_dock.setWidget(sidebar_panel)
        host.register_extension_dock(main_window, sidebar_dock)
    elif main_window is not None and hasattr(main_window, "addDockWidget"):
        from PySide6.QtWidgets import QDockWidget
        sidebar_dock = QDockWidget("TrazoMob", main_window)
        sidebar_dock.setObjectName("extension_trazomob")
        sidebar_dock.setWidget(sidebar_panel)
        main_window.addDockWidget(Qt.RightDockWidgetArea, sidebar_dock)

    if sidebar_dock is not None:
        sidebar_panel.set_dock(sidebar_dock)

    # Initialize the wall face selection manager (WallSelectionManager)
    from .wall.selection import WallSelectionManager
    wall_mgr = WallSelectionManager.get_instance(_vp(), sidebar_panel)
    wall_mgr.install_overlay()

    def _wire_trazomob_viewport(vp):
        if vp is None:
            return
        from PySide6.QtCore import QTimer
        setattr(vp, "_trazomob_sidebar", sidebar_panel)
        mod_ribbon = getattr(main_window, "_trazomob_module_ribbon", None) if main_window is not None else None
        if mod_ribbon is not None:
            setattr(vp, "_trazomob_ribbon", mod_ribbon)
        if vp not in _wired_viewports:
            _wired_viewports.append(vp)
        drag_f = getattr(vp, "_trazomob_drag_filter", None)
        if drag_f is None:
            from .interaction.magnetic_drag import MagneticModuleDragFilter
            drag_f = MagneticModuleDragFilter(vp, parent=vp)
            vp.installEventFilter(drag_f)
            setattr(vp, "_trazomob_drag_filter", drag_f)
        drag_f.snap_enabled = bool(_snap_state["enabled"])
        WallSelectionManager.get_instance(vp, sidebar_panel).install_overlay()
        # Auto-Migration and Backward Compatibility
        # Runs only ONCE after loading the scene, never on the recurring sceneVersionChanged signal
        scene = getattr(vp, "scene", None)
        if scene is not None and not getattr(scene, "_trazomob_migrated", False):
            setattr(scene, "_trazomob_migrated", True)
            from .domain.migration import migrate_scene_trazomob_entities
            QTimer.singleShot(250, lambda s=scene, v=vp: migrate_scene_trazomob_entities(s, viewport=v))

    for init_vp in host.all_viewports(window=main_window, viewport=viewport, app=app):
        _wire_trazomob_viewport(init_vp)

    # Wall cutouts are DERIVED from millwork opening positions: after any document
    # change (edit, Ctrl+Z, Ctrl+Y, Open, tab switch), recalculate them and sync context.
    from PySide6.QtCore import QTimer
    _resync_state = {"pending": False, "busy": False}

    def _do_resync():
        _resync_state["pending"] = False
        if _resync_state["busy"]:
            return
        _resync_state["busy"] = True
        try:
            vp = _vp()
            _wire_trazomob_viewport(vp)
            if vp is not None:
                wall_mgr.viewport = vp
                wall_mgr.sync_with_scene(getattr(vp, "scene", None))
                if hasattr(vp, "scene"):
                    from .wall.mesh_builder import WallMeshBuilder
                    if WallMeshBuilder.sync_scene_wall_openings(vp.scene):
                        vp.update()
            if main_window is not None:
                dlg = getattr(main_window, "_trazomob_dialog", None)
                if dlg is not None and dlg.isVisible() and hasattr(dlg, "sync_to_active_document"):
                    dlg.sync_to_active_document(vp)
                light_dlg = getattr(main_window, "_trazomob_light_dlg", None)
                if light_dlg is not None and light_dlg.isVisible() and hasattr(light_dlg, "sync_to_active_document"):
                    light_dlg.sync_to_active_document(vp)
        except Exception as exc:
            logger.debug("re-sincronização dos vãos da parede falhou: %s", exc)
        finally:
            _resync_state["busy"] = False

    def _schedule_resync():
        if not _resync_state["pending"] and not _resync_state["busy"]:
            _resync_state["pending"] = True
            QTimer.singleShot(0, _do_resync)

    if hasattr(app, "on_document_changed"):
        app.on_document_changed(_schedule_resync)
    if main_window is not None and hasattr(main_window, "documentChanged"):
        try:
            main_window.documentChanged.connect(_schedule_resync)
        except Exception:
            pass

    if hasattr(app, "on_document_closed"):
        def _on_doc_closed(closed_scene):
            nonlocal viewport
            # ``viewport`` was the tab open at setup. Its closure must not
            # keep that document alive after the tab is closed: the app is
            # still here, and ExtensionApp.viewport follows the active tab.
            try:
                if (viewport is not None and closed_scene is not None
                        and getattr(viewport, "scene", None) is closed_scene):
                    viewport = None
            except RuntimeError:        # C++ object already deleted
                viewport = None
            surviving = []
            for tracked_vp in _wired_viewports:
                try:
                    if closed_scene is not None and getattr(tracked_vp, "scene", None) is closed_scene:
                        drag_f = getattr(tracked_vp, "_trazomob_drag_filter", None)
                        if drag_f is not None and hasattr(drag_f, "cleanup"):
                            drag_f.cleanup()
                        continue
                    surviving.append(tracked_vp)
                except RuntimeError:
                    continue
            _wired_viewports[:] = surviving
            active_vp = _vp()
            wall_mgr.viewport = active_vp
            wall_mgr.sync_with_scene(getattr(active_vp, "scene", None))

        app.on_document_closed(_on_doc_closed)

    # Initialize the subtle graphic light visualizer (spotlight cones and LED strips)
    # 2. Native identification in IngeTrazo's Object Browser / Tree (Outliner)
    # As specified in docs/plugins.md (app.add_outliner_kind)
    if hasattr(app, "add_outliner_kind"):
        from .domain.entity import get_trazomob

        def _trazomob_outliner_provider(group):
            tm = get_trazomob(group)
            if not tm:
                return None
            kind = tm.get("kind", "")
            if kind == "module":
                tipo = str(tm.get("tipo", "Modulo"))
                w = tm.get("largura", tm.get("largura_mm", 0))
                h = tm.get("altura", tm.get("altura_mm", 0))
                d = tm.get("profundidade", tm.get("profundidade_mm", 0))
                dim_str = f"{int(w)} x {int(h)} x {int(d)} mm" if w and h and d else "-"
                return {
                    "type": tr("Movel"),
                    "props": [
                        (tr("Tipo"), tipo),
                        (tr("Dimensoes"), dim_str),
                    ],
                }
            elif kind == "wall":
                alt = tm.get("altura", 2.6)
                esp = tm.get("espessura", 0.15)
                n_segs = len(tm.get("pontos", []))
                return {
                    "type": tr("Parede"),
                    "props": [
                        (tr("Altura"), f"{float(alt):.2f} m"),
                        (tr("Espessura"), f"{float(esp) * 100:.0f} cm"),
                        (tr("Segmentos"), str(max(1, n_segs - 1))),
                    ],
                }
            elif kind == "esquadria":
                tipo = str(tm.get("tipo", "Esquadria"))
                w = tm.get("largura_mm", 0)
                h = tm.get("altura_mm", 0)
                p = tm.get("peitoril_mm", 0)
                med_str = f"{int(w)} x {int(h)} mm" if w and h else "-"
                return {
                    "type": tr("Esquadria"),
                    "props": [
                        (tr("Tipo"), tipo),
                        (tr("Medidas"), med_str),
                        (tr("Peitoril"), f"{int(p)} mm" if p else "0 mm"),
                    ],
                }
            elif kind in ("floor", "ceiling", "bancada", "light"):
                nomes = {"floor": tr("Piso"), "ceiling": tr("Teto"), "bancada": tr("Bancada"), "light": tr("Iluminacao")}
                return {"type": nomes.get(kind, "TrazoMob"), "props": []}
            return None

        # First-party: reads only group.ext, so the outliner may still patch
        # rows incrementally (third-party providers can add arbitrary data).
        _trazomob_outliner_provider.is_first_party = True
        app.add_outliner_kind(_trazomob_outliner_provider)

    if hasattr(app, "add_overlay"):
        from .render.lighting import TrazoMobLightVisualizer
        app.add_overlay(
            lambda vp, painter: TrazoMobLightVisualizer.draw_trazomob_lights(vp, painter)
        )

    # Allow selecting luminaires and light sources via the native Select tool and deleting with Delete
    if hasattr(app, "add_pickable"):
        from .render.lighting import TrazoMobLightVisualizer
        def _pick_trazomob_light(vp, px, py):
            res = TrazoMobLightVisualizer.pick_light_or_target(vp, px, py)
            return res if res is not None else None

        def _on_trazomob_light_selected(hit):
            vp = _vp()
            if hit is None:
                TrazoMobLightVisualizer.set_selected_index(None, vp)
                sidebar_panel.clear_light_selection()
            else:
                action, idx = hit
                TrazoMobLightVisualizer.set_selected_index(idx, vp)
                sidebar_panel.load_light(idx)

        def _delete_trazomob_light(hit):
            if hit is not None:
                action, idx = hit
                sidebar_panel.load_light(idx)
                sidebar_panel._delete_selected_light()

        app.add_pickable(
            pick=_pick_trazomob_light,
            on_select=_on_trazomob_light_selected,
            delete=_delete_trazomob_light,
        )

    if hasattr(app, "add_menu_action") and sidebar_dock is not None:
        app.add_menu_action(
            tr("Painel Lateral do TrazoMob"),
            sidebar_panel.focus_panel,
            tip=tr("Abre o editor de módulos dinâmicos na barra lateral."),
        )

    # 2. Create toolbar in the main interface
    if main_window is not None and hasattr(main_window, "addToolBar"):
        from PySide6.QtWidgets import QWidget
        parent_widget = main_window if isinstance(main_window, QWidget) else None
        tb = QToolBar("TrazoMob", parent_widget)
        tb.setObjectName("toolbar_trazomob")
        tb.setWindowTitle("TrazoMob")
        tb.setMovable(True)
        tb.setFloatable(True)
        tb.setIconSize(QSize(24, 24))
        tb.setToolButtonStyle(Qt.ToolButtonIconOnly)

        act_side = QAction(make_cabinet_icon(), tr("Editor Lateral"), main_window)
        act_side.setStatusTip(tr("Abrir e focar o editor do TrazoMob na barra lateral"))
        act_side.setToolTip(tr("Editor na Barra Lateral (TrazoMob)"))
        act_side.triggered.connect(sidebar_panel.focus_panel)
        tb.addAction(act_side)

        # Direct button to Build Walls (2D Floorplan)
        act_wall = QAction(make_wall_icon(), tr("Construir Paredes"), main_window)
        act_wall.setStatusTip(tr("Abrir editor de Planta Baixa 2D para desenhar paredes e gerar sólido 3D"))
        act_wall.setToolTip(tr("🧱 Construir Paredes (Planta Baixa 2D) — Atalho: W"))

        def _open_wall_floorplan_dialog():
            from .wall.floorplan_dialog import WallFloorplanDialog
            dlg = WallFloorplanDialog(_vp(), parent=main_window)
            dlg.exec()

        act_wall.triggered.connect(_open_wall_floorplan_dialog)
        tb.addAction(act_wall)

        # Direct button to Configure Height Rulers
        act_ruler = QAction(make_ruler_icon(), tr("Réguas de Altura"), main_window)
        act_ruler.setStatusTip(tr("Configurar, criar e personalizar réguas de altura e linhas-guia magnéticas de parede"))
        act_ruler.setToolTip(tr("📏 Réguas de Altura & Linhas-Guia (Personalizar / Criar)"))
        def _open_ruler_config():
            from .ui.ruler_editor_dialog import RulerEditorDialog
            from .wall.guides import WallGuideRulerManager
            ruler_mgr = WallGuideRulerManager.get_instance()
            dlg = RulerEditorDialog(parent=main_window, ruler_mgr=ruler_mgr)
            if dlg.exec():
                if hasattr(sidebar_panel, "cb_regua_ambiente"):
                    sidebar_panel.cb_regua_ambiente.blockSignals(True)
                    sidebar_panel.cb_regua_ambiente.clear()
                    sidebar_panel.cb_regua_ambiente.addItems(list(ruler_mgr.presets.keys()))
                    sidebar_panel.cb_regua_ambiente.setCurrentText(ruler_mgr.active_preset_name)
                    sidebar_panel.cb_regua_ambiente.blockSignals(False)
                vp = _vp()
                if vp is not None:
                    vp.update()
        act_ruler.triggered.connect(_open_ruler_config)
        tb.addAction(act_ruler)

        # Tabbed Modules Toolbar (instantiated on demand on first click)
        setattr(main_window, "_trazomob_module_ribbon", None)

        def _toggle_module_ribbon():
            vp = _vp()
            module_ribbon = getattr(main_window, "_trazomob_module_ribbon", None)
            if module_ribbon is None:
                from .ui.module_ribbon import TrazoMobModuleRibbonBar
                module_ribbon = TrazoMobModuleRibbonBar(main_window, vp, sidebar_panel)
                main_window.addToolBar(Qt.TopToolBarArea, module_ribbon)
                main_window.insertToolBarBreak(module_ribbon)
                setattr(main_window, "_trazomob_module_ribbon", module_ribbon)
                if vp is not None:
                    setattr(vp, "_trazomob_ribbon", module_ribbon)
                module_ribbon.show()
                act_mod.setChecked(True)
                if hasattr(vp, "flash_status"):
                    vp.flash_status(tr("🧱 Catálogo de Módulos ativo. Escolha a aba e clique no móvel."))
                return

            if module_ribbon.isVisible():
                module_ribbon.hide()
                act_mod.setChecked(False)
            else:
                if vp is not None:
                    setattr(vp, "_trazomob_ribbon", module_ribbon)
                module_ribbon.show()
                act_mod.setChecked(True)
                if hasattr(vp, "flash_status"):
                    vp.flash_status(tr("🧱 Catálogo de Módulos ativo. Escolha a aba e clique no móvel."))

        act_mod = QAction(make_cabinet_icon(), tr("Módulos"), main_window)
        act_mod.setCheckable(True)
        act_mod.setStatusTip(tr("Abrir/fechar barra superior de módulos por abas (Cozinha, Quarto, Banheiro...)"))
        act_mod.setToolTip(tr("🧱 Catálogo de Módulos (Abas por Ambiente) — TrazoMob"))
        act_mod.triggered.connect(_toggle_module_ribbon)
        tb.addAction(act_mod)

        def _rotate_active(deg: float):
            vp = _vp()
            if vp is None or not hasattr(vp, "scene"):
                return
            from .domain.assembly import is_module
            from .interaction.align_tools import (
                resolve_rotatable_groups,
                rotate_groups_with_command,
            )

            sel = list(getattr(vp.scene, "selection", []) or [])
            targets = resolve_rotatable_groups(vp.scene, sel)
            if not targets and not sel and getattr(vp.scene, "groups", None):
                for g in reversed(vp.scene.groups):
                    if is_module(g):
                        targets = [g]
                        break
            if targets:
                rotated = rotate_groups_with_command(targets, deg, vp)
                if rotated and hasattr(vp, "flash_status"):
                    if len(rotated) == 1:
                        g = rotated[0]
                        kind_label = "Módulo" if is_module(g) else "Objeto"
                        vp.flash_status(f"{kind_label} '{getattr(g, 'name', 'Objeto')}' girado {int(deg)}°")
                    else:
                        vp.flash_status(f"{len(rotated)} objetos girados {int(deg)}°")
            elif hasattr(vp, "flash_status"):
                vp.flash_status(tr("Selecione um móvel para girar 90°"))

        act_rot_ccw = QAction(make_rotate_ccw_icon(), tr("Girar 90° Anti-horário"), main_window)
        act_rot_ccw.setStatusTip(tr("Girar objeto ou módulo selecionado 90° para a esquerda (anti-horário)"))
        act_rot_ccw.setToolTip(tr("Girar 90° Anti-horário (↺)"))
        act_rot_ccw.triggered.connect(lambda: _rotate_active(-90.0))
        tb.addAction(act_rot_ccw)

        act_rot_cw = QAction(make_rotate_cw_icon(), tr("Girar 90° Horário"), main_window)
        act_rot_cw.setStatusTip(tr("Girar objeto ou módulo selecionado 90° para a direita (horário)"))
        act_rot_cw.setToolTip(tr("Girar 90° Horário (↻)"))
        act_rot_cw.triggered.connect(lambda: _rotate_active(90.0))
        tb.addAction(act_rot_cw)

        act_interact = QAction(make_interact_icon(), tr("Interagir"), main_window)
        act_interact.setStatusTip(tr("Clique nas portas e gavetas do armário para abrir ou fechar no 3D (Atalho: I)"))
        act_interact.setToolTip(tr("Interagir: Abrir/Fechar Portas e Gavetas (Atalho: I)"))
        def _activate_interact():
            key = "plugin_trazomob_CabinetInteractTool"
            host.activate_plugin_tool(main_window, _vp(), key, CabinetInteractTool)
        act_interact.triggered.connect(_activate_interact)
        tb.addAction(act_interact)

        # Interactive button to Align & Rest 3D Objects
        from .interaction.align_tool_interactive import AlignSnapTool
        act_align = QAction(make_align_tool_icon(), tr("Alinhar e Apoiar"), main_window)
        act_align.setStatusTip(tr("Alinhar, apoiar sobre superfícies ou encostar objetos no 3D com precisão (Atalho: Shift+A)"))
        act_align.setToolTip(tr("🎯 Alinhar & Apoiar Objetos (Shift+A) — Clique no objeto e na base (TAB alterna modo)"))
        def _activate_align():
            key = "plugin_trazomob_AlignSnapTool"
            host.activate_plugin_tool(main_window, _vp(), key, AlignSnapTool)
        act_align.triggered.connect(_activate_align)
        tb.addAction(act_align)

        def _open_or_show_dialog(tab_index: int = 0):
            vp = _vp()
            win = host.window_of(main_window, vp)
            dlg = getattr(win, "_trazomob_dialog", None)
            if dlg is None or not dlg.isVisible():
                from .ui.module_dialog import TrazoMobDialog
                dlg = TrazoMobDialog(vp, parent=win)
                if win is not None:
                    setattr(win, "_trazomob_dialog", dlg)
                if hasattr(dlg, "tabs") and 0 <= tab_index < dlg.tabs.count():
                    dlg.tabs.setCurrentIndex(tab_index)
                dlg.show()
            else:
                if hasattr(dlg, "sync_to_active_document"):
                    dlg.sync_to_active_document(vp)
                if hasattr(dlg, "tabs") and 0 <= tab_index < dlg.tabs.count():
                    dlg.tabs.setCurrentIndex(tab_index)
                dlg.raise_()
                dlg.activateWindow()

        act_list = QAction(make_cutlist_icon(), tr("Lista de Peças"), main_window)
        act_list.setStatusTip(tr("Gerar lista de peças, fitas de borda e copiar para o TrazoMob"))
        act_list.setToolTip(tr("Lista de Peças & Fitas de Borda (Ctrl+V)"))
        act_list.triggered.connect(lambda: _open_or_show_dialog(1))
        tb.addAction(act_list)

        act_plan = QAction(make_cut_plan_icon(), tr("Plano de Corte 2D"), main_window)
        act_plan.setStatusTip(tr("Abrir diagrama otimizado de corte de chapas (Nesting 2D)"))
        act_plan.setToolTip(tr("Plano de Corte Otimizado 2D (Nesting)"))
        def _open_plan():
            vp = _vp()
            if vp is None or not hasattr(vp, "scene"):
                return
            parts = extract_parts(vp.scene)
            if not parts:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(
                    main_window,
                    tr("Plano de Corte 2D"),
                    tr("Nenhuma peça de marcenaria encontrada na cena para gerar o plano de corte.\n"
                       "Insira módulos ou desenhe chapas antes de gerar o plano de corte.")
                )
                return
            dlg = CutPlanViewerDialog(parts, parent=main_window)
            dlg.exec()
        act_plan.triggered.connect(_open_plan)
        tb.addAction(act_plan)

        # ── DISPLAY STYLES DROPDOWN BUTTON (REPLACES CLUTTERED TOOLBAR) ──
        from PySide6.QtGui import QActionGroup
        from PySide6.QtWidgets import QMenu, QToolButton

        btn_styles = QToolButton(tb)
        btn_styles.setIcon(make_style_palette_icon())
        btn_styles.setToolTip(tr("Estilos de Visualização (Modos de Face, Arestas, Raio-X)"))
        btn_styles.setStatusTip(tr("Alterar modo de exibição de faces, arestas e transparência"))
        btn_styles.setPopupMode(QToolButton.InstantPopup)
        btn_styles.setStyleSheet("QToolButton::menu-indicator { image: none; }")

        menu_styles = QMenu(btn_styles)

        # 1. Face Style Modes
        from core.style import BUILTIN_STYLES
        group_styles = QActionGroup(menu_styles)

        lbl_section1 = menu_styles.addAction(tr("── Modos de Face ──"))
        lbl_section1.setEnabled(False)

        for preset in BUILTIN_STYLES:
            act_preset = QAction(preset.name, menu_styles)
            act_preset.setCheckable(True)
            group_styles.addAction(act_preset)
            def _apply(_checked=False, p=preset):
                if not host.apply_display_style(main_window, _vp(), p):
                    logger.debug("estilo %r não pôde ser aplicado", p.name)
            act_preset.triggered.connect(_apply)
            menu_styles.addAction(act_preset)


        menu_styles.addSeparator()

        # 2. Transparency / X-Ray
        act_xray = QAction(tr("⚡ Alternar Raio-X (Alt+X)"), menu_styles)
        act_xray.triggered.connect(lambda: host.toggle_xray(main_window, _vp()))
        menu_styles.addAction(act_xray)

        menu_styles.addSeparator()

        # 3. Edges and Profiles
        lbl_section2 = menu_styles.addAction(tr("── Arestas & Perfis ──"))
        lbl_section2.setEnabled(False)

        act_edges = QAction(tr("Arestas"), menu_styles)
        act_edges.setCheckable(True)
        def _toggle_edges(val):
            host.set_style_field(main_window, _vp(), "edges", val)
        act_edges.toggled.connect(_toggle_edges)
        menu_styles.addAction(act_edges)

        act_prof = QAction(tr("Perfis de Contorno"), menu_styles)
        act_prof.setCheckable(True)
        def _toggle_prof(val):
            host.set_style_field(main_window, _vp(), "profiles", val)
        act_prof.toggled.connect(_toggle_prof)
        menu_styles.addAction(act_prof)

        act_back = QAction(tr("Arestas Ocultas / Pontilhadas (K)"), menu_styles)
        act_back.setCheckable(True)
        def _toggle_back(val):
            host.set_style_field(main_window, _vp(), "back_edges", val)
        act_back.toggled.connect(_toggle_back)
        menu_styles.addAction(act_back)

        for _act in menu_styles.actions():
            _name_action(_act)

        # Sync checkbox states when opening the menu
        def _sync_style_dropdown():
            st = getattr(getattr(_vp(), "scene", None), "display_style", None)
            if st is None:
                return
            for a in group_styles.actions():
                a.blockSignals(True)
                a.setChecked(a.text() == st.name)
                a.blockSignals(False)
            act_edges.blockSignals(True)
            act_edges.setChecked(bool(getattr(st, "edges", True)))
            act_edges.blockSignals(False)
            act_prof.blockSignals(True)
            act_prof.setChecked(bool(getattr(st, "profiles", False)))
            act_prof.blockSignals(False)
            act_back.blockSignals(True)
            act_back.setChecked(bool(getattr(st, "back_edges", False)))
            act_back.blockSignals(False)

        menu_styles.aboutToShow.connect(_sync_style_dropdown)
        btn_styles.setMenu(menu_styles)
        tb.addWidget(btn_styles)

        # ── TOGGLE MAGNETIC SNAPS BUTTON (TRAZOMOB) ──
        act_snap = QAction(make_magnet_snap_icon(), tr("Snap Magnético"), main_window)
        act_snap.setCheckable(True)
        act_snap.setChecked(True)
        act_snap.setShortcut("Alt+S")
        act_snap.setToolTip(tr("Alternar Snap Magnético (Móveis e Linhas-Guia) — Atalho: Alt+S"))
        act_snap.setStatusTip(tr("Ativar ou desativar atração magnética de módulos ao piso, paredes e linhas-guia"))

        def _on_snap_toggled(checked: bool):
            _snap_state["enabled"] = bool(checked)
            for doc_vp in host.all_viewports(window=main_window, viewport=viewport, app=app):
                drag_f = getattr(doc_vp, "_trazomob_drag_filter", None)
                if drag_f is not None:
                    drag_f.snap_enabled = bool(checked)
            from .wall.guides import WallGuideRulerManager
            ruler_mgr = WallGuideRulerManager.get_instance()
            ruler_mgr.snap_enabled = bool(checked)
            vp = _vp()
            msg = "🧲 Snaps Magnéticos: ATIVADOS" if checked else "⚪ Snaps Magnéticos: DESATIVADOS (Ajuste Fino Livre)"
            if hasattr(vp, "flash_status"):
                vp.flash_status(msg)
            if vp is not None:
                vp.update()

        act_snap.toggled.connect(_on_snap_toggled)
        tb.addAction(act_snap)

        # ── TOGGLE FREE ZOOM / PASS THROUGH SOLIDS BUTTON (TRAZOMOB) ──
        from .interaction.free_zoom import FreeZoomManager
        act_free_zoom = QAction(make_free_zoom_icon(), tr("Zoom Livre / Atravessar"), main_window)
        act_free_zoom.setCheckable(True)
        act_free_zoom.setChecked(False)
        act_free_zoom.setShortcut("Alt+Z")
        act_free_zoom.setToolTip(tr("Zoom Contínuo Livre (Atravessar Sólidos / Estilo SketchUp) — Atalho: Alt+Z"))
        act_free_zoom.setStatusTip(tr("Permite que o zoom da roda atravesse paredes, portas e armários sem travar na casca externa"))

        def _on_free_zoom_toggled(checked: bool):
            FreeZoomManager.get_instance().is_enabled = bool(checked)
            vp = _vp()
            msg = "🚪 Zoom Livre (Atravessar Sólidos): ATIVADO" if checked else "🔒 Zoom Órbita Padrão: RESTAURADO"
            if hasattr(vp, "flash_status"):
                vp.flash_status(msg)
            if vp is not None:
                vp.update()

        act_free_zoom.toggled.connect(_on_free_zoom_toggled)
        tb.addAction(act_free_zoom)

        # ── PBR MATERIALS & SHADERS BUTTON (TRAZOMOB) ──
        act_pbr = QAction(make_pbr_material_icon(), tr("Materiais PBR (TrazoMob)"), main_window)
        act_pbr.setToolTip(tr("Materiais & Shaders PBR (Acabamentos, Reflexo, Relevo e Conta-gotas)"))
        act_pbr.setStatusTip(tr("Configurar propriedades PBR dos materiais da cena ou capturar face com conta-gotas"))
        def _open_pbr_editor():
            from .ui.material_editor_dialog import open_material_editor
            open_material_editor(viewport=_vp(), parent=main_window)
        act_pbr.triggered.connect(_open_pbr_editor)
        tb.addAction(act_pbr)

        # ── LIGHTING & PHYSICAL SPOTLIGHTS BUTTON (TRAZOMOB) ──
        act_light = QAction(make_light_icon(), tr("Iluminação e Spots Físicos (TrazoMob)"), main_window)
        act_light.setToolTip(tr("Gerenciador de Iluminação e Spots Físicos Profissionais"))
        act_light.setStatusTip(tr("Inserir e controlar spots, fitas LED, potência e cor da luz para o render"))
        def _open_light_manager():
            from .render.lighting import LightManagerDialog
            dlg = LightManagerDialog(_vp(), parent=main_window)
            if main_window is not None:
                _LIGHT_DLGS[main_window] = dlg  # non-modal: viewport must get clicks
            dlg.show()
        act_light.triggered.connect(_open_light_manager)
        tb.addAction(act_light)

        # ── TRAZOMOB PHOTOREALISTIC RENDER BUTTON (BLENDER CYCLES / EEVEE) ──
        act_render = QAction(make_render_icon(), tr("Render Foto-Realista (TrazoMob)"), main_window)
        act_render.setToolTip(tr("Render Foto-Realista de Interiores (Blender Cycles / EEVEE)"))
        act_render.setStatusTip(tr("Gera imagem foto-realista com iluminação de estúdio e materiais PBR"))
        def _open_render_dialog():
            from .render.dialog import TrazoMobRenderDialog
            cur_vp = _vp()
            dlg = _RENDER_DLGS.get(main_window) if main_window is not None else None
            if dlg is None or not dlg.isVisible() or getattr(dlg, "viewport", None) is not cur_vp:
                if dlg is not None and dlg.isVisible():
                    dlg.close()
                dlg = TrazoMobRenderDialog(cur_vp, parent=None)
                dlg.setModal(False)
                if main_window is not None:
                    _RENDER_DLGS[main_window] = dlg
                dlg.show()
            else:
                dlg.raise_()
                dlg.activateWindow()
        act_render.triggered.connect(_open_render_dialog)
        tb.addAction(act_render)

        # ── SUPPRESS / HIDE THE CLUTTERED igz_tb_style TOOLBAR ──
        def _suppress_legacy_style_toolbar():
            toolbar = host.legacy_style_toolbar(main_window)
            if toolbar is not None:
                toolbar.hide()
                toolbar.setVisible(False)
                toolbar.setEnabled(False)

        QTimer.singleShot(200, _suppress_legacy_style_toolbar)
        QTimer.singleShot(1000, _suppress_legacy_style_toolbar)

        for _act in tb.actions():
            _name_action(_act)
            _sub = _act.menu()
            if _sub is not None:
                for _sub_act in _sub.actions():
                    _name_action(_sub_act)

        main_window.addToolBar(Qt.TopToolBarArea, tb)
        # Ensure the TrazoMob toolbar sits on its own row to display
        # all its buttons and tools without being crushed or hidden by Qt overflow
        QTimer.singleShot(0, lambda: main_window.insertToolBarBreak(tb))

    # 3. Right-click context menu
    from .context_menu import build_context_menu

    app.add_context_menu(
        lambda menu, selection: build_context_menu(
            menu, selection, app, sidebar_panel, TrazoMobTool
        )
    )
