"""
scene_setup.py — environment, lighting, render settings, output helpers.

World lighting: if an HDRI image path is supplied (scene custom property
'hermes_hdri_path', or the HDRI_PATH constant below), it is loaded as an
equirectangular environment — point this at any urban-parking-lot HDRI
(e.g. a Poly Haven 4k+ .exr) for the photoreal look. With no HDRI we fall
back to a procedural Nishita sky, which still gives believable sun + soft
blue fill.

Render: Cycles, 512 samples, OptiX/OIDN denoise, filmic-ish view transform.
"""

import math
import os
import bpy

from . import utils, materials

# drop an absolute path to a parking-lot HDRI here, or set the scene
# property 'hermes_hdri_path' before running main_miata.build()
HDRI_PATH = ""


# ---------------------------------------------------------------------------
# World
# ---------------------------------------------------------------------------

def setup_world(scene):
    world = bpy.data.worlds.get(f"{utils.PREFIX}_World")
    if world is None:
        world = bpy.data.worlds.new(f"{utils.PREFIX}_World")
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    out = nodes.new('ShaderNodeOutputWorld'); out.location = (400, 0)
    bg = nodes.new('ShaderNodeBackground'); bg.location = (200, 0)
    links.new(bg.outputs['Background'], out.inputs['Surface'])

    hdri = scene.get("hermes_hdri_path", "") or HDRI_PATH
    if hdri and os.path.exists(bpy.path.abspath(hdri)):
        env = nodes.new('ShaderNodeTexEnvironment'); env.location = (-200, 0)
        env.image = bpy.data.images.load(bpy.path.abspath(hdri),
                                         check_existing=True)
        mapping = nodes.new('ShaderNodeMapping'); mapping.location = (-400, 0)
        mapping.inputs['Rotation'].default_value = (0, 0, math.radians(35))
        coord = nodes.new('ShaderNodeTexCoord'); coord.location = (-600, 0)
        links.new(coord.outputs['Generated'], mapping.inputs['Vector'])
        links.new(mapping.outputs['Vector'], env.inputs['Vector'])
        links.new(env.outputs['Color'], bg.inputs['Color'])
        bg.inputs['Strength'].default_value = 1.0
    else:
        # procedural daylight: late-afternoon sun, soft shadows
        sky = nodes.new('ShaderNodeTexSky'); sky.location = (-200, 0)
        if hasattr(sky, "sky_type"):
            try:
                sky.sky_type = 'NISHITA'
                sky.sun_elevation = math.radians(28)
                sky.sun_rotation = math.radians(140)
                sky.sun_intensity = 0.6
                sky.altitude = 10
            except (AttributeError, TypeError):
                pass
        links.new(sky.outputs['Color'], bg.inputs['Color'])
        bg.inputs['Strength'].default_value = 0.5
    return world


# ---------------------------------------------------------------------------
# Ground & fill lights
# ---------------------------------------------------------------------------

def setup_ground(coll):
    ground = utils.make_plane("Ground", 60, 60, location=(0, 0, 0),
                              coll=coll)
    utils.assign_material(ground, materials.asphalt())

    # faded parking-line stripes either side of the car
    line_mat, nodes, links, p, out = utils.new_node_material("ParkingLine")
    utils.set_inputs(p, base_color=(0.35, 0.33, 0.28), roughness=0.8)
    for i, x in enumerate((-1.6, 1.6)):
        line = utils.make_plane(f"ParkLine_{i}", 0.12, 5.5,
                                location=(x, 0, 0.001), coll=coll)
        utils.assign_material(line, line_mat)
    return ground


