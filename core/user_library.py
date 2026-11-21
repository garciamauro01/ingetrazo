# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez and IngeTrazo contributors.
"""The user's own component library: a folder of models the user already has,
indexed and managed here.

The app never downloads or publishes anything from this library. The user
brings the file — a 3D Warehouse download, a manufacturer's catalogue, a
model bought from an artist — and this module records where it is, what it
is and how it should be read. That is what keeps the collection the user's
own and the app a manager rather than a redistributor.

Every import is copied. The model and the files it needs (MTL, textures,
.bin) go into ``<library>/models/<id>/``, and the manifest keeps only a path
relative to the library. Moving or deleting the original changes nothing,
and a component in the scene is always a link to a file the library owns.

Older manifests with ``modo: "referencia"`` are still read so an existing
installation keeps working; registering or re-registering a file promotes
such an entry to a managed copy. No new reference entry is ever written.

The manifest is ``library.json`` under the library root, in the same
vocabulary the online catalogue uses (``nombre``, ``categoria``, ``licencia``,
``autor``) plus the facets this feature needs (``tipo``, ``marca``,
``modelo``, ``tags``). ``id`` is ours and safe to use as a path component.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import unicodedata
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from core.paths import user_data_dir

#: Bumped when the layout changes in a way older builds must notice.
VERSION = 1
MANIFEST = "library.json"

#: What the geometry loaders in :mod:`views.component_loader` can read.
MODEL_SUFFIXES = (".obj", ".glb", ".dae", ".stl", ".skp", ".igz")

#: Same shape the online library uses: an id becomes a folder name.
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")

#: Keys ``update`` is allowed to change. ``id``/``modo``/``archivo`` are the
#: entry's identity and are deliberately not here.
_EDITABLE = {
    "nombre", "categoria", "tipo", "marca", "modelo", "tags", "fuente",
    "licencia", "autor", "notas", "cm", "matrix", "miniatura", "origen",
    "escala", "y_up", "unidad",
}


def valid_id(ident) -> bool:
    return (isinstance(ident, str) and bool(_ID_RE.match(ident))
            and ".." not in ident)


def library_root() -> Path:
    """Where the user's components live. ``INGETRAZO_COMPONENTS`` overrides
    it (tests, a library on another drive, a shared folder)."""
    raw = os.environ.get("INGETRAZO_COMPONENTS")
    return (Path(raw).expanduser() if raw
            else user_data_dir() / "components")


def manifest_path() -> Path:
    return library_root() / MANIFEST


def models_dir() -> Path:
    return library_root() / "models"


def thumbs_dir() -> Path:
    return library_root() / "thumbs"


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def _empty() -> dict:
    return {"version": VERSION, "unidad": "m", "componentes": []}


def _read() -> dict:
    p = manifest_path()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _empty()
    if isinstance(data, list):                 # a hand-written early manifest
        data = {"version": VERSION, "componentes": data}
    if not isinstance(data, dict):
        return _empty()
    entries = data.get("componentes")
    if not isinstance(entries, list):
        data["componentes"] = []
    data.setdefault("version", VERSION)
    data.setdefault("unidad", "m")
    return data


def _write(data: dict) -> None:
    p = manifest_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".part")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    tmp.replace(p)                              # never a half-written manifest


def revision() -> int:
    """A cheap token that changes when the manifest does: the ribbon uses it
    to know its «Meus Componentes» tab is out of date without being told."""
    try:
        return manifest_path().stat().st_mtime_ns
    except OSError:
        return 0


def index(refresh: bool = False) -> list[dict]:
    """Every component, id-validated. ``refresh`` is accepted for symmetry
    with :func:`core.library.index`; this library is read from disk each
    time and has no cache to invalidate."""
    del refresh
    entries = _read().get("componentes") or []
    return [e for e in entries
            if isinstance(e, dict) and valid_id(e.get("id"))]


def get(ident: str) -> dict | None:
    for e in index():
        if e.get("id") == ident:
            return e
    return None


# ---------------------------------------------------------------------------
# Identity and paths
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    """A readable id from a name, without accents or punctuation."""
    raw = unicodedata.normalize("NFKD", str(text or ""))
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    raw = re.sub(r"[^A-Za-z0-9]+", "-", raw).strip("-").lower()
    return raw[:80] or "componente"


def _new_id(name: str, origin: str, taken: set) -> str:
    base = slugify(name)
    tag = hashlib.sha1(origin.casefold().encode("utf-8")).hexdigest()[:6]
    candidate = f"{base}-{tag}"[:120]
    if candidate not in taken:
        return candidate
    for n in range(2, 1000):
        candidate = f"{base}-{tag}-{n}"[:127]
        if candidate not in taken:
            return candidate
    return f"{base}-{uuid.uuid4().hex[:8]}"[:127]


def _relative_archive(ident: str, filename: str) -> str:
    return (Path("models") / ident / filename).as_posix()


def resolve(entry) -> Path | None:
    """The model file of ``entry`` (or of an id), or ``None`` when it is
    missing. A managed path never escapes the library folder, whatever the
    manifest says."""
    e = entry if isinstance(entry, dict) else get(entry)
    if not e:
        return None
    arch = str(e.get("archivo") or "").strip()
    if not arch:
        return None
    if e.get("modo") == "referencia":
        p = Path(arch).expanduser()
    else:
        rel = Path(arch)
        if rel.is_absolute():
            return None
        root = library_root().resolve()
        try:
            p = (root / rel).resolve()
            p.relative_to(root)
        except (OSError, ValueError):
            return None
    return p if p.is_file() else None


def missing(entry) -> bool:
    return resolve(entry) is None


def thumbnail_path(entry_or_id) -> Path:
    ident = (entry_or_id if isinstance(entry_or_id, str)
             else (entry_or_id or {}).get("id", ""))
    return thumbs_dir() / f"{ident}.png"


def thumbnail(entry_or_id) -> Path | None:
    """The preview if it exists. Never loads geometry, so a grid can paint
    what it has and ask for the rest."""
    p = thumbnail_path(entry_or_id)
    return p if p.is_file() else None


# ---------------------------------------------------------------------------
# Sidecars: what a model file needs beside it
# ---------------------------------------------------------------------------

def _rel_name(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except (OSError, ValueError):
        return path.name


def _obj_maps(mtl: Path) -> list[Path]:
    """The image files a MTL names (``map_Kd`` and friends)."""
    found: list[Path] = []
    try:
        text = mtl.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return found
    for line in text.splitlines():
        parts = line.split()
        if not parts or not parts[0].lower().startswith("map_"):
            continue
        # map_* lines may carry options (-s, -o, -t) before the filename;
        # take the first token that names a real file, and the whole tail
        # too, because a name can contain spaces.
        rest = line.split(None, 1)[1].strip() if len(parts) > 1 else ""
        candidates = []
        if rest:
            candidates.append(rest.strip('"'))
            candidates.extend(t.strip('"') for t in rest.split())
        for name in candidates:
            p = (mtl.parent / name).expanduser()
            if p.is_file() and p not in found:
                found.append(p)
    return found


def sidecars(path: Path) -> list[Path]:
    """Files that must travel with ``path`` for it to read correctly.

    OBJ: its MTL and the images the MTL names. DAE: the images its
    ``<init_from>`` elements name. GLB/IGZ/SKP: self-contained. STL: none.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    out: list[Path] = []

    def add(p: Path) -> None:
        if p.is_file() and p.resolve() != path.resolve() and p not in out:
            out.append(p)

    if suffix == ".obj":
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return out
        for line in text.splitlines():
            parts = line.split()
            if not parts or parts[0].lower() != "mtllib":
                continue
            names = [line.split(None, 1)[1].strip().strip('"')] if len(parts) > 1 else []
            names.extend(t.strip('"') for t in parts[1:])
            for name in names:
                mtl = (path.parent / name).expanduser()
                if mtl.is_file():
                    add(mtl)
                    for image in _obj_maps(mtl):
                        add(image)
    elif suffix == ".dae":
        import re as _re
        from urllib.parse import unquote, urlparse
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return out
        for raw in _re.findall(r"<init_from>\s*(.*?)\s*</init_from>",
                               text, _re.DOTALL):
            name = raw.strip()
            if not name:
                continue
            if name.startswith("file:"):
                # file:///C:/arte/tex.png — the form most exporters write.
                name = unquote(urlparse(name).path)
                if len(name) > 2 and name[0] == "/" and name[2] == ":":
                    name = name[1:]
            elif "://" in name:
                continue
            candidate = Path(name).expanduser()
            if not candidate.is_absolute():
                candidate = (path.parent / unquote(name)).expanduser()
            add(candidate)
    return out


