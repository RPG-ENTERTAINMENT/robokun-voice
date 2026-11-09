"""Render one cut of an episode with Blender (bpy).
  python render_cut.py <plan.json> <cut index> <outdir>   (HATENA_WORK has world.blend)
Writes <outdir>/cNN/f_####.jpg and heads.json (screen position of each character's head top per frame)."""
import bpy, bmesh, math, sys, os, json, random
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

PLAN = json.load(open(sys.argv[1])); CI = int(sys.argv[2]); OUTROOT = sys.argv[3]
CUT = PLAN['cuts'][CI]
FPS = PLAN.get('cfps', 12)
N = max(2, int(round((CUT['t1'] - CUT['t0']) * FPS)))
OUT = os.path.join(OUTROOT, f'c{CI:02d}'); os.makedirs(OUT, exist_ok=True)
WORK = os.environ.get('HATENA_WORK', '/tmp/hatena_work')
bpy.ops.wm.open_mainfile(filepath=os.path.join(WORK, 'world.blend'))
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, N
OL = bpy.data.objects['OLRig']; RO = bpy.data.objects['RoboRig']
CROWD = [bpy.data.objects[f'Crowd{i}'] for i in range(6)]
cam = bpy.data.objects['Cam']; sun = bpy.data.objects['Sun']
world_bg = sc.world.node_tree.nodes['Background']
OX, SX, BX, BY = 100, 200, 300, 60
fx_col = bpy.data.collections.new('FX'); sc.collection.children.link(fx_col)
R = random.Random(CI * 7 + PLAN.get('no', 1))

# ---------------- helpers ----------------
def newmat(name, rgb, emit=0.0, rough=0.8):
    if name in bpy.data.materials: return bpy.data.materials[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = tuple(rgb) + (1,)
    b.inputs['Roughness'].default_value = rough
    if emit: b.inputs['Emission Color'].default_value = tuple(rgb) + (1,); b.inputs['Emission Strength'].default_value = emit
    return m
for nm, c, e in [('pink', (0.95, 0.55, 0.65), 0), ('pink2', (0.85, 0.42, 0.55), 0), ('cereb', (1.0, 0.45, 0.1), 0.8),
                 ('cyan', (0.2, 0.9, 1.0), 1.0), ('gray', (0.45, 0.47, 0.5), 0), ('glove', (0.9, 0.88, 0.82), 0),
                 ('redglow', (1.0, 0.1, 0.1), 1.5), ('ocean', (0.12, 0.35, 0.85), 0), ('land', (0.25, 0.65, 0.25), 0),
                 ('ice', (0.95, 0.97, 1.0), 0), ('white', (0.95, 0.95, 0.97), 0.3), ('black', (0.03, 0.03, 0.04), 0),
                 ('moon', (1.0, 0.95, 0.6), 2.0), ('star', (1, 1, 0.9), 3.0), ('brown', (0.45, 0.28, 0.15), 0),
                 ('tan', (0.85, 0.65, 0.4), 0), ('graycat', (0.55, 0.55, 0.6), 0), ('fishor', (1.0, 0.5, 0.1), 0.3),
                 ('water', (0.2, 0.5, 0.9), 0.2), ('fire', (1.0, 0.3, 0.02), 2.5), ('fire2', (1.0, 0.75, 0.1), 2.5),
                 ('note1', (1.0, 0.3, 0.5), 1.0), ('note2', (0.3, 0.6, 1.0), 1.0), ('note3', (0.4, 1.0, 0.4), 1.0),
                 ('clockface', (0.97, 0.95, 0.88), 0.2), ('purple', (0.55, 0.3, 0.9), 0.8)]:
    newmat(nm, c, e)

def place(rig, x, y, z=0, look=None, yaw=None):
    rig.location = (x, y, z)
    if look is not None: rig.rotation_euler = (0, 0, math.atan2(look[0] - x, -(look[1] - y)))
    elif yaw is not None: rig.rotation_euler = (0, 0, math.radians(yaw))

def act(rig, name, hold_end=None):
    ad = rig.animation_data or rig.animation_data_create()
    for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
    ad.action = None
    for p in rig.pose.bones: p.rotation_mode = 'XYZ'; p.rotation_euler = (0, 0, 0); p.location = (0, 0, 0)
    if not name or name not in bpy.data.actions: return
    a = bpy.data.actions[name]
    st = ad.nla_tracks.new().strips.new(name, 1, a)
    if hasattr(st, 'action_slot') and getattr(a, 'slots', None): st.action_slot = a.slots[0]
    if hold_end: st.action_frame_end = hold_end; st.extrapolation = 'HOLD'
    else: st.repeat = max(1, math.ceil(N / max(1, a.frame_range[1] - a.frame_range[0])) + 1)

def pose_anim(rig, fn):
    act(rig, None)
    for f in range(1, N + 1):
        for bn, (x, y, z) in fn(f).items():
            pb = rig.pose.bones[bn]; pb.rotation_euler = tuple(math.radians(v) for v in (x, y, z)); pb.keyframe_insert('rotation_euler', frame=f)

def move(rig, p0, p1, f1=None):
    rig.location = p0; rig.keyframe_insert('location', frame=1)
    rig.location = p1; rig.keyframe_insert('location', frame=f1 or N)

def look_rot(pos, tgt, roll=0):
    q = (Vector(tgt) - Vector(pos)).to_track_quat('-Z', 'Y')
    return (q.to_matrix().to_4x4() @ Matrix.Rotation(math.radians(roll), 4, 'Z')).to_euler() if roll else q.to_euler()

def cam_path(keys, shake=0.0):
    for f in range(1, N + 1):
        k0, k1 = keys[0], keys[-1]
        for a, b in zip(keys, keys[1:]):
            if a[0] <= f <= b[0]: k0, k1 = a, b; break
        u = 0 if k1[0] == k0[0] else max(0, min(1, (f - k0[0]) / (k1[0] - k0[0]))); u = u * u * (3 - 2 * u)
        pos = Vector(k0[1]).lerp(Vector(k1[1]), u); tgt = Vector(k0[2]).lerp(Vector(k1[2]), u)
        lens = k0[3] + (k1[3] - k0[3]) * u
        roll = (k0[4] if len(k0) > 4 else 0) * (1 - u) + (k1[4] if len(k1) > 4 else 0) * u
        if shake:
            r = random.Random(f); pos += Vector((r.uniform(-1, 1), 0, r.uniform(-1, 1))) * shake
        cam.location = pos; cam.rotation_euler = look_rot(pos, tgt, roll); cam.data.lens = lens
        cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f); cam.data.keyframe_insert('lens', frame=f)
