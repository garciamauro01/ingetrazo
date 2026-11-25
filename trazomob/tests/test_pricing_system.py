# SPDX-License-Identifier: GPL-3.0-or-later
"""Testes do sistema híbrido de precificação, linhas de ferragens, cálculo de chapas e PIN."""
import pytest

from trazomob.domain.preferences import TrazoMobPreferencesManager
from trazomob.production.pricing import (
    calcular_orcamento_cutlist,
    calcular_orcamento_por_ambiente,
    formatar_moeda,
)


@pytest.fixture
def sample_parts():
    return [
        {
            "nome": "Porta Esquerda",
            "material": "MDF Louro Freijó 18mm",
            "espessura": 18.0,
            "comprimento": 700.0,
            "largura": 400.0,
            "quantidade": 2,
            "fita_c1": True, "fita_c2": True, "fita_l1": True, "fita_l2": True,
            "espessura_fita": 1.0,
            "ambiente": "Cozinha",
        },
        {
            "nome": "Lateral Esquerda",
            "material": "MDF Branco TX 15mm",
            "espessura": 15.0,
            "comprimento": 720.0,
            "largura": 560.0,
            "quantidade": 2,
            "fita_c1": True, "fita_c2": False, "fita_l1": False, "fita_l2": False,
            "espessura_fita": 0.45,
            "ambiente": "Cozinha",
        },
        {
            "nome": "Tampo Nicho",
            "material": "MDF MaterialInexistente 15mm",
            "espessura": 15.0,
            "comprimento": 600.0,
            "largura": 300.0,
            "quantidade": 1,
            "ambiente": "Banheiro",
        }
    ]


def test_pin_protection():
    prefs = TrazoMobPreferencesManager.get_instance()
    # Sem PIN inicialmente
    prefs.set_pin("")
    assert not prefs.has_pin()
    assert prefs.check_pin("qualquer") is True

    # Define PIN 1234
    assert prefs.set_pin("1234") is True
    assert prefs.has_pin() is True
    assert prefs.check_pin("1234") is True
    assert prefs.check_pin("0000") is False

    # Limpa PIN
    prefs.set_pin("")
    assert not prefs.has_pin()


def test_pin_usa_pbkdf2_com_salt():
    """O PIN é derivado com PBKDF2 + salt; hashes iguais geram valores distintos."""
    prefs = TrazoMobPreferencesManager.get_instance()
    try:
        prefs.set_pin("1234")
        primeiro = prefs.get_pricing_config()["pin_hash"]
        assert primeiro.startswith("pbkdf2_sha256$")
        assert len(primeiro.split("$")) == 4

        prefs.set_pin("1234")
        segundo = prefs.get_pricing_config()["pin_hash"]
        # Salt aleatório => hashes diferentes para o mesmo PIN
        assert primeiro != segundo
        assert prefs.check_pin("1234") is True
    finally:
        prefs.set_pin("")


def test_pin_migra_hash_legado_sem_salt():
    """Um hash antigo (SHA-256 sem salt) continua válido e é migrado no 1º uso."""
    import hashlib

    prefs = TrazoMobPreferencesManager.get_instance()
    try:
        pricing = prefs.get_pricing_config()
        pricing["pin_hash"] = hashlib.sha256("4321".encode("utf-8")).hexdigest()

        assert prefs.check_pin("4321") is True
        assert prefs.check_pin("0000") is False
        # Após o acesso bem-sucedido, o hash passa a ser PBKDF2
        assert prefs.get_pricing_config()["pin_hash"].startswith("pbkdf2_sha256$")
    finally:
        prefs.set_pin("")


def test_alerta_itens_sem_preco(sample_parts):
    resumo = calcular_orcamento_cutlist(sample_parts)
    # MDF MaterialInexistente deve cair em itens_sem_preco
    assert any("MaterialInexistente" in s for s in resumo.itens_sem_preco)


def test_linhas_ferragens_multiplicador(sample_parts):
    resumo_eco = calcular_orcamento_cutlist(sample_parts, linha_ferragem_override="economica")
    resumo_std = calcular_orcamento_cutlist(sample_parts, linha_ferragem_override="standard")
    resumo_prem = calcular_orcamento_cutlist(sample_parts, linha_ferragem_override="premium")

    assert resumo_eco.custo_ferragens < resumo_std.custo_ferragens
    assert resumo_prem.custo_ferragens > resumo_std.custo_ferragens
    assert resumo_prem.total_final > resumo_std.total_final


def test_orcamento_por_ambiente(sample_parts):
    ambientes = calcular_orcamento_por_ambiente(sample_parts)
    assert any("Cozinha" in k for k in ambientes.keys())
    assert any("Banheiro" in k for k in ambientes.keys())
    for res in ambientes.values():
        assert res.total_final > 0
        assert res.custo_direto > 0


def test_formatar_moeda():
    assert formatar_moeda(1250.50) == "R$ 1.250,50"
    assert formatar_moeda(0.0) == "R$ 0,00"

