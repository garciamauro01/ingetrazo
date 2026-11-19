# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations
import math
import os
from typing import Any
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox, QMenu, QApplication,
    QGroupBox, QComboBox
)
from core.group import Group, iter_placements

from ..production.export import (
    export_trazomob_csv,
    export_trazomob_hellomob,
    export_trazomob_json,
    format_trazomob_text,
)
from ..production.cut_plan_viewer import CutPlanViewerDialog
from ..ui.icons import make_cut_plan_icon
from ..production.parts import extract_parts, group_similar_parts
from ..domain.ambiente import iter_ambientes, iter_pavimentos

class CutListTabMixin:
    def _build_cutlist_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        top_bar = QHBoxLayout()
        self._filter_sel_cb = QCheckBox("Somente selecionados")
        self._filter_sel_cb.toggled.connect(self._reload_parts)
        top_bar.addWidget(self._filter_sel_cb)

        self._group_cb = QCheckBox("Agrupar peças idênticas")
        self._group_cb.setChecked(True)
        self._group_cb.toggled.connect(self._reload_parts)
        top_bar.addWidget(self._group_cb)

        top_bar.addSpacing(10)
        lbl_amb = QLabel("Ambiente:")
        lbl_amb.setStyleSheet("font-weight: bold; font-size: 11px;")
        top_bar.addWidget(lbl_amb)

        self._cb_ambiente = QComboBox()
        self._cb_ambiente.setStyleSheet("font-size: 11px; padding: 2px 6px;")
        self._cb_ambiente.currentIndexChanged.connect(self._reload_parts)
        top_bar.addWidget(self._cb_ambiente)

        btn_refresh = QPushButton("🔄 Atualizar Lista")
        btn_refresh.clicked.connect(self._reload_parts)
        top_bar.addWidget(btn_refresh)

        top_bar.addStretch()

        self.lbl_stats = QLabel("Total: 0 peças | 0.00 m²")
        self.lbl_stats.setStyleSheet("font-weight: bold; color: #2e7d32; font-size: 13px;")
        top_bar.addWidget(self.lbl_stats)

        layout.addLayout(top_bar)

        self.table = QTableWidget()
        headers = [
            "Qtd", "Comp. Final (mm)", "Larg. Final (mm)", "Comp. Corte (mm)", "Larg. Corte (mm)", "Esp. Chapa",
            "Descrição / Nome", "Material (Chapa)",
            "Esp. Fita", "Fita C1", "Fita C2", "Fita L1", "Fita L2",
            "Ignorar Veio", "Usinagens / Furações"
        ]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(14, QHeaderView.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        # Card de Resumo de Materiais & Estimativa de Chapas
        self.summary_box = QGroupBox("📊 Resumo de Materiais & Estimativa de Chapas (2750 x 1850 mm)")
        self.summary_box.setStyleSheet(
            "QGroupBox { font-size: 11px; font-weight: bold; margin-top: 4px; padding-top: 10px; }"
        )
        summary_layout = QHBoxLayout(self.summary_box)
        summary_layout.setContentsMargins(12, 6, 12, 6)
        summary_layout.setSpacing(18)

        self.lbl_sum_pecas = QLabel("📦 0 peças")
        self.lbl_sum_pecas.setStyleSheet("font-weight: bold; font-size: 12px; color: #0284c7;")
        summary_layout.addWidget(self.lbl_sum_pecas)

        self.lbl_sum_chapas = QLabel("🪵 Chapas: Nenhuma")
        self.lbl_sum_chapas.setStyleSheet("font-weight: 500; font-size: 11px; color: #1e293b;")
        summary_layout.addWidget(self.lbl_sum_chapas, stretch=1)

        self.lbl_sum_fita = QLabel("📏 Fita de Borda: 0.0 m")
        self.lbl_sum_fita.setStyleSheet("font-weight: bold; font-size: 12px; color: #dc2626;")
        summary_layout.addWidget(self.lbl_sum_fita)

        layout.addWidget(self.summary_box)

        # Barra 1: Fitamento em lote
        quick_bar = QHBoxLayout()
        quick_bar.setSpacing(6)
        lbl_quick = QLabel("Fitamento:")
        lbl_quick.setStyleSheet("font-weight: bold; font-size: 11px;")
        quick_bar.addWidget(lbl_quick)

        btn_fita_4 = QPushButton("4 Lados")
        btn_fita_4.clicked.connect(lambda: self._apply_quick_tape(True, True, True, True))
        quick_bar.addWidget(btn_fita_4)

        btn_fita_2c = QPushButton("2 Comp.")
        btn_fita_2c.clicked.connect(lambda: self._apply_quick_tape(True, True, False, False))
        quick_bar.addWidget(btn_fita_2c)

        btn_fita_1c = QPushButton("1 Comp.")
        btn_fita_1c.clicked.connect(lambda: self._apply_quick_tape(True, False, False, False))
        quick_bar.addWidget(btn_fita_1c)

        btn_fita_none = QPushButton("Limpar")
        btn_fita_none.clicked.connect(lambda: self._apply_quick_tape(False, False, False, False))
        quick_bar.addWidget(btn_fita_none)

        quick_bar.addSpacing(10)
        lbl_esp_fita = QLabel("Espessura Fita:")
        lbl_esp_fita.setStyleSheet("font-weight: bold; font-size: 11px;")
        quick_bar.addWidget(lbl_esp_fita)

        for esp_opt in [0.45, 1.0, 2.0]:
            btn_esp = QPushButton(f"{esp_opt:.2f} mm" if esp_opt < 1 else f"{esp_opt:.1f} mm")
            btn_esp.setToolTip(f"Aplica espessura de fita de {esp_opt}mm nas peças selecionadas")
            btn_esp.clicked.connect(lambda _, e=esp_opt: self._apply_quick_tape_thickness(e))
            quick_bar.addWidget(btn_esp)

        quick_bar.addStretch()
        layout.addLayout(quick_bar)

        # Barra 2: Ações de Plano de Corte e Exportações
        action_bar = QHBoxLayout()
        action_bar.setSpacing(6)

        self.btn_plan = QPushButton("📐 Plano de Corte 2D")
        self.btn_plan.setIcon(make_cut_plan_icon())
        self.btn_plan.setStyleSheet(
            "background-color: #0284c7; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px; font-size: 11px;"
        )
        self.btn_plan.clicked.connect(self._open_cut_plan_viewer)
        action_bar.addWidget(self.btn_plan)

        btn_csv = QPushButton("💾 CSV")
        btn_csv.clicked.connect(self._export_csv)
        action_bar.addWidget(btn_csv)

        btn_json = QPushButton("💾 JSON")
        btn_json.clicked.connect(self._export_json)
        action_bar.addWidget(btn_json)

        btn_hellomob = QPushButton("💾 Hellomob (.hellomob)")
        btn_hellomob.clicked.connect(self._export_hellomob)
        action_bar.addWidget(btn_hellomob)

        btn_labels = QPushButton("🏷️ Etiquetas de Produção")
        btn_labels.setToolTip("Gera etiquetas adesivas com código de barras, medidas finais/corte e fitas de borda")
        btn_labels.setStyleSheet("background-color: #4338CA; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px; font-size: 11px;")
        btn_labels.clicked.connect(self._open_production_labels)
        action_bar.addWidget(btn_labels)

        btn_manual = QPushButton("🛠️ Manual de Montagem")
        btn_manual.setToolTip("Gera o manual de montagem agrupado por módulo com ferragens, medidas e usinagens")
        btn_manual.setStyleSheet("background-color: #7C3AED; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px; font-size: 11px;")
        btn_manual.clicked.connect(self._open_assembly_manual)
        action_bar.addWidget(btn_manual)

        btn_report = QPushButton("📄 Relatório Executivo HTML")
        btn_report.setToolTip("Exporta um relatório executivo completo de materiais, m² e peças")
        btn_report.setStyleSheet("background-color: #0F766E; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px; font-size: 11px;")
        btn_report.clicked.connect(self._export_html_report)
        action_bar.addWidget(btn_report)

        btn_pricing_hub = QPushButton("💼 Orçamento & Preços")
        btn_pricing_hub.setToolTip("Abre o painel de orçamento com modo apresentação do cliente e retaguarda de custos protegida por PIN")
        btn_pricing_hub.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px; font-size: 11px;")
        btn_pricing_hub.clicked.connect(self._open_pricing_presentation)
        action_bar.addWidget(btn_pricing_hub)

        btn_proposal = QPushButton("📋 Proposta Comercial")
        btn_proposal.setToolTip("Gera proposta comercial com orçamento detalhado, dados do cliente, validade e assinatura")
        btn_proposal.setStyleSheet("background-color: #7C3AED; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px; font-size: 11px;")
        btn_proposal.clicked.connect(self._export_proposal)
        action_bar.addWidget(btn_proposal)

        action_bar.addStretch()

        self.btn_copy = QPushButton("📋 Copiar p/ TrazoMob")
        self.btn_copy.setStyleSheet(
            "background-color: #2e7d32; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px; font-size: 11px;"
        )
        self.btn_copy.clicked.connect(self._copy_to_trazomob)
        action_bar.addWidget(self.btn_copy)

        layout.addLayout(action_bar)

    def _update_ambiente_filter_options(self):
        if not hasattr(self, "_cb_ambiente"):
            return
        curr_data = self._cb_ambiente.currentData()
        self._cb_ambiente.blockSignals(True)
        self._cb_ambiente.clear()
        self._cb_ambiente.addItem("🏢 Todo o Projeto", None)

        ambientes = list(iter_ambientes(getattr(self.scene, "groups", [])))
        for amb in ambientes:
            nome_amb = getattr(amb, "name", "Ambiente")
            pav = ""
            ext = getattr(amb, "ext_attrs", {})
            if isinstance(ext, dict):
                pav = ext.get("trazomob_ambiente", {}).get("pavimento", "")
            label = f"📍 {nome_amb} ({pav})" if pav else f"📍 {nome_amb}"
            self._cb_ambiente.addItem(label, amb)

        idx = 0
        if curr_data is not None:
            for i in range(self._cb_ambiente.count()):
                if self._cb_ambiente.itemData(i) == curr_data:
                    idx = i
                    break
        self._cb_ambiente.setCurrentIndex(idx)
        self._cb_ambiente.blockSignals(False)

    def _reload_parts(self):
        if not hasattr(self, "_updating_amb_filter") or not self._updating_amb_filter:
            self._updating_amb_filter = True
            try:
                self._update_ambiente_filter_options()
            finally:
                self._updating_amb_filter = False

        selected_only = self._filter_sel_cb.isChecked()
        selected_amb = self._cb_ambiente.currentData() if hasattr(self, "_cb_ambiente") else None
        raw_parts = extract_parts(self.scene, selected_only=selected_only, ambiente=selected_amb)
        if self._group_cb.isChecked():
            self._parts = group_similar_parts(raw_parts)
        else:
            self._parts = raw_parts
        self._populate_table()

    def _populate_table(self):
        self.table.setRowCount(len(self._parts))
        total_pecas = 0
        total_m2 = 0.0

        for row, p in enumerate(self._parts):
            qtd = p.get("quantidade", 1)
            comp = p["comprimento"]
            larg = p["largura"]
            esp = p["espessura"]
            total_pecas += qtd
            total_m2 += (comp / 1000.0) * (larg / 1000.0) * qtd

            spin_qtd = QSpinBox()
            spin_qtd.setRange(1, 999)
            spin_qtd.setValue(qtd)
            spin_qtd.valueChanged.connect(lambda val, r=row: self._on_qtd_changed(r, val))
            self.table.setCellWidget(row, 0, spin_qtd)

            it_comp = QTableWidgetItem(f"{comp:.1f}")
            it_comp.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 1, it_comp)

            it_larg = QTableWidgetItem(f"{larg:.1f}")
            it_larg.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 2, it_larg)

            # Medidas de corte brutas (com desconto da fita)
            from ..production.parts import calculate_cut_dimensions
            fita_c1 = p.get("fita_c1", False)
            fita_c2 = p.get("fita_c2", False)
            fita_l1 = p.get("fita_l1", False)
            fita_l2 = p.get("fita_l2", False)
            esp_fita = float(p.get("espessura_fita") or 0.45)
            comp_corte, larg_corte = calculate_cut_dimensions(
                comp, larg, fita_c1, fita_c2, fita_l1, fita_l2, esp_fita
            )
            p["comprimento_corte"] = comp_corte
            p["largura_corte"] = larg_corte
            p["espessura_fita"] = esp_fita

            it_comp_corte = QTableWidgetItem(f"{comp_corte:.1f}")
            it_comp_corte.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_comp_corte.setForeground(QColor("#047857"))  # Destaque verde para medida de corte
            self.table.setItem(row, 3, it_comp_corte)

            it_larg_corte = QTableWidgetItem(f"{larg_corte:.1f}")
            it_larg_corte.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_larg_corte.setForeground(QColor("#047857"))
            self.table.setItem(row, 4, it_larg_corte)

            it_esp = QTableWidgetItem(f"{esp:.1f} mm")
            it_esp.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, it_esp)

            it_nome = QTableWidgetItem(p["nome"])
            self.table.setItem(row, 6, it_nome)

            it_mat = QTableWidgetItem(p["material"])
            self.table.setItem(row, 7, it_mat)

            # Seletor de Espessura da Fita por peça
            cb_esp_fita = QComboBox()
            cb_esp_fita.addItems(["0.45 mm", "1.00 mm", "2.00 mm"])
            if abs(esp_fita - 1.0) < 0.1:
                cb_esp_fita.setCurrentIndex(1)
            elif abs(esp_fita - 2.0) < 0.1:
                cb_esp_fita.setCurrentIndex(2)
            else:
                cb_esp_fita.setCurrentIndex(0)
            cb_esp_fita.currentIndexChanged.connect(lambda idx, r=row: self._on_esp_fita_changed(r, idx))
            self.table.setCellWidget(row, 8, cb_esp_fita)

            for col_idx, key in enumerate(["fita_c1", "fita_c2", "fita_l1", "fita_l2"], start=9):
                cb = QCheckBox()
                cb.setChecked(p.get(key, False))
                cb.toggled.connect(lambda checked, r=row, k=key: self._on_fita_toggled(r, k, checked))
                w = QWidget()
                l = QHBoxLayout(w)
                l.setContentsMargins(0, 0, 0, 0)
                l.setAlignment(Qt.AlignCenter)
                l.addWidget(cb)
                self.table.setCellWidget(row, col_idx, w)

            cb_veio = QCheckBox()
            cb_veio.setChecked(p.get("ignorar_veio", False))
            cb_veio.toggled.connect(lambda checked, r=row: self._on_veio_toggled(r, checked))
            w_veio = QWidget()
            l_veio = QHBoxLayout(w_veio)
            l_veio.setContentsMargins(0, 0, 0, 0)
            l_veio.setAlignment(Qt.AlignCenter)
            l_veio.addWidget(cb_veio)
            self.table.setCellWidget(row, 13, w_veio)

            ops = p.get("operacoes", [])
            ops_count = len(ops)
            if ops_count > 0:
                ops_txt = f"⚙️ {ops_count} op(s)"
                it_ops = QTableWidgetItem(ops_txt)
                it_ops.setToolTip("\n".join(o.get("descricao", "Usinagem") for o in ops))
                it_ops.setForeground(QColor("#0284c7"))
            else:
                it_ops = QTableWidgetItem("—")
                it_ops.setForeground(QColor("#94a3b8"))
            it_ops.setTextAlignment(Qt.AlignCenter)
            it_ops.setFlags(it_ops.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 14, it_ops)

        self._update_stats_label()

    def _on_qtd_changed(self, row: int, val: int):
        if row < len(self._parts):
            self._parts[row]["quantidade"] = val
            self._update_stats_label()

    def _on_esp_fita_changed(self, row: int, combo_idx: int):
        if row < len(self._parts):
            vals = [0.45, 1.0, 2.0]
            val = vals[combo_idx] if combo_idx < len(vals) else 0.45
            self._parts[row]["espessura_fita"] = val
            # Atualiza células de corte da linha
            p = self._parts[row]
            from ..production.parts import calculate_cut_dimensions
            comp_corte, larg_corte = calculate_cut_dimensions(
                p["comprimento"], p["largura"],
                p.get("fita_c1", False), p.get("fita_c2", False),
                p.get("fita_l1", False), p.get("fita_l2", False),
                val
            )
            p["comprimento_corte"] = comp_corte
            p["largura_corte"] = larg_corte
            it_c = self.table.item(row, 3)
            if it_c: it_c.setText(f"{comp_corte:.1f}")
            it_l = self.table.item(row, 4)
            if it_l: it_l.setText(f"{larg_corte:.1f}")
            self._update_stats_label()

    def _on_fita_toggled(self, row: int, key: str, val: bool):
        if row < len(self._parts):
            self._parts[row][key] = val
            p = self._parts[row]
            from ..production.parts import calculate_cut_dimensions
            comp_corte, larg_corte = calculate_cut_dimensions(
                p["comprimento"], p["largura"],
                p.get("fita_c1", False), p.get("fita_c2", False),
                p.get("fita_l1", False), p.get("fita_l2", False),
                p.get("espessura_fita", 0.45)
            )
            p["comprimento_corte"] = comp_corte
            p["largura_corte"] = larg_corte
            it_c = self.table.item(row, 3)
            if it_c: it_c.setText(f"{comp_corte:.1f}")
            it_l = self.table.item(row, 4)
            if it_l: it_l.setText(f"{larg_corte:.1f}")
            self._update_stats_label()

    def _on_veio_toggled(self, row: int, val: bool):
        if row < len(self._parts):
            self._parts[row]["ignorar_veio"] = val

    def _update_stats_label(self):
        total_pecas = 0
        total_m2 = 0.0
        total_fita_m = 0.0
        mats_m2 = {}
        fitas_detalhe = {}  # (espessura, material) -> metros

        for p in self._parts:
            qtd = p.get("quantidade", 1)
            comp_m = p["comprimento"] / 1000.0
            larg_m = p["largura"] / 1000.0
            area = comp_m * larg_m * qtd
            total_pecas += qtd
            total_m2 += area

            mat_name = f"{p['material']}"
            mats_m2[mat_name] = mats_m2.get(mat_name, 0.0) + area

            # Fita de borda
            fita_peca = 0.0
            if p.get("fita_c1"): fita_peca += comp_m
            if p.get("fita_c2"): fita_peca += comp_m
            if p.get("fita_l1"): fita_peca += larg_m
            if p.get("fita_l2"): fita_peca += larg_m
            metros_p = fita_peca * qtd
            total_fita_m += metros_p

            if metros_p > 0:
                esp_f = float(p.get("espessura_fita") or 0.45)
                mat_f = str(p.get("material_fita") or p.get("material") or "Padrão")
                key_f = (esp_f, mat_f)
                fitas_detalhe[key_f] = fitas_detalhe.get(key_f, 0.0) + metros_p

        self.lbl_stats.setText(f"Total: {total_pecas} peça(s) | {total_m2:.2f} m² de chapa")

        if hasattr(self, "lbl_sum_pecas"):
            self.lbl_sum_pecas.setText(f"📦 {total_pecas} peça{'s' if total_pecas != 1 else ''}")

        if hasattr(self, "lbl_sum_fita"):
            resumo_fitas = f"📏 Fita Total: {total_fita_m:.1f} m"
            if fitas_detalhe:
                partes_fita = [
                    f"{metros:.1f}m ({esp}mm {mat})"
                    for (esp, mat), metros in sorted(fitas_detalhe.items())
                ]
                resumo_fitas += " [" + " | ".join(partes_fita) + "]"
            self.lbl_sum_fita.setText(resumo_fitas)

        if hasattr(self, "lbl_sum_chapas"):
            if not mats_m2:
                self.lbl_sum_chapas.setText("🪵 Nenhuma chapa")
            else:
                itens_chapa = []
                for mat, a in mats_m2.items():
                    n_est = max(1, math.ceil(a / 4.3))
                    itens_chapa.append(f"{mat}: {a:.2f} m² (~{n_est} chapa{'s' if n_est > 1 else ''})")
                self.lbl_sum_chapas.setText("🪵 " + "  •  ".join(itens_chapa))

    def _apply_quick_tape_thickness(self, espessura: float):
        selected_rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()))
        if not selected_rows:
            selected_rows = list(range(len(self._parts)))

        for r in selected_rows:
            if r < len(self._parts):
                self._parts[r]["espessura_fita"] = float(espessura)
                # Recalcula corte
                p = self._parts[r]
                from ..production.parts import calculate_cut_dimensions
                comp_corte, larg_corte = calculate_cut_dimensions(
                    p["comprimento"], p["largura"],
                    p.get("fita_c1", False), p.get("fita_c2", False),
                    p.get("fita_l1", False), p.get("fita_l2", False),
                    float(espessura)
                )
                p["comprimento_corte"] = comp_corte
                p["largura_corte"] = larg_corte

        self._populate_table()

    def _apply_quick_tape(self, c1: bool, c2: bool, l1: bool, l2: bool):
        selected_rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()))
        if not selected_rows:
            selected_rows = list(range(len(self._parts)))

        for r in selected_rows:
            self._parts[r]["fita_c1"] = c1
            self._parts[r]["fita_c2"] = c2
            self._parts[r]["fita_l1"] = l1
            self._parts[r]["fita_l2"] = l2

        self._populate_table()

    def _copy_to_trazomob(self):
        tsv_text = format_trazomob_text(self._parts)
        if not tsv_text:
            QMessageBox.information(self, "TrazoMob", "Nenhuma peça detectada no modelo.")
            return

        QApplication.clipboard().setText(tsv_text)

        orig_text = self.btn_copy.text()
        self.btn_copy.setText("✔ COPIADO COM SUCESSO!")
        self.btn_copy.setStyleSheet("background-color: #1b5e20; color: #ffffff; font-weight: bold; padding: 7px 16px;")
        QTimer.singleShot(2500, lambda: [
            self.btn_copy.setText(orig_text),
            self.btn_copy.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 7px 16px; border-radius: 4px;")
        ])

        QMessageBox.information(
            self,
            "TrazoMob — Dados Copiados",
            "As peças foram copiadas para a área de transferência!\n\n"
            "Passo a passo:\n"
            "1. Abra a sua central de corte online ou planilha\n"
            "2. Crie ou abra o seu serviço\n"
            "3. Clique em 'Importar peças' ou 'Colar dados da planilha'\n"
            "4. Dê Ctrl+V no campo e confirme!"
        )

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Lista de Peças CSV", "trazomob.csv", "CSV (*.csv)")
        if not path:
            return
        export_trazomob_csv(self._parts, path)
        QMessageBox.information(self, "TrazoMob", f"Arquivo salvo com sucesso em:\n{path}")

    def _export_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Lista de Peças JSON", "trazomob.json", "JSON (*.json)")
        if not path:
            return
        export_trazomob_json(self._parts, path)
        QMessageBox.information(self, "TrazoMob", f"JSON salvo com sucesso em:\n{path}")

    def _export_hellomob(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Hellomob (.hellomob)", "trazomob.hellomob", "Hellomob (*.hellomob)"
        )
        if not path:
            return
        export_trazomob_hellomob(self._parts, path, scene=getattr(self, "scene", None))
        QMessageBox.information(self, "TrazoMob", f"Arquivo Hellomob salvo com sucesso em:\n{path}")

    def _open_cut_plan_viewer(self):
        """Abre a janela gráfica interativa de visualização e otimização do Plano de Corte 2D."""
        if not getattr(self, "_parts", None):
            self._reload_parts()
        if not self._parts:
            QMessageBox.information(
                self,
                "Plano de Corte 2D",
                "Nenhuma peça de marcenaria encontrada na cena para gerar o plano de corte.\n"
                "Insira módulos ou desenhe chapas antes de gerar o plano de corte."
            )
            return

        dlg = CutPlanViewerDialog(self._parts, parent=self)
        dlg.exec()

    def _duplicate_selected_module(self):
        """Duplica o módulo selecionado no 3D, posicionando-o ao lado com Undo/Redo."""
        target = self._editing_module or self._get_reference_module()
        if not target:
            QMessageBox.information(self, "Duplicar Módulo", "Selecione um módulo no 3D para duplicar.")
            return

        gap_mm = float(self.sp_align_gap.value()) if hasattr(self, "sp_align_gap") else 0.0
        from ..interaction.module_operations import duplicate_contiguous_module
        new_module = duplicate_contiguous_module(
            target,
            direction="right",
            gap_mm=gap_mm,
            viewport=self.viewport,
        )
        if new_module is not None:
            self._editing_module = new_module
            self._last_inserted_module = new_module
            self._load_module_values_if_editing()
            self._reload_parts()
            if hasattr(self, "lbl_dyn_status"):
                self.lbl_dyn_status.setText(f"📋 Módulo '{new_module.name}' duplicado com sucesso!")

    def _delete_selected_module(self):
        """Exclui o módulo selecionado da cena com confirmação e suporte a Undo/Redo."""
        target = self._editing_module or self._get_reference_module()
        if not target:
            return

        from ..interaction.module_operations import delete_module
        if delete_module(target, viewport=self.viewport, prompt_confirm=True, parent_widget=self):
            self._editing_module = None
            self._load_module_values_if_editing()
            self._reload_parts()
            if hasattr(self, "lbl_dyn_status"):
                self.lbl_dyn_status.setText(f"🗑️ Módulo '{target.name}' excluído com sucesso!")

    def _open_production_labels(self):
        """Abre a janela de visualização e exportação de etiquetas de produção com código de barras."""
        if not hasattr(self, "_parts") or not self._parts:
            self._reload_parts()
        if not self._parts:
            QMessageBox.information(self, "Etiquetas", "Nenhuma peça disponível para gerar etiquetas.")
            return
        from ..production.labels import ProductionLabelsDialog
        dlg = ProductionLabelsDialog(self._parts, parent=self)
        dlg.exec()

    def _open_assembly_manual(self):
        """Abre o diálogo para gerar e salvar o Manual de Montagem em HTML."""
        if not hasattr(self, "_parts") or not self._parts:
            self._reload_parts()
        if not self._parts:
            QMessageBox.information(self, "Manual de Montagem",
                                    "Nenhuma peça disponível para gerar o manual de montagem.")
            return

        from ..ui.assembly_manual_dialog import export_assembly_manual
        export_assembly_manual(
            self,
            self._parts,
            project_name="Projeto de Interiores TrazoMob",
        )

    def _export_html_report(self):
        """Exporta um relatório executivo completo em HTML com métricas e lista de corte por ambiente."""
        if not hasattr(self, "_parts") or not self._parts:
            self._reload_parts()
        if not self._parts:
            QMessageBox.information(self, "Relatório", "Nenhuma peça disponível para gerar o relatório.")
            return

        # Pergunta se quer incluir orçamento
        from PySide6.QtWidgets import QCheckBox, QDialogButtonBox
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Opções do Relatório")
        dlg.setText("Deseja incluir a seção de orçamento/preços no relatório?")
        dlg.setIcon(QMessageBox.Question)
        cb = QCheckBox("Incluir orçamento detalhado (preços, markup, impostos, desconto)")
        dlg.setCheckBox(cb)
        dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dlg.setDefaultButton(QMessageBox.Yes)

        if dlg.exec() != QMessageBox.Yes:
            return

        include_pricing = cb.isChecked()

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Relatório Executivo HTML",
            "Relatorio_Executivo_TrazoMob.html",
            "HTML (*.html)"
        )
        if not filepath:
            return

        from ..production.report import generate_project_html_report
        html = generate_project_html_report(
            self._parts,
            project_name="Projeto de Interiores TrazoMob",
            include_pricing=include_pricing,
        )
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        QMessageBox.information(self, "Relatório Salvo", f"✅ Relatório executivo HTML exportado com sucesso em:\n{filepath}")

    def _open_pricing_presentation(self):
        """Abre o painel de orçamentos e propostas com modo apresentação e custos com PIN."""
        if not hasattr(self, "_parts") or not self._parts:
            self._reload_parts()
        if not self._parts:
            QMessageBox.information(self, "Orçamento", "Nenhuma peça disponível para gerar o orçamento.")
            return

        from ..ui.pricing_dialog import PricingProposalPresentationDialog
        dlg = PricingProposalPresentationDialog(self._parts, parent=self)
        dlg.exec()

    def _export_proposal(self):
        """Exporta uma proposta comercial completa (HTML/PDF) com orçamento, cliente, validade e assinatura."""
        if not hasattr(self, "_parts") or not self._parts:
            self._reload_parts()
        if not self._parts:
            QMessageBox.information(self, "Proposta", "Nenhuma peça disponível para gerar a proposta.")
            return

        from ..ui.proposal_dialog import export_proposal

        export_proposal(
            self,
            self._parts,
            project_name="Projeto de Interiores TrazoMob",
        )
