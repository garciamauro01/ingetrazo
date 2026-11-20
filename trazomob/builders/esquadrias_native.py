# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Carregamento dos modelos reais (.igz) e sua cinemática."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Tuple

from PySide6.QtGui import QVector3D, QMatrix4x4
from core.group import Group
from core.mesh import Mesh

from .esquadrias_common import (
    ESQUADRIA_FILES,
    NOVAS_PORTAS_CINEMATICA,
    NOVAS_PORTAS_FOLHAS,
    PORTA_PROTO_CACHE,
    resolve_igz_path,
)


def get_porta_prototype(igz_path):
    """Carrega e armazena em cache os grupos protótipos já consolidados (xform baked) de uma porta .igz."""
    key = str(igz_path)
    cached = PORTA_PROTO_CACHE.get(key)
    if cached is not None:
        return cached

    from collections import defaultdict
    from core.scene import Scene
    from core.group import transformed_mesh
    from formats import igz

    temp_scene = Scene()
    igz.load_into(temp_scene, igz_path)

    def bake_xforms(group: Group, parent_matrix: QMatrix4x4 | None = None) -> None:
        if parent_matrix is None:
            current = QMatrix4x4(group.xform) if group.xform else QMatrix4x4()
        else:
            current = parent_matrix * (group.xform if group.xform else QMatrix4x4())
        group.xform = None
        if group.mesh and len(group.mesh.vertices) > 0:
            if not current.isIdentity():
                group.mesh = transformed_mesh(group.mesh, current)
        for c in getattr(group, "children", []):
            bake_xforms(c, current)

    for g in temp_scene.groups:
        bake_xforms(g)

    loaded_groups = list(temp_scene.groups)
    if "porta_pivotante_vidro" in igz_path.name and len(loaded_groups) == 1 and loaded_groups[0].mesh:
        orig_mesh = loaded_groups[0].mesh
        # 1. Folha de vidro: prisma sólido estanque com as dimensões reais do vão
        vidro_attrs = {
            "color": [0.9647058823529412, 0.9686274509803922, 0.9176470588235294],
            "material": "vidro_incolor",
        }
        mesh_vidro = Mesh()
        p0 = QVector3D(0.005, 0.04125, 0.01505)
        p1 = QVector3D(0.795, 0.05325, 2.08785)
        v000 = QVector3D(p0.x(), p0.y(), p0.z())
        v100 = QVector3D(p1.x(), p0.y(), p0.z())
        v110 = QVector3D(p1.x(), p1.y(), p0.z())
        v010 = QVector3D(p0.x(), p1.y(), p0.z())
        v001 = QVector3D(p0.x(), p0.y(), p1.z())
        v101 = QVector3D(p1.x(), p0.y(), p1.z())
        v111 = QVector3D(p1.x(), p1.y(), p1.z())
        v011 = QVector3D(p0.x(), p1.y(), p1.z())
        for gf in [
            [v000, v010, v110, v100],  # base
            [v001, v101, v111, v011],  # topo
            [v000, v100, v101, v001],  # frente
            [v110, v010, v011, v111],  # costas
            [v010, v000, v001, v011],  # esquerda
            [v100, v110, v111, v101],  # direita
        ]:
            nf = mesh_vidro.add_face(gf)
            nf.attrs = dict(vidro_attrs)

        # 2. Puxador: faces frontais/traseiras e tampões de apoio estanques
        mesh_puxador = Mesh()
        # 3. Braçadeiras/clamps articuláveis (giram com a porta)
        mesh_ferragens_moveis = Mesh()
        # 4. Bases dos pivôs fixas (chão e teto)
        mesh_pivots_fixos = Mesh()

        for i, f in enumerate(orig_mesh.faces):
            pts = [QVector3D(v) for v in f.vertices]
            attrs = dict(f.attrs) if hasattr(f, "attrs") else {}
            color = tuple(attrs.get("color")) if attrs.get("color") else None
            if color == (0.9647058823529412, 0.9686274509803922, 0.9176470588235294):
                continue
            elif color == (0.0, 0.0, 0.0) and min(p.x() for p in pts) > 0.5:
                nf = mesh_puxador.add_face(pts)
                nf.attrs = attrs
            elif i not in (0, 51) and i not in range(108, 120):
                zs = [round(p.z(), 4) for p in pts]
                if max(zs) <= 0.009 or min(zs) >= 2.091:
                    nf = mesh_pivots_fixos.add_face(pts)
                    nf.attrs = attrs
                else:
                    nf = mesh_ferragens_moveis.add_face(pts)
                    nf.attrs = attrs

        # Repara e fecha o puxador e as ferragens para solidez manifold estanque
        import plugins.solid_inspector as si
        from core.orient import orient_outward
        si.repair_mesh(mesh_puxador)

        for loop in si._border_loops(mesh_ferragens_moveis):
            si._cap(mesh_ferragens_moveis, loop)
        orient_outward(mesh_ferragens_moveis)
        orient_outward(mesh_pivots_fixos)

        grp_marco = Group(mesh=mesh_pivots_fixos, name="Pivôs Fixos Marco")
        grp_ferr_mov = Group(mesh=mesh_ferragens_moveis, name="Braçadeiras Ferragens Vidro")
        grp_folha = Group(mesh=mesh_vidro, name="Folha Vidro Pivotante")
        grp_pux = Group(mesh=mesh_puxador, name="Puxador Porta Pivotante")
        loaded_groups = [grp_marco, grp_ferr_mov, grp_folha, grp_pux]

    elif "porta_aluminio" in igz_path.name:
        # Separa o marco das ferragens da fechadura posterior que estavam fundidas em Agrupar#98
        g98 = next((g for g in loaded_groups if g.name == "Agrupar#98"), None)
        if g98 and g98.mesh and len(g98.mesh.faces) > 0:
            m_98 = g98.mesh

            def _pt_k(p):
                return (round(p.x(), 5), round(p.y(), 5), round(p.z(), 5))

            p2f: dict[tuple[float, float, float], list[int]] = {}
            for fi, f in enumerate(m_98.faces):
                for v in f.vertices:
                    p2f.setdefault(_pt_k(v), []).append(fi)
            f_adj = [set() for _ in range(len(m_98.faces))]
            for flist in p2f.values():
                for f1 in flist:
                    for f2 in flist:
                        if f1 != f2:
                            f_adj[f1].add(f2)
            vis = [False] * len(m_98.faces)
            comps: list[list[int]] = []
            for i in range(len(m_98.faces)):
                if not vis[i]:
                    comp = []
                    q = [i]
                    vis[i] = True
                    while q:
                        curr = q.pop()
                        comp.append(curr)
                        for nb in f_adj[curr]:
                            if not vis[nb]:
                                vis[nb] = True
                                q.append(nb)
                    comps.append(comp)

            fech_f_indices: list[int] = []
            marco_f_indices: list[int] = []
            for comp in comps:
                comp_pts = [v for fi in comp for v in m_98.faces[fi].vertices]
                xs = [p.x() for p in comp_pts]
                if min(xs) > 0.80 or len(comp) == 97:
                    marco_f_indices.extend(comp)
                else:
                    fech_f_indices.extend(comp)

            mesh_fech_post = Mesh()
            for fi in fech_f_indices:
                f = m_98.faces[fi]
                nf = mesh_fech_post.add_face([v for v in f.vertices])
                if f.attrs:
                    nf.attrs = dict(f.attrs)
                for h in f.holes:
                    mesh_fech_post.add_hole(nf, [v for v in h])

            mesh_marco_limpo = Mesh()
            for fi in marco_f_indices:
                f = m_98.faces[fi]
                nf = mesh_marco_limpo.add_face([v for v in f.vertices])
                if f.attrs:
                    nf.attrs = dict(f.attrs)
                for h in f.holes:
                    mesh_marco_limpo.add_hole(nf, [v for v in h])

            g98.mesh = mesh_marco_limpo
            g98.name = "Marco da Porta"
            grp_fech_post = Group(mesh=mesh_fech_post, name="Fechadura Posterior")

            new_loaded = []
            for g in loaded_groups:
                new_loaded.append(g)
                if g is g98:
                    new_loaded.append(grp_fech_post)
            loaded_groups = new_loaded

    elif "porta_correr" in igz_path.name:
        # Separa as duas folhas de correr (esquerda frontal e direita traseira)
        g_folha = next((g for g in loaded_groups if "Porta de correr" in g.name), None)
        if g_folha and g_folha.mesh and len(g_folha.mesh.faces) > 0:
            m_f = g_folha.mesh

            def _pt_kc(p):
                return (round(p.x(), 5), round(p.y(), 5), round(p.z(), 5))

            p2fc: dict[tuple[float, float, float], list[int]] = {}
            for fi, f in enumerate(m_f.faces):
                for v in f.vertices:
                    p2fc.setdefault(_pt_kc(v), []).append(fi)
            fc_adj = [set() for _ in range(len(m_f.faces))]
            for flist in p2fc.values():
                for f1 in flist:
                    for f2 in flist:
                        if f1 != f2:
                            fc_adj[f1].add(f2)
            vis_c = [False] * len(m_f.faces)
            comps_c: list[list[int]] = []
            for i in range(len(m_f.faces)):
                if not vis_c[i]:
                    comp = []
                    q = [i]
                    vis_c[i] = True
                    while q:
                        curr = q.pop()
                        comp.append(curr)
                        for nb in fc_adj[curr]:
                            if not vis_c[nb]:
                                vis_c[nb] = True
                                q.append(nb)
                    comps_c.append(comp)

            esq_f_indices: list[int] = []
            dir_f_indices: list[int] = []
            for comp in comps_c:
                comp_pts = [v for fi in comp for v in m_f.faces[fi].vertices]
                xs = [p.x() for p in comp_pts]
                if min(xs) < 0.80:
                    esq_f_indices.extend(comp)
                else:
                    dir_f_indices.extend(comp)

            mesh_esq = Mesh()
            for fi in esq_f_indices:
                f = m_f.faces[fi]
                nf = mesh_esq.add_face([v for v in f.vertices])
                if f.attrs:
                    nf.attrs = dict(f.attrs)
                for h in f.holes:
                    mesh_esq.add_hole(nf, [v for v in h])

            mesh_dir = Mesh()
            for fi in dir_f_indices:
                f = m_f.faces[fi]
                nf = mesh_dir.add_face([v for v in f.vertices])
                if f.attrs:
                    nf.attrs = dict(f.attrs)
                for h in f.holes:
                    mesh_dir.add_hole(nf, [v for v in h])

            g_folha.mesh = mesh_esq
            g_folha.name = "Folha de Correr Esquerda"
            grp_folha_dir = Group(mesh=mesh_dir, name="Folha de Correr Direita")

            new_loaded = []
            for g in loaded_groups:
                new_loaded.append(g)
                if g is g_folha:
                    new_loaded.append(grp_folha_dir)
            loaded_groups = new_loaded

    elif "janela_correr_2f" in igz_path.name:
        # Mesma estratégia da 4f: separa as faces originais por componentes conectados,
        # preservando os attrs de material/opacidade do vidro (reconstruir do zero
        # fazia o vidro perder "mat"/"opacity" e ficar opaco na cena).
        if loaded_groups and loaded_groups[0].mesh:
            m = loaded_groups[0].mesh
            def _pt_k(p): return (round(p.x(), 4), round(p.y(), 4), round(p.z(), 4))
            p2f = defaultdict(list)
            for fi, f in enumerate(m.faces):
                for pt in f.vertices: p2f[_pt_k(pt)].append(fi)
            f_adj = [set() for _ in range(len(m.faces))]
            for flist in p2f.values():
                for f1 in flist:
                    for f2 in flist:
                        if f1 != f2: f_adj[f1].add(f2)
            vis = [False] * len(m.faces)
            comps = []
            for i in range(len(m.faces)):
                if not vis[i]:
                    comp = []; q = [i]; vis[i] = True
                    while q:
                        curr = q.pop(); comp.append(curr)
                        for nb in f_adj[curr]:
                            if not vis[nb]: vis[nb] = True; q.append(nb)
                    comps.append(comp)

            def build_submesh(indices):
                nm = Mesh()
                for fi in indices:
                    f = m.faces[fi]
                    nf = nm.add_face([pt for pt in f.vertices])
                    if f.attrs: nf.attrs = dict(f.attrs)
                    for h in f.holes: nm.add_hole(nf, [pt for pt in h])
                return nm

            # comp 0: marco (137 faces)
            # folha esq: comp 2 (com vidro) + comps 1 e 3 (fecho e puxador esquerdos)
            # folha dir: comp 4 (com vidro) + comps 5 e 6 (fecho e puxador direitos)
            f_marco = list(comps[0])
            f_esq = list(comps[2]) + list(comps[1]) + list(comps[3])
            f_dir = list(comps[4]) + list(comps[5]) + list(comps[6])

            g_marco = Group(mesh=build_submesh(f_marco), name="Marco da Janela")
            g_esq = Group(mesh=build_submesh(f_esq), name="Folha de Correr Esquerda")
            g_dir = Group(mesh=build_submesh(f_dir), name="Folha de Correr Direita")
            loaded_groups = [g_marco, g_esq, g_dir]

    elif "janela_correr_4f" in igz_path.name:
        if loaded_groups and loaded_groups[0].mesh:
            m = loaded_groups[0].mesh
            def _pt_k(p): return (round(p.x(), 4), round(p.y(), 4), round(p.z(), 4))
            p2f = defaultdict(list)
            for fi, f in enumerate(m.faces):
                for pt in f.vertices: p2f[_pt_k(pt)].append(fi)
            f_adj = [set() for _ in range(len(m.faces))]
            for flist in p2f.values():
                for f1 in flist:
                    for f2 in flist:
                        if f1 != f2: f_adj[f1].add(f2)
            vis = [False] * len(m.faces)
            comps = []
            for i in range(len(m.faces)):
                if not vis[i]:
                    comp = []; q = [i]; vis[i] = True
                    while q:
                        curr = q.pop(); comp.append(curr)
                        for nb in f_adj[curr]:
                            if not vis[nb]: vis[nb] = True; q.append(nb)
                    comps.append(comp)

            def build_submesh(indices):
                nm = Mesh()
                for fi in indices:
                    f = m.faces[fi]
                    nf = nm.add_face([pt for pt in f.vertices])
                    if f.attrs: nf.attrs = dict(f.attrs)
                    for h in f.holes: nm.add_hole(nf, [pt for pt in h])
                return nm

            # comp 7: marco (137 faces)
            # fixa esq: comps 0, 2, e faces de comp 1 em X <= 0.510 (37 faces)
            # movel centro esq: comps 3, 4, 5, e faces de comp 1 em X > 0.480 e Y > 0.040 (81 faces)
            # movel centro dir: comps 6, 8, 9 (76 faces)
            # fixa dir: comps 10, 11 (29 faces)
            c1_esq = [13, 30, 17, 28, 18, 16]
            c1_centro = [40, 51, 49, 48, 56, 46, 39]
            f_fixa_esq = list(comps[0]) + list(comps[2]) + c1_esq
            f_movel_esq = list(comps[3]) + list(comps[4]) + list(comps[5]) + c1_centro
            f_movel_dir = list(comps[6]) + list(comps[8]) + list(comps[9])
            f_fixa_dir = list(comps[10]) + list(comps[11])
            f_marco = list(comps[7])

            g_marco = Group(mesh=build_submesh(f_marco), name="Marco da Janela")
            g_fixa_esq = Group(mesh=build_submesh(f_fixa_esq), name="Folha Fixa Esquerda")
            g_movel_esq = Group(mesh=build_submesh(f_movel_esq), name="Folha de Correr Centro Esquerda")
            g_movel_dir = Group(mesh=build_submesh(f_movel_dir), name="Folha de Correr Centro Direita")
            g_fixa_dir = Group(mesh=build_submesh(f_fixa_dir), name="Folha Fixa Direita")
            loaded_groups = [g_marco, g_fixa_esq, g_movel_esq, g_movel_dir, g_fixa_dir]

    elif "janela_maximar" in igz_path.name:
        if loaded_groups and loaded_groups[0].mesh:
            m = loaded_groups[0].mesh
            def _pt_k(p): return (round(p.x(), 4), round(p.y(), 4), round(p.z(), 4))
            p2f = defaultdict(list)
            for fi, f in enumerate(m.faces):
                for pt in f.vertices: p2f[_pt_k(pt)].append(fi)
            f_adj = [set() for _ in range(len(m.faces))]
            for flist in p2f.values():
                for f1 in flist:
                    for f2 in flist:
                        if f1 != f2: f_adj[f1].add(f2)
            vis = [False] * len(m.faces)
            comps = []
            for i in range(len(m.faces)):
                if not vis[i]:
                    comp = []; q = [i]; vis[i] = True
                    while q:
                        curr = q.pop(); comp.append(curr)
                        for nb in f_adj[curr]:
                            if not vis[nb]: vis[nb] = True; q.append(nb)
                    comps.append(comp)

            def build_submesh(indices):
                nm = Mesh()
                for fi in indices:
                    f = m.faces[fi]
                    nf = nm.add_face([pt for pt in f.vertices])
                    if f.attrs: nf.attrs = dict(f.attrs)
                    for h in f.holes: nm.add_hole(nf, [pt for pt in h])
                return nm

            # comp 3: marco fixo (124 faces)
            # comps 0, 1, 2, 4, 5: folha móvel basculante/projetante (113 faces)
            f_marco = list(comps[3])
            f_folha = list(comps[0]) + list(comps[1]) + list(comps[2]) + list(comps[4]) + list(comps[5])
            g_marco = Group(mesh=build_submesh(f_marco), name="Marco da Janela")
            g_folha = Group(mesh=build_submesh(f_folha), name="Folha Basculante Maxim-Ar")
            loaded_groups = [g_marco, g_folha]

    elif "janela_vertical" in igz_path.name:
        if loaded_groups and loaded_groups[0].mesh:
            m = loaded_groups[0].mesh
            def _pt_k(p): return (round(p.x(), 4), round(p.y(), 4), round(p.z(), 4))
            p2f = defaultdict(list)
            for fi, f in enumerate(m.faces):
                for pt in f.vertices: p2f[_pt_k(pt)].append(fi)
            f_adj = [set() for _ in range(len(m.faces))]
            for flist in p2f.values():
                for f1 in flist:
                    for f2 in flist:
                        if f1 != f2: f_adj[f1].add(f2)
            vis = [False] * len(m.faces)
            comps = []
            for i in range(len(m.faces)):
                if not vis[i]:
                    comp = []; q = [i]; vis[i] = True
                    while q:
                        curr = q.pop(); comp.append(curr)
                        for nb in f_adj[curr]:
                            if not vis[nb]: vis[nb] = True; q.append(nb)
                    comps.append(comp)

            def build_submesh(indices):
                nm = Mesh()
                for fi in indices:
                    f = m.faces[fi]
                    nf = nm.add_face([pt for pt in f.vertices])
                    if f.attrs: nf.attrs = dict(f.attrs)
                    for h in f.holes: nm.add_hole(nf, [pt for pt in h])
                return nm

            # folha móvel: comp 0 (10 faces), comp 5 (9 faces), e 5 faces de caixilho inferior (total 24 faces)
            # marco fixo e bandeiras fixas: 65 faces
            c2_folha = [50, 52, 49, 41, 64]
            f_folha = list(comps[0]) + list(comps[5]) + c2_folha
            f_marco = [fi for fi in range(len(m.faces)) if fi not in f_folha]
            g_marco = Group(mesh=build_submesh(f_marco), name="Marco da Janela")
            g_folha = Group(mesh=build_submesh(f_folha), name="Folha Basculante Vertical")
            loaded_groups = [g_marco, g_folha]

    sub_pieces: List[Group] = []
    def flatten_pieces(g: Group) -> None:
        if g.mesh and len(g.mesh.faces) > 0:
            sub_pieces.append(g)
        for c in getattr(g, "children", []):
            flatten_pieces(c)

    for g in loaded_groups:
        flatten_pieces(g)

    all_pts = [v.position for sp in sub_pieces if sp.mesh for v in sp.mesh.vertices]
    min_x = min(p.x() for p in all_pts) if all_pts else 0.0
    max_x = max(p.x() for p in all_pts) if all_pts else 0.80
    min_y = min(p.y() for p in all_pts) if all_pts else 0.0
    max_y = max(p.y() for p in all_pts) if all_pts else 0.15
    min_z = min(p.z() for p in all_pts) if all_pts else 0.0

    shift_zero = QVector3D(-min_x, -min_y, -min_z)
    for sp in sub_pieces:
        if sp.mesh:
            for v in sp.mesh.vertices:
                v.position += shift_zero
            sp.mesh._mut_serial = getattr(sp.mesh, "_mut_serial", 0) + 1

    # Calcula os limites Y do marco estrutural (após shift_zero) para que o espelhamento
    # Dentro/Fora (flip_y) reflita em torno do centro real do marco na parede!
    frame_names = {"Agrupar#95", "Agrupar#98", "Trilho e Marco Fixo", "Marco e Ferragens Fixas"}
    frame_pts = [
        v.position
        for sp in sub_pieces
        if sp.mesh and (sp.name in frame_names or "Marco" in sp.name or "Trilho" in sp.name)
        for v in sp.mesh.vertices
    ]
    if frame_pts:
        f_min_y = min(p.y() for p in frame_pts)
        f_max_y = max(p.y() for p in frame_pts)
    else:
        f_min_y = 0.0
        f_max_y = max_y - min_y

    res = (sub_pieces, max_x - min_x, f_min_y, f_max_y)
    PORTA_PROTO_CACHE[key] = res
    return res


