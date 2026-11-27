# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""TrazoMob **Room** (*Ambiente*) and **Floor** (*Pavimento*) entities.

A **Room** is a logical container that groups:
* walls (existing manifold solids)
* floor (slab/subfloor)
* ceiling/drop ceiling
* list of parametric modules belonging to that room

A **Floor** groups rooms at the same Z level (ground floor, 1st floor, ...).
Allows toggling visibility for the entire floor and computing total area.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from core.group import Group
from core.mesh import Mesh

if TYPE_CHECKING:
    from core.history import Command

from ..domain.schema import (
    KIND_AMBIENTE,
    KIND_CEILING,
    KIND_FLOOR,
    KIND_MODULE,
    KIND_PAVIMENTO,
    KIND_WALL,
    ambiente_params,
    is_kind,
    pavimento_params,
    set_ambiente_data,
    set_ceiling_data,
    set_floor_data,
    set_pavimento_data,
    update_ambiente_data,
    update_pavimento_data,
)

# ---------------------------------------------------------------------------
# Type helpers
# ---------------------------------------------------------------------------

def is_ambiente(group: Any) -> bool:
    """Return whether the group is a TrazoMob room."""
    return is_kind(group, KIND_AMBIENTE)


def is_pavimento(group: Any) -> bool:
    """Return whether the group is a TrazoMob floor."""
    return is_kind(group, KIND_PAVIMENTO)


# ---------------------------------------------------------------------------
# Tree iterators
# ---------------------------------------------------------------------------

def iter_ambientes(groups: Iterable[Any]) -> Iterable[Group]:
    """Traverse the tree (including nested groups) and yield only rooms."""
    for g in groups:
        if is_ambiente(g):
            yield g
        for child in getattr(g, "children", None) or []:
            yield from iter_ambientes([child])


def iter_pavimentos(groups: Iterable[Any]) -> Iterable[Group]:
    """Traverse the tree and yield only floors."""
    for g in groups:
        if is_pavimento(g):
            yield g
        for child in getattr(g, "children", None) or []:
            yield from iter_pavimentos([child])


def iter_modulos_do_ambiente(ambiente: Group) -> Iterable[Group]:
    """Yield parametric modules that are direct children of the room."""
    for child in getattr(ambiente, "children", None) or []:
        if is_kind(child, KIND_MODULE):
            yield child


def iter_paredes_do_ambiente(ambiente: Group) -> Iterable[Group]:
    """Yield walls that are direct children of the room."""
    for child in getattr(ambiente, "children", None) or []:
        if is_kind(child, KIND_WALL):
            yield child


def iter_pisos_do_ambiente(ambiente: Group) -> Iterable[Group]:
    """Yield floors/slabs that are direct children of the room."""
    for child in getattr(ambiente, "children", None) or []:
        if is_kind(child, KIND_FLOOR):
            yield child


def iter_tetos_do_ambiente(ambiente: Group) -> Iterable[Group]:
    """Yield ceilings/drop ceilings that are direct children of the room."""
    for child in getattr(ambiente, "children", None) or []:
        if is_kind(child, KIND_CEILING):
            yield child


def ambiente_do_modulo(modulo: Group) -> Group | None:
    """Walk up the hierarchy to find the parent room of the module."""
    # In IngeTrazo, the parent is not directly exposed; scan the scene instead.
    # Callers should pass the scene or the list of rooms.
    return None  # Implemented via scene lookup if needed


# ---------------------------------------------------------------------------
# Geometry calculations
# ---------------------------------------------------------------------------

def _bounds_do_grupo(group: Group) -> tuple[float, float, float, float, float, float] | None:
    """Return (minx, maxx, miny, maxy, minz, maxz) in meters for the group and its children."""
    xs, ys, zs = [], [], []
    for child in getattr(group, "children", None) or []:
        mesh = getattr(child, "mesh", None)
        if mesh and hasattr(mesh, "vertices"):
            xform = getattr(child, "xform", None)
            for v in mesh.vertices:
                p = xform.map(v.position) if xform is not None else v.position
                xs.append(p.x())
                ys.append(p.y())
                zs.append(p.z())
        # recursive
        b = _bounds_do_grupo(child)
        if b:
            xs.extend([b[0], b[1]])
            ys.extend([b[2], b[3]])
            zs.extend([b[4], b[5]])
    if not xs:
        return None
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def calcular_area_ambiente(ambiente: Group) -> float:
    """Room area in m² (XY projection of the floor slab or wall bounds)."""
    # Try using the floor first
    for piso in iter_pisos_do_ambiente(ambiente):
        mesh = getattr(piso, "mesh", None)
        if mesh and hasattr(mesh, "vertices") and mesh.vertices:
            # XY projection of the floor mesh
            xs = [v.position.x() for v in mesh.vertices]
            ys = [v.position.y() for v in mesh.vertices]
            return (max(xs) - min(xs)) * (max(ys) - min(ys))
    # Fallback: wall bounds
    b = _bounds_do_grupo(ambiente)
    if b:
        return (b[1] - b[0]) * (b[3] - b[2])
    return 0.0


