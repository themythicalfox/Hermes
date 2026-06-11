"""
wheels.py — 17" dark-bronze multi-spoke wheels, semi-slick tyres with white
NITTO sidewall lettering, brake discs and calipers.

One complete corner is assembled around an empty at the origin, then
duplicated (linked meshes where possible) to all four hubs. Outer-face
elements (lettering, polished lip) are built on the +X side and the whole
corner is yaw-flipped for the left side so the lettering always faces out.

Stance: aggressive — wheels pushed to the arch edge with ~1.5° negative
camber, matching the slammed green reference car.
"""

import math
from mathutils import Vector

from . import utils, materials
from .utils import TRACK, WHEEL_R, FRONT_AXLE_Y, REAR_AXLE_Y

RIM_R     = 0.215     # 17" rim radius
RIM_W     = 0.235     # ~9.5" wide
TIRE_R    = WHEEL_R   # overall rolling radius
TIRE_W    = 0.255     # 255-section semi slick
N_SPOKES  = 7
CAMBER    = math.radians(-1.5)


def _build_rim(coll):
    """Barrel + polished stepped lip + spokes + centre-lock cap."""
    parts = []

    barrel = utils.make_cylinder("RimBarrel", radius=RIM_R, depth=RIM_W,
                                 segments=48, rotation=(0, math.pi / 2, 0),
                                 coll=coll)
    utils.add_solidify(barrel, -0.008)
    utils.assign_material(barrel, materials.wheel_bronze())
    parts.append(barrel)

    lip = utils.make_torus("RimLip", major_r=RIM_R - 0.004, minor_r=0.016,
                           major_seg=48, minor_seg=12,
                           location=(RIM_W / 2 - 0.01, 0, 0),
                           rotation=(0, math.pi / 2, 0), coll=coll)
    utils.assign_material(lip, materials.polished_lip())
    parts.append(lip)

    # spokes: tapered boxes from hub to rim, slightly concave (tilt inward)
    for i in range(N_SPOKES):
        a = 2 * math.pi * i / N_SPOKES
        spoke = utils.make_box(f"Spoke_{i}",
                               size=(0.030, 0.040, RIM_R - 0.035),
                               coll=coll)
        # place mid-way out, rotate around the axle (X) axis
        r_mid = (RIM_R - 0.03) / 2 + 0.03
        spoke.location = (RIM_W / 2 - 0.045,
                          math.sin(a) * r_mid, math.cos(a) * r_mid)
        spoke.rotation_euler = (a, math.radians(-6), 0)  # concave dish
        utils.add_bevel(spoke, 0.004, 2)
        utils.assign_material(spoke, materials.wheel_bronze())
        parts.append(spoke)

    hub = utils.make_cylinder("HubFace", radius=0.062, depth=0.035,
                              segments=32,
                              location=(RIM_W / 2 - 0.035, 0, 0),
                              rotation=(0, math.pi / 2, 0), coll=coll)
    utils.assign_material(hub, materials.wheel_bronze())
    parts.append(hub)

    # centre-lock nut look: hex cylinder, polished
    nut = utils.make_cylinder("CenterLock", radius=0.030, depth=0.030,
                              segments=6,
                              location=(RIM_W / 2 - 0.012, 0, 0),
                              rotation=(0, math.pi / 2, 0), coll=coll)
    utils.assign_material(nut, materials.polished_lip())
    utils.shade_smooth(nut, 10)   # keep the hex facets crisp
    parts.append(nut)
    return parts


def _build_tire(coll):
    """Torus tyre with squared-off tread via vertex shaping."""
    tire = utils.make_torus("Tire", major_r=(RIM_R + TIRE_R) / 2 - 0.01,
                            minor_r=(TIRE_R - RIM_R) / 2 + 0.035,
                            major_seg=64, minor_seg=24,
                            rotation=(0, math.pi / 2, 0), coll=coll)
    # flatten the contact band: clamp tread radius, square the shoulders.
    # NOTE: local space — the torus is built around local Z; the object's
    # 90° Y rotation maps that to the world X axle.
    me = tire.data
    for v in me.vertices:
        r = math.hypot(v.co.x, v.co.y)        # radial distance (axle = Z)
        if r > TIRE_R - 0.012:                # outside max radius -> clamp
            s = (TIRE_R - 0.012) / r
            v.co.x *= s
            v.co.y *= s
        v.co.z = max(-TIRE_W / 2, min(TIRE_W / 2, v.co.z))  # sidewall width
    utils.add_subsurf(tire, 1)
    utils.assign_material(tire, materials.tire_rubber())
    return tire


