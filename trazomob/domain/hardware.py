# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Modelo de dados de ferragens para módulos TrazoMob.

Fornece:

* ``HardwareItem`` — um item de ferragem (dobradiça, trilho, corrediça, puxador,
  fixação etc.) com código estável, tipo, nome, quantidade e preço unitário.
* ``infer_module_hardware(params)`` — infere a lista de ferragens de um módulo a
  partir dos seus parâmetros (nº de portas, gavetas, portas de correr, tipo de
  puxador, profundidade etc.). É a origem automática dos dados.
* Serialização para/deserialização de dicionários, gravada em
  ``group.ext["trazomob_hardware"]`` para sobreviver a reaberturas/edições.
* Agregação de contagens para relatórios e orçamento, substituindo a heurística
  por nome da peça usada anteriormente em ``production/pricing.py`` e
  ``production/report.py``.

Regra: código novo lê/grava ferragens por aqui. Ler ``group.ext`` direto ou
inferir ferragens pelo nome da peça produz resultados inconsistentes entre
cutlist, orçamento e relatório.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple


# Código estável -> (tipo, nome amigável, preço unitário padrão em R$)
# O tipo controla a seção do relatório: dobradiça | trilho | corredica | puxador | fixacao | outro
HARDWARE_CATALOG: Dict[str, Dict[str, Any]] = {
    "dobradica_35mm": {
        "tipo": "dobradica",
        "nome": "Dobradiça 35mm (caneco)",
        "preco": 3.50,
    },
    "calco_dobradica": {
        "tipo": "dobradica",
        "nome": "Calço de Dobradiça",
        "preco": 1.20,
    },
    "trilho_correr": {
        "tipo": "trilho",
        "nome": "Trilho Superior para Porta de Correr",
        "preco": 28.00,
    },
    "roldana_correr": {
        "tipo": "trilho",
        "nome": "Roldana / Guias para Porta de Correr",
        "preco": 7.50,
    },
    "corredica_40": {
        "tipo": "corredica",
        "nome": "Corrediça Telescópica 400 mm",
        "preco": 18.00,
    },
    "corredica_50": {
        "tipo": "corredica",
        "nome": "Corrediça Telescópica 500 mm",
        "preco": 22.00,
    },
    "puxador_perfil": {
        "tipo": "puxador",
        "nome": "Puxador Perfil de Alumínio",
        "preco": 12.00,
    },
    "puxador_ponto": {
        "tipo": "puxador",
        "nome": "Puxador Ponto / Botão",
        "preco": 8.00,
    },
    "puxador_embutido": {
        "tipo": "puxador",
        "nome": "Puxador Embutido (Cava)",
        "preco": 15.00,
    },
    "minifix_kit": {
        "tipo": "fixacao",
        "nome": "Kit Minifix + Cavilha",
        "preco": 4.00,
    },
    "parafuso_confirmat": {
        "tipo": "fixacao",
        "nome": "Parafuso Confirmat",
        "preco": 0.60,
    },
    "pino_cavilha_8": {
        "tipo": "fixacao",
        "nome": "Pino / Cavilha Ø8 mm",
        "preco": 0.40,
    },
    "pes_nivelador": {
        "tipo": "outro",
        "nome": "Pé Nivelador",
        "preco": 5.00,
    },
    "kit_porta_tempero_aramado": {
        "tipo": "outro",
        "nome": "Kit Porta-Tempero Aramado Telescópico",
        "preco": 140.00,
    },
}

# Mapeia tipo de puxador salvo nos parâmetros para a chave do catálogo.
_PUXADOR_KEY: Dict[str, Optional[str]] = {
    "alca": "puxador_ponto",
    "perfil": "puxador_perfil",
    "cava": "puxador_embutido",
    "ponto": "puxador_ponto",
    "sem_puxador": None,
    "toque": None,
    "nenhum": None,
}

# Nº de dobradiças por porta conforme a altura (padrão marcenaria).
_DOBRA_POR_ALTURA: List[Tuple[float, int]] = [
    (2100.0, 5),
    (1600.0, 4),
    (900.0, 3),
    (0.0, 2),
]


