# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Testes automatizados para o sistema de internacionalização (i18n) do TrazoMob."""
from __future__ import annotations

import json
import os

from trazomob.domain.catalog import MODULE_CATALOG
from trazomob.domain.i18n import clear_i18n_cache, get_lang, tr


def test_i18n_json_files_valid():
    """Garante que es.json e en.json existem, são JSON válidos e possuem as mesmas chaves."""
    base_dir = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "i18n")
    )
    es_path = os.path.join(base_dir, "es.json")
    en_path = os.path.join(base_dir, "en.json")

    assert os.path.isfile(es_path), "Arquivo es.json não encontrado"
    assert os.path.isfile(en_path), "Arquivo en.json não encontrado"

    with open(es_path, "r", encoding="utf-8") as f:
        es_data = json.load(f)
    with open(en_path, "r", encoding="utf-8") as f:
        en_data = json.load(f)

    assert len(es_data) >= 200
    assert len(en_data) >= 200
    assert set(es_data.keys()) == set(en_data.keys()), "Chaves divergentes entre es.json e en.json"


def test_tr_translations_pt_es_en(monkeypatch):
    """Valida a tradução dinâmica entre Português (pt-BR), Espanhol (es) e Inglês (en)."""
    import core.i18n as core_i18n

    # 1. Português (nativo / fallback direto)
    monkeypatch.setattr(core_i18n, "current_language", lambda: "pt-BR")
    clear_i18n_cache()
    assert get_lang() == "pt-BR"
    assert tr("Medidas") == "Medidas"
    assert tr("Largura:") == "Largura:"
    assert tr("Balcão de Canto Reto (L Cego)") == "Balcão de Canto Reto (L Cego)"

    # 2. Espanhol (es)
    monkeypatch.setattr(core_i18n, "current_language", lambda: "es")
    clear_i18n_cache()
    assert get_lang() == "es"
    assert tr("Largura:") == "Ancho:"
    assert tr("Altura:") == "Altura:"
    assert tr("Profundidade:") == "Profundidad:"
    assert tr("Balcão de Canto Reto (L Cego)") == "Módulo Bajo Rincón Recto (Ciego)"
    assert tr("Régua Fechamento:") == "Regleta de Cierre:"

    # 3. Inglês (en)
    monkeypatch.setattr(core_i18n, "current_language", lambda: "en")
    clear_i18n_cache()
    assert get_lang() == "en"
    assert tr("Medidas") == "Dimensions"
    assert tr("Largura:") == "Width:"
    assert tr("Altura:") == "Height:"
    assert tr("Profundidade:") == "Depth:"
    assert tr("Balcão de Canto Reto (L Cego)") == "Blind Corner Base Cabinet"
    assert tr("Régua Fechamento:") == "Filler Strip:"

    # 4. Fallback seguro para chaves não cadastradas e interpolação kwargs
    assert tr("Texto Inexistente {n}", n=42) == "Texto Inexistente 42"


def test_catalog_categories_and_modules_translated(monkeypatch):
    """Verifica que todas as categorias principais do MODULE_CATALOG possuem tradução em es e en."""
    import core.i18n as core_i18n

    for lang in ("es", "en"):
        monkeypatch.setattr(core_i18n, "current_language", lambda lang=lang: lang)
        clear_i18n_cache()
        for cat_name, items in MODULE_CATALOG.items():
            # Categoria traduzida não deve ser vazia
            translated_cat = tr(cat_name)
            assert isinstance(translated_cat, str) and len(translated_cat) > 0
            for item in items:
                nome = item.get("nome", "")
                if nome:
                    assert len(tr(nome)) > 0


def test_build_all_catalog_modules_smoke():
    """Garante que TODOS os módulos do MODULE_CATALOG constroem via CabinetBuilder.build_module_group sem erro de assinatura."""
    from trazomob.builders.cabinet import CabinetBuilder
    from trazomob.ui.module_ribbon import build_default_module_params

    for cat_name, items in MODULE_CATALOG.items():
        for item in items:
            params = build_default_module_params(item)
            grp = CabinetBuilder.build_module_group(params)
            assert grp is not None, f"Falha ao construir módulo {item['id']} ({cat_name})"


