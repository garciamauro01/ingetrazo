# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Pré-assa decoração importada num ``.igz`` nativo, antes da inserção.

Marcenaria é paramétrica e não precisa disso: o builder gera a malha na hora.
Decoração (SKP, DAE, GLB, OBJ) chega em formato estrangeiro e paga a conversão
na primeira vez em que é arrastada para a cena — exatamente o pico que o
Promob evita ao distribuir o ``.mob3d`` já pronto.

O custo é pago quando o objeto entra na biblioteca (gancho em
``user_library.register``). O cache já sai **orientado, dimensionado e
centrado**: o ``fit()`` do host, que percorre cada vértice duas vezes para
calcular bounds e aplicar a matriz, roda uma única vez no assado.

Na inserção, ``load_component`` devolve direto o grupo lido do ``.igz`` —
sem ``fit``, sem ``flatten`` e sem materializar a malha lazy (~9 s -> ~0,2 s
num SKP de 100 mil faces).

A chave do cache inclui ``(caminho, mtime, tamanho, matrix, cm, anchor, fitted)``:
mudou a origem **ou** a forma de encaixe, mudou o arquivo. A ficha do host
(``library.json``) continua intocada.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from PySide6.QtGui import QMatrix4x4

from . import library_links
from . import platform as host

logger = logging.getLogger("trazomob.decor_bake")

#: Formatos que realmente precisam de conversão. ``.igz`` já é nativo e não
#: entra aqui: o carregador do host já lê esse formato direto.
BAKE_SUFFIXES = frozenset({".skp", ".dae", ".obj", ".glb", ".gltf"})

#: Nomes dos ganchos registrados em ``platform`` (para testes restaurarem).
HOOK_NAME = "decor.bake.user_library.register"
HOOK_LOAD_NAME = "decor.bake.component_loader.load_group"
HOOK_COMPONENT_NAME = "decor.bake.component_loader.load_component"

#: Matriz 3×3 identidade, no mesmo formato que o host passa a ``load_group``.
_IDENTITY = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)


def bake_root() -> Path:
    """Pasta dos protótipos assados, dentro da raiz da biblioteca do usuário."""
    return library_links.cache_root().parent / "baked"


def is_bakeable(path: Path | None) -> bool:
    return path is not None and path.suffix.lower() in BAKE_SUFFIXES


def source_of(entry: dict) -> Path | None:
    """O arquivo de origem de uma ficha da biblioteca do host."""
    if not isinstance(entry, dict):
        return None
    try:
        from core import user_library
        resolved = user_library.resolve(entry)
    except Exception:  # noqa: BLE001 - host sem resolve, cai para os campos
        resolved = None
    if resolved is None:
        raw = entry.get("origen") or entry.get("archivo")
        resolved = Path(str(raw)).expanduser() if raw else None
    if resolved is None:
        return None
    path = Path(str(resolved)).expanduser()
    return path if path.is_file() else None


def _norm_config(*, matrix=None, cm=None, anchor: str = "base",
                 fitted: bool = False) -> dict | None:
    """Configuração JSON-safe que faz parte da identidade do protótipo."""
    return {
        "matrix": [float(v) for v in matrix] if matrix is not None else None,
        "cm": [float(v) for v in cm] if cm else [],
        "anchor": str(anchor or "base"),
        "fitted": bool(fitted),
    }


def matrix_for_entry(entry: dict) -> tuple:
    """A mesma matriz que ``component_loader.load_component`` calcularia."""
    from views import component_loader

    matrix = entry.get("matrix")
    if matrix:
        return tuple(float(v) for v in matrix)
    m = component_loader.matrix_for(entry.get("unidad") or "m",
                                    bool(entry.get("y_up")))
    factor = float(entry.get("escala") or 1.0)
    if factor != 1.0:
        m = tuple(v * factor for v in m)
    return m


def config_for_entry(entry: dict, *, anchor: str = "base",
                     fitted: bool = True) -> dict:
    """A configuração de encaixe de uma ficha da biblioteca."""
    return _norm_config(matrix=matrix_for_entry(entry),
                        cm=entry.get("cm"), anchor=anchor, fitted=fitted)


