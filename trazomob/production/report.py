# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Gerador de Relatório Executivo, Orçamento Técnico e Proposta Comercial (TrazoMob Onda 3).

Produz documentos em HTML prontos para impressão/PDF:
- Relatório de produção (materiais, peças, fitas, ferragens)
- Orçamento detalhado com preços, markup, impostos, desconto, frete
- Proposta comercial com dados do cliente, empresa, validade
"""
from __future__ import annotations

import logging
import math
from typing import Any, List, Dict, Optional
from pathlib import Path

from ..production.pricing import (
    calcular_orcamento_cutlist,
    calcular_orcamento_por_ambiente,
    gerar_proposta_dados,
    formatar_moeda,
)
from ..domain.hardware import (
    consolidate_hardware,
    deserialize_hardware,
    hardware_total_preco,
)

logger = logging.getLogger("trazomob.report")


def generate_project_html_report(
    parts: List[dict[str, Any]],
    project_name: str = "Projeto TrazoMob",
    client_name: str = "Cliente",
    include_pricing: bool = False,
    client_data: Optional[Dict[str, str]] = None,
) -> str:
    """Gera um relatório executivo completo em HTML com design limpo e profissional.

    Args:
        parts: Lista de peças da cutlist
        project_name: Nome do projeto
        client_name: Nome do cliente
        include_pricing: Se True, inclui seção de orçamento/preços
        client_data: Dados adicionais do cliente (endereço, telefone, etc.)
    """
    total_pecas = sum(p.get("quantidade", 1) for p in parts)

    # Agrupa por material
    by_mat: Dict[str, Dict[str, float]] = {}
    total_area_m2 = 0.0
    total_linear_tape_m = 0.0

    # Estimativa de ferragens (a partir dos dados armazenados por módulo)
    seen_mod_keys: set = set()
    hw_entries: list = []
    total_puxadores = 0
    total_dobradicas = 0
    total_corredicas = 0

    for p in parts:
        qtd = p.get("quantidade", 1)
        mat = str(p.get("material", "MDF"))
        comp_m = float(p.get("comprimento", 0.0)) / 1000.0
        larg_m = float(p.get("largura", 0.0)) / 1000.0
        area_m2 = comp_m * larg_m * qtd
        total_area_m2 += area_m2

        if mat not in by_mat:
            by_mat[mat] = {"area": 0.0, "pecas": 0}
        by_mat[mat]["area"] += area_m2
        by_mat[mat]["pecas"] += qtd

        # Fitas de borda
        tape_len = 0.0
        if p.get("fita_c1"):
            tape_len += comp_m
        if p.get("fita_c2"):
            tape_len += comp_m
        if p.get("fita_l1"):
            tape_len += larg_m
        if p.get("fita_l2"):
            tape_len += larg_m
        total_linear_tape_m += tape_len * qtd

        # Ferragens: coleta uma vez por módulo (dedup por _module_key)
        mod_key = p.get("_module_key")
        module_hw = p.get("module_hardware") or []
        if mod_key is not None and module_hw and mod_key not in seen_mod_keys:
            seen_mod_keys.add(mod_key)
            hw_entries.append(
                (mod_key, deserialize_hardware(module_hw))
            )

    # Consolida ferragens de todos os módulos (uma contagem por módulo)
    consolidado_hw = consolidate_hardware(hw_entries)

    # Tabela de materiais
    mat_rows = ""
    for mat, data in by_mat.items():
        area = data["area"]
        chapas_est = math.ceil(area / (2.75 * 1.85 * 0.85))  # 85% aproveitamento
        mat_rows += f"""
        <tr>
            <td><b>{mat}</b></td>
            <td style="text-align: center;">{data['pecas']}</td>
            <td style="text-align: right;">{area:.2f} m²</td>
            <td style="text-align: right;"><b>~{chapas_est} chapa(s)</b></td>
        </tr>
        """

    # Tabela detalhada de peças
    part_rows = ""
    for i, p in enumerate(parts):
        qtd = p.get("quantidade", 1)
        comp = f"{p.get('comprimento', 0.0):.0f}"
        larg = f"{p.get('largura', 0.0):.0f}"
        comp_c = f"{p.get('comprimento_corte', p.get('comprimento', 0.0)):.0f}"
        larg_c = f"{p.get('largura_corte', p.get('largura', 0.0)):.0f}"
        esp = f"{p.get('espessura', 15.0):.0f}"
        fitas = f"C:{int(bool(p.get('fita_c1')))}/{int(bool(p.get('fita_c2')))} L:{int(bool(p.get('fita_l1')))}/{int(bool(p.get('fita_l2')))}"
        part_rows += f"""
        <tr>
            <td style="text-align: center;">{i+1}</td>
            <td><b>{p.get('nome', 'Peça')}</b></td>
            <td style="text-align: center;"><b>{qtd}</b></td>
            <td style="text-align: right;">{comp} x {larg} x {esp}</td>
            <td style="text-align: right; color: #475569;">{comp_c} x {larg_c}</td>
            <td>{p.get('material', '')}</td>
            <td style="text-align: center; font-size: 11px;">{fitas}</td>
        </tr>
        """

    # Tabela de ferragens (contagem real por módulo, sem heurística de nome)
    hw_rows = ""
    if consolidado_hw:
        for codigo, dados in consolidado_hw.items():
            hw_rows += f"""
            <tr>
                <td style="text-align: center; text-transform: capitalize;">{codigo}</td>
                <td><b>{dados['nome']}</b></td>
                <td style="text-align: center;"><b>{dados['quantidade']}</b></td>
                <td style="text-align: center;">un</td>
                <td style="text-align: right;">{formatar_moeda(dados['preco_unitario'])}</td>
                <td style="text-align: right;"><b>{formatar_moeda(dados['total'])}</b></td>
                <td style="text-align: center; text-transform: capitalize;">{dados['tipo']}</td>
            </tr>
            """
    hw_total = hardware_total_preco(consolidado_hw)
    total_qtd_hw = sum(int(d.get("quantidade", 0)) for d in consolidado_hw.values())
    hw_section = ""
    if consolidado_hw:
        hw_section = f"""
    <div class="section-title">🔧 Ferragens</div>
    <table>
        <thead>
            <tr>
                <th style="text-align: center;">Código</th>
                <th>Item</th>
                <th style="text-align: center;">Qtd</th>
                <th style="text-align: center;">Un</th>
                <th style="text-align: right;">Preço Unit.</th>
                <th style="text-align: right;">Total</th>
                <th style="text-align: center;">Tipo</th>
            </tr>
        </thead>
        <tbody>
            {hw_rows}
        </tbody>
        <tfoot>
            <tr>
                <td colspan="4" style="text-align: right;"><b>Total Ferragens</b></td>
                <td style="text-align: right;"></td>
                <td style="text-align: right;"><b>{formatar_moeda(hw_total)}</b></td>
                <td></td>
            </tr>
        </tfoot>
    </table>
    """

    # Seção de orçamento (opcional)
    orcamento_html = ""
    if include_pricing:
        from ..domain.preferences import TrazoMobPreferencesManager
        prefs = TrazoMobPreferencesManager.get_instance()
        empresa = prefs.get_empresa_config()

        orcamento = calcular_orcamento_cutlist(parts)
        orcamento_por_amb = calcular_orcamento_por_ambiente(parts)

        # Tabela de custos diretos
        custo_rows = ""
        for item in orcamento.itens:
            custo_rows += f"""
            <tr>
                <td>{item.descricao}</td>
                <td style="text-align: center;">{item.quantidade:.3f}</td>
                <td style="text-align: center;">{item.unidade}</td>
                <td style="text-align: right;">{formatar_moeda(item.preco_unitario)}</td>
                <td style="text-align: right;"><b>{formatar_moeda(item.total)}</b></td>
                <td style="text-align: center; text-transform: capitalize;">{item.categoria}</td>
            </tr>
            """

        # Resumo financeiro
        orcamento_html = f"""
        <div class="section-title">💰 Orçamento Detalhado</div>
        <table>
            <thead>
                <tr>
                    <th>Item</th>
                    <th style="text-align: center;">Qtd</th>
                    <th style="text-align: center;">Un</th>
                    <th style="text-align: right;">Preço Unit.</th>
                    <th style="text-align: right;">Total</th>
                    <th style="text-align: center;">Categoria</th>
                </tr>
            </thead>
            <tbody>
                {custo_rows}
            </tbody>
        </table>

        <div class="section-title">📊 Resumo Financeiro</div>
        <table style="max-width: 500px;">
            <tr><td>Custo Direto (materiais + mão de obra)</td><td style="text-align: right;"><b>{formatar_moeda(orcamento.custo_direto)}</b></td></tr>
            <tr><td>Markup ({prefs.get_markup():.0%})</td><td style="text-align: right;">{formatar_moeda(orcamento.markup_valor)}</td></tr>
            <tr><td>Subtotal com Markup</td><td style="text-align: right;"><b>{formatar_moeda(orcamento.subtotal_com_markup)}</b></td></tr>
            <tr><td>Impostos ({prefs.get_impostos_percent():.0%})</td><td style="text-align: right;">{formatar_moeda(orcamento.impostos_valor)}</td></tr>
            <tr><td>Subtotal com Impostos</td><td style="text-align: right;"><b>{formatar_moeda(orcamento.subtotal_com_markup + orcamento.impostos_valor)}</b></td></tr>
            <tr><td>Desconto ({prefs.get_desconto_percent():.0%})</td><td style="text-align: right;">-{formatar_moeda(orcamento.desconto_valor)}</td></tr>
            <tr><td>Frete</td><td style="text-align: right;">{formatar_moeda(orcamento.frete_valor)}</td></tr>
            <tr style="border-top: 2px solid #0284C7; font-size: 14px;">
                <td><b>TOTAL FINAL</b></td>
                <td style="text-align: right;"><b>{formatar_moeda(orcamento.total_final)}</b></td>
            </tr>
        </table>

        <div class="section-title">🏠 Orçamento por Ambiente</div>
        """

        for amb_key, amb_orc in orcamento_por_amb.items():
            orcamento_html += f"""
            <div style="margin-bottom: 16px; padding: 12px; background: #F8FAFC; border-radius: 6px; border-left: 4px solid #16A34A;">
                <div style="font-weight: bold; margin-bottom: 8px;">{amb_key}</div>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; font-size: 12px;">
                    <div>Custo Direto: <b>{formatar_moeda(amb_orc.custo_direto)}</b></div>
                    <div>Com Markup: <b>{formatar_moeda(amb_orc.subtotal_com_markup)}</b></div>
                    <div>Total: <b>{formatar_moeda(amb_orc.total_final)}</b></div>
                </div>
            </div>
            """

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatório Executivo — {project_name}</title>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 30px; color: #1E293B; background: #FFF; }}
    h1 {{ color: #0F172A; margin-bottom: 4px; font-size: 24px; }}
    .subtitle {{ color: #64748B; font-size: 13px; margin-bottom: 24px; }}
    .cards-row {{ display: flex; gap: 16px; margin-bottom: 24px; }}
    .card {{ flex: 1; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px; }}
    .card-title {{ font-size: 11px; font-weight: bold; color: #64748B; text-transform: uppercase; margin-bottom: 6px; }}
    .card-val {{ font-size: 20px; font-weight: bold; color: #0284C7; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 12px; }}
    th {{ background: #F1F5F9; color: #334155; font-weight: bold; text-align: left; padding: 8px 10px; border-bottom: 2px solid #CBD5E1; }}
    td {{ padding: 7px 10px; border-bottom: 1px solid #E2E8F0; }}
    tr:nth-child(even) {{ background: #F8FAFC; }}
    .section-title {{ font-size: 15px; font-weight: bold; color: #0F172A; margin: 20px 0 8px 0; border-left: 4px solid #0284C7; padding-left: 8px; }}
    .footer {{ font-size: 11px; color: #94A3B8; text-align: center; margin-top: 40px; border-top: 1px solid #E2E8F0; padding-top: 12px; }}
    @media print {{
        body {{ margin: 0; padding: 20px; }}
        .no-print {{ display: none; }}
    }}
</style>
</head>
<body>
    <h1>📄 Relatório Executivo & Orçamento Técnico</h1>
    <div class="subtitle">Projeto: <b>{project_name}</b> | Cliente: <b>{client_name}</b> | Sistema IngeTrazo / TrazoMob</div>

    <div class="cards-row">
        <div class="card">
            <div class="card-title">Total de Peças</div>
            <div class="card-val">{total_pecas} un.</div>
        </div>
        <div class="card">
            <div class="card-title">Área Total de Chapa</div>
            <div class="card-val">{total_area_m2:.2f} m²</div>
        </div>
        <div class="card">
            <div class="card-title">Fita de Borda</div>
            <div class="card-val">~{int(round(total_linear_tape_m))} metros</div>
        </div>
        <div class="card">
            <div class="card-title">Itens de Ferragem</div>
            <div class="card-val">{total_qtd_hw} un.</div>
        </div>
    </div>

    <div class="section-title">📊 Resumo de Chapas & Consumo de Materiais</div>
    <table>
        <thead>
            <tr>
                <th>Padrão / Material</th>
                <th style="text-align: center;">Qtd Peças</th>
                <th style="text-align: right;">Área Total</th>
                <th style="text-align: right;">Estimativa de Chapas (2750x1850)</th>
            </tr>
        </thead>
        <tbody>
            {mat_rows}
        </tbody>
    </table>

    <div class="section-title">📋 Lista Completa de Peças para Fabricação</div>
    <table>
        <thead>
            <tr>
                <th style="text-align: center;">#</th>
                <th>Descrição / Peça</th>
                <th style="text-align: center;">Qtd</th>
                <th style="text-align: right;">Medida Final (mm)</th>
                <th style="text-align: right;">Corte Bruto (mm)</th>
                <th>Material</th>
                <th style="text-align: center;">Fitas (C/L)</th>
            </tr>
        </thead>
        <tbody>
            {part_rows}
        </tbody>
    </table>

    {hw_section}

    {orcamento_html}

    <div class="footer">
        Documento gerado automaticamente pelo TrazoMob — Solução Paramétrica para Design de Interiores e Marcenaria.
    </div>
</body>
</html>
"""
    return html


