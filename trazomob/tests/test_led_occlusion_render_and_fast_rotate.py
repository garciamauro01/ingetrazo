# SPDX-License-Identifier: GPL-3.0-or-later
"""Testes para oclusao e emissao de fita LED, e rotacao rapida de 90 graus."""
from __future__ import annotations

import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PySide6.QtGui import QMatrix4x4, QVector3D

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent.parent
if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))

from core.group import Group
from core.mesh import Mesh
from core.scene import Scene
from trazomob.builders.cabinet import RotateTrazoMobModuleCommand
from trazomob.interaction.align_tools import (
    get_entity_world_bounds,
    resolve_rotatable_groups,
)
from trazomob.render.lighting import (
    TrazoMobLightVisualizer,
    _compute_led_strip_direction,
    _get_scene_lights,
    create_light_mesh,
    create_light_scene_group,
)


def _ray_aabb_intersect(orig: QVector3D, rdir: QVector3D, box: tuple[float, float, float, float, float, float]) -> float | None:
    """Intersecao raio-AABB exata para mocks de raycast 3D."""
    ox, oy, oz = orig.x(), orig.y(), orig.z()
    dx, dy, dz = rdir.x(), rdir.y(), rdir.z()
    bmin = (box[0], box[2], box[4])
    bmax = (box[1], box[3], box[5])
    o = (ox, oy, oz)
    d = (dx, dy, dz)
    tmin, tmax = 0.0, float("inf")
    for i in range(3):
        if abs(d[i]) < 1e-9:
            if o[i] < bmin[i] or o[i] > bmax[i]:
                return None
        else:
            inv = 1.0 / d[i]
            t1 = (bmin[i] - o[i]) * inv
            t2 = (bmax[i] - o[i]) * inv
            if t1 > t2:
                t1, t2 = t2, t1
            tmin = max(tmin, t1)
            tmax = min(tmax, t2)
            if tmax < tmin:
                return None
    return tmin if tmin >= 1e-5 else (tmax if tmax >= 1e-5 else None)


class _PickMockViewport:
    """Mock de viewport compatível com ``_pick_index`` e ``_ray_hits`` do host."""

    def __init__(self, eye: QVector3D, entities_boxes: list[tuple[object, object, tuple[float, float, float, float, float, float]]], scene=None):
        self._eye = eye
        self._entities_boxes = entities_boxes
        self.scene = scene
        self.camera = SimpleNamespace(perspective=True, eye=lambda: self._eye)
        self._idx = SimpleNamespace(
            entities=[(f, g) for f, g, _b in entities_boxes],
            ent_vis=np.ones(len(entities_boxes), dtype=bool),
        )

    def _pick_index(self):
        return self._idx

    def _ray_hits(self, idx, ray_orig, ray_dir, mask, reduce_global=False, reach=float("inf"), own=True):
        best = float("inf")
        for i, (_f, _g, box) in enumerate(self._entities_boxes):
            if not mask[i]:
                continue
            t = _ray_aabb_intersect(ray_orig, ray_dir, box)
            if t is not None and 1e-5 < t < reach and t < best:
                best = t
        return best if reduce_global else np.array([best], dtype=float)

    def world_to_pixel(self, pt: QVector3D):
        return (pt.x() * 100.0 + 400.0, 400.0 - pt.z() * 100.0)


