# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Exportação/importação da biblioteca do usuário como um ``.zip`` portátil.

O pacote contém ``library.json``, ``models/<id>/`` e ``thumbs/<id>.png``.
Nada é baixado ou publicado: é o usuário quem escolhe o arquivo e, na
importação, se ele mescla ou substitui a biblioteca atual.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QInputDialog, QMessageBox

from core import user_library
from core.i18n import tr
from views.filedialogs import file_dialogs

_ZIP_FILTER = tr("Zip files (*.zip)")


def export_library(parent, *, after: Callable[[], None] | None = None) -> None:
    path, _selected = file_dialogs.getSaveFileName(
        parent, tr("Export user library"), "biblioteca-usuario.zip",
        _ZIP_FILTER)
    if not path:
        return
    try:
        stats = user_library.export_bundle(path)
    except Exception as exc:  # noqa: BLE001 - diálogo nunca derruba o app
        QMessageBox.critical(parent, tr("Export user library"), str(exc))
        return
    QMessageBox.information(
        parent, tr("Export user library"),
        tr("{entries} components and {files} files exported to {path}",
           entries=stats["entries"], files=stats["files"],
           path=stats["path"]))
    if after is not None:
        after()


def import_library(parent, *, after: Callable[[], None] | None = None) -> None:
    path, _selected = file_dialogs.getOpenFileName(
        parent, tr("Import user library"), "", _ZIP_FILTER)
    if not path:
        return

    modes = [tr("Merge (keep current library)"),
             tr("Replace current library")]
    choice, accepted = QInputDialog.getItem(
        parent, tr("Import user library"),
        tr("How should the components be imported?"), modes, 0, False)
    if not accepted:
        return
    replace = choice == modes[1]
    if replace:
        answer = QMessageBox.question(
            parent, tr("Replace user library"),
            tr("The current library will be replaced. Continue?"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return

    try:
        stats = user_library.import_bundle(
            path, mode="replace" if replace else "merge")
    except Exception as exc:  # noqa: BLE001
        QMessageBox.critical(parent, tr("Import user library"), str(exc))
        return

    if replace:
        message = tr("{entries} components imported; the previous library "
                     "was replaced.", entries=stats["entries"])
    else:
        message = tr("{added} components imported, {skipped} already "
                     "present and kept unchanged.",
                     added=stats["added"], skipped=stats["skipped"])
    QMessageBox.information(parent, tr("Import user library"), message)
    if after is not None:
        after()
