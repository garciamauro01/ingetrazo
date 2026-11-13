# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors and Pair Programmer.
"""Construtor paramétrico de portas arquitetônicas e gerador de corte booleano em paredes."""
from __future__ import annotations

import math
from typing import Any, Tuple

from PySide6.QtGui import QVector3D
from core.group import Group
from core.mesh import Mesh


def create_oriented_box_mesh(
    origin: QVector3D,
    u: QVector3D,
    v: QVector3D,
    w: QVector3D,
    su: float,
    sv: float,
    sw: float,
    color: tuple[float, float, float] = (0.8, 0.8, 0.8),
) -> Mesh:
    """Cria uma malha sólida de paralelepípedo orientado por 3 vetores unitários ortogonais (u, v, w)."""
    mesh = Mesh()
    p0 = origin
    p1 = origin + u * su
    p2 = origin + u * su + v * sv
    p3 = origin + v * sv
    p4 = p0 + w * sw
    p5 = p1 + w * sw
    p6 = p2 + w * sw
    p7 = p3 + w * sw

    faces = [
        ([p0, p3, p2, p1], color),  # Inferior (-W)
        ([p4, p5, p6, p7], color),  # Superior (+W)
        ([p0, p1, p5, p4], color),  # Frontal (-V)
        ([p2, p3, p7, p6], color),  # Traseira (+V)
        ([p0, p4, p7, p3], color),  # Esquerda (-U)
        ([p1, p2, p6, p5], color),  # Direita (+U)
    ]
    for pts, c in faces:
        f = mesh.add_face(pts)
        f.attrs["color"] = c
    return mesh


def create_oriented_box_group(
    origin: QVector3D,
    u: QVector3D,
    v: QVector3D,
    w: QVector3D,
    su: float,
    sv: float,
    sw: float,
    color: tuple[float, float, float] = (0.8, 0.8, 0.8),
    name: str = "Solid",
) -> Group:
    """Cria um Group contendo um paralelepípedo sólido orientado."""
    mesh = create_oriented_box_mesh(origin, u, v, w, su, sv, sw, color)
    g = Group(mesh, name=name)
    return g


# Cores pré-definidas para acabamentos realistas de portas
DOOR_FINISHES = {
    "Madeira Carvalho": {
        "marco": (0.62, 0.44, 0.28),
        "folha": (0.70, 0.52, 0.35),
        "alizar": (0.60, 0.42, 0.26),
        "macaneta": (0.82, 0.82, 0.82),
    },
    "Madeira Freijó": {
        "marco": (0.55, 0.38, 0.24),
        "folha": (0.62, 0.45, 0.28),
        "alizar": (0.52, 0.35, 0.22),
        "macaneta": (0.85, 0.85, 0.85),
    },
    "Madeira Nogueira": {
        "marco": (0.35, 0.24, 0.17),
        "folha": (0.40, 0.28, 0.20),
        "alizar": (0.33, 0.22, 0.15),
        "macaneta": (0.88, 0.75, 0.35),  # Dourado escovado
    },
    "Branco Laqueado": {
        "marco": (0.95, 0.95, 0.95),
        "folha": (0.97, 0.97, 0.97),
        "alizar": (0.93, 0.93, 0.93),
        "macaneta": (0.20, 0.20, 0.20),  # Preto fosco moderno
    },
    "Preto Fosco": {
        "marco": (0.18, 0.18, 0.18),
        "folha": (0.22, 0.22, 0.22),
        "alizar": (0.16, 0.16, 0.16),
        "macaneta": (0.85, 0.75, 0.40),  # Dourado luxo
    },
    "Cinza Grafite": {
        "marco": (0.32, 0.34, 0.36),
        "folha": (0.38, 0.40, 0.42),
        "alizar": (0.30, 0.32, 0.34),
        "macaneta": (0.85, 0.85, 0.85),
    },
}


