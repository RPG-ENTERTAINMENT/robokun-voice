import numpy as np, json, math, sys, wave, subprocess, os, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import importlib
EPN = os.environ.get('EP', 'ep_engine')
EP = importlib.import_module(EPN)
globals().update({k: v for k, v in vars(EP).items() if not k.startswith('_') and k not in ('char_state',)})
VOICE_DIR = getattr(EP, 'VOICE_DIR', 'voice')
TABLES = getattr(EP, 'TABLES', {})
STEAMX = {'soup': 780, 'udon': 790, 'nabe': 790, 'pudding': 918}
import props

W, H = 1080, 1920
FEET_Y = 1405
CX = 540
FONT = 'fonts/package/900Black/MPLUSRounded1c_900Black.ttf'
FONTB = 'fonts/package/800ExtraBold/MPLUSRounded1c_800ExtraBold.ttf'

def ease_out_back(x):
    x = min(max(x, 0), 1); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def clamp(x, a=0, b=1): return max(a, min(b, x))

# ---------------- backgrounds ----------------
ZB = 1.07  # oversize for camera moves
BG = {}
ASSETS = os.environ.get('AIKA_ASSETS', 'assets')
for k in ('sun', 'rain', 'snow'):
    im = Image.open(f'{ASSETS}/bg_{k}.webp').convert('RGB').resize((W, H), Image.LANCZOS)
    BG[k] = np.asarray(im).astype(np.float32)
SC = W / 940.0
# window mask (where outdoor weather is visible)
wm = Image.new('L', (W, H), 0); d = ImageDraw.Draw(wm)
for box in [(168, 425, 528, 556), (668, 392, 818, 622), (12, 362, 82, 655)]:
    d.rectangle([box[0] * SC, box[1] * SC, box[2] * SC, box[3] * SC], fill=255)
WMASK = np.asarray(wm.filter(ImageFilter.GaussianBlur(3))).astype(np.float32)[..., None] / 255
# exclude seats/headrests from windshield (rough): seats at x 120-330 & 400-610 orig, y>455
sm = Image.new('L', (W, H), 255); d = ImageDraw.Draw(sm)
for box in [(122, 452, 322, 760), (398, 452, 608, 760), (300, 545, 430, 760), (305, 440, 420, 470)]:
    d.rounded_rectangle([box[0] * SC, box[1] * SC, box[2] * SC, box[3] * SC], radius=40, fill=0)
WMASK *= np.asarray(sm.filter(ImageFilter.GaussianBlur(4))).astype(np.float32)[..., None] / 255
# lantern glow
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
LX, LY = 836 * SC, 805 * SC
GLOW = np.exp(-((xx - LX) ** 2 + (yy - LY) ** 2) / (2 * 150 ** 2))[..., None] * np.array([255, 170, 80], np.float32)
GLOW2 = np.exp(-((xx - LX) ** 2 + (yy - LY) ** 2) / (2 * 420 ** 2))[..., None] * np.array([255, 160, 90], np.float32)
VIG = (1 - 0.35 * np.clip(((xx - W / 2) ** 2 / (W * 0.62) ** 2 + (yy - H / 2) ** 2 / (H * 0.62) ** 2) - 0.35, 0, 1))[..., None]
# sunlight beam (from right window toward floor)
beam = Image.new('L', (W, H), 0); d = ImageDraw.Draw(beam)
d.polygon([(700, 470), (820, 470), (560, 1500), (180, 1500)], fill=60)
BEAM = np.asarray(beam.filter(ImageFilter.GaussianBlur(60))).astype(np.float32)[..., None] / 255 * np.array([255, 235, 190], np.float32)
del xx, yy

# night variant built from the sunny background
_s = BG['sun']; _lum = _s.mean(2, keepdims=True)
_sky = np.clip((_s[..., 2:3] - _s[..., 0:1]) / 40 + (_lum - 150) / 60, 0, 1) * WMASK
_night = _s * np.array([0.30, 0.32, 0.45], np.float32)
_skycol = np.array([18, 26, 70], np.float32) + (_lum / 255) * np.array([30, 40, 80], np.float32)
BG['night'] = _night * (1 - WMASK) + (_skycol * (0.35 + 0.65 * _sky) + _s * 0.08 * (1 - _sky)) * WMASK
SKYMASK = _sky
_r2 = np.random.default_rng(11)
STARS = [(x, y, _r2.uniform(1.2, 3.2), _r2.uniform(0, 6.28)) for x, y in zip(_r2.uniform(0, W, 900), _r2.uniform(380, 860, 900))]
CEIL = None
GRADE = {'night': np.array([1.0, 1.0, 1.0]), 'sun': np.array([1.03, 1.0, 0.97]), 'rain': np.array([0.93, 0.97, 1.06]), 'snow': np.array([0.96, 0.98, 1.05])}

