# SPDX-License-Identifier: GPL-3.0-or-later
"""Ferramentas de Alinhamento e Centralização de Objetos no Espaço 3D (TrazoMob).

Permite centralizar um objeto móvel em relação a um objeto base (ou vice-versa),
ou alinhar faces/bordas nos eixos X (largura), Y (profundidade) e Z (altura).
Suporta Groups de marcenaria, peças soltas, e entidades em geral com histórico Undo/Redo.
"""
from __future__ import annotations

from typing import Optional, Tuple, List
from PySide6.QtGui import QVector3D
from core.group import Group, iter_placements
from core.history import MoveGroupCommand, CompoundCommand


_MESH_LOCAL_BOUNDS_CACHE: dict[int, tuple] = {}
_MAX_MESH_BOUNDS_CACHE = 4096


def _mesh_local_bounds(mesh) -> Optional[Tuple[float, float, float, float, float, float]]:
    """Retorna e armazena em cache a AABB local de uma malha sem materializar DeferredMesh."""
    if mesh is None:
        return None
    mesh_id = id(mesh)
    mut_serial = getattr(mesh, "_mut_serial", 0)
    is_deferred = type(mesh).__name__ == "DeferredMesh"

    if is_deferred:
        d = mesh.__dict__
        src = d.get("_deferred_source")
        plan = d.get("_deferred_plan")
        key = ("deferred", mut_serial, id(src), id(plan))
        cached = _MESH_LOCAL_BOUNDS_CACHE.get(mesh_id)
        if cached is not None and cached[0] == key:
            return cached[1]
        try:
            from core.group import _local_points
            pts = _local_points(mesh)
        except Exception:
            pts = None
        if pts is None or len(pts) == 0:
            return None
        mn = pts.min(axis=0)
        mx = pts.max(axis=0)
        bounds = (float(mn[0]), float(mx[0]), float(mn[1]), float(mx[1]), float(mn[2]), float(mx[2]))
    else:
        verts = getattr(mesh, "vertices", None)
        if not verts:
            return None
        n_v = len(verts)
        p0 = getattr(verts[0], "position", verts[0])
        p_last = getattr(verts[-1], "position", verts[-1])
        key = (
            mut_serial,
            n_v,
            (float(p0.x()), float(p0.y()), float(p0.z())),
            (float(p_last.x()), float(p_last.y()), float(p_last.z())),
        )
        cached = _MESH_LOCAL_BOUNDS_CACHE.get(mesh_id)
        if cached is not None and cached[0] == key:
            return cached[1]

        min_x = min_y = min_z = float("inf")
        max_x = max_y = max_z = float("-inf")
        for v in verts:
            p = getattr(v, "position", v)
            x, y, z = p.x(), p.y(), p.z()
            if x < min_x:
                min_x = x
            if x > max_x:
                max_x = x
            if y < min_y:
                min_y = y
            if y > max_y:
                max_y = y
            if z < min_z:
                min_z = z
            if z > max_z:
                max_z = z
        bounds = (min_x, max_x, min_y, max_y, min_z, max_z)

    if len(_MESH_LOCAL_BOUNDS_CACHE) >= _MAX_MESH_BOUNDS_CACHE:
        _MESH_LOCAL_BOUNDS_CACHE.clear()
    _MESH_LOCAL_BOUNDS_CACHE[mesh_id] = (key, bounds)
    return bounds


def get_entity_world_bounds(entity) -> Optional[Tuple[float, float, float, float, float, float]]:
    """Retorna os limites AABB (min_x, max_x, min_y, max_y, min_z, max_z) em metros no espaço global."""
    if entity is None:
        return None

    # Se for um Group ou módulo
    if isinstance(entity, Group):
        min_x, max_x = float("inf"), float("-inf")
        min_y, max_y = float("inf"), float("-inf")
        min_z, max_z = float("inf"), float("-inf")
        found = False

        for pg, xf in iter_placements(entity):
            lb = _mesh_local_bounds(getattr(pg, "mesh", None))
            if lb is None:
                continue
            lx0, lx1, ly0, ly1, lz0, lz1 = lb
            if xf is None or (hasattr(xf, "isIdentity") and xf.isIdentity()):
                if lx0 < min_x:
                    min_x = lx0
                if lx1 > max_x:
                    max_x = lx1
                if ly0 < min_y:
                    min_y = ly0
                if ly1 > max_y:
                    max_y = ly1
                if lz0 < min_z:
                    min_z = lz0
                if lz1 > max_z:
                    max_z = lz1
                found = True
            else:
                for cx in (lx0, lx1):
                    for cy in (ly0, ly1):
                        for cz in (lz0, lz1):
                            p = xf.map(QVector3D(cx, cy, cz))
                            px, py, pz = p.x(), p.y(), p.z()
                            if px < min_x:
                                min_x = px
                            if px > max_x:
                                max_x = px
                            if py < min_y:
                                min_y = py
                            if py > max_y:
                                max_y = py
                            if pz < min_z:
                                min_z = pz
                            if pz > max_z:
                                max_z = pz
                            found = True

        if found:
            return (min_x, max_x, min_y, max_y, min_z, max_z)

    # Se for uma Face ou Edge solta
    pts = []
    if hasattr(entity, "vertices"):
        pts = [getattr(v, "position", v) for v in entity.vertices]
    elif hasattr(entity, "a") and hasattr(entity, "b"):
        pts = [entity.a, entity.b]

    if pts:
        xs = [p.x() for p in pts]
        ys = [p.y() for p in pts]
        zs = [p.z() for p in pts]
        return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))

    return None


