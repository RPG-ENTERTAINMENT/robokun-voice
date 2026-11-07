"""忍者しずく チャレンジショート：台本（JSON）から縦動画（1080x1920・30fps）を作る。
使い方: python3 engine/render.py episodes/ep001.json out.mp4
"""
import json, math, os, random, subprocess, sys, tempfile, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from bg import static_bg, Wall, WALL, W, H  # noqa
import audio  # noqa

FPS = 30
FONT_T = os.path.join(ROOT, 'assets', 'LuckiestGuy.ttf')
FONT_B = os.path.join(ROOT, 'assets', 'Poppins-Bold.ttf')
FONT_N = os.path.join(ROOT, 'assets', 'DejaVuSans-Bold.ttf')
SPR_IMG = os.path.join(ROOT, 'assets', 'sprites.webp')   # 使うポーズを1枚にまとめた画像（位置は sprites.json）
HD_DIR = os.path.join(ROOT, 'assets', 'sprites_hd')      # AIで4倍に高画質化したポーズ（engine/upscale.py が作る。無ければ普通の画像を使う）
BGM_FILES = [os.path.join(ROOT, 'assets', f) for f in ('bgm1.ogg', 'bgm2.ogg')]   # 和風BGM（話数ごとに交互）
URL = 'https://www.rpgtokyo.com/ninjabar/'
FEET = 1480
PINK, CYAN, GOLD = (255, 61, 139), (56, 217, 255), (255, 200, 70)
FXCOL = {'fire': [(255, 220, 90), (255, 120, 30), (255, 50, 30)],
         'ice': [(220, 250, 255), (90, 210, 255), (40, 120, 255)],
         'thunder': [(255, 255, 210), (255, 235, 80), (180, 140, 255)],
         'love': [(255, 200, 230), (255, 90, 170), (255, 40, 120)],
         'magic': [(255, 255, 255), (190, 120, 255), (90, 200, 255)],
         'smoke': [(120, 110, 140), (90, 80, 110), (150, 140, 170)]}


def font(path, size, cache={}):
    k = (path, size)
    if k not in cache:
        cache[k] = ImageFont.truetype(path, size)
    return cache[k]


_sprites = {}


def sprite(name, scale):
    k = (name, round(scale, 3))
    if k not in _sprites:
        hd = os.path.join(HD_DIR, name + '.png')
        if os.path.exists(hd):
            im, f = Image.open(hd).convert('RGBA'), scale / 4
        else:
            if 'atlas' not in _sprites:
                _sprites['atlas'] = (Image.open(SPR_IMG).convert('RGBA'), json.load(open(SPR_IMG.replace('.webp', '.json'))))
            at, pos = _sprites['atlas']
            x, y, w, h = pos[name]
            im, f = at.crop((x, y, x + w, y + h)), scale
        _sprites[k] = im.resize((max(1, int(im.width * f)), max(1, int(im.height * f))), Image.LANCZOS)
    return _sprites[k]


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def back_out(x):
    x = max(0.0, min(1.0, x))
    c = 1.7
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


# ---------- 文字 ----------
def outlined(d, xy, text, f, fill, stroke=(20, 10, 40), sw=8, anchor='mm'):
    d.text(xy, text, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke, anchor=anchor)


def wrap(text, f, maxw, d):
    words, lines, cur = text.split(), [], ''
    for w_ in words:
        t = (cur + ' ' + w_).strip()
        if d.textlength(t, font=f) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def draw_caption(img, text, k, cy=800):
    """下の字幕（白い角丸＋ピンク枠）。k=出現の進み具合"""
    if not text or k <= 0:
        return
    d = ImageDraw.Draw(img)
    f = font(FONT_B, 50)
    lines = []
    for part in text.split('\n'):
        lines += wrap(part, f, 860, d)
    lh = 64
    bh = lh * len(lines) + 44
    bw = max(d.textlength(l, font=f) for l in lines) + 80
    s = back_out(k)
    cx = W / 2
    layer = Image.new('RGBA', (int(bw) + 20, int(bh) + 20), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle((10, 10, bw + 10, bh + 10), 34, fill=(255, 255, 255, 245), outline=PINK + (255,), width=7)
    for i, l in enumerate(lines):
        ld.text(((bw + 20) / 2, 10 + 22 + lh * i + lh / 2), l, font=f, fill=(30, 20, 60), anchor='mm')
    if s != 1:
        layer = layer.resize((max(1, int(layer.width * s)), max(1, int(layer.height * s))), Image.BICUBIC)
    img.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))


