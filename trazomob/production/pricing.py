# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Motor de precificação e orçamento do TrazoMob (Onda 3).

Calcula custo direto, markup, impostos, desconto e frete a partir da cutlist
e das preferências de preço do usuário. Gera estrutura de dados pronta para
o relatório de proposta PDF/HTML.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..domain.preferences import TrazoMobPreferencesManager, get_preferences_file_path


@dataclass
class ItemCusto:
    """Linha de custo detalhada."""
    descricao: str
    quantidade: float
    unidade: str
    preco_unitario: float
    total: float
    categoria: str  # "chapa" | "fita" | "ferragem" | "mao_de_obra" | "frete"


@dataclass
class ResumoOrcamento:
    """Resumo consolidado do orçamento."""
    custo_direto: float = 0.0
    custo_chapas: float = 0.0
    custo_fitas: float = 0.0
    custo_ferragens: float = 0.0
    custo_servicos: float = 0.0
    custo_mao_obra: float = 0.0
    custo_montagem: float = 0.0
    markup_valor: float = 0.0
    subtotal_com_markup: float = 0.0
    impostos_valor: float = 0.0
    desconto_valor: float = 0.0
    frete_valor: float = 0.0
    total_final: float = 0.0
    total_a_vista: float = 0.0
    total_parcelado: float = 0.0
    num_parcelas: int = 1
    valor_parcela: float = 0.0
    linha_ferragem: str = "standard"
    itens: List[ItemCusto] = field(default_factory=list)
    itens_sem_preco: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "custo_direto": round(self.custo_direto, 2),
            "custo_chapas": round(self.custo_chapas, 2),
            "custo_fitas": round(self.custo_fitas, 2),
            "custo_ferragens": round(self.custo_ferragens, 2),
            "custo_servicos": round(self.custo_servicos, 2),
            "custo_mao_obra": round(self.custo_mao_obra, 2),
            "custo_montagem": round(self.custo_montagem, 2),
            "markup_valor": round(self.markup_valor, 2),
            "subtotal_com_markup": round(self.subtotal_com_markup, 2),
            "impostos_valor": round(self.impostos_valor, 2),
            "desconto_valor": round(self.desconto_valor, 2),
            "frete_valor": round(self.frete_valor, 2),
            "total_final": round(self.total_final, 2),
            "total_a_vista": round(self.total_a_vista, 2),
            "total_parcelado": round(self.total_parcelado, 2),
            "num_parcelas": self.num_parcelas,
            "valor_parcela": round(self.valor_parcela, 2),
            "linha_ferragem": self.linha_ferragem,
            "itens_sem_preco": list(self.itens_sem_preco),
            "itens": [
                {
                    "descricao": i.descricao,
                    "quantidade": round(i.quantidade, 3),
                    "unidade": i.unidade,
                    "preco_unitario": round(i.preco_unitario, 2),
                    "total": round(i.total, 2),
                    "categoria": i.categoria,
                }
                for i in self.itens
            ],
        }


def _normalizar_material(mat: str) -> str:
    """Normaliza nome do material para chave de lookup."""
    mat = mat.strip()
    # Remove o sufixo de textura "TX" (ex.: "MDF Branco TX" -> "MDF Branco")
    if mat.endswith("TX"):
        mat = mat[:-2].strip()
    return mat


def _get_chapa_preco_flexivel(chapas_precos: Dict[str, float], material: str, espessura: float) -> float:
    """Busca preço de chapa com múltiplas estratégias de chave."""
    # 1. Chave exata como vem do builder: "Material Espessuramm"
    key1 = f"{material} {espessura:.0f}mm"
    if key1 in chapas_precos:
        return chapas_precos[key1]

    # 2. Chave normalizada (sem TX)
    mat_norm = _normalizar_material(material)
    key2 = f"{mat_norm} {espessura:.0f}mm"
    if key2 in chapas_precos:
        return chapas_precos[key2]

    # 3. Busca parcial por material: exige que TODAS as palavras do material
    # coincidam com as palavras da chave. O critério antigo (primeiro token,
    # geralmente "MDF") fazia "MDF Louro Freijó" cair no preço de "MDF Branco".
    alvo_tokens = set(mat_norm.lower().split())
    for k, v in chapas_precos.items():
        if f"{espessura:.0f}mm" not in k:
            continue
        base = re.sub(r"\s*\d+(?:[.,]\d+)?\s*mm\s*$", "", k).strip()
        base_tokens = set(base.lower().split())
        if not alvo_tokens or not base_tokens:
            continue
        if alvo_tokens.issubset(base_tokens) or base_tokens.issubset(alvo_tokens):
            return v

    return 0.0