def generate_proposal_html(
    parts: List[dict[str, Any]],
    project_name: str = "Projeto TrazoMob",
    client_name: str = "Cliente",
    client_data: Optional[Dict[str, str]] = None,
    observacoes: str = "",
    filepath: Optional[str | Path] = None,
) -> str:
    """Gera uma proposta comercial completa em HTML (pronta para PDF).

    Inclui:
    - Cabeçalho com dados da empresa e cliente
    - Descrição do projeto e ambientes
    - Orçamento detalhado com preços
    - Condições comerciais e validade
    - Assinatura

    Args:
        parts: Lista de peças da cutlist
        project_name: Nome do projeto
        client_name: Nome do cliente
        client_data: Dict com endereço, telefone, email, cpf_cnpj do cliente
        observacoes: Observações livres para a proposta
        filepath: Se fornecido, salva o arquivo no disco

    Returns:
        HTML da proposta como string
    """
    from datetime import datetime, timedelta
    from ..domain.preferences import TrazoMobPreferencesManager

    prefs = TrazoMobPreferencesManager.get_instance()
    empresa = prefs.get_empresa_config()

    proposta = gerar_proposta_dados(
        parts=parts,
        project_name=project_name,
        client_name=client_name,
        client_data=client_data,
        observacoes=observacoes,
    )

    orc = proposta["orcamento_geral"]
    stats = proposta["estatisticas"]
    data_emissao = proposta["data_emissao"]
    validade = proposta["validade_dias"]
    data_validade = (datetime.now() + timedelta(days=validade)).strftime("%d/%m/%Y")

    # Dados da empresa
    emp_nome = empresa.get("nome", "Marcenaria TrazoMob")
    emp_cnpj = empresa.get("cnpj", "")
    emp_end = empresa.get("endereco", "")
    emp_cid = empresa.get("cidade", "")
    emp_tel = empresa.get("telefone", "")
    emp_email = empresa.get("email", "")

    # Dados do cliente
    cli_end = client_data.get("endereco", "") if client_data else ""
    cli_cid = client_data.get("cidade", "") if client_data else ""
    cli_tel = client_data.get("telefone", "") if client_data else ""
    cli_email = client_data.get("email", "") if client_data else ""
    cli_doc = client_data.get("cpf_cnpj", "") if client_data else ""

    # Itens do orçamento
    item_rows = ""
    for item in orc["itens"]:
        item_rows += f"""
        <tr>
            <td>{item['descricao']}</td>
            <td style="text-align: center;">{item['quantidade']:.3f}</td>
            <td style="text-align: center;">{item['unidade']}</td>
            <td style="text-align: right;">{formatar_moeda(item['preco_unitario'])}</td>
            <td style="text-align: right;"><b>{formatar_moeda(item['total'])}</b></td>
        </tr>
        """

    # Orçamento por ambiente
    amb_rows = ""
    for amb_key, amb_orc in proposta["orcamento_por_ambiente"].items():
        amb_rows += f"""
        <tr>
            <td><b>{amb_key}</b></td>
            <td style="text-align: right;">{formatar_moeda(amb_orc['custo_direto'])}</td>
            <td style="text-align: right;">{formatar_moeda(amb_orc['subtotal_com_markup'])}</td>
            <td style="text-align: right;"><b>{formatar_moeda(amb_orc['total_final'])}</b></td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Proposta Comercial — {project_name}</title>
<style>
    body {{
        font-family: Arial, Helvetica, sans-serif;
        font-size: 11pt;
        color: #1E293B;
        background: #FFF;
        margin: 0;
        padding: 20px;
        line-height: 1.4;
    }}
    .container {{ width: 100%; max-width: 800px; margin: 0 auto; }}
    .header-tbl {{ width: 100%; border-bottom: 2pt solid #0284C7; padding-bottom: 12px; margin-bottom: 16px; }}
    .logo {{ font-size: 18pt; font-weight: bold; color: #0284C7; }}
    .title {{ font-size: 15pt; font-weight: bold; color: #0F172A; margin: 14px 0; text-align: center; }}
    .info-tbl {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; }}
    .info-box {{ background: #F8FAFC; border: 1pt solid #CBD5E1; padding: 10px; font-size: 10pt; vertical-align: top; width: 48%; }}
    .info-box h3 {{ margin: 0 0 8px 0; font-size: 10pt; color: #0284C7; text-transform: uppercase; border-bottom: 1pt solid #E2E8F0; padding-bottom: 4px; }}
    .stats-tbl {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; }}
    .stats-card {{ background: #F8FAFC; border: 1pt solid #CBD5E1; padding: 8px; text-align: center; width: 25%; }}
    .stats-num {{ font-size: 14pt; font-weight: bold; color: #0284C7; }}
    .stats-lbl {{ font-size: 9pt; color: #64748B; }}
    table.data-tbl {{ width: 100%; border-collapse: collapse; margin: 12px 0 20px 0; font-size: 10pt; }}
    table.data-tbl th {{ background: #0284C7; color: #FFFFFF; font-weight: bold; text-align: left; padding: 6pt 8pt; }}
    table.data-tbl td {{ padding: 5pt 8pt; border-bottom: 1pt solid #E2E8F0; }}
    .totals-tbl {{ width: 50%; border-collapse: collapse; margin-left: auto; font-size: 10pt; }}
    .totals-tbl td {{ padding: 4pt 8pt; }}
    .totals-tbl tr.final td {{ border-top: 2pt solid #0284C7; font-weight: bold; font-size: 12pt; color: #0F172A; }}
    .section-h2 {{ font-size: 12pt; font-weight: bold; color: #0F172A; border-left: 3pt solid #0284C7; padding-left: 8px; margin: 16px 0 8px 0; }}
    .notes {{ background: #FEF3C7; border: 1pt solid #FCD34D; padding: 10px; margin: 16px 0; font-size: 9.5pt; line-height: 1.5; }}
    .sig-tbl {{ width: 100%; border-collapse: collapse; margin-top: 40px; }}
    .sig-td {{ width: 45%; text-align: center; vertical-align: bottom; }}
    .sig-line {{ border-top: 1pt solid #334155; margin-top: 40px; padding-top: 6px; font-size: 10pt; font-weight: bold; }}
    .validade {{ text-align: right; color: #DC2626; font-weight: bold; font-size: 10pt; margin: 12px 0; }}
    .print-btn {{ position: fixed; top: 16px; right: 16px; padding: 8px 16px; background: #0284C7; color: white; border: none; cursor: pointer; font-weight: bold; }}
    @media print {{
        .print-btn {{ display: none; }}
        body {{ padding: 0; }}
    }}
</style>
</head>
<body>
    <button class="print-btn" onclick="window.print()">🖨️ Imprimir / Salvar PDF</button>

    <div class="container">
        <table class="header-tbl" cellpadding="0" cellspacing="0">
            <tr>
                <td style="vertical-align: top;">
                    <div class="logo">{emp_nome}</div>
                    <div style="font-size: 9.5pt; color: #64748B; margin-top: 4px;">
                        {emp_end} — {emp_cid}<br>
                        CNPJ: {emp_cnpj} | Tel: {emp_tel} | Email: {emp_email}
                    </div>
                </td>
                <td style="text-align: right; vertical-align: top;">
                    <div style="font-size: 9.5pt; color: #64748B;">PROPOSTA COMERCIAL</div>
                    <div style="font-size: 14pt; font-weight: bold; color: #0F172A; margin-top: 4px;">Nº {datetime.now().strftime("%Y%m%d%H%M")}</div>
                </td>
            </tr>
        </table>

        <div class="title">Proposta para <span style="color: #0284C7;">{client_name}</span> — {project_name}</div>

        <table class="info-tbl" cellpadding="0" cellspacing="0">
            <tr>
                <td class="info-box">
                    <h3>Emitente / Marcenaria</h3>
                    <b>Empresa:</b> {emp_nome}<br>
                    <b>CNPJ:</b> {emp_cnpj}<br>
                    <b>Endereço:</b> {emp_end}<br>
                    <b>Cidade:</b> {emp_cid}<br>
                    <b>Telefone:</b> {emp_tel}<br>
                    <b>E-mail:</b> {emp_email}
                </td>
                <td style="width: 4%;"></td>
                <td class="info-box">
                    <h3>Cliente</h3>
                    <b>Nome:</b> {client_name}<br>
                    <b>CPF/CNPJ:</b> {cli_doc}<br>
                    <b>Endereço:</b> {cli_end}<br>
                    <b>Cidade:</b> {cli_cid}<br>
                    <b>Telefone:</b> {cli_tel}<br>
                    <b>E-mail:</b> {cli_email}
                </td>
            </tr>
        </table>

        <table class="stats-tbl" cellpadding="4" cellspacing="4">
            <tr>
                <td class="stats-card">
                    <div class="stats-num" style="color: #0284C7;">{stats['total_pecas']}</div>
                    <div class="stats-lbl">Total de Peças</div>
                </td>
                <td class="stats-card">
                    <div class="stats-num" style="color: #16A34A;">{stats['total_area_m2']:.1f} m²</div>
                    <div class="stats-lbl">Área MDF / Painel</div>
                </td>
                <td class="stats-card">
                    <div class="stats-num" style="color: #7C3AED;">{stats['total_fita_m']:.0f} m</div>
                    <div class="stats-lbl">Fita de Borda</div>
                </td>
                <td class="stats-card">
                    <div class="stats-num" style="color: #DC2626;">{stats['num_ambientes']}</div>
                    <div class="stats-lbl">Ambientes</div>
                </td>
            </tr>
        </table>

        <div>
            <div class="section-h2">📋 Descrição do Projeto</div>
            <p style="color: #475569; font-size: 10pt; margin: 4px 0 14px 0;">
                Fornecimento e instalação de mobiliário planejado para o projeto <b>{project_name}</b>,
                compreendendo <b>{stats['total_pecas']} peças</b> distribuídas em <b>{stats['num_ambientes']} ambiente(s)</b>,
                totalizando <b>{stats['total_area_m2']:.2f} m²</b> de chapas processadas.
                Inclui corte, usinagens de montagem, fitas de borda nas faces aparentes, ferragens completas e instalação.
            </p>
        </div>

        <div>
            <div class="section-h2">🏠 Resumo por Ambiente</div>
            <table class="data-tbl">
                <thead>
                    <tr>
                        <th>Ambiente / Cômodo</th>
                        <th style="text-align: right;">Custo Direto</th>
                        <th style="text-align: right;">Subtotal</th>
                        <th style="text-align: right;">Valor de Venda</th>
                    </tr>
                </thead>
                <tbody>
                    {amb_rows}
                </tbody>
            </table>
        </div>

        <div>
            <div class="section-h2">💰 Composição de Itens do Projeto</div>
            <table class="data-tbl">
                <thead>
                    <tr>
                        <th>Item / Descrição</th>
                        <th style="text-align: center;">Quantidade</th>
                        <th style="text-align: center;">Un.</th>
                        <th style="text-align: right;">Preço Unit.</th>
                        <th style="text-align: right;">Total</th>
                    </tr>
                </thead>
                <tbody>
                    {item_rows}
                </tbody>
            </table>
        </div>

        <div>
            <div class="section-h2">📊 Resumo Financeiro & Condições</div>
            <table class="totals-tbl">
                <tr><td>Custo Direto de Produção:</td><td style="text-align: right;">{formatar_moeda(orc['custo_direto'])}</td></tr>
                <tr><td>Margem / Markup ({prefs.get_markup():.0%}):</td><td style="text-align: right;">{formatar_moeda(orc['markup_valor'])}</td></tr>
                <tr><td><b>Subtotal com Markup:</b></td><td style="text-align: right;"><b>{formatar_moeda(orc['subtotal_com_markup'])}</b></td></tr>
                <tr><td>Impostos ({prefs.get_impostos_percent():.0%}):</td><td style="text-align: right;">{formatar_moeda(orc['impostos_valor'])}</td></tr>
                <tr><td>Desconto Comercial ({prefs.get_desconto_percent():.0%}):</td><td style="text-align: right; color: #16A34A;">-{formatar_moeda(orc['desconto_valor'])}</td></tr>
                <tr><td>Frete / Logística:</td><td style="text-align: right;">{formatar_moeda(orc['frete_valor'])}</td></tr>
                <tr class="final"><td>TOTAL FINAL:</td><td style="text-align: right;">{formatar_moeda(orc['total_final'])}</td></tr>
            </table>
        </div>

        <div class="validade">
            Proposta válida até: {data_validade} (Emitida em {data_emissao})
        </div>

        <div class="notes">
            <b>Observações & Condições de Fornecimento:</b><br>
            {observacoes or "• Valores incluem matéria-prima, usinagens, ferragens e montagem no local.<br>• Condições de pagamento: Entrada 50% e saldo na entrega/instalação.<br>• Garantia legal de 12 meses contra defeitos de fabricação."}
        </div>

        <table class="sig-tbl" cellpadding="0" cellspacing="0">
            <tr>
                <td class="sig-td">
                    <div class="sig-line">{emp_nome}</div>
                    <div style="font-size: 9pt; color: #64748B; margin-top: 4px;">Responsável Técnico / Marcenaria</div>
                </td>
                <td style="width: 10%;"></td>
                <td class="sig-td">
                    <div class="sig-line">{client_name}</div>
                    <div style="font-size: 9pt; color: #64748B; margin-top: 4px;">Aceite do Cliente</div>
                </td>
            </tr>
        </table>

        <div style="text-align: center; margin-top: 30px; font-size: 9pt; color: #94A3B8; border-top: 1pt solid #E2E8F0; padding-top: 10px;">
            Documento gerado pelo TrazoMob — IngeTrazo | www.ingetrazo.com.br
        </div>
    </div>
</body>
</html>
"""

    if filepath:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

    return html


