# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, Mauro Garcia and IngeTrazo contributors.
"""Sistema de internacionalização (i18n) do plugin TrazoMob.

Usa o Português (pt-BR) como idioma-fonte (as chaves passadas para `tr` são
as próprias strings originais em Português), de forma que qualquer string não
traduzida faz fallback automático e seguro para o original, sem risco de quebrar
a interface ou os testes.

Os dicionários de tradução ficam em `assets/i18n/<lang>.json` (ex.: `es.json`, `en.json`).
Sincroniza automaticamente com `core.i18n.current_language()` do IngeTrazo.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

_I18N_DIR = Path(__file__).resolve().parent.parent / "assets" / "i18n"
_CATALOG_CACHE: dict[str, dict[str, str]] = {}

logger = logging.getLogger("trazomob.i18n")


def get_lang() -> str:
    """Retorna o código de idioma ativo no IngeTrazo (ex.: 'pt-BR', 'es', 'en')."""
    try:
        from core.i18n import current_language
        lang = current_language()
        return lang if lang else "pt-BR"
    except Exception:
        return "pt-BR"


def _get_catalog(lang: str) -> dict[str, str]:
    """Carrega e faz cache do dicionário JSON para o idioma informado."""
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
    """Fonte (pt-BR) de um texto já traduzido pelo catálogo do TrazoMob.

    O host usa ``action_key`` para lembrar atalhos; quando o texto de uma ação
    muda com o idioma, a chave muda e o atalho some. Reverter para a fonte antes
    de gerar um ``objectName`` dá uma chave estável em qualquer idioma.
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
    """Limpa o cache de traduções carregadas."""
    _CATALOG_CACHE.clear()


def tr(text: str, /, **kwargs) -> str:
    """Traduz `text` para o idioma atual do IngeTrazo e interpola `kwargs` se fornecidos."""
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

