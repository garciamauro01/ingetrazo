# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Aplicação do tema e estilos do diálogo TrazoMob."""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QListWidget

from ..ui.styles import get_theme_palette, get_dialog_stylesheet


class ModuleDialogStyleMixin:
    """Aplicação do tema e estilos do diálogo TrazoMob."""

    def _apply_dialog_styles(self):
        """Aplica estilo coeso e adaptável (Dark/Light) garantindo excelente contraste nos combos e inputs."""
        c = get_theme_palette()
        self.setStyleSheet(get_dialog_stylesheet(c))

        bg_input = c["bg_input"]
        border_input = c["border_input"]
        border_focus = c["border_focus"]
        text_main = c["text_main"]
        text_title = c["text_title"]
        text_muted = c["text_muted"]
        bg_list = c["bg_list"]
        bg_card = c["bg_card"]
        border_card = c["border_card"]
        hover_card = c["hover_card"]
        select_card = c["select_card"]
        banner_bg = c["banner_bg"]
        banner_text = c["banner_text"]
        banner_border = c["banner_border"]
        btn_step_bg = c["btn_step_bg"]

        # Título da Categoria
        if hasattr(self, "lbl_cat_title"):
            self.lbl_cat_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {text_title};")

        # Combobox de categoria com destaque
        if hasattr(self, "cb_category"):
            self.cb_category.setStyleSheet(f"""
                QComboBox {{
                    background-color: {bg_input};
                    color: {text_main};
                    border: 1.5px solid {border_input};
                    border-radius: 6px;
                    padding: 5px 10px;
                    font-size: 11px;
                    font-weight: 600;
                    min-width: 190px;
                }}
                QComboBox:hover {{
                    border: 1.5px solid {border_focus};
                }}
                QComboBox::drop-down {{
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 24px;
                    border-left: 1px solid {border_input};
                }}
                QComboBox QAbstractItemView {{
                    background-color: {bg_input};
                    color: {text_main};
                    border: 1.5px solid {border_focus};
                    border-radius: 6px;
                    selection-background-color: #2563EB;
                    selection-color: #FFFFFF;
                    padding: 4px;
                }}
                QComboBox QAbstractItemView::item {{
                    min-height: 26px;
                    padding: 4px 8px;
                    color: {text_main};
                }}
                QComboBox QAbstractItemView::item:selected {{
                    background-color: #2563EB;
                    color: #FFFFFF;
                }}
            """)

        # Banner azul TrazoMob
        if hasattr(self, "banner"):
            self.banner.setStyleSheet(
                f"background-color: {banner_bg}; color: {banner_text}; border: 1px solid {banner_border}; "
                f"border-radius: 6px; padding: 8px 12px; font-size: 12px; font-weight: bold;"
            )

        # Grade / Grid Visual com Miniaturas dos Armários
        if hasattr(self, "list_modules"):
            self.list_modules.setStyleSheet(f"""
                QListWidget {{
                    background-color: {bg_list};
                    border: 1px solid {border_input};
                    border-radius: 8px;
                    padding: 6px;
                }}
                QListWidget::item {{
                    background-color: {bg_card};
                    border: 1px solid {border_card};
                    border-radius: 8px;
                    margin: 4px;
                    padding: 6px;
                    color: {text_main};
                    font-weight: 500;
                    font-size: 11px;
                    text-align: center;
                }}
                QListWidget::item:hover {{
                    background-color: {hover_card};
                    border: 1.5px solid {border_focus};
                    color: {border_focus};
                }}
                QListWidget::item:selected {{
                    background-color: {select_card};
                    border: 2px solid {border_focus};
                    color: #FFFFFF;
                    font-weight: bold;
                }}
            """)

        # Card de Identificação do Módulo
        if hasattr(self, "card_info"):
            self.card_info.setStyleSheet(f"background-color: {bg_card}; border: 1px solid {border_card}; border-radius: 6px; padding: 6px;")
        if hasattr(self, "lbl_selected_title"):
            self.lbl_selected_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {text_title};")
        if hasattr(self, "lbl_module_desc"):
            self.lbl_module_desc.setStyleSheet(f"color: {text_muted}; font-size: 11px;")

        # Botões de ajuste rápido (+/- 50mm) e Botões de Alinhamento
        step_btn_css = f"background-color: {btn_step_bg}; color: {text_main}; border: 1px solid {border_input}; border-radius: 4px; font-weight: bold; font-size: 11px;"
        for btn in getattr(self, "_step_buttons", []):
            btn.setStyleSheet(step_btn_css)
        for btn in getattr(self, "_align_buttons", []):
            btn.setStyleSheet(step_btn_css)
