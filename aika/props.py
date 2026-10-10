"""Hand-painted props (chair / table / food) in anime style, drawn at 3x and downsampled.
All coordinates are final canvas coordinates (1080x1920)."""
import math, numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

W, H = 1080, 1920
SS = 3
X0, Y0, RW, RH = 120, 900, 960, 560   # working region on canvas
LINE = (88, 56, 40, 255)

def new():
    return Image.new('RGBA', (RW * SS, RH * SS), (0, 0, 0, 0))
def P(pts):  # canvas -> region*SS
    return [((x - X0) * SS, (y - Y0) * SS) for x, y in pts]
def B(b):
    return [(b[0] - X0) * SS, (b[1] - Y0) * SS, (b[2] - X0) * SS, (b[3] - Y0) * SS]

def lin_grad(size, p0, p1, c0, c1):
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    (x0, y0), (x1, y1) = p0, p1
    vx, vy = x1 - x0, y1 - y0; L = vx * vx + vy * vy + 1e-6
    t = np.clip(((xx - x0) * vx + (yy - y0) * vy) / L, 0, 1)[..., None]
    c0 = np.array(c0, np.float32); c1 = np.array(c1, np.float32)
    if len(c0) == 3: c0 = np.append(c0, 255); c1 = np.append(c1, 255)
    return Image.fromarray((c0 * (1 - t) + c1 * t).astype(np.uint8), 'RGBA')

def fill_shape(img, drawfn, p0, p1, c0, c1, outline=True, ow=3):
    """drawfn(draw, fill) draws the shape. gradient from canvas p0->p1"""
    m = Image.new('L', img.size, 0); drawfn(ImageDraw.Draw(m), 255)
    g = lin_grad(img.size, P([p0])[0], P([p1])[0], c0, c1)
    img.alpha_composite(Image.composite(g, Image.new('RGBA', img.size, (0, 0, 0, 0)), m))
    if outline and ow:
        bb = m.getbbox()
        if bb:
            r = int(round(ow * SS)); pad = r + 2
            bx = (max(0, bb[0] - pad), max(0, bb[1] - pad), min(img.width, bb[2] + pad), min(img.height, bb[3] + pad))
            mc = m.crop(bx)
            e = mc.filter(ImageFilter.MaxFilter(2 * r + 1))
            ring = ImageChops.subtract(e, mc)
            img.alpha_composite(Image.composite(Image.new('RGBA', mc.size, LINE), Image.new('RGBA', mc.size, (0, 0, 0, 0)), ring), (bx[0], bx[1]))
    return m

def poly(img, pts, c0, c1=None, g0=None, g1=None, ow=1.2):
    c1 = c1 or c0
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    g0 = g0 or (min(xs), min(ys)); g1 = g1 or (min(xs), max(ys))
    return fill_shape(img, lambda d, f: d.polygon(P(pts), fill=f), g0, g1, c0, c1, ow=ow)

def ell(img, b, c0, c1=None, g0=None, g1=None, ow=1.2):
    c1 = c1 or c0
    g0 = g0 or (b[0], b[1]); g1 = g1 or (b[0], b[3])
    return fill_shape(img, lambda d, f: d.ellipse(B(b), fill=f), g0, g1, c0, c1, ow=ow)

def line(img, pts, col, w):
    ImageDraw.Draw(img).line(P(pts), fill=col, width=int(w * SS), joint='curve')

def soft(img, drawfn, col, blur):
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); drawfn(ImageDraw.Draw(lay), col)
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(blur * SS)))

def clip_to(img, mask, layer):
    a = ImageChops.multiply(layer.getchannel('A'), mask)
    layer.putalpha(a); img.alpha_composite(layer)

def finish(img):
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    out.alpha_composite(img.resize((RW, RH), Image.LANCZOS), (X0, Y0))
    return out

WOOD = (214, 160, 102); WOOD_D = (150, 98, 58); WOOD_L = (238, 196, 140)

def wood_grain(img, mask, pts_dir, n=26, seed=1):
    rng = np.random.default_rng(seed)
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    w, h = img.size
    for i in range(n):
        y = rng.uniform(0, h); amp = rng.uniform(2, 7) * SS
        pts = [(x, y + amp * math.sin(x / (rng.uniform(40, 90) * SS) + i) + (x * pts_dir)) for x in range(0, w, 12)]
        d.line(pts, fill=(130, 82, 45, int(rng.uniform(40, 90))), width=SS)
    clip_to(img, mask, lay)

# ---------------- table (drawn IN FRONT of the character) ----------------
TT = [(652, 1116), (940, 1108), (982, 1182), (640, 1192)]   # table top quad (far-left, far-right, near-right, near-left)

