# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Gerador de Relatório Executivo HTML Profissional para TrazoMob com quebra por Ambiente/Pavimento."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def generate_executive_html_report(
    parts: List[Dict[str, Any]],
    filepath: str | Path,
    project_name: str = "Projeto TrazoMob",
    group_by_ambiente: bool = True,
) -> None:
    """Gera um relatório executivo HTML elegante, responsivo e pronto para impressão/PDF."""
    now_str = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")

    # Mapeamento e agrupamento
    total_pecas = sum(p.get("quantidade", 1) for p in parts)
    total_area_m2 = sum(
        (p["comprimento"] / 1000.0) * (p["largura"] / 1000.0) * p.get("quantidade", 1)
        for p in parts
    )

    # Agrupa peças por Ambiente e Pavimento
    groups: Dict[str, List[Dict[str, Any]]] = {}
    materiais_set = set()
    total_fita_m = 0.0

    for p in parts:
        qtd = p.get("quantidade", 1)
        c = p["comprimento"]
        l = p["largura"]
        esp_fita = float(p.get("espessura_fita") or 0.45)
        # Metragem linear de fita aplicada nesta peça
        comp_m = c / 1000.0
        larg_m = l / 1000.0
        fita_peca = 0.0
        if p.get("fita_c1"):
            fita_peca += comp_m
        if p.get("fita_c2"):
            fita_peca += comp_m
        if p.get("fita_l1"):
            fita_peca += larg_m
        if p.get("fita_l2"):
            fita_peca += larg_m
        total_fita_m += fita_peca * qtd

        mat = p.get("material", "MDF Branco TX")
        esp = p.get("espessura", 15.0)
        materiais_set.add(f"{mat} {esp:.0f}mm")

        if group_by_ambiente:
            amb = p.get("ambiente") or "Ambiente Geral"
            pav = p.get("pavimento") or "Térreo"
            key = f"📍 {amb} ({pav})" if pav else f"📍 {amb}"
        else:
            key = "📋 Lista Consolidada de Peças"

        if key not in groups:
            groups[key] = []
        groups[key].append(p)

    chapas_estimadas = max(1, int(round((total_area_m2 / (2.75 * 1.85)) * 1.25))) if total_area_m2 > 0 else 0

    # Renderiza HTML
    html_lines = [
        "<!DOCTYPE html>",
        "<html lang='pt-BR'>",
        "<head>",
        "  <meta charset='UTF-8'>",
        f"  <title>Relatório Executivo — {project_name}</title>",
        "  <style>",
        "    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; margin: 0; padding: 24px; background: #f8fafc; }",
        "    .container { max-width: 1050px; margin: 0 auto; background: #ffffff; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); padding: 32px; }",
        "    .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #e2e8f0; padding-bottom: 16px; margin-bottom: 24px; }",
        "    .title { font-size: 24px; font-weight: bold; color: #0f172a; margin: 0; }",
        "    .subtitle { font-size: 13px; color: #64748b; margin-top: 4px; }",
        "    .badges { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 28px; }",
        "    .card { background: #f1f5f9; border-radius: 6px; padding: 14px 18px; border-left: 4px solid #0284c7; }",
        "    .card.green { border-left-color: #16a34a; }",
        "    .card.red { border-left-color: #dc2626; }",
        "    .card.purple { border-left-color: #7c3aed; }",
        "    .card-title { font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: bold; }",
        "    .card-value { font-size: 20px; font-weight: bold; color: #0f172a; margin-top: 4px; }",
        "    .section-title { font-size: 16px; font-weight: bold; color: #1e293b; margin: 24px 0 12px 0; padding-bottom: 6px; border-bottom: 1px solid #cbd5e1; display: flex; align-items: center; justify-content: space-between; }",
        "    table { width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 24px; }",
        "    th { background: #f8fafc; color: #475569; font-weight: 600; text-align: left; padding: 8px 10px; border-bottom: 2px solid #e2e8f0; }",
        "    td { padding: 8px 10px; border-bottom: 1px solid #f1f5f9; vertical-align: middle; }",
        "    tr:hover { background: #f8fafc; }",
        "    .text-right { text-align: right; }",
        "    .text-center { text-align: center; }",
        "    .tag { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; }",
        "    .tag-cut { background: #ecfdf5; color: #059669; }",
        "    .tag-tape { background: #fee2e2; color: #dc2626; }",
        "    @media print {",
        "      body { background: #ffffff; padding: 0; }",
        "      .container { box-shadow: none; padding: 0; }",
        "      .page-break { page-break-before: always; }",
        "    }",
        "  </style>",
        "</head>",
        "<body>",
        "  <div class='container'>",
        "    <div class='header'>",
        "      <div>",
        "        <h1 class='title'>🪵 TrazoMob — Relatório Executivo</h1>",
        f"        <div class='subtitle'>{project_name} • Gerado em {now_str}</div>",
        "      </div>",
        "      <div>",
        "        <button onclick='window.print()' style='padding: 8px 16px; background: #0284c7; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer;'>🖨️ Imprimir / Salvar PDF</button>",
        "      </div>",
        "    </div>",
        "    <div class='badges'>",
        f"      <div class='card'><div class='card-title'>Total de Peças</div><div class='card-value'>📦 {total_pecas}</div></div>",
        f"      <div class='card green'><div class='card-title'>Área de MDF</div><div class='card-value'>📐 {total_area_m2:.2f} m²</div></div>",
        f"      <div class='card purple'><div class='card-title'>Est. Chapas (2.75x1.85m)</div><div class='card-value'>🪵 ~{chapas_estimadas} un</div></div>",
        f"      <div class='card red'><div class='card-title'>Fita de Borda</div><div class='card-value'>📏 {total_fita_m:.1f} m</div></div>",
        "    </div>",
    ]

    # Itera por grupos (ambientes)
    for g_idx, (group_name, group_parts) in enumerate(groups.items()):
        page_break_cls = " page-break" if g_idx > 0 else ""
        g_pecas = sum(p.get("quantidade", 1) for p in group_parts)
        g_m2 = sum(
            (p["comprimento"] / 1000.0) * (p["largura"] / 1000.0) * p.get("quantidade", 1)
            for p in group_parts
        )

        html_lines.append(f"    <div class='{page_break_cls}'>")
        html_lines.append(
            f"      <div class='section-title'><span>{group_name}</span><span style='font-size: 12px; color: #64748b; font-weight: normal;'>{g_pecas} peças • {g_m2:.2f} m²</span></div>"
        )
        html_lines.append("      <table>")
        html_lines.append("        <thead>")
        html_lines.append("          <tr>")
        html_lines.append("            <th class='text-center' style='width: 45px;'>Qtd</th>")
        html_lines.append("            <th>Descrição da Peça</th>")
        html_lines.append("            <th>Material / Espessura</th>")
        html_lines.append("            <th class='text-right'>Final (mm)</th>")
        html_lines.append("            <th class='text-right'>Corte Bruto (mm)</th>")
        html_lines.append("            <th class='text-center'>Fitas de Borda</th>")
        html_lines.append("            <th>Usinagens / Furos</th>")
        html_lines.append("          </tr>")
        html_lines.append("        </thead>")
        html_lines.append("        <tbody>")

        for p in group_parts:
            qtd = p.get("quantidade", 1)
            comp = p["comprimento"]
            larg = p["largura"]
            esp = p["espessura"]
            comp_c = p.get("comprimento_corte", comp)
            larg_c = p.get("largura_corte", larg)
            nome = p["nome"]
            mat = p["material"]
            esp_f = float(p.get("espessura_fita") or 0.45)

            # Resumo de fitas
            fitas_list = []
            if p.get("fita_c1"):
                fitas_list.append("C1")
            if p.get("fita_c2"):
                fitas_list.append("C2")
            if p.get("fita_l1"):
                fitas_list.append("L1")
            if p.get("fita_l2"):
                fitas_list.append("L2")

            if fitas_list:
                fita_str = f"<span class='tag tag-tape'>{'+'.join(fitas_list)} ({esp_f:.2f}mm)</span>"
            else:
                fita_str = "<span style='color: #94a3b8;'>-</span>"

            ops = p.get("operacoes", [])
            ops_desc = ", ".join(o.get("descricao", "") for o in ops if o.get("descricao")) if ops else "-"

            html_lines.append("          <tr>")
            html_lines.append(f"            <td class='text-center'><b>{qtd}</b></td>")
            html_lines.append(f"            <td><b>{nome}</b></td>")
            html_lines.append(f"            <td>{mat} ({esp:.0f}mm)</td>")
            html_lines.append(f"            <td class='text-right'>{comp:.1f} × {larg:.1f}</td>")
            html_lines.append(f"            <td class='text-right'><span class='tag tag-cut'>{comp_c:.1f} × {larg_c:.1f}</span></td>")
            html_lines.append(f"            <td class='text-center'>{fita_str}</td>")
            html_lines.append(f"            <td style='color: #475569;'>{ops_desc}</td>")
            html_lines.append("          </tr>")

        html_lines.append("        </tbody>")
        html_lines.append("      </table>")
        html_lines.append("    </div>")

    html_lines.append("  </div>")
    html_lines.append("</body>")
    html_lines.append("</html>")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(html_lines))