def cache_key(path: Path, config: dict | None = None) -> str:
    """Chave estável e barata: um ``stat``, nenhuma leitura do arquivo."""
    st = path.stat()
    raw = "%s|%d|%d" % (path.resolve(), st.st_mtime_ns, st.st_size)
    if config is not None:
        raw += "|" + json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def bake_path(path: Path, config: dict | None = None) -> Path:
    key = cache_key(path, config)
    return bake_root() / key[:2] / (key + ".igz")


def face_count(group) -> int:
    mesh = getattr(group, "mesh", None)
    return len(getattr(mesh, "faces", ()) or ())


def vertex_count(group) -> int:
    mesh = getattr(group, "mesh", None)
    return len(getattr(mesh, "vertices", ()) or (()))


def _is_identity_matrix(matrix) -> bool:
    """True para a matriz 3×3/4×4 identidade que o host costuma passar."""
    if matrix is None:
        return True
    if not isinstance(matrix, (tuple, list)):
        return False
    values = list(matrix)
    if len(values) == 9:
        expected = list(_IDENTITY)
    elif len(values) == 16:
        expected = [1.0, 0.0, 0.0, 0.0,
                    0.0, 1.0, 0.0, 0.0,
                    0.0, 0.0, 1.0, 0.0,
                    0.0, 0.0, 0.0, 1.0]
    else:
        return False
    try:
        return all(abs(float(a) - float(b)) < 1e-12
                   for a, b in zip(values, expected))
    except (TypeError, ValueError):
        return False


def _apply_matrix(group, matrix):
    """Aplica a matrix 3×3 exatamente como ``component_loader._bake`` faz."""
    from core.group import Group, transformed_mesh, world_mesh

    values = [float(v) for v in matrix]
    m = QMatrix4x4(values[0], values[1], values[2], 0.0,
                   values[3], values[4], values[5], 0.0,
                   values[6], values[7], values[8], 0.0,
                   0.0, 0.0, 0.0, 1.0)
    return Group(transformed_mesh(world_mesh(group), m),
                 name=getattr(group, "name", "") or "")


def _meta_path(cache: Path) -> Path:
    return cache.with_suffix(".json")


