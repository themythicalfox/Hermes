"""
body.py — procedural NB Miata widebody shell and exterior hardware.

Approach: the main body is a LOFT. We define half cross-section profiles
(x = half-width, z = height) at stations along the car's length, mirror them,
and bridge them into a watertight skin. A Subdivision Surface modifier turns
the coarse cage into the NB's smooth flowing curves; widebody flares are
pushed out vertex-by-vertex with a smooth falloff around each wheel arch,
then the arches themselves are cut with live boolean cylinders.

Hardware (wing, diffuser, exhaust, lights, soft top) are separate parented
objects so animation.py can wiggle/illuminate them independently.

Axes:  +Y nose, +X driver right, +Z up, ground at z=0.
"""

import math
import bmesh
from mathutils import Vector

from . import utils, materials
from .utils import (WHEELBASE, LENGTH, WIDTH, HEIGHT, TRACK, WHEEL_R,
                    RIDE_HEIGHT, FRONT_AXLE_Y, REAR_AXLE_Y)

HALF_W = WIDTH / 2.0 - 0.10      # half width before flares
SILL_Z = RIDE_HEIGHT             # bottom of the rockers
BELT_Z = 0.78                    # beltline (top of doors)
HOOD_Z = 0.82
DECK_Z = 0.84                    # rear deck


def _profile(y, half_w, sill, belt, top, tumblehome=0.10, n_side=4):
    """Build one half cross-section (driver side, +X) bottom -> centreline top.

    Points run: floor centre -> floor edge -> sill -> body side (bulged) ->
    beltline (tucked in by `tumblehome`) -> top centre. Constant point count
    (8) so every section bridges cleanly.
    """
    pts = []
    pts.append((0.0,        y, sill + 0.02))                  # floor centre
    pts.append((half_w*0.80, y, sill))                        # floor edge
    pts.append((half_w*0.98, y, sill + 0.06))                 # sill lip
    # body side: subtle outward bulge at mid height (Miata hips)
    pts.append((half_w*1.00, y, sill + 0.20))
    pts.append((half_w*1.02, y, (sill + belt) * 0.55))        # widest point
    pts.append((half_w*(1.0 - tumblehome*0.5), y, belt))      # beltline
    # shoulder roll-over onto hood/deck
    pts.append((half_w*0.55, y, top - 0.01))
    pts.append((0.0,        y, top))                          # centreline
    return pts


def _mirror_section(half):
    """half (centre->out implicitly reversed) -> full loop, -X to +X to -X."""
    # half runs centre-bottom .. centre-top on +X; build full ordered ring:
    # start at top centre, sweep down +X side, across the floor, up -X side.
    plus = list(reversed(half))                       # top-centre .. floor-centre
    minus = [(-x, y, z) for (x, y, z) in half[1:-1]]  # floor .. top, skip centres
    return plus + minus + [plus[0]]                   # closed ring (repeat 1st)


def _body_sections():
    """Stations nose -> tail with NB-ish proportions."""
    nose_y = LENGTH / 2.0
    tail_y = -LENGTH / 2.0
    secs = []

    def add(y, w_scale, sill, top):
        half = _profile(y, HALF_W * w_scale, sill, BELT_Z, top)
        secs.append(_mirror_section(half))

    # nose tip (narrow, low — pop-up-less NB front)
    add(nose_y - 0.02, 0.55, SILL_Z + 0.16, 0.55)
    add(nose_y - 0.18, 0.78, SILL_Z + 0.08, 0.62)
    # front overhang / bumper mass
    add(nose_y - 0.40, 0.92, SILL_Z + 0.02, 0.70)
    # front axle: hood rising
    add(FRONT_AXLE_Y,  1.00, SILL_Z, 0.78)
    # cowl / windscreen base — hood peaks
    add(FRONT_AXLE_Y - 0.55, 1.00, SILL_Z, HOOD_Z)
    # door section (widest = cabin)
    add(0.15, 1.00, SILL_Z, BELT_Z + 0.02)
    add(-0.45, 1.00, SILL_Z, BELT_Z + 0.02)
    # rear axle: haunches swell
    add(REAR_AXLE_Y,        1.02, SILL_Z, DECK_Z)
    add(REAR_AXLE_Y - 0.30, 0.96, SILL_Z + 0.02, DECK_Z - 0.02)
    # tail / rear bumper
    add(tail_y + 0.18, 0.82, SILL_Z + 0.06, DECK_Z - 0.06)
    add(tail_y + 0.02, 0.62, SILL_Z + 0.16, DECK_Z - 0.14)
    return secs


