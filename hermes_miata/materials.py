"""
materials.py — hyper-realistic procedural PBR materials for the Hermes Miata.

Every material is fully procedural (no image textures required) and built on
the Principled BSDF via the version-proof socket helpers in utils.py.

Material recipes match the reference images:
  * Deep metallic British Racing Green w/ pearlescent flake, clearcoat,
    orange-peel normal, faint swirl micro-scratches   (Image 1)
  * Dark gunmetal anodized metal w/ brushed anisotropy (Image 5 Sony panel)
  * Blue Alcantara w/ velvet sheen + SSS               (Image 3 interior)
  * NITTO-style tyre rubber + white sidewall lettering (Image 1 wheels)
  * E-ink pixel display shader                         (Image 4 panel)
"""

import bpy
import math
from . import utils
from .utils import new_node_material, set_inputs, PREFIX

# Cache so repeated builds re-use datablocks instead of piling up .001s
_cache = {}


def get(name, builder):
    key = f"{PREFIX}_{name}"
    if key in _cache and _cache[key].name in bpy.data.materials.keys():
        return _cache[key]
    existing = bpy.data.materials.get(key)
    if existing:
        _cache[key] = existing
        return existing
    mat = builder(name)
    _cache[key] = mat
    return mat


# ---------------------------------------------------------------------------
# Exterior
# ---------------------------------------------------------------------------

def car_paint():
    """Deep metallic British Racing Green.

    Layered look:
      base coat  – dark green, metallic, with a Voronoi-driven flake layer
                   whose normals randomise per-cell for the sparkle shift
      pearl      – slight hue shift with viewing angle via Layer Weight
      clear coat – Principled 'Coat' with an orange-peel noise normal
      wear       – very faint radial swirl marks modulating coat roughness
    """
    def build(name):
        mat, nodes, links, p, out = new_node_material(name)

        # --- base colour with facing-angle pearl shift -------------------
        layer_w = nodes.new('ShaderNodeLayerWeight'); layer_w.location = (-900, 300)
        layer_w.inputs['Blend'].default_value = 0.35
        ramp = nodes.new('ShaderNodeValToRGB'); ramp.location = (-700, 300)
        # facing: deep BRG  ->  grazing: slightly teal/blue pearl
        ramp.color_ramp.elements[0].color = (0.012, 0.075, 0.032, 1)
        ramp.color_ramp.elements[1].color = (0.020, 0.105, 0.085, 1)
        links.new(layer_w.outputs['Facing'], ramp.inputs['Fac'])

        # --- metallic flakes ---------------------------------------------
        tex_co = nodes.new('ShaderNodeTexCoord'); tex_co.location = (-1300, 0)
        flake_vor = nodes.new('ShaderNodeTexVoronoi'); flake_vor.location = (-1100, 0)
        flake_vor.feature = 'F1'
        flake_vor.inputs['Scale'].default_value = 9000.0   # micro flakes
        links.new(tex_co.outputs['Object'], flake_vor.inputs['Vector'])
        # per-flake random brightness, gated so only ~15% of cells sparkle
        flake_gate = nodes.new('ShaderNodeMath'); flake_gate.location = (-900, 0)
        flake_gate.operation = 'GREATER_THAN'
        flake_gate.inputs[1].default_value = 0.85
        links.new(flake_vor.outputs['Color'], flake_gate.inputs[0])
        flake_mix = nodes.new('ShaderNodeMixRGB'); flake_mix.location = (-500, 200)
        flake_mix.blend_type = 'ADD'
        flake_mix.inputs['Color2'].default_value = (0.20, 0.45, 0.30, 1)
        links.new(ramp.outputs['Color'], flake_mix.inputs['Color1'])
        links.new(flake_gate.outputs[0], flake_mix.inputs['Fac'])
        links.new(flake_mix.outputs['Color'], p.inputs['Base Color'])

        # flakes also perturb the normal a touch -> glittery normal jitter
        flake_bump = nodes.new('ShaderNodeBump'); flake_bump.location = (-500, -250)
        flake_bump.inputs['Strength'].default_value = 0.08
        flake_bump.inputs['Distance'].default_value = 0.0003
        links.new(flake_vor.outputs['Distance'], flake_bump.inputs['Height'])

        # --- orange peel on the clear coat --------------------------------
        peel = nodes.new('ShaderNodeTexNoise'); peel.location = (-900, -500)
        peel.inputs['Scale'].default_value = 450.0
        peel.inputs['Detail'].default_value = 2.0
        peel.inputs['Roughness'].default_value = 0.45
        links.new(tex_co.outputs['Object'], peel.inputs['Vector'])
        peel_bump = nodes.new('ShaderNodeBump'); peel_bump.location = (-300, -450)
        peel_bump.inputs['Strength'].default_value = 0.05
        peel_bump.inputs['Distance'].default_value = 0.0008
        links.new(peel.outputs['Fac'], peel_bump.inputs['Height'])
        links.new(flake_bump.outputs['Normal'], peel_bump.inputs['Normal'])
        links.new(peel_bump.outputs['Normal'], p.inputs['Normal'])

        # --- faint swirl marks: stretched noise modulating coat roughness --
        swirl = nodes.new('ShaderNodeTexNoise'); swirl.location = (-900, -750)
        swirl.inputs['Scale'].default_value = 60.0
        swirl.inputs['Detail'].default_value = 6.0
        swirl_map = nodes.new('ShaderNodeMapping'); swirl_map.location = (-1100, -750)
        swirl_map.inputs['Scale'].default_value = (1.0, 30.0, 1.0)  # streaky
        links.new(tex_co.outputs['Object'], swirl_map.inputs['Vector'])
        links.new(swirl_map.outputs['Vector'], swirl.inputs['Vector'])
        swirl_rng = nodes.new('ShaderNodeMapRange'); swirl_rng.location = (-700, -750)
        swirl_rng.inputs['To Min'].default_value = 0.03   # coat rough min
        swirl_rng.inputs['To Max'].default_value = 0.10   # swirl-mark max
        links.new(swirl.outputs['Fac'], swirl_rng.inputs['Value'])
        coat_r = utils.find_input(p, "coat_rough")
        if coat_r:
            links.new(swirl_rng.outputs['Result'], coat_r)

        set_inputs(p, metallic=1.0, roughness=0.32, coat=1.0, specular=0.6)
        return mat
    return get("CarPaint_BRG", lambda n: build(n))


