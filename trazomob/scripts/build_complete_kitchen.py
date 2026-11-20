# SPDX-License-Identifier: GPL-3.0-or-later
"""Script para construção do ambiente de Cozinha Completa Humanizada (.igz e render Blender)."""
from __future__ import annotations

import os
import sys
import json
import math
from pathlib import Path

# TrazoMob é first-party: a raiz do fork é dois níveis acima deste script.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.scene import Scene
from core.group import Group
from core.mesh import Mesh
from PySide6.QtGui import QVector3D, QMatrix4x4

from trazomob.builders.cabinet import CabinetBuilder
from trazomob.builders.countertops import BancadaBuilder
from trazomob.wall.plan_2d import WallGraph2D
from formats.igz import save_scene, load_into
from formats.gltf import save_glb


def create_box_mesh(
    min_x: float, max_x: float,
    min_y: float, max_y: float,
    min_z: float, max_z: float,
    texture_name: str | None = None,
    color: list[float] | tuple[float, ...] | None = None,
    mat_name: str | None = None,
    sw: float = 1.0, sh: float = 1.0
) -> Mesh:
    mesh = Mesh()
    p0 = QVector3D(min_x, min_y, min_z)
    p1 = QVector3D(max_x, min_y, min_z)
    p2 = QVector3D(max_x, max_y, min_z)
    p3 = QVector3D(min_x, max_y, min_z)
    p4 = QVector3D(min_x, min_y, max_z)
    p5 = QVector3D(max_x, min_y, max_z)
    p6 = QVector3D(max_x, max_y, max_z)
    p7 = QVector3D(min_x, max_y, max_z)

    faces_pts = [
        ([p0, p1, p2, p3], [0, 0, -1]),  # Fundo Z-
        ([p4, p7, p6, p5], [0, 0, 1]),   # Topo Z+
        ([p0, p4, p5, p1], [0, -1, 0]),  # Frente Y-
        ([p2, p6, p7, p3], [0, 1, 0]),   # Trás Y+
        ([p0, p3, p7, p4], [-1, 0, 0]),  # Esq X-
        ([p1, p5, p6, p2], [1, 0, 0]),   # Dir X+
    ]
    for pts, n in faces_pts:
        f = mesh.add_face(pts)
        if color:
            f.attrs["color"] = list(color)
        if mat_name:
            f.attrs["mat"] = mat_name
        if texture_name:
            base_tex = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "textures")
            tex_path = next(
                (p for p in (
                    os.path.join(base_tex, texture_name),
                    os.path.join(base_tex, "mdf", texture_name),
                    os.path.join(base_tex, "marmores", texture_name),
                ) if os.path.exists(p)),
                "",
            )
            if tex_path:
                f.attrs["texture"] = {"path": os.path.normpath(tex_path), "sw": sw, "sh": sh}
    return mesh


