"""Indoor rooms for hatena (exec'd inside world.py, uses its cube/mat/px_img/M/B/sc)."""
# INDOOR ROOMS (row y = -100; set centre = (X, -100)) ----------
RY = -100
M.update({
 'cream': mat('cream', px_img('cr', (238, 226, 200), 6, 30)),
 'bluewall': mat('bluewall', px_img('bw', (170, 190, 215), 6, 31)),
 'wtile': mat('wtile', px_img('wt', (235, 238, 240), 5, 32, pattern='tile')),
 'btile': mat('btile', px_img('bt', (150, 200, 225), 6, 33, pattern='tile')),
 'gtile': mat('gtile', px_img('gt', (120, 125, 132), 6, 34, pattern='tile')),
 'chk': mat('chk', px_img('ck', (235, 232, 225), 4, 35, pattern='checker')),
 'sky': mat('skywin', color=(0.35, 0.65, 1.0), emit=0.7),
 'nightwin': mat('nightwin', color=(0.04, 0.06, 0.2), emit=1.0),
 'frame': mat('frame', color=(0.93, 0.93, 0.9)),
 'sofa': mat('sofa', px_img('so', (70, 120, 170), 10, 36)),
 'rug': mat('rug', px_img('ru', (200, 150, 90), 12, 37, pattern='checker')),
 'tv': mat('tv', color=(0.08, 0.08, 0.1), rough=0.2),
 'tvon': mat('tvon', px_img('tvs', (90, 160, 230), 30, 38), emit=1.2),
 'sheet': mat('sheet', px_img('sh', (245, 245, 250), 4, 39)),
 'duvet': mat('duvet', px_img('du', (240, 170, 190), 10, 40)),
 'lampw': mat('lampw', color=(1.0, 0.85, 0.55), emit=4.0),
 'porc': mat('porc', color=(0.96, 0.96, 0.97), rough=0.15),
 'stall': mat('stall', px_img('stl', (120, 175, 215), 6, 41)),
 'mirror': mat('mirror', color=(0.8, 0.85, 0.9), rough=0.03),
 'water2': mat('bathwater', color=(0.35, 0.75, 0.95), emit=0.6, rough=0.05),
 'steel': mat('steel', color=(0.7, 0.72, 0.75), rough=0.25),
 'board': mat('board', px_img('bd', (40, 90, 60), 6, 42)),
 'chalk': mat('chalk', color=(0.97, 0.97, 0.95), emit=0.6),
 'seat': mat('seat', px_img('se', (60, 130, 90), 12, 43)),
 'trainwall': mat('trainwall', px_img('tw', (226, 224, 216), 4, 44)),
 'trainfloor': mat('trainfloor', px_img('tf', (110, 115, 125), 8, 45)),
 'strap': mat('strap', color=(0.95, 0.95, 0.95)),
 'yellowb': mat('yellowb', color=(1.0, 0.8, 0.1)),
 'redsign': mat('redsign', color=(0.9, 0.2, 0.25), emit=0.5),
 'bluesign': mat('bluesign', color=(0.15, 0.35, 0.9), emit=0.5),
 'fridge': mat('fridge', color=(0.92, 0.93, 0.94), rough=0.3),
 'cabinet': mat('cabinet', px_img('cb', (200, 160, 110), 8, 46, pattern='plank')),
 'burner': mat('burner', color=(1.0, 0.25, 0.05), emit=2.0),
})

def room(name, X, floor, wall, h=6.0, ceil=None, lamp=500, lamp_col=(1, 0.97, 0.9), back=4.0):
    col = bpy.data.collections.new(name); sc.collection.children.link(col)
    cube(name + '_floor', (X, RY - 1.5, -0.25), (14, 11 + back, 0.5), M[floor], col, B)
    cube(name + '_wb', (X, RY + back, h / 2), (14, 0.5, h), M[wall], col, B)
    for sx in (-6, 6): cube(name + '_ws', (X + sx, RY - 1.5, h / 2), (0.5, 11 + back, h), M[wall], col, B)
    if ceil: cube(name + '_ceil', (X, RY + back / 2 - 1, h), (14, back + 2.5, 0.2), M[ceil], col, B)
    L = bpy.data.objects.new(name + 'Lamp', bpy.data.lights.new(name + 'Lamp', 'AREA'))
    L.data.energy = lamp; L.data.size = 9; L.data.color = lamp_col; L.location = (X, RY - 0.5, h - 0.4); col.objects.link(L)
    F = bpy.data.objects.new(name + 'Fill', bpy.data.lights.new(name + 'Fill', 'AREA'))
    F.data.energy = lamp * 0.5; F.data.size = 6; F.data.color = lamp_col; F.location = (X, RY - 5, 2.4)
    F.rotation_euler = (math.radians(80), 0, 0); col.objects.link(F)
    return col

