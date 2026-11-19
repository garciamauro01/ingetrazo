# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Diálogo e painel de orçamento híbrido e proposta comercial (Visão Cliente + Retaguarda com PIN)."""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QTabWidget, QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QDoubleSpinBox, QSpinBox, QLineEdit, QFormLayout, QGroupBox,
    QMessageBox, QRadioButton,
    QDialogButtonBox,
)

from ..domain.preferences import TrazoMobPreferencesManager, _hash_pin
from ..production.pricing import (
    agrupar_por_ambiente,
    calcular_orcamento_cutlist,
    calcular_orcamento_por_ambiente,
    formatar_moeda,
)


class PinInputDialog(QDialog):
    """Diálogo compacto para entrada ou definição do PIN de segurança de 4 dígitos."""

    def __init__(self, parent=None, is_setting_new: bool = False):
        super().__init__(parent)
        self.is_setting_new = is_setting_new
        self.setWindowTitle("Definir PIN de Segurança" if is_setting_new else "Acesso Restrito — Painel de Custos")
        self.setFixedSize(340, 180)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl_icon = QLabel("🔐" if not self.is_setting_new else "🛡️")
        lbl_icon.setStyleSheet("font-size: 28px;")
        lbl_icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_icon)

        msg = (
            "Digite o PIN de 4 dígitos para acessar a tabela de custos:"
            if not self.is_setting_new
            else "Crie um PIN numérico para proteger sua margem e custos:"
        )
        lbl_msg = QLabel(msg)
        lbl_msg.setWordWrap(True)
        lbl_msg.setAlignment(Qt.AlignCenter)
        lbl_msg.setStyleSheet("font-size: 11px; color: #374151;")
        layout.addWidget(lbl_msg)

        self.ed_pin = QLineEdit()
        self.ed_pin.setEchoMode(QLineEdit.Password)
        self.ed_pin.setMaxLength(8)
        self.ed_pin.setAlignment(Qt.AlignCenter)
        self.ed_pin.setStyleSheet(
            "font-size: 20px; font-weight: bold; letter-spacing: 6px; padding: 6px;"
            "border: 2px solid #cbd5e1; border-radius: 6px; background-color: #f8fafc;"
        )
        layout.addWidget(self.ed_pin)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self.ed_pin.setFocus()

    def get_pin(self) -> str:
        return self.ed_pin.text().strip()