def _build_lettering(coll):
    """White 'NITTO' lettering bent around the outer sidewall.

    Text object -> extrude slightly -> SimpleDeform BEND around the wheel
    axis. Two instances at opposite clock positions like real sidewalls.
    """
    import bpy
    letters = []
    for k in range(2):
        curve = bpy.data.curves.new(f"{utils.PREFIX}_NittoText_{k}", 'FONT')
        curve.body = "NITTO"
        curve.size = 0.062
        curve.extrude = 0.0012      # raised rubber letters
        curve.align_x = 'CENTER'
        txt = bpy.data.objects.new(f"{utils.PREFIX}_NittoText_{k}", curve)
        coll.objects.link(txt)
        # lay text flat in XY then bend it into an arc around Z, then orient
        # the arc onto the sidewall (normal = +X, the outer face)
        bend = txt.modifiers.new("Bend", 'SIMPLE_DEFORM')
        bend.deform_method = 'BEND'
        bend.deform_axis = 'Z'
        bend.angle = math.radians(80)
        # radius of the lettering band on the sidewall
        band_r = (RIM_R + TIRE_R) / 2 + 0.022
        txt.location = (TIRE_W / 2 - 0.004, 0, 0)
        txt.rotation_euler = (0, math.radians(90 + (180 * k)),
                              math.radians(90))
        txt.scale = (1, 1, 1)
        # push the bent arc out to the band radius via a parent offset empty
        holder = utils.new_empty(f"NittoHolder_{k}", coll=coll)
        holder.empty_display_size = 0.05
        txt.parent = holder
        txt.location.z = band_r * (1 if k == 0 else -1)
        txt.data.materials.append(materials.white_lettering())
        letters.append(holder)
    return letters


def build_corner(coll):
    """Assemble one wheel+tyre corner parented to a hub empty at origin,
    outer face pointing +X."""
    hub = utils.new_empty("WheelHub_proto", coll=coll)
    for part in _build_rim(coll):
        utils.parent_keep_transform(part, hub)
    tire = _build_tire(coll)
    utils.parent_keep_transform(tire, hub)
    for holder in _build_lettering(coll):
        utils.parent_keep_transform(holder, hub)

    # brake disc + caliper sit behind the spokes (don't rotate with wheel
    # in a still scene, but parent to hub for simplicity here)
    disc = utils.make_cylinder("BrakeDisc", radius=0.150, depth=0.022,
                               segments=48,
                               location=(RIM_W / 2 - 0.10, 0, 0),
                               rotation=(0, math.pi / 2, 0), coll=coll)
    utils.assign_material(disc, materials.brake_metal())
    utils.parent_keep_transform(disc, hub)
    caliper = utils.make_box("Caliper", size=(0.06, 0.07, 0.13),
                             location=(RIM_W / 2 - 0.10, 0.11, 0.05),
                             coll=coll)
    utils.add_bevel(caliper, 0.008, 2)
    utils.assign_material(caliper, materials.orange_accent())
    utils.parent_keep_transform(caliper, hub)
    return hub


def build(root):
    """Place four corners. Returns hub empties keyed by corner tag."""
    coll = utils.sub_collection("Wheels")
    proto = build_corner(coll)

    positions = {
        "FR": ( TRACK / 2, FRONT_AXLE_Y),
        "FL": (-TRACK / 2, FRONT_AXLE_Y),
        "RR": ( TRACK / 2, REAR_AXLE_Y),
        "RL": (-TRACK / 2, REAR_AXLE_Y),
    }
    hubs = {}
    first = True
    for tag, (x, y) in positions.items():
        if first:
            hub = proto
            hub.name = f"{utils.PREFIX}_WheelHub_{tag}"
            first = False
        else:
            hub = _duplicate_hierarchy(proto, coll, tag)
        hub.location = (x, y, WHEEL_R)
        # left wheels: yaw 180° so the lettering/lip face outward
        hub.rotation_euler = (0, CAMBER * (1 if x > 0 else -1),
                              0 if x > 0 else math.pi)
        utils.parent_keep_transform(hub, root)
        hubs[tag] = hub
    return hubs


def _duplicate_hierarchy(src_root, coll, tag):
    """Linked-duplicate an object hierarchy (shared mesh data, new objects)."""
    import bpy
    mapping = {}

    def dup(obj):
        new = obj.copy()                      # object copy, shared data
        if obj.data is not None and obj.type != 'EMPTY':
            pass                              # keep linked mesh data
        new.name = f"{obj.name}_{tag}"
        coll.objects.link(new)
        mapping[obj] = new
        for child in obj.children:
            c = dup(child)
            c.parent = new
            c.matrix_parent_inverse = child.matrix_parent_inverse.copy()
        return new

    return dup(src_root)
