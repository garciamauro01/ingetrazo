# SPDX-License-Identifier: GPL-3.0-or-later
"""Script autônomo executado internamente pelo Blender em segundo plano (Headless).

Pertence exclusivamente ao TrazoMob. Transforma o modelo exportado em uma cena
de arquitetura e marcenaria foto-realista no Blender (Cycles / EEVEE Next):
1. Bevel Shader em Cycles para arredondamento sutil de quinas de MDF / fitas de borda.
2. Reconhecimento avançado de materiais PBR (MDF Madeirado, Laca, Espelho, Vidro Reflecta, Perfis de Alumínio).
3. Emissão para fitas de LED de marcenaria (luz quente 2700K - 3000K).
4. Câmera arquitetônica com correção de verticais de 2 pontos de fuga (Shift Y).
5. Iluminação de Interiores calibrada (Dia, Tarde/Golden Hour, Noturno com LEDs, Estúdio Showroom).
6. Denoiser via IA (OptiX / OpenImageDenoise) e Color Management AgX com alto contraste.
"""
import json
import math
import os
import re
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector


def say(*parts):
    print("TRAZOMOB_RENDER", *parts, flush=True)


def load_job():
    argv = sys.argv
    if "--" not in argv:
        raise SystemExit("photoreal_render.py: nenhum arquivo job.json passado após '--'")
    job_path = argv[argv.index("--") + 1]
    with open(job_path, encoding="utf-8") as fh:
        return json.load(fh)


def import_model(path):
    bpy.ops.import_scene.gltf(filepath=path)
    all_objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]

    # Dupla Proteção de Oclusão:
    # 1. Remove qualquer objeto MESH cujo nome seja de luz técnica
    # 2. Se o IngeTrazo uniu múltiplos materiais no mesmo MESH (primitives),
    #    apaga as faces que usam o material 'fonte de luz' ou 'fita led emissora'
    objs = []
    to_remove = []
    for obj in all_objs:
        name_lower = obj.name.lower()
        mat_names = [slot.material.name.lower() for slot in obj.material_slots if slot.material]
        is_pure_light_obj = (
            any(k in name_lower for k in ("fonte de luz", "fita led emissora", "trazomob_light", "atomic_light"))
            or (len(mat_names) == 1 and any("fonte de luz" in m or "fita led emissora" in m for m in mat_names))
        )
        if is_pure_light_obj:
            to_remove.append(obj)
        else:
            # Se for um mesh composto, remove os polígonos associados ao material da luz
            if any("fonte de luz" in m or "fita led emissora" in m for m in mat_names):
                try:
                    bm = bmesh.new()
                    bm.from_mesh(obj.data)
                    light_slot_indices = [
                        idx for idx, slot in enumerate(obj.material_slots)
                        if slot.material and any("fonte de luz" in k or "fita led emissora" in k for k in (slot.material.name.lower(),))
                    ]
                    faces_to_del = [f for f in bm.faces if f.material_index in light_slot_indices]
                    if faces_to_del:
                        bmesh.ops.delete(bm, geom=faces_to_del, context="FACES")
                        bm.to_mesh(obj.data)
                        obj.data.update()
                        say("purged_light_faces", len(faces_to_del), "from", obj.name)
                    bm.free()
                except Exception as e:
                    say("purge_light_err", str(e))
            objs.append(obj)

    for obj in to_remove:
        try:
            bpy.data.objects.remove(obj, do_unlink=True)
        except Exception:
            pass

    # Suporte a Proxies Automáticos (troca dinâmica leve no 3D -> alta definição no render)
    # Se um objeto tiver nome ou metadado indicando proxy (ex: "Poltrona_PROXY" ou arquivo high-poly na pasta)
    for obj in list(objs):
        name = obj.name
        if "_proxy" in name.lower():
            # Tenta encontrar o arquivo _HIGHPOLY na mesma pasta do modelo
            base_dir = os.path.dirname(path)
            clean_name = name.split(".")[0].replace("_PROXY", "").replace("_proxy", "")
            highpoly_cands = [
                os.path.join(base_dir, f"{clean_name}_HIGHPOLY.glb"),
                os.path.join(base_dir, f"{clean_name}_HIGHPOLY.obj"),
                os.path.join(base_dir, f"{clean_name}.glb"),
                os.path.join(base_dir, f"{clean_name}.obj")
            ]
            for cand in highpoly_cands:
                if os.path.exists(cand):
                    try:
                        mat_w = obj.matrix_world.copy()
                        if cand.endswith(".glb"):
                            bpy.ops.import_scene.gltf(filepath=cand)
                        else:
                            bpy.ops.wm.obj_import(filepath=cand)
                        new_imported = [o for o in bpy.context.selected_objects if o.type == "MESH"]
                        for nobj in new_imported:
                            nobj.matrix_world = mat_w
                            objs.append(nobj)
                        objs.remove(obj)
                        bpy.data.objects.remove(obj, do_unlink=True)
                        say("proxy_replaced", name, "->", cand)
                        break
                    except Exception as e:
                        say("proxy_replace_err", str(e))

    # Aplica normais ponderadas (Weighted Normals) e suavização inteligente de CAD
    for obj in objs:
        # Limpa split normals rígidas customizadas vindas do exportador de arquivo
        try:
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
        except Exception:
            pass

        # Suaviza faces curvas/cilíndricas para eliminar facetas em metais e superfícies poligonais
        if hasattr(obj.data, "polygons"):
            for poly in obj.data.polygons:
                poly.use_smooth = True

        # Habilita auto-smooth se disponível na versão do Blender (preserva quinas vivas acima do ângulo limite)
        if hasattr(obj.data, "use_auto_smooth"):
            obj.data.use_auto_smooth = True
            obj.data.auto_smooth_angle = math.radians(40.0)

        # Adiciona modificador Weighted Normal para quinas de marcenaria nítidas e perfeitas
        mod = obj.modifiers.new(name="TrazoNormals", type="WEIGHTED_NORMAL")
        mod.keep_sharp = True
        mod.weight = 50

    say("imported", len(objs), "objects (removidos", len(to_remove), "gizmos de luz)")
    return objs


def _set_bsdf_prop(bsdf, names, value):
    """Define valor no primeiro socket existente compatível (Blender 3.6 - 5.x)."""
    for n in names:
        sock = bsdf.inputs.get(n)
        if sock is not None:
            try:
                sock.default_value = value
            except (TypeError, ValueError):
                continue
            for link in list(sock.links):
                sock.id_data.links.remove(link)
            return True
    return False


def _is_shaggy_carpet(preset_type, cfg):
    """Retorna ``(is_shaggy, is_short_pile)`` a partir do preset/subtipo do tapete ou carpete."""
    if cfg.get("shaggy") is False:
        return False, False
    sub = str(cfg.get("sub_type", "")).lower()
    if any(k in sub for k in ("sem pelos", "liso", "trama baixa", "sisal", "kilim", "boucl", "comercial")):
        return False, False
    if any(k in sub for k in ("pelo curto", "aveludado", "fios curtos")):
        return True, True
    if cfg.get("shaggy") is True or preset_type == "carpete_felpudo":
        return True, False
    if any(k in sub for k in ("felpudo", "shaggy", "pelo alto")):
        return True, False
    return True, False


def _apply_carpet_hair_particles(mat, hair_length=0.019, is_short_pile=False):
    """Adiciona fios 3D (Hair Particles) nos objetos da cena que utilizam ``mat``."""
    scene = getattr(bpy.context, "scene", None)
    objects = getattr(scene, "objects", ()) if scene is not None else ()
    if not objects:
        return

    render = getattr(scene, "render", None)
    if render is not None and hasattr(render, "hair_type"):
        try:
            render.hair_type = "STRIP"
        except Exception:
            pass

    for obj in objects:
        if getattr(obj, "type", None) != "MESH":
            continue
        slots = list(getattr(obj, "material_slots", ()) or ())
        slot_idx = next(
            (idx for idx, slot in enumerate(slots) if getattr(slot, "material", None) == mat),
            None,
        )
        if slot_idx is None:
            continue

        mod_name = f"TrazoTapete_Fios_{slot_idx + 1}"
        if any(getattr(m, "name", "") == mod_name for m in (getattr(obj, "modifiers", ()) or ())):
            continue

        mod = obj.modifiers.new(mod_name, "PARTICLE_SYSTEM")
        ps_holder = getattr(obj, "particle_systems", None)
        psys = getattr(mod, "particle_system", None)
        if psys is None and ps_holder:
            psys = ps_holder[-1]
        if psys is None or getattr(psys, "settings", None) is None:
            continue

        scale = getattr(obj, "scale", (1.0, 1.0, 1.0))
        scale_z = max(0.05, abs(float(scale[2])) if len(scale) >= 3 else 1.0)
        local_length = float(hair_length) / scale_z

        ps = psys.settings
        ps.type = "HAIR"
        ps.count = 22000 if is_short_pile else 18000
        ps.hair_length = local_length
        ps.hair_step = 3
        ps.root_radius = 0.0018 if is_short_pile else 0.0025
        ps.tip_radius = 0.0008 if is_short_pile else 0.0010
        ps.use_advanced_hair = True
        ps.brownian_factor = 0.012 if is_short_pile else 0.025
        ps.child_type = "SIMPLE"
        ps.rendered_child_count = 8
        ps.child_radius = 0.005 if is_short_pile else 0.008
        ps.clump_factor = 0.20
        if hasattr(ps, "material"):
            ps.material = slot_idx + 1

        if len(slots) > 1 and hasattr(obj, "vertex_groups") and hasattr(getattr(obj, "data", None), "polygons"):
            vert_indices = sorted({
                v_idx
                for poly in obj.data.polygons
                if getattr(poly, "material_index", 0) == slot_idx
                for v_idx in getattr(poly, "vertices", ())
            })
            if vert_indices:
                vg = obj.vertex_groups.new(name=f"TrazoTapete_Area_{slot_idx + 1}")
                vg.add(vert_indices, 1.0, "REPLACE")
                ps.vertex_group_density = vg.name


