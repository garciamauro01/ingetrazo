# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Contratos compartilhados por builders, interação, UI e ganchos do host.

Reúne as três rotinas que antes viviam duplicadas (ou espalhadas) em módulos de
camadas diferentes:

* :func:`is_esquadria` — classificação de portas/janelas, aceita grupo ou id;
* :func:`resolve_igz_path` — resolução do ``.igz`` a partir do manifesto;
* :func:`shift_module_geometry` — translação de malha e metadados cinemáticos.

Os locais antigos continuam reexportando estas funções, então nenhum chamador
precisa mudar.  ``PySide6`` é importado sob demanda para manter este módulo
seguro para os ganchos de integração do host.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..assets.catalog import get_esquadria_files

if TYPE_CHECKING:  # pragma: no cover - apenas para anotações
    from PySide6.QtGui import QVector3D

    from core.group import Group

__all__ = ("is_esquadria", "resolve_igz_path", "shift_module_geometry")


def is_esquadria(value: Any) -> bool:
    """Reconhece uma esquadria pelo ``id`` do modelo ou pelo grupo carregado.

    Aceita tanto um ``str`` (id do catálogo, com os prefixos reservados
    ``porta_``/``janela_``) quanto um ``Group``.  Para grupos, considera as
    chaves canônicas e legadas de metadados, o ``kind`` do schema, o ``tipo``
    e, por fim, a camada ``ESQUADRIAS``.
    """
    if isinstance(value, str):
        return (value in get_esquadria_files()
                or value.startswith("janela_")
                or value.startswith("porta_"))
    if value is None:
        return False

    ext = getattr(value, "ext", None)
    if isinstance(ext, dict):
        if "trazomob_esquadria" in ext:
            return True
        for key in ("trazomob", "trazomob_module"):
            info = ext.get(key)
            if isinstance(info, dict):
                if str(info.get("kind", "")) == "esquadria":
                    return True
                if str(info.get("tipo", "")).startswith(("porta_", "janela_")):
                    return True

    if getattr(value, "layer", "") == "ESQUADRIAS":
        return True

    # Schema canônico: cobre grupos gravados antes da unificação das chaves.
    try:
        from .schema import kind_of, module_params

        if kind_of(value) == "esquadria":
            return True
        if str(module_params(value).get("tipo", "")).startswith(("porta_", "janela_")):
            return True
    except Exception:  # grupo do host sem metadados do plugin
        pass
    return False


def resolve_igz_path(base_dir: Any, item_id: str) -> Path:
    """Resolve o ``.igz`` de uma esquadria, com portas e janelas em pastas próprias.

    O nome do arquivo é preservado para não afetar os carregadores que
    reconhecem o modelo por ``igz_path.name``. A subpasta vem do prefixo do
    id e é definitiva: janelas só em ``janelas/``, portas só em ``portas/``.
    Não há busca em nenhuma outra pasta.
    """
    components = Path(base_dir) / "assets" / "components"
    subpasta = "janelas" if item_id.startswith("janela_") else "portas"
    mapped = get_esquadria_files().get(item_id)
    arquivo = mapped[0] if mapped else f"{item_id}.igz"
    candidatos = list(dict.fromkeys([
        components / subpasta / f"{item_id}.igz",
        components / subpasta / arquivo,
    ]))
    for candidato in candidatos:
        if candidato.exists():
            return candidato
    # Nenhum arquivo encontrado: devolve o caminho canônico ao chamador.
    return candidatos[0]


def shift_module_geometry(group: "Group", shift: "QVector3D") -> None:
    """Translada vértices e metadados cinemáticos de todas as peças de um módulo."""
    from PySide6.QtGui import QVector3D

    if shift.length() <= 1e-7:
        return
    targets = getattr(group, "children", []) or [group]
    for t in targets:
        m_sub = getattr(t, "mesh", None)
        if m_sub and hasattr(m_sub, "vertices"):
            for v in m_sub.vertices:
                v.position += shift
            m_sub._mut_serial = getattr(m_sub, "_mut_serial", 0) + 1
        t_ext = getattr(t, "ext", None)
        if isinstance(t_ext, dict):
            if "orig_vertices" in t_ext:
                t_ext["orig_vertices"] = [p + shift for p in t_ext["orig_vertices"]]
            if "hinge_pivot" in t_ext and isinstance(t_ext["hinge_pivot"], QVector3D):
                t_ext["hinge_pivot"] = t_ext["hinge_pivot"] + shift
            tm = t_ext.get("trazomob")
            if isinstance(tm, dict):
                for key in ("rot_origin", "hinge_pivot"):
                    orig_pt = tm.get(key)
                    if isinstance(orig_pt, QVector3D):
                        tm[key] = orig_pt + shift
                    elif isinstance(orig_pt, (list, tuple)) and len(orig_pt) == 3:
                        shifted = (
                            float(orig_pt[0]) + shift.x(),
                            float(orig_pt[1]) + shift.y(),
                            float(orig_pt[2]) + shift.z(),
                        )
                        tm[key] = list(shifted) if isinstance(orig_pt, list) else shifted