def create_french_door_refrigerator(x0: float, y0: float, z0: float, w: float = 0.82, d: float = 0.65, h: float = 1.82) -> Group:
    """Cria geladeira French Door com acabamento Inox Escovado."""
    grp = Group(name="Geladeira French Door Inox")

    # 1. Corpo principal
    m_body = create_box_mesh(
        x0 + 0.02, x0 + w - 0.02, y0, y0 + d - 0.05, z0, z0 + h,
        color=[0.25, 0.25, 0.27, 1.0], mat_name="Gabinete Geladeira Grafite"
    )
    grp.children.append(Group(m_body, name="Corpo Gabinete"))

    # 2. Portas superiores (French Door)
    h_portas_sup = 1.08
    z_portas_sup = z0 + h - h_portas_sup
    w_porta = (w - 0.01) / 2.0

    m_p_esq = create_box_mesh(
        x0, x0 + w_porta, y0 + d - 0.05, y0 + d, z_portas_sup, z0 + h,
        color=[0.82, 0.83, 0.85, 1.0], mat_name="Aco Inox Escovado Geladeira"
    )
    m_p_dir = create_box_mesh(
        x0 + w_porta + 0.01, x0 + w, y0 + d - 0.05, y0 + d, z_portas_sup, z0 + h,
        color=[0.82, 0.83, 0.85, 1.0], mat_name="Aco Inox Escovado Geladeira"
    )
    grp.children.append(Group(m_p_esq, name="Porta Superior Esq"))
    grp.children.append(Group(m_p_dir, name="Porta Superior Dir"))

    # Puxadores verticais
    m_h_esq = create_box_mesh(
        x0 + w_porta - 0.03, x0 + w_porta - 0.01, y0 + d, y0 + d + 0.025, z_portas_sup + 0.15, z_portas_sup + 0.75,
        color=[0.92, 0.92, 0.94, 1.0], mat_name="Puxador Inox Geladeira"
    )
    m_h_dir = create_box_mesh(
        x0 + w_porta + 0.02, x0 + w_porta + 0.04, y0 + d, y0 + d + 0.025, z_portas_sup + 0.15, z_portas_sup + 0.75,
        color=[0.92, 0.92, 0.94, 1.0], mat_name="Puxador Inox Geladeira"
    )
    grp.children.append(Group(m_h_esq, name="Puxador Esq"))
    grp.children.append(Group(m_h_dir, name="Puxador Dir"))

    # 3. Gaveta Freezer Inferior
    h_freezer = z_portas_sup - z0 - 0.015
    m_freezer = create_box_mesh(
        x0, x0 + w, y0 + d - 0.05, y0 + d, z0 + 0.05, z0 + 0.05 + h_freezer,
        color=[0.82, 0.83, 0.85, 1.0], mat_name="Aco Inox Escovado Geladeira"
    )
    grp.children.append(Group(m_freezer, name="Gavetao Freezer"))

    m_h_frz = create_box_mesh(
        x0 + 0.15, x0 + w - 0.15, y0 + d, y0 + d + 0.025, z0 + 0.05 + h_freezer - 0.08, z0 + 0.05 + h_freezer - 0.05,
        color=[0.92, 0.92, 0.94, 1.0], mat_name="Puxador Inox Geladeira"
    )
    grp.children.append(Group(m_h_frz, name="Puxador Freezer"))

    return grp


def create_kitchen_decorations(y_mod: float) -> list[Group]:
    """Cria itens de humanização de alta qualidade sobre a bancada e ilha."""
    decor_groups = []

    # 1. Fruteira moderna de madeira / centro de mesa na Ilha Gourmet
    # Centro da ilha: X = 2.10, Y = 2.30, Z = 0.89
    m_fruteira_base = create_box_mesh(
        2.00, 2.30, 2.25, 2.50, 0.89, 0.92,
        color=[0.80, 0.65, 0.45, 1.0],
        mat_name="Fruteira Madeira Centro"
    )
    # Frutas estilizadas (maçãs / laranjas)
    m_fruta1 = create_box_mesh(2.05, 2.13, 2.30, 2.38, 0.92, 0.99, color=[0.85, 0.15, 0.15, 1.0], mat_name="Maca Vermelha")
    m_fruta2 = create_box_mesh(2.15, 2.23, 2.33, 2.41, 0.92, 0.99, color=[0.95, 0.55, 0.10, 1.0], mat_name="Laranja")
    m_fruta3 = create_box_mesh(2.08, 2.16, 2.39, 2.47, 0.92, 0.98, color=[0.45, 0.75, 0.20, 1.0], mat_name="Maca Verde")
    g_fruteira = Group(name="Fruteira Ilha Gourmet")
    g_fruteira.children = [
        Group(m_fruteira_base, name="Prato Fruteira"),
        Group(m_fruta1, name="Fruta 1"),
        Group(m_fruta2, name="Fruta 2"),
        Group(m_fruta3, name="Fruta 3")
    ]
    decor_groups.append(g_fruteira)

    # 2. Tábua de corte gourmet em madeira nobre sobre a bancada principal
    # X = 2.00 a 2.25, Y = y_mod + 0.20 a y_mod + 0.55, Z = 0.84 a 0.865
    m_tabua = create_box_mesh(
        2.00, 2.25, y_mod + 0.20, y_mod + 0.55, 0.841, 0.860,
        texture_name="bancada_madeira_teca.jpg",
        mat_name="Tabua Madeira Teca",
        sw=0.5, sh=0.5
    )
    g_tabua = Group(m_tabua, name="Tabua de Corte Teca")
    decor_groups.append(g_tabua)

    # 3. Porta-Utensílios / Faqueiro inox e potes de tempero decorativos perto do cooktop
    # X = 3.25 a 3.38, Y = y_mod + 0.10 a y_mod + 0.23, Z = 0.84 a 1.04
    m_faqueiro = create_box_mesh(
        3.25, 3.38, y_mod + 0.10, y_mod + 0.23, 0.841, 1.02,
        color=[0.20, 0.20, 0.22, 1.0],
        mat_name="Bloco Facas Cozinha"
    )
    m_pote1 = create_box_mesh(3.15, 3.22, y_mod + 0.12, y_mod + 0.19, 0.841, 0.96, color=[0.90, 0.90, 0.92, 1.0], mat_name="Pote Porcelana Sal")
    m_pote2 = create_box_mesh(3.15, 3.22, y_mod + 0.22, y_mod + 0.29, 0.841, 0.94, color=[0.90, 0.90, 0.92, 1.0], mat_name="Pote Porcelana Pimenta")
    g_utensilios = Group(name="Utensilios e Temperos Bancada")
    g_utensilios.children = [
        Group(m_faqueiro, name="Bloco Facas"),
        Group(m_pote1, name="Pote 1"),
        Group(m_pote2, name="Pote 2")
    ]
    decor_groups.append(g_utensilios)

    # 4. Pequeno vaso de plantas / suculenta na bancada
    m_vaso = create_box_mesh(1.75, 1.87, y_mod + 0.12, y_mod + 0.24, 0.841, 0.94, color=[0.95, 0.95, 0.95, 1.0], mat_name="Vaso Branco")
    m_planta = create_box_mesh(1.73, 1.89, y_mod + 0.10, y_mod + 0.26, 0.94, 1.06, color=[0.25, 0.55, 0.25, 1.0], mat_name="Planta Suculenta")
    g_vaso = Group(name="Vaso Suculenta Bancada")
    g_vaso.children = [Group(m_vaso, name="Vaso"), Group(m_planta, name="Planta")]
    decor_groups.append(g_vaso)

    return decor_groups


