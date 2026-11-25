# SPDX-License-Identifier: GPL-3.0-or-later
"""Testes para cinemática contínua de abertura e detecção de colisões visuais."""
from PySide6.QtGui import QVector3D

from core.group import Group
from core.mesh import Mesh
from core.scene import Scene
from trazomob.interaction.collision import check_opening_collisions
from trazomob.interaction.interact import CabinetInteract


def _create_box_mesh(min_x, max_x, min_y, max_y, min_z, max_z):
    mesh = Mesh()
    pts = [
        QVector3D(min_x, min_y, min_z),
        QVector3D(max_x, min_y, min_z),
        QVector3D(max_x, max_y, min_z),
        QVector3D(min_x, max_y, min_z),
        QVector3D(min_x, min_y, max_z),
        QVector3D(max_x, min_y, max_z),
        QVector3D(max_x, max_y, max_z),
        QVector3D(min_x, max_y, max_z),
    ]
    # Cria faces simples
    mesh.add_face([pts[0], pts[1], pts[2], pts[3]])
    mesh.add_face([pts[4], pts[5], pts[6], pts[7]])
    return mesh


def test_drawer_fractional_opening():
    # Cria gaveta simples
    m = _create_box_mesh(0.0, 0.4, 0.0, 0.5, 0.0, 0.2)
    frente = Group(m, name="Balcao - Frente Gaveta 1")
    mod = Group(name="Balcao_1")
    mod.children = [frente]
    mod.ext = {"trazomob_module": {"rot_z": 0.0}}

    # Abertura 50%
    CabinetInteract.set_piece_open_fraction(frente, 0.5, module_group=mod)
    assert frente.ext.get("is_open") is True
    assert frente.ext.get("open_fraction") == 0.5
    # Deslocamento esperado em Y: -0.35 * 0.5 = -0.175
    ys = [v.position.y() for v in frente.mesh.vertices]
    assert min(ys) < -0.10

    # Fechamento (0%)
    CabinetInteract.set_piece_open_fraction(frente, 0.0, module_group=mod)
    assert frente.ext.get("is_open") is False
    assert frente.ext.get("open_fraction") == 0.0
    ys_closed = [v.position.y() for v in frente.mesh.vertices]
    assert abs(min(ys_closed) - 0.0) < 1e-4


def test_door_fractional_opening_and_hinge():
    # Porta esquerda (largura 0.4, altura 0.7, espessura 0.018)
    m = _create_box_mesh(0.0, 0.4, -0.018, 0.0, 0.0, 0.7)
    porta = Group(m, name="Balcao - Porta Esq")
    porta.ext = {"trazomob": {"door_side": "left"}}
    mod = Group(name="Balcao_1")
    mod.children = [porta]
    mod.ext = {"trazomob_module": {"rot_z": 0.0}}

    # 100% de abertura
    CabinetInteract.set_piece_open_fraction(porta, 1.0, module_group=mod)
    assert porta.ext.get("is_open") is True
    # O pivot deve ser próximo a min_x=0.0
    pivot = porta.ext.get("hinge_pivot")
    assert pivot is not None
    assert abs(pivot.x()) < 0.05


def test_collision_detection_between_open_pieces():
    scene = Scene()

    # Módulo A com gaveta abrindo em direção a -Y
    m1 = _create_box_mesh(0.0, 0.4, 0.0, 0.5, 0.0, 0.2)
    gaveta = Group(m1, name="Gaveta_A")
    mod_a = Group(name="Balcao_A")
    mod_a.children = [gaveta]
    mod_a.ext = {"trazomob_module": {"rot_z": 0.0}}

    # Obstáculo na frente da gaveta (ex: puxador de balcão de canto a -0.2m em Y)
    m2 = _create_box_mesh(0.1, 0.3, -0.25, -0.15, 0.0, 0.2)
    obstaculo = Group(m2, name="Puxador_Canto")

    scene.groups.extend([mod_a, obstaculo])

    # Fechada: sem colisão
    CabinetInteract.set_piece_open_fraction(gaveta, 0.0, module_group=mod_a, scene=scene)
    col_closed = check_opening_collisions(scene)
    assert len(col_closed) == 0

    # Aberta 100% (desloca 35cm para a frente -> atinge a zona de Y: -0.35 a 0.15, interceptando o obstáculo)
    CabinetInteract.set_piece_open_fraction(gaveta, 1.0, module_group=mod_a, scene=scene)
    col_open = check_opening_collisions(scene)
    assert len(col_open) > 0
    assert "Gaveta_A" in col_open[0]["desc"]
    assert "Puxador_Canto" in col_open[0]["desc"]


