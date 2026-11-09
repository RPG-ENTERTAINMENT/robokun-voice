"""Overlay + audio for one episode.
  python compose.py <episode.json> <timing.json> <plan.json> <frames dir> <voice.wav> <out.mp4>
Title band, the 'ドン!' title intro, speech bubbles (always in the upper half, tail to the speaker's head), tags, BGM/SE."""
import json, math, os, sys, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
EP, TM, PL, FR, VOICE, OUT = sys.argv[1:7]
ep = json.load(open(EP)); tm = json.load(open(TM)); plan = json.load(open(PL))
W, H, FPS, CFPS = 1080, 1920, 30, plan.get('cfps', 12)
TOP, VH = 420, 1500
INTRO, END = tm['intro'], tm['end']
CUTS = plan['cuts']; LINES = tm['lines']
def _font():
    for p in ['/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc', '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
              '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']:
        if os.path.exists(p): return p
    raise SystemExit('no CJK font')
FB = _font(); _fc = {}
def F(s):
    if s not in _fc: _fc[s] = ImageFont.truetype(FB, s, index=0)
    return _fc[s]
NAME = {'ol': ('ゆり', (240, 110, 150)), 'robo': ('ロボしず', (120, 125, 140))}
FOOT = 'あなたのハテナを解決してみる'

