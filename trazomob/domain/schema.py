# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez and IngeTrazo contributors.
"""Fonte única de verdade dos metadados do TrazoMob em ``group.ext``.

Historicamente o plugin grava os mesmos dados em até três chaves —
``ext["trazomob"]``, ``ext["trazomob_module"]`` e ``ext["trazomob_esquadria"]``
— com nomes de campo diferentes (``largura`` num, ``largura_mm`` noutro).
Um leitor que escolhia uma chave e ignorava as outras enxergava um valor
diferente do mesmo módulo, e um escritor que atualizava só uma delas deixava
as demais defasadas.

Este módulo centraliza as três decisões:

* **qual é o tipo** de um grupo (``kind_of``);
* **como ler** os parâmetros, seja qual for a chave que os gravou
  (``params_of``, ``module_params``, ``esquadria_params``);
* **como gravar** de modo que as chaves fiquem consistentes
  (``set_module_data``, ``set_esquadria_data``, ``update_module_data``).

Regra: código novo lê por estas funções e escreve por ``set_*``/``update_*``.
Ler ``group.ext["trazomob_module"]`` direto é o que produzia a divergência.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from ..domain.entity import get_trazomob

KIND_MODULE = "module"
KIND_ESQUADRIA = "esquadria"
KIND_WALL = "wall"
KIND_LIGHT = "light"
KIND_FLOOR = "floor"
KIND_CEILING = "ceiling"
KIND_BANCADA = "bancada"
KIND_AMBIENTE = "ambiente"
KIND_PAVIMENTO = "pavimento"
KIND_ASSEMBLY = "assembly"

#: Chaves legadas reconhecidas por tipo, na ordem em que ``kind_of`` as testa.
_KIND_KEYS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (KIND_ESQUADRIA, ("trazomob_esquadria",)),
    (KIND_MODULE, ("trazomob_module",)),
    (KIND_WALL, ("trazomob_wall",)),
    (KIND_BANCADA, ("trazomob_bancada",)),
    (KIND_LIGHT, ("trazomob_light",)),
    (KIND_FLOOR, ("trazomob_floor",)),
    (KIND_CEILING, ("trazomob_ceiling",)),
    (KIND_AMBIENTE, ("trazomob_ambiente",)),
    (KIND_PAVIMENTO, ("trazomob_pavimento",)),
)

#: Campos canônicos de módulo e os nomes que os representam em cada espelho (bidirecional EN <-> PT).
_MODULE_ALIASES: dict[str, tuple[str, ...]] = {
    # Dimensões
    "largura": ("largura", "largura_mm", "width", "width_mm"),
    "altura": ("altura", "altura_mm", "height", "height_mm"),
    "profundidade": ("profundidade", "profundidade_mm", "esp_parede_mm", "depth", "depth_mm"),
    "espessura": ("espessura", "espessura_mm", "thickness", "thickness_mm"),
    "width": ("width", "width_mm", "largura", "largura_mm"),
    "height": ("height", "height_mm", "altura", "altura_mm"),
    "depth": ("depth", "depth_mm", "profundidade", "profundidade_mm", "esp_parede_mm"),
    "thickness": ("thickness", "thickness_mm", "espessura", "espessura_mm"),

    # Tipos e estruturas
    "tipo": ("tipo", "type", "module_type"),
    "type": ("type", "module_type", "tipo"),
    "module_type": ("module_type", "type", "tipo"),

    "num_portas": ("num_portas", "door_count", "doors"),
    "door_count": ("door_count", "num_portas", "doors"),

    "num_gavetas": ("num_gavetas", "drawer_count", "drawers"),
    "drawer_count": ("drawer_count", "num_gavetas", "drawers"),

    "num_prateleiras": ("num_prateleiras", "shelf_count", "shelves"),
    "shelf_count": ("shelf_count", "num_prateleiras", "shelves"),

    "num_divisoes": ("num_divisoes", "divider_count", "dividers"),
    "divider_count": ("divider_count", "num_divisoes", "dividers"),

    "tem_fundo": ("tem_fundo", "has_back", "has_back_panel"),
    "has_back": ("has_back", "has_back_panel", "tem_fundo"),

    "tipo_fundo": ("tipo_fundo", "back_type"),
    "back_type": ("back_type", "tipo_fundo"),

    "rodape": ("rodape", "plinth_height", "baseboard"),
    "plinth_height": ("plinth_height", "baseboard", "rodape"),

    "puxador_tipo": ("puxador_tipo", "handle_type"),
    "handle_type": ("handle_type", "puxador_tipo"),

    "puxador_cor": ("puxador_cor", "handle_color"),
    "handle_color": ("handle_color", "puxador_cor"),

    "puxador_pos": ("puxador_pos", "handle_pos", "handle_position"),
    "handle_pos": ("handle_pos", "handle_position", "puxador_pos"),

    "material_caixa": ("material_caixa", "carcass_material"),
    "carcass_material": ("carcass_material", "material_caixa"),

    "material_frentes": ("material_frentes", "fronts_material"),
    "fronts_material": ("fronts_material", "material_frentes"),
}

#: Campos canônicos de esquadria e os nomes que os representam em cada espelho.
_ESQUADRIA_ALIASES: dict[str, tuple[str, ...]] = {
    "largura_mm": ("largura_mm", "largura"),
    "altura_mm": ("altura_mm", "altura"),
    "esp_parede_mm": ("esp_parede_mm", "profundidade", "espessura_parede_mm"),
    "peitoril_mm": ("peitoril_mm",),
}

#: Como o espelho ``trazomob_module`` de uma esquadria nomeia cada medida.
_ESQUADRIA_TO_MODULE: dict[str, tuple[str, ...]] = {
    "largura": ("largura", "largura_mm"),
    "altura": ("altura", "altura_mm"),
    "profundidade": ("profundidade", "esp_parede_mm"),
}


def _ensure_ext(group: Any) -> Optional[Dict[str, Any]]:
    """Garante um ``group.ext`` do tipo dicionário; devolve ``None`` sem grupo."""
    if group is None:
        return None
    ext = getattr(group, "ext", None)
    if not isinstance(ext, dict):
        try:
            group.ext = {}
        except Exception:
            return None
        ext = group.ext
    return ext


def kind_of(group: Any) -> Optional[str]:
    """Tipo de um grupo do TrazoMob, ou ``None`` quando ele não é do plugin.

    A chave oficial ``ext["trazomob"]["kind"]`` manda; as chaves legadas são
    reconhecidas como fallback para documentos gravados antes da unificação.
    """
    ext = getattr(group, "ext", None)
    if not isinstance(ext, dict):
        return None
    tm = ext.get("trazomob")
    if isinstance(tm, dict):
        kind = tm.get("kind")
        if kind:
            return str(kind)
    for kind, keys in _KIND_KEYS:
        for key in keys:
            value = ext.get(key)
            if isinstance(value, dict) or value is True:
                return kind
    return None


def is_kind(group: Any, kind: str) -> bool:
    """Atalho para ``kind_of(group) == kind``."""
    return kind_of(group) == kind


def _merged(group: Any) -> Dict[str, Any]:
    """Une as três chaves sem perder campos: a oficial sobrescreve as legadas."""
    ext = getattr(group, "ext", None)
    out: Dict[str, Any] = {}
    if not isinstance(ext, dict):
        return out
    for key in ("trazomob_module", "trazomob_esquadria", "trazomob"):
        value = ext.get(key)
        if isinstance(value, dict):
            out.update(value)
    # A chave oficial vem por último de propósito: em caso de conflito, vence.
    official = ext.get("trazomob")
    if isinstance(official, dict):
        out.update(official)
    return out


def _with_aliases(data: Dict[str, Any],
                  aliases: Dict[str, tuple[str, ...]]) -> Dict[str, Any]:
    """Completa os campos canônicos a partir dos nomes alternativos."""
    out = dict(data)
    for canonical, sources in aliases.items():
        if out.get(canonical) is not None:
            continue
        for source in sources:
            if out.get(source) is not None:
                out[canonical] = out[source]
                break
    return out


def params_of(group: Any) -> Dict[str, Any]:
    """Todos os parâmetros do grupo, com os nomes canônicos preenchidos.

    Serve tanto para módulos quanto para esquadrias: os apelidos das duas
    famílias são aplicados, então ``largura`` e ``largura_mm`` sempre existem
    quando o valor existe em qualquer espelho.
    """
    data = _merged(group)
    data = _with_aliases(data, _MODULE_ALIASES)
    return _with_aliases(data, _ESQUADRIA_ALIASES)


def module_params(group: Any) -> Dict[str, Any]:
    """Parâmetros de um módulo (cópia; para alterar use ``live_module_data``)."""
    return _with_aliases(_merged(group), _MODULE_ALIASES)


def esquadria_params(group: Any) -> Dict[str, Any]:
    """Parâmetros de uma esquadria (cópia)."""
    return _with_aliases(_merged(group), _ESQUADRIA_ALIASES)


def light_params(group: Any) -> Dict[str, Any]:
    """Dados de uma luminária (cópia)."""
    return dict(get_trazomob(group))


def wall_params(group: Any) -> Dict[str, Any]:
    """Dados de uma parede (cópia)."""
    return dict(get_trazomob(group))


def live_module_data(group: Any) -> Dict[str, Any]:
    """Dicionário **vivo** dos metadados de módulo, mutável no lugar.

    Use quando o chamador vai alterar valores (rotação, offset, medidas):
    as duas chaves apontam para o mesmo dicionário, então a alteração não
    fica presa a um espelho.
    """
    ext = _ensure_ext(group)
    if ext is None:
        return {}
    tm = ext.get("trazomob")
    if not isinstance(tm, dict):
        tm = {}
        ext["trazomob"] = tm
    tm.setdefault("kind", KIND_MODULE)
    ext["trazomob_module"] = tm
    return tm


def set_module_data(group: Any, data: Optional[Dict[str, Any]] = None,
                    **kwargs: Any) -> Dict[str, Any]:
    """Grava metadados de módulo nas duas chaves canônicas, com o mesmo dict."""
    ext = _ensure_ext(group)
    payload = dict(data or {})
    payload.update(kwargs)
    payload["kind"] = KIND_MODULE
    if ext is not None:
        ext["trazomob"] = payload
        ext["trazomob_module"] = payload
    return payload


def update_module_data(group: Any,
                       data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Atualiza no lugar o dicionário de módulo já publicado (não cria cópia).

    É o caminho para valores calculados depois de ``set_module_data`` — por
    exemplo o span não-rotacionado da caixaria. Com ``set_trazomob`` (que
    copiava) esses campos ficavam só na variável local e nunca chegavam ao
    documento.
    """
    ext = _ensure_ext(group)
    if ext is None:
        return {}
    tm = ext.get("trazomob")
    if not isinstance(tm, dict):
        return set_module_data(group, data)
    tm.update(dict(data or {}))
    ext["trazomob_module"] = tm
    return tm


