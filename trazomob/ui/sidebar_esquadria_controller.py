# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Mixin para o painel lateral do TrazoMob especializado em esquadrias (portas e janelas)."""
from __future__ import annotations

import math
from typing import Any
from PySide6.QtGui import QVector3D
from ..domain.i18n import tr
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSpinBox,
)
from core.group import Group


class SidebarEsquadriaMixin:
    """Encapsula o menu de catálogo, inserção em parede e ajustes finos de portas/janelas."""

    def _on_abrir_menu_esquadrias(self) -> None:
        """Abre o menu categorizado da biblioteca de esquadrias reais (.igz) para inserção na parede."""
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: palette(base); border: 1px solid palette(mid); } "
            "QMenu::item { padding: 6px 14px; font-size: 11px; color: palette(text); } "
            "QMenu::item:selected { background: palette(highlight); color: palette(highlighted-text); } "
            "QMenu::separator { height: 1px; background: palette(midlight); margin: 3px 6px; }"
        )

        from ..domain.catalog import MODULE_CATALOG
        esquadrias = MODULE_CATALOG.get("Portas & Janelas", [])

        # Submenu: Portas
        menu_portas = menu.addMenu("🚪 Portas Reais")
        # Submenu: Janelas
        menu_janelas = menu.addMenu("🪟 Janelas & Basculantes")

        actions_map = {}
        for item in esquadrias:
            item_id = item.get("id", "")
            nome = item.get("nome", item_id)
            larg = float(item.get("largura", 800))
            alt = float(item.get("altura", 2100))
            peit = float(item.get("peitoril", 0))

            if item_id.startswith("porta_"):
                act = menu_portas.addAction(f"🚪 {nome}")
            else:
                peit_label = f" (Peitoril {int(peit)}mm)" if peit > 0 else ""
                act = menu_janelas.addAction(f"🪟 {nome}{peit_label}")
            actions_map[act] = (item_id, larg, alt, peit)

        # Acesso rápido aos favoritos diretamente no menu raiz
        menu.addSeparator()
        act_quick_p80 = menu.addAction("⚡ Porta Giro 80x215 cm")
        act_quick_j130 = menu.addAction("⚡ Janela Correr 2F 130x120 cm (Peitoril 100cm)")
        actions_map[act_quick_p80] = ("porta_giro_80", 800.0, 2150.0, 0.0)
        actions_map[act_quick_j130] = ("janela_correr_2f_130", 1300.0, 1200.0, 1000.0)

        action = menu.exec(self.btn_inserir_esquadria.mapToGlobal(self.btn_inserir_esquadria.rect().bottomLeft()))
        if not action or action not in actions_map:
            return

        tipo_sel, larg_sel, alt_sel, peit_sel = actions_map[action]
        self._inserir_esquadria_na_parede(tipo_sel, largura_mm=larg_sel, altura_mm=alt_sel, peitoril_mm=peit_sel)

    def _inserir_esquadria_na_parede(self, tipo: str, largura_mm: float, altura_mm: float, peitoril_mm: float = 0.0) -> None:
        viewport = self._get_viewport()
        scene = getattr(viewport, "scene", None) if viewport else None
        if scene is None or viewport is None:
            return

        from ..wall.selection import WallSelectionManager
        wall_mgr = WallSelectionManager.get_instance(viewport)
        sel_wf = wall_mgr.selected_wall_face
        if sel_wf is None or sel_wf.face is None:
            self.lbl_status.setText("⚠️ Selecione uma parede para posicionar a esquadria.")
            return

        # Dados geometricos da parede hospedeira
        wall_grp = getattr(sel_wf, "wall_group", None)
        params_w = getattr(wall_grp, "ext", {}).get("trazomob_wall", {}) if wall_grp else {}
        esp_parede_m = float(params_w.get("espessura", 0.15))
        esp_parede_mm = round(esp_parede_m * 1000.0)
        alinhamento = params_w.get("alinhamento", "interno")
        pts_data = params_w.get("pontos", [])
        is_closed = params_w.get("is_closed", False)
        seg_idx = getattr(sel_wf, "segment_index", 0)
        n_pts = len(pts_data)
        n_segs = n_pts if is_closed else max(0, n_pts - 1)

        larg_m = largura_mm / 1000.0
        slot = wall_mgr.active_placement_slot
        start_u = 0.0

        if 0 <= seg_idx < n_segs:
            p0 = QVector3D(*pts_data[seg_idx])
            p1 = QVector3D(*pts_data[(seg_idx + 1) % n_pts])
            seg_v = p1 - p0
            seg_len = seg_v.length()
            seg_u = seg_v.normalized() if seg_len > 1e-4 else QVector3D(1, 0, 0)
            seg_n = QVector3D(-seg_u.y(), seg_u.x(), 0.0).normalized()

            # Se quad_2d estiver presente (parede segmentada de planta 2D), usa o centro geométrico real
            quad_2d = params_w.get("quad_2d")
            if isinstance(quad_2d, (list, tuple)) and len(quad_2d) == 4 and seg_idx == 0:
                q_pts = [QVector3D(float(pt[0]), float(pt[1]), 0.0) for pt in quad_2d]
                q_mid = (q_pts[0] + q_pts[1] + q_pts[2] + q_pts[3]) * 0.25
                proj_n_mid = QVector3D.dotProduct(q_mid - p0, seg_n)
                transv = seg_n * proj_n_mid
            elif alinhamento == "interno":
                transv = seg_n * (esp_parede_m * 0.5)
            elif alinhamento == "externo":
                transv = seg_n * (-esp_parede_m * 0.5)
            else:
                transv = QVector3D(0, 0, 0)

            anchor_u = slot.get("anchor_u") if slot else None
            if anchor_u is not None and anchor_u + larg_m <= seg_len:
                start_u = anchor_u
            else:
                start_u = max(0.0, (seg_len - larg_m) * 0.5)

            center_u = start_u + (larg_m * 0.5)
            c_seg_center = p0 + seg_u * center_u + transv
            from ..builders.esquadrias import EsquadriaBuilder
            mid_yl = EsquadriaBuilder.get_esquadria_local_mid_y(tipo, esp_parede_mm=esp_parede_mm)
            p_origin = c_seg_center - seg_u * (larg_m * 0.5) - seg_n * mid_yl
            p_center = c_seg_center
            rot_z = math.degrees(math.atan2(seg_u.y(), seg_u.x()))
        else:
            norm = sel_wf.normal
            n_dir = QVector3D(norm.x(), norm.y(), 0.0).normalized()
            u_dir = QVector3D(-n_dir.y(), n_dir.x(), 0.0).normalized()
            xf = getattr(sel_wf.wall_group, "xform", None)
            c_wall = xf.map(sel_wf.center) if xf is not None else sel_wf.center
            rot_z = math.degrees(math.atan2(u_dir.y(), u_dir.x()))
            from ..builders.esquadrias import EsquadriaBuilder
            mid_yl = EsquadriaBuilder.get_esquadria_local_mid_y(tipo, esp_parede_mm=esp_parede_mm)
            p_center = c_wall - n_dir * (esp_parede_m * 0.5)
            p_origin = p_center - u_dir * (larg_m * 0.5) + n_dir * mid_yl
        p_origin = QVector3D(p_origin.x(), p_origin.y(), 0.0)

        from ..builders.esquadrias import EsquadriaBuilder
        # Carrega o modelo com fallback inteligente e alta fidelidade
        g_esq = EsquadriaBuilder.load_esquadria_igz(
            item_id=tipo,
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            esp_parede_mm=esp_parede_mm,
            peitoril_mm=peitoril_mm,
            offset=(p_origin.x(), p_origin.y(), p_origin.z()),
            rot_z=rot_z,
        )

        from core.history import SnapshotImport
        def apply_insert_esq(sc):
            target_layer = getattr(g_esq, "layer", None)
            if target_layer and hasattr(sc, "layer") and hasattr(sc, "layers"):
                if sc.layer(target_layer) is None:
                    from core.layers import Layer
                    sc.layers.append(Layer(target_layer))
            sc.groups.append(g_esq)
            sc.selection = {g_esq}

            # ── ABERTURA / RECORTE DO VÃO NA PAREDE HOSPEDEIRA ──
            from ..wall.mesh_builder import WallMeshBuilder
            WallMeshBuilder.sync_scene_wall_openings(sc)

        viewport.history.execute(SnapshotImport(apply_insert_esq))
        viewport.notify_scene_changed()
        viewport.update()

        # Atualiza ancoragem contígua
        if slot is not None:
            slot["anchor_u"] = start_u + larg_m

        self.lbl_status.setText(tr("✅ {name} inserida na parede com sucesso!", name=g_esq.name))

    def _get_esquadria_wall_info(self, mod: Group, scene: Any) -> dict | None:
        """Calcula informações da parede hospedeira e posição U/distâncias da esquadria."""
        from ..interaction.magnetic_drag import get_module_reference_bounds
        b = get_module_reference_bounds(mod)
        if not b or not scene:
            return None
        c_esq = QVector3D((b[0] + b[1]) * 0.5, (b[2] + b[3]) * 0.5, 0.0)
        esq_info = getattr(mod, "ext", {}).get("trazomob_esquadria") or getattr(mod, "ext", {}).get("trazomob_module") or getattr(mod, "ext", {}).get("trazomob") or {}
        if "rot_z" in esq_info and esq_info["rot_z"] is not None:
            rad = math.radians(float(esq_info["rot_z"]))
            esq_u = QVector3D(math.cos(rad), math.sin(rad), 0.0).normalized()
        else:
            dx_b = b[1] - b[0]
            dy_b = b[3] - b[2]
            if dx_b >= dy_b * 1.2:
                esq_u = QVector3D(1.0, 0.0, 0.0)
            elif dy_b >= dx_b * 1.2:
                esq_u = QVector3D(0.0, 1.0, 0.0)
            else:
                esq_u = None

        for g in getattr(scene, "groups", []):
            if not (hasattr(g, "ext") and isinstance(g.ext, dict) and "trazomob_wall" in g.ext):
                continue
            w_ext = g.ext["trazomob_wall"]
            if w_ext.get("is_column"):
                continue
            pts_data = w_ext.get("pontos", [])
            is_closed = w_ext.get("is_closed", False)
            n_pts = len(pts_data)
            n_segs = n_pts if is_closed else max(0, n_pts - 1)
            for seg_i in range(n_segs):
                p0 = QVector3D(*pts_data[seg_i])
                p1 = QVector3D(*pts_data[(seg_i + 1) % n_pts])
                seg_v = p1 - p0
                seg_len = seg_v.length()
                if seg_len < 0.05:
                    continue
                seg_u = seg_v.normalized()
                if esq_u is not None and abs(QVector3D.dotProduct(esq_u, seg_u)) < 0.80:
                    continue
                seg_n = QVector3D(-seg_u.y(), seg_u.x(), 0.0).normalized()
                dist_norm = abs(QVector3D.dotProduct(c_esq - p0, seg_n))
                wall_esp = float(w_ext.get("espessura", 0.15))
                if dist_norm <= wall_esp + 0.25:
                    proj_c = QVector3D.dotProduct(c_esq - p0, seg_u)
                    if not (-0.05 <= proj_c <= seg_len + 0.05):
                        continue
                    projs = [
                        QVector3D.dotProduct(QVector3D(b[0], b[2], 0.0) - p0, seg_u),
                        QVector3D.dotProduct(QVector3D(b[1], b[2], 0.0) - p0, seg_u),
                        QVector3D.dotProduct(QVector3D(b[0], b[3], 0.0) - p0, seg_u),
                        QVector3D.dotProduct(QVector3D(b[1], b[3], 0.0) - p0, seg_u),
                    ]
                    u_min = min(projs)
                    u_max = max(projs)
                    return {
                        "wall": g,
                        "seg_i": seg_i,
                        "seg_len": seg_len,
                        "seg_u": seg_u,
                        "seg_n": seg_n,
                        "p0": p0,
                        "p1": p1,
                        "u_min": u_min,
                        "u_max": u_max,
                        "dist_esq_mm": round(u_min * 1000.0),
                        "dist_dir_mm": round((seg_len - u_max) * 1000.0),
                    }
        return None

    def _on_esquadria_dist_canto_changed(self, target_dist_mm: int) -> None:
        """Reposiciona a porta/janela para a distância especificada do canto da parede."""
        if getattr(self, "_updating_ui", False):
            return
        mod = self._active_selected_module()
        scene = self._get_scene()
        vp = self._get_viewport()
        if mod is None or scene is None or vp is None:
            return

        w_info = self._get_esquadria_wall_info(mod, scene)
        if not w_info:
            return

        target_u_m = float(target_dist_mm) / 1000.0
        cur_u_m = w_info["u_min"]
        delta_u = target_u_m - cur_u_m
        if abs(delta_u) < 1e-4:
            return

        seg_u = w_info["seg_u"]
        shift = seg_u * delta_u

        # Desloca os vértices e pivôs cinemáticos da esquadria no espaço 3D
        for c in (getattr(mod, "children", None) or [mod]):
            if hasattr(c, "mesh") and c.mesh and hasattr(c.mesh, "vertices"):
                for v in c.mesh.vertices:
                    v.position += shift
                c.mesh._mut_serial = getattr(c.mesh, "_mut_serial", 0) + 1
            if getattr(c, "ext", None) is not None and isinstance(c.ext, dict):
                if "orig_vertices" in c.ext and isinstance(c.ext["orig_vertices"], list):
                    c.ext["orig_vertices"] = [orig + shift for orig in c.ext["orig_vertices"]]
                if "hinge_pivot" in c.ext and isinstance(c.ext["hinge_pivot"], QVector3D):
                    c.ext["hinge_pivot"] += shift

        if getattr(mod, "ext", None) and isinstance(mod.ext, dict):
            for k_ext in ("trazomob_module", "trazomob_esquadria", "trazomob"):
                if k_ext in mod.ext and isinstance(mod.ext[k_ext], dict):
                    old_off = mod.ext[k_ext].get("offset", (0.0, 0.0, 0.0))
                    if isinstance(old_off, (list, tuple)) and len(old_off) >= 3:
                        mod.ext[k_ext]["offset"] = (
                            float(old_off[0]) + float(shift.x()),
                            float(old_off[1]) + float(shift.y()),
                            float(old_off[2]) + float(shift.z()),
                        )

        # Sincroniza o recorte do vão na alvenaria
        from ..wall.mesh_builder import WallMeshBuilder
        WallMeshBuilder.sync_scene_wall_openings(scene)

        # Atualiza a etiqueta de distância na barra lateral
        if hasattr(self, "lbl_esq_dist_canto"):
            self.lbl_esq_dist_canto.setText(f"Distância Canto ({int(target_dist_mm)}mm):")

        # Notifica o Viewport
        if hasattr(vp, "notify_scene_changed"):
            vp.notify_scene_changed()
        vp.update()

    def _centralizar_esquadria_na_parede(self) -> None:
        """Centraliza a esquadria perfeitamente no comprimento da parede hospedeira."""
        mod = self._active_selected_module()
        scene = self._get_scene()
        if mod is None or scene is None:
            return

        w_info = self._get_esquadria_wall_info(mod, scene)
        if not w_info:
            return

        seg_len = w_info["seg_len"]
        esq_w = w_info["u_max"] - w_info["u_min"]
        target_center_dist = max(0.0, (seg_len - esq_w) * 0.5)
        if hasattr(self, "sp_esq_dist_canto"):
            self.sp_esq_dist_canto.setValue(int(round(target_center_dist * 1000.0)))

    def _on_esquadria_inverter_lado_clicked(self) -> None:
        """Inverte rapidamente o lado de abertura da porta (Direita ↔ Esquerda)."""
        if not hasattr(self, "cb_esq_lado_abertura"):
            return
        cur = self.cb_esq_lado_abertura.currentIndex()
        self.cb_esq_lado_abertura.setCurrentIndex(0 if cur == 1 else 1)

    def _on_esquadria_inverter_sentido_clicked(self) -> None:
        """Inverte rapidamente o sentido de giro da porta (Para Dentro ↔ Para Fora)."""
        if not hasattr(self, "cb_esq_sentido_abertura"):
            return
        cur = self.cb_esq_sentido_abertura.currentIndex()
        self.cb_esq_sentido_abertura.setCurrentIndex(0 if cur == 1 else 1)

    def _on_esquadria_tamanho_rapido_changed(self, idx: int) -> None:
        """Altera dinamicamente a largura da porta ao selecionar um tamanho predefinido."""
        if getattr(self, "_updating_ui", False):
            return
        mod = self._active_selected_module()
        m_tipo = str(getattr(mod, "ext", {}).get("trazomob_module", {}).get("tipo", "")) if mod else ""
        is_piv = "pivotante" in m_tipo.lower()
        sizes = [800, 900, 1000] if is_piv else [700, 800, 900]
        if 0 <= idx < len(sizes):
            target_w = sizes[idx]
            if hasattr(self, "sp_largura"):
                self.sp_largura.setValue(target_w)
            self._apply_changes_to_selected()

    def _on_esquadria_abertura_combo_changed(self, _idx: int = 0) -> None:
        """Aplica imediatamente a inversão de lado ou sentido na porta selecionada."""
        if getattr(self, "_updating_ui", False):
            return
        self._apply_changes_to_selected()


    def _build_esquadria_rows(self) -> None:
        """Cria as linhas de ajustes de esquadrias na aba Medidas."""
        # ── Posição / Distância da Parede (para Esquadrias: Portas & Janelas) ──
        h_pos_esq = QHBoxLayout()
        self.sp_esq_dist_canto = QSpinBox()
        self.sp_esq_dist_canto.setRange(0, 50000)
        self.sp_esq_dist_canto.setValue(100)
        self.sp_esq_dist_canto.setSuffix(" mm")
        self.sp_esq_dist_canto.setSingleStep(50)
        self.sp_esq_dist_canto.setToolTip("Distância da porta ou janela em relação ao canto esquerdo da parede (Boneca).")
        h_pos_esq.addWidget(self.sp_esq_dist_canto)

        btn_pe_minus = QPushButton("-50")
        btn_pe_minus.setMaximumWidth(36)
        btn_pe_minus.clicked.connect(lambda: self.sp_esq_dist_canto.setValue(max(0, self.sp_esq_dist_canto.value() - 50)))
        h_pos_esq.addWidget(btn_pe_minus)
        btn_pe_plus = QPushButton("+50")
        btn_pe_plus.setMaximumWidth(36)
        btn_pe_plus.clicked.connect(lambda: self.sp_esq_dist_canto.setValue(self.sp_esq_dist_canto.value() + 50))
        h_pos_esq.addWidget(btn_pe_plus)

        btn_centralizar_esq = QPushButton("✛ Centralizar")
        btn_centralizar_esq.setToolTip("Centraliza a porta/janela no centro da parede hospedeira")
        btn_centralizar_esq.clicked.connect(self._centralizar_esquadria_na_parede)
        h_pos_esq.addWidget(btn_centralizar_esq)

        self.lbl_esq_dist_canto = QLabel("Distância Canto:")
        self.sec_dimensoes.form_layout.addRow(self.lbl_esq_dist_canto, h_pos_esq)
        self.lbl_esq_dist_canto.setVisible(False)
        self.sp_esq_dist_canto.setVisible(False)
        btn_pe_minus.setVisible(False)
        btn_pe_plus.setVisible(False)
        btn_centralizar_esq.setVisible(False)
        self._esquadria_pos_widgets = [
            self.lbl_esq_dist_canto, self.sp_esq_dist_canto,
            btn_pe_minus, btn_pe_plus, btn_centralizar_esq
        ]

        # Conecta a alteração da distância do canto ao reposicionamento dinâmico
        self.sp_esq_dist_canto.valueChanged.connect(self._on_esquadria_dist_canto_changed)

        # ── Largura / Tamanho Rápido da Porta de Giro ──
        h_esq_tam = QHBoxLayout()
        self.cb_esq_tamanho_rapido = QComboBox()
        self.cb_esq_tamanho_rapido.addItems([
            "70 cm (700 mm)",
            "80 cm (800 mm)",
            "90 cm (900 mm)",
            "📐 Personalizado",
        ])
        self.cb_esq_tamanho_rapido.setToolTip("Altera imediatamente a largura da porta de giro na cena 3D")
        h_esq_tam.addWidget(self.cb_esq_tamanho_rapido)
        self.lbl_esq_tamanho_rapido = QLabel("Tamanho Porta:")
        self.sec_dimensoes.form_layout.addRow(self.lbl_esq_tamanho_rapido, h_esq_tam)
        self.cb_esq_tamanho_rapido.currentIndexChanged.connect(self._on_esquadria_tamanho_rapido_changed)

        # ── Lado e Sentido de Abertura da Porta (para Esquadrias de Porta) ──
        h_esq_lado = QHBoxLayout()
        self.cb_esq_lado_abertura = QComboBox()
        self.cb_esq_lado_abertura.addItems([
            "➡️ Direita (Padrão)",
            "⬅️ Esquerda (Invertido)",
        ])
        self.cb_esq_lado_abertura.setToolTip("Define em qual lado fica a dobradiça / giro da porta")
        h_esq_lado.addWidget(self.cb_esq_lado_abertura)

        self.btn_esq_inverter_lado = QPushButton("⇄ Inverter Lado")
        self.btn_esq_inverter_lado.setToolTip("Inverte imediatamente o lado da porta (Esquerda ↔ Direita)")
        self.btn_esq_inverter_lado.clicked.connect(self._on_esquadria_inverter_lado_clicked)
        h_esq_lado.addWidget(self.btn_esq_inverter_lado)

        self.lbl_esq_lado_abertura = QLabel("Lado Abertura:")
        self.sec_dimensoes.form_layout.addRow(self.lbl_esq_lado_abertura, h_esq_lado)

        h_esq_sentido = QHBoxLayout()
        self.cb_esq_sentido_abertura = QComboBox()
        self.cb_esq_sentido_abertura.addItems([
            "🏠 Para Dentro (Interno)",
            "🚪 Para Fora (Externo)",
        ])
        self.cb_esq_sentido_abertura.setToolTip("Define para qual face da parede a porta abre (Dentro ou Fora)")
        h_esq_sentido.addWidget(self.cb_esq_sentido_abertura)

        self.btn_esq_inverter_sentido = QPushButton("⇅ Dentro/Fora")
        self.btn_esq_inverter_sentido.setToolTip("Inverte o sentido de abertura da porta na parede (Para Dentro ↔ Para Fora)")
        self.btn_esq_inverter_sentido.clicked.connect(self._on_esquadria_inverter_sentido_clicked)
        h_esq_sentido.addWidget(self.btn_esq_inverter_sentido)

        self.lbl_esq_sentido_abertura = QLabel("Sentido Giro:")
        self.sec_dimensoes.form_layout.addRow(self.lbl_esq_sentido_abertura, h_esq_sentido)

        self._esquadria_porta_widgets = [
            self.lbl_esq_tamanho_rapido, self.cb_esq_tamanho_rapido,
            self.lbl_esq_lado_abertura, self.cb_esq_lado_abertura, self.btn_esq_inverter_lado,
            self.lbl_esq_sentido_abertura, self.cb_esq_sentido_abertura, self.btn_esq_inverter_sentido,
        ]
        for w in self._esquadria_porta_widgets:
            w.setVisible(False)

        self.cb_esq_lado_abertura.currentIndexChanged.connect(self._on_esquadria_abertura_combo_changed)
        self.cb_esq_sentido_abertura.currentIndexChanged.connect(self._on_esquadria_abertura_combo_changed)