def build_parametric_door(
    base_center: QVector3D,
    u_right: QVector3D,
    v_inward: QVector3D,
    w_up: QVector3D,
    width: float = 0.80,
    height: float = 2.10,
    wall_thickness: float = 0.15,
    jamb_width: float = 0.03,
    alizar_width: float = 0.06,
    alizar_thickness: float = 0.015,
    leaf_thickness: float = 0.035,
    open_angle_deg: float = 0.0,
    hinge_side: str = "left",   # "left" ou "right"
    open_inward: bool = True,
    has_alizar: bool = True,
    finish_name: str = "Madeira Carvalho",
) -> Group:
    """Gera uma porta completa agrupada (Marco/Batente, Alisares frontal e traseiro, Folha e Maçaneta).
    
    Coordenadas:
    - base_center: ponto médio inferior do vão na face frontal da parede.
    - u_right: vetor unitário ao longo da largura do vão.
    - v_inward: vetor unitário para o interior da parede (profundidade).
    - w_up: vetor unitário vertical (+Z).
    """
    colors = DOOR_FINISHES.get(finish_name, DOOR_FINISHES["Madeira Carvalho"])
    c_marco = colors["marco"]
    c_folha = colors["folha"]
    c_alizar = colors["alizar"]
    c_macaneta = colors["macaneta"]

    half_w = width / 2.0
    # Canto inferior esquerdo frontal do vão
    left_bottom = base_center - u_right * half_w

    children = []

    # 1. Batentes / Marco (Jambs)
    # 1.1 Batente Esquerdo
    g_jamb_l = create_oriented_box_group(
        left_bottom,
        u_right, v_inward, w_up,
        jamb_width, wall_thickness, height,
        color=c_marco, name="Batente Esquerdo"
    )
    children.append(g_jamb_l)

    # 1.2 Batente Direito
    right_bottom = left_bottom + u_right * (width - jamb_width)
    g_jamb_r = create_oriented_box_group(
        right_bottom,
        u_right, v_inward, w_up,
        jamb_width, wall_thickness, height,
        color=c_marco, name="Batente Direito"
    )
    children.append(g_jamb_r)

    # 1.3 Batente Superior (Travessa do Marco)
    top_pos = left_bottom + w_up * (height - jamb_width)
    g_jamb_top = create_oriented_box_group(
        top_pos,
        u_right, v_inward, w_up,
        width, wall_thickness, jamb_width,
        color=c_marco, name="Travessa Superior Marco"
    )
    children.append(g_jamb_top)

    # 2. Guarnições / Alisares (Molduras em volta do vão em ambos os lados)
    if has_alizar:
        aw = alizar_width
        at = alizar_thickness
        # 2.1 Alisar Frontal (Face exterior: -V)
        # Esquerdo
        orig_alizar_fl = left_bottom - u_right * aw - v_inward * at
        children.append(create_oriented_box_group(
            orig_alizar_fl, u_right, v_inward, w_up,
            aw, at, height + aw,
            color=c_alizar, name="Alisar Frontal Esquerdo"
        ))
        # Direito
        orig_alizar_fr = left_bottom + u_right * width - v_inward * at
        children.append(create_oriented_box_group(
            orig_alizar_fr, u_right, v_inward, w_up,
            aw, at, height + aw,
            color=c_alizar, name="Alisar Frontal Direito"
        ))
        # Superior
        orig_alizar_ft = left_bottom - u_right * aw - v_inward * at + w_up * height
        children.append(create_oriented_box_group(
            orig_alizar_ft, u_right, v_inward, w_up,
            width + 2 * aw, at, aw,
            color=c_alizar, name="Alisar Frontal Superior"
        ))

        # 2.2 Alisar Traseiro (Face interior: +V)
        back_offset = v_inward * wall_thickness
        # Esquerdo
        orig_alizar_bl = left_bottom - u_right * aw + back_offset
        children.append(create_oriented_box_group(
            orig_alizar_bl, u_right, v_inward, w_up,
            aw, at, height + aw,
            color=c_alizar, name="Alisar Traseiro Esquerdo"
        ))
        # Direito
        orig_alizar_br = left_bottom + u_right * width + back_offset
        children.append(create_oriented_box_group(
            orig_alizar_br, u_right, v_inward, w_up,
            aw, at, height + aw,
            color=c_alizar, name="Alisar Traseiro Direito"
        ))
        # Superior
        orig_alizar_bt = left_bottom - u_right * aw + back_offset + w_up * height
        children.append(create_oriented_box_group(
            orig_alizar_bt, u_right, v_inward, w_up,
            width + 2 * aw, at, aw,
            color=c_alizar, name="Alisar Traseiro Superior"
        ))

    # 3. Folha da Porta com Abertura e Pivô Realista
    leaf_w = width - 2 * jamb_width
    leaf_h = height - jamb_width - 0.008  # folga de piso de 8mm
    leaf_z0 = 0.008

    # O pivô real da dobradiça fica na face do batente para a qual a porta abre:
    # Se open_inward = True (abre para o interior): pivô na face interna (v_inward * wall_thickness)
    # Se open_inward = False (abre para o exterior): pivô na face externa (v_inward * 0.0)
    ang_rad = math.radians(open_angle_deg)

    if open_inward:
        # Abre para o interior (+v_inward). Folha fechada fica recuada no rebaixo (-v_inward).
        if hinge_side == "left":
            pivot = left_bottom + u_right * jamb_width + v_inward * wall_thickness + w_up * leaf_z0
            # Ao abrir (ang_rad):
            # u_leaf gira de u_right para +v_inward
            u_leaf = u_right * math.cos(ang_rad) + v_inward * math.sin(ang_rad)
            # v_leaf gira de -v_inward para +u_right (mantendo a espessura para dentro do vão, nunca para o batente!)
            v_leaf = u_right * math.sin(ang_rad) - v_inward * math.cos(ang_rad)
        else:
            # Dobradiça na direita
            pivot = left_bottom + u_right * (width - jamb_width) + v_inward * wall_thickness + w_up * leaf_z0
            # Ao abrir (ang_rad):
            u_leaf = (-u_right) * math.cos(ang_rad) + v_inward * math.sin(ang_rad)
            v_leaf = (-u_right) * math.sin(ang_rad) - v_inward * math.cos(ang_rad)
    else:
        # Abre para o exterior (-v_inward). Folha fechada fica recuada para dentro (+v_inward).
        if hinge_side == "left":
            pivot = left_bottom + u_right * jamb_width + w_up * leaf_z0
            # Ao abrir (ang_rad):
            # u_leaf gira de u_right para -v_inward
            u_leaf = u_right * math.cos(ang_rad) - v_inward * math.sin(ang_rad)
            # v_leaf gira de +v_inward para +u_right (mantendo a espessura para dentro do vão!)
            v_leaf = u_right * math.sin(ang_rad) + v_inward * math.cos(ang_rad)
        else:
            # Dobradiça na direita
            pivot = left_bottom + u_right * (width - jamb_width) + w_up * leaf_z0
            u_leaf = (-u_right) * math.cos(ang_rad) - v_inward * math.sin(ang_rad)
            v_leaf = (-u_right) * math.sin(ang_rad) + v_inward * math.cos(ang_rad)

    g_leaf = create_oriented_box_group(
        pivot,
        u_leaf, v_leaf, w_up,
        leaf_w, leaf_thickness, leaf_h,
        color=c_folha, name="Folha da Porta"
    )
    children.append(g_leaf)

    # 4. Maçaneta / Puxador e Espelho
    # Altura padrão da maçaneta: 1.00m
    handle_h = 1.00
    handle_dist_from_edge = 0.06  # 6cm da borda de abertura
    handle_pos = pivot + u_leaf * (leaf_w - handle_dist_from_edge) + w_up * (handle_h - leaf_z0)

    # Roseta/Espelho frontal
    roseta_f = create_oriented_box_group(
        handle_pos - u_leaf * 0.025 - v_leaf * 0.005,
        u_leaf, v_leaf, w_up,
        0.05, 0.005, 0.15,
        color=c_macaneta, name="Espelho Maçaneta Frontal"
    )
    children.append(roseta_f)

    # Alavanca da Maçaneta frontal
    lever_dir = -u_leaf if (hinge_side == "left") else u_leaf
    lever_orig = handle_pos - v_leaf * 0.055 + w_up * 0.06
    lever_f = create_oriented_box_group(
        lever_orig,
        lever_dir, v_leaf, w_up,
        0.12, 0.05, 0.02,
        color=c_macaneta, name="Alavanca Maçaneta Frontal"
    )
    children.append(lever_f)

    # Roseta/Espelho traseiro
    roseta_b = create_oriented_box_group(
        handle_pos - u_leaf * 0.025 + v_leaf * leaf_thickness,
        u_leaf, v_leaf, w_up,
        0.05, 0.005, 0.15,
        color=c_macaneta, name="Espelho Maçaneta Traseiro"
    )
    children.append(roseta_b)

    # Alavanca traseira
    lever_b_orig = handle_pos + v_leaf * (leaf_thickness + 0.005) + w_up * 0.06
    lever_b = create_oriented_box_group(
        lever_b_orig,
        lever_dir, v_leaf, w_up,
        0.12, 0.05, 0.02,
        color=c_macaneta, name="Alavanca Maçaneta Traseira"
    )
    children.append(lever_b)

    # Monta o contêiner final
    container = Group(name=f"Porta {int(width*100)}x{int(height*100)}cm")
    container.children = children
    container.ext = {
        "porta_parametrica": {
            "width": width,
            "height": height,
            "wall_thickness": wall_thickness,
            "jamb_width": jamb_width,
            "alizar_width": alizar_width,
            "alizar_thickness": alizar_thickness,
            "leaf_thickness": leaf_thickness,
            "open_angle_deg": open_angle_deg,
            "hinge_side": hinge_side,
            "open_inward": open_inward,
            "has_alizar": has_alizar,
            "finish_name": finish_name,
            "base_center": (base_center.x(), base_center.y(), base_center.z()),
            "u_right": (u_right.x(), u_right.y(), u_right.z()),
            "v_inward": (v_inward.x(), v_inward.y(), v_inward.z()),
            "w_up": (w_up.x(), w_up.y(), w_up.z()),
        }
    }
    return container


