# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Codificador **Code 128** nativo para as etiquetas técnicas de produção.

Implementa a simbologia Code 128 de verdade (conjuntos A/B/C, dígito
verificador módulo 103 e padrões de barra oficiais), de forma que o código de
barras impresso nas etiquetas seja **escaneável** por leitores de fábrica — o
desenho anterior em ``labels.py`` era apenas decorativo (derivado de um hash)
e não podia ser lido.

Sem dependências externas: devolve a sequência de módulos (``"1"`` = barra,
``"0"`` = espaço) que a interface pinta com ``QPainter``.
"""
from __future__ import annotations

#: Padrões oficiais Code 128 (larguras alternadas barra/espaço) para os 107
#: símbolos (0..102 de dados, 103/104/105 = Start A/B/C, 106 = Stop).
#: Cada string tem 6 dígitos (soma 11 módulos); o Stop tem 7 dígitos (soma 13).
_CODE128_PATTERNS: tuple[str, ...] = (
    "212222", "222122", "222221", "121223", "121322", "131222", "122213",
    "122312", "132212", "221213", "221312", "231212", "112232", "122132",
    "122231", "113222", "123122", "123221", "223211", "221132", "221231",
    "213212", "223112", "312131", "311222", "321122", "321221", "312212",
    "322112", "322211", "212123", "212321", "232121", "111323", "131123",
    "131321", "112313", "132113", "132311", "211313", "231113", "231311",
    "112133", "112331", "132131", "113123", "113321", "133121", "313121",
    "211331", "231131", "213113", "213311", "213131", "311123", "311321",
    "331121", "312113", "312311", "332111", "314111", "221411", "431111",
    "111224", "111422", "121124", "121421", "141122", "141221", "112214",
    "112412", "122114", "122411", "142112", "142211", "241211", "221114",
    "413111", "241112", "134111", "111242", "121142", "121241", "114212",
    "124112", "124211", "411212", "421112", "421211", "212141", "214121",
    "412121", "111143", "111341", "131141", "114113", "114311", "411113",
    "411311", "113141", "114131", "311141", "411131", "211412", "211214",
    "211232", "2331112",
)

_START_B = 104
_STOP = 106

#: Faixa de caracteres representável no conjunto B (imprimíveis ASCII).
_CODE_B_MIN = 32
_CODE_B_MAX = 126


def _sanitize(text: str) -> str:
    """Remove caracteres não representáveis no conjunto B (mantém 32..126)."""
    return "".join(ch if _CODE_B_MIN <= ord(ch) <= _CODE_B_MAX else " " for ch in str(text or ""))


def code128_values(text: str) -> list[int]:
    """Devolve a lista de valores Code 128 (Start B + dados + checksum + Stop).

    O dígito verificador é o módulo 103 ponderado: ``(start + Σ v_i·i) % 103``,
    com ``i`` começando em 1 no primeiro caractere de dados.
    """
    data = _sanitize(text)
    if not data:
        data = " "
    valores = [_START_B]
    for ch in data:
        valores.append(ord(ch) - _CODE_B_MIN)
    checksum = valores[0]
    for i, v in enumerate(valores[1:], start=1):
        checksum += v * i
    valores.append(checksum % 103)
    valores.append(_STOP)
    return valores


def code128_modules(text: str) -> str:
    """Devolve a sequência de módulos (``"1"`` barra / ``"0"`` espaço) do código."""
    bits: list[str] = []
    for valor in code128_values(text):
        padrao = _CODE128_PATTERNS[valor]
        barra = True
        for largura_txt in padrao:
            bits.append(("1" if barra else "0") * int(largura_txt))
            barra = not barra
    return "".join(bits)


def code128_bar_widths(text: str) -> list[tuple[bool, int]]:
    """Devolve ``[(é_barra, largura_em_módulos), ...]`` para pintura direta."""
    barras: list[tuple[bool, int]] = []
    for valor in code128_values(text):
        padrao = _CODE128_PATTERNS[valor]
        barra = True
        for largura_txt in padrao:
            barras.append((barra, int(largura_txt)))
            barra = not barra
    return barras
