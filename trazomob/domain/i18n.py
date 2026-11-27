# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, Mauro Garcia and IngeTrazo contributors.
"""Internationalization (i18n) system for the TrazoMob plugin.

Uses Portuguese (pt-BR) as the source language (the keys passed to `tr` are
the original Portuguese strings themselves), so any untranslated string
safely falls back to the original without risking UI or test breakage.

Translation dictionaries live in `assets/i18n/<lang>.json` (e.g., `es.json`, `en.json`).
Automatically syncs with IngeTrazo's `core.i18n.current_language()`.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

_I18N_DIR = Path(__file__).resolve().parent.parent / "assets" / "i18n"
_CATALOG_CACHE: dict[str, dict[str, str]] = {}

logger = logging.getLogger("trazomob.i18n")


def get_lang() -> str:
    """Return the active language code in IngeTrazo (e.g., 'pt-BR', 'es', 'en')."""
    try:
        from core.i18n import current_language
        lang = current_language()
        return lang if lang else "pt-BR"
    except Exception:
        return "pt-BR"


def _get_catalog(lang: str) -> dict[str, str]:
    """Load and cache the JSON dictionary for the given language."""
    if not lang or lang in ("pt-BR", "pt", "pt_BR"):
        return {}
    if lang not in _CATALOG_CACHE:
        base_lang = lang.replace("_", "-").split("-")[0].lower()
        loaded: dict[str, str] = {}
        for candidate in (lang, base_lang):
            path = _I18N_DIR / f"{candidate}.json"
            if path.is_file():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        loaded = {str(k): str(v) for k, v in data.items()}
                        break
                except Exception:
                    logger.debug("Falha ao ler catálogo de tradução %s", path, exc_info=True)
        _CATALOG_CACHE[lang] = loaded
    return _CATALOG_CACHE[lang]


def source_text(text: str) -> str:
    """Source (pt-BR) of a text already translated by the TrazoMob catalog.

    The host uses ``action_key`` to remember shortcuts; when an action's text
    changes with the language, the key changes and the shortcut disappears.
    Reverting to the source text before generating an ``objectName`` yields a
    stable key in any language.
    """
    if not text:
        return text
    for catalog in (_get_catalog(get_lang()),
                    _get_catalog("en"), _get_catalog("es")):
        for source, translated in catalog.items():
            if translated == text:
                return source
    return text


def clear_i18n_cache() -> None:
    """Clear the loaded translations cache."""
    _CATALOG_CACHE.clear()


def tr(text: str, /, **kwargs) -> str:
    """Translate `text` to the current IngeTrazo language and interpolate `kwargs` if provided."""
    if not text:
        return text
    lang = get_lang()
    catalog = _get_catalog(lang)
    out = catalog.get(text, text)
    if kwargs:
        try:
            out = out.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            try:
                out = text.format(**kwargs)
            except Exception:
                logger.debug("Falha ao interpolar tradução '%s'", text, exc_info=True)
    return out

