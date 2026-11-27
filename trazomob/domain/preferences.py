# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Centralized manager for persistent user preferences in TrazoMob.

Stores in a JSON file at %LOCALAPPDATA%/IngeTrazo (Windows) or ~/.config/ingetrazo (Linux/macOS):
1. Global woodworking defaults (thicknesses, materials, edge banding, handles, fasteners);
2. Default dimensions by module type or category (base cabinets, drawer banks, wall cabinets, wardrobes, etc.);
3. Wall ruler and guide-line settings (active presets, visibility, dimensions).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
from pathlib import Path
from typing import Any

from core.paths import user_log_dir

PREFERENCES_FILENAME = "trazomob_preferences.json"

logger = logging.getLogger("trazomob.preferences")

# PIN derivation: PBKDF2-HMAC-SHA256 with random salt (replaces unsalted
# SHA-256, which allowed trivial brute-force cracking of a 4-digit PIN).
PIN_PBKDF2_PREFIX = "pbkdf2_sha256"
PIN_PBKDF2_ITERATIONS = 200_000


def _hash_pin(pin: str) -> str:
    """Derive the PIN hash in ``pbkdf2_sha256$iterations$salt$hash`` format."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", pin.encode("utf-8"), bytes.fromhex(salt), PIN_PBKDF2_ITERATIONS
    )
    return f"{PIN_PBKDF2_PREFIX}${PIN_PBKDF2_ITERATIONS}${salt}${dk.hex()}"


def _verify_pin(pin: str, stored: str) -> tuple[bool, bool]:
    """Verify the PIN. Returns ``(matches, needs_migration)``.

    Supports the legacy format (unsalted SHA-256) so existing PINs are not
    invalidated; when a legacy hash matches, signals migration to PBKDF2.
    """
    stored = stored.strip()
    if stored.startswith(PIN_PBKDF2_PREFIX + "$"):
        try:
            _, iters, salt, expected = stored.split("$")
            dk = hashlib.pbkdf2_hmac(
                "sha256", pin.encode("utf-8"), bytes.fromhex(salt), int(iters)
            )
            return hmac.compare_digest(dk.hex(), expected), False
        except (ValueError, TypeError):
            return False, False

    legacy = hashlib.sha256(pin.encode("utf-8")).hexdigest()
    ok = hmac.compare_digest(legacy, stored)
    return ok, ok


def get_preferences_file_path() -> Path:
    """Return the absolute path to the user preferences file."""
    # user_log_dir() returns the user data base folder (e.g., %LOCALAPPDATA%/IngeTrazo)
    base_dir = user_log_dir()
    return base_dir / PREFERENCES_FILENAME


DEFAULT_PREFERENCES: dict[str, Any] = {
    # ── 1. Global Woodworking Defaults ──
    "global": {
        "espessura_caixa_mm": 15.0,
        "espessura_frentes_mm": 15.0,
        "material_caixa": "MDF Branco TX",
        "material_frentes": "MDF Louro Freijó",
        "material_fita_caixa": None,
        "fita_caixa_modo": "frontal_1L",
        "puxador_tipo": "perfil",
        "puxador_cor": "anodizado_fosco",
        "puxador_pos": "superior",
        "perfil_modelo": "gola",
        "desconto_perfil_mm": 35.0,
        "tem_fundo": True,
        "tipo_fundo": "rasgo",
        "esp_fundo_mm": 6.0,
        "recuo_fundo_mm": 10.0,
        "prof_rasgo_mm": 5.0,
        "folga_fundo_mm": 2.0,
        "folga_frentes_mm": 3.0,
        "gerar_furacao": True,
        "dispositivo_fixacao": "minifix_cavilha",
        "afastamento_fixacao_frontal_mm": 50.0,
        "afastamento_fixacao_traseiro_mm": 50.0,
        "afastamento_cavilha_frontal_mm": 100.0,
        "afastamento_cavilha_traseiro_mm": 100.0,
        "travessa_frontal_em_pe": False,
        "travessa_traseira_em_pe": False,
        "larg_travessa_frontal_mm": 70.0,
        "larg_travessa_traseira_mm": 70.0,
        "recuo_porta_topo_mm": 50.0,
        "fita_travessas_modo": "frontal_1L",
    },
    # ── 2. Default Dimensions by Category or Type ──
    # If a type key (e.g., 'balcao', 'aereo') or category key (e.g., 'inferior') is set here,
    # newly inserted modules use these dimensions instead of the raw catalog.
    "module_defaults": {
        "inferior": {
            "altura": 720.0,
            "profundidade": 550.0,
            "rodape": 100.0,
        },
        "aereo": {
            "altura": 720.0,
            "profundidade": 350.0,
        },
        "alto": {
            "altura": 2200.0,
            "profundidade": 550.0,
        },
        "bancada": {
            "esp_pedra": 20.0,
            "altura_saia": 40.0,
            "altura_frontao": 100.0,
        },
    },
    # ── 3. Wall Rulers and Guide Lines ──
    "wall_guides": {
        "active_preset": "Cozinha",
        "visible": True,
        "show_labels": False,
        "snap_enabled": True,
        "custom_presets": {},
    },
    # ── 4. My Modules (user's personal catalog) ──
    # List of user-saved modules (dicts in the same format as
    # MODULE_CATALOG). Displayed in the gallery and ribbon as "My Modules".
    "user_modules": [],
    # ── 5. Pricing and Quoting (Hybrid + PIN) ──
    "pricing": {
        # Security: 4-digit PIN in SHA-256 hash (empty = no PIN)
        "pin_hash": "",
        # Sheet calculation mode: "m2_perda" | "inteira"
        "modo_calculo_chapas": "m2_perda",
        # Waste factor for calculation per m² (0.0 = no waste markup in default tests)
        "perda_chapa_percent": 0.0,
        # Standard dimensions of a full supplier sheet (mm)
        "chapa_padrao_dim": [2750.0, 1850.0],
        # Sheet prices per m² (key = "Material ThicknessMM")
        "chapas_m2": {
            "MDF Branco TX 15mm": 85.00,
            "MDF Fundo 6mm": 45.00,
            "MDF Louro Freijó 15mm": 95.00,
            "MDF Branco TX 18mm": 95.00,
            "MDF Louro Freijó 18mm": 105.00,
            "MDF Preto 15mm": 110.00,
            "MDF Cinza 15mm": 90.00,
            "Pedra Quartzo 20mm": 450.00,
            "Pedra Granito 20mm": 380.00,
            "Pedra Mármore 20mm": 520.00,
        },
        # Optional prices per full supplier sheet
        "chapas_inteiras": {},
        # Edge banding price per linear meter
        "fita_borda_m": {
            "0.45mm": 1.80,
            "1.0mm": 2.50,
            "2.0mm": 4.20,
        },
        # Outsourced cutting center services
        "servico_corte_por_chapa": 0.0,
        "servico_fita_por_metro": 0.0,
        # Active hardware tier: "economica" | "standard" | "premium"
        "linha_ferragem_ativa": "standard",
        # Base unit hardware prices (Standard Tier)
        "ferragens": {
            "puxador_perfil": 12.00,
            "puxador_ponto": 8.00,
            "puxador_embutido": 15.00,
            "dobradica_35mm": 3.50,
            "corredica_telescopica_40": 18.00,
            "corredica_telescopica_50": 22.00,
            "minifix_cavilha_kit": 1.20,
            "parafuso_confirmat": 0.35,
            "pes_nivelador": 2.80,
        },
        # Cost multipliers per hardware tier
        "linhas_ferragens_multiplicador": {
            "economica": 0.75,
            "standard": 1.00,
            "premium": 2.20,
        },
        # Selling price calculation mode: "detalhado" | "multiplicador"
        "modo_fechamento": "detalhado",
        # Simplified multiplier factor on materials (if mode == "multiplicador")
        "fator_multiplicador": 2.80,
        # Labor cost per m² of processed board (manufacturing)
        "mao_de_obra_m2": 45.00,
        # Assembly and installation
        "montagem_tipo": "percentual",  # Valid modes: "percentual" | "fixo" | "por_m2"
        "montagem_valor": 0.0,          # optional, defaults to 0 for backward compatibility
        # Percentage markup over direct cost (e.g., 1.35 = 35% margin)
        "markup": 1.35,
        # Taxes (e.g., ICMS, IPI, PIS/COFINS) - percentage over marked-up value
        "impostos_percent": 0.18,
        # Default commercial discount for cash payment (percentage)
        "desconto_percent": 0.05,
        # Default installment terms
        "parcelas_sem_juros": 6,
        "parcelas_max": 12,
        # Fixed or per-m² shipping
        "frete_tipo": "fixo",  # Valid types: "fixo" | "por_m2"
        "frete_valor": 150.00,
        # Company details for proposal
        "empresa": {
            "nome": "Marcenaria TrazoMob",
            "cnpj": "00.000.000/0001-00",
            "endereco": "Rua das Oficinas, 123 - Bairro Industrial",
            "cidade": "São Paulo - SP",
            "telefone": "(11) 99999-9999",
            "email": "orcamento@trazomob.com.br",
            "logo_path": "",
        },
    },
}


class TrazoMobPreferencesManager:
    """Singleton manager for safe reading and writing of user preferences."""

    _instance: TrazoMobPreferencesManager | None = None

    def __init__(self) -> None:
        self.filepath = get_preferences_file_path()
        self._data: dict[str, Any] = {}
        self.load()

    @classmethod
    def get_instance(cls) -> TrazoMobPreferencesManager:
        if cls._instance is None:
            cls._instance = TrazoMobPreferencesManager()
        return cls._instance

    def load(self) -> None:
        """Load preferences from disk with fallback to default values."""
        import copy
        self._data = copy.deepcopy(DEFAULT_PREFERENCES)

        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    if isinstance(saved, dict):
                        # Recursive dictionary merge
                        for section, values in saved.items():
                            if isinstance(values, dict) and isinstance(self._data.get(section), dict):
                                self._data[section].update(values)
                            else:
                                self._data[section] = values
            except Exception as e:
                # If corrupted, keep defaults
                logger.warning("Aviso ao carregar preferências: %s", e)

    def save(self) -> bool:
        """Write current preferences to disk."""
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error("Erro ao salvar preferências: %s", e)
            return False

    def get_section(self, section: str) -> dict[str, Any]:
        return self._data.setdefault(section, {})

    def get_global(self, key: str, default: Any = None) -> Any:
        return self._data.get("global", {}).get(key, default)

    def set_global(self, key: str, value: Any) -> None:
        self._data.setdefault("global", {})[key] = value

    def get_module_default(self, mod_id_or_cat: str, param: str, default: Any = None) -> Any:
        m_defs = self._data.get("module_defaults", {})
        if mod_id_or_cat in m_defs and param in m_defs[mod_id_or_cat]:
            return m_defs[mod_id_or_cat][param]
        return default

    def set_module_defaults(self, mod_id_or_cat: str, params: dict[str, Any]) -> None:
        m_defs = self._data.setdefault("module_defaults", {})
        target = m_defs.setdefault(mod_id_or_cat, {})
        target.update(params)

    def get_wall_guides_config(self) -> dict[str, Any]:
        return self._data.setdefault("wall_guides", {})

    def save_wall_guides_config(self, active_preset: str, visible: bool, show_labels: bool, snap_enabled: bool, custom_presets: dict | None = None) -> None:
        wg = self.get_wall_guides_config()
        wg["active_preset"] = active_preset
        wg["visible"] = bool(visible)
        wg["show_labels"] = bool(show_labels)
        wg["snap_enabled"] = bool(snap_enabled)
        if custom_presets is not None:
            wg["custom_presets"] = custom_presets
        self.save()

    # ── My Modules (personal catalog) ──
    def get_user_modules(self) -> list[dict[str, Any]]:
        """Return the list of user-saved modules (defensive copy)."""
        mods = self._data.setdefault("user_modules", [])
        if not isinstance(mods, list):
            mods = []
            self._data["user_modules"] = mods
        return [dict(m) for m in mods if isinstance(m, dict)]

    def set_user_modules(self, modules: list[dict[str, Any]]) -> bool:
        """Replace the entire collection of user modules and persist."""
        self._data["user_modules"] = [dict(m) for m in modules if isinstance(m, dict)]
        return self.save()

    def add_user_module(self, module: dict[str, Any]) -> bool:
        """Add (or update, matching ``id``) a user module and persist."""
        module = dict(module)
        module_id = module.get("id")
        mods = [m for m in self.get_user_modules() if m.get("id") != module_id]
        mods.append(module)
        return self.set_user_modules(mods)

    def remove_user_module(self, module_id: str) -> bool:
        """Remove a user module by ``id``. Returns True if removed."""
        mods = self.get_user_modules()
        restantes = [m for m in mods if m.get("id") != module_id]
        if len(restantes) == len(mods):
            return False
        return self.set_user_modules(restantes)

    # ── Pricing (Wave 3 + Hybrid) ──
    def get_pricing_config(self) -> dict[str, Any]:
        return self._data.setdefault("pricing", {})

    def check_pin(self, pin: str) -> bool:
        """Verify whether the provided PIN matches the configured one. Returns True if no PIN is set."""
        pricing = self.get_pricing_config()
        stored_hash = pricing.get("pin_hash", "").strip()
        if not stored_hash:
            return True
        ok, precisa_migrar = _verify_pin(pin, stored_hash)
        if ok and precisa_migrar:
            # Upgrade legacy hashes (unsalted SHA-256) to PBKDF2.
            pricing["pin_hash"] = _hash_pin(pin.strip())
            self.save()
        return ok

    def has_pin(self) -> bool:
        """Indicate whether a protection PIN has been configured."""
        pricing = self.get_pricing_config()
        return bool(pricing.get("pin_hash", "").strip())

    def set_pin(self, new_pin: str) -> bool:
        """Set or change the PIN (if new_pin is empty, removes the PIN)."""
        pricing = self.get_pricing_config()
        if not new_pin or not new_pin.strip():
            pricing["pin_hash"] = ""
        else:
            pricing["pin_hash"] = _hash_pin(new_pin.strip())
        return self.save()

    def get_chapa_price_m2(self, material: str, espessura: float) -> float:
        """Return board price per m². Expected key: 'Material XXmm'."""
        pricing = self.get_pricing_config()
        key = f"{material} {espessura:.0f}mm"
        return pricing.get("chapas_m2", {}).get(key, 0.0)

    def get_fita_price_m(self, espessura_fita: float) -> float:
        """Return edge banding price per linear meter."""
        pricing = self.get_pricing_config()
        key = f"{espessura_fita:.2f}mm".replace(".", ",")
        return pricing.get("fita_borda_m", {}).get(key, 0.0)

    def get_ferragem_price(self, ferragem_key: str) -> float:
        """Return unit price of a hardware item."""
        pricing = self.get_pricing_config()
        return pricing.get("ferragens", {}).get(ferragem_key, 0.0)

    def get_mao_de_obra_m2(self) -> float:
        pricing = self.get_pricing_config()
        return pricing.get("mao_de_obra_m2", 0.0)

    def get_markup(self) -> float:
        pricing = self.get_pricing_config()
        return pricing.get("markup", 1.0)

    def get_impostos_percent(self) -> float:
        pricing = self.get_pricing_config()
        return pricing.get("impostos_percent", 0.0)

    def get_desconto_percent(self) -> float:
        pricing = self.get_pricing_config()
        return pricing.get("desconto_percent", 0.0)

    def get_frete_config(self) -> dict[str, Any]:
        pricing = self.get_pricing_config()
        return {
            "tipo": pricing.get("frete_tipo", "fixo"),
            "valor": pricing.get("frete_valor", 0.0),
        }

    def get_empresa_config(self) -> dict[str, Any]:
        pricing = self.get_pricing_config()
        return pricing.get("empresa", {})

    def save_pricing_config(self, pricing_data: dict[str, Any]) -> None:
        self._data["pricing"] = pricing_data
        self.save()
