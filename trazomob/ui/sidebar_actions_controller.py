# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Acoes de edicao e manutencao de modulos na barra lateral."""
from __future__ import annotations

from core.group import Group

from ..builders.cabinet import RotateTrazoMobModuleCommand
from ..domain.i18n import tr
from ..domain.param_mapper import extract_ui_module_params
from ..domain.schema import module_params


class SidebarActionsMixin:
    """Acoes de rotacao, exclusao, duplicacao e persistencia de padroes."""

    def _save_current_as_default(self) -> None:
        """Salva as medidas, materiais e puxadores atuais como padrão permanente nas preferências."""
        mod = self._active_selected_module()
        if mod is None:
            return
        old_params = module_params(mod) if getattr(mod, "ext", None) else {}
        tipo = str(old_params.get("tipo", "balcao"))

        from ..domain.module_geometry import get_module_category
        cat = get_module_category(tipo)

        from ..domain.preferences import TrazoMobPreferencesManager
        prefs = TrazoMobPreferencesManager.get_instance()

        # Extrai parâmetros atuais do formulário
        curr_params = extract_ui_module_params(self, base_params=old_params)

        # 1. Salva dimensões padrão para esta categoria e tipo
        def_dim = {}
        if "altura" in curr_params:
            def_dim["altura"] = float(curr_params["altura"])
        if "profundidade" in curr_params:
            def_dim["profundidade"] = float(curr_params["profundidade"])
        if "rodape" in curr_params:
            def_dim["rodape"] = float(curr_params["rodape"])
        if "bancada" in tipo:
            if "esp_pedra" in curr_params:
                def_dim["esp_pedra"] = float(curr_params["esp_pedra"])
            if "altura_saia" in curr_params:
                def_dim["altura_saia"] = float(curr_params["altura_saia"])
            if "altura_frontao" in curr_params:
                def_dim["altura_frontao"] = float(curr_params["altura_frontao"])

        prefs.set_module_defaults(cat, def_dim)
        prefs.set_module_defaults(tipo, def_dim)

        # 2. Salva preferências globais de materiais e acabamentos
        if "espessura" in curr_params:
            prefs.set_global("espessura_caixa_mm", float(curr_params["espessura"]))
        if "espessura_frentes" in curr_params:
            prefs.set_global("espessura_frentes_mm", float(curr_params["espessura_frentes"]))
        if "material" in curr_params:
            prefs.set_global("material_caixa", str(curr_params["material"]).rsplit(" ", 1)[0])
        if "material_frentes" in curr_params:
            prefs.set_global("material_frentes", str(curr_params["material_frentes"]).rsplit(" ", 1)[0])
        if "puxador_tipo" in curr_params:
            prefs.set_global("puxador_tipo", str(curr_params["puxador_tipo"]))
        if "puxador_cor" in curr_params:
            prefs.set_global("puxador_cor", str(curr_params["puxador_cor"]))
        if "puxador_pos" in curr_params:
            prefs.set_global("puxador_pos", str(curr_params["puxador_pos"]))
        if "perfil_modelo" in curr_params:
            prefs.set_global("perfil_modelo", str(curr_params["perfil_modelo"]))
        if "desconto_perfil" in curr_params:
            prefs.set_global("desconto_perfil_mm", float(curr_params["desconto_perfil"]))

        # 3. Fundo e Furações
        if "tipo_fundo" in curr_params:
            prefs.set_global("tipo_fundo", str(curr_params["tipo_fundo"]))
        if "esp_fundo" in curr_params:
            prefs.set_global("esp_fundo_mm", float(curr_params["esp_fundo"]))
        if "recuo_fundo" in curr_params:
            prefs.set_global("recuo_fundo_mm", float(curr_params["recuo_fundo"]))
        if "prof_rasgo" in curr_params:
            prefs.set_global("prof_rasgo_mm", float(curr_params["prof_rasgo"]))
        if "folga_fundo" in curr_params:
            prefs.set_global("folga_fundo_mm", float(curr_params["folga_fundo"]))
        if "folga_frentes_mm" in curr_params:
            prefs.set_global("folga_frentes_mm", float(curr_params["folga_frentes_mm"]))
        if "dispositivo_fixacao" in curr_params:
            prefs.set_global("dispositivo_fixacao", str(curr_params["dispositivo_fixacao"]))

        # 4. Travessas Globais (em pé / deitada, larguras, materiais)
        if "travessa_frontal_em_pe" in curr_params:
            prefs.set_global("travessa_frontal_em_pe", bool(curr_params["travessa_frontal_em_pe"]))
        if "travessa_traseira_em_pe" in curr_params:
            prefs.set_global("travessa_traseira_em_pe", bool(curr_params["travessa_traseira_em_pe"]))
        if "larg_travessa_frontal_mm" in curr_params:
            prefs.set_global("larg_travessa_frontal_mm", float(curr_params["larg_travessa_frontal_mm"]))
        if "larg_travessa_traseira_mm" in curr_params:
            prefs.set_global("larg_travessa_traseira_mm", float(curr_params["larg_travessa_traseira_mm"]))
        if "recuo_porta_topo_mm" in curr_params:
            prefs.set_global("recuo_porta_topo_mm", float(curr_params["recuo_porta_topo_mm"]))
        if "material_travessas" in curr_params:
            prefs.set_global("material_travessas", curr_params["material_travessas"])
        if "esp_travessas_mm" in curr_params:
            prefs.set_global("esp_travessas_mm", curr_params["esp_travessas_mm"])
        if "fita_travessas_modo" in curr_params:
            prefs.set_global("fita_travessas_modo", str(curr_params["fita_travessas_modo"]))
        if "material_fita_travessas" in curr_params:
            prefs.set_global("material_fita_travessas", curr_params["material_fita_travessas"])

        ok = prefs.save()
        if ok:
            if hasattr(self, "_get_viewport"):
                vp = self._get_viewport()
                if vp and hasattr(vp, "flash_status"):
                    vp.flash_status(f"⭐ Padrões salvos! Novos módulos da categoria '{cat}' virão com estas medidas.")
            self.lbl_status.setText(tr("⭐ Medidas salvas como padrão permanente ({cat})!", cat=cat))

    def _save_current_to_user_modules(self) -> None:
        """Salva o módulo atual (com as opções da UI) em 'Meus Módulos'."""
        mod = self._active_selected_module()
        if mod is None:
            return

        from PySide6.QtWidgets import QInputDialog, QMessageBox

        from ..domain.catalog import MODULE_CATALOG, build_user_module
        from ..domain.preferences import TrazoMobPreferencesManager

        old_params = module_params(mod) if getattr(mod, "ext", None) else {}
        tipo = str(old_params.get("tipo", "balcao"))
        curr_params = extract_ui_module_params(self, base_params=old_params)

        base = None
        for items in MODULE_CATALOG.values():
            for item in items:
                if item.get("id") == tipo:
                    base = dict(item)
                    break
            if base:
                break
        if base is None:
            base = {"id": tipo, "nome": tipo, "desc": ""}

        nome, ok = QInputDialog.getText(
            self, "Meus Módulos", "Nome do módulo:", text=base.get("nome", tipo)
        )
        if not ok or not (nome or "").strip():
            return

        prefs = TrazoMobPreferencesManager.get_instance()
        existentes = {m.get("id") for m in prefs.get_user_modules() if isinstance(m, dict)}
        novo = build_user_module(base, curr_params, nome, existentes)

        if prefs.add_user_module(novo):
            if hasattr(self, "lbl_status"):
                self.lbl_status.setText(tr("💾 Módulo '{nome}' salvo em Meus Módulos!", nome=novo['nome']))
            if hasattr(self, "_get_viewport"):
                vp = self._get_viewport()
                if vp and hasattr(vp, "flash_status"):
                    vp.flash_status(f"💾 '{novo['nome']}' adicionado ao catálogo pessoal.")
        else:
            QMessageBox.warning(
                self, "Meus Módulos",
                "Não foi possível salvar o módulo nas preferências do usuário."
            )


    def _update_badges(self) -> None:
        """Atualiza dinamicamente as pílulas de resumo (badges) nos cabeçalhos das seções."""
        if not hasattr(self, "sec_dimensoes"):
            return

        # 1. Dimensões
        l = self.sp_largura.value()
        a = self.sp_altura.value()
        p = self.sp_prof.value()
        self.sec_dimensoes.set_badge(f"{l}x{a}x{p} mm")

        # 2. Frentes & Estrutura
        qtd = self.sp_qtd_elem.value()
        lbl_elem = self.lbl_qtd_elem.text().replace(":", "").strip()
        prat = self.sp_prateleiras.value()
        badge_frentes = f"{qtd} {lbl_elem}"
        if prat > 0:
            badge_frentes += f" | {prat} prat."
        self.sec_frentes.set_badge(badge_frentes)

        # 3. Puxadores
        pux = self.cb_puxador_tipo.currentText()
        if pux.lower() == "sem puxador":
            self.sec_puxadores.set_badge("Nenhum")
        else:
            self.sec_puxadores.set_badge(pux)

        # 4. Materiais
        mat_caixa = self.cb_material.currentText().split("(")[0].strip()
        self.sec_materiais.set_badge(mat_caixa)

        # 5. Ajustes Especiais
        if hasattr(self, "sec_ajustes"):
            disp_txt = self.cb_dispositivo_fixacao.currentText() if hasattr(self, "cb_dispositivo_fixacao") else "Padrão"
            self.sec_ajustes.set_badge(disp_txt)


    def _rotate_selected(self, deg: float) -> None:
        mod = self._active_selected_module()
        viewport = self._get_viewport()
        if viewport is None:
            return
        if mod is not None:
            cmd = RotateTrazoMobModuleCommand(mod, deg, viewport=viewport)
            if hasattr(viewport, "history") and viewport.history:
                viewport.history.execute(cmd)
            else:
                cmd.do(self._get_scene())
            if hasattr(viewport, "notify_scene_changed"):
                viewport.notify_scene_changed()
            viewport.update()
            self.load_module(mod)
            return

        from ..interaction.align_tools import resolve_rotatable_groups, rotate_groups_with_command

        targets = resolve_rotatable_groups(self._get_scene())
        if targets:
            rotate_groups_with_command(targets, deg, viewport)


    def _open_full_dialog(self) -> None:
        viewport = self._get_viewport()
        if viewport is None:
            return
        from ..integrations import platform as host
        from ..ui.module_dialog import TrazoMobDialog
        win = host.window_of(self._get_window(), viewport)
        dlg = getattr(win, "_trazomob_dialog", None)
        if dlg is None or not dlg.isVisible():
            dlg = TrazoMobDialog(viewport, parent=win)
            if win is not None:
                setattr(win, "_trazomob_dialog", dlg)
            dlg.show()
        else:
            if hasattr(dlg, "sync_to_active_document"):
                dlg.sync_to_active_document(viewport)
            dlg.raise_()
            dlg.activateWindow()


    def _duplicate_selected(self, direction: str = "right") -> None:
        """Duplica o módulo selecionado na cena perfeitamente encostado na face esquerda ou direita com Undo/Redo."""
        mod = self._active_selected_module()
        viewport = self._get_viewport()
        if mod is None or viewport is None:
            return

        from ..interaction.module_operations import duplicate_contiguous_module
        new_module = duplicate_contiguous_module(mod, direction=direction, viewport=viewport)
        if new_module is not None:
            self.load_module(new_module)
            self.lbl_status.setText(tr("📋 Módulo '{name}' duplicado!", name=new_module.name))


    def _delete_selected(self) -> None:
        """Exclui o módulo selecionado da cena com Undo/Redo."""
        mod = self._active_selected_module()
        viewport = self._get_viewport()
        if mod is None or viewport is None:
            return

        from ..interaction.module_operations import delete_module
        if delete_module(mod, viewport=viewport, parent_widget=self):
            self._selected_module = None
            self._set_editor_enabled(False)
            self.lbl_status.setText("🗑️ Módulo excluído com sucesso.")