def calcular_pe_direito_ambiente(ambiente: Group) -> float:
    """Room ceiling height in meters (ceiling Z - floor Z)."""
    z_piso = None
    z_teto = None
    for piso in iter_pisos_do_ambiente(ambiente):
        mesh = getattr(piso, "mesh", None)
        if mesh and mesh.vertices:
            zs = [v.position.z() for v in mesh.vertices]
            z_piso = max(zs)  # top of slab
            break
    for teto in iter_tetos_do_ambiente(ambiente):
        mesh = getattr(teto, "mesh", None)
        if mesh and mesh.vertices:
            zs = [v.position.z() for v in mesh.vertices]
            z_teto = min(zs)  # bottom of ceiling
            break
    if z_piso is not None and z_teto is not None:
        return max(0.0, z_teto - z_piso)
    # Fallback: greatest height among the room's walls. A low wall
    # cannot define the ceiling height for the others.
    alturas = []
    for parede in iter_paredes_do_ambiente(ambiente):
        mesh = getattr(parede, "mesh", None)
        if mesh and mesh.vertices:
            zs = [v.position.z() for v in mesh.vertices]
            alturas.append(max(zs) - min(zs))
    if alturas:
        return max(alturas)
    return 2.7  # default


# ---------------------------------------------------------------------------
# Room builder from 2D floorplan (integration with wall_plan_2d)
# ---------------------------------------------------------------------------

class AmbienteBuilder:
    """Build the Room group with walls, floor, ceiling, and metadata."""

    @staticmethod
    def build_ambiente_group(
        nome: str,
        paredes: list[Group],
        piso: Group | None,
        teto: Group | None,
        pavimento_nome: str = "Térreo",
        z_base: float = 0.0,
        pe_direito: float = 2.7,
    ) -> Group:
        """
        Create the Room group adopting walls, floor, and ceiling as children.

        Walls already come from ``WallPlan2D.build_3d_group`` (or similar).
        Floor and ceiling come from ``wall_mesh_builder``.
        """
        # Create the master room group
        master = Group(Mesh(), name=nome)

        filhos_iniciais = list(paredes)

        # Floor
        if piso is not None:
            filhos_iniciais.append(piso)
            schema_set = getattr(piso, "ext", None)
            if isinstance(schema_set, dict):
                set_floor_data(piso, {"ambiente": nome})

        # Ceiling
        if teto is not None:
            filhos_iniciais.append(teto)
            schema_set = getattr(teto, "ext", None)
            if isinstance(schema_set, dict):
                set_ceiling_data(teto, {"ambiente": nome})

        master.adopt(filhos_iniciais)

        # Room metadata
        area = calcular_area_ambiente(master)
        pe_dir = calcular_pe_direito_ambiente(master) or pe_direito

        set_ambiente_data(master, {
            "nome": nome,
            "pavimento": pavimento_nome,
            "z_base": z_base,
            "pe_direito": pe_dir,
            "area_m2": round(area, 2),
            "visivel": True,
        })

        return master

    @staticmethod
    def ensure_pavimento(scene_groups: list[Group], nome: str, z_base: float = 0.0) -> Group:
        """Ensure a Floor group with this name exists; create it if missing."""
        for g in scene_groups:
            if is_pavimento(g):
                params = pavimento_params(g)
                if params.get("nome") == nome:
                    if z_base > 0 and params.get("z_base", 0.0) == 0.0:
                        update_pavimento_data(g, {"z_base": z_base})
                    return g
        # Create new one and add to the scene list if provided
        pav = Group(Mesh(), name=nome)
        set_pavimento_data(pav, {"nome": nome, "z_base": z_base, "visivel": True})
        if scene_groups is not None and pav not in scene_groups:
            scene_groups.append(pav)
        return pav

    @classmethod
    def criar_pavimento(cls, scene_groups: list[Group], nome: str, z_base: float = 0.0) -> Group:
        """Alias for explicit floor creation."""
        return cls.ensure_pavimento(scene_groups, nome, z_base=z_base)

    @staticmethod
    def adicionar_ao_pavimento(pavimento: Group, ambiente: Group) -> None:
        """Adopt the room into the floor (without duplicating if already present)."""
        atuais = list(getattr(pavimento, "children", None) or [])
        if ambiente not in atuais:
            atuais.append(ambiente)
            pavimento.adopt(atuais)


