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
