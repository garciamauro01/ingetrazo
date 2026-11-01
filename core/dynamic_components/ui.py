# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
"""Diálogos da interface de Componentes Dinâmicos (Atributos e Opções) com paridade 100% ao SketchUp."""
from __future__ import annotations

from typing import Any
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .model import ensure_dc_data, evaluate_dc, get_dc_data, STANDARD_ATTRIBUTES


# Grupos de atributos categorizados exatamente como no SketchUp
DC_ATTRIBUTE_CATEGORIES = [
    (
        "Informações do componente",
        [
            ("Name", "Nome", ""),
            ("Summary", "Resumo", ""),
            ("Description", "Descrição", ""),
            ("ItemCode", "Código do Item", ""),
        ],
    ),
    (
        "Posição",
        [
            ("X", "Posição X", "m"),
            ("Y", "Posição Y", "m"),
            ("Z", "Posição Z", "m"),
        ],
    ),
    (
        "Tamanho",
        [
            ("LenX", "Tamanho X", "m"),
            ("LenY", "Tamanho Y", "m"),
            ("LenZ", "Tamanho Z", "m"),
        ],
    ),
    (
        "Rotação",
        [
            ("RotX", "Rotação X", "deg"),
            ("RotY", "Rotação Y", "deg"),
            ("RotZ", "Rotação Z", "deg"),
        ],
    ),
    (
        "Comportamentos",
        [
            ("Material", "Material", ""),
            ("ScaleTool", "Ferramenta Escala", ""),
            ("Hidden", "Oculto", ""),
            ("onClick", "Comportamento ao clicar", ""),
            ("Copies", "Número de Cópias", ""),
        ],
    ),
]


