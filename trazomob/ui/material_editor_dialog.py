# SPDX-License-Identifier: GPL-3.0-or-later
"""Editor e Gerenciador de Materiais PBR do TrazoMob para Renderização no Blender.

Permite listar todos os materiais da cena atual e configurar:
- Tipo PBR: Madeira/MDF, Mármore/Pedra, Tecido/Estofado, Metal, Vidro, Couro, Tinta de Parede
- Subtipos e Acabamentos: Laca Brilhante, Acetinada, Fosca, Polida, Levigada, Veludo, Escovado
- Sliders: Rugosidade (Roughness), Especular/Verniz (Clearcoat) e Intensidade de Relevo (Bump)
"""
from __future__ import annotations

from typing import Dict, Any, List
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPixmap, QImage, QPainter, QIcon
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QListWidget, QListWidgetItem,
    QGroupBox, QLabel, QComboBox, QSlider, QDoubleSpinBox, QPushButton,
    QWidget, QFrame, QFormLayout
)

# Presets predefinidos de shaders PBR
MATERIAL_PBR_TYPES = {
    "auto": {
        "label": "Auto-Detectar (Padrão Inteligente)",
        "roughness": 0.35,
        "specular": 0.50,
        "bump": 0.02,
        "subtypes": ["Padrão"]
    },
    "madeira": {
        "label": "Madeira / MDF / Marcenaria",
        "roughness": 0.32,
        "specular": 0.50,
        "bump": 0.035,
        "subtypes": ["MDF Madeirado (Textura Natural)", "Laca Fosca / Acetinada", "Laca Alto Brilho (High Gloss)"]
    },
    "pedra": {
        "label": "Mármore / Granito / Porcelanato / Piso",
        "roughness": 0.08,
        "specular": 0.85,
        "bump": 0.015,
        "subtypes": ["Polido (Espelhado com Verniz)", "Levigado / Escovado (Fosco)", "Acetinado (Piso/Revestimento)"]
    },
    "cromado": {
        "label": "Cromado / Inox Polido / Espelho Metálico",
        "roughness": 0.02,
        "specular": 1.0,
        "bump": 0.0,
        "subtypes": ["Cromado Espelhado (100% Reflexo)", "Inox Polido Brilhante", "Gold / Dourado Cromado", "Cobre / Rose Gold Cromado", "Black Chrome (Cromado Escuro)"]
    },
    "metal": {
        "label": "Metal / Alumínio / Perfis e Puxadores",
        "roughness": 0.22,
        "specular": 0.90,
        "bump": 0.005,
        "subtypes": ["Alumínio / Inox Escovado", "Preto Fosco Microtexturizado", "Champagne / Bronze Anodizado", "Latão Envelhecido / Dourado Acetinado", "Aço Corten / Industrial"]
    },
    "plastico": {
        "label": "Plástico / Acrílico / Polímeros",
        "roughness": 0.25,
        "specular": 0.50,
        "bump": 0.005,
        "subtypes": ["Plástico Brilhante (Liso)", "Plástico Fosco / Texturizado", "Plástico Acetinado", "Acrílico Translúcido"]
    },
    "vidro": {
        "label": "Vidro / Espelho / Reflecta",
        "roughness": 0.02,
        "specular": 0.95,
        "bump": 0.0,
        "subtypes": ["Vidro Incolor Transparente", "Vidro Reflecta Bronze/Fumê", "Vidro Canelado / Fluted", "Vidro Jateado / Fosco (Acidato)", "Espelho Cristal 100%"]
    },
    "tecido": {
        "label": "Tecido / Estofado / Cortina",
        "roughness": 0.85,
        "specular": 0.10,
        "bump": 0.04,
        "subtypes": ["Linho / Trama Fina", "Veludo Aveludado (Sheen)", "Algodão / Lona", "Cortina Voil / Translúcida"]
    },
    "couro": {
        "label": "Couro / Couro Ecológico",
        "roughness": 0.45,
        "specular": 0.30,
        "bump": 0.04,
        "subtypes": ["Couro Natural Poroso", "Couro Liso Acetinado", "Couro Nobuck / Camurça", "Couro Sintético Brilhoso"]
    },
    "parede": {
        "label": "Tinta de Parede / Drywall / Cimento",
        "roughness": 0.85,
        "specular": 0.18,
        "bump": 0.015,
        "subtypes": ["Tinta Acrílica Fosca / Acetinada", "Cimento Queimado / Concreto", "Gesso / Drywall Liso", "Tijolinho / Textura Rústica"]
    },
    "ceramica": {
        "label": "Cerâmica / Louça / Azulejo",
        "roughness": 0.05,
        "specular": 0.80,
        "bump": 0.005,
        "subtypes": ["Louça Sanitária / Cuba Branca Esmaltada", "Azulejo / Pastilha Brilhante", "Cerâmica Artesanal Acetinada", "Terracota Fosca"]
    },
    "emissivo": {
        "label": "Luz Emissiva / Neon / Fita LED",
        "roughness": 0.1,
        "specular": 0.0,
        "bump": 0.0,
        "subtypes": ["Luz Quente 3000K", "Luz Neutra 4000K", "Luz Fria 6000K", "Painel Iluminado / TV Ligada"]
    }
}


