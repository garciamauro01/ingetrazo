# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes para o novo paradigma de Planta Baixa 2D de paredes (WallGraph2D)."""
from core.scene import Scene
from trazomob.wall.plan_2d import WallGraph2D, dist_2d


def test_wall_graph_2d_basic():
    graph = WallGraph2D(default_thickness=0.15, default_height=2.60)
    assert graph.is_empty()

    # Cria parede de (0,0) a (5,0)
    s1 = graph.add_segment(0.0, 0.0, 5.0, 0.0)
    assert s1 is not None
    assert len(graph.segments) == 1
    assert len(graph.nodes) == 2


def test_wall_graph_2d_t_junction_split():
    graph = WallGraph2D(default_thickness=0.15, default_height=2.60)
    # Parede 1: (0,0) a (5,0)
    graph.add_segment(0.0, 0.0, 5.0, 0.0)
    assert len(graph.segments) == 1

    # Parede 2 em T: parte de (2.5, 0.0) e vai para (2.5, 3.0)
    s_t = graph.add_segment(2.5, 0.0, 2.5, 3.0)
    assert s_t is not None

    # A parede hospedeira foi subdividida automaticamente criando um nÃ³ em (2.5, 0)
    # Total de segmentos agora: 2 da hospedeira + 1 da ramificaÃ§Ã£o em T = 3 segmentos
    assert len(graph.segments) == 3
    assert len(graph.nodes) == 4

    # Testa a geraÃ§Ã£o 3D
    scene = Scene()
    grp_3d = graph.build_3d_group(scene, altura_m=2.6)
    assert grp_3d is not None
    assert len(grp_3d.mesh.faces) > 0


def test_wall_graph_2d_split_segment():
    """Adicionar um ponto no meio de uma parede divide-a em dois trechos independentes."""
    graph = WallGraph2D(default_thickness=0.15, default_height=2.60)
    seg = graph.add_segment(0.0, 0.0, 6.0, 0.0)
    assert seg is not None
    assert len(graph.segments) == 1
    assert round(graph.segments[seg].length(graph), 2) == 6.00

    # Divide no ponto t=0.5 (metade, em 3.0, 0)
    new_nid = graph.split_segment(seg, 0.5)
    assert new_nid is not None
    assert len(graph.segments) == 2
    assert len(graph.nodes) == 3

    s_a, s_b = graph.segments[seg], None
    for sid, s in graph.segments.items():
        if sid != seg:
            s_b = s
    assert s_b is not None
    # O segmento original agora vai de (0,0) atÃ© o nÃ³ criado em (3,0)
    assert round(graph.segments[seg].length(graph), 2) == 3.00
    # O novo segmento vai do nÃ³ criado atÃ© (6,0)
    assert round(s_b.length(graph), 2) == 3.00
    assert s_b.node_a_id == new_nid
    # O nÃ³ B original (em 6,0) nÃ¡o mudou; s_b termina nele
    assert s_b.node_b_id == graph.find_node_at(6.0, 0.0)

    # Herdou espessura e altura da parede original
    assert s_b.thickness == graph.segments[seg].thickness
    assert s_b.height == graph.segments[seg].height


def test_wall_graph_2d_merge_node():
    """Remover um nÃ³ interno colinear une dois trechos em uma parede única."""
    graph = WallGraph2D(default_thickness=0.15, default_height=2.60)
    # Parede de (0,0) atÃ© (6,0) jÃ¡ dividida em (3,0)
    graph.add_segment(0.0, 0.0, 3.0, 0.0)
    graph.add_segment(3.0, 0.0, 6.0, 0.0)
    assert len(graph.segments) == 2
    assert len(graph.nodes) == 3

    mid_nid = graph.find_node_at(3.0, 0.0)
    assert mid_nid is not None

    # Os dois trechos sÃ¡o colineares: unindo o nÃ³, resulta em uma parede de 6 m
    merged_id = graph.merge_node(mid_nid)
    assert merged_id is not None
    assert len(graph.segments) == 1
    assert len(graph.nodes) == 2
    remaining = next(iter(graph.segments.values()))
    assert round(remaining.length(graph), 2) == 6.00
    assert set((remaining.node_a_id, remaining.node_b_id)) == {
        graph.find_node_at(0.0, 0.0), graph.find_node_at(6.0, 0.0)
    }


def test_wall_graph_2d_merge_node_corner_not_allowed():
    """NÃ³ de canto (nÃ£o colinear) nÃ£o pode ser unido."""
    graph = WallGraph2D(default_thickness=0.15, default_height=2.60)
    graph.add_segment(0.0, 0.0, 4.0, 0.0)
    graph.add_segment(4.0, 0.0, 4.0, 3.0)

    corner_nid = graph.find_node_at(4.0, 0.0)
    assert corner_nid is not None
    assert graph.mergeable_segments_at(corner_nid) is None
    assert graph.merge_node(corner_nid) is None
    assert len(graph.segments) == 2


def test_wall_graph_2d_merge_node_t_junction_not_allowed():
    """NÃ³ de junÃ§Ã£o em T (grau 3) nÃ£o pode ser unido."""
    graph = WallGraph2D(default_thickness=0.15, default_height=2.60)
    graph.add_segment(0.0, 0.0, 6.0, 0.0)
    graph.add_segment(3.0, 0.0, 3.0, 4.0)
    assert len(graph.segments) == 3

    t_nid = graph.find_node_at(3.0, 0.0)
    assert t_nid is not None
    assert graph.mergeable_segments_at(t_nid) is None
    assert graph.merge_node(t_nid) is None
    assert len(graph.segments) == 3


def test_wall_graph_2d_load_and_continue_editing():
    """Testa reabrir o diÃ¡logo 2D com a parede 3D jÃ¡ existente e dar continuidade."""
    scene = Scene()
    g1 = WallGraph2D(default_thickness=0.15, default_height=2.60)
    g1.add_segment(0.0, 0.0, 4.0, 0.0)
    g1.add_segment(4.0, 0.0, 4.0, 4.0)

    # 1. Gera 3D na cena
    wall_grp = g1.build_3d_group(scene, altura_m=2.6)
    scene.groups.append(wall_grp)

    # 2. Carrega o grafo a partir do grupo existente na cena
    loaded_graph = WallGraph2D.from_group(wall_grp)
    assert loaded_graph is not None
    assert len(loaded_graph.segments) == 2

    # 3. DÃ¡ continuidade desenhando mais uma parede no mesmo layout
    loaded_graph.add_segment(4.0, 4.0, 0.0, 4.0)
    assert len(loaded_graph.segments) == 3

    # 4. Atualiza o grupo 3D
    updated_grp = loaded_graph.build_3d_group(scene, altura_m=2.6)
    assert updated_grp.ext["trazomob_wall"]["num_segments"] == 3


def test_wall_graph_2d_corner_miter_45_deg():
    """Testa se as paredes unidas em canto de 90Â° calculam os vÃ©rtices da bissetriz em 45Â°."""
    g = WallGraph2D(default_thickness=0.20, default_height=2.60)
    # Segmento 1: de (0,0) a (4,0)
    s1 = g.add_segment(0.0, 0.0, 4.0, 0.0)
    # Segmento 2: de (4,0) a (4,3)
    s2 = g.add_segment(4.0, 0.0, 4.0, 3.0)

    polys = g.compute_wall_polygons()
    assert s1 in polys and s2 in polys

    quad1 = polys[s1]
    quad2 = polys[s2]

    # No nÃ³ comum (4,0):
    # Para s1 (node_b em (4,0)), c1 e c2 devem encontrar a bissetriz a 45Â°
    # Para s2 (node_a em (4,0)), c0 e c3 devem ter exatamente as mesmas coordenadas do miter
    # Canto externo: (4.10, -0.10) e canto interno: (3.90, 0.10)
    pts1_corner = { (round(p[0], 2), round(p[1], 2)) for p in (quad1[1], quad1[2]) }
    pts2_corner = { (round(p[0], 2), round(p[1], 2)) for p in (quad2[0], quad2[3]) }

    assert pts1_corner == pts2_corner
    assert (4.10, -0.10) in pts1_corner
    assert (3.90, 0.10) in pts1_corner


def test_wall_graph_2d_t_junction_column():
    """Testa se uma coluna separadora Ã© gerada quando 3 paredes se encontram em um nÃ³ em T."""
    g = WallGraph2D(default_thickness=0.20, default_height=2.60)
    # Parede hospedeira de (0,0) a (6,0)
    g.add_segment(0.0, 0.0, 6.0, 0.0)
    # RamificaÃ§Ã£o em T em (3,0) subindo atÃ© (3,4)
    g.add_segment(3.0, 0.0, 3.0, 4.0)

    # O grafo deve ter 3 segmentos incidindo no nÃ³ (3,0)
    cols = g.compute_columns()
    assert len(cols) == 1
    t_nid = next(iter(cols.keys()))
    t_node = g.nodes[t_nid]
    assert abs(t_node.x - 3.0) < 1e-3 and abs(t_node.y - 0.0) < 1e-3

    c0, c1, c2, c3 = cols[t_nid]
    # Com espessura 0.20, a coluna tem half=0.10: [2.90, 3.10] em X e [-0.10, 0.10] em Y
    assert (round(c0[0], 2), round(c0[1], 2)) == (2.90, -0.10)
    assert (round(c2[0], 2), round(c2[1], 2)) == (3.10, 0.10)

    # Verifica se as paredes terminam exatamente na face externa da coluna
    polys = g.compute_wall_polygons()
    # Segmento 1 (0 -> 3): deve terminar em X=2.90
    s1_quad = polys[1]
    assert round(s1_quad[1][0], 2) == 2.90
    assert round(s1_quad[2][0], 2) == 2.90

    # Segmento 2 (3 -> 6): deve comeÃ§ar em X=3.10
    s2_quad = polys[2]
    assert round(s2_quad[0][0], 2) == 3.10
    assert round(s2_quad[3][0], 2) == 3.10

    # Segmento 3 (ramificaÃ§Ã£o subindo de 3,0 atÃ© 3,4): deve comeÃ§ar em Y=0.10
    s3_quad = polys[3]
    assert round(s3_quad[0][1], 2) == 0.10
    assert round(s3_quad[3][1], 2) == 0.10


def test_wall_graph_2d_move_t_junction_node():
    """Testa arrastar e reposicionar uma junÃ§Ã£o em T, movendo a coluna e as paredes conectadas."""
    g = WallGraph2D(default_thickness=0.20, default_height=2.60)
    g.add_segment(0.0, 0.0, 6.0, 0.0)
    g.add_segment(3.0, 0.0, 3.0, 4.0)

    # Identifica o nÃ³ da junÃ§Ã£o em T (originalmente em x=3.0, y=0.0)
    t_nid = g.find_node_at(3.0, 0.0, threshold=0.1)
    assert t_nid is not None

    # Move a junÃ§Ã£o em T de X=3.0 para X=4.5
    ok = g.move_node(t_nid, 4.5, 0.0)
    assert ok

    # Recalcula as colunas e os polÃ­gonos
    cols = g.compute_columns()
    assert t_nid in cols
    c0, c1, c2, c3 = cols[t_nid]
    # A coluna agora deve estar centralizada em X=4.5
    assert round(c0[0], 2) == 4.40
    assert round(c1[0], 2) == 4.60


def test_wall_graph_2d_set_segment_length():
    """Testa editar o comprimento de uma parede numericamente."""
    g = WallGraph2D(default_thickness=0.15, default_height=2.60)
    s1 = g.add_segment(0.0, 0.0, 3.0, 0.0)
    assert round(g.segments[s1].length(g), 2) == 3.00

    # Altera comprimento de 3.0 para 5.25 metros
    ok = g.set_segment_length(s1, 5.25)
    assert ok
    assert round(g.segments[s1].length(g), 2) == 5.25
    nb = g.nodes[g.segments[s1].node_b_id]
    assert round(nb.x, 2) == 5.25 and round(nb.y, 2) == 0.0


