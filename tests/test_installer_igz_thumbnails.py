# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez and IngeTrazo contributors.
"""The installer registers the .igz preview handler for Windows Explorer.

Inno Setup does not run on every machine, so this reads the script as text,
like tests/test_installer_skp_thumbnails.py does for the .skp fix.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ISS = ROOT / "installer" / "ingetrazo.iss"
SOURCE = ROOT / "installer" / "IngeTrazoThumbnailProvider.cs"
BUILD_SCRIPT = ROOT / "installer" / "build-thumbnail-provider.ps1"
HANDLER = "e357fccd-a995-4576-b01f-234630154e96"
CLSID = "a4c84e91-2e97-4d99-8fe5-e8b2b7d60d2b"


def _section(name: str) -> str:
    script = ISS.read_text(encoding="utf-8-sig")
    match = re.search(rf"^\[{name}\]\n(.*?)(?=^\[\w+\]|\Z)", script,
                      re.MULTILINE | re.DOTALL)
    assert match, f"no [{name}] section"
    return match.group(1)


def test_dll_is_shipped_and_rebuilt_from_source():
    files = _section("Files").replace("\\\n", " ")
    assert 'Source: "IngeTrazoThumbnailProvider.dll"' in files
    assert SOURCE.is_file() and BUILD_SCRIPT.is_file()
    # The registry names 1.0.0.0: the source must produce that version.
    assert 'AssemblyVersion("1.0.0.0")' in SOURCE.read_text(encoding="utf-8")


def test_handler_is_registered_on_igz():
    entries = _section("Registry").replace("\\\n", " ").splitlines()
    entry = next(line for line in entries
                 if r'Subkey: "Software\Classes\.igz\ShellEx' in line)
    assert HANDLER in entry.lower()
    assert CLSID in entry.lower()
    assert "uninsdeletekey" in entry


def test_com_server_has_every_value_explorer_needs():
    registry = _section("Registry").replace("\\\n", " ")
    assert ('Software\\Classes\\CLSID\\{{' + CLSID.upper() + '}') in registry
    for expected in ('ValueData: "mscoree.dll"',
                     'ValueName: "ThreadingModel"; ValueData: "Both"',
                     'ValueName: "Class"; ValueData: '
                     '"IngeTrazo.Shell.IngeTrazoThumbnailProvider"',
                     'ValueName: "Assembly"; ValueData: '
                     '"IngeTrazoThumbnailProvider, Version=1.0.0.0, '
                     'Culture=neutral, PublicKeyToken=null"',
                     'ValueName: "RuntimeVersion"; ValueData: "v4.0.30319"',
                     'ValueName: "CodeBase"; ValueData: '
                     '"file:///{app}\\IngeTrazoThumbnailProvider.dll"'):
        assert expected in registry


def test_our_handler_does_not_take_over_skp_previews():
    # Issue #804: IngeTrazo.skp borrows the previous program's handler.
    code = _section("Code")
    assert CLSID not in code.lower()
    assert len([line for line in code.splitlines()
                if "RegWriteStringValue" in line]) == 1
