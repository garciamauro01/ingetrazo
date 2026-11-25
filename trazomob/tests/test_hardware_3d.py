# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes de integração do modelo/representação 3D de ferragens."""

from __future__ import annotations

from PySide6.QtGui import QVector3D

from core.scene import Scene
from trazomob.builders.cabinet import CabinetBuilder
from trazomob.builders.hardware_geometry import is_hardware_group
from trazomob.domain.hardware import deserialize_hardware
from trazomob.production.parts import extract_parts


def _params_balcao() -> dict:
    return {
        "tipo": "balcao",
        "largura": 800,
        "altura": 720,
        "profundidade": 550,
        "espessura": 15,
        "rodape": 100,
        "material": "MDF Branco TX 15mm",
        "num_portas": 2,
        "num_divisoes": 1,
        "num_prateleiras": 0,
        "puxador_tipo": "alca",
        "dispositivo_fixacao": "minifix_cavilha",
    }


def test_module_persiste_ferragens_e_exclui_do_cutlist():
    scene = Scene()
    params = _params_balcao()
    params["num_gavetas"] = 2
    mod = CabinetBuilder.build_module_group(params, offset=(0.0, 0.0, 0.0))
    scene.groups.append(mod)

    # 1. Ext tem os dados de ferragens serializados
    hw = deserialize_hardware(mod.ext.get("trazomob_hardware", []))
    keys = {it.key for it in hw}
    assert "dobradica_35mm" in keys
    assert "minifix_kit" in keys
    assert "pes_nivelador" not in keys

    # 2. Há representação 3D marcada como hardware
    hw_children = [c for c in mod.children if is_hardware_group(c)]
    assert hw_children
    assert all(c.ext["trazomob"]["kind"] == "hardware" for c in hw_children)

    # 3. extract_parts não exporta as representações 3D como peças
    parts = extract_parts(scene)
    nomes = [p["nome"] for p in parts]
    assert not any("Ferragem -" in nome for nome in nomes)
    # Todas as peças pertencem ao mesmo módulo e trazem as ferragens do módulo
    assert parts
    assert len({p["_module_key"] for p in parts}) == 1
    assert all("module_hardware" in p for p in parts)


def test_gaveteiro_gera_corredica_e_pes():
    params = _params_balcao()
    params.update({"tipo": "gaveteiro", "num_portas": 0, "num_gavetas": 3})
    scene = Scene()
    mod = CabinetBuilder.build_module_group(params, offset=(0.0, 0.0, 0.0))
    scene.groups.append(mod)

    hw = deserialize_hardware(mod.ext.get("trazomob_hardware", []))
    keys = {it.key for it in hw}
    assert "corredica_50" in keys
    assert "pes_nivelador" not in keys
    runners = [c for c in mod.children
               if is_hardware_group(c) and "Corrediça" in c.name]
    assert len(runners) == 3
    assert all(c.ext["trazomob"].get("linked_piece") for c in runners)


def test_ferragens_acompanham_abertura_das_portas():
    from trazomob.interaction.interact import CabinetInteract

    scene = Scene()
    mod = CabinetBuilder.build_module_group(_params_balcao(), offset=(0, 0, 0))
    scene.groups.append(mod)

    # 1. Canecos móveis vinculados às portas
    caneco_groups = [c for c in mod.children
                     if is_hardware_group(c) and "Dobradiças" in c.name and "Calço" not in c.name]
    assert caneco_groups
    before_canecos = {
        g.name: tuple(QVector3D(v.position) for v in g.mesh.vertices)
        for g in caneco_groups
    }

    # 2. Calços fixos na lateral (sem linked_piece)
    calco_groups = [c for c in mod.children
                    if is_hardware_group(c) and "Dobradiças Calço" in c.name]
    assert calco_groups
    before_calcos = {
        g.name: tuple(QVector3D(v.position) for v in g.mesh.vertices)
        for g in calco_groups
    }

    assert CabinetInteract.set_module_open_fraction(mod, 0.5, scene, None)

    # Canecos se movem solidariamente com as portas
    for g in caneco_groups:
        target = g.ext["trazomob"].get("linked_piece")
        assert target
        assert any(
            a.position != b
            for a, b in zip(g.mesh.vertices, before_canecos[g.name])
        ), f"{g.name} deveria mover com {target}"
        target_group = next(c for c in mod.children if c.name == target)
        assert target_group.ext.get("is_open", False) is True

    # Calços permanecem 100% fixos na lateral da caixa
    for g in calco_groups:
        assert g.ext["trazomob"].get("linked_piece") is None
        assert all(
            a.position == b
            for a, b in zip(g.mesh.vertices, before_calcos[g.name])
        ), f"{g.name} deveria permanecer fixo na lateral"


