"""
main_miata.py — orchestrator. Builds the whole Hermes Miata scene.

Run it two ways:

A) As the installed add-on (recommended):
   Edit > Preferences > Add-ons > Install the hermes_miata folder (zipped),
   enable "Hermes Miata", then press N in the 3D viewport > Hermes tab >
   "Build Hermes Miata".

B) From the Text Editor without installing:
   import sys; sys.path.append(r"/path/to/Hermes")   # repo root
   from hermes_miata import main_miata
   main_miata.build()

Either way you get organized collections (Hermes_Miata_Body, _Wheels,
_Interior, _Cameras, _Scene), a 300-frame animated timeline, and Cycles
configured for finals. Tweakable custom properties live on the root empty.
"""

import bpy

from . import utils, body, wheels, interior, animation, scene_setup


def clear_previous():
    """Remove any earlier Hermes build so re-running is idempotent."""
    for obj in list(bpy.data.objects):
        if obj.name.startswith(utils.PREFIX):
            bpy.data.objects.remove(obj, do_unlink=True)
    for coll in list(bpy.data.collections):
        if coll.name.startswith(utils.ROOT_COLLECTION):
            bpy.data.collections.remove(coll)
    for block_list in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                       bpy.data.lights, bpy.data.cameras):
        for block in list(block_list):
            if block.name.startswith(utils.PREFIX) and block.users == 0:
                block_list.remove(block)


def build(with_animation=True, with_scene=True, samples=512):
    """Build everything. Returns the handles dict for scripting access."""
    clear_previous()
    scene = bpy.context.scene

    # root empty: the whole car hangs off this, and the idle vibration
    # noise lives on its f-curves so every part inherits it
    root = utils.new_empty("CarRoot", (0, 0, 0), utils.root_collection())

    # user-tweakable knobs surfaced as custom properties
    root["ride_height"] = utils.RIDE_HEIGHT
    root["flake_scale"] = 9000.0
    root["wing_angle_deg"] = 8.0
    root.id_properties_ensure()

    handles = {"root": root}

    body_handles = body.build(root)
    handles.update(body_handles)

    handles["wheel_hubs"] = wheels.build(root)

    interior_handles = interior.build(root)
    handles["displays"] = interior_handles["displays"]

    if with_scene:
        scene_handles = scene_setup.build(scene, handles["exhaust_tips"],
                                          samples=samples)
        handles.update(scene_handles)

    if with_animation:
        animation.build(scene, handles)

    print(f"[Hermes] Build complete: "
          f"{sum(1 for o in bpy.data.objects if o.name.startswith(utils.PREFIX))} "
          f"objects across {len([c for c in bpy.data.collections if c.name.startswith(utils.ROOT_COLLECTION)])} collections.")
    return handles


def render_reel():
    """Render the full 300-frame animation to //renders/."""
    scene = bpy.context.scene
    scene_setup.setup_render(scene, animation=True)
    bpy.ops.render.render(animation=True)


def render_stills():
    """Render the six signature still angles to //renders/stills/."""
    scene_setup.render_stills(bpy.context.scene)


if __name__ == "__main__":
    build()
