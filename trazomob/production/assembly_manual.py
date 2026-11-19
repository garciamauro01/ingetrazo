# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Gerador de **Manual de Montagem** a partir da lista de peças (cutlist).

Cada peça da cutlist já carrega ``operacoes``, ``_module_key``,
``module_hardware``, ``ambiente`` e ``pavimento`` (veja ``production.parts``).
Este módulo agrupa as peças por módulo, consolida as ferragens de cada módulo
(uma contagem por módulo, não uma por peça) e produz um documento HTML pronto
para impressão/PDF, reutilizando o estilo visual de ``production.report``.
"""
from __future__ import annotations

from typing import Any

from ..domain.hardware import consolidate_hardware, deserialize_hardware


def _op_instrucao(op: dict[str, Any]) -> str:
    """Converte uma operação de usinagem numa instrução de montagem legível."""
    tipo = str(op.get("tipo", "usinagem")).lower()
    face = op.get("face") or "peça"
    desc = op.get("descricao") or ""
    x = op.get("x")
    y = op.get("y")
    d = op.get("diametro")
    pos = ""
    if x is not None and y is not None:
        pos = f" em (x={float(x):.0f} mm, y={float(y):.0f} mm)"
    if d is not None:
        pos += f" Ø{float(d):.0f} mm"

    if tipo == "furo":
        verb = f"Fure a face {face}{pos}"
    elif tipo in ("rasgo", "rebaixo", "canal"):
        w = op.get("largura")
        c = op.get("comprimento")
        dim = ""
        if w is not None and c is not None:
            dim = f" {float(w):.0f}x{float(c):.0f} mm"
        verb = f"Faça um {tipo} na face {face}{dim}{pos}"
    elif tipo == "fresa":
        verb = f"Frese a face {face}{pos}"
    else:
        verb = f"Usine a face {face} ({tipo}){pos}"

    if desc:
        verb += f" — {desc}"
    return verb + "."


def _fitas_texto(p: dict[str, Any]) -> str:
    fitas = []
    if p.get("fita_c1"): fitas.append("C1")
    if p.get("fita_c2"): fitas.append("C2")
    if p.get("fita_l1"): fitas.append("L1")
    if p.get("fita_l2"): fitas.append("L2")
    esp = p.get("espessura_fita", 0.45)
    if not fitas:
        return "Sem fita de borda"
    return f"Fita {', '.join(fitas)} ({esp:.2f} mm)"


def _agrupar_por_modulo(
    parts: list[dict[str, Any]],
) -> tuple[list[tuple[Any, list[dict[str, Any]], list[dict[str, Any]]]], list[dict[str, Any]]]:
    """Agrupa peças por módulo (_module_key), consolidando ferragens por módulo.

    Retorna ``(modulos, avulsas)`` onde ``modulos`` é uma lista de
    ``(module_key, pecas_do_modulo, ferragens_consolidadas_dict)``.
    """
    modulos: dict[Any, list[dict[str, Any]]] = {}
    mod_hw: dict[Any, list[dict[str, Any]]] = {}
    avulsas: list[dict[str, Any]] = []
    seen_mod_keys: set = set()

    for p in parts:
        mk = p.get("_module_key")
        if mk is None:
            avulsas.append(p)
            continue
        if mk not in seen_mod_keys:
            seen_mod_keys.add(mk)
            modulos[mk] = []
            mod_hw[mk] = deserialize_hardware(p.get("module_hardware") or [])
        modulos[mk].append(p)

    resultado = []
    for mk, pecas in modulos.items():
        hw_entries = [(mk, deserialize_hardware(pecas[0].get("module_hardware") or []))]
        consolidado = consolidate_hardware(hw_entries)
        resultado.append((mk, pecas, consolidado))
    return resultado, avulsas


def generate_assembly_manual_html(
    parts: list[dict[str, Any]],
    project_name: str = "Projeto TrazoMob",
) -> str:
    """Gera o manual de montagem em HTML a partir da lista de peças."""
    total_pecas = sum(p.get("quantidade", 1) for p in parts)
    modulos, avulsas = _agrupar_por_modulo(parts)

    total_hw = 0
    for (_mk, _pecas, consolidado) in modulos:
        total_hw += sum(int(d.get("quantidade", 0)) for d in consolidado.values())

    # Cabeçalho e resumo
    mod_rows = ""
    for indice, (mk, pecas, consolidado) in enumerate(modulos, start=1):
        primeiro = pecas[0]
        ambiente = primeiro.get("ambiente") or "—"
        pavimento = primeiro.get("pavimento") or "—"

        hw_rows = ""
        if consolidado:
            for codigo, dados in consolidado.items():
                hw_rows += f"""
                <tr>
                    <td style="text-align: center; text-transform: capitalize;">{codigo}</td>
                    <td><b>{dados['nome']}</b></td>
                    <td style="text-align: center;"><b>{dados['quantidade']}</b></td>
                    <td style="text-align: center;">un</td>
                    <td style="text-align: center; text-transform: capitalize;">{dados.get('tipo','')}</td>
                </tr>
                """

        peca_rows = ""
        for i, p in enumerate(pecas, start=1):
            qtd = p.get("quantidade", 1)
            comp = f"{float(p.get('comprimento', 0.0)):.0f}"
            larg = f"{float(p.get('largura', 0.0)):.0f}"
            esp = f"{float(p.get('espessura', 15.0)):.0f}"
            comp_c = f"{float(p.get('comprimento_corte', p.get('comprimento', 0.0))):.0f}"
            larg_c = f"{float(p.get('largura_corte', p.get('largura', 0.0))):.0f}"
            ops = p.get("operacoes", []) or []
            ops_html = ""
            if ops:
                itens = "".join(f"<li>{_op_instrucao(o)}</li>" for o in ops)
                ops_html = f'<div style="margin-top:4px;"><b>Usinagens:</b><ul style="margin:4px 0 0 0; padding-left:16px; font-size:11px; color:#475569;">{itens}</ul></div>'

            peca_rows += f"""
            <tr>
                <td style="text-align: center;">{i}</td>
                <td><b>{p.get('nome', 'Peça')}</b></td>
                <td style="text-align: center;"><b>{qtd}</b></td>
                <td style="text-align: right;">{comp} x {larg} x {esp}</td>
                <td style="text-align: right; color: #475569;">{comp_c} x {larg_c}</td>
                <td>{p.get('material', '')}</td>
                <td style="text-align: center; font-size: 11px;">{_fitas_texto(p)}</td>
                <td style="font-size: 11px;">{ops_html if ops_html else "—"}</td>
            </tr>
            """

        mod_rows += f"""
        <div style="margin-bottom: 26px; border: 1px solid #E2E8F0; border-radius: 8px; overflow: hidden;">
            <div style="background: #F8FAFC; padding: 10px 14px; border-bottom: 1px solid #E2E8F0;">
                <div style="font-weight: bold; color: #0F172A;">Módulo {indice}</div>
                <div style="font-size: 12px; color: #64748B;">
                    🏠 Ambiente: <b>{ambiente}</b> &nbsp;|&nbsp; 🏢 Pavimento: <b>{pavimento}</b> &nbsp;|&nbsp;
                    📦 {len(pecas)} tipo(s) de peça &nbsp;|&nbsp; 🔧 {sum(int(d.get('quantidade',0)) for d in consolidado.values())} ferragem(ns)
                </div>
            </div>
            <table style="width: 100%; font-size: 12px;">
                <thead>
                    <tr style="background: #F1F5F9;">
                        <th style="text-align: center; padding: 6px 8px;">#</th>
                        <th style="padding: 6px 8px;">Peça</th>
                        <th style="text-align: center; padding: 6px 8px;">Qtd</th>
                        <th style="text-align: right; padding: 6px 8px;">Medida Final (mm)</th>
                        <th style="text-align: right; padding: 6px 8px;">Medida de Corte (mm)</th>
                        <th style="padding: 6px 8px;">Material</th>
                        <th style="text-align: center; padding: 6px 8px;">Fita de Borda</th>
                        <th style="padding: 6px 8px;">Usinagens / Montagem</th>
                    </tr>
                </thead>
                <tbody>
                    {peca_rows}
                </tbody>
            </table>
            {f'''
            <div style="padding: 8px 14px; background: #FFF7ED; border-top: 1px solid #FDBA74;">
                <div style="font-weight: bold; color: #92400e; font-size: 12px; margin-bottom: 4px;">🔧 Ferragens deste módulo</div>
                <table style="width: 100%; font-size: 11px;">
                    <thead><tr style="background: #FEF3C7;">
                        <th style="text-align: center; padding: 4px 6px;">Código</th>
                        <th style="padding: 4px 6px;">Item</th>
                        <th style="text-align: center; padding: 4px 6px;">Qtd</th>
                        <th style="text-align: center; padding: 4px 6px;">Un</th>
                        <th style="text-align: center; padding: 4px 6px;">Tipo</th>
                    </tr></thead>
                    <tbody>{hw_rows}</tbody>
                </table>
            </div>
            ''' if consolidado else ''
            }
        </div>
        """

    # Peças avulsas (sem módulo)
    avulsa_rows = ""
    if avulsas:
        for i, p in enumerate(avulsas, start=1):
            qtd = p.get("quantidade", 1)
            comp = f"{float(p.get('comprimento', 0.0)):.0f}"
            larg = f"{float(p.get('largura', 0.0)):.0f}"
            esp = f"{float(p.get('espessura', 15.0)):.0f}"
            comp_c = f"{float(p.get('comprimento_corte', p.get('comprimento', 0.0))):.0f}"
            larg_c = f"{float(p.get('largura_corte', p.get('largura', 0.0))):.0f}"
            avulsa_rows += f"""
            <tr>
                <td style="text-align: center;">{i}</td>
                <td><b>{p.get('nome', 'Peça')}</b></td>
                <td style="text-align: center;"><b>{qtd}</b></td>
                <td style="text-align: right;">{comp} x {larg} x {esp}</td>
                <td style="text-align: right; color: #475569;">{comp_c} x {larg_c}</td>
                <td>{p.get('material', '')}</td>
                <td style="text-align: center; font-size: 11px;">{_fitas_texto(p)}</td>
                <td style="font-size: 11px;">—</td>
            </tr>
            """

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Manual de Montagem — {project_name}</title>
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
    <h1>🛠️ Manual de Montagem</h1>
    <div class="subtitle">Projeto: <b>{project_name}</b> | Sistema IngeTrazo / TrazoMob</div>

    <div class="cards-row">
        <div class="card">
            <div class="card-title">Módulos</div>
            <div class="card-val">{len(modulos)}</div>
        </div>
        <div class="card">
            <div class="card-title">Tipos de Peça</div>
            <div class="card-val">{len(parts)}</div>
        </div>
        <div class="card">
            <div class="card-title">Peças (total)</div>
            <div class="card-val">{total_pecas} un.</div>
        </div>
        <div class="card">
            <div class="card-title">Ferragens</div>
            <div class="card-val">{total_hw} un.</div>
        </div>
    </div>

    <div class="section-title">📦 Módulos e Peças para Montagem</div>
    {mod_rows}

    {f'''
    <div class="section-title">🧩 Peças Avulsas (sem módulo)</div>
    <table>
        <thead>
            <tr style="background: #F1F5F9;">
                <th style="text-align: center; padding: 6px 8px;">#</th>
                <th style="padding: 6px 8px;">Peça</th>
                <th style="text-align: center; padding: 6px 8px;">Qtd</th>
                <th style="text-align: right; padding: 6px 8px;">Medida Final (mm)</th>
                <th style="text-align: right; padding: 6px 8px;">Medida de Corte (mm)</th>
                <th style="padding: 6px 8px;">Material</th>
                <th style="text-align: center; padding: 6px 8px;">Fita de Borda</th>
                <th style="padding: 6px 8px;">Usinagens / Montagem</th>
            </tr>
        </thead>
        <tbody>{avulsa_rows}</tbody>
    </table>
    ''' if avulsas else ''
    }

    <div class="footer">
        Manual de Montagem gerado automaticamente pelo TrazoMob — IngeTrazo.
        Conferir medidas de corte e usinagens antes da fabricação.
    </div>
</body>
</html>"""
    return html


def save_assembly_manual_html(
    parts: list[dict[str, Any]],
    filepath: str,
    project_name: str = "Projeto TrazoMob",
) -> bool:
    """Gera o manual de montagem e grava em ``filepath``. Retorna True se salvou."""
    try:
        html = generate_assembly_manual_html(parts, project_name=project_name)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        return True
    except OSError:
        return False
