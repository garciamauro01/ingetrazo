# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Operacoes de transformacao 3D do CabinetBuilder."""
from __future__ import annotations

import logging
import math
from typing import Any

from PySide6.QtGui import QMatrix4x4, QVector3D

from core.group import Group

logger = logging.getLogger("trazomob.cabinet_transform")


def _seed_subtree_proto_chunks(node: Any, viewport: Any, visited: set[int] | None = None) -> None:
    """Preserva chunks ja assados no cache do prototipo antes de promover ``xform``."""
    if node is None or viewport is None:
        return
    cache = getattr(viewport, "_group_chunks", None)
    if not isinstance(cache, dict):
        return
    if visited is None:
        visited = set()
    if id(node) in visited:
        return
    visited.add(id(node))
    if getattr(node, "xform", None) is not None:
        return

    mesh = getattr(node, "mesh", None)
    if mesh is not None:
        src_entry = cache.get(id(node))
        if src_entry is not None:
            try:
                from views.viewport import _paint_of, _proto_wrapper
                wrapper = _proto_wrapper(viewport, mesh, _paint_of(viewport, node))
                cache.setdefault(id(wrapper), dict(src_entry))
            except Exception:
                pass

    for child in (getattr(node, "children", None) or ()):
        _seed_subtree_proto_chunks(child, viewport, visited)


def _invalidate_transformed_caches(
    mutated_nodes: list[Any],
    promoted_nodes: list[Any],
    scene: Any,
    viewport: Any,
) -> None:
    """Invalida apenas os chunks dos nos alterados, preservando o restante da cena."""
    group_chunks = getattr(viewport, "_group_chunks", None) if viewport is not None else None
    inst_chunks = getattr(viewport, "_inst_chunks", None) if viewport is not None else None

    for node in mutated_nodes:
        mesh = getattr(node, "mesh", None)
        if mesh is not None:
            mesh._chunk_dirty = True
            mesh._attrs_dirty = True
        if isinstance(group_chunks, dict):
            group_chunks.pop(id(node), None)
        if isinstance(inst_chunks, dict):
            inst_chunks.pop(id(node), None)

    for node in promoted_nodes:
        if isinstance(group_chunks, dict):
            group_chunks.pop(id(node), None)

    if scene is not None:
        scene.version = getattr(scene, "version", 0) + 1

    if viewport is not None:
        if hasattr(viewport, "_placements_memo"):
            viewport._placements_memo = None
        if hasattr(viewport, "_epoch_same"):
            viewport._epoch_same = None
        if hasattr(viewport, "_static_occl_memo"):
            viewport._static_occl_memo = None
        if hasattr(viewport, "_sil_table"):
            viewport._sil_table = None


def invalidate_replaced_modules_caches(replacements, viewport) -> None:
    """Invalida só os chunks dos módulos substituídos por ``build_module_group``.

    Um Apply reconstrói o grupo inteiro com novos ids; os chunks antigos
    (keyed por ``id(group)``/``id(child)``/``id(proxy)``) ficam órfãos. Limpar
    ``_group_chunks``/``_inst_chunks`` inteiros — como o Apply fazia — força o
    rebake de VBOs e pick arrays de TODA a cena (paredes, importações grandes),
    que é a maior parcela dos ~5 s ao trocar a textura da marmoraria. O viewport
    já revalida os demais grupos em O(1) por ``_mut_serial`` (ver
    ``Viewport._group_chunk``), então remover somente os ids afetados é
    suficiente e seguro.

    ``replacements`` é uma lista de pares ``(old_group, new_group)``.
    """
    if not replacements or viewport is None:
        return

    group_chunks = getattr(viewport, "_group_chunks", None)
    inst_chunks = getattr(viewport, "_inst_chunks", None)
    proxies = getattr(viewport, "_placement_proxies", None)
    tops = getattr(viewport, "_placement_tops", None)

    stale: set[int] = set()

    def collect(node, visited):
        if node is None:
            return
        nid = id(node)
        if nid in visited:
            return
        visited.add(nid)
        stale.add(nid)
        for child in (getattr(node, "children", None) or ()):
            collect(child, visited)

    for old_group, _new_group in replacements:
        collect(old_group, set())

    # Proxies de placement são keyed por id(child) e seus chunks por id(proxy).
    if isinstance(proxies, dict):
        for cid in list(stale):
            proxy = proxies.get(cid)
            if proxy is not None:
                stale.add(id(proxy))

    if isinstance(group_chunks, dict):
        for gid in stale:
            group_chunks.pop(gid, None)
    if isinstance(inst_chunks, dict):
        for gid in stale:
            inst_chunks.pop(gid, None)
    if isinstance(proxies, dict):
        for gid in stale:
            proxies.pop(gid, None)
    if isinstance(tops, dict):
        for gid in stale:
            tops.pop(gid, None)

    for attr in ("_placements_memo", "_epoch_same", "_static_occl_memo", "_sil_table"):
        if hasattr(viewport, attr):
            setattr(viewport, attr, None)