def table_base():
    img = new()
    soft(img, lambda d, c: d.ellipse(B((600, 1340, 1040, 1440)), fill=c), (60, 30, 15, 120), 16)
    # far legs
    for a, b in [((664, 1128), (668, 1352)), ((930, 1122), (934, 1345))]:
        poly(img, [(a[0] - 8, a[1]), (a[0] + 8, a[1]), (b[0] + 7, b[1]), (b[0] - 7, b[1])], WOOD_D, (118, 76, 44))
    # lower shelf (storage)
    sh = [(664, 1290), (932, 1284), (968, 1330), (650, 1338)]
    msh = poly(img, sh, (196, 142, 88), (170, 118, 70))
    wood_grain(img, msh, 0.0, 10, 4)
    poly(img, [(650, 1338), (968, 1330), (968, 1342), (650, 1350)], WOOD_D)
    # apron / top thickness
    poly(img, [(640, 1192), (982, 1182), (982, 1206), (641, 1216)], (196, 138, 84), (160, 104, 60), g0=(0, 1182), g1=(0, 1216))
    # top surface with slats
    mt = poly(img, TT, WOOD_L, (222, 170, 112), g0=(980, 1110), g1=(640, 1190))
    slat = Image.new('RGBA', img.size, (0, 0, 0, 0))
    for k in range(1, 7):
        t = k / 7
        l = (TT[0][0] + (TT[3][0] - TT[0][0]) * t, TT[0][1] + (TT[3][1] - TT[0][1]) * t)
        r = (TT[1][0] + (TT[2][0] - TT[1][0]) * t, TT[1][1] + (TT[2][1] - TT[1][1]) * t)
        ImageDraw.Draw(slat).line(P([l, r]), fill=(150, 100, 58, 150), width=2 * SS)
        ImageDraw.Draw(slat).line(P([(l[0], l[1] + 2), (r[0], r[1] + 2)]), fill=(255, 236, 200, 110), width=SS)
    clip_to(img, mt, slat)
    wood_grain(img, mt, -0.02, 22, 2)
    # warm lantern highlight on right of top
    hl = lin_grad(img.size, P([(990, 1110)])[0], P([(760, 1180)])[0], (255, 220, 150, 110), (255, 220, 150, 0))
    clip_to(img, mt, hl)
    # near legs
    for a, b in [((654, 1214), (650, 1420)), ((966, 1204), (972, 1414))]:
        poly(img, [(a[0] - 11, a[1]), (a[0] + 11, a[1]), (b[0] + 10, b[1]), (b[0] - 10, b[1])], WOOD, WOOD_D, g0=(a[0] - 11, 0), g1=(a[0] + 11, 0))
        line(img, [(a[0] - 4, a[1] + 8), (b[0] - 4, b[1] - 8)], (255, 228, 185, 170), 3)
    return img

def contact_shadow(img, b, alpha=90):
    soft(img, lambda d, c: d.ellipse(B(b), fill=c), (90, 50, 25, alpha), 4)

def mug(img, cx, cy, body=(255, 246, 240), drink=(150, 92, 60), heart=True):
    contact_shadow(img, (cx - 34, cy + 36, cx + 40, cy + 54))
    # handle
    ImageDraw.Draw(img).ellipse(B((cx + 18, cy - 8, cx + 48, cy + 30)), outline=LINE, width=int(8.5 * SS))
    ImageDraw.Draw(img).ellipse(B((cx + 18, cy - 8, cx + 48, cy + 30)), outline=body + (255,), width=int(5 * SS))
    poly(img, [(cx - 30, cy - 30), (cx + 30, cy - 30), (cx + 28, cy + 40), (cx - 28, cy + 40)], body, (225, 205, 205), g0=(cx - 30, 0), g1=(cx + 30, 0))
    ell(img, (cx - 28, cy + 30, cx + 28, cy + 48), body, (220, 200, 200))
    poly(img, [(cx - 28, cy + 30), (cx + 28, cy + 30), (cx + 28, cy + 38), (cx - 28, cy + 38)], (238, 222, 222), ow=0)
    ell(img, (cx - 30, cy - 40, cx + 30, cy - 20), (255, 255, 255))
    ell(img, (cx - 25, cy - 37, cx + 25, cy - 23), drink, tuple(int(v * 0.8) for v in drink), ow=0.6)
    if heart:
        hx, hy = cx - 2, cy + 6; pts = []
        for i in range(40):
            a = i / 40 * 2 * math.pi
            pts.append((hx + 0.9 * 16 * math.sin(a) ** 3, hy - 0.9 * (13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))))
        ImageDraw.Draw(img).polygon(P(pts), fill=(255, 120, 160, 255))
    line(img, [(cx - 22, cy - 22), (cx - 20, cy + 30)], (255, 255, 255, 170), 4)