def test_wall_graph_2d_close_loop_detection_and_miter():
    """Testa desenhar 3 paredes abertas e depois fechar com uma 4Âª parede ou editando a medida.

    Verifica se todos os 4 cantos sÃ£o fundidos e detectados com grau 2 gerando cantos a 45Â°.
    """
    g = WallGraph2D(default_thickness=0.20, default_height=2.60)
    # 3 paredes em 'U'
    g.add_segment(0.0, 0.0, 4.0, 0.0)
    g.add_segment(4.0, 0.0, 4.0, 3.0)
    g.add_segment(4.0, 3.0, 0.0, 3.0)

    # Inicialmente estÃ¡ aberto: nÃ³ (0,0) tem grau 1 e nÃ³ (0,3) tem grau 1
    n_start = g.find_node_at(0.0, 0.0)
    n_open = g.find_node_at(0.0, 3.0)
    assert n_start is not None and n_open is not None
    deg_start = sum(1 for s in g.segments.values() if s.node_a_id == n_start or s.node_b_id == n_start)
    assert deg_start == 1

    # Fecha com a 4Âª parede de (0,3) a (0,0)
    g.add_segment(0.0, 3.0, 0.0, 0.0)
    g.merge_close_nodes(threshold=0.25)

    # Agora todos os 4 nÃ³s devem ter grau exatamente 2 (canto fechado)
    for nid, node in g.nodes.items():
        deg = sum(1 for s in g.segments.values() if s.node_a_id == nid or s.node_b_id == nid)
        assert deg == 2

    # Verifica se os 4 cantos formam miter a 45Â°
    polys = g.compute_wall_polygons()
    assert len(polys) == 4
    # Nenhum pilar ou T deve existir pois Ã© um cÃ´modo fechado de 4 cantos
    cols = g.compute_columns()
    assert len(cols) == 0

    # Valida detecÃ§Ã£o de ciclo do cÃ´modo
    cycles = g.find_closed_cycles()
    assert len(cycles) == 1
    assert len(cycles[0]) >= 4


def test_wall_graph_2d_alignment_effects():
    """Garante que toda parede Ã© unificada e calculada 100% pelo eixo central simÃ©trico (th/2 para cada lado)."""
    # Parede horizontal de (0,0) a (4,0) com espessura 0.20m
    # Sentido: de (0,0) para (4,0), vetor u=(1,0), normal Ã  esquerda n=(0,1)
    g_center = WallGraph2D(default_thickness=0.20, default_height=2.60)
    s1 = g_center.add_segment(0.0, 0.0, 4.0, 0.0)
    polys_c = g_center.compute_wall_polygons()
    c0, c1, c2, c3 = polys_c[s1]
    assert round(c0[1], 2) == 0.10
    assert round(c1[1], 2) == 0.10
    assert round(c2[1], 2) == -0.10
    assert round(c3[1], 2) == -0.10


def test_wall_graph_2d_closed_room_no_self_intersecting_quads():
    """Garante que em cÃ´modos fechados (horÃ¡rio ou anti-horÃ¡rio),
    nenhuma parede cruze faces ou tenha Ã¡rea nula/invertida (bowtie quad).
    """
    for loop in [
        [(0, 0), (4, 0), (4, 3), (0, 3)],  # Sentido HorÃ¡rio
        [(0, 0), (0, 3), (4, 3), (4, 0)],  # Sentido Anti-horÃ¡rio
    ]:
        g = WallGraph2D(default_thickness=0.20, default_height=2.60)
        for i in range(len(loop)):
            p1 = loop[i]
            p2 = loop[(i + 1) % len(loop)]
            g.add_segment(p1[0], p1[1], p2[0], p2[1])
        g.merge_close_nodes(threshold=0.1)

        polys = g.compute_wall_polygons()
        assert len(polys) == 4
        for sid, quad in polys.items():
            c0, c1, c2, c3 = quad
            area = 0.5 * (
                (c0[0]*c1[1] - c1[0]*c0[1]) +
                (c1[0]*c2[1] - c2[0]*c1[1]) +
                (c2[0]*c3[1] - c3[0]*c2[1]) +
                (c3[0]*c0[1] - c0[0]*c3[1])
            )
            assert abs(area) >= 0.40, f"Face de parede cruzada ou achatada! sid={sid}, area={area}"


def test_wall_graph_2d_t_junction_alignment():
    """Garante que ao adicionar uma parede em T, a coluna e as extremidades
    das paredes fiquem perfeitamente alinhadas com as faces sem invasÃ£o.
    """
    g = WallGraph2D(default_thickness=0.20, default_height=2.60)
    g.add_segment(0.0, 0.0, 6.0, 0.0)
    g.add_segment(3.0, 0.0, 3.0, 4.0)

    cols = g.compute_columns()
    assert len(cols) == 1
    t_nid = next(iter(cols.keys()))
    c0, c1, c2, c3 = cols[t_nid]

    # A coluna deve ser exatamente quadrada com lado 0.20
    assert round(c1[0] - c0[0], 2) == 0.20
    assert round(c3[1] - c0[1], 2) == 0.20

    # As 3 paredes conectadas devem terminar nas faces da coluna
    polys = g.compute_wall_polygons()
    assert len(polys) == 3
    for sid, quad in polys.items():
        area = 0.5 * (
            (quad[0][0]*quad[1][1] - quad[1][0]*quad[0][1]) +
            (quad[1][0]*quad[2][1] - quad[2][0]*quad[1][1]) +
            (quad[2][0]*quad[3][1] - quad[3][0]*quad[2][1]) +
            (quad[3][0]*quad[0][1] - quad[0][0]*quad[3][1])
        )
        assert abs(area) >= 0.50, "Face cruzada em T!"


def test_custom_dimension_tool_and_wall_update():
    """Garante que a ferramenta de Cotar permite criar cotas entre pontos e editar a medida da parede."""
    g = WallGraph2D(default_thickness=0.15, default_height=2.60)
    s1 = g.add_segment(0.0, 0.0, 4.0, 0.0)
    assert s1 is not None

    # Adiciona cota na face da parede
    d_id = g.add_dimension((0.0, 0.075), (4.0, 0.075), seg_id=s1)
    assert d_id is not None
    assert round(dist_2d(g.dimensions[d_id].p1, g.dimensions[d_id].p2), 2) == 4.00

    # Modifica comprimento da parede via cota
    g.set_segment_length(s1, 5.0)
    assert round(g.segments[s1].length(g), 2) == 5.00


def test_chain_wall_propagation_preserves_previous_walls_and_dimensions():
    """Garante que ao alterar a cota de uma parede em uma cadeia aberta de paredes,
    todas as paredes e cotas jÃ¡ definidas Ã  frente sÃ£o empurradas em bloco sem encolher nem mudar de tamanho.
    """
    g = WallGraph2D(default_thickness=0.15, default_height=2.60)
    # Cria cadeia aberta com 3 paredes (ex: (0,0)->(3,0), (3,0)->(3,2), (3,2)->(6,2))
    s1 = g.add_segment(0, 0, 3, 0)
    s2 = g.add_segment(3, 0, 3, 2)
    s3 = g.add_segment(3, 2, 6, 2)
    g.merge_close_nodes(0.1)

    # Cotas definidas nas paredes s2 e s3
    d2 = g.add_dimension((3.075, 0), (3.075, 2), seg_id=s2)
    d3 = g.add_dimension((3, 2.075), (6, 2.075), seg_id=s3)

    assert round(g.segments[s1].length(g), 2) == 3.00
    assert round(g.segments[s2].length(g), 2) == 2.00
    assert round(g.segments[s3].length(g), 2) == 3.00

    # Altera s2 de 2.00 m para 3.50 m
    g.set_segment_length(s2, 3.50)

    # s1 deve permanecer intacta com 3.00 m
    assert round(g.segments[s1].length(g), 2) == 3.00
    # s2 foi ajustada para 3.50 m
    assert round(g.segments[s2].length(g), 2) == 3.50
    # s3 foi empurrada para frente e permaneceu intacta com 3.00 m!
    assert round(g.segments[s3].length(g), 2) == 3.00
    # A cota d3 de s3 acompanhou o deslocamento e continuou valendo 3.00 m
    assert round(dist_2d(g.dimensions[d3].p1, g.dimensions[d3].p2), 2) == 3.00


def test_wall_floor_and_ceiling_not_duplicated_on_rebuild():
    """Garante que ao reconstruir ou concluir paredes sucessivamente, pisos e tetos nÃ£o se acumulam na cena."""
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication.instance() or QApplication(sys.argv)

    from core.scene import Scene
    from trazomob.wall.floorplan_dialog import WallFloorplanDialog

    scene = Scene()
    class DummyViewport:
        def __init__(self, sc):
            self.scene = sc
        def update(self):
            pass
        def flash_status(self, msg):
            pass

    vp = DummyViewport(scene)

    # 1. Cria um diÃ¡logo desenhando um cÃ´modo retangular fechado de 4m x 3m
    dlg1 = WallFloorplanDialog(vp)
    dlg1.graph.add_segment(0, 0, 4, 0)
    dlg1.graph.add_segment(4, 0, 4, 3)
    dlg1.graph.add_segment(4, 3, 0, 3)
    dlg1.graph.add_segment(0, 3, 0, 0)
    dlg1.chk_floor.setChecked(True)
    dlg1.chk_ceiling.setChecked(True)

    # Conclui e gera na cena
    dlg1._build_3d_and_close()

    # Deve haver: 1 parede, 1 piso, 1 teto
    floors = [g for g in scene.groups if isinstance(g.ext, dict) and g.ext.get("trazomob_floor")]
    ceilings = [g for g in scene.groups if isinstance(g.ext, dict) and g.ext.get("trazomob_ceiling")]
    walls = [g for g in scene.groups if isinstance(g.ext, dict) and g.ext.get("trazomob_wall")]

    # As 4 paredes do cÃ´modo sÃ£o criadas como grupos individuais seccionados
    assert len(walls) == 4
    assert len(floors) == 1
    assert len(ceilings) == 1

    # 2. UsuÃ¡rio clica em editar o mesmo ambiente ou reabre o diÃ¡logo para a mesma parede
    wall_grp = walls[0]
    scene.selection = {wall_grp}

    dlg2 = WallFloorplanDialog(vp)
    # Piso e teto existentes permanecem marcados ao reabrir a edição
    assert dlg2.chk_floor.isChecked() is True
    assert dlg2.chk_ceiling.isChecked() is True
    dlg2._build_3d_and_close()

    # O nÃºmero de pisos e tetos na cena NÃƒO deve ter dobrado para 2; deve continuar sendo 1!
    floors_after = [g for g in scene.groups if isinstance(g.ext, dict) and g.ext.get("trazomob_floor")]
    ceilings_after = [g for g in scene.groups if isinstance(g.ext, dict) and g.ext.get("trazomob_ceiling")]
    walls_after = [g for g in scene.groups if isinstance(g.ext, dict) and g.ext.get("trazomob_wall")]

    assert len(walls_after) == 4
    assert len(floors_after) == 1
    assert len(ceilings_after) == 1


