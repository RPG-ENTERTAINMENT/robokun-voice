"""Landscape lesson video (16:9) with ロボしず. usage: render_l.py ep.json vo_dir out.mp4 [--still t ...]"""
import sys, os, json, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
D = os.path.dirname(os.path.abspath(__file__))
EP, VO, OUT = sys.argv[1:4]
A = os.environ.get('IGC_ASSETS', os.path.join(D, '..', 'assets'))
W, H, FPS = 1920, 1080, 30
BLK = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'; BLD = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
def font(p, s): return ImageFont.truetype(p, s, index=0)
NAVY = (10, 40, 100); YEL = (255, 227, 90); WHITE = (255, 255, 255); PINK = (232, 72, 140)
ep = json.load(open(EP)); S = ep['screen']

def wav_info(path):
    with wave.open(path) as w:
        n, sr, ch = w.getnframes(), w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32)
    if ch > 1: x = x.reshape(-1, ch).mean(1)
    return n / sr, x / (np.abs(x).max() + 1e-6), sr

GAP = 0.45; beats = []; t = 0.4
for i, b in enumerate(ep['beats']):
    p = os.path.join(VO, f'{i:02d}.wav'); d, x, sr = wav_info(p)
    env = np.array([np.abs(x[int(k / FPS * sr):int((k + 1) / FPS * sr)]).mean() if int(k / FPS * sr) < len(x) else 0 for k in range(int(d * FPS) + 2)])
    sc = S[b['key']]
    beats.append(dict(i=i, start=t, dur=d, env=env / (env.max() + 1e-6), wav=p, **sc))
    t += d + GAP + sc.get('pause', 0)
TOTAL = t + 1.0
for k, b in enumerate(beats): b['end'] = beats[k + 1]['start'] if k + 1 < len(beats) else TOTAL

BG = Image.open(ep['bg']).convert('RGBA')
PX, PY, PW, PH = 60, 140, 1240, 780
MASK = Image.new('L', (PW, PH), 0); ImageDraw.Draw(MASK).rounded_rectangle((0, 0, PW - 1, PH - 1), 40, fill=255)
IMG = {}
def panel_img(name):
    if name not in IMG:
        im = Image.open(name).convert('RGB')
        r = max(PW * 1.08 / im.width, PH * 1.08 / im.height)
        IMG[name] = im.resize((int(im.width * r), int(im.height * r)), Image.LANCZOS)
    return IMG[name]
SPR = {}
def sprite(name, h):
    if (name, h) not in SPR:
        f = os.path.join(A, 'sp', name + '.png'); f = f if os.path.exists(f) else f[:-4] + '.webp'
        im = Image.open(f).convert('RGBA'); s = h / im.height
        SPR[(name, h)] = im.resize((int(im.width * s), h), Image.LANCZOS)
    return SPR[(name, h)]

def ease(k): return 1 - (1 - min(1, max(0, k))) ** 3
def backout(k, s=2.0):
    k = min(1, max(0, k)) - 1; return k * k * ((s + 1) * k + s) + 1
GL = {}
def glyph(ch, size, fill, stroke, sw):
    key = (ch, size, fill, stroke, sw)
    if key not in GL:
        f = font(BLK, size); pad = sw + 12
        bb = f.getbbox(ch, stroke_width=sw); w = max(1, bb[2] - bb[0]) + pad * 2; h = size + pad * 2 + 16
        g = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        if stroke:
            sh = Image.new('RGBA', (w, h), (0, 0, 0, 0)); ImageDraw.Draw(sh).text((pad - bb[0], pad + 8), ch, font=f, fill=(0, 0, 0, 90), stroke_width=sw, stroke_fill=(0, 0, 0, 90))
            g.alpha_composite(sh.filter(ImageFilter.GaussianBlur(5)))
        ImageDraw.Draw(g).text((pad - bb[0], pad), ch, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke)
        GL[key] = g
    return GL[key]
def layout(text, size, maxw, sw, spacing=1.2, align='center'):
    while True:
        f = font(BLK, size); lines = text.split('\n')
        if max(f.getlength(l) + sw * 0.3 * len(l) for l in lines) + sw * 2 <= maxw or size < 40: break
        size -= 4
    out = []; lh = size * spacing; y0 = -(len(lines) - 1) * lh / 2
    for li, l in enumerate(lines):
        x = -(f.getlength(l) + sw * 0.3 * len(l)) / 2 if align == 'center' else 0
        for ch in l:
            adv = f.getlength(ch) + sw * 0.3; out.append((ch, x + adv / 2, y0 + li * lh)); x += adv
    return out, size
