# SPDX-License-Identifier: GPL-3.0-or-later
"""Gerenciador visual e ferramenta de inserção e controle de luzes físicas do TrazoMob.

Permite inserir e controlar:
- Spot Embutido (Dicroica / AR70 / PAR20) com mira direcionável e ângulo do facho
- Fita LED de Marcenaria / Perfil Linear (iluminação indireta sob armários)
- Ponto de Luz Difuso / Plafon / Pendente
- Controle de Temperatura de Cor em Kelvin (2200K quente a 6500K frio)
- Potência em Watts
- Liga/Desliga individual (se todas forem apagadas num quarto fechado, o render respeita a escuridão física total)
"""
from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QVector3D,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.render_blender import (
    MAX_KELVIN,
    MIN_KELVIN,
    kelvin_to_rgb,
)

from ..domain.i18n import tr
from ..integrations import platform as host

logger = logging.getLogger("trazomob.light_tools")

_TRAZOMOB_LIGHT_KINDS = ("point", "spot", "led_strip")
_TRAZOMOB_EXTRA_KEYS = ("p1", "p2", "length", "profile_w", "target", "ies_path", "blend", "double_sided")



from .lighting import (
    LIGHT_PRESETS,
    AimLightTool,
    InsertLedStripTool,
    InsertLightTool,
    MoveLightTool,
    _get_document_lights,
    _save_document_lights,
    _translate_light_scene_group,
    wants_shadow,
)