def two_keys(p0, t0, p1, t1, lens=32, lens1=None): return [(1, p0, t0, lens), (N, p1, t1, lens1 or lens)]

def mk(name, loc, size, matname, parent=None):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); me.materials.append(bpy.data.materials[matname])
    ob.location = loc; fx_col.objects.link(ob)
    if parent: ob.parent = parent
    return ob
def empty(loc):
    e = bpy.data.objects.new('E', None); e.location = loc; fx_col.objects.link(e); return e
def animate(items):
    for ob, fn in items:
        for f in range(1, N + 1):
            loc, s, rz = fn(f)
            ob.location = loc; ob.scale = (s, s, s); ob.rotation_euler = (0, 0, rz)
            ob.keyframe_insert('location', frame=f); ob.keyframe_insert('scale', frame=f); ob.keyframe_insert('rotation_euler', frame=f)

def head_of(rig, h): return rig.location + Vector((0, 0, h))
H_OL, H_RO = 1.62, 1.8

# ---------------- poses ----------------
def tickle_self(f):
    w = math.sin(f * 2.2) * 8
    return {'Arm.R': (-25, 0, -25 + w), 'Arm.L': (-25, 0, 25 - w), 'Head': (8, 0, 0), 'Hips': (0, 0, 0)}
def laugh(f):
    w = math.sin(f * 2.6)
    return {'Arm.R': (-20, 0, -140 + w * 15), 'Arm.L': (-20, 0, 140 - w * 15), 'Head': (-15 + w * 8, w * 10, 0), 'Hips': (-6 + w * 5, 0, w * 6)}
def robo_tickle(f):
    w = math.sin(f * 2.4) * 12
    return {'Arm.R': (-80, 0, w), 'Arm.L': (-80, 0, -w), 'Head': (6, 0, 0), 'Hips': (0, 0, 0)}
def point(f):   # robot points forward / explains
    return {'Arm.R': (-80 - 6 * math.sin(f * 0.6), 0, 10), 'Arm.L': (0, 0, 0), 'Head': (3 * math.sin(f * 0.8), 0, 0), 'Hips': (0, 0, 0)}

# ---------------- set pieces ----------------
def sparkles(center, n=16, spread=(1.6, 0.6, 1.2)):
    c = Vector(center); r = random.Random(7); out = []
    for k in range(n):
        off = Vector((r.uniform(-1, 1) * spread[0], r.uniform(-1, 1) * spread[1], r.uniform(0, 1) * spread[2])); ph = r.uniform(0, 6)
        ob = mk('spk', c + off, (0.06, 0.06, 0.06), 'spark')
        out.append((ob, lambda f, off=off, ph=ph: (c + off + Vector((0, 0, 0.01 * f)), max(0, math.sin(f * 0.5 + ph)) * 1.4, f * 0.3)))
    animate(out)
def wave_rings(p0, p1, mat='wave_blue', count=4, period=12, n=12, r0=0.15, r1=0.7):
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
    perp = d.cross(Vector((0, 0, 1))).normalized(); up = Vector((0, 0, 1)); out = []
    for ring in range(count):
        for k in range(n):
            ang = 2 * math.pi * k / n; ob = mk('ring', p0, (0.11, 0.11, 0.11), mat)
            def fn(f, ring=ring, ang=ang):
                ph = ((f / period) + ring / count) % 1; c = p0 + d * ph; rad = r0 + (r1 - r0) * ph
                return c + perp * math.cos(ang) * rad + up * math.sin(ang) * rad, (1.0 if 0.03 < ph < 0.97 else 0.0), 0
            out.append((ob, fn))
    animate(out)
