"""
body.py — procedural NB Miata widebody exterior, built as SEPARATE PANELS.

Pipeline (v2):
  1. Loft a single smooth hull from 14 NB-proportioned cross sections so
     the surfacing flows continuously (modelling each panel separately by
     hand is covered in docs/MODELING_GUIDE.md — this is the procedural
     approximation).
  2. Push widebody flares out around the arches, subdivide, cut the wheel
     arches / cockpit / intakes with booleans, then BAKE the whole stack
     to real geometry and delete the cutters (no live-modifier wireframe
     clutter left in the viewport).
  3. SPLIT the baked hull into real panels — front bumper, hood, L/R front
     fenders, L/R doors, L/R rear quarters, trunk lid, rear bumper, tail
     panel — each its own object with thickness (solidify) and visible
     shutline gaps opened along the split boundaries.

Hardware (wing, diffuser, exhaust, lights, soft top, mirrors) parents to a
BodyPivot empty. The wing/diffuser pivots are now LOCAL (the v1 bug where
rotating them swung the part around the world origin is gone).

Axes:  +Y nose, +X driver right, +Z up, ground at z=0.
"""

import math
import bpy
import bmesh
from mathutils import Vector

from . import utils, materials
from .utils import (WHEELBASE, LENGTH, WIDTH, HEIGHT, TRACK, WHEEL_R,
                    RIDE_HEIGHT, FRONT_AXLE_Y, REAR_AXLE_Y)

SILL_Z = RIDE_HEIGHT          # rocker bottom
BELT_Z = 0.72                 # door-top beltline (slammed NB)
COWL_Z = 0.80                 # hood at the windscreen base
DECK_Z = 0.78                 # rear deck top

# windscreen geometry shared with the soft top
WS_BASE_Y, WS_TOP_Y = 0.515, 0.215
WS_BASE_Z, WS_TOP_Z = COWL_Z, 1.14


# ---------------------------------------------------------------------------
# Hull loft
# ---------------------------------------------------------------------------

# stations nose -> tail: (y, half_width, sill_z, belt_z, crown_z)
# tuned against NB profile photos: low rounded nose, hood rising to the
# cowl, flat-ish door section, haunches swelling over the rear axle,
# high rounded tail with the deck falling away.
_STATIONS = [
    ( 1.960, 0.300, 0.300, 0.450, 0.500),   # nose tip
    ( 1.860, 0.560, 0.140, 0.500, 0.550),
    ( 1.680, 0.740, 0.085, 0.540, 0.585),   # bumper face
    ( 1.400, 0.810, 0.085, 0.570, 0.630),
    ( 1.135, 0.840, 0.085, 0.600, 0.685),   # front axle
    ( 0.800, 0.855, 0.085, 0.640, 0.745),   # hood mid
    ( 0.500, 0.865, 0.085, 0.680, 0.800),   # cowl / windscreen base
    ( 0.200, 0.870, 0.085, 0.715, 0.735),   # door front (cabin: crown≈belt)
    (-0.400, 0.870, 0.085, 0.720, 0.740),   # door rear
    (-0.850, 0.875, 0.085, 0.730, 0.760),   # B-pillar / deck start
    (-1.135, 0.865, 0.085, 0.735, 0.785),   # rear axle (haunch)
    (-1.500, 0.800, 0.100, 0.740, 0.800),   # deck
    (-1.750, 0.700, 0.130, 0.700, 0.775),
    (-1.930, 0.460, 0.240, 0.550, 0.710),   # tail panel
]


def _half_profile(y, w, sill, belt, crown):
    """One half cross-section, floor-centre -> roof-centre (10 points).
    Widest point sits mid-height (the Miata 'hip'), tucks in to the belt,
    then rolls over the shoulder onto the hood/deck crown."""
    mid = (sill + belt) * 0.5
    return [
        (0.0,      y, sill + 0.012),                    # floor centre
        (w * 0.55, y, sill),                            # floor edge
        (w * 0.97, y, sill + 0.035),                    # rocker
        (w * 1.00, y, sill + 0.16),                     # lower bodyside
        (w * 1.025, y, mid),                            # widest hip
        (w * 0.995, y, belt - 0.05),                    # upper bodyside
        (w * 0.94, y, belt),                            # beltline shoulder
        (w * 0.80, y, belt + (crown - belt) * 0.55),    # shoulder roll
        (w * 0.45, y, crown - 0.008),                   # crown approach
        (0.0,      y, crown),                           # centreline
    ]


