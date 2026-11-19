# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Gerenciador centralizado de preferências persistentes do usuário para TrazoMob.

Armazena em arquivo JSON em %LOCALAPPDATA%/IngeTrazo (Windows) ou ~/.config/ingetrazo (Linux/macOS):
1. Padrões globais de marcenaria (espessuras, materiais, fita, puxadores, fixação);
2. Dimensões padrão por tipo ou categoria de módulo (balcões, gaveteiros, aéreos, roupeiros, etc.);
3. Configurações de réguas e linhas-guia de parede (presets ativos, visibilidade, cotas).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
from pathlib import Path
from typing import Any, Dict, Optional

from core.paths import user_log_dir


PREFERENCES_FILENAME = "trazomob_preferences.json"

logger = logging.getLogger("trazomob.preferences")

# Derivação do PIN: PBKDF2-HMAC-SHA256 com salt aleatório (substitui o SHA-256
# sem salt, que permitia quebrar um PIN de 4 dígitos por força bruta trivial).
PIN_PBKDF2_PREFIX = "pbkdf2_sha256"
PIN_PBKDF2_ITERATIONS = 200_000


def _hash_pin(pin: str) -> str:
    """Deriva o hash do PIN no formato ``pbkdf2_sha256$iterações$salt$hash``."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", pin.encode("utf-8"), bytes.fromhex(salt), PIN_PBKDF2_ITERATIONS
    )
    return f"{PIN_PBKDF2_PREFIX}${PIN_PBKDF2_ITERATIONS}${salt}${dk.hex()}"


def _verify_pin(pin: str, stored: str) -> tuple[bool, bool]:
    """Verifica o PIN. Retorna ``(confere, precisa_migrar)``.

    Suporta o formato legado (SHA-256 sem salt) para não invalidar PINs já
    configurados; quando um hash legado confere, sinaliza migração para PBKDF2.
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
    """Retorna o caminho absoluto do arquivo de preferências do usuário."""
    # user_log_dir() retorna a pasta base de dados do usuário (ex: %LOCALAPPDATA%/IngeTrazo)
    base_dir = user_log_dir()
    return base_dir / PREFERENCES_FILENAME