def carbon_fiber():
    """2x2 twill carbon: procedural checker weave under a glossy coat."""
    def build(name):
        mat, nodes, links, p, out = new_node_material(name)
        tex_co = nodes.new('ShaderNodeTexCoord')
        mapping = nodes.new('ShaderNodeMapping')
        mapping.inputs['Scale'].default_value = (300, 300, 300)
        links.new(tex_co.outputs['Object'], mapping.inputs['Vector'])
        # two perpendicular wave textures -> twill-ish interleave
        wave1 = nodes.new('ShaderNodeTexWave')
        wave1.inputs['Scale'].default_value = 2.0
        wave1.inputs['Distortion'].default_value = 0.0
        wave1.bands_direction = 'X'
        wave2 = nodes.new('ShaderNodeTexWave')
        wave2.inputs['Scale'].default_value = 2.0
        wave2.bands_direction = 'Y'
        links.new(mapping.outputs['Vector'], wave1.inputs['Vector'])
        links.new(mapping.outputs['Vector'], wave2.inputs['Vector'])
        weave = nodes.new('ShaderNodeMath'); weave.operation = 'MULTIPLY'
        links.new(wave1.outputs['Fac'], weave.inputs[0])
        links.new(wave2.outputs['Fac'], weave.inputs[1])
        ramp = nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].color = (0.008, 0.008, 0.010, 1)
        ramp.color_ramp.elements[1].color = (0.060, 0.060, 0.065, 1)
        links.new(weave.outputs[0], ramp.inputs['Fac'])
        links.new(ramp.outputs['Color'], p.inputs['Base Color'])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = 0.15
        links.new(weave.outputs[0], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], p.inputs['Normal'])
        set_inputs(p, metallic=0.3, roughness=0.18, coat=1.0, coat_rough=0.05,
                   anisotropic=0.6)
        return mat
    return get("CarbonFiber", build)


