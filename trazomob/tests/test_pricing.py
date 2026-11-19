# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes do motor de precificação e da proposta comercial (Onda 3)."""

from __future__ import annotations

import copy

import pytest

from trazomob.domain.preferences import DEFAULT_PREFERENCES, TrazoMobPreferencesManager
from trazomob.production.pricing import (
    _get_chapa_preco_flexivel,
    _get_fita_preco_flexivel,
    _inferir_ferragens_peca,
    agrupar_por_ambiente,
    calcular_orcamento_cutlist,
    calcular_orcamento_por_ambiente,
    formatar_moeda,
    gerar_proposta_dados,
)


@pytest.fixture()
def prefs():
    """Instancia o manager com a seção de preços restaurada para os padrões."""
    manager = TrazoMobPreferencesManager.get_instance()
    original = copy.deepcopy(manager._data.get("pricing", {}))
    manager._data["pricing"] = copy.deepcopy(DEFAULT_PREFERENCES["pricing"])
    try:
        yield manager
    finally:
        manager._data["pricing"] = original


def _peca(nome="Lateral Esquerda", comp=800, larg=550, esp=15, qtd=1,
          material="MDF Branco TX 15mm", fitas=(True, False, True, False),
          esp_fita=0.45, ambiente=None, pavimento=None):
    part = {
        "nome": nome,
        "comprimento": comp,
        "largura": larg,
        "espessura": esp,
        "quantidade": qtd,
        "material": material,
        "fita_c1": fitas[0],
        "fita_c2": fitas[1],
        "fita_l1": fitas[2],
        "fita_l2": fitas[3],
        "espessura_fita": esp_fita,
    }
    if ambiente is not None:
        part["ambiente"] = ambiente
    if pavimento is not None:
        part["pavimento"] = pavimento
    return part


# ─────────────────────────────────────────────────────────────────────────────
# Formatação e lookups flexíveis
# ─────────────────────────────────────────────────────────────────────────────

def test_formatar_moeda():
    assert formatar_moeda(0) == "R$ 0,00"
    assert formatar_moeda(1234.5) == "R$ 1.234,50"
    assert formatar_moeda(0.999) == "R$ 1,00"


def test_chapa_lookup_exato_e_sem_tx():
    tabela = {"MDF Branco TX 15mm": 85.0, "MDF Branco 15mm": 80.0}
    assert _get_chapa_preco_flexivel(tabela, "MDF Branco TX", 15) == 85.0
    assert _get_chapa_preco_flexivel(tabela, "MDF Branco", 15) == 80.0


def test_chapa_lookup_por_prefixo_e_desconhecido():
    tabela = {"MDF Branco TX 15mm": 85.0}
    # Nome do builder já com espessura inclusa
    assert _get_chapa_preco_flexivel(tabela, "MDF Branco TX 15mm", 15) == 85.0
    assert _get_chapa_preco_flexivel(tabela, "Compensado Naval", 15) == 0.0


def test_fita_lookup_virgula_ponto_e_prefixo():
    tabela = {"0,45mm": 1.80, "1.0mm": 2.50}
    assert _get_fita_preco_flexivel(tabela, 0.45) == 1.80
    assert _get_fita_preco_flexivel(tabela, 1.0) == 2.50
    assert _get_fita_preco_flexivel({"0,45mm": 1.80}, 0.45) == 1.80
    assert _get_fita_preco_flexivel({}, 0.45) == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Cálculo do orçamento
# ─────────────────────────────────────────────────────────────────────────────

def test_orcamento_basico_matematica(prefs):
    parts = [_peca(comp=1000, larg=1000, qtd=2)]  # 2 m²
    orc = calcular_orcamento_cutlist(parts)

    assert orc.custo_direto > 0
    assert orc.markup_valor == pytest.approx(orc.custo_direto * 0.35, abs=0.02)
    assert orc.subtotal_com_markup == pytest.approx(orc.custo_direto * 1.35, abs=0.02)
    assert orc.impostos_valor == pytest.approx(orc.subtotal_com_markup * 0.18, abs=0.02)
    esperado = (
        (orc.custo_direto * 1.35)
        + (orc.custo_direto * 1.35 * 0.18)
    )
    esperado -= esperado * 0.05
    esperado += 150.0
    assert orc.total_final == pytest.approx(esperado, abs=0.05)