def orbit_cubes(center, mat='wave_orange', n=12, rad=0.42, size=0.08):
    c = Vector(center); out = []
    for k in range(n):
        ob = mk('orb', c, (size, size, size), mat)
        def fn(f, k=k):
            a = f * 0.25 + 2 * math.pi * k / n; rr = rad * (1 + 0.25 * math.sin(f * 1.3 + k))
            return c + Vector((math.cos(a) * rr, math.sin(a) * rr * 0.6, 0.25 * math.sin(a * 2 + k))), 1.0 + 0.4 * math.sin(f * 0.9 + k), a
        out.append((ob, fn))
    animate(out)
def signal(p0, p1, n=6, period=10):
    p0, p1 = Vector(p0), Vector(p1); out = []
    for k in range(n):
        ob = mk('sig', p0, (0.09, 0.09, 0.09), 'cyan')
        out.append((ob, lambda f, k=k: (p0.lerp(p1, ((f / period) + k / n) % 1), 1.0, f * 0.3)))
    animate(out)
def space(color=(0.05, 0.03, 0.12)):
    world_bg.inputs['Color'].default_value = color + (1,); world_bg.inputs['Strength'].default_value = 1.0
    r = random.Random(11)
    for k in range(160):
        a, b = r.uniform(0, 2 * math.pi), r.uniform(-0.6, 1.2); d = r.uniform(18, 30)
        mk('st', (BX + math.cos(a) * d, BY + math.sin(a) * d, 2 + b * 12), (0.08, 0.08, 0.08), 'star')
def brain(shake=False, red=False):
    space(); r = random.Random(3); out = []
    for i in range(-5, 6):
        for j in range(-3, 4):
            for k in range(0, 5):
                x, y, z = i * 0.3, j * 0.3, k * 0.3
                if (x / 1.65) ** 2 + (y / 1.05) ** 2 + ((z - 0.3) / 1.3) ** 2 > 1: continue
                p = Vector((BX + x, BY + y, 2.0 + z)); ob = mk('br', p, (0.3, 0.3, 0.3), 'pink' if r.random() < .6 else 'pink2')
                if shake: out.append((ob, lambda f, p=p, q=r.random(): (p + Vector((math.sin(f * 3 + q * 9) * 0.04, 0, math.cos(f * 2.7 + q * 7) * 0.04)), 1.0, 0)))
    for i in range(-2, 3):
        for j in range(-1, 2):
            for k in range(0, 2):
                p = Vector((BX + 1.25 + 0.24 * i, BY - 0.15 + j * 0.24, 1.45 + k * 0.24))
                out.append((mk('cb', p, (0.24, 0.24, 0.24), 'redglow' if red else 'cereb'), lambda f, p=p: (p, 1.0 + 0.15 * math.sin(f * 0.6), 0)))
    animate(out)
def earth(spin=0.03, stop_at=None):
    space(); r = random.Random(5); e = empty((BX, BY, 2.2))
    for i in range(-5, 6):
        for j in range(-5, 6):
            for k in range(-5, 6):
                d = math.sqrt(i * i + j * j + k * k)
                if d > 5.2 or d < 4.0: continue
                lat = k / 5.0
                m = 'ice' if abs(lat) > 0.85 else ('land' if (math.sin(i * 0.9) + math.cos(j * 0.7 + k * 0.5) + r.uniform(-0.6, 0.6)) > 0.25 else 'ocean')
                mk('e', (i * 0.24, j * 0.24, k * 0.24), (0.24, 0.24, 0.24), m, parent=e)
    for f in range(1, N + 1):
        k = f if stop_at is None else min(f, stop_at)
        e.rotation_euler = (0.4, 0, k * spin); e.keyframe_insert('rotation_euler', frame=f)
    mk('moon', (BX + 4.5, BY + 3, 4.6), (0.5, 0.5, 0.5), 'moon')
def big_clock(c, speed=0.5):
    c = Vector(c)
    for k in range(24):
        a = 2 * math.pi * k / 24; mk('cf', c + Vector((math.cos(a) * 1.1, 0, math.sin(a) * 1.1)), (0.24, 0.2, 0.24), 'gold')
    mk('face', c + Vector((0, 0.05, 0)), (2.0, 0.05, 2.0), 'clockface')
    hands = []
    for L, w, sp in [(0.85, 0.09, speed), (0.6, 0.13, speed / 12)]:
        e = empty(c + Vector((0, -0.08, 0))); mk('hand', (0, 0, L / 2), (w, 0.04, L), 'black', parent=e)
        for f in range(1, N + 1):
            e.rotation_euler = (0, f * sp, 0); e.keyframe_insert('rotation_euler', frame=f)
def night():
    world_bg.inputs['Color'].default_value = (0.03, 0.04, 0.12, 1); world_bg.inputs['Strength'].default_value = 0.6
    sun.data.energy = 0.8; sun.data.color = (0.6, 0.7, 1.0)
    mk('moon', (6, 22, 9), (1.2, 1.2, 1.2), 'moon')
    r = random.Random(4)
    for k in range(60): mk('st', (r.uniform(-25, 25), r.uniform(24, 30), r.uniform(4, 16)), (0.1, 0.1, 0.1), 'star')