def window(X, y, x, z, w, h, glass, col):
    cube('win_f', (X + x, y, z), (w + 0.2, 0.1, h + 0.2), M['frame'], col)
    cube('win_g', (X + x, y - 0.06, z), (w, 0.04, h), M[glass], col)
    cube('win_m', (X + x, y - 0.09, z), (0.08, 0.04, h), M['frame'], col)

# HOME (living room)  X=0
X = 0; col = room('Home', X, 'plank', 'cream', ceil='cream')
window(X, RY + 3.74, -2.0, 2.6, 2.4, 1.6, 'sky', col)
for cx in (-3.5, -0.5): cube('curtain', (X + cx, RY + 3.6, 2.6), (0.5, 0.15, 2.2), M['duvet'], col)
cube('sofa_seat', (X - 2.0, RY + 2.9, 0.3), (3.0, 1.0, 0.6), M['sofa'], col)
cube('sofa_back', (X - 2.0, RY + 3.35, 0.85), (3.0, 0.3, 0.9), M['sofa'], col)
for ax in (-3.6, -0.4): cube('sofa_arm', (X + ax, RY + 2.9, 0.55), (0.3, 1.0, 0.7), M['sofa'], col)
cube('tvboard', (X + 3.0, RY + 3.3, 0.3), (2.4, 0.6, 0.6), M['plank'], col)
cube('tv', (X + 3.0, RY + 3.45, 1.35), (2.0, 0.1, 1.15), M['tv'], col)
cube('tvs', (X + 3.0, RY + 3.39, 1.35), (1.85, 0.02, 1.0), M['tvon'], col)
cube('rug', (X, RY + 0.3, 0.01), (5.0, 3.6, 0.02), M['rug'], col, 1.0)
cube('lowtable', (X - 2.0, RY + 1.6, 0.25), (1.4, 0.7, 0.08), M['plank'], col)
cube('lt_leg', (X - 2.0, RY + 1.6, 0.12), (1.2, 0.5, 0.22), M['log'], col)
cube('pot', (X + 5.0, RY + 3.2, 0.3), (0.5, 0.5, 0.6), M['log'], col)
for k in range(3): cube('plant', (X + 5.0, RY + 3.2, 0.85 + k * 0.45), (0.6 - k * 0.12,) * 3, M['leaf'], col)
cube('picture', (X + 3.0, RY + 3.72, 2.9), (1.0, 0.05, 0.7), M['frame'], col)
cube('picture_i', (X + 3.0, RY + 3.69, 2.9), (0.85, 0.02, 0.55), M['grass'], col)
cube('flamp_pole', (X - 4.6, RY + 3.0, 0.9), (0.08, 0.08, 1.8), M['dark'], col)
cube('flamp', (X - 4.6, RY + 3.0, 1.9), (0.45, 0.45, 0.4), M['lampw'], col)