def test_a_vista_e_parcelado_nao_duplicam_desconto(prefs):
    """Regressão: o desconto à vista é aplicado uma única vez.

    ``total_final`` é o preço à vista (desconto já embutido) e o parcelado parte
    do valor sem esse desconto, em vez de descontar duas vezes.
    """
    orc = calcular_orcamento_cutlist([_peca(comp=1000, larg=1000, qtd=2)])
    assert orc.total_a_vista == pytest.approx(orc.total_final, abs=0.01)
    assert orc.total_parcelado == pytest.approx(orc.total_final + orc.desconto_valor, abs=0.01)
    assert orc.valor_parcela == pytest.approx(orc.total_parcelado / orc.num_parcelas, abs=0.01)
    # O parcelado nunca é mais barato que o à vista
    assert orc.total_parcelado >= orc.total_a_vista


def test_orcamento_tem_chapa_e_fita(prefs):
    orc = calcular_orcamento_cutlist([_peca()])
    categorias = {i.categoria for i in orc.itens}
    assert "chapa" in categorias
    assert "fita" in categorias
    assert "ferragem" in categorias
    assert "mao_de_obra" in categorias
    assert "frete" in categorias

    chapas = [i for i in orc.itens if i.categoria == "chapa"]
    fitas = [i for i in orc.itens if i.categoria == "fita"]
    # Consolidado: uma linha por material / espessura de fita
    assert len(chapas) == 1
    assert len(fitas) == 1
    assert fitas[0].quantidade == pytest.approx(1.35, abs=0.01)  # 0.8 + 0.55


def test_orcamento_consolida_repetidas(prefs):
    parts = [_peca(qtd=3), _peca(qtd=2)]
    orc = calcular_orcamento_cutlist(parts)
    chapas = [i for i in orc.itens if i.categoria == "chapa"]
    assert len(chapas) == 1
    # 5 peças de 0.8 x 0.55 = 2.2 m²
    assert chapas[0].quantidade == pytest.approx(2.2, abs=0.001)


def test_orcamento_sem_preco_de_chapa(prefs):
    orc = calcular_orcamento_cutlist([_peca(material="Material Inexistente 15mm")])
    chapas = [i for i in orc.itens if i.categoria == "chapa"]
    assert chapas == []
    # Mão de obra e frete continuam sendo cobrados
    assert orc.custo_direto > 0


def test_frete_por_m2(prefs):
    prefs._data["pricing"]["frete_tipo"] = "por_m2"
    prefs._data["pricing"]["frete_valor"] = 10.0
    orc = calcular_orcamento_cutlist([_peca(comp=1000, larg=1000)])  # 1 m²
    assert orc.frete_valor == pytest.approx(10.0, abs=0.01)


def test_orcamento_por_ambiente(prefs):
    parts = [
        _peca(ambiente="Cozinha", pavimento="Térreo"),
        _peca(ambiente="Quarto", pavimento="Superior"),
        _peca(ambiente="Cozinha", pavimento="Térreo"),
    ]
    por_amb = calcular_orcamento_por_ambiente(parts)
    assert "Cozinha (Térreo)" in por_amb
    assert "Quarto (Superior)" in por_amb
    assert por_amb["Cozinha (Térreo)"].total_final > 0
    # A soma dos custos diretos por ambiente bate com o cálculo global
    total_amb = sum(o.custo_direto for o in por_amb.values())
    total_geral = calcular_orcamento_cutlist(parts).custo_direto
    assert total_amb == pytest.approx(total_geral, abs=0.05)