def _flare_fenders(obj):
    """Push verts outward around each wheel arch with a smooth radial falloff
    — this is the bolt-on-style widebody from the green reference car."""
    flare_amount = 0.085      # metres of extra width at the arch peak
    flare_radius = 0.62       # influence radius around the hub
    hub_z = WHEEL_R
    me = obj.data
    for v in me.vertices:
        for axle_y in (FRONT_AXLE_Y, REAR_AXLE_Y):
            d = math.hypot(v.co.y - axle_y, v.co.z - hub_z)
            if d < flare_radius and abs(v.co.x) > HALF_W * 0.55:
                # smoothstep falloff, stronger low on the body
                t = 1.0 - (d / flare_radius)
                t = t * t * (3 - 2 * t)
                v.co.x += math.copysign(flare_amount * t, v.co.x)


def build_body(coll):
    """The painted shell, returned for material/parenting."""
    body = utils.loft_sections("Body", _body_sections(), coll=coll)
    _flare_fenders(body)
    utils.add_subsurf(body, levels=2, render_levels=3)
    utils.assign_material(body, materials.car_paint())
    utils.shade_smooth(body, 60)

    # --- wheel arch cut-outs (live booleans, tight to the tyre) ----------
    arch_r = WHEEL_R + 0.045
    for tag, axle_y in (("F", FRONT_AXLE_Y), ("R", REAR_AXLE_Y)):
        cutter = utils.make_cylinder(
            f"ArchCutter_{tag}", radius=arch_r, depth=WIDTH * 1.2, segments=48,
            location=(0, axle_y, WHEEL_R),
            rotation=(0, math.pi / 2, 0), coll=coll)
        utils.boolean_cut(body, cutter)

    # --- cockpit opening (so the interior is visible) ---------------------
    cockpit = utils.make_box(
        "CockpitCutter",
        size=(WIDTH * 0.72, 1.55, 0.6),
        location=(0, -0.35, BELT_Z + 0.15), coll=coll)
    utils.boolean_cut(body, cockpit)

    # --- front intake mouth + lower grille --------------------------------
    mouth = utils.make_box(
        "IntakeCutter", size=(0.62, 0.30, 0.16),
        location=(0, LENGTH / 2 - 0.04, 0.34), coll=coll)
    utils.boolean_cut(body, mouth)
    for side in (-1, 1):   # brake-duct intakes
        duct = utils.make_box(
            f"DuctCutter_{'L' if side < 0 else 'R'}",
            size=(0.22, 0.25, 0.10),
            location=(side * 0.55, LENGTH / 2 - 0.05, 0.22), coll=coll)
        utils.boolean_cut(body, duct)
    return body


# ---------------------------------------------------------------------------
# Aero & hardware
# ---------------------------------------------------------------------------

def build_front_lip(coll, parent):
    lip = utils.make_box("FrontLip", size=(1.45, 0.30, 0.045),
                         location=(0, LENGTH / 2 - 0.10, RIDE_HEIGHT + 0.02),
                         coll=coll)
    utils.add_bevel(lip, 0.012, 3)
    utils.assign_material(lip, materials.carbon_fiber())
    utils.parent_keep_transform(lip, parent)
    return lip


