# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
"""Gerador de relatórios para Componentes Dinâmicos (Generate Report)."""
from __future__ import annotations

import csv
import io
from typing import Any
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from .model import get_dc_data


def collect_dc_report_rows(root_group) -> list[dict[str, Any]]:
    """Percorre recursivamente a árvore do componente e extrai a lista de peças e quantidades."""
    rows: list[dict[str, Any]] = []

    def _walk(g, path=""):
        name = getattr(g, "name", "Peça")
        curr_path = f"{path} > {name}" if path else name
        dc_data = get_dc_data(g)
        if dc_data:
            attrs = dc_data.get("attributes", {})
            row = {
                "Nome": name,
                "Caminho": curr_path,
                "Comprimento (LenX)": str(attrs.get("LenX", {}).get("value", "")),
                "Profundidade (LenY)": str(attrs.get("LenY", {}).get("value", "")),
                "Altura (LenZ)": str(attrs.get("LenZ", {}).get("value", "")),
                "Material": str(attrs.get("Material", {}).get("value", "")),
                "Cópias": str(attrs.get("Copies", {}).get("value", "0")),
            }
            # Adiciona atributos customizados extras
            for k, v in attrs.items():
                if k not in row and k not in ("X", "Y", "Z", "RotX", "RotY", "RotZ", "Hidden", "Copy", "ScaleTool"):
                    row[k] = str(v.get("value", ""))
            rows.append(row)

        for child in getattr(g, "children", []) or []:
            _walk(child, curr_path)

    _walk(root_group)
    return rows


class DCReportDialog(QDialog):
    """Janela 'Gerar Relatório' (Generate Report do SketchUp)."""

    def __init__(self, root_group, parent=None):
        super().__init__(parent)
        self.root_group = root_group
        self.setWindowTitle("Gerar Relatório do Componente Dinâmico (Generate Report)")
        self.resize(750, 450)
        self.rows = collect_dc_report_rows(root_group)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Lista de Peças e Quantidades Paramétricas</b>"))

        self.table = QTableWidget()
        if self.rows:
            headers = list(self.rows[0].keys())
            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)
            self.table.setRowCount(len(self.rows))
            for r_idx, r in enumerate(self.rows):
                for c_idx, h in enumerate(headers):
                    self.table.setItem(r_idx, c_idx, QTableWidgetItem(r.get(h, "")))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        btn_bar = QHBoxLayout()
        btn_csv = QPushButton("Exportar CSV...")
        btn_csv.clicked.connect(self._export_csv)
        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(self.accept)

        btn_bar.addWidget(btn_csv)
        btn_bar.addStretch()
        btn_bar.addWidget(btn_close)
        layout.addLayout(btn_bar)

    def _export_csv(self):
        if not self.rows:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Relatório CSV", "relatorio_componente.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            headers = list(self.rows[0].keys())
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(self.rows)
            QMessageBox.information(self, "Sucesso", f"Relatório exportado com sucesso para:\n{path}")
        except Exception as err:
            QMessageBox.critical(self, "Erro", f"Falha ao exportar CSV: {err}")