# ---------------------------------------------------------------------------
# Register / update / remove
# ---------------------------------------------------------------------------

def _entry(ident: str, src: Path, *, nombre, categoria, tipo, marca, modelo,
           tags, fuente, licencia, autor, notas, cm, matrix,
           escala, y_up, unidad) -> dict:
    return {
        "id": ident,
        "nombre": str(nombre or src.stem),
        "categoria": str(categoria or ""),
        "tipo": str(tipo or ""),
        "marca": str(marca or ""),
        "modelo": str(modelo or ""),
        "tags": [str(t) for t in (tags or []) if str(t).strip()],
        "modo": "gerenciado",
        "archivo": _relative_archive(ident, src.name),
        "origen": str(src),
        "cm": list(cm) if cm else None,
        "matrix": list(matrix) if matrix else None,
        "escala": float(escala) if escala is not None else 1.0,
        "y_up": bool(y_up),
        "unidad": str(unidad or "m"),
        "miniatura": f"thumbs/{ident}.png",
        "fuente": str(fuente or ""),
        "licencia": str(licencia or ""),
        "autor": str(autor or ""),
        "notas": str(notas or ""),
    }


def _bake_decoration(entry: dict) -> None:
    """Pré-assa uma decoração ao cadastrar (TrazoMob first-party).

    O custo da conversão estrangeira é pago uma vez, aqui — nunca na primeira
    inserção. Falha no assado nunca pode impedir o cadastro da ficha.
    """
    import logging

    try:
        from trazomob.integrations import decor_bake

        decor_bake.ensure_for_entry(entry)
    except Exception:  # noqa: BLE001 - otimização, não requisito
        logging.getLogger(__name__).exception(
            "pré-assado falhou ao registrar decoração")