def ghost(c):
    c = Vector(c); e = empty(c)
    for (x, z, s) in [(0, 0.5, 0.7), (0, 0.0, 0.6), (-0.2, -0.4, 0.25), (0.2, -0.45, 0.25), (0, -0.5, 0.25)]:
        mk('gh', (x, 0, z), (s, s * 0.8, s), 'white', parent=e)
    for x in (-0.15, 0.15): mk('ge', (x, -0.29, 0.6), (0.1, 0.03, 0.14), 'black', parent=e)
    for f in range(1, N + 1):
        e.location = c + Vector((math.sin(f * 0.15) * 0.4, 0, math.sin(f * 0.3) * 0.15)); e.keyframe_insert('location', frame=f)
def animals(c):
    c = Vector(c)
    for (dx, body, headc, s) in [(-0.45, 'tan', 'tan', 0.7), (0.45, 'graycat', 'graycat', 0.55)]:
        e = empty(c + Vector((dx, 0, 0)))
        mk('ab', (0, 0, 0.35 * s), (0.6 * s, 0.32 * s, 0.32 * s), body, parent=e)
        mk('ah', (-0.36 * s, -0.02, 0.6 * s), (0.3 * s, 0.3 * s, 0.3 * s), headc, parent=e)
        for ex in (-0.06, 0.06): mk('ae', (-0.52 * s, ex, 0.65 * s), (0.04, 0.05, 0.05), 'black', parent=e)
        for (lx, ly) in [(-0.2, -0.1), (-0.2, 0.1), (0.2, -0.1), (0.2, 0.1)]: mk('al', (lx * s, ly * s, 0.1 * s), (0.1 * s, 0.1 * s, 0.2 * s), body, parent=e)
        mk('at', (0.38 * s, 0, 0.5 * s), (0.08, 0.08, 0.3 * s), body, parent=e)
        for f in range(1, N + 1):
            e.location = c + Vector((dx, 0, abs(math.sin(f * 0.5 + dx)) * 0.08)); e.rotation_euler = (0, 0, math.radians(90 + 10 * math.sin(f * 0.3)))
            e.keyframe_insert('location', frame=f); e.keyframe_insert('rotation_euler', frame=f)
def fish_tank(c):
    c = Vector(c); mk('tank', c + Vector((0, 0.3, 1.6)), (3.6, 1.2, 2.4), 'water')
    out = []
    for k in range(3):
        e = empty(c); mk('fb', (0, 0, 0), (0.5, 0.2, 0.3), 'fishor', parent=e); mk('ft', (0.33, 0, 0), (0.16, 0.06, 0.3), 'fishor', parent=e)
        for f in range(1, N + 1):
            e.location = c + Vector((math.sin(f * 0.08 + k * 2) * 1.3, -0.4, 1.95 + k * 0.3)); e.rotation_euler = (0, 0, math.pi if math.cos(f * 0.08 + k * 2) > 0 else 0)
            e.keyframe_insert('location', frame=f); e.keyframe_insert('rotation_euler', frame=f)
def fire_at(p):
    p = Vector(p); out = []
    for k in range(14):
        ob = mk('fi', p, (0.06, 0.06, 0.06), 'fire' if k % 2 else 'fire2')
        out.append((ob, lambda f, k=k: (p + Vector((math.sin(k * 2.1) * 0.12, -0.05, ((f * 0.06 + k / 14) % 1) * 0.5)), 1.2 - ((f * 0.06 + k / 14) % 1), f * 0.4)))
    animate(out)
def notes(c):
    c = Vector(c); out = []
    for k in range(12):
        ob = mk('nt', c, (0.14, 0.05, 0.14), ['note1', 'note2', 'note3'][k % 3])
        out.append((ob, lambda f, k=k: (c + Vector((math.sin(k * 1.7 + f * 0.1) * 1.2, -0.3, ((f * 0.04 + k / 12) % 1) * 2.4)), 1.0, math.sin(f * 0.2 + k) * 0.5)))
    animate(out)
def big_phone(c):
    c = Vector(c); mk('BigPhoneB', c + Vector((0, 0, 1.6)), (1.6, 0.25, 3.0), 'dark')
    mk('BigPhoneS', c + Vector((0, -0.14, 1.65)), (1.4, 0.02, 2.6), 'screen'); mk('BigPhoneR', c + Vector((0, -0.16, 2.75)), (0.3, 0.02, 0.3), 'red')
def sunset():
    sun.data.color = (1.0, 0.75, 0.55); sun.data.energy = 3.0; sun.rotation_euler = (math.radians(70), 0, math.radians(20))
    world_bg.inputs['Color'].default_value = (1.0, 0.68, 0.55, 1); world_bg.inputs['Strength'].default_value = 0.7
def phone_in_hand():
    ph = bpy.data.objects['Phone']; ph.parent = OL; ph.parent_type = 'BONE'; ph.parent_bone = 'Arm.R'
    ph.location = (0.0, -0.02, -0.07); ph.rotation_euler = (math.radians(90), 0, 0)