def build_wall_cutter(
    base_center: QVector3D,
    u_right: QVector3D,
    v_inward: QVector3D,
    w_up: QVector3D,
    width: float = 0.80,
    height: float = 2.10,
    wall_thickness: float = 0.15,
    extra_depth: float = 0.15,
) -> Group:
    """Gera um bloco de corte sólido com folga para perfurar totalmente a parede via operação booleana."""
    half_w = width / 2.0
    # Inicia ligeiramente fora da face frontal (-v_inward * extra_depth)
    # e estende até além da face traseira (+v_inward * (wall_thickness + 2 * extra_depth))
    # Folga inferior de 1cm para garantir corte limpo no piso
    origin = base_center - u_right * half_w - v_inward * extra_depth - w_up * 0.01
    total_depth = wall_thickness + 2.0 * extra_depth
    cutter_height = height + 0.01

    cutter = create_oriented_box_group(
        origin,
        u_right, v_inward, w_up,
        width, total_depth, cutter_height,
        name="Cutter Vão de Porta"
    )
    return cutter


from core.history import Command


class EditDoorCommand(Command):
    """Comando reversível de edição paramétrica de uma porta já posicionada com ajuste automático do recorte na parede."""

    def __init__(self, door_group: Group, new_config: dict[str, Any], viewport=None) -> None:
        self.door_group = door_group
        self.new_config = dict(new_config)
        self.old_config = dict(door_group.ext.get("porta_parametrica", {}))
        self.old_children = list(door_group.children or [])
        self.old_name = door_group.name
        self.new_children = None
        self.viewport = viewport
        self.old_wall_group = None
        self.new_wall_group = None

    def do(self, scene) -> None:
        import core.solids as solids
        ext = self.door_group.ext.get("porta_parametrica", {})
        cfg = dict(self.new_config)

        # Vetores de ancoragem originais da porta
        bc_t = ext.get("base_center", (0.0, 0.0, 0.0))
        u_t = ext.get("u_right", (1.0, 0.0, 0.0))
        v_t = ext.get("v_inward", (0.0, 1.0, 0.0))
        w_t = ext.get("w_up", (0.0, 0.0, 1.0))

        bc = QVector3D(*bc_t)
        u = QVector3D(*u_t)
        v = QVector3D(*v_t)
        w = QVector3D(*w_t)

        old_w = float(ext.get("width", 0.80))
        old_h = float(ext.get("height", 2.10))
        old_wall_t = float(ext.get("wall_thickness", 0.15))

        new_w = float(cfg.get("width", old_w))
        new_h = float(cfg.get("height", old_h))
        new_wall_t = float(cfg.get("wall_thickness", old_wall_t))

        # Se a largura ou altura do vão mudou, reajusta o recorte na parede associada!
        size_changed = (abs(new_w - old_w) > 1e-4 or abs(new_h - old_h) > 1e-4)
        if size_changed and hasattr(scene, "groups"):
            target_wall = None
            for g in scene.groups:
                if g is not self.door_group and solids.is_solid(g):
                    # Verifica se a parede intercepta a região do vão
                    pts = [v.position if hasattr(v, "position") else v for v in g.mesh.vertices]
                    if pts:
                        xs = [pt.x() for pt in pts]
                        ys = [pt.y() for pt in pts]
                        zs = [pt.z() for pt in pts]
                        tol = 0.50
                        if (min(xs) - tol <= bc.x() <= max(xs) + tol and
                            min(ys) - tol <= bc.y() <= max(ys) + tol and
                            min(zs) - tol <= bc.z() <= max(zs) + tol):
                            target_wall = g
                            break

            if target_wall is not None:
                try:
                    # 1. Cicatriza o vão antigo unindo um plug correspondente ao recorte anterior
                    plug_origin = bc - u * (old_w / 2.0)
                    plug = create_oriented_box_group(plug_origin, u, v, w, old_w, old_wall_t, old_h)
                    _, res_healed = solids.run(solids.UNION, [plug, target_wall])
                    healed_wall = res_healed[0]

                    # 2. Corta o novo vão na medida solicitada
                    cutter_new = build_wall_cutter(bc, u, v, w, new_w, new_h, new_wall_t)
                    _, res_new_wall = solids.run(solids.SUBTRACT, [cutter_new, healed_wall])
                    new_wall = res_new_wall[0]

                    # Substitui a parede na cena
                    self.old_wall_group = target_wall
                    self.new_wall_group = new_wall
                    idx = scene.groups.index(target_wall)
                    scene.groups[idx] = new_wall
                except Exception as e:
                    print(f"[PortaParametrica] Aviso ao reajustar recorte da parede: {e}")

        # 3. Reconstrói a porta paramétrica completa
        rebuilt = build_parametric_door(
            bc, u, v, w,
            width=new_w,
            height=new_h,
            wall_thickness=new_wall_t,
            open_angle_deg=cfg.get("open_angle_deg", ext.get("open_angle_deg", 0.0)),
            hinge_side=cfg.get("hinge_side", ext.get("hinge_side", "left")),
            open_inward=cfg.get("open_inward", ext.get("open_inward", True)),
            has_alizar=cfg.get("has_alizar", ext.get("has_alizar", True)),
            finish_name=cfg.get("finish_name", ext.get("finish_name", "Madeira Carvalho")),
        )

        self.new_children = list(rebuilt.children or [])
        self.door_group.children = self.new_children
        self.door_group.ext["porta_parametrica"].update(cfg)
        self.door_group.name = rebuilt.name

        scene.version += 1
        if self.viewport is not None:
            self.viewport.update()

    def undo(self, scene) -> None:
        # Restaura a parede anterior se tiver sido modificada
        if (self.old_wall_group is not None and self.new_wall_group is not None and
            hasattr(scene, "groups") and self.new_wall_group in scene.groups):
            idx = scene.groups.index(self.new_wall_group)
            scene.groups[idx] = self.old_wall_group

        self.door_group.children = self.old_children
        self.door_group.ext["porta_parametrica"] = dict(self.old_config)
        self.door_group.name = self.old_name

        scene.version += 1
        if self.viewport is not None:
            self.viewport.update()


