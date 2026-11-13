# SPDX-License-Identifier: GPL-3.0-or-later
"""Very small interface translator.

The default interface is Brazilian Portuguese.  Messages are keyed by stable
identifiers rather than by the Portuguese text, so adding a language is a
matter of adding one dictionary and does not require touching call sites.

The host's own interface has its own translation system; this module only
translates strings owned by Furniture Pro.
"""
from __future__ import annotations

import os
from typing import Any

DEFAULT_LANGUAGE = "pt_BR"

_STRINGS: dict[str, dict[str, str]] = {
    "pt_BR": {
        "app.title": "Ingetrazo Furniture Pro",
        "app.subtitle": "Projetos de móveis planejados, fabricação e orçamento",
        "menu.root": "Furniture Pro",
        "menu.open": "Abrir projeto Furniture Pro…",
        "menu.insert": "Inserir módulo…",
        "menu.parts": "Lista de peças e fabricação…",
        "menu.cut": "Plano de corte…",
        "menu.budget": "Orçamento…",
        "menu.materials": "Gerenciador de materiais…",
        "menu.hardware": "Gerenciador de ferragens…",
        "menu.diagnostics": "Diagnóstico do plugin…",
        "menu.about": "Sobre o Furniture Pro…",
        "panel.title": "Furniture Pro",
        "panel.summary": "Projeto de móveis",
        "panel.no_project": "Nenhum módulo no documento.",
        "button.open": "Abrir editor",
        "button.insert": "Inserir no modelo",
        "button.update": "Atualizar selecionado",
        "button.new": "Novo módulo",
        "button.duplicate": "Duplicar",
        "button.delete": "Excluir",
        "button.save": "Salvar",
        "button.cancel": "Cancelar",
        "button.close": "Fechar",
        "button.export_csv": "Exportar CSV",
        "button.export_pdf": "Exportar PDF",
        "button.export_json": "Exportar JSON",
        "button.calculate": "Calcular",
        "button.optimize": "Gerar plano de corte",
        "tab.project": "Projeto",
        "tab.materials": "Materiais",
        "tab.hardware": "Ferragens",
        "tab.manufacturing": "Fabricação",
        "tab.pricing": "Orçamento",
        "tab.settings": "Configurações",
        "catalog.title": "Biblioteca de módulos",
        "catalog.search": "Pesquisar módulo…",
        "catalog.insert_hint": "Escolha um módulo para editar os parâmetros.",
        "params.title": "Parâmetros do módulo",
        "preview.title": "Prévia esquemática",
        "parts.title": "Lista de peças",
        "parts.scope": "Escopo",
        "parts.all": "Projeto completo",
        "parts.selected": "Módulo selecionado",
        "edge.title": "Fitas de borda",
        "cut.title": "Plano de corte",
        "cut.utilization": "Aproveitamento",
        "cut.boards": "Chapas",
        "cut.no_plan": "Gere o plano de corte para visualizar.",
        "quote.title": "Resumo do orçamento",
        "quote.module": "Módulo",
        "quote.room": "Ambiente",
        "quote.project": "Projeto",
        "materials.name": "Material",
        "materials.thickness": "Espessura (mm)",
        "materials.sheet": "Chapa (mm)",
        "materials.cost": "Custo por chapa",
        "materials.cost_m2": "Custo por m²",
        "materials.grain": "Veio",
        "materials.rotation": "Permite rotação",
        "materials.supplier": "Fornecedor",
        "hardware.category": "Categoria",
        "hardware.name": "Ferragem",
        "hardware.manufacturer": "Fabricante",
        "hardware.reference": "Referência",
        "hardware.unit": "Unidade",
        "hardware.cost": "Custo unitário",
        "hardware.verified": "Especificação verificada",
        "settings.language": "Idioma",
        "settings.currency": "Moeda",
        "settings.units": "Unidade de exibição",
        "settings.data_path": "Pasta de dados do usuário",
        "diagnostics.title": "Diagnóstico",
        "diagnostics.copy": "Copiar relatório",
        "error.title": "Furniture Pro",
        "error.details": "Detalhes técnicos",
        "warning.unpriced": "Há materiais ou ferragens sem preço cadastrado.",
        "warning.unverified": "Há ferragens com especificação não verificada.",
        "status.inserted": "Módulo inserido no modelo.",
        "status.updated": "Módulo reconstruído.",
        "status.deleted": "Módulo excluído.",
        "status.saved": "Dados salvos no documento.",
    },
    "en": {
        "app.title": "Ingetrazo Furniture Pro",
        "app.subtitle": "Custom furniture projects, manufacturing and quoting",
        "menu.root": "Furniture Pro",
        "menu.open": "Open Furniture Pro project…",
        "menu.insert": "Insert module…",
        "menu.parts": "Parts list and manufacturing…",
        "menu.cut": "Cutting plan…",
        "menu.budget": "Quote…",
        "menu.materials": "Material manager…",
        "menu.hardware": "Hardware manager…",
        "menu.diagnostics": "Plugin diagnostics…",
        "menu.about": "About Furniture Pro…",
        "panel.title": "Furniture Pro",
        "panel.summary": "Furniture project",
        "panel.no_project": "No modules in the document.",
        "button.open": "Open editor",
        "button.insert": "Insert into model",
        "button.update": "Update selected",
        "button.new": "New module",
        "button.duplicate": "Duplicate",
        "button.delete": "Delete",
        "button.save": "Save",
        "button.cancel": "Cancel",
        "button.close": "Close",
        "button.export_csv": "Export CSV",
        "button.export_pdf": "Export PDF",
        "button.export_json": "Export JSON",
        "button.calculate": "Calculate",
        "button.optimize": "Generate cutting plan",
        "tab.project": "Project",
        "tab.materials": "Materials",
        "tab.hardware": "Hardware",
        "tab.manufacturing": "Manufacturing",
        "tab.pricing": "Quote",
        "tab.settings": "Settings",
        "catalog.title": "Module library",
        "catalog.search": "Search module…",
        "catalog.insert_hint": "Pick a module to edit its parameters.",
        "params.title": "Module parameters",
        "preview.title": "Schematic preview",
        "parts.title": "Parts list",
        "parts.scope": "Scope",
        "parts.all": "Whole project",
        "parts.selected": "Selected module",
        "edge.title": "Edge banding",
        "cut.title": "Cutting plan",
        "cut.utilization": "Yield",
        "cut.boards": "Boards",
        "cut.no_plan": "Generate the cutting plan to view it.",
        "quote.title": "Quote summary",
        "quote.module": "Module",
        "quote.room": "Room",
        "quote.project": "Project",
        "materials.name": "Material",
        "materials.thickness": "Thickness (mm)",
        "materials.sheet": "Sheet (mm)",
        "materials.cost": "Cost per sheet",
        "materials.cost_m2": "Cost per m²",
        "materials.grain": "Grain",
        "materials.rotation": "Allows rotation",
        "materials.supplier": "Supplier",
        "hardware.category": "Category",
        "hardware.name": "Hardware",
        "hardware.manufacturer": "Manufacturer",
        "hardware.reference": "Reference",
        "hardware.unit": "Unit",
        "hardware.cost": "Unit cost",
        "hardware.verified": "Verified specification",
        "settings.language": "Language",
        "settings.currency": "Currency",
        "settings.units": "Display unit",
        "settings.data_path": "User data folder",
        "diagnostics.title": "Diagnostics",
        "diagnostics.copy": "Copy report",
        "error.title": "Furniture Pro",
        "error.details": "Technical details",
        "warning.unpriced": "Some materials or hardware have no price set.",
        "warning.unverified": "Some hardware specifications are unverified.",
        "status.inserted": "Module inserted into the model.",
        "status.updated": "Module rebuilt.",
        "status.deleted": "Module deleted.",
        "status.saved": "Data saved in the document.",
    },
}

_current = os.environ.get("FURNITURE_PRO_LANG", DEFAULT_LANGUAGE)
if _current not in _STRINGS:
    _current = DEFAULT_LANGUAGE


def set_language(language: str) -> None:
    """Set the interface language for strings translated after this call."""
    global _current
    _current = language if language in _STRINGS else DEFAULT_LANGUAGE


def current_language() -> str:
    return _current


def available_languages() -> list[str]:
    return sorted(_STRINGS)


def tr(key: str, **kwargs: Any) -> str:
    """Translate ``key``; unknown keys fall back to Portuguese then the key."""
    table = _STRINGS.get(_current, {})
    text = table.get(key) or _STRINGS[DEFAULT_LANGUAGE].get(key) or key
    try:
        return text.format(**kwargs)
    except (KeyError, IndexError):
        return text