def anim_text(im, text, cx, cy, size, fill, stroke, lt, sw=14, maxw=900, wave=1.0, step=0.04, align='center'):
    pts, size = layout(text, size, maxw, sw, align=align)
    for i, (ch, x, y) in enumerate(pts):
        if ch == ' ': continue
        k = (lt - i * step) / 0.3
        if k <= 0: continue
        sc = max(0.05, backout(k)); dy = (1 - ease(k)) * -50
        wv = wave * 5 * math.sin(2 * math.pi * 0.7 * lt - i * 0.5) * min(1, max(0, (lt - len(pts) * step - 0.3) / 0.5))
        g = glyph(ch, size, fill, stroke, sw)
        if abs(sc - 1) > 0.02: g = g.resize((max(1, int(g.width * sc)), max(1, int(g.height * sc))), Image.BILINEAR)
        if k < 0.34: g = g.copy(); g.putalpha(g.split()[3].point(lambda v: int(v * k / 0.34)))
        im.alpha_composite(g, (int(cx + x - g.width / 2), int(cy + y - g.height / 2 + dy + wv)))
    return len(pts) * step + 0.3

STATIC = BG.copy(); sd = ImageDraw.Draw(STATIC)
tag = ep.get('tag', '')
f = font(BLK, 34); bb = sd.textbbox((40, 48), tag, font=f, anchor='lm')
sd.rounded_rectangle((bb[0] - 22, bb[1] - 12, bb[2] + 22, bb[3] + 12), 28, fill=PINK); sd.text((40, 48), tag, font=f, fill=WHITE, anchor='lm')
f2 = font(BLD, 28); t2 = 'RPGクリエイタースクール'; bb = sd.textbbox((W - 40, 48), t2, font=f2, anchor='rm')
sd.rounded_rectangle((bb[0] - 20, bb[1] - 10, bb[2] + 20, bb[3] + 10), 24, fill=(6, 170, 80)); sd.text((W - 40, 48), t2, font=f2, fill=WHITE, anchor='rm')

if ep.get('credit'):
    fc = font(BLD, 24); sd.text((24, H - 22), ep['credit'], font=fc, fill=(255, 255, 255), anchor='ls', stroke_width=3, stroke_fill=(120, 80, 40))