def test_led_occlusion_18mm_door_and_light_mesh_excluded():
    """Chapa fina de 18mm na frente deve ocluir fita LED; malha propria da luz nao pode causar auto-oclusao."""
    light_data = {
        "kind": "led_strip",
        "pos": [0.5, 0.0, 2.0],
        "p1": [0.0, 0.0, 2.0],
        "p2": [1.0, 0.0, 2.0],
        "dir": [0.0, 0.0, -1.0],
        "length": 1.0,
        "power": 350.0,
        "on": True,
    }
    light_grp = create_light_scene_group(light_data, 0)
    shelf_grp = Group(Mesh(), name="Prateleira Superior")
    door_grp = Group(Mesh(), name="Porta MDF 18mm")

    eye = QVector3D(0.5, -1.0, 1.9)  # olhando no sentido +Y em direcao a Y=0
    entities = [
        # Malha da propria luz envolvendo (0.5, 0.0, 2.0) — NAO pode bloquear a visao
        (SimpleNamespace(hidden=False, attrs={"mat": "Fita LED Emissora"}), light_grp, (0.0, 1.0, -0.006, 0.006, 1.997, 2.003)),
        # Chapa superior de apoio atras/em cima da fita (Z = 2.000..2.018)
        (SimpleNamespace(hidden=False, attrs={}), shelf_grp, (0.0, 1.0, -0.30, 0.05, 2.000, 2.018)),
        # Porta frontal de 18mm cobrindo o trecho central X in [0.30, 0.70] em Y in [-0.030, -0.012]
        (SimpleNamespace(hidden=False, attrs={}), door_grp, (0.30, 0.70, -0.030, -0.012, 1.50, 2.20)),
    ]
    vp = _PickMockViewport(eye, entities)

    # Ponto esquerdo livre (X=0.10) deve estar visivel mesmo com a malha propria da luz
    assert TrazoMobLightVisualizer.is_point_visible(
        vp, QVector3D(0.10, 0.0, 2.0), normal_hint=QVector3D(0.0, 0.0, -1.0)
    ) is True
    # Ponto central atras da porta de 18mm (X=0.50) deve ficar OCULTO
    assert TrazoMobLightVisualizer.is_point_visible(
        vp, QVector3D(0.50, 0.0, 2.0), normal_hint=QVector3D(0.0, 0.0, -1.0)
    ) is False

    # Segmentacao parcial deve retornar exatamente os 2 trechos fora da porta: [0..0.30] e [0.70..1.0]
    segs = TrazoMobLightVisualizer.clip_visible_led_segments(
        vp,
        QVector3D(0.0, 0.0, 2.0),
        QVector3D(1.0, 0.0, 2.0),
        normal_hint=QVector3D(0.0, 0.0, -1.0),
    )
    assert len(segs) == 2
    s1_a, s1_b, s1_p1, s1_p2 = segs[0]
    s2_a, s2_b, s2_p1, s2_p2 = segs[1]
    assert s1_p1 is True and s1_p2 is False
    assert s2_p1 is False and s2_p2 is True
    assert s1_a.x() == 0.0 and abs(s1_b.x() - 0.30) < 0.02
    assert abs(s2_a.x() - 0.70) < 0.02 and s2_b.x() == 1.0


def test_draw_trazomob_lights_draws_only_unoccluded_segments():
    """O desenho da fita LED deve tracar apenas subsegmentos visiveis e suprimir pontas ocultas."""
    light_data = {
        "kind": "led_strip",
        "pos": [0.5, 0.0, 2.0],
        "p1": [0.0, 0.0, 2.0],
        "p2": [1.0, 0.0, 2.0],
        "dir": [0.0, 0.0, -1.0],
        "length": 1.0,
        "power": 350.0,
        "on": True,
    }
    scene = Scene()
    scene.groups.append(create_light_scene_group(light_data, 0))
    door_grp = Group(Mesh(), name="Porta Direita")
    # Porta cobre apenas metade direita (X in [0.60, 1.10])
    vp = _PickMockViewport(
        QVector3D(0.5, -1.0, 1.9),
        [(SimpleNamespace(hidden=False, attrs={}), door_grp, (0.60, 1.10, -0.025, -0.007, 1.50, 2.20))],
        scene=scene,
    )
    vp.active_tool = None

    class _FakePainter:
        def __init__(self):
            self.lines = []
            self.ellipses = []

        def setRenderHint(self, *_a):
            pass

        def setFont(self, *_a):
            pass

        def setPen(self, *_a):
            pass

        def setBrush(self, *_a):
            pass

        def drawLine(self, a, b):
            self.lines.append((round(a.x(), 1), round(b.x(), 1)))

        def drawEllipse(self, c, *_a):
            self.ellipses.append(round(c.x(), 1))

        def drawText(self, *_a):
            pass

    painter = _FakePainter()
    TrazoMobLightVisualizer.draw_trazomob_lights(vp, painter)

    # Deve ter desenhado linhas apenas ate ~X=0.60 (x_px ~ 460) e NUNCA ate P2 (x_px = 500)
    assert painter.lines, "Esperava pelo menos um trecho visivel desenhado"
    assert all(b <= 462.0 for _a, b in painter.lines)
    # Apenas P1 (x_px=400.0) visivel recebe ponto de extremidade; P2 (500.0) esta ocluido
    assert 400.0 in painter.ellipses
    assert all(ex < 480.0 for ex in painter.ellipses)