class LightManagerDialog(QDialog):
    """Diálogo visual para gerenciamento completo das luzes físicas da cena."""

    def __init__(self, viewport, parent=None):
        super().__init__(parent)
        self._host_window = host.window_of(window=parent, viewport=viewport)
        self._fallback_viewport = viewport
        self.setWindowTitle("💡 TrazoMob — Gerenciador de Iluminação & Spots Físicos")
        self.setMinimumSize(680, 520)

        self._lights: list[dict] = []
        self._current_index: int = -1

        self._build_ui()
        self._reload_lights()

    @property
    def viewport(self):
        return host.active_viewport(window=self._host_window, viewport=self._fallback_viewport)

    @viewport.setter
    def viewport(self, vp) -> None:
        if vp is not None:
            self._fallback_viewport = vp

    def sync_to_active_document(self, viewport=None) -> None:
        """Recarrega as luzes do documento atualmente ativo ao trocar de aba."""
        if viewport is not None:
            self._fallback_viewport = viewport
            win = host.window_of(viewport=viewport)
            if win is not None:
                self._host_window = win
        self._current_index = -1
        self._reload_lights()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Cabeçalho Explicativo
        lbl_head = QLabel(
            "<b>Controle Físico de Iluminação para Render Foto-Realista (Blender Cycles)</b><br>"
            "<span style='color: palette(text); font-size: 11px;'>"
            "As lâmpadas e spots inseridos iluminam fisicamente o ambiente.<br>"
            "Se todas as luzes forem desligadas e a cena for fechada, o render ficará no escuro real.</span>"
        )
        lbl_head.setWordWrap(True)
        layout.addWidget(lbl_head)

        # Corpo dividido em Lista (esquerda) e Propriedades (direita)
        splitter = QSplitter(Qt.Horizontal)

        # ── ESQUERDA: LISTA DE LUZES E PRESETS ──
        w_left = QWidget()
        l_left = QVBoxLayout(w_left)
        l_left.setContentsMargins(0, 0, 0, 0)
        l_left.setSpacing(8)

        lbl_list = QLabel("<b>Luzes no Projeto:</b>")
        l_left.addWidget(lbl_list)

        self.list_lights = QListWidget()
        self.list_lights.currentRowChanged.connect(self._on_light_selected)
        self.list_lights.itemChanged.connect(self._on_item_checked)
        l_left.addWidget(self.list_lights, 1)

        # Ações de adição rápida
        lbl_add = QLabel("<b>+ Adicionar Nova Luz:</b>")
        l_left.addWidget(lbl_add)

        h_add = QHBoxLayout()
        btn_add_spot = QPushButton("🔦 + Spot / Dicroica")
        btn_add_spot.setToolTip("Adiciona um spot com cone de luz direcionável")
        btn_add_spot.clicked.connect(lambda: self._start_placement("spot_quente"))
        h_add.addWidget(btn_add_spot)

        btn_add_led = QPushButton("✨ + Fita LED")
        btn_add_led.setToolTip("Adiciona iluminação difusa para nichos e sob armários")
        btn_add_led.clicked.connect(lambda: self._start_placement("fita_led"))
        h_add.addWidget(btn_add_led)

        l_left.addLayout(h_add)

        h_add2 = QHBoxLayout()
        btn_add_omni = QPushButton("💡 + Luz Omni")
        btn_add_omni.setToolTip("Lâmpada que ilumina em todas as direções (bulbo, pendente, arandela)")
        btn_add_omni.clicked.connect(lambda: self._start_placement("omni"))
        h_add2.addWidget(btn_add_omni)
        btn_add_plafon = QPushButton("⬜ + Plafon")
        btn_add_plafon.setToolTip("Luz geral difusa de teto, mais forte")
        btn_add_plafon.clicked.connect(lambda: self._start_placement("plafon_geral"))
        h_add2.addWidget(btn_add_plafon)
        l_left.addLayout(h_add2)

        btn_del = QPushButton("🗑️ Excluir Luz Selecionada")
        btn_del.clicked.connect(self._delete_current_light)
        l_left.addWidget(btn_del)

        splitter.addWidget(w_left)

        # ── DIREITA: PROPRIEDADES DA LUZ SELECIONADA ──
        self.w_right = QGroupBox("Propriedades da Luz")
        l_right = QVBoxLayout(self.w_right)
        l_right.setSpacing(10)

        # Nome
        h_name = QHBoxLayout()
        h_name.addWidget(QLabel("Nome / Identificação:"))
        self.txt_name = QPushButton()
        self.txt_name.setEnabled(False)
        h_name.addWidget(self.txt_name, 1)
        l_right.addLayout(h_name)

        # Tipo (Spot vs Difusa)
        h_kind = QHBoxLayout()
        h_kind.addWidget(QLabel("Tipo de Emissão:"))
        self.cb_kind = QComboBox()
        self.cb_kind.addItems([
            "Spot Direcionável (Cone de Foco)",
            "Omni / Ponto (todas as direções)",
            "Fita LED Linear",
        ])
        self.cb_kind.currentIndexChanged.connect(self._on_prop_changed)
        h_kind.addWidget(self.cb_kind, 1)
        l_right.addLayout(h_kind)

        # Potência (Watts)
        h_pwr = QHBoxLayout()
        h_pwr.addWidget(QLabel("Potência:"))
        self.spin_power = QDoubleSpinBox()
        self.spin_power.setRange(10.0, 10000.0)
        self.spin_power.setSingleStep(50.0)
        self.spin_power.setSuffix(" W")
        self.spin_power.valueChanged.connect(self._on_prop_changed)
        h_pwr.addWidget(self.spin_power, 1)
        l_right.addLayout(h_pwr)

        # Temperatura de Cor (Kelvin)
        lbl_k = QLabel("Temperatura de Cor (Kelvin):")
        l_right.addWidget(lbl_k)

        h_k = QHBoxLayout()
        self.slider_kelvin = QSlider(Qt.Horizontal)
        self.slider_kelvin.setRange(MIN_KELVIN, MAX_KELVIN)
        self.slider_kelvin.setSingleStep(100)
        self.spin_kelvin = QSpinBox()
        self.spin_kelvin.setRange(MIN_KELVIN, MAX_KELVIN)
        self.spin_kelvin.setSingleStep(100)
        self.spin_kelvin.setSuffix(" K")

        self.slider_kelvin.valueChanged.connect(self.spin_kelvin.setValue)
        self.spin_kelvin.valueChanged.connect(self.slider_kelvin.setValue)
        self.slider_kelvin.sliderReleased.connect(self._on_prop_changed)
        self.spin_kelvin.editingFinished.connect(self._on_prop_changed)

        h_k.addWidget(self.slider_kelvin, 1)
        h_k.addWidget(self.spin_kelvin)
        l_right.addLayout(h_k)

        self.lbl_kelvin_desc = QLabel("2700K — Amarela Quente Aconchegante")
        self.lbl_kelvin_desc.setStyleSheet("color: palette(mid); font-style: italic;")
        l_right.addWidget(self.lbl_kelvin_desc)

        self.chk_cast_shadow = QCheckBox(tr("Projetar Sombras"))
        self.chk_cast_shadow.setToolTip(
            tr("Desative em fitas LED embutidas no EEVEE se o armário bloquear a luz.")
        )
        self.chk_cast_shadow.setChecked(True)
        self.chk_cast_shadow.toggled.connect(self._on_prop_changed)
        l_right.addWidget(self.chk_cast_shadow)

        # Ângulo de Abertura (para Spots)
        self.w_spot_group = QWidget()
        l_spot = QVBoxLayout(self.w_spot_group)
        l_spot.setContentsMargins(0, 0, 0, 0)
        l_spot.setSpacing(8)

        h_ang = QHBoxLayout()
        h_ang.addWidget(QLabel("Abertura do Facho:"))
        self.spin_angle = QDoubleSpinBox()
        self.spin_angle.setRange(10.0, 120.0)
        self.spin_angle.setSingleStep(5.0)
        self.spin_angle.setSuffix(" °")
        self.spin_angle.valueChanged.connect(self._on_prop_changed)
        h_ang.addWidget(self.spin_angle, 1)
        l_spot.addLayout(h_ang)

        h_bld = QHBoxLayout()
        h_bld.addWidget(QLabel("Suavidade / Falloff:"))
        self.spin_blend = QDoubleSpinBox()
        self.spin_blend.setRange(0.0, 1.0)
        self.spin_blend.setSingleStep(0.05)
        self.spin_blend.setDecimals(2)
        self.spin_blend.setToolTip("Controle de transição do facho: 0.0 = borda nítida/cortada; 1.0 = borda ultra suave e difusa.")
        self.spin_blend.valueChanged.connect(self._on_prop_changed)
        h_bld.addWidget(self.spin_blend, 1)
        l_spot.addLayout(h_bld)

        h_ies = QHBoxLayout()
        self.btn_ies = QPushButton("📂 Carregar Fotometria IES...")
        self.btn_ies.setToolTip("Carrega arquivo .ies real do fabricante (Phillips, Osram, Stella) para facho foto-realista.")
        self.btn_ies.clicked.connect(self._select_ies_file)
        h_ies.addWidget(self.btn_ies, 1)

        self.btn_clear_ies = QPushButton("✕")
        self.btn_clear_ies.setToolTip("Remover curva IES e voltar ao cone padrão")
        self.btn_clear_ies.setFixedWidth(28)
        self.btn_clear_ies.clicked.connect(self._clear_ies_file)
        h_ies.addWidget(self.btn_clear_ies)
        l_spot.addLayout(h_ies)

        self.btn_aim = QPushButton("🎯 Mirar Spot no 3D (Clique onde iluminar)")
        self.btn_aim.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 6px;")
        self.btn_aim.clicked.connect(self._start_aim)
        l_spot.addWidget(self.btn_aim)

        l_right.addWidget(self.w_spot_group)

        # Altura / Elevação (Z)
        h_elev = QHBoxLayout()
        h_elev.addWidget(QLabel("Altura / Elevação (Z):"))
        self.spin_z = QDoubleSpinBox()
        self.spin_z.setRange(-10.0, 50.0)
        self.spin_z.setSingleStep(0.05)
        self.spin_z.setDecimals(2)
        self.spin_z.setSuffix(" m")
        self.spin_z.valueChanged.connect(self._on_prop_changed)
        h_elev.addWidget(self.spin_z, 1)

        btn_elev_up = QPushButton("▲ +10cm")
        btn_elev_up.clicked.connect(lambda: self.spin_z.setValue(self.spin_z.value() + 0.10))
        h_elev.addWidget(btn_elev_up)

        btn_elev_dn = QPushButton("▼ -10cm")
        btn_elev_dn.clicked.connect(lambda: self.spin_z.setValue(self.spin_z.value() - 0.10))
        h_elev.addWidget(btn_elev_dn)

        l_right.addLayout(h_elev)

        # Botão Reposicionar
        self.btn_reposition = QPushButton("📍 Reposicionar Luz no 3D")
        self.btn_reposition.clicked.connect(self._reposition_current_light)
        l_right.addWidget(self.btn_reposition)

        l_right.addStretch()
        splitter.addWidget(self.w_right)

        layout.addWidget(splitter, 1)

        # Rodapé
        h_bot = QHBoxLayout()
        h_bot.addStretch()
        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(self.accept)
        h_bot.addWidget(btn_close)
        layout.addLayout(h_bot)

    def _reload_lights(self):
        """Atualiza a lista visual com os dados das luzes salvas."""
        self._lights = _get_document_lights(self.viewport)
        self.list_lights.blockSignals(True)
        self.list_lights.clear()

        for i, lt in enumerate(self._lights):
            kind = "Spot" if lt.get("kind") == "spot" else "Difusa"
            name = lt.get("name") or f"Luz {i+1} ({kind})"
            power = int(lt.get("power", 400.0))
            k = int(lt.get("kelvin", 2700))
            icon_char = "🔦" if kind == "Spot" else "💡"

            item = QListWidgetItem(f"{icon_char} {name} — {power}W ({k}K)")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if lt.get("on", True) else Qt.Unchecked)
            self.list_lights.addItem(item)

        self.list_lights.blockSignals(False)

        if self._lights:
            sel_idx = min(max(self._current_index, 0), len(self._lights) - 1)
            self.list_lights.setCurrentRow(sel_idx)
        else:
            self._current_index = -1
            self.w_right.setEnabled(False)

    def _on_light_selected(self, row: int):
        self._current_index = row
        if not (0 <= row < len(self._lights)):
            self.w_right.setEnabled(False)
            return

        self.w_right.setEnabled(True)
        lt = self._lights[row]

        kind = lt.get("kind", "spot")
        self.cb_kind.blockSignals(True)
        if kind == "led_strip":
            self.cb_kind.setCurrentIndex(2)
            self.cb_kind.setEnabled(False)
        else:
            self.cb_kind.setCurrentIndex(0 if kind == "spot" else 1)
            self.cb_kind.setEnabled(True)
        self.cb_kind.blockSignals(False)

        self.txt_name.setText(lt.get("name") or f"Luz #{row+1}")

        self.spin_power.blockSignals(True)
        self.spin_power.setValue(float(lt.get("power", 400.0)))
        self.spin_power.blockSignals(False)

        k = int(lt.get("kelvin", 2700))
        self.slider_kelvin.blockSignals(True)
        self.spin_kelvin.blockSignals(True)
        self.slider_kelvin.setValue(k)
        self.spin_kelvin.setValue(k)
        self.slider_kelvin.blockSignals(False)
        self.spin_kelvin.blockSignals(False)
        self._update_kelvin_desc(k)

        self.w_spot_group.setVisible(kind == "spot")
        self.spin_angle.blockSignals(True)
        self.spin_angle.setValue(float(lt.get("angle", 45.0)))
        self.spin_angle.blockSignals(False)

        self.spin_blend.blockSignals(True)
        self.spin_blend.setValue(float(lt.get("blend", 0.35)))
        self.spin_blend.blockSignals(False)

        self.chk_cast_shadow.blockSignals(True)
        self.chk_cast_shadow.setChecked(wants_shadow(lt))
        self.chk_cast_shadow.blockSignals(False)

        ies_cur = lt.get("ies_path")
        if ies_cur:
            from pathlib import Path
            self.btn_ies.setText(f"📄 IES: {Path(ies_cur).name}")
            self.btn_ies.setStyleSheet("font-weight: bold; color: #0284C7;")
        else:
            self.btn_ies.setText("📂 Carregar Fotometria IES...")
            self.btn_ies.setStyleSheet("")

        pos = lt.get("pos") or [0, 0, 0]
        self.spin_z.blockSignals(True)
        self.spin_z.setValue(float(pos[2]))
        self.spin_z.blockSignals(False)

    def _select_ies_file(self):
        row = self._current_index
        if not (0 <= row < len(self._lights)):
            return
        from pathlib import Path

        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Arquivo de Fotometria IES",
            "",
            "Arquivos IES (*.ies);;Todos os Arquivos (*.*)"
        )
        if path:
            self._lights[row]["ies_path"] = path
            self.btn_ies.setText(f"📄 IES: {Path(path).name}")
            self.btn_ies.setStyleSheet("font-weight: bold; color: #0284C7;")
            _save_document_lights(self.viewport, self._lights)

    def _clear_ies_file(self):
        row = self._current_index
        if not (0 <= row < len(self._lights)):
            return
        self._lights[row].pop("ies_path", None)
        self.btn_ies.setText("📂 Carregar Fotometria IES...")
        self.btn_ies.setStyleSheet("")
        _save_document_lights(self.viewport, self._lights)

    def _update_kelvin_desc(self, k: int):
        if k < 2500:
            desc = "Luz de Vela / Fogo (Muito Quente)"
        elif k < 3200:
            desc = "Luz Quente Aconchegante (Ideal para quartos e salas)"
        elif k < 4500:
            desc = "Luz Neutra de Trabalho (Ideal para cozinhas e escritórios)"
        else:
            desc = "Luz Fria / Luz do Dia (LED 6500K)"
        self.lbl_kelvin_desc.setText(f"{k}K — {desc}")

    def _on_item_checked(self, item: QListWidgetItem):
        row = self.list_lights.row(item)
        if 0 <= row < len(self._lights):
            self._lights[row]["on"] = item.checkState() == Qt.Checked
            _save_document_lights(self.viewport, self._lights)

    def _on_prop_changed(self):
        row = self._current_index
        if not (0 <= row < len(self._lights)):
            return

        lt = self._lights[row]
        if lt.get("kind") == "led_strip":
            is_spot = False
        else:
            is_spot = self.cb_kind.currentIndex() == 0
            lt["kind"] = "spot" if is_spot else "point"
        self.w_spot_group.setVisible(is_spot)

        lt["power"] = float(self.spin_power.value())
        k = int(self.spin_kelvin.value())
        lt["kelvin"] = k
        lt["color"] = list(kelvin_to_rgb(k))
        lt["angle"] = float(self.spin_angle.value())
        lt["blend"] = float(self.spin_blend.value())
        lt["cast_shadow"] = bool(self.chk_cast_shadow.isChecked())

        # Atualiza Z e desloca target/fitas de acordo
        new_z = round(float(self.spin_z.value()), 4)
        pos = lt.get("pos") or [0, 0, 0]
        dz = new_z - pos[2]
        pos[2] = new_z
        lt["pos"] = pos

        if lt.get("kind") == "spot" and "target" in lt and lt["target"]:
            lt["target"][2] = round(lt["target"][2] + dz, 4)
        if lt.get("kind") == "led_strip" and "p1" in lt and "p2" in lt:
            lt["p1"][2] = round(lt["p1"][2] + dz, 4)
            lt["p2"][2] = round(lt["p2"][2] + dz, 4)

        self._update_kelvin_desc(k)
        _translate_light_scene_group(self.viewport, row, QVector3D(0.0, 0.0, dz), lt)
        _save_document_lights(self.viewport, self._lights)

        # Atualiza o texto do item da lista
        kind_label = "Spot" if is_spot else "Difusa"
        icon_char = "🔦" if is_spot else "💡"
        name = lt.get("name") or f"Luz {row+1} ({kind_label})"
        self.list_lights.item(row).setText(f"{icon_char} {name} — {int(lt['power'])}W ({k}K)")

    def _start_placement(self, preset_key: str):
        preset = LIGHT_PRESETS.get(preset_key, LIGHT_PRESETS["spot_quente"])
        new_light = dict(preset)
        new_light["color"] = list(kelvin_to_rgb(new_light["kelvin"]))

        self.hide()

        def _on_done(_placed):
            self._reload_lights()
            self.show()

        if preset.get("kind") == "led_strip" or preset_key == "fita_led":
            tool = InsertLedStripTool(new_light, on_placed=_on_done)
        else:
            tool = InsertLightTool(new_light, on_placed=_on_done)
        self.viewport.set_active_tool(tool)


    def _reposition_current_light(self):
        if not (0 <= self._current_index < len(self._lights)):
            return
        self.hide()

        def _on_done():
            self._reload_lights()
            self.show()

        tool = MoveLightTool(self._current_index, on_moved=_on_done)
        self.viewport.set_active_tool(tool)

    def _start_aim(self):
        if not (0 <= self._current_index < len(self._lights)):
            return
        self.hide()

        def _on_aimed():
            self._reload_lights()
            self.show()

        tool = AimLightTool(self._current_index, on_aimed=_on_aimed)
        self.viewport.set_active_tool(tool)

    def _delete_current_light(self):
        if 0 <= self._current_index < len(self._lights):
            del self._lights[self._current_index]
            _save_document_lights(self.viewport, self._lights, undoable=True)
            self._reload_lights()