# ---------------- scene layout ----------------
for c in CROWD: c.location = (400, 0, 0)
OL.location = (500, 500, 0); RO.location = (500, 500, 0)
SETS = {'park': Vector((0, 0, 0)), 'office': Vector((OX, 0.8, 0)), 'sunset': Vector((0, 0, 0)), 'night': Vector((0, 0, 0))}
SETNAME = CUT.get('set', 'park'); C = SETS.get(SETNAME, SETS['park'])
if SETNAME == 'sunset': sunset()
if SETNAME == 'night': night()
POS = {'ol': C + Vector((-0.9, 0, 0)), 'robo': C + Vector((0.9, 0, 0))}
RIG = {'ol': OL, 'robo': RO}
SP = CUT.get('sp', 'robo'); LS = 'ol' if SP == 'robo' else 'robo'
ACT = {'ol': {'talk': 'OL_Talk', 'idle': None, 'think': 'OL_Think', 'wave': 'OL_WaveR', 'walk': 'OL_Walk', 'surprised': 'OL_Surprised'},
       'robo': {'talk': 'Robo_Talk', 'idle': None, 'think': 'Robo_Think', 'wave': 'Robo_Wave', 'walk': 'Robo_Walk', 'surprised': 'Robo_Surprised'}}
def stand_pair(talk=True):
    for k in ('ol', 'robo'):
        o = 'robo' if k == 'ol' else 'ol'
        place(RIG[k], *POS[k][:2], look=(POS[o].x, POS[o].y - 0.7))
        a = CUT.get('act_' + k) or ('talk' if (k == SP and talk) else 'idle')
        if a == 'surprised': act(RIG[k], ACT[k][a], hold_end=11)
        elif a == 'laugh': pose_anim(RIG[k], laugh)
        elif a == 'tickle_self': pose_anim(RIG[k], tickle_self)
        elif a == 'point': pose_anim(RIG[k], point)
        else: act(RIG[k], ACT[k].get(a))
def headp(k): return POS[k] + Vector((0, 0, H_OL if k == 'ol' else H_RO))
SX_ = {'ol': 1, 'robo': -1}   # side the character faces (ol stands left, looks right)

# ---------------- shots ----------------
def shot_two():
    stand_pair(); cam_path(two_keys(C + Vector((0, -4.2, 1.5)), C + Vector((0, 0, 1.35)), C + Vector((0, -3.4, 1.5)), C + Vector((0, 0, 1.4)), 34))
def shot_close():
    stand_pair(); p = POS[SP]; s = SX_[SP]; h = headp(SP)
    cam_path(two_keys(p + Vector((s * 0.9, -1.6, 1.62)), h - Vector((0, 0, 0.08)), p + Vector((s * 0.7, -1.2, 1.66)), h - Vector((0, 0, 0.05)), 38))
def shot_ots():
    stand_pair(); L, S = POS[LS], POS[SP]; d = (L - S).normalized()
    cam_path(two_keys(L + d * 1.4 + Vector((0, -0.75, 1.9)), headp(SP) - Vector((0, 0, 0.2)), L + d * 1.2 + Vector((0, -0.7, 1.85)), headp(SP) - Vector((0, 0, 0.15)), 32))
def shot_low():
    stand_pair(); p = POS[SP]; s = SX_[SP]
    cam_path(two_keys(p + Vector((s * 1.4, -2.1, 0.75)), headp(SP), p + Vector((s * 1.1, -1.7, 0.85)), headp(SP), 32))
def shot_side():
    stand_pair(); cam_path(two_keys(C + Vector((-0.6, -3.6, 1.5)), C + Vector((0, 0, 1.45)), C + Vector((0.6, -3.3, 1.6)), C + Vector((0, 0, 1.5)), 30))
def shot_crane():
    stand_pair(); cam_path(two_keys(C + Vector((0.5, -6.0, 4.4)), C + Vector((0, 0, 1.0)), C + Vector((3.5, -4.4, 3.4)), C + Vector((0, 0, 1.0)), 28))
def shot_think():
    CUT['act_ol'] = 'think'; stand_pair(); p = POS['ol']
    cam_path(two_keys(p + Vector((1.5, -1.5, 1.4)), headp('ol'), p + Vector((1.1, -1.1, 1.5)), headp('ol'), 36))
def shot_surprised():
    k = CUT.get('who', 'ol'); CUT['act_' + k] = 'surprised'; stand_pair(False)
    place(RIG[k], *POS[k][:2], yaw=0); p = POS[k]; h = headp(k)
    cam_path([(1, p + Vector((0, -3.0, 1.6)), h - Vector((0, 0, 0.15)), 35), (8, p + Vector((0, -1.5, 1.75)), h, 35), (N, p + Vector((0, -1.35, 1.75)), h, 35)], shake=0.015)
