# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Operações canônicas de manipulação de módulos de marcenaria do TrazoMob.

Concentra e unifica regras de:
1. Duplicação contígua inteligente (esquerda/direita) com respeito rigoroso à rotação Z (rot_z).
2. Exclusão segura de módulos da cena com confirmação e suporte total a Undo/Redo.
3. Atualização em lote (Batch Update) de módulos com preservação de alinhamento e histórico único.
"""
from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QVector3D
from PySide6.QtWidgets import QMessageBox, QWidget

from core.group import Group
from core.history import SnapshotImport
from ..domain.assembly import is_module, iter_module_groups
from ..builders.cabinet import CabinetBuilder
from ..interaction.magnetic_drag import get_module_bounds
from ..domain.module_geometry import get_module_carcass_bounds, preserve_module_back_alignment
from ..domain.schema import module_params


def duplicate_contiguous_module(
    module: Group,
    direction: str = "right",
    gap_mm: float = 0.0,
    viewport: Any = None,
    scene: Any = None,
) -> Optional[Group]:
    """Duplica um módulo posicionando-o encostado contiguamente à esquerda ou direita.

    Leva em conta a largura total (largura_mm), o espaçamento livre (gap_mm)
    e a rotação espacial (rot_z) no plano horizontal XY para preservar o alinhamento
    perfeito com a parede onde o módulo estiver apoiado.
    """
    if module is None or not is_module(module):
        return None

    sc = scene or getattr(viewport, "scene", None)
    if sc is None:
        return None

    params = dict(module_params(module))
    orig_off = params.get("offset", (0.0, 0.0, 0.0))
    if not isinstance(orig_off, (list, tuple)) or len(orig_off) < 3:
        orig_off = (0.0, 0.0, 0.0)

    # Medidas em metros
    L_m = float(params.get("largura", 800.0)) / 1000.0
    gap_m = float(gap_mm) / 1000.0
    step_m = L_m + gap_m

    rot_z = float(params.get("rot_z", 0.0)) % 360.0
    rad = math.radians(rot_z)

    # Vetor unitário apontando para a direita local (+X local rotacionado em Z)
    u_dir = QVector3D(math.cos(rad), math.sin(rad), 0.0).normalized()
    mult = -1.0 if str(direction).strip().lower() == "left" else 1.0

    offset = (
        float(orig_off[0]) + mult * float(u_dir.x()) * step_m,
        float(orig_off[1]) + mult * float(u_dir.y()) * step_m,
        float(orig_off[2]),
    )

    new_module = CabinetBuilder.build_module_group(params, offset=offset)

    def apply_dup(target_scene):
        target_layer = getattr(new_module, "layer", None)
        if target_layer and hasattr(target_scene, "layer") and hasattr(target_scene, "layers"):
            if target_scene.layer(target_layer) is None:
                from core.layers import Layer
                target_scene.layers.append(Layer(target_layer))
        target_scene.groups.append(new_module)
        target_scene.selection = {new_module}

    if viewport and hasattr(viewport, "history") and viewport.history:
        viewport.history.execute(SnapshotImport(apply_dup))
        viewport.notify_scene_changed()
        viewport.update()
    else:
        apply_dup(sc)
        if viewport:
            viewport.update()

    return new_module


def delete_module(
    module: Group,
    viewport: Any = None,
    scene: Any = None,
    prompt_confirm: bool = True,
    parent_widget: Optional[QWidget] = None,
) -> bool:
    """Exclui com segurança um módulo da cena 3D com suporte a Undo/Redo."""
    if module is None:
        return False

    sc = scene or getattr(viewport, "scene", None)
    if sc is None:
        return False

    if prompt_confirm:
        reply = QMessageBox.question(
            parent_widget,
            "Excluir Módulo",
            f"Deseja excluir o módulo '{module.name}' da cena 3D?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return False

    def apply_del(target_scene):
        if module in target_scene.groups:
            target_scene.groups.remove(module)
        if hasattr(target_scene, "selection") and module in target_scene.selection:
            target_scene.selection.remove(module)

    if viewport and hasattr(viewport, "history") and viewport.history:
        viewport.history.execute(SnapshotImport(apply_del))
        viewport.notify_scene_changed()
        viewport.update()
    else:
        apply_del(sc)
        if viewport:
            viewport.update()

    return True


def batch_update_scene_modules(
    viewport: Any,
    filter_fn: Callable[[Group, Dict[str, Any]], bool],
    patch_fn: Callable[[Group, Dict[str, Any]], Optional[Dict[str, Any]]],
) -> int:
    """Executa a atualização de parâmetros e reconstrução em lote de múltiplos módulos na cena.

    :param viewport: Viewport do aplicativo.
    :param filter_fn: Função (modulo, params) -> bool indicando se deve ser alterado.
    :param patch_fn: Função (modulo, params) -> new_params_dict retornando o dicionário atualizado.
    :return: Quantidade de módulos reconstruídos e substituídos na transação.
    """
    if viewport is None:
        return 0
    sc = getattr(viewport, "scene", None)
    if sc is None:
        return 0

    all_modules = list(iter_module_groups(getattr(sc, "groups", [])))
    if not all_modules:
        return 0

    replacements: List[Tuple[Group, Group]] = []
    for mod in all_modules:
        old_params = module_params(mod)
        if not filter_fn(mod, old_params):
            continue

        new_params = patch_fn(mod, dict(old_params))
        if not new_params:
            continue

        offset = old_params.get("offset", (0.0, 0.0, 0.0))
        if not isinstance(offset, (list, tuple)) or len(offset) < 3:
            offset = (0.0, 0.0, 0.0)
        offset = tuple(float(v) for v in offset)

        rot_z_eff = float(new_params.get("rot_z", 0.0) or 0.0) % 360.0

        new_mod_group = CabinetBuilder.build_module_group(new_params, offset=offset)
        preserve_module_back_alignment(mod, new_mod_group, rot_z_eff)

        b_final = get_module_carcass_bounds(new_mod_group) or get_module_bounds(new_mod_group)
        if b_final and "trazomob_module" in new_mod_group.ext:
            mod_ext = new_mod_group.ext["trazomob_module"]
            cx_final = (b_final[0] + b_final[1]) * 0.5
            cy_final = (b_final[2] + b_final[3]) * 0.5
            cz_final = (b_final[4] + b_final[5]) * 0.5
            unrot_span = mod_ext.get("_unrot_carcass_span")
            if isinstance(unrot_span, (list, tuple)) and len(unrot_span) == 6:
                mod_ext["offset"] = (
                    cx_final - float(unrot_span[0]),
                    cy_final - float(unrot_span[1]),
                    cz_final - float(unrot_span[2]),
                )

        replacements.append((mod, new_mod_group))

    if not replacements:
        return 0

    def apply_batch_transaction(target_scene):
        for old_m, new_m in replacements:
            target_layer = getattr(new_m, "layer", None)
            if target_layer and hasattr(target_scene, "layer") and hasattr(target_scene, "layers"):
                if target_scene.layer(target_layer) is None:
                    from core.layers import Layer
                    target_scene.layers.append(Layer(target_layer))
            if old_m in target_scene.groups:
                target_scene.groups.remove(old_m)
            target_scene.groups.append(new_m)
        if replacements:
            target_scene.selection = {replacements[0][1]}

    if hasattr(viewport, "history") and viewport.history:
        viewport.history.execute(SnapshotImport(apply_batch_transaction))
    else:
        apply_batch_transaction(sc)

    # Invalida só os chunks dos módulos substituídos, preservando o resto da cena.
    from ..builders.cabinet_transform import invalidate_replaced_modules_caches
    invalidate_replaced_modules_caches(replacements, viewport)

    viewport.notify_scene_changed()
    viewport.update()
    return len(replacements)
