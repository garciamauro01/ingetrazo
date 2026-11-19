# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Gerador de **QR Code** nativo (modo byte, correção M) para as etiquetas.

Implementação enxuta e sem dependências externas, cobrindo as versões 1 a 6
(até 106 bytes — mais que suficiente para a carga útil de uma etiqueta de
marcenaria). Segue a norma ISO/IEC 18004: modo byte, nível de correção ``M``,
Reed-Solomon sobre GF(256), máscaras 0-7 com seleção por penalidade e
informação de formato com BCH(15,5).

Devolve a matriz de módulos (``True`` = módulo escuro), pronta para ser
desenhada com ``QPainter`` — sem ``qrcode``/``segno``/PIL instalados.
"""
from __future__ import annotations

from typing import List, Optional

# ── Aritmética de Galois GF(256), polinômio primitivo 0x11D ──────────────────
_EXP: List[int] = [0] * 512
_LOG: List[int] = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def _poly_mul(p: List[int], q: List[int]) -> List[int]:
    """Multiplica dois polinômios (coeficientes do maior grau para o menor)."""
    out = [0] * (len(p) + len(q) - 1)
    for i, a in enumerate(p):
        if a == 0:
            continue
        for j, b in enumerate(q):
            out[i + j] ^= _mul(a, b)
    return out


def _rs_generator(n: int) -> List[int]:
    """Polinômio gerador de Reed-Solomon com ``n`` codewords de correção."""
    g = [1]
    for i in range(n):
        g = _poly_mul(g, [1, _EXP[i]])
    return g


def _rs_remainder(data: List[int], gen: List[int], n: int) -> List[int]:
    """Resto da divisão de ``data·x^n`` pelo gerador (codewords de correção)."""
    res = list(data) + [0] * n
    for i in range(len(data)):
        coef = res[i]
        if coef:
            for j, g in enumerate(gen):
                res[i + j] ^= _mul(g, coef)
    return res[len(data):]


# ── Parâmetros por versão (nível de correção M) ─────────────────────────────
#: Total de codewords de dados por versão (nível M).
_CAP_M = {1: 16, 2: 28, 3: 44, 4: 64, 5: 86, 6: 108}
#: (ec_por_bloco, [(nº_blocos, codewords_de_dados_por_bloco), ...]) por versão.
_BLOCKS_M = {
    1: (10, [(1, 16)]),
    2: (16, [(1, 28)]),
    3: (26, [(1, 44)]),
    4: (18, [(2, 32)]),
    5: (24, [(2, 43)]),
    6: (16, [(4, 27)]),
}
#: Posições centrais dos padrões de alinhamento por versão.
_ALIGN = {1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34]}

_ECC_BITS = {"L": 0b01, "M": 0b00, "Q": 0b11, "H": 0b10}


def _choose_version(n_bytes: int, error: str = "M") -> int:
    for version in range(1, 7):
        cap = _CAP_M[version]
        # 4 bits de modo + 8 bits de contagem (versões 1-9) + dados
        if n_bytes <= (cap * 8 - 12) // 8:
            return version
    raise ValueError(
        "QR Code: dados excedem a capacidade da versão 6 (106 bytes)."
    )


def _data_codewords(data: bytes, version: int) -> List[int]:
    cap = _CAP_M[version]
    bits: List[int] = []
    _append_bits(bits, 0b0100, 4)          # modo byte
    _append_bits(bits, len(data), 8)       # contagem de caracteres
    for b in data:
        _append_bits(bits, b, 8)
    # Terminador (até 4 bits) + alinhamento ao byte
    max_bits = cap * 8
    bits.extend([0] * min(4, max_bits - len(bits)))
    while len(bits) % 8:
        bits.append(0)
    codewords = [int("".join(str(b) for b in bits[i:i + 8]), 2) for i in range(0, len(bits), 8)]
    # Bytes de preenchimento alternados
    pad = (0xEC, 0x11)
    k = 0
    while len(codewords) < cap:
        codewords.append(pad[k % 2])
        k += 1
    return codewords


def _append_bits(bits: List[int], value: int, length: int) -> None:
    for i in range(length - 1, -1, -1):
        bits.append((value >> i) & 1)


def _interleave(codewords: List[int], version: int) -> List[int]:
    ec_per_block, groups = _BLOCKS_M[version]
    gen = _rs_generator(ec_per_block)

    blocks_data: List[List[int]] = []
    blocks_ec: List[List[int]] = []
    idx = 0
    for n_blocks, size in groups:
        for _ in range(n_blocks):
            block = codewords[idx:idx + size]
            idx += size
            blocks_data.append(block)
            blocks_ec.append(_rs_remainder(block, gen, ec_per_block))

    out: List[int] = []
    max_data = max(len(b) for b in blocks_data)
    for i in range(max_data):
        for b in blocks_data:
            if i < len(b):
                out.append(b[i])
    for i in range(ec_per_block):
        for b in blocks_ec:
            out.append(b[i])
    return out


# ── Construção da matriz ────────────────────────────────────────────────────
class _Matrix:
    def __init__(self, size: int) -> None:
        self.size = size
        self.modules = [[0] * size for _ in range(size)]
        self.function = [[False] * size for _ in range(size)]

    def set(self, row: int, col: int, dark: int, function: bool = True) -> None:
        if 0 <= row < self.size and 0 <= col < self.size:
            self.modules[row][col] = 1 if dark else 0
            if function:
                self.function[row][col] = True


def _place_finder(m: _Matrix, row: int, col: int) -> None:
    for dr in range(-1, 8):
        for dc in range(-1, 8):
            r, c = row + dr, col + dc
            if 0 <= r < m.size and 0 <= c < m.size:
                inside = 0 <= dr <= 6 and 0 <= dc <= 6
                dark = inside and (dr in (0, 6) or dc in (0, 6) or (2 <= dr <= 4 and 2 <= dc <= 4))
                m.set(r, c, dark)


def _place_alignment(m: _Matrix, version: int) -> None:
    pos = _ALIGN[version]
    for r in pos:
        for c in pos:
            # Não sobrepõe os localizadores
            if (r <= 8 and c <= 8) or (r <= 8 and c >= m.size - 9) or (r >= m.size - 9 and c <= 8):
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    dark = max(abs(dr), abs(dc)) != 1
                    m.set(r + dr, c + dc, dark)


def _place_function_patterns(m: _Matrix, version: int) -> None:
    size = m.size
    # Localizadores + separadores
    _place_finder(m, 0, 0)
    _place_finder(m, 0, size - 7)
    _place_finder(m, size - 7, 0)
    # Temporização
    for i in range(8, size - 8):
        m.set(6, i, i % 2 == 0)
        m.set(i, 6, i % 2 == 0)
    # Alinhamento
    _place_alignment(m, version)
    # Módulo escuro fixo: reservado como claro durante a avaliação da máscara
    # (ISO/IEC 18004 §7.8.3) e aceso em ``_place_format`` no símbolo final.
    m.set(size - 8, 8, 0)
    # Reserva das áreas de informação de formato (sem tocar no módulo escuro
    # fixo em (size-8, 8), que fica logo abaixo da cópia inferior-esquerda)
    for i in range(9):
        if i != 6:
            m.set(8, i, 0)
            m.set(i, 8, 0)
    for i in range(8):
        m.set(8, size - 1 - i, 0)
    for i in range(7):
        m.set(size - 1 - i, 8, 0)


def _place_data(m: _Matrix, bits: List[int]) -> None:
    size = m.size
    i = 0
    col = size - 1
    upward = True
    while col >= 1:
        if col == 6:
            col = 5
        for k in range(size):
            row = (size - 1 - k) if upward else k
            for c in (col, col - 1):
                if not m.function[row][c]:
                    m.modules[row][c] = bits[i] if i < len(bits) else 0
                    i += 1
        upward = not upward
        col -= 2


_MASKS = (
    lambda r, c: (r + c) % 2 == 0,
    lambda r, c: r % 2 == 0,
    lambda r, c: c % 3 == 0,
    lambda r, c: (r + c) % 3 == 0,
    lambda r, c: (r // 2 + c // 3) % 2 == 0,
    lambda r, c: (r * c) % 2 + (r * c) % 3 == 0,
    lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
    lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
)


def _apply_mask(m: _Matrix, mask: int) -> None:
    fn = _MASKS[mask]
    for r in range(m.size):
        for c in range(m.size):
            if not m.function[r][c] and fn(r, c):
                m.modules[r][c] ^= 1


def _bch_format(data5: int) -> int:
    d = data5 << 10
    g = 0x537
    while d.bit_length() - 11 >= 0:
        d ^= g << (d.bit_length() - 11)
    return ((data5 << 10) | d) ^ 0x5412


def _place_format(m: _Matrix, error: str, mask: int) -> None:
    size = m.size
    # Módulo escuro fixo — sempre aceso no símbolo final
    m.set(size - 8, 8, 1)
    fmt = _bch_format((_ECC_BITS[error] << 3) | mask)
    for i in range(15):
        bit = (fmt >> (14 - i)) & 1
        # Cópia superior-esquerda
        if i < 6:
            m.set(8, i, bit)
        elif i == 6:
            m.set(8, 7, bit)
        elif i == 7:
            m.set(8, 8, bit)
        elif i == 8:
            m.set(7, 8, bit)
        else:
            m.set(14 - i, 8, bit)
        # Cópia inferior-esquerda / superior-direita
        if i < 7:
            m.set(size - 1 - i, 8, bit)
        else:
            m.set(8, size - 15 + i, bit)


def _penalty(m: _Matrix) -> int:
    """Penalidade ISO/IEC 18004 (N1..N4) para escolha da máscara.

    A avaliação é feita **antes** de gravar a informação de formato, como manda
    a norma (o formato só é adicionado após a escolha da máscara). Segue a
    mesma pontuação de referência (N1=3, N2=3, N3=40, N4=10) usada por
    implementações consagradas, garantindo a mesma máscara escolhida.
    """
    size = m.size
    mods = m.modules
    n3_pattern = bytes((1, 0, 1, 1, 1, 0, 1))

    def _n3_occurrences(seq: bytes) -> int:
        total = 0
        idx = seq.find(n3_pattern)
        while idx != -1:
            offset = idx + 7
            if (idx in (0, size - 7)
                    or not any(seq[max(idx - 4, 0):idx])
                    or not any(seq[offset:min(offset + 4, size)])):
                total += 40
            else:
                offset = idx + 4
            idx = seq.find(n3_pattern, offset)
        return total

    score_n1 = score_n2 = score_n3 = 0
    dark = 0
    last_row: Optional[List[int]] = None
    n3_column = bytearray(size)
    for i in range(size):
        row = mods[i]
        row_prev = -1
        col_prev = -1
        n1_row = n1_col = 0
        for j in range(size):
            row_bit = row[j]
            col_bit = mods[j][i]
            n3_column[j] = col_bit
            dark += row_bit
            # N1 — sequências na linha e na coluna
            if row_bit == row_prev:
                n1_row += 1
            else:
                if n1_row >= 5:
                    score_n1 += n1_row - 2
                n1_row = 1
            if col_bit == col_prev:
                n1_col += 1
            else:
                if n1_col >= 5:
                    score_n1 += n1_col - 2
                n1_col = 1
            # N2 — blocos 2x2 de mesma cor
            if last_row is not None and j and row_bit == row_prev == last_row[j] == last_row[j - 1]:
                score_n2 += 3
            row_prev = row_bit
            col_prev = col_bit
        last_row = row
        # N3 — padrão 1:1:3:1:1 precedido/seguido por 4 claros
        score_n3 += _n3_occurrences(bytes(row))
        score_n3 += _n3_occurrences(bytes(n3_column))
        if n1_row >= 5:
            score_n1 += n1_row - 2
        if n1_col >= 5:
            score_n1 += n1_col - 2
    # N4 — proporção de módulos escuros em faixas de 5%
    percent = float(dark) / (size * size)
    score_n4 = 10 * int(abs(percent * 100 - 50) / 5)
    return score_n1 + score_n2 + score_n3 + score_n4


def encode(text: str, error: str = "M", mask: Optional[int] = None) -> List[List[bool]]:
    """Codifica ``text`` e devolve a matriz de módulos (``True`` = escuro).

    ``error`` é o nível de correção (apenas ``"M"`` é suportado nesta versão).
    ``mask`` força uma máscara específica (0-7); por padrão escolhe a de menor
    penalidade.
    """
    error = (error or "M").upper()
    if error != "M":
        error = "M"
    data = str(text or "").encode("utf-8")
    version = _choose_version(len(data), error)
    codewords = _data_codewords(data, version)
    interleaved = _interleave(codewords, version)

    bits: List[int] = []
    for cw in interleaved:
        _append_bits(bits, cw, 8)

    size = 4 * version + 17
    m = _Matrix(size)
    _place_function_patterns(m, version)
    _place_data(m, bits)

    if mask is None:
        best_mask = 0
        best_score = None
        for candidate in range(8):
            trial = _Matrix(size)
            trial.modules = [row[:] for row in m.modules]
            trial.function = [row[:] for row in m.function]
            _apply_mask(trial, candidate)
            # Avalia a máscara antes de gravar o formato (ISO/IEC 18004 §7.8.3)
            score = _penalty(trial)
            if best_score is None or score < best_score:
                best_score = score
                best_mask = candidate
        mask = best_mask

    _apply_mask(m, mask)
    _place_format(m, error, mask)
    return [[bool(v) for v in row] for row in m.modules]
