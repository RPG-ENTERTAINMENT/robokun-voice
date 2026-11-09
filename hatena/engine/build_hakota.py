import bpy, bmesh, math, os, random, sys
os.makedirs(os.environ.get('HATENA_WORK', '/tmp/hatena_work'), exist_ok=True)
from mathutils import Vector
OUT = os.environ.get('HATENA_WORK', '/tmp/hatena_work')
TX = 1 / 16
WAVE_SIGN = -1.0  # one texel in metres

# ---------------- pixel textures ----------------
def make_image(name, rows):
    """rows: list of lists of RGB tuples (top row first)"""
    h = len(rows); w = len(rows[0])
    img = bpy.data.images.new(name, w, h, alpha=False)
    px = []
    for y in range(h - 1, -1, -1):
        for x in range(w):
            r, g, b = rows[y][x]
            px += [r / 255, g / 255, b / 255, 1]
    img.pixels = px
    img.pack()
    return img

def noisy(c, w, h, var=10, seed=0):
    r = random.Random(seed)
    return [[tuple(max(0, min(255, c[i] + r.randint(-var, var))) for i in range(3)) for _ in range(w)] for _ in range(h)]

SKIN = (238, 196, 160); HAIR = (40, 32, 30); EYE = (30, 30, 40); WHITE = (250, 250, 250)
MOUTH = (170, 80, 70); SUIT = (85, 90, 105); PANTS = (55, 58, 70); SHOE = (35, 30, 30)
TIE = (40, 70, 160); SHIRT = (245, 245, 245)

def face_front():
    g = noisy(SKIN, 8, 8, 6, 1)
    for x in range(8): g[0][x] = HAIR
    for x in range(8):
        if x != 5: g[1][x] = HAIR
    g[2][0] = HAIR; g[2][7] = HAIR
    for x in (1, 2, 5, 6): g[3][x] = HAIR          # eyebrows
    g[4][2] = EYE; g[4][5] = EYE; g[5][2] = EYE; g[5][5] = EYE
    g[5][1] = (240, 170, 160); g[5][6] = (240, 170, 160)  # cheeks
    g[6][3] = MOUTH; g[6][4] = MOUTH
    return g

def head_side(back=False):
    g = noisy(SKIN, 8, 8, 6, 2)
    rows_hair = 8 if back else 3
    for y in range(rows_hair):
        for x in range(8): g[y][x] = HAIR
    if not back:
        for x in range(4, 8): g[3][x] = HAIR  # sideburn toward back
    if back:
        for x in range(8): g[7][x] = SKIN
    return g

def flipx(g): return [list(reversed(r)) for r in g]

def body_front():
    g = noisy(SUIT, 8, 12, 6, 3)
    for y in range(5):
        for x in range(8):
            if abs(x - 3.5) < (5 - y) * 0.45: g[y][x] = SHIRT
    for y in range(1, 8):
        g[y][3] = TIE; g[y][4] = TIE
    g[11] = [(45, 40, 40)] * 8  # belt
    g[11][3] = (200, 180, 90); g[11][4] = (200, 180, 90)
    return g

def body_back():
    g = noisy(SUIT, 8, 12, 6, 4)
    g[0] = [SHIRT] * 8
    g[11] = [(45, 40, 40)] * 8
    return g

def side_tex(base, w, h, foot=None, foot_rows=0, seed=5, collar=False):
    g = noisy(base, w, h, 6, seed)
    for y in range(h - foot_rows, h):
        for x in range(w): g[y][x] = foot
    if collar: g[0] = [SHIRT] * w
    return g

def flat(c, w=4, h=4, seed=6): return noisy(c, w, h, 6, seed)

# ---------------- materials ----------------
def mat_from(name, rows):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Roughness'].default_value = 0.85
    t = nt.nodes.new('ShaderNodeTexImage')
    t.image = make_image(name, rows)
    t.interpolation = 'Closest'
    nt.links.new(t.outputs['Color'], bsdf.inputs['Base Color'])
    return m

