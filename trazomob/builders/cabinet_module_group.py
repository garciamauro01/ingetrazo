# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Orquestracao de montagem do CabinetBuilder."""
from __future__ import annotations

import logging
from typing import Any

from PySide6.QtGui import QVector3D

from core.group import Group
from core.mesh import Mesh

logger = logging.getLogger("trazomob.cabinet_module_group")


class ModuleGroupMixin:
    """Montagem completa do grupo mestre de um modulo."""

    @classmethod
    def build_module_group(cls, params: dict[str, Any], offset: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> Group:
        tipo = params.get("tipo", "balcao")
        L_mm = params["largura"]
        A_mm = params["altura"]
        P_mm = params["profundidade"]
        esp_mm = float(params.get("espessura", params.get("esp_mm", params.get("espessura_caixa", 15.0))))
        rodape_mm = float(params.get("rodape", 100.0))
        material = params.get("material", "MDF Branco TX 15mm")
        material_frentes = params.get("material_frentes", material)
        esp_frentes_mm = float(params.get("espessura_frentes", params.get("esp_frentes_mm", esp_mm)))

        # Configurações de Fundo TrazoMob
        tipo_fundo = params.get("tipo_fundo")
        if not tipo_fundo:
            tipo_fundo = "rasgo" if params.get("tem_fundo", True) else "sem_fundo"
        esp_fundo_mm = float(params.get("esp_fundo", 6.0))
        recuo_fundo_mm = float(params.get("recuo_fundo", 10.0))
        prof_rasgo_mm = float(params.get("prof_rasgo", 5.0))
        folga_fundo_mm = float(params.get("folga_fundo", 2.0))

        puxador_tipo = params.get("puxador_tipo", "alca")
        puxador_cor = params.get("puxador_cor", "preto")
        puxador_pos = params.get("puxador_pos", "padrao")
        perfil_modelo = str(params.get("perfil_modelo", "gola")).lower()
        if "desconto_perfil" in params:
            desconto_perfil_mm = float(params["desconto_perfil"])
        else:
            from ..profiles.library import get_profile
            desconto_perfil_mm = float(get_profile(perfil_modelo).get("desconto_mm", 35.0))
        pux_kw = {
            "puxador_tipo": puxador_tipo,
            "puxador_cor": puxador_cor,
            "puxador_pos": puxador_pos,
            "desconto_perfil_mm": desconto_perfil_mm,
            "perfil_modelo": perfil_modelo,
        }

        save_params = dict(params)
        pieces = []
        module_name = ""

        fundo_kwargs = {
            "tipo_fundo": tipo_fundo,
            "esp_fundo_mm": esp_fundo_mm,
            "recuo_fundo_mm": recuo_fundo_mm,
            "prof_rasgo_mm": prof_rasgo_mm,
            "folga_fundo_mm": folga_fundo_mm,
        }

        mat_trav_p = params.get("material_travessas")
        esp_trav_p = params.get("esp_travessas_mm", params.get("espessura_travessas"))
        esp_trav_val = float(esp_trav_p) if (esp_trav_p is not None and float(esp_trav_p) > 0) else None

        mat_fita_cx_p = params.get("material_fita_caixa")
        mat_fita_tr_p = params.get("material_fita_travessas")

        gaveta_kwargs = {
            "tipo_fundo_gaveta": str(params.get("tipo_fundo_gaveta", "rasgo")),
            "folga_corredica_mm": float(params.get("folga_corredica_mm", 26.0)),
            "material_gaveta": params.get("material_gaveta"),
            "esp_gaveta_mm": float(params.get("esp_gaveta_mm", 15.0)),
            "material_fita_gaveta": params.get("material_fita_gaveta"),
            "material_fundo_gaveta": params.get("material_fundo_gaveta"),
            "esp_fundo_gaveta_mm": float(params.get("esp_fundo_gaveta_mm", 6.0)),
        }

        travessas_kwargs = {
            "larg_travessa_frontal_mm": float(params.get("larg_travessa_frontal_mm", params.get("larg_travessa_mm", 70.0))),
            "larg_travessa_traseira_mm": float(params.get("larg_travessa_traseira_mm", 70.0)),
            "travessa_frontal_em_pe": bool(params.get("travessa_frontal_em_pe", (tipo == "balcao_pia"))),
            "travessa_traseira_em_pe": bool(params.get("travessa_traseira_em_pe", False)),
            "recuo_porta_topo_mm": float(params.get("recuo_porta_topo_mm", params.get("recuo_porta_pia_mm", 50.0))),
            "material_travessas": mat_trav_p,
            "esp_travessas_mm": esp_trav_val,
            "fita_travessas_modo": str(params.get("fita_travessas_modo", "frontal_1L")),
            "fita_travessas_faces": params.get("fita_travessas_faces"),
            "fita_caixa_modo": str(params.get("fita_caixa_modo", "frontal_1L")),
            "material_fita_caixa": mat_fita_cx_p,
            "material_fita_travessas": mat_fita_tr_p,
            "gerar_furacao": bool(params.get("gerar_furacao", True)),
            "dispositivo_fixacao": str(params.get("dispositivo_fixacao", "minifix_cavilha")),
        }

        from ..builders.registry import get_module_builder
        from ..builders.chapa_spec import ModuloMaterialContext
        builder_fn = get_module_builder(tipo)
        if builder_fn is not None:
            mat_ctx = ModuloMaterialContext.from_dict(params)
            ctx = {
                "L_mm": L_mm,
                "A_mm": A_mm,
                "P_mm": P_mm,
                "esp_mm": esp_mm,
                "rodape_mm": rodape_mm,
                "tipo_fundo": tipo_fundo,
                "material": material,
                "material_frentes": material_frentes,
                "esp_frentes_mm": esp_frentes_mm,
                "offset": offset,
                "fundo_kwargs": fundo_kwargs,
                "pux_kw": pux_kw,
                "travessas_kwargs": travessas_kwargs,
                "gaveta_kwargs": gaveta_kwargs,
                "afastamento_fixacao_frontal_mm": float(params.get("afastamento_fixacao_frontal_mm", 50.0)),
                "afastamento_fixacao_traseiro_mm": float(params.get("afastamento_fixacao_traseiro_mm", 50.0)),
                "afastamento_cavilha_frontal_mm": float(params.get("afastamento_cavilha_frontal_mm", 100.0)),
                "afastamento_cavilha_traseiro_mm": float(params.get("afastamento_cavilha_traseiro_mm", 100.0)),
                "mat_fita_cx_p": mat_fita_cx_p,
                "mat_ctx": mat_ctx,
            }
            pieces, module_name = builder_fn(cls, params, ctx)
            from ..production.joint_resolver import JointResolver
            JointResolver.resolve_module_joints(
                pieces=pieces,
                dispositivo_fixacao=str(params.get("dispositivo_fixacao", "minifix_cavilha")),
                dispositivo_prateleira=str(params.get("dispositivo_prateleira", params.get("fixacao_prateleira", "cavilha"))),
                gerar_furacao=bool(params.get("gerar_furacao", True)),
                espessura_chapa_mm=esp_mm,
                afastamento_fixacao_frontal_mm=ctx["afastamento_fixacao_frontal_mm"],
                afastamento_fixacao_traseiro_mm=ctx["afastamento_fixacao_traseiro_mm"],
                afastamento_cavilha_frontal_mm=ctx["afastamento_cavilha_frontal_mm"],
                afastamento_cavilha_traseiro_mm=ctx["afastamento_cavilha_traseiro_mm"],
            )
        elif any(str(tipo).startswith(prefix) for prefix in ("porta_", "janela_")):
            r_z = float(params.get("rot_z", params.get("rotacao", 0.0)) or 0.0)
            peit = float(params.get("peitoril_mm", params.get("peitoril", 0.0)) or 0.0)
            lado_ab = str(params.get("lado_abertura", "direita"))
            sent_ab = str(params.get("sentido_abertura", "interno"))
            return cls.load_esquadria_igz(
                item_id=str(tipo),
                largura_mm=L_mm,
                altura_mm=A_mm,
                esp_parede_mm=P_mm,
                peitoril_mm=peit,
                offset=offset,
                rot_z=r_z,
                lado_abertura=lado_ab,
                sentido_abertura=sent_ab,
            )
        elif "janela_maximar" in str(tipo):
            r_z = float(params.get("rot_z", params.get("rotacao", 0.0)) or 0.0)
            peit = float(params.get("peitoril_mm", 1600.0))
            return cls.build_janela_maximar(
                largura_mm=L_mm,
                altura_mm=A_mm,
                esp_parede_mm=P_mm,
                peitoril_mm=peit,
                offset=offset,
                rot_z=r_z,
            )

        # Módulo Mestre (Container)
        master = Group(Mesh(), name=module_name)
        from PySide6.QtGui import QMatrix4x4
        master.xform = QMatrix4x4()
        if "bancada" in str(tipo):
            mod_layer = "Bancadas"
        else:
            mod_layer = "PLANEJADOS"

        master.layer = mod_layer
        for p in pieces:
            p.layer = mod_layer

        lado_ab_porta = str(params.get("lado_abertura_porta", "")).strip().lower()
        if lado_ab_porta.startswith(("dir", "right")):
            from ..builders.mesh_utils import create_board_group
            new_pieces = []
            for p in pieces:
                p_meta = getattr(p, "ext", {}).get("trazomob", {}) if getattr(p, "ext", None) else {}
                if p_meta.get("door_side") == "single" and p.mesh and p.mesh.vertices:
                    xs = [v.position.x() for v in p.mesh.vertices]
                    ys = [v.position.y() for v in p.mesh.vertices]
                    zs = [v.position.z() for v in p.mesh.vertices]
                    ox_p, oy_p, oz_p = min(xs), min(ys), min(zs)
                    largura_porta_mm = p_meta.get("largura", (max(xs) - ox_p) * 1000.0)
                    sx_p = float(largura_porta_mm) / 1000.0
                    sy_p = p_meta.get("espessura", 15.0) / 1000.0
                    sz_p = p_meta.get("comprimento", (max(zs) - oz_p) * 1000.0) / 1000.0
                    p_name_dir = p.name if "dir" in p.name.lower() else f"{p.name} (Dir)"
                    # A porta foi construída como esquerda: ao invertê-la para a
                    # direita, as usinagens (canecos) também precisam ser refletidas
                    # no eixo X, senão as dobradiças ficam no lado oposto ao puxador.
                    ops_espelhadas = []
                    for op in p_meta.get("operacoes", []):
                        copia = dict(op)
                        if copia.get("x") is not None:
                            try:
                                copia["x"] = round(
                                    float(largura_porta_mm) - float(copia["x"]), 3)
                            except (TypeError, ValueError):
                                pass
                        ops_espelhadas.append(copia)
                    p_rebuilt = create_board_group(
                        p_name_dir,
                        (ox_p, max(ys) - sy_p, oz_p),
                        (sx_p, sy_p, sz_p),
                        p_meta.get("material", material_frentes or material),
                        fita_c1=p_meta.get("fita_c1", True),
                        fita_c2=p_meta.get("fita_c2", True),
                        fita_l1=p_meta.get("fita_l1", True),
                        fita_l2=p_meta.get("fita_l2", True),
                        color=cls.get_material_color(p_meta.get("material", material_frentes or material)),
                        puxador_tipo=puxador_tipo,
                        puxador_cor=puxador_cor,
                        puxador_pos=puxador_pos,
                        desconto_perfil_mm=desconto_perfil_mm,
                        perfil_modelo=perfil_modelo,
                        door_side="right",
                        is_upper=("aereo" in str(tipo).lower()),
                        operacoes=ops_espelhadas,
                    )
                    p_rebuilt.layer = mod_layer
                    new_pieces.append(p_rebuilt)
                else:
                    new_pieces.append(p)
            pieces = new_pieces

        if getattr(master, "children", None) is not None:
            for p in pieces:
                p.owner = master
            master.children.extend(pieces)

        if getattr(master, "ext", None) is None:
            master.ext = {}

        # Guarda parâmetros dinâmicos para reedição posterior
        save_params["offset"] = offset
        save_params["material_frentes"] = material_frentes
        save_params["espessura_frentes"] = esp_frentes_mm
        save_params["tipo_fundo"] = tipo_fundo
        save_params["esp_fundo"] = esp_fundo_mm
        save_params["recuo_fundo"] = recuo_fundo_mm
        save_params["prof_rasgo"] = prof_rasgo_mm
        save_params["folga_fundo"] = folga_fundo_mm
        save_params["puxador_tipo"] = puxador_tipo
        save_params["puxador_cor"] = puxador_cor
        save_params["puxador_pos"] = puxador_pos
        save_params["desconto_perfil"] = desconto_perfil_mm
        save_params["perfil_modelo"] = perfil_modelo
        from ..domain.schema import set_module_data
        set_module_data(master, save_params)

        # ── Ferragens do módulo (dobradiças, corrediças, trilhos, etc.) ──────
        # Gravado em ext para sobreviver a reaberturas/edições e ser lido por
        # cutlist, orçamento e relatórios sem depender de heurística por nome.
        # Aceita lista explícita vinda do diálogo (edição do usuário); caso
        # contrário, infere automaticamente a partir dos parâmetros.
        try:
            from ..domain.hardware import (
                deserialize_hardware,
                infer_module_hardware,
                serialize_hardware,
            )
            _hw_explicit = save_params.get("hardware")
            if isinstance(_hw_explicit, list) and _hw_explicit:
                _hw = deserialize_hardware(_hw_explicit)
            else:
                _hw = infer_module_hardware(save_params)
            if _hw:
                master.ext["trazomob_hardware"] = serialize_hardware(_hw)
                # Representação 3D esquemática (excluída do cutlist)
                if bool(save_params.get("hardware_3d_visible", True)):
                    try:
                        from ..builders.hardware_geometry import (
                            build_module_hardware_3d,
                        )
                        build_module_hardware_3d(master, _hw, list(master.children), save_params)
                    except Exception:
                        logger.debug("Falha ao construir ferragens 3D do módulo", exc_info=True)
        except Exception:
            # Ferragens nunca devem impedir a construção do módulo.
            logger.debug("Falha ao consolidar ferragens do módulo", exc_info=True)

        # Registra a relação exata do centro não-rotacionado com o offset para reconstruções perfeitas
        from ..domain.module_geometry import get_module_carcass_bounds
        cb_unrot = get_module_carcass_bounds(master)
        if tipo == "peca_prateleiras_avulsas":
            # Para prateleiras avulsas, o vão delimitado total informado pelo usuário (L_mm x P_mm x A_mm)
            # deve ser preservado como bounding box de referência do vão
            L_u = float(L_mm) / 1000.0
            P_u = float(P_mm) / 1000.0
            A_u = float(A_mm) / 1000.0
            cx_u = offset[0] + L_u * 0.5
            cy_u = offset[1] + P_u * 0.5
            cz_u = offset[2] + A_u * 0.5
            save_params["_unrot_carcass_span"] = (
                float(cx_u - offset[0]),
                float(cy_u - offset[1]),
                float(cz_u - offset[2]),
                float(L_u),
                float(P_u),
                float(A_u),
            )
        elif cb_unrot is not None:
            cx_u = (cb_unrot[0] + cb_unrot[1]) * 0.5
            cy_u = (cb_unrot[2] + cb_unrot[3]) * 0.5
            cz_u = (cb_unrot[4] + cb_unrot[5]) * 0.5
            save_params["_unrot_carcass_span"] = (
                float(cx_u - offset[0]),
                float(cy_u - offset[1]),
                float(cz_u - offset[2]),
                float(cb_unrot[1] - cb_unrot[0]),
                float(cb_unrot[3] - cb_unrot[2]),
                float(cb_unrot[5] - cb_unrot[4]),
            )

        # Espelhamento paramétrico: reflete a geometria já construída no eixo
        # local X, antes da rotação. O parâmetro ``mirror_x`` fica gravado no
        # ``ext`` (via save_params) para que toda reconstrução volte espelhada
        # — portas, puxadores, fita de borda e usinagens acompanham.
        if bool(params.get("mirror_x", False)):
            from ..builders.mirror import mirror_module_geometry
            if cb_unrot is not None:
                plano_x = (cb_unrot[0] + cb_unrot[1]) * 0.5
            else:
                plano_x = float(offset[0]) + (float(L_mm) / 2000.0)
            mirror_module_geometry(master, plano_x)

        # Se houver rotação 3D livre (rot_matrix_3d) ou rotação em Z solicitada nos parâmetros
        rot_z = float(params.get("rot_z", params.get("rotacao", 0.0)) or 0.0) % 360.0
        save_params["rot_z"] = rot_z

        # Faces horizontais do snap (superior/inferior) tombam a peça 90° em
        # torno do eixo X local, para que o topo/base fique plano contra a
        # parede. A inclinação é derivada de ``snap_parede`` a cada
        # reconstrução e acompanha a troca de face no diálogo.
        from ..domain.snap_contract import snap_face_tilt_deg
        tilt_x = snap_face_tilt_deg(params.get("snap_parede"))

        rot_mat_3d = params.get("rot_matrix_3d")
        if isinstance(rot_mat_3d, (list, tuple)) and len(rot_mat_3d) == 16:
            save_params["rot_matrix_3d"] = [float(x) for x in rot_mat_3d]
            if cb_unrot is not None:
                c_vec = QVector3D(
                    (cb_unrot[0] + cb_unrot[1]) * 0.5,
                    (cb_unrot[2] + cb_unrot[3]) * 0.5,
                    (cb_unrot[4] + cb_unrot[5]) * 0.5,
                )
            else:
                c_vec = QVector3D(float(offset[0]), float(offset[1]), float(offset[2]))
            m_pure = QMatrix4x4(*save_params["rot_matrix_3d"])
            t_out = QMatrix4x4()
            t_out.translate(c_vec)
            t_in = QMatrix4x4()
            t_in.translate(-c_vec)
            m_full = t_out * m_pure * t_in
            targets = getattr(master, "children", []) or [master]
            for t in targets:
                mesh = getattr(t, "mesh", None)
                if mesh and hasattr(mesh, "vertices"):
                    for v in mesh.vertices:
                        v.position = m_full.map(v.position)
                    mesh._mut_serial = getattr(mesh, "_mut_serial", 0) + 1
                if getattr(t, "ext", None) is not None:
                    if "orig_vertices" in t.ext:
                        t.ext["orig_vertices"] = [m_full.map(orig) for orig in t.ext["orig_vertices"]]
                    if "slide_delta" in t.ext and isinstance(t.ext["slide_delta"], QVector3D):
                        t.ext["slide_delta"] = m_full.mapVector(t.ext["slide_delta"])
                    if "slide_axis" in t.ext and isinstance(t.ext["slide_axis"], QVector3D):
                        t.ext["slide_axis"] = m_full.mapVector(t.ext["slide_axis"]).normalized()
                    if "flap_axis" in t.ext and isinstance(t.ext["flap_axis"], QVector3D):
                        t.ext["flap_axis"] = m_full.mapVector(t.ext["flap_axis"]).normalized()
                    if "hinge_pivot" in t.ext and isinstance(t.ext["hinge_pivot"], QVector3D):
                        t.ext["hinge_pivot"] = m_full.map(t.ext["hinge_pivot"])
        else:
            if abs(tilt_x) > 1e-4:
                cls.rotate_module(
                    master, tilt_x, center=None, axis=(1.0, 0.0, 0.0), update_param=False
                )
            if abs(rot_z) > 1e-4:
                cls.rotate_module(master, rot_z, center=None, update_param=False)

        # ``set_module_data`` publica uma cópia dos parâmetros; tudo o que é
        # calculado DEPOIS dele (span não-rotacionado, rot_z, rot_matrix_3d)
        # ficaria só em ``save_params`` e nunca chegaria ao documento.
        # ``update_module_data`` altera o dicionário já publicado no lugar.
        from ..domain.schema import update_module_data
        update_module_data(master, save_params)

        return master