def generate_proposal_pdf(
    parts: List[dict[str, Any]],
    filepath: str | Path,
    project_name: str = "Projeto TrazoMob",
    client_name: str = "Cliente",
    client_data: Optional[Dict[str, str]] = None,
    observacoes: str = "",
) -> bool:
    """Gera proposta em PDF nativamente via PySide6/Qt (ou weasyprint se disponível)."""
    html = generate_proposal_html(
        parts=parts,
        project_name=project_name,
        client_name=client_name,
        client_data=client_data,
        observacoes=observacoes,
    )

    # 1. Tenta via WeasyPrint se instalado
    try:
        from weasyprint import HTML
        HTML(string=html).write_pdf(str(filepath))
        return True
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("WeasyPrint falhou; usando fallback nativo: %s", exc)

    # 2. Geração nativa e robusta via PySide6 (sem dependências externas)
    try:
        from PySide6.QtGui import QTextDocument, QPageLayout, QPageSize
        from PySide6.QtCore import QMarginsF
        from PySide6.QtPrintSupport import QPrinter

        printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(str(filepath))
        layout = QPageLayout(
            QPageSize(QPageSize.A4),
            QPageLayout.Portrait,
            QMarginsF(12.0, 12.0, 12.0, 12.0)
        )
        printer.setPageLayout(layout)

        doc = QTextDocument()
        page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
        doc.setTextWidth(page_rect.width())
        doc.setHtml(html)
        doc.print_(printer)
        return True
    except Exception as e:
        logger.error("Erro ao gerar PDF nativo: %s", e)
        return False
