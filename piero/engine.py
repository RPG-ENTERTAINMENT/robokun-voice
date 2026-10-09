"""Piero video engine: dark room + lip-synced clown + timed text overlays.
Used for vertical shorts (1080x1920) and horizontal long videos (1920x1080)."""
import numpy as np, math, os, subprocess, glob
import multiprocessing as mp
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage as nd

FONT = '/usr/share/fonts/opentype/noto/NotoSerifCJK-Black.ttc'
def font(size): return ImageFont.truetype(FONT, size, index=0)

def blur(a, s): return nd.gaussian_filter(a, s)
def noise(h, w, s, seed):
    r = np.random.default_rng(seed).standard_normal((h, w)).astype(np.float32)
    r = blur(r, s); return (r - r.min()) / (r.max() - r.min() + 1e-9)

# ------------------------------------------------------------------ text
def text_img(txt, fnt, fill=(245, 240, 230), glow=(110, 0, 0), stroke=10, spacing=18, max_w=None, grunge=True):
    d0 = ImageDraw.Draw(Image.new('L', (1, 1)))
    bb = d0.multiline_textbbox((0, 0), txt, font=fnt, align='center', spacing=spacing, stroke_width=stroke)
    pad = 60
    w, h = int(bb[2] - bb[0] + 2 * pad), int(bb[3] - bb[1] + 2 * pad)
    m = Image.new('L', (w, h)); dm = ImageDraw.Draw(m)
    dm.multiline_text((pad - bb[0], pad - bb[1]), txt, font=fnt, fill=255, align='center', spacing=spacing, stroke_width=stroke + 8)
    g = m.filter(ImageFilter.GaussianBlur(22))
    out = Image.new('RGBA', (w, h), glow + (0,)); out.putalpha(g.point(lambda p: min(255, p * 2)))
    t = Image.new('RGBA', (w, h), (0, 0, 0, 0)); dt = ImageDraw.Draw(t)
    dt.multiline_text((pad - bb[0], pad - bb[1]), txt, font=fnt, fill=fill, align='center', spacing=spacing, stroke_width=stroke, stroke_fill=(8, 0, 0))
    if grunge:
        a = np.asarray(t).copy(); n = noise(h, w, 2.0, len(txt) + 7)
        a[..., 3] = (a[..., 3] * np.clip(0.55 + n * 1.2, 0, 1)).astype(np.uint8); t = Image.fromarray(a)
    out.alpha_composite(t)
    if max_w and out.width > max_w:
        k = max_w / out.width; out = out.resize((int(out.width * k), int(out.height * k)), Image.LANCZOS)
    return out

# ------------------------------------------------------------------ faces
GRID_R = [(0, 400), (400, 792), (792, 1199)]; GRID_C = [(0, 437), (437, 875), (875, 1312)]
NOSE = [(247, 203), (219, 206), (187, 198), (247, 199), (222, 177), (192, 194), (248, 203), (222, 193), (193, 193)]
REF = (230, 200)

def find_sheet(d):
    fs = sorted(glob.glob(os.path.join(d, '*')))
    fs = [f for f in fs if f.lower().endswith(('.png', '.webp', '.jpg', '.jpeg', '.heic'))]
    if not fs: raise SystemExit('clown image not found in ' + d)
    return fs[0]

