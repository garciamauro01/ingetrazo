# SPDX-License-Identifier: GPL-3.0-or-later
"""Testes para extração e exibição de texturas no MaterialEditorDialog."""
import pytest
from PySide6.QtGui import QVector3D

from core.group import Group
from core.mesh import Mesh
from core.scene import Scene
from trazomob.ui.material_editor_dialog import extract_scene_materials


def test_extract_scene_materials_group_texture(tmp_path):
    # Cria arquivo falso de textura
    tex_file = tmp_path / "tijolo_vista.png"
    tex_file.write_bytes(b"\x89PNG\r\n\x1a\n")

    scene = Scene()
    m = Mesh()
    f = m.add_face([QVector3D(0, 0, 0), QVector3D(1, 0, 0), QVector3D(1, 1, 0), QVector3D(0, 1, 0)])

    # Parede (grupo) com material de textura atribuído
    wall_group = Group(m, name="Parede 1")
    wall_group.material = {
        "texture": {"path": str(tex_file), "sw": 1.0, "sh": 1.0},
        "mat": "Tijolo a Vista"
    }
    scene.groups.append(wall_group)

    mats = extract_scene_materials(scene)
    names = [m["name"] for m in mats]
    assert "Tijolo a Vista" in names

    item = next(m for m in mats if m["name"] == "Tijolo a Vista")
    assert item["texture_path"] == str(tex_file)
    assert item["display_name"] == "Tijolo a Vista"


def test_extract_scene_materials_face_texture(tmp_path):
    tex_file = tmp_path / "madeira_nogueira.jpg"
    tex_file.write_bytes(b"\xff\xd8\xff")

    scene = Scene()
    m = Mesh()
    f = m.add_face([QVector3D(0, 0, 0), QVector3D(1, 0, 0), QVector3D(1, 1, 0), QVector3D(0, 1, 0)])
    f.attrs["texture"] = {"path": str(tex_file)}
    # Sem mat explícito: deve usar o stem do arquivo
    g = Group(m, name="Módulo 1")
    scene.groups.append(g)

    mats = extract_scene_materials(scene)
    names = [m["name"] for m in mats]
    assert "madeira_nogueira" in names

    item = next(m for m in mats if m["name"] == "madeira_nogueira")
    assert item["texture_path"] == str(tex_file)


def test_material_highlight_is_drawn_in_world_coordinates(qapp):
    """O destaque deve seguir o xform do grupo, não a malha local."""
    from types import SimpleNamespace

    from PySide6.QtGui import QMatrix4x4

    from trazomob.ui.material_editor_dialog import MaterialEditorDialog

    scene = Scene()
    mesh = Mesh()
    face = mesh.add_face([QVector3D(0, 0, 0), QVector3D(1, 0, 0),
                          QVector3D(1, 1, 0)])
    face.attrs = {"mat": "Vermelho", "color": (1.0, 0.0, 0.0)}
    group = Group(mesh, name="Bloco")
    moved = QMatrix4x4()
    moved.translate(10.0, 0.0, 0.0)
    group.xform = moved
    scene.groups.append(group)

    class Viewport:
        def world_to_pixel(self, point):
            return (point.x(), point.y())

    class Painter:
        def __init__(self):
            self.polygons = []

        def save(self):
            pass

        def restore(self):
            pass

        def setRenderHint(self, *_args):
            pass

        def setPen(self, *_args):
            pass

        def setBrush(self, *_args):
            pass

        def drawPolygon(self, polygon):
            self.polygons.append(polygon)

    dialog = SimpleNamespace(_highlight_active=True, _current_mat="Vermelho",
                             scene=scene, _group=None)
    painter = Painter()
    MaterialEditorDialog._draw_material_highlight(dialog, Viewport(), painter)

    assert len(painter.polygons) == 1
    xs = [point.x() for point in painter.polygons[0]]
    assert min(xs) == pytest.approx(10.0)
    assert max(xs) == pytest.approx(11.0)

    # Aberto sobre um grupo específico: mesma posição, sem varrer a cena inteira.
    dialog._group = group
    group_painter = Painter()
    MaterialEditorDialog._draw_material_highlight(dialog, Viewport(), group_painter)
    assert len(group_painter.polygons) == 1
    xs = [point.x() for point in group_painter.polygons[0]]
    assert min(xs) == pytest.approx(10.0)