# BEDROOM (night)  X=100
X = 100; col = room('Bedroom', X, 'plank', 'bluewall', ceil='bluewall', lamp=140, lamp_col=(1.0, 0.8, 0.55))
window(X, RY + 3.74, -2.3, 2.7, 2.2, 1.6, 'nightwin', col)
cube('moon_w', (X - 1.7, RY + 3.66, 3.1), (0.35, 0.02, 0.35), M['yellow'], col)
r = random.Random(9)
for k in range(10): cube('star_w', (X - 2.3 + r.uniform(-1, 1), RY + 3.66, 2.7 + r.uniform(-0.7, 0.7)), (0.05, 0.02, 0.05), M['yellow'], col)
cube('bed_frame', (X + 2.6, RY + 2.4, 0.25), (2.2, 3.0, 0.5), M['plank'], col)
cube('bed_mat', (X + 2.6, RY + 2.4, 0.6), (2.0, 2.8, 0.25), M['sheet'], col)
cube('bed_duvet', (X + 2.6, RY + 1.9, 0.78), (2.05, 1.9, 0.14), M['duvet'], col)
cube('pillow', (X + 2.6, RY + 3.4, 0.82), (1.2, 0.5, 0.2), M['sheet'], col)
cube('headboard', (X + 2.6, RY + 3.8, 0.9), (2.3, 0.15, 1.2), M['plank'], col)
cube('nightstand', (X + 4.4, RY + 3.4, 0.35), (0.7, 0.6, 0.7), M['plank'], col)
cube('ns_lamp', (X + 4.4, RY + 3.4, 0.95), (0.4, 0.4, 0.5), M['lampw'], col)
cube('rug', (X - 0.3, RY + 0.4, 0.01), (4.0, 3.0, 0.02), M['sofa'], col, 1.0)
cube('shelf', (X - 5.2, RY + 2.0, 1.0), (0.6, 1.6, 2.0), M['plank'], col)
nl = bpy.data.objects.new('BedLamp', bpy.data.lights.new('BedLamp', 'POINT')); nl.data.energy = 120; nl.data.color = (1, 0.75, 0.45)
nl.location = (X + 4.4, RY + 3.0, 1.4); col.objects.link(nl)

# TOILET (public restroom)  X=200
X = 200; col = room('Toilet', X, 'gtile', 'wtile', ceil='wtile', lamp=420)
for i, sx in enumerate((-3.0, -1.0, 1.0, 3.0)):
    cube('part', (X + sx - 1.0, RY + 3.0, 1.1), (0.08, 2.0, 2.2), M['stall'], col)
cube('part_e', (X + 3.0 + 1.0, RY + 3.0, 1.1), (0.08, 2.0, 2.2), M['stall'], col)
for i, sx in enumerate((-3.0, -1.0, 1.0, 3.0)):
    if i == 2:
        d = cube('door_open', (X + sx - 0.95 + 0.45, RY + 1.6, 1.1), (0.06, 0.9, 2.0), M['stall'], col)
        cube('toilet_bowl', (X + sx, RY + 3.3, 0.22), (0.5, 0.7, 0.44), M['porc'], col)
        cube('toilet_seat', (X + sx, RY + 3.25, 0.47), (0.55, 0.6, 0.06), M['porc'], col)
        cube('toilet_tank', (X + sx, RY + 3.85, 0.75), (0.6, 0.25, 0.6), M['porc'], col)
        cube('paper', (X + sx + 0.75, RY + 3.0, 0.75), (0.15, 0.15, 0.15), M['sheet'], col)
    else:
        cube('door', (X + sx, RY + 2.0, 1.1), (1.9, 0.06, 2.0), M['stall'], col)
        cube('knob', (X + sx + 0.7, RY + 1.95, 1.0), (0.1, 0.05, 0.1), M['steel'], col)
cube('stall_top', (X, RY + 2.0, 2.25), (8.2, 0.12, 0.1), M['steel'], col)
for sx in (-4.4, -2.6):
    cube('urinal', (X + sx, RY + 3.75, 0.9), (0.5, 0.4, 0.8), M['porc'], col)
cube('sign_m', (X - 3.5, RY + 3.73, 3.0), (0.4, 0.04, 0.6), M['bluesign'], col)
cube('sign_w', (X + 4.6, RY + 2.4, 2.6), (0.04, 0.4, 0.6), M['redsign'], col)
cube('sink_counter', (X - 5.5, RY - 0.5, 0.85), (0.8, 3.6, 0.15), M['porc'], col)
for sy in (-1.6, -0.5, 0.6): cube('faucet', (X - 5.7, RY + sy, 1.05), (0.1, 0.1, 0.25), M['steel'], col)
cube('mirror_t', (X - 5.72, RY - 0.5, 2.0), (0.04, 3.4, 1.3), M['mirror'], col)

