# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Entidades **Ambiente** e **Pavimento** do TrazoMob.

Um **Ambiente** é um contêiner lógico que agrupa:
* paredes (sólidos manifold já existentes)
* piso (laje/contrapiso)
* teto/forro
* lista de módulos paramétricos pertencentes a esse ambiente

Um **Pavimento** é um agrupador de ambientes no mesmo nível Z (térreo, 1º andar...).
Permite alternar visibilidade de todo o andar e calcular área total.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Tuple

from PySide6.QtGui import QVector3D

from core.group import Group
from core.mesh import Mesh

if TYPE_CHECKING:
    from core.history import Command

from ..domain.schema import (
    KIND_AMBIENTE,
    KIND_PAVIMENTO,
    KIND_MODULE,
    KIND_WALL,
    KIND_FLOOR,
    KIND_CEILING,
    is_kind,
    set_ambiente_data,
    set_pavimento_data,
    update_ambiente_data,
    update_pavimento_data,
    set_floor_data,
    set_ceiling_data,
    ambiente_params,
    pavimento_params,
)


# ---------------------------------------------------------------------------
# Helpers de tipo
# ---------------------------------------------------------------------------

def is_ambiente(group: Any) -> bool:
    """Diz se o grupo é um ambiente do TrazoMob."""
    return is_kind(group, KIND_AMBIENTE)


def is_pavimento(group: Any) -> bool:
    """Diz se o grupo é um pavimento do TrazoMob."""
    return is_kind(group, KIND_PAVIMENTO)


# ---------------------------------------------------------------------------
# Iteradores de árvore
# ---------------------------------------------------------------------------

def iter_ambientes(groups: Iterable[Any]) -> Iterable[Group]:
    """Percorre a árvore (inclui grupos aninhados) e yield apenas ambientes."""
    for g in groups:
        if is_ambiente(g):
            yield g
        for child in getattr(g, "children", None) or []:
            yield from iter_ambientes([child])


def iter_pavimentos(groups: Iterable[Any]) -> Iterable[Group]:
    """Percorre a árvore e yield apenas pavimentos."""
    for g in groups:
        if is_pavimento(g):
            yield g
        for child in getattr(g, "children", None) or []:
            yield from iter_pavimentos([child])


def iter_modulos_do_ambiente(ambiente: Group) -> Iterable[Group]:
    """Yield módulos paramétricos que são filhos diretos do ambiente."""
    for child in getattr(ambiente, "children", None) or []:
        if is_kind(child, KIND_MODULE):
            yield child


def iter_paredes_do_ambiente(ambiente: Group) -> Iterable[Group]:
    """Yield paredes que são filhas diretas do ambiente."""
    for child in getattr(ambiente, "children", None) or []:
        if is_kind(child, KIND_WALL):
            yield child


def iter_pisos_do_ambiente(ambiente: Group) -> Iterable[Group]:
    """Yield pisos que são filhos diretos do ambiente."""
    for child in getattr(ambiente, "children", None) or []:
        if is_kind(child, KIND_FLOOR):
            yield child


def iter_tetos_do_ambiente(ambiente: Group) -> Iterable[Group]:
    """Yield tetos/forros que são filhos diretos do ambiente."""
    for child in getattr(ambiente, "children", None) or []:
        if is_kind(child, KIND_CEILING):
            yield child


def ambiente_do_modulo(modulo: Group) -> Optional[Group]:
    """Sobe na hierarquia até encontrar o ambiente pai do módulo."""
    # Em IngeTrazo, o pai não é exposto diretamente; varremos a cena.
    # Quem chama deve passar a cena ou a lista de ambientes.
    return None  # Implementado via busca na cena se necessário


# ---------------------------------------------------------------------------
# Cálculos de geometria
# ---------------------------------------------------------------------------