rng = np.random.default_rng(7)
RAIN = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(900, 1400), rng.uniform(25, 45)) for _ in range(260)]
SNOW = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(40, 110), rng.uniform(2.5, 6), rng.uniform(0, 6.28)) for _ in range(220)]
DUST = [(rng.uniform(0, W), rng.uniform(300, 1500), rng.uniform(8, 22), rng.uniform(2, 4.5), rng.uniform(0, 6.28)) for _ in range(40)]

def weather_layer(kind, t):
    lay = Image.new('L', (W, H), 0); d = ImageDraw.Draw(lay)
    if kind == 'rain':
        for x0, y0, v, ln in RAIN:
            y = (y0 + v * t) % (H + 100) - 50; x = (x0 - 0.18 * v * t) % W
            d.line([(x, y), (x + 0.18 * ln, y - ln)], fill=200, width=2)
    elif kind == 'night':
        for x, y, rr, ph in STARS:
            a = 0.55 + 0.45 * math.sin(t * 3 + ph * 5)
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=int(255 * a))
    elif kind == 'snow':
        for x0, y0, v, r, ph in SNOW:
            y = (y0 + v * t) % (H + 40) - 20; x = (x0 + 25 * math.sin(t * 0.9 + ph)) % W
            d.ellipse([x - r, y - r, x + r, y + r], fill=235)
    return np.asarray(lay).astype(np.float32)[..., None] / 255

def bg_frame(kind, t, ts):
    b = BG[kind].copy()
    if kind == 'night':
        wl = weather_layer(kind, t) * SKYMASK
        b = b * (1 - wl) + np.array([255, 250, 225], np.float32) * wl
    if kind in ('rain', 'snow'):
        wl = weather_layer(kind, t) * WMASK
        col = np.array([215, 225, 245], np.float32) if kind == 'rain' else np.array([255, 255, 255], np.float32)
        b = b * (1 - wl * 0.75) + col * wl * 0.75
    fl = 0.85 + 0.1 * math.sin(t * 7.3) + 0.05 * math.sin(t * 17.1)
    gi = {'sun': 0.25, 'rain': 0.55, 'snow': 0.6, 'night': 1.4}[kind]
    b = b + GLOW * (0.35 * gi * fl) + GLOW2 * (0.10 * gi * fl)
    if kind == 'sun':
        b = b + BEAM * (0.55 + 0.08 * math.sin(t * 1.3))
    if kind == 'night':
        b = b + CEILG * (0.55 * fl)
    b = b * GRADE[kind] * VIG
    return b
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
CEILG = np.exp(-((_xx - 446) ** 2 / (2 * 260 ** 2) + (_yy - 360) ** 2 / (2 * 330 ** 2)))[..., None] * np.array([255, 190, 120], np.float32) * 0.6
del _yy, _xx

# ---------------- sprites ----------------
K = dict(getattr(EP, 'K', {}))
SPRITE_DIR = getattr(EP, 'SPRITE_DIR', 'sprites')
HEAD_ANCHOR = getattr(EP, 'HEAD_ANCHOR', {'wave'})
SIT = getattr(EP, 'SIT', {'fork', 'spoon', 'chop'})
CHAIR = getattr(EP, 'CHAIR', 'chair')
SPR = {}
def load_sprite(name):
    if name in SPR: return SPR[name]
    sheet = name.rsplit('_', 1)[0]
    im = Image.open(f'{ASSETS}/{name}.webp').convert('RGBA')
    k = K[sheet]
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    if k > 2: im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    a = np.asarray(im)[..., 3] > 128
    hgt = a.shape[0]
    if sheet in HEAD_ANCHOR:
        ys, xs = np.nonzero(a[: int(hgt * 0.35)])
    else:
        ys, xs = np.nonzero(a[int(hgt * 0.86):])
    ax = xs.mean()
    SPR[name] = (im, ax, hgt)
    return SPR[name]

# lip sync envelopes
META = json.load(open(f'{VOICE_DIR}/meta.json'))
ENV = {}
for k in VO:
    w = wave.open(f'{VOICE_DIR}/{k}.wav'); sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16) / 32768
    hop = sr // FPS
    n = len(x) // hop
    ENV[k] = np.array([np.sqrt(np.mean(x[i * hop:(i + 1) * hop] ** 2)) for i in range(n)])

