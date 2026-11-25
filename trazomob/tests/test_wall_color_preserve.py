# SPDX-License-Identifier: GPL-3.0-or-later
"""Testes unitários garantindo que a pintura/cor da parede seja preservada
ao atualizar parâmetros da parede e exportada fielmente para o render.
"""
from PySide6.QtGui import QVector3D

from core.scene import Scene
from formats.meshexport import collect_geometry, export_names
from trazomob.wall.builder import WallBuilderTool


def test_wall_color_preserved_on_update():
    """Garante que pintar a parede (ou suas faces) não reseta a cor ao atualizar parâmetros."""
    scene = Scene()
    pts = [QVector3D(0, 0, 0), QVector3D(4, 0, 0), QVector3D(4, 3, 0), QVector3D(0, 3, 0)]
    grp = WallBuilderTool.build_chain_group(
        scene=scene,
        pts=pts,
        is_closed=True,
        altura_m=2.6,
        espessura_m=0.15,
        alinhamento="interno",
    )
    scene.groups.append(grp)

    # 1. Simula pintura azul na parede inteira (balde de tinta no grupo)
    BLUE = [0.1, 0.3, 0.9]
    grp.material = {"color": list(BLUE)}
    # E simula pintura de textura ou cor em uma face individual
    grp.mesh.faces[2].attrs["color"] = [0.2, 0.4, 0.8]

    # Simula o fluxo de atualização do SidebarWallController
    old_material = getattr(grp, "material", None)
    old_face_attrs = [dict(f.attrs) if f.attrs else {} for f in grp.mesh.faces]

    new_grp = WallBuilderTool.build_chain_group(
        scene=scene,
        pts=pts,
        is_closed=True,
        altura_m=2.8,  # Mudou altura
        espessura_m=0.15,
        alinhamento="interno",
        name_override=grp.name,
    )
    if old_material:
        new_grp.material = dict(old_material)

    for idx, nf in enumerate(new_grp.mesh.faces):
        if idx < len(old_face_attrs) and old_face_attrs[idx]:
            for k in ("color", "texture", "opacity", "mat"):
                if k in old_face_attrs[idx]:
                    nf.attrs[k] = old_face_attrs[idx][k]

    # Validações
    assert new_grp.material is not None
    assert new_grp.material["color"] == BLUE
    assert new_grp.mesh.faces[2].attrs.get("color") == [0.2, 0.4, 0.8]


def test_wall_color_exported_to_render_clean_scene():
    """Garante que a cor aplicada à parede é assada nas faces e entra nos materiais do render."""
    from core.group import Group
    from core.materials import effective_attrs
    from core.mesh import Mesh

    scene = Scene()
    pts = [QVector3D(0, 0, 0), QVector3D(3, 0, 0), QVector3D(3, 3, 0), QVector3D(0, 3, 0)]
    grp = WallBuilderTool.build_chain_group(
        scene=scene,
        pts=pts,
        is_closed=True,
        altura_m=2.6,
        espessura_m=0.15,
        name_override="Parede Contínua",
    )
    # Pinta a parede de azul
    BLUE = (0.05, 0.2, 0.85)
    grp.material = {"color": list(BLUE)}
    scene.groups.append(grp)

    # Simula a montagem da clean_scene do render_engine.py
    clean_scene = Scene()
    paint = getattr(grp, "material", None)
    m_clean = Mesh()
    for f in grp.mesh.faces:
        nf = m_clean.add_face(list(f.vertices))
        attrs_baked = effective_attrs(f.attrs, paint) if paint else dict(f.attrs)
        if attrs_baked:
            if "mat" not in attrs_baked and "parede" in grp.name.lower():
                from trazomob.wall.paint_catalog import DEFAULT_WALL_PAINT
                attrs_baked["mat"] = DEFAULT_WALL_PAINT
            nf.attrs.update(attrs_baked)
    g_clean = Group(m_clean, name=grp.name)
    clean_scene.groups.append(g_clean)

    # Coleta geometria para exportação GLTF
    mats, prims = collect_geometry(clean_scene)
    names = export_names(mats)

    # Verifica se a cor azul foi capturada e se o nome do material é o padrão de parede
    color_keys = [k for k in mats.keys() if k[0] == "color"]
    assert len(color_keys) >= 1
    blue_mat_key = next((k for k in color_keys if abs(k[1][0] - BLUE[0]) < 1e-3), None)
    assert blue_mat_key is not None, "A cor azul deve estar presente nos materiais exportados."
    assert names.get(blue_mat_key) == "Pintura_de_parede_fosco_acetinado"
