# SPDX-License-Identifier: GPL-3.0-or-later
"""Undoable document edits for Furniture Pro.

Adding, replacing and deleting a module changes two things at once: the
``scene.groups`` membership and the project payload in
``scene.plugin_data``.  ``SnapshotImport`` does not restore removed groups on
undo, so these operations use one explicit command that owns both halves.
Undo puts the *same* group objects back, preserving identity for later history
steps and for the project browser.
"""
from __future__ import annotations

import json

from ..core.constants import PLUGIN_KEY

try:                                                    # pragma: no cover - host
    from core.history import Command
except Exception:                                       # noqa: BLE001
    class Command:                                      # type: ignore[no-redef]
        """Minimal stand-in so the adapter can be imported without a host."""

        def do(self, scene) -> None:                    # pragma: no cover
            raise NotImplementedError

        def undo(self, scene) -> None:                  # pragma: no cover
            raise NotImplementedError


def _copy(value):
    return None if value is None else json.loads(json.dumps(value))


class GroupsEditCommand(Command):
    """Replace group membership and the project payload as one undo step."""

    keeps_groups = True

    def __init__(self, added=None, removed=None, *, before_data=None,
                 after_data=None, description: str = "") -> None:
        self.added = list(added or [])
        self.removed = list(removed or [])
        self.before_data = _copy(before_data)
        self.after_data = _copy(after_data)
        self.description = description
        self._removed_indices: list[tuple[int, object]] = []
        self._added_present: list[object] = []

    # -- document data -------------------------------------------------------
    def _write_data(self, scene, value) -> None:
        data = scene.plugin_data
        if value is None:
            data.pop(PLUGIN_KEY, None)
        else:
            data[PLUGIN_KEY] = _copy(value)

    # -- command -------------------------------------------------------------
    def do(self, scene) -> None:
        self._removed_indices = []
        for group in self.removed:
            groups = scene.groups
            for index, current in enumerate(list(groups)):
                if current is group:
                    self._removed_indices.append((index, group))
                    groups.pop(index)
                    break
            scene.selection.discard(group)
        self._added_present = []
        for group in self.added:
            if group not in scene.groups:
                scene.groups.append(group)
                self._added_present.append(group)
        self._write_data(scene, self.after_data)
        scene.version += 1

    def undo(self, scene) -> None:
        for group in self._added_present:
            if group in scene.groups:
                scene.groups.remove(group)
            scene.selection.discard(group)
        self._added_present = []
        # Reinsert removed groups at their original positions, highest index
        # first so earlier indices stay valid.
        for index, group in sorted(self._removed_indices, key=lambda p: p[0],
                                   reverse=True):
            if group in scene.groups:
                continue
            target = max(0, min(len(scene.groups), index))
            scene.groups.insert(target, group)
        self._removed_indices = []
        self._write_data(scene, self.before_data)
        scene.version += 1


class ReplaceGroupCommand(GroupsEditCommand):
    """Replace one module group in place (same position in the scene)."""

    def __init__(self, old_group, new_group, *, before_data=None,
                 after_data=None, description: str = "") -> None:
        super().__init__(added=[new_group], removed=[old_group],
                         before_data=before_data, after_data=after_data,
                         description=description)
        self.old_group = old_group
        self.new_group = new_group


def add_module_command(group, before_data, after_data) -> GroupsEditCommand:
    return GroupsEditCommand(added=[group], before_data=before_data,
                             after_data=after_data, description="Inserir módulo")


def remove_module_command(group, before_data,
                          after_data) -> GroupsEditCommand:
    return GroupsEditCommand(removed=[group], before_data=before_data,
                             after_data=after_data, description="Excluir módulo")


def replace_module_command(old_group, new_group, before_data,
                           after_data) -> ReplaceGroupCommand:
    return ReplaceGroupCommand(old_group, new_group, before_data=before_data,
                               after_data=after_data,
                               description="Editar módulo")
