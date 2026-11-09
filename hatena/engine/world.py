import bpy, bmesh, math, random, os
W = os.environ.get('HATENA_WORK', '/tmp/hatena_work')
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
B = 0.5

# ---------- bring in characters ----------
def load(path, colnames):
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.collections = [c for c in src.collections if c in colnames]
        dst.actions = list(src.actions)
    for c in dst.collections: sc.collection.children.link(c)
    for a in dst.actions: a.use_fake_user = True
load(W + '/robot_and_ol.blend', ['Robot', 'OL'])
load(W + '/hakota_character.blend', ['Hakota'])
for o in bpy.data.objects:
    if o.type == 'ARMATURE': o.hide_render = True

# crowd copies of Hakota
hk = bpy.data.collections['Hakota']
crowd = bpy.data.collections.new('Crowd'); sc.collection.children.link(crowd)
src_rig = bpy.data.objects['HakotaRig']
for i in range(6):
    nr = src_rig.copy(); nr.data = src_rig.data; nr.name = f'Crowd{i}'; nr.animation_data_clear(); crowd.objects.link(nr)
    for ch in src_rig.children:
        nc = ch.copy(); nc.parent = nr; crowd.objects.link(nc)
    nr.location = (300 + i * 3, 0, 0)  # parked far away
src_rig.location = (300, 30, 0)

