# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Diálogo e fluxo reutilizável de exportação de proposta comercial (HTML/PDF).

Antes deste módulo, o fluxo de proposta estava duplicado e inconsistente: a aba
de plano de corte definia um diálogo de cliente aninhado no método e o painel de
orçamento exportava sem coletar nenhum dado (usava ``client_name="Cliente"``).
Centralizar aqui garante que os dois caminhos coletem os mesmos dados e gerem a
proposta do mesmo jeito.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)

from ..production.report import generate_proposal_html, generate_proposal_pdf

DEFAULT_PROJECT_NAME = "Projeto de Interiores TrazoMob"


class ProposalExportDialog(QDialog):
    """Coleta os dados do cliente usados na proposta comercial."""

    def __init__(self, parent=None, client_name: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Dados do Cliente para Proposta")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.ed_nome = QLineEdit(client_name or "Cliente")
        self.ed_cpf = QLineEdit()
        self.ed_end = QLineEdit()
        self.ed_cid = QLineEdit()
        self.ed_tel = QLineEdit()
        self.ed_email = QLineEdit()
        form.addRow("Nome *:", self.ed_nome)
        form.addRow("CPF/CNPJ:", self.ed_cpf)
        form.addRow("Endereço:", self.ed_end)
        form.addRow("Cidade/UF:", self.ed_cid)
        form.addRow("Telefone:", self.ed_tel)
        form.addRow("Email:", self.ed_email)
        layout.addLayout(form)

        layout.addWidget(QLabel("<b>Observações / Condições Especiais:</b>"))
        self.ed_obs = QTextEdit()
        self.ed_obs.setPlaceholderText(
            "Ex: Prazo de entrega, condições de pagamento, itens incluídos/excluídos..."
        )
        self.ed_obs.setMaximumHeight(100)
        layout.addWidget(self.ed_obs)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self) -> Dict[str, str]:
        return {
            "nome": self.ed_nome.text().strip(),
            "cpf_cnpj": self.ed_cpf.text().strip(),
            "endereco": self.ed_end.text().strip(),
            "cidade": self.ed_cid.text().strip(),
            "telefone": self.ed_tel.text().strip(),
            "email": self.ed_email.text().strip(),
            "observacoes": self.ed_obs.toPlainText().strip(),
        }


def export_proposal(
    parent,
    parts: List[Dict[str, Any]],
    project_name: str = DEFAULT_PROJECT_NAME,
    client_name: str = "",
) -> Optional[str]:
    """Coleta os dados do cliente, salva a proposta e devolve o caminho gerado.

    Retorna ``None`` quando o usuário cancela, quando não há peças ou quando o
    nome do cliente não é informado. Em caso de PDF indisponível, cai de volta
    para HTML de forma transparente.
    """
    if not parts:
        QMessageBox.information(
            parent, "Proposta", "Nenhuma peça disponível para gerar a proposta."
        )
        return None

    dlg = ProposalExportDialog(parent, client_name=client_name)
    if dlg.exec() != QDialog.Accepted:
        return None

    client_data = dlg.get_data()
    if not client_data["nome"]:
        QMessageBox.warning(parent, "Atenção", "Nome do cliente é obrigatório.")
        return None

    nome_arquivo = client_data["nome"].replace(" ", "_") or "Cliente"
    filepath, _ = QFileDialog.getSaveFileName(
        parent,
        "Salvar Proposta Comercial",
        f"Proposta_{nome_arquivo}_TrazoMob.html",
        "HTML (*.html);;PDF (*.pdf)",
    )
    if not filepath:
        return None

    observacoes = client_data["observacoes"]
    if filepath.lower().endswith(".pdf"):
        success = generate_proposal_pdf(
            parts=parts,
            filepath=filepath,
            project_name=project_name,
            client_name=client_data["nome"],
            client_data=client_data,
            observacoes=observacoes,
        )
        if not success:
            QMessageBox.warning(
                parent,
                "PDF",
                "Não foi possível gerar PDF (weasyprint não instalado).\nSalvando como HTML...",
            )
            filepath = filepath[:-4] + ".html"
            generate_proposal_html(
                parts=parts,
                project_name=project_name,
                client_name=client_data["nome"],
                client_data=client_data,
                observacoes=observacoes,
                filepath=filepath,
            )
    else:
        generate_proposal_html(
            parts=parts,
            project_name=project_name,
            client_name=client_data["nome"],
            client_data=client_data,
            observacoes=observacoes,
            filepath=filepath,
        )

    QMessageBox.information(
        parent, "Proposta Gerada", f"✅ Proposta comercial salva com sucesso em:\n{filepath}"
    )
    return filepath