def _rotate_group_ext(ext: Any, m) -> None:
    """Atualiza vetores auxiliares armazenados no dicionário ``ext`` após rotação."""
    if not isinstance(ext, dict):
        return
    if "orig_vertices" in ext:
        ext["orig_vertices"] = [m.map(orig) for orig in ext["orig_vertices"]]
    if "slide_delta" in ext and isinstance(ext["slide_delta"], QVector3D):
        ext["slide_delta"] = m.mapVector(ext["slide_delta"])
    if "slide_axis" in ext and isinstance(ext["slide_axis"], QVector3D):
        ext["slide_axis"] = m.mapVector(ext["slide_axis"]).normalized()
    if "flap_axis" in ext and isinstance(ext["flap_axis"], QVector3D):
        ext["flap_axis"] = m.mapVector(ext["flap_axis"]).normalized()
    if "hinge_pivot" in ext and isinstance(ext["hinge_pivot"], QVector3D):
        ext["hinge_pivot"] = m.map(ext["hinge_pivot"])


def _rotate_group_tree(
    grp: Any,
    m,
    visited: set[int],
    *,
    viewport: Any = None,
    scene: Any = None,
    mutated_nodes: list[Any] | None = None,
    promoted_nodes: list[Any] | None = None,
) -> None:
    """Rotaciona um Group em O(1) via ``xform`` quando seguro ou por vertices em modulos."""
    if grp is None or id(grp) in visited:
        return
    visited.add(id(grp))

    from core.group import _remap_uvws, carry_axes

    xf = getattr(grp, "xform", None)
    ext_dict = getattr(grp, "ext", None)
    is_trazomob_meta = isinstance(ext_dict, dict) and any(
        k in ext_dict for k in ("trazomob_module", "trazomob_esquadria", "trazomob", "trazomob_hardware")
    )
    is_light_meta = isinstance(ext_dict, dict) and "trazomob_light" in ext_dict
    is_trazomob_world_identity = xf is not None and xf.isIdentity() and is_trazomob_meta

    if xf is not None and not is_trazomob_world_identity:
        grp.xform = m * xf
        carry_axes(grp, m)
        _rotate_group_ext(ext_dict, m)
        return

    # Objetos genericos (ex.: modelos 3D importados com xform=None) sao promovidos para xform
    # em O(1) para evitar iterar dezenas/centenas de milhares de vertices em Python.
    edit_group = getattr(scene, "edit_group", None) if scene is not None else None
    if (
        isinstance(grp, Group)
        and xf is None
        and not is_trazomob_meta
        and not is_light_meta
        and edit_group is not grp
    ):
        _seed_subtree_proto_chunks(grp, viewport)
        grp.component = bool(grp.is_component())
        grp.xform = QMatrix4x4(m)
        carry_axes(grp, m)
        _rotate_group_ext(ext_dict, m)
        if promoted_nodes is not None:
            promoted_nodes.append(grp)
        return

    mesh = getattr(grp, "mesh", None)
    if mesh is not None and getattr(mesh, "vertices", None):
        for v in mesh.vertices:
            v.position = m.map(v.position)
        try:
            _remap_uvws(mesh, m)
        except Exception:
            pass
        mesh._mut_serial = getattr(mesh, "_mut_serial", 0) + 1
        mesh._chunk_dirty = True
        mesh._attrs_dirty = True
        if mutated_nodes is not None:
            mutated_nodes.append(grp)

    carry_axes(grp, m)
    _rotate_group_ext(ext_dict, m)

    for child in (getattr(grp, "children", None) or []):
        _rotate_group_tree(
            child,
            m,
            visited,
            viewport=viewport,
            scene=scene,
            mutated_nodes=mutated_nodes,
            promoted_nodes=promoted_nodes,
        )


