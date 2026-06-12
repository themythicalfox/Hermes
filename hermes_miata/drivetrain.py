"""
drivetrain.py — engine, transmission, driveline, fuel tank, suspension
and underbody, packaged in real NB Miata locations.

Layout (longitudinal FR, +Y = nose):
  radiator (y≈1.55) -> inline-4 engine behind the front axle (front-mid,
  y≈0.95..0.55) -> gearbox under the tunnel (y≈0.45..0.05) -> driveshaft
  -> differential at the rear axle -> halfshafts to the hubs.
  Fuel tank sits behind the seats, ahead of the rear axle (y≈-0.85) —
  exactly the space the interior layout now leaves free.

Everything is deliberately readable, named geometry: this is the layer the
user asked for so the car has guts (engine bay shots, under-car reflections,
no hollow shell).
"""

import math

from . import utils, materials
from .utils import FRONT_AXLE_Y, REAR_AXLE_Y, TRACK, WHEEL_R


# ---------------------------------------------------------------------------
# Materials local to the drivetrain
# ---------------------------------------------------------------------------

def _cast_alu():
    def build(name):
        mat, nodes, links, p, out = utils.new_node_material(name)
        utils.set_inputs(p, base_color=(0.45, 0.46, 0.48), metallic=1.0,
                         roughness=0.55)
        return mat
    return materials.get("CastAluminium", build)


def _steel():
    def build(name):
        mat, nodes, links, p, out = utils.new_node_material(name)
        utils.set_inputs(p, base_color=(0.20, 0.20, 0.21), metallic=1.0,
                         roughness=0.4, anisotropic=0.6)
        return mat
    return materials.get("DrivelineSteel", build)


def _crinkle_red():
    """Crinkle-coat valve cover — the one splash of colour in the bay."""
    def build(name):
        mat, nodes, links, p, out = utils.new_node_material(name)
        tex = nodes.new('ShaderNodeTexNoise')
        tex.inputs['Scale'].default_value = 500.0
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = 0.5
        bump.inputs['Distance'].default_value = 0.0008
        links.new(tex.outputs['Fac'], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], p.inputs['Normal'])
        utils.set_inputs(p, base_color=(0.30, 0.02, 0.02), metallic=0.2,
                         roughness=0.6)
        return mat
    return materials.get("CrinkleRed", build)


# ---------------------------------------------------------------------------
# Engine (BP-style inline 4, front-mid mounted)
# ---------------------------------------------------------------------------

def build_engine(coll, parent):
    alu = _cast_alu()
    parts = []

    block = utils.make_box("EngineBlock", size=(0.34, 0.42, 0.26),
                           location=(0.02, 0.75, 0.36), coll=coll)
    utils.add_bevel(block, 0.015, 2)
    utils.assign_material(block, alu)
    parts.append(block)

    pan = utils.make_box("OilPan", size=(0.26, 0.34, 0.10),
                         location=(0.02, 0.75, 0.20), coll=coll)
    utils.add_bevel(pan, 0.012, 2)
    utils.assign_material(pan, _steel())
    parts.append(pan)

    cover = utils.make_box("ValveCover", size=(0.26, 0.40, 0.07),
                           location=(0.02, 0.75, 0.525), coll=coll)
    utils.add_bevel(cover, 0.02, 3)
    utils.assign_material(cover, _crinkle_red())
    parts.append(cover)
    for i in range(4):   # spark plug bosses along the cover
        boss = utils.make_cylinder(f"PlugBoss_{i}", radius=0.018,
                                   depth=0.012, segments=16,
                                   location=(0.02, 0.61 + i * 0.095, 0.565),
                                   coll=coll)
        utils.assign_material(boss, alu)
        parts.append(boss)

    # intake manifold: four curved-ish runners sweeping to the left side
    for i in range(4):
        runner = utils.make_cylinder(f"IntakeRunner_{i}", radius=0.022,
                                     depth=0.20, segments=16,
                                     location=(-0.20, 0.61 + i * 0.095,
                                               0.46),
                                     rotation=(0, math.radians(65), 0),
                                     coll=coll)
        utils.assign_material(runner, alu)
        parts.append(runner)
    plenum = utils.make_cylinder("IntakePlenum", radius=0.05, depth=0.42,
                                 segments=24,
                                 location=(-0.30, 0.75, 0.40),
                                 rotation=(math.pi / 2, 0, 0), coll=coll)
    utils.assign_material(plenum, alu)
    parts.append(plenum)

    # exhaust manifold: four steel primaries diving down the right side
    for i in range(4):
        primary = utils.make_cylinder(f"ExhPrimary_{i}", radius=0.018,
                                      depth=0.22, segments=14,
                                      location=(0.22, 0.61 + i * 0.095,
                                                0.33),
                                      rotation=(0, math.radians(115), 0),
                                      coll=coll)
        utils.assign_material(primary, _steel())
        parts.append(primary)

    # accessory pulley face + belt hint at the nose of the engine
    pulley = utils.make_cylinder("CrankPulley", radius=0.06, depth=0.03,
                                 segments=24,
                                 location=(0.02, 0.97, 0.30),
                                 rotation=(math.pi / 2, 0, 0), coll=coll)
    utils.assign_material(pulley, _steel())
    parts.append(pulley)

    radiator = utils.make_box("Radiator", size=(0.56, 0.045, 0.30),
                              location=(0, 1.52, 0.36), coll=coll)
    radiator.rotation_euler.x = math.radians(12)
    utils.assign_material(radiator, materials.anodized_black())
    parts.append(radiator)

    for p in parts:
        utils.parent_keep_transform(p, parent)
    return parts


# ---------------------------------------------------------------------------
# Transmission, driveshaft, diff, halfshafts, fuel tank
# ---------------------------------------------------------------------------