def center_objects(
    target_group: Group,
    reference_entity,
    axes: str = "xy",
    viewport=None
) -> Optional[QVector3D]:
    """Centraliza `target_group` em relação a `reference_entity`.

    :param target_group: Objeto / Grupo que será movido.
    :param reference_entity: Objeto / Grupo / Parede de referência que ficará parado.
    :param axes: 'x' (apenas largura), 'y' (apenas profundidade), 'z' (apenas altura),
                 'xy' (plano horizontal), ou 'xyz' (centro tridimensional completo).
    :param viewport: Instância do viewport do IngeTrazo para executar o comando com Undo/Redo.
    :return: Vetor delta aplicado, ou None em caso de falha.
    """
    if target_group is None or reference_entity is None:
        return None
    if target_group is reference_entity:
        return None

    b_target = get_entity_world_bounds(target_group)
    b_ref = get_entity_world_bounds(reference_entity)

    if not b_target or not b_ref:
        return None

    # Centros atuais
    c_target_x = (b_target[0] + b_target[1]) * 0.5
    c_target_y = (b_target[2] + b_target[3]) * 0.5
    c_target_z = (b_target[4] + b_target[5]) * 0.5

    c_ref_x = (b_ref[0] + b_ref[1]) * 0.5
    c_ref_y = (b_ref[2] + b_ref[3]) * 0.5
    c_ref_z = (b_ref[4] + b_ref[5]) * 0.5

    dx = (c_ref_x - c_target_x) if "x" in axes.lower() else 0.0
    dy = (c_ref_y - c_target_y) if "y" in axes.lower() else 0.0
    dz = (c_ref_z - c_target_z) if "z" in axes.lower() else 0.0

    delta = QVector3D(dx, dy, dz)
    if delta.length() < 1e-5:
        if viewport and hasattr(viewport, "flash_status"):
            viewport.flash_status("Objetos já estão centralizados!")
        return delta

    if viewport and hasattr(viewport, "history"):
        cmd = MoveGroupCommand(target_group, delta)
        viewport.history.execute(cmd)
        if hasattr(viewport, "notify_scene_changed"):
            viewport.notify_scene_changed()
        viewport.update()

        # Mensagem de feedback na barra de status
        axes_label = axes.upper()
        if hasattr(viewport, "flash_status"):
            name_t = getattr(target_group, "name", "Objeto")
            name_r = getattr(reference_entity, "name", "Referência")
            viewport.flash_status(f"🎯 Centralizado [{axes_label}]: {name_t} em relação a {name_r}")

    return delta