def plate(img, cx, cy, rx, ry):
    contact_shadow(img, (cx - rx, cy + ry * 0.2, cx + rx + 6, cy + ry * 1.25), 110)
    ell(img, (cx - rx, cy - ry, cx + rx, cy + ry), (255, 255, 255), (226, 222, 230))
    ell(img, (cx - rx * 0.72, cy - ry * 0.68, cx + rx * 0.72, cy + ry * 0.72), (244, 240, 246), (255, 255, 255), ow=0.6)
    ImageDraw.Draw(img).arc(B((cx - rx + 4, cy - ry + 3, cx + rx - 4, cy + ry - 3)), 190, 260, fill=(255, 150, 180, 255), width=2 * SS)

def pancakes(img, cx, cy):
    plate(img, cx, cy + 6, 100, 34)
    rx, ry, th = 72, 24, 15
    for k in range(3):
        y = cy - k * th
        # side band
        poly(img, [(cx - rx, y - 2), (cx + rx, y - 2), (cx + rx, y + 12), (cx - rx, y + 12)], (214, 140, 66), (176, 104, 44), g0=(cx - rx, 0), g1=(cx + rx, 0), ow=0)
        ImageDraw.Draw(img).chord(B((cx - rx, y + 12 - ry, cx + rx, y + 12 + ry)), 0, 180, fill=(176, 104, 44, 255))
        ImageDraw.Draw(img).arc(B((cx - rx, y + 12 - ry, cx + rx, y + 12 + ry)), 0, 180, fill=LINE, width=int(1.2 * SS))
        line(img, [(cx - rx, y - 2), (cx - rx, y + 12)], LINE, 1.2); line(img, [(cx + rx, y - 2), (cx + rx, y + 12)], LINE, 1.2)
        line(img, [(cx - rx + 6, y + 6), (cx + rx - 6, y + 6)], (240, 196, 130, 160), 2)
        ell(img, (cx - rx, y - 2 - ry, cx + rx, y - 2 + ry), (244, 190, 112), (226, 160, 82), ow=1.0)
    y = cy - 2 * th - 2
    # golden top sheen
    soft(img, lambda d, c: d.ellipse(B((cx - 40, y - 16, cx + 20, y + 4)), fill=c), (255, 236, 180, 140), 4)
    # syrup
    sy = [(cx - 50, y - 6), (cx - 20, y - 18), (cx + 30, y - 16), (cx + 58, y - 2), (cx + 62, y + 22), (cx + 56, y + 30), (cx + 50, y + 8),
          (cx + 30, y + 14), (cx + 12, y + 40), (cx + 4, y + 16), (cx - 26, y + 14), (cx - 34, y + 34), (cx - 42, y + 10), (cx - 58, y + 4)]
    poly(img, sy, (170, 90, 30), (120, 58, 18), ow=0.8)
    line(img, [(cx - 30, y - 8), (cx + 10, y - 12)], (255, 220, 170, 200), 3)
    # butter
    poly(img, [(cx - 16, y - 22), (cx + 14, y - 24), (cx + 18, y - 10), (cx - 14, y - 8)], (255, 240, 150), (240, 210, 100))
    poly(img, [(cx - 14, y - 8), (cx + 18, y - 10), (cx + 18, y - 4), (cx - 14, y - 2)], (232, 200, 90), ow=0.8)
    # berries
    for bx, by in [(cx + 40, y - 6), (cx - 52, y + 2)]:
        ell(img, (bx - 11, by - 13, bx + 11, by + 9), (255, 80, 90), (200, 30, 50))
        for sx_, sy_ in [(-4, -3), (3, -5), (0, 2), (5, 3), (-5, 4)]:
            ImageDraw.Draw(img).ellipse(B((bx + sx_ - 1, by + sy_ - 1, bx + sx_ + 1, by + sy_ + 1)), fill=(255, 230, 140, 255))
        poly(img, [(bx - 7, by - 12), (bx, by - 18), (bx + 7, by - 12), (bx, by - 9)], (90, 180, 80), ow=0.6)
    for bx, by in [(cx + 22, y + 4), (cx - 30, y - 12), (cx + 60, y + 30)]:
        ell(img, (bx - 6, by - 6, bx + 6, by + 6), (90, 100, 190), (50, 50, 120), ow=0.8)
    # mint
    poly(img, [(cx - 4, y - 30), (cx + 10, y - 40), (cx + 6, y - 26)], (110, 200, 110), ow=0.6)