def register(source, *, nombre: str | None = None, categoria: str = "",
             tipo: str = "", marca: str = "", modelo: str = "",
             tags=None, fuente: str = "", licencia: str = "",
             autor: str = "", notas: str = "", cm=None, matrix=None,
             escala: float = 1.0, y_up: bool = False,
             unidad: str = "m") -> dict:
    """Copy one model file into the library and return its entry.

    The file and its sidecars always go to ``models/<id>/``; there is no
    reference-only mode. The same file imported twice (same resolved origin)
    is updated rather than duplicated. A legacy reference entry found on
    re-import is promoted to a managed copy.
    """
    src = Path(source).expanduser()
    if not src.is_file():
        raise FileNotFoundError(str(src))
    if src.suffix.lower() not in MODEL_SUFFIXES:
        raise ValueError(f"unsupported model format: {src.suffix}")
    src = src.resolve()
    data = _read()
    entries = data.setdefault("componentes", [])
    origin = str(src)

    for e in entries:
        try:
            same = bool(e.get("origen")) and \
                Path(str(e["origen"])).expanduser().resolve() == src
        except (OSError, ValueError):
            same = False
        if same:
            # A legacy entry that only referenced the file is promoted to a
            # managed copy on re-import. Every new import is already managed.
            if e.get("modo") != "gerenciado":
                ident = str(e.get("id"))
                dest_dir = models_dir() / ident
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest_dir / src.name)
                for dep in sidecars(src):
                    target = dest_dir / _rel_name(dep, src.parent)
                    try:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(dep, target)
                    except OSError:
                        pass
                e["modo"] = "gerenciado"
                e["archivo"] = _relative_archive(ident, src.name)
            changes = {
                "nombre": nombre, "categoria": categoria, "tipo": tipo,
                "marca": marca, "modelo": modelo, "tags": tags,
                "fuente": fuente, "licencia": licencia, "autor": autor,
                "notas": notas, "cm": cm, "matrix": matrix, "unidad": unidad,
            }
            for key, value in changes.items():
                if value not in (None, "", []):
                    e[key] = ([str(t) for t in value] if key == "tags"
                              else (list(value) if key in ("cm", "matrix")
                                    else value))
            e["escala"] = float(escala)
            e["y_up"] = bool(y_up)
            _write(data)
            _bake_decoration(e)
            return e

    ident = _new_id(nombre or src.stem, origin,
                    {e.get("id") for e in entries})
    dest_dir = models_dir() / ident
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest_dir / src.name)
    for dep in sidecars(src):
        target = dest_dir / _rel_name(dep, src.parent)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dep, target)
        except OSError:
            pass

    entry = _entry(ident, src, nombre=nombre, categoria=categoria, tipo=tipo,
                   marca=marca, modelo=modelo, tags=tags, fuente=fuente,
                   licencia=licencia, autor=autor, notas=notas, cm=cm,
                   matrix=matrix, escala=escala, y_up=y_up, unidad=unidad)
    entries.append(entry)
    _write(data)
    _bake_decoration(entry)
    return entry


