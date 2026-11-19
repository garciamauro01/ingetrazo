# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Aplicador de presets procedurais de render no Blender (sem texturas externas)."""
from __future__ import annotations


def apply_render_preset(mat, preset_id: str, obj=None) -> None:
    """Configura os nós do material ``mat`` no Blender para o ``preset_id`` escolhido."""
    import bpy

    if not mat or preset_id in ("", "original"):
        return

    if not mat.use_nodes:
        mat.use_nodes = True
    nt = mat.node_tree

    # Preserva textura de imagem existente caso o preset seja tapete felpudo sobre estampa
    existing_tex = next((n for n in nt.nodes if n.type == "TEX_IMAGE" and n.image is not None), None)
    existing_img = existing_tex.image if existing_tex else None

    if preset_id == "carpete_felpudo":
        if obj is not None and obj.type == "MESH" and not any(m.type == "PARTICLE_SYSTEM" for m in obj.modifiers):
            obj.modifiers.new("Carpete_Fios", "PARTICLE_SYSTEM")
            ps = obj.particle_systems[-1].settings
            ps.type = "HAIR"
            ps.count = 20000
            ps.hair_length = 0.018
            ps.hair_step = 3
            ps.root_radius = 0.003
            ps.tip_radius = 0.0015
            ps.use_advanced_hair = True
            ps.brownian_factor = 0.025
            ps.child_type = "SIMPLE"
            ps.rendered_child_count = 8
            ps.child_radius = 0.009
            ps.clump_factor = 0.20

        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.inputs["Roughness"].default_value = 0.88
        if existing_img is not None:
            tex = nt.nodes.new("ShaderNodeTexImage")
            tex.image = existing_img
            gamma = nt.nodes.new("ShaderNodeGamma")
            gamma.inputs["Gamma"].default_value = 1.35
            nt.links.new(tex.outputs["Color"], gamma.inputs["Color"])
            nt.links.new(gamma.outputs["Color"], bsdf.inputs["Base Color"])
        else:
            bsdf.inputs["Base Color"].default_value = (0.35, 0.35, 0.38, 1.0)
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        return

    if preset_id == "grama_3d":
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.inputs["Roughness"].default_value = 0.50
        if "Subsurface Weight" in bsdf.inputs:
            bsdf.inputs["Subsurface Weight"].default_value = 0.20
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 25.0
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (0.04, 0.14, 0.02, 1.0)
        ramp.color_ramp.elements[1].color = (0.14, 0.32, 0.04, 1.0)
        nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        return

    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")

    if preset_id in ("aco_escovado", "dourado_escovado"):
        bsdf.inputs["Base Color"].default_value = (
            (0.83, 0.65, 0.28, 1.0) if preset_id == "dourado_escovado" else (0.68, 0.70, 0.72, 1.0)
        )
        bsdf.inputs["Metallic"].default_value = 1.0
        if "Anisotropic" in bsdf.inputs:
            bsdf.inputs["Anisotropic"].default_value = 0.65
        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (4.0, 4.0, 140.0)
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 12.0
        noise.inputs["Detail"].default_value = 8.0
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (0.18, 0.18, 0.18, 1.0)
        ramp.color_ramp.elements[1].color = (0.30, 0.30, 0.30, 1.0)
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.025
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], noise.inputs["Vector"])
        nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Roughness"])
        nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    elif preset_id in ("cromado", "espelho"):
        bsdf.inputs["Base Color"].default_value = (0.92, 0.94, 0.96, 1.0)
        bsdf.inputs["Metallic"].default_value = 1.0
        bsdf.inputs["Roughness"].default_value = 0.01 if preset_id == "espelho" else 0.04

    elif preset_id == "preto_fosco_metal":
        bsdf.inputs["Base Color"].default_value = (0.04, 0.04, 0.045, 1.0)
        bsdf.inputs["Metallic"].default_value = 0.85
        bsdf.inputs["Roughness"].default_value = 0.42

    elif preset_id == "branco_esmaltado":
        bsdf.inputs["Base Color"].default_value = (0.95, 0.95, 0.96, 1.0)
        bsdf.inputs["Metallic"].default_value = 0.0
        bsdf.inputs["Roughness"].default_value = 0.07
        if "Coat Weight" in bsdf.inputs:
            bsdf.inputs["Coat Weight"].default_value = 1.0
            bsdf.inputs["Coat Roughness"].default_value = 0.02

    elif preset_id == "black_piano":
        bsdf.inputs["Base Color"].default_value = (0.01, 0.01, 0.012, 1.0)
        bsdf.inputs["Metallic"].default_value = 0.0
        bsdf.inputs["Roughness"].default_value = 0.05
        if "Coat Weight" in bsdf.inputs:
            bsdf.inputs["Coat Weight"].default_value = 1.0
            bsdf.inputs["Coat Roughness"].default_value = 0.02

    elif preset_id == "pintura_automotiva":
        bsdf.inputs["Metallic"].default_value = 0.85
        bsdf.inputs["Roughness"].default_value = 0.24
        if "Coat Weight" in bsdf.inputs:
            bsdf.inputs["Coat Weight"].default_value = 1.0
            bsdf.inputs["Coat Roughness"].default_value = 0.03
        lw = nt.nodes.new("ShaderNodeLayerWeight")
        lw.inputs["Blend"].default_value = 0.35
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (0.015, 0.12, 0.45, 1.0)
        ramp.color_ramp.elements[1].color = (0.06, 0.38, 0.82, 1.0)
        nt.links.new(lw.outputs["Facing"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

    elif preset_id in ("vidro_incolor", "vidro_fume", "vidro_jateado"):
        bsdf.inputs["Base Color"].default_value = (
            (0.10, 0.12, 0.15, 1.0) if preset_id == "vidro_fume" else (0.94, 0.97, 0.98, 1.0)
        )
        bsdf.inputs["Roughness"].default_value = 0.28 if preset_id == "vidro_jateado" else 0.02
        bsdf.inputs["IOR"].default_value = 1.52
        if "Transmission Weight" in bsdf.inputs:
            bsdf.inputs["Transmission Weight"].default_value = 0.88

    elif preset_id == "borracha_fosca":
        bsdf.inputs["Base Color"].default_value = (0.04, 0.04, 0.045, 1.0)
        bsdf.inputs["Metallic"].default_value = 0.0
        bsdf.inputs["Roughness"].default_value = 0.78

    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