def _rotate_light_metadata(ext: Any, m, m_dir) -> bool:
    """Atualiza coordenadas e direção de luminária TrazoMob após rotação."""
    if not isinstance(ext, dict) or not isinstance(ext.get("trazomob_light"), dict):
        return False
    lt = ext["trazomob_light"]
    for key in ("pos", "p1", "p2", "target"):
        val = lt.get(key)
        if isinstance(val, (list, tuple)) and len(val) >= 3:
            p_rot = m.map(QVector3D(float(val[0]), float(val[1]), float(val[2])))
            lt[key] = [round(p_rot.x(), 4), round(p_rot.y(), 4), round(p_rot.z(), 4)]
    dir_val = lt.get("dir")
    if isinstance(dir_val, (list, tuple)) and len(dir_val) >= 3:
        d_rot = m_dir.mapVector(QVector3D(float(dir_val[0]), float(dir_val[1]), float(dir_val[2])))
        if d_rot.length() > 1e-6:
            d_rot = d_rot.normalized()
        lt["dir"] = [round(d_rot.x(), 4), round(d_rot.y(), 4), round(d_rot.z(), 4)]
    return True


def _rotate_esquadria_metadata(ext: Any, m, axis_vec: QVector3D, degrees: float) -> None:
    """Sincroniza ``rot_z`` e ``offset`` quando uma esquadria TrazoMob é rotacionada."""
    if not isinstance(ext, dict) or not isinstance(ext.get("trazomob_esquadria"), dict):
        return
    esq = ext["trazomob_esquadria"]
    ax_norm = axis_vec.normalized()
    is_z_axis = abs(ax_norm.x()) < 1e-4 and abs(ax_norm.y()) < 1e-4 and abs(ax_norm.z()) > 0.5
    if is_z_axis:
        eff_deg_z = degrees if ax_norm.z() >= 0.0 else -degrees
        esq["rot_z"] = (float(esq.get("rot_z", 0.0) or 0.0) + eff_deg_z) % 360.0
    old_off = esq.get("offset")
    if isinstance(old_off, (list, tuple)) and len(old_off) >= 3:
        off_rot = m.map(QVector3D(float(old_off[0]), float(old_off[1]), float(old_off[2])))
        esq["offset"] = (float(off_rot.x()), float(off_rot.y()), float(off_rot.z()))


