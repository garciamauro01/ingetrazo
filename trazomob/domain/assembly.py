# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Agrupamento seguro de módulos do TrazoMob (assemblies).

O IngeTrazo já sabe agrupar grupos (``MakeNestedGroupCommand``) e desagrupar
(``ExplodeGroupCommand``), mas o resultado não é reconhecido pelo TrazoMob:

* a lista de corte só varria ``scene.groups`` — módulos dentro de um grupo
  desapareciam do cutlist;
* a barra lateral só encontrava módulos no primeiro nível — selecionar o
  grupo deixava o editor vazio.

Este módulo marca o contêiner com ``kind="assembly"`` e oferece a varredura
recursiva que os leitores usam. As duas operações reutilizam os comandos do
core, então posição, transformação e undo/redo continuam sendo os do app.
"""
from __future__ import annotations

from typing import Any, Iterable, Iterator, List, Optional

from core.group import Group
from core.history import ExplodeGroupCommand, MakeNestedGroupCommand

from ..domain.schema import KIND_MODULE, kind_of

#: ``kind`` gravado no ``ext`` do contêiner que agrupa módulos.
ASSEMBLY_KIND = "assembly"


def is_assembly(group: Any) -> bool:
    """Diz se o grupo é um contêiner de módulos criado por este plugin."""
    return kind_of(group) == ASSEMBLY_KIND


def is_module(group: Any) -> bool:
    """Diz se o grupo é um módulo paramétrico (inclusive os legados)."""
    if kind_of(group) == KIND_MODULE:
        return True
    ext = getattr(group, "ext", None)
    if not isinstance(ext, dict):
        return False
    return "trazomob_module" in ext


def assembly_members(group: Any) -> List[Any]:
    """Filhos diretos de um assembly (módulos e subgrupos)."""
    if not is_assembly(group):
        return []
    return list(getattr(group, "children", None) or [])


def iter_module_groups(roots: Iterable[Any]) -> Iterator[Any]:
    """Varre a árvore e devolve os módulos paramétricos em qualquer nível.

    Não desce para dentro de um módulo: os filhos de um módulo são peças, não
    módulos. Contêineres nativos (feitos com o "Criar Grupo" do app) também
    são atravessados, para o cutlist não perder módulos agrupados à mão.
    """
    for group in roots:
        if group is None:
            continue
        if is_module(group):
            yield group
            continue
        children = getattr(group, "children", None) or []
        if children:
            yield from iter_module_groups(children)


def _tag_assembly(container: Group, name: Optional[str] = None) -> Group:
    """Grava o ``kind`` de assembly no contêiner, preservando o que já havia."""
    ext = getattr(container, "ext", None)
    if not isinstance(ext, dict):
        ext = {}
        container.ext = ext
    data = ext.get("trazomob")
    if not isinstance(data, dict):
        data = {}
    data["kind"] = ASSEMBLY_KIND
    if name:
        data["nome"] = str(name)
    data["membros"] = [
        getattr(child, "uid", None)
        for child in (getattr(container, "children", None) or [])
    ]
    ext["trazomob"] = data
    return container


def build_assembly_command(
    groups: Iterable[Any],
    name: Optional[str] = None,
) -> Optional[MakeNestedGroupCommand]:
    """Prepara o comando que agrupa módulos, ou ``None`` se não há o que agrupar.

    Devolve o comando (em vez de executá-lo) para o chamador rodá-lo pelo
    ``viewport.history`` e ganhar undo/redo de graça.
    """
    members = [g for g in groups if isinstance(g, Group)]
    if len(members) < 2:
        return None
    return MakeNestedGroupCommand([], [], members, name=name)


def apply_assembly_tag(container: Optional[Group], name: Optional[str] = None) -> Optional[Group]:
    """Marca o contêiner devolvido pelo comando como assembly do TrazoMob."""
    if container is None:
        return None
    return _tag_assembly(container, name)


def build_dissolve_command(assembly: Any) -> Optional[ExplodeGroupCommand]:
    """Prepara o comando que devolve os módulos ao nível do modelo.

    O ``ExplodeGroupCommand`` do core levanta os filhos inteiros (com
    ``xform`` composto) e mantém o undo — nenhum metadado de módulo é tocado.
    """
    if not isinstance(assembly, Group) or not is_assembly(assembly):
        return None
    if not (getattr(assembly, "children", None) or []):
        return None
    return ExplodeGroupCommand(assembly)


def modules_in_selection(scene: Any) -> List[Group]:
    """Módulos selecionados diretamente (ignora peças e contêineres)."""
    selection = getattr(scene, "selection", None) or ()
    return [item for item in selection if isinstance(item, Group) and is_module(item)]


def selected_assembly(scene: Any) -> Optional[Group]:
    """Assembly selecionado, se houver exatamente um."""
    selection = getattr(scene, "selection", None) or ()
    assemblies = [item for item in selection if isinstance(item, Group) and is_assembly(item)]
    return assemblies[0] if len(assemblies) == 1 else None