def _bounds_do_grupo(group: Group) -> Optional[Tuple[float, float, float, float, float, float]]:
    """Retorna (minx, maxx, miny, maxy, minz, maxz) em metros do grupo e filhos."""
    xs, ys, zs = [], [], []
    for child in getattr(group, "children", None) or []:
        mesh = getattr(child, "mesh", None)
        if mesh and hasattr(mesh, "vertices"):
            xform = getattr(child, "xform", None)
            for v in mesh.vertices:
                p = xform.map(v.position) if xform is not None else v.position
                xs.append(p.x())
                ys.append(p.y())
                zs.append(p.z())
        # recursivo
        b = _bounds_do_grupo(child)
        if b:
            xs.extend([b[0], b[1]])
            ys.extend([b[2], b[3]])
            zs.extend([b[4], b[5]])
    if not xs:
        return None
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def calcular_area_ambiente(ambiente: Group) -> float:
    """Área do ambiente em m² (projeção XY do piso ou bounds das paredes)."""
    # Tenta usar o piso primeiro
    for piso in iter_pisos_do_ambiente(ambiente):
        mesh = getattr(piso, "mesh", None)
        if mesh and hasattr(mesh, "vertices") and mesh.vertices:
            # Projeção XY da malha do piso
            xs = [v.position.x() for v in mesh.vertices]
            ys = [v.position.y() for v in mesh.vertices]
            return (max(xs) - min(xs)) * (max(ys) - min(ys))
    # Fallback: bounds das paredes
    b = _bounds_do_grupo(ambiente)
    if b:
        return (b[1] - b[0]) * (b[3] - b[2])
    return 0.0


def calcular_pe_direito_ambiente(ambiente: Group) -> float:
    """Pé-direito do ambiente em metros (Z do teto - Z do piso)."""
    z_piso = None
    z_teto = None
    for piso in iter_pisos_do_ambiente(ambiente):
        mesh = getattr(piso, "mesh", None)
        if mesh and mesh.vertices:
            zs = [v.position.z() for v in mesh.vertices]
            z_piso = max(zs)  # topo da laje
            break
    for teto in iter_tetos_do_ambiente(ambiente):
        mesh = getattr(teto, "mesh", None)
        if mesh and mesh.vertices:
            zs = [v.position.z() for v in mesh.vertices]
            z_teto = min(zs)  # base do forro
            break
    if z_piso is not None and z_teto is not None:
        return max(0.0, z_teto - z_piso)
    # Fallback: maior altura entre as paredes do ambiente. Uma parede baixa
    # não pode definir o pé-direito das demais.
    alturas = []
    for parede in iter_paredes_do_ambiente(ambiente):
        mesh = getattr(parede, "mesh", None)
        if mesh and mesh.vertices:
            zs = [v.position.z() for v in mesh.vertices]
            alturas.append(max(zs) - min(zs))
    if alturas:
        return max(alturas)
    return 2.7  # padrão


# ---------------------------------------------------------------------------
# Builder de Ambiente a partir de planta 2D (integração com wall_plan_2d)
# ---------------------------------------------------------------------------

class AmbienteBuilder:
    """Constrói o grupo Ambiente com paredes, piso, teto e metadados."""

    @staticmethod
    def build_ambiente_group(
        nome: str,
        paredes: List[Group],
        piso: Optional[Group],
        teto: Optional[Group],
        pavimento_nome: str = "Térreo",
        z_base: float = 0.0,
        pe_direito: float = 2.7,
    ) -> Group:
        """
        Cria o grupo Ambiente adotando paredes, piso e teto como filhos.

        As paredes já vêm do ``WallPlan2D.build_3d_group`` (ou similar).
        Piso e teto vêm do ``wall_mesh_builder``.
        """
        # Cria o grupo mestre do ambiente
        master = Group(Mesh(), name=nome)

        filhos_iniciais = list(paredes)

        # Piso
        if piso is not None:
            filhos_iniciais.append(piso)
            schema_set = getattr(piso, "ext", None)
            if isinstance(schema_set, dict):
                set_floor_data(piso, {"ambiente": nome})

        # Teto
        if teto is not None:
            filhos_iniciais.append(teto)
            schema_set = getattr(teto, "ext", None)
            if isinstance(schema_set, dict):
                set_ceiling_data(teto, {"ambiente": nome})

        master.adopt(filhos_iniciais)

        # Metadados do ambiente
        area = calcular_area_ambiente(master)
        pe_dir = calcular_pe_direito_ambiente(master) or pe_direito

        set_ambiente_data(master, {
            "nome": nome,
            "pavimento": pavimento_nome,
            "z_base": z_base,
            "pe_direito": pe_dir,
            "area_m2": round(area, 2),
            "visivel": True,
        })

        return master

    @staticmethod
    def ensure_pavimento(scene_groups: List[Group], nome: str, z_base: float = 0.0) -> Group:
        """Garante que existe um grupo Pavimento com esse nome; cria se não houver."""
        for g in scene_groups:
            if is_pavimento(g):
                params = pavimento_params(g)
                if params.get("nome") == nome:
                    if z_base > 0 and params.get("z_base", 0.0) == 0.0:
                        update_pavimento_data(g, {"z_base": z_base})
                    return g
        # Cria novo e adiciona à lista da cena se fornecida
        pav = Group(Mesh(), name=nome)
        set_pavimento_data(pav, {"nome": nome, "z_base": z_base, "visivel": True})
        if scene_groups is not None and pav not in scene_groups:
            scene_groups.append(pav)
        return pav

    @classmethod
    def criar_pavimento(cls, scene_groups: List[Group], nome: str, z_base: float = 0.0) -> Group:
        """Alias para criação explícita de pavimento."""
        return cls.ensure_pavimento(scene_groups, nome, z_base=z_base)

    @staticmethod
    def adicionar_ao_pavimento(pavimento: Group, ambiente: Group) -> None:
        """Adota o ambiente no pavimento (sem duplicar se já estiver)."""
        atuais = list(getattr(pavimento, "children", None) or [])
        if ambiente not in atuais:
            atuais.append(ambiente)
            pavimento.adopt(atuais)