def chrome():
    def build(name):
        mat, nodes, links, p, out = new_node_material(name)
        set_inputs(p, base_color=(0.95, 0.95, 0.97), metallic=1.0,
                   roughness=0.04)
        return mat
    return get("Chrome", build)


def glass(tint=(0.35, 0.42, 0.40), name="Glass"):
    """Window glass: transmission, proper IOR, very light green tint."""
    def build(n):
        mat, nodes, links, p, out = new_node_material(n)
        set_inputs(p, base_color=tint, roughness=0.0, transmission=1.0,
                   ior=1.45, alpha=1.0)
        # Eevee fallback friendliness
        if hasattr(mat, "blend_method"):
            mat.blend_method = 'BLEND'
        return mat
    return get(name, build)


def soft_top_fabric():
    """Matte black canvas: tight weave bump + low-freq wrinkle noise."""
    def build(name):
        mat, nodes, links, p, out = new_node_material(name)
        tex_co = nodes.new('ShaderNodeTexCoord')
        # fine weave
        weave = nodes.new('ShaderNodeTexWave')
        weave.inputs['Scale'].default_value = 900.0
        weave.inputs['Distortion'].default_value = 1.5
        links.new(tex_co.outputs['Object'], weave.inputs['Vector'])
        # broad wrinkles / tension folds
        wrinkle = nodes.new('ShaderNodeTexNoise')
        wrinkle.inputs['Scale'].default_value = 6.0
        wrinkle.inputs['Detail'].default_value = 4.0
        links.new(tex_co.outputs['Object'], wrinkle.inputs['Vector'])
        add = nodes.new('ShaderNodeMath'); add.operation = 'ADD'
        links.new(weave.outputs['Fac'], add.inputs[0])
        links.new(wrinkle.outputs['Fac'], add.inputs[1])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = 0.35
        bump.inputs['Distance'].default_value = 0.002
        links.new(add.outputs[0], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], p.inputs['Normal'])
        set_inputs(p, base_color=(0.012, 0.012, 0.012), metallic=0.0,
                   roughness=0.85, sheen=0.4, specular=0.2)
        return mat
    return get("SoftTopCanvas", build)


def tire_rubber():
    """Semi-slick rubber: matte, fine radial tread bump near the contact band."""
    def build(name):
        mat, nodes, links, p, out = new_node_material(name)
        tex_co = nodes.new('ShaderNodeTexCoord')
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 150.0
        noise.inputs['Detail'].default_value = 8.0
        links.new(tex_co.outputs['Object'], noise.inputs['Vector'])
        # subtle circumferential grooves
        wave = nodes.new('ShaderNodeTexWave')
        wave.inputs['Scale'].default_value = 40.0
        wave.bands_direction = 'Z'
        links.new(tex_co.outputs['Object'], wave.inputs['Vector'])
        add = nodes.new('ShaderNodeMath'); add.operation = 'ADD'
        add.inputs[1].default_value = 0.0
        links.new(noise.outputs['Fac'], add.inputs[0])
        links.new(wave.outputs['Fac'], add.inputs[1])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = 0.4
        bump.inputs['Distance'].default_value = 0.0015
        links.new(add.outputs[0], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], p.inputs['Normal'])
        set_inputs(p, base_color=(0.015, 0.015, 0.015), metallic=0.0,
                   roughness=0.75, specular=0.3, sheen=0.1)
        return mat
    return get("TireRubber", build)


def white_lettering():
    """Slightly rough warm white for the raised NITTO sidewall letters."""
    def build(name):
        mat, nodes, links, p, out = new_node_material(name)
        set_inputs(p, base_color=(0.85, 0.84, 0.80), roughness=0.6)
        return mat
    return get("TireLettering", build)