def test_reference_image_persists_in_scene_and_reloads(tmp_path):
    """Garante que a imagem de referÃªncia Ã© salva no documento e restaurada ao reabrir o diÃ¡logo."""
    import os
    import sys
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QImage, QPixmap
    from core.scene import Scene
    from trazomob.wall.floorplan_dialog import WallFloorplanDialog
    app = QApplication.instance() or QApplication(sys.argv)

    # 1. Cria uma imagem temporÃ¡ria de teste
    img_path = str(tmp_path / "planta_teste.png")
    im = QImage(200, 150, QImage.Format_RGB32)
    im.fill(0xffffff)
    im.save(img_path, "PNG")

    scene = Scene()
    class DummyViewport:
        def __init__(self, sc):
            self.scene = sc
        def update(self):
            pass
        def flash_status(self, msg):
            pass

    vp = DummyViewport(scene)

    # 2. Abre o diÃ¡logo e carrega a imagem de referÃªncia
    dlg = WallFloorplanDialog(vp)
    ok = dlg.canvas.set_reference_image(img_path)
    assert ok is True
    assert dlg.canvas._ref_image_path == img_path

    # Ajusta opacidade e sincroniza com a cena
    dlg.slider_opac.setValue(70)
    dlg._sync_reference_image_to_scene()

    # Verifica se persistiu no plugin_data e em image_planes
    assert "trazomob_floorplan_ref" in scene.plugin_data
    assert scene.plugin_data["trazomob_floorplan_ref"]["path"] == img_path
    assert scene.plugin_data["trazomob_floorplan_ref"]["opacity"] == 0.7

    ref_planes = [im for im in scene.image_planes if getattr(im, "name", "") == "Planta Baixa Referencia (TrazoMob)"]
    assert len(ref_planes) == 1
    assert ref_planes[0].opacity == 0.7

    # 3. Fecha o diÃ¡logo simulando fechar a janela (closeEvent / reject)
    dlg.close()

    # 4. Ao abrir um novo diÃ¡logo no mesmo documento (mesma cena), a imagem deve ser automaticamente restaurada!
    dlg2 = WallFloorplanDialog(vp)
    assert dlg2.canvas._ref_pixmap is not None
    assert dlg2.canvas._ref_image_path == img_path
    assert round(dlg2.canvas._ref_opacity, 2) == 0.70
    assert dlg2.slider_opac.value() == 70
    assert dlg2.chk_ref_vis.isChecked() is True

    # 5. Se o usuÃ¡rio clicar em "âŒ Remover", a persistÃªncia Ã© limpa
    dlg2._on_remove_reference_image()
    assert dlg2.canvas._ref_pixmap is None
    assert "trazomob_floorplan_ref" not in scene.plugin_data
    ref_planes_after = [im for im in scene.image_planes if getattr(im, "name", "") == "Planta Baixa Referencia (TrazoMob)"]
    assert len(ref_planes_after) == 0


