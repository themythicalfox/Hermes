"""
utils.py — shared helpers for the Hermes Miata procedural build.

Everything here is deliberately version-defensive: Blender renamed several
Principled BSDF sockets between 3.x and 4.x/5.x ("Clearcoat" -> "Coat Weight",
"Subsurface" -> "Subsurface Weight", etc.), so material code never sets a
socket by a single hard-coded name. The helpers below try a list of aliases
and silently skip sockets that don't exist in the running version.
"""

import bpy
import bmesh
import math
from mathutils import Vector, Matrix

# ---------------------------------------------------------------------------
# Naming / scene constants
# ---------------------------------------------------------------------------

PREFIX = "HERMES"           # every object/material we create is namespaced
ROOT_COLLECTION = "Hermes_Miata"

# Car coordinate convention used by every module:
#   +Y = forward (nose),  +X = driver right,  +Z = up,  origin at ground
# under the car's geometric centre between the axles.
WHEELBASE   = 2.27          # metres (NB Miata)
LENGTH      = 3.95
WIDTH       = 1.88          # with widebody flares
HEIGHT      = 1.18          # lowered roofline
TRACK       = 1.60          # widened track, wheel centre to wheel centre
WHEEL_R     = 0.305         # ~17" wheel + semi-slick tyre rolling radius
RIDE_HEIGHT = 0.085         # slammed: rocker panel to ground

FRONT_AXLE_Y =  WHEELBASE / 2.0
REAR_AXLE_Y  = -WHEELBASE / 2.0


# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------

def ensure_collection(name, parent=None):
    """Get-or-create a collection and link it under `parent` (or the scene)."""
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
    parent = parent or bpy.context.scene.collection
    if coll.name not in [c.name for c in parent.children]:
        try:
            parent.children.link(coll)
        except RuntimeError:
            pass  # already linked somewhere else in the tree
    return coll


def link_only(obj, coll):
    """Link `obj` into `coll` and unlink it from every other collection."""
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)


def root_collection():
    return ensure_collection(ROOT_COLLECTION)


def sub_collection(name):
    return ensure_collection(f"{ROOT_COLLECTION}_{name}", root_collection())


# ---------------------------------------------------------------------------
# Object creation
# ---------------------------------------------------------------------------