def build_diffuser(coll, parent):
    """Rear diffuser: angled main plane + five vertical strakes (Image 2)."""
    parts = []
    plane = utils.make_box("DiffuserPlane", size=(1.30, 0.55, 0.025),
                           location=(0, -LENGTH / 2 + 0.22, RIDE_HEIGHT + 0.05),
                           coll=coll)
    plane.rotation_euler.x = math.radians(-12)   # kicks up toward the tail
    parts.append(plane)
    for i in range(5):
        x = -0.52 + i * 0.26
        strake = utils.make_box(f"DiffuserStrake_{i}", size=(0.012, 0.50, 0.11),
                                location=(x, -LENGTH / 2 + 0.22,
                                          RIDE_HEIGHT + 0.10), coll=coll)
        strake.rotation_euler.x = math.radians(-12)
        parts.append(strake)
    cf = materials.carbon_fiber()
    for p in parts:
        utils.assign_material(p, cf)
        utils.parent_keep_transform(p, parent)
    return parts


def build_wing(coll, parent):
    """Tall fixed GT wing inspired by the blue reference: swan uprights,
    carbon-top airfoil main plane, small endplates."""
    wing_z = DECK_Z + 0.28
    wing_y = -LENGTH / 2 + 0.16
    parts = []

    # main plane: lofted airfoil (flat bottom-ish, cambered top)
    chord, span, th = 0.26, 1.42, 0.030
    foil = [  # (y_frac along chord, z offset) — simple cambered section
        (0.00, 0.000), (0.15, 0.018), (0.45, 0.026), (0.80, 0.012),
        (1.00, -0.004), (0.80, -0.010), (0.45, -0.012), (0.15, -0.008),
        (0.00, 0.000),
    ]
    secs = []
    for x in (-span / 2, span / 2):
        secs.append([(x, wing_y + (1 - cy) * chord - chord / 2, wing_z + cz)
                     for (cy, cz) in foil])
    plane = utils.loft_sections("WingPlane", secs, close_ends=True, coll=coll)
    plane.rotation_euler.x = math.radians(8)     # angle of attack
    utils.add_subsurf(plane, 1)
    utils.assign_material(plane, materials.carbon_fiber())
    parts.append(plane)

    for side in (-1, 1):     # swan-neck uprights
        up = utils.make_box(f"WingUpright_{'L' if side < 0 else 'R'}",
                            size=(0.035, 0.16, 0.30),
                            location=(side * 0.48, wing_y + 0.03,
                                      DECK_Z + 0.13), coll=coll)
        up.rotation_euler.x = math.radians(-12)
        utils.assign_material(up, materials.anodized_black())
        parts.append(up)
        ep = utils.make_box(f"WingEndplate_{'L' if side < 0 else 'R'}",
                            size=(0.012, 0.30, 0.16),
                            location=(side * span / 2, wing_y, wing_z),
                            coll=coll)
        utils.assign_material(ep, materials.carbon_fiber())
        parts.append(ep)

    for p in parts:
        utils.parent_keep_transform(p, parent)
    return parts


def build_exhaust(coll, parent):
    """Quad exhaust: dual chrome tips each side. Returns the tip objects so
    animation.py can attach the idle-jiggle noise and park the heat haze."""
    tips = []
    tip_y = -LENGTH / 2 + 0.04
    for side in (-1, 1):
        for k in (0, 1):
            x = side * (0.42 + k * 0.11)
            tip = utils.make_cylinder(
                f"ExhaustTip_{'L' if side < 0 else 'R'}{k}",
                radius=0.042, depth=0.16, segments=32,
                location=(x, tip_y, RIDE_HEIGHT + 0.10),
                rotation=(math.pi / 2, 0, 0), coll=coll)
            utils.add_solidify(tip, -0.004)      # visible pipe wall
            utils.assign_material(tip, materials.chrome())
            utils.parent_keep_transform(tip, parent)
            tips.append(tip)
    return tips


# ---------------------------------------------------------------------------
# Lights
# ---------------------------------------------------------------------------

