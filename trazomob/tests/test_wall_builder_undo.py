# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes unitários para atalhos de Undo (Backspace/Ctrl+Z) e trava ortogonal no WallBuilderTool."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QVector3D

from core.history import History
from core.scene import Scene
from trazomob.wall.builder import WallBuilderTool


class DummyViewport:
    """Mock mínimo de viewport para testes da ferramenta WallBuilderTool."""

    def __init__(self, scene: Scene):
        self.scene = scene
        self.history = History(scene)
        self.updated = False
        self.last_msg = ""

    def update(self):
        self.updated = True

    def status_message(self, msg: str):
        self.last_msg = msg

    def flash_status(self, msg: str):
        self.last_msg = msg


class DummyContext:
    """Mock mínimo de ToolContext."""

    def __init__(self, viewport: DummyViewport, world: QVector3D, modifiers=Qt.NoModifier):
        self.viewport = viewport
        self.world = world
        self.modifiers = modifiers


def test_wall_builder_ortho_snap():
    """Testa se a atração ortogonal trava os eixos X e Y quando próximo de 0°, 90°, 180°, 270°."""
    tool = WallBuilderTool(altura_m=2.6, espessura_m=0.15)
    tool.start_point = QVector3D(0, 0, 0)

    # 1. Ponto próximo ao eixo X (ex: dx=3.0, dy=0.1 -> ângulo ~1.9° dentro da tolerância de 15°)
    pt_near_x = QVector3D(3.0, 0.1, 0.0)
    snapped, axis = tool._apply_ortho_snap(pt_near_x)
    assert axis == "x"
    assert snapped.x() == 3.0
    assert snapped.y() == 0.0

    # 2. Ponto próximo ao eixo Y (ex: dx=0.08, dy=2.5 -> ângulo ~88.1°)
    pt_near_y = QVector3D(0.08, 2.5, 0.0)
    snapped, axis = tool._apply_ortho_snap(pt_near_y)
    assert axis == "y"
    assert snapped.x() == 0.0
    assert snapped.y() == 2.5

    # 3. Ponto em diagonal livre sem shift (dx=2.0, dy=2.0 -> 45°)
    pt_diag = QVector3D(2.0, 2.0, 0.0)
    snapped, axis = tool._apply_ortho_snap(pt_diag, shift_held=False)
    assert axis is None
    assert snapped == pt_diag

    # 4. Ponto em diagonal COM Shift pressionado -> trava no eixo dominante (dx >= dy -> eixo X)
    snapped_shift, axis_shift = tool._apply_ortho_snap(pt_diag, shift_held=True)
    assert axis_shift == "x"
    assert snapped_shift.x() == 2.0
    assert snapped_shift.y() == 0.0


def test_wall_builder_undo_backspace():
    """Testa desfazer segmento por segmento com Backspace sem perder o fluxo do desenho."""
    scene = Scene()
    vp = DummyViewport(scene)
    tool = WallBuilderTool(altura_m=2.6, espessura_m=0.15)

    # Clique 1: Origem (0, 0)
    tool.on_click(DummyContext(vp, QVector3D(0, 0, 0)))
    assert len(tool.chain_points) == 1
    assert tool.start_point == QVector3D(0, 0, 0)
    assert tool._current_wall_group is None

    # Simula hover no eixo X e digita 3.0m no VCB
    tool.hover_point = QVector3D(3.0, 0.0, 0.0)
    applied = tool.on_value(vp, 3.0)
    assert applied is True
    assert len(tool.chain_points) == 2
    assert tool.start_point == QVector3D(3.0, 0.0, 0.0)
    assert tool._current_wall_group in scene.groups

    # Simula hover no eixo Y e digita 2.5m no VCB
    tool.hover_point = QVector3D(3.0, 2.5, 0.0)
    applied = tool.on_value(vp, 2.5)
    assert applied is True
    assert len(tool.chain_points) == 3
    assert tool.start_point == QVector3D(3.0, 2.5, 0.0)

    # Pressiona Backspace: deve remover o 2º segmento (voltar para 3.0, 0.0)
    handled = tool.on_key(vp, Qt.Key_Backspace, Qt.NoModifier)
    assert handled is True
    assert len(tool.chain_points) == 2
    assert tool.start_point == QVector3D(3.0, 0.0, 0.0)
    assert tool._current_wall_group in scene.groups

    # Pressiona Ctrl+Z: deve remover o 1º segmento (voltar para apenas o ponto inicial 0, 0)
    handled = tool.on_key(vp, Qt.Key_Z, Qt.ControlModifier)
    assert handled is True
    assert len(tool.chain_points) == 1
    assert tool.start_point == QVector3D(0, 0, 0)
    # Grupo de paredes é removido da cena pois sobrou apenas 1 ponto
    assert tool._current_wall_group is None
    assert len(scene.groups) == 0

    # Mais um Backspace cancela o início da parede por completo
    handled = tool.on_key(vp, Qt.Key_Backspace, Qt.NoModifier)
    assert handled is True
    assert tool.start_point is None
    assert len(tool.chain_points) == 0


