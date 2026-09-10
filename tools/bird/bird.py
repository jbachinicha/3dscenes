"""Procedurally build, rig and animate a low-poly bird, then export it as GLB.

Style target: the island scene's other props — faceted low-poly shapes in flat
pastel colours (mint foliage, pink blossom, coral beaks).

Two things are deliberate here, both learned from rigging the chicken:

1. Geometry is generated with divisions *spanning every joint*. Skin weights are
   per-vertex, so a joint in a region with no vertices cannot deform smoothly —
   the chicken had to use rigid weights because its legs had no mid-limb vertices.
   Here the wings, neck, tail and legs are lofted tubes/grids with several rings
   each, so there is something to interpolate across.

2. Limbs are bone *chains* (shoulder/elbow/wrist, thigh/shin/foot, 2 neck, 3
   spine, 2 tail) and skinning uses Blender's heat-diffusion automatic weights,
   so deformation blends instead of snapping at segment boundaries. Animation
   drives the chains with a phase lag outward, which is what makes a wingbeat
   read as a smooth unfurling rather than a rigid paddle.

The bird faces Blender -Y, which the glTF exporter maps to +Z, so the scene can
use `rotation.y = dir` with no extra offset.
"""
import bpy, bmesh, sys, math, json
from mathutils import Vector, Matrix

OUT = sys.argv[sys.argv.index('--') + 1]
GLB = sys.argv[sys.argv.index('--') + 2]

bpy.ops.wm.read_factory_settings(use_empty=True)

def mat(name, rgb, rough=0.85):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgb, 1.0)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = 0.0
    m.diffuse_color = (*rgb, 1.0)   # Workbench previews read this, not the node
    return m

BODY  = mat('body',  (0.42, 0.70, 0.89))
WING  = mat('wing',  (0.32, 0.58, 0.80))
BELLY = mat('belly', (1.00, 0.95, 0.86))
BEAK  = mat('beak',  (1.00, 0.64, 0.36))
EYE   = mat('eye',   (0.13, 0.13, 0.17))
SHINE = mat('shine', (1.00, 1.00, 1.00), rough=0.4)
LEG   = mat('leg',   (0.91, 0.58, 0.35))

parts = []
def finish(obj, material, force_bone=None):
    for p in obj.data.polygons:
        p.use_smooth = False
    obj.data.materials.append(material)
    # Detached bits (eyes, beak) are unreliable for heat-diffusion weighting, so
    # tag them to be pinned to one bone after automatic weights are computed.
    if force_bone:
        vg = obj.vertex_groups.new(name='FORCE_' + force_bone)
        vg.add([v.index for v in obj.data.vertices], 1.0, 'REPLACE')
    parts.append(obj)
    return obj

def ico(r, subdiv, loc, scale, material, force_bone=None):
    bpy.ops.mesh.primitive_ico_sphere_add(radius=r, subdivisions=subdiv, location=loc)
    o = bpy.context.active_object
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, material, force_bone)

def frame_at(tangent):
    """Stable orthonormal frame for a tube ring."""
    t = tangent.normalized()
    ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
    u = t.cross(ref).normalized()
    v = t.cross(u).normalized()
    return u, v