def bowl(img, cx, cy, rx, ry, depth, outer0, outer1, rim, liquid0, liquid1):
    contact_shadow(img, (cx - rx * 0.8, cy + depth - 8, cx + rx * 0.9, cy + depth + 14), 110)
    # body: half-ellipse-ish
    body = [(cx - rx, cy)] + [(cx + rx * math.cos(a), cy + depth * math.sin(a)) for a in np.linspace(math.pi, 0, 40)[::-1]][::-1] + [(cx + rx, cy)]
    pts = [(cx - rx, cy)]
    for a in np.linspace(0, math.pi, 40):
        pts.append((cx - rx * math.cos(a), cy + depth * math.sin(a) ** 0.8))
    poly(img, pts, outer0, outer1, g0=(cx - rx, 0), g1=(cx + rx, 0))
    # foot
    ell(img, (cx - rx * 0.4, cy + depth - 8, cx + rx * 0.4, cy + depth + 4), outer1, outer1, ow=0.8)
    # rim and liquid
    ell(img, (cx - rx, cy - ry, cx + rx, cy + ry), rim, rim)
    ell(img, (cx - rx * 0.88, cy - ry * 0.78, cx + rx * 0.88, cy + ry * 0.8), liquid0, liquid1, g0=(cx, cy - ry), g1=(cx, cy + ry), ow=0.7)
    line(img, [(cx - rx * 0.8, cy + 10), (cx - rx * 0.6, cy + depth * 0.7)], (255, 255, 255, 120), 4)

def soup(img, cx, cy):
    # small plate under bowl
    plate(img, cx, cy + 44, 92, 30)
    bowl(img, cx, cy, 70, 24, 52, (255, 238, 244), (236, 176, 196), (255, 252, 252), (255, 186, 92), (234, 140, 60))
    d = ImageDraw.Draw(img)
    # cream swirl & croutons & parsley
    d.arc(B((cx - 30, cy - 10, cx + 20, cy + 10)), 20, 300, fill=(255, 246, 225, 230), width=3 * SS)
    for x, y in [(cx - 38, cy - 4), (cx + 28, cy + 2), (cx + 6, cy - 12)]:
        poly(img, [(x - 7, y - 6), (x + 7, y - 7), (x + 8, y + 5), (x - 6, y + 6)], (240, 196, 110), (200, 150, 70), ow=0.7)
    for x, y in [(cx - 12, cy + 6), (cx + 40, cy - 8), (cx - 50, cy + 4), (cx + 18, cy + 10)]:
        d.ellipse(B((x - 3, y - 2, x + 3, y + 2)), fill=(90, 160, 70, 255))
    # bread on a little board
    poly(img, [(842, 1112), (936, 1104), (950, 1126), (848, 1136)], (205, 150, 92), (170, 118, 70))
    for k, (x, y) in enumerate([(870, 1108), (912, 1104)]):
        ell(img, (x - 22, y - 16, x + 22, y + 14), (238, 186, 110), (196, 132, 64))
        ell(img, (x - 15, y - 10, x + 15, y + 8), (255, 240, 214), (246, 222, 186), ow=0.6)

def udon(img, cx, cy):
    bowl(img, cx, cy, 82, 28, 62, (196, 52, 52), (130, 26, 30), (40, 30, 30), (226, 178, 108), (196, 140, 76))
    d = ImageDraw.Draw(img)
    # inner rim highlight
    d.arc(B((cx - 80, cy - 27, cx + 80, cy + 27)), 200, 340, fill=(255, 255, 255, 90), width=2 * SS)
    # noodles: thick white strands
    rng = np.random.default_rng(5)
    for k in range(9):
        y0 = cy - 14 + k * 3.6; x0 = cx - 58 + rng.uniform(-4, 4)
        pts = [(x0 + i * 14, y0 + 5 * math.sin(i * 0.9 + k)) for i in range(9)]
        line(img, pts, LINE, 8.5); line(img, pts, (255, 250, 236, 255), 6)
    # kamaboko (naruto)
    ell(img, (cx + 12, cy - 18, cx + 50, cy - 2), (255, 255, 255), (240, 232, 236))
    d.arc(B((cx + 20, cy - 15, cx + 42, cy - 5)), 0, 320, fill=(255, 110, 150, 255), width=2 * SS)
    # boiled egg half
    ell(img, (cx - 54, cy - 12, cx - 18, cy + 12), (255, 255, 250), (236, 232, 222))
    ell(img, (cx - 45, cy - 5, cx - 27, cy + 7), (255, 190, 60), (240, 150, 40), ow=0.6)
    # green onions
    for x, y in [(cx - 6, cy - 8), (cx + 2, cy + 4), (cx + 52, cy + 6), (cx - 60, cy + 12), (cx - 14, cy + 10), (cx + 30, cy + 10)]:
        d.ellipse(B((x - 5, y - 3, x + 5, y + 3)), fill=(80, 160, 60, 255), outline=(40, 100, 30, 255), width=SS)
    # shrimp tempura leaning on rim
    sh = [(cx + 36, cy - 30), (cx + 92, cy - 64), (cx + 104, cy - 56), (cx + 52, cy - 14)]
    poly(img, sh, (246, 196, 100), (210, 150, 60))
    for k in range(5):
        t = k / 5; x = cx + 40 + 56 * t; y = cy - 28 - 32 * t
        d.ellipse(B((x - 6, y - 3, x + 4, y + 5)), fill=(255, 224, 150, 255))
    poly(img, [(cx + 98, cy - 62), (cx + 116, cy - 74), (cx + 112, cy - 58)], (255, 90, 70), (200, 50, 40), ow=0.8)
    # yunomi tea cup
    cx2, cy2 = 920, 1112
    contact_shadow(img, (cx2 - 28, cy2 + 28, cx2 + 30, cy2 + 42))
    poly(img, [(cx2 - 24, cy2 - 22), (cx2 + 24, cy2 - 22), (cx2 + 21, cy2 + 32), (cx2 - 21, cy2 + 32)], (232, 222, 196), (190, 176, 150), g0=(cx2 - 24, 0), g1=(cx2 + 24, 0))
    line(img, [(cx2 - 23, cy2), (cx2 + 23, cy2)], (120, 150, 110, 200), 3)
    ell(img, (cx2 - 24, cy2 - 30, cx2 + 24, cy2 - 14), (240, 232, 210))
    ell(img, (cx2 - 20, cy2 - 27, cx2 + 20, cy2 - 17), (170, 190, 90), (130, 150, 60), ow=0.6)