def load_esquadria_igz(item_id: str, largura_mm: float, altura_mm: float, esp_parede_mm: float, peitoril_mm: float=0.0, offset: Tuple[float, float, float]=(0.0, 0.0, 0.0), rot_z: float=0.0, lado_abertura: str='direita', sentido_abertura: str='interno'):
    """Carrega e instancia o modelo 3D nativo (.igz) com sub-peças dinâmicas isoladas.

    Preserva 100% da fidelidade dos componentes (marco fixo, folha móvel articulável,
    fechadura e maçaneta sem distorção).
    """
    from pathlib import Path

    base_dir = Path(__file__).resolve().parents[1]
    # Modelos originais: portas e janelas em pastas separadas.
    user_portas_path = resolve_igz_path(base_dir, item_id)

    igz_path = user_portas_path
    if not igz_path.exists():
        raise FileNotFoundError(
            f"Modelo .igz de esquadria não encontrado para '{item_id}': {igz_path}"
        )

    # Todo modelo é carregado diretamente do .igz, preservando a fidelidade original.
    return load_porta_original_usuario(
        igz_path=igz_path,
        item_id=item_id,
        largura_mm=largura_mm,
        altura_mm=altura_mm,
        esp_parede_mm=esp_parede_mm,
        peitoril_mm=peitoril_mm,
        offset=offset,
        rot_z=rot_z,
        lado_abertura=lado_abertura,
        sentido_abertura=sentido_abertura,
    )