def mouth(t):
    for k, t0 in VO.items():
        i = int(round((t - t0) * FPS))
        e = ENV[k]
        if 0 <= i < len(e):
            # hysteresis-ish: open on loud, quick closures on gaps; slow down flapping
            v = e[i]
            if v > 0.055:
                return 1 if (i // 3) % 2 == 0 or v > 0.16 else 0
            return 0
    return 0
def speaking(t):
    for k, t0 in VO.items():
        m = META[k]
        if t0 + m['start'] - 0.05 <= t <= t0 + m['end'] + 0.05: return True
    return False

def cyc(frames, fps, t, t0=0):
    return frames[int((t - t0) * fps) % len(frames)]

if hasattr(EP, 'char_state'):
    char_state = lambda t: EP.char_state(t, mouth, cyc)

# pose change times (for squash pop)
POSE_T = []
_prev = None
for i in range(int(DUR * FPS)):
    t = i / FPS
    pk = char_state(t)[3]
    if pk != _prev: POSE_T.append(t); _prev = pk

def draw_char(canvas, t):
    n, dx, dy, pk, shake = char_state(t)
    im, ax, hgt = load_sprite(n)
    # breathing + pop squash
    br = math.sin(t * 2 * math.pi / 1.9)
    sy = 1 + 0.012 * br; sx = 1 - 0.006 * br
    last = max([p for p in POSE_T if p <= t] or [0])
    a = t - last
    sitting = n.split('_')[0] in SIT
    if a < 0.35 and last > 0.05:
        s = (0.015 if sitting else 0.06) * math.exp(-a * 12) * math.cos(a * 30)
        sy *= 1 - s; sx *= 1 + s * 0.7
    if speaking(t):
        sy *= 1 + 0.008 * math.sin(t * 13)
    if sitting: sy = 1 + (sy - 1) * 0.5
    if shake: dx += 9 * math.sin(t * 70)
    w2, h2 = max(1, round(im.width * sx)), max(1, round(im.height * sy))
    im2 = im.resize((w2, h2), Image.BILINEAR)
    x = round(CX + dx - ax * sx); y = round(FEET_Y + dy - h2)
    tn = EP.tint(t) if hasattr(EP, 'tint') else None
    if tn:
        target = canvas; canvas = Image.new('RGBA', target.size, (0, 0, 0, 0))
    if sitting:
        canvas.alpha_composite(PROP[CHAIR])
    # soft contact shadow
    if not sitting: canvas.alpha_composite(SHADOW, (round(CX + dx - SHADOW.width / 2), FEET_Y - SHADOW.height // 2 - 6))
    canvas.alpha_composite(im2, (x, y))
    if sitting:
        kind = EP.table_kind(t) if hasattr(EP, 'table_kind') else TABLES.get(n.split('_')[0])
        if kind: canvas.alpha_composite(PROP[PKEY(kind)])
        if kind and kind in STEAMX: steam(canvas, STEAMX[kind] - TSHIFT, 1120 if kind != 'pudding' else 1075, t)
    if tn:
        rgb = ImageChops.multiply(canvas.convert('RGB'), Image.new('RGB', canvas.size, tn))
        lay = rgb.convert('RGBA'); lay.putalpha(canvas.getchannel('A'))
        target.alpha_composite(lay)
    return n

TSHIFT = getattr(EP, 'TSHIFT', 28)
PKEY = lambda k: k if TSHIFT == 28 else f'{k}@{TSHIFT}'
import os, pickle
PROP = pickle.load(open('props_cache.pkl', 'rb')) if os.path.exists('props_cache.pkl') else {}
_chg = False
if CHAIR not in PROP: PROP[CHAIR] = getattr(props, CHAIR)(); _chg = True
for k in set(getattr(EP, 'FOODS', [v for v in TABLES.values() if v])):
    if PKEY(k) not in PROP:
        PROP[PKEY(k)] = props.table(k).crop((TSHIFT, 0, 1080 + TSHIFT, 1920)); _chg = True
if _chg: pickle.dump(PROP, open('props_cache.pkl', 'wb'))

SHADOW = Image.new('RGBA', (360, 70), (0, 0, 0, 0))
ImageDraw.Draw(SHADOW).ellipse([10, 10, 350, 60], fill=(60, 30, 20, 70))
SHADOW = SHADOW.filter(ImageFilter.GaussianBlur(10))

# ---------------- text ----------------
_TC = {}
def font(sz, f=FONT): return ImageFont.truetype(f, sz)
def text_img(txt, sz, fill='#ffffff', stroke='#ff6f91', sw=12, f=FONT, shadow=True, spacing=10):
    key = (txt, sz, fill, stroke, sw, f, shadow)
    if key in _TC: return _TC[key]
    fo = font(sz, f)
    dummy = ImageDraw.Draw(Image.new('RGBA', (10, 10)))
    bb = dummy.multiline_textbbox((0, 0), txt, font=fo, stroke_width=sw, align='center', spacing=spacing)
    w, h = int(bb[2] - bb[0] + 40), int(bb[3] - bb[1] + 40)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if shadow:
        sh = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).multiline_text((20 - bb[0] + 4, 20 - bb[1] + 7), txt, font=fo, fill=(90, 40, 50, 140), stroke_width=sw, stroke_fill=(90, 40, 50, 140), align='center', spacing=spacing)
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4)))
    d.multiline_text((20 - bb[0], 20 - bb[1]), txt, font=fo, fill=fill, stroke_width=sw, stroke_fill=stroke, align='center', spacing=spacing)
    _TC[key] = im
    return im