# ── Mini Popup Flutuante de Edição Rápida da Luz (HUD) ─────────────────────────
class LightQuickPopupHUD(QFrame):
    """Mini painel flutuante de edição rápida ao clicar numa luz no 3D."""

    def __init__(self, viewport, light_index: int, on_changed=None, parent=None):
        super().__init__(parent or viewport)
        self.viewport = viewport
        self.light_index = light_index
        self.on_changed = on_changed
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 35, 235);
                border: 1px solid #0284C7;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 11px;
            }
            QLabel { background: transparent; color: #FFFFFF; }
            QPushButton {
                background-color: #374151;
                border: 1px solid #4B5563;
                border-radius: 4px;
                padding: 4px 8px;
                color: white;
            }
            QPushButton:hover { background-color: #4B5563; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        lights = _get_document_lights(self.viewport)
        if not (0 <= self.light_index < len(lights)):
            self.close()
            return
        lt = lights[self.light_index]

        kind = lt.get("kind", "point")
        kind_label = "Spot Direcionável" if kind == "spot" else ("Fita LED Linear" if kind == "led_strip" else "Luz Ponto/Omni")

        # Cabeçalho
        h_top = QHBoxLayout()
        lbl_title = QLabel(f"<b>💡 {lt.get('name') or kind_label}</b>")
        h_top.addWidget(lbl_title, 1)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(20, 20)
        btn_close.clicked.connect(self.close)
        h_top.addWidget(btn_close)
        layout.addLayout(h_top)

        # Ligar / Desligar
        h_on = QHBoxLayout()
        self.btn_toggle = QPushButton("Desligar Luz" if lt.get("on", True) else "Ligar Luz")
        self.btn_toggle.setStyleSheet("background-color: #059669;" if lt.get("on", True) else "background-color: #6B7280;")
        self.btn_toggle.clicked.connect(self._toggle_on)
        h_on.addWidget(self.btn_toggle, 1)
        layout.addLayout(h_on)

        # Potência
        h_pwr = QHBoxLayout()
        h_pwr.addWidget(QLabel("Potência:"))
        self.sp_pwr = QSpinBox()
        self.sp_pwr.setRange(10, 10000)
        self.sp_pwr.setSingleStep(50)
        self.sp_pwr.setSuffix(" W")
        self.sp_pwr.setValue(int(lt.get("power", 400)))
        self.sp_pwr.valueChanged.connect(self._on_prop_change)
        h_pwr.addWidget(self.sp_pwr, 1)
        layout.addLayout(h_pwr)

        # Kelvin
        h_k = QHBoxLayout()
        h_k.addWidget(QLabel("Kelvin:"))
        self.sl_k = QSlider(Qt.Horizontal)
        self.sl_k.setRange(MIN_KELVIN, MAX_KELVIN)
        self.sl_k.setSingleStep(100)
        self.sl_k.setValue(int(lt.get("kelvin", 2700)))
        self.sl_k.valueChanged.connect(self._on_prop_change)
        h_k.addWidget(self.sl_k, 1)
        self.lbl_k_val = QLabel(f"{int(lt.get('kelvin', 2700))}K")
        h_k.addWidget(self.lbl_k_val)
        layout.addLayout(h_k)

        # Se for spot: botão para mirar ponto focal e ângulo
        if kind == "spot":
            h_ang = QHBoxLayout()
            h_ang.addWidget(QLabel("Ângulo Facho:"))
            self.sp_ang = QSpinBox()
            self.sp_ang.setRange(10, 120)
            self.sp_ang.setSuffix("°")
            self.sp_ang.setValue(int(lt.get("angle", 45)))
            self.sp_ang.valueChanged.connect(self._on_prop_change)
            h_ang.addWidget(self.sp_ang, 1)
            layout.addLayout(h_ang)

            btn_aim = QPushButton("🎯 Mirar no Ponto Focal (3D)")
            btn_aim.setStyleSheet("background-color: #0284C7; font-weight: bold;")
            btn_aim.clicked.connect(self._aim_spot)
            layout.addWidget(btn_aim)

        # Elevação / Altura Z
        pos = lt.get("pos") or [0, 0, 0]
        h_z = QHBoxLayout()
        h_z.addWidget(QLabel("Altura (Z):"))
        self.sp_z = QDoubleSpinBox()
        self.sp_z.setRange(-10.0, 50.0)
        self.sp_z.setSingleStep(0.05)
        self.sp_z.setDecimals(2)
        self.sp_z.setSuffix(" m")
        self.sp_z.setValue(float(pos[2]))
        self.sp_z.valueChanged.connect(self._on_z_change)
        h_z.addWidget(self.sp_z, 1)

        btn_z_up = QPushButton("▲")
        btn_z_up.setToolTip("Subir 10cm (+0.10m)")
        btn_z_up.setFixedWidth(24)
        btn_z_up.clicked.connect(lambda: self.sp_z.setValue(self.sp_z.value() + 0.10))
        h_z.addWidget(btn_z_up)

        btn_z_dn = QPushButton("▼")
        btn_z_dn.setToolTip("Descer 10cm (-0.10m)")
        btn_z_dn.setFixedWidth(24)
        btn_z_dn.clicked.connect(lambda: self.sp_z.setValue(self.sp_z.value() - 0.10))
        h_z.addWidget(btn_z_dn)

        layout.addLayout(h_z)

        # Ações inferiores: Mover e Excluir
        h_bot = QHBoxLayout()
        btn_move = QPushButton("📍 Mover Posição")
        btn_move.setStyleSheet("background-color: #2563EB; font-weight: bold;")
        btn_move.setToolTip("Clique na nova posição/superfície onde deseja fixar esta luz.")
        btn_move.clicked.connect(self._move_light)
        h_bot.addWidget(btn_move)

        btn_del = QPushButton("🗑️ Excluir")
        btn_del.setStyleSheet("background-color: #DC2626;")
        btn_del.clicked.connect(self._delete_light)
        h_bot.addWidget(btn_del)
        layout.addLayout(h_bot)

        self.adjustSize()

    def _move_light(self):
        self.close()
        tool = MoveLightTool(self.light_index, on_moved=self.on_changed)
        self.viewport.set_active_tool(tool)


    def _toggle_on(self):
        lights = _get_document_lights(self.viewport)
        if 0 <= self.light_index < len(lights):
            cur = lights[self.light_index].get("on", True)
            lights[self.light_index]["on"] = not cur
            _save_document_lights(self.viewport, lights)
            self.btn_toggle.setText("Desligar Luz" if not cur else "Ligar Luz")
            self.btn_toggle.setStyleSheet("background-color: #059669;" if not cur else "background-color: #6B7280;")
            if callable(self.on_changed):
                self.on_changed()

    def _on_prop_change(self):
        lights = _get_document_lights(self.viewport)
        if 0 <= self.light_index < len(lights):
            lt = lights[self.light_index]
            lt["power"] = float(self.sp_pwr.value())
            k = int(self.sl_k.value())
            lt["kelvin"] = k
            lt["color"] = list(kelvin_to_rgb(k))
            self.lbl_k_val.setText(f"{k}K")
            if hasattr(self, "sp_ang"):
                lt["angle"] = float(self.sp_ang.value())
            _save_document_lights(self.viewport, lights)
            if callable(self.on_changed):
                self.on_changed()

    def _on_z_change(self):
        lights = _get_document_lights(self.viewport)
        if 0 <= self.light_index < len(lights):
            lt = lights[self.light_index]
            new_z = round(float(self.sp_z.value()), 4)
            pos = lt.get("pos") or [0, 0, 0]
            dz = new_z - pos[2]
            pos[2] = new_z
            lt["pos"] = pos

            # Desloca target se for spot
            if lt.get("kind") == "spot" and "target" in lt and lt["target"]:
                lt["target"][2] = round(lt["target"][2] + dz, 4)

            # Desloca terminais se for fita LED
            if lt.get("kind") == "led_strip" and "p1" in lt and "p2" in lt:
                lt["p1"][2] = round(lt["p1"][2] + dz, 4)
                lt["p2"][2] = round(lt["p2"][2] + dz, 4)

            _translate_light_scene_group(self.viewport, self.light_index, QVector3D(0.0, 0.0, dz), lt)
            _save_document_lights(self.viewport, lights)
            if callable(self.on_changed):
                self.on_changed()

    def _aim_spot(self):
        self.close()
        tool = AimLightTool(self.light_index, on_aimed=self.on_changed)
        self.viewport.set_active_tool(tool)

    def _delete_light(self):
        lights = _get_document_lights(self.viewport)
        if 0 <= self.light_index < len(lights):
            del lights[self.light_index]
            _save_document_lights(self.viewport, lights, undoable=True)
        if callable(self.on_changed):
            self.on_changed()
        self.close()


_LIGHT_OCCLUDER_MASK_CACHE: dict[tuple[Any, ...], Any] = {}
_MAX_LIGHT_OCCLUDER_MASK_CACHE = 8