def _is_transparent_hit(hit_obj, poly_index):
    """Retorna True se o polígono atingido pertencer a material de vidro/translúcido."""
    if hit_obj is None:
        return False
    mat = None
    slots = getattr(hit_obj, "material_slots", None)
    if slots:
        mat_idx = 0
        mesh_data = getattr(hit_obj, "data", None)
        polys = getattr(mesh_data, "polygons", None)
        if polys is not None and isinstance(poly_index, int) and 0 <= poly_index < len(polys):
            mat_idx = getattr(polys[poly_index], "material_index", 0)
        if 0 <= mat_idx < len(slots):
            mat = getattr(slots[mat_idx], "material", None)
        if mat is None:
            mat = getattr(slots[0], "material", None)
    if mat is None:
        return False
    name_l = (getattr(mat, "name", "") or "").lower()
    if any(k in name_l for k in ("vidro", "glass", "reflecta", "voil")):
        return True
    nt = getattr(mat, "node_tree", None)
    nodes = getattr(nt, "nodes", ()) if nt else ()
    bsdf = next((n for n in nodes if getattr(n, "type", None) == "BSDF_PRINCIPLED"), None)
    if bsdf is not None:
        trans_sock = bsdf.inputs.get("Transmission Weight") or bsdf.inputs.get("Transmission")
        if trans_sock is not None and float(getattr(trans_sock, "default_value", 0.0) or 0.0) > 0.15:
            return True
        alpha_sock = bsdf.inputs.get("Alpha")
        if alpha_sock is not None and float(getattr(alpha_sock, "default_value", 1.0) or 1.0) < 0.85:
            return True
    return False


def _ray_reaches_sky(scene, depsgraph, target_pt, direction, max_dist=50.0):
    """Dispara raio de fora para dentro verificando se a direção alcança o ponto sem bater em parede opaca."""
    if depsgraph is None or not direction:
        return True
    d = Vector(direction)
    if d.length < 1e-6:
        return True
    d.normalize()
    inward = -d
    target = Vector(target_pt)
    probe = target + d * max_dist
    stop_margin = 0.05
    step = 0.02

    for _ in range(8):
        rem = (target - probe).dot(inward) - stop_margin
        if rem <= step:
            return True
        try:
            hit, loc, _norm, poly_idx, hit_obj, _mat = scene.ray_cast(
                depsgraph, probe, inward, distance=rem
            )
        except Exception:
            return True
        if not hit:
            return True
        if not _is_transparent_hit(hit_obj, poly_idx):
            return False
        probe = Vector(loc) + inward * step
    return False


def _segment_blocked_by_opaque(scene, depsgraph, p_from, p_to):
    """Retorna True se houver geometria opaca entre ``p_from`` e ``p_to``."""
    if depsgraph is None:
        return False
    a = Vector(p_from)
    b = Vector(p_to)
    diff = b - a
    total = diff.length
    if total < 0.08:
        return False
    d = diff / total
    step = 0.02
    probe = a + d * step
    stop_margin = 0.05

    for _ in range(8):
        rem = (b - probe).dot(d) - stop_margin
        if rem <= step:
            return False
        try:
            hit, loc, _norm, poly_idx, hit_obj, _mat = scene.ray_cast(
                depsgraph, probe, d, distance=rem
            )
        except Exception:
            return False
        if not hit:
            return False
        if not _is_transparent_hit(hit_obj, poly_idx):
            return True
        probe = Vector(loc) + d * step
    return False


def _is_tight_enclosure(scene, depsgraph, pt):
    """Retorna True se ``pt`` estiver dentro de um nicho/móvel estreito (< 0.9m de vão)."""
    if depsgraph is None:
        return False
    axes = (
        (Vector((1.0, 0.0, 0.0)), Vector((-1.0, 0.0, 0.0))),
        (Vector((0.0, 1.0, 0.0)), Vector((0.0, -1.0, 0.0))),
    )
    for pos_d, neg_d in axes:
        try:
            hit_p, loc_p, *_ = scene.ray_cast(depsgraph, pt, pos_d, distance=0.9)
            hit_n, loc_n, *_ = scene.ray_cast(depsgraph, pt, neg_d, distance=0.9)
        except Exception:
            continue
        if hit_p and hit_n:
            span = (Vector(loc_p) - Vector(loc_n)).length
            if span < 0.9:
                return True
    return False


def _room_probe_points(scene, depsgraph, cam_cfg):
    """Calcula pontos internos representativos do cômodo a partir da câmera."""
    eye = Vector(cam_cfg.get("eye", (0.0, 0.0, 1.6)))
    target = Vector(cam_cfg.get("target", (0.0, 1.0, 1.0)))
    diff = target - eye
    dist = diff.length
    fwd = (diff / dist) if dist > 1e-6 else Vector((0.0, 1.0, 0.0))

    p_eye = eye + fwd * min(0.25, max(0.05, dist * 0.15))
    points = [p_eye]
    if dist > 0.6:
        p_mid = eye.lerp(target, 0.55)
        if not _is_tight_enclosure(scene, depsgraph, p_mid):
            points.append(p_mid)
    return points


def _sky_sample_directions():
    """Retorna 21 direções distribuídas no hemisfério superior e linha do horizonte."""
    dirs = [(0.0, 0.0, 1.0)]
    for i in range(8):
        ang = math.radians(i * 45.0)
        dirs.append((0.766 * math.cos(ang), 0.766 * math.sin(ang), 0.643))
    for i in range(8):
        ang = math.radians(i * 45.0 + 22.5)
        dirs.append((0.966 * math.cos(ang), 0.966 * math.sin(ang), 0.259))
    dirs.extend(((1.0, 0.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, -1.0, 0.0)))
    return dirs


def measure_room_confinement(scene, depsgraph, cam_cfg, sun_dir=None):
    """Mede se a câmera está em ambiente confinado (teto/paredes opacas) e quanto céu/sol entra."""
    if depsgraph is None or not cam_cfg:
        return {
            "enclosed": False,
            "has_ceiling": False,
            "sky_open_ratio": 1.0,
            "sky_exposure": 1.0,
            "sun_visibility": 1.0,
        }

    probe_pts = _room_probe_points(scene, depsgraph, cam_cfg)
    up_dirs = (
        (0.0, 0.0, 1.0),
        (0.35, 0.0, 0.937),
        (-0.35, 0.0, 0.937),
        (0.0, 0.35, 0.937),
        (0.0, -0.35, 0.937),
    )
    open_up = sum(
        1 for d in up_dirs if any(_ray_reaches_sky(scene, depsgraph, pt, d) for pt in probe_pts)
    )
    has_ceiling = open_up <= 1

    sky_dirs = _sky_sample_directions()
    open_sky = sum(
        1 for d in sky_dirs if any(_ray_reaches_sky(scene, depsgraph, pt, d) for pt in probe_pts)
    )
    sky_open_ratio = open_sky / float(len(sky_dirs))

    enclosed = bool(has_ceiling or sky_open_ratio < 0.15)
    sky_exposure = min(1.0, sky_open_ratio * 1.8) if enclosed else 1.0

    sun_visibility = 1.0
    if sun_dir:
        s_base = Vector(sun_dir)
        if s_base.length > 1e-6:
            s_base.normalize()
            perp_a = s_base.cross(Vector((0.0, 0.0, 1.0)) if abs(s_base.z) < 0.9 else Vector((1.0, 0.0, 0.0))).normalized()
            perp_b = s_base.cross(perp_a).normalized()
            sun_samples = (
                s_base,
                (s_base + perp_a * 0.06).normalized(),
                (s_base - perp_a * 0.06).normalized(),
                (s_base + perp_b * 0.06).normalized(),
                (s_base - perp_b * 0.06).normalized(),
            )
            open_sun = sum(
                1 for d in sun_samples if any(_ray_reaches_sky(scene, depsgraph, pt, d) for pt in probe_pts)
            )
            sun_visibility = open_sun / float(len(sun_samples))

    return {
        "enclosed": enclosed,
        "has_ceiling": has_ceiling,
        "sky_open_ratio": sky_open_ratio,
        "sky_exposure": sky_exposure,
        "sun_visibility": sun_visibility,
    }


def _configure_material_shadow_containment(mat, preset_type, cfg, bsdf):
    """Garante sombra dupla-face opaca no EEVEE para paredes, tetos e chapas não transparentes."""
    sub_l = str((cfg or {}).get("sub_type", "")).lower()
    name_l = (getattr(mat, "name", "") or "").lower()
    cfg_op = (cfg or {}).get("opacity")
    has_opacity_override = False
    if cfg_op is not None:
        try:
            has_opacity_override = float(cfg_op) < 0.99
        except (TypeError, ValueError):
            has_opacity_override = False
    is_transparent = (
        preset_type == "vidro"
        or has_opacity_override
        or "transluc" in sub_l
        or "translúcid" in sub_l
        or "acrílico" in sub_l
        or "acrilico" in sub_l
        or "voil" in sub_l
        or any(k in name_l for k in ("vidro", "glass", "reflecta", "voil"))
    )
    if not is_transparent and not preset_type and bsdf is not None:
        trans_sock = bsdf.inputs.get("Transmission Weight") or bsdf.inputs.get("Transmission")
        if trans_sock is not None and float(getattr(trans_sock, "default_value", 0.0) or 0.0) > 0.15:
            is_transparent = True
        alpha_sock = bsdf.inputs.get("Alpha")
        if alpha_sock is not None and float(getattr(alpha_sock, "default_value", 1.0) or 1.0) < 0.85:
            is_transparent = True

    if is_transparent:
        return
    if hasattr(mat, "use_backface_culling"):
        mat.use_backface_culling = False
    if hasattr(mat, "shadow_method"):
        try:
            mat.shadow_method = "OPAQUE"
        except Exception:
            pass


