# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Interruptor global do motor do TrazoMob.

O motor controla todo o comportamento do plugin: ganchos de runtime, arraste
magnetico, snap, barra lateral, ribbon de modulos, menu de contexto e
ferramentas interativas. Ele vem DESLIGADO por padrao; a escolha do usuario e
persistida em ``QSettings`` e lida uma unica vez por sessao.

O botao correspondente fica na barra de ferramentas do TrazoMob.
"""

from __future__ import annotations

from typing import Any

#: Chave persistida em QSettings para a preferencia do motor.
SETTING_KEY = "trazomob/engine_enabled"

#: Valor quando o usuario nunca escolheu: desligado.
DEFAULT_ENABLED = False

_cached: bool | None = None


def _settings() -> Any:
    """Retorna o QSettings sem importar Qt no carregamento do modulo."""
    from PySide6.QtCore import QSettings

    return QSettings()


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on", "sim", "ligado")


def read_engine_preference() -> bool:
    """Le a preferencia persistida; sem Qt ou sem valor, retorna o padrao."""
    try:
        return _to_bool(_settings().value(SETTING_KEY, DEFAULT_ENABLED))
    except Exception:  # noqa: BLE001 - sem aplicacao Qt configurada ainda
        return DEFAULT_ENABLED


def is_engine_enabled() -> bool:
    """Estado atual do motor (memoria, com leitura unica da preferencia)."""
    global _cached
    if _cached is None:
        _cached = read_engine_preference()
    return bool(_cached)


def set_engine_enabled(enabled: bool, *, persist: bool = True) -> bool:
    """Atualiza o estado em memoria e, por padrao, grava a preferencia."""
    global _cached
    value = bool(enabled)
    _cached = value
    if persist:
        try:
            settings = _settings()
            settings.setValue(SETTING_KEY, "1" if value else "0")
            settings.sync()          # grava antes de outra leitura na sessão
        except Exception:  # noqa: BLE001 - persistencia best-effort
            pass
    return value


def reset_engine_cache() -> None:
    """Descarta o cache em memoria (util em testes)."""
    global _cached
    _cached = None
