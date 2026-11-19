# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Registro central de construtores de módulos (Registry Pattern) do TrazoMob.

Permite registrar de forma polimórfica e extensível os construtores de cada
tipo de armário, gaveteiro, aéreo, torre, roupeiro, bancada ou peça avulsa,
eliminando a necessidade de cadeias monolíticas de if/elif no CabinetBuilder.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple
from core.group import Group

# Assinatura de uma função de construção:
# (cls, params: dict, context: dict) -> Tuple[List[Group], str]  (onde str é o module_name)
ModuleBuilderFunc = Callable[[Any, Dict[str, Any], Dict[str, Any]], Tuple[List[Group], str]]

_BUILDER_REGISTRY: Dict[str, ModuleBuilderFunc] = {}


def register_module_builder(types: str | Tuple[str, ...]) -> Callable[[ModuleBuilderFunc], ModuleBuilderFunc]:
    """Decorador para associar uma função de geração a um ou mais tipos de módulos."""
    def decorator(fn: ModuleBuilderFunc) -> ModuleBuilderFunc:
        if isinstance(types, str):
            _BUILDER_REGISTRY[types] = fn
        else:
            for t in types:
                _BUILDER_REGISTRY[t] = fn
        return fn
    return decorator


def get_module_builder(tipo: str) -> Optional[ModuleBuilderFunc]:
    """Retorna o construtor registrado para o tipo solicitado, ou None."""
    return _BUILDER_REGISTRY.get(tipo)


# ── REGISTRO DOS CONSTRUTORES CANÔNICOS DE MARCADORES MOVELEIROS ───────────