def _apply_opacity_override(mat, bsdf, cfg, *, nodes=None, links=None):
    """Aplica transparência explícita (0..1) configurada no Editor de Materiais."""
    if not isinstance(cfg, dict) or cfg.get("opacity") is None or bsdf is None:
        return
    try:
        op_val = max(0.0, min(1.0, float(cfg["opacity"])))
    except (TypeError, ValueError):
        return
    if op_val >= 0.999:
        return

    alpha_inp = bsdf.inputs.get("Alpha")
    if alpha_inp is not None:
        existing_links = list(getattr(alpha_inp, "links", ()) or ())
        if existing_links and nodes is not None and links is not None:
            link = existing_links[0]
            src_sock = getattr(link, "from_socket", None)
            if src_sock is None and isinstance(link, (tuple, list)) and link:
                src_sock = link[0]
            if src_sock is not None:
                try:
                    links.remove(link)
                    mult = nodes.new("ShaderNodeMath")
                    mult.operation = "MULTIPLY"
                    links.new(src_sock, mult.inputs[0])
                    mult.inputs[1].default_value = op_val
                    links.new(mult.outputs[0], alpha_inp)
                except Exception:
                    _set_bsdf_prop(bsdf, ("Alpha",), op_val)
            else:
                _set_bsdf_prop(bsdf, ("Alpha",), op_val)
        else:
            _set_bsdf_prop(bsdf, ("Alpha",), op_val)

    if hasattr(mat, "blend_method"):
        try:
            mat.blend_method = "BLEND"
        except Exception:
            pass
    if hasattr(mat, "use_backface_culling"):
        mat.use_backface_culling = False


def _sanitize_gltf_mat_name(raw):
    """Espelha ``formats.meshexport.export_names`` para casar nomes sanitizados no GLB."""
    raw_s = str(raw or "").strip()
    if not raw_s:
        return ""
    base = "".join(c if c.isalnum() or c in "._-" else "_" for c in raw_s).strip("._-")
    if not base:
        return ""
    if base[0].isdigit():
        base = f"m_{base}"
    return base.lower()


def _match_material_override(mat, bsdf, nodes, overrides):
    """Encontra o override de material correspondente a ``mat``.

    Prioriza o identificador exato ``trazomob_pbr_id`` gravado pelo exportador GLB
    nos custom properties do material (sem depender de heurística de nome). Mantém
    fallbacks exatos para GLBs externos ou antigos onde o extra ainda não exista.
    """
    if not isinstance(overrides, dict) or not overrides:
        return {}

    # 0. Identificador exato anexado diretamente ao material durante a exportação GLB
    pbr_id = mat.get("trazomob_pbr_id") if hasattr(mat, "get") else None
    if pbr_id:
        cfg = overrides.get(str(pbr_id))
        if isinstance(cfg, dict) and cfg:
            return cfg
        return {}

    mat_name = getattr(mat, "name", None) or ""
    name_lower = mat_name.lower()
    cfg = overrides.get(mat_name) or overrides.get(name_lower)
    if isinstance(cfg, dict) and cfg:
        return cfg

    # Remove sufixo de deduplicacao do Blender (.001, .002)
    mat_no_dup = re.sub(r"\.\d{3}$", "", mat_name)
    if mat_no_dup != mat_name:
        cfg = overrides.get(mat_no_dup) or overrides.get(mat_no_dup.lower())
        if isinstance(cfg, dict) and cfg:
            return cfg

    # 1. Correspondencia pela sanitizacao exata de formats.meshexport.export_names
    # (ex.: "[Color C02]" -> "Color_C02", "*2" -> "m_2" / "m_2_2", "10 - Default" -> "m_10_-_Default")
    san_map = {}
    for k, v in overrides.items():
        if not isinstance(v, dict):
            continue
        sk = _sanitize_gltf_mat_name(k)
        if sk and sk not in san_map:
            san_map[sk] = v

    mat_san = _sanitize_gltf_mat_name(mat_no_dup)
    if mat_san in san_map:
        return san_map[mat_san]

    mat_san_base = re.sub(r"_\d+$", "", mat_san)
    if mat_san_base and mat_san_base != "m" and mat_san_base in san_map:
        return san_map[mat_san_base]

    # 2. Fallback de espaco vs underscore + sufixo de colisao glTF (_2, _3)
    clean_name = mat_no_dup.replace("_", " ").strip().lower()
    base_clean = re.sub(r" \d+$", "", clean_name).strip()
    for k, v in overrides.items():
        if not isinstance(v, dict):
            continue
        k_clean = str(k).replace("_", " ").strip().lower()
        if k_clean == clean_name or (base_clean and k_clean == base_clean):
            return v

    # 3. Materiais texturizados anonimos (matN no GLB) identificados pelo stem da imagem
    tex_img_node = next((n for n in nodes if getattr(n, "type", None) == "TEX_IMAGE"), None)
    img = getattr(tex_img_node, "image", None) if tex_img_node is not None else None
    img_name = getattr(img, "name", None) or getattr(img, "filepath", None) or ""
    if img_name:
        img_clean = os.path.basename(str(img_name))
        img_clean = re.sub(r"\.\d{3}$", "", img_clean)
        stem = os.path.splitext(img_clean)[0]
        if stem:
            cfg = overrides.get(stem) or overrides.get(stem.lower())
            if isinstance(cfg, dict) and cfg:
                return cfg
            stem_san = _sanitize_gltf_mat_name(stem)
            if stem_san in san_map:
                return san_map[stem_san]

    # 4. Correspondencia por cor RGB hexadecimal (ex.: 'Cor #A3A3A3')
    base_col_inp = bsdf.inputs.get("Base Color") if bsdf is not None else None
    if base_col_inp and hasattr(base_col_inp, "default_value"):
        c_val = base_col_inp.default_value
        if isinstance(c_val, (tuple, list)) or hasattr(c_val, "__len__"):
            r, g, b = float(c_val[0]) * 255.0, float(c_val[1]) * 255.0, float(c_val[2]) * 255.0
            best_diff = 999.0
            best_cfg = None
            for k, v in overrides.items():
                if not isinstance(v, dict):
                    continue
                m_hex = re.match(r"(?i)^cor\s*#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$", str(k).strip())
                if m_hex:
                    kr, kg, kb = int(m_hex.group(1), 16), int(m_hex.group(2), 16), int(m_hex.group(3), 16)
                    diff = abs(r - kr) + abs(g - kg) + abs(b - kb)
                    if diff <= 4.0 and diff < best_diff:
                        best_diff = diff
                        best_cfg = v
            if best_cfg is not None:
                return best_cfg

    return {}