def wheel_bronze():
    """Dark bronze wheel faces with a satin metallic finish."""
    def build(name):
        mat, nodes, links, p, out = new_node_material(name)
        set_inputs(p, base_color=(0.18, 0.11, 0.05), metallic=1.0,
                   roughness=0.35, coat=0.5, coat_rough=0.15)
        return mat
    return get("WheelBronze", build)


def polished_lip():
    def build(name):
        mat, nodes, links, p, out = new_node_material(name)
        set_inputs(p, base_color=(0.85, 0.85, 0.88), metallic=1.0,
                   roughness=0.08, anisotropic=0.8)
        return mat
    return get("PolishedLip", build)


def brake_metal():
    def build(name):
        mat, nodes, links, p, out = new_node_material(name)
        set_inputs(p, base_color=(0.35, 0.35, 0.36), metallic=1.0,
                   roughness=0.45, anisotropic=0.9)
        return mat
    return get("BrakeDisc", build)


# ---------------------------------------------------------------------------
# Lights
# ---------------------------------------------------------------------------

def _emissive(name, color, strength):
    """Emissive lamp material. The emission STRENGTH lives on a Value node
    named 'LightDriver' so animation.py can keyframe one scalar per lamp."""
    def build(n):
        mat, nodes, links, p, out = new_node_material(n)
        nodes.remove(p)
        em = nodes.new('ShaderNodeEmission'); em.location = (-200, 0)
        em.inputs['Color'].default_value = (*color, 1.0)
        val = nodes.new('ShaderNodeValue'); val.location = (-400, -100)
        val.name = val.label = "LightDriver"
        val.outputs[0].default_value = strength
        links.new(val.outputs[0], em.inputs['Strength'])
        links.new(em.outputs['Emission'], out.inputs['Surface'])
        return mat
    return get(name, build)


def headlight_led():
    return _emissive("HeadlightLED", (0.85, 0.9, 1.0), 0.0)   # off by default

def taillight_red():
    return _emissive("TaillightRed", (1.0, 0.02, 0.01), 0.0)

def blinker_amber():
    return _emissive("BlinkerAmber", (1.0, 0.45, 0.02), 0.0)

def taillight_lens():
    """Dark red translucent lens over the emitters."""
    def build(name):
        mat, nodes, links, p, out = new_node_material(name)
        set_inputs(p, base_color=(0.35, 0.01, 0.01), roughness=0.05,
                   transmission=0.9, ior=1.49)
        return mat
    return get("TaillightLens", build)

def headlight_housing():
    def build(name):
        mat, nodes, links, p, out = new_node_material(name)
        set_inputs(p, base_color=(0.02, 0.02, 0.02), metallic=0.8,
                   roughness=0.2)
        return mat
    return get("HeadlightHousing", build)


# ---------------------------------------------------------------------------
# Interior
# ---------------------------------------------------------------------------

def anodized_metal(name="AnodizedGunmetal", tint=(0.16, 0.18, 0.22)):
    """Brushed dark-gunmetal anodized aluminium (Sony panel, Image 5).

    metallic 0.9, roughness ~0.18, strong anisotropy aligned with a streaky
    noise 'brush' normal, plus a faint large-scale noise standing in for
    fingerprints/smudge on the roughness channel.
    """
    def build(n):
        mat, nodes, links, p, out = new_node_material(n)
        tex_co = nodes.new('ShaderNodeTexCoord')
        # brushing: noise squashed into long streaks
        mapping = nodes.new('ShaderNodeMapping')
        mapping.inputs['Scale'].default_value = (1.0, 800.0, 1.0)
        links.new(tex_co.outputs['Object'], mapping.inputs['Vector'])
        brush = nodes.new('ShaderNodeTexNoise')
        brush.inputs['Scale'].default_value = 8.0
        brush.inputs['Detail'].default_value = 8.0
        links.new(mapping.outputs['Vector'], brush.inputs['Vector'])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = 0.06
        bump.inputs['Distance'].default_value = 0.0002
        links.new(brush.outputs['Fac'], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], p.inputs['Normal'])
        # fingerprint smudges -> roughness variation 0.12..0.25
        smudge = nodes.new('ShaderNodeTexNoise')
        smudge.inputs['Scale'].default_value = 25.0
        smudge.inputs['Detail'].default_value = 3.0
        links.new(tex_co.outputs['Object'], smudge.inputs['Vector'])
        rng = nodes.new('ShaderNodeMapRange')
        rng.inputs['To Min'].default_value = 0.12
        rng.inputs['To Max'].default_value = 0.25
        links.new(smudge.outputs['Fac'], rng.inputs['Value'])
        links.new(rng.outputs['Result'], p.inputs['Roughness'])
        set_inputs(p, base_color=tint, metallic=0.92, anisotropic=0.85,
                   anisotropic_rotation=0.0)
        return mat
    return get(name, lambda n: build(n))


