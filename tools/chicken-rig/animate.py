import bpy, sys, math, json
sys.path.insert(0, sys.argv[sys.argv.index('--')+1])
from riglib import build, setup_render_iso, render
SRC = sys.argv[sys.argv.index('--')+2]
DST = sys.argv[sys.argv.index('--')+3]
OUT = sys.argv[sys.argv.index('--')+4]

mesh, arm, counts = build(SRC)
bpy.context.scene.render.fps = 24
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
for b in arm.pose.bones:
    b.rotation_mode = 'XYZ'

TAU = math.pi * 2

# A bone's local axes depend on its rest orientation and roll, so the axis that
# swings a limb fore/aft is not the same index for every bone. The chicken faces
# -X, so a fore/aft swing is a rotation about world Y: for each bone, find which
# local axis points along world Y and key that one. Picking the wrong index is
# what makes legs swing sideways instead of striding.
_SWING = {}
def swing_axis(bone):
    if bone not in _SWING:
        m = arm.pose.bones[bone].matrix
        best, dot_best = 0, 0.0
        for i in range(3):
            dot = m.col[i][:3][1]          # component along world +Y
            if abs(dot) > abs(dot_best):
                dot_best, best = dot, i
        _SWING[bone] = (best, 1.0 if dot_best > 0 else -1.0)
    return _SWING[bone]

def key(bone, frame, rx=None, loc_y=None):
    pb = arm.pose.bones[bone]
    if rx is not None:
        idx, sign = swing_axis(bone)
        pb.rotation_euler[idx] = math.radians(rx) * sign
        pb.keyframe_insert('rotation_euler', index=idx, frame=frame)
    if loc_y is not None:
        pb.location[1] = loc_y              # local Y runs along the bone
        pb.keyframe_insert('location', index=1, frame=frame)

def new_action(name):
    a = bpy.data.actions.new(name)
    a.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = a
    return a

def reset():
    for b in arm.pose.bones:
        b.rotation_euler = (0,0,0); b.location = (0,0,0)

# ── walk: legs alternate, body bobs twice per cycle, head bobs like a chicken ──
reset(); walk = new_action('walk')
FRAMES = 24
for i in range(FRAMES + 1):          # +1 duplicates frame 1 for a seamless loop
    f = 1 + i
    th = TAU * (i / FRAMES)
    key('thigh.L', f, rx=  30 * math.sin(th))
    key('thigh.R', f, rx= -30 * math.sin(th))
    key('foot.L',  f, rx= -18 * math.sin(th))
    key('foot.R',  f, rx=  18 * math.sin(th))
    key('root',    f, loc_y = -3.0 * abs(math.cos(th)))   # dip on each footfall
    key('head',    f, rx =  7 * math.sin(th * 2))
    key('tail',    f, rx = -5 * math.sin(th) + 4)

# ── idle: slow breathing sway with an occasional peck ──────────────────────
reset(); idle = new_action('idle')
IF = 72
for i in range(IF + 1):
    f = 1 + i
    th = TAU * (i / IF)
    peck = 0.0
    if 0.45 < (i / IF) < 0.62:        # quick dip of the head, then back up
        p = ((i / IF) - 0.45) / 0.17
        peck = -38 * math.sin(math.pi * p)
    key('head', f, rx = 4 * math.sin(th * 2) + peck)
    key('root', f, loc_y = -0.8 * math.sin(th * 2))
    key('tail', f, rx = 3 * math.sin(th * 3))
    key('thigh.L', f, rx = 2 * math.sin(th))
    key('thigh.R', f, rx = -2 * math.sin(th))

# ── fly: legs swept back, body pitched, quick oscillation ──────────────────
reset(); fly = new_action('fly')
FF = 12
for i in range(FF + 1):
    f = 1 + i
    th = TAU * (i / FF)
    key('thigh.L', f, rx = -42 + 6 * math.sin(th))
    key('thigh.R', f, rx = -42 - 6 * math.sin(th))
    key('foot.L',  f, rx =  25)
    key('foot.R',  f, rx =  25)
    key('head',    f, rx =  12 + 4 * math.sin(th))
    key('tail',    f, rx = -14 + 5 * math.sin(th))
    key('root',    f, loc_y = 1.5 * math.sin(th))

for a in (walk, idle, fly):
    a.use_fake_user = True

# Render a few walk frames so the cycle can be eyeballed
arm.animation_data.action = walk
setup_render_iso()
for i, f in enumerate([1, 7, 13, 19]):
    bpy.context.scene.frame_set(f)
    render(f'{OUT}/walk-f{i}.png')

# Verify numerically that the walk swings the foot fore/aft, not sideways
arm.animation_data.action = walk
def foot_tip_at(frame):
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    return (arm.matrix_world @ arm.pose.bones['foot.L'].tail).copy()
a, b2 = foot_tip_at(1), foot_tip_at(7)
travel = {'dX_foreaft': round(b2[0]-a[0],1), 'dY_sideways': round(b2[1]-a[1],1),
          'dZ_up': round(b2[2]-a[2],1)}
axes = {k: v for k, v in _SWING.items()}

bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.export_scene.gltf(
    filepath=DST, export_format='GLB',
    export_animations=True, export_animation_mode='ACTIONS',
    export_bake_animation=True,
)
print('BLENDER_JSON_START')
print(json.dumps({'actions': [a.name for a in bpy.data.actions],
                  'swingAxes': axes, 'footTravel': travel}))
print('BLENDER_JSON_END')
