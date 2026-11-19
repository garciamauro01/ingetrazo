# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Seção de ferragens do diálogo de módulos.

Permite visualizar e editar a lista de ferragens (dobradiças, trilhos,
corrediças, puxadores, fixações etc.) de um módulo. As ferragens são
inferidas automaticamente a partir dos parâmetros (nº de portas, gavetas,
portas de correr, tipo de puxador, profundidade etc.) e podem ser ajustadas
manualmente item a item. O resultado é gravado em
``params["hardware"]`` e, ao construir o módulo, armazenado em
``group.ext["trazomob_hardware"]`` para ser lido por cutlist, orçamento e
relatórios sem depender de heurística por nome da peça.
"""

from __future__ import annotations

from typing import Any, Dict, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ..domain.hardware import (
    HARDWARE_CATALOG,
    HardwareItem,
    deserialize_hardware,
    infer_module_hardware,
    serialize_hardware,
)


class ModuleDialogHardwareMixin:
    """Mix-in que adiciona a seção de ferragens ao diálogo de módulos."""

    # ------------------------------------------------------------------ build

    def _build_hardware_section(self, form_layout):
        """Card de ferragens: tabela com quantidade editável por item."""
        self.frame_hardware = QFrame()
        self.frame_hardware.setFrameShape(QFrame.StyledPanel)
        self.frame_hardware.setStyleSheet(
            "QFrame { background-color: #FAFCFF; border: 1px solid #E2E8F0; "
            "border-radius: 8px; padding: 8px; }"
        )
        v = QVBoxLayout(self.frame_hardware)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)

        lbl = QLabel("<b>🔧 Ferragens do Módulo</b>")
        lbl.setStyleSheet("font-size: 12px; color: #0F172A;")
        v.addWidget(lbl)

        self.lbl_hardware_sub = QLabel(
            "Inferida automaticamente a partir de portas, gavetas e puxadores. "
            "Edite as quantidades conforme necessário."
        )
        self.lbl_hardware_sub.setStyleSheet("font-size: 10px; color: #64748B;")
        self.lbl_hardware_sub.setWordWrap(True)
        v.addWidget(self.lbl_hardware_sub)

        self.tbl_hardware = QTableWidget(0, 5)
        self.tbl_hardware.setHorizontalHeaderLabels(
            ["Item", "Tipo", "Quantidade", "Preço Unit.", "Total"]
        )
        self.tbl_hardware.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        for col in (1, 2, 3, 4):
            self.tbl_hardware.horizontalHeader().setSectionResizeMode(
                col, QHeaderView.ResizeToContents
            )
        self.tbl_hardware.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_hardware.setAlternatingRowColors(True)
        self.tbl_hardware.setMaximumHeight(220)
        v.addWidget(self.tbl_hardware)

        self.chk_hardware_3d = QCheckBox("Mostrar ferragens no 3D")
        self.chk_hardware_3d.setChecked(True)
        self.chk_hardware_3d.setToolTip(
            "Cria uma representação 3D esquemática das ferragens (dobradiças, "
            "corrediças, trilhos e pés). Não é contabilizada na lista de peças."
        )
        v.addWidget(self.chk_hardware_3d)

        self.lbl_hardware_total = QLabel("Total: R$ 0,00")
        self.lbl_hardware_total.setStyleSheet(
            "font-weight: bold; color: #0F172A; font-size: 11px;"
        )
        v.addWidget(self.lbl_hardware_total)

        form_layout.addRow(self.frame_hardware)

        # Estado: lista de HardwareItem (editável pelo usuário)
        self._hardware_items: List[HardwareItem] = []

    # ------------------------------------------------------------------ fill

    def _fill_hardware_table(self, params: Dict[str, Any]) -> None:
        """Preenche a tabela a partir de ``params["hardware"]`` ou inferindo."""
        self.tbl_hardware.setRowCount(0)
        self._hardware_items = []

        explicit = params.get("hardware")
        if isinstance(explicit, list) and explicit:
            itens = deserialize_hardware(explicit)
        else:
            itens = infer_module_hardware(params or {})

        if not itens:
            self.lbl_hardware_sub.setText(
                "Nenhuma ferragem inferida para este tipo de módulo."
            )
            self.lbl_hardware_total.setText("Total: R$ 0,00")
            return

        self.lbl_hardware_sub.setText(
            "Inferida automaticamente a partir de portas, gavetas e puxadores. "
            "Edite as quantidades conforme necessário."
        )

        for it in itens:
            it = HardwareItem(
                key=it.key,
                tipo=it.tipo,
                nome=it.nome,
                quantidade=max(0, int(it.quantidade or 0)),
                preco_unitario=float(it.preco_unitario or 0.0),
                posicao=it.posicao,
                visivel_3d=bool(it.visivel_3d),
            )
            self._hardware_items.append(it)
            self._add_hardware_row(it)

        self._recalc_hardware_total()
        self.tbl_hardware.itemChanged.disconnect() if False else None

    def _add_hardware_row(self, it: HardwareItem) -> None:
        row = self.tbl_hardware.rowCount()
        self.tbl_hardware.insertRow(row)

        cat = HARDWARE_CATALOG.get(it.key, {})

        item_nome = QTableWidgetItem(it.nome or it.key)
        item_nome.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        self.tbl_hardware.setItem(row, 0, item_nome)

        item_tipo = QTableWidgetItem(
            {
                "dobradica": "Dobradiça",
                "trilho": "Trilho",
                "corredica": "Corrediça",
                "puxador": "Puxador",
                "fixacao": "Fixação",
                "outro": "Outro",
            }.get(it.tipo, it.tipo)
        )
        item_tipo.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        self.tbl_hardware.setItem(row, 1, item_tipo)

        spin = QSpinBox()
        spin.setRange(0, 1000)
        spin.setValue(it.quantidade)
        spin.setAlignment(Qt.AlignCenter)
        spin.valueChanged.connect(
            lambda value, idx=row: self._on_hardware_qty_changed(idx, value)
        )
        self.tbl_hardware.setCellWidget(row, 2, spin)

        preco = float(cat.get("preco", it.preco_unitario or 0.0))
        item_preco = QTableWidgetItem(f"R$ {preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        item_preco.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        item_preco.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.tbl_hardware.setItem(row, 3, item_preco)

        item_total = QTableWidgetItem(f"R$ {preco * it.quantidade:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        item_total.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        item_total.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.tbl_hardware.setItem(row, 4, item_total)

    def _on_hardware_qty_changed(self, row: int, value: int) -> None:
        if 0 <= row < len(self._hardware_items):
            self._hardware_items[row].quantidade = max(0, int(value))
            self._update_hardware_row_total(row)
            self._recalc_hardware_total()
            # Marca que o usuário editou explicitamente: grava params["hardware"]
            self._mark_hardware_edited()

    def _update_hardware_row_total(self, row: int) -> None:
        it = self._hardware_items[row]
        cat = HARDWARE_CATALOG.get(it.key, {})
        preco = float(cat.get("preco", it.preco_unitario or 0.0))
        self.tbl_hardware.item(row, 4).setText(
            f"R$ {preco * it.quantidade:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )

    def _recalc_hardware_total(self) -> None:
        total = sum(
            float(HARDWARE_CATALOG.get(it.key, {}).get("preco", it.preco_unitario or 0.0))
            * int(it.quantidade or 0)
            for it in self._hardware_items
        )
        self.lbl_hardware_total.setText(f"Total: R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    def _mark_hardware_edited(self) -> None:
        """Grava a lista editada em params para ser usada pelo construtor."""
        params = getattr(self, "_current_params", None)
        if params is None:
            return
        params["hardware"] = serialize_hardware(self._hardware_items)

    # ------------------------------------------------------------------ restore/save

    def _restore_hardware_from_module(self, params: Dict[str, Any]) -> None:
        """Carrega as ferragens do módulo editado na tabela."""
        if not hasattr(self, "tbl_hardware"):
            return
        hw_ext = None
        editing = getattr(self, "_editing_module", None)
        if editing is not None and hasattr(editing, "ext") and isinstance(editing.ext, dict):
            hw_ext = editing.ext.get("trazomob_hardware")
        if isinstance(hw_ext, list) and hw_ext:
            params["hardware"] = list(hw_ext)
        if hasattr(self, "chk_hardware_3d"):
            self.chk_hardware_3d.setChecked(
                bool(params.get("hardware_3d_visible", True))
            )
        self._fill_hardware_table(params)

    def _current_hardware_params(self) -> List[Dict[str, Any]]:
        """Retorna a lista de ferragens atual (editada) para gravação."""
        return serialize_hardware(self._hardware_items)
