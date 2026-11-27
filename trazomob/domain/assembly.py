# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Safe grouping of TrazoMob modules (assemblies).

IngeTrazo already knows how to group groups (``MakeNestedGroupCommand``) and
ungroup them (``ExplodeGroupCommand``), but the result is not recognized by
TrazoMob:

* the cutlist only scanned ``scene.groups`` — modules inside a group
  disappeared from the cutlist;
* the sidebar only found top-level modules — selecting the group left the
  editor empty.

This module tags the container with ``kind="assembly"`` and provides the
recursive traversal used by readers. Both operations reuse the core commands,
so position, transform, and undo/redo remain handled by the app.
"""
from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

from core.group import Group
from core.history import ExplodeGroupCommand, MakeNestedGroupCommand

from ..domain.schema import KIND_MODULE, kind_of

#: ``kind`` stored in the ``ext`` of the container that groups modules.
ASSEMBLY_KIND = "assembly"


def is_assembly(group: Any) -> bool:
    """Returns whether the group is a module container created by this plugin."""
    return kind_of(group) == ASSEMBLY_KIND


def is_module(group: Any) -> bool:
    """Returns whether the group is a parametric module (including legacy ones)."""
    if kind_of(group) == KIND_MODULE:
        return True
    ext = getattr(group, "ext", None)
    if not isinstance(ext, dict):
        return False
    return "trazomob_module" in ext


def assembly_members(group: Any) -> list[Any]:
    """Direct children of an assembly (modules and subgroups)."""
    if not is_assembly(group):
        return []
    return list(getattr(group, "children", None) or [])


def iter_module_groups(roots: Iterable[Any]) -> Iterator[Any]:
    """Walks the tree and yields parametric modules at any depth.

    Does not descend inside a module: a module's children are parts, not
    modules. Native containers (created with the app's "Create Group") are
    also traversed so the cutlist does not lose manually grouped modules.
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


def _tag_assembly(container: Group, name: str | None = None) -> Group:
    """Stores the assembly ``kind`` on the container, preserving existing fields."""
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
    name: str | None = None,
) -> MakeNestedGroupCommand | None:
    """Prepares the command that groups modules, or ``None`` if there is nothing to group.

    Returns the command (instead of executing it) so the caller can run it via
    ``viewport.history`` and get undo/redo for free.
    """
    members = [g for g in groups if isinstance(g, Group)]
    if len(members) < 2:
        return None
    return MakeNestedGroupCommand([], [], members, name=name)


def apply_assembly_tag(container: Group | None, name: str | None = None) -> Group | None:
    """Marks the container returned by the command as a TrazoMob assembly."""
    if container is None:
        return None
    return _tag_assembly(container, name)


def build_dissolve_command(assembly: Any) -> ExplodeGroupCommand | None:
    """Prepares the command that returns modules to the model level.

    Core's ``ExplodeGroupCommand`` lifts the children intact (with composed
    ``xform``) and preserves undo — no module metadata is touched.
    """
    if not isinstance(assembly, Group) or not is_assembly(assembly):
        return None
    if not (getattr(assembly, "children", None) or []):
        return None
    return ExplodeGroupCommand(assembly)


def modules_in_selection(scene: Any) -> list[Group]:
    """Directly selected modules (ignores parts and containers)."""
    selection = getattr(scene, "selection", None) or ()
    return [item for item in selection if isinstance(item, Group) and is_module(item)]


def selected_assembly(scene: Any) -> Group | None:
    """Selected assembly, if there is exactly one."""
    selection = getattr(scene, "selection", None) or ()
    assemblies = [item for item in selection if isinstance(item, Group) and is_assembly(item)]
    return assemblies[0] if len(assemblies) == 1 else None