def _ring(half):
    """Mirror a half profile into one closed, consistently-wound ring."""
    plus = list(reversed(half))                        # crown .. floor (+X)
    minus = [(-x, y, z) for (x, y, z) in half[1:-1]]   # floor .. crown (-X)
    return plus + minus + [plus[0]]                    # welded in the loft


def _build_hull(coll):
    hull = utils.loft_sections(
        "Hull", [_ring(_half_profile(*s)) for s in _STATIONS], coll=coll)
    _flare_fenders(hull)
    utils.add_subsurf(hull, levels=2, render_levels=2)
    return hull


def _flare_fenders(obj):
    """Bolt-on style widebody: radial outward push around each hub with a
    smoothstep falloff, biased to the lower body."""
    flare, radius, hub_z = 0.07, 0.58, WHEEL_R
    for v in obj.data.vertices:
        if abs(v.co.x) < 0.45:
            continue
        for axle_y in (FRONT_AXLE_Y, REAR_AXLE_Y):
            d = math.hypot(v.co.y - axle_y, v.co.z - hub_z)
            if d < radius:
                t = 1.0 - d / radius
                t = t * t * (3 - 2 * t)
                v.co.x += math.copysign(flare * t, v.co.x)


# ---------------------------------------------------------------------------
# Cut, bake, split
# ---------------------------------------------------------------------------

def _cut_openings(hull, coll):
    """Boolean the arches, cockpit and intakes, then return the cutters so
    they can be deleted after baking."""
    cutters = []
    arch_r = WHEEL_R + 0.05
    for tag, axle_y in (("F", FRONT_AXLE_Y), ("R", REAR_AXLE_Y)):
        c = utils.make_cylinder(f"_cutArch{tag}", radius=arch_r,
                                depth=WIDTH * 1.4, segments=48,
                                location=(0, axle_y, WHEEL_R),
                                rotation=(0, math.pi / 2, 0), coll=coll)
        utils.boolean_cut(hull, c)
        cutters.append(c)

    # cockpit opening: from just behind the windscreen base to the deck
    c = utils.make_box("_cutCockpit", size=(1.16, 1.30, 0.50),
                       location=(0, -0.20, BELT_Z + 0.24), coll=coll)
    utils.boolean_cut(hull, c)
    cutters.append(c)

    # front bumper mouth + brake ducts
    c = utils.make_box("_cutMouth", size=(0.60, 0.30, 0.14),
                       location=(0, LENGTH / 2 - 0.06, 0.30), coll=coll)
    utils.boolean_cut(hull, c)
    cutters.append(c)
    for side in (-1, 1):
        c = utils.make_box(f"_cutDuct{side}", size=(0.20, 0.26, 0.09),
                           location=(side * 0.52, LENGTH / 2 - 0.07, 0.20),
                           coll=coll)
        utils.boolean_cut(hull, c)
        cutters.append(c)
    return cutters


# panel predicates run on baked face centres (object sits at world origin)
def _panel_defs():
    HOOD_X, DECK_X = 0.52, 0.55
    return [
        ("Bumper_F",  lambda c: c.y > 1.58),
        ("Hood",      lambda c: 0.50 < c.y <= 1.58 and c.z > 0.55
                                and abs(c.x) < HOOD_X),
        ("Fender_FR", lambda c: 0.45 < c.y <= 1.58 and c.x >= 0),
        ("Fender_FL", lambda c: 0.45 < c.y <= 1.58 and c.x < 0),
        ("Door_R",    lambda c: -0.85 < c.y <= 0.45 and c.x >= 0),
        ("Door_L",    lambda c: -0.85 < c.y <= 0.45 and c.x < 0),
        ("Trunk",     lambda c: -1.66 < c.y <= -0.85 and c.z > 0.62
                                and abs(c.x) < DECK_X),
        ("Quarter_R", lambda c: -1.66 < c.y <= -0.85 and c.x >= 0),
        ("Quarter_L", lambda c: -1.66 < c.y <= -0.85 and c.x < 0),
        ("Bumper_R",  lambda c: c.y <= -1.66),
    ]