def draw_big(img, text, k, col, y=600, size=150):
    if not text or k <= 0:
        return
    s = back_out(min(1, k * 1.6)) * (1 + 0.04 * math.sin(k * 20))
    f = font(FONT_T, int(size * max(0.05, s)))
    d = ImageDraw.Draw(img)
    outlined(d, (W / 2 + 6, y + 8), text, f, (20, 10, 40), sw=14)
    outlined(d, (W / 2, y), text, f, col, sw=14)


# ---------- 効果 ----------
class Particles:
    def __init__(self):
        self.p = []

    def burst(self, x, y, kind, n=90, speed=26, life=1.0, grav=0.0, size=(10, 26)):
        cols = FXCOL.get(kind, FXCOL['magic'])
        for _ in range(n):
            a = random.random() * 6.283
            v = speed * (0.3 + random.random())
            self.p.append([x, y, math.cos(a) * v, math.sin(a) * v, life * (0.5 + random.random() * 0.7), 0, random.choice(cols), random.uniform(*size), grav])

    def confetti(self, n=120):
        for _ in range(n):
            self.p.append([random.uniform(0, W), random.uniform(-300, 0), random.uniform(-4, 4), random.uniform(6, 14), 3.0, 0,
                           random.choice([PINK, CYAN, GOLD, (140, 255, 120), (190, 120, 255)]), random.uniform(14, 24), 0.25, 'c', random.random() * 6])

    def trail(self, x, y, kind, n=4):
        cols = FXCOL.get(kind, FXCOL['magic'])
        for _ in range(n):
            self.p.append([x + random.uniform(-10, 10), y + random.uniform(-10, 10), random.uniform(-3, 3), random.uniform(-3, 3), 0.45, 0, random.choice(cols), random.uniform(10, 22), -0.2])

    def note(self, x, y):
        self.p.append([x, y, random.uniform(-1.5, 1.5), -4, 1.4, 0, random.choice([PINK, CYAN, GOLD, (190, 120, 255)]), 60, 0, 'n', random.choice('♪♫')])

    def swirl(self, cx, cy, kind, t):
        cols = FXCOL.get(kind, FXCOL['magic'])
        for i in range(3):
            a = t * 7 + i * 2.094
            r = 270 + 30 * math.sin(t * 5 + i)
            self.p.append([cx + math.cos(a) * r, cy + math.sin(a) * r * 0.55, -math.sin(a) * 6, math.cos(a) * 3, 0.5, 0, random.choice(cols), random.uniform(12, 24), -0.4])

    def step_draw(self, img):
        if not self.p:
            return
        glow = Image.new('RGB', (W // 2, H // 2), 0)
        gd = ImageDraw.Draw(glow)
        core = ImageDraw.Draw(img)
        alive = []
        for q in self.p:
            q[0] += q[2]; q[1] += q[3]; q[3] += q[8]; q[2] *= 0.96
            if len(q) <= 9:
                q[3] *= 0.96
            q[5] += 1 / FPS
            if q[5] >= q[4]:
                continue
            alive.append(q)
            k = 1 - q[5] / q[4]
            r = q[7] * (0.4 + 0.6 * k)
            if len(q) > 9 and q[9] == 'n':  # 音符
                core.text((q[0], q[1]), q[10], font=font(FONT_N, int(q[7])), fill=q[6] + (int(255 * min(1, k * 2)),), anchor='mm', stroke_width=3, stroke_fill=(20, 10, 40))
                continue
            if len(q) > 9:  # 紙吹雪
                q[10] += 0.2
                w_, h_ = r, r * 0.5 * abs(math.sin(q[10]))
                core.rectangle((q[0] - w_ / 2, q[1] - h_ / 2 - 2, q[0] + w_ / 2, q[1] + h_ / 2 + 2), fill=q[6] + (255,))
                continue
            gx, gy, gr = q[0] / 2, q[1] / 2, r
            gd.ellipse((gx - gr, gy - gr, gx + gr, gy + gr), fill=tuple(int(c * k) for c in q[6]))
            cr = r * 0.35
            core.ellipse((q[0] - cr, q[1] - cr, q[0] + cr, q[1] + cr), fill=(255, 255, 255, int(255 * k)))
        self.p = alive
        g = glow.filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BILINEAR)
        a = np.array(img, np.int32)
        a[..., :3] = np.minimum(255, a[..., :3] + np.array(g, np.int32) * 2)
        img.paste(Image.fromarray(a.astype(np.uint8)))


def shuriken(img, x, y, ang, size=46, glowcol=None):
    pts = []
    for i in range(8):
        r = size if i % 2 == 0 else size * 0.32
        a = ang + i * math.pi / 4
        pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
    d = ImageDraw.Draw(img)
    d.polygon(pts, fill=(70, 80, 100), outline=(235, 240, 255))
    d.ellipse((x - 8, y - 8, x + 8, y + 8), fill=(20, 20, 30), outline=(200, 210, 230))


def target(img, x, y, t, hit=False, scale=1.0):
    d = ImageDraw.Draw(img)
    p = 1 + 0.05 * math.sin(t * 6)
    for i, (r, c) in enumerate([(110, (255, 255, 255)), (88, (255, 61, 90)), (64, (255, 255, 255)), (40, (255, 61, 90)), (16, (255, 230, 80))]):
        rr = r * p * scale
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=c + (255,), outline=(40, 20, 60), width=4)
    if hit:
        d.line((x - 30, y - 30, x + 30, y + 30), fill=(40, 20, 60), width=10)