def test_proposta_dados_estrutura(prefs):
    dados = gerar_proposta_dados(
        parts=[_peca()],
        project_name="Cozinha",
        client_name="Maria",
        client_data={"telefone": "123"},
    )
    assert dados["cliente"] == "Maria"
    assert dados["projeto"] == "Cozinha"
    assert "orcamento_geral" in dados
    assert "orcamento_por_ambiente" in dados
    assert dados["estatisticas"]["total_pecas"] == 1
    assert dados["empresa"]["nome"]


# ─────────────────────────────────────────────────────────────────────────────
# Documentos HTML
# ─────────────────────────────────────────────────────────────────────────────

def test_proposta_html_contem_cliente_e_total(prefs, tmp_path):
    from trazomob.production.report import generate_proposal_html

    destino = tmp_path / "proposta.html"
    html = generate_proposal_html(
        parts=[_peca()],
        project_name="Cozinha Gourmet",
        client_name="Maria Souza",
        client_data={"telefone": "(11) 98888-7777", "cpf_cnpj": "000.000.000-00"},
        observacoes="Entrega em 30 dias.",
        filepath=destino,
    )
    assert destino.exists()
    assert "Maria Souza" in html
    assert "Cozinha Gourmet" in html
    assert "Proposta Comercial" in html
    assert "000.000.000-00" in html
    assert "Entrega em 30 dias." in html
    assert formatar_moeda(calcular_orcamento_cutlist([_peca()]).total_final) in html
    assert "Imprimir / Salvar PDF" in html


def test_relatorio_com_e_sem_orcamento(prefs):
    from trazomob.production.report import generate_project_html_report

    parts = [_peca()]
    sem = generate_project_html_report(parts, project_name="Projeto X")
    assert "Orçamento Detalhado" not in sem
    assert "Lista Completa de Peças" in sem

    com = generate_project_html_report(parts, project_name="Projeto X", include_pricing=True)
    assert "Orçamento Detalhado" in com
    assert "Resumo Financeiro" in com
    assert formatar_moeda(calcular_orcamento_cutlist(parts).total_final) in com


# ─────────────────────────────────────────────────────────────────────────────
# Regressão: inferência de ferragens (palavra inteira + altura)
# ─────────────────────────────────────────────────────────────────────────────

def test_inferir_ferragens_nao_casa_substring_de_pes():
    """``pes`` não pode casar dentro de "compesso"/"pessoal" (bug antigo)."""
    ferr = _inferir_ferragens_peca(
        {"nome": "Compesso Interno", "quantidade": 1, "comprimento": 800, "largura": 300}
    )
    assert ferr["pes_nivelador"] == 0
    assert all(v == 0 for v in ferr.values())


def test_inferir_ferragens_rodape_com_acento():
    """"Rodapé" deve casar (comparação sem acento) e contar o pé nivelador."""
    ferr = _inferir_ferragens_peca(
        {"nome": "Rodapé Frontal", "quantidade": 2, "comprimento": 600, "largura": 100}
    )
    assert ferr["pes_nivelador"] == 2


def test_inferir_ferragens_dobradicas_por_altura():
    """Porta alta recebe mais dobradiças que porta baixa."""
    baixa = _inferir_ferragens_peca(
        {"nome": "Porta Esquerda", "quantidade": 1, "comprimento": 700, "largura": 400}
    )
    alta = _inferir_ferragens_peca(
        {"nome": "Porta Esquerda", "quantidade": 1, "comprimento": 2000, "largura": 400}
    )
    assert baixa["dobradica_35mm"] == 2
    assert alta["dobradica_35mm"] == 4


# ─────────────────────────────────────────────────────────────────────────────
# Regressão: agrupamento por ambiente como fonte única de verdade
# ─────────────────────────────────────────────────────────────────────────────

def test_agrupar_por_ambiente_nao_colide_substring():
    """O agrupamento usa a chave exata, sem casar "Sala" com "Sala de Jantar"."""
    parts = [_peca(ambiente="Sala"), _peca(ambiente="Sala de Jantar")]
    grupos = agrupar_por_ambiente(parts)
    assert set(grupos) == {"Sala (Térreo)", "Sala de Jantar (Térreo)"}
    assert len(grupos["Sala (Térreo)"]) == 1
    assert len(grupos["Sala de Jantar (Térreo)"]) == 1


