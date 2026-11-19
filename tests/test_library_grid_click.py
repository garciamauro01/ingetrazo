"""Um item sem miniatura continua clicável em toda a sua casa do grid.

Sem ícone, o ``QListWidget`` em ``IconMode`` media o item só pelo texto: um
nome curto ficava com ~12 px de altura numa célula de ~142 px e o clique no
resto da casa não selecionava nada (Marco navegava com as setas até o item
e só então clicava em Inserir).
"""
from __future__ import annotations

from itertools import pairwise

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QListWidget, QListWidgetItem

from views import library_grid

GRID = QSize(130, 142)


def _grid(names, *, icons=False):
    lw = QListWidget()
    library_grid.configure(lw, icon=96, grid=GRID)
    lw.resize(420, 400)
    for name in names:
        item = QListWidgetItem(name)
        lw.addItem(item)
    lw.show()
    QApplication.processEvents()
    return lw


def _center_of_cell(widget, row):
    r = widget.visualItemRect(widget.item(row))
    return QPoint(r.left() + GRID.width() // 2,
                  r.top() + GRID.height() // 2)


def test_every_cell_is_clickable_without_a_thumbnail():
    lw = _grid(["Sofa", "Mesa", "Tapete", "Lava e Seca 11kg Inox"])

    for row in range(lw.count()):
        hit = lw.indexAt(_center_of_cell(lw, row))
        assert hit.isValid() and hit.row() == row, row


def test_a_real_click_on_an_iconless_cell_selects_it():
    lw = _grid(["Sofa", "Mesa", "Tapete"])
    QTest.mouseClick(lw.viewport(), Qt.LeftButton,
                     pos=_center_of_cell(lw, 1))
    assert lw.currentItem() is lw.item(1)


def test_long_names_still_hit_the_right_cell_and_do_not_overlap():
    names = [
        "Sofa",
        ("Armario ropero de tres puertas con espejo central, cajones "
         "inferiores y barredora, madera maciza de roble con acabado al "
         "aceite y tiradores de laton envejecido, baldas regulables"),
        "Mesa",
        ("Lavadora y secadora LG F4V9100WT de 11 kg con Inteligencia "
         "Artificial, WiFi, ciclo de vapor y programa rapido"),
    ]
    lw = _grid(names)

    rects = [lw.visualItemRect(lw.item(i)) for i in range(lw.count())]
    for i, r in enumerate(rects):
        hit = lw.indexAt(_center_of_cell(lw, i))
        assert hit.isValid() and hit.row() == i, i
    for a, b in pairwise(rects):
        assert a.bottom() < b.top() or a.right() < b.left()


def test_configure_keeps_icon_size_and_word_wrap():
    lw = _grid(["Sofa"])
    assert lw.viewMode() == QListWidget.IconMode
    assert lw.gridSize() == GRID
    assert lw.iconSize() == QSize(96, 96)
    assert lw.wordWrap()
    assert isinstance(lw.itemDelegate(), library_grid.CellDelegate)


def test_both_library_dialogs_use_the_cell_delegate(monkeypatch):
    from core import library, user_library
    from views import library_dialog, user_library_dialog

    monkeypatch.setattr(library, "index", list)
    monkeypatch.setattr(user_library, "index", list)
    monkeypatch.setattr(user_library, "facets",
                        lambda _: {k: {} for k in
                                   ("categorias", "tipos", "marcas")})

    online = library_dialog.LibraryDialog(None)
    own = user_library_dialog.UserLibraryDialog(None)
    try:
        assert isinstance(online._list.itemDelegate(),
                          library_grid.CellDelegate)
        assert isinstance(own._list.itemDelegate(),
                          library_grid.CellDelegate)
    finally:
        online.close()
        own.close()
