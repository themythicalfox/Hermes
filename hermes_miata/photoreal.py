"""
photoreal.py — one-click "make it look like a photograph" pass.

Applies every project / render / camera / world / compositor setting that
pushes the Hermes Miata from "nice CG" toward photorealism:

  * Cycles tuned for car paint + glass (deep glossy/transmission bounces,
    firefly clamping, glossy filtering, no caustics)
  * AgX colour management with a punchy look and gentle exposure lift
  * Real-photo camera physics: full-frame sensor, 9-blade iris, sane
    f-stops, motion blur at a 180° shutter for the reel
  * Shadow-terminator fixes on the smooth lofted body panels
  * A film-emulation compositor graph: fog-glow bloom, subtle barrel
    distortion + chromatic dispersion, vignette, fine photographic grain

Run from the N-panel ("Photoreal Polish") or:
    from hermes_miata import photoreal
    photoreal.apply(for_animation=False)

Manual finishing touches that scripts can't judge for you (HDRI choice,
sculpt passes, decals, stance tweaks) are documented in
docs/PHOTOREALISM.md at the repo root.
"""

import math
import bpy

from . import utils


# ---------------------------------------------------------------------------
# Cycles
# ---------------------------------------------------------------------------

def setup_cycles(scene, for_animation=False):
    """Sampling and light-path budget tuned for automotive work."""
    scene.render.engine = 'CYCLES'
    c = scene.cycles

    # --- sampling ---------------------------------------------------------
    # stills can afford to brute-force; animation leans on the denoiser
    c.samples = 512 if for_animation else 2048
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.02 if for_animation else 0.01
    c.use_denoising = True
    for attr, val in (("denoiser", 'OPENIMAGEDENOISE'),
                      ("denoising_input_passes", 'RGB_ALBEDO_NORMAL'),
                      ("denoising_prefilter", 'ACCURATE'),
                      ("denoising_use_gpu", True)):
        try:
            setattr(c, attr, val)
        except (AttributeError, TypeError):
            pass

    # --- light paths ------------------------------------------------------
    # clearcoat paint needs glossy depth; glass + headlight covers need
    # transmission depth; transparent depth keeps haze planes invisible
    c.max_bounces = 12
    c.diffuse_bounces = 4
    c.glossy_bounces = 8
    c.transmission_bounces = 12
    c.transparent_max_bounces = 16
    c.volume_bounces = 2

    # --- noise control ----------------------------------------------------
    c.sample_clamp_direct = 0.0          # never clamp direct (kills sun)
    c.sample_clamp_indirect = 10.0       # tames paint-flake fireflies
    c.blur_glossy = 0.5                  # "Filter Glossy" — softens caustic-y
    c.caustics_reflective = False        #   sparkle noise without visible loss
    c.caustics_refractive = False

    # --- film -------------------------------------------------------------
    try:
        c.pixel_filter_type = 'BLACKMAN_HARRIS'
        c.filter_width = 1.5             # crisp but not aliased, photo-like
    except (AttributeError, TypeError):
        pass

    # --- motion blur: the single biggest "video looks real" switch --------
    scene.render.use_motion_blur = for_animation
    scene.render.motion_blur_shutter = 0.5   # 180° shutter rule

    # --- performance ------------------------------------------------------
    scene.render.use_persistent_data = True  # huge speedup across frames
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        for dev_type in ('OPTIX', 'CUDA', 'HIP', 'METAL', 'ONEAPI'):
            try:
                prefs.compute_device_type = dev_type
                prefs.get_devices()
                if any(d.type != 'CPU' for d in prefs.devices):
                    c.device = 'GPU'
                    break
            except (TypeError, AttributeError):
                continue
    except (KeyError, AttributeError):
        pass


# ---------------------------------------------------------------------------
# Colour management & output
# ---------------------------------------------------------------------------

def setup_color(scene):
    """AgX handles speculars/sun far more photographically than Standard."""
    vs = scene.view_settings
    try:
        vs.view_transform = 'AgX'
    except TypeError:
        try:
            vs.view_transform = 'Filmic'   # older builds
        except TypeError:
            pass
    for look in ('AgX - Punchy', 'Punchy', 'High Contrast'):
        try:
            vs.look = look
            break
        except TypeError:
            continue
    vs.exposure = 0.15
    vs.gamma = 1.0

    # real-world scale matters for DOF/physics — confirm metric 1.0
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0