def table(kind):
    img = table_base()
    if kind == 'pancake':
        pancakes(img, 790, 1152); mug(img, 918, 1118)
    elif kind == 'soup':
        soup(img, 780, 1140)
    elif kind == 'udon':
        udon(img, 790, 1142)
    return finish(img)

# ---------------- episode 2/3 foods ----------------
def parfait(img, cx, by):
    """tall glass; by = bottom y on table"""
    contact_shadow(img, (cx - 40, by - 6, cx + 44, by + 10), 120)
    # foot + stem
    ell(img, (cx - 34, by - 12, cx + 34, by + 6), (235, 240, 250), (200, 210, 225), ow=1)
    poly(img, [(cx - 6, by - 40), (cx + 6, by - 40), (cx + 6, by - 6), (cx - 6, by - 6)], (230, 236, 248), (200, 208, 224), g0=(cx - 6, 0), g1=(cx + 6, 0), ow=1)
    top, bot = by - 175, by - 40
    def glass_pts(y0, y1):
        def wx(y):  # tapered glass
            t = (y - top) / (bot - top); return 44 - 16 * t ** 1.6
        return [(cx - wx(y0), y0), (cx + wx(y0), y0), (cx + wx(y1), y1), (cx - wx(y1), y1)]
    layers = [(bot - 30, bot, (240, 200, 120), (210, 160, 80)),      # cornflakes
              (bot - 58, bot - 30, (255, 252, 245), (240, 232, 225)),  # cream
              (bot - 84, bot - 58, (230, 60, 90), (190, 30, 60)),      # berry sauce
              (bot - 112, bot - 84, (255, 230, 240), (245, 200, 215)),  # strawberry mousse
              (top + 10, bot - 112, (255, 250, 245), (236, 228, 222))]  # cream
    for y0, y1, c0, c1 in layers:
        poly(img, glass_pts(y0, y1), c0, c1, g0=(cx - 40, 0), g1=(cx + 40, 0), ow=0)
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(3)
    for i in range(14):  # flakes texture
        x = cx + rng.uniform(-24, 24); y = bot - rng.uniform(4, 26)
        d.ellipse(B((x - 4, y - 2, x + 4, y + 2)), fill=(190, 130, 60, 255))
    # strawberry slices against glass
    for x, y in [(cx - 22, bot - 98), (cx + 18, bot - 98), (cx - 2, bot - 70)]:
        ell(img, (x - 12, y - 9, x + 12, y + 9), (255, 90, 110), (210, 40, 70), ow=0.8)
        ell(img, (x - 6, y - 4, x + 6, y + 4), (255, 200, 205), ow=0)
    # glass outline + highlight
    gp = glass_pts(top, bot)
    line(img, [gp[0], gp[3]], LINE, 1.4); line(img, [gp[1], gp[2]], LINE, 1.4)
    line(img, [(gp[3][0], gp[3][1]), (gp[2][0], gp[2][1])], LINE, 1.2)
    line(img, [(cx - 34, top + 14), (cx - 24, bot - 8)], (255, 255, 255, 170), 4)
    # whipped cream swirl on top
    for k, (rx, ry, yy) in enumerate([(46, 16, top), (36, 14, top - 14), (24, 11, top - 26), (12, 8, top - 36)]):
        ell(img, (cx - rx, yy - ry, cx + rx, yy + ry), (255, 255, 252), (238, 232, 230), ow=1)
    # strawberries on top
    for x, y, r in [(cx - 26, top - 16, 15), (cx + 24, top - 14, 14), (cx + 2, top - 46, 13)]:
        pts = [(x - r, y - r * 0.4), (x, y - r * 1.1), (x + r, y - r * 0.4), (x + r * 0.5, y + r), (x - r * 0.5, y + r)]
        ell(img, (x - r, y - r, x + r, y + r), (255, 70, 90), (200, 25, 50))
        for sx_, sy_ in [(-5, -2), (4, -4), (0, 4), (6, 4), (-6, 5)]:
            d.ellipse(B((x + sx_ - 1.2, y + sy_ - 1.2, x + sx_ + 1.2, y + sy_ + 1.2)), fill=(255, 230, 150, 255))
        poly(img, [(x - 8, y - r + 2), (x, y - r - 6), (x + 8, y - r + 2), (x, y - r + 5)], (90, 180, 80), ow=0.6)
    # wafer stick + mint
    poly(img, [(cx + 30, top - 70), (cx + 42, top - 74), (cx + 22, top - 4), (cx + 12, top - 2)], (240, 196, 120), (210, 150, 80))
    poly(img, [(cx - 14, top - 48), (cx - 2, top - 62), (cx + 2, top - 46)], (110, 200, 110), ow=0.6)
    # small plate with strawberries
    plate(img, 918, 1134, 46, 16)
    for x, y in [(906, 1124), (926, 1128)]:
        ell(img, (x - 11, y - 12, x + 11, y + 10), (255, 70, 90), (200, 25, 50))
        poly(img, [(x - 7, y - 11), (x, y - 17), (x + 7, y - 11), (x, y - 8)], (90, 180, 80), ow=0.6)

