import bpy, bmesh, math, os, random
OUT = os.environ.get('HATENA_WORK', '/tmp/hatena_work')
T = 1 / 16
WAVE_SIGN = -1.0

def make_image(name, rows):
    h = len(rows); w = len(rows[0])
    img = bpy.data.images.new(name, w, h, alpha=False)
    px = []
    for y in range(h - 1, -1, -1):
        for x in range(w):
            r, g, b = rows[y][x]; px += [r / 255, g / 255, b / 255, 1]
    img.pixels = px; img.pack(); return img

_seed = [0]
def noisy(c, w, h, var=8):
    _seed[0] += 1; r = random.Random(_seed[0])
    out = []
    for _ in range(h):
        row = []
        for _ in range(w):
            d = r.randint(-var, var); row.append(tuple(max(0, min(255, c[i] + d)) for i in range(3)))
        out.append(row)
    return out
def flipx(g): return [list(reversed(r)) for r in g]

def mat_from(name, rows, metallic=0.0, rough=0.85):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metallic
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = make_image(name, rows); t.interpolation = 'Closest'
    nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    return m

def box(name, size, pivot, offset, mats, col):
    sx, sy, sz = [s * T / 2 for s in size]
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    ox, oy, oz = offset
    c = {(ix, iy, iz): bm.verts.new((ox + ix * sx, oy + iy * sy, oz + iz * sz)) for ix in (-1, 1) for iy in (-1, 1) for iz in (-1, 1)}
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
    for i, k in enumerate(order):
        f = bm.faces.new(faces[k]); f.material_index = i
        for lp, uv in zip(f.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]): lp[uvl].uv = uv
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    for k in order: me.materials.append(mats.get(k, mats.get('side')))
    ob.location = pivot; col.objects.link(ob)
    return ob

def same(m, top=None, bottom=None):
    return {'side': m, 'top': top or m, 'bottom': bottom or m}

# ================= ROBOT =================
SIL = (200, 200, 206); SIL_D = (150, 150, 158); MOSS = (112, 122, 58); MOSS2 = (140, 150, 70)
DARK = (28, 28, 34); GLINT = (110, 140, 255)
SHIRT = (188, 188, 194); SLEEVE = (172, 172, 178); GLOVE = (226, 220, 204); PANT = (34, 34, 40); SHOE = (222, 222, 228)

def moss_patch(g, cells):
    r = random.Random(len(cells))
    for (y, x) in cells:
        if 0 <= y < len(g) and 0 <= x < len(g[0]): g[y][x] = MOSS if r.random() < .6 else MOSS2

def rob_face():
    g = noisy(SIL, 10, 10, 14)
    for i in range(10): g[0][i] = SIL_D; g[9][i] = SIL_D; g[i][0] = SIL_D; g[i][9] = SIL_D
    for (y, x) in [(4, 2), (4, 3), (5, 2), (5, 3), (4, 6), (4, 7), (5, 6), (5, 7)]: g[y][x] = DARK
    g[4][2] = GLINT
    g[7][4] = DARK; g[7][5] = DARK
    moss_patch(g, [(6, 2), (7, 2), (8, 2), (6, 3)])           # mossy "tear"
    moss_patch(g, [(0, 0), (0, 1), (1, 0), (0, 8), (0, 9), (1, 9), (2, 9)])
    return g
def rob_side():
    g = noisy(SIL, 10, 10, 14)
    for i in range(10): g[0][i] = SIL_D; g[9][i] = SIL_D; g[i][0] = SIL_D; g[i][9] = SIL_D
    moss_patch(g, [(0, 7), (0, 8), (0, 9), (1, 8), (1, 9), (2, 9), (3, 9)])
    return g
def rob_top():
    g = noisy(SIL, 10, 10, 14)
    moss_patch(g, [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (8, 9), (9, 9), (9, 8), (8, 8), (0, 9)])
    return g

