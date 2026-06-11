"""
interior.py — minimalist racing-luxury cockpit.

Matches the reference images:
  * Image 3: blue Alcantara buckets w/ black leather bolsters, thick
    Alcantara wheel with metal hub, tall gated shifter on the tunnel
  * Image 4: E-ink style pixel gauge cluster
  * Image 5: Sony-esque black anodized control panel — rotary knobs,
    toggle switches (one orange), fine machined detailing

Everything parents to one 'Interior' empty so the whole cockpit inherits
the body's idle vibration.
"""

import math
from mathutils import Vector

from . import utils, materials
from .utils import FRONT_AXLE_Y

FLOOR_Z   = 0.18         # cabin floor height
DASH_Y    = 0.85         # dashboard face (forward of seats)
SEAT_Y    = -0.45        # seat reference
TUNNEL_W  = 0.24


# ---------------------------------------------------------------------------
# Tub / dash / console
# ---------------------------------------------------------------------------

def build_tub(coll, parent):
    """Cabin floor + transmission tunnel + door cards."""
    floor = utils.make_box("CabinFloor", size=(1.30, 1.60, 0.03),
                           location=(0, -0.30, FLOOR_Z), coll=coll)
    utils.assign_material(floor, materials.alcantara("CarpetBlack",
                                                     (0.01, 0.01, 0.012)))
    utils.parent_keep_transform(floor, parent)

    tunnel = utils.make_box("Tunnel", size=(TUNNEL_W, 1.60, 0.22),
                            location=(0, -0.30, FLOOR_Z + 0.11), coll=coll)
    utils.add_bevel(tunnel, 0.02, 3)
    utils.assign_material(tunnel, materials.leather())
    utils.parent_keep_transform(tunnel, parent)

    for side in (-1, 1):
        card = utils.make_box(f"DoorCard_{'L' if side < 0 else 'R'}",
                              size=(0.03, 1.10, 0.42),
                              location=(side * 0.66, -0.25,
                                        FLOOR_Z + 0.30), coll=coll)
        utils.add_bevel(card, 0.012, 2)
        utils.assign_material(card, materials.alcantara())
        # leather armrest band across the middle of the card (local coords:
        # the card mesh is centred on its object origin)
        utils.assign_to_faces(card, materials.leather(),
                              lambda c: abs(c.z) < 0.08)
        utils.parent_keep_transform(card, parent)
    return floor


def build_dashboard(coll, parent):
    """Anodized slab dash with carbon topper and recessed vents."""
    dash = utils.make_box("Dashboard", size=(1.30, 0.30, 0.24),
                          location=(0, DASH_Y, 0.62), coll=coll)
    utils.add_bevel(dash, 0.02, 3)
    utils.assign_material(dash, materials.anodized_metal())
    utils.parent_keep_transform(dash, parent)

    topper = utils.make_box("DashTopper", size=(1.30, 0.32, 0.025),
                            location=(0, DASH_Y, 0.745), coll=coll)
    utils.add_bevel(topper, 0.01, 2)
    utils.assign_material(topper, materials.carbon_fiber())
    utils.parent_keep_transform(topper, parent)

    # vent grilles: recessed boxes with horizontal slats for real depth
    for side in (-1, 1):
        tag = 'L' if side < 0 else 'R'
        recess = utils.make_box(f"VentRecess_{tag}", size=(0.16, 0.04, 0.07),
                                location=(side * 0.52, DASH_Y - 0.14, 0.66),
                                coll=coll)
        utils.assign_material(recess, materials.dark_plastic())
        utils.parent_keep_transform(recess, parent)
        for i in range(4):
            slat = utils.make_box(f"VentSlat_{tag}{i}",
                                  size=(0.15, 0.012, 0.008),
                                  location=(side * 0.52, DASH_Y - 0.155,
                                            0.635 + i * 0.018), coll=coll)
            utils.assign_material(slat, materials.anodized_black())
            utils.parent_keep_transform(slat, parent)

    # precise screw heads along the dash face (machined look, Image 5)
    for i in range(6):
        x = -0.55 + i * 0.22
        screw = utils.make_cylinder(f"DashScrew_{i}", radius=0.005,
                                    depth=0.003, segments=12,
                                    location=(x, DASH_Y - 0.152, 0.535),
                                    rotation=(math.pi / 2, 0, 0), coll=coll)
        utils.assign_material(screw, materials.polished_lip())
        utils.parent_keep_transform(screw, parent)
    return dash


