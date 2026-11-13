# SPDX-License-Identifier: GPL-3.0-or-later
"""Main Furniture Pro window: project, libraries, manufacturing and quote."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox,
                               QDialog, QDoubleSpinBox, QFileDialog,
                               QFormLayout, QGridLayout, QGroupBox,
                               QHBoxLayout, QLabel, QLineEdit, QMenu,
                               QMessageBox, QPlainTextEdit, QPushButton,
                               QScrollArea, QSplitter, QTabWidget,
                               QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget)

from ..core.constants import (CARCASS_METHODS, DEFAULT_CURRENCIES,
                              GRAIN_LABELS, HARDWARE_CATEGORIES,
                              MODULE_LABELS, PLUGIN_VERSION)
from ..core.errors import FurnitureError
from ..core.logging_utils import get_logger
from ..furniture import templates
from ..manufacturing import CutSettings
from ..pricing import PricingSettings, format_money
from ..persistence import PROJECT_FILTER, PROJECT_SUFFIX
from .cut_view import CutPlanView
from .library_dialogs import (EdgeBandDialog, HardwareDialog, MaterialDialog)
from .module_form import ModuleEditorDialog

logger = get_logger()


def _money(value: float, currency: str) -> str:
    return format_money(value, currency)


def _table(headers: list[str]) -> QTableWidget:
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setStretchLastSection(True)
    return table


def _pct_spin() -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setRange(0, 100)
    box.setDecimals(2)
    box.setSuffix(" %")
    return box


def _field(form: QFormLayout, label: str, widget: QWidget) -> QWidget:
    form.addRow(label, widget)
    return widget


class FurnitureDialog(QDialog):
    """The single window users open from the Extensions menu."""

    def __init__(self, controller, parent=None, initial_tab: int = 0) -> None:
        super().__init__(parent)
        self.controller = controller
        self._busy = False
        self._mfg_loaded = False
        self._quote_loaded = False
        self.setWindowTitle("Ingetrazo Furniture Pro")
        self.resize(1180, 820)
        self.setMinimumSize(960, 680)
        self._build_ui()
        self.refresh_all()
        if 0 <= initial_tab < self.tabs.count():
            self.tabs.setCurrentIndex(initial_tab)

    # ==================================================================
    # UI construction
    # ==================================================================
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.addWidget(self._header())
        self.tabs = QTabWidget()
        self.tabs.addTab(self._project_tab(), "Projeto")
        self.tabs.addTab(self._materials_tab(), "Materiais e fitas")
        self.tabs.addTab(self._hardware_tab(), "Ferragens")
        self.tabs.addTab(self._manufacturing_tab(), "Fabricação")
        self.tabs.addTab(self._quote_tab(), "Orçamento")
        self.tabs.addTab(self._settings_tab(), "Configurações")
        self.tabs.currentChanged.connect(self._tab_changed)
        root.addWidget(self.tabs, 1)
        self.status = QLabel("Pronto.")
        self.status.setStyleSheet("color: #475569; padding: 4px 2px;")
        root.addWidget(self.status)

    def _header(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        title = QLabel("Furniture Pro")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)
        self.header_project = QLabel("")
        self.header_project.setStyleSheet("color: #334155;")
        layout.addWidget(self.header_project, 1)
        version = QLabel(PLUGIN_VERSION)
        version.setStyleSheet("color: #94a3b8;")
        layout.addWidget(version)
        return widget

    # -- project -------------------------------------------------------
    def _project_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        splitter = QSplitter(Qt.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.module_table = _table(["Código", "Nome", "Tipo",
                                    "L × A × P (mm)", "Ambiente"])
        self.module_table.doubleClicked.connect(lambda _i: self.edit_module())
        left_layout.addWidget(self.module_table, 1)
        buttons = QHBoxLayout()
        self.add_button = QPushButton("Inserir…")
        self.add_button.clicked.connect(self._add_menu)
        for label, slot in (("Editar…", self.edit_module),
                            ("Duplicar", self.duplicate_module),
                            ("Excluir", self.delete_module),
                            ("Regerar", self.rebuild_module)):
            button = QPushButton(label)
            button.clicked.connect(slot)
            buttons.addWidget(button)
        buttons.insertWidget(0, self.add_button)
        left_layout.addLayout(buttons)
        order = QHBoxLayout()
        up = QPushButton("Mover ↑")
        down = QPushButton("Mover ↓")
        up.clicked.connect(lambda: self._move_module(-1))
        down.clicked.connect(lambda: self._move_module(1))
        order.addWidget(up)
        order.addWidget(down)
        order.addStretch(1)
        left_layout.addLayout(order)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        summary_box = QGroupBox("Resumo")
        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        self.summary_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        box_layout = QVBoxLayout(summary_box)
        box_layout.addWidget(self.summary_label)
        right_layout.addWidget(summary_box)
        warn_box = QGroupBox("Avisos de validação")
        self.validation_text = QPlainTextEdit()
        self.validation_text.setReadOnly(True)
        box_layout = QVBoxLayout(warn_box)
        box_layout.addWidget(self.validation_text)
        right_layout.addWidget(warn_box, 1)
        splitter.addWidget(right)
        splitter.setSizes([720, 420])
        layout.addWidget(splitter, 1)
        return page

    # -- materials -----------------------------------------------------
    def _materials_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        inner = QTabWidget()
        # Materials
        materials_page = QWidget()
        m_layout = QVBoxLayout(materials_page)
        self.material_table = _table(
            ["Nome", "Categoria", "Esp.", "Chapa (mm)", "Custo chapa",
             "Custo m²", "Veio", "Disponível"])
        self.material_table.doubleClicked.connect(
            lambda _i: self.edit_material())
        m_layout.addWidget(self.material_table, 1)
        row = QHBoxLayout()
        for label, slot in (("Novo material…", self.add_material),
                            ("Editar…", self.edit_material),
                            ("Remover", self.remove_material)):
            button = QPushButton(label)
            button.clicked.connect(slot)
            row.addWidget(button)
        row.addStretch(1)
        save = QPushButton("Salvar bibliotecas")
        save.clicked.connect(self.save_libraries)
        row.addWidget(save)
        m_layout.addLayout(row)
        inner.addTab(materials_page, "Materiais")
        # Edge bands
        bands_page = QWidget()
        b_layout = QVBoxLayout(bands_page)
        self.band_table = _table(["Nome", "Espessura", "Material",
                                  "Custo/m", "Fornecedor", "Disponível"])
        self.band_table.doubleClicked.connect(lambda _i: self.edit_band())
        b_layout.addWidget(self.band_table, 1)
        row = QHBoxLayout()
        for label, slot in (("Nova fita…", self.add_band),
                            ("Editar…", self.edit_band),
                            ("Remover", self.remove_band)):
            button = QPushButton(label)
            button.clicked.connect(slot)
            row.addWidget(button)
        row.addStretch(1)
        b_layout.addLayout(row)
        inner.addTab(bands_page, "Fitas de borda")
        layout.addWidget(inner, 1)
        return page

    # -- hardware ------------------------------------------------------
    def _hardware_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.hardware_table = _table(["Nome", "Categoria", "Referência",
                                      "Unidade", "Custo", "Verificado"])
        self.hardware_table.doubleClicked.connect(
            lambda _i: self.edit_hardware())
        layout.addWidget(self.hardware_table, 1)
        row = QHBoxLayout()
        for label, slot in (("Nova ferragem…", self.add_hardware),
                            ("Editar…", self.edit_hardware),
                            ("Remover", self.remove_hardware)):
            button = QPushButton(label)
            button.clicked.connect(slot)
            row.addWidget(button)
        row.addStretch(1)
        layout.addLayout(row)
        note = QLabel(
            "“Verificado” significa que os dados de instalação vieram do "
            "catálogo do fabricante. O plugin não inventa copo, recuo ou "
            "entre-eixos de dobradiças e corrediças.")
        note.setWordWrap(True)
        note.setStyleSheet("color: #64748b;")
        layout.addWidget(note)
        return page

    # -- manufacturing -------------------------------------------------
    def _manufacturing_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        row = QHBoxLayout()
        for label, slot in (("Calcular plano", self.refresh_manufacturing),
                            ("Exportar lista (CSV)", self.export_parts_csv),
                            ("Exportar plano (CSV)", self.export_cut_csv),
                            ("Relatório PDF…", self.export_pdf),
                            ("Pacote completo…", self.export_bundle)):
            button = QPushButton(label)
            button.clicked.connect(slot)
            row.addWidget(button)
        layout.addLayout(row)
        self.mfg_summary = QLabel("")
        self.mfg_summary.setWordWrap(True)
        layout.addWidget(self.mfg_summary)
        inner = QTabWidget()
        parts_page = QWidget()
        p_layout = QVBoxLayout(parts_page)
        self.parts_table = _table(["Cód.", "Peça", "Módulos", "Material",
                                   "Esp.", "Comp.", "Larg.", "Qtd", "m²"])
        p_layout.addWidget(self.parts_table, 1)
        inner.addTab(parts_page, "Lista de peças")
        cut_page = QWidget()
        c_layout = QVBoxLayout(cut_page)
        self.cut_view = CutPlanView()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.cut_view)
        c_layout.addWidget(scroll, 1)
        inner.addTab(cut_page, "Plano de corte")
        warn_page = QWidget()
        w_layout = QVBoxLayout(warn_page)
        self.mfg_warnings = QPlainTextEdit()
        self.mfg_warnings.setReadOnly(True)
        w_layout.addWidget(self.mfg_warnings)
        inner.addTab(warn_page, "Avisos")
        layout.addWidget(inner, 1)
        return page

    # -- quote ---------------------------------------------------------
    def _quote_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        box = QGroupBox("Parâmetros comerciais")
        grid = QGridLayout(box)
        self.pricing_fields: dict[str, QDoubleSpinBox] = {}
        self.currency_combo = QComboBox()
        self.currency_combo.addItems(DEFAULT_CURRENCIES)
        fields = (
            ("margin_on_sale", "Margem sobre venda", "margem"),
            ("markup_on_cost", "Markup sobre custo", "markup"),
            ("discount_rate", "Desconto", "desconto"),
            ("tax_rate", "Impostos", "imposto"),
            ("commission_rate", "Comissão", "comissão"),
            ("overhead_rate", "Overhead", "custo indireto"),
            ("waste_rate", "Perda de material", "perda"),
        )
        for index, (key, label, tip) in enumerate(fields):
            spin = _pct_spin()
            spin.setToolTip(
                f"{tip}: aplicado conforme a fórmula documentada. "
                "Margem sobre venda e markup sobre custo são grandezas "
                "diferentes; não use uma chamando de outra.")
            self.pricing_fields[key] = spin
            grid.addWidget(QLabel(label), index // 3, (index % 3) * 2)
            grid.addWidget(spin, index // 3, (index % 3) * 2 + 1)
        self.labor_hour = QDoubleSpinBox()
        self.labor_hour.setRange(0, 1_000_000)
        self.labor_hour.setDecimals(2)
        self.assembly_hours = QDoubleSpinBox()
        self.assembly_hours.setRange(0, 1000)
        self.assembly_hours.setDecimals(2)
        self.labor_hours = QDoubleSpinBox()
        self.labor_hours.setRange(0, 100000)
        self.labor_hours.setDecimals(2)
        self.freight = QDoubleSpinBox()
        self.freight.setRange(0, 10_000_000)
        self.freight.setDecimals(2)
        self.extra_cost = QDoubleSpinBox()
        self.extra_cost.setRange(0, 10_000_000)
        self.extra_cost.setDecimals(2)
        self.rounding = QDoubleSpinBox()
        self.rounding.setRange(0, 100)
        self.rounding.setDecimals(2)
        grid.addWidget(QLabel("Valor/hora"), 3, 0)
        grid.addWidget(self.labor_hour, 3, 1)
        grid.addWidget(QLabel("Horas de montagem/módulo"), 3, 2)
        grid.addWidget(self.assembly_hours, 3, 3)
        grid.addWidget(QLabel("Horas avulsas"), 3, 4)
        grid.addWidget(self.labor_hours, 3, 5)
        grid.addWidget(QLabel("Frete"), 4, 0)
        grid.addWidget(self.freight, 4, 1)
        grid.addWidget(QLabel("Custos extras"), 4, 2)
        grid.addWidget(self.extra_cost, 4, 3)
        grid.addWidget(QLabel("Arredondamento"), 4, 4)
        grid.addWidget(self.rounding, 4, 5)
        grid.addWidget(QLabel("Moeda"), 5, 0)
        grid.addWidget(self.currency_combo, 5, 1)
        layout.addWidget(box)
        row = QHBoxLayout()
        calc = QPushButton("Calcular orçamento")
        calc.clicked.connect(lambda: self.refresh_quote(force=True))
        save = QPushButton("Salvar parâmetros no documento")
        save.clicked.connect(self.save_pricing)
        export = QPushButton("Exportar orçamento (CSV)…")
        export.clicked.connect(self.export_quote_csv)
        row.addWidget(calc)
        row.addWidget(save)
        row.addWidget(export)
        row.addStretch(1)
        layout.addLayout(row)
        self.quote_totals = QLabel("")
        self.quote_totals.setFont(QFont("Arial", 11))
        self.quote_totals.setWordWrap(True)
        layout.addWidget(self.quote_totals)
        self.quote_table = _table(["Módulo", "Código", "Custo", "Venda",
                                   "Margem", "Markup"])
        layout.addWidget(self.quote_table, 1)
        self.quote_warnings = QPlainTextEdit()
        self.quote_warnings.setReadOnly(True)
        self.quote_warnings.setMaximumHeight(110)
        layout.addWidget(self.quote_warnings)
        return page

    # -- settings ------------------------------------------------------
    def _settings_tab(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        project_box = QGroupBox("Projeto")
        form = QFormLayout(project_box)
        self.project_name = QLineEdit()
        self.project_code = QLineEdit()
        self.project_client = QLineEdit()
        self.project_contact = QLineEdit()
        self.project_address = QLineEdit()
        self.units_combo = QComboBox()
        self.units_combo.addItem("Milímetros (mm)", "mm")
        self.units_combo.addItem("Centímetros (cm)", "cm")
        self.units_combo.addItem("Metros (m)", "m")
        self.precision = QDoubleSpinBox()
        self.precision.setRange(0.001, 10)
        self.precision.setDecimals(3)
        self.precision.setSuffix(" mm")
        self.company_name = QLineEdit()
        self.company_document = QLineEdit()
        self.validity = QDoubleSpinBox()
        self.validity.setRange(0, 3650)
        self.validity.setDecimals(0)
        self.validity.setSuffix(" dias")
        _field(form, "Nome do projeto", self.project_name)
        _field(form, "Código", self.project_code)
        _field(form, "Cliente", self.project_client)
        _field(form, "Contato", self.project_contact)
        _field(form, "Endereço", self.project_address)
        _field(form, "Unidades de exibição", self.units_combo)
        _field(form, "Precisão de exibição", self.precision)
        _field(form, "Empresa", self.company_name)
        _field(form, "CNPJ / documento", self.company_document)
        _field(form, "Validade do orçamento", self.validity)
        outer.addWidget(project_box)

        cut_box = QGroupBox("Plano de corte")
        form = QFormLayout(cut_box)
        self.kerf = QDoubleSpinBox()
        self.kerf.setRange(0, 50)
        self.kerf.setDecimals(1)
        self.kerf.setSuffix(" mm")
        self.trim = QDoubleSpinBox()
        self.trim.setRange(0, 200)
        self.trim.setDecimals(1)
        self.trim.setSuffix(" mm")
        self.min_offcut = QDoubleSpinBox()
        self.min_offcut.setRange(0, 1000)
        self.min_offcut.setDecimals(1)
        self.min_offcut.setSuffix(" mm")
        self.rot_ok = QComboBox()
        self.rot_ok.addItem("Permitir quando o material permitir", True)
        self.rot_ok.addItem("Nunca girar peças", False)
        _field(form, "Kerf (espessura do corte)", self.kerf)
        _field(form, "Refilo da chapa", self.trim)
        _field(form, "Retalho mínimo útil", self.min_offcut)
        _field(form, "Rotação", self.rot_ok)
        outer.addWidget(cut_box)

        notes_box = QGroupBox("Observações de fabricação")
        n_layout = QVBoxLayout(notes_box)
        self.construction_notes = QPlainTextEdit()
        n_layout.addWidget(self.construction_notes)
        outer.addWidget(notes_box, 1)

        row = QHBoxLayout()
        save = QPushButton("Salvar dados no documento")
        save.clicked.connect(self.save_project_data)
        save_file = QPushButton("Salvar projeto em arquivo…")
        save_file.clicked.connect(self.save_project_file)
        open_file = QPushButton("Abrir projeto…")
        open_file.clicked.connect(self.open_project_file)
        export = QPushButton("Exportar pacote…")
        export.clicked.connect(self.export_bundle)
        diag = QPushButton("Diagnóstico…")
        diag.clicked.connect(self.show_diagnostics)
        for button in (save, save_file, open_file, export, diag):
            row.addWidget(button)
        row.addStretch(1)
        outer.addLayout(row)
        return page

    # ==================================================================
    # Refresh
    # ==================================================================
    def refresh_all(self) -> None:
        if self._busy:
            return
        self._busy = True
        try:
            self._refresh_header()
            self._refresh_project()
            self._refresh_materials()
            self._refresh_hardware()
            self._refresh_settings()
            self._mfg_loaded = False
            self._quote_loaded = False
            self._refresh_quote_fields()
        finally:
            self._busy = False
        if self.tabs.currentIndex() == 3:
            self.refresh_manufacturing()
        elif self.tabs.currentIndex() == 4:
            self.refresh_quote()

    def refresh_from_document(self) -> None:
        """Called when the host document changes (undo, open, new)."""
        if self._busy:
            return
        self._busy = True
        try:
            self.controller.reload()
        finally:
            self._busy = False
        self.refresh_all()

    def _refresh_header(self) -> None:
        project = self.controller.project
        self.header_project.setText(
            f"{project.name or 'Projeto sem nome'}"
            + (f" · {project.client}" if project.client else "")
            + f" · {len(project.modules)} módulo(s)")

    def _refresh_project(self) -> None:
        project = self.controller.project
        self.module_table.setRowCount(0)
        for spec in project.modules:
            row = self.module_table.rowCount()
            self.module_table.insertRow(row)
            values = (spec.code, spec.label, MODULE_LABELS.get(spec.type,
                                                               spec.type),
                      f"{spec.width_mm:.0f} × {spec.height_mm:.0f} × "
                      f"{spec.depth_mm:.0f}",
                      spec.room or "Geral")
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col == 0:
                    item.setData(Qt.UserRole, spec.id)
                self.module_table.setItem(row, col, item)
        report = self.controller.validation()
        self.validation_text.setPlainText(report.as_text())
        total_width = sum(s.width_mm for s in project.modules)
        self.summary_label.setText(
            f"Módulos: {len(project.modules)}\n"
            f"Ambientes: {', '.join(project.rooms()) or '—'}\n"
            f"Soma das larguras: {total_width:,.0f} mm\n"
            f"Chapas/fitas: {len(self.controller.materials.materials)} / "
            f"{len(self.controller.materials.edge_bands)}\n"
            f"Ferragens: {len(self.controller.hardware.items)}\n"
            f"Erros: {len(report.errors)} · Avisos: {len(report.warnings)}")
        self._refresh_header()

    def _refresh_materials(self) -> None:
        library = self.controller.materials
        self.material_table.setRowCount(0)
        for material in library.materials.values():
            row = self.material_table.rowCount()
            self.material_table.insertRow(row)
            values = (material.name, material.category,
                      f"{material.thickness_mm:g} mm",
                      f"{material.sheet_length_mm:.0f} × "
                      f"{material.sheet_width_mm:.0f}",
                      _money(material.cost_per_sheet, library_currency(self)),
                      _money(material.cost_per_m2, library_currency(self)),
                      GRAIN_LABELS.get(material.grain_axis,
                                       material.grain_axis),
                      "Sim" if material.availability else "Não")
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col == 0:
                    item.setData(Qt.UserRole, material.id)
                self.material_table.setItem(row, col, item)
        self.band_table.setRowCount(0)
        for band in library.edge_bands.values():
            row = self.band_table.rowCount()
            self.band_table.insertRow(row)
            values = (band.name, f"{band.thickness_mm:g} mm", band.material,
                      _money(band.cost_per_m, library_currency(self)),
                      band.supplier, "Sim" if band.availability else "Não")
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col == 0:
                    item.setData(Qt.UserRole, band.id)
                self.band_table.setItem(row, col, item)

    def _refresh_hardware(self) -> None:
        self.hardware_table.setRowCount(0)
        for item in self.controller.hardware.items.values():
            row = self.hardware_table.rowCount()
            self.hardware_table.insertRow(row)
            values = (item.name,
                      HARDWARE_CATEGORIES.get(item.category, item.category),
                      item.reference, item.unit,
                      _money(item.cost, library_currency(self)),
                      "Sim" if item.verified else "Não")
            for col, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                if col == 0:
                    cell.setData(Qt.UserRole, item.id)
                self.hardware_table.setItem(row, col, cell)

    def _refresh_settings(self) -> None:
        project = self.controller.project
        settings = project.settings
        self.project_name.setText(project.name)
        self.project_code.setText(project.code)
        self.project_client.setText(project.client)
        self.project_contact.setText(project.client_contact)
        self.project_address.setText(project.address)
        self.units_combo.setCurrentIndex(max(0, self.units_combo.findData(
            settings.units)))
        self.precision.setValue(settings.precision_mm)
        self.company_name.setText(settings.company_name)
        self.company_document.setText(settings.company_document)
        self.validity.setValue(settings.validity_days)
        cut = CutSettings.from_dict(project.cut)
        self.kerf.setValue(cut.kerf_mm)
        self.trim.setValue(cut.trim_mm)
        self.min_offcut.setValue(cut.min_offcut_mm)
        self.rot_ok.setCurrentIndex(0 if cut.allow_rotation else 1)
        self.construction_notes.setPlainText(settings.construction_notes)

    def _refresh_quote_fields(self) -> None:
        pricing = PricingSettings.from_dict(self.controller.project.pricing)
        for key, spin in self.pricing_fields.items():
            spin.setValue(float(getattr(pricing, key, 0.0)) * 100.0)
        self.labor_hour.setValue(pricing.labor_cost_per_hour)
        self.assembly_hours.setValue(pricing.assembly_hours_per_module)
        self.labor_hours.setValue(pricing.labor_hours)
        self.freight.setValue(pricing.freight)
        self.extra_cost.setValue(pricing.extra_cost)
        self.rounding.setValue(pricing.rounding_step)
        index = self.currency_combo.findText(pricing.currency)
        if index >= 0:
            self.currency_combo.setCurrentIndex(index)

    # ==================================================================
    # Project actions
    # ==================================================================
    def _selected_id(self) -> str | None:
        row = self.module_table.currentRow()
        if row < 0:
            return None
        item = self.module_table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def selected_spec(self):
        module_id = self._selected_id()
        return self.controller.project.module(module_id) if module_id else None

    def _add_menu(self) -> None:
        menu = QMenu(self)
        categories: dict[str, list] = {}
        for template in templates():
            categories.setdefault(template.category, []).append(template)
        for category, items in categories.items():
            submenu = menu.addMenu(category)
            for template in items:
                action = submenu.addAction(template.label)
                action.setToolTip(template.description)
                action.triggered.connect(
                    lambda _checked=False, t=template: self._insert_template(t))
        menu.addSeparator()
        custom = menu.addAction("Módulo personalizado…")
        custom.triggered.connect(self._insert_custom)
        menu.exec(self.add_button.mapToGlobal(self.add_button.rect().bottomLeft()))

    def _edit_spec(self, spec):
        dialog = ModuleEditorDialog(self.controller, spec, self)
        return dialog.result_spec() if dialog.exec() == QDialog.Accepted else None

    def _insert_template(self, template) -> None:
        spec = template.create()
        spec.code = self.controller.project.next_code(spec.type)
        self._insert_spec(spec)

    def _insert_custom(self) -> None:
        from ..core.models import ModuleSpec
        spec = ModuleSpec(type="personalizado", name="Módulo personalizado")
        spec.code = self.controller.project.next_code(spec.type)
        self._insert_spec(spec)

    def _insert_spec(self, spec) -> None:
        result = self._edit_spec(spec)
        if result is None:
            return
        self._run("Inserir módulo", lambda: self.controller.insert_module(result))
        self.refresh_all()

    def edit_module(self) -> None:
        spec = self.selected_spec()
        if spec is None:
            return
        result = self._edit_spec(spec.copy())
        if result is None:
            return
        self._run("Editar módulo", lambda: self.controller.update_module(result))
        self.refresh_all()

    def duplicate_module(self) -> None:
        spec = self.selected_spec()
        if spec is None:
            return
        self._run("Duplicar módulo",
                  lambda: self.controller.duplicate_module(spec.id))
        self.refresh_all()

    def delete_module(self) -> None:
        spec = self.selected_spec()
        if spec is None:
            return
        answer = QMessageBox.question(
            self, "Excluir módulo",
            f"Excluir “{spec.label}” e toda a geometria gerada?")
        if answer != QMessageBox.Yes:
            return
        self._run("Excluir módulo",
                  lambda: self.controller.delete_module(spec.id))
        self.refresh_all()

    def rebuild_module(self) -> None:
        spec = self.selected_spec()
        if spec is None:
            return
        self._run("Regerar módulo",
                  lambda: self.controller.update_module(spec.copy()))
        self.refresh_all()

    def _move_module(self, delta: int) -> None:
        spec = self.selected_spec()
        if spec is None:
            return
        self.controller.project.move_module(spec.id, delta)
        self._run("Reordenar módulo", self.controller.store_project)
        self.refresh_all()

    # ==================================================================
    # Library actions
    # ==================================================================
    def _selected_material_id(self):
        row = self.material_table.currentRow()
        if row < 0:
            return None
        item = self.material_table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _selected_band_id(self):
        row = self.band_table.currentRow()
        if row < 0:
            return None
        item = self.band_table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _selected_hardware_id(self):
        row = self.hardware_table.currentRow()
        if row < 0:
            return None
        item = self.hardware_table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def add_material(self) -> None:
        dialog = MaterialDialog(edge_bands=self.controller.materials.edge_bands,
                                parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            material = dialog.result_material()
            self.controller.materials.add_material(material)
            self.controller.save_libraries()
            self.controller.invalidate()
        except Exception as exc:                        # noqa: BLE001
            self._error("Material", exc)
            return
        self.refresh_all()

    def edit_material(self) -> None:
        material_id = self._selected_material_id()
        material = self.controller.materials.material(material_id) if material_id else None
        if material is None:
            return
        dialog = MaterialDialog(material, edge_bands=self.controller.materials.edge_bands,
                                parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.controller.materials.update_material(dialog.result_material())
            self.controller.save_libraries()
            self.controller.invalidate()
        except Exception as exc:                        # noqa: BLE001
            self._error("Material", exc)
            return
        self.refresh_all()

    def remove_material(self) -> None:
        material_id = self._selected_material_id()
        if not material_id:
            return
        in_use = any(s.material_id == material_id or
                     s.front_material_id == material_id or
                     s.back_material_id == material_id
                     for s in self.controller.project.modules)
        if in_use:
            QMessageBox.warning(self, "Material em uso",
                                "Este material está associado a um módulo. "
                                "Troque o material dos módulos antes de removê-lo.")
            return
        self.controller.materials.remove_material(material_id)
        self.controller.save_libraries()
        self.controller.invalidate()
        self.refresh_all()

    def add_band(self) -> None:
        dialog = EdgeBandDialog(parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.controller.materials.add_edge_band(dialog.result_band())
            self.controller.save_libraries()
            self.controller.invalidate()
        except Exception as exc:                        # noqa: BLE001
            self._error("Fita de borda", exc)
            return
        self.refresh_all()

    def edit_band(self) -> None:
        band_id = self._selected_band_id()
        band = self.controller.materials.edge_band(band_id) if band_id else None
        if band is None:
            return
        dialog = EdgeBandDialog(band, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.controller.materials.update_edge_band(dialog.result_band())
            self.controller.save_libraries()
            self.controller.invalidate()
        except Exception as exc:                        # noqa: BLE001
            self._error("Fita de borda", exc)
            return
        self.refresh_all()

    def remove_band(self) -> None:
        band_id = self._selected_band_id()
        if band_id:
            self.controller.materials.remove_edge_band(band_id)
            self.controller.save_libraries()
            self.controller.invalidate()
            self.refresh_all()

    def add_hardware(self) -> None:
        dialog = HardwareDialog(parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.controller.hardware.add(dialog.result_item())
            self.controller.save_libraries()
        except Exception as exc:                        # noqa: BLE001
            self._error("Ferragem", exc)
            return
        self.refresh_all()

    def edit_hardware(self) -> None:
        item_id = self._selected_hardware_id()
        item = self.controller.hardware.get(item_id) if item_id else None
        if item is None:
            return
        dialog = HardwareDialog(item, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.controller.hardware.update(dialog.result_item())
            self.controller.save_libraries()
        except Exception as exc:                        # noqa: BLE001
            self._error("Ferragem", exc)
            return
        self.refresh_all()

    def remove_hardware(self) -> None:
        item_id = self._selected_hardware_id()
        if item_id:
            self.controller.hardware.remove(item_id)
            self.controller.save_libraries()
            self.refresh_all()

    def save_libraries(self) -> None:
        self._run("Salvar bibliotecas", self.controller.save_libraries)
        self.set_status("Bibliotecas salvas.")

    # ==================================================================
    # Manufacturing
    # ==================================================================
    def refresh_manufacturing(self, *_args) -> None:
        if self._busy:
            return
        self._busy = True
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            parts = self.controller.parts_list()
            self.parts_table.setRowCount(0)
            for item in parts.items:
                row = self.parts_table.rowCount()
                self.parts_table.insertRow(row)
                material = self.controller.materials.material(item.material_id)
                values = (item.code, item.name,
                          ", ".join(item.source_codes),
                          material.name if material else item.material_id,
                          f"{item.thickness_mm:g}", f"{item.length_mm:g}",
                          f"{item.width_mm:g}", item.qty,
                          f"{item.area_m2:.3f}")
                for col, value in enumerate(values):
                    self.parts_table.setItem(row, col, QTableWidgetItem(str(value)))
            plan = None
            problem = ""
            try:
                plan = self.controller.cut_plan()
            except FurnitureError as exc:
                problem = exc.user_message
            self.cut_view.set_plan(plan)
            if plan is not None:
                self.mfg_summary.setText(
                    f"Peças: {parts.total_pieces} · Área: "
                    f"{parts.total_area_m2:.3f} m² · Chapas: {plan.board_count}"
                    f" · Aproveitamento: {plan.utilization * 100:.1f}%"
                    f" · Não encaixadas: {len(plan.unplaced)}")
                warnings = list(parts.warnings) + list(plan.warnings)
            else:
                self.mfg_summary.setText(
                    f"Peças: {parts.total_pieces} · Área: "
                    f"{parts.total_area_m2:.3f} m² · Plano de corte indisponível.")
                warnings = list(parts.warnings) + ([problem] if problem else [])
            self.mfg_warnings.setPlainText(
                "\n".join(f"• {w}" for w in warnings) or "Sem avisos.")
            self._mfg_loaded = True
            self.set_status("Lista de peças e plano de corte atualizados.")
        except Exception as exc:                        # noqa: BLE001
            logger.exception("manufacturing refresh failed")
            self._error("Fabricação", exc)
        finally:
            QApplication.restoreOverrideCursor()
            self._busy = False

    def export_parts_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar lista de peças", "lista_de_pecas.csv",
            "CSV (*.csv)")
        if not path:
            return
        from ..manufacturing import write_parts_csv
        self._run("Exportar lista", lambda: write_parts_csv(
            path, self.controller.parts_list(),
            self.controller.materials.materials))
        self.set_status(f"Lista exportada: {path}")

    def export_cut_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar plano de corte", "plano_de_corte.csv",
            "CSV (*.csv)")
        if not path:
            return
        from ..manufacturing import write_cut_plan_csv
        self._run("Exportar plano", lambda: write_cut_plan_csv(
            path, self.controller.cut_plan()))
        self.set_status(f"Plano exportado: {path}")

    def export_pdf(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Relatório em PDF", "relatorio.pdf", "PDF (*.pdf)")
        if not path:
            return
        from ..manufacturing import write_pdf_report
        parts = self.controller.parts_list()
        plan = self.controller.cut_plan()
        quote = self.controller.quote()

        def run():
            write_pdf_report(
                path, title=self.controller.project.name or "Projeto",
                parts=parts, plan=plan, quote=quote,
                materials=self.controller.materials.materials,
                hardware=self.controller.hardware.items)
        self._run("Relatório PDF", run)
        self.set_status(f"Relatório exportado: {path}")

    def export_bundle(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Escolher pasta para o pacote")
        if not directory:
            return
        try:
            result = self.controller.export_bundle(directory)
        except Exception as exc:                        # noqa: BLE001
            self._error("Pacote", exc)
            return
        message = f"{len(result['files'])} arquivo(s) gravados em:\n{directory}"
        if result["warnings"]:
            message += "\n\nAvisos:\n" + "\n".join(result["warnings"])
        QMessageBox.information(self, "Pacote exportado", message)
        self.set_status("Pacote exportado.")

    def export_quote_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar orçamento", "orcamento.csv", "CSV (*.csv)")
        if not path:
            return
        from ..import_export.bundle import _quote_csv_text
        quote = self.controller.quote()

        def run():
            Path(path).write_text(_quote_csv_text(quote), encoding="utf-8-sig")
        self._run("Exportar orçamento", run)
        self.set_status(f"Orçamento exportado: {path}")

    # ==================================================================
    # Quote
    # ==================================================================
    def _pricing_from_form(self) -> PricingSettings:
        settings = PricingSettings.from_dict(self.controller.project.pricing)
        for key, spin in self.pricing_fields.items():
            setattr(settings, key, spin.value() / 100.0)
        settings.labor_cost_per_hour = self.labor_hour.value()
        settings.assembly_hours_per_module = self.assembly_hours.value()
        settings.labor_hours = self.labor_hours.value()
        settings.freight = self.freight.value()
        settings.extra_cost = self.extra_cost.value()
        settings.rounding_step = self.rounding.value()
        settings.currency = self.currency_combo.currentText()
        return settings

    def refresh_quote(self, *, force: bool = False) -> None:
        if self._busy:
            return
        self._busy = True
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            settings = self._pricing_from_form()
            self.controller.set_pricing_settings(settings)
            quote = self.controller.quote(force=force)
            currency = quote.currency
            self.quote_totals.setText(
                f"Custo: {_money(quote.cost, currency)}   ·   "
                f"Total: {_money(quote.total, currency)}   ·   "
                f"Margem sobre venda: {quote.margin_on_sale * 100:.1f}%   ·   "
                f"Markup sobre custo: {quote.markup_on_cost * 100:.1f}%\n"
                f"Modo: {'margem sobre venda' if quote.pricing_mode == 'margin' else 'markup sobre custo'} "
                f"· Impostos: {_money(quote.tax, currency)} · Desconto: "
                f"{_money(quote.discount, currency)}")
            self.quote_table.setRowCount(0)
            for row in quote.modules:
                index = self.quote_table.rowCount()
                self.quote_table.insertRow(index)
                values = (row.name, row.code, _money(row.cost, currency),
                          _money(row.sale, currency),
                          f"{row.margin * 100:.1f}%", f"{row.markup * 100:.1f}%")
                for col, value in enumerate(values):
                    self.quote_table.setItem(index, col, QTableWidgetItem(value))
            self.quote_warnings.setPlainText(
                "\n".join(f"• {w}" for w in quote.warnings) or "Sem avisos.")
            self._quote_loaded = True
            self.set_status("Orçamento calculado.")
        except Exception as exc:                        # noqa: BLE001
            logger.exception("quote failed")
            self._error("Orçamento", exc)
        finally:
            QApplication.restoreOverrideCursor()
            self._busy = False

    def save_pricing(self) -> None:
        settings = self._pricing_from_form()
        problems = settings.validate()
        if problems:
            QMessageBox.warning(self, "Parâmetros inválidos",
                                "\n".join(f"• {p}" for p in problems))
            return
        self.controller.set_pricing_settings(settings)
        self._run("Salvar orçamento", self.controller.store_project)
        self.set_status("Parâmetros comerciais salvos no documento.")

    # ==================================================================
    # Settings and files
    # ==================================================================
    def save_project_data(self) -> None:
        project = self.controller.project
        project.name = self.project_name.text().strip() or "Projeto sem nome"
        project.code = self.project_code.text().strip()
        project.client = self.project_client.text().strip()
        project.client_contact = self.project_contact.text().strip()
        project.address = self.project_address.text().strip()
        project.settings.units = self.units_combo.currentData() or "mm"
        project.settings.precision_mm = self.precision.value()
        project.settings.currency = self.currency_combo.currentText()
        project.settings.company_name = self.company_name.text().strip()
        project.settings.company_document = self.company_document.text().strip()
        project.settings.validity_days = int(self.validity.value())
        project.settings.construction_notes = \
            self.construction_notes.toPlainText()
        cut = CutSettings.from_dict(project.cut)
        cut.kerf_mm = self.kerf.value()
        cut.trim_mm = self.trim.value()
        cut.min_offcut_mm = self.min_offcut.value()
        cut.allow_rotation = bool(self.rot_ok.currentData())
        self.controller.set_cut_settings(cut)
        self._run("Salvar projeto", self.controller.store_project)
        self._mfg_loaded = False
        self.set_status("Dados do projeto salvos no documento.")
        self.refresh_all()

    def save_project_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar projeto Furniture Pro", "projeto.fproj",
            PROJECT_FILTER)
        if not path:
            return
        if not path.lower().endswith((".fproj", ".json")):
            path += PROJECT_SUFFIX
        self._run("Salvar arquivo", lambda: self.controller.save_project(path))
        self.set_status(f"Projeto salvo: {path}")

    def open_project_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir projeto Furniture Pro", "", PROJECT_FILTER)
        if not path:
            return
        try:
            project = self.controller.load_project(path)
        except Exception as exc:                        # noqa: BLE001
            self._error("Abrir projeto", exc)
            return
        self.refresh_all()
        warnings = project.load_warnings
        message = f"Projeto aberto: {project.name}"
        if warnings:
            message += "\n\nAvisos:\n" + "\n".join(warnings[:12])
        QMessageBox.information(self, "Projeto aberto", message)
        self.set_status("Projeto aberto.")

    def show_diagnostics(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Diagnóstico — Furniture Pro")
        dialog.resize(760, 560)
        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText(self.controller.environment_report())
        layout = QVBoxLayout(dialog)
        layout.addWidget(text)
        close = QPushButton("Fechar")
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()

    # ==================================================================
    # Helpers
    # ==================================================================
    def _tab_changed(self, index: int) -> None:
        if index == 3 and not self._mfg_loaded:
            self.refresh_manufacturing()
        elif index == 4 and not self._quote_loaded:
            self.refresh_quote()

    def _run(self, label: str, function):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            result = function()
            return result
        except FurnitureError as exc:
            logger.warning("%s: %s", label, exc)
            QMessageBox.warning(self, label, exc.user_message
                                + (f"\n\n{exc.details}" if exc.details else ""))
            return None
        except Exception as exc:                        # noqa: BLE001
            logger.exception("%s failed", label)
            QMessageBox.critical(self, label,
                                 f"Falha inesperada: {exc}")
            return None
        finally:
            QApplication.restoreOverrideCursor()

    def _error(self, title: str, exc: Exception) -> None:
        if isinstance(exc, FurnitureError):
            QMessageBox.warning(self, title, exc.user_message)
        else:
            logger.exception("%s failed", title)
            QMessageBox.critical(self, title, f"Falha inesperada: {exc}")

    def set_status(self, text: str) -> None:
        self.status.setText(text)


def library_currency(dialog) -> str:
    try:
        return dialog.controller.project.settings.currency or "BRL"
    except Exception:                                   # noqa: BLE001
        return "BRL"