def build_robot(col, x0):
    M = {}
    M['face'] = mat_from('Robo_Face', rob_face(), 0.55, 0.45)
    M['side_r'] = mat_from('Robo_SideR', rob_side(), 0.55, 0.45)
    M['side_l'] = mat_from('Robo_SideL', flipx(rob_side()), 0.55, 0.45)
    M['back'] = mat_from('Robo_Back', noisy(SIL, 10, 10, 14), 0.55, 0.45)
    M['top'] = mat_from('Robo_Top', rob_top(), 0.55, 0.45)
    M['foil'] = mat_from('Robo_Foil', noisy((205, 205, 212), 6, 2, 30), 1.0, 0.3)
    M['bolt'] = mat_from('Robo_Bolt', noisy((120, 120, 128), 3, 3, 10), 0.7, 0.4)
    bf = noisy(SHIRT, 8, 12, 6)
    for y in range(0, 7): bf[y][4] = (150, 150, 158)
    bf[0] = [(185, 185, 192)] * 8; bf[0][4] = (150, 150, 158)
    M['body_f'] = mat_from('Robo_BodyF', bf)
    M['body_s'] = mat_from('Robo_BodyS', noisy(SHIRT, 4, 12, 6))
    M['body_b'] = mat_from('Robo_BodyB', noisy(SHIRT, 8, 12, 6))
    arm = noisy(SHIRT, 4, 12, 6)
    for y in range(4, 9): arm[y] = [tuple(v + random.randint(-6, 6) for v in SLEEVE) for _ in range(4)]
    arm[3] = [(180, 180, 186)] * 4
    for y in range(9, 12): arm[y] = noisy(GLOVE, 4, 1, 16)[0]
    M['arm'] = mat_from('Robo_Arm', arm)
    M['glove'] = mat_from('Robo_Glove', noisy(GLOVE, 4, 4, 16))
    leg = noisy(PANT, 4, 12, 5)
    for y in range(10, 12): leg[y] = noisy(SHOE, 4, 1, 8)[0]
    M['leg'] = mat_from('Robo_Leg', leg)
    M['shoe'] = mat_from('Robo_Shoe', noisy(SHOE, 4, 4, 8))
    M['pant'] = mat_from('Robo_Pant', noisy(PANT, 8, 4, 5))

    hip, neck = 12 * T, 24 * T
    parts = {}
    parts['Leg.L'] = [box('Robo_Leg.L', (4, 4, 12), (2 * T, 0, hip), (0, 0, -6 * T), same(M['leg'], bottom=M['shoe']), col)]
    parts['Leg.R'] = [box('Robo_Leg.R', (4, 4, 12), (-2 * T, 0, hip), (0, 0, -6 * T), same(M['leg'], bottom=M['shoe']), col)]
    parts['Hips'] = [box('Robo_Body', (8, 4, 12), (0, 0, hip), (0, 0, 6 * T),
                         {'front': M['body_f'], 'back': M['body_b'], 'side': M['body_s'], 'top': M['body_s'], 'bottom': M['pant']}, col)]
    parts['Arm.L'] = [box('Robo_Arm.L', (4, 4, 12), (6 * T, 0, neck - 2 * T), (0, 0, -4 * T), same(M['arm'], bottom=M['glove']), col)]
    parts['Arm.R'] = [box('Robo_Arm.R', (4, 4, 12), (-6 * T, 0, neck - 2 * T), (0, 0, -4 * T), same(M['arm'], bottom=M['glove']), col)]
    parts['Head'] = [
        box('Robo_Neck', (6, 6, 2), (0, 0, neck), (0, 0, 1 * T), same(M['foil']), col),
        box('Robo_Head', (10, 10, 10), (0, 0, neck), (0, 0, 7 * T),
            {'front': M['face'], 'back': M['back'], 'left': M['side_l'], 'right': M['side_r'], 'top': M['top'], 'bottom': M['back']}, col),
        box('Robo_Bolt.L', (1, 3, 3), (0, 0, neck), (5.5 * T, 0.5 * T, 7 * T), same(M['bolt']), col),
        box('Robo_Bolt.R', (1, 3, 3), (0, 0, neck), (-5.5 * T, 0.5 * T, 7 * T), same(M['bolt']), col),
    ]
    return make_rig('Robo', col, parts, x0, head_top=neck + 12 * T, arm_x=6 * T)