# ---------------------------------------------------------------------------
# Comando de agrupamento de módulos em ambiente (para a sidebar)
# ---------------------------------------------------------------------------

def build_ambiente_command(
    modulos: List[Group],
    nome: str,
    pavimento_nome: str = "Térreo",
) -> Optional["Command"]:
    """
    Cria um comando que agrupa os módulos selecionados num novo Ambiente.

    Reutiliza ``MakeNestedGroupCommand`` do core e marca como ambiente.
    """
    if len(modulos) < 1:
        return None

    from core.history import MakeNestedGroupCommand

    # Cria um grupo vazio que vai virar o ambiente
    container = Group(Mesh(), name=nome)
    cmd = MakeNestedGroupCommand(modulos, container=container, name=nome)

    # Wrapper para marcar como ambiente após executar
    class _AmbienteWrapper:
        def __init__(self, inner_cmd, pavimento_nome):
            self.inner = inner_cmd
            self.pavimento_nome = pavimento_nome
            self.container = None

        def do(self, scene):
            self.inner.do(scene)
            self.container = self.inner.container
            set_ambiente_data(self.container, {
                "nome": nome,
                "pavimento": self.pavimento_nome,
                "visivel": True,
            })

        def undo(self, scene):
            self.inner.undo(scene)

    return _AmbienteWrapper(cmd, pavimento_nome)


def build_dissolve_ambiente_command(ambiente: Group) -> Optional["Command"]:
    """Cria comando para dissolver o ambiente, devolvendo filhos ao nível do pai."""
    if not is_ambiente(ambiente):
        return None

    from core.history import ExplodeGroupCommand

    class _DissolveWrapper:
        def __init__(self, inner_cmd):
            self.inner = inner_cmd

        def do(self, scene):
            self.inner.do(scene)

        def undo(self, scene):
            self.inner.undo(scene)

    return _DissolveWrapper(ExplodeGroupCommand(ambiente))


# ---------------------------------------------------------------------------
# Utilitários de visibilidade
# ---------------------------------------------------------------------------

def set_ambiente_visivel(ambiente: Group, visivel: bool) -> None:
    """Alterna visibilidade do ambiente e propaga para filhos."""
    update_ambiente_data(ambiente, {"visivel": visivel})
    if hasattr(ambiente, "hidden"):
        ambiente.hidden = not visivel
    for child in getattr(ambiente, "children", None) or []:
        if hasattr(child, "hidden"):
            child.hidden = not visivel
        child.layer = "Ambientes" if visivel else "Hidden"


def set_pavimento_visivel(pavimento: Group, visivel: bool) -> None:
    """Alterna visibilidade do pavimento e de todos seus ambientes/filhos."""
    update_pavimento_data(pavimento, {"visivel": visivel})
    if hasattr(pavimento, "hidden"):
        pavimento.hidden = not visivel
    for item in getattr(pavimento, "children", None) or []:
        if hasattr(item, "hidden"):
            item.hidden = not visivel
        item.layer = "Ambientes" if visivel else "Hidden"
        if is_ambiente(item):
            set_ambiente_visivel(item, visivel)


# ---------------------------------------------------------------------------
# Exportação para cutlist / relatórios
# ---------------------------------------------------------------------------

def resumo_ambiente(ambiente: Group) -> Dict[str, Any]:
    """Dicionário pronto para relatório/cutlist filtrado por ambiente."""
    params = ambiente_params(ambiente)
    modulos = list(iter_modulos_do_ambiente(ambiente))
    return {
        "nome": params.get("nome", ambiente.name),
        "pavimento": params.get("pavimento", ""),
        "area_m2": params.get("area_m2", 0.0),
        "pe_direito": params.get("pe_direito", 0.0),
        "qtd_modulos": len(modulos),
        "modulos": [m.name for m in modulos],
    }