def test_picker_yellow_highlight_uses_world_xform_and_dialog_skips_blue_overlay(qapp):
    """O diálogo não instala o destaque azul global; apenas o conta-gotas destaca em amarelo."""
    from types import SimpleNamespace

    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QMatrix4x4

    from trazomob.interaction.material_picker_tool import MaterialPickerTool
    from trazomob.ui.material_editor_dialog import MaterialEditorDialog

    scene = Scene()
    mesh = Mesh()
    face = mesh.add_face([QVector3D(0, 0, 0), QVector3D(1, 0, 0),
                          QVector3D(1, 1, 0)])
    face.attrs = {"mat": "Carvalho", "color": (0.7, 0.5, 0.3)}
    group = Group(mesh, name="Bloco")
    moved = QMatrix4x4()
    moved.translate(5.0, 2.0, 0.0)
    group.xform = moved
    scene.groups.append(group)

    class FakeViewport:
        def __init__(self):
            self._ext_overlays = []
            self.hovered = "sentinel"
            self.updated = 0

        def pick_face_placement(self, _x, _y):
            return face, group

        def pick_face_any(self, _x, _y):
            return face, group

        def set_hover(self, target):
            self.hovered = target

        def update(self):
            self.updated += 1

        def world_to_pixel(self, point):
            return (point.x(), point.y())

    class Painter:
        def __init__(self):
            self.polygons = []

        def save(self):
            pass

        def restore(self):
            pass

        def setRenderHint(self, *_args):
            pass

        def setPen(self, *_args):
            pass

        def setBrush(self, *_args):
            pass

        def drawPolygon(self, polygon):
            self.polygons.append(polygon)

    vp = FakeViewport()
    dlg = MaterialEditorDialog(scene, viewport=vp)
    try:
        assert dlg._draw_material_highlight not in vp._ext_overlays
        assert vp.updated == 0
    finally:
        dlg.close()

    tool = MaterialPickerTool()
    tool.on_hover(SimpleNamespace(viewport=vp, screen=QPointF(10.0, 10.0)))
    assert vp.hovered is None

    painter = Painter()
    tool._draw_hover_overlay(vp, painter)
    assert len(painter.polygons) == 1
    xs = [pt.x() for pt in painter.polygons[0]]
    ys = [pt.y() for pt in painter.polygons[0]]
    assert min(xs) == pytest.approx(5.0)
    assert max(xs) == pytest.approx(6.0)
    assert min(ys) == pytest.approx(2.0)
    assert max(ys) == pytest.approx(3.0)