def extract_scene_materials(scene) -> List[dict]:
    """Extrai todos os materiais e texturas reais usados na cena, retornando lista de dicts com metadados.

    Cada item retornado possui:
    {
        'name': str,          # Nome de identificação (ex: 'Nogueira_Cacau', 'Branco_Fosco', 'Tinta_Suvinil')
        'display_name': str,  # Nome amigável para exibição
        'color': tuple|None,  # RGB (0..1)
        'texture_path': str|None, # Caminho da imagem se tiver
        'finish': str|None,   # Finish pré-definido se houver
    }
    """
    from pathlib import Path
    from formats.meshexport import world_faces
    from core.group import effective_material
    from core.materials import effective_attrs
    materials_dict = {}

    def _register_material_data(attrs: dict):
        if not attrs:
            return
        mat_name = attrs.get("mat")
        tex = attrs.get("texture")
        col = attrs.get("color")
        tex_path = tex.get("path") if (isinstance(tex, dict) and tex.get("path")) else None

        if mat_name:
            name = str(mat_name)
        elif tex_path:
            name = Path(tex_path).stem
        elif col:
            r, g, b = [int(max(0.0, min(1.0, c)) * 255) for c in col[:3]]
            name = f"Cor #{r:02X}{g:02X}{b:02X}"
        else:
            name = "Padrão (Sem Acabamento)"

        if name not in materials_dict:
            materials_dict[name] = {
                "name": name,
                "display_name": name,
                "color": tuple(col[:3]) if col else None,
                "texture_path": tex_path,
                "finish": attrs.get("finish"),
            }

    # 1. Varre os materiais cadastrados no registro da cena (scene.materials)
    registry = getattr(scene, "materials", None) or {}
    for name, mat in registry.items():
        if name and name not in materials_dict:
            tex_p = getattr(mat, "texture", {})
            path = tex_p.get("path") if isinstance(tex_p, dict) else None
            materials_dict[name] = {
                "name": name,
                "display_name": name,
                "color": getattr(mat, "color", None),
                "texture_path": path,
                "finish": getattr(mat, "finish", None),
            }

    # 2. Varre materiais atribuídos diretamente aos grupos/paredes (ex: parede pintada por fora)
    for g in getattr(scene, "groups", []):
        paint = effective_material(g)
        if paint:
            _register_material_data(paint)
        # Se as faces internas do grupo herdam o material do grupo:
        if hasattr(g, "mesh") and hasattr(g.mesh, "faces"):
            for f in g.mesh.faces:
                eff = effective_attrs(f.attrs, paint) if paint else f.attrs
                _register_material_data(eff)

    # 3. Varre todas as faces reais do mundo (peças avulsas + componentes)
    for face in world_faces(scene):
        attrs = getattr(face, "attrs", {}) or {}
        _register_material_data(attrs)

    # Ordena: nomeados primeiro, depois por ordem alfabética
    return sorted(list(materials_dict.values()), key=lambda m: m["display_name"].lower())