# BATH (Japanese bathroom)  X=300
X = 300; col = room('Bath', X, 'gtile', 'btile', h=4.5, ceil='wtile', lamp=650)
cube('tub_outer', (X + 1.8, RY + 2.6, 0.32), (3.2, 2.0, 0.64), M['porc'], col)
cube('tub_water', (X + 1.8, RY + 2.6, 0.62), (2.9, 1.7, 0.06), M['water2'], col)
cube('tub_lid', (X + 3.0, RY + 3.4, 0.7), (0.8, 0.4, 0.1), M['porc'], col)
cube('shower_bar', (X - 3.0, RY + 3.72, 1.6), (0.06, 0.06, 1.6), M['steel'], col)
cube('shower_head', (X - 3.0, RY + 3.6, 2.45), (0.25, 0.25, 0.12), M['steel'], col)
cube('faucet_b', (X - 3.0, RY + 3.65, 0.8), (0.5, 0.15, 0.12), M['steel'], col)
cube('mirror_b', (X - 3.0, RY + 3.72, 1.6), (0.9, 0.04, 0.6), M['mirror'], col)
cube('stool', (X - 3.0, RY + 2.6, 0.18), (0.45, 0.45, 0.36), M['porc'], col)
cube('bucket', (X - 2.2, RY + 2.4, 0.15), (0.35, 0.35, 0.3), M['yellowb'], col)
cube('shelf_b', (X - 4.5, RY + 3.6, 1.2), (1.2, 0.3, 0.06), M['steel'], col)
for k, c in enumerate(('sofa', 'duvet', 'porc')): cube('bottle', (X - 4.9 + k * 0.4, RY + 3.6, 1.38), (0.15, 0.15, 0.3), M[c], col)
r = random.Random(12)
for k in range(14): cube('steam', (X + 1.8 + r.uniform(-1.3, 1.3), RY + 2.6 + r.uniform(-0.6, 0.6), 0.9 + r.uniform(0, 1.4)), (0.15,) * 3, M['wall'], col)
window(X, RY + 3.74, 1.8, 2.6, 1.6, 0.8, 'sky', col)

# SCHOOL (classroom)  X=400
X = 400; col = room('School', X, 'plank', 'cream', ceil='cream', lamp=600)
cube('board', (X, RY + 3.72, 2.0), (5.0, 0.06, 1.6), M['board'], col)
cube('board_frame', (X, RY + 3.75, 2.0), (5.3, 0.04, 1.85), M['plank'], col)
cube('tray', (X, RY + 3.6, 1.18), (5.0, 0.2, 0.05), M['plank'], col)
r = random.Random(21)
for row in range(3):
    x0 = X - 2.0
    for k in range(r.randint(5, 9)):
        cube('chalk', (x0 + k * 0.32, RY + 3.68, 2.45 - row * 0.4), (0.24, 0.02, 0.05 + 0.05 * (k % 2)), M['chalk'], col)
cube('clock_s', (X, RY + 3.7, 3.4), (0.55, 0.05, 0.55), M['quartz'], col)
cube('clock_h', (X, RY + 3.66, 3.45), (0.04, 0.02, 0.22), M['dark'], col)
cube('kyotaku', (X + 3.4, RY + 2.6, 0.5), (1.2, 0.7, 1.0), M['plank'], col)
def sdesk(x, y):
    cube('sd_top', (x, y, 0.7), (0.9, 0.6, 0.06), M['plank'], col)
    cube('sd_leg', (x, y, 0.35), (0.06, 0.06, 0.7), M['steel'], col)
    cube('sd_chair', (x, y - 0.55, 0.4), (0.5, 0.45, 0.06), M['plank'], col)
    cube('sd_back', (x, y - 0.78, 0.65), (0.5, 0.05, 0.4), M['plank'], col)
for x in (-4.6, -3.2, 3.2, 4.6):
    for y in (0.6, -0.9, -2.4): sdesk(X + x, RY + y)
for y in (-3.0, -0.6, 1.8):
    cube('swin_f', (X - 5.72, RY + y, 2.3), (0.1, 2.0, 1.8), M['frame'], col)
    cube('swin_g', (X - 5.66, RY + y, 2.3), (0.04, 1.8, 1.6), M['sky'], col)
cube('locker', (X + 5.6, RY + 0, 0.6), (0.6, 4.0, 1.2), M['steel'], col)

