# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Gerenciamento centralizado de temas e estilos QSS para o plugin TrazoMob."""
from __future__ import annotations

from typing import Dict
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette


def get_theme_palette() -> Dict[str, str]:
    """Retorna os tokens de cores adaptados ao tema ativo (Dark/Light)."""
    app = QApplication.instance()
    is_dark = True
    if app is not None:
        is_dark = app.palette().color(QPalette.Window).lightness() < 128

    if is_dark:
        return {
            "bg_dialog": "#25272B",
            "bg_box": "#2C2E33",
            "bg_input": "#1C1D20",
            "border_input": "#4B515D",
            "border_focus": "#3B82F6",
            "text_main": "#F1F5F9",
            "text_title": "#FFFFFF",
            "text_muted": "#94A3B8",
            "bg_list": "#1A1C20",
            "bg_card": "#2A2D33",
            "border_card": "#3C404A",
            "hover_card": "#323B4A",
            "select_card": "#1E3A8A",
            "banner_bg": "#162842",
            "banner_text": "#60A5FA",
            "banner_border": "#2563EB",
            "btn_step_bg": "#32363F",
            "tbl_alt": "#212327",
        }
    return {
        "bg_dialog": "#F8FAFC",
        "bg_box": "#FFFFFF",
        "bg_input": "#FFFFFF",
        "border_input": "#CBD5E1",
        "border_focus": "#2563EB",
        "text_main": "#0F172A",
        "text_title": "#0F172A",
        "text_muted": "#475569",
        "bg_list": "#F1F5F9",
        "bg_card": "#FFFFFF",
        "border_card": "#CBD5E1",
        "hover_card": "#F0FDF4",
        "select_card": "#EFF6FF",
        "banner_bg": "#E0F2FE",
        "banner_text": "#0288D1",
        "banner_border": "#BAE6FD",
        "btn_step_bg": "#F1F5F9",
        "tbl_alt": "#F8FAFC",
    }


def get_dialog_stylesheet(c: Dict[str, str]) -> str:
    """Gera a folha de estilo principal para janelas e diálogos do TrazoMob."""
    return f"""
        QDialog {{
            background-color: {c['bg_dialog']};
            color: {c['text_main']};
        }}
        QGroupBox {{
            font-weight: bold;
            font-size: 12px;
            color: {c['text_title']};
            border: 1px solid {c['border_input']};
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 14px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 6px;
            color: {c['text_title']};
        }}
        QComboBox {{
            background-color: {c['bg_input']};
            color: {c['text_main']};
            border: 1.5px solid {c['border_input']};
            border-radius: 6px;
            padding: 5px 10px;
            font-size: 11px;
            min-height: 22px;
        }}
        QComboBox:hover {{
            border: 1.5px solid {c['border_focus']};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 24px;
            border-left: 1px solid {c['border_input']};
        }}
        QComboBox QAbstractItemView {{
            background-color: {c['bg_input']};
            color: {c['text_main']};
            border: 1.5px solid {c['border_focus']};
            border-radius: 6px;
            selection-background-color: #2563EB;
            selection-color: #FFFFFF;
            padding: 4px;
            outline: none;
        }}
        QComboBox QAbstractItemView::item {{
            min-height: 26px;
            padding: 4px 8px;
            border-radius: 4px;
            color: {c['text_main']};
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: #374151;
            color: #FFFFFF;
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: #2563EB;
            color: #FFFFFF;
        }}
        QLineEdit {{
            background-color: {c['bg_input']};
            color: {c['text_main']};
            border: 1.5px solid {c['border_input']};
            border-radius: 6px;
            padding: 5px 8px;
            font-size: 11px;
        }}
        QLineEdit:focus {{
            border: 1.5px solid {c['border_focus']};
        }}
        QSpinBox {{
            background-color: {c['bg_input']};
            color: {c['text_main']};
            border: 1.5px solid {c['border_input']};
            border-radius: 4px;
            padding: 4px 6px;
            font-size: 11px;
        }}
        QSpinBox:focus {{
            border: 1.5px solid {c['border_focus']};
        }}
        QLabel {{
            color: {c['text_main']};
        }}
        QTabWidget::pane {{
            border: 1px solid {c['border_input']};
            border-radius: 6px;
            background-color: {c['bg_box']};
        }}
        QTabBar::tab {{
            background-color: {c['bg_dialog']};
            color: {c['text_muted']};
            padding: 8px 16px;
            font-size: 12px;
            font-weight: bold;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            border: 1px solid {c['border_input']};
            border-bottom: none;
            margin-right: 2px;
        }}
        QTabBar::tab:selected {{
            background-color: {c['bg_box']};
            color: {c['border_focus']};
            border-bottom: 2px solid {c['border_focus']};
        }}
        QTableWidget {{
            background-color: {c['bg_input']};
            color: {c['text_main']};
            gridline-color: {c['border_input']};
            border: 1px solid {c['border_input']};
            border-radius: 6px;
            alternate-background-color: {c['tbl_alt']};
        }}
        QHeaderView::section {{
            background-color: {c['bg_box']};
            color: {c['text_title']};
            font-weight: bold;
            padding: 5px;
            border: 1px solid {c['border_input']};
        }}
    """