def setup_photoreal_materials(use_bevel=True, material_overrides=None, clay_mode=False):
    """Varre todos os materiais do modelo e aplica shaders PBR de alta fidelidade para marcenaria,
    respeitando overrides configurados pelo usuário na interface do TrazoMob (tecido, pedra, madeira, etc.).
    Suporta modo Maquete Branca (Clay Render) e materiais autoiluminados Emit[potência].
    """
    overrides = material_overrides or {}

    # Modo Clay Render: maquete branca fosca para estudo puro de luz e sombra
    if clay_mode:
        clay_mat = bpy.data.materials.new(name="TrazoMob_Clay_Mat")
        clay_mat.use_nodes = True
        c_nodes = clay_mat.node_tree.nodes
        c_links = clay_mat.node_tree.links
        c_nodes.clear()
        c_bsdf = c_nodes.new("ShaderNodeBsdfPrincipled")
        _set_bsdf_prop(c_bsdf, ("Base Color",), (0.85, 0.85, 0.85, 1.0))
        _set_bsdf_prop(c_bsdf, ("Roughness",), 0.75)
        _set_bsdf_prop(c_bsdf, ("Specular IOR Level", "Specular"), 0.2)
        c_out = c_nodes.new("ShaderNodeOutputMaterial")
        c_links.new(c_bsdf.outputs["BSDF"], c_out.inputs["Surface"])

        for obj in bpy.context.scene.objects:
            if obj.type == "MESH":
                obj.data.materials.clear()
                obj.data.materials.append(clay_mat)
        say("clay_mode_applied")
        return

    for mat in bpy.data.materials:
        if not mat.node_tree:
            continue
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        bsdf = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is None:
            continue

        mat_name = mat.name or ""
        name_lower = mat_name.lower()

        # Suporte a materiais emissores: Emit[potência] ou EmitFake
        if "emitfake" in name_lower:
            _set_bsdf_prop(bsdf, ("Emission Strength", "Emission"), 1.0)
            _set_bsdf_prop(bsdf, ("Roughness",), 1.0)
            continue
        elif "emit[" in name_lower:
            m = re.search(r"emit\[([0-9\.]+)\]", name_lower)
            pwr = float(m.group(1)) if m else 10.0
            _set_bsdf_prop(bsdf, ("Emission Strength", "Emission"), pwr)
            continue

        cfg = _match_material_override(mat, bsdf, nodes, overrides)


        # ── 1. Injeta Nó de Bevel (Chanfro / Quina Arredondada Fotorrealista) ──
        bevel_node = None
        if use_bevel:
            bevel_node = nodes.new("ShaderNodeBevel")
            bevel_node.inputs["Radius"].default_value = 0.0015  # Raio de 1.5mm (escala de fita de borda de marcenaria)
            bevel_node.samples = 8
            links.new(bevel_node.outputs["Normal"], bsdf.inputs["Normal"])

        # ── 2. SE O USUÁRIO DEFINIU PRESET EXPLICITAMENTE NO PAINEL ──
        preset_type = cfg.get("type")
        if preset_type == "auto":
            preset_type = None
        _configure_material_shadow_containment(mat, preset_type, cfg, bsdf)
        if preset_type:
            _apply_opacity_override(mat, bsdf, cfg, nodes=nodes, links=links)
            roughness = float(cfg.get("roughness", 0.5))
            specular = float(cfg.get("specular", 0.5)) if "specular" in cfg else None
            bump_strength = float(cfg.get("bump", 0.02))

            if preset_type == "tecido":
                # Tecido / Estofado / Cortina (Veludo, Linho, Algodão)
                _set_bsdf_prop(bsdf, ("Roughness",), max(0.65, roughness))
                _set_bsdf_prop(bsdf, ("Metallic",), 0.0)
                _set_bsdf_prop(bsdf, ("Specular IOR Level", "Specular"), specular if specular is not None else 0.1)
                _set_bsdf_prop(bsdf, ("Sheen Weight", "Sheen"), 0.85)  # Brilho de penugem nas bordas
                _set_bsdf_prop(bsdf, ("Sheen Roughness",), 0.5)
                # Trama fina de tecido (micro-weave noise)
                noise = nodes.new("ShaderNodeTexNoise")
                noise.inputs["Scale"].default_value = 160.0
                if "Detail" in noise.inputs:
                    noise.inputs["Detail"].default_value = 8.0
                bump = nodes.new("ShaderNodeBump")
                bump.inputs["Strength"].default_value = bump_strength or 0.035
                links.new(noise.outputs["Fac"], bump.inputs["Height"])
                links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
                continue

            elif preset_type in ("tapete", "carpete_felpudo"):
                # Tapete / Carpete (Felpudo Shaggy / Pelo Curto 3D ou Trama Plana Sem Pelos)
                sub = str(cfg.get("sub_type", "")).lower()
                is_shaggy, is_short_pile = _is_shaggy_carpet(preset_type, cfg)
                eff_bump = float(cfg.get("bump", 0.055 if is_shaggy else 0.03))
                _set_bsdf_prop(bsdf, ("Roughness",), max(0.70, roughness))
                _set_bsdf_prop(bsdf, ("Metallic",), 0.0)
                _set_bsdf_prop(bsdf, ("Specular IOR Level", "Specular"), specular if specular is not None else 0.08)
                _set_bsdf_prop(bsdf, ("Sheen Weight", "Sheen"), 0.95 if is_shaggy else 0.65)
                _set_bsdf_prop(bsdf, ("Sheen Roughness",), 0.65 if is_shaggy else 0.45)

                bump = nodes.new("ShaderNodeBump")
                if not is_shaggy and ("boucl" in sub or "comercial" in sub):
                    voronoi = nodes.new("ShaderNodeTexVoronoi")
                    voronoi.inputs["Scale"].default_value = 180.0
                    bump.inputs["Strength"].default_value = eff_bump or 0.025
                    links.new(voronoi.outputs["Distance"], bump.inputs["Height"])
                else:
                    noise = nodes.new("ShaderNodeTexNoise")
                    noise.inputs["Scale"].default_value = (
                        140.0 if is_short_pile else (95.0 if is_shaggy else 220.0)
                    )
                    if "Detail" in noise.inputs:
                        noise.inputs["Detail"].default_value = 10.0
                    bump.inputs["Strength"].default_value = eff_bump or (0.055 if is_shaggy else 0.03)
                    links.new(noise.outputs["Fac"], bump.inputs["Height"])
                links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

                if is_shaggy:
                    hair_len = (
                        max(0.004, eff_bump * 0.14)
                        if is_short_pile
                        else max(0.010, eff_bump * 0.35)
                    )
                    _apply_carpet_hair_particles(
                        mat,
                        hair_length=hair_len,
                        is_short_pile=is_short_pile,
                    )
                continue
                # Pedra / Mármore / Granito / Quartzo / Porcelanato
                is_polido = cfg.get("sub_type", "polido") == "polido"
                _set_bsdf_prop(bsdf, ("Roughness",), roughness if not is_polido else 0.06)
                _set_bsdf_prop(bsdf, ("Metallic",), 0.0)
                spec_val = specular if specular is not None else 0.85
                _set_bsdf_prop(bsdf, ("Specular IOR Level", "Specular"), spec_val)
                if is_polido:
                    _set_bsdf_prop(bsdf, ("Coat Weight", "Clearcoat"), min(1.0, spec_val * 0.8))
                    _set_bsdf_prop(bsdf, ("Coat Roughness", "Clearcoat Roughness"), 0.02)
                tex_img_node = next((n for n in nodes if n.type == "TEX_IMAGE"), None)
                bump = nodes.new("ShaderNodeBump")
                bump.inputs["Strength"].default_value = bump_strength or 0.015
                if tex_img_node:
                    links.new(tex_img_node.outputs["Color"], bump.inputs["Height"])
                else:
                    noise = nodes.new("ShaderNodeTexNoise")
                    noise.inputs["Scale"].default_value = 45.0
                    if "Detail" in noise.inputs:
                        noise.inputs["Detail"].default_value = 6.0
                    links.new(noise.outputs["Fac"], bump.inputs["Height"])
                if bevel_node:
                    links.new(bevel_node.outputs["Normal"], bump.inputs["Normal"])
                links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
                continue

            elif preset_type == "madeira":
                # Madeira / MDF
                is_gloss = cfg.get("sub_type") == "gloss"
                _set_bsdf_prop(bsdf, ("Roughness",), roughness if not is_gloss else 0.05)
                _set_bsdf_prop(bsdf, ("Metallic",), 0.0)
                spec_val = specular if specular is not None else 0.5
                _set_bsdf_prop(bsdf, ("Specular IOR Level", "Specular"), spec_val)
                if is_gloss:
                    _set_bsdf_prop(bsdf, ("Coat Weight", "Clearcoat"), min(1.0, spec_val * 0.9))
                    _set_bsdf_prop(bsdf, ("Coat Roughness", "Clearcoat Roughness"), 0.02)
                else:
                    tex_img_node = next((n for n in nodes if n.type == "TEX_IMAGE"), None)
                    bump = nodes.new("ShaderNodeBump")
                    bump.inputs["Strength"].default_value = bump_strength or 0.035
                    if tex_img_node:
                        links.new(tex_img_node.outputs["Color"], bump.inputs["Height"])
                    else:
                        noise = nodes.new("ShaderNodeTexNoise")
                        noise.inputs["Scale"].default_value = 35.0
                        links.new(noise.outputs["Fac"], bump.inputs["Height"])
                    if bevel_node:
                        links.new(bevel_node.outputs["Normal"], bump.inputs["Normal"])
                    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
                continue

            elif preset_type == "cromado":
                # Cromado / Inox Polido / Espelho Metálico
                _set_bsdf_prop(bsdf, ("Metallic",), 1.0)
                _set_bsdf_prop(bsdf, ("Roughness",), roughness if roughness < 0.1 else 0.02)
                _set_bsdf_prop(bsdf, ("Specular IOR Level", "Specular"), specular if specular is not None else 1.0)
                sub = str(cfg.get("sub_type", "")).lower()
                if "gold" in sub or "dourado" in sub:
                    _set_bsdf_prop(bsdf, ("Base Color",), (1.0, 0.766, 0.336, 1.0))
                elif "cobre" in sub or "rose" in sub:
                    _set_bsdf_prop(bsdf, ("Base Color",), (0.955, 0.637, 0.538, 1.0))
                elif "black" in sub:
                    _set_bsdf_prop(bsdf, ("Base Color",), (0.15, 0.15, 0.15, 1.0))
                else:
                    _set_bsdf_prop(bsdf, ("Base Color",), (0.95, 0.95, 0.95, 1.0))
                continue

            elif preset_type == "metal":
                # Metais (Inox, Alumínio, Dourado, Preto)
                _set_bsdf_prop(bsdf, ("Metallic",), 1.0)
                _set_bsdf_prop(bsdf, ("Roughness",), roughness)
                _set_bsdf_prop(bsdf, ("Specular IOR Level", "Specular"), specular if specular is not None else 0.9)
                _set_bsdf_prop(bsdf, ("Anisotropic",), 0.35)
                continue

            elif preset_type == "plastico":
                # Plástico / Acrílico / Fórmicas
                sub = str(cfg.get("sub_type", "")).lower()
                is_trans = "translúcido" in sub or "translucido" in sub or "acrílico" in sub or "acrilico" in sub
                _set_bsdf_prop(bsdf, ("Metallic",), 0.0)
                _set_bsdf_prop(bsdf, ("Roughness",), roughness)
                spec_val = specular if specular is not None else 0.5
                _set_bsdf_prop(bsdf, ("Specular IOR Level", "Specular"), spec_val)
                if is_trans:
                    _set_bsdf_prop(bsdf, ("Transmission Weight", "Transmission"), 0.88)
                    _set_bsdf_prop(bsdf, ("Roughness",), max(0.08, roughness))
                    _set_bsdf_prop(bsdf, ("IOR",), 1.49)
                    # Habilita refração no EEVEE Next e suporte a transparência
                    for attr, val in (("blend_method", "OPAQUE"), ("use_screen_refraction", True), ("use_raytrace_refraction", True)):
                        if hasattr(mat, attr):
                            try:
                                setattr(mat, attr, val)
                            except Exception:
                                pass
                elif "brilhante" in sub:
                    _set_bsdf_prop(bsdf, ("Coat Weight", "Clearcoat"), min(1.0, spec_val * 0.8))
                    _set_bsdf_prop(bsdf, ("Coat Roughness", "Clearcoat Roughness"), 0.03)
                continue

            elif preset_type == "ceramica":
                # Cerâmica / Louça / Azulejo
                _set_bsdf_prop(bsdf, ("Metallic",), 0.0)
                _set_bsdf_prop(bsdf, ("Roughness",), roughness if roughness < 0.15 else 0.04)
                spec_val = specular if specular is not None else 0.8
                _set_bsdf_prop(bsdf, ("Specular IOR Level", "Specular"), spec_val)
                _set_bsdf_prop(bsdf, ("Coat Weight", "Clearcoat"), min(1.0, spec_val * 0.9))
                _set_bsdf_prop(bsdf, ("Coat Roughness", "Clearcoat Roughness"), 0.02)
                continue

            elif preset_type == "emissivo":
                # Superfície que emite luz (LED / Neon / Painel Iluminado / Tela de TV)
                sub = str(cfg.get("sub_type", "")).lower()
                is_screen = any(k in sub for k in ("painel", "tv", "tela", "monitor"))
                custom_emit = cfg.get("emission_strength")
                custom_emit = max(0.1, float(custom_emit)) if custom_emit is not None else None
                tex_img_node = next((n for n in nodes if getattr(n, "type", None) == "TEX_IMAGE"), None)
                emit_sock = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")

                if is_screen:
                    screen_rough = min(0.12, roughness if roughness > 0.0 else 0.08)
                    _set_bsdf_prop(bsdf, ("Roughness",), screen_rough)
                    _set_bsdf_prop(bsdf, ("Metallic",), 0.0)
                    _set_bsdf_prop(bsdf, ("Specular IOR Level", "Specular"), 0.85)
                    _set_bsdf_prop(bsdf, ("Coat Weight", "Clearcoat"), 0.5)
                    _set_bsdf_prop(bsdf, ("Coat Roughness", "Clearcoat Roughness"), 0.03)

                    if (
                        tex_img_node is not None
                        and emit_sock is not None
                        and "Color" in getattr(tex_img_node, "outputs", {})
                    ):
                        for link in list(getattr(emit_sock, "links", ())):
                            links.remove(link)
                        links.new(tex_img_node.outputs["Color"], emit_sock)
                        _set_bsdf_prop(bsdf, ("Emission Strength",), custom_emit if custom_emit is not None else 2.4)
                        light_col = (0.78, 0.88, 1.0)
                    else:
                        base_inp = bsdf.inputs.get("Base Color")
                        base_val = getattr(base_inp, "default_value", (0.0, 0.0, 0.0, 1.0)) if base_inp else (0.0, 0.0, 0.0, 1.0)
                        r, g, b = float(base_val[0]), float(base_val[1]), float(base_val[2])
                        top = max(r, g, b)
                        if top < 0.22:
                            emit_col = (0.76, 0.86, 1.0, 1.0)
                            _set_bsdf_prop(bsdf, ("Base Color",), (0.12, 0.16, 0.22, 1.0))
                        else:
                            scale = max(1.0, 0.85 / top)
                            emit_col = (
                                min(1.0, r * scale),
                                min(1.0, g * scale),
                                min(1.0, b * scale),
                                1.0,
                            )
                        _set_bsdf_prop(bsdf, ("Emission Color", "Emission"), emit_col)
                        _set_bsdf_prop(bsdf, ("Emission Strength",), custom_emit if custom_emit is not None else 2.8)
                        light_col = emit_col[:3]

                    try:
                        mat["trazomob_emissive_kind"] = "screen"
                        mat["trazomob_emissive_color"] = list(light_col)
                    except Exception:
                        pass
                else:
                    _set_bsdf_prop(bsdf, ("Roughness",), 0.2)
                    if "3000k" in sub or "quente" in sub:
                        emit_col = (1.0, 0.82, 0.58, 1.0)
                    elif "6000k" in sub or "fria" in sub:
                        emit_col = (0.85, 0.92, 1.0, 1.0)
                    else:
                        emit_col = (1.0, 0.95, 0.88, 1.0)
                    _set_bsdf_prop(bsdf, ("Emission Color", "Emission"), emit_col)
                    _set_bsdf_prop(bsdf, ("Emission Strength",), custom_emit if custom_emit is not None else 8.0)
                    try:
                        mat["trazomob_emissive_kind"] = "led"
                        mat["trazomob_emissive_color"] = list(emit_col[:3])
                    except Exception:
                        pass
                continue

            elif preset_type == "parede":
                # Tinta de Parede / Drywall / Cimento. O padrao acetinado usa
                # roughness 0.45; os demais continuam foscos (minimo 0.7).
                sub_wall = str(cfg.get("sub_type", "")).lower()
                wall_rough = 0.45 if "acetinad" in sub_wall else max(0.7, roughness)
                _set_bsdf_prop(bsdf, ("Roughness",), wall_rough)
                _set_bsdf_prop(bsdf, ("Metallic",), 0.0)
                _set_bsdf_prop(bsdf, ("Specular IOR Level", "Specular"), specular if specular is not None else 0.2)
                noise = nodes.new("ShaderNodeTexNoise")
                noise.inputs["Scale"].default_value = 120.0
                bump = nodes.new("ShaderNodeBump")
                bump.inputs["Strength"].default_value = bump_strength or 0.015
                links.new(noise.outputs["Fac"], bump.inputs["Height"])
                links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
                continue

            elif preset_type == "vidro":
                # Vidro / Reflecta
                _set_bsdf_prop(bsdf, ("Transmission Weight", "Transmission"), 1.0)
                _set_bsdf_prop(bsdf, ("Roughness",), roughness)
                _set_bsdf_prop(bsdf, ("IOR",), 1.52)
                continue

            elif preset_type == "couro":
                # Couro / Couro Sintético
                _set_bsdf_prop(bsdf, ("Roughness",), max(0.4, roughness))
                _set_bsdf_prop(bsdf, ("Specular IOR Level", "Specular"), specular if specular is not None else 0.3)
                voronoi = nodes.new("ShaderNodeTexVoronoi")
                voronoi.inputs["Scale"].default_value = 120.0
                bump = nodes.new("ShaderNodeBump")
                bump.inputs["Strength"].default_value = bump_strength or 0.04
                links.new(voronoi.outputs["Distance"], bump.inputs["Height"])
                links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
                continue

        # Se o material não possui configuração explícita, mantém as propriedades padrão do material/textura original
        else:
            tex_img_node = next((n for n in nodes if n.type == "TEX_IMAGE"), None)
            if tex_img_node:
                # Conexão automática de transparência Alpha para imagens PNG recortadas
                alpha_inp = bsdf.inputs.get("Alpha")
                if ("Alpha" in tex_img_node.outputs and alpha_inp is not None
                        and not getattr(alpha_inp, "links", ())):
                    links.new(tex_img_node.outputs["Alpha"], alpha_inp)
            _apply_opacity_override(mat, bsdf, cfg, nodes=nodes, links=links)
            if bevel_node:
                links.new(bevel_node.outputs["Normal"], bsdf.inputs["Normal"])