class AdminCostSettingsDialog(QDialog):
    """Painel administrativo de retaguarda para definição de custos, margens e serviços."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Tabela de Custos e Margens (Retaguarda)")
        self.resize(780, 560)
        self.prefs = TrazoMobPreferencesManager.get_instance()
        # Cópia PROFUNDA: editar os campos não deve alterar as preferências
        # vivas antes do usuário confirmar em "Salvar Alterações".
        self.pricing = copy.deepcopy(self.prefs.get_pricing_config())
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        self.tabs = QTabWidget()
        self._build_tab_chapas_fitas()
        self._build_tab_ferragens()
        self._build_tab_servicos_montagem()
        self._build_tab_formacao_preco()
        self._build_tab_empresa_seguranca()
        main_layout.addWidget(self.tabs)

        # Botões Salvar / Fechar
        bot_bar = QHBoxLayout()
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #047857; font-weight: bold; font-size: 11px;")
        bot_bar.addWidget(self.lbl_status)
        bot_bar.addStretch()

        btn_salvar = QPushButton("💾 Salvar Alterações")
        btn_salvar.setStyleSheet(
            "background-color: #0284c7; color: white; font-weight: bold; padding: 6px 16px; border-radius: 4px;"
        )
        btn_salvar.clicked.connect(self._save_all)
        bot_bar.addWidget(btn_salvar)

        btn_fechar = QPushButton("Fechar")
        btn_fechar.clicked.connect(self.reject)
        bot_bar.addWidget(btn_fechar)

        main_layout.addLayout(bot_bar)

    def _build_tab_chapas_fitas(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(8)

        # Opções de cálculo de chapas
        box_modo = QGroupBox("🪵 Modo de Cobrança das Chapas")
        box_layout = QHBoxLayout(box_modo)

        self.rb_m2_perda = QRadioButton("Área Líquida (m²) + % de perda")
        self.rb_inteira = QRadioButton("Chapas Inteiras compradas (Plano de Corte)")

        cur_modo = self.pricing.get("modo_calculo_chapas", "m2_perda")
        if cur_modo == "inteira":
            self.rb_inteira.setChecked(True)
        else:
            self.rb_m2_perda.setChecked(True)

        box_layout.addWidget(self.rb_m2_perda)
        box_layout.addWidget(self.rb_inteira)

        box_layout.addSpacing(20)
        box_layout.addWidget(QLabel("Taxa de Perda:"))
        self.sp_perda = QDoubleSpinBox()
        self.sp_perda.setRange(0.0, 100.0)
        self.sp_perda.setSuffix(" %")
        self.sp_perda.setValue(float(self.pricing.get("perda_chapa_percent", 0.15)) * 100.0)
        box_layout.addWidget(self.sp_perda)
        box_layout.addStretch()

        layout.addWidget(box_modo)

        # Tabela de Chapas
        layout.addWidget(QLabel("<b>Tabela de Preços de Chapas (R$/m² e Chapa Inteira 2750x1850mm):</b>"))
        self.tbl_chapas = QTableWidget()
        self.tbl_chapas.setColumnCount(3)
        self.tbl_chapas.setHorizontalHeaderLabels(["Material e Espessura", "Preço por m² (R$)", "Chapa Inteira (R$)"])
        self.tbl_chapas.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_chapas.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_chapas.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self.tbl_chapas)

        self._populate_chapas_table()

        # Fitas de Borda
        fita_box = QGroupBox("📏 Fitas de Borda (Preço por Metro Linear)")
        fita_layout = QHBoxLayout(fita_box)
        self.sp_fita_045 = QDoubleSpinBox()
        self.sp_fita_045.setRange(0.0, 999.0)
        self.sp_fita_045.setPrefix("R$ ")
        self.sp_fita_045.setValue(float(self.pricing.get("fita_borda_m", {}).get("0.45mm", 1.80)))

        self.sp_fita_100 = QDoubleSpinBox()
        self.sp_fita_100.setRange(0.0, 999.0)
        self.sp_fita_100.setPrefix("R$ ")
        self.sp_fita_100.setValue(float(self.pricing.get("fita_borda_m", {}).get("1.0mm", 2.50)))

        self.sp_fita_200 = QDoubleSpinBox()
        self.sp_fita_200.setRange(0.0, 999.0)
        self.sp_fita_200.setPrefix("R$ ")
        self.sp_fita_200.setValue(float(self.pricing.get("fita_borda_m", {}).get("2.0mm", 4.20)))

        fita_layout.addWidget(QLabel("Fita 0,45 mm:"))
        fita_layout.addWidget(self.sp_fita_045)
        fita_layout.addSpacing(10)
        fita_layout.addWidget(QLabel("Fita 1,0 mm:"))
        fita_layout.addWidget(self.sp_fita_100)
        fita_layout.addSpacing(10)
        fita_layout.addWidget(QLabel("Fita 2,0 mm:"))
        fita_layout.addWidget(self.sp_fita_200)
        fita_layout.addStretch()

        layout.addWidget(fita_box)
        self.tabs.addTab(w, "🪵 Chapas & Fitas")

    def _populate_chapas_table(self):
        chapas_m2 = self.pricing.get("chapas_m2", {})
        chapas_inteiras = self.pricing.get("chapas_inteiras", {})
        dim = self.pricing.get("chapa_padrao_dim", [2750.0, 1850.0])
        area_int = (float(dim[0]) / 1000.0) * (float(dim[1]) / 1000.0) or 5.0875

        self.tbl_chapas.setRowCount(len(chapas_m2))
        for row, (mat_desc, p_m2) in enumerate(sorted(chapas_m2.items())):
            it_name = QTableWidgetItem(mat_desc)
            it_name.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            if p_m2 <= 0:
                it_name.setBackground(QColor("#fef2f2"))
                it_name.setForeground(QColor("#b91c1c"))

            self.tbl_chapas.setItem(row, 0, it_name)

            sp_m2 = QDoubleSpinBox()
            sp_m2.setRange(0.0, 9999.0)
            sp_m2.setPrefix("R$ ")
            sp_m2.setValue(float(p_m2))

            sp_int = QDoubleSpinBox()
            sp_int.setRange(0.0, 99999.0)
            sp_int.setPrefix("R$ ")
            p_int_val = chapas_inteiras.get(mat_desc, p_m2 * area_int)
            sp_int.setValue(float(p_int_val))

            def _sync_m2(val, s_int=sp_int, a=area_int):
                s_int.blockSignals(True)
                s_int.setValue(round(val * a, 2))
                s_int.blockSignals(False)

            def _sync_int(val, s_m2=sp_m2, a=area_int):
                s_m2.blockSignals(True)
                s_m2.setValue(round(val / a, 2) if a > 0 else 0.0)
                s_m2.blockSignals(False)

            sp_m2.valueChanged.connect(_sync_m2)
            sp_int.valueChanged.connect(_sync_int)

            self.tbl_chapas.setCellWidget(row, 1, sp_m2)
            self.tbl_chapas.setCellWidget(row, 2, sp_int)

    def _build_tab_ferragens(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(10)

        box_mult = QGroupBox("🔩 Multiplicadores de Linhas de Ferragens")
        b_layout = QHBoxLayout(box_mult)
        mults = self.pricing.get("linhas_ferragens_multiplicador", {})

        b_layout.addWidget(QLabel("Econômica:"))
        self.sp_mult_eco = QDoubleSpinBox()
        self.sp_mult_eco.setRange(0.1, 5.0)
        self.sp_mult_eco.setSingleStep(0.05)
        self.sp_mult_eco.setValue(float(mults.get("economica", 0.75)))
        b_layout.addWidget(self.sp_mult_eco)

        b_layout.addSpacing(10)
        b_layout.addWidget(QLabel("Standard (Base):"))
        self.sp_mult_std = QDoubleSpinBox()
        self.sp_mult_std.setRange(0.1, 5.0)
        self.sp_mult_std.setValue(float(mults.get("standard", 1.00)))
        self.sp_mult_std.setEnabled(False)
        b_layout.addWidget(self.sp_mult_std)

        b_layout.addSpacing(10)
        b_layout.addWidget(QLabel("Premium (Amortecedor / Oculta):"))
        self.sp_mult_prem = QDoubleSpinBox()
        self.sp_mult_prem.setRange(0.1, 10.0)
        self.sp_mult_prem.setSingleStep(0.1)
        self.sp_mult_prem.setValue(float(mults.get("premium", 2.20)))
        b_layout.addWidget(self.sp_mult_prem)
        b_layout.addStretch()

        layout.addWidget(box_mult)

        layout.addWidget(QLabel("<b>Tabela Base de Ferragens Unitárias (R$):</b>"))
        self.tbl_hw = QTableWidget()
        self.tbl_hw.setColumnCount(2)
        self.tbl_hw.setHorizontalHeaderLabels(["Item / Componente", "Preço Base Standard (R$)"])
        self.tbl_hw.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_hw.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        layout.addWidget(self.tbl_hw)

        hw_dict = self.pricing.get("ferragens", {})
        self.tbl_hw.setRowCount(len(hw_dict))
        for r, (k, v) in enumerate(sorted(hw_dict.items())):
            it_name = QTableWidgetItem(k.replace("_", " ").title())
            it_name.setData(Qt.UserRole, k)
            it_name.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.tbl_hw.setItem(r, 0, it_name)

            sp_price = QDoubleSpinBox()
            sp_price.setRange(0.0, 9999.0)
            sp_price.setPrefix("R$ ")
            sp_price.setValue(float(v))
            self.tbl_hw.setCellWidget(r, 1, sp_price)

        self.tabs.addTab(w, "🔩 Ferragens & Linhas")

    def _build_tab_servicos_montagem(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.sp_serv_corte = QDoubleSpinBox()
        self.sp_serv_corte.setRange(0.0, 999.0)
        self.sp_serv_corte.setPrefix("R$ ")
        self.sp_serv_corte.setValue(float(self.pricing.get("servico_corte_por_chapa", 35.00)))
        form.addRow("Corte terceirizado por Chapa:", self.sp_serv_corte)

        self.sp_serv_fita = QDoubleSpinBox()
        self.sp_serv_fita.setRange(0.0, 999.0)
        self.sp_serv_fita.setPrefix("R$ ")
        self.sp_serv_fita.setValue(float(self.pricing.get("servico_fita_por_metro", 3.50)))
        form.addRow("Colagem terceirizada por Metro de Fita:", self.sp_serv_fita)

        self.sp_mao_obra = QDoubleSpinBox()
        self.sp_mao_obra.setRange(0.0, 999.0)
        self.sp_mao_obra.setPrefix("R$ ")
        self.sp_mao_obra.setValue(float(self.pricing.get("mao_de_obra_m2", 45.00)))
        form.addRow("Mão de obra interna de fabricação (R$/m² chapa):", self.sp_mao_obra)

        self.cb_montagem_tipo = QComboBox()
        self.cb_montagem_tipo.addItems(["Percentual sobre Custo (%)", "Valor Fixo (R$)", "Por m² de Chapa (R$/m²)"])
        m_tipo = self.pricing.get("montagem_tipo", "percentual")
        if m_tipo == "fixo":
            self.cb_montagem_tipo.setCurrentIndex(1)
        elif m_tipo == "por_m2":
            self.cb_montagem_tipo.setCurrentIndex(2)
        else:
            self.cb_montagem_tipo.setCurrentIndex(0)

        self.sp_montagem_val = QDoubleSpinBox()
        self.sp_montagem_val.setRange(0.0, 99999.0)
        m_val = float(self.pricing.get("montagem_valor", 0.12))
        self.sp_montagem_val.setValue(m_val * 100.0 if m_tipo == "percentual" else m_val)
        form.addRow("Tipo de taxa de Montagem / Instalação:", self.cb_montagem_tipo)
        form.addRow("Valor / Alíquota da Montagem:", self.sp_montagem_val)

        layout.addLayout(form)
        layout.addStretch()
        self.tabs.addTab(w, "🏭 Serviços & Montagem")

    def _build_tab_formacao_preco(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)

        box_formacao = QGroupBox("📈 Método de Formação do Preço de Venda")
        b_layout = QVBoxLayout(box_formacao)

        self.rb_modo_detalhado = QRadioButton("Composição Detalhada (Custos + Montagem + Markup % + Impostos %)")
        self.rb_modo_mult = QRadioButton("Fator Multiplicador Rápido sobre Materiais (ex: 2.8x)")

        if self.pricing.get("modo_fechamento", "detalhado") == "multiplicador":
            self.rb_modo_mult.setChecked(True)
        else:
            self.rb_modo_detalhado.setChecked(True)

        b_layout.addWidget(self.rb_modo_detalhado)
        b_layout.addWidget(self.rb_modo_mult)
        layout.addWidget(box_formacao)

        form = QFormLayout()
        self.sp_mult_fator = QDoubleSpinBox()
        self.sp_mult_fator.setRange(1.0, 10.0)
        self.sp_mult_fator.setSingleStep(0.1)
        self.sp_mult_fator.setValue(float(self.pricing.get("fator_multiplicador", 2.80)))
        form.addRow("Fator Multiplicador (Modo Simples):", self.sp_mult_fator)

        self.sp_markup = QDoubleSpinBox()
        self.sp_markup.setRange(0.0, 300.0)
        self.sp_markup.setSuffix(" %")
        self.sp_markup.setValue((float(self.pricing.get("markup", 1.35)) - 1.0) * 100.0)
        form.addRow("Markup / Margem de Lucro Desejada:", self.sp_markup)

        self.sp_impostos = QDoubleSpinBox()
        self.sp_impostos.setRange(0.0, 50.0)
        self.sp_impostos.setSuffix(" %")
        self.sp_impostos.setValue(float(self.pricing.get("impostos_percent", 0.18)) * 100.0)
        form.addRow("Impostos e Tributos:", self.sp_impostos)

        self.sp_desconto = QDoubleSpinBox()
        self.sp_desconto.setRange(0.0, 30.0)
        self.sp_desconto.setSuffix(" %")
        self.sp_desconto.setValue(float(self.pricing.get("desconto_percent", 0.05)) * 100.0)
        form.addRow("Desconto Padrão à Vista:", self.sp_desconto)

        self.sp_parcelas = QSpinBox()
        self.sp_parcelas.setRange(1, 24)
        self.sp_parcelas.setValue(int(self.pricing.get("parcelas_sem_juros", 6)))
        form.addRow("Número de Parcelas Padrão:", self.sp_parcelas)

        layout.addLayout(form)
        layout.addStretch()
        self.tabs.addTab(w, "📈 Formação de Preço")

    def _build_tab_empresa_seguranca(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)

        # PIN de Segurança
        box_pin = QGroupBox("🛡️ Segurança e Proteção por PIN")
        pin_layout = QHBoxLayout(box_pin)
        self.lbl_pin_info = QLabel("")
        self.lbl_pin_info.setStyleSheet("font-weight: bold; font-size: 11px;")
        self._refresh_pin_label()
        pin_layout.addWidget(self.lbl_pin_info)

        btn_alterar_pin = QPushButton("Alterar / Criar PIN")
        btn_alterar_pin.clicked.connect(self._change_pin)
        pin_layout.addWidget(btn_alterar_pin)

        btn_remover_pin = QPushButton("Remover PIN")
        btn_remover_pin.clicked.connect(self._remove_pin)
        pin_layout.addWidget(btn_remover_pin)
        pin_layout.addStretch()
        layout.addWidget(box_pin)

        # Dados da Empresa
        box_emp = QGroupBox("🏢 Dados Cadastrais da Marcenaria (Cabeçalho da Proposta)")
        emp_layout = QFormLayout(box_emp)
        emp = self.pricing.get("empresa", {})

        self.ed_emp_nome = QLineEdit(emp.get("nome", "Marcenaria TrazoMob"))
        self.ed_emp_cnpj = QLineEdit(emp.get("cnpj", ""))
        self.ed_emp_tel = QLineEdit(emp.get("telefone", ""))
        self.ed_emp_email = QLineEdit(emp.get("email", ""))
        self.ed_emp_end = QLineEdit(emp.get("endereco", ""))

        emp_layout.addRow("Nome Fantasia:", self.ed_emp_nome)
        emp_layout.addRow("CNPJ / CPF:", self.ed_emp_cnpj)
        emp_layout.addRow("Telefone / WhatsApp:", self.ed_emp_tel)
        emp_layout.addRow("E-mail:", self.ed_emp_email)
        emp_layout.addRow("Endereço Completo:", self.ed_emp_end)

        layout.addWidget(box_emp)
        layout.addStretch()
        self.tabs.addTab(w, "🏢 Empresa & Segurança")

    def _pin_is_set(self) -> bool:
        """PIN definido na cópia de trabalho (ainda não necessariamente salvo)."""
        return bool(str(self.pricing.get("pin_hash", "") or "").strip())

    def _refresh_pin_label(self):
        self.lbl_pin_info.setText(
            "Status do PIN: 🔒 Protegido com PIN" if self._pin_is_set()
            else "Status do PIN: 🔓 Aberto (Sem PIN)"
        )

    def _change_pin(self):
        dlg = PinInputDialog(self, is_setting_new=True)
        if dlg.exec() == QDialog.Accepted:
            new_pin = dlg.get_pin()
            if len(new_pin) < 3:
                QMessageBox.warning(self, "PIN", "O PIN deve conter pelo menos 3 caracteres.")
                return
            # Aplicado apenas na cópia de trabalho; persiste em "Salvar Alterações".
            self.pricing["pin_hash"] = _hash_pin(new_pin)
            self._refresh_pin_label()
            QMessageBox.information(self, "PIN", "✅ Novo PIN será aplicado ao salvar as alterações.")

    def _remove_pin(self):
        self.pricing["pin_hash"] = ""
        self._refresh_pin_label()
        QMessageBox.information(self, "PIN", "🔓 O PIN será removido ao salvar as alterações.")

    def _save_all(self):
        # 1. Chapas
        chapas_m2 = {}
        chapas_inteiras = {}
        for r in range(self.tbl_chapas.rowCount()):
            desc = self.tbl_chapas.item(r, 0).text().strip()
            sp_m2 = self.tbl_chapas.cellWidget(r, 1)
            sp_int = self.tbl_chapas.cellWidget(r, 2)
            if sp_m2 and sp_int:
                chapas_m2[desc] = sp_m2.value()
                chapas_inteiras[desc] = sp_int.value()

        self.pricing["chapas_m2"] = chapas_m2
        self.pricing["chapas_inteiras"] = chapas_inteiras
        self.pricing["modo_calculo_chapas"] = "inteira" if self.rb_inteira.isChecked() else "m2_perda"
        self.pricing["perda_chapa_percent"] = self.sp_perda.value() / 100.0

        # Fitas
        self.pricing.setdefault("fita_borda_m", {})["0.45mm"] = self.sp_fita_045.value()
        self.pricing.setdefault("fita_borda_m", {})["1.0mm"] = self.sp_fita_100.value()
        self.pricing.setdefault("fita_borda_m", {})["2.0mm"] = self.sp_fita_200.value()

        # Ferragens
        hw = {}
        for r in range(self.tbl_hw.rowCount()):
            key = self.tbl_hw.item(r, 0).data(Qt.UserRole)
            sp = self.tbl_hw.cellWidget(r, 1)
            if key and sp:
                hw[key] = sp.value()
        self.pricing["ferragens"] = hw
        self.pricing.setdefault("linhas_ferragens_multiplicador", {})["economica"] = self.sp_mult_eco.value()
        self.pricing.setdefault("linhas_ferragens_multiplicador", {})["premium"] = self.sp_mult_prem.value()

        # Serviços e Montagem
        self.pricing["servico_corte_por_chapa"] = self.sp_serv_corte.value()
        self.pricing["servico_fita_por_metro"] = self.sp_serv_fita.value()
        self.pricing["mao_de_obra_m2"] = self.sp_mao_obra.value()

        idx_m = self.cb_montagem_tipo.currentIndex()
        if idx_m == 1:
            self.pricing["montagem_tipo"] = "fixo"
            self.pricing["montagem_valor"] = self.sp_montagem_val.value()
        elif idx_m == 2:
            self.pricing["montagem_tipo"] = "por_m2"
            self.pricing["montagem_valor"] = self.sp_montagem_val.value()
        else:
            self.pricing["montagem_tipo"] = "percentual"
            self.pricing["montagem_valor"] = self.sp_montagem_val.value() / 100.0

        # Formação de Preço
        self.pricing["modo_fechamento"] = "multiplicador" if self.rb_modo_mult.isChecked() else "detalhado"
        self.pricing["fator_multiplicador"] = self.sp_mult_fator.value()
        self.pricing["markup"] = 1.0 + (self.sp_markup.value() / 100.0)
        self.pricing["impostos_percent"] = self.sp_impostos.value() / 100.0
        self.pricing["desconto_percent"] = self.sp_desconto.value() / 100.0
        self.pricing["parcelas_sem_juros"] = self.sp_parcelas.value()

        # Empresa
        emp = self.pricing.setdefault("empresa", {})
        emp["nome"] = self.ed_emp_nome.text().strip()
        emp["cnpj"] = self.ed_emp_cnpj.text().strip()
        emp["telefone"] = self.ed_emp_tel.text().strip()
        emp["email"] = self.ed_emp_email.text().strip()
        emp["endereco"] = self.ed_emp_end.text().strip()

        self.prefs.save_pricing_config(self.pricing)
        self.lbl_status.setText("✅ Alterações salvas com sucesso!")
        self.accept()


class PricingProposalPresentationDialog(QDialog):
    """Janela de Orçamento e Proposta Comercial no Modo Apresentação (Visão Cliente)."""

    def __init__(self, parts: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("💼 Proposta Comercial & Orçamento (Visão de Apresentação)")
        self.resize(760, 520)
        self.parts = parts
        self.prefs = TrazoMobPreferencesManager.get_instance()
        self._init_ui()
        self._recompute()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # Barra Superior: Seletor de Padrão de Ferragem + Acesso Seguro
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("<b>Padrão de Ferragens:</b>"))
        self.cb_linha_hw = QComboBox()
        self.cb_linha_hw.addItem("🌱 Linha Econômica", "economica")
        self.cb_linha_hw.addItem("⭐ Linha Standard (Com Amortecedores)", "standard")
        self.cb_linha_hw.addItem("💎 Linha Premium (Corrediças Ocultas / Blum)", "premium")
        self.cb_linha_hw.setCurrentIndex(1)
        self.cb_linha_hw.currentIndexChanged.connect(self._recompute)
        top_bar.addWidget(self.cb_linha_hw)

        top_bar.addStretch()

        self.btn_admin_costs = QPushButton("🔐 Custos & Tabela de Preços")
        self.btn_admin_costs.setStyleSheet(
            "background-color: #f1f5f9; color: #334155; font-size: 11px; padding: 4px 10px;"
            "border: 1px solid #cbd5e1; border-radius: 4px; font-weight: bold;"
        )
        self.btn_admin_costs.clicked.connect(self._open_admin_panel)
        top_bar.addWidget(self.btn_admin_costs)

        main_layout.addLayout(top_bar)

        # Banner de Alerta de Preços Zerados (oculto por padrão)
        self.banner_alerta = QLabel("")
        self.banner_alerta.setStyleSheet(
            "background-color: #fef2f2; color: #b91c1c; font-weight: bold; font-size: 11px;"
            "padding: 6px 12px; border: 1px solid #fca5a5; border-radius: 4px;"
        )
        self.banner_alerta.setVisible(False)
        main_layout.addWidget(self.banner_alerta)

        # Tabela de Ambientes (Visão Cliente: sem custos nem margens)
        main_layout.addWidget(QLabel("<b>Resumo do Investimento por Ambiente:</b>"))
        self.tbl_ambientes = QTableWidget()
        self.tbl_ambientes.setColumnCount(3)
        self.tbl_ambientes.setHorizontalHeaderLabels(["Ambiente / Cômodo", "Peças / Área (m²)", "Valor de Venda (R$)"])
        self.tbl_ambientes.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_ambientes.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_ambientes.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_ambientes.setAlternatingRowColors(True)
        main_layout.addWidget(self.tbl_ambientes)

        # Painel de Condições de Pagamento
        card_pagto = QGroupBox("💳 Condições Comerciais & Pagamento")
        card_pagto.setStyleSheet("QGroupBox { font-weight: bold; font-size: 12px; }")
        card_layout = QHBoxLayout(card_pagto)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(24)

        self.lbl_total_vista = QLabel("À Vista: R$ 0,00")
        self.lbl_total_vista.setStyleSheet("font-size: 15px; font-weight: bold; color: #15803d;")
        card_layout.addWidget(self.lbl_total_vista)

        self.lbl_parcelamento = QLabel("Ou 6x de R$ 0,00")
        self.lbl_parcelamento.setStyleSheet("font-size: 14px; font-weight: 500; color: #1e293b;")
        card_layout.addWidget(self.lbl_parcelamento)

        card_layout.addStretch()

        self.lbl_total_final = QLabel("À Prazo: R$ 0,00")
        self.lbl_total_final.setStyleSheet("font-size: 18px; font-weight: 900; color: #0f172a;")
        card_layout.addWidget(self.lbl_total_final)

        main_layout.addWidget(card_pagto)

        # Barra de Ações (Emitir Proposta / Fechar)
        bot_bar = QHBoxLayout()
        btn_proposta = QPushButton("📄 Gerar Proposta Comercial (HTML/PDF)")
        btn_proposta.setStyleSheet(
            "background-color: #7c3aed; color: white; font-weight: bold; font-size: 12px;"
            "padding: 8px 18px; border-radius: 4px;"
        )
        btn_proposta.clicked.connect(self._export_proposal)
        bot_bar.addWidget(btn_proposta)

        bot_bar.addStretch()

        btn_fechar = QPushButton("Fechar")
        btn_fechar.clicked.connect(self.accept)
        bot_bar.addWidget(btn_fechar)

        main_layout.addLayout(bot_bar)

    def _open_admin_panel(self):
        # Validação por PIN
        if self.prefs.has_pin():
            dlg_pin = PinInputDialog(self)
            if dlg_pin.exec() != QDialog.Accepted:
                return
            if not self.prefs.check_pin(dlg_pin.get_pin()):
                QMessageBox.warning(self, "Acesso Negado", "❌ PIN incorreto.")
                return

        admin_dlg = AdminCostSettingsDialog(self)
        if admin_dlg.exec() == QDialog.Accepted:
            self._recompute()

    def _recompute(self):
        linha = self.cb_linha_hw.currentData() or "standard"
        self.resumo_geral = calcular_orcamento_cutlist(self.parts, linha_ferragem_override=linha)
        self.resumo_ambientes = calcular_orcamento_por_ambiente(self.parts)

        # Alerta de itens sem preço
        if self.resumo_geral.itens_sem_preco:
            itens_str = ", ".join(self.resumo_geral.itens_sem_preco[:3])
            extra = f" (+{len(self.resumo_geral.itens_sem_preco)-3})" if len(self.resumo_geral.itens_sem_preco) > 3 else ""
            self.banner_alerta.setText(f"⚠️ Atenção: {len(self.resumo_geral.itens_sem_preco)} item(ns) com preço R$ 0,00 na tabela: {itens_str}{extra}. Acesse 'Custos' para preencher.")
            self.banner_alerta.setVisible(True)
        else:
            self.banner_alerta.setVisible(False)

        # Preenche tabela de ambientes
        grupos = agrupar_por_ambiente(self.parts)
        self.tbl_ambientes.setRowCount(len(self.resumo_ambientes))
        for r, (amb_name, r_amb) in enumerate(self.resumo_ambientes.items()):
            amb_parts = grupos.get(amb_name, [])
            total_m2 = sum((p.get("comprimento", 0)/1000.0) * (p.get("largura", 0)/1000.0) * p.get("quantidade", 1) for p in amb_parts)
            qtd_p = sum(p.get("quantidade", 1) for p in amb_parts)

            self.tbl_ambientes.setItem(r, 0, QTableWidgetItem(f"📍 {amb_name}"))
            self.tbl_ambientes.setItem(r, 1, QTableWidgetItem(f"{qtd_p} peças ({total_m2:.2f} m²)"))

            it_val = QTableWidgetItem(formatar_moeda(r_amb.total_final))
            it_val.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            f = self.tbl_ambientes.font()
            f.setBold(True)
            it_val.setFont(f)
            self.tbl_ambientes.setItem(r, 2, it_val)

        # Atualiza card de condições comerciais
        self.lbl_total_vista.setText(f"À Vista: {formatar_moeda(self.resumo_geral.total_a_vista)}")
        self.lbl_parcelamento.setText(
            f"Ou {self.resumo_geral.num_parcelas}x de {formatar_moeda(self.resumo_geral.valor_parcela)} sem juros"
        )
        self.lbl_total_final.setText(f"À Prazo: {formatar_moeda(self.resumo_geral.total_parcelado)}")

    def _export_proposal(self):
        from .proposal_dialog import export_proposal

        export_proposal(
            self,
            self.parts,
            project_name="Projeto de Marcenaria TrazoMob",
        )

