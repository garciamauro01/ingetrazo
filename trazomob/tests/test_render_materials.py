# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes do mapeamento de presets procedurais de render por material."""
from __future__ import annotations

import pytest
from PySide6.QtGui import QVector3D
from PySide6.QtWidgets import QApplication

from core.group import Group
from core.mesh import Mesh
from trazomob.domain.render_materials import (
    RENDER_PRESET_IDS,
    extract_group_material_slots,
    get_group_render_materials,
    set_group_render_materials,
)
from trazomob.ui.render_materials_dialog import RenderMaterialsDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _make_face_mesh(color=None, tex_path=None):
    m = Mesh()
    f = m.add_face([
        QVector3D(0, 0, 0),
        QVector3D(1, 0, 0),
        QVector3D(1, 1, 0),
        QVector3D(0, 1, 0),
    ])
    if color is not None:
        f.attrs["color"] = color
    if tex_path is not None:
        f.attrs["texture"] = {"path": tex_path}
    return m


def test_extract_e_mapeamento_multiplos_materiais(qapp):
    root = Group(Mesh(), name="Lava e Seca")
    g_corpo = Group(_make_face_mesh(color=(0.9, 0.9, 0.9)), name="Corpo")
    g_vidro = Group(_make_face_mesh(color=(0.27, 0.28, 0.33)), name="Visor")
    g_estampa = Group(_make_face_mesh(tex_path="C:/tmp/persa.jpg"), name="Tapete")
    root.children = [g_corpo, g_vidro, g_estampa]

    slots = extract_group_material_slots(root)
    keys = {s["key"] for s in slots}
    assert "mat_90_90_90" in keys
    assert "mat_27_28_33" in keys
    assert "tex:C:/tmp/persa.jpg" in keys

    set_group_render_materials(root, {
        "mat_90_90_90": "aco_escovado",
        "mat_27_28_33": "vidro_fume",
        "tex:C:/tmp/persa.jpg": "carpete_felpudo",
        "mat_default": "original",  # 'original' não precisa ser persistido
    })
    saved = get_group_render_materials(root)
    assert saved == {
        "mat_90_90_90": "aco_escovado",
        "mat_27_28_33": "vidro_fume",
        "tex:C:/tmp/persa.jpg": "carpete_felpudo",
    }

    dlg = RenderMaterialsDialog(root)
    assert len(dlg._combos) == 3
    assert dlg._combos["mat_90_90_90"].currentData() == "aco_escovado"
    assert "branco_esmaltado" in RENDER_PRESET_IDS


