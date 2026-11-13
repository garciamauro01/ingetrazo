# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors and Pair Programmer.
"""Diálogo e painel de configuração rápida para a Porta Paramétrica."""
from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from .builder import DOOR_FINISHES


class DoorConfigWidget(QWidget):
    """Widget de formulário para ajustar dimensões, acabamento e abertura da porta."""

    config_changed = Signal(dict)

    def __init__(self, current_config: dict[str, Any] | None = None, parent=None) -> None:
        super().__init__(parent)
        self._cfg = {
            "width": 0.80,
            "height": 2.10,
            "wall_thickness": 0.15,
            "auto_detect_wall": True,
            "open_angle_deg": 60.0,
            "hinge_side": "left",
            "open_inward": True,
            "has_alizar": True,
            "finish_name": "Madeira Carvalho",
        }
        if current_config:
            self._cfg.update(current_config)

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # 1. Dimensões do Vão
        gb_dim = QGroupBox("Dimensões do Vão Arquitetônico")
        f_dim = QFormLayout(gb_dim)
        f_dim.setLabelAlignment(Qt.AlignRight)

        # Botões rápidos para larguras padrão de portas (60, 70, 80, 90, 100 cm)
        w_presets = QHBoxLayout()
        for w_val in [0.60, 0.70, 0.80, 0.90, 1.00]:
            btn = QPushButton(f"{int(w_val*100)}cm")
            btn.setMaximumWidth(48)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.clicked.connect(lambda _c=False, v=w_val: self._spin_w.setValue(v))
            w_presets.addWidget(btn)
        f_dim.addRow("Padrões:", w_presets)

        self._spin_w = QDoubleSpinBox()
        self._spin_w.setRange(0.40, 3.00)
        self._spin_w.setSingleStep(0.05)
        self._spin_w.setDecimals(2)
        self._spin_w.setSuffix(" m")
        self._spin_w.setValue(self._cfg["width"])
        self._spin_w.valueChanged.connect(self._on_field_changed)
        f_dim.addRow("Largura do Vão:", self._spin_w)

        self._spin_h = QDoubleSpinBox()
        self._spin_h.setRange(1.20, 4.00)
        self._spin_h.setSingleStep(0.05)
        self._spin_h.setDecimals(2)
        self._spin_h.setSuffix(" m")
        self._spin_h.setValue(self._cfg["height"])
        self._spin_h.valueChanged.connect(self._on_field_changed)
        f_dim.addRow("Altura da Porta:", self._spin_h)

        self._spin_wall = QDoubleSpinBox()
        self._spin_wall.setRange(0.05, 1.50)
        self._spin_wall.setSingleStep(0.01)
        self._spin_wall.setDecimals(2)
        self._spin_wall.setSuffix(" m")
        self._spin_wall.setValue(self._cfg["wall_thickness"])
        self._spin_wall.valueChanged.connect(self._on_field_changed)
        f_dim.addRow("Espessura Parede:", self._spin_wall)

        self._chk_auto_wall = QCheckBox("Detectar espessura da parede automaticamente")
        self._chk_auto_wall.setChecked(self._cfg["auto_detect_wall"])
        self._chk_auto_wall.toggled.connect(self._on_field_changed)
        f_dim.addRow("", self._chk_auto_wall)

        layout.addWidget(gb_dim)

        # 2. Sentido e Ângulo de Abertura
        gb_open = QGroupBox("Abertura e Dobradiças")
        f_open = QFormLayout(gb_open)

        self._cb_hinge = QComboBox()
        self._cb_hinge.addItem("Esquerda (Abre p/ Esquerda)", "left")
        self._cb_hinge.addItem("Direita (Abre p/ Direita)", "right")
        idx_hinge = 0 if self._cfg["hinge_side"] == "left" else 1
        self._cb_hinge.setCurrentIndex(idx_hinge)
        self._cb_hinge.currentIndexChanged.connect(self._on_field_changed)
        f_open.addRow("Lado da Dobradiça:", self._cb_hinge)

        self._chk_inward = QCheckBox("Abrir para o interior da parede / cômodo")
        self._chk_inward.setChecked(self._cfg["open_inward"])
        self._chk_inward.toggled.connect(self._on_field_changed)
        f_open.addRow("", self._chk_inward)

        slider_box = QHBoxLayout()
        self._slider_angle = QSlider(Qt.Horizontal)
        self._slider_angle.setRange(0, 120)
        self._slider_angle.setValue(int(self._cfg["open_angle_deg"]))
        self._lbl_angle = QLabel(f"{int(self._cfg['open_angle_deg'])}°")
        self._lbl_angle.setMinimumWidth(32)
        self._slider_angle.valueChanged.connect(lambda v: self._lbl_angle.setText(f"{v}°"))
        self._slider_angle.valueChanged.connect(self._on_field_changed)
        slider_box.addWidget(self._slider_angle)
        slider_box.addWidget(self._lbl_angle)
        f_open.addRow("Ângulo de Abertura:", slider_box)

        # Botões rápidos de ângulo (0° Fechada, 45°, 90°, 120°)
        ang_presets = QHBoxLayout()
        for ang_val in [0, 45, 90, 120]:
            btn_a = QPushButton(f"{ang_val}°")
            btn_a.setMaximumWidth(42)
            btn_a.setFocusPolicy(Qt.NoFocus)
            btn_a.clicked.connect(lambda _c=False, a=ang_val: self._slider_angle.setValue(a))
            ang_presets.addWidget(btn_a)
        f_open.addRow("", ang_presets)

        layout.addWidget(gb_open)

        # 3. Acabamento e Guarnições
        gb_style = QGroupBox("Estilo e Acabamento")
        f_style = QFormLayout(gb_style)

        self._cb_finish = QComboBox()
        for fname in DOOR_FINISHES.keys():
            self._cb_finish.addItem(fname, fname)
        idx_f = self._cb_finish.findData(self._cfg["finish_name"])
        if idx_f >= 0:
            self._cb_finish.setCurrentIndex(idx_f)
        self._cb_finish.currentIndexChanged.connect(self._on_field_changed)
        f_style.addRow("Acabamento:", self._cb_finish)

        self._chk_alizar = QCheckBox("Incluir guarnições / alisares (moldura nos 2 lados)")
        self._chk_alizar.setChecked(self._cfg["has_alizar"])
        self._chk_alizar.toggled.connect(self._on_field_changed)
        f_style.addRow("", self._chk_alizar)

        layout.addWidget(gb_style)

        # Dica de uso interativo
        lbl_hint = QLabel("💡 <b>Como usar:</b> Passe o mouse sobre a face de uma parede para ver a porta acompanhando em tempo real. Clique na parede para cortá-la e posicionar a porta!")
        lbl_hint.setWordWrap(True)
        lbl_hint.setStyleSheet("color: #778899; font-size: 11px; padding: 4px; background: rgba(0,0,0,0.03); border-radius: 4px;")
        layout.addWidget(lbl_hint)

        layout.addStretch()

    def _on_field_changed(self) -> None:
        self._cfg["width"] = float(self._spin_w.value())
        self._cfg["height"] = float(self._spin_h.value())
        self._cfg["wall_thickness"] = float(self._spin_wall.value())
        self._cfg["auto_detect_wall"] = self._chk_auto_wall.isChecked()
        self._cfg["hinge_side"] = self._cb_hinge.currentData()
        self._cfg["open_inward"] = self._chk_inward.isChecked()
        self._cfg["open_angle_deg"] = float(self._slider_angle.value())
        self._cfg["finish_name"] = self._cb_finish.currentData()
        self._cfg["has_alizar"] = self._chk_alizar.isChecked()

        self.config_changed.emit(dict(self._cfg))

    def get_config(self) -> dict[str, Any]:
        return dict(self._cfg)

    def set_config(self, cfg: dict[str, Any]) -> None:
        self._cfg.update(cfg)
        self._spin_w.setValue(self._cfg["width"])
        self._spin_h.setValue(self._cfg["height"])
        self._spin_wall.setValue(self._cfg["wall_thickness"])
        self._chk_auto_wall.setChecked(self._cfg["auto_detect_wall"])
        self._cb_hinge.setCurrentIndex(0 if self._cfg["hinge_side"] == "left" else 1)
        self._chk_inward.setChecked(self._cfg["open_inward"])
        self._slider_angle.setValue(int(self._cfg["open_angle_deg"]))
        idx_f = self._cb_finish.findData(self._cfg["finish_name"])
        if idx_f >= 0:
            self._cb_finish.setCurrentIndex(idx_f)
        self._chk_alizar.setChecked(self._cfg["has_alizar"])