def test_ferragens_seguem_portas_apos_copiar_modulo():
    """Regressão: copiar/colar um módulo não deve perder o vínculo dobradiça↔porta.

    O vínculo usa o nome serializável (``linked_piece``); se guardasse uma
    referência de objeto em ``ext``, o ``copy_group``/``deepcopy`` a quebraria.
    """
    from core.group import copy_group
    from trazomob.interaction.interact import CabinetInteract

    scene = Scene()
    mod = CabinetBuilder.build_module_group(_params_balcao(), offset=(0, 0, 0))
    scene.groups.append(mod)

    copia = copy_group(mod)
    scene.groups.append(copia)

    canecos = [c for c in copia.children
               if is_hardware_group(c) and "Dobradiças" in c.name and "Calço" not in c.name]
    assert canecos
    before = {g.name: tuple(QVector3D(v.position) for v in g.mesh.vertices) for g in canecos}

    assert CabinetInteract.set_module_open_fraction(copia, 0.5, scene, None)

    for g in canecos:
        target = g.ext["trazomob"].get("linked_piece")
        assert target
        assert any(
            a.position != b
            for a, b in zip(g.mesh.vertices, before[g.name])
        ), f"{g.name} deveria seguir a porta {target} na cópia do módulo"


def test_corredicas_acompanham_abertura_das_gavetas():
    from trazomob.interaction.interact import CabinetInteract

    params = _params_balcao()
    params.update({"tipo": "gaveteiro", "num_portas": 0, "num_gavetas": 3})
    scene = Scene()
    mod = CabinetBuilder.build_module_group(params, offset=(0, 0, 0))
    scene.groups.append(mod)

    runners = [c for c in mod.children
               if is_hardware_group(c) and "Corrediças" in c.name]
    assert len(runners) == 3
    before = {
        r.name: tuple(v.position for v in r.mesh.vertices)
        for r in runners
    }

    assert CabinetInteract.set_module_open_fraction(mod, 0.5, scene, None)

    for r in runners:
        target = r.ext["trazomob"]["linked_piece"]
        assert any(
            a.position != b
            for a, b in zip(r.mesh.vertices, before[r.name])
        ), f"{r.name} deveria mover com {target}"


def test_relatorio_contem_secao_ferragens():
    from trazomob.production.report import generate_project_html_report

    scene = Scene()
    scene.groups.append(
        CabinetBuilder.build_module_group(_params_balcao(), offset=(0, 0, 0))
    )
    parts = extract_parts(scene)
    html = generate_project_html_report(parts, project_name="Teste Ferragens")
    assert "Ferragens" in html
    assert "Dobradiça" in html
    assert "minifix" in html.lower() or "Minifix" in html


def test_balcao_misto_corredicas_ficam_apenas_no_lado_do_gaveteiro():
    """Garante que no balcão misto as corrediças 3D (interna, intermediária e trilho fixo)
    fiquem restritas ao vão real do gaveteiro (esquerda ou direita), nunca na lateral oposta das portas.
    """
    from trazomob.interaction.interact import CabinetInteract

    for lado_gav in ("esquerda", "direita"):
        params = {
            "tipo": "balcao_misto",
            "largura": 1200.0,
            "altura": 720.0,
            "profundidade": 550.0,
            "espessura": 15.0,
            "rodape": 100.0,
            "largura_gaveteiro": 450.0,
            "lado_gaveteiro": lado_gav,
            "num_gavetas": 4,
            "num_portas": 2,
        }
        mod = CabinetBuilder.build_module_group(params, offset=(0.0, 0.0, 0.0))
        hw_groups = [
            c for c in mod.children
            if is_hardware_group(c) and any(k in c.name for k in ("Corrediças", "Guia Telescópica", "Trilho Fixo"))
        ]
        assert len(hw_groups) == 4 * 3  # 3 estágios por gaveta

        # Coordenadas X de todos os vértices dos trilhos/corrediças
        xs_hw = [v.position.x() for g in hw_groups for v in g.mesh.vertices]
        if lado_gav == "esquerda":
            # O gaveteiro ocupa de X=0 até X=0.45m; nenhum trilho pode estar perto de X=1.20m
            assert max(xs_hw) < 0.48, f"Trilho vazou para o lado das portas (max_x={max(xs_hw):.3f}m)"
        else:
            # O gaveteiro ocupa de X=0.75m até X=1.20m; nenhum trilho pode estar perto de X=0.0m
            assert min(xs_hw) > 0.72, f"Trilho vazou para o lado das portas (min_x={min(xs_hw):.3f}m)"

        # Testa a cinemática de 3 estágios ao abrir o módulo
        trilhos_fixos = [g for g in hw_groups if "Trilho Fixo" in g.name]
        guias_meio = [g for g in hw_groups if "Guia Telescópica" in g.name]
        corredicas_int = [g for g in hw_groups if "Corrediças Gaveta" in g.name]

        y_fixo_antes = [v.position.y() for v in trilhos_fixos[0].mesh.vertices]
        y_meio_antes = min(v.position.y() for v in guias_meio[0].mesh.vertices)
        y_int_antes = min(v.position.y() for v in corredicas_int[0].mesh.vertices)

        CabinetInteract.set_module_open_fraction(mod, 1.0, None, None)

        y_fixo_depois = [v.position.y() for v in trilhos_fixos[0].mesh.vertices]
        y_meio_depois = min(v.position.y() for v in guias_meio[0].mesh.vertices)
        y_int_depois = min(v.position.y() for v in corredicas_int[0].mesh.vertices)

        # Trilho fixo não se move
        assert y_fixo_antes == y_fixo_depois
        # Guia intermediária avança metade (50%) do curso da corrediça interna
        desloc_meio = abs(y_meio_depois - y_meio_antes)
        desloc_int = abs(y_int_depois - y_int_antes)
        assert desloc_int > 0.30
        assert abs(desloc_meio - desloc_int * 0.5) < 1e-4

