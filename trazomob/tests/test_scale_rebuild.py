# SPDX-License-Identifier: GPL-3.0-or-later
"""Testes de rearranjo paramétrico dos módulos de marcenaria após uso do Scale (ferramenta S)."""
from PySide6.QtGui import QVector3D

from core.history import History, ScaleGroupCommand
from core.scene import Scene
from tools.scale import ScaleTool
from trazomob.builders.cabinet import CabinetBuilder


def test_scale_rebuild_preserves_board_thickness():
    """Garante que ao escalar um balcão em X, Y e Z com ScaleGroupCommand, as espessuras de 15mm não distorcem."""
    sc = Scene()
    p = {
        "tipo": "balcao",
        "largura": 800,
        "altura": 720,
        "profundidade": 550,
        "espessura": 15.0,
    }
    mod = CabinetBuilder.build_module_group(p, offset=(1.0, 2.0, 0.0))
    sc.groups.append(mod)

    # Escala dobrando altura Z e aumentando largura X em 50%
    cmd = ScaleGroupCommand(mod, QVector3D(1.0, 2.0, 0.0), (1.5, 1.0, 2.0))
    cmd.do(sc)

    # 1. Dimensões nominais atualizadas
    assert mod.ext["trazomob_module"]["largura"] == 1200.0
    assert mod.ext["trazomob_module"]["altura"] == 1440.0
    assert mod.ext["trazomob_module"]["profundidade"] == 550.0

    # 2. Espessuras reais da geometria das peças permanecem fiéis a 15mm (sem esticar para 30mm)
    base = [c for c in mod.children if "Base" in c.name][0]
    zs_base = [v.position.z() for v in base.mesh.vertices]
    assert round((max(zs_base) - min(zs_base)) * 1000.0, 1) == 15.0

    lat = [c for c in mod.children if "Lateral" in c.name][0]
    xs_lat = [v.position.x() for v in lat.mesh.vertices]
    assert round((max(xs_lat) - min(xs_lat)) * 1000.0, 1) == 15.0

    # 3. Undo reverte peças e dimensões perfeitamente
    cmd.undo(sc)
    assert mod.ext["trazomob_module"]["largura"] == 800.0
    assert mod.ext["trazomob_module"]["altura"] == 720.0
    base_u = [c for c in mod.children if "Base" in c.name][0]
    zs_base_u = [v.position.z() for v in base_u.mesh.vertices]
    assert round((max(zs_base_u) - min(zs_base_u)) * 1000.0, 1) == 15.0


def test_scale_rebuild_multiple_module_types():
    """Garante que gaveteiros, aéreos e nichos rearranjam suas peças após o scale."""
    sc = Scene()
    for tipo in ("gaveteiro", "aereo", "nicho"):
        p = {
            "tipo": tipo,
            "largura": 600,
            "altura": 600,
            "profundidade": 400,
            "espessura": 15.0,
        }
        mod = CabinetBuilder.build_module_group(p, offset=(0.0, 0.0, 0.0))
        sc.groups.append(mod)

        cmd = ScaleGroupCommand(mod, QVector3D(0.0, 0.0, 0.0), (1.2, 1.0, 1.5))
        cmd.do(sc)

        assert mod.ext["trazomob_module"]["largura"] == 720.0
        assert mod.ext["trazomob_module"]["altura"] == 900.0

        pecas = [c for c in mod.children if hasattr(c, "mesh") and c.mesh.vertices]
        assert len(pecas) > 0
        peca_horiz = [c for c in pecas if any(k in c.name for k in ("Base", "Tampo", "Prateleira"))][0]
        zs = [v.position.z() for v in peca_horiz.mesh.vertices]
        assert round((max(zs) - min(zs)) * 1000.0, 1) == 15.0


def test_scale_tool_promotes_child_selection_to_module():
    """Garante que ao clicar/selecionar qualquer peça interna de um balcão inferior,
    a ferramenta Scale (S) promove a seleção para o módulo completo e escala todo o móvel
    sem reverter ao soltar o mouse."""
    sc = Scene()
    p = {
        "tipo": "balcao",
        "largura": 800,
        "altura": 720,
        "profundidade": 550,
    }
    mod = CabinetBuilder.build_module_group(p, offset=(0.0, 0.0, 0.0))
    sc.groups.append(mod)

    # Seleciona uma peça componente interna (ex: a lateral esquerda)
    lateral = mod.children[0]
    sc.select([lateral])

    class FakeViewport:
        def __init__(self, scene):
            self.scene = scene
            self.history = History(scene)
            self.edit_group = None
        def update(self): pass

    vp = FakeViewport(sc)
    tool = ScaleTool()
    tool.on_activate(vp)

    # Verifica que a seleção foi promovida ao módulo raiz
    assert mod in sc.selection
    assert lateral not in sc.selection

    # Simula o arraste da alça de largura (face X)
    grip = [g for g in tool._grips if g.params == (1.0, 0.5, 0.5)][0]
    tool._grab(vp, grip, (100, 100))
    tool._moved = True
    tool._apply_preview(vp, (1.5, 1.0, 1.0))
    tool.on_release(vp)

    # Módulo não reverteu: ficou com 1200mm de largura!
    assert mod.ext["trazomob_module"]["largura"] == 1200.0
    base = [c for c in mod.children if "Base" in c.name][0]
    xs = [v.position.x() for v in base.mesh.vertices]
    assert round((max(xs) - min(xs)) * 1000.0, 1) == 1170.0