def test_agrupar_por_ambiente_chaves_batem_com_orcamento():
    parts = [
        _peca(ambiente="Cozinha", pavimento="Térreo"),
        _peca(ambiente="Quarto", pavimento="Superior"),
    ]
    assert set(agrupar_por_ambiente(parts)) == set(calcular_orcamento_por_ambiente(parts))


def test_ambiente_da_peca_le_ext_e_wall():
    """A peça herda ambiente/pavimento do módulo ou da parede que a contém."""
    from trazomob.production.parts import _ambiente_da_peca

    class _G:
        pass

    g1 = _G()
    g1.ext = {"ambiente": "Cozinha", "pavimento": "Térreo"}
    assert _ambiente_da_peca(g1) == ("Cozinha", "Térreo")

    g2 = _G()
    g2.ext = {"trazomob_wall": {"ambiente": "Sala"}}
    assert _ambiente_da_peca(g2) == ("Sala", None)

    g3 = _G()
    g3.ext = None
    assert _ambiente_da_peca(g3) == (None, None)


# ─────────────────────────────────────────────────────────────────────────────
# Regressão: fluxo de proposta reutilizável
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    return app


def test_proposal_export_dialog_get_data(qapp):
    from trazomob.ui.proposal_dialog import ProposalExportDialog

    dlg = ProposalExportDialog(client_name="Maria")
    dlg.ed_cpf.setText("  000.000.000-00  ")
    data = dlg.get_data()
    assert data["nome"] == "Maria"
    assert data["cpf_cnpj"] == "000.000.000-00"
    assert data["observacoes"] == ""


def test_export_proposal_sem_pecas_retorna_none(qapp, monkeypatch):
    from trazomob.ui import proposal_dialog

    monkeypatch.setattr(proposal_dialog.QMessageBox, "information", lambda *a, **k: None)
    assert proposal_dialog.export_proposal(None, []) is None


def test_export_proposal_nome_obrigatorio(qapp, monkeypatch):
    from trazomob.ui import proposal_dialog

    monkeypatch.setattr(proposal_dialog.ProposalExportDialog, "exec", lambda self: proposal_dialog.QDialog.Accepted)
    monkeypatch.setattr(
        proposal_dialog.ProposalExportDialog,
        "get_data",
        lambda self: {"nome": "", "cpf_cnpj": "", "endereco": "", "cidade": "",
                      "telefone": "", "email": "", "observacoes": ""},
    )
    monkeypatch.setattr(proposal_dialog.QMessageBox, "warning", lambda *a, **k: None)
    assert proposal_dialog.export_proposal(None, [_peca()]) is None


def test_export_proposal_gera_html(qapp, monkeypatch, tmp_path, prefs):
    from trazomob.ui import proposal_dialog

    destino = tmp_path / "proposta.html"
    monkeypatch.setattr(proposal_dialog.ProposalExportDialog, "exec", lambda self: proposal_dialog.QDialog.Accepted)
    monkeypatch.setattr(
        proposal_dialog.ProposalExportDialog,
        "get_data",
        lambda self: {"nome": "Maria Souza", "cpf_cnpj": "000.000.000-00", "endereco": "Rua X",
                      "cidade": "SP", "telefone": "(11) 98888-7777", "email": "m@x.com",
                      "observacoes": "Entrega em 30 dias."},
    )
    monkeypatch.setattr(
        proposal_dialog.QFileDialog,
        "getSaveFileName",
        lambda *a, **k: (str(destino), "HTML (*.html)"),
    )
    monkeypatch.setattr(proposal_dialog.QMessageBox, "information", lambda *a, **k: None)

    resultado = proposal_dialog.export_proposal(None, [_peca()], project_name="Cozinha")
    assert resultado == str(destino)
    assert destino.exists()
    html = destino.read_text(encoding="utf-8")
    assert "Maria Souza" in html
    assert "Cozinha" in html
    assert "Entrega em 30 dias." in html