def _get_fita_preco_flexivel(fita_precos: Dict[str, float], espessura_fita: float) -> float:
    """Busca preço de fita com múltiplas estratégias de chave."""
    # 1. Chave com vírgula (formato brasileiro)
    key1 = f"{espessura_fita:.2f}mm".replace(".", ",")
    if key1 in fita_precos:
        return fita_precos[key1]

    # 2. Chave com ponto
    key2 = f"{espessura_fita:.2f}mm"
    if key2 in fita_precos:
        return fita_precos[key2]

    # 3. Busca por prefixo
    for k, v in fita_precos.items():
        if k.startswith(f"{espessura_fita:.0f}"):
            return v

    return 0.0


def _normalizar_texto(texto: Any) -> str:
    """Minúsculas e sem acentos, para casar nomes de peça de forma robusta."""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower()


def _contem_palavra(texto: str, *palavras: str) -> bool:
    """Casa palavras inteiras (evita "pes" casar com "pessoal"/"compesso")."""
    return any(re.search(rf"\b{re.escape(p)}\b", texto) for p in palavras)


def _num_dobradicas(altura_mm: float) -> int:
    """Número de dobradiças por porta em função da altura (regra usual de mercado)."""
    if altura_mm <= 900:
        return 2
    if altura_mm <= 1600:
        return 3
    if altura_mm <= 2100:
        return 4
    return 5


def _inferir_ferragens_peca(part: Dict[str, Any]) -> Dict[str, int]:
    """Infere ferragens de uma peça avulsa a partir do nome e das dimensões.

    Usado apenas como *fallback* quando a peça não traz as ferragens do módulo
    (``module_hardware``). O casamento por palavras inteiras e sem acentos evita
    falsos positivos (ex.: "pes" dentro de "pessoal") e a contagem de dobradiças
    considera a altura da porta.
    """
    nome = _normalizar_texto(part.get("nome", ""))
    qtd = int(part.get("quantidade", 1) or 1)
    altura = max(
        float(part.get("comprimento", 0.0) or 0.0),
        float(part.get("largura", 0.0) or 0.0),
    )

    ferragens = {
        "puxador_perfil": 0,
        "puxador_ponto": 0,
        "puxador_embutido": 0,
        "dobradica_35mm": 0,
        "corredica_telescopica_40": 0,
        "corredica_telescopica_50": 0,
        "minifix_cavilha_kit": 0,
        "parafuso_confirmat": 0,
        "pes_nivelador": 0,
    }

    if _contem_palavra(nome, "porta"):
        ferragens["dobradica_35mm"] += _num_dobradicas(altura) * qtd
        ferragens["puxador_perfil"] += qtd
    elif _contem_palavra(nome, "gaveta"):
        ferragens["corredica_telescopica_40"] += qtd
        ferragens["puxador_ponto"] += qtd
    elif _contem_palavra(nome, "prateleira"):
        ferragens["minifix_cavilha_kit"] += 4 * qtd  # 4 suportes por prateleira
    elif _contem_palavra(nome, "lateral", "base", "tampo", "travessa"):
        ferragens["minifix_cavilha_kit"] += 4 * qtd
        ferragens["parafuso_confirmat"] += 8 * qtd
    elif _contem_palavra(nome, "pe", "pes", "rodape"):
        ferragens["pes_nivelador"] += qtd

    return ferragens


def _calcular_fita_metros(part: Dict[str, Any]) -> float:
    """Calcula metros lineares de fita de borda para uma peça."""
    qtd = part.get("quantidade", 1)
    comp_m = part.get("comprimento", 0.0) / 1000.0
    larg_m = part.get("largura", 0.0) / 1000.0

    metros = 0.0
    if part.get("fita_c1"):
        metros += comp_m
    if part.get("fita_c2"):
        metros += comp_m
    if part.get("fita_l1"):
        metros += larg_m
    if part.get("fita_l2"):
        metros += larg_m

    return metros * qtd


