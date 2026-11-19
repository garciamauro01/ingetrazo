import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QVector3D
from core.group import Group
from core.history import History
from core.mesh import Mesh
from core.scene import Scene
from trazomob.ui.sidebar_panel import TrazoMobSidebarPanel
from trazomob.builders.cabinet import CabinetBuilder

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

class DummyViewport:
    def __init__(self, scene):
        self.scene = scene
        self.history = History(scene)
        self._changed = False
    def update(self):
        pass
    def notify_scene_changed(self):
        self._changed = True

def test_swap_module_type(qapp):
    scene = Scene()
    vp = DummyViewport(scene)
    panel = TrazoMobSidebarPanel(None)
    panel._get_viewport = lambda: vp
    panel._get_scene = lambda: scene
    panel._ensure_form_built()

    # Cria um balcão 2P
    params = {
        "tipo": "balcao",
        "largura": 800,
        "altura": 720,
        "profundidade": 550,
        "rot_z": 90.0,
        "offset": (1.0, 2.0, 0.0),
    }
    mod = CabinetBuilder.build_module_group(params, offset=(1.0, 2.0, 0.0))
    scene.groups.append(mod)
    scene.selection = {mod}

    panel.load_module(mod)
    assert panel.cb_trocar_tipo.currentData() == "balcao"

    # Troca para gaveteiro
    idx_gav = panel.cb_trocar_tipo.findData("gaveteiro")
    assert idx_gav >= 0
    panel.cb_trocar_tipo.setCurrentIndex(idx_gav)

    # Verifica que o módulo substituído manteve medidas e rot_z
    new_mod = list(scene.selection)[0]
    new_p = new_mod.ext["trazomob_module"]
    assert new_p["tipo"] == "gaveteiro"
    assert new_p["largura"] == 800
    assert new_p["rot_z"] == 90.0

def test_contiguous_duplicate_left_and_right(qapp):
    scene = Scene()
    vp = DummyViewport(scene)
    panel = TrazoMobSidebarPanel(None)
    panel._get_viewport = lambda: vp
    panel._get_scene = lambda: scene
    panel._ensure_form_built()

    # Módulo inicial com largura 800mm e rot_z = 0 (u_dir = +X)
    params = {
        "tipo": "balcao",
        "largura": 800,
        "altura": 720,
        "profundidade": 550,
        "rot_z": 0.0,
        "offset": (0.0, 0.0, 0.0),
    }
    mod = CabinetBuilder.build_module_group(params, offset=(0.0, 0.0, 0.0))
    scene.groups.append(mod)
    scene.selection = {mod}
    panel.load_module(mod)

    # Duplicar à Direita
    panel._duplicate_selected(direction="right")
    assert len(scene.groups) == 2
    mod_right = scene.groups[-1]
    off_r = mod_right.ext["trazomob_module"]["offset"]
    assert pytest.approx(off_r[0], 0.001) == 0.8
    assert pytest.approx(off_r[1], 0.001) == 0.0

    # Seleciona novamente o módulo original e duplica à Esquerda
    scene.selection = {mod}
    panel.load_module(mod)
    panel._duplicate_selected(direction="left")
    assert len(scene.groups) == 3
    mod_left = scene.groups[-1]
    off_l = mod_left.ext["trazomob_module"]["offset"]
    assert pytest.approx(off_l[0], 0.001) == -0.8
    assert pytest.approx(off_l[1], 0.001) == 0.0