def test_led_strip_direction_and_flush_mesh_profile():
    """Direcao da fita nunca deve ser colinear nem apontar para dentro do MDF, e o perfil deve ser delgado."""
    p1 = QVector3D(0.0, 0.0, 2.0)
    p2 = QVector3D(1.0, 0.0, 2.0)
    # Simula clique capturando normal colinear (1,0,0) de uma lateral de armario
    d1 = _compute_led_strip_direction(None, p1, p2, n1=QVector3D(1.0, 0.0, 0.0), n2=QVector3D(-1.0, 0.0, 0.0))
    v_dir = QVector3D(*d1)
    u = (p2 - p1).normalized()
    assert abs(QVector3D.dotProduct(v_dir, u)) < 1e-4
    assert abs(d1[2] - (-1.0)) < 1e-4

    # Simula tampo de MDF imediatamente acima (+Z), enquanto abaixo (-Z) esta livre
    top_shelf = Group(Mesh(), name="Tampo Superior")
    vp = _PickMockViewport(
        QVector3D(0.5, -1.0, 1.9),
        [(SimpleNamespace(hidden=False, attrs={}), top_shelf, (-0.1, 1.1, -0.3, 0.3, 2.001, 2.019))],
    )
    d2 = _compute_led_strip_direction(vp, p1, p2, n1=QVector3D(0.0, 0.0, 1.0), n2=QVector3D(0.0, 0.0, 1.0))
    assert d2[2] < -0.9

    # Simula clique na parede traseira logo abaixo da base do aereo (normal da parede +Y, armario acima em Z=1.500)
    wall_grp = Group(Mesh(), name="Parede #1")
    cabinet_bottom = Group(Mesh(), name="Aereo - Base Inferior")
    vp_wall_seam = _PickMockViewport(
        QVector3D(0.5, 1.5, 1.2),
        [
            (SimpleNamespace(hidden=False, attrs={}), wall_grp, (-0.2, 1.2, -0.15, 0.0, 0.0, 2.6)),
            (SimpleNamespace(hidden=False, attrs={}), cabinet_bottom, (0.0, 1.0, 0.0, 0.35, 1.500, 1.515)),
        ],
    )
    d_seam = _compute_led_strip_direction(
        vp_wall_seam,
        QVector3D(0.0, 0.0, 1.499),
        QVector3D(1.0, 0.0, 1.498),
        n1=QVector3D(0.0, 1.0, 0.0),
        n2=QVector3D(0.0, 1.0, 0.0),
    )
    assert d_seam[2] < -0.9

    mesh = create_light_mesh({
        "kind": "led_strip",
        "pos": [0.5, 0.0, 2.0],
        "p1": [0.0, 0.0, 2.0],
        "p2": [1.0, 0.0, 2.0],
        "dir": d2,
    })
    zs = [v.position.z() for v in mesh.vertices]
    # Espessura total de 5mm (±2.5mm) nao atravessa chapas de 15/18mm
    assert (max(zs) - min(zs)) <= 0.006