def test_escape_and_discard_changes_protection():
    """Garante que ESC cancela operaÃ§Ãµes em andamento primeiro, e solicita confirmaÃ§Ã£o antes de fechar com alteraÃ§Ãµes."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent
    from core.scene import Scene
    from trazomob.wall.floorplan_dialog import WallFloorplanDialog

    scene = Scene()
    class DummyViewport:
        def __init__(self, sc):
            self.scene = sc
        def update(self):
            pass
        def flash_status(self, msg):
            pass

    vp = DummyViewport(scene)
    dlg = WallFloorplanDialog(vp)

    # 1. Sem alteraÃ§Ãµes: has_unsaved_changes deve ser False
    assert dlg.has_unsaved_changes() is False

    # 2. Inicia o traÃ§o de uma parede (corda elÃ¡stica ativa)
    dlg.canvas._start_pt = (0.0, 0.0)
    dlg.canvas._type_buffer = "1500"

    # Pressiona ESC: deve cancelar apenas o traÃ§o e o buffer, sem fechar a janela
    esc_event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
    dlg.keyPressEvent(esc_event)

    assert dlg.canvas._start_pt is None
    assert dlg.canvas._type_buffer == ""
    assert dlg.isVisible() or not dlg.result()  # NÃ£o foi rejeitado / fechado

    # 3. Adiciona uma parede (alteraÃ§Ã£o real)
    dlg.graph.add_segment(0, 0, 3, 0)
    assert dlg.has_unsaved_changes() is True

    # 4. Testa interceptaÃ§Ã£o de confirmaÃ§Ã£o de descarte
    # Se o usuÃ¡rio clicar em "NÃ£o" (cancelar fechamento), rejeiÃ§Ã£o deve ser abortada
    dlg._confirm_discard_changes = lambda: False
    dlg.reject()
    assert dlg.result() == 0  # RejeiÃ§Ã£o ignorada

    # Se o usuÃ¡rio confirmar descarte ("Sim"), fecha normalmente
    dlg._confirm_discard_changes = lambda: True
    dlg.reject()


def test_dimension_by_face_or_center_mode():
    """Garante que a visualizaÃ§Ã£o de paredes e cotagem interativa funciona com a ferramenta Cotar."""
    from core.scene import Scene
    from trazomob.wall.floorplan_dialog import WallFloorplanDialog

    scene = Scene()
    class DummyViewport:
        def __init__(self, sc):
            self.scene = sc
        def update(self):
            pass
        def flash_status(self, msg):
            pass

    vp = DummyViewport(scene)
    dlg = WallFloorplanDialog(vp)

    # Cria cÃ´modo 4x3 com paredes de espessura 0.15m
    s1 = dlg.graph.add_segment(0, 0, 4, 0)
    s2 = dlg.graph.add_segment(4, 0, 4, 3)
    s3 = dlg.graph.add_segment(4, 3, 0, 3)
    s4 = dlg.graph.add_segment(0, 3, 0, 0)

    # Verifica ferramenta de cota
    dlg._set_mode("cota")
    assert dlg.canvas.mode == "cota"

    # Adiciona cota na face interna do vÃ£o (entre 0.075 e 3.925)
    d_id = dlg.graph.add_dimension((0.075, 0.075), (3.925, 0.075), seg_id=s1)
    assert d_id is not None
    assert round(dist_2d(dlg.graph.dimensions[d_id].p1, dlg.graph.dimensions[d_id].p2), 2) == 3.85


def test_dimension_logistics_click_wall_select_delete_and_undo():
    """Valida a logÃ­stica completa de cotas: clique direto na parede, seleÃ§Ã£o, exclusÃ£o com Delete e Undo."""
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtCore import Qt, QPointF
    from core.scene import Scene
    from trazomob.wall.floorplan_dialog import WallFloorplanDialog

    scene = Scene()
    class DummyViewport:
        def __init__(self, sc):
            self.scene = sc
        def update(self):
            pass
        def flash_status(self, msg):
            pass

    vp = DummyViewport(scene)
    dlg = WallFloorplanDialog(vp)

    # 1. Cria uma parede de (0, 0) a (5, 0)
    sid = dlg.graph.add_segment(0, 0, 5, 0)
    assert sid in dlg.graph.segments

    # 2. Ativa ferramenta cota
    dlg._set_mode("cota")
    assert dlg.canvas.mode == "cota"

    # Simula clique sobre a parede (ex: em x=2.5, y=0.0)
    # Deve cotar a linha inteira da parede automaticamente
    class DummyMouseEvent:
        def __init__(self, pos, btn=Qt.LeftButton, mods=Qt.NoModifier):
            self._pos = pos
            self._btn = btn
            self._mods = mods
        def position(self):
            return self._pos
        def button(self):
            return self._btn
        def modifiers(self):
            return self._mods

    # Converte ponto (2.5, 0.0) de mundo para screen
    sp = dlg.canvas.world_to_screen(2.5, 0.0)
    # Suprime diÃ¡logo modal para o teste
    dlg.canvas._edit_custom_dimension_dialog = lambda did: None
    dlg.canvas.mousePressEvent(DummyMouseEvent(sp))

    assert len(dlg.graph.dimensions) == 1
    dim_id = list(dlg.graph.dimensions.keys())[0]
    dim = dlg.graph.dimensions[dim_id]
    assert dim.seg_id == sid
    assert round(dist_2d(dim.p1, dim.p2), 2) == 5.0
    assert dlg.canvas._selected_dim_id == dim_id

    # 3. Pressiona Delete / Backspace para excluir a cota selecionada
    del_ev = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Delete, Qt.NoModifier)
    dlg.canvas.keyPressEvent(del_ev)

    assert len(dlg.graph.dimensions) == 0
    assert dlg.canvas._selected_dim_id is None

    # 4. Desfazer (Ctrl+Z): deve restaurar a cota excluÃ­da
    undo_ev = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Z, Qt.ControlModifier)
    dlg.canvas.keyPressEvent(undo_ev)

    assert len(dlg.graph.dimensions) == 1
    assert len(dlg.graph.segments) == 1


def test_independent_dimensions_multi_wall_no_opposite_overwrite():
    """Garante que alterar a cota de uma parede nÃ£o deforma a cota da parede oposta ou anterior."""
    g = WallGraph2D()
    s1 = g.add_segment(0, 0, 4, 0)
    s2 = g.add_segment(4, 0, 4, 3)
    s3 = g.add_segment(4, 3, 2, 3)

    # Cotando s3 (que era menor: 2m) para 5m:
    # Deve empurrar a ponta livre sem alterar nem deformar s1 e s2
    g.set_segment_length(s3, 5.0)
    assert round(g.segments[s1].length(g), 2) == 4.0
    assert round(g.segments[s2].length(g), 2) == 3.0
    assert round(g.segments[s3].length(g), 2) == 5.0

    # Agora cotando s1 para 6m:
    # Deve empurrar s2 e s3 em bloco, preservando seus comprimentos intactos
    g.set_segment_length(s1, 6.0)
    assert round(g.segments[s1].length(g), 2) == 6.0
    assert round(g.segments[s2].length(g), 2) == 3.0
    assert round(g.segments[s3].length(g), 2) == 5.0


def test_horizontal_wall_with_three_vertical_partitions_dimensioning():
    """Valida o cenÃ¡rio exato especificado pelo usuÃ¡rio:
    Parede horizontal com 3 divisÃ³rias verticais intermediÃ¡rias.
    Cotas:
    1. VÃ£o entre v1 e v2 = 1000 mm (1.0 m)
    2. VÃ£o central v2 e v3 = 1000 mm (1.0 m)
    3. Canto da parede atÃ© a primeira divisÃ³ria = 500 mm (0.5 m)
    Lado final nÃ£o cotado absorve o restante.
    As trÃªs cotas definidas devem ser estritamente respeitadas independentemente da ordem.
    """
    g = WallGraph2D()
    # Parede horizontal de 10m
    s_main = g.add_segment(0, 0, 10, 0)
    # 3 paredes verticais intermediÃ¡rias
    s_v1 = g.add_segment(2, 0, 2, 3)
    s_v2 = g.add_segment(4, 0, 4, 3)
    s_v3 = g.add_segment(7, 0, 7, 3)

    # Segmentos horizontais criados:
    # seg 1: canto atÃ© v1
    # seg 2: vÃ£o v1 a v2
    # seg 4: vÃ£o v2 a v3
    # seg 6: sobra final nÃ£o cotada

    # 1. Define vÃ£o v1 a v2 para 1.0 m (1000 mm)
    g.set_segment_length(2, 1.0)
    assert round(g.segments[2].length(g), 2) == 1.0

    # 2. Define vÃ£o v2 a v3 para 1.0 m (1000 mm)
    g.set_segment_length(4, 1.0)
    assert round(g.segments[4].length(g), 2) == 1.0

    # 3. Define canto inicial atÃ© v1 para 0.50 m (500 mm)
    g.set_segment_length(1, 0.50)
    assert round(g.segments[1].length(g), 2) == 0.50

    # ValidaÃ§Ã£o rigorosa: todas as 3 cotas estabelecidas estÃ£o 100% preservadas!
    assert round(g.segments[1].length(g), 3) == 0.500
    assert round(g.segments[2].length(g), 3) == 1.000
    assert round(g.segments[4].length(g), 3) == 1.000

    # As 3 paredes verticais foram empurradas em bloco mantendo seus comprimentos intactos (3.0 m)
    assert round(g.segments[3].length(g), 2) == 3.0
    assert round(g.segments[5].length(g), 2) == 3.0
    assert round(g.segments[7].length(g), 2) == 3.0

    # PosiÃ§Ãµes finais dos nÃ³s no eixo X:
    # Canto fixo inicial: x = 0.0
    # DivisÃ³ria 1: x = 0.5 (500 mm do canto)
    # DivisÃ³ria 2: x = 1.5 (1000 mm de v1)
    # DivisÃ³ria 3: x = 2.5 (1000 mm de v2)
    assert round(g.nodes[1].x, 2) == 0.0
    assert round(g.nodes[3].x, 2) == 0.5
    assert round(g.nodes[5].x, 2) == 1.5
    assert round(g.nodes[7].x, 2) == 2.5


def test_drag_node_and_dimension_keeps_entire_wall_and_perpendicular_together():
    """Valida que mover ou arrastar um ponto de uma parede cotada leva a parede inteira e as subsequentes juntas."""
    g = WallGraph2D()
    s1 = g.add_segment(0, 0, 4, 0)
    s2 = g.add_segment(4, 0, 4, 3)
    s3 = g.add_segment(4, 3, 2, 3)

    d1 = g.add_dimension((0, 0), (4, 0), seg_id=s1)
    d2 = g.add_dimension((4, 0), (4, 3), seg_id=s2)
    d3 = g.add_dimension((4, 3), (2, 3), seg_id=s3)

    # Pega no nÃ³ de baixo (nÃ³ 1) e move para cima em Y (dy = 1.0)
    g.move_node(1, 0.0, 1.0)

    # Tudo sobe junto:
    # A parede s1 continua horizontal com 4m
    assert round(g.segments[s1].length(g), 2) == 4.0
    # A parede s2 continua vertical com 3m
    assert round(g.segments[s2].length(g), 2) == 3.0
    # A parede s3 continua horizontal com 2m
    assert round(g.segments[s3].length(g), 2) == 2.0

    # Todas as cotas acompanharam exatamente a subida
    assert g.dimensions[d1].p1 == (0.0, 1.0)
    assert g.dimensions[d1].p2 == (4.0, 1.0)
    assert g.dimensions[d2].p1 == (4.0, 1.0)
    assert g.dimensions[d2].p2 == (4.0, 4.0)
    assert g.dimensions[d3].p1 == (4.0, 4.0)
    assert g.dimensions[d3].p2 == (2.0, 4.0)


def test_rigid_dimension_component_preserves_dimensions_and_drags_together():
    """Valida que uma cota é rígida e imutável:
    - Ao arrastar um ponto ou parede cotada, todo o componente cotado Ã© transladado junto.
    - O comprimento cotado NUNCA se altera com o arraste.
    - Apenas as sobras e paredes nÃ£o cotadas absorvem a deformaÃ§Ã£o.
    """
    g = WallGraph2D()
    # Parede horizontal de 10m
    s_main = g.add_segment(0, 0, 10, 0)
    # DivisÃ³rias verticais
    s_v1 = g.add_segment(2, 0, 2, 3)
    s_v2 = g.add_segment(4, 0, 4, 3)
    s_v3 = g.add_segment(7, 0, 7, 3)

    # Aplica cotas de 1.0m nos vÃ£os
    g.set_segment_length(2, 1.0) # VÃ£o v1-v2 = 1.0m
    g.set_segment_length(4, 1.0) # VÃ£o v2-v3 = 1.0m
    g.set_segment_length(1, 0.5) # Canto - v1 = 0.5m

    # Registra cotas explÃ­citas nos vÃ£os
    d1 = g.add_dimension((0, 0), (0.5, 0), seg_id=1)
    d2 = g.add_dimension((0.5, 0), (1.5, 0), seg_id=2)
    d3 = g.add_dimension((1.5, 0), (2.5, 0), seg_id=4)

    # Identifica o nÃ³ da base da divisÃ³ria v2 (node_id 5, em x=1.5, y=0.0)
    # e move-o para a direita em X (+0.3m, novo x=1.8m)
    # Como as cotas sÃ£o rÃ­gidas e imutÃ¡veis, o bloco todo (canto inicial, v1, v2, v3) se desloca junto,
    # mantendo as medidas exatas de 0.5m, 1.0m e 1.0m inalteradas!
    g.move_node(5, 1.8, 0.0)

    # As 3 cotas continuam rigorosamente idÃªnticas (imutÃ¡veis)
    assert round(g.segments[1].length(g), 3) == 0.500
    assert round(g.segments[2].length(g), 3) == 1.000
    assert round(g.segments[4].length(g), 3) == 1.000

    # As paredes verticais continuam perpendiculares e intactas com 3.0m
    assert round(g.segments[3].length(g), 2) == 3.0
    assert round(g.segments[5].length(g), 2) == 3.0
    assert round(g.segments[7].length(g), 2) == 3.0

    # As novas posiÃ§Ãµes transladadas em +0.3m:
    assert round(g.nodes[1].x, 2) == 0.3
    assert round(g.nodes[3].x, 2) == 0.8
    assert round(g.nodes[5].x, 2) == 1.8
    assert round(g.nodes[7].x, 2) == 2.8


def test_cad_sequential_dimension_editing_and_synchronization():
    """Valida o caso real de CAD com ediÃ§Ã£o sequencial de cotas:
    - 3 divisÃ³rias em parede horizontal.
    - Cotas em todos os 3 vÃ£os.
    - Edita a Ãºltima cota: apenas a Ãºltima cota e o que estÃ¡ Ã  frente se ajustam.
    - Edita a segunda cota: a terceira cota translada junto em bloco e seu valor permanece 100% imutÃ¡vel.
    - Edita a primeira cota: todas as outras duas cotas transladam juntas em bloco e permanecem 100% imutÃ¡veis.
    """
    g = WallGraph2D()
    s_main = g.add_segment(0, 0, 10, 0)
    s_v1 = g.add_segment(2, 0, 2, 3)
    s_v2 = g.add_segment(4, 0, 4, 3)
    s_v3 = g.add_segment(7, 0, 7, 3)

    # Cria cotas nos 3 vÃ£os
    d1 = g.add_dimension((0, 0), (2, 0), seg_id=1)
    d2 = g.add_dimension((2, 0), (4, 0), seg_id=2)
    d3 = g.add_dimension((4, 0), (7, 0), seg_id=4)

    # 1. Edita d3 (vÃ£o v2-v3) para 1000 mm (1.0m)
    g.set_segment_length(4, 1.0)
    assert round(dist_2d(g.dimensions[d3].p1, g.dimensions[d3].p2), 2) == 1.00
    assert round(dist_2d(g.dimensions[d2].p1, g.dimensions[d2].p2), 2) == 2.00
    assert round(dist_2d(g.dimensions[d1].p1, g.dimensions[d1].p2), 2) == 2.00

    # 2. Edita d2 (vÃ£o v1-v2) para 1000 mm (1.0m)
    g.set_segment_length(2, 1.0)
    # d3 foi empurrada junto com v2 e manteve seus 1.0m exatos (imutÃ¡vel!)
    assert round(dist_2d(g.dimensions[d3].p1, g.dimensions[d3].p2), 2) == 1.00
    assert round(dist_2d(g.dimensions[d2].p1, g.dimensions[d2].p2), 2) == 1.00
    assert round(dist_2d(g.dimensions[d1].p1, g.dimensions[d1].p2), 2) == 2.00

    # 3. Edita d1 (canto atÃ© v1) para 500 mm (0.5m)
    g.set_segment_length(1, 0.5)
    # Tanto d2 quanto d3 foram empurradas em bloco e continuam com 1.0m exatos (imutÃ¡veis!)
    assert round(dist_2d(g.dimensions[d1].p1, g.dimensions[d1].p2), 2) == 0.50
    assert round(dist_2d(g.dimensions[d2].p1, g.dimensions[d2].p2), 2) == 1.00
    assert round(dist_2d(g.dimensions[d3].p1, g.dimensions[d3].p2), 2) == 1.00

    # Paredes verticais mantÃªm altura de 3m e Ã¢ngulos retos perfeitos
    assert round(g.segments[3].length(g), 2) == 3.00
    assert round(g.segments[5].length(g), 2) == 3.00
    assert round(g.segments[7].length(g), 2) == 3.00


def test_system_refuses_overconstrained_push_and_preserves_geometry():
    """Editar uma cota de um cômodo sobre-restrito deve ser recusado sem distorcer nada.

    Antes, o sistema empurrava apenas um nó por vez e gerava diagonais. Agora a
    edição é simulada em uma cópia do grafo; se ela entortar uma parede ou alterar
    outra cota driving, a operação é recusada integralmente.
    """
    g = WallGraph2D()
    s1 = g.add_segment(0, 0, 4, 0)
    s2 = g.add_segment(4, 0, 4, 3)
    s3 = g.add_segment(4, 3, 0, 3)
    s4 = g.add_segment(0, 3, 0, 0)
    g.merge_close_nodes()

    d1 = g.add_dimension((0, 0), (4, 0), seg_id=s1)
    d2 = g.add_dimension((4, 0), (4, 3), seg_id=s2)
    d3 = g.add_dimension((4, 3), (0, 3), seg_id=s3)

    before = {
        sid: (round(g.segments[sid].length(g), 3),
              g.segments[sid].node_a_id, g.segments[sid].node_b_id)
        for sid in g.segments
    }
    before_nodes = {nid: (n.x, n.y) for nid, n in g.nodes.items()}

    assert g.check_length_edit(s1, 5.0) is not None
    assert g.set_segment_length(s1, 5.0) is False

    # Nada mudou: nós, segmentos e cotas permanecem idênticos.
    assert {nid: (n.x, n.y) for nid, n in g.nodes.items()} == before_nodes
    assert {
        sid: (round(g.segments[sid].length(g), 3),
              g.segments[sid].node_a_id, g.segments[sid].node_b_id)
        for sid in g.segments
    } == before
    assert round(dist_2d(g.dimensions[d1].p1, g.dimensions[d1].p2), 2) == 4.0
    assert round(dist_2d(g.dimensions[d2].p1, g.dimensions[d2].p2), 2) == 3.0
    assert round(dist_2d(g.dimensions[d3].p1, g.dimensions[d3].p2), 2) == 4.0


def test_annotation_dimensions_do_not_constrain_geometry():
    """Cotas de anotação (driving=False) acompanham a parede e nunca bloqueiam edições."""
    g = WallGraph2D()
    s1 = g.add_segment(0, 0, 4, 0)
    s2 = g.add_segment(4, 0, 4, 3)
    s3 = g.add_segment(4, 3, 0, 3)
    s4 = g.add_segment(0, 3, 0, 0)
    g.merge_close_nodes()

    d1 = g.add_dimension((0, 0), (4, 0), seg_id=s1, driving=False)
    d2 = g.add_dimension((4, 0), (4, 3), seg_id=s2, driving=False)
    assert g.dimensions[d1].driving is False
    assert g.dimensions[d2].driving is False

    # Sem restrições driving, esticar a base preserva a ortogonalidade da cadeia.
    assert g.check_length_edit(s1, 5.0) is None
    assert g.set_segment_length(s1, 5.0) is True
    assert round(g.segments[s1].length(g), 3) == 5.0

    # Nenhuma parede virou diagonal.
    assert round(g.segments[s2].length(g), 3) == 3.0
    assert round(g.segments[s3].length(g), 3) == 5.0
    assert round(g.segments[s4].length(g), 3) == 3.0

    # A cota de anotação acompanha a nova geometria.
    assert round(dist_2d(g.dimensions[d1].p1, g.dimensions[d1].p2), 3) == 5.0


def test_partial_dimension_keeps_stable_inner_distance():
    """Cota interna de parede guarda (seg_id, distância) e não colapsa em um único nó."""
    g = WallGraph2D()
    s1 = g.add_segment(0, 0, 10, 0)
    did = g.add_dimension((0, 0), (4, 0), seg_id=s1)
    d = g.dimensions[did]
    assert d.node_a_id != d.node_b_id or d.node_b_id is None
    assert d.b_seg_id == s1 and d.b_end is None
    assert round(d.b_dist, 3) == 4.0

    # Ao esticar a parede, a ponta interna permanece a 4 m do início.
    assert g.set_segment_length(s1, 12.0) is True
    assert round(dist_2d(d.p1, d.p2), 3) == 4.0
    assert round(d.b_dist, 3) == 4.0


def test_free_dimension_stays_free_after_moving():
    """Cota no vazio nunca é associada implicitamente a nós próximos."""
    g = WallGraph2D()
    s1 = g.add_segment(0, 0, 4, 0)
    s2 = g.add_segment(4, 0, 4, 3)
    s3 = g.add_segment(4, 3, 0, 3)
    s4 = g.add_segment(0, 3, 0, 0)
    g.merge_close_nodes()

    did = g.add_dimension((1.0, 1.0), (3.0, 1.0), driving=False)
    d = g.dimensions[did]
    assert d.node_a_id is None and d.node_b_id is None
    assert d.a_seg_id is None and d.b_seg_id is None

    g.move_node(s1, 0.5, 0.0)
    g.sync_all_dimensions()

    assert d.node_a_id is None and d.node_b_id is None
    assert d.p1 == (1.0, 1.0) and d.p2 == (3.0, 1.0)


def _two_rooms_with_t_partition():
    g = WallGraph2D()
    s_bl = g.add_segment(0, 0, 5, 0)
    s_br = g.add_segment(5, 0, 10, 0)
    s_r = g.add_segment(10, 0, 10, 6)
    s_tr = g.add_segment(10, 6, 5, 6)
    s_tl = g.add_segment(5, 6, 0, 6)
    s_l = g.add_segment(0, 6, 0, 0)
    s_p = g.add_segment(5, 0, 5, 6)
    g.merge_close_nodes()
    return g, s_bl, s_br, s_r, s_tr, s_tl, s_l, s_p


def test_overconstrained_t_partition_edit_refused_without_distortion():
    """Editar uma cota de cômodo com T-junction não pode criar diagonais nem perder a junção."""
    g, s_bl, s_br, s_r, s_tr, s_tl, s_l, s_p = _two_rooms_with_t_partition()
    d1 = g.add_dimension((0, 0), (5, 0), seg_id=s_bl)
    d2 = g.add_dimension((5, 0), (10, 0), seg_id=s_br)
    d3 = g.add_dimension((5, 0), (5, 6), seg_id=s_p)
    # Cota total + cotas parciais = super-restrição clássica.
    d4 = g.add_dimension((0, 0), (10, 0), seg_id=s_br)
    assert round(dist_2d(g.dimensions[d4].p1, g.dimensions[d4].p2), 3) == 10.0

    nodes_before = {nid: (n.x, n.y) for nid, n in g.nodes.items()}
    segs_before = {sid: (s.node_a_id, s.node_b_id) for sid, s in g.segments.items()}

    assert g.check_length_edit(s_bl, 7.0) is not None
    assert g.set_segment_length(s_bl, 7.0) is False

    # Geometria intacta e sem diagonais.
    assert {nid: (n.x, n.y) for nid, n in g.nodes.items()} == nodes_before
    assert {sid: (s.node_a_id, s.node_b_id) for sid, s in g.segments.items()} == segs_before
    assert round(dist_2d(g.dimensions[d1].p1, g.dimensions[d1].p2), 3) == 5.0
    assert round(dist_2d(g.dimensions[d2].p1, g.dimensions[d2].p2), 3) == 5.0
    assert round(dist_2d(g.dimensions[d3].p1, g.dimensions[d3].p2), 3) == 6.0
    assert round(dist_2d(g.dimensions[d4].p1, g.dimensions[d4].p2), 3) == 10.0


def test_annotation_t_partition_edit_preserves_orthogonality_and_t():
    """Sem cotas driving conflitantes, esticar um lado move o T inteiro e mantém 90°."""
    g, s_bl, s_br, s_r, s_tr, s_tl, s_l, s_p = _two_rooms_with_t_partition()
    d1 = g.add_dimension((0, 0), (5, 0), seg_id=s_bl)
    d2 = g.add_dimension((5, 0), (10, 0), seg_id=s_br, driving=False)

    assert g.check_length_edit(s_bl, 7.0) is None
    assert g.set_segment_length(s_bl, 7.0) is True

    assert round(g.segments[s_bl].length(g), 3) == 7.0
    assert round(g.segments[s_br].length(g), 3) == 3.0
    assert round(g.segments[s_p].length(g), 3) == 6.0
    assert round(g.segments[s_l].length(g), 3) == 6.0

    # A divisória continua vertical (sem diagonal) e conectada ao topo.
    p = g.segments[s_p]
    na, nb = g.nodes[p.node_a_id], g.nodes[p.node_b_id]
    assert abs(na.x - nb.x) < 1e-9
    assert abs(na.y - 0.0) < 1e-9 and abs(nb.y - 6.0) < 1e-9

    # O T superior acompanhou o inferior e continua conectado às duas paredes do topo.
    tl = g.segments[s_tl]
    tr = g.segments[s_tr]
    assert nb.id in (tl.node_a_id, tl.node_b_id)
    assert nb.id in (tr.node_a_id, tr.node_b_id)
    assert abs(nb.x - 7.0) < 1e-9

    assert round(dist_2d(g.dimensions[d1].p1, g.dimensions[d1].p2), 3) == 7.0
    assert round(dist_2d(g.dimensions[d2].p1, g.dimensions[d2].p2), 3) == 3.0













def test_partition_room_preserves_all_walls_and_subdivides():
    """Garante que ao dividir um cômodo com uma parede divisória, nenhuma parede anterior
    some e todos os segmentos resultantes (incluindo as paredes subdivididas e a divisória)
    permanecem na cena 3D como sólidos estanques.
    """
    from trazomob.wall.floorplan_dialog import WallFloorplanDialog
    scene = Scene()
    class DummyViewport:
        def __init__(self, sc): self.scene = sc
        def update(self): pass
        def flash_status(self, msg): pass
    vp = DummyViewport(scene)

    # 1. Cria cÃ´modo 4x3m inicial (4 paredes)
    dlg1 = WallFloorplanDialog(vp)
    dlg1.graph.add_segment(0, 0, 4, 0)
    dlg1.graph.add_segment(4, 0, 4, 3)
    dlg1.graph.add_segment(4, 3, 0, 3)
    dlg1.graph.add_segment(0, 3, 0, 0)
    dlg1._build_3d_and_close()

    walls_initial = [g for g in scene.groups if isinstance(getattr(g, "ext", None), dict) and g.ext.get("trazomob_wall")]
    assert len(walls_initial) == 4

    # 2. Reabre e divide o cÃ´modo com uma nova parede divisÃ³ria no meio de (2, 0) a (2, 3)
    dlg2 = WallFloorplanDialog(vp)
    dlg2.graph.add_segment(2.0, 0.0, 2.0, 3.0)
    dlg2.graph.merge_close_nodes(threshold=0.25)
    dlg2._build_3d_and_close()

    walls_after = [g for g in scene.groups if isinstance(getattr(g, "ext", None), dict) and g.ext.get("trazomob_wall")]
    wall_segs = [g for g in walls_after if not g.ext["trazomob_wall"].get("is_column")]
    wall_cols = [g for g in walls_after if g.ext["trazomob_wall"].get("is_column")]

    # O cômodo de 4 paredes cortado ao meio deve gerar exatamente 7 segmentos de paredes:
    # 2 segmentos na parede sul dividida + 2 segmentos na parede norte dividida +
    # 2 paredes laterais (leste e oeste) + 1 parede divisória central = 7 paredes
    # + 2 colunas estruturais nas junções em T = 9 grupos no total
    assert len(wall_segs) == 7
    assert len(wall_cols) == 2
    assert len(walls_after) == 9

    # Todas as paredes e colunas devem ser sólidas estanques com normais apontando para fora
    for w in walls_after:
        assert len(w.mesh.faces) == 6
        assert not getattr(w, "hidden", False)
        # Verifica orientação das normais (outward winding): dot(normal, face_center - mesh_center) > 0
        verts_all = [v.position for v in w.mesh.vertices]
        cx = sum(p.x() for p in verts_all) / len(verts_all)
        cy = sum(p.y() for p in verts_all) / len(verts_all)
        cz = sum(p.z() for p in verts_all) / len(verts_all)
        from PySide6.QtGui import QVector3D
        mesh_center = QVector3D(cx, cy, cz)
        for f in w.mesh.faces:
            f_pts = f.vertices
            fc = QVector3D(
                sum(p.x() for p in f_pts) / len(f_pts),
                sum(p.y() for p in f_pts) / len(f_pts),
                sum(p.z() for p in f_pts) / len(f_pts),
            )
            assert QVector3D.dotProduct(f.normal(), fc - mesh_center) > 0, f"Face invertida em {w.name}"


def test_custom_dimensions_persist_after_build_3d_and_reopen_dialog():
    """Garante que cotas estipuladas no plano 2D persistem após clicar em Concluir (gerar paredes 3D)
    e clicar novamente no botão de Construir Paredes para reabrir o plano 2D.
    """
    from trazomob.wall.floorplan_dialog import WallFloorplanDialog
    scene = Scene()
    class DummyViewport:
        def __init__(self, sc): self.scene = sc
        def update(self): pass
        def flash_status(self, msg): pass
    vp = DummyViewport(scene)

    # 1. Abre o diálogo 2D, cria paredes e estipula uma cota
    dlg1 = WallFloorplanDialog(vp)
    s1 = dlg1.graph.add_segment(0.0, 0.0, 4.0, 0.0)
    s2 = dlg1.graph.add_segment(4.0, 0.0, 4.0, 3.0)
    dim_id = dlg1.graph.add_dimension((0.0, 0.0), (4.0, 0.0), seg_id=s1)
    assert dim_id is not None
    dlg1.graph.set_segment_length(s1, 4.50)

    # 2. Clica em Concluir (gera paredes no 3D e fecha)
    dlg1._build_3d_and_close()

    # 3. Clica novamente no botão de paredes logo em seguida (reabre WallFloorplanDialog)
    dlg2 = WallFloorplanDialog(vp)

    # A cota estipulada deve estar presente, visível e com o valor atualizado!
    assert len(dlg2.graph.dimensions) == 1
    restored_dim = dlg2.graph.dimensions[dim_id]
    assert round(dist_2d(restored_dim.p1, restored_dim.p2), 2) == 4.50
    assert restored_dim.seg_id == s1
    assert restored_dim.node_a_id is not None
    assert restored_dim.node_b_id is not None



def test_all_cabinet_modules_pass_solid_inspector():
    """Garante que todas as peças geradas pelo CabinetBuilder (incluindo laterais com furação,
    travessas em pé/deitadas, portas com dobradiças e puxadores alça/perfil/cava/ponto,
    cubas e torneiras) são sólidos 100% estanques (watertight) e sem faces invertidas no Solid Inspector.
    """
    from trazomob.builders.cabinet import CabinetBuilder
    from plugins.solid_inspector import inspect_mesh, is_sound, _problem_text

    module_configs = [
        {"tipo": "balcao", "largura": 800, "altura": 720, "profundidade": 550},
        {"tipo": "balcao", "largura": 800, "altura": 720, "profundidade": 550, "travessa_frontal_em_pe": True, "travessa_traseira_em_pe": True},
        {"tipo": "balcao", "largura": 800, "altura": 720, "profundidade": 550, "puxador_tipo": "perfil", "perfil_modelo": "gola"},
        {"tipo": "balcao", "largura": 800, "altura": 720, "profundidade": 550, "puxador_tipo": "cava"},
        {"tipo": "balcao", "largura": 800, "altura": 720, "profundidade": 550, "puxador_tipo": "ponto"},
        {"tipo": "gaveteiro", "largura": 600, "altura": 720, "profundidade": 550},
        {"tipo": "aereo", "largura": 800, "altura": 700, "profundidade": 350},
        {"tipo": "torre_quente", "largura": 700, "altura": 2200, "profundidade": 600},
        {"tipo": "roupeiro", "largura": 1600, "altura": 2300, "profundidade": 580},
        {"tipo": "canto_l", "largura": 900, "altura": 720, "profundidade": 550, "largura_ala": 900},
        {"tipo": "bancada_pia", "largura": 1200, "altura": 880, "profundidade": 600},
    ]

    for params in module_configs:
        grp = CabinetBuilder.build_module_group(params)
        for child in grp.children:
            if not child.mesh.faces and not child.mesh.edges:
                continue
            rep = inspect_mesh(child.mesh)
            assert is_sound(rep), f"Peça '{child.name}' ({params['tipo']}) falhou no Solid Inspector: {_problem_text(rep)}"


def test_sidebar_config_tabs_organization():
    """Garante que o painel lateral organiza as 5 categorias de configuração em abas (QTabWidget)
    e alterna dinamicamente a visibilidade das abas conforme o tipo de módulo carregado.
    """
    import sys
    from PySide6.QtWidgets import QApplication, QTabWidget
    from core.scene import Scene
    from trazomob.ui.sidebar_panel import TrazoMobSidebarPanel
    from trazomob.builders.cabinet import CabinetBuilder

    _app = QApplication.instance() or QApplication(sys.argv)
    scene = Scene()

    class DummyViewport:
        def __init__(self, sc):
            self.scene = sc
        def update(self):
            pass
        def flash_status(self, msg):
            pass

    class DummyApp:
        def __init__(self, vp):
            self.viewport = vp

    vp = DummyViewport(scene)
    panel = TrazoMobSidebarPanel(DummyApp(vp))

    # 1. Carrega um balcão tradicional: todas as 5 abas devem existir e estar visíveis
    mod_balcao = CabinetBuilder.build_module_group({"tipo": "balcao", "largura": 800, "altura": 720, "profundidade": 550})
    scene.groups.append(mod_balcao)
    panel.load_module(mod_balcao)

    assert hasattr(panel, "tabs_module")
    assert isinstance(panel.tabs_module, QTabWidget)
    assert panel.tabs_module.count() == 5
    for idx in range(5):
        assert panel.tabs_module.isTabVisible(idx) is True

    # 2. Carrega uma bancada de pedra: Frentes (1) e Puxadores (2) ficam ocultas
    mod_pia = CabinetBuilder.build_module_group({"tipo": "bancada_pia", "largura": 1200, "altura": 880, "profundidade": 600})
    scene.groups.append(mod_pia)
    panel.load_module(mod_pia)

    assert panel.tabs_module.isTabVisible(0) is True   # Medidas
    assert panel.tabs_module.isTabVisible(1) is False  # Estrutura
    assert panel.tabs_module.isTabVisible(2) is False  # Puxadores
    assert panel.tabs_module.isTabVisible(3) is True   # Materiais
    assert panel.tabs_module.isTabVisible(4) is True   # Avançado

    # 3. Volta para o balcão tradicional: todas as 5 abas voltam a ficar visíveis
    panel.load_module(mod_balcao)
    for idx in range(5):
        assert panel.tabs_module.isTabVisible(idx) is True


def test_balcao_misto_lado_gaveteiro():
    """Garante que o Balcão Misto permite escolher o lado do gaveteiro (esquerda ou direita),
    posicionando corretamente as frentes de gaveta, portas, divisória e prateleiras.
    """
    from trazomob.builders.cabinet import CabinetBuilder
    from plugins.solid_inspector import inspect_mesh, is_sound

    # 1. Gaveteiro à esquerda (padrão)
    grp_esq = CabinetBuilder.build_module_group({
        "tipo": "balcao_misto",
        "largura": 1200, "altura": 720, "profundidade": 550,
        "largura_gaveteiro": 450,
        "lado_gaveteiro": "esquerda",
    })
    gav_esq = next(c for c in grp_esq.children if "Gaveteiro - Frente 1" in c.name)
    porta_esq_1 = next(c for c in grp_esq.children if "Porta Esq" in c.name)
    xs_gav_esq = [v.position.x() for v in gav_esq.mesh.vertices]
    xs_porta_1 = [v.position.x() for v in porta_esq_1.mesh.vertices]
    assert max(xs_gav_esq) < min(xs_porta_1)

    # 2. Gaveteiro à direita
    grp_dir = CabinetBuilder.build_module_group({
        "tipo": "balcao_misto",
        "largura": 1200, "altura": 720, "profundidade": 550,
        "largura_gaveteiro": 450,
        "lado_gaveteiro": "direita",
    })
    gav_dir = next(c for c in grp_dir.children if "Gaveteiro - Frente 1" in c.name)
    porta_dir_1 = next(c for c in grp_dir.children if "Porta Esq" in c.name)
    xs_gav_dir = [v.position.x() for v in gav_dir.mesh.vertices]
    xs_porta_2 = [v.position.x() for v in porta_dir_1.mesh.vertices]
    assert min(xs_gav_dir) > max(xs_porta_2)

    # Verifica que todas as peças do balcão misto com gaveta à direita passam no Solid Inspector
    for child in grp_dir.children:
        if child.mesh.faces or child.mesh.edges:
            assert is_sound(inspect_mesh(child.mesh))


def test_wall_floorplan_reconciles_position_after_3d_move():
    """Garante que quando paredes são criadas no 2D, geradas no 3D e depois movidas na cena 3D
    (via MoveGroupCommand nos vértices ou via xform), ao reabrir o editor 2D elas aparecem
    exatamente na nova posição do plano cartesiano onde foram deixadas na cena.
    """
    import sys
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QVector3D
    from core.scene import Scene
    from core.history import MoveGroupCommand
    from trazomob.wall.floorplan_dialog import WallFloorplanDialog
    from trazomob.wall.plan_2d import dist_2d

    _app = QApplication.instance() or QApplication(sys.argv)
    scene = Scene()

    class DummyViewport:
        def __init__(self, sc):
            self.scene = sc
        def update(self):
            pass
        def flash_status(self, msg):
            pass

    vp = DummyViewport(scene)

    # 1. Cria duas paredes em L partindo de (0, 0) -> (4, 0) -> (4, 3) com cota
    dlg1 = WallFloorplanDialog(vp)
    s1 = dlg1.graph.add_segment(0.0, 0.0, 4.0, 0.0)
    s2 = dlg1.graph.add_segment(4.0, 0.0, 4.0, 3.0)
    dim_id = dlg1.graph.add_dimension((0.0, 0.0), (4.0, 0.0), seg_id=s1)
    dlg1._build_3d_and_close()

    # 2. Move todas as paredes geradas na cena 3D em +5.0m no eixo X e +2.5m no eixo Y
    delta = QVector3D(5.0, 2.5, 0.0)
    for g in scene.groups:
        if isinstance(getattr(g, "ext", None), dict) and "trazomob_wall" in g.ext:
            MoveGroupCommand(g, delta).do(scene)

    # 3. Reabre o editor 2D: os nós e cotas devem estar nas novas coordenadas do plano cartesiano!
    dlg2 = WallFloorplanDialog(vp)
    pts = sorted((round(n.x, 2), round(n.y, 2)) for n in dlg2.graph.nodes.values())
    assert pts == [(5.0, 2.5), (9.0, 2.5), (9.0, 5.5)]

    # E a cota deve ter acompanhado para (5.0, 2.5) -> (9.0, 2.5) mantendo 4.0m
    d = dlg2.graph.dimensions[dim_id]
    assert (round(d.p1[0], 2), round(d.p1[1], 2)) == (5.0, 2.5)
    assert (round(d.p2[0], 2), round(d.p2[1], 2)) == (9.0, 2.5)
    assert round(dist_2d(d.p1, d.p2), 2) == 4.0


def test_undo_preserves_individual_wall_height():
    """Undo deve restaurar a altura individual de cada parede, não só a geometria."""
    from core.scene import Scene
    from trazomob.wall.floorplan_dialog import WallFloorplanDialog

    scene = Scene()

    class DummyViewport:
        def __init__(self, sc):
            self.scene = sc
        def update(self):
            pass
        def flash_status(self, msg):
            pass

    dlg = WallFloorplanDialog(DummyViewport(scene))
    dlg.graph.add_segment(0.0, 0.0, 4.0, 0.0, height=2.35)
    dlg.canvas._save_history()

    dlg.graph.clear()
    assert not dlg.graph.segments

    assert dlg.canvas.undo() is True
    restored = next(iter(dlg.graph.segments.values()))
    assert restored.height is not None
    assert abs(restored.height - 2.35) < 1e-9


def test_add_segment_accepts_individual_height():
    """add_segment deve permitir definir a altura individual da parede."""
    graph = WallGraph2D(default_thickness=0.15, default_height=2.60)
    sid = graph.add_segment(0.0, 0.0, 3.0, 0.0, height=2.10)
    assert sid is not None
    assert abs(graph.segments[sid].height - 2.10) < 1e-9


def test_wall_split_preserves_individual_height():
    """Ao subdividir uma parede (junção em T), os dois trechos mantêm a altura individual."""
    graph = WallGraph2D(default_thickness=0.15, default_height=2.60)
    graph.add_segment(0.0, 0.0, 5.0, 0.0, height=2.20)
    graph.add_segment(2.5, 0.0, 2.5, 3.0)

    heights = [seg.height for seg in graph.segments.values() if seg.height is not None]
    assert len(heights) == 2
    assert all(abs(h - 2.20) < 1e-9 for h in heights)


def test_reconcile_ignores_asymmetric_opening_vertices():
    """Vãos assimétricos adicionam vértices à malha; o reconcile não pode usar a
    média desses vértices como centro, senão inclina as paredes vizinhas."""
    from math import atan2, degrees
    from PySide6.QtGui import QVector3D
    from core.scene import Scene
    from trazomob.wall.builder import WallBuilderTool
    from trazomob.wall.plan_2d import WallGraph2D

    scene = Scene()
    graph = WallGraph2D(default_thickness=0.15, default_height=2.60)
    graph.add_segment(0.0, 0.0, 4.0, 0.0)
    graph.add_segment(4.0, 0.0, 4.0, 3.0)
    graph.add_segment(4.0, 3.0, 0.0, 3.0)
    graph.add_segment(0.0, 3.0, 0.0, 0.0)

    wall_grp = graph.build_3d_group(scene, altura_m=2.6, name="Sala")
    subs = WallBuilderTool.split_wall_group_into_segments(wall_grp)

    # Simula o vão de uma porta recortado assimetricamente na parede #1.
    seg1 = next(s for s in subs if s.ext["trazomob_wall"].get("segment_id") == 1)
    for x in (0.5, 1.0, 1.1, 1.6):
        seg1.mesh.add_face([
            QVector3D(x, -0.075, 0.0),
            QVector3D(x, -0.075, 2.6),
            QVector3D(x + 0.05, -0.075, 2.6),
            QVector3D(x + 0.05, -0.075, 0.0),
        ])

    restored = WallGraph2D.from_dict(wall_grp.ext["trazomob_wall"]["graph_2d"])
    restored.reconcile_with_3d_groups(subs)

    # O quarto permanece quadrado: todos os ângulos continuam múltiplos de 90°.
    for seg in restored.segments.values():
        na = restored.nodes[seg.node_a_id]
        nb = restored.nodes[seg.node_b_id]
        ang = degrees(atan2(nb.y - na.y, nb.x - na.x))
        assert abs(ang / 90.0 - round(ang / 90.0)) < 1e-6
        assert abs(nb.x - na.x) < 1e-6 or abs(nb.y - na.y) < 1e-6


def test_calibrate_ref_two_clicks_invokes_prompt():
    """O modo calibrar_ref deve coletar dois cliques e chamar a calibração de escala."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPixmap
    from core.scene import Scene
    from trazomob.wall.floorplan_dialog import WallFloorplanDialog

    scene = Scene()

    class DummyViewport:
        def __init__(self, sc):
            self.scene = sc
        def update(self):
            pass
        def flash_status(self, msg):
            pass

    class DummyMouseEvent:
        def __init__(self, pos, btn=Qt.LeftButton, mods=Qt.NoModifier):
            self._pos = pos
            self._btn = btn
            self._mods = mods
        def position(self):
            return self._pos
        def button(self):
            return self._btn
        def modifiers(self):
            return self._mods

    dlg = WallFloorplanDialog(DummyViewport(scene))
    dlg.canvas.mode = "calibrar_ref"
    dlg.canvas._ref_pixmap = QPixmap(10, 10)

    medidas = []
    dlg.canvas._prompt_calibrate_scale = lambda dist: medidas.append(dist)

    p1 = dlg.canvas.world_to_screen(0.0, 0.0)
    p2 = dlg.canvas.world_to_screen(2.0, 0.0)

    dlg.canvas.mousePressEvent(DummyMouseEvent(p1))
    assert len(dlg.canvas._calib_points) == 1
    assert dlg.canvas.mode == "calibrar_ref"

    dlg.canvas.mousePressEvent(DummyMouseEvent(p2))
    assert dlg.canvas._calib_points == []
    assert len(medidas) == 1
    assert abs(medidas[0] - 2.0) < 1e-6
    assert dlg.canvas.mode == "linha"