def build_driveline(coll, parent):
    parts = []
    alu = _cast_alu()
    steel = _steel()

    gearbox = utils.make_box("Gearbox", size=(0.22, 0.46, 0.20),
                             location=(0, 0.28, 0.30), coll=coll)
    utils.add_bevel(gearbox, 0.02, 2)
    utils.assign_material(gearbox, alu)
    parts.append(gearbox)

    bell = utils.make_cylinder("Bellhousing", radius=0.13, depth=0.10,
                               segments=24, location=(0.01, 0.50, 0.32),
                               rotation=(math.pi / 2, 0, 0), coll=coll)
    utils.assign_material(bell, alu)
    parts.append(bell)

    # PPF-style driveshaft from gearbox tail to the diff nose
    shaft = utils.make_cylinder("Driveshaft", radius=0.025, depth=1.10,
                                segments=16, location=(0, -0.52, 0.26),
                                rotation=(math.pi / 2, 0, 0), coll=coll)
    utils.assign_material(shaft, steel)
    parts.append(shaft)

    diff = utils.make_uv_sphere("Differential", radius=0.11,
                                location=(0, REAR_AXLE_Y, 0.27), coll=coll)
    diff.scale = (0.9, 1.2, 0.9)
    utils.assign_material(diff, alu)
    parts.append(diff)

    for side in (-1, 1):
        half = utils.make_cylinder(
            f"Halfshaft_{'L' if side < 0 else 'R'}", radius=0.020,
            depth=TRACK / 2 - 0.12, segments=12,
            location=(side * (TRACK / 4 + 0.05), REAR_AXLE_Y, WHEEL_R),
            rotation=(0, math.pi / 2, 0), coll=coll)
        utils.assign_material(half, steel)
        parts.append(half)

    # fuel tank: saddle box behind the seats, ahead of the rear axle —
    # the packaging space the interior now leaves free
    tank = utils.make_box("FuelTank", size=(0.72, 0.34, 0.17),
                          location=(0, -0.84, 0.26), coll=coll)
    utils.add_bevel(tank, 0.03, 3)
    utils.assign_material(tank, steel)
    parts.append(tank)
    filler = utils.make_cylinder("FuelFiller", radius=0.025, depth=0.30,
                                 segments=12,
                                 location=(-0.70, -0.95, 0.45),
                                 rotation=(0, math.radians(35), 0),
                                 coll=coll)
    utils.assign_material(filler, steel)
    parts.append(filler)

    # exhaust run: midpipe + muffler feeding the visible tips
    mid = utils.make_cylinder("ExhaustMid", radius=0.030, depth=2.0,
                              segments=14, location=(0.18, -0.55, 0.16),
                              rotation=(math.pi / 2, 0, 0), coll=coll)
    utils.assign_material(mid, steel)
    parts.append(mid)
    muffler = utils.make_cylinder("Muffler", radius=0.08, depth=0.40,
                                  segments=20,
                                  location=(0.30, -1.62, 0.18),
                                  rotation=(math.pi / 2, 0, 0), coll=coll)
    utils.assign_material(muffler, steel)
    parts.append(muffler)

    for p in parts:
        utils.parent_keep_transform(p, parent)
    return parts


# ---------------------------------------------------------------------------
# Suspension & underbody
# ---------------------------------------------------------------------------

def build_suspension(coll, parent):
    parts = []
    steel = _steel()
    for tag, axle_y in (("F", FRONT_AXLE_Y), ("R", REAR_AXLE_Y)):
        for side in (-1, 1):
            s = f"{tag}{'L' if side < 0 else 'R'}"
            # lower control arm: hub inboard to a chassis pivot
            arm = utils.make_box(f"ControlArm_{s}",
                                 size=(TRACK / 2 - 0.18, 0.10, 0.03),
                                 location=(side * (TRACK / 4 + 0.04),
                                           axle_y, 0.18), coll=coll)
            utils.assign_material(arm, steel)
            parts.append(arm)
            # coilover: damper body + spring sleeve, leaning inboard
            damper = utils.make_cylinder(f"Damper_{s}", radius=0.020,
                                         depth=0.30, segments=12, coll=coll)
            damper.location = (side * (TRACK / 2 - 0.18), axle_y, 0.35)
            damper.rotation_euler.y = math.radians(-12 * side)
            utils.assign_material(damper, steel)
            parts.append(damper)
            spring = utils.make_cylinder(f"Spring_{s}", radius=0.038,
                                         depth=0.16, segments=16, coll=coll)
            spring.location = (side * (TRACK / 2 - 0.165), axle_y, 0.38)
            spring.rotation_euler.y = math.radians(-12 * side)
            utils.assign_material(spring, materials.orange_accent())
            parts.append(spring)

    # flat undertray nose-to-tail: hides the hollow shell from low angles
    tray = utils.make_box("Undertray", size=(1.28, 2.9, 0.012),
                          location=(0, 0, 0.115), coll=coll)
    utils.assign_material(tray, materials.carbon_fiber())
    parts.append(tray)

    # frame rails either side of the tunnel
    for side in (-1, 1):
        rail = utils.make_box(f"FrameRail_{'L' if side < 0 else 'R'}",
                              size=(0.06, 2.6, 0.06),
                              location=(side * 0.45, 0, 0.15), coll=coll)
        utils.assign_material(rail, steel)
        parts.append(rail)

    for p in parts:
        utils.parent_keep_transform(p, parent)
    return parts


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build(root):
    coll = utils.sub_collection("Drivetrain")
    pivot = utils.new_empty("Drivetrain", coll=coll)
    utils.parent_keep_transform(pivot, root)
    build_engine(coll, pivot)
    build_driveline(coll, pivot)
    build_suspension(coll, pivot)
    return {"drivetrain": pivot}