def load_faces(path):
    im = Image.open(path).convert('RGBA')
    sx, sy = im.width / 1312, im.height / 1199
    if (sx, sy) != (1, 1): im = im.resize((1312, 1199), Image.LANCZOS)
    A = np.asarray(im).astype(np.float32)
    has_alpha = (A[..., 3] < 250).mean() > 0.05
    faces = []
    for r, (r0, r1) in enumerate(GRID_R):
        for c, (c0, c1) in enumerate(GRID_C):
            cell = A[r0:r1, c0:c1].copy()
            if not has_alpha:   # white background -> transparent (flood from borders)
                mn = cell[..., :3].min(2); mx = cell[..., :3].max(2)
                wh = (mn > 225) & (mx - mn < 20)
                lab, _ = nd.label(wh)
                border = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])) - {0}
                bg = np.isin(lab, list(border))
                soft = np.clip((255 - mn) / 60, 0, 1)
                near = nd.binary_dilation(bg, iterations=4)
                cell[..., 3] = nd.gaussian_filter(np.where(bg, 0, np.where(near, soft, 1)), 0.8) * 255
            k = r * 3 + c
            f = np.zeros((410, 440, 4), np.float32); f[:cell.shape[0], :cell.shape[1]] = cell / 255
            f = nd.shift(f, (REF[1] - NOSE[k][1], REF[0] - NOSE[k][0], 0), order=1, mode='constant')
            fh = f.shape[0]; fy = np.arange(fh, dtype=np.float32)[:, None]
            f[..., 3] *= np.clip((fh - 8 - fy) / 30, 0, 1)
            faces.append(f)
    return faces

# ------------------------------------------------------------------ geometry
GEOM = {
    'short': dict(W=1080, H=1920, wain=1260, door=(30, 280, 630, 1540), knob=(225, 1110), frame=(800, 760),
                  table=1540, candle=(150, 1500), bulb=(880, 300), L1r=420, L1c=((700, 300), 700), L2r=260,
                  vig=(0.5, 0.45, 0.75, 0.62), nose=(540, 1130), SC=2.25, under=950, stripe=120),
    'long': dict(W=1920, H=1080, wain=640, door=(30, 250, 200, 935), knob=(225, 590), frame=None,
                 table=930, candle=(1010, 905), bulb=(640, 40), L1r=360, L1c=((620, 170), 620), L2r=230,
                 vig=(0.4, 0.5, 0.85, 0.85), nose=(590, 555), SC=1.85, under=480, stripe=110),
}