def shot_shock():
    k = CUT.get('who', 'ol'); CUT['act_' + k] = 'surprised'; stand_pair(False); place(RIG[k], *POS[k][:2], yaw=0)
    world_bg.inputs['Color'].default_value = (0.75, 0.12, 0.2, 1); sun.data.color = (1, 0.7, 0.7)
    p = POS[k]; cam_path([(1, p + Vector((0, -2.4, 1.5)), p + Vector((0, 0, 1.4)), 30, -14), (N, p + Vector((0, -2.0, 1.55)), p + Vector((0, 0, 1.45)), 30, 12)], shake=0.035)
def shot_rings():
    stand_pair(); wave_rings(headp('robo') + Vector((-0.2, 0, -0.1)), headp('ol') + Vector((0.2, 0, -0.1)))
    cam_path(two_keys(C + Vector((-0.5, -3.6, 1.5)), C + Vector((0, 0, 1.45)), C + Vector((0.5, -3.3, 1.6)), C + Vector((0, 0, 1.5)), 30))
def shot_orbit():
    k = CUT.get('who', 'ol'); stand_pair(); orbit_cubes(headp(k) - Vector((0, 0, 0.1)))
    p = POS[k]; s = SX_[k]
    def orb(az, d=1.9): a = math.radians(az); return p + Vector((s * math.sin(a) * d, -math.cos(a) * d, 1.75))
    cam_path(two_keys(orb(45), headp(k) - Vector((0, 0, 0.05)), orb(85), headp(k) - Vector((0, 0, 0.05)), 42))
def shot_signal():
    CUT['act_ol'] = 'tickle_self'; stand_pair(); h = headp('ol')
    signal(h, POS['ol'] + Vector((-0.25, -0.2, 1.05))); signal(h, POS['ol'] + Vector((0.25, -0.2, 1.05)))
    p = POS['ol']; cam_path(two_keys(p + Vector((1.0, -2.6, 1.6)), p + Vector((0, 0, 1.45)), p + Vector((0.6, -2.1, 1.6)), p + Vector((0, 0, 1.45)), 32))
def shot_brain(red=False):
    brain(shake=red, red=red); place(RO, BX - 2.2, BY - 1.0, look=(BX, BY)); act(RO, 'Robo_Talk')
    def ob(az, d, z): a = math.radians(az); return Vector((BX + math.sin(a) * d, BY - math.cos(a) * d, z))
    if red: cam_path(two_keys(ob(30, 4.6, 2.4), Vector((BX, BY, 2.2)), ob(-10, 4.0, 2.2), Vector((BX, BY, 2.2)), 30), shake=0.02)
    else: cam_path(two_keys(ob(-40, 5.2, 3.0), Vector((BX, BY, 2.3)), ob(10, 4.6, 2.6), Vector((BX, BY, 2.3)), 30))
