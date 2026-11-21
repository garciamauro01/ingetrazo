# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Itens de biblioteca como VÍNCULO, não como geometria no documento.

Um sofá, uma cadeira, um tapete: modelos de milhares de faces que incham o
``.igz``. Aqui o grupo guarda apenas *de onde* a geometria vem (biblioteca +
id + revisão) e *como* está colocado (``xform``); o host grava essa referência
em ``ext["igz_link"]`` e a malha é reconstruída ao abrir o documento.

O que entra no ``.igz`` (formato escrito por ``formats.igz``)::

    {"link": {"library": "user", "id": "...", "rev": "...", "entry": {...}},
     "xform": [...], "uid": "...", "layer": "...", ...}

O que NÃO entra: as ``edges``/``faces`` do modelo. Uma malha vazia vai junto
só para que um IngeTrazo anterior a este recurso abra o arquivo (sem o
objeto) em vez de falhar.

Três pontos de integração, todos por chamada direta do host first-party:

1. ao inserir um item da biblioteca, marcar o grupo
   (``mark_built_component``, chamado por ``_build_user_component`` e
   ``_build_library_component``);
2. ao abrir, reconstruir os grupos marcados (``rebuild_scene_links``, chamado
   por ``formats.igz.load_into``);
3. ``materialize()`` desfaz o vínculo e devolve a geometria ao documento.

A leitura de vínculos é sempre ativa. Só a criação de vínculos novos depende
do motor TrazoMob, e esse estado é verificado aqui mesmo, no TrazoMob.
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger("trazomob.library_links")

#: Chave em ``Group.ext`` que o host reconhece como referência externa.
LINK_KEY = "igz_link"

#: ``library`` de um vínculo cuja origem é um arquivo importado direto
#: (SKP, DAE, GLB, OBJ): não há ficha de biblioteca, só um caminho.
IMPORT_LIBRARY = "file"

#: Pasta do cache de importações, dentro da raiz da biblioteca do usuário.
CACHE_DIR = "_cache/imports"

#: Protótipos já lidos nesta sessão: (library, id, rev) -> Group.
_DEF_CACHE: dict[tuple, object] = {}

#: Evita recursão quando a definição de um link é, ela mesma, um ``.igz``.
_REBUILDING = [False]

#: A janela do host, para o aviso de vínculo não carregado na barra de status.
_HOST = [None]


# ---------------------------------------------------------------------------
# Marcação
# ---------------------------------------------------------------------------

def link_of(group) -> dict | None:
    """O payload do vínculo do grupo, ou ``None`` se ele não é um link."""
    ext = getattr(group, "ext", None)
    if not isinstance(ext, dict):
        return None
    link = ext.get(LINK_KEY)
    return link if isinstance(link, dict) else None


def is_linked(group) -> bool:
    return link_of(group) is not None


def set_link(group, payload: dict) -> None:
    """Marca ``group`` como vínculo de biblioteca (não grava geometria)."""
    if not isinstance(getattr(group, "ext", None), dict):
        group.ext = {}
    group.ext[LINK_KEY] = payload


def clear_link(group) -> bool:
    """Desfaz o vínculo: o próximo save volta a gravar a geometria."""
    ext = getattr(group, "ext", None)
    if not isinstance(ext, dict) or LINK_KEY not in ext:
        return False
    del ext[LINK_KEY]
    return True


def materialize(group) -> bool:
    """Sinônimo explícito de :func:`clear_link` para o fluxo «editei»."""
    return clear_link(group)


def link_from_entry(entry: dict, *, library: str = "user") -> dict:
    """O payload que vai para ``ext["igz_link"]`` a partir de uma ficha."""
    return {
        "library": str(library),
        "id": str(entry.get("id") or ""),
        "rev": _revision_of(entry),
        "entry": _snapshot(entry),
    }


def _snapshot(entry: dict) -> dict:
    """Cópia JSON-safe dos campos que a reconstrução precisa.

    Guardar a ficha inteira faria o ``.igz`` depender do manifesto atual;
    estas chaves bastam para reler o arquivo que a biblioteca copiou, mesmo
    que os metadados da ficha mudem depois.
    """
    keys = ("id", "nombre", "modo", "archivo", "origen", "cm", "matrix",
            "escala", "y_up", "unidad", "obj", "categoria", "tipo", "marca",
            "modelo")
    out = {}
    for key in keys:
        if key not in entry:
            continue
        value = entry[key]
        if isinstance(value, (str, int, float, bool)) or value is None:
            out[key] = value
        elif isinstance(value, (list, tuple)):
            out[key] = [v for v in value
                        if isinstance(v, (str, int, float, bool))]
        # qualquer outra coisa (Qt, Path…) fica de fora de propósito
    return out