def test_wall_set_segment_length_with_anchor_node():
    """Testa a alteração de medida indicando explicitamente qual nó deve ficar fixo (âncora)."""
    graph = WallGraph2D()
    # Cria uma cadeia de 3 paredes formando uma baioneta/diagonal:
    # Parede 1: (0, 1) -> (0, 2)
    # Parede 2: (0, 2) -> (1, 1)
    # Parede 3: (1, 1) -> (1, 0)
    s1 = graph.add_segment(0.0, 1.0, 0.0, 2.0)
    s2 = graph.add_segment(0.0, 2.0, 1.0, 1.0)
    s3 = graph.add_segment(1.0, 1.0, 1.0, 0.0)

    seg2 = graph.segments[s2]
    # Identifica o nó no topo (0, 2) e na base (1, 1)
    nid_topo = seg2.node_a_id if (graph.nodes[seg2.node_a_id].x, graph.nodes[seg2.node_a_id].y) == (0.0, 2.0) else seg2.node_b_id
    nid_baixo = seg2.node_b_id if nid_topo == seg2.node_a_id else seg2.node_a_id

    # 1. Altera o comprimento de s2 fixando o topo (0, 2):
    # s1 deve permanecer intacta em (0,1) -> (0,2), e o nó inferior e s3 devem ser empurrados
    graph.set_segment_length(s2, 2.0, anchor_node_id=nid_topo)
    seg1 = graph.segments[s1]
    na1, nb1 = graph.nodes[seg1.node_a_id], graph.nodes[seg1.node_b_id]
    # Posições de s1 inalteradas
    assert abs(na1.x - 0.0) < 1e-4 and abs(na1.y - 1.0) < 1e-4
    assert abs(nb1.x - 0.0) < 1e-4 and abs(nb1.y - 2.0) < 1e-4

    # 2. Agora altera s2 fixando a base (nid_baixo):
    # s3 deve permanecer fixa e s1 deve ser empurrada
    pos_s3_before = {graph.nodes[graph.segments[s3].node_a_id].x, graph.nodes[graph.segments[s3].node_b_id].x}
    graph.set_segment_length(s2, 1.5, anchor_node_id=nid_baixo)
    pos_s3_after = {graph.nodes[graph.segments[s3].node_a_id].x, graph.nodes[graph.segments[s3].node_b_id].x}
    assert pos_s3_before == pos_s3_after