def tube(name, path, radii, material, sides=7, squash=None, force_bone=None):
    """Loft a closed tube along a polyline — gives rings of vertices across joints."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    rings = []
    for i, c in enumerate(path):
        tan = (path[min(i+1, len(path)-1)] - path[max(i-1, 0)])
        if tan.length < 1e-6: tan = Vector((0, 1, 0))
        u, v = frame_at(tan)
        sq = squash[i] if squash else 1.0
        ring = []
        for k in range(sides):
            a = TAU * k / sides
            off = u * (math.cos(a) * radii[i]) + v * (math.sin(a) * radii[i] * sq)
            ring.append(bm.verts.new(c + off))
        rings.append(ring)
    bm.verts.ensure_lookup_table()
    for i in range(len(rings) - 1):
        for k in range(sides):
            k2 = (k + 1) % sides
            bm.faces.new([rings[i][k], rings[i][k2], rings[i+1][k2], rings[i+1][k]])
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        bm.faces.new(list(reversed(ring)) if rev else list(ring))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    return finish(o, material, force_bone)

TAU = math.pi * 2

# ── Body: dense enough to blend across the spine chain ─────────────────────
ico(0.5, 3, (0, 0.06, 0),      (0.72, 1.06, 0.80), BODY)
ico(0.5, 2, (0, -0.06, -0.16), (0.56, 0.82, 0.50), BELLY)

# ── Neck: a lofted tube, so the 2 neck bones bend it smoothly ─────────────
neck_path = [Vector((0, -0.26 - 0.055*i, 0.06 + 0.050*i)) for i in range(6)]
tube('neck', neck_path, [0.215, 0.195, 0.178, 0.166, 0.160, 0.170], BODY, sides=8)

# ── Head, beak, eyes ───────────────────────────────────────────────────────
ico(0.27, 3, (0, -0.64, 0.38), (1.05, 0.98, 1.0), BODY)
bpy.ops.mesh.primitive_cone_add(vertices=7, radius1=0.085, depth=0.28,
                                location=(0, -0.90, 0.33),
                                rotation=(math.radians(-90), 0, 0))
finish(bpy.context.active_object, BEAK, force_bone='head')
# Eyes must sit ON the head's surface. Placing them by eyeballed coordinates put
# their centres at 0.755 of the head radius with a radius of 0.23 of it, i.e.
# entirely inside the skull -- the bird had no visible eyes at all. So derive the
# position from the head ellipsoid instead: a unit direction scaled by the head's
# semi-axes, at 0.88 of the way out, which leaves the sphere proud of the surface.
HEAD_C = Vector((0, -0.64, 0.38))
HEAD_R = Vector((0.27 * 1.05, 0.27 * 0.98, 0.27))     # semi-axes after scaling
EYE_DIR = Vector((0.70, -0.62, 0.34)).normalized()     # out, forward and a little up
EYE_R, SHINE_R = 0.082, 0.032

for sx in (1, -1):
    d = Vector((EYE_DIR.x * sx, EYE_DIR.y, EYE_DIR.z))
    c = HEAD_C + Vector((d.x * HEAD_R.x, d.y * HEAD_R.y, d.z * HEAD_R.z)) * 0.88
    ico(EYE_R, 1, (c.x, c.y, c.z), (1, 1, 1), EYE, force_bone='head')
    # Catchlight, nudged further out so it reads on the eye's front face
    h = c + Vector((d.x, d.y, d.z)) * (EYE_R * 0.62) + Vector((0, -0.012, 0.022))
    ico(SHINE_R, 1, (h.x, h.y, h.z), (1, 1, 1), SHINE, force_bone='head')

# ── Wings: lofted grid, 9 spanwise stations across 3 bones ────────────────
def wing(side, name):
    STATIONS = 9
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    rings = []
    for i in range(STATIONS):
        t = i / (STATIONS - 1)
        x = side * (0.15 + 0.92 * t)
        # chord tapers and sweeps back toward the tip
        front = -0.28 - 0.10 * math.sin(math.pi * t) + 0.26 * t
        back  =  0.26 + 0.02 * t - 0.24 * t * t
        halfth = 0.060 * (1.0 - 0.75 * t)
        z = 0.14 + 0.05 * math.sin(math.pi * t)
        mid = (front + back) / 2
        ring = [
            bm.verts.new((x, front, z)),
            bm.verts.new((x, mid,   z + halfth)),
            bm.verts.new((x, back,  z)),
            bm.verts.new((x, mid,   z - halfth)),
        ]
        rings.append(ring)
    bm.verts.ensure_lookup_table()
    for i in range(STATIONS - 1):
        for k in range(4):
            k2 = (k + 1) % 4
            bm.faces.new([rings[i][k], rings[i][k2], rings[i+1][k2], rings[i+1][k]])
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(list(rings[-1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    return finish(o, WING)

wing(1, 'wingL'); wing(-1, 'wingR')

# ── Tail: flattened lofted tube over 2 bones ──────────────────────────────
tail_path = [Vector((0, 0.42 + 0.16*i, 0.04 + 0.022*i)) for i in range(6)]
tube('tail', tail_path, [0.20, 0.215, 0.225, 0.225, 0.21, 0.17], WING,
     sides=8, squash=[0.30]*6)

# ── Legs: lofted tubes over thigh/shin, plus a foot ───────────────────────
for sx, nm in ((1, 'legL'), (-1, 'legR')):
    path = [Vector((sx*0.15, 0.03 - 0.012*i, -0.34 - 0.098*i)) for i in range(6)]
    tube(nm, path, [0.075, 0.062, 0.052, 0.046, 0.042, 0.040], LEG, sides=6)
    ico(0.095, 1, (sx*0.15, -0.075, -0.85), (1.0, 1.5, 0.32), LEG,
        force_bone='foot.' + ('L' if sx > 0 else 'R'))

# Sanity-check that each eye actually protrudes from the head
_eye_report = []
for o in parts:
    if o.data.materials and o.data.materials[0].name in ('eye', 'shine'):
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        ctr = Vector((sum(b.x for b in bb)/8, sum(b.y for b in bb)/8, sum(b.z for b in bb)/8))
        rel = Vector(((ctr.x - HEAD_C.x)/HEAD_R.x, (ctr.y - HEAD_C.y)/HEAD_R.y,
                      (ctr.z - HEAD_C.z)/HEAD_R.z))
        outer = max((Vector(((b.x-HEAD_C.x)/HEAD_R.x, (b.y-HEAD_C.y)/HEAD_R.y,
                            (b.z-HEAD_C.z)/HEAD_R.z))).length for b in bb)
        _eye_report.append({'mat': o.data.materials[0].name,
                            'centreAtHeadRadius': round(rel.length, 2),
                            'outermostAtHeadRadius': round(outer, 2)})

PART_BOUNDS = []
for o in parts:
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    PART_BOUNDS.append({'name': o.name,
        'min': [round(min(p[i] for p in bb), 2) for i in range(3)],
        'max': [round(max(p[i] for p in bb), 2) for i in range(3)]})

# ── Join ───────────────────────────────────────────────────────────────────
bpy.ops.object.select_all(action='DESELECT')
for o in parts: o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
mesh = bpy.context.active_object
mesh.name = 'Bird'

# ── Armature: chains, not single bones ────────────────────────────────────
ad = bpy.data.armatures.new('BirdArmature')
arm = bpy.data.objects.new('BirdRig', ad)
bpy.context.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
eb = ad.edit_bones
def bone(n, h, t, p=None, connect=False):
    b = eb.new(n); b.head = Vector(h); b.tail = Vector(t)
    if p: b.parent = p; b.use_connect = connect
    return b

root   = bone('root',    (0, 0, -0.95), (0, 0, -0.40))
spine1 = bone('spine1',  (0, 0.42, -0.02), (0, 0.14, 0.01), root)
spine2 = bone('spine2',  (0, 0.14, 0.01), (0, -0.14, 0.02), spine1, True)
spine3 = bone('spine3',  (0, -0.14, 0.02), (0, -0.30, 0.06), spine2, True)
neck1  = bone('neck1',   (0, -0.28, 0.07), (0, -0.42, 0.17), spine3, True)
neck2  = bone('neck2',   (0, -0.42, 0.17), (0, -0.55, 0.29), neck1, True)
head   = bone('head',    (0, -0.55, 0.29), (0, -0.86, 0.36), neck2, True)
tail1  = bone('tail1',   (0, 0.42, 0.04), (0, 0.74, 0.09), spine1)
tail2  = bone('tail2',   (0, 0.74, 0.09), (0, 1.14, 0.15), tail1, True)

for s, sx in (('L', 1), ('R', -1)):
    a = bone(f'wing_a.{s}', (sx*0.15, 0, 0.13), (sx*0.45, 0, 0.15), spine2)
    b = bone(f'wing_b.{s}', (sx*0.45, 0, 0.15), (sx*0.76, 0, 0.17), a, True)
    bone(f'wing_c.{s}',     (sx*0.76, 0, 0.17), (sx*1.08, 0, 0.18), b, True)
    th = bone(f'thigh.{s}', (sx*0.15, 0.03, -0.34), (sx*0.15, 0.006, -0.58), spine1)
    sh = bone(f'shin.{s}',  (sx*0.15, 0.006, -0.58), (sx*0.15, -0.02, -0.82), th, True)
    bone(f'foot.{s}',       (sx*0.15, -0.02, -0.82), (sx*0.15, -0.20, -0.86), sh, True)
bpy.ops.object.mode_set(mode='OBJECT')

# ── Smooth skinning via heat-diffusion automatic weights ──────────────────
bpy.ops.object.select_all(action='DESELECT')
mesh.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type='ARMATURE_AUTO')

# Pin the detached bits that heat diffusion cannot reason about
forced = [g for g in mesh.vertex_groups if g.name.startswith('FORCE_')]
for g in forced:
    target = g.name[len('FORCE_'):]
    idx = [v.index for v in mesh.data.vertices
           if any(gr.group == g.index for gr in v.groups)]
    for i in idx:
        for gr in list(mesh.data.vertices[i].groups):
            grp = mesh.vertex_groups[gr.group]
            if grp.name != target:
                grp.remove([i])
    mesh.vertex_groups[target].add(idx, 1.0, 'REPLACE')
for g in forced:
    mesh.vertex_groups.remove(g)

# How smooth is the skinning? Count vertices influenced by >1 bone.
multi = sum(1 for v in mesh.data.vertices if len(v.groups) > 1)
influence = {}
for v in mesh.data.vertices:
    influence[len(v.groups)] = influence.get(len(v.groups), 0) + 1

# ── Animation ─────────────────────────────────────────────────────────────
bpy.context.scene.render.fps = 24
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
for b in arm.pose.bones: b.rotation_mode = 'XYZ'

_AX = {}
def axis_for(bone, world_axis):
    k = (bone, world_axis)
    if k not in _AX:
        mtx = arm.pose.bones[bone].matrix
        best, dot_best = 0, 0.0
        for i in range(3):
            dot = mtx.col[i][:3][world_axis]
            if abs(dot) > abs(dot_best): dot_best, best = dot, i
        _AX[k] = (best, 1.0 if dot_best > 0 else -1.0)
    return _AX[k]

X, Y, Z = 0, 1, 2
def key(bone, frame, deg, world_axis):
    pb = arm.pose.bones[bone]
    i, sign = axis_for(bone, world_axis)
    pb.rotation_euler[i] = math.radians(deg) * sign
    pb.keyframe_insert('rotation_euler', index=i, frame=frame)

def key_lift(frame, amount):
    pb = arm.pose.bones['root']
    pb.location[1] = amount
    pb.keyframe_insert('location', index=1, frame=frame)

def reset():
    for b in arm.pose.bones:
        b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0)

def action(name):
    a = bpy.data.actions.new(name); a.use_fake_user = True
    arm.animation_data_create(); arm.animation_data.action = a
    return a

# Wings run along +/-X, so a beat is a rotation about world Y, opposite per side.
# Positive rotates the tip down, negative lifts it.
#
# These bones are a CHAIN (wing_c child of wing_b child of wing_a), so rotations
# accumulate down it: what each segment gets is a *contribution*, not the angle
# the tip ends up at. Treating them as absolute angles tripled every pose --
# a -15 degree fold became -45 at the tip and threw the wing over the bird's back.
SEG_AMP = (1.00, 0.30, 0.22)   # fractions of the beat, summing to ~1.5x at the tip
LAG     = (0.00, 0.16, 0.32)   # outer segments lag, which gives the beat its curl

def wingbeat(f, th, amp, bias=(0.0, 0.0, 0.0)):
    for i, seg in enumerate('abc'):
        a = amp * SEG_AMP[i] * math.sin(th - TAU * LAG[i]) + bias[i]
        key(f'wing_{seg}.L', f,  a, Y)
        key(f'wing_{seg}.R', f, -a, Y)

def wingfold(f, sweep):
    """Sweep the wings back along the flanks (rotation about world Z).

    A perched bird folds its wings back over its body, not just down -- without
    this it sits on a branch with both wings held out sideways. Values are per
    segment and accumulate down the chain, same as the beat.
    """
    for i, seg in enumerate('abc'):
        key(f'wing_{seg}.L', f,  sweep[i], Z)
        key(f'wing_{seg}.R', f, -sweep[i], Z)

def tuck(f, amount):
    # Also a chain: thigh -> shin -> foot. `amount` is 0 for standing and 1 for
    # fully folded against the belly; 34 degrees of thigh swing (what this used to
    # do) leaves the legs dangling in flight, which looks like the bird forgot them.
    # Angles solved so the toe ends up at the belly line (z ~= -0.41) and tucked
    # back under the tail, rather than hanging below the body. Each value is
    # relative to its parent, since these are chained bones.
    for s in 'LR':
        key(f'thigh.{s}', f,  136 * amount, X)
        key(f'shin.{s}',  f, -120 * amount, X)
        key(f'foot.{s}',  f,   70 * amount, X)

# flap
reset(); flap_a = action('flap')
N = 14
for i in range(N + 1):
    f, th = 1 + i, TAU * (i / N)
    wingbeat(f, th, 30)
    wingfold(f, (10, 6, 4))
    tuck(f, 1.0)
    key('spine1', f, -3 * math.cos(th), X)
    key('spine3', f, -4 * math.cos(th), X)
    key('neck1', f, 3 * math.cos(th), X)
    key('head',  f, 3 * math.cos(th), X)
    key('tail1', f, 6 * math.sin(th) - 3, X)
    key('tail2', f, 5 * math.sin(th - 0.5), X)
    key_lift(f, 0.10 * math.cos(th))

# glide
reset(); glide_a = action('glide')
G = 60
for i in range(G + 1):
    f, th = 1 + i, TAU * (i / G)
    wingbeat(f, th, 3, bias=(-5, -2, -1))
    wingfold(f, (8, 5, 3))
    tuck(f, 1.0)
    key('spine1', f, -2, X)
    key('neck1', f, 2 * math.sin(th), X)
    key('head',  f, 2 * math.sin(th), X)
    key('tail1', f, -2 + 3 * math.sin(th), X)
    key('tail2', f, 2 * math.sin(th - 0.4), X)
    key_lift(f, 0.03 * math.sin(th))

# perch
reset(); perch_a = action('perch')
P = 84
for i in range(P + 1):
    f, th = 1 + i, TAU * (i / P)
    look = -24 if 0.30 < (i / P) < 0.44 else 0
    wingbeat(f, th, 1.5, bias=(11, 7, 5))
    wingfold(f, (44, 27, 17))   # tucked back along the body
    tuck(f, 0.0)
    key('spine1', f, 1.5 * math.sin(th * 2), X)
    key('spine3', f, 2 * math.sin(th * 2), X)
    key('neck1', f, 3 * math.sin(th * 3) + look * 0.6, X)
    key('head',  f, 4 * math.sin(th * 3) + look, X)
    key('tail1', f, 8 + 4 * math.sin(th * 2), X)
    key('tail2', f, 3 * math.sin(th * 2 - 0.4), X)
    key_lift(f, 0.0)

# ── Verify the beat is vertical and the chain actually curls ──────────────
def _footz(act):
    arm.animation_data.action = act
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    return round((arm.matrix_world @ arm.pose.bones['foot.L'].tail).z, 2)

arm.animation_data.action = flap_a
def wpos(bone, frame):
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    return (arm.matrix_world @ arm.pose.bones[bone].tail).copy()
lo, hi = wpos('wing_c.L', 1), wpos('wing_c.L', 5)
travel = {'dX': round(hi[0]-lo[0],2), 'dY_foreaft': round(hi[1]-lo[1],2),
          'dZ_vertical': round(hi[2]-lo[2],2)}
# Tip should sweep further than the shoulder joint if the lag is working
sh_lo, sh_hi = wpos('wing_a.L', 1), wpos('wing_a.L', 5)
curl = {'tip_dZ': round(abs(hi[2]-lo[2]),2), 'shoulder_dZ': round(abs(sh_hi[2]-sh_lo[2]),2)}

# Peak tip elevation over the whole beat, as an angle from the shoulder. Chained
# bones make it easy to overshoot without noticing; a real wingbeat stays well
# under 90 degrees.
shoulder = Vector((0.15, 0, 0.13))
peak = 0.0
for fr in range(1, N + 2):
    t = wpos('wing_c.L', fr)
    d = t - shoulder
    peak = max(peak, abs(math.degrees(math.atan2(d.z, abs(d.x)))))
curl['peakTipAngleDeg'] = round(peak, 1)
# Tucked feet should sit up near the belly, not hang below it
footz = {'flap': _footz(flap_a), 'glide': _footz(glide_a), 'perch': _footz(perch_a),
         'bodyBottomZ': -0.40}
# A folded wing should sit closer to the body (smaller |x|) and further back (+y)
def _tip(act):
    arm.animation_data.action = act
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    t = arm.matrix_world @ arm.pose.bones['wing_c.L'].tail
    return [round(t.x, 2), round(t.y, 2), round(t.z, 2)]
fold = {'restTipX': 1.08, 'flapTip': _tip(flap_a), 'glideTip': _tip(glide_a),
        'perchTip': _tip(perch_a)}
for name, act in (('flap', flap_a), ('glide', glide_a), ('perch', perch_a)):
    arm.animation_data.action = act
    hi_a = 0.0
    for fr in range(1, 8):
        t = wpos('wing_c.L', fr); d = t - shoulder
        hi_a = max(hi_a, abs(math.degrees(math.atan2(d.z, abs(d.x)))))
    curl[name + 'MaxTipDeg'] = round(hi_a, 1)
arm.animation_data.action = flap_a

# ── Previews ─────────────────────────────────────────────────────────────
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.color_type = 'MATERIAL'   # show the palette, not flat grey
sc.display.shading.light = 'STUDIO'
sc.render.resolution_x, sc.render.resolution_y = 900, 700
cd = bpy.data.cameras.new('c'); cd.type = 'ORTHO'; cd.ortho_scale = 3.6
cam = bpy.data.objects.new('c', cd); bpy.context.collection.objects.link(cam)
sc.camera = cam
def shot(path, loc, target=(0, 0, 0)):
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)

for i, f in enumerate([1, 4, 8, 11]):
    sc.frame_set(f); shot(f'{OUT}/bird-flap{i}.png', (-2.6, -2.2, 1.6))
arm.animation_data.action = perch_a
sc.frame_set(1); shot(f'{OUT}/bird-perch.png', (-2.6, -2.2, 1.2))
sc.frame_set(1); shot(f'{OUT}/bird-side.png', (-3.4, 0.0, 0.25))
sc.frame_set(1); shot(f'{OUT}/bird-front.png', (0.0, -3.4, 0.25))

bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.export_scene.gltf(filepath=GLB, export_format='GLB',
                          export_animations=True, export_animation_mode='ACTIONS',
                          export_bake_animation=True,
                          export_skins=True)
print('BLENDER_JSON_START')
print(json.dumps({'actions': [a.name for a in bpy.data.actions],
                  'bones': len(ad.bones), 'tris': len(mesh.data.polygons),
                  'verts': len(mesh.data.vertices),
                  'vertsWithMultipleBones': multi,
                  'influenceHistogram': influence,
                  'wingTipTravel': travel, 'curl': curl, 'footHeight': footz,
                  'wingFold': fold,
                  'eyes': _eye_report, 'partBounds': PART_BOUNDS}, indent=1))
print('BLENDER_JSON_END')