class MaterialEditorDialog(QDialog):
    """Diálogo visual para editar e atribuir shaders PBR aos materiais da cena."""

    materials_updated = Signal(dict)

    def __init__(self, scene, current_overrides: dict | None = None, viewport=None, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.viewport = viewport
        self._overrides = dict(current_overrides or {})
        self.setWindowTitle("🎨 TrazoMob — Configuração de Materiais & Shaders PBR (Blender)")
        self.setMinimumSize(780, 520)

        from PySide6.QtCore import QSettings
        import json
        settings = QSettings()
        raw_globals = settings.value("trazomob_render/global_material_defaults", "{}")
        try:
            self._global_defaults = json.loads(raw_globals) if isinstance(raw_globals, str) else {}
        except Exception:
            self._global_defaults = {}

        self._scene_materials = extract_scene_materials(scene)
        self._current_mat: str | None = None
        self._highlight_active = True

        # Registra overlay de destaque no viewport se disponível
        self._setup_viewport_overlay()

        self._build_ui()
        self._load_materials_list()

    def _setup_viewport_overlay(self):
        if self.viewport is not None:
            if not hasattr(self.viewport, "_ext_overlays"):
                self.viewport._ext_overlays = []
            if self._draw_material_highlight not in self.viewport._ext_overlays:
                self.viewport._ext_overlays.append(self._draw_material_highlight)

    def _cleanup_viewport_overlay(self):
        if self.viewport is not None and hasattr(self.viewport, "_ext_overlays"):
            if self._draw_material_highlight in self.viewport._ext_overlays:
                self.viewport._ext_overlays.remove(self._draw_material_highlight)
            self.viewport.update()

    def closeEvent(self, event):
        self._cleanup_viewport_overlay()
        super().closeEvent(event)

    def reject(self):
        self._cleanup_viewport_overlay()
        super().reject()

    def accept(self):
        self._cleanup_viewport_overlay()
        super().accept()

    def _draw_material_highlight(self, viewport, painter: QPainter):
        """Desenha contorno e realce sobre todas as faces do material selecionado na lista."""
        if not self._highlight_active or not self._current_mat or self.scene is None:
            return

        from formats.meshexport import world_faces
        from core.group import effective_material
        from core.materials import effective_attrs
        from pathlib import Path
        from PySide6.QtGui import QPen, QBrush, QColor, QPolygonF
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QVector3D

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        # Contorno ciano brilhante (#00D4FF) e preenchimento suave
        pen = QPen(QColor(0, 212, 255, 230), 2.2, Qt.SolidLine)
        brush = QBrush(QColor(0, 212, 255, 45))
        painter.setPen(pen)
        painter.setBrush(brush)

        cur_mat = self._current_mat

        def _resolve_mat_name(attrs: dict) -> str:
            if not attrs:
                return "Padrão (Sem Acabamento)"
            mat_name = attrs.get("mat")
            tex = attrs.get("texture")
            col = attrs.get("color")
            tex_path = tex.get("path") if (isinstance(tex, dict) and tex.get("path")) else None

            if mat_name:
                return str(mat_name)
            elif tex_path:
                return Path(tex_path).stem
            elif col:
                r, g, b = [int(max(0.0, min(1.0, c)) * 255) for c in col[:3]]
                return f"Cor #{r:02X}{g:02X}{b:02X}"
            return "Padrão (Sem Acabamento)"

        def _draw_face(f):
            pts_2d = []
            for v in getattr(f, "vertices", []):
                px = viewport.world_to_pixel(v)
                if px is not None:
                    pts_2d.append(QPointF(px[0], px[1]))
                else:
                    pts_2d = []
                    break
            if len(pts_2d) >= 3:
                painter.drawPolygon(QPolygonF(pts_2d))

        # Realça faces dos grupos (incluindo paredes pintadas externamente)
        for g in getattr(self.scene, "groups", []):
            if hasattr(self.scene, "entity_visible") and not self.scene.entity_visible(g):
                continue
            paint = effective_material(g)
            if hasattr(g, "mesh") and hasattr(g.mesh, "faces"):
                for f in g.mesh.faces:
                    if f.attrs.get("hidden"):
                        continue
                    eff = effective_attrs(f.attrs, paint) if paint else f.attrs
                    if _resolve_mat_name(eff) == cur_mat:
                        _draw_face(f)

        # Realça faces soltas da cena
        loose = getattr(self.scene, "loose_mesh", None) or getattr(self.scene, "mesh", None)
        if loose and hasattr(loose, "faces"):
            for f in loose.faces:
                if f.attrs.get("hidden"):
                    continue
                if _resolve_mat_name(f.attrs) == cur_mat:
                    _draw_face(f)

        painter.restore()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Cabeçalho
        lbl_head = QLabel(
            "<b>Definição de Shaders PBR Fotorrealistas para o Blender (Cycles / EEVEE)</b><br>"
            "<span style='color: palette(mid); font-size: 11px;'>"
            "Configure como cada material ou chapa do projeto reage à luz (tecidos aveludados, pedras polidas com verniz, veios de madeira, metais e couros).</span>"
        )
        lbl_head.setWordWrap(True)
        layout.addWidget(lbl_head)

        splitter = QSplitter(Qt.Horizontal)

        # ── ESQUERDA: LISTA DE MATERIAIS ENCONTRADOS ──
        w_left = QWidget()
        l_left = QVBoxLayout(w_left)
        l_left.setContentsMargins(0, 0, 0, 0)
        l_left.setSpacing(6)

        lbl_mats = QLabel("<b>Materiais no Projeto:</b>")
        l_left.addWidget(lbl_mats)

        # Botão Conta-gotas 3D direto na lista
        btn_pick_3d = QPushButton("🔍 Capturar do Modelo 3D (Conta-gotas)")
        btn_pick_3d.setToolTip("Clique neste botão e depois clique em qualquer face do 3D para selecionar o material automaticamente.")
        btn_pick_3d.setStyleSheet(
            "QPushButton { background-color: #0284C7; color: white; font-weight: bold; padding: 6px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #0369A1; }"
        )
        btn_pick_3d.clicked.connect(self._activate_picker_tool)
        l_left.addWidget(btn_pick_3d)

        self.list_mats = QListWidget()
        self.list_mats.currentRowChanged.connect(self._on_material_selected)
        l_left.addWidget(self.list_mats, 1)

        splitter.addWidget(w_left)

        # ── DIREITA: PROPRIEDADES DO MATERIAL SELECIONADO ──
        self.box_props = QGroupBox("Propriedades do Shader")
        l_right = QVBoxLayout(self.box_props)
        l_right.setSpacing(10)

        # Card de visualização do Material (Amostra / Preview visual grande)
        f_preview = QFrame()
        f_preview.setStyleSheet("QFrame { background-color: palette(base); border: 1px solid palette(mid); border-radius: 6px; padding: 6px; }")
        l_preview = QHBoxLayout(f_preview)
        l_preview.setContentsMargins(6, 6, 6, 6)
        l_preview.setSpacing(10)

        self.lbl_preview_icon = QLabel()
        self.lbl_preview_icon.setFixedSize(54, 54)
        self.lbl_preview_icon.setAlignment(Qt.AlignCenter)
        self.lbl_preview_icon.setStyleSheet("border: 1px solid palette(dark); border-radius: 4px; background: #e0e0e0;")
        l_preview.addWidget(self.lbl_preview_icon)

        l_prev_text = QVBoxLayout()
        l_prev_text.setSpacing(2)
        self.lbl_prev_title = QLabel("<b>Nome do Material</b>")
        self.lbl_prev_info = QLabel("Tipo: Textura")
        self.lbl_prev_info.setStyleSheet("color: palette(mid); font-size: 11px;")
        l_prev_text.addWidget(self.lbl_prev_title)
        l_prev_text.addWidget(self.lbl_prev_info)
        l_preview.addLayout(l_prev_text, 1)

        l_right.addWidget(f_preview)

        form = QFormLayout()
        form.setSpacing(8)

        # Tipo PBR
        self.cb_type = QComboBox()
        for k, v in MATERIAL_PBR_TYPES.items():
            self.cb_type.addItem(v["label"], k)
        self.cb_type.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("Tipo de Shader:", self.cb_type)

        # Subtipo / Acabamento
        self.cb_subtype = QComboBox()
        self.cb_subtype.currentIndexChanged.connect(self._on_subtype_changed)
        form.addRow("Acabamento:", self.cb_subtype)

        l_right.addLayout(form)

        # Sliders de Ajuste Fino
        l_right.addSpacing(6)
        lbl_adj = QLabel("<b>Ajustes de Reação à Luz:</b>")
        l_right.addWidget(lbl_adj)

        # 1. Rugosidade (Roughness)
        h_rough = QHBoxLayout()
        h_rough.addWidget(QLabel("Rugosidade:"))
        self.sl_rough = QSlider(Qt.Horizontal)
        self.sl_rough.setRange(0, 100)
        self.sl_rough.valueChanged.connect(self._on_slider_changed)
        h_rough.addWidget(self.sl_rough, 1)
        self.lbl_rough_val = QLabel("35%")
        h_rough.addWidget(self.lbl_rough_val)
        l_right.addLayout(h_rough)

        # 2. Refletividade / Especularidade (Specular / Verniz)
        h_spec = QHBoxLayout()
        h_spec.addWidget(QLabel("Refletividade:"))
        self.sl_specular = QSlider(Qt.Horizontal)
        self.sl_specular.setRange(0, 100)
        self.sl_specular.valueChanged.connect(self._on_slider_changed)
        h_spec.addWidget(self.sl_specular, 1)
        self.lbl_specular_val = QLabel("50%")
        h_spec.addWidget(self.lbl_specular_val)
        l_right.addLayout(h_spec)

        # 3. Relevo / Rugosidade Tátil (Bump Map)
        h_bump = QHBoxLayout()
        h_bump.addWidget(QLabel("Relevo Tátil (Bump):"))
        self.sl_bump = QSlider(Qt.Horizontal)
        self.sl_bump.setRange(0, 100)
        self.sl_bump.valueChanged.connect(self._on_slider_changed)
        h_bump.addWidget(self.sl_bump, 1)
        self.lbl_bump_val = QLabel("20%")
        h_bump.addWidget(self.lbl_bump_val)
        l_right.addLayout(h_bump)

        # Descrição explicativa do preset
        self.lbl_desc = QLabel()
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet("background-color: palette(base); border: 1px solid palette(mid); border-radius: 4px; padding: 6px; font-size: 11px;")
        l_right.addWidget(self.lbl_desc)

        l_right.addStretch()

        btn_reset_mat = QPushButton("Restaurar Padrão Deste Material")
        btn_reset_mat.clicked.connect(self._reset_current_material)
        l_right.addWidget(btn_reset_mat)

        splitter.addWidget(self.box_props)
        layout.addWidget(splitter, 1)

        # Rodapé
        h_bot = QHBoxLayout()
        h_bot.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        h_bot.addWidget(btn_cancel)

        btn_save_global = QPushButton("💾 Salvar como Padrão Global")
        btn_save_global.setToolTip("Salva as configurações atuais de materiais como preferência global para todos os novos projetos.")
        btn_save_global.clicked.connect(self._save_as_global_default)
        h_bot.addWidget(btn_save_global)

        btn_ok = QPushButton("Aplicar ao Projeto")
        btn_ok.setToolTip("Aplica as configurações a este projeto e render.")
        btn_ok.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 6px 14px;")
        btn_ok.clicked.connect(self._save_and_close)
        h_bot.addWidget(btn_ok)
        layout.addLayout(h_bot)

    def _load_materials_list(self):
        from pathlib import Path
        self.list_mats.blockSignals(True)
        self.list_mats.clear()
        for item in self._scene_materials:
            name = item["name"]
            disp_name = item["display_name"]
            cfg = self._overrides.get(name, {})
            p_type = cfg.get("type")
            prefix = "✨ " if p_type else "▫️ "
            lbl = f"{prefix}{disp_name}"
            if p_type:
                t_label = MATERIAL_PBR_TYPES.get(p_type, {}).get("label", p_type)
                lbl += f"  [{t_label}]"

            list_item = QListWidgetItem(lbl)

            # Carrega miniatura visual real (Textura ou Cor sólida)
            tex_p = item.get("texture_path")
            col = item.get("color")
            pix = None

            if tex_p and Path(tex_p).exists():
                img = QImage(str(tex_p))
                if not img.isNull():
                    scaled = img.scaled(22, 22, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    # Pega o recorte quadrado central 22x22
                    x = max(0, (scaled.width() - 22) // 2)
                    y = max(0, (scaled.height() - 22) // 2)
                    cropped = scaled.copy(x, y, 22, 22)
                    pix = QPixmap.fromImage(cropped)

            if pix is None:
                pix = QPixmap(22, 22)
                if col:
                    r, g, b = [int(max(0.0, min(1.0, c)) * 255) for c in col[:3]]
                    pix.fill(QColor(r, g, b))
                else:
                    pix.fill(QColor(220, 220, 220))

            list_item.setIcon(QIcon(pix))
            self.list_mats.addItem(list_item)

        self.list_mats.blockSignals(False)

        if self._scene_materials:
            self.list_mats.setCurrentRow(0)
        else:
            self.box_props.setEnabled(False)

    def select_material_by_name(self, mat_name: str) -> bool:
        """Seleciona um material na lista pelo seu identificador ou nome de exibição."""
        for idx, item in enumerate(self._scene_materials):
            if item.get("name") == mat_name or item.get("display_name") == mat_name:
                self.list_mats.setCurrentRow(idx)
                self.raise_()
                self.activateWindow()
                return True
        return False

    def _activate_picker_tool(self):
        """Ativa a ferramenta interativa de conta-gotas 3D no viewport."""
        if not self.viewport:
            return
        from ..interaction.material_picker_tool import MaterialPickerTool
        tool = MaterialPickerTool(on_material_picked_callback=self.select_material_by_name)
        if hasattr(self.viewport, "set_active_tool"):
            self.viewport.set_active_tool(tool)
        elif hasattr(self.viewport, "active_tool"):
            self.viewport.active_tool = tool
            tool.on_activate(self.viewport)

    def _on_material_selected(self, row: int):
        from pathlib import Path
        if not (0 <= row < len(self._scene_materials)):
            self.box_props.setEnabled(False)
            self._current_mat = None
            return

        self.box_props.setEnabled(True)
        mat_item = self._scene_materials[row]
        mat_name = mat_item["name"]
        disp_name = mat_item["display_name"]
        self._current_mat = mat_name
        self.box_props.setTitle(f"Propriedades de: {disp_name}")

        # Atualiza o Card de Visualização / Amostra grande
        tex_path = mat_item.get("texture_path")
        col = mat_item.get("color")
        self.lbl_prev_title.setText(f"<b>{disp_name}</b>")

        big_pix = None
        if tex_path and Path(tex_path).exists():
            img = QImage(str(tex_path))
            if not img.isNull():
                scaled = img.scaled(54, 54, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                x = max(0, (scaled.width() - 54) // 2)
                y = max(0, (scaled.height() - 54) // 2)
                big_pix = QPixmap.fromImage(scaled.copy(x, y, 54, 54))
                file_name = Path(tex_path).name
                self.lbl_prev_info.setText(f"📷 Textura de Imagem: {file_name}")

        if big_pix is None:
            big_pix = QPixmap(54, 54)
            if col:
                r, g, b = [int(max(0.0, min(1.0, c)) * 255) for c in col[:3]]
                big_pix.fill(QColor(r, g, b))
                self.lbl_prev_info.setText(f"🎨 Cor Sólida: RGB({r}, {g}, {b})")
            else:
                big_pix.fill(QColor(225, 225, 225))
                self.lbl_prev_info.setText("▫️ Sem textura (Padrão)")

        self.lbl_preview_icon.setPixmap(big_pix)

        cfg = self._overrides.get(mat_name, {})
        cur_type = cfg.get("type", "auto")

        # Seleciona o tipo no combobox
        idx = self.cb_type.findData(cur_type)
        self.cb_type.blockSignals(True)
        self.cb_type.setCurrentIndex(max(0, idx))
        self.cb_type.blockSignals(False)

        self._populate_subtypes(cur_type)

        rough = float(cfg.get("roughness", MATERIAL_PBR_TYPES.get(cur_type, {}).get("roughness", 0.35)))
        specular = float(cfg.get("specular", MATERIAL_PBR_TYPES.get(cur_type, {}).get("specular", 0.50)))
        bump = float(cfg.get("bump", MATERIAL_PBR_TYPES.get(cur_type, {}).get("bump", 0.02)))

        self.sl_rough.blockSignals(True)
        self.sl_rough.setValue(int(rough * 100))
        self.lbl_rough_val.setText(f"{int(rough * 100)}%")
        self.sl_rough.blockSignals(False)

        self.sl_specular.blockSignals(True)
        self.sl_specular.setValue(int(specular * 100))
        self.lbl_specular_val.setText(f"{int(specular * 100)}%")
        self.sl_specular.blockSignals(False)

        self.sl_bump.blockSignals(True)
        self.sl_bump.setValue(int(bump * 1000))
        self.lbl_bump_val.setText(f"{int(bump * 1000)}%")
        self.sl_bump.blockSignals(False)

        self._update_desc(cur_type)

        if self.viewport is not None:
            self.viewport.update()

    def _populate_subtypes(self, cur_type: str):
        self.cb_subtype.blockSignals(True)
        self.cb_subtype.clear()
        subtypes = MATERIAL_PBR_TYPES.get(cur_type, {}).get("subtypes", ["Padrão"])
        for st in subtypes:
            self.cb_subtype.addItem(st)
        self.cb_subtype.blockSignals(False)

    def _on_type_changed(self):
        if not self._current_mat:
            return
        new_type = self.cb_type.currentData()
        self._populate_subtypes(new_type)
        def_info = MATERIAL_PBR_TYPES.get(new_type, {})
        rough = def_info.get("roughness", 0.35)
        specular = def_info.get("specular", 0.50)
        bump = def_info.get("bump", 0.02)

        self.sl_rough.setValue(int(rough * 100))
        self.sl_specular.setValue(int(specular * 100))
        self.sl_bump.setValue(int(bump * 1000))

        if new_type == "auto":
            if self._current_mat in self._overrides:
                del self._overrides[self._current_mat]
        else:
            self._overrides[self._current_mat] = {
                "type": new_type,
                "sub_type": self.cb_subtype.currentText(),
                "roughness": rough,
                "specular": specular,
                "bump": bump,
            }

        self._update_desc(new_type)
        row = self.list_mats.currentRow()
        self._load_materials_list()
        self.list_mats.setCurrentRow(row)

    def _on_subtype_changed(self):
        if not self._current_mat or self._current_mat not in self._overrides:
            return
        self._overrides[self._current_mat]["sub_type"] = self.cb_subtype.currentText()

    def _on_slider_changed(self):
        if not self._current_mat:
            return
        r_val = self.sl_rough.value() / 100.0
        s_val = self.sl_specular.value() / 100.0
        b_val = self.sl_bump.value() / 1000.0
        self.lbl_rough_val.setText(f"{self.sl_rough.value()}%")
        self.lbl_specular_val.setText(f"{self.sl_specular.value()}%")
        self.lbl_bump_val.setText(f"{self.sl_bump.value() / 10.0:.1f}%")

        if self._current_mat in self._overrides:
            self._overrides[self._current_mat]["roughness"] = r_val
            self._overrides[self._current_mat]["specular"] = s_val
            self._overrides[self._current_mat]["bump"] = b_val

    def _update_desc(self, cur_type: str):
        descs = {
            "auto": "O motor analisa o nome da peça e textura para aplicar relevo e brilho ideais automaticamente.",
            "madeira": "Aplica shader de MDF com veios táteis e opção de laca fosca, acetinada ou alto brilho.",
            "pedra": "Gera camada vitrificada de verniz límpido (Clearcoat) e especularidade de mármores e granitos.",
            "cromado": "Simula reflexão metálica pura espelhada (Roughness 0.02, Metallic 1.0) para metais cromados, dourados e metais sanitários.",
            "metal": "Simula condutividade metálica (Metallic 1.0) e reflexo estriado/escovado em alumínios e puxadores.",
            "plastico": "Simula dielétrico liso ou texturizado com reflexo especular plástico característico (fórmicas e eletrodomésticos).",
            "vidro": "Aplica refração pura (IOR 1.52), reflecta, canelado ou jateado com reflexos realistas.",
            "tecido": "Ativa sombreamento micro-têxtil com penugem nas bordas (Sheen / Velvet) para sofás e cortinas.",
            "couro": "Cria células orgânicas procedurais com toque acetinado suave e relevo tátil.",
            "parede": "Micro-textura suave simulando tinta fosca e rolo de massa acrílica.",
            "ceramica": "Esmalte brilhante vitrificado de cubas, louças sanitárias, azulejos e porcelanatos.",
            "emissivo": "Superfície que emite luz própria no ambiente (fitas LED de sancas, perfis iluminados ou telas)."
        }
        self.lbl_desc.setText(descs.get(cur_type, ""))

    def _reset_current_material(self):
        if self._current_mat and self._current_mat in self._overrides:
            del self._overrides[self._current_mat]
            row = self.list_mats.currentRow()
            self._load_materials_list()
            self.list_mats.setCurrentRow(row)

    def _save_as_global_default(self):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QMessageBox
        import json
        settings = QSettings()
        # Mescla com as globais existentes
        self._global_defaults.update(self._overrides)
        try:
            settings.setValue("trazomob_render/global_material_defaults", json.dumps(self._global_defaults))
            QMessageBox.information(
                self,
                "Padrão Global Salvo",
                f"{len(self._overrides)} acabamentos foram salvos como seu padrão global.\n"
                "Sempre que você criar um novo projeto, essas preferências de reflexo e relevo virão ativas por padrão."
            )
        except Exception as exc:
            QMessageBox.warning(self, "Erro", f"Não foi possível salvar padrão global: {exc}")

    def _save_and_close(self):
        # Salva também no plugin_data da cena atual para persistir dentro do .igz
        if self.scene is not None:
            if not hasattr(self.scene, "plugin_data") or not isinstance(self.scene.plugin_data, dict):
                self.scene.plugin_data = {}
            if "trazomob" not in self.scene.plugin_data or not isinstance(self.scene.plugin_data["trazomob"], dict):
                self.scene.plugin_data["trazomob"] = {}
            self.scene.plugin_data["trazomob"]["material_overrides"] = dict(self._overrides)
            if hasattr(self.scene, "version"):
                self.scene.version += 1

        self.materials_updated.emit(self._overrides)
        self.accept()

    def get_overrides(self) -> dict:
        return dict(self._overrides)


def open_material_editor(viewport=None, parent=None, select_material: str | None = None) -> MaterialEditorDialog | None:
    """Abre ou traz à frente o diálogo de Materiais PBR do TrazoMob, opcionalmente selecionando um material."""
    scene = getattr(viewport, "scene", None) if viewport else None
    if scene is None:
        return None

    win = viewport.window() if viewport and hasattr(viewport, "window") else parent
    dlg = getattr(win, "_trazomob_material_dialog", None)
    
    current_overrides = None
    if hasattr(scene, "plugin_data") and isinstance(scene.plugin_data, dict):
        tm_data = scene.plugin_data.get("trazomob", {})
        if isinstance(tm_data, dict):
            current_overrides = tm_data.get("material_overrides")

    if dlg is None or not dlg.isVisible():
        dlg = MaterialEditorDialog(scene, current_overrides=current_overrides, viewport=viewport, parent=win)
        if win is not None:
            win._trazomob_material_dialog = dlg
        dlg.show()
    else:
        dlg.raise_()
        dlg.activateWindow()

    if select_material:
        dlg.select_material_by_name(select_material)

    return dlg