def anodized_black():
    return anodized_metal("AnodizedBlack", tint=(0.03, 0.03, 0.035))


def orange_accent():
    """Anodized orange for accent switches (Image 5's orange toggles)."""
    def build(name):
        mat, nodes, links, p, out = new_node_material(name)
        set_inputs(p, base_color=(0.85, 0.25, 0.02), metallic=0.9,
                   roughness=0.25, anisotropic=0.5)
        return mat
    return get("AnodizedOrange", build)


def alcantara(name="AlcantaraBlue", color=(0.030, 0.055, 0.160)):
    """Blue Alcantara: velvet sheen, dense micro-noise nap, subtle SSS."""
    def build(n):
        mat, nodes, links, p, out = new_node_material(n)
        tex_co = nodes.new('ShaderNodeTexCoord')
        nap = nodes.new('ShaderNodeTexNoise')
        nap.inputs['Scale'].default_value = 1200.0
        nap.inputs['Detail'].default_value = 3.0
        links.new(tex_co.outputs['Object'], nap.inputs['Vector'])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = 0.25
        bump.inputs['Distance'].default_value = 0.0004
        links.new(nap.outputs['Fac'], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], p.inputs['Normal'])
        # slight value variation so the nap "catches light" in patches
        patch = nodes.new('ShaderNodeTexNoise')
        patch.inputs['Scale'].default_value = 40.0
        links.new(tex_co.outputs['Object'], patch.inputs['Vector'])
        mix = nodes.new('ShaderNodeMixRGB'); mix.blend_type = 'MULTIPLY'
        mix.inputs['Fac'].default_value = 0.25
        mix.inputs['Color1'].default_value = (*color, 1.0)
        links.new(patch.outputs['Color'], mix.inputs['Color2'])
        links.new(mix.outputs['Color'], p.inputs['Base Color'])
        set_inputs(p, roughness=0.9, sheen=1.0, sheen_rough=0.3,
                   sss=0.05, specular=0.15)
        return mat
    return get(name, lambda n: build(n))


def leather(name="LeatherBlack", color=(0.018, 0.018, 0.020)):
    """Black leather with pebble-grain bump and a hint of SSS/gloss."""
    def build(n):
        mat, nodes, links, p, out = new_node_material(n)
        tex_co = nodes.new('ShaderNodeTexCoord')
        grain = nodes.new('ShaderNodeTexVoronoi')
        grain.inputs['Scale'].default_value = 600.0
        links.new(tex_co.outputs['Object'], grain.inputs['Vector'])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = 0.3
        bump.inputs['Distance'].default_value = 0.0006
        links.new(grain.outputs['Distance'], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], p.inputs['Normal'])
        set_inputs(p, base_color=color, roughness=0.45, sss=0.04,
                   coat=0.15, coat_rough=0.3, specular=0.4)
        return mat
    return get(name, lambda n: build(n))


def stitching_white():
    def build(name):
        mat, nodes, links, p, out = new_node_material(name)
        set_inputs(p, base_color=(0.8, 0.8, 0.75), roughness=0.7, sheen=0.5)
        return mat
    return get("StitchWhite", build)