def build_lights(coll, parent):
    """LED headlights, twin circular taillights per side (blue reference),
    amber blinkers. Returns a dict of element lists for animation.py."""
    out = {"head": [], "tail": [], "blink": []}

    # headlights: teardrop housings + emissive LED bar
    for side in (-1, 1):
        tag = 'L' if side < 0 else 'R'
        housing = utils.make_uv_sphere(f"HeadlightHousing_{tag}", radius=0.115,
                                       location=(side * 0.58, LENGTH / 2 - 0.14,
                                                 0.55), coll=coll)
        housing.scale = (1.5, 0.5, 0.8)
        utils.assign_material(housing, materials.headlight_housing())
        utils.parent_keep_transform(housing, parent)

        led = utils.make_box(f"HeadlightLED_{tag}", size=(0.16, 0.02, 0.018),
                             location=(side * 0.58, LENGTH / 2 - 0.085, 0.56),
                             coll=coll)
        utils.assign_material(led, materials.headlight_led())
        utils.parent_keep_transform(led, parent)
        out["head"].append(led)

        cover = utils.make_uv_sphere(f"HeadlightCover_{tag}", radius=0.118,
                                     location=(side * 0.58, LENGTH / 2 - 0.13,
                                               0.55), coll=coll)
        cover.scale = (1.5, 0.5, 0.8)
        utils.assign_material(cover, materials.glass((0.9, 0.9, 0.9),
                                                     "HeadlightGlass"))
        utils.parent_keep_transform(cover, parent)

        blink = utils.make_uv_sphere(f"BlinkerF_{tag}", radius=0.035,
                                     location=(side * 0.76, LENGTH / 2 - 0.16,
                                               0.50), coll=coll)
        blink.scale = (1.0, 0.5, 1.0)
        utils.assign_material(blink, materials.blinker_amber())
        utils.parent_keep_transform(blink, parent)
        out["blink"].append(blink)

    # taillights: two stacked-circle lamps each side (from the blue car)
    for side in (-1, 1):
        tag = 'L' if side < 0 else 'R'
        for k, x_in in enumerate((0.66, 0.46)):
            lamp = utils.make_cylinder(
                f"Taillight_{tag}{k}", radius=0.058, depth=0.03, segments=32,
                location=(side * x_in, -LENGTH / 2 + 0.035, 0.62),
                rotation=(math.pi / 2, 0, 0), coll=coll)
            utils.assign_material(lamp, materials.taillight_red())
            utils.parent_keep_transform(lamp, parent)
            out["tail"].append(lamp)
            lens = utils.make_cylinder(
                f"TaillightLens_{tag}{k}", radius=0.066, depth=0.012,
                segments=32,
                location=(side * x_in, -LENGTH / 2 + 0.018, 0.62),
                rotation=(math.pi / 2, 0, 0), coll=coll)
            utils.assign_material(lens, materials.taillight_lens())
            utils.parent_keep_transform(lens, parent)
        blink = utils.make_cylinder(
            f"BlinkerR_{tag}", radius=0.032, depth=0.025, segments=24,
            location=(side * 0.30, -LENGTH / 2 + 0.030, 0.60),
            rotation=(math.pi / 2, 0, 0), coll=coll)
        utils.assign_material(blink, materials.blinker_amber())
        utils.parent_keep_transform(blink, parent)
        out["blink"].append(blink)
    return out


# ---------------------------------------------------------------------------
# Glass & soft top
# ---------------------------------------------------------------------------

def build_windshield(coll, parent):
    """Raked windscreen + frame."""
    base_y, top_y = FRONT_AXLE_Y - 0.62, FRONT_AXLE_Y - 0.92
    base_z, top_z = HOOD_Z, HEIGHT - 0.02
    secs = []
    for t in (0.0, 1.0):
        y = base_y + (top_y - base_y) * t
        z = base_z + (top_z - base_z) * t
        w = 0.62 - 0.06 * t
        secs.append([(-w, y, z), (-w * 0.5, y, z + 0.015), (0, y, z + 0.02),
                     (w * 0.5, y, z + 0.015), (w, y, z)])
    glass = utils.loft_sections("Windshield", secs, close_ends=False,
                                coll=coll)
    utils.add_solidify(glass, 0.006)
    utils.assign_material(glass, materials.glass())
    utils.parent_keep_transform(glass, parent)

    frame = utils.make_box("WindshieldFrame", size=(1.30, 0.04, 0.035),
                           location=(0, top_y, top_z + 0.01), coll=coll)
    frame.rotation_euler.x = math.radians(-25)
    utils.assign_material(frame, materials.anodized_black())
    utils.parent_keep_transform(frame, parent)
    return glass


