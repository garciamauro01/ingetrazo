# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Mede o custo real de inserir decoração: converter vs. ler o pré-assado.

Gera um OBJ de ``n × n`` quads (formato que o host realmente converte), mede
``component_loader.load_group`` direto no OBJ e depois no ``.igz`` assado por
``decor_bake``. Rode da raiz do IngeTrazo::

    venv\\Scripts\\python.exe trazomob/scripts/benchmark_decor_bake.py 200
"""
from __future__ import annotations

import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

HOST_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HOST_ROOT))

_TMP = tempfile.TemporaryDirectory(prefix="trazomob-bake-bench-")
os.environ.setdefault("INGETRAZO_COMPONENTS", str(Path(_TMP.name) / "components"))

from views import component_loader  # noqa: E402

from trazomob.integrations import decor_bake  # noqa: E402


def write_obj(path: Path, n: int) -> Path:
    """OBJ ASCII com ``n²`` quads — decoração sintética, conversão real."""
    with path.open("w", encoding="utf-8") as out:
        for i in range(n + 1):
            for j in range(n + 1):
                out.write("v %.4f %.4f 0.0\n" % (i * 0.05, j * 0.05))
        for i in range(n):
            for j in range(n):
                a = i * (n + 1) + j + 1
                b, c, d = a + 1, a + n + 2, a + n + 1
                out.write("f %d %d %d %d\n" % (a, b, c, d))
    return path


def timed(fn, repeat: int = 5) -> tuple[float, float]:
    samples = []
    for _ in range(repeat):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    return min(samples), statistics.median(samples)


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    work = Path(_TMP.name)
    source = write_obj(work / ("almofada_%d.obj" % n), n)

    print("OBJ: %d x %d quads, %.1f KB" % (n, n, source.stat().st_size / 1024))

    t_bake = timed(lambda: decor_bake.bake_source(source), repeat=1)[0]
    meta = decor_bake.bake_source(source)
    if meta is None:
        print("falha: a origem não produziu geometria")
        return 1
    cached = Path(meta["cache"])

    cold_min, cold_med = timed(
        lambda: component_loader.load_group(source, matrix=None, name="Almofada"))
    warm_min, warm_med = timed(
        lambda: component_loader.load_group(cached, matrix=None, name="Almofada"))

    print("conversao OBJ  : min %.2f ms | mediana %.2f ms" %
          (cold_min * 1000, cold_med * 1000))
    print("leitura .igz   : min %.2f ms | mediana %.2f ms" %
          (warm_min * 1000, warm_med * 1000))
    print("speedup        : %.1fx (mediana)" % (cold_med / max(warm_med, 1e-9)))
    print("assado uma vez : %.2f ms -> %.1f KB" %
          (t_bake * 1000, cached.stat().st_size / 1024))
    print("geometria      : %d face(s), %d vertice(s)" %
          (meta["faces"], meta["vertices"]))
    print("(o loader do host funde quads coplanares; por isso 1 face com muitos vertices)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