def align_objects(
    target_group: Group,
    reference_entity,
    mode: str = "drop_top_center",
    viewport=None,
) -> Optional[QVector3D]:
    """Alinha ou apoia `target_group` em relação a `reference_entity`.

    Modos suportados:
    - 'drop_top_center': Pousa/Apoia em cima (Z_base = Z_topo_ref) e centraliza em X e Y (ideal para colchão na cama, enfeite na bancada).
    - 'drop_top': Apenas pousa em cima no eixo Z (Z_base = Z_topo_ref) sem mexer no plano XY.
    - 'flush_bottom': Alinha a base com a base da referência (Z_min = Z_min).
    - 'flush_top': Nivelamento pelo topo (Z_max = Z_max).
    - 'flush_left': Alinha a lateral esquerda com a lateral esquerda da referência (X_min = X_min).
    - 'flush_right': Alinha a lateral direita com a lateral direita da referência (X_max = X_max).
    - 'flush_back': Alinha a face traseira com a face traseira da referência (Y_max = Y_max).
    - 'flush_front': Alinha a face frontal com a face frontal da referência (Y_min = Y_min).
    - 'touch_right': Encosta a lateral esquerda do alvo na lateral direita da referência (X_min_alvo = X_max_ref).
    - 'touch_left': Encosta a lateral direita do alvo na lateral esquerda da referência (X_max_alvo = X_min_ref).
    - 'touch_front': Encosta a traseira do alvo na frente da referência (Y_min_alvo = Y_max_ref).
    - 'touch_back': Encosta a frente do alvo na traseira da referência (Y_max_alvo = Y_min_ref).

    :param target_group: Objeto que será movido.
    :param reference_entity: Objeto fixo de referência.
    :param mode: Nome do modo de alinhamento.
    :param viewport: Viewport do IngeTrazo com histórico Undo/Redo.
    :return: Vetor delta aplicado.
    """
    if target_group is None or reference_entity is None:
        return None
    if target_group is reference_entity:
        return None

    b_target = get_entity_world_bounds(target_group)
    b_ref = get_entity_world_bounds(reference_entity)

    if not b_target or not b_ref:
        return None

    # Limites (min_x, max_x, min_y, max_y, min_z, max_z)
    t_min_x, t_max_x, t_min_y, t_max_y, t_min_z, t_max_z = b_target
    r_min_x, r_max_x, r_min_y, r_max_y, r_min_z, r_max_z = b_ref

    c_target_x = (t_min_x + t_max_x) * 0.5
    c_target_y = (t_min_y + t_max_y) * 0.5
    c_ref_x = (r_min_x + r_max_x) * 0.5
    c_ref_y = (r_min_y + r_max_y) * 0.5

    dx = 0.0
    dy = 0.0
    dz = 0.0
    mode_label = mode

    if mode == "drop_top_center":
        # Apoia a base do alvo no topo da referência e centraliza horizontalmente
        dz = r_max_z - t_min_z
        dx = c_ref_x - c_target_x
        dy = c_ref_y - c_target_y
        mode_label = "Apoiado no Topo e Centralizado"
    elif mode == "drop_top":
        dz = r_max_z - t_min_z
        mode_label = "Apoiado no Topo (Z)"
    elif mode == "flush_bottom":
        dz = r_min_z - t_min_z
        mode_label = "Bases Niveladas (Z)"
    elif mode == "flush_top":
        dz = r_max_z - t_max_z
        mode_label = "Topos Nivelados (Z)"
    elif mode == "flush_left":
        dx = r_min_x - t_min_x
        mode_label = "Laterais Esquerdas Alinhadas (X)"
    elif mode == "flush_right":
        dx = r_max_x - t_max_x
        mode_label = "Laterais Direitas Alinhadas (X)"
    elif mode == "flush_back":
        dy = r_max_y - t_max_y
        mode_label = "Traseiras Alinhadas (Y)"
    elif mode == "flush_front":
        dy = r_min_y - t_min_y
        mode_label = "Frentes Alinhadas (Y)"
    elif mode == "touch_right":
        dx = r_max_x - t_min_x
        mode_label = "Encostado à Direita"
    elif mode == "touch_left":
        dx = r_min_x - t_max_x
        mode_label = "Encostado à Esquerda"
    elif mode == "touch_front":
        dy = r_max_y - t_min_y
        mode_label = "Encostado na Frente"
    elif mode == "touch_back":
        dy = r_min_y - t_max_y
        mode_label = "Encostado Atrás"

    delta = QVector3D(dx, dy, dz)
    if delta.length() < 1e-5:
        if viewport and hasattr(viewport, "flash_status"):
            viewport.flash_status("Objetos já estão na posição de alinhamento desejada!")
        return delta

    if viewport and hasattr(viewport, "history"):
        cmd = MoveGroupCommand(target_group, delta)
        viewport.history.execute(cmd)
        if hasattr(viewport, "notify_scene_changed"):
            viewport.notify_scene_changed()
        viewport.update()

        if hasattr(viewport, "flash_status"):
            name_t = getattr(target_group, "name", "Objeto")
            name_r = getattr(reference_entity, "name", "Referência")
            viewport.flash_status(f"🎯 {mode_label}: {name_t} ➔ {name_r}")

    return delta


def _is_group_like(obj) -> bool:
    """Identifica um nó estilo ``Group`` (inclusive doubles de teste)."""
    if obj is None:
        return False
    if isinstance(obj, Group):
        return True
    # Faces e Edges têm vertices/edges ou a/b, mas não têm children nem xform
    return hasattr(obj, "children") or hasattr(obj, "xform")


def _is_locked_architecture(obj) -> bool:
    """Retorna True para paredes/pisos/tetos estruturais ou grupos travados."""
    if obj is None:
        return True
    if getattr(obj, "motion_locked", False) or getattr(obj, "locked", False):
        return True
    ext = getattr(obj, "ext", None)
    if isinstance(ext, dict):
        if ext.get("motion_locked") or ext.get("locked"):
            return True
        if (
            ext.get("kind") in ("wall", "floor", "ceiling")
            or "trazomob_wall" in ext
            or "trazomob_floor" in ext
            or "trazomob_ceiling" in ext
        ):
            return True
    layer = str(getattr(obj, "layer", "") or "").strip().lower()
    return layer in ("parede", "paredes", "piso", "pisos", "teto", "forro")