def _revision_of(entry: dict) -> str | None:
    """``mtime_ns:size`` do arquivo: muda quando a biblioteca muda."""
    try:
        from core import user_library
        path = user_library.resolve(entry)
    except Exception:  # noqa: BLE001 - revisão é otimização, não requisito
        path = None
    if path is None:
        raw = entry.get("origen") or entry.get("archivo")
        try:
            from pathlib import Path
            path = Path(str(raw)).expanduser() if raw else None
        except Exception:  # noqa: BLE001
            path = None
    try:
        if path is not None and path.is_file():
            st = path.stat()
            return "%d:%d" % (st.st_mtime_ns, st.st_size)
    except OSError:
        pass
    return None


# ---------------------------------------------------------------------------
# Importação direta: o arquivo trazido para a cena vira vínculo
# ---------------------------------------------------------------------------

def cache_root() -> Path:
    """Onde ficam as geometrias processadas das importações.

    Dentro da raiz da biblioteca do usuário, para que o cache acompanhe a
    biblioteca e seja compartilhado entre documentos: o mesmo sofá importado
    em dez projetos é processado uma vez.
    """
    from core import user_library
    return user_library.library_root() / CACHE_DIR


def link_imported_group(group, source=None, *, digest: str | None = None,
                        index: int = 0) -> dict | None:
    """Marca ``group`` — recém-importado — como vínculo ao arquivo ``source``.

    A geometria processada vai para um ``.igz`` no cache (binário, compacto e
    rápido de reler) e o documento guarda só o link. Devolve o payload, ou
    ``None`` quando não há como identificar a origem — aí o grupo continua
    embutido, como antes.
    """
    if is_linked(group):
        return link_of(group)
    src = Path(source).expanduser() if source else None
    key = digest or (_file_digest(src) if src is not None else None) \
        or _group_digest(group)
    if not key:
        return None
    flat = _flatten_in_place(group)
    if not _has_geometry(flat):
        # Um grupo vazio (o nó raiz de um .skp, por exemplo) não vira vínculo:
        # o cache sairia sem geometria e o documento guardaria uma referência
        # que nunca devolve nada. Fica embutido, como antes.
        logger.debug("importação sem geometria não vira vínculo: %r",
                     getattr(group, "name", ""))
        return None
    cache = _cache_path(key, index)
    try:
        _write_cache(flat, cache)
    except Exception:  # noqa: BLE001 - um cache que falha não perde o grupo
        logger.exception("não foi possível gravar o cache de %r", key)
        return None
    payload = {
        "library": IMPORT_LIBRARY,
        "id": "%s:%d" % (key, int(index)),
        "rev": _file_revision(src) if src is not None else None,
        "entry": {
            "path": str(src) if src is not None else None,
            "cache": str(cache),
            "cache_rel": cache.relative_to(cache_root()).as_posix(),
            "name": getattr(flat, "name", "") or "",
            "index": int(index),
        },
    }
    set_link(flat, payload)
    return payload


def _flatten_in_place(group):
    """Deixa ``group`` com uma malha só, em coordenadas LOCAIS.

    Os filhos (hierarquia de uma importação) são dobrados na malha, mas a
    transformação do próprio grupo **não**: ela continua no vínculo, para o
    save gravar ``xform`` e o objeto voltar exatamente no mesmo lugar.
    """
    children = getattr(group, "children", None)
    if not children:
        return group                    # já é uma malha só, local
    from views.component_loader import flatten
    saved = getattr(group, "xform", None)
    group.xform = None                  # dobra os filhos, não o pai
    try:
        flat = flatten(group)
    finally:
        group.xform = saved
    group.mesh = flat.mesh
    group.children = []
    return group


def _cache_path(key: str, index: int) -> Path:
    key = str(key)
    return cache_root() / key[:2] / ("%s-%d.igz" % (key, int(index)))