def test_wall_builder_snap_existing_wall_t_junction():
    """Testa se o cursor atrai cantos existentes e pontos médios/arestas de paredes para junção em T."""
    scene = Scene()
    vp = DummyViewport(scene)

    # 1. Cria uma parede existente de (0,0) até (5,0)
    pts_existente = [QVector3D(0, 0, 0), QVector3D(5, 0, 0)]
    grp_parede1 = WallBuilderTool.build_chain_group(
        scene=scene,
        pts=pts_existente,
        is_closed=False,
        altura_m=2.6,
        espessura_m=0.15,
        name_override="Parede Sala",
    )
    scene.groups.append(grp_parede1)

    tool = WallBuilderTool(altura_m=2.6, espessura_m=0.15)

    # 2. Testa atração a um canto existente: cursor próximo de (5, 0)
    pt_canto, tipo_canto, snap_grp, snap_seg = tool._find_snap_on_existing_walls(QVector3D(4.9, 0.05, 0.0), scene, threshold_m=0.25)
    assert tipo_canto == "canto"
    assert pt_canto == QVector3D(5, 0, 0)
    assert snap_grp is grp_parede1

    # 3. Testa atração ao meio da parede para junção em T: cursor em (2.5, 0.08)
    pt_t, tipo_t, snap_grp_t, snap_seg_t = tool._find_snap_on_existing_walls(QVector3D(2.5, 0.08, 0.0), scene, threshold_m=0.25)
    assert tipo_t == "juncao_t"
    assert abs(pt_t.x() - 2.5) < 1e-4
    assert abs(pt_t.y() - 0.0) < 1e-4
    assert snap_grp_t is grp_parede1

    # 4. Inicia uma parede transversal perpendicular a partir dessa junção em T
    tool.on_hover(DummyContext(vp, QVector3D(2.5, 0.08, 0.0)))
    assert tool.hover_point == pt_t
    assert tool._snap_info == "juncao_t"

    tool.on_click(DummyContext(vp, tool.hover_point))
    assert tool.start_point == pt_t
    assert len(tool.chain_points) == 1

    # Digita 3m no VCB para subir a parede transversal
    tool.hover_point = pt_t + QVector3D(0, 3.0, 0)
    applied = tool.on_value(vp, 3.0)
    assert applied is True
    assert len(tool.chain_points) == 2

    # Pressiona Enter para finalizar a divisória aberta
    handled_enter = tool.on_key(vp, Qt.Key_Return, Qt.NoModifier)
    assert handled_enter is True
    assert tool.start_point is None
    assert len(tool.chain_points) == 0
    # Duas paredes distintas e sólidas foram construídas
    assert len(scene.groups) == 2
    host_wall = [g for g in scene.groups if g.name == "Parede Sala"][0]
    branch_wall = [g for g in scene.groups if g is not host_wall][0]
    assert len(host_wall.mesh.faces) > 0
    assert len(branch_wall.mesh.faces) > 0