# ---------------------------------------------------------------------------
# Command to group modules into a room (for the sidebar)
# ---------------------------------------------------------------------------

def build_ambiente_command(
    modulos: list[Group],
    nome: str,
    pavimento_nome: str = "Térreo",
) -> "Command" | None:
    """
    Create a command that groups the selected modules into a new Room.

    Reuses ``MakeNestedGroupCommand`` from core and marks it as a room.
    """
    if len(modulos) < 1:
        return None

    from core.history import MakeNestedGroupCommand

    # Create an empty group that will become the room
    container = Group(Mesh(), name=nome)
    cmd = MakeNestedGroupCommand(modulos, container=container, name=nome)

    # Wrapper to mark as room after execution
    class _AmbienteWrapper:
        def __init__(self, inner_cmd, pavimento_nome):
            self.inner = inner_cmd
            self.pavimento_nome = pavimento_nome
            self.container = None

        def do(self, scene):
            self.inner.do(scene)
            self.container = self.inner.container
            set_ambiente_data(self.container, {
                "nome": nome,
                "pavimento": self.pavimento_nome,
                "visivel": True,
            })

        def undo(self, scene):
            self.inner.undo(scene)

    return _AmbienteWrapper(cmd, pavimento_nome)


def build_dissolve_ambiente_command(ambiente: Group) -> "Command" | None:
    """Create a command to dissolve the room, returning children to the parent level."""
    if not is_ambiente(ambiente):
        return None

    from core.history import ExplodeGroupCommand

    class _DissolveWrapper:
        def __init__(self, inner_cmd):
            self.inner = inner_cmd

        def do(self, scene):
            self.inner.do(scene)

        def undo(self, scene):
            self.inner.undo(scene)

    return _DissolveWrapper(ExplodeGroupCommand(ambiente))


# ---------------------------------------------------------------------------
# Visibility utilities
# ---------------------------------------------------------------------------

def set_ambiente_visivel(ambiente: Group, visivel: bool) -> None:
    """Toggle room visibility and propagate to children."""
    update_ambiente_data(ambiente, {"visivel": visivel})
    if hasattr(ambiente, "hidden"):
        ambiente.hidden = not visivel
    for child in getattr(ambiente, "children", None) or []:
        if hasattr(child, "hidden"):
            child.hidden = not visivel
        child.layer = "Ambientes" if visivel else "Hidden"


def set_pavimento_visivel(pavimento: Group, visivel: bool) -> None:
    """Toggle floor visibility and all of its rooms/children."""
    update_pavimento_data(pavimento, {"visivel": visivel})
    if hasattr(pavimento, "hidden"):
        pavimento.hidden = not visivel
    for item in getattr(pavimento, "children", None) or []:
        if hasattr(item, "hidden"):
            item.hidden = not visivel
        item.layer = "Ambientes" if visivel else "Hidden"
        if is_ambiente(item):
            set_ambiente_visivel(item, visivel)


# ---------------------------------------------------------------------------
# Export for cutlist / reports
# ---------------------------------------------------------------------------

def resumo_ambiente(ambiente: Group) -> dict[str, Any]:
    """Dictionary ready for report/cutlist filtered by room."""
    params = ambiente_params(ambiente)
    modulos = list(iter_modulos_do_ambiente(ambiente))
    return {
        "nome": params.get("nome", ambiente.name),
        "pavimento": params.get("pavimento", ""),
        "area_m2": params.get("area_m2", 0.0),
        "pe_direito": params.get("pe_direito", 0.0),
        "qtd_modulos": len(modulos),
        "modulos": [m.name for m in modulos],
    }
