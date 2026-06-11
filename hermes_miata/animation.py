"""
animation.py — the 300-frame @ 30 fps reel.

Timeline layout (frames):
   1- 60   hero orbit begins, headlights sweep ON (20-35), idle vibration
  60-140   soft top OPENS (shape key 0 -> 1)
  80-200   blinkers hazard-flash (driver-based square wave)
 200-260   soft top CLOSES
 270-290   lights OFF
   1-300   continuous: camera orbit, exhaust jiggle, heat haze scroll,
           whole-car idle vibration

Camera system: an orbit empty at the car's centre with a child camera;
timeline markers bind extra fixed cameras (rear 3/4, front low, interior,
shifter close-up) so one render run yields a multi-angle reel.
"""

import math
import bpy

from . import utils
from .utils import keyframe, add_noise_to_fcurves

FPS = 30
FRAME_START = 1
FRAME_END = 300


def setup_timeline(scene):
    scene.frame_start = FRAME_START
    scene.frame_end = FRAME_END
    scene.render.fps = FPS


# ---------------------------------------------------------------------------
# Light animation
# ---------------------------------------------------------------------------

def _driver_node(mat):
    """Find the 'LightDriver' Value node animation hooks live on."""
    if not mat.use_nodes:
        return None
    return mat.node_tree.nodes.get("LightDriver")


def animate_lights(lights):
    """Headlights/taillights ramp on, then off near the end; blinkers get a
    frame-driven square-wave driver (classic ~90 cpm hazard cadence)."""
    seen = set()

    def strength_keys(objs, pairs):
        for obj in objs:
            for mat in obj.data.materials:
                if mat is None or mat.name in seen:
                    continue
                node = _driver_node(mat)
                if node is None:
                    continue
                seen.add(mat.name)
                sock = node.outputs[0]
                for fr, val in pairs:
                    sock.default_value = val
                    sock.keyframe_insert("default_value", frame=fr)

    strength_keys(lights["head"], [(1, 0), (20, 0), (35, 60), (270, 60),
                                   (285, 0)])
    strength_keys(lights["tail"], [(1, 0), (20, 0), (30, 25), (272, 25),
                                   (287, 0)])

    # blinkers: driver expression — on only between frames 80 and 200,
    # square wave at 1.5 Hz (30 fps -> period 20 frames)
    for obj in lights["blink"]:
        for mat in obj.data.materials:
            if mat is None:
                continue
            node = _driver_node(mat)
            if node is None or mat.name in seen:
                continue
            seen.add(mat.name)
            fcurve = node.outputs[0].driver_add("default_value")
            drv = fcurve.driver
            drv.type = 'SCRIPTED'
            drv.expression = ("(20 if (frame % 20) < 10 else 0)"
                              " * (1 if 80 <= frame <= 200 else 0)")


# ---------------------------------------------------------------------------
# Mechanical motion
# ---------------------------------------------------------------------------

def animate_idle_vibration(root):
    """Whole-car engine idle: sub-millimetre Z noise + tiny roll noise."""
    add_noise_to_fcurves(root, "location", strength=0.0012, scale=4.0,
                         indices=(2,))
    add_noise_to_fcurves(root, "rotation_euler", strength=0.0008, scale=5.0,
                         indices=(0, 1))


def animate_exhaust_jiggle(tips):
    """Exhaust pipes shiver a little harder than the body (rubber hangers)."""
    for tip in tips:
        add_noise_to_fcurves(tip, "location", strength=0.0025, scale=2.5,
                             indices=(2,))
        add_noise_to_fcurves(tip, "rotation_euler", strength=0.004,
                             scale=3.0, indices=(0,))


def animate_soft_top(soft_top):
    """Open 60->140, hold, close 200->260 via the 'Fold' shape key."""
    key = soft_top.data.shape_keys
    if key is None:
        return
    fold = key.key_blocks.get("Fold")
    if fold is None:
        return
    for fr, val in ((1, 0.0), (60, 0.0), (140, 1.0),
                    (200, 1.0), (260, 0.0)):
        fold.value = val
        fold.keyframe_insert("value", frame=fr)
    # ease the motion
    if key.animation_data and key.animation_data.action:
        for fc in key.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'SINE'
                kp.easing = 'EASE_IN_OUT'


def animate_heat_haze(haze_objs):
    """Scroll each haze shader's Mapping node downward in Z over time so
    the refraction noise appears to rise like hot air."""
    for obj in haze_objs:
        for mat in obj.data.materials:
            if mat is None or not mat.use_nodes:
                continue
            mapping = mat.node_tree.nodes.get("HazeScroll")
            if mapping is None:
                continue
            loc = mapping.inputs['Location']
            for fr, z in ((FRAME_START, 0.0), (FRAME_END, -6.0)):
                loc.default_value = (0.0, 0.0, z)
                loc.keyframe_insert("default_value", frame=fr)
            # linear scroll
            tree = mat.node_tree
            if tree.animation_data and tree.animation_data.action:
                for fc in tree.animation_data.action.fcurves:
                    for kp in fc.keyframe_points:
                        kp.interpolation = 'LINEAR'


