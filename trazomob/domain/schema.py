# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez and IngeTrazo contributors.
"""Single source of truth for TrazoMob metadata in ``group.ext``.

Historically, the plugin stored the same data in up to three keys —
``ext["trazomob"]``, ``ext["trazomob_module"]``, and ``ext["trazomob_esquadria"]``
— with different field names (``largura`` in one, ``largura_mm`` in another).
A reader that picked one key and ignored the others saw a different value
for the same module, and a writer that updated only one left the others out
of sync.

This module centralizes the three decisions:

* **what kind** a group is (``kind_of``);
* **how to read** parameters, regardless of which key wrote them
  (``params_of``, ``module_params``, ``esquadria_params``);
* **how to write** so that keys stay consistent
  (``set_module_data``, ``set_esquadria_data``, ``update_module_data``).

Rule: new code reads through these functions and writes via ``set_*``/``update_*``.
Reading ``group.ext["trazomob_module"]`` directly is what caused the divergence.
"""
from __future__ import annotations

from typing import Any

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

#: Legacy keys recognized per kind, in the order ``kind_of`` checks them.
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

#: Canonical module fields and the names representing them in each mirror (bidirectional EN <-> PT).
_MODULE_ALIASES: dict[str, tuple[str, ...]] = {
    # Dimensions
    "largura": ("largura", "largura_mm", "width", "width_mm"),
    "altura": ("altura", "altura_mm", "height", "height_mm"),
    "profundidade": ("profundidade", "profundidade_mm", "esp_parede_mm", "depth", "depth_mm"),
    "espessura": ("espessura", "espessura_mm", "thickness", "thickness_mm"),
    "width": ("width", "width_mm", "largura", "largura_mm"),
    "height": ("height", "height_mm", "altura", "altura_mm"),
    "depth": ("depth", "depth_mm", "profundidade", "profundidade_mm", "esp_parede_mm"),
    "thickness": ("thickness", "thickness_mm", "espessura", "espessura_mm"),

    # Types and structures
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

#: Canonical millwork-opening (``esquadria``) fields and the names representing them in each mirror.
_ESQUADRIA_ALIASES: dict[str, tuple[str, ...]] = {
    "largura_mm": ("largura_mm", "largura"),
    "altura_mm": ("altura_mm", "altura"),
    "esp_parede_mm": ("esp_parede_mm", "profundidade", "espessura_parede_mm"),
    "peitoril_mm": ("peitoril_mm",),
}

#: How a millwork opening's ``trazomob_module`` mirror names each dimension.
_ESQUADRIA_TO_MODULE: dict[str, tuple[str, ...]] = {
    "largura": ("largura", "largura_mm"),
    "altura": ("altura", "altura_mm"),
    "profundidade": ("profundidade", "esp_parede_mm"),
}


def _ensure_ext(group: Any) -> dict[str, Any] | None:
    """Ensures a dict ``group.ext``; returns ``None`` if there is no group."""
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


def kind_of(group: Any) -> str | None:
    """Kind of a TrazoMob group, or ``None`` when it does not belong to the plugin.

    The official key ``ext["trazomob"]["kind"]`` takes precedence; legacy keys
    are recognized as fallback for documents saved before unification.
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
    """Shortcut for ``kind_of(group) == kind``."""
    return kind_of(group) == kind


def _merged(group: Any) -> dict[str, Any]:
    """Merges the three keys without losing fields: the official key overrides legacy ones."""
    ext = getattr(group, "ext", None)
    out: dict[str, Any] = {}
    if not isinstance(ext, dict):
        return out
    for key in ("trazomob_module", "trazomob_esquadria", "trazomob"):
        value = ext.get(key)
        if isinstance(value, dict):
            out.update(value)
    # The official key comes last intentionally: on conflict, it wins.
    official = ext.get("trazomob")
    if isinstance(official, dict):
        out.update(official)
    return out


def _with_aliases(data: dict[str, Any],
                  aliases: dict[str, tuple[str, ...]]) -> dict[str, Any]:
    """Populates canonical fields from their alternative names."""
    out = dict(data)
    for canonical, sources in aliases.items():
        if out.get(canonical) is not None:
            continue
        for source in sources:
            if out.get(source) is not None:
                out[canonical] = out[source]
                break
    return out


def params_of(group: Any) -> dict[str, Any]:
    """All group parameters, with canonical names populated.

    Works for both modules and millwork openings: aliases for both families
    are applied, so ``largura`` and ``largura_mm`` always exist whenever the
    value exists in any mirror.
    """
    data = _merged(group)
    data = _with_aliases(data, _MODULE_ALIASES)
    return _with_aliases(data, _ESQUADRIA_ALIASES)


def module_params(group: Any) -> dict[str, Any]:
    """Module parameters (copy; to mutate in place use ``live_module_data``)."""
    return _with_aliases(_merged(group), _MODULE_ALIASES)


def esquadria_params(group: Any) -> dict[str, Any]:
    """Millwork-opening (``esquadria``) parameters (copy)."""
    return _with_aliases(_merged(group), _ESQUADRIA_ALIASES)


def light_params(group: Any) -> dict[str, Any]:
    """Luminaire data (copy)."""
    return dict(get_trazomob(group))


def wall_params(group: Any) -> dict[str, Any]:
    """Wall data (copy)."""
    return dict(get_trazomob(group))


def live_module_data(group: Any) -> dict[str, Any]:
    """**Live** module metadata dictionary, mutable in place.

    Use when the caller will modify values (rotation, offset, dimensions):
    both keys point to the same dictionary, so changes do not remain trapped
    in a single mirror.
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


def set_module_data(group: Any, data: dict[str, Any] | None = None,
                    **kwargs: Any) -> dict[str, Any]:
    """Writes module metadata to both canonical keys, sharing the same dict."""
    ext = _ensure_ext(group)
    payload = dict(data or {})
    payload.update(kwargs)
    payload["kind"] = KIND_MODULE
    if ext is not None:
        ext["trazomob"] = payload
        ext["trazomob_module"] = payload
    return payload


def update_module_data(group: Any,
                       data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Updates an already-published module dictionary in place (does not copy).

    This is the path for values computed after ``set_module_data`` — for
    example, the unrotated carcass span. With ``set_trazomob`` (which copied),
    those fields stayed in the local variable only and never reached the
    document.
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


def set_esquadria_data(group: Any, data: dict[str, Any] | None = None,
                       **kwargs: Any) -> dict[str, Any]:
    """Writes millwork-opening metadata across all three keys with matching aliases.

    ``trazomob`` holds ``kind`` and the ``*_mm`` names; ``trazomob_esquadria``
    keeps the historical format; ``trazomob_module`` receives the
    ``largura``/``altura``/``profundidade`` aliases expected by legacy readers.
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
                          data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Updates millwork-opening metadata while keeping all three keys consistent.

    Starts from what is already stored and rewrites everything via
    ``set_esquadria_data``: a field modified in one mirror never diverges from
    the others.
    """
    dados = esquadria_params(group)
    dados.update(dict(data or {}))
    return set_esquadria_data(group, dados)


def ambiente_params(group: Any) -> dict[str, Any]:
    """Room (``ambiente``) parameters (copy)."""
    return dict(get_trazomob(group))


def pavimento_params(group: Any) -> dict[str, Any]:
    """Floor-level (``pavimento``) data (copy)."""
    return dict(get_trazomob(group))


def set_ambiente_data(group: Any, data: dict[str, Any] | None = None,
                      **kwargs: Any) -> dict[str, Any]:
    """Writes room (``ambiente``) metadata to the official key."""
    ext = _ensure_ext(group)
    payload = dict(data or {})
    payload.update(kwargs)
    payload["kind"] = KIND_AMBIENTE
    if ext is not None:
        ext["trazomob"] = payload
        ext["trazomob_ambiente"] = payload
    return payload


def update_ambiente_data(group: Any,
                         data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Updates room (``ambiente``) metadata in place."""
    ext = _ensure_ext(group)
    if ext is None:
        return {}
    tm = ext.get("trazomob")
    if not isinstance(tm, dict):
        return set_ambiente_data(group, data)
    tm.update(dict(data or {}))
    ext["trazomob_ambiente"] = tm
    return tm


def set_pavimento_data(group: Any, data: dict[str, Any] | None = None,
                       **kwargs: Any) -> dict[str, Any]:
    """Writes floor-level (``pavimento``) metadata to the official key."""
    ext = _ensure_ext(group)
    payload = dict(data or {})
    payload.update(kwargs)
    payload["kind"] = KIND_PAVIMENTO
    if ext is not None:
        ext["trazomob"] = payload
        ext["trazomob_pavimento"] = payload
    return payload


def update_pavimento_data(group: Any,
                          data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Updates floor-level (``pavimento``) metadata in place."""
    ext = _ensure_ext(group)
    if ext is None:
        return {}
    tm = ext.get("trazomob")
    if not isinstance(tm, dict):
        return set_pavimento_data(group, data)
    tm.update(dict(data or {}))
    ext["trazomob_pavimento"] = tm
    return tm


def set_floor_data(group: Any, data: dict[str, Any] | None = None,
                   **kwargs: Any) -> dict[str, Any]:
    """Writes floor/slab metadata to the official key."""
    ext = _ensure_ext(group)
    payload = dict(data or {})
    payload.update(kwargs)
    payload["kind"] = KIND_FLOOR
    if ext is not None:
        ext["trazomob"] = payload
        ext["trazomob_floor"] = payload
    return payload


def set_ceiling_data(group: Any, data: dict[str, Any] | None = None,
                     **kwargs: Any) -> dict[str, Any]:
    """Writes ceiling metadata to the official key."""
    ext = _ensure_ext(group)
    payload = dict(data or {})
    payload.update(kwargs)
    payload["kind"] = KIND_CEILING
    if ext is not None:
        ext["trazomob"] = payload
        ext["trazomob_ceiling"] = payload
    return payload


def set_wall_data(group: Any, data: dict[str, Any] | None = None,
                  **kwargs: Any) -> dict[str, Any]:
    """Writes wall metadata to the official key."""
    ext = _ensure_ext(group)
    payload = dict(data or {})
    payload.update(kwargs)
    payload["kind"] = KIND_WALL
    if ext is not None:
        ext["trazomob"] = payload
        ext["trazomob_wall"] = payload
    return payload


# --- Re-exports and canonical cabinetry typing helpers ---

def is_module(group: Any) -> bool:
    """Returns whether the group is a parametric module (including legacy ones)."""
    if kind_of(group) == KIND_MODULE:
        return True
    ext = getattr(group, "ext", None)
    if not isinstance(ext, dict):
        return False
    return "trazomob_module" in ext


def is_assembly(group: Any) -> bool:
    """Returns whether the group is a module container created by this plugin."""
    return kind_of(group) == KIND_ASSEMBLY


def iter_module_groups(roots: Any) -> Any:
    """Walks the tree and yields parametric modules at any depth."""
    from ..domain.assembly import iter_module_groups as _iter_mg
    return _iter_mg(roots)