def set_architectural_camera(scene, cam_cfg, width, height, correct_verticals=False):
    """Cria uma câmera perfeitamente alinhada com o viewport do IngeTrazo.

    Reproduz com precisão milimétrica a matriz do IngeTrazo (resources/blender/render_scene.py)
    e suporta o modo Two-Point Perspective caso o usuário queira verticais corrigidas.
    """
    cam_data = bpy.data.cameras.new("TrazoMob_Cam")
    cam_obj = bpy.data.objects.new("TrazoMob Camera", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    eye = Vector(cam_cfg["eye"])
    target = Vector(cam_cfg["target"])
    up = Vector(cam_cfg["up"])

    fwd = (target - eye).normalized()
    right = fwd.cross(up)
    if right.length < 1e-9:
        right = fwd.cross(Vector((0.0, 1.0, 0.0)))
    right.normalize()
    true_up = right.cross(fwd).normalized()

    # Se 'correct_verticals' estiver marcado (ou a câmera original já for two_point):
    if correct_verticals and abs(fwd.z) > 0.01:
        fwd_level = Vector((fwd.x, fwd.y, 0.0)).normalized()
        true_up_level = Vector((0.0, 0.0, 1.0))
        right_level = fwd_level.cross(true_up_level).normalized()
        rot = Matrix((right_level, true_up_level, -fwd_level)).transposed()
        cam_obj.matrix_world = Matrix.Translation(eye) @ rot.to_4x4()

        # O deslocamento óptico correto do frustum no Blender (Shift Y):
        # target_rel = target - eye.
        # depth = target_rel . level_forward
        # shift_y = rel.z / depth
        rel = target - eye
        depth = rel.dot(fwd_level)
        if abs(depth) > 1e-4:
            fov_rad = math.radians(cam_cfg.get("fov_deg", 45.0))
            # No Blender, shift_y = 1.0 desloca exatamente meia altura do sensor.
            # O ângulo de visão vertical corresponde a 2 * atan(half_sensor / focal)
            # Portanto shift_y = (rel.z / depth) / tan(fov / 2)
            half_tan = math.tan(fov_rad / 2.0)
            if half_tan > 1e-4:
                cam_data.shift_y = (rel.z / depth) / (2.0 * half_tan)
    else:
        # Modo 100% idêntico ao viewport do IngeTrazo
        rot = Matrix((right, true_up, -fwd)).transposed()
        cam_obj.matrix_world = Matrix.Translation(eye) @ rot.to_4x4()

    cam_data.sensor_fit = "VERTICAL"
    if cam_cfg.get("perspective", True):
        cam_data.type = "PERSP"
        cam_data.angle_y = math.radians(cam_cfg.get("fov_deg", 45.0))
    else:
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = 2.0 * cam_cfg.get("half_height", 2.0) * max(
            1.0, width / max(height, 1)
        )

    cam_data.clip_start = max(cam_cfg.get("near", 0.05), 1e-4)
    cam_data.clip_end = max(cam_cfg.get("far", 1e5), cam_data.clip_start * 10)
    return cam_obj


def _find_blender_hdri(name="interior.exr"):
    """Localiza mapas HDRI/EXR de iluminação ambiente oficiais do Blender."""
    import glob
    candidates = []
    # 1. Tenta a partir do caminho de recursos do próprio Blender em execução
    try:
        base_res = bpy.utils.resource_path("LOCAL")
        candidates.append(os.path.join(base_res, "datafiles", "studiolights", "world", name))
    except Exception:
        pass
    # 2. Varreduras padrão de instalação no Windows / Linux / Mac
    try:
        for cand in glob.glob(os.path.join(os.path.dirname(bpy.app.binary_path), "**", name), recursive=True):
            candidates.append(cand)
    except Exception:
        pass
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def _compute_interior_bounce(interior_lights):
    """Calcula preenchimento indireto sutil de rebote interno (<= 0.04) com base nas luzes internas."""
    total_power = 0.0
    r_acc = 0.0
    g_acc = 0.0
    b_acc = 0.0
    for lt in interior_lights or ():
        if not lt.get("on", True):
            continue
        pwr = max(0.0, float(lt.get("power", 0.0)))
        if pwr <= 0.0:
            continue
        col = lt.get("color", (1.0, 0.9, 0.8))
        total_power += pwr
        r_acc += float(col[0]) * pwr
        g_acc += float(col[1]) * pwr
        b_acc += float(col[2]) * pwr
    if total_power <= 0.0:
        return 0.0, (0.0, 0.0, 0.0, 1.0)
    strength = min(0.04, max(0.005, (total_power / 1200.0) * 0.04))
    col_avg = (
        max(0.0, min(1.0, r_acc / total_power)),
        max(0.0, min(1.0, g_acc / total_power)),
        max(0.0, min(1.0, b_acc / total_power)),
        1.0,
    )
    return strength, col_avg


def apply_lighting_preset(
    scene,
    preset_name="dia",
    sun_dir=None,
    *,
    engine="cycles",
    confinement=None,
    interior_lights=None,
):
    """Aplica iluminação profissional de ambientes internos com suporte a HDRI de alta fidelidade."""
    world = bpy.data.worlds.new(f"TrazoMob_World_{preset_name}")
    scene.world = world
    if hasattr(world, "use_nodes"):
        world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    out_node = nodes.new("ShaderNodeOutputWorld")

    # Caso especial: Preset Totalmente Escuro / Breu (sem HDRI, sem sol, sem luz de ambiente)
    # Apenas as lâmpadas e fitas LED reais do usuário iluminam a cena (mesmo no EEVEE)
    if preset_name in ("escuro", "dark", "breu"):
        bg = nodes.new("ShaderNodeBackground")
        bg.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
        bg.inputs["Strength"].default_value = 0.0
        links.new(bg.outputs["Background"], out_node.inputs["Surface"])
        return

    is_eevee = str(engine or "cycles").lower() != "cycles"
    conf = confinement if (is_eevee and isinstance(confinement, dict)) else None
    is_confined = bool(conf and (conf.get("enclosed") or float(conf.get("sky_exposure", 1.0)) < 1.0))
    sky_open_ratio = float(conf.get("sky_open_ratio", 1.0)) if is_confined else 1.0
    sky_exposure = max(0.25, min(1.0, float(conf.get("sky_exposure", 1.0)))) if is_confined else 1.0
    sun_visibility = max(0.25, min(1.0, float(conf.get("sun_visibility", 1.0)))) if is_confined else 1.0
    fully_sealed = False

    base_strength = 1.0 if preset_name == "estudio" else (0.75 if preset_name == "dia" else 0.5)

    if fully_sealed:
        bounce_strength, bounce_col = _compute_interior_bounce(interior_lights)
        bg = nodes.new("ShaderNodeBackground")
        bg.inputs["Color"].default_value = bounce_col
        bg.inputs["Strength"].default_value = bounce_strength
        links.new(bg.outputs["Background"], out_node.inputs["Surface"])
    else:
        # Localiza HDRI de estúdio / interior arquitetônico
        hdri_file = "interior.exr" if preset_name in ("dia", "tarde", "estudio") else "night.exr"
        hdri_path = _find_blender_hdri(hdri_file) or _find_blender_hdri("studio.exr")

        if hdri_path and os.path.exists(hdri_path):
            # Configuração Dual-Ray via Light Path:
            # 1. Reflexos e Iluminação Indireta usam o HDRI fotográfico (metais, pedras, vidros e madeiras ganham reflexos ricos).
            # 2. A visualização de fundo direta da câmera usa um fundo arquitetônico limpo e elegante.
            env_node = nodes.new("ShaderNodeTexEnvironment")
            try:
                env_node.image = bpy.data.images.load(hdri_path)
            except Exception:
                env_node = None

            if env_node and env_node.image:
                bg_refl = nodes.new("ShaderNodeBackground")
                bg_refl.inputs["Strength"].default_value = base_strength * sky_exposure
                links.new(env_node.outputs["Color"], bg_refl.inputs["Color"])

                bg_cam = nodes.new("ShaderNodeBackground")
                if preset_name == "noturno":
                    bg_cam.inputs["Color"].default_value = (0.015, 0.02, 0.04, 1.0)
                elif preset_name == "tarde":
                    bg_cam.inputs["Color"].default_value = (0.96, 0.94, 0.90, 1.0)
                else:
                    bg_cam.inputs["Color"].default_value = (0.94, 0.95, 0.96, 1.0)
                bg_cam.inputs["Strength"].default_value = 1.0

                mix = nodes.new("ShaderNodeMixShader")
                lp = nodes.new("ShaderNodeLightPath")
                links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
                links.new(bg_refl.outputs["Background"], mix.inputs[1])
                links.new(bg_cam.outputs["Background"], mix.inputs[2])
                links.new(mix.outputs["Shader"], out_node.inputs["Surface"])
            else:
                bg = nodes.new("ShaderNodeBackground")
                bg.inputs["Color"].default_value = (0.92, 0.94, 0.96, 1.0)
                bg.inputs["Strength"].default_value = 1.0 * sky_exposure
                links.new(bg.outputs["Background"], out_node.inputs["Surface"])
        else:
            bg = nodes.new("ShaderNodeBackground")
            bg.inputs["Color"].default_value = (0.92, 0.94, 0.96, 1.0)
            bg.inputs["Strength"].default_value = 1.0 * sky_exposure
            links.new(bg.outputs["Background"], out_node.inputs["Surface"])

    # Se o preset tiver sol físico direcional (dia / tarde)
    if preset_name in ("dia", "tarde") and sun_dir:
        d = Vector(sun_dir).normalized()
        if preset_name == "tarde":
            d = Vector((d.x, d.y, max(0.12, d.z * 0.35))).normalized()
        sun_light = bpy.data.lights.new("TrazoMob Sun", type="SUN")
        base_sun_energy = 3.5 if preset_name == "dia" else 2.5
        sun_light.energy = 0.0 if fully_sealed else (base_sun_energy * sun_visibility)
        soft_deg = float(scene.get("sun_softness", 2.5))
        sun_light.angle = math.radians(soft_deg)
        if hasattr(sun_light, "use_shadow"):
            sun_light.use_shadow = True
        if hasattr(sun_light, "shadow_cascade_max_distance"):
            sun_light.shadow_cascade_max_distance = 50.0
        if preset_name == "tarde":
            sun_light.color = (1.0, 0.78, 0.52)
        sun_obj = bpy.data.objects.new("TrazoMob Sun", sun_light)
        scene.collection.objects.link(sun_obj)
        sun_obj.rotation_euler = d.to_track_quat("Z", "Y").to_euler()


def setup_render_engine(scene, engine="cycles", samples=128):
    """Configura Cycles ou EEVEE com Denoiser de IA e detecção de GPU."""
    if engine == "cycles":
        scene.render.engine = "CYCLES"
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
        # Calibração profissional de rebatimento de luz (Global Illumination):
        # 12 rebotes totais, 6 difusos e 8 de reflexo garantem luz indireta perfeita em nichos e armários
        scene.cycles.max_bounces = 12
        scene.cycles.diffuse_bounces = 6
        scene.cycles.glossy_bounces = 8
        scene.cycles.transmission_bounces = 12
        scene.cycles.transparent_max_bounces = 16
        try:
            # Tenta ativar OpenImageDenoise ou OptiX
            scene.cycles.denoiser = "OPENIMAGEDENOISE"
        except Exception:
            pass

        # Ativa aceleração por GPU se disponível
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            for backend in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
                try:
                    prefs.compute_device_type = backend
                except TypeError:
                    continue
                prefs.get_devices()
                gpus = [d for d in prefs.devices if d.type == backend]
                if gpus:
                    for d in prefs.devices:
                        d.use = d.type in (backend, "CPU")
                    scene.cycles.device = "GPU"
                    say("gpu_enabled", backend)
                    break
        except Exception:
            pass
    else:
        # EEVEE Next ou EEVEE Padrão
        for name in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
            try:
                scene.render.engine = name
                break
            except Exception:
                continue
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = min(samples, 64)
        # EEVEE Next headless (Blender 5.x): use_raytracing=True zera luzes AREA/POINT internas;
        # manter use_raytracing=False preserva as luzes internas e use_gtao/use_fast_gi dá profundidade.
        eevee_flags = {
            "use_shadows": True,
            "use_raytracing": False,
            "use_fast_gi": True,
            "use_gtao": True,
            "use_ssr": True,
            "use_ssr_refraction": True,
            "shadow_ray_count": 4,
            "shadow_step_count": 12,
            "gtao_distance": 0.5,
        }
        for flag, enabled in eevee_flags.items():
            if hasattr(scene.eevee, flag):
                try:
                    setattr(scene.eevee, flag, enabled)
                except Exception:
                    pass
        if hasattr(scene.eevee, "ray_tracing_options"):
            rto = scene.eevee.ray_tracing_options
            for opt, val in {
                "resolution": "HALF",
                "use_denoise": True,
                "denoise_spatial": True,
                "denoise_temporal": True,
                "denoise_bilateral": True,
                "trace_max_roughness": 0.8,
            }.items():
                if hasattr(rto, opt):
                    try:
                        setattr(rto, opt, val)
                    except Exception:
                        pass


def _is_under_cabinet(scene, depsgraph, p1, p2, dir_strip, horiz_dir):
    """Detecta se uma fita horizontal foi clicada junto a uma parede sob um armário aéreo."""
    if depsgraph is None or abs(dir_strip.z) >= 0.25 or horiz_dir.length < 1e-4:
        return False
    probe_dir = horiz_dir.normalized()
    up = Vector((0.0, 0.0, 1.0))
    down = Vector((0.0, 0.0, -1.0))
    for t_s in (0.25, 0.50, 0.75):
        pt = p1.lerp(p2, t_s) + probe_dir * 0.04 + Vector((0.0, 0.0, -0.02))
        try:
            hit_up, *_ = scene.ray_cast(depsgraph, pt, up, distance=0.06)
            hit_dn, *_ = scene.ray_cast(depsgraph, pt, down, distance=0.20)
        except Exception:
            continue
        if hit_up and not hit_dn:
            return True
    return False


def _wall_clearance_offset(scene, depsgraph, p1, p2, dir_strip, fwd_light):
    """Calcula deslocamento perpendicular para afastar a fita de uma parede adjacente."""
    if depsgraph is None or fwd_light.z > -0.5:
        return Vector((0.0, 0.0, 0.0))
    side = Vector((-dir_strip.y, dir_strip.x, 0.0))
    if side.length < 1e-4:
        return Vector((0.0, 0.0, 0.0))
    side.normalize()
    mid = (p1 + p2) * 0.5
    for away in (side, -side):
        probe = mid + Vector((0.0, 0.0, -0.02)) + away * 0.08
        try:
            hit_wall, loc, *_ = scene.ray_cast(depsgraph, probe, -away, distance=0.095)
            hit_opp, *_ = scene.ray_cast(depsgraph, mid + Vector((0.0, 0.0, -0.02)) + away * 0.01, away, distance=0.08)
        except Exception:
            continue
        if hit_wall and not hit_opp:
            current_dist = (mid - loc).dot(away)
            if current_dist < 0.04:
                return away * (0.045 - current_dist)
    return Vector((0.0, 0.0, 0.0))


def _create_led_strip_light(scene, depsgraph, index, lt, color, power):
    """Cria AreaLight retangular desobstruída e difusor emissivo visível para fitas LED."""
    p1 = Vector(lt["p1"])
    p2 = Vector(lt["p2"])
    diff = p2 - p1
    length = diff.length
    if length < 1e-4:
        length = 0.5
        mid = p1.copy()
        dir_strip = Vector((1.0, 0.0, 0.0))
    else:
        mid = (p1 + p2) * 0.5
        dir_strip = diff.normalized()

    raw_dir = Vector(lt.get("dir", (0.0, 0.0, -1.0)))
    fwd_light = raw_dir - dir_strip * raw_dir.dot(dir_strip)
    if fwd_light.length < 1e-4:
        ref_dir = Vector((0.0, 0.0, -1.0)) if abs(dir_strip.z) < 0.9 else Vector((0.0, -1.0, 0.0))
        fwd_light = ref_dir - dir_strip * ref_dir.dot(dir_strip)
    fwd_light.normalize()

    if abs(fwd_light.z) < 0.5 and _is_under_cabinet(scene, depsgraph, p1, p2, dir_strip, fwd_light):
        down_dir = Vector((0.0, 0.0, -1.0)) - dir_strip * (-dir_strip.z)
        if down_dir.length > 1e-4:
            fwd_light = down_dir.normalized()

    base_mid = mid + _wall_clearance_offset(scene, depsgraph, p1, p2, dir_strip, fwd_light)

    # Garante que tanto o difusor quanto a AreaLight fiquem livres abaixo da chapa/tampo de MDF
    surface_shift = 0.0
    if depsgraph is not None:
        max_hit_shift = None
        for t_s in (0.25, 0.50, 0.75):
            pt = p1.lerp(p2, t_s) + (base_mid - mid)
            probe = pt + fwd_light * 0.03
            try:
                hit_back, loc_back, *_ = scene.ray_cast(depsgraph, probe, -fwd_light, distance=0.045)
            except Exception:
                hit_back = False
            if hit_back:
                proj = (loc_back - pt).dot(fwd_light)
                if max_hit_shift is None or proj > max_hit_shift:
                    max_hit_shift = proj
        if max_hit_shift is not None and max_hit_shift > -0.005:
            surface_shift = max_hit_shift

    light_offset = surface_shift + 0.015
    if depsgraph is not None:
        for cand_off in (light_offset, surface_shift + 0.022, surface_shift + 0.030):
            try:
                hit, *_ = scene.ray_cast(depsgraph, base_mid + fwd_light * cand_off, fwd_light, distance=0.035)
            except Exception:
                hit = False
            if not hit:
                light_offset = cand_off
                break

    ldata = bpy.data.lights.new(f"TrazoLED_{index+1}", type="AREA")
    ldata.shape = "RECTANGLE"
    ldata.size = max(length, 0.05)
    ldata.size_y = 0.025  # 25mm de abertura do difusor
    ldata.energy = power
    ldata.color = color
    if hasattr(ldata, "spread"):
        ldata.spread = math.radians(150.0)
    if hasattr(ldata, "use_shadow"):
        ldata.use_shadow = bool(lt.get("cast_shadow", True))
    if hasattr(ldata, "shadow_buffer_clip_start"):
        ldata.shadow_buffer_clip_start = 0.005
    if hasattr(ldata, "use_contact_shadows"):
        ldata.use_contact_shadows = True

    lobj = bpy.data.objects.new(ldata.name, ldata)
    scene.collection.objects.link(lobj)
    lobj.location = base_mid + fwd_light * light_offset

    # Orienta: -Z da luz alinhado com fwd_light, e eixo X da luz alinhado com a fita dir_strip
    z_axis = -fwd_light
    x_axis = dir_strip
    y_axis = z_axis.cross(x_axis)
    if y_axis.length < 1e-4:
        fallback = Vector((0.0, 1.0, 0.0)) if abs(z_axis.y) < 0.9 else Vector((1.0, 0.0, 0.0))
        y_axis = z_axis.cross(fallback)
    y_axis.normalize()
    x_axis = y_axis.cross(z_axis).normalized()
    mat_rot = Matrix((x_axis, y_axis, z_axis)).transposed().to_4x4()
    lobj.matrix_world = Matrix.Translation(lobj.location) @ mat_rot

    # Difusor visível emissivo (sem projetar sombra sobre a luz AREA)
    try:
        em_mesh = bpy.data.meshes.new(f"TrazoLED_Emitter_{index+1}_Mesh")
        bm = bmesh.new()
        half_l = length * 0.5
        half_w = 0.006
        v0 = bm.verts.new((-half_l, -half_w, 0.0))
        v1 = bm.verts.new((half_l, -half_w, 0.0))
        v2 = bm.verts.new((half_l, half_w, 0.0))
        v3 = bm.verts.new((-half_l, half_w, 0.0))
        bm.faces.new((v0, v1, v2, v3))
        bm.to_mesh(em_mesh)
        bm.free()

        em_mat = bpy.data.materials.new(f"TrazoLED_EmitterMat_{index+1}")
        em_mat.use_nodes = True
        nt = em_mat.node_tree
        nt.nodes.clear()
        out_node = nt.nodes.new("ShaderNodeOutputMaterial")
        emit_node = nt.nodes.new("ShaderNodeEmission")
        emit_node.inputs["Color"].default_value = (color[0], color[1], color[2], 1.0)
        emit_node.inputs["Strength"].default_value = max(
            3.0, min(25.0, power / (max(length, 0.25) * 12.0))
        )
        nt.links.new(emit_node.outputs["Emission"], out_node.inputs["Surface"])
        em_mesh.materials.append(em_mat)

        em_obj = bpy.data.objects.new(f"TrazoLED_Emitter_{index+1}", em_mesh)
        scene.collection.objects.link(em_obj)
        em_obj.matrix_world = Matrix.Translation(base_mid + fwd_light * (surface_shift + 0.004)) @ mat_rot
        if hasattr(em_obj, "visible_shadow"):
            em_obj.visible_shadow = False
    except Exception as exc:
        print(f"[TrazoMob] Aviso ao criar difusor emissivo LED: {exc}")


def _emissive_plane_basis(fwd_dir):
    """Retorna eixos ortonormais ``(u_axis, v_axis)`` perpendiculares a ``fwd_dir``."""
    ref = Vector((0.0, 0.0, 1.0)) if abs(fwd_dir.z) < 0.9 else Vector((0.0, 1.0, 0.0))
    u_axis = ref.cross(fwd_dir)
    if u_axis.length < 1e-4:
        u_axis = Vector((1.0, 0.0, 0.0))
    u_axis.normalize()
    v_axis = fwd_dir.cross(u_axis).normalized()
    return u_axis, v_axis


def _pick_emissive_direction(scene, depsgraph, mw, rot3, polys):
    """Escolhe a direção principal de emissão de um grupo de polígonos no mundo."""
    clusters = []
    for p in polys:
        area = float(getattr(p, "area", 0.0) or 0.0)
        if area <= 1e-8:
            continue
        n_world = rot3 @ Vector(p.normal)
        if n_world.length < 1e-6:
            continue
        n_world.normalize()
        ctr_world = mw @ Vector(p.center)
        matched = None
        for c in clusters:
            if c["normal"].dot(n_world) >= 0.85:
                matched = c
                break
        if matched is None:
            clusters.append({
                "normal": n_world.copy(),
                "area": area,
                "weighted_ctr": ctr_world * area,
                "polys": [p],
            })
        else:
            matched["area"] += area
            matched["weighted_ctr"] += ctr_world * area
            matched["normal"] = (matched["normal"] + n_world * area).normalized()
            matched["polys"].append(p)

    if not clusters:
        return None

    # Se houver múltiplas orientações (ex.: chapa ou luminária 3D), prioriza a face desobstruída e com maior área.
    best = None
    best_score = -1.0
    for c in clusters:
        ctr = c["weighted_ctr"] / max(c["area"], 1e-8)
        n = c["normal"]
        clear = True
        if depsgraph is not None and hasattr(scene, "ray_cast"):
            try:
                hit, *_ = scene.ray_cast(depsgraph, ctr + n * 0.008, n, distance=0.08)
                clear = not hit
            except Exception:
                clear = True
        score = c["area"] * (10.0 if clear else 1.0)
        if score > best_score:
            best_score = score
            best = c
    return best


def create_emissive_material_lights(scene, depsgraph=None):
    """Cria AreaLights suaves para materiais configurados como ``emissivo`` no Editor PBR.

    No EEVEE (com raytracing desligado para manter luz direta estável), meshes emissivas
    não iluminam o ambiente ao redor; no Cycles, telas escuras de TV com emissão preservada
    para não estourar a imagem contribuem pouca luz indireta. A AreaLight calibrada resolve
    ambos os motores mantendo a imagem original da superfície emissora intacta.
    """
    created = []
    objects = getattr(scene, "objects", ()) or ()
    idx = 0

    for obj in objects:
        if getattr(obj, "type", None) != "MESH" or getattr(obj, "data", None) is None:
            continue
        slots = list(getattr(obj, "material_slots", ()) or ())
        if not slots:
            continue
        polys_all = list(getattr(obj.data, "polygons", ()) or ())
        verts_all = getattr(obj.data, "vertices", None)
        if not polys_all or verts_all is None:
            continue

        mw = obj.matrix_world
        rot3 = mw.to_3x3()

        for slot_idx, slot in enumerate(slots):
            mat = getattr(slot, "material", None)
            if mat is None:
                continue
            em_kind = mat.get("trazomob_emissive_kind") if hasattr(mat, "get") else None
            if not em_kind:
                continue

            polys = [p for p in polys_all if getattr(p, "material_index", 0) == slot_idx]
            if not polys:
                continue

            chosen = _pick_emissive_direction(scene, depsgraph, mw, rot3, polys)
            if chosen is None:
                continue

            fwd_dir = chosen["normal"]
            u_axis, v_axis = _emissive_plane_basis(fwd_dir)
            front_polys = chosen["polys"]
            pts = [
                mw @ Vector(verts_all[v_idx].co)
                for p in front_polys
                for v_idx in getattr(p, "vertices", ())
            ]
            if not pts:
                continue

            u_vals = [pt.dot(u_axis) for pt in pts]
            v_vals = [pt.dot(v_axis) for pt in pts]
            w_vals = [pt.dot(fwd_dir) for pt in pts]

            u_mid = 0.5 * (min(u_vals) + max(u_vals))
            v_mid = 0.5 * (min(v_vals) + max(v_vals))
            w_front = max(w_vals)
            size_u = max(0.04, max(u_vals) - min(u_vals))
            size_v = max(0.04, max(v_vals) - min(v_vals))

            center_front = u_axis * u_mid + v_axis * v_mid + fwd_dir * w_front

            base_off = 0.045 if em_kind == "screen" else 0.025
            light_off = base_off
            if depsgraph is not None and hasattr(scene, "ray_cast"):
                for cand in (base_off, base_off * 0.5, base_off * 1.5):
                    try:
                        hit, *_ = scene.ray_cast(depsgraph, center_front + fwd_dir * cand, fwd_dir, distance=0.05)
                    except Exception:
                        hit = False
                    if not hit:
                        light_off = cand
                        break

            light_pos = center_front + fwd_dir * light_off
            raw_col = mat.get("trazomob_emissive_color") if hasattr(mat, "get") else None
            if raw_col and len(raw_col) >= 3:
                emit_col = (float(raw_col[0]), float(raw_col[1]), float(raw_col[2]))
            else:
                emit_col = (0.78, 0.88, 1.0) if em_kind == "screen" else (1.0, 0.95, 0.88)

            area_m2 = max(0.02, size_u * size_v)
            if em_kind == "screen":
                energy = max(14.0, min(48.0, area_m2 * 52.0))
                spread_deg = 155.0
            else:
                energy = max(25.0, min(180.0, max(size_u, size_v) * 45.0))
                spread_deg = 150.0

            idx += 1
            ldata = bpy.data.lights.new(f"TrazoEmissive_{idx}", type="AREA")
            ldata.shape = "RECTANGLE"
            ldata.size = size_u
            ldata.size_y = size_v
            ldata.energy = energy
            ldata.color = emit_col
            if hasattr(ldata, "spread"):
                ldata.spread = math.radians(spread_deg)
            if hasattr(ldata, "use_shadow"):
                ldata.use_shadow = True
            if hasattr(ldata, "shadow_buffer_clip_start"):
                ldata.shadow_buffer_clip_start = 0.02
            if hasattr(ldata, "use_contact_shadows"):
                ldata.use_contact_shadows = True

            lobj = bpy.data.objects.new(ldata.name, ldata)
            scene.collection.objects.link(lobj)

            z_axis = -fwd_dir
            mat_rot = Matrix((u_axis, v_axis, z_axis)).transposed().to_4x4()
            lobj.matrix_world = Matrix.Translation(light_pos) @ mat_rot
            for vis_attr in ("visible_camera", "visible_glossy", "visible_transmission"):
                if hasattr(lobj, vis_attr):
                    try:
                        setattr(lobj, vis_attr, False)
                    except Exception:
                        pass

            created.append({
                "on": True,
                "kind": "emissive_area",
                "pos": [float(light_pos.x), float(light_pos.y), float(light_pos.z)],
                "power": float(energy),
                "color": list(emit_col),
            })

    if created:
        say("emissive_lights", len(created))
    return created


def main():
    job = load_job()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    # 1. Importa Modelo GLB
    import_model(job["glb"])

    engine_name = job.get("engine", "cycles")
    use_bevel = (engine_name == "cycles")

    # 2. Configura Materiais Fotorrealistas de Marcenaria e Overrides
    material_overrides = job.get("materials") or {}
    clay_mode = bool(job.get("clay_mode", False))
    setup_photoreal_materials(use_bevel=use_bevel, material_overrides=material_overrides, clay_mode=clay_mode)

    # 3. Câmera Arquitetônica
    w, h = int(job.get("width", 1920)), int(job.get("height", 1080))
    correct_vert = bool(job.get("correct_verticals", True))
    set_architectural_camera(scene, job["camera"], w, h, correct_verticals=correct_vert)

    # 4. Iluminação e Ambiente
    preset = job.get("preset", "dia")
    sun_dir = job.get("sun")
    lights = job.get("lights") or []
    try:
        depsgraph = bpy.context.evaluated_depsgraph_get()
    except Exception:
        depsgraph = None

    # 4b. Gera AreaLights suaves para materiais PBR emissivos (ex.: Painel Iluminado / TV Ligada)
    emissive_lights = [] if clay_mode else create_emissive_material_lights(scene, depsgraph)

    confinement = measure_room_confinement(scene, depsgraph, job["camera"], sun_dir=sun_dir)
    say(
        "confinement",
        f"enclosed={confinement['enclosed']}",
        f"ceiling={confinement['has_ceiling']}",
        f"sky_open={confinement['sky_open_ratio']:.2f}",
        f"sky_exp={confinement['sky_exposure']:.2f}",
        f"sun_vis={confinement['sun_visibility']:.2f}",
    )

    probe_pts = _room_probe_points(scene, depsgraph, job["camera"])
    interior_lights = []
    for lt in list(lights) + emissive_lights:
        if not lt.get("on", True):
            continue
        if lt.get("kind") == "led_strip" and "p1" in lt and "p2" in lt:
            mid_pt = (Vector(lt["p1"]) + Vector(lt["p2"])) * 0.5 + Vector(lt.get("dir", (0.0, 0.0, -1.0))) * 0.03
            pt_ref = mid_pt
        else:
            pt_ref = Vector(lt.get("pos", (0.0, 0.0, 1.0)))
        if any(not _segment_blocked_by_opaque(scene, depsgraph, pt_ref, p_in) for p_in in probe_pts):
            interior_lights.append(lt)

    scene["sun_softness"] = float(job.get("sun_softness", 2.5))
    apply_lighting_preset(
        scene,
        preset_name=preset,
        sun_dir=sun_dir,
        engine=engine_name,
        confinement=confinement,
        interior_lights=interior_lights,
    )

    # 5. Adiciona Luzes Pontuais / Spots / Fitas LED enviadas pelo usuário
    for i, lt in enumerate(lights):
        raw_kind = lt.get("kind", "point")
        color = tuple(lt.get("color", (1.0, 0.9, 0.8)))
        power = float(lt.get("power", 400.0))

        if raw_kind == "led_strip" and "p1" in lt and "p2" in lt:
            _create_led_strip_light(scene, depsgraph, i, lt, color, power)
            continue

        kind = "SPOT" if raw_kind == "spot" else "POINT"
        ldata = bpy.data.lights.new(f"TrazoLight_{i+1}", type=kind)
        ldata.energy = power
        ldata.color = color
        if hasattr(ldata, "use_shadow"):
            ldata.use_shadow = True
        if hasattr(ldata, "shadow_buffer_clip_start"):
            ldata.shadow_buffer_clip_start = 0.005
        if hasattr(ldata, "use_contact_shadows"):
            ldata.use_contact_shadows = True
        if hasattr(ldata, "shadow_soft_size"):
            ldata.shadow_soft_size = 0.08  # Lâmpada física com sombra realista
        if kind == "SPOT":
            spot_ang = math.radians(float(lt.get("angle", 60.0)))
            ldata.spot_size = spot_ang
            # Suavidade de borda / Falloff
            ldata.spot_blend = float(lt.get("blend", 0.35))

            # Suporte a Perfil IES Real (Fotometria do Fabricante)
            ies_path = lt.get("ies_path")
            if not ies_path:
                name_cand = lt.get("name", "")
                if name_cand.lower().endswith(".ies"):
                    ies_path = name_cand
            if ies_path and os.path.exists(ies_path):
                try:
                    ldata.use_nodes = True
                    l_nodes = ldata.node_tree.nodes
                    l_links = ldata.node_tree.links
                    l_nodes.clear()
                    node_out = l_nodes.new("ShaderNodeOutputLight")
                    node_emit = l_nodes.new("ShaderNodeEmission")
                    node_emit.inputs["Color"].default_value = (color[0], color[1], color[2], 1.0)
                    node_emit.inputs["Strength"].default_value = power
                    node_ies = l_nodes.new("ShaderNodeTexIES")
                    node_ies.mode = "EXTERNAL"
                    node_ies.filepath = ies_path
                    l_links.new(node_ies.outputs["Fac"], node_emit.inputs["Strength"])
                    l_links.new(node_emit.outputs["Emission"], node_out.inputs["Surface"])
                    say("ies_loaded", ies_path)
                except Exception as e:
                    say("ies_error", str(e))

        lobj = bpy.data.objects.new(ldata.name, ldata)
        scene.collection.objects.link(lobj)
        lobj.location = Vector(lt.get("pos", (0, 0, 1)))

        # Se for Spot, orienta o cone de luz na direção do alvo/mira (target ou dir)
        if kind == "SPOT":
            if "target" in lt:
                t_pos = Vector(lt["target"])
                d = (t_pos - lobj.location).normalized()
            elif "dir" in lt:
                d = Vector(lt["dir"]).normalized()
            else:
                d = Vector((0.0, 0.0, -1.0))
            if d.length > 1e-4:
                lobj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


    # 6. Motor de Render e Qualidade
    samples = int(job.get("samples", 128))
    setup_render_engine(scene, engine=engine_name, samples=samples)

    # 7. Color Management Profissional (AgX / Filmic High Contrast)
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = job["output"]

    view = scene.view_settings
    view.exposure = float(job.get("exposure", 0.0))
    for look in ("AgX - Medium High Contrast", "AgX - High Contrast", "Medium High Contrast", "Punchy"):
        try:
            view.look = look
            break
        except Exception:
            pass

    # Salva o arquivo .blend completo para inspeção direta se solicitado
    blend_path = job.get("blend_file")
    if blend_path:
        try:
            bpy.ops.wm.save_as_mainfile(filepath=blend_path)
            say("saved_blend", blend_path)
        except Exception:
            pass

    if job.get("prepare_only"):
        say("done", blend_path or "")
        return

    say("rendering", f"{w}x{h}", engine_name, f"samples={samples}")

    def on_render_stats(stats_str):
        say("STATS", stats_str)

    bpy.app.handlers.render_stats.append(on_render_stats)
    try:
        bpy.ops.render.render(write_still=True)
    finally:
        if on_render_stats in bpy.app.handlers.render_stats:
            bpy.app.handlers.render_stats.remove(on_render_stats)

    say("done", job["output"])


if __name__ == "__main__":
    main()