DEFAULT_PREFERENCES: Dict[str, Any] = {
    # ── 1. Padrões Globais de Marcenaria ──
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
    # ── 2. Dimensões Padrão por Categoria ou Tipo ──
    # Se uma chave de tipo (ex: 'balcao', 'aereo') ou categoria (ex: 'inferior') estiver aqui,
    # novos módulos inseridos usam estas dimensões no lugar do catálogo cru.
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
    # ── 3. Réguas e Linhas-guia de Parede ──
    "wall_guides": {
        "active_preset": "Cozinha",
        "visible": True,
        "show_labels": False,
        "snap_enabled": True,
        "custom_presets": {},
    },
    # ── 4. Meus Módulos (catálogo pessoal do usuário) ──
    # Lista de módulos salvos pelo usuário (dicts no mesmo formato do
    # MODULE_CATALOG). Aparecem na galeria e no ribbon como "Meus Módulos".
    "user_modules": [],
    # ── 5. Precificação e Orçamento (Híbrido + PIN) ──
    "pricing": {
        # Segurança: PIN de 4 dígitos em hash SHA-256 (vazio = sem PIN)
        "pin_hash": "",
        # Modo de cálculo de chapas: "m2_perda" | "inteira"
        "modo_calculo_chapas": "m2_perda",
        # Fator de perda para cálculo por m² (0.0 = sem acréscimo de perda em testes padrão)
        "perda_chapa_percent": 0.0,
        # Dimensões padrão da chapa inteira da revenda (mm)
        "chapa_padrao_dim": [2750.0, 1850.0],
        # Preços de chapas por m² (chave = "Material EspessuraMM")
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
        # Preços opcionais por chapa inteira da revenda
        "chapas_inteiras": {},
        # Preço da fita de borda por metro linear
        "fita_borda_m": {
            "0.45mm": 1.80,
            "1.0mm": 2.50,
            "2.0mm": 4.20,
        },
        # Serviços de central de corte terceirizada
        "servico_corte_por_chapa": 0.0,
        "servico_fita_por_metro": 0.0,
        # Linha ativa de ferragens: "economica" | "standard" | "premium"
        "linha_ferragem_ativa": "standard",
        # Preços de ferragens unitários base (Linha Standard)
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
        # Multiplicadores de custo por linha de ferragem
        "linhas_ferragens_multiplicador": {
            "economica": 0.75,
            "standard": 1.00,
            "premium": 2.20,
        },
        # Modo de formação de preço de venda: "detalhado" | "multiplicador"
        "modo_fechamento": "detalhado",
        # Fator multiplicador simplificado sobre materiais (se modo == "multiplicador")
        "fator_multiplicador": 2.80,
        # Mão de obra por m² de chapa processada (fabricação)
        "mao_de_obra_m2": 45.00,
        # Montagem e instalação
        "montagem_tipo": "percentual",  # "percentual" | "fixo" | "por_m2"
        "montagem_valor": 0.0,          # opcional, padrão 0 para retrocompatibilidade
        # Markup percentual sobre custo direto (ex: 1.35 = 35% de margem)
        "markup": 1.35,
        # Impostos (ex: ICMS, IPI, PIS/COFINS) - percentual sobre valor com markup
        "impostos_percent": 0.18,
        # Desconto comercial padrão para pagamento à vista (percentual)
        "desconto_percent": 0.05,
        # Condições de parcelamento padrão
        "parcelas_sem_juros": 6,
        "parcelas_max": 12,
        # Frete fixo ou por m²
        "frete_tipo": "fixo",  # "fixo" | "por_m2"
        "frete_valor": 150.00,
        # Dados da empresa para proposta
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
    """Gerenciador singleton para leitura e escrita segura de preferências do usuário."""

    _instance: Optional[TrazoMobPreferencesManager] = None

    def __init__(self) -> None:
        self.filepath = get_preferences_file_path()
        self._data: Dict[str, Any] = {}
        self.load()

    @classmethod
    def get_instance(cls) -> TrazoMobPreferencesManager:
        if cls._instance is None:
            cls._instance = TrazoMobPreferencesManager()
        return cls._instance

    def load(self) -> None:
        """Carrega as preferências do disco com fallback para os valores padrão."""
        import copy
        self._data = copy.deepcopy(DEFAULT_PREFERENCES)

        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    if isinstance(saved, dict):
                        # Merge recursivo de dicionários
                        for section, values in saved.items():
                            if isinstance(values, dict) and isinstance(self._data.get(section), dict):
                                self._data[section].update(values)
                            else:
                                self._data[section] = values
            except Exception as e:
                # Se corrompido, mantém os defaults
                logger.warning("Aviso ao carregar preferências: %s", e)

    def save(self) -> bool:
        """Grava as preferências atuais no disco."""
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error("Erro ao salvar preferências: %s", e)
            return False

    def get_section(self, section: str) -> Dict[str, Any]:
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

    def set_module_defaults(self, mod_id_or_cat: str, params: Dict[str, Any]) -> None:
        m_defs = self._data.setdefault("module_defaults", {})
        target = m_defs.setdefault(mod_id_or_cat, {})
        target.update(params)

    def get_wall_guides_config(self) -> Dict[str, Any]:
        return self._data.setdefault("wall_guides", {})

    def save_wall_guides_config(self, active_preset: str, visible: bool, show_labels: bool, snap_enabled: bool, custom_presets: Optional[Dict] = None) -> None:
        wg = self.get_wall_guides_config()
        wg["active_preset"] = active_preset
        wg["visible"] = bool(visible)
        wg["show_labels"] = bool(show_labels)
        wg["snap_enabled"] = bool(snap_enabled)
        if custom_presets is not None:
            wg["custom_presets"] = custom_presets
        self.save()

    # ── Meus Módulos (catálogo pessoal) ──
    def get_user_modules(self) -> list[Dict[str, Any]]:
        """Retorna a lista de módulos salvos pelo usuário (cópia defensiva)."""
        mods = self._data.setdefault("user_modules", [])
        if not isinstance(mods, list):
            mods = []
            self._data["user_modules"] = mods
        return [dict(m) for m in mods if isinstance(m, dict)]

    def set_user_modules(self, modules: list[Dict[str, Any]]) -> bool:
        """Substitui toda a coleção de módulos do usuário e persiste."""
        self._data["user_modules"] = [dict(m) for m in modules if isinstance(m, dict)]
        return self.save()

    def add_user_module(self, module: Dict[str, Any]) -> bool:
        """Adiciona (ou atualiza, mesmo ``id``) um módulo do usuário e persiste."""
        module = dict(module)
        module_id = module.get("id")
        mods = [m for m in self.get_user_modules() if m.get("id") != module_id]
        mods.append(module)
        return self.set_user_modules(mods)

    def remove_user_module(self, module_id: str) -> bool:
        """Remove um módulo do usuário pelo ``id``. Retorna True se removeu."""
        mods = self.get_user_modules()
        restantes = [m for m in mods if m.get("id") != module_id]
        if len(restantes) == len(mods):
            return False
        return self.set_user_modules(restantes)

    # ── Precificação (Onda 3 + Híbrido) ──
    def get_pricing_config(self) -> Dict[str, Any]:
        return self._data.setdefault("pricing", {})

    def check_pin(self, pin: str) -> bool:
        """Verifica se o PIN fornecido confere com o configurado. Retorna True se não houver PIN."""
        pricing = self.get_pricing_config()
        stored_hash = pricing.get("pin_hash", "").strip()
        if not stored_hash:
            return True
        ok, precisa_migrar = _verify_pin(pin, stored_hash)
        if ok and precisa_migrar:
            # Atualiza hashes legados (SHA-256 sem salt) para PBKDF2.
            pricing["pin_hash"] = _hash_pin(pin.strip())
            self.save()
        return ok

    def has_pin(self) -> bool:
        """Indica se um PIN de proteção foi configurado."""
        pricing = self.get_pricing_config()
        return bool(pricing.get("pin_hash", "").strip())

    def set_pin(self, new_pin: str) -> bool:
        """Define ou altera o PIN (se new_pin for vazio, remove o PIN)."""
        pricing = self.get_pricing_config()
        if not new_pin or not new_pin.strip():
            pricing["pin_hash"] = ""
        else:
            pricing["pin_hash"] = _hash_pin(new_pin.strip())
        return self.save()

    def get_chapa_price_m2(self, material: str, espessura: float) -> float:
        """Retorna preço por m² da chapa. Chave esperada: 'Material XXmm'."""
        pricing = self.get_pricing_config()
        key = f"{material} {espessura:.0f}mm"
        return pricing.get("chapas_m2", {}).get(key, 0.0)

    def get_fita_price_m(self, espessura_fita: float) -> float:
        """Retorna preço por metro linear da fita de borda."""
        pricing = self.get_pricing_config()
        key = f"{espessura_fita:.2f}mm".replace(".", ",")
        return pricing.get("fita_borda_m", {}).get(key, 0.0)

    def get_ferragem_price(self, ferragem_key: str) -> float:
        """Retorna preço unitário de uma ferragem."""
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

    def get_frete_config(self) -> Dict[str, Any]:
        pricing = self.get_pricing_config()
        return {
            "tipo": pricing.get("frete_tipo", "fixo"),
            "valor": pricing.get("frete_valor", 0.0),
        }

    def get_empresa_config(self) -> Dict[str, Any]:
        pricing = self.get_pricing_config()
        return pricing.get("empresa", {})

    def save_pricing_config(self, pricing_data: Dict[str, Any]) -> None:
        self._data["pricing"] = pricing_data
        self.save()