def test_tower_insertion_floor_to_top_guide():
    """Garante que as Torres de Eletros vão do chão (Z=0) até a guia Topo Aéreos / Torres da régua ativa."""
    from PySide6.QtGui import QVector3D

    from trazomob.domain.module_geometry import get_module_carcass_bounds
    from trazomob.ui.module_ribbon import TrazoMobModuleRibbonBar
    from trazomob.wall.guides import WallGuideRulerManager
    from trazomob.wall.selection import WallSelectionManager

    ruler_mgr = WallGuideRulerManager.get_instance()
    orig_preset = ruler_mgr.active_preset_name
    try:
        ruler_mgr.set_active_preset("Cozinha")
        ruler_mgr.reset_preset_to_default("Cozinha")
        assert ruler_mgr.get_tower_top_z_mm() == 2200.0

        # Simula cena e parede selecionada com um slot armado na faixa inferior (150mm a 900mm) ou aérea (1500mm a 2200mm)
        from core.scene import Scene

        class DummyHistory:
            def execute(self, cmd):
                cmd.do(self.scene)

        class DummyViewport:
            def __init__(self):
                self.scene = Scene()
                self.history = DummyHistory()
                self.history.scene = self.scene
                self.camera = None

            def notify_scene_changed(self):
                pass

            def update(self):
                pass

        class DummyWallFace:
            def __init__(self):
                self.normal = QVector3D(0, 1, 0)
                self.center = QVector3D(1.5, 0.0, 1.3)
                self.face = object()
                self.wall_group = None

        vp = DummyViewport()
        wall_mgr = WallSelectionManager.get_instance(vp)
        wall_mgr.selected_wall_face = DummyWallFace()
        # Mesmo que o usuário tenha clicado no vão aéreo (1.5m a 2.2m, prof=350mm),
        # a torre deve ir do chão (0.0m) até 2.2m (2200mm) e manter sua profundidade (580/600mm)!
        wall_mgr.active_placement_slot = {
            "z_base": 1.50,
            "z_top": 2.20,
            "height_mm": 700.0,
            "category": "aereo",
            "default_depth_mm": 350.0,
            "width_m": 0.80,
            "depth_m": 0.35,
            "center_pt": QVector3D(1.0, 0.0, 1.50),
            "u_pos": -1.0,
            "n_dir": QVector3D(0, 1, 0),
            "u_dir": QVector3D(-1, 0, 0),
            "box_vertices": {},
            "wall_face": wall_mgr.selected_wall_face,
        }

        ribbon = TrazoMobModuleRibbonBar.__new__(TrazoMobModuleRibbonBar)
        ribbon.viewport = vp
        ribbon.sidebar_panel = None

        for tower_item in MODULE_CATALOG["Cozinha — Torres"]:
            vp.scene.groups.clear()
            ribbon.insert_module_into_scene(tower_item)
            assert len(vp.scene.groups) == 1
            placed_mod = vp.scene.groups[0]
            mod_meta = placed_mod.ext["trazomob_module"]
            assert float(mod_meta["altura"]) == 2200.0
            # Garante que não herdou a profundidade aérea (350mm) do slot clicado
            assert float(mod_meta["profundidade"]) >= 550.0
            b = get_module_carcass_bounds(placed_mod)
            assert b is not None
            assert abs(b[4] - 0.0) < 1e-3, f"Base da torre deveria estar no chão (0.0), mas está em {b[4]}"
            assert abs(b[5] - 2.20) < 1e-3, f"Topo da torre deveria estar na guia (2.20m), mas está em {b[5]}"
    finally:
        ruler_mgr.set_active_preset(orig_preset)