TAB = [(846, 1034), (958, 1018), (960, 1094), (849, 1106)]   # tablet screen quad (canvas, before TSHIFT)
def cake_tablet(img):
    # little stand
    poly(img, [(890, 1098), (912, 1095), (926, 1142), (874, 1146)], (236, 236, 242), (190, 190, 200))
    # tablet with pink case (landscape), screen faces viewer/her
    d = ImageDraw.Draw(img)
    poly(img, [(836, 1026), (968, 1008), (971, 1102), (839, 1116)], (255, 170, 196), (230, 130, 160))
    poly(img, [(841, 1030), (963, 1013), (966, 1098), (844, 1111)], (40, 40, 50), (24, 24, 32), ow=0.6)
    poly(img, TAB, (40, 50, 80), ow=0)
    contact_shadow(img, (860, 1136, 940, 1150))
    # shortcake slice on plate
    cx, cy = 742, 1150
    plate(img, cx, cy + 8, 82, 28)
    # prism: back edge (cx-40,cy-30) apex at front (cx+44, cy+4)
    tb = [(cx - 52, cy - 34), (cx + 30, cy - 46), (cx + 46, cy - 8)]   # top triangle
    hgt = 46
    side = [tb[0], tb[2], (tb[2][0], tb[2][1] + hgt), (tb[0][0], tb[0][1] + hgt)]
    poly(img, side, (255, 236, 190), (246, 214, 160), ow=1.2)
    d = ImageDraw.Draw(img)
    # layers on cut face: sponge / cream+strawberry / sponge
    for k, (dy, c, w_) in enumerate([(14, (255, 255, 250, 255), 9), (24, (235, 60, 90, 255), 5), (32, (255, 255, 250, 255), 6)]):
        line(img, [(tb[0][0] + 2, tb[0][1] + dy), (tb[2][0] - 2, tb[2][1] + dy)], c[:3] + (255,), w_)
    poly(img, [tb[2], tb[1], (tb[1][0], tb[1][1] + hgt), (tb[2][0], tb[2][1] + hgt)], (255, 250, 245), (240, 230, 228), ow=1.2)
    poly(img, tb, (255, 255, 255), (245, 240, 240), ow=1.2)
    for x, y in [(cx - 30, cy - 34), (cx - 6, cy - 38), (cx + 18, cy - 36)]:
        ell(img, (x - 9, y - 7, x + 9, y + 7), (255, 255, 252), (236, 230, 228), ow=0.8)
    x, y, r = cx - 6, cy - 50, 14
    ell(img, (x - r, y - r, x + r, y + r), (255, 70, 90), (200, 25, 50))
    poly(img, [(x - 8, y - r + 2), (x, y - r - 6), (x + 8, y - r + 2), (x, y - r + 5)], (90, 180, 80), ow=0.6)
    line(img, [(x - 6, y - 6), (x - 2, y - 9)], (255, 220, 220, 230), 3)

