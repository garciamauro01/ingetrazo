# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Diálogo de exportação do Manual de Montagem (HTML).

Reutiliza o padrão de ``ui.proposal_dialog``: coleta opções do usuário, gera o
documento HTML em ``production.assembly_manual`` e salva em arquivo.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

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

from ..production.assembly_manual import save_assembly_manual_html

DEFAULT_PROJECT_NAME = "Projeto de Interiores TrazoMob"


class AssemblyManualDialog(QDialog):
    """Coleta os dados do projeto e salva o Manual de Montagem em HTML."""

    def __init__(self, parent=None, parts: Optional[List[Dict[str, Any]]] = None,
                 project_name: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Manual de Montagem — TrazoMob")
        self.setMinimumWidth(420)
        self.parts = parts or []

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.ed_projeto = QLineEdit(project_name or DEFAULT_PROJECT_NAME)
        form.addRow("Nome do Projeto *:", self.ed_projeto)
        layout.addLayout(form)

        info = QLabel(
            f"<b>Peças:</b> {sum(p.get('quantidade', 1) for p in self.parts)} un. &nbsp;|&nbsp; "
            f"<b>Tipos de peça:</b> {len(self.parts)}"
        )
        info.setStyleSheet("font-size: 12px; color: #1E293B; margin-top: 8px;")
        layout.addWidget(info)

        layout.addWidget(QLabel(
            "O manual agrupa as peças por módulo, lista as ferragens de cada "
            "módulo, medidas de corte/final e as usinagens (furos, rasgos, etc.)"
        ))
        layout.addWidget(QLabel(""))

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("💾 Salvar Manual (HTML)")
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
                self, "Manual de Montagem",
                "Nenhuma peça disponível para gerar o manual de montagem."
            )
            return

        nome_arquivo = "".join(c if c.isalnum() or c in " _-" else "_" for c in nome)
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Manual de Montagem",
            f"Manual_Montagem_{nome_arquivo}.html",
            "HTML (*.html)",
        )
        if not filepath:
            return

        ok = save_assembly_manual_html(self.parts, filepath, project_name=nome)
        if ok:
            QMessageBox.information(
                self, "Manual de Montagem",
                f"✅ Manual de montagem salvo com sucesso em:\n{filepath}"
            )
            self.accept()
        else:
            QMessageBox.critical(
                self, "Manual de Montagem",
                f"Não foi possível salvar o arquivo em:\n{filepath}"
            )


def export_assembly_manual(
    parent,
    parts: List[Dict[str, Any]],
    project_name: str = DEFAULT_PROJECT_NAME,
) -> Optional[str]:
    """Abre o diálogo e salva o Manual de Montagem. Retorna o caminho ou None."""
    if not parts:
        QMessageBox.information(
            parent, "Manual de Montagem",
            "Nenhuma peça disponível para gerar o manual de montagem."
        )
        return None

    dlg = AssemblyManualDialog(parent, parts=parts, project_name=project_name)
    if dlg.exec() != QDialog.Accepted:
        return None

    # O caminho é escolhido dentro do diálogo; devolvemos None (o diálogo já
    # informa o usuário). Mantido para simetria com export_proposal.
    return None