def test_material_editor_non_modal_owners_filter_and_picker_restore(qapp):
    """Identifica donos das texturas, filtra, seleciona no 3D e abre não-modal."""
    from types import SimpleNamespace

    from PySide6.QtCore import QPointF

    from trazomob.interaction.material_picker_tool import MaterialPickerTool
    from trazomob.ui.material_editor_dialog import open_material_editor

    scene = Scene()
    shared_mesh = Mesh()
    face = shared_mesh.add_face([QVector3D(0, 0, 0), QVector3D(1, 0, 0), QVector3D(1, 1, 0)])
    face.attrs = {"mat": "Tecido_Linho", "color": (0.8, 0.78, 0.72)}

    sofa = Group(shared_mesh, name="Sofá Sala")
    poltrona = Group(shared_mesh, name="Poltrona")
    scene.groups.extend([sofa, poltrona])

    class FakeSelectTool:
        name = "Select"

    class FakeViewport:
        def __init__(self):
            self.scene = scene
            self._ext_overlays = []
            self.active_tool = FakeSelectTool()
            self.updated = 0

        def set_active_tool(self, tool):
            self.active_tool = tool
            if hasattr(tool, "on_activate"):
                tool.on_activate(self)

        def pick_face_any(self, _x, _y):
            return face, sofa

        def set_hover(self, _target):
            pass

        def update(self):
            self.updated += 1

    vp = FakeViewport()
    dlg = open_material_editor(viewport=vp)
    assert dlg is not None
    try:
        assert dlg.isModal() is False
        assert dlg.btn_pick_3d.isVisibleTo(dlg) is True
        assert dlg.btn_select_owner.isVisibleTo(dlg) is True

        item_data = dlg._scene_materials[0]
        assert item_data["owners"] == ["Sofá Sala", "Poltrona"]
        assert item_data["owner_groups"] == [sofa, poltrona]
        assert "Sofá Sala" in dlg.lbl_prev_owners.text()

        # Filtro por nome do objeto dono
        dlg.txt_filter.setText("Poltrona")
        assert dlg.list_mats.item(0).isHidden() is False
        dlg.txt_filter.setText("Inexistente")
        assert dlg.list_mats.item(0).isHidden() is True

        # Botao selecionar objeto na cena
        dlg._select_owner_in_scene()
        assert set(scene.selection) == {sofa, poltrona}

        # Conta-gotas ativado pelo diálogo restaura ferramenta anterior após o clique e seleciona o material
        dlg._activate_picker_tool()
        assert isinstance(vp.active_tool, MaterialPickerTool)
        vp.active_tool.on_click(SimpleNamespace(viewport=vp, screen=QPointF(5.0, 5.0)))
        assert isinstance(vp.active_tool, FakeSelectTool)
        assert dlg.list_mats.item(0).isHidden() is False
    finally:
        dlg.close()


def test_material_editor_opacity_slider_updates_overrides_and_scene(qapp, tmp_path):
    """Slider de opacidade no Editor PBR lê, grava override e sincroniza com a cena 3D."""
    from trazomob.ui.material_editor_dialog import MaterialEditorDialog

    tex_file = tmp_path / "voil.png"
    tex_file.write_bytes(b"\x89PNG\r\n\x1a\n")

    scene = Scene()
    m_col = Mesh()
    f_col = m_col.add_face([QVector3D(0, 0, 0), QVector3D(1, 0, 0), QVector3D(1, 1, 0)])
    f_col.attrs = {"mat": "Vidro_Cor", "color": (0.4, 0.6, 0.7), "opacity": 0.7}
    g_col = Group(m_col, name="Divisoria")

    m_tex = Mesh()
    f_tex = m_tex.add_face([QVector3D(0, 0, 1), QVector3D(1, 0, 1), QVector3D(1, 1, 1)])
    f_tex.attrs = {"mat": "Cortina_Voil", "texture": {"path": str(tex_file), "sw": 1.0, "sh": 1.0}}
    g_tex = Group(m_tex, name="Cortina")
    scene.groups.extend([g_col, g_tex])

    dlg = MaterialEditorDialog(scene)
    try:
        assert dlg.select_material_by_name("Vidro_Cor") is True
        assert dlg.sl_opacity.value() == 70
        assert dlg.lbl_opacity_val.text() == "70%"

        dlg.sl_opacity.setValue(40)
        assert dlg.get_overrides()["Vidro_Cor"]["opacity"] == pytest.approx(0.4)
        assert dlg.lbl_opacity_val.text() == "40%"

        assert dlg.select_material_by_name("Cortina_Voil") is True
        assert dlg.sl_opacity.value() == 100
        dlg.cb_type.setCurrentIndex(dlg.cb_type.findData("tecido"))
        dlg.sl_opacity.setValue(55)
        ov_tex = dlg.get_overrides()["Cortina_Voil"]
        assert ov_tex["type"] == "tecido"
        assert ov_tex["opacity"] == pytest.approx(0.55)

        dlg._save_and_close()
    finally:
        dlg.close()

    assert f_col.attrs["opacity"] == pytest.approx(0.4)
    assert f_tex.attrs["opacity"] == pytest.approx(0.55)
    assert scene.plugin_data["trazomob"]["material_overrides"]["Cortina_Voil"]["opacity"] == pytest.approx(0.55)