class ComponentOptionsDialog(QDialog):
    """Janela 'Opções do componente' (estilo Component Options do SketchUp, não-modal)."""

    def __init__(self, group, viewport=None, parent=None):
        super().__init__(parent)
        self.group = group
        self.viewport = viewport
        self.setModal(False)
        self.setWindowTitle("Opções de componente")
        self.resize(360, 480)
        self._fields: dict[str, QWidget] = {}
        self.btn_apply: QPushButton | None = None
        self._setup_ui()

    def set_group(self, group):
        """Atualiza o grupo exibido sem recriar o diálogo."""
        self.group = group
        self._setup_ui()

    def _setup_ui(self):
        # Limpa layout anterior se houver
        if self.layout() is not None:
            QWidget().setLayout(self.layout())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        self._fields.clear()

        grp_name = getattr(self.group, 'name', 'Componente') if self.group else 'Componente'
        self.setWindowTitle(f"Opções de componente - {grp_name}")

        data = get_dc_data(self.group) if self.group else None
        if not data and self.group:
            data = ensure_dc_data(self.group)

        # Cabeçalho no estilo SketchUp (Banner / Caixa de Título)
        header_widget = QWidget()
        header_widget.setStyleSheet("background-color: palette(midlight); border-bottom: 1px solid palette(mid); border-radius: 2px;")
        h_layout = QHBoxLayout(header_widget)
        h_layout.setContentsMargins(8, 8, 8, 8)

        # Miniatura real do componente (estilo SketchUp Thumbnail)
        icon_lbl = QLabel()
        pm = None
        if self.group:
            try:
                from views.component_thumbs import thumbnail
                pm = thumbnail(self.group, size=64)
            except Exception:
                pm = None

        if pm is not None and not pm.isNull():
            icon_lbl.setPixmap(pm)
            icon_lbl.setStyleSheet("border: 1px solid palette(mid); border-radius: 3px; background-color: palette(base);")
        else:
            icon_lbl.setText("📦")
            icon_font = QFont()
            icon_font.setPointSize(24)
            icon_lbl.setFont(icon_font)
        h_layout.addWidget(icon_lbl)

        # Nome do componente
        title_lbl = QLabel(f"<h3>{grp_name}</h3>")
        title_lbl.setStyleSheet("color: palette(text); font-weight: bold;")
        h_layout.addWidget(title_lbl)
        h_layout.addStretch()

        layout.addWidget(header_widget)

        # Descrição opcional
        desc = (data.get("description", "") if data else "").strip()
        if desc:
            lbl_desc = QLabel(desc)
            lbl_desc.setWordWrap(True)
            lbl_desc.setStyleSheet("color: palette(placeholder-text); font-size: 11px;")
            layout.addWidget(lbl_desc)

        # Filtrar atributos configurados para o usuário final
        # No SketchUp: o painel de opções só exibe campos que foram configurados
        # como opção do usuário (user_editable, options lista pré-definida, ou rótulo explícito que não seja atributo interno)
        attrs = (data.get("attributes", {}) if data else {})
        user_options = {}

        for name, info in attrs.items():
            # Atributos internos geométricos padrão nunca aparecem em Opções a menos que tenham opções ou user_editable
            is_standard = name in ("X", "Y", "Z", "LenX", "LenY", "LenZ", "RotX", "RotY", "RotZ", "Copies", "Copy", "Hidden", "Material", "ScaleTool")
            has_options = bool(info.get("options"))
            is_user_editable = bool(info.get("user_editable", False))

            if has_options or is_user_editable:
                user_options[name] = info

        if not user_options:
            # Estado vazio idêntico ao SketchUp
            empty_lbl = QLabel("<i>Não há nenhuma opção para escolher neste componente.</i>")
            empty_lbl.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            empty_lbl.setStyleSheet("color: palette(placeholder-text); padding: 16px 4px; font-size: 12px;")
            empty_lbl.setWordWrap(True)
            layout.addWidget(empty_lbl)
            layout.addStretch()

            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            self.btn_apply = QPushButton("Aplicar")
            self.btn_apply.setEnabled(False)
            self.btn_apply.setStyleSheet("padding: 4px 18px;")
            btn_layout.addWidget(self.btn_apply)
            btn_layout.addStretch()
            layout.addLayout(btn_layout)
            return

        # Formulário dinâmico com as opções do usuário
        form = QFormLayout()
        form.setSpacing(8)

        def _to_display_val(raw_val, d_unit: str):
            if d_unit == "cm":
                try: return round(float(raw_val) * 100.0, 2)
                except Exception: return raw_val
            elif d_unit == "mm":
                try: return round(float(raw_val) * 1000.0, 1)
                except Exception: return raw_val
            elif d_unit == "in":
                try: return round(float(raw_val) / 0.0254, 2)
                except Exception: return raw_val
            return raw_val

        for name, info in user_options.items():
            has_formula = bool(str(info.get("formula", "")).strip())
            disp_unit = info.get("display_unit") or info.get("unit", "")
            lbl_text = info.get("label", name)
            label_text = f"{lbl_text} ({disp_unit}):" if disp_unit else f"{lbl_text}:"

            options = info.get("options", [])
            raw_curr = info.get("value", "")
            disp_curr = str(_to_display_val(raw_curr, disp_unit))

            if options:
                cmb = QComboBox()
                selected_idx = -1
                for i, opt in enumerate(options):
                    if isinstance(opt, dict):
                        opt_label = str(opt.get("label", opt.get("value", "")))
                        opt_val = opt.get("value", "")
                    else:
                        opt_label = str(opt)
                        opt_val = opt
                    
                    cmb.addItem(opt_label, opt_val)
                    # Verifica se corresponde ao valor atual (ou ao rótulo)
                    if str(opt_val) == str(raw_curr) or str(opt_label) == str(raw_curr):
                        selected_idx = i

                if selected_idx >= 0:
                    cmb.setCurrentIndex(selected_idx)
                else:
                    # Tenta encontrar por texto de exibição
                    idx = cmb.findText(disp_curr)
                    if idx >= 0:
                        cmb.setCurrentIndex(idx)

                cmb.setEnabled(not has_formula)
                cmb.setProperty("disp_unit", disp_unit)
                form.addRow(label_text, cmb)
                self._fields[name] = cmb
            else:
                edit = QLineEdit(disp_curr)
                edit.setEnabled(not has_formula)
                edit.setProperty("disp_unit", disp_unit)
                form.addRow(label_text, edit)
                self._fields[name] = edit

        layout.addLayout(form)
        layout.addStretch()

        # Botão Aplicar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_apply = QPushButton("Aplicar")
        self.btn_apply.setStyleSheet("font-weight: bold; padding: 6px 20px; background-color: #1976D2; color: white; border-radius: 3px;")
        self.btn_apply.clicked.connect(self._on_apply)
        btn_layout.addWidget(self.btn_apply)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _on_apply(self):
        if not self.group:
            return
        data = get_dc_data(self.group)
        if not data:
            return

        attrs = data.get("attributes", {})
        for name, widget in self._fields.items():
            if name in attrs and widget.isEnabled():
                disp_unit = widget.property("disp_unit") or ""
                if isinstance(widget, QComboBox):
                    # Se houver valor associado (userData), usa o valor real aceito; senão, usa currentText
                    c_data = widget.currentData()
                    raw_selected = c_data if c_data is not None else widget.currentText()
                    try:
                        val_num = float(raw_selected)
                        if disp_unit == "cm":
                            val = round(val_num / 100.0, 4)
                        elif disp_unit == "mm":
                            val = round(val_num / 1000.0, 4)
                        elif disp_unit == "in":
                            val = round(val_num * 0.0254, 4)
                        else:
                            val = val_num
                    except (ValueError, TypeError):
                        val = raw_selected
                else:
                    val_str = widget.text()
                    try:
                        val_num = float(val_str)
                        if disp_unit == "cm":
                            val = round(val_num / 100.0, 4)
                        elif disp_unit == "mm":
                            val = round(val_num / 1000.0, 4)
                        elif disp_unit == "in":
                            val = round(val_num * 0.0254, 4)
                        else:
                            val = val_num
                    except ValueError:
                        val = val_str
                attrs[name]["value"] = val

        evaluate_dc(self.group)
        if self.viewport:
            scene = getattr(self.viewport, "scene", None)
            if scene is not None:
                scene.version += 1
            if hasattr(self.viewport, "notify_scene_changed"):
                self.viewport.notify_scene_changed()
            elif hasattr(self.viewport, "update"):
                self.viewport.update()


