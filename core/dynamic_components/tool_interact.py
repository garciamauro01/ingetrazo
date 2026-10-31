# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
"""Ferramenta de interação com Componentes Dinâmicos (compatível com hierarquia e subcomponentes)."""
from __future__ import annotations

import re
from PySide6.QtCore import QTimer
from tools.base import Tool, ToolContext
from .model import evaluate_dc, get_dc_data
from .engine import SafeExpressionEvaluator


class DCAnimationController:
    """Controlador singleton para animações fluidas a 50 FPS."""

    def __init__(self):
        self._timer = QTimer()
        self._timer.setInterval(20)  # ~50 FPS
        self._timer.timeout.connect(self._on_tick)
        self._active_animations: list[dict] = []
        self._viewport = None

    def animate(self, group, var_name: str, start_val: float, end_val: float, duration_ms: int = 350, viewport=None):
        self._viewport = viewport
        anim = {
            "group": group,
            "var_name": var_name,
            "start": float(start_val),
            "end": float(end_val),
            "progress": 0.0,
            "step": 20.0 / max(duration_ms, 20),
        }
        self._active_animations.append(anim)
        if not self._timer.isActive():
            self._timer.start()

    def _on_tick(self):
        still_running = []
        for anim in self._active_animations:
            anim["progress"] += anim["step"]
            t = min(anim["progress"], 1.0)
            # Interpolação suave EaseInOut Quad
            ease = 2 * t * t if t < 0.5 else 1 - math_pow(-2 * t + 2, 2) / 2
            curr = anim["start"] + (anim["end"] - anim["start"]) * ease

            group = anim["group"]
            data = get_dc_data(group)
            if data and "attributes" in data and anim["var_name"] in data["attributes"]:
                data["attributes"][anim["var_name"]]["value"] = curr
                evaluate_dc(group)

            if t < 1.0:
                still_running.append(anim)
            else:
                if data and "attributes" in data and anim["var_name"] in data["attributes"]:
                    data["attributes"][anim["var_name"]]["value"] = anim["end"]
                    evaluate_dc(group)

        self._active_animations = still_running
        if not self._active_animations:
            self._timer.stop()

        if self._viewport and hasattr(self._viewport, "update"):
            self._viewport.update()


def math_pow(base: float, exp: float) -> float:
    return base ** exp


_anim_ctrl = DCAnimationController()


def _resolve_target(group, var_spec: str):
    """Resolve referências com 'SubComponente!Variavel' ou 'Variavel'."""
    chars_to_strip = "\"' "
    clean = var_spec.strip(chars_to_strip)
    if "!" in clean:
        parts = clean.split("!", 1)
        target_name = parts[0].strip().lower()
        var_name = parts[1].strip()

        # 1. Procura na raiz da árvore inteira ou no pai mais alto
        root = group
        while getattr(root, "owner", None) is not None:
            root = root.owner

        all_nodes = []
        def _collect(node):
            all_nodes.append(node)
            for child in getattr(node, "children", []) or []:
                _collect(child)

        _collect(root)

        # Passo A: Correspondência exata com o atributo Name do DC ou nome do grupo
        for node in all_nodes:
            n_name = getattr(node, "name", "").lower()
            data = get_dc_data(node)
            dc_name = str((data or {}).get("attributes", {}).get("Name", {}).get("value", "")).lower()
            if target_name == dc_name or target_name == n_name:
                return node, var_name

        # Passo B: Correspondência por prefixo / palavra completa
        for node in all_nodes:
            n_name = getattr(node, "name", "").lower()
            data = get_dc_data(node)
            dc_name = str((data or {}).get("attributes", {}).get("Name", {}).get("value", "")).lower()
            if dc_name.startswith(target_name) or n_name.startswith(target_name):
                return node, var_name

        # Passo C: Substring fallback
        for node in all_nodes:
            n_name = getattr(node, "name", "").lower()
            data = get_dc_data(node)
            dc_name = str((data or {}).get("attributes", {}).get("Name", {}).get("value", "")).lower()
            if target_name in dc_name or target_name in n_name:
                return node, var_name

        # Fallback: se o próprio grupo clicado contiver o atributo alvo
        data = get_dc_data(group)
        if data and "attributes" in data:
            for ak in data["attributes"].keys():
                if ak.lower() == var_name.lower():
                    return group, ak

    return group, clean