def test_material_editor_preserves_deferred_mesh_and_updates_without_reloading(qapp, tmp_path, monkeypatch):
    from PySide6.QtGui import QMatrix4x4

    from core import _native
    from core.mesh import DeferredMesh
    from core.scene import Scene
    from formats import igz
    from trazomob.ui.material_editor_dialog import (
        MaterialEditorDialog,
        extract_group_materials,
        extract_scene_materials,
    )

    monkeypatch.setattr(_native, "wanted", lambda: True)

    src_scene = Scene()
    g_paint = Group(_make_face_mesh(), name="Parede Pintada")
    g_paint.material = {"mat": "Suvinil_Branco", "color": (0.95, 0.95, 0.95)}

    m_col = _make_face_mesh(color=(0.8, 0.2, 0.1))
    g_col = Group(m_col, name="Cadeira")
    g_col.xform = QMatrix4x4()
    g_col.xform.translate(QVector3D(2.0, 0.0, 0.0))

    src_scene.groups.extend([g_paint, g_col])
    igz_path = tmp_path / "cena.igz"
    igz.save_scene(src_scene, igz_path, binary=True)

    loaded = Scene()
    igz.load_into(loaded, igz_path)

    assert type(loaded.groups[0].mesh) is DeferredMesh
    assert type(loaded.groups[1].mesh) is DeferredMesh

    scene_mats = extract_scene_materials(loaded)
    names = {m["name"] for m in scene_mats}
    assert "Suvinil_Branco" in names
    assert "Cor #CC3319" in names

    grp_mats = extract_group_materials(loaded.groups[1])
    assert [m["name"] for m in grp_mats] == ["Cor #CC3319"]

    # Extrair materiais nao pode materializar as DeferredMesh
    assert type(loaded.groups[0].mesh) is DeferredMesh
    assert type(loaded.groups[1].mesh) is DeferredMesh

    dlg = MaterialEditorDialog(loaded)
    try:
        assert dlg.list_mats.count() == len(scene_mats)
        assert dlg.select_material_by_name("Cor #CC3319") is True

        loops = dlg._get_highlight_loops("Cor #CC3319")
        assert len(loops) == 1
        assert min(p.x() for p in loops[0]) == pytest.approx(2.0)
        assert max(p.x() for p in loops[0]) == pytest.approx(3.0)
        assert type(loaded.groups[1].mesh) is DeferredMesh

        # Segunda consulta usa o cache
        assert dlg._get_highlight_loops("Cor #CC3319") is loops

        # Trocar shader atualiza rotulo da linha e overrides sem recriar a lista
        first_item = dlg.list_mats.currentItem()
        idx_metal = dlg.cb_type.findData("metal")
        dlg.cb_type.setCurrentIndex(idx_metal)
        assert dlg.list_mats.currentItem() is first_item
        assert "✨ " in first_item.text()
        assert dlg.get_overrides()["Cor #CC3319"]["type"] == "metal"

        # Reset restaura o padrao e remove override
        dlg._reset_current_material()
        assert "Cor #CC3319" not in dlg.get_overrides()
        assert "▫️ " in first_item.text()
    finally:
        dlg.close()


