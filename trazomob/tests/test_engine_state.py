# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes do interruptor global do motor do TrazoMob."""

from __future__ import annotations

from trazomob.domain.engine_state import (
    DEFAULT_ENABLED,
    SETTING_KEY,
    is_engine_enabled,
    read_engine_preference,
    reset_engine_cache,
    set_engine_enabled,
)


def _clear_setting() -> None:
    from PySide6.QtCore import QSettings

    st = QSettings()
    st.remove(SETTING_KEY)
    st.sync()


def test_motor_vem_desligado_por_padrao(qapp):
    _clear_setting()
    reset_engine_cache()

    assert DEFAULT_ENABLED is False
    assert read_engine_preference() is False
    assert is_engine_enabled() is False


def test_preferencia_do_motor_e_persistida(qapp):
    _clear_setting()
    reset_engine_cache()

    assert set_engine_enabled(True) is True
    assert is_engine_enabled() is True

    # Simula uma nova sessão: descarta o cache e le novamente do QSettings.
    reset_engine_cache()
    assert is_engine_enabled() is True

    set_engine_enabled(False)
    reset_engine_cache()
    assert is_engine_enabled() is False

    _clear_setting()
    reset_engine_cache()