def test_photoreal_render_applies_opacity_override_to_color_and_texture(monkeypatch):
    """photoreal_render aplica cfg['opacity'] em materiais sólidos e texturizados (PNG com alpha)."""
    import importlib.util
    import sys
    from pathlib import Path
    from types import SimpleNamespace

    class _Socket:
        def __init__(self, name, node):
            self.name = name
            self.node = node
            self.default_value = (0.8, 0.8, 0.8, 1.0) if name == "Base Color" else 1.0
            self.links = []

    class _Nodes(list):
        def new(self, bl_idname):
            node = _Node(bl_idname)
            self.append(node)
            return node

    class _Links(list):
        def new(self, out_sock, in_sock):
            link = SimpleNamespace(from_socket=out_sock, to_socket=in_sock)
            self.append(link)
            in_sock.links.append(link)
            return link

        def remove(self, link):
            if link in self:
                super().remove(link)
            if link in link.to_socket.links:
                link.to_socket.links.remove(link)

    class _Node:
        def __init__(self, bl_idname):
            self.bl_idname = bl_idname
            self.type = (
                "BSDF_PRINCIPLED"
                if bl_idname == "ShaderNodeBsdfPrincipled"
                else ("TEX_IMAGE" if bl_idname == "ShaderNodeTexImage" else bl_idname)
            )
            self.operation = None
            self.inputs = {
                n: _Socket(n, self)
                for n in ("Base Color", "Roughness", "Metallic", "Specular IOR Level", "Normal", "Alpha", "Radius", 0, 1)
            }
            self.outputs = {n: _Socket(n, self) for n in ("BSDF", "Normal", "Color", "Alpha", 0)}

    class _Material:
        def __init__(self, name):
            self.name = name
            self.blend_method = "OPAQUE"
            self.shadow_method = "OPAQUE"
            self.use_backface_culling = True
            self.node_tree = SimpleNamespace(nodes=_Nodes(), links=_Links())
            self.node_tree.nodes.new("ShaderNodeBsdfPrincipled")

    mat_col = _Material("Acrilico_Azul")
    mat_tex = _Material("Cortina_Voil")
    mat_tex.node_tree.nodes.new("ShaderNodeTexImage")

    fake_bpy = SimpleNamespace(
        data=SimpleNamespace(materials=[mat_col, mat_tex]),
        context=SimpleNamespace(scene=SimpleNamespace(objects=[])),
    )
    monkeypatch.setitem(sys.modules, "bpy", fake_bpy)
    monkeypatch.setitem(sys.modules, "bmesh", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "mathutils", SimpleNamespace(Matrix=object, Vector=object))

    script_path = Path(__file__).resolve().parents[1] / "blender_scripts" / "photoreal_render.py"
    spec = importlib.util.spec_from_file_location("_test_photoreal_opacity", script_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)

    mod.setup_photoreal_materials(
        use_bevel=False,
        material_overrides={
            "Acrilico_Azul": {"type": "plastico", "roughness": 0.25, "specular": 0.5, "bump": 0.005, "opacity": 0.4},
            "Cortina_Voil": {"type": "auto", "roughness": 0.35, "specular": 0.5, "bump": 0.02, "opacity": 0.55},
        },
    )

    bsdf_col = mat_col.node_tree.nodes[0]
    assert bsdf_col.inputs["Alpha"].default_value == pytest.approx(0.4)
    assert mat_col.blend_method == "BLEND"
    assert mat_col.use_backface_culling is False

    mult_nodes = [n for n in mat_tex.node_tree.nodes if n.bl_idname == "ShaderNodeMath"]
    assert len(mult_nodes) == 1
    assert mult_nodes[0].operation == "MULTIPLY"
    assert mult_nodes[0].inputs[1].default_value == pytest.approx(0.55)
    assert mat_tex.blend_method == "BLEND"
    assert mat_tex.use_backface_culling is False