def test_tapete_carpete_felpudo_e_sem_pelos_pbr_e_blender(qapp, monkeypatch):
    """Configura tapete/carpete como felpudo ou sem pelos no editor PBR e no shader Blender."""
    import importlib.util
    import sys
    from pathlib import Path
    from types import SimpleNamespace

    from core.scene import Scene
    from trazomob.ui.material_editor_dialog import (
        MATERIAL_PBR_TYPES,
        MaterialEditorDialog,
    )

    assert "tapete" in MATERIAL_PBR_TYPES
    subtypes = MATERIAL_PBR_TYPES["tapete"]["subtypes"]
    shaggy_sub = next(s for s in subtypes if "Felpudo" in s and "Pelo Alto" in s)
    flat_sub = next(s for s in subtypes if "Sem Pelos" in s and "Liso" in s)
    boucle_sub = next(s for s in subtypes if "Bouclê" in s)

    scene = Scene()
    tapete_mesh = _make_face_mesh(color=(0.75, 0.72, 0.66))
    tapete_mesh.faces[0].attrs["mat"] = "Tapete_Sala"
    g_tapete = Group(tapete_mesh, name="Tapete")

    outro_mesh = _make_face_mesh(color=(0.2, 0.2, 0.2))
    outro_mesh.faces[0].attrs["mat"] = "Carpete_Escritorio"
    g_outro = Group(outro_mesh, name="Escritorio")
    scene.groups.extend([g_tapete, g_outro])

    dlg = MaterialEditorDialog(scene)
    try:
        assert dlg.select_material_by_name("Tapete_Sala") is True
        idx_tapete = dlg.cb_type.findData("tapete")
        assert idx_tapete >= 0
        dlg.cb_type.setCurrentIndex(idx_tapete)

        assert dlg.get_overrides()["Tapete_Sala"]["type"] == "tapete"
        assert dlg.get_overrides()["Tapete_Sala"]["sub_type"] == shaggy_sub
        assert "Felpudo" in dlg.list_mats.currentItem().text()

        # Troca para opção sem pelos e valida manutenção ao navegar entre materiais
        idx_flat = dlg.cb_subtype.findText(flat_sub)
        assert idx_flat >= 0
        dlg.cb_subtype.setCurrentIndex(idx_flat)
        assert dlg.get_overrides()["Tapete_Sala"]["sub_type"] == flat_sub
        assert "Sem Pelos" in dlg.list_mats.currentItem().text()

        assert dlg.select_material_by_name("Carpete_Escritorio") is True
        assert dlg.select_material_by_name("Tapete_Sala") is True
        assert dlg.cb_type.currentData() == "tapete"
        assert dlg.cb_subtype.currentText() == flat_sub

        # Volta para felpudo em Tapete_Sala e salva
        dlg.cb_subtype.setCurrentIndex(dlg.cb_subtype.findText(shaggy_sub))
        dlg._save_and_close()
    finally:
        dlg.close()

    assert g_tapete.ext["trazomob_render_materials"]["Tapete_Sala"]["sub_type"] == shaggy_sub
    assert scene.plugin_data["trazomob"]["material_overrides"]["Tapete_Sala"]["type"] == "tapete"

    # Valida no script headless do Blender (photoreal_render.py) com mock de bpy
    class _FakeSocket:
        def __init__(self, name, node):
            self.name = name
            self.node = node
            self.id_data = node.id_data
            self.default_value = (0.8, 0.8, 0.8, 1.0) if name == "Base Color" else 0.0
            self.links = []

    class _FakeNodes(list):
        def __init__(self, tree):
            super().__init__()
            self._tree = tree

        def new(self, bl_idname):
            node = _FakeNode(bl_idname, self._tree)
            self.append(node)
            return node

    class _FakeLinks(list):
        def new(self, out_sock, in_sock):
            link = (out_sock, in_sock)
            self.append(link)
            in_sock.links.append(link)
            return link

        def remove(self, link):
            if link in self:
                super().remove(link)
            if link in link[1].links:
                link[1].links.remove(link)

    class _FakeNode:
        def __init__(self, bl_idname, tree):
            self.bl_idname = bl_idname
            self.type = "BSDF_PRINCIPLED" if bl_idname == "ShaderNodeBsdfPrincipled" else bl_idname
            self.id_data = tree
            self.inputs = {
                name: _FakeSocket(name, self)
                for name in (
                    "Base Color", "Roughness", "Metallic", "Specular IOR Level",
                    "Sheen Weight", "Sheen Roughness", "Normal", "Radius",
                    "Height", "Strength", "Scale", "Detail",
                )
            }
            self.outputs = {
                name: _FakeSocket(name, self)
                for name in ("BSDF", "Normal", "Fac", "Distance", "Color")
            }

    class _FakeMaterial:
        def __init__(self, name):
            self.name = name
            self.node_tree = SimpleNamespace()
            self.node_tree.nodes = _FakeNodes(self.node_tree)
            self.node_tree.links = _FakeLinks()
            self.node_tree.nodes.new("ShaderNodeBsdfPrincipled")

    class _FakeModifiers(list):
        def __init__(self, owner):
            super().__init__()
            self._owner = owner

        def new(self, name, mod_type):
            ps_settings = SimpleNamespace(material=1)
            psys = SimpleNamespace(settings=ps_settings)
            mod = SimpleNamespace(name=name, type=mod_type, particle_system=psys)
            self.append(mod)
            if mod_type == "PARTICLE_SYSTEM":
                self._owner.particle_systems.append(psys)
            return mod

    class _FakeVertexGroups:
        def __init__(self):
            self.groups = []

        def new(self, name):
            vg = SimpleNamespace(name=name, added=[])
            vg.add = lambda verts, weight, mode: vg.added.append((list(verts), weight, mode))
            self.groups.append(vg)
            return vg

    class _FakeMeshObj:
        def __init__(self, name, materials):
            self.name = name
            self.type = "MESH"
            self.scale = (1.0, 1.0, 1.0)
            self.material_slots = [SimpleNamespace(material=m) for m in materials]
            self.particle_systems = []
            self.modifiers = _FakeModifiers(self)
            self.vertex_groups = _FakeVertexGroups()
            self.data = SimpleNamespace(
                polygons=[
                    SimpleNamespace(material_index=idx, vertices=[idx * 4 + i for i in range(4)])
                    for idx in range(len(materials))
                ]
            )

    mat_shaggy = _FakeMaterial("Tapete_Felpudo")
    mat_flat = _FakeMaterial("Tapete_Sisal")
    mat_boucle = _FakeMaterial("Carpete_Boucle")
    mat_borda = _FakeMaterial("Borda_Algodao")

    obj_shaggy = _FakeMeshObj("Obj_Tapete_Sala", [mat_borda, mat_shaggy])
    obj_flat = _FakeMeshObj("Obj_Tapete_Sisal", [mat_flat])
    obj_boucle = _FakeMeshObj("Obj_Carpete_Boucle", [mat_boucle])

    fake_bpy = SimpleNamespace(
        data=SimpleNamespace(materials=[mat_borda, mat_shaggy, mat_flat, mat_boucle]),
        context=SimpleNamespace(
            scene=SimpleNamespace(
                objects=[obj_shaggy, obj_flat, obj_boucle],
                render=SimpleNamespace(hair_type="STRAND"),
            )
        ),
    )

    monkeypatch.setitem(sys.modules, "bpy", fake_bpy)
    monkeypatch.setitem(sys.modules, "bmesh", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "mathutils", SimpleNamespace(Matrix=object, Vector=object))

    script_path = Path(__file__).resolve().parents[1] / "blender_scripts" / "photoreal_render.py"
    spec = importlib.util.spec_from_file_location("_test_photoreal_render", script_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)

    mod.setup_photoreal_materials(
        use_bevel=False,
        material_overrides={
            "Tapete_Felpudo": {"type": "tapete", "sub_type": shaggy_sub, "roughness": 0.88, "specular": 0.08, "bump": 0.06},
            "Tapete_Sisal": {"type": "tapete", "sub_type": flat_sub, "roughness": 0.90, "specular": 0.06, "bump": 0.03},
            "Carpete_Boucle": {"type": "tapete", "sub_type": boucle_sub, "roughness": 0.85, "specular": 0.08, "bump": 0.025},
        },
    )

    # Felpudo: cria Hair particles no slot 2 (index 1 -> material=2) e vertex group apenas das faces do tapete
    assert len(obj_shaggy.particle_systems) == 1
    ps_shaggy = obj_shaggy.particle_systems[0].settings
    assert ps_shaggy.type == "HAIR"
    assert ps_shaggy.hair_length == pytest.approx(0.06 * 0.35)
    assert ps_shaggy.material == 2
    assert ps_shaggy.vertex_group_density == "TrazoTapete_Area_2"
    assert obj_shaggy.vertex_groups.groups[0].added[0][0] == [4, 5, 6, 7]
    bsdf_shaggy = mat_shaggy.node_tree.nodes[0]
    assert bsdf_shaggy.inputs["Sheen Weight"].default_value == pytest.approx(0.95)

    # Sem pelos (Sisal/Liso): não cria partículas, apenas shader de trama e sheen mais baixo
    assert len(obj_flat.particle_systems) == 0
    bsdf_flat = mat_flat.node_tree.nodes[0]
    assert bsdf_flat.inputs["Sheen Weight"].default_value == pytest.approx(0.65)
    assert any(n.bl_idname == "ShaderNodeTexNoise" for n in mat_flat.node_tree.nodes)

    # Sem pelos (Bouclê): não cria partículas e usa textura Voronoi para trama fechada
    assert len(obj_boucle.particle_systems) == 0
    assert any(n.bl_idname == "ShaderNodeTexVoronoi" for n in mat_boucle.node_tree.nodes)