def load_ingetrazo_human_figure(x: float, y: float, z: float) -> Group | None:
    """Carrega figura humana da biblioteca nativa do IngeTrazo e posiciona no ambiente."""
    chica_path = Path(r"d:\projetos\ingetrazo\resources\components\chica.igz")
    if not chica_path.exists():
        return None
    sc_fig = Scene()
    load_into(sc_fig, chica_path)
    if not sc_fig.groups:
        return None

    # Coleta todos os vértices para centralizar no pé
    grp = sc_fig.groups[0]
    xs, ys, zs = [], [], []
    def get_verts(g):
        if g.mesh:
            for v in g.mesh.vertices:
                xs.append(v.position.x())
                ys.append(v.position.y())
                zs.append(v.position.z())
        for ch in g.children:
            get_verts(ch)
    get_verts(grp)
    if not xs:
        return None

    cx = (min(xs) + max(xs)) * 0.5
    cy = (min(ys) + max(ys)) * 0.5
    cz = min(zs)

    dx = x - cx
    dy = y - cy
    dz = z - cz

    def translate_grp(g):
        if g.mesh:
            for v in g.mesh.vertices:
                v.position = QVector3D(v.position.x() + dx, v.position.y() + dy, v.position.z() + dz)
            g.mesh._mut_serial = getattr(g.mesh, "_mut_serial", 0) + 1
        for ch in g.children:
            translate_grp(ch)

    translate_grp(grp)
    grp.name = "Figura Humana Chica"
    return grp


