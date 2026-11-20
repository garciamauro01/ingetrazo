# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Manifest único das esquadrias reais do Trazomob.

Este pacote é a fonte única de verdade para:

* os dados de catálogo exibidos na UI (``get_esquadrias_catalogo``);
* a resolução do arquivo ``.igz`` de cada modelo (``get_esquadria_files``);
* os índices das peças-folha (``get_novas_portas_folhas``);
* o papel cinematográfico de cada peça (``get_novas_portas_cinematica``).

Os dados vivem em ``esquadrias.json``, na mesma pasta.  Nenhuma outra parte
do código deve repetir essas tabelas: alterar o JSON altera o catálogo, o
carregador e a cinemática ao mesmo tempo.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

_MANIFEST_PATH = Path(__file__).resolve().parent / "esquadrias.json"
_COMPONENTS_DIR = Path(__file__).resolve().parent.parent / "components"
_SUBPASTAS_VALIDAS = ("portas", "janelas")
_PAPEIS_VALIDOS = ("fixo", "movel")

# Chaves que são metadados do manifesto, não campos do catálogo de UI.
_METADADOS = ("igz_file", "subpasta", "folhas", "cinematica")


def _validar_manifest(dados: dict) -> None:
    """Valida integridade do manifesto, levantando ``ValueError`` se houver erro."""
    if dados.get("schema") != 1:
        raise ValueError(f"esquadrias.json: schema {dados.get('schema')!r} não suportado")

    modelos = dados.get("modelos")
    aliases = dados.get("aliases", {})
    if not isinstance(modelos, list) or not isinstance(aliases, dict):
        raise ValueError("esquadrias.json: 'modelos' deve ser lista e 'aliases' um objeto")

    vistos: set[str] = set()
    for papel, entradas in (("modelo", modelos), ("alias", aliases)):
        iterable = entradas if papel == "modelo" else aliases.items()
        for entrada in iterable:
            if papel == "alias":
                item_id, alvo = entrada
                if item_id in vistos:
                    raise ValueError(f"esquadrias.json: id duplicado '{item_id}'")
                vistos.add(item_id)
                if not isinstance(alvo, dict):
                    raise ValueError(f"esquadrias.json: alias '{item_id}' inválido")
                igz_file = alvo.get("igz_file")
                subpasta = alvo.get("subpasta")
                folhas = None
                cinematica = None
                num_portas = None
            else:
                if not isinstance(entrada, dict):
                    raise ValueError("esquadrias.json: entrada de modelo inválida")
                item_id = entrada.get("id")
                if not isinstance(item_id, str) or not item_id:
                    raise ValueError("esquadrias.json: modelo sem 'id'")
                if item_id in vistos:
                    raise ValueError(f"esquadrias.json: id duplicado '{item_id}'")
                vistos.add(item_id)
                igz_file = entrada.get("igz_file")
                subpasta = entrada.get("subpasta")
                folhas = entrada.get("folhas")
                cinematica = entrada.get("cinematica", {})
                num_portas = entrada.get("num_portas")

            if not isinstance(igz_file, str) or not igz_file.endswith(".igz"):
                raise ValueError(f"esquadrias.json: '{item_id}' com igz_file inválido")
            if Path(igz_file).name != igz_file:
                raise ValueError(f"esquadrias.json: igz_file não pode conter pastas: {igz_file!r}")
            if subpasta not in _SUBPASTAS_VALIDAS:
                raise ValueError(f"esquadrias.json: '{item_id}' com subpasta inválida {subpasta!r}")

            esperada = "janelas" if item_id.startswith("janela_") else "portas"
            if subpasta != esperada:
                raise ValueError(
                    f"esquadrias.json: '{item_id}' declarado em '{subpasta}', "
                    f"mas o prefixo exige '{esperada}'"
                )

            caminho = _COMPONENTS_DIR / subpasta / igz_file
            if not caminho.is_file():
                raise ValueError(
                    f"esquadrias.json: arquivo .igz não encontrado para '{item_id}': {caminho}"
                )

            if folhas is not None:
                if not isinstance(folhas, list) or not all(
                    isinstance(i, int) and i >= 0 for i in folhas
                ):
                    raise ValueError(f"esquadrias.json: 'folhas' inválido para '{item_id}'")
                if len(set(folhas)) != len(folhas):
                    raise ValueError(f"esquadrias.json: 'folhas' duplicadas em '{item_id}'")
                if num_portas is not None and num_portas != len(folhas):
                    raise ValueError(
                        f"esquadrias.json: '{item_id}' tem num_portas={num_portas} "
                        f"mas {len(folhas)} folha(s)"
                    )

            if cinematica:
                if not isinstance(cinematica, dict):
                    raise ValueError(f"esquadrias.json: 'cinematica' inválida para '{item_id}'")
                for chave, valor in cinematica.items():
                    try:
                        indice = int(chave)
                    except (TypeError, ValueError):
                        raise ValueError(
                            f"esquadrias.json: índice de peça inválido {chave!r} em '{item_id}'"
                        ) from None
                    if indice < 0:
                        raise ValueError(
                            f"esquadrias.json: índice de peça negativo {chave!r} em '{item_id}'"
                        )
                    if (not isinstance(valor, (list, tuple)) or len(valor) != 2
                            or valor[0] not in _PAPEIS_VALIDOS
                            or not isinstance(valor[1], int)):
                        raise ValueError(
                            f"esquadrias.json: papel cinematográfico inválido "
                            f"{valor!r} em '{item_id}[{chave}]'"
                        )
                    dono = valor[1]
                    if folhas is not None and dono >= len(folhas):
                        raise ValueError(
                            f"esquadrias.json: '{item_id}[{chave}]' referencia folha {dono} "
                            f"mas há apenas {len(folhas)} folha(s)"
                        )


