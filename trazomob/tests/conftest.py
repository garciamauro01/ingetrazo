# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Fixtures compartilhadas pela suíte TrazoMob (agora first-party).

O fork não depende de pytest-qt: ``qapp`` é fornecido aqui. O armazenamento de
preferências também é isolado — sem ``QApplication`` com nome de organização,
``QSettings()`` não tem arquivo e descarta escritas silenciosamente, o que
fazia ``test_engine_state`` passar só quando a suíte do host rodava antes.
"""
from __future__ import annotations

import tempfile

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

_settings_dir = tempfile.mkdtemp(prefix="trazomob-tests-settings-")
QSettings.setDefaultFormat(QSettings.IniFormat)
for _scope in (QSettings.UserScope, QSettings.SystemScope):
    QSettings.setPath(QSettings.IniFormat, _scope, _settings_dir)


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])
