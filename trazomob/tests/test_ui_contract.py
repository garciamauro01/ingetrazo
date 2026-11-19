# SPDX-License-Identifier: GPL-3.0-or-later
"""Contract & anti-regression tests for the TrazoMob 5-tab sidebar UI and builder propagation."""

from __future__ import annotations

import copy
import pytest
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QSpinBox,
    QWidget,
)

from core.group import Group
from core.history import History
from core.scene import Scene
from trazomob.builders.cabinet import CabinetBuilder
from trazomob.domain.migration import DEFAULT_MODULE_PARAMS
from trazomob.domain.preferences import (
    DEFAULT_PREFERENCES,
    TrazoMobPreferencesManager,
)
from trazomob.domain.ui_contract import (
    DEFAULT_FOLGA_FRENTES_MM,
    DEFAULT_PROF_RASGO_MM,
    DEFAULT_RECUO_FUNDO_MM,
    TAB_ORDER,
    UI_TABS_CONTRACT,
    should_show_config_gaveteiro,
    should_show_lado_porta_armario,
)
from trazomob.ui.sidebar_panel import TrazoMobSidebarPanel


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture()
def isolated_prefs():
    manager = TrazoMobPreferencesManager.get_instance()
    original = copy.deepcopy(manager._data)
    manager._data["global"] = copy.deepcopy(DEFAULT_PREFERENCES["global"])
    manager._data["module_defaults"] = {}
    try:
        yield manager
    finally:
        manager._data = original


class DummyViewport:
    def __init__(self, scene: Scene):
        self.scene = scene
        self.history = History(scene)
        self._changed = False

    def update(self) -> None:
        pass

    def notify_scene_changed(self) -> None:
        self._changed = True


def _make_panel(qapp):
    scene = Scene()
    vp = DummyViewport(scene)
    panel = TrazoMobSidebarPanel(None)
    panel._get_viewport = lambda: vp
    panel._get_scene = lambda: scene
    panel._ensure_form_built()
    return panel, scene, vp