def test_wall_builder_annex_room_closure_floor_ceiling():
    """Testa o caso real relatado pelo usuário: cômodo 1 existente (retângulo 4x4m),

    inicia 2º cômodo no canto (4, 0), faz 3 paredes novas e fecha no canto (4, 4) da parede existente,
    gerando automaticamente o piso do novo cômodo.
    """
    scene = Scene()
    vp = DummyViewport(scene)

    # 1. Cria Cômodo 1 existente (0,0) -> (4,0) -> (4,4) -> (0,4)
    pts_comodo1 = [QVector3D(0, 0, 0), QVector3D(4, 0, 0), QVector3D(4, 4, 0), QVector3D(0, 4, 0)]
    grp_parede1 = WallBuilderTool.build_chain_group(
        scene=scene,
        pts=pts_comodo1,
        is_closed=True,
        altura_m=2.6,
        espessura_m=0.15,
        name_override="Cômodo 1",
    )
    scene.groups.append(grp_parede1)

    # Piso do cômodo 1
    piso1 = WallBuilderTool.build_chain_group(scene, pts_comodo1, is_closed=True, altura_m=2.6, espessura_m=0.15)
    floor1 = WallBuilderTool._build_floor(None, scene, pts_comodo1)
    if floor1:
        floor1.do(scene)

    assert len(scene.groups) == 2  # parede1 + piso1

    # 2. Inicia Cômodo 2: clica no canto existente (4, 0)
    tool = WallBuilderTool(altura_m=2.6, espessura_m=0.15)
    tool.on_hover(DummyContext(vp, QVector3D(3.98, 0.02, 0.0)))
    assert tool._snap_info == "canto"
    assert tool.hover_point == QVector3D(4, 0, 0)

    # Clique 1: no canto (4, 0)
    tool.on_click(DummyContext(vp, tool.hover_point))
    assert tool.start_point == QVector3D(4, 0, 0)
    assert tool._initial_snap_grp is grp_parede1

    # Parede 1 do cômodo 2: avança +3m em X -> (7, 0)
    tool.hover_point = QVector3D(7, 0, 0)
    tool.on_click(DummyContext(vp, tool.hover_point))
    assert len(tool.chain_points) == 2

    # Parede 2 do cômodo 2: sobe +4m em Y -> (7, 4)
    tool.hover_point = QVector3D(7, 4, 0)
    tool.on_click(DummyContext(vp, tool.hover_point))
    assert len(tool.chain_points) == 3

    # Parede 3 do cômodo 2: fecha no canto existente da parede 1 em (4, 4)
    tool.on_hover(DummyContext(vp, QVector3D(4.05, 3.95, 0.0)))
    assert tool._snap_info == "canto"
    assert tool.hover_point == QVector3D(4, 4, 0)
    assert tool._snap_wall_grp is grp_parede1

    # Clique de fechamento no canto existente (4, 4)
    tool.on_click(DummyContext(vp, tool.hover_point))

    # A ferramenta deve ter detectado o fechamento com parede existente:
    # 1. Resetou o estado de desenho
    assert tool.start_point is None
    assert len(tool.chain_points) == 0

    # 2. Criou a nova parede e gerou automaticamente o novo Piso do Cômodo 2
    pisos = [g for g in scene.groups if getattr(g, "ext", {}).get("trazomob_floor")]
    assert len(pisos) == 2  # piso do comodo 1 + piso do comodo 2

    # 3. Verifica se as novas paredes foram seccionadas individualmente
    paredes = [g for g in scene.groups if getattr(g, "ext", {}).get("trazomob_wall")]
    # 1 parede existente do cômodo 1 + 3 paredes seccionadas do novo cômodo anexo = 4 paredes
    assert len(paredes) == 4
    # O comodo anexo gera 3 paredes seccionadas identificadas por 'Parede #'
    novas_paredes = [p for p in paredes if p.name.startswith("Parede #")]
    assert len(novas_paredes) == 3
    for pw in novas_paredes:
        assert len(pw.mesh.faces) > 0