def test_dimension_conflict_detection_and_discard_on_cancel():
    """Valida a detecção de cotas conflitantes/redundantes e o descarte de cota ao cancelar."""
    graph = WallGraph2D()
    # Cria uma parede dividida em 2 segmentos: (0,0)->(2,0) e (2,0)->(5,0)
    s1 = graph.add_segment(0.0, 0.0, 2.0, 0.0)
    s2 = graph.add_segment(2.0, 0.0, 5.0, 0.0)

    # 1. Adiciona cota para s1 (2.0m)
    d1 = graph.add_dimension((0.0, 0.0), (2.0, 0.0), seg_id=s1)
    assert d1 is not None
    assert len(graph.dimensions) == 1

    # 2. Tentar adicionar outra cota exatamente na mesma parede ou face deve acusar conflito de duplicidade
    conflict_same = graph.check_dimension_conflict((0.0, 0.0), (2.0, 0.0))
    assert conflict_same is not None

    # 3. Cotar o segundo segmento s2 (2,0) a (5,0) NÃO conflita pois não há sobreposição
    conflict_s2 = graph.check_dimension_conflict((2.0, 0.0), (5.0, 0.0))
    assert conflict_s2 is None

    # 4. Cotar de ponta a ponta (0,0) até (5,0) quando apenas UM dos dois segmentos está cotado é PERMITIDO!
    conflict_partial_span = graph.check_dimension_conflict((0.0, 0.0), (5.0, 0.0))
    assert conflict_partial_span is None

    # 5. Mas se TODOS os segmentos já estiverem cotados (adicionando d2):
    d2 = graph.add_dimension((2.0, 0.0), (5.0, 0.0), seg_id=s2)
    # Agora tentar cotar de ponta a ponta geraria conflito de redundância total:
    conflict_all_span = graph.check_dimension_conflict((0.0, 0.0), (5.0, 0.0))
    assert conflict_all_span is not None

    # 6. Testa descarte em remove_dimension
    assert graph.remove_dimension(d1) is True
    assert graph.remove_dimension(d2) is True
    assert len(graph.dimensions) == 0
    # Agora que foram removidas, a cota de ponta a ponta não conflita
    assert graph.check_dimension_conflict((0.0, 0.0), (5.0, 0.0)) is None