@dataclass
class HardwareItem:
    """Um item de ferragem."""

    key: str
    tipo: str
    nome: str
    quantidade: int = 1
    preco_unitario: float = 0.0
    posicao: Optional[Dict[str, Any]] = None
    visivel_3d: bool = True

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["preco_unitario"] = round(float(self.preco_unitario or 0.0), 2)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HardwareItem":
        return cls(
            key=str(data.get("key", "")),
            tipo=str(data.get("tipo", "outro")),
            nome=str(data.get("nome", "")),
            quantidade=int(data.get("quantidade", 1) or 1),
            preco_unitario=float(data.get("preco_unitario", 0.0) or 0.0),
            posicao=data.get("posicao"),
            visivel_3d=bool(data.get("visivel_3d", True)),
        )


def _catalogo(key: str) -> Dict[str, Any]:
    return HARDWARE_CATALOG.get(key, {"tipo": "outro", "nome": key, "preco": 0.0})


def _n_dobradicas(altura_mm: float) -> int:
    h = float(altura_mm or 0.0)
    for limite, n in _DOBRA_POR_ALTURA:
        if h >= limite:
            return n
    return 2


def infer_module_hardware(params: Dict[str, Any]) -> List[HardwareItem]:
    """Infere as ferragens de um módulo a partir dos parâmetros salvos.

    Regras de inferência automática:

    * **Portas com abrir**: ``n`` dobradiças por porta (conforme altura), calço
      para cada dobradiça e um puxador por porta (conforme o tipo escolhido).
    * **Gavetas**: um par de corrediças por gaveta (400 mm ou 500 mm conforme
      profundidade) e um puxador por frente de gaveta.
    * **Portas de correr**: um trilho e duas roldanas por porta.
    * **Junção da caixa**: kit minifix + cavilha (ou confirmat) conforme o
      dispositivo de fixação escolhido.
    * **Prateleiras**: pinos/cavilhas de apoio.
    * **Pé nivelador**: para módulos de chão (balcões, gaveteiros, torres etc.).
    """
    params = params or {}
    hw: List[HardwareItem] = []

    num_portas = int(params.get("num_portas", 0) or 0)
    num_gavetas = int(params.get("num_gavetas", 0) or 0)
    num_prateleiras = int(params.get("num_prateleiras", 0) or 0)
    altura_mm = float(params.get("altura", 720) or 720)
    profundidade_mm = float(params.get("profundidade", 550) or 550)
    pux_tipo = str(params.get("puxador_tipo", "alca") or "alca").lower()
    dispositivo = str(params.get("dispositivo_fixacao", "minifix_cavilha") or "minifix_cavilha").lower()
    tipo = str(params.get("tipo", "") or "").lower()
    is_correr = "correr" in tipo

    # balcao_forno sem gaveta não tem corrediças nem puxador de gaveta.
    if tipo == "balcao_forno" and not bool(params.get("tem_gaveta", True)):
        num_gavetas = 0

    # porta_tempero: frente deslizante única (tipo gavetão).
    # Se tipo_estrutura_tempero == "aramado", substitui corrediças avulsas pelo kit aramado completo.
    tipo_estrutura_tempero = str(params.get("tipo_estrutura_tempero", "mdf") or "mdf").lower()
    if tipo == "porta_tempero":
        if tipo_estrutura_tempero == "aramado":
            # Kit aramado já inclui corrediças integradas no mecanismo
            num_gavetas = 0
            cat_kit = _catalogo("kit_porta_tempero_aramado")
            hw.append(HardwareItem(
                "kit_porta_tempero_aramado", "outro", cat_kit["nome"], 1, float(cat_kit["preco"]),
                posicao={"onde": "interno_caixa"},
            ))
            # Puxador para a frente deslizante
            pux_key = _PUXADOR_KEY.get(pux_tipo)
            if pux_key:
                catp = _catalogo(pux_key)
                hw.append(HardwareItem(
                    pux_key, "puxador", catp["nome"], 1, float(catp["preco"]),
                    posicao={"por": "frente_gaveta"},
                ))
        else:
            # 100% MDF usa 1 par de corrediça telescópica
            num_gavetas = 1

    # Altura real da porta: no balcão a porta não cobre o rodapé nem o recuo
    # superior da travessa em pé (quando existir).
    altura_porta_mm = altura_mm
    if "balcao" in tipo:
        rodape_hw = float(params.get("rodape", 0.0) or 0.0)
        recuo_topo_hw = (
            float(params.get("recuo_porta_topo_mm", 0.0) or 0.0)
            if params.get("travessa_frontal_em_pe") else 0.0
        )
        altura_porta_mm = max(
            50.0, altura_mm - rodape_hw - recuo_topo_hw - 6.0)

    # ── Portas de abrir: dobradiças, calços e puxadores ──────────────────────
    if num_portas > 0 and not is_correr:
        n_por_porta = _n_dobradicas(altura_porta_mm)
        total_dobra = n_por_porta * num_portas
        cat_dobra = _catalogo("dobradica_35mm")
        hw.append(HardwareItem(
            "dobradica_35mm", "dobradica", cat_dobra["nome"],
            total_dobra, float(cat_dobra["preco"]),
            posicao={"por_porta": n_por_porta, "portas": num_portas},
        ))
        cat_calco = _catalogo("calco_dobradica")
        hw.append(HardwareItem(
            "calco_dobradica", "dobradica", cat_calco["nome"],
            total_dobra, float(cat_calco["preco"]),
            posicao={"por_porta": n_por_porta, "portas": num_portas},
        ))
        pux_key = _PUXADOR_KEY.get(pux_tipo)
        if pux_key:
            cat = _catalogo(pux_key)
            hw.append(HardwareItem(
                pux_key, "puxador", cat["nome"], num_portas, float(cat["preco"]),
                posicao={"por": "porta"},
            ))

    # ── Junção da caixa: minifix / cavilha / confirmat ───────────────────────
    if "minifix" in dispositivo:
        cat = _catalogo("minifix_kit")
        hw.append(HardwareItem(
            "minifix_kit", "fixacao", cat["nome"], 8, float(cat["preco"]),
            posicao={"onde": "juncao_caixa"},
        ))
    if any(k in dispositivo for k in ("soberba", "confirmat", "parafuso")):
        cat = _catalogo("parafuso_confirmat")
        hw.append(HardwareItem(
            "parafuso_confirmat", "fixacao", cat["nome"], 16, float(cat["preco"]),
            posicao={"onde": "juncao_caixa"},
        ))
    if "cavilha" in dispositivo and "minifix" not in dispositivo:
        cat = _catalogo("pino_cavilha_8")
        hw.append(HardwareItem(
            "pino_cavilha_8", "fixacao", cat["nome"], 16, float(cat["preco"]),
            posicao={"onde": "juncao_caixa"},
        ))

    # ── Gavetas: corrediças e puxadores ──────────────────────────────────────
    if num_gavetas > 0:
        chave = "corredica_50" if profundidade_mm > 500 else "corredica_40"
        cat = _catalogo(chave)
        hw.append(HardwareItem(
            chave, "corredica", cat["nome"], num_gavetas, float(cat["preco"]),
            posicao={"por": "gaveta"},
        ))
        pux_key = _PUXADOR_KEY.get(pux_tipo)
        if pux_key:
            catp = _catalogo(pux_key)
            hw.append(HardwareItem(
                pux_key, "puxador", catp["nome"], num_gavetas, float(catp["preco"]),
                posicao={"por": "frente_gaveta"},
            ))

    # ── Portas de correr: trilhos e roldanas ─────────────────────────────────
    if is_correr and num_portas > 0:
        cat_t = _catalogo("trilho_correr")
        hw.append(HardwareItem(
            "trilho_correr", "trilho", cat_t["nome"], num_portas, float(cat_t["preco"]),
            posicao={"por": "porta_correr"},
        ))
        cat_r = _catalogo("roldana_correr")
        hw.append(HardwareItem(
            "roldana_correr", "trilho", cat_r["nome"], num_portas * 2, float(cat_r["preco"]),
            posicao={"por": "porta_correr", "n_roldanas": 2},
        ))

    # ── Prateleiras: pinos de apoio ──────────────────────────────────────────
    if num_prateleiras > 0:
        # Cada vão possui sua própria prateleira e cada prateleira usa 4 pinos
        # (2 em cada lateral/divisória). A contagem de vãos segue a mesma regra
        # do build_balcao: mínimo estrutural para 3+ portas e máximo n_portas - 1.
        from .module_geometry import MAX_DOORS, auto_divisoes_for_doors

        n_p = max(0, min(MAX_DOORS, num_portas))
        min_divisoes_hw = auto_divisoes_for_doors(n_p) if n_p >= 3 else 0
        if params.get("num_divisoes") is not None:
            solicitadas_hw = max(0, int(params.get("num_divisoes") or 0))
            max_divisoes_hw = max(0, n_p - 1) if n_p > 0 else solicitadas_hw
            num_divisoes_hw = max(
                min_divisoes_hw, min(solicitadas_hw, max_divisoes_hw))
        else:
            num_divisoes_hw = min_divisoes_hw
        num_vaos = num_divisoes_hw + 1
        cat = _catalogo("pino_cavilha_8")
        hw.append(HardwareItem(
            "pino_cavilha_8", "fixacao", cat["nome"],
            num_prateleiras * 4 * num_vaos, float(cat["preco"]),
            posicao={"por": "prateleira", "n_pinos": 4, "vaos": num_vaos},
        ))

    # ── Pé nivelador: apenas se explicitamente solicitado nos parâmetros ──
    tem_pes = bool(params.get("tem_pes_nivelador", False))
    if tem_pes:
        cat = _catalogo("pes_nivelador")
        hw.append(HardwareItem(
            "pes_nivelador", "outro", cat["nome"], 4, float(cat["preco"]),
            posicao={"onde": "base"},
        ))

    return hw