def update(ident: str, **fields) -> dict | None:
    """Edit an entry's metadata (never its identity or where the file is)."""
    data = _read()
    for e in data.get("componentes") or []:
        if e.get("id") != ident:
            continue
        for key, value in fields.items():
            if key not in _EDITABLE:
                continue
            if key == "tags":
                e[key] = [str(t) for t in (value or []) if str(t).strip()]
            elif key in ("cm", "matrix"):
                e[key] = list(value) if value else None
            elif key == "y_up":
                e[key] = bool(value)
            elif key == "escala":
                e[key] = float(value)
            else:
                e[key] = "" if value is None else value
        _write(data)
        return e
    return None


def remove(ident: str, delete_files: bool = True) -> bool:
    """Drop an entry. The copy inside the library goes with it; the user's
    original file is never touched."""
    data = _read()
    entries = data.get("componentes") or []
    keep, gone = [], None
    for e in entries:
        if e.get("id") == ident:
            gone = e
        else:
            keep.append(e)
    if gone is None:
        return False
    data["componentes"] = keep
    if delete_files and gone.get("modo") == "gerenciado" and valid_id(ident):
        root = models_dir().resolve()
        target = (models_dir() / ident).resolve()
        try:
            target.relative_to(root)
            shutil.rmtree(target, ignore_errors=True)
        except (OSError, ValueError):
            pass
    try:
        thumbnail_path(ident).unlink()
    except OSError:
        pass
    _write(data)
    return True


# ---------------------------------------------------------------------------
# Bulk indexing
# ---------------------------------------------------------------------------

def add_folder(folder, *, recursive: bool = True,
               tags=None, **fields) -> list[dict]:
    """Copy every model under ``folder`` into the library. The relative
    folders become tags, so ``Geladeiras/Brastemp/BRM54.obj`` arrives tagged
    with both."""
    root = Path(folder).expanduser()
    if not root.is_dir():
        return []
    pattern = "**/*" if recursive else "*"
    added = []
    fields.pop("nombre", None)
    for path in sorted(root.glob(pattern)):
        if not path.is_file() or path.suffix.lower() not in MODEL_SUFFIXES:
            continue
        try:
            rel = path.parent.relative_to(root)
            folder_tags = [p for p in rel.parts if p not in ("", ".")]
        except ValueError:
            folder_tags = []
        added.append(register(
            path, nombre=path.stem,
            tags=list(tags or []) + folder_tags, **fields))
    return added


# ---------------------------------------------------------------------------
# Facets for the browser
# ---------------------------------------------------------------------------

def facets(entries=None) -> dict:
    """Counts by ``tipo``, ``marca``, ``categoria`` and ``tag`` — what the
    dialog's filters and the ribbon's brand buttons are built from."""
    entries = index() if entries is None else entries
    out = {"tipos": {}, "marcas": {}, "categorias": {}, "tags": {}}
    for e in entries:
        for key, field in (("tipos", "tipo"), ("marcas", "marca"),
                           ("categorias", "categoria")):
            value = str(e.get(field) or "").strip()
            if value:
                out[key][value] = out[key].get(value, 0) + 1
        for tag in e.get("tags") or []:
            tag = str(tag).strip()
            if tag:
                out["tags"][tag] = out["tags"].get(tag, 0) + 1
    return out


# ---------------------------------------------------------------------------
# Portable bundles: export / import the whole user library
# ---------------------------------------------------------------------------

