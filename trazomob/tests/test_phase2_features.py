import pytest
from PySide6.QtWidgets import QApplication

from core.history import History
from core.scene import Scene
from trazomob.builders.cabinet import CabinetBuilder
from trazomob.ui.sidebar_panel import TrazoMobSidebarPanel


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
    def flash_status(self, msg):
        pass

def test_front_style_presets(qapp):
    scene = Scene()
    vp = DummyViewport(scene)
    panel = TrazoMobSidebarPanel(None)
    panel._get_viewport = lambda: vp
    panel._get_scene = lambda: scene
    panel._ensure_form_built()

    # Cria balcão inicial
    params = {
        "tipo": "balcao",
        "largura": 800,
        "altura": 720,
        "profundidade": 550,
        "puxador_tipo": "alca",
    }
    mod = CabinetBuilder.build_module_group(params)
    scene.groups.append(mod)
    scene.selection = {mod}
    panel.load_module(mod)

    # Aplica preset Cava 45
    panel._apply_front_preset("cava_45")
    cur_mod = list(scene.selection)[0]
    assert cur_mod.ext["trazomob_module"]["puxador_tipo"] == "cava"

    # Aplica preset Tip-On / Toque
    panel._apply_front_preset("toque")
    cur_mod = list(scene.selection)[0]
    assert cur_mod.ext["trazomob_module"]["puxador_tipo"] == "sem_puxador"

def test_distribute_equidistant_modules(qapp):
    scene = Scene()
    vp = DummyViewport(scene)
    panel = TrazoMobSidebarPanel(None)
    panel._get_viewport = lambda: vp
    panel._get_scene = lambda: scene
    panel._ensure_form_built()

    # Cria 3 módulos de largura 500mm
    # M1 em x=0, M2 em x=600 (desalinhado), M3 em x=2000
    m1 = CabinetBuilder.build_module_group({"tipo": "balcao", "largura": 500, "altura": 720, "profundidade": 550}, offset=(0.0, 0.0, 0.0))
    m2 = CabinetBuilder.build_module_group({"tipo": "balcao", "largura": 500, "altura": 720, "profundidade": 550}, offset=(0.6, 0.0, 0.0))
    m3 = CabinetBuilder.build_module_group({"tipo": "balcao", "largura": 500, "altura": 720, "profundidade": 550}, offset=(2.0, 0.0, 0.0))

    for m in (m1, m2, m3):
        scene.groups.append(m)
    scene.selection = {m1, m2, m3}

    # Total span = (2.0 + 0.5) - 0.0 = 2.5m.
    # Soma larguras = 0.5 * 3 = 1.5m.
    # Total de sobra = 1.0m dividido em 2 vãos = 0.5m cada.
    # M1 começa em 0.0 -> termina em 0.5
    # M2 deve começar em 0.5 + 0.5 = 1.0m
    # M3 deve começar em 1.0 + 0.5 + 0.5 = 2.0m
    panel._distribute_selected_modules()

    from trazomob.interaction.align_tools import get_entity_world_bounds
    b1 = get_entity_world_bounds(m1)
    b2 = get_entity_world_bounds(m2)
    b3 = get_entity_world_bounds(m3)

    assert pytest.approx(b1[0], 0.01) == 0.0
    assert pytest.approx(b2[0], 0.01) == 1.0
    assert pytest.approx(b3[0], 0.01) == 2.0