def _carregar() -> dict:
    dados = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    _validar_manifest(dados)
    return dados


ESQUADRIAS_MANIFEST = _carregar()


def get_esquadrias_catalogo() -> list[dict]:
    """Itens da seção “Portas & Janelas” do catálogo, sem metadados internos."""
    return [
        {k: copy.deepcopy(v) for k, v in modelo.items() if k not in _METADADOS}
        for modelo in ESQUADRIAS_MANIFEST["modelos"]
    ]


def get_esquadria_modelo(item_id: str) -> dict | None:
    """Retorna os dados públicos de um modelo do catálogo, ou ``None``."""
    for modelo in ESQUADRIAS_MANIFEST["modelos"]:
        if modelo.get("id") == item_id:
            return {k: copy.deepcopy(v) for k, v in modelo.items() if k not in _METADADOS}
    return None


def get_esquadria_files() -> dict[str, tuple[str, str]]:
    """Id de esquadria -> (arquivo .igz, subpasta em assets/components)."""
    tabela: dict[str, tuple[str, str]] = {}
    for modelo in ESQUADRIAS_MANIFEST["modelos"]:
        tabela[modelo["id"]] = (modelo["igz_file"], modelo["subpasta"])
    for alias, alvo in ESQUADRIAS_MANIFEST.get("aliases", {}).items():
        tabela[alias] = (alvo["igz_file"], alvo["subpasta"])
    return tabela


def get_novas_portas_folhas() -> dict[str, tuple[int, ...]]:
    """Nome do arquivo .igz -> índices das peças que fazem o papel de folha."""
    return {
        modelo["igz_file"]: tuple(modelo["folhas"])
        for modelo in ESQUADRIAS_MANIFEST["modelos"]
        if "folhas" in modelo
    }


def get_novas_portas_cinematica() -> dict[str, dict[int, tuple[str, int]]]:
    """Nome do arquivo .igz -> {índice_da_peça: (papel, índice_da_folha)}."""
    return {
        modelo["igz_file"]: {
            int(chave): (valor[0], valor[1])
            for chave, valor in modelo.get("cinematica", {}).items()
        }
        for modelo in ESQUADRIAS_MANIFEST["modelos"]
        if "cinematica" in modelo
    }


def validar_manifest() -> None:
    """Revalida o manifesto carregado (útil em testes e ferramentas)."""
    _validar_manifest(ESQUADRIAS_MANIFEST)
