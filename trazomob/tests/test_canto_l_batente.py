# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Batente de quina opcional do Balcão Canto L.

Sem o batente o módulo mantém o cruzamento atual das portas. Com o batente,
surge um montante de 15 x 15 mm na quina interna e a porta da Ala Y recua
a espessura da frente para encostar nele com 3 mm de fresta.
"""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from trazomob.builders.cabinet import CabinetBuilder
from trazomob.domain.catalog import MODULE_CATALOG
from trazomob.domain.module_geometry import build_default_module_params


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _canto_l_params(com_batente: bool) -> dict:
    cat = next(
        m for c in MODULE_CATALOG.values() for m in c
        if m.get("id") == "balcao_canto_l")
    params = build_default_module_params(cat)
    params["rodape"] = 0.0
    params["tem_batente_canto"] = com_batente
    return params


def _bounds(group):
    pts = [(v.position.x() * 1000.0, v.position.y() * 1000.0)
           for v in group.mesh.vertices]
    return pts


def test_sem_batente_mantem_cruzamento_atual(qapp):
    mod = CabinetBuilder.build_module_group(_canto_l_params(False),
                                            offset=(0.0, 0.0, 0.0))

    assert not any("Batente Quina" in c.name for c in mod.children)
    porta_y = next(c for c in mod.children if "Porta Ala Y" in c.name)
    assert max(y for _, y in _bounds(porta_y)) > 445.0


def test_portas_cobrem_as_laterais_com_3_mm_da_borda(qapp):
    mod = CabinetBuilder.build_module_group(_canto_l_params(False),
                                            offset=(0.0, 0.0, 0.0))

    # A porta da Ala Y é sobreposta: começa a 3 mm da borda externa (Y = 3),
    # cobrindo a Lateral Frontal Ala Y (que ocupa Y = 0..15).
    porta_y = next(c for c in mod.children if "Porta Ala Y" in c.name)
    assert min(y for _, y in _bounds(porta_y)) == pytest.approx(3.0, abs=0.1)
    # 3 mm até a quina interna: 1000 - 550 - 3 (borda) - 3 (quina) = 444.
    assert porta_y.ext["trazomob"]["largura"] == pytest.approx(444.0, abs=0.1)

    # A porta da Ala X é sobreposta: cobre a Lateral Direita (X = 985..1000)
    # e termina a 3 mm da borda externa (X = 997).
    porta_x = next(c for c in mod.children if "Porta Ala X" in c.name)
    assert max(x for x, _ in _bounds(porta_x)) == pytest.approx(997.0, abs=0.1)
    # 1000 - (550 + 15 + 3) - 3 = 429.
    assert porta_x.ext["trazomob"]["largura"] == pytest.approx(429.0, abs=0.1)


def test_batente_fecha_quina_e_recua_porta_ala_y(qapp):
    mod = CabinetBuilder.build_module_group(_canto_l_params(True),
                                            offset=(0.0, 0.0, 0.0))

    batente = next(c for c in mod.children if "Batente Quina" in c.name)
    xs = [x for x, _ in _bounds(batente)]
    ys = [y for _, y in _bounds(batente)]
    assert min(xs) == pytest.approx(550.0, abs=0.1)
    assert max(xs) == pytest.approx(565.0, abs=0.1)
    assert min(ys) == pytest.approx(435.0, abs=0.1)
    assert max(ys) == pytest.approx(450.0, abs=0.1)

    porta_y = next(c for c in mod.children if "Porta Ala Y" in c.name)
    # A borda nominal fica em 432 mm; a geometria do perfil avança ~1,5 mm.
    assert max(y for _, y in _bounds(porta_y)) <= 434.0
