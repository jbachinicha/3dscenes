import bpy, json, math
from mathutils import Vector

Z_HIP, Z_ANKLE = 48.5, 13.1
Z_HEAD, X_HEAD = 140.0, -20.0
X_TAIL, Z_TAIL = 40.0, 100.0

def build(src):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)
    mesh = next(o for o in bpy.data.objects if o.type == 'MESH')
    bpy.ops.object.select_all(action='DESELECT')
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    mesh.parent = None
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in list(bpy.data.objects):
        if o.type == 'EMPTY': bpy.data.objects.remove(o)

    co = [v.co.copy() for v in mesh.data.vertices]
    def cen(pred):
        pts=[v for v in co if pred(v)]
        return Vector((sum(p.x for p in pts)/len(pts), sum(p.y for p in pts)/len(pts),
                       sum(p.z for p in pts)/len(pts))) if pts else None
    legL = cen(lambda v: Z_ANKLE<=v.z<Z_HIP and v.y>=0)
    legR = cen(lambda v: Z_ANKLE<=v.z<Z_HIP and v.y< 0)
    footL= cen(lambda v: v.z<Z_ANKLE and v.y>=0)
    footR= cen(lambda v: v.z<Z_ANKLE and v.y< 0)
    head = cen(lambda v: v.z>=Z_HEAD and v.x<=X_HEAD)
    tail = cen(lambda v: v.x>=X_TAIL and v.z>=Z_TAIL)
    # Anchor the spine on the legs, not the body centroid: the dense comb drags
    # the body mean far forward, which would put the hips under the head.
    hipX = (legL.x + legR.x) / 2

    ad = bpy.data.armatures.new('ChickenArmature')
    arm = bpy.data.objects.new('ChickenRig', ad)
    bpy.context.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    eb = ad.edit_bones
    def bone(n, h, t, p=None):
        b = eb.new(n); b.head=h; b.tail=t
        if p: b.parent=p; b.use_connect=False
        return b
    root = bone('root',  Vector((hipX,0,0)),        Vector((hipX,0,Z_HIP)))
    hips = bone('hips',  Vector((hipX,0,Z_HIP)),    Vector((hipX,0,Z_HIP+45)), root)
    spine= bone('spine', Vector((hipX,0,Z_HIP+45)), Vector((-25,0,132)), hips)
    bone('head', Vector((-25,0,132)), Vector((head.x,0,head.z)), spine)
    bone('tail', Vector((hipX+35,0,118)), Vector((tail.x,0,tail.z)), hips)
    for s,leg,foot in (('L',legL,footL),('R',legR,footR)):
        th = bone(f'thigh.{s}', Vector((leg.x,leg.y,Z_HIP)), Vector((leg.x,leg.y,Z_ANKLE)), hips)
        bone(f'foot.{s}', Vector((foot.x,foot.y,Z_ANKLE)), Vector((foot.x-18,foot.y,2.0)), th)
    bpy.ops.object.mode_set(mode='OBJECT')

    groups = {n: mesh.vertex_groups.new(name=n) for n in
              ['hips','spine','head','tail','thigh.L','thigh.R','foot.L','foot.R']}
    counts = {k:0 for k in groups}
    for i,v in enumerate(co):
        s = 'L' if v.y>=0 else 'R'
        if   v.z <  Z_ANKLE:                    g=f'foot.{s}'
        elif v.z <  Z_HIP:                      g=f'thigh.{s}'
        elif v.z >= Z_HEAD and v.x <= X_HEAD:   g='head'
        elif v.x >= X_TAIL and v.z >= Z_TAIL:   g='tail'
        elif v.z >= Z_HIP+60:                   g='spine'
        else:                                   g='hips'
        groups[g].add([i], 1.0, 'REPLACE'); counts[g]+=1

    m = mesh.modifiers.new(name='Armature', type='ARMATURE'); m.object = arm
    mesh.parent = arm
    return mesh, arm, counts

def setup_render(mid_x=0, mid_z=95, scale=300):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.render.resolution_x, sc.render.resolution_y = 900, 700
    sc.render.film_transparent = False
    cam_d = bpy.data.cameras.new('cam'); cam_d.type='ORTHO'; cam_d.ortho_scale=scale
    cam = bpy.data.objects.new('cam', cam_d)
    bpy.context.collection.objects.link(cam)
    cam.location = (mid_x, -600, mid_z)
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    return cam

def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

def setup_render_iso(target=(0,0,95), loc=(-380,-460,240), scale=300):
    import bpy, math
    from mathutils import Vector
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.render.resolution_x, sc.render.resolution_y = 900, 700
    cam_d = bpy.data.cameras.new('cam2'); cam_d.type='ORTHO'; cam_d.ortho_scale=scale
    cam = bpy.data.objects.new('cam2', cam_d)
    bpy.context.collection.objects.link(cam)
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z','Y').to_euler()
    sc.camera = cam
    return cam