def nabe(img, cx, cy):
    contact_shadow(img, (cx - 96, cy + 40, cx + 100, cy + 66), 120)
    # trivet
    poly(img, [(cx - 92, cy + 44), (cx + 92, cy + 44), (cx + 96, cy + 56), (cx - 96, cy + 56)], (180, 130, 80), (140, 96, 56))
    # pot body
    pts = [(cx - 96, cy)]
    for a in np.linspace(0, math.pi, 40):
        pts.append((cx - 96 * math.cos(a), cy + 50 * math.sin(a) ** 0.7))
    poly(img, pts, (120, 80, 60), (70, 44, 32), g0=(cx - 96, 0), g1=(cx + 96, 0))
    # white glaze drips on rim
    d = ImageDraw.Draw(img)
    for x in range(int(cx - 88), int(cx + 88), 14):
        d.ellipse(B((x - 6, cy + 2, x + 6, cy + 14 + (x * 7) % 9)), fill=(236, 226, 206, 255))
    # handles
    for sx_ in (-1, 1):
        ell(img, (cx + sx_ * 104 - 14, cy - 2, cx + sx_ * 104 + 14, cy + 12), (110, 72, 52), (70, 44, 32))
    ell(img, (cx - 96, cy - 32, cx + 96, cy + 32), (226, 214, 190), (200, 186, 160))
    ell(img, (cx - 86, cy - 26, cx + 86, cy + 26), (232, 196, 140), (210, 168, 110), ow=0.8)
    # ingredients
    for x, y in [(cx - 50, cy - 6), (cx - 20, cy + 8)]:   # napa cabbage
        poly(img, [(x - 20, y - 8), (x + 18, y - 12), (x + 22, y + 6), (x - 18, y + 10)], (240, 246, 220), (200, 226, 150), ow=0.8)
        line(img, [(x - 14, y), (x + 16, y - 2)], (160, 200, 110, 255), 2)
    for x, y in [(cx + 14, cy - 10), (cx + 44, cy - 2)]:  # tofu
        poly(img, [(x - 13, y - 9), (x + 13, y - 11), (x + 15, y + 7), (x - 11, y + 9)], (255, 253, 245), (236, 232, 220), ow=0.8)
    for x, y in [(cx - 60, cy + 12), (cx + 62, cy + 10)]:  # shiitake
        ell(img, (x - 14, y - 9, x + 14, y + 9), (140, 92, 60), (100, 62, 40), ow=0.8)
        line(img, [(x - 7, y - 4), (x + 7, y + 4)], (240, 220, 190, 255), 2); line(img, [(x + 7, y - 4), (x - 7, y + 4)], (240, 220, 190, 255), 2)
    for x, y in [(cx + 20, cy + 14), (cx - 40, cy - 18)]:  # carrot flowers
        for k in range(5):
            a = k / 5 * 2 * math.pi
            d.ellipse(B((x + 6 * math.cos(a) - 5, y + 3.5 * math.sin(a) - 4, x + 6 * math.cos(a) + 5, y + 3.5 * math.sin(a) + 4)), fill=(255, 140, 60, 255))
        d.ellipse(B((x - 3, y - 2, x + 3, y + 2)), fill=(255, 200, 120, 255))
    for x, y in [(cx + 40, cy - 18), (cx - 4, cy - 18), (cx - 70, cy - 4)]:  # chicken
        ell(img, (x - 10, y - 6, x + 10, y + 6), (250, 230, 205), (225, 196, 160), ow=0.7)
    for x, y in [(cx + 2, cy + 2), (cx + 30, cy + 4), (cx - 32, cy + 16), (cx + 50, cy + 18)]:
        d.ellipse(B((x - 5, y - 3, x + 5, y + 3)), fill=(90, 170, 60, 255), outline=(40, 100, 30, 255), width=SS)
    # small bowl (torizara) with ponzu
    bowl(img, 930, 1130, 32, 11, 22, (255, 245, 240), (226, 200, 196), (255, 255, 255), (170, 110, 60), (140, 80, 40))