class CabinetTransformMixin:
    """Rotacao e redimensionamento parametrico de modulos e objetos."""

    @classmethod
    def resolve_rotation_center(cls, target_group: Group) -> QVector3D:
        """Retorna o ponto central adequado para rotacionar um módulo ou objeto genérico."""
        if target_group is None:
            return QVector3D(0.0, 0.0, 0.0)
        ext = getattr(target_group, "ext", None)
        bounds = None
        if isinstance(ext, dict) and "trazomob_module" in ext:
            from ..domain.module_geometry import get_module_carcass_bounds
            bounds = get_module_carcass_bounds(target_group)
        if bounds is None:
            from ..interaction.align_tools import get_entity_world_bounds
            bounds = get_entity_world_bounds(target_group)
        if bounds is not None:
            return QVector3D(
                (bounds[0] + bounds[1]) * 0.5,
                (bounds[2] + bounds[3]) * 0.5,
                (bounds[4] + bounds[5]) * 0.5,
            )
        return QVector3D(0.0, 0.0, 0.0)

    @classmethod
    def rotate_module(
        cls,
        module_group: Group,
        degrees: float,
        center: tuple[float, float, float] | QVector3D | None = None,
        axis: tuple[float, float, float] | QVector3D = (0.0, 0.0, 1.0),
        scene=None,
        viewport=None,
        update_param: bool = True,
    ) -> bool:
        """Rotaciona um módulo do TrazoMob ou qualquer Group/objeto da cena pelo ângulo em graus.

        Suporta:
        - Módulo mestre contendo peças em ``module_group.children``.
        - Qualquer Group genérico, mobília, eletro, instância com ``xform``, luminária ou esquadria.
        - Peça individual com malha direta ``module_group.mesh``.
        - Atualização dos metadados e ``orig_vertices`` para preservação da cinemática interativa.
        """
        if module_group is None:
            return False

        from core.history import rotation_matrix

        # Converte o eixo para QVector3D
        if isinstance(axis, QVector3D):
            axis_vec = axis
        else:
            axis_vec = QVector3D(*axis)

        ext_root = getattr(module_group, "ext", None)
        needs_carcass_update = bool(
            update_param and isinstance(ext_root, dict) and "trazomob_module" in ext_root
        )
        carcass_center_before = (
            cls.resolve_rotation_center(module_group)
            if (center is None or needs_carcass_update)
            else None
        )

        # Determina o centro de rotação efetivo
        if center is None:
            center_vec = carcass_center_before
        elif isinstance(center, QVector3D):
            center_vec = center
        else:
            center_vec = QVector3D(*center)

        m = rotation_matrix(center_vec, axis_vec, degrees)
        m_dir = rotation_matrix(QVector3D(0.0, 0.0, 0.0), axis_vec, degrees)

        mutated_nodes: list[Any] = []
        promoted_nodes: list[Any] = []
        _rotate_group_tree(
            module_group,
            m,
            set(),
            viewport=viewport,
            scene=scene,
            mutated_nodes=mutated_nodes,
            promoted_nodes=promoted_nodes,
        )

        # Atualiza a rotação acumulada do módulo se solicitado (evita somar duas vezes durante build_module_group)
        if needs_carcass_update:
            from ..domain.schema import live_module_data
            mod_p = live_module_data(module_group)
            ax_norm = axis_vec.normalized()
            is_z_axis = abs(ax_norm.x()) < 1e-4 and abs(ax_norm.y()) < 1e-4 and abs(ax_norm.z()) > 0.5

            if is_z_axis:
                eff_deg_z = degrees if ax_norm.z() >= 0.0 else -degrees
                old_rot = float(mod_p.get("rot_z", 0.0) or 0.0)
                mod_p["rot_z"] = (old_rot + eff_deg_z) % 360.0
                # Se já possuía matriz 3D customizada, compõe a rotação Z nela também
                if "rot_matrix_3d" in mod_p and isinstance(mod_p["rot_matrix_3d"], (list, tuple)) and len(mod_p["rot_matrix_3d"]) == 16:
                    m_prev = QMatrix4x4(*[float(x) for x in mod_p["rot_matrix_3d"]])
                    m_step = rotation_matrix(QVector3D(0.0, 0.0, 0.0), ax_norm, degrees)
                    m_comb = m_step * m_prev
                    mod_p["rot_matrix_3d"] = [float(m_comb(r, c)) for r in range(4) for c in range(4)]
            else:
                # Rotação 3D livre (em X, Y ou eixo arbitrário): preserva a matriz 3D exata!
                if "rot_matrix_3d" in mod_p and isinstance(mod_p["rot_matrix_3d"], (list, tuple)) and len(mod_p["rot_matrix_3d"]) == 16:
                    m_prev = QMatrix4x4(*[float(x) for x in mod_p["rot_matrix_3d"]])
                else:
                    old_rot = float(mod_p.get("rot_z", 0.0) or 0.0)
                    m_prev = rotation_matrix(QVector3D(0.0, 0.0, 0.0), QVector3D(0.0, 0.0, 1.0), old_rot)
                m_step = rotation_matrix(QVector3D(0.0, 0.0, 0.0), ax_norm, degrees)
                m_comb = m_step * m_prev
                mod_p["rot_matrix_3d"] = [float(m_comb(r, c)) for r in range(4) for c in range(4)]

            # Sincroniza o offset base usando o deslocamento real do centro da caixaria (new_center - old_center)
            # e preservando a relação exata com as dimensões não-rotacionadas da peça/módulo!
            new_carcass_center = m.map(carcass_center_before)
            unrot_span = mod_p.get("_unrot_carcass_span")
            if isinstance(unrot_span, (list, tuple)) and len(unrot_span) == 6:
                mod_p["offset"] = (
                    float(new_carcass_center.x()) - float(unrot_span[0]),
                    float(new_carcass_center.y()) - float(unrot_span[1]),
                    float(new_carcass_center.z()) - float(unrot_span[2]),
                )
            else:
                delta_c = new_carcass_center - carcass_center_before
                old_off = mod_p.get("offset", (0.0, 0.0, 0.0))
                if isinstance(old_off, (list, tuple)) and len(old_off) >= 3:
                    mod_p["offset"] = (
                        float(old_off[0]) + float(delta_c.x()),
                        float(old_off[1]) + float(delta_c.y()),
                        float(old_off[2]) + float(delta_c.z()),
                    )

        ext_root = getattr(module_group, "ext", None)
        if update_param:
            _rotate_esquadria_metadata(ext_root, m, axis_vec, degrees)
        has_light_meta = _rotate_light_metadata(ext_root, m, m_dir)

        _invalidate_transformed_caches(mutated_nodes, promoted_nodes, scene, viewport)

        if viewport is not None:
            if has_light_meta:
                try:
                    from ..render.lighting import sync_scene_lights_to_document
                    sync_scene_lights_to_document(viewport)
                except Exception as exc:
                    logger.debug("sync_scene_lights_to_document falhou após rotação: %s", exc)
            viewport.update()

        return True

    @classmethod
    def scale_module(
        cls,
        module_group: Group,
        center: tuple[float, float, float] | QVector3D,
        factor: float | tuple[float, float, float] | list[float],
        axes=None,
        scene=None,
        viewport=None,
        update_param: bool = True,
        rebuild: bool = True,
    ) -> bool:
        """Escala um módulo do TrazoMob (e todas as suas peças filhas) em torno de ``center``
        e sincroniza automaticamente suas dimensões paramétricas (`largura`, `profundidade`, `altura`)
        e sua âncora (`offset`, `_unrot_carcass_span`) em ``module_group.ext['trazomob_module']``.
        Se ``rebuild=True`` e ``update_param=True``, regenera parametricamente os componentes filhos
        para preservar rigorosamente as espessuras de chapas (MDF 15/18mm) e ferragens sem distorção.
        """
        if module_group is None:
            return False

        from core.history import scale_matrix
        from core.group import _remap_uvws, carry_axes

        center_vec = center if isinstance(center, QVector3D) else QVector3D(*center)
        m = scale_matrix(center_vec, factor, axes)

        children = getattr(module_group, "children", []) or []
        targets = children if children else [module_group]
        scaled_nodes: list[Any] = []

        for t in targets:
            mesh = getattr(t, "mesh", None)
            if mesh and hasattr(mesh, "vertices"):
                for v in list(mesh.vertices):
                    mesh.move_vertex(v, m.map(v.position) - v.position)
                _remap_uvws(mesh, m)
                mesh._mut_serial = getattr(mesh, "_mut_serial", 0) + 1
                scaled_nodes.append(t)
            carry_axes(t, m)
            if getattr(t, "ext", None) is not None:
                if "orig_vertices" in t.ext and isinstance(t.ext["orig_vertices"], list):
                    t.ext["orig_vertices"] = [m.map(orig) for orig in t.ext["orig_vertices"] if isinstance(orig, QVector3D)]
                if "slide_delta" in t.ext and isinstance(t.ext["slide_delta"], QVector3D):
                    t.ext["slide_delta"] = m.mapVector(t.ext["slide_delta"])
                if "hinge_pivot" in t.ext and isinstance(t.ext["hinge_pivot"], QVector3D):
                    t.ext["hinge_pivot"] = m.map(t.ext["hinge_pivot"])

        if update_param and getattr(module_group, "ext", None) is not None and "trazomob_module" in module_group.ext:
            from ..domain.schema import live_module_data
            mod_p = live_module_data(module_group)
            tipo = str(mod_p.get("tipo", ""))
            rot_z = float(mod_p.get("rot_z", 0.0) or 0.0)
            rot_mat_3d = mod_p.get("rot_matrix_3d")

            if isinstance(rot_mat_3d, (list, tuple)) and len(rot_mat_3d) == 16:
                m_rot = QMatrix4x4(*[float(x) for x in rot_mat_3d])
                ex = m_rot.mapVector(QVector3D(1.0, 0.0, 0.0)).normalized()
                ey = m_rot.mapVector(QVector3D(0.0, 1.0, 0.0)).normalized()
                ez = m_rot.mapVector(QVector3D(0.0, 0.0, 1.0)).normalized()
            else:
                rad = math.radians(rot_z)
                ex = QVector3D(math.cos(rad), math.sin(rad), 0.0)
                ey = QVector3D(-math.sin(rad), math.cos(rad), 0.0)
                ez = QVector3D(0.0, 0.0, 1.0)

            s_x = m.mapVector(ex).length()
            s_y = m.mapVector(ey).length()
            s_z = m.mapVector(ez).length()

            if s_x > 1e-6 and s_y > 1e-6 and s_z > 1e-6:
                # Mapeia os fatores de escala locais (s_x, s_y, s_z) para os parâmetros de marcenaria:
                if tipo == "peca_lateral":
                    # Lateral avulsa: X local é espessura (E), Y local é profundidade (P), Z local é altura (A)
                    if abs(s_y - 1.0) > 1e-4 and "profundidade" in mod_p:
                        mod_p["profundidade"] = round(float(mod_p["profundidade"]) * s_y, 2)
                    if abs(s_z - 1.0) > 1e-4 and "altura" in mod_p:
                        mod_p["altura"] = round(float(mod_p["altura"]) * s_z, 2)
                elif tipo in ("peca_porta", "peca_fundo", "peca_travessa_em_pe", "peca_pilar_quina"):
                    # Chapa frontal/vertical em XZ: X local é largura (L), Y local é espessura (E), Z local é altura (A)
                    if abs(s_x - 1.0) > 1e-4 and "largura" in mod_p:
                        mod_p["largura"] = round(float(mod_p["largura"]) * s_x, 2)
                    if abs(s_z - 1.0) > 1e-4 and "altura" in mod_p:
                        mod_p["altura"] = round(float(mod_p["altura"]) * s_z, 2)
                    if abs(s_y - 1.0) > 1e-4 and "profundidade" in mod_p:
                        mod_p["profundidade"] = round(float(mod_p["profundidade"]) * s_y, 2)
                else:
                    # Todos os armários, balcões, bancadas, tampo engrossado, base, prateleira, travessa deitada:
                    # X local é largura (L), Y local é profundidade (P), Z local é altura (A)
                    if abs(s_x - 1.0) > 1e-4 and "largura" in mod_p:
                        mod_p["largura"] = round(float(mod_p["largura"]) * s_x, 2)
                    if abs(s_y - 1.0) > 1e-4 and "profundidade" in mod_p:
                        mod_p["profundidade"] = round(float(mod_p["profundidade"]) * s_y, 2)
                    if abs(s_z - 1.0) > 1e-4 and "altura" in mod_p:
                        mod_p["altura"] = round(float(mod_p["altura"]) * s_z, 2)

                # Limitação rígida (Clamp) de marcenaria: não permite que dimensões ultrapassem o limite útil da chapa (2720mm)
                from ..domain.materials_catalog import CHAPA_MAX_COMPRIMENTO_UTIL_MM
                for dim_key in ("largura", "altura", "profundidade"):
                    if dim_key in mod_p and isinstance(mod_p[dim_key], (int, float)):
                        if mod_p[dim_key] > CHAPA_MAX_COMPRIMENTO_UTIL_MM:
                            mod_p[dim_key] = CHAPA_MAX_COMPRIMENTO_UTIL_MM

                from ..domain.module_geometry import get_module_carcass_bounds
                from ..interaction.magnetic_drag import get_module_bounds
                b_after = get_module_carcass_bounds(module_group) or get_module_bounds(module_group)
                if b_after is not None:
                    cx_a = (b_after[0] + b_after[1]) * 0.5
                    cy_a = (b_after[2] + b_after[3]) * 0.5
                    cz_a = (b_after[4] + b_after[5]) * 0.5
                    unrot_span = mod_p.get("_unrot_carcass_span")
                    if isinstance(unrot_span, (list, tuple)) and len(unrot_span) == 6:
                        new_span = (
                            float(unrot_span[0]) * s_x,
                            float(unrot_span[1]) * s_y,
                            float(unrot_span[2]) * s_z,
                            float(unrot_span[3]) * s_x,
                            float(unrot_span[4]) * s_y,
                            float(unrot_span[5]) * s_z,
                        )
                        mod_p["_unrot_carcass_span"] = new_span
                        mod_p["offset"] = (
                            float(cx_a - new_span[0]),
                            float(cy_a - new_span[1]),
                            float(cz_a - new_span[2]),
                        )
                    else:
                        L_m = float(mod_p.get("largura", 800.0)) / 1000.0
                        P_m = float(mod_p.get("profundidade", 550.0)) / 1000.0
                        mod_p["offset"] = (
                            float(cx_a - L_m * 0.5),
                            float(cy_a - P_m * 0.5),
                            float(b_after[4]),
                        )

                    # Se solicitado o rearranjo paramétrico, regenera as peças filhas
                    # mantendo a espessura de chapas de MDF (15/18mm) e ferragens sem distorção.
                    if rebuild:
                        try:
                            cls._rebuild_scaled_module_pieces(module_group, mod_p, b_after)
                        except Exception:
                            logger.debug("Falha ao reconstruir peças do módulo redimensionado", exc_info=True)

        _invalidate_transformed_caches(scaled_nodes, [], scene, viewport)
        if viewport is not None:
            viewport.update()

        return True

    @classmethod
    def _rebuild_scaled_module_pieces(
        cls,
        module_group: Group,
        mod_p: dict[str, Any],
        b_after: tuple[float, float, float, float, float, float],
    ) -> None:
        """Regenera in-place as peças componentes de um módulo de marcenaria escalado,
        garantindo espessuras nominais fiéis de MDF (15/18mm) e ferragens sem deformação.
        """
        from ..builders.cabinet import CabinetBuilder
        from ..domain.module_geometry import get_module_carcass_bounds
        from ..interaction.magnetic_drag import get_module_bounds

        params_build = dict(mod_p)
        offset = params_build.get("offset", (0.0, 0.0, 0.0))
        if not isinstance(offset, (list, tuple)) or len(offset) < 3:
            offset = (0.0, 0.0, 0.0)
        offset = tuple(float(v) for v in offset)

        new_mod = CabinetBuilder.build_module_group(params_build, offset=offset)
        if new_mod is None:
            return

        b_new = get_module_carcass_bounds(new_mod) or get_module_bounds(new_mod)
        if b_after and b_new:
            shift = QVector3D(
                b_after[0] - b_new[0],
                b_after[2] - b_new[2],
                b_after[4] - b_new[4],
            )
            if shift.length() > 1e-7:
                targets = getattr(new_mod, "children", []) or [new_mod]
                for t in targets:
                    m_sub = getattr(t, "mesh", None)
                    if m_sub and hasattr(m_sub, "vertices"):
                        for v in m_sub.vertices:
                            v.position += shift
                        m_sub._mut_serial = getattr(m_sub, "_mut_serial", 0) + 1
                    if getattr(t, "ext", None) is not None:
                        if "orig_vertices" in t.ext:
                            t.ext["orig_vertices"] = [orig + shift for orig in t.ext["orig_vertices"]]
                        if "hinge_pivot" in t.ext and isinstance(t.ext["hinge_pivot"], QVector3D):
                            t.ext["hinge_pivot"] += shift

        # Atualiza o grupo mestre in-place com a geometria e peças reconstruídas
        for c in new_mod.children:
            c.owner = module_group
        module_group.children = list(new_mod.children)
        module_group.name = new_mod.name
        if hasattr(new_mod, "mesh") and new_mod.mesh is not None:
            module_group.mesh = new_mod.mesh
        if hasattr(new_mod, "ext") and isinstance(new_mod.ext, dict):
            # Preserva os metadados calculados
            for k, val in new_mod.ext.items():
                if k not in module_group.ext or k in ("trazomob_module", "trazomob_esquadria"):
                    module_group.ext[k] = val