def eink_display():
    """Retro-futuristic E-ink / pixel gauge shader (Image 4).

    Pixel grid via snapped coordinates feeding noise -> hard-stepped two-tone
    palette (paper-white / ink-black) with a slow horizontal scanline shimmer.
    The 'DisplayDriver' value node lets animation.py flicker content.
    """
    def build(name):
        mat, nodes, links, p, out = new_node_material(name)
        nodes.remove(p)
        tex_co = nodes.new('ShaderNodeTexCoord')

        # snap UVs into a coarse pixel grid
        snap_scale = nodes.new('ShaderNodeVectorMath'); snap_scale.operation = 'MULTIPLY'
        snap_scale.inputs[1].default_value = (90.0, 32.0, 1.0)   # px count
        links.new(tex_co.outputs['UV'], snap_scale.inputs[0])
        snap = nodes.new('ShaderNodeVectorMath'); snap.operation = 'FLOOR'
        links.new(snap_scale.outputs[0], snap.inputs[0])

        # animatable phase
        phase = nodes.new('ShaderNodeValue')
        phase.name = phase.label = "DisplayDriver"
        phase.outputs[0].default_value = 0.0
        offset = nodes.new('ShaderNodeVectorMath'); offset.operation = 'ADD'
        combine = nodes.new('ShaderNodeCombineXYZ')
        links.new(phase.outputs[0], combine.inputs['X'])
        links.new(snap.outputs[0], offset.inputs[0])
        links.new(combine.outputs[0], offset.inputs[1])

        # pseudo "content": white noise per pixel cell, hard threshold
        cells = nodes.new('ShaderNodeTexWhiteNoise')
        cells.noise_dimensions = '3D'
        links.new(offset.outputs[0], cells.inputs['Vector'])
        step = nodes.new('ShaderNodeMath'); step.operation = 'GREATER_THAN'
        step.inputs[1].default_value = 0.55
        links.new(cells.outputs['Value'], step.inputs[0])

        # two-tone palette: warm paper white vs ink black
        pal = nodes.new('ShaderNodeMixRGB')
        pal.inputs['Color1'].default_value = (0.02, 0.02, 0.025, 1)  # ink
        pal.inputs['Color2'].default_value = (0.75, 0.74, 0.70, 1)   # paper
        links.new(step.outputs[0], pal.inputs['Fac'])

        # scanline darkening stripes
        sep = nodes.new('ShaderNodeSeparateXYZ')
        links.new(tex_co.outputs['UV'], sep.inputs[0])
        scan = nodes.new('ShaderNodeMath'); scan.operation = 'MULTIPLY'
        scan.inputs[1].default_value = 200.0
        links.new(sep.outputs['Y'], scan.inputs[0])
        scan_sin = nodes.new('ShaderNodeMath'); scan_sin.operation = 'SINE'
        links.new(scan.outputs[0], scan_sin.inputs[0])
        scan_rng = nodes.new('ShaderNodeMapRange')
        scan_rng.inputs['From Min'].default_value = -1.0
        scan_rng.inputs['To Min'].default_value = 0.85
        scan_rng.inputs['To Max'].default_value = 1.0
        links.new(scan_sin.outputs[0], scan_rng.inputs['Value'])
        dark = nodes.new('ShaderNodeMixRGB'); dark.blend_type = 'MULTIPLY'
        dark.inputs['Fac'].default_value = 1.0
        links.new(pal.outputs['Color'], dark.inputs['Color1'])
        links.new(scan_rng.outputs['Result'], dark.inputs['Color2'])

        em = nodes.new('ShaderNodeEmission')
        em.inputs['Strength'].default_value = 1.6   # soft glow, e-ink-ish
        links.new(dark.outputs['Color'], em.inputs['Color'])
        links.new(em.outputs['Emission'], out.inputs['Surface'])
        return mat
    return get("EInkDisplay", build)


# ---------------------------------------------------------------------------
# Scene / FX
# ---------------------------------------------------------------------------

