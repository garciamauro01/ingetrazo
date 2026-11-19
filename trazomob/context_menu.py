# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Menu de contexto do TrazoMob (botão direito no viewport).

Extraído de ``__init__.py``. O handler recebe ``app``, ``sidebar_panel`` e a
classe ``TrazoMobTool`` para evitar import circular com o módulo-raiz.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QTimer

from core.group import Group

from .domain.i18n import tr
from .domain.engine_state import is_engine_enabled
from .interaction.interact import CabinetInteract

logger = logging.getLogger("trazomob.context_menu")


def build_context_menu(menu, selection, app, sidebar_panel, tool_cls) -> None:
    """Adiciona ao ``menu`` as ações do TrazoMob para a ``selection`` atual."""
    if not is_engine_enabled():
        return
    wall = None
    for item in selection:
        if hasattr(item, "ext") and isinstance(item.ext, dict) and "trazomob_wall" in item.ext:
            wall = item
            break
    if wall is None and hasattr(app, "viewport") and hasattr(app.viewport, "scene"):
        for g in getattr(app.viewport.scene, "groups", []):
            if hasattr(g, "ext") and isinstance(g.ext, dict) and "trazomob_wall" in g.ext:
                children = getattr(g, "children", []) or []
                if any(child in selection for child in children):
                    wall = g
                    break

    if wall is not None:
        # Tenta identificar qual segmento de parede específico foi clicado
        seg_index = None
        params = wall.ext.get("trazomob_wall") or {}
        face_map = params.get("face_segment_map", {})
        if hasattr(app, "viewport") and hasattr(app.viewport, "_context_pixel"):
            px, py = app.viewport._context_pixel
            hit_face, hit_grp = app.viewport.pick_face_any(px, py)
            if hit_grp is wall and hit_face in getattr(wall.mesh, "faces", []):
                f_idx = wall.mesh.faces.index(hit_face)
                seg_index = face_map.get(f_idx)

        is_seg = bool(params.get("is_segmented", False))
        pts_count = len(params.get("pontos", []))

        # Se for monólito contínuo, oferece ação para seccionar em paredes individuais
        if not is_seg and pts_count > 2:
            act_split = menu.addAction(tr("✂️ Seccionar em Paredes Individuais"))
            def _do_split(w=wall):
                if hasattr(app, "viewport") and hasattr(app.viewport, "history"):
                    from .wall.builder import WallBuilderTool, SplitWallGroupCommand
                    subs = WallBuilderTool.split_wall_group_into_segments(w)
                    if len(subs) > 1:
                        app.viewport.history.execute(SplitWallGroupCommand(w, subs))
                        app.viewport.update()
                        if hasattr(app.viewport, "flash_status"):
                            app.viewport.flash_status(f"✂️ Bloco dividido com sucesso em {len(subs)} paredes individuais!")
            act_split.triggered.connect(_do_split)

        seg_text = f" #{seg_index + 1}" if (seg_index is not None and not is_seg) else ""
        act_wall = menu.addAction(f"🧱 Editar Parede{seg_text} na Barra Lateral")
        def _open_wall_side(s_idx=seg_index):
            if hasattr(app, "viewport") and hasattr(app.viewport, "scene"):
                app.viewport.scene.selection = {wall}
                app.viewport.update()
            sidebar_panel.focus_panel()
            sidebar_panel.load_wall(wall, segment_index=s_idx)
        act_wall.triggered.connect(lambda: QTimer.singleShot(0, _open_wall_side))

        is_locked = bool(getattr(wall, "motion_locked", False) or (hasattr(wall, "ext") and isinstance(wall.ext, dict) and wall.ext.get("motion_locked", False)))
        lock_label = tr("🔓 Destravar Posição das Paredes e Piso") if is_locked else tr("🔒 Travar Posição das Paredes e Piso")
        act_lock = menu.addAction(lock_label)
        def _toggle_lock_from_menu():
            new_state = not is_locked
            if hasattr(sidebar_panel, "btn_lock_walls_floor"):
                sidebar_panel.btn_lock_walls_floor.setChecked(new_state)
            if hasattr(sidebar_panel, "_toggle_walls_floor_lock"):
                sidebar_panel._toggle_walls_floor_lock(new_state)
        act_lock.triggered.connect(_toggle_lock_from_menu)

        # Opção de Ocultar / Reexibir Parede (vital para visão interna de câmeras)
        hide_label = f"👁️ Ocultar {wall.name}" if is_seg else f"👁️ Ocultar Parede{seg_text}"
        act_hide_wall = menu.addAction(hide_label)
        def _hide_this_wall(w=wall, s_idx=seg_index):
            if hasattr(app, "viewport") and hasattr(app.viewport, "history"):
                from core.history import HideCommand
                from .wall.selection import WallSelectionManager
                from .wall.builder import WallBuilderTool, SplitWallGroupCommand

                p = getattr(w, "ext", {}).get("trazomob_wall") if isinstance(getattr(w, "ext", None), dict) else {}
                is_s = bool(p.get("is_segmented", False))
                p_cnt = len(p.get("pontos", []))

                # Se já for seccionada, oculta diretamente o grupo da parede
                if is_s or p_cnt <= 2:
                    app.viewport.history.execute(HideCommand([w], hidden=True))
                    if hasattr(app.viewport, "scene"):
                        app.viewport.scene.selection.discard(w)
                    WallSelectionManager.get_instance().clear_selection()
                    app.viewport.update()
                    if hasattr(app.viewport, "flash_status"):
                        app.viewport.flash_status(f"👁️ {w.name} ocultada (use 'Reexibir Paredes' para mostrar novamente).")
                    return

                # Se for monólito contínuo, secciona primeiro e oculta a parede escolhida
                eff_idx = s_idx if s_idx is not None else p.get("selected_segment", 0)
                subs = WallBuilderTool.split_wall_group_into_segments(w)
                if len(subs) > 1:
                    cmd_split = SplitWallGroupCommand(w, subs)
                    app.viewport.history.execute(cmd_split)
                    target_sub = next((s for s in subs if s.ext.get("trazomob_wall", {}).get("segment_index") == int(eff_idx)), subs[0])
                    app.viewport.history.execute(HideCommand([target_sub], hidden=True))
                    if hasattr(app.viewport, "scene"):
                        app.viewport.scene.selection.discard(w)
                    WallSelectionManager.get_instance().clear_selection()
                    app.viewport.update()
                    if hasattr(app.viewport, "flash_status"):
                        app.viewport.flash_status(f"👁️ Parede #{int(eff_idx) + 1} seccionada e ocultada com sucesso!")
                    return
        act_hide_wall.triggered.connect(_hide_this_wall)

        # Se houver alguma parede, teto ou face oculta, adiciona atalho para reexibir
        has_hidden_arch = False
        if hasattr(app, "viewport") and hasattr(app.viewport, "scene"):
            for g in getattr(app.viewport.scene, "groups", []):
                ext = getattr(g, "ext", {})
                if isinstance(ext, dict) and ("trazomob_wall" in ext or "trazomob_ceiling" in ext):
                    if getattr(app.viewport.scene, "entity_hidden", lambda e: False)(g):
                        has_hidden_arch = True
                        break
                    if hasattr(g, "mesh") and hasattr(g.mesh, "faces"):
                        if any(f.attrs.get("hidden") for f in g.mesh.faces):
                            has_hidden_arch = True
                            break
        if has_hidden_arch:
            act_unhide_arch = menu.addAction(tr("👁️ Reexibir Todas as Paredes e Tetos"))
            def _unhide_all_arch():
                arch_to_show = []
                for g in getattr(app.viewport.scene, "groups", []):
                    ext = getattr(g, "ext", {})
                    if isinstance(ext, dict) and ("trazomob_wall" in ext or "trazomob_ceiling" in ext):
                        if getattr(app.viewport.scene, "entity_hidden", lambda e: False)(g):
                            arch_to_show.append(g)
                        if hasattr(g, "mesh") and hasattr(g.mesh, "faces"):
                            for f in g.mesh.faces:
                                if f.attrs.get("hidden"):
                                    arch_to_show.append(f)
                        if hasattr(g, "mesh") and hasattr(g.mesh, "edges"):
                            for e in g.mesh.edges:
                                if getattr(e, "hidden", False):
                                    arch_to_show.append(e)
                if arch_to_show:
                    from core.history import HideCommand
                    app.viewport.history.execute(HideCommand(arch_to_show, hidden=False))
                    app.viewport.update()
                    if hasattr(app.viewport, "flash_status"):
                        app.viewport.flash_status("👁️ Paredes e tetos reexibidos.")
            act_unhide_arch.triggered.connect(_unhide_all_arch)

        menu.addSeparator()

    mod = None
    from .domain.assembly import is_module
    for item in selection:
        if is_module(item):
            mod = item
            break
    if mod is None and hasattr(app, "viewport") and hasattr(app.viewport, "scene"):
        for g in getattr(app.viewport.scene, "groups", []):
            if is_module(g):
                children = getattr(g, "children", [])
                if any(child in selection for child in children):
                    mod = g
                    break
    if mod is not None:
        action_side = menu.addAction(f"📐 Editar na Barra Lateral: {mod.name}")
        def _open_side():
            if hasattr(app, "viewport") and hasattr(app.viewport, "scene"):
                app.viewport.scene.selection = {mod}
                app.viewport.update()
            sidebar_panel.focus_panel()
            sidebar_panel.load_module(mod)
        action_side.triggered.connect(lambda: QTimer.singleShot(0, _open_side))

        action = menu.addAction(f"Editar Módulo (Janela): {mod.name}…")
        def _open():
            app.viewport.scene.selection = {mod}
            app.viewport.update()
            tool_cls().on_activate(app.viewport)
        action.triggered.connect(lambda: QTimer.singleShot(0, _open))

        act_tg = menu.addAction(tr("🚪 Abrir / Fechar Portas e Gavetas"))
        act_tg.triggered.connect(lambda: CabinetInteract.toggle_all(mod, app.viewport.scene, app.viewport))

    # ── Menu de Rotação 90° (qualquer objeto selecionado) ───────────────────
    vp_ctx = getattr(app, "viewport", None)
    scene_ctx = getattr(vp_ctx, "scene", None) if vp_ctx is not None else None
    from .interaction.align_tools import resolve_rotatable_groups, rotate_groups_with_command

    rot_targets = resolve_rotatable_groups(scene_ctx, selection)
    if rot_targets and vp_ctx is not None:
        rot_menu = menu.addMenu(tr("🔄 Girar 90° (TrazoMob)"))
        rot_cw = rot_menu.addAction(tr("↻ Girar 90° Horário"))
        rot_cw.triggered.connect(lambda: rotate_groups_with_command(rot_targets, 90.0, vp_ctx))
        rot_ccw = rot_menu.addAction(tr("↺ Girar 90° Anti-horário"))
        rot_ccw.triggered.connect(lambda: rotate_groups_with_command(rot_targets, -90.0, vp_ctx))
        rot_180 = rot_menu.addAction(tr("🔁 Girar 180°"))
        rot_180.triggered.connect(lambda: rotate_groups_with_command(rot_targets, 180.0, vp_ctx))

    # ── Menu de Alinhamento e Centralização (TrazoMob) ──────────────────────
    sel_groups = [it for it in selection if isinstance(it, Group)]
    if len(sel_groups) >= 2:
        from .interaction.align_tools import center_objects
        # O último clicado ou selecionado serve de alvo, o primeiro é a base/referência
        alvo = sel_groups[-1]
        base = sel_groups[0]
        menu.addSeparator()
        align_menu = menu.addMenu(f"🎯 Centralizar / Alinhar ({alvo.name} ➔ {base.name})")

        act_c_xy = align_menu.addAction(tr("✛ Centralizar no Centro (Largura e Profundidade - XY)"))
        act_c_xy.triggered.connect(lambda: center_objects(alvo, base, axes="xy", viewport=getattr(app, "viewport", None)))

        act_c_x = align_menu.addAction(tr("↔ Centralizar na Largura (Eixo X)"))
        act_c_x.triggered.connect(lambda: center_objects(alvo, base, axes="x", viewport=getattr(app, "viewport", None)))

        act_c_y = align_menu.addAction(tr("↕ Centralizar na Profundidade (Eixo Y)"))
        act_c_y.triggered.connect(lambda: center_objects(alvo, base, axes="y", viewport=getattr(app, "viewport", None)))

        act_c_z = align_menu.addAction(tr("⬍ Centralizar na Altura (Eixo Z)"))
        act_c_z.triggered.connect(lambda: center_objects(alvo, base, axes="z", viewport=getattr(app, "viewport", None)))

        act_c_all = align_menu.addAction(tr("🎯 Centralizar em Todos os Eixos (XYZ)"))
        act_c_all.triggered.connect(lambda: center_objects(alvo, base, axes="xyz", viewport=getattr(app, "viewport", None)))

