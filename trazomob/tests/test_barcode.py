# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Etiquetas técnicas: Code 128 real, QR Code nativo e carga útil estável.

Estes testes garantem que o código de barras e o QR impressos nas etiquetas são
**escaneáveis de verdade** (não apenas decorativos) e que a carga útil é estável
entre execuções — o que antes não acontecia, pois derivava de ``hash()``.
"""
from __future__ import annotations

import pytest
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from trazomob.production.barcode import (
    code128_bar_widths,
    code128_modules,
    code128_values,
)
from trazomob.production.labels import (
    label_payload,
    render_label_pixmap,
    stable_piece_code,
)
from trazomob.production.qr import (
    _data_codewords,
    _rs_generator,
    _rs_remainder,
    encode as qr_encode,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ── Code 128 ────────────────────────────────────────────────────────────────

def test_code128_known_answer_values():
    """Vetores de referência da simbologia Code 128 (conjunto B)."""
    assert code128_values("A") == [104, 33, 34, 106]
    assert code128_values("AB") == [104, 33, 34, 102, 106]


def test_code128_checksum_is_modulo_103():
    for texto in ("A", "AB", "TM-45397-700-400", "1234567890"):
        valores = code128_values(texto)
        assert valores[0] == 104  # Start B
        assert valores[-1] == 106  # Stop
        dados = valores[1:-2]
        esperado = (104 + sum(v * (i + 1) for i, v in enumerate(dados))) % 103
        assert valores[-2] == esperado


def test_code128_modules_structure():
    modulos = code128_modules("A")
    assert set(modulos) <= {"0", "1"}
    # 3 símbolos de dados (11 módulos) + Stop (13 módulos)
    assert len(modulos) == 11 + 11 + 11 + 13
    assert modulos.startswith("11010010000")  # Start B
    assert modulos.endswith("1100011101011")  # Stop


def test_code128_bar_widths_alternate_and_are_valid():
    barras = code128_bar_widths("TM-45397-700-400")
    assert barras[0][0] is True  # começa com barra
    for i, (e_barra, largura) in enumerate(barras):
        assert e_barra is (i % 2 == 0)
        assert 1 <= largura <= 4


def test_code128_sanitizes_non_representable_chars():
    """Caracteres fora do conjunto B viram espaço, mas o código segue válido."""
    valores = code128_values("café")  # 'é' fora do ASCII imprimível
    assert valores[0] == 104 and valores[-1] == 106
    assert all(0 <= v <= 106 for v in valores)


# ── QR Code ─────────────────────────────────────────────────────────────────

def test_qr_short_text_is_version_1():
    matriz = qr_encode("HELLO", "M")
    assert len(matriz) == 21
    assert all(len(linha) == 21 for linha in matriz)
    assert all(isinstance(v, bool) for linha in matriz for v in linha)


def test_qr_finder_patterns_present():
    matriz = qr_encode("HELLO", "M")
    n = len(matriz)
    for (r0, c0) in ((0, 0), (0, n - 7), (n - 7, 0)):
        # anel externo escuro
        assert all(matriz[r0][c0 + i] for i in range(7))
        assert all(matriz[r0 + i][c0] for i in range(7))
        # anel interno claro
        assert not any(matriz[r0 + 1][c0 + 1 + i] for i in range(5))
        # centro 3x3 escuro
        assert matriz[r0 + 3][c0 + 3]


def test_qr_dark_module_always_lit():
    for texto in ("A", "HELLO", "x" * 60):
        matriz = qr_encode(texto, "M")
        n = len(matriz)
        assert matriz[n - 8][8] is True


def test_qr_timing_pattern_alternates():
    matriz = qr_encode("HELLO", "M")
    n = len(matriz)
    for i in range(8, n - 8):
        assert matriz[6][i] != matriz[6][i + 1]
        assert matriz[i][6] != matriz[i + 1][6]


def test_qr_data_codewords_known_answer():
    """Vetor conhecido para ``HELLO`` (versão 1, nível M)."""
    assert _data_codewords(b"HELLO", 1) == [
        0x40, 0x54, 0x84, 0x54, 0xC4, 0xC4, 0xF0,
        0xEC, 0x11, 0xEC, 0x11, 0xEC, 0x11, 0xEC, 0x11, 0xEC,
    ]


def test_qr_reed_solomon_remainder_is_valid():
    """A sequência dados+correção deve ser divisível pelo gerador (resto nulo)."""
    for n_ec, dados in ((10, b"HELLO"), (16, b"http://x"), (26, b"x" * 40)):
        version = {10: 1, 16: 2, 26: 3}[n_ec]
        codewords = _data_codewords(dados, version)
        gen = _rs_generator(n_ec)
        ec = _rs_remainder(codewords, gen, n_ec)
        completa = codewords + ec
        assert _rs_remainder(completa, gen, n_ec) == [0] * n_ec


def test_qr_grows_with_payload():
    tamanhos = [len(qr_encode("x" * n, "M")) for n in (1, 20, 40, 60)]
    assert tamanhos == sorted(tamanhos)
    assert tamanhos[0] < tamanhos[-1]


def test_qr_all_masks_are_distinct_but_valid():
    matrizes = [qr_encode("TM-45397-700-400", "M", mask=mk) for mk in range(8)]
    for m in matrizes:
        n = len(m)
        assert m[n - 8][8] is True
    assert len({tuple(tuple(row) for row in m) for m in matrizes}) == 8


def test_qr_matches_segno_when_available():
    """Comparação opcional com ``segno`` (dependência só de desenvolvimento).

    ``segno`` não é requisito do plugin: o teste é ignorado quando ele não
    está instalado. Quando está, neutralizamos a peculiaridade de padding do
    ``segno`` (que acrescenta um byte ``0x00`` extra já alinhado) para comparar
    bit a bit a matriz produzida.
    """
    segno = pytest.importorskip("segno")
    segno_encoder = pytest.importorskip("segno.encoder")

    def _padding_iso(buff, version, length):
        if version not in (segno_encoder.consts.VERSION_M1, segno_encoder.consts.VERSION_M3):
            resto = length % 8
            if resto:
                buff.extend([0] * (8 - resto))

    segno_encoder.write_padding_bits = _padding_iso
    for texto in ("HELLO", "http://x", "TM-45397-700-400", "x" * 40):
        ref = segno.make(texto, error="m", micro=False, boost_error=False, mode="byte")
        esperado = [[bool(v) for v in row] for row in ref.matrix]
        assert qr_encode(texto, "M") == esperado


# ── Carga útil e renderização ───────────────────────────────────────────────

_PART = {
    "nome": "Lateral Esquerda",
    "modulo": "Balcao 800",
    "material": "MDF Branco TX",
    "comprimento": 700.0,
    "largura": 400.0,
    "espessura": 18.0,
    "comprimento_corte": 704.0,
    "largura_corte": 404.0,
    "fita_c1": True,
    "fita_l1": True,
    "operacoes": [1, 2, 3],
    "quantidade": 2,
    "espessura_fita": 0.45,
}


def test_label_payload_is_stable_and_ascii():
    a = label_payload(dict(_PART))
    b = label_payload(dict(_PART))
    assert a == b
    assert a.isascii()
    assert a == "TM-45397-700-400"
    assert stable_piece_code(dict(_PART)) == "45397"


def test_stable_code_independent_of_int_or_float_dimensions():
    """``700`` e ``700.0`` devem gerar o mesmo código (e a mesma carga útil)."""
    inteiro = dict(_PART, comprimento=700, largura=400, espessura=18)
    flutuante = dict(_PART, comprimento=700.0, largura=400.0, espessura=18.0)
    assert stable_piece_code(inteiro) == stable_piece_code(flutuante)
    assert label_payload(inteiro) == label_payload(flutuante)


def test_label_payload_changes_with_dimensions():
    outro = dict(_PART, comprimento=800.0)
    assert label_payload(outro) != label_payload(_PART)


def _dark_pixels(image: QImage, x0: int, y0: int, x1: int, y1: int) -> int:
    total = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            if image.pixelColor(x, y).lightness() < 128:
                total += 1
    return total


def test_render_label_has_scannable_regions(qapp):
    pix = render_label_pixmap(dict(_PART))
    assert not pix.isNull()
    assert (pix.width(), pix.height()) == (340, 210)
    image = pix.toImage()
    # Região do código de barras (esquerda do rodapé)
    assert _dark_pixels(image, 12, 156, 262, 186) > 50
    # Região do QR Code (direita do rodapé)
    assert _dark_pixels(image, 272, 150, 328, 206) > 50


def test_render_label_scale_multiplies_resolution(qapp):
    pix = render_label_pixmap(dict(_PART), scale=3.0)
    assert (pix.width(), pix.height()) == (1020, 630)


def test_render_label_handles_minimal_part(qapp):
    pix = render_label_pixmap({"nome": "Peça"})
    assert not pix.isNull()
    assert pix.width() == 340