def asphalt():
    """Parking-lot asphalt: dark grey aggregate, oily patches, coarse bump."""
    def build(name):
        mat, nodes, links, p, out = new_node_material(name)
        tex_co = nodes.new('ShaderNodeTexCoord')
        agg = nodes.new('ShaderNodeTexVoronoi')
        agg.inputs['Scale'].default_value = 250.0
        links.new(tex_co.outputs['Object'], agg.inputs['Vector'])
        big = nodes.new('ShaderNodeTexNoise')
        big.inputs['Scale'].default_value = 0.8
        big.inputs['Detail'].default_value = 6.0
        links.new(tex_co.outputs['Object'], big.inputs['Vector'])
        mix = nodes.new('ShaderNodeMixRGB'); mix.blend_type = 'MULTIPLY'
        mix.inputs['Fac'].default_value = 0.6
        mix.inputs['Color1'].default_value = (0.045, 0.045, 0.048, 1)
        links.new(big.outputs['Color'], mix.inputs['Color2'])
        links.new(mix.outputs['Color'], p.inputs['Base Color'])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = 0.5
        bump.inputs['Distance'].default_value = 0.003
        links.new(agg.outputs['Distance'], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], p.inputs['Normal'])
        # wet/oily patches: noise drives roughness 0.25..0.85
        rng = nodes.new('ShaderNodeMapRange')
        rng.inputs['To Min'].default_value = 0.25
        rng.inputs['To Max'].default_value = 0.85
        links.new(big.outputs['Fac'], rng.inputs['Value'])
        links.new(rng.outputs['Result'], p.inputs['Roughness'])
        return mat
    return get("Asphalt", build)


def heat_haze():
    """Refraction-based heat shimmer for above the exhaust tips.

    A nearly-invisible refraction shader whose normal is wobbled by noise;
    animation.py keyframes the Mapping node's Z location so the distortion
    streams upward like rising hot air.
    """
    def build(name):
        mat, nodes, links, p, out = new_node_material(name)
        nodes.remove(p)
        tex_co = nodes.new('ShaderNodeTexCoord')
        mapping = nodes.new('ShaderNodeMapping')
        mapping.name = mapping.label = "HazeScroll"
        links.new(tex_co.outputs['Object'], mapping.inputs['Vector'])
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 18.0
        noise.inputs['Detail'].default_value = 4.0
        links.new(mapping.outputs['Vector'], noise.inputs['Vector'])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = 0.6
        bump.inputs['Distance'].default_value = 0.02
        links.new(noise.outputs['Fac'], bump.inputs['Height'])
        refr = nodes.new('ShaderNodeBsdfRefraction')
        refr.inputs['IOR'].default_value = 1.03   # barely bends light
        refr.inputs['Roughness'].default_value = 0.0
        links.new(bump.outputs['Normal'], refr.inputs['Normal'])
        # fade the effect out toward the top of the haze volume
        sep = nodes.new('ShaderNodeSeparateXYZ')
        links.new(tex_co.outputs['Generated'], sep.inputs[0])
        fade = nodes.new('ShaderNodeMapRange')
        fade.inputs['From Min'].default_value = 0.0
        fade.inputs['From Max'].default_value = 1.0
        fade.inputs['To Min'].default_value = 1.0
        fade.inputs['To Max'].default_value = 0.0
        links.new(sep.outputs['Z'], fade.inputs['Value'])
        transp = nodes.new('ShaderNodeBsdfTransparent')
        mix = nodes.new('ShaderNodeMixShader')
        links.new(fade.outputs['Result'], mix.inputs['Fac'])
        links.new(transp.outputs[0], mix.inputs[1])
        links.new(refr.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], out.inputs['Surface'])
        if hasattr(mat, "blend_method"):
            mat.blend_method = 'BLEND'
        if hasattr(mat, "shadow_method"):
            mat.shadow_method = 'NONE'   # removed in newer Eevee; Cycles N/A
        return mat
    return get("HeatHaze", build)


def dark_plastic():
    def build(name):
        mat, nodes, links, p, out = new_node_material(name)
        set_inputs(p, base_color=(0.02, 0.02, 0.02), roughness=0.5)
        return mat
    return get("DarkPlastic", build)
