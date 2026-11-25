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


def test_no_monkeypatch_infrastructure_is_exposed():
    """O fork é first-party: o host chama o TrazoMob, não o contrário."""
    for name in ("install_hook", "hook_installed", "installed_hooks",
                 "restore_hook", "restore_all_hooks"):
        assert not hasattr(host, name)


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


# Pontos do host que chamam o TrazoMob. Se um deles desaparecer, a chamada
# direta some junto e a funcionalidade morre em silêncio.
HOST_CALL_TARGETS = {
    "core.group": ["copy_group"],
    "core.history": [
        "RotateGroupCommand", "ScaleGroupCommand", "MoveGroupCommand"],
    "core.render_blender": ["clean_lights", "write_job"],
    "tools.move": ["MoveTool", "gather_targets"],
    "tools.scale": ["ScaleTool"],
    "views.viewport": ["Viewport"],
    "plugins.render_blender": ["draw_lights"],
    "formats.igz": ["load_into"],
    "views.main_window": ["MainWindow"],
}


@pytest.mark.parametrize(
    "module_name,symbol",
    [(m, s) for m, names in HOST_CALL_TARGETS.items() for s in names],
)
def test_host_call_target_exists(module_name, symbol):
    module = importlib.import_module(module_name)
    assert hasattr(module, symbol), (
        f"{module_name}.{symbol} desapareceu: um ponto de chamada direta do "
        "TrazoMob foi perdido."
    )


def test_host_files_call_trazomob_directly():
    root = Path(__file__).resolve().parents[2]
    expectations = {
        "core/group.py": "host_calls",
        "core/history.py": "host_calls",
        "core/render_blender.py": "host_calls",
        "tools/move.py": "host_calls",
        "tools/scale.py": "host_calls",
        "views/viewport.py": "host_calls",
        "plugins/render_blender.py": "host_calls",
        "formats/igz.py": "library_links",
        "views/main_window.py": "library_links",
    }
    for relative, module in expectations.items():
        text = (root / relative).read_text(encoding="utf-8")
        assert "from trazomob.integrations import %s" % module in text, relative


def test_trazomob_has_no_runtime_hooks():
    """Nenhum módulo do TrazoMob pode instalar monkeypatch no host."""
    root = Path(__file__).resolve().parents[1]
    offenders = []
    for path in root.rglob("*.py"):
        if path.name == "test_platform_contract.py":
            continue
        text = path.read_text(encoding="utf-8")
        if "install_hook(" in text or "apply_runtime_hooks(" in text:
            offenders.append(path.relative_to(root).as_posix())
    assert not offenders, "hooks residuais: " + ", ".join(offenders)



# ---------------------------------------------------------------------------
# Catraca da dívida: a API privada do host não pode crescer.
# ---------------------------------------------------------------------------
# Contagem congelada em 2026-11-20, quando a catraca passou a percorrer as
# subpastas (antes usava ``root.glob("*.py")`` e via só 3 de 157 arquivos).
# Cada número é dívida conhecida: o alvo é chegar a zero e mover o acesso para
# platform.py. Se este teste falhar, o código novo tocou um ``_privado`` do host
# fora da camada anticorrupção.
PRIVATE_ATTR_BASELINE = {}

PRIVATE_IMPORT_BASELINE = {
    "render/lighting.py": 1,
}

_ATTR_RE = re.compile(r"\b(main_window|window|app|viewport)\s*\._[A-Za-z]")
_IMPORT_RE = re.compile(
    r"from\s+(?:core|tools|views|formats)\.[A-Za-z_.]+\s+import\s+[^\n]*\b_[A-Za-z]")
_EXEMPT = {"platform.py", "host_calls.py"}
# Pastas que nao fazem parte do codigo de producao do Trazomob.
_SKIP_DIRS = {"tests", "scripts", "blender_scripts"}


def _source_files():
    root = Path(__file__).resolve().parents[1]
    for path in sorted(root.rglob("*.py")):
        if _SKIP_DIRS.intersection(path.relative_to(root).parts):
            continue
        if path.name in _EXEMPT:
            continue
        yield root, path


def _counts(pattern):
    result = {}
    for root, path in _source_files():
        count = len(pattern.findall(path.read_text(encoding="utf-8")))
        if count:
            result[path.relative_to(root).as_posix()] = count
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


@pytest.mark.parametrize("baseline,label", [
    (PRIVATE_ATTR_BASELINE, "acesso a atributo privado do host"),
    (PRIVATE_IMPORT_BASELINE, "import de símbolo privado do host"),
])
def test_private_host_api_baseline_has_no_stale_paths(baseline, label):
    """Garante que a catraca continue enxergando todo arquivo referenciado."""
    sources = {path.relative_to(root).as_posix() for root, path in _source_files()}
    orphans = sorted(set(baseline) - sources)
    assert not orphans, (
        f"{label}: chaves de baseline sem arquivo correspondente: {orphans}. "
        "O baseline deve usar caminhos relativos a trazomob/."
    )


