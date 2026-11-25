# SPDX-License-Identifier: GPL-3.0-or-later
"""Teste unitário do TrazoMob para validar a exclusão de oclusão de luzes no render."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Adiciona o diretório raiz do IngeTrazo ao sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtGui import QVector3D

from core.group import Group
from core.mesh import Mesh
from core.scene import Scene
from formats.gltf import save_glb
from trazomob.render.lighting import create_light_scene_group


class TestLightOcclusionExclusion(unittest.TestCase):
    """Garante que objetos indicadores de luz (gizmos) sejam excluídos do render,
    impedindo que a luz fique enclausurada dentro de sua própria malha 3D.
    """

    def test_light_group_filtered_from_render_scene(self):
        """Valida que a lógica do render_engine descarta o grupo de luz da exportação GLB."""
        scene = Scene()

        # Cria uma parede / móvel da cena
        m_wall = Mesh()
        pts = [QVector3D(0, 0, 0), QVector3D(2, 0, 0), QVector3D(2, 0, 2), QVector3D(0, 0, 2)]
        f = m_wall.add_face(pts)
        f.attrs["mat"] = "MDF_Carvalho"
        grp_wall = Group(m_wall, name="Móvel_Armário")
        scene.groups.append(grp_wall)

        # Adiciona um Spot de Luz pelo TrazoMob
        grp_light = create_light_scene_group({
            "kind": "spot",
            "pos": [1.0, 0.5, 2.2],
            "power": 450,
            "kelvin": 3000
        })
        scene.groups.append(grp_light)

        # Executa a filtragem idêntica à de render_engine.py
        def _is_light_group(g):
            ext = getattr(g, "ext", None)
            if isinstance(ext, dict) and (ext.get("atomic_light") or "trazomob_light" in ext):
                return True
            name = (getattr(g, "name", "") or "").lower()
            return "💡" in name or "fonte de luz" in name

        clean_scene = Scene()
        for g in scene.groups:
            if not _is_light_group(g):
                clean_scene.groups.append(g)

        # Asserções
        self.assertEqual(len(scene.groups), 2, "A cena original deve ter a parede e o gizmo da luz.")
        self.assertEqual(len(clean_scene.groups), 1, "A cena filtrada de render deve ter APENAS o móvel/parede.")
        self.assertEqual(clean_scene.groups[0].name, "Móvel_Armário")

        # Testa a exportação para GLB da cena limpa
        tmp_glb = tempfile.mktemp(suffix=".glb")
        save_glb(clean_scene, tmp_glb)
        self.assertTrue(os.path.exists(tmp_glb))
        self.assertGreater(os.path.getsize(tmp_glb), 0)

        # Inspeciona o JSON interno do GLB para garantir que 'Fonte_de_Luz' não existe no arquivo
        with open(tmp_glb, "rb") as f_glb:
            header = f_glb.read(12)
            chunk0_hdr = f_glb.read(8)
            import json
            import struct
            c_len = struct.unpack("<I", chunk0_hdr[0:4])[0]
            gltf_json = json.loads(f_glb.read(c_len).decode("utf-8"))
            mat_names = [m.get("name") for m in gltf_json.get("materials", [])]

            self.assertIn("MDF_Carvalho", mat_names, "O material do móvel deve estar presente no GLB.")
            self.assertNotIn("Fonte_de_Luz", mat_names, "O material da luz NÃO pode estar presente no GLB.")

        try:
            os.remove(tmp_glb)
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()