def setup_output(scene, for_animation=False):
    scene.render.resolution_percentage = 100
    if for_animation:
        scene.render.resolution_x = 2560
        scene.render.resolution_y = 1440
        scene.render.image_settings.file_format = 'FFMPEG'
        scene.render.ffmpeg.format = 'MPEG4'
        scene.render.ffmpeg.codec = 'H264'
        scene.render.ffmpeg.constant_rate_factor = 'PERC_LOSSLESS'
        scene.render.ffmpeg.gopsize = 15
        scene.render.filepath = "//renders/hermes_reel_"
    else:
        scene.render.resolution_x = 3840
        scene.render.resolution_y = 2160
        # EXR keeps full dynamic range for grading; switch to PNG-16 if you
        # want straight-out-of-Blender files
        scene.render.image_settings.file_format = 'OPEN_EXR'
        scene.render.image_settings.color_depth = '32'
        scene.render.filepath = "//renders/hermes_still_"


# ---------------------------------------------------------------------------
# Cameras — real-photo physics
# ---------------------------------------------------------------------------

# per-camera photographic intent: (lens mm, f-stop)
_CAM_OPTICS = {
    "Cam_Orbit":    (60, 4.0),   # walkaround: enough DOF to keep car sharp
    "Cam_HeroSide": (85, 2.8),   # compressed hero profile, creamy bokeh
    "Cam_Rear34":   (50, 4.0),
    "Cam_FrontLow": (35, 5.6),   # wide + low wants more in focus
    "Cam_Interior": (24, 2.8),   # tight cockpit, shallow falloff
    "Cam_Shifter":  (50, 1.8),   # macro-ish detail shot
}


def polish_cameras(scene):
    for obj in bpy.data.objects:
        if obj.type != 'CAMERA' or not obj.name.startswith(utils.PREFIX):
            continue
        cam = obj.data
        cam.sensor_width = 36.0          # full-frame back
        cam.sensor_fit = 'HORIZONTAL'
        cam.dof.use_dof = True
        cam.dof.aperture_blades = 9      # rounded, photographic bokeh
        cam.dof.aperture_rotation = math.radians(10)
        for key, (lens, fstop) in _CAM_OPTICS.items():
            if key in obj.name:
                cam.lens = lens
                cam.dof.aperture_fstop = fstop
                break


# ---------------------------------------------------------------------------
# Geometry fixes
# ---------------------------------------------------------------------------

def polish_objects():
    """Shadow-terminator offsets stop the banded 'CG shadow' artefact on
    the smooth-shaded low-poly-cage body panels."""
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or not obj.name.startswith(utils.PREFIX):
            continue
        try:
            obj.cycles.shadow_terminator_geometry_offset = 0.1
            obj.cycles.shadow_terminator_offset = 0.05
        except AttributeError:
            pass


# ---------------------------------------------------------------------------
# Compositor: the "shot on a camera" layer
# ---------------------------------------------------------------------------