@register_module_builder("balcao")
def _build_balcao(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Balcao {int(L)}x{int(A)}x{int(P)}"
    pieces = cls.build_balcao(
        L, A, P,
        esp_mm=ctx["esp_mm"],
        rodape_mm=ctx["rodape_mm"],
        num_portas=params.get("num_portas", 2),
        num_prateleiras=params.get("num_prateleiras", 1),
        num_divisoes=params.get("num_divisoes"),
        lado_abertura_porta=params.get("lado_abertura_porta", "esquerda"),
        tem_fundo=(ctx["tipo_fundo"] != "sem_fundo"),
        material=ctx["material"],
        material_frentes=ctx["material_frentes"],
        esp_frentes_mm=ctx["esp_frentes_mm"],
        offset=ctx["offset"],
        mat_ctx=ctx.get("mat_ctx"),
        **ctx["fundo_kwargs"],
        **ctx["pux_kw"],
        **ctx["travessas_kwargs"],
    )
    return pieces, name


@register_module_builder("gaveteiro")
def _build_gaveteiro(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Gaveteiro {int(L)}x{int(A)}x{int(P)}"
    pieces = cls.build_gaveteiro(
        L, A, P,
        num_gavetas=params.get("num_gavetas", 4),
        esp_mm=ctx["esp_mm"],
        rodape_mm=ctx["rodape_mm"],
        material=ctx["material"],
        material_frentes=ctx["material_frentes"],
        esp_frentes_mm=ctx["esp_frentes_mm"],
        offset=ctx["offset"],
        mat_ctx=ctx.get("mat_ctx"),
        **ctx["fundo_kwargs"],
        **ctx["pux_kw"],
        **ctx["travessas_kwargs"],
        **ctx["gaveta_kwargs"],
    )
    return pieces, name


@register_module_builder("balcao_misto")
def _build_balcao_misto(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Balcao Misto {int(L)}x{int(A)}x{int(P)}"
    pieces = cls.build_balcao_misto(
        L, A, P,
        num_gavetas=params.get("num_gavetas", 4),
        largura_gaveteiro_mm=params.get("largura_gaveteiro", 450.0),
        lado_gaveteiro=params.get("lado_gaveteiro", "esquerda"),
        num_portas=params.get("num_portas", 2),
        num_prateleiras=params.get("num_prateleiras", 1),
        esp_mm=ctx["esp_mm"],
        rodape_mm=ctx["rodape_mm"],
        material=ctx["material"],
        material_frentes=ctx["material_frentes"],
        esp_frentes_mm=ctx["esp_frentes_mm"],
        offset=ctx["offset"],
        mat_ctx=ctx.get("mat_ctx"),
        lado_abertura_porta=params.get("lado_abertura_porta"),
        **ctx["fundo_kwargs"],
        **ctx["pux_kw"],
        **ctx["travessas_kwargs"],
        **ctx["gaveta_kwargs"],
    )
    return pieces, name


@register_module_builder("balcao_pia")
def _build_balcao_pia(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Balcao Pia {int(L)}x{int(A)}x{int(P)}"
    pieces = cls.build_balcao_pia(
        L, A, P,
        esp_mm=ctx["esp_mm"],
        rodape_mm=ctx["rodape_mm"],
        num_portas=params.get("num_portas", 2),
        material=ctx["material"],
        material_frentes=ctx["material_frentes"],
        esp_frentes_mm=ctx["esp_frentes_mm"],
        tem_fundo=(ctx["tipo_fundo"] != "sem_fundo"),
        offset=ctx["offset"],
        mat_ctx=ctx.get("mat_ctx"),
        lado_abertura_porta=params.get("lado_abertura_porta", "esquerda"),
        **ctx["fundo_kwargs"],
        **ctx["pux_kw"],
        **ctx["travessas_kwargs"],
    )
    return pieces, name


@register_module_builder("balcao_canto")
def _build_balcao_canto(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Balcao Canto Reto {int(L)}x{int(A)}x{int(P)}"
    lado_cego = params.get("lado_cego", "esquerda")
    larg_porta_canto = float(params.get("largura_porta_canto", 450.0))
    esp_mont_canto = float(params.get("esp_montante_canto", 70.0))
    tem_fech = bool(params.get("tem_fechamento_canto", True))
    tem_regua = bool(params.get("tem_regua_fechamento", False))
    larg_regua = float(params.get("larg_regua_fechamento_mm", 50.0))
    larg_cego_param = params.get("largura_cego_mm", None)
    larg_cego_val = float(larg_cego_param) if larg_cego_param is not None else None
    dist_regua_param = params.get("dist_regua_fechamento_mm", None)
    dist_regua_val = float(dist_regua_param) if dist_regua_param is not None else None
    pieces = cls.build_canto_reto(
        L, A, P,
        esp_mm=ctx["esp_mm"],
        rodape_mm=ctx["rodape_mm"],
        lado_cego=lado_cego,
        largura_porta_mm=larg_porta_canto,
        largura_cego_mm=larg_cego_val,
        esp_montante_mm=esp_mont_canto,
        tem_fechamento=tem_fech,
        tem_regua_fechamento=tem_regua,
        larg_regua_fechamento_mm=larg_regua,
        dist_regua_fechamento_mm=dist_regua_val,
        num_prateleiras=params.get("num_prateleiras", 1),
        material=ctx["material"],
        material_frentes=ctx["material_frentes"],
        esp_frentes_mm=ctx["esp_frentes_mm"],
        offset=ctx["offset"],
        **ctx["fundo_kwargs"],
        **ctx["pux_kw"],
        **ctx["travessas_kwargs"],
        mat_ctx=ctx.get("mat_ctx"),
    )
    return pieces, name


@register_module_builder(("balcao_canto_l", "canto_l"))
def _build_canto_l(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Canto L {int(L)}x{int(A)}x{int(P)}"
    pieces = cls.build_canto_l(
        L, A, P,
        larg_asa_esq_mm=params.get("larg_asa_esq", 550.0),
        larg_asa_dir_mm=params.get("larg_asa_dir", 550.0),
        tem_batente_canto=bool(params.get("tem_batente_canto", False)),
        esp_mm=ctx["esp_mm"],
        rodape_mm=ctx["rodape_mm"],
        num_prateleiras=params.get("num_prateleiras", 1),
        material=ctx["material"],
        material_frentes=ctx["material_frentes"],
        esp_frentes_mm=ctx["esp_frentes_mm"],
        offset=ctx["offset"],
        **ctx["fundo_kwargs"],
        **ctx["pux_kw"],
        **ctx["travessas_kwargs"],
        mat_ctx=ctx.get("mat_ctx"),
    )
    return pieces, name


@register_module_builder("porta_tempero")
def _build_porta_tempero(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Porta Tempero {int(L)}x{int(A)}x{int(P)}"
    pieces = cls.build_porta_tempero(
        L, A, P,
        esp_mm=ctx["esp_mm"],
        rodape_mm=ctx["rodape_mm"],
        material=ctx["material"],
        material_frentes=ctx["material_frentes"],
        esp_frentes_mm=ctx["esp_frentes_mm"],
        offset=ctx["offset"],
        **ctx["fundo_kwargs"],
        **ctx["pux_kw"],
        **ctx["travessas_kwargs"],
        tipo_estrutura_tempero=str(params.get("tipo_estrutura_tempero", "mdf")),
        cor_aramado=str(params.get("cor_aramado", "cromado")),
        mat_ctx=ctx.get("mat_ctx"),
    )
    return pieces, name


@register_module_builder("balcao_forno")
def _build_balcao_forno(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Balcao Forno {int(L)}x{int(A)}x{int(P)}"
    pieces = cls.build_balcao_forno(
        L, A, P,
        esp_mm=ctx["esp_mm"],
        rodape_mm=ctx["rodape_mm"],
        tem_gaveta=bool(params.get("tem_gaveta", True)),
        alt_gaveta_mm=float(params.get("alt_gaveta_mm", 150.0)),
        material=ctx["material"],
        material_frentes=ctx["material_frentes"],
        esp_frentes_mm=ctx["esp_frentes_mm"],
        offset=ctx["offset"],
        **ctx["pux_kw"],
        **ctx["travessas_kwargs"],
        mat_ctx=ctx.get("mat_ctx"),
        **ctx["gaveta_kwargs"],
    )
    return pieces, name


@register_module_builder("aereo")
def _build_aereo(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Aereo {int(L)}x{int(A)}x{int(P)}"
    pieces = cls.build_aereo(
        L, A, P,
        esp_mm=ctx["esp_mm"],
        num_portas=params.get("num_portas", 2),
        num_prateleiras=params.get("num_prateleiras", 1),
        material=ctx["material"],
        material_frentes=ctx["material_frentes"],
        esp_frentes_mm=ctx["esp_frentes_mm"],
        offset=ctx["offset"],
        gerar_furacao=ctx["travessas_kwargs"]["gerar_furacao"],
        dispositivo_fixacao=ctx["travessas_kwargs"]["dispositivo_fixacao"],
        mat_ctx=ctx.get("mat_ctx"),
        lado_abertura_porta=params.get("lado_abertura_porta", "esquerda"),
        **ctx["fundo_kwargs"],
        **ctx["pux_kw"],
    )
    return pieces, name


@register_module_builder(("aereo_correr", "aereo_correr_2p", "aereo_correr_3p", "aereo_correr_4p"))
def _build_aereo_correr(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    tipo = str(params.get("tipo", "aereo_correr"))
    if tipo == "aereo_correr_2p":
        default_vaos = 2
    elif tipo == "aereo_correr_3p":
        default_vaos = 3
    elif tipo == "aereo_correr_4p":
        default_vaos = 4
    else:
        default_vaos = int(params.get("num_vaos", params.get("num_portas", 3)))
    n_vaos = int(params.get("num_vaos", default_vaos))
    n_vaos = max(2, min(4, n_vaos))
    name = f"Aereo {n_vaos} Vãos Correr {int(L)}x{int(A)}x{int(P)}"
    pieces = cls.build_aereo_correr(
        L, A, P,
        esp_mm=ctx["esp_mm"],
        num_vaos=n_vaos,
        num_portas=n_vaos,
        num_prateleiras=int(params.get("num_prateleiras", 0)),
        material=ctx["material"],
        material_frentes=ctx["material_frentes"],
        esp_frentes_mm=ctx["esp_frentes_mm"],
        offset=ctx["offset"],
        exibir_portas=bool(params.get("exibir_portas", params.get("has_portas", True))),
        gerar_furacao=ctx["travessas_kwargs"]["gerar_furacao"],
        dispositivo_fixacao=ctx["travessas_kwargs"]["dispositivo_fixacao"],
        mat_ctx=ctx.get("mat_ctx"),
        **ctx["fundo_kwargs"],
        **ctx["pux_kw"],
    )
    return pieces, name


@register_module_builder("aereo_basculante")
def _build_aereo_basculante(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Aereo Basculante {int(L)}x{int(A)}x{int(P)}"
    pieces = cls.build_aereo_basculante(
        L, A, P,
        esp_mm=ctx["esp_mm"],
        material=ctx["material"],
        material_frentes=ctx["material_frentes"],
        esp_frentes_mm=ctx["esp_frentes_mm"],
        offset=ctx["offset"],
        gerar_furacao=ctx["travessas_kwargs"]["gerar_furacao"],
        dispositivo_fixacao=ctx["travessas_kwargs"]["dispositivo_fixacao"],
        mat_ctx=ctx.get("mat_ctx"),
        **ctx["fundo_kwargs"],
        **ctx["pux_kw"],
    )
    return pieces, name


@register_module_builder("aereo_basculante_duplo")
def _build_aereo_basculante_duplo(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Aereo Basculante Duplo {int(L)}x{int(A)}x{int(P)}"
    pieces = cls.build_aereo_basculante_duplo(
        L, A, P,
        esp_mm=ctx["esp_mm"],
        material=ctx["material"],
        material_frentes=ctx["material_frentes"],
        esp_frentes_mm=ctx["esp_frentes_mm"],
        offset=ctx["offset"],
        gerar_furacao=ctx["travessas_kwargs"]["gerar_furacao"],
        dispositivo_fixacao=ctx["travessas_kwargs"]["dispositivo_fixacao"],
        mat_ctx=ctx.get("mat_ctx"),
        **ctx["fundo_kwargs"],
        **ctx["pux_kw"],
    )
    return pieces, name


@register_module_builder("aereo_microondas")
def _build_aereo_microondas(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Aereo Microondas {int(L)}x{int(A)}x{int(P)}"
    pieces = cls.build_aereo_microondas(
        L, A, P,
        esp_mm=ctx["esp_mm"],
        tipo_porta_superior=str(params.get("tipo_porta_superior", "basculante")),
        num_portas=int(params.get("num_portas", 1)),
        material=ctx["material"],
        material_frentes=ctx["material_frentes"],
        esp_frentes_mm=ctx["esp_frentes_mm"],
        offset=ctx["offset"],
        mat_ctx=ctx.get("mat_ctx"),
        **ctx["fundo_kwargs"],
        **ctx["pux_kw"],
    )
    return pieces, name


@register_module_builder("torre_quente")
def _build_torre_quente(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Torre Quente {int(L)}x{int(A)}x{int(P)}"
    pieces = cls.build_torre_quente(
        L, A, P,
        esp_mm=ctx["esp_mm"],
        rodape_mm=ctx["rodape_mm"],
        material=ctx["material"],
        material_frentes=ctx["material_frentes"],
        esp_frentes_mm=ctx["esp_frentes_mm"],
        offset=ctx["offset"],
        gerar_furacao=ctx["travessas_kwargs"]["gerar_furacao"],
        dispositivo_fixacao=ctx["travessas_kwargs"]["dispositivo_fixacao"],
        mat_ctx=ctx.get("mat_ctx"),
        lado_abertura_porta=params.get("lado_abertura_porta", "esquerda"),
        **ctx["fundo_kwargs"],
        **ctx["pux_kw"],
        **ctx["gaveta_kwargs"],
    )
    return pieces, name


@register_module_builder("caixa_geladeira")
def _build_caixa_geladeira(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Torre Geladeira {int(L)}x{int(A)}x{int(P)}"
    alt_nicho_gel = float(params.get("alt_nicho_geladeira_mm", params.get("alt_nicho_geladeira", 1800.0)))
    pieces = cls.build_caixa_geladeira(
        L, A, P,
        esp_mm=ctx["esp_mm"],
        alt_nicho_geladeira_mm=alt_nicho_gel,
        num_portas=int(params.get("num_portas", 2)),
        tipo_porta_superior=str(params.get("tipo_porta_superior", "duas_portas")),
        material=ctx["material"],
        material_frentes=ctx["material_frentes"],
        esp_frentes_mm=ctx["esp_frentes_mm"],
        offset=ctx["offset"],
        mat_ctx=ctx.get("mat_ctx"),
        **ctx["fundo_kwargs"],
        **ctx["pux_kw"],
    )
    return pieces, name


@register_module_builder(("roupeiro", "armario_1p_cabide"))
def _build_roupeiro(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    tipo = params.get("tipo", "roupeiro")
    name = f"Roupeiro {int(L)}x{int(A)}x{int(P)}"
    n_portas = int(params.get("num_portas", 1 if tipo == "armario_1p_cabide" else 2))
    pieces = cls.build_roupeiro_cabideiro(
        L, A, P,
        num_portas=n_portas,
        esp_mm=ctx["esp_mm"],
        rodape_mm=ctx["rodape_mm"],
        material=ctx["material"],
        material_frentes=ctx["material_frentes"],
        esp_frentes_mm=ctx["esp_frentes_mm"],
        offset=ctx["offset"],
        gerar_furacao=ctx["travessas_kwargs"]["gerar_furacao"],
        dispositivo_fixacao=ctx["travessas_kwargs"]["dispositivo_fixacao"],
        mat_ctx=ctx.get("mat_ctx"),
        lado_abertura_porta=params.get("lado_abertura_porta", "esquerda"),
        **ctx["fundo_kwargs"],
        **ctx["pux_kw"],
    )
    return pieces, name


@register_module_builder(("roupeiro_correr", "roupeiro_correr_2p", "roupeiro_correr_3p"))
def _build_roupeiro_correr(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    tipo = params.get("tipo", "roupeiro_correr")
    n_vaos = int(params.get("num_vaos", 3 if tipo == "roupeiro_correr_3p" or int(params.get("num_portas", 2)) == 3 else 2))
    exibir_portas = bool(params.get("exibir_portas", params.get("has_portas", True)))
    name = f"Roupeiro {n_vaos} Vãos Correr {int(L)}x{int(A)}x{int(P)}"
    pieces = cls.build_roupeiro_portas_correr(
        L, A, P,
        num_portas=n_vaos,
        num_vaos=n_vaos,
        esp_mm=ctx["esp_mm"],
        rodape_mm=ctx["rodape_mm"],
        material=ctx["material"],
        material_frentes=ctx["material_frentes"],
        esp_frentes_mm=ctx["esp_frentes_mm"],
        offset=ctx["offset"],
        exibir_portas=exibir_portas,
        gerar_furacao=ctx["travessas_kwargs"]["gerar_furacao"],
        dispositivo_fixacao=ctx["travessas_kwargs"]["dispositivo_fixacao"],
        mat_ctx=ctx.get("mat_ctx"),
        **ctx["fundo_kwargs"],
        **ctx["pux_kw"],
    )
    return pieces, name


@register_module_builder(("armario_prateleiras", "armario_1p_prat", "armario_2p_prat"))
def _build_armario_prateleiras(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    tipo = params.get("tipo", "armario_prateleiras")
    n_portas = int(params.get("num_portas", 1 if tipo == "armario_1p_prat" else 2))
    n_prat = params.get("num_prateleiras", 5 if n_portas == 1 else 4)
    name = f"Armario {int(L)}x{int(A)}x{int(P)}"
    pieces = cls.build_armario_prateleiras(
        L, A, P,
        num_portas=n_portas,
        num_prateleiras=n_prat,
        esp_mm=ctx["esp_mm"],
        rodape_mm=ctx["rodape_mm"],
        material=ctx["material"],
        material_frentes=ctx["material_frentes"],
        esp_frentes_mm=ctx["esp_frentes_mm"],
        offset=ctx["offset"],
        gerar_furacao=ctx["travessas_kwargs"]["gerar_furacao"],
        dispositivo_fixacao=ctx["travessas_kwargs"]["dispositivo_fixacao"],
        mat_ctx=ctx.get("mat_ctx"),
        lado_abertura_porta=params.get("lado_abertura_porta", "esquerda"),
        **ctx["fundo_kwargs"],
        **ctx["pux_kw"],
    )
    return pieces, name


@register_module_builder("armario_2p_divisao")
def _build_armario_2p_divisao(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Armario 2P Divisao {int(L)}x{int(A)}x{int(P)}"
    pieces = cls.build_armario_divisoria(
        L, A, P,
        num_prateleiras=params.get("num_prateleiras", 4),
        esp_mm=ctx["esp_mm"],
        rodape_mm=ctx["rodape_mm"],
        material=ctx["material"],
        material_frentes=ctx["material_frentes"],
        esp_frentes_mm=ctx["esp_frentes_mm"],
        offset=ctx["offset"],
        gerar_furacao=ctx["travessas_kwargs"]["gerar_furacao"],
        dispositivo_fixacao=ctx["travessas_kwargs"]["dispositivo_fixacao"],
        mat_ctx=ctx.get("mat_ctx"),
        **ctx["fundo_kwargs"],
        **ctx["pux_kw"],
    )
    return pieces, name


@register_module_builder("armario_3p_divisao")
def _build_armario_3p_divisao(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Armario 3P {int(L)}x{int(A)}x{int(P)}"
    pieces = cls.build_armario_3portas(
        L, A, P,
        num_gavetas=params.get("num_gavetas", 2),
        esp_mm=ctx["esp_mm"],
        rodape_mm=ctx["rodape_mm"],
        material=ctx["material"],
        material_frentes=ctx["material_frentes"],
        esp_frentes_mm=ctx["esp_frentes_mm"],
        offset=ctx["offset"],
        gerar_furacao=ctx["travessas_kwargs"]["gerar_furacao"],
        dispositivo_fixacao=ctx["travessas_kwargs"]["dispositivo_fixacao"],
        mat_ctx=ctx.get("mat_ctx"),
        lado_abertura_porta=params.get("lado_abertura_porta", "esquerda"),
        **ctx["fundo_kwargs"],
        **ctx["pux_kw"],
    )
    return pieces, name


@register_module_builder("gabinete_banheiro")
def _build_gabinete_banheiro(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Gabinete Banheiro {int(L)}x{int(A)}x{int(P)}"
    pieces = cls.build_gabinete_banheiro(
        L, A, P,
        esp_mm=ctx["esp_mm"],
        material=ctx["material"],
        material_frentes=ctx["material_frentes"],
        esp_frentes_mm=ctx["esp_frentes_mm"],
        offset=ctx["offset"],
        gerar_furacao=ctx["travessas_kwargs"]["gerar_furacao"],
        dispositivo_fixacao=ctx["travessas_kwargs"]["dispositivo_fixacao"],
        mat_ctx=ctx.get("mat_ctx"),
        **ctx["fundo_kwargs"],
        **ctx["pux_kw"],
        **ctx["gaveta_kwargs"],
    )
    return pieces, name


@register_module_builder("nicho")
def _build_nicho(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Nicho {int(L)}x{int(A)}x{int(P)}"
    div_v = int(params.get("num_divisoes", params.get("divisoes_vert", 0)))
    div_h = int(params.get("num_prateleiras", params.get("divisoes_horiz", 1)))
    tem_f = bool(params.get("tem_fundo", False)) and ctx["tipo_fundo"] != "sem_fundo"
    pieces = cls.build_nicho(
        L, A, P,
        esp_mm=ctx["esp_mm"],
        divisoes_vert=div_v,
        divisoes_horiz=div_h,
        material=ctx["material"],
        offset=ctx["offset"],
        tem_fundo=tem_f,
        fita_caixa_modo=ctx["travessas_kwargs"]["fita_caixa_modo"],
        material_fita_caixa=ctx["travessas_kwargs"]["material_fita_caixa"],
        gerar_furacao=ctx["travessas_kwargs"]["gerar_furacao"],
        dispositivo_fixacao=ctx["travessas_kwargs"]["dispositivo_fixacao"],
        mat_ctx=ctx.get("mat_ctx"),
        **ctx["fundo_kwargs"],
    )
    return pieces, name


@register_module_builder("rack_nicho_gaveta")
def _build_rack_nicho_gaveta(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Rack Nicho {int(L)}x{int(A)}x{int(P)}"
    larg_gav = float(params.get("largura_gaveteiro", params.get("largura_gaveteiro_mm", 600.0)))
    lado_gav = str(params.get("lado_gaveteiro", "esquerda"))
    num_gav = int(params.get("num_gavetas", 1))
    pieces = cls.build_rack_nicho_gaveta(
        largura_mm=L,
        altura_mm=A,
        prof_mm=P,
        largura_gaveteiro_mm=larg_gav,
        lado_gaveteiro=lado_gav,
        num_gavetas=num_gav,
        esp_mm=ctx["esp_mm"],
        material=ctx["material"],
        material_frentes=ctx["material_frentes"],
        esp_frentes_mm=ctx["esp_frentes_mm"],
        offset=ctx["offset"],
        material_gaveta=ctx["gaveta_kwargs"]["material_gaveta"],
        esp_gaveta_mm=ctx["gaveta_kwargs"]["esp_gaveta_mm"],
        material_fita_gaveta=ctx["gaveta_kwargs"]["material_fita_gaveta"],
        material_fundo_gaveta=ctx["gaveta_kwargs"]["material_fundo_gaveta"],
        esp_fundo_gaveta_mm=ctx["gaveta_kwargs"]["esp_fundo_gaveta_mm"],
        tipo_fundo_gaveta=ctx["gaveta_kwargs"]["tipo_fundo_gaveta"],
        folga_corredica_mm=ctx["gaveta_kwargs"]["folga_corredica_mm"],
        fita_caixa_modo=ctx["travessas_kwargs"]["fita_caixa_modo"],
        material_fita_caixa=ctx["travessas_kwargs"]["material_fita_caixa"],
        mat_ctx=ctx.get("mat_ctx"),
        **ctx["pux_kw"],
    )
    return pieces, name


@register_module_builder("bancada_reta")
def _build_bancada_reta(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Bancada Pedra {int(L)}x{int(P)}"
    pieces = cls.build_bancada_reta(
        L, altura_mm=A, prof_mm=P,
        esp_pedra_mm=float(params.get("esp_pedra", 20.0)),
        altura_saia_mm=float(params.get("altura_saia", 40.0)),
        altura_frontao_mm=float(params.get("altura_frontao", 100.0)),
        balanco_frontal_mm=float(params.get("balanco_frontal", 20.0)),
        tem_frontao_traseiro=bool(params.get("tem_frontao_traseiro", True)),
        tem_frontao_esq=bool(params.get("tem_frontao_esq", False)),
        tem_frontao_dir=bool(params.get("tem_frontao_dir", False)),
        tem_saia_esq=bool(params.get("tem_saia_esq", True)),
        tem_saia_dir=bool(params.get("tem_saia_dir", True)),
        material=ctx["material"],
        offset=ctx["offset"],
    )
    return pieces, name


@register_module_builder("bancada_pia")
def _build_bancada_pia(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Bancada Pia {int(L)}x{int(P)}"
    pieces = cls.build_bancada_pia(
        L, altura_mm=A, prof_mm=P,
        esp_pedra_mm=float(params.get("esp_pedra", 20.0)),
        altura_saia_mm=float(params.get("altura_saia", 40.0)),
        altura_frontao_mm=float(params.get("altura_frontao", 100.0)),
        balanco_frontal_mm=float(params.get("balanco_frontal", 20.0)),
        tem_saia_esq=bool(params.get("tem_saia_esq", True)),
        tem_saia_dir=bool(params.get("tem_saia_dir", True)),
        largura_cuba_mm=float(params.get("largura_cuba", 560.0)),
        prof_cuba_mm=float(params.get("prof_cuba", 400.0)),
        profundidade_cuba_mm=float(params.get("profundidade_cuba", 180.0)),
        posicao_cuba=str(params.get("posicao_cuba", "centro")),
        tipo_cuba=str(params.get("tipo_cuba", "inox_simples")),
        canto_recorte=str(params.get("canto_recorte", "arredondado")),
        raio_canto_mm=float(params.get("raio_canto_mm", 20.0)),
        tem_area_molhada=bool(params.get("tem_area_molhada", True)),
        rebaixo_molhado_mm=float(params.get("rebaixo_molhado_mm", 3.0)),
        tem_torneira=bool(params.get("tem_torneira", True)),
        material=ctx["material"],
        offset=ctx["offset"],
    )
    return pieces, name


@register_module_builder(("bancada_canto_l", "bancada_canto"))
def _build_bancada_canto_l(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Bancada L {int(L)}x{int(P)}"
    pieces = cls.build_bancada_canto_l(
        L, altura_mm=A, prof_mm=P,
        larg_asa_mm=float(params.get("larg_asa", 600.0)),
        esp_pedra_mm=float(params.get("esp_pedra", 20.0)),
        altura_saia_mm=float(params.get("altura_saia", 40.0)),
        altura_frontao_mm=float(params.get("altura_frontao", 100.0)),
        tem_saia_esq=bool(params.get("tem_saia_esq", True)),
        tem_saia_dir=bool(params.get("tem_saia_dir", True)),
        material=ctx["material"],
        offset=ctx["offset"],
    )
    return pieces, name


@register_module_builder("bancada_ilha")
def _build_bancada_ilha(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Ilha Gourmet {int(L)}x{int(P)}"
    pieces = cls.build_bancada_ilha(
        L, altura_mm=A, prof_mm=P,
        esp_pedra_mm=float(params.get("esp_pedra", 20.0)),
        altura_saia_mm=float(params.get("altura_saia", 60.0)),
        material=ctx["material"],
        offset=ctx["offset"],
    )
    return pieces, name


@register_module_builder("bancada_tampao_engrossado")
def _build_bancada_tampao_engrossado(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Tampao Engrossado Pedra {int(L)}x{int(A)}x{int(P)}"
    pieces = cls.build_tampao_engrossado_pedra(
        largura_mm=L,
        altura_mm=A,
        prof_mm=P,
        esp_pedra_mm=float(params.get("esp_pedra", 20.0)),
        material=ctx["material"],
        offset=ctx["offset"],
    )
    return pieces, name


@register_module_builder(("peca_tamponamento", "tamponamento_vertical"))
def _build_peca_tamponamento(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Tamponamento {int(P)}x{int(A)}"
    fita_modo = str(params.get("fita_caixa_modo", params.get("fita_borda_modo", "4L")))
    pieces = cls.build_peca_avulsa(
        "tamponamento_vertical", L, A, P,
        esp_mm=ctx["esp_mm"],
        material=ctx["material"],
        offset=ctx["offset"],
        material_fita=ctx["mat_fita_cx_p"],
        fita_borda_modo=fita_modo,
    )
    return pieces, name


@register_module_builder(("peca_lateral", "peca_lateral_esquerda"))
def _build_peca_lateral(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Lateral Esq {int(P)}x{int(A)}"
    pieces = cls.build_peca_avulsa(
        "lateral_esquerda", L, A, P,
        esp_mm=ctx["esp_mm"],
        material=ctx["material"],
        offset=ctx["offset"],
        material_fita=ctx["mat_fita_cx_p"],
    )
    return pieces, name


@register_module_builder("peca_lateral_direita")
def _build_peca_lateral_direita(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Lateral Dir {int(P)}x{int(A)}"
    pieces = cls.build_peca_avulsa(
        "lateral_direita", L, A, P,
        esp_mm=ctx["esp_mm"],
        material=ctx["material"],
        offset=ctx["offset"],
        material_fita=ctx["mat_fita_cx_p"],
    )
    return pieces, name


@register_module_builder("peca_base")
def _build_peca_base(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Base {int(L)}x{int(P)}"
    pieces = cls.build_peca_avulsa(
        "base", L, A, P,
        esp_mm=ctx["esp_mm"],
        material=ctx["material"],
        offset=ctx["offset"],
        material_fita=ctx["mat_fita_cx_p"],
    )
    return pieces, name


@register_module_builder("peca_tampo_superior")
def _build_peca_tampo_superior(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Tampo Superior {int(L)}x{int(P)}"
    pieces = cls.build_peca_avulsa(
        "tampo_superior", L, A, P,
        esp_mm=ctx["esp_mm"],
        material=ctx["material"],
        offset=ctx["offset"],
        material_fita=ctx["mat_fita_cx_p"],
    )
    return pieces, name


@register_module_builder("peca_divisoria_vertical")
def _build_peca_divisoria_vertical(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Divisória Vertical {int(P)}x{int(A)}"
    cav_cima = bool(params.get("cavilha_topo_superior", params.get("furacao_cima", True)))
    cav_baixo = bool(params.get("cavilha_topo_inferior", params.get("furacao_baixo", True)))
    afast_f = float(params.get("afastamento_cavilha_frontal_mm", 50.0))
    afast_t = float(params.get("afastamento_cavilha_traseiro_mm", 50.0))
    pieces = cls.build_peca_avulsa(
        "divisoria_vertical", L, A, P,
        esp_mm=ctx["esp_mm"],
        material=ctx["material"],
        offset=ctx["offset"],
        material_fita=ctx["mat_fita_cx_p"],
        cavilha_topo_superior=cav_cima,
        cavilha_topo_inferior=cav_baixo,
        afastamento_cavilha_frontal_mm=afast_f,
        afastamento_cavilha_traseiro_mm=afast_t,
    )
    return pieces, name


@register_module_builder("peca_divisoria_horizontal")
def _build_peca_divisoria_horizontal(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Divisória Horizontal {int(L)}x{int(P)}"
    pieces = cls.build_peca_avulsa(
        "divisoria_horizontal", L, A, P,
        esp_mm=ctx["esp_mm"],
        material=ctx["material"],
        offset=ctx["offset"],
        material_fita=ctx["mat_fita_cx_p"],
    )
    return pieces, name


@register_module_builder("peca_porta_esquerda")
def _build_peca_porta_esquerda(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Porta Esq {int(L)}x{int(A)}"
    pieces = cls.build_peca_avulsa(
        "porta_esquerda", L, A, P,
        esp_mm=ctx["esp_mm"],
        material=ctx["material_frentes"] or ctx["material"],
        offset=ctx["offset"],
        material_fita=ctx["mat_fita_cx_p"],
        **ctx["pux_kw"],
    )
    return pieces, name


@register_module_builder("peca_porta_direita")
def _build_peca_porta_direita(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Porta Dir {int(L)}x{int(A)}"
    pieces = cls.build_peca_avulsa(
        "porta_direita", L, A, P,
        esp_mm=ctx["esp_mm"],
        material=ctx["material_frentes"] or ctx["material"],
        offset=ctx["offset"],
        material_fita=ctx["mat_fita_cx_p"],
        **ctx["pux_kw"],
    )
    return pieces, name


@register_module_builder("peca_porta_basculante")
def _build_peca_porta_basculante(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Porta Basculante {int(L)}x{int(A)}"
    pieces = cls.build_peca_avulsa(
        "porta_basculante", L, A, P,
        esp_mm=ctx["esp_mm"],
        material=ctx["material_frentes"] or ctx["material"],
        offset=ctx["offset"],
        material_fita=ctx["mat_fita_cx_p"],
        **ctx["pux_kw"],
    )
    return pieces, name


@register_module_builder("peca_frente_gaveta")
def _build_peca_frente_gaveta(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Frente Gaveta {int(L)}x{int(A)}"
    pieces = cls.build_peca_avulsa(
        "frente_gaveta", L, A, P,
        esp_mm=ctx["esp_mm"],
        material=ctx["material_frentes"] or ctx["material"],
        offset=ctx["offset"],
        material_fita=ctx["mat_fita_cx_p"],
        **ctx["pux_kw"],
    )
    return pieces, name


@register_module_builder("peca_tampo_engrossado")
def _build_peca_tampo_engrossado(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    esp_chapa = float(params.get("esp_chapa", ctx["esp_mm"]))
    qtd_engrosso = int(params.get("qtd_engrosso", 1))
    larg_engrosso = float(params.get("larg_engrosso", 70))
    tipo_engrosso = str(params.get("tipo_engrosso", "3_lados"))
    fechar_embaixo = bool(params.get("fechar_embaixo", False))
    snap_parede = str(params.get("snap_parede", "auto"))
    name = f"Tampo Engrossado {int(L)}x{int(P)} ({int(esp_chapa * (qtd_engrosso + 1))}mm)"
    pieces = cls.build_tampo_engrossado(
        largura_mm=L,
        altura_mm=A,
        prof_mm=P,
        esp_chapa_mm=esp_chapa,
        larg_engrosso_mm=larg_engrosso,
        tipo_engrosso=tipo_engrosso,
        qtd_engrosso=qtd_engrosso,
        fechar_embaixo=fechar_embaixo,
        snap_parede=snap_parede,
        material=ctx["material"],
        offset=ctx["offset"],
        material_fita=ctx["mat_fita_cx_p"],
    )
    return pieces, name


@register_module_builder("peca_prateleira")
def _build_peca_prateleira(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Prateleira {int(L)}x{int(P)}"
    pieces = cls.build_peca_avulsa(
        "prateleira", L, A, P,
        esp_mm=ctx["esp_mm"],
        material=ctx["material"],
        offset=ctx["offset"],
        material_fita=ctx["mat_fita_cx_p"],
    )
    return pieces, name


@register_module_builder("peca_prateleiras_avulsas")
def _build_peca_prateleiras_avulsas(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    n_prat = int(params.get("num_prateleiras", 2))
    has_primeira = bool(params.get("has_primeira", False))
    has_ultima = bool(params.get("has_ultima", False))
    qtd_total = n_prat + (1 if has_primeira else 0) + (1 if has_ultima else 0)
    name = f"Prateleiras Avulsas ({qtd_total} un) {int(L)}x{int(A)}x{int(P)}"
    pieces = cls.build_prateleiras_avulsas(
        largura_mm=L,
        altura_mm=A,
        prof_mm=P,
        num_prateleiras=n_prat,
        esp_mm=ctx["esp_mm"],
        has_primeira=has_primeira,
        has_ultima=has_ultima,
        material=ctx["material"],
        offset=ctx["offset"],
        material_fita=ctx["mat_fita_cx_p"],
        mat_ctx=ctx.get("mat_ctx"),
    )
    return pieces, name


@register_module_builder("peca_travessa_deitada")
def _build_peca_travessa_deitada(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Travessa Deitada {int(L)}x{int(P)}"
    pieces = cls.build_peca_avulsa(
        "travessa_deitada", L, A, P,
        esp_mm=ctx["esp_mm"],
        material=ctx["material"],
        offset=ctx["offset"],
        material_fita=ctx["mat_fita_cx_p"],
    )
    return pieces, name


@register_module_builder("peca_travessa_em_pe")
def _build_peca_travessa_em_pe(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Travessa em Pe {int(L)}x{int(A)}"
    pieces = cls.build_peca_avulsa(
        "travessa_em_pe", L, A, P,
        esp_mm=ctx["esp_mm"],
        material=ctx["material"],
        offset=ctx["offset"],
        material_fita=ctx["mat_fita_cx_p"],
    )
    return pieces, name


@register_module_builder("peca_pilar_quina")
def _build_peca_pilar_quina(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Pilar Quina {int(L)}x{int(A)}x{int(P)}"
    pieces = cls.build_peca_avulsa(
        "pilar_quina", L, A, P,
        esp_mm=ctx["esp_mm"],
        material=ctx["material"],
        offset=ctx["offset"],
        material_fita=ctx["mat_fita_cx_p"],
    )
    return pieces, name


@register_module_builder("peca_fundo")
def _build_peca_fundo(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Fundo {int(L)}x{int(A)}"
    pieces = cls.build_peca_avulsa(
        "fundo", L, A, P,
        esp_mm=ctx["esp_mm"],
        material=ctx["material"],
        offset=ctx["offset"],
        material_fita=ctx["mat_fita_cx_p"],
    )
    return pieces, name


@register_module_builder("peca_porta")
def _build_peca_porta(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Porta/Frente {int(L)}x{int(A)}"
    pieces = cls.build_peca_avulsa(
        "porta", L, A, P,
        esp_mm=ctx["esp_mm"],
        material=ctx["material_frentes"] or ctx["material"],
        offset=ctx["offset"],
        material_fita=ctx["mat_fita_cx_p"],
        lado_abertura_porta=params.get("lado_abertura_porta", "esquerda"),
        **ctx["pux_kw"],
    )
    return pieces, name


@register_module_builder("peca_portas_correr")
def _build_peca_portas_correr(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    n_portas = max(2, min(4, int(params.get("num_portas", 2))))
    transpasse = float(params.get("transpasse_mm", 30.0))
    esp_folha = float(ctx["esp_frentes_mm"] or ctx["esp_mm"])
    name = f"Portas Correr ({n_portas}P) {int(L)}x{int(A)}"
    pieces = cls.build_portas_correr_avulsas(
        L, A, P,
        num_portas=n_portas,
        esp_mm=esp_folha,
        transpasse_mm=transpasse,
        material=ctx["material_frentes"] or ctx["material"],
        material_fita=ctx["mat_fita_cx_p"],
        offset=ctx["offset"],
        **ctx["pux_kw"],
    )
    return pieces, name


@register_module_builder("rodape_fechado")
def _build_rodape_fechado(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Rodapé Fechado {int(L)}x{int(A)}x{int(P)}"
    recuo_frontal = float(params.get("recuo_frontal_mm", params.get("recuo_frontal", 30.0)))
    larg_trav_topo = float(params.get("larg_travessa_topo_mm", params.get("larg_travessa_topo", 70.0)))
    pieces = cls.build_rodape_fechado(
        largura_mm=L,
        altura_mm=A,
        prof_mm=P,
        esp_mm=ctx["esp_mm"],
        larg_travessa_topo_mm=larg_trav_topo,
        recuo_frontal_mm=recuo_frontal,
        material=ctx["material"],
        offset=ctx["offset"],
        material_fita=ctx["mat_fita_cx_p"],
    )
    return pieces, name


@register_module_builder("armario_maleiro_tamponado")
def _build_armario_maleiro_tamponado(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    n_caixas = int(params.get("num_caixas", params.get("num_vaos", 2)))
    modo_caixaria = str(params.get("modo_caixaria", "isoladas"))
    name = f"Armário Maleiro Tamponado {n_caixas} Caixas {int(L)}x{int(A)}x{int(P)}"
    pieces = cls.build_armario_maleiro_tamponado(
        largura_mm=L,
        altura_mm=A,
        prof_mm=P,
        num_caixas=n_caixas,
        modo_caixaria=modo_caixaria,
        esp_mm=ctx["esp_mm"],
        esp_tamponamento_mm=float(params.get("esp_tamponamento_mm", 18.0)),
        recuo_portas_correr_mm=float(params.get("recuo_portas_correr_mm", 70.0)),
        rodape_mm=ctx["rodape_mm"],
        recuo_rodape_mm=float(params.get("recuo_rodape_mm", 30.0)),
        alt_maleiro_mm=float(params.get("alt_maleiro_mm", 400.0)),
        material=ctx["material"],
        material_tamponamento=params.get("material_tamponamento") or ctx["material"],
        tipo_fundo=ctx["fundo_kwargs"].get("tipo_fundo", "rasgo"),
        esp_fundo_mm=ctx["fundo_kwargs"].get("esp_fundo_mm", 6.0),
        recuo_fundo_mm=ctx["fundo_kwargs"].get("recuo_fundo_mm", 10.0),
        offset=ctx["offset"],
        mat_ctx=ctx.get("mat_ctx"),
    )
    return pieces, name


# -------------------------------------------------------------------------
# Camas Planejadas
# -------------------------------------------------------------------------
@register_module_builder("cama_gaveteiros")
def _build_cama_gaveteiros(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Cama Plataforma com Gaveteiros {int(L)}x{int(P)}x{int(A)}"
    pieces = cls.build_cama_gaveteiros(
        largura_mm=L,
        prof_mm=P,
        altura_mm=A,
        esp_mm=ctx["esp_mm"],
        num_gavetoes=params.get("num_gavetas", 4),
        lado_gavetas=params.get("lado_gavetas", "ambos"),
        material=ctx["material"],
        material_frentes=ctx.get("material_frentes"),
        mat_ctx=ctx.get("mat_ctx"),
        offset=ctx["offset"],
    )
    return pieces, name


@register_module_builder("cama_bau")
def _build_cama_bau(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Cama Baú com Pistões {int(L)}x{int(P)}x{int(A)}"
    pieces = cls.build_cama_bau(
        largura_mm=L,
        prof_mm=P,
        altura_mm=A,
        esp_mm=ctx["esp_mm"],
        esp_fundo_mm=ctx["fundo_kwargs"].get("esp_fundo_mm", 6.0),
        material=ctx["material"],
        material_frentes=ctx.get("material_frentes"),
        mat_ctx=ctx.get("mat_ctx"),
        offset=ctx["offset"],
    )
    return pieces, name


@register_module_builder("cama_cabeceira")
def _build_cama_cabeceira(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Cama com Cabeceira Estendida {int(L)}x{int(P)}x{int(A)}"
    pieces = cls.build_cama_cabeceira(
        largura_mm=L,
        prof_mm=P,
        altura_mm=A,
        esp_mm=ctx["esp_mm"],
        material=ctx["material"],
        material_frentes=ctx.get("material_frentes"),
        mat_ctx=ctx.get("mat_ctx"),
        offset=ctx["offset"],
        larg_cama_mm=params.get("larg_cama"),
        alt_cama_mm=params.get("alt_cama"),
    )
    return pieces, name


@register_module_builder("bicama")
def _build_bicama(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Bicama Solteiro com Auxiliar {int(L)}x{int(P)}x{int(A)}"
    pieces = cls.build_bicama(
        largura_mm=L,
        prof_mm=P,
        altura_mm=A,
        esp_mm=ctx["esp_mm"],
        material=ctx["material"],
        material_frentes=ctx.get("material_frentes"),
        mat_ctx=ctx.get("mat_ctx"),
        offset=ctx["offset"],
    )
    return pieces, name


@register_module_builder("beliche")
def _build_beliche(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Beliche Planejado {int(L)}x{int(P)}x{int(A)}"
    pieces = cls.build_beliche(
        largura_mm=L,
        prof_mm=P,
        altura_mm=A,
        esp_mm=ctx["esp_mm"],
        material=ctx["material"],
        material_frentes=ctx.get("material_frentes"),
        mat_ctx=ctx.get("mat_ctx"),
        offset=ctx["offset"],
        alt_leito_sup_mm=params.get("alt_leito_sup"),
    )
    return pieces, name


@register_module_builder("cama_colmeia")
def _build_cama_colmeia(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    name = f"Cama Colmeia Estrutural {int(L)}x{int(P)}x{int(A)}"
    pieces = cls.build_cama_colmeia(
        largura_mm=L,
        prof_mm=P,
        altura_mm=A,
        esp_mm=ctx["esp_mm"],
        material=ctx["material"],
        material_frentes=ctx.get("material_frentes"),
        mat_ctx=ctx.get("mat_ctx"),
        offset=ctx["offset"],
        rodape_mm=float(params.get("rodape") or 60.0),
        recuo_rodape_mm=float(params.get("recuo_rodape") or 100.0),
        num_longarinas=params.get("num_longarinas"),
        num_travessas=params.get("num_travessas"),
        altura_aba_mm=float(params.get("altura_aba", 50.0)),
        tipo_apoio=str(params.get("tipo_apoio", "rodape")),
        alt_apoio_mm=float(params.get("alt_apoio", 100.0)),
        vao_colmeia_mm=float(params.get("vao_colmeia", 300.0)),
        tem_colchao=bool(params.get("tem_colchao", False)),
        gerar_furacao=bool(params.get("gerar_furacao", True)),
        dispositivo_fixacao=str(params.get("dispositivo_fixacao", "cavilha_soberba")),
    )
    return pieces, name


@register_module_builder("peca_tamponamento_linha")
def _build_tamponamento_linha(cls, params: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[List[Group], str]:
    L, A, P = ctx["L_mm"], ctx["A_mm"], ctx["P_mm"]
    tipo_env = params.get("tipo_envoltorio", "u_completo")
    name = f"Tamponamento de Linha ({tipo_env}) {int(L)}x{int(A)}x{int(P)}"
    pieces = cls.build_tamponamento_linha(
        largura_mm=L,
        altura_mm=A,
        prof_mm=P,
        esp_mm=float(params.get("espessura_tampo_mm", params.get("espessura", 18.0))),
        esp_lateral_mm=float(params.get("espessura_lateral_mm", params.get("espessura", 18.0))),
        tipo_envoltorio=tipo_env,
        material=ctx["material"],
        material_fita=params.get("material_fita"),
        recuo_frontal_mm=float(params.get("recuo_frontal_mm", 0.0)),
        sobra_frontal_mm=float(params.get("sobra_frontal_mm", 20.0)),
        offset=ctx["offset"],
        mat_ctx=ctx.get("mat_ctx"),
    )
    return pieces, name

