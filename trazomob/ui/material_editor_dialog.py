# SPDX-License-Identifier: GPL-3.0-or-later
"""Editor e Gerenciador de Materiais PBR do TrazoMob para Renderização no Blender.

Permite listar todos os materiais da cena atual e configurar:
- Tipo PBR: Madeira/MDF, Mármore/Pedra, Tecido/Estofado, Metal, Vidro, Couro, Tinta de Parede
- Subtipos e Acabamentos: Laca Brilhante, Acetinada, Fosca, Polida, Levigada, Veludo, Escovado
- Sliders: Rugosidade (Roughness), Especular/Verniz (Clearcoat) e Intensidade de Relevo (Bump)
"""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
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
    "tapete": {
        "label": "Tapete / Carpete",
        "roughness": 0.88,
        "specular": 0.08,
        "bump": 0.055,
        "subtypes": [
            "Tapete / Carpete Felpudo — Pelo Alto (Shaggy 3D)",
            "Tapete / Carpete Felpudo — Pelo Curto / Aveludado (3D)",
            "Sem Pelos — Tapete Liso / Trama Baixa (Sisal / Kilim)",
            "Sem Pelos — Carpete Comercial / Bouclê (Trama Fechada)",
        ]
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


def _resolve_mat_name(attrs: dict | None) -> str:
    """Resolve o identificador amigável de material a partir dos atributos efetivos."""
    from pathlib import Path

    if not attrs:
        return "Padrão (Sem Acabamento)"
    mat_name = attrs.get("mat")
    tex = attrs.get("texture")
    col = attrs.get("color")
    tex_path = tex.get("path") if (isinstance(tex, dict) and tex.get("path")) else None

    if mat_name:
        return str(mat_name)
    if tex_path:
        return Path(tex_path).stem
    if col:
        r, g, b = [int(max(0.0, min(1.0, c)) * 255) for c in col[:3]]
        return f"Cor #{r:02X}{g:02X}{b:02X}"
    return "Padrão (Sem Acabamento)"


def _register_material_entry(
    materials_dict: dict[str, dict[str, Any]],
    attrs: dict | None,
    *,
    owner_name: str | None = None,
    owner_group: Any = None,
) -> None:
    """Registra um material em ``materials_dict`` e vincula seu objeto dono."""
    if not attrs:
        return
    name = _resolve_mat_name(attrs)
    raw_op = attrs.get("opacity")
    op_val = float(raw_op) if raw_op is not None else 1.0
    entry = materials_dict.get(name)
    if entry is None:
        tex = attrs.get("texture")
        col = attrs.get("color")
        tex_path = tex.get("path") if (isinstance(tex, dict) and tex.get("path")) else None
        entry = {
            "name": name,
            "display_name": name,
            "color": tuple(col[:3]) if col else None,
            "texture_path": tex_path,
            "finish": attrs.get("finish"),
            "opacity": op_val,
            "owners": [],
            "owner_groups": [],
        }
        materials_dict[name] = entry
    elif raw_op is not None and entry.get("opacity", 1.0) >= 0.999:
        entry["opacity"] = op_val
    if owner_name and owner_name not in entry["owners"]:
        entry["owners"].append(owner_name)
    if owner_group is not None and owner_group not in entry["owner_groups"]:
        entry["owner_groups"].append(owner_group)


def _mesh_unique_attrs(
    mesh: Any,
    paint: Any,
    cache: dict[tuple[int, int], list[dict]],
) -> list[dict]:
    """Extrai os dicionários de atributos efetivos únicos de ``mesh`` com cache por ``(id(mesh), id(paint))``."""
    from core.materials import effective_attrs
    from core.mesh import face_attrs

    cache_key = (id(mesh), id(paint))
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    unique_attrs: dict[str, dict] = {}
    for f_attrs in face_attrs(mesh):
        if not isinstance(f_attrs, dict):
            continue
        if f_attrs.get("hidden") or f_attrs.get("igz_link_placeholder"):
            continue
        eff = effective_attrs(f_attrs, paint) if paint else f_attrs
        if not eff:
            continue
        mat_key = _resolve_mat_name(eff)
        if mat_key not in unique_attrs:
            unique_attrs[mat_key] = eff

    result = list(unique_attrs.values())
    cache[cache_key] = result
    return result


def _collect_group_materials(
    group: Any,
    materials_dict: dict[str, dict[str, Any]],
    mesh_attrs_cache: dict[tuple[int, int], list[dict]],
    *,
    top_group: Any = None,
) -> None:
    """Varre placements de ``group`` sem materializar ``DeferredMesh`` nem clonar geometria."""
    from core.group import iter_painted_placements

    root_owner = top_group if top_group is not None else group
    root_name = str(getattr(root_owner, "name", "") or "").strip()

    for placement, _m, paint in iter_painted_placements(group):
        p_name = str(getattr(placement, "name", "") or "").strip() or root_name or "Objeto"
        if paint:
            _register_material_entry(
                materials_dict,
                paint,
                owner_name=p_name,
                owner_group=root_owner,
            )
        mesh = getattr(placement, "mesh", None)
        if mesh is None or getattr(mesh, "_is_link_placeholder", False):
            continue
        for eff in _mesh_unique_attrs(mesh, paint, mesh_attrs_cache):
            _register_material_entry(
                materials_dict,
                eff,
                owner_name=p_name,
                owner_group=root_owner,
            )


def extract_scene_materials(scene) -> list[dict]:
    """Extrai todos os materiais e texturas reais usados na cena, retornando lista de dicts com metadados.

    Cada item retornado possui:
    {
        'name': str,          # Nome de identificação (ex: 'Nogueira_Cacau', 'Branco_Fosco', 'Tinta_Suvinil')
        'display_name': str,  # Nome amigável para exibição
        'color': tuple|None,  # RGB (0..1)
        'texture_path': str|None, # Caminho da imagem se tiver
        'finish': str|None,   # Finish pré-definido se houver
        'owners': list[str],  # Objetos que utilizam este material
        'owner_groups': list, # Referências aos grupos donos na cena
    }
    """
    from core.mesh import face_attrs

    materials_dict: dict[str, dict[str, Any]] = {}

    # 1. Varre os materiais cadastrados no registro da cena (scene.materials)
    registry = getattr(scene, "materials", None) or {}
    for name, mat in registry.items():
        if name and name not in materials_dict:
            tex_p = getattr(mat, "texture", {})
            path = tex_p.get("path") if isinstance(tex_p, dict) else None
            mat_op = getattr(mat, "opacity", None)
            materials_dict[name] = {
                "name": name,
                "display_name": name,
                "color": getattr(mat, "color", None),
                "texture_path": path,
                "finish": getattr(mat, "finish", None),
                "opacity": float(mat_op) if mat_op is not None else 1.0,
                "owners": [],
                "owner_groups": [],
            }

    # 2. Varre faces soltas (sem materializar DeferredMesh)
    loose_mesh = getattr(scene, "loose_mesh", None)
    if loose_mesh is None:
        loose_mesh = getattr(scene, "mesh", None)
    if loose_mesh is not None and not getattr(loose_mesh, "_is_link_placeholder", False):
        for f_attrs in face_attrs(loose_mesh):
            if not isinstance(f_attrs, dict):
                continue
            if f_attrs.get("hidden") or f_attrs.get("igz_link_placeholder"):
                continue
            _register_material_entry(materials_dict, f_attrs, owner_name="Geometria solta")

    # 3. Varre grupos e componentes com herança de pintura sem clonar para coordenadas do mundo
    ent_vis = getattr(scene, "entity_visible", None)
    mesh_attrs_cache: dict[tuple[int, int], list[dict]] = {}
    for g in getattr(scene, "groups", []):
        if callable(ent_vis) and not ent_vis(g):
            continue
        _collect_group_materials(g, materials_dict, mesh_attrs_cache, top_group=g)

    # Ordena: nomeados primeiro, depois por ordem alfabética
    return sorted(list(materials_dict.values()), key=lambda m: m["display_name"].lower())


def extract_group_materials(group) -> list[dict[str, Any]]:
    """Extrai todos os materiais e texturas usados em um único Group (e seus filhos)."""
    if group is None:
        return []
    materials_dict: dict[str, dict[str, Any]] = {}
    _collect_group_materials(group, materials_dict, {}, top_group=group)
    return sorted(list(materials_dict.values()), key=lambda m: m["display_name"].lower())


class _ViewportEyedropperFilter(QObject):
    """Captura um clique no viewport 3D para selecionar o material sob o cursor."""

    def __init__(self, dialog: "MaterialEditorDialog", viewport: Any) -> None:
        super().__init__(dialog)
        self._dialog = dialog
        self._viewport = viewport

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        etype = event.type()
        if etype == QEvent.MouseButtonPress:
            btn = event.button()
            if btn == Qt.LeftButton:
                pos = event.position().toPoint()
                self._dialog._finish_eyedropper(pos.x(), pos.y())
                return True
            if btn == Qt.RightButton:
                self._dialog._cancel_eyedropper()
                return True
        elif etype == QEvent.KeyPress and event.key() == Qt.Key_Escape:
            self._dialog._cancel_eyedropper()
            return True
        return False


class MaterialEditorDialog(QDialog):
    """Diálogo visual para editar e atribuir shaders PBR aos materiais da cena ou de um componente."""

    materials_updated = Signal(dict)

    def __init__(
        self,
        scene=None,
        current_overrides: dict | None = None,
        viewport=None,
        parent=None,
        group=None,
    ):
        super().__init__(parent)
        self.scene = scene
        self.viewport = viewport
        self._group = group
        self._eyedropper_filter: _ViewportEyedropperFilter | None = None
        self._overrides = dict(current_overrides or {})
        if group is not None:
            gname = getattr(group, "name", "") or "Objeto"
            self.setWindowTitle(f"🎨 TrazoMob — Materiais & Shaders PBR ({gname})")
        else:
            self.setWindowTitle("🎨 TrazoMob — Configuração de Materiais & Shaders PBR (Blender)")
        self.setMinimumSize(780, 520)

        import json

        from PySide6.QtCore import QSettings
        settings = QSettings()
        raw_globals = settings.value("trazomob_render/global_material_defaults", "{}")
        try:
            self._global_defaults = json.loads(raw_globals) if isinstance(raw_globals, str) else {}
        except Exception:
            self._global_defaults = {}

        if group is not None:
            self._scene_materials = extract_group_materials(group)
        elif scene is not None:
            self._scene_materials = extract_scene_materials(scene)
        else:
            self._scene_materials = []
        self._current_mat: str | None = None
        self._highlight_active = False
        self._icon_cache: dict = {}
        self._preview_cache: dict = {}
        self._highlight_cache_key = None
        self._highlight_loops: list = []

        # Registra overlay de destaque no viewport se disponível
        self._setup_viewport_overlay()

        self._build_ui()
        self._load_materials_list()

    def _setup_viewport_overlay(self):
        if not self._highlight_active:
            return
        if self.viewport is not None:
            from trazomob.integrations.platform import register_viewport_overlay
            register_viewport_overlay(self.viewport, self._draw_material_highlight)

    def _cleanup_viewport_overlay(self):
        if self.viewport is not None and hasattr(self.viewport, "_ext_overlays"):
            from trazomob.integrations.platform import unregister_viewport_overlay
            unregister_viewport_overlay(self.viewport, self._draw_material_highlight)
            self.viewport.update()

    def _cleanup_eyedropper(self):
        if self._eyedropper_filter is not None and self.viewport is not None:
            try:
                self.viewport.removeEventFilter(self._eyedropper_filter)
            except Exception:
                pass
            if hasattr(self.viewport, "unsetCursor"):
                self.viewport.unsetCursor()
        self._eyedropper_filter = None

    def _start_eyedropper(self):
        if self.viewport is None or not hasattr(self.viewport, "pick_face_any"):
            return
        self._cleanup_eyedropper()
        self._eyedropper_filter = _ViewportEyedropperFilter(self, self.viewport)
        self.viewport.installEventFilter(self._eyedropper_filter)
        if hasattr(self.viewport, "setCursor"):
            self.viewport.setCursor(Qt.CrossCursor)
        self.hide()

    def _cancel_eyedropper(self):
        self._cleanup_eyedropper()
        self.show()
        self.raise_()
        self.activateWindow()

    def _finish_eyedropper(self, px: int, py: int):
        from core.group import effective_material
        from core.materials import effective_attrs

        self._cleanup_eyedropper()
        hit_face, hit_grp = None, None
        try:
            hit_face, hit_grp = self.viewport.pick_face_any(px, py)
        except Exception:
            pass

        self.show()
        self.raise_()
        self.activateWindow()

        if hit_face is None:
            return
        paint = effective_material(hit_grp) if hit_grp is not None else None
        f_attrs = getattr(hit_face, "attrs", None) or {}
        eff = effective_attrs(f_attrs, paint) if paint else f_attrs
        self.select_material_by_name(_resolve_mat_name(eff))

    def closeEvent(self, event):
        self._cleanup_eyedropper()
        self._cleanup_viewport_overlay()
        super().closeEvent(event)

    def reject(self):
        self._cleanup_eyedropper()
        self._cleanup_viewport_overlay()
        super().reject()

    def accept(self):
        self._cleanup_viewport_overlay()
        super().accept()

    _MAX_HIGHLIGHT_POLYS = 6000

    @staticmethod
    def _mesh_uses_material(mesh: Any, paint: Any, cur_mat: str) -> bool:
        """Verifica sem materializar ``DeferredMesh`` se alguma face efetiva usa ``cur_mat``."""
        from core.materials import effective_attrs
        from core.mesh import face_attrs

        if paint and _resolve_mat_name(paint) == cur_mat:
            return True
        for f_attrs in face_attrs(mesh):
            if not isinstance(f_attrs, dict):
                continue
            if f_attrs.get("hidden") or f_attrs.get("igz_link_placeholder"):
                continue
            eff = effective_attrs(f_attrs, paint) if paint else f_attrs
            if _resolve_mat_name(eff) == cur_mat:
                return True
        return False

    @staticmethod
    def _deferred_matching_loops(mesh: Any, m: Any, paint: Any, cur_mat: str, remaining: int) -> list:
        """Extrai anéis externos em coordenadas do mundo de ``DeferredMesh`` sem materializá-la."""
        import numpy as np
        from PySide6.QtGui import QVector3D

        from core.group import np_affine
        from core.materials import effective_attrs
        from trazomob.integrations.platform import face_attrs_from_json

        src = mesh.__dict__.get("_deferred_source")
        if not isinstance(src, dict):
            return []
        table = src["meta"].get("face_attrs") or []
        matching_ids: set[int] = set()
        for k, raw in enumerate(table):
            parsed = face_attrs_from_json(raw) or {}
            eff = effective_attrs(parsed, paint) if paint else parsed
            if eff.get("hidden") or eff.get("igz_link_placeholder"):
                continue
            if _resolve_mat_name(eff) == cur_mat:
                matching_ids.add(k)
        empty_eff = effective_attrs({}, paint) if paint else {}
        if empty_eff and not empty_eff.get("hidden") and not empty_eff.get("igz_link_placeholder"):
            if _resolve_mat_name(empty_eff) == cur_mat:
                matching_ids.add(-1)
        if not matching_ids:
            return []

        fa = np.asarray(src["face_attr"], dtype=np.int64)
        mask = np.isin(fa, list(matching_ids))
        face_indices = np.flatnonzero(mask)
        if not len(face_indices):
            return []
        if remaining > 0 and len(face_indices) > remaining:
            step = max(1, len(face_indices) // remaining)
            face_indices = face_indices[::step][:remaining]

        pos = src["pos"]
        rings = src["rings"]
        sizes = src["sizes"]
        counts = src["counts"]
        ring_start = np.concatenate(([0], np.cumsum(sizes)))
        face_ring = np.concatenate(([0], np.cumsum(counts)))
        rot, trans = np_affine(m) if m is not None else (None, None)

        loops: list = []
        for fi in face_indices.tolist():
            r_idx = int(face_ring[fi])
            s0 = int(ring_start[r_idx])
            s1 = int(ring_start[r_idx + 1])
            if s1 - s0 < 3:
                continue
            pts = pos[rings[s0:s1]]
            if rot is not None:
                pts = pts @ rot.T + trans
            loops.append([QVector3D(float(x), float(y), float(z)) for x, y, z in pts.tolist()])
        return loops

    def _collect_mesh_highlight_loops(self, mesh: Any, m: Any, paint: Any, cur_mat: str, remaining: int) -> list:
        """Extrai anéis em coordenadas do mundo das faces de ``mesh`` que usam ``cur_mat``."""
        from core.materials import effective_attrs
        from core.mesh import DeferredMesh

        if mesh is None or getattr(mesh, "_is_link_placeholder", False):
            return []
        if not MaterialEditorDialog._mesh_uses_material(mesh, paint, cur_mat):
            return []
        if type(mesh) is DeferredMesh:
            return MaterialEditorDialog._deferred_matching_loops(mesh, m, paint, cur_mat, remaining)

        loops: list = []
        for f in getattr(mesh, "faces", ()):
            f_attrs = getattr(f, "attrs", None) or {}
            eff = effective_attrs(f_attrs, paint) if paint else f_attrs
            if eff.get("hidden") or eff.get("igz_link_placeholder"):
                continue
            if _resolve_mat_name(eff) == cur_mat:
                verts = getattr(f, "vertices", ())
                if len(verts) >= 3:
                    loops.append([
                        m.map(v) if m is not None else v
                        for v in verts
                    ])
        return loops

    def _get_highlight_loops(self, cur_mat: str) -> list:
        """Retorna loops em coordenadas do mundo para ``cur_mat``, com cache por cena/material."""
        key = (cur_mat, getattr(self.scene, "version", None), id(self._group))
        if getattr(self, "_highlight_cache_key", None) == key and hasattr(self, "_highlight_loops"):
            return self._highlight_loops

        from core.group import iter_painted_placements
        from core.mesh import DeferredMesh

        loops: list = []
        budget = MaterialEditorDialog._MAX_HIGHLIGHT_POLYS

        if self._group is not None:
            for p, m, paint in iter_painted_placements(self._group):
                loops.extend(MaterialEditorDialog._collect_mesh_highlight_loops(self, p.mesh, m, paint, cur_mat, budget))
        elif self.scene is not None:
            ent_vis = getattr(self.scene, "entity_visible", None)
            loose_mesh = getattr(self.scene, "loose_mesh", None)
            if loose_mesh is None:
                loose_mesh = getattr(self.scene, "mesh", None)
            if loose_mesh is not None:
                if type(loose_mesh) is DeferredMesh or not callable(ent_vis):
                    loops.extend(MaterialEditorDialog._collect_mesh_highlight_loops(self, loose_mesh, None, None, cur_mat, budget))
                else:
                    for f in getattr(loose_mesh, "faces", ()):
                        if not ent_vis(f):
                            continue
                        f_attrs = getattr(f, "attrs", None) or {}
                        if f_attrs.get("hidden") or f_attrs.get("igz_link_placeholder"):
                            continue
                        if _resolve_mat_name(f_attrs) == cur_mat:
                            verts = getattr(f, "vertices", ())
                            if len(verts) >= 3:
                                loops.append(list(verts))
            for g in getattr(self.scene, "groups", []):
                if callable(ent_vis) and not ent_vis(g):
                    continue
                for p, m, paint in iter_painted_placements(g):
                    loops.extend(MaterialEditorDialog._collect_mesh_highlight_loops(self, p.mesh, m, paint, cur_mat, budget))

        if len(loops) > budget:
            step = max(1, len(loops) // budget)
            loops = loops[::step][:budget]

        self._highlight_cache_key = key
        self._highlight_loops = loops
        return loops

    def _draw_material_highlight(self, viewport, painter: QPainter):
        """Desenha contorno e realce sobre todas as faces do material selecionado na lista."""
        if not self._highlight_active or not self._current_mat or self.scene is None:
            return

        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QBrush, QColor, QPen, QPolygonF

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        # Contorno ciano brilhante (#00D4FF) e preenchimento suave
        pen = QPen(QColor(0, 212, 255, 230), 2.2, Qt.SolidLine)
        brush = QBrush(QColor(0, 212, 255, 45))
        painter.setPen(pen)
        painter.setBrush(brush)

        for loop in MaterialEditorDialog._get_highlight_loops(self, self._current_mat):
            pts_2d = []
            for v in loop:
                px = viewport.world_to_pixel(v)
                if px is not None:
                    pts_2d.append(QPointF(px[0], px[1]))
                else:
                    pts_2d = []
                    break
            if len(pts_2d) >= 3:
                painter.drawPolygon(QPolygonF(pts_2d))

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

        lbl_mats = QLabel(
            "<b>Materiais do Objeto:</b>" if self._group is not None else "<b>Materiais no Projeto:</b>"
        )
        l_left.addWidget(lbl_mats)

        # Botão Conta-gotas 3D direto na lista
        self.btn_pick_3d = QPushButton("🔍 Capturar do Modelo 3D (Conta-gotas)")
        self.btn_pick_3d.setToolTip("Clique neste botão e depois clique em qualquer face do 3D para selecionar o material automaticamente.")
        self.btn_pick_3d.setStyleSheet(
            "QPushButton { background-color: #0284C7; color: white; font-weight: bold; padding: 6px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #0369A1; }"
        )
        self.btn_pick_3d.clicked.connect(self._activate_picker_tool)
        self.btn_pick_3d.setVisible(self.viewport is not None)
        l_left.addWidget(self.btn_pick_3d)

        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("Filtrar material, textura ou objeto…")
        self.txt_filter.setClearButtonEnabled(True)
        self.txt_filter.textChanged.connect(self._apply_filter)
        l_left.addWidget(self.txt_filter)

        self.list_mats = QListWidget()
        self.list_mats.setUniformItemSizes(True)
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
        self.lbl_prev_owners = QLabel("")
        self.lbl_prev_owners.setWordWrap(True)
        self.lbl_prev_owners.setStyleSheet("color: palette(text); font-size: 11px;")
        l_prev_text.addWidget(self.lbl_prev_title)
        l_prev_text.addWidget(self.lbl_prev_info)
        l_prev_text.addWidget(self.lbl_prev_owners)
        l_preview.addLayout(l_prev_text, 1)

        self.btn_select_owner = QPushButton("🎯 Selecionar Objeto no 3D")
        self.btn_select_owner.setToolTip("Seleciona na cena 3D o(s) objeto(s) que utilizam este material.")
        self.btn_select_owner.clicked.connect(self._select_owner_in_scene)
        self.btn_select_owner.setVisible(self.viewport is not None)
        l_preview.addWidget(self.btn_select_owner)

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

        # 4. Opacidade / Transparência (3D + Render)
        h_opac = QHBoxLayout()
        h_opac.addWidget(QLabel("Opacidade:"))
        self.sl_opacity = QSlider(Qt.Horizontal)
        self.sl_opacity.setRange(5, 100)
        self.sl_opacity.setValue(100)
        self.sl_opacity.valueChanged.connect(self._on_slider_changed)
        h_opac.addWidget(self.sl_opacity, 1)
        self.lbl_opacity_val = QLabel("100%")
        h_opac.addWidget(self.lbl_opacity_val)
        l_right.addLayout(h_opac)

        # 5. Emissive Intensity / Power (emissive shader only)
        self.emission_widget = QWidget()
        h_emit = QHBoxLayout(self.emission_widget)
        h_emit.setContentsMargins(0, 0, 0, 0)
        h_emit.addWidget(QLabel(tr("Potência da Luz:")))
        self.sl_emission = QSlider(Qt.Horizontal)
        self.sl_emission.setRange(1, 300)
        self.sl_emission.setValue(80)
        self.sl_emission.valueChanged.connect(self._on_slider_changed)
        h_emit.addWidget(self.sl_emission, 1)
        self.lbl_emission_val = QLabel("8.0")
        h_emit.addWidget(self.lbl_emission_val)
        self.emission_widget.setVisible(False)
        l_right.addWidget(self.emission_widget)

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

    @staticmethod
    def _format_owners_summary(owners: list[str] | None, *, limit: int = 2) -> str:
        clean = [o for o in (owners or ()) if o]
        if not clean:
            return ""
        if len(clean) <= limit:
            return ", ".join(clean)
        return f"{', '.join(clean[:limit])} (+{len(clean) - limit})"

    def _material_item_label(self, item: dict) -> str:
        disp_name = item["display_name"]
        cfg = self._overrides.get(item["name"], {})
        p_type = cfg.get("type")
        prefix = "✨ " if p_type else "▫️ "
        lbl = f"{prefix}{disp_name}"
        if p_type:
            t_label = MATERIAL_PBR_TYPES.get(p_type, {}).get("label", p_type)
            if p_type == "tapete":
                sub = str(cfg.get("sub_type") or "").lower()
                if any(k in sub for k in ("sem pelos", "liso", "trama baixa", "sisal", "kilim", "boucl", "comercial")):
                    lbl += f"  [{t_label} — Sem Pelos]"
                elif "pelo curto" in sub or "aveludado" in sub:
                    lbl += f"  [{t_label} — Felpudo Curto]"
                else:
                    lbl += f"  [{t_label} — Felpudo]"
            else:
                lbl += f"  [{t_label}]"
        owners_text = self._format_owners_summary(item.get("owners"))
        if owners_text:
            lbl += f" — {owners_text}"
        return lbl

    def _material_item_tooltip(self, item: dict) -> str:
        parts = [item["display_name"]]
        if item.get("texture_path"):
            from pathlib import Path
            parts.append(f"Textura: {Path(item['texture_path']).name}")
        owners = [o for o in (item.get("owners") or ()) if o]
        if owners:
            parts.append(f"Usado em: {', '.join(owners)}")
        return "\n".join(parts)

    def _apply_filter(self, text: str = "") -> None:
        needle = (text or "").strip().casefold()
        for row, item in enumerate(self._scene_materials):
            list_item = self.list_mats.item(row)
            if list_item is None:
                continue
            if not needle:
                list_item.setHidden(False)
                continue
            haystack = " ".join([
                str(item.get("display_name") or ""),
                str(item.get("name") or ""),
                str(item.get("texture_path") or ""),
                " ".join(str(o) for o in (item.get("owners") or ())),
            ]).casefold()
            list_item.setHidden(needle not in haystack)

    def _build_swatch_pixmap(self, tex_p: str | None, col: tuple | None, size: int, default_gray: int) -> QPixmap:
        from pathlib import Path

        if tex_p and Path(tex_p).exists():
            img = QImage(str(tex_p))
            if not img.isNull():
                scaled = img.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                x = max(0, (scaled.width() - size) // 2)
                y = max(0, (scaled.height() - size) // 2)
                return QPixmap.fromImage(scaled.copy(x, y, size, size))

        pix = QPixmap(size, size)
        if col:
            r, g, b = [int(max(0.0, min(1.0, c)) * 255) for c in col[:3]]
            pix.fill(QColor(r, g, b))
        else:
            pix.fill(QColor(default_gray, default_gray, default_gray))
        return pix

    def _get_material_icon(self, item: dict) -> QIcon:
        tex_p = item.get("texture_path")
        col = item.get("color")
        key = (tex_p, col)
        icon = self._icon_cache.get(key)
        if icon is None:
            icon = QIcon(self._build_swatch_pixmap(tex_p, col, 22, 220))
            self._icon_cache[key] = icon
        return icon

    def _refresh_row_label(self, row: int) -> None:
        if not (0 <= row < self.list_mats.count() and row < len(self._scene_materials)):
            return
        list_item = self.list_mats.item(row)
        if list_item is not None:
            list_item.setText(self._material_item_label(self._scene_materials[row]))

    def _load_materials_list(self):
        self.list_mats.blockSignals(True)
        self.list_mats.clear()
        for item in self._scene_materials:
            list_item = QListWidgetItem(self._material_item_label(item))
            list_item.setIcon(self._get_material_icon(item))
            list_item.setToolTip(self._material_item_tooltip(item))
            self.list_mats.addItem(list_item)

        self.list_mats.blockSignals(False)
        self._apply_filter(self.txt_filter.text() if hasattr(self, "txt_filter") else "")

        if self._scene_materials:
            self.list_mats.setCurrentRow(0)
        else:
            self.box_props.setEnabled(False)

    def select_material_by_name(self, mat_name: str) -> bool:
        """Seleciona um material na lista pelo seu identificador ou nome de exibição."""
        for idx, item in enumerate(self._scene_materials):
            if item.get("name") == mat_name or item.get("display_name") == mat_name:
                list_item = self.list_mats.item(idx)
                if list_item is not None and list_item.isHidden() and hasattr(self, "txt_filter"):
                    self.txt_filter.clear()
                self.list_mats.setCurrentRow(idx)
                self.show()
                self.raise_()
                self.activateWindow()
                return True
        return False

    def _activate_picker_tool(self):
        """Ativa a ferramenta interativa de conta-gotas 3D no viewport."""
        if not self.viewport:
            return
        from ..interaction.material_picker_tool import MaterialPickerTool
        prev_tool = getattr(self.viewport, "active_tool", None)
        if isinstance(prev_tool, MaterialPickerTool):
            prev_tool = getattr(prev_tool, "_prev_tool", None)
        tool = MaterialPickerTool(
            on_material_picked_callback=self.select_material_by_name,
            prev_tool=prev_tool,
        )
        if hasattr(self.viewport, "set_active_tool"):
            self.viewport.set_active_tool(tool)
        elif hasattr(self.viewport, "active_tool"):
            self.viewport.active_tool = tool
            tool.on_activate(self.viewport)
        vp_win = self.viewport.window() if hasattr(self.viewport, "window") else None
        if vp_win is not None and vp_win is not self:
            if hasattr(vp_win, "raise_"):
                vp_win.raise_()
            if hasattr(vp_win, "activateWindow"):
                vp_win.activateWindow()
        if hasattr(self.viewport, "setFocus"):
            self.viewport.setFocus()

    def _select_owner_in_scene(self) -> None:
        """Seleciona no viewport 3D os objetos que utilizam o material atual."""
        if self.viewport is None or self.scene is None:
            return
        row = self.list_mats.currentRow()
        if not (0 <= row < len(self._scene_materials)):
            return
        owners = [g for g in (self._scene_materials[row].get("owner_groups") or []) if g is not None]
        if not owners:
            return
        if hasattr(self.scene, "select"):
            self.scene.select(owners, mode="replace")
        else:
            self.scene.selection = set(owners)
        if hasattr(self.viewport, "notify_scene_changed"):
            self.viewport.notify_scene_changed()
        elif hasattr(self.viewport, "update"):
            self.viewport.update()

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

        if tex_path and Path(tex_path).exists():
            file_name = Path(tex_path).name
            self.lbl_prev_info.setText(f"📷 Textura de Imagem: {file_name}")
        elif col:
            r, g, b = [int(max(0.0, min(1.0, c)) * 255) for c in col[:3]]
            self.lbl_prev_info.setText(f"🎨 Cor Sólida: RGB({r}, {g}, {b})")
        else:
            self.lbl_prev_info.setText("▫️ Sem textura (Padrão)")

        owners = [o for o in (mat_item.get("owners") or ()) if o]
        if hasattr(self, "lbl_prev_owners"):
            self.lbl_prev_owners.setText(
                f"📦 Usado em: {', '.join(owners)}" if owners else ""
            )
            self.lbl_prev_owners.setVisible(bool(owners))
        if hasattr(self, "btn_select_owner"):
            has_group = bool(mat_item.get("owner_groups"))
            self.btn_select_owner.setEnabled(has_group)

        prev_key = (tex_path, col)
        big_pix = self._preview_cache.get(prev_key)
        if big_pix is None:
            big_pix = self._build_swatch_pixmap(tex_path, col, 54, 225)
            self._preview_cache[prev_key] = big_pix

        self.lbl_preview_icon.setPixmap(big_pix)

        cfg = self._overrides.get(mat_name, {})
        cur_type = cfg.get("type", "auto")

        # Seleciona o tipo no combobox
        idx = self.cb_type.findData(cur_type)
        self.cb_type.blockSignals(True)
        self.cb_type.setCurrentIndex(max(0, idx))
        self.cb_type.blockSignals(False)

        self._populate_subtypes(cur_type)
        saved_sub = str(cfg.get("sub_type") or "")
        if saved_sub:
            sub_idx = self.cb_subtype.findText(saved_sub)
            if sub_idx >= 0:
                self.cb_subtype.blockSignals(True)
                self.cb_subtype.setCurrentIndex(sub_idx)
                self.cb_subtype.blockSignals(False)

        rough = float(cfg.get("roughness", MATERIAL_PBR_TYPES.get(cur_type, {}).get("roughness", 0.35)))
        specular = float(cfg.get("specular", MATERIAL_PBR_TYPES.get(cur_type, {}).get("specular", 0.50)))
        bump = float(cfg.get("bump", MATERIAL_PBR_TYPES.get(cur_type, {}).get("bump", 0.02)))
        base_op = float(mat_item.get("opacity", 1.0) if mat_item.get("opacity") is not None else 1.0)
        opacity = float(cfg.get("opacity", base_op) if cfg.get("opacity") is not None else base_op)
        op_pct = max(5, min(100, int(round(opacity * 100))))

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

        self.sl_opacity.blockSignals(True)
        self.sl_opacity.setValue(op_pct)
        self.lbl_opacity_val.setText(f"{op_pct}%")
        self.sl_opacity.blockSignals(False)

        self.emission_widget.setVisible(cur_type == "emissivo")
        default_emit = 2.4 if "painel" in str(cfg.get("sub_type", "")).lower() else 8.0
        emit_val = float(cfg.get("emission_strength", default_emit))
        emit_slider = max(1, min(300, int(round(emit_val * 10))))
        self.sl_emission.blockSignals(True)
        self.sl_emission.setValue(emit_slider)
        self.lbl_emission_val.setText(f"{emit_slider / 10.0:.1f}")
        self.sl_emission.blockSignals(False)

        self._update_desc(cur_type)

        if self._highlight_active and self.viewport is not None:
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

        mat_item = next(
            (m for m in self._scene_materials if m.get("name") == self._current_mat),
            None,
        )
        base_op = float(
            mat_item.get("opacity", 1.0)
            if mat_item and mat_item.get("opacity") is not None
            else 1.0
        )
        base_pct = max(5, min(100, int(round(base_op * 100))))
        op_pct = self.sl_opacity.value()
        op_val = round(op_pct / 100.0, 4)

        self.sl_rough.setValue(int(rough * 100))
        self.sl_specular.setValue(int(specular * 100))
        self.sl_bump.setValue(int(bump * 1000))

        if new_type == "auto":
            if op_pct != base_pct:
                self._overrides[self._current_mat] = {
                    "type": "auto",
                    "sub_type": self.cb_subtype.currentText(),
                    "roughness": rough,
                    "specular": specular,
                    "bump": bump,
                    "opacity": op_val,
                }
            elif self._current_mat in self._overrides:
                del self._overrides[self._current_mat]
        else:
            entry = {
                "type": new_type,
                "sub_type": self.cb_subtype.currentText(),
                "roughness": rough,
                "specular": specular,
                "bump": bump,
            }
            if op_pct < 100 or op_pct != base_pct:
                entry["opacity"] = op_val
            self._overrides[self._current_mat] = entry

        self._update_desc(new_type)
        self._refresh_row_label(self.list_mats.currentRow())

    def _on_subtype_changed(self):
        if not self._current_mat or self._current_mat not in self._overrides:
            return
        self._overrides[self._current_mat]["sub_type"] = self.cb_subtype.currentText()
        self._refresh_row_label(self.list_mats.currentRow())

    def _on_slider_changed(self):
        if not self._current_mat:
            return
        r_val = self.sl_rough.value() / 100.0
        s_val = self.sl_specular.value() / 100.0
        b_val = self.sl_bump.value() / 1000.0
        op_pct = self.sl_opacity.value()
        op_val = round(op_pct / 100.0, 4)
        e_val = round(self.sl_emission.value() / 10.0, 1)
        self.lbl_rough_val.setText(f"{self.sl_rough.value()}%")
        self.lbl_specular_val.setText(f"{self.sl_specular.value()}%")
        self.lbl_bump_val.setText(f"{self.sl_bump.value() / 10.0:.1f}%")
        self.lbl_opacity_val.setText(f"{op_pct}%")
        self.lbl_emission_val.setText(f"{e_val:.1f}")

        mat_item = next(
            (m for m in self._scene_materials if m.get("name") == self._current_mat),
            None,
        )
        base_op = float(
            mat_item.get("opacity", 1.0)
            if mat_item and mat_item.get("opacity") is not None
            else 1.0
        )
        base_pct = max(5, min(100, int(round(base_op * 100))))

        if self._current_mat not in self._overrides and op_pct != base_pct:
            self._overrides[self._current_mat] = {
                "type": self.cb_type.currentData() or "auto",
                "sub_type": self.cb_subtype.currentText(),
                "roughness": r_val,
                "specular": s_val,
                "bump": b_val,
                "opacity": op_val,
            }
        elif self._current_mat in self._overrides:
            self._overrides[self._current_mat]["roughness"] = r_val
            self._overrides[self._current_mat]["specular"] = s_val
            self._overrides[self._current_mat]["bump"] = b_val
            if self.cb_type.currentData() == "emissivo":
                self._overrides[self._current_mat]["emission_strength"] = e_val
            if op_pct < 100 or op_pct != base_pct or "opacity" in self._overrides[self._current_mat]:
                self._overrides[self._current_mat]["opacity"] = op_val

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
            "tapete": "Configura tapetes e carpetes com opção de fios 3D felpudos (Pelo Alto Shaggy / Pelo Curto) ou trama plana sem pelos (Sisal, Kilim, Bouclê). O slider de Relevo ajusta a altura/intensidade da felpa.",
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
            self._refresh_row_label(row)
            self._on_material_selected(row)

    def _save_as_global_default(self):
        import json

        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QMessageBox
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
        self._cleanup_eyedropper()
        if self._group is not None:
            if getattr(self._group, "ext", None) is None or not isinstance(self._group.ext, dict):
                self._group.ext = {}
            mat_names = {m.get("name") for m in self._scene_materials if m.get("name")}
            grp_overrides = (
                {k: dict(v) for k, v in self._overrides.items()
                 if isinstance(v, dict) and (not mat_names or k in mat_names)}
            )
            if grp_overrides:
                self._group.ext["trazomob_render_materials"] = grp_overrides
            else:
                self._group.ext.pop("trazomob_render_materials", None)
        elif self.scene is not None:
            for mat_item in self._scene_materials:
                mat_name = mat_item.get("name")
                if not mat_name:
                    continue
                override = self._overrides.get(mat_name)
                for owner_grp in (mat_item.get("owner_groups") or ()):
                    if owner_grp is None:
                        continue
                    ext = getattr(owner_grp, "ext", None)
                    if isinstance(override, dict) and override:
                        if not isinstance(ext, dict):
                            ext = owner_grp.ext = {}
                        mats = ext.get("trazomob_render_materials")
                        if not isinstance(mats, dict):
                            mats = ext["trazomob_render_materials"] = {}
                        mats[mat_name] = dict(override)
                    elif isinstance(ext, dict) and isinstance(ext.get("trazomob_render_materials"), dict):
                        ext["trazomob_render_materials"].pop(mat_name, None)
                        if not ext["trazomob_render_materials"]:
                            ext.pop("trazomob_render_materials", None)

        # Salva também no plugin_data da cena atual para persistir dentro do .igz
        if self.scene is not None:
            if not hasattr(self.scene, "plugin_data") or not isinstance(self.scene.plugin_data, dict):
                self.scene.plugin_data = {}
            if "trazomob" not in self.scene.plugin_data or not isinstance(self.scene.plugin_data["trazomob"], dict):
                self.scene.plugin_data["trazomob"] = {}
            if self._group is not None:
                merged = dict(self.scene.plugin_data["trazomob"].get("material_overrides") or {})
                merged.update(self._overrides)
                self.scene.plugin_data["trazomob"]["material_overrides"] = merged
            else:
                self.scene.plugin_data["trazomob"]["material_overrides"] = dict(self._overrides)
            self._apply_opacity_overrides_to_scene()
            if hasattr(self.scene, "version"):
                self.scene.version += 1

        self.materials_updated.emit(self._overrides)
        self.accept()

    def _apply_opacity_overrides_to_scene(self) -> None:
        """Sincroniza os ajustes de opacidade (0.05..1.0) para o modelo 3D."""
        if self.scene is None:
            return
        opacity_updates: dict[str, float | None] = {}
        for mat_item in self._scene_materials:
            mat_name = mat_item.get("name")
            if not mat_name:
                continue
            cfg = self._overrides.get(mat_name)
            if not isinstance(cfg, dict) or cfg.get("opacity") is None:
                continue
            op_val = max(0.05, min(1.0, float(cfg["opacity"])))
            opacity_updates[mat_name] = round(op_val, 4) if op_val < 0.999 else None
        if not opacity_updates:
            return

        from core.group import iter_painted_placements
        from core.materials import has_own_material
        from core.mesh import face_attrs
        from trazomob.integrations.platform import dirty_group_chunks

        changed = False
        registry = getattr(self.scene, "materials", None)
        if isinstance(registry, dict):
            for mname, op_attr in opacity_updates.items():
                mat_obj = registry.get(mname)
                if mat_obj is not None and getattr(mat_obj, "opacity", None) != op_attr:
                    mat_obj.opacity = op_attr
                    changed = True

        def _update_mesh_faces(mesh, paint) -> bool:
            if mesh is None or getattr(mesh, "_is_link_placeholder", False):
                return False
            if not any(_resolve_mat_name(fa) in opacity_updates for fa in face_attrs(mesh)):
                return False
            mesh_changed = False
            for f in getattr(mesh, "faces", ()):
                f_attrs = getattr(f, "attrs", None)
                if not isinstance(f_attrs, dict):
                    f_attrs = {}
                    f.attrs = f_attrs
                if paint and not has_own_material(f_attrs) and not f_attrs.get("mat"):
                    continue
                mname = _resolve_mat_name(f_attrs)
                if mname not in opacity_updates:
                    continue
                op_attr = opacity_updates[mname]
                if f_attrs.get("opacity") != op_attr:
                    if op_attr is None:
                        f_attrs.pop("opacity", None)
                    else:
                        f_attrs["opacity"] = op_attr
                    mesh_changed = True
            if mesh_changed and hasattr(mesh, "_mut_serial"):
                mesh._mut_serial += 1
            return mesh_changed

        target_groups = (
            [self._group]
            if self._group is not None
            else list(getattr(self.scene, "groups", ()) or ())
        )
        seen_meshes: set[tuple[int, bool]] = set()
        for grp in target_groups:
            for placement, _m, paint in iter_painted_placements(grp):
                pm_mat = getattr(placement, "material", None)
                if isinstance(pm_mat, dict):
                    pm_name = _resolve_mat_name(pm_mat)
                    if pm_name in opacity_updates:
                        op_attr = opacity_updates[pm_name]
                        if pm_mat.get("opacity") != op_attr:
                            new_pm = dict(pm_mat)
                            if op_attr is None:
                                new_pm.pop("opacity", None)
                            else:
                                new_pm["opacity"] = op_attr
                            placement.material = new_pm
                            changed = True
                mesh = getattr(placement, "mesh", None)
                mkey = (id(mesh), bool(paint))
                if mesh is not None and mkey not in seen_meshes:
                    seen_meshes.add(mkey)
                    if _update_mesh_faces(mesh, paint):
                        changed = True

        if self._group is None:
            loose_mesh = getattr(self.scene, "loose_mesh", None)
            if loose_mesh is None:
                loose_mesh = getattr(self.scene, "mesh", None)
            if _update_mesh_faces(loose_mesh, None):
                changed = True

        if changed:
            dirty_group_chunks(self.scene)
            if self.viewport is not None:
                if hasattr(self.viewport, "notify_scene_changed"):
                    self.viewport.notify_scene_changed()
                elif hasattr(self.viewport, "update"):
                    self.viewport.update()

    def get_overrides(self) -> dict:
        return dict(self._overrides)


def open_material_editor(
    viewport=None,
    parent=None,
    select_material: str | None = None,
    group=None,
) -> MaterialEditorDialog | None:
    """Abre ou traz à frente (não-modal) o diálogo de Materiais PBR do TrazoMob."""
    scene = getattr(viewport, "scene", None) if viewport else None
    if scene is None:
        return None

    win = viewport.window() if viewport and hasattr(viewport, "window") else parent
    dlg = getattr(win, "_trazomob_material_dialog", None)

    current_overrides: dict = {}
    if hasattr(scene, "plugin_data") and isinstance(scene.plugin_data, dict):
        tm_data = scene.plugin_data.get("trazomob", {})
        if isinstance(tm_data, dict) and isinstance(tm_data.get("material_overrides"), dict):
            current_overrides.update(tm_data["material_overrides"])
    if group is not None:
        grp_ext = getattr(group, "ext", None)
        if isinstance(grp_ext, dict) and isinstance(grp_ext.get("trazomob_render_materials"), dict):
            for k, v in grp_ext["trazomob_render_materials"].items():
                if isinstance(v, dict):
                    current_overrides[k] = v

    same_target = (
        dlg is not None
        and dlg.isVisible()
        and getattr(dlg, "scene", None) is scene
        and getattr(dlg, "_group", None) is group
    )
    if not same_target:
        if dlg is not None and dlg.isVisible():
            dlg.close()
        dlg = MaterialEditorDialog(
            scene,
            current_overrides=current_overrides,
            viewport=viewport,
            parent=win,
            group=group,
        )
        dlg.setModal(False)
        if win is not None:
            win._trazomob_material_dialog = dlg
            render_dlg = getattr(win, "_trazomob_render_dlg", None)
            if render_dlg is not None and hasattr(render_dlg, "_on_materials_updated"):
                if not getattr(dlg, "_render_dlg_sync_connected", False):
                    dlg.materials_updated.connect(render_dlg._on_materials_updated)
                    dlg._render_dlg_sync_connected = True
        dlg.show()
    else:
        if win is not None:
            render_dlg = getattr(win, "_trazomob_render_dlg", None)
            if render_dlg is not None and hasattr(render_dlg, "_on_materials_updated"):
                if not getattr(dlg, "_render_dlg_sync_connected", False):
                    dlg.materials_updated.connect(render_dlg._on_materials_updated)
                    dlg._render_dlg_sync_connected = True
        dlg.raise_()
        dlg.activateWindow()

    if select_material:
        dlg.select_material_by_name(select_material)

    return dlg