def setup_compositor(scene):
    """Bloom -> lens distortion + chromatic dispersion -> vignette -> grain.

    Each effect is deliberately at the edge of perception: if you can name
    the effect while looking at the image, it's too strong.
    """
    scene.use_nodes = True
    tree = scene.node_tree
    if tree is None:
        return
    tree.nodes.clear()

    rl = tree.nodes.new('CompositorNodeRLayers');   rl.location = (-800, 0)
    out = tree.nodes.new('CompositorNodeComposite'); out.location = (900, 0)

    last = rl.outputs['Image']

    # --- bloom: fog glow lifts headlight/spec highlights like real glass --
    try:
        glare = tree.nodes.new('CompositorNodeGlare')
        glare.location = (-550, 0)
        glare.glare_type = 'FOG_GLOW'
        glare.quality = 'HIGH'
        if hasattr(glare, "mix"):
            glare.mix = -0.92          # mostly original image, whisper of glow
        if hasattr(glare, "threshold"):
            glare.threshold = 1.0
        if hasattr(glare, "size"):
            glare.size = 7
        tree.links.new(last, glare.inputs['Image'])
        last = glare.outputs['Image']
    except (RuntimeError, AttributeError, TypeError):
        pass

    # --- lens distortion + chromatic aberration ---------------------------
    try:
        lens = tree.nodes.new('CompositorNodeLensdist')
        lens.location = (-300, 0)
        if 'Distort' in lens.inputs:
            lens.inputs['Distort'].default_value = 0.004      # faint barrel
        if 'Dispersion' in lens.inputs:
            lens.inputs['Dispersion'].default_value = 0.008   # CA at edges
        tree.links.new(last, lens.inputs['Image'])
        last = lens.outputs['Image']
    except (RuntimeError, AttributeError, KeyError):
        pass

    # --- vignette: ellipse mask, heavily blurred, multiplied at ~12% ------
    try:
        mask = tree.nodes.new('CompositorNodeEllipseMask')
        mask.location = (-300, -350)
        mask.width = 0.92
        mask.height = 0.72
        blur = tree.nodes.new('CompositorNodeBlur')
        blur.location = (-100, -350)
        blur.filter_type = 'FAST_GAUSS'
        blur.size_x = blur.size_y = 400
        blur.use_relative = False
        tree.links.new(mask.outputs['Mask'], blur.inputs['Image'])

        vmap = tree.nodes.new('CompositorNodeMapRange')
        vmap.location = (100, -350)
        vmap.inputs['To Min'].default_value = 0.88   # corner darkening
        vmap.inputs['To Max'].default_value = 1.0
        tree.links.new(blur.outputs['Image'], vmap.inputs['Value'])

        vmix = tree.nodes.new('CompositorNodeMixRGB')
        vmix.location = (300, 0)
        vmix.blend_type = 'MULTIPLY'
        vmix.inputs['Fac'].default_value = 1.0
        tree.links.new(last, vmix.inputs[1])
        tree.links.new(vmap.outputs['Result'], vmix.inputs[2])
        last = vmix.outputs['Image']
    except (RuntimeError, AttributeError, KeyError):
        pass

    # --- photographic grain: clouds texture, soft-light at ~3% ------------
    try:
        ntex = bpy.data.textures.get(f"{utils.PREFIX}_Grain")
        if ntex is None:
            ntex = bpy.data.textures.new(f"{utils.PREFIX}_Grain", 'CLOUDS')
            ntex.noise_scale = 0.0008    # fine, high-frequency grain
            ntex.noise_depth = 0
        tex_node = tree.nodes.new('CompositorNodeTexture')
        tex_node.location = (300, -350)
        tex_node.texture = ntex
        gmix = tree.nodes.new('CompositorNodeMixRGB')
        gmix.location = (600, 0)
        gmix.blend_type = 'SOFT_LIGHT'
        gmix.inputs['Fac'].default_value = 0.03
        tree.links.new(last, gmix.inputs[1])
        tree.links.new(tex_node.outputs[0], gmix.inputs[2])
        last = gmix.outputs['Image']
    except (RuntimeError, AttributeError, KeyError):
        pass

    tree.links.new(last, out.inputs['Image'])


# ---------------------------------------------------------------------------
# World nudges
# ---------------------------------------------------------------------------

def polish_world(scene):
    """If running on the procedural-sky fallback, nudge the sun low and warm
    (golden hour reads as 'photo' far more than noon light)."""
    world = scene.world
    if world is None or not world.use_nodes:
        return
    for node in world.node_tree.nodes:
        if node.type == 'TEX_SKY' and getattr(node, "sky_type", "") == 'NISHITA':
            node.sun_elevation = math.radians(14)   # long raking shadows
            node.sun_rotation = math.radians(125)
            node.sun_intensity = 0.55
            node.dust_density = 3.0                 # hazy urban air
            node.ozone_density = 1.2
        if node.type == 'TEX_ENVIRONMENT':
            # HDRI in use: leave colour alone, that's the ground truth
            pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def apply(scene=None, for_animation=False):
    scene = scene or bpy.context.scene
    setup_cycles(scene, for_animation)
    setup_color(scene)
    setup_output(scene, for_animation)
    polish_cameras(scene)
    polish_objects()
    polish_world(scene)
    setup_compositor(scene)
    print("[Hermes] Photoreal polish applied "
          f"({'animation' if for_animation else 'stills'} profile).")