def _group_matches_item(grp, item) -> bool:
    """Verifica se ``item`` é o próprio grupo ou um sub-elemento de sua malha."""
    if grp is item:
        return True
    if _is_group_like(item):
        return False
    mesh = getattr(grp, "mesh", None)
    if mesh is not None:
        if mesh is item:
            return True
        if getattr(item, "owner", None) is grp:
            return True
        if getattr(item, "mesh", None) is mesh:
            return True
    return False


def _find_group_path(grp, item, visited: set[int]):
    """Retorna a cadeia de grupos [raiz, ..., dono] se ``item`` pertencer a ``grp``."""
    if grp is None or id(grp) in visited:
        return None
    visited.add(id(grp))

    if _group_matches_item(grp, item):
        return [grp]
    for child in (getattr(grp, "children", None) or []):
        sub = _find_group_path(child, item, visited)
        if sub is not None:
            return [grp] + sub
    return None


def resolve_rotatable_groups(scene, candidates=None) -> list[Group]:
    """Resolve quais grupos rotacionáveis correspondem à seleção atual.

    Aceita módulos TrazoMob, grupos genéricos da cena, móveis importados,
    eletros, instâncias de componente (``xform``), luminárias e esquadrias.
    Paredes, pisos e entidades explicitamente travadas são ignorados.
    """
    raw = list(candidates) if candidates is not None else list(getattr(scene, "selection", None) or [])
    if not raw:
        return []

    top_groups = list(getattr(scene, "groups", None) or [])
    top_ids = {id(g) for g in top_groups}
    resolved: list[Group] = []
    seen: set[int] = set()

    for item in raw:
        if item is None:
            continue
        target = None
        upward_chain: list[Any] = []
        cur = item
        visited_up: set[int] = set()
        while cur is not None and id(cur) not in visited_up:
            visited_up.add(id(cur))
            upward_chain.append(cur)
            if id(cur) in top_ids:
                break
            cur = getattr(cur, "owner", None) or getattr(cur, "parent", None)

        if upward_chain and id(upward_chain[-1]) in top_ids:
            for node in reversed(upward_chain):
                if _is_group_like(node) and not _is_locked_architecture(node):
                    target = node
                    break
        else:
            for top_g in top_groups:
                path = _find_group_path(top_g, item, set())
                if path:
                    for node in path:
                        if _is_group_like(node) and not _is_locked_architecture(node):
                            target = node
                            break
                    if target is not None:
                        break
            if target is None:
                for node in reversed(upward_chain):
                    if _is_group_like(node) and not _is_locked_architecture(node):
                        target = node
                        break

        if target is not None and id(target) not in seen:
            seen.add(id(target))
            resolved.append(target)

    return resolved


def _combined_bounds_center(groups: list[Group]) -> Optional[QVector3D]:
    """Calcula o centro da AABB combinada de uma lista de grupos."""
    min_x = min_y = min_z = float("inf")
    max_x = max_y = max_z = float("-inf")
    found = False
    for g in groups:
        b = get_entity_world_bounds(g)
        if b is None:
            continue
        min_x = min(min_x, b[0])
        max_x = max(max_x, b[1])
        min_y = min(min_y, b[2])
        max_y = max(max_y, b[3])
        min_z = min(min_z, b[4])
        max_z = max(max_z, b[5])
        found = True
    if not found:
        return None
    return QVector3D(
        (min_x + max_x) * 0.5,
        (min_y + max_y) * 0.5,
        (min_z + max_z) * 0.5,
    )


def rotate_groups_with_command(
    groups: list[Group],
    degrees: float,
    viewport,
    axis: tuple[float, float, float] | QVector3D = (0.0, 0.0, 1.0),
) -> list[Group]:
    """Executa rotação reversível (Undo/Redo) para um ou vários grupos selecionados."""
    valid = [g for g in (groups or []) if g is not None and not _is_locked_architecture(g)]
    if not valid or viewport is None:
        return []

    from ..builders.cabinet import RotateTrazoMobModuleCommand

    if len(valid) == 1:
        cmd = RotateTrazoMobModuleCommand(valid[0], degrees, axis=axis, viewport=viewport)
    else:
        center = _combined_bounds_center(valid)
        cmds = [
            RotateTrazoMobModuleCommand(g, degrees, center=center, axis=axis, viewport=viewport)
            for g in valid
        ]
        cmd = CompoundCommand(cmds)

    history = getattr(viewport, "history", None)
    if history is not None:
        history.execute(cmd)
    else:
        cmd.do(getattr(viewport, "scene", None))

    if hasattr(viewport, "notify_scene_changed"):
        viewport.notify_scene_changed()
    if hasattr(viewport, "update"):
        viewport.update()
    return valid