def lightning(img, x0, y0, x1, y1, seed):
    rnd = random.Random(seed)
    pts = [(x0, y0)]
    n = 10
    for i in range(1, n):
        f = i / n
        pts.append((x0 + (x1 - x0) * f + rnd.uniform(-60, 60), y0 + (y1 - y0) * f))
    pts.append((x1, y1))
    layer = Image.new('RGB', (W, H), 0)
    ld = ImageDraw.Draw(layer)
    ld.line(pts, fill=(200, 180, 255), width=26)
    layer = layer.filter(ImageFilter.GaussianBlur(14))
    a = np.array(img, np.int32)
    a[..., :3] = np.minimum(255, a[..., :3] + np.array(layer, np.int32))
    img.paste(Image.fromarray(a.astype(np.uint8)))
    ImageDraw.Draw(img).line(pts, fill=(255, 255, 240), width=8)


FRUIT_JUICE = {'watermelon': 'love', 'apple': 'fire', 'orange': 'fire', 'grape': 'magic'}
_fr = {}


def _fruit_img(kind):
    if kind in _fr:
        return _fr[kind]
    S = 170
    im = Image.new('RGBA', (S, S), 0)
    d = ImageDraw.Draw(im)
    if kind == 'watermelon':
        d.ellipse((5, 5, S - 5, S - 5), fill=(40, 160, 60), outline=(20, 60, 25), width=6)
        for k in range(-3, 4):
            d.arc((S / 2 - 30 + k * 22, 5, S / 2 + 30 + k * 22, S - 5), 250, 290, fill=(20, 90, 35), width=10)
    elif kind == 'apple':
        d.ellipse((10, 20, S - 10, S - 5), fill=(220, 40, 50), outline=(110, 15, 20), width=6)
        d.line((S / 2, 25, S / 2 + 6, 0), fill=(90, 50, 20), width=8)
        d.ellipse((S / 2 + 6, 2, S / 2 + 46, 26), fill=(60, 170, 60))
        d.ellipse((40, 45, 70, 80), fill=(255, 140, 150))
    elif kind == 'orange':
        d.ellipse((8, 8, S - 8, S - 8), fill=(255, 150, 20), outline=(150, 70, 0), width=6)
        for _ in range(30):
            x, y = random.uniform(30, S - 30), random.uniform(30, S - 30)
            d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(230, 120, 10))
        d.ellipse((S / 2 - 10, 6, S / 2 + 10, 20), fill=(60, 140, 50))
    else:
        for (x, y) in [(60, 40), (100, 40), (40, 75), (80, 75), (120, 75), (60, 110), (100, 110), (80, 140)]:
            d.ellipse((x - 24, y - 24, x + 24, y + 24), fill=(140, 60, 190), outline=(70, 20, 100), width=4)
    _fr[kind] = im
    return im