# ================= OL =================
HAIR = (112, 66, 42); HAIR_D = (88, 50, 32); SKIN = (246, 212, 186); EYE = (58, 34, 30)
CHEEK = (250, 160, 170); LIP = (226, 104, 120); NAVY = (52, 62, 105); NAVY_D = (44, 50, 88)
BLOUSE = (250, 250, 250); RIBBON = (240, 120, 155); STOCK = (232, 198, 172); PUMP = (30, 24, 30)

def ol_face():
    g = noisy(SKIN, 8, 8, 4)
    for x in range(8): g[0][x] = HAIR; g[1][x] = HAIR
    for x in (0, 1, 3, 4, 6, 7): g[2][x] = HAIR
    g[2][2] = HAIR_D
    for y in range(3, 8): g[y][0] = HAIR; g[y][7] = HAIR
    g[1][6] = (255, 170, 200)  # hair clip
    W_ = (255, 255, 255)
    g[4][1] = EYE; g[4][2] = W_; g[5][1] = EYE; g[5][2] = EYE
    g[4][5] = EYE; g[4][6] = W_; g[5][5] = EYE; g[5][6] = EYE
    g[3][1] = HAIR_D; g[3][6] = HAIR_D
    g[6][1] = CHEEK; g[6][6] = CHEEK
    g[6][3] = (232, 130, 140); g[6][4] = (232, 130, 140)
    g[2][2] = HAIR
    return g
def ol_side():  # +X face: image right = back
    g = noisy(SKIN, 8, 8, 4)
    for y in range(8):
        for x in range(8):
            if y < 2 or x >= 3 or (x == 2 and y < 6): g[y][x] = HAIR
    g[4][1] = (240, 200, 175)
    return g