def shot_earth(stop=False):
    earth(stop_at=(N // 2) if stop else None)
    place(RO, BX - 2.6, BY - 2.0, z=0, look=(BX, BY)); RO.location.z = -50   # robot hidden in space
    def ob(az, d, z): a = math.radians(az); return Vector((BX + math.sin(a) * d, BY - math.cos(a) * d, z))
    cam_path(two_keys(ob(-25, 5.0, 3.0), Vector((BX, BY, 2.2)), ob(15, 4.3, 2.6), Vector((BX, BY, 2.2)), 30), shake=0.03 if stop else 0)
def shot_space():
    space(); place(OL, BX - 0.8, BY, yaw=-20); place(RO, BX + 0.8, BY, yaw=20)
    for k in ('ol', 'robo'): RIG[k].location.z = 0.0
    act(OL, 'OL_Think'); act(RO, 'Robo_Talk' if SP == 'robo' else None)
    mk('rock', (BX, BY, -0.25), (4.0, 3.0, 0.5), 'gray')
    cam_path(two_keys(Vector((BX + 0.4, BY - 4.6, 1.2)), Vector((BX, BY, 1.6)), Vector((BX - 0.4, BY - 3.8, 1.5)), Vector((BX, BY, 1.7)), 28))
def shot_clock():
    stand_pair(); big_clock(C + Vector((0, 2.2, 2.4)), speed=0.6)
    cam_path(two_keys(C + Vector((0, -4.4, 1.3)), C + Vector((0, 0.8, 1.8)), C + Vector((0, -3.6, 1.4)), C + Vector((0, 0.8, 1.9)), 30))
def shot_ghost():
    night(); CUT['act_ol'] = 'surprised'; stand_pair(False); ghost(C + Vector((0, 1.4, 2.0)))
    cam_path(two_keys(C + Vector((0.4, -4.2, 1.2)), C + Vector((0, 0.6, 1.6)), C + Vector((-0.3, -3.4, 1.3)), C + Vector((0, 0.6, 1.7)), 30), shake=0.01)
def shot_night():
    night(); stand_pair()
    cam_path(two_keys(C + Vector((0, -4.4, 1.2)), C + Vector((0, 2, 2.4)), C + Vector((0.4, -3.8, 1.3)), C + Vector((0, 2, 2.5)), 28))
def shot_animals():
    stand_pair(); animals(C + Vector((0, -1.3, 0)))
    cam_path(two_keys(C + Vector((0, -3.6, 1.0)), C + Vector((0, -0.4, 0.8)), C + Vector((0.3, -3.0, 1.1)), C + Vector((0, -0.4, 0.9)), 30))
def shot_fish():
    stand_pair(); fish_tank(C + Vector((0, 1.6, 0)))
    cam_path(two_keys(C + Vector((0, -4.4, 1.3)), C + Vector((0, 0.8, 1.7)), C + Vector((0.3, -3.8, 1.35)), C + Vector((0, 0.8, 1.75)), 30))
def shot_fire():
    CUT['act_ol'] = 'surprised'; stand_pair(False); place(OL, *POS['ol'][:2], yaw=0); fire_at(headp('ol') + Vector((0, -0.38, -0.32)))
    p = POS['ol']; cam_path(two_keys(p + Vector((0, -2.4, 1.5)), p + Vector((0, 0, 1.45)), p + Vector((0, -1.9, 1.55)), p + Vector((0, 0, 1.5)), 32), shake=0.02)
def shot_notes():
    stand_pair(); notes(C + Vector((0, 0.4, 0.6)))
    cam_path(two_keys(C + Vector((0.5, -3.8, 1.4)), C + Vector((0, 0, 1.5)), C + Vector((-0.5, -3.4, 1.5)), C + Vector((0, 0, 1.5)), 30))
def shot_phone():
    big_phone(C + Vector((0, 2.2, 0))); stand_pair()
    wave_rings(C + Vector((-3.5, -0.4, 1.8)), C + Vector((-0.1, 2.0, 1.8)), count=4, period=14)
    cam_path(two_keys(C + Vector((-3.0, -5.2, 2.2)), C + Vector((0, 1.5, 1.6)), C + Vector((2.8, -5.0, 2.0)), C + Vector((0, 1.5, 1.6)), 30))
def shot_crowd():
    place(OL, C.x, C.y, yaw=0); act(OL, 'OL_Talk' if SP == 'ol' else 'OL_Think')
    place(RO, C.x + 1.5, C.y - 1.7, look=(C.x, C.y)); act(RO, 'Robo_Talk' if SP == 'robo' else None)
    for i, c in enumerate(CROWD):
        a = math.radians(60 + i * 48); place(c, C.x + math.cos(a) * 2.5, C.y + math.sin(a) * 2.5 - 0.2, look=(C.x, C.y))
        act(c, 'Wave' if i % 2 == 0 else None)
    cam_path(two_keys(C + Vector((0.5, -6.0, 4.6)), C + Vector((0, 0, 0.9)), C + Vector((4.2, -4.6, 3.6)), C + Vector((0, 0, 1.0)), 28))
def shot_eq():
    place(OL, SX, -0.2, 0.5, yaw=0); act(OL, 'OL_Wave'); place(RO, SX + 2.3, -0.6, 0, look=(SX, -0.2)); act(RO, 'Robo_Talk')
    out = []
    for i in range(9):
        x = SX - 3.6 + 7.2 * i / 8
        for j in range(6):
            ob = mk('eq', (x, 1.6, 0.3 + j * 0.42), (0.38, 0.38, 0.38), 'wave_orange')
            out.append((ob, lambda f, i=i, j=j, x=x: ((x, 1.6, 0.3 + j * 0.42), (1.0 if j < 2.5 + 2.5 * abs(math.sin(f * 0.35 + i * 0.8)) else 0.0), 0)))
    animate(out)
    cam_path(two_keys(Vector((SX + 1.4, -5.2, 0.6)), Vector((SX + 0.4, 0, 1.6)), Vector((SX - 1.4, -5.0, 0.8)), Vector((SX + 0.4, 0, 1.6)), 28))
def shot_stage():
    place(OL, SX, -0.2, 0.5, yaw=0); act(OL, 'OL_WaveR'); place(RO, SX + 2.3, -0.6, 0, look=(SX, -0.2)); act(RO, 'Robo_Talk')
    sparkles((SX, -0.4, 1.0), 22, (1.4, 0.6, 1.8))
    cam_path(two_keys(Vector((SX, -3.2, 1.0)), Vector((SX, 0, 1.9)), Vector((SX - 0.4, -2.5, 2.6)), Vector((SX, 0, 1.85)), 34))
def shot_walkin():
    place(OL, OX - 0.9, 0.9, look=(OX + 1.0, 0.7)); act(OL, 'OL_Talk' if SP == 'ol' else None)
    place(RO, OX + 3.5, 0.6, look=(OX - 0.9, 0.9)); act(RO, 'Robo_Walk'); move(RO, (OX + 3.6, 0.6, 0), (OX + 0.9, 0.7, 0), int(N * 0.8))
    cam_path(two_keys(Vector((OX + 0.8, -4.6, 1.9)), Vector((OX + 1.2, 0.8, 1.2)), Vector((OX + 0.1, -4.2, 1.8)), Vector((OX + 0.2, 0.8, 1.25)), 30))
def shot_laugh():
    place(OL, C.x - 0.9, C.y, look=(C.x, C.y - 0.3)); pose_anim(OL, laugh)
    place(RO, C.x, C.y, look=(C.x - 0.9, C.y)); pose_anim(RO, robo_tickle)
    sparkles((C.x - 0.9, C.y - 0.3, 1.4), 20, (0.9, 0.4, 1.2))
    cam_path(two_keys(C + Vector((-0.6, -2.4, 1.5)), C + Vector((-0.6, 0, 1.45)), C + Vector((-0.4, -2.1, 1.55)), C + Vector((-0.6, 0, 1.5)), 32), shake=0.03)
def shot_point():
    CUT['act_robo'] = 'point'; shot_two()
def shot_intro(b=False):
    place(OL, C.x - 0.7, C.y, yaw=-10); act(OL, 'OL_Think'); place(RO, C.x + 0.7, C.y, yaw=12); act(RO, 'Robo_Think')
    for i, (x, z) in enumerate([(-1.3, 2.55), (0.0, 2.85), (1.3, 2.6)]):
        ob = mk('q', (0, 0, 0), (0.42, 0.42, 0.42), 'gold')
        animate([(ob, lambda f, x=x, z=z, i=i: (C + Vector((x, 0.3, z + 0.08 * math.sin(f * 0.5 + i * 2))), 1.0, 0.25 * math.sin(f * 0.2 + i)))])
    if not b: cam_path(two_keys(C + Vector((0, -4.6, 1.6)), C + Vector((0, 0, 1.6)), C + Vector((0, -3.8, 1.6)), C + Vector((0, 0, 1.65)), 30))
    else: cam_path(two_keys(C + Vector((-2.4, -2.8, 0.7)), C + Vector((0, 0, 1.8)), C + Vector((-1.2, -3.2, 0.8)), C + Vector((0, 0, 1.85)), 30))
def shot_end(b=False):
    place(OL, C.x - 0.7, C.y, yaw=-8); act(OL, 'OL_WaveR'); place(RO, C.x + 0.7, C.y, yaw=8); act(RO, 'Robo_Wave')
    sparkles(C + Vector((0, -0.3, 0.6)), 18, (2.0, 0.8, 1.8))
    if not b: cam_path(two_keys(C + Vector((0, -3.0, 1.5)), C + Vector((0, 0, 1.3)), C + Vector((0, -6.5, 3.4)), C + Vector((0, 0, 1.2)), 32))
    else: cam_path(two_keys(C + Vector((0.4, -4.0, 1.4)), C + Vector((0, 0, 1.25)), C + Vector((-0.2, -3.4, 1.45)), C + Vector((0, 0, 1.3)), 34))

SHOTS = {'two': shot_two, 'close': shot_close, 'ots': shot_ots, 'low': shot_low, 'side': shot_side, 'crane': shot_crane,
         'think': shot_think, 'surprised': shot_surprised, 'shock': shot_shock, 'rings': shot_rings, 'orbit': shot_orbit,
         'signal': shot_signal, 'brain': shot_brain, 'brain_red': lambda: shot_brain(True), 'earth': shot_earth,
         'earth_stop': lambda: shot_earth(True), 'space': shot_space, 'clock': shot_clock, 'ghost': shot_ghost,
         'night': shot_night, 'animals': shot_animals, 'fish': shot_fish, 'fire': shot_fire, 'notes': shot_notes,
         'phone': shot_phone, 'crowd': shot_crowd, 'eq': shot_eq, 'stage': shot_stage, 'walkin': shot_walkin,
         'laugh': shot_laugh, 'point': shot_point, 'introA': shot_intro, 'introB': lambda: shot_intro(True),
         'endA': shot_end, 'endB': lambda: shot_end(True)}
if CUT.get('phone'): phone_in_hand()
SHOTS.get(CUT['shot'], shot_two)()

# ---------------- head projection + render ----------------
heads = []
for f in range(1, N + 1):
    sc.frame_set(f); row = {}
    for key, rig in (('ol', OL), ('robo', RO)):
        v = world_to_camera_view(sc, cam, rig.matrix_world @ rig.pose.bones['Head'].tail.copy())
        row[key] = [v.x, 1 - v.y, v.z]
    heads.append(row)
json.dump(heads, open(f'{OUT}/heads.json', 'w'))
sc.render.engine = 'BLENDER_EEVEE'
sc.eevee.taa_render_samples = int(os.environ.get('SAMP', 3))
try: sc.eevee.shadow_ray_count = 1; sc.eevee.shadow_step_count = 2
except Exception: pass
sc.render.resolution_x, sc.render.resolution_y = int(os.environ.get('RX', 720)), int(os.environ.get('RY', 1000))
sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 92
if os.environ.get('PREVIEW'):
    for f in sorted({1, N}):
        sc.frame_set(f); sc.render.filepath = f'{OUT}/prev_{f:04d}.jpg'; bpy.ops.render.render(write_still=True)
else:
    todo = [f for f in range(1, N + 1) if not os.path.exists(f'{OUT}/f_{f:04d}.jpg')]
    if todo:
        sc.frame_start, sc.frame_end = todo[0], N; sc.render.filepath = f'{OUT}/f_'
        bpy.ops.render.render(animation=True)
print('CUT DONE', CI, CUT['shot'], N)
