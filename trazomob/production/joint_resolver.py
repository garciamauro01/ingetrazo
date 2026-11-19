# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Gerenciador automático de contato e alinhador de juntas/furações (JointResolver).

Analisa as peças de um módulo de marcenaria, detecta encontros face-a-face
(AABB e proximidade geométrica) e sincroniza as operações de usinagem
(cavilhas, minifix, parafusos, calços de dobradiça e suportes de prateleira)
garantindo que:
1. Peças que se tocam recebam furações correspondentes perfeitamente alinhadas.
2. Faces livres (sem contato) não recebam furos desnecessários.
3. Não haja duplicação de furações já calculadas.
"""
from __future__ import annotations

import math
from typing import Any
from PySide6.QtGui import QVector3D
from core.group import Group
from .machining import (
    MachiningOp,
    make_shelf_side_holes,
    make_shelf_joint_holes,
    make_hinge_plate_holes,
    make_cabinet_joint_holes,
    make_horizontal_board_edge_holes,
    make_stretcher_joint_holes,
)


def get_piece_bounds(piece: Group) -> tuple[QVector3D, QVector3D] | None:
    """Retorna (min_point, max_point) dos vértices da peça no espaço local."""
    mesh = getattr(piece, "mesh", None)
    if mesh is None or not getattr(mesh, "vertices", None):
        return None
    min_x = min_y = min_z = float("inf")
    max_x = max_y = max_z = float("-inf")
    for v in mesh.vertices:
        p = getattr(v, "position", v)
        x, y, z = p.x(), p.y(), p.z()
        if x < min_x: min_x = x
        if x > max_x: max_x = x
        if y < min_y: min_y = y
        if y > max_y: max_y = y
        if z < min_z: min_z = z
        if z > max_z: max_z = z
    if min_x == float("inf"):
        return None
    return QVector3D(min_x, min_y, min_z), QVector3D(max_x, max_y, max_z)


def get_piece_operations(piece: Group) -> list[dict[str, Any]]:
    """Obtém ou inicializa a lista de operações de usinagem nos metadados da peça."""
    ext = getattr(piece, "ext", None)
    if ext is None:
        piece.ext = {}
        ext = piece.ext
    tm = ext.setdefault("trazomob", {})
    return tm.setdefault("operacoes", [])


class JointResolver:
    """Gerenciador e sincronizador automático de contatos e juntas de marcenaria."""

    @classmethod
    def resolve_module_joints(
        cls,
        pieces: list[Group],
        dispositivo_fixacao: str = "minifix_cavilha",
        dispositivo_prateleira: str = "cavilha",
        gerar_furacao: bool = True,
        tol_mm: float = 3.0,
        espessura_chapa_mm: float = 15.0,
        afastamento_fixacao_frontal_mm: float = 50.0,
        afastamento_fixacao_traseiro_mm: float = 50.0,
        afastamento_cavilha_frontal_mm: float = 100.0,
        afastamento_cavilha_traseiro_mm: float = 100.0,
    ) -> None:
        """Examina todas as peças de um módulo e sincroniza furações entre peças em contato."""
        if not pieces:
            return

        if not gerar_furacao:
            # Se a furação estiver desativada pelo usuário, limpa quaisquer operações das peças
            for p in pieces:
                ext = getattr(p, "ext", None)
                if ext and "trazomob" in ext and "operacoes" in ext["trazomob"]:
                    ext["trazomob"]["operacoes"] = []
            return

        tol = tol_mm / 1000.0

        laterais: list[tuple[Group, QVector3D, QVector3D]] = []
        divisorias: list[tuple[Group, QVector3D, QVector3D]] = []
        prateleiras: list[tuple[Group, QVector3D, QVector3D]] = []
        portas: list[tuple[Group, QVector3D, QVector3D]] = []
        horizontais_estruturais: list[tuple[Group, QVector3D, QVector3D]] = []
        travessas: list[tuple[Group, QVector3D, QVector3D]] = []

        for p in pieces:
            b = get_piece_bounds(p)
            if not b:
                continue
            name = (getattr(p, "name", "") or "").lower()
            p_min, p_max = b

            if "fundo" in name:
                continue
            elif "porta" in name or "folha" in name or "frente" in name:
                portas.append((p, p_min, p_max))
            elif "travessa" in name and "gaveta" not in name:
                travessas.append((p, p_min, p_max))
            elif "lateral" in name and "gaveta" not in name:
                laterais.append((p, p_min, p_max))
            elif "divisoria" in name or "divisória" in name:
                if (p_max.x() - p_min.x()) < (p_max.z() - p_min.z()):
                    divisorias.append((p, p_min, p_max))
                else:
                    horizontais_estruturais.append((p, p_min, p_max))
            elif "prateleira" in name or "sapateira" in name:
                prateleiras.append((p, p_min, p_max))
            elif "ferragem" in name or "tamponamento" in name:
                continue
            elif "base" in name or "tampo" in name or "topo" in name or "maleiro" in name:
                if (p_max.z() - p_min.z()) <= (p_max.x() - p_min.x()) + 0.05:
                    horizontais_estruturais.append((p, p_min, p_max))

        suportes_verticais = laterais + divisorias
        cls._resolve_prateleiras_contato(
            prateleiras, suportes_verticais, tol,
            afastamento_mm=afastamento_fixacao_frontal_mm,
            dispositivo_prateleira=dispositivo_prateleira,
        )
        cls._resolve_portas_dobradicas(portas, suportes_verticais, tol)
        cls._resolve_caixaria_contato(
            horizontais_estruturais, suportes_verticais, tol, dispositivo_fixacao,
            espessura_chapa_mm=espessura_chapa_mm,
            afastamento_fixacao_frontal_mm=afastamento_fixacao_frontal_mm,
            afastamento_fixacao_traseiro_mm=afastamento_fixacao_traseiro_mm,
            afastamento_cavilha_frontal_mm=afastamento_cavilha_frontal_mm,
            afastamento_cavilha_traseiro_mm=afastamento_cavilha_traseiro_mm,
        )
        cls._resolve_travessas_contato(travessas, suportes_verticais, tol, dispositivo_fixacao)

        # Atualiza a malha 3D de peças cujas operações foram adicionadas ou enriquecidas
        # pelo JointResolver (evita dupla perfuração checando _rendered_ops_count).
        cls.apply_pending_machining_to_meshes(pieces)

    @classmethod
    def apply_pending_machining_to_meshes(cls, pieces: list[Group]) -> None:
        """Renderiza furações adicionadas pelo JointResolver nas malhas 3D das peças.

        Verifica se a peça já teve furações renderizadas anteriormente na malha
        (_rendered_ops_count) para nunca duplicar add_hole/cilindros 3D na geometria.
        """
        from ..builders.mesh_utils import _render_machining_holes_in_mesh

        for p in pieces:
            mesh = getattr(p, "mesh", None)
            if mesh is None:
                continue

            ext = getattr(p, "ext", None)
            if not ext or "trazomob" not in ext:
                continue

            tm = ext["trazomob"]
            operacoes = tm.get("operacoes", [])
            rendered_count = int(tm.get("_rendered_ops_count", 0))

            if len(operacoes) <= rendered_count:
                continue

            novas_ops = operacoes[rendered_count:]
            b = get_piece_bounds(p)
            if not b:
                continue

            p_min, p_max = b
            origin = (p_min.x(), p_min.y(), p_min.z())
            size = (p_max.x() - p_min.x(), p_max.y() - p_min.y(), p_max.z() - p_min.z())

            _render_machining_holes_in_mesh(mesh, origin, size, novas_ops, piece_name=getattr(p, "name", ""))
            tm["_rendered_ops_count"] = len(operacoes)

    @classmethod
    def _resolve_travessas_contato(
        cls,
        travessas: list[tuple[Group, QVector3D, QVector3D]],
        suportes: list[tuple[Group, QVector3D, QVector3D]],
        tol: float,
        dispositivo_fixacao: str,
    ) -> None:
        """Sincroniza furações entre travessas estruturais (topo frontal/traseiro) e os suportes verticais."""
        usar_minifix = "minifix" in str(dispositivo_fixacao).lower()
        for trav, t_min, t_max in travessas:
            larg_x_mm = (t_max.x() - t_min.x()) * 1000.0
            dim_y_mm = (t_max.y() - t_min.y()) * 1000.0
            dim_z_mm = (t_max.z() - t_min.z()) * 1000.0
            z_centro_trav = (t_min.z() + t_max.z()) / 2.0
            t_ops = get_piece_operations(trav)

            # Detecta se é travessa deitada (largura em Y, espessura em Z) ou em pé (espessura em Y, largura em Z)
            eh_deitada = dim_y_mm > dim_z_mm
            largura_util_mm = dim_y_mm if eh_deitada else dim_z_mm
            esp_util_mm = dim_z_mm if eh_deitada else dim_y_mm
            face_tambor = "base" if eh_deitada else "traseira"

            for sup, s_min, s_max in suportes:
                sobrepos_y = min(t_max.y(), s_max.y()) - max(t_min.y(), s_min.y())
                if sobrepos_y <= 0.0:
                    continue

                if not (s_min.z() - tol <= z_centro_trav <= s_max.z() + tol):
                    continue

                toca_esq = abs(t_min.x() - s_max.x()) <= tol
                toca_dir = abs(t_max.x() - s_min.x()) <= tol

                if not (toca_esq or toca_dir):
                    continue

                face_sup = "direita" if toca_esq else "esquerda"
                sup_name = (getattr(sup, "name", "") or "").lower()
                face_lat_furo = "traseira" if ("lateral" in sup_name and ("esq" in sup_name or "dir" in sup_name)) else face_sup
                sup_ops = get_piece_operations(sup)

                # Posição Y da travessa em relação à borda frontal do suporte (0.0 = frente do móvel)
                pos_lat_y_mm = (t_min.y() - s_min.y()) * 1000.0
                pos_lat_z_mm = (z_centro_trav - s_min.z()) * 1000.0

                # 1. Checa se o suporte já tem furos para esta travessa
                ja_tem_no_sup = any(
                    op.get("tipo") == "furo"
                    and op.get("face") in (face_lat_furo, "traseira")
                    and ("travessa" in str(op.get("descricao", "")).lower())
                    and abs(float(op.get("x", 0.0)) - (pos_lat_y_mm + 25.0)) < 15.0
                    and abs(float(op.get("y", 0.0)) - pos_lat_z_mm) < 15.0
                    for op in sup_ops
                )

                if not ja_tem_no_sup:
                    furos_sup = make_stretcher_joint_holes(
                        largura_travessa_mm=largura_util_mm,
                        esp_travessa_mm=esp_util_mm,
                        face=face_lat_furo,
                        usar_minifix=usar_minifix,
                        eh_travessa=False,
                        dispositivo_fixacao=dispositivo_fixacao,
                        posicao_lateral_y_mm=pos_lat_y_mm,
                        posicao_lateral_z_mm=pos_lat_z_mm,
                    )
                    sup_ops.extend([o.to_dict() for o in furos_sup])

                # 2. Checa se a própria travessa já tem furações nos topos
                face_topo_trav = "esquerda" if toca_esq else "direita"
                ja_tem_na_trav = any(
                    op.get("tipo") == "furo"
                    and op.get("face") == face_topo_trav
                    for op in t_ops
                )

                if not ja_tem_na_trav:
                    furos_trav = make_stretcher_joint_holes(
                        largura_travessa_mm=largura_util_mm,
                        esp_travessa_mm=esp_util_mm,
                        face=face_tambor,
                        usar_minifix=usar_minifix,
                        comprimento_travessa_mm=larg_x_mm,
                        eh_travessa=True,
                        dispositivo_fixacao=dispositivo_fixacao,
                    )
                    # Filtra apenas os furos correspondentes ao topo que encostou
                    furos_topo_correto = [
                        o for o in furos_trav
                        if (o.face == face_topo_trav)
                        or (o.face == face_tambor and (("esq" in o.descricao.lower() and toca_esq) or ("dir" in o.descricao.lower() and toca_dir)))
                    ]
                    t_ops.extend([o.to_dict() for o in furos_topo_correto])

    @classmethod
    def _resolve_caixaria_contato(
        cls,
        horizontais: list[tuple[Group, QVector3D, QVector3D]],
        suportes: list[tuple[Group, QVector3D, QVector3D]],
        tol: float,
        dispositivo_fixacao: str,
        espessura_chapa_mm: float = 15.0,
        afastamento_fixacao_frontal_mm: float = 50.0,
        afastamento_fixacao_traseiro_mm: float = 50.0,
        afastamento_cavilha_frontal_mm: float = 100.0,
        afastamento_cavilha_traseiro_mm: float = 100.0,
    ) -> None:
        """Resolve contatos estruturais entre bases/tampos/divisórias horizontais e as laterais/divisórias."""
        usar_minifix = "minifix" in str(dispositivo_fixacao).lower()
        for horiz, h_min, h_max in horizontais:
            prof_horiz_mm = (h_max.y() - h_min.y()) * 1000.0
            esp_horiz_mm = (h_max.z() - h_min.z()) * 1000.0
            larg_horiz_mm = (h_max.x() - h_min.x()) * 1000.0
            z_centro_horiz = (h_min.z() + h_max.z()) / 2.0
            h_name = (getattr(horiz, "name", "") or "").lower()
            h_ops = get_piece_operations(horiz)

            # Para cada suporte vertical (lateral esq, lateral dir, divisória vertical)
            for sup, s_min, s_max in suportes:
                sobrepos_y = min(h_max.y(), s_max.y()) - max(h_min.y(), s_min.y())
                if sobrepos_y < 0.050:
                    continue

                if not (s_min.z() - tol <= z_centro_horiz <= s_max.z() + tol):
                    continue

                toca_esq = abs(h_min.x() - s_max.x()) <= tol
                toca_dir = abs(h_max.x() - s_min.x()) <= tol

                if not (toca_esq or toca_dir):
                    continue

                face_sup = "direita" if toca_esq else "esquerda"
                sup_name = (getattr(sup, "name", "") or "").lower()
                z_rel_sup_mm = (z_centro_horiz - s_min.z()) * 1000.0

                # Face de furação da lateral: se for lateral canônica, furação na face traseira (2D face interna)
                face_lat_furo = "traseira" if ("lateral" in sup_name and ("esq" in sup_name or "dir" in sup_name)) else face_sup
                sup_ops = get_piece_operations(sup)

                # 1. Checa se o suporte já tem furos de junta nessa altura
                ja_tem_no_sup = any(
                    op.get("tipo") == "furo"
                    and op.get("face") in (face_lat_furo, "traseira")
                    and ("minifix" in str(op.get("descricao", "")).lower() or "cavilha de jun" in str(op.get("descricao", "")).lower())
                    and abs(float(op.get("y", 0.0)) - z_rel_sup_mm) < 6.0
                    for op in sup_ops
                )

                if not ja_tem_no_sup:
                    furos_sup = make_cabinet_joint_holes(
                        comprimento_junta_mm=prof_horiz_mm,
                        posicao_borda_mm=z_rel_sup_mm,
                        face=face_lat_furo,
                        usar_minifix=usar_minifix,
                        dispositivo_fixacao=dispositivo_fixacao,
                        espessura_chapa_mm=espessura_chapa_mm,
                        afastamento_frontal_mm=afastamento_fixacao_frontal_mm,
                        afastamento_traseiro_mm=afastamento_fixacao_traseiro_mm,
                        afastamento_cavilha_frontal_mm=afastamento_cavilha_frontal_mm,
                        afastamento_cavilha_traseiro_mm=afastamento_cavilha_traseiro_mm,
                    )
                    sup_ops.extend([o.to_dict() for o in furos_sup])

                # 2. Checa se a peça horizontal já tem furos no topo correspondente
                face_topo_horiz = "esquerda" if toca_esq else "direita"
                ja_tem_no_horiz = any(
                    op.get("tipo") == "furo"
                    and op.get("face") == face_topo_horiz
                    and ("cavilha topo" in str(op.get("descricao", "")).lower() or "haste minifix" in str(op.get("descricao", "")).lower() or "guia parafuso" in str(op.get("descricao", "")).lower())
                    for op in h_ops
                )

                if not ja_tem_no_horiz:
                    face_tambor = "base" if ("tampo" in h_name or "sup" in h_name) else "base"
                    ops_esq, ops_dir, ops_face = make_horizontal_board_edge_holes(
                        prof_chapa_mm=prof_horiz_mm,
                        largura_chapa_mm=larg_horiz_mm,
                        esp_chapa_mm=esp_horiz_mm,
                        afastamento_fixacao_frontal_mm=afastamento_fixacao_frontal_mm,
                        afastamento_fixacao_traseiro_mm=afastamento_fixacao_traseiro_mm,
                        afastamento_cavilha_frontal_mm=afastamento_cavilha_frontal_mm,
                        afastamento_cavilha_traseiro_mm=afastamento_cavilha_traseiro_mm,
                        usar_minifix=usar_minifix,
                        dispositivo_fixacao=dispositivo_fixacao,
                        face_tambor=face_tambor,
                    )
                    ops_topo = ops_esq if toca_esq else ops_dir
                    h_ops.extend([o.to_dict() for o in ops_topo])

                    # Se for minifix, adicionar tambores correspondentes ao lado de contato
                    if usar_minifix:
                        if toca_esq:
                            tambores_lado = [o for o in ops_face if "esq" in o.descricao.lower()]
                        else:
                            tambores_lado = [o for o in ops_face if "dir" in o.descricao.lower()]
                        for tb in tambores_lado:
                            if not any(abs(float(e.get("x", 0.0)) - tb.x) < 2.0 and abs(float(e.get("y", 0.0)) - tb.y) < 2.0 for e in h_ops if "tambor" in str(e.get("descricao", "")).lower()):
                                h_ops.append(tb.to_dict())

    @classmethod
    def _resolve_prateleiras_contato(
        cls,
        prateleiras: list[tuple[Group, QVector3D, QVector3D]],
        suportes: list[tuple[Group, QVector3D, QVector3D]],
        tol: float,
        afastamento_mm: float = 50.0,
        dispositivo_prateleira: str = "cavilha",
    ) -> None:
        eh_vb = any(k in str(dispositivo_prateleira).lower() for k in ("vb35", "vb36", "vb_35", "vb_36", "vb"))
        for prat, p_min, p_max in prateleiras:
            prof_prat_mm = (p_max.y() - p_min.y()) * 1000.0
            esp_prat_mm = (p_max.z() - p_min.z()) * 1000.0
            larg_prat_mm = (p_max.x() - p_min.x()) * 1000.0
            z_centro_prat = (p_min.z() + p_max.z()) / 2.0
            prat_ops = get_piece_operations(prat)

            for sup, s_min, s_max in suportes:
                sobrepos_y = min(p_max.y(), s_max.y()) - max(p_min.y(), s_min.y())
                if sobrepos_y < 0.050:
                    continue

                if not (s_min.z() - tol <= z_centro_prat <= s_max.z() + tol):
                    continue

                toca_esq = abs(p_min.x() - s_max.x()) <= tol
                toca_dir = abs(p_max.x() - s_min.x()) <= tol

                if toca_esq or toca_dir:
                    face_sup = "direita" if toca_esq else "esquerda"
                    sup_name = (getattr(sup, "name", "") or "").lower()
                    # Laterais canônicas usam a face interna "traseira" no 2D.
                    face_lat_furo = (
                        "traseira"
                        if "lateral" in sup_name and ("esq" in sup_name or "dir" in sup_name)
                        else face_sup
                    )
                    z_rel_sup_mm = (z_centro_prat - s_min.z()) * 1000.0
                    recuo_front_mm = max(0.0, (p_min.y() - s_min.y()) * 1000.0)

                    # 1. Furação na face interna do suporte vertical (lateral / divisória)
                    sup_ops = get_piece_operations(sup)
                    if eh_vb:
                        # Se for VB, substitui furações legadas de cavilha na mesma altura por furos de pino VB (Ø5mm)
                        furos_cavilha_antigos = [
                            op for op in sup_ops
                            if op.get("tipo") == "furo"
                            and op.get("face") == face_lat_furo
                            and "cavilha prateleira" in str(op.get("descricao", "")).lower()
                            and abs(float(op.get("y", 0.0)) - z_rel_sup_mm) < 8.0
                        ]
                        for c_ant in furos_cavilha_antigos:
                            sup_ops.remove(c_ant)

                    ja_existe_sup = any(
                        op.get("tipo") == "furo"
                        and op.get("face") == face_lat_furo
                        and ("prateleira" in str(op.get("descricao", "")).lower() or "vb" in str(op.get("descricao", "")).lower())
                        and abs(float(op.get("y", 0.0)) - z_rel_sup_mm) < 8.0
                        for op in sup_ops
                    )
                    if not ja_existe_sup:
                        novos_furos = make_shelf_side_holes(
                            pos_z_na_lateral_mm=(p_min.z() - s_min.z()) * 1000.0,
                            prof_prateleira_mm=prof_prat_mm,
                            recuo_frontal_mm=recuo_front_mm,
                            afastamento_mm=afastamento_mm,
                            esp_prateleira_mm=esp_prat_mm,
                            face=face_lat_furo,
                            dispositivo_prateleira=dispositivo_prateleira,
                        )
                        sup_ops.extend([o.to_dict() for o in novos_furos])

                    # 2. Furação na própria prateleira (Tambor VB35/36 na face inferior OU Cavilhas nos topos)
                    if eh_vb:
                        # Remove cavilhas legadas de topo na prateleira para evitar conflito com VB
                        lado_topo = "esquerda" if toca_esq else "direita"
                        cavilhas_topo_antigas = [
                            op for op in prat_ops
                            if op.get("tipo") == "furo"
                            and op.get("face") == lado_topo
                            and "cavilha" in str(op.get("descricao", "")).lower()
                        ]
                        for c_ant in cavilhas_topo_antigas:
                            prat_ops.remove(c_ant)

                        lado_str = "esq" if toca_esq else "dir"
                        ja_tem_vb = any(
                            op.get("tipo") == "furo"
                            and op.get("face") == "base"
                            and "vb" in str(op.get("descricao", "")).lower()
                            and lado_str in str(op.get("descricao", "")).lower()
                            for op in prat_ops
                        )
                        if not ja_tem_vb:
                            ops_esq, ops_dir = make_shelf_joint_holes(
                                prof_prateleira_mm=prof_prat_mm,
                                afastamento_mm=afastamento_mm,
                                esp_prateleira_mm=esp_prat_mm,
                                dispositivo_prateleira=dispositivo_prateleira,
                                largura_prateleira_mm=larg_prat_mm,
                            )
                            # Adiciona os tambores correspondentes ao lado de contato
                            ops_lado = ops_esq if toca_esq else ops_dir
                            prat_ops.extend([o.to_dict() for o in ops_lado])
                    else:
                        face_topo = "esquerda" if toca_esq else "direita"
                        ja_tem_topo = any(
                            op.get("tipo") == "furo"
                            and op.get("face") == face_topo
                            and "cavilha" in str(op.get("descricao", "")).lower()
                            for op in prat_ops
                        )
                        if not ja_tem_topo:
                            ops_esq, ops_dir = make_shelf_joint_holes(
                                prof_prateleira_mm=prof_prat_mm,
                                afastamento_mm=afastamento_mm,
                                esp_prateleira_mm=esp_prat_mm,
                                dispositivo_prateleira=dispositivo_prateleira,
                            )
                            ops_topo = ops_esq if toca_esq else ops_dir
                            prat_ops.extend([o.to_dict() for o in ops_topo])

    @classmethod
    def _resolve_portas_dobradicas(
        cls,
        portas: list[tuple[Group, QVector3D, QVector3D]],
        suportes: list[tuple[Group, QVector3D, QVector3D]],
        tol: float,
    ) -> None:
        for porta, p_min, p_max in portas:
            p_ops = get_piece_operations(porta)
            canecos = [
                op for op in p_ops
                if op.get("tipo") == "furo" and "caneco" in str(op.get("descricao", "")).lower()
            ]
            if not canecos:
                continue

            door_side = getattr(porta, "ext", {}).get("trazomob", {}).get("door_side")
            p_name = (getattr(porta, "name", "") or "").lower()
            e_direita = (door_side == "right") or ("dir" in p_name and "esq" not in p_name)

            # Canto da dobradiça na porta (em X)
            x_dobradica = p_max.x() if e_direita else p_min.x()

            melhor_sup = None
            menor_dist = float("inf")

            for sup, s_min, s_max in suportes:
                if s_max.z() < p_min.z() or s_min.z() > p_max.z():
                    continue

                dist_para_face_dir = abs(x_dobradica - s_max.x())
                dist_para_face_esq = abs(x_dobradica - s_min.x())
                min_d = min(dist_para_face_dir, dist_para_face_esq)

                if min_d < menor_dist:
                    menor_dist = min_d
                    melhor_sup = sup

            if melhor_sup is not None and menor_dist <= 0.050:
                b_sup = get_piece_bounds(melhor_sup)
                if not b_sup:
                    continue
                s_min, s_max = b_sup
                sup_name = (getattr(melhor_sup, "name", "") or "").lower()
                sup_ops = get_piece_operations(melhor_sup)

                calcos_y_sup = []
                for c in canecos:
                    caneco_y = float(c.get("y", 0.0))
                    z_global = p_min.z() + (caneco_y / 1000.0)
                    z_rel_sup_mm = (z_global - s_min.z()) * 1000.0
                    calcos_y_sup.append(z_rel_sup_mm)

                # Nas laterais canônicas, a furação interna usa face="traseira"
                if "esq" in sup_name:
                    faces_para_calco = ["traseira"]
                elif "dir" in sup_name:
                    faces_para_calco = ["traseira"]
                else:
                    dist_dir = abs(x_dobradica - s_max.x())
                    dist_esq = abs(x_dobradica - s_min.x())
                    faces_para_calco = ["direita"] if dist_dir <= dist_esq else ["esquerda"]

                calcos_faltantes = []
                for cy in calcos_y_sup:
                    ja_tem = any(
                        op.get("tipo") == "furo"
                        and op.get("face") in faces_para_calco
                        and ("cal" in str(op.get("descricao", "")).lower())
                        and (
                            abs(float(op.get("y", 0.0)) - cy) < 6.0
                            or abs(float(op.get("y", 0.0)) - (cy - 16.0)) < 4.0
                            or abs(float(op.get("y", 0.0)) - (cy + 16.0)) < 4.0
                        )
                        for op in sup_ops
                    )
                    if not ja_tem:
                        calcos_faltantes.append(cy)

                if calcos_faltantes:
                    for f_cal in faces_para_calco:
                        novos_calcos = make_hinge_plate_holes(
                            posicoes_y_mm=calcos_faltantes,
                            recuo_borda_frontal_mm=37.0,
                            face=f_cal,
                            tipo_fixacao="parafuso",
                        )
                        sup_ops.extend([o.to_dict() for o in novos_calcos])
