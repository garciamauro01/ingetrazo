# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez and IngeTrazo contributors.
"""The user's own component library, browsable and editable.

A file the user downloaded — from 3D Warehouse, a manufacturer, anywhere —
is copied here and indexed, not published. The dialog is the manager: import
one file with its ficha (type, brand, model, licence…), copy a whole folder
into the library, edit what was recorded, remove it, and insert it into the
drawing.

Previews are generated from the geometry by :mod:`views.component_thumbs`,
one at a time and only for rows on screen. A folder of five hundred models
therefore opens instantly; the pictures arrive as they are scrolled to.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core import user_library
from core.i18n import tr
from views import component_loader, library_grid
from views.filedialogs import file_dialogs
from views.length_field import LengthSpinBox
from views.user_library_transfer import export_library, import_library

ICON = 96

CATEGORIES = (
    "Cozinha", "Sala", "Quarto", "Banheiro", "Iluminação", "Exterior",
    "Escritório", "Diversos",
)
UNITS = (("m", "Metros"), ("cm", "Centímetros"), ("mm", "Milímetros"),
         ("in", "Polegadas"), ("ft", "Pés"))


def _model_filter() -> str:
    return tr("3D models ({p})", p=" ".join("*" + s
                                             for s in user_library.MODEL_SUFFIXES))


class ComponentDialog(QDialog):
    """The ficha of one component: import it, or edit what was recorded."""

    def __init__(self, parent=None, *, path=None, entry=None) -> None:
        super().__init__(parent)
        self.entry = None
        self._edit = entry is not None
        self._group = None
        # Identity and placement are kept apart from the widgets: an edit
        # never changes where the file is, only what is said about it.
        self._editing_id = str((entry or {}).get("id") or "")
        self._editing_matrix = (entry or {}).get("matrix")
        self._editing_escala = float((entry or {}).get("escala") or 1.0)
        self._orientation_dirty = False
        self._loading = False
        self._source = (Path(path).expanduser() if path else
                        (user_library.resolve(entry) if entry else None))
        self.setWindowTitle(tr("Edit component") if self._edit
                            else tr("Import component"))
        self.resize(760, 520)

        outer = QVBoxLayout(self)
        body = QHBoxLayout()
        outer.addLayout(body, 1)

        form = QFormLayout()
        body.addLayout(form, 1)

        self._path_edit = QLineEdit(str(self._source or ""))
        self._path_edit.setReadOnly(True)
        file_row = QHBoxLayout()
        file_row.addWidget(self._path_edit, 1)
        self._browse = QPushButton(tr("Browse…"))
        self._browse.clicked.connect(self._browse_file)
        self._browse.setEnabled(not self._edit)
        file_row.addWidget(self._browse)
        file_widget = QWidget()
        file_widget.setLayout(file_row)
        form.addRow(tr("File:"), file_widget)

        self._name = QLineEdit()
        form.addRow(tr("Name:"), self._name)

        self._category = QComboBox()
        self._category.setEditable(True)
        self._category.addItem("")
        self._category.addItems([tr(c) for c in CATEGORIES])
        form.addRow(tr("Category:"), self._category)

        self._tipo = QLineEdit()
        self._tipo.setPlaceholderText(tr("fridge, stove, sofa…"))
        form.addRow(tr("Type:"), self._tipo)
        self._marca = QLineEdit()
        self._marca.setPlaceholderText(tr("Brastemp, Electrolux…"))
        form.addRow(tr("Brand:"), self._marca)
        self._modelo = QLineEdit()
        form.addRow(tr("Model:"), self._modelo)

        self._tags = QLineEdit()
        self._tags.setPlaceholderText(tr("inox, frost-free, french-door"))
        form.addRow(tr("Tags:"), self._tags)

        self._fuente = QLineEdit()
        self._fuente.setPlaceholderText(tr("3D Warehouse, manufacturer site…"))
        form.addRow(tr("Source:"), self._fuente)
        self._licencia = QLineEdit()
        self._licencia.setPlaceholderText(tr("CC0, CC BY, permission…"))
        form.addRow(tr("Licence:"), self._licencia)
        self._autor = QLineEdit()
        form.addRow(tr("Author:"), self._autor)
        self._notas = QLineEdit()
        form.addRow(tr("Notes:"), self._notas)

        dims = QHBoxLayout()
        self._width = LengthSpinBox(minimum=0.0, maximum=1000.0)
        self._depth = LengthSpinBox(minimum=0.0, maximum=1000.0)
        self._height = LengthSpinBox(minimum=0.0, maximum=1000.0)
        for label, spin in ((tr("W"), self._width), (tr("D"), self._depth),
                            (tr("H"), self._height)):
            dims.addWidget(QLabel(label))
            dims.addWidget(spin, 1)
        self._measure_btn = QPushButton(tr("Measure"))
        self._measure_btn.clicked.connect(self._measure)
        dims.addWidget(self._measure_btn)
        dims_widget = QWidget()
        dims_widget.setLayout(dims)
        form.addRow(tr("Size (W × D × H):"), dims_widget)

        self._unit = QComboBox()
        for key, label in UNITS:
            self._unit.addItem(f"{key}|{tr(label)}", key)
        form.addRow(tr("File unit:"), self._unit)
        self._unit.currentIndexChanged.connect(self._source_changed)

        self._vertical = QComboBox()
        self._vertical.addItem(tr("Z up (IngeTrazo, SketchUp)"), False)
        self._vertical.addItem(tr("Y up (Blender, 3D Warehouse)"), True)
        form.addRow(tr("Vertical axis:"), self._vertical)
        self._vertical.currentIndexChanged.connect(self._source_changed)

        side = QVBoxLayout()
        body.addLayout(side)
        self._preview = QLabel()
        self._preview.setFixedSize(180, 180)
        self._preview.setAlignment(Qt.AlignCenter)
        self._preview.setStyleSheet(
            "QLabel { border: 1px solid palette(midlight);"
            " border-radius: 6px; background: palette(base); }")
        side.addWidget(self._preview)
        self._btn_render_mats = QPushButton(tr("🎨 Acabamentos de Render…"))
        self._btn_render_mats.setToolTip(tr("Definir presets procedurais de render por material/cor"))
        self._btn_render_mats.clicked.connect(self._edit_render_materials)
        side.addWidget(self._btn_render_mats)
        self._render_materials: dict[str, str] = {}
        self._status = QLabel("")
        self._status.setWordWrap(True)
        side.addWidget(self._status)
        side.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok
                                   | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        if entry:
            self._fill(entry)
        else:
            self._apply_unit_default()
            if self._source is not None:
                self._name.setText(self._source.stem)
                QTimer.singleShot(0, self._measure)

    # ---- form ---------------------------------------------------------
    def _fill(self, entry: dict) -> None:
        self._loading = True
        self._name.setText(entry.get("nombre", ""))
        self._category.setCurrentText(entry.get("categoria", ""))
        self._tipo.setText(entry.get("tipo", ""))
        self._marca.setText(entry.get("marca", ""))
        self._modelo.setText(entry.get("modelo", ""))
        self._tags.setText(", ".join(entry.get("tags") or []))
        self._fuente.setText(entry.get("fuente", ""))
        self._licencia.setText(entry.get("licencia", ""))
        self._render_materials = dict(entry.get("render_materials") or {})
        self._update_render_mats_button()
        self._autor.setText(entry.get("autor", ""))
        self._notas.setText(entry.get("notas", ""))
        unit = entry.get("unidad") or "m"
        index = self._unit.findData(unit)
        self._unit.setCurrentIndex(index if index >= 0 else 0)
        self._vertical.setCurrentIndex(
            1 if entry.get("y_up") else 0)
        # Unit and vertical stay editable: a model imported with the wrong
        # answer must be fixable without removing and re-importing it.
        cm = entry.get("cm") or ()
        if len(cm) == 3:
            self._width.setValue(float(cm[0]) / 100.0)
            self._depth.setValue(float(cm[1]) / 100.0)
            self._height.setValue(float(cm[2]) / 100.0)
        self._loading = False
        self._load_preview(entry)

    def _apply_unit_default(self) -> None:
        if self._source is None:
            return
        suffix = self._source.suffix.lower()
        unit = "mm" if suffix == ".stl" else "m"
        if suffix == ".obj":
            try:
                from formats.obj import suggest_unit
                unit = suggest_unit(self._source)
            except Exception:  # noqa: BLE001 - a suggestion only
                pass
        index = self._unit.findData(unit)
        if index >= 0:
            self._unit.setCurrentIndex(index)

    def _browse_file(self) -> None:
        path, _ = file_dialogs.getOpenFileName(
            self, tr("Import component"), "", _model_filter())
        if not path:
            return
        self._source = Path(path)
        self._path_edit.setText(path)
        if not self._name.text().strip():
            self._name.setText(self._source.stem)
        self._apply_unit_default()
        self._measure()

    def _source_changed(self, *_args) -> None:
        if self._loading:
            return
        self._orientation_dirty = True
        self._measure()

    def _matrix(self) -> tuple:
        return component_loader.matrix_for(
            self._unit.currentData() or "m",
            bool(self._vertical.currentData()))

    def _edited_matrix(self):
        """The matrix to record when saving. An edit keeps the matrix the
        entry was imported with unless the user touched unit or vertical;
        then it is rebuilt (with the entry's scale, if it had one)."""
        if not self._edit:
            return self._matrix()
        if not self._orientation_dirty:
            return self._editing_matrix
        factor = self._editing_escala or 1.0
        return tuple(v * factor for v in self._matrix())

    def _measure(self) -> None:
        if self._source is None or not self._source.is_file():
            self._status.setText(tr("Choose a model file first."))
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            group = component_loader.load_group(
                self._source,
                matrix=self._edited_matrix() or self._matrix(),
                name=self._name.text().strip() or self._source.stem)
            group = component_loader.fit(group, anchor="base")
        except component_loader.ComponentLoadError as exc:
            self._status.setText(str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        self._group = group
        size = component_loader.size_cm(group)
        for spin, value in zip((self._width, self._depth, self._height),
                               size):
            spin.setValue(value / 100.0)
        self._preview.setPixmap(
            component_loader.thumbnail_pixmap(group, 180))
        self._status.setText(tr("Measured from the file."))

    def _load_preview(self, entry: dict) -> None:
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            loaded = component_loader.load_component(entry)
        finally:
            QApplication.restoreOverrideCursor()
        if loaded is None:
            self._status.setText(tr(
                "The model file is missing. The entry keeps its metadata."))
            return
        self._group = loaded.group
        # Se já existe miniatura gerada em disco para o item, usa diretamente a miniatura oficial
        thumb_path = user_library.thumbnail(entry)
        if thumb_path and thumb_path.is_file():
            pix = QPixmap(str(thumb_path))
            if not pix.isNull():
                self._preview.setPixmap(pix.scaled(
                    180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                return
        self._preview.setPixmap(
            component_loader.thumbnail_pixmap(loaded.group, 180))

    def _update_render_mats_button(self) -> None:
        configured = sum(
            1 for v in self._render_materials.values()
            if (isinstance(v, dict) and bool(v)) or (isinstance(v, str) and v and v != "original")
        )
        if configured == 1:
            self._btn_render_mats.setText(tr("🎨 Materiais PBR (1 configurado)…"))
        elif configured > 1:
            self._btn_render_mats.setText(
                tr("🎨 Materiais PBR ({n} configurados)…", n=configured))
        else:
            self._btn_render_mats.setText(tr("🎨 Materiais PBR (Render)…"))

    def _edit_render_materials(self) -> None:
        if self._group is None and self._source is not None and self._source.is_file():
            self._measure()
        if self._group is None:
            QMessageBox.information(
                self, tr("Materiais PBR (Render)"),
                tr("Escolha primeiro um arquivo de modelo válido."))
            return
        from trazomob.ui.material_editor_dialog import MaterialEditorDialog

        current = {
            k: v for k, v in (self._render_materials or {}).items()
            if isinstance(v, dict)
        }
        dlg = MaterialEditorDialog(
            scene=None,
            current_overrides=current,
            viewport=None,
            parent=self,
            group=self._group,
        )
        if dlg.exec():
            self._render_materials = dlg.get_overrides()
            self._update_render_mats_button()

    def _dimensions_cm(self) -> list | None:
        values = [spin.value() * 100.0
                  for spin in (self._width, self._depth, self._height)]
        return values if all(v > 0.0 for v in values) else None

    def _accept(self) -> None:
        if self._source is None or not self._source.is_file():
            QMessageBox.warning(self, tr("Import component"),
                                tr("Choose a model file first."))
            return
        name = self._name.text().strip() or self._source.stem
        cm = self._dimensions_cm()
        tags = [t.strip() for t in self._tags.text().split(",") if t.strip()]
        common = dict(
            nombre=name,
            categoria=self._category.currentText().strip(),
            tipo=self._tipo.text().strip(),
            marca=self._marca.text().strip(),
            modelo=self._modelo.text().strip(),
            tags=tags,
            fuente=self._fuente.text().strip(),
            licencia=self._licencia.text().strip(),
            autor=self._autor.text().strip(),
            notas=self._notas.text().strip(),
            render_materials=dict(self._render_materials),
        )
        if self._edit:
            updated = user_library.update(
                self._editing_id, matrix=self._edited_matrix(),
                unidad=self._unit.currentData() or "m",
                y_up=bool(self._vertical.currentData()), cm=cm, **common)
            if updated is None:
                QMessageBox.warning(self, tr("Edit component"),
                                    tr("The component is no longer indexed."))
                return
            entry = updated
        else:
            try:
                entry = user_library.register(
                    self._source,
                    matrix=self._matrix(), cm=cm,
                    unidad=self._unit.currentData() or "m",
                    y_up=bool(self._vertical.currentData()), **common)
            except (OSError, ValueError) as exc:
                QMessageBox.critical(self, tr("Import component"), str(exc))
                return
        self.entry = entry
        # The preview is generated from the just-recorded entry, so it
        # reflects the size and the orientation the insertion will use.
        if self._group is not None:
            fitted = component_loader.fit(
                self._group, cm=entry.get("cm"), anchor="base")
            component_loader.save_thumbnail(
                fitted, user_library.thumbnail_path(entry), 128)
        else:
            component_loader.load_component(
                entry, thumbnail_size=128, strict=False)
        self.accept()


class UserLibraryDialog(QDialog):
    """Browse, filter, insert, edit and remove the user's components."""

    def __init__(self, window, *, brand: str | None = None) -> None:
        super().__init__(window)
        self._window = window
        self.setWindowTitle(tr("My components"))
        self.resize(860, 600)
        lay = QVBoxLayout(self)

        top = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText(tr("Search name, brand, model, tag…"))
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._refill)
        top.addWidget(self._search, 1)
        self._category = QComboBox()
        self._category.currentIndexChanged.connect(self._refill)
        top.addWidget(self._category)
        self._tipo = QComboBox()
        self._tipo.currentIndexChanged.connect(self._refill)
        top.addWidget(self._tipo)
        self._marca = QComboBox()
        self._marca.currentIndexChanged.connect(self._refill)
        top.addWidget(self._marca)
        lay.addLayout(top)

        self._list = QListWidget()
        library_grid.configure(self._list, icon=ICON,
                               grid=QSize(ICON + 40, ICON + 54))
        self._list.itemDoubleClicked.connect(lambda _i: self._insert())
        self._list.currentItemChanged.connect(self._show_credit)
        lay.addWidget(self._list, 1)

        self._credit = QLabel("")
        self._credit.setWordWrap(True)
        lay.addWidget(self._credit)

        row = QHBoxLayout()
        self._status = QLabel("")
        row.addWidget(self._status, 1)
        for label, slot in (
                (tr("Import file…"), self.import_file),
                (tr("Add folder…"), self.add_folder),
                (tr("Edit…"), self.edit_selected),
                (tr("Remove"), self.remove_selected),
                (tr("Open folder"), self._open_folder)):
            button = QPushButton(label)
            button.clicked.connect(slot)
            row.addWidget(button)

        transfer = QPushButton(tr("Transfer…"))
        transfer_menu = QMenu(transfer)
        transfer_menu.addAction(tr("Export library…"),
                                lambda: export_library(self, after=self._reload))
        transfer_menu.addAction(tr("Import library…"),
                                lambda: import_library(self, after=self._reload))
        transfer.setMenu(transfer_menu)
        row.addWidget(transfer)

        self._insert_btn = QPushButton(tr("Insert"))
        self._insert_btn.setDefault(True)
        self._insert_btn.clicked.connect(self._insert)
        row.addWidget(self._insert_btn)
        close = QPushButton(tr("Close"))
        close.clicked.connect(self.reject)
        row.addWidget(close)
        lay.addLayout(row)

        self._thumbs_timer = QTimer(self)
        self._thumbs_timer.timeout.connect(self._fill_visible_thumbs)
        self._thumbs_timer.start(150)
        self._pending: list = []
        self._queued: set = set()
        self._failed: set = set()

        self._reload(select_brand=brand)

    # ---- listing ------------------------------------------------------
    def _reload(self, select_brand: str | None = None) -> None:
        self._entries = user_library.index()
        facets = user_library.facets(self._entries)
        current = {box: box.currentData()
                   for box in (self._category, self._tipo, self._marca)}
        for box, key, label in (
                (self._category, "categorias", tr("All categories")),
                (self._tipo, "tipos", tr("All types")),
                (self._marca, "marcas", tr("All brands"))):
            box.blockSignals(True)
            box.clear()
            box.addItem(label, "")
            for value in sorted(facets[key], key=str.casefold):
                box.addItem(f"{value} ({facets[key][value]})", value)
            chosen = select_brand if box is self._marca and select_brand else current[box]
            index = box.findData(chosen or "")
            box.setCurrentIndex(index if index >= 0 else 0)
            box.blockSignals(False)
        self._refill()

    def _refill(self) -> None:
        text = self._search.text().strip().casefold()
        cat = self._category.currentData() or ""
        tipo = self._tipo.currentData() or ""
        marca = self._marca.currentData() or ""
        self._list.clear()
        self._pending.clear()
        self._queued.clear()
        shown = 0
        for entry in self._entries:
            if cat and entry.get("categoria") != cat:
                continue
            if tipo and entry.get("tipo") != tipo:
                continue
            if marca and entry.get("marca") != marca:
                continue
            haystack = " ".join([
                str(entry.get("nombre") or ""),
                str(entry.get("marca") or ""),
                str(entry.get("modelo") or ""),
                str(entry.get("categoria") or ""),
                str(entry.get("tipo") or ""),
                " ".join(str(t) for t in entry.get("tags") or []),
            ]).casefold()
            if text and text not in haystack:
                continue
            label = entry.get("nombre") or entry.get("id", "?")
            if user_library.missing(entry):
                label += " " + tr("(missing)")
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, entry)
            item.setToolTip(self._tooltip(entry))
            self._list.addItem(item)
            shown += 1
        if not self._entries:
            self._status.setText(tr(
                "No components yet. Import a file or add a folder."))
        else:
            self._status.setText(tr("{n} of {total} components",
                                    n=shown, total=len(self._entries)))
        QTimer.singleShot(0, self._fill_visible_thumbs)

    def _tooltip(self, entry: dict) -> str:
        parts = [entry.get("nombre", "")]
        if entry.get("marca"):
            parts.append(entry["marca"])
        if entry.get("modelo"):
            parts.append(entry["modelo"])
        cm = entry.get("cm") or ()
        if len(cm) == 3:
            parts.append("%g × %g × %g cm" % tuple(cm))
        if user_library.missing(entry):
            parts.append(tr("File missing"))
        return " · ".join(str(p) for p in parts if p)

    def _show_credit(self, current, _prev=None) -> None:
        entry = current.data(Qt.UserRole) if current is not None else None
        if not entry:
            self._credit.setText("")
            return
        bits = [entry.get("nombre", "")]
        if entry.get("marca") or entry.get("modelo"):
            bits.append(" ".join(str(entry.get(k) or "")
                                 for k in ("marca", "modelo")).strip())
        if entry.get("licencia") or entry.get("autor"):
            bits.append(tr("{licence} · by {author}",
                           licence=entry.get("licencia") or tr("unknown licence"),
                           author=entry.get("autor") or tr("unknown author")))
        if user_library.missing(entry):
            bits.append(tr("The file is missing from where it was indexed."))
        self._credit.setText("  ·  ".join(b for b in bits if b))

    def _selected_entry(self) -> dict | None:
        item = self._list.currentItem()
        return item.data(Qt.UserRole) if item is not None else None

    # ---- previews -----------------------------------------------------
    _LOOKAHEAD = 20

    def _fill_visible_thumbs(self) -> None:
        rect = self._list.viewport().rect()
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item is None or not rect.intersects(self._list.visualItemRect(item)):
                continue
            if not item.icon().isNull():
                continue
            entry = item.data(Qt.UserRole) or {}
            path = user_library.thumbnail(entry)
            if path is not None:
                pix = QPixmap(str(path))
                if not pix.isNull():
                    item.setIcon(QIcon(pix))
                    continue
            ident = entry.get("id", "")
            if not ident or ident in self._failed or ident in self._queued:
                continue
            if user_library.missing(entry):
                continue
            self._queued.add(ident)
            self._pending.append(entry)
        if self._pending:
            QTimer.singleShot(0, self._make_one_thumb)

    def _make_one_thumb(self) -> None:
        if not self._pending:
            return
        entry = self._pending.pop(0)
        ident = entry.get("id", "")
        self._status.setText(tr("Drawing a preview of {name}…",
                                name=entry.get("nombre", "")))
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            loaded = component_loader.load_component(entry,
                                                     thumbnail_size=128)
        finally:
            QApplication.restoreOverrideCursor()
        if loaded is None:
            self._failed.add(ident)
        else:
            self._reload_item_icon(ident)
        self._queued.discard(ident)
        if self._pending:
            QTimer.singleShot(0, self._make_one_thumb)
        else:
            self._refill_status()

    def _reload_item_icon(self, ident: str) -> None:
        path = user_library.thumbnail(ident)
        if path is None:
            return
        pix = QPixmap(str(path))
        if pix.isNull():
            return
        for i in range(self._list.count()):
            item = self._list.item(i)
            entry = item.data(Qt.UserRole) or {}
            if entry.get("id") == ident:
                item.setIcon(QIcon(pix))
                break

    def _refill_status(self) -> None:
        self._status.setText(tr("{n} of {total} components",
                                n=self._list.count(),
                                total=len(self._entries)))

    # ---- actions ------------------------------------------------------
    def import_file(self, path=None) -> None:
        if path is None:
            path, _ = file_dialogs.getOpenFileName(
                self, tr("Import component"), "", _model_filter())
        if not path:
            return
        dialog = ComponentDialog(self, path=path)
        if dialog.exec() != QDialog.Accepted or dialog.entry is None:
            return
        self._reload()
        self._select(dialog.entry.get("id", ""))

    def add_folder(self) -> None:
        folder = file_dialogs.getExistingDirectory(
            self, tr("Add component folder"))
        if not folder:
            return
        answer = QMessageBox.question(
            self, tr("Add component folder"),
            tr("Include subfolders?"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            added = user_library.add_folder(
                folder, recursive=answer == QMessageBox.Yes)
        finally:
            QApplication.restoreOverrideCursor()
        self._reload()
        QMessageBox.information(
            self, tr("Add component folder"),
            tr("{n} components indexed from {folder}",
               n=len(added), folder=folder))

    def edit_selected(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            return
        dialog = ComponentDialog(self, entry=entry)
        if dialog.exec() != QDialog.Accepted:
            return
        self._reload()
        self._select(entry.get("id", ""))

    def remove_selected(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            return
        message = tr("Remove “{name}” from the library?",
                     name=entry.get("nombre", ""))
        message += "\n\n" + tr(
            "The managed copy inside the library will be deleted. "
            "The original file is not touched.")
        if QMessageBox.question(self, tr("Remove component"), message,
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No) != QMessageBox.Yes:
            return
        user_library.remove(entry.get("id", ""))
        self._reload()

    def _insert(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            return
        if user_library.missing(entry):
            QMessageBox.warning(
                self, tr("Insert component"),
                tr("The model file is missing. Use Edit… to relocate it "
                   "or remove the entry."))
            return
        insert = getattr(self._window, "insert_user_component", None)
        if not callable(insert):
            QMessageBox.warning(self, tr("Insert component"),
                                tr("This build cannot insert user components."))
            return
        insert(entry)
        self.accept()

    def _select(self, ident: str) -> None:
        for i in range(self._list.count()):
            item = self._list.item(i)
            entry = item.data(Qt.UserRole) or {}
            if entry.get("id") == ident:
                self._list.setCurrentItem(item)
                break

    def _open_folder(self) -> None:
        root = user_library.library_root()
        root.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(root)))


def open_import_dialog(parent, path=None):
    """The tray's short path: pick one file, fill the ficha, index it.

    Returns the new entry, or ``None`` when cancelled. Used by the main
    window so the tray does not need to know the dialog's widgets.
    """
    if path is None:
        path, _ = file_dialogs.getOpenFileName(
            parent, tr("Import component"), "", _model_filter())
    if not path:
        return None
    dialog = ComponentDialog(parent, path=path)
    if dialog.exec() != QDialog.Accepted:
        return None
    return dialog.entry