def build_ol(col, x0):
    M = {}
    M['face'] = mat_from('OL_Face', ol_face())
    M['side_r'] = mat_from('OL_SideR', ol_side())
    M['side_l'] = mat_from('OL_SideL', flipx(ol_side()))
    M['hair'] = mat_from('OL_Hair', noisy(HAIR, 8, 8, 8))
    M['hairlong'] = mat_from('OL_HairLong', noisy(HAIR, 8, 10, 8))
    M['chin'] = mat_from('OL_Chin', noisy(SKIN, 8, 8, 4))
    bf = noisy(NAVY, 8, 12, 5)
    for y in range(0, 8):
        for x in range(8):
            if 3 <= x <= 4 or (y < 3 and 2 <= x <= 5): bf[y][x] = BLOUSE
    bf[1][3] = RIBBON; bf[1][4] = RIBBON; bf[2][3] = RIBBON
    bf[5][6] = (235, 235, 245); bf[6][6] = (90, 140, 220)  # ID card
    for y in range(8, 12): bf[y] = noisy(NAVY_D, 8, 1, 4)[0]
    bf[7] = [(40, 40, 50)] * 8
    M['body_f'] = mat_from('OL_BodyF', bf)
    bb = noisy(NAVY, 8, 12, 5)
    bb[0] = [BLOUSE] * 8
    for y in range(8, 12): bb[y] = noisy(NAVY_D, 8, 1, 4)[0]
    M['body_b'] = mat_from('OL_BodyB', bb)
    bs = noisy(NAVY, 4, 12, 5)
    for y in range(8, 12): bs[y] = noisy(NAVY_D, 4, 1, 4)[0]
    M['body_s'] = mat_from('OL_BodyS', bs)
    M['body_t'] = mat_from('OL_BodyT', noisy(BLOUSE, 8, 4, 3))
    arm = noisy(NAVY, 3, 12, 5)
    arm[8] = [BLOUSE] * 3
    for y in range(9, 12): arm[y] = noisy(SKIN, 3, 1, 4)[0]
    M['arm'] = mat_from('OL_Arm', arm)
    M['armtop'] = mat_from('OL_ArmTop', noisy(NAVY, 3, 4, 5))
    M['hand'] = mat_from('OL_Hand', noisy(SKIN, 3, 4, 4))
    leg = noisy(STOCK, 4, 12, 4)
    for y in range(0, 3): leg[y] = noisy(NAVY_D, 4, 1, 4)[0]
    for y in range(10, 12): leg[y] = noisy(PUMP, 4, 1, 4)[0]
    M['leg'] = mat_from('OL_Leg', leg)
    M['pump'] = mat_from('OL_Pump', noisy(PUMP, 4, 4, 4))
    M['skirt'] = mat_from('OL_Skirt', noisy(NAVY_D, 8, 4, 4))

    hip, neck = 12 * T, 24 * T
    parts = {}
    parts['Leg.L'] = [box('OL_Leg.L', (4, 4, 12), (2 * T, 0, hip), (0, 0, -6 * T), same(M['leg'], bottom=M['pump']), col)]
    parts['Leg.R'] = [box('OL_Leg.R', (4, 4, 12), (-2 * T, 0, hip), (0, 0, -6 * T), same(M['leg'], bottom=M['pump']), col)]
    parts['Hips'] = [box('OL_Body', (8, 4, 12), (0, 0, hip), (0, 0, 6 * T),
                         {'front': M['body_f'], 'back': M['body_b'], 'side': M['body_s'], 'top': M['body_t'], 'bottom': M['skirt']}, col)]
    parts['Arm.L'] = [box('OL_Arm.L', (3, 4, 12), (5.5 * T, 0, neck - 2 * T), (0, 0, -4 * T), same(M['arm'], top=M['armtop'], bottom=M['hand']), col)]
    parts['Arm.R'] = [box('OL_Arm.R', (3, 4, 12), (-5.5 * T, 0, neck - 2 * T), (0, 0, -4 * T), same(M['arm'], top=M['armtop'], bottom=M['hand']), col)]
    parts['Head'] = [
        box('OL_Head', (8, 8, 8), (0, 0, neck), (0, 0, 4 * T),
            {'front': M['face'], 'back': M['hair'], 'left': M['side_l'], 'right': M['side_r'], 'top': M['hair'], 'bottom': M['chin']}, col),
        box('OL_HairLong', (8.6, 1.4, 10), (0, 0, neck), (0, 4.3 * T, 1 * T), same(M['hairlong']), col),
    ]
    return make_rig('OL', col, parts, x0, head_top=neck + 8 * T, arm_x=5.5 * T)