class ToggleDoorCommand(Command):
    """Comando rápido para abrir (90°) ou fechar (0°) a folha da porta com 1 clique."""

    def __init__(self, door_group: Group, viewport=None) -> None:
        self.door_group = door_group
        ext = door_group.ext.get("porta_parametrica", {})
        curr_ang = float(ext.get("open_angle_deg", 0.0))
        target_ang = 0.0 if curr_ang > 10.0 else 90.0
        new_cfg = dict(ext)
        new_cfg["open_angle_deg"] = target_ang
        self._edit_cmd = EditDoorCommand(door_group, new_cfg, viewport)

    def do(self, scene) -> None:
        self._edit_cmd.do(scene)

    def undo(self, scene) -> None:
        self._edit_cmd.undo(scene)


# ==============================================================================
# JANELA PARAMÉTRICA COM CORTE DINÂMICO
# ==============================================================================

WINDOW_FINISHES = {
    "Alumínio Preto": {
        "frame": (0.16, 0.16, 0.16),
        "peitoril": (0.88, 0.88, 0.88),
        "glass": (0.65, 0.82, 0.94),
        "opacity": 0.45,
    },
    "Alumínio Branco": {
        "frame": (0.95, 0.95, 0.95),
        "peitoril": (0.92, 0.92, 0.92),
        "glass": (0.70, 0.85, 0.95),
        "opacity": 0.40,
    },
    "Alumínio Natural": {
        "frame": (0.78, 0.79, 0.80),
        "peitoril": (0.85, 0.85, 0.85),
        "glass": (0.68, 0.84, 0.95),
        "opacity": 0.45,
    },
    "Madeira Carvalho": {
        "frame": (0.62, 0.44, 0.28),
        "peitoril": (0.85, 0.82, 0.78),
        "glass": (0.70, 0.85, 0.95),
        "opacity": 0.45,
    },
    "Madeira Freijó": {
        "frame": (0.55, 0.38, 0.24),
        "peitoril": (0.82, 0.80, 0.76),
        "glass": (0.70, 0.85, 0.95),
        "opacity": 0.45,
    },
}