def build_body_panels(coll, pivot):
    """Hull -> bake -> split into separate painted panels with thickness."""
    hull = _build_hull(coll)
    cutters = _cut_openings(hull, coll)
    utils.bake_modifiers(hull)
    for c in cutters:
        mesh = c.data
        bpy.data.objects.remove(c, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)

    panels = utils.split_into_panels(hull, _panel_defs(), "Cowl", coll)
    paint = materials.car_paint()
    for p in panels:
        utils.add_solidify(p, 0.015)         # real sheet-metal thickness
        utils.add_bevel(p, 0.0025, 2, 30)    # softened panel edges
        utils.assign_material(p, paint)
        utils.shade_smooth(p, 40)
        utils.parent_keep_transform(p, pivot)
    return panels


# ---------------------------------------------------------------------------
# Aero & hardware (all pivots LOCAL now)
# ---------------------------------------------------------------------------

def build_front_lip(coll, parent):
    lip = utils.make_box("FrontLip", size=(1.50, 0.34, 0.05),
                         location=(0, LENGTH / 2 - 0.14, SILL_Z + 0.03),
                         coll=coll)
    utils.add_bevel(lip, 0.012, 3)
    utils.assign_material(lip, materials.carbon_fiber())
    utils.parent_keep_transform(lip, parent)
    return lip


def build_diffuser(coll, parent):
    parts = []
    plane = utils.make_box("DiffuserPlane", size=(1.30, 0.55, 0.025),
                           location=(0, -LENGTH / 2 + 0.24, SILL_Z + 0.06),
                           coll=coll)
    plane.rotation_euler.x = math.radians(-12)
    parts.append(plane)
    for i in range(5):
        strake = utils.make_box(f"DiffuserStrake_{i}",
                                size=(0.012, 0.50, 0.11),
                                location=(-0.52 + i * 0.26,
                                          -LENGTH / 2 + 0.24,
                                          SILL_Z + 0.11), coll=coll)
        strake.rotation_euler.x = math.radians(-12)
        parts.append(strake)
    cf = materials.carbon_fiber()
    for p in parts:
        utils.assign_material(p, cf)
        utils.parent_keep_transform(p, parent)
    return parts


def build_wing(coll, parent):
    """GT wing. The airfoil is lofted in LOCAL coordinates around its own
    origin, so the angle-of-attack rotation pivots on the wing itself."""
    wing_y = -LENGTH / 2 + 0.18
    wing_z = DECK_Z + 0.26
    chord, span = 0.26, 1.42
    parts = []

    foil = [(0.00, 0.000), (0.15, 0.018), (0.45, 0.026), (0.80, 0.012),
            (1.00, -0.004), (0.80, -0.010), (0.45, -0.012), (0.15, -0.008),
            (0.00, 0.000)]
    secs = [[(x, (0.5 - cy) * chord, cz) for (cy, cz) in foil]
            for x in (-span / 2, span / 2)]
    plane = utils.loft_sections("WingPlane", secs, close_ends=True,
                                coll=coll)
    plane.location = (0, wing_y, wing_z)
    plane.rotation_euler.x = math.radians(8)     # pivots locally now
    utils.add_subsurf(plane, 1)
    utils.assign_material(plane, materials.carbon_fiber())
    parts.append(plane)

    for side in (-1, 1):
        tag = 'L' if side < 0 else 'R'
        up = utils.make_box(f"WingUpright_{tag}", size=(0.035, 0.14, 0.27),
                            location=(side * 0.48, wing_y + 0.02,
                                      DECK_Z + 0.115), coll=coll)
        up.rotation_euler.x = math.radians(-10)
        utils.assign_material(up, materials.anodized_black())
        parts.append(up)
        ep = utils.make_box(f"WingEndplate_{tag}", size=(0.012, 0.30, 0.15),
                            location=(side * span / 2, wing_y, wing_z),
                            coll=coll)
        utils.assign_material(ep, materials.carbon_fiber())
        parts.append(ep)

    for p in parts:
        utils.parent_keep_transform(p, parent)
    return parts


def build_exhaust(coll, parent):
    tips = []
    for side in (-1, 1):
        for k in (0, 1):
            tip = utils.make_cylinder(
                f"ExhaustTip_{'L' if side < 0 else 'R'}{k}",
                radius=0.042, depth=0.16, segments=32,
                location=(side * (0.42 + k * 0.11), -LENGTH / 2 + 0.06,
                          SILL_Z + 0.10),
                rotation=(math.pi / 2, 0, 0), coll=coll)
            utils.add_solidify(tip, -0.004)
            utils.assign_material(tip, materials.chrome())
            utils.parent_keep_transform(tip, parent)
            tips.append(tip)
    return tips


# ---------------------------------------------------------------------------
# Lights — flush-mounted now, not poking spheres
# ---------------------------------------------------------------------------