def build_kitchen():
    print("Iniciando montagem arquitetonica e marcenaria da Cozinha...")
    scene = Scene()
    base_dir = Path(__file__).resolve().parents[1]
    tex_dir = base_dir / "assets" / "textures"

    # ── 1. AMBIENTE ARQUITETÔNICO ──────────────────────────────────────
    wall_graph = WallGraph2D()
    wall_graph.thickness = 0.15
    wall_graph.add_segment(0.0, 0.0, 4.40, 0.0)   # Parede Fundo
    wall_graph.add_segment(0.0, 0.0, 0.0, 3.60)   # Parede Esquerda
    wall_graph.add_segment(4.40, 0.0, 4.40, 3.60) # Parede Direita

    g_walls = wall_graph.build_3d_group(scene, altura_m=2.70, z_base=0.0)
    if g_walls:
        g_walls.name = "Paredes da Cozinha"
        for f in g_walls.mesh.faces:
            f.attrs["color"] = [0.93, 0.93, 0.92, 1.0]
            f.attrs["mat"] = "Tinta Parede Off-White"
        scene.groups.append(g_walls)

    m_piso = create_box_mesh(
        -0.2, 4.6, -0.2, 3.8, -0.05, 0.0,
        texture_name="concreto_cimento_queimado.jpg",
        mat_name="Piso Concreto Acetinado",
        sw=2.0, sh=2.0
    )
    g_piso = Group(m_piso, name="Piso Porcelanato")
    scene.groups.append(g_piso)

    m_teto = create_box_mesh(
        -0.2, 4.6, -0.2, 3.8, 2.70, 2.75,
        color=[0.95, 0.95, 0.95, 1.0],
        mat_name="Forro Gesso Branco"
    )
    g_teto = Group(m_teto, name="Teto Gesso")
    scene.groups.append(g_teto)

    # Janela panorâmica moderna na parede dos fundos com árvore de fundo visível
    m_janela_marco = create_box_mesh(
        2.02, 3.18, -0.05, 0.05, 1.15, 1.95,
        color=[0.12, 0.12, 0.12, 1.0],
        mat_name="Aluminio Preto Esquadria"
    )
    m_janela_vidro = create_box_mesh(
        2.06, 3.14, -0.005, 0.005, 1.19, 1.91,
        color=[0.85, 0.92, 0.98, 0.15],
        mat_name="Vidro Cristal Transparente"
    )
    g_janela = Group(name="Janela Cozinha Panoramica")
    g_janela.children = [
        Group(m_janela_marco, name="Marco Janela"),
        Group(m_janela_vidro, name="Vidro Janela")
    ]
    scene.groups.append(g_janela)

    # ── 2. MARCENARIA: MÓDULOS DA LINHA PRINCIPAL (ROT_Z = 180) ────────
    y_mod = 0.15
    # ALTURA DOS BALCÕES: Ajustada para 840mm total (Rodapé 100mm + Caixa 740mm),
    # encostando PERFEITAMENTE na base da bancada de pedra (Z = 0.84m)
    h_balcao = 840.0

    # 2.1 Torre Quente (X = 0.18m a 0.83m)
    p_torre = {
        "tipo": "torre_quente",
        "largura": 650.0,
        "altura": 2200.0,
        "profundidade": 580.0,
        "material": "MDF Louro Freijo 18mm",
        "material_frentes": "MDF Grafite TX 18mm",
        "offset": (0.18, y_mod, 0.0),
        "rot_z": 180.0,
        "puxador_tipo": "cava_45",
        "puxador_cor": "preto",
        "puxador_pos": "padrao",
        "has_forno": True,
        "has_micro": True
    }
    g_torre = CabinetBuilder.build_module_group(p_torre, offset=(0.18, y_mod, 0.0))
    g_torre.name = "Torre Quente (Forno + Micro)"

    x_int_torre = 0.18 + 0.018
    w_int_torre = 0.650 - 2 * 0.018
    z_forno = 0.100 + 0.018 + 0.550 + 0.018
    m_forno = create_box_mesh(
        x_int_torre + 0.005, x_int_torre + w_int_torre - 0.005,
        y_mod + 0.58 - 0.52, y_mod + 0.58 + 0.015,
        z_forno + 0.005, z_forno + 0.595,
        texture_name="eletro_forno_h60_digital.jpg",
        color=[0.15, 0.15, 0.15, 1.0],
        mat_name="Eletro Forno Digital Embutido"
    )
    g_torre.children.append(Group(m_forno, name="Forno Eletrico Digital Embutido"))

    z_micro = z_forno + 0.600 + 0.018
    m_micro = create_box_mesh(
        x_int_torre + 0.005, x_int_torre + w_int_torre - 0.005,
        y_mod + 0.58 - 0.52, y_mod + 0.58 + 0.015,
        z_micro + 0.005, z_micro + 0.395,
        texture_name="eletro_microondas_h35.jpg",
        color=[0.15, 0.15, 0.15, 1.0],
        mat_name="Eletro Microondas Embutido"
    )
    g_torre.children.append(Group(m_micro, name="Microondas Digital Embutido"))
    scene.groups.append(g_torre)

    # 2.2 Torre Geladeira (X = 0.83m a 1.68m)
    p_geladeira = {
        "tipo": "caixa_geladeira",
        "largura": 850.0,
        "altura": 2200.0,
        "profundidade": 600.0,
        "material": "MDF Louro Freijo 18mm",
        "material_frentes": "MDF Grafite TX 18mm",
        "offset": (0.83, y_mod, 0.0),
        "rot_z": 180.0,
        "alt_nicho_geladeira_mm": 1850.0
    }
    g_geladeira = CabinetBuilder.build_module_group(p_geladeira, offset=(0.83, y_mod, 0.0))
    g_geladeira.name = "Torre Geladeira"

    g_refr_french = create_french_door_refrigerator(
        x0=0.85, y0=y_mod + 0.05, z0=0.0, w=0.81, d=0.64, h=1.82
    )
    g_geladeira.children.append(g_refr_french)
    scene.groups.append(g_geladeira)

    # 2.3 Balcões Inferiores com Altura 840mm (Encostando diretamente no tampo Z=0.84m):
    # Gaveteiro 4G
    p_gav = {
        "tipo": "gaveteiro",
        "largura": 450.0,
        "altura": h_balcao,
        "profundidade": 550.0,
        "rodape": 100.0,
        "num_gavetas": 4,
        "material": "MDF Branco TX 15mm",
        "material_frentes": "MDF Louro Freijo 18mm",
        "offset": (1.68, y_mod, 0.0),
        "rot_z": 180.0,
        "puxador_tipo": "perfil_gola",
        "puxador_cor": "preto",
        "perfil_modelo": "gola"
    }
    g_gav = CabinetBuilder.build_module_group(p_gav, offset=(1.68, y_mod, 0.0))
    g_gav.name = "Balcao Gaveteiro 4G"
    scene.groups.append(g_gav)

    # Balcão Pia 2P - portas cobrindo até o topo sem vão
    p_pia = {
        "tipo": "balcao",
        "largura": 1000.0,
        "altura": h_balcao,
        "profundidade": 550.0,
        "rodape": 100.0,
        "num_portas": 2,
        "material": "MDF Branco TX 15mm",
        "material_frentes": "MDF Louro Freijo 18mm",
        "offset": (2.13, y_mod, 0.0),
        "rot_z": 180.0,
        "puxador_tipo": "perfil_gola",
        "puxador_cor": "preto",
        "perfil_modelo": "gola"
    }
    g_pia = CabinetBuilder.build_module_group(p_pia, offset=(2.13, y_mod, 0.0))
    g_pia.name = "Balcao de Pia 2P"
    scene.groups.append(g_pia)

    # Balcão Porta-Tempero
    p_tempero = {
        "tipo": "porta_tempero",
        "largura": 200.0,
        "altura": h_balcao,
        "profundidade": 550.0,
        "rodape": 100.0,
        "material": "MDF Branco TX 15mm",
        "material_frentes": "MDF Louro Freijo 18mm",
        "offset": (3.13, y_mod, 0.0),
        "rot_z": 180.0,
        "puxador_tipo": "perfil_gola",
        "puxador_cor": "preto"
    }
    g_tempero = CabinetBuilder.build_module_group(p_tempero, offset=(3.13, y_mod, 0.0))
    g_tempero.name = "Balcao Porta-Tempero"
    scene.groups.append(g_tempero)

    # Balcão Cooktop / Gavetão
    p_forno = {
        "tipo": "balcao_forno",
        "largura": 800.0,
        "altura": h_balcao,
        "profundidade": 550.0,
        "rodape": 100.0,
        "material": "MDF Branco TX 15mm",
        "material_frentes": "MDF Louro Freijo 18mm",
        "offset": (3.33, y_mod, 0.0),
        "rot_z": 180.0,
        "puxador_tipo": "perfil_gola",
        "puxador_cor": "preto",
        "tem_gaveta": True,
        "alt_gaveta_mm": 200.0
    }
    g_forno = CabinetBuilder.build_module_group(p_forno, offset=(3.33, y_mod, 0.0))
    g_forno.name = "Balcao Cooktop"
    scene.groups.append(g_forno)

    # ── 3. MARMORARIA: BANCADA CALACATTA GOLD MACIÇA (PERFEITAMENTE APOIADA) ────
    # A bancada assenta em Z = 0.84m até 0.88m (40mm de espessura de pedra maciça)
    # A saia frontal desce 40mm (de 0.84 a 0.88m), cobrindo o topo da caixa sem nenhum vão
    g_bancada = Group(name="Bancada Marmore Calacatta Gold")

    m_tampo_pedra = create_box_mesh(
        1.68, 4.15, y_mod, y_mod + 0.60, 0.84, 0.88,
        texture_name="marmore_calacatta_gold.jpg",
        mat_name="Marmore Calacatta Gold",
        sw=1.2, sh=1.2
    )
    m_saia_pedra = create_box_mesh(
        1.68, 4.15, y_mod + 0.58, y_mod + 0.60, 0.81, 0.84,
        texture_name="marmore_calacatta_gold.jpg",
        mat_name="Marmore Calacatta Gold",
        sw=1.2, sh=1.2
    )
    m_frontao_pedra = create_box_mesh(
        1.68, 4.15, y_mod, y_mod + 0.02, 0.88, 1.00,
        texture_name="marmore_calacatta_gold.jpg",
        mat_name="Marmore Calacatta Gold",
        sw=1.2, sh=1.2
    )
    g_bancada.children = [
        Group(m_tampo_pedra, name="Bancada - Tampo Superior Inteirico"),
        Group(m_saia_pedra, name="Bancada - Saia Frontal"),
        Group(m_frontao_pedra, name="Bancada - Frontao Traseiro")
    ]

    # Cuba Inox de sobrepor no Balcão de Pia (X = 2.30m a 2.90m)
    m_cuba = create_box_mesh(
        2.30, 2.90, y_mod + 0.08, y_mod + 0.50, 0.881, 0.885,
        color=[0.80, 0.82, 0.85, 1.0], mat_name="Cuba Inox Acetinado"
    )
    m_bacia = create_box_mesh(
        2.34, 2.86, y_mod + 0.12, y_mod + 0.46, 0.68, 0.88,
        color=[0.72, 0.74, 0.78, 1.0], mat_name="Cuba Inox Acetinado"
    )
    g_bancada.children.extend([Group(m_cuba, name="Cuba - Borda"), Group(m_bacia, name="Cuba - Bacia")])

    # Torneira Gourmet Monocomando Inox
    m_torneira_base = create_box_mesh(
        2.58, 2.62, y_mod + 0.03, y_mod + 0.07, 0.88, 0.92,
        color=[0.88, 0.89, 0.92, 1.0], mat_name="Metal Cromado Torneira"
    )
    m_torneira_corpo = create_box_mesh(
        2.59, 2.61, y_mod + 0.04, y_mod + 0.06, 0.92, 1.25,
        color=[0.88, 0.89, 0.92, 1.0], mat_name="Metal Cromado Torneira"
    )
    m_torneira_bico = create_box_mesh(
        2.59, 2.61, y_mod + 0.04, y_mod + 0.22, 1.23, 1.25,
        color=[0.88, 0.89, 0.92, 1.0], mat_name="Metal Cromado Torneira"
    )
    g_bancada.children.extend([
        Group(m_torneira_base, name="Torneira Base"),
        Group(m_torneira_corpo, name="Torneira Corpo"),
        Group(m_torneira_bico, name="Torneira Bico")
    ])
    scene.groups.append(g_bancada)

    # Cooktop de Indução 4 Bocas
    m_cooktop = create_box_mesh(
        3.45, 4.00, y_mod + 0.07, y_mod + 0.53, 0.881, 0.888,
        color=[0.05, 0.05, 0.05, 1.0],
        mat_name="Cooktop Vidro Preto Vitroceramico"
    )
    g_cooktop = Group(m_cooktop, name="Cooktop de Inducao 4 Bocas")
    scene.groups.append(g_cooktop)

    # ── 4. ARMÁRIOS AÉREOS E ILUMINAÇÃO LED EMBUTIDA (ROT_Z = 180) ─────
    p_aereo1 = {
        "tipo": "aereo_basculante_duplo",
        "largura": 800.0,
        "altura": 700.0,
        "profundidade": 350.0,
        "material": "MDF Branco TX 15mm",
        "material_frentes": "MDF Grafite TX 18mm",
        "offset": (1.68, y_mod, 1.50),
        "rot_z": 180.0,
        "puxador_tipo": "toque"
    }
    g_aereo1 = CabinetBuilder.build_module_group(p_aereo1, offset=(1.68, y_mod, 1.50))
    g_aereo1.name = "Aereo Basculante Duplo"
    scene.groups.append(g_aereo1)

    p_aereo2 = {
        "tipo": "aereo",
        "largura": 950.0,
        "altura": 700.0,
        "profundidade": 350.0,
        "num_portas": 2,
        "material": "MDF Branco TX 15mm",
        "material_frentes": "MDF Grafite TX 18mm",
        "offset": (2.48, y_mod, 1.50),
        "rot_z": 180.0,
        "puxador_tipo": "toque"
    }
    g_aereo2 = CabinetBuilder.build_module_group(p_aereo2, offset=(2.48, y_mod, 1.50))
    g_aereo2.name = "Aereo 2P Vidro/Grafite"
    scene.groups.append(g_aereo2)

    p_aereo3 = {
        "tipo": "aereo_basculante",
        "largura": 720.0,
        "altura": 450.0,
        "profundidade": 350.0,
        "material": "MDF Branco TX 15mm",
        "material_frentes": "MDF Grafite TX 18mm",
        "offset": (3.43, y_mod, 1.75),
        "rot_z": 180.0,
        "puxador_tipo": "toque"
    }
    g_aereo3 = CabinetBuilder.build_module_group(p_aereo3, offset=(3.43, y_mod, 1.75))
    g_aereo3.name = "Aereo Coifa Slim"
    scene.groups.append(g_aereo3)

    m_led = create_box_mesh(
        1.68, 4.15, y_mod + 0.28, y_mod + 0.32, 1.488, 1.498,
        color=[1.0, 0.95, 0.85, 1.0],
        mat_name="Fita LED Emissora Quente 3000K"
    )
    g_led = Group(m_led, name="Iluminacao Fita LED Bancada")
    scene.groups.append(g_led)

    # ── 5. ILHA GOURMET CENTRAL E BANQUETAS ─────────────────────────────
    m_ilha_pedra = create_box_mesh(
        1.60, 3.00, 2.00, 2.80, 0.84, 0.89,
        texture_name="marmore_calacatta_gold.jpg",
        mat_name="Marmore Calacatta Gold",
        sw=1.2, sh=1.2
    )
    g_ilha = Group(m_ilha_pedra, name="Ilha Gourmet Calacatta")
    scene.groups.append(g_ilha)

    m_ilha_base = create_box_mesh(
        1.65, 2.95, 2.05, 2.60, 0.0, 0.84,
        texture_name="mdf_louro_freijo.jpg",
        mat_name="MDF Louro Freijo Ripado Ilha",
        sw=1.0, sh=1.0
    )
    g_ilha_base = Group(m_ilha_base, name="Base Marcenaria Ilha")
    scene.groups.append(g_ilha_base)

    for idx_bq, x_bq in enumerate([1.85, 2.45]):
        m_assento = create_box_mesh(
            x_bq, x_bq + 0.38, 2.85, 3.23, 0.65, 0.71,
            color=[0.25, 0.25, 0.26, 1.0],
            mat_name="Estofado Grafite Banqueta"
        )
        m_pes = create_box_mesh(
            x_bq + 0.03, x_bq + 0.35, 2.88, 3.20, 0.0, 0.65,
            color=[0.10, 0.10, 0.10, 1.0],
            mat_name="Metal Preto Banqueta"
        )
        g_bq = Group(name=f"Banqueta Gourmet {idx_bq+1}")
        g_bq.children = [Group(m_assento), Group(m_pes)]
        scene.groups.append(g_bq)

    # ── 6. HUMANIZAÇÃO: DECORAÇÃO DE COZINHA + FIGURA HUMANA INGETRAZO ──
    for decor in create_kitchen_decorations(y_mod):
        scene.groups.append(decor)

    # Figura humana Chica ao lado da ilha (em pé perto de X=1.35, Y=2.35, Z=0.0)
    g_human = load_ingetrazo_human_figure(x=1.30, y=2.30, z=0.0)
    if g_human:
        scene.groups.append(g_human)

    # ── 7. LUZES TÉCNICAS E CÊNICAS (CALIBRAÇÃO FOTOMÉTRICA CONTRA ESTOURO) ──
    # Potências rebaixadas para eliminar totalmente o estouro de branco
    lights_data = [
        {
            "kind": "led_strip",
            "p1": [1.68, y_mod + 0.30, 1.48],
            "p2": [4.15, y_mod + 0.30, 1.48],
            "dir": [0.0, 0.0, -1.0],
            "color": [1.0, 0.94, 0.84],
            "power": 35.0,  # Reduzido de 65W para 35W
            "on": True
        },
        {
            "kind": "point",
            "pos": [2.30, 2.40, 2.25],
            "color": [1.0, 0.96, 0.90],
            "power": 35.0,  # Reduzido de 60W para 35W
            "on": True
        },
        {"kind": "point", "pos": [1.20, 1.20, 2.65], "color": [1.0, 0.98, 0.96], "power": 25.0, "on": True},
        {"kind": "point", "pos": [3.20, 1.20, 2.65], "color": [1.0, 0.98, 0.96], "power": 25.0, "on": True},
        {"kind": "point", "pos": [2.20, 3.10, 2.65], "color": [1.0, 0.98, 0.96], "power": 25.0, "on": True},
    ]

    print(f"Cena arquitetonica montada com sucesso! ({len(scene.groups)} grupos)")
    return scene, lights_data