def _collect_bounds(obj) -> tuple[float, float, float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []

    def _walk(node):
        mesh = getattr(node, "mesh", None)
        if mesh and getattr(mesh, "vertices", None):
            for v in mesh.vertices:
                pos = v.position
                xs.append(float(pos.x()))
                ys.append(float(pos.y()))
                zs.append(float(pos.z()))
        for ch in getattr(node, "children", []):
            _walk(ch)

    _walk(obj)
    assert xs and ys and zs, f"Objeto sem vértices de malha: {getattr(obj, 'name', obj)}"
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


def _find_front_pieces(mod: Group, keyword: str) -> list[Group]:
    pieces = []
    for p in getattr(mod, "children", []):
        low = p.name.lower()
        if keyword == "porta" and "porta" in low and "frente" not in low:
            pieces.append(p)
        elif keyword == "frente" and "frente" in low and "contra-frente" not in low and "porta" not in low:
            pieces.append(p)
    pieces.sort(key=lambda g: _collect_bounds(g)[0])
    return pieces


def _find_fundo_piece(mod: Group) -> Group:
    for p in getattr(mod, "children", []):
        if "fundo" in p.name.lower():
            return p
    raise AssertionError(f"Nenhuma peça de fundo encontrada em {mod.name}")


# ── 1. Contrato formal das 5 abas e posse de widgets ────────────────────────────

def test_tab_order_and_widget_ownership(qapp):
    panel, _, _ = _make_panel(qapp)
    assert panel.tabs_module.count() == len(TAB_ORDER)

    for key in TAB_ORDER:
        contract = UI_TABS_CONTRACT[key]
        section = getattr(panel, contract.section_attr)
        assert panel.tabs_module.widget(contract.index) is section

        for w_name in contract.required_widgets:
            widget = getattr(panel, w_name)
            assert section.isAncestorOf(widget), (
                f"Widget '{w_name}' deve pertencer à aba '{key}' ({contract.section_attr})."
            )

        for f_name in contract.forbidden_widgets:
            widget = getattr(panel, f_name)
            assert not section.isAncestorOf(widget), (
                f"Widget proibido '{f_name}' vazou para a aba '{key}' ({contract.section_attr})."
            )


# ── 2. Aba 1 (Medidas): exatamente 5 campos universais visíveis ─────────────────

def test_medidas_5_universal_fields_and_corner_visibility(qapp):
    panel, scene, _ = _make_panel(qapp)
    panel.resize(420, 820)
    panel.show()

    mod = CabinetBuilder.build_module_group({
        "tipo": "balcao",
        "largura": 800.0,
        "altura": 720.0,
        "profundidade": 550.0,
    })
    scene.groups.append(mod)
    scene.selection = {mod}
    panel.load_module(mod)
    panel.tabs_module.setCurrentIndex(0)
    qapp.processEvents()

    expected_universal = {
        panel.cb_trocar_tipo,
        panel.sp_largura,
        panel.sp_altura,
        panel.sp_prof,
        panel.sp_elevacao,
        panel.sp_afastamento_parede,
    }
    for w in expected_universal:
        assert not w.isHidden(), f"Campo universal {w} deveria estar visível em Medidas."

    all_inputs = [
        w for w in panel.sec_dimensoes.findChildren(QWidget)
        if isinstance(w, (QSpinBox, QDoubleSpinBox, QComboBox))
    ]
    visible_inputs = {w for w in all_inputs if not w.isHidden()}
    assert visible_inputs == expected_universal, (
        f"Medidas deve exibir exatamente 6 campos universais; encontrados {len(visible_inputs)}."
    )

    # Em módulos de canto L, os controles extras de canto devem ficar visíveis
    mod_canto = CabinetBuilder.build_module_group({
        "tipo": "balcao_canto_l",
        "largura": 900.0,
        "altura": 720.0,
        "profundidade": 550.0,
    })
    scene.groups.append(mod_canto)
    scene.selection = {mod_canto}
    panel.load_module(mod_canto)
    qapp.processEvents()

    corner_visible_inputs = {w for w in all_inputs if not w.isHidden()}
    assert len(corner_visible_inputs) > len(expected_universal)
    assert not panel.sp_elevacao.isHidden()


# ── 3. Aba 2 (Estrutura): lado da porta, qtd_elem e travessa frontal ────────────

def test_lado_porta_visibility_predicate_and_dynamic_toggle(qapp):
    assert should_show_lado_porta_armario("balcao_canto", False, 1) is True
    assert should_show_lado_porta_armario("balcao", True, 1) is True
    assert should_show_lado_porta_armario("balcao", True, 3) is True
    assert should_show_lado_porta_armario("balcao", True, 2) is False
    assert should_show_lado_porta_armario("balcao", True, 4) is False
    assert should_show_lado_porta_armario("gaveteiro", False, 3) is False

    panel, scene, _ = _make_panel(qapp)
    mod_2p = CabinetBuilder.build_module_group({
        "tipo": "balcao",
        "largura": 800.0,
        "altura": 720.0,
        "profundidade": 550.0,
        "num_portas": 2,
    })
    scene.groups.append(mod_2p)
    scene.selection = {mod_2p}
    panel.load_module(mod_2p)

    # 2 portas -> par -> lado da porta isolada oculto
    assert panel.cb_lado_porta_armario.isHidden() is True

    # Alterar dinamicamente para 3 portas -> ímpar -> exibe seletor
    panel.sp_qtd_elem.setValue(3)
    assert panel.cb_lado_porta_armario.isHidden() is False

    # Voltar para 2 portas -> oculta novamente
    panel.sp_qtd_elem.setValue(2)
    assert panel.cb_lado_porta_armario.isHidden() is True

    # 1 porta -> ímpar -> exibe
    panel.sp_qtd_elem.setValue(1)
    assert panel.cb_lado_porta_armario.isHidden() is False

    # Balcão Canto Reto -> sempre exibe para lado cego
    mod_canto = CabinetBuilder.build_module_group({
        "tipo": "balcao_canto",
        "largura": 900.0,
        "altura": 720.0,
        "profundidade": 550.0,
    })
    scene.groups.append(mod_canto)
    scene.selection = {mod_canto}
    panel.load_module(mod_canto)
    assert panel.cb_lado_porta_armario.isHidden() is False

    # sp_recuo_porta_topo acompanha chk_travessa_frontal_em_pe
    panel.load_module(mod_2p)
    panel.chk_travessa_frontal_em_pe.setChecked(True)
    assert panel.sp_recuo_porta_topo.isHidden() is False
    panel.chk_travessa_frontal_em_pe.setChecked(False)
    assert panel.sp_recuo_porta_topo.isHidden() is True


def test_rack_nicho_gaveta_expoe_config_gaveteiro(qapp):
    assert should_show_config_gaveteiro("balcao_misto") is True
    assert should_show_config_gaveteiro("rack_nicho_gaveta") is True
    assert should_show_config_gaveteiro("gaveteiro") is False

    panel, scene, _ = _make_panel(qapp)
    rack = CabinetBuilder.build_module_group({
        "tipo": "rack_nicho_gaveta",
        "largura": 1600.0,
        "altura": 500.0,
        "profundidade": 450.0,
        "espessura": 18.0,
        "largura_gaveteiro": 600.0,
        "lado_gaveteiro": "direita",
        "num_gavetas": 2,
    })
    scene.groups.append(rack)
    scene.selection = {rack}
    panel.load_module(rack)

    assert panel.lbl_largura_gaveteiro.isHidden() is False
    assert panel.sp_largura_gaveteiro.isHidden() is False
    assert panel.sp_largura_gaveteiro.value() == 600
    assert panel.lbl_lado_gaveteiro.isHidden() is False
    assert panel.cb_lado_gaveteiro.isHidden() is False
    assert panel.cb_lado_gaveteiro.currentIndex() == 1
    assert panel.sp_qtd_elem.value() == 2


# ── 4. Padrões de fundo (5mm/10mm) e bloqueio pela travessa traseira em pé ──────

def test_fundo_defaults_and_rear_stretcher_lock(qapp, isolated_prefs):
    assert DEFAULT_PROF_RASGO_MM == 5.0
    assert DEFAULT_RECUO_FUNDO_MM == 10.0
    assert DEFAULT_PREFERENCES["global"]["prof_rasgo_mm"] == 5.0
    assert DEFAULT_PREFERENCES["global"]["recuo_fundo_mm"] == 10.0

    assert DEFAULT_MODULE_PARAMS["prof_rasgo"] == pytest.approx(5.0)
    assert DEFAULT_MODULE_PARAMS["recuo_fundo"] == pytest.approx(10.0)
    assert DEFAULT_MODULE_PARAMS["folga_frentes_mm"] == pytest.approx(3.0)

    panel, scene, _ = _make_panel(qapp)
    assert panel.sp_prof_rasgo.value() == 5
    assert panel.sp_recuo_fundo.value() == 10

    mod = CabinetBuilder.build_module_group({
        "tipo": "balcao",
        "largura": 800.0,
        "altura": 720.0,
        "profundidade": 550.0,
        "tem_fundo": True,
        "tipo_fundo": "rasgo",
        "travessa_traseira_em_pe": False,
    })
    scene.groups.append(mod)
    scene.selection = {mod}
    panel.load_module(mod)

    assert panel.sp_recuo_fundo.isEnabled() is True
    assert panel.sp_recuo_fundo.value() == 10

    # Marcar travessa traseira em pé bloqueia recuo_fundo na espessura da travessa (15mm)
    panel.chk_travessa_traseira_em_pe.setChecked(True)
    assert panel.sp_recuo_fundo.isEnabled() is False
    assert panel.sp_recuo_fundo.value() == 15

    # Desmarcar restaura para 10mm e libera edição
    panel.chk_travessa_traseira_em_pe.setChecked(False)
    assert panel.sp_recuo_fundo.isEnabled() is True
    assert panel.sp_recuo_fundo.value() == 10

    # No 3D: com travessa_traseira_em_pe=False, fundo tem recuo de 10mm e rasgo de 5mm
    fundo = _find_fundo_piece(mod)
    _, _, _, y_max_fundo, _, _ = _collect_bounds(fundo)
    recuo_real_mm = (0.550 - y_max_fundo) * 1000.0
    assert recuo_real_mm == pytest.approx(10.0, abs=0.05)

    lateral = next(p for p in mod.children if "lateral" in p.name.lower())
    ops = lateral.ext.get("trazomob", {}).get("operacoes", [])
    rasgos = [o for o in ops if "rasgo" in str(o.get("tipo", "")).lower() or "canal" in str(o.get("descricao", "")).lower()]
    assert rasgos, "Lateral deveria ter usinagem de rasgo para o fundo."
    assert any(float(r.get("profundidade", 0)) == pytest.approx(5.0) for r in rasgos)
    assert any(float(r.get("y", 0)) == pytest.approx(10.0) for r in rasgos)


# ── 5. Aba 3 (Puxadores): remoção da caixa escura / diagram 115x80 do Gola ──────

def test_puxadores_gola_clean_layout(qapp):
    panel, scene, _ = _make_panel(qapp)
    mod = CabinetBuilder.build_module_group({
        "tipo": "balcao",
        "largura": 800.0,
        "altura": 720.0,
        "profundidade": 550.0,
        "puxador_tipo": "perfil",
    })
    scene.groups.append(mod)
    scene.selection = {mod}
    panel.load_module(mod)

    assert panel.frame_perfil.frameShape() == QFrame.NoFrame
    assert "#F8FAFC" not in (panel.frame_perfil.styleSheet() or "").upper()
    assert panel.lbl_perfil_diagram.isHidden() is True
    for attr in (
        "frame_perfil",
        "cb_perfil_modelo",
        "btn_gerenciar_perfis",
        "cb_altura_perfil",
        "sp_desconto_perfil",
        "lbl_perfil_diagram",
    ):
        assert hasattr(panel, attr)


# ── 6. Aba 5 (Avançado): folga_frentes_mm destravada + reconstrução 3D ─────────

def test_folga_frentes_ui_and_builder_propagation(qapp):
    assert DEFAULT_FOLGA_FRENTES_MM == 3.0
    panel, scene, _ = _make_panel(qapp)
    assert panel.sp_folga_frentes.minimum() == 0
    assert panel.sp_folga_frentes.maximum() == 15
    assert panel.sp_folga_frentes.value() == 3

    # Balcão 2P com folga = 2mm e sem travessa frontal em pé (sem recuo topo)
    mod_balcao = CabinetBuilder.build_module_group({
        "tipo": "balcao",
        "largura": 800.0,
        "altura": 720.0,
        "profundidade": 550.0,
        "rodape": 100.0,
        "num_portas": 2,
        "travessa_frontal_em_pe": False,
        "folga_frentes_mm": 2.0,
    })
    portas = _find_front_pieces(mod_balcao, "porta")
    assert len(portas) == 2
    p1_b = _collect_bounds(portas[0])
    p2_b = _collect_bounds(portas[1])
    # Cada porta: (0.800 - 3 * 0.002) / 2 = 0.397m; vão entre elas = 0.002m; Z = 0.100 + 0.002 = 0.102m
    assert (p1_b[1] - p1_b[0]) == pytest.approx(0.397, abs=1e-4)
    assert (p2_b[0] - p1_b[1]) == pytest.approx(0.002, abs=1e-4)
    assert p1_b[4] == pytest.approx(0.102, abs=1e-4)
    assert p1_b[5] == pytest.approx(0.718, abs=1e-4)

    # Gaveteiro 3G com folga = 2mm
    mod_gav = CabinetBuilder.build_module_group({
        "tipo": "gaveteiro",
        "largura": 600.0,
        "altura": 720.0,
        "profundidade": 550.0,
        "rodape": 100.0,
        "num_gavetas": 3,
        "travessa_frontal_em_pe": False,
        "folga_frentes_mm": 2.0,
    })
    frentes_gav = _find_front_pieces(mod_gav, "frente")
    assert len(frentes_gav) == 3
    frentes_gav.sort(key=lambda g: _collect_bounds(g)[4])
    g1_b = _collect_bounds(frentes_gav[0])
    g2_b = _collect_bounds(frentes_gav[1])
    assert (g1_b[1] - g1_b[0]) == pytest.approx(0.596, abs=1e-4)
    assert (g2_b[4] - g1_b[5]) == pytest.approx(0.002, abs=1e-4)

    # Aéreo 2P com folga = 2mm
    mod_aereo = CabinetBuilder.build_module_group({
        "tipo": "aereo",
        "largura": 800.0,
        "altura": 700.0,
        "profundidade": 350.0,
        "num_portas": 2,
        "folga_frentes_mm": 2.0,
    }, offset=(0.0, 0.0, 0.0))
    portas_aer = _find_front_pieces(mod_aereo, "porta")
    assert len(portas_aer) == 2
    pa1_b = _collect_bounds(portas_aer[0])
    pa2_b = _collect_bounds(portas_aer[1])
    assert (pa2_b[0] - pa1_b[1]) == pytest.approx(0.002, abs=1e-4)
    assert pa1_b[4] == pytest.approx(0.002, abs=1e-4)

    # Round-trip completo pela UI
    scene.groups.append(mod_balcao)
    scene.selection = {mod_balcao}
    panel.load_module(mod_balcao)
    assert panel.sp_folga_frentes.isEnabled() is True
    assert panel.sp_folga_frentes.value() == 2

    panel.sp_folga_frentes.setValue(4)
    panel._apply_changes_to_selected()
    rebuilt = list(scene.selection)[0]
    assert rebuilt.ext["trazomob_module"]["folga_frentes_mm"] == pytest.approx(4.0)
    rebuilt_portas = _find_front_pieces(rebuilt, "porta")
    rp1_b = _collect_bounds(rebuilt_portas[0])
    rp2_b = _collect_bounds(rebuilt_portas[1])
    assert (rp2_b[0] - rp1_b[1]) == pytest.approx(0.004, abs=1e-4)


# ── 7. Aba 1 (Medidas): sp_elevacao carrega e desloca eixo Z do módulo ─────────

def test_elevacao_load_and_apply(qapp):
    panel, scene, _ = _make_panel(qapp)
    mod = CabinetBuilder.build_module_group({
        "tipo": "balcao",
        "largura": 800.0,
        "altura": 720.0,
        "profundidade": 550.0,
    }, offset=(0.0, 0.0, 0.0))
    scene.groups.append(mod)
    scene.selection = {mod}

    panel.load_module(mod)
    assert panel.sp_elevacao.value() == 0

    panel.sp_elevacao.setValue(250)
    panel._apply_changes_to_selected()

    rebuilt = list(scene.selection)[0]
    assert rebuilt.ext["trazomob_module"]["elevacao_mm"] == pytest.approx(250.0)
    _, _, _, _, min_z, _ = _collect_bounds(rebuilt)
    assert min_z == pytest.approx(0.250, abs=1e-4)

    panel.load_module(rebuilt)
    assert panel.sp_elevacao.value() == 250