def build_parametric_window(
    base_center: QVector3D,
    u_right: QVector3D,
    v_inward: QVector3D,
    w_up: QVector3D,
    width: float = 1.20,
    height: float = 1.20,
    sill_height: float = 1.00,
    wall_thickness: float = 0.15,
    frame_width: float = 0.045,
    frame_depth: float = 0.08,
    has_sill: bool = True,
    window_type: str = "sliding",  # "sliding" (correr 2 folhas), "fixed" (fixa), "casement" (abrir 2 folhas)
    open_pct: float = 0.0,         # 0.0 a 100.0%
    finish_name: str = "Alumínio Preto",
) -> Group:
    """Gera uma janela paramétrica completa agrupada com caixilho, peitoril em pedra/alumínio e vidros."""
    colors = WINDOW_FINISHES.get(finish_name, WINDOW_FINISHES["Alumínio Preto"])
    c_frame = colors["frame"]
    c_peitoril = colors["peitoril"]
    c_glass = colors["glass"]
    glass_opacity = colors["opacity"]

    half_w = width / 2.0
    # O vão da janela começa a sill_height acima da base da parede
    bottom_center = base_center + w_up * sill_height
    left_bottom = bottom_center - u_right * half_w

    # Posiciona o caixilho no centro da espessura da parede
    caixilho_y = max(0.01, (wall_thickness - frame_depth) / 2.0)
    frame_origin = left_bottom + v_inward * caixilho_y

    children = []

    # 1. Peitoril / Pingadeira inferior (opcional)
    if has_sill:
        sill_thick = 0.03
        sill_overhang_front = 0.03
        sill_overhang_side = 0.03
        sill_orig = left_bottom - u_right * sill_overhang_side - v_inward * sill_overhang_front - w_up * (sill_thick - 0.005)
        sill_w = width + 2 * sill_overhang_side
        sill_d = wall_thickness + 2 * sill_overhang_front
        g_sill = create_oriented_box_group(
            sill_orig, u_right, v_inward, w_up,
            sill_w, sill_d, sill_thick,
            color=c_peitoril, name="Peitoril / Pingadeira"
        )
        children.append(g_sill)

    # 2. Caixilho / Marco Perimetral da Janela
    # Marco Esquerdo
    children.append(create_oriented_box_group(
        frame_origin, u_right, v_inward, w_up,
        frame_width, frame_depth, height,
        color=c_frame, name="Marco Esquerdo"
    ))
    # Marco Direito
    children.append(create_oriented_box_group(
        frame_origin + u_right * (width - frame_width), u_right, v_inward, w_up,
        frame_width, frame_depth, height,
        color=c_frame, name="Marco Direito"
    ))
    # Marco Superior
    children.append(create_oriented_box_group(
        frame_origin + w_up * (height - frame_width), u_right, v_inward, w_up,
        width, frame_depth, frame_width,
        color=c_frame, name="Marco Superior"
    ))
    # Marco Inferior
    children.append(create_oriented_box_group(
        frame_origin, u_right, v_inward, w_up,
        width, frame_depth, frame_width,
        color=c_frame, name="Marco Inferior"
    ))

    # 3. Folhas e Vidros
    inner_w = width - 2 * frame_width
    inner_h = height - 2 * frame_width
    inner_origin = frame_origin + u_right * frame_width + w_up * frame_width

    def _make_glass_pane(origin, u, v, w, su, sv, sw, name="Vidro"):
        m = Mesh()
        p0 = origin
        p1 = origin + u * su
        p2 = origin + u * su + v * sv
        p3 = origin + v * sv
        p4 = p0 + w * sw
        p5 = p1 + w * sw
        p6 = p2 + w * sw
        p7 = p3 + w * sw
        for pts in [[p0, p3, p2, p1], [p4, p5, p6, p7], [p0, p1, p5, p4], [p2, p3, p7, p6], [p0, p4, p7, p3], [p1, p2, p6, p5]]:
            f = m.add_face(pts)
            f.attrs["color"] = c_glass
            f.attrs["opacity"] = glass_opacity
            f.attrs["mat"] = "Vidro Incolor"
            f.attrs["back"] = True
        return Group(m, name=name)

    def _make_hollow_sash_frame(orig, u, v, w, sw, sd, sh, profile_w, name="Moldura Folha"):
        """Cria uma moldura oca/vazada (2 montantes verticais e 2 travessas horizontais)."""
        g_sash = Group(name=name)
        # Montante Esquerdo
        g_sash.children.append(create_oriented_box_group(
            orig, u, v, w, profile_w, sd, sh, color=c_frame, name="Montante Esquerdo"
        ))
        # Montante Direito
        g_sash.children.append(create_oriented_box_group(
            orig + u * (sw - profile_w), u, v, w, profile_w, sd, sh, color=c_frame, name="Montante Direito"
        ))
        # Travessa Inferior
        g_sash.children.append(create_oriented_box_group(
            orig + u * profile_w, u, v, w, sw - 2 * profile_w, sd, profile_w, color=c_frame, name="Travessa Inferior"
        ))
        # Travessa Superior
        g_sash.children.append(create_oriented_box_group(
            orig + u * profile_w + w * (sh - profile_w), u, v, w, sw - 2 * profile_w, sd, profile_w, color=c_frame, name="Travessa Superior"
        ))
        return g_sash

    if window_type == "fixed":
        # Vidro único centralizado
        glass_t = 0.008
        g_orig = inner_origin + v_inward * ((frame_depth - glass_t) / 2.0)
        children.append(_make_glass_pane(g_orig, u_right, v_inward, w_up, inner_w, glass_t, inner_h, "Vidro Fixo"))

    elif window_type == "casement":
        # Janela de abrir (2 folhas com dobradiças laterais)
        sash_frame_w = 0.045
        sash_thick = 0.035
        leaf_w = inner_w / 2.0
        ang_deg = (open_pct / 100.0) * 90.0
        ang_rad = math.radians(ang_deg)

        # Folha Esquerda (Moldura vazada + Vidro central)
        piv_l = inner_origin + v_inward * ((frame_depth - sash_thick) / 2.0)
        u_l = u_right * math.cos(ang_rad) - v_inward * math.sin(ang_rad)
        v_l = u_right * math.sin(ang_rad) + v_inward * math.cos(ang_rad)
        children.append(_make_hollow_sash_frame(
            piv_l, u_l, v_l, w_up, leaf_w, sash_thick, inner_h, sash_frame_w, name="Folha Esquerda"
        ))
        glass_l_orig = piv_l + u_l * sash_frame_w + v_l * ((sash_thick - 0.006) / 2.0) + w_up * sash_frame_w
        children.append(_make_glass_pane(
            glass_l_orig, u_l, v_l, w_up, leaf_w - 2 * sash_frame_w, 0.006, inner_h - 2 * sash_frame_w, "Vidro Esquerdo"
        ))

        # Folha Direita (Moldura vazada + Vidro central)
        piv_r = inner_origin + u_right * inner_w + v_inward * ((frame_depth - sash_thick) / 2.0)
        u_r = (-u_right) * math.cos(ang_rad) - v_inward * math.sin(ang_rad)
        v_r = (-u_right) * math.sin(ang_rad) + v_inward * math.cos(ang_rad)
        children.append(_make_hollow_sash_frame(
            piv_r, u_r, v_r, w_up, leaf_w, sash_thick, inner_h, sash_frame_w, name="Folha Direita"
        ))
        glass_r_orig = piv_r + u_r * sash_frame_w + v_r * ((sash_thick - 0.006) / 2.0) + w_up * sash_frame_w
        children.append(_make_glass_pane(
            glass_r_orig, u_r, v_r, w_up, leaf_w - 2 * sash_frame_w, 0.006, inner_h - 2 * sash_frame_w, "Vidro Direito"
        ))

    else:
        # Padrão: Janela de correr 2 folhas (Sliding)
        sash_frame_w = 0.045
        sash_thick = frame_depth * 0.42
        leaf_w = (inner_w / 2.0) + 0.015  # trespasse de 3cm no meio
        max_slide = (inner_w / 2.0) - 0.03
        slide_offset = (open_pct / 100.0) * max_slide

        # Folha 1 (Trilho interno: Moldura vazada + Vidro)
        f1_orig = inner_origin + v_inward * 0.005
        children.append(_make_hollow_sash_frame(
            f1_orig, u_right, v_inward, w_up, leaf_w, sash_thick, inner_h, sash_frame_w, name="Folha Fixa (Trilho Interno)"
        ))
        children.append(_make_glass_pane(
            f1_orig + u_right * sash_frame_w + v_inward * ((sash_thick - 0.006) / 2.0) + w_up * sash_frame_w,
            u_right, v_inward, w_up,
            leaf_w - 2 * sash_frame_w, 0.006, inner_h - 2 * sash_frame_w,
            "Vidro Folha 1"
        ))

        # Folha 2 (Trilho externo corrediça: Moldura vazada móvel + Vidro)
        f2_x = (inner_w / 2.0) - 0.015 - slide_offset
        f2_orig = inner_origin + u_right * f2_x + v_inward * (sash_thick + 0.008)
        children.append(_make_hollow_sash_frame(
            f2_orig, u_right, v_inward, w_up, leaf_w, sash_thick, inner_h, sash_frame_w, name="Folha Móvel (Trilho Externo)"
        ))
        children.append(_make_glass_pane(
            f2_orig + u_right * sash_frame_w + v_inward * ((sash_thick - 0.006) / 2.0) + w_up * sash_frame_w,
            u_right, v_inward, w_up,
            leaf_w - 2 * sash_frame_w, 0.006, inner_h - 2 * sash_frame_w,
            "Vidro Folha 2"
        ))

    container = Group(name=f"Janela {int(width*100)}x{int(height*100)}cm")
    container.children = children
    container.ext = {
        "janela_parametrica": {
            "width": width,
            "height": height,
            "sill_height": sill_height,
            "wall_thickness": wall_thickness,
            "frame_width": frame_width,
            "frame_depth": frame_depth,
            "has_sill": has_sill,
            "window_type": window_type,
            "open_pct": open_pct,
            "finish_name": finish_name,
            "base_center": (base_center.x(), base_center.y(), base_center.z()),
            "u_right": (u_right.x(), u_right.y(), u_right.z()),
            "v_inward": (v_inward.x(), v_inward.y(), v_inward.z()),
            "w_up": (w_up.x(), w_up.y(), w_up.z()),
        }
    }
    return container