def setup_fill_lights(coll):
    """Soft area fills so the paint flake and metal anisotropy read clearly
    even under flat HDRI light — classic automotive 'window' reflections."""
    specs = [
        # name,            loc,             rot (deg),        size,  power
        ("KeyTop",    (0, 0, 6.0),       (0, 0, 0),         (8, 3),  500),
        ("RimRear",   (-4.0, -5.0, 2.0), (65, 0, -140),     (4, 2),  200),
        ("FillFront", (3.5, 4.5, 1.5),   (75, 0, 35),       (3, 3),  120),
    ]
    lights = []
    for name, loc, rot, size, power in specs:
        data = bpy.data.lights.new(f"{utils.PREFIX}_{name}", 'AREA')
        data.shape = 'RECTANGLE'
        data.size, data.size_y = size
        data.energy = power
        obj = bpy.data.objects.new(f"{utils.PREFIX}_{name}", data)
        obj.location = loc
        obj.rotation_euler = [math.radians(a) for a in rot]
        coll.objects.link(obj)
        lights.append(obj)
    return lights


# ---------------------------------------------------------------------------
# Heat haze volumes (placed above the exhaust tips)
# ---------------------------------------------------------------------------

def setup_heat_haze(coll, exhaust_tips):
    haze_mat = materials.heat_haze()
    haze_objs = []
    for tip in exhaust_tips:
        loc = tip.matrix_world.translation
        haze = utils.make_plane(f"Haze_{tip.name.split('_')[-1]}",
                                0.14, 0.45,
                                location=(loc.x, loc.y - 0.12, loc.z + 0.20),
                                rotation=(math.radians(90), 0, 0),
                                coll=coll)
        utils.assign_material(haze, haze_mat)
        haze.visible_shadow = False
        haze_objs.append(haze)
    return haze_objs


# ---------------------------------------------------------------------------
# Render settings
# ---------------------------------------------------------------------------

def setup_render(scene, samples=512, animation=False):
    scene.render.engine = 'CYCLES'
    cycles = scene.cycles
    cycles.samples = samples
    cycles.use_denoising = True
    cycles.preview_samples = 64
    try:
        cycles.denoiser = 'OPENIMAGEDENOISE'
    except TypeError:
        pass
    # GPU if available
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        for dev_type in ('OPTIX', 'CUDA', 'HIP', 'METAL', 'ONEAPI'):
            try:
                prefs.compute_device_type = dev_type
                cycles.device = 'GPU'
                break
            except TypeError:
                continue
    except (KeyError, AttributeError):
        pass

    scene.render.resolution_x = 2560
    scene.render.resolution_y = 1440
    scene.render.film_transparent = False

    # cinematic colour: AgX (5.x default) with a touch more contrast
    try:
        scene.view_settings.view_transform = 'AgX'
        scene.view_settings.look = 'AgX - Punchy'
    except TypeError:
        pass
    scene.view_settings.exposure = 0.15

    if animation:
        scene.render.image_settings.file_format = 'FFMPEG'
        scene.render.ffmpeg.format = 'MPEG4'
        scene.render.ffmpeg.codec = 'H264'
        scene.render.ffmpeg.constant_rate_factor = 'HIGH'
        scene.render.filepath = "//renders/hermes_reel_"
    else:
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_depth = '16'
        scene.render.filepath = "//renders/hermes_still_"


# ---------------------------------------------------------------------------
# Still-frame helper
# ---------------------------------------------------------------------------

STILL_FRAMES = {
    # frame -> the marker-bound camera already active there (see animation.py)
    "orbit_hero": 45,
    "rear_34":    110,
    "interior":   160,
    "shifter":    185,
    "front_low":  230,
    "hero_side":  280,
}


def render_stills(scene, out_dir="//renders/stills/"):
    """Render the six signature angles as high-res PNGs."""
    scene.render.image_settings.file_format = 'PNG'
    for name, frame in STILL_FRAMES.items():
        scene.frame_set(frame)
        scene.render.filepath = f"{out_dir}hermes_{name}"
        bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build(scene, exhaust_tips, samples=512):
    coll = utils.sub_collection("Scene")
    setup_world(scene)
    setup_ground(coll)
    setup_fill_lights(coll)
    haze = setup_heat_haze(coll, exhaust_tips)
    setup_render(scene, samples=samples)
    return {"haze": haze}
