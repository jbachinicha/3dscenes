"""Model a low-poly turbo exhaust flame, then export it as GLB.

Style target: the timeline scene's palette (blush/pink/rose) rather than a
literal orange fire — two nested, jagged licks so it still reads as flame
when flat-shaded and faceted like the rest of this project's props.

No armature: unlike the bird/chicken, a flame has no joints to hinge, so
Three.js drives the whole animation at runtime (scale + opacity flicker on
the mesh group, see scenes/timeline/index.html) rather than baking a clip
here. Blender's only job is the geometry.

The shape is a tapered lofted tube (same `tube()` approach as bird.py's neck
and legs) with the ring radius jittered per-station so the silhouette is
jagged rather than a smooth cone, and a slight sideways wobble down its
length so it doesn't read as a perfectly straight party-hat.
"""
import bpy, bmesh, sys, math, json
from mathutils import Vector

OUT = sys.argv[sys.argv.index('--') + 1]
GLB = sys.argv[sys.argv.index('--') + 2]

bpy.ops.wm.read_factory_settings(use_empty=True)

def mat(name, rgb, rough=0.7):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgb, 1.0)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = 0.0
    if 'Emission Color' in b.inputs:
        b.inputs['Emission Color'].default_value = (*rgb, 1.0)
        b.inputs['Emission Strength'].default_value = 1.4
    m.diffuse_color = (*rgb, 1.0)
    return m

OUTER = mat('flameOuter', (1.00, 0.44, 0.60))   # rose
INNER = mat('flameInner', (1.00, 0.82, 0.48))   # warm cream-gold core

TAU = math.pi * 2

def frame_at(tangent):
    t = tangent.normalized()
    ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
    u = t.cross(ref).normalized()
    v = t.cross(u).normalized()
    return u, v

def lick(name, length, base_r, sides, jitter, seed, material):
    """A tapered, jaggy lofted tube standing on Blender +Z, apex away from
    the base — same station-count-spans-the-shape idea as bird.py's tube(),
    just with per-station radius jitter instead of a smooth taper so the
    silhouette reads as flame rather than a cone."""
    STATIONS = 7
    path = []
    radii = []
    rnd = seed
    def nextf():
        nonlocal rnd
        rnd = (rnd * 1103515245 + 12345) & 0x7fffffff
        return (rnd / 0x7fffffff) * 2 - 1

    for i in range(STATIONS):
        t = i / (STATIONS - 1)
        z = length * t
        wob = 0.05 * length * math.sin(t * math.pi * 1.6) * (1 if seed % 2 == 0 else -1)
        path.append(Vector((wob * 0.6, wob, z)))
        taper = (1.0 - t) ** 1.3
        r = base_r * taper * (1.0 + jitter * nextf() * (0.4 + 0.6 * t))
        radii.append(max(r, 0.004))

    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    rings = []
    for i, c in enumerate(path):
        tan = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)])
        if tan.length < 1e-6:
            tan = Vector((0, 0, 1))
        u, v = frame_at(tan)
        ring = []
        for k in range(sides):
            a = TAU * k / sides
            off = u * (math.cos(a) * radii[i]) + v * (math.sin(a) * radii[i])
            ring.append(bm.verts.new(c + off))
        rings.append(ring)
    bm.verts.ensure_lookup_table()
    for i in range(len(rings) - 1):
        for k in range(sides):
            k2 = (k + 1) % sides
            bm.faces.new([rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]])
    bm.faces.new(list(reversed(rings[0])))
    # No end cap at the tip — it tapers to a near-point already
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    for p in o.data.polygons:
        p.use_smooth = False
    o.data.materials.append(material)
    return o

parts = []
# Outer lick: wider, shorter, jaggier — the visible "body" of the flame
parts.append(lick('flame_outer', length=0.62, base_r=0.15, sides=7, jitter=0.22, seed=7, material=OUTER))
# Inner lick: narrower, taller, sits proud at the front — the hot core
inner = lick('flame_inner', length=0.72, base_r=0.075, sides=6, jitter=0.14, seed=13, material=INNER)
inner.location.z = 0.02
parts.append(inner)

bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
mesh = bpy.context.active_object
mesh.name = 'TurboFlame'

# Flame points along Blender +Z from the origin (the exhaust). The glTF
# exporter's default +Y-up conversion maps Blender +Z to three.js +Y, so
# rotate -90 about X here to send it out along +Z in Blender terms first —
# simplest is to just build it lying along -Y instead, matching bird.py's
# "faces -Y -> glTF +Z" convention used elsewhere in this project.
mesh.rotation_euler = (math.radians(-90), 0, 0)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

bb = [mesh.matrix_world @ Vector(c) for c in mesh.bound_box]
bounds = {'min': [round(min(p[i] for p in bb), 3) for i in range(3)],
          'max': [round(max(p[i] for p in bb), 3) for i in range(3)]}

bpy.ops.export_scene.gltf(filepath=GLB, export_format='GLB', export_animations=False)

print('BLENDER_JSON_START')
print(json.dumps({
    'tris': len(mesh.data.polygons),
    'verts': len(mesh.data.vertices),
    'bounds': bounds,
}, indent=1))
print('BLENDER_JSON_END')
