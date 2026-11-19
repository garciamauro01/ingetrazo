# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Catálogo centralizado de materiais e texturas de MDF e Marmoraria do TrazoMob."""
from __future__ import annotations

from pathlib import Path
from .materials_registry import MaterialsRegistry, MaterialDefinition

# Obtém a lista dinâmica a partir do registro oficial de materiais
def get_available_mdf_materials() -> list[str]:
    """Retorna a lista de padrões de MDF cadastrados."""
    return [m.nome for m in MaterialsRegistry.get_instance().list_materials(categoria="mdf")]


def get_available_stone_materials() -> list[str]:
    """Retorna a lista de padrões de pedras e bancadas cadastradas."""
    return [m.nome for m in MaterialsRegistry.get_instance().list_materials(categoria="pedra")] + [
        m.nome for m in MaterialsRegistry.get_instance().list_materials(categoria="madeira_macica")
    ]


def get_all_materials() -> list[str]:
    """Retorna todos os materiais suportados."""
    return [m.nome for m in MaterialsRegistry.get_instance().list_materials()]


# Compatibilidade legada para referências diretas de listas
MDF_MATERIALS = get_available_mdf_materials()
STONE_MATERIALS = get_available_stone_materials()
ALL_BOX_MATERIALS = get_all_materials()

# ── Limites Físicos de Fabricação de Chapas de MDF (Padrão Industrial) ──
# Dimensões brutas padrão da chapa no mercado: 2750 x 1850 mm
# Margem mínima de limpeza / refilo de esquadro nas extremidades: 15 mm de cada lado
# Comprimento útil máximo: 2750 - (2 * 15) = 2720 mm
# Largura útil máxima: 1850 - (2 * 15) = 1820 mm
CHAPA_BRUTA_COMPRIMENTO_MM = 2750.0
CHAPA_BRUTA_LARGURA_MM = 1850.0
CHAPA_REFILO_LIMPEZA_MM = 15.0
CHAPA_MAX_COMPRIMENTO_UTIL_MM = CHAPA_BRUTA_COMPRIMENTO_MM - (2.0 * CHAPA_REFILO_LIMPEZA_MM)  # 2720.0 mm
CHAPA_MAX_LARGURA_UTIL_MM = CHAPA_BRUTA_LARGURA_MM - (2.0 * CHAPA_REFILO_LIMPEZA_MM)          # 1820.0 mm


def clamp_peca_to_sheet_limits(
    dim1_m: float,
    dim2_m: float,
    dim3_m: float,
    material: str = "",
) -> tuple[float, float, float]:
    """Valida e aplica o limite rígido de chapa (com refilo de limpeza) a uma peça de marcenaria.

    Para chapas de MDF, a maior dimensão plana da peça não pode exceder o comprimento útil máximo
    (2720 mm) e a segunda maior dimensão não pode exceder a largura útil máxima (1820 mm).
    """
    mat_lower = str(material or "").lower()
    # Se for pedra/bancada/granito ou perfil metálico, pode ter outro tratamento
    if "granito" in mat_lower or "mármore" in mat_lower or "quartzo" in mat_lower:
        return dim1_m, dim2_m, dim3_m

    limite_maior_m = CHAPA_MAX_COMPRIMENTO_UTIL_MM / 1000.0  # 2.72 m
    limite_menor_m = CHAPA_MAX_LARGURA_UTIL_MM / 1000.0      # 1.82 m

    # Identifica o eixo da espessura (menor dimensão)
    dims = [abs(dim1_m), abs(dim2_m), abs(dim3_m)]
    min_dim = min(dims)
    esp_idx = dims.index(min_dim)

    # Os outros dois eixos são as dimensões de face/corte da chapa
    face_indices = [i for i in range(3) if i != esp_idx]
    d_a, d_b = dims[face_indices[0]], dims[face_indices[1]]

    # A maior dimensão da face pode ter até 2720mm, e a outra até 1820mm
    if d_a >= d_b:
        d_a_clamped = min(d_a, limite_maior_m)
        d_b_clamped = min(d_b, limite_menor_m)
    else:
        d_b_clamped = min(d_b, limite_maior_m)
        d_a_clamped = min(d_a, limite_menor_m)

    res = list(dims)
    res[face_indices[0]] = d_a_clamped
    res[face_indices[1]] = d_b_clamped

    # Preserva o sinal original
    s1 = -res[0] if dim1_m < 0 else res[0]
    s2 = -res[1] if dim2_m < 0 else res[1]
    s3 = -res[2] if dim3_m < 0 else res[2]
    return (s1, s2, s3)