def serialize_hardware(items: Iterable[HardwareItem]) -> List[Dict[str, Any]]:
    """Converte uma lista de ``HardwareItem`` para dicionários serializáveis."""
    return [it.to_dict() for it in items]


def deserialize_hardware(data: Any) -> List[HardwareItem]:
    """Recria ``HardwareItem``s a partir de dados serializados (ext/JSON)."""
    if not isinstance(data, list):
        return []
    itens: List[HardwareItem] = []
    for d in data:
        if not isinstance(d, dict) or not d.get("key"):
            continue
        try:
            itens.append(HardwareItem.from_dict(d))
        except (TypeError, ValueError):
            continue
    return itens


def consolidate_hardware(
    entries: Iterable[Tuple[Any, List[HardwareItem]]],
) -> Dict[str, Dict[str, Any]]:
    """Agrega ferragens de vários módulos numa única contagem.

    ``entries`` é um iterável de ``(chave_modulo, [HardwareItem, ...])``. A
    chave do módulo evita contar a mesma ferragem duas vezes quando várias
    peças de um mesmo módulo aparecem na cutlist.

    Retorna ``{codigo: {"tipo", "nome", "quantidade", "preco_unitario", "total"}}``.
    """
    resultado: Dict[str, Dict[str, Any]] = {}
    for _chave_modulo, items in entries:
        for it in items:
            if it.quantidade <= 0:
                continue
            entrada = resultado.setdefault(
                it.key,
                {
                    "tipo": it.tipo,
                    "nome": it.nome,
                    "quantidade": 0,
                    "preco_unitario": float(it.preco_unitario or 0.0),
                    "total": 0.0,
                },
            )
            entrada["quantidade"] += int(it.quantidade)
            entrada["total"] = round(
                entrada["quantidade"] * float(entrada["preco_unitario"]), 2
            )
    return resultado


def hardware_total_preco(consolidado: Dict[str, Dict[str, Any]]) -> float:
    """Soma o preço total de todas as ferragens consolidadas."""
    return round(sum(float(e.get("total", 0.0)) for e in consolidado.values()), 2)