def test_wall_builder_corner_t_junction():
    """Testa o bug relatado: cômodo fechado (0,0)->(4,0)->(4,4)->(0,4).
    Em seguida, inicia uma nova parede no canto (4,0) avançando para (7,0) formando um T.
    A nova parede deve se integrar perfeitamente à quina externa da parede existente,
    sem invadir o vão interno do cômodo e mantendo alinhamento coplanar contínuo.
    """
    scene = Scene()
    vp = DummyViewport(scene)

    # 1. Cria Cômodo Fechado (0,0) -> (4,0) -> (4,4) -> (0,4)
    pts_comodo = [QVector3D(0, 0, 0), QVector3D(4, 0, 0), QVector3D(4, 4, 0), QVector3D(0, 4, 0)]
    grp_comodo = WallBuilderTool.build_chain_group(
        scene=scene,
        pts=pts_comodo,
        is_closed=True,
        altura_m=2.6,
        espessura_m=0.15,
        name_override="Cômodo Fechado",
    )
    scene.groups.append(grp_comodo)

    tool = WallBuilderTool(altura_m=2.6, espessura_m=0.15)

    # 2. Hover no canto (4, 0)
    tool.on_hover(DummyContext(vp, QVector3D(3.95, 0.05, 0.0)))
    assert tool._snap_info == "canto"
    assert tool.hover_point == QVector3D(4, 0, 0)

    # Clique no canto (4, 0) para iniciar nova parede
    tool.on_click(DummyContext(vp, tool.hover_point))
    assert tool.start_point == QVector3D(4, 0, 0)
    assert tool._initial_snap_grp is grp_comodo

    # Move para (7, 0) e clica para formar a parede em T
    tool.hover_point = QVector3D(7, 0, 0)
    tool.on_click(DummyContext(vp, tool.hover_point))

    # Pressiona Enter para finalizar a parede aberta
    tool.on_key(vp, Qt.Key_Return, Qt.NoModifier)

    # Verifica se a nova parede foi construída
    paredes = [g for g in scene.groups if getattr(g, "ext", {}).get("trazomob_wall")]
    assert len(paredes) == 2
    parede_t = [p for p in paredes if p is not grp_comodo and p.name != "Cômodo Fechado"][0]
    parede_host = [p for p in paredes if p.name == "Cômodo Fechado"][0]

    # Vértices da base do segmento da parede T
    mesh_t = parede_t.mesh
    assert len(mesh_t.faces) > 0

    # Garante que nenhum vértice da nova parede invade o interior do cômodo fechado (onde 0 < X < 4 e 0 < Y < 4)
    for v in mesh_t.vertices:
        p = v.position
        inside_comodo = (0.01 < p.x() < 3.99) and (0.01 < p.y() < 3.99)
        assert not inside_comodo, f"Vértice {p} invadiu o interior do cômodo fechado!"






def test_wall_builder_partition_cuts_room_and_persists():
    """Testa o caso relatado pelo usuário: cômodo fechado existente cortado por uma nova parede divisória.
    O primeiro clique ancora com snap na parede 1, e o segundo clique fecha em T na parede oposta,
    criando a parede divisória como sólido 3D completo que persiste na cena sem sumir.
    """
    class DummyHistory:
        def __init__(self, sc):
            self.scene = sc
            self.undo_stack = []
        def execute(self, cmd):
            cmd.do(self.scene)
            self.undo_stack.append(cmd)

    class DummyViewport:
        def __init__(self, sc):
            self.scene = sc
            self.history = DummyHistory(sc)
        def update(self):
            pass
        def flash_status(self, msg):
            pass

    class DummyContext:
        def __init__(self, vp, pt):
            self.viewport = vp
            self.world = pt

    scene = Scene()
    vp = DummyViewport(scene)

    # 1. Cria cômodo 4x3m seccionado em paredes individuais
    pts_comodo = [QVector3D(0, 0, 0), QVector3D(4, 0, 0), QVector3D(4, 3, 0), QVector3D(0, 3, 0)]
    mono = WallBuilderTool.build_chain_group(scene, pts_comodo, is_closed=True, altura_m=2.6, espessura_m=0.15)
    subs = WallBuilderTool.split_wall_group_into_segments(mono)
    scene.groups.extend(subs)

    assert len(scene.groups) == 4

    # 2. Inicia divisória cortando o cômodo de (2, 0) a (2, 3)
    tool = WallBuilderTool(altura_m=2.6, espessura_m=0.15)

    # Clique 1: snap na parede sul em (2, 0)
    tool.on_hover(DummyContext(vp, QVector3D(2.0, 0.05, 0.0)))
    assert tool.hover_point == QVector3D(2.0, 0.0, 0.0)
    tool.on_click(DummyContext(vp, tool.hover_point))

    assert tool.start_point == QVector3D(2.0, 0.0, 0.0)
    assert len(tool.chain_points) == 1

    # Clique 2: fecha na parede norte em (2, 3)
    tool.on_hover(DummyContext(vp, QVector3D(2.0, 2.95, 0.0)))
    assert tool.hover_point == QVector3D(2.0, 3.0, 0.0)
    tool.on_click(DummyContext(vp, tool.hover_point))

    # A ferramenta deve ter detectado closing_with_existing:
    # 1. Resetou para estar pronta para o próximo comando
    assert tool.start_point is None
    assert len(tool.chain_points) == 0

    # 2. A nova parede divisória foi criada e persiste na cena (não sumiu!)
    paredes = [g for g in scene.groups if isinstance(getattr(g, "ext", None), dict) and g.ext.get("trazomob_wall")]
    # 4 paredes originais (subdivididas/abertas no T) + nova parede divisória
    assert len(paredes) >= 5
    for p in paredes:
        assert len(p.mesh.faces) > 0