def frame(tt):
    im = STATIC.copy()
    cur = beats[0]
    for b in beats:
        if tt >= b['start'] - GAP / 2: cur = b
    first = cur['i'] == 0
    lt = 99 if first else tt - (cur['start'] - GAP / 2)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 96, W, 110), fill=(160, 116, 72)); d.rectangle((0, 96, int(W * tt / TOTAL), 110), fill=YEL)
    # panel
    prev = beats[cur['i'] - 1] if cur['i'] else None
    same = prev is not None and prev['img'] == cur['img']
    newimg = cur['img']
    pi = panel_img(newimg); prog = min(1, max(0, (tt - cur['start']) / max(0.1, cur['end'] - cur['start'])))
    z = 1.0 + 0.05 * prog; cw, ch = int(pi.width / 1.08 * 1.08 / z), int(pi.height / 1.08 * 1.08 / z)
    cw, ch = int(PW * 1.08 / z), int(PH * 1.08 / z); ox, oy = (pi.width - cw) // 2, (pi.height - ch) // 2
    crop = pi.crop((ox, oy, ox + cw, oy + ch)).resize((PW, PH), Image.BILINEAR)
    k = 1.0 if (first or cur.get('nocut')) else ease(lt / 0.32)
    if cur.get('fade') or same:   # cross-fade between related slides (e.g. highlight changes)
        if prev and k < 1:
            pp = panel_img(prev['img']); pc = pp.crop((ox, oy, ox + cw, oy + ch)).resize((PW, PH), Image.BILINEAR)
            crop = Image.blend(pc, crop, k)
        xoff = 0
    else:
        xoff = int((1 - k) * -W * 0.75)
    card = Image.new('RGBA', (PW + 16, PH + 16), (0, 0, 0, 0)); ImageDraw.Draw(card).rounded_rectangle((0, 0, PW + 15, PH + 15), 48, fill=WHITE)
    card.paste(crop, (8, 8), MASK)
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((PX + xoff + 4, PY + 16, PX + PW + xoff + 4, PY + PH + 22), 48, fill=(80, 50, 20, 80))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    im.alpha_composite(card, (PX - 8 + xoff, PY - 8))
    # title overlay (frame 0 = thumbnail)
    if cur.get('title'):
        anim_text(im, cur['kicker'], PX + 360, PY + 150, 64, WHITE, PINK, tt + 9 if first else lt, sw=12, maxw=640)
        anim_text(im, cur['title'], PX + 360, PY + 420, 104, YEL, NAVY, tt + 9 if first else lt - 0.3, sw=16, maxw=660)
    # keyword bubble (right top)
    if cur.get('kw'):
        same_kw = prev is not None and prev.get('kw') == cur['kw']
        bk = 1.0 if same_kw else backout((lt - 0.05) / 0.3)
        if bk > 0.02:
            bw, bh = 540, 300
            bub = Image.new('RGBA', (bw + 40, bh + 70), (0, 0, 0, 0)); bd = ImageDraw.Draw(bub)
            bd.rounded_rectangle((20, 20, bw + 20, bh + 20), 46, fill=WHITE, outline=PINK, width=8)
            bd.polygon([(bw // 2 - 10, bh + 16), (bw // 2 + 50, bh + 16), (bw // 2 + 30, bh + 66)], fill=WHITE)
            bd.line((bw // 2 - 6, bh + 22, bw // 2 + 30, bh + 66), fill=PINK, width=8); bd.line((bw // 2 + 30, bh + 66, bw // 2 + 52, bh + 22), fill=PINK, width=8)
            if bk < 0.999: bub = bub.resize((max(1, int(bub.width * bk)), max(1, int(bub.height * bk))), Image.BILINEAR)
            cx, cy = 1610, 330
            im.alpha_composite(bub, (cx - bub.width // 2, cy - bub.height // 2 + int(10 * (1 - bk))))
            if bk > 0.9:
                anim_text(im, cur['kw'], cx, cy - 10, cur.get('kw_size', 76), NAVY, None, 99 if same_kw else lt - 0.18, sw=0, maxw=480, wave=0.5)
    # robo
    fi = int((tt - cur['start']) * FPS); amp = cur['env'][fi] if 0 <= fi < len(cur['env']) else 0
    sp = sprite(cur['pose'], 430); bob = int(8 * math.sin(tt * 2 * math.pi * 0.8))
    if amp > 0.05: sp = sp.resize((int(sp.width * (1 - 0.03 * amp)), int(sp.height * (1 + 0.035 * amp))), Image.BILINEAR)
    d.ellipse((1610 - 140, 1015, 1610 + 140, 1045), fill=(140, 96, 56))
    im.alpha_composite(sp, (1610 - sp.width // 2, 1032 - sp.height + bob - int(14 * amp)))
    return im.convert('RGB')

if '--still' in sys.argv:
    os.makedirs(os.path.dirname(OUT) or '.', exist_ok=True)
    for s_ in sys.argv[sys.argv.index('--still') + 1:]: frame(float(s_)).save(OUT + f'.still_{s_}.png')
    print('total', round(TOTAL, 2)); sys.exit()
n = int(TOTAL * FPS); tmpv = OUT + '.v.mp4'
p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                      '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', tmpv], stdin=subprocess.PIPE)
for f_ in range(n): p.stdin.write(frame(f_ / FPS).tobytes())
p.stdin.close(); p.wait()
ins, flt, mix = [], [], []
def add(path, vol, at, loop=False):
    ins.extend((['-stream_loop', '-1'] if loop else []) + ['-i', path]); k = ins.count('-i'); ms = int(at * 1000)
    flt.append(f'[{k}:a]aresample=48000,volume={vol},adelay={ms}|{ms}' + (f',atrim=0:{TOTAL:.2f},afade=t=in:d=1,afade=t=out:st={TOTAL-1.5:.2f}:d=1.5' if loop else '') + f'[a{k}]'); mix.append(f'[a{k}]')
for b in beats:
    add(b['wav'], 1.7, b['start'])
    if b.get('sfx'): add((lambda q: q if os.path.exists(q) else q[:-4] + '.wav')(os.path.join(A, 'audio', 'sfx', b['sfx'] + '.ogg')), 0.35, max(0, b['start'] - GAP / 2))
add(ep['bgm'], ep.get('bgm_vol', 0.16), 0, loop=True)
bg = mix.pop(); vb = ''.join(mix)
flt.append(f'{vb}amix=inputs={len(mix)}:normalize=0,asplit=2[vox][sc]')
flt.append(f'{bg}[sc]sidechaincompress=threshold=0.02:ratio=6:attack=20:release=400[bgd]')
flt.append('[vox][bgd]amix=inputs=2:normalize=0,loudnorm=I=-15:TP=-1.5:LRA=9[a]')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmpv] + ins + ['-filter_complex', ';'.join(flt), '-map', '0:v', '-map', '[a]',
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-t', f'{TOTAL:.2f}', '-movflags', '+faststart', OUT], check=True)
os.remove(tmpv); print('done', round(TOTAL, 2))