def test_scene_light_collection_and_native_write_job_expansion(tmp_path, monkeypatch):
    """Engine coleta luzes direto da scene e write_job expande fita LED para render nativo."""
    import json

    from core import render_blender as rb
    from core.camera import OrbitCamera

    scene = Scene()
    led = {
        "kind": "led_strip",
        "name": "LED Nicho",
        "pos": [0.5, 0.2, 2.0],
        "p1": [0.0, 0.2, 2.0],
        "p2": [1.0, 0.2, 2.0],
        "dir": [0.0, 0.0, -1.0],
        "power": 300.0,
        "color": [1.0, 0.9, 0.8],
        "on": True,
    }
    scene.plugin_data = {"render_blender": {"lights": [dict(led)]}}
    lights = _get_scene_lights(scene)
    assert len(lights) == 1
    assert lights[0]["kind"] == "led_strip"

    monkeypatch.setattr("formats.gltf.save_glb", lambda *a, **kw: tmp_path / "model.glb")
    job_path = rb.write_job(scene, OrbitCamera(), tmp_path, lights=[dict(led)])
    job = json.loads(Path(job_path).read_text(encoding="utf-8"))
    assert len(job["lights"]) >= 4
    assert all(lt["kind"] == "point" for lt in job["lights"])
    assert all(abs(lt["pos"][2] - (2.0 - 0.015)) < 1e-4 for lt in job["lights"])
    assert math.isclose(sum(lt["power"] for lt in job["lights"]), 300.0, rel_tol=1e-3)


def _make_dense_box_mesh(nx: int = 25, ny: int = 25) -> Mesh:
    m = Mesh()
    step = 0.02
    for i in range(nx):
        for j in range(ny):
            x0, y0 = i * step, j * step
            x1, y1 = x0 + step, y0 + step
            m.add_face([
                QVector3D(x0, y0, 0.0),
                QVector3D(x1, y0, 0.0),
                QVector3D(x1, y1, 0.0),
                QVector3D(x0, y1, 0.0),
            ])
    return m


def test_fast_90deg_rotation_preserves_other_caches_and_uses_xform():
    """Rotacao 90° em objeto generico usa xform em O(1) e nao limpa caches do resto da cena."""
    scene = Scene()
    heavy_mesh = _make_dense_box_mesh(25, 25)
    v0_before = QVector3D(heavy_mesh.vertices[0].position)
    heavy_grp = Group(heavy_mesh, name="Ventilador Importado")
    heavy_grp.xform = None
    heavy_grp.component = False

    other_grp = Group(_make_dense_box_mesh(2, 2), name="Outro Armario")
    scene.groups = [heavy_grp, other_grp]

    vp = SimpleNamespace(
        scene=scene,
        _group_chunks={id(heavy_grp): {"uid": 10}, id(other_grp): {"uid": 20}},
        _inst_chunks={id(other_grp): {"ikey": (20,)}},
        _placements_memo=("stale",),
        _epoch_same=123,
        updated=False,
    )
    vp.update = lambda: setattr(vp, "updated", True)

    assert resolve_rotatable_groups(scene, [heavy_grp]) == [heavy_grp]

    cmd = RotateTrazoMobModuleCommand(heavy_grp, 90.0, axis=(0.0, 0.0, 1.0), viewport=vp)
    cmd.do(scene)

    assert isinstance(heavy_grp.xform, QMatrix4x4)
    assert heavy_grp.is_component() is False
    # Vertices da malha original nao devem ter sido iterados/mutados em Python
    assert heavy_mesh.vertices[0].position == v0_before
    # Cache de OUTROS objetos da cena deve permanecer intacto (evita reconstruir a cena toda)
    assert id(other_grp) in vp._group_chunks
    assert id(other_grp) in vp._inst_chunks
    # Prototipo do objeto promovido deve ter sido pre-semeado
    assert getattr(vp, "_proto_wrappers", None)

    b_rot = get_entity_world_bounds(heavy_grp)
    assert b_rot is not None

    cmd.undo(scene)
    # Apos Undo, bounds voltam a coincidir com o original
    assert heavy_grp.xform is not None
    v0_world_after_undo = heavy_grp.xform.map(heavy_mesh.vertices[0].position)
    assert (v0_world_after_undo - v0_before).length() < 1e-4


def test_photoreal_render_has_top_level_bmesh_and_eevee_diffuse_safe_flags():
    """Script headless do Blender deve importar bmesh no topo e desativar raytracing/fast_gi no EEVEE."""
    import ast

    script_path = ROOT / "blender_scripts" / "photoreal_render.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    top_imports = {
        alias.name
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert "bmesh" in top_imports
    assert '"use_raytracing": False' in source
    assert '"use_fast_gi": False' in source