# ---------- textures ----------
def px_img(name, base, var=14, seed=0, top=None, pattern=None):
    r = random.Random(seed)
    img = bpy.data.images.new(name, 16, 16); p = []
    for y in range(15, -1, -1):
        for x in range(16):
            c = base
            if top and y < 4 + (r.random() < .5): c = top
            if pattern == 'brick' and (y % 4 == 3 or (x + (8 if (y // 4) % 2 else 0)) % 8 == 7): c = tuple(v - 40 for v in c)
            if pattern == 'plank' and (y % 4 == 3 or (y // 4 % 2 == 0 and x == 11) or (y // 4 % 2 == 1 and x == 4)): c = tuple(v - 35 for v in c)
            if pattern == 'window' and 2 <= x <= 13 and 2 <= y <= 13 and x not in (7, 8) and y != 7: c = (150, 200, 235)
            d = r.randint(-var, var)
            p += [max(0, min(255, c[i] + d)) / 255 for i in range(3)] + [1]
    img.pixels = p; img.pack(); return img

def mat(name, img=None, color=None, emit=0.0, rough=0.9):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = rough
    if img:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = img; t.interpolation = 'Closest'
        nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
        if emit: nt.links.new(t.outputs['Color'], b.inputs['Emission Color'])
    if color:
        b.inputs['Base Color'].default_value = color + (1,)
        if emit: b.inputs['Emission Color'].default_value = color + (1,)
    if emit: b.inputs['Emission Strength'].default_value = emit
    return m

M = {
 'grass': mat('grass', px_img('g', (95, 159, 53), seed=1)),
 'stone': mat('stone', px_img('st', (140, 140, 145), 12, 3, pattern='brick')),
 'win': mat('win', px_img('w', (120, 120, 128), 10, 4, pattern='window'), rough=0.3),
 'leaf': mat('leaf', px_img('l', (60, 130, 45), 24, 5)),
 'log': mat('log', px_img('lo', (105, 80, 50), 14, 6)),
 'path': mat('path', px_img('p', (170, 160, 130), 12, 7)),
 'plank': mat('plank', px_img('pl', (170, 135, 85), 12, 8, pattern='plank')),
 'wall': mat('wallw', px_img('ww', (225, 222, 210), 8, 9)),
 'quartz': mat('quartz', px_img('q', (236, 233, 225), 6, 11)),
 'gold': mat('gold', px_img('go', (240, 195, 60), 18, 12), rough=0.4),
 'dark': mat('dark', px_img('dk', (40, 40, 48), 6, 13)),
 'screen': mat('screen', px_img('sc', (80, 170, 240), 18, 14), emit=1.5),
 'red': mat('red', color=(0.9, 0.08, 0.08), emit=2.0),
 'blue': mat('wave_blue', color=(0.15, 0.5, 1.0), emit=0.7),
 'orange': mat('wave_orange', color=(1.0, 0.35, 0.05), emit=0.7),
 'yellow': mat('spark', color=(1.0, 0.85, 0.2), emit=2.0),
 'carpet': mat('carpet', px_img('ca', (180, 50, 60), 10, 15)),
}
FLW = [mat(f'f{i}', px_img(f'fi{i}', c, 10, 20 + i)) for i, c in enumerate([(240, 70, 70), (255, 220, 60), (250, 250, 250), (210, 110, 230)])]

def cube(name, loc, size, m, col=None, uv_scale=None):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    uvl = bm.loops.layers.uv.new()
    for f in bm.faces:
        n = f.normal
        for lp in f.loops:
            co = lp.vert.co
            if uv_scale:
                if abs(n.z) > .5: u, v = co.x, co.y
                elif abs(n.x) > .5: u, v = co.y, co.z
                else: u, v = co.x, co.z
                lp[uvl].uv = (u / uv_scale, v / uv_scale)
        if not uv_scale:
            for lp, uv in zip(f.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]): lp[uvl].uv = uv
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); me.materials.append(m)
    ob.location = loc; (col or sc.collection).objects.link(ob); return ob

# ---------- PARK (around origin) ----------
park = bpy.data.collections.new('Park'); sc.collection.children.link(park)
cube('ground', (0, 10, -0.25), (80, 60, 0.5), M['grass'], park, B)
cube('path', (0, 3, 0.003), (80, 1.5, 0.01), M['path'], park, B)
for bx0, bx1, h, yb in [(-13, -5, 7.5, 16), (-4, 4.5, 10.5, 18), (5.5, 13, 6, 15), (-24, -15, 9, 20), (15, 24, 8, 19)]:
    cube('bld', ((bx0 + bx1) / 2, yb + 2, h / 2), (bx1 - bx0, 4, h), M['win'], park, 1.5)
def tree(x, y, hgt=3, col=park):
    for k in range(hgt): cube('log', (x, y, B / 2 + k * B), (B, B, B), M['log'], col)
    for i in range(-2, 3):
        for j in range(-2, 3):
            for k in range(2):
                if abs(i) + abs(j) < 4 - k: cube('leaf', (x + i * B, y + j * B, hgt * B + B / 2 + k * B), (B, B, B), M['leaf'], col)
    cube('leaf', (x, y, hgt * B + B / 2 + 2 * B), (B, B, B), M['leaf'], col)
for x, y, h in [(-4.6, 6.5, 4), (4.8, 6.0, 4), (-8.5, 9, 3), (9, 10, 3), (-6, -4, 3), (7, -5, 4)]: tree(x, y, h)
r = random.Random(4)
for i in range(40):
    x = r.uniform(-9, 9); y = r.uniform(-6, 2)
    if abs(x) < 3 and -3 < y < 1.5: continue
    cube('flw', (x, y, 0.09), (0.18, 0.18, 0.18), FLW[i % 4], park)
# bench
cube('bench', (0, 1.6, 0.45), (1.8, 0.5, 0.12), M['plank'], park)
cube('bench_l', (-0.8, 1.6, 0.2), (0.12, 0.5, 0.4), M['log'], park)
cube('bench_r', (0.8, 1.6, 0.2), (0.12, 0.5, 0.4), M['log'], park)

# ---------- OFFICE (x = 100) ----------
office = bpy.data.collections.new('Office'); sc.collection.children.link(office)
OX = 100
cube('o_floor', (OX, 0, -0.25), (14, 14, 0.5), M['plank'], office, B)
cube('o_wall_b', (OX, 5, 2), (14, 0.5, 4), M['wall'], office, B)
cube('o_wall_l', (OX - 6, 0, 2), (0.5, 14, 4), M['wall'], office, B)
cube('o_wall_r', (OX + 6, 0, 2), (0.5, 14, 4), M['wall'], office, B)
for x in (-4, -1, 2, 5):
    cube('o_win', (OX + x, 4.74, 2.2), (2, 0.05, 1.6), M['win'], office, 1.0)
cube('o_ceil', (OX, 0, 4.1), (14, 14, 0.2), M['wall'], office, B)
for x in (-3, 0, 3):
    cube('o_light', (OX + x, 0, 3.98), (1.6, 0.4, 0.05), M['yellow'], office)
def desk(x, y, rot=0):
    cube('desk', (x, y, 0.72), (1.6, 0.8, 0.08), M['plank'], office)
    for dx in (-0.7, 0.7):
        cube('leg', (x + dx, y, 0.36), (0.08, 0.7, 0.72), M['log'], office)
    cube('pc', (x, y + 0.2, 1.05), (0.7, 0.06, 0.45), M['dark'], office)
    cube('pc_s', (x, y + 0.165, 1.06), (0.62, 0.02, 0.37), M['screen'], office)
    cube('kb', (x, y - 0.15, 0.78), (0.5, 0.18, 0.03), M['dark'], office)
for x, y in [(-3.5, 2.6), (-0.5, 2.6), (2.5, 2.6), (-3.5, -1.5), (2.5, -1.5)]: desk(OX + x, y)
cube('o_plant_pot', (OX + 5, 3.8, 0.25), (0.5, 0.5, 0.5), M['log'], office)
cube('o_plant', (OX + 5, 3.8, 0.75), (0.5, 0.5, 0.5), M['leaf'], office)
cube('o_plant2', (OX + 5, 3.8, 1.25), (0.5, 0.5, 0.5), M['leaf'], office)
office_light = bpy.data.objects.new('OfficeLamp', bpy.data.lights.new('OfficeLamp', 'AREA'))
office_light.data.energy = 250; office_light.data.size = 8; office_light.location = (OX, 0, 3.8); office.objects.link(office_light)

# ---------- STAGE set (x = 200) ----------
stage = bpy.data.collections.new('Stage'); sc.collection.children.link(stage)
SX = 200
cube('st_floor', (SX, 0, -0.25), (30, 30, 0.5), M['dark'], stage, B)
for i in range(-3, 4):
    for j in range(-2, 2):
        cube('st_gold', (SX + i * B, j * B, 0.25), (B, B, B), M['gold'], stage)
cube('st_back', (SX, 3, 3), (12, 0.5, 6), M['carpet'], stage, B)
cube('mic_stand', (SX + 0.35, -0.75, 1.0), (0.05, 0.05, 1.0), M['dark'], stage)
cube('mic', (SX + 0.35, -0.75, 1.55), (0.12, 0.12, 0.18), M['dark'], stage)
spot = bpy.data.objects.new('Spot', bpy.data.lights.new('Spot', 'SPOT'))
spot.data.energy = 2500; spot.data.spot_size = math.radians(40); spot.data.color = (1, 0.9, 0.7)
spot.location = (SX, -3, 6); stage.objects.link(spot)
spot.rotation_euler = (math.radians(30), 0, 0)

# ---------- PROPS ----------
props = bpy.data.collections.new('Props'); sc.collection.children.link(props)
phone = cube('Phone', (0, 0, 0), (0.09, 0.03, 0.17), M['dark'], props)
ps = cube('PhoneScreen', (0, -0.016, 0), (0.075, 0.005, 0.145), M['screen'], props); ps.parent = phone
bigphone = cube('BigPhone', (300, -40, 1.6), (1.6, 0.25, 3.0), M['dark'], props)
bps = cube('BigPhoneScreen', (300, -40.13, 1.65), (1.4, 0.02, 2.6), M['screen'], props); bps.parent = bigphone
bps.matrix_parent_inverse = bigphone.matrix_world.inverted()
rec = cube('BigPhoneRec', (300, -40.15, 2.7), (0.3, 0.02, 0.3), M['red'], props); rec.parent = bigphone
rec.matrix_parent_inverse = bigphone.matrix_world.inverted()

# ---------- world / sun / camera ----------
w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (0.55, 0.75, 1.0, 1); bg.inputs['Strength'].default_value = 0.9
sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); sc.collection.objects.link(sun)
sun.data.energy = 3.2; sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(-35))
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); sc.collection.objects.link(cam); sc.camera = cam
sc.render.engine = 'BLENDER_EEVEE'
sc.eevee.taa_render_samples = 6
sc.view_settings.view_transform = 'Standard'
sc.render.resolution_x, sc.render.resolution_y = 720, 1000
sc.render.fps = 15
for _m in bpy.data.materials: _m.use_fake_user = True
bpy.ops.wm.save_as_mainfile(filepath=W + '/world.blend', compress=True)
print('WORLD OK')
