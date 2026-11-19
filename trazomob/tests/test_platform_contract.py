# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Contrato entre o TrazoMob e o IngeTrazo.

Este teste falha quando o host muda algo de que o plugin depende. É o alarme
que falta hoje: em vez de descobrir num release que ``_dirty_group_chunks``
mudou de módulo, a suíte aponta o símbolo exato.

Os símbolos marcados como dívida (prefixo ``_``) são API interna do host que
o plugin ainda usa. A meta é zerar essa lista: cada um que sai daqui vira um
gancho oficial na API de extensões.
"""
import importlib
import re
from pathlib import Path

import pytest

from trazomob.integrations import platform as host

# Contrato usado hoje pelo plugin: módulo do host -> símbolos.
# ``DEBT`` são símbolos privados que precisam virar API pública.
CONTRACT = {
    "core.group": [
        "Group", "iter_placements", "transformed_mesh", "carry_axes",
        "group_frame", "effective_material",
        "DEBT:_remap_uvws",
    ],
    "core.mesh": ["Mesh", "Face"],
    "core.scene": ["Scene"],
    "core.layers": ["Layer"],
    "core.style": ["BUILTIN_STYLES", "style_by_name"],
    "core.history": [
        "Command", "SnapshotImport", "MoveGroupCommand", "CompoundCommand",
        "MakeNestedGroupCommand", "ExplodeGroupCommand", "HideCommand",
        "SetPluginDataCommand", "RotateGroupCommand", "ScaleGroupCommand",
        "MoveGroupCommand", "rotation_matrix", "scale_matrix",
        "invert_scale_factor",
        "DEBT:_dirty_group_chunks",
    ],
    "core.triangulate": ["triangulate"],
    "core.orient": ["orient_outward"],
    "core.materials": ["effective_attrs"],
    "core.snap": ["face_plane_world"],
    "core.texture": ["face_uv_axes"],
    "core.units": [
        "bare_number_scale", "model_precision", "model_unit", "format_length",
    ],
    "core.image_plane": ["ImagePlane"],
    "core.paths": ["app_root", "user_log_dir"],
    "core.i18n": ["tr"],
    "core.library": ["index", "cached_thumbnail", "prefetch_thumbnails"],
    "core.render_blender": [
        "LIGHT_KINDS", "DEFAULT_POWER", "clean_lights", "sun_toward",
        "camera_dict", "clean_env",
    ],
    "core.topology": ["DEBT:_key"],
    "tools.base": ["Tool", "ToolContext"],
    "tools.select": ["selection_mode"],
    "formats.igz": [],
    "formats.meshexport": ["world_faces"],
    "formats.gltf": ["save_glb"],
    "views.extension_api": ["ExtensionApp", "API_VERSION"],
}


def _symbols(names):
    for raw in names:
        debt = raw.startswith("DEBT:")
        yield (raw.removeprefix("DEBT:"), debt)


@pytest.mark.parametrize("module_name", sorted(CONTRACT))
def test_host_module_is_importable(module_name):
    assert importlib.import_module(module_name) is not None


@pytest.mark.parametrize(
    "module_name,symbol,is_debt",
    [
        (module_name, symbol, debt)
        for module_name, names in CONTRACT.items()
        for symbol, debt in _symbols(names)
    ],
)
def test_host_symbol_exists(module_name, symbol, is_debt):
    module = importlib.import_module(module_name)
    if not hasattr(module, symbol):
        kind = "dívida de API interna" if is_debt else "API pública"
        pytest.fail(
            f"{module_name}.{symbol} desapareceu ({kind}). "
            "Ajuste trazomob/integrations/platform.py e o ponto de uso antes de "
            "atualizar o IngeTrazo."
        )


def test_extension_api_version_is_supported():
    from views.extension_api import API_VERSION
    assert API_VERSION >= 2, (
        "O TrazoMob usa recursos da API 2 (paineis nomeados, add_pickable, "
        "add_outliner_kind)."
    )


class _FakeOwner:
    def __init__(self):
        self.value = "original"


def test_install_hook_is_idempotent_and_reversible():
    owner = _FakeOwner()

    def uninstall():
        for feature in list(host.installed_hooks()):
            host.restore_hook(feature)

    uninstall()
    try:
        assert host.install_hook("test.value", owner, "value",
                                 lambda original: "wrapper") is True
        assert owner.value == "wrapper"
        assert host.install_hook("test.value", owner, "value",
                                 lambda original: "outro") is False
        assert owner.value == "wrapper"
        assert host.restore_hook("test.value") is True
        assert owner.value == "original"
    finally:
        uninstall()


def test_install_hook_degrades_when_attribute_is_gone():
    owner = _FakeOwner()
    assert host.install_hook("test.missing", owner, "nao_existe",
                             lambda original: original) is False
    assert not host.hook_installed("test.missing")


class _FakeStyle:
    def __init__(self, name="Default"):
        self.name = name
        self.edges = True
        self.profiles = False

    def copy(self):
        return _FakeStyle(self.name)


class _FakeScene:
    def __init__(self):
        self.display_style = _FakeStyle()


class _FakeViewport:
    def __init__(self):
        self.scene = _FakeScene()
        self.updates = 0

    def update(self):
        self.updates += 1


def test_style_fallback_works_without_host_helpers():
    """Num host sem ``_apply_display_style`` o plugin ainda troca o estilo."""
    viewport = _FakeViewport()
    preset = _FakeStyle("X-ray")
    assert host.apply_display_style(None, viewport, preset) is True
    assert viewport.scene.display_style.name == "X-ray"
    assert viewport.updates == 1

    assert host.set_style_field(None, viewport, "edges", False) is True
    assert viewport.scene.display_style.edges is False


def test_capabilities_are_empty_without_a_window():
    assert host.capabilities(window=None, viewport=None) == {}
    assert host.supports("display_style") is False


# Ganchos que o plugin precisa instalar. Se um deles não instala, alguma
# funcionalidade do TrazoMob morre em silêncio (foi assim que o undo/redo
# paramétrico ficou anos sem funcionar: o import de TranslateGroupCommand
# falhava dentro de um try/except).
EXPECTED_HOOKS = {
    "group.copy",
    "history.move",
    "history.rotate.do",
    "history.rotate.undo",
    "history.scale.do",
    "history.scale.undo",
    "move.commit",
    "move.lock",
    "render.led_lights",
    "scale.capture",
    "scale.ruler_snap",
}

HOOK_TARGETS = {
    "core.group": ["copy_group"],
    "core.history": ["RotateGroupCommand", "ScaleGroupCommand", "MoveGroupCommand"],
    "core.render_blender": ["clean_lights"],
    "tools.move": ["MoveTool", "gather_targets"],
    "tools.scale": ["ScaleTool"],
}


@pytest.mark.parametrize(
    "module_name,symbol",
    [(m, s) for m, names in HOOK_TARGETS.items() for s in names],
)
def test_hook_target_exists(module_name, symbol):
    module = importlib.import_module(module_name)
    assert hasattr(module, symbol), (
        f"{module_name}.{symbol} desapareceu: o gancho correspondente em "
        "trazomob/integrations/hooks.py deixaria de instalar."
    )


def test_every_expected_hook_installs():
    from trazomob.integrations import hooks

    host.restore_all_hooks()
    try:
        hooks.apply_runtime_hooks()
        installed = set(host.installed_hooks())
        assert EXPECTED_HOOKS <= installed, (
            "ganchos que não instalaram: "
            + ", ".join(sorted(EXPECTED_HOOKS - installed))
        )
    finally:
        host.restore_all_hooks()


class _FakeExtensionApp:
    def __init__(self):
        self.calls = []

    def register_light_kind(self, *args):
        self.calls.append("light_kind")

    def add_group_copy_hook(self, fn):
        from core import extension_hooks
        self.calls.append("copy")
        extension_hooks.add_copy_hook(fn)

    def add_move_filter(self, fn):
        from core import extension_hooks
        self.calls.append("move_filter")
        extension_hooks.add_move_filter(fn)

    def add_group_transform_hook(self, fn):
        from core import extension_hooks
        self.calls.append("transform")
        extension_hooks.add_transform_hook(fn)


def test_official_extension_api_is_preferred_over_monkeypatching():
    """Num host que oferece a API oficial, copy/luz/movimento/transformação
    vão por ela; só os pontos ainda não expostos caem no patch.

    O IngeTrazo puro não tem esses métodos — aí o teste é pulado e o
    caminho de monkeypatch (test_every_expected_hook_installs) vale.
    """
    extension_hooks = pytest.importorskip(
        "core.extension_hooks",
        reason="host sem a API oficial de ganchos; o TrazoMob usa patch")
    from trazomob.integrations import hooks

    host.restore_all_hooks()
    extension_hooks.clear()
    try:
        app = _FakeExtensionApp()
        hooks.apply_runtime_hooks(app)
        assert set(app.calls) == {"light_kind", "copy", "move_filter", "transform"}
        assert extension_hooks.registered() == {
            "transform": 1, "copy": 1, "move_filter": 1}
        assert set(host.installed_hooks()) == {
            "move.commit", "scale.ruler_snap", "scale.capture"}
    finally:
        extension_hooks.clear()
        host.restore_all_hooks()



# ---------------------------------------------------------------------------
# Catraca da dívida: a API privada do host não pode crescer.
# ---------------------------------------------------------------------------
# Contagem congelada em 2026-11-02 (repartida em 2026-11-11 quando o setup saiu
# de __init__.py). Cada número é dívida conhecida: o alvo é chegar a zero e mover
# o acesso para platform.py. Se este teste falhar, o código novo tocou um
# ``_privado`` do host fora da camada anticorrupção.
PRIVATE_ATTR_BASELINE = {
    "bootstrap.py": 1,
    "builder.py": 4,
    "context_menu.py": 1,
    "interact.py": 16,
    "magnetic_drag.py": 11,
    "material_editor_dialog.py": 5,
    "module_operations.py": 1,
    "sidebar.py": 1,
    "wall_selection.py": 6,
}

PRIVATE_IMPORT_BASELINE = {
    "builder.py": 3,
    "interact.py": 1,
    "magnetic_drag.py": 2,
    "wall_selection.py": 3,
}

_ATTR_RE = re.compile(r"\b(main_window|window|app|viewport)\s*\._[A-Za-z]")
_IMPORT_RE = re.compile(
    r"from\s+(?:core|tools|views|formats)\.[A-Za-z_.]+\s+import\s+[^\n]*\b_[A-Za-z]")
_EXEMPT = {"platform.py", "hooks.py"}


def _counts(pattern):
    root = Path(__file__).resolve().parents[1]
    result = {}
    for path in root.glob("*.py"):
        if path.name in _EXEMPT:
            continue
        count = len(pattern.findall(path.read_text(encoding="utf-8")))
        if count:
            result[path.name] = count
    return result


@pytest.mark.parametrize("pattern,baseline,label", [
    (_ATTR_RE, PRIVATE_ATTR_BASELINE, "acesso a atributo privado do host"),
    (_IMPORT_RE, PRIVATE_IMPORT_BASELINE, "import de símbolo privado do host"),
])
def test_private_host_api_debt_does_not_grow(pattern, baseline, label):
    current = _counts(pattern)
    grew = {
        name: (baseline.get(name, 0), count)
        for name, count in current.items()
        if count > baseline.get(name, 0)
    }
    assert not grew, (
        f"{label} aumentou: "
        + ", ".join(f"{n} {old}->{new}" for n, (old, new) in grew.items())
        + ". Passe o acesso por trazomob/integrations/platform.py."
    )