def test_led_strip_resizes_when_physical_mesh_group_is_scaled_or_stretched():
    """Redimensionar a malha 3D da fita LED (Escalar pelo centro/ponta ou Push/Pull) atualiza p1, p2, pos e length."""
    from core.history import scale_matrix

    lt = {
        "kind": "led_strip",
        "name": "LED Bancada",
        "pos": [0.5, 0.0, 2.0],
        "p1": [0.0, 0.0, 2.0],
        "p2": [1.0, 0.0, 2.0],
        "dir": [0.0, 0.0, -1.0],
        "length": 1.0,
        "power": 300.0,
        "color": [1.0, 0.9, 0.8],
        "on": True,
    }
    scene = Scene()
    grp = create_light_scene_group(lt, 0)
    scene.groups = [grp]
    scene.plugin_data = {"render_blender": {"lights": [dict(lt)]}}

    # 1. Escala simétrica pelo centro (2x no eixo X via grp.xform) — centro não muda!
    grp.xform = scale_matrix(QVector3D(0.5, 0.0, 2.0), (2.0, 1.0, 1.0))
    lights_after_center_scale = _get_scene_lights(scene)
    assert len(lights_after_center_scale) == 1
    l_sym = lights_after_center_scale[0]
    assert math.isclose(l_sym["p1"][0], -0.5, abs_tol=1e-3)
    assert math.isclose(l_sym["p2"][0], 1.5, abs_tol=1e-3)
    assert math.isclose(l_sym["pos"][0], 0.5, abs_tol=1e-3)
    assert math.isclose(l_sym["length"], 2.0, abs_tol=1e-3)
    assert math.isclose(scene.plugin_data["render_blender"]["lights"][0]["length"], 2.0, abs_tol=1e-3)

    # 2. Push/Pull / ScaleGroupCommand direto nos vértices da tampa p2 (+0.5m em X após limpar xform)
    from core.history import ScaleGroupCommand
    grp.xform = None
    ScaleGroupCommand(grp, QVector3D(0.5, 0.0, 2.0), (2.0, 1.0, 1.0)).do(scene)
    cap_p2 = next(f for f in grp.mesh.faces if f.attrs.get("led_cap") == "p2")
    for v in list(cap_p2.loop):
        grp.mesh.move_vertex(v, QVector3D(0.5, 0.0, 0.0))

    lights_after_stretch = _get_scene_lights(scene)
    l_st = lights_after_stretch[0]
    assert math.isclose(l_st["p1"][0], -0.5, abs_tol=1e-3)
    assert math.isclose(l_st["p2"][0], 2.0, abs_tol=1e-3)
    assert math.isclose(l_st["pos"][0], 0.75, abs_tol=1e-3)
    assert math.isclose(l_st["length"], 2.5, abs_tol=1e-3)
    assert math.isclose(scene.plugin_data["render_blender"]["lights"][0]["p2"][0], 2.0, abs_tol=1e-3)


