# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared constants and defaults for Furniture Pro.

All business calculations are done in millimetres.  The geometry adapter is
the only place that converts to Ingetrazo's metre-based model coordinates.
"""
from __future__ import annotations

PLUGIN_NAME = "Ingetrazo Furniture Pro"
PLUGIN_KEY = "furniture_pro"
PLUGIN_VERSION = "1.0.0-mvp"
SCHEMA_VERSION = 1

MM = 0.001
M2 = 1.0

#: Prefix used for material identities created in the host material registry.
MATERIAL_PREFIX = "FP - "

#: Module types implemented by the parametric catalogue.
MODULE_TYPES = (
    "armario_inferior",
    "armario_superior",
    "torre",
    "guarda_roupa",
    "closet",
    "gaveteiro",
    "balcao",
    "nicho",
    "prateleira",
    "painel",
    "porta_abrir",
    "porta_correr",
    "personalizado",
    "bancada",
)

MODULE_LABELS = {
    "armario_inferior": "Armário inferior",
    "armario_superior": "Armário superior",
    "torre": "Torre / coluna",
    "guarda_roupa": "Guarda-roupa",
    "closet": "Closet",
    "gaveteiro": "Gaveteiro",
    "balcao": "Balcão",
    "nicho": "Nicho",
    "prateleira": "Prateleira",
    "painel": "Painel / divisória",
    "porta_abrir": "Porta de abrir",
    "porta_correr": "Porta de correr",
    "personalizado": "Módulo personalizado",
    "bancada": "Bancada",
}

CARCASS_METHODS = {
    "laterais_passantes": "Laterais passantes",
    "tampo_base_passantes": "Tampo e base passantes",
    "montagem_oculta": "Montagem oculta (mesma geometria externa)",
    "personalizado": "Personalizado (regras do usuário)",
}

TOP_METHODS = {
    "tampo": "Tampo inteiriço",
    "travessas": "Travessas frontais/traseiras",
    "sem_topo": "Sem topo",
}

BACK_METHODS = {
    "rasgo": "Fundo em rasgo",
    "sobreposto": "Fundo sobreposto",
    "sem_fundo": "Sem fundo",
}

DOOR_TYPES = {
    "none": "Sem portas",
    "hinged": "Portas de abrir",
    "sliding": "Portas de correr",
}

GRAIN_CHOICES = ("length", "width", "none")
GRAIN_LABELS = {
    "length": "Ao comprimento",
    "width": "À largura",
    "none": "Indiferente",
}

#: Empty prices are intentional: no commercial value is invented.  The user
#: fills the price table from their supplier before issuing a quote.
SHEET_DEFAULT_LENGTH_MM = 2750.0
SHEET_DEFAULT_WIDTH_MM = 1830.0

DEFAULT_EDGE_BAND_ID = "EB-PVC-BRANCO-045"
DEFAULT_MATERIAL_ID = "MAT-MDF-BRANCO-18"

#: Per-type validation limits.  They can be overridden by a project's settings
#: (``FurnitureSettings.limits``) without editing code.
DEFAULT_LIMITS = {
    "armario_inferior": {"w": (250.0, 1400.0), "h": (500.0, 1100.0), "d": (250.0, 750.0)},
    "armario_superior": {"w": (200.0, 1400.0), "h": (250.0, 1200.0), "d": (200.0, 500.0)},
    "torre": {"w": (250.0, 1400.0), "h": (900.0, 3000.0), "d": (250.0, 800.0)},
    "guarda_roupa": {"w": (500.0, 4000.0), "h": (1500.0, 3200.0), "d": (400.0, 900.0)},
    "closet": {"w": (400.0, 4000.0), "h": (1200.0, 3200.0), "d": (300.0, 800.0)},
    "gaveteiro": {"w": (250.0, 1200.0), "h": (400.0, 1200.0), "d": (300.0, 800.0)},
    "balcao": {"w": (300.0, 2400.0), "h": (650.0, 1100.0), "d": (300.0, 900.0)},
    "nicho": {"w": (150.0, 2000.0), "h": (200.0, 2500.0), "d": (100.0, 600.0)},
    "prateleira": {"w": (150.0, 3000.0), "h": (18.0, 500.0), "d": (100.0, 700.0)},
    "painel": {"w": (100.0, 4000.0), "h": (100.0, 3200.0), "d": (6.0, 100.0)},
    "porta_abrir": {"w": (150.0, 1200.0), "h": (150.0, 2600.0), "d": (10.0, 80.0)},
    "porta_correr": {"w": (300.0, 3000.0), "h": (300.0, 2800.0), "d": (10.0, 100.0)},
    "personalizado": {"w": (50.0, 6000.0), "h": (50.0, 4000.0), "d": (10.0, 1200.0)},
    "bancada": {"w": (300.0, 4000.0), "h": (20.0, 300.0), "d": (300.0, 1200.0)},
}

DEFAULT_FINISHES = (
    "Liso", "Madeira", "Fosco", "Brilhante", "Texturizado", "Pedra",
    "Vidro", "Metal", "Tecido",
)

DEFAULT_CURRENCIES = ("BRL", "USD", "EUR", "ARS", "PEN")

#: Hardware categories understood by the rules and editors.
HARDWARE_CATEGORIES = {
    "dobradica": "Dobradiça",
    "corredica": "Corrediça",
    "puxador": "Puxador",
    "pe": "Pé / nivelador",
    "rodizio": "Rodízio",
    "parafuso": "Parafuso",
    "cavilha": "Cavilha",
    "minifix": "Minifix",
    "outro": "Outro",
}