def paste_scaled(canvas, im, cx, cy, s=1.0, rot=0.0, alpha=1.0):
    if s <= 0.01 or alpha <= 0.01: return
    if abs(s - 1) > 0.005: im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.BILINEAR)
    if rot: im = im.rotate(rot, Image.BICUBIC, expand=True)
    if alpha < 0.999:
        im = im.copy(); a = im.getchannel('A').point(lambda v: int(v * alpha)); im.putalpha(a)
    canvas.alpha_composite(im, (round(cx - im.width / 2), round(cy - im.height / 2)))

def sub_img(k):
    key = ('SUB', k)
    if key in _TC: return _TC[key]
    txt = SUB[k]; fo = font(54, FONTB)
    d0 = ImageDraw.Draw(Image.new('RGBA', (10, 10)))
    bb = d0.multiline_textbbox((0, 0), txt, font=fo, align='center', spacing=14)
    tw, th = int(bb[2] - bb[0]), int(bb[3] - bb[1])
    w, h = max(tw + 90, 520), th + 64
    im = Image.new('RGBA', (w + 20, h + 26), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([10, 18, w + 10, h + 18], radius=44, fill=(120, 50, 70, 90))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([10, 8, w + 10, h + 8], radius=44, fill=(255, 255, 255, 240), outline=(255, 140, 170, 255), width=7)
    d.multiline_text((10 + (w - tw) / 2 - bb[0], 8 + (h - th) / 2 - bb[1]), txt, font=fo, fill=(92, 52, 58), align='center', spacing=14)
    _TC[key] = im
    return im

def chapter_img(num, txt):
    key = ('CH', num)
    if key in _TC: return _TC[key]
    fo = font(64); fn = font(60)
    d0 = ImageDraw.Draw(Image.new('RGBA', (10, 10)))
    bb = d0.textbbox((0, 0), txt, font=fo)
    tw = int(bb[2] - bb[0])
    w, h = tw + 170, 130
    im = Image.new('RGBA', (w + 30, h + 30), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([15, 22, w + 15, h + 22], radius=65, fill=(150, 60, 90, 110))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(7)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([15, 12, w + 15, h + 12], radius=65, fill=(255, 120, 160, 255), outline=(255, 255, 255, 255), width=7)
    d.ellipse([30, 25, 134, 129], fill=(255, 255, 255, 255))
    nb = d.textbbox((0, 0), num, font=fn)
    d.text((82 - (nb[0] + nb[2]) / 2, 77 - (nb[1] + nb[3]) / 2), num, font=fn, fill=(255, 100, 145))
    d.text((150 - bb[0], 77 - (bb[1] + bb[3]) / 2), txt, font=fo, fill=(255, 255, 255), stroke_width=4, stroke_fill=(230, 80, 125))
    _TC[key] = im
    return im

# ---------------- little drawings ----------------
def heart_img(sz, col=(255, 95, 140)):
    s = 4; im = Image.new('RGBA', (sz * s, sz * s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = []
    for i in range(100):
        a = i / 100 * 2 * math.pi
        x = 16 * math.sin(a) ** 3; y = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
        pts.append((sz * s / 2 + x * sz * s / 36, sz * s / 2 + y * sz * s / 36 - sz * s * 0.03))
    d.polygon(pts, fill=col + (255,), outline=(255, 255, 255, 255), width=s * 2)
    return im.resize((sz, sz), Image.LANCZOS)
def star_img(sz, col=(255, 230, 90)):
    s = 4; im = Image.new('RGBA', (sz * s, sz * s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = sz * s / 2; pts = []
    for i in range(10):
        r = c * (0.95 if i % 2 == 0 else 0.42); a = -math.pi / 2 + i * math.pi / 5
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    d.polygon(pts, fill=col + (255,), outline=(255, 255, 255, 255), width=s * 2)
    return im.resize((sz, sz), Image.LANCZOS)
HEART = heart_img(70); STAR = star_img(64); STAR_S = star_img(40, (255, 255, 255))

def steam(canvas, cx, cy, t):
    lay = Image.new('RGBA', (240, 260), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for j in range(3):
        ph = (t * 0.9 + j / 3) % 1
        x0 = 60 + j * 60
        pts = [(x0 + 14 * math.sin(ph * 8 + k * 0.7 + j), 230 - k * 18 - ph * 40) for k in range(10)]
        d.line(pts, fill=(255, 255, 255, int(200 * (1 - ph))), width=12, joint='curve')
    lay = lay.filter(ImageFilter.GaussianBlur(4))
    canvas.alpha_composite(lay, (round(cx - 120), round(cy - 260)))

# ---------------- title ----------------
TITLE = getattr(EP, 'TITLE', ('くるまのおうちの１日', '車中泊で', 'なにができる？'))
ENDC = getattr(EP, 'ENDC', ('車中泊って', 'さいこう！', 'フォローして いっしょに旅しよ♪'))
END_T = getattr(EP, 'END_T', 56.8)
def draw_title(canvas, t):
    if t >= TRANS[0]: return
    s = 1 + 0.025 * math.sin(t * 3)
    tag = text_img(TITLE[0], 50, '#ffffff', '#ff8fb1', 10)
    paste_scaled(canvas, tag, CX, 205 + 4 * math.sin(t * 2.5), 1)
    t1 = text_img(TITLE[1], 128, '#ffffff', '#ff5f8f', 18)
    t2 = text_img(TITLE[2], 128, '#fff36b', '#ff5f8f', 18)
    paste_scaled(canvas, t1, CX, 330, s, rot=2 * math.sin(t * 2))
    paste_scaled(canvas, t2, CX, 480, s, rot=-2 * math.sin(t * 2 + 1))

def draw_endcard(canvas, t):
    if t < END_T: return
    a = t - END_T
    t1 = text_img(ENDC[0], 120, '#ffffff', '#ff5f8f', 18)
    t2 = text_img(ENDC[1], 140 if len(ENDC[1]) <= 6 else 112, '#fff36b', '#ff5f8f', 20)
    paste_scaled(canvas, t1, CX, 300, ease_out_back(a / 0.45), rot=3 * math.sin(t * 3))
    paste_scaled(canvas, t2, CX, 460, ease_out_back((a - 0.15) / 0.45), rot=-3 * math.sin(t * 3))
    f = text_img(ENDC[2], 50, '#ffffff', '#ff7aa2', 10)
    paste_scaled(canvas, f, CX, 1810, ease_out_back((a - 0.5) / 0.4) * (1 + 0.04 * math.sin(t * 6)))

def draw_overlays(canvas, t):
    # chapter
    for s0, s1, bgk, ch in SCENES:
        if ch and s0 <= t < s1:
            a = t - (s0 + 0.35)
            if a > 0:
                im = chapter_img(*ch)
                paste_scaled(canvas, im, CX, 250 + 5 * math.sin(t * 2.4), ease_out_back(a / 0.4))
    draw_title(canvas, t); draw_endcard(canvas, t)
    # onomatopoeia
    for o0, o1, txt, x, y, col, sz in ONO:
        if o0 <= t < o1:
            a = t - o0; out = clamp((o1 - t) / 0.2)
            im = text_img(txt, sz, col, '#ffffff', 10)
            wob = 6 * math.sin(t * 9)
            paste_scaled(canvas, im, x + (8 * math.sin(t * 60) if 'あちち' in txt else 0), y - 20 * clamp(a / 0.4), ease_out_back(a / 0.3) * out, rot=wob)
    # particles
    for b0, x, y, kind, n in BURST:
        a = t - b0
        if 0 <= a < 1.6:
            r = random.Random(int(b0 * 100))
            for i in range(n):
                ang = r.uniform(0, 2 * math.pi); sp = r.uniform(250, 520)
                px = x + math.cos(ang) * sp * a * (1 - a / 3)
                py = y + math.sin(ang) * sp * a * (1 - a / 3) - (90 * a if kind == 'heart' else 0) + 160 * a * a * (kind == 'star')
                sc = (1 - a / 1.6) * r.uniform(0.6, 1.1)
                paste_scaled(canvas, HEART if kind == 'heart' else (STAR if i % 2 else STAR_S), px, py, sc, rot=a * 200 * (1 if i % 2 else -1))
    # subtitles
    for k, t0 in VO.items():
        m = META[k]
        s0, s1 = t0 + max(0, m['start'] - 0.1), t0 + m['end'] + 0.3
        first = t0 < 0.5
        if first: s0 = 0
        if s0 <= t < s1:
            a = t - s0
            paste_scaled(canvas, sub_img(k), CX, 1580, 1.0 if first else 0.9 + 0.1 * ease_out_back(a / 0.18))
    # sparkle dust in sunny scenes
    return

def dust(canvas, t):
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for x0, y0, v, r, ph in DUST:
        x = (x0 + v * t + 30 * math.sin(t * 0.7 + ph)) % W; y = y0 + 25 * math.sin(t * 0.5 + ph * 2)
        al = int(120 + 100 * math.sin(t * 2 + ph))
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 245, 200, max(0, al)))
    canvas.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1.5)))

def scene_at(t):
    for s in SCENES:
        if s[0] <= t < s[1]: return s
    return SCENES[-1]

# iris pattern
PAT = Image.new('RGB', (W, H), (255, 182, 200)); d = ImageDraw.Draw(PAT)
for yy_ in range(0, H, 90):
    for xx_ in range(0, W, 90):
        o = 45 if (yy_ // 90) % 2 else 0
        d.ellipse([xx_ + o - 12, yy_ - 12, xx_ + o + 12, yy_ + 12], fill=(255, 225, 235))
PAT = PAT.convert('RGBA')

def render(t):
    s0, s1, bgk, ch = scene_at(t)
    ts = t - s0
    R = sys.modules[__name__]
    if hasattr(EP, 'bg_mix'):
        k1, k2, al = EP.bg_mix(t)
        b = bg_frame(k1, t, ts) if al < 0.999 else 0
        if al > 0.001: b = b * (1 - al) + bg_frame(k2, t, ts) * al
        bgk = k2 if al > 0.5 else k1
    else:
        b = bg_frame(bgk, t, ts)
    base = Image.fromarray(np.clip(b, 0, 255).astype(np.uint8)).convert('RGBA')
    if bgk == 'sun': dust(base, t)
    if hasattr(EP, 'draw_back'): EP.draw_back(base, t, R)
    draw_char(base, t)
    if hasattr(EP, 'draw_front'): EP.draw_front(base, t, R)
    # camera: slow push-in per scene, with origin near character face
    z = 1.0 + 0.045 * clamp(ts / max(1, s1 - s0))
    if z > 1.001:
        cw, chh = W / z, H / z
        fx, fy = CX, 1000
        x0 = fx - cw * (fx / W); y0 = fy - chh * (fy / H)
        if hasattr(EP, 'cam_shake'):
            sx_, sy_ = EP.cam_shake(t); x0 += sx_; y0 += sy_
        base = base.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + chh))
    draw_overlays(base, t)
    if hasattr(EP, 'draw_top'): EP.draw_top(base, t, R)
    # transitions
    for T in TRANS:
        if T - TW <= t < T + TW:
            p = abs(t - T) / TW
            r = 1250 * (p ** 1.6)
            m = Image.new('L', (W, H), 0)
            ImageDraw.Draw(m).ellipse([CX - r, 880 - r, CX + r, 880 + r], fill=255)
            base = Image.composite(base, PAT, m)
    for T in FLASH:
        if T <= t < T + 0.3:
            a = 1 - (t - T) / 0.3
            base = Image.blend(base, Image.new('RGBA', (W, H), (255, 255, 255, 255)), a * 0.85)
    return base.convert('RGB')

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        for ts in sys.argv[2:]:
            render(float(ts)).save(f'out/still_{ts}.png')
    else:
        a, b, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                              '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
        for i in range(a, b):
            p.stdin.write(render(i / FPS).tobytes())
            if i % 60 == 0: print(i, flush=True)
        p.stdin.close(); p.wait()