def _write_cache(group, path: Path) -> None:
    """Grava a geometria local de ``group`` num ``.igz`` binário.

    O ``xform`` sai do arquivo de propósito: ele pertence ao documento (o
    vínculo), não à definição — assim a mesma definição serve a várias
    instâncias em lugares diferentes.
    """
    from core.scene import Scene
    from formats import igz
    path.parent.mkdir(parents=True, exist_ok=True)
    scene = Scene()
    scene.groups.append(group)
    saved = getattr(group, "xform", None)
    group.xform = None
    try:
        igz.save_scene(scene, path, binary=True)
    finally:
        group.xform = saved


def _file_digest(path) -> str | None:
    """sha256 do arquivo: a identidade do que foi importado."""
    if path is None:
        return None
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _group_digest(group) -> str | None:
    """Identidade de um grupo sem arquivo de origem (colagem, simulação)."""
    mesh = getattr(group, "mesh", None)
    faces = len(getattr(mesh, "faces", ()) or ())
    name = getattr(group, "name", "") or ""
    if not faces and not name:
        return None
    return hashlib.sha256(("%s|%d" % (name, faces)).encode("utf-8")).hexdigest()


def _file_revision(path) -> str | None:
    try:
        st = path.stat()
        return "%d:%d" % (st.st_mtime_ns, st.st_size)
    except (OSError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Reconstrução
# ---------------------------------------------------------------------------

def rebuild_group(group) -> bool:
    """Troca a malha vazia do stub pela geometria da biblioteca."""
    return _rebuild(group) in ("rebuilt", "ready")


def _rebuild(group) -> str:
    """Classifica o que aconteceu com o vínculo de ``group``.

    ``ready`` (já tinha geometria), ``rebuilt`` (a geometria voltou),
    ``empty`` (a definição existe mas não tem geometria) ou ``missing``
    (não foi possível ler a definição).
    """
    link = link_of(group)
    if link is None:
        return "missing"
    if _has_geometry(group):
        return "ready"                  # já materializado: nada a fazer
    proto = _definition(link)
    if proto is None:
        return "missing"
    if not _has_geometry(proto):
        # Vínculo para uma definição vazia: não há o que devolver. O stub
        # fica no lugar e o chamador conta como «empty», não como sucesso.
        return "empty"
    group.mesh = proto.mesh
    group.children = list(getattr(proto, "children", ()) or ())
    group.component = True
    if getattr(group, "xform", None) is None:
        from PySide6.QtGui import QMatrix4x4
        group.xform = QMatrix4x4()      # a definição fica no lugar salvo
    return "rebuilt"


def rebuild_scene_links(scene, *, on_missing=None) -> dict:
    """Reconstrói todos os vínculos de ``scene``; devolve as contagens.

    ``on_missing(group, link)`` é chamado para cada vínculo que não devolveu
    geometria — o grupo continua na cena como stub, para o usuário
    relocalizar. ``stats`` separa ``missing`` (arquivo de origem
    inacessível) de ``empty`` (definição sem geometria): um documento que
    abre «vazio» precisa dizer por quê.
    """
    stats = {"rebuilt": 0, "missing": 0, "empty": 0, "linked": 0}
    if _REBUILDING[0]:
        return stats
    _REBUILDING[0] = True
    try:
        for group in _iter_groups(getattr(scene, "groups", ()) or ()):
            if not is_linked(group):
                continue
            stats["linked"] += 1
            outcome = _rebuild(group)
            if outcome in ("rebuilt", "ready"):
                stats["rebuilt"] += 1
                continue
            stats[outcome] += 1
            logger.warning("vínculo de biblioteca %s: %r",
                           "sem geometria" if outcome == "empty"
                           else "não resolvido", link_of(group))
            if on_missing is not None:
                try:
                    on_missing(group, link_of(group))
                except Exception:  # noqa: BLE001
                    logger.exception("on_missing do vínculo falhou")
    finally:
        _REBUILDING[0] = False
    _report(stats)
    return stats


def _report(stats: dict) -> None:
    """Avisa na barra de status que parte dos vínculos não carregou.

    Silêncio aqui era o pior sintoma: o documento abria «rápido e vazio» sem
    uma palavra. O aviso não bloqueia a abertura nem o salvamento.
    """
    missing = int(stats.get("missing") or 0)
    empty = int(stats.get("empty") or 0)
    if not missing and not empty:
        return
    window = _HOST[0]
    if window is None or not hasattr(window, "statusBar"):
        return
    try:
        from ..domain.i18n import tr
        parts = []
        if missing:
            parts.append(tr("{n} sem o arquivo de origem", n=missing))
        if empty:
            parts.append(tr("{n} sem geometria", n=empty))
        message = tr(
            "TrazoMob: {total} vínculo(s) não carregado(s) — {detail}.",
            total=missing + empty, detail="; ".join(parts))
        bar = window.statusBar()
        if bar is not None:
            bar.showMessage(message, 15000)
    except Exception:  # noqa: BLE001 - aviso nunca derruba a abertura
        logger.debug("não foi possível avisar sobre os vínculos", exc_info=True)


def _iter_groups(groups):
    for group in groups:
        yield group
        yield from _iter_groups(getattr(group, "children", ()) or ())


def _has_geometry(group) -> bool:
    mesh = getattr(group, "mesh", None)
    if mesh is not None and getattr(mesh, "faces", None):
        return True
    return any(_has_geometry(c)
               for c in getattr(group, "children", ()) or ())


def _definition(link: dict):
    """A geometria da biblioteca, lida uma vez por ``(library, id, rev)``."""
    key = (link.get("library"), link.get("id"), link.get("rev"))
    if key in _DEF_CACHE:
        return _DEF_CACHE[key]
    entry = link.get("entry") if isinstance(link.get("entry"), dict) else {}
    try:
        if link.get("library") == IMPORT_LIBRARY:
            proto = _load_imported(link)
        elif link.get("library") == "online":
            proto = _load_online(entry)
        else:
            proto = _load_user(entry, str(link.get("id") or ""))
    except Exception:  # noqa: BLE001 - arquivo ruim não derruba a abertura
        logger.exception("falha ao ler o vínculo %r", key)
        proto = None
    if proto is not None:
        _DEF_CACHE[key] = proto
    return proto


def _load_user(entry: dict, ident: str):
    """Lê a ficha do usuário: primeiro a atual, depois a guardada no link."""
    from core import user_library
    from views import component_loader

    candidates = []
    if ident:
        try:
            fresh = user_library.get(ident)
        except Exception:  # noqa: BLE001
            fresh = None
        if fresh:
            candidates.append(fresh)
    if entry:
        candidates.append(entry)
    for candidate in candidates:
        try:
            loaded = component_loader.load_component(candidate, strict=True)
        except Exception:  # noqa: BLE001 - tenta a próxima ficha
            continue
        if loaded is not None:
            return loaded.group
    return None


def _load_online(entry: dict):
    """O mesmo caminho de ``_build_library_component``, sem a UI."""
    from core import library
    from core.group import Group
    from core.scene import Scene
    from formats import obj as obj_format
    from formats.fuse import soften_smooth_edges

    obj = library.model_file(entry)
    if obj is None:
        return None
    temp = Scene()
    obj_format.load_obj(temp, obj,
                        matrix=library.model_matrix(entry, obj))
    mesh = temp.mesh
    if not getattr(mesh, "faces", None) and temp.groups:
        mesh = temp.groups[0].mesh
    if not getattr(mesh, "faces", None):
        return None
    soften_smooth_edges(mesh, cos_threshold=0.55)
    return Group(mesh, name=entry.get("nombre", ""))


def _load_imported(link: dict):
    """A geometria de um arquivo importado: o cache primeiro, a origem depois."""
    entry = link.get("entry") if isinstance(link.get("entry"), dict) else {}
    group = _read_cached(entry)
    if group is not None:
        return group
    source = entry.get("path")
    if not source:
        return None
    src = Path(str(source)).expanduser()
    if not src.is_file():
        return None
    group = _reimport(src, entry)
    if group is None:
        return None
    try:
        _write_cache(group, _cache_from_entry(entry, link))
    except Exception:  # noqa: BLE001 - reler já funcionou; gravar é extra
        logger.exception("não foi possível regravar o cache de %r", source)
    return group


def _read_cached(entry: dict):
    for candidate in _cache_candidates(entry):
        if candidate is None or not candidate.is_file():
            continue
        group = _read_igz_group(candidate)
        if group is not None:
            return group
    return None


def _cache_candidates(entry: dict):
    raw = entry.get("cache")
    if raw:
        yield Path(str(raw)).expanduser()
    rel = entry.get("cache_rel")
    if rel:
        yield cache_root() / str(rel)


def _cache_from_entry(entry: dict, link: dict) -> Path:
    rel = entry.get("cache_rel")
    if rel:
        return cache_root() / str(rel)
    raw = entry.get("cache")
    if raw:
        return Path(str(raw)).expanduser()
    key = str(link.get("id") or "unknown").split(":")[0]
    return _cache_path(key, int(entry.get("index") or 0))


def _read_igz_group(path: Path):
    """O grupo que o cache guarda — ``_REBUILDING`` evita reconstruir de novo."""
    from core.group import Group
    from core.scene import Scene
    from formats import igz

    temp = Scene()
    igz.load_into(temp, path)       # _REBUILDING mantém o gancho fora
    groups = list(getattr(temp, "groups", ()) or ())
    if not groups:
        mesh = getattr(temp, "mesh", None)
        if mesh is not None and getattr(mesh, "faces", None):
            return Group(mesh)
        return None
    group = groups[0]
    if len(groups) > 1:
        group.adopt(groups[1:])
    return group


def _reimport(path: Path, entry: dict):
    """Relê o arquivo de origem quando o cache sumiu."""
    from core.scene import Scene
    from views.component_loader import flatten

    suffix = path.suffix.lower()
    scene = Scene()
    try:
        if suffix == ".igz":
            from formats import igz
            igz.load_into(scene, path)
        elif suffix == ".skp":
            from formats import skp
            skp.load_skp(scene, path)
        elif suffix == ".dae":
            from formats import dae
            dae.load_dae(scene, path)
        elif suffix in (".glb", ".gltf"):
            from formats import glb
            glb.load_glb(scene, path)
        elif suffix == ".obj":
            from formats import obj
            obj.load_obj(scene, path)
        else:
            return None
    except Exception:  # noqa: BLE001 - origem ruim vira «faltando»
        logger.exception("falha ao reler a origem %r", path)
        return None
    return _scene_group(scene, entry, flatten)


def _scene_group(scene, entry: dict, flatten):
    """O grupo que a importação produziu, achado pelo nome e depois pelo
    índice — a mesma ordem em que o cache foi gravado."""
    from core.group import Group

    groups = list(getattr(scene, "groups", ()) or ())
    if not groups:
        mesh = getattr(scene, "mesh", None)
        if mesh is not None and getattr(mesh, "faces", None):
            return Group(mesh, name=entry.get("name") or "")
        return None
    wanted = entry.get("name")
    index = int(entry.get("index") or 0)
    group = None
    if wanted:
        group = next((g for g in groups
                      if (getattr(g, "name", "") or "") == wanted), None)
    if group is None:
        group = groups[index] if index < len(groups) else groups[0]
    rest = [g for g in groups if g is not group]
    if rest:
        group.adopt(rest)
    flat = flatten(group)
    group.mesh = flat.mesh
    group.children = []
    group.xform = None
    return group


# ---------------------------------------------------------------------------
# Pontos de chamada do host (first-party, sem ganchos)
# ---------------------------------------------------------------------------

def set_host_window(window) -> None:
    """Guarda a janela do host para os avisos na barra de status."""
    _HOST[0] = window


def mark_built_component(group, entry: dict, *, library: str = "user"):
    """Marca o grupo devolvido por um construtor da biblioteca do host."""
    if group is None:
        return None
    payload = link_from_entry(entry, library=library)
    set_link(group, payload)
    return payload


def mark_imported_groups(groups, source=None) -> None:
    """Marca os grupos de topo que uma importação direta acrescentou.

    ``groups`` é ``SnapshotImport.added_groups`` — exatamente o que a
    importação pôs na cena. O cache nunca derruba uma importação.
    """
    try:
        src = Path(source).expanduser() if source else None
        digest = _file_digest(src)
        for i, group in enumerate(groups or ()):
            link_imported_group(group, src, digest=digest, index=i)
    except Exception:  # noqa: BLE001 - o cache nunca derruba uma importação
        logger.exception("não foi possível vincular a importação")


__all__ = [
    "LINK_KEY", "IMPORT_LIBRARY", "link_of", "is_linked", "set_link",
    "clear_link", "materialize", "link_from_entry", "link_imported_group",
    "cache_root", "rebuild_group", "rebuild_scene_links", "set_host_window",
    "mark_built_component", "mark_imported_groups",
]
