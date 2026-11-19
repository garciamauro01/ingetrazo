# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Montagem da aba Puxadores e Perfis da barra lateral."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
)

from ..domain.i18n import tr
from ..profiles import library as perfis_lib
from ..profiles.editor import fill_profile_combo, PerfilLibraryDialog
from ..ui.icons import make_perfil_diagram_pixmap


class SidebarPuxadoresMixin:
    """Cria as secoes de puxadores e o card de perfil de aluminio."""

    def _build_puxadores_section(self) -> None:
        """Monta as secoes de puxadores e perfis."""
        # --- Puxadores (Portas e Gavetas) ---

        self.cb_puxador_tipo = QComboBox()
        self.cb_puxador_tipo.addItems([
            tr("Puxador Alça (Linear)"),
            tr("Puxador Perfil (Alumínio)"),
            tr("Puxador Cava (Chanfro 45°)"),
            tr("Puxador Ponto (Botão)"),
            tr("Sem Puxador (Toque)"),
        ])
        self.lbl_puxador_tipo = QLabel(tr("Modelo:"))
        self.sec_puxadores.form_layout.addRow(self.lbl_puxador_tipo, self.cb_puxador_tipo)

        self.cb_puxador_cor = QComboBox()
        self.cb_puxador_cor.addItems([
            tr("Preto Fosco"),
            tr("Alumínio / Inox"),
            tr("Dourado / Champanhe"),
            tr("Cobre / Rosé"),
            tr("Branco"),
        ])
        self.lbl_puxador_cor = QLabel(tr("Acabamento:"))
        self.sec_puxadores.form_layout.addRow(self.lbl_puxador_cor, self.cb_puxador_cor)

        self.cb_puxador_pos = QComboBox()
        self.cb_puxador_pos.addItems([
            tr("📌 Automático / Padrão"),
            tr("⬆️ Na Parte de Cima (Topo)"),
            tr("↕️ Na Extensão da Porta (Lateral)"),
            tr("⬇️ Na Parte de Baixo (Base)"),
            tr("🎯 No Centro"),
        ])
        self.lbl_puxador_pos = QLabel(tr("Posição:"))
        self.sec_puxadores.form_layout.addRow(self.lbl_puxador_pos, self.cb_puxador_pos)

        # Presets Rápidos de Frentes e Puxadores (1 Clique)
        lbl_presets_frentes = QLabel(f"<b>{tr('Presets Rápidos de Estilo:')}</b>")
        self.sec_puxadores.form_layout.addRow(lbl_presets_frentes)

        h_presets_row1 = QHBoxLayout()
        h_presets_row1.setSpacing(4)
        btn_preset_alca = QPushButton(tr("Alça"))
        btn_preset_alca.setToolTip(tr("Preset Alça: Puxador linear moderno com alinhamento padrão"))
        btn_preset_alca.setStyleSheet("font-size: 10px; font-weight: bold; padding: 4px;")
        btn_preset_alca.clicked.connect(lambda: self._apply_front_preset("alca"))
        h_presets_row1.addWidget(btn_preset_alca)

        btn_preset_gola = QPushButton(tr("Perfil Gola"))
        btn_preset_gola.setToolTip(tr("Preset Perfil Gola: Puxador perfil em alumínio embutido no topo/topo de gaveta"))
        btn_preset_gola.setStyleSheet("font-size: 10px; font-weight: bold; padding: 4px;")
        btn_preset_gola.clicked.connect(lambda: self._apply_front_preset("perfil_gola"))
        h_presets_row1.addWidget(btn_preset_gola)
        self.sec_puxadores.form_layout.addRow(h_presets_row1)

        h_presets_row2 = QHBoxLayout()
        h_presets_row2.setSpacing(4)
        btn_preset_cava = QPushButton(tr("Cava 45°"))
        btn_preset_cava.setToolTip(tr("Preset Cava: Bordo chanfrado em 45 graus usinado na chapa (clean)"))
        btn_preset_cava.setStyleSheet("font-size: 10px; font-weight: bold; padding: 4px;")
        btn_preset_cava.clicked.connect(lambda: self._apply_front_preset("cava_45"))
        h_presets_row2.addWidget(btn_preset_cava)

        btn_preset_toque = QPushButton(tr("Tip-On / Toque"))
        btn_preset_toque.setToolTip(tr("Preset Toque: Sem puxador aparente com pistão pulsador/fecho-toque"))
        btn_preset_toque.setStyleSheet("font-size: 10px; font-weight: bold; padding: 4px;")
        btn_preset_toque.clicked.connect(lambda: self._apply_front_preset("toque"))
        h_presets_row2.addWidget(btn_preset_toque)
        self.sec_puxadores.form_layout.addRow(h_presets_row2)

        # Botão para troca de puxadores em lote em todos os armários do ambiente
        self.btn_aplicar_puxador_todos = QPushButton(tr("🔄 Aplicar Puxadores em Todo o Projeto"))
        self.btn_aplicar_puxador_todos.setToolTip(tr("Aplica o modelo, acabamento e posição de puxadores selecionados a todos os armários da cena"))
        self.btn_aplicar_puxador_todos.setStyleSheet(
            "QPushButton { background-color: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 4px; padding: 5px; font-weight: bold; color: #334155; }"
            "QPushButton:hover { background-color: #E2E8F0; color: #0F172A; border-color: #94A3B8; }"
        )
        self.btn_aplicar_puxador_todos.clicked.connect(self._on_apply_puxadores_to_all_modules)
        self.sec_puxadores.form_layout.addRow(self.btn_aplicar_puxador_todos)

        # --- Puxador Perfil de Alumínio (container transparente alinhado às demais abas) ---
        self.frame_perfil = QFrame()
        self.frame_perfil.setFrameShape(QFrame.NoFrame)
        self.frame_perfil.setStyleSheet("QFrame { background: transparent; border: none; }")
        layout_perfil = QFormLayout(self.frame_perfil)
        layout_perfil.setContentsMargins(0, 0, 0, 0)
        layout_perfil.setSpacing(6)

        # Atributo mantido oculto por compatibilidade sem renderizar caixa preta
        self.lbl_perfil_diagram = QLabel(self.frame_perfil)
        self.lbl_perfil_diagram.setVisible(False)

        h_mod_row = QHBoxLayout()
        h_mod_row.setSpacing(4)
        self.cb_perfil_modelo = QComboBox()
        h_mod_row.addWidget(self.cb_perfil_modelo, stretch=1)

        self.btn_gerenciar_perfis = QPushButton(tr("⚙️ Perfis…"))
        self.btn_gerenciar_perfis.setToolTip(tr("Abrir editor de perfis (seções 2D personalizadas, medidas e extrusão)"))
        self.btn_gerenciar_perfis.clicked.connect(self._open_perfis_manager)
        h_mod_row.addWidget(self.btn_gerenciar_perfis)
        layout_perfil.addRow(tr("Modelo Perfil:"), h_mod_row)

        self.cb_altura_perfil = QComboBox()
        self.cb_altura_perfil.addItems([
            tr("Padrão do perfil"),
            "35 MM",
            "40 MM",
            "38 MM",
            "32 MM",
            "30 MM",
            "25 MM",
            "22 MM",
        ])
        layout_perfil.addRow(tr("Desconto Perfil:"), self.cb_altura_perfil)

        self.sp_desconto_perfil = QSpinBox(self.frame_perfil)
        self.sp_desconto_perfil.setRange(15, 60)
        self.sp_desconto_perfil.setValue(35)
        self.sp_desconto_perfil.setVisible(False)

        self._refresh_perfil_modelos()
        self.cb_perfil_modelo.currentIndexChanged.connect(self._on_perfil_modelo_changed)
        self.cb_altura_perfil.currentTextChanged.connect(self._sync_desconto_perfil_from_combo)

        self.sec_puxadores.form_layout.addRow(self.frame_perfil)

        def _update_perfil_card_visibility(idx):
            is_perfil = (idx == 1)
            self.frame_perfil.setVisible(is_perfil)

        self.cb_puxador_tipo.currentIndexChanged.connect(_update_perfil_card_visibility)
        _update_perfil_card_visibility(self.cb_puxador_tipo.currentIndex())



    def _refresh_perfil_modelos(self, select_id: str | None = None) -> None:
        """Recarrega os modelos de perfil da biblioteca para o combobox."""
        fill_profile_combo(self.cb_perfil_modelo, select_id=select_id)
        self._on_perfil_modelo_changed()


    def _on_perfil_modelo_changed(self) -> None:
        """Atualiza o desconto padrão conforme o modelo de perfil selecionado."""
        pid = self.cb_perfil_modelo.currentData() or "gola"
        p = perfis_lib.get_profile(pid)
        if getattr(self, "lbl_perfil_diagram", None) is not None and self.lbl_perfil_diagram.isVisible():
            if pid in ("gola", "facetato", "canal_c", "sp7000"):
                self.lbl_perfil_diagram.setPixmap(make_perfil_diagram_pixmap(115, 80, modelo=pid))
            else:
                self.lbl_perfil_diagram.setPixmap(perfis_lib.render_profile_pixmap(p, 115, 80, cotas=True))

        desc = float(p.get("desconto_mm", 35.0))
        if hasattr(self, "cb_altura_perfil") and self.cb_altura_perfil.currentIndex() == 0:
            if hasattr(self, "sp_desconto_perfil"):
                self.sp_desconto_perfil.setValue(int(round(desc)))


    def _open_perfis_manager(self) -> None:
        """Abre o diálogo de gerenciamento/cadastro de perfis 2D com medidas e extrusão."""
        cur_id = self.cb_perfil_modelo.currentData()
        dlg = PerfilLibraryDialog(parent=self._get_window(), select_id=cur_id)
        if dlg.exec():
            selected = dlg.selected_id or cur_id
            self._refresh_perfil_modelos(select_id=selected)


    def _apply_front_preset(self, preset_name: str) -> None:
        """Aplica presets prontos de puxador e modelo de frente (Alça, Perfil Gola, Cava 45° ou Tip-on/Toque)."""
        if preset_name == "alca":
            self.cb_puxador_tipo.setCurrentIndex(0)  # Puxador Alça
            self.cb_puxador_pos.setCurrentIndex(0)   # Automático
        elif preset_name == "perfil_gola":
            self.cb_puxador_tipo.setCurrentIndex(1)  # Puxador Perfil
            if hasattr(self, "cb_perfil_modelo"):
                idx_g = self.cb_perfil_modelo.findText("Gola", Qt.MatchContains)
                if idx_g >= 0:
                    self.cb_perfil_modelo.setCurrentIndex(idx_g)
            self.cb_puxador_pos.setCurrentIndex(1)   # Topo
        elif preset_name == "cava_45":
            self.cb_puxador_tipo.setCurrentIndex(2)  # Puxador Cava 45
            self.cb_puxador_pos.setCurrentIndex(1)   # Topo
        elif preset_name == "toque":
            self.cb_puxador_tipo.setCurrentIndex(4)  # Sem Puxador (Toque)
        self._apply_changes_to_selected()
        self.lbl_status.setText(tr("✨ Preset de frentes '{preset_name}' aplicado com sucesso!", preset_name=preset_name))


    def _sync_desconto_perfil_from_combo(self, text: str) -> None:
        try:
            val = int(text.split()[0])
            self.sp_desconto_perfil.setValue(val)
        except (ValueError, IndexError):
            self.sp_desconto_perfil.setValue(35)


# Aliases
SidebarHandlesMixin = SidebarPuxadoresMixin

