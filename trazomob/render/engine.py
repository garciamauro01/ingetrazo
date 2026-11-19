# SPDX-License-Identifier: GPL-3.0-or-later
"""Gerenciador e orquestrador de renderização foto-realista do TrazoMob.

Executa o Blender em segundo plano de forma 100% autônoma, usando o script
exclusivo do TrazoMob (`blender_scripts/photoreal_render.py`).
"""
from __future__ import annotations

import json
import os
import sys
import glob
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

from PySide6.QtCore import QObject, QProcess, Signal, QSettings
from PySide6.QtGui import QVector3D


class TrazoMobRenderEngine(QObject):
    """Orquestra a criação do job e o processo em background do Blender."""

    progress_updated = Signal(int, str)  # percent (0..100 or -1 for indeterminate), message
    render_finished = Signal(str)  # Caminho da imagem gerada
    render_failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process: Optional[QProcess] = None
        self._output_path: Optional[str] = None

    @staticmethod
    def get_blender_executable() -> Optional[str]:
        """Localiza o executável do Blender no sistema operacional."""
        settings = QSettings()
        custom = settings.value("render/blender_path", "")
        if custom and os.path.isfile(custom):
            return str(custom)

        candidates = []
        if sys.platform == "win32":
            roots = [os.environ.get(k) for k in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")]
            for root in filter(None, roots):
                candidates += sorted(glob.glob(os.path.join(root, "Blender Foundation", "Blender*", "blender.exe")), reverse=True)
                candidates.append(os.path.join(root, "Steam", "steamapps", "common", "Blender", "blender.exe"))
        elif sys.platform == "darwin":
            candidates += sorted(glob.glob("/Applications/Blender*.app/Contents/MacOS/Blender"), reverse=True)
        else:
            candidates += ["/usr/bin/blender", "/usr/local/bin/blender", "/snap/bin/blender"]
            candidates += sorted(glob.glob("/opt/blender*/blender"), reverse=True)

        for p in candidates:
            if os.path.isfile(p):
                return p
        return None

    def start_render(
        self,
        scene,
        camera,
        preset: str = "dia",
        engine: str = "cycles",
        quality: str = "high",
        width: int = 1920,
        height: int = 1080,
        correct_verticals: bool = True,
        material_overrides: Optional[dict] = None,
        clay_mode: bool = False,
        selected_only: bool = False,
        sun_softness: float = 2.5
    ) -> bool:
        """Inicia a renderização fotorrealista via Blender em segundo plano."""
        blender_exe = self.get_blender_executable()
        if not blender_exe:
            self.render_failed.emit(
                "O Blender não foi encontrado automaticamente no seu computador.\n"
                "Instale o Blender (gratuito) em www.blender.org ou aponte o executável nas configurações."
            )
            return False

        # Cria pasta temporária exclusiva para este render
        stamp = time.strftime("%Y%m%d-%H%M%S")
        from PySide6.QtCore import QStandardPaths
        base_cache = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericCacheLocation)
        work_dir = Path(base_cache) / "IngeTrazo" / "trazomob_renders" / stamp
        work_dir.mkdir(parents=True, exist_ok=True)

        # 1. Exporta o modelo para GLB (suporta cena inteira ou apenas seleção)
        # Regra de Oclusão: remove qualquer Group de luz técnica (atomic_light / trazomob_light)
        # da cena exportada para que o arquivo 3D contenha APENAS os móveis e paredes.
        glb_path = work_dir / "scene.glb"
        from formats.gltf import save_glb
        from core.scene import Scene
        from core.group import Group

        def _is_light_group(g):
            ext = getattr(g, "ext", None)
            if isinstance(ext, dict) and (ext.get("atomic_light") or "trazomob_light" in ext):
                return True
            name = (getattr(g, "name", "") or "").lower()
            return "💡" in name or "fonte de luz" in name

        clean_scene = Scene()
        source_items = scene.selection if (selected_only and hasattr(scene, "selection") and len(scene.selection) > 0) else getattr(scene, "groups", [])
        for item in source_items:
            # Respeita o estado de ocultação: se o usuário escondeu a parede ou o teto, não envia para o render
            if hasattr(scene, "entity_visible") and not scene.entity_visible(item):
                continue

            if isinstance(item, Group):
                if not _is_light_group(item):
                    from core.group import effective_material
                    from core.materials import effective_attrs
                    paint = effective_material(item)
                    has_hidden_faces = hasattr(item, "mesh") and hasattr(item.mesh, "faces") and any(f.attrs.get("hidden") for f in item.mesh.faces)

                    # Sempre cria uma cópia com as faces visíveis e cores/materiais do grupo assados nas faces
                    if hasattr(item, "mesh") and hasattr(item.mesh, "faces") and item.mesh.faces:
                        from core.mesh import Mesh
                        m_clean = Mesh()
                        for f in item.mesh.faces:
                            if not f.attrs.get("hidden"):
                                nf = m_clean.add_face(list(f.vertices))
                                # Se a face não tem cor própria mas o grupo tem material/cor (ex: pintou a parede com balde de tinta),
                                # aplica a cor do grupo à face para o Blender renderizar fielmente
                                attrs_baked = effective_attrs(f.attrs, paint) if paint else dict(f.attrs)
                                if attrs_baked:
                                    # Se a face não tem tag de material 'mat' explícita, marca com o nome do grupo
                                    # para que o motor de render do Blender identifique como Parede / Alvenaria / Tinta
                                    if "mat" not in attrs_baked and ("parede" in (item.name or "").lower() or "wall" in (item.name or "").lower()):
                                        from ..wall.paint_catalog import DEFAULT_WALL_PAINT
                                        attrs_baked["mat"] = DEFAULT_WALL_PAINT
                                    nf.attrs.update(attrs_baked)
                        # Aplica suavização automática de arestas (soft edges) entre faces coplanares ou curvas
                        from formats.fuse import soften_smooth_edges
                        soften_smooth_edges(m_clean, cos_threshold=0.85)
                        g_clean = Group(m_clean, name=item.name)
                        g_clean.layer = getattr(item, "layer", None)
                        g_clean.xform = getattr(item, "xform", None)
                        g_clean.material = getattr(item, "material", None)
                        if getattr(item, "children", None):
                            g_clean.children = list(item.children)
                        clean_scene.groups.append(g_clean)
                    else:
                        clean_scene.groups.append(item)
            elif hasattr(item, "mesh"):
                clean_scene.groups.append(item)

        # Copia materiais, loose_mesh e configurações da cena
        if hasattr(scene, "loose_mesh") and not selected_only:
            clean_scene.mesh = scene.loose_mesh
        if hasattr(scene, "materials"):
            clean_scene.materials = dict(scene.materials)

        save_glb(clean_scene, glb_path)

        # 2. Amostras conforme a qualidade
        samples_map = {
            "draft": 32 if engine == "cycles" else 16,
            "medium": 128 if engine == "cycles" else 32,
            "high": 256 if engine == "cycles" else 64,
            "ultra": 512 if engine == "cycles" else 128,
        }
        samples = samples_map.get(quality, 128)

        # 3. Calcula vetor de luz do sol do IngeTrazo se dia/tarde
        from core.render_blender import sun_toward, camera_dict
        sun_vec = sun_toward(scene) if preset in ("dia", "tarde") else None

        # Coleta as luzes / spots / lâmpadas diretamente da cena (com fallback para janela ativa)
        from ..render.lighting import _get_scene_lights, _lights_from_any_window, _clean_trazomob_lights
        raw_lights = _get_scene_lights(scene)
        if not raw_lights:
            try:
                raw_lights = _lights_from_any_window()
            except Exception:
                raw_lights = []

        user_lights = [lt for lt in _clean_trazomob_lights(raw_lights) if lt.get("on", True)]

        # 4. Monta o job.json
        output_img = work_dir / "render_trazomob.png"
        self._output_path = str(output_img)

        # Coleta os overrides de materiais do projeto se configurados.
        # Paredes novas já saem com tinta branca fosco acetinada no render;
        # um override do usuario continua tendo prioridade.
        mat_overrides = dict(material_overrides or {})
        from ..wall.paint_catalog import DEFAULT_WALL_PAINT
        mat_overrides.setdefault(DEFAULT_WALL_PAINT, {
            "type": "parede",
            "sub_type": "Tinta Acrílica Fosca / Acetinada",
            "roughness": 0.45,
            "specular": 0.18,
            "bump": 0.015,
        })

        job = {
            "glb": str(glb_path),
            "output": str(output_img),
            "engine": engine,
            "preset": preset,
            "samples": samples,
            "width": width,
            "height": height,
            "correct_verticals": correct_verticals,
            "camera": camera_dict(camera),
            "sun": sun_vec,
            "sun_softness": sun_softness,
            "lights": user_lights,
            "materials": mat_overrides,
            "clay_mode": clay_mode,
            "exposure": 0.0 if preset in ("dia", "noturno", "estudio") else -0.1,
            "blend_file": str(work_dir / "cena_marcenaria_trazomob.blend"),
        }

        job_path = work_dir / "job.json"
        job_path.write_text(json.dumps(job, indent=2), encoding="utf-8")

        # 5. Localiza o script autônomo do TrazoMob
        curr_dir = Path(__file__).resolve().parents[1]
        script_path = curr_dir / "blender_scripts" / "photoreal_render.py"

        # 6. Prepara e executa o QProcess
        self._process = QProcess(self)
        from core.render_blender import clean_env
        from PySide6.QtCore import QProcessEnvironment
        q_env = QProcessEnvironment()
        for k, v in clean_env().items():
            q_env.insert(k, v)
        self._process.setProcessEnvironment(q_env)

        args = ["-b", "--factory-startup", "--python", str(script_path), "--", str(job_path)]

        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.readyReadStandardError.connect(self._on_stderr)
        self._process.finished.connect(self._on_finished)

        self.progress_updated.emit(5, "Iniciando motor do Blender e shaders PBR...")
        self._process.start(blender_exe, args)
        return True

    def cancel(self):
        """Cancela a renderização se estiver em andamento."""
        if self._process and self._process.state() != QProcess.NotRunning:
            self._process.kill()
            self.progress_updated.emit(0, "Renderização cancelada.")

    def _on_stdout(self):
        if not self._process:
            return
        data = self._process.readAllStandardOutput().data().decode("utf-8", errors="ignore")
        for line in data.splitlines():
            line_str = line.strip()
            if not line_str:
                continue

            if "TRAZOMOB_RENDER" in line_str:
                parts = line_str.split("TRAZOMOB_RENDER", 1)[-1].strip()
                if "rendering" in parts:
                    self.progress_updated.emit(20, "🎨 Renderizando cena foto-realista no Blender...")
                elif "imported" in parts:
                    self.progress_updated.emit(10, "📦 Geometria e texturas de marcenaria carregadas...")
                elif "gpu_enabled" in parts:
                    self.progress_updated.emit(15, "🚀 Aceleração por Placa de Vídeo (GPU) ativada!")
            elif "Sample " in line_str:
                # Exemplo Cycles: "Sample 25/128" ou "Sample 15/128 | Time: 00:03.21"
                import re
                match = re.search(r"Sample\s+(\d+)\s*/\s*(\d+)", line_str)
                if match:
                    cur = int(match.group(1))
                    tot = int(match.group(2))
                    pct = int(20 + (cur / max(1, tot)) * 75)
                    self.progress_updated.emit(pct, f"Amostragem Cycles ({cur}/{tot} samples)")
                else:
                    self.progress_updated.emit(-1, f"Calculando iluminação: {line_str}")
            elif "Denoising" in line_str or "denoise" in line_str.lower():
                self.progress_updated.emit(96, "✨ Aplicando Inteligência Artificial Denoiser (redução de ruído)...")
            elif "Writing: " in line_str or "Saved: " in line_str:
                self.progress_updated.emit(99, "💾 Gravando arquivo PNG final com alta fidelidade...")

    def _on_stderr(self):
        if not self._process:
            return
        # Apenas consome stderr sem travar o buffer
        self._process.readAllStandardError()

    def _on_finished(self, exit_code, exit_status):
        if exit_code == 0 and self._output_path and os.path.isfile(self._output_path):
            self.progress_updated.emit(100, "✅ Imagem foto-realista concluída!")
            self.render_finished.emit(self._output_path)
        else:
            self.render_failed.emit("O processo de renderização foi interrompido ou falhou.")
