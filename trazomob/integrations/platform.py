# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Camada de acesso do TrazoMob às APIs do IngeTrazo.

O TrazoMob é first-party: o host chama as funções de
:mod:`integrations.host_calls` diretamente nos pontos de edição. Aqui ficam
apenas as consultas e ações que o TrazoMob ainda precisa fazer *sobre* o host
(janela ativa, estilos, diálogos, docks).

Regras (verificadas por ``tests/test_platform_contract.py``):

1. Nenhum outro módulo do TrazoMob acessa atributos privados do host
   (``main_window._*``, ``viewport._*``) por conta própria: chama este módulo.
2. Toda capacidade é detectada antes de usada e degrada com elegância: um
   host que mudou não derruba o TrazoMob.

Se o IngeTrazo mudar, este arquivo é o único que precisa mudar.
"""
from __future__ import annotations

import importlib
import logging
from typing import Any

logger = logging.getLogger("trazomob.platform")


# ---------------------------------------------------------------------------
# Versão e capacidades do host
# ---------------------------------------------------------------------------

def host_version() -> str | None:
    """Versão do IngeTrazo em execução, ou ``None`` fora do host."""
    try:
        from core.version import __version__
        return str(__version__)
    except Exception:
        return None


def api_version() -> int | None:
    """``API_VERSION`` da API de extensões, ou ``None`` fora do host."""
    try:
        from views.extension_api import API_VERSION
        return int(API_VERSION)
    except Exception:
        return None


def window_of(window: Any = None, viewport: Any = None) -> Any:
    """A janela principal, dada a janela, o viewport ou o ``app``."""
    if window is None:
        window = getattr(viewport, "window", None)
        window = window() if callable(window) else window
    return window


def active_viewport(window: Any = None, viewport: Any = None, app: Any = None) -> Any:
    """Retorna o viewport do documento atualmente ativo na janela principal."""
    win = window_of(window, viewport)
    if win is None and app is not None:
        win = getattr(app, "window", None)
    if win is not None and hasattr(win, "documents"):
        win_vp = getattr(win, "viewport", None)
        if win_vp is not None and not callable(win_vp):
            return win_vp
    if app is not None:
        app_vp = getattr(app, "viewport", None)
        if app_vp is not None and not callable(app_vp):
            return app_vp
    if win is not None and window is not None:
        win_vp = getattr(win, "viewport", None)
        if win_vp is not None and not callable(win_vp) and win_vp is not win:
            return win_vp
    return viewport


def all_viewports(window: Any = None, viewport: Any = None, app: Any = None) -> list[Any]:
    """Retorna todos os viewports de documentos abertos conhecidos pelo host."""
    win = window_of(window, viewport)
    if win is None and app is not None:
        win = getattr(app, "window", None)
    if win is not None:
        if hasattr(win, "all_viewports"):
            try:
                vps = [vp for vp in (win.all_viewports() or []) if vp is not None]
                if vps:
                    return vps
            except Exception:
                pass
        docs = getattr(win, "documents", None)
        if docs:
            vps = []
            for doc in docs:
                for attr in ("front_view", "viewport"):
                    vp = getattr(doc, attr, None)
                    if vp is not None and vp not in vps:
                        vps.append(vp)
            if vps:
                return vps
    vp = active_viewport(window=window, viewport=viewport, app=app)
    return [vp] if vp is not None else []


def capabilities(window: Any = None, viewport: Any = None) -> dict[str, bool]:
    """O que este host sabe fazer. Consulte em vez de usar ``hasattr`` solto."""
    win = window_of(window, viewport)
    if win is None:
        return {}
    return {
        "display_style": callable(getattr(win, "_apply_display_style", None)),
        "style_field": callable(getattr(win, "_set_style_field", None)),
        "style_menu": callable(getattr(win, "_sync_style_menu", None)),
        "xray": callable(getattr(win, "_toggle_xray", None)),
        "plugin_tool": callable(getattr(win, "_activate_plugin_tool", None)),
        "insert_component": callable(getattr(win, "_on_insert_component", None)),
        "insert_person": callable(getattr(win, "_on_insert_person_2d", None)),
        "insert_user_component": callable(
            getattr(win, "insert_user_component", None)),
        "import_user_component": callable(
            getattr(win, "import_user_component", None)),
        "open_user_library": callable(
            getattr(win, "_on_open_user_library", None)),
        "extension_dock": callable(getattr(win, "_register_extension_dock", None)),
    }


def supports(name: str, window: Any = None, viewport: Any = None) -> bool:
    return bool(capabilities(window, viewport).get(name, False))


def _scene(viewport: Any):
    return getattr(viewport, "scene", None)


# ---------------------------------------------------------------------------
# Estilos de visualização
# ---------------------------------------------------------------------------

def apply_display_style(window: Any, viewport: Any, preset: Any) -> bool:
    """Aplica um estilo de face. Usa a API do host quando existe; senão,
    escreve direto na cena (que é API pública do documento)."""
    viewport = active_viewport(window, viewport)
    win = window_of(window, viewport)
    apply_fn = getattr(win, "_apply_display_style", None)
    if callable(apply_fn):
        apply_fn(preset)
        return True
    scene = _scene(viewport)
    if scene is None or not hasattr(scene, "display_style"):
        logger.debug("host sem suporte a estilo de visualização")
        return False
    scene.display_style = preset.copy()
    sync_style_menu(win)
    update = getattr(viewport, "update", None)
    if callable(update):
        update()
    return True


def set_style_field(window: Any, viewport: Any, name: str, value: bool) -> bool:
    """Liga/desliga um campo booleano do estilo (edges, profiles, ...)."""
    viewport = active_viewport(window, viewport)
    win = window_of(window, viewport)
    setter = getattr(win, "_set_style_field", None)
    if callable(setter):
        setter(name, value)
        return True
    scene = _scene(viewport)
    style = getattr(scene, "display_style", None)
    if style is None or not hasattr(style, name):
        return False
    setattr(style, name, bool(value))
    update = getattr(viewport, "update", None)
    if callable(update):
        update()
    return True


def sync_style_menu(window: Any) -> bool:
    syncer = getattr(window_of(window), "_sync_style_menu", None)
    if callable(syncer):
        syncer()
        return True
    return False


def toggle_xray(window: Any, viewport: Any = None) -> bool:
    viewport = active_viewport(window, viewport)
    win = window_of(window, viewport)
    toggler = getattr(win, "_toggle_xray", None)
    if callable(toggler):
        toggler()
        return True
    return False


def legacy_style_toolbar(window: Any):
    """A barra ``igz_tb_style`` do host, se existir (o TrazoMob a esconde
    porque traz o próprio dropdown de estilos)."""
    win = window_of(window)
    if win is None or not callable(getattr(win, "findChildren", None)):
        return None
    from PySide6.QtWidgets import QToolBar
    for child in win.findChildren(QToolBar):
        if child.objectName() == "igz_tb_style":
            return child
    return None


# ---------------------------------------------------------------------------
# Ferramentas e componentes do host
# ---------------------------------------------------------------------------

def activate_plugin_tool(window: Any, viewport: Any, key: str,
                         fallback_factory: Any = None) -> bool:
    """Aciona uma ferramenta registrada (uma vez), com o caminho do host
    como preferido e o caminho direto do viewport como reserva.

    ``fallback_factory`` é chamado só quando o host não tem a ferramenta
    registrada, para não construir um ``Tool`` à toa.
    """
    viewport = active_viewport(window, viewport)
    win = window_of(window, viewport)
    activate = getattr(win, "_activate_plugin_tool", None)
    tools = getattr(win, "_tools", None)
    if callable(activate) and isinstance(tools, dict) and key in tools:
        activate(key)
        return True
    setter = getattr(viewport, "set_active_tool", None)
    if fallback_factory is not None and callable(setter):
        setter(fallback_factory())
        return True
    logger.debug("não foi possível ativar a ferramenta %r", key)
    return False


def insert_component(window: Any, key: str, name: str | None = None) -> bool:
    """Insere um componente nativo do IngeTrazo, pronto para posicionar."""
    fn = getattr(window_of(window), "_on_insert_component", None)
    if not callable(fn):
        logger.debug("host sem _on_insert_component: componente %r ignorado", key)
        return False
    fn(key, name)
    return True


def insert_person_2d(window: Any, image: str, height: float = 1.75,
                     name: str | None = None) -> bool:
    """Insere a figura humana em escala (billboard face-me)."""
    fn = getattr(window_of(window), "_on_insert_person_2d", None)
    if not callable(fn):
        logger.debug("host sem _on_insert_person_2d: figura %r ignorada", image)
        return False
    fn(image, height, name)
    return True


def insert_user_component(window: Any, entry: dict) -> bool:
    """Insere um componente da biblioteca do próprio usuário, pronto para
    posicionar. ``entry`` é uma ficha de :mod:`core.user_library`."""
    fn = getattr(window_of(window), "insert_user_component", None)
    if not callable(fn):
        logger.debug("host sem insert_user_component: componente %r ignorado",
                     (entry or {}).get("id"))
        return False
    fn(entry)
    return True


def import_user_component(window: Any, path: str | None = None) -> bool:
    """Abre a ficha de importação de um componente e, se confirmada, o
    posiciona. Um host sem o recurso devolve ``False`` sem quebrar."""
    fn = getattr(window_of(window), "import_user_component", None)
    if not callable(fn):
        logger.debug("host sem import_user_component")
        return False
    fn(path)
    return True


def open_user_library(window: Any, brand: str | None = None) -> bool:
    """Abre o gerenciador da biblioteca do usuário, opcionalmente já
    filtrado por marca (é o que o botão de cada marca no ribbon pede)."""
    fn = getattr(window_of(window), "_on_open_user_library", None)
    if not callable(fn):
        logger.debug("host sem _on_open_user_library")
        return False
    fn(brand)
    return True


def register_extension_dock(window: Any, dock: Any) -> bool:
    """Registra um dock na janela, pelo caminho público do host."""
    win = window_of(window)
    fn = getattr(win, "_register_extension_dock", None)
    if callable(fn):
        fn(dock)
        return True
    adder = getattr(win, "addDockWidget", None)
    if callable(adder):
        from PySide6.QtCore import Qt
        adder(Qt.RightDockWidgetArea, dock)
        return True
    return False


def import_module(name: str):
    """``importlib.import_module`` com log — para o host nunca derrubar o
    plugin por causa de um módulo que mudou de lugar."""
    try:
        return importlib.import_module(name)
    except Exception:
        logger.exception("módulo do host indisponível: %s", name)
        return None


__all__ = [
    "host_version", "api_version", "window_of", "active_viewport", "all_viewports",
    "capabilities", "supports",
    "apply_display_style", "set_style_field", "sync_style_menu", "toggle_xray",
    "legacy_style_toolbar", "activate_plugin_tool", "insert_component",
    "insert_person_2d", "insert_user_component",
    "import_user_component", "open_user_library", "register_extension_dock",
    "import_module",
]