def load_porta_original_usuario(igz_path: Path, item_id: str, largura_mm: float, altura_mm: float, esp_parede_mm: float, peitoril_mm: float=0.0, offset: Tuple[float, float, float]=(0.0, 0.0, 0.0), rot_z: float=0.0, lado_abertura: str='direita', sentido_abertura: str='interno'):
    """Carrega com máxima fidelidade uma das portas reais fornecidas pelo usuário.

    Preserva 100% da malha geométrica original sem distorcer fechaduras ou puxadores.
    Utiliza protótipo pré-consolidado em cache e cópia vetorizada (transformed_mesh),
    com suporte a inversão de lado (esquerda/direita) e sentido (interno/externo).
    """
    from core.group import transformed_mesh

    proto_pieces, orig_w, f_min_y, f_max_y = get_porta_prototype(igz_path)

    # Suporte a redimensionamento paramétrico contínuo de largura (70, 80, 90cm ou personalizado)
    # sem deformar fechaduras, puxadores, ferragens ou caixilhos/folhas:
    target_w = float(largura_mm) / 1000.0 if largura_mm and float(largura_mm) > 100 else orig_w
    delta_w = target_w - orig_w
    is_j2f = "janela_correr_2f" in igz_path.name
    is_j4f = "janela_correr_4f" in igz_path.name
    cut_x = 0.40 if "porta_pivotante" in igz_path.name else 0.50

    flip_x = str(lado_abertura or "direita").strip().lower().startswith(("esq", "left"))
    flip_y = str(sentido_abertura or "interno").strip().lower().startswith(("ext", "for", "out"))
    lado_norm = "esquerda" if flip_x else "direita"
    sentido_norm = "externo" if flip_y else "interno"

    ox, oy, oz = offset
    peit_m = peitoril_mm / 1000.0
    m_transform = QMatrix4x4()
    m_transform.translate(ox, oy, oz + peit_m)
    if abs(rot_z) > 1e-4:
        m_transform.rotate(rot_z, 0.0, 0.0, 1.0)
    if flip_x or flip_y:
        m_transform.translate(target_w if flip_x else 0.0, (f_min_y + f_max_y) if flip_y else 0.0, 0.0)
        m_transform.scale(-1.0 if flip_x else 1.0, -1.0 if flip_y else 1.0, 1.0)

    odd_reflection = (flip_x != flip_y)

    sub_pieces: List[Group] = []
    ident = QMatrix4x4()
    d_quart = delta_w * 0.25

    for proto in proto_pieces:
        if not proto.mesh:
            cloned_mesh = Mesh()
        else:
            cloned_mesh = transformed_mesh(proto.mesh, ident)
            if abs(delta_w) > 1e-4:
                p_name = proto.name or ""
                if is_j2f:
                    # Janela de correr 2 folhas: escala uniforme em X.
                    # Os limites fixos antigos (0.65/0.60/0.35/0.95) colapsavam a
                    # barra central do marco (~5 cm) quando delta_w era negativo:
                    # em 1,20 os vertices 0.6214+(-0,05) e 0.6714+(-0,10)
                    # coincidiam; abaixo disso a ordem se invertia. Escalar tudo
                    # preserva marco, folhas, vidro e ferragens sem colapsos.
                    scale_x = target_w / orig_w
                    for v in cloned_mesh.vertices:
                        v.position.setX(v.position.x() * scale_x)
                elif is_j4f or "porta_correr_vidro_4f" in igz_path.name:
                    # Janela ou Porta de correr 4 folhas: 2 fixas laterais + 2 móveis centrais
                    center_delta = delta_w * 0.5
                    is_porta_4f = "porta_correr_vidro_4f" in igz_path.name
                    for v in cloned_mesh.vertices:
                        vx = v.position.x()
                        vz = v.position.z()
                        if "Marco" in p_name:
                            if is_porta_4f and 0.70 < vz < 1.20 and 1.30 < vx < 1.60:
                                v.position.setX(vx + center_delta)
                            elif vx > (2.80 if is_porta_4f else 1.80):
                                v.position.setX(vx + delta_w)
                            elif vx > (2.10 if is_porta_4f else 1.30):
                                v.position.setX(vx + d_quart * 3.0)
                            elif vx > (1.40 if is_porta_4f else 0.90):
                                v.position.setX(vx + center_delta if is_porta_4f else vx + d_quart * 2.0)
                            elif vx > (0.70 if is_porta_4f else 0.40):
                                v.position.setX(vx + d_quart)
                        elif "Fixa Esquerda" in p_name:
                            if vx > 0.25:
                                v.position.setX(vx + d_quart)
                        elif "Centro Esquerda" in p_name:
                            if is_porta_4f:
                                if vx > 1.00:
                                    v.position.setX(vx + center_delta)
                                else:
                                    v.position.setX(vx + d_quart)
                            else:
                                if vx > 0.70:
                                    v.position.setX(vx + d_quart * 2.0)
                                else:
                                    v.position.setX(vx + d_quart)
                        elif "Centro Direita" in p_name:
                            if is_porta_4f:
                                if vx > 1.80:
                                    v.position.setX(vx + d_quart * 3.0)
                                else:
                                    v.position.setX(vx + center_delta)
                            else:
                                if vx > 1.15:
                                    v.position.setX(vx + d_quart * 3.0)
                                else:
                                    v.position.setX(vx + d_quart * 2.0)
                        elif "Fixa Direita" in p_name:
                            if vx > (2.50 if is_porta_4f else 1.60):
                                v.position.setX(vx + delta_w)
                            else:
                                v.position.setX(vx + d_quart * 3.0)
                else:
                    for v in cloned_mesh.vertices:
                        if v.position.x() > cut_x:
                            v.position.setX(v.position.x() + delta_w)
            cloned_mesh = transformed_mesh(cloned_mesh, m_transform)
        if odd_reflection and cloned_mesh.faces:
            for face in cloned_mesh.faces:
                # ``Face.vertices`` is a read-only property returning a fresh
                # list; reversing it is a no-op.  Reverse the live loop (and
                # the live hole loops) so normals survive a mirrored axis.
                face.loop.reverse()
                if getattr(face, "hole_loops", None):
                    for hloop in face.hole_loops:
                        hloop.reverse()
            cloned_mesh._mut_serial = getattr(cloned_mesh, "_mut_serial", 0) + 1
        sp = Group(mesh=cloned_mesh, name=proto.name)
        sp.layer = "ESQUADRIAS"
        sub_pieces.append(sp)

    rad = math.radians(rot_z)
    u_dir = QVector3D(math.cos(rad), math.sin(rad), 0.0)
    n_dir = QVector3D(-math.sin(rad), math.cos(rad), 0.0)
    p_orig_2d = QVector3D(ox, oy, 0.0)

    def _local_extents(mesh_obj: Mesh) -> tuple[float, float, float, float]:
        pts = [v.position for v in mesh_obj.vertices]
        if not pts:
            return (0.0, 0.0, 0.0, 0.0)
        us = [QVector3D.dotProduct(QVector3D(p.x(), p.y(), 0.0) - p_orig_2d, u_dir) for p in pts]
        ns = [QVector3D.dotProduct(QVector3D(p.x(), p.y(), 0.0) - p_orig_2d, n_dir) for p in pts]
        return (min(us), max(us), min(ns), max(ns))

    sx = -1.0 if flip_x else 1.0
    sy = -1.0 if flip_y else 1.0

    # Identifica folha e acessórios conforme o tipo de porta
    linked_names = []
    if "porta_madeira_ff" in igz_path.name:
        # Porta de madeira FF: folha, guarnição e maçanetas frente/verso.
        # A malha original é preservada; apenas os papéis cinemáticos mudam.
        macaneta_idx = 0
        for sp in sub_pieces:
            if sp.name == "Agrupar#66":
                sp.name = "Folha da Porta"
            elif sp.name in ("Agrupar#60", "Agrupar#61", "Agrupar#54"):
                sp.name = f"Guarnição {sp.name}"
            elif sp.name in ("Component#20", "Component#5", "Group#13"):
                if sp.name == "Component#20":
                    macaneta_idx += 1
                sp.name = f"Maçaneta {macaneta_idx} {sp.name}"
        linked_names.append("Maçaneta")
        for sp in sub_pieces:
            if sp.name == "Folha da Porta":
                if getattr(sp, "ext", None) is None:
                    sp.ext = {}
                sp.ext["linked_pieces"] = list(linked_names)
                min_u_f, max_u_f, min_n_f, max_n_f = _local_extents(sp.mesh)
                hinge_u = min_u_f if flip_x else max_u_f
                hinge_n = max_n_f if flip_y else min_n_f
                hp_2d = p_orig_2d + u_dir * hinge_u + n_dir * hinge_n
                sp.ext["hinge_pivot"] = QVector3D(hp_2d.x(), hp_2d.y(), 0.0)
                sp.ext["door_angle"] = 95.0 * sx * sy

    elif "porta_madeira_pj" in igz_path.name:
        # Porta do SKP porta+e+janela: folha, painéis decorativos e duas maçanetas.
        linked_names.clear()
        for sp in sub_pieces:
            if sp.name == "Group#6":
                sp.name = "Folha da Porta"
            elif sp.name == "Doorknob_Round2":
                sp.name = "Maçaneta Doorknob"
                if sp.name not in linked_names:
                    linked_names.append(sp.name)
            else:
                sp.name = f"Painel {sp.name}"
                linked_names.append(sp.name)
        for sp in sub_pieces:
            if sp.name == "Folha da Porta":
                if getattr(sp, "ext", None) is None:
                    sp.ext = {}
                sp.ext["linked_pieces"] = list(linked_names)
                min_u_f, max_u_f, min_n_f, max_n_f = _local_extents(sp.mesh)
                hinge_u = min_u_f if flip_x else max_u_f
                hinge_n = max_n_f if flip_y else min_n_f
                hp_2d = p_orig_2d + u_dir * hinge_u + n_dir * hinge_n
                sp.ext["hinge_pivot"] = QVector3D(hp_2d.x(), hp_2d.y(), 0.0)
                sp.ext["door_angle"] = 95.0 * sx * sy

    elif igz_path.name in NOVAS_PORTAS_FOLHAS:
        # Portas dos SKP repostos: a malha original e preservada; apenas
        # os papeis cinematicos (folha, ferragens, marco) sao atribuidos.
        indices_folha = NOVAS_PORTAS_FOLHAS[igz_path.name]
        cinematica = NOVAS_PORTAS_CINEMATICA.get(igz_path.name, {})
        pivotante = "pivotante_ok" in igz_path.name
        for i in indices_folha:
            if not (0 <= i < len(sub_pieces)):
                raise ValueError(
                    f"{igz_path.name}: indice de folha {i} invalido; "
                    f"prototipo tem {len(sub_pieces)} pecas"
                )
        folhas = [sub_pieces[i] for i in indices_folha]
        folhas_set = set(id(f) for f in folhas)
        for n, folha in enumerate(folhas):
            folha.name = ("Folha da Porta" if len(folhas) == 1 else
                          f"Folha {'Esquerda' if n == 0 else 'Direita'}")

        # Renomeia as pecas nao-folha com nomes estaveis e unicos (o
        # casamento de linked_pieces em interact.py e por substring).
        contadores: dict[str, int] = {}
        linked_por_folha: list[list[str]] = [[] for _ in folhas]
        for i, sp in enumerate(sub_pieces):
            if id(sp) in folhas_set:
                continue
            papel, dono = cinematica.get(i, ("fixo", 0))
            prefixo = "Ferragem" if papel == "movel" else "Marco"
            contadores[prefixo] = contadores.get(prefixo, 0) + 1
            sp.name = f"{prefixo} {contadores[prefixo]} {sp.name}"
            if papel == "movel" and 0 <= dono < len(linked_por_folha):
                linked_por_folha[dono].append(sp.name)

        for n, folha in enumerate(folhas):
            if getattr(folha, "ext", None) is None:
                folha.ext = {}
            folha.ext["linked_pieces"] = list(linked_por_folha[n])
            min_u_f, max_u_f, min_n_f, max_n_f = _local_extents(folha.mesh)
            if pivotante:
                hinge_u = (max_u_f - 0.075) if flip_x else (min_u_f + 0.075)
                angle = -90.0 * sx * sy
            elif len(folhas) == 2:
                # Espelhamento em X inverte a orientacao visual das folhas;
                # troca o lado da dobradica para manter a folha rotulada
                # "Esquerda" fisicamente a esquerda.
                primeira = 1 if flip_x else 0
                hinge_u = min_u_f if n == primeira else max_u_f
                angle = 90.0 * sx * sy * (-1 if n == primeira else 1)
            else:
                hinge_u = min_u_f if flip_x else max_u_f
                angle = 95.0 * sx * sy
            hinge_n = max_n_f if flip_y else min_n_f
            hp_2d = p_orig_2d + u_dir * hinge_u + n_dir * hinge_n
            folha.ext["hinge_pivot"] = QVector3D(hp_2d.x(), hp_2d.y(), 0.0)
            folha.ext["door_angle"] = angle

    elif "porta_giro" in igz_path.name:
        for sp in sub_pieces:
            if sp.name == "Agrupar#89":
                sp.name = "Folha da Porta"
            elif sp.name == "Agrupar#95":
                sp.name = "Marco da Porta"
            else:
                sp.name = f"Fechadura {sp.name}"
                linked_names.append(sp.name)
        for sp in sub_pieces:
            if sp.name == "Folha da Porta":
                if getattr(sp, "ext", None) is None:
                    sp.ext = {}
                sp.ext["linked_pieces"] = list(linked_names)
                min_u_f, max_u_f, min_n_f, max_n_f = _local_extents(sp.mesh)
                hinge_u = min_u_f if flip_x else max_u_f
                hinge_n = max_n_f if flip_y else min_n_f
                hp_2d = p_orig_2d + u_dir * hinge_u + n_dir * hinge_n
                sp.ext["hinge_pivot"] = QVector3D(hp_2d.x(), hp_2d.y(), 0.0)
                sp.ext["door_angle"] = 95.0 * sx * sy

    elif "porta_aluminio" in igz_path.name:
        for sp in sub_pieces:
            if sp.name == "Agrupar#91":
                sp.name = "Folha da Porta"
            elif sp.name in ("Agrupar#98", "Marco da Porta"):
                sp.name = "Marco da Porta"
            elif "Agrupar#6" in sp.name:
                sp.name = f"Ferragem {sp.name}"
                linked_names.append(sp.name)
            else:
                sp.name = f"Fechadura {sp.name}"
                linked_names.append(sp.name)
        for sp in sub_pieces:
            if sp.name == "Folha da Porta":
                if getattr(sp, "ext", None) is None:
                    sp.ext = {}
                sp.ext["linked_pieces"] = list(linked_names)
                min_u_f, max_u_f, min_n_f, max_n_f = _local_extents(sp.mesh)
                hinge_u = min_u_f if flip_x else max_u_f
                hinge_n = max_n_f if flip_y else min_n_f
                hp_2d = p_orig_2d + u_dir * hinge_u + n_dir * hinge_n
                sp.ext["hinge_pivot"] = QVector3D(hp_2d.x(), hp_2d.y(), 0.0)
                sp.ext["door_angle"] = 95.0 * sx * sy

    elif "porta_correr_vidro_4f" in igz_path.name:
        for sp in sub_pieces:
            if "Centro Esquerda" in sp.name:
                sp.name = "Folha de Correr Centro Esquerda"
                if getattr(sp, "ext", None) is None:
                    sp.ext = {}
                sp.ext["slide_axis"] = QVector3D(-u_dir.x() * sx, -u_dir.y() * sx, 0.0)
                sp.ext["slide_distance"] = max(0.20, 0.6449 + d_quart)
            elif "Centro Direita" in sp.name:
                sp.name = "Folha de Correr Centro Direita"
                if getattr(sp, "ext", None) is None:
                    sp.ext = {}
                sp.ext["slide_axis"] = QVector3D(u_dir.x() * sx, u_dir.y() * sx, 0.0)
                sp.ext["slide_distance"] = max(0.20, 0.6409 + d_quart)
            elif "Fixa" in sp.name:
                # Folhas fixas laterais não abrem nem giram
                if getattr(sp, "ext", None) is None:
                    sp.ext = {}
                sp.ext["is_fixed"] = True
    elif "porta_correr" in igz_path.name:
        for sp in sub_pieces:
            if "Esquerda" in sp.name:
                sp.name = "Folha de Correr Esquerda"
                if getattr(sp, "ext", None) is None:
                    sp.ext = {}
                # Folha esquerda desliza em direção à folha direita (fica face a face / uma atrás da outra)
                sp.ext["slide_axis"] = QVector3D(u_dir.x() * sx, u_dir.y() * sx, 0.0)
                sp.ext["slide_distance"] = 0.788
            elif "Direita" in sp.name:
                sp.name = "Folha de Correr Direita"
                if getattr(sp, "ext", None) is None:
                    sp.ext = {}
                # Folha direita desliza em direção à folha esquerda
                sp.ext["slide_axis"] = QVector3D(-u_dir.x() * sx, -u_dir.y() * sx, 0.0)
                sp.ext["slide_distance"] = 0.788
            elif "Folha" in sp.name or "Porta" in sp.name:
                sp.name = "Folha de Correr"
                if getattr(sp, "ext", None) is None:
                    sp.ext = {}
                sp.ext["slide_axis"] = QVector3D(u_dir.x() * sx, u_dir.y() * sx, 0.0)
                sp.ext["slide_distance"] = 0.788
            else:
                sp.name = "Trilho e Marco Fixo"

    elif "porta_pivotante" in igz_path.name:
        for sp in sub_pieces:
            if "Puxador" in sp.name or "Braçadeira" in sp.name:
                linked_names.append(sp.name)
        for sp in sub_pieces:
            if "Folha Vidro" in sp.name:
                if getattr(sp, "ext", None) is None:
                    sp.ext = {}
                sp.ext["linked_pieces"] = list(linked_names)
                min_u_f, max_u_f, min_n_f, max_n_f = _local_extents(sp.mesh)
                hinge_u = (max_u_f - 0.075) if flip_x else (min_u_f + 0.075)
                hinge_n = max_n_f if flip_y else min_n_f
                hp_2d = p_orig_2d + u_dir * hinge_u + n_dir * hinge_n
                sp.ext["hinge_pivot"] = QVector3D(hp_2d.x(), hp_2d.y(), 0.0)
                sp.ext["door_angle"] = -90.0 * sx * sy

    elif "janela_correr_pj" in igz_path.name:
        # Janela do SKP porta+e+janela: marco fixo e 4 folhas (2 fixas, 2 de correr).
        curso = 0.40 * (target_w / orig_w)
        for sp in sub_pieces:
            if sp.name == "Group#45":
                sp.name = "Marco da Janela"
                continue
            if getattr(sp, "ext", None) is None:
                sp.ext = {}
            if "Fixa Esquerda" in sp.name:
                sp.name = "Folha Fixa Esquerda"
                sp.ext["is_fixed"] = True
            elif "Correr Esquerda" in sp.name:
                sp.name = "Folha de Correr Esquerda"
                sp.ext["slide_axis"] = QVector3D(u_dir.x() * sx, u_dir.y() * sx, 0.0)
                sp.ext["slide_distance"] = curso
            elif "Correr Direita" in sp.name:
                sp.name = "Folha de Correr Direita"
                sp.ext["slide_axis"] = QVector3D(-u_dir.x() * sx, -u_dir.y() * sx, 0.0)
                sp.ext["slide_distance"] = curso
            elif "Fixa Direita" in sp.name:
                sp.name = "Folha Fixa Direita"
                sp.ext["is_fixed"] = True

    elif "janela_correr_2f" in igz_path.name:
        # O curso de 0.589 m e a diferenca entre as posicoes iniciais das
        # folhas no template de 1,30 m; escala junto com a largura para que
        # a folha movel continue alinhada a fixa em qualquer medida.
        slide_dist_2f = 0.589 * (target_w / orig_w)
        for sp in sub_pieces:
            if "Esquerda" in sp.name:
                if getattr(sp, "ext", None) is None:
                    sp.ext = {}
                sp.ext["slide_axis"] = QVector3D(u_dir.x() * sx, u_dir.y() * sx, 0.0)
                sp.ext["slide_distance"] = slide_dist_2f
            elif "Direita" in sp.name:
                if getattr(sp, "ext", None) is None:
                    sp.ext = {}
                sp.ext["slide_axis"] = QVector3D(-u_dir.x() * sx, -u_dir.y() * sx, 0.0)
                sp.ext["slide_distance"] = slide_dist_2f

    elif "janela_correr_4f" in igz_path.name:
        for sp in sub_pieces:
            if "Centro Esquerda" in sp.name:
                if getattr(sp, "ext", None) is None:
                    sp.ext = {}
                sp.ext["slide_axis"] = QVector3D(-u_dir.x() * sx, -u_dir.y() * sx, 0.0)
                sp.ext["slide_distance"] = max(0.20, 0.4328 + d_quart)
            elif "Centro Direita" in sp.name:
                if getattr(sp, "ext", None) is None:
                    sp.ext = {}
                sp.ext["slide_axis"] = QVector3D(u_dir.x() * sx, u_dir.y() * sx, 0.0)
                sp.ext["slide_distance"] = max(0.20, 0.4459 + d_quart)

    elif "janela_maximar" in igz_path.name:
        for sp in sub_pieces:
            if "Basculante" in sp.name:
                if getattr(sp, "ext", None) is None:
                    sp.ext = {}
                zs = [v.position.z() for v in sp.mesh.vertices]
                pz = max(zs) if zs else oz + peit_m + 0.55
                top_verts = [v.position for v in sp.mesh.vertices if abs(v.position.z() - pz) < 0.015]
                if top_verts:
                    px = sum(v.x() for v in top_verts) / len(top_verts)
                    py = sum(v.y() for v in top_verts) / len(top_verts)
                else:
                    px, py = ox, oy
                sp.ext["hinge_pivot"] = QVector3D(px, py, pz)
                sp.ext["flap_axis"] = QVector3D(u_dir.x(), u_dir.y(), 0.0).normalized()

    elif "janela_vertical" in igz_path.name:
        for sp in sub_pieces:
            if "Basculante" in sp.name:
                if getattr(sp, "ext", None) is None:
                    sp.ext = {}
                zs = [v.position.z() for v in sp.mesh.vertices]
                pz = max(zs) if zs else oz + peit_m + 0.88
                top_verts = [v.position for v in sp.mesh.vertices if abs(v.position.z() - pz) < 0.015]
                if top_verts:
                    px = sum(v.x() for v in top_verts) / len(top_verts)
                    py = sum(v.y() for v in top_verts) / len(top_verts)
                else:
                    px, py = ox, oy
                sp.ext["hinge_pivot"] = QVector3D(px, py, pz)
                sp.ext["flap_axis"] = QVector3D(u_dir.x(), u_dir.y(), 0.0).normalized()

    root_name = f"{item_id.replace('_', ' ').title()} {int(largura_mm)}x{int(altura_mm)}"
    root_grp = Group(name=root_name)
    for sp in sub_pieces:
        sp.owner = root_grp
    root_grp.children.extend(sub_pieces)
    root_grp.layer = "ESQUADRIAS"
    if getattr(root_grp, "ext", None) is None:
        root_grp.ext = {}
    from ..domain.schema import set_esquadria_data
    set_esquadria_data(root_grp, {
        "tipo": item_id,
        "largura_mm": float(largura_mm),
        "altura_mm": float(altura_mm),
        "esp_parede_mm": float(esp_parede_mm),
        "peitoril_mm": float(peitoril_mm),
        "offset": offset,
        "rot_z": float(rot_z),
        "lado_abertura": lado_norm,
        "sentido_abertura": sentido_norm,
    })
    return root_grp


def get_local_mid_y(item_id: str, esp_parede_mm: float=150.0):
    """Retorna a coordenada Y central local da esquadria sem precisar clonar ou construir toda a malha."""
    from pathlib import Path
    base_dir = Path(__file__).resolve().parents[1]
    igz_path = resolve_igz_path(base_dir, item_id)
    if igz_path.exists():
        _, _, min_y, max_y = get_porta_prototype(igz_path)
        return (min_y + max_y) * 0.5
    return (esp_parede_mm / 1000.0) * 0.5