def calcular_orcamento_cutlist(
    parts: List[Dict[str, Any]],
    incluir_frete: bool = True,
    linha_ferragem_override: Optional[str] = None,
) -> ResumoOrcamento:
    """
    Calcula orçamento completo a partir da cutlist (lista de peças).

    Suporta:
    - Modo de chapas: 'm2_perda' (área líquida + % de perda) ou 'inteira' (por chapa da revenda)
    - Linhas de ferragem: 'economica', 'standard' ou 'premium'
    - Modo de formação: 'detalhado' ou 'multiplicador'
    - Serviços de central de corte terceirizada e montagem
    - Destaque de itens sem preço cadastrado
    """
    prefs = TrazoMobPreferencesManager.get_instance()
    pricing = prefs.get_pricing_config()

    # Parâmetros gerais
    modo_calculo_chapas = pricing.get("modo_calculo_chapas", "m2_perda")
    perda_chapa_pct = pricing.get("perda_chapa_percent", 0.15)
    chapa_dim = pricing.get("chapa_padrao_dim", [2750.0, 1850.0])
    area_chapa_inteira_m2 = (float(chapa_dim[0]) / 1000.0) * (float(chapa_dim[1]) / 1000.0)
    if area_chapa_inteira_m2 <= 0.1:
        area_chapa_inteira_m2 = 5.0875

    modo_fechamento = pricing.get("modo_fechamento", "detalhado")
    fator_mult = pricing.get("fator_multiplicador", 2.80)

    markup = pricing.get("markup", 1.35)
    impostos_pct = pricing.get("impostos_percent", 0.18)
    desconto_pct = pricing.get("desconto_percent", 0.05)
    frete_tipo = pricing.get("frete_tipo", "fixo")
    frete_valor = pricing.get("frete_valor", 150.00)
    mao_obra_m2 = pricing.get("mao_de_obra_m2", 45.00)

    # Linha de ferragem
    linha_ativa = linha_ferragem_override or pricing.get("linha_ferragem_ativa", "standard")
    mult_linhas = pricing.get("linhas_ferragens_multiplicador", {
        "economica": 0.75, "standard": 1.0, "premium": 2.2
    })
    fator_linha = mult_linhas.get(linha_ativa, 1.0)

    # Serviços e Montagem
    servico_corte_chapa = pricing.get("servico_corte_por_chapa", 35.00)
    servico_fita_m = pricing.get("servico_fita_por_metro", 3.50)
    montagem_tipo = pricing.get("montagem_tipo", "percentual")
    montagem_valor = pricing.get("montagem_valor", 0.12)

    chapas_precos = pricing.get("chapas_m2", {})
    chapas_inteiras_precos = pricing.get("chapas_inteiras", {})
    fita_precos = pricing.get("fita_borda_m", {})
    ferragens_precos = pricing.get("ferragens", {})

    # Agregadores
    chapa_area: Dict[str, Dict[str, Any]] = {}
    fita_metros: Dict[float, Dict[str, float]] = {}
    custo_chapas = 0.0
    custo_fitas = 0.0
    custo_ferragens = 0.0
    custo_servicos = 0.0
    total_area_liquida_m2 = 0.0
    total_fita_m = 0.0
    ferragens_count: Dict[str, int] = {}
    seen_modules: set = set()
    itens_sem_preco: set = set()

    # 1. Processa peças da cutlist
    for part in parts:
        qtd = part.get("quantidade", 1)
        mat_raw = part.get("material", "MDF Branco TX")
        esp = part.get("espessura", 15.0)
        comp_m = part.get("comprimento", 0.0) / 1000.0
        larg_m = part.get("largura", 0.0) / 1000.0
        area_m2 = comp_m * larg_m * qtd
        total_area_liquida_m2 += area_m2

        # Identificador do material da chapa
        if str(esp).rstrip("0").rstrip(".") + "mm" in mat_raw or f"{esp:.0f}mm" in mat_raw:
            mat_desc = mat_raw
        else:
            mat_desc = f"{mat_raw} {esp:.0f}mm"

        preco_m2 = _get_chapa_preco_flexivel(chapas_precos, mat_raw, esp)
        preco_inteira = chapas_inteiras_precos.get(mat_desc, 0.0)
        if preco_inteira <= 0 and preco_m2 > 0:
            preco_inteira = preco_m2 * area_chapa_inteira_m2
        elif preco_m2 <= 0 and preco_inteira > 0:
            preco_m2 = preco_inteira / area_chapa_inteira_m2

        if preco_m2 <= 0:
            itens_sem_preco.add(f"Chapa: {mat_desc}")

        entry_c = chapa_area.setdefault(mat_desc, {
            "area_liquida": 0.0,
            "preco_m2": preco_m2,
            "preco_inteira": preco_inteira,
        })
        entry_c["area_liquida"] += area_m2

        # Fitas de borda
        fita_m = _calcular_fita_metros(part)
        total_fita_m += fita_m
        esp_fita = float(part.get("espessura_fita", 0.45))
        preco_fita = _get_fita_preco_flexivel(fita_precos, esp_fita)
        if preco_fita <= 0 and fita_m > 0:
            itens_sem_preco.add(f"Fita: {esp_fita:.2f}mm")

        if fita_m > 0:
            entry_f = fita_metros.setdefault(esp_fita, {"metros": 0.0, "preco": preco_fita})
            entry_f["metros"] += fita_m

        # Ferragens consolidadas
        mod_key = part.get("_module_key")
        module_hw = part.get("module_hardware") or []
        if mod_key is not None and module_hw and mod_key not in seen_modules:
            seen_modules.add(mod_key)
            from ..domain.hardware import (
                consolidate_hardware,
                deserialize_hardware,
            )
            cons = consolidate_hardware([(mod_key, deserialize_hardware(module_hw))])
            for f_key, f_data in cons.items():
                f_qtd = int(f_data.get("quantidade", 0) or 0)
                if f_qtd > 0:
                    ferragens_count[f_key] = ferragens_count.get(f_key, 0) + f_qtd
        elif mod_key is None:
            ferragens_peca = _inferir_ferragens_peca(part)
            for f_key, f_qtd in ferragens_peca.items():
                if f_qtd > 0:
                    ferragens_count[f_key] = ferragens_count.get(f_key, 0) + f_qtd

    itens: List[ItemCusto] = []
    total_chapas_compradas = 0

    # 2. Consolidação de Chapas
    for desc, c_data in chapa_area.items():
        area_liq = c_data["area_liquida"]
        p_unit_m2 = c_data["preco_m2"]
        p_unit_int = c_data["preco_inteira"]
        if p_unit_m2 <= 0 and p_unit_int <= 0:
            continue

        if modo_calculo_chapas == "inteira":
            # Número inteiro de chapas da revenda
            qtd_chapas = max(1, math.ceil(area_liq / area_chapa_inteira_m2))
            total_chapas_compradas += qtd_chapas
            p_unit = p_unit_int
            total_item = qtd_chapas * p_unit
            custo_chapas += total_item
            itens.append(ItemCusto(
                descricao=f"Chapas Inteiras: {desc} (2750x1850mm)",
                quantidade=float(qtd_chapas),
                unidade="chapa",
                preco_unitario=round(p_unit, 2),
                total=round(total_item, 2),
                categoria="chapa",
            ))
        else:
            # m² com fator de perda
            fator_perda_val = max(0.0, float(perda_chapa_pct))
            area_faturada = area_liq * (1.0 + fator_perda_val)
            p_unit = p_unit_m2
            total_item = area_faturada * p_unit
            custo_chapas += total_item
            total_chapas_compradas += math.ceil(area_faturada / area_chapa_inteira_m2)
            lbl_desc = f"Chapa: {desc}" if fator_perda_val <= 0 else f"Chapa: {desc} (com {fator_perda_val*100:.0f}% perda)"
            itens.append(ItemCusto(
                descricao=lbl_desc,
                quantidade=round(area_faturada, 3),
                unidade="m²",
                preco_unitario=round(p_unit, 2),
                total=round(total_item, 2),
                categoria="chapa",
            ))

    # 3. Consolidação de Fitas
    for esp_fita, f_data in sorted(fita_metros.items()):
        metros = f_data["metros"]
        preco_u = f_data["preco"]
        total_f = metros * preco_u
        custo_fitas += total_f
        itens.append(ItemCusto(
            descricao=f"Fita de Borda {esp_fita:.2f}mm".replace(".", ","),
            quantidade=round(metros, 2),
            unidade="m",
            preco_unitario=round(preco_u, 2),
            total=round(total_f, 2),
            categoria="fita",
        ))

    # 4. Consolidação de Ferragens (aplicando multiplicador da linha)
    for f_key, f_qtd in ferragens_count.items():
        p_base = ferragens_precos.get(f_key, 0.0)
        p_ajustado = p_base * fator_linha
        if p_ajustado <= 0:
            itens_sem_preco.add(f"Ferragem: {f_key}")
        total_hw = f_qtd * p_ajustado
        custo_ferragens += total_hw
        nome_amigavel = f_key.replace("_", " ").title()
        itens.append(ItemCusto(
            descricao=f"Ferragem ({linha_ativa.title()}): {nome_amigavel}",
            quantidade=float(f_qtd),
            unidade="un",
            preco_unitario=round(p_ajustado, 2),
            total=round(total_hw, 2),
            categoria="ferragem",
        ))

    # 5. Serviços terceirizados de corte e colagem de fita
    if servico_corte_chapa > 0 and total_chapas_compradas > 0:
        custo_corte = total_chapas_compradas * servico_corte_chapa
        custo_servicos += custo_corte
        itens.append(ItemCusto(
            descricao="Serviço: Corte por chapa (Central)",
            quantidade=float(total_chapas_compradas),
            unidade="chapa",
            preco_unitario=round(servico_corte_chapa, 2),
            total=round(custo_corte, 2),
            categoria="servico",
        ))
    if servico_fita_m > 0 and total_fita_m > 0:
        custo_colagem = total_fita_m * servico_fita_m
        custo_servicos += custo_colagem
        itens.append(ItemCusto(
            descricao="Serviço: Colagem de fita de borda (Central)",
            quantidade=round(total_fita_m, 2),
            unidade="m",
            preco_unitario=round(servico_fita_m, 2),
            total=round(custo_colagem, 2),
            categoria="servico",
        ))

    # 6. Mão de Obra de Fabricação
    custo_mao_obra = total_area_liquida_m2 * mao_obra_m2
    if custo_mao_obra > 0:
        itens.append(ItemCusto(
            descricao="Mão de obra de oficina / fabricação",
            quantidade=round(total_area_liquida_m2, 2),
            unidade="m²",
            preco_unitario=round(mao_obra_m2, 2),
            total=round(custo_mao_obra, 2),
            categoria="mao_de_obra",
        ))

    # 7. Custo Direto Total
    custo_direto = custo_chapas + custo_fitas + custo_ferragens + custo_servicos + custo_mao_obra

    # 8. Montagem / Instalação
    custo_montagem = 0.0
    if montagem_tipo == "percentual" and montagem_valor > 0:
        custo_montagem = custo_direto * montagem_valor
    elif montagem_tipo == "por_m2" and montagem_valor > 0:
        custo_montagem = total_area_liquida_m2 * montagem_valor
    elif montagem_tipo == "fixo" and montagem_valor > 0:
        custo_montagem = montagem_valor

    if custo_montagem > 0:
        itens.append(ItemCusto(
            descricao="Instalação e montagem no local",
            quantidade=1.0,
            unidade="un",
            preco_unitario=round(custo_montagem, 2),
            total=round(custo_montagem, 2),
            categoria="montagem",
        ))

    # 9. Formação do Preço de Venda
    if modo_fechamento == "multiplicador":
        # Multiplicador simples sobre insumos materiais
        custo_materiais = custo_chapas + custo_fitas + custo_ferragens
        subtotal_com_markup = (custo_materiais * fator_mult) + custo_servicos + custo_montagem
        markup_valor = max(0.0, subtotal_com_markup - custo_direto)
    else:
        # Composição detalhada com Markup e Impostos
        base_markup = custo_direto + custo_montagem
        markup_valor = base_markup * (markup - 1.0)
        subtotal_com_markup = base_markup + markup_valor

    impostos_valor = subtotal_com_markup * impostos_pct
    subtotal_com_impostos = subtotal_com_markup + impostos_valor
    desconto_valor = subtotal_com_impostos * desconto_pct
    total_com_desconto = subtotal_com_impostos - desconto_valor

    # Frete
    if not incluir_frete:
        frete_calculado = 0.0
    elif frete_tipo == "por_m2":
        frete_calculado = total_area_liquida_m2 * frete_valor
    else:
        frete_calculado = frete_valor

    if frete_calculado > 0:
        itens.append(ItemCusto(
            descricao="Frete / Logística",
            quantidade=1.0,
            unidade="un",
            preco_unitario=round(frete_calculado, 2),
            total=round(frete_calculado, 2),
            categoria="frete",
        ))

    # ``total_final`` já contempla o desconto (aplicado uma única vez em
    # ``desconto_valor``) e representa o preço à vista. O parcelamento parte do
    # valor sem o desconto à vista, para que o benefício do pagamento à vista
    # apareça de forma explícita (sem aplicar o desconto duas vezes).
    total_final = total_com_desconto + frete_calculado
    total_a_vista = total_final
    total_parcelado = total_final + desconto_valor

    num_parcelas = int(pricing.get("parcelas_sem_juros", 6) or 6)
    if num_parcelas < 1:
        num_parcelas = 1
    valor_parcela = total_parcelado / num_parcelas

    return ResumoOrcamento(
        custo_direto=round(custo_direto, 2),
        custo_chapas=round(custo_chapas, 2),
        custo_fitas=round(custo_fitas, 2),
        custo_ferragens=round(custo_ferragens, 2),
        custo_servicos=round(custo_servicos, 2),
        custo_mao_obra=round(custo_mao_obra, 2),
        custo_montagem=round(custo_montagem, 2),
        markup_valor=round(markup_valor, 2),
        subtotal_com_markup=round(subtotal_com_markup, 2),
        impostos_valor=round(impostos_valor, 2),
        desconto_valor=round(desconto_valor, 2),
        frete_valor=round(frete_calculado, 2),
        total_final=round(total_final, 2),
        total_a_vista=round(total_a_vista, 2),
        total_parcelado=round(total_parcelado, 2),
        num_parcelas=num_parcelas,
        valor_parcela=round(valor_parcela, 2),
        linha_ferragem=linha_ativa,
        itens=itens,
        itens_sem_preco=sorted(itens_sem_preco),
    )


