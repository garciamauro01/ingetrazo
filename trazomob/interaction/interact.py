# SPDX-License-Identifier: GPL-3.0-or-later

# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.

"""Interatividade dinâmica: abertura e fechamento de portas e gavetas."""

from __future__ import annotations



import math

from typing import Any



from PySide6.QtCore import Qt

from PySide6.QtGui import QMatrix4x4, QVector3D



from core.group import Group

from tools.base import Tool, ToolContext





class CabinetInteract:

    """Controlador de abertura e fechamento interativo de portas e gavetas."""



    @staticmethod

    def is_interactive_piece(name: str) -> bool:

        if not name:

            return False

        n = name.lower()

        if n.startswith("ferragem -"):

            return False

        if "travessa" in n or "contra-frente" in n or "lateral" in n or "rodape" in n or "rodapé" in n or "divisoria" in n or "divisória" in n:

            return False

        if "marco" in n or "alisar" in n or "trilho" in n or "batente" in n:

            return False

        if "puxador" in n or "fechadura" in n or "maçaneta" in n or "macaneta" in n or "braçadeira" in n or "bracadeira" in n:

            return False

        return any(k in n for k in ["porta", "gaveta", "frente", "basc", "folha", "cama auxiliar"])



    @classmethod

    def get_piece_interaction_type(cls, name: str) -> str | None:

        """Retorna 'drawer', 'door_flap', 'door_right', 'door_left' ou None."""

        if not name:

            return None

        n = name.lower()

        # Não confunde peças da estrutura externa (laterais, travessas, divisórias, rodapé) com portas ou gavetas

        if "travessa" in n or "divisoria" in n or "divisória" in n or "rodape" in n or "rodapé" in n or "tampo" in n:

            return None

        if "lateral" in n and "gaveta" not in n:

            return None

        if "base" in n and "gaveta" not in n:

            return None

        if "prateleira" in n:

            return None

        if "fundo" in n and "gaveta" not in n:

            return None

        if "puxador" in n or "fechadura" in n or "maçaneta" in n or "macaneta" in n or "braçadeira" in n or "bracadeira" in n or n.startswith("ferragem -"):

            return None



        # Identifica peças de gaveta (frente, laterais da caixa, contra-frentes, fundo da gaveta, cama auxiliar)

        if "gaveta" in n or "cf " in n or "contra-frente" in n or "cama auxiliar" in n or ("frente" in n and "porta" not in n):

            return "drawer"

        if ("basc" in n or "basculante" in n) and ("porta" in n or "folha" in n or "frente" in n or "tampa" in n):

            return "door_flap"

        if "canto" in n and "porta" in n:

            if "ala x" in n or "plano x" in n:

                return "door_canto_l_x"

            if "ala y" in n or "plano y" in n:

                return "door_canto_l_y"

        if "porta" in n or "folha" in n:

            if "correr" in n or "slide" in n:

                return "door_slide"

            if "dir" in n or "direita" in n:

                return "door_right"

            return "door_left"

        return None



    @classmethod

    def get_drawer_id(cls, name: str) -> str | None:

        """Extrai um identificador da gaveta (ex: 'gaveta_1', 'gaveta_2') ou None se não pertencer a gaveta."""

        import re

        n = name.lower()

        if n.startswith("ferragem -"):

            return None

        if "cama auxiliar" in n:

            return "bicama_aux"

        if "mesinha esq" in n:

            return "gaveta_mesinha_esq"

        if "mesinha dir" in n:

            return "gaveta_mesinha_dir"

        if "gaveta" not in n and "frente" not in n and "contra-frente" not in n and "cf " not in n:

            return None

        m_side = re.search(r"gaveta\s+(dir|esq)\s*(\d+)", n)

        if m_side:

            return f"gaveta_{m_side.group(1)}_{m_side.group(2)}"

        m = re.search(r"(?:gaveta|frente)\s*(\d+)", n)

        if m:

            return f"gaveta_{m.group(1)}"

        return "gaveta_1"


    @staticmethod
    def _collect_linked_children(module_group, piece):
        """Retorna filhos ligados à ``piece`` (por nome ou ``linked_piece``)."""
        result = []
        if module_group is None or not hasattr(module_group, "children") or piece is None:
            return result

        p_name = getattr(piece, "name", "")
        p_ext = getattr(piece, "ext", None)
        linked = p_ext.get("linked_pieces", []) if isinstance(p_ext, dict) else []
        linked_names = list(linked) if isinstance(linked, (list, tuple)) else [linked]

        for child in module_group.children:
            if child is piece:
                continue
            c_ext = getattr(child, "ext", None)
            c_tm = c_ext.get("trazomob", {}) if isinstance(c_ext, dict) else {}
            linked_piece = c_tm.get("linked_piece") if isinstance(c_tm, dict) else None
            if linked_piece == p_name:
                result.append(child)
                continue
            child_name = str(getattr(child, "name", ""))
            if any(key in child_name for key in linked_names if key):
                result.append(child)
        return result




    @classmethod

    def set_piece_open_fraction(

        cls,

        piece: Group,

        fraction: float,

        module_group: Group | None = None,

        scene=None,

        viewport=None,

    ) -> bool:

        """Define o percentual contínuo de abertura (0.0 = fechado, 1.0 = 100% aberto) da peça."""

        if piece is None or not hasattr(piece, "mesh") or not getattr(piece.mesh, "vertices", None):

            return False



        itype = cls.get_piece_interaction_type(getattr(piece, "name", ""))

        if not itype:

            return False



        if getattr(piece, "ext", None) is None:

            piece.ext = {}



        frac = max(0.0, min(1.0, float(fraction)))



        # Resgata rotação e transformação do módulo pai

        rot_z = 0.0

        if module_group and hasattr(module_group, "ext") and isinstance(module_group.ext, dict):

            from ..domain.schema import module_params

            rot_z = float(module_params(module_group).get("rot_z", 0.0) or 0.0)



        from core.group import _remap_uvws



        def _init_uvws_if_needed(target_piece):

            """Garante que todas as faces com textura possuam 'uvw' ancorado antes de qualquer movimento."""

            if not hasattr(target_piece, "mesh") or not getattr(target_piece.mesh, "faces", None):

                return

            from core.texture import face_uv_axes

            for f in target_piece.mesh.faces:

                tex = f.attrs.get("texture") if f.attrs else None

                if tex and "uvw" not in tex:

                    gu, cu, gv, cv = face_uv_axes(tex, f.normal())

                    tex["uvw"] = [

                        gu.x(), gu.y(), gu.z(), cu,

                        gv.x(), gv.y(), gv.z(), cv

                    ]



        def _restore_orig_uvws(target_piece):

            """Restaura os UVWs originais da peça a partir do backup em ext."""

            orig_uvws = target_piece.ext.get("orig_uvws")

            if not orig_uvws or not hasattr(target_piece, "mesh") or not getattr(target_piece.mesh, "faces", None):

                return

            for f, u_saved in zip(target_piece.mesh.faces, orig_uvws):

                if u_saved is not None and f.attrs and "texture" in f.attrs:

                    f.attrs["texture"]["uvw"] = list(u_saved)



        def _backup_orig_uvws(target_piece):

            """Gera backup dos UVWs se ainda não existir."""

            if "orig_uvws" not in target_piece.ext:

                _init_uvws_if_needed(target_piece)

                target_piece.ext["orig_uvws"] = [

                    list(f.attrs["texture"]["uvw"]) if (f.attrs and f.attrs.get("texture") and "uvw" in f.attrs["texture"]) else None

                    for f in target_piece.mesh.faces

                ]



        if itype == "drawer":

            p_ext = getattr(piece, "ext", None) or {}

            explicit_drawer_id = p_ext.get("drawer_id")

            drawer_id = explicit_drawer_id or cls.get_drawer_id(piece.name)

            siblings = [piece]

            if drawer_id and module_group and hasattr(module_group, "children"):

                for child in module_group.children:

                    if child is piece:

                        continue

                    c_ext = getattr(child, "ext", None)

                    c_drawer_id = c_ext.get("drawer_id") if isinstance(c_ext, dict) else None

                    if c_drawer_id:

                        if c_drawer_id == drawer_id:

                            siblings.append(child)

                    elif not explicit_drawer_id and cls.get_drawer_id(getattr(child, "name", "")) == drawer_id:

                        siblings.append(child)

            for linked_child in cls._collect_linked_children(module_group, piece):
                if linked_child not in siblings:
                    siblings.append(linked_child)



            custom_axis = p_ext.get("slide_axis")

            slide_dist = float(p_ext.get("slide_distance", 0.35)) * frac

            if isinstance(custom_axis, QVector3D) and custom_axis.lengthSquared() > 1e-6:

                delta = custom_axis.normalized() * slide_dist

            else:

                rad = math.radians(rot_z)

                delta = QVector3D(slide_dist * math.sin(rad), -slide_dist * math.cos(rad), 0.0)



            m_slide = QMatrix4x4()

            m_slide.translate(delta)



            for p in siblings:

                if getattr(p, "ext", None) is None:

                    p.ext = {}

                p_slide_scale = float(p.ext.get("slide_scale", 1.0))
                p_delta = delta * p_slide_scale

                ov = p.ext.get("orig_vertices")

                if not isinstance(ov, list) or len(ov) != len(p.mesh.vertices) or not all(isinstance(pt, QVector3D) for pt in ov):

                    p.ext["orig_vertices"] = [QVector3D(v.position) for v in p.mesh.vertices]



                _backup_orig_uvws(p)

                _restore_orig_uvws(p)



                for v, orig in zip(p.mesh.vertices, p.ext["orig_vertices"]):

                    v.position = orig + p_delta

                if abs(p_slide_scale - 1.0) < 1e-6:
                    _remap_uvws(p.mesh, m_slide)
                else:
                    m_p_slide = QMatrix4x4()
                    m_p_slide.translate(p_delta)
                    _remap_uvws(p.mesh, m_p_slide)



                p.ext["is_open"] = (frac > 0.05)

                p.ext["open_fraction"] = frac

                if hasattr(p, "mesh") and p.mesh is not None:

                    p.mesh._mut_serial = getattr(p.mesh, "_mut_serial", 0) + 1



        elif itype == "door_flap":

            ov = piece.ext.get("orig_vertices")

            if not isinstance(ov, list) or len(ov) != len(piece.mesh.vertices) or not all(isinstance(pt, QVector3D) for pt in ov):

                piece.ext["orig_vertices"] = [QVector3D(v.position) for v in piece.mesh.vertices]



            from core.history import rotation_matrix

            hp = piece.ext.get("hinge_pivot")

            flap_axis = piece.ext.get("flap_axis")

            if not isinstance(hp, QVector3D) or not isinstance(flap_axis, QVector3D):

                zs = [pt.z() for pt in piece.ext["orig_vertices"]]

                pz = max(zs)

                rad = math.radians(rot_z)

                axis_x = math.cos(rad)

                axis_y = math.sin(rad)

                cand = [pt for pt in piece.ext["orig_vertices"] if abs(pt.z() - pz) < 0.01]

                if cand:

                    px = sum(pt.x() for pt in cand) / len(cand)

                    py = sum(pt.y() for pt in cand) / len(cand)

                else:

                    px, py = piece.ext["orig_vertices"][0].x(), piece.ext["orig_vertices"][0].y()

                hp = QVector3D(px, py, pz)

                flap_axis = QVector3D(axis_x, axis_y, 0.0).normalized()

                piece.ext["hinge_pivot"] = hp

                piece.ext["flap_axis"] = flap_axis



            max_angle = float(piece.ext.get("flap_max_angle_deg", -80.0))

            angle_deg = max_angle * frac

            m_door = rotation_matrix(piece.ext["hinge_pivot"], piece.ext["flap_axis"], angle_deg)

            siblings = [piece] + cls._collect_linked_children(module_group, piece)

            for p in siblings:

                if getattr(p, "ext", None) is None:

                    p.ext = {}

                ov = p.ext.get("orig_vertices")

                if not isinstance(ov, list) or len(ov) != len(p.mesh.vertices) or not all(isinstance(pt, QVector3D) for pt in ov):

                    p.ext["orig_vertices"] = [QVector3D(v.position) for v in p.mesh.vertices]

                _backup_orig_uvws(p)

                _restore_orig_uvws(p)

                for v, orig in zip(p.mesh.vertices, p.ext["orig_vertices"]):

                    v.position = m_door.map(orig)

                _remap_uvws(p.mesh, m_door)

                p.ext["is_open"] = (frac > 0.05)

                p.ext["open_fraction"] = frac

                if hasattr(p, "mesh") and p.mesh is not None:

                    p.mesh._mut_serial = getattr(p.mesh, "_mut_serial", 0) + 1




        elif itype == "door_slide":

            # Porta de correr (deslizamento horizontal)

            axis = piece.ext.get("slide_axis", QVector3D(1.0, 0.0, 0.0))

            dist = float(piece.ext.get("slide_distance", 0.70))

            delta = axis * (dist * frac)

            m_slide = QMatrix4x4()

            m_slide.translate(delta)



            siblings = [piece] + cls._collect_linked_children(module_group, piece)



            for p in siblings:

                if getattr(p, "ext", None) is None:

                    p.ext = {}

                p_slide_scale = float(p.ext.get("slide_scale", 1.0))
                p_delta = delta * p_slide_scale

                ov = p.ext.get("orig_vertices")

                if not isinstance(ov, list) or len(ov) != len(p.mesh.vertices) or not all(isinstance(pt, QVector3D) for pt in ov):

                    p.ext["orig_vertices"] = [QVector3D(v.position) for v in p.mesh.vertices]



                _backup_orig_uvws(p)

                _restore_orig_uvws(p)



                for v, orig in zip(p.mesh.vertices, p.ext["orig_vertices"]):

                    v.position = orig + p_delta

                if abs(p_slide_scale - 1.0) < 1e-6:
                    _remap_uvws(p.mesh, m_slide)
                else:
                    m_p_slide = QMatrix4x4()
                    m_p_slide.translate(p_delta)
                    _remap_uvws(p.mesh, m_p_slide)



                p.ext["is_open"] = (frac > 0.05)

                p.ext["open_fraction"] = frac

                if hasattr(p, "mesh") and p.mesh is not None:

                    p.mesh._mut_serial = getattr(p.mesh, "_mut_serial", 0) + 1



        elif itype in ("door_canto_l", "door_canto_l_y", "door_canto_l_x"):

            from core.history import rotation_matrix

            ov = piece.ext.get("orig_vertices")

            if not isinstance(ov, list) or len(ov) != len(piece.mesh.vertices) or not all(isinstance(pt, QVector3D) for pt in ov):

                piece.ext["orig_vertices"] = [QVector3D(v.position) for v in piece.mesh.vertices]



            hp = piece.ext.get("hinge_pivot")

            if not isinstance(hp, QVector3D):

                xs = [pt.x() for pt in piece.ext["orig_vertices"]]

                ys = [pt.y() for pt in piece.ext["orig_vertices"]]

                if itype == "door_canto_l_x":

                    px, py = max(xs), max(ys)

                    ang = 90.0

                else:

                    px, py = min(xs), min(ys)

                    ang = -90.0

                piece.ext["hinge_pivot"] = QVector3D(px, py, 0.0)

                piece.ext["door_angle"] = ang



            total_ang = piece.ext.get("door_angle", 90.0 if itype == "door_canto_l_x" else -90.0)

            ang = total_ang * frac

            m_door = rotation_matrix(piece.ext["hinge_pivot"], QVector3D(0.0, 0.0, 1.0), ang)

            siblings = [piece] + cls._collect_linked_children(module_group, piece)

            for p in siblings:

                if getattr(p, "ext", None) is None:

                    p.ext = {}

                p_ov = p.ext.get("orig_vertices")

                if not isinstance(p_ov, list) or len(p_ov) != len(p.mesh.vertices) or not all(isinstance(pt, QVector3D) for pt in p_ov):

                    p.ext["orig_vertices"] = [QVector3D(v.position) for v in p.mesh.vertices]

                _backup_orig_uvws(p)

                _restore_orig_uvws(p)

                for v, orig in zip(p.mesh.vertices, p.ext["orig_vertices"]):

                    v.position = m_door.map(orig)

                _remap_uvws(p.mesh, m_door)

                p.ext["is_open"] = (frac > 0.05)

                p.ext["open_fraction"] = frac

                if hasattr(p, "mesh") and p.mesh is not None:

                    p.mesh._mut_serial = getattr(p.mesh, "_mut_serial", 0) + 1



        else:

            # Portas de giro laterais

            from core.history import rotation_matrix



            # Coleta peças vinculadas à folha (maçanetas, puxadores, frisos)

            siblings = [piece] + cls._collect_linked_children(module_group, piece)



            hp = piece.ext.get("hinge_pivot")

            if not isinstance(hp, QVector3D):

                ov_test = piece.ext.get("orig_vertices")

                if not isinstance(ov_test, list) or len(ov_test) != len(piece.mesh.vertices):

                    ov_test = [QVector3D(v.position) for v in piece.mesh.vertices]

                pts = ov_test

                rad = math.radians(rot_z)

                u_x, u_y = math.cos(rad), math.sin(rad)

                f_x, f_y = math.sin(rad), -math.cos(rad)



                proj_u = [pt.x() * u_x + pt.y() * u_y for pt in pts]

                proj_f = [pt.x() * f_x + pt.y() * f_y for pt in pts]



                meta_side = getattr(piece, "ext", {}).get("trazomob", {}).get("door_side")

                is_right = (itype == "door_right" or meta_side == "right")



                target_u = max(proj_u) if is_right else min(proj_u)

                target_f = max(proj_f)



                best_pt = min(pts, key=lambda pt: (

                    ((pt.x() * u_x + pt.y() * u_y) - target_u) ** 2 +

                    ((pt.x() * f_x + pt.y() * f_y) - target_f) ** 2

                ))



                ang = 95.0 if is_right else -95.0

                piece.ext["hinge_pivot"] = QVector3D(best_pt.x(), best_pt.y(), 0.0)

                piece.ext["door_angle"] = ang



            total_ang = piece.ext.get("door_angle", 95.0 if itype == "door_right" else -95.0)

            ang = total_ang * frac

            m_door = rotation_matrix(piece.ext["hinge_pivot"], QVector3D(0.0, 0.0, 1.0), ang)



            for p in siblings:

                if getattr(p, "ext", None) is None:

                    p.ext = {}

                ov = p.ext.get("orig_vertices")

                if not isinstance(ov, list) or len(ov) != len(p.mesh.vertices) or not all(isinstance(pt, QVector3D) for pt in ov):

                    p.ext["orig_vertices"] = [QVector3D(v.position) for v in p.mesh.vertices]



                _backup_orig_uvws(p)

                _restore_orig_uvws(p)



                for v, orig in zip(p.mesh.vertices, p.ext["orig_vertices"]):

                    v.position = m_door.map(orig)

                _remap_uvws(p.mesh, m_door)



                p.ext["is_open"] = (frac > 0.05)

                p.ext["open_fraction"] = frac

                if hasattr(p, "mesh") and p.mesh is not None:

                    p.mesh._mut_serial = getattr(p.mesh, "_mut_serial", 0) + 1



        return True



    @classmethod

    def toggle_piece(cls, piece: Group, module_group: Group | None = None, scene=None, viewport=None) -> bool:

        """Alterna o estado de abertura (aberto <-> fechado) da peça clicada."""

        if piece is None or not hasattr(piece, "ext"):

            return False

        curr_open = bool(getattr(piece, "ext", None) and piece.ext.get("is_open"))

        target_frac = 0.0 if curr_open else 1.0

        ok = cls.set_piece_open_fraction(piece, target_frac, module_group, scene, viewport)

        if ok:

            cls._notify_scene(scene, viewport)

        return ok



    @classmethod

    def set_module_open_fraction(cls, module_group: Group, fraction: float, scene=None, viewport=None) -> bool:

        """Define o percentual de abertura de todas as portas e gavetas do módulo especificado."""

        if not module_group or not hasattr(module_group, "children"):

            return False



        interactive_children = [

            c for c in module_group.children if cls.is_interactive_piece(getattr(c, "name", ""))

        ]

        if not interactive_children:

            return False



        handled_drawers = set()

        for child in interactive_children:

            itype = cls.get_piece_interaction_type(child.name)

            if itype == "drawer":

                did = cls.get_drawer_id(child.name)

                if did in handled_drawers:

                    continue

                handled_drawers.add(did)

            cls.set_piece_open_fraction(child, fraction, module_group, scene, None)



        cls._notify_scene(scene, viewport)

        return True



    @classmethod

    def set_scene_open_fraction(cls, scene, fraction: float, viewport=None) -> list[dict[str, Any]]:

        """Abertura Dinâmica Global: abre todas as portas e gavetas de todos os armários da cena 3D."""

        if scene is None:

            return []



        for g in getattr(scene, "groups", []):

            if hasattr(g, "ext") and isinstance(g.ext, dict) and "trazomob_module" in g.ext:

                cls.set_module_open_fraction(g, fraction, scene, None)



        cls._notify_scene(scene, viewport)



        from ..interaction.collision import check_opening_collisions

        return check_opening_collisions(scene)

    @classmethod
    def capture_open_state(cls, module_group: Group) -> dict[str, Any]:
        """Captura o estado de abertura de portas e gavetas de um módulo para restauração."""
        state: dict[str, Any] = {
            "pieces": {},      # {piece_name: open_fraction}
            "by_type": {},     # {itype: open_fraction}
            "has_open": False,
            "max_frac": 0.0,
        }
        if not module_group or not hasattr(module_group, "children"):
            return state

        for child in module_group.children:
            c_name = getattr(child, "name", "")
            if not cls.is_interactive_piece(c_name):
                continue
            ext = getattr(child, "ext", None) or {}
            frac = float(ext.get("open_fraction", 0.0))
            is_open = bool(ext.get("is_open", False))
            if is_open and frac <= 0.0:
                frac = 1.0
            if frac > 0.0:
                state["has_open"] = True
                if frac > state["max_frac"]:
                    state["max_frac"] = frac
            state["pieces"][c_name] = frac
            itype = cls.get_piece_interaction_type(c_name)
            if itype:
                state["by_type"][itype] = frac

        return state

    @classmethod
    def restore_open_state(
        cls,
        module_group: Group,
        state: dict[str, Any],
        scene=None,
        viewport=None,
    ) -> bool:
        """Restaura o estado de abertura de portas e gavetas em um módulo recém-construído."""
        if not module_group or not hasattr(module_group, "children") or not state:
            return False

        pieces_state = state.get("pieces", {})
        by_type_state = state.get("by_type", {})
        max_frac = float(state.get("max_frac", 0.0))
        if not state.get("has_open") and max_frac <= 0.0:
            return False

        restored_any = False
        interactive_children = [
            c for c in module_group.children if cls.is_interactive_piece(getattr(c, "name", ""))
        ]

        handled_drawers = set()
        for child in interactive_children:
            c_name = getattr(child, "name", "")
            itype = cls.get_piece_interaction_type(c_name)

            if itype == "drawer":
                did = cls.get_drawer_id(c_name)
                if did in handled_drawers:
                    continue
                handled_drawers.add(did)

            target_frac = pieces_state.get(c_name)
            if target_frac is None and itype:
                target_frac = by_type_state.get(itype)
            if target_frac is None and max_frac > 0.0:
                target_frac = max_frac

            if target_frac is not None and target_frac > 0.0:
                ok = cls.set_piece_open_fraction(child, target_frac, module_group, scene, None)
                if ok:
                    restored_any = True

        if restored_any:
            cls._notify_scene(scene, viewport)

        return restored_any



    @staticmethod

    def _notify_scene(scene, viewport) -> None:

        if scene is not None:

            scene.version += 1

        if viewport is not None:

            if hasattr(viewport, "_group_chunks"):

                viewport._group_chunks.clear()

            if hasattr(viewport, "_inst_chunks"):

                viewport._inst_chunks.clear()

            if hasattr(viewport, "_placement_proxies"):

                viewport._placement_proxies.clear()

            viewport._placements_memo = None

            viewport._pick_block = None

            viewport._pick_memo = None

            viewport._face_any_memo = None

            if hasattr(viewport, "_dirty"):

                viewport._dirty = True

            if hasattr(viewport, "notify_scene_changed"):

                viewport.notify_scene_changed()

            elif hasattr(viewport, "update"):

                viewport.update()



    @classmethod

    def toggle_all(cls, module_group: Group, scene=None, viewport=None) -> bool:

        """Abre ou fecha todas as portas e gavetas do módulo especificado."""

        if not module_group or not hasattr(module_group, "children"):

            return False



        interactive_children = [

            c for c in module_group.children if cls.is_interactive_piece(getattr(c, "name", ""))

        ]

        if not interactive_children:

            return False



        # Se alguma porta ou gaveta estiver aberta, a intenção de clicar no móvel/toggle_all é FECHAR tudo.

        # Caso tudo esteja fechado, abre tudo.

        any_open = any(bool(getattr(c, "ext", None) and c.ext.get("is_open")) for c in interactive_children)

        target_open = not any_open



        handled_drawers = set()

        for child in interactive_children:

            itype = cls.get_piece_interaction_type(child.name)

            curr_state = bool(getattr(child, "ext", None) and child.ext.get("is_open"))



            if itype == "drawer":

                did = cls.get_drawer_id(child.name)

                if did in handled_drawers:

                    continue

                handled_drawers.add(did)

                if curr_state != target_open:

                    cls.toggle_piece(child, module_group, scene, None)

            else:

                if curr_state != target_open:

                    cls.toggle_piece(child, module_group, scene, None)



        if scene is not None:

            scene.version += 1

        if viewport is not None:

            if hasattr(viewport, "_group_chunks"):

                viewport._group_chunks.clear()

            if hasattr(viewport, "_inst_chunks"):

                viewport._inst_chunks.clear()

            if hasattr(viewport, "_placement_proxies"):

                viewport._placement_proxies.clear()

            viewport._placements_memo = None

            viewport._pick_block = None

            viewport._pick_memo = None

            viewport._face_any_memo = None

            if hasattr(viewport, "_dirty"):

                viewport._dirty = True

            if hasattr(viewport, "notify_scene_changed"):

                viewport.notify_scene_changed()

            elif hasattr(viewport, "update"):

                viewport.update()



        return True