def pudding(img, cx, cy):
    plate(img, cx, cy + 8, 82, 28)
    # pudding: truncated cone
    top_r, bot_r, hgt = 34, 50, 56
    ty = cy - hgt
    poly(img, [(cx - top_r, ty), (cx + top_r, ty), (cx + bot_r, cy), (cx - bot_r, cy)], (255, 214, 110), (238, 176, 70), g0=(cx - bot_r, 0), g1=(cx + bot_r, 0))
    ImageDraw.Draw(img).chord(B((cx - bot_r, cy - 14, cx + bot_r, cy + 14)), 0, 180, fill=(238, 176, 70, 255))
    ImageDraw.Draw(img).arc(B((cx - bot_r, cy - 14, cx + bot_r, cy + 14)), 0, 180, fill=LINE, width=int(1.2 * SS))
    ell(img, (cx - top_r, ty - 11, cx + top_r, ty + 11), (150, 74, 26), (110, 50, 16))
    # caramel drips
    for x, ln in [(cx - 26, 22), (cx - 6, 30), (cx + 18, 18), (cx + 30, 12)]:
        poly(img, [(x - 5, ty + 2), (x + 5, ty + 2), (x + 4, ty + ln), (x, ty + ln + 5), (x - 4, ty + ln)], (150, 74, 26), (120, 56, 18), ow=0.6)
    line(img, [(cx - 30, ty + 18), (cx - 40, cy - 8)], (255, 245, 210, 170), 4)
    # cream + cherry
    for rx, ry, yy in [(20, 8, ty - 10), (13, 6, ty - 18)]:
        ell(img, (cx - rx, yy - ry, cx + rx, yy + ry), (255, 255, 252), (236, 230, 228), ow=0.9)
    ell(img, (cx - 9, ty - 40, cx + 9, ty - 22), (230, 30, 60), (170, 10, 40))
    line(img, [(cx + 2, ty - 38), (cx + 12, ty - 56)], (90, 140, 60, 255), 2.5)
    line(img, [(cx - 4, ty - 34), (cx - 1, ty - 36)], (255, 200, 210, 255), 3)
    # cocoa mug with marshmallows
    mug(img, 918, 1118, body=(255, 240, 246), drink=(140, 84, 56))
    for x, y in [(906, 1081), (922, 1083), (932, 1079)]:
        ImageDraw.Draw(img).rounded_rectangle(B((x - 6, y - 4, x + 6, y + 4)), radius=2 * SS, fill=(255, 250, 252, 255), outline=LINE, width=SS)

_old_table = table
def table(kind):
    if kind in ('pancake', 'soup', 'udon'): return _old_table(kind)
    img = table_base()
    if kind == 'parfait': parfait(img, 790, 1172)
    elif kind == 'cake_tablet': cake_tablet(img)
    elif kind == 'nabe': nabe(img, 790, 1132)
    elif kind == 'pudding': pudding(img, 776, 1150)
    return finish(img)

# ---------------- front-facing chair (for frontal sitting poses) ----------------
def chair_front():
    img = new()
    soft(img, lambda d, c: d.ellipse(B((340, 1360, 740, 1430)), fill=c), (60, 30, 15, 130), 14)
    # back legs + backrest posts (behind her)
    for x in (432, 648):
        poly(img, [(x - 9, 1000), (x + 9, 1000), (x + 9, 1352), (x - 9, 1352)], WOOD_D, (118, 76, 44), g0=(x - 9, 0), g1=(x + 9, 0))
    poly(img, [(424, 1010), (656, 1010), (656, 1040), (424, 1040)], WOOD, WOOD_D)
    poly(img, [(436, 1300), (644, 1300), (644, 1312), (436, 1312)], WOOD_D)
    # seat top (mostly hidden under her) + cushion
    poly(img, [(420, 1214), (660, 1214), (690, 1244), (390, 1244)], (120, 196, 186), (96, 170, 160))
    poly(img, [(390, 1244), (690, 1244), (690, 1270), (390, 1270)], (96, 170, 160), (70, 140, 132), g0=(0, 1244), g1=(0, 1270))
    line(img, [(392, 1246), (688, 1246)], (220, 245, 240, 220), 3)
    for x in (450, 540, 630):
        ImageDraw.Draw(img).ellipse(B((x - 4, 1255, x + 4, 1261)), fill=(60, 120, 112, 255))
    # front rail
    poly(img, [(394, 1270), (686, 1270), (686, 1290), (394, 1290)], WOOD, WOOD_D, g0=(0, 1270), g1=(0, 1290))
    line(img, [(398, 1273), (682, 1273)], (255, 230, 190, 170), 2)
    # front legs
    for x in (408, 672):
        poly(img, [(x - 11, 1288), (x + 11, 1288), (x + 10, 1414), (x - 10, 1414)], WOOD, WOOD_D, g0=(x - 11, 0), g1=(x + 11, 0))
        line(img, [(x - 4, 1294), (x - 4, 1406)], (255, 228, 185, 170), 3)
    poly(img, [(412, 1372), (668, 1372), (668, 1382), (412, 1382)], WOOD_D)
    return finish(img)