def get_available_mdf_materials() -> list[str]:
    """Retorna a lista de padrões de MDF."""
    return list(MDF_MATERIALS)


def get_available_stone_materials() -> list[str]:
    """Retorna a lista de padrões de pedras e bancadas."""
    return list(STONE_MATERIALS)


def get_all_materials() -> list[str]:
    """Retorna todos os materiais suportados."""
    return list(ALL_BOX_MATERIALS)


def get_material_color(material: str) -> tuple[float, float, float]:
    """Retorna a cor RGB normalizada (0.0 a 1.0) para um determinado acabamento ou padrão de material."""
    mat_def = MaterialsRegistry.get_instance().get_material(material)
    if mat_def and mat_def.cor_rgb and len(mat_def.cor_rgb) >= 3:
        return (mat_def.cor_rgb[0], mat_def.cor_rgb[1], mat_def.cor_rgb[2])

    mat_lower = (material or "").lower()
    # Materiais de Marmoraria / Pedras / Metais
    if "sao gabriel" in mat_lower or "preto absoluto" in mat_lower or "granito preto" in mat_lower:
        return (0.12, 0.12, 0.13)
    if "nero" in mat_lower or "marquina" in mat_lower:
        return (0.10, 0.10, 0.11)
    if "pietra" in mat_lower or "grey" in mat_lower:
        return (0.32, 0.33, 0.35)
    if "armani" in mat_lower or "gris" in mat_lower:
        return (0.42, 0.38, 0.35)
    if "siena" in mat_lower or "branco siena" in mat_lower:
        return (0.88, 0.88, 0.86)
    if "calacatta" in mat_lower or "calacata" in mat_lower or "carrara" in mat_lower or "parana" in mat_lower:
        return (0.93, 0.93, 0.94)
    if "travertino" in mat_lower or "bege" in mat_lower:
        return (0.86, 0.82, 0.75)
    if "concreto" in mat_lower or "cimento" in mat_lower:
        return (0.62, 0.62, 0.60)
    if "teca" in mat_lower or "lamelado" in mat_lower:
        return (0.72, 0.52, 0.32)
    if "quartzo" in mat_lower or "silestone" in mat_lower:
        return (0.95, 0.95, 0.95)
    if "corumba" in mat_lower or "cinza andorinha" in mat_lower:
        return (0.58, 0.58, 0.59)
    if "inox" in mat_lower or "aco" in mat_lower or "aço" in mat_lower:
        return (0.80, 0.82, 0.84)
    if "cuba" in mat_lower:
        return (0.75, 0.77, 0.80)
    # MDF / Marcenaria
    if "autentic" in mat_lower:
        return (198 / 255.0, 165 / 255.0, 127 / 255.0)
    if "ciliegio" in mat_lower or "florenca" in mat_lower:
        return (206 / 255.0, 190 / 255.0, 171 / 255.0)
    if "castanho" in mat_lower:
        return (100 / 255.0, 74 / 255.0, 54 / 255.0)
    if "carvalho" in mat_lower:
        return (203 / 255.0, 175 / 255.0, 142 / 255.0)
    if "freijo" in mat_lower or "madeira" in mat_lower:
        return (0.75, 0.55, 0.35)
    if "grafite" in mat_lower or "preto" in mat_lower or "chumbo" in mat_lower:
        return (0.25, 0.25, 0.25)
    if "cinza" in mat_lower or "titanio" in mat_lower:
        return (0.65, 0.65, 0.65)
    return (0.95, 0.95, 0.93)