def test_chain_collinear_segments_for_dimension():
    """Valida a identificação de cadeias de paredes segmentadas para cotas de ponta a ponta."""
    from trazomob.wall.floorplan_canvas import WallFloorplanCanvas
    graph = WallGraph2D()
    s1 = graph.add_segment(0.21, 14.65, 0.21, 13.56)
    s2 = graph.add_segment(0.21, 13.56, 0.21, 11.791)

    canvas = WallFloorplanCanvas(graph)
    chain = canvas._find_segments_along_dimension((0.21, 14.65), (0.21, 11.791))
    assert len(chain) == 2
    assert chain[0][0] == s1
    assert chain[1][0] == s2
    total_len = sum(item[3] for item in chain)
    assert abs(total_len - 2.859) < 1e-3


def test_chain_dimension_sync_on_edit():
    """Garante que ao editar o valor de uma cota de cadeia segmentada, a cota atualiza sua extensão (p1, p2)."""
    from trazomob.wall.floorplan_canvas import WallFloorplanCanvas
    graph = WallGraph2D()
    # s1: 1.090m (de y=14.65 para y=13.56)
    s1 = graph.add_segment(0.21, 14.65, 0.21, 13.56)
    # s2: 1.769m (de y=13.56 para y=11.791) -> total 2.859m
    s2 = graph.add_segment(0.21, 13.56, 0.21, 11.791)

    # Cota de ponta a ponta (com offset em X)
    dim_id = graph.add_dimension((0.0, 14.65), (0.0, 11.791))
    dim = graph.dimensions[dim_id]
    assert round(dist_2d(dim.p1, dim.p2), 3) == 2.859

    canvas = WallFloorplanCanvas(graph)
    # Mock do diálogo para retornar 3.000m (em escala 1.0 m) fixando início (14.65) e empurrando o fim
    from unittest.mock import patch
    with patch("PySide6.QtWidgets.QDialog.exec", return_value=1):
        with patch("PySide6.QtWidgets.QDoubleSpinBox.value", return_value=3.000):
            res = canvas._edit_custom_dimension_dialog(dim_id)
            assert res is True

    # Verifica se a cota foi redimensionada para exatamente 3.000m
    new_dim_len = dist_2d(dim.p1, dim.p2)
    assert round(new_dim_len, 3) == 3.000

    # Verifica se a parede segmentada (s1 + s2) agora mede 3.000m no total
    total_wall_len = graph.segments[s1].length(graph) + graph.segments[s2].length(graph)
    assert round(total_wall_len, 3) == 3.000


def test_undo_restores_dimension_references_and_driving_flag():
    """O snapshot de undo deve preservar IDs, referências de segmento e flags driving."""
    from core.scene import Scene
    from trazomob.wall.floorplan_dialog import WallFloorplanDialog

    scene = Scene()

    class DummyViewport:
        def __init__(self, sc):
            self.scene = sc
        def update(self):
            pass
        def flash_status(self, msg):
            pass

    dlg = WallFloorplanDialog(DummyViewport(scene))
    s1 = dlg.graph.add_segment(0.0, 0.0, 10.0, 0.0)
    did = dlg.graph.add_dimension((0.0, 0.0), (4.0, 0.0), seg_id=s1, driving=False)
    dlg.canvas._save_history()

    dlg.graph.clear()
    assert not dlg.graph.dimensions

    assert dlg.canvas.undo() is True
    restored = dlg.graph.dimensions[did]
    assert restored.driving is False
    assert restored.a_seg_id == s1 and restored.a_end == "a"
    assert restored.b_seg_id == s1 and restored.b_end is None
    assert round(restored.b_dist, 3) == 4.0
    assert round(dist_2d(restored.p1, restored.p2), 3) == 4.0


def _is_orthogonal(g) -> bool:
    for s in g.segments.values():
        na = g.nodes[s.node_a_id]
        nb = g.nodes[s.node_b_id]
        if abs(na.x - nb.x) > 1e-6 and abs(na.y - nb.y) > 1e-6:
            return False
    return True


def test_drag_constrained_corner_never_creates_diagonals():
    """Arrastar um canto cotado não pode girar as paredes vizinhas."""
    g = WallGraph2D()
    s1 = g.add_segment(0, 0, 4, 0)
    s2 = g.add_segment(4, 0, 4, 3)
    s3 = g.add_segment(4, 3, 0, 3)
    s4 = g.add_segment(0, 3, 0, 0)
    g.merge_close_nodes()
    d1 = g.add_dimension((0, 0), (4, 0), seg_id=s1)

    g.move_node(1, 0.5, 0.2)

    assert _is_orthogonal(g)
    assert round(dist_2d(g.dimensions[d1].p1, g.dimensions[d1].p2), 3) == 4.0
    assert round(g.segments[s1].length(g), 3) == 4.0
    assert round(g.segments[s2].length(g), 3) == 3.0
    assert round(g.segments[s3].length(g), 3) == 4.0
    assert round(g.segments[s4].length(g), 3) == 3.0