def agrupar_por_ambiente(parts: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Agrupa peças pela chave ``"Ambiente (Pavimento)"``.

    Fonte única de verdade do agrupamento por ambiente, usada tanto pelo cálculo
    quanto pela interface — evitando que a UI remonte os grupos por substring.
    """
    from collections import defaultdict

    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for p in parts:
        amb = p.get("ambiente") or "Ambiente Geral"
        pav = p.get("pavimento") or "Térreo"
        key = f"{amb} ({pav})" if pav else amb
        groups[key].append(p)
    return dict(groups)


def calcular_orcamento_por_ambiente(parts: List[Dict[str, Any]]) -> Dict[str, ResumoOrcamento]:
    """
    Calcula orçamento separado por ambiente/pavimento.
    Retorna dict { "Ambiente (Pavimento)": ResumoOrcamento }.
    """
    groups = agrupar_por_ambiente(parts)
    return {
        amb_key: calcular_orcamento_cutlist(amb_parts, incluir_frete=False)
        for amb_key, amb_parts in groups.items()
    }


def formatar_moeda(valor: float) -> str:
    """Formata valor como moeda brasileira."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_proposta_dados(
    parts: List[Dict[str, Any]],
    project_name: str = "Projeto TrazoMob",
    client_name: str = "Cliente",
    client_data: Optional[Dict[str, str]] = None,
    observacoes: str = "",
) -> Dict[str, Any]:
    """
    Gera estrutura completa de dados para proposta (PDF/HTML).
    Inclui orçamento geral, por ambiente, dados da empresa e cliente.
    """
    prefs = TrazoMobPreferencesManager.get_instance()
    empresa = prefs.get_empresa_config()

    orcamento_geral = calcular_orcamento_cutlist(parts)
    orcamento_por_amb = calcular_orcamento_por_ambiente(parts)

    # Estatísticas gerais
    total_pecas = sum(p.get("quantidade", 1) for p in parts)
    total_area_m2 = sum(
        (p.get("comprimento", 0) / 1000.0) * (p.get("largura", 0) / 1000.0) * p.get("quantidade", 1)
        for p in parts
    )
    total_fita_m = sum(_calcular_fita_metros(p) for p in parts)

    from datetime import datetime
    data_emissao = datetime.now().strftime("%d/%m/%Y")
    validade = 30  # dias

    return {
        "projeto": project_name,
        "cliente": client_name,
        "cliente_dados": client_data or {},
        "data_emissao": data_emissao,
        "validade_dias": validade,
        "observacoes": observacoes,
        "empresa": empresa,
        "estatisticas": {
            "total_pecas": total_pecas,
            "total_area_m2": round(total_area_m2, 2),
            "total_fita_m": round(total_fita_m, 1),
            "num_ambientes": len(orcamento_por_amb),
        },
        "orcamento_geral": orcamento_geral.to_dict(),
        "orcamento_por_ambiente": {
            k: v.to_dict() for k, v in orcamento_por_amb.items()
        },
        "itens_detalhados": orcamento_geral.itens,  # para compatibilidade
    }
