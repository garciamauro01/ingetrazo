# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Assembly Manual export dialog (HTML).

Reuses the ``ui.proposal_dialog`` pattern: collects user options, generates the
HTML document in ``production.assembly_manual``, and saves it to a file.
"""
from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from ..domain.i18n import tr
from ..production.assembly_manual import save_assembly_manual_html

DEFAULT_PROJECT_NAME = "Projeto de Interiores TrazoMob"


class AssemblyManualDialog(QDialog):
    """Collects project data and saves the Assembly Manual as HTML."""

    def __init__(self, parent=None, parts: list[dict[str, Any]] | None = None,
                 project_name: str = ""):
        super().__init__(parent)
        self.setWindowTitle(tr("Manual de Montagem — TrazoMob"))
        self.setMinimumWidth(420)
        self.parts = parts or []

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.ed_projeto = QLineEdit(project_name or tr(DEFAULT_PROJECT_NAME))
        form.addRow(tr("Nome do Projeto *:"), self.ed_projeto)
        layout.addLayout(form)

        info = QLabel(
            f"<b>{tr('Peças:')}</b> {sum(p.get('quantidade', 1) for p in self.parts)} {tr('un.')} &nbsp;|&nbsp; "
            f"<b>{tr('Tipos de peça:')}</b> {len(self.parts)}"
        )
        info.setStyleSheet("font-size: 12px; color: #1E293B; margin-top: 8px;")
        layout.addWidget(info)

        layout.addWidget(QLabel(tr(
            "O manual agrupa as peças por módulo, lista as ferragens de cada "
            "módulo, medidas de corte/final e as usinagens (furos, rasgos, etc.)"
        )))
        layout.addWidget(QLabel(""))

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText(tr("💾 Salvar Manual (HTML)"))
        buttons.button(QDialogButtonBox.Save).setStyleSheet(
            "background-color: #0284C7; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;"
        )
        buttons.accepted.connect(self._salvar)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _salvar(self) -> None:
        nome = self.ed_projeto.text().strip() or DEFAULT_PROJECT_NAME
        if not self.parts:
            QMessageBox.information(
                self, tr("Manual de Montagem"),
                tr("Nenhuma peça disponível para gerar o manual de montagem.")
            )
            return

        nome_arquivo = "".join(c if c.isalnum() or c in " _-" else "_" for c in nome)
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            tr("Salvar Manual de Montagem"),
            f"Manual_Montagem_{nome_arquivo}.html",
            "HTML (*.html)",
        )
        if not filepath:
            return

        ok = save_assembly_manual_html(self.parts, filepath, project_name=nome)
        if ok:
            QMessageBox.information(
                self, tr("Manual de Montagem"),
                tr("✅ Manual de montagem salvo com sucesso em:\n{filepath}").format(filepath=filepath)
            )
            self.accept()
        else:
            QMessageBox.critical(
                self, tr("Manual de Montagem"),
                tr("Não foi possível salvar o arquivo em:\n{filepath}").format(filepath=filepath)
            )


def export_assembly_manual(
    parent,
    parts: list[dict[str, Any]],
    project_name: str = DEFAULT_PROJECT_NAME,
) -> str | None:
    """Abre o diálogo e salva o Manual de Montagem. Retorna o caminho ou None."""
    if not parts:
        QMessageBox.information(
            parent, tr("Manual de Montagem"),
            tr("Nenhuma peça disponível para gerar o manual de montagem.")
        )
        return None

    dlg = AssemblyManualDialog(parent, parts=parts, project_name=project_name)
    if dlg.exec() != QDialog.Accepted:
        return None

    # O caminho é escolhido dentro do diálogo; devolvemos None (o diálogo já
    # informa o usuário). Mantido para simetria com export_proposal.
    return None