class CabinetInteractTool(Tool):

    """Ferramenta de clique interativo para abrir e fechar portas e gavetas no 3D."""

    name = "Interagir Módulo"

    shortcut = "I"

    description = "Clique nas portas ou gavetas para abrir e fechar no 3D."

    uses_snap = False



    def on_activate(self, viewport) -> None:
        from ..domain.engine_state import is_engine_enabled
        if not is_engine_enabled():
            return
        if hasattr(viewport, "setCursor"):

            viewport.setCursor(Qt.PointingHandCursor)



    def on_deactivate(self, viewport) -> None:

        if hasattr(viewport, "unsetCursor"):

            viewport.unsetCursor()



    def on_hover(self, ctx: ToolContext) -> None:

        face, piece = ctx.viewport.pick_face_placement(ctx.screen.x(), ctx.screen.y())

        if piece is not None and CabinetInteract.is_interactive_piece(getattr(piece, "name", "")):

            ctx.viewport.setCursor(Qt.PointingHandCursor)

            return

        group = ctx.viewport.pick_group(ctx.screen.x(), ctx.screen.y())

        if group is not None and hasattr(group, "ext") and isinstance(group.ext, dict):

            if "trazomob_module" in group.ext:

                ctx.viewport.setCursor(Qt.PointingHandCursor)

                return

        ctx.viewport.setCursor(Qt.ArrowCursor)



    def on_click(self, ctx: ToolContext) -> None:

        face, piece = ctx.viewport.pick_face_placement(ctx.screen.x(), ctx.screen.y())

        group = ctx.viewport.pick_group(ctx.screen.x(), ctx.screen.y())



        # Encontra o móvel dono da peça clicada

        module_owner = None

        if piece is not None:

            module_owner = getattr(piece, "owner", None)

            if module_owner is None and hasattr(ctx.viewport, "scene"):

                for g in getattr(ctx.viewport.scene, "groups", []):

                    if hasattr(g, "children"):

                        if piece in g.children or any(getattr(c, "mesh", None) is getattr(piece, "mesh", None) for c in g.children):

                            module_owner = g

                            break

        if module_owner is None:

            module_owner = group



        # Se clicou em uma representação 3D de ferragem, redireciona para a peça correspondente
        if piece is not None and module_owner is not None and hasattr(module_owner, "children"):
            p_ext = getattr(piece, "ext", None)
            p_tm = p_ext.get("trazomob", {}) if isinstance(p_ext, dict) else {}
            p_hardware = bool(p_tm.get("kind") == "hardware") if isinstance(p_tm, dict) else False
            target = p_tm.get("linked_piece") if isinstance(p_tm, dict) else None
            if p_hardware and target:
                for child in module_owner.children:
                    if getattr(child, "name", None) == target:
                        piece = child
                        break

        # Se clicou diretamente em uma peça acessória vinculada (puxador, maçaneta, braçadeira),
        # redireciona o clique para a folha de porta ou frente correspondente:
        if piece is not None and module_owner is not None and hasattr(module_owner, "children"):
            p_name = getattr(piece, "name", "")
            for child in module_owner.children:
                if child is not piece and hasattr(child, "ext") and isinstance(child.ext, dict):
                    linked = child.ext.get("linked_pieces", [])
                    if any(k in p_name for k in linked):
                        piece = child
                        break

        # Se clicou em uma porta ou gaveta interativa específica:

        if piece is not None and CabinetInteract.is_interactive_piece(getattr(piece, "name", "")):

            real_piece = piece

            if module_owner is not None and hasattr(module_owner, "children"):

                for child in module_owner.children:

                    if child is piece or getattr(child, "mesh", None) is getattr(piece, "mesh", None):

                        real_piece = child

                        break

                p_name = getattr(real_piece, 'name', '')

                for child in module_owner.children:

                    if child is not real_piece and hasattr(child, 'ext') and isinstance(child.ext, dict):

                        linked = child.ext.get('linked_pieces', [])

                        if any(k in p_name for k in linked):

                            real_piece = child

                            break

            CabinetInteract.toggle_piece(real_piece, module_owner, ctx.viewport.scene, ctx.viewport)

            return



        # Se clicou no corpo/carcaça do armário (lateral, rodapé, topo, travessa, etc.):

        if module_owner is not None and hasattr(module_owner, "ext"):

            is_mod = "trazomob_module" in module_owner.ext

            if is_mod:

                CabinetInteract.toggle_all(module_owner, ctx.viewport.scene, ctx.viewport)

        elif piece is not None and module_owner is not None:

            CabinetInteract.toggle_all(module_owner, ctx.viewport.scene, ctx.viewport)







