# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Delegadores de compatibilidade do CabinetBuilder."""
from __future__ import annotations

from core.group import Group

from ..builders.wall_tall_cabinets import WallTallCabinetBuilder as AereoTorreBuilder
from ..builders.wardrobes import WardrobeBuilder as ArmarioBuilder
from ..builders.base_wall_cabinets import BaseWallCabinetBuilder as BalcaoAereoBuilder
from ..builders.countertops import CountertopBuilder as BancadaBuilder
from ..builders.corner_cabinets import CornerCabinetBuilder as CantoEspecialBuilder
from ..builders.beds import BedBuilder as CamaBuilder
from ..builders.esquadrias import EsquadriaBuilder
from ..builders.tamponamento_linha import TamponamentoLinhaBuilder


class DelegatesMixin:
    """Fachadas dos construtores especializados."""

    @classmethod
    def build_balcao(cls, *args, **kwargs) -> list[Group]:
        return BalcaoAereoBuilder.build_balcao(*args, **kwargs)

    @classmethod
    def build_gaveteiro(cls, *args, **kwargs) -> list[Group]:
        return BalcaoAereoBuilder.build_gaveteiro(*args, **kwargs)

    @classmethod
    def build_balcao_misto(cls, *args, **kwargs) -> list[Group]:
        return BalcaoAereoBuilder.build_balcao_misto(*args, **kwargs)

    @classmethod
    def build_aereo(cls, *args, **kwargs) -> list[Group]:
        return BalcaoAereoBuilder.build_aereo(*args, **kwargs)

    @classmethod
    def build_aereo_correr(cls, *args, **kwargs) -> list[Group]:
        return BalcaoAereoBuilder.build_aereo_correr(*args, **kwargs)

    @classmethod
    def build_nicho(cls, *args, **kwargs) -> list[Group]:
        return BalcaoAereoBuilder.build_nicho(*args, **kwargs)

    @classmethod
    def build_rack_nicho_gaveta(cls, *args, **kwargs) -> list[Group]:
        return BalcaoAereoBuilder.build_rack_nicho_gaveta(*args, **kwargs)

    @classmethod
    def build_balcao_pia(cls, *args, **kwargs) -> list[Group]:
        return BalcaoAereoBuilder.build_balcao_pia(*args, **kwargs)

    @classmethod
    def build_canto_reto(cls, *args, **kwargs) -> list[Group]:
        return CantoEspecialBuilder.build_canto_reto(*args, **kwargs)

    @classmethod
    def build_canto_l(cls, *args, **kwargs) -> list[Group]:
        return CantoEspecialBuilder.build_canto_l(*args, **kwargs)

    @classmethod
    def build_porta_tempero(cls, *args, **kwargs) -> list[Group]:
        return CantoEspecialBuilder.build_porta_tempero(*args, **kwargs)

    @classmethod
    def build_balcao_forno(cls, *args, **kwargs) -> list[Group]:
        return CantoEspecialBuilder.build_balcao_forno(*args, **kwargs)

    @classmethod
    def build_aereo_basculante(cls, *args, **kwargs) -> list[Group]:
        """Gera aéreo basculante (delegado para AereoTorreBuilder)."""
        return AereoTorreBuilder.build_aereo_basculante(*args, **kwargs)

    @classmethod
    def build_aereo_basculante_duplo(cls, *args, **kwargs) -> list[Group]:
        """Gera aéreo basculante duplo (delegado para AereoTorreBuilder)."""
        return AereoTorreBuilder.build_aereo_basculante_duplo(*args, **kwargs)

    @classmethod
    def build_aereo_microondas(cls, *args, **kwargs) -> list[Group]:
        """Gera aéreo para microondas (delegado para AereoTorreBuilder)."""
        return AereoTorreBuilder.build_aereo_microondas(*args, **kwargs)

    @classmethod
    def build_torre_quente(cls, *args, **kwargs) -> list[Group]:
        """Gera torre quente para fornos e gavetas (delegado para AereoTorreBuilder)."""
        return AereoTorreBuilder.build_torre_quente(*args, **kwargs)

    @classmethod
    def build_caixa_geladeira(cls, *args, **kwargs) -> list[Group]:
        """Gera caixa/fechamento para geladeira com maleiro (delegado para AereoTorreBuilder)."""
        return AereoTorreBuilder.build_caixa_geladeira(*args, **kwargs)

    @classmethod
    def build_roupeiro_portas_correr(cls, *args, **kwargs) -> list[Group]:
        """Gera roupeiro de portas de correr (delegado para ArmarioBuilder)."""
        return ArmarioBuilder.build_roupeiro_portas_correr(*args, **kwargs)

    @classmethod
    def build_roupeiro_cabideiro(cls, *args, **kwargs) -> list[Group]:
        """Gera roupeiro com cabideiro e maleiro (delegado para ArmarioBuilder)."""
        return ArmarioBuilder.build_roupeiro_cabideiro(*args, **kwargs)

    @classmethod
    def build_armario_prateleiras(cls, *args, **kwargs) -> list[Group]:
        """Gera armário com prateleiras e divisórias (delegado para ArmarioBuilder)."""
        return ArmarioBuilder.build_armario_prateleiras(*args, **kwargs)

    @classmethod
    def build_armario_divisoria(cls, *args, **kwargs) -> list[Group]:
        """Gera armário 2 portas com divisória central (delegado para ArmarioBuilder)."""
        return ArmarioBuilder.build_armario_divisoria(*args, **kwargs)

    @classmethod
    def build_armario_3portas(cls, *args, **kwargs) -> list[Group]:
        """Gera armário 3 portas com divisórias internas (delegado para ArmarioBuilder)."""
        return ArmarioBuilder.build_armario_3portas(*args, **kwargs)

    @classmethod
    def build_armario_maleiro_tamponado(cls, *args, **kwargs) -> list[Group]:
        """Gera armário maleiro com caixas tamponadas (delegado para ArmarioBuilder)."""
        return ArmarioBuilder.build_armario_maleiro_tamponado(*args, **kwargs)

    @classmethod
    def build_gabinete_banheiro(cls, *args, **kwargs) -> list[Group]:
        return BalcaoAereoBuilder.build_gabinete_banheiro(*args, **kwargs)

    @classmethod
    def build_bancada_reta(cls, *args, **kwargs) -> list[Group]:
        """Gera uma bancada reta de pedra (delegado para BancadaBuilder)."""
        return BancadaBuilder.build_bancada_reta(*args, **kwargs)

    @classmethod
    def build_bancada_pia(cls, *args, **kwargs) -> list[Group]:
        """Gera uma bancada de pia com cuba (delegado para BancadaBuilder)."""
        return BancadaBuilder.build_bancada_pia(*args, **kwargs)

    @classmethod
    def build_bancada_canto_l(cls, *args, **kwargs) -> list[Group]:
        """Gera uma bancada em L contínua de pedra (delegado para BancadaBuilder)."""
        return BancadaBuilder.build_bancada_canto_l(*args, **kwargs)

    @classmethod
    def build_bancada_ilha(cls, *args, **kwargs) -> list[Group]:
        """Gera uma ilha / bancada gourmet 360° (delegado para BancadaBuilder)."""
        return BancadaBuilder.build_bancada_ilha(*args, **kwargs)

    @classmethod
    def build_tampao_engrossado_pedra(cls, *args, **kwargs) -> list[Group]:
        """Gera um tampão engrossado de marmoraria/pedra (delegado para BancadaBuilder)."""
        return BancadaBuilder.build_tampao_engrossado_pedra(*args, **kwargs)

    @classmethod
    def build_peca_avulsa(cls, *args, **kwargs) -> list[Group]:
        from ..builders.parts import CustomPartsBuilder
        return CustomPartsBuilder.build_peca_avulsa(*args, **kwargs)

    @classmethod
    def build_tampo_engrossado(cls, *args, **kwargs) -> list[Group]:
        from ..builders.parts import CustomPartsBuilder
        return CustomPartsBuilder.build_tampo_engrossado(*args, **kwargs)

    @classmethod
    def build_portas_correr_avulsas(cls, *args, **kwargs) -> list[Group]:
        from ..builders.parts import CustomPartsBuilder
        return CustomPartsBuilder.build_portas_correr_avulsas(*args, **kwargs)

    @classmethod
    def build_prateleiras_avulsas(cls, *args, **kwargs) -> list[Group]:
        from ..builders.parts import CustomPartsBuilder
        return CustomPartsBuilder.build_prateleiras_avulsas(*args, **kwargs)

    @classmethod
    def build_cama_gaveteiros(cls, *args, **kwargs) -> list[Group]:
        return CamaBuilder.build_cama_gaveteiros(*args, **kwargs)

    @classmethod
    def build_cama_bau(cls, *args, **kwargs) -> list[Group]:
        return CamaBuilder.build_cama_bau(*args, **kwargs)

    @classmethod
    def build_cama_cabeceira(cls, *args, **kwargs) -> list[Group]:
        return CamaBuilder.build_cama_cabeceira(*args, **kwargs)

    @classmethod
    def build_bicama(cls, *args, **kwargs) -> list[Group]:
        return CamaBuilder.build_bicama(*args, **kwargs)

    @classmethod
    def build_beliche(cls, *args, **kwargs) -> list[Group]:
        return CamaBuilder.build_beliche(*args, **kwargs)

    @classmethod
    def build_cama_colmeia(cls, *args, **kwargs) -> list[Group]:
        return CamaBuilder.build_cama_colmeia(*args, **kwargs)

    @classmethod
    def build_rodape_fechado(cls, *args, **kwargs) -> list[Group]:
        from ..builders.parts import CustomPartsBuilder
        return CustomPartsBuilder.build_rodape_fechado(*args, **kwargs)

    @classmethod
    def build_tamponamento_linha(cls, *args, **kwargs) -> list[Group]:
        return TamponamentoLinhaBuilder.build_tamponamento_linha(*args, **kwargs)

    # ------------------------------------------------------------------
    # Esquadrias (portas e janelas): contrato próprio em mm
    # (largura_mm, altura_mm, esp_parede_mm, ...), fora do contrato de
    # mobiliário (prof_mm/esp_mm) porque não entram no plano de corte.
    # ------------------------------------------------------------------
    @classmethod
    def build_porta_giro(cls, *args, **kwargs) -> Group:
        return EsquadriaBuilder.build_porta_giro(*args, **kwargs)

    @classmethod
    def build_porta_pivotante(cls, *args, **kwargs) -> Group:
        return EsquadriaBuilder.build_porta_pivotante(*args, **kwargs)

    @classmethod
    def build_porta_correr_vidro(cls, *args, **kwargs) -> Group:
        return EsquadriaBuilder.build_porta_correr_vidro(*args, **kwargs)

    @classmethod
    def build_janela_correr(cls, *args, **kwargs) -> Group:
        return EsquadriaBuilder.build_janela_correr(*args, **kwargs)

    @classmethod
    def build_janela_correr_4folhas(cls, *args, **kwargs) -> Group:
        return EsquadriaBuilder.build_janela_correr_4folhas(*args, **kwargs)

    @classmethod
    def build_janela_maximar(cls, *args, **kwargs) -> Group:
        return EsquadriaBuilder.build_janela_maximar(*args, **kwargs)

    @classmethod
    def build_janela_vertical_bandeira(cls, *args, **kwargs) -> Group:
        return EsquadriaBuilder.build_janela_vertical_bandeira(*args, **kwargs)

    @classmethod
    def load_esquadria_igz(cls, *args, **kwargs) -> Group:
        return EsquadriaBuilder.load_esquadria_igz(*args, **kwargs)

    @classmethod
    def get_esquadria_local_mid_y(cls, *args, **kwargs) -> float:
        return EsquadriaBuilder.get_esquadria_local_mid_y(*args, **kwargs)