BUNDLE_MANIFEST = "bundle.json"
BUNDLE_FORMAT = "ingetrazo-user-library"
BUNDLE_VERSION = 1


def _portable_entry(entry: dict) -> dict:
    """A copy of ``entry`` without the absolute path of the original file.

    ``origen`` is provenance, not something the app resolves, but it would
    leak the donor's disk layout into another machine. Keep only the file
    name; ``archivo`` stays relative to the library root.
    """
    out = dict(entry)
    origin = str(out.get("origen") or "").strip()
    if origin:
        out["origen"] = re.split(r"[\\/]", origin)[-1]
    return out


def export_bundle(dest, *, entries=None) -> dict:
    """Write the whole library to ``dest`` as a self-contained ``.zip``.

    Only managed entries whose model file still exists are exported; a legacy
    reference entry or a missing file cannot travel and is skipped. No
    absolute path is written into the bundle.
    """
    target = Path(dest).expanduser()
    if target.suffix.lower() != ".zip":
        target = target.with_suffix(".zip")
    target.parent.mkdir(parents=True, exist_ok=True)

    entries = index() if entries is None else entries
    root = library_root().resolve()
    included: list[dict] = []
    members: set[str] = set()

    for entry in entries:
        ident = entry.get("id")
        if not valid_id(ident) or entry.get("modo") == "referencia":
            continue
        model = resolve(entry)
        if model is None:
            continue
        try:
            model_rel = model.resolve().relative_to(root)
        except ValueError:
            continue
        members.add(model_rel.as_posix())
        included.append(_portable_entry(entry))

        model_folder = models_dir() / ident
        if model_folder.is_dir():
            for path in model_folder.rglob("*"):
                if path.is_file():
                    members.add(path.relative_to(library_root()).as_posix())
        thumb = thumbnail(ident)
        if thumb is not None:
            members.add(thumb.relative_to(library_root()).as_posix())

    data = _read()
    bundle = {
        "format": BUNDLE_FORMAT,
        "version": BUNDLE_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "library_version": data.get("version", VERSION),
        "unidad": data.get("unidad", "m"),
        "entries": len(included),
        "files": len(members),
    }

    tmp = target.with_name(target.name + ".part")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(BUNDLE_MANIFEST,
                    json.dumps(bundle, ensure_ascii=False, indent=2) + "\n")
        zf.writestr(MANIFEST,
                    json.dumps({"version": data.get("version", VERSION),
                                "unidad": data.get("unidad", "m"),
                                "componentes": included},
                               ensure_ascii=False, indent=2) + "\n")
        for name in sorted(members):
            zf.write(library_root() / name, name)
    tmp.replace(target)
    return {"path": target, "entries": len(included),
            "files": len(members), "skipped": len(entries) - len(included)}


def _valid_member(name: str) -> PurePosixPath:
    """Reject anything that could write outside the library on import."""
    path = PurePosixPath(name)
    if (not name or name.endswith("/") or path.is_absolute()
            or ".." in path.parts or path.parts[0] not in ("models", "thumbs")):
        raise ValueError(f"arquivo inválido no pacote: {name!r}")
    if path.parts[0] == "models":
        if len(path.parts) < 3 or not valid_id(path.parts[1]):
            raise ValueError(f"modelo inválido no pacote: {name!r}")
    elif len(path.parts) != 2:
        raise ValueError(f"miniatura inválida no pacote: {name!r}")
    return path