def fruit(img, x, y, kind, half=0, ang=0):
    im = _fruit_img(kind)
    if half:
        w = im.width // 2
        im = im.crop((0, 0, w, im.height)) if half < 0 else im.crop((w, 0, im.width, im.height))
    im = im.rotate(ang, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(im, (int(x - im.width / 2), int(y - im.height / 2)))


def slash(img, k):
    layer = Image.new('RGBA', (W, H), 0)
    d = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = 60, 1150, 1020, 560
    xm = x0 + (x1 - x0) * min(1, k * 1.5)
    ym = y0 + (y1 - y0) * min(1, k * 1.5)
    d.line((x0, y0, xm, ym), fill=(200, 240, 255, 230), width=34)
    layer = layer.filter(ImageFilter.GaussianBlur(8))
    img.alpha_composite(layer)
    ImageDraw.Draw(img).line((x0, y0, xm, ym), fill=(255, 255, 255, 255), width=10)


def onigiri(img, x, y, ang):
    S = 150
    im = Image.new('RGBA', (S, S), 0)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((10, 10, S - 10, S - 10), 30, fill=0)
    d.polygon([(S / 2, 8), (S - 8, S - 14), (8, S - 14)], fill=(255, 255, 250), outline=(80, 70, 70))
    d.line([(S / 2, 8), (S - 8, S - 14), (8, S - 14), (S / 2, 8)], fill=(80, 70, 70), width=6, joint='curve')
    d.rectangle((S / 2 - 30, S - 62, S / 2 + 30, S - 16), fill=(25, 40, 30))
    im = im.rotate(ang, resample=Image.BICUBIC)
    img.alpha_composite(im, (int(x - S / 2), int(y - S / 2)))


def tophat(img, x, y):
    d = ImageDraw.Draw(img)
    d.ellipse((x - 120, y - 30, x + 120, y + 18), fill=(25, 20, 40), outline=(90, 80, 120), width=4)
    d.rectangle((x - 80, y - 190, x + 80, y - 5), fill=(30, 24, 50), outline=(90, 80, 120), width=4)
    d.rectangle((x - 80, y - 60, x + 80, y - 30), fill=(200, 30, 50))
    d.ellipse((x - 80, y - 210, x + 80, y - 170), fill=(15, 10, 25), outline=(90, 80, 120), width=4)


def meter(img, v, label):
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 240, 330, 840, 730
    d.rounded_rectangle((x0, y0, x1, y1), 34, fill=(10, 5, 30), outline=GOLD, width=8)
    d.text((W / 2, y0 + 70), label, font=font(FONT_T, 70), fill=CYAN, anchor='mm')
    col = (255, 61, 139) if v < 80 else GOLD if v < 100 else (120, 255, 140)
    d.text((W / 2, y0 + 220), str(int(round(v))), font=font(FONT_T, 190), fill=col, anchor='mm', stroke_width=8, stroke_fill=(20, 10, 40))
    d.rounded_rectangle((x0 + 50, y1 - 90, x1 - 50, y1 - 50), 20, fill=(40, 30, 70))
    fw = (x1 - x0 - 100) * max(0, min(1, v / 100))
    if fw > 10:
        d.rounded_rectangle((x0 + 50, y1 - 90, x0 + 50 + fw, y1 - 50), 20, fill=col)


# ---------- 本物のお店の映像・写真（assets/real.mp4, poster.webp, logo.webp） ----------
REAL = os.path.join(ROOT, 'assets', 'real.mp4')
POSTER = os.path.join(ROOT, 'assets', 'poster.webp')
LOGO = os.path.join(ROOT, 'assets', 'logo.webp')
CLIP_CAP = ["This is the REAL\nNINJA DIGITAL BAR!", "Real ninja jutsu\nwith digital art!", "YOUR moves make\nfire, water & thunder!"]
PHOTO_CAP = ["Ninja cocktails &\nninja cosplay!", "Come visit us\nin Tokyo!", "Be a ninja for\none night!"]


def add_promo(ep):
    """終わりの画面の前に、本物のお店の映像（約4秒）とポスター（約2.6秒）を入れる。素材が無いときは何もしない"""
    if not ep.get('promo', True) or not (os.path.exists(REAL) and os.path.exists(POSTER)):
        return
    r = random.Random(ep.get('seed', 1) * 31)
    sc = ep['scenes']
    i = next((j for j, x in enumerate(sc) if x.get('end')), len(sc))
    sc[i:i] = [{"dur": 4.0, "clip": True, "cap": r.choice(CLIP_CAP), "target": False, "sfx": [[0.0, "whoosh"], [0.3, "sparkle"]]},
               {"dur": 2.6, "photo": True, "cap": r.choice(PHOTO_CAP), "target": False, "sfx": [[0.0, "pop"], [0.4, "sparkle"]]}]


class ClipReader:
    def __init__(self, path):
        self.p = subprocess.Popen(['ffmpeg', '-loglevel', 'quiet', '-i', path, '-vf', f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}',
                                   '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
        self.last = Image.new('RGB', (W, H))

    def frame(self):
        b = self.p.stdout.read(W * H * 3)
        if len(b) == W * H * 3:
            self.last = Image.frombytes('RGB', (W, H), b)
        return self.last.convert('RGBA')


def poster_base():
    im = Image.open(POSTER).convert('RGB')
    s = max(W / im.width, H / im.height)
    back = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.BILINEAR).crop((0, 0, W, H)).filter(ImageFilter.GaussianBlur(30))
    back = Image.eval(back, lambda v: int(v * 0.45)).convert('RGBA')
    fw = W - 60
    fg = im.resize((fw, int(im.height * fw / im.width)), Image.LANCZOS).convert('RGBA')
    return back, fg


def logo_img(size):
    return Image.open(LOGO).convert('RGBA').resize((size, size), Image.LANCZOS) if os.path.exists(LOGO) else None


def music_mix(total, events, path, music):
    """用意したBGM（和風）に効果音を重ねて wav にする"""
    SR = audio.SR
    raw = subprocess.run(['ffmpeg', '-loglevel', 'quiet', '-i', music, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True).stdout
    m = np.frombuffer(raw, np.float32).astype(np.float64)
    n = int(total * SR) + 1
    if len(m) < SR:
        return False
    if len(m) < n:
        m = np.tile(m, n // len(m) + 1)
    out = m[:n] * 0.55
    fo = int(1.5 * SR)
    out[-fo:] *= np.linspace(1, 0, fo)
    out[:int(0.03 * SR)] *= np.linspace(0, 1, int(0.03 * SR))
    for at, name in events:
        s_ = audio.sfx(name) * 0.85
        st = int(at * SR)
        if st >= n:
            continue
        e = min(n, st + len(s_))
        out[st:e] += s_[:e - st]
    out = np.tanh(out * 1.05) * 0.92
    data = (out * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(np.stack([data, data], 1).tobytes())
    return True


def qr_image(url, size):
    import qrcode
    q = qrcode.QRCode(border=2, box_size=10, error_correction=qrcode.constants.ERROR_CORRECT_M)
    q.add_data(url)
    q.make(fit=True)
    return q.make_image(fill_color='black', back_color='white').convert('RGBA').resize((size, size), Image.NEAREST)


# ---------- 本体 ----------
def render(ep, out):
    random.seed(ep.get('seed', 1))
    add_promo(ep)
    bg = static_bg(FONT_T).convert('RGBA')
    clip, pbase, logo_s, logo_b = None, None, logo_img(230), logo_img(330)
    wall = Wall()
    btx, bty = ep.get('target', [760, 560])
    mv = ep.get('target_move', 0)
    scenes = ep['scenes']
    starts, t0 = [], 0.0
    for s in scenes:
        starts.append(t0)
        t0 += s['dur']
    total = t0
    nframes = int(round(total * FPS))
    P = Particles()
    sfx = []
    tmp = tempfile.mkdtemp()
    proc = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                             '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', os.path.join(tmp, 'v.mp4')], stdin=subprocess.PIPE)
    qr = qr_image(ep.get('url', URL), 330)
    done = set()
    shake = 0.0
    flash = 0.0
    hit_state = False
    for fi in range(nframes):
        t = fi / FPS
        tx, ty = btx + mv * math.sin(t * 2.2), bty
        si = max(i for i, st in enumerate(starts) if st <= t + 1e-9)
        s = scenes[si]
        lt = t - starts[si]
        k = lt / s['dur']
        # 効果音（場面の頭に一度だけ登録）
        if si not in done:
            done.add(si)
            for at, name in s.get('sfx', []):
                sfx.append((starts[si] + at, name))
            if s.get('reset_hit'):
                hit_state = False
        media = s.get('clip') or s.get('photo')
        if s.get('clip'):
            if clip is None:
                clip = ClipReader(REAL)
            img = clip.frame()
        elif s.get('photo'):
            if pbase is None:
                pbase = poster_base()
            img = pbase[0].copy()
            z = 1 + 0.06 * ease(k)
            fg = pbase[1].resize((int(pbase[1].width * z), int(pbase[1].height * z)), Image.BILINEAR)
            img.alpha_composite(fg, (int(W / 2 - fg.width / 2), int(H / 2 + 20 - fg.height / 2)))
        else:
            img = bg.copy()
            wl = wall.frame(t, boost=s.get('wall_boost', 0.0) + flash * 0.8, tint=s.get('tint'))
            img.paste(wl, (WALL[0], WALL[1]))
        if media and logo_s is not None:
            img.alpha_composite(logo_s, (W - logo_s.width - 30, 40))
        # 的
        if not media and s.get('target', ep.get('show_target', True)) and s.get('end') is None:
            target(img, tx, ty, t, hit=hit_state)
        # キャラクター
        pose = s.get('pose', 'stand1')
        if pose in ('run', 'walk'):
            pose = f"{pose}{int(t * 10) % 4 + 1}"
        if pose == 'blink':
            pose = 'stand2' if (t % 2.6) < 0.15 else 'stand1'
        sc = s.get('scale', 2.4)
        cx = s.get('x', 540)
        if isinstance(cx, list):
            cx = cx[0] + (cx[1] - cx[0]) * ease(k)
        mot = s.get('motion', 'bob')
        dy, ang, sx = 0.0, 0.0, 1.0
        if mot == 'bob':
            dy = -abs(math.sin(t * 5)) * 14
        elif mot == 'jump':
            dy = -math.sin(min(1, k * 1.4) * math.pi) * 180
        elif mot == 'shake':
            cx += math.sin(t * 60) * 10
        elif mot == 'pop':
            sx = back_out(min(1, lt * 4))
        elif mot == 'bounce':
            dy = -abs(math.sin(t * 9)) * 40
        spr = sprite(pose, sc * sx)
        if s.get('flip'):
            spr = spr.transpose(Image.FLIP_LEFT_RIGHT)
        # 足元の影
        sh = Image.new('RGBA', (W, H), 0)
        ImageDraw.Draw(sh).ellipse((cx - 170, FEET - 26, cx + 170, FEET + 26), fill=(0, 0, 0, 110))
        if not s.get('end') and not media:
            img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
            img.alpha_composite(spr, (int(cx - spr.width / 2), int(FEET - spr.height + dy)))
        # 効果
        for fx in s.get('fx', []):
            at, dur = fx.get('at', 0), fx.get('dur', 0.6)
            p = (lt - at) / dur if dur else 0
            typ = fx['type']
            kind = fx.get('kind', 'magic')
            if typ == 'throw' and 0 <= p <= 1.4:
                hx, hy = cx + 120, FEET - 430
                if fx.get('result') == 'hit':
                    ex, ey = tx, ty
                else:
                    ex, ey = tx + fx.get('miss_dx', 260), ty + fx.get('miss_dy', -160)
                pp = min(1, p)
                x = hx + (ex - hx) * pp
                y = hy + (ey - hy) * pp - math.sin(pp * math.pi) * 160
                if p > 1 and fx.get('result') != 'hit':
                    x += (p - 1) * 300; y += (p - 1) ** 2 * 1400
                if not (fx.get('result') == 'hit' and p > 1):
                    if kind != 'none':
                        P.trail(x, y, kind, 3)
                    shuriken(img, x, y, t * 25)
                if fx.get('result') == 'hit' and p >= 1 and ('hit', si, id(fx)) not in done:
                    done.add(('hit', si, id(fx)))
                    hit_state = True
                    P.burst(tx, ty, kind, 160, 34, 1.2)
                    flash = 1.0
                    shake = 1.0
            elif typ == 'swirl' and 0 <= p <= 1:
                P.swirl(cx, FEET - 140, kind, t)
            elif typ == 'burst' and p >= 0 and ('b', si, id(fx)) not in done:
                done.add(('b', si, id(fx)))
                bx, by = fx.get('xy', [cx, FEET - 300])
                P.burst(bx, by, kind, fx.get('n', 120), fx.get('speed', 28), fx.get('life', 1.0))
                if fx.get('flash'):
                    flash = 1.0
                if fx.get('shake'):
                    shake = 1.0
            elif typ == 'confetti' and p >= 0 and ('c', si, id(fx)) not in done:
                done.add(('c', si, id(fx)))
                P.confetti(fx.get('n', 140))
            elif typ == 'sparkle' and 0 <= p <= 1 and fi % 3 == 0:
                P.burst(cx + random.uniform(-260, 260), FEET - random.uniform(150, 650), kind, 6, 6, 0.6)
            elif typ == 'fruits':
                for j, it in enumerate(fx['items']):
                    q = (lt - it['t0']) / it.get('fly', 1.3)
                    if q < 0 or q > 1.6:
                        continue
                    x = it['x0'] + (it['x1'] - it['x0']) * q
                    y = FEET - 150 - (FEET - 150 - it['peak']) * (1 - (2 * q - 1) ** 2)
                    sl = fx.get('slash_at')
                    cut = sl is not None and lt >= sl and j not in fx.get('miss', [])
                    if cut:
                        q0 = (sl - it['t0']) / it.get('fly', 1.3)
                        x0 = it['x0'] + (it['x1'] - it['x0']) * q0
                        y0 = FEET - 150 - (FEET - 150 - it['peak']) * (1 - (2 * q0 - 1) ** 2)
                        dt = lt - sl
                        if ('cut', si, id(fx), j) not in done:
                            done.add(('cut', si, id(fx), j))
                            P.burst(x0, y0, FRUIT_JUICE.get(it['kind'], 'fire'), 40, 18, 0.7)
                        for side in (-1, 1):
                            hx = x0 + side * (40 + dt * 320)
                            hy = y0 + dt * dt * 1800 - dt * 200
                            fruit(img, hx, hy, it['kind'], half=side, ang=side * dt * 200)
                    else:
                        fruit(img, x, y, it['kind'], ang=lt * 120)
                sl = fx.get('slash_at')
                if sl is not None and 0 <= lt - sl < 0.18:
                    slash(img, (lt - sl) / 0.18)
            elif typ == 'drop':
                it = fx
                q = (lt - it.get('at', 0)) / it.get('fall', 0.9)
                if q >= 0:
                    hy = FEET - 470
                    if it.get('caught') and q >= 1:
                        if ('cg', si, id(fx)) not in done:
                            done.add(('cg', si, id(fx)))
                            P.burst(it['x'], hy, 'magic', 30, 12, 0.6)
                    elif q < 1:
                        onigiri(img, it['x'], 230 + (hy - 230) * q * q, lt * 200)
                    else:
                        yy = min(FEET - 40, hy + (q - 1) * 900)
                        onigiri(img, it['x'] + (q - 1) * 60, yy, 0)
                        if yy >= FEET - 40 and ('sp', si, id(fx)) not in done:
                            done.add(('sp', si, id(fx)))
                            P.burst(it['x'], FEET - 40, 'magic', 20, 10, 0.5)
            elif typ == 'meter':
                q = ease((lt - at) / dur) if lt >= at else 0
                meter(img, fx.get('from', 0) + (fx['to'] - fx.get('from', 0)) * q, fx.get('label', 'SCORE'))
            elif typ == 'notes' and 0 <= p <= 1 and fi % 4 == 0:
                P.note(cx + random.uniform(-160, 160), FEET - random.uniform(380, 560))
            elif typ == 'hat':
                tophat(img, fx.get('x', 790), 1215)
                if 0 <= p <= 1 and fi % 2 == 0:
                    P.burst(fx.get('x', 790), 1100, 'smoke', 6, 8, 0.8, grav=-0.3)
                if fx.get('pop') and p >= 1 and ('hp', si, id(fx)) not in done:
                    done.add(('hp', si, id(fx)))
                    P.burst(fx.get('x', 790), 1080, fx.get('kind', 'love'), 140, 30, 1.3, grav=0.5)
                    P.confetti(60)
            elif typ == 'lightning' and 0 <= p <= 1:
                if fi % 2 == 0:
                    lightning(img, fx.get('x0', tx), WALL[1], fx.get('x1', tx), fx.get('y1', ty), fi)
        P.step_draw(img)
        # 終わりの画面（QR）
        if s.get('end'):
            ke = ease(lt / 0.5)
            panel = Image.new('RGBA', (W, H), (8, 4, 20, int(200 * ke)))
            img.alpha_composite(panel)
            d = ImageDraw.Draw(img)
            e = s['end']
            outlined(d, (W / 2, 330), e.get('l1', 'PLAY NINJA GAMES'), font(FONT_T, 92), (255, 255, 255), sw=10)
            outlined(d, (W / 2, 440), e.get('l2', 'WITH ME!'), font(FONT_T, 92), PINK, sw=10)
            outlined(d, (W / 2, 560), 'NINJA DIGITAL BAR', font(FONT_T, 74), CYAN, sw=8)
            d.text((W / 2, 640), e.get('l3', '15 min from Shinjuku & Shibuya'), font=font(FONT_B, 44), fill=(255, 255, 255), anchor='mm')
            box = Image.new('RGBA', (400, 400), (255, 255, 255, 255))
            ImageDraw.Draw(box).rounded_rectangle((0, 0, 399, 399), 30, outline=PINK, width=10)
            box.alpha_composite(qr, (35, 35))
            qs = back_out(min(1, max(0, lt - 0.2) * 2.5))
            if qs > 0.02:
                b2 = box.resize((int(400 * qs), int(400 * qs)), Image.BICUBIC)
                img.alpha_composite(b2, (int(W / 2 - b2.width / 2), int(910 - b2.height / 2)))
            d.text((W / 2, 1150), 'Scan to visit our website', font=font(FONT_B, 40), fill=(255, 230, 120), anchor='mm')
            d.text((W / 2, 1210), 'rpgtokyo.com/ninjabar', font=font(FONT_B, 46), fill=(255, 255, 255), anchor='mm')
            outlined(d, (W / 2, 1300), e.get('l4', 'NEW CHALLENGE EVERY DAY!'), font(FONT_T, 60), GOLD, sw=8)
            if logo_b is not None:
                img.alpha_composite(logo_b, (W - logo_b.width - 20, 1560 - logo_b.height // 2))
            spr2 = sprite(e.get('pose', 'wave'), 2.0)
            img.alpha_composite(spr2, (int(W / 2 - spr2.width / 2), int(1860 - spr2.height - abs(math.sin(t * 5)) * 12)))
        if s.get('hud'):
            d = ImageDraw.Draw(img)
            f = font(FONT_T, 64)
            tw_ = d.textlength(s['hud'], font=f)
            d.rounded_rectangle((W / 2 - tw_ / 2 - 30, 238, W / 2 + tw_ / 2 + 30, 318), 26, fill=(10, 5, 30), outline=CYAN, width=5)
            d.text((W / 2, 280), s['hud'], font=f, fill=(255, 255, 255), anchor='mm')
        # 字幕・大きい文字
        draw_caption(img, s.get('cap'), min(1, lt * 4), 1690 if media else 800)
        if s.get('big'):
            draw_big(img, s['big'], min(1, max(0, lt - s.get('big_at', 0)) * 2.2) if lt >= s.get('big_at', 0) else 0,
                     tuple(s.get('big_col', GOLD)), min(s.get('big_y', 640), 820), s.get('big_size', 150))
        # タイトル（1コマ目から完成した絵）
        if s.get('title'):
            tt = s['title']
            d = ImageDraw.Draw(img)
            band = Image.new('RGBA', (W, 520), (0, 0, 0, 0))
            bd = ImageDraw.Draw(band)
            bd.rounded_rectangle((40, 30, W - 40, 500), 40, fill=(10, 5, 30, 225), outline=GOLD + (255,), width=8)
            img.alpha_composite(band, (0, 250))
            outlined(d, (W / 2, 350), 'NINJA SHIZUKU', font(FONT_T, 76), CYAN, sw=8)
            outlined(d, (W / 2, 460), tt.get('no', 'CHALLENGE #1'), font(FONT_T, 110), (255, 255, 255), sw=10)
            for i, line in enumerate(tt.get('q', '').split('\n')):
                outlined(d, (W / 2, 590 + i * 92), line, font(FONT_T, 84 if len(line) < 18 else 70), GOLD, sw=9)
        # 画面の揺れ・フラッシュ
        if shake > 0.02:
            ox, oy = int(random.uniform(-1, 1) * 26 * shake), int(random.uniform(-1, 1) * 26 * shake)
            img2 = Image.new('RGBA', (W, H), (0, 0, 0, 255))
            img2.paste(img, (ox, oy))
            img = img2
            shake *= 0.85
        if flash > 0.02:
            a = np.array(img, np.float32)
            a[..., :3] = a[..., :3] + (255 - a[..., :3]) * flash * 0.55
            img = Image.fromarray(a.astype(np.uint8))
            flash *= 0.8
        proc.stdin.write(img.convert('RGB').tobytes())
    proc.stdin.close()
    proc.wait()
    wav = os.path.join(tmp, 'a.wav')
    bgms = [b for b in BGM_FILES if os.path.exists(b)]
    if not (bgms and music_mix(total, sfx, wav, bgms[(ep.get('no', ep.get('seed', 1)) - 1) % len(bgms)])):
        audio.mix(total, sfx, wav, seed=ep.get('seed', 1), bgm=ep.get('bgm', 'cute'))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', os.path.join(tmp, 'v.mp4'), '-i', wav, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', out], check=True)
    return total


if __name__ == '__main__':
    ep = json.load(open(sys.argv[1]))
    print('seconds', render(ep, sys.argv[2]))