def animate_displays(displays):
    """Step the E-ink content a few times (page refresh feel, not video)."""
    for obj in displays:
        for mat in obj.data.materials:
            if mat is None or not mat.use_nodes:
                continue
            node = mat.node_tree.nodes.get("DisplayDriver")
            if node is None:
                continue
            sock = node.outputs[0]
            for i, fr in enumerate(range(FRAME_START, FRAME_END, 45)):
                sock.default_value = float(i * 13)   # jump to a new "page"
                sock.keyframe_insert("default_value", frame=fr)
            if mat.node_tree.animation_data and \
                    mat.node_tree.animation_data.action:
                for fc in mat.node_tree.animation_data.action.fcurves:
                    for kp in fc.keyframe_points:
                        kp.interpolation = 'CONSTANT'   # hard e-ink refresh


# ---------------------------------------------------------------------------
# Cameras
# ---------------------------------------------------------------------------

def _make_camera(name, location, coll, focus=None, lens=50, fstop=2.8):
    cam_data = bpy.data.cameras.new(f"{utils.PREFIX}_{name}")
    cam_data.lens = lens
    cam_data.dof.use_dof = True
    cam_data.dof.aperture_fstop = fstop
    if focus is not None:
        cam_data.dof.focus_object = focus
    cam = bpy.data.objects.new(f"{utils.PREFIX}_{name}", cam_data)
    cam.location = location
    coll.objects.link(cam)
    return cam


def _track(cam, target):
    con = cam.constraints.new('TRACK_TO')
    con.target = target
    con.track_axis = 'TRACK_NEGATIVE_Z'
    con.up_axis = 'UP_Y'


def build_camera_rig(scene, focus_target):
    """Orbit rig + fixed beauty cams bound to timeline markers."""
    coll = utils.sub_collection("Cameras")

    # aim point: car centre at hood height
    aim = utils.new_empty("CamAim", (0, 0, 0.55), coll)

    # --- orbiting hero camera ---------------------------------------------
    pivot = utils.new_empty("OrbitPivot", (0, 0, 0.5), coll)
    orbit_cam = _make_camera("Cam_Orbit", (4.6, -3.4, 1.15), coll,
                             focus=focus_target, lens=60, fstop=2.5)
    utils.parent_keep_transform(orbit_cam, pivot)
    _track(orbit_cam, aim)
    keyframe(pivot, "rotation_euler",
             [(FRAME_START, 0.0), (FRAME_END, math.radians(300))], index=2,
             interpolation='LINEAR')

    # --- fixed cameras ------------------------------------------------------
    fixed = {
        "Cam_HeroSide":  ((5.2, 0.0, 0.85), 85, 2.0),
        "Cam_Rear34":    ((3.4, -4.4, 1.30), 50, 2.8),
        "Cam_FrontLow":  ((-2.6, 4.6, 0.42), 35, 4.0),
        "Cam_Interior":  ((-0.35, -1.45, 0.95), 24, 2.0),
        "Cam_Shifter":   ((0.35, -0.75, 0.75), 50, 1.8),
    }
    cams = {}
    for name, (loc, lens, fstop) in fixed.items():
        cam = _make_camera(name, loc, coll, focus=focus_target,
                           lens=lens, fstop=fstop)
        if name == "Cam_Interior":
            interior_aim = utils.new_empty("CamAimInterior",
                                           (0, 0.6, 0.55), coll)
            _track(cam, interior_aim)
        elif name == "Cam_Shifter":
            shifter_aim = utils.new_empty("CamAimShifter",
                                          (0, 0.0, 0.45), coll)
            _track(cam, shifter_aim)
        else:
            _track(cam, aim)
        cams[name] = cam

    # --- bind cameras to timeline segments via markers ----------------------
    scene.timeline_markers.clear()
    segments = [
        (1,   orbit_cam),            # opening orbit
        (90,  cams["Cam_Rear34"]),   # wing/diffuser with top opening
        (140, cams["Cam_Interior"]), # cockpit while the top is down
        (175, cams["Cam_Shifter"]),  # gated shifter close-up
        (210, cams["Cam_FrontLow"]), # top closing, low front
        (255, cams["Cam_HeroSide"]), # closing hero profile
    ]
    for frame, cam in segments:
        m = scene.timeline_markers.new(f"CUT_{cam.name}", frame=frame)
        m.camera = cam
    scene.camera = orbit_cam
    return cams


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build(scene, handles):
    """`handles` is the dict assembled by main_miata.py."""
    setup_timeline(scene)
    animate_idle_vibration(handles["root"])
    animate_exhaust_jiggle(handles["exhaust_tips"])
    animate_lights(handles["lights"])
    animate_soft_top(handles["soft_top"])
    animate_heat_haze(handles.get("haze", []))
    animate_displays(handles.get("displays", []))
    build_camera_rig(scene, handles["body"])
