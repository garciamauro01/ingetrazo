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
    """Janela 'Opções do Componente' (estilo Component Options do SketchUp)."""

    def __init__(self, group, viewport=None, parent=None):
        super().__init__(parent)
        self.group = group
        self.viewport = viewport
        self.setWindowTitle(f"Opções do componente - {getattr(group, 'name', 'Componente')}")
        self.resize(380, 480)
        self._fields: dict[str, QWidget] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        data = ensure_dc_data(self.group)

        # Cabeçalho
        title_box = QGroupBox("Parâmetros do Componente")
        title_layout = QVBoxLayout(title_box)

        name_lbl = QLabel(f"<b>{data.get('name', 'Componente')}</b>")
        title_layout.addWidget(name_lbl)

        desc = data.get("description", "").strip()
        if desc:
            lbl_desc = QLabel(desc)
            lbl_desc.setWordWrap(True)
            title_layout.addWidget(lbl_desc)

        layout.addWidget(title_box)

        # Formulário dinâmico
        form = QFormLayout()
        attrs = data.get("attributes", {})

        for name, info in attrs.items():
            if not info.get("editable", True):
                continue
            has_formula = bool(str(info.get("formula", "")).strip())
            unit = info.get("unit", "")
            label_text = f"{info.get('label', name)} ({unit}):" if unit else f"{info.get('label', name)}:"

            options = info.get("options", [])
            if options:
                cmb = QComboBox()
                for opt in options:
                    cmb.addItem(str(opt))
                curr = str(info.get("value", ""))
                idx = cmb.findText(curr)
                if idx >= 0:
                    cmb.setCurrentIndex(idx)
                cmb.setEnabled(not has_formula)
                form.addRow(label_text, cmb)
                self._fields[name] = cmb
            else:
                edit = QLineEdit(str(info.get("value", "")))
                edit.setEnabled(not has_formula)
                form.addRow(label_text, edit)
                self._fields[name] = edit

        layout.addLayout(form)
        layout.addStretch()

        # Botões de Ação
        btn_layout = QHBoxLayout()
        btn_apply = QPushButton("Aplicar")
        btn_apply.setStyleSheet("font-weight: bold; padding: 6px 16px; background-color: #1976D2; color: white;")
        btn_apply.clicked.connect(self._on_apply)
        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(self.accept)

        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    def _on_apply(self):
        data = get_dc_data(self.group)
        if not data:
            return

        attrs = data.get("attributes", {})
        for name, widget in self._fields.items():
            if name in attrs and widget.isEnabled():
                val_str = widget.currentText() if isinstance(widget, QComboBox) else widget.text()
                try:
                    val = float(val_str)
                except ValueError:
                    val = val_str
                attrs[name]["value"] = val

        evaluate_dc(self.group)
        if self.viewport and hasattr(self.viewport, "update"):
            self.viewport.update()
        QMessageBox.information(self, "Sucesso", "Parâmetros aplicados e geometria recalculada!")


class ComponentAttributesDialog(QDialog):
    """Janela 'Atributos de componente' com 100% de paridade ao SketchUp."""

    def __init__(self, group, viewport=None, parent=None):
        super().__init__(parent)
        self.root_group = group
        self.viewport = viewport
        self.setWindowTitle(f"Atributos de componente - {getattr(group, 'name', 'Componente')}")
        self.resize(520, 680)
        self._setup_ui()

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
        self.summary_text = QLabel("<b>Componente Dinâmico</b><br><small>Clique no (+) para adicionar atributos.</small>")
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

        # Recursão para subcomponentes filhos
        for child in getattr(group, "children", []) or []:
            self._build_group_node(child, parent_item=item)

    def _build_attr_row(self, group_item: QTreeWidgetItem, group: Any, attr_key: str, attr_info: dict):
        attr_item = QTreeWidgetItem(group_item)
        attr_item.setData(0, Qt.UserRole, ("attr", group, attr_key))

        # Coluna 0: Nome do Atributo + botão '-' para remover
        col0_w = QWidget()
        c0_lay = QHBoxLayout(col0_w)
        c0_lay.setContentsMargins(18, 0, 2, 0)

        lbl = QLabel(attr_key)
        lbl.setStyleSheet("color: #37474F; font-weight: 500;")
        c0_lay.addWidget(lbl)
        c0_lay.addStretch()

        btn_del = QToolButton()
        btn_del.setText("✕")
        btn_del.setToolTip(f"Remover {attr_key}")
        btn_del.setStyleSheet("color: #9E9E9E; border: none; font-size: 10px;")
        btn_del.clicked.connect(lambda _c=None, g=group, k=attr_key: self._remove_attribute(g, k))
        c0_lay.addWidget(btn_del)

        self.tree.setItemWidget(attr_item, 0, col0_w)

        # Coluna 1: Input para valor ou fórmula (iniciando com =)
        formula = str(attr_info.get("formula", "")).strip()
        val = str(attr_info.get("value", ""))
        display_text = formula if formula else val

        val_input = QLineEdit(display_text)
        val_input.setStyleSheet("border: 1px solid #B0BEC5; border-radius: 2px; padding: 2px 4px;")
        if formula.startswith("="):
            val_input.setStyleSheet("border: 1px solid #4CAF50; background-color: #F1F8E9; border-radius: 2px; padding: 2px 4px;")

        val_input.editingFinished.connect(lambda g=group, k=attr_key, w=val_input: self._on_attr_edited(g, k, w.text()))
        self.tree.setItemWidget(attr_item, 1, val_input)

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

    def _on_item_selected(self):
        item = self.tree.currentItem()
        if not item:
            return
        node_info = item.data(0, Qt.UserRole)
        if node_info and node_info[0] == "group":
            g = node_info[1]
            d = ensure_dc_data(g)
            name = getattr(g, "name", "Componente")
            desc = d.get("description", "Sem descrição.")
            self.summary_text.setText(f"<b>{name}</b><br><small>{desc}</small>")

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
