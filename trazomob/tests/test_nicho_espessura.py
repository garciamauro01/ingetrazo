# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes de parametrização e consistência da espessura de chapas no Nicho Aberto Decorativo."""
from __future__ import annotations

import pytest
from trazomob.builders.cabinet import CabinetBuilder
from trazomob.domain.param_mapper import extract_ui_module_params, populate_ui_from_module


class _DummyWidget:
    def __init__(self, value):
        self._val = value

    def value(self):
        return self._val

    def currentText(self):
        return str(self._val)

    def currentIndex(self):
        return 0


class _DummyForm:
    def __init__(self, esp_txt="18 mm", mat_txt="MDF Louro Freijó"):
        self.sp_largura = _DummyWidget(600)
        self.sp_altura = _DummyWidget(400)
        self.sp_prof = _DummyWidget(300)
        self.sp_rodape = _DummyWidget(0)
        self.sp_prateleiras = _DummyWidget(2)
        self.sp_divisoes = _DummyWidget(1)
        self.cb_espessura = _DummyWidget(esp_txt)
        self.cb_material = _DummyWidget(mat_txt)


@pytest.mark.parametrize("esp_esperada", [15.0, 18.0, 20.0, 25.0])
def test_nicho_todas_as_pecas_respeitam_espessura(esp_esperada):
    """Garante que no nicho aberto 100% das peças (Laterais, Base, Tampo, Divisões Horiz e Vert) possuem a espessura exata."""
    form = _DummyForm(esp_txt=f"{int(esp_esperada)} mm", mat_txt="MDF Louro Freijó")
    params = extract_ui_module_params(form, base_params={"tipo": "nicho"})

    assert params["espessura"] == esp_esperada
    assert f"{int(esp_esperada)}mm" in params["material"]

    grp = CabinetBuilder.build_module_group(params)
    assert len(grp.children) >= 4  # 2 Laterais + Base + Tampo + Divisórias

    nomes_esperados = [
        "Nicho - Lateral Esquerda",
        "Nicho - Lateral Direita",
        "Nicho - Base Inferior",
        "Nicho - Tampo Superior",
        "Nicho - Divisao Horiz 1",
        "Nicho - Divisao Horiz 2",
        "Nicho - Divisao Vert 1",
    ]

    for child in grp.children:
        meta = child.ext.get("trazomob", {})
        assert meta is not None, f"Peça {child.name} não possui metadados trazomob"
        assert meta.get("espessura") == esp_esperada, (
            f"Peça '{child.name}' tem espessura {meta.get('espessura')}mm, esperava {esp_esperada}mm"
        )
        assert meta.get("material") == f"MDF Louro Freijó {int(esp_esperada)}mm"


def test_nicho_sem_form_usando_espessura_param():
    """Garante que a construção direta com chave 'espessura' ou 'esp_mm' propaga 25mm em todas as peças."""
    params = {
        "tipo": "nicho",
        "largura": 800,
        "altura": 500,
        "profundidade": 350,
        "espessura": 25.0,
        "material": "MDF Grafite 25mm",
        "num_prateleiras": 1,
        "num_divisoes": 1,
    }
    grp = CabinetBuilder.build_module_group(params)
    for child in grp.children:
        meta = child.ext.get("trazomob", {})
        assert meta.get("espessura") == 25.0, f"Peça {child.name} não obedeceu a espessura de 25mm"
        assert meta.get("material") == "MDF Grafite 25mm"