class AttributeDetailsDialog(QDialog):
    """Janela de detalhes e regras de exibição do atributo (estilo SketchUp Component Attributes)."""

    def __init__(self, group_name: str, attr_key: str, attr_info: dict, parent=None):
        super().__init__(parent)
        self.attr_key = attr_key
        self.attr_info = attr_info
        self.setWindowTitle("Atributos de componente")
        self.resize(440, 520)
        self._setup_ui(group_name)

    def _setup_ui(self, group_name: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Cabeçalho com ícone de caixa/amostra e nome do atributo
        header = QWidget()
        header.setStyleSheet("background-color: palette(midlight); border-bottom: 1px solid palette(mid); border-radius: 2px;")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(8, 8, 8, 8)

        icon_lbl = QLabel("📦")
        icon_font = QFont()
        icon_font.setPointSize(20)
        icon_lbl.setFont(icon_font)
        h_lay.addWidget(icon_lbl)

        title_lbl = QLabel(f"<b>{group_name}!{self.attr_key}</b>")
        title_lbl.setStyleSheet("color: palette(text);")
        h_lay.addWidget(title_lbl)
        h_lay.addStretch()
        layout.addWidget(header)

        # Regra de exibição
        rule_lay = QHBoxLayout()
        rule_lbl = QLabel("Regra de exibição:")
        rule_lbl.setStyleSheet("font-weight: bold; color: palette(text);")
        rule_lay.addWidget(rule_lbl)

        self.cmb_rule = QComboBox()
        self.cmb_rule.addItem("Os usuários não podem ver este atributo.")       # 0: invisível
        self.cmb_rule.addItem("Os usuários podem ver este atributo.")           # 1: somente leitura
        self.cmb_rule.addItem("Os usuários podem editar o texto.")              # 2: caixa de texto editável
        self.cmb_rule.addItem("Os usuários podem selecionar de uma lista.")     # 3: lista suspensa

        # Determina estado atual
        has_options = bool(self.attr_info.get("options"))
        user_editable = bool(self.attr_info.get("user_editable", False))
        user_visible = bool(self.attr_info.get("user_visible", False))

        if has_options:
            self.cmb_rule.setCurrentIndex(3)
        elif user_editable:
            self.cmb_rule.setCurrentIndex(2)
        elif user_visible:
            self.cmb_rule.setCurrentIndex(1)
        else:
            self.cmb_rule.setCurrentIndex(0)

        self.cmb_rule.currentIndexChanged.connect(self._on_rule_changed)
        rule_lay.addWidget(self.cmb_rule)
        layout.addLayout(rule_lay)

        # Rótulo de exibição e Unidades
        self.lbl_row = QWidget()
        lbl_lay = QFormLayout(self.lbl_row)
        lbl_lay.setContentsMargins(0, 4, 0, 4)

        self.edit_label = QLineEdit(str(self.attr_info.get("label", self.attr_key)))
        self.edit_label.setStyleSheet("color: palette(text); background-color: palette(base);")
        lbl_lay.addRow("Rótulo de exibição:", self.edit_label)

        self.cmb_units = QComboBox()
        self.cmb_units.addItem("Padrão do componente", "")
        self.cmb_units.addItem("Metros (m)", "m")
        self.cmb_units.addItem("Centímetros (cm)", "cm")
        self.cmb_units.addItem("Milímetros (mm)", "mm")
        self.cmb_units.addItem('Polegadas (")', "in")
        self.cmb_units.addItem("Graus (°)", "deg")

        curr_unit = str(self.attr_info.get("display_unit", self.attr_info.get("unit", "")))
        for i in range(self.cmb_units.count()):
            if self.cmb_units.itemData(i) == curr_unit:
                self.cmb_units.setCurrentIndex(i)
                break
        lbl_lay.addRow("Unidades:", self.cmb_units)
        layout.addWidget(self.lbl_row)

        # Painel da Lista de Opções (Tabela exatamente como no SketchUp: Rótulo de exibição e Valor real aceito)
        self.list_box = QGroupBox("Opções da Lista (Rótulo de exibição & Valor real aceito)")
        list_vbox = QVBoxLayout(self.list_box)
        list_vbox.setContentsMargins(6, 6, 6, 6)

        self.options_table = QTableWidget()
        self.options_table.setColumnCount(2)
        self.options_table.setHorizontalHeaderLabels(["Opção da lista (Exibição)", "Valor real aceito"])
        self.options_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.options_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.options_table.verticalHeader().setDefaultSectionSize(26)
        self.options_table.setStyleSheet("QTableWidget { background-color: palette(base); color: palette(text); gridline-color: palette(mid); }")

        # Preenche com as opções atuais
        curr_opts = self.attr_info.get("options", [])
        self.options_table.setRowCount(len(curr_opts))
        for r, opt in enumerate(curr_opts):
            if isinstance(opt, dict):
                l_txt = str(opt.get("label", opt.get("value", "")))
                v_txt = str(opt.get("value", ""))
            else:
                l_txt = str(opt)
                v_txt = str(opt)
            it_label = QTableWidgetItem(l_txt)
            it_val = QTableWidgetItem(v_txt)
            self.options_table.setItem(r, 0, it_label)
            self.options_table.setItem(r, 1, it_val)

        list_vbox.addWidget(self.options_table)

        # Botões de Adicionar e Remover linha da tabela
        tbl_btn_lay = QHBoxLayout()
        btn_add_opt = QPushButton("➕ Adicionar Opção")
        btn_add_opt.setStyleSheet("font-size: 11px; padding: 4px 10px;")
        btn_add_opt.clicked.connect(self._add_option_row)

        btn_del_opt = QPushButton("➖ Remover Selecionada")
        btn_del_opt.setStyleSheet("font-size: 11px; padding: 4px 10px;")
        btn_del_opt.clicked.connect(self._remove_option_row)

        tbl_btn_lay.addWidget(btn_add_opt)
        tbl_btn_lay.addWidget(btn_del_opt)
        tbl_btn_lay.addStretch()
        list_vbox.addLayout(tbl_btn_lay)

        layout.addWidget(self.list_box)

        layout.addStretch()

        # Botões Aplicar e Cancelar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_apply = QPushButton("Aplicar")
        btn_apply.setStyleSheet("font-weight: bold; padding: 6px 18px; background-color: #1976D2; color: white; border-radius: 3px;")
        btn_apply.clicked.connect(self._on_apply)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self._on_rule_changed(self.cmb_rule.currentIndex())

    def _add_option_row(self):
        row = self.options_table.rowCount()
        self.options_table.insertRow(row)
        self.options_table.setItem(row, 0, QTableWidgetItem(f"Opção {row + 1}"))
        self.options_table.setItem(row, 1, QTableWidgetItem(f"{row + 1}"))
        self.options_table.setCurrentCell(row, 0)

    def _remove_option_row(self):
        cur_row = self.options_table.currentRow()
        if cur_row >= 0:
            self.options_table.removeRow(cur_row)
        elif self.options_table.rowCount() > 0:
            self.options_table.removeRow(self.options_table.rowCount() - 1)

    def _on_rule_changed(self, index: int):
        # 0: Não podem ver
        # 1: Podem ver (read only)
        # 2: Podem editar o texto
        # 3: Podem selecionar de uma lista
        self.lbl_row.setVisible(index > 0)
        self.list_box.setVisible(index == 3)

    def _on_apply(self):
        idx = self.cmb_rule.currentIndex()
        lbl_txt = self.edit_label.text().strip() or self.attr_key
        self.attr_info["label"] = lbl_txt
        unit_val = self.cmb_units.currentData()
        if unit_val:
            self.attr_info["display_unit"] = unit_val

        if idx == 0:
            self.attr_info["user_editable"] = False
            self.attr_info["user_visible"] = False
            self.attr_info["options"] = []
        elif idx == 1:
            self.attr_info["user_editable"] = False
            self.attr_info["user_visible"] = True
            self.attr_info["options"] = []
        elif idx == 2:
            self.attr_info["user_editable"] = True
            self.attr_info["user_visible"] = True
            self.attr_info["options"] = []
        elif idx == 3:
            self.attr_info["user_editable"] = True
            self.attr_info["user_visible"] = True
            opts = []
            for r in range(self.options_table.rowCount()):
                it_label = self.options_table.item(r, 0)
                it_val = self.options_table.item(r, 1)
                l_str = it_label.text().strip() if it_label else ""
                v_str = it_val.text().strip() if it_val else ""
                if not l_str and not v_str:
                    continue
                # Tenta converter v_str para float ou int se for número
                parsed_val: Any = v_str
                try:
                    if "." in v_str:
                        parsed_val = float(v_str)
                    else:
                        parsed_val = int(v_str)
                except ValueError:
                    parsed_val = v_str
                
                opts.append({
                    "label": l_str or str(parsed_val),
                    "value": parsed_val
                })
            self.attr_info["options"] = opts

        self.accept()


class ComponentAttributesDialog(QDialog):
    """Janela 'Atributos de componente' com 100% de paridade ao SketchUp (não-modal)."""

    def __init__(self, group, viewport=None, parent=None):
        super().__init__(parent)
        self.root_group = group
        self.viewport = viewport
        self.setModal(False)
        self.setWindowTitle("Atributos de componente")
        self.resize(520, 680)
        self._setup_ui()

    def set_group(self, group):
        """Atualiza o grupo raiz exibido sem recriar a janela."""
        self.root_group = group
        grp_name = getattr(group, 'name', 'Componente') if group else 'Componente'
        self.setWindowTitle(f"Atributos de componente - {grp_name}")
        self._populate_tree()
        d = ensure_dc_data(group) if group else {}
        desc = d.get("description", "Sem descrição.")
        self.summary_text.setText(f"<b>{grp_name}</b><br><small>{desc}</small>")

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)

        # Abas superiores: [ Informações ] [ Funções ]
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # 1. Aba Informações (Árvore de componentes com atributos e fórmulas)
        info_tab = QWidget()
        info_layout = QVBoxLayout(info_tab)
        info_layout.setContentsMargins(4, 4, 4, 4)

        # Header do componente selecionado
        self.summary_box = QGroupBox()
        sum_layout = QHBoxLayout(self.summary_box)
        sum_layout.setContentsMargins(8, 4, 8, 4)
        icon_lbl = QLabel("📦")
        font = QFont()
        font.setPointSize(16)
        icon_lbl.setFont(font)
        self.summary_text = QLabel("<b>Atributos</b> &middot; Adicione os atributos abaixo para criar opções de componente.")
        sum_layout.addWidget(icon_lbl)
        sum_layout.addWidget(self.summary_text)
        sum_layout.addStretch()

        # Botão de atualizar / reavaliar
        btn_refresh = QToolButton()
        btn_refresh.setText("🔄")
        btn_refresh.setToolTip("Atualizar e recalcular todas as fórmulas")
        btn_refresh.clicked.connect(self._on_refresh_all)
        sum_layout.addWidget(btn_refresh)
        info_layout.addWidget(self.summary_box)

        # Árvore Principal de Componentes e Atributos
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Componente / Atributo", "Valor / Fórmula"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemSelectionChanged.connect(self._on_item_selected)
        info_layout.addWidget(self.tree)

        # Barra inferior de ações
        action_bar = QHBoxLayout()
        btn_calc = QPushButton("Avaliar Fórmulas")
        btn_calc.clicked.connect(self._on_refresh_all)
        btn_save = QPushButton("Salvar e Aplicar")
        btn_save.setStyleSheet("font-weight: bold; background-color: #2e7d32; color: white; padding: 6px 14px;")
        btn_save.clicked.connect(self._on_save_all)

        action_bar.addWidget(btn_calc)
        action_bar.addStretch()
        action_bar.addWidget(btn_save)
        info_layout.addLayout(action_bar)

        self.tabs.addTab(info_tab, "📋 Informações")

        # 2. Aba Funções (Catálogo de funções matemáticas e lógicas)
        func_tab = self._build_functions_tab()
        self.tabs.addTab(func_tab, "fx Funções")

        self._populate_tree()

    def _build_functions_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        help_table = QTableWidget()
        help_table.setColumnCount(3)
        help_table.setHorizontalHeaderLabels(["Função", "Exemplo", "Descrição"])
        help_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        help_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        help_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

        funcs = [
            ("ANIMATE", 'ANIMATE("RotZ", 0, -90)', "Anima a rotação ou posição entre valores suaves"),
            ("ANIMATESLOW", 'ANIMATESLOW("RotZ", 0, 90)', "Animação lenta"),
            ("ANIMATEFAST", 'ANIMATEFAST("X", 0, 100)', "Animação rápida"),
            ("SET", 'SET("Aberto", 1 - Aberto)', "Altera uma variável no clique"),
            ("ALERT", 'ALERT("Porta aberta!")', "Exibe mensagem na tela"),
            ("IF", '=IF(Aberto=1, 90, 0)', "Condicional SE verdadeiro ENTÃO SENÃO"),
            ("CHOOSE", '=CHOOSE(Cor, "Red", "Green", "Blue")', "Seleciona valor pelo índice"),
            ("CURRENT", '=CURRENT("LenX")', "Valor atual antes do cálculo"),
            ("NEAREST", '=NEAREST(LenX, 60, 70, 80)', "Arredonda para a opção mais próxima"),
            ("ROUND", '=ROUND(LenX * 100)', "Arredonda para número inteiro"),
            ("SIN / COS / TAN", '=SIN(RotZ)', "Funções trigonométricas em graus"),
            ("SQRT", '=SQRT(LenX^2 + LenY^2)', "Raiz quadrada"),
        ]
        help_table.setRowCount(len(funcs))
        for row, (fn, ex, desc) in enumerate(funcs):
            help_table.setItem(row, 0, QTableWidgetItem(fn))
            help_table.setItem(row, 1, QTableWidgetItem(ex))
            help_table.setItem(row, 2, QTableWidgetItem(desc))

        lay.addWidget(help_table)
        return w

    def _collect_all_groups(self, node: Any, res: list) -> None:
        res.append(node)
        for child in getattr(node, "children", []) or []:
            self._collect_all_groups(child, res)

    def _populate_tree(self):
        self.tree.clear()
        self._build_group_node(self.root_group, parent_item=None)
        self.tree.expandAll()

    def _build_group_node(self, group: Any, parent_item: QTreeWidgetItem | None = None):
        data = ensure_dc_data(group)
        grp_name = getattr(group, "name", "Componente")

        item = QTreeWidgetItem(self.tree if parent_item is None else parent_item)
        item.setData(0, Qt.UserRole, ("group", group))

        # Widget personalizado para o nó do grupo (Nome + Botão '+')
        node_widget = QWidget()
        h_lay = QHBoxLayout(node_widget)
        h_lay.setContentsMargins(2, 1, 2, 1)

        name_lbl = QLabel(f"<b>{grp_name}</b>")
        h_lay.addWidget(name_lbl)
        h_lay.addStretch()

        btn_add = QToolButton()
        btn_add.setText("+")
        btn_add.setToolTip("Adicionar atributo a este componente")
        btn_add.setStyleSheet("font-weight: bold; color: #1976D2; padding: 1px 6px; border: 1px solid #90CAF9; border-radius: 3px;")
        btn_add.clicked.connect(lambda _c=None, g=group: self._show_add_menu(btn_add, g))
        h_lay.addWidget(btn_add)

        self.tree.setItemWidget(item, 0, node_widget)

        # Popula os atributos do grupo
        attrs = data.get("attributes", {})
        for attr_key, attr_info in sorted(attrs.items()):
            self._build_attr_row(item, group, attr_key, attr_info)

        # Se houver onClick
        onclick_val = data.get("onClick", "")
        if onclick_val:
            self._build_attr_row(item, group, "onClick", {"value": onclick_val, "formula": onclick_val, "label": "onClick"})

        # Linha 'Adicionar atributo' no final do grupo (estilo SketchUp)
        self._build_add_attr_row(item, group)

        # Recursão para subcomponentes filhos
        for child in getattr(group, "children", []) or []:
            self._build_group_node(child, parent_item=item)

    def _build_add_attr_row(self, group_item: QTreeWidgetItem, group: Any):
        add_item = QTreeWidgetItem(group_item)
        add_item.setData(0, Qt.UserRole, ("add_btn", group))

        col0_w = QWidget()
        c0_lay = QHBoxLayout(col0_w)
        c0_lay.setContentsMargins(18, 0, 2, 0)
        c0_lay.setSpacing(6)

        btn_plus = QToolButton()
        btn_plus.setText("⊕")
        btn_plus.setStyleSheet("color: #1976D2; font-weight: bold; border: none; font-size: 14px;")
        btn_plus.setToolTip("Adicionar atributo")
        c0_lay.addWidget(btn_plus)

        # Campo editável "Digite um nome" exatamente como no SketchUp
        edit_add = QLineEdit()
        edit_add.setPlaceholderText("Digite um nome")
        edit_add.setStyleSheet("border: 1px solid palette(highlight); border-radius: 2px; padding: 1px 4px; color: palette(text); background-color: palette(base);")

        def _on_enter():
            name = edit_add.text().strip()
            if name:
                self._add_attribute(group, name, name, "")
            else:
                self._show_add_menu(edit_add, group)

        edit_add.returnPressed.connect(_on_enter)
        btn_plus.clicked.connect(lambda _c=None, w=edit_add, g=group: self._show_add_menu(w, g))
        edit_add.mousePressEvent = lambda _e, w=edit_add, g=group: (QLineEdit.mousePressEvent(edit_add, _e), self._show_add_menu(w, g))
        c0_lay.addWidget(edit_add)

        self.tree.setItemWidget(add_item, 0, col0_w)

    def _build_attr_row(self, group_item: QTreeWidgetItem, group: Any, attr_key: str, attr_info: dict):
        attr_item = QTreeWidgetItem(group_item)
        attr_item.setData(0, Qt.UserRole, ("attr", group, attr_key))

        # Coluna 0: Nome do Atributo + botão '-' para remover
        col0_w = QWidget()
        c0_lay = QHBoxLayout(col0_w)
        c0_lay.setContentsMargins(18, 0, 2, 0)

        lbl = QLabel(attr_key)
        lbl.setStyleSheet("color: palette(text); font-weight: 500;")
        c0_lay.addWidget(lbl)
        c0_lay.addStretch()

        btn_del = QToolButton()
        btn_del.setText("✕")
        btn_del.setToolTip(f"Remover {attr_key}")
        btn_del.setStyleSheet("color: palette(placeholder-text); border: none; font-size: 11px;")
        btn_del.clicked.connect(lambda _c=None, g=group, k=attr_key: self._remove_attribute(g, k))
        c0_lay.addWidget(btn_del)

        self.tree.setItemWidget(attr_item, 0, col0_w)

        # Coluna 1: Input para valor ou fórmula + botão de detalhes (Regra de Exibição)
        col1_w = QWidget()
        c1_lay = QHBoxLayout(col1_w)
        c1_lay.setContentsMargins(0, 0, 4, 0)
        c1_lay.setSpacing(4)

        formula = str(attr_info.get("formula", "")).strip()
        val = str(attr_info.get("value", ""))
        display_text = formula if formula else val

        val_input = QLineEdit(display_text)
        val_input.setStyleSheet("border: 1px solid palette(mid); border-radius: 2px; padding: 2px 4px; color: palette(text); background-color: palette(base);")
        if formula.startswith("="):
            val_input.setStyleSheet("border: 1px solid #4CAF50; background-color: rgba(76, 175, 80, 0.18); color: palette(text); border-radius: 2px; padding: 2px 4px;")

        val_input.editingFinished.connect(lambda g=group, k=attr_key, w=val_input: self._on_attr_edited(g, k, w.text()))
        c1_lay.addWidget(val_input)

        # Botão de regras de exibição e opções do usuário (estilo SketchUp)
        btn_details = QToolButton()
        has_rule = bool(attr_info.get("options") or attr_info.get("user_editable") or attr_info.get("user_visible"))
        btn_details.setText("🏷️" if has_rule else "»")
        btn_details.setToolTip("Regra de exibição e opções do usuário...")
        btn_details.setStyleSheet("color: #1976D2; font-weight: bold; border: 1px solid palette(mid); border-radius: 2px; padding: 1px 4px;")
        btn_details.clicked.connect(lambda _c=None, g=group, k=attr_key, info=attr_info: self._open_attr_details(g, k, info))
        c1_lay.addWidget(btn_details)

        self.tree.setItemWidget(attr_item, 1, col1_w)

    def _show_add_menu(self, btn: QToolButton, group: Any):
        """Menu Popup categorizado exatamente como no SketchUp."""
        menu = QMenu(self)
        data = ensure_dc_data(group)
        current_attrs = data.get("attributes", {})

        for cat_title, items in DC_ATTRIBUTE_CATEGORIES:
            sub_menu = menu.addMenu(cat_title)
            for attr_id, attr_label, unit in items:
                act = QAction(attr_id, sub_menu)
                act.setStatusTip(f"{attr_label} ({unit})" if unit else attr_label)
                if attr_id in current_attrs or (attr_id == "onClick" and data.get("onClick")):
                    act.setEnabled(False)  # Já adicionado
                act.triggered.connect(lambda _c=None, g=group, k=attr_id, l=attr_label, u=unit: self._add_attribute(g, k, l, u))
                sub_menu.addAction(act)

        menu.addSeparator()
        act_custom = QAction("+ Adicionar Atributo Personalizado...", menu)
        act_custom.triggered.connect(lambda: self._prompt_custom_attribute(group))
        menu.addAction(act_custom)

        menu.exec_(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _add_attribute(self, group: Any, key: str, label: str, unit: str):
        data = ensure_dc_data(group)
        if key == "onClick":
            data["onClick"] = 'ANIMATE("RotZ", 0, -90)'
        else:
            std = STANDARD_ATTRIBUTES.get(key, {})
            val = std.get("value", 0.0 if unit else "")
            data["attributes"][key] = {
                "label": label or key,
                "value": val,
                "formula": "",
                "unit": unit,
                "editable": True,
            }
        evaluate_dc(group)
        self._populate_tree()
        if self.viewport:
            scene = getattr(self.viewport, 'scene', None)
            if scene is not None:
                scene.version += 1
            if hasattr(self.viewport, 'notify_scene_changed'):
                self.viewport.notify_scene_changed()
            elif hasattr(self.viewport, 'update'):
                self.viewport.update()

    def _prompt_custom_attribute(self, group: Any):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Novo Atributo", "Nome do atributo:")
        if ok and name.strip():
            self._add_attribute(group, name.strip(), name.strip(), "")

    def _remove_attribute(self, group: Any, key: str):
        data = ensure_dc_data(group)
        if key == "onClick":
            data["onClick"] = ""
        elif key in data.get("attributes", {}):
            del data["attributes"][key]
        evaluate_dc(group)
        self._populate_tree()
        if self.viewport:
            scene = getattr(self.viewport, 'scene', None)
            if scene is not None:
                scene.version += 1
            if hasattr(self.viewport, 'notify_scene_changed'):
                self.viewport.notify_scene_changed()
            elif hasattr(self.viewport, 'update'):
                self.viewport.update()

    def _open_attr_details(self, group: Any, key: str, info: dict):
        grp_name = getattr(group, "name", "Componente")
        dlg = AttributeDetailsDialog(grp_name, key, info, parent=self)
        if dlg.exec_():
            evaluate_dc(group)
            self._populate_tree()
            if self.viewport:
                scene = getattr(self.viewport, 'scene', None)
                if scene is not None:
                    scene.version += 1
                if hasattr(self.viewport, 'notify_scene_changed'):
                    self.viewport.notify_scene_changed()
                elif hasattr(self.viewport, 'update'):
                    self.viewport.update()

    def _on_attr_edited(self, group: Any, key: str, text: str):
        text = text.strip()
        data = ensure_dc_data(group)
        if key == "onClick":
            data["onClick"] = text
        elif key in data.get("attributes", {}):
            attr = data["attributes"][key]
            if text.startswith("="):
                attr["formula"] = text
            else:
                attr["formula"] = ""
                try:
                    attr["value"] = float(text)
                except ValueError:
                    attr["value"] = text
        evaluate_dc(group)
        if self.viewport:
            scene = getattr(self.viewport, 'scene', None)
            if scene is not None:
                scene.version += 1
            if hasattr(self.viewport, 'notify_scene_changed'):
                self.viewport.notify_scene_changed()
            elif hasattr(self.viewport, 'update'):
                self.viewport.update()

    def _on_item_selected(self):
        item = self.tree.currentItem()
        if not item:
            return
        node_info = item.data(0, Qt.UserRole)
        if not node_info:
            return

        if node_info[0] == "group":
            g = node_info[1]
            d = ensure_dc_data(g)
            name = getattr(g, "name", "Componente")
            desc = d.get("description", "Adicione os atributos abaixo para criar suas opções de componente.")
            self.summary_text.setText(f"<b>{name}</b> &middot; {desc}")
        elif node_info[0] == "attr":
            g, attr_k = node_info[1], node_info[2]
            # Descrições oficiais do SketchUp para os atributos
            attr_descriptions = {
                "LenX": "Tamanho ao longo do eixo vermelho.",
                "LenY": "Tamanho ao longo do eixo verde.",
                "LenZ": "Tamanho ao longo do eixo azul.",
                "X": "Posição ao longo do eixo vermelho.",
                "Y": "Posição ao longo do eixo verde.",
                "Z": "Posição ao longo do eixo azul.",
                "RotX": "Rotação em torno do eixo vermelho.",
                "RotY": "Rotação em torno do eixo verde.",
                "RotZ": "Rotação em torno do eixo azul.",
                "Material": "Como \"Verde\" ou \"#FF0000\".",
                "Copies": "Número de cópias a serem criadas a partir do componente.",
                "Hidden": "1 para ocultar o componente, 0 para mostrá-lo.",
                "onClick": "Comportamento ao clicar na entidade com a ferramenta Interagir.",
                "ScaleTool": "Restringe os eixos da ferramenta Escala."
            }
            d_text = attr_descriptions.get(attr_k, f"Atributo {attr_k} do componente.")
            self.summary_text.setText(f"<b>{attr_k}</b> &middot; {d_text}")

    def _on_refresh_all(self):
        all_groups = []
        self._collect_all_groups(self.root_group, all_groups)
        for g in all_groups:
            evaluate_dc(g)
        self._populate_tree()
        if self.viewport:
            scene = getattr(self.viewport, "scene", None)
            if scene is not None:
                scene.version += 1
            if hasattr(self.viewport, "notify_scene_changed"):
                self.viewport.notify_scene_changed()
            elif hasattr(self.viewport, "update"):
                self.viewport.update()

    def _on_save_all(self):
        self._on_refresh_all()
        QMessageBox.information(self, "Sucesso", "Atributos e fórmulas atualizados e aplicados à cena!")
