# SPDX-License-Identifier: GPL-3.0-or-later
"""The freeze watchdog must write beside the other black-box logs, on every OS."""
from __future__ import annotations


def test_freeze_log_path_uses_user_log_dir(monkeypatch, tmp_path):
    import core.paths
    import main

    monkeypatch.setattr(core.paths, "user_log_dir", lambda: tmp_path)

    assert main._freeze_log_path() == tmp_path / "ingetrazo-freeze.log"