def wrap_title(t):
    t = t.replace('\n', '')
    if len(t) <= 13: return t
    best = len(t) // 2
    for i in range(len(t) // 2 - 4, len(t) // 2 + 5):
        if 0 < i < len(t) and t[i - 1] in 'とをはがにでもの、': best = i; break
    return t[:best] + '\n' + t[best:]
TITLE = wrap_title(ep['title'])

def outline_text(d, xy, text, font, fill=(255, 255, 255), stroke=(0, 0, 0), sw=8, anchor='mm', spacing=14):
    d.multiline_text(xy, text, font=font, fill=fill, stroke_width=sw, stroke_fill=stroke, anchor=anchor, align='center', spacing=spacing)
def fit(d, text, start, maxw, sw=0, spacing=14):
    fs = start
    while fs > 34:
        bb = d.multiline_textbbox((0, 0), text, font=F(fs), stroke_width=sw, spacing=spacing)
        if bb[2] - bb[0] <= maxw: break
        fs -= 2
    return fs
def title_band(img):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, TOP], fill=(30, 28, 40))
    d.rectangle([24, 120, W - 24, 372], outline=(255, 210, 60), width=8)
    d.rectangle([60, 40, 520, 110], fill=(255, 210, 60))
    d.text((290, 75), 'ハテナ解決', font=F(48), fill=(30, 28, 40), anchor='mm')
    fs = fit(d, TITLE, 72, W - 110, 8, 18)
    outline_text(d, (W // 2, 246), TITLE, F(fs), fill=(255, 245, 140), sw=8, spacing=18)
def footer(img):
    d = ImageDraw.Draw(img); d.rectangle([0, H - 64, W, H], fill=(25, 22, 32))
    d.text((W // 2, H - 32), FOOT, font=F(34), fill=(170, 170, 190), anchor='mm')

_heads = {}; _img = {}
def heads(c):
    if c not in _heads: _heads[c] = json.load(open(f'{FR}/c{c:02d}/heads.json'))
    return _heads[c]
def cut_img(c, f):
    if (c, f) not in _img:
        if len(_img) > 6: _img.clear()
        p = f'{FR}/c{c:02d}/f_{f:04d}.jpg'
        if not os.path.exists(p):   # fall back to the nearest rendered frame
            fs = sorted(x for x in os.listdir(f'{FR}/c{c:02d}') if x.startswith('f_'))
            p = f'{FR}/c{c:02d}/{fs[min(len(fs) - 1, f - 1)]}'
        _img[(c, f)] = Image.open(p).convert('RGBA').resize((W, VH), Image.LANCZOS)
    return _img[(c, f)]
def cut_at(t):
    for i, c in enumerate(CUTS):
        if c['t0'] <= t < c['t1']: return i
    return len(CUTS) - 1

def tag(img, txt, lt):
    k = min(1, lt / 0.2); d = ImageDraw.Draw(img); f = F(50)
    bb = d.textbbox((0, 0), txt, font=f); w = bb[2] - bb[0] + 70
    x0 = int(-w + (w + 30) * (1 - (1 - k) ** 3))
    d.rounded_rectangle([x0, H - 200, x0 + w, H - 110], radius=22, fill=(230, 110, 40), outline=(255, 255, 255), width=6)
    d.text((x0 + w // 2, H - 156), txt, font=f, fill=(255, 255, 255), anchor='mm')

def bubble(img, ln, lt, anchor, side):
    nm, nc = NAME[ln['sp']]; d0 = ImageDraw.Draw(img)
    fs = fit(d0, ln['text'], 62, 860)
    bb = d0.multiline_textbbox((0, 0), ln['text'], font=F(fs), spacing=14)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]; bw, bh = max(420, tw + 90), th + 110
    MINY = TOP + 24
    if anchor is not None:
        hx, hy = anchor; by0 = max(MINY, hy - 30 - 60 - bh); cx = hx
        tip = (hx, min(max(hy - 20, by0 + bh + 40), by0 + bh + 160))
    else:
        by0 = MINY; cx = W // 2 + side * 120; tip = (W - 20 if side > 0 else 20, by0 + bh // 2)
    cx = max(bw // 2 + 24, min(W - bw // 2 - 24, cx)); bx0 = cx - bw // 2
    k = min(1, max(0, lt + 0.12) / 0.2); sc_ = 0.55 + 0.45 * (1 - (1 - k) ** 3)
    L = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L); tx, ty = tip
    if ty > by0 + bh:
        bxm = max(bx0 + 60, min(bx0 + bw - 60, tx)); base = [(bxm - 32, by0 + bh - 8), (bxm + 32, by0 + bh - 8)]
    else:
        ex = bx0 + bw - 8 if tx > cx else bx0 + 8; base = [(ex, by0 + bh // 2 - 30), (ex, by0 + bh // 2 + 30)]
    d.rounded_rectangle([bx0, by0, bx0 + bw, by0 + bh], radius=40, fill=(255, 255, 255), outline=(30, 30, 40), width=8)
    d.polygon([base[0], base[1], (tx, ty)], fill=(255, 255, 255))
    d.line([base[0], (tx, ty), base[1]], fill=(30, 30, 40), width=8, joint='curve')
    d.rectangle([bx0 + 30, by0 - 20, bx0 + 250, by0 + 32], fill=nc, outline=(30, 30, 40), width=5)
    d.text((bx0 + 140, by0 + 6), nm, font=F(34), fill=(255, 255, 255), anchor='mm')
    d.multiline_text((cx, by0 + bh // 2 + 10), ln['text'], font=F(fs), fill=(30, 30, 40), anchor='mm', align='center', spacing=14)
    if sc_ < 1:
        b = L.getbbox(); piece = L.crop(b)
        piece = piece.resize((max(1, int(piece.size[0] * sc_)), max(1, int(piece.size[1] * sc_))), Image.LANCZOS)
        L = Image.new('RGBA', (W, H), (0, 0, 0, 0)); L.alpha_composite(piece, (max(0, int(tx - (tx - b[0]) * sc_)), max(0, int(ty - (ty - b[1]) * sc_))))
    img.alpha_composite(L)

COLS = [(255, 255, 255), (255, 230, 90), (255, 255, 255), (255, 230, 90), (255, 255, 255), (255, 230, 90)]
def intro_overlay(img, t):
    ch = tm['chunks']; shown = [c for c in ch if c['t'] <= t]
    if shown: img.alpha_composite(Image.new('RGBA', (W, VH), (10, 8, 20, 120)), (0, TOP))
    n = len(ch); gap = min(180, 900 // max(1, n - 1)) if n > 1 else 0
    y0 = 1020 - gap * (n - 1) // 2 - (40 if n > 1 else 0)
    for i, c in enumerate(shown):
        last = i == n - 1; k = (t - c['t']) / 0.16
        L = Image.new('RGBA', (W, 320), (0, 0, 0, 0)); dd = ImageDraw.Draw(L)
        fs = fit(dd, c['text'], 200 if last else 140, W - 60, 14)
        outline_text(dd, (W // 2, 160), c['text'], F(fs), fill=(255, 70, 80) if last else COLS[i % len(COLS)], sw=14)
        s = 1.0 + max(0, 1 - k) * 0.7
        if s != 1: L = L.resize((int(W * s), int(320 * s)), Image.LANCZOS)
        shake = math.sin(t * 90) * 10 * max(0, 1 - (t - c['t']) / 0.25)
        y = y0 + i * gap + (60 if last else 0)
        img.alpha_composite(L, (int(W // 2 - L.size[0] // 2 + shake), int(y - L.size[1] // 2)))

def frame(t):
    ci = cut_at(t); c = CUTS[ci]; hs = heads(ci)
    f = min(len(hs), int((t - c['t0']) * CFPS) + 1)
    img = Image.new('RGBA', (W, H), (25, 22, 32, 255)); img.alpha_composite(cut_img(ci, f), (0, TOP))
    if t < INTRO:
        intro_overlay(img, t)
    else:
        ln = None
        for l in LINES:
            if l['s'] - 0.12 <= t: ln = l
        ln = ln or LINES[0]
        if ln.get('tag'): tag(img, ln['tag'], t - ln['s'])
        x, y, z = hs[f - 1][ln['sp']]
        if z > 0 and 0.04 < x < 0.96 and 0.0 < y < 1.0: anchor, side = (x * W, TOP + y * VH), 0
        else: anchor, side = None, (-1 if ln['sp'] == 'ol' else 1)
        bubble(img, ln, t - ln['s'], anchor, side)
    title_band(img); footer(img)
    return img.convert('RGB')

# ---------------- audio ----------------
SR = 48000
def mix(path_out):
    w = wave.open(VOICE); v = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    N = len(v); rng = np.random.default_rng(plan['no'])
    sq = lambda f, tt, duty=.5: np.where((tt * f) % 1 < duty, 1., -1.)
    mf = lambda m: 440 * 2 ** ((m - 69) / 12)
    MEL = [[72, 74, 76, 79, 76, 74, 72, 67, 69, 72, 74, 76, 74, 72, 69, 67], [76, 79, 81, 79, 76, 74, 72, 74, 76, 79, 84, 83, 81, 79, 76, 74],
           [69, 72, 76, 72, 74, 77, 81, 77, 72, 76, 79, 76, 74, 71, 67, 71]]
    BASS = [[48, 48, 45, 45, 41, 41, 43, 43], [45, 45, 41, 41, 43, 43, 48, 48], [45, 45, 50, 50, 48, 48, 43, 43]]
    k = plan['no'] % 3; mel, bass = MEL[k], BASS[k]; beat = 60 / (118 + 4 * k)
    bgm = np.zeros(N); s0 = int(INTRO * SR)
    for i in range(int((N - s0) / SR / (beat / 2)) + 1):
        s = s0 + int(i * beat / 2 * SR); e = min(N, s0 + int((i + 1) * beat / 2 * SR))
        if s >= N: break
        tt = np.arange(e - s) / SR
        bgm[s:e] += 0.22 * sq(mf(mel[i % 16]), tt, .25) * np.exp(-tt * 8) + 0.32 * (2 * np.abs(2 * ((tt * mf(bass[(i // 2) % 8])) % 1) - 1) - 1) * np.exp(-tt * 3)
    bgm *= 0.10; sfx = np.zeros(N)
    n = int(0.45 * SR); tt = np.arange(n) / SR; fq = 110 * np.exp(-tt * 6) + 45
    boom = np.sin(2 * np.pi * np.cumsum(fq) / SR) * np.exp(-tt * 7) * 0.9 + 0.35 * rng.standard_normal(n) * np.exp(-tt * 40)
    for i, c in enumerate(tm['chunks']):
        s = int(c['t'] * SR); sfx[s:s + n] += boom[:max(0, min(n, N - s))] * (1.0 if i == len(tm['chunks']) - 1 else 0.8)
    for c in CUTS[2:]:
        s = int(c['t0'] * SR); m = int(.18 * SR); tt2 = np.arange(m) / SR
        if s + m < N: sfx[s:s + m] += 0.06 * rng.standard_normal(m) * np.sin(np.pi * tt2 / .18)
        if c['shot'] in ('shock', 'surprised', 'laugh', 'fire', 'ghost', 'brain_red', 'earth_stop'):
            m = int(.12 * SR); tt2 = np.arange(m) / SR
            if s + m < N: sfx[s:s + m] += 0.3 * sq(600 + 2500 * tt2, tt2) * np.exp(-tt2 * 25)
    out = v * 1.1 + bgm + sfx; out /= max(1, np.abs(out).max() / 0.95)
    st = np.repeat((out * 32767).astype(np.int16)[:, None], 2, 1)
    w = wave.open(path_out, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())

if __name__ == '__main__':
    if len(sys.argv) > 7 and sys.argv[7] == 'check':
        for t in map(float, sys.argv[8:]): frame(t).save(f'{os.path.dirname(OUT) or "."}/check_{t}.jpg', quality=85)
        sys.exit(0)
    n = int(END * FPS); tmp = OUT + '.v.mp4'
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-crf', '20', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', tmp], stdin=subprocess.PIPE)
    for i in range(n): p.stdin.write(frame(i / FPS).tobytes())
    p.stdin.close(); assert p.wait() == 0
    mix(OUT + '.a.wav')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp, '-i', OUT + '.a.wav', '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac',
                    '-b:a', '192k', '-shortest', '-movflags', '+faststart', OUT], check=True)
    os.remove(tmp); os.remove(OUT + '.a.wav')
    print('COMPOSE OK', OUT)