def test_render_dialog_shows_wait_cursor_immediately_and_restores(qapp, tmp_path, monkeypatch):
    """Ao iniciar o render, o diálogo mostra WaitCursor imediatamente e restaura ao concluir ou cancelar."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from core import _native
    from core.camera import OrbitCamera
    from core.mesh import DeferredMesh
    from core.scene import Scene
    from formats import igz
    from trazomob.render.dialog import TrazoMobRenderDialog

    while QApplication.overrideCursor() is not None:
        QApplication.restoreOverrideCursor()

    monkeypatch.setattr(_native, "wanted", lambda: True)
    src_scene = Scene()
    src_scene.groups.append(Group(_make_face_mesh(color=(0.8, 0.8, 0.8)), name="Balcao"))
    igz_path = tmp_path / "balcao.igz"
    igz.save_scene(src_scene, igz_path, binary=True)

    scene = Scene()
    igz.load_into(scene, igz_path)
    assert type(scene.groups[0].mesh) is DeferredMesh

    vp = pytest.importorskip("PySide6.QtWidgets").QWidget()
    vp.scene = scene
    vp.camera = OrbitCamera()

    dlg = TrazoMobRenderDialog(vp)
    try:
        captured = {}

        def _fake_start_render(**_kwargs):
            cur = QApplication.overrideCursor()
            captured["cursor"] = cur.shape() if cur is not None else None
            captured["max"] = dlg.progress_bar.maximum()
            captured["status"] = dlg.lbl_status.text()
            return True

        monkeypatch.setattr(dlg._engine, "start_render", _fake_start_render)
        dlg._start_render()
        assert captured["cursor"] == Qt.WaitCursor
        assert captured["max"] == 0
        assert "Preparando" in captured["status"]
        assert QApplication.overrideCursor() is not None

        dlg._cancel_render()
        assert QApplication.overrideCursor() is None
        assert dlg.btn_render.isEnabled() is True

        # Falha também restaura o cursor
        dlg._start_render()
        assert QApplication.overrideCursor() is not None
        monkeypatch.setattr("trazomob.render.dialog.QMessageBox.warning", lambda *a, **kw: None)
        dlg._on_failed("erro simulado")
        assert QApplication.overrideCursor() is None
    finally:
        dlg.close()
        while QApplication.overrideCursor() is not None:
            QApplication.restoreOverrideCursor()

    # Engine preserva DeferredMesh sem clonar malha quando não há faces ocultas/tag de parede
    from trazomob.render.engine import TrazoMobRenderEngine
    eng = TrazoMobRenderEngine()
    monkeypatch.setattr(eng, "get_blender_executable", lambda: "C:/fake/blender.exe")
    seen_scenes = []
    monkeypatch.setattr("formats.gltf.save_glb", lambda clean_sc, _p: seen_scenes.append(clean_sc))

    class _FakeProc:
        def __init__(self, *_a):
            self.readyReadStandardOutput = type("_Sig", (), {"connect": lambda *_x: None})()
            self.readyReadStandardError = type("_Sig", (), {"connect": lambda *_x: None})()
            self.finished = type("_Sig", (), {"connect": lambda *_x: None})()

        def setProcessEnvironment(self, *_a):
            pass

        def start(self, *_a):
            pass

    monkeypatch.setattr("PySide6.QtCore.QProcess", _FakeProc)
    assert eng.start_render(scene, vp.camera) is True
    assert len(seen_scenes) == 1
    assert seen_scenes[0].groups[0] is scene.groups[0]
    assert type(scene.groups[0].mesh) is DeferredMesh


def test_photoreal_emissive_tv_screen_and_glb_name_matching(monkeypatch):
    """Casamento GLB sanitizado ('[Color C02]' -> 'Color_C02', '*2' -> 'm_2_2', 'mat7' via imagem)
    e shader 'Painel Iluminado / TV Ligada' preservando textura + gerando AreaLight para Cycles/EEVEE."""
    import importlib.util
    import math
    import sys
    from pathlib import Path
    from types import SimpleNamespace

    class _FakeVec:
        def __init__(self, xyz=(0.0, 0.0, 0.0)):
            if isinstance(xyz, _FakeVec):
                self.x, self.y, self.z = xyz.x, xyz.y, xyz.z
            else:
                self.x, self.y, self.z = float(xyz[0]), float(xyz[1]), float(xyz[2])

        def __add__(self, other):
            return _FakeVec((self.x + other.x, self.y + other.y, self.z + other.z))

        def __sub__(self, other):
            return _FakeVec((self.x - other.x, self.y - other.y, self.z - other.z))

        def __neg__(self):
            return _FakeVec((-self.x, -self.y, -self.z))

        def __mul__(self, s):
            return _FakeVec((self.x * s, self.y * s, self.z * s))

        def __truediv__(self, s):
            return _FakeVec((self.x / s, self.y / s, self.z / s))

        def dot(self, other):
            return self.x * other.x + self.y * other.y + self.z * other.z

        def cross(self, other):
            return _FakeVec((
                self.y * other.z - self.z * other.y,
                self.z * other.x - self.x * other.z,
                self.x * other.y - self.y * other.x,
            ))

        @property
        def length(self):
            return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

        def copy(self):
            return _FakeVec((self.x, self.y, self.z))

        def normalize(self):
            ln = self.length
            if ln > 1e-12:
                self.x /= ln
                self.y /= ln
                self.z /= ln
            return self

        def normalized(self):
            return self.copy().normalize()

    class _FakeMatrix:
        def __init__(self, rows=None):
            if rows is None:
                self.rows = (
                    (1.0, 0.0, 0.0, 0.0),
                    (0.0, 1.0, 0.0, 0.0),
                    (0.0, 0.0, 1.0, 0.0),
                    (0.0, 0.0, 0.0, 1.0),
                )
            else:
                norm_rows = []
                for row in rows:
                    if isinstance(row, _FakeVec):
                        norm_rows.append((row.x, row.y, row.z))
                    else:
                        norm_rows.append(tuple(row))
                self.rows = tuple(norm_rows)

        @classmethod
        def Translation(cls, vec):
            return cls((
                (1.0, 0.0, 0.0, vec.x),
                (0.0, 1.0, 0.0, vec.y),
                (0.0, 0.0, 1.0, vec.z),
                (0.0, 0.0, 0.0, 1.0),
            ))

        def to_3x3(self):
            return self

        def transposed(self):
            r = self.rows
            return _FakeMatrix(tuple(tuple(r[j][i] for j in range(len(r))) for i in range(len(r[0]))))

        def to_4x4(self):
            r = self.rows
            if len(r) == 4:
                return self
            return _FakeMatrix((
                (r[0][0], r[0][1], r[0][2], 0.0),
                (r[1][0], r[1][1], r[1][2], 0.0),
                (r[2][0], r[2][1], r[2][2], 0.0),
                (0.0, 0.0, 0.0, 1.0),
            ))

        def __matmul__(self, other):
            if isinstance(other, _FakeVec):
                r = self.rows
                return _FakeVec((
                    r[0][0] * other.x + r[0][1] * other.y + r[0][2] * other.z + (r[0][3] if len(r[0]) > 3 else 0.0),
                    r[1][0] * other.x + r[1][1] * other.y + r[1][2] * other.z + (r[1][3] if len(r[1]) > 3 else 0.0),
                    r[2][0] * other.x + r[2][1] * other.y + r[2][2] * other.z + (r[2][3] if len(r[2]) > 3 else 0.0),
                ))
            a, b = self.rows, other.rows
            return _FakeMatrix(tuple(
                tuple(sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4))
                for i in range(4)
            ))

    class _FakeSocket:
        def __init__(self, name, node):
            self.name = name
            self.node = node
            self.id_data = node.id_data
            self.default_value = (0.0, 0.0, 0.0, 1.0) if "Color" in name else 0.0
            self.links = []

    class _FakeNodes(list):
        def __init__(self, tree):
            super().__init__()
            self._tree = tree

        def new(self, bl_idname):
            node = _FakeNode(bl_idname, self._tree)
            self.append(node)
            return node

    class _FakeLinks(list):
        def new(self, out_sock, in_sock):
            link = (out_sock, in_sock)
            self.append(link)
            in_sock.links.append(link)
            return link

        def remove(self, link):
            if link in self:
                super().remove(link)
            if link in link[1].links:
                link[1].links.remove(link)

    class _FakeNode:
        def __init__(self, bl_idname, tree, image_name=None):
            self.bl_idname = bl_idname
            self.type = (
                "BSDF_PRINCIPLED"
                if bl_idname == "ShaderNodeBsdfPrincipled"
                else ("TEX_IMAGE" if bl_idname == "ShaderNodeTexImage" else bl_idname)
            )
            self.id_data = tree
            self.image = SimpleNamespace(name=image_name, filepath=image_name) if image_name else None
            self.inputs = {
                n: _FakeSocket(n, self)
                for n in (
                    "Base Color", "Roughness", "Metallic", "Specular IOR Level",
                    "Coat Weight", "Coat Roughness", "Emission Color", "Emission Strength",
                    "Sheen Weight", "Sheen Roughness", "Normal", "Radius", "Height",
                    "Strength", "Scale", "Detail",
                )
            }
            self.outputs = {n: _FakeSocket(n, self) for n in ("BSDF", "Normal", "Fac", "Distance", "Color")}

    class _FakeMaterial(dict):
        def __init__(self, name, image_name=None):
            super().__init__()
            self.name = name
            self.node_tree = SimpleNamespace()
            self.node_tree.nodes = _FakeNodes(self.node_tree)
            self.node_tree.links = _FakeLinks()
            self.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
            if image_name:
                self.node_tree.nodes.append(_FakeNode("ShaderNodeTexImage", self.node_tree, image_name=image_name))

    mat_tv = _FakeMaterial("Color_C02", image_name="a841e4b51847c9fb-mjm.jpg")
    mat_star = _FakeMaterial("m_2_2")
    mat_anon_tex = _FakeMaterial("mat7", image_name="1719b0e96fd4d91d-marmore_calacatta.jpg")
    mat_panel_solid = _FakeMaterial("Painel_Backlight")

    tv_verts = [
        SimpleNamespace(co=(0.0, -0.6, 0.9)),
        SimpleNamespace(co=(0.0, 0.6, 0.9)),
        SimpleNamespace(co=(0.0, 0.6, 1.6)),
        SimpleNamespace(co=(0.0, -0.6, 1.6)),
    ]
    tv_poly = SimpleNamespace(
        material_index=0,
        area=0.84,
        normal=(1.0, 0.0, 0.0),
        center=(0.0, 0.0, 1.25),
        vertices=[0, 1, 2, 3],
    )
    tv_obj = SimpleNamespace(
        name="TV_Sala",
        type="MESH",
        matrix_world=_FakeMatrix(),
        material_slots=[SimpleNamespace(material=mat_tv)],
        data=SimpleNamespace(polygons=[tv_poly], vertices=tv_verts),
    )

    created_lights = []
    created_objs = []

    def _new_light(name, type="AREA"):
        lt = SimpleNamespace(name=name, type=type, shape="SQUARE", size=1.0, size_y=1.0, energy=0.0, color=(1.0, 1.0, 1.0))
        created_lights.append(lt)
        return lt

    def _new_obj(name, data):
        obj = SimpleNamespace(name=name, data=data, matrix_world=None, visible_camera=True, visible_glossy=True, visible_transmission=True)
        created_objs.append(obj)
        return obj

    fake_scene = SimpleNamespace(
        objects=[tv_obj],
        collection=SimpleNamespace(objects=SimpleNamespace(link=lambda _o: None)),
        ray_cast=lambda *_a, **_kw: (False, _FakeVec(), _FakeVec(), -1, None, None),
    )
    fake_bpy = SimpleNamespace(
        data=SimpleNamespace(
            materials=[mat_tv, mat_star, mat_anon_tex, mat_panel_solid],
            lights=SimpleNamespace(new=_new_light),
            objects=SimpleNamespace(new=_new_obj),
        ),
        context=SimpleNamespace(scene=fake_scene),
    )

    monkeypatch.setitem(sys.modules, "bpy", fake_bpy)
    monkeypatch.setitem(sys.modules, "bmesh", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "mathutils", SimpleNamespace(Matrix=_FakeMatrix, Vector=_FakeVec))

    script_path = Path(__file__).resolve().parents[1] / "blender_scripts" / "photoreal_render.py"
    spec = importlib.util.spec_from_file_location("_test_photoreal_emissive_tv", script_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)

    mod.setup_photoreal_materials(
        use_bevel=False,
        material_overrides={
            "[Color C02]": {
                "type": "emissivo",
                "sub_type": "Painel Iluminado / TV Ligada",
                "roughness": 0.1,
                "specular": 0.0,
                "bump": 0.0,
            },
            "*2": {"type": "tecido", "sub_type": "Linho / Trama Fina", "roughness": 0.85},
            "1719b0e96fd4d91d-marmore_calacatta": {"type": "madeira", "sub_type": "MDF Madeirado", "roughness": 0.32, "bump": 0.035},
            "Painel_Backlight": {"type": "emissivo", "sub_type": "Painel Iluminado / TV Ligada", "roughness": 0.1},
        },
    )

    # TV com textura: conecta a imagem no Emission Color, nao sobrescreve com cor solida e marca metadado
    bsdf_tv = mat_tv.node_tree.nodes[0]
    tex_tv = mat_tv.node_tree.nodes[1]
    assert bsdf_tv.inputs["Emission Strength"].default_value == pytest.approx(2.4)
    assert any(lnk[0] is tex_tv.outputs["Color"] and lnk[1] is bsdf_tv.inputs["Emission Color"] for lnk in mat_tv.node_tree.links)
    assert mat_tv.get("trazomob_emissive_kind") == "screen"

    # Casamento de '*2' -> 'm_2_2' (tecido) e 'mat7' via stem da imagem (madeira)
    assert mat_star.node_tree.nodes[0].inputs["Sheen Weight"].default_value == pytest.approx(0.85)
    assert any(n.bl_idname == "ShaderNodeBump" for n in mat_anon_tex.node_tree.nodes)

    # Painel sem textura e cor preta: ganha emissao suave e cor base visivel
    bsdf_panel = mat_panel_solid.node_tree.nodes[0]
    assert bsdf_panel.inputs["Emission Strength"].default_value == pytest.approx(2.8)
    assert bsdf_panel.inputs["Emission Color"].default_value[2] > 0.8

    # Quando trazomob_pbr_id esta presente no material (via extras do GLB), ele e isolado por ID exato
    # e nao herda nem propaga configuracoes para outros materiais com nome parecido ou sufixo _2
    mat_tagged_other = _FakeMaterial("Color_C02_Outro")
    mat_tagged_other["trazomob_pbr_id"] = "Outro_Material_Diferente"
    assert mod._match_material_override(
        mat_tagged_other,
        mat_tagged_other.node_tree.nodes[0],
        mat_tagged_other.node_tree.nodes,
        {"[Color C02]": {"type": "emissivo", "sub_type": "Painel Iluminado / TV Ligada"}},
    ) == {}

    mat_tagged_exact = _FakeMaterial("mat99")
    mat_tagged_exact["trazomob_pbr_id"] = "[Color C02]"
    assert mod._match_material_override(
        mat_tagged_exact,
        mat_tagged_exact.node_tree.nodes[0],
        mat_tagged_exact.node_tree.nodes,
        {"[Color C02]": {"type": "emissivo", "sub_type": "Painel Iluminado / TV Ligada"}},
    )["type"] == "emissivo"

    # Gera AreaLight retangular na frente da TV para iluminar a cena no EEVEE e no Cycles
    em_lights = mod.create_emissive_material_lights(fake_scene, depsgraph=object())
    assert len(em_lights) == 1
    assert len(created_lights) == 1
    assert created_lights[0].type == "AREA"
    assert created_lights[0].shape == "RECTANGLE"
    assert created_lights[0].size == pytest.approx(1.2)
    assert created_lights[0].size_y == pytest.approx(0.7)
    assert created_lights[0].energy > 15.0
    assert created_objs[0].visible_camera is False
    assert created_objs[0].visible_glossy is False
    assert em_lights[0]["pos"][0] == pytest.approx(0.045)