def build_lights(coll, parent):
    out = {"head": [], "tail": [], "blink": []}

    for side in (-1, 1):
        tag = 'L' if side < 0 else 'R'
        # NB-style flush oval lamp sunk into the nose
        housing = utils.make_uv_sphere(f"HeadlightHousing_{tag}",
                                       radius=0.105,
                                       location=(side * 0.50, 1.78, 0.515),
                                       coll=coll)
        housing.scale = (1.45, 0.42, 0.62)
        housing.rotation_euler = (math.radians(-18), 0,
                                  math.radians(-10 * side))
        utils.assign_material(housing, materials.headlight_housing())
        utils.parent_keep_transform(housing, parent)

        led = utils.make_box(f"HeadlightLED_{tag}", size=(0.15, 0.02, 0.016),
                             location=(side * 0.50, 1.82, 0.52), coll=coll)
        led.rotation_euler.z = math.radians(-10 * side)
        utils.assign_material(led, materials.headlight_led())
        utils.parent_keep_transform(led, parent)
        out["head"].append(led)

        cover = utils.make_uv_sphere(f"HeadlightCover_{tag}", radius=0.108,
                                     location=(side * 0.50, 1.785, 0.515),
                                     coll=coll)
        cover.scale = (1.45, 0.42, 0.62)
        cover.rotation_euler = (math.radians(-18), 0,
                                math.radians(-10 * side))
        utils.assign_material(cover, materials.glass((0.9, 0.9, 0.9),
                                                     "HeadlightGlass"))
        utils.parent_keep_transform(cover, parent)

        blink = utils.make_uv_sphere(f"BlinkerF_{tag}", radius=0.032,
                                     location=(side * 0.60, 1.80, 0.40),
                                     coll=coll)
        blink.scale = (1.0, 0.45, 1.0)
        utils.assign_material(blink, materials.blinker_amber())
        utils.parent_keep_transform(blink, parent)
        out["blink"].append(blink)

    for side in (-1, 1):
        tag = 'L' if side < 0 else 'R'
        for k, x_in in enumerate((0.60, 0.42)):
            lamp = utils.make_cylinder(
                f"Taillight_{tag}{k}", radius=0.055, depth=0.03, segments=32,
                location=(side * x_in, -LENGTH / 2 + 0.045, 0.56),
                rotation=(math.pi / 2, 0, 0), coll=coll)
            utils.assign_material(lamp, materials.taillight_red())
            utils.parent_keep_transform(lamp, parent)
            out["tail"].append(lamp)
            lens = utils.make_cylinder(
                f"TaillightLens_{tag}{k}", radius=0.063, depth=0.012,
                segments=32,
                location=(side * x_in, -LENGTH / 2 + 0.028, 0.56),
                rotation=(math.pi / 2, 0, 0), coll=coll)
            utils.assign_material(lens, materials.taillight_lens())
            utils.parent_keep_transform(lens, parent)
        blink = utils.make_cylinder(
            f"BlinkerR_{tag}", radius=0.030, depth=0.025, segments=24,
            location=(side * 0.27, -LENGTH / 2 + 0.040, 0.54),
            rotation=(math.pi / 2, 0, 0), coll=coll)
        utils.assign_material(blink, materials.blinker_amber())
        utils.parent_keep_transform(blink, parent)
        out["blink"].append(blink)
    return out


# ---------------------------------------------------------------------------
# Glass & soft top
# ---------------------------------------------------------------------------

def build_windshield(coll, parent):
    secs = []
    for t in (0.0, 0.5, 1.0):
        y = WS_BASE_Y + (WS_TOP_Y - WS_BASE_Y) * t
        z = WS_BASE_Z + (WS_TOP_Z - WS_BASE_Z) * t
        w = 0.60 - 0.07 * t
        secs.append([(-w, y, z), (-w * 0.5, y, z + 0.018), (0, y, z + 0.024),
                     (w * 0.5, y, z + 0.018), (w, y, z)])
    glass = utils.loft_sections("Windshield", secs, close_ends=False,
                                coll=coll)
    utils.add_solidify(glass, 0.006)
    utils.assign_material(glass, materials.glass())
    utils.parent_keep_transform(glass, parent)

    # A-pillar frame rails + header bar
    header = utils.make_box("WSHeader", size=(1.10, 0.05, 0.035),
                            location=(0, WS_TOP_Y, WS_TOP_Z + 0.005),
                            coll=coll)
    utils.assign_material(header, materials.anodized_black())
    utils.parent_keep_transform(header, parent)
    for side in (-1, 1):
        rail = utils.make_cylinder(f"APillar_{'L' if side < 0 else 'R'}",
                                   radius=0.022, depth=0.50, segments=12,
                                   coll=coll)
        rail.location = (side * 0.565, (WS_BASE_Y + WS_TOP_Y) / 2,
                         (WS_BASE_Z + WS_TOP_Z) / 2)
        rail.rotation_euler.x = math.atan2(WS_BASE_Y - WS_TOP_Y,
                                           WS_TOP_Z - WS_BASE_Z)
        utils.assign_material(rail, materials.car_paint())
        utils.parent_keep_transform(rail, parent)
    return glass