def test_peca_portas_correr_2_to_4_doors():
    """Garante a construção correta do Conjunto de Portas de Correr Avulsas para 2, 3 e 4 portas,
    validando largura idêntica das folhas, transpasse exato de 30mm, planos Y dos trilhos e lado dos puxadores."""
    from trazomob.builders.cabinet import CabinetBuilder
    from trazomob.ui.module_ribbon import build_default_module_params

    item = next(
        m for m in MODULE_CATALOG["Peças Avulsas / Componentes"] if m["id"] == "peca_portas_correr"
    )
    assert item is not None

    L_mm = 2000.0
    L_m = L_mm / 1000.0
    transpasse_mm = 30.0
    transpasse_m = transpasse_mm / 1000.0

    for pux_tipo in ("alca", "perfil"):
        for n_portas in (2, 3, 4):
            params = build_default_module_params(item)
            params["largura"] = L_mm
            params["altura"] = 2200.0
            params["profundidade"] = 65.0
            params["num_portas"] = n_portas
            params["transpasse_mm"] = transpasse_mm
            params["puxador_tipo"] = pux_tipo
            # Mantém puxador_pos como veio do build_default_module_params ("superior"/"padrao")
            # para garantir que o construtor coloque na lateral/extensão das folhas de correr!

            grp = CabinetBuilder.build_module_group(params)
            assert grp is not None
            assert grp.layer == "PLANEJADOS"

            from trazomob.builders.hardware_geometry import is_hardware_group
            folhas = [c for c in grp.children
                      if "Porta Correr" in getattr(c, "name", "") and not is_hardware_group(c)]
            trilhos = [c for c in grp.children
                       if "Trilho" in getattr(c, "name", "") and not is_hardware_group(c)]
            assert len(folhas) == n_portas, f"Esperado {n_portas} folhas, obteve {len(folhas)}"
            assert len(trilhos) == 2

            # 1. Verifica que todas as folhas têm exatamente a mesma largura total 3D (nenhuma porta menor que a outra!)
            comprimentos_corte = [f.ext["trazomob"]["comprimento"] for f in folhas]
            assert len(set(comprimentos_corte)) == 1
            if n_portas in (2, 4) or pux_tipo != "perfil":
                larguras_corte = [f.ext["trazomob"]["largura"] for f in folhas]
                assert len(set(larguras_corte)) == 1, (
                    f"[{n_portas}P / {pux_tipo}] As folhas deveriam ter largura de corte idêntica, mas tiveram: {larguras_corte}"
                )
            else:
                # Em 3 portas com perfil integrado, as folhas 1 e 3 descontam 1 perfil e a folha central 2 desconta 2 perfis
                assert abs(folhas[0].ext["trazomob"]["largura"] - folhas[2].ext["trazomob"]["largura"]) < 0.2
                assert folhas[1].ext["trazomob"]["largura"] < folhas[0].ext["trazomob"]["largura"]

            # Extrai bounding box de cada folha e identifica a posição X do puxador/perfil de cada folha
            bounds_folhas = []
            handle_xs_folhas = []
            for f in folhas:
                verts = f.mesh.vertices
                xs = [v.position.x() for v in verts]
                min_x, max_x = min(xs), max(xs)
                ys = [v.position.y() for v in verts]
                board_back_y = max(ys)
                if pux_tipo == "perfil":
                    # No perfil integrado, a aba traseira de fixação do perfil avança em +Y além da chapa de MDF
                    back_flange_xs = [v.position.x() for v in verts if v.position.y() > board_back_y - 0.0005]
                    assert back_flange_xs, f"Nenhum vértice de perfil encontrado para {f.name}"
                    handle_xs = (min(back_flange_xs), max(back_flange_xs))
                else:
                    # No puxador alça/ponto/cava, os vértices do puxador avançam em -Y à frente da chapa
                    esp_frente_m = float(f.ext["trazomob"]["espessura"]) / 1000.0
                    front_handle_xs = [v.position.x() for v in verts if v.position.y() < board_back_y - esp_frente_m - 0.001]
                    assert front_handle_xs, f"Nenhum vértice de puxador encontrado para {f.name} ({pux_tipo})"
                    handle_xs = (min(front_handle_xs), max(front_handle_xs))
                bounds_folhas.append((min_x, max_x, board_back_y))
                handle_xs_folhas.append(handle_xs)

            # Todas as folhas têm a mesma largura total (max_x - min_x), dentro de 0.5mm (folga de 0.2mm do perfil)
            widths_3d = [b[1] - b[0] for b in bounds_folhas]
            assert max(widths_3d) - min(widths_3d) < 1e-3, (
                f"[{n_portas}P / {pux_tipo}] Larguras 3D divergentes entre folhas: {widths_3d}"
            )

            # 2. Verifica posicionamento X, transpasse de 30mm e planos Y (frontal vs traseiro)
            if n_portas == 2:
                expected_w = (L_m + transpasse_m) / 2.0
                assert abs((bounds_folhas[0][1] - bounds_folhas[0][0]) - expected_w) < 1e-3
                # Transpasse entre Folha 1 (Esq) e Folha 2 (Dir) == 30mm
                overlap_1_2 = bounds_folhas[0][1] - bounds_folhas[1][0]
                assert abs(overlap_1_2 - transpasse_m) < 1e-3, f"Transpasse esperado {transpasse_m}, obteve {overlap_1_2}"
                # Folha 1 no trilho traseiro (+Y), Folha 2 no trilho frontal (-Y)
                assert bounds_folhas[0][2] > bounds_folhas[1][2]
                # Lado dos puxadores: Folha 1 na borda esquerda, Folha 2 na borda direita
                assert folhas[0].ext["trazomob"]["door_side"] == "right"
                assert folhas[1].ext["trazomob"]["door_side"] == "left"
                # Confirma geometricamente que o puxador da Folha 1 está na metade esquerda da Folha 1
                # e o puxador da Folha 2 está na metade direita da Folha 2
                h1_center = sum(handle_xs_folhas[0]) * 0.5
                h2_center = sum(handle_xs_folhas[1]) * 0.5
                f1_center = (bounds_folhas[0][0] + bounds_folhas[0][1]) * 0.5
                f2_center = (bounds_folhas[1][0] + bounds_folhas[1][1]) * 0.5
                assert h1_center < f1_center, "Puxador da Porta 1 (Esq) deveria estar na borda esquerda!"
                assert h2_center > f2_center, "Puxador da Porta 2 (Dir) deveria estar na borda direita!"

            elif n_portas == 3:
                expected_w = (L_m + 2.0 * transpasse_m) / 3.0
                assert abs((bounds_folhas[0][1] - bounds_folhas[0][0]) - expected_w) < 1e-3
                # Transpasse entre Folha 1 e Folha 2 == 30mm, e entre Folha 2 e Folha 3 == 30mm
                overlap_1_2 = bounds_folhas[0][1] - bounds_folhas[1][0]
                overlap_2_3 = bounds_folhas[1][1] - bounds_folhas[2][0]
                assert abs(overlap_1_2 - transpasse_m) < 1e-3
                assert abs(overlap_2_3 - transpasse_m) < 1e-3
                # Folhas 1 e 3 no trilho traseiro (+Y), Folha 2 (Centro) no trilho frontal (-Y)
                assert bounds_folhas[0][2] > bounds_folhas[1][2]
                assert bounds_folhas[2][2] > bounds_folhas[1][2]
                # Lado dos puxadores: Folha 1 na esquerda, Folha 2 (Central) nos DOIS lados ("both"), Folha 3 na direita
                assert folhas[0].ext["trazomob"]["door_side"] == "right"
                assert folhas[1].ext["trazomob"]["door_side"] == "both"
                assert folhas[2].ext["trazomob"]["door_side"] == "left"
                h1_center = sum(handle_xs_folhas[0]) * 0.5
                h3_center = sum(handle_xs_folhas[2]) * 0.5
                assert h1_center < (bounds_folhas[0][0] + bounds_folhas[0][1]) * 0.5
                assert h3_center > (bounds_folhas[2][0] + bounds_folhas[2][1]) * 0.5
                # Na Folha 2 (Central), há puxadores nas duas extremidades (perto de min_x e perto de max_x)
                assert handle_xs_folhas[1][0] < bounds_folhas[1][0] + 0.06
                assert handle_xs_folhas[1][1] > bounds_folhas[1][1] - 0.06

            elif n_portas == 4:
                expected_w = (L_m + 2.0 * transpasse_m) / 4.0
                assert abs((bounds_folhas[0][1] - bounds_folhas[0][0]) - expected_w) < 1e-3
                # Transpasse lateral esquerdo (Folha 1 com Folha 2) == 30mm
                overlap_1_2 = bounds_folhas[0][1] - bounds_folhas[1][0]
                # Encontro central (Folha 2 com Folha 3) == 0mm (topo a topo no centro)
                center_gap_2_3 = bounds_folhas[2][0] - bounds_folhas[1][1]
                # Transpasse lateral direito (Folha 3 com Folha 4) == 30mm
                overlap_3_4 = bounds_folhas[2][1] - bounds_folhas[3][0]
                assert abs(overlap_1_2 - transpasse_m) < 1e-3
                assert abs(center_gap_2_3) < 1e-3
                assert abs(overlap_3_4 - transpasse_m) < 1e-3
                # Folhas 1 e 4 no trilho traseiro (+Y), Folhas 2 e 3 no trilho frontal (-Y)
                assert bounds_folhas[0][2] > bounds_folhas[1][2]
                assert bounds_folhas[3][2] > bounds_folhas[2][2]
                # Puxadores simétricos: F1 na esquerda, F2 na direita (centro), F3 na esquerda (centro), F4 na direita
                assert [f.ext["trazomob"]["door_side"] for f in folhas] == ["right", "left", "right", "left"]
                h1_center = sum(handle_xs_folhas[0]) * 0.5
                h2_center = sum(handle_xs_folhas[1]) * 0.5
                h3_center = sum(handle_xs_folhas[2]) * 0.5
                h4_center = sum(handle_xs_folhas[3]) * 0.5
                assert h1_center < (bounds_folhas[0][0] + bounds_folhas[0][1]) * 0.5
                assert h2_center > (bounds_folhas[1][0] + bounds_folhas[1][1]) * 0.5
                assert h3_center < (bounds_folhas[2][0] + bounds_folhas[2][1]) * 0.5
                assert h4_center > (bounds_folhas[3][0] + bounds_folhas[3][1]) * 0.5

            # 3. Verifica cinemática (door_slide): quando a porta desliza, a textura (UVW) deve se mover junto com os vértices!
            from trazomob.interaction.interact import CabinetInteract
            # Aplica um material madeirado com textura para garantir que o UVW exista e se mova junto
            params_tex = dict(params)
            params_tex["material"] = "MDF Louro Freijó 15mm"
            params_tex["material_frentes"] = "MDF Louro Freijó 15mm"
            grp_tex = CabinetBuilder.build_module_group(params_tex)
            f_tex = [c for c in grp_tex.children if "Porta Correr" in getattr(c, "name", "")][0]
            CabinetInteract.set_piece_open_fraction(f_tex, 0.0, grp_tex)
            face_tex = next((fc for fc in f_tex.mesh.faces if fc.attrs and fc.attrs.get("texture") and "uvw" in fc.attrs["texture"]), None)
            assert face_tex is not None, "A folha madeirada deveria possuir atributo de textura UVW"
            uvw_closed = list(face_tex.attrs["texture"]["uvw"])
            v0_closed = f_tex.mesh.vertices[0].position.x()

            CabinetInteract.set_piece_open_fraction(f_tex, 1.0, grp_tex)
            uvw_open = list(face_tex.attrs["texture"]["uvw"])
            v0_open = f_tex.mesh.vertices[0].position.x()
            delta_v = v0_open - v0_closed
            # Verifica que o valor de UV calculado no vértice transformado (u = gx*x + c) permaneceu idêntico ao fechado!
            u_at_v0_closed = uvw_closed[0] * v0_closed + uvw_closed[3]
            u_at_v0_open = uvw_open[0] * v0_open + uvw_open[3]
            assert abs(delta_v) > 0.10
            assert abs(u_at_v0_open - u_at_v0_closed) < 1e-4, (
                f"A textura UV deveria acompanhar a porta (u_closed={u_at_v0_closed}, u_open={u_at_v0_open})"
            )