def obj_from_bmesh(name, bm, coll=None, smooth=True):
    """Bake a bmesh into a new mesh object and link it to `coll`."""
    mesh = bpy.data.meshes.new(f"{PREFIX}_{name}_mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(f"{PREFIX}_{name}", mesh)
    (coll or root_collection()).objects.link(obj)
    if smooth:
        shade_smooth(obj)
    return obj


def new_empty(name, location=(0, 0, 0), coll=None):
    e = bpy.data.objects.new(f"{PREFIX}_{name}", None)
    e.empty_display_size = 0.25
    e.location = location
    (coll or root_collection()).objects.link(e)
    return e


def shade_smooth(obj, angle_deg=35.0):
    """Smooth shading with an edge-angle limit, across Blender versions.

    4.1+ removed mesh.use_auto_smooth, so we fall back to marking sharp
    edges by angle which both old and new versions respect.
    """
    me = obj.data
    for p in me.polygons:
        p.use_smooth = True
    if hasattr(me, "use_auto_smooth"):          # <= 4.0
        me.use_auto_smooth = True
        me.auto_smooth_angle = math.radians(angle_deg)
    else:                                       # 4.1+ / 5.x
        limit = math.radians(angle_deg)
        # edge angles aren't exposed on Mesh edges directly; a lightweight
        # bmesh pass marks edges sharper than the limit as flat-shaded
        bm = bmesh.new()
        bm.from_mesh(me)
        for e in bm.edges:
            if e.is_manifold and e.calc_face_angle(0.0) > limit:
                e.smooth = False
        bm.to_mesh(me)
        bm.free()


# ---------------------------------------------------------------------------
# Modifiers
# ---------------------------------------------------------------------------

def add_subsurf(obj, levels=2, render_levels=None):
    m = obj.modifiers.new("Subsurf", 'SUBSURF')
    m.levels = levels
    m.render_levels = render_levels or max(levels, 2)
    return m


def add_mirror_x(obj):
    m = obj.modifiers.new("MirrorX", 'MIRROR')
    m.use_axis = (True, False, False)
    m.use_clip = True
    return m


def add_bevel(obj, width=0.004, segments=2, angle_deg=40):
    m = obj.modifiers.new("Bevel", 'BEVEL')
    m.width = width
    m.segments = segments
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(angle_deg)
    return m


def add_solidify(obj, thickness=0.02):
    m = obj.modifiers.new("Solidify", 'SOLIDIFY')
    m.thickness = thickness
    return m


def boolean_cut(obj, cutter, hide_cutter=True):
    """Subtract `cutter` from `obj` (modifier left live for tweakability)."""
    m = obj.modifiers.new(f"Cut_{cutter.name}", 'BOOLEAN')
    m.operation = 'DIFFERENCE'
    m.object = cutter
    m.solver = 'EXACT'
    if hide_cutter:
        cutter.display_type = 'WIRE'
        cutter.hide_render = True
    return m


# ---------------------------------------------------------------------------
# Primitive builders (bmesh-based so nothing touches bpy.ops / context)
# ---------------------------------------------------------------------------

def make_box(name, size, location=(0, 0, 0), coll=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    obj = obj_from_bmesh(name, bm, coll, smooth=False)
    obj.location = location
    return obj


def make_cylinder(name, radius=0.1, depth=0.1, segments=32,
                  location=(0, 0, 0), rotation=(0, 0, 0), coll=None,
                  cap='NGON'):
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=(cap == 'TRI'), segments=segments,
        radius1=radius, radius2=radius, depth=depth)
    obj = obj_from_bmesh(name, bm, coll)
    obj.location = location
    obj.rotation_euler = rotation
    return obj


def make_torus(name, major_r=0.3, minor_r=0.1, major_seg=48, minor_seg=18,
               location=(0, 0, 0), rotation=(0, 0, 0), coll=None):
    """Watertight torus around local +Z, faces built explicitly (no ops
    whose loop-pairing is heuristic)."""
    bm = bmesh.new()
    rings = []
    for i in range(major_seg):
        a = 2 * math.pi * i / major_seg
        ring = []
        for j in range(minor_seg):
            b = 2 * math.pi * j / minor_seg
            r = major_r + minor_r * math.cos(b)
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a),
                                      minor_r * math.sin(b))))
        rings.append(ring)
    for i in range(major_seg):
        ra, rb = rings[i], rings[(i + 1) % major_seg]
        for j in range(minor_seg):
            jn = (j + 1) % minor_seg
            bm.faces.new((ra[j], ra[jn], rb[jn], rb[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = obj_from_bmesh(name, bm, coll)
    obj.location = location
    obj.rotation_euler = rotation
    return obj


def make_uv_sphere(name, radius=0.1, segments=24, rings=16,
                   location=(0, 0, 0), coll=None):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings,
                              radius=radius)
    obj = obj_from_bmesh(name, bm, coll)
    obj.location = location
    return obj


def make_plane(name, size_x=1.0, size_y=1.0, location=(0, 0, 0),
               rotation=(0, 0, 0), coll=None):
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    bmesh.ops.scale(bm, vec=Vector((size_x, size_y, 1.0)), verts=bm.verts)
    obj = obj_from_bmesh(name, bm, coll, smooth=False)
    obj.location = location
    obj.rotation_euler = rotation
    return obj


# ---------------------------------------------------------------------------
# Lofting: the workhorse for the car body
# ---------------------------------------------------------------------------

def loft_sections(name, sections, close_ends=True, coll=None):
    """Bridge a list of cross-section vertex loops into a skinned surface.

    `sections` is a list of lists of (x, y, z) tuples; every section must
    contain the same number of points, ordered consistently (we go from the
    bottom-outboard point up over the top — body.py builds them that way).
    """
    bm = bmesh.new()
    rings = []
    for sec in sections:
        ring = [bm.verts.new(Vector(p)) for p in sec]
        rings.append(ring)
    bm.verts.index_update()
    # bridge consecutive rings with quads
    for ra, rb in zip(rings[:-1], rings[1:]):
        for i in range(len(ra) - 1):
            bm.faces.new((ra[i], ra[i + 1], rb[i + 1], rb[i]))
    if close_ends:
        # fan-cap each end on its centroid so subsurf keeps it rounded
        for ring in (rings[0], rings[-1]):
            centre = sum((v.co for v in ring), Vector()) / len(ring)
            cv = bm.verts.new(centre)
            for i in range(len(ring) - 1):
                if ring is rings[0]:
                    bm.faces.new((ring[i + 1], ring[i], cv))
                else:
                    bm.faces.new((ring[i], ring[i + 1], cv))
    # rings that close on a repeated point leave a coincident seam — weld it
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bmesh(name, bm, coll)


# ---------------------------------------------------------------------------
# Material socket helpers (version-proof Principled BSDF access)
# ---------------------------------------------------------------------------

# alias table: our key -> candidate socket names, oldest API last
_SOCKET_ALIASES = {
    "base_color":   ["Base Color"],
    "metallic":     ["Metallic"],
    "roughness":    ["Roughness"],
    "ior":          ["IOR"],
    "alpha":        ["Alpha"],
    "specular":     ["Specular IOR Level", "Specular"],
    "anisotropic":  ["Anisotropic"],
    "anisotropic_rotation": ["Anisotropic Rotation"],
    "coat":         ["Coat Weight", "Clearcoat"],
    "coat_rough":   ["Coat Roughness", "Clearcoat Roughness"],
    "sheen":        ["Sheen Weight", "Sheen"],
    "sheen_tint":   ["Sheen Tint"],
    "sheen_rough":  ["Sheen Roughness"],
    "sss":          ["Subsurface Weight", "Subsurface"],
    "sss_radius":   ["Subsurface Radius"],
    "sss_scale":    ["Subsurface Scale"],
    "transmission": ["Transmission Weight", "Transmission"],
    "emission":     ["Emission Color", "Emission"],
    "emission_strength": ["Emission Strength"],
    "normal":       ["Normal"],
}


def find_input(node, key):
    """Resolve one of our alias keys (or a raw name) to a node input socket."""
    for name in _SOCKET_ALIASES.get(key, [key]):
        sock = node.inputs.get(name)
        if sock is not None:
            return sock
    return None


def set_inputs(node, **kwargs):
    """Set default_value on Principled sockets via alias keys.

    Colors may be given as 3-tuples and are padded to RGBA.
    Sockets missing in this Blender version are skipped silently.
    """
    for key, value in kwargs.items():
        sock = find_input(node, key)
        if sock is None:
            continue
        if hasattr(sock, "default_value"):
            dv = sock.default_value
            try:
                if hasattr(dv, "__len__") and len(dv) == 4 and \
                        hasattr(value, "__len__") and len(value) == 3:
                    value = (*value, 1.0)
                sock.default_value = value
            except (TypeError, ValueError):
                pass


def new_node_material(name):
    """Create a node material and return (mat, nodes, links, principled, output)."""
    mat = bpy.data.materials.new(f"{PREFIX}_{name}")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    principled = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    output = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
    return mat, nodes, links, principled, output


def assign_material(obj, mat, slot=None):
    """Append (or set) a material on an object, returns its slot index."""
    if slot is not None and slot < len(obj.data.materials):
        obj.data.materials[slot] = mat
        return slot
    obj.data.materials.append(mat)
    return len(obj.data.materials) - 1


def assign_to_faces(obj, mat, predicate):
    """Add `mat` as a new slot and assign it to faces whose centre passes
    `predicate(Vector) -> bool`. Used for two-tone seats etc."""
    idx = assign_material(obj, mat)
    for poly in obj.data.polygons:
        if predicate(Vector(poly.center)):
            poly.material_index = idx
    return idx


# ---------------------------------------------------------------------------
# F-curve helpers
# ---------------------------------------------------------------------------

def add_noise_to_fcurves(obj, data_path, strength=0.002, scale=8.0,
                         indices=(0, 1, 2)):
    """Insert a base keyframe then layer a NOISE modifier on each f-curve —
    this is how the idle-vibration and exhaust-jiggle effects are driven."""
    obj.keyframe_insert(data_path=data_path, frame=1)
    if not obj.animation_data or not obj.animation_data.action:
        return
    for fc in obj.animation_data.action.fcurves:
        if fc.data_path == data_path and fc.array_index in indices:
            mod = fc.modifiers.new('NOISE')
            mod.strength = strength
            mod.scale = scale
            mod.phase = fc.array_index * 17.0   # decorrelate the axes


def keyframe(obj_or_id, data_path, frame_value_pairs, index=-1,
             interpolation='BEZIER'):
    """Tiny helper: keyframe a property at several (frame, value) pairs."""
    for frame, value in frame_value_pairs:
        if index >= 0:
            attr = getattr(obj_or_id, data_path.split('.')[-1], None)
            try:
                cur = list(attr)
                cur[index] = value
                setattr(obj_or_id, data_path.split('.')[-1], cur)
            except TypeError:
                pass
        else:
            # path may be nested ("location") or a custom prop
            try:
                obj_or_id.path_resolve(data_path)
                exec_set(obj_or_id, data_path, value)
            except ValueError:
                pass
        obj_or_id.keyframe_insert(data_path=data_path, frame=frame,
                                  index=index)
    # set interpolation on the curves we just made
    ad = obj_or_id.animation_data if hasattr(obj_or_id, "animation_data") else None
    if ad and ad.action:
        for fc in ad.action.fcurves:
            if fc.data_path == data_path:
                for kp in fc.keyframe_points:
                    kp.interpolation = interpolation


def exec_set(owner, path, value):
    """Set a (possibly nested) rna path like 'location' or '["prop"]'."""
    if path.startswith('["'):
        owner[path[2:-2]] = value
        return
    parts = path.split('.')
    target = owner
    for p in parts[:-1]:
        target = getattr(target, p)
    setattr(target, parts[-1], value)


def parent_keep_transform(child, parent):
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()
