# SPDX-License-Identifier: GPL-3.0-or-later
"""Gerenciador e orquestrador de renderização foto-realista do TrazoMob.

Executa o Blender em segundo plano de forma 100% autônoma, usando o script
exclusivo do TrazoMob (`blender_scripts/photoreal_render.py`).
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QProcess, QSettings, QThread, Signal, Slot


def _set_process_low_priority(pid: int) -> bool:
    """Ajusta a prioridade do processo do Blender para BELOW_NORMAL no Windows/Linux/macOS."""
    try:
        if sys.platform == "win32":
            import ctypes
            PROCESS_SET_INFORMATION = 0x0200
            BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_SET_INFORMATION, False, pid)
            if handle:
                ctypes.windll.kernel32.SetPriorityClass(handle, BELOW_NORMAL_PRIORITY_CLASS)
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
        elif hasattr(os, "nice"):
            # Em Unix/macOS, o processo filho herdaria nice, ou podemos tentar os.setpriority se disponível
            try:
                os.setpriority(os.PRIO_PROCESS, pid, 10)
                return True
            except (AttributeError, OSError, PermissionError):
                pass
    except Exception:
        pass
    return False


class _ExportWorker(QObject):
    """Trabalhador que roda em uma QThread separada para montar e exportar o GLB da cena sem travar a UI."""

    progress = Signal(int, str)
    finished = Signal(object, object)  # (job_dict, error_msg)

    def __init__(
        self,
        scene,
        camera,
        work_dir: Path,
        preset: str,
        engine: str,
        quality: str,
        width: int,
        height: int,
        correct_verticals: bool,
        material_overrides: Optional[dict],
        clay_mode: bool,
        selected_only: bool,
        sun_softness: float,
    ):
        super().__init__()
        self.scene = scene
        self.camera = camera
        self.work_dir = work_dir
        self.preset = preset
        self.engine = engine
        self.quality = quality
        self.width = width
        self.height = height
        self.correct_verticals = correct_verticals
        self.material_overrides = material_overrides
        self.clay_mode = clay_mode
        self.selected_only = selected_only
        self.sun_softness = sun_softness

    def run(self):
        try:
            self.progress.emit(-1, "⏳ Preparando geometria e texturas da cena em segundo plano...")
            scene = self.scene
            camera = self.camera
            work_dir = self.work_dir

            glb_path = work_dir / "scene.glb"
            from core.group import Group, effective_material
            from core.materials import effective_attrs
            from core.mesh import Mesh, face_attrs, face_count
            from core.scene import Scene
            from formats.gltf import save_glb

            from ..wall.paint_catalog import DEFAULT_WALL_PAINT

            def _is_light_group(g):
                ext = getattr(g, "ext", None)
                if isinstance(ext, dict) and (ext.get("atomic_light") or "trazomob_light" in ext):
                    return True
                name = (getattr(g, "name", "") or "").lower()
                return "💡" in name or "fonte de luz" in name

            clean_scene = Scene()
            source_items = (
                scene.selection
                if (self.selected_only and hasattr(scene, "selection") and len(scene.selection) > 0)
                else getattr(scene, "groups", [])
            )
            for item in source_items:
                if hasattr(scene, "entity_visible") and not scene.entity_visible(item):
                    continue

                if isinstance(item, Group):
                    if not _is_light_group(item):
                        mesh = getattr(item, "mesh", None)
                        paint = effective_material(item)
                        own_mat = getattr(item, "material", None)
                        if mesh is not None and face_count(mesh) > 0:
                            attrs_list = list(face_attrs(mesh))
                            has_hidden_faces = any(
                                isinstance(a, dict) and a.get("hidden") for a in attrs_list
                            )
                            item_name_l = (item.name or "").lower()
                            is_wall_named = "parede" in item_name_l or "wall" in item_name_l
                            needs_wall_tag = is_wall_named and any(
                                not isinstance(a, dict) or "mat" not in a for a in attrs_list
                            )
                            if not has_hidden_faces and not needs_wall_tag and paint == own_mat:
                                clean_scene.groups.append(item)
                                continue

                            m_clean = Mesh()
                            for f in mesh.faces:
                                if not f.attrs.get("hidden"):
                                    nf = m_clean.add_face(list(f.vertices))
                                    attrs_baked = (
                                        effective_attrs(f.attrs, paint) if paint else dict(f.attrs)
                                    )
                                    if attrs_baked:
                                        if "mat" not in attrs_baked and is_wall_named:
                                            attrs_baked["mat"] = DEFAULT_WALL_PAINT
                                        nf.attrs.update(attrs_baked)
                            from formats.fuse import soften_smooth_edges
                            soften_smooth_edges(m_clean, cos_threshold=0.85)
                            g_clean = Group(m_clean, name=item.name)
                            g_clean.layer = getattr(item, "layer", None)
                            g_clean.xform = getattr(item, "xform", None)
                            g_clean.material = own_mat
                            if getattr(item, "children", None):
                                g_clean.children = list(item.children)
                            clean_scene.groups.append(g_clean)
                        else:
                            clean_scene.groups.append(item)
                elif hasattr(item, "mesh"):
                    clean_scene.groups.append(item)

            if hasattr(scene, "loose_mesh") and not self.selected_only:
                clean_scene.mesh = scene.loose_mesh
            if hasattr(scene, "materials"):
                clean_scene.materials = dict(scene.materials)

            self.progress.emit(-1, "⏳ Exportando modelo 3D e texturas para o Blender...")
            save_glb(clean_scene, glb_path)

            samples_map = {
                "draft": 32 if self.engine == "cycles" else 16,
                "medium": 128 if self.engine == "cycles" else 32,
                "high": 256 if self.engine == "cycles" else 64,
                "ultra": 512 if self.engine == "cycles" else 128,
            }
            samples = samples_map.get(self.quality, 128)

            from core.render_blender import camera_dict, sun_toward
            sun_vec = sun_toward(scene) if self.preset in ("dia", "tarde") else None

            from ..render.lighting import (
                _clean_trazomob_lights,
                _get_scene_lights,
                _lights_from_any_window,
            )
            raw_lights = _get_scene_lights(scene)
            if not raw_lights:
                try:
                    raw_lights = _lights_from_any_window()
                except Exception:
                    raw_lights = []

            user_lights = [lt for lt in _clean_trazomob_lights(raw_lights) if lt.get("on", True)]

            output_img = work_dir / "render_trazomob.png"
            mat_overrides = dict(self.material_overrides or {})
            pdata = getattr(scene, "plugin_data", None)
            if isinstance(pdata, dict):
                tm_data = pdata.get("trazomob")
                if isinstance(tm_data, dict) and isinstance(tm_data.get("material_overrides"), dict):
                    for mat_key, mat_cfg in tm_data["material_overrides"].items():
                        if isinstance(mat_cfg, dict):
                            mat_overrides.setdefault(mat_key, dict(mat_cfg))
            from ..domain.render_materials import collect_group_render_overrides
            for mat_key, mat_cfg in collect_group_render_overrides(source_items).items():
                mat_overrides.setdefault(mat_key, mat_cfg)
            from ..wall.paint_catalog import DEFAULT_WALL_PAINT
            mat_overrides.setdefault(
                DEFAULT_WALL_PAINT,
                {
                    "type": "parede",
                    "sub_type": "Tinta Acrílica Fosca / Acetinada",
                    "roughness": 0.45,
                    "specular": 0.18,
                    "bump": 0.015,
                },
            )

            job = {
                "glb": str(glb_path),
                "output": str(output_img),
                "engine": self.engine,
                "preset": self.preset,
                "samples": samples,
                "width": self.width,
                "height": self.height,
                "correct_verticals": self.correct_verticals,
                "camera": camera_dict(camera),
                "sun": sun_vec,
                "sun_softness": self.sun_softness,
                "lights": user_lights,
                "materials": mat_overrides,
                "clay_mode": self.clay_mode,
                "exposure": 0.0 if self.preset in ("dia", "noturno", "estudio") else -0.1,
                "blend_file": str(work_dir / "cena_marcenaria_trazomob.blend"),
            }

            job_path = work_dir / "job.json"
            job_path.write_text(json.dumps(job, indent=2), encoding="utf-8")

            self.finished.emit({"job_path": str(job_path), "output_img": str(output_img)}, None)
        except Exception as exc:
            self.finished.emit(None, str(exc))


class TrazoMobRenderEngine(QObject):
    """Orquestra a criação do job e o processo em background do Blender."""

    progress_updated = Signal(int, str)  # percent (0..100 or -1 for indeterminate), message
    render_finished = Signal(str)  # Caminho da imagem gerada
    render_failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process: Optional[QProcess] = None
        self._output_path: Optional[str] = None
        self._export_thread: Optional[QThread] = None
        self._export_worker: Optional[_ExportWorker] = None

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

        # Cancela qualquer export ou render anterior ainda em execução
        self.cancel()

        self.progress_updated.emit(-1, "⏳ Preparando geometria e texturas da cena...")

        # Cria pasta temporária exclusiva para este render
        stamp = time.strftime("%Y%m%d-%H%M%S")
        from PySide6.QtCore import QStandardPaths
        base_cache = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericCacheLocation)
        work_dir = Path(base_cache) / "IngeTrazo" / "trazomob_renders" / stamp
        work_dir.mkdir(parents=True, exist_ok=True)

        # Inicia a preparação e exportação do GLB numa QThread dedicada para não travar a UI
        self._export_thread = QThread(self)
        self._export_worker = _ExportWorker(
            scene=scene,
            camera=camera,
            work_dir=work_dir,
            preset=preset,
            engine=engine,
            quality=quality,
            width=width,
            height=height,
            correct_verticals=correct_verticals,
            material_overrides=material_overrides,
            clay_mode=clay_mode,
            selected_only=selected_only,
            sun_softness=sun_softness,
        )
        self._current_blender_exe = blender_exe
        self._export_worker.moveToThread(self._export_thread)
        self._export_worker.progress.connect(self.progress_updated)
        self._export_worker.finished.connect(self._on_worker_finished)
        self._export_thread.started.connect(self._export_worker.run)

        # Se for ambiente de teste ou thread sem event loop concorrente, executa síncrono para previsibilidade
        if os.environ.get("PYTEST_CURRENT_TEST"):
            self._export_worker.run()
        else:
            self._export_thread.start()
        return True

    @Slot(object, object)
    def _on_worker_finished(self, payload: Optional[dict], err_msg: Optional[str]):
        """Slot conectado diretamente para garantir execução na thread principal do Engine."""
        blender_exe = getattr(self, "_current_blender_exe", None) or self.get_blender_executable()
        self._on_export_finished(payload, err_msg, blender_exe)

    def _on_export_finished(self, payload: Optional[dict], err_msg: Optional[str], blender_exe: str):
        """Chamado quando o worker de exportação conclui o processamento."""
        from PySide6.QtCore import QThread
        if self._export_thread is not None:
            # Evita QThread::wait na própria thread se porventura o sinal for tratado na thread do worker
            if QThread.currentThread() != self._export_thread:
                self._export_thread.quit()
                self._export_thread.wait(500)
            else:
                self._export_thread.quit()
            self._export_thread = None
            self._export_worker = None

        if err_msg or not payload:
            self.render_failed.emit(err_msg or "Falha ao preparar os dados da cena para renderização.")
            return

        job_path = payload["job_path"]
        self._output_path = payload["output_img"]

        # Localiza o script autônomo do TrazoMob
        curr_dir = Path(__file__).resolve().parents[1]
        script_path = curr_dir / "blender_scripts" / "photoreal_render.py"

        # Garante que o QProcess não receba pai de outra thread se executado fora da thread principal
        parent_obj = self if self.thread() == QThread.currentThread() else None
        self._process = QProcess(parent_obj)
        from PySide6.QtCore import QProcessEnvironment

        from core.render_blender import clean_env
        q_env = QProcessEnvironment()
        for k, v in clean_env().items():
            q_env.insert(k, v)
        self._process.setProcessEnvironment(q_env)

        # Limitação preventiva de threads: reserva ao menos 1 thread para o sistema/interface
        cpu_total = os.cpu_count() or 4
        render_threads = max(1, cpu_total - 1)

        args = [
            "-b",
            "--factory-startup",
            "-t", str(render_threads),
            "--python", str(script_path),
            "--", str(job_path)
        ]

        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.readyReadStandardError.connect(self._on_stderr)
        self._process.finished.connect(self._on_finished)
        self._process.started.connect(self._on_process_started)

        self.progress_updated.emit(5, "Iniciando motor do Blender e shaders PBR...")
        self._process.start(blender_exe, args)

    def _on_process_started(self):
        """Reduz a prioridade do processo do Blender para manter a interface fluida."""
        if self._process:
            pid = self._process.processId()
            if pid:
                _set_process_low_priority(pid)

    def cancel(self):
        """Cancela a preparação e a renderização se estiverem em andamento."""
        if self._export_thread is not None and self._export_thread.isRunning():
            self._export_thread.quit()
            self._export_thread.wait(1000)
            self._export_thread = None
            self._export_worker = None

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
                elif "STATS" in parts:
                    # Captura estatísticas reais do Blender Cycles (ex: Remaining: 00:15 | Sample 45/128)
                    stats_text = parts.split("STATS", 1)[-1].strip()
                    import re
                    match = re.search(r"Sample\s+(\d+)\s*/\s*(\d+)", stats_text)
                    time_match = re.search(r"Remaining:\s*([\d:\.]+)", stats_text)
                    rem_str = f" | Restante: {time_match.group(1)}" if time_match else ""
                    if match:
                        cur = int(match.group(1))
                        tot = int(match.group(2))
                        pct = int(20 + (cur / max(1, tot)) * 75)
                        self.progress_updated.emit(pct, f"Amostragem Cycles: {cur}/{tot} samples{rem_str}")
                    elif "Synchronizing" in stats_text or "Updating" in stats_text:
                        self.progress_updated.emit(18, f"Preparando shaders: {stats_text.split('|')[-1].strip()}")
                    elif "Finished" in stats_text:
                        self.progress_updated.emit(95, "Processando pós-produção e desfoque...")
            elif "Sample " in line_str:
                import re
                match = re.search(r"Sample\s+(\d+)\s*/\s*(\d+)", line_str)
                time_match = re.search(r"Remaining:\s*([\d:\.]+)", line_str)
                rem_str = f" | Restante: {time_match.group(1)}" if time_match else ""
                if match:
                    cur = int(match.group(1))
                    tot = int(match.group(2))
                    pct = int(20 + (cur / max(1, tot)) * 75)
                    self.progress_updated.emit(pct, f"Amostragem Cycles: {cur}/{tot} samples{rem_str}")
                else:
                    self.progress_updated.emit(-1, f"Calculando iluminação: {line_str}")
            elif "Denoising" in line_str or "denoise" in line_str.lower():
                self.progress_updated.emit(96, "✨ Aplicando Inteligência Artificial Denoiser (redução de ruído)...")
            elif "Writing: " in line_str or "Saved: " in line_str or "saved_blend" in line_str:
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