def save_and_render():
    scene, lights_data = build_kitchen()

    out_dir = Path(__file__).resolve().parents[1] / "dist"
    out_dir.mkdir(parents=True, exist_ok=True)
    igz_file = out_dir / "cozinha_completa_humanizada.igz"
    save_scene(scene, igz_file)
    print(f"✅ Arquivo .igz salvo em: {igz_file}")

    glb_file = out_dir / "cozinha_completa.glb"
    save_glb(scene, glb_file)
    print(f"✅ Arquivo GLB salvo em: {glb_file}")

    # Câmera arquitetônica com enquadramento suave da linha completa
    eye = QVector3D(4.30, 3.75, 1.40)
    target = QVector3D(2.15, 1.15, 1.05)
    up = QVector3D(0.0, 0.0, 1.0)

    half_h = 1.40 * math.tan(math.radians(52.0) / 2.0)
    camera_info = {
        "eye": [eye.x(), eye.y(), eye.z()],
        "target": [target.x(), target.y(), target.z()],
        "up": [up.x(), up.y(), up.z()],
        "perspective": True,
        "fov_deg": 52.0,
        "half_height": float(half_h),
        "near": 0.1,
        "far": 100.0,
    }

    render_output = out_dir / "cozinha_render_final.png"
    blend_file = out_dir / "cozinha_completa.blend"

    # Sol suave e exposição negativa (-0.75) para controle estrito de estouro
    job = {
        "glb": str(glb_file),
        "output": str(render_output),
        "engine": "cycles",
        "preset": "dia",
        "samples": 64,
        "width": 1280,
        "height": 720,
        "correct_verticals": False,
        "camera": camera_info,
        "sun": [-0.35, 0.60, 0.50],
        "sun_softness": 4.5,
        "lights": lights_data,
        "materials": {
            "Marmore Calacatta Gold": {"type": "pedra", "sub_type": "polido", "roughness": 0.06, "bump": 0.01},
            "Piso Concreto Acetinado": {"type": "pedra", "sub_type": "fosco", "roughness": 0.40, "bump": 0.02},
            "Aco Inox Escovado Geladeira": {"type": "metal", "roughness": 0.18},
            "Puxador Inox Geladeira": {"type": "metal", "roughness": 0.12},
            "Cooktop Vidro Preto Vitroceramico": {"type": "pedra", "sub_type": "polido", "roughness": 0.03},
            "Aluminio Preto Esquadria": {"type": "metal", "roughness": 0.35},
            "Metal Cromado Torneira": {"type": "metal", "roughness": 0.06},
            "Cuba Inox Acetinado": {"type": "metal", "roughness": 0.20},
            "Estofado Grafite Banqueta": {"type": "tecido", "roughness": 0.70},
            "Metal Preto Banqueta": {"type": "metal", "roughness": 0.40},
            "Vidro Cristal Transparente": {"type": "vidro", "roughness": 0.01},
            "Fita LED Emissora Quente 3000K": {"emission_strength": 8.0, "emission_color": [1.0, 0.94, 0.82]}
        },
        "clay_mode": False,
        "exposure": -0.75,  # Exposição fotográfica calibrada para não estourar brancos
        "blend_file": str(blend_file)
    }

    job_path = out_dir / "job.json"
    with open(job_path, "w", encoding="utf-8") as f:
        json.dump(job, f, indent=2)

    print(f"✅ Job de render preparado em: {job_path}")
    return igz_file, glb_file, job_path, render_output


if __name__ == "__main__":
    save_and_render()
