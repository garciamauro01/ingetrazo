# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Fase 5: a auditoria de miniaturas não altera os PNGs existentes."""
from __future__ import annotations

from trazomob.assets.catalog import get_esquadrias_catalogo
from trazomob.scripts.audit_esquadria_thumbs import audit_thumbs


def test_auditoria_nao_aponta_pngs_corrompidos():
    resultado = audit_thumbs()
    assert resultado["invalidas"] == []
    assert set(resultado["com_miniatura"]).issubset(
        {str(modelo["id"]) for modelo in get_esquadrias_catalogo()}
    )
    # Os órfãos conhecidos são variantes legadas com sufixo de largura
    # (porta_giro_80.png etc.). A galeria procura "<id>.png", então eles não
    # são usados; permanecem no disco até decisão explícita de limpeza.
    assert all(nome.rsplit("_", 1)[-1].isdigit() for nome in resultado["orfas"])


def test_todas_as_portas_e_janelas_tem_miniatura_propria():
    """Os ícones da galeria devem vir das próprias portas/janelas, não do genérico."""
    assert audit_thumbs()["sem_miniatura"] == []


def test_auditoria_particiona_o_catalogo_sem_perder_modelos():
    resultado = audit_thumbs()
    com = set(resultado["com_miniatura"])
    sem = set(resultado["sem_miniatura"])
    assert com.isdisjoint(sem)
    assert com | sem == {str(modelo["id"]) for modelo in get_esquadrias_catalogo()}


def test_auditoria_e_somente_leitura(tmp_path):
    alvo = tmp_path / "thumbs"
    alvo.mkdir()
    (alvo / "porta_giro.png").write_bytes(b"\x89PNG\r\n\x1a\nconteudo")
    (alvo / "quebrado.png").write_bytes(b"nao-e-png")
    antes = {p.name: p.read_bytes() for p in alvo.iterdir()}

    resultado = audit_thumbs(alvo)

    assert resultado["invalidas"] == ["quebrado.png"]
    assert {p.name: p.read_bytes() for p in alvo.iterdir()} == antes
