"""
Hermes Miata — procedural modded 2002 NB Mazda Miata for Blender.

Add-on entry point: registers a sidebar panel (3D View > N > Hermes) with
build/render operators, plus the operators themselves. All real work lives
in the sibling modules (body, wheels, interior, materials, animation,
scene_setup) orchestrated by main_miata.py.
"""

bl_info = {
    "name": "Hermes Miata",
    "author": "Hermes Project",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),   # tested against 5.1; 4.2 LTS API floor
    "location": "View3D > Sidebar > Hermes",
    "description": "Procedurally build, texture and animate a modded NB "
                   "Mazda Miata (widebody, BRG, blue Alcantara interior)",
    "category": "Add Mesh",
}

import importlib
import bpy

from . import utils, materials, body, wheels, interior, animation, \
    scene_setup, main_miata

_MODULES = (utils, materials, body, wheels, interior, animation,
            scene_setup, main_miata)

# dev convenience: F8 / re-enable reloads edited submodules
if "bpy" in locals():
    for _m in _MODULES:
        importlib.reload(_m)


class HERMES_OT_build(bpy.types.Operator):
    """Build the complete Hermes Miata (car, scene, animation)"""
    bl_idname = "hermes.build_miata"
    bl_label = "Build Hermes Miata"
    bl_options = {'REGISTER', 'UNDO'}

    with_animation: bpy.props.BoolProperty(
        name="Animate", default=True,
        description="Create the 300-frame reel (lights, soft top, cameras)")
    with_scene: bpy.props.BoolProperty(
        name="Scene & Lighting", default=True,
        description="World, asphalt ground, fill lights, render settings")
    samples: bpy.props.IntProperty(
        name="Cycles Samples", default=512, min=32, max=4096)

    def execute(self, context):
        try:
            main_miata.build(with_animation=self.with_animation,
                             with_scene=self.with_scene,
                             samples=self.samples)
        except Exception as exc:   # surface build errors in the UI
            self.report({'ERROR'}, f"Build failed: {exc}")
            raise
        self.report({'INFO'}, "Hermes Miata built")
        return {'FINISHED'}


class HERMES_OT_render_stills(bpy.types.Operator):
    """Render the six signature still angles to //renders/stills/"""
    bl_idname = "hermes.render_stills"
    bl_label = "Render Stills"

    def execute(self, context):
        main_miata.render_stills()
        return {'FINISHED'}


class HERMES_OT_render_reel(bpy.types.Operator):
    """Render the full animation reel to //renders/"""
    bl_idname = "hermes.render_reel"
    bl_label = "Render Animation Reel"

    def execute(self, context):
        main_miata.render_reel()
        return {'FINISHED'}


class HERMES_PT_panel(bpy.types.Panel):
    bl_label = "Hermes Miata"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Hermes"

    def draw(self, context):
        col = self.layout.column(align=True)
        col.operator(HERMES_OT_build.bl_idname, icon='AUTO')
        col.separator()
        col.label(text="HDRI (optional):")
        col.prop(context.scene, "hermes_hdri_path", text="")
        col.separator()
        col.operator(HERMES_OT_render_stills.bl_idname, icon='RENDER_STILL')
        col.operator(HERMES_OT_render_reel.bl_idname,
                     icon='RENDER_ANIMATION')


_CLASSES = (HERMES_OT_build, HERMES_OT_render_stills,
            HERMES_OT_render_reel, HERMES_PT_panel)


def register():
    bpy.types.Scene.hermes_hdri_path = bpy.props.StringProperty(
        name="HDRI Path", subtype='FILE_PATH', default="",
        description="Equirectangular HDRI for the parking-lot environment "
                    "(falls back to a procedural sky when empty)")
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.hermes_hdri_path
