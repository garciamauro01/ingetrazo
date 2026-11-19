# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations
from typing import Any
from PySide6.QtGui import QVector3D
from PySide6.QtWidgets import QMessageBox
from core.group import Group, iter_placements
from core.history import MoveGroupCommand

class ModuleAlignerMixin:
    def _get_module_bounds(self, mod: Group) -> tuple[float, float, float, float, float, float] | None:
        """Calcula os limites em metros: (min_x, max_x, min_y, max_y, min_z, max_z)."""
        from core.group import iter_placements
        min_x, max_x = float("inf"), float("-inf")
        min_y, max_y = float("inf"), float("-inf")
        min_z, max_z = float("inf"), float("-inf")
        found = False
        for pg, m in iter_placements(mod):
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

    def _get_module_carcass_bounds(self, mod: Group) -> tuple[float, float, float, float, float, float] | None:
        """Calcula os limites em metros da CAIXARIA (desconsiderando portas, frentes, puxadores e saliências).

        Garante que a profundidade e alinhamento do módulo reflitam a CAIXA real do armário,
        sem somar a espessura da porta (+15/18mm) nem puxadores ou saliências frontais.
        """
        from core.group import iter_placements
        min_x, max_x = float("inf"), float("-inf")
        min_y, max_y = float("inf"), float("-inf")
        min_z, max_z = float("inf"), float("-inf")
        found = False
        for pg, m in iter_placements(mod):
            nome = getattr(pg, "name", "")
            if any(ign in nome for ign in ("Porta", "Frente", "Puxador", "Perfil", "Base Projetada")):
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
            return self._get_module_bounds(mod)
        return (min_x, max_x, min_y, max_y, min_z, max_z)

    def _get_module_position(self, mod: Group) -> tuple[float, float, float]:
        """Calcula o ponto de ancoragem mínimo (x, y, z) do módulo existente no 3D."""
        b = self._get_module_carcass_bounds(mod)
        if b is not None:
            return (b[0], b[2], b[4])
        from ..domain.schema import module_params
        return module_params(mod).get("offset", (0.0, 0.0, 0.0))

    def _get_module_dims(self, mod: Group) -> tuple[float, float, float] | None:
        """Calcula a largura (X), profundidade (Y) e altura (Z) da CAIXARIA em mm do módulo."""
        b = self._get_module_carcass_bounds(mod)
        if b is not None:
            return ((b[1] - b[0]) * 1000.0, (b[3] - b[2]) * 1000.0, (b[5] - b[4]) * 1000.0)
        return None


    def _find_scene_modules(self) -> list[Group]:
        """Lista todos os módulos de marcenaria presentes na cena."""
        modules = []
        for g in getattr(self.scene, "groups", []):
            if hasattr(g, "ext") and isinstance(g.ext, dict) and "trazomob_module" in g.ext:
                modules.append(g)
        return modules

    def _get_reference_module(self) -> Group | None:
        """Obtém o módulo de referência para ancoragem automática ou alinhamento."""
        sel = list(getattr(self.scene, "selection", []))
        for item in sel:
            if hasattr(item, "ext") and isinstance(item.ext, dict) and "trazomob_module" in item.ext:
                return item
        for g in self._find_scene_modules():
            children = getattr(g, "children", [])
            if any(child in sel for child in children):
                return g
        if self._editing_module is not None and self._editing_module in getattr(self.scene, "groups", []):
            return self._editing_module
        if getattr(self, "_last_inserted_module", None) is not None:
            if self._last_inserted_module in getattr(self.scene, "groups", []):
                return self._last_inserted_module
        modules = self._find_scene_modules()
        if modules:
            return modules[-1]
        return None

    def _update_align_reference_label(self):
        """Atualiza a indicação do módulo que serve como base de alinhamento e sincroniza a orientação padrão."""
        if not hasattr(self, "lbl_align_ref"):
            return
        ref = self._get_reference_module()
        if ref is not None:
            self.lbl_align_ref.setText(f"📌 Encostar em: {ref.name}")
            # Se for uma nova inserção, herda a rotação/sentido do módulo de referência
            if self._editing_module is None and hasattr(self, "cb_orientacao"):
                ref_rot = 0.0
                if hasattr(ref, "ext") and "trazomob_module" in ref.ext:
                    ref_rot = float(ref.ext["trazomob_module"].get("rot_z", 0.0)) % 360.0
                idx_rot = int(round(ref_rot / 90.0)) % 4
                self.cb_orientacao.setCurrentIndex(idx_rot)
        else:
            self.lbl_align_ref.setText("📌 Encostar em: Origem (1º Módulo)")

    def _align_module(self, action: str):
        """Move o módulo ativo para alinhar magneticamente com seu vizinho mais próximo."""
        target = self._editing_module or self._get_reference_module()
        if not target:
            QMessageBox.information(self, "Alinhamento", "Selecione ou crie um módulo no 3D para alinhar.")
            return

        all_mods = self._find_scene_modules()
        other_mods = [m for m in all_mods if m is not target]
        if not other_mods:
            QMessageBox.information(self, "Alinhamento", "É necessário ao menos dois módulos na cena para alinhar.")
            return

        target_b = self._get_module_bounds(target)
        if not target_b:
            return

        # Encontra o vizinho mais próximo no plano XY
        best_ref = None
        best_dist = float("inf")
        cx_target = (target_b[0] + target_b[1]) / 2.0
        cy_target = (target_b[2] + target_b[3]) / 2.0

        for m in other_mods:
            mb = self._get_module_bounds(m)
            if not mb:
                continue
            cx_m = (mb[0] + mb[1]) / 2.0
            cy_m = (mb[2] + mb[3]) / 2.0
            dist = (cx_target - cx_m)**2 + (cy_target - cy_m)**2
            if dist < best_dist:
                best_dist = dist
                best_ref = m

        if not best_ref:
            return

        ref_b = self._get_module_bounds(best_ref)
        if not ref_b:
            return

        gap_m = (self.sp_align_gap.value() if hasattr(self, "sp_align_gap") else 0) / 1000.0
        delta_x = 0.0
        delta_y = 0.0
        delta_z = 0.0

        ref_rot_z = 0.0
        if hasattr(best_ref, "ext") and "trazomob_module" in best_ref.ext:
            ref_rot_z = float(best_ref.ext["trazomob_module"].get("rot_z", 0.0)) % 360.0

        if abs(ref_rot_z - 180.0) < 1e-4:
            # Se o vizinho está girado 180°:
            if action == "right":  # Direita local do vizinho é -X
                target_width = target_b[1] - target_b[0]
                delta_x = (ref_b[0] - target_width - gap_m) - target_b[0]
                delta_y = ref_b[2] - target_b[2]
                delta_z = ref_b[4] - target_b[4]
            elif action == "left": # Esquerda local do vizinho é +X
                delta_x = (ref_b[1] + gap_m) - target_b[0]
                delta_y = ref_b[2] - target_b[2]
                delta_z = ref_b[4] - target_b[4]
            elif action == "height":
                delta_z = ref_b[4] - target_b[4]
            elif action == "depth":
                delta_y = ref_b[3] - target_b[3]
        elif abs(ref_rot_z - 90.0) < 1e-4:
            # Vizinho girado 90°: Direita local é +Y
            if action == "right":
                delta_x = ref_b[0] - target_b[0]
                delta_y = (ref_b[3] + gap_m) - target_b[2]
                delta_z = ref_b[4] - target_b[4]
            elif action == "left":
                target_depth = target_b[3] - target_b[2]
                delta_x = ref_b[0] - target_b[0]
                delta_y = (ref_b[2] - target_depth - gap_m) - target_b[2]
                delta_z = ref_b[4] - target_b[4]
            elif action == "height":
                delta_z = ref_b[4] - target_b[4]
            elif action == "depth":
                delta_x = ref_b[0] - target_b[0]
        elif abs(ref_rot_z - 270.0) < 1e-4:
            # Vizinho girado 270°: Direita local é -Y
            if action == "right":
                target_depth = target_b[3] - target_b[2]
                delta_x = ref_b[0] - target_b[0]
                delta_y = (ref_b[2] - target_depth - gap_m) - target_b[2]
                delta_z = ref_b[4] - target_b[4]
            elif action == "left":
                delta_x = ref_b[0] - target_b[0]
                delta_y = (ref_b[3] + gap_m) - target_b[2]
                delta_z = ref_b[4] - target_b[4]
            elif action == "height":
                delta_z = ref_b[4] - target_b[4]
            elif action == "depth":
                delta_x = ref_b[1] - target_b[1]
        else:
            # Rotação 0° padrão
            if action == "right":  # Encostar à direita do vizinho
                delta_x = (ref_b[1] + gap_m) - target_b[0]
                delta_y = ref_b[2] - target_b[2]  # Alinha o fundo/parede
                delta_z = ref_b[4] - target_b[4]  # Alinha o piso/base
            elif action == "left":  # Encostar à esquerda do vizinho
                target_width = target_b[1] - target_b[0]
                delta_x = (ref_b[0] - target_width - gap_m) - target_b[0]
                delta_y = ref_b[2] - target_b[2]
                delta_z = ref_b[4] - target_b[4]
            elif action == "height":  # Nivelar altura Z
                delta_z = ref_b[4] - target_b[4]
            elif action == "depth":  # Nivelar profundidade Y
                delta_y = ref_b[2] - target_b[2]

        if abs(delta_x) < 0.0001 and abs(delta_y) < 0.0001 and abs(delta_z) < 0.0001:
            return

        from core.history import MoveGroupCommand
        self.viewport.history.execute(MoveGroupCommand(target, QVector3D(delta_x, delta_y, delta_z)))
        self.viewport.notify_scene_changed()
        self.viewport.update()
        self._load_module_values_if_editing()

    def _rotate_selected_module(self, degrees: float):
        """Rotaciona o módulo ativo ou qualquer objeto selecionado em 90 graus com Undo/Redo."""
        target = self._editing_module or self._get_reference_module()
        if target is not None:
            from ..builders.cabinet import RotateTrazoMobModuleCommand
            cmd = RotateTrazoMobModuleCommand(target, degrees, viewport=self.viewport)
            self.viewport.history.execute(cmd)
            self.viewport.notify_scene_changed()
            self.viewport.update()
            self._load_module_values_if_editing()
            return

        from .align_tools import resolve_rotatable_groups, rotate_groups_with_command
        scene = getattr(self.viewport, "scene", None) if self.viewport else None
        targets = resolve_rotatable_groups(scene)
        if not targets:
            QMessageBox.information(self, "Girar Objeto", "Selecione um objeto ou módulo no 3D para girar.")
            return

        rotate_groups_with_command(targets, degrees, self.viewport)
        self._load_module_values_if_editing()

        # Atualiza a orientação na interface para o próximo módulo herdar
        if hasattr(self, "cb_orientacao"):
            target_rot = 0.0
            if hasattr(target, "ext") and "trazomob_module" in target.ext:
                target_rot = float(target.ext["trazomob_module"].get("rot_z", 0.0)) % 360.0
            idx_rot = int(round(target_rot / 90.0)) % 4
            self.cb_orientacao.setCurrentIndex(idx_rot)

