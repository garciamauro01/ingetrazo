# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Gerenciador da biblioteca de perfis de alumínio (cadastro de seções 2D)."""
from __future__ import annotations

import re
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import library as lib

_HELP = (
    "<b>Como desenhar a seção</b> (medidas em mm, perfil na posição <i>topo</i>):<br>"
    "• <b>u</b> = profundidade: 0 = face da frente da porta, positivo entra no MDF, negativo sai para frente.<br>"
    "• <b>v</b> = altura: 0 = topo da chapa já descontada, positivo sobe, negativo desce sobre a chapa.<br>"
    "Digite os pontos do contorno em ordem (horário ou anti-horário). "
    "Na base e na lateral a seção é espelhada/girada automaticamente e extrudada por toda a porta."
)


def _fmt(x: float) -> str:
    return f"{float(x):g}".replace(".", ",")


def _parse(txt: str) -> float:
    return float(txt.strip().replace(",", "."))


class PerfilLibraryDialog(QDialog):
    """Cadastro, edição e pré-visualização das seções de perfis."""

    def __init__(self, parent=None, select_id: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("Biblioteca de Perfis de Alumínio")
        self.resize(980, 640)
        self._perfis: list[dict[str, Any]] = [lib.copy_profile(p) for p in lib.load_library(force=True)]
        self._cur: int = -1
        self._loading = False
        self.selected_id: str | None = select_id

        root = QHBoxLayout(self)

        # ---- Lista ----
        left = QVBoxLayout()
        left.addWidget(QLabel("<b>Perfis cadastrados</b>"))
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._on_select)
        left.addWidget(self.list, 1)
        row = QHBoxLayout()
        for txt, tip, fn in (
            ("➕", "Novo perfil", self._new),
            ("⧉", "Duplicar perfil", self._dup),
            ("🗑", "Excluir perfil", self._del),
            ("↺", "Restaurar perfis padrão", self._reset),
        ):
            b = QPushButton(txt)
            b.setToolTip(tip)
            b.setFixedWidth(38)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch()
        left.addLayout(row)
        lw = QWidget()
        lw.setLayout(left)
        lw.setFixedWidth(240)
        root.addWidget(lw)

        # ---- Edição ----
        mid = QVBoxLayout()
        form = QFormLayout()
        self.ed_nome = QLineEdit()
        self.ed_codigo = QLineEdit()
        self.sp_desc = QDoubleSpinBox()
        self.sp_desc.setRange(0.0, 200.0)
        self.sp_desc.setDecimals(1)
        self.sp_desc.setSuffix(" mm")
        self.sp_desc.setToolTip("Quanto a chapa de MDF é cortada para encaixar o perfil")
        self.sp_esp = QDoubleSpinBox()
        self.sp_esp.setRange(3.0, 60.0)
        self.sp_esp.setDecimals(1)
        self.sp_esp.setSuffix(" mm")
        self.sp_esp.setToolTip("Espessura do MDF usada no desenho. Pontos com u ≥ este valor acompanham a espessura real da porta.")
        form.addRow("Nome:", self.ed_nome)
        form.addRow("Código:", self.ed_codigo)
        form.addRow("Desconto na chapa:", self.sp_desc)
        form.addRow("Espessura MDF de referência:", self.sp_esp)
        mid.addLayout(form)

        mid.addWidget(QLabel("<b>Pontos da seção (u, v) em mm</b>"))
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["u (profundidade)", "v (altura)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.itemChanged.connect(self._on_table_changed)
        mid.addWidget(self.table, 1)

        prow = QHBoxLayout()
        for txt, tip, fn in (
            ("+ Ponto", "Inserir ponto após o selecionado", self._add_pt),
            ("− Ponto", "Remover ponto selecionado", self._del_pt),
            ("↑", "Mover para cima", lambda: self._move_pt(-1)),
            ("↓", "Mover para baixo", lambda: self._move_pt(1)),
            ("📋 Colar", "Colar lista de pontos (uma linha por ponto: u;v ou u<TAB>v)", self._paste),
            ("⇋ Espelhar", "Espelhar seção em altura (v → -v)", self._mirror_v),
        ):
            b = QPushButton(txt)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            prow.addWidget(b)
        mid.addLayout(prow)

        for w in (self.ed_nome, self.ed_codigo):
            w.textChanged.connect(self._on_meta_changed)
        for w in (self.sp_desc, self.sp_esp):
            w.valueChanged.connect(self._on_meta_changed)

        mw = QWidget()
        mw.setLayout(mid)
        root.addWidget(mw, 1)

        # ---- Pré-visualização ----
        right = QVBoxLayout()
        right.addWidget(QLabel("<b>Pré-visualização da seção</b>"))
        self.preview = QLabel()
        self.preview.setFixedSize(380, 330)
        self.preview.setStyleSheet("border: 1px solid #94A3B8; border-radius: 6px;")
        right.addWidget(self.preview)
        self.lbl_info = QLabel()
        self.lbl_info.setStyleSheet("color: #334155;")
        right.addWidget(self.lbl_info)
        hlp = QLabel(_HELP)
        hlp.setWordWrap(True)
        hlp.setStyleSheet("font-size: 11px; color: #475569;")
        right.addWidget(hlp)
        right.addStretch()
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Save).setText("Salvar biblioteca")
        bb.button(QDialogButtonBox.Cancel).setText("Cancelar")
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        right.addWidget(bb)
        rw = QWidget()
        rw.setLayout(right)
        rw.setFixedWidth(400)
        root.addWidget(rw)

        self._refresh_list(select_id)

    # ------------------------------------------------------------------ lista
    def _refresh_list(self, select_id: str | None = None) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        sel = 0
        for i, p in enumerate(self._perfis):
            it = QListWidgetItem(lib.profile_label(p))
            it.setIcon(lib.render_profile_pixmap(p, 40, 32, cotas=False))
            self.list.addItem(it)
            if select_id and p.get("id") == select_id:
                sel = i
        self.list.blockSignals(False)
        if self._perfis:
            self.list.setCurrentRow(sel)
            self._on_select(sel)

    def _on_select(self, row: int) -> None:
        if row < 0 or row >= len(self._perfis):
            return
        self._cur = row
        p = self._perfis[row]
        self._loading = True
        self.ed_nome.setText(str(p.get("nome", "")))
        self.ed_codigo.setText(str(p.get("codigo", "")))
        self.sp_desc.setValue(float(p.get("desconto_mm", 0.0)))
        self.sp_esp.setValue(float(p.get("esp_ref_mm", 18.0)))
        self.table.setRowCount(0)
        for u, v in p.get("pontos", []):
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(_fmt(u)))
            self.table.setItem(r, 1, QTableWidgetItem(_fmt(v)))
        self._loading = False
        self._update_preview()

    def _current(self) -> dict[str, Any] | None:
        return self._perfis[self._cur] if 0 <= self._cur < len(self._perfis) else None

    def _new(self) -> None:
        nid = lib.new_profile_id("perfil_novo", self._perfis)
        self._perfis.append({
            "id": nid, "nome": "Novo perfil", "codigo": "", "desconto_mm": 20.0, "esp_ref_mm": 18.0,
            "pontos": [[0, 0], [18, 0], [18, 20], [0, 20]], "furos": [],
        })
        self._refresh_list(nid)

    def _dup(self) -> None:
        p = self._current()
        if not p:
            return
        c = lib.copy_profile(p)
        c["id"] = lib.new_profile_id(p["id"], self._perfis)
        c["nome"] = f"{p.get('nome', '')} (cópia)"
        self._perfis.append(c)
        self._refresh_list(c["id"])

    def _del(self) -> None:
        p = self._current()
        if not p or len(self._perfis) <= 1:
            return
        if QMessageBox.question(self, "Excluir perfil", f"Excluir \"{lib.profile_label(p)}\"?") != QMessageBox.Yes:
            return
        self._perfis.pop(self._cur)
        self._refresh_list()

    def _reset(self) -> None:
        if QMessageBox.question(self, "Restaurar", "Restaurar os perfis padrão? Perfis personalizados serão perdidos.") != QMessageBox.Yes:
            return
        self._perfis = lib._default_profiles()
        self._refresh_list()

    # ------------------------------------------------------------------ edição
    def _on_meta_changed(self, *_a) -> None:
        p = self._current()
        if self._loading or not p:
            return
        p["nome"] = self.ed_nome.text()
        p["codigo"] = self.ed_codigo.text()
        p["desconto_mm"] = round(self.sp_desc.value(), 2)
        p["esp_ref_mm"] = round(self.sp_esp.value(), 2)
        it = self.list.item(self._cur)
        if it:
            it.setText(lib.profile_label(p))
        self._update_preview()

    def _read_table(self) -> list[list[float]] | None:
        pts = []
        for r in range(self.table.rowCount()):
            try:
                pts.append([_parse(self.table.item(r, 0).text()), _parse(self.table.item(r, 1).text())])
            except (AttributeError, ValueError):
                return None
        return pts

    def _on_table_changed(self, *_a) -> None:
        if self._loading:
            return
        p = self._current()
        pts = self._read_table()
        if p is not None and pts is not None:
            p["pontos"] = pts
        self._update_preview(error=pts is None)

    def _set_points(self, pts: list[list[float]]) -> None:
        p = self._current()
        if p is None:
            return
        p["pontos"] = pts
        self._on_select(self._cur)

    def _add_pt(self) -> None:
        p = self._current()
        if p is None:
            return
        pts = list(p.get("pontos", []))
        r = self.table.currentRow()
        r = len(pts) - 1 if r < 0 else r
        base = pts[r] if pts else [0.0, 0.0]
        nxt = pts[(r + 1) % len(pts)] if pts else [0.0, 0.0]
        pts.insert(r + 1, [round((base[0] + nxt[0]) / 2, 2), round((base[1] + nxt[1]) / 2, 2)])
        self._set_points(pts)
        self.table.setCurrentCell(r + 1, 0)

    def _del_pt(self) -> None:
        p = self._current()
        r = self.table.currentRow()
        if p is None or r < 0 or len(p["pontos"]) <= 3:
            return
        pts = list(p["pontos"])
        pts.pop(r)
        self._set_points(pts)

    def _move_pt(self, d: int) -> None:
        p = self._current()
        r = self.table.currentRow()
        if p is None or r < 0 or not (0 <= r + d < len(p["pontos"])):
            return
        pts = list(p["pontos"])
        pts[r], pts[r + d] = pts[r + d], pts[r]
        self._set_points(pts)
        self.table.setCurrentCell(r + d, 0)

    def _paste(self) -> None:
        txt = QApplication.clipboard().text()
        pts = []
        for line in txt.splitlines():
            parts = [s for s in re.split(r"[;\t ]+", line.strip()) if s]
            if len(parts) >= 2:
                try:
                    pts.append([_parse(parts[0]), _parse(parts[1])])
                except ValueError:
                    continue
        if len(pts) < 3:
            QMessageBox.warning(self, "Colar pontos", "Copie ao menos 3 linhas no formato  u;v  (ex.: 0;34,5).")
            return
        self._set_points(pts)

    def _mirror_v(self) -> None:
        p = self._current()
        if p is None:
            return
        self._set_points([[u, -v] for u, v in p["pontos"]])

    # ------------------------------------------------------------------ preview
    def _update_preview(self, error: bool = False) -> None:
        p = self._current()
        if p is None:
            return
        if error:
            self.lbl_info.setText("⚠️ Valor inválido na tabela.")
            return
        self.preview.setPixmap(lib.render_profile_pixmap(p, 380, 330))
        try:
            u0, v0, u1, v1 = lib.section_bbox(p)
            area = abs(lib.signed_area(lib._clean(p["pontos"])))
            self.lbl_info.setText(
                f"Largura: {_fmt(round(u1 - u0, 2))} mm   Altura: {_fmt(round(v1 - v0, 2))} mm   "
                f"Área: {_fmt(round(area, 1))} mm²   Pontos: {len(p['pontos'])}"
            )
        except (ValueError, KeyError):
            self.lbl_info.setText("")

    # ------------------------------------------------------------------ salvar
    def _save(self) -> None:
        for p in self._perfis:
            if len(lib._clean(p.get("pontos", []))) < 3 or abs(lib.signed_area(lib._clean(p["pontos"]))) < 1e-6:
                QMessageBox.warning(self, "Perfil inválido", f"O perfil \"{lib.profile_label(p)}\" precisa de uma seção com área.")
                return
        try:
            lib.save_library(self._perfis)
        except OSError as exc:
            QMessageBox.critical(self, "Erro", f"Não foi possível salvar a biblioteca:\n{exc}")
            return
        cur = self._current()
        self.selected_id = cur.get("id") if cur else None
        self.accept()


def fill_profile_combo(combo, select_id: str | None = None) -> None:
    """Preenche um QComboBox com os perfis da biblioteca (itemData = id)."""
    combo.blockSignals(True)
    cur = select_id or combo.currentData()
    combo.clear()
    for p in lib.load_library():
        combo.addItem(lib.render_profile_pixmap(p, 32, 24, cotas=False), lib.profile_label(p), p.get("id"))
    idx = combo.findData(cur) if cur else 0
    combo.setCurrentIndex(idx if idx >= 0 else 0)
    combo.blockSignals(False)