# ================= rig & actions =================
def make_rig(prefix, col, parts, x0, head_top, arm_x):
    hip, neck = 12 * T, 24 * T
    ad = bpy.data.armatures.new(prefix + 'Rig'); rig = bpy.data.objects.new(prefix + 'Rig', ad)
    col.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    eb = ad.edit_bones
    def bone(n, h, t, p=None):
        b = eb.new(n); b.head = h; b.tail = t
        if p: b.parent = eb[p]
    bone('Root', (0, 0, 0), (0, 0, hip))
    bone('Hips', (0, 0, hip), (0, 0, neck), 'Root')
    bone('Head', (0, 0, neck), (0, 0, head_top), 'Hips')
    bone('Arm.L', (arm_x, 0, neck - 2 * T), (arm_x, 0, neck - 12 * T), 'Hips')
    bone('Arm.R', (-arm_x, 0, neck - 2 * T), (-arm_x, 0, neck - 12 * T), 'Hips')
    bone('Leg.L', (2 * T, 0, hip), (2 * T, 0, 0), 'Root')
    bone('Leg.R', (-2 * T, 0, hip), (-2 * T, 0, 0), 'Root')
    bpy.ops.object.mode_set(mode='OBJECT')
    for bn, obs in parts.items():
        for ob in obs:
            mw = ob.matrix_world.copy()
            ob.parent = rig; ob.parent_type = 'BONE'; ob.parent_bone = bn
            bpy.context.view_layer.update(); ob.matrix_world = mw
    rig.location.x = x0
    rig.animation_data_create()
    pb = rig.pose.bones
    for p in pb: p.rotation_mode = 'XYZ'
    Z = (0, 0, 0)
    def key(f, rots, loc=(0, 0, 0)):
        full = {'Hips': Z, 'Head': Z, 'Arm.L': Z, 'Arm.R': Z, 'Leg.L': Z, 'Leg.R': Z}; full.update(rots)
        for n, r in full.items():
            pb[n].rotation_euler = tuple(math.radians(v) for v in r); pb[n].keyframe_insert('rotation_euler', frame=f)
        pb['Root'].location = loc; pb['Root'].keyframe_insert('location', frame=f)
    def act(name):
        a = bpy.data.actions.new(f'{prefix}_{name}'); a.use_fake_user = True
        rig.animation_data.action = a; return a
    act('Walk')
    for f, s in [(1, 1), (7, 0), (13, -1), (19, 0), (25, 1)]:
        a = 35 * s
        key(f, {'Leg.L': (a, 0, 0), 'Leg.R': (-a, 0, 0), 'Arm.L': (-a, 0, 0), 'Arm.R': (a, 0, 0), 'Head': (0, 0, 3 * s)}, (0, 0, 0.03 * (1 - abs(s))))
    act('Wave')
    for f, s in [(1, 1), (9, -1), (17, 1), (25, -1), (33, 1)]:
        key(f, {'Arm.L': (0, 0, WAVE_SIGN * (145 + 20 * s)), 'Head': (0, 6 * s, 0)})
    act('WaveR')
    for f, s in [(1, 1), (9, -1), (17, 1), (25, -1), (33, 1)]:
        key(f, {'Arm.R': (0, 0, -WAVE_SIGN * (145 + 20 * s)), 'Head': (0, -6 * s, 0)})
    act('Surprised')
    key(1, {})
    key(6, {'Arm.L': (-15, 0, WAVE_SIGN * 135), 'Arm.R': (-15, 0, -WAVE_SIGN * 135), 'Head': (-12, 0, 0), 'Hips': (-6, 0, 0)}, (0, 0, 0.12))
    key(12, {'Arm.L': (-15, 0, WAVE_SIGN * 125), 'Arm.R': (-15, 0, -WAVE_SIGN * 125), 'Head': (-10, 0, 0), 'Hips': (-4, 0, 0)})
    key(20, {})
    act('Talk')  # head nods + hand gesture
    for f, s in [(1, 0), (6, 1), (11, 0), (16, 1), (21, 0)]:
        key(f, {'Head': (-6 * s, 4 * s, 0), 'Arm.R': (-50 - 10 * s, 0, 8), 'Arm.L': (0, 0, 0)})
    act('Think')  # hand on chin
    key(1, {'Arm.R': (-115, 0, -25), 'Arm.L': (-30, 0, 30), 'Head': (6, -10, 8)})
    key(30, {'Arm.R': (-118, 0, -25), 'Arm.L': (-30, 0, 30), 'Head': (6, -14, 8)})
    rig.animation_data.action = None
    for p in pb: p.rotation_euler = Z; p.location = Z
    return rig

bpy.ops.wm.read_factory_settings(use_empty=True)
cR = bpy.data.collections.new('Robot'); bpy.context.scene.collection.children.link(cR)
cO = bpy.data.collections.new('OL'); bpy.context.scene.collection.children.link(cO)
robo = build_robot(cR, 0.55)
ol = build_ol(cO, -0.55)
bpy.ops.wm.save_as_mainfile(filepath=f'{OUT}/robot_and_ol.blend', compress=True)
print('BUILD2 OK')