def _save_meta(meta: dict) -> None:
    try:
        _meta_path(Path(meta["cache"])).write_text(
            json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    except (OSError, TypeError, ValueError):
        logger.debug("sidecar do cache não pôde ser gravado")


def _read_meta(cache: Path) -> dict | None:
    try:
        data = json.loads(_meta_path(cache).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def _warm_chunk_cache(group) -> bool:
    """Deixa o chunk da decoração pronto no cache de disco do host.

    O ``Viewport`` já persiste chunks por digest estável do conteúdo, mas só
    quando desenha o grupo — ou seja, na primeira inserção. Rodar o mesmo
    caminho durante o cadastro paga isso uma vez, junto com o assado, e a
    primeira abertura do objeto lê o array pronto em vez de reconstruí-lo.
    A gravação é síncrona porque o cadastro pode inserir logo em seguida.
    """
    try:
        from core.scene import Scene
        from views import array_bake
        from views.viewport import Viewport
    except Exception:  # noqa: BLE001 - fora do host
        return False
    if face_count(group) < getattr(Viewport, "_CHUNK_CACHE_MIN_FACES", 5000):
        return False
    if array_bake.can_bake(group.mesh):
        # O motor nativo monta o chunk direto dos arrays e não consulta o
        # cache de disco: escrever aqui só custaria tempo e espaço à toa.
        return False
    try:
        scene = Scene()
        scene.groups.append(group)
        # __new__: o builder de chunk não abre contexto GL, e o cadastro pode
        # rodar em threads/testes sem QApplication.
        vp = Viewport.__new__(Viewport)
        vp.scene = scene
        # _group_chunk agenda a gravação numa thread; aqui queremos o arquivo
        # pronto antes de continuar, então fazemos essa parte nós mesmos.
        store = Viewport._chunk_cache_store
        vp._chunk_cache_store = None
        entry = vp._group_chunk(group)
        if entry is None:
            return False
        store(vp, group.mesh, entry, sync=True)
        return True
    except Exception:  # noqa: BLE001 - cache é otimização, não requisito
        logger.debug("não foi possível aquecer o cache de chunk da decoração")
        return False


def bake_source(path: Path, *, name: str | None = None, index: int = 0,
                force: bool = False, config: dict | None = None) -> dict | None:
    """Converte ``path`` uma vez e grava o protótipo em ``.igz``.

    Com ``config["fitted"]``, a geometria já sai orientada, dimensionada e
    centrada — idêntica ao que ``component_loader.load_component`` devolveria.
    Devolve metadados somente leitura; ``None`` quando a origem não é um
    formato de decoração conhecido ou não produziu geometria alguma.
    """
    src = Path(str(path)).expanduser()
    if not src.is_file() or not is_bakeable(src):
        return None
    try:
        out = bake_path(src, config)
    except OSError:
        logger.debug("não foi possível calcular a chave de %r", src)
        return None

    meta = {
        "key": out.stem,
        "cache": str(out),
        "source": str(src),
        "faces": 0,
        "vertices": 0,
        "bytes": 0,
        "config": config,
        "bounds": None,
        "chunk_ready": False,
    }
    if out.is_file() and not force:
        try:
            meta["bytes"] = out.stat().st_size
        except OSError:
            pass
        saved = _read_meta(out)
        if saved is not None:
            meta.update({k: v for k, v in saved.items()
                         if k in ("faces", "vertices", "bytes", "source",
                                  "bounds", "config", "chunk_warmed",
                                  "chunk_ready")})
        return meta

    group = library_links._reimport(src, {
        "name": name or src.stem,
        "index": int(index),
    })
    if group is None or not face_count(group):
        logger.debug("origem %r não produziu geometria; nada foi assado", src)
        return None

    if config:
        matrix = config.get("matrix")
        if matrix and not _is_identity_matrix(matrix):
            group = _apply_matrix(group, matrix)
        if config.get("fitted"):
            from views import component_loader
            group = component_loader.fit(group,
                                         cm=config.get("cm") or None,
                                         anchor=config.get("anchor") or "base")
            group = component_loader.flatten(group)

    try:
        library_links._write_cache(group, out)
    except Exception:  # noqa: BLE001 - cache é otimização, não requisito
        logger.exception("falha ao assar %r", src)
        return None
    meta["faces"] = face_count(group)
    meta["vertices"] = vertex_count(group)
    from views import component_loader
    lo, hi = component_loader.bounds(group)
    meta["bounds"] = [list(lo), list(hi)]
    try:
        meta["bytes"] = out.stat().st_size
    except OSError:
        pass
    meta["chunk_warmed"] = _warm_chunk_cache(group)
    meta["chunk_ready"] = True
    _save_meta(meta)
    return meta


def ensure_for_entry(entry: dict, *, anchor: str = "base") -> dict | None:
    """Garante que a decoração de uma ficha já está assada e pronta para pôr."""
    src = source_of(entry)
    if src is None:
        return None
    return bake_source(src, name=str(entry.get("nombre") or src.stem),
                       config=config_for_entry(entry, anchor=anchor))


def load_baked(path: Path):
    """Lê o protótipo assado sem passar pelo gancho de load do host.

    Um cache criado antes deste aquecimento é preparado aqui uma única vez —
    é o mesmo trabalho que o primeiro desenho já faria, só que antecedendo a
    inserção em vez de coincidir com o primeiro clique.
    """
    path = Path(str(path)).expanduser()
    group = library_links._read_igz_group(path)
    if group is not None:
        meta = _read_meta(path)
        if meta is not None and not meta.get("chunk_ready"):
            _warm_chunk_cache(group)
            meta["chunk_ready"] = True
            _save_meta(meta)
    return group


def load_for_entry(entry: dict, *, anchor: str = "base"):
    """O protótipo assado de uma ficha, ou ``None`` se ainda não existe."""
    src = source_of(entry)
    if src is None or not is_bakeable(src):
        return None
    config = config_for_entry(entry, anchor=anchor)
    try:
        out = bake_path(src, config)
    except OSError:
        return None
    if not out.is_file():
        return None
    return load_baked(out)


def bake_stats() -> dict:
    """Contagem simples do cache, útil no benchmark e no diagnóstico."""
    root = bake_root()
    if not root.is_dir():
        return {"files": 0, "bytes": 0}
    files = list(root.rglob("*.igz"))
    return {
        "files": len(files),
        "bytes": sum(p.stat().st_size for p in files),
    }


def _make_register_wrapper(original):
    def register(*args, **kwargs):
        entry = original(*args, **kwargs)
        if isinstance(entry, dict):
            try:
                ensure_for_entry(entry)
            except Exception:  # noqa: BLE001 - registrar nunca pode falhar
                logger.exception("pré-assado falhou ao registrar decoração")
        return entry
    return register


def _prebaked_group(entry: dict, *, anchor: str = "base"):
    """Lê o protótipo pronto; ``None`` quando não há cache utilizável."""
    src = source_of(entry)
    if src is None or not is_bakeable(src):
        return None
    try:
        meta = bake_source(src, name=str(entry.get("nombre") or src.stem),
                           config=config_for_entry(entry, anchor=anchor))
        cached = Path(meta["cache"]) if meta else None
        if cached is None or not cached.is_file():
            return None
        return load_baked(cached)
    except Exception:  # noqa: BLE001 - assar é otimização, não requisito
        logger.exception("falha ao usar o pré-assado de %r", src)
        return None


def load_component_fast(entry: dict, *, anchor: str = "base",
                        thumbnail_size: int | None = None):
    """Inserção first-party: o protótipo assado, já centrado e dimensionado.

    Devolve ``component_loader.Loaded``, ou ``None`` quando a ficha não é uma
    decoração assada (marcenaria continua pelo caminho normal do host).
    """
    if not isinstance(entry, dict):
        return None
    group = _prebaked_group(entry, anchor=anchor or "base")
    if group is None:
        return None
    from core import user_library
    from views import component_loader

    src = source_of(entry)
    group.name = str(entry.get("nombre") or src.stem)
    if thumbnail_size:
        component_loader.save_thumbnail(
            group, user_library.thumbnail_path(entry), thumbnail_size)
    return component_loader.Loaded(group, src)


def load_group_fast(path, *, matrix=None, name: str | None = None):
    """Leitura direta first-party: o ``.igz`` assado no lugar da origem.

    ``None`` quando ``path`` não é decoração ou não há cache utilizável.
    """
    src = Path(str(path)).expanduser()
    if not is_bakeable(src):
        return None
    try:
        config = _norm_config(matrix=matrix, fitted=False)
        meta = bake_source(src, name=str(name or src.stem), config=config)
    except Exception:  # noqa: BLE001 - assar é otimização
        logger.exception("falha ao assar %r na leitura", src)
        return None
    if not meta:
        return None
    cached = Path(meta["cache"])
    if not cached.is_file():
        return None
    group = load_baked(cached)
    if group is not None:
        group.name = str(name or src.stem)
    return group


def _make_load_component_wrapper(original):
    """Compatibilidade: delega na chamada first-party."""
    def load_component(entry, *args, **kwargs):
        loaded = load_component_fast(
            entry, anchor=kwargs.get("anchor", "base") or "base",
            thumbnail_size=kwargs.get("thumbnail_size"))
        return loaded if loaded is not None else original(entry, *args, **kwargs)
    return load_component


def _make_load_group_wrapper(original):
    """Compatibilidade: delega na chamada first-party."""
    def load_group(path, *args, **kwargs):
        group = load_group_fast(
            path, matrix=kwargs.get("matrix"), name=kwargs.get("name"))
        return group if group is not None else original(path, *args, **kwargs)
    return load_group


def install() -> bool:
    """Instala o assado no cadastro e a leitura rápida na inserção.

    ``register`` paga o custo ao cadastrar; ``load_component`` aproveita o
    cache em cada inserção; ``load_group`` cobre chamadores diretos. Num host
    sem esses símbolos, nada é instalado e o fluxo original continua intacto.
    """
    try:
        from core import user_library
        from views import component_loader
    except Exception:  # noqa: BLE001 - fora do host
        return False
    host.install_hook(HOOK_NAME, user_library, "register",
                      _make_register_wrapper)
    host.install_hook(HOOK_COMPONENT_NAME, component_loader, "load_component",
                      _make_load_component_wrapper)
    host.install_hook(HOOK_LOAD_NAME, component_loader, "load_group",
                      _make_load_group_wrapper)
    return True


__all__ = [
    "BAKE_SUFFIXES", "HOOK_COMPONENT_NAME", "HOOK_LOAD_NAME", "HOOK_NAME",
    "bake_root", "bake_source", "bake_stats", "cache_key", "config_for_entry",
    "ensure_for_entry", "face_count", "install", "is_bakeable", "load_baked",
    "load_for_entry", "matrix_for_entry", "source_of", "vertex_count",
]
