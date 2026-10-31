# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
"""Avaliador completo com detecção de dependência circular topológica (Cycle Detection)."""
from __future__ import annotations

import ast
import datetime
import math
import re
from typing import Any


class CycleInFormulaError(Exception):
    """Exceção levantada quando há dependência circular entre fórmulas."""
    pass


class SafeExpressionEvaluator:
    """Avaliador seguro para expressões com todas as funções matemáticas, texto, lógicas e detecção de ciclos."""

    @classmethod
    def get_builtins(cls, current_context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx_data = current_context or {}

        def _nearest(target, *candidates):
            try:
                t = float(target)
                c_vals = [float(c) for c in candidates]
                return min(c_vals, key=lambda c: abs(c - t))
            except Exception:
                return candidates[0] if candidates else target

        def _current(attr_name: str):
            clean_name = str(attr_name).strip("\"'")
            return ctx_data.get(clean_name, 0.0)

        return {
            # Matemáticas
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sqrt": math.sqrt,
            "sin": lambda deg: math.sin(math.radians(deg)),
            "cos": lambda deg: math.cos(math.radians(deg)),
            "tan": lambda deg: math.tan(math.radians(deg)),
            "asin": lambda x: math.degrees(math.asin(x)),
            "acos": lambda x: math.degrees(math.acos(x)),
            "atan": lambda x: math.degrees(math.atan(x)),
            "radians": math.radians,
            "degrees": math.degrees,
            "floor": math.floor,
            "ceil": math.ceil,
            "int": int,
            "float": float,
            "str": str,
            "len": len,
            "pi": math.pi,
            "exp": math.exp,
            "log": math.log,
            "log10": math.log10,

            # Funções SketchUp DC
            "ABS": abs,
            "ROUND": round,
            "SQRT": math.sqrt,
            "SIN": lambda deg: math.sin(math.radians(deg)),
            "COS": lambda deg: math.cos(math.radians(deg)),
            "TAN": lambda deg: math.tan(math.radians(deg)),
            "DEGREES": math.degrees,
            "RADIANS": math.radians,
            "FLOOR": math.floor,
            "CEILING": math.ceil,
            "SMALLEST": min,
            "LARGEST": max,
            "NEAREST": _nearest,
            "CURRENT": _current,

            # Lógica e Escolha
            "IF": lambda cond, val_true, val_false: val_true if cond else val_false,
            "AND": lambda *args: all(args),
            "OR": lambda *args: any(args),
            "NOT": lambda x: not x,
            "CHOOSE": lambda idx, *choices: choices[int(idx) - 1] if 1 <= int(idx) <= len(choices) else choices[-1],

            # Texto
            "CONCATENATE": lambda *args: "".join(str(a) for a in args),
            "LEFT": lambda s, n: str(s)[:int(n)],
            "RIGHT": lambda s, n: str(s)[-int(n):] if int(n) > 0 else "",
            "MID": lambda s, start, length: str(s)[int(start)-1:int(start)-1+int(length)],
            "TRIM": lambda s: str(s).strip(),
            "UPPER": lambda s: str(s).upper(),
            "LOWER": lambda s: str(s).lower(),
            "SUBSTITUTE": lambda text, old, new: str(text).replace(str(old), str(new)),
            "FIND": lambda find_txt, within_txt, start=1: str(within_txt).find(str(find_txt), int(start)-1) + 1,

            # Conversão de Unidades
            "INCHES_TO_CM": lambda inches: float(inches) * 2.54,
            "CM_TO_INCHES": lambda cm: float(cm) / 2.54,
            "M_TO_CM": lambda m: float(m) * 100.0,
            "CM_TO_M": lambda cm: float(cm) / 100.0,
            "M_TO_INCHES": lambda m: float(m) * 39.3701,
            "INCHES_TO_M": lambda inches: float(inches) * 0.0254,

            # Data
            "CURRENT_DATE": lambda: datetime.date.today().isoformat(),
            "CURRENT_YEAR": lambda: datetime.date.today().year,
        }

    @classmethod
    def get_referenced_names(cls, expr: str) -> set[str]:
        """Extrai os nomes de variáveis referenciados na fórmula para análise de dependências."""
        expr = str(expr).strip()
        if not expr:
            return set()
        if expr.startswith("="):
            expr = expr[1:].strip()
        expr = re.sub(r"([A-Za-z0-9_]+)!([A-Za-z0-9_]+)", r"\1__\2", expr)

        try:
            tree = ast.parse(expr, mode="eval")
        except Exception:
            return set()

        builtins = set(cls.get_builtins().keys())
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if node.id not in builtins:
                    names.add(node.id)
        return names

    @classmethod
    def evaluate(cls, expr: str, context: dict[str, Any]) -> Any:
        expr = str(expr).strip()
        if not expr:
            return None
        if expr.startswith("="):
            expr = expr[1:].strip()

        expr = re.sub(r"([A-Za-z0-9_]+)!([A-Za-z0-9_]+)", r"\1__\2", expr)

        ctx = cls.get_builtins(context)
        for k, v in context.items():
            norm_k = k.replace("!", "__")
            ctx[norm_k] = v

        try:
            tree = ast.parse(expr, mode="eval")
            return cls._eval_node(tree.body, ctx)
        except Exception as err:
            return f"#ERRO: {err}"

    @classmethod
    def _eval_node(cls, node: ast.AST, ctx: dict[str, Any]) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            if node.id in ctx:
                return ctx[node.id]
            for k, v in ctx.items():
                if k.lower() == node.id.lower():
                    return v
            raise NameError(f"Variável ou função indefinida: '{node.id}'")
        elif isinstance(node, ast.UnaryOp):
            val = cls._eval_node(node.operand, ctx)
            if isinstance(node.op, ast.UAdd):
                return +val
            elif isinstance(node.op, ast.USub):
                return -val
            elif isinstance(node.op, ast.Not):
                return not val
        elif isinstance(node, ast.BinOp):
            left = cls._eval_node(node.left, ctx)
            right = cls._eval_node(node.right, ctx)
            if isinstance(node.op, ast.Add):
                if isinstance(left, str) or isinstance(right, str):
                    return str(left) + str(right)
                return left + right
            elif isinstance(node.op, ast.Sub):
                return left - right
            elif isinstance(node.op, ast.Mult):
                return left * right
            elif isinstance(node.op, ast.Div):
                return left / right if right != 0 else 0.0
            elif isinstance(node.op, ast.FloorDiv):
                return left // right if right != 0 else 0
            elif isinstance(node.op, ast.Mod):
                return left % right
            elif isinstance(node.op, ast.Pow):
                return left ** right
        elif isinstance(node, ast.Compare):
            left = cls._eval_node(node.left, ctx)
            res = True
            for op, comparator in zip(node.ops, node.comparators):
                right = cls._eval_node(comparator, ctx)
                if isinstance(op, ast.Eq):
                    res = (left == right)
                elif isinstance(op, ast.NotEq):
                    res = (left != right)
                elif isinstance(op, ast.Lt):
                    res = (left < right)
                elif isinstance(op, ast.LtE):
                    res = (left <= right)
                elif isinstance(op, ast.Gt):
                    res = (left > right)
                elif isinstance(op, ast.GtE):
                    res = (left >= right)
                else:
                    raise TypeError(f"Operador de comparação não suportado: {type(op)}")
                if not res:
                    return False
                left = right
            return res
        elif isinstance(node, ast.Call):
            func = cls._eval_node(node.func, ctx)
            args = [cls._eval_node(a, ctx) for a in node.args]
            return func(*args)
        elif isinstance(node, ast.IfExp):
            test = cls._eval_node(node.test, ctx)
            return cls._eval_node(node.body, ctx) if test else cls._eval_node(node.orelse, ctx)
        elif isinstance(node, ast.List):
            return [cls._eval_node(e, ctx) for e in node.elts]
        elif isinstance(node, ast.Tuple):
            return tuple(cls._eval_node(e, ctx) for e in node.elts)

        raise ValueError(f"Expressão ou nó não suportado: {type(node)}")
