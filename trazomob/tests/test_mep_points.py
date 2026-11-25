# SPDX-License-Identifier: GPL-3.0-or-later
"""Testes unitários para Pontos Elétricos e Hidráulicos (MEP)."""
from __future__ import annotations

from trazomob.domain.mep_points import (
    MEPPoint,
    build_mep_point_group,
    check_mep_interferences,
)


def test_mep_point_roundtrip_serialization():
    pt = MEPPoint(id=1, seg_id=10, kind="agua_fria", offset_m=1.25, height_m=0.60, side="right", label="Pia")
    data = pt.to_dict()
    restored = MEPPoint.from_dict(data)
    assert restored == pt


def test_build_mep_point_group_creates_valid_3d_group():
    pt = MEPPoint(id=2, seg_id=10, kind="tomada_220v", offset_m=0.80, height_m=1.15)
    grp = build_mep_point_group(pt, world_pos=(0.80, 0.0, 1.15))
    assert grp.name == "MEP_tomada_220v_2"
    assert grp.ext["trazomob_mep_point"]["kind"] == "tomada_220v"
    assert grp.mesh is not None and len(grp.mesh.faces) > 0


def test_check_mep_interferences_detects_blocked_and_ignores_clear_points():
    p_blocked = MEPPoint(id=1, seg_id=1, kind="interruptor", offset_m=0.5, height_m=1.10)
    p_clear = MEPPoint(id=2, seg_id=1, kind="tomada_110v", offset_m=2.5, height_m=0.30)

    positions = {
        1: (0.50, 0.05, 1.10),
        2: (2.50, 0.05, 0.30),
    }
    modules = [
        ("Torre Quente 700x2100x600", (0.10, 0.0, 0.0), (0.80, 0.60, 2.10)),
    ]

    alerts = check_mep_interferences([p_blocked, p_clear], positions, modules)
    assert len(alerts) == 1
    assert alerts[0]["point_id"] == 1
    assert alerts[0]["module_name"] == "Torre Quente 700x2100x600"


def test_wall_graph_add_and_remove_mep_point():
    from trazomob.wall.plan_2d import WallGraph2D

    g = WallGraph2D()
    s1 = g.add_segment(0.0, 0.0, 3.0, 0.0)

    pid = g.add_mep_point(s1, "tomada_110v", offset_m=1.2)
    assert pid in g.mep_points
    assert g.mep_points[pid].height_m == 0.30
    assert g.remove_mep_point(pid) is True
    assert pid not in g.mep_points


def test_wall_graph_mep_points_persist_in_to_dict_and_from_dict():
    from trazomob.wall.plan_2d import WallGraph2D

    g = WallGraph2D()
    s1 = g.add_segment(0.0, 0.0, 4.0, 0.0)
    pid = g.add_mep_point(s1, "agua_quente", offset_m=1.5, height_m=0.65, label="Aquecedor")

    data = g.to_dict()
    g2 = WallGraph2D.from_dict(data)
    assert pid in g2.mep_points
    assert g2.mep_points[pid].kind == "agua_quente"
    assert g2.mep_points[pid].offset_m == 1.5
    assert g2.mep_points[pid].label == "Aquecedor"


def test_compute_mep_wall_distances_and_update_from_nearest_corner():
    from trazomob.domain.mep_points import (
        MEPPoint,
        compute_mep_wall_distances,
        update_mep_point_position,
    )

    # Parede de 3.0m, ponto em 2.4m -> canto mais próximo é o final (0.6m)
    pt = MEPPoint(id=5, seg_id=1, kind="tomada_110v", offset_m=2.40, height_m=0.30)
    info = compute_mep_wall_distances(pt, 3.0)
    assert info["nearest_corner"] == "end"
    assert abs(info["nearest_dist_m"] - 0.60) < 1e-6

    # Usuário clica na cota do canto mais próximo e corrige para 0.45m, e altura para 1.15m
    update_mep_point_position(pt, 3.0, height_m=1.15, dist_from_nearest_m=0.45)
    assert abs(pt.height_m - 1.15) < 1e-6
    assert abs(pt.offset_m - 2.55) < 1e-6


def test_draw_mep_selection_overlay_handles_tuple_world_to_pixel():
    from types import SimpleNamespace
    from trazomob.domain.mep_points import MEPPoint, build_mep_point_group
    from trazomob.wall.selection import WallSelectionManager

    pt = MEPPoint(id=7, seg_id=1, kind="tomada_110v", offset_m=1.20, height_m=0.30)
    grp = build_mep_point_group(pt, world_pos=(1.20, 0.0, 0.30))

    drawn_lines = []
    drawn_texts = []

    class DummyPainter:
        def save(self): pass
        def restore(self): pass
        def setPen(self, _): pass
        def drawLine(self, a, b): drawn_lines.append((a, b))
        def drawText(self, x, y, txt): drawn_texts.append((x, y, txt))

    vp = SimpleNamespace(
        scene=SimpleNamespace(selection=[grp]),
        world_to_pixel=lambda v: (100.0 + v.x() * 10.0, 200.0 - v.z() * 10.0),
    )
    mgr = WallSelectionManager.__new__(WallSelectionManager)
    mgr._draw_mep_selection_overlay(vp, DummyPainter())

    assert len(drawn_lines) == 1
    assert len(drawn_texts) == 1
    assert "Alt: 0.30m" in drawn_texts[0][2]
