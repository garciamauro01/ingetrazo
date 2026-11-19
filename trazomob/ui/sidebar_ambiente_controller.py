# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Controlador e Widget de Gerenciamento de Pavimentos & Ambientes para a Sidebar do TrazoMob."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QFrame,
    QInputDialog,
    QDoubleSpinBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
)

from core.group import Group
from ..domain.ambiente import (
    AmbienteBuilder,
    iter_ambientes,
    iter_pavimentos,
    set_ambiente_visivel,
    set_pavimento_visivel,
    is_ambiente,
    is_pavimento,
)
from ..domain.schema import update_ambiente_data, update_pavimento_data, ambiente_params, pavimento_params


class SidebarAmbienteController(QWidget):
    """Card retrátil na Sidebar para visualização, isolamento e visibilidade de pavimentos e cômodos."""

    def __init__(self, sidebar_panel: Any, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.sidebar_panel = sidebar_panel
        self._updating_tree = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Frame container
        self.container = QFrame(self)
        self.container.setStyleSheet(
            "QFrame { background-color: palette(base); border: 1px solid palette(mid); border-radius: 4px; padding: 4px; }"
        )
        l_box = QVBoxLayout(self.container)
        l_box.setContentsMargins(6, 6, 6, 6)
        l_box.setSpacing(4)

        # Cabeçalho do Card
        h_header = QHBoxLayout()
        self.btn_toggle = QPushButton("▼ 🏢 Pavimentos & Ambientes")
        self.btn_toggle.setStyleSheet(
            "QPushButton { font-weight: bold; font-size: 11px; text-align: left; border: none; background: transparent; color: palette(text); }"
            "QPushButton:hover { color: palette(highlight); }"
        )
        self.btn_toggle.clicked.connect(self._toggle_collapse)
        h_header.addWidget(self.btn_toggle, stretch=1)

        self.btn_add_pav = QPushButton("+ Pavimento")
        self.btn_add_pav.setToolTip("Adicionar um novo pavimento (ex: 1º Andar)")
        self.btn_add_pav.setStyleSheet("QPushButton { font-size: 10px; padding: 2px 6px; }")
        self.btn_add_pav.clicked.connect(self._on_add_pavimento)
        h_header.addWidget(self.btn_add_pav)

        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setToolTip("Atualizar lista de pavimentos e ambientes da cena")
        self.btn_refresh.setStyleSheet("QPushButton { font-size: 10px; padding: 2px 5px; }")
        self.btn_refresh.clicked.connect(self.refresh_tree)
        h_header.addWidget(self.btn_refresh)

        l_box.addLayout(h_header)

        # Conteúdo colapsável
        self.content_widget = QWidget(self.container)
        l_content = QVBoxLayout(self.content_widget)
        l_content.setContentsMargins(0, 2, 0, 0)
        l_content.setSpacing(4)

        # Árvore de Pavimentos e Ambientes
        self.tree = QTreeWidget(self.content_widget)
        self.tree.setHeaderHidden(True)
        self.tree.setStyleSheet(
            "QTreeWidget { border: 1px solid palette(midlight); border-radius: 3px; font-size: 11px; }"
            "QTreeWidget::item { padding: 3px 0; }"
        )
        self.tree.itemChanged.connect(self._on_item_changed)
        l_content.addWidget(self.tree)

        # Barra inferior com botões rápidos
        h_bottom = QHBoxLayout()
        h_bottom.setSpacing(4)

        self.btn_unhide_all = QPushButton("👁️ Mostrar Todos")
        self.btn_unhide_all.setToolTip("Torna todos os pavimentos e ambientes visíveis")
        self.btn_unhide_all.setStyleSheet("QPushButton { font-size: 10px; padding: 3px; }")
        self.btn_unhide_all.clicked.connect(self._on_show_all)
        h_bottom.addWidget(self.btn_unhide_all)

        l_content.addLayout(h_bottom)
        l_box.addWidget(self.content_widget)
        layout.addWidget(self.container)

    def _toggle_collapse(self) -> None:
        is_visible = self.content_widget.isVisible()
        self.content_widget.setVisible(not is_visible)
        arrow = "▶" if is_visible else "▼"
        self.btn_toggle.setText(f"{arrow} 🏢 Pavimentos & Ambientes")

    def _get_scene(self) -> Any:
        return self.sidebar_panel._get_scene()

    def _get_viewport(self) -> Any:
        return self.sidebar_panel._get_viewport()

    def refresh_tree(self) -> None:
        """Varre a cena e atualiza a árvore hierárquica."""
        scene = self._get_scene()
        if scene is None:
            return

        self._updating_tree = True
        self.tree.clear()

        groups = getattr(scene, "groups", [])
        pavimentos = list(iter_pavimentos(groups))
        ambientes_soltos = []

        # Coleta todos os ambientes
        all_ambientes = list(iter_ambientes(groups))

        # Associa cada ambiente ao seu pavimento se estiver contido
        amb_in_pav = set()
        pav_by_name = {}
        for pav in pavimentos:
            p_params = pavimento_params(pav)
            p_nome = p_params.get("nome", getattr(pav, "name", "Pavimento"))
            p_visivel = p_params.get("visivel", True)
            z_base = p_params.get("z_base", 0.0)

            item_pav = QTreeWidgetItem(self.tree)
            item_pav.setText(0, f"🏢 {p_nome} (Z: {z_base:.2f}m)")
            item_pav.setFlags(item_pav.flags() | Qt.ItemIsUserCheckable)
            item_pav.setCheckState(0, Qt.Checked if p_visivel else Qt.Unchecked)
            item_pav.setData(0, Qt.UserRole, pav)
            item_pav.setExpanded(True)
            pav_by_name[p_nome] = item_pav

            for amb in getattr(pav, "children", None) or []:
                if is_ambiente(amb):
                    amb_in_pav.add(id(amb))
                    self._add_ambiente_item(item_pav, amb)

        # Também detecta pavimentos e ambientes definidos nas paredes/módulos
        # garantindo que o que foi criado pela Planta 2D apareça na árvore
        for g in groups:
            ext = getattr(g, "ext", {})
            if not isinstance(ext, dict):
                continue
            p_nome = (ext.get("pavimento") or ext.get("trazomob_wall", {}).get("pavimento") or "").strip()
            a_nome = (ext.get("ambiente") or ext.get("trazomob_wall", {}).get("ambiente") or "").strip()
            if p_nome and p_nome not in pav_by_name:
                z_deduzido = 0.0
                if "1" in p_nome and "andar" in p_nome.lower():
                    z_deduzido = 2.80
                elif "2" in p_nome and "andar" in p_nome.lower():
                    z_deduzido = 5.60
                elif "subsolo" in p_nome.lower():
                    z_deduzido = -2.80

                # Cria o nó do pavimento na árvore
                item_pav = QTreeWidgetItem(self.tree)
                item_pav.setText(0, f"🏢 {p_nome} (Z: {z_deduzido:.2f}m)")
                item_pav.setFlags(item_pav.flags() | Qt.ItemIsUserCheckable)
                item_pav.setCheckState(0, Qt.Checked)
                item_pav.setData(0, Qt.UserRole, {"nome_pavimento": p_nome})
                item_pav.setExpanded(True)
                pav_by_name[p_nome] = item_pav

        # Se houver ambientes definidos nas paredes/módulos que não são nós de ambiente formal:
        ambientes_nomes_por_pav = {}
        for g in groups:
            ext = getattr(g, "ext", {})
            if not isinstance(ext, dict):
                continue
            p_nome = (ext.get("pavimento") or ext.get("trazomob_wall", {}).get("pavimento") or "Térreo").strip()
            a_nome = (ext.get("ambiente") or ext.get("trazomob_wall", {}).get("ambiente") or "").strip()
            if a_nome:
                ambientes_nomes_por_pav.setdefault(p_nome, set()).add(a_nome)

        # Adiciona ambientes identificados aos seus respectivos pavimentos na árvore
        for p_nome, item_pav in pav_by_name.items():
            ambs_existentes_no_item = {item_pav.child(i).text(0) for i in range(item_pav.childCount())}
            for a_nome in sorted(ambientes_nomes_por_pav.get(p_nome, [])):
                if not any(a_nome.lower() in t.lower() for t in ambs_existentes_no_item):
                    item_sub = QTreeWidgetItem(item_pav)
                    item_sub.setText(0, f"🚪 {a_nome}")
                    item_sub.setFlags(item_sub.flags() | Qt.ItemIsUserCheckable)
                    item_sub.setCheckState(0, Qt.Checked)
                    item_sub.setData(0, Qt.UserRole, {"nome_ambiente": a_nome, "nome_pavimento": p_nome})

                    btn_iso = QPushButton("🔍 Isolar")
                    btn_iso.setStyleSheet("QPushButton { font-size: 9px; padding: 1px 4px; border-radius: 2px; }")
                    btn_iso.clicked.connect(lambda _, an=a_nome, pn=p_nome: self._on_isolate_by_name(an, pn))
                    self.tree.setItemWidget(item_sub, 1, btn_iso)

        # Ambientes fora de pavimentos formais
        for amb in all_ambientes:
            if id(amb) not in amb_in_pav:
                ambientes_soltos.append(amb)

        if ambientes_soltos:
            item_root = QTreeWidgetItem(self.tree)
            item_root.setText(0, "📍 Outros Ambientes")
            item_root.setFlags(item_root.flags() | Qt.ItemIsUserCheckable)
            item_root.setCheckState(0, Qt.Checked)
            item_root.setData(0, Qt.UserRole, None)
            item_root.setExpanded(True)
            for amb in ambientes_soltos:
                self._add_ambiente_item(item_root, amb)

        self._updating_tree = False

    def _add_ambiente_item(self, parent_item: QTreeWidgetItem, amb: Group) -> None:
        params = ambiente_params(amb)
        nome = params.get("nome", getattr(amb, "name", "Ambiente"))
        visivel = params.get("visivel", True)
        area = params.get("area_m2", 0.0)

        label = f"🛋️ {nome}" if "sala" in nome.lower() else (
            f"🍳 {nome}" if "coz" in nome.lower() else (
                f"🛏️ {nome}" if "quarto" in nome.lower() or "dorm" in nome.lower() else (
                    f"🚿 {nome}" if "banh" in nome.lower() else f"🚪 {nome}"
                )
            )
        )
        if area > 0:
            label += f" ({area:.1f} m²)"

        item_amb = QTreeWidgetItem(parent_item)
        item_amb.setText(0, label)
        item_amb.setFlags(item_amb.flags() | Qt.ItemIsUserCheckable)
        item_amb.setCheckState(0, Qt.Checked if visivel else Qt.Unchecked)
        item_amb.setData(0, Qt.UserRole, amb)

        # Widget de ação "Isolar"
        btn_isolate = QPushButton("🔍 Isolar")
        btn_isolate.setStyleSheet(
            "QPushButton { font-size: 9px; padding: 1px 4px; background: palette(button); border: 1px solid palette(mid); border-radius: 2px; }"
            "QPushButton:hover { background: palette(highlight); color: palette(highlighted-text); }"
        )
        btn_isolate.setToolTip(f"Oculta todos os outros e exibe apenas {nome}")
        btn_isolate.clicked.connect(lambda _, a=amb: self._on_isolate_ambiente(a))
        self.tree.setItemWidget(item_amb, 1, btn_isolate)

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._updating_tree or column != 0:
            return

        is_checked = item.checkState(0) == Qt.Checked
        target_obj = item.data(0, Qt.UserRole)

        if target_obj is None:
            return

        if isinstance(target_obj, dict):
            # Objeto de pavimento ou ambiente deduzido
            scene = self._get_scene()
            if scene is not None:
                p_filter = target_obj.get("nome_pavimento")
                a_filter = target_obj.get("nome_ambiente")
                for g in getattr(scene, "groups", []):
                    ext = getattr(g, "ext", {})
                    if not isinstance(ext, dict):
                        continue
                    gp = (ext.get("pavimento") or ext.get("trazomob_wall", {}).get("pavimento") or "Térreo").strip()
                    ga = (ext.get("ambiente") or ext.get("trazomob_wall", {}).get("ambiente") or "").strip()
                    if a_filter:
                        if gp == p_filter and ga == a_filter:
                            if hasattr(g, "hidden"):
                                g.hidden = not is_checked
                            g.layer = "Ambientes" if is_checked else "Hidden"
                    elif p_filter:
                        if gp == p_filter:
                            if hasattr(g, "hidden"):
                                g.hidden = not is_checked
                            g.layer = "Ambientes" if is_checked else "Hidden"

            # Propaga check visual para os filhos se for pavimento
            if "nome_pavimento" in target_obj and "nome_ambiente" not in target_obj:
                self._updating_tree = True
                for i in range(item.childCount()):
                    item.child(i).setCheckState(0, Qt.Checked if is_checked else Qt.Unchecked)
                self._updating_tree = False

            vp = self._get_viewport()
            if vp is not None:
                vp.update()
            return

        if is_pavimento(target_obj):
            set_pavimento_visivel(target_obj, is_checked)
            # Propaga check visual para os filhos na árvore
            self._updating_tree = True
            for i in range(item.childCount()):
                item.child(i).setCheckState(0, Qt.Checked if is_checked else Qt.Unchecked)
            self._updating_tree = False
        elif is_ambiente(target_obj):
            set_ambiente_visivel(target_obj, is_checked)

        vp = self._get_viewport()
        if vp is not None:
            vp.update()

    def _on_isolate_by_name(self, target_amb: str, target_pav: str) -> None:
        """Isola paredes e módulos pelo nome do ambiente e pavimento."""
        scene = self._get_scene()
        if scene is None:
            return
        for g in getattr(scene, "groups", []):
            ext = getattr(g, "ext", {})
            if not isinstance(ext, dict):
                continue
            gp = (ext.get("pavimento") or ext.get("trazomob_wall", {}).get("pavimento") or "Térreo").strip()
            ga = (ext.get("ambiente") or ext.get("trazomob_wall", {}).get("ambiente") or "").strip()
            # Deixa visível apenas se coincidir
            match = (gp == target_pav and ga == target_amb)
            if hasattr(g, "hidden"):
                g.hidden = not match
            g.layer = "Ambientes" if match else "Hidden"
        vp = self._get_viewport()
        if vp is not None:
            if hasattr(vp, "flash_status"):
                vp.flash_status(f"Ambiente '{target_amb}' isolado.")
            vp.update()

    def _on_isolate_ambiente(self, target_ambiente: Group) -> None:
        """Oculta todos os outros ambientes e pavimentos, mantendo apenas o selecionado visível."""
        scene = self._get_scene()
        if scene is None:
            return

        groups = getattr(scene, "groups", [])
        for amb in iter_ambientes(groups):
            set_ambiente_visivel(amb, amb is target_ambiente)

        vp = self._get_viewport()
        if vp is not None:
            if hasattr(vp, "flash_status"):
                params = ambiente_params(target_ambiente)
                vp.flash_status(f"Ambiente isolado: {params.get('nome', target_ambiente.name)}")
            vp.update()

        self.refresh_tree()

    def _on_show_all(self) -> None:
        """Exibe todos os pavimentos e ambientes."""
        scene = self._get_scene()
        if scene is None:
            return

        groups = getattr(scene, "groups", [])
        for pav in iter_pavimentos(groups):
            set_pavimento_visivel(pav, True)
        for amb in iter_ambientes(groups):
            set_ambiente_visivel(amb, True)

        vp = self._get_viewport()
        if vp is not None:
            if hasattr(vp, "flash_status"):
                vp.flash_status("Todos os ambientes visíveis.")
            vp.update()

        self.refresh_tree()

    def _on_add_pavimento(self) -> None:
        """Abre diálogo para criar um novo pavimento com sugestão inteligente de nome e elevação."""
        scene = self._get_scene()
        groups = getattr(scene, "groups", []) if scene is not None else []
        existentes = [p for p in iter_pavimentos(groups)]
        nomes_existentes = [pavimento_params(p).get("nome", getattr(p, "name", "")).strip() for p in existentes]

        # Sugestão inteligente: se não tem Térreo, sugere Térreo (Z=0.0)
        # Se já tem Térreo, sugere 1º Andar (Z=2.80), 2º Andar (Z=5.60), etc.
        if "Térreo" not in nomes_existentes:
            sugestao_nome = "Térreo"
            sugestao_z = 0.00
        elif "1º Andar" not in nomes_existentes:
            sugestao_nome = "1º Andar"
            sugestao_z = 2.80
        elif "2º Andar" not in nomes_existentes:
            sugestao_nome = "2º Andar"
            sugestao_z = 5.60
        else:
            n_idx = len(nomes_existentes)
            sugestao_nome = f"{n_idx}º Andar"
            sugestao_z = round(n_idx * 2.80, 2)

        from core.units import bare_number_scale, model_precision, model_unit
        scale = bare_number_scale()
        p = model_precision()
        u_name = model_unit().name

        dlg = QDialog(self)
        dlg.setWindowTitle("Novo Pavimento")
        layout = QVBoxLayout(dlg)

        form = QFormLayout()
        txt_nome = QLineEdit(dlg)
        txt_nome.setText(sugestao_nome)
        form.addRow("Nome do Pavimento:", txt_nome)

        sp_z = QDoubleSpinBox(dlg)
        sp_z.setRange(-500000.0, 500000.0)
        sp_z.setDecimals(p)
        sp_z.setValue(round(sugestao_z / scale, p))
        sp_z.setSingleStep(100.0 if scale <= 0.001 else 0.10)
        sp_z.setSuffix(f" {u_name}")
        form.addRow(f"Elevação Base (Z em {u_name}):", sp_z)

        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dlg)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)

        if dlg.exec() == QDialog.Accepted:
            nome = txt_nome.text().strip() or "Pavimento"
            z_base = float(sp_z.value()) * scale
            if scene is not None:
                pav = AmbienteBuilder.ensure_pavimento(scene.groups, nome, z_base=z_base)
                if pav not in scene.groups:
                    scene.groups.append(pav)
                vp = self._get_viewport()
                if vp is not None:
                    if hasattr(vp, "flash_status"):
                        vp.flash_status(f"Pavimento '{nome}' criado (Z={z_base:.2f}m).")
                    vp.update()
                self.refresh_tree()