def test_eevee_room_confinement_blocks_sky_and_sun_unless_opening_or_glass(monkeypatch):
    """EEVEE deve conter luz externa em ambiente fechado (como no Cycles) e permitir atravessar vidros."""
    import importlib.util

    import pytest

    class _FakeVec:
        def __init__(self, coords=(0.0, 0.0, 0.0)):
            if isinstance(coords, _FakeVec):
                self._c = list(coords._c)
            else:
                self._c = [float(coords[0]), float(coords[1]), float(coords[2])]

        @property
        def x(self):
            return self._c[0]

        @property
        def y(self):
            return self._c[1]

        @property
        def z(self):
            return self._c[2]

        def __len__(self):
            return 3

        def __getitem__(self, idx):
            return self._c[idx]

        def copy(self):
            return _FakeVec(self._c)

        def __add__(self, other):
            o = _FakeVec(other)
            return _FakeVec((self.x + o.x, self.y + o.y, self.z + o.z))

        def __sub__(self, other):
            o = _FakeVec(other)
            return _FakeVec((self.x - o.x, self.y - o.y, self.z - o.z))

        def __neg__(self):
            return _FakeVec((-self.x, -self.y, -self.z))

        def __mul__(self, scalar):
            s = float(scalar)
            return _FakeVec((self.x * s, self.y * s, self.z * s))

        __rmul__ = __mul__

        def __truediv__(self, scalar):
            s = float(scalar)
            return _FakeVec((self.x / s, self.y / s, self.z / s))

        @property
        def length(self):
            return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

        def normalized(self):
            ln = self.length
            return _FakeVec((self.x / ln, self.y / ln, self.z / ln)) if ln > 1e-12 else _FakeVec()

        def normalize(self):
            ln = self.length
            if ln > 1e-12:
                self._c = [self.x / ln, self.y / ln, self.z / ln]
            return self

        def dot(self, other):
            o = _FakeVec(other)
            return self.x * o.x + self.y * o.y + self.z * o.z

        def cross(self, other):
            o = _FakeVec(other)
            return _FakeVec((
                self.y * o.z - self.z * o.y,
                self.z * o.x - self.x * o.z,
                self.x * o.y - self.y * o.x,
            ))

        def lerp(self, other, t):
            o = _FakeVec(other)
            return _FakeVec((
                self.x + (o.x - self.x) * t,
                self.y + (o.y - self.y) * t,
                self.z + (o.z - self.z) * t,
            ))

        def to_track_quat(self, *_args):
            return SimpleNamespace(to_euler=lambda: (0.0, 0.0, 0.0))

    class _FakeSocket:
        def __init__(self, name, node):
            self.name = name
            self.node = node
            self.id_data = node.id_data
            self.default_value = (0.8, 0.8, 0.8, 1.0) if "Color" in str(name) else 0.0
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
                    "Transmission Weight", "IOR", "Alpha", "Normal", "Radius",
                    "Height", "Strength", "Scale", "Detail", "Color", "Surface",
                    "Fac", 1, 2,
                )
            }
            self.outputs = {
                name: _FakeSocket(name, self)
                for name in ("BSDF", "Normal", "Fac", "Distance", "Color", "Background", "Shader", "Is Camera Ray")
            }

    class _FakeMaterial:
        def __init__(self, name, transmission=0.0):
            self.name = name
            self.use_nodes = True
            self.use_backface_culling = True
            self.shadow_method = "NONE"
            self.node_tree = SimpleNamespace()
            self.node_tree.nodes = _FakeNodes(self.node_tree)
            self.node_tree.links = _FakeLinks()
            bsdf = self.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
            bsdf.inputs["Transmission Weight"].default_value = transmission
            bsdf.inputs["Alpha"].default_value = 1.0

    def _make_world(name):
        nt = SimpleNamespace()
        nt.nodes = _FakeNodes(nt)
        nt.links = _FakeLinks()
        return SimpleNamespace(name=name, use_nodes=True, node_tree=nt)

    created_lights = []

    def _new_light(name, type="POINT"):
        lt = SimpleNamespace(
            name=name,
            type=type,
            energy=0.0,
            angle=0.0,
            color=(1.0, 1.0, 1.0),
            use_shadow=False,
            shadow_cascade_max_distance=200.0,
        )
        created_lights.append(lt)
        return lt

    def _new_obj(name, data):
        return SimpleNamespace(name=name, data=data, rotation_euler=(0.0, 0.0, 0.0))

    mat_wall = _FakeMaterial("Parede_Branca")
    mat_glass = _FakeMaterial("Vidro_Incolor", transmission=1.0)

    def _build_box_raycaster(boxes_with_mats):
        def _ray_cast(_depsgraph, origin, direction, distance=1e5):
            o_q = QVector3D(float(origin[0]), float(origin[1]), float(origin[2]))
            d_v = _FakeVec(direction).normalized()
            d_q = QVector3D(d_v.x, d_v.y, d_v.z)
            best_t = None
            best_mat = None
            for box, mat in boxes_with_mats:
                t = _ray_aabb_intersect(o_q, d_q, box)
                if t is not None and 1e-5 < t <= distance:
                    if best_t is None or t < best_t:
                        best_t = t
                        best_mat = mat
            if best_t is None:
                return False, _FakeVec(), _FakeVec(), -1, None, None
            loc = _FakeVec(origin) + d_v * best_t
            hit_obj = SimpleNamespace(
                material_slots=[SimpleNamespace(material=best_mat)],
                data=SimpleNamespace(polygons=[SimpleNamespace(material_index=0)]),
            )
            return True, loc, _FakeVec((0.0, 0.0, 1.0)), 0, hit_obj, None

        return _ray_cast

    fake_bpy = SimpleNamespace(
        app=SimpleNamespace(binary_path=""),
        utils=SimpleNamespace(resource_path=lambda _k: "Z:/nonexistent"),
        data=SimpleNamespace(
            materials=[mat_wall, mat_glass],
            worlds=SimpleNamespace(new=_make_world),
            lights=SimpleNamespace(new=_new_light),
            objects=SimpleNamespace(new=_new_obj),
        ),
        context=SimpleNamespace(scene=SimpleNamespace(objects=[])),
    )

    monkeypatch.setitem(sys.modules, "bpy", fake_bpy)
    monkeypatch.setitem(sys.modules, "bmesh", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "mathutils", SimpleNamespace(Matrix=object, Vector=_FakeVec))

    script_path = ROOT / "blender_scripts" / "photoreal_render.py"
    spec = importlib.util.spec_from_file_location("_test_photoreal_confinement", script_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)

    # 1. Materiais opacos devem receber sombra dupla-face; vidros permanecem intocados
    mod.setup_photoreal_materials(
        use_bevel=False,
        material_overrides={"Parede_Branca": {"type": "parede"}},
    )
    assert mat_wall.use_backface_culling is False
    assert mat_wall.shadow_method == "OPAQUE"
    assert mat_glass.shadow_method == "NONE"

    # Sala 4x4m, pe-direito 2.7m
    closed_walls_and_floor = [
        ((-2.0, 2.0, -2.0, 2.0, -0.1, 0.0), mat_wall),   # piso
        ((-2.1, -2.0, -2.0, 2.0, 0.0, 2.7), mat_wall),   # parede -X
        ((2.0, 2.1, -2.0, 2.0, 0.0, 2.7), mat_wall),     # parede +X
        ((-2.0, 2.0, -2.1, -2.0, 0.0, 2.7), mat_wall),   # parede -Y
        ((-2.0, 2.0, 2.0, 2.1, 0.0, 2.7), mat_wall),     # parede +Y
    ]
    ceiling_box = ((-2.1, 2.1, -2.1, 2.1, 2.7, 2.8), mat_wall)

    cam_cfg = {"eye": [0.0, -1.2, 1.5], "target": [0.0, 1.2, 1.1], "up": [0.0, 0.0, 1.0]}
    sun_dir = [0.4, 0.3, 0.85]

    # Caso A: Comodo 100% fechado (com teto e 4 paredes opacas)
    scene_closed = SimpleNamespace(
        collection=SimpleNamespace(objects=SimpleNamespace(link=lambda _o: None)),
        ray_cast=_build_box_raycaster(closed_walls_and_floor + [ceiling_box]),
        eevee=SimpleNamespace(
            taa_render_samples=16,
            use_shadows=False,
            use_raytracing=True,
            use_fast_gi=True,
            shadow_ray_count=1,
            shadow_step_count=4,
            gtao_distance=0.2,
        ),
        render=SimpleNamespace(engine="CYCLES"),
    )
    scene_closed.__setitem__ = lambda k, v: setattr(scene_closed, f"prop_{k}", v)
    scene_closed.get = lambda k, default=None: getattr(scene_closed, f"prop_{k}", default)

    conf_closed = mod.measure_room_confinement(scene_closed, object(), cam_cfg, sun_dir=sun_dir)
    assert conf_closed["enclosed"] is True
    assert conf_closed["has_ceiling"] is True
    assert conf_closed["sky_open_ratio"] == pytest.approx(0.0)
    assert conf_closed["sky_exposure"] == pytest.approx(0.0)
    assert conf_closed["sun_visibility"] == pytest.approx(0.0)

    # Sem luzes internas -> escuro total (World = 0.0) e Sol bloqueado (energy = 0.0) no EEVEE
    created_lights.clear()
    mod.apply_lighting_preset(
        scene_closed, preset_name="dia", sun_dir=sun_dir, engine="eevee", confinement=conf_closed, interior_lights=[]
    )
    bg_closed = next(n for n in scene_closed.world.node_tree.nodes if n.bl_idname == "ShaderNodeBackground")
    assert bg_closed.inputs["Strength"].default_value == pytest.approx(0.0)
    sun_closed = next(lt for lt in created_lights if lt.type == "SUN")
    assert sun_closed.energy == pytest.approx(0.0)
    assert sun_closed.use_shadow is True

    # Com luz interna ativa -> preenchimento sutil de rebote interno (<= 0.04), sem vazamento do ceu
    mod.apply_lighting_preset(
        scene_closed,
        preset_name="dia",
        sun_dir=sun_dir,
        engine="eevee",
        confinement=conf_closed,
        interior_lights=[{"on": True, "power": 600.0, "color": (1.0, 0.85, 0.7)}],
    )
    bg_lit = next(n for n in scene_closed.world.node_tree.nodes if n.bl_idname == "ShaderNodeBackground")
    assert 0.0 < bg_lit.inputs["Strength"].default_value <= 0.04
    assert bg_lit.inputs["Color"].default_value[:3] == pytest.approx((1.0, 0.85, 0.7))

    # No modo Cycles, o World/Sol permanecem inalterados pois o próprio Cycles traça as paredes/teto
    created_lights.clear()
    mod.apply_lighting_preset(
        scene_closed, preset_name="dia", sun_dir=sun_dir, engine="cycles", confinement=conf_closed
    )
    sun_cycles = next(lt for lt in created_lights if lt.type == "SUN")
    assert sun_cycles.energy == pytest.approx(3.5)

    # EEVEE engine flags de sombra e protecao contra bug difuso
    mod.setup_render_engine(scene_closed, engine="eevee", samples=32)
    assert scene_closed.eevee.use_shadows is True
    assert scene_closed.eevee.use_raytracing is False
    assert scene_closed.eevee.use_fast_gi is False
    assert scene_closed.eevee.shadow_ray_count == 4
    assert scene_closed.eevee.shadow_step_count == 12
    assert scene_closed.eevee.gtao_distance == pytest.approx(0.5)

    # Caso B: Comodo fechado com janela envidracada (vidro em x=+2.0) -> raio atravessa vidro
    wall_east_parts = [
        ((2.0, 2.1, -2.0, -0.8, 0.0, 2.7), mat_wall),
        ((2.0, 2.1, 0.8, 2.0, 0.0, 2.7), mat_wall),
        ((2.0, 2.1, -0.8, 0.8, 0.0, 0.8), mat_wall),
        ((2.0, 2.1, -0.8, 0.8, 2.2, 2.7), mat_wall),
        ((2.02, 2.05, -0.8, 0.8, 0.8, 2.2), mat_glass),
    ]
    windowed_boxes = closed_walls_and_floor[:2] + wall_east_parts + closed_walls_and_floor[3:] + [ceiling_box]
    scene_windowed = SimpleNamespace(
        collection=scene_closed.collection,
        ray_cast=_build_box_raycaster(windowed_boxes),
    )
    conf_windowed = mod.measure_room_confinement(scene_windowed, object(), cam_cfg, sun_dir=sun_dir)
    assert conf_windowed["enclosed"] is True
    assert conf_windowed["has_ceiling"] is True
    assert 0.0 < conf_windowed["sky_open_ratio"] < 0.45
    assert 0.0 < conf_windowed["sky_exposure"] < 1.0

    # Caso C: Cena aberta (sem teto) -> iluminacao externa total preservada
    scene_open = SimpleNamespace(
        collection=scene_closed.collection,
        ray_cast=_build_box_raycaster(closed_walls_and_floor),
    )
    conf_open = mod.measure_room_confinement(scene_open, object(), cam_cfg, sun_dir=sun_dir)
    assert conf_open["has_ceiling"] is False
    assert conf_open["enclosed"] is False
    assert conf_open["sky_exposure"] == pytest.approx(1.0)
    assert conf_open["sun_visibility"] == pytest.approx(1.0)