def build_soft_top(coll, parent):
    """Black canvas soft top with a 'Fold' shape key.

    Basis = closed, taut over the cabin. 'Fold' = collapsed flat behind the
    seats. animation.py keyframes the shape-key value for open/close; the
    fold path rotates each section back around a hinge at the rear deck.
    """
    hinge = Vector((0.0, -0.85, BELT_Z + 0.02))   # rear deck pivot
    front_y = FRONT_AXLE_Y - 0.92                  # meets windshield header
    n_secs, n_pts = 9, 9
    secs = []
    for i in range(n_secs):
        t = i / (n_secs - 1)
        y = front_y + (hinge.y - front_y) * t
        # roof arc: peaks just behind the windscreen, falls to the deck
        peak = HEIGHT - 0.02 + 0.035 * math.sin(t * math.pi)
        base_z = BELT_Z + 0.02 + (peak - BELT_Z - 0.02) * (1 - t * 0.15)
        w = 0.60 - 0.10 * t
        ring = []
        for j in range(n_pts):
            u = j / (n_pts - 1)            # 0..1 across the roof, -X to +X
            x = -w + 2 * w * u
            arch = math.sin(u * math.pi)   # side rails low, centre high
            z = BELT_Z + 0.04 + (base_z - BELT_Z - 0.04) * arch
            ring.append((x, y, z))
        secs.append(ring)
    top = utils.loft_sections("SoftTop", secs, close_ends=False, coll=coll)
    utils.add_solidify(top, 0.012)
    utils.add_subsurf(top, 2)
    utils.assign_material(top, materials.soft_top_fabric())
    utils.parent_keep_transform(top, parent)

    # --- shape key: folded down behind the seats --------------------------
    top.shape_key_add(name="Basis")
    fold = top.shape_key_add(name="Fold")
    for v, kv in zip(top.data.vertices, fold.data):
        co = v.co.copy()
        # how far forward of the hinge this vert sits (0 at hinge, 1 at front)
        reach = max(0.0, (co.y - hinge.y) / (front_y - hinge.y))
        # rotate back around the hinge, accordion-compressing as it goes
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
        stalk = utils.make_box(f"MirrorStalk_{tag}", size=(0.05, 0.02, 0.06),
                               location=(side * (HALF_W + 0.02),
                                         FRONT_AXLE_Y - 0.70, BELT_Z + 0.06),
                               coll=coll)
        utils.assign_material(stalk, materials.car_paint())
        utils.parent_keep_transform(stalk, parent)
        head = utils.make_uv_sphere(f"MirrorHead_{tag}", radius=0.055,
                                    location=(side * (HALF_W + 0.07),
                                              FRONT_AXLE_Y - 0.70,
                                              BELT_Z + 0.10), coll=coll)
        head.scale = (1.0, 0.45, 0.7)
        utils.assign_material(head, materials.car_paint())
        utils.parent_keep_transform(head, parent)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build(root):
    """Build the whole exterior. Returns a dict of animatable handles."""
    coll = utils.sub_collection("Body")
    body = build_body(coll)
    utils.parent_keep_transform(body, root)

    build_front_lip(coll, body)
    build_diffuser(coll, body)
    build_wing(coll, body)
    exhaust_tips = build_exhaust(coll, body)
    lights = build_lights(coll, body)
    build_windshield(coll, body)
    soft_top = build_soft_top(coll, body)
    build_mirrors(coll, body)

    return {
        "body": body,
        "exhaust_tips": exhaust_tips,
        "lights": lights,
        "soft_top": soft_top,
    }