class InteractTool(Tool):
    """Ferramenta da 'Mãozinha' para interagir com Componentes Dinâmicos."""

    name = "Interact"
    description = "Click on a dynamic component to trigger actions (onClick)."
    shortcut = None
    uses_snap = False

    def on_activate(self, viewport) -> None:
        if viewport and hasattr(viewport, "flash_status"):
            viewport.flash_status("Interact tool active: click on a dynamic component.", 3000)

    def on_deactivate(self, viewport) -> None:
        pass

    def on_click(self, ctx: ToolContext) -> None:
        viewport = ctx.viewport
        screen_x = int(ctx.screen.x())
        screen_y = int(ctx.screen.y())

        # 1. Tenta pegar o grupo direto
        group = getattr(viewport, "pick_group", lambda x, y: None)(screen_x, screen_y)

        # 2. Se não encontrou grupo direto, tenta achar pelo face_placement
        if not group and hasattr(viewport, "pick_face_placement"):
            face, place = viewport.pick_face_placement(screen_x, screen_y)
            group = place

        # 3. Fallback: buscar pelo pick_face_any
        if not group and hasattr(viewport, "pick_face_any"):
            face, place = viewport.pick_face_any(screen_x, screen_y)
            group = place

        if not group:
            if hasattr(viewport, "flash_status"):
                viewport.flash_status("No object under cursor.", 2000)
            return

        # Busca onClick subindo na hierarquia até achar ou desce procurando em filhos
        curr = group
        target_group = None
        on_click_cmd = ""
        while curr:
            data = get_dc_data(curr)
            if data and data.get("onClick"):
                target_group = curr
                on_click_cmd = str(data.get("onClick", "")).strip()
                break
            curr = getattr(curr, "owner", None)

        # Se não achou subindo, pesquisa nos filhos diretos se algum tem onClick
        if not target_group:
            for child in getattr(group, "children", []) or []:
                data = get_dc_data(child)
                if data and data.get("onClick"):
                    target_group = child
                    on_click_cmd = str(data.get("onClick", "")).strip()
                    break

        if not target_group or not on_click_cmd:
            data = get_dc_data(group)
            if not data:
                if hasattr(viewport, "flash_status"):
                    viewport.flash_status(f"'{getattr(group, 'name', 'Object')}' is not a dynamic component.", 2000)
                return
            if hasattr(viewport, "flash_status"):
                viewport.flash_status("Dynamic component has no onClick behavior configured.", 2000)
            return

        self._execute_action(target_group, on_click_cmd, viewport)

    def _execute_action(self, group, cmd: str, viewport) -> None:
        cmd = cmd.strip()
        cmd = re.sub(r"['\"]+\)$", ")", cmd)

        # ANIMATE / ANIMATESLOW / ANIMATEFAST
        m_anim = re.match(r"^ANIMATE(SLOW|FAST)?\(\s*(.+?)\s*\)$", cmd, re.IGNORECASE)
        if m_anim:
            speed = m_anim.group(1) or ""
            args_str = m_anim.group(2)
            parts = [p.strip().strip("'\"") for p in args_str.split(",")]
            if len(parts) >= 2:
                raw_var = parts[0]
                target_grp, var_name = _resolve_target(group, raw_var)
                t_data = get_dc_data(target_grp)
                t_attrs = t_data.get("attributes", {}) if t_data else {}

                # Normaliza busca case-insensitive no atributo alvo
                real_attr_name = var_name
                for ak in t_attrs.keys():
                    if ak.lower() == var_name.lower():
                        real_attr_name = ak
                        break

                val_choices = parts[1:]
                duration = 600 if "SLOW" in speed.upper() else (200 if "FAST" in speed.upper() else 350)

                curr_val = float(t_attrs.get(real_attr_name, {}).get("value", 0.0))
                try:
                    num_choices = [float(p) for p in val_choices]
                    closest_idx = 0
                    min_diff = float("inf")
                    for i, v in enumerate(num_choices):
                        diff = abs(v - curr_val)
                        if diff < min_diff:
                            min_diff = diff
                            closest_idx = i
                    next_val = num_choices[(closest_idx + 1) % len(num_choices)]
                except Exception:
                    next_val = float(val_choices[0])

                _anim_ctrl.animate(target_grp, real_attr_name, curr_val, next_val, duration_ms=duration, viewport=viewport)
                if hasattr(viewport, "flash_status"):
                    viewport.flash_status(f"{target_grp.name} -> {real_attr_name} = {next_val}", 2000)
                return

        # SET("var", expr)
        m_set = re.match(r"^SET\(\s*(.+?)\s*\)$", cmd, re.IGNORECASE)
        if m_set:
            parts = [p.strip().strip("'\"") for p in m_set.group(1).split(",", 1)]
            if len(parts) == 2:
                raw_var, expr = parts[0], parts[1]
                target_grp, var_name = _resolve_target(group, raw_var)
                t_data = get_dc_data(target_grp)
                t_attrs = t_data.get("attributes", {}) if t_data else {}
                ctx = {k: v.get("value") for k, v in t_attrs.items()}
                new_val = SafeExpressionEvaluator.evaluate(expr, ctx)
                if var_name in t_attrs and new_val is not None:
                    t_attrs[var_name]["value"] = new_val
                    evaluate_dc(target_grp)
                    if hasattr(viewport, "flash_status"):
                        viewport.flash_status(f"{var_name} = {new_val}", 2000)
                    if hasattr(viewport, "update"):
                        viewport.update()
                    return

        if hasattr(viewport, "flash_status"):
            viewport.flash_status(f"Command executed: {cmd}", 2000)