def build_displays(coll, parent):
    """E-ink gauge cluster behind the wheel + small console readout."""
    eink = materials.eink_display()
    cluster = utils.make_plane("GaugeCluster", 0.30, 0.115,
                               location=(-0.35, DASH_Y - 0.155, 0.655),
                               rotation=(math.radians(80), 0, math.pi),
                               coll=coll)
    utils.assign_material(cluster, eink)
    utils.parent_keep_transform(cluster, parent)

    bezel = utils.make_box("ClusterBezel", size=(0.33, 0.015, 0.145),
                           location=(-0.35, DASH_Y - 0.145, 0.655), coll=coll)
    utils.add_bevel(bezel, 0.006, 2)
    utils.assign_material(bezel, materials.anodized_black())
    utils.parent_keep_transform(bezel, parent)

    console_disp = utils.make_plane("ConsoleDisplay", 0.14, 0.07,
                                    location=(0, DASH_Y - 0.158, 0.62),
                                    rotation=(math.radians(75), 0, math.pi),
                                    coll=coll)
    utils.assign_material(console_disp, eink)
    utils.parent_keep_transform(console_disp, parent)
    return [cluster, console_disp]


# ---------------------------------------------------------------------------
# Sony-style control panel (Image 5)
# ---------------------------------------------------------------------------

def build_control_panel(coll, parent):
    """Black anodized panel on the centre stack: 3 rotary knobs with
    knurled edges, a row of 7 toggle switches (one orange), screw heads."""
    panel = utils.make_box("ControlPanel", size=(0.26, 0.02, 0.20),
                           location=(0, DASH_Y - 0.16, 0.46), coll=coll)
    utils.add_bevel(panel, 0.005, 2)
    utils.assign_material(panel, materials.anodized_black())
    utils.parent_keep_transform(panel, parent)

    # rotary knobs — knurling faked with a high-segment cylinder + aniso mat
    for i in range(3):
        x = -0.08 + i * 0.08
        knob = utils.make_cylinder(f"Knob_{i}", radius=0.022, depth=0.022,
                                   segments=48,
                                   location=(x, DASH_Y - 0.18, 0.51),
                                   rotation=(math.pi / 2, 0, 0), coll=coll)
        utils.assign_material(knob, materials.anodized_black())
        utils.parent_keep_transform(knob, parent)
        marker = utils.make_box(f"KnobMark_{i}", size=(0.003, 0.006, 0.012),
                                location=(x, DASH_Y - 0.192, 0.518),
                                coll=coll)
        utils.assign_material(marker, materials.white_lettering())
        utils.parent_keep_transform(marker, parent)

    # toggle switch row — index 3 gets the orange accent (Image 5)
    for i in range(7):
        x = -0.105 + i * 0.035
        base = utils.make_cylinder(f"ToggleBase_{i}", radius=0.008,
                                   depth=0.008, segments=16,
                                   location=(x, DASH_Y - 0.175, 0.425),
                                   rotation=(math.pi / 2, 0, 0), coll=coll)
        utils.assign_material(base, materials.polished_lip())
        utils.parent_keep_transform(base, parent)
        lever = utils.make_box(f"ToggleLever_{i}",
                               size=(0.008, 0.022, 0.008),
                               location=(x, DASH_Y - 0.19, 0.43), coll=coll)
        lever.rotation_euler.x = math.radians(25 if i % 2 else -25)
        mat = materials.orange_accent() if i == 3 else materials.anodized_metal()
        utils.assign_material(lever, mat)
        utils.parent_keep_transform(lever, parent)

    for sx, sz in ((-0.115, 0.54), (0.115, 0.54), (-0.115, 0.38),
                   (0.115, 0.38)):
        screw = utils.make_cylinder(f"PanelScrew_{sx:.2f}_{sz:.2f}",
                                    radius=0.0045, depth=0.003, segments=12,
                                    location=(sx, DASH_Y - 0.172, sz),
                                    rotation=(math.pi / 2, 0, 0), coll=coll)
        utils.assign_material(screw, materials.polished_lip())
        utils.parent_keep_transform(screw, parent)
    return panel