def test_drag_open_chain_keeps_walls_orthogonal():
    """Em cadeia aberta, o arraste pode esticar paredes livres, mas nunca diagonalizá-las."""
    g = WallGraph2D()
    s1 = g.add_segment(0, 0, 4, 0)
    s2 = g.add_segment(4, 0, 4, 3)
    s3 = g.add_segment(4, 3, 2, 3)
    d1 = g.add_dimension((0, 0), (4, 0), seg_id=s1)

    g.move_node(1, 0.0, 1.0)

    assert _is_orthogonal(g)
    assert round(dist_2d(g.dimensions[d1].p1, g.dimensions[d1].p2), 3) == 4.0
    assert round(g.segments[s1].length(g), 3) == 4.0
    assert round(g.segments[s3].length(g), 3) == 2.0


def test_face_extension_at_corner_matches_miter_geometry():
    """get_start_extension deve devolver o deslocamento real da face no canto em 45°."""
    g = WallGraph2D(default_thickness=0.2)
    s1 = g.add_segment(0, 0, 4, 0)
    s2 = g.add_segment(4, 0, 4, 3)

    # Extremidade livre: sem extensão
    assert abs(g.get_start_extension((0, 0), (1, 0), 0.2, "left")) < 1e-9
    assert abs(g.get_start_extension((0, 0), (1, 0), 0.2)) < 1e-9

    # Canto em L: cada face desloca ±t/2 ao longo da parede
    assert abs(g.get_start_extension((4, 0), (1, 0), 0.2, "left") - 0.1) < 1e-9
    assert abs(g.get_start_extension((4, 0), (0, 1), 0.2, "left") - 0.1) < 1e-9
    assert abs(g.get_start_extension((4, 0), (0, 1), 0.2, "right") + 0.1) < 1e-9
    assert abs(g.get_start_node_extension(2, (0, 1), 0.2, "left") - 0.1) < 1e-9

    # Modo eixo central permanece neutro
    assert abs(g.get_start_extension((4, 0), (0, 1), 0.2)) < 1e-9


def test_segment_face_length_and_typed_face_compensation():
    """Digitar uma medida de face deve resultar naquela face, não no eixo central."""
    g = WallGraph2D(default_thickness=0.2)
    a = g.add_segment(0, 0, 4, 0)
    b = g.add_segment(4, 0, 4, 3)

    assert round(g.segments[a].length(g), 4) == 4.0
    assert round(g.segment_face_length(a, "left"), 4) == 3.9
    assert round(g.segment_face_length(a, "right"), 4) == 4.1

    # Mesma conversão feita pelo diálogo: face desejada -> eixo central
    desired_face = 4.5
    center_target = desired_face + (g.segments[a].length(g) - g.segment_face_length(a, "left"))
    assert g.set_segment_length(a, center_target, anchor_node_id=g.segments[a].node_a_id) is True
    assert round(g.segment_face_length(a, "left"), 4) == desired_face
    assert round(g.segments[a].length(g), 4) == 4.6

    # Parede vertical: face esquerda de 4.0 m exige eixo de 4.1 m
    desired_v = 4.0
    center_v = desired_v + (g.segments[b].length(g) - g.segment_face_length(b, "left"))
    assert g.set_segment_length(b, center_v, anchor_node_id=g.segments[b].node_a_id) is True
    assert round(g.segment_face_length(b, "left"), 4) == desired_v


def test_dimension_chain_is_exact_only_when_walls_cover_the_span():
    """A cobertura da cota é geométrica: nada de heurística de 30 %."""
    g = WallGraph2D(default_thickness=0.2)
    s1 = g.add_segment(0, 0, 10, 0)

    # Cota de 2.5 m dentro de uma parede de 10 m: NÃO é construtiva (seria esticar a parede toda).
    partial = g.resolve_dimension_chain((3.0, 0.0), (5.5, 0.0))
    assert partial.seg_ids == [s1]
    assert partial.exact is False
    assert partial.is_constructive is False
    assert round(partial.overshoot_m, 3) == 4.5  # sobra 4,5 m depois da última ponta
    assert round(partial.span_len, 3) == 2.5

    # Cota de 3.5 m (mais que os 30 % antigos) continua não construtiva.
    over_thirty = g.resolve_dimension_chain((3.0, 0.0), (6.5, 0.0))
    assert over_thirty.exact is False

    # Cota de ponta a ponta é construtiva.
    full = g.resolve_dimension_chain((0.0, 0.0), (10.0, 0.0))
    assert full.seg_ids == [s1]
    assert full.exact is True
    assert full.is_constructive is True
    assert full.start_node_id is not None and full.end_node_id is not None
    assert full.start_node_id != full.end_node_id


def test_dimension_chain_rejects_gaps_and_partial_but_accepts_inner_segment():
    """Vãos (porta) e trechos parciais ficam como referência; segmento inteiro entre nós é construtivo."""
    g = WallGraph2D(default_thickness=0.2)
    # Parede com porta: 0-2, vão 2-3, 3-5
    a = g.add_segment(0, 0, 2, 0)
    c = g.add_segment(3, 0, 5, 0)

    across_door = g.resolve_dimension_chain((0.0, 0.0), (5.0, 0.0))
    assert across_door.seg_ids == [a, c]
    assert round(across_door.gap_m, 3) == 1.0
    assert across_door.is_constructive is False

    # Cota do vão exato de uma parede: construtiva, mesmo com vizinhas colineares.
    g2 = WallGraph2D(default_thickness=0.2)
    s1 = g2.add_segment(0, 0, 2, 0)
    s2 = g2.add_segment(2, 0, 5, 0)
    middle = g2.resolve_dimension_chain((2.0, 0.0), (5.0, 0.0))
    assert middle.seg_ids == [s2]
    assert middle.exact is True
    assert middle.start_node_id == g2.segments[s2].node_a_id
    assert middle.end_node_id == g2.segments[s2].node_b_id

    both = g2.resolve_dimension_chain((0.0, 0.0), (5.0, 0.0))
    assert both.seg_ids == [s1, s2]
    assert both.exact is True


def test_partial_dimension_never_stretches_the_whole_wall():
    """Editar uma cota interna de parede longa não deve redimensionar a parede inteira."""
    from trazomob.wall.floorplan_canvas import WallFloorplanCanvas
    from unittest.mock import patch

    graph = WallGraph2D(default_thickness=0.2)
    s1 = graph.add_segment(0, 0, 10, 0)
    dim_id = graph.add_dimension((3.0, 0.0), (5.5, 0.0), seg_id=s1, driving=True)

    canvas = WallFloorplanCanvas(graph)
    with patch("PySide6.QtWidgets.QDialog.exec", return_value=1):
        with patch("PySide6.QtWidgets.QDoubleSpinBox.value", return_value=4.0):
            with patch("PySide6.QtWidgets.QMessageBox.information", return_value=0):
                canvas._edit_custom_dimension_dialog(dim_id)

    # A parede permanece com 10 m; a cota vira apenas referência.
    assert round(graph.segments[s1].length(graph), 3) == 10.0
    assert graph.dimensions[dim_id].driving is False

    # O mesmo vale para a associação usada na criação da cota.
    assert canvas._find_segment_for_dimension((3.0, 0.0), (5.5, 0.0)) == s1


def test_face_edge_dimension_from_canvas_binds_to_nodes_and_is_constructive():
    """Clicar na face de uma parede deve gerar cota restritiva, não apenas anotação."""
    from trazomob.wall.floorplan_canvas import WallFloorplanCanvas

    g = WallGraph2D(default_thickness=0.2)
    s1 = g.add_segment(0, 0, 4, 0)
    s2 = g.add_segment(4, 0, 4, 3)
    s3 = g.add_segment(4, 3, 0, 3)
    s4 = g.add_segment(0, 3, 0, 0)
    g.merge_close_nodes()

    quads = g.compute_wall_polygons()
    inner_p1, inner_p2 = quads[s1][0], quads[s1][1]   # face esquerda/interna
    outer_p1, outer_p2 = quads[s1][3], quads[s1][2]   # face direita/externa

    for p1, p2 in ((inner_p1, inner_p2), (outer_p1, outer_p2)):
        did = g.add_dimension(p1, p2, seg_id=s1, driving=True)
        d = g.dimensions[did]
        assert d.node_a_id is not None and d.node_b_id is not None
        assert d.node_a_id != d.node_b_id
        assert g.dimension_has_partial_anchor(d) is False
        assert g.resolve_dimension_chain(d.p1, d.p2).is_constructive is True
        g.remove_dimension(did)

    # A cota da face interna (3,8 m) aceita edição e faz a face medir o valor digitado.
    from unittest.mock import patch
    did = g.add_dimension(inner_p1, inner_p2, seg_id=s1, driving=True)
    canvas = WallFloorplanCanvas(g)
    with patch("PySide6.QtWidgets.QDialog.exec", return_value=1):
        with patch("PySide6.QtWidgets.QDoubleSpinBox.value", return_value=5.0):
            assert canvas._edit_custom_dimension_dialog(did) is True

    assert round(g.segment_face_length(s1, "left"), 3) == 5.0
    assert round(g.segment_face_length(s1, "right"), 3) == 5.4
    # A parede perpendicular mantém o vão de 3,0 m (só translada com o canto).
    assert round(g.segments[s2].length(g), 3) == 3.0
    assert round(g.segment_face_length(s2, "left"), 3) == 2.8
    assert round(g.segment_face_length(s3, "left"), 3) == 5.0


def test_legacy_face_dimension_is_migrated_to_node_anchor():
    """Cotas antigas gravadas como 'ponto interno' sobre cantos devem virar restritivas ao carregar."""
    g = WallGraph2D(default_thickness=0.2)
    s1 = g.add_segment(0, 0, 4, 0)
    s2 = g.add_segment(4, 0, 4, 3)
    s3 = g.add_segment(4, 3, 0, 3)
    s4 = g.add_segment(0, 3, 0, 0)
    g.merge_close_nodes()
    quads = g.compute_wall_polygons()

    did = g.add_dimension(quads[s1][0], quads[s1][1], seg_id=s1, driving=False)
    d = g.dimensions[did]
    # Simula o estado antigo (ponta no meio, sem nó)
    d.a_end = None
    d.b_end = None
    d.node_a_id = None
    d.node_b_id = None
    d.p1 = quads[s1][0]
    d.p2 = quads[s1][1]
    assert g.dimension_has_partial_anchor(d) is True

    g.sync_all_dimensions()

    assert g.dimension_has_partial_anchor(d) is False
    assert d.node_a_id is not None and d.node_b_id is not None
    assert g.resolve_dimension_chain(d.p1, d.p2).is_constructive is True
    assert round(dist_2d(d.p1, d.p2), 3) == 3.8


def test_from_dict_normalizes_legacy_partial_dimension():
    """Ao abrir um plano salvo, cotas antigas de canto devem ser reancoradas em nós."""
    g = WallGraph2D(default_thickness=0.2)
    s1 = g.add_segment(0, 0, 4, 0)
    s2 = g.add_segment(4, 0, 4, 3)
    s3 = g.add_segment(4, 3, 0, 3)
    s4 = g.add_segment(0, 3, 0, 0)
    g.merge_close_nodes()
    quads = g.compute_wall_polygons()

    did = g.add_dimension(quads[s1][0], quads[s1][1], seg_id=s1, driving=True)
    d = g.dimensions[did]
    # Estado legado: ponta interna, sem nó
    d.a_end = None
    d.b_end = None
    d.node_a_id = None
    d.node_b_id = None
    d.a_dist = 0.1
    d.b_dist = 3.9
    d.p1 = quads[s1][0]
    d.p2 = quads[s1][1]

    restored = WallGraph2D.from_dict(g.to_dict())
    rd = restored.dimensions[did]
    assert restored.dimension_has_partial_anchor(rd) is False
    assert rd.node_a_id is not None and rd.node_b_id is not None
    assert restored.resolve_dimension_chain(rd.p1, rd.p2).is_constructive is True
    assert round(dist_2d(rd.p1, rd.p2), 3) == 3.8