class Scene:
    def __init__(self, kind, faces):
        g = GEOM[kind]; self.g = g; self.kind = kind
        W, H = self.W, self.H = g['W'], g['H']
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); self.yy = yy
        # wall
        base = np.array([62, 56, 46], np.float32) / 255
        st = g['stripe']
        stripe = 0.5 + 0.5 * np.cos(2 * np.pi * xx / st)
        dam = 0.5 + 0.5 * np.cos(2 * np.pi * (xx % st - st / 2) / (st / 2)) * np.cos(2 * np.pi * yy / 90)
        pat = 0.82 + 0.08 * stripe + 0.07 * (dam > 0.8)
        stain = 0.55 + 0.6 * noise(H, W, 60, 1)
        streak = blur(np.random.default_rng(2).standard_normal((H // 8 + 1, W)).astype(np.float32), (40, 3))
        streak = np.kron(streak, np.ones((8, 1), np.float32))[:H]
        streak = 1 - 0.35 * np.clip(streak * 3, 0, 1)
        mold = noise(H, W, 18, 3); mold = 1 - 0.5 * np.clip((mold - 0.6) * 4, 0, 1)
        fine = 0.92 + 0.16 * noise(H, W, 1.2, 4)
        wall = base[None, None] * (pat * stain * streak * mold * fine)[..., None]
        wood = np.array([40, 26, 18], np.float32) / 255
        grain = 0.75 + 0.4 * noise(H, W, (1, 25), 5)
        ws = yy > g['wain']
        panel = 1 - 0.35 * ((xx % 270 < 10) | (yy < g['wain'] + 20))
        wall = np.where(ws[..., None], wood[None, None] * (grain * panel)[..., None], wall)
        x0, x1, y0, y1 = g['door']
        door = (xx > x0) & (xx < x1) & (yy > y0) & (yy < y1)
        frame = door & ~((xx > x0 + 20) & (xx < x1 - 20) & (yy > y0 + 20))
        wall = np.where(door[..., None], (wood * 0.9)[None, None] * grain[..., None], wall)
        wall = np.where(frame[..., None], (wood * 1.3)[None, None] * grain[..., None], wall)
        gap = (xx > x1 - 40) & (xx < x1 - 18) & (yy > y0 + 20) & (yy < y1)
        wall = np.where(gap[..., None], 0.005, wall)
        kx, ky = g['knob']
        wall = np.where((((xx - kx) ** 2 + (yy - ky) ** 2) < 130)[..., None], np.array([0.35, 0.28, 0.12])[None, None], wall)
        img = Image.fromarray((np.clip(wall, 0, 1) * 255).astype(np.uint8))
        if g['frame']:
            pf = Image.new('RGBA', (240, 300), (0, 0, 0, 0)); d = ImageDraw.Draw(pf)
            d.rectangle([0, 0, 239, 299], fill=(70, 52, 20, 255)); d.rectangle([16, 16, 223, 283], fill=(18, 16, 14, 255))
            d.ellipse([85, 70, 155, 150], fill=(42, 38, 33, 255)); d.rectangle([75, 150, 165, 283], fill=(36, 32, 28, 255))
            d.ellipse([102, 100, 112, 110], fill=(90, 20, 20, 255)); d.ellipse([128, 100, 138, 110], fill=(90, 20, 20, 255))
            pf = pf.rotate(-5, expand=True, resample=Image.BICUBIC); img.paste(pf, g['frame'], pf)
        self.WALL = np.asarray(img).astype(np.float32) / 255
        ty = g['table']
        self.TMASK = yy >= ty
        tgrain = 0.7 + 0.5 * noise(H, W, (0.8, 40), 8)
        tcol = np.array([48, 28, 16], np.float32) / 255 * tgrain[..., None]
        tcol *= (1 - 0.5 * np.clip((yy - ty) / max(1, H - ty), 0, 1))[..., None]
        tcol = np.where(((yy >= ty) & (yy < ty + 10))[..., None], tcol * 2.2, tcol)
        self.TABLE = np.where(self.TMASK[..., None], tcol, 0)
        def radial(c, r, p):
            d = np.sqrt((xx - c[0]) ** 2 + (yy - c[1]) ** 2); return 1 / (1 + (d / r) ** p)
        self.L1 = radial(g['bulb'], g['L1r'], 1.8); self.L1c = radial(g['L1c'][0], g['L1c'][1], 1.5)
        self.L2 = radial(g['candle'], g['L2r'], 2.0)
        vx, vy, ax, ay = g['vig']
        self.VIG = np.clip(1.25 - 0.9 * (((xx - W * vx) / (W * ax)) ** 2 + ((yy - H * vy) / (H * ay)) ** 2), 0.12, 1)[..., None]
        self.FOG = noise(H // 4, W // 2, 14, 11)
        self.UNDER = (0.85 + 0.25 * np.clip((yy - g['under']) / 500, 0, 1))[..., None]
        self.GRAIN = [np.random.default_rng(100 + i).standard_normal((H // 2, W // 2)).astype(np.float32) for i in range(6)]
        rng = np.random.default_rng(7); ND = 70 if kind == 'short' else 90
        self.DUST = np.c_[rng.uniform(0, W, ND), rng.uniform(0, H, ND), rng.uniform(1, 3.5, ND), rng.uniform(-8, 8, ND), rng.uniform(-14, -3, ND)]
        # faces
        self.FACES = faces
        fh, fw = faces[0].shape[:2]; self.fh, self.fw = fh, fw
        fy, fx = np.mgrid[0:fh, 0:fw].astype(np.float32)
        def emask(cx, cy, rx, ry, f=0.35):
            d = np.sqrt(((fx - cx) / rx) ** 2 + ((fy - cy) / ry) ** 2); return np.clip((1 - d) / f, 0, 1)[..., None]
        self.MOUTH = emask(REF[0], REF[1] + 45, 70, 40); self.EYES = emask(REF[0], REF[1] - 48, 105, 32)

    def face_img(self, base, mouth, blink):
        f = self.FACES[base].copy()
        if mouth is not None and mouth != base:
            f[..., :3] = f[..., :3] * (1 - self.MOUTH) + self.FACES[mouth][..., :3] * self.MOUTH
        if blink:
            f[..., :3] = f[..., :3] * (1 - self.EYES) + self.FACES[7][..., :3] * self.EYES
        return f

# ------------------------------------------------------------------ timeline
class Timeline:
    """cues: list of dict(s, e, expr, mood); env: mouth envelope per frame; overlays: list of
    dict(s, e, img, xy=(cx, cy), anim='pop'|'fade'|'none', jitter=px)"""
    def __init__(self, cues, env, overlays, total, fps):
        self.cues, self.env, self.ov, self.total, self.fps = cues, env, overlays, total, fps
        self.NF = int(total * fps)
    def cue_at(self, t):
        for i, c in enumerate(self.cues):
            nxt = self.cues[i + 1]['s'] if i + 1 < len(self.cues) else self.total
            if t < nxt: return c
        return self.cues[-1]

def flick(t, seed, base, amt):
    n = sum(math.sin(t * f + seed * p) / (k + 1) for k, (f, p) in enumerate([(13.1, 1.3), (29.7, 2.1), (7.3, .7), (53.0, 3.3)]))
    return base + amt * n

def render_frame(S, T, fi):
    g = S.g; W, H = S.W, S.H; fps = T.fps
    rng = np.random.default_rng(fi * 7919 + 13)
    t = fi / fps
    c = T.cue_at(t); s, e, mood = c['s'], c['e'], c.get('mood', '')
    f1 = 1.0 + 0.06 * math.sin(t * 40)
    if (int(t * 7.3) % 23 == 5) or (mood == 'scare' and e < t < e + 0.25) or (math.sin(t * 2.1) > 0.995):
        f1 = 0.25
    f2 = flick(t, 1, 0.9, 0.12)
    if fi == 0: f1, f2 = 1.0, 0.9
    light = 0.06 + 1.15 * f1 * S.L1 + 0.35 * f1 * S.L1c
    light3 = light[..., None] * np.array([1.0, 0.9, 0.7], np.float32) + (0.9 * f2 * S.L2)[..., None] * np.array([1.0, 0.8, 0.55], np.float32)
    lt = t - s; speaking = s <= t <= e
    lvl = T.env[fi] if (speaking and fi < len(T.env)) else 0
    base = c.get('expr', 1)
    laugh = mood in ('intro', 'outro') and lt < 1.4
    if lvl < 0.07: mouth = {4: 0, 6: 2, 2: 2}.get(base, base)
    elif lvl < 0.3: mouth = 1 if laugh else 8
    else: mouth = 6 if laugh else (4 if (fi // 3) % 3 == 0 else 8)
    if base == 6 and not speaking: mouth = 6 if (fi // 4) % 2 else 2
    blink = (fi % 97 in (0, 1, 2)) and base != 4 and fi > 3
    if mood == 'scare' and t > e: base, mouth, blink = 6, 6, False
    face = S.face_img(base, mouth, blink)
    bob = 6 * math.sin(t * 1.7) + lvl * 6; sway = 4 * math.sin(t * 1.1)
    sc = g['SC'] * (1.0 + 0.03 * min(1, lt / 4))
    fw2, fh2 = int(S.fw * sc), int(S.fh * sc)
    fimg = Image.fromarray((np.clip(face, 0, 1) * 255).astype(np.uint8)).rotate(math.sin(t * 0.9) * 2.2, resample=Image.BICUBIC, center=REF)
    fimg = fimg.resize((fw2, fh2), Image.BICUBIC)
    CX, CY = g['nose']
    ox = int(CX + sway - REF[0] * sc); oy = int(CY + bob - REF[1] * sc)
    canvas = np.zeros((H, W, 4), np.float32)
    fa = np.asarray(fimg).astype(np.float32) / 255
    x0, y0 = max(0, ox), max(0, oy); x1, y1 = min(W, ox + fw2), min(H, oy + fh2)
    canvas[y0:y1, x0:x1] = fa[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
    ca = canvas[..., 3:]
    sh = np.roll(np.roll(ca[..., 0], 60, 0), -70, 1)
    sh = nd.zoom(blur(sh[::4, ::4], 6), 4, order=1)
    shf = np.zeros((H, W), np.float32); shf[:min(H, sh.shape[0]), :min(W, sh.shape[1])] = sh[:H, :W]
    scene = S.WALL * (1 - 0.6 * f1 * shf[..., None]) * light3
    clown_l = (0.10 + 0.95 * f1 * (0.55 + 0.6 * S.L1c) + 0.5 * f2 * S.L2)[..., None] * np.array([1.0, 0.88, 0.78], np.float32)
    clown_l = clown_l * S.UNDER
    scene = scene * (1 - ca) + canvas[..., :3] * clown_l * ca
    scene = np.where(S.TMASK[..., None], S.TABLE * (0.12 + 0.7 * f2 * S.L2 + 0.4 * f1 * S.L1c)[..., None] * np.array([1.3, 1.04, 0.72], np.float32), scene)
    fo = np.roll(S.FOG, int(t * 12), 1)
    fo = nd.zoom(fo, (H / fo.shape[0], W / fo.shape[1]), order=1)
    fof = np.zeros((H, W), np.float32); fof[:min(H, fo.shape[0]), :min(W, fo.shape[1])] = fo[:H, :W]
    scene = scene + (0.05 * fof * (0.4 + S.L1))[..., None] * np.array([0.8, 0.85, 0.9], np.float32)
    scene = scene * S.VIG
    if mood == 'scare':
        k = min(1, max(0, (t - s) / max(0.1, e - s)))
        scene = scene * (1 - 0.3 * k) + scene * np.array([1.2, 0.4, 0.4], np.float32) * 0.3 * k
        if e < t < e + 0.12: scene = scene * 0.3 + np.array([0.9, 0.05, 0.05], np.float32) * 0.7
    gr = np.kron(S.GRAIN[fi % 6], np.ones((2, 2), np.float32))
    grf = np.zeros((H, W), np.float32); grf[:gr.shape[0], :gr.shape[1]] = gr[:H, :W]
    scene = scene + 0.035 * grf[..., None]
    img = Image.fromarray((np.clip(scene, 0, 1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    cx_, cy_ = g['candle']
    d.rectangle([cx_ - 22, cy_ - 80, cx_ + 22, g['table'] + 10], fill=(int(190 * f2), int(170 * f2), int(130 * f2)))
    fl = 1 + 0.15 * math.sin(t * 23)
    d.ellipse([cx_ - 10, cy_ - 80 - 52 * fl, cx_ + 10, cy_ - 78], fill=(255, 200, 90))
    d.ellipse([cx_ - 5, cy_ - 100 - 30 * fl, cx_ + 5, cy_ - 80], fill=(255, 245, 210))
    bx, by = g['bulb']
    d.line([bx, 0, bx, by - 28], fill=(25, 22, 20), width=4)
    bc = int(255 * min(1, f1))
    d.ellipse([bx - 22, by - 28, bx + 22, by + 26], fill=(bc, int(bc * 0.9), int(bc * 0.65)))
    for x, y, r, vx, vy in S.DUST:
        px = (x + vx * t + 10 * math.sin(t + y)) % W; py = (y + vy * t) % H
        br = int(min(255, 40 + 220 * float(S.L1[int(py), int(px)]) * f1))
        d.ellipse([px - r, py - r, px + r, py + r], fill=(br, br, int(br * 0.85)))
    zoom = 1.0; shx = shy = 0
    if mood == 'scare': zoom = 1 + 0.35 * min(1, max(0, (t - s) / (e - s + 0.4))) ** 1.5
    if mood == 'scare' and t > e: zoom = 1.45; shx, shy = rng.integers(-28, 28, 2)
    if mood == 'outro' and lt < 1.5: shx, shy = rng.integers(-6, 6, 2)
    if mood == 'head' and lt < 0.25: zoom = 1.06; shx, shy = rng.integers(-14, 14, 2)
    if fi == 0: zoom, shx, shy = 1.0, 0, 0
    if zoom != 1 or shx or shy:
        cw, ch = W / zoom, H / zoom
        cx0 = max(-30, min(W - cw + 30, CX - cw / 2 + shx)); cy0 = (CY - 80) * (1 - 1 / zoom) + shy
        img = img.transform((W, H), Image.EXTENT, (cx0, cy0, cx0 + cw, cy0 + ch), Image.BICUBIC)
    glitch = (mood == 'head' and lt < 0.22) or (mood == 'scare' and e < t < e + 0.5) or (fi % 211 in (0, 1) and fi > 5)
    if glitch and fi > 0:
        a = np.asarray(img).copy()
        for _ in range(6):
            y = rng.integers(0, H - 80); hgt = rng.integers(10, 80); a[y:y + hgt] = np.roll(a[y:y + hgt], rng.integers(-60, 60), 1)
        a[..., 0] = np.roll(a[..., 0], 12, 1); a[..., 2] = np.roll(a[..., 2], -12, 1)
        img = Image.fromarray(a)
    img = img.convert('RGBA')
    for o in T.ov:
        if not (o['s'] <= t < o['e']): continue
        im2 = o['img']; anim = o.get('anim', 'none')
        if anim in ('pop', 'bigpop') and fi > 0:
            k = min(1, (t - o['s']) / 0.15 + 0.25)
            scl = (1.35 - 0.35 * k) if anim == 'bigpop' else (1.12 - 0.12 * k)
            if scl != 1: im2 = im2.resize((max(1, int(im2.width * scl)), max(1, int(im2.height * scl))), Image.BICUBIC)
            if k < 1:
                aa = np.asarray(im2).copy(); aa[..., 3] = (aa[..., 3] * k).astype(np.uint8); im2 = Image.fromarray(aa)
        j = o.get('jitter', 0)
        jx, jy = (rng.integers(-j, j + 1, 2) if j and fi > 0 else (0, 0))
        cx, cy = o['xy']
        img.alpha_composite(im2, (int(cx - im2.width / 2 + jx), int(cy - im2.height / 2 + jy)))
    return img.convert('RGB')

# ------------------------------------------------------------------ parallel render
_S = _T = None
def _work(args):
    a, b, out = args
    W, H = _S.W, _S.H
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(_T.fps),
                          '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-maxrate', '6M', '-bufsize', '12M', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    for f in range(a, b): p.stdin.write(render_frame(_S, _T, f).tobytes())
    p.stdin.close(); p.wait(); return out

def render_video(S, T, audio_wav, out, procs=None, tmp='tmp_render'):
    global _S, _T
    _S, _T = S, T
    procs = procs or os.cpu_count() or 2
    os.makedirs(tmp, exist_ok=True)
    nseg = procs * 3
    bounds = np.linspace(0, T.NF, nseg + 1).astype(int)
    jobs = [(int(bounds[i]), int(bounds[i + 1]), f'{tmp}/seg{i:03d}.mp4') for i in range(nseg) if bounds[i + 1] > bounds[i]]
    ctx = mp.get_context('fork')
    with ctx.Pool(procs) as pool:
        segs = pool.map(_work, jobs, chunksize=1)
    with open(f'{tmp}/list.txt', 'w') as fh:
        for sgm in segs: fh.write(f"file '{os.path.abspath(sgm)}'\n")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', f'{tmp}/list.txt', '-i', audio_wav,
                    '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out], check=True)
    for sgm in segs: os.remove(sgm)
    return out