def set_esquadria_data(group: Any, data: Optional[Dict[str, Any]] = None,
                       **kwargs: Any) -> Dict[str, Any]:
    """Grava metadados de esquadria nas três chaves, com os apelidos certos.

    ``trazomob`` fica com o ``kind`` e os nomes ``*_mm``; ``trazomob_esquadria``
    mantém o formato histórico; ``trazomob_module`` recebe os apelidos
    ``largura``/``altura``/``profundidade`` que os leitores antigos esperam.
    """
    ext = _ensure_ext(group)
    payload = dict(data or {})
    payload.update(kwargs)
    payload["kind"] = KIND_ESQUADRIA
    if ext is None:
        return payload
    oficial = dict(payload)
    espelho_esquadria = {k: v for k, v in payload.items() if k != "kind"}
    espelho_module = _with_aliases(payload, _ESQUADRIA_TO_MODULE)
    espelho_module.pop("kind", None)
    ext["trazomob"] = oficial
    ext["trazomob_esquadria"] = espelho_esquadria
    ext["trazomob_module"] = espelho_module
    return oficial


def update_esquadria_data(group: Any,
                          data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Atualiza metadados de esquadria mantendo as três chaves coerentes.

    Parte do que já está gravado e reescreve tudo por ``set_esquadria_data``:
    um campo alterado num só espelho nunca fica divergente dos outros.
    """
    dados = esquadria_params(group)
    dados.update(dict(data or {}))
    return set_esquadria_data(group, dados)


def ambiente_params(group: Any) -> Dict[str, Any]:
    """Parâmetros de um ambiente (cópia)."""
    return dict(get_trazomob(group))


def pavimento_params(group: Any) -> Dict[str, Any]:
    """Dados de um pavimento (cópia)."""
    return dict(get_trazomob(group))


def set_ambiente_data(group: Any, data: Optional[Dict[str, Any]] = None,
                      **kwargs: Any) -> Dict[str, Any]:
    """Grava metadados de ambiente na chave oficial."""
    ext = _ensure_ext(group)
    payload = dict(data or {})
    payload.update(kwargs)
    payload["kind"] = KIND_AMBIENTE
    if ext is not None:
        ext["trazomob"] = payload
        ext["trazomob_ambiente"] = payload
    return payload


def update_ambiente_data(group: Any,
                         data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Atualiza metadados de ambiente no lugar."""
    ext = _ensure_ext(group)
    if ext is None:
        return {}
    tm = ext.get("trazomob")
    if not isinstance(tm, dict):
        return set_ambiente_data(group, data)
    tm.update(dict(data or {}))
    ext["trazomob_ambiente"] = tm
    return tm


def set_pavimento_data(group: Any, data: Optional[Dict[str, Any]] = None,
                       **kwargs: Any) -> Dict[str, Any]:
    """Grava metadados de pavimento na chave oficial."""
    ext = _ensure_ext(group)
    payload = dict(data or {})
    payload.update(kwargs)
    payload["kind"] = KIND_PAVIMENTO
    if ext is not None:
        ext["trazomob"] = payload
        ext["trazomob_pavimento"] = payload
    return payload


def update_pavimento_data(group: Any,
                          data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Atualiza metadados de pavimento no lugar."""
    ext = _ensure_ext(group)
    if ext is None:
        return {}
    tm = ext.get("trazomob")
    if not isinstance(tm, dict):
        return set_pavimento_data(group, data)
    tm.update(dict(data or {}))
    ext["trazomob_pavimento"] = tm
    return tm


def set_floor_data(group: Any, data: Optional[Dict[str, Any]] = None,
                   **kwargs: Any) -> Dict[str, Any]:
    """Grava metadados de piso/laje na chave oficial."""
    ext = _ensure_ext(group)
    payload = dict(data or {})
    payload.update(kwargs)
    payload["kind"] = KIND_FLOOR
    if ext is not None:
        ext["trazomob"] = payload
        ext["trazomob_floor"] = payload
    return payload


def set_ceiling_data(group: Any, data: Optional[Dict[str, Any]] = None,
                     **kwargs: Any) -> Dict[str, Any]:
    """Grava metadados de teto/forro na chave oficial."""
    ext = _ensure_ext(group)
    payload = dict(data or {})
    payload.update(kwargs)
    payload["kind"] = KIND_CEILING
    if ext is not None:
        ext["trazomob"] = payload
        ext["trazomob_ceiling"] = payload
    return payload


def set_wall_data(group: Any, data: Optional[Dict[str, Any]] = None,
                  **kwargs: Any) -> Dict[str, Any]:
    """Grava metadados de parede na chave oficial."""
    ext = _ensure_ext(group)
    payload = dict(data or {})
    payload.update(kwargs)
    payload["kind"] = KIND_WALL
    if ext is not None:
        ext["trazomob"] = payload
        ext["trazomob_wall"] = payload
    return payload


# --- Reexportações e helpers de tipagem moveleira canônica ---

def is_module(group: Any) -> bool:
    """Diz se o grupo é um módulo paramétrico (inclusive os legados)."""
    if kind_of(group) == KIND_MODULE:
        return True
    ext = getattr(group, "ext", None)
    if not isinstance(ext, dict):
        return False
    return "trazomob_module" in ext


def is_assembly(group: Any) -> bool:
    """Diz se o grupo é um contêiner de módulos criado por este plugin."""
    return kind_of(group) == KIND_ASSEMBLY


def iter_module_groups(roots: Any) -> Any:
    """Varre a árvore e devolve os módulos paramétricos em qualquer nível."""
    from ..domain.assembly import iter_module_groups as _iter_mg
    return _iter_mg(roots)