# TRAIN (commuter car)  X=500
X = 500; col = room('Train', X, 'trainfloor', 'trainwall', h=2.9, ceil='trainwall', lamp=550, back=3.6)
cube('t_seat', (X, RY + 3.0, 0.45), (10.0, 0.9, 0.18), M['seat'], col)
cube('t_seat_base', (X, RY + 3.05, 0.2), (10.0, 0.8, 0.4), M['steel'], col)
cube('t_back', (X, RY + 3.42, 0.85), (10.0, 0.15, 0.7), M['seat'], col)
for wx in (-3.6, 0.0, 3.6):
    cube('t_win_f', (X + wx, RY + 3.33, 1.75), (3.1, 0.06, 0.95), M['frame'], col)
    cube('t_win_g', (X + wx, RY + 3.28, 1.75), (2.9, 0.04, 0.8), M['sky'], col)
cube('t_rack', (X, RY + 3.0, 2.35), (10.0, 0.55, 0.05), M['steel'], col)
cube('t_rail', (X, RY + 1.6, 2.45), (12.0, 0.05, 0.05), M['steel'], col)
for k in range(-9, 10):
    cube('strap_s', (X + k * 0.6, RY + 1.6, 2.28), (0.03, 0.03, 0.3), M['strap'], col)
    cube('strap_r', (X + k * 0.6, RY + 1.6, 2.06), (0.14, 0.03, 0.14), M['strap'], col)
for px in (-5.2, 5.2): cube('pole', (X + px, RY + 2.4, 1.45), (0.06, 0.06, 2.9), M['steel'], col)
for sx in (-5.74, 5.74):
    cube('t_door', (X + sx, RY + 0.3, 1.1), (0.06, 1.3, 2.1), M['steel'], col)
    cube('t_door_w', (X + sx * 0.995, RY + 0.3, 1.5), (0.04, 0.9, 0.8), M['sky'], col)
for lx in (-3, 0, 3): cube('t_light', (X + lx, RY + 1.0, 2.78), (2.0, 0.25, 0.04), M['quartz'], col)
cube('t_ad', (X + 2.0, RY + 3.34, 2.65), (1.4, 0.04, 0.4), M['tvon'], col)

# KITCHEN  X=600
X = 600; col = room('Kitchen', X, 'chk', 'cream', ceil='cream', lamp=600)
cube('k_counter', (X - 1.0, RY + 3.3, 0.45), (6.0, 0.8, 0.9), M['cabinet'], col)
cube('k_top', (X - 1.0, RY + 3.3, 0.92), (6.1, 0.85, 0.05), M['steel'], col)
cube('k_sink', (X - 2.5, RY + 3.3, 0.94), (1.0, 0.6, 0.03), M['dark'], col)
cube('k_faucet', (X - 2.5, RY + 3.6, 1.15), (0.08, 0.08, 0.4), M['steel'], col)
cube('k_stove', (X + 0.8, RY + 3.3, 0.95), (1.2, 0.7, 0.03), M['dark'], col)
for bx in (0.5, 1.1): cube('k_burner', (X + bx, RY + 3.3, 0.97), (0.3, 0.3, 0.02), M['burner'], col)
cube('k_pot', (X + 0.5, RY + 3.3, 1.12), (0.4, 0.4, 0.3), M['steel'], col)
cube('k_upper', (X - 1.0, RY + 3.55, 2.5), (6.0, 0.5, 0.9), M['cabinet'], col)
cube('k_hood', (X + 0.8, RY + 3.4, 1.9), (1.2, 0.7, 0.3), M['steel'], col)
window(X, RY + 3.74, -2.5, 1.65, 1.4, 0.7, 'sky', col)
cube('fridge', (X + 3.4, RY + 3.2, 1.0), (1.1, 0.9, 2.0), M['fridge'], col)
cube('fridge_h', (X + 2.95, RY + 2.73, 1.3), (0.05, 0.05, 0.5), M['steel'], col)
cube('k_table', (X - 4.0, RY + 0.8, 0.75), (1.4, 1.0, 0.06), M['plank'], col)
cube('k_table_l', (X - 4.0, RY + 0.8, 0.37), (0.1, 0.1, 0.74), M['log'], col)
for bx, c in ((-4.3, 'carpet'), (-3.7, 'yellowb')): cube('dish', (X + bx, RY + 0.8, 0.81), (0.3, 0.3, 0.06), M[c], col)