def test_door_opening_texture_uv_fixed():
    """Garante que a textura aplicada à face da porta não se desloque nem 'ande' durante a rotação de abertura."""
    from core.texture import face_uv_axes

    m = _create_box_mesh(0.0, 0.4, -0.018, 0.0, 0.0, 0.7)
    # Adiciona textura na face frontal
    f_front = m.faces[0]
    f_front.attrs["texture"] = {"path": "dummy.jpg", "sw": 1.0, "sh": 1.0}

    porta = Group(m, name="Balcao - Porta Esq")
    porta.ext = {"trazomob": {"door_side": "left"}}
    mod = Group(name="Balcao_1")
    mod.children = [porta]
    mod.ext = {"trazomob_module": {"rot_z": 0.0}}

    # Obtém UV em um vértice específico quando a porta está fechada
    v0 = m.vertices[0]
    CabinetInteract.set_piece_open_fraction(porta, 0.0, module_group=mod)
    gu0, cu0, gv0, cv0 = face_uv_axes(f_front.attrs["texture"], f_front.normal())
    u0 = QVector3D.dotProduct(gu0, v0.position) + cu0
    v_coord0 = QVector3D.dotProduct(gv0, v0.position) + cv0

    # Abre a porta em 50%
    CabinetInteract.set_piece_open_fraction(porta, 0.5, module_group=mod)
    gu50, cu50, gv50, cv50 = face_uv_axes(f_front.attrs["texture"], f_front.normal())
    u50 = QVector3D.dotProduct(gu50, v0.position) + cu50
    v_coord50 = QVector3D.dotProduct(gv50, v0.position) + cv50

    # Abre a porta em 100%
    CabinetInteract.set_piece_open_fraction(porta, 1.0, module_group=mod)
    gu100, cu100, gv100, cv100 = face_uv_axes(f_front.attrs["texture"], f_front.normal())
    u100 = QVector3D.dotProduct(gu100, v0.position) + cu100
    v_coord100 = QVector3D.dotProduct(gv100, v0.position) + cv100

    # As coordenadas UV relativas ao vértice devem permanecer idênticas durante todo o movimento
    assert abs(u0 - u50) < 1e-4
    assert abs(v_coord0 - v_coord50) < 1e-4
    assert abs(u0 - u100) < 1e-4
    assert abs(v_coord0 - v_coord100) < 1e-4


def test_capture_and_restore_open_state():
    """Garante que o estado de abertura seja capturado e restaurado ao reconstruir um módulo."""
    m_old = _create_box_mesh(0.0, 0.4, -0.018, 0.0, 0.0, 0.7)
    porta_old = Group(m_old, name="Balcao - Porta Esq")
    porta_old.ext = {"trazomob": {"door_side": "left"}}
    mod_old = Group(name="Balcao_1")
    mod_old.children = [porta_old]
    mod_old.ext = {"trazomob_module": {"rot_z": 0.0}}

    # Abre a porta em 75%
    CabinetInteract.set_piece_open_fraction(porta_old, 0.75, module_group=mod_old)
    assert porta_old.ext.get("open_fraction") == 0.75

    # Captura o estado
    state = CabinetInteract.capture_open_state(mod_old)
    assert state["has_open"] is True
    assert state["max_frac"] == 0.75
    assert state["pieces"]["Balcao - Porta Esq"] == 0.75

    # Simula um novo módulo reconstruído (portas fechadas de fábrica)
    m_new = _create_box_mesh(0.0, 0.45, -0.018, 0.0, 0.0, 0.7)
    porta_new = Group(m_new, name="Balcao - Porta Esq")
    porta_new.ext = {"trazomob": {"door_side": "left"}}
    mod_new = Group(name="Balcao_1")
    mod_new.children = [porta_new]
    mod_new.ext = {"trazomob_module": {"rot_z": 0.0}}

    # Restaura o estado no novo módulo
    restored = CabinetInteract.restore_open_state(mod_new, state)
    assert restored is True
    assert porta_new.ext.get("is_open") is True
    assert porta_new.ext.get("open_fraction") == 0.75