class DoorConfigDialog(QDialog):
    """Diálogo modal/não-modal para configurar ou editar a porta paramétrica."""

    def __init__(
        self,
        current_config: dict[str, Any],
        on_apply: Callable[[dict[str, Any]], None],
        title: str = "Gerador de Portas Parametrizável",
        apply_text: str = "Aplicar e Inserir Porta",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(380, 520)

        self._on_apply = on_apply
        self.widget = DoorConfigWidget(current_config, self)

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.widget)

        btn_box = QHBoxLayout()
        btn_apply = QPushButton(apply_text)
        btn_apply.setStyleSheet("background-color: #f37329; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        btn_apply.clicked.connect(self._do_apply)

        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(self.accept)

        btn_box.addWidget(btn_close)
        btn_box.addWidget(btn_apply)
        vbox.addLayout(btn_box)

    def _do_apply(self) -> None:
        cfg = self.widget.get_config()
        self._on_apply(cfg)
        self.accept()


# ==============================================================================
# CONFIGURAÇÃO DE JANELA PARAMÉTRICA
# ==============================================================================

class WindowConfigWidget(QWidget):
    """Widget de formulário para ajustar dimensões, peitoril, acabamento e abertura da janela."""

    config_changed = Signal(dict)

    def __init__(self, current_config: dict[str, Any] | None = None, parent=None) -> None:
        super().__init__(parent)
        from .builder import WINDOW_FINISHES
        self._cfg = {
            "width": 1.20,
            "height": 1.20,
            "sill_height": 1.00,
            "wall_thickness": 0.15,
            "auto_detect_wall": True,
            "window_type": "sliding",
            "open_pct": 0.0,
            "has_sill": True,
            "finish_name": "Alumínio Preto",
        }
        if current_config:
            self._cfg.update(current_config)

        self._setup_ui()

    def _setup_ui(self) -> None:
        from .builder import WINDOW_FINISHES
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # 1. Dimensões do Vão
        gb_dim = QGroupBox("Dimensões do Vão da Janela")
        f_dim = QFormLayout(gb_dim)
        f_dim.setLabelAlignment(Qt.AlignRight)

        # Botões rápidos de largura de janela (1.00, 1.20, 1.50, 1.80, 2.00m)
        w_presets = QHBoxLayout()
        for w_val in [1.00, 1.20, 1.50, 1.80, 2.00]:
            btn = QPushButton(f"{w_val:.2f}m")
            btn.setMaximumWidth(46)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.clicked.connect(lambda _c=False, v=w_val: self._spin_w.setValue(v))
            w_presets.addWidget(btn)
        f_dim.addRow("Padrões:", w_presets)

        self._spin_w = QDoubleSpinBox()
        self._spin_w.setRange(0.40, 5.00)
        self._spin_w.setSingleStep(0.10)
        self._spin_w.setDecimals(2)
        self._spin_w.setSuffix(" m")
        self._spin_w.setValue(self._cfg["width"])
        self._spin_w.valueChanged.connect(self._on_field_changed)
        f_dim.addRow("Largura do Vão:", self._spin_w)

        self._spin_h = QDoubleSpinBox()
        self._spin_h.setRange(0.30, 3.00)
        self._spin_h.setSingleStep(0.10)
        self._spin_h.setDecimals(2)
        self._spin_h.setSuffix(" m")
        self._spin_h.setValue(self._cfg["height"])
        self._spin_h.valueChanged.connect(self._on_field_changed)
        f_dim.addRow("Altura da Janela:", self._spin_h)

        self._spin_sill = QDoubleSpinBox()
        self._spin_sill.setRange(0.00, 2.50)
        self._spin_sill.setSingleStep(0.05)
        self._spin_sill.setDecimals(2)
        self._spin_sill.setSuffix(" m")
        self._spin_sill.setValue(self._cfg["sill_height"])
        self._spin_sill.valueChanged.connect(self._on_field_changed)
        f_dim.addRow("Altura do Peitoril:", self._spin_sill)

        # Botões rápidos de peitoril (0.80, 0.90, 1.00, 1.10m e 1.60m banheiro)
        sill_presets = QHBoxLayout()
        for s_val, s_lbl in [(0.90, "0.90m"), (1.00, "1.00m"), (1.10, "1.10m"), (1.60, "1.60m (BWC)")]:
            btn_s = QPushButton(s_lbl)
            btn_s.setFocusPolicy(Qt.NoFocus)
            btn_s.clicked.connect(lambda _c=False, v=s_val: self._spin_sill.setValue(v))
            sill_presets.addWidget(btn_s)
        f_dim.addRow("", sill_presets)

        self._spin_wall = QDoubleSpinBox()
        self._spin_wall.setRange(0.05, 1.50)
        self._spin_wall.setSingleStep(0.01)
        self._spin_wall.setDecimals(2)
        self._spin_wall.setSuffix(" m")
        self._spin_wall.setValue(self._cfg["wall_thickness"])
        self._spin_wall.valueChanged.connect(self._on_field_changed)
        f_dim.addRow("Espessura Parede:", self._spin_wall)

        self._chk_auto_wall = QCheckBox("Detectar espessura da parede automaticamente")
        self._chk_auto_wall.setChecked(self._cfg["auto_detect_wall"])
        self._chk_auto_wall.toggled.connect(self._on_field_changed)
        f_dim.addRow("", self._chk_auto_wall)

        layout.addWidget(gb_dim)

        # 2. Tipologia e Abertura
        gb_open = QGroupBox("Tipologia e Abertura")
        f_open = QFormLayout(gb_open)

        self._cb_type = QComboBox()
        self._cb_type.addItem("Janela de Correr (2 Folhas)", "sliding")
        self._cb_type.addItem("Janela de Abrir (2 Folhas)", "casement")
        self._cb_type.addItem("Painel de Vidro Fixo", "fixed")
        idx_t = self._cb_type.findData(self._cfg["window_type"])
        if idx_t >= 0:
            self._cb_type.setCurrentIndex(idx_t)
        self._cb_type.currentIndexChanged.connect(self._on_field_changed)
        f_open.addRow("Tipo de Janela:", self._cb_type)

        slider_box = QHBoxLayout()
        self._slider_pct = QSlider(Qt.Horizontal)
        self._slider_pct.setRange(0, 100)
        self._slider_pct.setValue(int(self._cfg["open_pct"]))
        self._lbl_pct = QLabel(f"{int(self._cfg['open_pct'])}%")
        self._lbl_pct.setMinimumWidth(36)
        self._slider_pct.valueChanged.connect(lambda v: self._lbl_pct.setText(f"{v}%"))
        self._slider_pct.valueChanged.connect(self._on_field_changed)
        slider_box.addWidget(self._slider_pct)
        slider_box.addWidget(self._lbl_pct)
        f_open.addRow("Abertura da Folha:", slider_box)

        # Botões rápidos de abertura (Fechada 0%, 50%, 100%)
        ang_presets = QHBoxLayout()
        for pct_val, plbl in [(0, "0% (Fechada)"), (50, "50%"), (100, "100% (Aberta)")]:
            btn_p = QPushButton(plbl)
            btn_p.setFocusPolicy(Qt.NoFocus)
            btn_p.clicked.connect(lambda _c=False, p=pct_val: self._slider_pct.setValue(p))
            ang_presets.addWidget(btn_p)
        f_open.addRow("", ang_presets)

        layout.addWidget(gb_open)

        # 3. Acabamento e Peitoril
        gb_style = QGroupBox("Materiais e Peitoril")
        f_style = QFormLayout(gb_style)

        self._cb_finish = QComboBox()
        for fname in WINDOW_FINISHES.keys():
            self._cb_finish.addItem(fname, fname)
        idx_f = self._cb_finish.findData(self._cfg["finish_name"])
        if idx_f >= 0:
            self._cb_finish.setCurrentIndex(idx_f)
        self._cb_finish.currentIndexChanged.connect(self._on_field_changed)
        f_style.addRow("Acabamento Caixilho:", self._cb_finish)

        self._chk_sill = QCheckBox("Incluir peitoril / pingadeira de proteção")
        self._chk_sill.setChecked(self._cfg["has_sill"])
        self._chk_sill.toggled.connect(self._on_field_changed)
        f_style.addRow("", self._chk_sill)

        layout.addWidget(gb_style)

        lbl_hint = QLabel("💡 <b>Como usar:</b> Aponte o cursor na face de uma parede sólida. A janela se alinha e abre o vão automaticamente respeitando a altura do peitoril!")
        lbl_hint.setWordWrap(True)
        lbl_hint.setStyleSheet("color: #778899; font-size: 11px; padding: 4px; background: rgba(0,0,0,0.03); border-radius: 4px;")
        layout.addWidget(lbl_hint)

        layout.addStretch()

    def _on_field_changed(self) -> None:
        self._cfg["width"] = float(self._spin_w.value())
        self._cfg["height"] = float(self._spin_h.value())
        self._cfg["sill_height"] = float(self._spin_sill.value())
        self._cfg["wall_thickness"] = float(self._spin_wall.value())
        self._cfg["auto_detect_wall"] = self._chk_auto_wall.isChecked()
        self._cfg["window_type"] = self._cb_type.currentData()
        self._cfg["open_pct"] = float(self._slider_pct.value())
        self._cfg["finish_name"] = self._cb_finish.currentData()
        self._cfg["has_sill"] = self._chk_sill.isChecked()

        self.config_changed.emit(dict(self._cfg))

    def get_config(self) -> dict[str, Any]:
        return dict(self._cfg)

    def set_config(self, cfg: dict[str, Any]) -> None:
        self._cfg.update(cfg)
        self._spin_w.setValue(self._cfg["width"])
        self._spin_h.setValue(self._cfg["height"])
        self._spin_sill.setValue(self._cfg["sill_height"])
        self._spin_wall.setValue(self._cfg["wall_thickness"])
        self._chk_auto_wall.setChecked(self._cfg["auto_detect_wall"])
        idx_t = self._cb_type.findData(self._cfg["window_type"])
        if idx_t >= 0:
            self._cb_type.setCurrentIndex(idx_t)
        self._slider_pct.setValue(int(self._cfg["open_pct"]))
        idx_f = self._cb_finish.findData(self._cfg["finish_name"])
        if idx_f >= 0:
            self._cb_finish.setCurrentIndex(idx_f)
        self._chk_sill.setChecked(self._cfg["has_sill"])


class WindowConfigDialog(QDialog):
    """Diálogo modal/não-modal para configurar ou editar a janela paramétrica."""

    def __init__(
        self,
        current_config: dict[str, Any],
        on_apply: Callable[[dict[str, Any]], None],
        title: str = "Gerador de Janelas Parametrizável",
        apply_text: str = "Aplicar e Inserir Janela",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(380, 560)

        self._on_apply = on_apply
        self.widget = WindowConfigWidget(current_config, self)

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.widget)

        btn_box = QHBoxLayout()
        btn_apply = QPushButton(apply_text)
        btn_apply.setStyleSheet("background-color: #2b78e4; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        btn_apply.clicked.connect(self._do_apply)

        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(self.accept)

        btn_box.addWidget(btn_close)
        btn_box.addWidget(btn_apply)
        vbox.addLayout(btn_box)

    def _do_apply(self) -> None:
        cfg = self.widget.get_config()
        self._on_apply(cfg)
        self.accept()