def build_soft_top(coll, parent):
    """Canvas roof from the windscreen header down to the rear deck, with
    a proper arched silhouette and the 'Fold' open/close shape key."""
    hinge = Vector((0.0, -0.85, BELT_Z + 0.02))
    front_y = WS_TOP_Y
    n_secs, n_pts = 11, 11
    secs = []
    for i in range(n_secs):
        t = i / (n_secs - 1)
        y = front_y + (hinge.y - front_y) * t
        # roofline: starts at the header, gentle crown, sweeps down to deck
        ridge = WS_TOP_Z + 0.02 - 0.36 * (t ** 1.6)
        w = 0.565 - 0.09 * t
        rail_z = BELT_Z + 0.03
        ring = []
        for j in range(n_pts):
            u = j / (n_pts - 1)
            x = -w + 2 * w * u
            arch = math.sin(u * math.pi) ** 0.8     # flat-ish crown
            ring.append((x, y, rail_z + (ridge - rail_z) * arch))
        secs.append(ring)
    top = utils.loft_sections("SoftTop", secs, close_ends=False, coll=coll)
    utils.add_solidify(top, 0.012)
    utils.add_subsurf(top, 1)
    utils.assign_material(top, materials.soft_top_fabric())
    utils.parent_keep_transform(top, parent)

    top.shape_key_add(name="Basis")
    fold = top.shape_key_add(name="Fold")
    for v, kv in zip(top.data.vertices, fold.data):
        co = v.co.copy()
        reach = max(0.0, (co.y - hinge.y) / (front_y - hinge.y))
        ang = math.radians(150) * reach
        rel = Vector((0, co.y - hinge.y, co.z - hinge.z))
        rot_y = rel.y * math.cos(ang) - rel.z * math.sin(ang)
        rot_z = rel.y * math.sin(ang) + rel.z * math.cos(ang)
        kv.co = Vector((co.x * (1 - 0.25 * reach),
                        hinge.y + rot_y * (1 - 0.55 * reach),
                        max(BELT_Z - 0.04,
                            hinge.z + rot_z * (1 - 0.55 * reach))))
    fold.value = 0.0
    return top


def build_mirrors(coll, parent):
    for side in (-1, 1):
        tag = 'L' if side < 0 else 'R'
        stalk = utils.make_box(f"MirrorStalk_{tag}", size=(0.05, 0.02, 0.05),
                               location=(side * 0.875, 0.44, BELT_Z + 0.03),
                               coll=coll)
        utils.assign_material(stalk, materials.car_paint())
        utils.parent_keep_transform(stalk, parent)
        head = utils.make_uv_sphere(f"MirrorHead_{tag}", radius=0.052,
                                    location=(side * 0.92, 0.44,
                                              BELT_Z + 0.07), coll=coll)
        head.scale = (1.0, 0.45, 0.7)
        utils.assign_material(head, materials.car_paint())
        utils.parent_keep_transform(head, parent)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build(root):
    coll = utils.sub_collection("Body")
    pivot = utils.new_empty("BodyPivot", (0, 0, 0), coll)
    utils.parent_keep_transform(pivot, root)

    panels = build_body_panels(coll, pivot)
    build_front_lip(coll, pivot)
    build_diffuser(coll, pivot)
    build_wing(coll, pivot)
    exhaust_tips = build_exhaust(coll, pivot)
    lights = build_lights(coll, pivot)
    build_windshield(coll, pivot)
    soft_top = build_soft_top(coll, pivot)
    build_mirrors(coll, pivot)

    return {
        "body": pivot,            # DOF target / parent handle
        "panels": panels,
        "exhaust_tips": exhaust_tips,
        "lights": lights,
        "soft_top": soft_top,
    }