# ---------------- textured box ----------------
def box(name, size, pivot, offset, mats):
    """size (x,y,z) in texels; mats dict face->material: front(-y) back(+y) left(-x) right(+x) top bottom.
    pivot = world location of object origin; offset = box center relative to origin (metres)."""
    sx, sy, sz = [s * TX / 2 for s in size]
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    ox, oy, oz = offset
    def v(x, y, z): return bm.verts.new((ox + x * sx, oy + y * sy, oz + z * sz))
    c = {}
    for ix in (-1, 1):
        for iy in (-1, 1):
            for iz in (-1, 1):
                c[(ix, iy, iz)] = v(ix, iy, iz)
    # faces with vertex order: bottom-left, bottom-right, top-right, top-left as seen from outside
    faces = {
        'front': [c[(-1, -1, -1)], c[(1, -1, -1)], c[(1, -1, 1)], c[(-1, -1, 1)]],
        'back': [c[(1, 1, -1)], c[(-1, 1, -1)], c[(-1, 1, 1)], c[(1, 1, 1)]],
        'left': [c[(-1, 1, -1)], c[(-1, -1, -1)], c[(-1, -1, 1)], c[(-1, 1, 1)]],
        'right': [c[(1, -1, -1)], c[(1, 1, -1)], c[(1, 1, 1)], c[(1, -1, 1)]],
        'top': [c[(-1, -1, 1)], c[(1, -1, 1)], c[(1, 1, 1)], c[(-1, 1, 1)]],
        'bottom': [c[(-1, 1, -1)], c[(1, 1, -1)], c[(1, -1, -1)], c[(-1, -1, -1)]],
    }
    order = ['front', 'back', 'left', 'right', 'top', 'bottom']
    uvl = bm.loops.layers.uv.new()
    uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
    for i, k in enumerate(order):
        f = bm.faces.new(faces[k])
        f.material_index = i
        for lp, uv in zip(f.loops, uvs): lp[uvl].uv = uv
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    for k in order: me.materials.append(mats[k])
    ob.location = pivot
    bpy.context.collection.objects.link(ob)
    return ob

# ---------------- build ----------------
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

M = {}
M['face'] = mat_from('Head_Front', face_front())
M['head_l'] = mat_from('Head_Left', head_side())
M['head_r'] = mat_from('Head_Right', flipx(head_side()))
M['head_b'] = mat_from('Head_Back', head_side(back=True))
M['hair'] = mat_from('Head_Top', flat(HAIR, 8, 8))
M['chin'] = mat_from('Head_Bottom', flat(SKIN, 8, 8))
M['body_f'] = mat_from('Body_Front', body_front())
M['body_b'] = mat_from('Body_Back', body_back())
M['body_s'] = mat_from('Body_Side', side_tex(SUIT, 4, 12, (45, 40, 40), 1, collar=True))
M['body_t'] = mat_from('Body_Top', flat(SHIRT, 8, 4))
M['body_bt'] = mat_from('Body_Bottom', flat(PANTS, 8, 4))
M['arm_s'] = mat_from('Arm_Side', side_tex(SUIT, 4, 12, SKIN, 3, 7))
M['arm_t'] = mat_from('Arm_Top', flat(SUIT))
M['hand'] = mat_from('Hand', flat(SKIN))
M['leg_s'] = mat_from('Leg_Side', side_tex(PANTS, 4, 12, SHOE, 2, 8))
M['shoe'] = mat_from('Shoe', flat(SHOE))

def allm(side, top, bottom, front=None):
    return {'front': front or side, 'back': side, 'left': side, 'right': side, 'top': top, 'bottom': bottom}

T = TX
hip_z = 12 * T; neck_z = 24 * T; sh_z = 24 * T
leg_L = box('Leg.L', (4, 4, 12), (2 * T, 0, hip_z), (0, 0, -6 * T), allm(M['leg_s'], M['leg_s'], M['shoe']))
leg_R = box('Leg.R', (4, 4, 12), (-2 * T, 0, hip_z), (0, 0, -6 * T), allm(M['leg_s'], M['leg_s'], M['shoe']))
body = box('Body', (8, 4, 12), (0, 0, hip_z), (0, 0, 6 * T),
           {'front': M['body_f'], 'back': M['body_b'], 'left': M['body_s'], 'right': M['body_s'], 'top': M['body_t'], 'bottom': M['body_bt']})
arm_L = box('Arm.L', (4, 4, 12), (6 * T, 0, sh_z - 2 * T), (0, 0, -4 * T), allm(M['arm_s'], M['arm_t'], M['hand']))
arm_R = box('Arm.R', (4, 4, 12), (-6 * T, 0, sh_z - 2 * T), (0, 0, -4 * T), allm(M['arm_s'], M['arm_t'], M['hand']))
head = box('Head', (8, 8, 8), (0, 0, neck_z), (0, 0, 4 * T),
           {'front': M['face'], 'back': M['head_b'], 'left': M['head_r'], 'right': M['head_l'], 'top': M['hair'], 'bottom': M['chin']})

# ---------------- armature ----------------
arm_data = bpy.data.armatures.new('HakotaRig')
rig = bpy.data.objects.new('HakotaRig', arm_data)
sc.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones
def bone(n, h, t, parent=None):
    b = eb.new(n); b.head = h; b.tail = t
    if parent: b.parent = eb[parent]
    return b