def _read_bundle(source, zf: zipfile.ZipFile) -> tuple[dict, dict, list[str]]:
    names = zf.namelist()
    if BUNDLE_MANIFEST not in names or MANIFEST not in names:
        raise ValueError("não é um pacote da biblioteca do IngeTrazo")
    bundle = json.loads(zf.read(BUNDLE_MANIFEST).decode("utf-8"))
    if (not isinstance(bundle, dict)
            or bundle.get("format") != BUNDLE_FORMAT
            or bundle.get("version") != BUNDLE_VERSION):
        raise ValueError("formato de pacote não reconhecido")
    data = json.loads(zf.read(MANIFEST).decode("utf-8"))
    if not isinstance(data, dict) or not isinstance(
            data.get("componentes"), list):
        raise ValueError("manifesto do pacote inválido")

    entries: dict[str, dict] = {}
    for entry in data["componentes"]:
        if not isinstance(entry, dict):
            raise ValueError("entrada inválida no pacote")
        ident = entry.get("id")
        if not valid_id(ident) or ident in entries:
            raise ValueError(f"id inválido ou repetido no pacote: {ident!r}")
        if entry.get("modo") == "referencia":
            raise ValueError("o pacote contém uma referência, não uma cópia")
        archivo = str(entry.get("archivo") or "")
        rel = PurePosixPath(archivo)
        if (not archivo or rel.is_absolute() or ".." in rel.parts
                or len(rel.parts) < 3 or rel.parts[0] != "models"
                or rel.parts[1] != ident):
            raise ValueError(f"arquivo de modelo inválido: {archivo!r}")
        entries[ident] = _portable_entry(entry)

    members: list[str] = []
    for name in names:
        if name in (BUNDLE_MANIFEST, MANIFEST):
            continue
        _valid_member(name)
        members.append(name)
    for entry in entries.values():
        if entry["archivo"] not in members:
            raise ValueError(
                f"falta o arquivo {entry['archivo']!r} no pacote")
    return bundle, entries, members


def _copy_member(zf: zipfile.ZipFile, name: str, root: Path) -> Path:
    target = root / Path(name)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zf.open(name) as source, target.open("wb") as dest:
        shutil.copyfileobj(source, dest)
    return target


def import_bundle(source, *, mode: str = "merge") -> dict:
    """Import a bundle made by :func:`export_bundle`.

    ``mode='merge'`` keeps the current library and adds only ids that do not
    exist yet. ``mode='replace'`` builds the new library in a staging folder
    and swaps it in only after every file has been copied; the previous
    library is kept as a backup until the swap succeeds.
    """
    if mode not in ("merge", "replace"):
        raise ValueError("mode deve ser 'merge' ou 'replace'")
    src = Path(source).expanduser()
    if not src.is_file():
        raise FileNotFoundError(f"pacote não encontrado: {src}")
    with zipfile.ZipFile(src) as zf:
        bundle, incoming, members = _read_bundle(src, zf)
        if mode == "merge":
            return _merge_bundle(zf, incoming, members)
        return _replace_bundle(zf, bundle, incoming, members)


def _merge_bundle(zf: zipfile.ZipFile, incoming: dict,
                  members: list[str]) -> dict:
    root = library_root()
    existing = {str(e.get("id")) for e in index()}
    added: list[dict] = []
    copied: list[Path] = []
    try:
        for ident, entry in incoming.items():
            if ident in existing:
                continue
            for name in members:
                if (name.startswith(f"models/{ident}/")
                        or name == f"thumbs/{ident}.png"):
                    copied.append(_copy_member(zf, name, root))
            added.append(entry)
        if added:
            data = _read()
            current = {str(e.get("id")) for e in data["componentes"]
                       if isinstance(e, dict)}
            data["componentes"].extend(
                entry for entry in added if entry["id"] not in current)
            _write(data)
    except Exception:
        for path in copied:
            try:
                path.unlink()
            except OSError:
                pass
        raise
    return {"mode": "merge", "added": len(added),
            "skipped": len(incoming) - len(added), "files": len(copied)}


def _replace_bundle(zf: zipfile.ZipFile, bundle: dict, incoming: dict,
                    members: list[str]) -> dict:
    root = library_root()
    root.parent.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    stage = root.parent / f".{root.name}.import-{token}"
    backup = root.parent / f".{root.name}.backup-{token}"
    try:
        stage.mkdir(parents=True)
        for name in members:
            _copy_member(zf, name, stage)
        (stage / MANIFEST).write_text(
            json.dumps({"version": bundle.get("library_version", VERSION),
                        "unidad": bundle.get("unidad", "m"),
                        "componentes": list(incoming.values())},
                       ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        (stage / BUNDLE_MANIFEST).write_text(
            json.dumps(bundle, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        if root.exists():
            root.rename(backup)
        stage.rename(root)
    except Exception:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        if backup.exists() and not root.exists():
            backup.rename(root)
        raise
    if backup.exists():
        shutil.rmtree(backup, ignore_errors=True)
    return {"mode": "replace", "entries": len(incoming),
            "files": len(members)}