# ---------------------------------------------------------------------------
# Gated shifter (Image 3)
# ---------------------------------------------------------------------------

def build_shifter(coll, parent):
    """Exposed-gate manual shifter: brushed plate with H-pattern slots cut
    by boolean, polished lever, ball top, leather boot ring."""
    plate_z = FLOOR_Z + 0.235
    plate = utils.make_box("GatePlate", size=(0.13, 0.17, 0.012),
                           location=(0, SEAT_Y + 0.45, plate_z), coll=coll)
    utils.add_bevel(plate, 0.004, 2)
    utils.assign_material(plate, materials.anodized_metal())
    utils.parent_keep_transform(plate, parent)

    # H-pattern: three lengthwise slots + one cross slot, cut as booleans
    for i, x in enumerate((-0.035, 0.0, 0.035)):
        slot = utils.make_box(f"GateSlot_{i}", size=(0.012, 0.12, 0.05),
                              location=(x, SEAT_Y + 0.45, plate_z), coll=coll)
        utils.boolean_cut(plate, slot)
    cross = utils.make_box("GateSlotCross", size=(0.085, 0.012, 0.05),
                           location=(0, SEAT_Y + 0.45, plate_z), coll=coll)
    utils.boolean_cut(plate, cross)

    lever = utils.make_cylinder("ShiftLever", radius=0.009, depth=0.17,
                                segments=20,
                                location=(0, SEAT_Y + 0.45, plate_z + 0.085),
                                coll=coll)
    lever.rotation_euler.x = math.radians(-8)
    utils.assign_material(lever, materials.polished_lip())
    utils.parent_keep_transform(lever, parent)

    ball = utils.make_uv_sphere("ShiftBall", radius=0.026,
                                location=(0, SEAT_Y + 0.43, plate_z + 0.175),
                                coll=coll)
    utils.assign_material(ball, materials.polished_lip())
    utils.parent_keep_transform(ball, parent)

    # leather boot ring at the lever base, wrinkled by displacement-ish bump
    boot = utils.make_cylinder("ShiftBoot", radius=0.035, depth=0.05,
                               segments=24,
                               location=(0, SEAT_Y + 0.45, plate_z + 0.02),
                               coll=coll)
    utils.assign_material(boot, materials.leather())
    utils.parent_keep_transform(boot, parent)
    return ball


# ---------------------------------------------------------------------------
# Steering wheel (Image 3)
# ---------------------------------------------------------------------------

def build_steering_wheel(coll, parent):
    """Thick Alcantara rim, three brushed spokes, machined centre hub."""
    centre = Vector((-0.35, DASH_Y - 0.34, 0.58))
    tilt = math.radians(70)   # column rake

    rim = utils.make_torus("SteeringRim", major_r=0.165, minor_r=0.021,
                           major_seg=48, minor_seg=16,
                           location=centre, rotation=(tilt, 0, 0), coll=coll)
    utils.assign_material(rim, materials.alcantara())
    utils.parent_keep_transform(rim, parent)

    for ang in (0, 120, 240):
        a = math.radians(ang + 90)
        spoke = utils.make_box(f"WheelSpoke_{ang}",
                               size=(0.03, 0.145, 0.012), coll=coll)
        # position along the rim plane, then tilt with the column
        local = Vector((math.cos(a) * 0.08, 0.0, math.sin(a) * 0.08))
        rot_x = Vector((local.x,
                        local.z * math.cos(tilt) - 0 * math.sin(tilt),
                        local.z * math.sin(tilt)))
        spoke.location = centre + rot_x
        spoke.rotation_euler = (tilt, 0, a + math.pi / 2)
        utils.assign_material(spoke, materials.anodized_metal())
        utils.parent_keep_transform(spoke, parent)

    hub = utils.make_cylinder("WheelHubCentre", radius=0.045, depth=0.03,
                              segments=32, location=centre,
                              rotation=(tilt, 0, 0), coll=coll)
    utils.assign_material(hub, materials.anodized_metal())
    utils.parent_keep_transform(hub, parent)

    column = utils.make_cylinder("SteeringColumn", radius=0.025, depth=0.25,
                                 segments=20,
                                 location=centre + Vector((0, 0.10, 0.035)),
                                 rotation=(tilt, 0, 0), coll=coll)
    utils.assign_material(column, materials.dark_plastic())
    utils.parent_keep_transform(column, parent)
    return rim