bone('Root', (0, 0, 0), (0, 0, hip_z))
bone('Hips', (0, 0, hip_z), (0, 0, neck_z), 'Root')
bone('Head', (0, 0, neck_z), (0, 0, neck_z + 8 * T), 'Hips')
bone('Arm.L', (6 * T, 0, sh_z - 2 * T), (6 * T, 0, sh_z - 12 * T), 'Hips')
bone('Arm.R', (-6 * T, 0, sh_z - 2 * T), (-6 * T, 0, sh_z - 12 * T), 'Hips')
bone('Leg.L', (2 * T, 0, hip_z), (2 * T, 0, 0), 'Root')
bone('Leg.R', (-2 * T, 0, hip_z), (-2 * T, 0, 0), 'Root')
bpy.ops.object.mode_set(mode='OBJECT')

for ob, bn in [(body, 'Hips'), (head, 'Head'), (arm_L, 'Arm.L'), (arm_R, 'Arm.R'), (leg_L, 'Leg.L'), (leg_R, 'Leg.R')]:
    mw = ob.matrix_world.copy()
    ob.parent = rig; ob.parent_type = 'BONE'; ob.parent_bone = bn
    bpy.context.view_layer.update()
    ob.matrix_world = mw

# ---------------- animations ----------------
rig.animation_data_create()
pb = rig.pose.bones
for p in pb: p.rotation_mode = 'XYZ'

def key(frame, rots, loc=None):
    for n, (x, y, z) in rots.items():
        pb[n].rotation_euler = (math.radians(x), math.radians(y), math.radians(z))
        pb[n].keyframe_insert('rotation_euler', frame=frame)
    if loc is not None:
        pb['Root'].location = loc
        pb['Root'].keyframe_insert('location', frame=frame)

def new_action(name):
    a = bpy.data.actions.new(name); a.use_fake_user = True
    rig.animation_data.action = a
    for p in pb:
        p.rotation_euler = (0, 0, 0); p.location = (0, 0, 0)
    return a

# Walk (24 frames loop)
walk = new_action('Walk')
for f, s in [(1, 1), (7, 0), (13, -1), (19, 0), (25, 1)]:
    a = 35 * s
    key(f, {'Leg.L': (a, 0, 0), 'Leg.R': (-a, 0, 0), 'Arm.L': (-a, 0, 0), 'Arm.R': (a, 0, 0),
            'Head': (0, 0, 3 * s), 'Hips': (0, 0, 0)}, loc=(0, abs(s) * -0.0 + 0, 0.03 * (1 - abs(s))) if True else None)

# Wave (32 frames loop)
wave = new_action('Wave')
for f, s in [(1, 1), (9, -1), (17, 1), (25, -1), (33, 1)]:
    key(f, {'Arm.R': (0, 0, 0), 'Arm.L': (0, 0, WAVE_SIGN * (145 + 20 * s)),
            'Head': (0, 6 * s, 0), 'Leg.L': (0, 0, 0), 'Leg.R': (0, 0, 0), 'Hips': (0, 0, 0)}, loc=(0, 0, 0))

# Surprised (the "え、なんで？" pose, 20 frames)
shock = new_action('Surprised')
key(1, {'Arm.L': (0, 0, 0), 'Arm.R': (0, 0, 0), 'Head': (0, 0, 0), 'Hips': (0, 0, 0), 'Leg.L': (0, 0, 0), 'Leg.R': (0, 0, 0)}, loc=(0, 0, 0))
key(6, {'Arm.L': (-15, 0, WAVE_SIGN * 135), 'Arm.R': (-15, 0, -WAVE_SIGN * 135), 'Head': (-12, 0, 0), 'Hips': (-6, 0, 0), 'Leg.L': (0, 0, 0), 'Leg.R': (0, 0, 0)}, loc=(0, 0, 0.12))
key(12, {'Arm.L': (-15, 0, WAVE_SIGN * 125), 'Arm.R': (-15, 0, -WAVE_SIGN * 125), 'Head': (-10, 0, 0), 'Hips': (-4, 0, 0), 'Leg.L': (0, 0, 0), 'Leg.R': (0, 0, 0)}, loc=(0, 0, 0))
key(20, {'Arm.L': (0, 0, 0), 'Arm.R': (0, 0, 0), 'Head': (0, 0, 0), 'Hips': (0, 0, 0), 'Leg.L': (0, 0, 0), 'Leg.R': (0, 0, 0)}, loc=(0, 0, 0))

for a in (walk, wave, shock):
    for fc in (a.fcurves if hasattr(a, 'fcurves') else []):
        pass
rig.animation_data.action = None
for p in pb: p.rotation_euler = (0, 0, 0); p.location = (0, 0, 0)

# collection tidy
col = bpy.data.collections.new('Hakota')
sc.collection.children.link(col)
for ob in [rig, body, head, arm_L, arm_R, leg_L, leg_R]:
    for c in ob.users_collection: c.objects.unlink(ob)
    col.objects.link(ob)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'hakota_character.blend'), compress=True)
print('BUILD OK')