def build_window_wall_cutter(
    base_center: QVector3D,
    u_right: QVector3D,
    v_inward: QVector3D,
    w_up: QVector3D,
    width: float = 1.20,
    height: float = 1.20,
    sill_height: float = 1.00,
    wall_thickness: float = 0.15,
    extra_depth: float = 0.15,
) -> Group:
    """Gera um bloco de corte sólido posicionado na altura do peitoril para perfurar a parede."""
    half_w = width / 2.0
    origin = base_center + w_up * sill_height - u_right * half_w - v_inward * extra_depth
    total_depth = wall_thickness + 2.0 * extra_depth

    cutter = create_oriented_box_group(
        origin,
        u_right, v_inward, w_up,
        width, total_depth, height,
        name="Cutter Vão de Janela"
    )
    return cutter


class EditWindowCommand(Command):
    """Comando reversível de edição paramétrica de janela já posicionada com ajuste de recorte."""

    def __init__(self, window_group: Group, new_config: dict[str, Any], viewport=None) -> None:
        self.window_group = window_group
        self.new_config = dict(new_config)
        self.old_config = dict(window_group.ext.get("janela_parametrica", {}))
        self.old_children = list(window_group.children or [])
        self.old_name = window_group.name
        self.viewport = viewport
        self.old_wall_group = None
        self.new_wall_group = None

    def do(self, scene) -> None:
        import core.solids as solids
        ext = self.window_group.ext.get("janela_parametrica", {})
        cfg = dict(self.new_config)

        bc = QVector3D(*ext.get("base_center", (0, 0, 0)))
        u = QVector3D(*ext.get("u_right", (1, 0, 0)))
        v = QVector3D(*ext.get("v_inward", (0, 1, 0)))
        w = QVector3D(*ext.get("w_up", (0, 0, 1)))

        old_w = float(ext.get("width", 1.20))
        old_h = float(ext.get("height", 1.20))
        old_sill = float(ext.get("sill_height", 1.00))
        old_wall_t = float(ext.get("wall_thickness", 0.15))

        new_w = float(cfg.get("width", old_w))
        new_h = float(cfg.get("height", old_h))
        new_sill = float(cfg.get("sill_height", old_sill))
        new_wall_t = float(cfg.get("wall_thickness", old_wall_t))

        # Se mudou largura, altura ou peitoril, reajusta o recorte na parede!
        cut_changed = (abs(new_w - old_w) > 1e-4 or abs(new_h - old_h) > 1e-4 or abs(new_sill - old_sill) > 1e-4)
        if cut_changed and hasattr(scene, "groups"):
            target_wall = None
            mid_z = bc.z() + old_sill + (old_h / 2.0)
            for g in scene.groups:
                if g is not self.window_group and solids.is_solid(g):
                    pts = [pt.position if hasattr(pt, "position") else pt for pt in g.mesh.vertices]
                    if pts:
                        xs = [p.x() for p in pts]
                        ys = [p.y() for p in pts]
                        zs = [p.z() for p in pts]
                        tol = 0.50
                        if (min(xs) - tol <= bc.x() <= max(xs) + tol and
                            min(ys) - tol <= bc.y() <= max(ys) + tol and
                            min(zs) - tol <= mid_z <= max(zs) + tol):
                            target_wall = g
                            break

            if target_wall is not None:
                try:
                    # 1. Plug para fechar o vão antigo
                    plug_origin = bc + w * old_sill - u * (old_w / 2.0)
                    plug = create_oriented_box_group(plug_origin, u, v, w, old_w, old_wall_t, old_h)
                    _, res_healed = solids.run(solids.UNION, [plug, target_wall])
                    healed_wall = res_healed[0]

                    # 2. Novo cutter com novas dimensões
                    cutter_new = build_window_wall_cutter(bc, u, v, w, new_w, new_h, new_sill, new_wall_t)
                    _, res_new_wall = solids.run(solids.SUBTRACT, [cutter_new, healed_wall])
                    new_wall = res_new_wall[0]

                    self.old_wall_group = target_wall
                    self.new_wall_group = new_wall
                    idx = scene.groups.index(target_wall)
                    scene.groups[idx] = new_wall
                except Exception as e:
                    print(f"[JanelaParametrica] Aviso ao reajustar recorte da parede: {e}")

        # 3. Reconstrói a janela
        rebuilt = build_parametric_window(
            bc, u, v, w,
            width=new_w,
            height=new_h,
            sill_height=new_sill,
            wall_thickness=new_wall_t,
            frame_width=cfg.get("frame_width", ext.get("frame_width", 0.045)),
            frame_depth=cfg.get("frame_depth", ext.get("frame_depth", 0.08)),
            has_sill=cfg.get("has_sill", ext.get("has_sill", True)),
            window_type=cfg.get("window_type", ext.get("window_type", "sliding")),
            open_pct=cfg.get("open_pct", ext.get("open_pct", 0.0)),
            finish_name=cfg.get("finish_name", ext.get("finish_name", "Alumínio Preto")),
        )
        self.window_group.children = list(rebuilt.children or [])
        self.window_group.ext["janela_parametrica"].update(cfg)
        self.window_group.name = rebuilt.name

        scene.version += 1
        if self.viewport is not None:
            self.viewport.update()

    def undo(self, scene) -> None:
        if (self.old_wall_group is not None and self.new_wall_group is not None and
            hasattr(scene, "groups") and self.new_wall_group in scene.groups):
            idx = scene.groups.index(self.new_wall_group)
            scene.groups[idx] = self.old_wall_group

        self.window_group.children = self.old_children
        self.window_group.ext["janela_parametrica"] = dict(self.old_config)
        self.window_group.name = self.old_name

        scene.version += 1
        if self.viewport is not None:
            self.viewport.update()


class ToggleWindowCommand(Command):
    """Comando rápido para abrir (50%) ou fechar (0%) a janela com 1 clique."""

    def __init__(self, window_group: Group, viewport=None) -> None:
        self.window_group = window_group
        ext = window_group.ext.get("janela_parametrica", {})
        curr_pct = float(ext.get("open_pct", 0.0))
        target_pct = 0.0 if curr_pct > 5.0 else 50.0
        new_cfg = dict(ext)
        new_cfg["open_pct"] = target_pct
        self._edit_cmd = EditWindowCommand(window_group, new_cfg, viewport)

    def do(self, scene) -> None:
        self._edit_cmd.do(scene)

    def undo(self, scene) -> None:
        self._edit_cmd.undo(scene)