# ---------------------------------------------------------------------------
# Seats (Image 3)
# ---------------------------------------------------------------------------

def build_seat(coll, parent, x):
    """Deep bucket: base + backrest + side bolsters, blue Alcantara centre
    with black leather bolsters (assigned per-face by distance from the
    seat's centre plane) and white piping along the bolster edges."""
    tag = 'L' if x < 0 else 'R'
    parts = []

    base = utils.make_box(f"SeatBase_{tag}", size=(0.50, 0.52, 0.14),
                          location=(x, SEAT_Y, FLOOR_Z + 0.12), coll=coll)
    utils.add_bevel(base, 0.03, 3)
    utils.add_subsurf(base, 1)
    parts.append(base)

    back = utils.make_box(f"SeatBack_{tag}", size=(0.50, 0.13, 0.62),
                          location=(x, SEAT_Y - 0.24, FLOOR_Z + 0.46),
                          coll=coll)
    back.rotation_euler.x = math.radians(-12)
    utils.add_bevel(back, 0.03, 3)
    utils.add_subsurf(back, 1)
    parts.append(back)

    # bolsters: four raised pads hugging the occupant
    for side in (-1, 1):
        cushion_b = utils.make_box(f"SeatBolsterB_{tag}{side}",
                                   size=(0.10, 0.46, 0.10),
                                   location=(x + side * 0.21, SEAT_Y,
                                             FLOOR_Z + 0.18), coll=coll)
        utils.add_bevel(cushion_b, 0.03, 3)
        utils.add_subsurf(cushion_b, 1)
        parts.append(cushion_b)
        cushion_s = utils.make_box(f"SeatBolsterS_{tag}{side}",
                                   size=(0.09, 0.12, 0.55),
                                   location=(x + side * 0.215, SEAT_Y - 0.235,
                                             FLOOR_Z + 0.46), coll=coll)
        cushion_s.rotation_euler.x = math.radians(-12)
        utils.add_bevel(cushion_s, 0.03, 3)
        utils.add_subsurf(cushion_s, 1)
        parts.append(cushion_s)

    headrest = utils.make_box(f"Headrest_{tag}", size=(0.30, 0.12, 0.16),
                              location=(x, SEAT_Y - 0.31, FLOOR_Z + 0.82),
                              coll=coll)
    utils.add_bevel(headrest, 0.04, 3)
    utils.add_subsurf(headrest, 1)
    parts.append(headrest)

    blue = materials.alcantara()
    black = materials.leather()
    bolsters = {p.name for p in parts if "Bolster" in p.name}
    for p in parts:
        if p.name in bolsters:
            # bolster pads are full black leather (Image 3)
            utils.assign_material(p, black)
        else:
            # centre panels blue Alcantara, outboard faces leather —
            # face centres are in the part's LOCAL space (mesh centred
            # on its origin), so |x| > 0.16 selects the side panels
            utils.assign_material(p, blue)
            utils.assign_to_faces(p, black, lambda c: abs(c.x) > 0.16)
        utils.parent_keep_transform(p, parent)

    # white contrast piping along the seat centreline seams
    for dz, dy in ((0.20, 0.02), (0.46, -0.235)):
        pipe = utils.make_cylinder(f"SeatPipe_{tag}_{dz}", radius=0.004,
                                   depth=0.45, segments=8,
                                   location=(x, SEAT_Y + dy, FLOOR_Z + dz),
                                   rotation=(math.radians(78), 0, 0),
                                   coll=coll)
        utils.assign_material(pipe, materials.stitching_white())
        utils.parent_keep_transform(pipe, parent)
    return parts


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build(root):
    coll = utils.sub_collection("Interior")
    pivot = utils.new_empty("Interior", coll=coll)
    utils.parent_keep_transform(pivot, root)

    build_tub(coll, pivot)
    build_dashboard(coll, pivot)
    displays = build_displays(coll, pivot)
    build_control_panel(coll, pivot)
    build_shifter(coll, pivot)
    build_steering_wheel(coll, pivot)
    build_seat(coll, pivot, -0.35)   # driver (LHD)
    build_seat(coll, pivot, 0.35)

    return {"pivot": pivot, "displays": displays}
