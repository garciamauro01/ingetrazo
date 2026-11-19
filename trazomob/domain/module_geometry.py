# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Utilitários geométricos, alinhamento espacial e classificação funcional de módulos do TrazoMob.

Concentra:
1. Cálculo de limites de caixaria (desconsiderando portas, puxadores e frentes projetadas).
2. Vetores normais de alinhamento traseiro/lateral conforme rotação espacial.
3. Preservação de alinhamento traseiro e canto de parede durante redimensionamento.
4. Classificação funcional de categorias para herança de medidas (inferior, aéreo, torre, esquadrias).
"""
from __future__ import annotations

import math
from typing import Any, Tuple, Optional

from PySide6.QtGui import QVector3D

from core.group import Group, iter_placements
from ..domain.schema import kind_of, module_params


def get_module_carcass_bounds(mod: Group) -> Optional[Tuple[float, float, float, float, float, float]]:
    """Calcula os limites em metros da caixaria (min_x, max_x, min_y, max_y, min_z, max_z).

    Ignora frentes móveis, portas abertas, puxadores e perfis de acabamento para obter o volume
    bruto real da estrutura de madeira ou alvenaria.
    """
    if mod is None:
        return None

    min_x, max_x = float("inf"), float("-inf")
    min_y, max_y = float("inf"), float("-inf")
    min_z, max_z = float("inf"), float("-inf")
    found = False
    tipo = ""
    is_esquadria = getattr(mod, "layer", "") == "ESQUADRIAS"
    if getattr(mod, "ext", None) and isinstance(mod.ext, dict):
        if kind_of(mod) == "esquadria":
            is_esquadria = True
        tipo = str(module_params(mod).get("tipo", ""))
        if tipo.startswith(("porta_", "janela_")):
            is_esquadria = True

    if is_esquadria:
        ignore_terms: tuple[str, ...] = ("Folha", "Fechadura", "Ferragem", "Maçaneta", "Alavanca", "Espelho", "Puxador")
    elif tipo in ("peca_porta", "peca_portas_correr"):
        ignore_terms = ("Puxador", "Perfil", "Base Projetada")
    else:
        ignore_terms = ("Porta", "Frente", "Puxador", "Perfil", "Base Projetada")

    for pg, m in iter_placements(mod):
        nome = getattr(pg, "name", "")
        if any(ign in nome for ign in ignore_terms) or nome.startswith("Ferragem -"):
            continue
        mesh = getattr(pg, "mesh", None)
        if mesh is not None and getattr(mesh, "vertices", None):
            for v in mesh.vertices:
                p = getattr(v, "position", v)
                if m is not None:
                    p = m.map(p)
                min_x, max_x = min(min_x, p.x()), max(max_x, p.x())
                min_y, max_y = min(min_y, p.y()), max(max_y, p.y())
                min_z, max_z = min(min_z, p.z()), max(max_z, p.z())
                found = True

    if not found:
        # Fallback de segurança: calcula com todos os vértices do módulo se os nomes divergirem
        for pg, m in iter_placements(mod):
            if str(getattr(pg, "name", "")).startswith("Ferragem -"):
                continue
            mesh = getattr(pg, "mesh", None)
            if mesh is not None and getattr(mesh, "vertices", None):
                for v in mesh.vertices:
                    p = getattr(v, "position", v)
                    if m is not None:
                        p = m.map(p)
                    min_x, max_x = min(min_x, p.x()), max(max_x, p.x())
                    min_y, max_y = min(min_y, p.y()), max(max_y, p.y())
                    min_z, max_z = min(min_z, p.z()), max(max_z, p.z())
                    found = True

    if not found:
        return None
    return (min_x, max_x, min_y, max_y, min_z, max_z)


def get_module_back_normal(rot_z_deg: float) -> QVector3D:
    """Retorna o vetor unitário apontando para a traseira/fundo do módulo no plano XY."""
    rad = math.radians(rot_z_deg % 360.0)
    # No construtor (rot_z=0), a traseira fica em +Y
    # Rotacionando em Z por 'rot_z':
    # x' = -sin(rot)
    # y' = cos(rot)
    return QVector3D(-math.sin(rad), math.cos(rad), 0.0).normalized()


def preserve_module_back_alignment(old_mod: Group, new_mod: Group, rot_z_deg: float) -> None:
    """Ajusta new_mod para que sua quina traseira-esquerda e sua base Z permaneçam rigorosamente no mesmo ponto de old_mod.

    Isso garante que ao alterar largura, profundidade, altura ou se o móvel tiver sido movido/rotacionado
    no 3D (com snap magnético ou com a ferramenta Move/Rotate nativa), a traseira continue colada na parede,
    a lateral esquerda continue ancorada nos módulos vizinhos e a base continue na mesma altura Z.
    """
    b_old = get_module_carcass_bounds(old_mod)
    b_new = get_module_carcass_bounds(new_mod)
    if b_old is None or b_new is None:
        return

    back_n = get_module_back_normal(rot_z_deg)
    # Vetor unitário apontando para a Esquerda local do móvel (-X local rotacionado por rot_z_deg)
    rad = math.radians(rot_z_deg % 360.0)
    left_n = QVector3D(-math.cos(rad), -math.sin(rad), 0.0).normalized()

    corners_old = [
        QVector3D(b_old[0], b_old[2], 0.0), QVector3D(b_old[1], b_old[2], 0.0),
        QVector3D(b_old[0], b_old[3], 0.0), QVector3D(b_old[1], b_old[3], 0.0),
    ]
    corners_new = [
        QVector3D(b_new[0], b_new[2], 0.0), QVector3D(b_new[1], b_new[2], 0.0),
        QVector3D(b_new[0], b_new[3], 0.0), QVector3D(b_new[1], b_new[3], 0.0),
    ]

    proj_back_old = max(QVector3D.dotProduct(p, back_n) for p in corners_old)
    proj_back_new = max(QVector3D.dotProduct(p, back_n) for p in corners_new)
    delta_back = proj_back_old - proj_back_new

    proj_left_old = max(QVector3D.dotProduct(p, left_n) for p in corners_old)
    proj_left_new = max(QVector3D.dotProduct(p, left_n) for p in corners_new)
    delta_left = proj_left_old - proj_left_new

    dz = b_old[4] - b_new[4]

    shift = back_n * delta_back + left_n * delta_left + QVector3D(0.0, 0.0, dz)
    shift_module_geometry(new_mod, shift)


def shift_module_geometry(group: Group, shift: QVector3D) -> None:
    """Translada vértices e metadados cinemáticos de todas as peças de um módulo."""
    if shift.length() <= 1e-7:
        return
    targets = getattr(group, "children", []) or [group]
    for t in targets:
        m_sub = getattr(t, "mesh", None)
        if m_sub and hasattr(m_sub, "vertices"):
            for v in m_sub.vertices:
                v.position += shift
            m_sub._mut_serial = getattr(m_sub, "_mut_serial", 0) + 1
        t_ext = getattr(t, "ext", None)
        if isinstance(t_ext, dict):
            if "orig_vertices" in t_ext:
                t_ext["orig_vertices"] = [p + shift for p in t_ext["orig_vertices"]]
            if "hinge_pivot" in t_ext and isinstance(t_ext["hinge_pivot"], QVector3D):
                t_ext["hinge_pivot"] = t_ext["hinge_pivot"] + shift
            tm = t_ext.get("trazomob")
            if isinstance(tm, dict):
                for key in ("rot_origin", "hinge_pivot"):
                    orig_pt = tm.get(key)
                    if isinstance(orig_pt, QVector3D):
                        tm[key] = orig_pt + shift
                    elif isinstance(orig_pt, (list, tuple)) and len(orig_pt) == 3:
                        shifted = (
                            float(orig_pt[0]) + shift.x(),
                            float(orig_pt[1]) + shift.y(),
                            float(orig_pt[2]) + shift.z(),
                        )
                        tm[key] = list(shifted) if isinstance(orig_pt, list) else shifted


def get_reference_module(scene) -> Optional[Group]:
    """Retorna o módulo de referência selecionado ou o último adicionado na cena."""
    if scene is None:
        return None
    sel = getattr(scene, "selection", None)
    if sel:
        from ..domain.assembly import is_module
        for s in sel:
            if is_module(s):
                return s
    grps = getattr(scene, "groups", [])
    if grps:
        from ..domain.assembly import is_module
        for g in reversed(grps):
            if is_module(g):
                return g
    return None


def get_module_category(tipo: str, default_z: float = 0.0) -> str:
    """Classifica o módulo em uma categoria funcional para herança de cotas e alinhamento contíguo.

    Categorias:
    - 'peca': peças avulsas de marcenaria (não herdam medidas de balcões nem de armários)
    - 'porta': esquadrias do tipo porta (nível do solo Z=0)
    - 'janela': esquadrias do tipo janela (peitoril elevado Z>0)
    - 'aereo': módulos aéreos suspensos (Z >= 0.8m, nichos de parede, aéreos)
    - 'alto': torres de eletro, roupeiros, armários verticais altos (H >= 1.6m)
    - 'bancada': tampos e bancadas de pedra / marmoraria
    - 'inferior': balcões de chão, gaveteiros, etc. (Z < 0.8m)
    """
    t = str(tipo).lower()
    if t.startswith("peca_") or t == "rodape_fechado":
        return "peca"
    if "porta" in t and "porta_tempero" not in t:
        return "porta"
    if "janela" in t:
        return "janela"
    if t.startswith("cama_") or t in ("bicama", "beliche"):
        return "cama"
    if "bancada" in t or "ilha" in t:
        return "bancada"
    if any(k in t for k in ("aereo", "nicho")):
        return "aereo"
    if any(k in t for k in ("torre", "geladeira", "roupeiro", "armario")):
        return "alto"
    if "banheiro" in t or "gabinete" in t:
        return "banheiro"
    if float(default_z) >= 0.8:
        return "aereo"
    return "inferior"


def is_compatible_category(cat1: str, cat2: str) -> bool:
    """Retorna True se duas categorias devem compartilhar e herdar altura, profundidade e alinhamento."""
    # Peças avulsas, esquadrias e camas NUNCA compartilham/herdam medidas de móveis completos ou entre si
    if cat1 in ("peca", "porta", "janela", "cama") or cat2 in ("peca", "porta", "janela", "cama"):
        return False
    if cat1 == cat2:
        return True
    # Inferiores e Gabinetes de banheiro compartilham profundidade/alinhamento de chão
    if cat1 in ("inferior", "banheiro") and cat2 in ("inferior", "banheiro"):
        return True
    # Aéreos e Nichos suspensos compartilham elevação e profundidade
    if cat1 in ("aereo", "nicho") and cat2 in ("aereo", "nicho"):
        return True
    return False


#: Regra do balcão e aéreo com portas: 1 a 4 portas, 400 mm cada.
DOOR_WIDTH_MM = 400.0
MIN_DOORS = 1
MAX_DOORS = 4


def width_for_doors(num_portas: int) -> float:
    """Largura do balcão para ``num_portas`` portas de 400 mm."""
    n = max(MIN_DOORS, min(MAX_DOORS, int(num_portas)))
    return n * DOOR_WIDTH_MM


def auto_divisoes_for_doors(num_portas: int) -> int:
    """Divisórias estruturais necessárias para ``num_portas`` portas.

    O balcão com portas é limitado a 4 portas (``MAX_DOORS``). A partir da
    3ª porta é preciso uma divisória: 1 e 2 portas usam os próprios montantes
    laterais; 3 e 4 portas usam 1 divisória (um vão duplo + um simples, ou
    dois vãos duplos).
    """
    n = max(0, min(MAX_DOORS, int(num_portas)))
    if n < 3:
        return 0
    return (n + 1) // 2 - 1


def build_default_module_params(mod_data: dict[str, Any]) -> dict[str, Any]:
    """Preenche os parâmetros completos para construir um módulo.

    A precedência é: catálogo (``mod_data``) -> preferências globais de
    marcenaria -> medidas padrão salvas para o tipo/categoria do módulo.
    Esquadrias (portas e janelas) preservam sempre as medidas do catálogo.
    """
    from ..domain.preferences import TrazoMobPreferencesManager

    prefs = TrazoMobPreferencesManager.get_instance()

    tipo = str(mod_data.get("id") or mod_data.get("tipo") or "balcao")
    cat = get_module_category(tipo, default_z=float(mod_data.get("default_z", 0.0)))

    # Esquadrias e peças avulsas preservam sempre suas medidas originais do catálogo
    is_peca_ou_esquadria = (
        cat == "peca"
        or mod_data.get("tipo") == "esquadria"
        or (
            ("porta" in tipo.lower() or "janela" in tipo.lower())
            and not tipo.lower().startswith("peca_")
            and "porta_tempero" not in tipo.lower()
        )
    )

    # 1. Dimensões: catálogo base -> preferências do usuário para o tipo ou categoria
    if is_peca_ou_esquadria:
        L_mm = float(mod_data.get("largura", 800.0))
        A_mm = float(mod_data.get("altura", 720.0))
        P_mm = float(mod_data.get("profundidade", 550.0))
        rodape_mm = float(mod_data.get("rodape", 0.0))
    elif cat == "cama":
        # Camas preservam dimensões nominais do catálogo (ou default explícito do próprio tipo),
        # sem herdar medidas de balcões inferiores nem compartilhar categoria com outros modelos.
        L_mm = float(prefs.get_module_default(tipo, "largura", mod_data.get("largura", 800.0)))
        A_mm = float(prefs.get_module_default(tipo, "altura", mod_data.get("altura", 400.0)))
        P_mm = float(prefs.get_module_default(tipo, "profundidade", mod_data.get("profundidade", 2000.0)))
        rodape_mm = float(prefs.get_module_default(tipo, "rodape", mod_data.get("rodape", 0.0)))
    else:
        # Balcão com portas: se não houver largura salva explicitamente para
        # este tipo, calcula a partir do número de portas (400 mm cada).
        # Isso evita que o default do catálogo (800 mm = 2 portas) vença a regra.
        num_portas_cat = int(mod_data.get("num_portas", 2))
        tipo_defaults = prefs._data.get("module_defaults", {}).get(tipo, {})
        cat_defaults = prefs._data.get("module_defaults", {}).get(cat, {})
        if tipo in ("balcao", "aereo") and "largura" not in tipo_defaults and "largura" not in cat_defaults:
            L_mm = width_for_doors(num_portas_cat)
        else:
            L_mm = float(prefs.get_module_default(
                tipo, "largura",
                prefs.get_module_default(cat, "largura",
                                         mod_data.get("largura", 800.0))))

        A_mm = float(prefs.get_module_default(
            tipo, "altura",
            prefs.get_module_default(cat, "altura",
                                     mod_data.get("altura", 720.0))))
        P_mm = float(prefs.get_module_default(
            tipo, "profundidade",
            prefs.get_module_default(cat, "profundidade",
                                     mod_data.get("profundidade", 550.0))))
        if tipo == "balcao_canto_l":
            # O balcão de canto em L é quadrado por definição (1000 × 1000 mm):
            # não herda a profundidade padrão da categoria de balcões retos.
            L_mm = float(prefs.get_module_default(
                tipo, "largura", mod_data.get("largura", 1000.0)))
            P_mm = float(prefs.get_module_default(
                tipo, "profundidade", mod_data.get("profundidade", 1000.0)))
        rodape_mm = float(prefs.get_module_default(
            tipo, "rodape",
            prefs.get_module_default(cat, "rodape",
                                     mod_data.get("rodape", 0.0))))

    # 2. Padrões globais de marcenaria salvos pelo usuário
    esp_mm = float(prefs.get_global("espessura_caixa_mm", 15.0))
    esp_frentes_mm = float(prefs.get_global("espessura_frentes_mm", esp_mm))
    mat_caixa = str(prefs.get_global("material_caixa", "MDF Branco TX"))
    mat_frentes = str(prefs.get_global("material_frentes", "MDF Louro Freijó"))
    pux_tipo = str(prefs.get_global("puxador_tipo", "perfil"))
    pux_cor = str(prefs.get_global("puxador_cor", "anodizado_fosco"))
    pux_pos = str(prefs.get_global("puxador_pos", "superior"))
    perf_mod = str(prefs.get_global("perfil_modelo", "gola"))
    desc_perf = float(prefs.get_global("desconto_perfil_mm", 35.0))

    has_fundo_default = bool(mod_data.get("has_fundo", True))
    tipo_fundo_default = (
        str(prefs.get_global("tipo_fundo", "rasgo"))
        if has_fundo_default else "sem_fundo"
    )

    params: dict[str, Any] = dict(mod_data)
    params.update({
        "tipo": tipo,
        "largura": L_mm,
        "altura": A_mm,
        "profundidade": P_mm,
        "espessura": esp_mm,
        "rodape": rodape_mm,
        "material": (mat_caixa if mat_caixa.endswith("mm")
                     else f"{mat_caixa} {int(esp_mm)}mm"),
        "material_frentes": (mat_frentes if mat_frentes.endswith("mm")
                             else f"{mat_frentes} {int(esp_frentes_mm)}mm"),
        "espessura_frentes": esp_frentes_mm,
        "tem_fundo": has_fundo_default and (tipo_fundo_default != "sem_fundo"),
        "tipo_fundo": tipo_fundo_default,
        "esp_fundo": float(prefs.get_global("esp_fundo_mm", 6.0)),
        "recuo_fundo": float(prefs.get_global("recuo_fundo_mm", 10.0)),
        "prof_rasgo": float(prefs.get_global("prof_rasgo_mm", 5.0)),
        "folga_fundo": float(prefs.get_global("folga_fundo_mm", 2.0)),
        "folga_frentes_mm": float(prefs.get_global("folga_frentes_mm", 3.0)),
        "puxador_tipo": pux_tipo,
        "puxador_cor": pux_cor,
        "puxador_pos": pux_pos,
        "desconto_perfil": desc_perf,
        "perfil_modelo": perf_mod,
        "fita_caixa_modo": str(prefs.get_global("fita_caixa_modo", "frontal_1L")),
        "material_fita_caixa": prefs.get_global("material_fita_caixa", None),
        "gerar_furacao": bool(prefs.get_global("gerar_furacao", True)),
        "dispositivo_fixacao": str(
            prefs.get_global("dispositivo_fixacao", "minifix_cavilha")),
        "rot_z": 0.0,
    })

    # Bancada de pedra: as medidas padrão da categoria vencem o catálogo
    if "bancada" in tipo:
        params["esp_pedra"] = float(
            prefs.get_module_default("bancada", "esp_pedra", 20.0))
        params["altura_saia"] = float(
            prefs.get_module_default("bancada", "altura_saia", 40.0))
        params["altura_frontao"] = float(
            prefs.get_module_default("bancada", "altura_frontao", 100.0))
        params["tem_saia_esq"] = True
        params["tem_saia_dir"] = True
        params["tipo_cuba"] = mod_data.get("tipo_cuba", "inox_simples")
        params["has_cuba"] = params["tipo_cuba"] != "sem_cuba"
        params["posicao_cuba"] = "centro"
        params["tem_torneira"] = True
        params["canto_recorte"] = "arredondado"
        params["raio_canto_mm"] = 20.0
        params["tem_area_molhada"] = True
        if tipo in ("bancada_canto_l", "bancada_canto"):
            params["larg_asa_esq"] = float(mod_data.get("larg_asa_esq", mod_data.get("larg_asa", 600.0)))
            params["larg_asa_dir"] = float(mod_data.get("larg_asa_dir", mod_data.get("larg_asa", 600.0)))

    if tipo in ("balcao_misto", "rack_nicho_gaveta"):
        params["num_gavetas"] = int(mod_data.get("num_gavetas", 4 if tipo == "balcao_misto" else 1))
        params["largura_gaveteiro"] = float(
            mod_data.get("largura_gaveteiro", 450.0 if tipo == "balcao_misto" else 600.0))
        params["lado_gaveteiro"] = str(
            mod_data.get("lado_gaveteiro", "esquerda"))
        if tipo == "balcao_misto":
            params["num_portas"] = int(mod_data.get("num_portas", 2))
    elif mod_data.get("has_gavetas"):
        params["num_gavetas"] = int(mod_data.get("num_gavetas", 4))
    elif mod_data.get("has_portas"):
        params["num_portas"] = int(mod_data.get("num_portas", 2))

    # Balcão com portas: divisórias estruturais automáticas a partir de 3 portas
    if tipo == "balcao" and params.get("num_portas", 2) >= 3:
        params["num_divisoes"] = auto_divisoes_for_doors(int(params["num_portas"]))

    if mod_data.get("has_prateleiras"):
        params["num_prateleiras"] = int(mod_data.get("num_prateleiras", 1))
    if tipo == "nicho":
        params["num_divisoes"] = int(mod_data.get("num_divisoes", mod_data.get("divisoes_vert", 0)))
        params["divisoes_vert"] = params["num_divisoes"]
        params["divisoes_horiz"] = int(params.get("num_prateleiras", mod_data.get("divisoes_horiz", 1)))

    # Travessas de cozinhas inferiores
    ids_coz_inf = {
        "balcao", "gaveteiro", "balcao_misto", "balcao_pia",
        "balcao_canto", "balcao_canto_l", "porta_tempero", "balcao_forno",
    }
    if tipo in ids_coz_inf:
        params["travessa_frontal_em_pe"] = bool(prefs.get_global(
            "travessa_frontal_em_pe",
            mod_data.get("travessa_frontal_em_pe", False)))
        params["travessa_traseira_em_pe"] = bool(
            prefs.get_global("travessa_traseira_em_pe", False))
        params["larg_travessa_frontal_mm"] = float(prefs.get_global(
            "larg_travessa_frontal_mm",
            mod_data.get("larg_travessa_frontal_mm", 70.0)))
        params["larg_travessa_traseira_mm"] = float(prefs.get_global(
            "larg_travessa_traseira_mm",
            mod_data.get("larg_travessa_traseira_mm", 70.0)))
        params["recuo_porta_topo_mm"] = float(prefs.get_global(
            "recuo_porta_topo_mm",
            mod_data.get("recuo_porta_topo_mm", 50.0)))
        params["fita_travessas_modo"] = str(
            prefs.get_global("fita_travessas_modo", "frontal_1L"))
        if prefs.get_global("material_travessas") is not None:
            params["material_travessas"] = prefs.get_global("material_travessas")
        if prefs.get_global("esp_travessas_mm") is not None:
            params["esp_travessas_mm"] = prefs.get_global("esp_travessas_mm")
            params["espessura_travessas"] = params["esp_travessas_mm"]
        if prefs.get_global("material_fita_travessas") is not None:
            params["material_fita_travessas"] = prefs.get_global(
                "material_fita_travessas")

    if tipo == "balcao_forno":
        params["tem_gaveta"] = bool(mod_data.get("tem_gaveta", True))
        params["alt_gaveta_mm"] = float(mod_data.get("alt_gaveta_mm", 150.0))

    if tipo == "caixa_geladeira":
        params["alt_nicho_geladeira_mm"] = float(
            mod_data.get("alt_nicho_geladeira_mm", 1800.0))
        params["tipo_porta_superior"] = "duas_portas"
        params["num_portas"] = 2

    if tipo == "aereo_microondas":
        params["tipo_porta_superior"] = "basculante"
        params["num_portas"] = 1

    # Gavetas
    if (mod_data.get("has_gavetas")
            or tipo in ("gaveteiro", "balcao_misto", "torre_quente",
                        "gabinete_banheiro")):
        params["tipo_fundo_gaveta"] = "rasgo"
        params["folga_corredica_mm"] = 26.0
        params["esp_gaveta_mm"] = 15.0
        params["esp_fundo_gaveta_mm"] = 6.0

    # Tampo engrossado de marcenaria
    if tipo in ("peca_tampo_engrossado", "tampo_engrossado"):
        params["esp_chapa"] = float(mod_data.get("esp_chapa", 18.0))
        params["qtd_engrosso"] = int(mod_data.get("qtd_engrosso", 1))
        params["larg_engrosso"] = float(mod_data.get("larg_engrosso", 70.0))
        params["tipo_engrosso"] = str(
            mod_data.get("tipo_engrosso", "3_lados"))
        params["fechar_embaixo"] = bool(
            mod_data.get("fechar_embaixo", False))
        params["snap_parede"] = str(
            mod_data.get("snap_parede", "auto"))

    return params

